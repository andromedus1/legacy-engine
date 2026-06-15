---
id: fix-scryfall-face-indexing-db
kind: story
stage: done
tags: [ingestion, bug]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-31
updated: 2026-06-14
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

## Layout-aware extension (2026-05-31, prompted by the maintainer)
the maintainer flagged that crude combined-attribute aliasing is wrong for multi-face cards ("you play the front,
then trigger the back"). Reworked `load_cards` to be LAYOUT-AWARE: face rows carry the FACE's own
type/cmc/power/toughness; colors = front-face's own for front-cast layouts (transform/flip/meld — you only
pay the front; the back is reached in play) vs UNION color identity for both-castable layouts
(adventure/split/modal_dfc); modal-DFC with a land face is land-capable under its front name; the combined
A//B row gets the union identity (no more empty-colored DFCs). Also: (1) `seed cards` now `rebuild()`s the
table so re-seeds are a clean refresh (INSERT OR IGNORE aliases couldn't otherwise be refreshed — stale
rows persisted); (2) non-gameplay layouts (art_series/token/emblem/…) are excluded from aliasing (the Tamiyo
art_series card was shadowing the real transform front face with empty attrs). Verified on real DB: Tamiyo,
Inquisitive Student → colors=U, power=0, front-face type; Brazen Borrower → colors=U, power=3. 968 tests.
MDFC is_land call (land-capable if any face is a land) per the maintainer's chosen option — flag if you want it
narrower.
