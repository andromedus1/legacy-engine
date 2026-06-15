"""Sideboard recommender — weighted saturating-coverage (ILP + greedy).

Recommends a 15-card sideboard as a weighted saturating-coverage problem:
  maximize Σ_e weight_e·g(cov_e)  s.t.  Σ_c x_c ≤ budget;  x_c ≤ max_copies.

g(n) = 1 − (1−p)^n  (saturating model, p = _COVERAGE_P ≈ 0.5).
The marginal value of the n-th answer covering element e is weight_e·(g(n)−g(n−1)),
positive but diminishing, so redundant answers earn slots until the budget fills.

Per-card-copy redundancy penalty (epic-sideboard-core-and-hedge-concave-value): the
objective optionally subtracts a per-copy penalty so copies of the SAME card saturate,
  maximize Σ_e weight_e·g(cov_e) − Σ_c Σ_{k≥2} penalty(k)·[card c has ≥k copies].
Gated by ``redundancy_strength`` (default 0.0 → penalty ≡ 0 → byte-identical to the
forced-15 model above). With it on, a copy whose coverage gain < its penalty is not
picked, so the recommendation may be FEWER than 15 cards (the natural-budget τ stop and
the <15 output contract are owned by sibling features in the epic).

Elements = (archetype, tag) pairs + anti-hate pseudo-elements ``"_hate:<k>"``).
Weights  = field_share(archetype) × swing(best_hoser_for_that_tag).
Solver   = PuLP/CBC with incremental y_a^t linearization (exact ILP primary);
           greedy marginal-gain as fallback AND always as the explainable trace.

Heuristic note: swing magnitudes are curated constants (_SWING_DEDICATED / _SWING_SOFT),
NOT empirically derived.  Every SideboardPackage carries ``heuristic_note`` labeling this.

Maindeck-aware extension (epic-deck-generation-sideboard-maindeck):
  When per-card×matchup data clears the confidence gate (≥evolving tier), the
  coverage model element weights are nudged by ``matchup_pressure`` (a multiplier
  in [1, 1+MAX_PRESSURE] derived from how poorly the maindeck performs vs that
  archetype), and a per-matchup OUT/IN plan is computed over the chosen 15.

  GATING: all new behavior is disabled when per-card data is absent (rounds-less
  corpus).  ``matchup_pressure=None`` → element weights are BYTE-IDENTICAL to the
  pre-rework model.  Existing tests never supply a rounds corpus, so they are
  guaranteed to stay green.

  PRESENCE-CORRELATIONAL NOTE: per-card win-rates reflect the registered 75 for
  decks that appeared in resolved matches, not causal game-by-game effects.  The
  OUT/IN plan is a data-guided starting point, not a deterministic prescription.

Archetype-empirical recommendations extension (feature-archetype-empirical-recommendations):
  Two complementary filters prevent anti-synergistic hoser proposals:

  (A) Anti-synergy pre-filter: ``DeckAntiSynergySignals`` captures three deck-composition
      signals derived from oracle-text-free card data (avg CMC, nonbasic land fraction,
      reactive-mass fraction).  ``is_anti_synergistic(card_name, signals)`` checks a
      hard-coded map of known self-harming hosers against those signals.  Implemented as a
      pure function with no DB dependency — testable with hand-built card lists.

      - low_curve deck (avg non-land CMC < 1.5) → Chalice of the Void blocked
      - nonbasic_heavy deck (>50% non-basic lands) → Back to Basics blocked
      - reactive deck (reactive fraction > 0.40) → Defense Grid blocked

  (B) Empirical archetype sideboard pool filter: when ``archetype`` is known and
      the DB has regime-windowed sideboard data, ``_empirical_sideboard_pool`` returns the
      set of cards that real archetype lists ran above ``min_adoption`` (default 5%).
      ``_build_coverage_model`` accepts an optional ``empirical_pool`` frozenset; when
      provided, catalog candidates not in the pool are dropped.

  (C) Empirical pool PROMOTION (fix-sideboard-surface-field-staples):
      Pool cards that are NOT in the catalog are PROMOTED into the candidate set as
      ``HoserCard`` entries with best-effort coverage attribution derived from oracle_text
      and ``card_tags.staple_role``.  This makes high-adoption field staples like
      Force of Negation and Consign to Memory surfaceable even though they are absent from
      the hand-curated HOSER_CATALOG.

      Attribution rules (``_derive_attacks_for_promoted``):
        - "counter target" or "counter that spell" in oracle_text → ``{"combo", "storm-reliant"}``
        - "exile" + "graveyard" in oracle_text → ``{"graveyard-reliant"}``
        - Removal keywords ("destroy target", "exile target creature") → ``{"creature-based"}``
        - ``staple_role`` == "free_interaction" → ``{"combo", "storm-reliant"}``
        - Unattributed cards: a conservative ``{"combo"}`` set (labeled in a warning) so
          the solver can still select them on adoption signal.

      ``max_copies``: from the archetype's modal_count for that card (capped at 4).
      ``swing``: ``_SWING_SOFT`` — conservative, since attribution is best-effort.

      Promoted cards carry a distinct ``promoted_from_empirical`` label so the caller
      can distinguish them from catalog entries.  The anti-synergy filter still applies.

  GATING (gated-additive):
    - Anti-synergy signals are None when no deck card objects are supplied (empty maindeck
      path in tests).  ``is_anti_synergistic(card, None)`` always returns False → no-op.
    - Empirical pool is None when ``archetype`` is not supplied, the archetype has no
      sideboard data, or the pool would be empty.  ``empirical_pool=None`` → no-op.
    - Empirical promotions are None when the caller supplies no ``freq_map`` (the modal-count
      lookup dict).  No promotion → no-op.
    - Existing tests supply empty maindecks and no archetype → both filters are no-ops →
      test output is byte-identical to pre-feature.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Optional

import duckdb

import re

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.advisory.whattoplay import (
    field_vulnerability_tags,
    vulnerability_tags_for_deck,
    _load_deck_cards,
)
from legacy_engine.colors import compute_deck_colors

# Alternative-cost ("pitch") spell detection — mirrors card_tags._FREE_SPELL_RE.
# Force of Will (CMC 5), Force of Negation (CMC 3), Daze (CMC 2), etc. are playable
# for free by pitching a card; their nominal CMC does not predict Chalice self-harm.
# Imported here as a module-level constant to avoid importing card_tags (circular risk).
_PITCH_SPELL_RE = re.compile(
    r"rather than pay this spell's mana cost"
    r"|without paying its mana cost"
    r"|without paying \(its|their\) mana cost"
    r"|you may exile .+ rather than pay"
    r"|you may return .+ to its owner's hand rather than pay",
    re.IGNORECASE,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extension A: MatchupPlan + per-card matchup-value adapter (maindeck-aware rework)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchupPlan:
    """Per-opponent OUT/IN swap plan for the maindeck.

    ``opponent``:   field archetype being planned for.
    ``side_out``:   maindeck cards to remove (card -> copies).
    ``side_in``:    sideboard cards to bring in (card -> copies).
    ``post_board``: the resulting 60 (maindeck − out + in).
    ``n_basis``:    min matchup-cell n backing this plan (0 when degraded).
    ``tier``:       weakest tier among the cells used ("speculative" when degraded).
    ``degraded``:   True when matchup data below gate — no OUT/IN, rely on 15 composition.
    ``note``:       human-readable explanation of the plan or degradation reason.
    """

    opponent: str
    side_out: dict[str, int]
    side_in: dict[str, int]
    post_board: dict[str, int]
    n_basis: int
    tier: str
    degraded: bool
    note: str


@dataclass
class _OppValues:
    """Internal: per-card value data for one opponent matchup."""

    opponent: str
    maindeck: dict   # card -> CardValue (all maindeck cards vs opponent)
    side: dict       # card -> CardValue (all sideboard_15 cards vs opponent)
    cleared_gate: bool


# Gate tiers that count as "data is sufficient to act on"
_VALUE_GATE: tuple[str, ...] = ("evolving", "established")

# Presence-correlational disclaimer surfaced in CLI/report renders
_VALUE_DISCLAIMER = (
    "Per-card win-rates are PRESENCE-CORRELATIONAL (registered 75 for resolved matches), "
    "not causal.  OUT/IN plans are a data-guided starting point, not a deterministic prescription."
)

# Maximum fractional pressure a matchup deficit can add to element weight
_MAX_PRESSURE = 0.5


def _field_matchup_values(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    deck_maindeck: dict[str, int],
    sideboard_15: dict[str, int],
    *,
    since: str | None = None,
    until: str | None = None,
    top_k: int = 8,
    gate: tuple[str, ...] = _VALUE_GATE,
    card_winrates=None,
    adaptive_windows: "dict[str, tuple[str | None, str | None]] | None" = None,
    top_opponents: "list[str] | None" = None,
) -> dict[str, _OppValues]:
    """Build per-opponent CardValue maps for the top_k field archetypes.

    Returns a dict keyed by opponent archetype name.  Each value is an
    ``_OppValues`` with:
      - ``maindeck``: {card -> CardValue} for every card in deck_maindeck vs opponent.
      - ``side``:     {card -> CardValue} for every card in sideboard_15 vs opponent.
      - ``cleared_gate``: True iff any cell in (maindeck ∪ side) vs opponent has
            tier in ``gate`` (meaning the data is sufficient to act on).

    ``card_winrates``: an optional precomputed ``CardWinRates`` (over the same window).
    Pass it to avoid recomputing the heavy full-corpus scan when a caller already has one
    (e.g. ``recommend_sideboard`` reuses one across its two passes; ``tune_deck`` threads
    one through the whole tune). When None, it is computed here.

    ``adaptive_windows``: optional dict mapping opponent archetype → (since, until) for that
    opponent's adaptive ban-aware window.  When provided, a per-window ``CardWinRates``
    cache is built (one scan per distinct window, not per opponent), and each opponent's
    card values are sourced from its own window's aggregate.  When ``card_winrates`` is ALSO
    provided alongside ``adaptive_windows``, it seeds the cache for ``(since, until)`` (the
    uniform fallback window) to avoid a redundant scan when one of the adaptive windows
    happens to match the uniform window.

    ``top_opponents``: pre-computed ordered list of top-k opponents (avoids recomputing
    it when the caller already selected them).  When None, they are computed here.

    Window defaults to the latest ban regime when both since/until are None.

    Returns {} if the per-card win-rate table cannot be built (no rounds data).
    """
    from legacy_engine.analytics.match_results import compute_card_winrates
    from legacy_engine.analytics.card_value import card_values_vs

    # ── Determine top_opponents ────────────────────────────────────────────────
    if top_opponents is None:
        top_opponents = [
            arch
            for arch, _ in sorted(field.shares.items(), key=lambda kv: kv[1], reverse=True)
        ][:top_k]

    main_cards = list(deck_maindeck.keys())
    side_cards = list(sideboard_15.keys())

    # ── Adaptive-windows path (Fix B): per-window CardWinRates cache ──────────
    if adaptive_windows is not None:
        # Build a cache: window_tuple → CardWinRates (one scan per distinct window).
        # Seed the cache with any pre-computed card_winrates to avoid a redundant scan when
        # an adaptive window happens to equal the caller's uniform fallback window.
        wr_cache: dict[tuple[str | None, str | None], object] = {}
        if card_winrates is not None:
            wr_cache[(since, until)] = card_winrates
        result: dict[str, _OppValues] = {}
        for opp in top_opponents:
            opp_window = adaptive_windows.get(opp, (since, until))
            if opp_window not in wr_cache:
                try:
                    wr_cache[opp_window] = compute_card_winrates(
                        con, since=opp_window[0], until=opp_window[1]
                    )
                except Exception as exc:
                    log.debug("_field_matchup_values (adaptive): compute_card_winrates failed for window %s: %s", opp_window, exc)
                    wr_cache[opp_window] = None
            r_opp = wr_cache[opp_window]
            if r_opp is None or r_opp.coverage.decisive_matched == 0:
                # No data for this window — degrade honestly with a note
                result[opp] = _OppValues(
                    opponent=opp,
                    maindeck={},
                    side={},
                    cleared_gate=False,
                )
                continue
            main_vals = card_values_vs(r_opp, main_cards, "main", opp, gate=gate) if main_cards else {}
            side_vals = card_values_vs(r_opp, side_cards, "side", opp, gate=gate) if side_cards else {}
            cleared = any(cv.tier in gate for cv in main_vals.values()) or any(
                cv.tier in gate for cv in side_vals.values()
            )
            result[opp] = _OppValues(
                opponent=opp,
                maindeck=main_vals,
                side=side_vals,
                cleared_gate=cleared,
            )
        return result

    # ── Uniform-window path (original behavior, byte-identical) ───────────────
    if card_winrates is not None:
        r = card_winrates
    else:
        try:
            r = compute_card_winrates(con, since=since, until=until)
        except Exception as exc:
            log.debug("_field_matchup_values: compute_card_winrates failed: %s", exc)
            return {}

    # If there are no resolved matches at all, bail early — all gates will fail.
    if r.coverage.decisive_matched == 0:
        return {}

    result = {}
    for opp in top_opponents:
        main_vals = card_values_vs(r, main_cards, "main", opp, gate=gate) if main_cards else {}
        side_vals = card_values_vs(r, side_cards, "side", opp, gate=gate) if side_cards else {}

        # Gate: any cell with tier in the gate counts as "cleared"
        cleared = any(cv.tier in gate for cv in main_vals.values()) or any(
            cv.tier in gate for cv in side_vals.values()
        )

        result[opp] = _OppValues(
            opponent=opp,
            maindeck=main_vals,
            side=side_vals,
            cleared_gate=cleared,
        )

    return result


# ---------------------------------------------------------------------------
# Saturating coverage model  g(n) = 1 − (1−p)^n
# ---------------------------------------------------------------------------

_COVERAGE_P = 0.5  # per-answer success probability for the saturating model


def _g(n: int) -> float:
    """Saturating coverage value at n answers: g(n) = 1 − (1−_COVERAGE_P)^n."""
    if n <= 0:
        return 0.0
    return 1.0 - (1.0 - _COVERAGE_P) ** n


def _marginal_g(n: int) -> float:
    """Marginal value of the n-th answer: g(n) − g(n−1).  Always > 0 for n ≥ 1."""
    return _g(n) - _g(n - 1)


# ---------------------------------------------------------------------------
# Per-card-copy redundancy penalty (epic-sideboard-core-and-hedge-concave-value)
# ---------------------------------------------------------------------------
# The per-element saturating g(n) above already diminishes the value of multiple
# *answers* to one element (the access-probability term). What it does NOT capture is
# the disutility of stacking copies of the SAME card: per the sideboard-construction
# brief, "the 2nd copy in hand is frequently a dead draw that displaces a threat", so
# the marginal utility of the k-th DRAWN copy decays sharply. We model that as an
# additive per-copy penalty subtracted from a card's coverage marginal — additive (not
# a multiplicative factor) so the greedy and the ILP share one LP-representable
# objective. Gated-additive: strength=0.0 → penalty(k)=0 ∀k → byte-identical baseline.

# Utility weight of the k-th drawn copy (k=1,2,3,4); k>len clamps to the last entry.
_U_REDUNDANCY_DEFAULT: tuple[float, ...] = (1.0, 0.55, 0.25, 0.10)
# Penalty scale in coverage-value units. Tunable; default chosen so the 2nd copy of a
# card competes with covering a fresh element rather than stacking. The natural-budget
# τ stop (dedicated-core feature) is the real budget control; this only *shapes* copies.
_REDUNDANCY_STRENGTH: float = 0.10


def _u_redundancy(k: int, curve: tuple[float, ...] = _U_REDUNDANCY_DEFAULT) -> float:
    """Utility weight of the k-th drawn copy of a card (1.0 at k=1, decaying).

    ``k`` clamps to ``len(curve)`` so high copy counts never raise. ``k <= 0`` → 1.0.
    """
    if k <= 1:
        return curve[0]
    return curve[min(k, len(curve)) - 1]


def _redundancy_penalty(
    k: int,
    *,
    strength: float = _REDUNDANCY_STRENGTH,
    curve: tuple[float, ...] = _U_REDUNDANCY_DEFAULT,
) -> float:
    """Additive penalty for the k-th copy of a card: ``strength · (1 − _u_redundancy(k))``.

    ``penalty(1) == 0.0`` (the first copy is never penalized); non-decreasing in k.
    ``strength == 0.0`` → ``0.0`` for all k (the gated no-op baseline).
    """
    if strength <= 0.0:
        return 0.0
    return strength * (1.0 - _u_redundancy(k, curve))


# ---------------------------------------------------------------------------
# Heuristic swing constants (NOT empirical — labeled in every package output)
# ---------------------------------------------------------------------------

_SWING_DEDICATED = 0.20   # dedicated hate vs its primary target tag
_SWING_SOFT = 0.10        # soft / partial answers (counter-hosers, artifact removal, etc.)

# Pseudo-element key prefix for anti-hate elements
_HATE_ELEMENT_PREFIX = "_hate:"

# Minimum weight threshold for anti-hate pseudo-elements (filter out noise)
_HATE_ELEMENT_MIN_WEIGHT = 0.02

_HEURISTIC_NOTE = (
    "Swing magnitudes (_SWING_DEDICATED=0.20, _SWING_SOFT=0.10) are curated heuristic constants, "
    "NOT empirically derived from before/after-sideboard win-rate data.  The coverage structure "
    "(which archetypes/tags are answered and their field-share weighting) is data-driven; "
    "the per-tag swing magnitude is an estimate.  Treat card ordering as indicative, not precise."
)

# Note on measurability (feature-empirical-sideboard-swings):
# ─────────────────────────────────────────────────────────────
# What is NOT measurable from this corpus:
#   A true "before/after-board" win-rate swing cannot be derived.  The ``rounds``
#   table stores only match-level aggregate scores ("2-1", "2-0") — individual
#   game-within-match outcomes are not recorded, so game 1 (pre-board) cannot be
#   separated from games 2–3 (post-board).
#
# What IS available (presence-correlational proxy):
#   ``card_value_matchup`` from ``analytics.card_value`` provides a per-card×matchup
#   lift estimate: how much better decks running card X in board ``"side"`` tend to win
#   vs archetype Y, relative to the card's overall corpus average.  This is a
#   PRESENCE-CORRELATIONAL signal (registered 75 for decks that appeared in resolved
#   matches) — confounded by deck quality and player selection.  It is NOT causal.
#
#   Where this signal gates at ≥ evolving tier (n ≥ 30), it is used to replace the
#   catalog's curated swing for that card in the ``best_swing_for_tag`` computation.
#   This is labeled ``"data-informed"`` (not "empirical") throughout.  Where the data
#   is thin (speculative tier, n < 30), the curated constant + caveat is retained.

# Maximum swing value the empirical proxy is allowed to produce.
# The curated _SWING_DEDICATED cap of 0.20 reflects expert estimates; the proxy
# can exceed it on strong presence-correlational signal, but is capped to prevent
# extreme selection effects from dominating the element weights.
_EMPIRICAL_SWING_CAP: float = 0.35

# Minimum lift magnitude to treat the proxy as a non-trivial signal.
# Lifts smaller than this (in absolute value) are treated as noise and the catalog
# constant is retained.
_EMPIRICAL_SWING_MIN_LIFT: float = 0.02

_DATA_INFORMED_NOTE = (
    "Swing magnitudes (_SWING_DEDICATED=0.20, _SWING_SOFT=0.10) are curated heuristic constants.  "
    "Where per-card corpus data cleared the ≥evolving tier (n≥30 decisive matches) for sideboard "
    "cards vs specific matchups, a PRESENCE-CORRELATIONAL swing proxy replaced the catalog value "
    "in the element-weight computation for those cards.  This proxy reflects how decks registering "
    "card X in their sideboard fared vs archetype Y — confounded by deck-quality selection, NOT a "
    "causal before/after-board measurement (individual game outcomes are not in the corpus).  Cards "
    "with thin data (n<30) retain the curated constant + caveat.  Treat card ordering as indicative."
)


def empirical_swing_proxy(cv: object) -> "float | None":
    """Convert a ``CardValue`` for a sideboard card to a presence-correlational swing proxy.

    Accepts any object with ``.tier`` (str) and ``.lift`` (float) attributes, matching the
    ``CardValue`` dataclass from ``analytics.card_value``.  Using ``object`` in the signature
    avoids a circular import (sideboard.py ← advisory ← analytics) while remaining duck-typed.

    Returns a float in ``(_EMPIRICAL_SWING_MIN_LIFT, _EMPIRICAL_SWING_CAP]`` when
    the card value gates at ``"evolving"`` or ``"established"`` tier AND the lift is
    above the noise floor ``_EMPIRICAL_SWING_MIN_LIFT``.  Returns ``None`` otherwise.

    HONESTY CONSTRAINTS:
    - Only positive lifts produce a proxy (negative lift = the card is present in
      losing decks; using it as a SWING proxy would be misleading — we keep the
      curated constant instead so the card is not penalised by selection effects).
    - Lifts below ``_EMPIRICAL_SWING_MIN_LIFT`` are treated as noise (return None).
    - The proxy is capped at ``_EMPIRICAL_SWING_CAP`` (0.35) to prevent extreme
      selection-effect outliers from dominating element weights.
    - Callers MUST label the proxy as "data-informed (presence-correlational)" and
      MUST NOT present it as a causal win-rate delta.

    Parameters
    ----------
    cv : CardValue (duck-typed as object)
        A ``card_value_matchup`` result for a sideboard card (``board="side"``) vs a
        specific opponent archetype.

    Returns
    -------
    float | None
        The proxy swing value, or None when the data is thin or the lift is negligible.
    """
    tier = getattr(cv, "tier", None)
    lift = getattr(cv, "lift", 0.0)

    if tier not in ("evolving", "established"):
        return None
    if lift < _EMPIRICAL_SWING_MIN_LIFT:
        return None
    return min(lift, _EMPIRICAL_SWING_CAP)


# ---------------------------------------------------------------------------
# Unit 1: HoserCard + HOSER_CATALOG
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HoserCard:
    """A curated sideboard hoser candidate.

    ``attacks``: frozenset of vulnerability tags (or ``"_hate"`` for counter-hosers that
                 protect the deck by answering the field's hate cards).
    ``colors``:  frozenset of WUBRG single-char color strings required to cast.
                 Empty frozenset = colorless (always legal).
    ``max_copies``: hard upper bound on copies in the 15 (catalog-curated).
    ``swing``:   heuristic win-rate-swing constant (curated, NOT empirical).
    ``castable_any_color``: True for cards with alternate costs that make them
                 castable regardless of deck color identity (e.g. Phyrexian mana,
                 free-activation abilities).  When True the color pre-filter is
                 bypassed so all decks can receive the card as a candidate.
    """

    name: str
    attacks: frozenset[str]
    colors: frozenset[str]
    max_copies: int
    swing: float
    castable_any_color: bool = False


# ---------------------------------------------------------------------------
# Hoser catalog loader — reads from the editable JSON data file.
# Mirrors the variants-registry load pattern (config.HOSERS_REGISTRY_PATH).
# ---------------------------------------------------------------------------

# Swing-alias map: JSON authors write "dedicated" / "soft" instead of raw floats
# so the data file is self-documenting and immune to constant renames in code.
_SWING_ALIAS: dict[str, float] = {
    "dedicated": _SWING_DEDICATED,
    "soft": _SWING_SOFT,
}

_VALID_COLORS = frozenset("WUBRG")


def load_hoser_catalog(path: "Path | str") -> "dict[str, HoserCard]":
    """Load and validate a hoser catalog from a JSON data file.

    Format: ``{"version": "<date>", "hosers": [ { ... }, ... ]}``.

    Each hoser entry must have:
      ``name``          (str)
      ``attacks``       (list of tag strings; non-empty)
      ``colors``        (list of WUBRG single-char strings; empty = colorless)
      ``max_copies``    (int ≥ 1)
      ``swing``         (float in (0,1) OR the aliases "dedicated" / "soft")

    Optional:
      ``castable_any_color`` (bool, default False)
      ``_comment``           (str, ignored)

    Raises ``ValueError`` on schema violations (bad swing alias, empty attacks,
    invalid colors, max_copies < 1) or ``FileNotFoundError`` when the path is absent.
    Duplicate names raise ``ValueError`` so catalog integrity is enforced at load time.

    This is a module-level loader called once at import; the result is cached as
    ``HOSER_CATALOG``.  Callers that need a different catalog can call
    ``load_hoser_catalog`` directly.
    """
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    hosers_raw = raw.get("hosers")
    if not isinstance(hosers_raw, list):
        raise ValueError(f"load_hoser_catalog: 'hosers' must be a list in {path}")

    catalog: dict[str, HoserCard] = {}
    for idx, entry in enumerate(hosers_raw):
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"load_hoser_catalog: entry[{idx}] missing or empty 'name'")

        if name in catalog:
            raise ValueError(
                f"load_hoser_catalog: duplicate hoser name {name!r} at entry[{idx}] in {path}"
            )

        attacks_raw = entry.get("attacks")
        if not isinstance(attacks_raw, list) or not attacks_raw:
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'attacks' must be a non-empty list"
            )
        attacks = frozenset(str(t) for t in attacks_raw)

        colors_raw = entry.get("colors")
        if not isinstance(colors_raw, list):
            raise ValueError(f"load_hoser_catalog: {name!r} 'colors' must be a list")
        colors: frozenset[str] = frozenset(
            c for c in (str(x) for x in colors_raw) if c in _VALID_COLORS
        )
        # Warn on unrecognized color chars (silently drop; not a hard error).
        unknown = [x for x in colors_raw if str(x) not in _VALID_COLORS]
        if unknown:
            log.warning(
                "load_hoser_catalog: %r has unrecognized color chars %s (dropped)", name, unknown
            )

        max_copies = entry.get("max_copies")
        if not isinstance(max_copies, int) or max_copies < 1:
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'max_copies' must be an int ≥ 1"
            )

        swing_raw = entry.get("swing")
        if isinstance(swing_raw, str):
            if swing_raw not in _SWING_ALIAS:
                raise ValueError(
                    f"load_hoser_catalog: {name!r} swing alias {swing_raw!r} unknown; "
                    f"use 'dedicated', 'soft', or a float"
                )
            swing = _SWING_ALIAS[swing_raw]
        elif isinstance(swing_raw, (int, float)):
            swing = float(swing_raw)
        else:
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'swing' must be a float or alias string"
            )
        if not (0.0 < swing < 1.0):
            raise ValueError(
                f"load_hoser_catalog: {name!r} swing={swing} out of (0, 1)"
            )

        castable_any_color = bool(entry.get("castable_any_color", False))

        catalog[name] = HoserCard(
            name=name,
            attacks=attacks,
            colors=colors,
            max_copies=max_copies,
            swing=swing,
            castable_any_color=castable_any_color,
        )

    return catalog


# Load the catalog from the shipped data file at module import time.
# The path is resolved from config so tests can override HOSERS_REGISTRY_PATH.
# Inline the default path here (same pattern as variants: no runtime import of config
# in the hot path — the path is a constant once the module loads).
def _load_default_hoser_catalog() -> "dict[str, HoserCard]":
    """Load HOSER_CATALOG from the shipped data file; fall back to empty dict on error."""
    try:
        from legacy_engine.config import HOSERS_REGISTRY_PATH
        return load_hoser_catalog(HOSERS_REGISTRY_PATH)
    except Exception as exc:
        log.error(
            "HOSER_CATALOG: failed to load from data file — returning empty catalog: %s", exc
        )
        return {}


HOSER_CATALOG: dict[str, HoserCard] = _load_default_hoser_catalog()


# ---------------------------------------------------------------------------
# Extension C: Anti-synergy filter + empirical archetype pool
# (feature-archetype-empirical-recommendations)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeckAntiSynergySignals:
    """Deck-composition signals used to block self-harming hoser proposals.

    All three signals are derived from the deck's card objects (no DB beyond card lookup).
    The dataclass is frozen so it can be safely passed through the solver pipeline.

    ``low_curve``: avg non-land CMC < ``_LOW_CURVE_CMC_THRESHOLD`` — Chalice@1 wrecks the deck.
    ``nonbasic_heavy``: >``_NONBASIC_FRACTION_THRESHOLD`` of land slots are non-basics
                        (e.g. duals/fetches) — Back to Basics locks the deck out.
    ``reactive``: reactive fraction of the non-land card pool > ``_REACTIVE_FRACTION_THRESHOLD``
                  — Defense Grid prevents the deck from operating on the opponent's turn.
    """

    low_curve: bool        # avg non-land CMC < threshold → Chalice self-harm
    nonbasic_heavy: bool   # >threshold fraction of lands are non-basic → BtB self-harm
    reactive: bool         # reactive mass fraction > threshold → Defense Grid self-harm


# Thresholds (empirically tuned to the Dimir Tempo archetype profile)
_LOW_CURVE_CMC_THRESHOLD: float = 1.5   # avg non-land CMC; below this → low-curve
_NONBASIC_FRACTION_THRESHOLD: float = 0.50  # fraction of land slots; above → nonbasic-heavy
_REACTIVE_FRACTION_THRESHOLD: float = 0.40  # fraction of non-land card pool; above → reactive

# Empirical sideboard pool: minimum adoption rate to include a card in the pool.
# 5% means the card appeared in the sideboard of ≥5% of the archetype's in-regime decks.
_EMPIRICAL_POOL_MIN_ADOPTION: float = 0.05


# Map: hoser name → tuple of signal attribute names that make it anti-synergistic.
# A hoser is blocked if ANY of its listed signals is True on the deck.
_ANTI_SYNERGY_MAP: dict[str, tuple[str, ...]] = {
    "Chalice of the Void": ("low_curve",),
    "Back to Basics": ("nonbasic_heavy",),
    "Defense Grid": ("reactive",),
}


def compute_deck_anti_synergy_signals(
    cards_with_counts: "list[tuple[object, int]]",
) -> DeckAntiSynergySignals:
    """Derive anti-synergy signals from a (Card, count) list (pure, no DB).

    Accepts the same ``list[tuple[Card, count]]`` format as ``_load_deck_cards``
    returns.  Returns all-False when the list is empty (no deck → no signals).

    The three signals:
    - ``low_curve``: avg non-land CMC < _LOW_CURVE_CMC_THRESHOLD.
    - ``nonbasic_heavy``: fraction of land slots that are non-basic > _NONBASIC_FRACTION_THRESHOLD.
    - ``reactive``: reactive non-land card fraction > _REACTIVE_FRACTION_THRESHOLD.
      "Reactive" cards are counters, removal, and protection spells — identified via
      the ``_card_roles`` helper from ``whattoplay`` (not imported directly to avoid
      a circular import; we inline the reactive-role logic here).

    This is an objective-search-split pure function: heavy DB work (resolving cards)
    is already done by the caller; this function only does arithmetic.
    """
    if not cards_with_counts:
        return DeckAntiSynergySignals(low_curve=False, nonbasic_heavy=False, reactive=False)

    # --- low_curve: avg non-land CMC ---
    total_nonland_cmc = 0.0
    total_nonland_count = 0
    total_land_count = 0
    total_nonbasic_land_count = 0

    # --- reactive: count cards whose role includes counter/removal/protection ---
    reactive_nonland_count = 0

    for card, count in cards_with_counts:
        is_land = getattr(card, "is_land", False)
        cmc = getattr(card, "cmc", 0.0) or 0.0
        type_line = (getattr(card, "type_line", "") or "").lower()
        oracle_text = (getattr(card, "oracle_text", "") or "").lower()

        if is_land:
            total_land_count += count
            # Non-basic: not a basic land (doesn't have "Basic" in type line)
            if "basic" not in type_line:
                total_nonbasic_land_count += count
        else:
            total_nonland_count += count
            # Exclude free pitch spells (Force of Will, Daze, Force of Negation, etc.)
            # from the CMC average.  Their nominal CMC (5, 2, 3 …) inflates the average
            # and prevents low_curve from firing for decks that ARE vulnerable to Chalice
            # @1 — they run 4x Brainstorm/Ponder at CMC 1 alongside 4x FoW at CMC 5.
            # Pitch spells are playable for free so their CMC does not predict self-harm.
            is_pitch = bool(_PITCH_SPELL_RE.search(oracle_text))
            if not is_pitch:
                total_nonland_cmc += cmc * count
            # Reactive role detection (inline, avoids circular import with whattoplay).
            # Keywords that mark interaction-on-opponent's-turn play patterns.
            is_reactive = any(kw in oracle_text for kw in (
                "counter target",
                "counter that spell",
                "destroy target",
                "exile target creature",
                "exile target attacking",
                "protection from",
                "hexproof",
                "shroud",
            ))
            if is_reactive:
                reactive_nonland_count += count

    avg_cmc = (
        total_nonland_cmc / total_nonland_count if total_nonland_count > 0 else 2.0
    )
    nonbasic_fraction = (
        total_nonbasic_land_count / total_land_count if total_land_count > 0 else 0.0
    )
    reactive_fraction = (
        reactive_nonland_count / total_nonland_count if total_nonland_count > 0 else 0.0
    )

    return DeckAntiSynergySignals(
        low_curve=avg_cmc < _LOW_CURVE_CMC_THRESHOLD,
        nonbasic_heavy=nonbasic_fraction > _NONBASIC_FRACTION_THRESHOLD,
        reactive=reactive_fraction > _REACTIVE_FRACTION_THRESHOLD,
    )


def is_anti_synergistic(
    card_name: str,
    signals: "DeckAntiSynergySignals | None",
) -> bool:
    """Return True if ``card_name`` is anti-synergistic with the deck described by ``signals``.

    Pure lookup: checks ``_ANTI_SYNERGY_MAP`` against the signals.  Returns False when
    ``signals`` is None (gated-additive no-op for callers without deck data).
    """
    if signals is None:
        return False
    reasons = _ANTI_SYNERGY_MAP.get(card_name)
    if not reasons:
        return False
    return any(getattr(signals, attr, False) for attr in reasons)


def _empirical_sideboard_pool(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    since: "str | None" = None,
    until: "str | None" = None,
    min_adoption: float = _EMPIRICAL_POOL_MIN_ADOPTION,
) -> "tuple[frozenset[str], dict[str, int]] | None":
    """Return ``(pool, freq_map)`` for the archetype's real sideboard, or None when no data.

    ``pool`` — frozenset of cards whose sideboard adoption >= ``min_adoption``.
    ``freq_map`` — mapping of card name → modal_count (for max_copies on promoted cards).

    Uses ``card_frequencies(board='side')`` — the per-archetype in-regime adoption primitive.
    Returns None (not a pair of empty containers) when:
    - the archetype has no in-regime sideboard data (thin archetype)
    - card_frequencies raises (schema not initialised, etc.)

    Returning None (vs an empty pool) allows callers to distinguish "no data → skip filter"
    from "data says no cards pass threshold → genuinely empty pool".  In practice the latter
    is extremely rare and is still treated as None (skip filter) to avoid producing empty
    sideboards when real archetype data is absent.
    """
    try:
        from legacy_engine.generation.consensus import card_frequencies
        freqs = card_frequencies(con, archetype, board="side", since=since, until=until)
        if not freqs:
            return None
        freq_map = {cf.name: cf.modal_count for cf in freqs}
        pool = frozenset(
            cf.name for cf in freqs if cf.inclusion_pct >= min_adoption
        )
        return (pool, freq_map) if pool else None
    except Exception as exc:
        log.debug("_empirical_sideboard_pool: card_frequencies failed for %r: %s", archetype, exc)
        return None


# ---------------------------------------------------------------------------
# Extension C: Empirical pool promotion
# (fix-sideboard-surface-field-staples)
# ---------------------------------------------------------------------------

# Minimum adoption rate for an empirical card to be promoted into the candidate set.
# Must match or exceed _EMPIRICAL_POOL_MIN_ADOPTION (both default to 5%).
_EMPIRICAL_PROMOTE_MIN_ADOPTION: float = _EMPIRICAL_POOL_MIN_ADOPTION

# Tag set assigned when oracle_text attribution is genuinely unknown.
# Conservative single tag so the card participates but does not over-capture.
_FALLBACK_ATTACKS: frozenset[str] = frozenset({"combo"})


def _derive_attacks_for_promoted(
    card_name: str,
    oracle_text: str,
    type_line: str,
) -> frozenset[str]:
    """Derive best-effort vulnerability-tag coverage for a promoted empirical card.

    Pure function — no DB.  Priority order (multiple tags possible):

    1. Counter magic:  "counter target" / "counter that spell"
       → {combo, storm-reliant}   (answers the most common free-spell targets)
    2. Graveyard exile: "exile" AND "graveyard" present
       → {graveyard-reliant}
    3. Removal: "destroy target" / "exile target creature" / "exile target attacking"
       → {creature-based}
    4. staple_role == "free_interaction" (card_tags lookup)
       → {combo, storm-reliant}   (Force of Negation, Daze, etc.)
    5. Artifact/enchantment removal: "destroy target artifact" / "destroy target enchantment"
       → {greedy-manabase}        (answers Blood Moon, Back to Basics, Chalice)
    6. Fallback: {combo}  (conservative — labeled in warning by caller).

    Returns a frozenset of tag strings.  Never returns the empty frozenset so
    ``HoserCard.attacks`` is always non-empty.
    """
    from legacy_engine.card_tags import staple_role

    text_lower = (oracle_text or "").lower()
    tags: set[str] = set()

    # 1. Counter magic
    if "counter target" in text_lower or "counter that spell" in text_lower:
        tags.update({"combo", "storm-reliant"})

    # 2. Graveyard exile
    if "graveyard" in text_lower and "exile" in text_lower:
        tags.add("graveyard-reliant")

    # 3. Creature removal
    if (
        "destroy target" in text_lower
        or "exile target creature" in text_lower
        or "exile target attacking" in text_lower
    ):
        tags.add("creature-based")

    # 4. staple_role == free_interaction (Force of Negation, Daze, etc.)
    if staple_role(card_name) == "free_interaction":
        tags.update({"combo", "storm-reliant"})

    # 5. Artifact/enchantment removal → answers lock pieces / mana hosers
    if (
        "destroy target artifact" in text_lower
        or "destroy target enchantment" in text_lower
        or ("exile target" in text_lower and "artifact" in text_lower)
        or ("exile target" in text_lower and "enchantment" in text_lower)
    ):
        tags.add("greedy-manabase")

    return frozenset(tags) if tags else _FALLBACK_ATTACKS


def _build_promoted_candidates(
    empirical_pool: "frozenset[str]",
    catalog: "dict[str, HoserCard]",
    freq_map: "dict[str, int]",
    con: "duckdb.DuckDBPyConnection",
) -> "tuple[dict[str, HoserCard], list[str]]":
    """Build HoserCard entries for empirical-pool cards NOT already in the catalog.

    Promoted cards participate in the coverage solver exactly like catalog cards, but with:
    - ``swing = _SWING_SOFT`` (conservative — attribution is best-effort).
    - ``attacks`` derived by ``_derive_attacks_for_promoted`` (oracle_text heuristics).
    - ``colors`` from the DB card record (or empty frozenset if card not in DB).
    - ``max_copies`` from ``freq_map`` (modal_count), capped at 4.
    - ``castable_any_color`` derived from ``card_tags.is_free_spell``.

    Returns ``(promoted_dict, warnings)`` where ``promoted_dict`` maps card_name → HoserCard
    and ``warnings`` is a list of human-readable strings for cards that fell back to the
    conservative attribution.

    When the oracle_text lookup fails (card not in DB), the card is still promoted with
    empty colors (colorless = always castable) and the fallback tag set.

    GATING: returns ({}, []) when ``empirical_pool`` is None or when ``freq_map`` is empty.
    This is called ONLY from ``_build_coverage_model`` when ``empirical_pool`` is not None.
    """
    promoted: dict[str, HoserCard] = {}
    warnings: list[str] = []

    pool_not_in_catalog = empirical_pool - frozenset(catalog.keys())
    if not pool_not_in_catalog:
        return {}, []

    # Batch-fetch card data from the DB for all promoted cards.
    # ``colors`` is stored as a concatenated WUBRG string (e.g. "U", "UB", "WUB") —
    # see store.py _tuple: "".join(colors).
    card_data: dict[str, tuple[str, str, list[str], bool]] = {}  # name → (oracle, type, colors, free)
    try:
        from legacy_engine.card_tags import _FREE_SPELL_RE
        rows = con.execute(
            "SELECT name, oracle_text, type_line, colors FROM cards WHERE name IN ({})".format(
                ", ".join("?" * len(pool_not_in_catalog))
            ),
            list(pool_not_in_catalog),
        ).fetchall()
        for row in rows:
            name, oracle_text, type_line, colors_raw = row
            # colors is a VARCHAR string like "U", "UB", "WUB", or NULL / ""
            if isinstance(colors_raw, str):
                # Each character is a WUBRG color letter
                colors_list = [c for c in colors_raw if c in "WUBRG"]
            else:
                colors_list = []
            free = bool(_FREE_SPELL_RE.search(oracle_text or ""))
            card_data[name] = (oracle_text or "", type_line or "", colors_list, free)
    except Exception as exc:
        log.debug("_build_promoted_candidates: card DB fetch failed: %s", exc)

    for card_name in sorted(pool_not_in_catalog):  # sorted for determinism
        oracle_text, type_line, colors_list, free_spell = card_data.get(
            card_name, ("", "", [], False)
        )

        attacks = _derive_attacks_for_promoted(card_name, oracle_text, type_line)

        # Warn when attribution fell back to the conservative default
        if attacks == _FALLBACK_ATTACKS and not oracle_text:
            warnings.append(
                f"promoted empirical card {card_name!r}: not found in DB — "
                f"using fallback attacks={sorted(_FALLBACK_ATTACKS)}; review attribution"
            )
        elif attacks == _FALLBACK_ATTACKS:
            warnings.append(
                f"promoted empirical card {card_name!r}: oracle_text attribution unknown — "
                f"using fallback attacks={sorted(_FALLBACK_ATTACKS)}; review attribution"
            )

        # max_copies from modal_count, capped at 4
        max_copies = min(freq_map.get(card_name, 2), 4)

        # Colors from card DB record
        card_colors: frozenset[str] = frozenset(c for c in colors_list if c in "WUBRG")

        promoted[card_name] = HoserCard(
            name=card_name,
            attacks=attacks,
            colors=card_colors,
            max_copies=max_copies,
            swing=_SWING_SOFT,
            castable_any_color=free_spell,
        )
        log.debug(
            "_build_promoted_candidates: promoted %r → attacks=%s, colors=%s, max_copies=%d, free=%s",
            card_name, sorted(attacks), sorted(card_colors), max_copies, free_spell,
        )

    return promoted, warnings


# ---------------------------------------------------------------------------
# Unit 2: CoverageModel + _build_coverage_model
# ---------------------------------------------------------------------------

@dataclass
class CoverageModel:
    """Abstraction shared by both solvers.

    ``element_weight``: element id → weight (archetype IDs + "_hate:<k>" pseudo-elements).
    ``candidate_covers``: card name → frozenset of element ids it covers.
    ``candidate_meta``: card name → HoserCard (for max_copies lookups).
    ``warnings``: any issues encountered during construction.
    """

    element_weight: dict[str, float]
    candidate_covers: dict[str, frozenset[str]]
    candidate_meta: dict[str, HoserCard]
    warnings: tuple[str, ...]


def _build_coverage_model(
    field: FieldDistribution,
    archetype_tags: dict[str, frozenset[str]],
    deck_colors: frozenset[str],
    deck_tags: frozenset[str],
    *,
    catalog: Optional[dict[str, HoserCard]] = None,
    matchup_pressure: Optional[dict[str, float]] = None,
    anti_synergy_signals: "DeckAntiSynergySignals | None" = None,
    empirical_pool: "frozenset[str] | None" = None,
    promoted_candidates: "dict[str, HoserCard] | None" = None,
    card_swing_overrides: "dict[str, float] | None" = None,
) -> CoverageModel:
    """Build the coverage model: elements with weights + color-prefiltered candidates.

    Elements = (archetype, tag) pairs (weight = share × best_swing_for_that_specific_tag)
             + anti-hate pseudo-elements ``"_hate:<k>"`` for each vulnerability tag the
               deck carries, weighted by the field share of archetypes that are interactive
               (i.e., carry the tag themselves or have interaction) and can plausibly bring
               hate for tag k.

    Using (archetype, tag) elements rather than flat archetypes prevents soft hosers from
    capturing the weight of dedicated-hate tags they don't attack.  A hoser covering only
    tag X of a multi-tag archetype earns only the weight tied to that tag, not the full
    best-swing weight.

    Color pre-filter: drop catalog hosers whose required colors are not a subset of
    ``deck_colors`` (colorless/empty-color hosers are always allowed).  Cards with
    ``castable_any_color=True`` bypass the filter entirely (Phyrexian mana / free activations).

    Anti-hate (Fix 5): pseudo-element weight = Σ field_share(a) over archetypes that are
    NOT tagged low-interaction (conservative proxy for "can bring interactive sideboard
    cards") × the _SWING_SOFT constant.  Each counter-hoser covers only the hate
    pseudo-elements for the deck-vulnerability tags that interactive field archetypes
    actually care about — not every tag indiscriminately.

    Anti-synergy filter (feature-archetype-empirical-recommendations):
    When ``anti_synergy_signals`` is not None, catalog candidates whose name appears in
    ``_ANTI_SYNERGY_MAP`` and whose signal fires for this deck are dropped before coverage
    computation.  Gated-additive: ``anti_synergy_signals=None`` → no-op (byte-identical to
    pre-feature for callers that don't supply deck composition).

    Empirical pool filter (feature-archetype-empirical-recommendations):
    When ``empirical_pool`` is not None, catalog candidates NOT in the pool are dropped.
    Gated-additive: ``empirical_pool=None`` → no-op.

    Empirical pool promotion (fix-sideboard-surface-field-staples):
    When ``promoted_candidates`` is not None, those HoserCard entries are ADDED to the
    candidate universe alongside the (already-filtered) catalog cards.  Color pre-filter,
    anti-synergy filter, and element-coverage computation all apply equally.
    Gated-additive: ``promoted_candidates=None`` → no-op (byte-identical to pre-fix for
    callers that don't supply the promotion dict).

    Data-informed swing overrides (feature-empirical-sideboard-swings):
    When ``card_swing_overrides`` is not None, it maps card name → data-informed swing proxy
    derived from ``empirical_swing_proxy`` (presence-correlational per-card×matchup lift).
    For each card with an override, its override value is used instead of its catalog swing
    when computing ``best_swing_for_tag``.  Where data is thin (not in overrides), the
    catalog constant + caveat is retained.  Gated-additive: ``card_swing_overrides=None``
    → no-op (byte-identical to pre-feature for callers without card-value data).
    """
    if catalog is None:
        catalog = HOSER_CATALOG

    warnings: list[str] = []

    # --- Step 1: Identify best swing per tag across the full catalog + promoted candidates ---
    # Computed globally (not per-deck-color) so element weights reflect the best
    # *theoretical* swing for that tag; color filtering happens in candidate_covers.
    # Promoted candidates are included here so new tags they cover can seed element weights.
    # Data-informed swing overrides (feature-empirical-sideboard-swings): when provided,
    # a card's override swing (presence-correlational proxy, gate-cleared) replaces its
    # catalog swing in this computation.  Thin-data cards retain the catalog constant.
    best_swing_for_tag: dict[str, float] = {}
    _all_hosers_for_swing = list(catalog.values())
    if promoted_candidates:
        _all_hosers_for_swing.extend(promoted_candidates.values())
    for hoser in _all_hosers_for_swing:
        for tag in hoser.attacks:
            if tag == "_hate":
                continue  # counter-hosers don't directly represent archetype swing
            # Use the data-informed override when available; otherwise use catalog swing.
            effective_swing = (
                card_swing_overrides[hoser.name]
                if card_swing_overrides and hoser.name in card_swing_overrides
                else hoser.swing
            )
            best_swing_for_tag[tag] = max(best_swing_for_tag.get(tag, 0.0), effective_swing)

    # --- Step 2: Build (archetype, tag) element weights ---
    # Each element is keyed as "<archetype>|<tag>" so a soft hoser covering only
    # tag X captures only the weight for that tag, not for tag Y of the same archetype.
    element_weight: dict[str, float] = {}
    # Track which element keys belong to each archetype (for coverage lookup below).
    _archetype_tag_keys: dict[str, set[str]] = {}  # archetype → set of element keys

    for archetype, share in field.shares.items():
        tags = archetype_tags.get(archetype, frozenset())
        archetype_element_keys: set[str] = set()
        any_covered = False
        for tag in tags:
            swing = best_swing_for_tag.get(tag, 0.0)
            if swing > 0.0:
                key = f"{archetype}|{tag}"
                element_weight[key] = share * swing
                archetype_element_keys.add(key)
                any_covered = True
        _archetype_tag_keys[archetype] = archetype_element_keys
        if not any_covered and share > 0.0:
            if not tags:
                warnings.append(
                    f"archetype '{archetype}' (share={share:.3f}) has no vulnerability tags "
                    "— no catalog hoser can cover it; weight=0"
                )
            else:
                warnings.append(
                    f"archetype '{archetype}' (share={share:.3f}, tags={sorted(tags)}) "
                    "has no catalog hoser for any of its tags; weight=0"
                )

    # --- Step 3: Anti-hate pseudo-elements (tied to specific deck-tag categories) ---
    # For each vulnerability tag k the DECK carries:
    #   • Only create a pseudo-element if some counter-hoser in the catalog attacks "_hate".
    #   • Weight = Σ field_share(a) for archetypes that are interactive (NOT "low-interaction")
    #     × _SWING_SOFT.  This models the field share that can plausibly bring hate for k.
    #   • Each counter-hoser (_hate attacker) covers only hate_keys for the deck-vulnerability
    #     tags whose hoser category the counter-hoser is actually relevant for.  Since all
    #     counter-hosers in the catalog are general interaction (Veil, Defense Grid, Carpet),
    #     they cover ALL deck-tag hate pseudo-elements — but the weight is now field-appropriate
    #     rather than the full field share.
    hate_elements_added: set[str] = set()
    counter_hosers_exist = any("_hate" in h.attacks for h in catalog.values())
    if deck_tags and counter_hosers_exist:
        # Interactive field share: archetypes NOT tagged "low-interaction"
        interactive_share = sum(
            share
            for archetype, share in field.shares.items()
            if "low-interaction" not in archetype_tags.get(archetype, frozenset())
            and share >= 0.01
        )
        for tag in deck_tags:
            hate_key = _HATE_ELEMENT_PREFIX + tag
            weight = interactive_share * _SWING_SOFT
            if weight >= _HATE_ELEMENT_MIN_WEIGHT:
                element_weight[hate_key] = weight
                hate_elements_added.add(tag)

    # --- Step 3b: Apply matchup_pressure multipliers to archetype element weights ---
    # When matchup_pressure is not None (i.e. per-card data cleared the gate for ≥1
    # opponent), we up-weight elements for archetypes where the maindeck performs poorly.
    # When matchup_pressure is None, this step is a no-op → byte-identical to pre-rework.
    if matchup_pressure is not None:
        for key in list(element_weight.keys()):
            if "|" not in key:
                continue  # skip anti-hate pseudo-elements
            arch = key.split("|", 1)[0]
            multiplier = matchup_pressure.get(arch, 1.0)
            if multiplier != 1.0:
                element_weight[key] = element_weight[key] * multiplier

    # --- Step 4: Color-prefiltered candidate hosers ---
    candidate_covers: dict[str, frozenset[str]] = {}
    candidate_meta: dict[str, HoserCard] = {}

    for card_name, hoser in catalog.items():
        # Empirical pool filter (gated-additive): when provided, drop cards not in the pool.
        # This grounds recommendations in what real archetype sideboards actually run.
        if empirical_pool is not None and card_name not in empirical_pool:
            log.debug(
                "_build_coverage_model: dropping %r — not in empirical archetype pool", card_name
            )
            continue

        # Anti-synergy filter (gated-additive): drop self-harming hosers.
        # e.g. Chalice into a 1-CMC-heavy deck, Back to Basics into a nonbasic manabase,
        # Defense Grid into a reactive counter deck.
        if is_anti_synergistic(card_name, anti_synergy_signals):
            log.debug(
                "_build_coverage_model: dropping %r — anti-synergistic with deck composition",
                card_name,
            )
            continue

        # Color pre-filter: hoser.colors must be subset of deck_colors.
        # Empty hoser.colors = colorless → always legal.
        # castable_any_color=True bypasses the filter (Phyrexian mana / free activations).
        if hoser.colors and not hoser.colors.issubset(deck_colors) and not hoser.castable_any_color:
            continue  # drop off-color hosers

        # Compute which elements this hoser covers.
        covered: set[str] = set()

        # Coverage for (archetype, tag) elements: this hoser covers an element key
        # "<archetype>|<tag>" only when the hoser's attacks include that specific tag.
        for archetype, tag_keys in _archetype_tag_keys.items():
            for key in tag_keys:
                # key format: "<archetype>|<tag>"
                tag_part = key.split("|", 1)[1]
                if tag_part in hoser.attacks:
                    covered.add(key)

        # Counter-hosers (attacks contains "_hate") cover anti-hate pseudo-elements.
        if "_hate" in hoser.attacks:
            for tag in hate_elements_added:
                hate_key = _HATE_ELEMENT_PREFIX + tag
                if hate_key in element_weight:
                    covered.add(hate_key)

        if covered:
            candidate_covers[card_name] = frozenset(covered)
            candidate_meta[card_name] = hoser

    # --- Step 4b: Promoted empirical candidates (gated-additive) ---
    # Cards from the empirical pool that were NOT in the catalog.  They bypass the
    # empirical-pool filter (they are already FROM the pool) but still go through the
    # color pre-filter and anti-synergy filter.
    if promoted_candidates:
        for card_name, hoser in promoted_candidates.items():
            # Anti-synergy filter applies to promoted cards too.
            if is_anti_synergistic(card_name, anti_synergy_signals):
                log.debug(
                    "_build_coverage_model: dropping promoted %r — anti-synergistic with deck",
                    card_name,
                )
                continue

            # Color pre-filter applies equally.
            if hoser.colors and not hoser.colors.issubset(deck_colors) and not hoser.castable_any_color:
                log.debug(
                    "_build_coverage_model: dropping promoted %r — off-color (%s not in %s)",
                    card_name, sorted(hoser.colors), sorted(deck_colors),
                )
                continue

            # Compute coverage exactly as for catalog cards.
            covered_promoted: set[str] = set()
            for archetype, tag_keys in _archetype_tag_keys.items():
                for key in tag_keys:
                    tag_part = key.split("|", 1)[1]
                    if tag_part in hoser.attacks:
                        covered_promoted.add(key)

            if "_hate" in hoser.attacks:
                for tag in hate_elements_added:
                    hate_key = _HATE_ELEMENT_PREFIX + tag
                    if hate_key in element_weight:
                        covered_promoted.add(hate_key)

            if covered_promoted:
                candidate_covers[card_name] = frozenset(covered_promoted)
                candidate_meta[card_name] = hoser
                log.debug(
                    "_build_coverage_model: admitted promoted %r covering %d elements",
                    card_name, len(covered_promoted),
                )
            else:
                log.debug(
                    "_build_coverage_model: promoted %r covers no live elements — skipped",
                    card_name,
                )

    return CoverageModel(
        element_weight=element_weight,
        candidate_covers=candidate_covers,
        candidate_meta=candidate_meta,
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Unit 3: PickTrace + _greedy_solve
# ---------------------------------------------------------------------------

@dataclass
class PickTrace:
    """A single greedy pick with its marginal gain and newly covered elements."""

    card: str
    marginal_gain: float
    newly_covered: frozenset[str]


def _greedy_solve(
    model: CoverageModel,
    *,
    budget: int,
    redundancy_strength: float = 0.0,
    tau: float = 0.0,
) -> tuple[dict[str, int], list[PickTrace]]:
    """Greedy saturating-coverage with diminishing-returns marginal gain.

    Each step picks the card maximizing Σ_e weight_e × (g(cov_e+1) − g(cov_e)) over the
    elements it covers, where cov_e is the current coverage count for element e and
    g(n) = 1−(1−p)^n is the saturating model (_COVERAGE_P = 0.5).

    Because the marginal gain is positive for every n (never zero), additional copies
    continue to earn diminishing-but-positive value, allowing the solver to fill the full
    budget rather than stopping after the first pass of binary coverage.

    ``max_copies`` is respected; halts only when budget is exhausted or every remaining
    candidate has zero marginal gain (degenerate model).

    Returns (card→copies, ordered_trace).
    """
    picks: dict[str, int] = {}          # card → copies picked so far
    trace: list[PickTrace] = []
    cov_counts: dict[str, int] = {}     # element → coverage count (number of answers so far)
    slots_remaining = budget

    while slots_remaining > 0:
        best_card: str | None = None
        best_gain: float = 0.0
        best_newly: frozenset[str] = frozenset()

        for card_name, element_ids in model.candidate_covers.items():
            current_copies = picks.get(card_name, 0)
            max_copies = model.candidate_meta[card_name].max_copies
            if current_copies >= max_copies:
                continue  # exhausted this card's copy limit

            # Marginal gain = Σ_e weight_e × (g(cov_e+1) − g(cov_e)) for each covered element.
            # With the saturating model this is always > 0, so redundant answers earn value.
            gain = 0.0
            for e in element_ids:
                w = model.element_weight.get(e, 0.0)
                if w > 0.0:
                    cov_e = cov_counts.get(e, 0)
                    gain += w * _marginal_g(cov_e + 1)

            # Per-card-copy redundancy penalty: the (current_copies+1)-th copy of THIS card
            # is worth less (or net-negative) than its raw coverage marginal. No-op when
            # redundancy_strength == 0.0 (byte-identical baseline).
            gain -= _redundancy_penalty(current_copies + 1, strength=redundancy_strength)

            if gain > best_gain or (
                gain == best_gain and gain > 0 and (best_card is None or card_name < best_card)
            ):
                best_gain = gain
                best_card = card_name
                best_newly = frozenset(e for e in element_ids if cov_counts.get(e, 0) == 0)

        if best_card is None or best_gain <= tau:
            # Natural-budget stop (dedicated-core): no card clears the per-slot floor τ.
            # τ is the opportunity cost of a dedicated slot — when the best remaining net
            # marginal (coverage − redundancy penalty) ≤ τ, stop rather than padding the
            # budget. τ == 0.0 (default) reproduces the prior "stop only at zero gain"
            # behavior exactly (gains are ≥0 by the argmax floor → == 0.0 and ≤ 0.0 coincide).
            break

        picks[best_card] = picks.get(best_card, 0) + 1
        # Increment coverage counts for all elements this card covers.
        for e in model.candidate_covers[best_card]:
            cov_counts[e] = cov_counts.get(e, 0) + 1
        trace.append(PickTrace(
            card=best_card,
            marginal_gain=best_gain,
            newly_covered=best_newly,
        ))
        slots_remaining -= 1

    return picks, trace


# ---------------------------------------------------------------------------
# Unit 4: ILP solver (PuLP/CBC)
# ---------------------------------------------------------------------------

class _ILPFailed(Exception):
    """Sentinel raised when the ILP cannot produce an Optimal solution."""
    pass


def _ilp_solve(model: CoverageModel, *, budget: int, redundancy_strength: float = 0.0, tau: float = 0.0) -> dict[str, int]:
    """Exact saturating-coverage ILP via PuLP/CBC with incremental y_a^t linearization.

    Formulation:
      Variables:
        x_c ∈ {0..max_copies} integer for each candidate card c.
        y_a^t ∈ {0,1} for element a and coverage level t = 1..T_a
            (T_a = min(sum of max_copies of covering cards, _ILP_T_CAP)).
      Objective:
        max Σ_{a,t} weight_a · (g(t)−g(t−1)) · y_a^t
      Constraints:
        Σ_c x_c ≤ budget                               (slot budget)
        x_c ≤ max_copies_c                              (copy cap)
        Σ_{t=1}^{T_a} y_a^t ≤ Σ_{c covers a} x_c      ∀a  (level t can only fire if an answer is picked)
        y_a^t ∈ {0,1}                                   (binary; monotone fill is automatic because
                                                         coefficients are decreasing so solver prefers
                                                         lower t first)

    The y_a^t monotone-fill property: since g(t)−g(t−1) > g(t+1)−g(t) (decreasing marginals),
    the solver will always prefer to fill y_a^1 before y_a^2, so explicit ordering constraints
    are unnecessary.

    Returns card→copies (only x_c > 0 entries).
    Raises _ILPFailed if CBC is unavailable or status is not Optimal.
    """
    try:
        import pulp
    except ImportError as exc:
        raise _ILPFailed("PuLP not installed") from exc

    # Cap on coverage levels per element: use the budget itself so the ILP can
    # allocate up to budget answers for any element.  The old hard cap of 4 caused
    # the ILP to under-fill the budget (12 vs 15 slots) on multi-copy models where
    # greedy correctly uses the uncapped g(n) objective.  With budget as the cap the
    # ILP objective matches the uncapped g(n) that greedy and _compute_covered_weight
    # use, and all three agree on the correct budget-filling behaviour.
    _ILP_T_CAP = budget

    def _safe(s: str) -> str:
        """Sanitize a string for use as a PuLP variable name."""
        return s.replace(" ", "_").replace(",", "").replace("'", "").replace("&", "").replace("|", "_").replace(":", "_").replace("-", "_")

    prob = pulp.LpProblem("sideboard_saturating_coverage", pulp.LpMaximize)

    # --- Decision variables: x_c for each candidate card ---
    x_vars: dict[str, pulp.LpVariable] = {}
    for card_name, hoser in model.candidate_meta.items():
        x_vars[card_name] = pulp.LpVariable(
            name=f"x_{_safe(card_name)}",
            lowBound=0,
            upBound=hoser.max_copies,
            cat="Integer",
        )

    # --- Per-copy redundancy penalty (epic-sideboard-core-and-hedge-concave-value) ---
    # Incremental copy vars z_c^k (the k-th copy of card c) with x_c = Σ_k z_c^k and
    # monotone fill z_c^k ≥ z_c^{k+1}; the objective subtracts penalty(k) for k≥2. Omitted
    # entirely when redundancy_strength == 0.0 → model byte-identical to the pre-feature ILP.
    penalty_terms: list = []
    if redundancy_strength > 0.0:
        for card_name, hoser in model.candidate_meta.items():
            mc = hoser.max_copies
            if mc < 1:
                continue
            z = {
                k: pulp.LpVariable(name=f"z_{_safe(card_name)}_k{k}", cat="Binary")
                for k in range(1, mc + 1)
            }
            prob += pulp.lpSum(z.values()) == x_vars[card_name], f"zlink_{_safe(card_name)}"
            for k in range(1, mc):
                prob += z[k] >= z[k + 1], f"zmono_{_safe(card_name)}_{k}"
            for k in range(2, mc + 1):
                pen = _redundancy_penalty(k, strength=redundancy_strength)
                if pen > 0.0:
                    penalty_terms.append(-pen * z[k])

    # --- Decision variables: y_a^t for each element a and level t ---
    # T_a = min(total possible answers for element a, _ILP_T_CAP)
    y_vars: dict[tuple[str, int], pulp.LpVariable] = {}
    elem_t_cap: dict[str, int] = {}

    for elem_id, weight in model.element_weight.items():
        # Max feasible answers = sum of max_copies of all cards covering this element
        max_answers = sum(
            model.candidate_meta[c].max_copies
            for c, elems in model.candidate_covers.items()
            if elem_id in elems and c in model.candidate_meta
        )
        t_cap = min(max_answers, _ILP_T_CAP)
        elem_t_cap[elem_id] = t_cap
        for t in range(1, t_cap + 1):
            y_vars[(elem_id, t)] = pulp.LpVariable(
                name=f"y_{_safe(elem_id)}_t{t}",
                cat="Binary",
            )

    # --- Objective: saturating coverage ---
    obj_terms = []
    for elem_id, weight in model.element_weight.items():
        t_cap = elem_t_cap.get(elem_id, 0)
        for t in range(1, t_cap + 1):
            coef = weight * _marginal_g(t)
            if coef > 0.0:
                obj_terms.append(coef * y_vars[(elem_id, t)])
    obj_terms.extend(penalty_terms)  # negative per-copy redundancy terms (empty when off)
    # Natural-budget τ (dedicated-core): a per-slot opportunity cost so the ILP only fills
    # a slot whose marginal coverage clears τ — mirrors the greedy stop, returns <budget at
    # the knee. τ == 0.0 (default) adds nothing → byte-identical to the pre-feature objective.
    if tau > 0.0:
        for card_name, x_var in x_vars.items():
            obj_terms.append(-tau * x_var)
    if obj_terms:
        prob += pulp.lpSum(obj_terms)
    else:
        prob += 0

    # --- Budget constraint ---
    prob += pulp.lpSum(x_vars.values()) <= budget, "budget"

    # --- Linking constraints: Σ_t y_a^t ≤ Σ_{c covers a} x_c ---
    for elem_id in model.element_weight:
        t_cap = elem_t_cap.get(elem_id, 0)
        if t_cap == 0:
            continue
        covering_cards = [
            x_vars[c]
            for c, elems in model.candidate_covers.items()
            if elem_id in elems and c in x_vars
        ]
        if covering_cards:
            prob += (
                pulp.lpSum(y_vars[(elem_id, t)] for t in range(1, t_cap + 1))
                <= pulp.lpSum(covering_cards),
                f"cov_{_safe(elem_id)}",
            )
        else:
            # No card covers this element → force all y_a^t = 0
            for t in range(1, t_cap + 1):
                prob += y_vars[(elem_id, t)] == 0, f"nocov_{_safe(elem_id)}_t{t}"

    # --- Solve ---
    try:
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
    except Exception as exc:
        raise _ILPFailed(f"PuLP solve exception: {exc}") from exc

    status = pulp.LpStatus.get(prob.status, "Unknown")
    if status != "Optimal":
        raise _ILPFailed(f"ILP status: {status}")

    # --- Extract solution ---
    result: dict[str, int] = {}
    for card_name, var in x_vars.items():
        val = var.value()
        if val is not None and val > 0.5:
            result[card_name] = int(round(val))

    return result


# ---------------------------------------------------------------------------
# Extension B: Per-matchup OUT/IN planner (maindeck-aware rework)
# ---------------------------------------------------------------------------

def _plan_matchups(
    con: duckdb.DuckDBPyConnection,
    deck_maindeck: dict[str, int],
    sideboard_15: dict[str, int],
    opp_values: dict[str, "_OppValues"],
    archetype: str | None,
    *,
    max_swaps: int = 4,
    lock_threshold: float = 0.65,
    since: str | None = None,
    until: str | None = None,
    catalog: Optional[dict[str, HoserCard]] = None,
    adaptive_windows: "dict[str, tuple[str | None, str | None]] | None" = None,
) -> dict[str, MatchupPlan]:
    """Build per-opponent OUT/IN swap plans for the maindeck.

    For each opponent in ``opp_values``:

    - If ``not cleared_gate``: returns a degraded MatchupPlan (no OUT/IN, post_board
      == maindeck, explanatory note).
    - If ``cleared_gate``: builds a real OUT/IN plan:
        - Locked core: maindeck cards run by ≥ lock_threshold of the archetype's decks
          (from card_frequencies) — never sided out.  When archetype is None all
          maindeck cards are flex (degraded locked-core protection, noted).
        - OUT candidates: (maindeck \\ locked) ranked ascending by matchup lift (most
          dead vs opponent first), only gate-clearing cards with lift ≤ 0, capped at
          max_swaps copies total.
        - IN candidates: sideboard_15 ranked descending by matchup lift, gate-clearing,
          lift > 0, capped at max_swaps copies total.
        - Pairs OUT[i] ↔ IN[i] up to min(available_out, available_in) copies.
        - Enforces legality: post_board sums to exactly 60; per-card copies ≤
          max(catalog max_copies, 4).  Illegal swaps are skipped (fewer swaps is
          always legal).
        - side_out and side_in must have equal total copies (a swap conserves 60).

    Returns dict[opponent -> MatchupPlan].
    """
    if catalog is None:
        catalog = HOSER_CATALOG

    # Max copies limit: prefer catalog, fall back to 4
    def _max_copies_for(card: str) -> int:
        if card in catalog:
            return max(catalog[card].max_copies, 4)
        return 4

    plans: dict[str, MatchupPlan] = {}

    # Build locked core once per archetype using the deck-archetype's own adaptive window.
    # When adaptive_windows is provided, use the deck-archetype's own window (not an
    # opponent's window) — the locked core describes the deck's identity, not a matchup.
    locked_core: frozenset[str] = frozenset()
    lock_note = ""
    arch_since = since
    arch_until = until
    if archetype is not None and adaptive_windows is not None:
        # Use the deck-archetype's own window (keyed by archetype itself, if present)
        arch_win = adaptive_windows.get(archetype)
        if arch_win is not None:
            arch_since, arch_until = arch_win
    if archetype is not None:
        try:
            from legacy_engine.generation.consensus import card_frequencies
            freqs = card_frequencies(con, archetype, board="main", since=arch_since, until=arch_until)
            locked_core = frozenset(
                cf.name for cf in freqs if cf.inclusion_pct >= lock_threshold
            )
        except Exception as exc:
            log.debug("_plan_matchups: card_frequencies failed: %s", exc)
            locked_core = frozenset()
            lock_note = f" (locked-core unavailable: {exc})"
    else:
        lock_note = " (archetype=None — all maindeck cards are flex; locked-core protection skipped)"

    for opp, ov in opp_values.items():
        if not ov.cleared_gate:
            # Build an honest degraded note: name the adaptive window if one was used,
            # so the user knows the pooling was attempted and how thin the window still is.
            if adaptive_windows is not None and opp in adaptive_windows:
                opp_win = adaptive_windows[opp]
                since_label = opp_win[0] or "full-corpus"
                note = (
                    f"even pooling to {since_label}, the {opp} matchup is thin "
                    f"(n<gate threshold) — guidance is reasoning-based, not data-derived"
                )
            else:
                note = (
                    f"thin data (n < gate threshold) for {opp} — "
                    "no per-matchup plan; rely on the maindeck-aware 15 composition"
                )
            plans[opp] = MatchupPlan(
                opponent=opp,
                side_out={},
                side_in={},
                post_board=dict(deck_maindeck),
                n_basis=0,
                tier="speculative",
                degraded=True,
                note=note,
            )
            continue

        # ── Compute OUT candidates ─────────────────────────────────────────
        # Only flex maindeck cards (not in locked_core) that clear the gate (tier in
        # _VALUE_GATE) and have lift ≤ 0 (genuinely weak vs opponent).
        out_candidates: list[tuple[str, float, int, str]] = []  # (card, lift, copies, tier)
        for card, cv in ov.maindeck.items():
            if card in locked_core:
                continue
            if cv.tier not in _VALUE_GATE:
                continue
            if cv.lift > 0:
                continue  # positive lift → keep it in
            copies_available = deck_maindeck.get(card, 0)
            if copies_available <= 0:
                continue
            out_candidates.append((card, cv.lift, copies_available, cv.tier))

        # Sort ascending by lift (most dead first); tie-break by card name for stability
        out_candidates.sort(key=lambda x: (x[1], x[0]))

        # ── Compute IN candidates ──────────────────────────────────────────
        # Sideboard_15 cards that clear the gate and have lift > 0 vs this opponent.
        in_candidates: list[tuple[str, float, int, str]] = []  # (card, lift, copies, tier)
        for card, cv in ov.side.items():
            if cv.tier not in _VALUE_GATE:
                continue
            if cv.lift <= 0:
                continue
            copies_available = sideboard_15.get(card, 0)
            if copies_available <= 0:
                continue
            in_candidates.append((card, cv.lift, copies_available, cv.tier))

        # Sort descending by lift (best first)
        in_candidates.sort(key=lambda x: (-x[1], x[0]))

        # ── Pair OUT ↔ IN up to max_swaps total copies ────────────────────
        side_out: dict[str, int] = {}
        side_in: dict[str, int] = {}
        swaps_done = 0

        out_iter = iter(out_candidates)
        in_iter = iter(in_candidates)

        out_card, _out_lift, out_avail, _out_tier = None, 0.0, 0, "speculative"
        in_card, _in_lift, in_avail, _in_tier = None, 0.0, 0, "speculative"
        out_exhausted = in_exhausted = False

        def _next_out() -> bool:
            nonlocal out_card, _out_lift, out_avail, _out_tier, out_exhausted
            try:
                out_card, _out_lift, out_avail, _out_tier = next(out_iter)
                return True
            except StopIteration:
                out_exhausted = True
                return False

        def _next_in() -> bool:
            nonlocal in_card, _in_lift, in_avail, _in_tier, in_exhausted
            try:
                in_card, _in_lift, in_avail, _in_tier = next(in_iter)
                return True
            except StopIteration:
                in_exhausted = True
                return False

        if not _next_out():
            out_exhausted = True
        if not _next_in():
            in_exhausted = True

        while swaps_done < max_swaps and not out_exhausted and not in_exhausted:
            # Try one copy of out_card ↔ one copy of in_card
            # Legality check: post_board for this card must not exceed max_copies
            post_in_count = (deck_maindeck.get(in_card, 0)
                             + side_in.get(in_card, 0)
                             - side_out.get(in_card, 0))
            if post_in_count + 1 > _max_copies_for(in_card):
                # Skip this IN candidate
                if not _next_in():
                    break
                continue

            # Also check out_card is still in the tentative post_board
            post_out_count = (deck_maindeck.get(out_card, 0)
                              - side_out.get(out_card, 0))
            if post_out_count <= 0:
                # Already used all copies of this out_card
                if not _next_out():
                    break
                continue

            # Execute one copy swap
            side_out[out_card] = side_out.get(out_card, 0) + 1
            side_in[in_card] = side_in.get(in_card, 0) + 1
            swaps_done += 1

            # Advance iterators when a card's copies are exhausted
            out_avail -= 1
            if out_avail <= 0 or side_out.get(out_card, 0) >= deck_maindeck.get(out_card, 0):
                if not _next_out():
                    out_exhausted = True

            in_avail -= 1
            if in_avail <= 0 or side_in.get(in_card, 0) >= sideboard_15.get(in_card, 0):
                if not _next_in():
                    in_exhausted = True

        # ── Tally swaps ──────────────────────────────────────────────────────
        # Since each swap removes one and adds one, total = sum(deck_maindeck.values()) always.
        out_total = sum(side_out.values())
        # Invariant: each swap removes one and adds one, so out_total == sum(side_in.values())
        # by construction. post_board is rebuilt independently from side_out/side_in,
        # so it stays correct regardless.

        # Build post_board
        post_board = dict(deck_maindeck)
        for card, copies in side_out.items():
            post_board[card] = post_board.get(card, 0) - copies
            if post_board[card] <= 0:
                del post_board[card]
        for card, copies in side_in.items():
            post_board[card] = post_board.get(card, 0) + copies

        # Determine n_basis and tier from the cells used
        cells_used = (
            [ov.maindeck[c] for c in side_out if c in ov.maindeck]
            + [ov.side[c] for c in side_in if c in ov.side]
        )
        if cells_used:
            n_basis = min(cv.n for cv in cells_used)
            # Weakest tier = tier corresponding to n_basis
            from legacy_engine.confidence import tier_for_sample
            tier = tier_for_sample(n_basis)
        else:
            n_basis = 0
            tier = "speculative"

        if out_total == 0:
            note = (
                f"vs {opp}: data cleared gate but no flex dead cards found "
                f"(or no high-lift sideboard IN candidates){lock_note}"
            )
            plans[opp] = MatchupPlan(
                opponent=opp,
                side_out={},
                side_in={},
                post_board=dict(deck_maindeck),
                n_basis=n_basis,
                tier=tier,
                degraded=False,
                note=note,
            )
        else:
            lock_str = f"; locked={sorted(locked_core)}" if locked_core else lock_note
            note = (
                f"vs {opp}: {out_total} swap(s); "
                f"tier={tier}, n_basis={n_basis}{lock_str}"
            )
            plans[opp] = MatchupPlan(
                opponent=opp,
                side_out=dict(side_out),
                side_in=dict(side_in),
                post_board=post_board,
                n_basis=n_basis,
                tier=tier,
                degraded=False,
                note=note,
            )

    return plans


# ---------------------------------------------------------------------------
# Unit 5: ConsideringCard + _rank_considering_pool
# ---------------------------------------------------------------------------

# Maximum number of candidates to surface in the considering pool.
# Chosen 15 + considering up to 15 = ~30 total context (as specified).
_CONSIDERING_CAP = 15


@dataclass(frozen=True)
class ConsideringCard:
    """One entry in the "considering" (bubble) pool emitted by ``recommend_sideboard``.

    These are ranked candidates that the solver evaluated but did NOT select —
    the next-best cards by marginal coverage value that were just outside the
    chosen 15.  They represent flex options and meta-call alternatives.

    ``card``:           card name.
    ``marginal_gain``:  coverage-model marginal gain given the final solution's
                        coverage state (what the engine would earn by adding this
                        card next — the residual opportunity cost).
    ``covers_elements``: frozenset of element IDs (archetype|tag or _hate:tag) this
                        card covers that are not yet fully saturated by the solution.
    ``label``:          human-readable "why on bubble" string (coverage contribution
                        and value tier; e.g. "covers graveyard-reliant (Dredge 18%)").
    ``promoted``:       True when the card was promoted from the empirical pool (not
                        in the hand-curated catalog) — indicates best-effort attribution.
    """

    card: str
    marginal_gain: float
    covers_elements: frozenset[str]
    label: str
    promoted: bool


def _rank_considering_pool(
    model: CoverageModel,
    final_cards: dict[str, int],
    *,
    cap: int = _CONSIDERING_CAP,
    promoted_names: "frozenset[str] | None" = None,
) -> "list[ConsideringCard]":
    """Rank candidates NOT in the final 15 by residual marginal coverage gain.

    Computes the coverage state from ``final_cards``, then for every candidate
    not yet at max_copies evaluates its marginal gain given that state.
    Returns the top-``cap`` candidates sorted by marginal_gain DESC, card_name ASC
    (deterministic tie-break).

    Pure function — no DB, no IO.  Satisfies the objective-search-split pattern
    (the heavy DB work is already done in recommend_sideboard; this is the pure loop).

    Parameters
    ----------
    model
        The CoverageModel used to solve for ``final_cards``.
    final_cards
        The chosen sideboard (card → copies).
    cap
        Maximum number of candidates to return (default ``_CONSIDERING_CAP`` = 15).
    promoted_names
        Set of card names that were promoted from the empirical pool (not in catalog).
        Used to set ``ConsideringCard.promoted``.

    Returns
    -------
    list[ConsideringCard]
        Ranked list of bubble candidates (may be shorter than ``cap`` if fewer
        candidates exist).
    """
    if promoted_names is None:
        promoted_names = frozenset()

    # Build coverage counts from final solution (element → copies covered).
    cov_counts: dict[str, int] = {}
    for card_name, copies in final_cards.items():
        for e in model.candidate_covers.get(card_name, frozenset()):
            cov_counts[e] = cov_counts.get(e, 0) + copies

    candidates: list[ConsideringCard] = []

    for card_name, element_ids in model.candidate_covers.items():
        current_copies = final_cards.get(card_name, 0)
        max_copies = model.candidate_meta[card_name].max_copies

        # Skip if already at max_copies (fully placed in the solution).
        if current_copies >= max_copies:
            continue

        # Compute residual marginal gain (as if we added one more copy).
        gain = 0.0
        residual_elements: set[str] = set()
        for e in element_ids:
            w = model.element_weight.get(e, 0.0)
            if w > 0.0:
                cov_e = cov_counts.get(e, 0)
                mg = _marginal_g(cov_e + 1)
                gain += w * mg
                if mg > 0.0:
                    residual_elements.add(e)

        if gain <= 0.0:
            continue  # no residual coverage value → skip

        # Build human-readable label for what this card covers.
        label = _considering_label(card_name, element_ids, model, cov_counts)

        candidates.append(ConsideringCard(
            card=card_name,
            marginal_gain=gain,
            covers_elements=frozenset(residual_elements),
            label=label,
            promoted=card_name in promoted_names,
        ))

    # Sort: marginal gain DESC, card name ASC (deterministic tie-break).
    candidates.sort(key=lambda c: (-c.marginal_gain, c.card))
    return candidates[:cap]


def _considering_label(
    card_name: str,
    element_ids: "frozenset[str]",
    model: CoverageModel,
    cov_counts: "dict[str, int]",
) -> str:
    """Build a concise label explaining why a card is on the considering bubble.

    Extracts the top 1–2 highest-weight uncovered (or under-covered) elements
    this card addresses and formats them as: "covers <tag> (<archetype>),
    <tag2>".

    Pure function — no DB.
    """
    # Collect (element_key, residual_weight) pairs for this card.
    element_gains: list[tuple[str, float]] = []
    for e in element_ids:
        w = model.element_weight.get(e, 0.0)
        if w <= 0.0:
            continue
        cov_e = cov_counts.get(e, 0)
        mg = _marginal_g(cov_e + 1)
        residual_w = w * mg
        if residual_w > 0.0:
            element_gains.append((e, residual_w))

    if not element_gains:
        return f"{card_name}: no uncovered elements (low residual)"

    # Sort by residual weight DESC to surface the most important coverage.
    element_gains.sort(key=lambda x: -x[1])

    parts: list[str] = []
    for e, _ in element_gains[:2]:
        if "|" in e:
            # Archetype|tag element — format as "tag (Archetype)"
            arch, tag = e.split("|", 1)
            parts.append(f"{tag} ({arch})")
        elif e.startswith("_hate:"):
            tag = e[len("_hate:"):]
            parts.append(f"anti-hate:{tag}")
        else:
            parts.append(e)

    return "covers " + ", ".join(parts)


# ---------------------------------------------------------------------------
# Unit 5: SideboardPackage + recommend_sideboard
# ---------------------------------------------------------------------------

@dataclass
class SideboardPackage:
    """Output of ``recommend_sideboard``.

    ``cards``: recommended card → copies (sum ≤ budget = 15 − reserved).
    ``trace``: greedy marginal-gain trace (always present, even when ILP is used).
    ``covered_weight``: Σ element_weight for covered elements (using the solution's picks).
    ``budget``: effective budget used (15 − reserved).
    ``reserved``: slots held for flex/maindeck-overlap (not assigned by solver).
    ``solver_used``: ``"ilp"`` or ``"greedy"``.
    ``field_source``: from the FieldDistribution.
    ``heuristic_note``: explicit label that swing magnitudes are curated estimates.
    ``warnings``: any issues from coverage model build or solver.

    New additive fields (all have defaults — existing constructors keep working):
    ``matchup_plans``: per-opponent OUT/IN plans (empty dict when no per-card data).
    ``value_informed``: True when ≥1 opponent cleared the per-card data gate.
    ``plan_window``: (since, until) window used for per-card data (both None = no data).
    ``plan_window_label``: human-readable label for the plan window (for CLI echo).
    ``plan_windows``: per-opponent adaptive window audit (opponent → (since, until)).
    """

    cards: dict[str, int]
    trace: list[PickTrace]
    covered_weight: float
    budget: int
    reserved: int
    solver_used: str
    field_source: str
    heuristic_note: str
    warnings: tuple[str, ...]
    # --- Additive fields (unit 4: maindeck-aware extension) ---
    matchup_plans: dict[str, MatchupPlan] = dc_field(default_factory=dict)
    value_informed: bool = False
    plan_window: tuple[str | None, str | None] = (None, None)
    # --- Additive fields (regime-windowing-consistency) ---
    plan_window_label: str = ""                              # "" = not set; "adaptive (per-opponent ban-aware)" in adaptive mode
    plan_windows: dict[str, tuple[str | None, str | None]] = dc_field(default_factory=dict)  # per-opponent audit
    # --- Additive fields (feature-collection-aware-engine) ---
    # owned: annotation for each recommended card (empty dict → not collection-aware).
    # collection_aware: True iff a CollectionView was supplied.
    # Gate: collection=None → owned={}, collection_aware=False → byte-identical to pre-feature.
    owned: "dict[str, object]" = dc_field(default_factory=dict)
    collection_aware: bool = False
    # --- Additive fields (feature-empirical-sideboard-swings) ---
    # swing_data_informed: True when ≥1 catalog card had its swing replaced by a
    #   presence-correlational proxy derived from gate-clearing per-card×matchup data.
    #   False → all swings are curated constants (heuristic_note applies fully).
    # swing_overrides_count: number of cards whose swing was data-informed.
    # Gate: no card-value data or all data thin → swing_data_informed=False →
    #   heuristic_note is the full note; byte-identical element weights to pre-feature.
    swing_data_informed: bool = False
    swing_overrides_count: int = 0
    # --- Additive fields (feature-considering-cards-pool) ---
    # considering: ranked bubble candidates NOT selected in the final 15, sorted by
    #   residual marginal coverage gain.  Always populated (up to _CONSIDERING_CAP ≈ 15).
    #   Empty tuple when there are no remaining candidates (degenerate / budget-filled model).
    #   Gated-additive: existing callers that don't use this field see no change in cards/trace.
    considering: "tuple[ConsideringCard, ...]" = dc_field(default_factory=tuple)
    # --- Additive fields (epic-sideboard-core-and-hedge-output-contract) ---
    # Honest-degrade output for the core+hedge solver. All None/empty in the forced-budget
    # baseline (redundancy_strength==0 AND tau==0) → byte-identical rendering for every
    # existing caller. Populated only when the new behavior is active.
    # natural_budget_count: total copies the dedicated core committed (the "natural budget",
    #   e.g. 7 of 15), or None in the forced-budget baseline.
    # marginal_curve: (cumulative copies, cumulative covered weight) after each greedy pick —
    #   the budget→coverage curve that exposes the knee.
    # uncovered_tail: (element_id, weight) for the highest-weight field elements the package
    #   does NOT answer, sorted desc — the honest "what you're leaving open".
    # insurance_cards: subset of ``cards`` the hedge added in flex slots (empty until the
    #   hedge feature lands; every other card is "commit" / dedicated core).
    natural_budget_count: int | None = None
    marginal_curve: tuple[tuple[int, float], ...] = dc_field(default_factory=tuple)
    uncovered_tail: tuple[tuple[str, float], ...] = dc_field(default_factory=tuple)
    insurance_cards: frozenset[str] = dc_field(default_factory=frozenset)


def _compute_covered_weight(cards: dict[str, int], model: CoverageModel) -> float:
    """Compute total saturating-coverage value of a set of picks.

    Uses the saturating model: Σ_e weight_e × g(cov_e) where cov_e = number of cards
    in ``cards`` that cover element e (accounting for copy counts).
    """
    cov_counts: dict[str, int] = {}
    for card_name, copies in cards.items():
        for e in model.candidate_covers.get(card_name, frozenset()):
            cov_counts[e] = cov_counts.get(e, 0) + copies
    return sum(
        model.element_weight.get(e, 0.0) * _g(n)
        for e, n in cov_counts.items()
        if e in model.element_weight
    )


def recommend_sideboard(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    deck_maindeck: dict[str, int],
    *,
    reserved: int = 0,
    solver: str = "ilp",
    catalog: Optional[dict[str, HoserCard]] = None,
    # New optional kwargs (Unit 4: maindeck-aware extension).
    # All have safe defaults so existing callers are unaffected.
    archetype: str | None = None,
    since: str | None = None,
    until: str | None = None,
    opponents: list[str] | None = None,
    max_swaps: int = 4,
    card_winrates=None,
    # Fix B: adaptive ban-aware per-opponent windows (regime-windowing-consistency).
    # When True and archetype is set, pool each opponent's card-value cells back to
    # max(valid_since[archetype], valid_since[opponent]) — mirrors build_adaptive_matrix.
    # When False (or archetype is None), falls back to the single uniform window path
    # (byte-identical to pre-feature for existing callers).
    adaptive: bool = True,
    # New optional kwarg (feature-collection-aware-engine).
    # Gated-additive: None → no-op (byte-identical to pre-feature for all existing callers).
    collection: "Optional[object]" = None,
    # Per-copy redundancy penalty strength (epic-sideboard-core-and-hedge-concave-value).
    # Gated-additive: 0.0 → no per-copy penalty → byte-identical to the forced-15 baseline.
    # The gating feature wires a CLI flag to this; the dedicated-core feature adds the τ stop.
    redundancy_strength: float = 0.0,
    # Natural-budget floor τ (epic-sideboard-core-and-hedge-dedicated-core): per-slot
    # opportunity cost — the solver stops committing dedicated cards once the best marginal
    # coverage ≤ τ, so the package may be FEWER than 15. Gated-additive: 0.0 → no stop →
    # byte-identical to the forced-15 baseline. The gating feature wires a CLI flag + default.
    tau: float = 0.0,
) -> SideboardPackage:
    """Recommend a 15-card sideboard via weighted max-coverage.

    Steps:
    1. Resolve deck colors via ``_load_deck_cards`` + ``compute_deck_colors``.
    2. Get deck's vulnerability tags via ``vulnerability_tags_for_deck``.
    3. Get per-archetype tags via ``field_vulnerability_tags``.
    NEW 2b. Build per-card matchup values (_field_matchup_values); derive matchup_pressure.
    4. Build the coverage model (elements, weights, color-prefiltered candidates).
    5. Solve with ILP (primary) or greedy (fallback / forced).
    6. Always compute the greedy trace (explainable per-card rationale).
    NEW 6b. Plan per-matchup OUT/IN swaps (_plan_matchups).
    7. Return a SideboardPackage with both results + new additive fields.

    ``solver="greedy"`` forces the greedy path (e.g. for testing or if CBC is unavailable).

    New optional kwargs (all default-safe):
    - ``archetype``: the deck's own archetype string (for locked-core computation).
    - ``since``/``until``: date window for per-card win-rate data.  When both are
      None the latest ban-regime window is used automatically.
    - ``opponents``: subset of field archetypes to plan for (None = top-8 by share).
    - ``max_swaps``: maximum copies to swap per matchup plan (default 4).

    On a rounds-less corpus all per-card gates fail → matchup_pressure=None →
    element weights are BYTE-IDENTICAL to the pre-rework model → existing tests green.
    """
    if catalog is None:
        catalog = HOSER_CATALOG

    budget = 15 - reserved
    if budget <= 0:
        log.warning("recommend_sideboard: reserved=%d leaves budget=%d ≤ 0; returning empty package", reserved, budget)
        return SideboardPackage(
            cards={},
            trace=[],
            covered_weight=0.0,
            budget=budget,
            reserved=reserved,
            solver_used="none",
            field_source=field.field_source,
            heuristic_note=_HEURISTIC_NOTE,
            warnings=("budget ≤ 0 — all slots reserved",),
            plan_window_label="",
            plan_windows={},
        )

    warnings: list[str] = []

    # --- Step 1: Deck colors ---
    cards_with_counts = _load_deck_cards(con, deck_maindeck)
    deck_card_objects = [card for card, _count in cards_with_counts]
    deck_colors_str = compute_deck_colors(deck_card_objects)
    deck_colors: frozenset[str] = frozenset(deck_colors_str) if deck_colors_str else frozenset()

    if not deck_colors:
        log.warning("recommend_sideboard: deck has no colors (colorless or empty deck) — only colorless hosers considered")
        warnings.append("deck has no detected colors; only colorless hosers included")

    # --- Step 2: Deck vulnerability tags ---
    deck_tags = vulnerability_tags_for_deck(con, deck_maindeck)

    # --- Step 3: Field archetype tags ---
    archetype_tags = field_vulnerability_tags(con, field)

    # --- Step 2b (setup): Resolve effective window ---
    # Done early so Steps 3c and later can all use eff_since/eff_until.
    eff_since = since
    eff_until = until
    if eff_since is None and eff_until is None:
        try:
            from legacy_engine.generation.consensus import _latest_regime_window
            eff_since, eff_until = _latest_regime_window()
        except Exception:
            pass  # keep both None (open window)

    # --- Step 3b: Anti-synergy signals (NEW, gated-additive) ---
    # Computed from the resolved card objects (already available from Step 1).
    # None when the deck is empty — that signals no-op to _build_coverage_model.
    anti_synergy_signals: "DeckAntiSynergySignals | None" = None
    if cards_with_counts:
        anti_synergy_signals = compute_deck_anti_synergy_signals(cards_with_counts)
        if anti_synergy_signals.low_curve:
            log.debug("recommend_sideboard: low-curve deck detected → Chalice of the Void filtered")
        if anti_synergy_signals.nonbasic_heavy:
            log.debug("recommend_sideboard: nonbasic-heavy deck detected → Back to Basics filtered")
        if anti_synergy_signals.reactive:
            log.debug("recommend_sideboard: reactive deck detected → Defense Grid filtered")

    # --- Step 3c: Empirical archetype sideboard pool (NEW, gated-additive) ---
    # When archetype is known, restrict the catalog to cards real lists actually run,
    # AND promote high-adoption pool cards that are absent from the catalog.
    # None when archetype is unknown, no in-regime sideboard data, or pool would be empty.
    empirical_pool: "frozenset[str] | None" = None
    promoted_candidates: "dict[str, HoserCard] | None" = None
    _empirical_freq_map: "dict[str, int]" = {}  # card → modal_count (for promoted max_copies)
    if archetype is not None:
        _pool_result = _empirical_sideboard_pool(
            con, archetype, since=eff_since, until=eff_until
        )
        if _pool_result is not None:
            empirical_pool, _empirical_freq_map = _pool_result

        if empirical_pool is not None:
            log.debug(
                "recommend_sideboard: empirical pool for %r has %d cards (min_adoption=%.0f%%)",
                archetype, len(empirical_pool), _EMPIRICAL_POOL_MIN_ADOPTION * 100,
            )
            # --- Step 3d: Promote pool cards not in the catalog (gated-additive) ---
            # Cards in the empirical pool but absent from the catalog get promoted into the
            # candidate set with best-effort coverage attribution.
            _promo_dict, _promo_warnings = _build_promoted_candidates(
                empirical_pool, catalog, _empirical_freq_map, con
            )
            if _promo_dict:
                promoted_candidates = _promo_dict
                warnings.extend(_promo_warnings)
                log.debug(
                    "recommend_sideboard: %d empirical cards promoted from pool (not in catalog): %s",
                    len(_promo_dict), sorted(_promo_dict.keys()),
                )
        else:
            log.debug(
                "recommend_sideboard: no empirical sideboard pool for %r (thin/no data) — "
                "skipping pool filter + promotion", archetype,
            )

    # --- Step 2b: Per-card matchup values + matchup_pressure (NEW, gated) ---
    # We don't have the final_cards yet; use empty sideboard for the value adapter call.
    # After solving we'll rebuild opp_values with the real 15.  For the pressure pass
    # we only need the maindeck values (used to derive the deficit), so this is correct.
    opp_values_pre: dict[str, _OppValues] = {}
    matchup_pressure: Optional[dict[str, float]] = None
    any_gate_cleared = False

    # eff_since/eff_until already computed above (Step 2b setup).

    plan_window: tuple[str | None, str | None] = (eff_since, eff_until)
    plan_window_label: str = ""
    computed_adaptive_windows: dict[str, tuple[str | None, str | None]] | None = None

    # Fix B: build per-opponent adaptive windows (ban-aware, mirrors build_adaptive_matrix).
    # Pool each opponent's window back to max(valid_since[deck_arch], valid_since[opp]).
    # Only computed when:
    #   - adaptive=True and archetype is set, AND
    #   - no explicit since/until was passed by the caller (same rule as resolve_advisory_window:
    #     default is adaptive; explicit flags = uniform request).
    # This preserves byte-identical behavior for all existing callers that pass since/until.
    # Compute the top-k opponents ONCE so both _field_matchup_values passes and the
    # adaptive-window resolution use the same set (prevents window/opponent drift).
    _top_opponents: list[str] | None = None
    _top_k = 8  # must match _field_matchup_values default

    # Use the ORIGINAL since/until args (before regime-window defaulting) to decide whether
    # the caller explicitly requested a specific window.
    _caller_explicit_window = (since is not None) or (until is not None)
    _use_adaptive = adaptive and archetype is not None and not _caller_explicit_window
    if _use_adaptive:
        _top_opponents = [
            arch
            for arch, _ in sorted(field.shares.items(), key=lambda kv: kv[1], reverse=True)
        ][:_top_k]
        try:
            from legacy_engine.analytics.affectedness import archetype_valid_since as _avs
            all_archetypes_to_check = list({archetype, *_top_opponents})
            valid_since_map = _avs(con, all_archetypes_to_check)
            deck_valid_since = valid_since_map.get(archetype)

            computed_adaptive_windows = {}
            for opp in _top_opponents:
                opp_valid_since = valid_since_map.get(opp)
                # Pool to max(valid_since[deck_arch], valid_since[opp])
                both = [s for s in (deck_valid_since, opp_valid_since) if s is not None]
                opp_since = max(both) if both else None
                computed_adaptive_windows[opp] = (opp_since, None)
            # Also record deck-archetype's own window (for locked-core in _plan_matchups)
            if deck_valid_since is not None:
                computed_adaptive_windows[archetype] = (deck_valid_since, None)

            plan_window = (None, None)  # no single uniform window in adaptive mode
            plan_window_label = "adaptive (per-opponent ban-aware)"
            log.debug(
                "recommend_sideboard: adaptive windows for %d opponents (deck_arch=%s, valid_since=%s)",
                len(_top_opponents), archetype, deck_valid_since,
            )
        except Exception as exc:
            log.debug(
                "recommend_sideboard: adaptive window resolution failed (%s); falling back to uniform",
                exc,
            )
            computed_adaptive_windows = None
            plan_window = (eff_since, eff_until)
            plan_window_label = ""

    # Compute the per-card win-rate aggregate ONCE (heavy full-corpus scan) and reuse it
    # across both _field_matchup_values passes below; callers (e.g. tune_deck) may inject one.
    # In adaptive mode the uniform aggregate is NOT used for per-opponent values (each opponent
    # uses its own window's aggregate via _field_matchup_values adaptive_windows param), but we
    # still compute it here as a fallback for the pressure pass when adaptive_windows fails.
    if card_winrates is None:
        try:
            from legacy_engine.analytics.match_results import compute_card_winrates
            card_winrates = compute_card_winrates(con, since=eff_since, until=eff_until)
        except Exception as exc:
            log.debug("recommend_sideboard: compute_card_winrates failed: %s", exc)
            card_winrates = None

    try:
        opp_values_pre = _field_matchup_values(
            con, field, deck_maindeck, {},
            since=eff_since, until=eff_until,
            # Pass card_winrates as a cache seed for both adaptive and uniform paths.
            # In adaptive mode it seeds the (eff_since, eff_until) entry, avoiding a redundant
            # scan when an opponent's adaptive window happens to equal the uniform fallback.
            card_winrates=card_winrates,
            adaptive_windows=computed_adaptive_windows,
            top_opponents=_top_opponents,
        )
    except Exception as exc:
        log.debug("recommend_sideboard: _field_matchup_values failed: %s", exc)
        opp_values_pre = {}

    # Derive matchup_pressure from pre-15 opp_values (maindeck values only).
    # pressure[arch] = 1 + MAX_PRESSURE * clamp01(deficit)
    # deficit = how far below 0 the mean maindeck lift vs opponent sits.
    # Only gate-clearing opponents get a multiplier > 1.0; others get 1.0.
    if opp_values_pre:
        pressure: dict[str, float] = {}
        for opp, ov in opp_values_pre.items():
            if not ov.cleared_gate:
                pressure[opp] = 1.0
                continue
            any_gate_cleared = True
            main_lifts = [cv.lift for cv in ov.maindeck.values() if cv.tier in _VALUE_GATE]
            if not main_lifts:
                pressure[opp] = 1.0
                continue
            mean_lift = sum(main_lifts) / len(main_lifts)
            # deficit = how negative the mean lift is; clamp to [0, 1]
            deficit = max(0.0, min(1.0, -mean_lift))
            pressure[opp] = 1.0 + _MAX_PRESSURE * deficit

        if any_gate_cleared:
            matchup_pressure = pressure
        # else: keep matchup_pressure as None → byte-identical model

    # --- Step 3e: Data-informed swing overrides (feature-empirical-sideboard-swings) ---
    # Where per-card×matchup data for SIDEBOARD catalog cards gates at ≥evolving tier,
    # replace the curated catalog swing with a presence-correlational proxy.
    #
    # HONESTY: this is NOT a before/after-board measurement — game-level data is not in
    # the corpus (rounds table stores only match-level aggregate scores).  This proxy
    # reflects how decks registering card X in the board fared vs archetype Y.  Thin
    # cells (n<30) retain the curated constant.
    #
    # GATING: only runs when card_winrates is available (rounds corpus) and any_gate_cleared
    # (at least one maindeck cell gated, confirming the corpus is non-trivial).  When no
    # data → card_swing_overrides=None → _build_coverage_model is byte-identical.
    card_swing_overrides: "dict[str, float] | None" = None
    _swing_data_informed = False
    _swing_overrides_count = 0

    if card_winrates is not None and any_gate_cleared and _top_opponents:
        from legacy_engine.analytics.card_value import card_values_vs
        # Query sideboard card values for each catalog card vs each top opponent.
        # We use the uniform window (card_winrates) rather than adaptive windows here
        # because: (a) adaptive windows are per-opponent and catalog-card swings are
        # global (not per-opponent); (b) using the pooled corpus maximises n for thin
        # sideboard cells, which is more honest (fewer speculative → evolving upgrades).
        catalog_card_names = list(catalog.keys())
        _override_map: dict[str, list[float]] = {}  # card → list of gate-clearing proxies

        for opp in _top_opponents:
            opp_share = field.shares.get(opp, 0.0)
            if opp_share < 0.01:
                continue  # skip negligible-share opponents to avoid noise
            try:
                side_values = card_values_vs(
                    card_winrates, catalog_card_names, "side", opp, gate=_VALUE_GATE
                )
            except Exception as exc:
                log.debug(
                    "recommend_sideboard: card_values_vs (side) failed for %r: %s", opp, exc
                )
                continue

            for card_name, cv in side_values.items():
                proxy = empirical_swing_proxy(cv)
                if proxy is not None:
                    _override_map.setdefault(card_name, []).append(proxy)

        if _override_map:
            # For each card, take the max proxy across matchups (strongest data-informed signal).
            # Bounded by catalog swing range constraints and _EMPIRICAL_SWING_CAP (already
            # applied in empirical_swing_proxy).
            overrides: dict[str, float] = {}
            for card_name, proxies in _override_map.items():
                best_proxy = max(proxies)
                cat_swing = catalog[card_name].swing if card_name in catalog else _SWING_SOFT
                # Only use the proxy if it differs from the catalog swing by more than noise.
                # We never suppress a card that the catalog rates highly — use max(proxy, catalog).
                # This is intentionally conservative: the proxy can raise the effective swing
                # but catalog expertise is preserved as a floor.
                effective = max(best_proxy, cat_swing)
                if abs(effective - cat_swing) > _EMPIRICAL_SWING_MIN_LIFT:
                    overrides[card_name] = effective

            if overrides:
                card_swing_overrides = overrides
                _swing_data_informed = True
                _swing_overrides_count = len(overrides)
                log.debug(
                    "recommend_sideboard: data-informed swing overrides for %d catalog cards "
                    "(presence-correlational proxy, NOT before/after-board): %s",
                    _swing_overrides_count,
                    {k: f"{v:.3f}" for k, v in sorted(overrides.items())},
                )

    # --- Step 4: Build coverage model ---
    model = _build_coverage_model(
        field,
        archetype_tags,
        deck_colors,
        deck_tags,
        catalog=catalog,
        matchup_pressure=matchup_pressure,
        anti_synergy_signals=anti_synergy_signals,
        empirical_pool=empirical_pool,
        promoted_candidates=promoted_candidates,
        card_swing_overrides=card_swing_overrides,
    )
    warnings.extend(model.warnings)

    if not model.candidate_covers:
        warnings.append("no catalog hosers are castable in this deck's colors — returning empty sideboard")
        return SideboardPackage(
            cards={},
            trace=[],
            covered_weight=0.0,
            budget=budget,
            reserved=reserved,
            solver_used="none",
            field_source=field.field_source,
            heuristic_note=_DATA_INFORMED_NOTE if _swing_data_informed else _HEURISTIC_NOTE,
            warnings=tuple(warnings),
            value_informed=any_gate_cleared,
            plan_window=plan_window,
            plan_window_label=plan_window_label,
            plan_windows=computed_adaptive_windows if computed_adaptive_windows is not None else {},
            owned={},
            collection_aware=collection is not None,
            swing_data_informed=_swing_data_informed,
            swing_overrides_count=_swing_overrides_count,
        )

    # --- Step 5 + 6: Solve and always compute greedy trace ---
    solver_used = "greedy"
    ilp_cards: dict[str, int] = {}

    if solver == "ilp":
        try:
            ilp_cards = _ilp_solve(model, budget=budget, redundancy_strength=redundancy_strength, tau=tau)
            solver_used = "ilp"
        except _ILPFailed as exc:
            log.warning("recommend_sideboard: ILP failed (%s); falling back to greedy", exc)
            warnings.append(f"ILP solver failed ({exc}); using greedy fallback")
            solver_used = "greedy"
        except Exception as exc:
            log.warning("recommend_sideboard: unexpected ILP error (%s); falling back to greedy", exc)
            warnings.append(f"ILP solver error ({exc}); using greedy fallback")
            solver_used = "greedy"

    # Always compute greedy trace (explainability rationale)
    greedy_cards, greedy_trace = _greedy_solve(model, budget=budget, redundancy_strength=redundancy_strength, tau=tau)

    # Choose final cards based on solver
    final_cards = ilp_cards if solver_used == "ilp" else greedy_cards

    # Compute covered weight for the final solution
    cov_weight = _compute_covered_weight(final_cards, model)

    # --- Step 6b: Per-matchup OUT/IN plans (NEW, gated) ---
    matchup_plans: dict[str, MatchupPlan] = {}
    if any_gate_cleared and final_cards:
        # Re-build opp_values with the real 15 so the planner has correct side values.
        try:
            opp_values_final = _field_matchup_values(
                con, field, deck_maindeck, final_cards,
                since=eff_since, until=eff_until,
                card_winrates=card_winrates,
                adaptive_windows=computed_adaptive_windows,
                top_opponents=_top_opponents,
            )
            # If caller restricted to specific opponents, filter here.
            if opponents is not None:
                opp_values_final = {
                    k: v for k, v in opp_values_final.items() if k in opponents
                }
            matchup_plans = _plan_matchups(
                con, deck_maindeck, final_cards, opp_values_final, archetype,
                max_swaps=max_swaps,
                since=eff_since,
                until=eff_until,
                catalog=catalog,
                adaptive_windows=computed_adaptive_windows,
            )
        except Exception as exc:
            log.warning("recommend_sideboard: _plan_matchups failed: %s", exc)
            warnings.append(f"per-matchup plan failed: {exc}")

    # --- Step 6c: Considering pool (feature-considering-cards-pool, always-on additive) ---
    # Rank all model candidates not fully selected in final_cards by their residual
    # marginal gain given the final coverage state.  This is the "what would we pick
    # next" computation — the bubble of flex / meta-call alternatives the solver weighed.
    # Gated-additive: final_cards / model / trace are byte-identical to pre-feature.
    _promoted_names = frozenset(promoted_candidates.keys()) if promoted_candidates else frozenset()
    considering_pool = _rank_considering_pool(
        model, final_cards, promoted_names=_promoted_names
    )

    # --- Collection-aware annotation (gated-additive, feature-collection-aware-engine) ---
    # annotate_owned returns {} when collection is None → gate closed → byte-identical.
    from legacy_engine.advisory.collection import annotate_owned
    owned_annotations = annotate_owned(final_cards, collection)  # type: ignore[arg-type]

    # --- Step 6d: Output contract (epic-sideboard-core-and-hedge-output-contract) ---
    # Honest-degrade structured output. Populated ONLY when the core+hedge behavior is active
    # (redundancy_strength>0 or tau>0); the forced-budget baseline leaves these None/empty →
    # byte-identical to every existing caller's package + rendering.
    _natural_budget_count: int | None = None
    _marginal_curve: tuple[tuple[int, float], ...] = ()
    _uncovered_tail: tuple[tuple[str, float], ...] = ()
    if redundancy_strength > 0.0 or tau > 0.0:
        _natural_budget_count = sum(final_cards.values())
        # Cumulative net marginal value after each greedy pick — the budget→coverage curve
        # whose flattening shows the natural-budget knee (the explainable greedy trace).
        _cum = 0.0
        _curve: list[tuple[int, float]] = []
        for _i, _pick in enumerate(greedy_trace, start=1):
            _cum += _pick.marginal_gain
            _curve.append((_i, round(_cum, 4)))
        _marginal_curve = tuple(_curve)
        # Field elements the final solution does NOT answer, by weight (top 8) — the honest
        # "what you're leaving open" tail.
        _covered_elems: set[str] = set()
        for _c in final_cards:
            _covered_elems |= model.candidate_covers.get(_c, frozenset())
        _tail = sorted(
            ((e, w) for e, w in model.element_weight.items() if w > 0.0 and e not in _covered_elems),
            key=lambda kv: kv[1], reverse=True,
        )
        _uncovered_tail = tuple((e, round(w, 4)) for e, w in _tail[:8])

    return SideboardPackage(
        cards=final_cards,
        trace=greedy_trace,
        covered_weight=cov_weight,
        budget=budget,
        reserved=reserved,
        solver_used=solver_used,
        field_source=field.field_source,
        heuristic_note=_DATA_INFORMED_NOTE if _swing_data_informed else _HEURISTIC_NOTE,
        warnings=tuple(warnings),
        matchup_plans=matchup_plans,
        value_informed=any_gate_cleared,
        plan_window=plan_window,
        plan_window_label=plan_window_label,
        plan_windows=computed_adaptive_windows if computed_adaptive_windows is not None else {},
        owned=owned_annotations,
        collection_aware=collection is not None,
        swing_data_informed=_swing_data_informed,
        swing_overrides_count=_swing_overrides_count,
        considering=tuple(considering_pool),
        natural_budget_count=_natural_budget_count,
        marginal_curve=_marginal_curve,
        uncovered_tail=_uncovered_tail,
        insurance_cards=frozenset(),  # populated by the hedge-allocator feature (v1: all commit)
    )
