---
id: feature-ranking-refresh-insights
kind: feature
stage: done
tags: [analytics, advisory]
parent: null
depends_on: [feature-validated-historical-evidence-promotion]
release_binding: null
gate_origin: null
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
Test first/unchanged/regime/method/scenario states, old/new directions, new-opponent missing forecast, Shapley arithmetic identity, fixed-support floor invariance to weight magnitudes, and truncation to three observations. Integration test successive writes plus simulated failed publication preserving the previous source. Node/desktop/mobile checks cover escaping, readability, and prior controls. Sparse changes are observations, not a claim of statistical significance. Review once at standard weight after integrated feature verification.

## Implementation dispatch

The shared projection/evaluator code is verified and at review; its actual-corpus experiment runs
in parallel. Refresh comparisons consume the fixed report payload and do not depend on the
eventual borrowing selection. One Luna xhigh worker owns the pure comparison module, publication
read/attach seam, template card, and focused tests. Do not change compute_blob, the projection,
or historical evaluation code while forecast freezes run. Existing card styling is reused under
the approved existing-component mock exception. Host retains empirical selection and PR/CI.

## Implementation notes
- Execution capability: Luna xhigh single-owner pass; the comparison module, publication attachment seam, existing-style card, and focused contracts form one cohesive change.
- Review weight: standard (project default; host agent performs the independent feature review).
- Files changed: `src/legacy_engine/advisory/ranking_changes.py`, `scripts/refresh_best_call_ranking.py`, `scripts/best_call_ranking_template.html`, and `tests/test_ranking_changes.py`.
- Tests added/removed: `tests/test_ranking_changes.py` covers baseline, unchanged data, compatibility boundaries, symmetric attribution identity, missing forecasts, floor support handling, and JSON-decoder prior reads; no tests removed.
- Simplification: refresh inputs are persisted in the existing `meta.refresh_changes.snapshot`; no second store, computation path, or UI control was introduced.
- Discrepancies from design: the additive `meta.refresh_changes` field is excluded from `_authority_payload` so diagnostic publication metadata cannot alter the ranking authority invariant.
- Adjacent issues parked: none.

## Standard review and accepted fixes

One fresh-context Sol xhigh review requested changes; the Claude peer remained unavailable, so
this was same-harness independent review. All findings were accepted and verified:

- Changed performance calls now show the relative field-weight and matchup-estimate shift when
  both candidate decompositions exist, including when both decks declined.
- Observed-count-only refreshes remain analytically unchanged; the zero-observation guard stays
  separate.
- A recognized payload missing rows, field shares, or comparison dates is malformed comparison
  input, not a clean baseline.
- Removed the unused per-candidate support list (about 160KB in the current snapshot).
- Missing attribution for an unrelated candidate cannot displace a valid changed recommendation
  or exact beneficiary insight. Full unavailable details remain in the payload.

57 focused comparison/publication checks pass. The reviewer also verified that the live page's
cell ledger reconstructs eligible performance values with structural mirrors to floating-point
precision, and found escaping, static filter behavior, periods, and atomic publication sound.
No second standard review is required; final combined CI/browser verification remains pending.
Implementation commits were briefly amended concurrently by the two workers; host checked that
all content survived in `9864a58` and `91a36f1`. Subsequent work uses new commits only.

## Completion evidence — 2026-09-05

Complete after the single standard independent review, accepted-fix verification, and final-source
CI at `87f5f80637c06fddf5e5944e9774aae8c735544d`: run `33991481774` passed on Python 3.11
and 3.13, each **4,183 passed, 2 skipped**. The final focused integration set passed 118 tests;
touched-file Ruff and `git diff --check` passed. Documentation review found no Critical/High drift.

Both actual reports were regenerated from that source and Chromium-checked at desktop and
390px mobile widths: keyboard/touch tooltips, coverage and n filters, unchanged underlying
recommendations and refresh comparisons, dated Method scores, and camp-link navigation all pass.
Global and local reports preserve identical eligible archetype/camp sets. Corpus maximum is
2026-09-03. Global performance/floor calls are ReaShow / Ad Nauseam Tendrils.

Global artifact: `decks/deck-rankings.html`, SHA256
`3735f4d155942c5a886b45226c22a36739d9eed7ee54c3b1c9e43792100a4a68`; the operational status
records this digest. Refresh completed; two existing era alarms remain pending confirmation data.
Local artifact: `decks/deck-rankings-local-saved.html`, SHA256
`cd65f4d0d9c9883cbf9b7777c0eeb62566429b839256db0cb9e3426e077b9b6c`. Its saved post-May 18
sample has 107 players, unspecified end date, and 7.48% explicit unknown opponent mass; it is
not described as a newly observed local field. Local camp performance changes from Eldrazi
[Abundant Countryside] to Death & Taxes [Marsh Flats]. Local plan shares remain visible while
composition-specific plan performance/floor estimates are explicitly unavailable.

Delivery PR: https://github.com/andromedus1/legacy-engine/pull/92, based on the existing
`codex/deck-rankings-baseline` integration branch after PR91 merged there. No claim of a main
release: the older baseline history remains separate from this feature's completion.
