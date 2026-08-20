---
source_handle: ddv-compare-current-corpus
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Refreshed Doomsday comparison corpus

## Source structure

The DuckDB store was opened read-only. The observations below join `tournaments`, `decks`, and
`deck_cards` on tournament and deck identifiers. Dates use the first ten characters of the stored
tournament date. The refresh reaches 2026-08-19; the comparison window below begins 2026-08-10,
the first date after the Fantasticar exclusion interval recorded by the engagement dispatch.

## Key passages

1. **Current window.** `left(t.date,10) >= '2026-08-10'` returns 386 deck rows. The largest assigned
   archetype counts are Tron 31, Dimir Tempo 28, Dimir Midrange 25, Boros Energy 25, Death & Taxes
   23, Azorius Midrange 18, Blue Artifacts 18, Aluren 15, Lands 14, Golgari Landfall 12, Izzet
   Delver 12, Show and Tell 12, Doomsday 12, Unknown 12, Grixis Reanimator 11, Mardu Energy 9, TES
   8, and White Beanstalk 8. These are list prevalences, not matchup frequencies or win rates.

2. **Current Doomsday sample.** The 12 Doomsday rows represent 11 case-normalized pilot names. Ten
   lists, from nine pilots, put at least one of Barrowgoyf, Murktide Regent, or Tamiyo, Inquisitive
   Student in the sideboard. Ten lists contain Barrowgoyf in the sideboard (25 total copies); seven
   contain sideboard Murktide Regent (14 copies); two contain sideboard Tamiyo (two copies).

3. **White and green packages overlap the creature plan.** Five current lists contain Teferi, Time
   Raveler or Swords to Plowshares; four contain Teferi in the main deck (nine copies total), five
   contain Swords across main or side (16 copies total), and three of those five also contain the
   sideboard creature package. Two current lists contain Veil of Summer or Carpet of Flowers. Both
   green lists also contain white cards and white duals; neither is a pure BUG configuration. The
   two green-white lists contain six total sideboard Carpets, five total Veils across main and side,
   Swords, Tropical Island, Tundra, and Scrubland.

4. **Representative current Dimir list.** 2plus2isfive's 2026-08-16 Challenge 10th-place list uses
   four Underground Sea, Undercity Sewers, one Island, one Swamp, and no splash dual. Its sideboard
   is 3 Barrowgoyf, 2 Murktide Regent, 2 Dauthi Voidwalker, 3 Fatal Push, 1 Snuff Out, 2 Force of
   Negation, 1 Engineered Explosives, and 1 Jace, Wielder of Mysteries.

5. **Representative current Esper list.** Battlegrounds' 2026-08-12 League 5-0 list uses three
   Underground Sea, one Tundra, one Scrubland, Undercity Sewers, one Island, and one Swamp. It has
   two Teferi in the main deck; its sideboard is 2 Barrowgoyf, 2 Murktide Regent, 2 Dauthi
   Voidwalker, 2 Orcish Bowmasters, 2 Force of Negation, 2 Prismatic Ending, and 3 Swords to
   Plowshares.

6. **Representative current green-white hybrid.** wakame's 2026-08-14 League 5-0 list uses two
   Underground Sea, two Tropical Island, one Tundra, one Scrubland, Undercity Sewers, and one
   Island. The main deck contains three Teferi and three Veil; the sideboard is 3 Carpet, 3 Force
   of Negation, 3 Prismatic Ending, 3 Swords, 2 Nihil Spellbomb, and 1 Jace. The current 2026-08-15
   wizardpasta Challenge list is a second green-white configuration: one main and one side Veil,
   three Carpet, four total Swords, one Prismatic Ending, one Tropical Island, Tundra, and
   Scrubland.

7. **Current results are heterogeneous.** The 12 current Doomsday rows include six League 5-0s,
   Challenge finishes of 7th, 10th, 14th, 17th, and 32nd, and one paper 16th. The two green-white
   rows are a League 5-0 and Challenge 17th; the four main-deck-Teferi rows are two League 5-0s, a
   League 5-0 green-white list, and Challenge 14th. The store does not provide a controlled
   comparison among packages.

8. **Squelcher's dated Grixis cluster.** From 2026-04-20 onward, nine Doomsday lists contain Hexing
   Squelcher, representing six pilots. Every one uses Badlands plus Volcanic Island. Seven use
   Pyroblast and two use Red Elemental Blast. Six use the same visible package of 1 Squelcher main,
   2 Squelcher side, 2 Pyroblast side, and 4 Barrowgoyf side; the two Zlatan87 lists omit the main
   Squelcher and use 2 Squelcher plus 2 Red Elemental Blast in the sideboard. Results include four
   League 5-0 rows, Challenge 3rd and Showcase 10th, paper 8th and 9th, and paper 57th. The latest
   Squelcher row is dated 2026-06-27; none appears in the current 12-list window.

9. **Representative Grixis list.** nevilshute's 2026-05-24 Showcase 10th-place list uses three
   Underground Sea, one Badlands, one Volcanic Island, Undercity Sewers, one Island, and one Swamp.
   It has one Squelcher main; its sideboard is 4 Barrowgoyf, 2 Squelcher, 2 Pyroblast, 2 Force of
   Negation, 2 Long Goodbye, 1 Brazen Borrower, 1 Nihil Spellbomb, and 1 Sheoldred, the Apocalypse.

10. **Pure BUG remains evidenced but is not current-window adoption.** Pure green-black-blue lists
    using Bayou and Tropical Island recur between April and July. Examples include Dominic Rode's
    2026-07-06 paper 8th with 4 Veil, 3 Carpet, and 2 Abrupt Decay in the sideboard; wakame's
    2026-07-13 League 5-0 with 2 sideboard Veil and 3 Carpet; and gusti99's 2026-06-20 Challenge 6th
    with 2 Veil, 3 Carpet, and 2 Abrupt Decay. The latest pure BUG row found is 2026-07-13. Several
    repeated pilots and visibly repeated packages mean list rows are not independent endorsements.

## Revisions

- 2026-08-20 — Correction: changed the current League 5-0 total from seven to six after
  reconciling the 12-row outcome inventory: six League rows plus five Challenge rows and one paper
  row. The listed family outcomes are unchanged.
