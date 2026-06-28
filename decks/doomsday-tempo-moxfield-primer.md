# Doomsday Tempo

*Legacy · post–Undercity Informer regime · the consensus UB Tempo Doomsday maindeck, sideboarded for the Boulder paper meta*

A blue-black tempo deck that disrupts, clocks, and grinds like Dimir Tempo — but
carries a **Doomsday → Thassa's Oracle** combo as a second way to win. You choose,
game by game, whether to play the fair tempo game or assemble the kill. Against the
resilient permanent decks that crush fair tempo (Death & Taxes, Lands, prison), you
combo *under* them; against the blue mirrors that punish all-in combo, you fall back
to the fair plan.

**The maindeck is the stock current-regime consensus list, untouched.** All of the
Boulder/meta adaptation lives in the sideboard — so the deck you practice is the deck
the broader field has already tuned, and your local read is expressed only where it
belongs.

---

## Why this deck for Boulder (read the gates first)

This is a **lean, not a verdict.** On a **regime-clean** field (current-regime
composition, adaptive ban-aware matrix) Doomsday positions at **S ≈ 0.50 [0.465,
0.539], ~54% coverage**, *ahead of* Dimir Tempo (≈0.483) for the current meta. But:

- **Regime currency:** your local Boulder 4-month sample is only ~29% current-regime;
  the regime-clean read uses global paper as a proxy (not Boulder-specific).
- **Coverage:** ~44% of the field has no matchup data (Jeskai/Esper/TES/Stiflenought).
- **CIs overlap** every candidate — no deck is *statistically* best.
- The local "Doomsday 65%" is **pilot-skill-inflated**, and **Doomsday has a steep
  learning curve** — the deck rewards reps.

**The honest case:** Doomsday inverts your worst Dimir-Tempo matchups (Death & Taxes
34%→76%, Lands 34%→56%) by going under them. **The risk:** your biggest Boulder
matchup, **Izzet Delver (~14%), is Doomsday's worst (~40%)** — counters + a fast clock
+ burn punish a combo deck sitting at half life. The sideboard is built around that
problem.

---

## The two game plans

**Plan A — Fair tempo.** Tamiyo and Murktide backed by Thoughtseize, Force of Will,
Daze, and Wasteland — nearly your Dimir Tempo game. Use it when comboing is too risky:
open counters, fast clocks, graveyard hate.

**Plan B — The Doomsday kill.** Resolve Doomsday, build a five-card pile, dig through
it in one turn, win with Thassa's Oracle. Use it when the coast is clear — they're
tapped out, out of counters (Thoughtseize confirms), or you're racing a combo/prison
deck you can't beat fairly.

The deck's skill is knowing **which plan, when** — and threatening both.

---

## How the combo works

The pieces (oracle text, exact):

- **Doomsday** `{B}{B}{B}` — *Search your library and graveyard for five cards and exile
  the rest. Put them on top of your library in any order. You lose half your life,
  rounded up.* (Dark Ritual powers it out turn 1–2; you set a five-card stack and torch
  the rest of your deck.)
- **Thassa's Oracle** `{U}{U}` — *When it enters, look at the top X cards where X is your
  devotion to blue; **if X ≥ the number of cards in your library, you win.***
- **Free / cheap draws to eat the pile:** your **draw step**, **Street Wraith** (cycle —
  pay 2 life), **Edge of Autumn** (cycle — sacrifice a land), **Consider**, **Brainstorm/
  Ponder**, and **Lion's Eye Diamond** (sac → three mana for the Oracle).
- **Protection & redundancy:** **Cavern of Souls** naming **Merfolk** makes Thassa's
  Oracle **uncounterable** (this is a *stock* consensus card — the counter-protection a
  blue field needs comes free with the list). **Unearth** `{B}` returns a countered/
  discarded Oracle from the graveyard. **Jace, Wielder of Mysteries** (sideboard) is a
  third, hard-to-interact-with win condition.

**The principle:** build the pile so Thassa's Oracle is the **last** card, stack
free/cheap draws above it, dig your library down to (at most) your blue devotion in one
turn, then cast the Oracle. The exact pile depends on the mana and draws you have when
Doomsday resolves — **pile construction is the core skill of the deck.** The common
shape is `[mana source] [free draw] [free draw] [setup] [Thassa's Oracle]`, run
top-to-bottom in one turn. Don't fire a Doomsday you can't finish.

---

## The maindeck (stock current-regime consensus)

**Combo core (13)**
- **4 Doomsday**, **4 Dark Ritual** — the engine and the ritual that casts it ahead of curve.
- **2 Lotus Petal**, **1 Lion's Eye Diamond** — free/fast mana for Doomsday or the Oracle.
- **1 Thassa's Oracle** — the kill (one copy is enough with Unearth + Cavern as backups).
- **1 Unearth** — rebuy a countered Oracle (or a creature MV ≤ 3) for `{B}`.

**Card selection (15)**
- **4 Brainstorm**, **4 Ponder**, **1 Consider** — dig to pieces or threats.
- **4 Flow State** — `{1}{U}` dig-3-take-1 (take-2 with an instant + sorcery in the yard);
  also fuels Murktide.
- **1 Street Wraith**, **1 Edge of Autumn** — "free" cantrips that double as pile-diggers.

**Threats (6)** — **4 Tamiyo, Inquisitive Student**, **2 Murktide Regent**.

**Disruption (9)** — **4 Force of Will**, **3 Daze**, **2 Thoughtseize**.

