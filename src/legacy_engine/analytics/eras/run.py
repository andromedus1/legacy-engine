"""``eras run`` — the offline era-labeling pass: series -> detectors -> ensemble -> attribution ->
drift alarm -> persisted store.

Sibling of `label`/`discover run` (json-ssot-rebuildable-duckdb-table's rebuild-pass
convention): a full-corpus recompute every call, never incremental — `ensemble.derive_eras`'s
BH-FDR needs the whole fleet's p-values together, so a partial run would corrupt every OTHER
entity's `bh_accepted` verdict.

The drift alarm closes the absorbed banlist-currency loop
(`docs/briefs/change-point-detection.md` §7): a Beta-Binomial BOCPD tail check on each high-share
entity's own (decks, field_decks) share series, firing when a recent disturbance is NOT already
explained by an accepted, attributed (ban/release) boundary — i.e. the drift alarm IS the
unattributed case.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone

import duckdb
import numpy as np

from legacy_engine.analytics.eras.attribution import Attribution, attribute_boundaries
from legacy_engine.analytics.eras.bocpd import beta_binomial_bocpd
from legacy_engine.analytics.eras.detect import (
    CandidateBoundary,
    corroborate_winrate,
    detect_composition,
    detect_presence,
    detect_share,
)
from legacy_engine.analytics.eras.ensemble import EntityEras, derive_eras
from legacy_engine.analytics.eras.series import EntitySeries, build_entity_series
from legacy_engine.analytics.eras.store import write_entity_eras
from legacy_engine.ingestion.banlist import BAN_EVENTS

_ATTRIBUTION_TOLERANCE_DAYS: int = 14

# ---------------------------------------------------------------------------
# Drift alarm — calibrated 2026-07-11 against tests/analytics/eras/conftest.py's real-corpus
# fixtures, using beta_binomial_bocpd's own default hazard_lambda (25.0, ~4 disturbances/year):
#   tron_cliff_series's last complete bucket (the Candelabra cliff, 59->20 decks/week) spikes
#     p_change to ~0.9996 (see tests/analytics/eras/test_run.py::TestAlarmCalibration).
#   stable_nonevent_series's last 3 complete buckets top out at ~0.11 (periodic wobble, no true
#     disturbance).
# 0.5 sits with wide margin either side of that gap.
# ---------------------------------------------------------------------------
_ALARM_BAR: float = 0.5
_ALARM_SHARE_FLOOR: float = 0.02      # entities below 2% field share are never alarm-eligible
_ALARM_RECENT_BUCKETS: int = 3        # "recent" = the last N complete buckets
_ALARM_MIN_COMPLETE_BUCKETS: int = 4  # below this, bucket 0's cold-start p_change=1.0 (bocpd.py
                                       # module docstring) could leak into the "recent" window


@dataclass(frozen=True)
class AlarmFlag:
    """One entity's unattributed drift alarm — the loud, human-facing half of the banlist-
    currency loop."""

    entity: str
    p_change: float
    note: str


@dataclass(frozen=True)
class EntityRunSummary:
    """Per-entity headline for the CLI/report layer."""

    entity: str
    stable_since: str | None
    inherited_from_parent: bool
    n_boundaries: int
    n_accepted: int
    post_boundary_decks: int


@dataclass(frozen=True)
class ErasRunResult:
    """The full result of one `run_eras` pass — persisted to `entity_eras` AND returned here so
    the CLI can render without a second DB round trip."""

    summaries: dict[str, EntityRunSummary]
    attributions: dict[tuple[str, str], Attribution]
    alarms: dict[str, AlarmFlag]
    n_entities: int
    provenance: str | None
    alpha: float


_UNATTRIBUTED_DEFAULT = Attribution(
    kind="unattributed", card=None, detail="(no attribution on record)",
)


def _default_release_source(con: duckdb.DuckDBPyConnection) -> dict[str, date]:
    """No-network stub: card name -> release date, read from the ``cards`` table if it carries a
    release-date column. As of this feature's schema (`ingestion/store.py::CARDS_DDL`), it does
    not — this honestly degrades to an empty mapping (release attribution unavailable; BAN_EVENTS-
    only attribution still covers the headline ban case) rather than failing the whole run.
    """
    try:
        cols = {row[1] for row in con.execute("PRAGMA table_info('cards')").fetchall()}
    except Exception:
        return {}
    release_col = next((c for c in ("release_date", "released_at") if c in cols), None)
    if release_col is None:
        return {}
    rows = con.execute(
        f"SELECT name, {release_col} FROM cards WHERE {release_col} IS NOT NULL"  # noqa: S608
    ).fetchall()
    out: dict[str, date] = {}
    for name, raw in rows:
        if isinstance(raw, date):
            out[name] = raw
        else:
            try:
                out[name] = date.fromisoformat(str(raw))
            except ValueError:
                continue
    return out


def _post_boundary_decks(s: EntitySeries, stable_since: str | None) -> int:
    """Sample size for `eras list`'s confidence tier: decks at/after `stable_since`, or the
    entity's whole pool when there is no boundary (full history IS the sample)."""
    if stable_since is None:
        return sum(b.decks for b in s.buckets)
    return sum(b.decks for b in s.buckets if b.start >= stable_since)


