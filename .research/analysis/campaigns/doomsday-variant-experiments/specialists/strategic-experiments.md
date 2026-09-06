---
title: Doomsday strategic, matchup-economics, and play-style experiments
description: Reproducible break-even scenarios and prospective paired tests for registered Doomsday variants.
type: research
provenance: agent-synthesis
updated: 2026-08-20
decisions:
  - Do not name a universal winner without paired played-game evidence.
  - Treat sideboard-led, maindeck-value, and deep-denial configurations as different interventions.
key_findings:
  - A one-point broad-field cost requires 10.9 points of improvement against an 8.4% hostile pocket.
  - The five-role prospective matrix requires 260 candidate and 260 paired-control matches.
---

# Doomsday strategic experiments

## Boundary and reproducible outputs

The refreshed ranking page covers a transition-stabilized decision field from August 10 through
August 19: 386 observed decks plus an explicit prior contribution. Its five representative rows
used here—Dimir Tempo, Tron, Boros Energy, Azorius Midrange, and Doomsday—sum to `30.0%` of that
decision field.[ddx-strategy-field-ranking]{1}[ddx-strategy-field-ranking]{2}

The registry contains 14 unique 75-card candidates and distinguishes exact registrations from
historical observations and reconstructions.[ddx-strategy-manifest]{1}[ddx-strategy-manifest]{2}
The deterministic experiment at
`experiments/strategy/run_scenarios.py` revalidates the registered parsed-deck hashes, inventories
the lists, extracts those field rows, computes the break-even grid, and emits the prospective test
matrix. `scenario_summary.json` explicitly reports zero played-game results.

Outputs:

- `representative_field.csv` — source-clock and shares for five strategic-role representatives.
- `candidate_inventory.csv` — registered card-package inventory and evidence posture.
- `break_even.csv` — hypothetical hostile-pocket gain required to repay broad-field loss.
- `physical_test_matrix.csv` — exact candidate/control/opponent match allocations.

## Experiment 1: break-even economics

Let `s` be the share of a hostile pocket, `g` the matchup gain there in percentage points, and `c`
the average loss across the rest of the field. The pivot breaks even when
`s × g = (1 − s) × c`, so `g = c × (1 − s) / s`. {inferred: algebraically derives from a
two-stratum weighted average}

| Hostile share | Gain needed for `0.5`-point broad cost | 1-point cost | 2-point cost |
|---:|---:|---:|---:|
| `2.4%` (Doomsday row) | `20.33` | `40.67` | `81.33` |
| `8.4%` (Dimir Tempo row) | `5.45` | `10.90` | `21.81` |
| `10.0%` | `4.5` | `9.0` | `18.0` |
| `20.0%` | `2.0` | `4.0` | `8.0` |
| `30.0%` (all five representatives) | `1.17` | `2.33` | `4.67` |

{inferred: These are hypothetical thresholds, not estimated candidate effects.} They explain why a
narrow juke can look attractive yet fail in aggregate: at an `8.4%` target share, even a modest
one-point loss elsewhere needs nearly eleven points of improvement inside that pocket. Conversely,
a package relevant across several genuinely shared hostile matchups has a much lower repayment
threshold. The five archetype rows are representatives of distinct strategic roles, however, so
their shares must not be pooled into one “same effect” stratum without played evidence.

## Experiment 2: separate the interventions

The registered constructions do not support a single turbo-versus-tempo axis:

| Intervention | Registered examples | What actually changes | Interpretive limit |
|---|---|---|---|
| Focused access | Personal Tutor turbo | Three Personal Tutors in the 60; creatures remain possible after boarding.[ddx-strategy-list-turbo]{1}[ddx-strategy-list-turbo]{2} | Not a literal no-creature 75. |
| Sideboard-led pivot | Current Dimir | Two Tutor/two Tamiyo main; seven sideboard creatures.[ddx-strategy-list-dimir]{1}[ddx-strategy-list-dimir]{2} | Not a pure sideboard-only causal treatment because the 60 differs from turbo. |
| Shield splash | Light green-white / reconstructed BUG | Veil/Carpet packages and splash mana; the exact light list also crosses white/green cards between main and side.[ddx-strategy-list-green]{1}[ddx-strategy-list-green]{2}[ddx-strategy-list-bug]{1}[ddx-strategy-list-bug]{2} | BUG is reconstructed, and Carpet is conditional on opposing Islands.[ddx-strategy-card-rules]{2} |
| Maindeck value | Esper / four-color | Esper has Bilbo, Tamiyo, and Teferi main; four-color has Tamiyo/Teferi/Veil main plus Carpet/Swords side.[ddx-strategy-list-esper]{1}[ddx-strategy-list-esper]{2}[ddx-strategy-list-four-color]{1}[ddx-strategy-list-four-color]{2} | Changes game-one sequencing and mana, not merely boarding. |
| Compact protection/value | Historical Grixis | One Squelcher main, two more plus creatures side.[ddx-strategy-list-grixis]{1}[ddx-strategy-list-grixis]{2} | Historical at the cutoff, not evidence of current performance. |
| Deep denial-tempo | Wasteland/Murktide | Three Wasteland and two Murktide are already in the 60, with six sideboard creatures.[ddx-strategy-list-wasteland]{1}[ddx-strategy-list-wasteland]{2} | A different game-one resource plan, not a “juke intensity” increment. |

