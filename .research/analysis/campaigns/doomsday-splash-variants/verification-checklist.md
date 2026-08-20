---
description: Fresh-context adversarial verification of the Doomsday splash-variants synthesis.
type: research
kind: research
summary: Two adversarial passes preserved the taxonomy and temporal conclusions; the second retained NEEDS-REVISION for three citation ordinals, one marker, and a missing correction log, which the lead subsequently remediated without replacing the reviewer verdict.
updated: 2026-08-20
provenance: agent-synthesis
decisions:
  - Mark the first adversarial pass NEEDS-REVISION pending source-count reconciliation, citation repair, and epistemic-marker cleanup.
  - Mark the second adversarial pass NEEDS-REVISION pending a small terminal repair set.
key_findings:
  - The post-ban family map, BUG currency gap, Grixis currency gap, and protection-card rules distinctions survive semantic review.
  - Grixis Squelcher has six pilot names in the attested nine-entry May-June cluster, not five.
  - The module catalog and recommendation prose contain multiple read-but-not-attested or unmarked composed claims despite clean mechanical lint.
  - The corrected attestations now consistently report six current League 5-0s and six Grixis pilots, with revision logs.
  - Three module-catalog mechanics claims still point at wrong or incomplete numbered specifics.
---

# Doomsday splash variants — adversarial-read checklist

## Second-pass result

The correction pass resolves most of the first-pass findings:

- `ddv-landscape-current-db` now reports six Squelcher pilots, names the same six, and records the
  correction in `## Revisions`; the parent uses six in both the Grixis section and disconfirming
  analysis.
- `ddv-compare-current-corpus` now reports six current League 5-0s and records the correction in
  `## Revisions`; the parent already used the supported six.
- Witherbloom Charm now cites `[ddv-packages-release-sos]{3}`.
- Cutter's Fantasticar statement and the Moonshadow/Cutter legality sentence now cite
  `[ddv-landscape-current-db]{7}`; the contradiction row separately cites the representative BUG
  75, avoiding a whole-lineage overstatement.
- The experiment sequence, chassis-first choice, Dimir control, Esper priority, Grixis priority,
  build order, and measurement design now carry explicit inference markers. “Dominant,” “broadest,”
  and “strong first splash” were replaced with bounded language.
- The practical program now distinguishes the banned-core BUG reconstruction from the dated
  attested Grixis registration; it no longer implies that Grixis requires a legality rebuild.
- Mechanical lint has improved to 98 resolved citations with zero broken, thin, or pattern flags.

Three residual findings remain:

1. **Medium — two module rows still cite the wrong Oracle ordinals.** At `parent.md:210`, the
   Sheoldred/Kaito/Arena mechanics cite local details `{12}` and `{18}`. Detail 12 is Cabal
   Ritual/Spoils; Arena is in `{14}`, while Sheoldred and Kaito are in `{18}`. At `parent.md:212`,
   the graveyard row cites `{14}` and `{22}`. Detail 14 is Ring/Arena; Leyline/Cage is `{15}`, while
   Dauthi/Surgical/Spellbomb/Crypt/Faerie/Cling is `{22}`. Replace `{12}` with `{14}` on the first
   row and `{14}` with `{15}` on the second. The resolved handles do not currently attest every
   named mechanic.
2. **Low — Oracle's payoff mechanic remains absent from the Paradigm row's card citation.**
   `parent.md:203` says Oracle remains the empty-library payoff. `[ddv-compare-wide-corpus]{9}`
   attests that the observed package contains extra Oracles, while `[ddv-compare-wide-cards]{6}`
   attests Paradigm and Jace mechanics, not Oracle's win ability. Add
   `[ddv-packages-card-oracle-local]{6}` for the named Oracle payoff claim.
3. **Low — correction discipline is incomplete at the analytical tier.** The parent was corrected
   in place but has no `## Revisions` log, contrary to the correction-versus-reversal discipline.
   Add a concise correction entry naming the count, citation-locus, legality wording, and inference-
   marker repairs. Also mark the remaining design instruction at `parent.md:251-252` (“should begin
   only after...”) as `{inferred: experimental design}`; it is a composed sequencing recommendation,
   not an attested historical fact.

