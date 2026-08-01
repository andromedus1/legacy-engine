"""Hermetic CLI tests for the `discover` group (Unit 6 of the discovery engine).

Follows the file-backed-cli-test-db-builder pattern: `_build_discovery_db(tmp_path) -> str`
stands up a tmp DuckDB (schema + a seeded two-camp Doomsday-like pool) and EVERY
`runner.invoke` passes `--db <that path>` — never the default DB. Staging/registry paths are
likewise pinned under tmp_path via `--discovered-path` / `--registry-path` so no test ever
touches the shipped package data.

`--all-pool` on `discover run`: these fixtures' tournaments are dated '2026-01-01' with no
`entity_eras` row for 'Doomsday'/'Lands', so the era-aware default (epic-stable-era-windows-
discovery-gate Unit 2) falls back to the CURRENT ban-regime window (`entity_era_window`'s
"absent entirely" branch) — a window that will drift ahead of a fixed fixture date over time.
Tests that exercise the discovery pipeline itself (not the era-default window logic, which has
its own dedicated tests below) pass `--all-pool` to pin the pre-epic unwindowed-pool behavior.
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


def _build_two_generation_db(tmp_path) -> str:
    """Tmp DuckDB: the same clean two-camp 'Doomsday' split, but each camp's decks are dated a
    full list-generation apart (camp A ~2025-06, camp B ~2026-05) — Gate C's calibration shape
    (epic-stable-era-windows-discovery-gate Unit 1), used here to exercise the CLI's Gate C
    surfacing (report warning + per-camp median/pct_current rendering)."""
    from legacy_engine.ingestion import store

    db_path = str(tmp_path / "two_gen.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    con.execute(
        "INSERT INTO tournaments VALUES ('old', 'Old', '2025-06-01', NULL, 'Legacy', 'src', 'online')"
    )
    con.execute(
        "INSERT INTO tournaments VALUES ('new', 'New', '2026-05-01', NULL, 'Legacy', 'src', 'online')"
    )
    deck_rows = []
    card_rows = []
    for idx in range(35):
        deck_rows.append(("old", idx, "p", "W", "Doomsday", None))
        card_rows += [
            ("old", idx, "main", "Core Land", 4),
            ("old", idx, "main", "Card A1", 4),
            ("old", idx, "main", "Card A2", 3),
        ]
    for idx in range(35):
        deck_rows.append(("new", idx, "p", "W", "Doomsday", None))
        card_rows += [
            ("new", idx, "main", "Core Land", 4),
            ("new", idx, "main", "Card B1", 4),
            ("new", idx, "main", "Card B2", 3),
        ]
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
            "--n-boot", "10", "--all-pool",
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
            "--n-boot", "10", "--all-pool",
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

    def test_rerun_echoes_honest_replacement_of_prior_staged_candidate(self, runner, tmp_path):
        """Finding 3: re-running `discover run` for the same parent silently overwrote the
        staged candidate before — must now echo what it replaced."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")

        first = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert first.exit_code == 0, first.output
        assert "// replaced prior staged candidate" not in first.output

        second = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert second.exit_code == 0, second.output
        assert "// replaced prior staged candidate for 'Doomsday'" in second.output
        assert "generated_from=" in second.output
        assert "camps=" in second.output

    def test_different_parent_does_not_trigger_replacement_echo(self, runner, tmp_path):
        """The replacement echo must fire only on a genuine same-parent overwrite, not whenever
        something is staged."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")

        first = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert first.exit_code == 0, first.output

        # A second DB (distinct file, different parent archetype name) — first-ever stage for
        # that parent, so no replacement should be reported.
        db_path2 = _build_discovery_db(tmp_path / "second")
        from legacy_engine.ingestion import store
        con2 = store.connect(db_path2)
        con2.execute("UPDATE decks SET archetype = 'Lands' WHERE archetype = 'Doomsday'")
        con2.close()

        second = runner.invoke(main, [
            "discover", "run", "--archetype", "Lands",
            "--db", db_path2, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert second.exit_code == 0, second.output
        assert "// replaced prior staged candidate" not in second.output


# ---------------------------------------------------------------------------
# discover run — era-aware default window + --all-pool escape (Unit 2)
# ---------------------------------------------------------------------------

class TestDiscoverRunEraDefault:
    def test_no_era_data_falls_back_to_ban_regime_and_excludes_stale_fixture(self, runner, tmp_path):
        """No `entity_eras` row for 'Doomsday' -> `entity_era_window`'s "absent entirely"
        branch (ban-regime fallback, label 'ban regime'). The fixture's tournament (2026-01-01)
        predates the live ban regime, so the era-default pool ends up empty and the split
        degrades honestly rather than silently defaulting to the full corpus."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5",
        ])
        assert result.exit_code == 0, result.output
        assert "// pool window: since " in result.output
        assert "(ban regime)" in result.output
        assert "// verdict: FAIL" in result.output
        assert "no separable structure" in result.output
        assert not (tmp_path / "discovered.json").exists()

    def test_all_pool_restores_full_corpus_and_stages(self, runner, tmp_path):
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "10", "--all-pool",
        ])
        assert result.exit_code == 0, result.output
        assert "// pool window: full corpus (--all-pool); % current vs " in result.output
        assert "// verdict: PASS" in result.output
        assert (tmp_path / "discovered.json").exists()

    def test_explicit_since_overrides_era_default_and_all_pool(self, runner, tmp_path):
        """An explicit --since wins over both the era-default AND a simultaneous --all-pool —
        and doesn't get the dedicated `// pool window:` echo (that line is era-default/--all-pool
        only; the existing `// window: ...` report line already covers the explicit case)."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "10",
            "--since", "2026-01-01", "--all-pool",
        ])
        assert result.exit_code == 0, result.output
        assert "// pool window:" not in result.output
        assert "// window: 2026-01-01" in result.output
        assert "// verdict: PASS" in result.output

    def test_seeded_era_window_includes_fixture_and_echoes_label(self, runner, tmp_path):
        """A seeded `entity_eras` `stable_since` matching the fixture's date -> the era-default
        pool includes every fixture deck and the CLI echoes the ledger's own since + label."""
        db_path = _build_discovery_db(tmp_path)
        from legacy_engine.analytics.eras.ensemble import EntityEras
        from legacy_engine.analytics.eras.store import write_entity_eras
        from legacy_engine.ingestion import store

        con = store.connect(db_path)
        write_entity_eras(
            con,
            {"Doomsday": EntityEras(
                entity="Doomsday", stable_since="2026-01-01", boundaries=(),
                inherited_from_parent=False,
            )},
            {}, {},
            run_meta={
                "provenance": None, "alpha": 0.05, "run_at": "2026-07-12T00:00:00+00:00",
                "post_boundary_decks": {}, "parent": {"Doomsday": "Doomsday"},
            },
        )
        con.close()

        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "10",
        ])
        assert result.exit_code == 0, result.output
        assert "// pool window: since 2026-01-01 (" in result.output
        assert "// verdict: PASS" in result.output


