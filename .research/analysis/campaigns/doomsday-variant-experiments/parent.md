---
title: Doomsday field guide — variant experiments and decision synthesis
description: Evidence-bounded synthesis of observed outcomes, deterministic construction experiments, scenario economics, and the next paired tests for Legacy Doomsday variants.
type: research
kind: research
summary: Current Dimir is the live control, Personal Tutor is the focused-access benchmark, and splash or tempo packages should be chosen only when their measured paired gain clears their metagame cost.
updated: 2026-08-20
provenance: agent-synthesis
decisions:
  - Rank variants by testing and building priority, not unsupported power.
  - Keep observed outcomes, deterministic draw/construction results, inferred scenarios, and prospective played tests separate.
  - Use the smallest intervention whose eventual paired gain clears its field-weighted break-even threshold.
key_findings:
  - The refreshed current standings surface is too small and dependent to identify a best-performing variant.
  - Personal Tutor and reconstructed BUG lead the principal arms on the deterministic access-plus-black-or-Petal opening measure at 53.906 percent.
  - A one-point broad-field cost requires 10.90 points of improvement in an 8.4 percent hostile pocket.
  - The registered screening matrix has zero played-game results and requires 260 candidate plus 260 paired-control matches.
---

# Doomsday field guide: what to build, what to test, and why

## Read this first

There is no measured universal winner. The refreshed current window contains twelve exact-archetype
registrations, but only six are standings-backed; those six total 18-16 across five pilots and five
events. Current B sideboard-led, C value-combo, and D deep-denial records are 7-5, 4-2, and 7-9,
with wide, overlapping Wilson intervals. League 5-0 publications strongly favor B and C in the
published surface and have no failed-run denominator. [ddx-outcome-db]{1}[ddx-outcome-db]{2}

{inferred: decision synthesis} The defensible answer is therefore a **conditional build and testing
hierarchy**, not a power ranking:

1. **Current Dimir is the live control.** It has an exact current 75, a standings-backed 4-2
   registration, a `49.320%` raw access-plus-black-or-Petal opening event, and a real post-board
   creature switch. It is the deck against which every larger intervention should earn its slots.
   [ddx-outcome-db]{6}[ddx-construction-results]{2}
   [ddx-strategy-list-dimir]{1}[ddx-strategy-list-dimir]{2}
2. **Personal Tutor turbo is the focused-access benchmark.** Its registered 60 leads the registered
   principal constructions in access density, but the stored current publication differs by one
   sideboard card, so exact recurrence is zero rather than a hidden 5-0 claim. [ddx-construction-results]{2}
   [ddx-outcome-db]{7}
3. **Light green-white is the first shield-splash test.** It is exact/current, changes fewer
   mechanisms than four-color, retains five access and 15 selection cards, and has a 3-3 current
   Challenge observation. Its Veil/Carpet/Swords package must earn the color and conditional-card
   costs in paired play. [ddx-construction-results]{2}[ddx-outcome-db]{6}
4. **Wasteland/Murktide is the denial-tempo test, not an upgraded juke.** The exact list has a
   duplicate-collapsed 21-8 standings lineage plus one League publication, but all five collapsed
   registrations are one pilot. Its 19 lands increase two-land raw sevens while its four access
   cards and seven acceleration cards make a different game-one resource plan. [ddx-outcome-db]{6}
   [ddx-construction-results]{2}
5. **Esper is the white value test.** Its exact 75 presents Bilbo/Tamiyo/Teferi before sideboarding
   and eight sideboard creatures plus removal afterward. Its only exact recurrence is a selected
   League publication, so the attractive mechanism has no standings denominator yet.
   [ddx-strategy-list-esper]{1}[ddx-strategy-list-esper]{2}[ddx-outcome-db]{6}
6. **Grixis Squelcher is a current-regime replication target.** Its historical exact list has a
   7-1 Challenge and one League publication, both from one pilot. Squelcher is a persistent
   protection-and-clock experiment; it is not current performance evidence. [ddx-outcome-db]{6}
   [ddx-strategy-card-rules]{5}[ddx-strategy-list-grixis]{1}

