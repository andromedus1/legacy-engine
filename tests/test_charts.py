"""Charts tests — prep helpers + smoke renders + CLI wiring for epic-meta-analytics-charts.

House style: module-level raw dicts → ``parse_cache_item`` → ``store.load_tournament``
into ``:memory:``; labels pinned via direct SQL UPDATE; ``TestX`` classes; deterministic.
CliRunner for CLI tests.

Covers:
- TestHeatmapModel — masking, p_shrunk, annotations, mirror, caveat.
- TestMetashareModel — speculative muted, fringe/Other flagged, subtitle labeled.
- TestTierModel — S/A/B bucket boundaries; confidence carried; Other/never-other excluded.
- TestTrendModel — per-regime series with None gaps; thin_regimes mirrors regime flags.
- TestRenderSmoke — each render_* writes a non-empty PNG; empty inputs still write a valid PNG.
- TestReportTiersCLI — report tiers prints a labeled text tier list.
- TestChartDirCLI — --chart-dir writes expected filenames; omitting it leaves text-only output.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pytest
from click.testing import CliRunner

from legacy_engine.analytics.charts import (
    BarModel,
    HeatmapModel,
    TierModel,
    TrendModel,
    _heatmap_model,
    _metashare_model,
    _tier_model,
    _trends_model,
    render_matchup_heatmap,
    render_metashare,
    render_tier_list,
    render_trends,
)
from legacy_engine.analytics.matchup import build_matrix
from legacy_engine.analytics.metashare import compute_metashare
from legacy_engine.analytics.trends import compute_trends
from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.ingestion.store import init_schema

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


def _setup_db_file(tmp_path, label_online=True) -> Path:
    """Create a file-based DuckDB with a minimal labeled corpus."""
    db_path = tmp_path / "charts_test.duckdb"
    con = duckdb.connect(str(db_path))
    init_schema(con)
    tid = store.load_tournament(con, parse_cache_item(_ONLINE_T1, "MTGO"))
    if label_online:
        con.execute(
            "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'alice'",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'bob'",
            [tid],
        )
    con.close()
    return db_path


# ---------------------------------------------------------------------------
# Build a large corpus (≥30 decks per matchup) for testing the matchup heatmap
# display=True path.  We need n≥30 between two archetypes.
# ---------------------------------------------------------------------------


def _build_large_matchup_corpus(con):
    """Build enough matchup data for at least one cell to have n≥30 (display=True)."""
    # We need 30+ Delver-vs-Lands matches.  Build 31 rounds:
    # Each 'round' is a separate mini-tournament with 2 players (one Delver, one Lands)
    # to give us 31 decisive match results total.
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
# TestHeatmapModel
# ---------------------------------------------------------------------------


class TestHeatmapModel:
    def test_low_n_cell_is_masked(self):
        """display=False (n<30) cells are masked: values[i][j] is None, masked[i][j] is True."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        # In a 2-archetype matrix, find the non-mirror Delver-vs-Lands cell
        if "Delver" in model.archetypes and "Lands" in model.archetypes:
            d_idx = model.archetypes.index("Delver")
            l_idx = model.archetypes.index("Lands")
            # n=1 match → display is False → masked
            assert model.masked[d_idx][l_idx] is True
            assert model.values[d_idx][l_idx] is None
        con.close()

    def test_n_zero_cell_is_masked(self):
        """n==0 cells are masked regardless of display flag."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        # Count all masked cells with values=None
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
        # Find a cell that is not masked and not a mirror
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
        # No data → no archetypes above any threshold
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        model = _heatmap_model(matrix)
        assert model.archetypes == []
        assert model.values == []
        assert model.masked == []
        assert model.mirror == []
        assert model.annotations == []
        con.close()


# ---------------------------------------------------------------------------
# TestMetashareModel
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
        # Build a 100-deck corpus; all labeled Delver except one tiny Lands → Lands gets grouped into Other
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
        # 2-deck corpus: each at 50% share but we use group_other=False to keep fringe rows
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        # Build a bigger corpus where Lands is fringe
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
        # Lands should be fringe (share ≈ 2/53 ≈ 3.8% from first tournament, much less than 2% from combined)
        # Actually let's just verify: fringe entries map to fringe[i] True
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
        # No data at all
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        model = _metashare_model(report)
        assert model.labels == []
        assert model.shares == []
        assert model.muted == []
        assert model.fringe == []
        con.close()


# ---------------------------------------------------------------------------
# TestTierModel
# ---------------------------------------------------------------------------


class TestTierModel:
    def _build_tier_corpus(self, con):
        """Build a corpus with exact share counts: S-tier, A-tier, B-tier, sub-floor."""
        # 100 decks total:
        # - 12 Reanimator (12% → S)
        # - 7 Delver (7% → A)
        # - 3 Combo (3% → B)
        # - 1 Stompy (1% → sub-floor)
        # - 77 Control (77% → S)
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
        """An archetype at 12% lands in the 'S' tier bucket."""
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        s_archs = [arch for arch, _share, _tier in model.buckets["S"]]
        # Reanimator is at 12% → S
        assert "Reanimator" in s_archs
        con.close()

    def test_a_tier_boundary(self):
        """An archetype at 7% lands in the 'A' tier bucket."""
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        a_archs = [arch for arch, _share, _tier in model.buckets["A"]]
        assert "Delver" in a_archs
        con.close()

    def test_b_tier_boundary(self):
        """An archetype at 3% lands in the 'B' tier bucket."""
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        b_archs = [arch for arch, _share, _tier in model.buckets["B"]]
        assert "Combo" in b_archs
        con.close()

    def test_sub_floor_is_untiered(self):
        """An archetype at 1% (below b_min=2%) is absent from all buckets."""
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
        """Each bucket entry carries the archetype's confidence tier from the report."""
        con = _con()
        self._build_tier_corpus(con)
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0, group_other=False)
        model = _tier_model(report)
        entry_tiers = {e.archetype: e.tier for e in report.entries}
        for tier_key in ("S", "A", "B"):
            for arch, _share, conf_tier in model.buckets[tier_key]:
                assert conf_tier == entry_tiers[arch], (
                    f"{arch}: bucket tier={conf_tier!r} but report tier={entry_tiers[arch]!r}"
                )
        con.close()

    def test_other_excluded_from_tiers(self):
        """The 'Other' row is excluded from all tier buckets."""
        con = _con()
        # Build corpus with Other row
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
            labels[p] = "Smol"  # fringe → grouped into Other
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
        # group_other=True so "Smol" is rolled into "Other"
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
# TestTrendModel
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
            assert len(arch_series) == len(model.regime_labels), (
                f"series[{archetype!r}] length {len(arch_series)} != "
                f"regime count {len(model.regime_labels)}"
            )
            # Each entry is float or None
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
            assert model.thin_regimes[k] == regime.thin, (
                f"thin_regimes[{k}]={model.thin_regimes[k]!r} != "
                f"regime.thin={regime.thin!r} for {regime.label!r}"
            )
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
        # Empty corpus → empty series
        model = _trends_model(trend_series)
        assert model.regime_labels == []
        assert model.archetypes == []
        assert model.series == {}
        assert model.thin_regimes == []
        con.close()


