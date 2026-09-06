"""Immutable DuckDB ledger for content-addressed discovery runs."""

from __future__ import annotations

import json
from datetime import date

import duckdb

from legacy_engine.analytics.eras.discovery import canonical_json, payload_sha256
from legacy_engine.analytics.eras.discovery_run import DiscoveryRun

DISCOVERY_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS era_discovery_runs (
    run_id VARCHAR PRIMARY KEY,
    as_of DATE NOT NULL,
    method_id VARCHAR NOT NULL,
    calibration_id VARCHAR NOT NULL,
    source_sha256 VARCHAR NOT NULL,
    manifest_json VARCHAR NOT NULL,
    results_json VARCHAR NOT NULL,
    results_sha256 VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    reasons_json VARCHAR NOT NULL
)
"""


def init_discovery_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(DISCOVERY_RUNS_DDL)


def _payloads(run: DiscoveryRun) -> tuple[str, str]:
    manifest_json = canonical_json(run.manifest)
    results_json = canonical_json([result.model_dump(mode="json") for result in run.results])
    if payload_sha256(json.loads(results_json)) != run.results_sha256:
        raise ValueError(f"discovery run {run.run_id} has an invalid results_sha256")
    if payload_sha256(json.loads(manifest_json)) != run.run_id:
        raise ValueError(f"discovery run {run.run_id} does not match its manifest digest")
    return manifest_json, results_json


def write_discovery_run(con: duckdb.DuckDBPyConnection, run: DiscoveryRun) -> None:
    """Insert an immutable run, accepting exact-byte retries only."""

    manifest_json, results_json = _payloads(run)
    init_discovery_schema(con)
    existing = con.execute(
        "SELECT manifest_json, results_json, results_sha256, status, reasons_json FROM era_discovery_runs WHERE run_id = ?",
        [run.run_id],
    ).fetchone()
    reasons_json = canonical_json(list(run.reasons))
    if existing is not None:
        expected = (manifest_json, results_json, run.results_sha256, run.status, reasons_json)
        if tuple(existing) != expected:
            raise ValueError(f"immutable discovery run collision for run_id {run.run_id}")
        return
    try:
        con.execute("BEGIN")
        con.execute(
            """
            INSERT INTO era_discovery_runs (
                run_id, as_of, method_id, calibration_id, source_sha256,
                manifest_json, results_json, results_sha256, status, reasons_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run.run_id,
                run.manifest.as_of,
                run.manifest.method_id,
                run.manifest.calibration_id,
                run.manifest.source_sha256,
                manifest_json,
                results_json,
                run.results_sha256,
                run.status,
                reasons_json,
            ],
        )
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except duckdb.Error:
            pass
        raise


def read_discovery_run(con: duckdb.DuckDBPyConnection, run_id: str) -> DiscoveryRun | None:
    """Read by exact content id; an absent table/run degrades to ``None``."""

    try:
        row = con.execute(
            "SELECT run_id, manifest_json, results_json, results_sha256, status, reasons_json FROM era_discovery_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
    except duckdb.CatalogException:
        return None
    if row is None:
        return None
    stored_run_id, manifest_json, results_json, results_sha256, status, reasons_json = row
    try:
        manifest_payload = json.loads(manifest_json)
        results_payload = json.loads(results_json)
        reasons_payload = json.loads(reasons_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid discovery ledger JSON for run_id {run_id}") from exc
    if (
        canonical_json(manifest_payload) != manifest_json
        or canonical_json(results_payload) != results_json
        or canonical_json(reasons_payload) != reasons_json
    ):
        raise ValueError(f"noncanonical discovery ledger JSON for run_id {run_id}")
    if payload_sha256(manifest_payload) != stored_run_id or payload_sha256(results_payload) != results_sha256:
        raise ValueError(f"discovery ledger hash mismatch for run_id {run_id}")
    return DiscoveryRun.model_validate({
        "run_id": stored_run_id,
        "manifest": manifest_payload,
        "results_sha256": results_sha256,
        "status": status,
        "reasons": reasons_payload,
        "results": results_payload,
    })


def discovery_run_ids(con: duckdb.DuckDBPyConnection, *, as_of: date | None = None) -> tuple[str, ...]:
    try:
        if as_of is None:
            rows = con.execute("SELECT run_id FROM era_discovery_runs ORDER BY run_id").fetchall()
        else:
            rows = con.execute("SELECT run_id FROM era_discovery_runs WHERE as_of = ? ORDER BY run_id", [as_of]).fetchall()
    except duckdb.CatalogException:
        return ()
    return tuple(row[0] for row in rows)


__all__ = ["DISCOVERY_RUNS_DDL", "init_discovery_schema", "write_discovery_run", "read_discovery_run", "discovery_run_ids"]