# ---------------------------------------------------------------------------
# discover run/list — Gate C temporal-mixing surfacing (Unit 2)
# ---------------------------------------------------------------------------

class TestDiscoverGateCSurfacing:
    def test_run_report_shows_median_dates_and_temporal_mixing_warning(self, runner, tmp_path):
        db_path = _build_two_generation_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        result = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "10", "--all-pool",
        ])
        assert result.exit_code == 0, result.output
        assert "// verdict: PASS" in result.output   # Gate C flags, never fails
        assert "// ⚠ temporal mixing: camps may be list generations" in result.output
        assert "median 2025-06-01" in result.output
        assert "median 2026-05-01" in result.output
        # --all-pool pools the full corpus but %current stays anchored to the entity's ERA
        # since (ban-regime fallback here) — the documented diagnostic (Unit 2 design decision).
        assert "% current" in result.output

    def test_list_renders_the_same_gate_c_fields(self, runner, tmp_path):
        db_path = _build_two_generation_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        run = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "10", "--all-pool",
        ])
        assert run.exit_code == 0, run.output

        result = runner.invoke(main, ["discover", "list", "--discovered-path", staged])
        assert result.exit_code == 0, result.output
        assert "// ⚠ temporal mixing: camps may be list generations" in result.output
        assert "median 2025-06-01" in result.output
        assert "median 2026-05-01" in result.output

    def test_staged_record_persists_gate_c_fields_on_disk(self, runner, tmp_path):
        db_path = _build_two_generation_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        run = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "10", "--all-pool",
        ])
        assert run.exit_code == 0, run.output

        data = json.loads((tmp_path / "discovered.json").read_text())
        split = data["splits"][0]
        assert split["temporal_mixing"] is True
        assert split["temporal_note"] == "camps may be list generations"
        median_dates = {c["median_date"] for c in split["camps"]}
        assert median_dates == {"2025-06-01", "2026-05-01"}

    def test_old_shape_staged_record_still_loads_and_lists(self, runner, tmp_path):
        """A staged record written before this epic (no median_date/pct_current/temporal_mixing
        keys at all) must still load and list cleanly — additive-JSON-keys backward compat."""
        staged = tmp_path / "discovered.json"
        staged.write_text(json.dumps({
            "version": "1",
            "splits": [
                {
                    "parent": "Doomsday",
                    "generated_from": "discover run @ 2026-01-01 (pre-epic)",
                    "params": {"since": None, "reducer": "svd", "seed": 0, "n_boot": 20},
                    "camps": [
                        {
                            "name": "Murktide Regent",
                            "signature_cards": ["Murktide Regent"],
                            "n": 40,
                            "tier": "evolving",
                            "member_keys": [["t1", 0]],
                        },
                        {
                            "name": "non-Murktide Regent",
                            "signature_cards": ["Personal Tutor"],
                            "n": 35,
                            "tier": "evolving",
                            "member_keys": [["t1", 1]],
                        },
                    ],
                    "stability": 0.95,
                    "status": "candidate",
                }
            ],
        }, indent=2))

        result = runner.invoke(main, ["discover", "list", "--discovered-path", str(staged)])
        assert result.exit_code == 0, result.output
        assert "Doomsday" in result.output
        assert "Murktide Regent" in result.output
        # No Gate C fields on the old record -> nothing fabricated, no crash.
        assert "temporal mixing" not in result.output
        assert "median" not in result.output


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
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
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
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
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


