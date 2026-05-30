---
description: The exact JSON rule schema of Badaro/MTGOFormatData (the archetype-detection ruleset we WRAP, ported to Python). Defines the data contract the legacy-engine `archetype/` module consumes — condition types, archetype/variant/fallback structure, color flags, and the Legacy taxonomy. Read before designing the rule-loader and the matching algorithm.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Documents the rule-as-data schema of Badaro/MTGOFormatData for Legacy: an archetype is a JSON file
  with a `Name`, an `IncludeColorInName` flag, a `Conditions` array (AND-combined), and optional ordered
  `Variants` (sub-archetypes that require the parent to match first). Twelve condition `Type` values cover
  presence/absence in main/side/either at 1+ and 2+ thresholds. Fallbacks are `CommonCards`-similarity
  "piles" used only when no archetype matches (≥10% overlap floor). Color/guild naming is NOT in this
  repo — it is computed by the consumer (MTGOArchetypeParser) from the manabase, with this repo supplying
  only `color_overrides.json` (land/non-land color hints) and the per-rule `IncludeColorInName` toggle.
  Legacy has ~174 archetype files + 8 fallbacks; the taxonomy matches the community tier list. Updated
  roughly monthly; last Legacy commit 2026-05-18.
key_findings:
  - "A rule = JSON object: `Name` (string), `IncludeColorInName` (bool), `Conditions` (array, ALL must pass = logical AND), optional `Variants` (ordered array of sub-rules). One archetype per file under `Formats/Legacy/Archetypes/`."
  - "Twelve condition `Type` values: `InMainboard`/`InSideboard`/`InMainOrSideboard` (any one of `Cards` present), the `OneOrMore*` and `TwoOrMore*` count-threshold trio for each zone, and `DoesNotContain`/`DoesNotContainMainboard`/`DoesNotContainSideboard` (exclusion). Within a condition the `Cards` array is OR/any-of; across conditions it is AND."
  - "Variants require the parent archetype to match FIRST, then the variant's own conditions; they are evaluated in array order and refine the label (e.g. Delver → Temur Delver / Tempo). `DoesNotContain` is the standard tool to make sibling archetypes mutually exclusive (Delver excludes Entomb/Doomsday/Hogaak/Grief; Show and Tell excludes Doomsday/Aluren/Reanimate/Hive Mind)."
  - "Fallbacks (`Formats/Legacy/Fallbacks/`, 8 files: Aggro, Control, Cradle, Dredge, GenericZoo, Midrange, Patchwork, Stompy) have `Name` + `IncludeColorInName` + `CommonCards` (no Conditions). Used only when no archetype matched; the deck is assigned to the highest-overlap fallback, requiring ≥10% card overlap, else unclassified."
  - "Color/guild naming is the CONSUMER'S job, NOT in this repo. MTGOFormatData supplies only the per-rule `IncludeColorInName` boolean and `Formats/Legacy/color_overrides.json` ({`Lands`,`NonLands`} each a list of {`Name`,`Color`} where Color is a WUBRG-letter string). The parser computes deck colors from the manabase + overrides, then prefixes the guild name (UB→Dimir) when the flag is true."
  - "Legacy coverage ≈ 174 archetype files; taxonomy matches the community tier list — Delver (with Tempo variant), Show and Tell, Lands, Reanimator, Oops! All Spells, Doomsday, Eldrazi, D&T, ANT/TES/RubyStorm, Painter, Depths, etc. are all present as named files."
  - "`metas.json` defines ~40 named format eras (StartDate yyyy-mm-dd + Name; latest `PostFrogBan` 2024-12-16) — rules are time-versioned by era, so a consumer must pick the era matching each event's date. Maintenance is monthly-ish; last Legacy commit `Mid May 2026 Formats update (#152)` on 2026-05-18."
  - "Track upstream by pinning a commit SHA of `master` and diffing `Formats/Legacy/` between SHAs; commits are tagged `[Legacy] ...` (mostly 'conflict' fixes) so the Legacy-relevant delta is greppable from the log."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md, relationship: extends}
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md, relationship: parallel-to}
  - {slug: docs/briefs/legacy-metagame.md, relationship: refines}
