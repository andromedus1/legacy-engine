# Orzhov Energy (Overlord / Phelia) — comprehensive Legacy primer

Snapshot: 2026-08-04. This guide is for the exact 75 in
`decks/orzhov-energy-overlord-moxfield.txt`. It is the W/B cut of the black-splash Energy deck —
Amped Raptor and Goblin Bombardment traded away for Solitude, Overlord of the Balemurk, Phelia, and
Staff of the Storyteller. Every baseline exchange has equal cards in and out.

**Read the honesty section before you trust a single number in the matchup tables.** This camp is
real and has 35 tournament lists behind it, but **0% of its own match record is in the current ban
regime.** Everything below is a lean, not a result.

## The 75

```text
4 Guide of Souls             4 Swords to Plowshares
4 Ocelot Pride               4 Thoughtseize
4 Ajani, Nacatl Pariah       4 Cabal Therapy
4 Orcish Bowmasters          2 Staff of the Storyteller
3 Phelia, Exuberant Shepherd
3 Overlord of the Balemurk   21 lands
3 Solitude

Sideboard
4 Deafening Silence          2 Static Prison
3 Disruptor Flute            2 Surgical Extraction
2 Containment Priest         2 Wrath of the Skies
```

Lands: `4 Marsh Flats · 4 Scrubland · 4 Wasteland · 2 Arid Mesa · 2 Karakas · 2 Plains ·
1 Bloodstained Mire · 1 Shadowy Backstreet · 1 Swamp`

## What this deck is and why it exists

The Mardu list wins with **Amped Raptor** — a {1}{R} 2/1 first striker that reads "you get {E}{E},
then if you cast it from your hand, exile cards from the top of your library until you exile a
nonland card. You may cast that card by paying an amount of {E} equal to its mana value." In a deck
where every maindeck nonland costs two or less, that's four free spells plus energy. It is the card
advantage engine, and it is red.

Cutting red costs you Raptor, Hexing Squelcher, and Goblin Bombardment. The camp replaces that
engine with a black-and-white one:

- **Overlord of the Balemurk** — {3}{B}{B} 5/5 Enchantment Creature Avatar Horror with
  "Impending 5—{1}{B}" and "Whenever this permanent enters or attacks, mill four cards, then you may
  return a non-Avatar creature card or a planeswalker card from your graveyard to your hand."
- **Solitude** — {3}{W}{W} 3/2 flash lifelink Elemental Incarnation, "When this creature enters,
  exile up to one other target creature. That creature's controller gains life equal to its power,"
  with "Evoke—Exile a white card from your hand." Free unconditional removal that leaves a creature
  card in your graveyard for Overlord to buy back.
- **Phelia, Exuberant Shepherd** — {1}{W} 2/2 flash Dog, "Whenever Phelia attacks, exile up to one
  other target nonland permanent. At the beginning of the next end step, return that card to the
  battlefield under its owner's control. If it entered under your control, put a +1/+1 counter on
  Phelia."
- **Staff of the Storyteller** — {1}{W} artifact; ETB a 1/1 flying Spirit, "Whenever you create one
  or more creature tokens, put a story counter on this artifact," and "{W}, {T}, Remove a story
  counter: Draw a card." Every Ocelot Pride Cat, every Ajani token, every Spirit charges it.

The trade in one line: **you give up the format's best free-spell engine and gain unconditional
free removal plus a recursion engine that never runs out of cards.** You get a deck that beats fair
blue harder and grinds better, and loses the ability to punch through a fast combo turn with tempo
alone.

One naming note so the classifier doesn't mislead you: the engine labels this **Energy**, but
Guide of Souls' Angel pump is your *only* maindeck energy sink. Energy is a minor subtheme here, not
the deck's motor. Wrath of the Skies and Static Prison in the board are the other two payoffs.

## The engine — the interaction the whole deck is built on

**Phelia attacks, exiles your own impending Overlord.**

Cast Overlord on turn two for its impending cost of {1}{B}. Per the reminder text it "enters with
five time counters and isn't a creature until the last is removed" — so it mills four and returns a
creature or planeswalker immediately, then sits as a *noncreature enchantment* that creature removal
can't touch. Later, attack with Phelia and target your own Overlord. It's exiled and returns to the
battlefield at the beginning of that same end step. **A permanent returning from exile was not
cast, so impending never applies** — it comes back as a full 5/5 creature, triggers "whenever this
permanent enters" for a second mill-four-and-return, and Phelia gets a +1/+1 counter.