Reconstructed BUG, four-color, Paradigm Shift, and the remaining alternate modules stay in the
queue for mechanism or branch testing, not as recommended winners. The registry distinguishes
exact/current, exact/published, historical, and reconstructed evidence postures and supplies no
matchup results itself. [ddx-construction-registry]{2}[ddx-outcome-manifest]{2}

## Evidence legend

| Mark | Evidence class | What it can establish |
|---|---|---|
| **OBSERVED** | Stored tournament or standings result | A record for the named entrant/list, with publication and dependence caveats. |
| **DETERMINISTIC** | Exact registered-list parsing or unordered seven-card calculation | Composition and raw opening frequencies under disclosed assumptions; never game speed or win rate. |
| **INFERRED** | Cross-source interpretation or algebraic scenario | A decision hypothesis whose assumptions remain visible. |
| **PROSPECTIVE** | Preregistered paired-play design | What future physical matches can identify; this campaign recorded zero played games. |

## At-a-glance comparison

The opening event below is “at least one access card and at least one fetch-enabled black land
source or Lotus Petal” in an unordered seven-card hand, without mulligans, sequencing, piles, or an
opponent. Protection/value labels use a disclosed card-name role map. [ddx-construction-results]{1}
{inferred: qualitative comparison} The play-pattern, upside, and cost cells interpret registered
card composition and rules; they are not directly observed pilot experience or matchup effects.

| Version | Evidence posture | Play pattern | Access / selection | Key construction signal | Main upside | Principal cost |
|---|---|---|---:|---|---|---|
| Current Dimir transform | exact current; `4-2` recurrence | Combo-disruption G1; creature pressure available post-board | `6 / 14` | **`49.32%`** access + B/Petal; `7` side-pivot cards | Flexible reference with native Dimir mana | Post-board hands can split across plans. [ddx-construction-results]{2}[ddx-outcome-db]{6} |
| Personal Tutor turbo | exact published; current near-match only | Find and protect Doomsday with minimal G1 fair material | **`7 / 13`** | **`53.906%`** access + B/Petal | Clean access benchmark | Tutor telegraphs the top card; narrow posture may leave opposing hate live. [ddx-construction-results]{2}[ddx-outcome-db]{7} |
| Light green-white | exact current; `3-3` recurrence | Compact combo with bounded green shield and white removal | `5 / 15` | `41.516%` access + B/Petal; B13/W10/G9 sources | Tests Veil/Carpet without the full four-color bundle | Conditional cards and splash allocation. [ddx-construction-results]{2}[ddx-outcome-db]{6} |
| Esper Teferi/Swords | exact current; League-only recurrence | Develop value/Teferi, then combo or transform | `4 / 13` | `34.855%` access + B/Petal; `10` main value/tempo | Board presence, response-window control, creature removal | Lower raw access and multicolor sequencing. [ddx-construction-results]{2}[ddx-outcome-db]{6} |
| Four-color shield | exact current; League-only recurrence | Layer Teferi, Veil, Carpet, and removal around combo | `4 / 10` | **`14 protection`**; `34.855%` access + B/Petal; B12/W10/G10 | Broad mechanism coverage | Attribution, color pressure, trailing principal compound access/selection/resource event. [ddx-construction-results]{2}[ddx-outcome-db]{6} |
| BUG Veil/Carpet | reconstructed | Access-first combo with conditional green protection/mana | **`7 / 13`** | **`53.906%`** access + B/Petal; `9` acceleration | Disconfirms “every splash lowers raw access” | Not an observed exact 75; no recurrence. [ddx-construction-results]{2}[ddx-construction-registry]{2} |
| Grixis Squelcher | historical; one-pilot `7-1` plus League | Resolve a protection creature, then exploit its window or combo | `4 / 15` | `35.589%` access + B/Petal; `12` protection | Protection and clock in one permanent | Historical only; red requirement; exposed to creature removal. [ddx-construction-results]{2}[ddx-outcome-db]{6} |
| Wasteland/Murktide | exact published; one-pilot lineage | Attack nonbasic mana while applying pressure and retaining combo | `4 / 13` | **`72.058%`** two-land sevens; `19` lands; `34.855%` access + B/Petal | Durable land drops and real denial/clock axis | Lower access/acceleration; Wasteland competes with colored combo mana. [ddx-construction-results]{2}[ddx-outcome-db]{6} |

