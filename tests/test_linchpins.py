"""Archetype linchpin model tests — Unit 4 of feature-sb-effect-tagging-model.

House style mirrors test_whattoplay.py / test_sideboard.py: hand-built ``Card`` fixtures via a
local ``_make_card`` helper, no DB required (derivation is pure per objective-search-split).
Loader tests mirror TestHoserCatalog's fail-fast-citing-the-entry style.
"""

from __future__ import annotations

import json

import pytest

from legacy_engine.advisory.linchpins import (
    Linchpin,
    LINCHPIN_OVERRIDES,
    _DERIVED_CENTRALITY,
    _LINCHPIN_INCLUSION,
    _infer_neutralized_by,
    _load_default_linchpin_overrides,
    _merge_linchpins,
    derive_linchpins,
    linchpins_for_archetype,
    load_linchpin_overrides,
)
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card(**kwargs) -> Card:
    """Construct a Card with defaults for unspecified fields (mirrors test_whattoplay.py)."""
    defaults = dict(name="Test Card", type_line="Instant", oracle_text="", cmc=1.0)
    defaults.update(kwargs)
    return Card(**defaults)


# ---------------------------------------------------------------------------
# TestDeriveLinchpins — pure composition-derived candidates
# ---------------------------------------------------------------------------

class TestDeriveLinchpins:
    def test_tutor_role_qualifies_at_high_inclusion(self):
        tutor = _make_card(
            name="Totally Not Demonic Tutor",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put it into your hand, then shuffle.",
        )
        result = derive_linchpins(
            "TestArch", [(tutor, 1)], {"Totally Not Demonic Tutor": 0.95}
        )
        assert len(result) == 1
        lp = result[0]
        assert lp.archetype == "TestArch"
        assert lp.name == "Totally Not Demonic Tutor"
        assert lp.role == "combo-tutor"
        assert lp.centrality == _DERIVED_CENTRALITY

    def test_storm_role_maps_to_key_payoff(self):
        storm_payoff = _make_card(
            name="Test Storm Payoff",
            type_line="Sorcery",
            oracle_text=(
                "Storm (When you cast this spell, copy it for each spell cast before it this "
                "turn.)\nEach opponent loses 1 life."
            ),
        )
        result = derive_linchpins(
            "TestArch", [(storm_payoff, 1)], {"Test Storm Payoff": 0.92}
        )
        assert len(result) == 1
        assert result[0].role == "key-payoff"

    def test_ritual_role_maps_to_combo_engine(self):
        ritual = _make_card(
            name="Test Ritual",
            type_line="Instant",
            oracle_text="Add {B}{B}{B}.",
        )
        result = derive_linchpins("TestArch", [(ritual, 1)], {"Test Ritual": 1.0})
        assert len(result) == 1
        assert result[0].role == "combo-engine"

    def test_fast_mana_role_maps_to_combo_engine(self):
        petal = _make_card(
            name="Lotus Petal",
            type_line="Artifact",
            oracle_text="{T}, Sacrifice Lotus Petal: Add one mana of any color.",
        )
        result = derive_linchpins("TestArch", [(petal, 1)], {"Lotus Petal": 1.0})
        assert len(result) == 1
        assert result[0].role == "combo-engine"

    def test_below_inclusion_threshold_not_derived(self):
        tutor = _make_card(
            name="Totally Not Demonic Tutor",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put it into your hand, then shuffle.",
        )
        result = derive_linchpins(
            "TestArch", [(tutor, 1)], {"Totally Not Demonic Tutor": _LINCHPIN_INCLUSION - 0.01}
        )
        assert result == []

    def test_no_matching_role_not_derived_even_at_full_inclusion(self):
        cantrip = _make_card(
            name="Test Cantrip",
            type_line="Instant",
            oracle_text="Draw a card.",
        )
        result = derive_linchpins("TestArch", [(cantrip, 1)], {"Test Cantrip": 1.0})
        assert result == []

    def test_missing_from_inclusion_pct_treated_as_zero(self):
        tutor = _make_card(
            name="Totally Not Demonic Tutor",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put it into your hand, then shuffle.",
        )
        result = derive_linchpins("TestArch", [(tutor, 1)], {})
        assert result == []

    def test_role_priority_prefers_tutor_over_storm(self):
        both = _make_card(
            name="Test Multi Role",
            type_line="Sorcery",
            oracle_text=(
                "Search your library for a card, put it into your hand, then shuffle.\n"
                "Storm (When you cast this spell, copy it for each spell cast before it this turn.)"
            ),
        )
        result = derive_linchpins("TestArch", [(both, 1)], {"Test Multi Role": 1.0})
        assert len(result) == 1
        assert result[0].role == "combo-tutor"

    def test_empty_cards_with_counts_returns_empty(self):
        assert derive_linchpins("TestArch", [], {}) == []


