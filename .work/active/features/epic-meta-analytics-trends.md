---
id: epic-meta-analytics-trends
kind: feature
stage: drafting
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-metashare]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Meta Trends Across Ban-List Regimes (version-stamped)

## Brief
Track how the metagame evolves over time, **segmented by ban-list regime**. Partition the corpus into
windows bounded by `BanListSnapshot` `banned_date`s (a B&R announcement opens a new regime; an
archetype can be born or killed at that date — PRINCIPLES #5 legality-is-live-data), and compute the
meta-share series (per `metashare`'s definitions) within each regime / time window. Emit a
version-stamped trend series: for each archetype, its share trajectory across regimes, so a reader can
see "Archetype X was 12% pre-ban, 3% after". Stamp every series point with the regime it belongs to and
the window's event count, and flag short/thin windows `evolving` with a banner (per the ops brief's
corpus-window gate: <~4 events or <2 weeks → flagged).

Reuses `metashare` for the per-window computation rather than re-deriving share logic; this feature owns
the **time/regime partitioning and the version-stamping**, not the share math. Honors the online/paper
split. Wires the `report tiers` trend view (the tier-list-over-time surface) and/or a dedicated trends
CLI leaf as feature-design decides.

Does NOT compute matchup trends (matchup evolution is out of scope for MVP — the matchup sample is too
sparse per-regime to be honest; revisit later), nor render charts (`charts` consumes this series).

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: consumer of `metashare` (per-window share computation). Producer of the
  version-stamped trend series that `charts` renders.

## Inherited design decisions
- **Segment by ban-list regime** (B&R `banned_date` boundaries), version-stamped — reuse `BanListSnapshot` from ingestion.
- **Reuse `metashare` per-window**, don't re-derive share math.
- **Short-window gating**: <~4 events or <2 weeks → flag the window `evolving` + banner.
- **Meta-share trends only for MVP**; matchup trends deferred (per-regime matchup sample too sparse).

## Research briefs
- `docs/briefs/legacy-metagame.md` — the current meta + meta-evolution direction; ban-list regimes as the natural segmentation.
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §6 (corpus-window gating thresholds), §2 (version-stamping discipline via the manifest).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/trends.py`; `ingestion/banlist.py` `BanListSnapshot`.
- `docs/PRINCIPLES.md` — #5 legality-is-live-data (version-stamp on B&R), #7 confidence-gate.

<!-- feature-design fills in: the regime-partitioning logic, the trend-series record type, the window-gating, the CLI surface, and test approach. -->
