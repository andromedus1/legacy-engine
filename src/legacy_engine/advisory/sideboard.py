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

Breadth = true submodular marginal-gain (feature-sfv-breadth-objective): F(S) = Σ_e
weight_e·g(cov_e(S)) is a monotone submodular coverage function (g concave/non-decreasing
composed with the modular per-element coverage count).  A card's marginal value is therefore
the SUM of its marginal contribution to EVERY element it covers — F(S∪{c}) − F(S) = Σ_{e ∈
covers(c)} weight_e·(g(cov_e(S)+1) − g(cov_e(S))) — not any single element viewed in
isolation.  This is what credits a broad, flexible card (one answering many matchups at once,
e.g. Force of Negation post-attachment) with large marginal value, and is exactly what gives
greedy maximization its (1−1/e) approximation guarantee (docs/briefs/scorer-flexibility-
valuation.md §1).  ``_element_sum_marginal_gain`` is the ONE canonical implementation of this
sum; ``_greedy_solve``, ``_hedge_fill``, and ``_rank_considering_pool`` all call it so the
aggregation cannot silently diverge between them, and ``_ilp_solve``'s y_a^t linearization
encodes the identical per-element sum as a linear program (Σ_{a,t} weight_a·Δg(t)·y_a^t).  The
concave saturation g() itself stays a PER-ELEMENT diminishing-returns curve (multiple answers
to the same need still saturate — that axis is intentionally untouched); what changed is that
a card's SCORE now has one, explicit, tested home for aggregating ACROSS the distinct elements
it answers, rather than three independently-maintained inline copies of the same formula.

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
        - "counter target noncreature spell" (feature-sfv-attachments) additionally adds
          ``{"noncreature-reliant"}`` — the broad-interaction attachment axis so a free/soft
          anti-noncreature counter (Force of Negation, Spell Pierce) credits the WHOLE
          combo/control plurality it answers, not just the narrower combo/storm-reliant slice.
        - "counter target ... colorless spell" (feature-sfv-colorless-axis) additionally adds
          ``{"colorless-reliant"}`` — Consign to Memory / Ceremonious Rejection; an axis
          independent of the noncreature restriction above.
        - "target red/blue spell/permanent" or "if it's red/blue" (color-blast template
          shared by Pyroblast/Hydroblast/Blue|Red Elemental Blast) → ``{"plays-red"}`` /
          ``{"plays-blue"}``
        - "exile" + "graveyard" in oracle_text → ``{"graveyard-recursion"}``
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

