---
id: epic-recurrent-stable-era-evidence-best-call-integration-review-corrections
kind: story
stage: implementing
tags: [analytics, advisory, ui, testing]
parent: epic-recurrent-stable-era-evidence-best-call-integration
depends_on:
  - epic-recurrent-stable-era-evidence-best-call-integration-page-composition
release_binding: null
gate_origin: review
created: 2026-08-16
updated: 2026-08-16
---

# Complete and harden Best Call evidence publication

## Brief

Resolve every blocker from the standard review of frozen commit `14fe333`. Wire the typed evidence
projection and historical target model into the actual generated report, fail closed on artifact
identity, eliminate post-cutoff leakage, publish bundles atomically and safely, and add the missing
acceptance tests and runbook updates.

## Required corrections

- Compose exact interval/amplification evidence into `generate_ranking`, call the public validator,
  require the exact run/clock/certificate/profile/registry/pair/baseline identities, preserve
  degraded/refusal reasons and match digests, derive inspectable interval components, and prove the
  authority payload is byte-stable before/after attachment.
- Bound every target-dependent SQL query and derived regime/ban selection by the exclusive cutoff;
  make `ReportTarget` enforce current and retrospective semantics and emit a max-date/digest audit.
- Render the direct views and six named challenger diagnostics in the existing page patterns,
  including camp-current-only semantics, unavailable/refused reasons, decomposition/concentration,
  admitted intervals, visible `Today’s model`, keyboard-accessible target navigation, and scoped
  progressive disclosure without changing ranking authority.
- Stage all target pages plus manifest before atomically replacing final artifacts, preserve the
  last-good bundle on any failure, give each page its correct selected target, represent unavailable
  targets honestly, remove wall-clock nondeterminism, and escape JSON/script-hostile labels.
- Add end-to-end exact-run/tamper/degraded, authority-byte, post-cutoff mutation, historical ban,
  target invariant, camp parity, bundle failure/determinism, DOM/JS/accessibility, hostile-text, and
  regression tests. Update the Best Call refresh runbook to the shipped contract.

## Acceptance

- Every blocker in the parent feature's standard-review findings has a direct regression test.
- A current report with an exact valid run shows frozen diagnostics while producing the same
  authoritative ranking payload and order as the no-evidence path.
- A retrospective page is invariant to all post-cutoff tournament mutations and labels its weaker
  `Today’s model` claim without implying `As known then`.
- Invalid evidence fails before publication; valid degraded or unavailable evidence renders typed
  reasons; bundle failure preserves every prior canonical artifact.
- Existing ranking, matchup, camp, interval, and amplification regression suites remain green.
