---
source_handle: ddv-landscape-current-db
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Refreshed legacy-engine tournament corpus: Doomsday configurations

## Structural metadata

- DuckDB tables read: `decks`, `deck_cards`, and `tournaments`.
- Refresh extent observed in the queried rows: Doomsday entries through 2026-08-18.
- Archetype predicate: `decks.archetype = 'Doomsday'`.
- Exact-list identity: SHA-256 over the ordered `(board, card name, count)` rows for one
  `(tournament_id, deck_idx)`.
- Color-package classification used for this extract:
  - green signal: Veil of Summer, Carpet of Flowers, Abrupt Decay, Witherbloom Charm/Command,
    Boseiju, Tropical Island, or Bayou;
  - white signal: Swords to Plowshares, Teferi, Tundra, Scrubland, Voice of Victory, Portable Hole,
    or Prismatic Ending;
  - red signal: Pyroblast, Red Elemental Blast, Badlands, or Volcanic Island.

## Attested extracts

### 1. Post-ban entries, 2026-08-10 through 2026-08-18

The corpus contains 12 Doomsday entries from 11 pilot names and 12 exact-list hashes. Six are
blue-black-only by the signals above, four carry white but not green or red, and two carry both
white and green. No post-ban entry carries a pure green or red package.

The six blue-black entries are SmokyboyJFF (5-0 league, August 10), HJ_Kaiser (7th Challenge,
August 12), Ney Costa Lima (16th paper event, August 13), 2plus2isfive (10th Challenge, August 16),
HJ_Kaiser (32nd Challenge, August 16), and clan (5-0 league, August 18). Every one contains
creatures in the main deck or sideboard drawn from Tamiyo, Murktide Regent, Barrowgoyf, Orcish
Bowmasters, Bilbo, or Dauthi Voidwalker.

Three white entries use the Teferi/Swords family: thescuba96 (5-0 league, August 11) has two Teferi,
three sideboard Swords, two sideboard Prismatic Ending, one Tundra, and one Scrubland; Battlegrounds
(5-0 league, August 12) has the same counts for those cards; rgbandre (14th Challenge, August 15)
has two Teferi, three sideboard Swords, two sideboard Prismatic Ending, one Tundra, and one
Scrubland. Enrichetta's August 11 5-0 is a distinct white creature/permanent package: one main-deck
Voice of Victory, one Tundra, and one sideboard Portable Hole, with no Teferi or Swords.

The two white-green entries are wakame (5-0 league, August 14) and wizardpasta (17th Challenge,
August 15). Wakame has three main-deck Teferi, three main-deck Veil, two Tropical Island, one
Tundra, one Scrubland, and three each of sideboard Carpet, Swords, and Prismatic Ending.
Wizardpasta has two main-deck Swords, one main-deck Veil, one each of Tropical Island, Tundra, and
Scrubland, then three Carpet, two more Swords, one more Veil, two Voice of Victory, one Portable
Hole, and one Prismatic Ending in the sideboard.

All six post-ban league entries are recorded as 5-0; the six non-league entries range from 7th to
32nd. The queried tables do not supply a denominator of failed league runs.

### 2. Green-only configuration history

Using the same signals, the corpus has 29 green-without-white-or-red entries from 14 pilot names and
22 exact-list hashes between 2026-05-23 and 2026-07-13. Period splits are 19 rows / 8 pilots / 12
hashes for May 18-June 19 and 10 rows / 7 pilots / 8 hashes for June 20-August 9. There are no such
entries from August 10 through August 18.

Representative green-only packages include:

- nao_xx, second in the June 6 Challenge: Bayou, Tropical Island, two main-deck Witherbloom Charm,
  two sideboard Carpet, and one sideboard Veil;
- Dominic Rode, eighth at Legacy League Cologne on July 6: Bayou, Tropical Island, two sideboard
  Abrupt Decay, three Carpet, and four Veil;
- wakame, 5-0 on July 13: Bayou, Tropical Island, one main-deck Witherbloom Charm, and a sideboard of
  three Carpet, two Veil, and two Witherbloom Charm.

The corpus also includes green-white hybrids before the ban, including wakame's repeated
Teferi/Veil/Carpet/Swords list on July 22 and July 25.

### 3. Hexing Squelcher Grixis history

