"""Immutable DuckDB JSON ledger for recurrent-era certification runs."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import duckdb

from legacy_engine.analytics.eras.certification import payload_sha256
from legacy_engine.analytics.eras.certification_run import CertificationRun, certification_run_identity
from legacy_engine.analytics.eras.discovery import canonical_json

CERTIFICATION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS era_certification_runs (
    run_id VARCHAR PRIMARY KEY,
    as_of DATE NOT NULL,
    discovery_run_id VARCHAR NOT NULL,
    calibration_profile_id VARCHAR NOT NULL,
    manifest_json VARCHAR NOT NULL,
    results_json VARCHAR NOT NULL,
    results_sha256 VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    reasons_json VARCHAR NOT NULL,
    knowledge_available_at VARCHAR NOT NULL
)
"""


def init_certificate_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(CERTIFICATION_RUNS_DDL)


def _payloads(run: CertificationRun) -> tuple[str, str, str]:
    manifest_json = canonical_json(run.manifest)
    results_json = canonical_json([result.model_dump(mode="json") for result in run.results])
    reasons_json = canonical_json(list(run.reasons))
    expected_id = certification_run_identity(run.manifest, run.status, run.reasons)
    if expected_id != run.run_id:
        raise ValueError(f"certification run {run.run_id} does not match its manifest digest")
    if payload_sha256(json.loads(results_json)) != run.results_sha256:
        raise ValueError(f"certification run {run.run_id} has an invalid results_sha256")
    return manifest_json, results_json, reasons_json


def write_certification_run(con: duckdb.DuckDBPyConnection, run: CertificationRun) -> None:
    """Insert an immutable run; exact-byte retries are idempotent."""

    manifest_json, results_json, reasons_json = _payloads(run)
    knowledge_available_at = run.knowledge_available_at or datetime.now(UTC)
    knowledge_text = knowledge_available_at.astimezone(UTC).isoformat()
    init_certificate_schema(con)
    try:
        existing = con.execute(
            "SELECT manifest_json, results_json, results_sha256, status, reasons_json, knowledge_available_at FROM era_certification_runs WHERE run_id = ?",
            [run.run_id],
        ).fetchone()
    except duckdb.CatalogException:
        existing = None
    if existing is not None:
        expected_without_knowledge = (manifest_json, results_json, run.results_sha256, run.status, reasons_json)
        if tuple(existing[:5]) != expected_without_knowledge:
            raise ValueError(f"immutable certification run collision for run_id {run.run_id}")
        if run.knowledge_available_at is not None and existing[5] != knowledge_text:
            raise ValueError(f"immutable certification knowledge timestamp collision for run_id {run.run_id}")
        return
    try:
        con.execute("BEGIN")
        con.execute(
            """
            INSERT INTO era_certification_runs (
                run_id, as_of, discovery_run_id, calibration_profile_id,
                manifest_json, results_json, results_sha256, status, reasons_json, knowledge_available_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [run.run_id, run.manifest.certification_as_of, run.manifest.discovery_run_id,
             run.manifest.calibration_profile_id, manifest_json, results_json,
             run.results_sha256, run.status, reasons_json, knowledge_text],
        )
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except duckdb.Error:
            pass
        raise


def read_certification_run(con: duckdb.DuckDBPyConnection, run_id: str) -> CertificationRun | None:
    """Read by exact immutable id; absent tables/runs return ``None``."""

    try:
        row = con.execute(
            "SELECT run_id, manifest_json, results_json, results_sha256, status, reasons_json, knowledge_available_at FROM era_certification_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
    except duckdb.CatalogException:
        return None
    if row is None:
        return None
    stored_id, manifest_json, results_json, results_sha256, status, reasons_json, knowledge_text = row
    try:
        manifest_payload = json.loads(manifest_json)
        results_payload = json.loads(results_json)
        reasons_payload = json.loads(reasons_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid certification ledger JSON for run_id {run_id}") from exc
    if (
        canonical_json(manifest_payload) != manifest_json
        or canonical_json(results_payload) != results_json
        or canonical_json(reasons_payload) != reasons_json
    ):
        raise ValueError(f"noncanonical certification ledger JSON for run_id {run_id}")
    from legacy_engine.analytics.eras.certification_run import CertificationManifest
    if certification_run_identity(
        CertificationManifest.model_validate(manifest_payload), status, tuple(reasons_payload),
    ) != stored_id or payload_sha256(results_payload) != results_sha256:
        raise ValueError(f"certification ledger hash mismatch for run_id {run_id}")
    return CertificationRun.model_validate({
        "run_id": stored_id, "manifest": manifest_payload, "results_sha256": results_sha256,
        "status": status, "reasons": reasons_payload, "results": results_payload,
        "knowledge_available_at": knowledge_text,
    })


def certification_run_ids(con: duckdb.DuckDBPyConnection, *, as_of: date | None = None) -> tuple[str, ...]:
    try:
        if as_of is None:
            rows = con.execute("SELECT run_id FROM era_certification_runs ORDER BY run_id").fetchall()
        else:
            rows = con.execute("SELECT run_id FROM era_certification_runs WHERE as_of = ? ORDER BY run_id", [as_of]).fetchall()
    except duckdb.CatalogException:
        return ()
    return tuple(row[0] for row in rows)


__all__ = [
    "CERTIFICATION_RUNS_DDL", "init_certificate_schema", "write_certification_run",
    "read_certification_run", "certification_run_ids",
]
