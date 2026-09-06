---
description: Adversarial-read verification of the Doomsday pivot-intensity and performance campaign.
type: research
summary: Mechanical citation lint is clean, but cohort drift, source-row errors, an over-literal sideboard-only class, and unattested mechanism and status claims require revision before the campaign can be approved.
updated: 2026-08-20
provenance: agent-synthesis
decisions:
  - Mark the adversarial read NEEDS-REVISION.
  - Preserve the narrow descriptive result that the Tutor/Wasteland direction remains after publication and event restrictions, while treating a pilot-controlled effect as unavailable.
  - Require one explicit post-ban population contract before class outcomes or threshold sensitivity are interpreted.
key_findings:
  - Terminal reviewer lint resolved 135 citation occurrences with zero broken chains, zero structurally thin attestations, and zero pattern flags.
  - The outcome and taxonomy attestations call different twelve-row cohorts the post-ban slice and the parent blends them without disclosure.
  - Two outcome rows incorrectly label sideboard Tamiyo as maindeck Tamiyo, despite the aggregate Tamiyo count using the correct mainboard definition.
  - The class named sideboard-only includes registrations with measured or unmeasured maindeck pivot cards and cannot stand in for the proposed matched-main sideboard experiment.
  - Card-role, candidate-status, and banned-chassis claims exceed the specifics recorded in the current ddp attestations.
---

# Doomsday pivot performance — adversarial-read checklist

## Verdict

**NEEDS-REVISION.**

The narrow performance result is source-supported: the published Personal Tutor/Wasteland surface
moves from 22-5 versus 7-9, to 7-5 versus 7-9 with League rows removed, and to 7-5 versus 7-7 in
MTGO Challenges. That is a persistent numerical direction under the available publication and event
restrictions, not a demonstrated tempo penalty. A pilot-controlled result is unavailable because
the Challenge-only Wasteland arm is one pilot's two lists.

The proposed decision posture is therefore still plausible: retain focused Tutor turbo as a
priority arm, create the matched-main no-juke/juke comparison first, keep value-combo separate, and
retain deep denial-tempo as a diagnostic arm. It is not yet certifiable because the campaign blends
two population contracts, uses a class name that does not describe its members literally, and has
several source-chain defects that mechanical lint cannot detect.

## Mechanical baseline and direct checks

- The terminal reviewer lint over the campaign directory, with URL probing disabled, reports
  **135 resolved citations, 0 broken chains, 0 structurally thin attestations, 0 omitted substrate-
  confidence fields, 0 campaign-binding findings, and 0 pattern flags**.
- Every citation handle resolves to one of the seven `ddp-*` source-direct attestations. No citation
  resolves to the prior `doomsday-splash-variants` campaign or another analytical-tier artifact.
- Every cited numeric scope is present: outcome scopes 1–6, post-ban-taxonomy scopes 1–5,
  registry scopes 1–4, and scope 1 for each single-scope attestation.
- Direct read-only checks were also made against `data/legacy.duckdb`, the fourteen candidate deck
  files plus `manifest.json`, the paired-playtest protocol, and the relevant card rows. The
  registered construction table, manifest count/alias, playtest threshold, and reported
  Tutor/Wasteland sensitivity arithmetic reconcile to those sources.

## Required correction set

### 1. High — the parent blends two different post-ban cohorts

`ddp-outcome-current-corpus.md:14-17` selects `archetype = 'Doomsday'` from August 10 onward. Its
twelve rows include SmokyboyJFF and exclude lassi. `ddp-taxonomy-postban.md:13-17` instead selects
any row with a maindeck Doomsday from August 11 onward. Its twelve rows include lassi, whose stored
archetype is `Conflict(Doomsday,TES)`, and exclude SmokyboyJFF. A direct source query finds thirteen
maindeck-Doomsday rows from August 10 through 18; the two attested twelve-row sets overlap in eleven
rows.

The parent calls both sets *the* twelve-list post-ban slice at `parent.md:55-69`, and later combines
taxonomy and outcome interpretations at `parent.md:148-195`. The specialist briefs likewise never
surface this population difference. This is a smoothed incommensurability, not a cosmetic date
label.

The downstream impact is observable. Under the outcome attestation's cohort, the baseline class
counts remain A0/B5/C4/D3, but the six-card side-module stress test becomes A1/B4/C4/D3 rather than
A2/B3/C4/D3. The class-B surface becomes three undefeated League publications plus Challenge
10th/17th, instead of two undefeated League publications plus Challenge 10th/17th and a paper 14th.
The baseline count happens to
remain equal because SmokyboyJFF and lassi both satisfy B under the current rule; that coincidence
does not make the populations interchangeable.

Choose and state one population contract. The outcome contract matches the campaign's August 10
ban boundary and existing exact-archetype outcome calculation. If the broader maindeck-Doomsday
population is decision-relevant, analyze all thirteen rows as a separately named construction
surface. Then recompute `pivot-taxonomy.md:86-145`, the parent taxonomy and disconfirmation claims,
and the contradiction ledger. Do not silently swap one B member for another.

