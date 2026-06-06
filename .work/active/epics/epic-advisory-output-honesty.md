---
id: epic-advisory-output-honesty
kind: epic
stage: drafting
tags: [advisory, analytics, correctness]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Advisory Output Honesty

## Brief

The engine's *statistics* are trustworthy (adaptive windowing, credible intervals, empirical-Bayes
shrinkage, Q0.25 risk-sort all hold up under scrutiny) but several of its *labels, summaries, and
headline numbers over-state confidence the underlying sample does not support* — surfaced repeatedly
across two dogfooding sessions (2026-06-04 and 2026-06-06). A score dominated by an imputation prior,
a "100%" card read on n=11, a tier list crowning a dead deck, threshold cliffs that mislabel the best
field pick — each is individually small, but together they erode trust in exactly the differentiator
pillar (Meta Attack / Advisory). This epic makes every advisory output *honest about its own
confidence*: surface coverage/sample, degrade or flag low-support claims, replace cliffs with
gradients, and stop treating placeholder/aggregate buckets as real opponents.

This is a presentation-and-confidence epic, not a re-derivation of the math. Where a number is sound
but its framing misleads, fix the framing. `/epic-design` decomposes the findings below into features.

## Member findings (absorbed from backlog — full text in git history)

- **positioning-field-coverage-gap** [advisory, analytics, correctness]: against a broad field the
  matchup matrix covers ~15 archetypes so ~322/335 opponents are imputed and S collapses to the ~0.50
  prior — yet S prints with full authority. Surface a share-weighted **field-coverage ratio** as a
  headline next to S; degrade/flag S when coverage is low; consider `--covered-only` / auto-restrict.
- **pbest-zero-coverage-flag** [advisory]: in `--candidates` ranking, zero-data decks (cov=0.00)
  surface spuriously high raw P(best) (~0.17) from imputation. Suppress/flag P(best) + wide imputed
  CIs when coverage ≈ 0.
- **bestcall-threshold-gradient** [advisory]: `best_deck_vs_best_call` hard cutoffs (spread_hi=0.02,
  mean_hi=0.52) create cliff effects — D&T was the best field pick but labeled "neither". Replace
  cliffs with a gradient / continuous signal.
- **inclusion-smallsample-presentation** [generation, analytics]: card-inclusion % reported without
  foregrounding n — a 7-week-old current-regime Dimir Tempo (n=11) read "100%". Foreground sample
  size; gate or annotate small-n inclusion reads.
- **tiers-default-current-regime** [analytics]: `report tiers` defaults to all-time, so it crowned
  Dimir Reanimator #1 — dead in the current regime. Default tiers to the current regime (consistent
  with the advisory layer's regime-awareness).
- **unknown-archetype-handling** [analytics, archetype]: 'Unknown' treated as a real opponent in
  fields and matchup rows (8.5% current-regime share). Decide and apply consistent semantics
  (exclude / bucket / flag) so it doesn't distort fields and positioning.
- **report-data-freshness** [analytics, ingestion]: no report surfaces data currency, so a stale DB
  yields confident-looking outdated output. Print a 'data current as of <max event date>' + corpus
  size header; warn when newest event is older than N days.
- **list-granular-positioning** [advisory, analytics]: positioning S is archetype-granular — two
  different 75s of the same deck score identically. Explore a clearly-labeled list-aware heuristic
  overlay (per-card composition nudges per-matchup WR) on top of the archetype-level S.
- **whattoplay-surface-positioning** [advisory]: `whattoplay` prints proactivity / vuln tags /
  best-deck-call but omits the positioning S (expected WR) — the one number a user most wants.
  Surface it.
- **tune-transparency** [generation]: `generate tune` is opaque/conservative — reports Value/Coverage
  with no sense of scale and no rationale. Add scale anchoring + per-swap rationale.
