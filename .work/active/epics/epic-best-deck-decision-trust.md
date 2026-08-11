---
id: epic-best-deck-decision-trust
kind: epic
stage: review
tags: [analytics, advisory, ingestion, infra]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Best-deck decision trust — correct, validate, and keep the evidence current

## Brief

Make legacy-engine's answer to “what are the best decks right now?” scientifically and
operationally trustworthy. The arc repairs known ranking defects, reconciles competing
measurement bases before adding richer presentation, validates frozen predictions against
future events, keeps the inputs current enough for those claims, and tests player effects as a
diagnostic rather than assuming they improve deck-strength estimates.

This epic is deliberately narrower than the full data-autonomy, sideboard-advisor, and rules
simulation programs. It owns the evidence chain behind archetype/camp ranking. Observed
top-finisher sideboards remain the primary sideboard evidence; the modeled recommender and
goldfish/rules engine are deferred and outside this autopilot scope.

## Strategic decisions

- **Order of proof**: correct the measurement basis and candidacy coverage before adding
  stability or posterior presentation.
- **Meaning of “best right now”**: candidates with zero current presence cannot compete for
  the headline P(best), but remain visible as explicitly inactive historical evidence.
- **Validation standard**: a chronological, future-only walk-forward benchmark is the proof
  gate for predictive claims; unit tests prove implementation correctness, not usefulness.
- **Comparison standard**: benchmark against simple internal baselines first and support
  operator-supplied dated external snapshots without making a brittle scraper a prerequisite.
- **Player effects**: start with identity coverage and pilot-stickiness diagnostics; expose a
  player-adjusted deck claim only if a strictly pre-match model improves future-only scoring.
- **Currency scope**: fix local/CI environment drift, localized and new-card resolution,
  coverage reporting, and repeatable refresh orchestration. Defer upstream hot-spare ownership,
  vendor-price expansion, and unrelated catalog programs.
- **Sideboards and simulation**: use observed deck choices; defer recommender-model rescue and
  goldfish/rules simulation.

## Child feature graph

- `feature-ranking-measurement-integrity` — reconcile adjusted-WR/window divergences and make
  unobserved floors explicit.
- `feature-ranking-honesty-guards` — repair P(best) coverage/candidacy and quarantine imputation.
- `feature-agency-page-methodology` — add estimator stability, posterior leans, and paths to
  grounding after the underlying measures are trustworthy.
- `feature-decision-data-currency` — make the local environment and ranking refresh inputs
  current, repeatable, and visibly covered.
- `feature-ranking-future-only-benchmark` — frozen walk-forward evaluation against baselines and
  optional dated external snapshots.
- `feature-player-effect-diagnostic` — pilot stickiness plus experimental strictly pre-match
  player effects evaluated inside the benchmark.

## Decomposition

Decomposition pre-existed at epic-design entry: six coherent child features cover measurement
integrity, ranking honesty, methodology, data currency, future-only validation, and the dependent
player-effect experiment. The graph has two independent foundation lanes (measurement/honesty and
currency), joins at methodology and the future-only benchmark, then gates the experimental player
effect. No additional feature is required.

## Simplification opportunity

Consolidate ranking recomputation and coverage definitions so the page, Monte Carlo ranker, and
validation harness cannot maintain subtly different versions of “measured coverage” or adjusted
field win rate. Prefer one refresh pipeline and one frozen prediction artifact over session
scratchpads. Do not retain a second ranking implementation solely for benchmark use.

## Child features reviewed and complete (2026-08-11)

All six direct child features completed implementation, independent standard review, receiver
adjudication, named fix verification, and closure:

- `feature-ranking-measurement-integrity`
- `feature-ranking-honesty-guards`
- `feature-agency-page-methodology`
- `feature-decision-data-currency`
- `feature-ranking-future-only-benchmark`
- `feature-player-effect-diagnostic`

The epic is ready for its deeper aggregate review. The latest repository verification recorded by
the final child closure is 3,710 passed and 1 expected optional-stack skip; the canonical knowledge
index reports 0 errors and 11 pre-existing advisory warnings.
