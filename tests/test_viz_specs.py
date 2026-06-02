"""Viz specs tests — prep models + Vega-Lite builder tests for the four chart surfaces.

Replaces the old test_charts.py (matplotlib-era) after the charts-migration feature.
House style: CliRunner + in-memory DuckDB; TestX classes; deterministic.

Covers:
- TestHeatmapModel — masking, p_shrunk, annotations, mirror, caveat (moved from test_charts.py).
- TestMetashareModel — speculative muted, fringe/Other flagged, subtitle (moved).
- TestTierModel — S/A/B bucket boundaries; confidence carried; Other/never-other excluded (moved).
- TestTrendModel — per-regime series with None gaps; thin_regimes mirrors regime flags (moved).
- TestSpecMetashare — schema + description + assert_renders; muted/fringe data in rows.
- TestSpecMatchupHeatmap — schema + description + assert_renders; masked/mirror/annotation rows.
- TestSpecTierList — schema + description + assert_renders; facet rows; empty model.
- TestSpecTrends — schema + description + assert_renders; thin-band layer; gap (None) omission.
"""

from __future__ import annotations

import json

import duckdb
import pytest
from click.testing import CliRunner

from legacy_engine.analytics.matchup import build_matrix
from legacy_engine.analytics.metashare import compute_metashare
from legacy_engine.analytics.trends import compute_trends
from legacy_engine.config import VL_SCHEMA_URL
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.ingestion.store import init_schema
from legacy_engine.viz.models import (
    HeatmapModel,
    BarModel,
    TierModel,
    TrendModel,
    _heatmap_model,
    _metashare_model,
    _tier_model,
    _trends_model,
)
from legacy_engine.viz.specs import (
    spec_matchup_heatmap,
    spec_metashare,
    spec_tier_list,
    spec_trends,
)
from tests.conftest import assert_renders

# ---------------------------------------------------------------------------
# Shared raw tournament fixtures
# ---------------------------------------------------------------------------

_ONLINE_T1 = {
    "Tournament": {
        "Name": "Legacy Challenge",
        "Date": "2026-05-24",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-2026-05-24",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "alice",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "bob",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [
        {"Rank": 1, "Player": "alice", "Points": 18},
        {"Rank": 2, "Player": "bob", "Points": 15},
    ],
}

