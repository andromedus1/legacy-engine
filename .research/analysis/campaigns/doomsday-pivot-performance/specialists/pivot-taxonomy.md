---
provenance: agent-synthesis
updated: 2026-08-20
---

# Pivot-intensity taxonomy for exact Doomsday 75s

## Decision frame

The construction evidence separates **where** a second plan lives from **how much game-one
infrastructure it consumes**. {inferred: taxonomy} A sideboard creature package, a maindeck value
engine, and a Wasteland-backed pressure plan should not share one “tempo juke” label: the registered
examples occupy different land, fast-mana, selection, threat, and denial profiles.
[ddp-taxonomy-registry]{1} [ddp-taxonomy-registry]{2} [ddp-taxonomy-registry]{3}

The taxonomy below measures exact 75s and deliberately ignores color identity and published result
when assigning a class. {confidence: construction-only} It is reproducible from card counts, but it
does not estimate matchup win rate or the causal cost of any package. The post-ban source mixes
League publication records with event placements and lacks matchup-conditioned outcomes.
[ddp-taxonomy-postban]{5}

## Inspectable measurements

Six dimensions are retained rather than collapsed into one score:

1. **Mainboard lands**, with Wasteland separately counted as land denial.
2. **Fast acceleration:** Dark Ritual, Lion's Eye Diamond, and Lotus Petal.
3. **Selection/access:** Personal Tutor and Flow State.
4. **Engine bundle:** four Doomsday plus acceleration plus selection/access.
5. **Main-value permanents:** Tamiyo, Bilbo, Teferi, Murktide, and Squelcher.
6. **Sideboard pivot signatures:** named fair/value permanents and mechanically linked alternate
   combo packages, counted separately. [ddp-taxonomy-registry]{1}

{inferred: measurement-boundary} The named-card sets are transparent proxies, not claims that every
card within a set serves the same role. In particular, Teferi, Tamiyo, Murktide, and Squelcher have
different game functions; their common measurement is that each commits a maindeck permanent slot
outside the narrow Doomsday/Oracle engine. The raw columns remain available so later analysis need
not accept the grouping.

## Four mutually exclusive classes

Apply the rules in order; precedence prevents overlapping signatures from being double-counted.

| Priority | Class | Reproducible rule | Interpretation |
|---:|---|---|---|
| 1 | **D — deep denial/tempo hybrid** | at least 3 main Wasteland **and** at least 4 main-value permanents | Game-one denial plus enough permanent pressure/value to make the denial commitment structural. |
| 2 | **C — value-combo overlap** | not D; at least 6 main-value permanents | A substantial game-one permanent engine without Wasteland denial. |
| 3 | **B — sideboard-led pivot** | not C/D; at least 4 side-fair cards **or** at least 2 linked side-alt cards | The measured maindeck value count remains below threshold and the qualifying module is sideboarded; other maindeck interaction or up to two named value permanents may still be present. |
| 4 | **A — focused combo** | none of the above | No measured deep denial, large maindeck value engine, or qualifying sideboard pivot. |

{inferred: thresholds} Four main-value cards is the lower deep-hybrid threshold because the
post-ban Wasteland registrations contain either four or six such permanents, always alongside
three Wasteland and 19 lands. Six is the value-combo threshold because the registered non-Wasteland
middle contains seven or ten main-value permanents, while the ordinary sideboard-led lists contain
zero to two. Four sideboard cards recognizes a compact but intentional module rather than a
singleton hedge. [ddp-taxonomy-registry]{1} [ddp-taxonomy-postban]{2}

## Classification of the fourteen registered candidates

| Class | Candidates | Count | Construction signature |
|---|---|---:|---|
| A — focused combo | BUG Veil/Carpet reconstruction | 1 | 16 lands, 9 acceleration, 6 selection, 19-card engine bundle; no measured main-value or sideboard pivot cards. |
| B — sideboard-led pivot | current Dimir, light green-white, Grixis Squelcher, Personal Tutor turbo, Paradigm Shift, Emrakul/Shelldock, Moonshadow, Cutter/Barrowgoyf, Chancellor, value-threats module | 10 | Main-value count 0–2; side-fair 4–10 or side-alt 2–7. Median construction: 16 lands, 8 acceleration, 5 selection, 17-card engine bundle. |
| C — value-combo overlap | Esper Teferi/Swords; four-color shield | 2 | 7–10 main-value permanents, 17 lands, no Wasteland; engine bundles 13–14. |
| D — deep denial/tempo hybrid | Wasteland/Murktide | 1 | 19 lands, 3 Wasteland, 6 main-value permanents, 7 acceleration, 4 selection, 15-card engine bundle. |

The exact per-list counts support the classifications above. [ddp-taxonomy-registry]{1}

{inferred: comparison} The registered Wasteland/Murktide list is genuinely a deeper game-one
commitment than the creature sideboards on construction alone: it is the sole registered list with
Wasteland, adds three lands relative to the class-B median, carries six main-value permanents, and
has two fewer engine-bundle cards than that median. This does **not** establish that it is slower or
worse in play. [ddp-taxonomy-registry]{1} [ddp-taxonomy-registry]{2}

