---
description: Adversarial-read verification of the Energy Cabal Therapy primer campaign.
type: research
summary: Second-pass findings were surfaced and resolved; the final lead spot-check approves the corrected campaign.
updated: 2026-08-03
provenance: agent-synthesis
decisions:
  - Mark the second adversarial pass NEEDS-REVISION and resolve its two residuals in the terminal lead spot-check.
key_findings:
  - The registered maindeck, attestations, synthesis, and primer now consistently report 22 lands and four Thoughtseize.
  - The revised prevalence prose accurately follows the mixed project snapshot without claiming a false ordering rule.
  - The stale source ranges and matchup-inventory overstatement were corrected after the second pass.
---

# Energy Cabal Therapy primer — adversarial-read checklist

## Lead resolution after second pass

**Final lead spot-check: APPROVED (2026-08-03).** The second-pass residuals were corrected without a
third adversarial loop: `ecp-exact-75.md` now uses the actual source ranges (main 1–21, sideboard
24–29), and `parent.md` describes the matchup-section contents without claiming universal mulligan
or contingency branches. Final checks: parent citation lint 25 resolved / 0 broken / 0 thin;
registered list 60/15; 23 numbered matchups; every parsed numeric swap balanced; no stale
count/anchor phrases; `git diff --check` clean.

## Second-pass result

The correction pass successfully reconciled the card counts through the full downstream chain:
`decks/energy-cabal-therapy-moxfield.txt` sums to 60 main / 15 side, both exact-list attestations now
record 22 lands and four Thoughtseize with correction logs, and the exact-75 specialist, campaign
synthesis, and player primer agree. The player primer now says **recommended** rather than tested;
the Lands branch unambiguously retains the one baseline-boarded Voice and cuts a Thoughtseize; and
the prevalence paragraph accurately reports the mixed project snapshot instead of claiming a
different local popularity spine. Citation lint is mechanically clean (25 resolved, no broken or
thin chains), all 23 matchup headings remain present, and every parsed numeric swap balances.

Two residual findings prevent approval:

1. **Medium — stale, nonexistent source line anchors (job g).** `ecp-exact-75.md` says the main deck
   occupies “lines 1–37” and sideboard “lines 39–45.” The current registered source actually has
   maindeck entries on lines 1–21, the `Sideboard` marker on line 23, and sideboard entries on lines
   24–29. Replace the two ranges with the real ranges (preferably `lines 1–21` and `lines 24–29`),
   then ensure no consumer relies on the stale anchors.
2. **Low — campaign inventory remains overstated (job b).** `parent.md` still says all 23 matchup
   sections each contain “mulligan/Therapy direction” **and** “observed-build or play/draw
   branches.” Every section has Therapy guidance, but several have no explicit mulligan direction
   and straightforward sections such as the Energy mirror have no build/play-draw branch. Replace
   the sentence with a literal inventory, for example: “It contains 23 matchup sections, each with
   the opponent's plan, our counter-plan, Therapy direction, and a balanced baseline; matchup-
   specific mulligan and observed-build/play-draw branches appear where material.”

One nonblocking editorial cleanup is advisable: `ecp-exact-list.md` describes “eight one-mana
targeted interaction spells” and then separately lists four Swords, even though Swords is part of
that eight. The detailed list below is correct, but naming “four Thoughtseize and four Swords” in
the summary would remove the apparent double count.

### Second-pass jobs a–h

- **(a) Semantic chain:** corrected count and prevalence chains now support the downstream claims;
  no new semantic mismatch surfaced.
- **(b) Missed claim shapes:** unsupported “tested” was corrected; the per-section inventory
  overstatement above remains.
- **(c) Contradictions:** the prevalence smoothing was removed; Dredge, Aluren, and Blue Artifacts
  qualifications remain structurally visible.
- **(d) Relevance weighting:** direct registration and Oracle sources remain primary; no
  noise-domination finding.
- **(e) Quote context:** no verbatim synthesis quotes; nothing surfaced.
- **(f) Analytical inheritance:** no analytical-tier citation laundering; nothing surfaced.
- **(g) Line references:** stale exact-75 ranges above require correction.
- **(h) Thin attestations:** no thin attestation; corrected exact-list bodies are substantive.

## (a) Semantic citation-chain walk

**High — exact-list chain fails at the source.** `parent.md:20-22` says the exact 60 has 21 lands
and cites `[ecp-exact-list]{1}`. The player primer repeats 21 lands at line 16, making the displayed
maindeck total only 59 (25 creatures + 13 noncreature spells + 21 lands). Directly summing
`decks/energy-cabal-therapy-moxfield.txt` gives **22 lands**: eight fetchlands, four Wasteland, two
Karakas, two Plateau, two Scrubland, and four singletons. The citation resolves mechanically but
the attestation is itself wrong. A second attestation, `ecp-exact-75.md`, independently says 23
lands and three Thoughtseize, also contradicting the source (which has 22 and four). Fix toward the
substrate: correct both attestations, then correct `parent.md` and the player primer to 22 lands.

