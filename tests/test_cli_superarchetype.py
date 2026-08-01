"""CLI tests for the `superarchetype` command group (run|list|explain).

House style: file-backed hermetic DuckDB via `_build_superarchetype_db(tmp_path) -> str`, every
`runner.invoke` pinned to `--db <that path>` — never the default DB. The derived registry is always
redirected to a tmp path via `--registry-path`-equivalent monkeypatching of the config constant, so
no test writes into the project's data directory, and the curated registry is monkeypatched to empty
so the shipped file is never read by a test.
"""

from __future__ import annotations

import duckdb
import pytest
from click.testing import CliRunner

from legacy_engine.cli import main

_STAPLES = ["Brainstorm", "Force of Will", "Ponder", "Wasteland", "Underground Sea"]
_FAMILIES = {
    "combo": ["Show and Tell", "Omniscience", "Emrakul", "Atraxa", "Ancient Tomb", "Lotus Petal"],
    "fair": ["Swords to Plowshares", "Stoneforge Mystic", "Batterskull", "Flooded Strand",
             "Plains", "Thalia"],
    "graveyard": ["Cabal Therapy", "Narcomoeba", "Bridge from Below", "Cephalid Coliseum",
                  "Ichorid", "Prized Amalgam"],
    "lands": ["Life from the Loam", "Dark Depths", "Thespian's Stage", "Exploration",
              "Mox Diamond", "Bojuka Bog"],
}
_DEFINERS = [
    ("Show and Tell", "combo", "Sneak Attack"),
    ("Aluren", "combo", "Acererak the Archlich"),
    ("Azorius Stoneblade", "fair", "Sword of Fire and Ice"),
    ("Death & Taxes", "fair", "Kaldra Compleat"),
    ("Dredge", "graveyard", "Creeping Chill"),
    ("Oops! All Spells", "graveyard", "Balustrade Spy"),
    ("Lands", "lands", "Sphere of Resistance"),
    ("Cradle Control", "lands", "Gaea's Cradle"),
]
_GENERIC_POOL = [
    "Chalice of the Void", "Karakas", "Pithing Needle", "Grafdigger's Cage",
    "Endurance", "Mindbreak Trap", "Surgical Extraction", "Boseiju, Who Endures",
]


def _build_superarchetype_db(tmp_path) -> str:
    """Eight definers in four planted families plus one long-tail brew and one two-card brew."""
    db_path = str(tmp_path / "superarchetype_cli.duckdb")
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE tournaments (id VARCHAR, name VARCHAR, date VARCHAR, "
                "uri VARCHAR, format VARCHAR, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, "
                "result VARCHAR, archetype VARCHAR, variant VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, "
                "board VARCHAR, name VARCHAR, count INTEGER)")
    con.execute(
        "INSERT INTO tournaments VALUES ('t1', 'Test', '2026-06-01', '', 'Legacy', 'x', 'online')"
    )

    deck_idx = 0

    def _add(archetype: str, cards: list[str], n: int) -> None:
        nonlocal deck_idx
        for _ in range(n):
            con.execute(
                "INSERT INTO decks VALUES ('t1', ?, ?, '5-0', ?, NULL)",
                [deck_idx, f"p{deck_idx}", archetype],
            )
            for card in cards:
                con.execute(
                    "INSERT INTO deck_cards VALUES ('t1', ?, 'main', ?, 4)", [deck_idx, card]
                )
            deck_idx += 1

    for i, (label, family, unique) in enumerate(_DEFINERS):
        generics = [_GENERIC_POOL[i], _GENERIC_POOL[(i + 3) % len(_GENERIC_POOL)]]
        _add(label, _STAPLES + _FAMILIES[family] + [unique] + generics, 40)

    _add("Tiny Combo Brew", _FAMILIES["combo"][:5] + ["Brainstorm"], 4)
    _add("Two Card Brew", ["Odd Card A", "Odd Card B"], 3)
    con.close()
    return db_path


@pytest.fixture
def isolated_registry(tmp_path, monkeypatch):
    """Redirect the derived registry path and empty the curated registry for every CLI test."""
    path = tmp_path / "derived" / "superarchetypes.json"
    monkeypatch.setattr("legacy_engine.config.DERIVED_SUPERARCHETYPES_PATH", path)
    monkeypatch.setattr(
        "legacy_engine.analytics.superarchetype.registry.CURATED_SUPERARCHETYPES", {}
    )
    return path


@pytest.fixture
def runner():
    return CliRunner()


def _run(runner, db_path, *extra):
    return runner.invoke(
        main, ["superarchetype", "run", "--db", db_path, "--n-boot", "10", *extra]
    )