# Regime A tournament (2024-09-01, after Grief ban)
_REGIME_A_T1 = {
    "Tournament": {
        "Name": "Legacy Challenge A1",
        "Date": "2024-09-01",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-a1-2024-09-01",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "p1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "p2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
        {
            "Player": "p3",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

# Regime C tournament (2026-05-25, after Undercity Informer ban)
_REGIME_C_T1 = {
    "Tournament": {
        "Name": "Legacy Challenge C1",
        "Date": "2026-05-25",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-c1-2026-05-25",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "s1",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "s2",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _con():
    """Return an in-memory DuckDB connection with the schema initialized."""
    con = store.connect(":memory:")
    init_schema(con)
    return con


def _load_and_label(con, raw_dict, source, labels: dict[str, str]):
    tid = store.load_tournament(con, parse_cache_item(raw_dict, source))
    for player, archetype in labels.items():
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            [archetype, tid, player],
        )
    return tid


def _build_large_matchup_corpus(con):
    """Build enough matchup data for at least one cell to have n≥30 (display=True)."""
    for i in range(31):
        raw = {
            "Tournament": {
                "Name": f"Mini Event {i}",
                "Date": f"2026-01-{(i % 28) + 1:02d}",
                "Uri": f"https://www.mtgo.com/decklist/mini-event-{i}",
                "Formats": "Legacy",
            },
            "Decks": [
                {
                    "Player": "delver_player",
                    "Result": "1st",
                    "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                    "Sideboard": [],
                },
                {
                    "Player": "lands_player",
                    "Result": "2nd",
                    "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
                    "Sideboard": [],
                },
            ],
            "Rounds": [{"Player1": "delver_player", "Player2": "lands_player", "Result": "2-1"}],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'delver_player'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'lands_player'",
            [tid],
        )


# ---------------------------------------------------------------------------
# TestHeatmapModel (moved from test_charts.py; re-pointed to viz.models)
# ---------------------------------------------------------------------------


class TestHeatmapModel:
    def test_low_n_cell_is_masked(self):
        """display=False (n<30) cells are masked: values[i][j] is None, masked[i][j] is True."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        if "Delver" in model.archetypes and "Lands" in model.archetypes:
            d_idx = model.archetypes.index("Delver")
            l_idx = model.archetypes.index("Lands")
            assert model.masked[d_idx][l_idx] is True
            assert model.values[d_idx][l_idx] is None
        con.close()

    def test_n_zero_cell_is_masked(self):
        """n==0 cells are masked regardless of display flag."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        for i, row in enumerate(model.values):
            for j, v in enumerate(row):
                if model.masked[i][j]:
                    assert v is None
        con.close()

    def test_displayed_cell_has_p_shrunk(self):
        """A displayed cell (n≥30) has values[i][j] == cell.p_shrunk."""
        con = _con()
        _build_large_matchup_corpus(con)
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        found_displayed = False
        for i in range(len(model.archetypes)):
            for j in range(len(model.archetypes)):
                if not model.masked[i][j] and not model.mirror[i][j]:
                    found_displayed = True
                    arch_a = model.archetypes[i]
                    arch_b = model.archetypes[j]
                    cell = matrix.cells.get((arch_a, arch_b))
                    assert cell is not None
                    assert cell.display is True
                    assert model.values[i][j] == pytest.approx(cell.p_shrunk)
        assert found_displayed, "Expected at least one displayed (n≥30) cell"
        con.close()

    def test_displayed_cell_annotation_contains_n(self):
        """A displayed cell's annotation contains its n count."""
        con = _con()
        _build_large_matchup_corpus(con)
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        for i in range(len(model.archetypes)):
            for j in range(len(model.archetypes)):
                if not model.masked[i][j] and not model.mirror[i][j]:
                    arch_a = model.archetypes[i]
                    arch_b = model.archetypes[j]
                    cell = matrix.cells.get((arch_a, arch_b))
                    assert cell is not None
                    assert f"n={cell.n}" in model.annotations[i][j]
        con.close()

    def test_mirror_cells_flagged(self):
        """Diagonal (a, a) cells have mirror[i][i] is True."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        for i in range(len(model.archetypes)):
            assert model.mirror[i][i] is True
        con.close()

    def test_caveat_carried_from_matrix(self):
        """model.caveat == matrix.caveat."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        assert model.caveat == matrix.caveat
        con.close()

    def test_empty_matrix_produces_empty_model(self):
        """An empty matrix (no archetypes) produces a HeatmapModel with empty lists."""
        con = _con()
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        assert model.archetypes == []
        assert model.values == []
        assert model.masked == []
        assert model.mirror == []
        assert model.annotations == []
        con.close()


# ---------------------------------------------------------------------------
# TestMetashareModel (moved from test_charts.py; re-pointed to viz.models)
# ---------------------------------------------------------------------------


class TestMetashareModel:
    def _build_speculative_corpus(self, con):
        """2-deck corpus: each archetype has n=1 → speculative tier."""
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})

    def test_speculative_tier_bar_is_muted(self):
        """An entry with tier='speculative' → muted[i] is True."""
        con = _con()
        self._build_speculative_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _metashare_model(report)
        for i, label in enumerate(model.labels):
            entry = next(e for e in report.entries if e.archetype == label)
            if entry.tier == "speculative":
                assert model.muted[i] is True
            else:
                assert model.muted[i] is False
        con.close()

    def test_other_bar_is_fringe(self):
        """An 'Other' entry → fringe[i] is True."""
        con = _con()
        decks = []
        for k in range(99):
            decks.append({
                "Player": f"d{k}",
                "Result": f"{k+1}th",
                "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                "Sideboard": [],
            })
        decks.append({
            "Player": "l1",
            "Result": "100th",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        })
        raw = {
            "Tournament": {
                "Name": "Other Test",
                "Date": "2026-05-24",
                "Uri": "https://www.mtgo.com/decklist/other-test-2026-05-24",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for k in range(99):
            con.execute(
                "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = ?",
                [tid, f"d{k}"],
            )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'l1'",
            [tid],
        )
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.02, group_other=True)
        model = _metashare_model(report)
        other_indices = [i for i, lbl in enumerate(model.labels) if lbl == "Other"]
        assert other_indices, "Expected 'Other' in model labels"
        for i in other_indices:
            assert model.fringe[i] is True
        con.close()

    def test_fringe_entry_is_fringe_flagged(self):
        """An entry with fringe=True → fringe[i] is True in model."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        decks = []
        for k in range(50):
            decks.append({
                "Player": f"d{k}",
                "Result": f"{k+1}th",
                "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                "Sideboard": [],
            })
        decks.append({
            "Player": "l1",
            "Result": "51st",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        })
        raw = {
            "Tournament": {
                "Name": "Fringe Model Test",
                "Date": "2026-05-26",
                "Uri": "https://www.mtgo.com/decklist/fringe-model-test-2026-05-26",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid2 = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for k in range(50):
            con.execute(
                "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = ?",
                [tid2, f"d{k}"],
            )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'l1'",
            [tid2],
        )
        report = compute_metashare(
            con, definition="raw", provenance=None, min_share=0.02, group_other=False
        )
        model = _metashare_model(report)
        for i, label in enumerate(model.labels):
            entry = next(e for e in report.entries if e.archetype == label)
            if entry.fringe:
                assert model.fringe[i] is True
        con.close()

    def test_subtitle_contains_definition_and_basis(self):
        """subtitle contains the definition and provenance basis."""
        con = _con()
        self._build_speculative_corpus(con)
        report = compute_metashare(con, definition="raw", provenance="online", min_share=0.0, group_other=False)
        model = _metashare_model(report)
        assert "RAW" in model.subtitle or "raw" in model.subtitle.upper()
        assert "online" in model.subtitle
        con.close()

    def test_subtitle_contains_total_decks(self):
        """subtitle contains total_decks."""
        con = _con()
        self._build_speculative_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _metashare_model(report)
        assert str(report.total_decks) in model.subtitle
        con.close()

    def test_empty_report_produces_empty_model_labels(self):
        """Empty report (no entries) → model.labels is empty list."""
        con = _con()
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        model = _metashare_model(report)
        assert model.labels == []
        assert model.shares == []
        assert model.muted == []
        assert model.fringe == []
        con.close()


# ---------------------------------------------------------------------------
# TestTierModel (moved from test_charts.py; re-pointed to viz.models)
# ---------------------------------------------------------------------------


class TestTierModel:
    def _build_tier_corpus(self, con):
        """Build a corpus with exact share counts: S-tier, A-tier, B-tier, sub-floor."""
        decks = []
        labels = {}
        idx = 0
        for _ in range(12):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []})
            labels[p] = "Reanimator"
        for _ in range(7):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []})
            labels[p] = "Delver"
        for _ in range(3):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}], "Sideboard": []})
            labels[p] = "Combo"
        for _ in range(1):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Ponder"}], "Sideboard": []})
            labels[p] = "Stompy"
        for _ in range(77):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []})
            labels[p] = "Control"
        raw = {
            "Tournament": {
                "Name": "Tier Test",
                "Date": "2026-05-24",
                "Uri": "https://www.mtgo.com/decklist/tier-test-2026-05-24",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for player, archetype in labels.items():
            con.execute(
                "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
                [archetype, tid, player],
            )

    def test_s_tier_boundary(self):
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        s_archs = [arch for arch, _share, _tier in model.buckets["S"]]
        assert "Reanimator" in s_archs
        con.close()

    def test_a_tier_boundary(self):
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        a_archs = [arch for arch, _share, _tier in model.buckets["A"]]
        assert "Delver" in a_archs
        con.close()

    def test_b_tier_boundary(self):
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        b_archs = [arch for arch, _share, _tier in model.buckets["B"]]
        assert "Combo" in b_archs
        con.close()

    def test_sub_floor_is_untiered(self):
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        all_tiered = (
            [arch for arch, _, _ in model.buckets["S"]]
            + [arch for arch, _, _ in model.buckets["A"]]
            + [arch for arch, _, _ in model.buckets["B"]]
        )
        assert "Stompy" not in all_tiered
        con.close()

    def test_confidence_tier_carried_in_bucket(self):
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        entry_tiers = {e.archetype: e.tier for e in report.entries}
        for tier_key in ("S", "A", "B"):
            for arch, _share, conf_tier in model.buckets[tier_key]:
                assert conf_tier == entry_tiers[arch]
        con.close()

    def test_other_excluded_from_tiers(self):
        """The 'Other' row is excluded from all tier buckets."""
        con = _con()
        decks = []
        labels = {}
        idx = 0
        for _ in range(90):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []})
            labels[p] = "Delver"
        for _ in range(10):
            p = f"p{idx}"; idx += 1
            decks.append({"Player": p, "Result": f"{idx}th",
                           "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []})
            labels[p] = "Smol"
        raw = {
            "Tournament": {
                "Name": "Other Excl Test",
                "Date": "2026-05-24",
                "Uri": "https://www.mtgo.com/decklist/other-excl-test-2026-05-24",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for player, archetype in labels.items():
            con.execute(
                "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
                [archetype, tid, player],
            )
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.5, group_other=True)
        model = _tier_model(report)
        all_tiered = (
            [arch for arch, _, _ in model.buckets["S"]]
            + [arch for arch, _, _ in model.buckets["A"]]
            + [arch for arch, _, _ in model.buckets["B"]]
        )
        assert "Other" not in all_tiered
        con.close()

    def test_never_other_excluded(self):
        """Unknown / Conflict labels are excluded from tier buckets."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Unknown", "bob": "Lands"})
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        all_tiered = (
            [arch for arch, _, _ in model.buckets["S"]]
            + [arch for arch, _, _ in model.buckets["A"]]
            + [arch for arch, _, _ in model.buckets["B"]]
        )
        assert "Unknown" not in all_tiered
        con.close()


