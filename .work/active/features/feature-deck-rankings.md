---
id: feature-deck-rankings
kind: feature
stage: review
tags: [analytics, advisory, ui]
parent: null
depends_on: []
release_binding: null
created: 2026-09-05
updated: 2026-09-05
---

# Deck Rankings: performance and matchup floor

## Brief
Implement the September 5 methodology review and Andrew's correction: performance and the highest worst-matchup floor are dual priorities. Make `decks/deck-rankings.html` the official refreshed landing page. Preserve the agency map, strategy/superarchetype table, archetypes, camps, and useful matchup dropdowns; remove repeated caveats and competing diagnostic columns.

## Design decisions
- User authorization: implement all review findings; keep performance and floor equally visible; preserve the existing visual direction and named surfaces, simplify their composition/copy.
- Directional alignment pass: no unanswered strategic questions. Existing report is the selected visual reference; prepare a concise refinement mock before production editing.
- Performance is the full-field posterior expected match win rate. Floor is the minimum posterior mean across non-mirror current-field opponents, with a posterior interval of the minimum. Show the efficient frontier/tradeoff rather than blending objectives or claiming no bad matchups are proven.
- Use every valid observation continuously. Evidence thresholds describe support; they do not suppress estimates or choose the source for the new decision view. Prior-only rows are visible but not recommended. Preserve integrity/ban boundaries.
- Current field uses exponential recency weighting (28-day half-life, explicitly provisional) on the observed ban-regime slice, retains bounded transition support, and labels the denominator as published lists unless completeness is established. Raw sightings stay exact and separate from effective evidence.
- One cell posterior supplies estimates, intervals, field performance and floor. Carry the actual prior strength; supplied zero-observation cells retain their fitted prior, while absent ledger cells use a weak 50% prior. Use compatible clean interval data once each when supplied; avoid pooling overlapping fallback/current evidence.
- Existing frozen benchmark estimators remain reproducible. Add a separately named current-method evaluation rather than attributing old validation to new rankings. Chronological scoring and sensitivity to field half-life compare against simple baselines; report results without a pass prerequisite for descriptive output.
- No new external dependencies. All changes reversible in a PR; preserve unrelated Hogaak research, indexes, and uv.lock edits.

## Architectural choice
Considered lowering old thresholds, adding another diagnostic toggle, or making a coherent dual-objective decision projection. Choose the latter: threshold lowering retains cliffs, and another toggle compounds report bloat. Reuse the typed source ledger and existing interval recovery; retain old benchmark code as a versioned evaluator, not the visible decision rule.

## Implementation units
1. `src/legacy_engine/advisory/deck_ranking.py`: `rank_matchup_rows(rows: Mapping[str, Sequence[RankingCellMeasurement]], shares: Mapping[str, float], *, counts: Mapping[str,float] | None = None, draws: int = 10000, seed: int = 730021) -> dict`. Serialize per-cell mean/95% interval/record/prior provenance plus row performance, floor and their intervals, evidence coverage, worst opponent and Pareto status. Add `prior_strength` to MatchupCell and populate it in build_cell. Test analytic posterior parity, weak/missing evidence, mirrors, no gate cliff, determinism, performance/floor disagreement, complete-field denominator and invalid inputs.
2. `src/legacy_engine/advisory/recent_field.py`: `build_recent_field(con, *, since: str, until: str, half_life_days: float = 28, provenance: str | None = None)`. Return weighted shares, concentration counts, exact observations, source composition, camp fractions and recent-vs-previous movement. Test time cutoff, age weights, source denominator, effective sample, camp reconciliation and ordering. Add chronological evaluation script for decision projection using pre-cutoff sources and holdout matches; no tuning on evaluated outcomes.
3. `scripts/refresh_best_call_ranking.py`, template, refresh/CLI/scheduler defaults: integrate new field and posterior; compact dual priorities, shared table sort, current presence filtering and readable dropdown ledger. Rename default output everywhere, retain historical filenames only in archival evidence. Rebuild actual report, inspect browser rendering/interactions, update README/foundations/runbook and regenerate knowledge index.

## Testing
Focused analytical and report tests, browser interaction verification with sparse data and both objectives, full pytest suite and CI. New statistics must reconcile with serialized cell means. Saved benchmarks are historical evidence, not a validation claim for the new method.

## Risks
- Conditional empirical-Bayes intervals do not include every model/selection uncertainty; explain once in methodology, keep observed event/source concentration visible.
- Minimum estimates over incompletely observed fields depend on priors; show unknown field share and wide intervals, never promise zero bad matchups.
- Existing fixtures encode old prose/order; update only assertions deliberately superseded by this approved contract.
- The failed refresh duplicate-key issue must be diagnosed and repaired through tracked bug work if reproduced; never silently assert data currency.

## Execution
One cohesive feature split by disjoint write ownership: posterior module/model, recent-field/evaluation modules, host generator/UI/refresh integration. Workers use Luna xhigh per implement-orchestrator; host retains integration context. Standard independent feature review after integrated verification. No child stories needed; ownership units are in this body and one feature commit captures integration.

## Mockups
Selected: option-1, clear priorities, explicitly approved by Andrew on 2026-09-05. Reference: `.mockups/screens/feature-deck-rankings/index.html`.

