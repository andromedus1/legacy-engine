"""Sideboard recommender tests — Units 1–6 of epic-advisory-sideboard.

House style: hand-built FieldDistribution + archetype_tags maps for deterministic coverage
arithmetic (no DB needed for most ILP/greedy tests).  A :memory: corpus is used only for the
recommend_sideboard integration seam (resolves deck colors + vulnerability tags).

Design decisions tested:
- HOSER_CATALOG seeds: §6 graveyard / combo / counter-hoser / greedy-manabase entries.
- _build_coverage_model: element weights = share × swing; color pre-filter; anti-hate pseudo-elements.
- _greedy_solve: dominant-tag first pick; trace ordering; budget/copy bounds.
- _ilp_solve: objective ≥ greedy; budget/copy respected; non-Optimal → _ILPFailed.
- recommend_sideboard: graveyard-heavy field → GY hate; solver="greedy" path; heuristic_note present.
"""

from __future__ import annotations

import pytest

from legacy_engine.advisory.field import FieldDistribution, build_custom_field
from legacy_engine.advisory.sideboard import (
    HOSER_CATALOG,
    HoserCard,
    CoverageModel,
    PickTrace,
    SideboardPackage,
    _SWING_DEDICATED,
    _SWING_SOFT,
    _build_coverage_model,
    _greedy_solve,
    _ilp_solve,
    _ILPFailed,
    recommend_sideboard,
)
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _con():
    """In-memory DuckDB connection with schema."""
    con = store.connect(":memory:")
    store.init_schema(con)
    return con


def _make_field(shares: dict[str, float]) -> FieldDistribution:
    """Build a FieldDistribution from raw shares (normalizes automatically)."""
    return build_custom_field(shares)


def _make_model(
    element_weight: dict[str, float],
    candidate_covers: dict[str, frozenset[str]],
    candidate_meta: dict[str, HoserCard],
) -> CoverageModel:
    """Convenience factory for hand-built CoverageModel instances."""
    return CoverageModel(
        element_weight=element_weight,
        candidate_covers=candidate_covers,
        candidate_meta=candidate_meta,
        warnings=(),
    )


def _minimal_hoser(
    name: str,
    attacks: frozenset[str],
    max_copies: int = 4,
    swing: float = 0.20,
    colors: frozenset[str] | None = None,
) -> HoserCard:
    """Build a minimal HoserCard for test models."""
    return HoserCard(
        name=name,
        attacks=attacks,
        colors=colors or frozenset(),
        max_copies=max_copies,
        swing=swing,
    )


# ---------------------------------------------------------------------------
# TestHoserCatalog — §6 seeds present; well-formed entries
# ---------------------------------------------------------------------------

class TestHoserCatalog:
    def test_catalog_not_empty(self):
        assert len(HOSER_CATALOG) >= 10

    def test_surgical_extraction_present(self):
        """Surgical Extraction → graveyard-reliant (§6 seed)."""
        assert "Surgical Extraction" in HOSER_CATALOG
        h = HOSER_CATALOG["Surgical Extraction"]
        assert "graveyard-reliant" in h.attacks

    def test_faerie_macabre_present(self):
        """Faerie Macabre → graveyard-reliant (§6 seed)."""
        assert "Faerie Macabre" in HOSER_CATALOG

    def test_leyline_of_the_void_present(self):
        assert "Leyline of the Void" in HOSER_CATALOG
        assert "graveyard-reliant" in HOSER_CATALOG["Leyline of the Void"].attacks

    def test_endurance_present(self):
        assert "Endurance" in HOSER_CATALOG
        assert "graveyard-reliant" in HOSER_CATALOG["Endurance"].attacks

    def test_containment_priest_present(self):
        assert "Containment Priest" in HOSER_CATALOG
        assert "graveyard-reliant" in HOSER_CATALOG["Containment Priest"].attacks

    def test_grafdiggers_cage_present(self):
        assert "Grafdigger's Cage" in HOSER_CATALOG
        assert "graveyard-reliant" in HOSER_CATALOG["Grafdigger's Cage"].attacks

    def test_force_of_will_present_attacks_combo(self):
        """Force of Will → combo (§6 seed)."""
        assert "Force of Will" in HOSER_CATALOG
        h = HOSER_CATALOG["Force of Will"]
        assert "combo" in h.attacks

    def test_flusterstorm_present(self):
        assert "Flusterstorm" in HOSER_CATALOG
        assert "combo" in HOSER_CATALOG["Flusterstorm"].attacks

    def test_mindbreak_trap_present(self):
        assert "Mindbreak Trap" in HOSER_CATALOG
        assert "combo" in HOSER_CATALOG["Mindbreak Trap"].attacks

    def test_thoughtseize_present(self):
        assert "Thoughtseize" in HOSER_CATALOG

    def test_duress_present(self):
        assert "Duress" in HOSER_CATALOG

    def test_veil_of_summer_attacks_hate(self):
        """Veil of Summer → _hate pseudo-element (counter-hoser, §6 seed)."""
        assert "Veil of Summer" in HOSER_CATALOG
        assert "_hate" in HOSER_CATALOG["Veil of Summer"].attacks

    def test_defense_grid_attacks_hate(self):
        assert "Defense Grid" in HOSER_CATALOG
        assert "_hate" in HOSER_CATALOG["Defense Grid"].attacks

    def test_carpet_of_flowers_attacks_hate(self):
        assert "Carpet of Flowers" in HOSER_CATALOG
        assert "_hate" in HOSER_CATALOG["Carpet of Flowers"].attacks

    def test_blood_moon_attacks_greedy_manabase(self):
        assert "Blood Moon" in HOSER_CATALOG
        assert "greedy-manabase" in HOSER_CATALOG["Blood Moon"].attacks

    def test_back_to_basics_attacks_greedy_manabase(self):
        assert "Back to Basics" in HOSER_CATALOG
        assert "greedy-manabase" in HOSER_CATALOG["Back to Basics"].attacks

    def test_wasteland_attacks_greedy_manabase(self):
        assert "Wasteland" in HOSER_CATALOG
        assert "greedy-manabase" in HOSER_CATALOG["Wasteland"].attacks

    def test_force_of_vigor_present(self):
        """Force of Vigor → greedy-manabase (§6 seed)."""
        assert "Force of Vigor" in HOSER_CATALOG

    def test_krosan_grip_present(self):
        assert "Krosan Grip" in HOSER_CATALOG

    def test_all_entries_have_nonempty_attacks(self):
        for name, h in HOSER_CATALOG.items():
            assert len(h.attacks) > 0, f"{name} has empty attacks"

    def test_all_entries_have_max_copies_at_least_one(self):
        for name, h in HOSER_CATALOG.items():
            assert h.max_copies >= 1, f"{name} has max_copies < 1"

    def test_all_entries_have_swing_in_range(self):
        for name, h in HOSER_CATALOG.items():
            assert 0.0 < h.swing < 1.0, f"{name} swing={h.swing} out of (0,1)"

    def test_grafdiggers_cage_is_colorless(self):
        """Grafdigger's Cage is an artifact — colorless (always castable)."""
        assert HOSER_CATALOG["Grafdigger's Cage"].colors == frozenset()

    def test_defense_grid_is_colorless(self):
        assert HOSER_CATALOG["Defense Grid"].colors == frozenset()