There are nine 2026 Doomsday entries containing Hexing Squelcher from May 24 through June 27. They
represent six pilot names and five exact-list hashes:

- nevilshute, 10th in the May 24 Showcase Challenge, 5-0 on May 29, and 3rd in the May 31 Challenge;
- Solace_Solanum, 5-0 on May 29;
- TDjr, 57th at the May 31 SCG CON paper event;
- Zlatan87, 5-0 entries dated June 8 and June 17;
- turbo_land, 9th at Bazaar of Boxes on June 13;
- Wilson Prado, 8th at a paper event on June 27.

The commonly repeated package has one Badlands and one Volcanic Island, one Hexing Squelcher main,
two Squelcher side, and two Pyroblast side. Zlatan87's repeated list instead has two sideboard
Squelcher and two Red Elemental Blast. Wilson Prado has one Squelcher main and one side.
No Hexing Squelcher Doomsday entry occurs after June 27, including the August 10-18 post-ban slice.

### 4. Duplicate and date-quality observations

Some records are repeated across distinct MTGO source URLs or carry a tournament date that does not
match the date embedded in the source URL. Examples include the same June 20 Challenge lists also
attached to a May 18 URL, and same-player/same-list Challenge rows duplicated on June 6 with a June 1
URL. Consequently, raw row totals in the older windows are source-entry counts, not a clean count of
independent tournament appearances. Pilot counts and exact-list hashes reduce, but do not eliminate,
copy and identity dependence. The 12-row August 10-18 slice has no exact duplicate URI/player/list
tuple in this extract.

### 5. Period definitions used in the extract

The read-only aggregate grouped dates as May 18-June 19 (clean pre-exposure), June 20-August 9
(Fantasticar interval), and August 10-August 18 (post-ban). These are query partitions applied to
the stored tournament date. They do not repair the older date/source mismatches described above.

### 6. Core and tutor branches

The 12 post-ban entries do not share one nonland core. Five contain main-deck Personal Tutor, eight
contain main-deck Tamiyo, three contain three Wasteland, two contain main-deck Murktide, four contain
Bilbo, and four contain Teferi. One list, 2plus2isfive, overlaps the Personal Tutor and Tamiyo sets;
three of the four Bilbo lists also contain Teferi. The exact selected-card signatures are unique
across all 12 entries.

The post-ban Personal Tutor entries are SmokyboyJFF (three), Enrichetta (three), wizardpasta (one),
2plus2isfive (two), and clan (three). The three Wasteland lists are HJ_Kaiser on August 12, Ney Costa
Lima on August 13, and HJ_Kaiser on August 16; the first two also have two main-deck Murktide, while
the August 16 list has two Bilbo instead. Bilbo also appears in the thescuba96, Battlegrounds, and
rgbandre white lists.

Before the ban, the corpus records several other core branches. During June 20-August 9, 173 of 226
entries contain main-deck The Fantasticar and 125 contain Mishra's Bauble. From May 23-July 11, The
One Ring occurs in 15 source entries from five pilot names and eight exact-list hashes after
identical duplicate card rows are collapsed; most are nao_xx green lists. Main-deck Cabal Ritual
occurs in 35 source entries between May 19 and July 20. Personal Tutor occurs in 25 clean-pre rows,
28 Fantasticar-interval rows, and five post-ban rows.

### 7. Transformational creature packages

Sideboard Force of Negation appears in 84 of 85 clean-pre entries, 223 of 226 Fantasticar-interval
entries, and all 12 post-ban entries. The corresponding sideboard counts for Barrowgoyf are 76,
184, and 10; for Dauthi Voidwalker, 55, 165, and 11; for Murktide Regent, 4, 103, and 7; and for
Orcish Bowmasters, 9, 69, and 6. Main-deck Tamiyo rises from 40 clean-pre entries to eight of the 12
post-ban entries. These counts show both sideboard transformation and main-deck creature branches.

Two bounded transformational packages appear during the Fantasticar interval:

- Four sideboard Moonshadow occurs in seven source entries from six pilots and four exact-list
  hashes, dated June 24-29. Every entry also has The Fantasticar and Mishra's Bauble main. Recorded
  results include two Challenge wins and three 5-0 league entries, alongside lower finishes.