# ---------------------------------------------------------------------------
# TestTrendModel (moved from test_charts.py; re-pointed to viz.models)
# ---------------------------------------------------------------------------


class TestTrendModel:
    def _build_multi_regime_corpus(self, con):
        """Load events in two regimes: A (2024-09-01) and C (2026-05-25)."""
        _load_and_label(
            con, _REGIME_A_T1, "MTGO",
            {"p1": "Delver", "p2": "Lands", "p3": "Reanimator"},
        )
        _load_and_label(
            con, _REGIME_C_T1, "MTGO",
            {"s1": "Delver", "s2": "Lands"},
        )

    def test_series_per_regime_with_none_gaps(self):
        """series[arch] has one entry per regime; None where archetype is absent."""
        con = _con()
        self._build_multi_regime_corpus(con)
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        model = _trends_model(trend_series)

        for archetype in model.archetypes:
            arch_series = model.series[archetype]
            assert len(arch_series) == len(model.regime_labels)
            for val in arch_series:
                assert val is None or isinstance(val, float)
        con.close()

    def test_thin_regimes_mirrors_regime_flags(self):
        """thin_regimes[k] == series.regimes[k].thin for each k."""
        con = _con()
        self._build_multi_regime_corpus(con)
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        model = _trends_model(trend_series)

        assert len(model.thin_regimes) == len(trend_series.regimes)
        for k, regime in enumerate(trend_series.regimes):
            assert model.thin_regimes[k] == regime.thin
        con.close()

    def test_regime_labels_match_series_regimes(self):
        """regime_labels matches [r.label for r in series.regimes]."""
        con = _con()
        self._build_multi_regime_corpus(con)
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        model = _trends_model(trend_series)

        expected = [r.label for r in trend_series.regimes]
        assert model.regime_labels == expected
        con.close()

    def test_present_archetype_has_non_none_share(self):
        """An archetype present in a regime has a non-None float in that regime's series slot."""
        con = _con()
        self._build_multi_regime_corpus(con)
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        model = _trends_model(trend_series)

        for k, regime in enumerate(trend_series.regimes):
            for archetype in model.archetypes:
                cell = trend_series.cells.get((regime.label, archetype))
                expected_val = cell.share if cell is not None else None
                actual_val = model.series[archetype][k]
                if expected_val is None:
                    assert actual_val is None
                else:
                    assert actual_val == pytest.approx(expected_val)
        con.close()

    def test_empty_series_produces_empty_model(self):
        """An empty TrendSeries produces a TrendModel with no regimes or archetypes."""
        con = _con()
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        model = _trends_model(trend_series)
        assert model.regime_labels == []
        assert model.archetypes == []
        assert model.series == {}
        assert model.thin_regimes == []
        con.close()