class TestSuperarchetypeRun:
    def test_derives_and_persists_a_taxonomy(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path)
        assert result.exit_code == 0, result.output
        assert "// superarchetype run:" in result.output
        assert "8 definer(s)" in result.output
        assert "format staples hard-removed (5)" in result.output
        assert "// written" in result.output
        assert isolated_registry.exists()

    def test_planted_families_land_together(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path)
        assert result.exit_code == 0, result.output
        assert "Show and Tell + Aluren" in result.output or "Aluren + Show and Tell" in result.output

    def test_every_provenance_and_audit_line_is_comment_prefixed(
        self, tmp_path, runner, isolated_registry
    ):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path)
        for needle in ("// stability:", "// churn:", "// unassigned"):
            assert needle in result.output

    def test_long_tail_is_assigned_and_labeled(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path)
        assert "Tiny Combo Brew  (assigned" in result.output

    def test_below_floor_archetype_is_named_not_dropped(
        self, tmp_path, runner, isolated_registry
    ):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path)
        assert "Two Card Brew: below assignee core floor" in result.output

    def test_dry_run_writes_nothing(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path, "--dry-run")
        assert result.exit_code == 0, result.output
        assert "// dry run — nothing written" in result.output
        assert not isolated_registry.exists()

    def test_is_deterministic_across_invocations(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        first = _run(runner, db_path, "--dry-run").output
        second = _run(runner, db_path, "--dry-run").output
        assert first == second

    def test_a_second_run_reports_churn_against_the_first(
        self, tmp_path, runner, isolated_registry
    ):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = _run(runner, db_path)
        assert result.exit_code == 0, result.output
        assert "co-membership agreement 1.000" in result.output

    def test_an_impossible_au_floor_degrades_with_named_singletons(
        self, tmp_path, runner, isolated_registry
    ):
        db_path = _build_superarchetype_db(tmp_path)
        result = _run(runner, db_path, "--au-min", "1.1")
        assert result.exit_code == 0, result.output
        assert "no branch cleared the AU cut" in result.output
        assert "au-unsupported singleton" in result.output

    def test_an_empty_corpus_degrades_loudly(self, tmp_path, runner, isolated_registry):
        db_path = str(tmp_path / "empty.duckdb")
        con = duckdb.connect(db_path)
        con.execute("CREATE TABLE tournaments (id VARCHAR, date VARCHAR)")
        con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, "
                    "archetype VARCHAR)")
        con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, "
                    "board VARCHAR, name VARCHAR, count INTEGER)")
        con.close()
        result = _run(runner, db_path)
        assert result.exit_code == 0, result.output
        assert "// DEGRADED: no taxonomy derived" in result.output


class TestSuperarchetypeList:
    def test_reports_absence_honestly(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        result = runner.invoke(main, ["superarchetype", "list", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "(no superarchetype registry — run `superarchetype run` first)" in result.output

    def test_lists_clusters_with_provenance_after_a_run(
        self, tmp_path, runner, isolated_registry
    ):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = runner.invoke(main, ["superarchetype", "list", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "// derived over" in result.output
        assert "(derived, n=40)" in result.output
        assert "sa-00" in result.output

    def test_filters_to_one_cluster(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = runner.invoke(
            main, ["superarchetype", "list", "--db", db_path, "--cluster", "sa-001"]
        )
        assert result.exit_code == 0, result.output
        assert "sa-002" not in result.output

    def test_unknown_cluster_fails_loudly(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = runner.invoke(
            main, ["superarchetype", "list", "--db", db_path, "--cluster", "sa-999"]
        )
        assert result.exit_code != 0
        assert "unknown cluster" in result.output


class TestSuperarchetypeExplain:
    def test_walks_an_assignment(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = runner.invoke(main, ["superarchetype", "explain", "Aluren", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "=== Aluren — superarchetype assignment ===" in result.output
        assert "// cluster: sa-" in result.output
        assert "// provenance: derived" in result.output
        assert "shared (" in result.output
        assert "multiplicity correction" in result.output

    def test_names_the_reason_for_an_unassigned_archetype(
        self, tmp_path, runner, isolated_registry
    ):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = runner.invoke(
            main, ["superarchetype", "explain", "Two Card Brew", "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        assert "// UNASSIGNED: below assignee core floor" in result.output

    def test_unknown_archetype_fails_loudly(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        _run(runner, db_path)
        result = runner.invoke(main, ["superarchetype", "explain", "Nope", "--db", db_path])
        assert result.exit_code != 0
        assert "unknown archetype" in result.output

    def test_without_a_registry_it_says_so(self, tmp_path, runner, isolated_registry):
        db_path = _build_superarchetype_db(tmp_path)
        result = runner.invoke(main, ["superarchetype", "explain", "Aluren", "--db", db_path])
        assert result.exit_code != 0
        assert "no superarchetype registry" in result.output
