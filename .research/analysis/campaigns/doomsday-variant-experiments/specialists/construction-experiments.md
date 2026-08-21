---
description: Deterministic construction and opening-access comparison of the registered Doomsday variants.
type: brief
kind: research
summary: Verifies the 14 canonical 75s and compares mana, access, selection, protection, value/tempo density, sideboard capacity, and exact seven-card opening distributions without inferring game outcomes.
updated: 2026-08-20
provenance: agent-synthesis
key_findings:
  - All 14 registered candidates parse as exact 60/15s, match their registered hashes, and pass pinned and current legality checks.
  - Personal Tutor density separates raw access-heavy constructions from value, shield, and Wasteland constructions more strongly than land count does.
  - Splash and tempo arms buy registered protection, interaction, or value density while exposing lower black-source or access-plus-resource opening frequencies; those are construction costs, not measured win-rate penalties.
---

# Doomsday variants — construction and access experiment

## Decision surface

All 14 canonical candidates parse as 60-card maindecks plus 15-card sideboards, reproduce their
manifest hashes, and pass both the pinned August 10 and current legality snapshots. Their evidence
postures are not interchangeable: six principal arms are exact/current or exact/published, Grixis
is observed-historical, BUG is reconstructed, and several alternate modules are historical or
reconstructed. [ddx-construction-registry]{1}[ddx-construction-results]{1}

The table below is a construction comparison, not a performance ranking. `{inferred: classify}`
Access is Doomsday plus Personal Tutor; selection, protection, interaction, value/tempo, and pivot
counts use the disclosed card-name role map. Exact opening probabilities use an unordered seven-card
hand with no mulligans. [ddx-construction-results]{1}

| Principal arm | Posture | Land / accel | Access / selection | Protection / value-tempo | Side pivot | Fetch-enabled land sources B · splash | P(access + B/Petal) | P(access + selection + B/Petal) | Evidence |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| Personal Tutor turbo | exact published | 16 / 8 | **7 / 13** | 12 / 0 | 6 | 14 · — | **`53.91%`** | **`42.91%`** | [ddx-construction-results]{1}
| Current Dimir transform | exact current | 17 / 8 | 6 / 14 | 11 / 2 | 7 | **15** · — | `49.32%` | `40.55%` | [ddx-construction-results]{1}
| Light green-white | exact current | 17 / 8 | 5 / **15** | 10 / 0 | 5 | 13 · W10 G9 | `41.52%` | `34.91%` | [ddx-construction-results]{1}
| Esper Teferi/Swords | exact current | 17 / 7 | 4 / 13 | 8 / **10** | 8 | 14 · W10 | `34.86%` | `27.37%` | [ddx-construction-results]{1}
| Four-color shield | exact current | 17 / **9** | 4 / 10 | **14** / 7 | 0 | 12 · W10 G10 | `34.86%` | `23.72%` | [ddx-construction-results]{1}
| BUG Veil/Carpet | **inferred** | 16 / 9 | **7 / 13** | 10 / 1 | 0 | 13 · G10 | **`53.91%`** | **`42.91%`** | [ddx-construction-results]{1}
| Grixis Squelcher | historical | 17 / 8 | 4 / **15** | 12 / 2 | 6 | 14 · R10 | `35.59%` | `29.88%` | [ddx-construction-results]{1}
| Wasteland/Murktide | exact published | **19** / 7 | 4 / 13 | 8 / **10** | 6 | 14 · — | `34.86%` | `27.37%` | [ddx-construction-results]{1}

`B/Petal` means a fetch-enabled black land source or Lotus Petal. Cavern of Souls is reported
separately in the result because its colored mana is conditional. A fetchland is counted for a color
only when the registered maindeck contains a typed land it can find that produces that color.
[ddx-construction-card-catalog]{1}[ddx-construction-results]{1}

## What the distributions actually distinguish

### Access-first Dimir