The numeric construction comparisons are source-direct deterministic results.
[ddx-construction-results]{2} The status and observed-recurrence clauses come from the registry and
refreshed exact-hash extract. [ddx-construction-registry]{2}[ddx-outcome-db]{6}

### The six secondary branches

The principal table is a first-read selection, not the full experiment population. All fourteen
candidates were parsed and measured; the remaining six preserve distinct questions:

| Branch | Posture | Construction signal | Why it remains secondary |
|---|---|---|---|
| Paradigm Shift / Oracle | observed historical; two-pilot recurrence | `5` access, `16` selection, `7` alternate-combo sideboard cards | Alternate win-condition treatment, not a fair-pivot increment; historical windows differ. |
| Emrakul / Shelldock Isle | observed historical | `7` access, `11` selection, `2` alternate-combo sideboard cards | Exact League publication but no standings-backed denominator. |
| Moonshadow creature switch | inferred reconstruction | `8` access; `59.767%` access + B/Petal; `4` pivot cards | Strong raw-access disconfirmer, but not an observed legal 75. |
| Cori-Steel Cutter / Barrowgoyf | inferred reconstruction | `7` access, registry-high `17` selection, `10` pivot cards | Deep sideboard capacity from a repaired historical chassis, not current recurrence. |
| Chancellor protection | observed historical | `5` access, `15` selection, `9` pivot cards | One exact 3-3 standings recurrence; mechanism remains narrow and historical. |
| Jace / Riddler / Sheoldred value threats | observed historical | `6` access, `13` selection, `8` pivot cards | Heterogeneous value module with one exact 3-3 recurrence rather than one clean mechanism. |

The construction values and evidence postures come from the deterministic registry experiment;
the recurrence statements come from exact-hash outcome matching. [ddx-construction-results]{2}
[ddx-construction-results]{3}[ddx-construction-registry]{2}[ddx-outcome-db]{6}

## How each version feels to play

These are `{inferred: play-style portraits}` derived from registered branches and card rules. The
campaign did not measure difficulty, fatigue, skill ceiling, or subjective pilot experience.

- **Focused access — decisive and resource-compressive.** Mulligans emphasize access, mana, and
  protection. Most cards point at one finish, so sequencing is about when to expose Tutor and when
  to fight. The registered sideboard still contains creatures; “turbo” is not “never fair.”
  [ddx-strategy-list-turbo]{1}[ddx-strategy-list-turbo]{2}
- **Dimir transform — role-flexible.** Game one stays access/disruption weighted; post-board hands
  may combo, clock, or threaten both. `{inferred: play-style trade-off}` That ambiguity can make
  opposing sideboarding awkward, but it can also strand halves of two plans. The future log must
  record actual deployment rather than crediting creatures merely for being boarded.
  [ddx-strategy-playtest-protocol]{4}
- **Green shield — timing-sensitive and opponent-dependent.** Veil is bounded to blue/black
  interaction; Carpet requires opposing Islands. The pilot values functional green mana only when
  the payoff is live, and should not pool all interactive opponents into one claimed matchup.
  [ddx-strategy-card-rules]{2}
- **Esper/four-color value — board-building combo.** The pilot decides whether to invest in
  creatures or Teferi before committing Doomsday. Teferi constrains timing; Swords answers
  creatures, not the stack. More mechanisms create more lines and more attribution ambiguity.
  [ddx-strategy-card-rules]{3}[ddx-strategy-card-rules]{6}
