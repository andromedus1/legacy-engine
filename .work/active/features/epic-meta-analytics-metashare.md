---
id: epic-meta-analytics-metashare
kind: feature
stage: drafting
tags: [analytics]
parent: epic-meta-analytics
depends_on: [epic-meta-analytics-match-results]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Meta-Share Computation (three labeled definitions)

## Brief
Compute metagame share **three genuinely different, always-labeled ways** over the labeled DuckDB
decks, per PRINCIPLES #6 (never an unlabeled meta-%): **(a) raw entry share** (`count(archetype) /
total decks` — "what people brought"), **(b) top-cut presence share** (share among published top
finishers — "what won", success-filtered), and **(c) win-rate-weighted share** (`share_raw · wr(a)`,
renormalized — "expected field strength", consuming the per-archetype win/loss aggregate from
`match-results`). Every emitted share states its `(definition, online/paper basis, window)`.

Split **online / paper / blend** off `tournaments.provenance`: display each separately by default; a
weighted blend is opt-in only, with stated weights, never the default and never unlabeled. Apply a
**≥2%-of-field inclusion floor** for headline views (group sub-2% archetypes into "Other"; never tier
them). Attach `ConfidenceMetadata` + sample `n` to every share via the existing `tier_for_sample(n)`
(established ≥100 / evolving 30–99 / speculative <30); fringe (<2% share) is flagged, not silently
shown. Bucket the classifier's raw `Conflict(...)` / `Unknown` labels here (analytics owns bucketing,
per the classifier's locked decision). Wires the `report meta` CLI leaf.

Does NOT compute matchup cells (that's `matchup-matrix`), trends over time (`trends`), or render charts
(`charts`). The win-rate input for §3c comes from `match-results`, not recomputed here.

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: consumer of `match-results` (for the §3c win-rate-weighted definition). Parallel
  to `matchup-matrix`. Producer for `trends` and `charts`.

## Inherited design decisions
- **Three definitions, always labeled** with `(definition, online/paper basis, window)` — never an unlabeled blended number (PRINCIPLES #6).
- **≥2% inclusion floor** for headlines; sub-2% → "Other", never tiered.
- **online/paper split by default**; blend is opt-in with stated weights.
- **Confidence on every stat** via `tier_for_sample(n)` — reuse `confidence.py`, don't reinvent.
- **§3c win-rate input is consumed from `match-results`**, not recomputed.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §3 (the three definitions + the MTGO success-filter caveat + MTGGoldfish 5% anchor), §5 (online/paper split + the product rule), §6 (confidence gating thresholds).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/metashare.py`; the `decks` / `tournaments.provenance` schema.
- `docs/PRINCIPLES.md` — #6 never-an-unlabeled-meta-%, #7 confidence-gate-every-stat.

<!-- feature-design fills in: the SQL for each definition, the share record type, the inclusion-floor + Other-bucketing logic, the CLI leaf, and test approach (known subset → hand-checked stats). -->
