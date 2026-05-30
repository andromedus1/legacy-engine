---
description: What are the rules, mulligan mechanics, and format constraints of Legacy that an analytics/simulation platform must encode? Read before designing the deck-as-data model, goldfish sim, or legality validation.
type: brief
kind: research
research_method: /research
updated: 2026-05-29
status: draft
summary: |
  Grounding brief on Legacy format fundamentals for the legacy-engine analytics platform.
  Covers Magic's turn structure / stack / state-based actions (framed for goldfish simulation),
  the London mulligan and its hand-quality math, and Legacy's deck-construction + banned-list
  constraints with the format-defining staple cards. Frames every section for the eventual
  platform (deck-as-data model, mana solver, mulligan Monte Carlo, legality validation).
key_findings:
  - A Legacy goldfish sim needs ~8 core rules encoded; the heart is a mana-payment solver (can_pay(cost, untapped_sources)) plus a LIFO stack for the deck's own triggers (CR 405/601/605).
  - Legacy uses straight London mulligan, NO free mulligan; model keep() and bottom() as separate archetype-parameterized functions via Monte Carlo, not closed-form hypergeometric.
  - London disproportionately benefits combo/specific-card decks (+10-18pp to assemble "the nuts"); calibrate the sim against published tables (Chalice T1 53->63%, Power Monolith 21->31%).
  - Legacy legality is a BLACKLIST (all cards legal except the banned list) — unlike Standard/Modern whitelists; banned list changes ~quarterly and must be version-stamped by date.
  - Legacy bans outright what Vintage restricts (Power 9, Sol Ring, etc. are 0-of in Legacy); no restricted list exists. "Free" interaction (Force of Will/Daze) is the defining structural trait.
  - Banned list is current as of the May 18 2026 announcement (Undercity Informer); next scheduled June 30 2026.
---

# Brief: Legacy Format Foundations

## Purpose
Ground the legacy-engine platform in the rules, mulligan mechanics, and format constraints of
Magic: The Gathering's Legacy format. This is the hard prerequisite for designing three platform
pieces: the **deck-as-data model** (what fields a Legacy decklist needs), the **goldfish
simulation engine** (what rules a single-deck turn loop must respect), and **legality validation**
(banned list + deck construction). Sibling project edh-engine solves the analogous problem for cEDH;
this brief is framed to reuse that architecture where the domains overlap and flag where they diverge.

---

## 1. Rules & Turn Structure (framed for goldfish simulation)

A **goldfish sim** simulates one deck's own development across turns to measure how fast and
consistently it executes its plan, with no opponent in the simplest model. That framing collapses
the large parts of the rules that govern player interaction (priority round-robin, blocking,
instant-speed responses to *opposing* spells) but must still respect timing rules that constrain
what the deck can do on its own turn.

### Turn structure (CR 500–514)
Five phases in order: **beginning** (untap/upkeep/draw), **precombat main**, **combat**
(begin/declare attackers/declare blockers/combat damage/end of combat), **postcombat main**,
**ending** (end step/cleanup).

