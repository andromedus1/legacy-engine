---
id: epic-stable-era-windows-shrinkage
kind: feature
stage: drafting
tags: [analytics, methodology]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-consumption]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Hierarchical cell shrinkage: parent-anchored + cross-era priors as default

## Brief

Replaces the flat-0.5 matchup-cell prior with the hierarchy the repo's own
two-level-empirical-bayes pattern prescribes: a camp cell shrinks toward the SHRUNK parent-
archetype cell (leave-camp-out, so the parent estimate excludes the camp's own matches — no
double-counting), the parent cell shrinks toward its marginal, the marginal toward 0.5. PLUS the
cross-era prior this epic makes necessary: a thin post-disturbance cell shrinks toward its own
pre-disturbance value (labeled as such) instead of flat 0.5 — the right prior for young eras.
Worked motivating case: Lands[Sphere/Tomb] vs S&T raw 31.2 n=16 displays 40.3 today (pulled
toward 50); parent-anchored (~45.3) it reads ~38. Becomes the DEFAULT displayed estimate
everywhere in the same release as the window swap (design decision: one user-visible all-cells
shift); triple-display (shrunk%|raw% n=) is the honesty carrier — never a shrunk estimate without
raw + n. Design must specify: shrink-strength allocation across levels, leave-camp-out estimator,
interaction between the hierarchy and the cross-era prior (which anchor wins when both apply),
and the shrinkage-compression caveat (camp S* compressed toward 50 vs parents — compare camps to
camps) that the 07-11 analysis logged.

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: final layer — needs era boundaries (ledger) and lands on top of the
  re-windowed cells, re-pinning goldens once at the end.

## Inherited design decisions

- Shrinkage rollout — one shot, both default together (design decision): default in the same
  RELEASE as stable_since windows; goldens re-pinned; triple-display carries it.
- idea-hierarchical-cell-shrinkage absorbed in full: camp→parent chain AND cross-era prior (scope
  decision).

## Research briefs

- `docs/briefs/change-point-detection.md` (era boundaries the cross-era prior keys on).
- In-repo: `.agents/skills/patterns/two-level-empirical-bayes.md` — the primitive
  (`beta_binomial_shrink_to`) and the shrink-toward-SHRUNK-parent chain (card_value.py precedent).

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/matchup.py (`beta_binomial_shrink_to`, `SHRINK_STRENGTH`,
  cell assembly), analytics/card_value.py (the existing two-level chain to mirror).
- Patterns: two-level-empirical-bayes, confidence-metadata, freshness-stripped-cli-body-golden,
  honest-degrade-marker (cross-era-prior label).