Impact-modulated element weights + draw-probability copy-shaping
(feature-sb-field-weighted-scorer, Units B3+B4 — "replace the scoring core in place"):
  The decomposed ``advisory.impact`` model (centrality × symmetry × castability × draw_prob,
  see that module) modulates two, and only two, things in the existing ILP+greedy+τ+hedge
  machinery — everything else (swing sourcing, coverage saturation g(n), the natural-budget
  stop, the hedge allocator) is untouched:

  (B3) Element weight for an (archetype, tag) pair becomes
       ``field_share × swing × impact(best_hoser_for_tag, archetype, ...).score_without_draw_prob()``
       instead of plain ``field_share × swing``.  ``best_hoser_for_tag`` is the SAME hoser Step 1
       already selects for the tag's swing magnitude (swing sourcing is unchanged — impact only
       *modulates* the weight computed from it).  The impact call uses ``copies=1`` but the
       resulting ``draw_prob`` factor is DISCARDED (feature-sfv-weights) — the element weight
       asks "is there a good, castable, non-self-hosing answer", never "how likely am I to draw
       it"; draw-probability belongs exclusively to (B4)'s per-copy taper below, so applying it
       here too would double-count that same draw dimension AND (being a near-uniform ~0.4×
       factor) silently deflate the whole element-weight scale the natural-budget τ stop reads.
       Needs, per opponent archetype: that opponent's ``Linchpin`` list (``opp_linchpins``) and
       optionally its known maindeck composition (``opp_cards``, for ``cast_requires`` gating)
       — both precomputed ONCE by ``recommend_sideboard`` (objective-search-split:
       ``_field_opponent_linchpins`` does the DB work; ``_build_coverage_model`` stays pure) and
       threaded in via the new ``opponent_linchpins``/``opponent_cards`` params.  My deck's own
       colors/vulnerability-tags reuse the ``deck_colors``/``deck_tags`` params already threaded
       through for the anti-hate elements — no new "my-side" parameters needed.

       GATING: ``opponent_linchpins=None`` (the default) → every impact multiplier is 1.0 →
       element weights are BYTE-IDENTICAL to pre-impact (mirrors the ``matchup_pressure is None``
       precedent above).  ``recommend_sideboard`` only supplies a non-None dict when it found
       real linchpin data (derived from corpus composition OR a curated override) for at least
       one field archetype — a field of archetypes with no in-regime decks and no curated
       overrides degrades to the same None gate.

  (B4) The per-card-copy utility curve ``_U_REDUNDANCY_DEFAULT`` (consumed by ``_u_redundancy``
       / ``_redundancy_penalty``, unchanged otherwise) is now DERIVED from the
       ``advisory.impact.draw_probability`` hypergeometric marginal (``P(draw≥1 in a Bo3)``)
       instead of the generic curated ``(1.0, 0.55, 0.25, 0.10)`` constants — the Nth copy's
       utility is ``(draw_prob(N) − draw_prob(N−1))`` normalized so the 1st copy stays exactly
       1.0 (preserving ``_redundancy_penalty``'s ``penalty(1) == 0`` contract).  This is still a
       precomputed tuple of floats (LP-representable exactly like the curve it replaces); the
       ILP's ``z_c^k`` incremental-copy linearization and the greedy per-copy subtraction are
       untouched.  Still fully gated by ``redundancy_strength``/``tau`` == 0.0 → no-op.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field as dc_field, replace as _dc_replace
from pathlib import Path
from typing import Callable, Optional

import duckdb
from scipy.stats import beta as _beta_dist

import re

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.analytics.matchup import lookup_head_to_head
from legacy_engine.advisory.impact import ImpactBreakdown
from legacy_engine.advisory.impact import draw_probability as _draw_probability
from legacy_engine.advisory.impact import impact as _compute_impact
from legacy_engine.advisory.linchpins import Linchpin, linchpins_for_archetype
from legacy_engine.advisory.whattoplay import (
    field_vulnerability_tags,
    vulnerability_tags_for_deck,
    _load_deck_cards,
)
from legacy_engine.colors import compute_deck_colors
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

# Reused verbatim from `advise positioning`'s Dirichlet field-share uncertainty model
# (SSOT — see Unit B5's `_dirichlet_share_lower_bound` docstring below for why sideboard.py
# needs only the independent-marginal shortcut, not positioning's full joint-MC machinery).
# `compare.py` already establishes the precedent of importing these two private constants
# directly from `positioning` rather than re-declaring them.
from legacy_engine.advisory.positioning import _DEFAULT_RISK_QUANTILE, _DIRICHLET_GAMMA

# Alternative-cost ("pitch") spell detection — mirrors card_tags._FREE_SPELL_RE.
# Force of Will (CMC 5), Force of Negation (CMC 3), Daze (CMC 2), etc. are playable
# for free by pitching a card; their nominal CMC does not predict Chalice self-harm.
# Imported here as a module-level constant to avoid importing card_tags (circular risk).
_PITCH_SPELL_RE = re.compile(
    r"rather than pay this spell's mana cost"
    r"|without paying (?:its|their) mana costs?"
    r"|you may exile .+ rather than pay"
    r"|you may return .+ to its owner's hand rather than pay",
    re.IGNORECASE,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extension A: MatchupPlan + per-card matchup-value adapter (maindeck-aware rework)
# ---------------------------------------------------------------------------

# MatchupPlan.plan_status: the closed vocabulary naming WHY a plan looks the way it does.
# Two of the six mean "degraded" (see _DEGRADED_PLAN_STATUSES); the rest are real answers.
# "no-legal-flex" is structural (the eligible-slot pool is empty before any data is read);
# "no-dead-cards" / "no-in-candidates" / "no-legal-swap" are data answers over a live pool.
_PLAN_STATUS_PLANNED = "planned"
_PLAN_STATUS_THIN_DATA = "thin-data"
_PLAN_STATUS_NO_FLEX = "no-legal-flex"
_PLAN_STATUS_NO_DEAD_CARDS = "no-dead-cards"
_PLAN_STATUS_NO_IN = "no-in-candidates"
_PLAN_STATUS_NO_LEGAL_SWAP = "no-legal-swap"

_VALID_PLAN_STATUSES: frozenset[str] = frozenset({
    _PLAN_STATUS_PLANNED,
    _PLAN_STATUS_THIN_DATA,
    _PLAN_STATUS_NO_FLEX,
    _PLAN_STATUS_NO_DEAD_CARDS,
    _PLAN_STATUS_NO_IN,
    _PLAN_STATUS_NO_LEGAL_SWAP,
})

# Statuses that set degraded=True: no plan was produced for a reason that is not "the data
# says keep the 60".  Both suppress the magnitude and carry a named reason in ``note``.
_DEGRADED_PLAN_STATUSES: frozenset[str] = frozenset({
    _PLAN_STATUS_THIN_DATA,
    _PLAN_STATUS_NO_FLEX,
})

# Max declined candidates named inline in a plan note; the full list stays on the dataclass.
_SUPPRESSED_NOTE_CAP = 3


@dataclass(frozen=True)
class MatchupPlan:
    """Per-opponent OUT/IN swap plan for the maindeck.

    ``opponent``:   field archetype being planned for.
    ``side_out``:   maindeck cards to remove (card -> copies).
    ``side_in``:    sideboard cards to bring in (card -> copies).
    ``post_board``: the resulting 60 (maindeck − out + in).
    ``n_basis``:    min matchup-cell n backing this plan (0 when degraded).
    ``tier``:       weakest tier among the cells used ("speculative" when degraded).
    ``degraded``:   True when no plan was produced for a reason in ``_DEGRADED_PLAN_STATUSES``.
    ``note``:       human-readable explanation of the plan or degradation reason.

    ``plan_status``: token from ``_VALID_PLAN_STATUSES`` naming WHY the plan looks like this.
        Accepts ``None`` at construction (legacy 8-arg callers) and is then derived from
        ``degraded``; readers may treat it as always-``str``.
    ``out_suppressed`` / ``in_suppressed``: ``(card, lift, reason)`` for candidates the
        correlational signal favored but eligibility declined — divergence-as-diagnostic:
        an overruled signal stays visible instead of vanishing.  Empty for callers/paths
        that decline nothing.
    """

    opponent: str
    side_out: dict[str, int]
    side_in: dict[str, int]
    post_board: dict[str, int]
    n_basis: int
    tier: str
    degraded: bool
    note: str
    plan_status: str | None = None
    out_suppressed: tuple[tuple[str, float, str], ...] = ()
    in_suppressed: tuple[tuple[str, float, str], ...] = ()

    def __post_init__(self) -> None:
        if self.plan_status is None:
            derived = _PLAN_STATUS_THIN_DATA if self.degraded else _PLAN_STATUS_PLANNED
            object.__setattr__(self, "plan_status", derived)
        elif self.plan_status not in _VALID_PLAN_STATUSES:
            raise ValueError(
                f"MatchupPlan.plan_status {self.plan_status!r} not in "
                f"{sorted(_VALID_PLAN_STATUSES)}"
            )


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
# Per-opponent linchpins + composition (feature-sb-field-weighted-scorer-wiring, Unit B3)
# ---------------------------------------------------------------------------
# Objective-search-split: the DB work (resolving an archetype's in-regime maindeck
# composition to feed advisory.linchpins.linchpins_for_archetype) happens HERE, once per
# archetype, so _build_coverage_model's impact-modulated weight computation stays a pure,
# DB-free function fed a precomputed dict — exactly like matchup_pressure / empirical_pool /
# card_swing_overrides above.

def _archetype_linchpins_and_cards(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    since: str | None = None,
    until: str | None = None,
) -> "tuple[list[Linchpin], dict[str, int]]":
    """Resolve one archetype's linchpins + known maindeck composition from the corpus.

    ``card_frequencies`` (board="main") supplies inclusion_pct + modal_count for the
    archetype's real 60; ``_load_deck_cards`` resolves those names to ``Card`` objects so
    ``linchpins_for_archetype`` (pure — see linchpins.py) can classify roles/derive centrality.

    ``linchpins_for_archetype`` is called even when the corpus has NO in-regime decks for this
    archetype (empty ``cards_with_counts``/``inclusion_pct``) — it always merges in curated
    ``LINCHPIN_OVERRIDES`` regardless of derived candidates, so a well-known archetype (e.g.
    Painter) still yields its curated linchpins against a thin or synthetic corpus.

    Returns ``([], {})`` — an honest "no data", not a crash — on any DB/lookup failure, or
    when the archetype has neither corpus composition nor a curated override.  The second
    element (``dict[name, modal_count]``) doubles as the ``opp_cards`` composition signal for
    ``impact.castability_factor``'s ``cast_requires`` gating (e.g. "does this opponent run a
    Plains").
    """
    cards_with_counts: "list[tuple[Card, int]]" = []
    inclusion_pct: "dict[str, float]" = {}
    modal_counts: "dict[str, int]" = {}
    try:
        from legacy_engine.generation.consensus import card_frequencies
        freqs = card_frequencies(con, archetype, board="main", since=since, until=until)
        inclusion_pct = {cf.name: cf.inclusion_pct for cf in freqs}
        modal_counts = {cf.name: cf.modal_count for cf in freqs}
        if modal_counts:
            cards_with_counts = _load_deck_cards(con, modal_counts)
    except Exception as exc:
        log.debug(
            "_archetype_linchpins_and_cards: composition lookup failed for %r: %s", archetype, exc
        )

    try:
        linchpins = linchpins_for_archetype(archetype, cards_with_counts, inclusion_pct)
    except Exception as exc:
        log.debug(
            "_archetype_linchpins_and_cards: linchpins_for_archetype failed for %r: %s",
            archetype, exc,
        )
        linchpins = []

    return linchpins, modal_counts


def _field_opponent_linchpins(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    *,
    since: str | None = None,
    until: str | None = None,
) -> "tuple[dict[str, list[Linchpin]], dict[str, dict[str, int]]]":
    """``_archetype_linchpins_and_cards`` for every archetype in the field.

    Mirrors ``field_vulnerability_tags``'s one-query-per-archetype precedent.  Returns
    ``(linchpins_by_archetype, cards_by_archetype)`` — both keyed by every archetype in
    ``field.shares`` (values are ``[]``/``{}`` for archetypes with no data, never a missing key).
    """
    linchpins_by_arch: "dict[str, list[Linchpin]]" = {}
    cards_by_arch: "dict[str, dict[str, int]]" = {}
    for archetype in field.shares:
        lps, cards = _archetype_linchpins_and_cards(con, archetype, since=since, until=until)
        linchpins_by_arch[archetype] = lps
        cards_by_arch[archetype] = cards
    return linchpins_by_arch, cards_by_arch


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
# Canonical submodular marginal-gain aggregation (feature-sfv-breadth-objective)
# ---------------------------------------------------------------------------
# The epic's locked decision: "reformulate the coverage objective to true submodular
# marginal-gain — a card credited by its TOTAL marginal coverage across every element it
# answers" (docs/briefs/scorer-flexibility-valuation.md §1, distortion D1). Audited against
# the shipped code (post feature-sfv-attachments + feature-sfv-weights): the greedy solver,
# the hedge fill, and the considering-pool ranker ALREADY compute this quantity correctly —
# each independently summed weight_e·(g(cov_e+1)−g(cov_e)) over EVERY element a card covers,
# not a single element in isolation. That sum, evaluated at a given coverage state, IS the
# textbook submodular marginal gain of the objective F(S) = Σ_e weight_e·g(cov_e(S)); it is
# exactly what the ILP's y_a^t linearization (`_ilp_solve`) also encodes (Σ_{a,t}
# weight_a·Δg(t)·y_a^t sums the identical per-element marginal contributions), so greedy and
# ILP already optimize the SAME aggregate-breadth objective and both inherit the (1−1/e)
# greedy guarantee for it.
#
# What was missing was not the arithmetic but a single canonical, tested, documented home for
# it: before this feature, three call sites (`_greedy_solve`, `_hedge_fill`,
# `_rank_considering_pool`) each reimplemented the same "Σ over covered elements" loop inline.
# They agreed today, but nothing enforced that a future edit to just one of them couldn't
# silently re-fragment breadth credit (the D1 distortion, in latent/structural form — the risk
# the epic is guarding against, not a live bug found in this feature's audit). This function is
# now the ONE place that formula lives; every consumer that decides "how much is picking (or
# considering) one more copy of this card worth right now" calls it, so the aggregation cannot
# drift between them again.
def _element_sum_marginal_gain(
    model: "CoverageModel",
    card_name: str,
    cov_counts: "dict[str, int]",
    *,
    weights: "dict[str, float] | None" = None,
) -> float:
    """Submodular marginal gain of one more copy of ``card_name``: Σ over ALL elements it
    covers of ``weight_e · (g(cov_e+1) − g(cov_e))``.

    This is the whole-card aggregate, not a per-element score — a card covering many
    elements is credited by the SUM of its marginal contribution to each one (breadth is
    credited by construction, per submodular coverage theory; see the module docstring).

    ``cov_counts``: element id → current coverage count in the caller's in-progress solution.
    Read-only here; the caller applies the pick and increments coverage afterward.

    ``weights``: override ``model.element_weight`` (the hedge fill widens weights toward
    uniform before calling this — see ``_hedge_fill``). Defaults to the model's own weights.
    Elements with weight ≤ 0 (or absent from ``weights``) contribute nothing, matching every
    call site's existing filter.

    Pure function — no mutation, no DB. ``card_name`` need not be in ``model.candidate_covers``
    (returns 0.0), so callers don't need to pre-check membership.
    """
    active_weights = model.element_weight if weights is None else weights
    total = 0.0
    for element_id in model.candidate_covers.get(card_name, frozenset()):
        w = active_weights.get(element_id, 0.0)
        if w > 0.0:
            cov_e = cov_counts.get(element_id, 0)
            total += w * _marginal_g(cov_e + 1)
    return total


# ---------------------------------------------------------------------------
# Per-card-copy redundancy penalty (epic-sideboard-core-and-hedge-concave-value;
# curve replaced by the draw-probability marginal in feature-sb-field-weighted-scorer-wiring,
# Unit B4)
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
#
# Unit B4: derived from advisory.impact.draw_probability's hypergeometric marginal —
# P(draw>=1 copy in a Bo3) — instead of a hand-curated (1.0, 0.55, 0.25, 0.10) constant.
# u(k) = (draw_prob(k) - draw_prob(k-1)) / (draw_prob(1) - draw_prob(0)), normalized so
# u(1) == 1.0 exactly (preserving _redundancy_penalty's "penalty(1) == 0" contract). The
# hypergeometric marginal is concave/decreasing over 1..4 copies by construction (see
# draw_probability's docstring) — same SHAPE as the constant it replaces, now grounded in
# the mechanics-based draw model instead of a curated guess. Still a plain tuple of floats
# precomputed once at import time, so it stays a drop-in, LP-representable replacement:
# _u_redundancy / _redundancy_penalty / the ILP's z_c^k linearization are all unchanged.
def _draw_prob_redundancy_curve(max_k: int = 4) -> tuple[float, ...]:
    """Build the B4 per-copy utility curve from the draw-probability marginal.

    Degrades to an all-1.0 curve (no shaping) in the defensive case ``draw_probability(1)``
    is somehow 0 — cannot happen with the module's own default constants, but keeps this a
    total function rather than one that could divide by zero if the underlying constants are
    ever retuned to something degenerate.
    """
    marginals = [_draw_probability(k) - _draw_probability(k - 1) for k in range(1, max_k + 1)]
    m1 = marginals[0]
    if m1 <= 0.0:
        return tuple(1.0 for _ in range(max_k))
    return tuple(m / m1 for m in marginals)


_U_REDUNDANCY_DEFAULT: tuple[float, ...] = _draw_prob_redundancy_curve()
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


# --- Smart-mode calibration (epic-sideboard-core-and-hedge-gating) ---
# Field-element coverage marginals scale with (field_share × swing × Δg) — typically
# ~0.005–0.02 — so an ABSOLUTE redundancy_strength/τ tuned on unit models (weight≈1.0)
# would be wildly over-strong on a real field (→ 1-of-everything). Smart-mode derives both
# as FRACTIONS of the model's own coverage scale (the value of the best single first pick),
# so the defaults are field-scale-invariant. Tunable; the hedge feature may revisit.
_SMART_REDUNDANCY_FRACTION: float = 0.5   # 2nd copy of even the best card competes; weak cards → 1-of
_SMART_TAU_FRACTION: float = 0.1          # stop committing when a slot is worth <10% of the best pick


def _coverage_scale(model: "CoverageModel") -> float:
    """Value of the best single first-copy pick: max over candidates of Σ_e weight_e·Δg(1).

    The reference scale smart-mode multiplies its fractions by, so redundancy/τ track the
    actual field-weight magnitudes rather than absolute constants. 0.0 for an empty model.
    """
    best = 0.0
    m1 = _marginal_g(1)
    for _card, elems in model.candidate_covers.items():
        g = sum(model.element_weight.get(e, 0.0) for e in elems) * m1
        if g > best:
            best = g
    return best


# --- Hedge allocator (epic-sideboard-core-and-hedge-hedge-allocator, fast-follow) ---
# The dedicated core commits answers for the field you're CONFIDENT about; the leftover slots
# (when τ stopped the core short of the budget) are filled by the hedge — insurance against the
# field being different from your point estimate. v1 implements the brief's default mild
# EXPECTED-coverage hedge: optimize coverage over a field WIDENED toward uniform (so the hedge
# values archetypes the point estimate underweights), strong 1-of diversity, never re-picking or
# displacing a core commit. CVaR/worst-tail (the aggressive dial) is a documented future option.
_HEDGE_BLEND: float = 0.4  # 0 = point estimate, 1 = fully uniform; mild widening of the field


def _hedge_fill(
    model: "CoverageModel",
    core_cards: dict[str, int],
    *,
    budget: int,
    blend: float = _HEDGE_BLEND,
    option_value_bonus: "dict[str, float] | None" = None,
) -> dict[str, int]:
    """Fill leftover slots (budget − core) with diversity-preferring insurance picks.

    Greedily covers the field — WIDENED toward uniform by ``blend`` — that the core left
    uncovered, one copy per card (pure breadth), starting from the core's coverage state and
    never re-picking a core card. Returns {card: 1} for the hedge picks only (the insurance set);
    empty when the core already filled the budget or nothing positive remains.

    ``option_value_bonus`` (feature-sfv-option-value): optional card → CVaR tail-robustness
    bonus. Every hedge pick is, by construction, a card's first (and only) copy in the hedge
    set — cards already in ``core_cards`` are skipped, and the loop never re-picks a card once
    it's in ``insurance`` — so the bonus is applied unconditionally here (no first-copy check
    needed). ``None``/empty → byte-identical to the pre-feature hedge.
    """
    slots = budget - sum(core_cards.values())
    if slots <= 0:
        return {}
    pos = {e: w for e, w in model.element_weight.items() if w > 0.0}
    if not pos:
        return {}
    # Widened weights: blend each element toward the uniform mean (hedge the field-share estimate).
    uniform = sum(pos.values()) / len(pos)
    wide = {e: (1.0 - blend) * w + blend * uniform for e, w in pos.items()}
    # Coverage state inherited from the core (so the hedge covers what the core left open).
    cov: dict[str, int] = {}
    for c, n in core_cards.items():
        for e in model.candidate_covers.get(c, frozenset()):
            cov[e] = cov.get(e, 0) + n
    insurance: dict[str, int] = {}
    for _ in range(slots):
        best_card: str | None = None
        best_gain = 0.0
        for card in model.candidate_covers:
            if card in core_cards or card in insurance:
                continue  # 1-of diversity; never touch a core commit
            # feature-sfv-breadth-objective: canonical Σ-over-elements marginal gain
            # (weights=wide reproduces the prior inline `if e in wide` filter exactly,
            # since `wide`'s keys are precisely the positive-weight elements).
            gain = _element_sum_marginal_gain(model, card, cov, weights=wide)
            # feature-sfv-option-value: CVaR tail-robustness bonus (always first-copy here).
            if option_value_bonus:
                gain += option_value_bonus.get(card, 0.0)
            if gain > best_gain or (
                gain == best_gain and gain > 0.0 and (best_card is None or card < best_card)
            ):
                best_gain = gain
                best_card = card
        if best_card is None or best_gain <= 0.0:
            break  # no remaining card adds positive widened coverage
        insurance[best_card] = 1
        for e in model.candidate_covers[best_card]:
            cov[e] = cov.get(e, 0) + 1
    return insurance


# ---------------------------------------------------------------------------
# Heuristic swing constants (NOT empirical — labeled in every package output)
# ---------------------------------------------------------------------------

_SWING_DEDICATED = 0.20   # dedicated hate vs its primary target tag
_SWING_SOFT = 0.10        # soft / partial answers (counter-hosers, artifact removal, etc.)

# Pseudo-element key prefix for anti-hate elements
_HATE_ELEMENT_PREFIX = "_hate:"

# Minimum weight threshold for anti-hate pseudo-elements (filter out noise)
_HATE_ELEMENT_MIN_WEIGHT = 0.02

# feature-sfv-weights: cap on an UNCOVERED `_hate:` pseudo-element's weight, as a multiple of
# the largest real (archetype, tag) element weight already in the model.  A `_hate:<tag>`
# element's natural weight (Σ interactive field share × _SWING_SOFT) is NOT itself
# impact-discounted per-opponent the way real coverage weights are, so on a real field it can
# be several times larger than any single opponent element — that's fine IF the deck can
# actually field a protective answer (real, servable coverage should compete on its full
# weight). It becomes "dead crowding weight" (brief §2, distortion D2) only when NO catalog
# candidate survives this deck's color/anti-synergy filters to cover it (e.g. Veil of
# Summer/Carpet of Flowers need G; Defense Grid self-hoses a reactive counterspell deck — a UB
# reactive tempo deck honestly has no castable, non-self-hosing protective answer today). In
# that uncovered case only, cap the weight at this ratio × the model's own largest real element
# weight so it can no longer categorically out-rank every actual opponent need. 1.0 = "no more
# valuable than the single best real matchup this field presents" — generous enough that
# self-protection still shows up in the audit trail and can still win a slot when nothing else
# is competitive, but can't dominate for want of an answer nobody can play. See Step 4c below.
_HATE_UNCOVERED_WEIGHT_CAP_RATIO = 1.0

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
    ``symmetry``: ``"asymmetric"`` (default; affects only the opponent/their stuff) or
                 ``"symmetric"`` (affects the controller too — e.g. Grafdigger's Cage
                 stops ALL players casting from graveyard/library, including a
                 graveyard-recursion deck's own plan).  Consumed by Feature B's
                 self-hosing check; validated-but-inert in this feature.
    ``cast_requires``: a structured cast-condition token, or ``None`` when the card has
                 no conditional-cast requirement.  Known tokens: ``None``,
                 ``"opp_controls_plains"`` (e.g. Massacre's free-cast clause).
    ``functional_group``: identical-effect group key, or ``None``.  Cards sharing a
                 ``functional_group`` (Hydroblast ≡ Blue Elemental Blast, both
                 ``"red-blast"``) are de-duplicated to one coverage contribution in
                 ``_build_coverage_model`` — they don't stack as distinct coverage.
    """

    name: str
    attacks: frozenset[str]
    colors: frozenset[str]
    max_copies: int
    swing: float
    castable_any_color: bool = False
    symmetry: str = "asymmetric"
    cast_requires: "str | None" = None
    functional_group: "str | None" = None


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

# HoserCard.symmetry: valid values (Unit 2, feature-sb-effect-tagging-model).
_VALID_SYMMETRY = frozenset({"asymmetric", "symmetric"})

# HoserCard.cast_requires: known structured cast-condition tokens.  "opp_controls_plains"
# is Massacre's free-cast clause; Massacre itself is empirically promoted (not a curated
# catalog entry), so no shipped entry uses this token yet — the loader must still accept it.
_VALID_CAST_REQUIRES = frozenset({"opp_controls_plains"})

# HoserCard.attacks: the closed vulnerability-tag vocabulary a curated entry may claim.
# MUST stay in sync with the tags emitted by whattoplay._vulnerability_from_composition and
# whattoplay._color_contingent_tags — a curated tag outside this set can never match a derived
# vulnerability tag, so the entry would silently cover nothing. "_hate" is the counter-hoser
# pseudo-attack (see _HATE_ELEMENT_PREFIX), not a derived vulnerability tag.
_VALID_ATTACK_TAGS: frozenset[str] = frozenset({
    "_hate",
    "artifact-mana-reliant",
    "colorless-reliant",
    "combo",
    "creature-based",
    "graveyard-fuel",
    "graveyard-recursion",
    "low-curve",
    "low-interaction",
    "nonbasic-manabase",
    "noncreature-reliant",
    "ramp",
    "storm-reliant",
    "plays-black",
    "plays-blue",
    "plays-green",
    "plays-red",
    "plays-white",
})


def load_hoser_catalog(path: "Path | str") -> "dict[str, HoserCard]":
    """Load and validate a hoser catalog from a JSON data file.

    Format: ``{"version": "<date>", "hosers": [ { ... }, ... ]}``.

    Each hoser entry must have:
      ``name``          (str)
      ``attacks``       (list of tag strings; non-empty, each in ``_VALID_ATTACK_TAGS``)
      ``colors``        (list of WUBRG single-char strings; empty = colorless)
      ``max_copies``    (int ≥ 1)
      ``swing``         (float in (0,1) OR the aliases "dedicated" / "soft")

    Optional:
      ``castable_any_color`` (bool, default False)
      ``symmetry``           (str, one of "asymmetric"/"symmetric"; default "asymmetric")
      ``cast_requires``      (str or null; one of the known tokens; default null)
      ``functional_group``   (str or null; identical-effect group key; default null)
      ``_comment``           (str, ignored)

    Raises ``ValueError`` on schema violations (bad swing alias, empty attacks,
    invalid colors, max_copies < 1, unrecognized ``symmetry``/``cast_requires``)
    or ``FileNotFoundError`` when the path is absent.
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
        unknown_attacks = sorted(attacks - _VALID_ATTACK_TAGS)
        if unknown_attacks:
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'attacks' has unknown tag(s) "
                f"{unknown_attacks}; allowed: {sorted(_VALID_ATTACK_TAGS)}"
            )

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

        symmetry = entry.get("symmetry", "asymmetric")
        if symmetry not in _VALID_SYMMETRY:
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'symmetry' {symmetry!r} must be one of "
                f"{sorted(_VALID_SYMMETRY)}"
            )

        cast_requires = entry.get("cast_requires")
        if cast_requires is not None and cast_requires not in _VALID_CAST_REQUIRES:
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'cast_requires' {cast_requires!r} must be "
                f"null or one of {sorted(_VALID_CAST_REQUIRES)}"
            )

        functional_group_raw = entry.get("functional_group")
        if functional_group_raw is not None and not isinstance(functional_group_raw, str):
            raise ValueError(
                f"load_hoser_catalog: {name!r} 'functional_group' must be a string or null"
            )

        catalog[name] = HoserCard(
            name=name,
            attacks=attacks,
            colors=colors,
            max_copies=max_copies,
            swing=swing,
            castable_any_color=castable_any_color,
            symmetry=symmetry,
            cast_requires=cast_requires,
            functional_group=functional_group_raw,
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

# Color-blast oracle-text detection (feature-sb-effect-tagging-model, Unit 5).
# Matches the "Choose one — Counter target <color> spell; or Destroy target <color>
# permanent." template shared by Pyroblast/Hydroblast/Blue Elemental Blast/Red Elemental
# Blast, plus the "if it's <color>" phrasing Pyroblast/Hydroblast themselves use.
_RE_BLAST_RED = re.compile(r"target red (?:spell|permanent)|if it'?s red", re.IGNORECASE)
_RE_BLAST_BLUE = re.compile(r"target blue (?:spell|permanent)|if it'?s blue", re.IGNORECASE)

# Land destruction (epic-card-semantics-ir-fix-ld-mislabel): "destroy target land" / "destroy
# target nonbasic land" — Wasteland ("{T}, Sacrifice this land: Destroy target nonbasic
# land.") and Ghost Quarter ("{T}, Sacrifice this land: Destroy target land. ...").  Must be
# checked BEFORE rule 4's bare "destroy target" substring check, which would otherwise
# mislabel a promoted (non-catalog) land-destruction card as creature-based.
_RE_LAND_DESTRUCTION = re.compile(r"destroy target (?:nonbasic )?land\b", re.IGNORECASE)

# Broad free/soft anti-noncreature interaction (feature-sfv-attachments): the exact
# "counter target noncreature spell" template shared by Force of Negation / Spell Pierce /
# Mental Misstep-style noncreature-restricted counters — distinct from the generic
# "counter target spell" rule 1 already matches.  Attaches to the `noncreature-reliant`
# archetype axis so these cards credit the WHOLE combo/control plurality they answer,
# not only the narrower `combo`/`storm-reliant` tags rule 1 attaches to.
_RE_COUNTER_NONCREATURE = re.compile(r"counter target noncreature spell", re.IGNORECASE)

# Colorless-specific counter (feature-sfv-colorless-axis): "colorless spell" appearing
# alongside a counter effect — Consign to Memory ("Counter target triggered ability or
# colorless spell."), Ceremonious Rejection ("Counter target colorless spell.").  Attaches
# to the `colorless-reliant` archetype axis (whattoplay._vulnerability_from_composition),
# an axis independent of `noncreature-reliant` — a card can restrict to colorless spells
# without restricting to noncreature spells, and vice versa (Force of Negation/Spell Pierce
# hit noncreature spells of ANY color, including colorless, but do not specifically call out
# "colorless spell" the way Consign/Ceremonious Rejection do).
# `[^.]*` (not DOTALL `.*`) bounds the match to a single sentence — a future card reading
# "Counter target spell. ... colorless spell ..." in a LATER, unrelated sentence must not
# match; `[^.]*` still crosses the newline inside Consign to Memory's one sentence ("Counter
# target triggered ability or\ncolorless spell.") since a negated character class matches
# newlines regardless of DOTALL.
_RE_COUNTER_COLORLESS = re.compile(r"counter target[^.]*colorless spell", re.IGNORECASE)


def _derive_attacks_for_promoted(
    card_name: str,
    oracle_text: str,
    type_line: str,
) -> frozenset[str]:
    """Derive best-effort vulnerability-tag coverage for a promoted empirical card.

    Pure function — no DB.  Priority order (multiple tags possible):

    1. Counter magic:  "counter target" / "counter that spell"
       → {combo, storm-reliant}   (answers the most common free-spell targets)
    1b. Broad anti-noncreature counter: "counter target noncreature spell" (feature-sfv-
        attachments) → adds {noncreature-reliant}   (Force of Negation, Spell Pierce —
        attaches to the WHOLE combo/control plurality, not just rule 1's narrower slice)
    1c. Colorless-specific counter: "counter target ... colorless spell" (feature-sfv-
        colorless-axis) → adds {colorless-reliant}   (Consign to Memory, Ceremonious
        Rejection — an axis independent of 1b's noncreature restriction)
    2. Color blast: "target red/blue spell" / "target red/blue permanent" / "if it's red/blue"
       → {plays-red} / {plays-blue}   (Hydroblast/Pyroblast/Blue|Red Elemental Blast template)
    3. Graveyard exile: "exile" AND "graveyard" present
       → {graveyard-recursion}
    3b. Land destruction: "destroy target land" / "destroy target nonbasic land" (Wasteland,
        Ghost Quarter) → {nonbasic-manabase}   (checked, and skipped for rule 4, the same way
        rule 2's ``is_color_blast`` short-circuits rule 4 — otherwise the bare "destroy
        target" substring in rule 4 would mislabel a land-destruction spell creature-based)
    4. Removal: "destroy target" / "exile target creature" / "exile target attacking"
       → {creature-based}
    5. staple_role == "free_interaction" (card_tags lookup)
       → {combo, storm-reliant}   (Force of Negation, Daze, etc.)
    6. Artifact/enchantment removal: "destroy target artifact" / "destroy target enchantment"
       → {artifact-mana-reliant}  (reaches artifact mana sources — Lotus Petal, Chrome
       Mox, Lion's Eye Diamond. It cannot reach lands, so it does NOT credit nonbasic-manabase. Such a card's
       value in answering an opposing Blood Moon / Back to Basics is PROTECTION of its own
       controller's manabase, a relation this attack vocabulary does not express.)
    7. Fallback: {combo}  (conservative — labeled in warning by caller).

    Returns a frozenset of tag strings.  Never returns the empty frozenset so
    ``HoserCard.attacks`` is always non-empty.
    """
    from legacy_engine.card_tags import staple_role

    text_lower = (oracle_text or "").lower()
    tags: set[str] = set()

    # 1. Counter magic
    if "counter target" in text_lower or "counter that spell" in text_lower:
        tags.update({"combo", "storm-reliant"})

    # 1b. Broad anti-noncreature counter (feature-sfv-attachments) — additive on top of
    # rule 1's combo/storm-reliant: attaches to the noncreature-reliant axis so a card
    # like Force of Negation credits the whole combo/control plurality it answers.
    if _RE_COUNTER_NONCREATURE.search(text_lower):
        tags.add("noncreature-reliant")

    # 1c. Colorless-specific counter (feature-sfv-colorless-axis) — additive on top of
    # rule 1's combo/storm-reliant, independent of 1b's noncreature-reliant.
    if _RE_COUNTER_COLORLESS.search(text_lower):
        tags.add("colorless-reliant")

    # 2. Color blast — checked before the generic "destroy target" removal rule below,
    # since blasts phrase permanent-destruction as "destroy target red/blue permanent",
    # which would otherwise false-positive into creature-based.
    is_color_blast = False
    if _RE_BLAST_RED.search(text_lower):
        tags.add("plays-red")
        is_color_blast = True
    if _RE_BLAST_BLUE.search(text_lower):
        tags.add("plays-blue")
        is_color_blast = True

    # 3. Graveyard exile
    if "graveyard" in text_lower and "exile" in text_lower:
        tags.add("graveyard-recursion")

    # 3b. Land destruction — checked before rule 4's bare "destroy target" substring check,
    # which would otherwise mislabel Wasteland/Ghost Quarter-style effects creature-based.
    is_land_destruction = bool(_RE_LAND_DESTRUCTION.search(text_lower))
    if is_land_destruction:
        tags.add("nonbasic-manabase")

    # 4. Creature removal (skip when already attributed as a color blast — see #2 — or as
    # land destruction — see #3b)
    if not is_color_blast and not is_land_destruction and (
        "destroy target" in text_lower
        or "exile target creature" in text_lower
        or "exile target attacking" in text_lower
    ):
        tags.add("creature-based")

    # 5. staple_role == free_interaction (Force of Negation, Daze, etc.)
    if staple_role(card_name) == "free_interaction":
        tags.update({"combo", "storm-reliant"})

    # 6. Artifact/enchantment removal → reaches artifact mana sources only, never lands
    if (
        "destroy target artifact" in text_lower
        or "destroy target enchantment" in text_lower
        or ("exile target" in text_lower and "artifact" in text_lower)
        or ("exile target" in text_lower and "enchantment" in text_lower)
    ):
        tags.add("artifact-mana-reliant")

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
# Unit C1 (feature-sb-maindeck-aware-coverage, story …-discount): maindeck-answer
# coverage detector.
# ---------------------------------------------------------------------------

# Max fraction of an element's weight a fully-maindeck-covered tag loses (never fully
# zeroes an axis — a maindeck answer is rarely a perfect substitute for a dedicated SB
# slot: it may be a single copy already in play, timing-constrained, or matched up
# against a different specific threat than the SB slot would cover).
_MAINDECK_DISCOUNT: float = 0.6

# Copies of maindeck answers at which a tag's coverage saturates to 1.0. 4 mirrors the
# Legacy 4-of ceiling — a deck answering an axis with its full playset of copies is
# treated as maximally (but not more than maximally) covering that axis.
_MAINDECK_SATURATION: int = 4


def _maindeck_answer_coverage(
    main_cards: "dict[str, int]",
    get_card: "Callable[[str], Card | None]",
    *,
    catalog: "dict[str, HoserCard] | None" = None,
) -> "dict[str, float]":
    """Saturating [0,1] per-tag coverage the MAINDECK already provides.

    For each maindeck card (name -> copy count), determine which vulnerability tags it
    answers and accumulate a copy-weighted coverage score per tag, saturating at
    ``_MAINDECK_SATURATION`` copies (a full playset maxes a tag's coverage at 1.0; more
    copies cannot push it past 1.0).

    Attribution, in priority order:
      1. Catalog lookup — when the maindeck card is itself a curated ``HOSER_CATALOG``
         entry (e.g. Wasteland, whose curated ``attacks`` is ``{"nonbasic-manabase"}``),
         its hand-curated ``attacks`` are authoritative. This is the common case for the
         motivating bug (maindeck utility lands/interaction that double as catalog hosers).
      2. Oracle-text derivation — for maindeck cards NOT in the catalog, reuse
         ``_derive_attacks_for_promoted`` (the same oracle->attacks heuristic
         ``_build_promoted_candidates`` already uses for empirical SB promotions) against
         the card's resolved ``oracle_text``/``type_line``. Cards for which the heuristic
         only reaches its conservative ``_FALLBACK_ATTACKS`` (i.e. no concrete signal
         matched) are treated as answering NOTHING — crediting the fallback tag here would
         indiscriminately discount that tag for every maindeck (60 cards, most of which
         answer nothing), which is not the intent.

    ``get_card``: name -> resolved ``Card`` (or ``None`` if unresolved). Injected so this
    function stays DB-free and pure (objective-search-split): the caller resolves cards
    ONCE (``_load_deck_cards``) and passes a plain dict-backed lookup; this loop is then
    unit-testable with hand-built ``get_card`` callables, no DB required.

    The ``"_hate"`` pseudo-attack (counter-hoser marker) is not a real vulnerability tag
    and is excluded from the returned coverage, mirroring how ``_build_coverage_model``
    already excludes ``_hate:`` pseudo-elements from other multiplier passes.
    """
    if catalog is None:
        catalog = HOSER_CATALOG

    raw_copies: dict[str, float] = {}  # tag -> Σ copies of maindeck cards answering it
    for name, count in main_cards.items():
        if count <= 0:
            continue

        hoser = catalog.get(name)
        if hoser is not None:
            attacks = hoser.attacks
        else:
            card = get_card(name)
            if card is None:
                continue
            attacks = _derive_attacks_for_promoted(name, card.oracle_text, card.type_line)
            if attacks == _FALLBACK_ATTACKS:
                continue  # no concrete signal — don't credit the conservative fallback

        for tag in attacks:
            if tag == "_hate":
                continue
            raw_copies[tag] = raw_copies.get(tag, 0.0) + count

    return {
        tag: min(1.0, copies / _MAINDECK_SATURATION)
        for tag, copies in raw_copies.items()
    }


# ---------------------------------------------------------------------------
# Unit 2: CoverageModel + _build_coverage_model
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 4-of legality guard (epic-sb-advisor-correctness-fourof-guard).
# ---------------------------------------------------------------------------

# Format copy limit. Basic lands are exempt (CR 100.2a / the "any number of basic lands"
# carve-out); every other card is capped at 4 across maindeck + sideboard COMBINED.
_FORMAT_MAX_COPIES = 4


def _is_basic_land(card: "Card | None") -> bool:
    """True for basic lands, which the 4-of rule exempts.

    Detected from ``type_line`` containing "Basic" (the supertype), so snow-covered basics
    and Wastes are covered without a hardcoded name list. Unknown cards (``None``) are NOT
    treated as basics — an unresolvable card must not silently bypass the legality cap.
    """
    if card is None:
        return False
    return "basic" in (card.type_line or "").lower()


def _maindeck_copy_caps(
    main_cards: "dict[str, int]",
    get_card: "Callable[[str], Card | None]",
) -> "dict[str, int]":
    """Remaining format-legal copies per maindeck card name.

    ``{name: 4 - maindeck_copies}`` for every non-basic card the maindeck already runs,
    floored at 0. A name absent from the result is unconstrained (the maindeck runs none).
    Basics are omitted entirely — they are exempt from the 4-of rule.

    Pure function (objective-search-split): the caller resolves Card objects once and
    passes a lookup, so no DB access happens inside the loop.
    """
    caps: dict[str, int] = {}
    for name, copies in main_cards.items():
        if copies <= 0:
            continue
        if _is_basic_land(get_card(name)):
            continue
        caps[name] = max(0, _FORMAT_MAX_COPIES - copies)
    return caps


def _fourof_legality_warnings(
    sideboard_cards: "dict[str, int]",
    main_cards: "dict[str, int]",
    get_card: "Callable[[str], Card | None]",
) -> "list[str]":
    """Post-check the assembled package: combined main+SB copies must not exceed 4.

    Returns one honest-degrade warning per offending card (empty list = legal). This is a
    backstop, not the primary mechanism — the candidate cap in ``_build_coverage_model``
    should prevent an illegal package from ever being assembled. It fires only if some path
    bypasses that cap, which is exactly when a silent illegal board would otherwise ship.
    """
    out: list[str] = []
    for name, sb_copies in sorted(sideboard_cards.items()):
        main_copies = main_cards.get(name, 0)
        total = main_copies + sb_copies
        if total <= _FORMAT_MAX_COPIES:
            continue
        if _is_basic_land(get_card(name)):
            continue
        out.append(
            f"// ILLEGAL: {name} {main_copies} main + {sb_copies} SB = {total} copies "
            f"(max {_FORMAT_MAX_COPIES})"
        )
    return out


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
    opponent_linchpins: "dict[str, list[Linchpin]] | None" = None,
    opponent_cards: "dict[str, dict[str, int]] | None" = None,
    maindeck_coverage: "dict[str, float] | None" = None,
    maindeck_copy_caps: "dict[str, int] | None" = None,
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
    actually care about — not every tag indiscriminately.  Coverability (feature-sfv-weights):
    a counter-hoser that survives the color/anti-synergy/empirical-pool filters below covers
    every `_hate:<tag>` element the deck carries at FULL natural weight — real self-protection
    is real coverage.  When NO candidate survives those filters for a given deck (its
    color/anti-synergy profile leaves nothing castable), Step 4c caps that element's weight
    relative to the model's own real coverage scale instead of leaving it as uncapped "dead
    crowding weight" (brief §2, D2).

    Anti-synergy filter (feature-archetype-empirical-recommendations):
    When ``anti_synergy_signals`` is not None, catalog candidates whose name appears in
    ``_ANTI_SYNERGY_MAP`` and whose signal fires for this deck are dropped before coverage
    computation.  Gated-additive: ``anti_synergy_signals=None`` → no-op (byte-identical to
    pre-feature for callers that don't supply deck composition).

    Empirical pool filter (feature-archetype-empirical-recommendations):
    When ``empirical_pool`` is not None, catalog candidates NOT in the pool are dropped.
    Gated-additive: ``empirical_pool=None`` → no-op.  Counter-hosers (``"_hate"`` in
    ``hoser.attacks``, feature-sfv-weights) are EXEMPT from this filter — see Step 4's inline
    comment for why self-protection doesn't need corpus-adoption validation the way an
    opponent-facing hoser does.

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

    Impact-modulated element weights (feature-sb-field-weighted-scorer-wiring, Unit B3;
    draw-prob deflation removed by feature-sfv-weights):
    When ``opponent_linchpins`` is not None, each (archetype, tag) element's weight is
    additionally multiplied by
    ``impact(best_hoser_for_tag, archetype, ...).score_without_draw_prob()`` — the decomposed
    centrality × symmetry × castability score (see ``advisory.impact``; NOT ``.score()``, which
    also folds in ``draw_prob``) of the SAME hoser Step 1 already selected as the tag's
    best-swing answer, evaluated specifically against that opponent archetype's linchpins
    (``opponent_linchpins[archetype]``, defaulting to ``[]``) and this deck's own
    colors/vulnerability-tags (``deck_colors``/``deck_tags`` — reused as-is; no separate
    "my-side" parameters needed).  ``opponent_cards`` optionally supplies each opponent's known
    maindeck composition for the ``cast_requires`` castability gate (e.g. Massacre's "opponent
    controls a Plains" clause).  Uses ``copies=1`` only to evaluate castability
    (``cast_requires`` gating can be copy-count-sensitive in principle, though none of today's
    tokens are); the resulting ``draw_prob`` factor is discarded, never multiplied in — the
    copy-count taper is EXCLUSIVELY Unit B4's job (the ILP/greedy per-copy marginal via
    ``_u_redundancy``).  Folding ``draw_probability`` into the element weight too would
    double-count the same draw dimension AND uniformly deflate the whole element-weight scale
    (draw_prob(1)≈0.4 for every impact-modulated element) — the exact bug feature-sfv-weights
    fixes (see ``docs/briefs/scorer-flexibility-valuation.md`` §2, distortion D2).
    Gated-additive: ``opponent_linchpins=None`` (the default) → every impact multiplier is 1.0 →
    element weights are BYTE-IDENTICAL to pre-impact (mirrors the ``matchup_pressure is None``
    no-op above).

    Maindeck-aware coverage discount (feature-sb-maindeck-aware-coverage, Unit C2):
    When ``maindeck_coverage`` is not None (see ``_maindeck_answer_coverage``), each
    (archetype, tag) element's weight is additionally multiplied by
    ``(1 - _MAINDECK_DISCOUNT * maindeck_coverage.get(tag, 0.0))`` — an axis the maindeck
    already answers (e.g. 4 maindeck Wasteland covering "nonbasic-manabase") should not also
    claim a full-weight dedicated SB slot for the same axis. ``_hate:`` pseudo-elements are
    EXEMPT (mirrors the ``"|" not in key`` skip in the ``matchup_pressure`` pass above) —
    they represent field-wide interaction pressure against the DECK's own vulnerabilities,
    not an archetype-vs-tag coverage axis a maindeck card could substitute for. A
    ``// maindeck-aware: ...`` audit line is appended to ``warnings`` for each tag actually
    discounted. Gated-additive: ``maindeck_coverage=None`` or ``{}`` → no-op → element
    weights are BYTE-IDENTICAL to pre-discount (mirrors the ``opponent_linchpins is None``
    no-op above).
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
    # best_hoser_for_tag (Unit B3): the specific hoser object achieving best_swing_for_tag[tag],
    # tracked alongside so the impact multiplier in Step 2 can be computed for "the same best
    # hoser for the tag the code already selects" — best_swing_for_tag's VALUES are unaffected
    # (still the strict running max), only this extra hoser-identity bookkeeping is new.
    best_swing_for_tag: dict[str, float] = {}
    best_hoser_for_tag: dict[str, HoserCard] = {}
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
            if effective_swing > best_swing_for_tag.get(tag, 0.0):
                best_swing_for_tag[tag] = effective_swing
                best_hoser_for_tag[tag] = hoser

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
                weight = share * swing

                # Impact modulation (Unit B3): scale by the decomposed impact score of the
                # tag's best-swing hoser against THIS specific opponent archetype. A
                # symmetric self-hosing hoser or one this deck can't cast for this matchup
                # shouldn't carry full weight just because it's the theoretical best swing.
                # copies=1: the taper across MULTIPLE copies is Unit B4's job (the ILP/greedy
                # per-copy marginal) — reusing draw_probability here at max_copies would
                # double-count that taper.
                if opponent_linchpins is not None:
                    best_hoser = best_hoser_for_tag.get(tag)
                    if best_hoser is not None:
                        opp_lps = opponent_linchpins.get(archetype, [])
                        opp_cards_for_arch = (
                            opponent_cards.get(archetype) if opponent_cards else None
                        )
                        breakdown = _compute_impact(
                            best_hoser,
                            archetype,
                            opp_linchpins=opp_lps,
                            my_vulnerability_tags=deck_tags,
                            my_colors=deck_colors,
                            copies=1,
                            opp_cards=opp_cards_for_arch,
                        )
                        # feature-sfv-weights: centrality × symmetry × castability ONLY —
                        # NOT .score() (which also multiplies by draw_prob).  draw_prob(1)≈0.4
                        # belongs exclusively to the per-copy taper (_u_redundancy, B4 below);
                        # folding it into the element weight too double-counted the draw
                        # dimension and uniformly deflated every impact-modulated weight ~0.4x
                        # (see docstring + docs/briefs/scorer-flexibility-valuation.md §2 D2).
                        weight *= breakdown.score_without_draw_prob()

                element_weight[key] = weight
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

    # Snapshot of the largest REAL (archetype, tag) element weight, taken before any `_hate:`
    # pseudo-element exists — this is the reference scale Step 4c's uncovered-weight cap sizes
    # against (feature-sfv-weights).  Deliberately captured here (only Step 2 has run) rather
    # than after Step 3b/3c's matchup-pressure/maindeck-discount multipliers, so the cap
    # reference is stable and independent of those later, unrelated modulations.
    _max_real_element_weight = max(element_weight.values(), default=0.0)

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
    #   • Step 4c (below, feature-sfv-weights) caps this natural weight when NO candidate ends
    #     up covering it — "dead crowding weight" per the epic's D2 finding — while a hate
    #     element that IS covered by a real candidate keeps this full, uncapped weight.
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

    # --- Step 3c: Maindeck-aware coverage discount (feature-sb-maindeck-aware-coverage,
    # Unit C2) ---
    # When maindeck_coverage is not None, discount each (archetype, tag) element's weight
    # by how much the MAINDECK already answers that tag — stops the solver from double-
    # counting an axis (e.g. 4 maindeck Wasteland already covering "nonbasic-manabase" ->
    # the SB shouldn't also spend a full-weight slot on Ghost Quarter for the same axis).
    # `_hate:` pseudo-elements are exempt (same "|" not in key skip as Step 3b) — they
    # model field-wide interactive pressure against the deck's OWN vulnerabilities, not an
    # archetype coverage axis a maindeck card could substitute for.
    # When maindeck_coverage is None (or empty), this step is a no-op -> byte-identical.
    if maindeck_coverage:
        _discounted_tags: set[str] = set()
        for key in list(element_weight.keys()):
            if "|" not in key:
                continue  # skip anti-hate pseudo-elements
            tag = key.split("|", 1)[1]
            coverage = maindeck_coverage.get(tag, 0.0)
            if coverage <= 0.0:
                continue
            discount = _MAINDECK_DISCOUNT * coverage
            element_weight[key] = element_weight[key] * (1.0 - discount)
            _discounted_tags.add(tag)
        for tag in sorted(_discounted_tags):
            pct = _MAINDECK_DISCOUNT * maindeck_coverage.get(tag, 0.0) * 100.0
            warnings.append(
                f"// maindeck-aware: discounted {tag} by {pct:.0f}% (deck already answers it)"
            )

    # --- Step 4: Color-prefiltered candidate hosers ---
    candidate_covers: dict[str, frozenset[str]] = {}
    candidate_meta: dict[str, HoserCard] = {}

    # 4-of legality cap (epic-sb-advisor-correctness-fourof-guard): a candidate's usable
    # copies are bounded by what the MAINDECK leaves legal, not by the catalog/modal count
    # alone. Applied here at candidate_meta assembly — the single point every consumer
    # (_greedy_solve, _ilp_solve, _rank_considering_pool) reads max_copies from — so the
    # solver and the considering pool are capped by one rule instead of two.
    # Element weights are deliberately NOT touched: how valuable answering a tag is does not
    # depend on how many copies THIS deck may still add.
    # Gated-additive: maindeck_copy_caps None/{} -> no-op -> byte-identical.
    _capped_out: list[str] = []
    _capped_down: list[str] = []

    def _apply_copy_cap(name: str, hoser: HoserCard) -> "HoserCard | None":
        """Cap a candidate at its remaining format-legal copies; None = drop entirely."""
        if not maindeck_copy_caps:
            return hoser
        cap = maindeck_copy_caps.get(name)
        if cap is None or cap >= hoser.max_copies:
            return hoser
        if cap <= 0:
            _capped_out.append(name)
            return None
        _capped_down.append(f"{name} ({hoser.max_copies}->{cap})")
        return _dc_replace(hoser, max_copies=cap)

    for card_name, hoser in catalog.items():
        # Empirical pool filter (gated-additive): when provided, drop cards not in the pool.
        # This grounds OPPONENT-facing recommendations in what real archetype sideboards
        # actually run.  Counter-hosers (attacks contains "_hate", feature-sfv-weights) are
        # EXEMPT: self-protection castability is already fully decided by the color and
        # anti-synergy checks below — a protective card doesn't need "the field to run answers
        # like this" validation the way an opponent-facing hoser does, and gating it on
        # adoption-in-the-corpus would just re-introduce uncoverable `_hate:` weight for any
        # deck/archetype combination where nobody has happened to register it yet (mirrors the
        # existing `_hate:` exemption from the Step 3c maindeck-aware discount below).
        if (
            empirical_pool is not None
            and card_name not in empirical_pool
            and "_hate" not in hoser.attacks
        ):
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
            _capped = _apply_copy_cap(card_name, hoser)
            if _capped is None:
                continue
            candidate_covers[card_name] = frozenset(covered)
            candidate_meta[card_name] = _capped

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
                _capped_p = _apply_copy_cap(card_name, hoser)
                if _capped_p is None:
                    continue
                candidate_covers[card_name] = frozenset(covered_promoted)
                candidate_meta[card_name] = _capped_p
                log.debug(
                    "_build_coverage_model: admitted promoted %r covering %d elements",
                    card_name, len(covered_promoted),
                )
            else:
                log.debug(
                    "_build_coverage_model: promoted %r covers no live elements — skipped",
                    card_name,
                )

    # Audit lines for the 4-of cap — emitted once, after BOTH the catalog and promoted
    # candidate loops, so a card capped on either path is reported the same way.
    if _capped_out:
        warnings.append(
            "// 4-of guard: dropped "
            + ", ".join(sorted(set(_capped_out)))
            + " (maindeck already runs 4)"
        )
    if _capped_down:
        warnings.append(
            "// 4-of guard: capped " + ", ".join(sorted(set(_capped_down))) + " by maindeck copies"
        )

    # --- Step 4c: cap UNCOVERED `_hate:` weight (feature-sfv-weights) ---
    # The epic's locked decision is to make protective/counter-hoser cards actually COVER the
    # `_hate:` pseudo-elements they represent (Step 3/4/4b above already do this correctly: a
    # counter-hoser that survives the empirical-pool/anti-synergy/color filters covers every
    # `_hate:<tag>` element the deck carries) — real, castable, non-self-hosing self-protection
    # earns its full natural weight as genuine coverage, no cap.
    #
    # But a hate element can still end up with ZERO covering candidate — e.g. a UB reactive
    # tempo deck: Veil of Summer / Carpet of Flowers require G, and Defense Grid is correctly
    # anti-synergy-filtered for a reactive counterspell shell (it taxes the deck's OWN
    # instant-speed answers too). That is not a bug to paper over — it would be dishonest to
    # force a green card castable in a blue-black deck, or to waive a genuine self-harm check —
    # it is the brief's D2 finding: dead crowding weight with no way to be served. Cap it
    # relative to the model's own largest real element weight (``_max_real_element_weight``,
    # snapshotted before Step 3) so it can no longer out-rank every actual opponent need, while
    # staying visible (not zeroed) in the audit trail.
    if hate_elements_added:
        _hate_covered_keys: set[str] = set()
        for covers in candidate_covers.values():
            for key in covers:
                if key.startswith(_HATE_ELEMENT_PREFIX):
                    _hate_covered_keys.add(key)
        for tag in sorted(hate_elements_added):
            hate_key = _HATE_ELEMENT_PREFIX + tag
            if hate_key in _hate_covered_keys:
                continue  # a real candidate covers it — full natural weight stands
            if _max_real_element_weight <= 0.0:
                continue  # nothing real to size the cap against — leave the natural weight
            natural = element_weight.get(hate_key, 0.0)
            cap = _HATE_UNCOVERED_WEIGHT_CAP_RATIO * _max_real_element_weight
            if natural > cap:
                element_weight[hate_key] = cap
                warnings.append(
                    f"// hate-uncovered: capped {hate_key} weight to {cap:.4f} "
                    f"(was {natural:.4f}) — no compatible protective card covers it "
                    "for this deck (color/anti-synergy exclusion)"
                )

    # --- Step 5: functional_group de-dup (feature-sb-effect-tagging-model, Unit 5) ---
    # Cards sharing a functional_group are mechanically identical effects (Hydroblast ≡
    # Blue Elemental Blast, both "red-blast") — only the best-swing candidate per group
    # stays in the candidate universe so they don't stack as distinct coverage.  Ties break
    # on name for determinism.  Ownership is deliberately NOT a tiebreaker here: the
    # coverage model must stay collection-blind (byte-identical contract, Unit 2 of
    # epic-deck-generation-sideboard-maindeck) — ownership is a post-hoc annotation layer.
    _group_best: dict[str, tuple[float, str]] = {}
    for name, hoser in candidate_meta.items():
        group = hoser.functional_group
        if group is None:
            continue
        effective_swing = (
            card_swing_overrides[name]
            if card_swing_overrides and name in card_swing_overrides
            else hoser.swing
        )
        current = _group_best.get(group)
        if current is None or effective_swing > current[0] or (
            effective_swing == current[0] and name < current[1]
        ):
            _group_best[group] = (effective_swing, name)

    for name in list(candidate_meta.keys()):
        group = candidate_meta[name].functional_group
        if group is not None and _group_best[group][1] != name:
            log.debug(
                "_build_coverage_model: dropping %r — functional_group %r de-dup (kept %r)",
                name, group, _group_best[group][1],
            )
            del candidate_meta[name]
            del candidate_covers[name]

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
    option_value_bonus: "dict[str, float] | None" = None,
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

    ``option_value_bonus`` (feature-sfv-option-value): optional card → CVaR tail-robustness
    bonus (see ``_build_option_value_bonuses``), credited ONLY on a card's first copy — the
    option value is "having access to this answer at all", not a per-copy dimension, strictly
    separate from the redundancy/draw-probability taper below. ``None``/empty → byte-identical
    to the pre-feature objective. The bonus is added to a card's gain BEFORE the τ natural-budget
    comparison below runs, so it can deliberately resurrect a card past the τ stop that its base
    coverage marginal alone would not have cleared (see the natural-budget-stop comment).

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

            # feature-sfv-breadth-objective: canonical Σ-over-elements submodular marginal
            # gain (see `_element_sum_marginal_gain`) — a card's value aggregates its
            # marginal contribution across EVERY element it covers, not one in isolation.
            # With the saturating model this per-element term is always > 0, so redundant
            # answers earn value.
            gain = _element_sum_marginal_gain(model, card_name, cov_counts)

            # Per-card-copy redundancy penalty: the (current_copies+1)-th copy of THIS card
            # is worth less (or net-negative) than its raw coverage marginal. No-op when
            # redundancy_strength == 0.0 (byte-identical baseline).
            gain -= _redundancy_penalty(current_copies + 1, strength=redundancy_strength)

            # feature-sfv-option-value: CVaR tail-robustness bonus, first copy only.
            if current_copies == 0 and option_value_bonus:
                gain += option_value_bonus.get(card_name, 0.0)

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
            # A card resurrected past this stop purely by its option-value bonus (base marginal
            # ≤ τ, base+bonus > τ) is intended, not a bug — the bonus is insurance-like and is
            # allowed to buy a dedicated slot the mean-field coverage marginal alone could not.
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


def _build_ilp_problem(
    model: CoverageModel,
    *,
    budget: int,
    redundancy_strength: float = 0.0,
    tau: float = 0.0,
    option_value_bonus: "dict[str, float] | None" = None,
) -> "tuple[object, dict[str, object]]":
    """Construct the saturating-coverage ILP; returns ``(problem, x_vars)`` unsolved.

    Split from ``_ilp_solve`` (idea-ilp-tiebreak-nondeterminism) so tests can assert the
    construction invariant directly: the generated formulation must be identical regardless
    of the iteration order of ``model``'s dicts. Upstream those dicts inherit run-to-run-
    unstable orderings (DuckDB's multithreaded row emission; str-hash randomization across
    processes); pre-fix that order decided CONSTRAINT insertion order (PuLP name-sorts
    variables at write time, but rows keep insertion order), and CBC's tie resolution is
    sensitive to row order — equal-objective boards flipped between runs (observed: Snuff
    Out vs Sheoldred's Edict on identical Dimir Tempo inputs, 2026-07-04). Every loop below
    therefore iterates in sorted order.

    Formulation:
      Variables:
        x_c ∈ {0..max_copies} integer for each candidate card c.
        y_a^t ∈ {0,1} for element a and coverage level t = 1..T_a
            (T_a = min(sum of max_copies of covering cards, _ILP_T_CAP)).
        p_c ∈ [0,1] continuous for each card c with a positive option-value bonus
            (feature-sfv-option-value; omitted entirely when ``option_value_bonus`` is
            None/empty).
      Objective:
        max Σ_{a,t} weight_a · (g(t)−g(t−1)) · y_a^t  +  Σ_c option_value_bonus[c] · p_c
      Constraints:
        Σ_c x_c ≤ budget                               (slot budget)
        x_c ≤ max_copies_c                              (copy cap)
        Σ_{t=1}^{T_a} y_a^t ≤ Σ_{c covers a} x_c      ∀a  (level t can only fire if an answer is picked)
        y_a^t ∈ {0,1}                                   (binary; monotone fill is automatic because
                                                         coefficients are decreasing so solver prefers
                                                         lower t first)
        p_c ≤ x_c                                       (p_c is a presence indicator: the
                                                         solver sets it to min(1, x_c) since its
                                                         objective coefficient is non-negative)

    The y_a^t monotone-fill property: since g(t)−g(t−1) > g(t+1)−g(t) (decreasing marginals),
    the solver will always prefer to fill y_a^1 before y_a^2, so explicit ordering constraints
    are unnecessary.

    Raises _ILPFailed if PuLP is unavailable.
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
    for card_name, hoser in sorted(model.candidate_meta.items()):
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
        for card_name, hoser in sorted(model.candidate_meta.items()):
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

    # --- Option-value presence bonus (feature-sfv-option-value) ---
    # p_c ∈ [0,1] continuous, constrained p_c ≤ x_c: since the objective is a MAXIMIZATION
    # and every bonus_c ≥ 0, the solver always sets p_c = min(1, x_c) at the optimum — an
    # exact LP encoding of "does this card appear at all" that needs no extra integer/binary
    # variable. Credited once per card (not per copy) — strictly separate from the per-copy
    # redundancy penalty above, mirroring the first-copy-only gating in `_greedy_solve`/
    # `_hedge_fill`/`_rank_considering_pool`. Only cards with a positive bonus get a p_c var
    # at all (mirrors the `if coef > 0.0`/`if pen > 0.0` filters elsewhere) — when
    # `option_value_bonus` is None/empty, no p_c vars or constraints are created → the model
    # is byte-identical to the pre-feature ILP.
    option_bonus_terms: list = []
    if option_value_bonus:
        for card_name, bonus in sorted(option_value_bonus.items()):
            if bonus <= 0.0 or card_name not in x_vars:
                continue
            p_c = pulp.LpVariable(name=f"p_{_safe(card_name)}", lowBound=0, upBound=1, cat="Continuous")
            prob += p_c <= x_vars[card_name], f"presence_{_safe(card_name)}"
            option_bonus_terms.append(bonus * p_c)

    # --- Decision variables: y_a^t for each element a and level t ---
    # T_a = min(total possible answers for element a, _ILP_T_CAP)
    y_vars: dict[tuple[str, int], pulp.LpVariable] = {}
    elem_t_cap: dict[str, int] = {}

    for elem_id, weight in sorted(model.element_weight.items()):
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
    # feature-sfv-breadth-objective: this sum over (element, level) pairs is the LP
    # linearization of the SAME aggregate quantity `_element_sum_marginal_gain` computes for
    # greedy — Σ_{a,t} weight_a·Δg(t)·y_a^t equals Σ_e weight_e·g(cov_e) at the optimum, so a
    # card credited across many elements accumulates exactly as much objective value here as
    # in the greedy trace. Kept as an explicit y_a^t LP (not a call into the greedy helper)
    # because CBC needs a linear objective; the two are provably the same F(S).
    obj_terms = []
    for elem_id, weight in sorted(model.element_weight.items()):
        t_cap = elem_t_cap.get(elem_id, 0)
        for t in range(1, t_cap + 1):
            coef = weight * _marginal_g(t)
            if coef > 0.0:
                obj_terms.append(coef * y_vars[(elem_id, t)])
    obj_terms.extend(penalty_terms)  # negative per-copy redundancy terms (empty when off)
    obj_terms.extend(option_bonus_terms)  # positive first-copy option-value terms (empty when off)
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
    for elem_id in sorted(model.element_weight):
        t_cap = elem_t_cap.get(elem_id, 0)
        if t_cap == 0:
            continue
        covering_cards = [
            x_vars[c]
            for c, elems in sorted(model.candidate_covers.items())
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

    return prob, x_vars


def _ilp_solve(
    model: CoverageModel,
    *,
    budget: int,
    redundancy_strength: float = 0.0,
    tau: float = 0.0,
    option_value_bonus: "dict[str, float] | None" = None,
) -> dict[str, int]:
    """Exact saturating-coverage ILP via PuLP/CBC — see ``_build_ilp_problem`` for the model.

    Returns card→copies (only x_c > 0 entries).
    Raises _ILPFailed if CBC is unavailable or status is not Optimal.
    """
    prob, x_vars = _build_ilp_problem(
        model,
        budget=budget,
        redundancy_strength=redundancy_strength,
        tau=tau,
        option_value_bonus=option_value_bonus,
    )
    import pulp  # _build_ilp_problem already proved it importable

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

def _resolve_land_names(
    con: duckdb.DuckDBPyConnection, names: "Iterable[str]"
) -> frozenset[str]:
    """Names among ``names`` whose ``cards.type_line`` contains "Land".

    The land test is the TYPE LINE, never the ``cards.is_land`` column.  ``is_land`` is TRUE
    for modal-DFC face-alias rows whose front face is a spell (``store.load_cards`` sets
    ``face_is_land`` for every face of a both-castable layout when ANY face is a land), so
    gating on the column would exempt Sink into Stupor (``type_line = 'Instant'``),
    Shatterskull Smashing, Fell the Profane and 31 other spells from ever being sided out.
    The type-line test still catches Dryad Arbor (``'Land Creature — Forest Dryad'``) and
    transform lands like Westvale Abbey (``'Land'``), whose front face IS a land drop.

    Returns ``frozenset()`` on any lookup failure — an unresolvable card list degrades to the
    pre-exemption behavior rather than crashing the planner.
    """
    unique = sorted({n for n in names if n})
    if not unique:
        return frozenset()
    try:
        placeholders = ", ".join("?" for _ in unique)
        rows = con.execute(
            # placeholders is a "?, ?, …" run sized to `unique`; every NAME is bound, never
            # interpolated.
            f"SELECT name FROM cards WHERE name IN ({placeholders}) "
            "AND type_line ILIKE '%land%'",
            unique,
        ).fetchall()
    except Exception as exc:
        log.debug("_resolve_land_names: type_line lookup failed: %s", exc)
        return frozenset()
    return frozenset(row[0] for row in rows)


def _in_axis_verdict(
    card_axes: frozenset[str], opp_axes: frozenset[str]
) -> tuple[bool, str]:
    """``(allowed, reason)`` for one IN candidate against one opponent's axis set.

    Correlational lift alone promoted cards with no target in the matchup (a Hydroblast
    ``{"plays-red"}`` IN against a UB mirror).  This adds the axis check; it never promotes,
    only declines.

    Absence of evidence never suppresses: an empty ``opp_axes`` (no vulnerability tags derived
    for that opponent) or an empty ``card_axes`` (card outside the catalog and un-derived)
    leaves the gate open with the reason naming which side was unknown.

    ``_hate`` is allowed against every opponent: ``_hate:<tag>`` pseudo-elements are keyed by
    the DECK's own vulnerability tags and weighted by field-wide interactive share — they carry
    no archetype key, so there is no per-opponent axis a ``_hate``-only card (Veil of Summer,
    Defense Grid, Carpet of Flowers) could be tested against.
    """
    if not opp_axes:
        return True, "opponent-axes-unknown"
    if not card_axes:
        return True, "card-axes-unknown"
    if card_axes & opp_axes:
        return True, "on-axis"
    if "_hate" in card_axes:
        return True, "hate-axis-field-wide"
    return False, "off-axis"


def _format_suppressed(entries: "tuple[tuple[str, float, str], ...]") -> str:
    """Render up to ``_SUPPRESSED_NOTE_CAP`` declined candidates plus a residual count."""
    if not entries:
        return ""
    shown = entries[:_SUPPRESSED_NOTE_CAP]
    parts = [f"{card} (lift {lift:+.3f}, {reason})" for card, lift, reason in shown]
    rest = len(entries) - len(shown)
    if rest > 0:
        parts.append(f"+{rest} more")
    return ", ".join(parts)


def format_plan_declines(plan: "MatchupPlan") -> str:
    """One-line summary of what a plan's eligibility gates declined, "" when nothing.

    Renderers emit this only when non-empty, so a plan that declined nothing renders
    byte-identically to the pre-feature output.
    """
    parts: list[str] = []
    out_s = _format_suppressed(plan.out_suppressed)
    if out_s:
        parts.append(f"OUT {out_s}")
    in_s = _format_suppressed(plan.in_suppressed)
    if in_s:
        parts.append(f"IN {in_s}")
    return "; ".join(parts)


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
    land_names: "frozenset[str] | None" = None,
    opponent_axes: "dict[str, frozenset[str]] | None" = None,
    card_axes: "dict[str, frozenset[str]] | None" = None,
) -> dict[str, MatchupPlan]:
    """Build per-opponent OUT/IN swap plans for the maindeck.

    For each opponent in ``opp_values``:

    - If ``not cleared_gate``: returns a degraded MatchupPlan (no OUT/IN, post_board
      == maindeck, explanatory note).
    - If ``cleared_gate``: builds a real OUT/IN plan:
        - Locked core: maindeck cards run by ≥ lock_threshold of the archetype's decks
          (from card_frequencies) — never sided out.  When archetype is None all
          maindeck cards are flex (degraded locked-core protection, noted).
        - Lands are exempt from the OUT pool.  Cutting lands from a 60-card maindeck is
          not a sideboard decision; it is what an unconstrained optimizer does when the
          locked core leaves nothing else unlocked.
        - Flex pool = maindeck − locked core − lands, computed on slot eligibility ALONE
          before any lift is read.  Empty flex pool → degraded ``no-legal-flex`` plan:
          no amount of data could produce a legal cut, so say that rather than
          manufacture one.
        - OUT candidates: flex-pool cards ranked ascending by matchup lift (most dead vs
          opponent first), only gate-clearing cards with lift ≤ 0, capped at max_swaps
          copies total.
        - IN candidates: sideboard_15 ranked descending by matchup lift, gate-clearing,
          lift > 0, AND attaching to an axis the opponent actually presents
          (``_in_axis_verdict``), capped at max_swaps copies total.
        - Pairs OUT[i] ↔ IN[i] up to min(available_out, available_in) copies.
        - Enforces legality: post_board sums to exactly 60; per-card copies ≤
          max(catalog max_copies, 4).  Illegal swaps are skipped (fewer swaps is
          always legal).
        - side_out and side_in must have equal total copies (a swap conserves 60).

    Eligibility inputs (``objective-search-split`` — resolved once by the caller, consumed
    as plain collections here):

    - ``land_names``: maindeck cards that are lands.  ``None`` → resolved from ``con`` via
      ``_resolve_land_names``.  There is deliberately no "no exemption" default: the land
      exemption is a correctness fix, not an opt-in overlay.
    - ``opponent_axes``: opponent archetype → its vulnerability tags.  ``None`` → the IN axis
      gate is inactive (the tags need a ``FieldDistribution`` only the caller holds).  A
      present-but-empty tag set for one opponent also leaves the gate open for that opponent —
      absence of evidence is not evidence of irrelevance.
    - ``card_axes``: card → the vulnerability tags it attacks.  Falls back to ``catalog``
      per card; a card with neither is un-assessable and passes the gate.

    Returns dict[opponent -> MatchupPlan].
    """
    if catalog is None:
        catalog = HOSER_CATALOG

    # Max copies limit: prefer catalog, fall back to 4
    def _max_copies_for(card: str) -> int:
        if card in catalog:
            return max(catalog[card].max_copies, 4)
        return 4

    def _axes_for(card: str) -> frozenset[str]:
        if card_axes is not None and card in card_axes:
            return card_axes[card]
        hoser = catalog.get(card)
        return frozenset(hoser.attacks) if hoser is not None else frozenset()

    if land_names is None:
        land_names = _resolve_land_names(con, deck_maindeck)

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

    # Structural flex pool: eligibility ALONE, computed once, before any lift is read.  Empty
    # here means no data could ever produce a legal cut — a degrade, not a "no dead cards"
    # answer.  Conflating the two is what let land cuts read as a real plan.
    flex_pool: frozenset[str] = frozenset(
        card for card, copies in deck_maindeck.items()
        if copies > 0 and card not in locked_core and card not in land_names
    )
    maindeck_land_count = sum(
        copies for card, copies in deck_maindeck.items()
        if copies > 0 and card in land_names
    )
    locked_maindeck_count = sum(
        1 for card, copies in deck_maindeck.items()
        if copies > 0 and card in locked_core
    )

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
                plan_status=_PLAN_STATUS_THIN_DATA,
            )
            continue

        # ── Compute OUT candidates ─────────────────────────────────────────
        # Gate + lift are read FIRST so out_suppressed records only signal-bearing declines
        # (a card the correlational signal actually favored cutting), not the whole locked core.
        out_candidates: list[tuple[str, float, int, str]] = []  # (card, lift, copies, tier)
        out_suppressed: list[tuple[str, float, str]] = []
        for card, cv in ov.maindeck.items():
            if cv.tier not in _VALUE_GATE:
                continue
            if cv.lift > 0:
                continue  # positive lift → keep it in
            copies_available = deck_maindeck.get(card, 0)
            if copies_available <= 0:
                continue
            if card in land_names:
                out_suppressed.append((card, cv.lift, "land"))
                continue
            if card in locked_core:
                out_suppressed.append((card, cv.lift, "locked-core"))
                continue
            out_candidates.append((card, cv.lift, copies_available, cv.tier))

        # Sort ascending by lift (most dead first); tie-break by card name for stability
        out_candidates.sort(key=lambda x: (x[1], x[0]))
        out_suppressed.sort(key=lambda x: (x[1], x[0]))

        # ── Compute IN candidates ──────────────────────────────────────────
        # Sideboard_15 cards that clear the gate, have lift > 0 vs this opponent, AND attach
        # to an axis this opponent presents.  Correlational lift alone boarded a Hydroblast
        # into a UB mirror; the axis check declines that without touching the ranking.
        opp_axis_set: frozenset[str] = (
            opponent_axes.get(opp, frozenset()) if opponent_axes is not None else frozenset()
        )
        in_candidates: list[tuple[str, float, int, str]] = []  # (card, lift, copies, tier)
        in_suppressed: list[tuple[str, float, str]] = []
        for card, cv in ov.side.items():
            if cv.tier not in _VALUE_GATE:
                continue
            if cv.lift <= 0:
                continue
            copies_available = sideboard_15.get(card, 0)
            if copies_available <= 0:
                continue
            allowed, reason = _in_axis_verdict(_axes_for(card), opp_axis_set)
            if not allowed:
                in_suppressed.append((card, cv.lift, reason))
                continue
            in_candidates.append((card, cv.lift, copies_available, cv.tier))

        # Sort descending by lift (best first)
        in_candidates.sort(key=lambda x: (-x[1], x[0]))
        in_suppressed.sort(key=lambda x: (-x[1], x[0]))

        out_suppressed_t = tuple(out_suppressed)
        in_suppressed_t = tuple(in_suppressed)

        if not flex_pool:
            # Honest degrade: the OUT pool is structurally empty, so no plan exists at this
            # consensus level.  Name both causes with counts and surface what was declined —
            # never a silent empty plan, never a fabricated cut.
            reasons = [
                (
                    f"{locked_maindeck_count} card(s) locked core "
                    f"(≥{lock_threshold:.0%} archetype adoption)"
                ),
                f"{maindeck_land_count} land slot(s) exempt from cuts",
            ]
            note = (
                f"vs {opp}: NO LEGAL FLEX — {'; '.join(reasons)}. No OUT/IN proposed; "
                f"the 15's composition carries this matchup"
            )
            declined = _format_suppressed(out_suppressed_t)
            if declined:
                note += f". Declined despite negative lift: {declined}"
            plans[opp] = MatchupPlan(
                opponent=opp,
                side_out={},
                side_in={},
                post_board=dict(deck_maindeck),
                n_basis=0,
                tier="speculative",
                degraded=True,
                note=note,
                plan_status=_PLAN_STATUS_NO_FLEX,
                out_suppressed=out_suppressed_t,
                in_suppressed=in_suppressed_t,
            )
            continue

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
            # Live flex pool, zero swaps — a real answer, not a degrade.  Name WHICH of the
            # three causes it was rather than the old "no dead cards (or no IN candidates)".
            if not out_candidates:
                status = _PLAN_STATUS_NO_DEAD_CARDS
                cause = "no flex maindeck card is dead vs this opponent"
            elif not in_candidates:
                status = _PLAN_STATUS_NO_IN
                cause = "no sideboard card clears the gate on an axis this opponent presents"
            else:
                status = _PLAN_STATUS_NO_LEGAL_SWAP
                cause = "every candidate pairing would break a copy limit"
            note = f"vs {opp}: data cleared gate but {cause}{lock_note}"
            declined_in = _format_suppressed(in_suppressed_t)
            if declined_in:
                note += f". Declined off-axis IN: {declined_in}"
            declined_out = _format_suppressed(out_suppressed_t)
            if declined_out:
                note += f". Declined OUT: {declined_out}"
            plans[opp] = MatchupPlan(
                opponent=opp,
                side_out={},
                side_in={},
                post_board=dict(deck_maindeck),
                n_basis=n_basis,
                tier=tier,
                degraded=False,
                note=note,
                plan_status=status,
                out_suppressed=out_suppressed_t,
                in_suppressed=in_suppressed_t,
            )
        else:
            lock_str = f"; locked={sorted(locked_core)}" if locked_core else lock_note
            note = (
                f"vs {opp}: {out_total} swap(s); "
                f"tier={tier}, n_basis={n_basis}{lock_str}"
            )
            declined_in = _format_suppressed(in_suppressed_t)
            if declined_in:
                note += f"; declined off-axis IN: {declined_in}"
            plans[opp] = MatchupPlan(
                opponent=opp,
                side_out=dict(side_out),
                side_in=dict(side_in),
                post_board=post_board,
                n_basis=n_basis,
                tier=tier,
                degraded=False,
                note=note,
                plan_status=_PLAN_STATUS_PLANNED,
                out_suppressed=out_suppressed_t,
                in_suppressed=in_suppressed_t,
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
                        and value tier; e.g. "covers graveyard-recursion (Dredge 18%)").
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
    option_value_bonus: "dict[str, float] | None" = None,
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
    option_value_bonus
        Optional card → CVaR tail-robustness bonus (feature-sfv-option-value; see
        ``_build_option_value_bonuses``), credited only when the card has zero copies in
        ``final_cards`` (a card already at some copies here is being evaluated for its NEXT
        copy, not its first). ``None``/empty → byte-identical to the pre-feature ranking.

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

        # feature-sfv-breadth-objective: canonical Σ-over-elements marginal gain (as if we
        # added one more copy) — same formula the greedy solver and hedge fill use.
        gain = _element_sum_marginal_gain(model, card_name, cov_counts)
        # feature-sfv-option-value: CVaR tail-robustness bonus, first copy only.
        if current_copies == 0 and option_value_bonus:
            gain += option_value_bonus.get(card_name, 0.0)
        # Elements this card would contribute residual value to. `_marginal_g(cov_e+1)` is
        # always > 0 (see its docstring), so this reduces exactly to "positive weight" —
        # matching the prior per-element `mg > 0.0` check without recomputing mg.
        residual_elements = {e for e in element_ids if model.element_weight.get(e, 0.0) > 0.0}

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
# Unit B5 (feature-sb-field-weighted-scorer-output): explainable per-card breakdown +
# coverage% diagnostic + Dirichlet field-share uncertainty.
#
# SCOPE: this unit is output/explainability/uncertainty-annotation ONLY. It does NOT touch
# `_build_coverage_model`'s element_weight computation (Units B1-B4, already wired + reviewed
# on main) — the ILP/greedy objective, and therefore which cards get recommended, is
# byte-identical before and after this unit. Everything below is computed from the ALREADY-
# SOLVED `final_cards` and is purely additive to `SideboardPackage`.
# ---------------------------------------------------------------------------

_BRITTLE_SHARE_SHRINK_RATIO = 0.5
"""A recommendation's reference matchup is flagged ``brittle`` when the Dirichlet
lower-quantile (risk-adjusted) share estimate for that archetype falls below this fraction
of its raw point-estimate share — i.e. the field's own share-uncertainty could plausibly cut
the matchup's true weight by half or more. This is the concrete, numeric form of "don't
over-commit a silver bullet to a noisy small-share matchup" (parent feature § commitments):
a genuinely well-sampled archetype's lower quantile sits close to its point estimate (ratio
~1.0) regardless of the raw share's size, so this only fires for THIN-count archetypes, not
merely small ones with plenty of backing data."""


def _relevant_field_archetypes(
    hoser: HoserCard,
    field: FieldDistribution,
    archetype_tags: "dict[str, frozenset[str]]",
) -> "frozenset[str]":
    """Field archetypes this hoser is meaningfully relevant against.

    "Relevant" = the hoser's ``attacks`` tags overlap the archetype's vulnerability tags —
    the same tag-overlap test ``_build_coverage_model`` uses to decide coverage, but recomputed
    here directly against ``field``/``archetype_tags`` (already-resolved, DB-free inputs) rather
    than the model's internal ``_archetype_tag_keys`` bookkeeping, so this helper works for any
    hoser independent of whether it ended up in the final solution.

    This is the "field coverage" axis from the feature's design input: "the share of the
    current field a card is meaningfully relevant against, summing field-shares of the
    archetypes it impacts" (e.g. "Null Rod hits ~26%"). Deliberately independent of
    ``opponent_linchpins`` — coverage% renders even when impact data (Unit B1-B4's per-opponent
    linchpin signal) is unavailable, since it needs only tags, not linchpins.

    Counter-hosers (``"_hate"`` in ``hoser.attacks``) never match here — no archetype carries
    the pseudo-tag ``"_hate"`` — so they correctly report 0% field coverage by this measure;
    their value is deck-protection, not archetype-targeted relevance, and is out of scope for
    this diagnostic.
    """
    return frozenset(
        arch
        for arch, tags in archetype_tags.items()
        if arch in field.shares and hoser.attacks & tags
    )


def _card_coverage_pct(
    hoser: HoserCard,
    field: FieldDistribution,
    archetype_tags: "dict[str, frozenset[str]]",
) -> float:
    """Σ field-share of archetypes this one hoser is relevant against (point estimate)."""
    return sum(
        field.shares[arch] for arch in _relevant_field_archetypes(hoser, field, archetype_tags)
    )


def _board_coverage_pct(
    final_cards: "dict[str, int]",
    candidate_meta: "dict[str, HoserCard]",
    field: FieldDistribution,
    archetype_tags: "dict[str, frozenset[str]]",
) -> float:
    """Σ field-share of archetypes the WHOLE recommended board is relevant against.

    Union across all recommended cards, not a sum of per-card coverage — an archetype
    double-covered by two cards (e.g. two graveyard hosers vs Reanimator) contributes its
    share once, not twice. This is a diagnostic headline number for the package as a whole,
    the board-level analogue of ``_card_coverage_pct``.
    """
    relevant: "set[str]" = set()
    for card_name in final_cards:
        hoser = candidate_meta.get(card_name)
        if hoser is None:
            continue
        relevant |= _relevant_field_archetypes(hoser, field, archetype_tags)
    return sum(field.shares.get(arch, 0.0) for arch in relevant)


def _dirichlet_share_lower_bound(
    field: FieldDistribution,
    *,
    quantile: float = _DEFAULT_RISK_QUANTILE,
    gamma: float = _DIRICHLET_GAMMA,
) -> "dict[str, float] | None":
    """Risk-adjusted (lower-quantile) field share per archetype.

    Reuses `advise positioning`'s Dirichlet field-share uncertainty model verbatim
    (``positioning._DIRICHLET_GAMMA`` for the Jeffreys pseudo-count, and the same
    ``_DEFAULT_RISK_QUANTILE`` positioning's own ``rank_decks`` uses to risk-adjust away from
    thin-data spikes) rather than reinventing a shrinkage scheme for this feature.

    Positioning treats the field share vector as ``w ~ Dirichlet(counts + gamma)`` and draws
    it jointly via Monte Carlo (``rng.dirichlet``) because it needs cross-archetype
    CORRELATION to produce an honest P(best) across competing decks (``_sample_S``). Nothing
    here needs that correlation — this function only needs a conservative bound on ONE
    archetype's share in isolation, so it uses the standard Dirichlet identity that each
    component's MARGINAL distribution is exactly ``Beta(alpha_i, alpha_0 - alpha_i)`` where
    ``alpha_i = counts[i] + gamma`` and ``alpha_0 = Σ alpha``. The lower quantile is then read
    off in closed form via ``scipy.stats.beta.ppf`` — deterministic and exact, no RNG/seed
    needed, and cheap enough to run on every ``recommend_sideboard`` call.

    A thin-count archetype's Beta marginal is wide, so its lower quantile sits well below its
    point share; a well-sampled archetype's marginal is tight, so its lower quantile sits close
    to its point share. This is the numeric form of "don't over-commit a silver bullet to a
    noisy small-share matchup" — see ``_BRITTLE_SHARE_SHRINK_RATIO``.

    Returns ``None`` when ``field.counts`` is ``None`` — a share-only custom field (built via
    ``build_custom_field`` without ``counts``) has no backing sample to build a posterior over,
    mirroring positioning's own "counts=None -> fixed point shares, no share-variance"
    contract. Callers should fall back to treating every share as fully-trusted (no shrink, no
    confidence gating) in that case.
    """
    if field.counts is None:
        return None

    archetypes = list(field.shares)
    if not archetypes:
        return {}

    alphas = {arch: field.counts.get(arch, 0) + gamma for arch in archetypes}
    alpha_total = sum(alphas.values())

    bounds: "dict[str, float]" = {}
    for arch in archetypes:
        alpha_i = alphas[arch]
        beta_i = alpha_total - alpha_i
        if beta_i <= 0:
            # Degenerate (single-archetype field): the Beta marginal collapses to a point
            # mass at 1.0 — no meaningful "lower bound" below the point share itself.
            bounds[arch] = field.shares[arch]
        else:
            bounds[arch] = float(_beta_dist.ppf(quantile, alpha_i, beta_i))
    return bounds


# ---------------------------------------------------------------------------
# Unit B6 (feature-sfv-option-value): CVaR-style tail-robustness option value.
#
# The submodular coverage objective above (Units B1-B4 + feature-sfv-breadth-objective's
# `_element_sum_marginal_gain`) already credits a card by its marginal coverage summed
# across every element it answers — but that sum is evaluated entirely at the field's
# POINT-ESTIMATE (mean) share. It has no notion that the field itself is uncertain: two
# cards with equal mean-field marginal gain are scored identically even when one of them
# only pays off if a single archetype shows up and the other pays off across many.
#
# This unit adds a SEPARATE, PURELY ADDITIVE axis: a per-card "option value" bonus that
# credits a card for retaining coverage value in the WORST-TAIL draws of the uncertain
# (Dirichlet) field, not just its mean — docs/briefs/scorer-flexibility-valuation.md §3.
# Computed ONCE per `recommend_sideboard` call (objective-search-split: the field/model
# inspection happens once, producing a plain `dict[str, float]`) and looked up by every
# consumer (`_greedy_solve`, `_hedge_fill`, `_rank_considering_pool`, `_ilp_solve`) via an
# `option_value_bonus` parameter — never recomputed inline, mirroring how
# `_element_sum_marginal_gain` itself became the single canonical home for breadth credit.
# ---------------------------------------------------------------------------

_DEFAULT_OPTION_VALUE_ALPHA: float = 0.7
"""Risk-appetite dial (brief §3): blends how much a card's option-value bonus leans on the
field's mean estimate vs. its worst-tail (Dirichlet lower-quantile) estimate. ``alpha=1.0``
means "tune entirely to the expected field" (bonus is always 0.0 — the documented disabled
path); a smaller ``alpha`` means "hedge more toward the field you fear" (the bonus grows
toward ``_OPTION_VALUE_SCALE * tail_share``). 0.7 is a conservative default, chosen by the
field-scoped `advise backtest` acceptance run (Dimir Tempo vs the Boulder field, see this
feature's design notes) so the bonus nudges ranking toward robust, multi-archetype cards
without moving the already-validated recommendation off the overlap it earned."""

_OPTION_VALUE_SCALE: float = 0.05
"""Swing-unit scale for the option-value bonus. NOTE the operating regime (2026-07-03 review):
on the real model the positive opponent element weights run ~0.0006-0.0135 (median ~0.0035)
after impact modulation, so a broad card's bonus (measured 0.0014-0.0125) is COMPARABLE to a
whole element's weight and 27-68% of its entire base marginal gain — a substantial re-ranking
force, not a small nudge relative to raw ``_SWING_SOFT``. The defaults (alpha=0.7, scale=0.05)
are justified EMPIRICALLY by the field-scoped ``advise backtest`` acceptance run (overlap
improved 5->6/7 with FoN held at 99.2%), not by an a-priori magnitude argument."""


def _dirichlet_group_lower_bound(
    field: FieldDistribution,
    archetypes: "frozenset[str] | set[str]",
    *,
    quantile: float = _DEFAULT_RISK_QUANTILE,
    gamma: float = _DIRICHLET_GAMMA,
) -> "float | None":
    """Closed-form Dirichlet AGGREGATE lower-quantile share for a GROUP of archetypes.

    Extends ``_dirichlet_share_lower_bound``'s single-archetype identity via the standard
    Dirichlet AGGREGATION property: the sum of any subset R of a Dirichlet's components is
    itself Beta-distributed, ``Beta(alpha_R, alpha_0 - alpha_R)`` where
    ``alpha_R = Σ_{a in R} (counts[a] + gamma)`` and ``alpha_0 = Σ_all (counts[a] + gamma)`` —
    the same closed-form machinery (``scipy.stats.beta.ppf``), summed over a SUBSET of
    categories before reading the quantile off, rather than over just one. Deterministic and
    exact — no RNG/seed, no Monte Carlo.

    This is the mechanism that makes a card's coverage of MANY archetypes worth more, in the
    tail, than treating each archetype's uncertainty independently would suggest: a Beta's
    coefficient of variation (std/mean) shrinks as its mean grows, for the SAME ``alpha_0``
    (``Var = mean·(1−mean)/(alpha_0+1)``, so relative spread scales like ``1/mean``). A group
    spanning several archetypes has a larger aggregate mean than any single member, so its
    lower-quantile retains a LARGER fraction of its mean than any individual member's
    lower-quantile retains of ITS mean — concretely, the group's tail share exceeds the SUM
    of the members' individually-computed tail shares. That is the closed-form expression of
    CVaR's subadditivity ("diversification never increases risk", brief §3
    ``[cvar-expected-shortfall]``): pooling many matchups one card can plausibly answer into
    a single aggregate need is safer, in the tail, than scoring each matchup's uncertainty
    alone — exactly the flexibility hedge this feature exists to value.

    Returns ``None`` when ``field.counts`` is ``None`` (no backing sample; mirrors
    ``_dirichlet_share_lower_bound``'s contract) or when ``archetypes`` is empty.
    """
    if field.counts is None or not archetypes:
        return None

    all_archetypes = list(field.shares)
    if not all_archetypes:
        return None

    alphas = {arch: field.counts.get(arch, 0) + gamma for arch in all_archetypes}
    alpha_total = sum(alphas.values())
    alpha_r = sum(alphas[a] for a in archetypes if a in alphas)
    if alpha_r <= 0.0:
        return 0.0
    beta_r = alpha_total - alpha_r
    if beta_r <= 0:
        # Degenerate: the group IS the entire field — no meaningful lower bound below the
        # point-estimate sum itself.
        return sum(field.shares.get(a, 0.0) for a in archetypes)
    return float(_beta_dist.ppf(quantile, alpha_r, beta_r))


def _card_covered_archetypes(model: "CoverageModel", card_name: str) -> "frozenset[str]":
    """Archetypes ``card_name`` has REAL (positively-weighted) coverage against.

    Deliberately derived from ``model.candidate_covers``/``model.element_weight`` — the
    model's OWN attachment computation — rather than re-testing ``hoser.attacks`` against
    ``archetype_tags`` the way ``_relevant_field_archetypes`` does for the coverage%
    diagnostic. That looser test can be True for an archetype the card is thematically
    relevant to even when NO element was ever created for it (e.g. no catalog hoser has
    positive swing for that specific tag) — using it here would let the option-value bonus
    credit a card with ZERO underlying coverage, manufacturing a pick out of pure
    field-relevance rather than rewarding an EXISTING coverage need's robustness. Restricting
    to the model's actual ``<archetype>|<tag>`` keys (skipping ``_hate:`` pseudo-elements,
    which carry no ``|``) guarantees the option-value bonus is exactly 0.0 whenever the
    card's mean-field marginal gain (``_element_sum_marginal_gain``) is also 0.0.
    """
    archetypes: set[str] = set()
    for key in model.candidate_covers.get(card_name, frozenset()):
        if "|" not in key:
            continue  # skip `_hate:` pseudo-elements
        if model.element_weight.get(key, 0.0) <= 0.0:
            continue  # no real coverage value on this element
        archetypes.add(key.split("|", 1)[0])
    return frozenset(archetypes)


def _build_option_value_bonuses(
    model: "CoverageModel",
    field: FieldDistribution,
    *,
    alpha: float = _DEFAULT_OPTION_VALUE_ALPHA,
    quantile: float = _DEFAULT_RISK_QUANTILE,
    gamma: float = _DIRICHLET_GAMMA,
    scale: float = _OPTION_VALUE_SCALE,
) -> "dict[str, float]":
    """Pure-mechanics CVaR tail-robustness bonus, one scalar per candidate card.

    ``bonus(card) = (1 - alpha) * scale * tail_share(_card_covered_archetypes(card))`` where
    ``tail_share`` is the closed-form Dirichlet GROUP lower-quantile above. Always ``>= 0.0``
    — a bonus, never a penalty — and is added ON TOP of the existing mean-field marginal-gain
    sum, never substituted for it, so a card's already-validated mean-field coverage value is
    preserved intact; only the RELATIVE ranking among candidates shifts, toward cards whose
    EXISTING coverage is robust to field uncertainty. A card with zero real coverage
    (``_card_covered_archetypes`` empty) always gets bonus 0.0 — this term can never promote a
    card with ZERO covered archetypes into the board (empty covered set -> bonus 0.0 — the
    hard guardrail against manufacturing picks from field-relevance alone). It CAN, however,
    add an already-covering card whose residual coverage gain is saturated to ~0 (redundant
    coverage) purely on its static first-copy bonus — observed: the recommended board grows
    6->9 cards when the term turns on. That is intended "flexible insurance" behavior
    (brief §4's one-of insurance thesis), but it means the term adds cards, not just re-ranks.

    Zero-mechanics, no empirical winning-board input (epic guardrail): the only inputs are
    the field's own Dirichlet posterior (``field.counts``/``field.shares``) and the model's
    own already-computed attachment (``candidate_covers``/``element_weight``) — no new data
    source, no empirical adoption signal.

    Counter-hosers (``"_hate"`` in ``hoser.attacks``) are excluded — self-protection is not a
    "which matchup will I face" hedge; it is a different axis, already made coverable by
    feature-sfv-weights' ``_hate:`` pseudo-elements.

    Returns ``{}`` (every consumer's ``.get(card, 0.0)`` then no-ops, byte-identical to the
    pre-feature objective) when disabled (``alpha >= 1.0``) or when the field carries no
    backing counts (``field.counts is None``, e.g. a share-only custom field).
    """
    if alpha >= 1.0 or field.counts is None:
        return {}

    bonuses: "dict[str, float]" = {}
    for card_name, hoser in model.candidate_meta.items():
        if "_hate" in hoser.attacks:
            continue
        covered = _card_covered_archetypes(model, card_name)
        if not covered:
            continue
        tail_share = _dirichlet_group_lower_bound(field, covered, quantile=quantile, gamma=gamma)
        if tail_share is None or tail_share <= 0.0:
            continue
        bonus = (1.0 - alpha) * scale * tail_share
        if bonus > 0.0:
            bonuses[card_name] = bonus
    return bonuses


@dataclass(frozen=True)
class CardImpactAnnotation:
    """Per-recommended-card explainability + honest-uncertainty annotation (Unit B5).

    ``breakdown``: the ``ImpactBreakdown`` (centrality/symmetry/castability/draw_prob) computed
        for this card against ``reference_archetype`` at its ACTUAL recommended copy count —
        so the pilot can audit exactly why the card scored the way it did, factor by factor.
    ``reference_archetype``: the highest-field-share opponent archetype this card's ``attacks``
        tags actually address. Impact is inherently per-(card, opponent) — never a flat score
        (see ``advisory.impact`` module docstring) — so one concrete anchor matchup is chosen
        rather than averaging across unrelated archetypes into a meaningless composite. The
        highest-share relevant archetype is the most consequential single matchup to audit.
    ``reference_share``: that archetype's point-estimate field share (for display context).
    ``confidence``: ``tier_for_sample(field.counts[reference_archetype])`` — ``None`` when the
        field carries no backing counts at all (share-only custom field; honestly "no data" is
        distinct from a graded tier, never silently defaulted to a tier).
    ``brittle``: True when the Dirichlet lower-quantile share estimate for
        ``reference_archetype`` falls below ``_BRITTLE_SHARE_SHRINK_RATIO`` of its point share —
        this card's coverage leans on a thin-count matchup whose true weight the field's own
        uncertainty could materially cut. False (never fabricated True) when ``field.counts``
        is unavailable — the flag requires backing counts to compute honestly.
    """

    breakdown: "ImpactBreakdown"
    reference_archetype: str
    reference_share: float
    confidence: "ConfidenceLevel | None"
    brittle: bool


def _build_impact_annotations(
    final_cards: "dict[str, int]",
    candidate_meta: "dict[str, HoserCard]",
    field: FieldDistribution,
    archetype_tags: "dict[str, frozenset[str]]",
    opponent_linchpins: "dict[str, list[Linchpin]] | None",
    opponent_cards: "dict[str, dict[str, int]] | None",
    deck_colors: "frozenset[str]",
    deck_tags: "frozenset[str]",
) -> "dict[str, CardImpactAnnotation]":
    """Build the per-card ``CardImpactAnnotation`` map for the FINAL recommended cards.

    Gated on ``opponent_linchpins is not None`` — the same gate ``_build_coverage_model``
    (Unit B3) already uses to decide whether real per-opponent linchpin data was found for
    this field. When it's None, no per-card breakdown is fabricated: the no-impact-data path
    returns ``{}`` (nothing to render), consistent with the honest-degrade convention of never
    showing a number that wasn't actually computed from data.

    Counter-hosers (``"_hate"`` in ``hoser.attacks``) and cards with zero relevant field
    archetypes are skipped — impact is defined per-(card, opponent), and neither has a single
    coherent opponent to anchor a breakdown to.

    Uses each card's ACTUAL recommended copy count (not a fixed ``copies=1`` like Unit B3's
    element-weight computation) — this is a display-only recomputation, so it can afford to
    show the more informative, copy-count-accurate draw probability without affecting the
    (already-solved, unchanged) objective.
    """
    if opponent_linchpins is None:
        return {}

    conservative_shares = _dirichlet_share_lower_bound(field)

    annotations: "dict[str, CardImpactAnnotation]" = {}
    for card_name, copies in final_cards.items():
        hoser = candidate_meta.get(card_name)
        if hoser is None or "_hate" in hoser.attacks:
            continue

        relevant = _relevant_field_archetypes(hoser, field, archetype_tags)
        if not relevant:
            continue

        reference_archetype = max(relevant, key=lambda arch: field.shares.get(arch, 0.0))
        reference_share = field.shares.get(reference_archetype, 0.0)

        opp_lps = opponent_linchpins.get(reference_archetype, [])
        opp_cards_for_arch = (
            opponent_cards.get(reference_archetype) if opponent_cards else None
        )
        breakdown = _compute_impact(
            hoser,
            reference_archetype,
            opp_linchpins=opp_lps,
            my_vulnerability_tags=deck_tags,
            my_colors=deck_colors,
            copies=copies,
            opp_cards=opp_cards_for_arch,
        )

        confidence: "ConfidenceLevel | None" = None
        brittle = False
        if field.counts is not None:
            confidence = tier_for_sample(field.counts.get(reference_archetype, 0))
        if (
            conservative_shares is not None
            and reference_share > 0.0
            and conservative_shares.get(reference_archetype, 0.0) / reference_share
            < _BRITTLE_SHARE_SHRINK_RATIO
        ):
            brittle = True

        annotations[card_name] = CardImpactAnnotation(
            breakdown=breakdown,
            reference_archetype=reference_archetype,
            reference_share=reference_share,
            confidence=confidence,
            brittle=brittle,
        )
    return annotations


# ---------------------------------------------------------------------------
# Units D1+D2: Slot-ROI table + punt detection (feature-sb-slot-roi-punt)
# ---------------------------------------------------------------------------
# ADDITIVE decision-support layer on top of the already-solved coverage model + field's
# matchup matrix. Answers "is dedicating sideboard slots to matchup X worth it, or would
# those slots buy more expected wins moved elsewhere?" — a slot-ALLOCATION question above
# per-card scoring. Does NOT touch card selection: `_slot_roi_table` is a pure function of
# already-resolved inputs (field, matchup matrix, coverage model) and never mutates or
# re-derives `final_cards`.
#
# max_equity_gain deliberately REUSES the coverage model's own concave per-copy shaping
# (`_u_redundancy`, Unit B4's draw-probability-derived curve) rather than a fresh curve, so
# this layer's ROI numbers are consistent with what the solver can actually buy — the risk
# called out in the parent feature's "Risks" section (a divergent curve would misinform).

# Number of dedicated copies the realistic-ceiling projection sums over. Matches the length
# of `_U_REDUNDANCY_DEFAULT` (copies beyond it clamp to the curve's last, near-zero entry via
# `_u_redundancy`, so summing further would add negligible value anyway).
_MAX_DEDICATED_SLOTS: int = len(_U_REDUNDANCY_DEFAULT)

# Hard ceiling on any single matchup's projected max_equity_gain — mirrors
# `_EMPIRICAL_SWING_CAP`'s role elsewhere as a sanity bound against an unrealistic swing
# estimate dominating the advice (e.g. a single high-swing hoser stacked with a large field
# share should not imply an implausible double-digit equity swing).
_MAX_REALISTIC_EQUITY_GAIN: float = 0.35

# Reallocation-punt margin (Unit D2, condition b). A matchup's first-slot ROI must fall
# BELOW this fraction of the best viable (crosses_half) alternative's ROI elsewhere in the
# field before it is flagged for reallocation. A literal "not strictly the top-ranked
# matchup" test would flag every matchup but the single best one, which is not useful
# decision support (real boards legitimately hedge across several matchups) — this requires
# a MEANINGFUL gap: the slot here buys less than half the expected match-wins available
# elsewhere.
_REALLOCATION_MARGIN: float = 0.5

# Punt reason labels (rendered verbatim by `advise sideboard`'s slot-ROI block).
_PUNT_REASON_CANT_CROSS_HALF = "max dedication still <50%"
_PUNT_REASON_BETTER_ROI_ELSEWHERE = "better ROI elsewhere"

# Minimum field share for a matchup to earn a slot-ROI row at all. Mirrors the same 1%
# noise-floor threshold `recommend_sideboard` already applies when scanning opponents for
# data-informed swing overrides ("skip negligible-share opponents to avoid noise") — a
# real field distribution can carry a long tail of hundreds of near-zero-share archetypes
# (rounding error / one-off registrations), and a slot-allocation decision-support table is
# not useful, and actively noisy, if it lists all of them.
_MIN_FIELD_SHARE_FOR_ROI: float = 0.01


@dataclass(frozen=True)
class MatchupROI:
    """Decision-support record: is dedicating sideboard slots to ``opponent`` worth it?

    ``opponent``: field archetype.
    ``field_share``: this opponent's share of the expected field.
    ``base_equity``: matchup cell ``p_shrunk`` (pre-board) vs the deck's own archetype.
        Honest-degrade: ``0.5`` when the cell is thin (``speculative`` tier) or absent
        entirely (no matrix, archetype not in the matrix, or an unobserved pair) — see
        ``confidence``.
    ``max_equity_gain``: realistic ceiling on how far dedicating slots can move
        ``base_equity``, reusing the coverage model's own concave swing × ``_u_redundancy``
        per-copy shaping (Unit B4) so this number is consistent with what the solver can
        actually buy. Capped at ``_MAX_REALISTIC_EQUITY_GAIN``. ``0.0`` when no catalog
        candidate answers any tag of this opponent.
    ``roi_per_slot``: the FIRST dedicated slot's marginal equity gain × ``field_share`` —
        the expected-match-win unit this table ranks by (comparable across matchups).
    ``crosses_half``: whether ``base_equity + max_equity_gain >= 0.5`` — whether max
        realistic dedication is enough to flip this matchup favorable.
    ``punt``: True when investment doesn't pay (Unit D2). HARD RULE: never True when
        ``confidence == "speculative"`` — a thin/absent cell is labeled low-confidence
        instead of used to recommend conceding a matchup on noise.
    ``confidence``: tier sourced from the matchup cell (``tier_for_sample`` semantics via
        ``MatchupCell.tier``); ``"speculative"`` for the honest-degrade branch.
    ``punt_reason``: human-readable reason when ``punt`` is True; ``""`` otherwise.
    """

    opponent: str
    field_share: float
    base_equity: float
    max_equity_gain: float
    roi_per_slot: float
    crosses_half: bool
    punt: bool
    confidence: "ConfidenceLevel | None"
    punt_reason: str = ""


def _matchup_max_equity_gain(
    opponent: str,
    field_share: float,
    coverage_model: "CoverageModel",
) -> "tuple[float, float]":
    """Realistic ceiling + first-slot marginal gain for dedicating slots vs ``opponent``.

    Recovers the per-copy equity swing the coverage model actually assigned to this
    opponent's best-covered ``(archetype, tag)`` element: ``element_weight`` there is
    already ``field_share × swing × impact_multiplier`` (Unit B3), so dividing back out
    ``field_share`` yields the per-copy equity value the solver itself would realize for
    the FIRST copy answering this opponent — not a re-derived heuristic. Multiple dedicated
    copies are shaped by the SAME concave ``_u_redundancy`` curve the solver uses for
    per-card-copy diminishing returns (Unit B4), summed over ``_MAX_DEDICATED_SLOTS``
    copies and capped at ``_MAX_REALISTIC_EQUITY_GAIN``.

    Returns ``(max_equity_gain, first_slot_gain)``. Both are ``0.0`` when
    ``field_share <= 0`` (nothing to divide by; a zero-share matchup has no ROI) or when the
    coverage model has no candidate covering any tag of ``opponent`` (an honest "we can't
    do anything about this matchup" — distinct from, and a stronger signal than, a punt).
    """
    if field_share <= 0.0:
        return 0.0, 0.0
    prefix = f"{opponent}|"
    opp_weights = [
        w for key, w in coverage_model.element_weight.items() if key.startswith(prefix)
    ]
    if not opp_weights:
        return 0.0, 0.0
    per_copy_equity = max(opp_weights) / field_share
    first_slot_gain = per_copy_equity * _u_redundancy(1)  # _u_redundancy(1) == 1.0 always
    cumulative = sum(
        per_copy_equity * _u_redundancy(k) for k in range(1, _MAX_DEDICATED_SLOTS + 1)
    )
    max_equity_gain = min(cumulative, _MAX_REALISTIC_EQUITY_GAIN)
    return max_equity_gain, first_slot_gain


def _slot_roi_table(
    deck_archetype: "str | None",
    field: FieldDistribution,
    matchup_matrix: "object | None",
    coverage_model: "CoverageModel",
) -> "list[MatchupROI]":
    """Per-field-matchup slot ROI + punt detection (Units D1+D2, feature-sb-slot-roi-punt).

    Pure given resolved inputs — no DB access. Reads the ALREADY-BUILT ``coverage_model``
    (so ``max_equity_gain`` matches what the solver can actually buy) and the field's own
    matchup matrix for base equities; never touches card selection.

    ``matchup_matrix`` accepts a plain ``MatchupMatrix``, the ``AdaptiveMatrix`` wrapper
    returned by ``build_adaptive_matrix`` (its ``.matrix`` is unwrapped automatically), or
    ``None`` — which degrades every matchup to the absent-cell honest-degrade branch
    (``base_equity=0.5``, ``confidence="speculative"``).

    Mirror matches (``opponent == deck_archetype``) and negligible-share field entries
    (below ``_MIN_FIELD_SHARE_FOR_ROI``, 1%) are skipped — there is no meaningful "hose the
    mirror" question for this layer, and a real field's long tail of near-zero-share
    archetypes would otherwise make the table noise rather than decision support.

    Unit D2 punt rules (evaluated only for non-``speculative`` rows — the hard rule below):
      (a) ``not crosses_half`` — max realistic dedication still can't reach 50%.
      (b) this matchup's ``roi_per_slot`` is below ``_REALLOCATION_MARGIN`` of the best
          OTHER matchup's ``roi_per_slot`` among matchups that themselves ``crosses_half``
          (a genuinely investable alternative, not just a theoretically higher number).

    HARD RULE: ``confidence == "speculative"`` (thin/absent cell) never punts — it is
    labeled low-confidence instead, per the parent feature's explicit risk mitigation
    against conceding a matchup on noise.

    Returns rows sorted by ``roi_per_slot`` descending; ``[]`` when ``deck_archetype`` is
    ``None`` or the field is empty.
    """
    if deck_archetype is None or not field.shares:
        return []

    # Unwrap AdaptiveMatrix (.matrix) without importing the type — avoids a hard dependency
    # on analytics.matchup's wrapper class for callers that pass a plain MatchupMatrix.
    matrix = getattr(matchup_matrix, "matrix", matchup_matrix)

    rows: list[MatchupROI] = []
    for opponent, share in field.shares.items():
        if opponent == deck_archetype or share < _MIN_FIELD_SHARE_FOR_ROI:
            continue

        cell = lookup_head_to_head(matrix, deck_archetype, opponent) if matrix is not None else None
        confidence: "ConfidenceLevel | None"
        if cell is None or cell.tier == "speculative":
            base_equity = 0.5
            confidence = "speculative"
        else:
            base_equity = cell.p_shrunk if cell.p_shrunk is not None else 0.5
            confidence = cell.tier

        max_gain, first_slot_gain = _matchup_max_equity_gain(opponent, share, coverage_model)
        crosses_half = (base_equity + max_gain) >= 0.5

        rows.append(
            MatchupROI(
                opponent=opponent,
                field_share=share,
                base_equity=base_equity,
                max_equity_gain=max_gain,
                roi_per_slot=first_slot_gain * share,
                crosses_half=crosses_half,
                punt=False,  # resolved below, once every row's crosses_half is known
                confidence=confidence,
            )
        )

    # --- Unit D2: punt detection (needs the full ranked set for condition (b)) ---
    resolved: list[MatchupROI] = []
    for row in rows:
        punt = False
        reason = ""
        if row.confidence != "speculative":  # hard rule: never punt on thin/absent data
            if not row.crosses_half:
                punt = True
                reason = _PUNT_REASON_CANT_CROSS_HALF
            else:
                best_other = max(
                    (
                        r.roi_per_slot
                        for r in rows
                        if r.opponent != row.opponent and r.crosses_half
                    ),
                    default=0.0,
                )
                if best_other > 0.0 and row.roi_per_slot < best_other * _REALLOCATION_MARGIN:
                    punt = True
                    reason = _PUNT_REASON_BETTER_ROI_ELSEWHERE
        resolved.append(_dc_replace(row, punt=punt, punt_reason=reason))

    resolved.sort(key=lambda r: r.roi_per_slot, reverse=True)
    return resolved


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
    plan_window_label: str = ""                              # "" = not set; "adaptive (per-opponent era-aware)" in adaptive mode (epic-stable-era-windows-mixed-horizon-consumers: resolved via analytics.eras.consume.era_horizons, the same adapter build_adaptive_matrix uses — honest-degrades to the pre-epic ban-only archetype_valid_since window when there is no era data)
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
    # --- Additive fields (feature-sb-field-weighted-scorer-output, Unit B5) ---
    # Explainable per-card breakdown + honest field-share uncertainty annotation. Empty/0.0
    # defaults are the byte-identical no-op path (matches every other gated-additive field
    # above): a caller ignoring these fields sees no change; recommend_sideboard only
    # populates them when the underlying data (impact linchpins / field counts) exists.
    # impact_annotations: card -> CardImpactAnnotation (ImpactBreakdown + reference opponent +
    #   confidence tier + brittle flag). Empty dict when opponent_linchpins was None (no
    #   per-opponent impact data available) — never a fabricated breakdown.
    # board_coverage_pct / card_coverage_pct: the coverage% DIAGNOSTIC (locked decision: a
    #   relevance number, NOT the optimization objective) — Σ field-share of archetypes the
    #   board/card is meaningfully relevant against (union at board level, per-card at card
    #   level). Always computed (needs only tags, independent of impact-data availability).
    impact_annotations: "dict[str, CardImpactAnnotation]" = dc_field(default_factory=dict)
    board_coverage_pct: float = 0.0
    card_coverage_pct: "dict[str, float]" = dc_field(default_factory=dict)
    # --- Additive field (feature-sb-slot-roi-punt, Units D1+D2+D3) ---
    # slot_roi: per-field-matchup decision-support table (see `_slot_roi_table`) — ranked by
    # roi_per_slot desc, with punt flags for matchups where dedicating slots doesn't pay.
    # DECISION SUPPORT ONLY: computed from the field + matchup matrix + the already-built
    # coverage model; never fed back into card selection. Empty tuple when `archetype` was
    # not supplied to `recommend_sideboard` or matrix/model construction failed — an honest
    # "not computed", never a fabricated table.
    slot_roi: "tuple[MatchupROI, ...]" = dc_field(default_factory=tuple)


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
    # Smart-mode master switch (epic-sideboard-core-and-hedge-gating): when True, derive
    # field-scale-invariant defaults for redundancy_strength/tau from the model's coverage
    # scale (an explicit non-zero redundancy_strength/tau still wins). False → no derivation;
    # with the strengths at their 0.0 defaults this is byte-identical to the forced-15 baseline.
    smart: bool = False,
    # Hedge mode (epic-sideboard-core-and-hedge-hedge-allocator): "off" (default) | "expected".
    # When "expected", leftover slots the core left open (τ stopped it short of budget) are
    # filled with diversity-preferring insurance picks over a uniform-widened field. "off" → no
    # hedge → byte-identical.
    hedge: str = "off",
    # CVaR tail-robustness risk-appetite dial (feature-sfv-option-value, brief §3):
    # alpha=1.0 tunes the objective purely to the field's mean (point-estimate) share — the
    # documented byte-identical no-op. Smaller alpha credits cards more for coverage that
    # survives the field's own worst-tail (Dirichlet lower-quantile) draws, on top of (never
    # instead of) the existing mean-field marginal-gain sum. Default 0.7 is ON by default
    # (this IS the epic's shipped mechanism, not an opt-in experiment) — see
    # `_DEFAULT_OPTION_VALUE_ALPHA`'s docstring for the backtest-driven calibration rationale.
    # No-ops automatically (bonus map is `{}`) when the field carries no backing counts
    # (`field.counts is None`, e.g. a share-only custom field) — nothing here fabricates
    # Dirichlet uncertainty that isn't actually backed by a sample.
    option_value_alpha: float = _DEFAULT_OPTION_VALUE_ALPHA,
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

    # Fix B: build per-opponent adaptive windows, resolved via the SAME era-horizon adapter
    # build_adaptive_matrix uses (epic-stable-era-windows-mixed-horizon-consumers): one horizon
    # source per recommendation, rather than this surface staying on the pre-epic ban-only
    # `archetype_valid_since` while the slot-ROI matrix below (`build_adaptive_matrix`) already
    # reads era-aware `stable_since` horizons. `era_horizons` honest-degrades to the identical
    # `archetype_valid_since` ban-only fallback when `entity_eras` has no data at all (its
    # ban-only branch calls the very same function with the same arguments — see
    # `analytics.eras.consume.era_horizons`), so this is BYTE-IDENTICAL to the pre-epic behavior
    # until `eras run` actually populates era data. Pool each opponent's window back to
    # max(valid_since[deck_arch], valid_since[opp]).
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
            from legacy_engine.analytics.eras.consume import era_horizons
            all_archetypes_to_check = list({archetype, *_top_opponents})
            horizon_meta, _era_audit = era_horizons(con, all_archetypes_to_check)
            valid_since_map = {a: h.since for a, h in horizon_meta.items()}
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
            plan_window_label = "adaptive (per-opponent era-aware)"
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

    # --- Step 3f: Opponent linchpins + composition (feature-sb-field-weighted-scorer-wiring,
    # Unit B3) ---
    # Computed ONCE here (objective-search-split) and threaded into _build_coverage_model so
    # its impact-modulated element weights stay a pure/DB-free computation. Gated: stays None
    # (byte-identical element weights) unless at least one field archetype yields real linchpin
    # data — derived from in-regime corpus composition, or a curated LINCHPIN_OVERRIDES entry
    # (checked even when the corpus has no decks for that archetype) — mirrors the
    # any_gate_cleared gating already used for matchup_pressure above.
    opponent_linchpins: "dict[str, list[Linchpin]] | None" = None
    opponent_cards: "dict[str, dict[str, int]] | None" = None
    try:
        _linchpins_by_arch, _cards_by_arch = _field_opponent_linchpins(
            con, field, since=eff_since, until=eff_until
        )
        if any(_linchpins_by_arch.values()):
            opponent_linchpins = _linchpins_by_arch
            opponent_cards = _cards_by_arch
            log.debug(
                "recommend_sideboard: opponent linchpin data for %d/%d field archetypes",
                sum(1 for lps in _linchpins_by_arch.values() if lps), len(_linchpins_by_arch),
            )
    except Exception as exc:
        log.debug("recommend_sideboard: _field_opponent_linchpins failed: %s", exc)

    # --- Step 3g: Maindeck-aware coverage discount (feature-sb-maindeck-aware-coverage,
    # Unit C1) ---
    # Computed ONCE here from the already-resolved deck_card_objects (objective-search-split
    # — no extra DB round-trip inside the pure _maindeck_answer_coverage loop) and threaded
    # into _build_coverage_model so it can discount element weights for axes the maindeck
    # itself already answers (e.g. 4 maindeck Wasteland -> "nonbasic-manabase"). Empty when the
    # deck answers no tracked vulnerability tags -> _build_coverage_model no-ops (byte-identical).
    _card_by_name: "dict[str, Card]" = {card.name: card for card in deck_card_objects}
    maindeck_coverage = _maindeck_answer_coverage(
        deck_maindeck, _card_by_name.get, catalog=catalog
    )

    # --- Step 3h: 4-of legality caps (epic-sb-advisor-correctness-fourof-guard) ---
    # Resolved from the same already-fetched deck_card_objects. Threaded into
    # _build_coverage_model so a card the maindeck already runs 4 of can never be offered
    # as a 5th copy by the solver OR the considering pool.
    maindeck_copy_caps = _maindeck_copy_caps(deck_maindeck, _card_by_name.get)

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
        opponent_linchpins=opponent_linchpins,
        opponent_cards=opponent_cards,
        maindeck_coverage=maindeck_coverage,
        maindeck_copy_caps=maindeck_copy_caps,
    )
    warnings.extend(model.warnings)

    # --- Step 4a: CVaR tail-robustness option-value bonuses (feature-sfv-option-value) ---
    # Computed ONCE from the already-built model + field (objective-search-split): a plain
    # card -> bonus dict every solver below looks up via `option_value_bonus`. `{}` when
    # `option_value_alpha >= 1.0` or `field.counts is None` (share-only custom field) —
    # byte-identical to the pre-feature objective in both cases.
    option_value_bonus = _build_option_value_bonuses(
        model, field, alpha=option_value_alpha,
    )

    # --- Step 4b: Slot-ROI + punt table (feature-sb-slot-roi-punt, Units D1+D2) ---
    # ADDITIVE decision-support layer: consumes the coverage model just built above (so its
    # max_equity_gain matches what the solver can actually buy) + a freshly-built adaptive
    # matchup matrix for base equities. Computed here — before the solver runs — because it
    # is a pure function of (archetype, field, matrix, model) and does NOT depend on, or
    # feed back into, final_cards. Gated on `archetype` (need a "my side" to look up matchup
    # cells for) and degrades to `[]` (never a fabricated table) on any matrix-build failure
    # (e.g. a rounds-less corpus) — every row inside `_slot_roi_table` already honest-degrades
    # per-cell, but the matrix build itself can raise on a schema-less/absent `rounds` table.
    slot_roi: "tuple[MatchupROI, ...]" = ()
    if archetype is not None:
        try:
            from legacy_engine.analytics.matchup import build_adaptive_matrix
            _adaptive_matrix = build_adaptive_matrix(con)
            slot_roi = tuple(_slot_roi_table(archetype, field, _adaptive_matrix, model))
        except Exception as exc:
            log.debug("recommend_sideboard: slot-ROI table failed: %s", exc)
            slot_roi = ()

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
            slot_roi=slot_roi,
        )

    # --- Smart-mode calibration (epic-sideboard-core-and-hedge-gating) ---
    # Derive field-scale-invariant redundancy_strength/τ from the model's coverage scale.
    # Explicit non-zero values always win (power users / tests). When smart is off and the
    # strengths are 0.0 (defaults), this is a no-op → byte-identical forced-15 baseline.
    if smart:
        _scale = _coverage_scale(model)
        if redundancy_strength <= 0.0:
            redundancy_strength = _SMART_REDUNDANCY_FRACTION * _scale
        if tau <= 0.0:
            tau = _SMART_TAU_FRACTION * _scale

    # --- Step 5 + 6: Solve and always compute greedy trace ---
    solver_used = "greedy"
    ilp_cards: dict[str, int] = {}

    if solver == "ilp":
        try:
            ilp_cards = _ilp_solve(
                model, budget=budget, redundancy_strength=redundancy_strength, tau=tau,
                option_value_bonus=option_value_bonus,
            )
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
    greedy_cards, greedy_trace = _greedy_solve(
        model, budget=budget, redundancy_strength=redundancy_strength, tau=tau,
        option_value_bonus=option_value_bonus,
    )

    # Choose final cards based on solver
    final_cards = ilp_cards if solver_used == "ilp" else greedy_cards

    # --- Hedge fill (epic-sideboard-core-and-hedge-hedge-allocator, fast-follow) ---
    # The core above may have stopped short of the budget (τ). When hedge="expected", fill the
    # leftover slots with diversity-preferring insurance picks over a uniform-widened field.
    # "off" → no change → byte-identical. natural_budget_count below reflects the CORE size.
    _core_count = sum(final_cards.values())
    _insurance: dict[str, int] = {}
    if hedge == "expected":
        _insurance = _hedge_fill(model, final_cards, budget=budget, option_value_bonus=option_value_bonus)
        for _c, _n in _insurance.items():
            final_cards[_c] = final_cards.get(_c, 0) + _n

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
            # Eligibility inputs, resolved once here (objective-search-split): the land set
            # costs one type_line query; the opponent axis sets and the card→attacks map are
            # already in hand from Step 3 and the catalog/promotion pass.
            _plan_land_names = _resolve_land_names(con, deck_maindeck)
            _plan_card_axes: dict[str, frozenset[str]] = {
                name: frozenset(hoser.attacks) for name, hoser in catalog.items()
            }
            if promoted_candidates:
                _plan_card_axes.update(
                    {name: frozenset(hoser.attacks)
                     for name, hoser in promoted_candidates.items()}
                )
            matchup_plans = _plan_matchups(
                con, deck_maindeck, final_cards, opp_values_final, archetype,
                max_swaps=max_swaps,
                since=eff_since,
                until=eff_until,
                catalog=catalog,
                adaptive_windows=computed_adaptive_windows,
                land_names=_plan_land_names,
                opponent_axes=archetype_tags,
                card_axes=_plan_card_axes,
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
        model, final_cards, promoted_names=_promoted_names,
        option_value_bonus=option_value_bonus,
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
    if redundancy_strength > 0.0 or tau > 0.0 or _insurance:
        # natural_budget_count is the DEDICATED CORE size (excludes hedge/insurance picks).
        _natural_budget_count = _core_count
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

    # --- Step 6e: Explainable breakdown + coverage% diagnostic + field-share uncertainty
    # (feature-sb-field-weighted-scorer-output, Unit B5) ---
    # Purely additive/derived from the ALREADY-SOLVED final_cards; does not affect the
    # objective, solver_used, or which cards were picked (see Unit B5's module-level scope
    # note above `_relevant_field_archetypes`).
    _impact_annotations = _build_impact_annotations(
        final_cards,
        model.candidate_meta,
        field,
        archetype_tags,
        opponent_linchpins,
        opponent_cards,
        deck_colors,
        deck_tags,
    )
    _board_coverage = _board_coverage_pct(final_cards, model.candidate_meta, field, archetype_tags)
    _card_coverage = {
        card_name: _card_coverage_pct(hoser, field, archetype_tags)
        for card_name, hoser in model.candidate_meta.items()
        if card_name in final_cards
    }

    # --- Step 6f: 4-of legality post-check (epic-sb-advisor-correctness-fourof-guard) ---
    # Backstop over the ALREADY-SOLVED final_cards. The candidate cap should make this
    # unreachable; if it ever fires, the board is format-illegal and the user is told so
    # explicitly rather than shipping a silently illegal list.
    warnings.extend(
        _fourof_legality_warnings(final_cards, deck_maindeck, _card_by_name.get)
    )

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
        slot_roi=slot_roi,
        insurance_cards=frozenset(_insurance),  # hedge picks (commit = the rest)
        impact_annotations=_impact_annotations,
        board_coverage_pct=_board_coverage,
        card_coverage_pct=_card_coverage,
    )
