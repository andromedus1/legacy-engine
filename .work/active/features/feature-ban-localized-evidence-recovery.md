---
id: feature-ban-localized-evidence-recovery
kind: feature
stage: review
tags: [analytics, advisory, ui, testing]
parent: null
depends_on: [epic-recurrent-stable-era-evidence]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Recover matchup evidence locally across short-lived banned-card windows

## Brief

Make the Best Deck / Best Call report useful immediately after a localized ban. Current field shares
remain post-ban because they answer what is being played now, but matchup evidence must no longer
reset globally. For an unaffected subject/opponent pair, retain compatible historical matches. For
an edge involving an archetype materially affected by a banned card, exclude the card's exposure
interval and admit clean pre-release/pre-adoption evidence together with post-ban evidence.

Fantasticar is the forcing case: it appears in the corpus only from 2026-06-20 through its
2026-08-10 ban, with most use concentrated in five archetypes. The current report nevertheless has
zero proof-grounded parent rows because its current-field clock and strict pair evidence presentation
effectively erase useful history. The correction must make the archetype table informative without
pretending that contaminated matches or borrowed estimates are direct proof.

## Strategic decisions

- **Separate field and evidence clocks:** current field composition stays post-ban; matchup evidence
  uses entity-pair clean interval unions.
- **Localize invalidation:** a ban removes only the exposure interval for materially affected
  entities and only from edges involving them; it does not reset unrelated matchup histories.
- **Recover the clean past:** affected edges may use evidence before the banned card's release or
  outcome-free corpus-first-adoption boundary plus post-ban evidence, preserving the excluded gap.
- **Useful estimates are primary:** the archetype table shows the best available current estimate
  with direct/history/borrowed provenance and confidence; proof-grade remains a badge/filter, not a
  requirement to render an estimate.
- **No silent promotion:** recovered and amplified evidence remains labeled and decomposed. Changing
  production authority still requires validation, but diagnostic usefulness may not be hidden.

## Simplification opportunity

Replace the report's conflation of one scalar post-ban field window with matchup-evidence authority.
Reuse the exact interval selector and selected-outcome ledger already built by the recurrent-evidence
epic; do not create another SQL aggregation path or require manually supplied run ids for the normal
localized-ban case.

## UI surface

Reuse the existing archetype table, evidence disclosure, confidence chips, and filters. No new screen
or design-system primitive is needed. The default table should foreground active-field rows and
their best available estimate, while the strict proof view remains available as a filter/audit.

## Acceptance direction

- On the current Fantasticar corpus, unaffected pairs retain pre-ban evidence and affected pairs
  exclude only the Fantasticar exposure gap while admitting clean pre-exposure plus post-ban rows.
- Every physical match enters an estimate at most once; reverse orientation is derived; gaps never
  collapse into a scalar range.
- Post-ban field shares and action universe remain unchanged.
- The default archetype table renders informative estimates for active supported rows even when
  none are proof-grounded, with exact evidence/provenance/refusal labels.
- A current-corpus before/after utility audit quantifies active-row estimate coverage, direct match
  recovery, affected/unaffected edge behavior, and any authority change.

## Design decisions

- **Exposure-boundary authority is explicit and typed.** The localized-ban seam may not infer its
  exclusion gap from one incidental scalar date. The system needs a reusable exposure-boundary
  authority that records, per banned card and entity, the clean pre-exposure upper bound, the
  contaminated exposure interval, the post-ban lower bound, and provenance for how each bound was
  chosen. Because the cards dimension does not currently carry release dates, the authority must
  support deterministic sources such as authoritative card release metadata when available and
  corpus-first-seen / first-material-adoption fallbacks when not. The forcing Fantasticar case
  therefore remains `2026-06-20` through `2026-08-10`, but the implementation must generalize to
  later localized bans rather than hard-coding that one span.