## Implementation and verification
- Implemented `deck-rankings-v1`: complete-field posterior performance, independent highest-floor leader, compatible history once per cell, exact prior strength, and recency-weighted published-list field. Legacy evaluators remain unchanged.
- Actual browser inspection confirmed desktop/mobile rendering, no page errors or horizontal overflow, search, independent sorting, matchup disclosures, and strategic-plan expansion. Floor display now pairs its point estimate with the named toughest-cell interval; draw-wise minimum uncertainty remains in evidence details. This presentation avoids conflating two distinct statistical quantities.
- Removed the arbitrary two-percentage-point performance restriction from the floor leader so the user’s priorities remain independent. Both calls are interpretable alongside the efficient frontier and direct-evidence share.
- The template and serialized reading payload omit retired diagnostic bloat; analytical return values preserve frozen legacy contracts.
- First full suite: 4,107 passed, 1 skipped, 2 exact-run fixture failures caused by mocking the old generator boundary. Fixtures now isolate exact-run attachment explicitly; focused integration/evidence verification passes after that repair. A new integration test proves legacy gate changes do not change current decisions, reconciles full-field means, and verifies toughest-cell intervals and the floor call.
- Fixed half-life evaluation: 105 chronological complete-day folds, 6,648 published held-out decks, requested 2026-05-18 through 2026-09-05. Mean log loss: 14d 4.40745, 28d 4.41766, 56d 4.42696, uniform 4.43926. Brier: .96414, .96503, .96557, .96619 respectively. This supports recency weighting descriptively; 28d remains provisional and was not retuned on these outcomes. No claim of production deck-ranking validation.
- A full scheduled refresh is running with the tracked duplicate-assignment recovery fix; status publication and final refreshed artifact remain to verify.

- Integrated report/evidence tests: 49 passed. Full rerun remains in progress. Scheduled refresh published a 5.25 MB report successfully (down from 41.47 MB), with 66 current archetypes and 53 camps. Its degraded status is due to four pre-existing/operator era-release alerts, not a failed pipeline step. Final browser checks passed at desktop/mobile widths.

- Final full local suite: 4,110 passed, 1 skipped (Python 3.13). New modules pass Ruff correctness rules. Knowledge index regeneration: 32 docs, 0 errors, 6 existing structural warnings.
- Independent review: attempted Claude Opus via peeragent, which failed before review because OAuth had expired; same-harness fresh-context Sol xhigh fallback is running.

## Review findings and corrections
- Regenerate from the final Python snapshot and recheck browser behavior/status digest. Earlier long-running refreshes had loaded source before late edits.
- Clarify supplied zero-observation cells retain fitted priors; absent ledger cells alone use Beta(1,1). Added a numerical regression, prior-floor badge and named toughest opponent on the floor card; corrected stale MatchupCell documentation.
- Add explicit `observed_field_ess` to utility status; raw observed and prior integer counts remain separate. Legacy integer totals retain their stored compatibility semantics but no longer stand in for current effective evidence in status/refresh text.
- Update current decks index and remaining live names. Mobile controls have 44px hit areas; the agency map scrolls at readable size instead of shrinking its type to approximately4px.
- CI exposed two non-hermetic pre-existing tests. The report integration test now injects the fixture’s staged parents instead of reading the ignored local registry. Removed an unused-file immutability test: it read an ignored historical protocol before and after a loader that never accesses that file; its missing data dependency failed clean checkouts and the test covered no loader behavior. Existing registered-protocol and base-hash tests retain the actual immutability/identity contracts.


## Independent review (2026-09-05)
Standard weight, exactly one completed fresh-context Sol xhigh pass over `b8c24fa..176ae76`;
preferred Claude authentication failed before reviewing. Initial verdict: request changes.
Accepted the two blockers (prior-floor disclosure and final source/artifact alignment) and all
three important findings (utility ESS accounting, mobile hit areas/chart legibility, canonical
entry points). The named code/docs/UI fixes are implemented; 98 focused tests pass. Final
scheduled regeneration, browser measurements, and CI remain closure requirements. No second
review pass is required. No deferred findings or backlog items remain from this review.


## User review refinement (2026-09-05)
Andrew requested restoring useful agency-map tooltips and the old floor-coverage/minimum-matchup-n
controls. Add shared view filters: n defines the support counted toward non-mirror field coverage,
coverage selects visible rows, and the same subset drives map and independent leaders. Estimates
retain the coherent posterior definition. Restore a concise hover/focus/tap tooltip with intervals,
worst pairing/record/prior status, coverage, match count, and field share. Reuse existing controls
and disclosure styling; no new visual direction or independent review round is needed for these
user-review corrections. Prior implementation CI passed on Python3.11 and3.13; the13 job passed
its retry after one runner timeout. Verify the refinement through focused JS/browser checks and CI.

- Refinement verification:43 focused report tests pass, including a new JS test proving support
  filtering leaves posterior values unchanged, updates leaders/map, recomputes tradeoffs among
  shown candidates, and escapes tooltip content. Desktop hover, keyboard/Enter/Escape, empty
  state, coverage/n/filter reset, frontier, and disclosure checks pass against actual corpus data.
  The map narrows64→13 candidates at40% coverage/n8 and restores64 on reset. Mobile tap tooltip
  stays within390×844 viewport; page has no unintended overflow or JS errors. Controls reuse
  the reviewed44px pattern; touch map points have44px hit areas and fine-pointer hover uses dots.