The residuals are bounded and do not overturn the taxonomy or decision direction, but the semantic
citation chain and correction log are completion requirements. A terminal spot-check after these
edits should be sufficient; no new research acquisition is indicated.

## Revisions

- 2026-08-20 — Correction, second adversarial pass: verified the first repair set, preserved the
  initial findings below, and narrowed NEEDS-REVISION to three citation-locus/correction-discipline
  residuals.

## First-pass result

The campaign's central model is useful and substantially supported: current Doomsday lists vary by
chassis as well as color; post-ban green registrations are green-white/four-color rather than pure
BUG; pure BUG and Grixis are evidenced but dated; and Veil, Squelcher, Teferi, and Mindbreak Trap do
not perform the same rules role. The reported mechanical result—84 resolved citations, zero broken,
zero thin, and zero pattern flags—is plausible at the handle/ordinal level.

Approval is nevertheless blocked by one factual count error and a cluster of semantic-grounding
defects that mechanical lint cannot see. The minimum repair set is:

1. Correct the Grixis Squelcher cluster from **five pilots** to **six pilots** everywhere in the
   synthesis and downstream frontmatter/findings. Reconcile the internally inconsistent landscape
   attestation before re-pointing the synthesis.
2. Repair the wrong or incomplete citation loci for Witherbloom Charm, Cori-Steel Cutter,
   Moonshadow/Cutter legality, and the module catalog's card-role column.
3. Mark or reformulate the composed experiment order, control selection, splash ordering,
   broadest/dominant comparisons, build instructions, and measurement design.
4. Distinguish the dated-but-apparently-still-legal attested Grixis registration from the attested
   BUG 75 that actually requires banned-card replacement.
5. Correct the contradictory current-League count in `ddv-compare-current-corpus` and preserve the
   correction in its revisions log.

## (a) Semantic citation-chain walk

**High — the Grixis pilot count is wrong.** `parent.md:163-166` and `parent.md:275-278` say the nine
Squelcher entries represent five pilots. `[ddv-landscape-current-db]{3}` repeats “five pilot names,”
but its own enumeration names six: nevilshute, Solace_Solanum, TDjr, Zlatan87, turbo_land, and
Wilson Prado. `[ddv-compare-current-corpus]{8}` independently reports six pilots. A direct read-only
query of the refreshed database for the attested May 24-June 27 cluster also yields those six names.
Correct the landscape attestation toward the database, add a correction log, then change both
parent occurrences to six. Do not preserve the five-pilot claim merely because its handle resolves.

**Medium — Witherbloom Charm points at the wrong numbered specific.** `parent.md:135-137` describes
Charm's sacrifice/draw, life, and cheap-permanent modes but cites
`[ddv-packages-card-oracle-local]{9}`. Detail 9 is Bilbo/Unearth, not Witherbloom Charm. The claim is
already attested at `[ddv-packages-release-sos]{3}` (and in
`[ddv-compare-wide-cards]{5}`). Re-point the claim to the matching source-direct specific; retain
`[ddv-compare-card-affordances]{7}` for Abrupt Decay.

**Medium — the module catalog's “What it changes” column is systematically under-cited.** At
`parent.md:200-209`, the evidence-status citations generally establish occurrence counts, not the
adjacent rules or strategic-role claims. Examples: Paradigm Shift's library action, Emrakul plus
Shelldock's play condition, Cutter's second-spell token trigger, Chancellor's tax, Jace's empty-
library win, and the named graveyard tools' different mechanisms. The fetched Oracle attestations
contain these specifics (`ddv-compare-wide-cards` and `ddv-packages-card-oracle-local`), but the
parent does not cite them here. Add card-affordance citations and mark strategic categorization as
`{inferred: role}` where the prose goes beyond Oracle text. Occurrence evidence alone cannot attest
what a card changes.

**Medium — Cutter's Fantasticar qualification is absent from the cited locus.**
`parent.md:203` says all six Cutter rows use red duals **and Fantasticar**, but
`[ddv-compare-wide-corpus]{12}` records red duals and the Cutter/Barrowgoyf package without recording
Fantasticar. `[ddv-landscape-current-db]{7}` contains the Fantasticar/Bauble fact. Cite that detail
for the legality qualification.

