"""Hermetic CLI tests for the `discover` group (Unit 6 of the discovery engine).

Follows the file-backed-cli-test-db-builder pattern: `_build_discovery_db(tmp_path) -> str`
stands up a tmp DuckDB (schema + a seeded two-camp Doomsday-like pool) and EVERY
`runner.invoke` passes `--db <that path>` — never the default DB. Staging/registry paths are
likewise pinned under tmp_path via `--discovered-path` / `--registry-path` so no test ever
touches the shipped package data.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main


# ---------------------------------------------------------------------------
# DB builders (file-backed, hermetic)
# ---------------------------------------------------------------------------

def _build_discovery_db(tmp_path) -> str:
    """Tmp DuckDB with a clean two-camp 'Doomsday' pool (35 + 35 decks)."""
    from legacy_engine.ingestion import store

    db_path = str(tmp_path / "discovery.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    con.execute(
        "INSERT INTO tournaments VALUES ('t1', 'T', '2026-01-01', NULL, 'Legacy', 'src', 'online')"
    )
    deck_rows = []
    card_rows = []
    idx = 0
    for _ in range(35):
        deck_rows.append(("t1", idx, "p", "W", "Doomsday", None))
        card_rows += [
            ("t1", idx, "main", "Core Land", 4),
            ("t1", idx, "main", "Card A1", 4),
            ("t1", idx, "main", "Card A2", 3),
        ]
        idx += 1
    for _ in range(35):
        deck_rows.append(("t1", idx, "p", "W", "Doomsday", None))
        card_rows += [
            ("t1", idx, "main", "Core Land", 4),
            ("t1", idx, "main", "Card B1", 4),
            ("t1", idx, "main", "Card B2", 3),
        ]
        idx += 1
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", deck_rows)
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", card_rows)
    con.close()
    return db_path


def _build_blob_db(tmp_path) -> str:
    """Tmp DuckDB with a homogeneous 'Doomsday' pool — no separable structure (FAIL case)."""
    from legacy_engine.ingestion import store

    db_path = str(tmp_path / "blob.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    con.execute(
        "INSERT INTO tournaments VALUES ('t1', 'T', '2026-01-01', NULL, 'Legacy', 'src', 'online')"
    )
    deck_rows = []
    card_rows = []
    for idx in range(70):
        deck_rows.append(("t1", idx, "p", "W", "Doomsday", None))
        card_rows += [
            ("t1", idx, "main", "Core Land", 4),
            ("t1", idx, "main", "Flex A", 3),
            ("t1", idx, "main", "Flex B", 2),
        ]
        # Two low-inclusion tech cards keep >=2 cards inside the default flex band
        # (otherwise the run degrades at matrix build, a different honest FAIL path).
        if idx % 3 == 0:
            card_rows.append(("t1", idx, "main", "Tech One", 1))
        if idx % 4 == 0:
            card_rows.append(("t1", idx, "main", "Tech Two", 1))
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", deck_rows)
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", card_rows)
    con.close()
    return db_path


def _curated_registry(tmp_path) -> str:
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({"version": "test", "variants": [], "defaults": {}}, indent=2))
    return str(path)


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# discover run
# ---------------------------------------------------------------------------

class TestDiscoverRun:
    def test_pass_stages_and_reports(self, runner, tmp_path):
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
            "--n-boot", "10",
        ])
        assert result.exit_code == 0, result.output
        assert "// verdict: PASS" in result.output
        assert "// stability:" in result.output
        assert "// params: reducer=svd seed=0 n_boot=10" in result.output
        assert "camp " in result.output
        assert "// staged candidate split for 'Doomsday'" in result.output

        data = json.loads((tmp_path / "discovered.json").read_text())
        assert data["splits"][0]["parent"] == "Doomsday"
        assert data["splits"][0]["status"] == "candidate"
        assert len(data["splits"][0]["camps"]) == 2

    def test_fail_prints_honest_report_and_does_not_stage(self, runner, tmp_path):
        db_path = _build_blob_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
            "--n-boot", "10",
        ])
        assert result.exit_code == 0, result.output
        assert "// verdict: FAIL" in result.output
        # The honest report still shows the gate reasoning — never silently dropped.
        assert "gate A stability" in result.output
        assert "// not staged" in result.output
        assert not (tmp_path / "discovered.json").exists()

    def test_run_carries_double_dipping_guard_note(self, runner, tmp_path):
        db_path = _build_discovery_db(tmp_path)
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", str(tmp_path / "d.json"),
            "--n-boot", "5",
        ])
        assert result.exit_code == 0, result.output
        assert "double-dipping" in result.output

    def test_unknown_archetype_reports_fail_honestly(self, runner, tmp_path):
        db_path = _build_discovery_db(tmp_path)
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Nonexistent",
            "--db", db_path, "--discovered-path", str(tmp_path / "d.json"),
            "--n-boot", "5",
        ])
        assert result.exit_code == 0, result.output
        assert "// verdict: FAIL" in result.output
        assert "no separable structure" in result.output


# ---------------------------------------------------------------------------
# discover list
# ---------------------------------------------------------------------------

class TestDiscoverList:
    def test_empty_registry(self, runner, tmp_path):
        result = runner.invoke(main, [
            "discover", "list", "--discovered-path", str(tmp_path / "nope.json"),
        ])
        assert result.exit_code == 0, result.output
        assert "no staged candidate splits" in result.output

    def test_lists_staged_split(self, runner, tmp_path):
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        run = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5",
        ])
        assert run.exit_code == 0, run.output

        result = runner.invoke(main, ["discover", "list", "--discovered-path", staged])
        assert result.exit_code == 0, result.output
        assert "Doomsday" in result.output
        assert "[status: candidate]" in result.output
        assert "stability=" in result.output
        assert "signature:" in result.output


# ---------------------------------------------------------------------------
# discover promote
# ---------------------------------------------------------------------------

class TestDiscoverPromote:
    def _run_and_get_camp(self, runner, tmp_path) -> tuple[str, str, str]:
        """discover run against the two-camp DB; return (staged_path, registry_path, camp)."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        run = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5",
        ])
        assert run.exit_code == 0, run.output
        data = json.loads((tmp_path / "discovered.json").read_text())
        # Pick the positive camp (the one not named non-*).
        camp = next(
            c["name"] for c in data["splits"][0]["camps"] if not c["name"].startswith("non-")
        )
        return staged, _curated_registry(tmp_path), camp

    def test_promote_appends_rule_and_default(self, runner, tmp_path):
        staged, registry, camp = self._run_and_get_camp(runner, tmp_path)
        result = runner.invoke(main, [
            "discover", "promote", "--archetype", "Doomsday", "--variant", camp,
            "--discovered-path", staged, "--registry-path", registry,
        ])
        assert result.exit_code == 0, result.output
        assert f"// promoted 'Doomsday'/{camp!r}" in result.output
        assert "InMainboard" in result.output

        data = json.loads((tmp_path / "legacy.json").read_text())
        names = [v["name"] for v in data["variants"] if v["parent"] == "Doomsday"]
        assert names == [camp]
        assert data["defaults"]["Doomsday"] == f"non-{camp}"

        staged_data = json.loads((tmp_path / "discovered.json").read_text())
        assert staged_data["splits"][0]["status"] == "promoted"

    def test_promote_unknown_camp_fails_loudly(self, runner, tmp_path):
        staged, registry, _camp = self._run_and_get_camp(runner, tmp_path)
        result = runner.invoke(main, [
            "discover", "promote", "--archetype", "Doomsday", "--variant", "Bogus",
            "--discovered-path", staged, "--registry-path", registry,
        ])
        assert result.exit_code != 0
        assert "no camp 'Bogus'" in result.output

    def test_promote_twice_fails_loudly(self, runner, tmp_path):
        staged, registry, camp = self._run_and_get_camp(runner, tmp_path)
        first = runner.invoke(main, [
            "discover", "promote", "--archetype", "Doomsday", "--variant", camp,
            "--discovered-path", staged, "--registry-path", registry,
        ])
        assert first.exit_code == 0, first.output
        second = runner.invoke(main, [
            "discover", "promote", "--archetype", "Doomsday", "--variant", camp,
            "--discovered-path", staged, "--registry-path", registry,
        ])
        assert second.exit_code != 0
        assert "already promoted" in second.output

    def test_promote_nothing_staged_fails_loudly(self, runner, tmp_path):
        registry = _curated_registry(tmp_path)
        result = runner.invoke(main, [
            "discover", "promote", "--archetype", "Doomsday", "--variant", "X",
            "--discovered-path", str(tmp_path / "empty.json"),
            "--registry-path", registry,
        ])
        assert result.exit_code != 0
        assert "no staged split" in result.output