This separation matters because Personal Tutor directly increases sorcery access, while Wasteland
trades a land to attack a nonbasic, Veil answers a bounded blue/black interaction class, Teferi
changes opponent casting timing, and Squelcher protects the pilot's spells while presenting a
creature.[ddx-strategy-card-rules]{1}[ddx-strategy-card-rules]{2}[ddx-strategy-card-rules]{3}[ddx-strategy-card-rules]{4}[ddx-strategy-card-rules]{5}
{inferred: Those rules create different resource and sequencing surfaces; they do not establish
matchup gains.}

## Play-style portraits

These are construction-derived portraits, not measurements of pilot skill, cognitive load, or win
rate.

| Style | Sequencing posture | Resource axis | Mulligan emphasis | Vulnerability profile | Boarding implication |
|---|---|---|---|---|---|
| Focused access | Preserve a compact path to the sorcery and the draw-through; choose when to expose the top-deck Tutor line. | Cards/mana assembled toward Doomsday. | Access plus mana plus protection. | A narrow plan can make opposing combo-specific interaction live. | Add only the threats/interactions needed for the matchup; do not call the registered 75 “no-juke.” |
| Sideboard-led Dimir | Game one remains access/disruption weighted; post-board hands can threaten combo or deploy a creature clock. | Conversion of sideboard slots into a second pressure axis. | Post-board hand must function on at least one axis without stranded halves. | Role ambiguity can become dilution when neither axis is sufficiently supported. | Record actual alternate-plan deployment and cards in/out, as the protocol requires.[ddx-strategy-playtest-protocol]{4} |
| Green shield | Time Veil around blue/black interaction and Carpet around an opponent controlling Islands.[ddx-strategy-card-rules]{2} | Colored splash mana versus conditional protection/mana. | Functional green source plus an opponent-dependent payoff, not payoff alone. | Splash-color exposure and dead conditional cards outside their target class. | Test blue permission/discard separately from nonblue lock and creature fields. |
| Esper/four-color value | Decide whether to invest in attack/planeswalker value before committing the combo; Teferi can constrain response timing.[ddx-strategy-card-rules]{3}[ddx-strategy-card-rules]{6} | Board development, graveyard reuse, and stack insulation alongside combo mana. | Functional multicolor mana plus an internally coherent early action. | More non-combo permanents and colors can tax speed/consistency; magnitude is unmeasured. | Keep removal and protection endpoints separate; Swords addresses creatures, not stack interaction.[ddx-strategy-card-rules]{3} |
| Grixis Squelcher | Resolve/protect Squelcher, then exploit its counter-protection, or remain on the combo line.[ddx-strategy-card-rules]{5} | A red creature as protection and clock. | Red access plus a hand that benefits from the protection window. | Creature removal can answer the enabling permanent; current-field efficacy is unsupported. | Treat as an experimental historical arm, not a current recommendation. |
| Deep denial-tempo | Allocate land drops between colored combo mana and Wasteland activation while presenting Tamiyo/Murktide pressure. | Opponent nonbasic mana and both graveyards, alongside Doomsday resources.[ddx-strategy-card-rules]{4}[ddx-strategy-list-wasteland]{1} | Functional colored mana plus pressure/interaction; Wasteland alone is not combo access. | Lower Tutor density and self-sacrificed lands may conflict with combo assembly; size of cost is unmeasured. | Preserve the denial/clock package when it attacks the opponent's actual mana plan; otherwise test trimming it rather than assuming transformation. |

{inferred: Relative decision density increases when a hand supports two live plans because the pilot
must allocate mana/cards between them.} This is a statement about available branches in the list,
not a claim that one style is harder, more skill-intensive, or better for a particular person.

## Experiment 3: prospective paired physical matrix

The protocol requires a candidate and control to face the same registered opponent list/version,
balances play/draw and test order, and withholds rankings below 20 completed matches per list.
[ddx-strategy-playtest-protocol]{1}[ddx-strategy-playtest-protocol]{2}[ddx-strategy-playtest-protocol]{3}

`physical_test_matrix.csv` assigns every non-control candidate to five opponent roles at four
completed matches apiece:

| Opponent | Decision share | Role | Matches per candidate | Paired control matches |
|---|---:|---|---:|---:|
| Dimir Tempo | `8.4%` | disrupt-pressure | 4 | 4 |
| Tron | `7.0%` | go-over | 4 | 4 |
| Boros Energy | `6.4%` | go-wide | 4 | 4 |
| Azorius Midrange | `5.8%` | lock-outlast | 4 | 4 |
| Doomsday | `2.4%` | go-off | 4 | 4 |