**Medium — the direct citation on the Moonshadow/Cutter legality sentence is too indirect.**
`parent.md:211-212` cites `[ddv-landscape-current-db]{10}` for “every observed implementation used”
Fantasticar. Detail 10 audits maindeck location and refers back to the packages, but detail 7 is
where the all-implementation Fantasticar fact is actually attested. Re-point to `{7}`. In the
contradiction row at `parent.md:263-266`, distinguish the representative BUG 75
(`[ddv-packages-list-bug-wakame-preban]{4}`) from the universal Moonshadow/Cutter observation
(`[ddv-landscape-current-db]{7}`); the current wording can be read as saying the whole BUG lineage
used Fantasticar.

The other load-bearing chains sampled in full are semantically sound: the 12-list post-ban family
map and six published League 5-0s; the current tutor/value/tempo chassis counts; the representative
Esper and green-white registrations; the pure-BUG temporal gap; the splash-card mana schedules;
and the Veil/Squelcher/Teferi/Mindbreak Trap rules comparison.

## (b) Uncited plausible attributions, overextensions, and disguised comparatives

**High — composed recommendations are not consistently marked.** The inference-marker discipline
is applied well in the chassis table and several room hypotheses, but not at the parent decision
surface. Unmarked examples include:

- the entire recommended learning sequence at `parent.md:31-41`;
- “the chassis question comes before the sideboard question” at `parent.md:73`;
- the Dimir control choice and its “widely adopted, mana-stable” rationale at
  `parent.md:100-101`;
- “a strong first splash” at `parent.md:112`;
- the Grixis ordering for a generic mixed field at `parent.md:174-177`;
- the start/reconstruct/prototype instructions at `parent.md:236-239`; and
- the test-recording prescription at `parent.md:241-245` (the marker appears only after most of
  the prescription has already been stated).

These are cross-source experimental-design judgments, not source-attested facts. Add scoped
`{inferred: experimental design}`, `{inferred: test priority}`, or `{extends}` markers. Source-
specific counts and rules claims need no extra marker when their citations already carry them.

**Medium — comparative wording crosses the composed-claim fence.** “The dominant current
sideboard module” (`parent.md:93`) and “the broadest evidenced protection/control direction”
(`parent.md:154`) are comparative/superlative formulations. Replace them with literal, bounded
descriptions such as the exact 12-list frequencies and the exact set of roles/cards combined by the
four-color registration. “Strong first splash” should likewise become an explicitly marked test-
priority judgment rather than an apparently attested quality claim.

**Medium — Grixis is blurred with BUG in the rebuild instruction.** `parent.md:236-238` says to
“reconstruct legal post-ban BUG and Grixis candidates.” The cited BUG 75 contains four banned
Fantasticars and genuinely requires replacement. The representative Grixis attestation lists no
banned card and the synthesis elsewhere describes Grixis as dated, not illegal. Unless a source-
direct legality check finds another illegal card, describe Grixis as an **attested dated legal
registration to refresh/test**, not as a 75 requiring legal reconstruction. Keep the absence of a
post-ban result separate from deck legality.

No uncited attribution to a non-corpus author, over-extended cite-through, absolute effort estimate,
or fabricated bibliography entry was found.

## (c) Coherence read for smoothed contradictions

The explicit contradiction section correctly preserves current green versus dated BUG, repeatable
Grixis versus absent current adoption, published finishes versus missing denominator, and recurring
cards versus archetype status. It does not average pre-ban and post-ban evidence, and it correctly
avoids treating placements as package-controlled win rates.

**Medium — the evidence caveat and later generic-field ranking are in tension.** The decision result
says the sequence is not a matchup ranking and that package effects are not isolated
(`parent.md:43-45`), while `parent.md:174-177` places Grixis behind three alternatives “for a generic
mixed field.” That ordering may be a reasonable learning-priority inference from currency and card
scope, but it is not a source-attested comparative result. Mark it explicitly as test-priority
inference and state the basis as recency/scope, or remove the generic-field ranking.

