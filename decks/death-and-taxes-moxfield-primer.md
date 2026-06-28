# Death & Taxes

*Legacy · post–Undercity Informer regime · the consensus mono-white hatebears deck, with a locally tuned sideboard option*

A white "tax-and-beatdown" deck: deploy disruptive creatures and deny the opponent's
mana while a Stoneforge package and a stream of free removal grind them out. You're not
the fastest or the most powerful deck — you're the one that makes *their* deck not work,
then wins with efficient bodies. Strong against fair decks and combo (via hatebears +
a deep sideboard); weak to decks that go *under* you (fast combo) or *over* you
(sweepers, big mana).

**Why it's here:** in this session's best-deck / best-call analysis, **Death & Taxes
topped *both* lenses** for the current the local meta-proxy field — highest raw power
(ū ≈ 0.519) *and* best field-weighted positioning (S ≈ 0.523). It preys on the fair
tempo decks the field is full of, and brings real combo hate for the combo half.

---

## Read the gates first

This is a **lean, not a verdict** — same caveats as everything this session:

- **It's a lean:** P(best) for D&T was only ~12.6%, every candidate's CI overlaps, and
  the field model has **~54% coverage** (Jeskai/Esper/TES invisible).
- **Field is regime-clean but global-paper**, not local-field-specific — no geo dimension,
  and the local org data is MWP aggregates with no decklists.
- **D&T's own paper sample** is 24 (current regime) / 68 (4-month) — healthier than most,
  but "paper" still isn't "the local meta."