- **Field clocks and matchup evidence clocks stay separate end to end.** The current field answer
  remains “what is being played after the ban today,” so the ranking share logic keeps the existing
  post-ban current/transition-field behavior. Matchup evidence instead flows from exact pairwise
  clean-interval selection. No report code may widen or reset pair evidence just because the field
  clock starts at the latest ban boundary.
- **Localized contamination is pair- and entity-specific, not global.** Unaffected subject/opponent
  pairs keep compatible certified history across the ban boundary. Affected edges exclude only the
  contaminated exposure interval for the materially affected entity or entities involved in that
  edge. If both sides are affected, the selected history is the exact intersection of their clean
  intervals, preserving every positive gap explicitly rather than collapsing to one scalar
  `since`.
- **Pre-exposure and post-ban evidence are both admissible when clean.** For a materially affected
  entity, the localized authority may admit certified clean history before card release or before
  deterministic first material adoption, then a gap over the exposure interval, then current/post-
  ban evidence after the ban boundary. The clean pre-exposure interval is not a “legacy fallback”;
  it becomes part of the exact expanded interval set and must remain inspectable in the selected
  component ledger.
- **One physical match, one orientation authority, zero double counting.** The recurrent-evidence
  epic’s one-orientation selected-outcome ledger remains the only selection seam. Reverse
  orientation is still derived. Localized contamination gaps may change which components are
  admissible, but they may not reintroduce duplicate physical matches, history/prior overlap, or a
  donor/direct double count in amplified views.
- **Parent history never silently authorizes camps.** Parent archetype interval recovery can widen
  parent evidence, but camps stay current-only unless they have their own independently supported
  localized-clean interval authority. Localized recovery may still inform a camp’s borrowed
  structure through the existing amplification/report contracts, yet a camp cannot inherit parent
  direct history observations.
- **Normal refresh activation must not depend on manual exact ids.** The generated Best Deck / Best
  Call report should automatically use the exact current-corpus recurrent evidence artifacts that
  correspond to the frozen current cutoff when they are present and valid. Normal scheduled/manual
  refreshes may not require an operator to hand-supply certificate or amplification run ids for the
  localized-ban usefulness case. The activation rule must still refuse mismatched artifacts loudly,
  preserve the existing authority payload, and avoid any `latest winner` or silent production
  promotion behavior.
- **Best estimate is visible by default; provenance and proof stay separate.** The archetype table
  should surface the best available current estimate for active supported rows using the existing
  table/disclosure patterns. Direct/history/borrowed provenance, confidence, refusal state, and
  proof-grade status remain separately labeled, filterable, and auditable. A row may be useful
  without being proof-grounded, but it may never be visually upgraded into validated authority by
  omission of those labels.
- **Utility is measured against the current degraded state, not assumed.** On Monday, August 17,
  2026, the scheduled refresh status is degraded because the ranking reports `0/50` proof-grade-
  grounded supported rows. This feature’s success bar is not “some extra matches”: it must publish a
  before/after audit for the current corpus that names recovered active-row estimates, recovered
  direct match cells, unaffected-pair retention, affected-edge exclusions, and any authority or
  usefulness status change. The forcing corpus has 16 materially affected parent archetypes at the
  Fantasticar ban boundary, with Doomsday, Blue Artifacts, Dimir Midrange, TES, and Mystic Forge
  Combo accounting for most exposure volume; the design and tests should target that real shape.

## Mockups

Skipped. This feature reuses the existing archetype table, evidence disclosures, chips, and
methodology/audit composition. The needed UI change is hierarchy and copy inside established
patterns, not a new screen or primitive, so a standalone mock would duplicate the accepted surface
instead of resolving an open taste decision.

## Directional only-questions pass

- Does a localized ban reset all matchup evidence? **No** — only edges touching materially affected
  entities lose the contaminated exposure interval.
- Can an affected edge recover pre-exposure history? **Yes** — if the interval is deterministically
  clean and still pairwise compatible after exact intersection.
