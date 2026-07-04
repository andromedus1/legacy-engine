"""Tests for advisory.sweep — the archetype-sweep backtest (batch divergence mining).

Pure clustering/ranking functions are exercised with hand-built BoardBacktest objects (no
DB — objective-search-split). Driver + CLI tests use the file-backed-cli-test-db-builder
pattern: a tmp DuckDB, ALWAYS passed via --db, with `recommend_sideboard` monkeypatched at
the backtest module seam (the same seam test_backtest.py uses).
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from legacy_engine.advisory import backtest as backtest_mod
from legacy_engine.advisory.backtest import BoardBacktest
from legacy_engine.advisory.sweep import (
    UNCLASSIFIED_TAG,
    ArchetypeSweepEntry,
    ClusterMember,
    DivergenceCluster,
    cluster_divergences,
    enumerate_archetypes,
    rank_clusters,
    run_sweep,
)
from legacy_engine.cli import main
from legacy_engine.ingestion import store

# Reuse the hermetic corpus + fakes from the backtest tests (same fixture semantics).
from tests.test_backtest import _build_backtest_db, _fake_field, _fake_package


# ---------------------------------------------------------------------------
# Hand-built inputs for the pure functions
# ---------------------------------------------------------------------------


def _bt(
    archetype: str,
    *,
    confidence: str | None = "evolving",
    scorer_only: tuple[str, ...] = (),
    winners_only: tuple[str, ...] = (),
    observed: dict[str, float] | None = None,
) -> BoardBacktest:
    return BoardBacktest(
        archetype=archetype,
        n_winning_decks=0 if confidence is None else 40,
        confidence=confidence,
        recommended=scorer_only,
        observed_frequency=observed or {},
        overlap=(),
        scorer_only=scorer_only,
        winners_only=winners_only,
    )


def _entry(archetype: str, bt: BoardBacktest | None, n_decks: int = 50) -> ArchetypeSweepEntry:
    return ArchetypeSweepEntry(
        archetype=archetype,
        n_decks_in_window=n_decks,
        backtest=bt,
        skipped_reason=None if bt is not None else "below --min-decks (5 < 20)",
    )


_TAGS = {
    "Fatal Push": frozenset({"creature-based"}),
    "Snuff Out": frozenset({"creature-based"}),
    "Defense Grid": frozenset({"combo", "storm-reliant"}),
    "Mystery Card": frozenset(),
}


def _lookup(name: str) -> frozenset[str]:
    return _TAGS.get(name, frozenset())


class TestClusterDivergences:
    def test_shared_tag_groups_cards_across_archetypes(self):
        entries = [
            _entry("Dimir Tempo", _bt(
                "Dimir Tempo",
                winners_only=("Fatal Push", "Snuff Out"),
                observed={"Fatal Push": 0.6, "Snuff Out": 0.4},
            )),
            _entry("Grixis Reanimator", _bt(
                "Grixis Reanimator",
                winners_only=("Fatal Push",),
                observed={"Fatal Push": 0.5},
            )),
        ]
        clusters = cluster_divergences(entries, _lookup)
        creature = [c for c in clusters if c.tag == "creature-based"]
        assert len(creature) == 1
        c = creature[0]
        assert c.direction == "winners_only"
        assert c.n_archetypes == 2
        assert {(m.card, m.archetype) for m in c.members} == {
            ("Fatal Push", "Dimir Tempo"),
            ("Fatal Push", "Grixis Reanimator"),
            ("Snuff Out", "Dimir Tempo"),
        }
        assert c.total_adoption == pytest.approx(1.5)

    def test_directions_never_merge(self):
        entries = [
            _entry("A", _bt("A", scorer_only=("Fatal Push",), winners_only=("Snuff Out",),
                            observed={"Snuff Out": 0.5, "Fatal Push": 0.15})),
        ]
        clusters = cluster_divergences(entries, _lookup)
        keys = {(c.direction, c.tag) for c in clusters}
        assert ("scorer_only", "creature-based") in keys
        assert ("winners_only", "creature-based") in keys
        # scorer_only members keep their REAL sub-threshold adoption (15% here) — a
        # recommendation some winners play is a weaker false-positive signal than one
        # nobody plays; clamping to 0.0 would fabricate away that distinction.
        so = next(c for c in clusters if c.direction == "scorer_only")
        assert [m.adoption_pct for m in so.members] == [pytest.approx(0.15)]

    def test_multi_tag_card_contributes_to_every_tag(self):
        entries = [_entry("A", _bt("A", scorer_only=("Defense Grid",)))]
        clusters = cluster_divergences(entries, _lookup)
        tags = {c.tag for c in clusters}
        assert tags == {"combo", "storm-reliant"}

    def test_untagged_card_lands_in_unclassified_never_dropped(self):
        entries = [_entry("A", _bt("A", winners_only=("Mystery Card",),
                                   observed={"Mystery Card": 0.3}))]
        clusters = cluster_divergences(entries, _lookup)
        assert len(clusters) == 1
        assert clusters[0].tag == UNCLASSIFIED_TAG
        assert clusters[0].members[0].card == "Mystery Card"

    def test_no_winner_sample_contributes_nothing(self):
        entries = [
            _entry("A", _bt("A", confidence=None, winners_only=("Fatal Push",))),
            _entry("B", None),  # skipped entry
        ]
        assert cluster_divergences(entries, _lookup) == ()

    def test_tier_breakdown_counts_distinct_archetypes(self):
        entries = [
            _entry("A", _bt("A", confidence="evolving", winners_only=("Fatal Push",),
                            observed={"Fatal Push": 0.5})),
            _entry("B", _bt("B", confidence="speculative", winners_only=("Snuff Out",),
                            observed={"Snuff Out": 0.4})),
        ]
        c = cluster_divergences(entries, _lookup)[0]
        assert c.tier_breakdown == {"evolving": 1, "speculative": 1}
        assert c.n_archetypes_nonspeculative == 1


class TestRankClusters:
    def _cluster(self, tag: str, direction: str, nonspec: int, adoption: float,
                 n_arch: int) -> DivergenceCluster:
        return DivergenceCluster(
            tag=tag,
            direction=direction,
            members=(ClusterMember("X", "A", adoption, "evolving"),),
            n_archetypes=n_arch,
            n_archetypes_nonspeculative=nonspec,
            total_adoption=adoption,
            tier_breakdown={},
        )

    def test_nonspeculative_support_outranks_raw_archetype_count(self):
        thin_wide = self._cluster("thin-wide", "winners_only", nonspec=0, adoption=2.0, n_arch=3)
        solid_narrow = self._cluster("solid-narrow", "winners_only", nonspec=2, adoption=0.8, n_arch=2)
        ranked = rank_clusters([thin_wide, solid_narrow])
        assert [c.tag for c in ranked] == ["solid-narrow", "thin-wide"]
        # The thin cluster carries its explicit marker.
        assert ranked[1].n_archetypes_nonspeculative == 0

    def test_adoption_breaks_ties_within_same_support(self):
        low = self._cluster("low", "winners_only", nonspec=1, adoption=0.3, n_arch=1)
        high = self._cluster("high", "winners_only", nonspec=1, adoption=0.9, n_arch=1)
        assert [c.tag for c in rank_clusters([low, high])] == ["high", "low"]

    def test_scorer_only_adoption_ranks_inverted(self):
        """For false positives, LOWER winner adoption = harder false positive: a cluster
        of 0%-played recommendations outranks one winners play at 19%."""
        soft = self._cluster("soft-fp", "scorer_only", nonspec=1, adoption=0.19, n_arch=1)
        hard = self._cluster("hard-fp", "scorer_only", nonspec=1, adoption=0.0, n_arch=1)
        assert [c.tag for c in rank_clusters([soft, hard])] == ["hard-fp", "soft-fp"]

    def test_deterministic_tail_by_direction_and_tag(self):
        a = self._cluster("alpha", "scorer_only", nonspec=1, adoption=0.0, n_arch=1)
        b = self._cluster("alpha", "winners_only", nonspec=1, adoption=0.0, n_arch=1)
        ranked = rank_clusters([b, a])
        assert [c.direction for c in ranked] == ["scorer_only", "winners_only"]


# ---------------------------------------------------------------------------
# Driver + enumeration on the hermetic corpus
# ---------------------------------------------------------------------------


class TestEnumerateArchetypes:
    def test_counts_window_and_min_decks(self, tmp_path):
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        try:
            # Corpus: Doomsday 10 decks, Boulder 8, Reanimator 6 across T1-T3.
            rows = enumerate_archetypes(con, since=None, until=None, min_decks=7)
        finally:
            con.close()
        assert rows == [("Doomsday", 10, True), ("Boulder", 8, True), ("Reanimator", 6, False)]

    def test_unknown_and_null_are_excluded(self, tmp_path):
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        try:
            con.execute("UPDATE decks SET archetype = 'Unknown' WHERE archetype = 'Reanimator'")
            con.execute("UPDATE decks SET archetype = NULL WHERE archetype = 'Doomsday'")
            rows = enumerate_archetypes(con, since=None, until=None, min_decks=1)
        finally:
            con.close()
        assert [r[0] for r in rows] == ["Boulder"]


class TestRunSweep:
    def test_sweep_entries_skips_and_clusters(self, tmp_path, monkeypatch):
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod,
            "recommend_sideboard",
            lambda *a, **k: _fake_package({"Toxic Deluge": 1}),
        )
        seen_progress: list[tuple[int, int, str]] = []
        try:
            result = run_sweep(
                con, _fake_field(), min_decks=7,
                progress=lambda i, t, e: seen_progress.append((i, t, e.archetype)),
            )
        finally:
            con.close()

        by_arch = {e.archetype: e for e in result.entries}
        assert by_arch["Boulder"].backtest is not None
        assert by_arch["Reanimator"].backtest is None
        assert "below --min-decks (6 < 7)" == by_arch["Reanimator"].skipped_reason
        # Progress fired once per enumerated archetype, in order, with the right total.
        assert seen_progress == [(1, 3, "Doomsday"), (2, 3, "Boulder"), (3, 3, "Reanimator")]

        # Boulder's winners run Surgical Extraction (100%) which the fake scorer never
        # recommends -> a winners_only divergence exists; Surgical is catalog-curated so
        # it clusters under a real tag. Non-catalog cards (Ravenous Trap — the hermetic DB
        # has no `cards` oracle rows) land in the honest unclassified cluster, not dropped.
        winners = {c.tag: c for c in result.clusters if c.direction == "winners_only"}
        assert "graveyard-recursion" in winners
        assert "Surgical Extraction" in {m.card for m in winners["graveyard-recursion"].members}
        assert UNCLASSIFIED_TAG in winners
        assert "Ravenous Trap" in {m.card for m in winners[UNCLASSIFIED_TAG].members}

    def test_solver_pass_through(self, tmp_path, monkeypatch):
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        seen: dict = {}

        def _capture(*a, **k):
            seen.update(k)
            return _fake_package({})

        monkeypatch.setattr(backtest_mod, "recommend_sideboard", _capture)
        try:
            result = run_sweep(con, _fake_field(), min_decks=7, solver="greedy")
        finally:
            con.close()
        assert seen.get("solver") == "greedy"
        assert result.solver == "greedy"

    def test_backtest_raise_becomes_skipped_entry_and_warning_never_a_crash(
        self, tmp_path, monkeypatch
    ):
        """backtest_board never raises by contract, but if it ever does the sweep must
        degrade that archetype to a skipped entry + warning and keep sweeping."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)

        def _boom(con, archetype, *a, **k):
            raise RuntimeError(f"backtest exploded for {archetype}")

        import legacy_engine.advisory.sweep as sweep_mod

        monkeypatch.setattr(sweep_mod, "backtest_board", _boom)
        try:
            result = run_sweep(con, _fake_field(), min_decks=7)
        finally:
            con.close()

        qualifying = [e for e in result.entries if e.n_decks_in_window >= 7]
        assert qualifying and all(e.backtest is None for e in qualifying)
        assert all("backtest failed" in (e.skipped_reason or "") for e in qualifying)
        assert any("backtest exploded" in w for w in result.warnings)
        assert result.clusters == ()

    def test_empty_corpus_degrades_honestly(self, tmp_path):
        db_path = str(tmp_path / "empty.duckdb")
        con = store.connect(db_path)
        try:
            result = run_sweep(con, _fake_field(), min_decks=1)
        finally:
            con.close()
        assert result.entries == ()
        assert result.clusters == ()


