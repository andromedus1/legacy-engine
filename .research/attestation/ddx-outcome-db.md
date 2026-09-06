---
source_handle: ddx-outcome-db
fetched: 2026-08-20
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Refreshed Doomsday outcome, recurrence, and sensitivity extract

## Structural metadata

- The DuckDB file SHA-256 is
  `b984afffd2e1fb3c377f6c1877b1d9c56368e969c61b8e432601fe61bebf4dca`.
- The latest stored tournament date is 2026-08-19. The latest exact-archetype Doomsday entry is
  dated 2026-08-18; therefore the August 19 refresh adds no exact-archetype Doomsday registration.
- Current-population predicate: `decks.archetype = 'Doomsday'` and stored date from 2026-08-10
  through 2026-08-19, inclusive.
- Broader-construction diagnostic: a positive maindeck count of `Doomsday` in the same dates while
  `decks.archetype <> 'Doomsday'`. It is not pooled with the exact-archetype population.
- A League publication uses the stored `5-0` result only as a published result. A non-League
  outcome uses the matching standings row. No League publication is interpreted as an
  unconditional entrant or causal win-rate observation.
- Exact-list identity is SHA-256 over canonical main- and sideboard card/count maps. The
  deterministic reproduction is
  `.research/analysis/campaigns/doomsday-variant-experiments/experiments/outcome/run_outcome_experiments.py`.

## Key passages

### 1. Refreshed exact-archetype census

The current population remains twelve exact registrations, eleven pilot names, eleven tournament
IDs, and twelve distinct exact-list hashes.

| Date | Pilot | Evidence channel | Record | Baseline construction class | Hash prefix |
|---|---|---|---:|---|---|
| Aug 10 | SmokyboyJFF | League publication | 5-0 | B sideboard-led | `5497edf87512` |
| Aug 11 | Enrichetta | League publication | 5-0 | B sideboard-led | `cae8e2467158` |
| Aug 11 | thescuba96 | League publication | 5-0 | C value-combo | `7e6b984d3b82` |
| Aug 12 | HJ_Kaiser | standings | 4-3 | D deep denial | `a3b4be9ef985` |
| Aug 12 | Battlegrounds | League publication | 5-0 | C value-combo | `e0237b790a3c` |
| Aug 13 | Ney Costa Lima | standings | 0-2 | D deep denial | `a92f09d9a909` |
| Aug 14 | wakame | League publication | 5-0 | C value-combo | `4109763e425c` |
| Aug 15 | rgbandre | standings | 4-2 | C value-combo | `f9e5ee05fd7a` |
| Aug 15 | wizardpasta | standings | 3-3 | B sideboard-led | `dbd444ab4327` |
| Aug 16 | 2plus2isfive | standings | 4-2 | B sideboard-led | `02eb0b378efb` |
| Aug 16 | HJ_Kaiser | standings | 3-4 | D deep denial | `9c90fda162da` |
| Aug 18 | clan | League publication | 5-0 | B sideboard-led | `741cdc2621fa` |

Six rows are selected League 5-0 publications and six are standings-backed entrants. The latter
sum to 18-16. Their decision-win percentage is 52.9%; the ordinary 95% Wilson interval over the 34
recorded decisions is 36.7–68.5%. Matches are nested within only five pilots and five events, so
that interval is descriptive and does not repair cluster dependence.

### 2. Current category and class outcomes

The following rows use standings-backed entrants only. Named-card categories overlap; baseline
classes are mutually exclusive.

| Category or class | Entries / pilots | Record | Decision win % | 95% Wilson interval |
|---|---:|---:|---:|---:|
| Personal Tutor main | 2 / 2 | 7-5 | 58.3% | 32.0–80.7% |
| Wasteland main | 3 / 2 | 7-9 | 43.8% | 23.1–66.8% |
| Tamiyo main | 5 / 4 | 15-13 | 53.6% | 35.8–70.5% |
| Bilbo main | 2 / 2 | 7-6 | 53.8% | 29.1–76.8% |
| Teferi main | 1 / 1 | 4-2 | 66.7% | 30.0–90.3% |
| Murktide main | 2 / 2 | 4-5 | 44.4% | 18.9–73.3% |
| Hexing Squelcher main | 0 | — | — | — |
| A focused combo | 0 | — | — | — |
| B sideboard-led | 2 / 2 | 7-5 | 58.3% | 32.0–80.7% |
| C value-combo | 1 / 1 | 4-2 | 66.7% | 30.0–90.3% |
| D deep denial | 3 / 2 | 7-9 | 43.8% | 23.1–66.8% |

Adding the League publications changes B to 22-5 and C to 19-2 while D remains 7-9 because no D
row is a League publication. This is a publication-channel imbalance, not an estimate that B or C
wins more often.

### 3. Event and pilot dependence

For standings-backed Personal Tutor, leaving out either pilot produces decision-win percentages
from 50.0% to 66.7%. For Wasteland, leaving out one pilot produces a range from 0.0% to 50.0%; the
0.0% endpoint is the single 0-2 paper entrant after HJ_Kaiser is removed. The class-D range is the
same. Murktide's leave-one-pilot-out range is 0.0–57.1%. Teferi has one standings-backed entrant,
so no leave-one-pilot or leave-one-event sensitivity can be calculated.

