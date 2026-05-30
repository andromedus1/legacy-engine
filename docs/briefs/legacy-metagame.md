---
description: What is the current Legacy metagame (2026) — tier list, archetype mechanics & goldfish speeds, data sources, and how to attack the field? Read before designing meta-ingestion, the matchup model, or the meta-speed metric.
type: brief
kind: research
research_method: /research
updated: 2026-05-29
status: draft
summary: |
  The core domain brief for legacy-engine. Maps the 2026 Legacy metagame: the four-pillar tier
  structure (no Tier 0), per-archetype game plans and goldfish turn-to-kill clocks, the data-source
  ecosystem (the edhtop16 analog), and the strategic landscape of how to attack the field (matchup
  matrix, hosers-by-target, sideboard strategy, "what to play"). Every section is framed for the
  analytics platform's ingestion, simulation, and advisory pillars.
key_findings:
  - 2026 Legacy is a blue-tempo-centered four-pillar format with NO Tier 0; Dimir Tempo is #1 (~16% play, ~52% non-mirror WR) but "popular not oppressive" — Wizards deemed it healthy (Feb 2026 no-change).
  - The data ingestion analog to edhtop16 is the fbettega community pipeline (mtg_decklist_scrapper + MTG_decklistcache, both pushed 2026-05-29) labeled by Badaro/MTGOFormatData archetype rules; Scryfall is the shared card-data source. NO clean official API exists.
  - Legacy needs an explicit archetype-PARSER layer that cEDH does not (no commander to key on) — this is the key architectural delta from edh-engine.
  - Goldfish clock ladder (turn-to-kill, unopposed) — calibration anchor Oops All Spells = 66% T1 / 76% by T2 / 83% by T3 [cited]; combo T1-3, fair tempo/control T4-6+ (win by disruption/attrition, not a clock).
  - Meta-speed metric = per-archetype goldfish-clock PMF weighted by meta share; model BOTH a goldfish clock (upper bound) and an effective clock (convolved with Force of Will/Daze survival) — the gap is a format-health signal.
  - Aggregator sites (MTGGoldfish/MTGTop8/mtgdecks) are HTML-only and 403-block bots; meta % is computed differently by each (top-cut presence vs raw count vs winrate-weighted) and online/paper diverge materially — compute % yourself from raw finishes under multiple definitions and label the source.
  - The universally-agreed format constant: dedicated graveyard hate + free counters belong in every sideboard (Reanimator + Oops + Sneak&Show + Painter are all GY/combo-adjacent).
---

# Brief: Legacy Metagame (2026)

## Purpose
The central domain brief for legacy-engine. It maps **what the Legacy metagame actually is** in mid-2026
and frames it for the three analytical pillars the platform will build: **meta ingestion & performance
tracking**, **deck mechanics & goldfish simulation**, and an **advisory layer** (matchup positioning,
sideboard recommendation, "what to play"). Where edh-engine's pillars apply, the mapping is noted;
where Legacy diverges (notably: it needs an archetype *parser*), that's flagged.

---

## 1. State of the format (one line)
Legacy in mid-2026 is a **blue-tempo-centered, four-pillar format with no Tier 0**. After a multi-year
ban campaign (Grief, Psychic Frog, Entomb, Nadu, Troll, Mycospawn all gone), Wizards' **Feb 9 2026
no-change decision** judged the format healthy: the most-played deck (Dimir Tempo) sits at ~52–53%
non-mirror win rate — popular but not oppressive. The Nov 10 2025 **Entomb ban** is the most important
recent fact: it deliberately decoupled "cheat-a-fatty" combo from fair decks, pushing the meta
**fair-leaning**.

## 2. Tier list (2026)

| Tier | Archetypes |
|------|-----------|
| **Tier 0** | *(none)* |
| **Tier 1** | Dimir Tempo (UB) · Izzet/UR Tempo ("Cutter"/Delver) · UWx (Azorius/Jeskai) Control · Sneak & Show |
| **Tier 2** | Artifacts Prison / Mystic Forge–Karn ("Trini Tron") · Lands · Boros/Mardu Energy · Reanimator (UB) · Doomsday · Oops All Spells · Eldrazi Aggro |
| **Tier 3** | Death & Taxes · Cradle Control · ANT / TES / Ruby Storm · Dragon/Red Stompy · Stoneblade · 4/5c Control · Painter · Dark Depths/Lands-combo |
| **Fringe** | Maverick · Merfolk · Death's Shadow · Dredge · Cephalid Breakfast · Infect · Elves · Goblins |