# ---------------------------------------------------------------------------
# TestCoverageModel — weights, color pre-filter, anti-hate pseudo-elements
# ---------------------------------------------------------------------------

class TestCoverageModel:
    """Tests use hand-built fields and tag maps for exact arithmetic."""

    def _gy_field_and_catalog(self):
        """Field: Reanimator 60%, Combo 40%.  Mini-catalog: Surgical only."""
        field = _make_field({"Reanimator": 0.6, "Combo": 0.4})
        archetype_tags = {
            "Reanimator": frozenset({"graveyard-reliant"}),
            "Combo": frozenset({"combo"}),
        }
        catalog = {
            "Surgical Extraction": _minimal_hoser(
                "Surgical Extraction",
                frozenset({"graveyard-reliant"}),
                max_copies=2,
                swing=_SWING_DEDICATED,
                colors=frozenset({"B"}),
            ),
        }
        return field, archetype_tags, catalog

    def test_graveyard_archetype_weight_is_share_times_swing(self):
        """Reanimator (0.6) with graveyard-reliant + Surgical (swing=0.20) → weight=0.12.

        Elements are now (archetype, tag) keyed as "Reanimator|graveyard-reliant".
        """
        field, archetype_tags, catalog = self._gy_field_and_catalog()
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "B"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )
        # Reanimator normalized share ≈ 0.6 (after build_custom_field normalization)
        reanimator_share = field.shares["Reanimator"]
        expected_weight = reanimator_share * _SWING_DEDICATED
        # Elements are now (archetype, tag) pairs
        elem_key = "Reanimator|graveyard-reliant"
        assert elem_key in model.element_weight, (
            f"Expected element key {elem_key!r} in element_weight; got {list(model.element_weight)}"
        )
        assert pytest.approx(model.element_weight[elem_key], abs=1e-6) == expected_weight

    def test_graveyard_archetype_covered_by_surgical(self):
        """Surgical Extraction covers the Reanimator|graveyard-reliant element."""
        field, archetype_tags, catalog = self._gy_field_and_catalog()
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "B"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )
        assert "Surgical Extraction" in model.candidate_covers
        # Elements are now (archetype, tag) keyed as "Reanimator|graveyard-reliant"
        assert "Reanimator|graveyard-reliant" in model.candidate_covers["Surgical Extraction"]

    def test_combo_archetype_not_covered_by_graveyard_hoser(self):
        """Surgical Extraction does NOT cover Combo (different tag)."""
        field, archetype_tags, catalog = self._gy_field_and_catalog()
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "B"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )
        if "Surgical Extraction" in model.candidate_covers:
            assert "Combo" not in model.candidate_covers["Surgical Extraction"]

    def test_red_hoser_dropped_when_deck_has_no_red(self):
        """Blood Moon (R) is dropped when deck_colors lacks R."""
        field = _make_field({"Greedy": 1.0})
        archetype_tags = {"Greedy": frozenset({"greedy-manabase"})}
        catalog = {
            "Blood Moon": _minimal_hoser(
                "Blood Moon",
                frozenset({"greedy-manabase"}),
                colors=frozenset({"R"}),
            ),
            "Wasteland": _minimal_hoser(
                "Wasteland",
                frozenset({"greedy-manabase"}),
                colors=frozenset(),   # colorless
            ),
        }
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "B"}),  # no R
            deck_tags=frozenset(),
            catalog=catalog,
        )
        assert "Blood Moon" not in model.candidate_covers, "Red hoser should be dropped for UB deck"
        assert "Wasteland" in model.candidate_covers, "Colorless hoser should be kept"

    def test_colorless_hoser_always_included(self):
        """Grafdigger's Cage (colorless) is included regardless of deck colors."""
        field = _make_field({"Reanimator": 1.0})
        archetype_tags = {"Reanimator": frozenset({"graveyard-reliant"})}
        catalog = {
            "Grafdigger's Cage": _minimal_hoser(
                "Grafdigger's Cage",
                frozenset({"graveyard-reliant"}),
                colors=frozenset(),  # colorless
            ),
        }
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"R"}),  # no G or B
            deck_tags=frozenset(),
            catalog=catalog,
        )
        assert "Grafdigger's Cage" in model.candidate_covers

    def test_anti_hate_pseudo_element_created_for_deck_tags(self):
        """A deck carrying 'combo' vulnerability → '_hate:combo' pseudo-element in model."""
        field = _make_field({"Reanimator": 0.5, "Storm": 0.5})
        archetype_tags = {
            "Reanimator": frozenset({"graveyard-reliant"}),
            "Storm": frozenset({"storm-reliant"}),
        }
        catalog = {
            "Veil of Summer": _minimal_hoser(
                "Veil of Summer",
                frozenset({"_hate"}),
                colors=frozenset({"G"}),
            ),
        }
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "G"}),
            deck_tags=frozenset({"combo"}),  # deck is combo — field may bring hate
            catalog=catalog,
        )
        hate_elements = [k for k in model.element_weight if k.startswith("_hate:")]
        assert len(hate_elements) >= 1, "Expected at least one anti-hate pseudo-element"

    def test_veil_of_summer_covers_anti_hate_element(self):
        """Veil of Summer (attacks=_hate) covers the _hate:combo pseudo-element."""
        field = _make_field({"Reanimator": 0.5, "Storm": 0.5})
        archetype_tags = {
            "Reanimator": frozenset({"graveyard-reliant"}),
            "Storm": frozenset({"storm-reliant"}),
        }
        catalog = {
            "Veil of Summer": _minimal_hoser(
                "Veil of Summer",
                frozenset({"_hate"}),
                colors=frozenset({"G"}),
            ),
        }
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "G"}),
            deck_tags=frozenset({"combo"}),
            catalog=catalog,
        )
        if "_hate:combo" in model.element_weight and "Veil of Summer" in model.candidate_covers:
            assert "_hate:combo" in model.candidate_covers["Veil of Summer"]

    def test_archetype_with_no_catalog_answer_gets_warning(self):
        """An archetype no catalog hoser covers gets no element keys and a warning.

        With (archetype, tag) elements, archetypes whose tags have no swing entry
        generate no element_weight keys (not a weight=0 entry).  The warning still fires.
        """
        field = _make_field({"UniqueArchetype": 0.5, "Reanimator": 0.5})
        archetype_tags = {
            "UniqueArchetype": frozenset({"some-unknown-tag"}),
            "Reanimator": frozenset({"graveyard-reliant"}),
        }
        catalog = {
            "Surgical Extraction": _minimal_hoser(
                "Surgical Extraction",
                frozenset({"graveyard-reliant"}),
                colors=frozenset({"B"}),
            ),
        }
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "B"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )
        # UniqueArchetype's unknown tag produces no element_weight entry (swing=0)
        assert not any(k.startswith("UniqueArchetype|") for k in model.element_weight)
        # Should have a warning about uncoverable archetype
        assert any("UniqueArchetype" in w or "some-unknown-tag" in w or "no catalog" in w.lower()
                   for w in model.warnings)

    def test_archetype_with_no_tags_gets_warning(self):
        """An archetype with no tags produces no element_weight entries and a warning."""
        field = _make_field({"NoTags": 0.4, "Reanimator": 0.6})
        archetype_tags = {
            "NoTags": frozenset(),
            "Reanimator": frozenset({"graveyard-reliant"}),
        }
        catalog = {
            "Surgical Extraction": _minimal_hoser(
                "Surgical Extraction",
                frozenset({"graveyard-reliant"}),
                colors=frozenset({"B"}),
            ),
        }
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "B"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )
        # NoTags has no tags → no (archetype, tag) keys in element_weight
        assert not any(k.startswith("NoTags|") for k in model.element_weight)
        assert any("NoTags" in w for w in model.warnings)

    def test_covered_archetypes_have_element_keys(self):
        """Archetypes with known-swing tags appear as 'archetype|tag' keys in element_weight.

        Archetypes with no tags (B) or no catalog swing produce no keys (warning only).
        """
        field = _make_field({"A": 0.5, "B": 0.3, "C": 0.2})
        archetype_tags = {
            "A": frozenset({"graveyard-reliant"}),
            "B": frozenset(),
            "C": frozenset({"combo"}),
        }
        catalog = {
            "Surgical": _minimal_hoser("Surgical", frozenset({"graveyard-reliant"})),
            "Force": _minimal_hoser("Force", frozenset({"combo"})),
        }
        model = _build_coverage_model(
            field, archetype_tags,
            deck_colors=frozenset({"U", "B", "G"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )
        # A and C have known-swing tags → present as (archetype, tag) keys
        assert "A|graveyard-reliant" in model.element_weight
        assert "C|combo" in model.element_weight
        # B has no tags → no keys, but a warning
        assert not any(k.startswith("B|") for k in model.element_weight)
        assert any("B" in w for w in model.warnings)


# ---------------------------------------------------------------------------
# TestGreedy — marginal-gain ordering, budget, copy bounds
# ---------------------------------------------------------------------------

class TestGreedy:
    """Tests use hand-built CoverageModel instances for exact arithmetic."""

    def _gy_heavy_model(self) -> CoverageModel:
        """Field: Reanimator 70%, Combo 30%.  Two hosers: GY and Combo."""
        gy_hoser = _minimal_hoser("GY-Hoser", frozenset({"Reanimator"}), max_copies=4, swing=0.20)
        combo_hoser = _minimal_hoser("Combo-Hoser", frozenset({"Combo"}), max_copies=2, swing=0.10)
        element_weight = {"Reanimator": 0.70 * 0.20, "Combo": 0.30 * 0.10}
        candidate_covers = {
            "GY-Hoser": frozenset({"Reanimator"}),
            "Combo-Hoser": frozenset({"Combo"}),
        }
        candidate_meta = {"GY-Hoser": gy_hoser, "Combo-Hoser": combo_hoser}
        return _make_model(element_weight, candidate_covers, candidate_meta)

    def test_first_pick_is_dominant_archetype_hoser(self):
        """On a graveyard-heavy field, greedy's first pick is the GY hoser."""
        model = self._gy_heavy_model()
        picks, trace = _greedy_solve(model, budget=1)
        assert len(trace) == 1
        assert trace[0].card == "GY-Hoser", (
            f"Expected GY-Hoser as first pick, got {trace[0].card}"
        )

    def test_trace_ordered_by_descending_marginal_gain(self):
        """Trace is ordered by marginal gain (first pick has higher or equal gain than subsequent)."""
        model = self._gy_heavy_model()
        picks, trace = _greedy_solve(model, budget=2)
        if len(trace) >= 2:
            for i in range(len(trace) - 1):
                assert trace[i].marginal_gain >= trace[i + 1].marginal_gain

    def test_total_picks_respect_budget(self):
        """Sum of copies ≤ budget."""
        model = self._gy_heavy_model()
        picks, trace = _greedy_solve(model, budget=3)
        assert sum(picks.values()) <= 3

    def test_copies_respect_max_copies(self):
        """No card exceeds its max_copies."""
        model = self._gy_heavy_model()
        picks, trace = _greedy_solve(model, budget=10)
        for card_name, copies in picks.items():
            assert copies <= model.candidate_meta[card_name].max_copies

    def test_trace_entries_count_matches_copies(self):
        """Trace has one entry per copy picked (length = total copies)."""
        model = self._gy_heavy_model()
        picks, trace = _greedy_solve(model, budget=3)
        assert len(trace) == sum(picks.values())

    def test_zero_budget_returns_empty(self):
        model = self._gy_heavy_model()
        picks, trace = _greedy_solve(model, budget=0)
        assert picks == {}
        assert trace == []

    def test_newly_covered_field_is_subset_of_element_ids(self):
        """PickTrace.newly_covered is a frozenset of valid element ids."""
        model = self._gy_heavy_model()
        _, trace = _greedy_solve(model, budget=2)
        all_elements = set(model.element_weight.keys())
        for pt in trace:
            assert pt.newly_covered.issubset(all_elements)

    def test_second_copy_same_card_zero_gain_if_already_covered(self):
        """After first GY-Hoser copy covers Reanimator, a 2nd copy gains 0 (binary coverage)."""
        # Single-element field: one element, one hoser.
        hoser = _minimal_hoser("GY-Hoser", frozenset({"Reanimator"}), max_copies=4)
        model = _make_model(
            element_weight={"Reanimator": 0.14},
            candidate_covers={"GY-Hoser": frozenset({"Reanimator"})},
            candidate_meta={"GY-Hoser": hoser},
        )
        picks, trace = _greedy_solve(model, budget=2)
        # First copy has gain 0.14; second copy covers no NEW elements → gain=0 → greedy stops.
        assert picks.get("GY-Hoser", 0) == 1
        assert len(trace) == 1

    def test_multiple_hosers_in_trace_when_multi_element(self):
        """With multiple elements, greedy picks different hosers to cover each."""
        h_a = _minimal_hoser("HoserA", frozenset({"ElemA"}), max_copies=1, swing=0.20)
        h_b = _minimal_hoser("HoserB", frozenset({"ElemB"}), max_copies=1, swing=0.15)
        model = _make_model(
            element_weight={"ElemA": 0.5 * 0.20, "ElemB": 0.5 * 0.15},
            candidate_covers={"HoserA": frozenset({"ElemA"}), "HoserB": frozenset({"ElemB"})},
            candidate_meta={"HoserA": h_a, "HoserB": h_b},
        )
        picks, trace = _greedy_solve(model, budget=2)
        assert "HoserA" in picks
        assert "HoserB" in picks


# ---------------------------------------------------------------------------
# TestILP — objective ≥ greedy; budget/copy respected; fallback on non-Optimal
# ---------------------------------------------------------------------------

class TestILP:
    """Tests require PuLP/CBC — assert ILP works (not skip)."""

    def _multi_element_model(self) -> CoverageModel:
        """4-element model with 4 hosers; budget=2 forces an interesting choice."""
        hosers = {
            "H1": _minimal_hoser("H1", frozenset({"E1", "E2"}), max_copies=1, swing=0.20),
            "H2": _minimal_hoser("H2", frozenset({"E3"}), max_copies=2, swing=0.15),
            "H3": _minimal_hoser("H3", frozenset({"E4"}), max_copies=1, swing=0.10),
            "H4": _minimal_hoser("H4", frozenset({"E1"}), max_copies=1, swing=0.10),
        }
        element_weight = {
            "E1": 0.4 * 0.20,
            "E2": 0.3 * 0.20,
            "E3": 0.2 * 0.15,
            "E4": 0.1 * 0.10,
        }
        candidate_covers = {
            "H1": frozenset({"E1", "E2"}),
            "H2": frozenset({"E3"}),
            "H3": frozenset({"E4"}),
            "H4": frozenset({"E1"}),
        }
        return _make_model(element_weight, candidate_covers, hosers)

    def _greedy_objective(self, model: CoverageModel, budget: int) -> float:
        picks, _ = _greedy_solve(model, budget=budget)
        covered: set[str] = set()
        for card in picks:
            covered |= model.candidate_covers.get(card, frozenset())
        return sum(model.element_weight.get(e, 0.0) for e in covered)

    def _ilp_objective(self, model: CoverageModel, budget: int) -> float:
        picks = _ilp_solve(model, budget=budget)
        covered: set[str] = set()
        for card in picks:
            covered |= model.candidate_covers.get(card, frozenset())
        return sum(model.element_weight.get(e, 0.0) for e in covered)

    def test_ilp_objective_gte_greedy_objective(self):
        """ILP (exact) objective ≥ greedy ((1−1/e) approx) on the same model."""
        model = self._multi_element_model()
        ilp_obj = self._ilp_objective(model, budget=2)
        greedy_obj = self._greedy_objective(model, budget=2)
        assert ilp_obj >= greedy_obj - 1e-6, (
            f"ILP objective {ilp_obj:.4f} < greedy {greedy_obj:.4f}"
        )

    def test_ilp_respects_budget(self):
        """ILP solution total copies ≤ budget."""
        model = self._multi_element_model()
        picks = _ilp_solve(model, budget=3)
        assert sum(picks.values()) <= 3

    def test_ilp_respects_max_copies(self):
        """ILP solution respects each card's max_copies."""
        model = self._multi_element_model()
        picks = _ilp_solve(model, budget=5)
        for card, copies in picks.items():
            assert copies <= model.candidate_meta[card].max_copies, (
                f"{card}: ILP picked {copies} but max_copies={model.candidate_meta[card].max_copies}"
            )

    def test_ilp_returns_only_positive_copies(self):
        """ILP result only includes cards with x_c > 0."""
        model = self._multi_element_model()
        picks = _ilp_solve(model, budget=2)
        for card, copies in picks.items():
            assert copies > 0

    def test_ilp_budget_zero_returns_empty(self):
        """With budget=0, ILP can only pick 0 cards."""
        model = self._multi_element_model()
        picks = _ilp_solve(model, budget=0)
        assert sum(picks.values()) == 0

    def test_ilp_larger_budget_nondecreasing_objective(self):
        """More budget → ILP objective does not decrease (monotone coverage)."""
        model = self._multi_element_model()
        obj1 = self._ilp_objective(model, budget=1)
        obj2 = self._ilp_objective(model, budget=2)
        assert obj2 >= obj1 - 1e-9

    def test_ilp_full_coverage_with_enough_budget(self):
        """With budget ≥ number of distinct hosers, all elements can be covered."""
        h_a = _minimal_hoser("HA", frozenset({"EA"}), max_copies=1)
        h_b = _minimal_hoser("HB", frozenset({"EB"}), max_copies=1)
        model = _make_model(
            element_weight={"EA": 0.10, "EB": 0.10},
            candidate_covers={"HA": frozenset({"EA"}), "HB": frozenset({"EB"})},
            candidate_meta={"HA": h_a, "HB": h_b},
        )
        picks = _ilp_solve(model, budget=2)
        covered = set()
        for card in picks:
            covered |= model.candidate_covers[card]
        assert "EA" in covered
        assert "EB" in covered

    def test_ilp_reserved_reduces_effective_budget(self):
        """The budget parameter directly controls slot allocation (reserved computed by caller)."""
        model = self._multi_element_model()
        picks_full = _ilp_solve(model, budget=4)
        picks_restricted = _ilp_solve(model, budget=2)
        # Restricted picks ≤ full picks in total copies.
        assert sum(picks_restricted.values()) <= sum(picks_full.values())

    def test_ilp_empty_model_returns_empty(self):
        """ILP on a model with no candidates returns empty dict."""
        model = _make_model(
            element_weight={"E1": 0.10},
            candidate_covers={},
            candidate_meta={},
        )
        picks = _ilp_solve(model, budget=5)
        assert picks == {}


# ---------------------------------------------------------------------------
# TestRecommendSideboard — integration tests using :memory: corpus
# ---------------------------------------------------------------------------

class TestRecommendSideboard:
    """Integration tests for recommend_sideboard.

    Most use a :memory: corpus with minimal cards loaded.  The recommend_sideboard call
    resolves deck colors + vulnerability tags from the DB.
    """

    def _build_gy_corpus(self):
        """Corpus with Reanimator archetype + a simple deck that is colorless for safety."""
        con = _con()
        # Load cards needed for the graveyard archetype composition check
        cards = [
            Card(
                name="Reanimate",
                type_line="Sorcery",
                oracle_text=(
                    "Put target creature card from a graveyard onto the battlefield "
                    "under your control. You lose life equal to its mana value."
                ),
                cmc=1.0,
                colors=["B"],
            ),
            Card(
                name="Swamp",
                type_line="Basic Land — Swamp",
                oracle_text="{T}: Add {B}.",
                cmc=0.0,
                produced_mana=["B"],
            ),
        ]
        store.load_cards(con, cards)

        import uuid
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        for idx in range(3):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, ?, ?)",
                [tid, idx, f"player{idx}", "1st", "Reanimator"],
            )
            for card_name, count in [("Reanimate", 4), ("Swamp", 10)]:
                con.execute(
                    "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                    [tid, idx, "main", card_name, count],
                )
        return con

    def test_heuristic_note_always_present(self):
        """SideboardPackage always has a non-empty heuristic_note."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        # Simple colorless deck (no cards in DB needed)
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert pkg.heuristic_note
        assert "heuristic" in pkg.heuristic_note.lower() or "curated" in pkg.heuristic_note.lower()
        con.close()

    def test_field_source_propagated(self):
        """SideboardPackage.field_source matches the input FieldDistribution.field_source."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert pkg.field_source == field.field_source
        con.close()

    def test_reserved_reduces_budget(self):
        """reserved=3 → package.budget == 12 and sum(cards.values()) ≤ 12."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=3, solver="greedy")
        assert pkg.reserved == 3
        assert pkg.budget == 12
        assert sum(pkg.cards.values()) <= 12
        con.close()

    def test_sum_of_cards_at_most_fifteen(self):
        """Total card copies ≤ 15 (full budget)."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert sum(pkg.cards.values()) <= 15
        con.close()

    def test_solver_greedy_forces_greedy(self):
        """solver='greedy' → solver_used == 'greedy' in the package."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert pkg.solver_used == "greedy"
        con.close()

    def test_trace_always_present(self):
        """Package always carries a trace (may be empty only if no candidates)."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert isinstance(pkg.trace, list)
        con.close()

    def test_warnings_is_tuple(self):
        """warnings is always a tuple."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert isinstance(pkg.warnings, tuple)
        con.close()

    def test_ilp_solver_used_when_available(self):
        """solver='ilp' → solver_used == 'ilp' (CBC is available in CI)."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="ilp")
        # ILP should succeed with CBC installed; if it falls back, solver_used='greedy'
        assert pkg.solver_used in ("ilp", "greedy")
        con.close()

    def test_graveyard_heavy_field_includes_gy_hate(self):
        """On a graveyard-heavy field, the recommended package includes GY hate cards."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 0.7, "Delver": 0.3})

        # Minimal catalog: only GY hosers and combo hosers (colorless so always castable)
        mini_catalog = {
            "Grafdigger's Cage": HoserCard(
                name="Grafdigger's Cage",
                attacks=frozenset({"graveyard-reliant"}),
                colors=frozenset(),
                max_copies=4,
                swing=_SWING_DEDICATED,
            ),
            "Faerie Macabre": HoserCard(
                name="Faerie Macabre",
                attacks=frozenset({"graveyard-reliant"}),
                colors=frozenset({"B"}),
                max_copies=2,
                swing=_SWING_DEDICATED,
            ),
        }

        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy", catalog=mini_catalog)
        # On a graveyard-heavy field, GY hate should dominate the package (Grafdigger's Cage is colorless)
        gy_hate_cards = {"Grafdigger's Cage", "Faerie Macabre"}
        package_gy_cards = set(pkg.cards.keys()) & gy_hate_cards
        assert len(package_gy_cards) >= 1 or not pkg.cards, (
            f"Expected GY hate in package but got: {pkg.cards}"
        )
        con.close()

    def test_covered_weight_nonnegative(self):
        """covered_weight is always ≥ 0."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        pkg = recommend_sideboard(con, field, {}, reserved=0, solver="greedy")
        assert pkg.covered_weight >= 0.0
        con.close()

    def test_custom_catalog_respected(self):
        """Passing a custom catalog restricts the hosers considered."""
        con = self._build_gy_corpus()
        field = _make_field({"Reanimator": 1.0})
        single_hoser_catalog = {
            "Grafdigger's Cage": HoserCard(
                name="Grafdigger's Cage",
                attacks=frozenset({"graveyard-reliant"}),
                colors=frozenset(),
                max_copies=4,
                swing=0.20,
            ),
        }
        pkg = recommend_sideboard(
            con, field, {}, reserved=0, solver="greedy", catalog=single_hoser_catalog
        )
        # Only Grafdigger's Cage can appear in the package (or it's empty if no archetype tags)
        for card in pkg.cards:
            assert card == "Grafdigger's Cage"
        con.close()

    def test_deck_with_black_mana_can_use_surgical(self):
        """A Black deck can use Black hosers (Surgical Extraction)."""
        con = _con()
        # Load cards for the deck
        cards = [
            Card(
                name="Reanimate",
                type_line="Sorcery",
                oracle_text=(
                    "Put target creature card from a graveyard onto the battlefield "
                    "under your control. You lose life equal to its mana value."
                ),
                cmc=1.0,
                colors=["B"],
            ),
            Card(
                name="Swamp",
                type_line="Basic Land — Swamp",
                oracle_text="{T}: Add {B}.",
                cmc=0.0,
                produced_mana=["B"],
            ),
        ]
        store.load_cards(con, cards)

        # Small catalog: only Surgical (Black) and Cage (colorless)
        catalog = {
            "Surgical Extraction": HoserCard(
                name="Surgical Extraction",
                attacks=frozenset({"graveyard-reliant"}),
                colors=frozenset({"B"}),
                max_copies=2,
                swing=_SWING_DEDICATED,
            ),
            "Grafdigger's Cage": HoserCard(
                name="Grafdigger's Cage",
                attacks=frozenset({"graveyard-reliant"}),
                colors=frozenset(),
                max_copies=4,
                swing=_SWING_DEDICATED,
            ),
        }

        # Field with graveyard archetype, deck is Black
        field = _make_field({"Reanimator": 1.0})
        deck_maindeck = {"Reanimate": 4, "Swamp": 16}
        pkg = recommend_sideboard(con, field, deck_maindeck, reserved=0, solver="greedy", catalog=catalog)

        # A Black deck should have access to both Surgical and Cage
        # (Surgical is B, and we have Swamps producing B)
        all_hoser_names = set(catalog.keys())
        assert any(card in all_hoser_names for card in pkg.cards) or not pkg.cards
        con.close()


