# Tron — Blue Karn (post-Candelabra) — comprehensive Legacy primer

Snapshot: 2026-08-04. This guide is for the exact 75 in `decks/tron-blue-karn-moxfield.txt`.
Every baseline exchange has equal cards in and out.

**Read the honesty section before you trust any rate in this document.** The Candelabra of Tawnos
ban (2026-06-29) was aimed at this deck and it landed: Tron went from 9.49% of the field to 2.03%,
196 lists in June to 38 in July. The deck that came out the other side is a **different deck** — a
blue control deck with Tron mana, not a ramp deck — and it has **six decisive matches of post-ban
data.** Everything numeric here is either pre-ban (a different deck) or too thin to be a number.

## The 75

```text
4 Karn, the Great Creator    4 Force of Will          22 lands + 3 MDFC:
4 Kozilek's Command          3 Force of Negation        4 Planar Nexus
4 Stock Up                   3 The One Ring             4 Urza's Tower
4 Thundertrap Trainer        2 Eldrazi Confluence       4 Petrified Hamlet
                             2 Ugin, Eye of the Storms  3 Ancient Tomb
2 Expedition Map             1 Tishana's Tidebinder     2 Urza's Mine
2 Waterlogged Teachings*     1 Dismember                2 Urza's Power Plant
1 Sink into Stupor*          1 Lórien Revealed          2 Island · 1 Underground Sea
                                                        *MDFC — land on the back

Sideboard — the Karn wishboard is the top block, real cards below
1 Ensnaring Bridge    1 Tormod's Crypt          1 Engineered Explosives   1 Walking Ballista
1 Mycosynth Lattice   1 The One Ring            1 Invasion Submersible
4 Barrowgoyf   2 Hullbreacher   1 Force of Negation   1 Hydroblast
```

## The land trick that makes this deck work

**Planar Nexus** — "This land is every nonbasic land type." That means one Planar Nexus is
*simultaneously* an Urza's Mine, an Urza's Power-Plant, and an Urza's Tower.

Urza's Tower reads "If you control an Urza's Mine and an Urza's Power-Plant, add {C}{C}{C}
instead." A single Nexus satisfies both conditions. So:

- **Nexus + Tower = 4 mana off two lands** (Tower {C}{C}{C}, Nexus {C})
- **Nexus + Mine = 3 mana off two lands** (Mine {C}{C}, Nexus {C})
- **Nexus + Nexus + Tower = 5 mana off three lands**

