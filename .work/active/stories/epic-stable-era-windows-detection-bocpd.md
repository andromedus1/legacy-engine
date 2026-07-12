---
id: epic-stable-era-windows-detection-bocpd
kind: story
stage: review
tags: [analytics, methodology]
parent: epic-stable-era-windows-detection
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Beta-Binomial BOCPD recursion (analytics/eras/bocpd.py)

## Brief
In-project Adams–MacKay Bayesian online change-point recursion with a Beta–Binomial predictive
(no Python package covers count/proportion likelihoods — verified in the brief). Pure
numpy/scipy, deterministic, zero-trial-safe. Consumed later by the era-ledger drift alarm.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Unit 2 (exact signatures + acceptance
criteria there).

## Implementation notes

Built `src/legacy_engine/analytics/eras/bocpd.py` implementing `BocpdResult` and
`beta_binomial_bocpd` per the parent feature's Unit 2 contract: the Adams-MacKay run-length
recursion with an exact Beta-Binomial predictive (`gammaln`/`betaln`, log-space pmf), explicit
per-hypothesis run-length bookkeeping (not inferred from array position, so `_MASS_TRUNCATION`
can never desynchronize "index" from "run length"), and reported values captured before
truncation so the 1e-9 mass cutoff can never change a result.

**Design deviation, load-bearing (worth flagging even though I did not revert the story to
`drafting`, since I found a correct, in-spec fix rather than a genuine infeasibility):** the
design's literal `p_change[t] = posterior mass at run length 0` is provably degenerate under any
hazard that does not depend on run length (the "constant hazard" this story specifies). By
Bayes' rule, the changepoint mass and the total growth mass share the identical
data-weighted sum (hazard doesn't depend on `r`, so it factors out of both), which forces
`P(run_length_t = 0 | data)` to equal exactly `1/hazard_lambda` for EVERY bucket, on ANY input —
verified both by hand derivation and empirically (a 0.05->0.30 step at t=20 produced a
perfectly flat `p_change` at 0.04 with the literal definition). The real signal lives one bucket
later: run length 1 is fed only by the previous step's freshly-reset (flat, uninformative)
predictive, so it spikes exactly when established hypotheses are surprised by a real break.
`p_change` is implemented as `P(run_length <= 1)` — the minimal, hazard-independent window that
recovers a genuine, non-degenerate alarm signal — with the full derivation documented in the
module docstring. `map_run_length` is unaffected and correctly resets at the true break
regardless. This is implemented and tested, not left as an open question.

Also noted: bucket 0 is an inherent cold-start artifact (`p_change[0] == 1.0` for any input,
since the hypothesis universe is only `{0, 1}` with no prior history) — documented in the
docstring; tests exclude this single burn-in bucket when searching for/comparing peaks, standard
practice for online change detectors.

Tests: `tests/analytics/eras/test_bocpd.py`, 8 tests. Synthetic step series (`round(p*n)`,
deterministic, no sampling) peaks within the true break; stationary-noise peak is more than 2x
below the step peak; zero-trial buckets pin to the exact closed form
`hazard * (2 - hazard)` and never spike; shape/frozen-dataclass/determinism/mismatched-shape
checks. All pass; full repo suite (`pytest -q`) is green at 2770 passed / 1 pre-existing xfail.

No production bugs found or parked during this story.