---

# Brief: Badaro/MTGOFormatData — The Archetype Rule Schema (Legacy)

## Purpose & scope
legacy-engine's `archetype/` module will **wrap Badaro/MTGOFormatData's rules, ported to Python**
(decision already made). This brief pins the **data contract** of those rules: the exact JSON shape an
`archetype/` rule-loader must parse and the matching semantics it must honor. It is the labeling layer
named in [`docs/briefs/legacy-metagame.md`](../legacy-metagame.md) §5 ("Use their Legacy rules so the
taxonomy matches the community's and is auditable").

**In scope:** the rule file format, archetype/variant/fallback distinction, the color-flag data, the
Legacy taxonomy coverage, the non-card metadata files, and versioning/maintenance.
**Out of scope (sibling subdomains):** the matching *algorithm* that evaluates these rules (CLASSIFY),
the fbettega decklist cache shape (INGEST), Scryfall card fields (CARD-CONTRACT), and the C#→Python
port strategy (PORT). I document the rule DATA, not the engine that runs it.

Repo: `https://github.com/Badaro/MTGOFormatData` (the data) — consumed by the companion engine
`https://github.com/Badaro/MTGOArchetypeParser` (the C# tool we are porting the *behavior* of).

## 1. The rule file format

### 1.1 Top-level layout
The repo root holds only `README.md` and `Formats/`. Each format lives under `Formats/<FormatName>/`.
For Legacy (`Formats/Legacy/`):

```
Formats/Legacy/
├── metas.json            # named format eras (date-versioned rule sets)
├── color_overrides.json  # land/non-land color hints for color detection
├── Archetypes/           # ~174 *.json — one named archetype per file
└── Fallbacks/            # 8 *.json — "piles" / catch-alls
```

### 1.2 An archetype rule (verbatim)
An archetype is a JSON object with `Name`, an optional `IncludeColorInName` boolean, a `Conditions`
array, and an optional `Variants` array. Each condition has a `Type` and a `Cards` array. **All
conditions must be satisfied for the archetype to match** (logical AND across conditions).

Real Legacy combo example — `Formats/Legacy/Archetypes/ANT.json` (verbatim):

```json
{
	"Name": "Ad Nauseam Tendrils",
	"IncludeColorInName": false,
	"Conditions": [
		{ "Type": "InMainboard", "Cards": ["Lion's Eye Diamond"] },
		{ "Type": "InMainboard", "Cards": ["Dark Ritual"] },
		{ "Type": "OneOrMoreInMainboard",
		  "Cards": ["Infernal Tutor", "Dark Petition", "Wishclaw Talisman"] },
		{ "Type": "OneOrMoreInMainboard",
		  "Cards": ["Past in Flames", "Gaea's Will", "Pair o' Dice Lost"] },
		{ "Type": "DoesNotContain", "Cards": ["Urza's Saga"] }
	]
}
```

Reading it: a deck is **Ad Nauseam Tendrils** iff it has *both* Lion's Eye Diamond *and* Dark Ritual in
the main, *and* at least one of (Infernal Tutor / Dark Petition / Wishclaw Talisman), *and* at least one
of (Past in Flames / Gaea's Will / Pair o' Dice Lost), *and* does **not** contain Urza's Saga (the last
condition separates ANT from Urza's-Saga storm builds). Note the dual semantics: **within** a
single condition the `Cards` array is **any-of (OR)**; **across** conditions it is **all-of (AND)**.

### 1.3 The condition `Type` enumeration (all 12, verbatim from README)
| Type | Meaning (with its `Cards` array) |
|---|---|
| `InMainboard` | at least one listed card is in the maindeck |
| `InSideboard` | at least one listed card is in the sideboard |
| `InMainOrSideboard` | at least one listed card is anywhere in the 75 |
| `OneOrMoreInMainboard` | ≥1 of the listed cards in the main (semantically same as `InMainboard`; used for readability of multi-card OR sets) |
| `OneOrMoreInSideboard` | ≥1 of the listed cards in the side |
| `OneOrMoreInMainOrSideboard` | ≥1 anywhere |
| `TwoOrMoreInMainboard` | ≥2 *distinct* listed cards in the main |
| `TwoOrMoreInSideboard` | ≥2 distinct in the side |
| `TwoOrMoreInMainOrSideboard` | ≥2 distinct anywhere |
| `DoesNotContain` | none of the listed cards appear anywhere (75-card exclusion) |
| `DoesNotContainMainboard` | none of the listed cards in the main |
| `DoesNotContainSideboard` | none of the listed cards in the side |

> Note on `TwoOrMore*`: the threshold counts **distinct card names from the list present**, not copies.
> See Delver below: `TwoOrMoreInMainboard` over a 5-card threat suite means "runs ≥2 of these threat
> names." (Confirm copy-vs-name semantics against the parser source during PORT — this is the one place
> the data alone is ambiguous; sibling CLASSIFY owns the precise count rule.)

### 1.4 The matching contract this data implies (for the loader, not the algorithm)
- A rule passes iff **every** condition passes. Conditions are unordered AND.
- Card names are **exact Oracle name strings** (e.g. `"Hogaak, Arisen Necropolis"`, `"Pair o' Dice
  Lost"`) — the join key to the card dimension (CARD-CONTRACT sibling owns Scryfall name normalization;
  DFC/split-name handling must be agreed at that boundary).
- `DoesNotContain*` conditions are how the dataset enforces **mutual exclusivity** between overlapping
  archetypes (see §2.2).

## 2. Archetype vs Variant vs Fallback

### 2.1 Variants (sub-archetypes, ordered, parent-gated)
An archetype may carry a `Variants` array. README (verbatim): *"for a variant to match the deck needs to
first match the 'main' archetype rules, then match the variant rules."* Each variant has the **same
structure** as an archetype (`Name`, `IncludeColorInName`, `Conditions`). The variant `Name` *replaces*
or refines the displayed archetype name. Order matters — the consumer evaluates variants top-down and
takes the first that matches.

Real tempo example — `Formats/Legacy/Archetypes/Delver.json` (verbatim):

```json
{
  "Name": "Delver",
  "IncludeColorInName": true,
  "Conditions": [
    { "Type": "TwoOrMoreInMainboard",
      "Cards": ["Dragon's Rage Channeler", "Delver of Secrets", "Orcish Bowmasters",
                "Nethergoyf", "Murktide Regent"] },
    { "Type": "DoesNotContain", "Cards": ["Entomb"] },
    { "Type": "OneOrMoreInMainboard", "Cards": ["Daze", "Snuff Out"] },
    { "Type": "DoesNotContain", "Cards": ["Up the Beanstalk"] },
    { "Type": "DoesNotContain", "Cards": ["Death's Shadow"] },
    { "Type": "DoesNotContain", "Cards": ["Animate Dead"] },
    { "Type": "DoesNotContain", "Cards": ["Hogaak, Arisen Necropolis"] },
    { "Type": "DoesNotContain", "Cards": ["Teferi, Time Raveler"] },
    { "Type": "DoesNotContain", "Cards": ["Doomsday"] },
    { "Type": "DoesNotContain", "Cards": ["Grief"] }
  ],
  "Variants": [
    { "Name": "Temur Delver", "IncludeColorInName": false,
      "Conditions": [ { "Type": "InMainboard", "Cards": ["Questing Druid"] } ] },
    { "Name": "Tempo", "IncludeColorInName": true,
      "Conditions": [ { "Type": "InMainboard", "Cards": ["Kaito, Bane of Nightmares"] } ] },
    { "Name": "Tempo", "IncludeColorInName": true,
      "Conditions": [
        { "Type": "InMainboard", "Cards": ["Nethergoyf"] },
        { "Type": "InMainboard", "Cards": ["Murktide Regent"] },
        { "Type": "DoesNotContain", "Cards": ["Kaito, Bane of Nightmares"] } ] }
  ]
}
```

This single file is the key worked example for the brief's mission (how "Dimir Tempo" arises):
- The **base** matches a blue-tempo shell (≥2 of the threat suite + Daze/Snuff Out), and uses a stack
  of `DoesNotContain` to peel off neighbors (Reanimator via Entomb/Animate Dead, Beanstalk control via
  Up the Beanstalk, Death's Shadow, Hogaak, Teferi-control, Doomsday, Scam via Grief).
- `IncludeColorInName: true` on the base means the consumer will **prefix the computed color/guild**.
- The **`Tempo` variant** (`Nethergoyf` + `Murktide Regent`, no Kaito) also has
  `IncludeColorInName: true`. A UB manabase here yields the final label **"Dimir Tempo"** — the color
  prefix is *not* stored in the rule; it is computed downstream and concatenated (see §3).
- `Temur Delver` overrides with `IncludeColorInName: false` (a fixed nickname, no color prefix).

### 2.2 Mutual exclusivity is data, not code
Sibling archetypes are kept disjoint by `DoesNotContain` lists inside each rule. Example — `Show
and Tell.json` (`ShowAndTell.json`, verbatim base) excludes Doomsday, Aluren, Reanimate, Manifold Key,
Coveted Jewel, and Hive Mind so that those other combo decks (which also might run Show and Tell as a
card) don't get mislabeled, and carries variants `Hypergenesis` and `Creative technique` (both gated on
`Omniscience`). The "conflict" commits in the changelog (e.g. *"[Legacy] Show and Tell conflict"*) are
precisely maintainers tuning these exclusion lists — a consumer should expect these lists to churn.

### 2.3 Fallbacks ("piles")
`Formats/Legacy/Fallbacks/` holds **8** files: `Aggro`, `Control`, `Cradle`, `Dredge`, `GenericZoo`,
`Midrange`, `Patchwork`, `Stompy`. A fallback has **no `Conditions`** — instead a `CommonCards` list.
Real example — `Fallbacks/Control.json` (verbatim):

```json
{
  "Name": "Control",
  "IncludeColorInName": true,
  "CommonCards": [
    "Teferi, Time Raveler", "Uro, Titan of Nature's Wrath", "Narset, Parter of Veils",
    "Leyline Binding", "Forth Eorlingas!", "Leovold, Emissary of Trest",
    "Snapcaster Mage", "Terminus"
  ]
}
```

Semantics (README, verbatim): fallbacks are *"a set of 'Common Cards' that are frequently used in decks
of this archetype"*; when no specific archetype matched, the consumer *"compare[s] this deck to all the
fallbacks defined and see[s] which fallback it shares the most cards with,"* subject to a *"rule
requiring at least 10% matching cards with a fallback."* Below that floor the deck is left unclassified.
Fallbacks carry `IncludeColorInName` too (Control = true → "Azorius Control" etc.).

**Precedence the data implies:** Variants ⊂ Archetypes (specific) → tried first; Fallbacks (generic
similarity) → only on archetype miss; unclassified → on fallback floor miss.

## 3. Color / guild naming — what is data vs what is algorithm
**Critical boundary fact: the guild-name mapping (UB→Dimir, WUB→Esper, etc.) is NOT in MTGOFormatData.**
It is computed by the consumer (MTGOArchetypeParser) and lives in that tool's source. There is **no
`color.json` at the repo root** (verified 404) and **no guild table** in the data repo. What the rule
DATA contributes to color naming is exactly two things:

1. **`IncludeColorInName` (per-rule boolean)** — the toggle that says "prefix this archetype's name with
   the computed color/guild" (Delver/Tempo/Control = true; ANT/Show and Tell/Temur Delver = false,
   because those have canonical color-independent names). This is the override mechanism for color
   naming — there is no separate override flag; the boolean IS the flag.
