---
id: feature-validated-historical-evidence-promotion
kind: feature
stage: review
tags: [analytics, advisory]
parent: null
depends_on: [feature-deck-rankings]
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-09-05
---

# Improve Deck Rankings historical borrowing and evaluate the served model

## Brief
Evaluate the actual Deck Rankings estimator and input policy against simpler alternatives on chronological later tournament outcomes. Use the results to improve compatible historical borrowing, especially sparse matchup floors. Evaluation informs model changes and disclosures; it never suppresses descriptive estimates or adds a publication gate.

## Outcome boundary
- One production/evaluation estimation path, with explicit exclusive data cutoffs, historical taxonomy/knowledge semantics, per-cell provenance, and no duplicated physical matches.
- Fixed baseline/challenger comparisons on identical later cases; report proper scores, support strata, uncertainty, floor sensitivity, and which conclusions are supported. Distinguish development evaluation from genuinely held-out confirmation.
- Run the comparison on the actual available corpus, explain whether any proposed borrowing change helps, and ship justified improvements with regression tests. An inconclusive comparison does not justify fabricated improvement or a new silence gate.
- Preserve independent performance and minimum-matchup-floor priorities and coherent posterior summaries.

## Simplification
Replace the obsolete requirement to promote into the mature gated Agency/P(best) path. Reuse its cutoff-safe evidence machinery where useful; keep the frozen legacy benchmark reproducible. This item now owns the current Deck Rankings method, not another serving-policy approval framework.

## Grounding
.research/analysis/campaigns/recurrent-era-intervals/parent.md; advisory/deck_ranking.py; scripts/evaluate_deck_rankings.py; existing recurrent validation and ranking benchmark workflows.

## Authorized direction
Andrew approved the four-part sequence on 2026-09-05 and asked to execute it: improve historical borrowing and evaluate the exact current model; explain refresh changes concisely; examine pilotable archetype units; apply both independent priorities to custom fields. Keep estimates visible throughout. Existing data integrity and incompatible-era boundaries remain in force. Current report styling and interactions are the approved reference. No new audience, hosted product, or geographic ingestion is in scope.

## Execution
Standard feature review (default): one independent pass followed by verification of accepted fixes. Features run in the approved order. Reuse existing implementation and research before adding abstractions; preserve unrelated Hogaak files and uv.lock changes. Design records concrete interfaces before implementation.

## Design decisions (--only-questions directional pass)
The approved sequence, current report, and existing research pin the direction; no unresolved user-level decisions. Evaluation uses retrospective fixed parent taxonomy and refitted pre-cutoff raw snapshots, not a claim of knowledge as known then. Camps remain current descriptive outputs until an origin-local camp reconstruction exists. Fixed challengers change prior strength continuously and preserve every direct observation; they never cross excluded intervals or add a support gate. Actual evaluation results determine whether a challenger deserves a production change. Operator alerts and PR integration are separate operational closure work.

## Architectural choice
Options: extend the old recurrent promotion framework; duplicate a fast evaluator; or share the production projection and reuse raw snapshot utilities. Choose the third. The first lacks a production OriginRefitExecutor and recreates the obsolete gated architecture. The second would evaluate a different estimator. Keep existing legacy benchmark contracts frozen.

The hardest unit is production/evaluation input parity: cutoff snapshots must refit era state and classifications, then use the same era/fallback selection, positive-n interval overrides, field pseudo-counts, and posterior kernel as publication. Do not use live derived caches or truncate only outcomes. Snapshot/refit uses existing build_origin_snapshot; load_heldout_outcomes supplies one physical match ledger. Frozen current parent rules are explicitly retrospective. Use one consistent exclusive ban cutoff (< cutoff), including at boundary-day origins.

