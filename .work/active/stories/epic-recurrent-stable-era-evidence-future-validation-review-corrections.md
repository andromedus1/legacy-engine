---
id: epic-recurrent-stable-era-evidence-future-validation-review-corrections
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-future-validation
depends_on:
  - epic-recurrent-stable-era-evidence-future-validation-promotion-gate
release_binding: null
gate_origin: review
created: 2026-08-16
updated: 2026-08-16
---

# Replace placeholder future validation with an executable cutoff-safe benchmark

## Brief

Resolve every blocker from the standard review of frozen commit `811b04b`. Implement the actual
origin-local refit and seal, estimator-independent future-case ledger, predictive and decision
evaluation, simultaneous promotion conjunction, immutable artifact workflow, and focused
adversarial tests described by the parent feature.

## Required corrections

- Refit the typed discovery/certification/interval/amplification chain from the injected origin
  snapshot, require exact clock/config/corpus/pair/draw identities, and prove every selected outcome
  is strictly before the exclusive origin.
- Canonicalize mapping rows without comparing dictionaries and bind evaluation to the exact
  protocol, fold, horizon, case manifest, action universe, and support thresholds.
- Compute proper scores, calibration, predictive interval behavior, service coverage, and decision
  regret from common cases and aligned whole-event evidence. A refusal must execute the frozen
  current-only action while retaining the challenger all-case forecast.
- Evaluate all useful-coverage and non-degradation clauses from values and paired simultaneous
  bounds, producing all five statuses honestly and deterministically.
- Add the content-addressed validation bundle/store and explicit plan/freeze/evaluate/aggregate/
  proposal workflow or CLI boundary without any latest alias or promotion actuator.
- Replace placeholder protocol identities/folds with a self-consistent immutable protocol and add
  adversarial tests for cutoff leakage, identity mismatch, support censoring, negative evidence,
  inconclusive bounds, successful promotion assessment, draw integrity, multiplicity, store
  collision, CLI/workflow behavior, and old benchmark compatibility.

## Acceptance

- Every blocker in the parent feature's standard-review findings has a direct regression test.
- A real file-backed origin run reaches a sealed typed prediction bundle only after the entire
  pre-origin evidence chain completes; future mutations cannot change its bytes.
- Predictive and decision evidence use the same model-independent future cases, shared event
  blocks, and frozen policy inputs, with current-only fallback cost represented.
- The gate can produce `promotable`, `negative`, `inconclusive`, `support-censored`, and `invalid`
  from complete clause ledgers, and only a promotable exact assessment can yield an inert proposal.
- Existing benchmark artifacts remain byte-interpretable and the broader recurrent/amplification/
  ranking regressions stay green.

## Implementation record

- **Execution capability:** current frontier implementation; the change spans temporal leakage
  boundaries, immutable evidence identities, predictive/decision uncertainty, and operator
  authority.
- **Review weight:** standard, inherited from the parent feature. The correction closes the
  independent review blockers; the integrated feature returns to `stage: review` for verification.
- **Primary implementation:** `advisory/recurrent_validation.py` now owns closed typed protocol,
  stage-chain, forecast/draw, future-case, predictive, decision, promotion, proposal, and bundle
  contracts. `workflows/recurrent_validation.py` supplies the honest injected refit orchestrator,
  cutoff snapshot construction, and content-addressed origin/evaluation/bundle/proposal stores.
- **Operator surface:** `advise recurrent-validation plan|freeze|evaluate|aggregate|proposal`
  exposes the artifact lifecycle without `run`, `latest`, apply, winner selection, or active-config
  mutation.
- **Immutable inputs:** added a preregistered future parent benchmark plan and a self-consistent
  recurrent protocol bound to its exact protocol, fold, B&R, taxonomy, calibration, interval,
  structure, and amplification hashes. Historical v1 benchmark artifacts and registries were not
  modified.
- **Identity hardening:** sealed origins, future-case manifests, predictive/decision branches,
  candidate configs, aligned draws, evaluations, and validation bundles revalidate their derived
  identities. Invented support, divergent field mass, branch mixing, and artifact collisions fail
  closed.
- **Simplification:** one estimator-independent future-case ledger feeds both evidence branches;
  one frozen registry drives prediction grids, assessments, and bundle validation; one injected
  executor protocol isolates the repository from a speculative generic benchmark framework.
- **Design discrepancy:** the originally checked-in placeholder/backdated protocol could not
  honestly preregister future evidence. The correction adds a new parent protocol whose six folds
  begin after registration, rather than weakening registration or minimum-origin checks.
- **Adjacent test debt repaired:** normalized the repository's mixed `tests.*` and sibling-module
  fixture imports so the full suite collects without changing production behavior.

## Verification evidence

- Recurrent correction suite: `35 passed`.
- Recurrent plus interval/amplification integration slice: `66 passed`.
- Full repository suite: `3982 passed, 1 skipped`.
- Adjacent matchup/ranking/advisory CLI regression slice: `505 passed`.
- Ruff: all correction source/tests pass; `cli.py` passes with only the repository's existing
  `F821,F541` baseline ignored.
- Compileall: recurrent advisory/workflow and CLI modules pass.
- Knowledge-index regeneration: `0 errors`; six pre-existing advisory warnings remain.
- Mandatory documentation re-audit after fixes: `0 Critical, 0 High`; report at
  `doc-review-report.md`.

## Commits

- `03df4d5` — cutoff-safe recurrent origin refit and typed contracts.
- `805467e` — adversarial scoring, decision, promotion, and store gates.
- `1d4c106` — content-addressed workflow and CLI surface.
- `1867707` — exact sealed/evaluation/bundle identity enforcement.
- `d54fed3`, `7635d7c` — honest shared test-package collection.
- `4f0a43b`, `d5202f7` — documentation alignment, index regeneration, and doc-review closure.
