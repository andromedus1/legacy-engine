---
source_handle: superrep-psis-influence
fetched: 2026-08-01
source_url: https://www.jmlr.org/papers/v25/19-556.html
provenance: source-direct
substrate_confidence: source-direct
---

# Pareto Smoothed Importance Sampling

## Summary

Vehtari and colleagues analyze instability in importance-weighted estimates when a few ratios have a
heavy right tail. They propose Pareto smoothing, an effective-sample-size estimate, Monte Carlo error
estimates, and the Pareto-k diagnostic. The diagnostic identifies cases where an approximation is
dominated by a few draws or where finite-sample convergence is unreliable. The paper presents the
diagnostic as broadly useful for Monte Carlo estimators and as infrastructure for efficient
leave-one-out model assessment.

## Key passages

- Abstract: importance weighting can become highly variable when importance ratios have a heavy
  right tail.
- Abstract: the method includes stabilized effective sample size, Monte Carlo error, and convergence
  diagnostics.
- §1, PDF pp. 1–2: a few ratios can dominate an estimator even when its theoretical variance is
  finite, motivating built-in error assessment.
- §1: Pareto-k is proposed as a finite-sample convergence-rate diagnostic and underlies efficient
  leave-one-out implementations.

## Structural metadata

Peer-reviewed JMLR article, volume 25, article 72 (2024). Full PDF and abstract page fetched.