### 2. Medium — two exact-list chassis labels are false against the source

`ddp-outcome-current-corpus.md:42` and `:53` label SmokyboyJFF and clan as both Personal Tutor and
Tamiyo under a definition that requires a positive **maindeck** count. Direct card rows show three
Personal Tutor main and one Tamiyo **sideboard** for each list, with no maindeck Tamiyo. The
attestation's aggregate table correctly reports eight Tamiyo-main entries, so the exact-list table
also contradicts its own aggregate.

Correct both row labels toward the database and add a revision entry. Recheck every downstream
exact-list-membership example; the current aggregate Tutor/Wasteland comparison does not change.

### 3. Medium — class B is not literally sideboard-only

The B rule at `pivot-taxonomy.md:46-49` allows up to two measured maindeck value permanents and does
not measure maindeck interaction outside that proxy set. Its registered members include current
Dimir with two maindeck Tamiyo, Grixis with one maindeck Hexing Squelcher, and light green-white with
maindeck Swords to Plowshares and Veil of Summer. The source counts support the rule, but not its
literal name or the general statement that game one remains focused.

Rename B to a construction-faithful label such as **low measured main-value plus side module** or
**sideboard-led pivot**. Reserve **sideboard-only transformation** for the proposed A/B experiment
whose exact maindeck and mana base are held constant. Update `parent.md:42-58`,
`pivot-taxonomy.md:40-49`, and all class-B interpretation/disconfirmation prose. This keeps the
valuable four-rung design while preventing selected B publications from being read as evidence for
a treatment that the corpus does not contain.

### 4. Medium — standings coverage is overstated and internally inconsistent

`matchup-economics.md:22-27` says standings are present for the listed registrations. They are not
present for the Battlegrounds, four-color wakame, clan, or dated BUG League sources; those sources
have deck-level result fields and no standings or rounds. Standings are present for the current
Dimir, wizardpasta, HJ_Kaiser, and nevilshute event registrations. This also conflicts with
`ddp-outcome-current-corpus.md:61-74`, which correctly records zero standings for the current League
rows.

Correct `ddp-match-store.md:15-23` to distinguish deck result fields, standings rows, event-level
round rows, and direct target-player round rows. Include tournament IDs or equally precise query
anchors. Then replace the specialist's blanket standings sentence with the row-specific boundary.
The conclusion that direct matchup coverage is inadequate remains supported.

### 5. Medium — named mechanisms and candidate statuses are read-but-not-attested

The mechanism table at `matchup-economics.md:61-79` assigns roles to Bilbo, Swords to Plowshares,
Witherbloom Charm, and Barrowgoyf, but `ddp-card-capabilities.md` records none of those cards. The
table's role-to-endpoint mapping is also composed experimental design and needs an epistemic marker,
not only the later acknowledgment at lines 148–150.

The same attestation paraphrases Teferi as able to bounce “a permanent.” The fetched card row limits
that ability to an artifact, creature, or enchantment. Correct the qualifier before using Teferi as
generic permanent interaction.

Separately, `matchup-economics.md:97-108` makes current, dated, reconstructed, legality, and
banned-chassis claims. `ddp-registered-candidates.md` says that status fields exist but does not
record the relevant per-candidate values, and no current `ddp-*` legality attestation supports the
claim that Moonshadow/Cutter reconstruct a banned chassis. The prior campaign cannot fill either
gap because it is lens only.

Extend the current source-direct attestations with the exact card rules and per-candidate status or
legality specifics before retaining these claims. Cite the matching specifics and mark the
mechanism-to-endpoint mapping as inference. Do not cite the prior campaign as substrate.

### 6. Low — claim precision and substrate prose need cleanup

- `parent.md:74` collapses **Teferi main** and **white-only** into one slash label because both happen
  to total 19-2 and 4-2. They are different four-list sets: wakame appears only in the Teferi set and
  Enrichetta only in the white-only set. Give them separate rows or state that the totals coincide
  despite different membership.
- `parent.md:78` says all category memberships overlap, although color packages are explicitly
  exclusive. Say that chassis categories can overlap and that each list has one exclusive color-
  package label.
- `matchup-economics.md:32` calls the paired log the “first usable source for the decision.” That
  unsupported superlative conflicts with the campaign's legitimate descriptive use of published
  outcomes. Narrow it to the prospective source for matchup-specific package effects.
- `outcome-surface.md:82` refers to “the user's” observation, `parent.md:60` refers to an undefined
  “initial Grixis intuition,” and `matchup-economics.md:154-163` narrates the agent's search in first
  person. Restate these as durable hypotheses and neutral source-search results so the artifacts pass
  the first-engagement substrate test.

## Jobs (a)–(h)

### (a) Semantic citation-chain walk