**Medium — corpus-count contradictions are not structurally acknowledged.** The attestation set
contains two internal conflicts: landscape detail 3 says five Squelcher pilots while naming six,
and `ddv-compare-current-corpus` detail 7 says the 12 current rows include seven League 5-0s even
though its listed outcome categories total 13 and the direct 12-row inventory contains six League
5-0s. Correct both attestations rather than asking the synthesis to average them. The parent's six-
League statement is the supported one.

## (d) Noise domination and relevance weighting

The synthesis is not noise-dominated. Direct cached registrations and the refreshed DuckDB extracts
carry configuration/prevalence claims; Wizards release notes and comprehensive rules carry card-
behavior claims. Historical singleton and duplicate-amplified experiments are explicitly demoted.
The wide-net catalog remains relevant to the user's learning objective.

The main weighting defect is local: occurrence-count attestations are sometimes made to carry card-
mechanics or strategic-role claims even though dedicated Oracle attestations were fetched. Repair
those local chains rather than shrinking the source set.

## (e) Quote-context walk

No load-bearing verbatim source quotation appears in the synthesis. Quoted terms such as “Turbo,”
“other version,” and the disconfirmed stock-list propositions are authored labels or hypothetical
claims, not attributed quotations. Nothing else surfaced.

## (f) Analytical-tier-inheritance walk

No parent citation resolves to a specialist brief, campaign parent, prior synthesis, glossary, or
other analytical-tier artifact. All cited handles resolve to the `ddv-*` attestation tier; there is
no direct lens-as-substrate laundering.

**Medium — uncited inheritance still obscures status.** Several parent recommendations closely
carry forward marked specialist judgments but lose their markers at synthesis time, especially the
experiment order, “strong first splash,” Grixis priority, and build/test program. A specialist's
analysis does not become source-attested merely because the parent omits its handle. Apply the
markers identified in job (b).

## (g) Line and ordinal reference walk

The attestations mostly use source-internal card names, event anchors, query definitions, and
numbered details rather than fragile source line ranges. No stale explicit line range was found.

Actionable ordinal/locus defects are the wrong Witherbloom Charm `{9}`, Cutter's incomplete
`{12}`, and the Moonshadow/Cutter legality citation to landscape `{10}` rather than `{7}`. The
mechanical resolver can validate all three ordinals while still missing that they do not contain the
cited specific.

## (h) Substantively thin-attestation check

No cited attestation is globally empty or structurally thin, and all carry the normative source
handle, fetch date, source path/URL, and source-direct provenance. The representative-list
attestations are concise but contain enough card, mana, result, and source-anchor detail for their
uses.

Two substantive consistency defects require correction despite the zero-thin lint result:

- `ddv-landscape-current-db` detail 3 reports five Squelcher pilots while enumerating six.
- `ddv-compare-current-corpus` detail 7 reports seven current League 5-0s, conflicting with its own
  12-row outcome inventory and with landscape detail 1's supported six.

These are inaccurate attestations, not mere editorial noise. Correct toward the refreshed database
and record each as a correction in the attestation's revisions log before updating the synthesis.
No project-framing leak or agent-task-history prose was found in the cited attestation bodies.

## Verdict

**NEEDS-REVISION**

Second-pass residual set: repair the three module-catalog mechanics citation loci, mark the remaining
shared-project sequencing instruction, and add the parent's correction log. Then rerun lint and
perform a terminal ordinal/marker spot-check.

## Lead terminal remediation after the second-pass verdict

The lead corrected the three named ordinal loci: Paradigm/Oracle now cites the Oracle detail,
Sheoldred/Kaito/Arena points to details 14 and 18, and the graveyard row points to details 15 and
22. The later interchangeable-sideboard sequencing sentence now carries an inference marker, and
the parent has a revisions log.

Terminal mechanical lint reports 99 resolved citations, zero broken, zero thin, and zero pattern
flags. The lead spot-checked the six-pilot Grixis count, six current League publications,
Witherbloom detail, module table, Fantasticar qualification, and recommendation markers against the
attestations. This addendum records remediation; it does not replace the second reviewer's
`NEEDS-REVISION` verdict with an `APPROVED` verdict, and no third adversarial pass was run.