- **Untap step (502):** active player untaps simultaneously as a turn-based action. **No player gets priority** — nothing can be cast here.
- **Draw step (504.1):** active player draws (turn-based, doesn't use stack); player on the play skips their first draw.
- **Precombat main (505):** sorcery-speed window — creatures, sorceries, lands. ~All goldfish decisions concentrate here.
- **Combat (506–511):** in a no-opponent model, declare-blockers is a no-op; combat damage = sum unblocked power vs a virtual 20-life opponent.
- **Cleanup (514):** discard to 7, remove damage, "until end of turn" effects end. **Normally no priority.**

### The stack & priority (CR 116/117, 405, 608)
The stack is **LIFO** (CR 405.2): last-added resolves first. Simultaneous triggers go on in APNAP
order. **Even single-player, the sim needs a real stack** to resolve the deck's own triggered
abilities (ETBs, storm, cascade) in correct order. Priority collapses to "active player acts until
pass / stack empties." Instant speed = any priority window; sorcery speed = own main phase, empty
stack, priority.

### State-based actions (CR 704)
Checked whenever a player would get priority; performed simultaneously, don't use the stack. The
ones a sim must check: **0 life loses (704.5a)**, **drawing from empty library loses (704.5b — the
loss is the *draw attempt*, critical for Thassa's Oracle / Demonic Consultation kills)**, 0-toughness
to graveyard (704.5f), lethal damage destroys (704.5g), poison ≥10 (704.5c), legend rule (704.5j),
Saga final-chapter sacrifice (704.5s). Run a `check_state_based_actions()` loop until stable before
every priority grant.

### Mana & casting (CR 106, 601, 605)
Casting steps (CR 601.2a–i) happen as one uninterruptible proposal; the key insight: **mana abilities
resolve immediately, don't use the stack, can't be responded to (605.3b)**. The core goldfish
computation is "**can I cast this on turn N?**" = given a cost and the set of currently untapped mana
sources, decide `can_pay(cost) → bool` as a **set-cover / flow problem** over color-producing sources.
Cost objects: `{generic, colored:{W,U,B,R,G,C}, X, additional_costs}`.

### Key timing concepts the sim must respect
- **Sorcery-speed gating** (307.5/505.5b): non-instants only in own main phase, empty stack.
- **Summoning sickness** (302.6): a creature can't attack or use {T} abilities unless controlled since the controller's most recent turn began — gates mana dorks and aggro clocks; haste bypasses.
- **One land drop per turn** (505.5b): per-turn counter, default cap 1, raisable (Exploration); land plays bypass the stack.
- **Mana pool empties between steps** (500.4).

### Implementation relevance — the ~8 rules a Legacy goldfish sim must encode
1. Ordered turn loop with per-step priority flags (untap/cleanup grant none; draw/untap are automatic).
2. The stack as a real LIFO structure — required even solo for the deck's own triggers.
3. A **mana-payment solver** (`can_pay(cost, untapped_sources)`) — the heart of the engine.
4. A state-based-action loop (min: 0 life, empty-library draw, 0-toughness/lethal damage).
5. Per-turn land-drop counter.
6. Per-creature summoning-sickness flag.
7. Sorcery-speed gating.
8. Cast-trigger emission at 601.2i (storm count, prowess) — distinct from inline mana abilities.

> **Reuse note:** edh-engine already ships a goldfish sim (deck-as-data, bipartite-matching mana,
> role-dispatch engine, London mulligan). The turn-loop and mana-solver concepts transfer directly;
> the 20-life-opponent default and 60-card/4-of construction are the Legacy-specific deltas.

**Sources:** Official CR eff. 2026-02-27 ([PDF](https://media.wizards.com/2026/downloads/MagicCompRules%2020260227.pdf), [WotC rules](https://magic.wizards.com/en/rules)); section mirrors [ancestral.vision](https://ancestral.vision/), [yawgatog](https://yawgatog.com/resources/magic-rules/).

---

## 2. The London Mulligan

### Mechanics (CR 103.5, effective M20 / July 2019)
Draw 7; decide keep or mulligan. On each mulligan, shuffle hand in, draw 7 again. **Once you keep,
put N cards on the bottom in any order, where N = number of mulligans taken.** You always see a fresh
7 and pay the cost (bottoming) *after* deciding to keep. This converts the mulligan from "smaller
random hand" (Vancouver: draw one fewer + scry 1) into "smaller *selected* hand" — a strictly larger
selection advantage.

**Legacy uses straight London with NO free mulligan.** (The free-first-mulligan is a multiplayer
Commander add-on; do not implement it for Legacy.)

### The math
Single-hand baseline is hypergeometric: P(≥1 of 4-of in opening 7, 60-card deck) ≈ **39.9%** — which
is why **redundancy (8+ functional copies) is the primary consistency lever** (Karsten). But London's
"draw 7, keep best 6/5" selection is conditional and **requires Monte Carlo**, not closed form.
Published simulation (tmikonen, <1% error) shows London's gain concentrated in low-base, specific-card
events:

| Scenario | Vancouver | London | Δ |
|---|---|---|---|
| Legacy Chalice on T1 | 53% | 63% | +10pp |
| Sneak & Show A+B pieces | 70% | 79% | +9pp |
| Power Monolith combo | 21% | 31% | +10pp (~+48% relative) |
| Aggressive 3-threat start | 30% | 48% | +18pp |

**Why combo benefits most:** selection rewards specificity (combo needs *particular* cards), relative
gain scales with target rarity, and combo can afford to dig to 5 to find its 2 pieces while fair decks
lose grind resources. Cantrips (Brainstorm/Ponder/Preordain) are *complementary*: London fixes the
opener, cantrips fix turns 1–3.

### Implementation relevance
1. Model straight London, no free mull (format flag, off for Legacy).
2. Separate `keep(hand, target_size)` and `bottom(hand, n)` — London's whole advantage lives in the bottoming step. Don't conflate "keep a random 6" with "keep best 6 of 7."
3. Encode keepability as **archetype-parameterized predicates** (combo: ≥1 piece-A AND ≥1 piece-B AND ≥k mana, or a cantrip-bridge fallback; fair: ≥2 lands + color access; aggro: ≥2 lands + ⅔ spells). Calibrate against the table above as regression fixtures.
4. Bottoming heuristic = rank by marginal value, drop lowest N (surplus lands → uncastable/off-plan → redundant copies → keep scarce plan-critical pieces).
5. Implement a mulligan floor + "mulligan-more" bias (post-mull hands are stronger because selected from 7).
6. **Output full distributions, report by-turn** (P(keepable) at 7/6/5; kept-hand-size distribution; P(goal by turn T)) — matches edh-engine's mulligan-consistency direction (evaluate distributions, not point values).

**Sources:** [WotC London announcement](https://magic.wizards.com/en/news/announcements/london-mulligan-2019-06-03); [tmikonen Monte Carlo tables](https://tmikonen.github.io/quantitatively/2019-03-01-london-mulligan/); [MinMax Eternal perspective](https://minmaxblog.com/the-london-mulligan-an-eternal-perspective); [F2F bottoming/keep](https://magic.facetofacegames.com/cracking-the-london-mulligan/).

---

## 3. Format Constraints

### Deck construction
- **60-card maindeck minimum** (no max, must shuffle unaided); **max 4 copies** of any card across maindeck+sideboard (exceptions: basic lands unlimited; explicit overrides like Seven Dwarves=7, Relentless Rats=∞).
- **Sideboard: 0 or up to 15 cards**, counts against the 4-copy limit. Matches are **best-of-3**; G1 maindeck only, sideboard between games.
- **Card pool = every set ever printed, minus the banned list** — the second-largest pool behind Vintage, a strict superset of Modern. Excludes silver/gold-border and non-standard backs. **Legality is a BLACKLIST**, not a whitelist (the key structural difference from Standard/Pioneer/Modern).

### Legacy bans vs Vintage restricts
Legacy has **no restricted list**. What Vintage restricts to 1 copy (Power 9, Sol Ring, Mana Crypt,
the Moxen, Black Lotus, Ancestral Recall…), Legacy **bans outright (0 copies)**. Dominant cards get
banned rather than throttled, so the format is governed entirely by the ban lever (~quarterly cadence).

### Recent bans (2023–2026) — track with dates + reasons
| Date | Card(s) | Reason |
|---|---|---|
| 2022 | Ragavan | Format-warping UR Delver engine |
| Mar 6 2023 | Expressive Iteration, White Plume Adventurer | Izzet Delver + Mono-W Initiative ≈30% of meta |
| Aug 26 2024 | Grief | Powered Dimir Reanimator hand disruption |
| Dec 16 2024 | Psychic Frog, Vexing Bauble | Dimir Reanimator/tempo 2× next deck |
| Feb 2025 | Underworld Breach | Cross-format combo engine |
| Mar 31 2025 | Troll of Khazad-dûm, Sowing Mycospawn | Reanimator target + Eldrazi land-denial; open space for control/midrange |
| Nov 10 2025 | Entomb, Nadu Winged Wisdom | Decouple "cheat-a-fatty" from fair decks; power-level |
| May 18 2026 | Undercity Informer | De-power MH3 Oops All Spells |

> **Correction to a common misconception:** Mishra's Workshop and Bazaar of Baghdad are **BANNED in
> Legacy** (legal/restricted only in Vintage). The One Ring, Orcish Bowmasters, Sheoldred remain legal.
> Preordain is **legal** (long-since unbanned).

### Format-defining staples (platform tagging table)
| Role | Cards | Why format-defining |
|---|---|---|
| Dual lands | Underground Sea, Tropical Island, Volcanic Island, … | Untapped, two-typed, fetchable; Legacy-exclusive |
| Fetchlands | Polluted Delta, Flooded Strand, Misty Rainforest, … | Fetch duals, fuel Brainstorm shuffles, delve |
| Land denial | Wasteland, Rishadan Port | Punish nonbasic mana; the "tax/denial" plan |
| Fast mana | Ancient Tomb, City of Traitors, Chrome Mox, Lotus Petal | T1 explosive starts |
| Free interaction | **Force of Will, Force of Negation, Daze, Force of Vigor, Pyroblast** | **THE defining trait — no-mana interaction polices T1/T2 combo** |
| Cantrips | Brainstorm, Ponder, Preordain | Card selection density → blue consistency |
| Discard | Thoughtseize, Duress, Hymn to Tourach | Proactive disruption for combo/reanimator |
| Engines (2024–26) | The One Ring, Orcish Bowmasters, Sheoldred | Card-advantage/inevitability reshaping midrange |
| Combo enablers | Doomsday, Reanimate/Animate Dead, Show and Tell, Sneak Attack, LED+storm, Goblin Charbelcher | Define the combo axis |
| Lock pieces | Chalice of the Void, Trinisphere, Karn the Great Creator, Blood Moon | Prison/stax tax-and-lock |

### Implementation relevance (deck-as-data model)
- **Banned-list validation as blacklist:** `banned_cards` set keyed by canonical name, **with `banned_date` + `ban_reason`** so a deck can be validated against the legality snapshot at a given tournament date (critical for historical meta analysis). Add category predicates (conspiracy/ante/stickers/offensive) and a `printing_legal` flag.
- **Deck-construction validation:** `maindeck≥60`, `sideboard∈{0..15}`, `count(name)≤4` unless basic/override.
- **Staple-card tagging:** `staple_role` enum + boolean `is_free_spell` (the single most analytically valuable Legacy-specific tag for modeling interaction density and meta speed).
- **Mana-base classification:** per-land tags (`is_original_dual`, `is_fetchland`, `is_fast_mana_land`, `is_denial_land`, `produces_colors[]`, `enters_tapped`, `is_fetchable_by[]`) → derive a mana-base archetype signal.

**Sources:** [WotC B&R list](https://magic.wizards.com/en/banned-restricted-list); [WotC Legacy format](https://magic.wizards.com/en/formats/legacy); B&R announcements [May 18 2026](https://magic.wizards.com/en/news/announcements/banned-and-restricted-may-18-2026), [Mar 31 2025](https://magic.wizards.com/en/news/announcements/banned-and-restricted-announcement-march-31-2025), [Dec 16 2024](https://magic.wizards.com/en/news/announcements/banned-and-restricted-december-16-2024); [MTG Wiki Legacy](https://mtg.fandom.com/wiki/Legacy).

---

## Caveats & currency
- Banned list: **high confidence, current** to the May 18 2026 announcement; re-verify against WotC each quarter.
- Underworld Breach exact Legacy ban date should be double-checked (Modern history conflates it).
- CR citations extracted from faithful section mirrors (Fandom/mtg.wiki 403-blocked automated fetch); rule numbers confirmed against fetched text.
