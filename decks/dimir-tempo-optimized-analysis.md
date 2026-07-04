# Dimir Tempo — sideboard optimization analysis (the local meta, 2026-07-04)

Companion to [dimir-tempo-optimized.txt](dimir-tempo-optimized.txt). How the board was optimized:
what the engine considered, why each decision fell the way it did. Engine: post-v0.2.0 scorer
(decomposed impact + flexibility valuation), validated via field-scoped `advise backtest` against
258 local-field-relevant top-finisher Dimir boards (established tier). Regenerate the raw surfaces:
`advise sideboard --deck decks/dimir-tempo-current.txt --field decks/local-field-current.txt --smart`
and `advise backtest --archetype "Dimir Tempo" --field decks/local-field-current.txt --field-scope`.

## 1. What the engine saw

**Deck profile (before scoring a single SB card):**
- *Maindeck-aware discounts fired:* **combo −60%** (4 FoW + 3 Daze + 4 Thoughtseize), **creature-based
  −60%** (3 Push + Snuff Out + 4 Bowmasters), **greedy-manabase −60%** (4 Wasteland). SB candidates
  duplicating these axes get their credit slashed — why no Ghost Quarter / extra discard.
- *Own vulnerability tags* (low-curve, blue/black, instant-speed game) feed the **symmetry gate**: a
  symmetric hoser that hits our own plan is floored to 0.15.

**Field:** the 107-player post-ban the local meta snapshot — blue plurality ~45% (Izzet 11.2%, Show&Tell
10.3%, mirror/Jeskai/Azorius/Esper), black/colorless combo wedge (Saga Storm 6.5%, Doomsday 5.6%),
fair tail (D&T, Eldrazi, Painter, Blue Artifacts, Energy). Per-archetype vulnerability profiles are
composition-derived, including the new axes: `noncreature-reliant` (plans living on the stack) and
`colorless-reliant` (Eldrazi 0.562 / Mystic Forge 0.635 / Saga Storm 0.284 colorless density vs our
0.021).

## 2. The objective, in plain terms

Maximize expected match-wins: each (archetype, vulnerability) element is weighted
`field_share × swing × impact` where impact = **centrality × symmetry × castability** (linchpin hit
or fringe? hoses us too? castable in that matchup?). A card is credited for its **total marginal
coverage across every element it answers** (submodular breadth), plus a **CVaR option-value bonus**
(α=0.7) for coverage robust to *which* field actually shows up. Copies taper by hypergeometric draw
probability (2nd copy ≈61% of the 1st, 3rd ≈37%). The **natural budget** stopped at 6 dedicated
slots — the field doesn't reward a rigid 15.

## 3. Slot-ROI — where the slots went

| Matchup | Equity → ceiling | ROI/slot | Call |
|---|---|---|---|
| Show and Tell (10.7%) | 62.0 → 89.6% | **0.0135** ⭐ | invest — best matchup gets better |
| Izzet Delver (11.7%) | 54.9 → 76.9% | **0.0117** | invest — biggest share |
| Black Midrange / Saga Storm (6.8% ea) | 50.0 → 76.4% | 0.0081 | invest (speculative data) |
| W.Beanstalk / Jeskai / Doomsday | 50–55 → 72–79% | 0.0070–79 | moderate |
| Painter · Eldrazi · D&T · Blue Artifacts | — | 0.0024–61 | **PUNT — better ROI elsewhere** |

Counterintuitive but correct: **spend on your good matchups, concede the bad ones.** A Show&Tell slot
buys ~3× the expected wins of a D&T slot. The old board spent ~7 slots on the punt column; this one
spends ~2.

## 4. The 15, slot by slot

**Counter core (2 FoN · 2 Consign · 2 Hydroblast)** — aimed at the top of the ROI table:
- **Force of Negation** — breadth: attaches to the whole combo/storm/noncreature plurality (~44% of
  field); largest option-value bonus. 99.2% of winning boards.
- **Consign to Memory** — NOT FoN redundancy: `centrality=0.60 vs Saga Storm` (linchpin hit via
  counter-on-cast) + the `colorless-reliant` axis FoN can't cover — **triggered abilities + colorless
  spells** (Saga chapters, storm/Chalice triggers, Eldrazi). Complements, not subset. 95.7% winners.
- **Hydroblast** — `plays-red`: Izzet (#1 share) + Painter + Energy. 85.7% winners. Two copies: the
  draw taper still pays at copy 2 for ~20% target mass.

**One-of toolbox (EE, Edict, Null Rod, Dauthi, Snuff Out, Harbinger)** — natural-budget flexible
tier, each a distinct axis: EE (low-curve sweep + Painter pair, 48.4% winners), Sheoldred's Edict
(edict vs hexproof/ward, 50.4%), Null Rod (Painter **Grindstone linchpin lock** + artifact mana,
32.9%), Dauthi (graveyard-*fuel* denial vs Murktide/delve, 31.8%), Snuff Out (free removal into
Izzet low-curve — the top uncovered element, 30.2%), Harbinger (greedy manabases; deploy black
first, then it's a mono-blue lock — 26.4%). Honesty detail: **EE and Null Rod carry symmetry=0.15**
— the engine priced their self-hosing (EE sweeps our low curve; Null Rod is symmetric) and they
earned slots anyway on breadth.

**Judgment fills (Barrowgoyf, Toxic Deluge, 4th Fatal Push)** — cover the engine's *tracked* blind
spot (winners-only creature-interaction cluster). Barrowgoyf: **83.7%** of winners vs ~24% midrange
field — the clearest "the field knows something the model doesn't yet."

## 5. Considered and rejected

| Candidate | Verdict | Mechanism |
|---|---|---|
| Defense Grid (engine wanted 2) | **overridden out** | `_hate` coverage applies no impact/symmetry factor (confirmed structural defect, tracked); its tax hits our own instant-speed game. **0.0%** of winners. |
| Damping Sphere (engine wanted 1) | **overridden out** | verified base-model near-miss (recommended even with option-value off); taxes our own cantrip turns. 2.7% of winners. Tracked. |
| Mystical Dispute / Spell Pierce | not picked — legitimately | earlier hand *coverage* analysis over-rated them; with breadth aggregating correctly, FoN/Consign dominate the same axes at higher impact. Winners agree (<20% adoption). The model corrected the human. |
| Ghost Quarter | not picked | maindeck-aware: 4 Wasteland pre-covers the axis 60%. |
| Flusterstorm ×2 (old board) | cut | <20% winner adoption; dominated by FoN/Consign on the same elements. |
| Surgical (old board) | cut | dead axis — no graveyard decks in the local meta; fuel-denial covered by Dauthi with a body. |
| 2 Massacre + 1 Toxic, 2 Hurkyl's (old board) | trimmed | the punt column; kept 1 Toxic as insurance, EE+Null Rod cover artifacts more broadly. |

## 6. Honest limits

Per-card impacts are **speculative-tier** on this field (~36% of matchup cells thin); swings are
curated-or-correlational, not causal; the ILP has one cosmetic tie (Snuff Out vs Long Goodbye, slot
9 — tracked); the two overrides are engine defects being fixed, not meta-calls. The validation that
matters: **7 of 9 engine picks appear in ≥20% of 258 local-field-relevant winning boards**, achieved by
mechanism with zero winner data in the scores. Net: a portfolio — concentrated counters where the
ROI is, a diversified toolbox across live axes, deliberate punts, self-hosing priced, redundancy
with the 60 discounted, every number auditable.
