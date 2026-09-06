"""Held-out source adapter for recurrent-era certification.

Only this module may combine an exact discovery ledger row with the outcome-
free DuckDB projection.  It deliberately selects through the same
``load_outcome_free_corpus`` adapter used by discovery and never opens a
``latest``/status-filtered run.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import duckdb

from legacy_engine.analytics.eras.discovery import DiscoveryBoundary, OutcomeFreeCorpus, load_outcome_free_corpus
from legacy_engine.analytics.eras.discovery_run import DiscoveryRun
from legacy_engine.analytics.eras.discovery_store import read_discovery_run
from legacy_engine.analytics.eras.certification import (
    CertificationCalibration,
    EventPartitionPlan,
    PartitionManifest,
    PartitionedOutcomeFreeCorpus,
    partition_outcome_free_corpus,
)


def _raise_mismatch(field: str, expected: object, actual: object) -> None:
    if expected != actual:
        raise ValueError(f"certification corpus {field} mismatch: expected {expected!r}, got {actual!r}")


def load_certification_corpus(
    con: duckdb.DuckDBPyConnection,
    *,
    discovery_run: DiscoveryRun,
    calibration: CertificationCalibration,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
) -> tuple[OutcomeFreeCorpus, PartitionManifest]:
    """Rebuild and verify the exact certification half for one discovery run.

    The returned corpus contains only the certification role.
    """

    if discovery_run.manifest.partition_role != "discovery":
        raise ValueError("discovery run is not marked partition_role='discovery'")
    expected_plan: EventPartitionPlan = calibration.partition
    _raise_mismatch("partition plan id", expected_plan.plan_id, discovery_run.manifest.partition_plan_id)
    from legacy_engine.analytics.eras.certification import _partition_rule_sha256

    _raise_mismatch("partition rule", _partition_rule_sha256(expected_plan), discovery_run.manifest.partition_rule_sha256)
    _raise_mismatch("as_of", as_of, discovery_run.manifest.as_of)
    _raise_mismatch("taxonomy_version", taxonomy_version, discovery_run.manifest.taxonomy_version)
    _raise_mismatch("legality_version", legality_version, discovery_run.manifest.legality_version)
    normalized_provenance = provenance.strip() if provenance is not None else None
    normalized_provenance = normalized_provenance or None
    _raise_mismatch("provenance_filter", normalized_provenance, discovery_run.manifest.provenance_filter)

    full = load_outcome_free_corpus(
        con,
        as_of=as_of,
        taxonomy_version=taxonomy_version,
        legality_version=legality_version,
        semantic_boundaries=semantic_boundaries,
        provenance=normalized_provenance,
    )
    boundaries_payload = [boundary.model_dump(mode="json") for boundary in full.semantic_boundaries]
    from legacy_engine.analytics.eras.discovery import payload_sha256

    _raise_mismatch("semantic_boundaries_sha256", payload_sha256(boundaries_payload),
                    discovery_run.manifest.semantic_boundaries_sha256)
    partitioned: PartitionedOutcomeFreeCorpus = partition_outcome_free_corpus(full, expected_plan)
    _raise_mismatch("source_sha256", partitioned.discovery.source_sha256, discovery_run.manifest.source_sha256)
    _raise_mismatch("partition event ids", partitioned.manifest.discovery_event_ids_sha256,
                    discovery_run.manifest.partition_event_ids_sha256)
    _raise_mismatch("partition manifest", partitioned.manifest.plan_id, discovery_run.manifest.partition_plan_id)
    # Re-validate immutable output, rather than trusting a caller's in-memory
    # object.  The run store performs the same hashes on reads.
    _raise_mismatch("discovery run id", payload_sha256(discovery_run.manifest.model_dump(mode="json")),
                    discovery_run.run_id)
    _raise_mismatch(
        "discovery results hash",
        payload_sha256([result.model_dump(mode="json") for result in discovery_run.results]),
        discovery_run.results_sha256,
    )
    return partitioned.certification, partitioned.manifest


def load_certification_corpus_by_id(
    con: duckdb.DuckDBPyConnection,
    *,
    discovery_run_id: str,
    calibration: CertificationCalibration,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
) -> tuple[OutcomeFreeCorpus, PartitionManifest]:
    """Exact-id convenience adapter; absence is an explicit refusal."""

    run = read_discovery_run(con, discovery_run_id)
    if run is None:
        raise ValueError(f"discovery run {discovery_run_id!r} not found")
    return load_certification_corpus(
        con,
        discovery_run=run,
        calibration=calibration,
        as_of=as_of,
        taxonomy_version=taxonomy_version,
        legality_version=legality_version,
        semantic_boundaries=semantic_boundaries,
        provenance=provenance,
    )


__all__ = ["load_certification_corpus", "load_certification_corpus_by_id", "partition_outcome_free_corpus"]
