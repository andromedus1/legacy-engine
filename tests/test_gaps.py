"""Tests for advisory.gaps — the archetype-gap finder (epic-gap-discovery-archetype-gaps).

Two layers:
- Pure ``_assemble_gaps`` over hand-built FieldDistribution + DeckRanking (no DB, no MC) —
  exercises the gap-score arithmetic, ordering, tie-break, tier, and the thin-data exclusion.
- Corpus-backed ``compute_archetype_gaps`` + the ``report gaps`` CLI for the DB/MC seam.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.advisory.gaps import _assemble_gaps, compute_archetype_gaps
from legacy_engine.advisory.positioning import DeckRanking
from legacy_engine.cli import main

SEED = 42


def _ranking(s_mean, s_quantile, data_coverage, low_coverage) -> DeckRanking:
    decks = list(s_mean)
    return DeckRanking(
        decks=decks,
        p_best={d: 0.0 for d in decks},
        s_mean=s_mean,
        s_ci={d: (s_mean[d] - 0.05, s_mean[d] + 0.05) for d in decks},
        s_quantile=s_quantile,
        quantile_level=0.25,
        data_coverage=data_coverage,
        low_coverage=set(low_coverage),
        pairwise={},
        field_source="global",
    )


def _field(shares, counts) -> FieldDistribution:
    return FieldDistribution(
        shares=shares, field_source="global", counts=counts, no_data=frozenset(), warnings=()
    )


class TestAssembleGaps:
    def _inputs(self):
        shares = {"ArchA": 0.05, "ArchB": 0.25, "ArchC": 0.10, "ArchD": 0.02}
        counts = {"ArchA": 120, "ArchB": 300, "ArchC": 200, "ArchD": 20}
        s_mean = {"ArchA": 0.55, "ArchB": 0.55, "ArchC": 0.60, "ArchD": 0.45}
        s_quantile = {"ArchA": 0.50, "ArchB": 0.52, "ArchC": 0.55, "ArchD": 0.40}
        coverage = {"ArchA": 0.9, "ArchB": 1.0, "ArchC": 0.2, "ArchD": 0.8}
        field = _field(shares, counts)
        ranking = _ranking(s_mean, s_quantile, coverage, low_coverage={"ArchC"})
        return field, ranking

    def test_popularity_penalty_ordering(self):
        field, ranking = self._inputs()
        report = _assemble_gaps(field, ranking, share_weight=1.0, min_coverage=0.5)
        # gaps: A=0.50, D=0.43, B=0.30; C excluded (low coverage)
        assert [g.archetype for g in report.gaps] == ["ArchA", "ArchD", "ArchB"]

    def test_gap_score_arithmetic(self):
        field, ranking = self._inputs()
        report = _assemble_gaps(field, ranking, share_weight=1.0, min_coverage=0.5)
        by = {g.archetype: g for g in report.gaps}
        assert by["ArchA"].gap_score == pytest.approx(0.55 - 0.05)
        assert by["ArchB"].gap_score == pytest.approx(0.55 - 0.25)

    def test_share_weight_scales_penalty(self):
        field, ranking = self._inputs()
        report = _assemble_gaps(field, ranking, share_weight=2.0, min_coverage=0.5)
        by = {g.archetype: g for g in report.gaps}
        assert by["ArchB"].gap_score == pytest.approx(0.55 - 2.0 * 0.25)

    def test_thin_data_excluded_not_hidden(self):
        field, ranking = self._inputs()
        report = _assemble_gaps(field, ranking, share_weight=1.0, min_coverage=0.5)
        assert report.excluded_low_coverage == ["ArchC"]
        assert "ArchC" not in {g.archetype for g in report.gaps}

    def test_tier_from_counts(self):
        field, ranking = self._inputs()
        report = _assemble_gaps(field, ranking, share_weight=1.0, min_coverage=0.5)
        by = {g.archetype: g for g in report.gaps}
        assert by["ArchA"].tier == "established"   # 120 ≥ 100
        assert by["ArchD"].tier == "speculative"   # 20 < 30

    def test_metadata_passthrough(self):
        field, ranking = self._inputs()
        report = _assemble_gaps(field, ranking, share_weight=1.5, min_coverage=0.4)
        assert report.field_source == "global"
        assert report.risk_quantile == 0.25
        assert report.share_weight == 1.5
        assert report.min_coverage == 0.4


class TestComputeArchetypeGaps:
    def test_seam_ranks_and_is_deterministic(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=50)  # established matchup data
        a = compute_archetype_gaps(con, min_coverage=0.0, seed=SEED)
        b = compute_archetype_gaps(con, min_coverage=0.0, seed=SEED)
        names_a = [g.archetype for g in a.gaps]
        names_b = [g.archetype for g in b.gaps]
        assert names_a == names_b                     # determinism under a fixed seed
        assert set(names_a) == {"Control", "Combo"}   # both positionable archetypes surface
        # Control beats Combo in the corpus → higher S, higher gap → ranked first.
        assert names_a[0] == "Control"
        con.close()

    def test_empty_field_no_crash(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        con.execute("DELETE FROM decks")  # strip labels → empty positionable field
        report = compute_archetype_gaps(con, seed=SEED)
        assert report.gaps == [] and report.excluded_low_coverage == []
        con.close()


class TestReportGapsCLI:
    @pytest.fixture
    def db_with_corpus(self, tmp_path, make_rounds_corpus):
        db_path = tmp_path / "gaps.duckdb"
        con_mem, _ = make_rounds_corpus(n_repeats=50)
        from legacy_engine.ingestion import store as _store
        con_file = _store.connect(str(db_path))
        _store.init_schema(con_file)
        for table in ("tournaments", "decks", "deck_cards", "rounds"):
            rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                placeholders = ", ".join(["?"] * len(rows[0]))
                con_file.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
        con_mem.close()
        con_file.close()
        return str(db_path)

    def test_gaps_help_lists_options(self):
        result = CliRunner().invoke(main, ["report", "gaps", "--help"])
        assert result.exit_code == 0
        for opt in ("--share-weight", "--min-coverage", "--risk-quantile", "--seed"):
            assert opt in result.output

    def test_gaps_listed_in_report_group(self):
        result = CliRunner().invoke(main, ["report", "--help"])
        assert result.exit_code == 0
        assert "gaps" in result.output

    def test_gaps_happy_path(self, db_with_corpus):
        result = CliRunner().invoke(
            main, ["report", "gaps", "--db", db_with_corpus, "--min-coverage", "0.0", "--seed", "42"]
        )
        assert result.exit_code == 0, result.output
        assert "Archetype Gaps" in result.output
        assert "Control" in result.output

    def test_gaps_empty_db_no_crash(self, tmp_path):
        db_path = str(tmp_path / "empty.duckdb")
        from legacy_engine.ingestion import store as _store
        con = _store.connect(db_path)
        _store.init_schema(con)
        con.close()
        result = CliRunner().invoke(main, ["report", "gaps", "--db", db_path])
        assert result.exit_code == 0, result.output
