# Doomsday Tempo — the local meta build

*Legacy · post–Undercity Informer regime · stock UB Tempo-Doomsday maindeck, sideboard **re-tuned to the local field** around one finding: the standard grind pivot is flat against the decks the local meta is actually made of.*

A blue-black tempo deck that disrupts, clocks, and grinds like Dimir Tempo — but carries a **Doomsday → Thassa's Oracle** combo as a second way to win. You pick, game by game, whether to play fair or assemble the kill. Against the resilient permanent decks that crush fair tempo (Death & Taxes, prison, big mana) you combo *under* them; against the blue mirrors that punish all-in combo you fall back to the fair plan.

**The maindeck is the stock current-regime consensus list, untouched.** Everything in this build that's specific to the local meta lives in the **sideboard** — and it's a sharper sideboard than the consensus default, because we audited the consensus board against the actual local field and found it half-aimed at the wrong things.

---

## Why this build for the local meta (read the gates first)

This is a **lean, not a verdict.** On a regime-clean current field, Doomsday Tempo positions roughly even with — slightly ahead of — dedicated Dimir Tempo, and it inverts your worst Dimir matchups (Death & Taxes 35%→72%, Energy 38%→60%) by going under them. But:

- **Regime currency:** the local paper sample is thin and only partly current-regime; the read leans on the global paper corpus as a proxy.
- **Coverage & significance:** roughly a third of the field has little reliable matchup data, every candidate's confidence interval overlaps, and **every sideboard win-rate swing below is statistically non-significant** — directional, not proven.
- **Pilot skill:** Doomsday has a steep learning curve and rewards reps; local win-rates are pilot-inflated.

**The risk this build is built around:** your single biggest the local meta matchup, **Izzet Delver (~11–12%), is Doomsday's worst (~41%)** — counters + a fast clock + burn punish a combo deck sitting at half life. The blue/cantrip decks (Izzet, the mirror, Show and Tell, Beanstalk, Jeskai, Esper) are **~45% of the field.** So the sideboard's first job is to win the blue matchups — and that's exactly where the consensus board comes up short.

---

## The sideboard thesis (what this build changes and why)

We audited the consensus Doomsday sideboard against the local field, card by card. Two things fell out:

**1. The standard grind pivot doesn't beat the blue decks.** Barrowgoyf is the consensus "transform into a fair deck" card, but in the matchup data it's **flat where it matters** — Barrowgoyf vs Izzet Delver `−0` (n=87), vs the Dimir mirror `−2` (n=133). It grinds *midrange* fine; it doesn't beat *tempo*. The card that beats blue tempo — **Orcish Bowmasters** — is in your stock list **zero times.**

> **Orcish Bowmasters** `{1}{B}` — *Flash. When it enters and whenever an opponent draws a card except the first in each of their draw steps, deal 1 damage to any target. Then amass Orcs 1.* Every Brainstorm, Ponder, and Delver draw-step extra now costs them a creature or a life — it's the premier punisher of the entire blue plurality, and a flash body that ambushes their threats. The ~14-point gap between Dimir-vs-Izzet (55%) and Doomsday-vs-Izzet (41%) is, in large part, this card.

