"""Sideboard recommender — weighted max-coverage (ILP + greedy).

Recommends a 15-card sideboard as a weighted maximum-coverage problem:
  maximize Σ_e weight_e·y_e  s.t.  Σ_c x_c ≤ budget;  y_e ≤ Σ_{c covers e} x_c  ∀e.

Elements = field archetypes (+ anti-hate pseudo-elements ``"_hate:<k>"``).
Weights  = field_share(archetype) × swing(best_hoser_for_that_tag).
Solver   = PuLP/CBC (exact, ILP primary); greedy (1−1/e) marginal-gain as fallback AND
           always as the explainable per-card trace.

Binary coverage (n=1 saturating case) is MVP.  Multi-answer saturating g(n) refinement
is a noted additive extension.

Heuristic note: swing magnitudes are curated constants (_SWING_DEDICATED / _SWING_SOFT),
NOT empirically derived.  Every SideboardPackage carries ``heuristic_note`` labeling this.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from typing import Optional

import duckdb

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.advisory.whattoplay import (
    field_vulnerability_tags,
    vulnerability_tags_for_deck,
    _load_deck_cards,
)
from legacy_engine.colors import compute_deck_colors

log = logging.getLogger(__name__)

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
    """

    name: str
    attacks: frozenset[str]
    colors: frozenset[str]
    max_copies: int
    swing: float


