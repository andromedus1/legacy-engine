---
id: story-fix-ranking-phase-markdown
kind: story
stage: done
tags: [analytics, advisory]
parent: feature-validated-historical-evidence-promotion
depends_on: []
release_binding: null
created: 2026-09-05
updated: 2026-09-05
---

# Preserve distinct Markdown artifacts for evaluation phases

## Symptom and root cause
The real development → confirmation CLI sequence successfully sealed all scores but exited with
`FileExistsError: refusing to overwrite different artifact: .../summary.md`. Both phases used
the same immutable Markdown destination, although their JSON destinations were distinct.

## Fix and verification
Use phase-specific Markdown paths, preserving the existing first-phase convenience summary.
Add a public orchestration regression that runs development then confirmation and verifies both
reports remain readable. Reproduce failure before repair; verify focused evaluator suite and
write the already sealed real confirmation artifact without recomputing or changing scores.
This child bug is covered by the parent feature's completed standard review and direct fix verification.

Verification: public development→confirmation regression failed with the original FileExistsError,
then passed after the phase-path repair. All 17 evaluator/integrated-freeze tests pass. Both actual
phase Markdown reports were recovered from unchanged sealed JSON scores; no outcomes were rescored.