> **Source disagreement on tiering & shares is real:** mtgdecks (May 2026) ranks Dimir Tempo ~16%
> first; MTGTop8 (last-2-weeks) puts UR Tempo ~9% slightly ahead and elevates Artifacts Prison/Lands;
> AetherHub's 180-day window inflates Tron. The two blue tempo decks + UWx Control + Sneak & Show are
> unambiguously Tier 1 across sources; Tier 2 ordering shifts by source and window. **Treat specific
> percentages as approximate and window-dependent.**

## 3. The four pillars + per-archetype capsules (with goldfish clock)

Confidence flags: **[cited]** = explicit sourced number, **[consensus]** = multiple primers agree,
**[estimate]** = interpolated from mechanics.

### Pillar 1 — Tempo (central; ~mid-40s% combined)
- **Dimir Tempo (UB)** — #1 deck. Cheap evasive threat (Murktide Regent, Nethergoyf, Orcish Bowmasters) + Force/Daze/Wasteland/Fatal Push/Thoughtseize/Brainstorm. Wins by landing & protecting an early threat. **Goldfish clock ~T4–6 [estimate]** — the archetypal "slow goldfish, fast in practice via disruption" deck.
- **Izzet/UR Tempo ("Cutter", Delver)** — Delver/DRC/Murktide + burn + Cori-Steel Cutter token engine. Historic central pillar; currently a hair below 50% (overplayed). Clock ~T4–5.

### Pillar 2 — Control / Midrange
- **UWx Control (Azorius/Jeskai)** — counters, sweepers, planeswalkers, **The One Ring** engine. Beneficiary of the 2025 bans; preys on tempo. **Goldfish clock T6+ / attrition.**
- **Cradle Control, Stoneblade, 4/5c** — value/midrange grind piles.

### Pillar 3 — Combo
- **Sneak & Show (UR)** — Show and Tell / Sneak Attack to cheat **Emrakul / Griselbrand / Atraxa**. **T1 possible (Ancient Tomb), T2–3 typical [consensus].**
- **Oops, All Spells!** — *fastest deck.* Self-mill (Balustrade Spy) → Narcomoeba → Dread Return → **Thassa's Oracle** (library=0 wins). **66% T1 / 76% by T2 / 83% by T3 [cited]** — the cleanest calibration anchor in the corpus.
- **Reanimator (UB, post-Entomb)** — Faithless Looting/Careful Study discard a fatty (**Atraxa Grand Unifier** now the workhorse) → Reanimate/Animate Dead. **T1–2, slower & less consistent post-Entomb-ban [flag: version-stamp].**
- **Doomsday** — set library to a 5-card pile → cantrip into Thassa's Oracle. **T2–3 [consensus].**
- **ANT / TES / Ruby Storm** — ritual storm → **Tendrils of Agony** (10 copies = 20 life) or Empty the Warrens. **ANT T2 protected; TES ~1 turn faster [consensus].**
- **Cephalid Breakfast, Painter, Dark Depths-combo** — T2–3 niche combos.

### Pillar 4 — Aggro / Prison / Stax
- **Artifacts Prison / Trini-Tron-Karn** — Mystic Forge + Karn + One Ring grind/lock; had a 59%-WR week. Strong vs tempo/control/aggro.
- **Boros/Mardu Energy** — the **breakout of 2025–26**: genuine non-blue aggro powered by MH3 energy (Guide of Souls, Ocelot Pride, Amped Raptor) + Voice of Victory. ~51% non-mirror. Made aggro viable in a blue format.
- **Eldrazi Aggro** — sol-land ramp into Thought-Knot Seer / Reality Smasher. **~T3–4 [estimate].**
- **Death & Taxes** — Aether Vial + hatebears + Stoneforge→Batterskull + Wasteland/Port denial. **~T4–6 [consensus].**
- **Lands** — **Dark Depths + Thespian's Stage → 20/20 Marit Lage**; Tabernacle/Loam/Wasteland prison engine. **Marit Lage T2–3 [consensus]**, but usually plays prison first.

### The fair/unfair axis (community framing)
`Oops/Storm/Reanimator (T1-2, ignore opp) → Sneak&Show/Cephalid/Painter (T2-3) → Lands/Eldrazi (T2-4, semi-prison) → Dimir/UR/Azorius Tempo (T4-6, disrupt+clock) → D&T/Cradle/control (T5+, attrition)`

The meta currently sits **fair-leaning** by design (Entomb ban). Cluster weights ≈ fair tempo/control
30–35%, combo 20–25%, prison/stax/aggro 15–20%, rest rogue.

