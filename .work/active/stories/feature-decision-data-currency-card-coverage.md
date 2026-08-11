---
id: feature-decision-data-currency-card-coverage
kind: story
stage: done
tags: [ingestion, analytics]
parent: feature-decision-data-currency
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Resolve exact card aliases and report card-dimension coverage

## Brief

Stream Scryfall's compressed every-language card artifact into an exact localized-alias index with
collision/provenance data, canonicalize only uniquely earned mappings, recognize oracle-refresh
new-card recoveries, and replace warning noise on the decision-refresh path with a compact typed
coverage report that keeps ambiguous, suspected-truncated, and unresolved gaps visible.

## Implementation

Implement Units 2 and 3 in the parent feature's `## Implementation Units` section. Neither the
current `oracle_cards` mirror, the sparse-language `default_cards` price bulk, nor Scryfall's exact
name endpoint resolves the observed localized spellings. Do not substitute fuzzy matching or mutate
price tables.

## Implementation notes

- Execution capability: frontier/high; the external every-language bulk contract, transactional
  derived cache, and silent data-rewrite risk warranted the caller-selected strongest worker.
- Review weight: standard (caller).
- Files changed: `src/legacy_engine/config.py`, `src/legacy_engine/models/card.py`,
  `src/legacy_engine/ingestion/scryfall.py`, `src/legacy_engine/ingestion/store.py`,
  `src/legacy_engine/ingestion/card_coverage.py`, `src/legacy_engine/cli.py`,
  `tests/test_card_name_resolution.py`, and `tests/test_card_coverage_cli.py`.
- Tests added: seven hermetic tests covering JSONL-gzip streaming, alias-key normalization,
  collision preservation, manifest cadence, unique/new/ambiguous/truncated reconciliation,
  explicit empty coverage, and the file-backed CLI audit surface.
- Simplification: one exact resolution transaction and one typed summary replace per-name warning
  interpretation on this path; no fuzzy or targeted-network fallback was added.
- Discrepancies from design: the all-cards iterator accepts both provider JSON arrays and compact
  JSONL gzip fixtures; this broadens the parser boundary without changing resolution semantics.
- Adjacent issues parked: none.

## Verification

- `.venv/bin/python -m pytest -q tests/test_card_name_resolution.py tests/test_card_coverage_cli.py`
  — 7 passed.
