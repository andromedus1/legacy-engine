---
source_handle: recurrent-consume-sklearn-timeseries
fetched: 2026-08-13
source_url: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
provenance: source-direct
substrate_confidence: source-direct
source_class: official-documentation
---

# scikit-learn TimeSeriesSplit documentation

## Summary

The official scikit-learn documentation defines forward time-series splits so that training
observations precede test observations, with expanding training windows and an optional gap. It
also states an equal-spacing condition for comparable fold metrics.

## Key passages

1. The class is intended for time-ordered data because ordinary cross-validation can train on
   future observations and evaluate on past observations (lines 633–640).
2. In split `k`, the first `k` folds train and the next fold tests; successive training sets are
   supersets of earlier ones (lines 640–642).
3. The documentation requires equally spaced samples for directly comparable fold metrics so that
   test folds cover equal durations (lines 638–640).
4. `gap` excludes observations between the end of training and the beginning of testing, and the
   example demonstrates the excluded indices (lines 671 and 724–738).

## Structural metadata

Official scikit-learn API documentation for `sklearn.model_selection.TimeSeriesSplit`.