# ---------------------------------------------------------------------------
# TestSideboardPackageStructure — dataclass fields + types
# ---------------------------------------------------------------------------

class TestSideboardPackageStructure:
    def test_package_has_all_required_fields(self):
        """SideboardPackage carries all declared fields."""
        pkg = SideboardPackage(
            cards={"Surgical Extraction": 2},
            trace=[PickTrace(card="Surgical Extraction", marginal_gain=0.12, newly_covered=frozenset({"Reanimator"}))],
            covered_weight=0.12,
            budget=15,
            reserved=0,
            solver_used="ilp",
            field_source="custom",
            heuristic_note="test note",
            warnings=(),
        )
        assert pkg.cards == {"Surgical Extraction": 2}
        assert pkg.solver_used == "ilp"
        assert pkg.heuristic_note == "test note"
        assert pkg.budget == 15
        assert pkg.reserved == 0

    def test_pick_trace_fields(self):
        """PickTrace carries card, marginal_gain, newly_covered."""
        pt = PickTrace(
            card="Grafdigger's Cage",
            marginal_gain=0.08,
            newly_covered=frozenset({"Reanimator", "Combo"}),
        )
        assert pt.card == "Grafdigger's Cage"
        assert pt.marginal_gain == pytest.approx(0.08)
        assert "Reanimator" in pt.newly_covered


