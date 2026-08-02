"""Superarchetype registry — curated merge, persistence, stable identity, churn.

Three patterns meet here:

- **curated-json-resource-loader**: ``load_curated_superarchetypes(path)`` is standalone,
  path-taking, and fails fast citing the offending path and key; ``_load_default_curated()``
  resolves the config path and degrades to ``{}`` so an absent or mis-edited curated file no-ops
  instead of crashing import.
- **hybrid-derived-curated-registry**: ``merge_curated`` — curated clusters win their id and label
  outright, curated membership wins by archetype key, and every override records the derived
  assignment it replaced so the divergence stays auditable.
- **json-ssot-rebuildable-duckdb-table**: ``DERIVED_SUPERARCHETYPES_PATH`` is the source of truth;
  ``superarchetype_members``/``superarchetype_meta`` are derived caches rebuilt DROP -> schema ->
  INSERT on every run, and the consumption seam the matrix layer will read.

Cluster **identity** is stable across refreshes by max-overlap matching against the previous
registry; **membership** is recomputed per window and the difference is surfaced as a churn
diagnostic (brief §9: measured ~0.96 co-membership agreement window-over-window, so a materially
lower figure is itself the alarm).

This module writes and reads only its own tables. It never reads corpus rows.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from legacy_engine.analytics.superarchetype.cluster import (
    ClusterMember,
    ClusterSolution,
    cluster_archetypes,
    load_archetype_decks,
)

log = logging.getLogger(__name__)

__all__ = [
    "CURATED_SUPERARCHETYPES",
    "ChurnReport",
    "CuratedCluster",
    "RegistryCluster",
    "RunResult",
    "SuperarchetypeRegistry",
    "init_superarchetype_schema",
    "load_curated_superarchetypes",
    "match_identities",
    "membership_churn",
    "merge_curated",
    "read_derived_registry",
    "read_superarchetype_members",
    "rebuild_superarchetype_members",
    "run_superarchetypes",
    "write_derived_registry",
]

_ID_PREFIX = "sa-"
_CHURN_BASELINE = 0.96
"""Measured window-over-window co-membership agreement (brief §9). A materially lower run figure is
the alarm, not a reason to re-derive."""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CuratedCluster:
    """One hand-authored cluster from the shipped curated registry."""

    id: str
    label: str
    archetypes: tuple[str, ...]


@dataclass(frozen=True)
class RegistryCluster:
    """One cluster as persisted: a stable id, a display label, and its members with provenance."""

    id: str
    label: str
    members: tuple[ClusterMember, ...]
    au: float | None
    height: float | None
    bp_at_unit_scale: float | None
    curated: bool

    @property
    def archetypes(self) -> tuple[str, ...]:
        return tuple(m.archetype for m in self.members)


@dataclass(frozen=True)
class SuperarchetypeRegistry:
    """The full persisted taxonomy for one derivation window."""

    clusters: tuple[RegistryCluster, ...]
    staples: tuple[str, ...]
    unassigned: tuple[tuple[str, str], ...]
    window_since: str | None
    window_until: str | None
    derived_at: str
    stability: float
    cophenetic: float
    degraded: bool
    reasons: tuple[str, ...]
    seed: int
    n_boot: int
    window_policy: str = "global"
    entity_horizons: tuple[tuple[str, str | None, str], ...] = ()
    audit_lines: tuple[str, ...] = ()

    def cluster_of(self, archetype: str) -> RegistryCluster | None:
        """The cluster an archetype belongs to, or ``None`` when it is unassigned."""
        for cluster in self.clusters:
            if archetype in cluster.archetypes:
                return cluster
        return None


@dataclass(frozen=True)
class ChurnReport:
    """Membership movement between two refreshes (brief §9 — a diagnostic, never a silent number)."""

    comparable: int
    agreement: float | None
    moves: tuple[tuple[str, str, str], ...]
    arrivals: tuple[str, ...]
    departures: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class RunResult:
    """One ``superarchetype run`` pass — returned so the CLI renders without a second read."""

    registry: SuperarchetypeRegistry
    solution: ClusterSolution
    churn: ChurnReport
    remap: tuple[str, ...]
    n_archetypes: int
    n_definers: int
    definer_field_share: float
    assigned_field_share: float
    written: bool


# ---------------------------------------------------------------------------
# Curated loader (curated-json-resource-loader)
# ---------------------------------------------------------------------------


def load_curated_superarchetypes(path: Path | str) -> dict[str, CuratedCluster]:
    """Load + validate the curated cluster registry. Raises ``ValueError`` citing path and key.

    Schema::

        {"version": 1, "clusters": [{"id": "sa-cheat", "label": "...", "archetypes": ["A", "B"]}]}

    Fails fast on a missing/blank ``id`` or ``label``, an empty or non-list ``archetypes``, a
    duplicate cluster id, or an archetype claimed by two clusters — all author errors that would
    otherwise produce a silently half-applied override.

    Shape errors raise ``ValueError`` rather than ``TypeError`` (hence the ``TRY004`` suppressions):
    the caller's fault is a mis-edited data FILE, not a wrong argument type, and every other curated
    loader in the project reports the same way (curated-json-resource-loader).
    """
    path = Path(path)
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(  # noqa: TRY004
            f"load_curated_superarchetypes: {path} must hold a JSON object"
        )

    entries = raw.get("clusters", [])
    if not isinstance(entries, list):
        raise ValueError(  # noqa: TRY004
            f"load_curated_superarchetypes: 'clusters' must be a list in {path}"
        )

    out: dict[str, CuratedCluster] = {}
    claimed: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(  # noqa: TRY004
                f"load_curated_superarchetypes: clusters[{index}] must be an object in {path}"
            )
        cluster_id = str(entry.get("id", "")).strip()
        label = str(entry.get("label", "")).strip()
        if not cluster_id:
            raise ValueError(
                f"load_curated_superarchetypes: clusters[{index}] has no 'id' in {path}"
            )
        if not label:
            raise ValueError(
                f"load_curated_superarchetypes: cluster {cluster_id!r} has no 'label' in {path}"
            )
        if cluster_id in out:
            raise ValueError(
                f"load_curated_superarchetypes: duplicate cluster id {cluster_id!r} in {path}"
            )
        archetypes = entry.get("archetypes")
        if not isinstance(archetypes, list) or not archetypes:
            raise ValueError(
                f"load_curated_superarchetypes: cluster {cluster_id!r} needs a non-empty "
                f"'archetypes' list in {path}"
            )
        names: list[str] = []
        for archetype in archetypes:
            name = str(archetype).strip()
            if not name:
                raise ValueError(
                    f"load_curated_superarchetypes: cluster {cluster_id!r} has a blank archetype "
                    f"name in {path}"
                )
            if name in claimed:
                raise ValueError(
                    f"load_curated_superarchetypes: archetype {name!r} is claimed by both "
                    f"{claimed[name]!r} and {cluster_id!r} in {path}"
                )
            claimed[name] = cluster_id
            names.append(name)
        out[cluster_id] = CuratedCluster(
            id=cluster_id, label=label, archetypes=tuple(sorted(names))
        )
    return out


def _load_default_curated() -> dict[str, CuratedCluster]:
    """Resolve the shipped curated path, degrading to ``{}`` on any error (gated-additive)."""
    try:
        from legacy_engine.config import SUPERARCHETYPES_REGISTRY_PATH

        return load_curated_superarchetypes(SUPERARCHETYPES_REGISTRY_PATH)
    except Exception as exc:  # noqa: BLE001 — a broken curated file must never crash import
        log.error("superarchetype: failed to load curated registry — returning empty: %s", exc)
        return {}


CURATED_SUPERARCHETYPES: dict[str, CuratedCluster] = _load_default_curated()


# ---------------------------------------------------------------------------
# Merge (hybrid-derived-curated-registry)
# ---------------------------------------------------------------------------


def merge_curated(
    solution: ClusterSolution,
    curated: Mapping[str, CuratedCluster],
    *,
    deck_counts: Mapping[str, int],
    window_since: str | None,
    window_until: str | None,
    derived_at: str,
    window_policy: str = "global",
    entity_horizons: tuple[tuple[str, str | None, str], ...] = (),
    audit_lines: tuple[str, ...] = (),
) -> SuperarchetypeRegistry:
    """Merge curated clusters over the derived solution — curated wins by key.

    A curated cluster keeps its own id and label. Every archetype it names is pulled out of whatever
    derived cluster held it, stamped ``provenance="curated"``, and carries a note recording the
    derived assignment it replaced. A derived cluster emptied by overrides is dropped with a reason.
    Derived clusters enter with an empty id — ``match_identities`` assigns stable ids.
    """
    claimed_by: dict[str, str] = {
        archetype: cluster.id
        for cluster in curated.values()
        for archetype in cluster.archetypes
    }
    derived_home: dict[str, str] = {
        member.archetype: cluster.label
        for cluster in solution.clusters
        for member in cluster.members
    }
    reasons = list(solution.reasons)

    clusters: list[RegistryCluster] = []
    for cluster_id in sorted(curated):
        entry = curated[cluster_id]
        members = tuple(
            ClusterMember(
                archetype=archetype,
                provenance="curated",
                n_decks=int(deck_counts.get(archetype, 0)),
                note=(
                    "curated override; derived assignment was "
                    f"{derived_home.get(archetype, '(unassigned)')}"
                ),
            )
            for archetype in entry.archetypes
        )
        clusters.append(RegistryCluster(
            id=entry.id, label=entry.label, members=members,
            au=None, height=None, bp_at_unit_scale=None, curated=True,
        ))
        reasons.append(
            f"curated cluster {entry.id!r} ({entry.label!r}) wins by key over the derived "
            f"assignment for {len(entry.archetypes)} archetype(s)"
        )

    for cluster in solution.clusters:
        kept = tuple(m for m in cluster.members if m.archetype not in claimed_by)
        if not kept:
            reasons.append(
                f"derived cluster {cluster.label!r} dropped: every member claimed by a curated "
                "cluster"
            )
            continue
        clusters.append(RegistryCluster(
            id="", label=cluster.label, members=kept,
            au=cluster.au, height=cluster.height,
            bp_at_unit_scale=cluster.bp_at_unit_scale, curated=False,
        ))

    unassigned = tuple(
        (archetype, reason)
        for archetype, reason in solution.unassigned
        if archetype not in claimed_by
    )

    return SuperarchetypeRegistry(
        clusters=tuple(clusters),
        staples=solution.staples,
        unassigned=unassigned,
        window_since=window_since,
        window_until=window_until,
        derived_at=derived_at,
        stability=solution.stability,
        cophenetic=solution.cophenetic,
        degraded=solution.degraded,
        reasons=tuple(reasons),
        seed=solution.seed,
        n_boot=solution.n_boot,
        window_policy=window_policy,
        entity_horizons=entity_horizons,
        audit_lines=audit_lines,
    )


# ---------------------------------------------------------------------------
# Stable identity across refreshes
# ---------------------------------------------------------------------------


def _next_id(taken: set[str]) -> str:
    used = {
        int(cluster_id[len(_ID_PREFIX):])
        for cluster_id in taken
        if cluster_id.startswith(_ID_PREFIX) and cluster_id[len(_ID_PREFIX):].isdigit()
    }
    return f"{_ID_PREFIX}{(max(used) + 1) if used else 1:03d}"


def match_identities(
    new: SuperarchetypeRegistry,
    previous: SuperarchetypeRegistry | None,
) -> tuple[SuperarchetypeRegistry, tuple[str, ...]]:
    """Give every derived cluster a stable id by max-overlap matching against ``previous``.

    Greedy by descending overlap, one previous id to at most one new cluster. Curated clusters own
    their ids outright and are never remapped. An unmatched cluster mints a fresh ``sa-<nnn>``. The
    mapping decisions are returned as audit lines rather than applied silently — a greedy match can
    hand an id to the wrong half of a split, and the fix for that is a curated entry.
    """
    notes: list[str] = []
    taken: set[str] = {c.id for c in new.clusters if c.id}
    previous_members: dict[str, set[str]] = (
        {c.id: set(c.archetypes) for c in previous.clusters} if previous is not None else {}
    )
    taken |= set(previous_members)

    pending = [(idx, c) for idx, c in enumerate(new.clusters) if not c.id]
    candidates: list[tuple[int, int, str]] = []
    for idx, cluster in pending:
        members = set(cluster.archetypes)
        for previous_id, previous_set in previous_members.items():
            overlap = len(members & previous_set)
            if overlap:
                candidates.append((-overlap, idx, previous_id))
    candidates.sort()

    assigned: dict[int, str] = {}
    used_previous: set[str] = set()
    for negative_overlap, idx, previous_id in candidates:
        if idx in assigned or previous_id in used_previous:
            continue
        assigned[idx] = previous_id
        used_previous.add(previous_id)
        moved = set(new.clusters[idx].archetypes) ^ previous_members[previous_id]
        if moved:
            notes.append(
                f"{previous_id}: kept identity (overlap {-negative_overlap}), "
                f"{len(moved)} membership change(s)"
            )

    resolved: list[RegistryCluster] = []
    for idx, cluster in enumerate(new.clusters):
        if cluster.id:
            resolved.append(cluster)
            continue
        cluster_id = assigned.get(idx)
        if cluster_id is None:
            cluster_id = _next_id(taken)
            taken.add(cluster_id)
            notes.append(f"{cluster_id}: new cluster ({cluster.label})")
        resolved.append(RegistryCluster(
            id=cluster_id, label=cluster.label, members=cluster.members,
            au=cluster.au, height=cluster.height,
            bp_at_unit_scale=cluster.bp_at_unit_scale, curated=cluster.curated,
        ))

    for previous_id in sorted(set(previous_members) - used_previous - {c.id for c in new.clusters if c.curated}):
        notes.append(f"{previous_id}: retired (no successor cluster)")

    resolved.sort(key=lambda c: c.id)
    return (
        SuperarchetypeRegistry(
            clusters=tuple(resolved),
            staples=new.staples,
            unassigned=new.unassigned,
            window_since=new.window_since,
            window_until=new.window_until,
            derived_at=new.derived_at,
            stability=new.stability,
            cophenetic=new.cophenetic,
            degraded=new.degraded,
            reasons=new.reasons,
            seed=new.seed,
            n_boot=new.n_boot,
            window_policy=new.window_policy,
            entity_horizons=new.entity_horizons,
            audit_lines=new.audit_lines,
        ),
        tuple(notes),
    )


def membership_churn(
    new: SuperarchetypeRegistry,
    previous: SuperarchetypeRegistry | None,
) -> ChurnReport:
    """Co-membership agreement and per-archetype moves between two refreshes.

    ``agreement`` is ``None`` when there is no previous registry or fewer than two archetypes are
    present in both — an honest "cannot compare", never a fabricated 1.0.
    """
    if previous is None:
        return ChurnReport(
            comparable=0, agreement=None, moves=(), arrivals=(), departures=(),
            note="no previous registry — first derivation, nothing to compare",
        )

    new_home = {m.archetype: c.id for c in new.clusters for m in c.members}
    old_home = {m.archetype: c.id for c in previous.clusters for m in c.members}
    common = sorted(set(new_home) & set(old_home))

    moves = tuple(
        (archetype, old_home[archetype], new_home[archetype])
        for archetype in common
        if old_home[archetype] != new_home[archetype]
    )
    arrivals = tuple(sorted(set(new_home) - set(old_home)))
    departures = tuple(sorted(set(old_home) - set(new_home)))

    if len(common) < 2:
        return ChurnReport(
            comparable=len(common), agreement=None, moves=moves,
            arrivals=arrivals, departures=departures,
            note=f"only {len(common)} archetype(s) present in both refreshes — agreement undefined",
        )

    agree = total = 0
    for i, a in enumerate(common):
        for b in common[i + 1:]:
            total += 1
            if (new_home[a] == new_home[b]) == (old_home[a] == old_home[b]):
                agree += 1
    agreement = agree / total
    note = (
        f"co-membership agreement {agreement:.3f} over {len(common)} shared archetype(s) "
        f"(measured baseline ~{_CHURN_BASELINE:.2f}; materially lower is itself the alarm)"
    )
    return ChurnReport(
        comparable=len(common), agreement=agreement, moves=moves,
        arrivals=arrivals, departures=departures, note=note,
    )


# ---------------------------------------------------------------------------
# Persistence — JSON SSOT (json-ssot-rebuildable-duckdb-table)
# ---------------------------------------------------------------------------


def _registry_to_dict(registry: SuperarchetypeRegistry) -> dict:
    return {
        "version": 1,
        "derived_at": registry.derived_at,
        "window_since": registry.window_since,
        "window_until": registry.window_until,
        "stability": registry.stability,
        "cophenetic": registry.cophenetic,
        "degraded": registry.degraded,
        "seed": registry.seed,
        "n_boot": registry.n_boot,
        "window_policy": registry.window_policy,
        "entity_horizons": [list(row) for row in registry.entity_horizons],
        "audit_lines": list(registry.audit_lines),
        "staples": list(registry.staples),
        "unassigned": [[a, r] for a, r in registry.unassigned],
        "reasons": list(registry.reasons),
        "clusters": [
            {
                "id": c.id,
                "label": c.label,
                "au": c.au,
                "height": c.height,
                "bp_at_unit_scale": c.bp_at_unit_scale,
                "curated": c.curated,
                "members": [
                    {
                        "archetype": m.archetype,
                        "provenance": m.provenance,
                        "n_decks": m.n_decks,
                        "note": m.note,
                    }
                    for m in c.members
                ],
            }
            for c in registry.clusters
        ],
    }


def _registry_from_dict(raw: Mapping) -> SuperarchetypeRegistry:
    return SuperarchetypeRegistry(
        clusters=tuple(
            RegistryCluster(
                id=c["id"],
                label=c["label"],
                members=tuple(
                    ClusterMember(
                        archetype=m["archetype"],
                        provenance=m["provenance"],
                        n_decks=int(m["n_decks"]),
                        note=m.get("note"),
                    )
                    for m in c["members"]
                ),
                au=c.get("au"),
                height=c.get("height"),
                bp_at_unit_scale=c.get("bp_at_unit_scale"),
                curated=bool(c.get("curated", False)),
            )
            for c in raw.get("clusters", [])
        ),
        staples=tuple(raw.get("staples", ())),
        unassigned=tuple((a, r) for a, r in raw.get("unassigned", ())),
        window_since=raw.get("window_since"),
        window_until=raw.get("window_until"),
        derived_at=raw["derived_at"],
        stability=float(raw.get("stability", 0.0)),
        cophenetic=float(raw.get("cophenetic", 0.0)),
        degraded=bool(raw.get("degraded", False)),
        reasons=tuple(raw.get("reasons", ())),
        seed=int(raw.get("seed", 0)),
        n_boot=int(raw.get("n_boot", 0)),
        window_policy=raw.get("window_policy", "global"),
        entity_horizons=tuple(
            (str(a), since, str(source))
            for a, since, source in raw.get("entity_horizons", ())
        ),
        audit_lines=tuple(raw.get("audit_lines", ())),
    )


def write_derived_registry(registry: SuperarchetypeRegistry, path: Path | str) -> None:
    """Write the derived registry JSON (the SSOT). Creates the parent directory at write time."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_registry_to_dict(registry), indent=2, sort_keys=False) + "\n")