- Do camps inherit that recovered parent direct history? **No** — camps remain current-only unless
  independently supported.
- Can the report show useful estimates when none are proof-grounded? **Yes** — that is the explicit
  usefulness goal, but the proof/provenance labels remain separate and visible.
- Should the normal refresh require a human to pass exact recurrent run ids? **No** — exact current
  artifacts should resolve automatically when available and validated.
- Is a new mockup or unresolved taste choice blocking design? **No** — existing table/disclosure
  patterns and the feature brief fix the composition.

## Other agent review

- Invoked because: this feature crosses recurrent evidence authority, current refresh activation,
  and published usefulness semantics.
- Skipped/degraded: the current assignment prohibits nested agents, so no peer design pass was run.
- Receiver judgment: accepted research, the closed recurrent-evidence contracts, and the current
  degraded Fantasticar corpus provide enough grounding to proceed directly to implementation.

## Architectural choice

Three shapes were considered. A global post-ban reset would be simple, but it reproduces the exact
failure this feature exists to undo by erasing unrelated useful evidence. A scalar “ban-scoped
fallback” per row would recover some estimates, but it cannot represent clean pre-exposure plus
post-ban unions without hiding contamination gaps or risking duplicate selection. The chosen design
is to add one explicit exposure-boundary authority that feeds generalized clean-interval atoms into
the existing recurrent interval selector and publication contracts.

That keeps the code honest in two ways. First, interval geometry stays inside one proven exact
selection seam instead of being reimplemented in the report generator. Second, current usefulness
publication stays additive: the ranking authority and production recommendation logic remain intact,
while the report’s first-read table can become useful again by rendering the best available row
estimate with exact provenance and proof status beside it.

The highest-risk seam is automatic current refresh activation. The generator already supports exact
targeted evidence bundles, but the normal current report path still revolves around field clocks and
manual/typed target plumbing. This feature must add an exact-current evidence resolution boundary
that finds the matching current recurrent artifacts, validates them against the frozen current
cutoff/corpus, and attaches them without changing authority bytes. The second risk is contamination
geometry: exposure boundaries must stay explicit, deterministic, and inspectable so affected edges
exclude exactly the intended gap and unaffected edges stay untouched.

## Implementation Units

### Unit 1: Exposure-boundary authority and localized clean-interval atoms

**Files**: `src/legacy_engine/analytics/affectedness.py`,
`src/legacy_engine/analytics/eras/consume.py`,
`src/legacy_engine/analytics/match_results.py`,
`tests/analytics/eras/test_interval_consumption.py`,
`tests/test_match_results.py`
**Story**: `feature-ban-localized-evidence-recovery-exposure-authority`

Add a typed exposure-boundary authority that, for each materially affected entity/card pair,
captures:

- the banned card id/name and ban date,
- the clean pre-exposure upper bound,
- the contaminated exposure interval `[exposure_start, ban_date)`,
- the clean post-ban lower bound,
- and deterministic provenance (`released-at`, `corpus-first-seen`, `first-material-adoption`,
  `confirmed-ban`, or future equivalent extensions).

Then compile that authority into exact clean-interval atoms for entity eligibility so affected
entities contribute `pre-exposure` plus `post-ban` clean components instead of one scalar
post-ban-only horizon.

**Acceptance criteria**:

- [x] Fantasticar-aware parent entities can represent clean history before `2026-06-20`, an exact
  excluded exposure gap through `2026-08-10`, and post-ban evidence after `2026-08-10`.
- [x] Unaffected entities continue to expose their certified/current intervals unchanged.
- [x] Intersection remains exact and gap-preserving; no adjacent clean spans separated by a positive
  exposure gap are merged.
- [x] Reverse-orientation selection stays derived from one physical selected match set.
- [x] Missing release metadata degrades to deterministic fallback provenance rather than a silent
  fabricated bound.

### Unit 2: Pairwise localized selection, report evidence views, and camp/current-only protection