## Implementation units
1. Shared projection: `src/legacy_engine/advisory/deck_ranking_projection.py`, exact typed inputs via a small dataclass if useful. Export `project_ranking_rows(rows, shares, *, counts=None, candidate_presence=None, cell_overrides=None, override_sources=None, prior_scale=1.0, draws=10000, seed=730021) -> dict`. Resolve cell sources once, scale each selected cell's actual positive prior strength by prior_scale, and call rank_matchup_rows. Missing cells retain their named weak prior and scale consistently only in explicit challengers. Expose original/effective prior strength and prior contribution fraction; preserve full source identity. Refactor `_publish_deck_rankings` to use it; baseline prior_scale=1 must match the shipped output exactly. Reuse the same field input construction, with the current corpus_max+1 recency anchor.
2. `src/legacy_engine/workflows/deck_ranking_evaluation.py` or a bounded script adapter: `freeze_ranking_origin(source_db: Path, output_dir: Path, *, cutoff: str, evaluation_until: str, regime_start: str, prior_scales: tuple[float,...]=(1.0,0.5,2.0), draws: int=2000) -> dict`. Use BenchmarkFold/build_origin_snapshot, production compute_blob with parents={} and no composition-derived families, the same interval constructor/selection, and shared current projection. Freeze prediction JSON + metadata/code/config/rules/input hashes BEFORE loading future outcomes. Predict the same origin-fixed candidate/opponent grid for all methods. An unknown future label uses an explicit missing forecast rather than disappearing from the denominator; report served/common-case and total support distinctly.
3. `evaluate_ranking_origin(forecasts, outcomes) -> dict`: proper log/Brier scores with half weight for each direction of each physical match, event-level paired score differences and support strata (n=0, n1–7, n>=8), calibration summary, reciprocity discrepancy, and later outcomes for each predeclared toughest pairing. Missing later floor evidence is unavailable, never a zero loss or a safe floor. Forecast summaries show independent calls and prior-scale floor/rank sensitivity. Do not present realized minimum of a sparse future matrix as truth.
4. `scripts/evaluate_deck_rankings.py`: retain existing field diagnostic CLI compatibility, add an explicit served-model mode with output directory and declared chronological origins. CLI runs fixed candidates and produces a compact Markdown/JSON comparison. Predeclare development and confirmation origins before reading their heldout results. Run a bounded actual-corpus comparison and record negative/inconclusive results honestly; no tuning on confirmation outcomes. Keep production scale 1 unless evidence supports a fixed alternative; any selected change must be versioned and final-source verified. Include small sensitivity details in existing Method disclosure, not a new headline or gate.

## Testing
Production-versus-evaluator parity on identical snapshot inputs; n0 fitted versus absent prior; preserved observations under prior scaling; future fact/cache mutation leaves origin forecasts unchanged; cutoff-day exclusion; identical physical cases and one-match weighting; relabeling does not change scoring; missing future floor pairing stays unavailable; deterministic seeds; no target outcomes double-counted; corrupt/mismatched frozen inputs fail clearly. Focused suites then full repository CI and one standard independent review. Actual corpus results are required in the item body and a concise generated evaluation artifact.

## Risks
Prior-strength comparison isolates borrowing intensity, not every possible family model; do not overclaim it. Conditional intervals omit fitted-prior uncertainty. Exact recurrent certificates cannot be borrowed backward from current state. Snapshot evaluation is expensive, so use six predeclared nonoverlapping short horizons initially and preserve completed artifacts. If a snapshot fails due to real missing metadata, surface its precise exclusion/support rather than silently changing cases across methods.

## Implementation record

The shared production handoff is implemented in `src/legacy_engine/advisory/deck_ranking_projection.py`.
It resolves the interval override first, then era, then fallback, materializes the named weak prior
for absent cells, and scales only the selected prior strength for the fixed sensitivity methods.
Each projected cell carries its original/effective prior strength, prior contribution fraction, and
serialized source identity. `scripts/refresh_best_call_ranking.py` uses this handoff for the page;
retrospective evaluation passes `include_plans=False` so current strategic-plan composition is not
projected backward.

`src/legacy_engine/workflows/deck_ranking_evaluation.py` freezes a raw cutoff snapshot, refits its
parent era state, builds the same interval/current source ledger, and writes a hashed prediction
artifact before loading later outcomes. `scripts/evaluate_deck_rankings.py --served-model` retains
the field diagnostic mode and adds the served-model run. Focused projection and scoring contracts
pass (`tests/test_deck_ranking_projection.py` and
`tests/workflows/test_deck_ranking_evaluation.py`); the existing ranking, refresh, evaluator CLI,
and snapshot suites also pass. The actual-corpus run is owned by the host and remains pending
verification.

The fixed `opponent-plan-prior-v1` challenger now reuses the exact parent interval corpus and
curated primary-plan registry. It overlays only conditional prior mean/strength, records donor and
selection hashes in each frozen cell, and omits no-donor targets so the fitted baseline is exact.
The evaluator uses the fixed `quarantine-unresolved-decks` policy with 0.5% deck and 2% round
ceilings for both training snapshots and heldout reads; policy and ledgers are bound in manifests,
prediction metadata, evaluations, and the summary. Heldout rows carry source `match_idx`, so
same-player rematches remain separate while reverse duplicates are counted once.

## Predeclared served-model origins

