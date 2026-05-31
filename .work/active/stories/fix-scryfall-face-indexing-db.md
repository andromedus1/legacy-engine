---
id: fix-scryfall-face-indexing-db
kind: story
stage: done
tags: [ingestion, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-31
updated: 2026-05-31
---

# Fix: DuckDB cards table misses multi-face front-face names

## Brief
Discovered while refreshing card data (2026-05-31): multi-face cards (transform DFC, adventure,
split, MDFC) are stored in the DuckDB `cards` table ONLY under their combined `A // B` name, so
front-face lookups by the name decklists actually use (`Tamiyo, Inquisitive Student`,
`Brazen Borrower`) miss. The in-memory `scryfall.load_card_index` DOES face-index (scryfall.py:117-126),
but `store.load_cards` (store.py:84) inserts one row per combined `name` only, and `seed cards` dedupes
by full name (cli.py:59) — so faces never reach the DB the advisory/generation code queries. Real impact:
`Tamiyo, Inquisitive Student` is a 4-of in current Dimir Tempo → `whattoplay`/tuning emit "unknown card".

## Fix
`store.load_cards`: after inserting full-name rows (INSERT OR REPLACE), also insert face-alias rows from
`name.split(" // ")` via INSERT OR IGNORE (mapped to the combined card's attributes — parity with the
in-memory index; IGNORE so a genuine standalone card with that name is never clobbered, and real cards are
inserted first). Then re-run `seed cards` to re-index. Test: a deck/adventure card loaded under `A // B`
resolves by both `A` and `B` and by `A // B`; a standalone card sharing a face name is not overwritten.

## Resolution (2026-05-31)
Fixed in `store.load_cards` (face-alias rows via INSERT OR IGNORE after the full-name pass). 3 regression
tests in `tests/test_store.py::TestFaceAliases` (front/back/combined resolve; alias never clobbers a real
standalone card). Re-ran `seed cards` → `Tamiyo, Inquisitive Student`, `Brazen Borrower`, `Petty Theft` all
resolve; `generate tune` on real Dimir Tempo no longer emits "unknown card". Suite 964 green.
Follow-up nice-to-have (NOT done): transform-DFC top-level `colors` is empty in the Scryfall oracle pool
(colors live on `card_faces`), so the front-face alias inherits empty colors — deck-color computation is
unaffected in practice (other sources), but per-face attribute extraction would be more faithful.
