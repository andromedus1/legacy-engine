---
id: epic-stable-era-windows-discovery-gate
kind: feature
stage: drafting
tags: [analytics, archetype]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-era-ledger]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery temporal gate: stable-window clustering + era-mixing detection

## Brief

Closes the era-cluster confound (the absorbed idea-discovery-temporal-gate): 27/46 ranked camps
from the 18-month discovery pool were TIME clusters — new-card signatures date-stamp clusters, so
"camps" were list generations, not coexisting builds. Three deliverables: (1) `discover run`
defaults its clustering pool to the parent's detected stable window (from the era ledger), with
the previous full-pool behavior available explicitly; (2) a temporal-mixing Gate C alongside the
existing statistical and domain gates — flag/fail splits whose camps' deck-date distributions
separate strongly (e.g. median-date gap / distribution-distance thresholds), with the
honest-degrade label "camps may be list generations"; (3) per-camp %current + median date
surfaced in the discover report (cheap, immediate, the era-audit's manual diagnostics made
first-class).

Re-running the full-meta discovery sweep and re-ranking best-build on stable windows is NOT in
this feature — that is the post-epic dogfooding payoff.

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: consumer of the era ledger, independent of `-consumption` — parallelizable
  with it.

## Inherited design decisions

- Detect parent change points FIRST, then discover camps within stable windows; Gate C is the
  backstop for splits that still straddle a boundary (epic Brief + change-point brief §7).

## Research briefs

- `docs/briefs/change-point-detection.md` §7 (sequencing with discovery).
- `docs/briefs/subarchetype-discovery.md` — the gate architecture this extends (Gate A
  statistical / Gate B domain; Gate C is temporal).

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/discovery.py + archetype/discovered.py (discover
  run|list|apply|promote).
- Patterns: honest-degrade-marker (Gate C label), confidence-metadata.