# ---------------------------------------------------------------------------
# CLI: advise sweep
# ---------------------------------------------------------------------------


class TestAdviseSweepCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_renders_headers_progress_clusters_and_caveat(self, tmp_path, runner, monkeypatch):
        db_path = _build_backtest_db(tmp_path)
        monkeypatch.setattr(
            backtest_mod,
            "recommend_sideboard",
            lambda *a, **k: _fake_package({"Toxic Deluge": 1}),
        )
        field_file = tmp_path / "field.txt"
        field_file.write_text("0.6 Boulder\n0.4 Doomsday\n")

        result = runner.invoke(
            main,
            [
                "advise", "sweep",
                "--field", str(field_file),
                "--since", "2026-01-01",
                "--min-decks", "7",
                "--db", db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        out = result.output
        assert "// sweep: archetype-sweep backtest" in out
        assert "// window: since=2026-01-01" in out
        assert "min-decks=7" in out
        assert "// [2/3] Boulder: winners n=" in out
        assert "Reanimator: SKIPPED — below --min-decks (6 < 7)" in out
        assert "Winners-only clusters" in out
        assert "Scorer-only clusters" in out
        assert "Substrate-ready findings" in out
        assert (
            "// divergence is a signal to investigate, not proof of error "
            "(winning boards are self-selected + metagame-lagged)" in out
        )

    def test_json_payload_round_trips_with_copy_histograms(self, tmp_path, runner, monkeypatch):
        db_path = _build_backtest_db(tmp_path)
        monkeypatch.setattr(
            backtest_mod,
            "recommend_sideboard",
            lambda *a, **k: _fake_package({"Toxic Deluge": 2}),
        )
        field_file = tmp_path / "field.txt"
        field_file.write_text("0.6 Boulder\n0.4 Doomsday\n")
        json_path = tmp_path / "sweep.json"

        result = runner.invoke(
            main,
            [
                "advise", "sweep",
                "--field", str(field_file),
                "--since", "2026-01-01",
                "--min-decks", "7",
                "--json", str(json_path),
                "--db", db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert f"// json payload written: {json_path}" in result.output

        payload = json.loads(json_path.read_text())
        assert payload["min_decks"] == 7
        assert payload["window"]["since"] == "2026-01-01"
        by_arch = {a["archetype"]: a for a in payload["archetypes"]}
        boulder = by_arch["Boulder"]
        # The copy dimension the distribution study consumes: solver copies + histograms.
        assert boulder["recommended_counts"] == {"Toxic Deluge": 2}
        assert boulder["observed_copy_distribution"]["Surgical Extraction"] == {"1": 4}
        assert boulder["n_winning_decks"] == 4
        # Skipped archetypes serialize their reason and no backtest keys.
        assert by_arch["Reanimator"]["skipped_reason"] is not None
        assert "n_winning_decks" not in by_arch["Reanimator"]
        assert payload["clusters"], "clusters must be present"

    def test_degenerate_corpus_is_honest_not_a_crash(self, tmp_path, runner):
        db_path = str(tmp_path / "empty.duckdb")
        con = store.connect(db_path)
        con.close()
        field_file = tmp_path / "field.txt"
        field_file.write_text("1.0 Boulder\n")

        result = runner.invoke(
            main,
            ["advise", "sweep", "--field", str(field_file), "--since", "2026-01-01",
             "--db", db_path],
        )
        assert result.exit_code == 0, result.output
        assert "swept 0 archetypes" in result.output
