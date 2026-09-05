---
id: feature-deck-rankings
kind: feature
stage: implementing
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
- One cell posterior supplies estimates, intervals, field performance and floor. Carry the actual prior strength; missing cells retain a weak 50% prior. Use compatible clean interval data once each when supplied; avoid pooling overlapping fallback/current evidence.
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
Pending concise refinement of the existing report at `.mockups/screens/feature-deck-rankings/`.
