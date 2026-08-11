from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from legacy_engine.ingestion import store
from legacy_engine.workflows.player_effect_diagnostic import (
    load_player_diagnostic_rows,
    load_player_identity_snapshot,
)


def _snapshot(path: Path, *, effective_at: str = "2025-12-01") -> Path:
    path.mkdir()
    aliases = path / "aliases.json"
    aliases.write_text(json.dumps({
        "players": {"curated": {"handles": ["Online Name", "Paper Name"]}},
    }))
    (path / "manifest.json").write_text(json.dumps({
        "source": "fixture", "effective_at": effective_at, "aliases_file": "aliases.json",
        "aliases_sha256": hashlib.sha256(aliases.read_bytes()).hexdigest(),
    }))
    return path


def _db(path: Path) -> Path:
    con = store.connect(path)
    store.init_schema(con)
    con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)", [
        ("online", "Online", "2025-12-10", "u", "Legacy", "fixture", "online"),
        ("paper", "Paper", "2025-12-11", "u", "Legacy", "fixture", "paper"),
    ])
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", [
        ("online", 0, "Online Name", "1", "A", "one"),
        ("online", 1, "duplicate", "2", "B", None),
        ("online", 2, "duplicate", "3", "C", None),
        ("paper", 0, "Paper Name", "1", "A", "two"),
        ("paper", 1, "", "2", "B", None),
    ])
    con.executemany("INSERT INTO rounds VALUES (?, ?, ?, ?, ?)", [
        ("online", 0, "Online Name", "duplicate", "2-0"),
        ("paper", 0, "Paper Name", "", "2-1"),
    ])
    con.close()
    return path


def test_identity_snapshot_is_dated_hashed_and_mode_strict(tmp_path):
    snapshot = _snapshot(tmp_path / "identity")
    aliases, digest = load_player_identity_snapshot(
        snapshot, mode="dated-curated-alias", cutoff="2026-01-01",
    )
    assert aliases == {"online name": "curated", "paper name": "curated"}
    assert digest is not None
    with pytest.raises(ValueError, match="does not accept"):
        load_player_identity_snapshot(
            snapshot, mode="provenance-local-handle", cutoff="2026-01-01",
        )
    future = _snapshot(tmp_path / "future", effective_at="2026-02-01")
    with pytest.raises(ValueError, match="later than"):
        load_player_identity_snapshot(future, mode="dated-curated-alias", cutoff="2026-01-01")
    (snapshot / "aliases.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_player_identity_snapshot(snapshot, mode="dated-curated-alias", cutoff="2026-01-01")


def test_workflow_reconciles_blank_duplicate_alias_and_provenance(tmp_path):
    db = _db(tmp_path / "players.duckdb")
    local_regs, local_matches, identity_hash = load_player_diagnostic_rows(
        db, until="2026-01-01", identity_mode="provenance-local-handle",
        identity_snapshot=None,
    )
    assert identity_hash is None
    assert len(local_regs) == 5
    assert sum(row.exclusion_reason == "ambiguous-within-event-handle" for row in local_regs) == 2
    assert sum(row.exclusion_reason == "blank-handle" for row in local_regs) == 1
    online = next(row for row in local_regs if row.player_key == "handle:online:online name")
    paper = next(row for row in local_regs if row.player_key == "handle:paper:paper name")
    assert online.player_key != paper.player_key
    assert len(local_matches) == 1
    assert all(row.opponent_player_key is None for row in local_matches)

    aliased_regs, _, digest = load_player_diagnostic_rows(
        db, until="2026-01-01", identity_mode="dated-curated-alias",
        identity_snapshot=_snapshot(tmp_path / "snapshot"),
    )
    assert digest is not None
    assert {
        row.player_key for row in aliased_regs if row.player_key == "alias:curated"
    } == {"alias:curated"}
    assert {row.configuration for row in aliased_regs if row.parent == "A"} == {
        "A::one", "A::two",
    }
