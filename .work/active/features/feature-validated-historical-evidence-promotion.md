---
id: feature-validated-historical-evidence-promotion
kind: feature
stage: implementing
tags: [analytics, advisory]
parent: null
depends_on: [feature-deck-rankings]
release_binding: null
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

## Ownership
One Luna xhigh implementation worker owns this feature's new shared projection/evaluator modules, evaluator CLI, production generator integration, and relevant tests; no nested agents. Host owns actual-corpus experiment execution, documentation, operational triage, and later-feature design. Standard review is the default. Keep one feature implementation commit and no push; host handles PR publication under project authorization.
