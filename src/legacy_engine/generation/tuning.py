"""Field-tuning for deck generation (mode 2) — rework (2026-05-31).

Optimises a consensus (or user-supplied) 60+15 shell against the current or
projected field by swapping flexible maindeck slots toward cards with better
**field-weighted per-card matchup lift**, then re-running the sideboard
recommender for the 15.

Objective (rework — fixes review finding #4):
- **Per-card-value is the SOLE maindeck-swap driver.**  The greedy loop swaps
  maindeck flex purely by field-weighted per-card matchup lift (gated by tier).
  Coverage (the old objective) stays where it belongs — as the SIDEBOARD's
  objective — and is still computed + reported as an audit metric only.
- When there is NO gate-clearing per-card signal for any field opponent, the
  tuner makes NO maindeck swaps (keeps the consensus maindeck) and says so.
  This fully prevents gameplan-hollowing: coverage can never cut a proactive
  maindeck card.

Algorithm:
- ``field_weighted_values``: runs ``compute_card_winrates`` ONCE (heavy path);
  builds fwv[card] = Σ_opp field.shares[opp] * lift(card vs opp) over only
  gate-clearing cells.
- ``_greedy_tune``: pure greedy maximising fwv[add]-fwv[cut], strict-improve,
  locked core never cut, deterministic tie-break, legal_swap INJECTED.
  Testable with a hand-built fwv + trivial legal_swap, NO DB.
- ``_legal_swap_maindeck``: validates COMBINED main+side (fix #3), enforces
  4-copy + overrides + exemptions, exactly-60.
- ``tune_deck``: orchestrates; if has_value_signal -> _greedy_tune; else
  fell_back=True, no maindeck swaps.  Always calls recommend_sideboard with
  archetype/since/until for per-matchup plans.

Units:
  1  ``field_weighted_values`` + ``has_value_signal``  — per-card value
  2  ``_greedy_tune``                                  — pure greedy search
  3  ``_legal_swap_maindeck``                          — combined legality (fix #3)
  4  ``TunedDeck`` + ``tune_deck``                     — orchestration rewire
  5  ``partition_flex`` + ``candidate_pool``            — unchanged from prior impl
     ``coverage_value`` + ``build_tuning_coverage_model`` — audit metrics only
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from typing import Callable, Optional

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_global_field
from legacy_engine.advisory.sideboard import (
    CoverageModel,
    MatchupPlan,
    _build_coverage_model,
    _compute_covered_weight,
    recommend_sideboard,
)
from legacy_engine.advisory.whattoplay import field_vulnerability_tags, vulnerability_tags_for_deck
from legacy_engine.analytics.matchup import build_matrix
from legacy_engine.generation.consensus import _latest_regime_window, card_frequencies
from legacy_engine.ingestion.banlist import current_banlist, validate_deck

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_LOCK_THRESHOLD: float = 0.65   # ≥65% inclusion → locked core
_DEFAULT_MAX_SWAPS: int = 8             # cap on greedy maindeck swap rounds
_MAIN_SIZE: int = 60

# Confidence tiers that count as gate-clearing for per-card value
_VALUE_GATE: tuple[str, ...] = ("evolving", "established")


# ---------------------------------------------------------------------------
# Public thin wrapper: build the coverage model from the field + deck context
# (audit-metric use only — NOT the maindeck swap driver)
# ---------------------------------------------------------------------------

def build_tuning_coverage_model(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    deck_maindeck: dict[str, int],
) -> CoverageModel:
    """Build a CoverageModel for tuning from the field and the current maindeck.

    Thin public wrapper over ``advisory.sideboard._build_coverage_model`` so
    ``generation.tuning`` can reuse the exact same model without duplicating it.

    Returns a ``CoverageModel`` with elements/weights/candidates derived from
    the field's archetype tags and the deck's color identity.

    Used for audit metrics (coverage_before/after) only — NOT the swap driver.
    """
    from legacy_engine.advisory.whattoplay import _load_deck_cards
    from legacy_engine.colors import compute_deck_colors as _compute_colors

    cards_with_counts = _load_deck_cards(con, deck_maindeck)
    deck_card_objects = [card for card, _count in cards_with_counts]
    deck_colors_str = _compute_colors(deck_card_objects)
    deck_colors: frozenset[str] = frozenset(deck_colors_str) if deck_colors_str else frozenset()

    deck_tags = vulnerability_tags_for_deck(con, deck_maindeck)
    archetype_tags = field_vulnerability_tags(con, field)

    return _build_coverage_model(
        field,
        archetype_tags,
        deck_colors,
        deck_tags,
    )


# ---------------------------------------------------------------------------
# Unit 5 — Flex/locked partition + candidate pool (unchanged from prior impl)
# ---------------------------------------------------------------------------

def partition_flex(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    *,
    lock_threshold: float = _DEFAULT_LOCK_THRESHOLD,
    since: str | None = None,
    until: str | None = None,
    players: set[str] | None = None,
    alias_map: dict[str, str] | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    """Partition a maindeck into (locked, flex) slices.

    A card is LOCKED if its archetype consensus inclusion_pct >= ``lock_threshold``;
    otherwise it is in the flexible pool the tuner may swap.

    Lands and high-inclusion proactive core cards land in ``locked`` automatically
    (they appear in >=65% of the archetype's decks by definition).

    Parameters
    ----------
    con
        DuckDB connection with the tournament corpus.
    archetype
        The archetype whose consensus frequencies determine lock status.
    maindeck
        The starting maindeck (card->count).  Keys not in the archetype's card pool
        (e.g. cards the user injected) are placed in flex by default.
    lock_threshold
        Inclusion fraction at or above which a card is locked (default 0.65).
    since / until
        Date window for consensus frequencies; ``None`` defaults to the latest
        ban-regime window.
    players / alias_map
        Optional player filter (gated-additive; ``None`` → unchanged behaviour).

    Returns
    -------
    (locked, flex)
        Two disjoint dicts that together cover every card in ``maindeck``.

    AC: cards run by >=65% of the archetype's decks are locked;
        flex = the rest; locked | flex = maindeck.
    """
    if since is None and until is None:
        since, until = _latest_regime_window()

    freqs = card_frequencies(
        con, archetype, board="main", since=since, until=until,
        players=players, alias_map=alias_map,
    )
    inclusion: dict[str, float] = {cf.name: cf.inclusion_pct for cf in freqs}

    locked: dict[str, int] = {}
    flex: dict[str, int] = {}

    for card, count in maindeck.items():
        pct = inclusion.get(card, 0.0)
        if pct >= lock_threshold:
            locked[card] = count
        else:
            flex[card] = count

    return locked, flex


def candidate_pool(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    since: str | None = None,
    until: str | None = None,
    players: set[str] | None = None,
    alias_map: dict[str, str] | None = None,
) -> list[str]:
    """Return observed archetype maindeck card names (the swap-in candidate pool).

    These are the cards the archetype has run in-window, sourced from
    ``generation.consensus.card_frequencies``.  Bounded and faithful to
    "what wins now."  Cards the archetype hasn't run are excluded (deferred to
    gap-discovery mode 3).

    Returns a list of card names, ordered by inclusion_pct DESC, modal_count DESC.

    ``players`` / ``alias_map`` — optional player filter (gated-additive; ``None`` unchanged).

    AC: result = all card names from card_frequencies for this archetype (main board).
    """
    if since is None and until is None:
        since, until = _latest_regime_window()

    freqs = card_frequencies(
        con, archetype, board="main", since=since, until=until,
        players=players, alias_map=alias_map,
    )
    return [cf.name for cf in freqs]


# ---------------------------------------------------------------------------
# Coverage objective (audit metric only — NOT the maindeck swap driver)
# ---------------------------------------------------------------------------

def coverage_value(model: CoverageModel, cards: dict[str, int]) -> float:
    """Compute the field-weighted saturating-coverage value of a set of cards.

    Sigma_e weight_e * g(cov_e)  where cov_e = number of cards in ``cards``
    (accounting for copy counts) that cover element e, and g(n)=1-(1-p)^n.

    Delegates to ``advisory.sideboard._compute_covered_weight``.

    Used for before/after audit reporting only — NOT the greedy swap driver.
    """
    return _compute_covered_weight(cards, model)


# ---------------------------------------------------------------------------
# Unit 1 — Field-weighted per-card value (the REAL swap objective)
# ---------------------------------------------------------------------------

def field_weighted_values(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    cards: list[str],
    *,
    since: str | None = None,
    until: str | None = None,
    gate: tuple[str, ...] = _VALUE_GATE,
    card_winrates=None,
) -> dict[str, float]:
    """Compute field-weighted per-card matchup lift for a list of cards.

    Pass a precomputed ``card_winrates`` (``CardWinRates`` over the same window) to reuse
    the heavy full-corpus scan instead of recomputing it; ``tune_deck`` threads one through
    here and into ``recommend_sideboard``. When None it is computed here.

    Runs ``compute_card_winrates`` ONCE (heavy path) then:

        fwv[card] = Sum_opp field.shares[opp] * lift(card vs opp)

    summed only over (card, opp) cells whose tier is in ``gate``; thin cells
    (speculative tier) contribute 0 so they do not drive swaps.

    ``cards`` should be the union of the maindeck and the candidate pool
    (value every card the greedy loop might touch).

    Window defaults to ``_latest_regime_window()`` when both since/until are None.

    Returns
    -------
    dict[str, float]
        card -> field-weighted matchup lift.  Cards with no gate-clearing cell
        anywhere get 0.0.

    AC
    --
    - A card with proven positive lift vs high-share opponents gets a high fwv.
    - A card dead vs the field gets a low/negative fwv.
    - A card with only speculative cells gets 0.0.
    """
    from legacy_engine.analytics.match_results import compute_card_winrates
    from legacy_engine.analytics.card_value import card_values_vs

    if since is None and until is None:
        since, until = _latest_regime_window()

    # Heavy path: runs once; greedy loop then works on precomputed floats.
    if card_winrates is not None:
        r = card_winrates
    else:
        try:
            r = compute_card_winrates(con, since=since, until=until)
        except Exception as exc:
            log.debug("field_weighted_values: compute_card_winrates failed: %s", exc)
            return {card: 0.0 for card in cards}

    if r.coverage.decisive_matched == 0:
        return {card: 0.0 for card in cards}

    fwv: dict[str, float] = {card: 0.0 for card in cards}

    for opp, share in field.shares.items():
        if share <= 0.0:
            continue
        cvs = card_values_vs(r, cards, "main", opp, gate=gate)
        for card, cv in cvs.items():
            if cv.tier in gate:
                fwv[card] = fwv.get(card, 0.0) + share * cv.lift

    return fwv


def has_value_signal(fwv: dict[str, float]) -> bool:
    """Return True iff any card has a non-zero field-weighted value.

    A non-zero fwv means at least one (card, opponent) cell cleared the gate,
    giving the greedy loop actionable data.

    AC: True iff any |fwv[card]| > 0.
    """
    return any(v != 0.0 for v in fwv.values())


# ---------------------------------------------------------------------------
# Unit 2 — Pure greedy tuner (the trickiest unit; tests pass hand-built fwv)
# ---------------------------------------------------------------------------

def _greedy_tune(
    fwv: dict[str, float],
    maindeck: dict[str, int],
    locked: dict[str, int],
    flex: dict[str, int],
    pool: list[str],
    *,
    max_swaps: int,
    legal_swap: Callable[[dict[str, int], str, str], tuple[bool, dict[str, int]]],
) -> tuple[dict[str, int], list[tuple[str, str]], float, float]:
    """Pure greedy maindeck tuner driven by field-weighted per-card lift.

    value(cards) = Sum copies * fwv.get(card, 0.0)

    Each round: among legal (flex card with copies > 0 cut, pool card added,
    add != cut, add not already in locked core in current deck):
      - pick the swap maximising fwv[add] - fwv[cut]
      - accept iff gain > 0 (STRICT improve — no ties)
      - apply; update flex; record
      - stop at convergence or max_swaps

    Parameters
    ----------
    fwv
        Precomputed field-weighted value per card (pure dict — no DB calls here).
    maindeck
        Starting maindeck (card -> count, must sum to 60).
    locked
        Locked core (subset of maindeck keys) — NEVER cut.
    flex
        Flex slice of the maindeck (disjoint from locked).
    pool
        Candidate pool of card names the greedy loop may swap in.
    max_swaps
        Maximum number of swap rounds.
    legal_swap
        Injected callable: ``(current_main, cut, add) -> (ok, new_main)``.
        Enforces exactly-60 and copy-limit legality; pure (no DB required when
        supplied as a trivial lambda in tests).

    Returns
    -------
    (final_main, swaps, value_before, value_after)
        ``swaps`` is the ordered audit log of (cut, added) pairs.
        ``value_before`` and ``value_after`` are the field-weighted sum values.

    AC
    --
    - Given an fwv where a flex card scores low and a pool card scores high,
      exactly that swap is made and value_after > value_before.
    - Locked core never appears in swaps.
    - No strictly-improving swap left at stop.
    - Deterministic tie-break by (cut_name, add_name) lex order.
    """
    locked_cards: frozenset[str] = frozenset(locked.keys())

    def _value(cards: dict[str, int]) -> float:
        return sum(copies * fwv.get(card, 0.0) for card, copies in cards.items())

    value_before = _value(maindeck)

    current_main = dict(maindeck)
    current_flex = dict(flex)
    swaps: list[tuple[str, str]] = []

    for _round in range(max_swaps):
        best_gain: float = 0.0
        best_cut: str | None = None
        best_add: str | None = None
        best_main: dict[str, int] | None = None

        for cut_card in sorted(current_flex.keys()):  # deterministic iteration order
            if current_main.get(cut_card, 0) <= 0:
                continue  # fully cut in a previous round

            cut_lift = fwv.get(cut_card, 0.0)

            for add_card in pool:
                if add_card == cut_card:
                    continue
                # Don't add a card that is already part of the locked core in the
                # current maindeck (it's already there; adding would exceed the limit).
                if add_card in locked_cards and add_card in current_main:
                    continue

                add_lift = fwv.get(add_card, 0.0)
                gain = add_lift - cut_lift

                # Only strictly-improving swaps (gain > 0).
                if gain <= 0.0:
                    continue

                # Check legality (injected — pure in tests, DB-backed in prod).
                valid, new_main = legal_swap(current_main, cut_card, add_card)
                if not valid:
                    continue

                # Deterministic tie-break: prefer lex-smaller (cut, add) pair.
                if gain > best_gain or (
                    gain == best_gain
                    and best_cut is not None
                    and (cut_card, add_card) < (best_cut, best_add)
                ):
                    best_gain = gain
                    best_cut = cut_card
                    best_add = add_card
                    best_main = new_main

        if best_cut is None:
            log.debug("_greedy_tune: converged after %d swap(s)", len(swaps))
            break

        # Apply the best swap.
        swaps.append((best_cut, best_add))
        current_main = best_main

        # Update flex to reflect the new maindeck state.
        if current_main.get(best_cut, 0) == 0:
            current_flex.pop(best_cut, None)
        else:
            current_flex[best_cut] = current_main[best_cut]

        # If the added card is now in the maindeck and NOT in the locked core,
        # it becomes a flex candidate (can be swapped out in a future round).
        if best_add in current_main and best_add not in locked_cards:
            current_flex[best_add] = current_main[best_add]

        log.debug(
            "_greedy_tune: swap %d: cut=%r (fwv=%.4f) add=%r (fwv=%.4f) gain=%.4f",
            len(swaps), best_cut, fwv.get(best_cut, 0.0),
            best_add, fwv.get(best_add, 0.0), best_gain,
        )

    value_after = _value(current_main)
    return current_main, swaps, value_before, value_after


# ---------------------------------------------------------------------------
# Unit 3 — Combined-legality swap (fix #3: validate main+side together)
# ---------------------------------------------------------------------------

def _legal_swap_maindeck(
    current: dict[str, int],
    cut: str,
    add: str,
    sideboard: dict[str, int],
    *,
    banlist_snapshot,
) -> tuple[bool, dict[str, int]]:
    """Attempt to apply a (cut, add) swap to ``current`` and validate legality.

    FIX #3: validates COMBINED main+side (pass the sideboard, not {}).
    Enforces the 4-copy limit + COPY_LIMIT_OVERRIDES + UNLIMITED/BASIC exemptions
    against the COMBINED deck (main + side) so the greedy loop cannot over-stack
    a card across both boards.

    Returns (valid, new_maindeck).  ``valid=False`` when the swap would:
    - Remove more copies than currently held (cut > current[cut]).
    - Add a banned card.
    - Exceed the combined copy limit for the added card (main + side).
    - Cause the maindeck to differ from exactly 60 cards.

    NOTE: Catalog ``max_copies`` (e.g. Surgical Extraction = 2) is a SIDEBOARD
    rule enforced inside ``recommend_sideboard``.  The maindeck candidate pool
    is the archetype's observed maindeck cards, bound by the standard 4-copy rule
    (+ overrides + unlimited exemptions) — catalog max_copies does not apply here.
    """
    from legacy_engine.models.banlist import BASIC_LAND_NAMES, COPY_LIMIT_OVERRIDES, UNLIMITED_COPIES

    cut_count = current.get(cut, 0)
    if cut_count <= 0:
        return False, current

    # Build the new maindeck (never mutate current).
    new_main = dict(current)
    if new_main[cut] == 1:
        del new_main[cut]
    else:
        new_main[cut] -= 1

    # Exactly-60 check BEFORE adding (avoids building a dict for an illegal state).
    # After swap: remove 1 copy of cut, add 1 copy of add — net zero.
    # Verify current sum is 60 first (caller's contract).
    if sum(new_main.values()) + 1 != _MAIN_SIZE:  # +1 because we haven't added yet
        return False, current

    # Combined copy-limit check for the added card.
    if add not in BASIC_LAND_NAMES and add not in UNLIMITED_COPIES:
        limit = COPY_LIMIT_OVERRIDES.get(add, 4)
        main_copies = new_main.get(add, 0)
        side_copies = sideboard.get(add, 0)
        combined_after_add = main_copies + 1 + side_copies
        if combined_after_add > limit:
            return False, current

    new_main[add] = new_main.get(add, 0) + 1

    # Final combined legality via validate_deck.
    errors = validate_deck(new_main, sideboard, banlist_snapshot)
    if errors:
        return False, current

    return True, new_main


# ---------------------------------------------------------------------------
# Unit 4 — TunedDeck + tune_deck rewire
# ---------------------------------------------------------------------------

@dataclass
class TunedDeck:
    """Output of ``tune_deck`` (rework 2026-05-31).

    ``value_before`` / ``value_after``: field-weighted per-card matchup lift sum
    for the maindeck before and after tuning.  This is the REAL optimization
    objective that drove maindeck swaps (or was absent, triggering fell_back).

    ``coverage_before`` / ``coverage_after``: saturating-coverage value of the
    maindeck before and after.  Kept as AUDIT context — NOT the swap driver.

    ``matchup_plans``: per-opponent OUT/IN plans from ``recommend_sideboard``
    (populated when per-card data cleared the gate for >= 1 opponent).

    ``objective``: ``"per-card-value"`` when swaps were driven by per-card lift;
    ``"no-signal-skip"`` when no gate-clearing signal was found (fell_back=True).

    ``fell_back=True`` <=> no per-card signal => no maindeck swaps; the consensus
    maindeck is returned unchanged.  The sideboard recommender is still called.

    ``legality_errors`` is ALWAYS [] on return (Unit 3 guarantee).
    """

    archetype: str
    maindeck: dict[str, int]
    sideboard: dict[str, int]
    swaps: list[tuple[str, str]]             # (cut, added) in order — audit log

    # Per-card value objective (new — the REAL driver)
    value_before: float
    value_after: float

    # Saturating coverage (audit context only — NOT the driver)
    coverage_before: float
    coverage_after: float

    positioning_s: float | None              # archetype S (None if absent from matrix)

    # Per-matchup OUT/IN plans (new; from recommend_sideboard)
    matchup_plans: dict[str, MatchupPlan] = dc_field(default_factory=dict)

    # Objective label
    objective: str = "no-signal-skip"        # "per-card-value" | "no-signal-skip"

    fell_back: bool = False
    reason: str = ""                         # explanation of objective/fallback
    legality_errors: list[str] = dc_field(default_factory=list)  # ALWAYS [] on return


def tune_deck(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    sideboard: dict[str, int],
    *,
    field: FieldDistribution | None = None,
    since: str | None = None,
    until: str | None = None,
    lock_threshold: float = _DEFAULT_LOCK_THRESHOLD,
    max_swaps: int = _DEFAULT_MAX_SWAPS,
    card_winrates=None,
    players: set[str] | None = None,
    alias_map: dict[str, str] | None = None,
) -> TunedDeck:
    """Optimise a maindeck against the field using greedy per-card-value tuning.

    Rework (2026-05-31): per-card field-weighted matchup lift is now the SOLE
    maindeck swap driver (fixes review finding #4 — coverage objective was
    hoser-blind and would hollow the gameplan by cutting proactive flex cards).

    Algorithm
    ---------
    1. Resolve window + field.
    2. Build matchup matrix; compute positioning_s (archetype context).
    3. Build coverage model for audit metrics (coverage_before/after); NOT the swap driver.
    4. Build partition_flex + candidate_pool; fetch banlist snapshot.
    5. Compute fwv = field_weighted_values(con, field, maindeck|pool, ...).
    6. If has_value_signal(fwv): build legal_swap closure; run _greedy_tune
       (objective="per-card-value").
       Else: no maindeck swaps, fell_back=True, objective="no-signal-skip".
    7. Re-run recommend_sideboard(archetype=archetype, since/until) for the 15 +
       per-matchup plans.
    8. Final combined validate_deck; guarantee legality_errors == [] (revert to
       consensus main + empty side if needed).

    Parameters
    ----------
    con
        DuckDB connection.
    archetype
        Target archetype (used for consensus frequencies + positioning context).
    maindeck
        Starting maindeck (dict card->count, should sum to 60).
    sideboard
        Starting sideboard (dict card->count). Will be replaced by the recommender.
    field
        Pre-built FieldDistribution; ``None`` uses the global field.
    since / until
        Date window for consensus frequencies.  ``None`` defaults to the latest
        ban-regime window.
    lock_threshold
        Inclusion fraction at or above which a card is locked (default 0.65).
    max_swaps
        Maximum number of greedy swap rounds on the maindeck (default 8).

    Returns
    -------
    TunedDeck (legality_errors is always [])

    AC
    --
    - Per-card signal present: value_after > value_before, swaps non-empty,
      locked core untouched, maindeck stays exactly 60 + legal.
    - No per-card signal: fell_back=True, objective="no-signal-skip",
      maindeck == consensus input, sideboard still built with matchup_plans.
    - legality_errors == [] on return (always).
    - positioning_s carried as archetype context; unchanged by card swaps (labeled).
    """
    # ── Resolve window + field ────────────────────────────────────────────────
    if since is None and until is None:
        eff_since, eff_until = _latest_regime_window()
    else:
        eff_since, eff_until = since, until

    if field is None:
        field = build_global_field(con)

    # ── Build matchup matrix for positioning_s ────────────────────────────────
    matrix = build_matrix(con)

    # ── Positioning S (archetype context; unchanged by card swaps) ───────────
    positioning_s: float | None = None
    if archetype in matrix.archetypes:
        try:
            from legacy_engine.advisory.positioning import positioning_score
            pos = positioning_score(matrix, field, archetype, seed=42)
            positioning_s = pos.s_mean
        except Exception as exc:
            log.warning("tune_deck: positioning_score failed for %r: %s", archetype, exc)

    # ── Coverage model for audit metrics ────────────────────────────────────
    # Build once up front; used for coverage_before/after (NOT the swap driver).
    try:
        model = build_tuning_coverage_model(con, field, maindeck)
        cov_before = coverage_value(model, maindeck)
    except Exception as exc:
        log.debug("tune_deck: coverage model build failed: %s", exc)
        model = None
        cov_before = 0.0

    # ── Build flex/locked partition + candidate pool ─────────────────────────
    locked, flex = partition_flex(
        con, archetype, maindeck,
        lock_threshold=lock_threshold,
        since=eff_since, until=eff_until,
        players=players, alias_map=alias_map,
    )
    pool = candidate_pool(
        con, archetype, since=eff_since, until=eff_until,
        players=players, alias_map=alias_map,
    )
    snapshot = current_banlist()

    # ── Per-card win-rate aggregate: compute ONCE, thread everywhere ─────────
    # The heavy full-corpus scan runs a single time and is reused by both
    # field_weighted_values (the swap objective) and recommend_sideboard (the
    # value-aware weighting + per-matchup plans), rather than 3x per tune.
    # A caller (e.g. the `--discover` CLI path) may inject a precomputed aggregate
    # over the same window to avoid a second scan; None → compute here as before.
    if card_winrates is None:
        try:
            from legacy_engine.analytics.match_results import compute_card_winrates
            card_winrates = compute_card_winrates(con, since=eff_since, until=eff_until)
        except Exception as exc:
            log.debug("tune_deck: compute_card_winrates failed: %s", exc)
            card_winrates = None

    # ── Compute field-weighted per-card values (reuses the aggregate above) ──
    all_cards = list(set(list(maindeck.keys()) + pool))
    fwv = field_weighted_values(
        con, field, all_cards,
        since=eff_since, until=eff_until, card_winrates=card_winrates,
    )

    log.debug(
        "tune_deck: archetype=%r signal=%s non_zero_cards=%d pool=%d",
        archetype, has_value_signal(fwv),
        sum(1 for v in fwv.values() if v != 0.0), len(pool),
    )

    # ── Per-card value objective: greedy or no-signal fallback ───────────────
    if not has_value_signal(fwv):
        # No gate-clearing per-card signal → no maindeck swaps.
        # This is the honest response to absent data (not fabricating an edge).
        reason = (
            "no-signal-skip: no gate-clearing per-card matchup data found for "
            f"archetype {archetype!r} vs the current field in window "
            f"[{eff_since}, {eff_until}]. "
            "Maindeck kept as-is (consensus); sideboard recommender still applied. "
            f"[window audit: consensus/card-freq list window [{eff_since}..{eff_until}] (uniform); "
            "matchup math uses adaptive per-opponent ban-aware windows — intentional divergence]"
        )
        log.info("tune_deck: %s", reason)

        # Compute value_before on the input maindeck (will equal value_after since
        # no swaps are made; both are 0.0 when there's no signal).
        v_before = sum(copies * fwv.get(card, 0.0) for card, copies in maindeck.items())

        # Still run the sideboard recommender for the 15.
        sb_pkg = recommend_sideboard(
            con, field, maindeck, solver="greedy",
            archetype=archetype, since=eff_since, until=eff_until,
            card_winrates=card_winrates,
        )
        recommended_sb = dict(sb_pkg.cards)

        # Final combined legality.
        legality_errors = validate_deck(maindeck, recommended_sb, snapshot)
        if legality_errors:
            log.warning("tune_deck: legality errors (no-signal path): %s", legality_errors)
            # Worst-case: return with empty sideboard (always legal).
            recommended_sb = {}
            legality_errors = validate_deck(maindeck, recommended_sb, snapshot)

        cov_after = coverage_value(model, maindeck) if model else cov_before

        return TunedDeck(
            archetype=archetype,
            maindeck=dict(maindeck),
            sideboard=recommended_sb,
            swaps=[],
            value_before=v_before,
            value_after=v_before,      # no swaps
            coverage_before=cov_before,
            coverage_after=cov_after,
            positioning_s=positioning_s,
            matchup_plans=dict(sb_pkg.matchup_plans),
            objective="no-signal-skip",
            fell_back=True,
            reason=reason,
            legality_errors=legality_errors,
        )

    # ── Greedy swap loop (per-card-value objective) ───────────────────────────
    # Build the legal_swap closure: captures `snapshot` + a mutable sideboard
    # reference.  The sideboard changes after the greedy loop (re-run recommender),
    # but during the greedy loop we use the STARTING sideboard for combined checks
    # (conservative: ensures the greedy picks stay legal even before the re-run).
    starting_sideboard = dict(sideboard)

    def _legal_swap_closure(current_main: dict[str, int], cut: str, add: str) -> tuple[bool, dict[str, int]]:
        return _legal_swap_maindeck(
            current_main, cut, add, starting_sideboard,
            banlist_snapshot=snapshot,
        )

    final_main, swaps, v_before, v_after = _greedy_tune(
        fwv, maindeck, locked, flex, pool,
        max_swaps=max_swaps,
        legal_swap=_legal_swap_closure,
    )

    reason = (
        f"per-card-value greedy converged after {len(swaps)} swap(s)"
        if len(swaps) < max_swaps
        else f"per-card-value greedy: max_swaps={max_swaps} reached"
    )
    # Fix A: note the intentional window divergence so it is never silent.
    reason += (
        f" [window audit: consensus/card-freq list uses current-regime window "
        f"[{eff_since}..{eff_until}] (uniform); matchup math uses adaptive per-opponent "
        "ban-aware windows — intentional divergence, not a bug]"
    )

    # ── Re-run sideboard recommender for the tuned maindeck ──────────────────
    sb_pkg = recommend_sideboard(
        con, field, final_main, solver="greedy",
        archetype=archetype, since=eff_since, until=eff_until,
        card_winrates=card_winrates,
    )
    recommended_sb = dict(sb_pkg.cards)

    # ── Coverage audit (NOT the driver) ──────────────────────────────────────
    if model is not None:
        cov_after = coverage_value(model, final_main)
    else:
        cov_after = cov_before

    # ── Final combined legality guarantee ─────────────────────────────────────
    legality_errors = validate_deck(final_main, recommended_sb, snapshot)
    if legality_errors:
        log.warning(
            "tune_deck: final legality errors after greedy: %s — reverting to consensus main",
            legality_errors,
        )
        # Revert: return the input (consensus) main + recommended side.
        # Worst case trim the sideboard to empty.
        final_main = dict(maindeck)
        recommended_sb = {}
        legality_errors = validate_deck(final_main, recommended_sb, snapshot)
        swaps = []
        v_after = v_before  # no swaps applied
        reason += " [REVERTED: final legality failed; returned consensus main]"

    return TunedDeck(
        archetype=archetype,
        maindeck=final_main,
        sideboard=recommended_sb,
        swaps=swaps,
        value_before=v_before,
        value_after=v_after,
        coverage_before=cov_before,
        coverage_after=cov_after,
        positioning_s=positioning_s,
        matchup_plans=dict(sb_pkg.matchup_plans),
        objective="per-card-value",
        fell_back=False,
        reason=reason,
        legality_errors=legality_errors,
    )