## 4. Engines vs payoffs (deck-context-dependent — confirms edh-engine's payoff model)
The *same* card flips role by shell: **Ad Nauseam** is a draw engine in a value deck but the literal
kill-enabler in ANT; **Orcish Bowmasters** is a hate-engine in fair decks and a tempo *payoff* in Dimir;
**The One Ring** is a pure engine (refuels, never wins). **Murktide/Nethergoyf** = payoff bodies that
need a full graveyard (context-dependent enabler). Tax/lock pieces (Tabernacle, Chalice, Trinisphere)
are *neither* engine nor payoff. **A sim must tag card roles per-deck, not globally** — directly
mirrors edh-engine's `project_payoff_model` memory.

## 5. Data sources (the ingestion layer — the edhtop16 analog)

**There is no clean official tournament-results API.** The recommended pipeline mirrors edh-engine's
two-pillar pattern (results source + Scryfall), with one extra layer Legacy uniquely needs:

| Source | Data | Access | API? | Notes |
|---|---|---|---|---|
| **fbettega/MTG_decklistcache** | Pre-scraped tournament JSON (MTGO + Melee + Topdeck) | git clone / raw GitHub | static files | **Primary fact source — the edhtop16 analog.** Pushed 2026-05-29 (live). Successor to Badaro's cache (which shut down 2025-06-10). |
| **fbettega/mtg_decklist_scrapper** | The scraper itself | Python, GitHub | — | Run only if backfilling beyond the cache. |
| **Badaro/MTGOFormatData** + **MTGOArchetypeParser** | Archetype-detection rules → decklist→archetype name | GitHub JSON + C# tool | static/tool | **The key Legacy-specific layer.** No commander to key on, so archetype labels need explicit rules. Pushed 2026-05-18. Use their Legacy rules so the taxonomy matches the community's and is auditable. |
| **Scryfall API** | Oracle text, types, mana cost, CMC, color identity, legality | REST + daily bulk | **yes, free** | Canonical card dimension. Bulk has NO rate limit; ≤10 req/s otherwise. **Shared with edh-engine.** |
| **MTGJSON** | Bulk card data (Parquet/SQL) | bulk download | static | Secondary to Scryfall; handy for warehousing. |
| **MTGGoldfish / MTGTop8 / mtgdecks.net** | Meta %, decklists, matchup matrix | HTML only | **no; 403 bots** | Reference/validation only. mtgdecks uniquely exposes a **matchup winrate matrix** (30,926 matches Nov 2025–May 2026). |
| **Melee.gg** | Paper event standings/decklists | REST | **gated/paid** | Hosts Eternal Weekend EU / BMO; fbettega already pulls public Melee data. |
| ~~17lands~~ | — | — | — | **NOT applicable** — Limited only. |

