---
id: epic-recurrent-stable-era-evidence-best-call-integration
kind: feature
stage: drafting
tags: [analytics, advisory, ui]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-amplification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Best Call evidence and historical-target integration

## Brief

Extend the generated Best Deck / Best Call page to publish current-only, certified-expanded,
added-history, and amplified challenger evidence without conflating their authority. Each row and
ledger exposes the direct/historical/borrowed contribution, admitted interval components,
concentration, confidence, and refusal reasons while the existing authoritative ranking remains
unchanged until validation permits promotion.

After the current report gains useful recovered evidence, add retrospective `Today’s model`
targets such as pre-ban cutoffs by threading `data_until` through the entire ranking composition.
Do not label a retrospective reconstruction as `As known then`; that later mode requires a real
`knowledge_as_of` substrate. Reuse the existing page's controls and disclosure patterns rather than
introducing a new screen.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: diagnostic publication consumer; independent of benchmark execution.

## Inherited design decisions

- Current-report evidence recovery ships before the historical target selector.
- Expanded and amplified estimates remain diagnostic until future-only promotion.
- The UI visibly decomposes direct, certified-historical, and borrowed evidence.
- Historical targets are explicitly labeled `Today’s model`; `As known then` is not implied.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — reporting views and two-clock
  historical semantics.
- `docs/analysis/best-call-ranking.md` — generated page method and publication contract.

## Foundation references

- `docs/VISION.md` — advisory as a first-class product surface.
- `docs/SPEC.md` — self-contained visualization and honest-degrade requirements.
- `docs/ARCHITECTURE.md` — ranking generator and recurrent evidence consumers.