{inferred: comparison} Esper/Bilbo occupies a distinct middle rather than the same endpoint. Its ten
main-value permanents are a larger permanent commitment than the registered denial list, but it
retains a 17-land, zero-Wasteland mana structure. Its eight-card fair sideboard also means “value
combo” and “post-board juke” overlap; class C wins only because the game-one commitment is the more
decision-relevant distinction. [ddp-taxonomy-registry]{1} [ddp-taxonomy-registry]{3}

{inferred: comparison} The registered Grixis Squelcher construction belongs with sideboard-led pivots,
not deep tempo: only one Squelcher is main, no Wasteland is present, and six fair permanents are in
the sideboard. Red identity alone therefore does not produce a tempo classification.
[ddp-taxonomy-registry]{4}

## Post-ban slice under the same rules

The twelve exact-archetype registrations from August 10–18 classify as **A 0 / B 5 / C 4 / D 3**. The deep
class is the two HJ_Kaiser registrations plus Ney Costa Lima; all use 19 lands, three Wasteland,
seven fast-mana cards, four selection cards, and four or six main-value permanents.
[ddp-taxonomy-postban]{1} [ddp-taxonomy-postban]{2} [ddp-taxonomy-postban]{3}

The four value-combo registrations are thescuba96, Battlegrounds, wakame, and rgbandre, with seven
to ten named main-value permanents and no Wasteland. The five sideboard-led registrations are
SmokyboyJFF, Enrichetta, wizardpasta, 2plus2isfive, and clan. [ddp-taxonomy-postban]{1}

{confidence: descriptive-only} Published outcomes do not cleanly order these classes. Class C
contains three League 5-0 publications and a Challenge 14th; class B contains three League 5-0s plus
Challenge 10th/17th; class D contains Challenge 7th/32nd and a paper 16th. Those
observation types are not common-denominator records, so the absence of a class-D 5-0 is a signal
to test, not a performance estimate. [ddp-taxonomy-postban]{1} [ddp-taxonomy-postban]{5}

## Threshold and overlap stress test

| Alternative | Registered 14 | Post-ban 12 | What moves |
|---|---|---|---|
| Baseline above | A1 / B10 / C2 / D1 | A0 / B5 / C4 / D3 | — |
| Deep requires 6 rather than 4 main-value permanents | unchanged | A0 / B6 / C4 / D2 | Ney Costa Lima moves D→B; both HJ_Kaiser rows remain D. |
| Side module requires 6 rather than 4 cards | A3 / B8 / C2 / D1 | A1 / B4 / C4 / D3 | Registered light-green-white and Moonshadow, plus post-ban wizardpasta, lose B status. |
| Value-combo requires 8 rather than 6 main-value permanents | A2 / B10 / C1 / D1 | A1 / B6 / C2 / D3 | Four-color/wakame (7) lose C; rgbandre (7 with an 8-card side pivot) moves C→B. |

{inferred: robustness} Two structural conclusions survive the threshold variants: the registered
Wasteland list remains the sole deep denial candidate, and the high-density Esper registration
remains value-combo. The unstable boundary is not “tempo versus combo”; it is how compact
four-to-five-card sideboard modules and seven-card maindeck value packages should be named.
[ddp-taxonomy-registry]{1} [ddp-taxonomy-postban]{1}

The raw signatures also expose overlap before precedence. In the registered set, twelve candidates
have a qualifying sideboard-pivot signature, three have at least six main-value permanents, and one
has the Wasteland/deep signature; Esper and Wasteland/Murktide qualify on more than one axis.
{inferred: overlap} Reporting both class and raw dimensions is therefore mandatory for later
performance work. [ddp-taxonomy-registry]{1}

## Implications for the “two weaker strategies” hypothesis

The construction evidence **qualifies** that hypothesis. {inferred: hypothesis-split} It predicts
three different possible taxes that should not be pooled:

- **Side-module tax:** the qualifying second plan is sideboarded, but the observed class does not
  guarantee an otherwise identical or purely combo-focused maindeck.
- **Value-overlap tax:** six or more maindeck permanents reduce the measured engine bundle without
  adding denial lands.
- **Deep-hybrid tax:** land count, denial lands, pressure, and reduced acceleration/access all move
  together.

The registered medians make the distinction inspectable: class B has a 17-card median engine
bundle; class C has a median of thirteen and one-half; class D has 15 plus 19 lands and three Wasteland. {inferred:
construction-cost} Only controlled games can tell whether those slot costs are repaid in hostile
matchups. [ddp-taxonomy-registry]{1}

The post-ban publications actively disconfirm the broad claim that every juke is harmful: five
class-B lists include three published 5-0s, while three class-C lists also published 5-0s despite
large maindeck value packages. {confidence: publication-selected} This does not prove either design
is good; it shows that the available construction/outcome surface cannot support “all-in always
wins” as an absolute. [ddp-taxonomy-postban]{1} [ddp-taxonomy-postban]{5}

## Testing recommendation