def compute_drift_alarms(
    series: dict[str, EntitySeries],
    eras: dict[str, EntityEras],
    attributions: dict[tuple[str, str], Attribution],
) -> dict[str, AlarmFlag]:
    """BOCPD tail check: alarm on a high-share entity whose recent share history looks freshly
    disturbed AND is not already explained by an accepted, attributed (ban/release) boundary.

    Public (not a private helper) so it is directly testable against the shared calibration
    fixtures without needing a full DB corpus (see `test_run.py::TestAlarmCalibration`).
    """
    alarms: dict[str, AlarmFlag] = {}
    for entity, s in series.items():
        complete = [b for b in s.buckets if b.complete]
        if len(complete) < _ALARM_MIN_COMPLETE_BUCKETS:
            continue

        successes = np.array([b.decks for b in complete], dtype=float)
        trials = np.array([b.field_decks for b in complete], dtype=float)
        total_trials = float(trials.sum())
        if total_trials <= 0:
            continue
        share = float(successes.sum() / total_trials)
        if share < _ALARM_SHARE_FLOOR:
            continue

        result = beta_binomial_bocpd(successes, trials)
        recent = result.p_change[-_ALARM_RECENT_BUCKETS:]
        max_p = float(recent.max())
        if max_p < _ALARM_BAR:
            continue

        recent_start = complete[-min(_ALARM_RECENT_BUCKETS, len(complete))].start
        entity_eras = eras.get(entity)
        covered = False
        if entity_eras is not None:
            covered = any(
                b.bh_accepted and not b.floor_rejected and b.date >= recent_start
                and attributions.get((entity, b.date), _UNATTRIBUTED_DEFAULT).kind != "unattributed"
                for b in entity_eras.boundaries
            )
        if covered:
            continue

        alarms[entity] = AlarmFlag(
            entity=entity,
            p_change=max_p,
            note=(
                f"unattributed disturbance (p_change={max_p:.3f}) — "
                "possible unregistered B&R change"
            ),
        )
    return alarms


def run_eras(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    alpha: float = 0.05,
    seed: int = 0,
    release_source: "Callable[[duckdb.DuckDBPyConnection], dict[str, date]] | None" = None,
) -> ErasRunResult:
    """The offline era-labeling pass — sibling of `label`/`discover run`.

    Full-corpus recompute: build every entity's series, run every detector, merge + fleet-wide
    BH-FDR + deck floor + camp inheritance (`ensemble.derive_eras`), attribute each boundary to
    the ban/release ledger (or leave it an honest unattributed disturbance), check the BOCPD
    drift alarm, and persist the whole result to `entity_eras` (DROP + reload; never an
    incremental upsert).
    """
    series = build_entity_series(con, provenance=provenance)

    candidates: list[CandidateBoundary] = []
    for s in series.values():
        cands = detect_presence(s)
        cands += detect_composition(s, seed=seed)
        cands += detect_share(s, seed=seed)
        cands = corroborate_winrate(s, cands)
        candidates.extend(cands)

    eras = derive_eras(series, candidates, alpha=alpha)

    releases = (release_source or _default_release_source)(con)
    attributions = attribute_boundaries(
        eras, ban_events=BAN_EVENTS, releases=releases, series=series,
        tolerance_days=_ATTRIBUTION_TOLERANCE_DAYS,
    )

    alarms = compute_drift_alarms(series, eras, attributions)

    run_at = datetime.now(timezone.utc).isoformat()
    post_boundary_decks = {
        entity: _post_boundary_decks(series[entity], e.stable_since)
        for entity, e in eras.items()
    }
    parent_map = {entity: s.parent for entity, s in series.items()}

    write_entity_eras(
        con, eras, attributions, alarms,
        run_meta={
            "provenance": provenance,
            "alpha": alpha,
            "run_at": run_at,
            "post_boundary_decks": post_boundary_decks,
            "parent": parent_map,
        },
    )

    summaries = {
        entity: EntityRunSummary(
            entity=entity,
            stable_since=e.stable_since,
            inherited_from_parent=e.inherited_from_parent,
            n_boundaries=len(e.boundaries),
            n_accepted=sum(1 for b in e.boundaries if b.bh_accepted and not b.floor_rejected),
            post_boundary_decks=post_boundary_decks[entity],
        )
        for entity, e in eras.items()
    }
    return ErasRunResult(
        summaries=summaries,
        attributions=attributions,
        alarms=alarms,
        n_entities=len(series),
        provenance=provenance,
        alpha=alpha,
    )