# ---------------------------------------------------------------------------
# Builder fixtures — minimal representative models for spec tests
# ---------------------------------------------------------------------------


def _make_bar_model() -> BarModel:
    """Representative BarModel with one muted + one fringe entry."""
    from legacy_engine.confidence import ConfidenceLevel
    return BarModel(
        labels=["Delver", "Lands", "Other"],
        shares=[0.40, 0.25, 0.05],
        muted=[True, False, False],
        fringe=[False, False, True],
        tiers=["speculative", "evolving", "evolving"],
        subtitle="definition=RAW  basis=all  total_decks=100",
        title="Meta Share [RAW]  basis=all",
    )


def _make_heatmap_model() -> HeatmapModel:
    """Representative HeatmapModel with 2 archetypes, 1 display cell, all others masked."""
    return HeatmapModel(
        archetypes=["Delver", "Lands"],
        values=[
            [None, 0.65],
            [0.35, None],
        ],
        masked=[
            [True, False],
            [False, True],
        ],
        mirror=[
            [True, False],
            [False, True],
        ],
        annotations=[
            ["mirror", "65%\n(n=31)"],
            ["35%\n(n=31)", "mirror"],
        ],
        caveat="n=31 decisive matches; shrunk win rates",
        title="Matchup Matrix  [basis=all]",
    )