The host experiment is fixed before heldout outcomes are opened. Development origins are
`2026-07-13→2026-07-20`, `2026-07-20→2026-07-27`, and `2026-07-27→2026-08-03`, each with
`regime_start=2026-06-29`. Confirmation origins are `2026-08-17→2026-08-24`,
`2026-08-24→2026-08-31`, and `2026-08-31→2026-09-04`, each with `regime_start=2026-08-10`.
All origins compare prior scales `(1, 0.5, 2)` on the same frozen candidate/opponent grid.
Confirmation outcomes must remain unopened until all origin prediction artifacts are sealed; no
scale is selected from confirmation results.

## Ownership
One Luna xhigh implementation worker owns this feature's new shared projection/evaluator modules, evaluator CLI, production generator integration, and relevant tests; no nested agents. Host owns actual-corpus experiment execution, documentation, operational triage, and later-feature design. Standard review is the default. Keep one feature implementation commit and no push; host handles PR publication under project authorization.

## Actual-corpus execution and selection protocol

The first pilot stopped before scores because card metadata closure failed. Reuse the existing
`quarantine-unresolved-decks` policy with fixed ceilings of 0.5% of decks and 2% of rounds,
identically across methods and training/heldout windows. This is the known
`bug-card-dimension-localized-and-new-card-gaps` backlog issue; no card names were guessed or
metadata repaired. Read-only preflight found 26/66,750 decks and 100/80,845 rounds excluded before
July 13; 27/69,303 decks and 104/81,875 rounds before August 31. The July 27 development horizon
excludes one of 400 decks and four of 219 rounds. Other development and all confirmation horizons
have zero exclusions. Every examined window remains within the existing ceilings.

Six freeze-only runs launched from source commit `b13b0bd`, two processes at a time, under
`data/benchmarks/deck-rankings-evaluation-v1/`. All six predictions must exist and verify before
any heldout outcome is loaded. The fixed fourth method is `opponent-plan-prior-v1`: target-pair
excluded donor counts, Beta(1,1) smoothing, strength min(15, donor n), primary-only registry
assignment, same clean interval corpus, no-donor baseline unchanged.

Before opening development outcomes, use match-weighted proper log loss as the primary
comparison, Brier score as a corroborating check, and paired-event differences/support strata to
explain stability. Record the selected development candidate and its settings before opening
confirmation. Do not require significance to publish descriptive estimates. A confirmation
reversal or conflicting scores can justify retaining the baseline; never tune the candidate on
confirmation or call a sparse result proven. Independent performance and floor sensitivity are
reported rather than optimized against a noisy realized future minimum. Actual findings remain
pending; the baseline production prior is unchanged.

The single standard independent implementation review runs alongside the forecast freezes.
Actual-corpus results, review fixes, and CI remain required for final feature closure.

## Current-cycle implementation update — 2026-09-05

Accepted review corrections are implemented in the shared projection, raw snapshot/heldout
utilities, served evaluator, and generator handoff.  Parent classification now binds and replays
the production colour-split registry (including Energy branches) in both training and heldout
windows.  Optional `match_idx` is carried from the source rounds table, so physical identity
deduplication preserves same-player rematches and removes only the reverse row for the same match.
The fixed quarantine policy remains `quarantine-unresolved-decks` with ceilings of 0.005 decks and
0.02 rounds in every training and heldout window; its ledger and retained-facts binding are
recorded in the artifacts.  The evaluator requires an artifact digest, rejects duplicate forecast
cells, and reports selected-view identity including source clock, windows, components, match hash,
and concentration for every positive-n interval override.  The plan-borrowing challenger remains
conditional: it overlays mean/strength while preserving direct W/n and source identity, and a
target with no donors exactly uses the baseline prior.

The served CLI has explicit `freeze`, `development`, `confirmation`, and `all` phases.  The
default `--served-model` invocation freezes all six predeclared origins and scores only the three
development horizons, writing `development-summary.json`; confirmation reads sealed predictions,
requires `--selected-method`, writes `development-selection.json`, and only then opens its three
confirmation horizons.  Summaries contain match-weighted scores, event-paired stability,
per-method performance/floor order sensitivity, and named-floor followups for every method, with
descriptive `supported`, `tentative`, or `inconclusive` status and no significance/publication
gate.  Runnable commands are:

```
.venv/bin/python scripts/evaluate_deck_rankings.py --db <source.duckdb> --served-model \
  --output-dir data/benchmarks/deck-rankings-evaluation-v1 --phase development
.venv/bin/python scripts/evaluate_deck_rankings.py --db <source.duckdb> --served-model \
  --output-dir data/benchmarks/deck-rankings-evaluation-v1 --phase confirmation \
  --selected-method <development-method>
```