Two mana on turn two becomes a 5/5, two cards of graveyard value, and a growing Phelia.

Supporting details that matter at the table:

- Overlord returns "a **non-Avatar** creature card or a planeswalker card." It cannot return another
  Overlord. It *can* return Solitude (Elemental Incarnation), Guide, Ocelot, Bowmasters, Phelia, and
  Ajani's front face (a creature card whose back face is a planeswalker).
- Solitude's evoke exiles a white card from hand and Solitude is sacrificed — straight into your
  graveyard, straight back to your hand off the next Overlord trigger. This is the deck's grind loop.
- Overlord returning is "another creature you control enters," so **Guide of Souls triggers**: gain
  1 life, get {E}.
- **Sequencing:** Overlord's delayed return and Ocelot Pride's end-step trigger both happen at the
  beginning of your end step, and you order your own triggers. Put the Overlord return **first** —
  Guide's lifegain then satisfies Ocelot's "if you gained life this turn" check.
- While impending, Overlord is not a creature: it can't attack, can't block, and **can't be
  sacrificed to Cabal Therapy's flashback**. It also dodges Swords, Solitude, and Push.
- Phelia can blink Staff of the Storyteller for a fresh Spirit token (and therefore a fresh story
  counter), or exile an opposing blocker/threat for a turn to force damage through.
- Karakas returns any legendary creature: it saves Phelia and front-face Ajani from removal, and
  answers a cheated-in legend. It cannot target transformed Ajani (a planeswalker).

## Card roles

- **Guide of Souls** — best turn-one play. Guide before Ocelot makes Ocelot's entry gain life,
  turning on the Cat that end step. Bank energy; spend three only when flying and +2/+2 change the
  race or dodge removal.
- **Ocelot Pride** — engine, first striker, Ajani enabler, Cabal Therapy fodder, Staff charger.
  Ascend is a bonus, not a plan to contort toward.
- **Ajani, Nacatl Pariah** — two bodies for two mana and the best bridge to the long game. Another
  Cat dying transforms him. Therapy flashback can sacrifice his token at the exact right moment.
- **Orcish Bowmasters** — the reason this deck beats cantrip decks. Hold it for the Brainstorm when
  the trigger decides the game; deploy proactively when the clock or the Army body matters more.
- **Swords to Plowshares / Solitude** — Swords is your cheap answer, Solitude is your free one.
  Solitude is the only card in the deck that answers a resolved Marit Lage, Thought-Knot Seer, or a
  Show-and-Tell'd fatty at instant speed for zero mana.
- **Thoughtseize / Cabal Therapy** — eight discard spells. Thoughtseize before Therapy converts a
  guess into exact information. Therapy's flashback needs a *creature* to sacrifice, which is why the
  token engines matter.
- **Staff of the Storyteller** — the slow card-advantage tap. Two copies, never more; it needs a
  token engine already running to be worth a slot.
- **Wasteland** — treat it as a spell unless the rest of the hand already casts its first two turns.
  Do not strand Guide, Thoughtseize, or a two-drop just because a target exists.
- **Arid Mesa is not a Boros leftover.** It fetches "a Mountain or **Plains** card" — Scrubland and
  Shadowy Backstreet are both `Land — Plains Swamp`, so Mesa finds your untapped W/B dual. Same for
  Bloodstained Mire ("Mountain or **Swamp**").

## Sideboard cards and their jobs

- **4 Deafening Silence** — "Each player can't cast more than one noncreature spell each turn."
  The single best card against Show and Tell, Doomsday, and Saga Storm. It also taxes *you*: your
  Thoughtseize, Therapy, Swords, and Staff activation all compete for that one slot. Sequence
  deliberately. Your creatures are unaffected, which is why this deck can afford four.
- **3 Disruptor Flute** — {2} flash, name a card: it costs {3} more and its activated abilities are
  shut off unless they're mana abilities. Names Grindstone, Chalice of the Void, Show and Tell,
  Doomsday, Force of Will, Urza's Saga — whatever the read demands.
- **2 Containment Priest** — "If a nontoken creature would enter and it wasn't cast, exile it
  instead." Answers the Show and Tell creature branch, Reanimator, and Cephalid. **Read the nonbo
  section before boarding these in.**
