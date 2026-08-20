# Alternate Doomsday module workbook

These six files are bounded learning instruments for recurring Doomsday modules. They are not
current stock lists, matchup recommendations, or package-controlled performance claims. The
corpus mixes historical registrations, concentrated pilots, and pre-ban chassis; those
qualifications stay attached to each prototype.

## Cutoff and legality

- Read-only evidence cutoff: **2026-08-20** (the local Doomsday corpus runs through 2026-08-18).
- Every emitted file is exactly 60 maindeck cards plus 15 sideboard cards and contains no
  `The Fantasticar` card entry.
- Moonshadow and Cutter are legal reconstructions of Fantasticar-era source lists. Their
  substitutions are explicitly listed below; no reconstructed 75 is an observed registration.
- Published finishes and adoption counts establish registrations or recurrence only. They do not
  establish matchup or package superiority.

## Prototype manifest — authoritative

| id | filename | module | evidence posture | observed source / citation | reconstruction |
| --- | --- | --- | --- | --- | --- |
| `paradigm-shift-oracle` | `paradigm-shift-oracle.txt` | Paradigm Shift plus extra Thassa's Oracle | observed-historical; legal at cutoff | rgbandre, 5-0 Legacy League, 2026-05-11; `.research/attestation/ddv-compare-wide-corpus.md` §9 | none; exact registered 75 |
| `emrakul-shelldock-isle` | `emrakul-shelldock-isle.txt` | Emrakul, the Aeons Torn plus Shelldock Isle | observed-historical; legal at cutoff | Bejamel, 5-0 Legacy League, 2026-05-12; `.research/attestation/ddv-packages-module-census.md` §7 | none; exact registered 75 |
| `moonshadow-creature-switch` | `moonshadow-creature-switch.txt` | four-card Moonshadow creature transformation | inferred-reconstruction; Fantasticar-era source | Lans_NL, 5-0 Legacy League, 2026-06-29; `.research/attestation/ddv-landscape-current-db.md` §7 | main `-4 The Fantasticar +4 Personal Tutor` |
| `cori-steel-cutter-barrowgoyf` | `cori-steel-cutter-barrowgoyf.txt` | Cori-Steel Cutter plus Barrowgoyf red hybrid | inferred-reconstruction; Fantasticar-era source | Eureka22422, 5-0 Legacy League, 2026-07-17; `.research/attestation/ddv-compare-wide-corpus.md` §12 | main `-3 The Fantasticar +3 Personal Tutor` |
| `chancellor-annex-protection` | `chancellor-annex-protection.txt` | four-card Chancellor of the Annex opening-hand tax | observed-historical; concentrated pilot lineage | ragavanejoyer, 25th Legacy Challenge, 2026-06-27; `.research/attestation/ddv-compare-wide-corpus.md` §10 | none; exact registered 75 |
| `value-threats-jace-riddler-sheoldred` | `value-threats-jace-riddler-sheoldred.txt` | Quantum Riddler, Jace, and Sheoldred-class value threats | observed-historical; heterogeneous module | Ich1k4, 25th Melee Legacy event, 2026-08-08; `.research/attestation/ddv-landscape-current-db.md` §8 | none; exact registered 75 |

## Module notes and measurement questions

### Paradigm Shift / Oracle

Observed historical package: four Paradigm Shift and three additional Oracles in the sideboard,
with one Oracle in the main deck. Paradigm Shift replaces the library with the graveyard's cards;
Oracle remains the empty-library payoff. Sequence it as a post-board alternate combo rather than
assuming that four sideboard cards are interchangeable with the primary pile. Measure whether the
alternate line is assembled and resolved, and whether its extra Oracles are useful outside that
line.

### Emrakul / Shelldock Isle

Observed historical package: one Shelldock Isle and one Emrakul in the sideboard. Shelldock's
hidden-card condition and the twenty-or-fewer-card threshold require deliberate library planning;
Emrakul's cast trigger is a payoff, not a generic reanimation target. Measure whether the package
actually reaches a legal Shelldock activation and whether it consumes sideboard slots without
displacing the primary Oracle line.

### Moonshadow creature switch

The selected later anchor had four Moonshadow in the sideboard and a four-Fantasticar/four-Bauble
maindeck. The seven late-June Moonshadow lists in that lineage used the now-banned Fantasticar
chassis. Fantasticar is banned, so this file removes only those four copies and adds four Personal
Tutor as an inferred legal repair. A separate exact legal Enrichetta 2026-01-29 60+15 registration
had four Personal Tutor main and four Moonshadow side; the later anchor remains selected because it
tests the repeated late-June Fantasticar/Bauble lineage and isolates the legality repair rather
than silently substituting an earlier shell. Moonshadow is a combat transformation, not evidence
of a faster Doomsday kill. Measure post-board threat density, graveyard-dependent growth, and how
often the replacement Tutor changes an opening-hand or pile decision.

### Cori-Steel Cutter / Barrowgoyf

The source had four Cutter and four Barrowgoyf in the sideboard, red duals in the maindeck, and
three Fantasticar. This file removes those three banned copies and adds three Personal Tutor; the
red mana and sideboard module remain visible. Cutter's second-spell Monk trigger and Barrowgoyf's
fair pressure are separate roles. Measure whether the red mana tax changes keeps/sequencing and
whether the transformational cards win games or merely occupy slots.

### Chancellor of the Annex

The observed form is four sideboard Chancellor with four Barrowgoyf, attached mostly to one pilot
lineage and without a post-ban continuation. Chancellor's opening-hand reveal taxes the opponent's
first spell; the battlefield copy taxes every opposing spell. Sequence the package around the
opening-hand decision and measure the number of taxed spells, mulligans influenced, and games where
the tax matters—not a headline win rate inferred from placements.

### Recurring value threats

This exact pre-ban-free registration combines one main Quantum Riddler, one sideboard Quantum
Riddler, one sideboard Jace, and two sideboard Sheoldred. These cards recur across heterogeneous
shells and are therefore a module workbook entry, not a new archetype. Measure cards drawn or
discarded to the value permanents, mana spent before Doomsday, and whether the alternate threat
actually closes a game after opponents remove or constrain the primary combo.

## Substitution ledger

| prototype | zone | observed source delta | inferred candidate delta | reason |
| --- | --- | --- | --- | --- |
| `moonshadow-creature-switch` | maindeck | `The Fantasticar -4` | `Personal Tutor +4` | remove banned chassis while retaining a legal Doomsday shell; inferred, not observed |
| `cori-steel-cutter-barrowgoyf` | maindeck | `The Fantasticar -3` | `Personal Tutor +3` | remove banned chassis while retaining a legal Doomsday shell; inferred, not observed |

All other prototypes have an empty substitution ledger: their emitted card tuples match the cited
registration. The exact card files are the import surface; this workbook owns their evidence,
qualification, sequencing caveats, and measurement questions.
