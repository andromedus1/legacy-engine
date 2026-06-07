---
id: epic-advisory-output-honesty-positioning-coverage
kind: feature
stage: drafting
tags: [advisory, analytics, correctness]
parent: epic-advisory-output-honesty
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Positioning Coverage & Confidence

## Brief

Make the positioning score honest about how much of the field it can actually see. Today, against a
broad field the matchup matrix covers only ~15 archetypes, so the vast majority of opponents are
imputed and `S` collapses to the ~0.50 imputation prior — yet S prints with full authority, and in
`--candidates` ranking zero-data decks (cov=0.00) surface spuriously high raw P(best) from the same
imputation. This feature introduces a share-weighted **field-coverage ratio** (the % of field mass
with real matchup data) as a first-class concept, auto-restricts the headline S to the covered
sub-field, and suppresses/flags low-support derived numbers.

Covers: surfacing the coverage ratio next to S; computing S over the covered sub-field with the
excluded share reported; suppressing/flagging P(best) and wide imputed CIs when coverage ≈ 0. This is
the foundation feature of the epic — the coverage concept it establishes is consumed by
whattoplay-honesty (which surfaces the coverage-aware S).

Does NOT cover: list-level granularity (deferred — see backlog `idea-list-granular-positioning`);
the "what to play" output surface (see `epic-advisory-output-honesty-whattoplay-honesty`).

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: foundation feature — `whattoplay-honesty` depends on the coverage-aware S it produces.

## Inherited design decisions
- **Low-coverage behavior**: **auto-restrict + note** — compute S over the covered sub-field
  automatically, print it alongside the field-coverage ratio and the excluded share. No flag required;
  the honest result is the default. Preserve the existing full-field path byte-identical when coverage
  is already high, and leave explicit `--field` / `--all-time` invocations behaving predictably.
- **P(best) at zero coverage**: suppress or visually flag raw P(best) (and the wide imputed CIs) when
  a candidate's coverage ≈ 0, so imputation-driven values don't read as real.

## Foundation references
- `docs/SPEC.md` — NFRs "Confidence-gated stats" + "Source transparency / no unlabeled headline numbers"
- `src/legacy_engine/advisory/positioning.py`, `advisory/field.py`, `advisory/gaps.py`
- Pattern: confidence-metadata (`tier_for_sample(n)`), gated-additive-augmentation (no-op path byte-identical to baseline)