2. **`color_overrides.json` (per-format file)** — manual color hints feeding the consumer's color
   detector. Structure: two keys, `Lands` and `NonLands`, each a list (or `null`) of
   `{ "Name": <card>, "Color": <WUBRG-letters> }`. For Legacy, `NonLands` is currently `null` and
   `Lands` carries ~6 five-color lands (e.g. `Ancient Ziggurat`, `Sliver Hive`) marked `"WUBRG"` so a
   five-color manabase isn't mis-detected from those fixers.

**Color-detection inputs (for the consumer; CLASSIFY owns the algorithm):** the deck's colors are
derived from the **mana symbols of the nonland cards plus the lands' produced colors**, with
`color_overrides.json` supplying corrections for lands (and, in principle, nonlands) whose color the
naive detector would get wrong. The resulting color set (e.g. `{U,B}`) is mapped to a guild/shard name
**by the parser**, then prefixed to the archetype `Name` only when `IncludeColorInName` is true. So
"Dimir Tempo" = (parser computes `UB` from the manabase) + (guild table `UB→Dimir`, in the parser) +
(Delver→Tempo variant `Name`, with `IncludeColorInName:true`, from this repo).

> **Implication for the port:** legacy-engine must supply its own guild-name table (it is not vendored
> here) — but that is shared, stable MTG convention (10 guilds / 10 shard-wedge / WUBRG), and belongs to
> the CLASSIFY/PORT siblings, not this data contract. From the DATA side, honor `IncludeColorInName` and
> load `color_overrides.json`.