- **2 Static Prison** — {W}: exile target nonland permanent an opponent controls until it leaves,
  you get {E}{E}, and you sacrifice it at your first main phase unless you pay {E}. It ignores mana
  value, so it answers a resolved Omniscience, Marit Lage, or Thought-Knot Seer for one mana.
  Guide keeps it fed; without Guide it dies on turn three.
- **2 Surgical Extraction** — Doomsday, Saga Storm, Reanimator, and any linchpin you've just
  discarded.
- **2 Wrath of the Skies** — {X}{W}{W}: "You get X {E}, then you may pay any amount of {E}. Destroy
  each artifact, creature, and enchantment with mana value less than or equal to the amount of {E}
  paid." **You may pay banked energy, not just X** — with Guide online you can cast it for {W}{W} and
  still sweep for three. It is symmetric: your Cats and Ajani tokens are mana value 0, and paying
  five kills your own impending Overlord.

### Nonbos you must remember

- **Containment Priest exiles your own Ajani when he transforms** (he returns to the battlefield
  without being cast), and it **exiles the Overlord that Phelia blinks**. Two of your best engines
  turn off. Board Priest only when the Show-and-Tell / reanimation branch is actually demonstrated,
  and when it's out, stop blinking Overlord and stop killing your own Cats.
- **Deafening Silence** limits you to one noncreature spell per turn — Thoughtseize, Therapy,
  Swords, and Staff's activation all queue behind it.
- **Wrath of the Skies** kills your own token board. Sweep before you widen, not after.
- **Impending Overlord is an enchantment**, so Wrath at five and opposing enchantment removal reach
  it while creature removal doesn't.
- **Cabal Therapy flashback needs a creature.** An impending Overlord and a Staff are not creatures.
- **Surgical Extraction needs a card in a graveyard.** If you've already locked their yard, it may
  have no target.

## Mulligans

An unknown-matchup keep needs all four:

- a colored source and a credible first two turns (Wasteland is not a colored source);
- a turn-one engine or a discard spell;
- follow-through — a second creature, a land, Ajani, Overlord, or interaction;
- pressure plus disruption, or enough of one that the other can arrive.

This deck's curve is lower than it looks — Overlord costs {1}{B} on turn two and Solitude costs zero
— but it has **no cantrips and no free card advantage in the first two turns.** You cannot dig out of
a bad hand. Be more willing to mulligan than you would be with the Mardu list, which has Raptor to
paper over a flat draw.

Matchup adjustments:

- **Fast combo:** require turn-one disruption, or a postboard hate start plus pressure.
- **Tempo / Wasteland decks:** want two functioning sources or a fetch that finds Scrubland. Be
  skeptical of one nonbasic plus a Wasteland as the whole mana base.
- **Creature decks:** a one-drop or Ajani plus Swords or Solitude.
- **Control:** layered threats and the Overlord recursion loop. One threat plus four removal spells
  is a weak hand here.
- **On the play:** Thoughtseize and Wasteland improve. **On the draw:** Swords, Bowmasters, Solitude,
  and stable mana improve; speculative Therapy and Wasteland-as-land get worse.

Examples. Keep `Marsh Flats, Scrubland, Guide, Ocelot, Ajani, Swords, Overlord` unknown. Keep
`Marsh Flats, Scrubland, Wasteland, Thoughtseize, Therapy, Bowmasters, Overlord` versus combo.
Mulligan `Wasteland, Karakas, Plains, Solitude, Solitude, Overlord, Staff` — it cannot function
before turn four. Mulligan a beautiful Guide/Ocelot/Ajani/Swords fair hand against known fast combo
with no interaction in it.

## Cabal Therapy naming ladder

1. A revealed hand: take the decisive remaining card, or a duplicate.
2. Observed actions: fetches, cantrips, a pass, a protected card — all narrow the range.
3. Archetype plus your intended line: name what beats your *next play*, not the deck's most famous
   card.
4. Truly blind: only when a miss is affordable. Name the common card most capable of beating your
   immediate plan.

Flash Therapy back when the hand is known, when the body is temporary or removal-bound or surplus,
when the sacrifice flips Ajani, or when the exact card opens a winning turn. Do not sacrifice your
only engine or shorten a lethal attack to buy information.

---

## Honesty section — read this before the matchup tables

