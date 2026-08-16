---
id: epic-recurrent-stable-era-evidence
kind: epic
stage: done
tags: [analytics, advisory, testing, ui]
parent: null
depends_on: [feature-ranking-measurement-integrity, feature-ranking-credible-window-utility, feature-ranking-future-only-benchmark]
release_binding: null
gate_origin: null
research_origin: recurrent-era-intervals
created: 2026-08-13
updated: 2026-08-16
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

## Design decisions

<!-- captured 2026-08-16 via research-pipeline:epic-design --only-questions -->

- **First certification surface:** certify parent archetypes first; camps remain current-only until
  their own independent support clears the certificate gates. Parent certificates never silently
  stand in for camp equivalence.
- **Delivery priority:** recover and expose useful evidence in the current report before adding the
  broader retrospective `Today’s model` historical selector; both remain in this epic, with the
  historical target following the current-report integration.
- **Primary recurrence method:** begin with the inspectable outcome-firewalled segment/fingerprint
  method. Sticky-state and other latent-state methods remain explicit benchmark challengers rather
  than production complexity included by default.
- **Success objective:** maximize useful coverage subject to non-degradation in future calibration,
  proper scores, and decision regret. Raw added match count, narrower intervals, and a larger number
  of grounded labels are not sufficient success criteria.
- **Automation authority:** deterministic discovery and certification rebuild automatically from
  objective gates; changing calibration/configuration, confirming format truth, or promoting a
  methodology remains an operator decision.
- **Offensive evidence lane:** pair recurrent-history recovery with structured evidence amplification
  challengers—hierarchical partial pooling, composition-aware borrowing, multi-resolution priors,
  and low-rank matchup structure—that try to improve future predictions from the same corpus. Every
  estimate must decompose direct, certified-historical, and structurally borrowed contribution, and
  only future-only evidence can promote an amplified method.

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

## Decomposition

The epic is split by evidence capability rather than technical layer. Outcome-firewalled discovery
produces candidates for independent certification; certified interval sets become the single
eligibility seam; structured amplification then challenges the direct-evidence estimator. The report
and future-only benchmark consume those shared contracts independently, so diagnostic publication
does not wait for promotion and validation never depends on presentation code.

### Child features

- `epic-recurrent-stable-era-evidence-discovery` — build outcome-firewalled segment fingerprints and
  nominate recurrent parent-archetype states — depends on: `[]`
- `epic-recurrent-stable-era-evidence-certification` — independently certify, reject, or abstain on
  nominated reunions and persist versioned certificate artifacts — depends on:
  `[epic-recurrent-stable-era-evidence-discovery]`
- `epic-recurrent-stable-era-evidence-interval-consumption` — intersect subject/opponent interval
  unions exactly and expose current, expanded, and added-history evidence — depends on:
  `[epic-recurrent-stable-era-evidence-certification]`
- `epic-recurrent-stable-era-evidence-amplification` — evaluate transparent hierarchical,
  composition-aware, multi-resolution, and low-rank borrowing challengers — depends on:
  `[epic-recurrent-stable-era-evidence-interval-consumption]`
- `epic-recurrent-stable-era-evidence-best-call-integration` — publish decomposed diagnostic evidence
  and retrospective `Today’s model` targets in the generated Best Call page — depends on:
  `[epic-recurrent-stable-era-evidence-amplification]`
- `epic-recurrent-stable-era-evidence-future-validation` — refit every method at historical cutoffs,
  compare challengers, and enforce promotion policy — depends on:
  `[epic-recurrent-stable-era-evidence-amplification]`

### Decomposition risks

- The current series schema carries wins/losses, so the discovery feature must make the outcome
  firewall structural rather than relying on callers to ignore fields.
- Sparse independent event partitions may leave most reunion candidates inconclusive. That is an
  acceptable honest result, but calibration must distinguish an underpowered method from a broken
  implementation.
- Exact disjoint intervals invalidate the current one-scan-per-scalar-date batching assumption;
  interval eligibility must remain exact before any performance optimization is earned.
- Historical matches admitted as observations cannot also feed the existing pre-disturbance prior.
  The consumption/amplification boundary must prevent that double count explicitly.
- Parent certificates cannot be inherited as camp certificates. Camps remain current-only until
  independently supported.
- `data_until` must reach ranking construction and certificate lookup, not exist only as a browser
  filter. `knowledge_as_of` remains a separate future contract and may not be implied by the first
  retrospective selector.
- No new screen mock is required at epic design: the report extends the existing generated page's
  dropdown, chip, disclosure, and audit patterns. Feature design should mock only if the historical
  target composition proves materially ambiguous.

## Implementation summary

All six child features are complete and individually reviewed:

- outcome-firewalled weekly segmentation and recurrent candidate discovery;
- independent event-partitioned positive-equivalence certification with immutable exact artifacts;
- provenance-preserving disjoint interval selection and current/expanded/added evidence views;
- six transparent structured-borrowing challengers with aligned draw and decomposition ledgers;
- diagnostic-only Best Call publication plus cutoff-exact retrospective `Today’s model` bundles;
  and
- preregistered cutoff-local future validation with proper scores, event-block regret, exhaustive
  promotion statuses, content-addressed artifacts, and no automatic promotion actuator.

The standard feature reviews found and drove substantial corrections rather than rubber-stamping
the first implementations: exact change-point boundaries and distribution metrics, certification
bootstrap/semantic integrity, canonical one-orientation interval ledgers, real challenger fits,
complete report composition/cutoff safety, and executable future-validation gates. The final full
repository verification is `3,982 passed, 1 skipped`; the combined corrected acceptance surface is
`95 passed`. Only the pre-existing uncommitted `uv.lock` remains outside the epic.

## Aggregate review

Approved with no material findings. A fresh reviewer traced the complete methodology arc from the
structural discovery firewall through independent certification, exact pairwise interval authority,
one-orientation selected outcomes, non-overlapping direct/history/prior roles, camp current-only
semantics, differentiated amplification fits and aligned draws, exact-run diagnostic publication,
authority sealing, retrospective cutoff invariance, and cutoff-local future scoring/regret/gating.
The review confirmed that promotion remains an inert operator proposal and that no latest alias or
automatic production actuator exists. Its targeted adversarial/integration slice passed
`139 tests in 11.54s`.