## 4. Legacy taxonomy coverage
`Formats/Legacy/Archetypes/` contains **≈174 JSON files** (plus 8 fallbacks). The taxonomy maps cleanly
onto the community tier list in [`legacy-metagame.md`](../legacy-metagame.md) §2:

| Community tier-list name | MTGOFormatData file (Archetypes/) |
|---|---|
| Dimir / UR Tempo (Delver) | `Delver.json` (base + `Tempo` variant + `Temur Delver`) |
| Sneak & Show / Show and Tell | `ShowAndTell.json` (+ `ReaShow.json`) |
| Lands / Dark Depths | `Lands.json`, `Depths.json`, `Landfall.json` |
| Reanimator | `Reanimator.json` |
| Oops All Spells | `Oops! All Spells.json` |
| Doomsday | `Doomsday.json` |
| Eldrazi | `Eldrazi.json` |
| Death & Taxes | `D&T.json` (+ `Vial.json`) |
| ANT / TES / Ruby Storm | `ANT.json`, `TES.json`, `RubyStorm.json`, `NecroStorm.json`, `BlackSagaStorm.json` |
| Painter | `Painter.json`, `Cephalid painter.json` |
| Energy | `Energy.json` |
| Stoneblade | `Stoneblade.json` |
| Tron / Artifacts Prison | `Tron.json`, `MUD.json`, `Mystic Forge combo.json`, `Post.json` |
| Mono-color / Stompy / Burn / fringe | `RStompy.json`, `Burn.json`, `Merfolk.json`, `Elves.json`, `Goblins.json`, `infect.json`, `dredge.json`, `Manaless Dredge.json`, `death's shadow.json`, etc. |

