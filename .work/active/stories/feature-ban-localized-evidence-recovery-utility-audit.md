---
id: feature-ban-localized-evidence-recovery-utility-audit
kind: story
stage: done
tags: [analytics, advisory, testing, docs]
parent: feature-ban-localized-evidence-recovery
depends_on: [feature-ban-localized-evidence-recovery-refresh-publication]
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-08-16
---

# Current-corpus utility audit and adversarial localized-ban regressions

## Brief

Implement Unit 4 of the parent feature: lock in the Monday, August 17, 2026 degraded baseline and
prove that localized evidence recovery increases usefulness without globally widening authority.

The audit must name before/after active-row estimate coverage, recovered direct match cells,
affected/unaffected edge behavior, and any usefulness or authority status change on the current
Fantasticar corpus.

## Implementation notes

- Locked the degraded baseline at 0/50 proof-grounded supported parent rows with no visible direct
  estimate. The August 16 live corpus (exclusive cutoff August 17) now publishes direct estimates
  for 50/50 supported rows across 2,716 matchup cells.
- Recovered 9,949 unique clean-history physical matches beyond current-only evidence. The
  observation-based cell audit records 745 estimates with selected localized history and 1,971
  current/certified estimates; proof remains separately and honestly 0/50 with no proof-grade call.
- Preserved current post-ban field shares: 197 observed decks since August 10, 2026. The practical
  diagnostic call is Show and Tell; no proof-grade call is published at 0/50 grounded rows.
- Kept the complete typed evidence surface in library/store APIs while projecting only four
  highest-share opponent ledgers per supported row into the offline page. Raw match-id arrays are
  replaced by counts/digests and the global pair universe is omitted.
- The final report is 38,637,569 bytes (200 parent + 95 camp detailed ledgers), versus the rejected
  538,582,790-byte full-pair draft and the prior roughly 34MB report.
- Fantasticar boundary, unaffected-retention, exact gap, no-duplicate/reverse-derived, camp-current-
  only, automatic-target, mismatch-refusal, DOM copy/column arithmetic, and authority-invariance
  regressions are covered by focused tests.

## Verification evidence

- `.venv/bin/pytest -q tests/test_refresh_best_call_ranking.py
  tests/analytics/amplification/test_best_call_evidence.py
  tests/analytics/eras/test_interval_consumption.py` — 79 passed.
- `.venv/bin/pytest -q` — 4,002 passed, 1 skipped.
- Live current generation — corpus max 2026-08-16, exact interval 61.6s, compact projection 5.8s,
  serialization + atomic write 0.3s; zero expanded observations inside typed localized gaps.
- Controlled interval benchmark — parent 24.284s, camp 34.954s, 59.2s combined with exact parity.