All twelve current exact hashes are unique. HJ_Kaiser is the only repeated current pilot and
supplies both Challenge Wasteland lists. The current data therefore permit list-level
deduplication but not a stable pilot-adjusted or event-adjusted estimate.

### 4. Taxonomy-threshold sensitivity

The baseline current class counts are A0/B5/C4/D3. Requiring six rather than four named main-value
permanents for D changes them to A0/B6/C4/D2. Requiring a six-card rather than four-card side
module changes them to A1/B4/C4/D3. Requiring eight rather than six main-value permanents for C
changes them to A1/B6/C2/D3.

The standings-backed records also move with the labels. Under the baseline, B/C/D are 7-5, 4-2,
and 7-9. With a six-card side threshold, the one A entrant is 3-3 and B is 4-2. With an eight-card
value threshold, C has no standings-backed entrant; B absorbs three entrants and becomes 11-7.

### 5. Back-cast historical windows

Applying the same present-day literal card taxonomy backward gives the following duplicate-
collapsed standings surface:

| Window | All | A focused | B sideboard-led | C value-combo | D deep denial |
|---|---:|---:|---:|---:|---:|
| Jan 1–Jun 30 | 775-569 (57.7%) | 93-85 (52.2%) | 408-278 (59.5%) | 57-51 (52.8%) | 217-155 (58.3%) |
| Jul 1–Aug 9 | 411-285 (59.1%) | 28-21 (57.1%) | 380-260 (59.4%) | 3-3 (50.0%) | 0-1 (0.0%) |
| Aug 10–19 | 18-16 (52.9%) | no entrants | 7-5 (58.3%) | 4-2 (66.7%) | 7-9 (43.8%) |

The corresponding all-class Wilson intervals are 55.0–60.3%, 55.4–62.6%, and 36.7–68.5%.
League publications number 139, 61, and 6 across the same windows and are all stored as 5-0; they
are separated from standings outcomes. The historical taxonomy is a back-cast of current named
card sets across different construction and legality regimes, so its categories are descriptive
rather than a time-series treatment comparison.

### 6. Exact-hash recurrence

Across all exact-archetype Doomsday rows through August 19, the following exact hashes recur:

| Hash prefix | Raw / obvious-duplicate-collapsed entries | Pilots | League publications | Standings record, raw / collapsed |
|---|---:|---:|---:|---:|
| `a3b4be9ef985` | 6 / 5 | 1 | 1 | 25-10 / 21-8 |
| `b950ff11c75c` | 2 / 2 | 1 | 1 | 7-1 / 7-1 |
| `4645f0497d1b` | 4 / 4 | 2 | 2 | 8-4 / 8-4 |
| `02eb0b378efb` | 1 / 1 | 1 | 0 | 4-2 / 4-2 |
| `e0237b790a3c` | 1 / 1 | 1 | 1 | no standings |
| `4109763e425c` | 1 / 1 | 1 | 1 | no standings |
| `dbd444ab4327` | 1 / 1 | 1 | 0 | 3-3 / 3-3 |
| `fbe82f8aef61` | 1 / 1 | 1 | 0 | 3-3 / 3-3 |
| `33f0802a7aa0` | 1 / 1 | 1 | 0 | 3-3 / 3-3 |
| `9b675ea4b051` | 1 / 1 | 1 | 1 | no standings |

The duplicate rule collapses rows sharing stored date, pilot, exact hash, and published result. It
removes one duplicate June 14 HJ_Kaiser `a3b4...` row. The remaining five `a3b4...` entries are all
HJ_Kaiser, so its 21-8 collapsed standings record measures one pilot/list lineage rather than
independent adoption. The two `b950...` entries are also one pilot: a League 5-0 publication and a
7-1 Challenge. The four `4645...` entries use two pilots and combine two League publications with
two Challenge records totaling 8-4.

### 7. Source-normalization mismatch

No stored exact-archetype list has canonical hash `b53aef5db960...`. Its nearest row is clan's
August 18 League publication at card-count distance two: the stored sideboard contains one `Hide
on the Ceiling`, while the compared 75 contains one `Spectral Restitching`. Every other card/count
is identical. Exact recurrence must therefore remain zero unless a documented card-name
normalization equates those names.

### 8. Exact-archetype versus broader construction

The broader maindeck-Doomsday diagnostic adds exactly one current row: lassi, dated August 15, with
three maindeck Doomsday, stored archetype `Conflict(Doomsday,TES)`, rank 14, and standings 0-3. It
is not included in any of the twelve-row current outcome or taxonomy totals.

## Query anchors

- Current exact population: `decks.archetype = 'Doomsday'` and date between `2026-08-10` and
  `2026-08-19`.
- Standings bind on exact tournament ID and player string.
- Obvious duplicate key: stored date, pilot, exact hash, and published result.
- Wilson intervals use wins and losses only; every cited standings row has zero draws.
- Full deterministic outputs are under
  `.research/analysis/campaigns/doomsday-variant-experiments/experiments/outcome/`.

