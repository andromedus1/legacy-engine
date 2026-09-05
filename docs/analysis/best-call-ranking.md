---
description: Read before refreshing or interpreting the Deck Rankings page — the current performance and matchup-floor projection, its field basis, and its evidence boundaries.
type: design
kind: planning
status: active
updated: 2026-09-05
summary: |
  Runbook for decks/deck-rankings.html, a self-contained generated landing page. The
  refresh script retains the mature Best Call evidence ledger and adds a separately
  named current projection whose two visible priorities are full-field performance
  and the highest worst-matchup floor.
decisions:
  - "Performance is the field-share-weighted mean of per-cell posterior means, including structural 50% mirrors; floor is the minimum posterior mean across non-mirror current-field opponents."
  - "The performance interval and all-opponent minimum-floor interval use seeded posterior draws; the visible floor range is the named toughest pairing's cell interval, while the all-opponent minimum interval remains available in evidence details."
  - "Performance and floor have independent leaders. The floor leader maximizes the floor among eligible rows, with performance breaking floor ties; both are independent table sorts, and Pareto rows show the efficient frontier."
  - "Every valid cell contributes an estimate. Prior-only and uncertain cells remain visible with W-L/n, interval, prior strength, prior provenance, source kind, and source window; prior-only rows are not recommendation candidates."
  - "The current field uses a provisional 28-day exponential half-life over the observed ban-regime slice. The denominator is published deck lists, not a census of entrants. Integer observed counts, decay-weighted counts, effective sample size, and bounded transition prior counts remain separate."
  - "Clean interval evidence may override a cell once. The override keeps the actual MatchupCell prior_strength and its interval/source provenance; it is not pooled again with overlapping fallback evidence."
  - "The mature positioning estimator and future-only benchmark remain frozen reference surfaces. Their outputs do not validate or promote this current descriptive projection."
  - "scripts/evaluate_deck_rankings.py is a retrospective diagnostic: it compares fixed field half-lives chronologically and optionally scores a limited matchup baseline. It is not an exact production replay or a deployment gate."
  - "The generated page is disposable. Edit the tracked script or template, then regenerate decks/deck-rankings.html; do not hand-edit the output."
---

# Deck Rankings — refresh runbook

The generated page is [decks/deck-rankings.html](../../decks/deck-rankings.html). It is offline,
self-contained, and gitignored. The tracked implementation is
`scripts/refresh_best_call_ranking.py` plus `scripts/best_call_ranking_template.html`.

## Refresh

For the complete data lifecycle, run:

```bash
.venv/bin/python scripts/refresh_decision_data.py
```

That composed command refreshes sources and cards, reconciles names, labels decks, applies staged
camps, runs era detection, and writes the ranking last. It uses the default output above and leaves
the previous page in place when a required step fails. Release and format-monitor degradation is
reported in typed status; it does not silently claim a fresh ranking.

For a focused ranking rebuild after its inputs are already current:

```bash
.venv/bin/python scripts/refresh_best_call_ranking.py
```

The script name is retained for callers and scheduler wiring. `--db` and `--out` remain available;
the default output is `decks/deck-rankings.html`. Historical target flags still produce exclusive-
cutoff “Today’s model” pages using current taxonomy/configuration, with optional interval evidence
attached diagnostically.

## Current projection

`src/legacy_engine/advisory/deck_ranking.py::rank_matchup_rows` receives the typed matchup ledger
and field shares. For each row it computes a conditional Beta posterior from `wins`, `n`,
`prior_mean`, and the cell’s actual `prior_strength`. A supplied cell with zero direct results retains its fitted prior; only an absent ledger cell
uses a weak Beta(1, 1) 50% prior. The cell’s analytic posterior mean is the point estimate. Draws use the same posterior and
seeded RNG to produce 95% performance intervals, 95% minimum-floor intervals, probability that
performance exceeds 50%, and expected exposure to cells below the descriptive 45% marker.

