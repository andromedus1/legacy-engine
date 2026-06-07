---
id: epic-advisory-output-honesty-coverage-consumers
kind: feature
stage: drafting
tags: [advisory, analytics, correctness]
parent: epic-advisory-output-honesty
depends_on: [epic-advisory-output-honesty-positioning-coverage]
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Coverage Honesty Across the Remaining Positioning Consumers

## Brief

`epic-advisory-output-honesty-positioning-coverage` made the single-deck `positioning_score` honest
(auto-restrict to the covered sub-field, refuse at zero coverage), but the coverage-honesty did not
propagate to the *other* surfaces that read S. This feature closes that gap so the toolset is
internally consistent — a user must never see two different "S" for the same deck at the same
coverage.

Primary issue (Important, from review of the foundation feature): the `--candidates` **ranking path
(`rank_decks`) still computes and prints a raw full-field S** (pulled toward 0.50 by imputation),
which contradicts the single-deck `advise positioning` output that now says "S vs covered sub-field".
Note the design tension: `rank_decks` deliberately uses a *shared* sampled field across all candidates
to make P(best) honest, so per-deck restriction is NOT a drop-in — the fix is likely to
annotate/caveat (or suppress) the S column for low-coverage decks rather than restrict each deck to a
different field. The feature design pass must resolve this without breaking the shared-field MC.

Also folds in the coverage-honesty nits surfaced in the same review:
- **`PositioningResult.imputed` is misleading when `restricted=True`** — it still lists the dropped
  no-data opponents and the "imputed N no-data opponent(s)" warning still fires, but the restricted S
  imputed nothing (those were excluded). Clear/relabel `imputed` (or suppress the warning) when
  restricted.
- **`advise report` audit line prints `s_mean=nan`** when `s_computable=False` (the user-facing render
  is correct; only the diagnostic audit line is ungated).
- **`generation/tuning.py` carries NaN into the tune result's `positioning_s`** when a tuned archetype
  has zero coverage (was ~0.50 before). Fall back to `None` when `not s_computable`. Context-only
  (not a swap driver), but it leaks NaN into displayed/serialized tune output.
- **`viz/deck_dashboard.py`** reads S from `rank_decks` (un-restricted), so it inherits the same
  ranking-path inconsistency — make it consistent with whatever the ranking-path fix chooses.

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: follow-up to `positioning-coverage` — extends its honesty to the ranking, audit,
  tuning, and viz consumers. Filed from the foundation feature's fresh-context review.

## Inherited design decisions
- The single-deck `positioning_score` restriction semantics (auto-restrict < 0.85, refuse at zero
  coverage) are fixed; this feature makes the OTHER consumers consistent with them, NOT re-litigate
  them.
- `rank_decks`' shared-field MC for honest P(best) is load-bearing — do not break it to restrict S.