**Findings.** The numerical Tutor/Wasteland surface, exact-list counts/hashes, registered
construction counts, break-even arithmetic, protocol fields, and twenty-match threshold are
semantically supported. The failures are the cross-cohort use in finding 1, the false Tamiyo row
labels in finding 2, the standings statement in finding 4, and the absent card/status specifics in
finding 5. Those claims resolve mechanically but do not walk cleanly to source-direct specifics.

### (b) Claim shapes mechanical lint missed

**Findings.** The literal sideboard-only label and game-one-focus interpretation exceed the measured
proxy; the card-role and candidate-status claims are unattested; and “first usable source” is an
unsupported comparative. The task-context phrases in finding 6 also fail the substrate test. No
absolute effort estimate or fabricated bibliographic metadata appears.

### (c) Coherence read for smoothed contradictions

**Findings.** The eleven-row cohort overlap is smoothed into one twelve-list slice. Standings are
also described differently in the outcome and matchup briefs. Neither conflict appears in the
campaign's contradiction tables. The raw-versus-restricted outcome difference, persistent numerical
direction versus pilot dependence, and historical-versus-current boundary are otherwise kept
visible rather than averaged away.

### (d) Noise domination and relevance weighting

**No independent noise-domination finding.** The direct tournament extract is the relevant source
for the outcome surface; exact deck files and the manifest are relevant for construction; the
protocol is relevant for prospective measurements. The problem is inconsistent population use and
missing current attestation detail, not displacement by a noisier external source. The acquisitions
ledger appropriately treats absent League denominators and match rows as missing observations rather
than naming an unsupported acquisition candidate.

### (e) Quote-context walk

**No attributed verbatim quotation appears.** Quotation marks introduce hypotheses, labels, or field
values rather than source quotations. The lost Teferi qualifier is an inaccurate attestation
paraphrase and is recorded under jobs (a) and (h), not a verbatim-quote framing failure.

### (f) Analytical-tier inheritance walk

**No direct citation laundering.** Lint reports no analytical-tier citation target, and the prior
campaign is not cited. The current mechanism/status/banned-chassis gap is nevertheless an inheritance
risk: those claims resemble prior analytical framing but have not been re-attested in the current
campaign. Repair them from source-direct card, manifest, and legality records; keep
`doomsday-splash-variants` as lens only.

### (g) Line and ordinal reference walk

**No stale explicit line or section range appears.** All cited numeric scopes exist within their
attestations, and each source path resolves. The defects above concern population identity and the
content inside resolved scopes, not nonexistent ordinals.

### (h) Substantive thin-attestation check

**Findings despite zero structural lint flags.** `ddp-match-store.md` is too thin for its exact-source
coverage use because it omits tournament IDs, dates, query anchors, and a row-wise distinction among
deck results, standings, event rounds, and direct player rounds. `ddp-registered-candidates.md` is
adequate for the fourteen-count and alias claims but too thin for the per-candidate currency,
reconstruction, and legality claims made downstream. `ddp-card-capabilities.md` is substantive for
the cards it lists but passage-absent for several cards used in the mechanism table.

## Revision gate

1. Choose or explicitly separate the post-ban population contract and recompute all affected
   taxonomy, sensitivity, and class-outcome statements.
2. Correct the two Tamiyo memberships, the League standings boundary, and the Teferi qualifier
   toward the fetched sources.
3. Rename class B and revise every downstream sentence that treats it as a literal sideboard-only
   treatment.
4. Extend current source-direct attestations for the named card roles and candidate status/legality
   claims; add epistemic markers to the composed mechanism map.
5. Add revision logs to every corrected existing artifact, rerun citation/pattern/thin lint, and
   repeat a direct-source spot check of population membership, standings coverage, and cited card
   rules.

Approval requires all five steps. The supported descriptive outcome need not be reversed unless the
recomputed common population changes it; the current campaign requires correction and downstream
reconciliation, not a new superseding artifact.

## Lead correction disposition

All five revision-gate steps were applied after this single standard adversarial pass:

- the shared post-ban population is now the twelve exact `Doomsday` rows from August 10–18, with
  the conflict-labelled row kept outside the comparison;
- Tamiyo zone membership, standings coverage, and Teferi's permanent-type qualifier were corrected;
- class B is now consistently named **sideboard-led pivot**, while **sideboard-only** is reserved for
  the proposed matched-main experimental treatment;
- card capabilities and candidate provenance, reconstruction, currency, and legality posture were
  extended in source-direct attestations; and
- every corrected artifact carries a revision log.

Lead verification then repeated the population, zone, standings, card-rule, and candidate-status
spot checks. Citation lint resolved 141 citations with zero broken, thin, or pattern flags, and
`git diff --check` passed. Per the standard-rigor policy, no second independent adversarial review
was commissioned.

## Revisions

- 2026-08-20: Recorded the lead's correction disposition and direct-verification result without
  changing the independent review verdict.