- **Grixis — window creation.** Squelcher supplies an uncounterable, warded body that prevents the
  pilot's spells from being countered. The strategic question is whether that persistent window is
  worth red mana and exposure to creature interaction. [ddx-strategy-card-rules]{5}
- **Wasteland/Murktide — genuine tempo-combo.** Land drops must serve colored combo mana or
  Wasteland activations while Tamiyo/Murktide applies pressure. It asks whether denial and clock
  are intrinsically relevant to the opponent—not whether a generic fair juke is desirable.
  [ddx-strategy-card-rules]{4}[ddx-strategy-list-wasteland]{1}

{inferred: branch-count interpretation} Lists supporting two live plans create more allocation
decisions, but the experiments did not measure difficulty, skill ceiling, fatigue, or pilot fit.

## Choose for the expected room

{inferred: metagame-conditioned recommendations}

| Expected pressure | Start with | Why this is the bounded test | Reject or escalate when… |
|---|---|---|---|
| Mixed or uncertain room | Current Dimir, with Personal Tutor as the access control | Smallest current reference; preserves a measured comparison anchor | A narrower no-juke pair shows the transform costs more than it rescues |
| Blue/black stack interaction and Islands | Light green-white; BUG second | Veil and Carpet directly address bounded rules conditions; light G/W is exact/current | Green cards are dead often, splash effects fail, or paired gain misses break-even |
| Creature boards plus permission | Esper | Separates white value/removal from the full four-color mechanism bundle | Speed/access losses dominate or removal is irrelevant |
| Several distinct shield mechanisms are intentionally under test | Four-color | Tests Teferi + Veil + Carpet + Swords as a combined system | Attribution matters, black-source pressure appears, or simpler arms perform the same job |
| Slower, nonbasic-dependent decks | Wasteland/Murktide | Treats denial-tempo as the plan rather than a sideboard surprise | Opposing mana is resilient or colored-mana sacrifice impedes combo |
| Countermagic-heavy field where a persistent creature window is plausible | Grixis Squelcher | Replicates a historically observed exact mechanism | Current independent-pilot results fail to appear or creature removal neutralizes the window |

The selection rule is: choose a limited intervention whose **paired, measured** gain against its
target clears the weighted loss elsewhere. For hostile share `s`, hostile gain `g`, and broad-field
cost `c`, break-even is `g = c × (1 − s) / s`. `{inferred: algebraic scenario}`

| Hostile pocket | Gain required to repay `0.5` point elsewhere | `1` point | `2` points |
|---:|---:|---:|---:|
| `8.4%` | `5.45` | **`10.90`** | `21.81` |
| `10%` | `4.50` | **`9.00`** | `18.00` |
| `20%` | `2.00` | **`4.00`** | `8.00` |
| `30%` | `1.17` | **`2.33`** | `4.67` |

These are hypothetical thresholds, not estimated matchup effects. The `8.4%` example is the
refreshed Dimir Tempo decision-field share; the field source itself labels practical ranks below
proof-grade confidence. [ddx-strategy-field-ranking]{1}[ddx-strategy-field-ranking]{3}

## What was actually experimented on

### Delivery boundary

The refreshed Best Deck / Best Call HTML was regenerated before these experiments from the local
DuckDB: corpus maximum 2026-08-19, field since 2026-08-10, 386 observed field decks, 95 archetype
rows, 106 camp rows, and a 35,928,949-byte self-contained output. [ddx-strategy-field-ranking]{1}
The separate user-facing Doomsday HTML is a presentation projection of this verified synthesis;
responsive/accessibility checks belong to that delivery artifact rather than to the evidence
claims in this research document.

### Observed outcome experiments