Focused projection, evaluator, snapshot, CLI compatibility, and file-backed production parity
tests pass.  The actual-corpus freeze and all development/confirmation scores remain pending
host execution; no empirical conclusion or production prior change is claimed here.

## Review boundary

Shared projection, fixed challengers, snapshot/heldout policy, and evaluator implementation are
verified (28 focused tests and 85 regression tests); the initial CI pass is green on Python 3.11
and 3.13. Advance the code to review while the real-corpus forecast freezes run. Empirical
selection and final-source CI remain explicit closure requirements, and no production borrowing
change is made yet. The next feature depends on the now-stable published projection contract,
not on which fixed challenger wins. Its presentation implementation can therefore proceed while
this review and experiment finish, preserving the approved delivery priorities.

## Standard independent review — accepted corrections

One fresh-context Sol xhigh review requested changes. Claude peer authentication was unavailable;
this was same-harness independent review, not cross-model evidence. All six findings are accepted:

- Replay and hash the production color-split registry in training and heldout classification
  (Energy must remain Boros/Mardu). The first six-origin freeze was stopped before any score or
  heldout outcome was opened; its partial snapshots are not evaluation evidence.
- Separate public freeze/development/confirmation phases and seal the development decision before
  reading confirmation. This protects experimental interpretation, not report publication.
- Preserve each interval override's selected-view identity, components/windows, and match digest
  in the shared handoff and frozen per-cell provenance.
- Require frozen digests and reject duplicate forecast cells.
- Report all methods' named-floor followups, match-weighted aggregates, event stability/uncertainty,
  and independent performance/floor sensitivity with a concise conclusion.
- Add one real file-backed freeze regression for production parity, cutoff-day/future-fact
  invariance, and parent taxonomy binding. Host owns this isolated test; the implementation worker
  owns the code fixes.

The review found the prior construction, direct-observation preservation, physical rematches, and
quarantine handling sound; 119 focused checks passed. Complete accepted fixes and verify them
without a second standard review pass. The separate refresh-insights work continues on unaffected
publication/template regions; it cannot change the projection while this experiment is frozen.

## Accepted-fix verification and restarted experiment

Source commit `91a36f1` contains the accepted code corrections. A checkpointed byte copy of
`data/legacy.duckdb` was made under a read lock for this experiment, SHA-256
`82011023b61848c52748d595336291ee815d168bdb08df8f1d6cb146c1f2c9da`, stored as
`data/benchmarks/deck-rankings-evaluation-v1/source.duckdb`. No heldout results were inspected.
Six forecast-only jobs restarted against that immutable input. Later report/template work does
not alter their projection or taxonomy functions.

Four integrated freeze/phase tests now verify exact parent point/cell parity and provenance,
future-fact/cache invariance, registry binding, reuse of sealed artifacts between phases, and
configuration mismatch rejection. The initial full CI pass was green on both Python versions;
the implementation worker also reports 4,151 local suite passes and one skip. Final-source CI
will cover the remaining integrated changes.

The comparison adds a deterministic paired-event bootstrap interval for the event-average loss
difference (2,000 resamples, seed 730022). Events receive equal weight for this stability check;
the primary proper score remains match-weighted. No interval is claimed from fewer than two
events. Markdown now shows this distinction and the independent performance/floor call counts
across origins; detailed per-method floor followups remain in the JSON. These diagnostics do not
create a significance or publication requirement. Fifteen focused evaluator/integration checks pass.

## Development selection — sealed before confirmation outcomes

All six prediction artifacts completed before the development phase was scored. The development
comparison selected **prior scale 2**: match-weighted log loss 0.690337 versus baseline
0.696988 and half-strength 0.708919; Brier 0.248590 versus baseline 0.251759. The plan-donor
challenger scored worse than baseline (log loss 0.703727; Brier 0.254790), so it is not selected.
Double strength improved all three development origins, and 22 of 32 paired event means;
equal-event mean delta -0.00833 with 95% bootstrap interval [-0.01437, -0.00248].
The development score uses 347.5 directed half-match weights from 420 eligible physical
matches; 326 have both directions forecast. All methods use identical forecast availability.
Performance and floor leaders were unchanged by strength scaling at all three origins.

This selection is recorded before opening any confirmation scores. Next: seal candidate `2`
against the development artifact and evaluate the three fixed August confirmation horizons.
Production remains at scale 1 until those outcomes are inspected; no confirmation tuning.
