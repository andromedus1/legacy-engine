---
id: feature-three-venue-meta-frame
kind: feature
stage: drafting
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

Standardize meta analysis as a default **three-lens read** rather than one global field:

1. **Online meta** — MTGO/online-derived field (today: `--provenance online`).
2. **Local meta** — a specific locality the user actually plays (e.g. Boulder, CO).
3. **Regional / travel-tournament meta** — large events people travel to (Eternal Weekend,
   Champs, regional opens).

"We should always approach meta this way." The point is that these three fields diverge sharply
and tuning should be done against the venue you're actually attending. Concrete evidence from the
2026-06-13 session (current Undercity Informer regime): online is **Tron-dominated (12.9%,
established tier)**, while paper has **Tron at 2.2%** and a long fair-deck tail (Izzet Delver,
Show and Tell, Painter, Dimir Delver, Aluren, Beanstalk, Stoneblade, Cradle Control). The
online/paper split alone already changes the deck-tuning answer.

**Gap:** the engine does online-vs-paper via `--provenance`, but it **cannot isolate a specific
locality (Boulder)** or an **event-tier (regional / large traveled-to events)** from global paper.
Delivering this frame motivates:
- `epic-local-meta-support` phase-2 geo/location dimension (filter by region natively), AND
- a **new event-tier / event-size dimension** (distinguish a 200-person regional from a weekly local).

Make "online / local / regional" a first-class, repeatable analysis frame across reports + advise.
Links to [[epic-local-meta-support]].
