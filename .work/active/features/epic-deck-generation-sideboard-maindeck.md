---
id: epic-deck-generation-sideboard-maindeck
kind: feature
stage: drafting
tags: [generation, advisory]
parent: epic-deck-generation
depends_on: [epic-deck-generation-per-card-value]
release_binding: null
gate_origin: null
created: 2026-05-31
updated: 2026-05-31
---

# Maindeck-aware sideboard (per-matchup OUT/IN plan)

## Brief

Rework `advisory/sideboard.py` from a maindeck-blind max-coverage-over-hosers model into a **maindeck-aware**
recommender. the maintainer's framing (2026-05-31): sideboarding is a main↔side **swap per matchup** — you side cards
OUT of the 60 to bring cards IN from the 15 — so the recommendation cannot be computed independently of the
maindeck. The 15 should be chosen to maximize the value of the *post-board* 60s across the weighted field,
given what the maindeck already does.

**Deliverable = hybrid (locked):**
- **Primary — per-matchup OUT/IN plan.** For each top field archetype where the per-card×matchup data clears
  the confidence gate: the cards to side OUT of the 60 (the maindeck's dead/low-value-in-matchup cards, by
  per-card×matchup value) + the cards to side IN from the 15 → the post-board 60. The 15 is selected to serve
  these plans (fill what the maindeck lacks per matchup; don't double-cover what the main already answers).
- **Degrade gracefully — maindeck-aware 15 composition.** Where a matchup is too thin for a credible OUT/IN
  guide, fall back to the 15-composition rationale (gap-fill / no double-cover) WITHOUT inventing an OUT/IN
  list for that cell, and say so. Never fabricate a plan from imputed data.

## SSOT / blast radius (locked)
- **Rework in place** — one model both the `advise sideboard` CLI path and the `generation` tuner consume.
  This **re-opens the done `epic-advisory` sideboard feature**, changes its outputs (the recommendation is no
  longer a standalone 15 — it gains the maindeck input + per-matchup plan), and **will change existing tests**:
  regression-cover them, don't silently break them. Keep the saturating max-coverage primitive
  (`g(n)=1−(1−p)^n`, `max_copies`, weighted field threat-elements) — it stays the fallback objective when
  per-card data is absent; the per-card×matchup value augments it, it does not delete it.
- Consumes `epic-deck-generation-per-card-value` for the per-card×matchup signal (value + confidence tier).

## Foundation references
- `src/legacy_engine/advisory/sideboard.py` — `HoserCard`, `HOSER_CATALOG`, `CoverageModel`,
  `_build_coverage_model`, `_compute_covered_weight`, `recommend_sideboard`, `SideboardPackage`. The current
  contract + the `build_tuning_coverage_model` wrapper in `generation/tuning.py` that depends on it.
- `src/legacy_engine/advisory/field.py` (`build_global_field`/`build_custom_field`), `analytics/matchup.py`
  (`build_matrix`) — field weights + matchup-weak signal feeding the model.
- `docs/briefs/advisory-methods.md` — sideboard method.

## Design decisions (locked 2026-05-31 — do not re-decide)
- **Objective is maindeck-aware + per-card-value-driven**, with the existing coverage model as the
  data-absent fallback (above).
- **Which maindeck cards are siddable-out:** data-driven by per-card×matchup value (low/negative-in-matchup
  cards come out first), bounded by the available IN cards and a sane per-matchup swap cap. Locked-core
  protection (high-inclusion proactive staples never auto-sided-out) carries over from the tuning flex/locked
  partition concept. Exact cap + tie-breaks = feature-design unit choice.
- **`SideboardPackage` gains** the maindeck input + a per-matchup OUT/IN plan structure + per-cell confidence
  tier; the `advise sideboard` CLI prints the plan (degraded note where thin).

## Acceptance (sketch — feature-design fleshes into units + tests)
- `recommend_sideboard` (or its successor) takes the maindeck + field; returns the 15 PLUS per-matchup OUT/IN
  plans for gate-clearing archetypes.
- Post-board 60s are exactly-60 + legal (incl. `max_copies`); the 15 respects catalog `max_copies`.
- Thin matchup → degrades to composition rationale, flagged; no fabricated OUT/IN list.
- Existing `advise sideboard` tests updated/regression-covered, not broken silently.
- Reuses the rounds-bearing fixture from `epic-deck-generation-per-card-value`.
