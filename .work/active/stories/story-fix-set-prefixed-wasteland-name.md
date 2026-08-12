---
id: story-fix-set-prefixed-wasteland-name
kind: story
stage: review
tags: [bug, ingestion, cards, benchmark]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Resolve the verified set-prefixed Wasteland name

## Symptom

After the historical Goblin repair allowed six benchmark folds to run, the unchanged protocol
failed snapshot closure at fold `2025-04-28--2025-05-26` with `snapshot has 1 deck-card rows
without observed card metadata`.

## Root cause

The mirrored MTGmelee JSON preserves `[TMP] Wasteland` verbatim in `Decks[5].Sideboard[14].CardName`
for paper event 212627 on 2025-04-06. `TMP` is the set/edition code for Tempest, embedded by that
provider/export in the card-name field; Scryfall's canonical Oracle card is `Wasteland` under
oracle id `09a70ae8-3859-4a09-901d-dce063fa3b5f`. Generic name reconciliation correctly does not
strip arbitrary bracketed prefixes, so this exact provider spelling remains unresolved.

## Fix approach

Add the one verified raw spelling to the existing evidence-bearing provider alias registry. Reuse
the current loader and reconciliation logic, which requires the canonical Scryfall target to exist
before updating derived deck-card names. Do not create generic bracket stripping, a placeholder
card, or any raw-cache/source-DB/protocol mutation.

## Regression test

`tests/test_card_name_resolution.py` seeds the authoritative `Wasteland` card and the exact
`[TMP] Wasteland` sideboard spelling, then requires exact reconciliation and zero unresolved gaps.
Before the fix it fails because the observed provider name is retained.

## Reproduction evidence

- Raw path: `data/cache/Tournaments/MTGmelee/2025/04/06/8-tappa-tigullio-legacy-league-by-kryptalegacy-212627-2025-04-06.json`.
- Partial benchmark summary artifact:
  `c51ca0acdd12f20d97ad90ce77d6885b7c7df6557112911bae10d3838098702e` under unchanged protocol
  `6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561`.
- Focused regression reproduced the unresolved `[TMP] Wasteland` value on 2026-08-12.

## Implementation notes

- Execution capability: direct focused implementation in the current frontier worker. The verified
  defect is one exact provider spelling at the already-reviewed alias boundary.
- Changed only the package-shipped provider alias registry, its card-name regression, and this story.
  No generic bracket-prefix behavior was introduced.
- The existing alias loader continues to require provider, Oracle id, and evidence, and
  reconciliation continues to fail if `Wasteland` is absent from the authoritative card dimension.
- Four-step confirmation: focused regression passes; affected suite passes (`31 passed`); full suite
  passes (`3802 passed, 1 skipped`); a fresh ignored byte-copy reconciled through the normal CLI has
  zero metadata orphans through the previously failing 2025-04-28 cutoff (locked source had 616).
  The raw cache, `data/legacy.duckdb`, and protocol remain unchanged.
- The exact unchanged benchmark replay follows from the committed code revision in a new immutable
  artifact directory. Any independently unresolved later name remains outside this fix.