def read_derived_registry(path: Path | str) -> SuperarchetypeRegistry | None:
    """Read the derived registry JSON. ``None`` when absent (honest-degrade); malformed stays loud."""
    path = Path(path)
    if not path.exists():
        return None
    return _registry_from_dict(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Persistence — rebuildable DuckDB cache (the consumption seam)
# ---------------------------------------------------------------------------

SUPERARCHETYPE_MEMBERS_DDL = """
CREATE TABLE IF NOT EXISTS superarchetype_members (
    cluster_id VARCHAR NOT NULL,
    cluster_label VARCHAR NOT NULL,
    archetype VARCHAR NOT NULL,
    provenance VARCHAR NOT NULL,
    n_decks INTEGER NOT NULL,
    note VARCHAR,
    au DOUBLE,
    height DOUBLE,
    bp_at_unit_scale DOUBLE,
    curated BOOLEAN NOT NULL,
    member_idx INTEGER NOT NULL
)
"""

SUPERARCHETYPE_META_DDL = """
CREATE TABLE IF NOT EXISTS superarchetype_meta (
    derived_at VARCHAR NOT NULL,
    window_since VARCHAR,
    window_until VARCHAR,
    staples_json VARCHAR NOT NULL,
    unassigned_json VARCHAR NOT NULL,
    reasons_json VARCHAR NOT NULL,
    stability DOUBLE NOT NULL,
    cophenetic DOUBLE NOT NULL,
    degraded BOOLEAN NOT NULL,
    seed INTEGER NOT NULL,
    n_boot INTEGER NOT NULL,
    window_policy VARCHAR NOT NULL,
    entity_horizons_json VARCHAR NOT NULL,
    audit_lines_json VARCHAR NOT NULL
)
"""


def init_superarchetype_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create both derived-cache tables if absent (idempotent)."""
    con.execute(SUPERARCHETYPE_MEMBERS_DDL)
    con.execute(SUPERARCHETYPE_META_DDL)


def rebuild_superarchetype_members(
    con: duckdb.DuckDBPyConnection, registry: SuperarchetypeRegistry
) -> None:
    """DROP -> schema -> INSERT. Always a full replace: the taxonomy is recomputed whole every run,
    so an incremental upsert would mix memberships derived over two different windows."""
    con.execute("DROP TABLE IF EXISTS superarchetype_members")
    con.execute("DROP TABLE IF EXISTS superarchetype_meta")
    init_superarchetype_schema(con)

    member_rows = [
        (
            cluster.id, cluster.label, member.archetype, member.provenance, int(member.n_decks),
            member.note, cluster.au, cluster.height, cluster.bp_at_unit_scale,
            bool(cluster.curated), idx,
        )
        for cluster in registry.clusters
        for idx, member in enumerate(cluster.members)
    ]
    if member_rows:
        con.executemany(
            """
            INSERT INTO superarchetype_members (
                cluster_id, cluster_label, archetype, provenance, n_decks, note,
                au, height, bp_at_unit_scale, curated, member_idx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            member_rows,
        )

    con.execute(
        """
        INSERT INTO superarchetype_meta (
            derived_at, window_since, window_until, staples_json, unassigned_json, reasons_json,
            stability, cophenetic, degraded, seed, n_boot, window_policy,
            entity_horizons_json, audit_lines_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            registry.derived_at, registry.window_since, registry.window_until,
            json.dumps(list(registry.staples)),
            json.dumps([[a, r] for a, r in registry.unassigned]),
            json.dumps(list(registry.reasons)),
            registry.stability, registry.cophenetic, registry.degraded,
            registry.seed, registry.n_boot, registry.window_policy,
            json.dumps([list(row) for row in registry.entity_horizons]),
            json.dumps(list(registry.audit_lines)),
        ],
    )


def read_superarchetype_members(
    con: duckdb.DuckDBPyConnection,
) -> SuperarchetypeRegistry | None:
    """Read the persisted taxonomy back. ``None`` on a fresh/missing table (honest-degrade — the CLI
    renders "no registry" rather than crashing). Only the missing-table case degrades; any other DB
    error stays loud."""
    try:
        meta_columns = {
            str(row[1]) for row in con.execute(
                "PRAGMA table_info('superarchetype_meta')"
            ).fetchall()
        }
        if not meta_columns:
            return None
        metadata_tail = (
            "window_policy, entity_horizons_json, audit_lines_json"
            if "window_policy" in meta_columns
            else "'global' AS window_policy, '[]' AS entity_horizons_json, "
                 "'[]' AS audit_lines_json"
        )
        meta = con.execute(
            f"""
            SELECT derived_at, window_since, window_until, staples_json, unassigned_json,
                   reasons_json, stability, cophenetic, degraded, seed, n_boot,
                   {metadata_tail}
            FROM superarchetype_meta
            """
        ).fetchall()
        rows = con.execute(
            """
            SELECT cluster_id, cluster_label, archetype, provenance, n_decks, note,
                   au, height, bp_at_unit_scale, curated, member_idx
            FROM superarchetype_members
            ORDER BY cluster_id, member_idx
            """
        ).fetchall()
    except duckdb.CatalogException:
        return None
    if not meta:
        return None

    (
        derived_at, window_since, window_until, staples_json, unassigned_json, reasons_json,
        stability, cophenetic, degraded, seed, n_boot, window_policy,
        entity_horizons_json, audit_lines_json,
    ) = meta[0]

    staged: dict[str, dict] = {}
    for (
        cluster_id, cluster_label, archetype, provenance, n_decks, note,
        au, height, bp_at_unit_scale, curated, _member_idx,
    ) in rows:
        entry = staged.setdefault(cluster_id, {
            "label": cluster_label, "au": au, "height": height,
            "bp_at_unit_scale": bp_at_unit_scale, "curated": bool(curated), "members": [],
        })
        entry["members"].append(ClusterMember(
            archetype=archetype, provenance=provenance, n_decks=int(n_decks), note=note,
        ))

    clusters = tuple(
        RegistryCluster(
            id=cluster_id, label=entry["label"], members=tuple(entry["members"]),
            au=entry["au"], height=entry["height"],
            bp_at_unit_scale=entry["bp_at_unit_scale"], curated=entry["curated"],
        )
        for cluster_id, entry in sorted(staged.items())
    )
    return SuperarchetypeRegistry(
        clusters=clusters,
        staples=tuple(json.loads(staples_json)),
        unassigned=tuple((a, r) for a, r in json.loads(unassigned_json)),
        window_since=window_since,
        window_until=window_until,
        derived_at=derived_at,
        stability=float(stability),
        cophenetic=float(cophenetic),
        degraded=bool(degraded),
        reasons=tuple(json.loads(reasons_json)),
        seed=int(seed),
        n_boot=int(n_boot),
        window_policy=window_policy,
        entity_horizons=tuple(
            (str(a), since, str(source))
            for a, since, source in json.loads(entity_horizons_json)
        ),
        audit_lines=tuple(json.loads(audit_lines_json)),
    )


# ---------------------------------------------------------------------------
# The offline pass
# ---------------------------------------------------------------------------


def run_superarchetypes(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str | None = None,
    until: str | None = None,
    seed: int = 0,
    n_boot: int = 200,
    au_min: float | None = None,
    min_bp: float | None = None,
    curated: Mapping[str, CuratedCluster] | None = None,
    derived_path: Path | str | None = None,
    write: bool = True,
) -> RunResult:
    """Recluster over the window, merge curated overrides, persist, and report churn.

    Sibling of ``label`` / ``discover run`` / ``eras run``: a full recompute every call, never
    incremental. ``write=False`` computes and returns without touching either persistence surface.

    ``curated`` defaults to the shipped registry and ``derived_path`` to the configured derived
    path; both are injectable so tests never touch the shipped file or the project data directory.
    """
    from legacy_engine.config import DERIVED_SUPERARCHETYPES_PATH

    resolved_path = Path(derived_path) if derived_path is not None else DERIVED_SUPERARCHETYPES_PATH
    resolved_curated = CURATED_SUPERARCHETYPES if curated is None else curated

    window_policy = "global" if since is not None else "per-entity-era"
    entity_horizons: tuple[tuple[str, str | None, str], ...] = ()
    audit_lines: tuple[str, ...] = ()
    if window_policy == "per-entity-era":
        from legacy_engine.analytics.eras.consume import era_horizons

        labels = [
            str(row[0]) for row in con.execute(
                "SELECT DISTINCT archetype FROM decks "
                "WHERE archetype IS NOT NULL AND archetype <> '' ORDER BY archetype"
            ).fetchall()
        ]
        horizons, audit_lines = era_horizons(con, labels)
        entity_horizons = tuple(
            (label, horizons[label].since, horizons[label].source) for label in labels
        )
        decks = load_archetype_decks(
            con, until=until,
            since_by_archetype={label: horizon.since for label, horizon in horizons.items()},
        )
    else:
        decks = load_archetype_decks(con, since=since, until=until)
    deck_counts: dict[str, int] = {}
    for deck in decks:
        deck_counts[deck.archetype] = deck_counts.get(deck.archetype, 0) + 1

    kwargs: dict[str, object] = {"seed": seed, "n_boot": n_boot}
    if au_min is not None:
        kwargs["au_min"] = au_min
    if min_bp is not None:
        kwargs["min_bp"] = min_bp
    solution = cluster_archetypes(decks, **kwargs)  # type: ignore[arg-type]

    previous = read_derived_registry(resolved_path)
    merged = merge_curated(
        solution, resolved_curated,
        deck_counts=deck_counts, window_since=since, window_until=until,
        derived_at=datetime.now(UTC).isoformat(),
        window_policy=window_policy,
        entity_horizons=entity_horizons,
        audit_lines=audit_lines,
    )
    registry, remap = match_identities(merged, previous)
    churn = membership_churn(registry, previous)

    if write:
        write_derived_registry(registry, resolved_path)
        rebuild_superarchetype_members(con, registry)

    total = len(decks)
    definer_decks = sum(deck_counts.get(a, 0) for a in solution.definers)
    placed = {m.archetype for c in registry.clusters for m in c.members}
    assigned_decks = sum(deck_counts.get(a, 0) for a in placed)
    return RunResult(
        registry=registry,
        solution=solution,
        churn=churn,
        remap=remap,
        n_archetypes=len(deck_counts),
        n_definers=len(solution.definers),
        definer_field_share=(definer_decks / total) if total else 0.0,
        assigned_field_share=(assigned_decks / total) if total else 0.0,
        written=write,
    )