def _make_tier_model() -> TierModel:
    """Representative TierModel with one entry per bucket."""
    return TierModel(
        buckets={
            "S": [("Control", 0.30, "established")],
            "A": [("Delver", 0.07, "evolving")],
            "B": [("Combo", 0.03, "speculative")],
        },
        subtitle="definition=RAW  basis=all  total_decks=100  S≥10% A≥5% B≥2%",
        title="Tier List [RAW]  basis=all",
    )


def _make_trend_model() -> TrendModel:
    """Representative TrendModel: 2 archetypes × 3 regimes, 1 gap, 1 thin regime."""
    return TrendModel(
        regime_labels=["Grief era", "Post-Grief", "Post-Undercity"],
        archetypes=["Delver", "Reanimator"],
        series={
            "Delver": [0.25, 0.30, None],        # absent from regime 3 → gap
            "Reanimator": [None, 0.15, 0.20],    # absent from regime 1 → gap
        },
        thin_regimes=[False, True, False],
        subtitle="definition=RAW  basis=all",
        title="Meta Trends [RAW]  basis=all",
    )


# ---------------------------------------------------------------------------
# TestSpecMetashare — spec_metashare builder
# ---------------------------------------------------------------------------


class TestSpecMetashare:
    def test_schema_present(self):
        """spec_metashare returns a dict with $schema == VL_SCHEMA_URL."""
        spec = spec_metashare(_make_bar_model())
        assert spec["$schema"] == VL_SCHEMA_URL

    def test_description_non_empty(self):
        """spec_metashare sets a non-empty description."""
        spec = spec_metashare(_make_bar_model())
        assert isinstance(spec.get("description"), str)
        assert len(spec["description"]) > 0

    def test_no_config_key(self):
        """spec_metashare does NOT set config (theme is injected at render time)."""
        spec = spec_metashare(_make_bar_model())
        assert "config" not in spec

    def test_data_values_contains_all_rows(self):
        """spec data.values has one row per label."""
        model = _make_bar_model()
        spec = spec_metashare(model)
        rows = spec["data"]["values"]
        assert len(rows) == len(model.labels)

    def test_muted_flag_present_in_rows(self):
        """Rows include the muted field so opacity conditions can fire."""
        spec = spec_metashare(_make_bar_model())
        rows = spec["data"]["values"]
        muted_row = next(r for r in rows if r["archetype"] == "Delver")
        assert muted_row["muted"] is True

    def test_fringe_flag_present_in_rows(self):
        """Rows include the fringe field so color conditions can fire."""
        spec = spec_metashare(_make_bar_model())
        rows = spec["data"]["values"]
        fringe_row = next(r for r in rows if r["archetype"] == "Other")
        assert fringe_row["fringe"] is True

    def test_assert_renders(self):
        """spec_metashare passes the real Vega-Lite compiler (assert_renders)."""
        assert_renders(spec_metashare(_make_bar_model()))

    def test_json_snapshot(self):
        """spec_metashare produces a stable JSON snapshot for the representative model."""
        spec = spec_metashare(_make_bar_model())
        # Round-trip through JSON to catch any non-serialisable values
        serialised = json.loads(json.dumps(spec))
        assert serialised["$schema"] == VL_SCHEMA_URL
        assert serialised["encoding"]["y"]["field"] == "archetype"
        assert serialised["encoding"]["x"]["field"] == "share"