**Files**: `src/legacy_engine/analytics/matchup.py`,
`src/legacy_engine/advisory/best_call_evidence.py`,
`tests/analytics/amplification/test_best_call_evidence.py`,
`tests/test_refresh_best_call_ranking.py`
**Story**: `feature-ban-localized-evidence-recovery-pair-selection`

Thread the localized clean-interval authority through the interval matrix and evidence projection so
unaffected parent pairs keep compatible history, affected parent pairs exclude only contaminated
intervals, and camps retain the established `camp-current-only` direct-evidence behavior.

**Acceptance criteria**:

- [x] Parent evidence views distinguish unaffected retention from affected-edge recovery/exclusion on
  the same current report.
- [x] Added-history views include clean pre-exposure rows when compatible, not only post-ban rows.
- [x] Parent/camp parity rules hold: camps do not inherit direct parent history observations.
- [x] History/prior/donor roles remain non-overlapping under localized recovery.
- [x] The exact evidence ledger stays inspectable per component with explicit localized-gap
  provenance.

### Unit 3: Automatic current-refresh evidence activation and utility-first table publication

**Files**: `scripts/refresh_best_call_ranking.py`,
`src/legacy_engine/workflows/decision_refresh.py`,
`src/legacy_engine/ops/status.py`,
`tests/test_refresh_best_call_ranking.py`,
`tests/test_decision_refresh.py`,
`tests/test_ops_status.py`
**Story**: `feature-ban-localized-evidence-recovery-refresh-publication`

Add the normal-refresh resolver for exact current recurrent evidence artifacts and update the
generated page/status publication so the default archetype table shows the best available current
estimate with separate provenance/confidence/proof labels. This is an additive usefulness change:
the authority seal, production recommendation, and no-auto-promotion contract remain intact.

**Acceptance criteria**:

- [x] The current report path resolves matching exact current evidence automatically when present,
  and fails loudly on mismatched artifacts.
- [x] No manual certificate/amplification run id is required for the normal localized-ban current
  refresh path.
- [x] The first-read archetype table remains the single decision surface and uses existing table /
  disclosure patterns.
- [x] Proof-grade status remains visible and separate from “best estimate shown”.
- [x] Scheduled status/usefulness output reflects localized recovery honestly without claiming
  validation or promotion.

### Unit 4: Current-corpus utility audit and adversarial regression suite

**Files**: `tests/test_refresh_best_call_ranking.py`,
`tests/analytics/eras/test_interval_consumption.py`,
`tests/analytics/amplification/test_best_call_evidence.py`,
`tests/test_decision_refresh.py`,
`docs/analysis/best-call-ranking.md`
**Story**: `feature-ban-localized-evidence-recovery-utility-audit`

Capture the current-corpus before/after audit and the adversarial checks that prove the feature is
localized rather than globally permissive.

**Acceptance criteria**:

- [x] The audit records the August 17, 2026 baseline (`0/50` proof-grounded supported rows) and the
  post-change current-corpus recovery counts.
- [x] Tests cover unaffected pairs retaining history across the Fantasticar ban boundary.
- [x] Tests cover affected edges excluding exactly the Fantasticar exposure interval while admitting
  clean pre-exposure plus post-ban rows.
- [x] Tests cover no duplicate physical-match selection, no scalarized gap collapse, and no camp
  history inheritance.
- [x] Tests cover artifact auto-resolution/mismatch refusal and utility/status publication honesty.

## Implementation order

1. `feature-ban-localized-evidence-recovery-exposure-authority`
2. `feature-ban-localized-evidence-recovery-pair-selection`
3. `feature-ban-localized-evidence-recovery-refresh-publication`
4. `feature-ban-localized-evidence-recovery-utility-audit`

## Testing

- Hermetic interval-selection tests for explicit exposure boundaries, gap preservation, one-
  orientation match selection, and camp current-only behavior.
- Current-report integration tests for unaffected-pair retention, affected-edge clean-pre-exposure
  recovery, and exact evidence ledger publication.
