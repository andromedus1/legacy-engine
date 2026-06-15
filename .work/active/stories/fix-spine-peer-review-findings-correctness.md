---
id: fix-spine-peer-review-findings-correctness
kind: story
stage: done
tags: [ingestion, archetype, bug]
parent: fix-spine-peer-review-findings
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-30
updated: 2026-06-14
---

# Rules SHA pinning + validate_deck enforcement (findings 5, 7)

## Brief
True rules pinning (#5): `refresh_rules` checks out a configured `MTGOFORMATDATA_SHA` and fails if the
post-checkout HEAD doesn't match, instead of recording whatever HEAD was cloned/pulled. Deck validation
(#7): `validate_deck` rejects nonpositive counts and enforces category bans — ante/offensive via a
name-enumerated `CATEGORY_BANNED_NAMES` set, plus an optional injected `type_line_of` resolver for
Conspiracy/Attraction/Sticker types (skipped when absent, per Ports & Adapters).

## Implementation
Parent `fix-spine-peer-review-findings` → **Unit 2 (rules_vendor.py + config.py)** and **Unit 3
(banlist.py + models/banlist.py)**. Pin SHA = `e056bc7d63c0138091986ce1696c705bc7dee296`. Tests in
`tests/test_rules_vendor.py` (fake runner asserts fetch/checkout/verify; mismatch raises) and
`tests/test_banlist.py` (nonpositive counts, category-banned names, injected type_line_of, None path).
See parent `## Implementation Units` Units 2-3 for signatures + acceptance criteria.

## Implementation notes

### Unit 2 — Rules SHA pinning (`rules_vendor.py` + `config.py`)

**What changed**: `refresh_rules` now accepts a `sha` parameter (defaulting to
`MTGOFORMATDATA_SHA` from config). After clone/existing-repo detection, it always runs
`git fetch --depth 1 origin <sha>` + `git checkout FETCH_HEAD` to stay shallow while
reaching an arbitrary historical commit. Post-checkout it calls `_resolve_sha` and raises
`RuntimeError` if the result doesn't match the requested SHA. The manifest records the
*input* SHA (not the resolved one) so `pinned_sha()` is consistent with what was requested.

**Call sequence** (fresh clone):
1. `git clone --depth 1 <repo> <dest>`
2. `git -C <dest> fetch --depth 1 origin <sha>`
3. `git -C <dest> checkout FETCH_HEAD`
4. `git -C <dest> rev-parse HEAD` → raises if mismatch

(Existing repo skips step 1.)

**Existing tests updated**: `test_pulls_when_present` → `test_skips_clone_when_git_dir_present`
(the old `git pull` is gone; fetch+checkout replaces it). All old assertions preserved.

**Config**: added `MTGOFORMATDATA_SHA = "e056bc7d63c0138091986ce1696c705bc7dee296"` after
`MTGOFORMATDATA_REPO`. Kept `RULES_PINNED_SHA = ""` (different concern — the archetype
fail-fast guard — not changed).

### Unit 3 — `validate_deck` counts + category bans (`banlist.py` + `models/banlist.py`)

**What changed**:

- `models/banlist.py`: added `CATEGORY_BANNED_NAMES: frozenset[str]` — 9 ante cards + 7
  offensive cards not derivable from type_line and not already in BASELINE_BANS (16 total).

- `ingestion/banlist.py`: `validate_deck` extended with:
  1. **Nonpositive count guard**: `count <= 0` appends an error before ban/limit checks.
  2. **Category ban check**: `name in CATEGORY_BANNED_NAMES` appends error regardless of
     snapshot contents — fires even when the snapshot's `banned` set is empty.
  3. **Injected type-line resolver**: `type_line_of: Callable[[str], str | None] | None = None`;
     when provided, flags Conspiracy/Attraction/Sticker type lines; when `None`, skipped
     entirely (no crash, no error). Ports & Adapters: domain does not import Scryfall or store.

**Tests added** (17 new, across 3 new test classes):
- `TestNonpositiveCounts` — negative count, zero count, positive count (no false positive).
- `TestCategoryBans` — ante card flagged with bare snapshot, offensive card flagged, set
  cardinality check, full-membership check.
- `TestTypeLineInjection` — Conspiracy/Attraction/Sticker each flagged; `None` path doesn't
  crash; default (no arg) doesn't crash.

**Test total**: 14 → 31 (all passing).