# ---------------------------------------------------------------------------
# TestInferNeutralizedBy — capability-token inference from type_line/oracle_text
# ---------------------------------------------------------------------------

class TestInferNeutralizedBy:
    def test_artifact_with_activated_ability(self):
        grindstone_like = _make_card(
            name="Grindstone-Alike",
            type_line="Artifact",
            oracle_text="{3}, {T}: Target player mills two cards.",
        )
        tags = _infer_neutralized_by(grindstone_like)
        assert tags == frozenset(
            {"artifact-ability-lock", "artifact-bounce", "artifact-removal"}
        )

    def test_artifact_without_activated_ability(self):
        chalice_like = _make_card(
            name="Chalice-Alike",
            type_line="Artifact",
            oracle_text=(
                "This artifact enters with X charge counters on it.\n"
                "Whenever a player casts a spell with mana value equal to the number of charge "
                "counters on this artifact, counter that spell."
            ),
        )
        tags = _infer_neutralized_by(chalice_like)
        assert tags == frozenset({"artifact-removal"})

    def test_creature_gets_removal_and_sweep(self):
        creature = _make_card(name="Test Creature", type_line="Creature — Human", oracle_text="")
        assert _infer_neutralized_by(creature) == frozenset({"creature-removal", "board-sweep"})

    def test_enchantment_gets_enchantment_removal(self):
        ench = _make_card(name="Test Enchantment", type_line="Enchantment", oracle_text="")
        assert _infer_neutralized_by(ench) == frozenset({"enchantment-removal"})

    def test_instant_gets_counter_on_cast(self):
        instant = _make_card(name="Test Instant", type_line="Instant", oracle_text="")
        assert _infer_neutralized_by(instant) == frozenset({"counter-on-cast"})

    def test_sorcery_with_graveyard_recursion_gets_both(self):
        reanimate_like = _make_card(
            name="Reanimate-Alike",
            type_line="Sorcery",
            oracle_text="Return target creature card from your graveyard to the battlefield.",
        )
        assert _infer_neutralized_by(reanimate_like) == frozenset(
            {"counter-on-cast", "exile-graveyard"}
        )

    def test_land_infers_nothing(self):
        land = _make_card(name="Test Land", type_line="Basic Land — Island", oracle_text="")
        assert _infer_neutralized_by(land) == frozenset()


# ---------------------------------------------------------------------------
# TestLoadLinchpinOverrides — curated-json-resource-loader fail-fast validation
# ---------------------------------------------------------------------------

def _write_json(tmp_path, data) -> str:
    path = tmp_path / "linchpins.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