- Four sideboard Cori-Steel Cutter occurs in six source entries from four pilots and three exact-list
  hashes, dated July 12-21. All six also have main-deck Badlands, Volcanic Island, Mishra's Bauble,
  and three Fantasticar, plus four sideboard Barrowgoyf. Eureka22422 supplies three of the six rows,
  including two 5-0s; the other results include 10th, 26th, 1-1, and 0-1.

Four sideboard Chancellor of the Annex appears in nine source entries, but eight are attached to
wonderPreaux and several are source/date duplicates; one additional ragavanejoyer row carries the
same four-card package. This is a concentrated pilot lineage rather than broad adoption.

### 8. Protection, interaction, and value modules

Main-deck Flusterstorm occurs in 26 of 85 clean-pre entries and 15 of 226 Fantasticar-interval
entries, then disappears from the 12 post-ban entries. Main-deck Misdirection occurs in 16
Fantasticar-interval entries and one post-ban entry; one additional post-ban list has Misdirection
in the sideboard. The green Veil/Carpet, white Teferi/Swords/Ending, and red Squelcher/Blast modules
are recorded in sections 1-3 above.

Several recurring cards do not define a stable list family:

- Sheoldred, the Apocalypse appears in 22 sideboards across multiple color and core branches, plus
  one main deck. It is usually a singleton.
- Quantum Riddler appears somewhere in 18 source entries from 13 pilots and 15 exact-list hashes,
  split between main and side; it co-occurs with Fantasticar, Tamiyo/Wasteland, green-white, and
  creature-transform lists rather than one common shell.
- Phyrexian Arena appears in six sideboards from three pilots and five exact-list hashes between
  July 18 and August 1, as one or two copies alongside different creature packages.
- Voice of Victory appears in 13 source entries from eight pilots and 12 hashes, usually in the
  sideboard of white or white-green lists; Enrichetta has the one post-ban main-deck copy.
- Vision Charm appears in 12 source entries from four pilots and nine hashes, with clan accounting
  for seven entries. Cling to Dust appears in 14 source entries but only two pilot names, with
  source/date duplication. These are pilot-concentrated utility modules.

### 9. One-off and duplicate-amplified experiments

The 80-card Yorion list attributed to michaelvlevine contains four Thundertrap Trainer, one Temporal
Mastery, main-deck Barrowgoyf/Murktide/Tamiyo/Wasteland, and a Yorion sideboard. It appears under
three source URLs all stored on June 20 with the same player, result, and underlying configuration.
It is one experiment amplified by source duplication.

Other narrow experiments include two wonderPreaux appearances of two sideboard Dark Confidant plus
one Skeletal Scrying, two duplicated source entries for ice_nine_BIGFAN's main-deck Reanimate, and
two duplicated source entries for clan's sideboard Reanimate. These do not establish independent
configuration families.

### 10. Main-deck location audit for package interchangeability

Every pure-green lineage entry in section 2 has Bayou or Tropical Island in the main deck, and the
representative configurations also place Veil or Witherbloom Charm main. Every Hexing Squelcher
Grixis entry in section 3 has Badlands or Volcanic Island main; seven of the nine source entries
also have a main-deck Squelcher.

The current Esper and white-green entries in section 1 place Tundra/Scrubland and their Teferi,
Voice, Swords, or Veil cards in the main deck. Older white pivots can be sideboard-contained:
rgbandre on July 27 and thescuba96 on July 28 have Fantasticar turbo main decks with Tundra,
Scrubland, three Teferi, and three Swords all in the sideboard; ZeeSeeKay on August 8 similarly has
Tundra, Scrubland, four Tamiyo, three Teferi, and two Swords in the sideboard.

The Moonshadow and Chancellor packages in section 7 are sideboard-only in their repeated forms and
do not add a main-deck mana source. The Cori-Steel Cutter package is not: its six entries all place
Badlands and Volcanic Island in the main deck. Barrowgoyf/Dauthi/Murktide/Bowmasters packages occur
both as sideboard-only transformations and as lists with Tamiyo, Murktide, Bowmasters, Bilbo, or
Barrowgoyf already in the main deck.

## Revisions

- 2026-08-20 — Correction: changed the Squelcher cluster from five to six pilot names after
  reconciling the stated total with the six enumerated names and the direct database result. The
  five exact-list-hash count is unchanged.