The file granularity is **finer** than the community tier list (it splits storm into ANT/TES/RubyStorm/
NecroStorm and has many niche combos: `Aluren`, `Food Chain`, `High Tide`, `Worldgorger Combo`,
`Hive Mind`, `Echo of Eons`, `Tin Fins`, `Charbelcher`, etc.). For meta-share reporting, legacy-engine
will likely need a **roll-up map** from these fine labels to display archetypes (an engine-side concern,
not in the data). File-naming is inconsistent (mixed case, spaces, `!`, `&`, `'`) — the loader must
treat the on-disk filename as opaque and use the JSON `Name` field as the identifier.

## 5. Non-card metadata the rules depend on
1. **`Formats/Legacy/color_overrides.json`** — land/non-land color hints (see §3). The only card→color
   reference data in the repo; deliberately minimal (relies on the consumer's mana-symbol detector for
   the rest).
2. **`Formats/Legacy/metas.json`** — an array of **~40 named format eras**, each `{ "StartDate":
   "yyyy-mm-dd", "Name": <era> }` (e.g. `StartOfMtgoData` 2015-11-01 … `PostModernHorizons3` 2024-06-11,
   `PostGriefBan` 2024-08-26, latest in-file `PostFrogBan` 2024-12-16). This is **time-versioning
   metadata**: it lets a consumer bucket each tournament by the rules-era in force on its date. (The
   `master` rules are "current"; eras are for historical attribution / reproducible relabels of old
   events.)