The outcome pass separated standings from selected League publications, calculated descriptive
Wilson intervals, deleted pilots/events, varied taxonomy thresholds, back-cast historical windows,
and matched exact hashes. It found no stable current ordering: threshold changes can move entrants
between classes, pilot deletion moves the Wasteland estimate from 0% through 50%, and the historical
back-cast crosses construction and legality regimes. [ddx-outcome-db]{3}[ddx-outcome-db]{4}
[ddx-outcome-db]{5}

### Deterministic construction and draw experiments

All fourteen candidates parsed as exact 60/15s, matched registered hashes, and passed the pinned
and current legality checks. Exact hypergeometric enumeration compared composition and raw
unordered seven-card events. It did **not** model mulligans, sequencing, mana assignment, piles,
interaction, matchups, or wins. [ddx-construction-results]{1}

### Inferred scenarios

The break-even grid asks how much a package must improve its target pocket to repay a specified
loss elsewhere. It estimates no package effect. Representative field rows are scenario weights,
not forecasts. [ddx-strategy-field-ranking]{1}[ddx-strategy-field-ranking]{2}

### Prospective played tests

The registered screen assigns each of thirteen non-control candidates four matches against each of
five registered-opponent roles and the same allocation to the Dimir control: 260 candidate and 260
paired-control matches. [ddx-strategy-results]{1} The protocol balances play/draw and order and withholds rankings below 20
completed matches per list. **Played-game results in this campaign: zero.**
[ddx-strategy-playtest-protocol]{1}[ddx-strategy-playtest-protocol]{2}
[ddx-strategy-playtest-protocol]{3}

## Exact next physical experiments

{inferred: experimental design} These steps extend the attested protocol and deterministic
allocation; they are proposed interventions, not completed game results.

1. **Register five opponent 75s and versions** for Dimir Tempo, Tron, Boros Energy, Azorius
   Midrange, and the Doomsday mirror before any block begins.
2. **Create the missing identical-main Dimir pair:** retain the current Dimir 60 exactly; compare
   its registered creature-transform 15 against a newly registered no-creature combo/protection 15.
   This proposed contrast is designed to isolate the sideboard juke itself.
3. **Run the focused-access calibration:** Personal Tutor turbo versus current Dimir across the
   five roles, four candidate and four paired-control matches per role. Record mulligans, actual
   combo turn, and cards exchanged; do not treat this as the sideboard-only causal test.
4. **Run shield/value blocks separately:** light green-white, reconstructed BUG as a mechanism
   sandbox, Esper, then four-color. Do not promote BUG to observed-current status unless an exact
   published legal 75 replaces the reconstruction. Log whether Veil, Carpet, Teferi, and removal
   were relevant, stranded, or imposed splash-mana effects.
5. **Run denial and persistent-protection blocks:** Wasteland/Murktide and Grixis, with an
   independent pilot required for the replication question. Log Wasteland exposure, alternate-plan
   deployment, and the protection window actually used.
6. **Complete the registered screen:** all thirteen candidates receive 20 matches and paired Dimir
   controls receive 260 total matched assignments. [ddx-strategy-results]{1} Treat four-match matchup cells as descriptive;
   rank no candidate below the protocol threshold. [ddx-strategy-playtest-protocol]{3}
7. **Promote only measured mechanisms:** compare paired differences with the relevant break-even
   row; reject packages whose gains appear outside their declared target or fail to repay losses.

## Disconfirming analysis

- **Against “tempo is simply worse”:** the exact Wasteland/Murktide lineage is 21-8 in
  duplicate-collapsed standings, and the earlier-2026 back-cast D class is 217-155.
  [ddx-outcome-db]{5}[ddx-outcome-db]{6}
- **Against “Wasteland is therefore the answer”:** every exact recurrence is one pilot; current D
  is `7-9` with a `23.1–66.8%` interval. [ddx-outcome-db]{2}[ddx-outcome-db]{6}
- **Against “every splash costs access”:** reconstructed BUG matches Personal Tutor turbo at
  `53.906%` on the access-plus-black-or-Petal event. It remains a reconstruction rather than an
  observed 75. [ddx-construction-results]{2}[ddx-construction-registry]{2}