Across 13 non-control candidates this totals 260 candidate matches plus 260 paired-control
matches. [ddx-strategy-results]{1} Each opponent list/version must be registered before its block; this design allocates
matches but does not silently choose an opponent 75. {inferred: The allocation reaches the
protocol's 20-match candidate threshold while spreading first-pass evidence across five strategic
roles.} It is a screening design: candidate-level totals mix matchups, while the four-match cells
remain thin and descriptive.

A literal sideboard-only causal experiment is still absent. To isolate that effect, register a
second Dimir 75 with the **identical 60 and main-deck hash** as the current Dimir control but a
no-creature, combo/protection sideboard; then pair it against the creature-transform sideboard under
the same five opponent versions. Until that exact 15 is registered, turbo versus current Dimir
cannot identify “sideboard juke” as the cause because their maindecks differ.

## Conditional recommendations

- **Low concentration of a specifically targetable hostile pocket:** begin with focused access.
  {inferred: A narrow `4–8.4%` pocket demands `10.9–24` points of improvement to repay a one-point
  broad-field cost.} This is a testing priority, not a win-rate claim.
- **Blue/black interaction and Islands are prevalent:** prioritize light green-white as the exact
  shield test, with reconstructed BUG as a secondary mechanism check. Veil and Carpet have bounded
  rules targets, so aggregate all “interactive” decks only after the log shows shared relevance.
  [ddx-strategy-card-rules]{2}
- **Creature boards plus permission are both common:** test Esper before four-color if minimizing
  the number of splash mechanisms is valuable; test four-color when the combined Teferi/Veil/Carpet/
  Swords shield is the intervention of interest. {inferred: Neither is superior absent paired
  results; the latter simply bundles more mechanisms and therefore more attribution problems.}
- **Nonbasic-dependent, slower opponents dominate the expected room:** treat Wasteland/Murktide as
  a distinct denial-tempo deck and test it on that premise, not as a generic transformational
  upgrade.[ddx-strategy-card-rules]{4}[ddx-strategy-list-wasteland]{1}
- **Interest in Squelcher protection:** keep Grixis in the experimental queue, but its historical
  status prevents a current-performance recommendation.[ddx-strategy-list-grixis]{1}

There is no source-grounded universal winner. The selection rule is conditional: choose the
smallest intervention whose *measured paired gain* clears the break-even threshold for the expected
field, and reject a pivot whose gains occur outside the interaction class it was built to target.
{inferred: decision rule composed from the weighted break-even model and protocol}

## Disconfirming analysis

- The refreshed field source itself disconfirms proof-grade use of its headline ranking: it labels
  the practical call lower-confidence because supported rows are not proof-grade grounded.
  [ddx-strategy-field-ranking]{3} The field shares are scenario weights, not proof of stable future
  attendance.
- The focused-access list disconfirms a clean “turbo means no fair plan” binary because its
  sideboard includes creatures.[ddx-strategy-list-turbo]{2}
- The current Dimir list disconfirms a clean sideboard-only causal contrast with turbo because its
  maindeck contains a different Tutor/Tamiyo mix.[ddx-strategy-list-dimir]{1}
- The four-color list disconfirms treating every pivot as tempo: it contains no counted sideboard
  creature pivot and instead layers protection/removal mechanisms.[ddx-strategy-list-four-color]{2}
- The registry disconfirms treating all 14 candidates as equally current: several are historical or
  reconstructed.[ddx-strategy-manifest]{2}
- No played results exist in this experiment. Accordingly, construction-derived vulnerabilities
  and recommendations remain marked inference rather than being backfilled with matchup claims.

## Contradictions

No two fetched sources make incompatible claims within a shared measurement frame. There are two
important evidentiary tensions:

| Source position A | Relationship | Source position B |
|---|---|---|
| The registry makes 14 artifacts reproducibly testable.[ddx-strategy-manifest]{1}[ddx-strategy-manifest]{3} | `qualifies` | Historical/reconstructed posture prevents treating all 14 as current observed strategies.[ddx-strategy-manifest]{2} |
| The ranking page supplies refreshed field weights.[ddx-strategy-field-ranking]{1}[ddx-strategy-field-ranking]{2} | `qualifies` | The same page says practical ranks lack proof-grade grounding.[ddx-strategy-field-ranking]{3} |

## Revisit if

- Any candidate or opponent deck hash/version changes.
- The decision field moves enough to change hostile-pocket shares or the August 10 transition model.
- The paired log reaches 20 completed matches per candidate, or supplies enough per-matchup pairs to
  replace hypothetical break-even gains with observed descriptive deltas.
- A literal identical-main/no-juke Dimir 75 is registered, enabling the sideboard-only causal
  contrast.
- Multiple pilots produce enough balanced blocks to examine pilot sensitivity without exposing
  identities or presenting human-skill claims as facts.