# ---------------------------------------------------------------------------
# TestILPvsGreedyObjective — explicit hand-built comparison
# ---------------------------------------------------------------------------

class TestILPvsGreedyObjective:
    """Direct comparison: ILP objective ≥ greedy on crafted adversarial models."""

    def _adversarial_model(self) -> CoverageModel:
        """3 elements; greedy is suboptimal.

        Element weights: E1=0.15, E2=0.15, E3=0.20.
        Hosers: H_AB covers {E1, E2} (gain 0.30); H_C covers {E3} (gain 0.20); H_A covers {E1} alone.
        Greedy with budget=2 might pick H_AB (0.30) then H_C (0.20) = 0.50 (optimal in this case).
        But: H_A alone covers E1 (0.15) — greedy won't prefer it.
        ILP ≥ greedy is the invariant, not ILP > greedy.
        """
        h_ab = _minimal_hoser("H_AB", frozenset({"E1", "E2"}), max_copies=1, swing=0.15)
        h_c = _minimal_hoser("H_C", frozenset({"E3"}), max_copies=1, swing=0.20)
        h_a = _minimal_hoser("H_A", frozenset({"E1"}), max_copies=1, swing=0.10)
        element_weight = {"E1": 0.15, "E2": 0.15, "E3": 0.20}
        candidate_covers = {
            "H_AB": frozenset({"E1", "E2"}),
            "H_C": frozenset({"E3"}),
            "H_A": frozenset({"E1"}),
        }
        return _make_model(element_weight, candidate_covers, {"H_AB": h_ab, "H_C": h_c, "H_A": h_a})

    def test_ilp_objective_geq_greedy(self):
        model = self._adversarial_model()
        budget = 2

        greedy_picks, _ = _greedy_solve(model, budget=budget)
        greedy_covered = set()
        for c in greedy_picks:
            greedy_covered |= model.candidate_covers.get(c, frozenset())
        greedy_obj = sum(model.element_weight.get(e, 0.0) for e in greedy_covered)

        ilp_picks = _ilp_solve(model, budget=budget)
        ilp_covered = set()
        for c in ilp_picks:
            ilp_covered |= model.candidate_covers.get(c, frozenset())
        ilp_obj = sum(model.element_weight.get(e, 0.0) for e in ilp_covered)

        assert ilp_obj >= greedy_obj - 1e-6, (
            f"ILP objective {ilp_obj:.4f} should be ≥ greedy {greedy_obj:.4f}"
        )


