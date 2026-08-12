---
id: story-fix-missing-goblin-card-metadata
kind: story
stage: done
tags: [bug, ingestion, cards, benchmark]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-12
---

# Resolve the verified historical Goblin card name

## Symptom

The unchanged benchmark protocol fails snapshot closure before its first frozen prediction with
`snapshot has 615 deck-card rows without observed card metadata`. All affected rows are the raw
tournament-provider spelling `_____ Goblin` across 615 pre-cutoff decks.

## Root cause

The mirrored tournament source uses the historical five-underscore English spelling, while the
current Scryfall oracle bulk identifies the same Unfinity card as `________ Goblin` under oracle id
`88222fd2-8316-426c-8218-64f6be5ca0f8`. Scryfall's printed/localized alias feed does not carry the
historical English spelling, and generic normalized-name matching correctly treats different
underscore counts as different names. Consequently the exact reconciliation step leaves the raw
provider spelling unresolved even though its authoritative canonical card exists.

## Fix approach

Add one package-shipped, evidence-bearing provider-name alias and consume it through the existing
card-dimension reconciliation boundary. Validate that its canonical target exists in the current
card dimension before applying it. Keep the provider cache immutable, preserve Scryfall as the card
metadata authority, and rebuild only the derived `deck_cards` names through the normal reconciliation
command. Do not add a placeholder card row or weaken snapshot closure.

## Regression test

`tests/test_card_name_resolution.py` seeds the canonical eight-underscore Scryfall card plus the
five-underscore observed provider name and requires reconciliation to update the derived deck-card
name with zero unresolved gaps. Before the fix it fails because the observed name remains unchanged.

## Reproduction evidence

- Locked protocol: `6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561`.
- Original current-corpus run: canonical status `not-evaluable`, stopped at fold
  `2024-12-16--2025-01-13` with 615 orphan rows.
- Focused failing regression reproduced on 2026-08-11 with the observed name remaining
  `_____ Goblin` rather than resolving to `________ Goblin`.

## Implementation notes

- Execution capability: direct focused implementation in the current frontier worker. The defect is
  one reconciliation boundary with a known corpus reproduction; additional delegation would add
  handoff cost without independent breadth.
- Changed `ingestion/card_coverage.py`, `config.py`, and the package-shipped
  `data/card_name_aliases/legacy.json`; added regressions in `tests/test_card_name_resolution.py`.
- The curated entry records provider, canonical Oracle id, and WotC evidence. Its loader validates
  complete provenance and duplicate/self mappings. Reconciliation applies the alias only when the
  Scryfall canonical target already exists in `cards`; otherwise it fails loudly.
- Regression confirmation: the focused test failed before implementation and the complete card-name
  suite passes (`14 passed`). Affected card-coverage/refresh/benchmark suites pass (`30 passed`).
  Full repository verification passes (`3715 passed, 1 skipped`). Ruff and diff checks pass.
- Original reproduction on an ignored byte copy of the locked corpus, followed by the normal
  `refresh card-coverage` command, reduces pre-2024-12-16 card-metadata orphans from 615 to 0. The
  raw provider cache, `data/legacy.duckdb`, and frozen benchmark protocol remain unchanged.
- Adjacent corpus-name gaps after the first cutoff are not bundled. The unchanged 24-fold benchmark
  will reveal whether any independently unresolved later names block subsequent folds; its result
  will be preserved without widening this fix or tuning the protocol.

## Bounded inline review (2026-08-12)

Verdict: pass, with no findings. The repair adds one evidence-bearing exact historical spelling,
requires its canonical Scryfall target to exist, and preserves the raw cache and locked corpus. The
regression exercises the production reconciliation seam, and focused, affected, and full-suite
verification are green. Broader provider serialization and later metadata gaps remain outside this
standalone fix and are tracked separately.