{inferred: experimental-design} Prioritize four arms that isolate intensity rather than color:

1. **A focused-combo control:** the BUG reconstruction is the sole registered A construction, but
   its splash is a confound; for a clean experiment, derive or register a no-pivot Dimir 75 with
   comparable mana before calling this the control. [ddp-taxonomy-registry]{1}
2. **B sideboard-led pivot:** the registered high-engine turbo or current Dimir lists provide a low
   measured-main-value construction with a six- or seven-card fair side package. A literal
   sideboard-only treatment requires a new matched-main pair. [ddp-taxonomy-registry]{1}
3. **C value-combo:** the registered high-density Esper/Bilbo list provides the value arm; four-color is a
   useful lower-boundary sensitivity arm. [ddp-taxonomy-registry]{3}
4. **D deep hybrid:** Wasteland/Murktide is the registered denial arm; the Ney Costa Lima exact 75
   is a lower-pressure sensitivity case in the public slice. [ddp-taxonomy-registry]{2}
   [ddp-taxonomy-postban]{3}

Record the raw six dimensions with each list version. Compare game one separately from post-board
games, and stratify by opponent archetype so an aggregate loss cannot conceal a gain against the
specific hostile matchup that justified the pivot. {inferred: measurement-design} For class B,
record exact cards removed and whether the alternate plan was deployed; for C/D, the pivot is
already present in game one, so those fields should not be treated as equivalent.

## Disconfirming analysis

- **Against “tempo is just Murktide or fair creatures.”** Ten registered class-B candidates carry a
  sideboard pivot without Wasteland, while the deep registered list combines 19 lands, three
  Wasteland, six main-value permanents, and a smaller engine bundle. [ddp-taxonomy-registry]{1}
- **Against “all Wasteland builds are the same.”** The post-ban Wasteland rows use Murktide/Tamiyo,
  a lighter 2/2 split, or Bilbo/Tamiyo with Murktide sideboarded. [ddp-taxonomy-postban]{3}
- **Against “Esper is merely a sideboard splash.”** The registered Esper list has ten main-value
  permanents before its eight-card fair sideboard. [ddp-taxonomy-registry]{3}
- **Against “Grixis Squelcher is deep tempo.”** The exact registered list has only one Squelcher
  main and no Wasteland; most measured fair density is sideboarded. [ddp-taxonomy-registry]{4}
- **Against “sideboard-led pivots explain the weak-looking tempo outcomes.”** Sideboard-pivot signatures
  occur across eleven of twelve post-ban lists before precedence, including multiple 5-0
  publications; the distinctive weak-looking group is the three Wasteland constructions, not the
  existence of a creature sideboard. [ddp-taxonomy-postban]{1}
- **Against causal performance language.** Selected undefeated League publication and Challenge/paper placement are
  different observation surfaces, and no matchup-conditioned comparison exists in this source.
  [ddp-taxonomy-postban]{5}

## Contradictions

| Relationship | Position A | Position B |
|---|---|---|
| `qualifies` — apparent tempo penalty | The three post-ban deep-hybrid rows show 7th, 16th, and 32nd rather than a published 5-0. [ddp-taxonomy-postban]{1} | The observation surface mixes placements with selected League records, so those labels do not estimate class win rates. [ddp-taxonomy-postban]{5} |
| `tension` — sideboard pivot versus focused main | Personal Tutor turbo has zero measured main-value permanents and a 17-card engine bundle. [ddp-taxonomy-registry]{1} | It still devotes six sideboard slots to measured fair permanents, so “focused” depends on whether the unit is game one or the full 75. [ddp-taxonomy-registry]{1} |
| `tension` — value commitment versus denial commitment | Esper has ten main-value permanents, more than Wasteland/Murktide's six. [ddp-taxonomy-registry]{1} | Wasteland/Murktide uniquely couples its six permanents to three denial lands, 19 total lands, and seven fast-mana cards. [ddp-taxonomy-registry]{2} |
| `qualifies` — four-color as value-combo | Four-color has seven main-value permanents and therefore clears the baseline C threshold. [ddp-taxonomy-registry]{3} | Raising the threshold to eight moves it to A because its sideboard has no measured fair/alternate module; that boundary is taxonomy-sensitive. [ddp-taxonomy-registry]{1} |

## Revisit if

- Game-level logs bind exact list versions to opponent archetype, pre/post-board state, and combo
  timing.
- A registered pure Dimir 75 removes the sideboard pivot and supplies an unconfounded class-A
  control.
- New permanent engines or denial lands make the named-card proxies incomplete.
- The post-ban slice grows enough to compare repeated exact 75s rather than single registrations.
- Boarding guides establish that nominal sideboard “fair” cards are retained only as interaction
  rather than deployed as an alternate win plan.

## Revisions

- 2026-08-20 — Renamed class B from literal “sideboard-only juke” to “sideboard-led pivot,” aligned
  the post-ban roster to the exact-archetype August 10–18 population, recomputed the six-card-module
  sensitivity to A1/B4/C4/D3, and reserved sideboard-only language for a proposed matched-main
  experiment.
