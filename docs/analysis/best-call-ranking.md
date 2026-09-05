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
  - "scripts/evaluate_deck_rankings.py retains its retrospective field diagnostic. Separate --served-model phases seal all six predictions before development scoring and require a sealed development selection before confirmation outcomes open; no phase publishes a method."
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

## Expected-field reports

Use the same projection for a private expected field by supplying a separate output:

```bash
.venv/bin/python scripts/refresh_best_call_ranking.py \
  --field decks/local-field-saved-post-may18-107.txt \
  --field-label "Saved post-May 18 field (107 players)" \
  --out decks/deck-rankings-local-saved.html
```

The saved sample has no supplied end date and is historical evidence scored with the current model;
its 107 counted players include four explicitly unmapped Affinity Combo players. The input uses the
established `<share> <archetype> [count]` grammar. Every row must include a count for a supplied-
observation scenario; `# effective_n` instead declares concentration, and rows without either remain
fixed weights.

The page records the file hash, evidence basis, unknown opponents, and global-versus-scenario
performance/floor calls. Scenario shares and counts reweight the existing cells; global current-corpus
presence still determines which decks can be recommended, so a playable deck need not appear among
the expected opponents. Positive unknown mass remains as weak-prior cells. Strategic-plan shares stay
visible, but every local plan projection is explicitly unavailable because the global plan cells
cannot be coherently reweighted within plan composition. Custom runs cannot replace
`decks/deck-rankings.html`, and refresh comparisons require the same scenario identity.

## Refresh changes

After projecting the current page, the publisher reads the prior page's embedded JSON without
executing the HTML. Compatible snapshots share method, scenario, regime, and field start. The page
shows at most three observations: largest visible field movement, largest modeled performance
beneficiary, and changed performance/floor calls. For each candidate with the full union of required
opponent forecasts, performance movement is exactly decomposed into symmetric field-weight and
matchup-estimate terms. A floor explanation names a changed minimum pairing or positive-support set;
field-share magnitudes do not explain floor movement when opponent support is unchanged.

First publication starts a baseline; analytically equal inputs report no change. Incompatible or
malformed prior payloads and missing forecasts remain explicit while the new page stays publishable.
The comparison snapshot uses the same atomic HTML publication, and refresh diagnostics are excluded
from the ranking-authority invariant.

## Build decision units

Expanded parent rows compare at least two current camp rows on the full positive-share external-opponent
set, excluding the parent. The disclosure separates pure pooling uplift—minimum of the camp-weighted
matchup vector minus the weighted camp minima—from the actual parent/build floor gap, which can also
reflect priors or evidence windows. Missing opponent cells remain unavailable. Camp weights,
common-opponent field coverage, toughest pairing, n, and prior fraction stay visible, including `n=0`
cells.

Composition uses `0.5 × Σ|mean copies A − mean copies B|` separately for main and side decks, with
within-camp radius and separate main/side card-record denominators. Pilot overlap uses source-scoped
normalized handles, reports known and missing-handle denominators, and is unavailable if either build
has no known pilot. The disclosure never promotes a camp or changes the parent call. For a
read-only JSON or Markdown audit of the generated page, run:

```bash
.venv/bin/python scripts/analyze_decision_units.py \
  --db data/legacy.duckdb --report decks/deck-rankings.html --format markdown
```

The 2026-08-10 through 2026-09-04 audit found 29 parents and 16 exact two-current-build comparisons.
The largest grounded pure pooling uplifts were Jeskai Midrange 3.62pp, Azorius Midrange 2.28pp,
Show and Tell 1.94pp, and Dimir Tempo 1.13pp; these point-estimate diagnostics did not change taxonomy.

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

`scripts/evaluate_deck_rankings.py` has two retrospective modes. The default field diagnostic still
scores fixed 14-, 28-, 56-day, and uniform methods on chronological complete-day folds without
tuning; its optional matchup pass remains the limited pre-cutoff adaptive baseline.