class TestLoadLinchpinOverrides:
    def test_valid_file_loads(self, tmp_path):
        path = _write_json(
            tmp_path,
            {
                "version": 1,
                "linchpins": {
                    "Painter": [
                        {
                            "name": "Grindstone",
                            "role": "combo-engine",
                            "centrality": 1.0,
                            "neutralized_by": ["artifact-ability-lock", "artifact-bounce"],
                        }
                    ]
                },
            },
        )
        result = load_linchpin_overrides(path)
        assert list(result.keys()) == ["Painter"]
        lp = result["Painter"][0]
        assert lp == Linchpin(
            archetype="Painter",
            name="Grindstone",
            role="combo-engine",
            centrality=1.0,
            neutralized_by=frozenset({"artifact-ability-lock", "artifact-bounce"}),
        )

    def test_neutralized_by_defaults_to_empty_when_omitted(self, tmp_path):
        path = _write_json(
            tmp_path,
            {
                "version": 1,
                "linchpins": {"X": [{"name": "Y", "role": "key-payoff", "centrality": 0.5}]},
            },
        )
        result = load_linchpin_overrides(path)
        assert result["X"][0].neutralized_by == frozenset()

    @pytest.mark.parametrize("bad_centrality", [0.0, -0.5, 1.1, 2.0])
    def test_centrality_out_of_range_raises(self, tmp_path, bad_centrality):
        path = _write_json(
            tmp_path,
            {
                "version": 1,
                "linchpins": {
                    "Painter": [
                        {"name": "Grindstone", "role": "combo-engine", "centrality": bad_centrality}
                    ]
                },
            },
        )
        with pytest.raises(ValueError, match="Painter.*Grindstone"):
            load_linchpin_overrides(path)

    def test_non_numeric_centrality_raises(self, tmp_path):
        path = _write_json(
            tmp_path,
            {
                "version": 1,
                "linchpins": {
                    "Painter": [{"name": "Grindstone", "role": "combo-engine", "centrality": "high"}]
                },
            },
        )
        with pytest.raises(ValueError, match="Grindstone"):
            load_linchpin_overrides(path)

    def test_missing_name_raises(self, tmp_path):
        path = _write_json(
            tmp_path,
            {"version": 1, "linchpins": {"Painter": [{"role": "combo-engine", "centrality": 1.0}]}},
        )
        with pytest.raises(ValueError, match="Painter"):
            load_linchpin_overrides(path)

    def test_missing_role_raises(self, tmp_path):
        path = _write_json(
            tmp_path,
            {"version": 1, "linchpins": {"Painter": [{"name": "Grindstone", "centrality": 1.0}]}},
        )
        with pytest.raises(ValueError, match="Grindstone"):
            load_linchpin_overrides(path)

    def test_neutralized_by_not_a_list_raises(self, tmp_path):
        path = _write_json(
            tmp_path,
            {
                "version": 1,
                "linchpins": {
                    "Painter": [
                        {
                            "name": "Grindstone",
                            "role": "combo-engine",
                            "centrality": 1.0,
                            "neutralized_by": "artifact-removal",
                        }
                    ]
                },
            },
        )
        with pytest.raises(ValueError, match="Grindstone"):
            load_linchpin_overrides(path)

    def test_entries_not_a_list_raises(self, tmp_path):
        path = _write_json(tmp_path, {"version": 1, "linchpins": {"Painter": {"not": "a list"}}})
        with pytest.raises(ValueError, match="Painter"):
            load_linchpin_overrides(path)

    def test_linchpins_key_not_a_dict_raises(self, tmp_path):
        path = _write_json(tmp_path, {"version": 1, "linchpins": ["not", "a", "dict"]})
        with pytest.raises(ValueError, match="linchpins"):
            load_linchpin_overrides(path)

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_linchpin_overrides(tmp_path / "does_not_exist.json")


# ---------------------------------------------------------------------------
# TestLoadDefaultLinchpinOverrides — module-level default + degrade-to-empty
# ---------------------------------------------------------------------------

class TestLoadDefaultLinchpinOverrides:
    def test_shipped_registry_loads_clean(self):
        from legacy_engine.config import LINCHPINS_REGISTRY_PATH

        result = load_linchpin_overrides(LINCHPINS_REGISTRY_PATH)
        assert "Painter" in result
        names = {lp.name for lp in result["Painter"]}
        assert "Grindstone" in names

    def test_module_level_registry_is_bound_and_nonempty(self):
        assert isinstance(LINCHPIN_OVERRIDES, dict)
        assert "Painter" in LINCHPIN_OVERRIDES

    def test_degrades_to_empty_dict_on_bad_path(self, monkeypatch, tmp_path):
        import legacy_engine.config as config_module

        monkeypatch.setattr(
            config_module, "LINCHPINS_REGISTRY_PATH", tmp_path / "does_not_exist.json"
        )
        assert _load_default_linchpin_overrides() == {}

    def test_degrades_to_empty_dict_on_malformed_file(self, monkeypatch, tmp_path):
        import legacy_engine.config as config_module

        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps({"version": 1, "linchpins": {"X": [{"name": ""}]}}))
        monkeypatch.setattr(config_module, "LINCHPINS_REGISTRY_PATH", bad_path)
        assert _load_default_linchpin_overrides() == {}


# ---------------------------------------------------------------------------
# TestMergeLinchpins — pure merge logic (curated wins by name, case-insensitive)
# ---------------------------------------------------------------------------

