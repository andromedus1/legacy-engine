---
source_handle: ddp-outcome-current-corpus
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Post-ban Doomsday outcome and coverage extract

## Structural metadata

- DuckDB tables read: `tournaments`, `decks`, `deck_cards`, `standings`, and `rounds`.
- Snapshot cutoff: 2026-08-20. The latest Doomsday row in the queried post-ban slice is dated
  2026-08-18.
- Population predicate: `decks.archetype = 'Doomsday'` and stored tournament date on or after
  2026-08-10.
- League identification: `tournaments.name = 'Legacy League'`.
- Exact-list identity: SHA-256 over newline-joined, lexically ordered `board|card name|count` rows
  for each `(tournament_id, deck_idx)`.
- Chassis membership is overlapping and based on a positive main-deck count of the named card:
  `Personal Tutor`, `Wasteland`, `Tamiyo, Inquisitive Student`, `Bilbo, Thief in the Night`,
  `Teferi, Time Raveler`, or `Murktide Regent`.
- Exclusive color-package labels use occurrence anywhere in the 75. Green signals are Veil of
  Summer, Carpet of Flowers, Abrupt Decay, Witherbloom Charm/Command, Boseiju, Tropical Island,
  or Bayou. White signals are Swords to Plowshares, Teferi, Tundra, Scrubland, Voice of Victory,
  Portable Hole, or Prismatic Ending. Red signals are Pyroblast, Red Elemental Blast, Badlands,
  or Volcanic Island.
- A published record is the deck's `result` field for a League row and the matching `standings`
  wins/losses/draws for a non-League row. This extract does not treat either as a causal estimate.

## Attested extracts

### 1. Exact-list outcome surface

The slice contains 12 deck entries, 11 pilot names, 11 tournament source IDs, and 12 distinct
exact-list hashes. HJ_Kaiser is the sole repeated pilot. The August 15 Challenge is the sole source
containing two of the 12 entries. No exact list repeats.

| Date | Event | Pilot | Published / standings record | Exact-list SHA-256 | Overlapping chassis | Exclusive color package |
|---|---|---|---:|---|---|---|
| 2026-08-10 | Legacy League | SmokyboyJFF | 5-0 | `673815364b69761c36b0cfb0908463f9fa96b618512fd6d5518daaf7f20e36af` | Personal Tutor | UB |
| 2026-08-11 | Legacy League | Enrichetta | 5-0 | `ba8a2a6c97703472c81304a886cf5d8e814a4df2ef8dd1546e2cf636cca90552` | Personal Tutor | white-only |
| 2026-08-11 | Legacy League | thescuba96 | 5-0 | `108c7180cbe579e76beece8e30cf73962a8b43926ce84361ee6adb55478e45b8` | Tamiyo; Bilbo; Teferi | white-only |
| 2026-08-12 | Legacy League | Battlegrounds | 5-0 | `57f307e914dafdb8a11d8d7aa10cd45b516a996e6477cd9bd0b7ddb4f048b6c1` | Tamiyo; Bilbo; Teferi | white-only |
| 2026-08-12 | Legacy Challenge 32 | HJ_Kaiser | 4-3 | `69cb933ed54ad28a52b145cb199c894b9f173a5bebef7b97a6906b942a716ed4` | Wasteland; Tamiyo; main Murktide | UB |
| 2026-08-13 | Mont Weekly Legacy | Ney Costa Lima | 0-2 | `f36e1d8c57dced24466a43f18dc0b7fdf00c76aea0cee7474fd48e61ba444431` | Wasteland; Tamiyo; main Murktide | UB |
| 2026-08-14 | Legacy League | wakame | 5-0 | `2e1297d8efb4d22e6d3591a264ef9728682ee5c4c5765d9e54e4ed7f6b767961` | Tamiyo; Teferi | green-white |
| 2026-08-15 | Legacy Challenge 32 | rgbandre | 4-2 | `884929addf0cc013b1d520100d704a4a3e20889ab4b383c7915a1a84ee213798` | Tamiyo; Bilbo; Teferi | white-only |
| 2026-08-15 | Legacy Challenge 32 | wizardpasta | 3-3 | `ac2c52bb6da12c6bc5985fd0fb9f81d95a7a0ff11059321895fa2c99c794c400` | Personal Tutor | green-white |
| 2026-08-16 | Legacy Challenge 32 | 2plus2isfive | 4-2 | `70eb54981e4b5072680a53f96bf0549f773471b6ebb4c21247234ca90f745531` | Personal Tutor; Tamiyo | UB |
| 2026-08-16 | Legacy Challenge 32 | HJ_Kaiser | 3-4 | `ad6683e268116c1a4f822ac1a7f783666a3e889048d9302fa1620ef498b72e8d` | Wasteland; Tamiyo; Bilbo | UB |
| 2026-08-18 | Legacy League | clan | 5-0 | `599c70cbb1a68ea57f16c41be625f892443b4650b563d0d0c200a5e066926bdd` | Personal Tutor | UB |

Murktide occurs somewhere in more lists than the two marked `main Murktide`; only main-deck
Murktide defines that chassis column. Sideboard creature packages therefore do not cause a list to
enter that chassis.

### 2. Publication mechanism and evidence coverage

