---
id: epic-recurrent-stable-era-evidence-certification
kind: feature
stage: drafting
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-discovery]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Independent equivalence certification and persistence

## Brief

Turn outcome-free recurrent candidates into versioned `certified`, `rejected`, or `inconclusive`
decisions through independent event partitions, positive practical-equivalence tests, semantic
affectedness vetoes, context/support/concentration guards, and family-wise error control. Persist
enough evidence and version identity to reproduce why each interval reunion was admitted or refused.

Certificates are derived analytical artifacts rebuilt automatically under a fixed configuration;
changing calibration, confirming format truth, or promoting methodology remains operator-controlled.
This feature does not consume matchup outcomes or publish expanded matchup estimates.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: decision boundary between candidate discovery and every evidence consumer.

## Inherited design decisions

- Nonsignificance is not equivalence; underpowered candidates remain inconclusive.
- Confirmed affectedness is a hard veto, while pending format-monitor candidates are not truth.
- Parent certificates never stand in for independently supported camp certificates.
- Calibration and certificate schemas are versioned, deterministic, and operator-promoted.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — positive-equivalence burden and
  persistence contract.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/certify.md` — equivalence,
  multiplicity, support, and context guards.
- `.research/analysis/campaigns/recurrent-era-intervals/verification-checklist.md` — approved
  adversarial review.

## Foundation references

- `docs/SPEC.md` — versioned interval certification and honest abstention.
- `docs/ARCHITECTURE.md` — `EraCertificate` store and format-truth boundaries.
- `docs/PRINCIPLES.md` — confidence gating and live legality.