- **The shape of its win rate is lopsided:** it *crushes* the fair decks (it's
  **Dimir Tempo's nightmare — Dimir is only ~34% into it**) but **folds to fast combo
  (it loses ~76% to Doomsday**, which simply goes under it). It's the field's best deck
  *because the field is fair-heavy* — not because it beats everything.

---

## The game plan

1. **Tax and deny.** Thalia slows every noncreature deck; White Orchid Phantom and
   Wasteland attack nonbasic manabases; Karakas neuters legends (and bounces Marit Lage).
2. **Answer for free.** Solitude (evoke), Swords to Plowshares, and Skyclave Apparition
   exile threats at a rate fair decks can't match — often without spending a card or a turn.
3. **Beat down with the Stoneforge package.** Stoneforge Mystic cheats Meteor Sword /
   Pre-War Formalwear / Lion Sash into play; Recruiter of the Guard and Aether Vial keep
   the disruptive bodies coming.
4. **Hate them out after board.** A deep, tutorable toolbox (Deafening Silence, Disruptor
   Flute, Containment Priest, Grafdigger's Cage, Mindbreak Trap) shuts down whole strategies.

---

## Key cards (oracle text, grounded)

**Disruption**
- **Thalia, Guardian of Thraben** — noncreature spells cost {1} more. Taxes every cantrip,
  counter, combo piece, and removal spell in the format.
- **White Orchid Phantom** `{W}{W}` — 2/2 flying first strike; ETB **destroys a nonbasic
  land** (they get a basic). Repeatable mana denial with blink (Phelia, Flickerwisp).
- **Wasteland** + **Karakas** — kill nonbasics; bounce/neuter legendary creatures
  (including **Marit Lage** from Lands — bounce the token and it's gone).

**Free / efficient removal**
- **Solitude** `{3}{W}{W}` — flash lifelink Elemental; ETB exiles a creature. **Evoke**
  (exile a white card) makes it *free* removal that also leaves a body when hard-cast.
- **Swords to Plowshares** — the best removal in the format; exile a creature, they gain life.
- **Skyclave Apparition** — exile a nonland, nontoken permanent with MV ≤ 4 (creatures,
  artifacts, enchantments, planeswalkers). They get an Illusion token only when it leaves.

**Threats & engine**
- **Stoneforge Mystic** — tutor an Equipment to hand, then cheat it into play. Fetches
  **Meteor Sword** ({7} — ETB destroy any permanent, +3/+3), **Pre-War Formalwear**
  (reanimate a MV ≤ 3 creature + equip), or **Lion Sash** (graveyard hate that grows).
- **Recruiter of the Guard** — tutor any creature with toughness ≤ 2 (Thalia, Phelia,
  White Orchid Phantom, Skyclave…). The toolbox engine.
- **Aether Vial** — drop creatures at instant speed, dodging counters and your own Thalia.
- **Phelia, Exuberant Shepherd** — flash dog; on attack, blink a permanent (your own ETB
  for value, or an opposing blocker/threat out of the way).

**Mana (19):** 5 Plains · 4 Karakas · 4 Marsh Flats · 4 Wasteland · 2 Shadowy Backstreet
(W/B surveil dual — the light black option for sideboard cards + selection).

---

## Sideboard — the consensus 15 (pool-grounded)

| Cards | Role |
|---|---|
| **3 Wrath of the Skies** | Scalable energy sweeper — vs go-wide / bigger creature decks (Eldrazi, stompy, the mirror) |
| **3 Deafening Silence** | One noncreature spell per turn — **brutal vs Doomsday/Storm/Show & Tell** |
| **3 Disruptor Flute** | Name a card: tax it +3 *and* shut off its activated abilities (Painter's Grindstone, LED, a key combo piece) |
| **1 Containment Priest** | Flash — exiles creatures that enter without being cast (Show & Tell, Sneak, Reanimator) |
| **1 Mindbreak Trap** | Free vs Storm (TES, Saga Storm) |
| **1 Grafdigger's Cage** | Shuts off graveyard/library cheats (Reanimator, Dredge, Sneak) |
| **1 Surgical Extraction** | Graveyard exile (Reanimator, the rising Grixis Reanimator) |
| **1 Faerie Macabre** | Free graveyard hate |
| **1 Yorion, Sky Nomad** | Value blink threat / grind finisher |

*This board is **already well-aimed at the local meta** — the field is combo-heavy (Doomsday,
Show & Tell, Painter, Storm ≈ 29%), and Deafening Silence + Disruptor Flute + Containment
Priest + Grafdigger + Mindbreak Trap is a deep anti-combo package. D&T's tutors
(Recruiter, Stoneforge) and Aether Vial make a singleton-heavy toolbox work.*

---

## local sideboard vs. the consensus

The consensus board suits the local meta well as-is. The one local lean is toward your **biggest
matchup, Izzet Delver (~14%)** — a red tempo deck the consensus board doesn't directly
answer. A modest, pool-grounded swap:

| Change | Card | Why |
|---|---|---|
| **IN** | **+2 Path to Exile** | Cheap instant exile-removal for Izzet's threats (DRC, Murktide) + Painter's creatures. A real consensus-pool SB card (~32%), just not in the top 15. *the local meta lean.* |
| **OUT** | **−1 Wrath of the Skies** (3→2) | Three sweepers is a lot for a field that's more combo + spot-removable tempo than go-wide. |
| **OUT** | **−1 Mindbreak Trap** | Storm is only ~6% locally; the rest of the package (Deafening Silence, Disruptor Flute, Containment Priest, Grafdigger) covers combo broadly. |

> **Honesty note:** D&T isn't a deck we have local-meta data for (paper ≠ the local meta, zero local
> decklists), and it isn't your home archetype — so Path to Exile is a *reasoned lean*, not
> observed local tech. The consensus 15 is the safer default; this swap is a hypothesis to
> test if your Izzet matchup feels light.

---

## Matchup notes (vs the local field)

*Reasoned from card function — D&T sideboarding is a deep skill and these are starting points.*

- **Izzet Delver / Dimir Tempo (fair tempo)** — your good matchups. Tax them, trade with
  removal, grind with Stoneforge. IN extra removal (Path to Exile); the combo-hate package
  stays home. Mother-of-Runes-style protection would help vs burn if you run it.
- **Doomsday (your worst — ~24% for you)** — they go under you. Your only real plan is
  **Thalia + Deafening Silence + Disruptor Flute (name Lion's Eye Diamond or Doomsday) +
  Mindbreak/Containment** and a fast clock. Mulligan aggressively for disruption.
- **Show and Tell / Sneak** — Containment Priest + Deafening Silence + Karakas (bounce the
  cheated legend) + Skyclave/Solitude on the fatty. One of your better combo matchups.
- **Painter** — Disruptor Flute naming **Grindstone** turns off the combo outright.
- **Lands** — Wasteland + White Orchid Phantom attack their mana; Karakas answers Marit
  Lage. Grindy but playable.
- **Eldrazi / stompy / the mirror** — Wrath of the Skies is your reset; removal + Karakas
  on their legends.

---

## Mulligan & play tips

- **Keep disruptive hands.** A hand with Thalia/Wasteland + a threat + removal is the goal;
  all lands or all threats with no disruption is a mulligan.
- **Sequence the tax.** Thalia *before* they untap with counter mana; White Orchid Phantom
  /Wasteland to keep them off colors and off the splash.
- **Evoke Solitude is free — but it's card disadvantage.** Use it to break serve or save
  yourself; hard-cast it when you can afford the tempo for the lifelink body.
- **Blink for value.** Phelia and Flickerwisp re-trigger White Orchid Phantom (more land
  destruction), Skyclave, Recruiter, Solitude.
- **Against combo, the clock matters as much as the hate.** Deafening Silence buys turns —
  use them; don't durdle.

---

*Build: Death & Taxes — global consensus current-regime maindeck + pool-grounded consensus
sideboard, with a the local meta lean (+2 Path to Exile). 60 + 15. Tops both best-deck and
best-call lenses for the the local meta-proxy field (ū ≈ 0.519, S ≈ 0.523) — a lean, not a
verdict. The field's best fair deck: crushes tempo, folds to fast combo. ~$650 to build
(Solitude/Stoneforge/Marsh Flats drive the cost).*
