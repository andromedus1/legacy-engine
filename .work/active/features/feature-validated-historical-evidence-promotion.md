---
id: feature-validated-historical-evidence-promotion
kind: feature
stage: drafting
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