Performance is the weighted mean over the complete field. A structural mirror is fixed at 50% and
is included in performance. The floor is the minimum point estimate over non-mirror opponents with
positive field share; its draw interval takes the minimum across those same opponents on each draw.
The floor does not claim that unobserved opponents are safe. The page shows the direct-evidence
share and every cell’s estimate so missing and uncertain parts of the floor can be inspected.

`_publish_deck_rankings` in `scripts/refresh_best_call_ranking.py` supplies the current field from
`src/legacy_engine/advisory/recent_field.py::build_recent_field`, then applies each available clean
interval cell as one override. It preserves interval/source notes and the overridden cell’s prior
strength. Era evidence is preferred when present; fallback is used only when era evidence is absent,
and overlapping sources are not combined a second time.

The field projection uses the half-open `[field_since, corpus_max + 1 day)` window and a provisional
28-day half-life. `RecentField` records exact integer sightings, weighted counts, Kish effective
sample size, source composition, camp fractions, and recent-vs-previous movement. The source
denominator is explicitly `published-list`; completeness of those lists is unverified. Transition
support contributes bounded integer prior counts to effective field concentration while remaining
separate from observed counts and recent presence.

The page opens with two equal-priority cards: the performance leader and the independent floor
leader. Performance breaks ties among equal floors. The visible floor range names the toughest
pairing's cell interval; the all-opponent minimum-floor interval remains in evidence details.
Coverage/n controls filter the shared view; n defines which matchups count toward coverage.
The map marks tradeoffs among shown decks, with hover/focus/tap tooltips. The strategic-plan, archetype, and camp
surfaces remain available, with camps retaining their parent/camp presentation and plan cells
remaining direct match aggregates.

## Evidence and interpretation

There is no point-estimate threshold that suppresses a new projection estimate. A row can show
posterior values from direct evidence, clean historical evidence, or fitted/weak priors without direct results.
Rows without direct support are labeled `prior only` and are excluded from the two calls; inactive
classifier labels retain their field context but are not current deck recommendations. Expand a row
to inspect opponent, field share, posterior interval, W-L/n, source window, prior source, and clean
interval concentration details.

Floor coverage is the non-mirror field-share fraction meeting the chosen minimum matchup n.
Coverage filters select rows; posterior estimates and intervals retain their original definition. Intervals are conditional on supplied
priors and do not include every model, selection, event, or source-concentration uncertainty.

The existing `advisory/positioning.py` estimator and its CLI remain available with their established
adaptive field/matchup windowing and `--provenance` options. They are a legacy reference surface;
their Agency/P(best) terminology must not be read as the definition of the Deck Rankings page.
Likewise, the future-only ranking benchmark evaluates its preregistered legacy estimators and does
not certify this new current method.

`scripts/evaluate_deck_rankings.py` is optional retrospective evidence. Its field pass scores fixed
14-, 28-, 56-day, and uniform methods on chronological complete-day folds without tuning. Its
optional matchup pass is limited to a pre-cutoff adaptive baseline and scores each unordered
holdout pair once; it is not an exact reproduction of the production page’s interval overrides,
field/prior composition, or recommendation projection.

The operational status schema may report `useful` when the generated artifact contains supported
performance/floor estimates and a practical call, even when evidence is thin or the current method
has no validation claim. Inspect `legacy-engine ops status` for the artifact path, digest, utility
summary, and any pending action before intervening. `effective_observed` is the recency-weighted
observed ESS; prior pseudo-lists stay separate. The legacy integer total remains in stored status.

## Related code and docs

- `src/legacy_engine/advisory/deck_ranking.py` — posterior rows, intervals, floor, and Pareto status.
- `src/legacy_engine/advisory/recent_field.py` — dated field observations and evidence accounting.
- `scripts/refresh_best_call_ranking.py` — legacy ledger plus current projection and publication.
- `scripts/refresh_decision_data.py` — full refresh composition and default publication path.
- `scripts/evaluate_deck_rankings.py` — retrospective diagnostic comparisons.
- [README.md](../../README.md) — user-facing commands and local refresh overview.