# ---------------------------------------------------------------------------
# TestSpecMatchupHeatmap — spec_matchup_heatmap builder
# ---------------------------------------------------------------------------


class TestSpecMatchupHeatmap:
    def test_schema_present(self):
        spec = spec_matchup_heatmap(_make_heatmap_model())
        assert spec["$schema"] == VL_SCHEMA_URL

    def test_description_non_empty(self):
        spec = spec_matchup_heatmap(_make_heatmap_model())
        assert isinstance(spec.get("description"), str)
        assert len(spec["description"]) > 0

    def test_no_config_key(self):
        spec = spec_matchup_heatmap(_make_heatmap_model())
        assert "config" not in spec

    def test_has_two_layers(self):
        """Heatmap has a rect layer and a text layer."""
        spec = spec_matchup_heatmap(_make_heatmap_model())
        assert "layer" in spec
        assert len(spec["layer"]) == 2
        marks = [layer["mark"] for layer in spec["layer"]]
        assert "rect" in marks
        assert any(m == "text" or (isinstance(m, dict) and m.get("type") == "text") for m in marks)

    def test_data_values_has_n_squared_rows(self):
        """A 2×2 heatmap has 4 rows in data.values."""
        model = _make_heatmap_model()
        spec = spec_matchup_heatmap(model)
        n = len(model.archetypes)
        rows = spec["data"]["values"]
        assert len(rows) == n * n

    def test_masked_cells_present_in_data(self):
        """Masked cells appear in data.values with p_shrunk == None."""
        spec = spec_matchup_heatmap(_make_heatmap_model())
        rows = spec["data"]["values"]
        masked_rows = [r for r in rows if r["masked"]]
        assert len(masked_rows) > 0
        for r in masked_rows:
            assert r["p_shrunk"] is None

    def test_mirror_cells_annotated(self):
        """Mirror cells carry annotation == 'mirror'."""
        spec = spec_matchup_heatmap(_make_heatmap_model())
        rows = spec["data"]["values"]
        mirror_rows = [r for r in rows if r["mirror"]]
        assert len(mirror_rows) > 0
        for r in mirror_rows:
            assert r["annotation"] == "mirror"

    def test_assert_renders(self):
        """spec_matchup_heatmap passes the real Vega-Lite compiler."""
        assert_renders(spec_matchup_heatmap(_make_heatmap_model()))

    def test_json_snapshot(self):
        spec = spec_matchup_heatmap(_make_heatmap_model())
        serialised = json.loads(json.dumps(spec))
        assert serialised["$schema"] == VL_SCHEMA_URL
        # Rect layer encodes x as archetype_b, y as archetype_a
        rect_layer = next(l for l in serialised["layer"] if l["mark"] == "rect")
        assert rect_layer["encoding"]["x"]["field"] == "archetype_b"
        assert rect_layer["encoding"]["y"]["field"] == "archetype_a"
        # Color scale scheme
        assert rect_layer["encoding"]["color"]["field"] == "p_shrunk"
        assert rect_layer["encoding"]["color"]["scale"]["scheme"] == "redyellowgreen"