- **Against “focused means no fair plan”:** the registered Personal Tutor sideboard contains six
  creatures. [ddx-strategy-list-turbo]{2}
- **Against “white value is the current winner”:** current standings-backed C is one 4-2 entrant;
  its other current rows are selected League publications. [ddx-outcome-db]{1}
- **Against “Grixis is either absent or proven”:** the exact historical list has a 7-1 Challenge
  and a League publication, but both are one pilot and neither is current. [ddx-outcome-db]{6}

## Contradictions and tensions

No fetched sources made directly incompatible claims within one shared measurement frame. The
table therefore preserves substantive tensions, qualifications, and one incommensurable treatment
rather than manufacturing a contradiction.

| Relationship | Position A | Position B | Treatment |
|---|---|---|---|
| `tension` | Current deep denial is 7-9. [ddx-outcome-db]{2} | The exact Wasteland list has a 21-8 collapsed standings lineage. [ddx-outcome-db]{6} | Keep class/current and exact-lineage units separate. |
| `qualifies` | Wasteland recurs five times after duplicate collapse. [ddx-outcome-db]{6} | All five are one pilot. [ddx-outcome-db]{6} | Seek independent pilots before ranking. |
| `tension` | Four-color has a principal protection count of `14`. [ddx-construction-results]{2} | It trails the other principal arms on the access-plus-selection-plus-resource event at `23.72%`. [ddx-construction-results]{2} | Do not collapse protection and access into one “consistency” score. |
| `qualifies` | The registry contains 15 artifacts representing 14 unique candidates. [ddx-construction-registry]{1} | Several candidates are historical or reconstructed. [ddx-strategy-manifest]{2} | Testing readiness is not currency or performance. |
| `incommensurable` | Registered creature transformations consume measured sideboard-pivot capacity. [ddx-construction-results]{2} | Paradigm Shift uses seven sideboard cards in the alternate-combo role. [ddx-construction-results]{3} | Test alternate combos as separate interventions. |

## Limitations

- Six current exact-archetype rows are selected League 5-0 publications; failed League runs are
  absent. [ddx-outcome-db]{1}
- Current standings evidence is only 34 decisions nested within five pilots/events; ordinary
  Wilson intervals do not repair that dependence. [ddx-outcome-db]{1}
- Taxonomy thresholds are analyst-defined and move outcome-bearing entrants. [ddx-outcome-db]{4}
- Raw-seven calculations omit mulligans, sequencing, piles, and opponents. Role groups do not
  assert equivalent card function. [ddx-construction-results]{1}
- No current exact Squelcher entrant and no observed exact BUG reconstruction exist.
  [ddx-outcome-db]{2}[ddx-outcome-manifest]{1}
- No physical matches were played; the scenario experiment allocates them prospectively.

## Revisit conditions

Revisit this hierarchy when an August 20-or-later refresh adds exact Doomsday entrants; an
independent pilot repeats Wasteland or Grixis in current standings; an exact published legal BUG,
Moonshadow, or Cutter 75 replaces a reconstruction; the Personal Tutor naming mismatch is resolved;
the identical-main Dimir sideboard pair is registered; or any paired candidate reaches the
protocol's stopping threshold. [ddx-outcome-db]{7}[ddx-strategy-playtest-protocol]{3}

## Revisions

- 2026-08-20: Corrected attestation ordinals, added the deterministic strategy-result chain for
  the 260+260 prospective allocation, replaced a qualitative Dimir access claim with its measured
  value, distinguished 15 artifacts from 14 candidates, and sourced both sides of the
  creature-pivot versus alternate-combo comparison after full-rigor adversarial review.
- 2026-08-20: Added ranking-delivery metadata, a six-branch remainder ledger, explicit play-style
  and experimental-design inference boundaries, BUG's prospective test placement, and the result
  of the direct-contradiction search after isolated evaluation.