# Seeded from docs/briefs/legacy-metagame.md §6 "Hosers by target"
# Colors use single WUBRG chars; empty = colorless.
# swing: _SWING_DEDICATED (0.20) for dedicated hate, _SWING_SOFT (0.10) for soft/partial answers.
HOSER_CATALOG: dict[str, HoserCard] = {
    # --- Graveyard hate → graveyard-reliant ---
    "Surgical Extraction": HoserCard(
        name="Surgical Extraction",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset({"B"}),
        max_copies=2,
        swing=_SWING_DEDICATED,
    ),
    "Faerie Macabre": HoserCard(
        name="Faerie Macabre",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset({"B"}),
        max_copies=2,
        swing=_SWING_DEDICATED,
    ),
    "Leyline of the Void": HoserCard(
        name="Leyline of the Void",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset({"B"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Endurance": HoserCard(
        name="Endurance",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset({"G"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Containment Priest": HoserCard(
        name="Containment Priest",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset({"W"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Grafdigger's Cage": HoserCard(
        name="Grafdigger's Cage",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset(),          # colorless artifact
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Nihil Spellbomb": HoserCard(
        name="Nihil Spellbomb",
        attacks=frozenset({"graveyard-reliant"}),
        colors=frozenset({"B"}),
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    # --- Combo hate → combo + storm-reliant ---
    "Force of Will": HoserCard(
        name="Force of Will",
        attacks=frozenset({"combo", "storm-reliant"}),
        colors=frozenset({"U"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Flusterstorm": HoserCard(
        name="Flusterstorm",
        attacks=frozenset({"combo", "storm-reliant"}),
        colors=frozenset({"U"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Mindbreak Trap": HoserCard(
        name="Mindbreak Trap",
        attacks=frozenset({"combo", "storm-reliant"}),
        colors=frozenset({"U"}),
        max_copies=2,
        swing=_SWING_DEDICATED,
    ),
    "Thoughtseize": HoserCard(
        name="Thoughtseize",
        attacks=frozenset({"combo", "storm-reliant"}),
        colors=frozenset({"B"}),
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    "Duress": HoserCard(
        name="Duress",
        attacks=frozenset({"combo", "storm-reliant"}),
        colors=frozenset({"B"}),
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    # --- Counter-hosers → _hate pseudo-elements ---
    # These defend the deck against opposing hate rather than attacking archetypes.
    "Veil of Summer": HoserCard(
        name="Veil of Summer",
        attacks=frozenset({"_hate"}),
        colors=frozenset({"G"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Defense Grid": HoserCard(
        name="Defense Grid",
        attacks=frozenset({"_hate"}),
        colors=frozenset(),          # colorless artifact
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    "Carpet of Flowers": HoserCard(
        name="Carpet of Flowers",
        attacks=frozenset({"_hate"}),
        colors=frozenset({"G"}),
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    # --- Greedy-manabase hate → greedy-manabase ---
    "Blood Moon": HoserCard(
        name="Blood Moon",
        attacks=frozenset({"greedy-manabase"}),
        colors=frozenset({"R"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Back to Basics": HoserCard(
        name="Back to Basics",
        attacks=frozenset({"greedy-manabase"}),
        colors=frozenset({"U"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Wasteland": HoserCard(
        name="Wasteland",
        attacks=frozenset({"greedy-manabase"}),
        colors=frozenset(),          # colorless land
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    # --- Artifact/enchantment removal → greedy-manabase (answers Blood Moon/Back to Basics/Chalice) ---
    "Force of Vigor": HoserCard(
        name="Force of Vigor",
        attacks=frozenset({"greedy-manabase"}),
        colors=frozenset({"G"}),
        max_copies=4,
        swing=_SWING_DEDICATED,
    ),
    "Krosan Grip": HoserCard(
        name="Krosan Grip",
        attacks=frozenset({"greedy-manabase"}),
        colors=frozenset({"G"}),
        max_copies=3,
        swing=_SWING_SOFT,
    ),
    # --- Additional useful hosers ---
    "Pyroblast": HoserCard(
        name="Pyroblast",
        attacks=frozenset({"combo", "low-interaction"}),
        colors=frozenset({"R"}),
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    "Hydroblast": HoserCard(
        name="Hydroblast",
        attacks=frozenset({"greedy-manabase", "low-interaction"}),
        colors=frozenset({"U"}),
        max_copies=4,
        swing=_SWING_SOFT,
    ),
    "Chalice of the Void": HoserCard(
        name="Chalice of the Void",
        attacks=frozenset({"combo", "storm-reliant", "low-curve"}),
        colors=frozenset(),          # colorless artifact
        max_copies=2,
        swing=_SWING_DEDICATED,
    ),
}


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
) -> CoverageModel:
    """Build the coverage model: elements with weights + color-prefiltered candidates.

    Elements = field archetypes (weight = share × best_swing_for_that_archetype's_tags)
             + anti-hate pseudo-elements ``"_hate:<k>"`` for each vulnerability tag the
               deck carries that the field is likely to bring hate for.

    Color pre-filter: drop catalog hosers whose required colors are not a subset of
    ``deck_colors`` (colorless/empty-color hosers are always allowed).

    Anti-hate: for each tag ``k`` in ``deck_tags``, estimate how much of the field might
    bring hate for ``k`` against the deck (= Σ_a field_share(a) where archetype ``a``
    has access to counter-hosers).  The heuristic: ``a`` is assumed to bring hate ``k``
    if at least one ``_hate`` catalog hoser castable in ``a``'s colors exists.  Since we
    don't track archetype colors in the field, we use a simpler conservative heuristic:
    every archetype in the field is assumed capable of bringing hate for any tag the deck
    carries (a conservative overestimate; the optimizer then decides if the slot is worth
    it).
    """
    if catalog is None:
        catalog = HOSER_CATALOG

    warnings: list[str] = []

    # --- Step 1: Identify best swing per tag across the (color-prefiltered) catalog ---
    # We compute this globally (not per-deck-color) for the element-weight step, because
    # element weight = best theoretical swing for that tag, not constrained by the deck.
    # Color filtering happens only in candidate_covers.
    best_swing_for_tag: dict[str, float] = {}
    for hoser in catalog.values():
        for tag in hoser.attacks:
            if tag == "_hate":
                continue  # counter-hosers don't directly represent archetype swing
            best_swing_for_tag[tag] = max(best_swing_for_tag.get(tag, 0.0), hoser.swing)

    # --- Step 2: Build element weights for field archetypes ---
    element_weight: dict[str, float] = {}
    for archetype, share in field.shares.items():
        tags = archetype_tags.get(archetype, frozenset())
        # Best swing = max over all tags this archetype carries (any catalog hoser attacks any of them)
        best_swing = max(
            (best_swing_for_tag.get(tag, 0.0) for tag in tags),
            default=0.0,
        )
        weight = share * best_swing
        element_weight[archetype] = weight
        if weight == 0.0 and share > 0.0:
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

    # --- Step 3: Anti-hate pseudo-elements ---
    # For each vulnerability tag the DECK itself carries, estimate the field's hate equity
    # as a pseudo-element weight.  Counter-hosers (attacks={"_hate"}) cover these elements.
    # Conservative heuristic: assume all archetypes in the field can bring hate for the tag
    # if any counter-hoser exists that is castable in some color (since we don't know each
    # archetype's sideboard colors well).  Weight = total field share (conservative overestimate).
    hate_elements_added: set[str] = set()
    if deck_tags:
        total_field_share = sum(field.shares.values())
        for tag in deck_tags:
            # Only create a pseudo-element for tags where counter-hosers exist in the catalog
            # (i.e., "_hate" hosers could defend against hate brought for this tag).
            hate_key = _HATE_ELEMENT_PREFIX + tag
            # Weight = proportion of field share that's expected to bring this hate against us.
            # Heuristic: weight = total field share that is combo/tempo (likely to have interaction).
            # Simpler MVP: weight = Σ field_share over all archetypes that have "low-interaction"
            # NOT in their tags (i.e., likely interactive enough to bring hate).
            # For MVP simplicity, weight = total field share that is non-trivial.
            weight = sum(
                share
                for archetype, share in field.shares.items()
                if share >= 0.01  # skip micro-slivers
            )
            if weight >= _HATE_ELEMENT_MIN_WEIGHT:
                element_weight[hate_key] = weight * _SWING_SOFT
                hate_elements_added.add(tag)

    # --- Step 4: Color-prefiltered candidate hosers ---
    candidate_covers: dict[str, frozenset[str]] = {}
    candidate_meta: dict[str, HoserCard] = {}

    for card_name, hoser in catalog.items():
        # Color pre-filter: hoser.colors must be subset of deck_colors.
        # Empty hoser.colors = colorless → always legal.
        if hoser.colors and not hoser.colors.issubset(deck_colors):
            continue  # drop off-color hosers

        # Compute which elements this hoser covers.
        covered: set[str] = set()

        for archetype, tags in archetype_tags.items():
            if archetype not in element_weight:
                continue
            # This hoser covers the archetype if any of its attacks tags overlap with the archetype's tags.
            if hoser.attacks & tags:
                covered.add(archetype)

        # Counter-hosers (attacks contains "_hate") cover anti-hate pseudo-elements.
        if "_hate" in hoser.attacks:
            for tag in hate_elements_added:
                hate_key = _HATE_ELEMENT_PREFIX + tag
                if hate_key in element_weight:
                    covered.add(hate_key)

        if covered:
            candidate_covers[card_name] = frozenset(covered)
            candidate_meta[card_name] = hoser

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
) -> tuple[dict[str, int], list[PickTrace]]:
    """Greedy (1−1/e) weighted max-coverage.

    Iteratively pick the card with maximum marginal gain (weight of newly-covered elements),
    respecting ``max_copies`` per card, until the budget is exhausted.

    Binary coverage: once an element is covered (y_e = 1), additional copies of the same
    card that cover it provide zero marginal gain for that element.  A 2nd copy is only
    useful if it covers elements not yet covered by the first copy (which can't happen for
    a single card, but can happen when max_copies > 1 is paired with the card's multi-tag
    ``attacks`` that are only partially covered by current picks).

    Returns (card→copies, ordered_trace).
    """
    picks: dict[str, int] = {}          # card → copies picked so far
    trace: list[PickTrace] = []
    covered: set[str] = set()           # elements already covered
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

            # Marginal gain = weight of elements this pick would newly cover.
            # Binary coverage: if the element is already covered, gain = 0 for that element.
            newly = element_ids - covered
            gain = sum(model.element_weight.get(e, 0.0) for e in newly)

            if gain > best_gain or (
                gain == best_gain and gain > 0 and (best_card is None or card_name < best_card)
            ):
                best_gain = gain
                best_card = card_name
                best_newly = newly

        if best_card is None or best_gain == 0.0:
            # No more cards provide positive marginal gain; stop early.
            break

        picks[best_card] = picks.get(best_card, 0) + 1
        covered |= best_newly
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


def _ilp_solve(model: CoverageModel, *, budget: int) -> dict[str, int]:
    """Exact weighted max-coverage via PuLP/CBC.

    Formulation:
      Variables:
        x_c ∈ {0..max_copies} integer for each candidate card c
        y_e ∈ {0,1} binary for each element e
      Objective:
        max Σ_e element_weight[e] · y_e
      Constraints:
        Σ_c x_c ≤ budget              (slot budget)
        y_e ≤ Σ_{c: e ∈ covers(c)} x_c   ∀e  (can only count as covered if a hoser is picked)

    Returns card→copies (only x_c > 0 entries).
    Raises _ILPFailed if CBC is unavailable or status is not Optimal.
    """
    try:
        import pulp
    except ImportError as exc:
        raise _ILPFailed("PuLP not installed") from exc

    prob = pulp.LpProblem("sideboard_max_coverage", pulp.LpMaximize)

    # Decision variables: x_c for each candidate card
    x_vars: dict[str, pulp.LpVariable] = {}
    for card_name, hoser in model.candidate_meta.items():
        safe_name = card_name.replace(" ", "_").replace(",", "").replace("'", "").replace("&", "")
        x_vars[card_name] = pulp.LpVariable(
            name=f"x_{safe_name}",
            lowBound=0,
            upBound=hoser.max_copies,
            cat="Integer",
        )

    # Decision variables: y_e for each element
    y_vars: dict[str, pulp.LpVariable] = {}
    for elem_id in model.element_weight:
        y_vars[elem_id] = pulp.LpVariable(
            name=f"y_{elem_id.replace(' ', '_').replace('-', '_').replace(':', '_')}",
            cat="Binary",
        )

    # Objective: maximize weighted coverage
    prob += pulp.lpSum(
        model.element_weight[e] * y_vars[e]
        for e in model.element_weight
    )

    # Budget constraint
    prob += pulp.lpSum(x_vars.values()) <= budget, "budget"

    # Coverage constraints: y_e ≤ Σ_{c covers e} x_c  for each element e
    for elem_id in model.element_weight:
        covering_cards = [
            x_vars[c]
            for c, elems in model.candidate_covers.items()
            if elem_id in elems and c in x_vars
        ]
        if covering_cards:
            prob += y_vars[elem_id] <= pulp.lpSum(covering_cards), f"cov_{elem_id.replace(' ', '_').replace('-', '_').replace(':', '_')}"
        else:
            # No card covers this element → force y_e = 0
            prob += y_vars[elem_id] == 0, f"nocov_{elem_id.replace(' ', '_').replace('-', '_').replace(':', '_')}"

    # Solve
    try:
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
    except Exception as exc:
        raise _ILPFailed(f"PuLP solve exception: {exc}") from exc

    status = pulp.LpStatus.get(prob.status, "Unknown")
    if status != "Optimal":
        raise _ILPFailed(f"ILP status: {status}")

    # Extract solution
    result: dict[str, int] = {}
    for card_name, var in x_vars.items():
        val = var.value()
        if val is not None and val > 0.5:
            result[card_name] = int(round(val))

    return result


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


def _compute_covered_weight(cards: dict[str, int], model: CoverageModel) -> float:
    """Compute total weight of elements covered by a set of picks."""
    covered: set[str] = set()
    for card_name in cards:
        covered |= model.candidate_covers.get(card_name, frozenset())
    return sum(model.element_weight.get(e, 0.0) for e in covered)


def recommend_sideboard(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    deck_maindeck: dict[str, int],
    *,
    reserved: int = 0,
    solver: str = "ilp",
    catalog: Optional[dict[str, HoserCard]] = None,
) -> SideboardPackage:
    """Recommend a 15-card sideboard via weighted max-coverage.

    Steps:
    1. Resolve deck colors via ``_load_deck_cards`` + ``compute_deck_colors``.
    2. Get deck's vulnerability tags via ``vulnerability_tags_for_deck``.
    3. Get per-archetype tags via ``field_vulnerability_tags``.
    4. Build the coverage model (elements, weights, color-prefiltered candidates).
    5. Solve with ILP (primary) or greedy (fallback / forced).
    6. Always compute the greedy trace (explainable per-card rationale).
    7. Return a SideboardPackage with both results.

    ``solver="greedy"`` forces the greedy path (e.g. for testing or if CBC is unavailable).
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

    # --- Step 4: Build coverage model ---
    model = _build_coverage_model(
        field,
        archetype_tags,
        deck_colors,
        deck_tags,
        catalog=catalog,
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
            heuristic_note=_HEURISTIC_NOTE,
            warnings=tuple(warnings),
        )

    # --- Step 5 + 6: Solve and always compute greedy trace ---
    solver_used = "greedy"
    ilp_cards: dict[str, int] = {}

    if solver == "ilp":
        try:
            ilp_cards = _ilp_solve(model, budget=budget)
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
    greedy_cards, greedy_trace = _greedy_solve(model, budget=budget)

    # Choose final cards based on solver
    final_cards = ilp_cards if solver_used == "ilp" else greedy_cards

    # Compute covered weight for the final solution
    cov_weight = _compute_covered_weight(final_cards, model)

    return SideboardPackage(
        cards=final_cards,
        trace=greedy_trace,
        covered_weight=cov_weight,
        budget=budget,
        reserved=reserved,
        solver_used=solver_used,
        field_source=field.field_source,
        heuristic_note=_HEURISTIC_NOTE,
        warnings=tuple(warnings),
    )
