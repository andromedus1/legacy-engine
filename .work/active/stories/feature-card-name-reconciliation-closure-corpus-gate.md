---
id: feature-card-name-reconciliation-closure-corpus-gate
kind: story
stage: done
tags: [ingestion, data-quality, benchmark, docs]
parent: feature-card-name-reconciliation-closure
depends_on: [feature-card-name-reconciliation-closure-cutoff-preflight]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Gate benchmark launch on full-corpus metadata closure

## Brief

Implement Unit 3 from the parent design: integrated CLI assertions, current-state documentation, and
fresh derived-copy evidence. Restart the unchanged benchmark only when every planned training cutoff
has zero metadata gaps.

## Acceptance criteria

- The parent Unit 3 acceptance criteria are green.
- Focused and full repository verification pass.
- The durable evidence truthfully records either benchmark launch/artifact identity or the exact
  nonzero closure reason.

## Implementation notes

- Execution capability: direct cohesive implementation; the cross-CLI contract, rolling docs, and
  fresh-copy evidence form one launch-gate checkpoint.
- Review weight: standard, inherited from the parent feature/default project policy.
- Files changed: `tests/test_ranking_benchmark_cli.py`, `docs/ARCHITECTURE.md`,
  `docs/analysis/best-call-ranking.md`, and generated knowledge-index layers.
- Tests added: a cross-feature blocked-to-cleared handoff proves the preflight preserves frozen
  protocol bytes and clears only after card metadata exists.
- Simplification: the documented benchmark runbook now has one explicit zero-required-gap gate
  instead of relying on serial benchmark failures.
- Discrepancies from design: the benchmark was not restarted because the required gate was nonzero,
  exactly as designed.
- Fresh-copy evidence: after scheduler writer PID 76214 closed, a byte-copy at
  `data/benchmarks/best-deck-decision-trust-current-corpus-v1-closure-gate/reconciled-corpus.duckdb`
  matched live-source SHA-256 `abb9cfc628335609ff063a1ed50c3463faf26021b97d4cf866366e7bdf098d7e`.
  Normal reconciliation used alias snapshot `2026-08-11T21:18:07.865+00:00` (241,911 unique
  aliases; 457 ambiguous keys). Preflight against unchanged 13,397-byte protocol hash
  `6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561` found 60 rows / 53
  names in planned-cutoff cohorts and 2 rows / 2 names after the last cutoff. The earliest blocker
  is `Explosao Elemental do Vermelho` at cutoff 2025-08-18.
- Benchmark launch: not run; exact reason is the nonzero planned-cutoff closure gate. No protocol,
  estimator, raw cache, or live database was changed.
- Verification: reconciliation/coverage/benchmark CLI focused suites pass (`31 passed`).
- Adjacent issues parked: none; the named fail-closed evidence queue remains intentional feature
  output rather than speculative mappings.