3. **No `lands` list, no set-legality table, no global card DB** lives in this repo. Card legality and
   card attributes come from the card dimension (Scryfall — CARD-CONTRACT sibling). MTGOFormatData is
   intentionally thin: it is *rules + color hints + eras*, nothing more.

## 6. Maintenance & versioning
- **Cadence:** roughly monthly, event-driven (new sets, bans, and "conflict" disambiguation). Recent
  Legacy-tagged commits: `Mid May 2026 Formats update (#152)` with *"[Legacy] Show and Tell conflict"*
  on **2026-05-18** (matches `legacy-metagame.md`'s "pushed 2026-05-18"); `[Legacy] Artifacts`
  2026-01-26; `[Legacy] Conflicts` / `[Legacy] Energy` 2025-11-18 (post-Entomb-ban window); earlier
  2025 commits ~every 1–3 months. Gaps of 2–3 months occur.
- **Tracking upstream (recommended for legacy-engine):**
  1. **Pin a commit SHA** of `master` in config; never float on HEAD (rules churn changes labels and
     thus reported meta shares — pinning makes relabels reproducible).
  2. **Diff `Formats/Legacy/` between the pinned SHA and a newer SHA** (e.g. via the GitHub compare API
     or `git diff <old>..<new> -- Formats/Legacy`) to see exactly which archetype/variant/exclusion
     lists changed before adopting an update.
  3. **Filter the commit log by `[Legacy]` tags** — maintainers prefix Legacy changes, so the
     Legacy-relevant delta is greppable; most are exclusion-list ("conflict") tweaks.
  4. **Snapshot/vendor** the rule set at the pinned SHA into legacy-engine (the cache is community-run
     and could move; vendoring also lets the port add fields without upstream coupling).

## Suggested cross-references to sibling subdomains
- **CLASSIFY (matching algorithm)** — *consumes-this-contract.* This brief defines the rule DATA;
  CLASSIFY owns evaluating it: AND-across-conditions / OR-within-`Cards`, the `TwoOrMore*` copy-vs-name
  count rule (flagged ambiguous here — resolve against parser source), variant ordering/first-match,
  fallback `CommonCards` similarity + the 10% floor, and the precedence chain (variant → archetype →
  fallback → unclassified). Hand the condition-type table (§1.3) and the Delver/ANT/ShowAndTell examples
  straight to that subdomain.
- **CARD-CONTRACT (Scryfall fields)** — *shared-join-key.* Rule `Cards` arrays are exact Oracle name
  strings; CARD-CONTRACT owns name normalization, DFC/split/adventure naming, and the mana-symbol →
  color derivation that `color_overrides.json` (§3) supplements. The join key contract (exact name match
  vs normalized) must be agreed at this edge.
- **PORT (C#→Python)** — *port-target.* The guild-name table and the color-detection algorithm are NOT
  vendored in MTGOFormatData (verified) and must be reimplemented from MTGOArchetypeParser source; this
  brief tells PORT which pieces are data (load as-is: archetypes, fallbacks, `color_overrides.json`,
  `metas.json`) vs code (reimplement: matcher, color detector, guild map). Recommend vendoring the data
  at a pinned SHA (§6).
- **INGEST (fbettega cache)** — *upstream-producer.* INGEST yields the decklists (main/side card lists)
  that these rules score; the mainboard/sideboard split the condition types depend on must survive
  ingestion intact, and each deck needs an event date to pick the right `metas.json` era (§5).
- **SERVE/OPS** — *versioning-surface.* The pinned-SHA + diff workflow (§6) is an ops concern: rule
  updates change historical meta shares, so relabels should be a versioned, reproducible operation, not
  an implicit HEAD pull.
- **legacy-metagame.md (existing)** — *labeling-layer-detail.* This brief is the deep dive behind that
  brief's §5 line naming MTGOFormatData as the archetype-label source; it does not duplicate the
  metagame/tier content there.
