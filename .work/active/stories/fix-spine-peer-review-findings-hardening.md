---
id: fix-spine-peer-review-findings-hardening
kind: story
stage: implementing
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