**Medium — popularity claim is not supported as phrased.** `parent.md:27-33` says the local snapshot
places Dimir Tempo, Azorius Midrange, Doomsday, Energy, Blue Artifacts, and Dimir Midrange “at the
front” and that the primer uses the local field as its popularity spine. But
`[ecp-current-corpus]{2}` ranks Tron, Show and Tell, Izzet Delver, Energy, Dimir Tempo, Doomsday,
Blue Artifacts, and Grixis Reanimator as the top eight; Azorius is ninth and Dimir Midrange tenth.
The primer itself begins Dimir, Izzet, Azorius, Control, Energy rather than following that local
order. Either (1) reorder the matchup headings to the local ranking and describe the exact ordering
rule, or (2) remove “local popularity spine” and say the guide covers the convergent leading field
in a player-oriented grouping. Also amend the frontmatter decision at `parent.md:8`.

Other sampled load-bearing chains—Raptor casting constraints, Priest versus Ajani/Show and Tell,
Conqueror symmetry, Leyline/Surgical tension, and Rod/Conqueror scope—are semantically supported by
their Oracle attestations.

## (b) Claim shapes mechanical lint missed

**Medium — unsupported empirical wording.** The player primer at lines 3-6 calls the sideboard maps
“tested starting points.” The campaign documents representative-list analysis and synthesis, not
match testing of all 23 plans. Replace **tested** with **synthesized** (or identify and attest actual
match-test evidence).

**Low — overstatement of section completeness.** `parent.md:70-72` says each of 23 sections has
“mulligan/Therapy direction” and an observed-build or play/draw branch. All 23 do contain opponent
plan, counter-plan, Therapy direction, and a balanced baseline, but several have no explicit
mulligan instruction and several have no branch. Rewrite the inventory to match the artifact, or
add the missing per-matchup mulligan and branch guidance.

No over-extended cite-through or uncited comparative-superlative claim was otherwise found. The
lint's low comparative phrase is not load-bearing once “tested” is corrected.

## (c) Coherence read for smoothed contradictions

**Medium — local-order contradiction is surfaced, then smoothed.** The `## Contradictions` section
correctly preserves the local-versus-external ranking conflict, but the decision prose converts it
into a purported local popularity spine that follows neither cited order. Apply one of the two
repairs in job (a); do not characterize a custom editorial order as the local ranking.

The Dredge-label contradiction and Aluren qualification remain visible in the player-facing plans;
no additional cross-source contradiction was smoothed away.

## (d) Noise domination / relevance weighting

The direct deck registration and local Oracle bulk data are the most relevant sources for deck
counts and rules interactions. The synthesis generally uses them appropriately, except that the
two erroneous exact-list attestations displaced the direct source count. For metagame prevalence,
the local corpus and external rolling aggregation both remain visible and appropriately
venue/window-qualified after the ordering repair above. No other less-relevant source displaced a
more relevant attestation in the sampled matchup claims.

## (e) Quote-context walk

No verbatim quotations occur in the synthesis or player-facing primer. Nothing surfaced.

## (f) Analytical-tier inheritance walk

No citation resolves to a specialist brief, campaign synthesis, prior position, or other
analytical-tier artifact. The player-facing strategy is explicitly presented as synthesis, and its
evidence boundary points readers to the campaign rather than laundering that campaign as a direct
source. Nothing else surfaced.

## (g) Line-reference walk

The synthesis and primer do not cite source line/section ranges. The MTGDecks attestation records
the page ranges it used, but the synthesis cites the attestation handle rather than making a false
sub-range claim. Nothing surfaced.

## (h) Thin-attestation check

No structurally thin attestation was reported by lint, and the sampled Oracle, current-corpus,
representative-list, and deck-registration attestations contain enough claim-level specifics for
their uses. **First-pass finding, resolved on second pass:** the two exact-list summaries formerly
disagreed with the registered file; their corrected counts now reconcile. The stale source line
ranges identified in the second-pass result remain a granularity problem, not thinness.

## Player-facing matchup and arithmetic audit

- The claim that **23 archetypes are covered** is numerically correct: the primer has numbered
  sections 1 through 23. Several headings intentionally combine aliases or nearby builds, so it
  covers at least 23 recognizable archetype labels and includes every archetype in the local
  corpus's listed top 20, though not in local rank order.
- Every explicit numeric baseline and conditional exchange has equal cards in and out. “No change”
  plans are arithmetically valid.
- **First-pass finding, resolved on second pass:** the former impossible “fourth Voice” wording now
  correctly says to retain the boarded-out Voice and cut one Thoughtseize instead.
- Rules sampling found the highlighted interactions accurate: Priest prevents an uncast Ajani
  return and must preexist Show and Tell; Conqueror is symmetric; Voice tokens survive through
  postcombat main phase; Bombardment can trigger an opposing Bridge's exile clause; Silence can
  strand a Raptor noncreature hit; and Leyline can remove Surgical's target.

## Verdict

**NEEDS-REVISION**

Residual repair set: correct the two stale source line ranges in `ecp-exact-75.md` and make the
23-section inventory sentence in `parent.md` literal. Then re-run lint and perform the terminal
spot-check against the direct deck file. The first-pass count, prevalence, “tested,” and Lands-branch
findings are resolved.
