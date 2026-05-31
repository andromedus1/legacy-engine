---
id: improve-whattoplay-proactivity-threat-signal
kind: feature
stage: implementing
tags: [advisory]
parent: epic-advisory-hardening
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

## Design decisions (--only-questions, 2026-05-30)
- **Threat signal = BOTH, layered** (user-directed). Primary: add `power`/`toughness` to the `Card` model
  + Scryfall ingestion (Scryfall already provides these — small additive change), and derive a general
  proactive-threat signal (low-MV creature with a real body, e.g. `cmc <= 2 and power >= 2`). Supplement:
  a small curated `THREAT_CARDS`/override set for proactive threats raw stats miss (cheap planeswalkers,
  evasive/payoff cards, creatures whose text understates them). The general signal does the heavy lifting;
  the curated list is a targeted override — not a standalone heuristic. This adds a (small) ingestion-layer
  dependency: the `Card.power/toughness` fields + seed must land before the proactivity recalibration.
- **Vulnerability tags → density/share threshold** (not mere presence) to kill the aggregate false positives
  (e.g. the spurious `storm-reliant`/`greedy-manabase=100%`).
- Calibration target unchanged: assert *relative ordering* (combo > tempo > control) on real archetypes;
  Izzet Delver should land ~0.5–0.6.

## Design (autopilot, 2026-05-30)

**Architectural choice:** general threat signal from `Card.power` + a small curated override (the pinned
"both" decision). Power/toughness are Scryfall string fields that thread through unchanged via
`Card.model_validate`. Vulnerability tags move from presence to density thresholds.

### Implementation Units
1. **`models/card.py`** — add `power: str | None = None`, `toughness: str | None = None` (Scryfall keys
   auto-populate via `model_validate`). Add a helper `power_int(self) -> int | None` (parse "2"→2; "*"/"1+*"/
   None → None).
2. **`ingestion/store.py`** — add `power VARCHAR, toughness VARCHAR` to the `cards` DDL (now 11 cols); add
   `c.power, c.toughness` to the `load_cards` row tuple + the `INSERT OR REPLACE … VALUES` placeholders;
   include them in `_card_from_row`/`fetch_card` consumers. Note: existing `data/legacy.duckdb` needs a
   `seed cards` re-run to backfill the new columns (CREATE TABLE IF NOT EXISTS won't alter an existing table)
   — flag in implementation notes; tests use fresh `:memory:` so they get the new schema.
3. **`advisory/whattoplay.py` `_card_roles`** — add a `threat` role: `"Creature" in type_line and cmc <= 2
   and (power_int >= 2)`, OR `name in _THREAT_CARDS` (curated override set seeded from current staples: Dragon's
   Rage Channeler, Murktide Regent, Tarmogoyf, Goblin Guide, Death's Shadow, the Goyfs, etc., + proactive
   non-creature threats like cheap planeswalkers). `_load_deck_cards` must carry power through.
4. **proactivity** — add `threat` density to `proactive_mass`; reconcile `low_curve_score` so its
   nonland-avg-MV computation matches the `low-curve` vulnerability-tag threshold (single shared helper).
5. **vulnerability tags** — density/share thresholds (e.g. a tag fires only if its role density ≥ ~10-15% of
   nonland cards), killing the presence-based false positives (`storm-reliant` on Brainstorm-adjacent
   aggregates, `greedy-manabase` on everything).
6. **exports/tests** — `tests/test_whattoplay.py`: threat-role detection (DRC/Murktide → threat; vanilla 5-drop
   → not), proactivity **relative ordering** Izzet Delver ~0.5–0.6 > control, density-threshold tag tests
   (no spurious storm-reliant), `Card.power_int` parsing. Update `tests/test_card.py`/`test_store*.py` for the
   new fields.

### Tests / acceptance
- Izzet-Delver-like composition (DRC + Murktide + bolt + cantrips) scores **> 0.5** proactivity (was 0.00).
- A control composition stays < 0.4; combo (rituals+tutors) stays high — ordering combo > tempo > control.
- A deck with one stray storm card does NOT get `storm-reliant` (density gate).
- All existing tests stay green (additive Card fields; defaults None).