**2. Some of the consensus hate is dead in this field.** **Surgical Extraction** has no real targets — the local meta has no Reanimator/Dredge — and it shows up *negative* in the data (a dead card you're forced to draw). And against the field's three "both-modes-bad" holes, the stock deck has **no answer at all**: it runs Hurkyl's Recall 3% of the time and Toxic Deluge ~never.

So this build makes a **targeted reallocation** — cut what's dead or flat *in this meta*, add the tempo card the blue plurality demands plus the two missing answers, and **keep the hate that's actually working** (Hydroblast: Painter +8 / Energy +31; Consign vs Show and Tell; Force of Negation as combo insurance).

| Out (dead / flat vs the local meta) | In (the local meta-demanded) |
|---|---|
| 1 Surgical Extraction — *dead, no graveyard decks* | **4 Orcish Bowmasters** — *beats the blue ~45%* |
| 2 Barrowgoyf (4→2) — *flat vs Izzet/mirror* | **1 Hurkyl's Recall** — *Blue Artifacts/Kappa, the missing answer* |
| 2 Dauthi Voidwalker — *graveyard half dead here* | **1 Toxic Deluge** — *Eldrazi creature sweep* |
| 1 Long Goodbye + 1 Jace — *flat / combo-redundant* | +1 Fatal Push (1→2) |

Every card in this build is one you already own across your two decks — nothing to acquire.

---

## The two game plans

**Plan A — Fair tempo.** Tamiyo and Murktide backed by Thoughtseize, Force of Will, Daze, and Wasteland — nearly your Dimir Tempo game, and post-board it gets *real* teeth with Orcish Bowmasters + Barrowgoyf. Use it when comboing is too risky: open counters, fast clocks.

**Plan B — The Doomsday kill.** Resolve Doomsday, build a five-card pile, dig through it in one turn, win with Thassa's Oracle. Use it when the coast is clear — they're tapped out, out of counters (Thoughtseize confirms), or you're racing a fair/prison deck you can't beat the long way.

The deck's skill is knowing **which plan, when** — and threatening both.

---

## How the combo works

The pieces (oracle text, exact):

- **Doomsday** `{B}{B}{B}` — *Search your library and graveyard for five cards and exile the rest. Put them on top of your library in any order. You lose half your life, rounded up.* (Dark Ritual powers it out turn 1–2.)
- **Thassa's Oracle** `{U}{U}` — *When it enters, look at the top X cards where X is your devotion to blue; **if X ≥ the number of cards in your library, you win.***
- **Free / cheap draws to eat the pile:** your **draw step**, **Street Wraith** (cycle — pay 2 life), **Edge of Autumn** (cycle — sac a land), **Consider**, **Brainstorm/Ponder**, and **Lion's Eye Diamond** (sac → three mana for the Oracle).
- **Protection & redundancy:** **Cavern of Souls** naming **Merfolk** makes Thassa's Oracle **uncounterable**; **Unearth** `{B}` returns a countered/discarded Oracle.

**The principle:** build the pile so Thassa's Oracle is the **last** card, stack free/cheap draws above it, dig your library down to (at most) your blue devotion in one turn, then cast the Oracle. **Pile construction is the core skill of the deck.** Don't fire a Doomsday you can't finish.

### A worked pile

Devotion counts `{U}` symbols on your permanents — **Thassa's Oracle is `{U}{U}`, so it pays for itself**: with just the Oracle out, a library of **2 or fewer wins.**

A clean five-card pile (top → bottom): **Street Wraith · Edge of Autumn · Thassa's Oracle · buffer · buffer.**

1. Kickoff draw (draw step / held Consider) → **Street Wraith** to hand. *(library: 4)*
2. Cycle Street Wraith (pay 2 life) → draw **Edge of Autumn**. *(library: 3)*
3. Cycle Edge of Autumn (sac a spare land) → draw **Thassa's Oracle**. *(library: 2)*
4. Cast Thassa's Oracle `{U}{U}`. Devotion 2 ≥ library 2 → **you win.**

**Mana math** is why the rituals exist: in one turn you need `{B}{B}{B}` for Doomsday *and* the kickoff *and* `{U}{U}` for the Oracle. **LED is the closer** — cast Doomsday off lands, crack LED (discarding your spent hand) for the `{U}{U}{U}` that finishes; it's also how you go off at instant speed on their end step. **Thoughtseize first** to strip the counter and confirm the path.

---

## The maindeck (stock current-regime consensus)

**Combo core (13):** 4 Doomsday, 4 Dark Ritual, 2 Lotus Petal, 1 Lion's Eye Diamond, 1 Thassa's Oracle, 1 Unearth.
**Card selection (15):** 4 Brainstorm, 4 Ponder, 1 Consider, 4 Flow State, 1 Street Wraith, 1 Edge of Autumn.
**Threats (6):** 4 Tamiyo, Inquisitive Student · 2 Murktide Regent.
**Disruption (9):** 4 Force of Will, 3 Daze, 2 Thoughtseize.
**Manabase (17):** 4 Underground Sea, 1 Undercity Sewers, 1 Island, 1 Swamp · 4 Polluted Delta, 1 Flooded Strand, 1 Misty Rainforest · 1 Cavern of Souls (name Merfolk) · 3 Wasteland.

---

## The local-meta sideboard (15)

| Cards | Role |
|---|---|
| **4 Orcish Bowmasters** | The tempo engine vs the blue plurality — punishes every cantrip/Delver draw, ambushes threats at flash. The headline change. |
| **2 Barrowgoyf** | Grind threat vs midrange; lifelink flips burn races. (Trimmed from 4 — flat vs the tempo decks.) |
| **2 Force of Negation** | Combo/control insurance — Show and Tell, the mirror, Saga Storm. Near-universal for a reason. |
| **2 Hydroblast** | Red hate — Painter (the deck's confirmed lift here), Izzet's Bolt/DRC, Energy. |
| **2 Fatal Push** | Cheap removal — D&T, Delver, Energy, Eldrazi's smaller bodies. |
| **1 Consign to Memory** | Counters colorless spells / key triggers — Show and Tell's payoff, Eldrazi's Thought-Knot ETB / Chalice. |
| **1 Hurkyl's Recall** | The **Blue Artifacts** answer — returns *all* their artifacts (targets the player, so it ignores Kappa Cannoneer's ward and wipes the Construct tokens). Also resets Painter's Grindstone. |
| **1 Toxic Deluge** | The **Eldrazi** sweep — `−X/−X`, ward-proof; X=4 clears Thought-Knot and the early board (pay 4 life). |

---

## Matchup & sideboard guide

*Plans are starting points. Against blue, transform to fair tempo (Plan A). Against fair/prison/grindy decks, combo under them (Plan B).*

### The matchup the build is for

**Izzet Delver** (worst + most common) — **full transform into a fair UB tempo deck.**
- **IN:** 4 Orcish Bowmasters, 2 Barrowgoyf, 2 Fatal Push, 2 Hydroblast
- **OUT:** 4 Doomsday, 4 Dark Ritual, 1 Lion's Eye Diamond, 1 Thassa's Oracle
- Why: their counters + clock + burn make the combo a trap at half life. Out-tempo them instead — Bowmasters taxes their cantrips and clocks them, Barrowgoyf's lifelink undoes the burn race, Hydroblast kills DRC/Bolt. This is the matchup the whole reallocation exists to fix.

### Combo decks — keep the kill, add insurance

**Show and Tell / Black Saga Storm / Doomsday mirror**
- **IN:** 2 Force of Negation, 1 Consign to Memory
- **OUT:** 2 Murktide Regent, 1 Street Wraith
- Why: race their cheat with a protected, faster kill; Consign counters the Show-and-Tell payoff's ETB.

### The three holes — patch, don't chase

**Painter** (~even, the one hole you can flip) — disrupt the combo, attack the red half.
- **IN:** 2 Hydroblast, 1 Hurkyl's Recall
- **OUT:** 3 Daze, 1 Street Wraith — *(Daze is weak against their Ancient Tomb starts)*
- Why: Hydroblast is your measured edge here; Hurkyl's bounces Grindstone + their artifact mana.

**Blue Artifacts** (unfavored) — the bounce is your only real swing.
- **IN:** 1 Hurkyl's Recall, 4 Orcish Bowmasters, 2 Fatal Push
- **OUT:** 4 Doomsday, 1 Lion's Eye Diamond, 1 Thassa's Oracle, 1 Dark Ritual
- Why: Hurkyl's wipes the board including Kappa (ward-proof, player-target); Bowmasters punishes Emry/Urza's-Saga draws and pings the tokens.

**Eldrazi** (unfavored — buy turns, don't expect to dominate)
- **IN:** 1 Toxic Deluge, 2 Fatal Push, 4 Orcish Bowmasters
- **OUT:** 3 Daze, 1 Street Wraith, 1 Edge of Autumn, 2 Lotus Petal
- Why: Toxic (X=4) resets Thought-Knot + the early board; Push/Bowmasters trade and chip. Daze/fast-mana are weak vs Ancient Tomb. You're playing for ~48% — competitive, not favored.

### Favored — combo under them

**Death & Taxes** (your best) — combo under the hatebears; kill Thalia so she can't tax you.
- **IN:** 2 Fatal Push · **OUT:** 3 Daze (slow them less than removal does) — *(mostly stay combo)*

**Energy** — go over the top; bring removal for the early creatures.
- **IN:** 2 Fatal Push, 2 Hydroblast · **OUT:** 3 Daze, 1 Street Wraith

**Midrange (Jeskai / Azorius / Black / Esper)** — transform and grind.
- **IN:** 4 Orcish Bowmasters, 2 Barrowgoyf, 2 Fatal Push · **OUT:** 4 Doomsday, 4 Dark Ritual

---

## Mulligan & play tips

- **Keep hands that do *a* thing well**, not hands that need everything. A disruptive tempo hand (Thoughtseize + threat + counter) is a fine keep with no combo; so is a fast, protected combo hand. Half-and-half and slow is a mulligan.
- **Don't fire a Doomsday you can't finish** — count your draws and `{U}{U}` first; a pile you can't close just halves your life and shows your hand.
- **Thoughtseize before you go off** — take the counter, confirm the path, then combo.
- **Post-board vs blue, you are a tempo deck** — lead with Bowmasters/Tamiyo and protect the clock; the combo is a bluff you rarely need.
- **Name Merfolk with Cavern** by default (uncounterable Oracle).
- **Sequence black mana carefully** — Flooded Strand / Misty only fetch your Island-typed duals; lead Polluted Delta when you need Swamp.

---

*Build: Tempo Doomsday — stock current-regime consensus maindeck, **locally tuned sideboard**. 60 + 15. Combo-front, transforms into fair UB tempo vs the blue decks. The sideboard cuts the consensus board's meta-dead slots (Surgical / excess Barrowgoyf / Dauthi / Long Goodbye / Jace) for the tempo card the blue plurality demands (Orcish Bowmasters) plus the two answers the stock deck lacks (Hurkyl's, Toxic Deluge). **Every sideboard swing here is directional, not significant — and "Bowmasters lifts the blue matchups" is an inference from Dimir's numbers + card mechanics, not a measurement.** Register it and play the blue games to settle it.*
