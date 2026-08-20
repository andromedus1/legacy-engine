---
source_handle: ddv-packages-module-census
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Doomsday module census in the refreshed tournament store

## Structural metadata

- Tables read: `decks`, `deck_cards`, and `tournaments` from `data/legacy.duckdb` in read-only mode.
- Archetype predicate: `decks.archetype = 'Doomsday'`.
- Current window: stored tournament date on or after 2026-08-10.
- Historical census window: stored tournament date on or after 2026-01-01.
- A “list” is one `(tournament_id, deck_idx)` source row. A pilot count uses distinct stored player
  names. Older source/date duplication means list totals are not independent tournament counts.

## Key passages

1. **Current shared core and build axes.** All 12 current lists contain four Brainstorm, four Dark
   Ritual, four Doomsday, four Force of Will, Lotus Petal, Street Wraith, Thassa's Oracle, Edge of
   Autumn, Cavern of Souls, Consider, Lion's Eye Diamond, and Undercity Sewers. Eleven contain Flow
   State and eleven contain Thoughtseize. Five lists from five pilot names use Personal Tutor (12
   copies); eight lists from seven names use Tamiyo (27); four lists from four names use Bilbo (10);
   and five lists from five names use Unearth (five). Three lists contain Tamiyo, Bilbo, and Unearth
   together.

2. **Current tempo/control main packages.** Three current lists from two pilot names use three
   Wasteland; two lists use main-deck Murktide Regent; one uses main-deck Orcish Bowmasters. Two
   HJ_Kaiser rows use one main-deck Jace, Wielder of Mysteries; sideboard Jace occurs in three lists
   from three other pilot names. One current list omits Daze, and the wakame green-white list omits
   Flow State.

3. **Current transformational creature inventory.** Sideboards contain Dauthi Voidwalker in 11
   lists (22 copies), Barrowgoyf in ten (25), Murktide Regent in seven (14), Orcish Bowmasters in six
   (11), and Tamiyo in two (two). The same 12-list slice includes ten sideboard-creature lists
   carrying at least two different names from that set; several Esper and Dimir lists carry four
   distinct threat names.

4. **Current protection and disruption inventory.** Every current sideboard contains Force of
   Negation (25 total copies). Consign to Memory occurs in six lists (nine copies), Duress in four
   mains plus two sideboards, Misdirection in one main and one sideboard, and Voice of Victory in
   one main plus another list's sideboard. White/green and red protection packages are recorded in
   the separate color-package attestations.

5. **Current removal and graveyard inventory.** Fatal Push appears in four sideboards (nine copies)
   and one main (two); Long Goodbye in five sideboards; Bitter Triumph in three; Swords to
   Plowshares and Prismatic Ending each in five sideboards or 75s; Portable Hole in two. Dauthi is
   the repeated graveyard-interaction creature. The noncreature graveyard cards are concentrated:
   one list has two Nihil Spellbomb, one has Surgical Extraction, and one has Tormod's Crypt.

6. **Historical tutor, acceleration, and draw alternatives.** In 2026 source rows, main-deck Cabal
   Ritual appears under 36 distinct pilot names and Spoils of the Vault under nine. Alternate
   draw/card-flow cards include Quantum Riddler under 22 names, Deep Analysis under 14, The One Ring
   under 11, Night's Whisper under eight, Lórien Revealed under six, Predict under five, and Ideas
   Unbound under two. These counts establish use, not a single coherent package or comparative
   performance.

7. **Historical alternate wins and transformation threats.** Emrakul, the Aeons Torn and Shelldock
   Isle occur together in seven source rows from at least six pilot names. Four sideboard Paradigm
   Shift occurs in five rows from three names. Four sideboard Cori-Steel Cutter occurs in six rows
   from four names, each with Badlands and Volcanic Island. Four sideboard Moonshadow occurs in
   eight rows from seven names. Sheoldred, the Apocalypse appears in sideboards under 26 names and
   Kaito, Bane of Nightmares under four. Phyrexian Arena appears in six sideboard rows from three
   names.

8. **Historical graveyard, prison, and control pivots.** Sideboard Leyline of the Void appears under
   15 pilot names, Grafdigger's Cage under 12, Containment Priest under eight, Opposition Agent under
   three, and Chancellor of the Annex under two. Mana Maze appears in two source rows from one pilot.
   Engineered Explosives, broad removal, blue blasts, bounce, and additional counterspells recur,
   but individual occurrence does not establish that they were registered as one fixed package.

9. **Banned engine boundary.** The Fantasticar appears in 173 2026 source rows and Mishra's Bauble
   in 125, with both ending in the stored rows dated August 9 or earlier. This historical engine is
   excluded from current package compatibility because The Fantasticar is now banned in Legacy.

10. **Dependence warning.** The historical store contains repeated players, exact lists, source
    URLs, and date anomalies. The module census therefore uses pilot breadth to distinguish a
    distributed module from one pilot's repeat, but neither pilot nor row counts are matchup rates.

11. **Historical protection alternatives.** Across 2026 source rows, protection/discard cards occur
    under these distinct pilot-name counts: Force of Negation 186, Consign to Memory 157, Duress 84,
    Flusterstorm 76, Misdirection 17, Spell Pierce seven, Orim's Chant five, Inquisition of Kozilek
    four, Cabal Therapy four, Pact of Negation three, Commandeer three, and Unmask two. Board
    placement varies, so these are independent card modules rather than one sideboard package.

12. **Historical graveyard alternatives.** Dauthi Voidwalker appears under 147 names, Surgical
    Extraction 25, Nihil Spellbomb 24, Leyline of the Void 15, Tormod's Crypt 13, Grafdigger's Cage
    12, Faerie Macabre five, and Cling to Dust two. These are occurrence counts across mixed
    regimes, not comparative performance.

## Revisions

- 2026-08-20 — Correction: changed the current multi-threat count from eight to ten after an
  explicit per-deck distinct-name query; the package position is unchanged.
- 2026-08-20 — Refresh: extended the census with protection and graveyard alternatives requested at
  Checkpoint B.