`--served-model --output-dir <path>` instead evaluates the current Deck Rankings projection through
optional `--phase freeze|development|confirmation|all`; the default is `development`. Freeze only
seals artifacts. Development creates raw pre-cutoff snapshots and seals predictions for all six
declared origins before loading outcomes for its first three. Confirmation validates and reuses that
exact configuration, requires `--selected-method <method>`, writes an immutable development-selection
artifact, and only then opens the final three horizons. `all` is the combined convenience phase and
also requires the selected method.

The taxonomy is parent-only but includes the production color split that labels Energy as Boros
Energy or Mardu Energy. Parent rules and the color-split registry are hash-pinned across freeze and
evaluation; camps are disabled. Card availability is observed-by-cutoff where release dates are
unavailable, and retrospective fixed-parent labeling does not reconstruct the label knowledge an
operator had at the cutoff. The same outcome-blind card-metadata quarantine applies to training and
held-out data for every method, with hard ceilings of `.5%` of decks and `2%` of rounds. Raw and
retained denominators, evidence, and hashes remain visible; quarantine excludes unresolved whole
decks rather than repairing metadata.

The declared comparison includes production scale `1`, fixed prior-strength sensitivities `.5` and
`2`, and `opponent-plan-prior-v1`. The challenger conditionally borrows a prior from cutoff-safe
evidence for opponents assigned to the same primary strategic plan while preserving each target
cell's direct wins/n and selected-source identity. Outputs retain source/config hashes and report log
loss, Brier score, calibration, support strata, reciprocity, paired event log-loss differences,
performance/floor order, and later support for the baseline's named floor pairings. Missing forecasts
and unavailable floor outcomes stay visible. Each frozen cell also carries the exact selected view,
its observation match-id digest, admitted components and windows, analysis clock, status, and
concentration evidence. Existing predictions are reused only when their fold, protocol, requested
scales/draws, taxonomy, quarantine policy, strategic-plan registry, manifest, snapshot, and artifact
hashes still match.

Development scored 347.5 weighted half-match cases and selected scale `2`: log loss was `0.690337`
versus `0.696988` for scale `1`, and Brier was `0.248590` versus `0.251759`. Confirmation scored 92
weighted cases and slightly reversed that result: scale `1` had log loss `0.685469` and Brier
`0.246262`, versus `0.686405` and `0.246695` for scale `2`. The independent scale-`2` leaders stayed
unchanged at all six origins; scale `.5` and the plan challenger changed calls but did not improve
the proper scores. Production therefore retains scale `1`. The generated page may load the sealed
confirmation artifact into its Method disclosure; the evaluator has no publication or deployment
gate.

The operational status schema may report `useful` when the generated artifact contains supported
performance/floor estimates and a practical call, even when evidence is thin or the current method
has no validation claim. Inspect `legacy-engine ops status` for the artifact path, digest, utility
summary, and any pending action before intervening. `effective_observed` is the recency-weighted
observed ESS; prior pseudo-lists stay separate. The legacy integer total remains in stored status.

## Related code and docs

- `src/legacy_engine/advisory/deck_ranking.py` — posterior rows, intervals, floor, and Pareto status.
- `src/legacy_engine/advisory/recent_field.py` — dated field observations and evidence accounting.
- `src/legacy_engine/advisory/field_scenario.py` — private expected-field validation and provenance.
- `src/legacy_engine/advisory/ranking_changes.py` — successive-publication comparison and attribution.
- `src/legacy_engine/advisory/decision_units.py` — parent/build floor, composition, and pilot diagnostics.
- `scripts/refresh_best_call_ranking.py` — legacy ledger plus current projection and publication.
- `scripts/refresh_decision_data.py` — full refresh composition and default publication path.
- `scripts/evaluate_deck_rankings.py` — default field diagnostic and frozen served-model evaluation.
- `src/legacy_engine/advisory/deck_ranking_projection.py` — shared production/evaluation projection handoff.
- `src/legacy_engine/workflows/deck_ranking_evaluation.py` — freeze-before-outcomes artifact and scoring workflow.
- [README.md](../../README.md) — user-facing commands and local refresh overview.