**Manabase (17)** — 4 Underground Sea, 1 Undercity Sewers, 1 Island, 1 Swamp ·
4 Polluted Delta, 1 Flooded Strand, 1 Misty Rainforest · **1 Cavern of Souls** (name
Merfolk) · **3 Wasteland**.

---

## Sideboard (15) — consensus base, tuned for Boulder + the post-ban global shift

| Cards | Role | vs consensus |
|---|---|---|
| **4 Barrowgoyf** | Transform into a fair grind deck (lifelink flips burn races) | consensus |
| **2 Dauthi Voidwalker** | Evasive clock **+ graveyard hate** (DRC delirium, Murktide delve, Reanimator) | consensus |
| **2 Force of Negation** | Combo/control counter; the only answer to Cori-Steel Cutter | consensus |
| **1 Long Goodbye** | Uncounterable removal (Thalia, DRC, MV ≤ 3 threats) | consensus |
| **1 Jace, Wielder of Mysteries** | Resilient win condition vs Jeskai/Esper | consensus |
| **1 Fatal Push** | Cheap removal | consensus (−1) |
| **1 Consign to Memory** | Colorless spells / triggers (Show & Tell fatties, Tron) | consensus (−1) |
| **2 Hydroblast** | **Boulder tweak:** red is ~21% locally (Izzet 14% + Painter 7%) — kills DRC, Cori-Steel Cutter, Bolt | **+2 off-consensus** |
| **1 Surgical Extraction** | **Meta-shift tweak:** Grixis Reanimator rose +1.9% post-ban; also the mirror + Dredge | **+1 off-consensus** |

*The two labeled deviations (Hydroblast, Surgical) are reasoned from your field + the
global movers — **hypotheses to test at the table, not proven local tech.** The cuts
(−1 Fatal Push, −1 Consign, −Bitter Triumph) track what the global meta shed since the
ban (Eldrazi −2.0%, Mystic Forge −2.3%).*

---

## Matchup & sideboard guide

*Plans are starting points. Against blue decks, transform (Plan A); against fair/prison
decks, combo under them (Plan B).*

### Unfavored — the build's focus

**Izzet Delver** (worst + most common, ~14%) — **full transform into a fair UB deck.**
- IN: 4 Barrowgoyf, 2 Dauthi Voidwalker, 2 Hydroblast, 2 Force of Negation, 1 Fatal Push, 1 Long Goodbye
- OUT: 4 Doomsday, 4 Dark Ritual, 1 Lion's Eye Diamond, 1 Thassa's Oracle, 1 Street Wraith, 1 Lotus Petal
- Why: their counters + clock + burn make the combo a trap, and you're at half life. Out-grind them instead — Barrowgoyf's lifelink undoes their burn race, Dauthi shuts off DRC delirium + Murktide delve, Hydroblast kills DRC/Cutter/Bolt. **Cori-Steel Cutter is your problem card** — nothing removes it once it lands; counter it with FoN on the cast or kill the Monk tokens and race.

**Jeskai / Esper control** (no data — play to not lose to counters)
- IN: 4 Barrowgoyf, 2 Dauthi Voidwalker, 1 Jace, 2 Force of Negation
- OUT: 4 Doomsday, 1 Lion's Eye Diamond, 2 Lotus Petal, 1 Thassa's Oracle, 1 Street Wraith
- Why: grind with threats + Jace as the inevitability they can't easily answer. You *can* keep a slim combo here (they punish a stumble slower than Izzet).

### Favored

**Death & Taxes** (your best) — combo under their hatebears; kill Thalia so she can't tax you.
- IN: 1 Fatal Push, 1 Long Goodbye, 2 Dauthi Voidwalker
- OUT: 3 Daze (mana denial), 1 Street Wraith

**Show and Tell** — race their cheat with a protected, faster kill.
- IN: 2 Force of Negation, 1 Consign to Memory
- OUT: 2 Murktide, 1 Street Wraith

**Lands** — go under the lock; Wasteland slows them, Marit Lage doesn't matter if you win first.
- IN: 1 Surgical Extraction (Loam / Field of the Dead)
- OUT: 1 Murktide

### Roughly even

**Painter** (red combo, ~7% local) — disrupt the combo, attack the red half.
- IN: 2 Force of Negation, 2 Hydroblast
- OUT: 3 Daze, 1 Street Wraith

---

## Mulligan & play tips

- **Keep hands that do *a* thing well**, not hands that need everything. A disruptive
  tempo hand (Thoughtseize + threat + counter) is a fine keep with no combo; so is a
  fast, protected combo hand. Half-and-half and slow is a mulligan.
- **Don't fire a Doomsday you can't finish** — halving your life and stacking five known
  cards with no payoff hands the game away. Count draws and mana first.
- **Thoughtseize before you go off** — take the counter, confirm the path, then combo.
- **Name Merfolk with Cavern** by default (uncounterable Oracle); name Dragon only if
  Murktide is your actual wincon that game.
- **Sequence black mana carefully** — Flooded Strand / Misty can only fetch your
  *Island-typed* duals for black; lead on Polluted Delta when you need Swamp.
- **Pick your plan by matchup, then board state.** Blue counters up → transform. Fair
  deck durdling → combo.

---

*Build: Tempo Doomsday — stock current-regime consensus maindeck, Boulder-tuned
sideboard. 60 + 15. Positions ≈0.50 vs a regime-clean current field (CI [0.465, 0.539],
~54% coverage) — a lean, not a verdict. Inverts Dimir Tempo's worst matchups at the cost
of Izzet Delver; sideboard transforms into fair UB tempo vs the blue decks. The two
off-consensus sideboard cards (Hydroblast, Surgical) are local hypotheses — validate
them at the table.*