**Recommended ingest order:** (1) Scryfall bulk Oracle Cards (card dimension); (2) fbettega cache JSON
(tournament facts — mirror it locally, it's community-run and fragile); (3) MTGOFormatData/Parser
(archetype labels); (4) MTGTop8 secondary/historical backfill; (5) mtgdecks winrate matrix as
matchup-analytics enrichment (or compute your own from cache standings).

**How meta % is computed (critical caveat):** sources are NOT comparable. MTGGoldfish = presence among
scraped MTGO lists with a 5% inclusion floor; MTGO Challenge data = **success-filtered top finishers**
(inflates winners); mtgdecks = raw count + a separate winrate matrix. **Online vs paper diverge
materially** (online skews cheap tuned tempo; paper has more dual-heavy diversity). **Recommendation:
ingest raw per-deck records with finish position + event metadata, compute your own meta % under
multiple definitions (raw count / top-8 presence / winrate-weighted), and always label online-vs-paper.**

**Major 2025 paper events feeding the cache:** NA Legacy Champs @ Eternal Weekend Pittsburgh 944p
(2025-11-10); Eternal Weekend EU Lucca 965p (2025-11-29, won by Colorless/Eldrazi Storm); EW Asia 676p.

## 6. How to attack the meta

### Matchup matrix (anchor cells; full N×N needs headed scraping of mtgdecks/Legacy/winrates)
- **Dimir Reanimator**: positive non-mirror vs everything **except Lands (42.3%)**; ~56.3% overall (strongest aggregate earlier 2026, share since cooled).
- **Dimir Tempo**: ~50–51% non-mirror, no bad matchups, no dominant edges — the high-floor "best deck if unsure."
- **Eldrazi Aggro** ~51.1%. **Lands** beats Reanimator; favored vs Eldrazi/D&T/Maverick/Delver; **very unfavored vs Sneak & Show**.
- Directional: **tempo preys on combo G1** (pressure + counters deny setup); **combo beats hateless fair grind**; **Lands/prison prey on basics-light fair creature decks** but get raced by fast combo.

### Hosers by target (seed edge list for a recommender)
- **Graveyard** (Reanimator/Lands-Loam/Dredge/Oops/Painter): Surgical Extraction, **Faerie Macabre** (free, uncounterable), Leyline of the Void, **Endurance** (MVP), Containment Priest, Nihil Spellbomb/Grafdigger's Cage.
- **Combo** (Storm/Sneak&Show/Doomsday): Force of Will, Flusterstorm, **Mindbreak Trap** (*exiles* — Veil of Summer does NOT save the combo), Thoughtseize/Duress/Hymn.
- **Combo's own anti-hate**: Veil of Summer, Defense Grid, Carpet of Flowers — these are *counter-hosers* (edges point at hate cards, not archetypes).
- **Blue**: Pyroblast / Red Elemental Blast / Hydroblast split.
- **Low curve / cantrip / combo**: Chalice of the Void (X=1), Trinisphere / Sphere of Resistance / Thorn.
- **Greedy nonbasic manabases**: Blood Moon / Back to Basics (much weaker post-Force of Vigor), **Wasteland**, From the Ashes.
- **Artifacts/enchantments**: **Force of Vigor** (free 2-for-1; demoted Blood Moon, made Chalice answerable), Abrupt Decay, Krosan Grip.
> Note: Initiative is **historical** (White Plume Adventurer banned) — not a current attack vector.

### Sideboard strategy
Built as a **target-indexed toolbox**, not "good cards." Lands' template buckets 15 into (1)
artifact/enchantment removal, (2) combo/sphere effects, (3) **non-graveyard win conditions** (dodge
opposing GY hate). Two transformational patterns: combo boards *toward resilience* (Defense Grid/Veil);
graveyard decks bring *non-GY win-cons* so Leyline/RIP become blanks. Splits beat singletons
(Hydroblast/Pyroblast, Surgical/Faerie).

### "What to play" framework (three axes)
1. **Proactive** (Sneak&Show/Reanimator/Storm/Oops/Eldrazi — force the opponent to have the answer) vs **Reactive** (Dimir/UWx/Lands — win on card quality + disruption, rewards skill).
2. **"Best deck"** (highest aggregate WR — Dimir Reanimator ~56%) vs **"best metagame call"** (hosers line up against the expected field — e.g. bring Lands to a Reanimator-heavy room).
3. **Hating-out-the-field** — dedicate the most slots against the largest pillar. Right now **graveyard hate + free counters are the highest-equity slots** (Reanimator+Oops+Sneak&Show+Painter all GY/combo-adjacent).

**Current read (May 2026):** No hard consensus — format is healthy/multi-pillar. Pragmatic: **Dimir
Tempo/Reanimator for raw winrate if you don't know the field; Lands or sphere-prison if you expect a
graveyard/combo-skewed field.** The non-negotiable: dedicated GY hate + free counters in every sideboard.

## 7. Implementation relevance (platform modeling)

**Meta-speed metric (headline):** assign each archetype a **goldfish-clock PMF** (use [cited] PMFs
where available — Oops 66/76/83 — else a triangular/PERT from (min,mode,max) ranges); weight by meta
share for the format's aggregate "what turn does a random opponent kill, unopposed?" distribution;
**track monthly** (the Entomb ban is a worked regime-shift example). Model **two distributions per
deck**: *goldfish* (upper bound) and *effective* (goldfish ⊗ Force-of-Will/Daze survival) — the gap is
a format-health signal. (Connects to `project_meta_speed_metric` memory.)

**Deck-as-data combo line** (sim-executable):
```yaml
archetype: oops_all_spells
cluster: combo_turbo
fair_axis: unfair                 # ordinal unfair=0 ... fair=4
goldfish_clock: {p_turn1: 0.66, p_by_turn2: 0.76, p_by_turn3: 0.83}  # [cited]
combo_line:
  - {step: enabler, cards: [Balustrade Spy, Undercity Informer], mana: 2}
  - {step: trigger, cards: [Narcomoeba x3], from: self_mill}
  - {step: payoff_setup, cards: [Dread Return], cost: sac_3_creatures}
  - {step: payoff, cards: [Thassa's Oracle], win_if: library==0}
card_roles: {payoffs: [...], enablers: [...], engines: []}   # per-deck, NOT global
disruption_susceptibility: {force_of_will: high, daze: high, graveyard_hate: medium}
```

**Matchup matrix model:** N×N table of (archetype_a, archetype_b)→{winrate, sample_n, ci, window};
gate display on sample size (reuse the goldfish-track confidence-metadata pattern — flag n<100).

**Meta-positioning score:** `score(deck) = Σ field_share(arch) × winrate(deck vs arch)` (expected WR vs
the *weighted* field) — distinguishes "best metagame call" from "best deck." Let the user supply a
custom field distribution (their expected local meta). **Highest-value feature for a competitive player.**

**Sideboard recommender** = hoser→target bipartite graph; given an expected field, pick a 15-card package
by weighted set-cover over field share subject to color/slot constraints. Encode the anti-hate second
order (Veil/Defense Grid/Force of Vigor point at *hate cards*) to model the post-board meta.

**Encode caveats:** version-stamp Reanimator (pre/post-Entomb — same name, different clock); tempo/control
need a disruption-density axis, not a misleadingly-late turn-to-kill; combo "kill" ≠ always 20 damage
(storm-lethal / deck-out / Annihilator / Oracle-library=0).

---

## Sources (with dates)
Metagame: [mtgdecks.net/Legacy](https://mtgdecks.net/Legacy) (May 2026), [/winrates](https://mtgdecks.net/Legacy/winrates) (30,926 matches Nov 2025–May 2026), [MTGTop8 LE](https://mtgtop8.com/format?f=LE) (live), [MTGGoldfish meta](https://www.mtggoldfish.com/metagame/legacy), [AetherHub 180d](https://aetherhub.com/Metagame/Legacy/).
This Week in Legacy: [April 2026](https://www.mtggoldfish.com/articles/this-week-in-legacy-checking-in-on-legacy-for-april-2026), [It's Gonna Be May](https://www.mtggoldfish.com/articles/this-week-in-legacy-it-s-gonna-be-may), [Dimir](https://www.mtggoldfish.com/articles/this-week-in-legacy-dimir), [Is Reanimator Dead?](https://www.mtggoldfish.com/articles/this-week-in-legacy-is-reanimator-dead).
B&R: [Nov 10 2025](https://magic.wizards.com/en/news/announcements/banned-and-restricted-november-10-2025), [Feb 9 2026](https://magic.wizards.com/en/news/announcements/banned-and-restricted-february-9-2026).
Data infra: [Scryfall API](https://scryfall.com/docs/api), [bulk](https://scryfall.com/docs/api/bulk-data); [fbettega scraper](https://github.com/fbettega/mtg_decklist_scrapper), [cache](https://github.com/fbettega/MTG_decklistcache); [Badaro MTGOFormatData](https://github.com/Badaro/MTGOFormatData), [ArchetypeParser](https://github.com/Badaro/MTGOArchetypeParser); [MTGJSON](https://mtgjson.com/downloads/all-files/).
Archetype primers: ANT [cardmarket](https://www.cardmarket.com/en/Insight/Articles/The-Complete-Guide-to-Ad-Nauseam-Tendrils)/[eternalcentral](https://www.eternalcentral.com/the-legacy-laser-ubr-ad-nauseam-tendrils/); Oops [moxgate](https://www.moxgate.com/guides/oops-all-spells-legacy/); Doomsday [doomsday.wiki](https://doomsday.wiki/appendices/faq); Lands/Depths [cardkingdom](https://blog.cardkingdom.com/combo-crash-course-dark-depths/); Dimir Tempo [cardsrealm](https://mtg.cardsrealm.com/en-us/articles/legacy-dimir-tempo-deck-tech-and-sideboard-guide).
Attack-the-meta: [greensunszenith GY hate](https://greensunszenith.com/legacy-options-for-graveyard-hate/) (Jan 2026), [pendrellvale Lands matchups](https://pendrellvalecom.wordpress.com/menu/matchups/), [theepicstorm Mindbreak](https://www.theepicstorm.com/how-to-beat-mindbreak-trap/), [magic.gg Metagame Mentor](https://magic.gg/news/metagame-mentor-the-top-legacy-and-vintage-decks-for-eternal-weekend).

**Key caveats:** aggregator sites 403-block automated fetch (winrate cells snippet-derived, approximate); meta shares disagree across windows/sources; some primers dated (used for durable role/hate logic, not current shares); full N×N matrix needs headed scraping.
