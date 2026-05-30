---
id: epic-advisory-whattoplay
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-field-model]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# What-to-Play Advisor (proactivity · vulnerability · hate-equity)

## Brief
The strategic read. Derive a continuous **proactivity score [0,1]** from card composition
(`proactive_mass = fast_mana + ritual + tutor + low_curve_score + compact_combo`;
`reactive_mass = counters + removal + stax + card_advantage + protection`;
`PROACTIVITY = proactive / (proactive + reactive)`) — auditable from card counts, not the archetype tag —
and **surface disagreement** between the computed score and the archetype's fair/unfair tag as a finding.
Tag archetypes with **vulnerability classes** (graveyard-reliant, combo, low-curve, greedy-manabase,
creature-based, low-interaction, storm-reliant) from oracle-text roles + metagame data. Compute
**hate-equity = the field share each hate category attacks** (`Σ field_share(a) for a carrying the tag`),
using **coverage, not a naive sum** for a package — this vector is exactly the sideboard recommender's
weighting input. Classify **best-deck vs best-call** from the **variance of a deck's matchup spread**
(low spread + high mean = robust BEST DECK; high spread + high field-specific mean = BEST CALL gamble).
Emit transparent **plan-clash WHY strings** (a readable rule table layered over the empirical matchup
numbers, never replacing them).

Consumes `field-model` (field shares for hate-equity) and the done `matchup-matrix` (spread variance) +
`Card` model (composition/oracle-text roles). 

Does NOT solve the sideboard ILP (`sideboard` consumes the hate-equity/vulnerability output), compute the
positioning score (`positioning`), or render the combined report (`report`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: consumer of `field-model` + done `matchup-matrix`/`Card`; **producer of the
  vulnerability tags + hate-equity vector that `sideboard` depends on**. Parallel to `positioning`.

## Inherited design decisions
- **Proactivity is composition-derived** (auditable from card counts), not the archetype tag; surface
  computed-vs-tag disagreement as a finding.
- **Hate-equity uses coverage, not naive sum** (a deck carries multiple tags); it is the sideboard
  weighting input.
- **best-deck vs best-call = matchup-spread variance** classification (independent of `positioning`'s S
  ranking — the two combine only in `report`).
- **Plan-clash heuristics are a readable rule table → WHY strings layered over empirical numbers**, never
  replacing them; flag heuristic-vs-data disagreement.

## Research briefs
- `docs/briefs/advisory-methods.md` — §4 (proactivity formula + calibration, vulnerability-tag table,
  hate-equity coverage, plan-clash rule table, best-deck/best-call).
- `docs/briefs/legacy-metagame.md` §6-7 — hosers-by-target, current strategic read (tag-derivation inputs).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/whattoplay.py`; `models/Card` role tags; `analytics/matchup.py`.
- `docs/PRINCIPLES.md` — #7 confidence-gate; heuristic-vs-data-driven labeling.

<!-- feature-design fills in: proactivity/vulnerability/hate-equity signatures, the rule table, test approach. -->