# ---------------------------------------------------------------------------
# discover apply
# ---------------------------------------------------------------------------

class TestDiscoverApply:
    def _run_discover(self, runner, tmp_path) -> tuple[str, str]:
        """discover run against the two-camp DB; return (db_path, staged_path)."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        run = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert run.exit_code == 0, run.output
        return db_path, staged

    def test_apply_labels_decks_and_leaves_status_candidate(self, runner, tmp_path):
        db_path, staged = self._run_discover(runner, tmp_path)

        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert result.exit_code == 0, result.output
        assert "// camps:" in result.output
        assert "deck(s) labeled from staged candidate for 'Doomsday'" in result.output
        assert (
            "// STAGED CANDIDATE labels applied to decks.variant — speculative provenance; "
            "not promoted to the curated registry" in result.output
        )

        # Not a promotion: status stays candidate; curated registry untouched.
        data = json.loads((tmp_path / "discovered.json").read_text())
        assert data["splits"][0]["status"] == "candidate"

        listed = runner.invoke(main, ["discover", "list", "--discovered-path", staged])
        assert "[status: candidate]" in listed.output

        # All 70 Doomsday decks resolve (2-camp split: positive rule + default complement).
        import duckdb
        con = duckdb.connect(db_path)
        n_variant = con.execute(
            "SELECT count(*) FROM decks WHERE archetype = 'Doomsday' AND variant IS NOT NULL"
        ).fetchone()[0]
        con.close()
        assert n_variant == 70

    def test_apply_with_no_staged_split_fails_loudly(self, runner, tmp_path):
        db_path = _build_discovery_db(tmp_path)
        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", str(tmp_path / "empty.json"),
        ])
        assert result.exit_code != 0
        assert "no staged candidate split" in result.output

    def test_promote_still_works_after_apply(self, runner, tmp_path):
        db_path, staged = self._run_discover(runner, tmp_path)
        applied = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert applied.exit_code == 0, applied.output

        data = json.loads((tmp_path / "discovered.json").read_text())
        camp = next(
            c["name"] for c in data["splits"][0]["camps"] if not c["name"].startswith("non-")
        )
        registry = _curated_registry(tmp_path)
        promoted = runner.invoke(main, [
            "discover", "promote", "--archetype", "Doomsday", "--variant", camp,
            "--discovered-path", staged, "--registry-path", registry,
        ])
        assert promoted.exit_code == 0, promoted.output

        staged_data = json.loads((tmp_path / "discovered.json").read_text())
        assert staged_data["splits"][0]["status"] == "promoted"

    def test_apply_reports_zero_incremental_candidates_on_a_full_member_fixture(
        self, runner, tmp_path,
    ):
        """Every deck in this fixture is a cluster member, so the incremental pass has nothing
        to consider — the new audit lines are purely additive."""
        db_path, staged = self._run_discover(runner, tmp_path)
        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert result.exit_code == 0, result.output
        assert "// 0 deck(s) incrementally assigned" in result.output
        assert "0 candidate(s) left unlabeled below threshold" in result.output

    def test_min_similarity_help_default_matches_the_engine_constant(self, runner):
        """The shown default is a literal (importing the constant into cli.py would pull numpy
        into every invocation) — pin it to the real constant so it cannot drift."""
        from legacy_engine.analytics.discovery import DEFAULT_MIN_SIMILARITY

        result = runner.invoke(main, ["discover", "apply", "--help"])
        assert result.exit_code == 0, result.output
        assert str(DEFAULT_MIN_SIMILARITY) in result.output

    def test_apply_surfaces_provenance_in_report_matchups(self, runner, tmp_path, monkeypatch):
        """End-to-end: discover run -> discover apply -> report matchups --split-variant shows
        both the camp rows (from decks.variant) and the staged-candidate provenance note."""
        db_path, staged = self._run_discover(runner, tmp_path)
        applied = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert applied.exit_code == 0, applied.output

        # report matchups reads the DEFAULT staging path (no CLI flag) — point it at our tmp
        # staged file so the test stays hermetic (never touches the real project data dir).
        monkeypatch.setattr(
            "legacy_engine.config.DISCOVERED_VARIANTS_PATH", staged,
        )

        result = runner.invoke(main, [
            "report", "matchups", "--db", db_path, "--all-time",
            "--split-variant", "Doomsday",
        ])
        assert result.exit_code == 0, result.output
        assert "// split-variant: Doomsday" in result.output
        assert (
            "// provenance: Doomsday has a STAGED (unpromoted) candidate split — variant "
            "labels may be speculative-provenance" in result.output
        )


# ---------------------------------------------------------------------------
# discover apply — nearest-camp incremental assignment for post-staging decks
# ---------------------------------------------------------------------------

# Post-staging deck indices, outside the clustered pool's 0..69.
CLOSE_IDX, PARTIAL_IDX, FAR_IDX = 100, 101, 102


def _add_post_staging_decks(db_path: str) -> None:
    """Insert three decks AFTER the split was staged (so none is in any member_keys).

    This is the shape a growing corpus produces between discovery runs — the decks that stay
    permanently unlabeled when a re-run fails its stability gate. Their similarity to camp A's
    centroid spans the decision space:

    - ``CLOSE_IDX``   — the camp-A list verbatim; cosine 1.0 (every camp-A fixture deck is
                        identical, so the centroid IS that deck's vector).
    - ``PARTIAL_IDX`` — camp A's first card only; cosine 0.8, above the 0.35 default floor but
                        below a tightened one.
    - ``FAR_IDX``     — shares no flex-band card at all; cosine 0.0, always declined.
    """
    from legacy_engine.ingestion import store

    con = store.connect(db_path)
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", [
        ("t1", CLOSE_IDX, "p", "W", "Doomsday", None),
        ("t1", PARTIAL_IDX, "p", "W", "Doomsday", None),
        ("t1", FAR_IDX, "p", "W", "Doomsday", None),
    ])
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [
        ("t1", CLOSE_IDX, "main", "Core Land", 4),
        ("t1", CLOSE_IDX, "main", "Card A1", 4),
        ("t1", CLOSE_IDX, "main", "Card A2", 3),
        ("t1", PARTIAL_IDX, "main", "Core Land", 4),
        ("t1", PARTIAL_IDX, "main", "Card A1", 4),
        ("t1", FAR_IDX, "main", "Core Land", 4),
        ("t1", FAR_IDX, "main", "Weird Tech", 4),
    ])
    con.close()


class TestDiscoverApplyIncremental:
    def _staged_with_extras(self, runner, tmp_path) -> tuple[str, str]:
        """Stage over the clean 70-deck pool, THEN add the post-staging decks."""
        db_path = _build_discovery_db(tmp_path)
        staged = str(tmp_path / "discovered.json")
        run = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert run.exit_code == 0, run.output
        _add_post_staging_decks(db_path)
        return db_path, staged

    def _variant(self, db_path: str, deck_idx: int) -> str | None:
        import duckdb
        con = duckdb.connect(db_path)
        try:
            return con.execute(
                "SELECT variant FROM decks WHERE tournament_id = 't1' AND deck_idx = ?",
                [deck_idx],
            ).fetchone()[0]
        finally:
            con.close()

    def test_close_post_staging_decks_are_assigned_and_audited(self, runner, tmp_path):
        db_path, staged = self._staged_with_extras(runner, tmp_path)

        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert result.exit_code == 0, result.output
        assert "// 2 deck(s) incrementally assigned (assigned_by=incremental" in result.output
        assert "1 candidate(s) left unlabeled below threshold" in result.output

        camp = self._variant(db_path, CLOSE_IDX)
        assert camp is not None
        assert self._variant(db_path, PARTIAL_IDX) == camp
        assert f"//   camp {camp}: +2" in result.output

        import duckdb
        con = duckdb.connect(db_path)
        rows = con.execute(
            "SELECT deck_idx, parent, camp, assigned_by FROM variant_incremental_assignments "
            "ORDER BY deck_idx"
        ).fetchall()
        con.close()
        assert rows == [
            (CLOSE_IDX, "Doomsday", camp, "incremental"),
            (PARTIAL_IDX, "Doomsday", camp, "incremental"),
        ]

    def test_far_post_staging_deck_stays_unlabeled(self, runner, tmp_path):
        db_path, staged = self._staged_with_extras(runner, tmp_path)
        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert result.exit_code == 0, result.output
        assert self._variant(db_path, FAR_IDX) is None

    def test_no_incremental_suppresses_the_pass_entirely(self, runner, tmp_path):
        db_path, staged = self._staged_with_extras(runner, tmp_path)

        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--no-incremental",
        ])
        assert result.exit_code == 0, result.output
        assert "incrementally assigned" not in result.output
        for idx in (CLOSE_IDX, PARTIAL_IDX, FAR_IDX):
            assert self._variant(db_path, idx) is None

        import duckdb
        con = duckdb.connect(db_path)
        n_tables = con.execute(
            "SELECT count(*) FROM duckdb_tables() "
            "WHERE table_name = 'variant_incremental_assignments'"
        ).fetchone()[0]
        con.close()
        assert n_tables == 0   # the table is never even created

    def test_min_similarity_flag_tightens_the_floor(self, runner, tmp_path):
        """The partial deck (cosine 0.8) clears the 0.35 default but not a 0.9 floor; the
        verbatim camp-A list (cosine 1.0) still clears it."""
        db_path, staged = self._staged_with_extras(runner, tmp_path)

        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--min-similarity", "0.9",
        ])
        assert result.exit_code == 0, result.output
        assert "// 1 deck(s) incrementally assigned" in result.output
        assert "min_similarity=0.9" in result.output
        assert "2 candidate(s) left unlabeled below threshold" in result.output
        assert self._variant(db_path, CLOSE_IDX) is not None
        assert self._variant(db_path, PARTIAL_IDX) is None

    def test_next_passing_run_supersedes_the_incremental_label(self, runner, tmp_path):
        """The full dogfood loop: apply (incremental) -> a later PASSing `discover run` that
        clusters the deck for real -> apply again clears the stale row and the membership label
        stands."""
        db_path, staged = self._staged_with_extras(runner, tmp_path)
        first = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert first.exit_code == 0, first.output
        assert "// 2 deck(s) incrementally assigned" in first.output

        rerun = runner.invoke(main, [
            "discover", "run", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged, "--n-boot", "5", "--all-pool",
        ])
        assert rerun.exit_code == 0, rerun.output
        assert "// verdict: PASS" in rerun.output

        second = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", staged,
        ])
        assert second.exit_code == 0, second.output
        assert (
            "// cleared 2 stale incremental assignment(s) from a prior staged generation"
            in second.output
        )

        import duckdb
        con = duckdb.connect(db_path)
        still_incremental = con.execute(
            "SELECT count(*) FROM variant_incremental_assignments WHERE deck_idx = ?",
            [CLOSE_IDX],
        ).fetchone()[0]
        con.close()
        assert still_incremental == 0                     # now a real cluster member
        assert self._variant(db_path, CLOSE_IDX) is not None

    def test_pre_feature_staged_record_degrades_with_a_named_reason(self, runner, tmp_path):
        """A staged record written before this feature (no flex_cards/centroid keys) — the state
        every real staged split is in until its next `discover run`."""
        db_path = _build_discovery_db(tmp_path)
        staged = tmp_path / "discovered.json"
        staged.write_text(json.dumps({
            "version": "1",
            "splits": [{
                "parent": "Doomsday",
                "generated_from": "discover run @ 2026-01-01 (pre-feature)",
                "params": {},
                "camps": [
                    {"name": "Card A1", "signature_cards": ["Card A1"], "n": 35,
                     "tier": "evolving", "member_keys": [["t1", i] for i in range(35)]},
                    {"name": "non-Card A1", "signature_cards": ["Card B1"], "n": 35,
                     "tier": "evolving", "member_keys": [["t1", i] for i in range(35, 70)]},
                ],
                "stability": 0.95,
                "status": "candidate",
            }],
        }, indent=2))
        _add_post_staging_decks(db_path)

        result = runner.invoke(main, [
            "discover", "apply", "--archetype", "Doomsday",
            "--db", db_path, "--discovered-path", str(staged),
        ])
        assert result.exit_code == 0, result.output
        assert "// incremental assignment skipped:" in result.output
        assert "no frozen flex vocabulary" in result.output
        assert "discover run" in result.output
        assert self._variant(db_path, CLOSE_IDX) is None