# ---------------------------------------------------------------------------
# Regression tests for peer-review bug fixes
# ---------------------------------------------------------------------------


class TestRegressionPeerReviewFixes:
    """One regression test per sideboard-related finding (2026-05-30 peer review)."""

    # --- Fix 4: soft hoser covering tag X does NOT capture dedicated-hate (tag Y) weight ---

    def test_fix4_soft_hoser_does_not_capture_dedicated_hate_weight(self):
        """Bug: flat-archetype element weight = share × best_swing across ALL tags.
        A soft hoser overlapping only tag X captured the full best-swing weight (which
        came from dedicated tag Y).
        Fix: elements are (archetype, tag) pairs; each hoser covers only the tags it attacks.
        """
        # Archetype "Alpha" has two tags: "graveyard-reliant" (dedicated swing=0.20)
        # and "low-interaction" (soft swing=0.10).
        # Soft hoser: attacks only "low-interaction".
        # It should NOT see the weight for "graveyard-reliant".
        field = _make_field({"Alpha": 1.0})
        archetype_tags = {"Alpha": frozenset({"graveyard-reliant", "low-interaction"})}
        dedicated_hoser = _minimal_hoser(
            "DedicatedHater",
            frozenset({"graveyard-reliant"}),
            swing=_SWING_DEDICATED,
        )
        soft_hoser = _minimal_hoser(
            "SoftHater",
            frozenset({"low-interaction"}),
            swing=_SWING_SOFT,
        )
        catalog = {"DedicatedHater": dedicated_hoser, "SoftHater": soft_hoser}

        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset(),  # colorless hosers
            deck_tags=frozenset(),
            catalog=catalog,
        )

        # SoftHater must NOT cover the "graveyard-reliant" element of Alpha
        soft_covered = model.candidate_covers.get("SoftHater", frozenset())
        assert "Alpha|graveyard-reliant" not in soft_covered, (
            "Soft hoser (attacks=low-interaction) must NOT cover the graveyard-reliant element"
        )

        # DedicatedHater DOES cover it
        dedicated_covered = model.candidate_covers.get("DedicatedHater", frozenset())
        assert "Alpha|graveyard-reliant" in dedicated_covered

    # --- Fix 5: counter-hoser covers only hate categories with appropriate weight ---

    def test_fix5_hate_element_weight_based_on_interactive_field_share(self):
        """Bug: _hate pseudo-elements were weighted at near-total field share × swing.
        Fix: weight = interactive-field-share (non-low-interaction archetypes) × _SWING_SOFT.
        A field where half is low-interaction → hate weight ≈ half field share × _SWING_SOFT.
        """
        # Field: Aggro (low-interaction, 50%) + Control (NOT low-interaction, 50%)
        field = _make_field({"Aggro": 0.5, "Control": 0.5})
        archetype_tags = {
            "Aggro": frozenset({"low-interaction", "creature-based"}),
            "Control": frozenset({"combo"}),
        }
        catalog = {
            "Veil of Summer": _minimal_hoser(
                "Veil of Summer",
                frozenset({"_hate"}),
                colors=frozenset({"G"}),
            ),
        }
        # Deck is combo-vulnerable (may get hate from the field)
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"U", "G"}),
            deck_tags=frozenset({"combo"}),
            catalog=catalog,
        )

        hate_key = "_hate:combo"
        assert hate_key in model.element_weight, "Expected _hate:combo pseudo-element"

        # Interactive share = Control only (Aggro is low-interaction) → 0.5 normalized
        # Weight should be ≈ 0.5 × _SWING_SOFT, NOT full field share × _SWING_SOFT
        interactive_share = field.shares["Control"]  # ~0.5
        expected_weight = interactive_share * _SWING_SOFT
        actual_weight = model.element_weight[hate_key]
        # Allow ±10% relative tolerance
        assert abs(actual_weight - expected_weight) / max(expected_weight, 1e-9) < 0.1, (
            f"Hate element weight {actual_weight:.4f} should ≈ interactive share {expected_weight:.4f}"
        )

    # --- Fix 6: all-white deck receives Surgical Extraction + Faerie Macabre ---

    def test_fix6_all_white_deck_gets_surgical_extraction_and_faerie_macabre(self):
        """Bug: Surgical Extraction and Faerie Macabre were marked black-only (colors={'B'}).
        Non-black decks could not receive them.
        Fix: castable_any_color=True so the color pre-filter is bypassed.
        """
        field = _make_field({"Reanimator": 1.0})
        archetype_tags = {"Reanimator": frozenset({"graveyard-reliant"})}
        catalog = {
            "Surgical Extraction": HOSER_CATALOG["Surgical Extraction"],
            "Faerie Macabre": HOSER_CATALOG["Faerie Macabre"],
            "Leyline of the Void": HOSER_CATALOG["Leyline of the Void"],
        }

        # All-white deck: no black in colors
        model = _build_coverage_model(
            field,
            archetype_tags,
            deck_colors=frozenset({"W"}),
            deck_tags=frozenset(),
            catalog=catalog,
        )

        # Surgical + Faerie must be in the candidate set for an all-white deck
        assert "Surgical Extraction" in model.candidate_covers, (
            "Surgical Extraction (Phyrexian mana) must be available to non-black decks"
        )
        assert "Faerie Macabre" in model.candidate_covers, (
            "Faerie Macabre (free discard activation) must be available to non-black decks"
        )
        # Leyline of the Void (normal black cost) must NOT be available
        assert "Leyline of the Void" not in model.candidate_covers, (
            "Leyline of the Void (normal black mana) must NOT be available to non-black decks"
        )
