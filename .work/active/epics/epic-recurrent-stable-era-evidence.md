---
id: epic-recurrent-stable-era-evidence
kind: epic
stage: drafting
tags: [analytics, advisory, testing, ui]
parent: null
depends_on: [feature-ranking-measurement-integrity, feature-ranking-credible-window-utility, feature-ranking-future-only-benchmark]
release_binding: null
gate_origin: null
research_origin: recurrent-era-intervals
created: 2026-08-13
updated: 2026-08-13
---

# Recurrent stable-era evidence — recover compatible history without contamination

## Brief

Replace the current scalar `stable_since` consumption model with versioned, certified sets of
compatible historical intervals. The engine should recover older pockets where an archetype's deck
construction and relevant context genuinely recur, skip incompatible gaps, and admit a matchup only
where the focal and opponent archetypes' certified interval sets overlap. This expands usable data
without selecting history because it produces a favorable matchup result.

The capability arc has four natural design seams for epic decomposition: outcome-firewalled recurrent
state discovery; independent equivalence certification and certificate persistence; pairwise interval
consumption with current-only/expanded/added-history evidence views; and leakage-free chained
validation plus historical-report targets. The first historical selector mode is retrospective—old
outcome cutoffs analyzed with today's model and labeled honestly. “As known then” requires a separate
knowledge cutoff and reproducible historical versions of every derived input.

## Strategic decisions

- **Discovery cannot see outcomes:** deck/card composition, field context, legality, taxonomy, and
  provenance may nominate recurrent pockets; matchup wins, standings, and conversion may not.
- **Equivalence is affirmative and abstention-friendly:** candidates become `certified`, `rejected`,
  or `inconclusive`; failure to detect a difference is never enough to reunite eras.
- **Bans are not blanket resets:** confirmed affectedness is a hard semantic veto for the affected
  entity, while unaffected entities may certify history across a ban boundary.
- **Both matchup sides govern eligibility:** selected matches come from the normalized intersection
  of subject and opponent certificate sets, never from a subject-only expanded window.
- **Minimum matchup n stays downstream:** interval certificates determine admissible rows; the
  existing minimum-`n` control determines whether the chosen evidence is displayed as measured.
- **Expanded evidence starts diagnostic:** current-only, expanded, and added-history estimates remain
  side by side until future-only validation supports any promotion.
- **Historical time has two axes:** `data_until` bounds outcomes and `knowledge_as_of` bounds facts,
  classifications, certificates, configuration, and derived state. The UI must never conflate them.

## UI surface

Extend the existing Best Deck / Best Call HTML page rather than introducing a new application or
visual system. Reuse its current dropdown, chip, table, disclosure, keyboard, and responsive patterns.
The historical target control offers Current and pre-ban cutoffs with a compact mode label such as
“Today's model”; detailed provenance remains progressively disclosed. Screen-level alternatives can
be mocked during epic/feature design if the interaction cannot be expressed cleanly with those
existing primitives.

## Simplification opportunity

Make normalized interval-set eligibility the single source of truth for historical match selection.
Retire duplicated scalar-window comparisons as consumers migrate; retain `stable_since` only as the
explicit current-only/no-certificate fallback, not as a permanent parallel interpretation. Reuse the
existing measurement ledger and future-only benchmark rather than building report-only estimators or
a second validation harness.

## Dependencies

- `feature-ranking-measurement-integrity` supplies pair-window provenance and concentration evidence.
- `feature-ranking-credible-window-utility` supplies affectedness clamps, transition-field honesty,
  and the current practical/proof-grade publication contract.
- `feature-ranking-future-only-benchmark` supplies frozen cutoff semantics and proper-score/regret
  evaluation. All three prerequisites are complete at scope time.

## Research grounding

**Source**: `.research/analysis/campaigns/recurrent-era-intervals/parent.md`
(slug: `recurrent-era-intervals`)

The approved campaign recommends outcome-free segmentation plus segment similarity, independent
positive-equivalence certification, pairwise interval-set intersection, concentration-aware evidence
views, and two-clock historical reporting. Its adversarial verification is approved at
`.research/analysis/campaigns/recurrent-era-intervals/verification-checklist.md`.

## Scope boundaries

- No matchup-outcome-adaptive interval discovery or borrowing weights.
- No production promotion based solely on larger `n`; chained future-only evidence is required.
- No claim that a retrospectively regenerated report is what the system knew or published then.
- No hosted service or multi-screen application; this remains a local generated-report capability.
- Child-to-parent reconstruction from surviving camps is related but remains separately parked unless
  epic design proves it is a necessary certificate-consumption case.