Personal Tutor turbo registers seven access cards and a `60.09%` chance to open at least one; current Dimir registers six and `54.14%`. Their access-plus-selection-plus-black/Petal events occur in `42.91%` and `40.55%` of raw sevens. [ddx-construction-results]{1} `{inferred: interpret construction}` These are exact-registered
ways in this registry to test whether access density is worth more than preloaded fair/value
material. They do not establish a faster actual combo turn because the experiment never sequences
the hand or builds a pile. [ddx-construction-results]{1}

### White, green, and four-color shields

Light green-white retains five access cards and 15 selection cards while registering ten white and nine green fetch-enabled sources. Its access-plus-black/Petal event is `41.52%`, between the access Dimir arms and the four-access arms. Four-color shield instead registers 14 protection cards, more than any other principal arm, and nine acceleration cards, but only four access and ten selection; its three-way access/selection/resource event is `23.72%`, below every other principal-arm value. [ddx-construction-results]{1}

`{inferred: identify pressure}` The four-color construction's black fetch-enabled source count is
12 versus current Dimir's 15, while it adds ten white and ten green sources. That is visible
color-allocation pressure, not proof of color failure: fetchlands are choices, not simultaneous
mana, and a raw hand model does not decide which land to fetch or which spell to cast first.
[ddx-construction-results]{1}

BUG combines seven access cards with nine acceleration and ten green sources, producing the same `53.91%` access-plus-black/Petal measurement as Personal Tutor turbo. [ddx-construction-results]{1} This is disconfirming evidence
against a blanket claim that every splash mechanically lowers raw access. However, the emitted BUG
75 is an inferred reconstruction rather than an observed list, so its attractive construction
profile is a hypothesis generator. [ddx-construction-registry]{1}[ddx-construction-results]{1}

### Value and tempo preloading

Esper and Wasteland/Murktide each devote ten maindeck cards to the disclosed value/tempo group and each has four access cards. Their access-plus-selection-plus-black/Petal result is identical at `27.37%`, despite very different contents. [ddx-construction-results]{1} Esper reaches that density with Bilbo, Tamiyo, and Teferi;
Wasteland reaches it with Tamiyo, Murktide, Jace, and Wasteland in the role map. `{inferred: do not
equate mechanisms}` Equal opening-category probabilities do not make their play patterns or
resource demands equivalent. [ddx-construction-results]{1}

Wasteland/Murktide's 19 lands yield a `72.06%` chance of at least two lands, compared with `60.83–64.82%` for the other principal arms. [ddx-construction-results]{1} It also has seven acceleration and eight protection cards. This
quantifies the registered exchange toward durable land drops and maindeck tempo density; it cannot
tell whether that exchange improves a matchup or merely dilutes combo execution. [ddx-construction-results]{1}

Historical Grixis registers 15 selection and 12 protection cards, ten red sources, and six pivot
sideboard cards. Its access/resource probability remains in the four-access cluster. `{inferred:
testing implication}` Hexing Squelcher therefore belongs in a persistent-protection experiment,
not in an access-density claim, and the arm must retain its historical posture. [ddx-construction-registry]{1}[ddx-construction-results]{1}

## Sideboard exchange and dilution capacity

The sideboard role map counts registered capacity, not prescribed boarding. Current Dimir can
present seven pivot cards, Esper eight, Grixis and Wasteland six each, and light green-white five.
Four-color and reconstructed BUG contain no cards in the narrow creature-pivot set; their sideboards
instead emphasize protection, interaction, or alternate Jace capacity. [ddx-construction-results]{1}

At the high end, the inferred Cutter arm contains ten pivot cards, Chancellor nine, and the historical value-threat arm eight. Swapping all of those cards would displace `16.67%`, `15%`, and `13.33%` of a maindeck respectively. [ddx-construction-results]{1} `{inferred: dilution ceiling}` Those percentages are maximum
registered exchange capacities—not recommendations and not evidence that the corresponding cards
should all enter together. The actual cards removed, matchup, mana, and post-board line must be
logged.

