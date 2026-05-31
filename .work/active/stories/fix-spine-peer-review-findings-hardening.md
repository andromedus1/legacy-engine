---
id: fix-spine-peer-review-findings-hardening
kind: story
stage: review
tags: [ingestion, archetype, bug]
parent: fix-spine-peer-review-findings
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Ingestion edge hardening (findings 6, 8, 9)

## Brief
Latent/edge fixes: `_coerce_format` returns `"Legacy"` when it appears in a multi-format list rather than
the first element (#6, prevents skipping multi-format Legacy events); Scryfall `normalize_name` adds NFC
Unicode normalization and the index keys + `card_faces[].name` are indexed so accented names like
"Khazad-dûm" resolve (#8); fallback `tournament_id` for no-URI events appends a deterministic player-set
hash so distinct same-source/name/date events don't collide (#9), preserving idempotent refresh.

## Implementation
Parent `fix-spine-peer-review-findings` → **Unit 4 (cache.py)**, **Unit 5 (scryfall.py)**, **Unit 6
(store.py)**. Tests in `tests/test_cache_parser.py`, `tests/test_scryfall.py`, `tests/test_store.py`.
See parent `## Implementation Units` Units 4-6 for signatures + acceptance criteria.

## Implementation notes

**Unit 4 — `_coerce_format` (cache.py)**
Added `"Legacy" in value` check before `value[0]` fallback. Zero behavioral change on existing data
(host-verified no multi-format list entries), but now correct when they appear. 8 tests in
`TestCoerceFormat` cover: multi-format with Legacy anywhere, single-element list, empty list, bare
string, falsy string.

**Unit 5 — Scryfall Unicode + face-name indexing (scryfall.py)**
- Added `import unicodedata`; `normalize_name` now wraps the curly-apostrophe replacement chain in
  `unicodedata.normalize("NFC", ...)`. Curly-apostrophe handling unchanged.
- `load_card_index` keys by `normalize_name(name)` instead of raw `name`. Also indexes
  `card_faces[].name` entries (via `card.get("card_faces", []) or []`) using `setdefault` to avoid
  overriding the primary or `//' split entries.
- **Editor auto-curling gotcha**: the `normalize_name` return statement requires literal U+0027
  (straight apostrophe) as the replacement target. The Edit tool auto-curled both replacement strings
  to U+2019, silently breaking the replacement. Fixed by direct binary patch. Tests use `chr(0x0027)`
  and `chr(0x2019)` to avoid the same editor trap in assertions.
- 7 new tests: NFD→NFC index key, `card_faces[]` indexing, curly-apostrophe normalized key, NFD query
  resolution via `get_card`, DFC face name resolution, curly/straight apostrophe query equivalence,
  NFD normalize_name unit test.

**Unit 6 — `tournament_id` collision (store.py)**
Added `import hashlib`. Fallback branch now builds a `"|".join(sorted(d.player for d in tr.decks))`
player string, takes `sha1(...).hexdigest()[:8]`, and appends it as a fourth segment. URI path
unchanged. 7 tests in `TestTournamentId`: URI passthrough, determinism, distinct player sets →
distinct ids, order-independence, id format (prefix + 8-char hex digest), idempotent `load_tournament`.

**All 49 tests in scope pass.**