class TestMergeLinchpins:
    def test_curated_wins_over_derived_same_name(self):
        derived = [
            Linchpin(
                archetype="A", name="Grindstone", role="combo-engine",
                centrality=_DERIVED_CENTRALITY, neutralized_by=frozenset(),
            )
        ]
        curated = [
            Linchpin(
                archetype="A", name="Grindstone", role="combo-engine",
                centrality=1.0, neutralized_by=frozenset({"artifact-ability-lock"}),
            )
        ]
        merged = _merge_linchpins(derived, curated)
        assert len(merged) == 1
        assert merged[0].centrality == 1.0

    def test_curated_match_is_case_insensitive(self):
        derived = [
            Linchpin(
                archetype="A", name="grindstone", role="combo-engine",
                centrality=_DERIVED_CENTRALITY, neutralized_by=frozenset(),
            )
        ]
        curated = [
            Linchpin(
                archetype="A", name="Grindstone", role="combo-engine",
                centrality=1.0, neutralized_by=frozenset(),
            )
        ]
        merged = _merge_linchpins(derived, curated)
        assert len(merged) == 1
        assert merged[0].centrality == 1.0

    def test_unmatched_derived_kept_alongside_curated(self):
        derived = [
            Linchpin(
                archetype="A", name="Other Engine Piece", role="combo-tutor",
                centrality=_DERIVED_CENTRALITY, neutralized_by=frozenset(),
            )
        ]
        curated = [
            Linchpin(
                archetype="A", name="Grindstone", role="combo-engine",
                centrality=1.0, neutralized_by=frozenset(),
            )
        ]
        merged = _merge_linchpins(derived, curated)
        names = {lp.name for lp in merged}
        assert names == {"Other Engine Piece", "Grindstone"}

    def test_empty_curated_returns_derived_unchanged(self):
        derived = [
            Linchpin(
                archetype="A", name="X", role="combo-tutor",
                centrality=_DERIVED_CENTRALITY, neutralized_by=frozenset(),
            )
        ]
        assert _merge_linchpins(derived, []) == derived


# ---------------------------------------------------------------------------
# TestLinchpinsForArchetype — the public merge entry point (acceptance criteria)
# ---------------------------------------------------------------------------

class TestLinchpinsForArchetype:
    def test_painter_grindstone_curated_centrality_beats_derived_default(self, monkeypatch):
        """AC: curated override (1.0) wins even though derivation would default to 0.6."""
        import legacy_engine.advisory.linchpins as linchpins_module

        monkeypatch.setattr(
            linchpins_module,
            "LINCHPIN_OVERRIDES",
            {
                "Painter": [
                    Linchpin(
                        archetype="Painter", name="Grindstone", role="combo-engine",
                        centrality=1.0, neutralized_by=frozenset({"artifact-ability-lock"}),
                    )
                ]
            },
        )
        # A synthetic Grindstone whose text WOULD trigger derivation (tutor role) at 0.95
        # inclusion, so this test proves the override wins over a genuine derived candidate —
        # not merely that a card absent from derivation defaults to the curated value.
        grindstone_would_derive = _make_card(
            name="Grindstone",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put it into your hand, then shuffle.",
        )
        derived_only = derive_linchpins(
            "Painter", [(grindstone_would_derive, 1)], {"Grindstone": 0.95}
        )
        assert derived_only[0].centrality == _DERIVED_CENTRALITY  # sanity: derivation alone is 0.6

        result = linchpins_for_archetype(
            "Painter", [(grindstone_would_derive, 1)], {"Grindstone": 0.95}
        )
        assert len(result) == 1
        assert result[0].name == "Grindstone"
        assert result[0].centrality == 1.0

    def test_shipped_registry_painter_grindstone_is_centrality_one(self):
        """AC (against the real shipped catalog, no monkeypatch): Painter's curated Grindstone
        entry is present at centrality 1.0 regardless of derivation input."""
        result = linchpins_for_archetype("Painter", [], {})
        by_name = {lp.name: lp for lp in result}
        assert "Grindstone" in by_name
        assert by_name["Grindstone"].centrality == 1.0

    def test_derived_only_archetype_returns_near_mandatory_engine_pieces(self):
        """AC: an archetype with no curated entry still returns derived linchpins at
        _DERIVED_CENTRALITY."""
        tutor = _make_card(
            name="Totally Not Demonic Tutor",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put it into your hand, then shuffle.",
        )
        result = linchpins_for_archetype(
            "Some Brand New Archetype Nobody Has Curated",
            [(tutor, 1)],
            {"Totally Not Demonic Tutor": 0.95},
        )
        assert len(result) == 1
        assert result[0].role == "combo-tutor"
        assert result[0].centrality == _DERIVED_CENTRALITY

    def test_no_cards_and_no_curated_entry_returns_empty(self):
        assert linchpins_for_archetype("Nonexistent Archetype", [], {}) == []
