---
id: epic-recurrent-stable-era-evidence-interval-consumption
kind: feature
stage: drafting
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-certification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Exact interval consumption and evidence decomposition

## Brief

Replace scalar-window eligibility at the analytical seam with normalized disjoint half-open interval
sets. Matchup evidence is admissible only inside the exact intersection of the subject and opponent
certificate sets, further bounded by explicit `data_until` and `knowledge_as_of` contracts. Excluded
gaps must remain excluded throughout match scanning, matrix construction, parent/camp parity, and
ranking measurement.

Expose typed current-only, certified-expanded, and added-history views with certificate/component
provenance, event/source concentration, and effective support. Preserve the existing scalar
`stable_since` path as the explicit current-only/no-certificate fallback while retiring it as a
parallel interpretation. Prevent admitted historical observations from also entering a
pre-disturbance prior.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: shared evidence-selection seam consumed by amplification, reporting, and
  validation.

## Inherited design decisions

- Both matchup sides govern eligibility through exact interval intersection.
- Expanded evidence remains diagnostic and decomposed from direct current evidence.
- `data_until` and `knowledge_as_of` are independent clocks.
- Camps remain current-only until independently certified.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — interval algebra and evidence
  view contract.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/consume-validate.md` — exact
  consumption, provenance, concentration, and temporal semantics.
- `docs/analysis/best-call-ranking.md` — current ranking ledger and honesty contract.

## Foundation references

- `docs/VISION.md` — compatible historical pockets with named provenance.
- `docs/SPEC.md` — current/expanded/added-history reporting.
- `docs/ARCHITECTURE.md` — single interval-set eligibility seam and matchup integration.

