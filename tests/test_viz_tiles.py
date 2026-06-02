"""Tests for the per-deck chart builders: spec_matchup_row and spec_positioning.

Covers:
- TestSpecMatchupRow  — schema, description, assert_renders, masking, 0.5 ref, CI rule
- TestSpecPositioning — schema, description, assert_renders, subject highlight, low_coverage opacity
"""

from __future__ import annotations

import json

import pytest

from legacy_engine.advisory.positioning import DeckRanking
from legacy_engine.config import VL_SCHEMA_URL
from legacy_engine.viz.specs import spec_matchup_row, spec_positioning
from tests.conftest import assert_renders


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_matchup_rows():
    """Minimal matchup rows covering: displayed, masked, reference 0.5 line."""
    return [
        {
            "opponent": "Control",
            "p_shrunk": 0.62,
            "ci_low": 0.55,
            "ci_high": 0.70,
            "n": 45,
            "tier": "established",
            "display": True,
            "window": "2025-06-01",
        },
        {
            "opponent": "Combo",
            "p_shrunk": 0.38,
            "ci_low": 0.31,
            "ci_high": 0.46,
            "n": 40,
            "tier": "established",
            "display": True,
            "window": "2025-09-01",
        },
        {
            "opponent": "Aggro",
            "p_shrunk": None,
            "ci_low": None,
            "ci_high": None,
            "n": 10,
            "tier": "speculative",
            "display": False,
            "window": None,
        },
    ]


@pytest.fixture
def sample_ranking():
    """Minimal DeckRanking with 3 candidates including a subject and a low-coverage deck."""
    decks = ["Control", "Combo", "Aggro"]
    return DeckRanking(
        decks=decks,
        p_best={"Control": 0.6, "Combo": 0.3, "Aggro": 0.1},
        s_mean={"Control": 0.535, "Combo": 0.490, "Aggro": 0.460},
        s_ci={
            "Control": (0.510, 0.560),
            "Combo": (0.460, 0.520),
            "Aggro": (0.410, 0.510),
        },
        s_quantile={"Control": 0.510, "Combo": 0.460, "Aggro": 0.410},
        quantile_level=0.05,
        data_coverage={"Control": 0.9, "Combo": 0.8, "Aggro": 0.15},
        low_coverage={"Aggro"},
        pairwise={
            ("Control", "Combo"): 0.72,
            ("Control", "Aggro"): 0.80,
            ("Combo", "Control"): 0.28,
            ("Combo", "Aggro"): 0.60,
            ("Aggro", "Control"): 0.20,
            ("Aggro", "Combo"): 0.40,
        },
        field_source="global",
    )


# ---------------------------------------------------------------------------
# TestSpecMatchupRow
# ---------------------------------------------------------------------------

