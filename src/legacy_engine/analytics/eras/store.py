"""``entity_eras`` — the persisted, explainable era ledger.

There is no separate JSON SSOT for this domain (unlike the collection/cards json-ssot-
rebuildable-duckdb-table instances): the corpus itself, via `series.build_entity_series` +
`detect` + `ensemble.derive_eras`, IS the source of truth this table caches. `eras run`
(`analytics/eras/run.py`) is the sibling of `label`/`discover run` — a full-corpus, offline
labeling pass rerun at refresh — and this module owns exactly its persisted shape:

    init_eras_schema(con)                                     -> idempotent CREATE IF NOT EXISTS
    write_entity_eras(con, eras, attributions, alarms, ...)    -> DROP -> schema -> INSERT
    read_entity_eras(con) -> dict[str, StoredEntityEras]       -> full typed round-trip
    stable_since_map(con) -> dict[str, str | None]             -> the consumption seam

``write_entity_eras`` is a full rebuild every call, never an incremental upsert: BH-FDR is
fleet-wide (`ensemble.derive_eras`), so persisting a partial recompute would silently corrupt the
false-positive control for every OTHER entity's `bh_accepted` flag.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

import duckdb

from legacy_engine.analytics.eras.ensemble import EntityEras

if TYPE_CHECKING:
    from legacy_engine.analytics.eras.attribution import Attribution
    from legacy_engine.analytics.eras.run import AlarmFlag

ENTITY_ERAS_DDL = """
CREATE TABLE IF NOT EXISTS entity_eras (
    entity VARCHAR PRIMARY KEY,
    parent VARCHAR NOT NULL,
    stable_since VARCHAR,
    inherited_from_parent BOOLEAN NOT NULL,
    post_boundary_decks INTEGER NOT NULL,
    boundaries_json VARCHAR NOT NULL,
    alarm_fired BOOLEAN NOT NULL,
    alarm_p_change DOUBLE,
    alarm_note VARCHAR,
    run_provenance VARCHAR,
    run_alpha DOUBLE,
    run_at VARCHAR NOT NULL
)
"""


# ---------------------------------------------------------------------------
# Read-side dataclasses (frozen — a stored era history is an immutable snapshot of one run)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StoredAttribution:
    """Round-tripped mirror of `attribution.Attribution` (kept independent of that module so
    `store.py` never needs to import it at runtime — see the `TYPE_CHECKING` guard above)."""

    kind: str
    card: str | None
    detail: str


@dataclass(frozen=True)
class StoredSignal:
    """Round-tripped mirror of one `detect.CandidateBoundary` folded into a stored boundary."""

    signal: str
    magnitude: float
    pvalue: float
    evidence: str
    trigger_card: str | None


@dataclass(frozen=True)
class StoredBoundary:
    """Round-tripped mirror of one `ensemble.EraBoundary`, with its attribution attached."""

    date: str
    pvalue: float
    bh_accepted: bool
    floor_rejected: bool
    attribution: StoredAttribution | None
    signals: tuple[StoredSignal, ...]


@dataclass(frozen=True)
class StoredEntityEras:
    """One entity's full persisted era history, as read back from `entity_eras`."""

    entity: str
    parent: str
    stable_since: str | None
    inherited_from_parent: bool
    post_boundary_decks: int
    boundaries: tuple[StoredBoundary, ...]
    alarm_fired: bool
    alarm_p_change: float | None
    alarm_note: str | None
    run_provenance: str | None
    run_alpha: float | None
    run_at: str


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def init_eras_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the ``entity_eras`` table if absent (idempotent)."""
    con.execute(ENTITY_ERAS_DDL)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _boundary_to_dict(boundary, attribution: "Attribution | None") -> dict:
    return {
        "date": boundary.date,
        "pvalue": boundary.pvalue,
        "bh_accepted": boundary.bh_accepted,
        "floor_rejected": boundary.floor_rejected,
        "attribution": (
            {"kind": attribution.kind, "card": attribution.card, "detail": attribution.detail}
            if attribution is not None else None
        ),
        "signals": [
            {
                "signal": sig.signal,
                "magnitude": sig.magnitude,
                "pvalue": sig.pvalue,
                "evidence": sig.evidence,
                "trigger_card": sig.trigger_card,
            }
            for sig in boundary.signals
        ],
    }


def _boundary_from_dict(raw: dict) -> StoredBoundary:
    attribution_raw = raw.get("attribution")
    attribution = (
        StoredAttribution(
            kind=attribution_raw["kind"],
            card=attribution_raw.get("card"),
            detail=attribution_raw["detail"],
        )
        if attribution_raw is not None else None
    )
    signals = tuple(
        StoredSignal(
            signal=s["signal"], magnitude=s["magnitude"], pvalue=s["pvalue"],
            evidence=s["evidence"], trigger_card=s.get("trigger_card"),
        )
        for s in raw.get("signals", [])
    )
    return StoredBoundary(
        date=raw["date"],
        pvalue=raw["pvalue"],
        bh_accepted=raw["bh_accepted"],
        floor_rejected=raw["floor_rejected"],
        attribution=attribution,
        signals=signals,
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_entity_eras(
    con: duckdb.DuckDBPyConnection,
    eras: "dict[str, EntityEras]",
    attributions: "Mapping[tuple[str, str], Attribution]",
    alarms: "Mapping[str, AlarmFlag]",
    *,
    run_meta: Mapping[str, object],
) -> None:
    """Persist ``eras`` (json-ssot-rebuildable-duckdb-table's rebuild half: DROP -> schema ->
    INSERT). Idempotent to call repeatedly, but ALWAYS a full replace — `eras run` recomputes the
    whole fleet every time, so a merge/upsert here would silently mix stale and fresh
    `bh_accepted` verdicts.

    ``run_meta`` carries this run's provenance:
      - ``"provenance"``: the ``--provenance`` filter used (``None`` = combined).
      - ``"alpha"``: the BH-FDR alpha used.
      - ``"run_at"``: ISO timestamp of the run.
      - ``"post_boundary_decks"``: ``dict[entity, int]`` — the confidence-tier sample size
        (`eras list` reads this via `confidence.tier_for_sample`).
      - ``"parent"``: ``dict[entity, str]`` — `EntityEras` itself carries no `parent` field
        (that lives on `series.EntitySeries`), so the run pass threads it through here.
    """
    con.execute("DROP TABLE IF EXISTS entity_eras")
    init_eras_schema(con)

    provenance = run_meta.get("provenance")
    alpha = run_meta.get("alpha")
    run_at = run_meta["run_at"]
    post_boundary_decks: Mapping[str, int] = run_meta.get("post_boundary_decks") or {}
    parent_map: Mapping[str, str] = run_meta.get("parent") or {}

    rows = []
    for entity, entity_eras in eras.items():
        boundaries_payload = [
            _boundary_to_dict(b, attributions.get((entity, b.date)))
            for b in entity_eras.boundaries
        ]
        alarm = alarms.get(entity)
        rows.append((
            entity,
            parent_map.get(entity, entity),
            entity_eras.stable_since,
            bool(entity_eras.inherited_from_parent),
            int(post_boundary_decks.get(entity, 0)),
            json.dumps(boundaries_payload),
            alarm is not None,
            alarm.p_change if alarm is not None else None,
            alarm.note if alarm is not None else None,
            provenance,
            alpha,
            run_at,
        ))

    if rows:
        con.executemany(
            """
            INSERT INTO entity_eras (
                entity, parent, stable_since, inherited_from_parent, post_boundary_decks,
                boundaries_json, alarm_fired, alarm_p_change, alarm_note,
                run_provenance, run_alpha, run_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def read_entity_eras(con: duckdb.DuckDBPyConnection) -> dict[str, StoredEntityEras]:
    """Read every persisted entity row, fully deserialized. Empty dict on a fresh/missing table
    (honest-degrade — `eras list`/`explain` render "no era data" rather than crash)."""
    try:
        rows = con.execute(
            """
            SELECT entity, parent, stable_since, inherited_from_parent, post_boundary_decks,
                   boundaries_json, alarm_fired, alarm_p_change, alarm_note,
                   run_provenance, run_alpha, run_at
            FROM entity_eras
            """
        ).fetchall()
    except Exception:
        return {}

    out: dict[str, StoredEntityEras] = {}
    for (
        entity, parent, stable_since, inherited, post_boundary_decks, boundaries_json,
        alarm_fired, alarm_p_change, alarm_note, run_provenance, run_alpha, run_at,
    ) in rows:
        boundaries = tuple(_boundary_from_dict(b) for b in json.loads(boundaries_json))
        out[entity] = StoredEntityEras(
            entity=entity,
            parent=parent,
            stable_since=stable_since,
            inherited_from_parent=bool(inherited),
            post_boundary_decks=int(post_boundary_decks),
            boundaries=boundaries,
            alarm_fired=bool(alarm_fired),
            alarm_p_change=alarm_p_change,
            alarm_note=alarm_note,
            run_provenance=run_provenance,
            run_alpha=run_alpha,
            run_at=run_at,
        )
    return out


def stable_since_map(con: duckdb.DuckDBPyConnection) -> dict[str, str | None]:
    """The consumption seam: ``entity -> stable_since`` (``None`` = full history). A lightweight
    direct query — no `boundaries_json` deserialization — since the adaptive-matrix horizon
    function (`-consumption`) only ever needs the date. Empty dict on a fresh/missing table."""
    try:
        rows = con.execute("SELECT entity, stable_since FROM entity_eras").fetchall()
    except Exception:
        return {}
    return {entity: since for entity, since in rows}