Five gates, weakest first.

1. **Regime currency: 0%.** This camp's own 84-match record contains **zero matches in the current
   (post-2026-05-18 Undercity Informer) regime.** 61% sits in the prior post-Entomb regime, 39% is
   older. The camp peaked at 13 lists in December 2025 and has produced **5 lists in all of 2026,
   one since March.** Meanwhile Boros/Mardu Energy went from 26 lists in December to 36–67 per
   month across 2026. The format's Energy decks moved to red and this camp did not follow.
2. **Sample tier.** The Orzhov value camp is 35 decks / 84 decisive matches — *evolving* tier, not
   established. The shared-core Energy matchup cells cited below are archetype-level and dominated by
   Boros/Mardu lists, so they describe the Guide/Ocelot/Ajani/Bowmasters shell you share, **not this
   list.** The engine has no separate matchup row for this camp.
3. **Field coverage.** Against the current local field, positioning runs at **67% coverage** —
   Azorius Midrange, Jeskai Midrange, Black Midrange, Black Saga Storm, and Esper Midrange have no
   n≥30 cells at all. Five of the local meta's fifteen slices are unmodeled.
4. **CI separation: none — and the flattering comparison was window-mismatched.** The camp's 57.1%
   (raw 48-36, n=84) is an **all-time** number, and Mardu's all-time 53.5% (raw 516-449, n=965) is
   dragged down by pre-Amped-Raptor-boom lists. Window both to the same era (since 2025-12-22, the
   engine's Energy era pool) and **Mardu is 57.7% (raw 263-193, n=456) and 58.6% in the current
   regime (raw 75-53, n=128)** — while this camp has n=11 on that window. On a fair window the Mardu
   list is *ahead*, not behind. Also note the honest denominator: **all 77 W/B Energy lists together
   run 50.3% (raw 74-73, n=147)** — the 57.1% only appears once you select the Overlord/Solitude/
   Phelia subset after the fact.
5. **Confounds — this is the big one.** Split the camp's 84 matches by pilot:
   **Lemure90 / Carroz / Trohck / hoojchoons are 16-4 (80.0%, CI [59.2%, 92.8%]); everyone else is
   32-32 (exactly 50.0%, CI [38.1%, 61.9%]).** Four repeat pilots carry the entire edge. Eleven of the
   35 lists are theirs. The camp's headline win rate is close to "good pilots play it well." Sub-shell
   choice explains nothing by comparison (pure-Energy 56.9% n=72 vs the Stoneforge/Vial toolbox 58.3%
   n=12). Card-level and sideboard-level signals in this project are presence-correlational, never
   causal.

**The one number that is current, established, and clean:** the Orzhov Overlord/Phelia *package*
inside Death & Taxes runs **57.9% in the current regime (raw 62-45, n=107, CI [48.5%, 66.9%])**, and
56.5% across all of 2026 (raw 231-178, n=409). That is the real evidence that Overlord + Phelia +
Solitude is a good package *right now*. It is evidence for the cards, not for this shell.

**What this actually means.** The deck you asked about exists, has a coherent 35-list consensus, and
posted a good record — in late 2025, mostly in four pilots' hands. Its component package is thriving
in 2026 inside a different archetype. Nobody has posted a current-regime result with the Energy
version. You are not brewing from nothing; you are reviving a camp that went quiet, with strong
independent evidence that its key cards are still good — but the corpus does **not** support
"this beats the Mardu list." On a window-matched read, Mardu is ahead. Play this because you want
the grind plan and the Overlord loop, not because the numbers say it's better. Treat it as a live
hypothesis to validate with reps.

**The one matchup that should worry you:** the Overlord package is **0.33 against Energy** (raw
8-16, n=24, 2026) and 0.14 in the current regime (raw 1-6, n=7 — speculative, treat as a flag not a
number). The Mardu list is 0.50 in that same matchup (raw 11-11, n=22). Amped Raptor decks appear to
beat Overlord decks. In the local meta, Energy is only 3.7% of the field, so this is survivable. In a field
where Energy is 5.8% and climbing, it is a real cost of the switch.

## Matchups and sideboarding

Two data sources are cited per matchup where they exist, and they are *different things*:

- **core** = the engine's archetype-level Energy row, since 2025-08-01, shown as `shrunk% | raw%
  n=`. It describes the shared Guide/Ocelot/Ajani/Bowmasters shell, mostly Boros/Mardu lists.
- **pkg** = the Death & Taxes Overlord camp's 2026 raw record — a proxy for what
  Overlord/Phelia/Solitude does in the current format.

Where the two disagree, that disagreement *is* the information. Do not average them.

Ordered by share of the current local field.

### 1. Izzet Delver — 11.2% of the local meta

`core 63.3% | raw 64.5% n=107 (established)` · `pkg 0.70 (raw 19-8, n=27)`

Both sources agree this is your best matchup. **Their plan:** Dragon's Rage Channeler and Murktide
behind Daze, Force of Will, Bolt, and Cori-Steel Cutter. **Counter:** you go wider than their removal
and Bowmasters punishes every cantrip. Fetch stable mana, save Swords for Murktide or a large Cutter
token, kill Channeler before delirium. Solitude answers the threat they protected with Force.
Therapy names: Bolt blind, Force before your key spell, Cutter after a setup cantrip.

**Board:** no change. Your maindeck is already the correct 60 here.

### 2. Show and Tell — 10.3% of the local meta

`core 47.8% | raw 46.9% n=113 (established)` · `pkg 0.55 (raw 21-17, n=38)`

**Their plan:** cantrips and Stock Up plus protection into Show and Tell for Omniscience or a large
legend. **Counter:** discard the enabler, keep Karakas up for the legend, use Deafening Silence to
break setup-plus-combo, and remember **Static Prison answers a resolved Omniscience** — it exiles a
nonland permanent regardless of mana value. Solitude answers the creature branch at instant speed for
free. Mulligan fair-value hands. Therapy name: Show and Tell, then Force, Omniscience, or the pivot.

**Board:** `+4 Deafening Silence, +2 Static Prison; -4 Swords to Plowshares, -2 Staff of the
Storyteller`. Containment Priest is *available* but it exiles your own transformed Ajani and blinked
Overlord — only add `+2 Priest; -2 Cabal Therapy` when their creature branch is confirmed and you are
willing to stop using both engines.

### 3. White Beanstalk — 7.5% of the local meta

`core 51.4% | raw 50.0% n=32 (evolving)` · `pkg 0.36 (raw 4-7, n=11 — speculative)`

The sources disagree and the pkg cell is too thin to trust; read this as "even, possibly worse."
**Their plan:** Beanstalk/Stock Up card advantage, exile removal, Phelia, planeswalkers, sweepers.
**Counter:** pressure in waves rather than committing everything into a sweeper; the Overlord loop
wins a long attrition game they can't answer permanently. Hold the third threat. Karakas fights their
Phelia. Therapy names: the known sweeper, Swords, or their draw engine.

**Board:** `+2 Wrath of the Skies; -2 Staff of the Storyteller`. Against a build with six or more
creature threats, `+2 Wrath, +2 Static Prison; -2 Staff, -2 Cabal Therapy`.

### 4. Dimir Tempo — 7.5% of the local meta

`core 63.0% | raw 63.9% n=133 (established)` · `pkg 0.68 (raw 23-11, n=34)`

Your other premium matchup, and the camp's own thin record agrees (raw 9-2, n=11). **Their plan:**
cheap threats behind discard, Daze/Force, removal, Wasteland, Kaito; Murktide, Barrowgoyf,
transformed Tamiyo, and postboard Massacre reverse a go-wide board. **Counter:** be the go-wide deck.
Fetch stable mana, kill Tamiyo before it transforms, save Swords for the big blocker, and keep Ajani
plus the Overlord loop as your Massacre insurance — they cannot beat a recursion engine with
one-for-ones. Therapy names: Brainstorm blind, Push to protect an engine, informed Massacre or Kaito.

**Board:** no change.

### 5. Jeskai Midrange — 7.5% of the local meta

**No matchup cell in either source.** Unmodeled — this is one of the five the local meta slices with no
data. Play it as a fair blue matchup: layered threats, respect sweepers, don't overextend, lean on
Overlord recursion to out-grind them. Therapy names: the sweeper, Force, or their draw engine.

**Board:** `+2 Wrath of the Skies; -2 Staff of the Storyteller` if they're creature-forward;
otherwise no change.

### 6. Azorius Midrange — 6.5% of the local meta

**No established cell** (n=5, online only — ignore it). Their Phelia/Tamiyo/Stifle/Daze shell is a
fair blue deck; treat it like Dimir Tempo but respect the exile removal. Karakas answers their
Phelia and their legends. Deny profitable Phelia attacks by keeping a relevant blocker. Therapy
names: Swords, Force, Phelia, or a known Wrath.

**Board:** no change. Add `+2 Static Prison; -2 Staff` only if they're on planeswalkers you can't
otherwise answer.

### 7. Black Midrange — 6.5% of the local meta

**No matchup cell.** Discard, efficient threats, removal, graveyard value. **Counter:** go wide,
preserve engines, Swords the threat that dominates combat, and win the attrition war with Overlord —
this is the archetype the recursion engine was built to beat. Avoid blind Therapy without a list read.

**Board:** no change. If Reanimate or an opposing Overlord is central, `+2 Surgical Extraction; -2
Cabal Therapy`.

### 8. Black Saga Storm — 6.5% of the local meta

**No matchup cell.** Graveyard-and-Saga-driven storm. **Counter:** discard the payoff, land Deafening
Silence (it breaks the multi-spell turn), Surgical the recursion engine, and clock them.

**Board:** `+4 Deafening Silence, +2 Surgical Extraction; -4 Swords to Plowshares, -2 Staff of the
Storyteller`.

### 9. Death & Taxes — 5.6% of the local meta

`core 55.1% | raw 55.3% n=47 (evolving)` · `pkg 0.50 (raw 7-7, n=14 — speculative)`

Note that "pkg" here is the Overlord camp playing *against other D&T*, so it's a near-mirror and
reads even. **Their plan:** Vial, mana denial, Thalia, Stoneforge, Solitude, Recruiter, blink, and
often the same Overlord/Phelia package you have. **Counter:** fetch untapped white, kill the
equipment and blink engines, and out-grind them — your Overlord loop plus eight discard spells is the
edge. Karakas fights their legends. Therapy names: Vial, Solitude, Stoneforge, or Skyclave.

**Board:** `+3 Disruptor Flute; -2 Staff of the Storyteller, -1 Cabal Therapy`. Flute names Aether
Vial. Against Vial-light mono-white, `+2 Static Prison; -2 Staff` instead.

### 10. Doomsday — 5.6% of the local meta

`core 44.2% | raw 41.2% n=51 (evolving)` · `pkg 0.19 (raw 3-13, n=16)`

**Your worst modeled matchup, and both sources agree — the package version looks materially worse
than the shared core.** Take this seriously: 0.19 on n=16 is thin but it points the same direction as
the core cell and the same direction as the current-regime slice (raw 1-4, n=5). **Their plan:**
resolve Doomsday through discard and counters, then traverse a five-card pile. **Counter:** attack
hand, mana, and draw access while clocking. Deafening Silence stops ritual-or-cantrip *into*
Doomsday. Surgical after a discard spell strips the pile. You have no counterspells, so discard plus
clock is the entire plan. Therapy names: Doomsday blind, Force or Daze before your hate, a known draw
effect once observed.

**Board:** `+4 Deafening Silence, +2 Surgical Extraction, +3 Disruptor Flute; -4 Swords to
Plowshares, -3 Solitude, -2 Staff of the Storyteller`. Flute names Doomsday. Against a creature
pivot in game three, return `+3 Solitude; -3 Disruptor Flute`.

### 11. Eldrazi — 5.6% of the local meta

`core 56.1% | raw 56.5% n=62 (evolving)` · `pkg 0.50 (raw 6-6, n=12 — speculative)`

**Their plan:** sol lands into Thought-Knot Seer, Fleshraker, Kozilek's Command, postboard Chalice.
**Counter:** this is where Solitude earns its slot — free, unconditional, exiles a Thought-Knot at
instant speed with no mana. Race with width, Swords the threat that breaks combat, and Wasteland only
to buy a full turn. Therapy names: Command, Thought-Knot, or Chalice.

**Board:** `+2 Static Prison, +3 Disruptor Flute; -3 Cabal Therapy, -2 Staff of the Storyteller`.
Flute names Chalice of the Void or Ancient Tomb.

### 12. Painter — 4.7% of the local meta

`core 58.8% | raw 60.5% n=38 (evolving)` · `pkg 0.90 (raw 9-1, n=10 — speculative)`

**Their plan:** Painter's Servant plus Grindstone, Welder/Engineer recursion, Blasts, Saga, Karn.
**Counter:** kill the recursion creatures, name Grindstone with Flute (which shuts the activated
ability, not just the cast), Surgical a combo half after removal or discard. Therapy names: Painter's
Servant, Pyroblast before your hate, Engineer, or the known half.

**Board:** `+3 Disruptor Flute, +2 Surgical Extraction; -3 Cabal Therapy, -2 Staff of the
Storyteller`.

### 13. Blue Artifacts / Affinity — 3.7% of the local meta

`core 49.6% | raw 48.5% n=68 (evolving)` · `pkg 0.57 (raw 13-10, n=23)`

**Their plan:** cheap artifacts into Opal, Emry, Thoughtcast, Urza's Saga, and large synergy threats.
**Counter:** Flute names Urza's Saga or Emry; keep Swords and Solitude because static and triggered
engines survive artifact hate. Wasteland the Saga. Therapy names: Force before your hate, or Emry.

**Board:** `+3 Disruptor Flute, +2 Static Prison; -3 Cabal Therapy, -2 Staff of the Storyteller`.

### 14. Energy mirror (Boros / Mardu) — 3.7% of the local meta

`core 50% (mirror row, uninformative)` · `pkg 0.33 (raw 8-16, n=24)`

**This is the matchup you lose by switching to Orzhov, and the honesty section flags it.** Their
Amped Raptor generates free cards you cannot match, and Goblin Bombardment beats you in combat and
protects their engine from your removal. **Counter:** preserve material, Swords their engine or a
profitable Ajani, Wrath of the Skies at two or three sweeps their Cats without killing your Overlord,
and your Solitudes are better than any removal they have. The grind is your only real edge — do not
try to race.

**Board:** `+2 Wrath of the Skies, +2 Static Prison; -2 Cabal Therapy, -2 Staff of the Storyteller`.

### 15. Esper Midrange — 3.7% of the local meta

**No matchup cell.** Treat as fair blue with exile removal and better sweepers. Layered threats,
Overlord grind, don't overextend. Therapy names: the sweeper, Force, or their draw engine.

**Board:** `+2 Wrath of the Skies; -2 Staff of the Storyteller`.

### Global-field matchups the local meta doesn't currently have

Keep these plans available for online play and for out-of-town events.

**Lands** — `core 51.1% | raw 50.0% n=46` · `pkg 0.65 (raw 13-7, n=20)`. The package version looks
better, plausibly because Overlord recursion beats Loam attrition. Save Wasteland for Stage or
Depths, keep Karakas for Marit Lage (and Static Prison as the backup — it exiles the token
regardless of mana value), and deploy only enough bodies to pay Tabernacle.
**Board:** `+2 Surgical Extraction, +3 Disruptor Flute; -4 Swords to Plowshares, -1 Staff`. Flute
names Life from the Loam.

**Tron** — `core 39.0% | raw 29.4% n=17 (speculative, online only)`. Bad and under-sampled. Wasteland
the Nexus or the missing piece, Flute the engine, and attack. **Board:** `+3 Disruptor Flute, +2
Static Prison; -4 Swords to Plowshares, -1 Solitude`.

**Grixis Reanimator / Oops! All Spells** — no core cell; `pkg 0.22 vs Oops (raw 2-7, n=9)`. You have
no Leyline of the Void and only two Surgical, so your graveyard hate is thin — this is a known hole
in the 15. Deafening Silence is unusually good here: with Entomb banned they need a discard outlet
*and* a reanimation spell, and Silence lets them cast only one noncreature spell per turn.
**Board vs Reanimator:** `+4 Deafening Silence, +2 Surgical Extraction, +2 Containment Priest;
-4 Cabal Therapy, -2 Swords to Plowshares, -2 Staff of the Storyteller`. Keep two Swords and all
three Solitude for the resolved fatty — Therapy is the weak card against a deck that *wants* cards in
its graveyard. Accept that Priest turns off Ajani's transform and the Phelia/Overlord blink for the
rest of the game. If you expect these decks in volume, cut two Disruptor Flute for two Faerie Macabre
— free, dodges Force *and* Deafening Silence (discarding it is an activated ability, not a spell), and
the camp runs it in 40% of lists.

**Cephalid Breakfast / Aluren** — no cells. Deafening Silence plus Containment Priest is the
package; Priest stops the Aluren creature branch only after Aluren resolves, not the loop itself.
Same Priest nonbo applies.

## Tournament shorthand

- **Fair blue (44% of the local meta):** develop stable mana, go wide, board lightly, respect sweepers.
  This is why you're playing the deck.
- **Combo (22% of the local meta):** discard plus Deafening Silence plus a clock. Trim Swords and Staff.
- **Creature decks:** keep Swords and Solitude; board only hate that answers a demonstrated engine.
- **Graveyard combo:** your weakest board. Surgical plus Priest plus pressure, and know the Priest
  nonbo before you sleeve it up.
- **When uncertain:** board fewer narrow cards. The main 60 is cohesive and beats fair decks on its
  own.

## Build notes and deviations

The 60 is the camp consensus (n=35 lists), anchored on Lemure90's 2026-07-05 5-0 — the only
current-year list in the camp. Consensus inclusion across the camp: Guide 100%, Marsh Flats 100%,
Swords 100%, Ocelot 100%, Bowmasters 100%, Karakas 100% (avg 2.0), Wasteland 97%, Scrubland 97%,
Solitude 94% (avg 3.2), Phelia 94% (avg 3.1), Thoughtseize 91%, Overlord 89% (avg 2.9), Therapy 77%,
Ajani 74%, Staff 54% (always exactly 2 when present).

Two deliberate deviations, both in the sideboard:

- **Cut Damping Sphere and Erode** from Lemure90's board. the local meta has no Tron or Post, and a fifth
  removal spell is worse than a fifth answer to combo.
- **Added 2 Static Prison and 2 Containment Priest** in their place. Static Prison is a one-mana
  catch-all that ignores mana value (Omniscience, Marit Lage, Thought-Knot) and the camp runs it in
  43% of lists; Priest addresses the local meta's 10.3% Show and Tell, with the Ajani/Overlord nonbo
  documented above.

**Paper cost.** Against the maintainer's binder this is 56 cards to acquire, roughly **$1,530** at cheapest
printings — and **$860 of that is four Scrubland at $215 each.** The budget mana base, if you want
one: `4 Marsh Flats · 2 Arid Mesa · 2 Godless Shrine · 2 Shadowy Backstreet · 2 Silent Clearing ·
4 Wasteland · 2 Karakas · 2 Plains · 1 Swamp` (21) saves about **$830**. What you actually pay for it:
Godless Shrine enters untapped only if you pay 2 life, Silent Clearing charges 1 life per activation,
and Shadowy Backstreet always enters tapped — a real life-total tax in a deck that already runs 4
Thoughtseize and 6 fetches, which matters most against Delver and burn-ish draws. Note that Marsh
Flats and Arid Mesa can fetch Godless Shrine and Shadowy Backstreet (both `Land — Plains Swamp`) but
**cannot** fetch Silent Clearing, which has no basic land type.

## Evidence and refresh boundary

Every number here comes from `data/legacy.duckdb` as of 2026-07-30 (67,581 decks). Camp definition:
archetype matching `Energy`, mainboard Guide of Souls, zero red cards in the 75, ≥3 black cards
maindeck, no blue or green, and ≥4 combined copies of Overlord/Solitude/Phelia. Camp cohort n=35
lists, 84 decisive matches, 0% current-regime. Package proxy: Death & Taxes lists with mainboard
Overlord of the Balemurk, n=107 current-regime decisive matches. Archetype-level cells from
`report matchups --a Energy --b <opp> --since 2025-08-01`, shown shrunk|raw with n per the project's
triple-display rule. Field weights from `decks/local-field-current.txt` (103 of 107 players
modeled, post-2026-05-18).

The engine's own camp discovery (`discover run --archetype Energy`) splits Energy into three
established camps — Sand Scout (n=377), Thoughtseize (n=174), Cabal Therapy (n=131) — and does
**not** surface an Orzhov camp, because the Orzhov lists fall into the 123 noise decks or into the
black-splash camps alongside Mardu. The camp in this primer was found by hand-querying color
identity, not by the clustering pass. That is a gap in the taxonomy, not evidence the camp isn't real.

Refresh this primer after a ban, a major release, a sideboard change, or after **2026-09-04** —
and refresh it immediately if any pilot posts a current-regime result with this shell, because that
would be the first such data point in existence.