class TestSpecMatchupRow:
    def test_schema_present(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        assert spec.get("$schema") == VL_SCHEMA_URL

    def test_description_non_empty(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        assert spec.get("description"), "description must be non-empty"
        assert "Tempo" in spec["description"]

    def test_no_config_key(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        assert "config" not in spec, "builders must NOT set config (injected at render time)"

    def test_assert_renders(self, sample_matchup_rows):
        """Real vl_convert compile round-trip — must produce valid PNG bytes."""
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        assert_renders(spec)

    def test_has_three_layers(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        assert "layer" in spec
        assert len(spec["layer"]) == 3, "should have bar + CI + ref layers"

    def test_reference_rule_at_0_5(self, sample_matchup_rows):
        """Third layer should be the 0.5 reference rule with its data value."""
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        ref_layer = spec["layer"][2]
        data_values = ref_layer.get("data", {}).get("values", [])
        assert len(data_values) == 1
        assert data_values[0].get("ref") == pytest.approx(0.5)

    def test_masked_row_has_display_false_in_data(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        bar_layer = spec["layer"][0]
        data_values = bar_layer.get("data") or spec.get("data", {}).get("values", [])
        # top-level data
        if "data" in spec:
            rows = spec["data"]["values"]
        else:
            rows = bar_layer["data"]["values"]
        masked_rows = [r for r in rows if r["opponent"] == "Aggro"]
        assert len(masked_rows) == 1
        assert not masked_rows[0]["display"]
        assert masked_rows[0]["p_shrunk"] is None

    def test_displayed_rows_have_p_shrunk(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        rows = spec["data"]["values"]
        displayed = [r for r in rows if r["display"]]
        assert len(displayed) == 2
        for r in displayed:
            assert r["p_shrunk"] is not None

    def test_json_serializable(self, sample_matchup_rows):
        spec = spec_matchup_row(sample_matchup_rows, deck="Tempo")
        # must be JSON-serializable (no non-JSON types)
        dumped = json.dumps(spec)
        assert len(dumped) > 0


# ---------------------------------------------------------------------------
# TestSpecPositioning
# ---------------------------------------------------------------------------

class TestSpecPositioning:
    def test_schema_present(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control")
        assert spec.get("$schema") == VL_SCHEMA_URL

    def test_description_non_empty(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control")
        assert spec.get("description"), "description must be non-empty"
        assert "Control" in spec["description"]

    def test_no_config_key(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control")
        assert "config" not in spec

    def test_assert_renders(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control")
        assert_renders(spec)

    def test_subject_highlighted_in_color_condition(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Combo")
        bar_layer = spec["layer"][0]
        color_enc = bar_layer["encoding"]["color"]
        condition = color_enc["condition"]
        # The condition test must use the boolean field idiom, not raw string interpolation
        assert condition["test"] == "datum.is_subject"
        assert condition["value"] == "#D55E00"

    def test_subject_is_subject_field_in_data(self, sample_ranking):
        """The subject deck must have is_subject=True in emitted data (boolean-field idiom)."""
        spec = spec_positioning(sample_ranking, subject="Combo")
        rows = spec["data"]["values"]
        combo_rows = [r for r in rows if r["deck"] == "Combo"]
        assert len(combo_rows) == 1
        assert combo_rows[0]["is_subject"] is True
        # Non-subject decks must have is_subject=False
        non_subj = [r for r in rows if r["deck"] != "Combo"]
        for r in non_subj:
            assert r["is_subject"] is False

    def test_low_coverage_deck_has_opacity_in_data(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control")
        rows = spec["data"]["values"]
        aggro_rows = [r for r in rows if r["deck"] == "Aggro"]
        assert len(aggro_rows) == 1
        assert aggro_rows[0]["low_coverage"] is True

    def test_has_ci_layer(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control")
        # bar layer + CI layer (at minimum 2 layers)
        assert "layer" in spec
        assert len(spec["layer"]) >= 2

    def test_u_bar_overlay_when_provided(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control", u_bar=0.52)
        assert len(spec["layer"]) == 3, "should have bar + CI + u_bar layers"
        u_layer = spec["layer"][2]
        data_values = u_layer.get("data", {}).get("values", [])
        assert len(data_values) == 1
        assert data_values[0].get("u_bar") == pytest.approx(0.52)

    def test_no_u_bar_overlay_when_none(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control", u_bar=None)
        assert len(spec["layer"]) == 2, "should only have bar + CI layers"

    def test_json_serializable(self, sample_ranking):
        spec = spec_positioning(sample_ranking, subject="Control", u_bar=0.53)
        dumped = json.dumps(spec)
        assert len(dumped) > 0

    def test_apostrophe_subject_renders_and_is_highlighted(self):
        """B1 regression: archetype names with apostrophes must not produce invalid Vega expressions.

        Uses the boolean is_subject field idiom instead of raw string interpolation
        so names like "Dimir Death's Shadow" or "Mind's Desire" compile without error.
        """
        apos_subject = "Dimir Death's Shadow"
        decks = [apos_subject, "Control", "Combo"]
        ranking = DeckRanking(
            decks=decks,
            p_best={apos_subject: 0.5, "Control": 0.3, "Combo": 0.2},
            s_mean={apos_subject: 0.540, "Control": 0.510, "Combo": 0.480},
            s_ci={
                apos_subject: (0.510, 0.570),
                "Control": (0.490, 0.530),
                "Combo": (0.450, 0.510),
            },
            s_quantile={apos_subject: 0.510, "Control": 0.490, "Combo": 0.450},
            quantile_level=0.05,
            data_coverage={apos_subject: 0.85, "Control": 0.90, "Combo": 0.80},
            low_coverage=set(),
            pairwise={
                (apos_subject, "Control"): 0.60,
                (apos_subject, "Combo"): 0.55,
                ("Control", apos_subject): 0.40,
                ("Control", "Combo"): 0.52,
                ("Combo", apos_subject): 0.45,
                ("Combo", "Control"): 0.48,
            },
            field_source="global",
        )
        spec = spec_positioning(ranking, subject=apos_subject)

        # No apostrophe must appear in any Vega expression string
        import json as _json
        spec_str = _json.dumps(spec)
        # The subject name appears in data values (safe), but NOT in a condition test string
        bar_layer = spec["layer"][0]
        condition_test = bar_layer["encoding"]["color"]["condition"]["test"]
        assert "'" not in condition_test, (
            f"apostrophe found in condition test expression: {condition_test!r}"
        )
        assert condition_test == "datum.is_subject"

        # Real Vega compiler must accept the spec (would raise ValueError on invalid expression)
        assert_renders(spec)

        # The subject row must have is_subject=True in the emitted data
        rows = spec["data"]["values"]
        subj_rows = [r for r in rows if r["deck"] == apos_subject]
        assert len(subj_rows) == 1
        assert subj_rows[0]["is_subject"] is True