# ---------------------------------------------------------------------------
# TestSpecTierList — spec_tier_list builder
# ---------------------------------------------------------------------------


class TestSpecTierList:
    def test_schema_present(self):
        spec = spec_tier_list(_make_tier_model())
        assert spec["$schema"] == VL_SCHEMA_URL

    def test_description_non_empty(self):
        spec = spec_tier_list(_make_tier_model())
        assert isinstance(spec.get("description"), str)
        assert len(spec["description"]) > 0

    def test_no_config_key(self):
        spec = spec_tier_list(_make_tier_model())
        assert "config" not in spec

    def test_data_values_has_one_row_per_archetype(self):
        """data.values has one row per tiered archetype (3 = 1 S + 1 A + 1 B)."""
        model = _make_tier_model()
        spec = spec_tier_list(model)
        rows = spec["data"]["values"]
        total_archs = sum(len(v) for v in model.buckets.values())
        assert len(rows) == total_archs

    def test_facet_by_bucket(self):
        """Spec uses facet with row field == 'bucket'."""
        spec = spec_tier_list(_make_tier_model())
        assert "facet" in spec
        assert spec["facet"]["row"]["field"] == "bucket"

    def test_bucket_order_is_s_a_b(self):
        """Facet row sort order is ['S', 'A', 'B']."""
        spec = spec_tier_list(_make_tier_model())
        assert spec["facet"]["row"]["sort"] == ["S", "A", "B"]

    def test_empty_tier_model_renders(self):
        """An empty TierModel (no buckets) still produces a valid renderable spec."""
        empty_model = TierModel(
            buckets={"S": [], "A": [], "B": []},
            subtitle="definition=RAW  basis=all  total_decks=0  S≥10% A≥5% B≥2%",
            title="Tier List [RAW]  basis=all",
        )
        spec = spec_tier_list(empty_model)
        assert spec["$schema"] == VL_SCHEMA_URL
        assert_renders(spec)

    def test_assert_renders(self):
        """spec_tier_list passes the real Vega-Lite compiler."""
        assert_renders(spec_tier_list(_make_tier_model()))

    def test_json_snapshot(self):
        spec = spec_tier_list(_make_tier_model())
        serialised = json.loads(json.dumps(spec))
        assert serialised["$schema"] == VL_SCHEMA_URL
        assert serialised["facet"]["row"]["field"] == "bucket"
        # Inner spec encodes x=share, y=archetype
        inner = serialised["spec"]["encoding"]
        assert inner["x"]["field"] == "share"
        assert inner["y"]["field"] == "archetype"


# ---------------------------------------------------------------------------
# TestSpecTrends — spec_trends builder
# ---------------------------------------------------------------------------


