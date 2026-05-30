---
id: improve-whattoplay-proactivity-threat-signal
kind: feature
stage: drafting
tags: [advisory]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Calibrate whattoplay proactivity: add an aggressive-threat signal

## Brief
Surfaced by running the advisor on real data (top-6 last-year meta analysis, 2026-05-30): the
composition-derived **proactivity score under-credits creature-tempo decks**. Izzet Delver — a fast,
proactive aggro-tempo clock (Dragon's Rage Channeler + Murktide + Cori-Steel Cutter + Lightning Bolt) —
scored **0.00 proactivity**, ranking as *more reactive than Dimir Tempo and Show and Tell*, which is
backwards. Root cause: `_proactivity_from_cards` builds `proactive_mass` from
`fast_mana + ritual + tutor + low_curve_score + compact_combo` only. Efficient creature *threats* (DRC,
Murktide, Tarmogoyf, Goblin Guide) carry **no proactive role** in `_card_roles` (a vanilla/near-vanilla
beater returns an empty role set), so a deck whose whole plan is "deploy a threat and protect it" reads as
0 proactive mass. Two secondary observations from the same run:

1. **`low_curve_score` isn't reaching `proactive_mass` as designed** — Izzet Delver got the `low-curve`
   *vulnerability* tag (avg MV < 2.0 fired) yet `low_curve_score` contributed ~0 to proactivity. The two
   low-curve computations are inconsistent; reconcile them.
2. **Presence-based vulnerability tags trip false positives over a noisy archetype aggregate** — e.g. a
   spurious `storm-reliant` tag on Izzet Delver / Dimir Tempo (a stray storm card in the aggregated
   composition flips the presence threshold). Consider a share/density threshold instead of mere presence.

## Why this matters
`whattoplay` is the soft, explicitly-heuristic layer (the engine already labels it heuristic-not-data and
the design committed only to *relative ordering* combo > tempo > control). The data shows the ordering is
wrong for creature-tempo — so any consumer leaning on proactivity (and the `report`/`advise whattoplay`
narrative) is misled. The meta-share + matchup layers are unaffected (data-driven, high-confidence).

## How to apply
- Add an **aggressive-threat proactive signal** to `_card_roles` / `_proactivity_from_cards`: a low-MV
  creature with a relevant body (power ≥ 2 at MV ≤ 2, or a known threat role) contributes proactive mass.
  Derive from `Card` type_line + cmc + power where available (power isn't modeled yet — may need a Card
  field or a curated threat list seeded from legacy-foundations staples).
- Reconcile `low_curve_score` so the proactivity low-curve term and the `low-curve` vulnerability tag use
  the same nonland-avg-MV computation.
- Switch vulnerability tags from presence to a **density/share threshold** to kill aggregate false positives.
- Recalibrate against the real corpus: Izzet Delver should land ~0.5–0.6; combo (Oops 0.77, Show and Tell)
  stays high; control/D&T stays low. Assert *relative ordering* (combo > tempo > control) on real archetypes.

## Foundation references
- `docs/briefs/advisory-methods.md` — §4 (proactivity formula + calibration targets; vulnerability tags).
- Source: `src/legacy_engine/advisory/whattoplay.py` (`_card_roles`, `_proactivity_from_cards`,
  `vulnerability_tags`).

## Notes
Greenfield-ish calibration of an existing module — route through `/feature-design` when picked up
(net-new threat-signal logic + threshold changes + recalibration tests). Not a blocker for the shipped
advisory pillar; an accuracy improvement to the heuristic layer.
