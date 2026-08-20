---
source_handle: ddp-taxonomy-registry
fetched: 2026-08-20
source_path: decks/doomsday-variants/manifest.json
provenance: source-direct
substrate_confidence: source-direct
---

# Registered Doomsday 75s: construction measurements

## Source structure

The manifest declares fourteen unique candidates and a path for each exact 75. Each linked text
file was read directly. Land counts were resolved against `cards.is_land` in the local card
dimension. The remaining columns are literal card-count sums:

- `acc`: Dark Ritual, Lion's Eye Diamond, and Lotus Petal;
- `select`: Personal Tutor and Flow State;
- `main-value`: Tamiyo, Inquisitive Student; Bilbo, Thief in the Night; Teferi, Time Raveler;
  Murktide Regent; and Hexing Squelcher;
- `denial-land`: Wasteland;
- `side-fair`: Barrowgoyf, Dauthi Voidwalker, Murktide Regent, Orcish Bowmasters, Tamiyo,
  Moonshadow, Cori-Steel Cutter, Chancellor of the Annex, Sheoldred, Quantum Riddler, Brazen
  Borrower, Voice of Victory, and Containment Priest;
- `side-alt`: Paradigm Shift, Thassa's Oracle, Emrakul, and Shelldock Isle.

These are construction counts, not card-quality or performance scores.

## Key passages

1. **Fourteen-list measurements.** `engine` is `4 Doomsday + acc + select`.

   | candidate | lands | acc | select | engine | main-value | denial-land | side-fair | side-alt |
   |---|---:|---:|---:|---:|---:|---:|---:|---:|
   | current-dimir-creature-transform | 17 | 8 | 6 | 18 | 2 | 0 | 7 | 0 |
   | current-esper-teferi-swords | 17 | 7 | 3 | 14 | 10 | 0 | 8 | 0 |
   | current-light-green-white | 17 | 8 | 5 | 17 | 0 | 0 | 5 | 0 |
   | current-four-color-shield | 17 | 9 | 0 | 13 | 7 | 0 | 0 | 0 |
   | bug-veil-carpet-reconstructed | 16 | 9 | 6 | 19 | 0 | 0 | 0 | 0 |
   | grixis-squelcher-refresh | 17 | 8 | 4 | 16 | 1 | 0 | 6 | 0 |
   | personal-tutor-turbo | 16 | 8 | 5 | 17 | 0 | 0 | 6 | 0 |
   | wasteland-murktide-tempo | 19 | 7 | 4 | 15 | 6 | 3 | 6 | 0 |
   | paradigm-shift-oracle | 16 | 9 | 5 | 18 | 0 | 0 | 0 | 7 |
   | emrakul-shelldock-isle | 16 | 8 | 3 | 15 | 0 | 0 | 0 | 2 |
   | moonshadow-creature-switch | 16 | 9 | 4 | 17 | 0 | 0 | 4 | 0 |
   | cori-steel-cutter-barrowgoyf | 16 | 9 | 6 | 19 | 0 | 0 | 10 | 0 |
   | chancellor-annex-protection | 16 | 8 | 5 | 17 | 0 | 0 | 9 | 0 |
   | value-threats-jace-riddler-sheoldred | 16 | 9 | 4 | 17 | 0 | 0 | 8 | 0 |

2. **The registered Wasteland construction is singular on multiple axes.** It is the only one of
   the fourteen with Wasteland; it has three. It also has 19 lands, seven fast-mana cards, six
   named main-value permanents (four Tamiyo and two Murktide), and six side-fair cards.

3. **Esper and four-color occupy the large main-value band without Wasteland.** The Esper exact 75
   has ten named main-value permanents: four Tamiyo, four Bilbo, and two Teferi. The four-color
   shield has seven: four Tamiyo and three Teferi. Their engine sums are fourteen and thirteen,
   respectively.

4. **The registered Grixis list is not a mainboard tempo-density peer of the Wasteland list.** It
   has one named main-value permanent (one Hexing Squelcher), no Wasteland, 17 lands, and an engine
   sum of sixteen. Its sideboard has six named fair cards: four Barrowgoyf, one Brazen Borrower,
   and one Sheoldred.

5. **Sideboard modules vary without requiring mainboard fair density.** The BUG reconstruction has
   zero named main-value, side-fair, or side-alt cards. Personal Tutor turbo has zero main-value
   and six side-fair cards. Paradigm Shift has seven side-alt cards; Emrakul/Shelldock has two.

## Source paths

The exact paths are the fourteen `candidates[].path` values in the manifest. The manifest's single
artifact alias is excluded because it resolves to the same canonical 75 as
`current-esper-teferi-swords`.
