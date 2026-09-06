---
id: epic-best-deck-decision-trust-review-fixes
kind: story
stage: done
tags: [analytics, advisory, honesty, testing, players, privacy, docs]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close aggregate best-deck decision-trust findings

Implement the receiver-confirmed cross-feature findings from the epic's one standard aggregate
review, then execute the real-corpus future-only benchmark without retrospective tuning.

## Acceptance criteria

- [x] Retrospective origin snapshots reclassify training decks through pinned parent rules (or fail
      exact stored/replayed parity), and stored-label mutation cannot change frozen predictions.
- [x] One shared production recommendation function owns grounded/current/Agency ordering; page and
      benchmark parity holds when a stale grounded deck has higher Agency than a current one.
- [x] Player fit-summary counts below the privacy floor serialize/render as suppressed nulls while
      sufficient aggregate counts remain available.
- [x] Benchmark frozen methodology evidence computes the true uniform strict-common-era diagnostic
      or emits a named unavailable reason; it never relabels adaptive sources as strict-common.
- [x] Page and runbook display benchmark validation state and artifact identity, with honest defaults
      for not-run/not-evaluable/descriptive/predictive-claim-supported.
- [x] The preregistered benchmark is executed against the current repository corpus after fixes;
      artifacts are local/immutable, their ids and claim status are recorded in durable story/epic
      evidence, and no estimator/threshold is changed in response to outcomes.
- [x] Cross-feature focused tests and the full repository suite are green; knowledge/docs checks pass.

## Review closure contract

This story is the named fix set for a `standard`-weight epic review. Green verification and honest
empirical execution return the epic directly to `done`; do not run a second independent review pass.

## Implementation checkpoint (2026-08-11)

- Retrospective snapshots now replay every pre-cutoff deck through the hash-pinned parent rules and
  fingerprint raw training facts independently of mutable stored labels. An adversarial stored-label
  mutation produces the same manifest and frozen prediction content.
- `production_recommendation_order` is the single page/benchmark policy: grounded and at least five
  decks in the frozen trailing 28-day corpus wins over a stale grounded row even when the latter has
  higher Agency; Agency orders only within the honesty tier.
- Player fit summaries emit `null` and render `suppressed` for repeat/familiarity counts below the
  protocol privacy floor. Sufficient aggregate counts remain available.
- Benchmark methodology now rebuilds one uniform strict-common matrix at the maximum effective
  source horizon and names the no-resolved-cell case instead of relabeling adaptive evidence.
- Page generation accepts an explicitly supplied canonical benchmark summary, content-hashes it,
  and renders its status/reason/id. The no-artifact default is `not-run`; malformed evidence fails.
- Focused cross-feature verification: `101 passed`. Changed production lint and diff checks pass;
  knowledge-index regeneration reports 0 errors and 11 pre-existing advisory warnings.
- The real-corpus protocol/run follows after this checkpoint so each prediction records the repaired
  code commit. The registered schedule is fixed before observing results: cutoff 2024-12-16 through
  exclusive bound 2026-08-06, retrospective fixed-parent replay, default estimators/support/seed.

## Empirical execution and closure (2026-08-11)

Commands (source DB opened read-only; outputs under the ignored benchmark directory):

```bash
uv run --no-sync legacy-engine advise benchmark plan \
  --db /Users/andrewclark/dev/legacy-engine/data/legacy.duckdb \
  --protocol-id best-deck-decision-trust-current-corpus-v1 \
  --created-at 2024-12-16T00:00:00Z --first-cutoff 2024-12-16 \
  --until 2026-08-06 --taxonomy-mode retrospective-fixed-parent \
  --out /Users/andrewclark/dev/legacy-engine/data/benchmarks/best-deck-decision-trust-current-corpus-v1/protocol.json
uv run --no-sync legacy-engine advise benchmark run \
  --db /Users/andrewclark/dev/legacy-engine/data/legacy.duckdb \
  --protocol /Users/andrewclark/dev/legacy-engine/data/benchmarks/best-deck-decision-trust-current-corpus-v1/protocol.json \
  --artifact-dir /Users/andrewclark/dev/legacy-engine/data/benchmarks/best-deck-decision-trust-current-corpus-v1
uv run --no-sync python scripts/refresh_best_call_ranking.py \
  --db /Users/andrewclark/dev/legacy-engine/data/legacy.duckdb \
  --out /Users/andrewclark/dev/legacy-engine/data/benchmarks/best-deck-decision-trust-current-corpus-v1/best-call-ranking.html \
  --benchmark-summary /Users/andrewclark/dev/legacy-engine/data/benchmarks/best-deck-decision-trust-current-corpus-v1/summary.json
```

- Protocol/artifact id: `6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561`;
  24 folds planned across the fixed schedule.
- Summary artifact id: `42e0e6f643b7f32df1e19760c30ad0fb28a19bb11c3871c27b3f52fc7e202083`;
  status **not-evaluable**, 0 completed/evaluable folds and 0 represented regimes.
- Execution stopped before the first frozen prediction because snapshot closure found 615 rows (one
  unique name, `_____ Goblin`, across 615 decks) without observed card metadata. This is preserved as
  the primary summary reason; no source data, rules, thresholds, estimators, or protocol fields were
  changed. Backlog capture: `idea-missing-goblin-card-metadata`.
- The generated evidence page embeds that exact not-evaluable summary id and separately reports the
  shared-policy current call (`White Beanstalk`). Current-call output is therefore descriptive, not
  a supported predictive claim. Historical replay execution occurred after the outcomes; the frozen
  origin timestamp is reproducibility metadata, not a claim of contemporaneous preregistration.
- Verification: focused cross-feature suite `101 passed`; full repository suite `3713 passed, 1
  skipped`; changed production lint and diff checks pass. Knowledge index: 0 errors, 11 existing
  advisory warnings after regeneration.
