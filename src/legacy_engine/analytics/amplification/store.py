from __future__ import annotations
import json
from .run import AmplificationRun


def init_amplification_schema(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS amplification_runs (run_id VARCHAR PRIMARY KEY, payload JSON NOT NULL)"
    )


def write_amplification_run(con, run: AmplificationRun) -> None:
    init_amplification_schema(con)
    payload = json.dumps(
        run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    existing = con.execute(
        "SELECT payload FROM amplification_runs WHERE run_id=?", [run.run_id]
    ).fetchone()
    if existing and existing[0] != payload:
        raise ValueError("amplification run id collision")
    con.execute(
        "INSERT OR IGNORE INTO amplification_runs VALUES (?, ?)", [run.run_id, payload]
    )


def read_amplification_run(con, run_id: str):
    init_amplification_schema(con)
    row = con.execute(
        "SELECT payload FROM amplification_runs WHERE run_id=?", [run_id]
    ).fetchone()
    return AmplificationRun.model_validate(json.loads(row[0])) if row else None