class TestSpecTrends:
    def test_schema_present(self):
        spec = spec_trends(_make_trend_model())
        assert spec["$schema"] == VL_SCHEMA_URL

    def test_description_non_empty(self):
        spec = spec_trends(_make_trend_model())
        assert isinstance(spec.get("description"), str)
        assert len(spec["description"]) > 0

    def test_no_config_key(self):
        spec = spec_trends(_make_trend_model())
        assert "config" not in spec

    def test_none_cells_omitted_from_line_layer(self):
        """None (absent) cells are not emitted in the line layer data; line breaks via gap."""
        model = _make_trend_model()
        spec = spec_trends(model)
        # Line layer is the last layer
        line_layer = spec["layer"][-1]
        rows = line_layer["data"]["values"]
        # Delver absent from regime 3 → only 2 rows for Delver
        delver_rows = [r for r in rows if r["archetype"] == "Delver"]
        assert len(delver_rows) == 2
        # Reanimator absent from regime 1 → only 2 rows for Reanimator
        reanimator_rows = [r for r in rows if r["archetype"] == "Reanimator"]
        assert len(reanimator_rows) == 2
        # No row with share == 0 from a gap
        for r in rows:
            if r["archetype"] in ("Delver", "Reanimator"):
                assert r["share"] is not None
                assert r["share"] > 0

    def test_thin_regime_band_layer_present(self):
        """When thin_regimes has True entries, a rect band layer is present."""
        model = _make_trend_model()  # thin_regimes=[False, True, False]
        spec = spec_trends(model)
        assert "layer" in spec
        # Should have 2 layers: band + line
        assert len(spec["layer"]) == 2
        band_layer = spec["layer"][0]
        assert band_layer["mark"]["type"] == "rect"
        # Band data has one row for the one thin regime
        assert len(band_layer["data"]["values"]) == 1
        assert band_layer["data"]["values"][0]["regime"] == "Post-Grief"

    def test_no_thin_band_when_no_thin_regimes(self):
        """When thin_regimes are all False, no band layer is emitted."""
        model = TrendModel(
            regime_labels=["Era A", "Era B"],
            archetypes=["Delver"],
            series={"Delver": [0.20, 0.25]},
            thin_regimes=[False, False],
            subtitle="definition=RAW  basis=all",
            title="Meta Trends [RAW]  basis=all",
        )
        spec = spec_trends(model)
        # Only the line layer should be present
        assert len(spec["layer"]) == 1
        assert spec["layer"][0]["mark"]["type"] == "line"

    def test_regime_order_preserved(self):
        """The regime sort order in x encoding matches model.regime_labels."""
        model = _make_trend_model()
        spec = spec_trends(model)
        line_layer = spec["layer"][-1]
        x_sort = line_layer["encoding"]["x"]["sort"]
        assert x_sort == model.regime_labels

    def test_assert_renders(self):
        """spec_trends passes the real Vega-Lite compiler."""
        assert_renders(spec_trends(_make_trend_model()))

    def test_json_snapshot(self):
        spec = spec_trends(_make_trend_model())
        serialised = json.loads(json.dumps(spec))
        assert serialised["$schema"] == VL_SCHEMA_URL
        line_layer = serialised["layer"][-1]
        assert line_layer["encoding"]["x"]["field"] == "regime"
        assert line_layer["encoding"]["x"]["type"] == "ordinal"
        assert line_layer["encoding"]["y"]["field"] == "share"
        assert line_layer["encoding"]["color"]["field"] == "archetype"

    def test_empty_trends_model_renders(self):
        """An empty TrendModel (no archetypes, no regimes) still produces a valid spec."""
        empty = TrendModel(
            regime_labels=[],
            archetypes=[],
            series={},
            thin_regimes=[],
            subtitle="definition=RAW  basis=all",
            title="Meta Trends [RAW]  basis=all",
        )
        spec = spec_trends(empty)
        assert spec["$schema"] == VL_SCHEMA_URL
        assert_renders(spec)
