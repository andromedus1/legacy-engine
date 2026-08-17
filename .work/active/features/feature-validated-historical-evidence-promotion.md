---
id: feature-validated-historical-evidence-promotion
kind: feature
stage: drafting
tags: [analytics, advisory, ui, testing]
parent: null
depends_on: [epic-recurrent-stable-era-evidence]
release_binding: null
gate_origin: null
research_refs:
  - .research/analysis/campaigns/recurrent-era-intervals/parent.md
created: 2026-08-17
updated: 2026-08-17
---

# Promote validated historical evidence into ranking authority

## Brief

Turn the recurrent-evidence program from a rich diagnostic into a production ranking method that can
actually learn from the historical corpus. The current report has 9,949 clean recovered physical
matches and useful direct estimates for every supported archetype, yet reports zero grounded rows
because the mature Agency path still treats the latest scalar era and raw `n >= 8` top-opponent gate
as its authority. Exact interval-expanded, composition-aware, hierarchical, and low-rank estimates
remain outside that gate even when they carry stronger admissible evidence.

Create the separately reviewed promotion capability already required by `docs/SPEC.md`. It consumes
an exact promotable future-validation assessment and inert operator proposal, binds one versioned
serving policy, and allows only the validated estimator and support rule to feed Agency, floor,
grounding, P(best), and the production recommendation. Promotion is explicit and reversible;
missing, censored, inconclusive, negative, mismatched, or stale evidence retains current-only
authority. No `latest`, implicit winner, in-sample selection, or automatic apply path is allowed.

The promoted support contract should answer “how much validated information supports this current
matchup?” rather than treating raw post-boundary match count as the only proof. It may use exact clean
direct history, effective event/component support, source concentration, calibrated predictive
uncertainty, and validated structured borrowing. Raw match `n` remains visible and the interactive
`n` control remains a useful sensitivity view, but changing browser controls never masquerades as a
new production validation result. The current coverage control must either become a real exploratory
grounding threshold or be relabeled as the row-visibility filter it is.

## Strategic decisions

- **Promotion is earned out of sample:** only a promotable chained future-validation assessment over
  identical future cases can authorize a production candidate; added matches, narrower intervals,
  or more grounded labels alone cannot.
- **One current-target estimand:** historical components inform today's matchup through an explicit
  validated model; they are not blindly pooled as if time and deck composition had not changed.
- **Exact eligibility remains upstream authority:** subject/opponent interval intersection and hard
  affectedness gaps decide which physical outcomes may enter. Promotion changes estimation and
  support, never contamination rules.
- **Support replaces the raw-count cliff, not transparency:** production support combines validated
  uncertainty with effective event/component/source diversity. Raw `n`, admitted intervals,
  current/history/borrowed decomposition, and refusal reasons stay visible.
- **Operator-controlled and rollback-safe:** an operator selects an exact promotable proposal and a
  versioned serving configuration. The prior current-only policy remains a deterministic fallback
  and rollback target.
- **Exploration stays exploration:** table controls may recompute alternative `n` and coverage views,
  but P(best), evidence strata, and authority-dependent labels must become unavailable or explicitly
  stale whenever the browser state differs from the promoted configuration.

## Outcome boundary

The feature is complete when a promotion candidate can travel from its immutable validation bundle
through an explicit operator selection into the ranking composition root, and the generated report
can prove which serving policy produced every authoritative cell and call. Acceptance must include:

- current-only, recurrent-expanded, and amplified candidates evaluated on the same frozen future
  cases with proper scores, calibration, served/fallback accounting, and whole-event decision regret;
- a fail-closed promotion read that binds assessment, proposal, estimator registry, profile,
  interval corpus, clocks, code/config hashes, support policy, and rollback identity;
- an uncertainty- and concentration-aware support decision with no double counting of current,
  historical, reverse-orientation, prior, or borrowed observations;
- end-to-end Agency, floor, grounding, P(best), ordering, recommendation, and report provenance from
  the selected policy, while non-promoted and exploratory views remain clearly labeled;
- historical-origin and current-report regression tests proving post-cutoff mutation resistance,
  negative-transfer refusal, current-only parity/fallback, and deterministic rollback; and
- a live utility audit that reports both usefulness gain and validation cost. Success is improved
  validated coverage without material degradation, not a predetermined number of grounded rows.

## Existing substrate

This work consumes rather than rebuilds the completed recurrent-evidence stack:

- exact pairwise clean-interval selection and one-orientation selected-outcome ledger;
- localized exposure gaps and current/expanded/added-history decomposition;
- six typed amplification challengers with aligned draws and contribution ledgers;
- cutoff-safe recurrent origin refits, common future-case scoring, decision regret, promotion
  assessment, and inert operator proposal storage; and
- the Best Call authority digest, practical/proof separation, atomic publication, and interactive
  sensitivity controls.

## Simplification opportunity

Replace the parallel “mature scalar authority plus richer diagnostic tree” interpretation with one
versioned serving-policy registry whose current-only member preserves today's fallback exactly and
whose promoted members consume the same canonical interval corpus. Retire raw `n >= 8` as the sole
cell-authority test once a validated support policy is selected; retain raw `n` as evidence and as an
interactive sensitivity parameter. Do not add another ranking table, latest-run selector, or
template-only score.

## UI surface

This extends the existing self-contained Best Call page and its current tables, controls, chips, and
disclosures. No new screen, journey, visual language, or design-system primitive is implied at scope
time, so a mock is not required here. Feature design must resolve the smallest clear presentation for
the active serving policy, validated-support basis, current/history/borrowed decomposition, rollback
identity, and exploratory-control staleness.
