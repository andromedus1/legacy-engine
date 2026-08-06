# Death & Taxes — Yorion / Overlord (the current build) — comprehensive Legacy primer

Snapshot: 2026-08-04. This guide is for the exact 80+15 in
`decks/death-and-taxes-yorion-overlord-moxfield.txt`. Every baseline exchange has equal cards in and out.

**Read this first: it's 80 cards on purpose.** Yorion, Sky Nomad's companion clause is "Your starting
deck contains at least twenty cards more than the minimum deck size." Every current top-finishing D&T
list in the corpus is an 80-card Yorion deck — that is not a quirk of one pilot, it's what the
archetype now is.

## The 80

```text
4 Aether Vial                4 Thoughtseize            31 lands + 2 MDFC:
4 Thalia, Guardian of Thraben 4 Swords to Plowshares     5 Plains · 1 Swamp
4 Stoneforge Mystic          4 Solitude                  4 Karakas · 4 Wasteland
4 Recruiter of the Guard     2 Skyclave Apparition       4 Marsh Flats · 4 Prismatic Vista
4 Phelia, Exuberant Shepherd 3 White Orchid Phantom      3 Scrubland · 2 Shadowy Backstreet
4 Overlord of the Balemurk   1 Flickerwisp               2 Flooded Strand
2 Witch Enchanter (MDFC)     1 Cloak and Dagger          1 Arid Mesa · 1 Windswept Heath
2 Pre-War Formalwear         1 Lion Sash · 1 Meteor Sword

Sideboard
3 Deafening Silence   2 Disruptor Flute   1 Containment Priest   1 Mindbreak Trap
3 Wrath of the Skies  2 Erode             1 Faerie Macabre       1 Surgical Extraction
                                                                 1 Yorion, Sky Nomad ← companion
```

## What this deck is

It is **not** a go-wide creature deck. It is a **tutor-and-blink toolbox with a mana-denial tax
package**, and the difference matters for every decision you make. The Energy decks win by putting
four bodies on the board by turn three and pointing them at your face. This deck wins by answering
the specific card that beats it, then grinding you out of resources while Thalia and Wasteland make
everything you do cost more.

Three overlapping engines:

1. **Aether Vial into a tutored toolbox.** Vial at two puts Thalia, Phelia, Stoneforge, or Lion Sash
   in at instant speed under a counterspell. **Recruiter of the Guard** — "you may search your library
   for a creature card with **toughness 2 or less**" — reads on *toughness*, not power, which is more
   permissive than people expect. It finds Thalia (2/1), Phelia (2/2), Skyclave (2/2), White Orchid
   Phantom (2/2), Flickerwisp (3/1), Witch Enchanter (2/2), Cloak and Dagger (2/2), another Recruiter
   (1/1), Lion Sash (1/1), Stoneforge (1/2), and **Solitude (3/2)**. The only creature in the deck it
   can't find is **Overlord (5/5)**.
