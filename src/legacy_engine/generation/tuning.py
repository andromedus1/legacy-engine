"""Field-tuning for deck generation (mode 2).

Optimizes a consensus (or user-supplied) 60+15 shell against the current or projected
field by swapping flexible maindeck slots toward cards with better field-weighted
coverage, then re-running the sideboard recommender for the 15.

Approach (from feature spec § Design decisions):
- **Coverage objective**: reuses advisory.sideboard's CoverageModel — Σ weight_e·g(n_e),
  g(n)=1−(1−p)^n over field threat-elements weighted by archetype share. Card-aware,
  submodular — greedy is near-optimal.
- **Flex/locked partition**: cards run by ≥ lock_threshold of archetype decks are LOCKED
  (high-inclusion proactive core); the rest are flexible. Data-driven.
- **Candidate pool**: observed archetype maindeck cards in-window (bounded, faithful to
  "what wins now").
- **Search**: greedy one-swap-at-a-time; stop when no swap strictly improves coverage
  OR max_swaps reached. Maindeck stays exactly 60 + legal at every step.
- **Bimodal fallback**: if the archetype is absent from the matchup matrix OR the
  relevant matchups are thin (n < DISPLAY_GATE_N), set fell_back=True, skip maindeck
  swaps, keep consensus main, still run the sideboard recommender for the 15.
- **Positioning S**: archetype-level context only (unchanged by card swaps by design).
  Computed once and carried in the result.

Units:
  1  ``partition_flex`` + ``candidate_pool``  — flex/locked partition
  2  ``coverage_value``                        — field-weighted coverage objective
  3  ``tune_deck`` + ``TunedDeck``             — greedy swap loop + bimodal fallback
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from typing import Optional

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_global_field
from legacy_engine.advisory.sideboard import (
    CoverageModel,
    _build_coverage_model,
    _compute_covered_weight,
    recommend_sideboard,
)
from legacy_engine.advisory.whattoplay import field_vulnerability_tags, vulnerability_tags_for_deck
from legacy_engine.analytics.matchup import DISPLAY_GATE_N, MatchupMatrix, build_matrix
from legacy_engine.colors import compute_deck_colors
from legacy_engine.generation.consensus import _latest_regime_window, card_frequencies
from legacy_engine.ingestion.banlist import current_banlist, validate_deck

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_LOCK_THRESHOLD: float = 0.65   # ≥65% inclusion → locked core
_DEFAULT_MAX_SWAPS: int = 8             # cap on greedy maindeck swap rounds
_MAIN_SIZE: int = 60


# ---------------------------------------------------------------------------
# Public thin wrapper: build the coverage model from the field + deck context
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
# Unit 1 — Flex/locked partition + candidate pool
# ---------------------------------------------------------------------------

def partition_flex(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    *,
    lock_threshold: float = _DEFAULT_LOCK_THRESHOLD,
    since: str | None = None,
    until: str | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    """Partition a maindeck into (locked, flex) slices.

    A card is LOCKED if its archetype consensus inclusion_pct ≥ ``lock_threshold``;
    otherwise it is in the flexible pool the tuner may swap.

    Lands and high-inclusion proactive core cards land in ``locked`` automatically
    (they appear in ≥65% of the archetype's decks by definition).

    Parameters
    ----------
    con
        DuckDB connection with the tournament corpus.
    archetype
        The archetype whose consensus frequencies determine lock status.
    maindeck
        The starting maindeck (card→count).  Keys not in the archetype's card pool
        (e.g. cards the user injected) are placed in flex by default.
    lock_threshold
        Inclusion fraction at or above which a card is locked (default 0.65).
    since / until
        Date window for consensus frequencies; ``None`` defaults to the latest
        ban-regime window.

    Returns
    -------
    (locked, flex)
        Two disjoint dicts that together cover every card in ``maindeck``.

    AC: cards run by ≥65% of the archetype's decks are locked;
        flex = the rest; locked ∪ flex = maindeck.
    """
    if since is None and until is None:
        since, until = _latest_regime_window()

    freqs = card_frequencies(con, archetype, board="main", since=since, until=until)
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
) -> list[str]:
    """Return observed archetype maindeck card names (the swap-in candidate pool).

    These are the cards the archetype has run in-window, sourced from
    ``generation.consensus.card_frequencies``.  Bounded and faithful to
    "what wins now."  Cards the archetype hasn't run are excluded (deferred to
    gap-discovery mode 3).

    Returns a list of card names, ordered by inclusion_pct DESC, modal_count DESC.

    AC: result = all card names from card_frequencies for this archetype (main board).
    """
    if since is None and until is None:
        since, until = _latest_regime_window()

    freqs = card_frequencies(con, archetype, board="main", since=since, until=until)
    return [cf.name for cf in freqs]


# ---------------------------------------------------------------------------
# Unit 2 — Field-weighted coverage objective
# ---------------------------------------------------------------------------

def coverage_value(model: CoverageModel, cards: dict[str, int]) -> float:
    """Compute the field-weighted saturating-coverage value of a set of cards.

    Σ_e weight_e · g(cov_e)  where  cov_e = number of cards in ``cards``
    (accounting for copy counts) that cover element e, and g(n)=1−(1−p)^n.

    Delegates to ``advisory.sideboard._compute_covered_weight`` — the same
    primitive used by the sideboard recommender to score its solution.
    This ensures the tuner's objective matches what the recommender optimizes.

    Pure function; safe to call repeatedly in the greedy loop.

    AC: adding an answer that covers a high-weight field element raises the
        value with diminishing returns (saturating g(n)).
    """
    return _compute_covered_weight(cards, model)


# ---------------------------------------------------------------------------
# Unit 3 — TunedDeck + greedy swap loop + bimodal fallback
# ---------------------------------------------------------------------------

@dataclass
class TunedDeck:
    """Output of ``tune_deck``.

    ``swaps`` is the ordered audit log of (cut, added) pairs made during tuning.
    ``coverage_before`` is the coverage value of the starting maindeck.
    ``coverage_after`` is the coverage value of the final maindeck (= before when
    ``fell_back=True`` — no swaps were made).
    ``positioning_s`` is the archetype's positioning score S (field context only;
    unchanged by card swaps by design — see spec § Architectural choice).
    ``fell_back=True`` means the archetype was absent from the matchup matrix or
    the relevant matchups were too thin (n < DISPLAY_GATE_N), so no maindeck swaps
    were made.  The sideboard is still recommended in both paths.
    ``legality_errors`` mirrors ``ingestion.banlist.validate_deck``.
    """

    archetype: str
    maindeck: dict[str, int]
    sideboard: dict[str, int]
    swaps: list[tuple[str, str]]             # (cut, added) in order — audit log
    coverage_before: float
    coverage_after: float
    positioning_s: float | None              # archetype S (None if absent from matrix)
    fell_back: bool
    reason: str                              # fallback explanation or "greedy converged"
    legality_errors: list[str]


def _is_thin_field(matrix: MatchupMatrix, archetype: str) -> bool:
    """Return True if the archetype has no displayable (n≥30) matchup cells.

    A field is "thin" for bimodal fallback purposes when:
    - the archetype is absent from the matrix altogether, OR
    - the archetype is in the matrix but EVERY non-mirror cell has n < DISPLAY_GATE_N.

    This maps directly to the "matchup-n < 30 / archetype absent from the matrix"
    gating in the feature spec § Bimodal fallback.
    """
    if archetype not in matrix.archetypes:
        return True

    for opp in matrix.archetypes:
        if opp == archetype:
            continue
        cell = matrix.cells.get((archetype, opp))
        if cell is not None and cell.n >= DISPLAY_GATE_N:
            return False

    # All non-mirror cells are thin (or absent)
    return True


def _legal_swap_maindeck(
    current: dict[str, int],
    cut: str,
    add: str,
    *,
    banlist_snapshot,
) -> tuple[bool, dict[str, int]]:
    """Attempt to apply a (cut, add) swap to ``current`` and validate legality.

    Returns (valid, new_maindeck).  ``valid=False`` when the swap would:
    - Remove more copies than currently held (cut > current[cut]).
    - Add a banned card.
    - Exceed the 4-copy limit for the added card (combined main count).
    - Cause the maindeck to differ from exactly 60 cards.

    Does NOT re-check the sideboard — the caller passes the combined snapshot.
    """
    # The swap: cut 1 copy of ``cut``, add 1 copy of ``add``.
    cut_count = current.get(cut, 0)
    if cut_count <= 0:
        return False, current

    # Build the new maindeck (don't mutate current).
    new_main = dict(current)
    if new_main[cut] == 1:
        del new_main[cut]
    else:
        new_main[cut] -= 1

    add_count = new_main.get(add, 0)
    # Check the copy limit for ``add`` in the maindeck alone.
    # validate_deck checks combined main+side, but here we keep it conservative:
    # maindeck-only 4-copy rule (basic lands / overrides handled by validate_deck).
    from legacy_engine.models.banlist import BASIC_LAND_NAMES, COPY_LIMIT_OVERRIDES, UNLIMITED_COPIES
    if add not in BASIC_LAND_NAMES and add not in UNLIMITED_COPIES:
        limit = COPY_LIMIT_OVERRIDES.get(add, 4)
        if add_count + 1 > limit:
            return False, current

    new_main[add] = add_count + 1

    # Exactly-60 check.
    if sum(new_main.values()) != _MAIN_SIZE:
        return False, current

    # Legality check (main only; sideboard is kept from the caller's context).
    errors = validate_deck(new_main, {}, banlist_snapshot)
    if errors:
        return False, current

    return True, new_main


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
) -> TunedDeck:
    """Optimize a maindeck against the field using greedy coverage-swap tuning.

    Algorithm
    ---------
    1. Build the field (global or supplied) + CoverageModel.  Compute coverage_before.
    2. Bimodal fallback: if the archetype is absent from the matchup matrix OR all
       matchups are thin (n < DISPLAY_GATE_N), set ``fell_back=True``, skip maindeck
       swaps, run the sideboard recommender for the 15, and return early.
    3. Greedy loop: each round, find the (flex_out, pool_in) swap that maximally
       raises ``coverage_value`` while keeping exactly-60 + legality; accept if it
       strictly improves; stop when none improves or ``max_swaps`` hit.
    4. Re-run ``recommend_sideboard`` for the 15 against the (possibly tuned) maindeck.
    5. Compute coverage_after + positioning_s (archetype context only).
    6. Final legality validation.

    Parameters
    ----------
    con
        DuckDB connection.
    archetype
        Target archetype (used for consensus frequencies + positioning context).
    maindeck
        Starting maindeck (dict card→count, must sum to 60).
    sideboard
        Starting sideboard (dict card→count).  Will be replaced by the recommender.
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
    TunedDeck

    AC
    --
    - A deck with a weak slot vs a high-share threat gets that slot swapped toward a
      covering card: ``coverage_after > coverage_before``.
    - Maindeck stays exactly 60 + legal at every step.
    - Locked core is never modified.
    - Thin-field (bimodal fallback): ``fell_back=True``, maindeck unchanged, sideboard
      still built.
    - Swap log reproduces the before→after transition.
    - Deterministic given a seeded field + fixed archetype data.
    """
    # ── Resolve window + field ────────────────────────────────────────────────
    if since is None and until is None:
        eff_since, eff_until = _latest_regime_window()
    else:
        eff_since, eff_until = since, until

    if field is None:
        field = build_global_field(con)

    # ── Build coverage model + baseline score ────────────────────────────────
    model = build_tuning_coverage_model(con, field, maindeck)
    cov_before = coverage_value(model, maindeck)

    log.debug(
        "tune_deck: archetype=%r coverage_before=%.4f model_elements=%d candidates=%d",
        archetype, cov_before, len(model.element_weight), len(model.candidate_covers),
    )

    # ── Build matchup matrix for thin-field check + positioning_s ────────────
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

    # ── Bimodal fallback check ────────────────────────────────────────────────
    thin = _is_thin_field(matrix, archetype)
    if thin:
        reason = (
            f"bimodal fallback: archetype {archetype!r} is absent from the matchup "
            "matrix or all relevant matchups have n < 30 (DISPLAY_GATE_N). "
            "Maindeck kept as-is; sideboard recommender still applied."
        )
        log.info("tune_deck: %s", reason)

        # Still run the sideboard recommender for the 15.
        sb_pkg = recommend_sideboard(con, field, maindeck, solver="greedy")
        recommended_sb = dict(sb_pkg.cards)

        snapshot = current_banlist()
        legality_errors = validate_deck(maindeck, recommended_sb, snapshot)

        return TunedDeck(
            archetype=archetype,
            maindeck=dict(maindeck),
            sideboard=recommended_sb,
            swaps=[],
            coverage_before=cov_before,
            coverage_after=cov_before,      # no maindeck swaps
            positioning_s=positioning_s,
            fell_back=True,
            reason=reason,
            legality_errors=legality_errors,
        )

    # ── Greedy swap loop ──────────────────────────────────────────────────────
    locked, flex = partition_flex(
        con, archetype, maindeck,
        lock_threshold=lock_threshold,
        since=eff_since, until=eff_until,
    )
    pool = candidate_pool(con, archetype, since=eff_since, until=eff_until)
    snapshot = current_banlist()

    current_main = dict(maindeck)
    swaps: list[tuple[str, str]] = []
    current_coverage = cov_before

    for _round in range(max_swaps):
        # Find the best (flex_out, pool_in) swap that strictly improves coverage.
        best_gain: float = 0.0
        best_cut: str | None = None
        best_add: str | None = None
        best_main: dict[str, int] | None = None

        for cut_card in list(flex):
            if cut_card not in current_main:
                continue  # already fully cut in a previous round

            for add_card in pool:
                if add_card == cut_card:
                    continue
                # Don't add a card already in the locked core (it's already there).
                if add_card in locked and add_card in current_main:
                    # Already in maindeck as part of locked core — skip.
                    continue

                valid, new_main = _legal_swap_maindeck(
                    current_main, cut_card, add_card, banlist_snapshot=snapshot
                )
                if not valid:
                    continue

                # Rebuild coverage model against the new maindeck (colors/tags may
                # differ slightly; reuse same field for speed — model rebuild is cheap).
                new_cov = coverage_value(model, new_main)
                gain = new_cov - current_coverage

                if gain > best_gain or (
                    gain == best_gain and gain > 0.0
                    and (best_cut is None or (cut_card, add_card) < (best_cut, best_add))
                ):
                    best_gain = gain
                    best_cut = cut_card
                    best_add = add_card
                    best_main = new_main

        if best_cut is None or best_gain <= 0.0:
            # No more improving swaps.
            log.debug("tune_deck: greedy converged after %d swap(s)", len(swaps))
            break

        # Apply the best swap.
        swaps.append((best_cut, best_add))
        current_main = best_main
        current_coverage = coverage_value(model, current_main)

        # Update flex to reflect the new maindeck state.
        # If we fully cut the cut_card, remove it from flex.
        if best_cut not in current_main:
            del flex[best_cut]
        else:
            flex[best_cut] = current_main[best_cut]

        # If we added a card that was in the pool but not in flex, add it to flex
        # (so it can be cut in a future round if a better option appears).
        # Check it isn't now locked.
        if best_add in current_main and best_add not in locked:
            flex[best_add] = current_main[best_add]

        log.debug(
            "tune_deck: swap %d: cut=%r add=%r cov=%.4f → %.4f",
            len(swaps), best_cut, best_add,
            current_coverage - best_gain, current_coverage,
        )

    cov_after = current_coverage
    reason = (
        f"greedy converged after {len(swaps)} swap(s)"
        if len(swaps) < max_swaps
        else f"max_swaps={max_swaps} reached"
    )

    # ── Re-run sideboard recommender for the tuned maindeck ──────────────────
    sb_pkg = recommend_sideboard(con, field, current_main, solver="greedy")
    recommended_sb = dict(sb_pkg.cards)

    # ── Final legality validation ─────────────────────────────────────────────
    legality_errors = validate_deck(current_main, recommended_sb, snapshot)
    if legality_errors:
        log.warning("tune_deck: legality errors after tuning: %s", legality_errors)

    return TunedDeck(
        archetype=archetype,
        maindeck=current_main,
        sideboard=recommended_sb,
        swaps=swaps,
        coverage_before=cov_before,
        coverage_after=cov_after,
        positioning_s=positioning_s,
        fell_back=False,
        reason=reason,
        legality_errors=legality_errors,
    )