That is why the counts are 4 Nexus / 4 Tower / 2 Mine / 2 Power Plant instead of the old 4/4/4.
Nexus is a wildcard piece, so you need fewer real ones — and it also fixes colour ("{1}, {T}: Add
one mana of any color"), which is how a deck with 2 Island and 1 Underground Sea casts Force of
Will. Treat Nexus as your most valuable land and the primary Expedition Map target.

**Petrified Hamlet** is the anti-hate land, and it's a 4-of because land destruction is this deck's
oldest weakness. "When this land enters, choose a land card name. Activated abilities of sources
with the chosen name can't be activated unless they're mana abilities. Lands with the chosen name
have '{T}: Add {C}.'" Name **Wasteland** and every Wasteland on the other side of the table becomes
a Wastes that cannot sacrifice itself. Other live names: **Urza's Saga** (no construct fetch),
**Ghost Quarter**, **Karakas**, **Boseiju, Who Endures**. Hamlet has no Urza's type, so it does not
help assemble Tron — it taps for {C} and it turns off their plan.

## What this deck is now

Before the ban this was a ramp deck: Candelabra untapping Tron lands into an early, oppressive Karn
or Ugin. That deck is gone. What replaced it is **a blue permission deck that happens to make five
colourless mana**:

- **4 Force of Will, 3 Force of Negation, 1 Tishana's Tidebinder, 1 Sink into Stupor** — you
  interact on turns one through three now. You are not "durdling until Tron."
- **4 Stock Up, 4 Thundertrap Trainer, 1 Lórien Revealed, 2 Waterlogged Teachings** — a real card
  selection suite. Grim Monolith is down to 45% of lists and is not in this 75; velocity replaced
  fast mana.
- **4 Karn, 3 The One Ring, 2 Ugin, 4 Kozilek's Command** — the payoffs, cast on a normal curve
  behind counterspells rather than on turn three off a broken mana burst.

Play it like Azorius Control with a mana advantage, not like a combo deck.

## Card roles and the rulings that decide games

- **Karn, the Great Creator** — the static line is the important half: "Activated abilities of
  artifacts your opponents control can't be activated." That is a hard lock on Aether Vial, Lion's
  Eye Diamond, Lotus Petal, Mox Opal, Chrome Mox, Grindstone, Painter's Servant activations,
  Expedition Map, Walking Ballista, and **The One Ring's draw**. Against artifact combo Karn alone
  often wins. The −2 fetches an artifact you own from outside the game — that's the wishboard.
  **Karn has no mana-ability exemption** — unlike Petrified Hamlet, whose lock reads "unless they're
  mana abilities" — so Karn genuinely stops Lotus Petal, Lion's Eye Diamond, Mox Opal, and Chrome Mox
  from producing mana at all. Two locks, two different carve-outs; know which one you have out.
- **Karn + Mycosynth Lattice is the lock.** Lattice makes "All permanents are artifacts in addition
  to their other types," so Karn's static now shuts off the activated abilities of **every**
  opposing permanent, including lands. They cannot tap for mana. Fetch Lattice with Karn −2 and
  cast it for {6}; Tron mana gets there.
- **Kozilek's Command** {X}{C}{C}, choose two of: X Eldrazi Spawn tokens / scry X then draw / exile
  a creature with mana value X or less / exile up to X cards from graveyards. It is your removal,
  your graveyard hate, your ramp, and your card — the most flexible slot in the deck. At X=1 for
  {1}{C}{C} it kills a Delver and draws you a card.
- **Ugin, Eye of the Storms** {7} — "When you cast this spell, exile up to one target permanent
  that's one or more colors. **Whenever you cast a colorless spell, exile up to one target permanent
  that's one or more colors.**" The second line is the engine: once Ugin is out, every Karn, every
  One Ring, every Kozilek's Command, every Expedition Map exiles another coloured permanent. `0:
  Add {C}{C}{C}` also means Ugin ramps toward the next colourless spell. Note it only ever hits
  **coloured** permanents — it does nothing to Eldrazi, artifacts, or Marit Lage.
- **The One Ring** — "When The One Ring enters, **if you cast it**, you gain protection from
  everything until your next turn." Read that clause: a Ring you *cast* fogs a lethal attack; a Ring
  put onto the battlefield another way does not. Burden counters accumulate, so the second and third
  activations cost real life. Karn can fetch the sideboard copy when the maindeck ones are gone.
- **Thundertrap Trainer** {1}{U} — "When this creature enters, look at the top four cards of your
  library. You may reveal a noncreature, nonland card from among them and put it into your hand."
  Your consistency engine: it finds Karn, One Ring, Command, Stock Up, or a Force. It is printed as a
  **Token Creature**, which means effects that say "nontoken" — Containment Priest most relevantly —
  do not touch it.
- **Eldrazi Confluence** {2}{C}{C}, choose three modes and you may repeat one: +3/−3 to a creature /
  exile a nonland permanent and return it tapped / make a 1/1 Scion that sacs for {C}. Three copies
  of the first mode is −9/−9. The second mode resets an opposing Urza's Saga, a Marit Lage token
  (it returns as a token — which means it ceases to exist), or your own One Ring to clear burden
  counters. Three Scions is four mana of ramp.
- **Waterlogged Teachings // Inundated Archive** — the instant half tutors any instant or flash card
  (Force of Will, Force of Negation, Eldrazi Confluence, Tishana's Tidebinder, Dismember); the back
  is a land. **Sink into Stupor // Soporific Springs** the same — bounce a spell *or* a nonland
  permanent, or play it as a blue land for 3 life. These three MDFC slots are why 22 true lands is
  enough.
- **Tishana's Tidebinder** — flash 3/2 that counters an activated or triggered ability, and if it hit
  an ability of an artifact, creature, or planeswalker, that permanent **loses all abilities** while
  Tidebinder stays. It answers a Thassa's Oracle trigger, an Urza's Saga chapter, a Vial activation,
  a Grindstone.
- **Ancient Tomb** deals you 2 every time. In a deck that also runs The One Ring, watch the total.

## Mulligans

You need two things: **a path to Tron or to five mana**, and **a way to survive to it**. A hand with
neither is a mulligan regardless of how many spells it has.

A keep needs:

- **three lands, or two lands plus Expedition Map**, and at least one of those lands being Nexus,
  Tower, Mine, or Power Plant. Remember Nexus + Tower alone is four mana.
- **a blue source** if the hand is leaning on Force of Will — Nexus counts, Island and Underground
  Sea count, the two MDFC backs count.
- **either interaction or a fast Karn.** Stock Up plus three lands is not a keep against combo.

Matchup adjustments:

- **Against combo:** you want Force of Will in the opener. Not Stock Up into Force — the actual card.
  Thundertrap Trainer finding a Force on turn two is the acceptable version.
- **Against Wasteland decks:** Petrified Hamlet is close to a mulligan-changer. A hand with Hamlet
  plus two other lands is a keep that would otherwise be shaky.
- **Against creature decks:** Kozilek's Command at low X is your early game; keep it over a Stock Up.
- **On the draw:** the extra card matters more here than in most decks because you have no fast mana
  left to punish with. Be slightly greedier on the play, slightly more conservative on the draw.

---

## Honesty section — lead with this

1. **Post-ban Tron is statistically unmeasured.** 38 lists exist since 2026-06-29 and they have
   produced **6 decisive matches in rounds-bearing events (2-4)**. That is not a win rate, it is a
   rounding error. For comparison, pre-ban 2026 Tron ran **54.2% (raw 211-178, n=389, established)**
   — but that was the Candelabra deck, which no longer exists (zero copies of Candelabra remain in
   the corpus post-ban). **Do not carry the 54.2% forward.**
2. **The "20 of 38 lists are 5-0" figure is a publication artifact, not a win rate.** 18 of the 38
   come from Legacy League dumps, which publish *only* 5-0 decks and carry no round data. The
   unbiased slice is 12 Challenge entries plus 8 Last Chance entries, and their finishes are:
   2nd, 5th, 6th, 8th, 25th, 25th, 27th, 32nd, 32nd, and three sub-.500 records. That looks like a
   real but unremarkable deck, not a dominant one.
3. **Zero paper data.** All 38 post-ban lists are online. For a the local meta read that is a hard
   limitation, not a footnote — this deck's whole plan is vulnerable to Wasteland and Boseiju, and
   paper fields differ.
4. **The engine's own Tron numbers are currently blended and wrong.** `entity_eras` gives Tron
   `stable_since = 2026-05-11` (attributed to the Undercity Informer ban via a Faerie Macabre
   presence signal, p=1.7e-31) and has **no 2026-06-29 boundary candidate at all** — even though
   the same detection run found that boundary for Blue Artifacts, Doomsday, and Izzet Delver. So any
   default-window Tron read averages a 9.49%-share deck with a 2.03%-share deck. Filed as
   `bug-tron-candelabra-cliff-not-detected`. `report meta` will tell you Tron is 6.60% of the current
   regime; its trailing-month share is 2.03%.
5. **The 60 is a hard consensus even though the sample is small.** Four separate pilots registered
   the *identical* maindeck: AFX (2nd, Legacy Challenge 32, 2026-07-22), Lans_NL (5-0, 2026-07-21),
   _Batutinha_ (5th, Challenge 32, 2026-07-25), MystikHawk (8th, Challenge 32, 2026-07-18). The
   only variation among them is one flex slot — Dismember or Cyclonic Rift. That convergence is
   worth something even when the match data isn't there. The sideboard here is AFX's, being the best
   finish.

**What to conclude.** This is a real, currently-played deck with a coherent new identity and a hard
list consensus, whose performance is genuinely unknown. If you want a deck the data endorses, this
isn't it. If you want the deck that inherited the Tron shell and want to be early on it, this is the
list — and you should expect to be generating the evidence rather than reading it.

## Matchups and sideboarding

**No post-ban matchup cell in this archetype reaches n=3.** Every plan below is derived from card
mechanics and from what the old Tron deck's cells implied, explicitly labelled as reasoning rather
than measurement. Ordered by share of the current local field.

### 1. Izzet Delver — 11.2% of the local meta
**Their plan:** Channeler and Murktide behind Daze, Force, Bolt, Cori-Steel Cutter, and Wasteland.
**Your plan:** Petrified Hamlet naming Wasteland is the single most important card in the matchup —
it turns their mana denial off entirely. Kozilek's Command at X=1 or 2 answers everything they play.
Force of Will their threat, then land Karn or Ring and bury them. **Board:** `+1 Force of Negation,
+1 Hydroblast; -1 Dismember, -1 Lórien Revealed`. Hydroblast kills a resolved Cutter or Channeler.

### 2. Show and Tell — 10.3% of the local meta
**Their plan:** cantrips and Stock Up plus protection into Show and Tell for Omniscience or a legend.
**Your plan:** you are a permission deck with 7 counterspells — this is a fight you can actually
have. Force of Negation is free on their turn and counters Show and Tell. Ugin cast after they land
a coloured fatty exiles it. Kozilek's Command exiles a creature with mana value X or less; Emrakul
and friends are expensive, so plan on Ugin or a counter instead. **Board:** `+1 Force of Negation,
+2 Hullbreacher; -1 Dismember, -1 Eldrazi Confluence, -1 Expedition Map`. Hullbreacher turns their
Show-and-Tell-fuelled draws into your Treasures and blanks Stock Up.

### 3. White Beanstalk — 7.5% of the local meta
**Their plan:** Beanstalk/Stock Up value, exile removal, Phelia, planeswalkers, sweepers.
**Your plan:** grind. You have more raw card advantage than they do once Ring or Ugin lands, and
Ugin exiles their coloured permanents one per colourless spell. Hullbreacher taxes Beanstalk and
Stock Up hard. **Board:** `+2 Hullbreacher, +1 The One Ring; -1 Dismember, -1 Tishana's Tidebinder,
-1 Eldrazi Confluence`.

### 4. Dimir Tempo — 7.5% of the local meta
The only post-ban cell that exists at all: **1-2, n=3.** Meaningless; noted for completeness.
**Their plan:** cheap threats behind discard, Daze, Force, Wasteland, Kaito. **Your plan:** Hamlet
on Wasteland, Command their threats, and remember their discard is at its best against your
5-plus-mana hands — Thundertrap Trainer and Stock Up let you rebuild. **Board:** `+1 Force of
Negation, +4 Barrowgoyf; -1 Ugin, -2 Expedition Map, -1 Eldrazi Confluence, -1 Lórien Revealed`.
See the Barrowgoyf note below.

### 5. Jeskai Midrange — 7.5% of the local meta
**No cell.** Fair blue with burn and sweepers. Counter the engine, land Karn, Hydroblast the red
permanent. **Board:** `+1 Hydroblast, +1 Force of Negation; -1 Dismember, -1 Lórien Revealed`.

### 6. Azorius Midrange — 6.5% of the local meta
**No cell.** Their Stifle is a real problem for Expedition Map and for Tron assembly; sequence lands
so a Stifle costs them the least. Karakas is answered by Petrified Hamlet naming it.
**Board:** `+2 Hullbreacher, +1 Force of Negation; -1 Dismember, -1 Eldrazi Confluence, -1 Lórien
Revealed`.

### 7. Black Midrange — 6.5% of the local meta
**No cell.** Discard plus efficient threats. Kozilek's Command's graveyard mode fights their
recursion; Ugin exiles their black permanents. This should be a good matchup — you go far over the
top of a fair black deck. **Board:** `+4 Barrowgoyf; -2 Expedition Map, -1 Ugin, -1 Lórien Revealed`.

### 8. Black Saga Storm — 6.5% of the local meta
**No cell, and this is your best structural matchup in the room.** Their engine is 4 Lion's Eye
Diamond, 4 Lotus Petal, 4 Mox Opal, 4 Chrome Mox, 3.4 Urza's Saga — **Karn's static turns every one
of those off**, and Petrified Hamlet naming Urza's Saga kills the Saga plan. Force of Negation is
free on their turn. Note their ~3 Veil of Summer does nothing against you: you have no black or blue
*targeted* interaction they care about, and Veil doesn't stop Force of Will countering the spell.
**Board:** `+1 Force of Negation, +1 Tormod's Crypt (via Karn or hard-cast); -1 Dismember,
-1 Eldrazi Confluence`. Karn −2 for Tormod's Crypt answers Gaea's Will.

### 9. Death & Taxes (80-card Yorion) — 5.6% of the local meta
**No cell.** Their Wasteland, White Orchid Phantom, and Karakas all attack your mana; **Petrified
Hamlet answers two of the three** (name Wasteland, or name Karakas if their legends matter more).
Karn shuts off Aether Vial. Their Solitude and Swords do nothing to your permanents. **Board:**
`+1 Ensnaring Bridge (Karn target), +1 Engineered Explosives; -1 Lórien Revealed, -1 Dismember`.
Ensnaring Bridge under a full grip is close to unbeatable for a creature deck.

### 10. Doomsday — 5.6% of the local meta
**No cell.** You have 7 counterspells and they have to resolve a 3-mana sorcery and then a pile —
this is a much better matchup for this deck than for any creature deck. Force of Negation is free.
Tishana's Tidebinder counters the Thassa's Oracle trigger. Kozilek's Command exiles their graveyard
in response to Gaea's-Will-style rebuilds. **Board:** `+1 Force of Negation, +1 Tormod's Crypt;
-1 Dismember, -1 Eldrazi Confluence`.

### 11. Eldrazi — 5.6% of the local meta
**No cell.** The awkward one: **Ugin only exiles coloured permanents, so it does nothing here**, and
their Chalice of the Void on 1 is bad for Expedition Map, Thundertrap-adjacent one-drops, and
Sink into Stupor. Kozilek's Command exiles a creature with mana value X or less — that's your
Thought-Knot answer, at X=4. Karn's static reaches their Walking Ballista and any artifact mana, but
**not** Chalice (a static ability, not activated) or Ancient Tomb and the sol lands (lands, not
artifacts) — do not board on the assumption Karn taxes their mana. **Board:**
`+1 Engineered Explosives, +1 Walking Ballista, +1 Force of Negation; -1 Lórien Revealed,
-1 Stock Up, -1 Tishana's Tidebinder`.

### 12. Painter — 4.7% of the local meta
**No cell; should be excellent.** Karn's static shuts off Grindstone entirely — the combo cannot be
activated while Karn is on the battlefield. Tidebinder counters a Grindstone activation and strips
its abilities. Their Pyroblast is the danger to your blue half; Hamlet cannot help there.
**Board:** `+1 Hydroblast, +1 Force of Negation; -1 Dismember, -1 Lórien Revealed`.

### 13. Blue Artifacts — 3.7% of the local meta
**No cell; also excellent.** Karn turns off Mox Opal, Bauble, Emry activations, and Urza's Saga
constructs; Hamlet naming Urza's Saga finishes the job; Engineered Explosives on 1 sweeps their
board. **Board:** `+1 Engineered Explosives, +1 Force of Negation, +1 Invasion Submersible;
-1 Dismember, -1 Lórien Revealed, -1 Tishana's Tidebinder`.

### 14. Energy — 3.7% of the local meta
**No cell.** A genuine race problem: they deploy four bodies by turn three and you are a five-mana
deck. Kozilek's Command at low X, Eldrazi Confluence's +3/−3 mode used three times, and Ensnaring
Bridge are your outs. **Karn does almost nothing here** — his static hits activated abilities of
*artifacts* only, so it misses Guide of Souls entirely (a creature, and its energy payment is part
of a triggered ability anyway), Ocelot Pride, Ajani, and Amped Raptor. Board and play accordingly:
Karn is a 4-mana blank in this matchup unless they have Aether Vial or Null Rod-adjacent artifacts.
**Board:** `+1 Ensnaring Bridge, +1 Walking Ballista, +1 Engineered Explosives; -1 Lórien Revealed,
-1 Expedition Map, -1 Tishana's Tidebinder`.

### 15. Esper Midrange — 3.7% of the local meta
**No cell.** Fair blue-black. Go over the top; Hullbreacher taxes their draw; Ugin exiles their
coloured permanents. **Board:** `+2 Hullbreacher, +1 Force of Negation; -1 Dismember,
-1 Eldrazi Confluence, -1 Lórien Revealed`.

### Global-field matchups the local meta doesn't currently have

**Lands** — historically Tron's nightmare and still is: Wasteland, Ghost Quarter, Sphere of
Resistance, Tabernacle, and Boseiju all attack you. **Petrified Hamlet can only name one of them at
a time.** Name Wasteland first, Ghost Quarter second. Karn shuts off Mox Diamond and Ensnaring
Bridge is dead weight against Marit Lage (a token with power 20). Eldrazi Confluence's exile-and-
return mode makes a Marit Lage token cease to exist — that's your cleanest answer. **Board:**
`+1 Engineered Explosives, +1 Force of Negation, +1 Invasion Submersible; -1 Dismember,
-1 Stock Up, -1 Lórien Revealed`.

**Grixis Reanimator / Oops! All Spells** — Karn −2 for Tormod's Crypt, Kozilek's Command's graveyard
mode, Force of Negation. You have real interaction here for the first time in Tron's history.
**Board:** `+1 Tormod's Crypt, +1 Force of Negation; -1 Dismember, -1 Eldrazi Confluence`.

### The Barrowgoyf plan

4 Barrowgoyf in the board is a **transform package**, the same juke the Doomsday and Grixis camps
use: against fair decks that are attacking your mana base, you cut the top end (Ugin, Expedition
Map, Lórien Revealed) and become a blue-black midrange deck that wins with a cheap resilient
threat instead of assembling Tron. Barrowgoyf is {2}{B} — castable off Underground Sea, Planar
Nexus's any-colour ability, or the Inundated Archive back face of Waterlogged Teachings, so check
your black sources before you board it in. Use it against Dimir Tempo, Black Midrange, and any
Wasteland deck that would otherwise just win the mana war.

## Cost

I have not priced this against your binder — say the word and I'll run it. The expensive slots are
predictable: **Ancient Tomb ×3, Underground Sea ×1, Force of Will ×4, The One Ring ×4 (3 main +
1 board), Karn ×4, Grim Monolith is *not* in this list** (a genuine saving versus the old build).
The Urza lands, Planar Nexus, and Petrified Hamlet are cheap.

## Evidence and refresh boundary

Corpus as of 2026-07-30 (67,581 decks). Post-ban pool hand-windowed to `t.date >= '2026-06-29'`
because the engine's era window for Tron is wrong (see honesty gate 4) — n=38 lists, 100% online,
18 from 5-0-only league dumps. Composition histogram over all 38; the 60 is the modal list,
registered identically by AFX / Lans_NL / _Batutinha_ / MystikHawk. Match record: 2-4 (n=6) from
`rounds` via `parse_match_result`. Pre-ban comparator: 211-178 (n=389) over 2026-01-01 to 06-29.
Field weights from `decks/local-field-current.txt`.

**Refresh this early and often** — sooner than any other primer in this repo. Two specific triggers:
(a) once ~3 more weeks of post-ban Challenge data accrue, the cells become readable and the
matchup section above should be replaced with measurements rather than reasoning; (b) if the engine
picks up the 2026-06-29 boundary for Tron, re-run every read here against it. Otherwise refresh at
**2026-09-04**, on a ban, or on a major release.