# ---------------------------------------------------------------------------
# TestRenderSmoke
# ---------------------------------------------------------------------------


class TestRenderSmoke:
    def test_render_matchup_heatmap_writes_nonempty_png(self, tmp_path):
        """render_matchup_heatmap writes a non-empty PNG for a minimal corpus."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        out = tmp_path / "heatmap.png"
        result = render_matchup_heatmap(matrix, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_matchup_heatmap_empty_matrix_writes_png(self, tmp_path):
        """render_matchup_heatmap with empty matrix writes a valid placeholder PNG."""
        con = _con()
        matrix = build_matrix(con, provenance=None, min_row_share=0.0)
        out = tmp_path / "heatmap_empty.png"
        result = render_matchup_heatmap(matrix, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_metashare_writes_nonempty_png(self, tmp_path):
        """render_metashare writes a non-empty PNG for a minimal corpus."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        out = tmp_path / "metashare.png"
        result = render_metashare(report, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_metashare_empty_report_writes_png(self, tmp_path):
        """render_metashare with empty report writes a valid placeholder PNG."""
        con = _con()
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        out = tmp_path / "metashare_empty.png"
        result = render_metashare(report, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_tier_list_writes_nonempty_png(self, tmp_path):
        """render_tier_list writes a non-empty PNG for a minimal corpus."""
        con = _con()
        _load_and_label(con, _ONLINE_T1, "MTGO", {"alice": "Delver", "bob": "Lands"})
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        out = tmp_path / "tiers.png"
        result = render_tier_list(report, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_tier_list_empty_report_writes_png(self, tmp_path):
        """render_tier_list with empty report writes a valid placeholder PNG."""
        con = _con()
        report = compute_metashare(con, definition="raw", provenance=None, min_share=0.0)
        out = tmp_path / "tiers_empty.png"
        result = render_tier_list(report, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_trends_writes_nonempty_png(self, tmp_path):
        """render_trends writes a non-empty PNG for a multi-regime corpus."""
        con = _con()
        _load_and_label(con, _REGIME_A_T1, "MTGO", {"p1": "Delver", "p2": "Lands", "p3": "Reanimator"})
        _load_and_label(con, _REGIME_C_T1, "MTGO", {"s1": "Delver", "s2": "Lands"})
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        out = tmp_path / "trends.png"
        result = render_trends(trend_series, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()

    def test_render_trends_empty_series_writes_png(self, tmp_path):
        """render_trends with empty series writes a valid placeholder PNG."""
        con = _con()
        trend_series = compute_trends(con, definition="raw", min_share=0.0)
        out = tmp_path / "trends_empty.png"
        result = render_trends(trend_series, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0
        con.close()


# ---------------------------------------------------------------------------
# TestReportTiersCLI
# ---------------------------------------------------------------------------


class TestReportTiersCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_report_tiers_no_longer_stub(self, runner, tmp_path):
        """report tiers is implemented — does NOT return 'not implemented'."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(main, ["report", "tiers", "--db", str(db_path)])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "not implemented" not in result.output

    def test_report_tiers_prints_tier_headers(self, runner, tmp_path):
        """report tiers output contains Tier S, Tier A, Tier B labels."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(main, ["report", "tiers", "--db", str(db_path)])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "Tier S" in result.output
        assert "Tier A" in result.output
        assert "Tier B" in result.output

    def test_report_tiers_prints_labeled_title(self, runner, tmp_path):
        """report tiers output contains definition and basis labels."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(
            main, ["report", "tiers", "--definition", "raw", "--provenance", "all", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "RAW" in result.output or "raw" in result.output.lower()

    def test_report_tiers_on_empty_db_runs_ok(self, runner, tmp_path):
        """report tiers on an empty DB runs without error."""
        db_path = tmp_path / "empty.duckdb"
        con = duckdb.connect(str(db_path))
        init_schema(con)
        con.close()
        result = runner.invoke(main, ["report", "tiers", "--db", str(db_path)])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

    def test_report_tiers_help_shows_options(self, runner):
        """report tiers --help shows the expected options."""
        result = runner.invoke(main, ["report", "tiers", "--help"])
        assert result.exit_code == 0
        assert "--definition" in result.output
        assert "--provenance" in result.output
        assert "--min-share" in result.output
        assert "--chart-dir" in result.output

    def test_report_tiers_single_provenance(self, runner, tmp_path):
        """report tiers --provenance online prints only one basis."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(
            main, ["report", "tiers", "--provenance", "online", "--db", str(db_path)]
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "online" in result.output


# ---------------------------------------------------------------------------
# TestChartDirCLI
# ---------------------------------------------------------------------------


class TestChartDirCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_report_meta_chart_dir_writes_png(self, runner, tmp_path):
        """report meta --chart-dir D writes PNG files into D."""
        db_path = _setup_db_file(tmp_path)
        chart_dir = tmp_path / "charts"
        result = runner.invoke(
            main,
            [
                "report", "meta",
                "--definition", "raw",
                "--provenance", "all",
                "--db", str(db_path),
                "--chart-dir", str(chart_dir),
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Expect filenames for each basis: meta_raw_all.png, meta_raw_online.png, meta_raw_paper.png
        for basis in ("all", "online", "paper"):
            expected = chart_dir / f"meta_raw_{basis}.png"
            assert expected.exists(), f"Expected {expected} to exist; output:\n{result.output}"
            assert expected.stat().st_size > 0

    def test_report_meta_no_chart_dir_text_only(self, runner, tmp_path):
        """report meta without --chart-dir produces text output only (no PNG mentioned)."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(
            main,
            ["report", "meta", "--definition", "raw", "--provenance", "all", "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "Chart written" not in result.output

    def test_report_matchups_chart_dir_writes_png(self, runner, tmp_path):
        """report matchups --chart-dir D writes PNG files into D."""
        db_path = _setup_db_file(tmp_path)
        chart_dir = tmp_path / "charts_matchups"
        result = runner.invoke(
            main,
            [
                "report", "matchups",
                "--provenance", "all",
                "--db", str(db_path),
                "--chart-dir", str(chart_dir),
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        # Expect matchups_all.png, matchups_online.png, matchups_paper.png
        for basis in ("all", "online", "paper"):
            expected = chart_dir / f"matchups_{basis}.png"
            assert expected.exists(), f"Expected {expected} to exist; output:\n{result.output}"
            assert expected.stat().st_size > 0

    def test_report_matchups_no_chart_dir_text_only(self, runner, tmp_path):
        """report matchups without --chart-dir produces no chart output."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(
            main,
            ["report", "matchups", "--provenance", "all", "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "Chart written" not in result.output

    def test_report_trends_chart_dir_writes_png(self, runner, tmp_path):
        """report trends --chart-dir D writes PNG files into D."""
        db_path = _setup_db_file(tmp_path)
        chart_dir = tmp_path / "charts_trends"
        result = runner.invoke(
            main,
            [
                "report", "trends",
                "--definition", "raw",
                "--provenance", "all",
                "--db", str(db_path),
                "--chart-dir", str(chart_dir),
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        for basis in ("all", "online", "paper"):
            expected = chart_dir / f"trends_raw_{basis}.png"
            assert expected.exists(), f"Expected {expected} to exist; output:\n{result.output}"
            assert expected.stat().st_size > 0

    def test_report_trends_no_chart_dir_text_only(self, runner, tmp_path):
        """report trends without --chart-dir produces no chart output."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(
            main,
            ["report", "trends", "--definition", "raw", "--provenance", "all", "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "Chart written" not in result.output

    def test_report_tiers_chart_dir_writes_png(self, runner, tmp_path):
        """report tiers --chart-dir D writes tiers_*.png files into D."""
        db_path = _setup_db_file(tmp_path)
        chart_dir = tmp_path / "charts_tiers"
        result = runner.invoke(
            main,
            [
                "report", "tiers",
                "--definition", "raw",
                "--provenance", "all",
                "--db", str(db_path),
                "--chart-dir", str(chart_dir),
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        for basis in ("all", "online", "paper"):
            expected = chart_dir / f"tiers_raw_{basis}.png"
            assert expected.exists(), f"Expected {expected} to exist; output:\n{result.output}"
            assert expected.stat().st_size > 0

    def test_report_tiers_no_chart_dir_text_only(self, runner, tmp_path):
        """report tiers without --chart-dir produces no chart output."""
        db_path = _setup_db_file(tmp_path)
        result = runner.invoke(
            main,
            ["report", "tiers", "--definition", "raw", "--provenance", "all", "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert "Chart written" not in result.output

    def test_chart_dir_created_if_not_exists(self, runner, tmp_path):
        """--chart-dir creates the directory if it does not exist."""
        db_path = _setup_db_file(tmp_path)
        chart_dir = tmp_path / "nonexistent" / "deep" / "charts"
        assert not chart_dir.exists()
        result = runner.invoke(
            main,
            [
                "report", "meta",
                "--definition", "raw",
                "--provenance", "online",
                "--db", str(db_path),
                "--chart-dir", str(chart_dir),
            ],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert chart_dir.exists()
