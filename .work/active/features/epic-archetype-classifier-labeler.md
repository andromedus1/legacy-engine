---
id: epic-archetype-classifier-labeler
kind: feature
stage: done
tags: [archetype]
parent: epic-archetype-classifier
depends_on: [epic-archetype-classifier-matcher]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
---

# Labeler + `legacy label` CLI

## Brief
Orchestrate end-to-end labeling: read each deck from DuckDB (`decks` + `deck_cards`), resolve card
names to `Card`s via the Scryfall index, compute deck colors, `classify` against the loaded ruleset,
and persist the resulting archetype label into `decks.archetype` (the column foundations left NULL).
Wire the `legacy label` CLI. Conflict/Unknown labels are written raw. Idempotent (re-labeling
overwrites). Does NOT compute meta-share/matchups (analytics epic) — it only populates the archetype
column those will read.

## Epic context
- Parent epic: `epic-archetype-classifier`. The integration feature — ties rules-loader + matcher + the foundations card/store layers into `legacy label`.

## Inherited design decisions
- Conflict/Unknown written raw to `decks.archetype`.
- Reuse foundations: ScryfallClient index for name→Card, `compute_deck_colors`, the DuckDB store.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/parent.md` — the end-to-end pipeline (resolve → colors → classify → persist).
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — name→Card resolution + the color helper.

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/labeler.py`; the `legacy label` CLI; `decks.archetype` column.

## Implementation notes
- **Files created**: `src/legacy_engine/archetype/labeler.py` (`label_decks`, injected `resolve_card`); wired `legacy label` CLI (load_ruleset + ScryfallClient.get_card + store).
- **Tests added**: `tests/test_labeler.py` — end-to-end (load tournament → label → assert `decks.archetype`); Dimir Tempo + Unknown; idempotent relabel. Full suite **129 passing in 0.55s**.
- **Discrepancies from design**: none. `resolve_card` injected so the test runs without the Scryfall bulk.
- **Test debt fixed**: removed `label` from `test_cli`'s not-implemented list (now wired).
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `label_decks` resolves + classifies one deck at a time (fine; analytics will read the persisted column, not re-run this). Unresolved card names simply don't contribute to color computation (no crash) — consistent with the foundations unmatched-name tolerance.
**Notes**: Ties rules-loader + matcher + foundations (Card index, compute_deck_colors, DuckDB store) into `legacy label`; Conflict/Unknown written raw. Idempotent. 129 tests green. Closes archetype-classifier.
