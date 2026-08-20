---
source_handle: ddp-taxonomy-postban
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Post-ban Doomsday registrations: construction measurements

## Source structure

The local DuckDB store was opened read-only. Rows join `tournaments`, `decks`, and `deck_cards` by
tournament and deck index, require `decks.archetype = 'Doomsday'`, and use stored dates 2026-08-10
through 2026-08-18. This produces the same twelve-list post-ban population used by the outcome
extract. A broader maindeck-Doomsday predicate would add the stored `Conflict(Doomsday,TES)` lassi
row and is not used here. The construction columns use
the same literal card sets defined in `ddp-taxonomy-registry`; the hashes below are short local
fingerprints of the ordered main/side card-count rows, included only to expose exact-list identity.

## Key passages

1. **Twelve exact registrations.** No two rows have the same exact-75 fingerprint.

   | date | pilot | result | fp | lands | acc | select | main-value | Wasteland | side-fair |
   |---|---|---|---|---:|---:|---:|---:|---:|---:|
   | 2026-08-10 | SmokyboyJFF | 5-0 | 67381536 | 16 | 8 | 5 | 0 | 0 | 6 |
   | 2026-08-11 | Enrichetta | 5-0 | 141f146e | 17 | 8 | 6 | 0 | 0 | 11 |
   | 2026-08-11 | thescuba96 | 5-0 | a0f74469 | 17 | 7 | 3 | 8 | 0 | 8 |
   | 2026-08-12 | Battlegrounds | 5-0 | ed1b7664 | 17 | 7 | 3 | 10 | 0 | 8 |
   | 2026-08-12 | HJ_Kaiser | 7th Place | fa382796 | 19 | 7 | 4 | 6 | 3 | 6 |
   | 2026-08-13 | Ney Costa Lima | 16th Place | 5a07979f | 19 | 7 | 4 | 4 | 3 | 5 |
   | 2026-08-14 | wakame | 5-0 | cfd04e24 | 17 | 9 | 0 | 7 | 0 | 0 |
   | 2026-08-15 | rgbandre | 14th Place | 896da179 | 17 | 8 | 3 | 7 | 0 | 8 |
   | 2026-08-15 | wizardpasta | 17th Place | abf22b78 | 17 | 8 | 5 | 0 | 0 | 5 |
   | 2026-08-16 | 2plus2isfive | 10th Place | 6e75d302 | 17 | 8 | 6 | 2 | 0 | 7 |
   | 2026-08-16 | HJ_Kaiser | 32nd Place | effba6bd | 19 | 7 | 4 | 6 | 3 | 8 |
   | 2026-08-18 | clan | 5-0 | 04e0386c | 16 | 8 | 5 | 0 | 0 | 6 |

2. **Wasteland co-occurs with a distinct resource profile in this slice.** The three Wasteland
   rows all use three copies, 19 lands, seven fast-mana cards, four selection cards, and four or
   six named main-value permanents. Every non-Wasteland row uses 16 or 17 lands and seven to nine
   fast-mana cards.

3. **The three Wasteland constructions are not identical.** The 2026-08-12 HJ_Kaiser list has four
   Tamiyo and two Murktide main. Ney Costa Lima has two Tamiyo and two Murktide main. The
   2026-08-16 HJ_Kaiser list has four Tamiyo and two Bilbo main, with two Murktide in the sideboard.

4. **Large main-value counts also occur without land denial.** Four non-Wasteland rows contain
   seven to ten named main-value permanents: thescuba96 (8), Battlegrounds (10), wakame (7), and
   rgbandre (7).

5. **Outcome fields are publication records, not common-denominator match totals.** Six rows say
   `5-0`; the others are event placements. The tables do not supply matchup-conditioned outcomes
   or an observation mechanism that makes League publications comparable to all Challenge
   entries.

## Query anchors

- Date condition: `substr(t.date,1,10) between '2026-08-10' and '2026-08-18'`.
- Deck condition: `decks.archetype='Doomsday'`; all selected rows also contain maindeck Doomsday.
- Card counts: grouped `deck_cards.count` by `board` and `name`; land identity comes from
  `cards.is_land`.

## Revisions

- 2026-08-20 — Aligned the population contract to the outcome extract's exact-archetype August
  10–18 boundary. Replaced the broader-predicate lassi row with SmokyboyJFF and documented the
  excluded conflict-archetype row. Baseline class counts remain A0/B5/C4/D3; under a six-card side
  module threshold the aligned population is A1/B4/C4/D3.
