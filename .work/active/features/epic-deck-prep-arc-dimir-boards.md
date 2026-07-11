---
id: epic-deck-prep-arc-dimir-boards
kind: feature
stage: done
tags: [advisory, analysis, dogfooding]
parent: epic-deck-prep-arc
depends_on: []
release_binding: v0.3.0
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Dimir Tempo sideboard refresh — two collection-aware boards

## Brief

Fresh optimized sideboard for Andrew's Dimir Tempo (Build B, `decks/dimir-tempo-current.txt`;
prior optimized board + analysis: `decks/dimir-tempo-optimized.txt` + `-analysis.md`), using
the post-sweep engine (deterministic ILP, PR #35). Produce TWO boards per meta lens where
they differ: **Board A** unconstrained — may include cards Andrew doesn't own, and those
unowned inclusions double as the acquisition-target list (paired-swap presentation: every
add names its cut); **Board B** constrained to the current collection (`decks/binder.txt`
is confirmed accurate). Deliverable: updated board files + analysis doc in `decks/` per the
established pattern (frequency-distribution-detail: show full 0x-4x copy histograms vs
winners, now available natively from the sweep/backtest copy surfaces).

Does NOT cover: other archetypes, meta-specific 60s (next feature), scorer changes. Apply
session-1 judgment overrides where still mechanically justified (Defense Grid / Damping
Sphere exclusions — both now confirmed systematic by the sweep).

## Epic context

- Parent epic: `epic-deck-prep-arc`
- Position: foundation stride — establishes the refreshed Dimir reference the comparison
  feature consumes.

## Inherited design decisions

- Collection data is CURRENT; Board A unconstrained (= acquisition targets), Board B
  owned-only. If the solver lacks a hard owned-only mode, restrict the candidate pool to
  owned cards and label the constraint honestly (feature-design call).
- Boulder field = `decks/boulder-field-since-518.txt`; online = `provenance='online'`,
  current-regime window.

## Design decisions (feature-design, 2026-07-04, autopilot)

- **Maindeck input**: `decks/dimir-tempo-current.txt` (= Build B, Andrew's committed 75).
- **Board B mechanism (verified against code)**: `advise sideboard --owned-only` is a
  DISPLAY filter only (suppresses unowned rows post-solve, cli.py ~2894) and the coverage
  model is deliberately collection-blind (sideboard.py ~2015) — no owned-only solve mode
  exists. Board B therefore re-solves via a small Python driver: `recommend_sideboard`
  with the hoser catalog filtered to owned cards (collection = `decks/binder.txt` via the
  shipped CollectionView loader), then post-check `owned` annotations — any unowned card
  that still enters through the promoted-empirical-pool path (which bypasses the catalog)
  is repaired with the best OWNED alternative from the `considering` ranked pool, each
  repair labeled as a paired swap. Board B is labeled "owned-constrained (catalog-filtered
  + labeled repairs)" — never presented as a native solver mode.
- **Deliverables roll forward in place** (rolling-foundation): update
  `decks/dimir-tempo-optimized.txt` + `-analysis.md`; Board B lands as
  `decks/dimir-tempo-optimized-owned.txt`. Board A's unowned inclusions render as the
  acquisition list with paired swaps (add → cut), copy histograms per
  frequency-distribution-detail (0x-4x from `observed_copy_distribution`).
- **Primary lens = Boulder** (Andrew plays paper Boulder); the online-lens board is a
  labeled variant section in the analysis doc, not a separate file — the meta-decks
  feature owns full per-meta lists.
- Session-1 judgment overrides re-applied only if still mechanically justified: Defense
  Grid + Damping Sphere exclusions (both sweep-confirmed systematic scorer false
  positives, 18 and 6 archetypes respectively).

## Implementation Units (analysis stride)

1. **Currency check** — data freshness (`refresh all` upstream cap), collection load
   (binder.txt parses; count echoed). AC: both echoed in the analysis doc header.
2. **Board A (Boulder lens)** — `advise sideboard` vs Boulder field with `--collection`,
   plus `advise backtest --field-scope` context (overlap/scorer-only/winners-only + copy
   histograms). AC: board sums to 15; every off-consensus inclusion has a stated
   mechanical rationale; Defense Grid/Damping Sphere handled per override rule.
3. **Board B (owned-constrained)** — the driver described above. AC: every card owned per
   binder.txt; every divergence from Board A labeled as a paired swap with the residual
   coverage delta; A-vs-B delta section = the acquisition shortlist.
4. **Online-lens variant** — same solve vs the online-provenance field; report only the
   DIFF vs the Boulder board (venue-divergence presentation, never blended). AC: diff
   section with per-card reasons.
5. **Analysis doc** — update `decks/dimir-tempo-optimized-analysis.md` in place (rolling
   foundation; git keeps history): boards, paired swaps, copy histograms, acquisition
   list, honest tiers (winner sample n + confidence per claim). AC: presentation rules
   ([[paired-swap-for-card-additions]], [[frequency-distribution-detail]],
   [[analysis-statistical-context-gates]]) all satisfied.

Single-stride — no child stories. Trickiest unit is #3 (designed above; the repair loop
is deterministic and uses only shipped surfaces).

## Risks

- **Owned catalog too thin for whole answer classes** → Board B honestly shorter-coverage;
  the A-vs-B delta IS the deliverable insight, not a failure.
- **Upstream data still capped at 2026-06-15** → note currency in the doc header; regime
  window unchanged (2026-05-18+), so analysis stays regime-clean.
