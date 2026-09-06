---
id: epic-recurrent-stable-era-evidence-discovery-review-corrections
kind: story
stage: done
tags: [analytics, testing, perf]
parent: epic-recurrent-stable-era-evidence-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Correct recurrent discovery review failures

## Scope

Repair the receiver-confirmed standard-review findings without widening discovery into
certification or outcome-bearing analysis.

## Acceptance criteria

- A hard semantic boundary splits at its exact effective date (or otherwise represents the exact
  partial-bucket contract) and segments on opposite sides always carry incompatible epochs.
- Field/source distance uses mathematically coherent union-vocabulary smoothing; wholly disjoint
  distributions cannot pass the shipped v1 thresholds.
- The persisted v1 method and calibration describe the executed segmentation. Every declared
  feature weight, including subject share, participates and is covered by an adversarial test.
- Current-corpus execution pre-indexes counts, calendar buckets, membership, and reusable
  vocabulary so eligibility and per-entity segmentation avoid nested fleet-wide scans.
- Historical segments independently satisfy the configured bucket-duration floor before
  nomination.
- Tests cover outcome mutation invariance, exact mid-bucket hard boundaries, disjoint sideboard /
  mixture / field / source channels, complete-link anti-chaining, support floors, non-hard evidence,
  immutable collision/tamper refusal, and the corrected method identity.
- Focused discovery tests, the full era suite, Ruff, compileall, and a representative current-corpus
  runtime check pass. No `uv.lock` change is included.

## Review origin

Created from the single standard independent review of the parent feature on 2026-08-16. Once this
named fix set is green, the parent closes administratively without a second independent pass.

## Implementation notes

- Files changed: `src/legacy_engine/analytics/eras/discovery.py`,
  `src/legacy_engine/analytics/eras/discovery_source.py`,
  `src/legacy_engine/data/eras/discovery-v1.json`, and focused discovery tests.
- Corrected exact hard-boundary bucket starts/epochs, union-vocabulary smoothing with explicit
  disjoint-support rejection, subject-share participation, historical duration floors, and a
  shared one-pass corpus index for fleet eligibility/buckets/vocabulary.
- Replaced the heuristic boundary detector with declared
  `ruptures.KernelCPD(kernel="cosine")`, versioned as
  `segment-fingerprint-complete-link-v2` with `recurrent-segment-fingerprint-v2` calibration.
- Verification: focused discovery tests — 15 passed; full `PYTHONPATH=. .venv/bin/pytest -q
  tests/analytics/eras` — 184 passed; discovery-owned Ruff and compileall checks passed; the
  indexed synthetic corpus check completed successfully. The pre-existing `uv.lock` remains
  untouched.
- Adjacent shared-file issue: certification partition edits remain uncommitted in
  `discovery_run.py`; this correction does not stage or alter those hunks.