Paradigm Shift is structurally different: seven sideboard cards fall in the alternate-combo group.
Emrakul/Shelldock has two. `{inferred: separate treatment}` They should be analyzed as alternate
library-win treatments rather than pooled with creature transformations. [ddx-construction-results]{1}

## Alternate branches worth preserving

The inferred Moonshadow arm has eight access cards and an access-plus-black/Petal raw-opening probability of `59.77%`, exceeding every other registry arm; inferred Cutter has 17 selection cards and ten pivot slots. [ddx-construction-results]{1}
These results actively challenge a simple “transformation always costs pre-board access” story,
but both 75s are legal repairs of Fantasticar-era sources rather than observed configurations.
[ddx-construction-registry]{1}[ddx-construction-results]{1}

Chancellor, Paradigm Shift, Emrakul/Shelldock, and the heterogeneous value-threat list all preserve
distinct experimental questions. Their measured role counts support keeping them separate; the
construction experiment supplies no basis for claiming that any is stronger than the principal
arms. [ddx-construction-results]{1}

## Disconfirming analysis

- A splash does not mechanically imply low raw access: reconstructed BUG matches Personal Tutor
  turbo on the access-plus-black/Petal metric because it also registers three Personal Tutors.
  Its evidence posture prevents promoting that observation into an observed-current conclusion.
  [ddx-construction-registry]{1}[ddx-construction-results]{1}
- A deep pivot does not mechanically imply an access profile below every other arm: inferred Moonshadow has the registry's highest access count. Its maindeck is not an observed 75, so this disconfirms an
  absolute construction claim but not a performance claim. [ddx-construction-registry]{1}[ddx-construction-results]{1}
- More protection does not imply a better compound opening under this definition: four-color has
  14 protection cards but an access-plus-selection-plus-resource probability below every other arm among the
  principal arms. Conversely, the metric does not value Veil or Teferi's context, so it cannot
  establish that those cards are a net cost. [ddx-construction-results]{1}
- Wasteland's extra lands materially increase two-land raw openings. This is a resource advantage
  the access-only comparison would hide; whether it compensates for lower acceleration/access is
  outside the model. [ddx-construction-results]{1}

## Contradictions

| Relationship | Evidence | Treatment |
| --- | --- | --- |
| `tension` | Four-color leads the disclosed protection count while trailing the compound access/selection/resource event. | Preserve both dimensions; do not collapse them into “consistency.” |
| `qualifies` | BUG and Moonshadow show access-heavy splash/pivot constructions, but both are inferred reconstructions. | Use as experimental arms, not observed-current recommendations. |
| `incommensurable` | Creature-pivot capacity and alternate-combo capacity consume sideboard slots but pursue different lines. | Report them in separate columns and treatments. |
| `qualifies` | Esper and Wasteland share exact compound probabilities but have different role composition and land counts. | Do not infer similar play style or outcome from equal percentages. |

## Experimental handoff

Use the exact registered version/hash for each arm. The construction results support four first-order
contrasts: Personal Tutor vs current Dimir for access density; light green-white vs four-color for
incremental versus full shield; Grixis vs Esper for persistent red versus white timing protection;
and Wasteland/Murktide vs a matched Dimir arm for maindeck tempo density. `{inferred: prioritize}`

Record mulligans, fetched colors, mana spent before Doomsday, actual combo turn, cards exchanged,
and alternate-plan deployment in gameplay. The raw-hand result must not be substituted for any of
those observations.

## Revisit if

- Any registered path, canonical hash, or manifest evidence posture changes.
- The Legacy ban list or local Oracle export changes.
- A published exact BUG, Moonshadow, or Cutter legal 75 replaces an inferred reconstruction.
- A mulligan/sequencing engine can model keeps and actual mana assignments without assuming away
  Doomsday piles or opponent interaction.
- Paired gameplay reaches its registered stopping threshold and can test whether the construction
  differences correspond to actual outcomes.
