"""Composition root for immutable recurrent discovery runs."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Literal

import duckdb
from pydantic import field_validator, model_validator

from legacy_engine.analytics.eras.discovery import (
    DiscoveryBoundary,
    DiscoveryCalibration,
    DiscoveryReason,
    EntityDiscoveryResult,
    OutcomeFreeModel,
    OutcomeFreeCorpus,
    canonical_json,
    discover_recurrent_states,
    load_outcome_free_corpus,
    payload_sha256,
)

DiscoveryRunStatus = Literal["complete", "degraded"]
DiscoveryRunReason = Literal["no-eligible-parent-archetypes"]

# Closed, typed feature paths.  The tuple is intentionally not caller
# extensible: changing the admissible evidence is a new run contract.
DISCOVERY_FEATURE_ALLOWLIST = (
    "deck.mainboard",
    "deck.parent_archetype",
    "deck.pilot_key",
    "deck.sideboard",
    "event.date",
    "event.provenance",
    "event.source",
    "legality.version",
    "semantic.boundaries",
    "taxonomy.version",
)


class DiscoveryManifest(OutcomeFreeModel):
    method_id: str
    calibration_id: str
    calibration_sha256: str
    as_of: date
    taxonomy_version: str
    legality_version: str
    provenance_filter: str | None
    semantic_boundaries_sha256: str
    source_sha256: str
    feature_allowlist: tuple[str, ...]
    seed: int

    @field_validator(
        "method_id", "calibration_id", "calibration_sha256", "taxonomy_version",
        "legality_version", "semantic_boundaries_sha256", "source_sha256",
    )
    @classmethod
    def _nonempty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("manifest value must be non-empty")
        return value

    @field_validator("provenance_filter")
    @classmethod
    def _manifest_provenance(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def _closed_contract(self) -> "DiscoveryManifest":
        if self.feature_allowlist != DISCOVERY_FEATURE_ALLOWLIST:
            raise ValueError("feature_allowlist must equal the shipped discovery allowlist")
        digest_fields = {
            "calibration_sha256": self.calibration_sha256,
            "semantic_boundaries_sha256": self.semantic_boundaries_sha256,
            "source_sha256": self.source_sha256,
        }
        for key, value in digest_fields.items():
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError(f"{key} must be a lowercase SHA-256 hex digest")
        return self


class DiscoveryRun(OutcomeFreeModel):
    run_id: str
    manifest: DiscoveryManifest
    results_sha256: str
    status: DiscoveryRunStatus
    reasons: tuple[DiscoveryRunReason, ...]
    results: tuple[EntityDiscoveryResult, ...]


def build_discovery_manifest(
    corpus: OutcomeFreeCorpus,
    calibration: DiscoveryCalibration,
    *,
    seed: int,
) -> DiscoveryManifest:
    boundaries_payload = [boundary.model_dump(mode="json") for boundary in corpus.semantic_boundaries]
    calibration_payload = calibration.model_dump(mode="json")
    return DiscoveryManifest(
        method_id=calibration.method_id,
        calibration_id=calibration.calibration_id,
        calibration_sha256=payload_sha256(calibration_payload),
        as_of=corpus.as_of,
        taxonomy_version=corpus.taxonomy_version,
        legality_version=corpus.legality_version,
        provenance_filter=corpus.provenance_filter,
        semantic_boundaries_sha256=payload_sha256(boundaries_payload),
        source_sha256=corpus.source_sha256,
        feature_allowlist=DISCOVERY_FEATURE_ALLOWLIST,
        seed=seed,
    )


def run_recurrent_discovery(
    con: duckdb.DuckDBPyConnection,
    *,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    calibration: DiscoveryCalibration,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
    seed: int = 0,
) -> DiscoveryRun:
    """Build and persist one outcome-free discovery run.

    The source connection is used only to construct the frozen corpus.  The
    pure engine receives no connection and all persisted output is self-
    contained, allowing certification to consume an exact run id later.
    """

    corpus = load_outcome_free_corpus(
        con,
        as_of=as_of,
        taxonomy_version=taxonomy_version,
        legality_version=legality_version,
        semantic_boundaries=semantic_boundaries,
        provenance=provenance,
    )
    manifest = build_discovery_manifest(corpus, calibration, seed=seed)
    results = discover_recurrent_states(corpus, calibration, seed=seed)
    eligible = {
        deck.parent_archetype
        for deck in corpus.decks
        if deck.parent_archetype.strip().casefold() != "unknown"
        and not deck.parent_archetype.strip().casefold().startswith("conflict(")
        and sum(item.parent_archetype == deck.parent_archetype for item in corpus.decks)
        >= calibration.min_subject_decks
    }
    reasons: tuple[DiscoveryRunReason, ...] = () if eligible else ("no-eligible-parent-archetypes",)
    status: DiscoveryRunStatus = "complete" if eligible else "degraded"
    results_payload = [result.model_dump(mode="json") for result in results]
    results_sha256 = payload_sha256(results_payload)
    run_id = payload_sha256(manifest.model_dump(mode="json"))
    run = DiscoveryRun(
        run_id=run_id,
        manifest=manifest,
        results_sha256=results_sha256,
        status=status,
        reasons=reasons,
        results=results,
    )
    # Local import keeps the composition root independent of the storage
    # implementation and avoids a module cycle.
    from legacy_engine.analytics.eras.discovery_store import init_discovery_schema, write_discovery_run

    init_discovery_schema(con)
    write_discovery_run(con, run)
    return run


__all__ = [
    "DISCOVERY_FEATURE_ALLOWLIST",
    "DiscoveryManifest",
    "DiscoveryRun",
    "build_discovery_manifest",
    "run_recurrent_discovery",
]