- Refresh/status tests for automatic current-artifact resolution, mismatch refusal, usefulness
  status changes, and authority-payload invariance.
- Utility-audit assertions pinned to the live forcing corpus shape: 16 materially affected
  archetypes at the Fantasticar boundary, with Doomsday, Blue Artifacts, Dimir Midrange, TES, and
  Mystic Forge Combo as the dominant exposure-volume cases.

## Risks

- The release-date authority is partially outside the current cards table, so the exposure-boundary
  seam must avoid creating a second hidden source of truth or a silent guessed date.
- Automatic current-artifact resolution can easily drift into an unsafe “latest” alias if the
  lookup contract is not exact about cutoff/corpus compatibility.
- Utility-first publication can accidentally blur diagnostic usefulness into authority if proof and
  provenance labels are not kept visibly separate on the first-read surface.
- Localized pair recovery increases interval complexity, so tests must attack duplicate selection,
  gap collapse, donor/direct overlap, and unaffected-pair regressions directly.

## Implementation result

All four units are implemented. Current field authority remains post-ban, while typed pair evidence
uses explicit localized clean interval unions. The normal current refresh needs no manual run ids
and works without certification/amplification tables; exact artifacts remain optional fail-closed
enrichment. Camps remain current-only. The mature authority payload is digest-invariant before and
after diagnostic attachment.

The default archetype table now shows a covered-field direct matchup estimate, direct sample,
estimated-cell/field coverage, recovered clean-history sample, provenance, confidence, and proof
state separately. The full typed pair surface remains available to library/store consumers. The
offline HTML publishes only four highest-share opponent ledgers per supported row, uses counts and
digests in place of raw match-id arrays, and omits the duplicated global pair universe.

On the live corpus through August 16, 2026, the corrected report recovers estimates for 50/50
supported rows across 2,716 cells using 9,949 unique clean-history physical matches.
Observation-based provenance distinguishes 745 cells with actually selected localized history from
1,971 current/certified cells. Proof stays 0/50, so `proof_grade_call` is null while the practical
diagnostic call remains separately labeled. The final self-contained report is 38,637,569 bytes,
close to the prior roughly 34MB output and 90% smaller than the rejected full-pair draft.

## Verification

- Focused localized evidence, report projection, workflow, and status tests: 110 passed.
- Full repository suite: 4,002 passed, 1 skipped.
- Live generation: field 197 since 2026-08-10; corpus max 2026-08-16; 95 parent + 106 camp rows.
- Live HTML JavaScript syntax/load parse: passed.
- Knowledge-index regeneration/lint: 0 errors (six pre-existing/document-size warnings).
- Performance: one resolver call per ledger with exact reference parity; controlled parent/camp
  interval benchmark 59.2s combined. Final run: exact intervals 61.6s, compact projection 5.8s,
  serialization/atomic write 0.3s.

## Review correction — 2026-08-16

The independent review requested changes before approval:

- derive fallback exposure from the banned-card/cohort's global corpus-first-seen date so every
  materially affected entity shares the exact Fantasticar contamination gap;
- bound recovered pre-exposure history by the previous confirmed-ban regime, without allowing a
  later stored horizon to erase clean pre-history;
- classify localized/certified/current provenance from selected added observations rather than
  eligible interval geometry;
- enforce `proof_grade_call` as null whenever no grounded row exists; and
- recompute the live utility audit and its affected/unaffected counts after those corrections.

All review blockers were corrected. Every one of the 16 live Fantasticar authorities now uses the
global `[2026-06-20, 2026-08-10)` gap and typed 2026-05-18 prior-regime lower bound. Doomsday, TES,
and Mystic Forge Combo retain clean pre atoms; Mystic Forge's later Fantasticar-pre interval remains
excluded where the older Candelabra contamination gap overlaps it. The production ledger validator
confirmed zero expanded observations inside any typed localized gap during final generation.
