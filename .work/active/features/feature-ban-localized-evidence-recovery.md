---
id: feature-ban-localized-evidence-recovery
kind: feature
stage: drafting
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