Six entries are League publications. Every one has `result = '5-0'`; none has a matching
`standings` row, and their tournament IDs have zero `standings` and zero `rounds` rows. The database
therefore contains no failed-League denominator or matchup rows for this slice.

The other six entries have matching standings rows. Five are from four 32-player MTGO Challenges
and one is from a 17-player paper event. Their standings records are HJ_Kaiser 4-3, Ney Costa Lima
0-2, rgbandre 4-2, wizardpasta 3-3, 2plus2isfive 4-2, and HJ_Kaiser 3-4.

The four Challenge tournament IDs each have 32 standings rows but only seven `rounds` rows. Those
round rows are the top-eight elimination matches rather than Swiss coverage. Among the five
Challenge Doomsday entries, only seventh-place HJ_Kaiser appears in a round row, once. The paper
event has 17 standings rows and 33 round rows; Ney Costa Lima appears in two round rows. Thus all
six non-League entries have standings-derived records, while only two of those six pilots and three
of their matches appear in `rounds`.

### 3. Aggregate category surface

These categories overlap. Records are descriptive sums of the exact-list rows above.

| Category | Entries | Pilot names | All published records | League-excluded records | MTGO-Challenge-only records |
|---|---:|---:|---:|---:|---:|
| Personal Tutor main | 5 | 5 | 22-5 | 7-5 | 7-5 |
| Wasteland main | 3 | 2 | 7-9 | 7-9 | 7-7 |
| Tamiyo main | 8 | 7 | 30-13 | 15-13 | 15-11 |
| Bilbo main | 4 | 4 | 17-6 | 7-6 | 7-6 |
| Teferi main | 4 | 4 | 19-2 | 4-2 | 4-2 |
| Murktide main | 2 | 2 | 4-5 | 4-5 | 4-3 |
| UB color package | 6 | 5 | 21-11 | 11-11 | 11-9 |
| White-only color package | 4 | 4 | 19-2 | 4-2 | 4-2 |
| Green-white color package | 2 | 2 | 8-3 | 3-3 | 3-3 |

There are no pure-green or red-package entries in this post-ban slice. The category sums are not
mutually exclusive: for example, 2plus2isfive is both Personal Tutor and Tamiyo, while thescuba96,
Battlegrounds, and rgbandre are simultaneously Tamiyo, Bilbo, and Teferi.

### 4. Personal Tutor versus Wasteland sensitivity

Across all 12 publications, Personal Tutor rows sum to 22-5 (81.5% of recorded decisions won) and
Wasteland rows sum to 7-9 (43.8%), a descriptive difference of 37.7 percentage points. Three of the
five Personal Tutor rows are selected League 5-0 publications; none of the Wasteland rows is a
League publication.

Removing all League rows leaves two Personal Tutor lists at 7-5 (58.3%) and all three Wasteland
lists at 7-9 (43.8%), a descriptive difference of 14.6 percentage points. Restricting further to
MTGO Challenges leaves the same two Personal Tutor lists at 7-5 and two Wasteland entries at 7-7
(50.0%), a difference of 8.3 percentage points.

All five Personal Tutor rows are different pilots and exact lists. The three Wasteland rows are
different exact lists but only two pilot names: HJ_Kaiser's two lists pool to 7-7, while Ney Costa
Lima's paper-event list is 0-2. In the Challenge-only restriction, the Wasteland result is entirely
one pilot's two exact lists. There are too few clusters for an inferential pilot- or list-cluster
estimate.

### 5. Source, list, pilot, and event dependence

- Exact-list deduplication does not remove a post-ban row because all 12 hashes differ.
- Pilot deduplication would require choosing between HJ_Kaiser's 4-3 and 3-4 Wasteland lists; the
  source does not provide a principled reason to retain one and discard the other.
- Event clustering joins rgbandre's white-only value list and wizardpasta's green-white Personal
  Tutor list inside the same August 15 field. Their results are not independent observations of
  the event environment, although their 75s and pilots differ.
- The League rows are independent source IDs and pilot names in this slice, but all are conditioned
  on the same undefeated-publication mechanism.
- The non-League standings records provide observed denominators for those published entrants, not
  the population of all Doomsday decks played at those events; only decklists present in the
  database can enter this extract.

### 6. Historical comparability boundary

The same database contains older pure-BUG, Grixis Squelcher, Moonshadow, Cutter, Chancellor, and
other alternate configurations, but they occupy earlier card-legality and adoption windows. Their
published rows mix selected League 5-0s, standings-backed events, repeated pilots, repeated exact
lists, and known duplicate/date-quality defects. They are usable as evidence that configurations
were registered and achieved particular finishes, but not as a performance baseline commensurate
with the 12-row post-ban slice without a separately defined era/event restriction.

## Query notes

The extract joined `decks` to `tournaments`, then left-joined `standings` on exact tournament ID and
player string. Card memberships were read from `deck_cards` for each exact `(tournament_id,
deck_idx)`. Round coverage counted a match when the deck pilot's exact player string appeared as
`player1` or `player2`. Percentages use wins divided by wins plus losses; all attested rows have zero
draws.

## Revisions

- 2026-08-20 — Corrected SmokyboyJFF and clan chassis labels: each has Tamiyo only in the
  sideboard, so neither belongs to the maindeck-Tamiyo category. The aggregate Tamiyo count and all
  Tutor/Wasteland sensitivity totals already used the correct maindeck predicate.