2. **The blink web.** Every ETB in this deck is a reusable effect if you can re-trigger it, and there
   are four ways to do that: **Yorion** ("exile any number of other nonland permanents you own and
   control. Return those cards to the battlefield at the beginning of the next end step"), **Phelia**,
   **Flickerwisp**, and **Pre-War Formalwear** (which returns a creature card with mana value 3 or
   less from your graveyard to the battlefield and attaches itself to it). Blinking Overlord, Skyclave,
   Witch Enchanter, White Orchid Phantom, Recruiter, and Solitude is where the card advantage lives.
3. **Mana denial.** 4 Wasteland, 3 White Orchid Phantom ("destroy up to one target nonbasic land"),
   4 Thalia taxing noncreature spells, and 4 Karakas. Against greedy mana bases this is often the
   whole game.

**Overlord of the Balemurk** ({3}{B}{B}, Impending 5—{1}{B}; "Whenever this permanent enters or
attacks, mill four cards, then you may return a non-Avatar creature card or a planeswalker card from
your graveyard to your hand") is a 4-of here rather than a 3-of because this shell has four blink
outlets instead of one. Cast it turn two for {1}{B} as a noncreature enchantment, then convert it into
a 5/5 with a fresh ETB whenever a blink is convenient. **A permanent returning from exile was not
cast, so impending never applies** — it comes back a full creature immediately.

The **Yorion turn** is the deck's haymaker: blink Overlord + Skyclave + Witch Enchanter + White Orchid
Phantom in one shot and you've drawn a card, exiled a permanent, destroyed an artifact, and blown up
a land, off a 5-mana 4/5 flyer you cast from outside the game.

## Card roles and the details that decide games

- **Aether Vial** — set it to 2 and leave it there most games; 2 is Thalia / Phelia / Lion Sash /
  Stoneforge. Vialing in a creature during their turn under Force of Will is why this deck beats
  counterspell decks.
- **Thalia** — 4-of, and she is a huge part of the combo matchups. First strike also brawls well
  against Delver and Channeler.
- **Stoneforge Mystic** into **Meteor Sword** ({7} equipment, "When this Equipment enters, destroy
  target permanent," +3/+3, Equip {3}) — Stoneforge puts it onto the battlefield without paying {7},
  so the destroy trigger fires immediately. That's the "kill any permanent" button. **Pre-War
  Formalwear** is the other Stoneforge target and it doubles as reanimation. **Lion Sash** is graveyard
  hate on a body that grows: "{W}: Exile target card from a graveyard. If it was a permanent card, put
  a +1/+1 counter on this permanent."
- **Solitude** — free removal, and every evoked copy leaves a creature card in your graveyard for
  Overlord to buy back. Do not evoke it when you can afford to hard-cast and keep the 3/2 lifelink body
  for a Yorion blink.
- **Witch Enchanter // Witch-Blessed Meadow** — the free-roll slot. Front face is a {3}{W} 2/2 that
  destroys an opposing artifact or enchantment; back face is a white land that enters untapped if you
  pay 3 life. Play it as a land when you're short, as a Disenchant-on-a-body when you're not. This is
  why the deck can run 33 land-capable slots without flooding.
- **White Orchid Phantom** — {W}{W} 2/2 flying first strike that destroys a nonbasic land. They get a
  *basic* back, tapped. Against Lands, Tron, and 4-color piles this plus Wasteland is the plan.
- **Skyclave Apparition** — exiles a nonland, nontoken permanent with mana value 4 or less. Remember
  the drawback: when Skyclave *leaves*, the owner makes an X/X Illusion where X is the exiled card's
  mana value. Blinking Skyclave hands them a token — usually still worth it, but count the board first.
- **Cloak and Dagger, Entwined** ({1}{W}{B} 2/2 deathtouch lifelink) — a Recruiter-findable
  Thoughtseize on a body: reveal their hand and exile a nonland card (or a creature) until Cloak and
  Dagger leave. Tutorable disruption is why a 1-of matters.
- **Karakas** — 4 copies. Bounces any legendary creature: saves your own Thalia and Phelia from
  removal, and answers most cheated-in legends. It does **not** stop Thassa's Oracle (not legendary).
- **Flickerwisp** — 3/1 flying, exiles another target permanent and returns it at the next end step.
  Also a tempo play on an opposing land, and it can blink your own Overlord.

### Nonbos and traps

- **Containment Priest is a real cost here, not a free hate card.** "If a nontoken creature would
  enter and it wasn't cast, exile it instead" — that turns off **Aether Vial**, **Yorion's return**,
  **Phelia's return**, **Flickerwisp's return**, and **Pre-War Formalwear's reanimation**. With Priest
  on the battlefield this deck loses four of its engines. Board it only against decks that actually
  cheat creatures in, and expect to play a much worse deck for that game.
- **Mindbreak Trap costs {2}{U}{U} and you have no blue mana.** It is in the board strictly for its
  alternative cost: "If an opponent cast three or more spells this turn, you may pay {0}." It's a
  storm/Doomsday-pile answer only. You can never hard-cast it.
- **Blinking Skyclave gives them an Illusion token** (see above).
- **Overlord mills you four.** With Lion Sash and Faerie Macabre that's usually fine, but against
  opposing Surgical Extraction and Bitter Ordeal-style effects you're feeding them information and
  targets.
- **Thalia taxes your own** Swords, Thoughtseize, Vial, and equipment. Sequence the noncreature spell
  before she lands when the extra {1} matters this turn.
- **Wrath of the Skies is symmetric** and your board is wide; it also kills your own Vial and equipment.

## Mulligans on 80 cards

This is the part most people get wrong. An 80-card deck sees a *smaller fraction* of itself, so
individual 1-ofs are less findable — but this deck doesn't care, because **Recruiter and Vial convert
"a creature" into "the right creature."** Keep hands that produce a Vial or a Recruiter, not hands
that happen to contain the perfect answer.

A keep needs:

- **two lands minimum, and white by turn one or two.** With 33 land-capable slots and 6 fetches you'll
  hit them; a one-land hand is a mulligan even with Vial.
- **an engine** — Aether Vial, Recruiter, Stoneforge, or Overlord for {1}{B}.
- **a reason the first three turns matter** — Thalia, Vial, Wasteland, Thoughtseize, or a Phelia.

Ship hands that are pure lands-and-answers with no engine; on 80 cards you will not naturally draw
into a plan the way a 60-card cantrip deck does.

Matchup adjustments:

- **Fast combo:** you want Thalia or Thoughtseize on turn one, full stop. A hand with Stoneforge and
  Meteor Sword and no disruption loses to Doomsday before it does anything.
- **Blue tempo:** Vial is your best card — it beats Daze, Force, and Stifle. Keep it over almost
  anything else.
- **Greedy mana (Lands, Tron, 4c piles):** Wasteland plus White Orchid Phantom plus any two-drop is a
  premium keep on the play.
- **Creature decks:** Swords, Solitude, Skyclave, and enough lands to cast them.

---

## Honesty section

1. **Sample and currency are genuinely good here** — the best of anything in this thread. The
   Overlord camp has **757 decks** and **1,429 decisive matches all-time**, with **107 matches in the
   current regime**, all established tier. This is not a fringe read.
2. **The camp beats the rest of its own archetype, holding the archetype fixed:**

| | decks | all-time | since 2025-12-22 | current regime |
|---|---|---|---|---|
| **D&T [Overlord] camp** | 757 | 54.6% · raw 780-649 n=1429 · est | 56.6% · n=412 · est | **57.9% · raw 62-45 n=107 · est** |
| D&T [no Overlord] | 1057 | 50.2% · raw 1563-1550 n=3113 · est | 52.3% · n=260 · est | 52.9% · raw 74-66 n=140 · est |
| D&T parent (both) | 1814 | 51.6% · raw 2343-2199 n=4542 · est | 54.9% · n=672 · est | 55.1% · raw 136-111 n=247 · est |

   All-time the two camps' intervals **separate** (54.6% [52,57] vs 50.2% [48,52]) on established
   samples — that is the strongest card-package evidence in this whole investigation. In the current
   regime they overlap ([48,67] vs [45,61]), so treat the *current* +5 as directional.
3. **Field coverage against Boulder is only 53%** — positioning returns S = 0.533 [0.482, 0.583] with
   Azorius Midrange, Jeskai Midrange, Black Midrange, Black Saga Storm, Esper Midrange, Painter, and
   White Beanstalk all uncovered. Seven of fifteen Boulder slices are unmodeled.
4. **The no-Overlord half is growing.** June 2026 was the first month it outnumbered the Overlord camp
   (48 to 34), and July was close (24 to 31). Current-regime totals are 86 / 85 — a dead heat. Something
   is pulling pilots back toward the mono-white Flagstones/Thalia/Ghost Quarter build. Watch it.
5. **Confound:** the current-regime Overlord sample is concentrated in a handful of grinders
   (IsolatedSystem, yoshiwata, Alico, misteriggins, Carroz), same caveat as everywhere else.

### The Doomsday hole is real, and it is the reason to think hard about this deck

You called this correctly. Two independent measurements:

| | vs Doomsday |
|---|---|
| **D&T [Overlord] camp** (hand tally) | **14.7%** · raw 5-29 n=34 · evolving |
| D&T [no Overlord] (hand tally) | 36.0% · raw 18-32 n=50 · evolving |
| **D&T parent** (engine cell, since 2025-08-01) | **27.8%** raw · shrunk 35.9% · n=36 · evolving |
| **Energy** (engine cell, since 2025-08-01) | **41.2%** raw · shrunk 44.2% · n=51 · evolving |

The gap between D&T and Energy against Doomsday is **13.4 points on raw rate**, both on evolving-tier
samples, and my independent all-time hand tally of D&T (27.4%, raw 23-61, n=84) reproduces it. The CIs
overlap so this is directional rather than a verdict — but it is the *same* direction in three separate
measurements, and the mechanical story is coherent: Doomsday does not care about Wasteland, White Orchid
Phantom, Skyclave, Stoneforge, or Karakas, and this deck's clock is slow (Recruiter tutors, Overlord
impends, 80 cards dilute). Energy simply kills them faster and has Bowmasters to punish the draw-seven.

**What is *not* established:** that Energy is *favored* against Doomsday — 41.2% is still an underdog —
and that the Cabal Therapy/Squelcher camp specifically is better than the Energy average. That camp's
Doomsday cell is **4-2, n=6, speculative.** It points your way, it cannot carry the claim yet.

### Correction to what I told you earlier

I used the D&T Overlord camp's 57.9% as a "the package is current and good" proxy for the Orzhov Energy
deck. **You're right that that overreached.** The 57.9% belongs to *this* strategy — Vial, Recruiter,
mana denial, a four-outlet blink web — and it comes bundled with a 14.7% Doomsday cell that the Energy
shell does not have. What the D&T data legitimately supports is the narrower internal claim in gate 2
above: **within a W/B creature deck, adding the Overlord package beats not adding it.** It says nothing
about how a go-wide energy deck performs, and I should have drawn that line the first time.

## Matchups and sideboarding

Ordered by share of the current Boulder field. Cells are the engine's D&T archetype row since
2025-08-01 as `shrunk% | raw% n=`, plus the Overlord camp's own hand tally where n allows. Note the
camp row and the parent row often disagree — where they do, that disagreement is the information.

**Two boarding rules specific to this deck.** First, **your real sideboard is 14 cards, not 15** —
Yorion occupies a slot and can never be boarded in, because it's your companion. Second, **every swap
must be equal in and out** or you lose Yorion: the companion condition is checked against your starting
deck each game, so the moment your main dips to 79 you no longer have a companion. Every plan below is
balanced for exactly that reason; do not "just take out two cards" the way you would in a 60.

### 1. Izzet Delver — 11.2% of Boulder
`camp 0.70 (raw 19-8, n=27, 2026)`. Vial is the card. It beats Daze, Force, and Stifle, and Thalia
taxes their whole deck. Swords the Murktide, Skyclave the Cutter, and let Overlord grind them out —
they run out of cards, you don't. Karakas protects Thalia and Phelia. Therapy of choice is Thoughtseize
naming Force before your Overlord turn. **Board:** no change.

### 2. Show and Tell — 10.3% of Boulder
`camp 0.55 (raw 21-17, n=38, 2026)` · `current regime 0.30 (raw 3-7, n=10 — speculative, a warning)`.
Thalia taxes Show and Tell to {3}{U}. Karakas answers a legend. Thoughtseize the enabler. Static hate
isn't available to you, so this is a discard-plus-clock plan with Deafening Silence as the breaker.
**Board:** `+3 Deafening Silence, +1 Mindbreak Trap; -1 Lion Sash, -1 Meteor Sword, -1 Pre-War
Formalwear, -1 Cloak and Dagger`. Containment Priest looks right and mostly isn't — read the nonbo
section; add it only if you're willing to switch off Vial and every blink for the game.

### 3. White Beanstalk — 7.5% of Boulder
`camp 0.36 (raw 4-7, n=11 — speculative)`. Near-mirror-ish grind. Thalia and Wasteland tax their
Beanstalk/Stock Up engine; Skyclave and Meteor Sword answer the resolved threat; Karakas fights their
Phelia. Don't overextend into Wrath. **Board:** `+3 Wrath of the Skies; -1 Thoughtseize, -1 Cloak and
Dagger, -1 Flickerwisp`.

### 4. Dimir Tempo — 7.5% of Boulder
`camp 0.68 (raw 23-11, n=34, 2026)` · `current regime 7-0 (n=7 — speculative)`. Your best matchup.
Vial under Daze, Thalia taxing removal, Karakas saving legends, Overlord out-grinding one-for-ones.
Save Swords for Barrowgoyf or Murktide. **Board:** no change.

### 5. Jeskai Midrange — 7.5% of Boulder
**No cell in either source.** Fair blue with burn: keep Vial, respect sweepers, and lean on White
Orchid Phantom plus Wasteland if their mana is greedy. **Board:** `+3 Wrath of the Skies; -1 Cloak and
Dagger, -1 Meteor Sword, -1 Lion Sash` if they're creature-forward, else no change.

### 6. Azorius Midrange — 6.5% of Boulder
**No established cell.** Treat as Dimir Tempo with better sweepers and their own Phelia. Karakas is
excellent — it answers their Phelia and their legends. **Board:** no change.

### 7. Black Midrange — 6.5% of Boulder
**No cell.** Grind matchup you should win: Overlord recursion plus Solitude plus equipment beats
one-for-one removal. Skyclave their engine. **Board:** `+1 Surgical Extraction, +1 Faerie Macabre;
-1 Cloak and Dagger, -1 Flickerwisp` if Reanimate or an opposing Overlord is central; else no change.

### 8. Black Saga Storm — 6.5% of Boulder
**No cell.** Thalia plus Deafening Silence plus Thoughtseize, and Mindbreak Trap is free on their
big turn. Faerie Macabre and Lion Sash attack the graveyard axis without costing you a card.
**Board:** `+3 Deafening Silence, +1 Mindbreak Trap, +1 Surgical Extraction, +1 Faerie Macabre;
-1 Meteor Sword, -1 Lion Sash, -1 Pre-War Formalwear, -1 Cloak and Dagger, -2 Skyclave Apparition`.

### 9. Death & Taxes (mirror, incl. the no-Overlord build) — 5.6% of Boulder
`camp 0.50 (raw 7-7, n=14 — speculative)`. Karakas wars, Vial wars, and Overlord is the tiebreaker —
you have four, the mono-white build has none. Skyclave and Meteor Sword answer their equipment; Erode
answers a Thalia or a Recruiter chain. **Board:** `+2 Erode; -1 Thoughtseize, -1 Cloak and Dagger`.

### 10. Doomsday — 5.6% of Boulder
**`camp 14.7% raw 5-29 n=34 evolving` · `parent 27.8% raw n=36 evolving`. This is the hole.**
Everything you do is a permanent and they don't care. **The whole plan is turn-one Thalia or
Thoughtseize, then Deafening Silence, then race.** Thalia taxing Doomsday to {B}{B}{B}{1} and every
pile piece by {1} is genuinely the best card you have. Mindbreak Trap is free on the pile turn — hold
it. Karakas does **not** answer Thassa's Oracle. Do not board into a worse Doomsday deck by adding
Priest. **Board:** `+3 Deafening Silence, +1 Mindbreak Trap, +1 Surgical Extraction; -1 Meteor Sword,
-1 Lion Sash, -1 Pre-War Formalwear, -1 Cloak and Dagger, -1 Flickerwisp`. Expect to lose this
matchup more than you win it and plan your event around that.

### 11. Eldrazi — 5.6% of Boulder
`camp 0.50 (raw 6-6, n=12 — speculative)`. Solitude is free and exiles a Thought-Knot at instant
speed; Wasteland and White Orchid Phantom attack the sol lands; Karakas is dead here. Skyclave gets
mana value 4 or less, so it answers Thought-Knot ({3}{C}) but not Kozilek's Command targets above it.
**Board:** `+2 Disruptor Flute; -1 Cloak and Dagger, -1 Thoughtseize`. Flute names Chalice or Ancient Tomb.

### 12. Painter — 4.7% of Boulder
`camp 0.90 (raw 9-1, n=10 — speculative)`. Witch Enchanter and Skyclave answer the combo halves,
Disruptor Flute names Grindstone (shutting the activated ability, not just the cast), Meteor Sword
destroys any permanent. Lion Sash eats Welder targets. **Board:** `+2 Disruptor Flute, +1 Surgical
Extraction; -1 Cloak and Dagger, -1 Thoughtseize, -1 Flickerwisp`.

### 13. Blue Artifacts — 3.7% of Boulder
`camp 0.57 (raw 13-10, n=23, 2026)`. Witch Enchanter ×2 is maindeck Disenchant; Wasteland the Urza's
Saga; Skyclave the Emry or the Opal-fueled threat. **Board:** `+2 Disruptor Flute, +2 Erode;
-1 Cloak and Dagger, -1 Thoughtseize, -1 Flickerwisp, -1 Pre-War Formalwear`.

### 14. Energy (Boros / Mardu / Orzhov) — 3.7% of Boulder
**`camp 0.33 (raw 8-16, n=24, 2026)` · `current regime 0.14 (raw 1-6, n=7 — speculative)`.
Your second-worst modeled matchup, and it's the deck you already own.** They go wider than your
removal and Goblin Bombardment beats your blockers and dodges your exile effects. Wrath of the Skies
is the swing card — with X=2 or 3 you sweep their Cats, Guides, and Ocelot tokens; count carefully
because it also kills your Vial and equipment. Swords the Ajani or the pumped attacker; Solitude the
Raptor engine. **Board:** `+3 Wrath of the Skies; -1 Cloak and Dagger, -1 Meteor Sword, -1 Lion Sash`.

### 15. Esper Midrange — 3.7% of Boulder
**No cell.** Fair blue with exile removal. Vial, Thalia, grind. **Board:** `+3 Wrath of the Skies;
-1 Cloak and Dagger, -1 Meteor Sword, -1 Lion Sash`.

### Global-field matchups Boulder doesn't currently have

**Lands** — `camp 0.65 (raw 13-7, n=20, 2026)`. Strong. Wasteland plus White Orchid Phantom plus
Karakas for Marit Lage is the whole plan; Witch Enchanter answers Sphere and Mox Diamond.
**Board:** `+2 Erode, +1 Surgical Extraction; -1 Cloak and Dagger, -1 Thoughtseize, -1 Flickerwisp`.

**Grixis Reanimator / Oops! All Spells** — `camp 0.22 vs Oops (raw 2-7, n=9)`. Faerie Macabre is free
and dodges Force and Deafening Silence; Lion Sash grinds their yard; Surgical after a Thoughtseize.
This is the one place Containment Priest earns its nonbo, because the whole opposing plan is putting
uncast creatures onto the battlefield. **Board:** `+1 Containment Priest, +1 Faerie Macabre,
+1 Surgical Extraction, +3 Deafening Silence; -1 Meteor Sword, -1 Lion Sash, -1 Cloak and Dagger,
-1 Pre-War Formalwear, -2 Skyclave Apparition`. With Priest out, stop blinking and stop Vialing.

**Tron** — Wasteland, White Orchid Phantom, and Thalia. Witch Enchanter answers the artifact engine.
Good matchup on paper; no camp cell above n=5.

## Boulder-tuned sideboard alternative (labeled: our reasoning, not observed)

The consensus 15 above is what the corpus plays. Boulder is **22.4% combo** (Show and Tell 10.3 +
Black Saga Storm 6.5 + Doomsday 5.6) against a global field that isn't, and Doomsday is your hole.
Two swaps derived from cards already in this camp's observed sideboard pool:

- **+1 Deafening Silence (to 4), +1 Sanctum Prelate; −2 Erode.**

Sanctum Prelate ({1}{W}{W} 2/2, "As this creature enters, choose a number. Noncreature spells with
mana value equal to the chosen number can't be cast") is the sharpest anti-Doomsday card available to
a white deck: **Doomsday is {B}{B}{B}, mana value 3**, so Prelate on 3 stops it outright, and Prelate
is Vial-able at 3 and Recruiter-findable (toughness 2). Two paper pilots in this camp already run it.
Erode is the cut because you have 4 Swords, 4 Solitude, 2 Skyclave, and Meteor Sword — the fifth-plus
removal spell is the least valuable card in the 15 for a combo-heavy room.

This is a reasoned local adjustment, not a measured one. Try the consensus 15 first if you'd rather
match the data exactly.

## Cost

83 cards to acquire against your binder, **≈$1,458** at cheapest printings. Same shape as the Orzhov
Energy build: **3 Scrubland is $645 of it (44%)**, then Solitude $138, Marsh Flats $129, Stoneforge
$119, Prismatic Vista $108, Overlord $80. Budget swap for the Scrublands: 2 Godless Shrine + 1 more
Shadowy Backstreet saves ~$620 (Godless Shrine enters untapped for 2 life; both are `Land — Plains
Swamp` so Marsh Flats, Arid Mesa, and Windswept Heath all fetch them). Note this deck is only lightly
black — Thoughtseize, Overlord, Cloak and Dagger — so a slightly worse black source hurts less here
than in the Energy build.

## Evidence and refresh boundary

Corpus as of 2026-07-30 (67,581 decks). The 80 is the **modal current-regime list**, registered
near-identically by IsolatedSystem (5-0 on 2026-07-29; 5th, Legacy Challenge 32, 2026-07-19),
yoshiwata (4th, Legacy Challenge 32, 2026-07-12; 26th on 07-11 and 07-18), Alico (26th, 07-26), and
misteriggins (5-0, 07-23) — not a single pilot's brew. Camp definition: `archetype = 'Death & Taxes'`
(exact label, excluding `Conflict(Esper Blink,Death & Taxes)`) with mainboard Overlord of the Balemurk;
n=75 current-regime lists for the composition histogram, n=757 decks / 1,429 decisive matches for the
record. Matchup cells: engine `report matchups --a "Death & Taxes" --b <opp> --since 2025-08-01` for
parent rows, hand tally from `rounds` via `parse_match_result` for camp rows, Wilson/Jeffreys
intervals throughout. Field weights from `decks/boulder-field-current.txt` (103 of 107 players
modeled, post-2026-05-18).

Refresh after a ban, a major release, or **2026-09-04** — and refresh sooner if the no-Overlord share
keeps climbing, because a second consecutive month of it outnumbering this camp would mean the
archetype is moving and this 80 is the trailing build, not the current one.
