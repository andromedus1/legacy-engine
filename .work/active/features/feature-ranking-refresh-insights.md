---
id: feature-ranking-refresh-insights
kind: feature
stage: drafting
tags: [analytics, advisory]
parent: null
depends_on: [feature-validated-historical-evidence-promotion]
release_binding: null
created: 2026-09-05
updated: 2026-09-05
---

# Explain what changed in Deck Rankings

## Brief
Add at most three concise data-derived observations to the canonical report: field movement, who benefits, and changed recommendations with attribution to field weights versus matchup estimates. Compare successive compatible published snapshots; first publication, unchanged data, and incompatible comparisons need honest useful behavior. Avoid canned prose and noise disguised as movement.

## Outcome boundary
Persist the small comparison inputs through the existing atomic refresh publication path. Derive observations deterministically from actual deltas, showing the comparison period. Reuse the report's compact card/disclosure styling. Keep the map, evidence filters, and independent picks. Test first/same/changed snapshot and counterfactual attribution.

## Simplification
Use the existing report payload and atomic publication rather than a second report, external language-model call, or new database.

## Authorized direction
Andrew approved the four-part sequence on 2026-09-05 and asked to execute it: improve historical borrowing and evaluate the exact current model; explain refresh changes concisely; examine pilotable archetype units; apply both independent priorities to custom fields. Keep estimates visible throughout. Existing data integrity and incompatible-era boundaries remain in force. Current report styling and interactions are the approved reference. No new audience, hosted product, or geographic ingestion is in scope.

## Execution
Standard feature review (default): one independent pass followed by verification of accepted fixes. Features run in the approved order. Reuse existing implementation and research before adding abstractions; preserve unrelated Hogaak files and uv.lock changes. Design records concrete interfaces before implementation.

## Design decisions (--only-questions directional pass)
No unanswered user-level choice: at most three short observations in the approved report, current global refresh comparisons, no invented narrative or extra controls. Compare the last successfully published report at the same output path. Reuse the existing card and muted-caption styling below the priority cards; this minor content extension needs no new visual language or mock under AGENTS' existing-component exception. Browser evidence filters do not redefine historical refresh changes; label the section as the published field comparison.

## Architectural choice
Options: a separate snapshot database; a sidecar JSON with a two-file publication contract; or derive the comparison snapshot from the already atomic published HTML. Choose the last. The embedded `const D` JSON already carries every required cell and field weight; parse it with JSONDecoder, never execute HTML. This avoids duplicated persisted state and makes failed writes leave the prior comparison intact.

## Implementation units
- `src/legacy_engine/advisory/ranking_changes.py`: `ranking_snapshot(blob: Mapping) -> dict`, `compare_ranking_snapshots(current: Mapping, previous: Mapping | None) -> dict`. Snapshot captures method, scenario identity (global initially), field start/corpus cutoff, field shares, eligible candidate set, cell means, and independent calls. Exclude timestamps and display-only filters from analytical equality. Return status/comparison dates plus at most three typed insights with text and numeric evidence.
- The field insight names largest absolute share movement in percentage points. The beneficiary insight uses a two-factor symmetric decomposition: field contribution = sum((w1-w0)*(p0+p1)/2); matchup-estimate contribution = sum((w0+w1)*(p1-p0)/2). Their sum equals the complete-field performance change. Mirrors are explicitly 0.5. Only compute exact decomposition where both snapshots contain the full required union of positive-share opponents for that candidate. New missing forecasts produce an explicit unavailable comparison, not silent imputation or renormalization. This is arithmetic attribution, not a causal claim about new data.
- The call insight names changed performance and/or floor leaders with old→new names and their available performance decomposition. A changed minimum pairing or positive-support opponent set explains floor movement; do not attribute a floor change to field share magnitudes when opponent support is unchanged.
- First publication: short baseline statement. Same analytical snapshot: unchanged statement without pretending elapsed time is new evidence. Method/regime/scenario mismatch: start a new comparison with named reason. Zero previous observed field: unavailable movement. Tiny changes that round to 0.0pp do not become headlines. If calls do not change, use the meaningful changes available rather than padding to three.
- `scripts/refresh_best_call_ranking.py`: load previous output with a small `read_published_ranking(path: Path) -> dict | None` helper, compute changes after current decisions, attach `meta.refresh_changes`, then serialize through the existing atomic writer. A legacy file with no recognized payload starts a baseline; malformed recognized payload reports comparison unavailable while current report remains publishable.
- `scripts/best_call_ranking_template.html`: render concise escaped insight text and comparison dates into one existing-style card, retaining all existing controls/map/table behavior.

## Testing and risks
Test first/unchanged/regime/method/scenario states, old/new directions, new-opponent missing forecast, Shapley arithmetic identity, fixed-support floor invariance to weight magnitudes, and truncation to three observations. Integration test successive writes plus simulated failed publication preserving the previous source. Node/desktop/mobile checks cover escaping, readability, and prior controls. Sparse changes are observations, not a claim of statistical significance. Review once at standard weight after prior feature implementation and actual evaluation verify.
