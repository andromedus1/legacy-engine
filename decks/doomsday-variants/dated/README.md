# Dated Doomsday splash candidates

This manifest is authoritative for the two curated candidates in this directory. It keeps
observed registrations, legality, currency, and inferred reconstruction separate. The card files
are ordinary import text; this workbook owns their source and cutoff context and does not claim a
matchup ranking.

## Currency snapshot

- Read-only query date/cutoff: 2026-08-20; no network refresh was run.
- Local status projection: stale at `2026-08-18T13:42:03.720730+00:00`; format-monitor legality
  is pending. The campaign documents that this banner is not terminalized by a manual refresh.
- Database maximum Doomsday tournament date observed: **2026-08-18**.
- Post-2026-08-10 exact green-only BUG signature rows: **0**.
- Post-2026-08-10 exact Hexing Squelcher signature rows: **0**.
- Squelcher rows in the read-only Doomsday query have a latest observed date of **2026-06-27**;
  no Squelcher list appeared after June 27 in the campaign snapshot. (The database query observed
  12 source rows across all stored dates; this is a source-entry count, not independent pilots or
  exact-list count.)
- These checks establish currency labels only. They are not evidence that any card is superior in
  a matchup, and the database is not a test dependency.

## Candidate manifest

| id | filename | status | observed source path and anchor | evidence date / cutoff | legality snapshot | observed package | inferred substitutions | unchanged-card count | bounded learning question |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| `bug-veil-carpet-reconstructed` | `bug-veil-carpet-reconstructed.txt` | `inferred-reconstruction` | `data/cache/Tournaments/MTGO/2026/07/13/legacy-league-2026-07-1310831.json`; [source-direct attestation](../../../.research/attestation/ddv-packages-list-bug-wakame-preban.md), wakame anchor `https://www.mtgo.com/decklist/legacy-league-2026-07-1310831#deck_wakame` | observed 2026-07-13; currency cutoff 2026-08-20 (max Doomsday 2026-08-18) | legal at 2026-08-20 and current | observed BUG shell: main Witherbloom Charm; side 3 Carpet of Flowers, 2 Veil of Summer, 2 Witherbloom Charm | main: `-4 The Fantasticar, +3 Personal Tutor, +1 Thassa's Oracle`; side: `-2 Duress, +2 Abrupt Decay`; both splices are inferred and independent | 69 copy slots from the source 75 | Does the legal Tutor/Oracle repair plus Decay overlay preserve the BUG shell's pile consistency without conflating the two changes? |
| `grixis-squelcher-refresh` | `grixis-squelcher-refresh.txt` | `observed-historical` / `legal-at-cutoff` (not observed-current) | `data/cache/Tournaments/MTGO/2026/05/31/legacy-challenge-32-2026-05-3112843423.json`; [source-direct attestation](../../../.research/attestation/ddv-packages-list-grixis-nevilshute.md), nevilshute anchor `https://www.mtgo.com/decklist/legacy-challenge-32-2026-05-3112843423#deck_nevilshute` | observed 2026-05-31; Squelcher corpus through 2026-06-27; currency cutoff 2026-08-20 (max Doomsday 2026-08-18) | legal at 2026-08-20 and current | observed red/fair package: 1 main + 2 side Hexing Squelcher, 2 side Pyroblast, 1 Molten Collapse, 4 side Barrowgoyf, Badlands + Volcanic Island | none; exact registered 75 preserved card-for-card | 75 copy slots from the source 75 | In a current field test, does persistent Squelcher plus Pyroblast produce a distinct protection outcome worth the dated mana tax? |

## Provenance and interpretation

The BUG source is the July 13 wakame registration and is illegal as printed because it contains four
`The Fantasticar`; the emitted BUG file is therefore not a published or proven 75. Its Personal
Tutor/Oracle module is anchored by the current-corpus Personal Tutor branch in
`.research/attestation/ddv-landscape-current-db.md`, while the two-Abrupt-Decay overlay follows the
campaign's attested BUG lineage. The exact combined splice is inferred.

The Grixis file is nevilshute's exact May 31 registration. “Refresh” means the read-only legality,
adoption, and field-relevance check; it does not turn a dated registration into an observed-current
list or authorize card changes. Published finishes establish registrations, not package-controlled
matchup superiority. The campaign parent is
`.research/analysis/campaigns/doomsday-splash-variants/parent.md`.

## Substitution ledger

| zone | source delta | candidate delta | net |
| --- | --- | --- | ---: |
| maindeck | `The Fantasticar -4` | `Personal Tutor +3`, `Thassa's Oracle +1` | 0 |
| sideboard | `Duress -2` | `Abrupt Decay +2` | 0 |

Both BUG zones remain 60/15 after each transformation. Grixis has no substitution ledger because
its normalized `(zone, card, count)` tuples match the cached source exactly.
