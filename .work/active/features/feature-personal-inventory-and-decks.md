---
id: feature-personal-inventory-and-decks
kind: feature
stage: implementing
tags: [ingestion, data-model, advisory, foundation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

The engine needs **persistent storage for the user's own card inventory**, plus a way to **identify
which deck each card belongs to** — where "deck" means *the user's specific variation*, not just an
archetype label the engine infers from tournament data.

Two coupled needs:

1. **Persistent inventory.** A durable, stateful store of owned cards → quantities (and ideally
   printing/condition, given the $33-vs-$2 Dismember lesson). This session the "collection" was pasted
   into chat and re-reconciled by hand every time; it should live in the engine and persist across
   sessions. This is the storage layer beneath [[idea-collection-aware-engine]] (which assumed a
   collection could merely be passed in).

2. **Cards ↔ decks membership.** Model the user's **own decks as first-class persistent entities** —
   "my Dimir Tempo" with my exact 60 + my 15(s) — distinct from the engine's archetype classification.
   Track which physical copies are allocated to which deck vs free in the binder. This unlocks:
   - "Can I build deck X entirely from my collection?" (we checked this by hand repeatedly);
   - "What's free for the sideboard if I move these 2 Barrowgoyf to the board?";
   - registering/loading "my deck" instead of passing `/tmp/*.txt` files into every command;
   - tracking a deck's evolution over time (versions/variants), and supporting multiple decks that
     may share/contend for the same physical cards.

Note the distinction the user drew: a "deck" is *the user's variation* (their precise 75 and its
history), which the engine should store and version — separate from the archetype label
([[idea-subarchetype-variants]] is about engine-side variant detection; this is user-side deck
ownership). Foundational for [[idea-deck-tuning-refresh-workflow]] and the acquisition advisor, and a
likely first home for the [[idea-web-interface]] surface (manage inventory + decks in a UI). Has
foundation-doc impact (new persistent entities: Inventory, Deck) — route through scope/epic-design.

## Strategic decisions

These are **locked** prior to design (scope decision, 2026-06-13). Recorded here so a later session
doesn't relitigate them.

1. **Collection + decks ARE in scope.** Foundation docs already rolled forward: `SPEC.md` carries the
   `Inventory` and `UserDeck` entities; `VISION.md` non-goals now state the engine models the user's
   personal collection and own decks as a first-class *local* layer (CLI-first, not a deckbuilding
   editor). This design builds against that committed shape — it does not re-open the in/out question.

2. **Local single-user now, schema designed cloud-ready for later.** We model it so a future hosted /
   multi-user surface can migrate **without a rewrite**. Concretely (see Design → Cloud-ready shape):
   - **Stable, opaque ids** on every persistent entity (`UserDeck.id`, `DeckVersion.id`) — UUIDs, not
     names or array indices — so renames/edits don't break references and ids survive a server import.
   - **An explicit `owner` key on every owned row**, defaulted to a single local owner constant
     (`LOCAL_OWNER = "local"`) now, but present in the schema and threaded through every query, so
     multi-tenancy is a *value* change (real user ids + a WHERE filter), not a *schema* migration.
   - **No assumptions that break under multi-tenancy:** no global "the inventory" singleton in code
     paths (always keyed by owner), no name-as-primary-key for user-owned objects, timestamps in UTC
     ISO-8601, additive/append-only versioning (never destructive in-place edits to a shipped version).

3. **CLI-first; no web UI now.** The `[[idea-web-interface]]` surface is deferred to its own research
   (per VISION non-goals). This feature ships a CLI command surface and a clean module seam a future
   web layer can call; it does **not** ship a server, HTTP, or editor GUI.

## Design

### Overview

A new **`collection/` module** owns two new persistent, user-owned entities — **`Inventory`** (owned
cards → quantity, with optional printing/condition) and **`UserDeck`** (a named, **versioned** 75 the
user owns and plays). It follows the project's established **raw-files = source of truth, DuckDB =
derived** pattern: user data persists as human-readable JSON under `data/collection/` (the SSOT,
git-friendly, hand-editable, backupable), and is loaded into rebuildable DuckDB tables for the
allocation/buildability queries. Deleting the DuckDB never loses collection data — exactly the
property `store.py` already guarantees for tournament data.

`collection/` is a **peer of `ingestion/`** in the layer diagram (it's a data-acquisition + persistence
concern), sitting beneath `analytics/`/`advisory/`/`generation/`, and it reuses the existing
decklist text format (`advisory.report._parse_decklist` ⇄ `generation.export.format_decklist`) so a
`UserDeck` version imports/exports through the same `<count> <name>` plumbing every other command
already speaks.

### Data model (new Pydantic models, `models/collection.py`)

All subclass `LegacyEngineModel` (per the pydantic-base-model pattern). No dataclasses.

```python
# models/collection.py
LOCAL_OWNER = "local"   # the single-user default; becomes a real user id under a hosted surface

class InventoryEntry(LegacyEngineModel):
    name: str                      # oracle/face name, resolves against the cards table
    count: int = 1
    printing: str | None = None    # Scryfall set code + collector number, e.g. "mh3:62" — optional
    condition: str | None = None   # NM/LP/MP/HP/DMG — optional, free text for now
    foil: bool = False
    # NOTE: identity of a *physical-copy bucket* = (name, printing, condition, foil).
    # The $33-vs-$2 Dismember lesson: same name, different printing = materially different copy.

class Inventory(LegacyEngineModel):
    owner: str = LOCAL_OWNER
    entries: list[InventoryEntry] = []
    updated: str = ""              # UTC ISO-8601, set on write
    # Aggregate "how many <name> do I own (any printing)" is a derived query, not stored.

class DeckCardRef(LegacyEngineModel):
    name: str
    count: int
    board: str = "main"            # "main" | "side"
    printing: str | None = None    # optional: pin a version to a specific printing for value/allocation

class DeckVersion(LegacyEngineModel):
    id: str                        # stable UUID — immutable once created
    version: int                   # monotonic per UserDeck, 1-based
    label: str = ""                # optional human tag, e.g. "post-Frog-ban"
    cards: list[DeckCardRef] = []  # the 75 (main + side)
    created: str = ""              # UTC ISO-8601
    note: str = ""                 # free-text changelog for this version

class UserDeck(LegacyEngineModel):
    id: str                        # stable UUID — survives renames
    owner: str = LOCAL_OWNER
    name: str                      # "my Dimir Tempo" — user-facing, mutable, NOT the key
    archetype_hint: str | None = None   # optional user label; engine archetype is still inferred
    versions: list[DeckVersion] = []    # append-only history; newest = current by default
    current_version_id: str | None = None  # which version is "the deck" right now
    created: str = ""
    updated: str = ""
```

**Versioning** is append-only: editing a deck appends a new `DeckVersion` (new UUID, `version+1`) and
moves `current_version_id`; prior versions are immutable. This gives "track a deck's evolution over
time" for free and is the multi-tenant-safe shape (no destructive in-place edits). `deck save` to an
existing deck creates a new version; `deck save` to a new name creates a new `UserDeck`.

**Allocation** (cards → a deck vs free in the binder) is **derived, not stored as a third entity.** A
card is "allocated" iff it appears in some deck's *current* version; "free in the binder" =
`inventory_count(name[,printing]) − Σ allocated_in_current_versions(name[,printing])`. Modeling
allocation as a computed view (rather than a stored assignment table) means there is exactly one source
of truth for "what I own" (Inventory) and one for "what's in each deck" (UserDeck versions) — no
third table to keep consistent. Contention (two decks wanting the same physical copy) is then a
*reported overlap*, not a write-time lock: `collection status` surfaces "−2 Barrowgoyf: 2 decks claim
the same copies." This is the honest, data-driven choice and avoids a stateful assignment layer that
would fight the append-only version model.

### Storage approach (raw JSON SSOT + DuckDB derived)

**Raw files (source of truth)** under a new `data/collection/` dir:
- `data/collection/inventory.json` — one `Inventory` document (current single owner).
- `data/collection/decks/<deck-id>.json` — one `UserDeck` document per deck (id-named file, so a
  rename is a field change, not a file move).

Justification for JSON-file SSOT (vs DuckDB-as-truth): mirrors the architecture's reproducibility NFR
and the existing `store.py` contract exactly — raw is truth, DuckDB is a rebuildable cache. Collection
data is **user-authored and precious** (unlike tournament data, it can't be re-fetched), so it belongs
in human-readable, diffable, git-trackable files the user can hand-edit and back up. DuckDB tables are
populated from these files and exist purely to make allocation/buildability **joinable** against
`cards` and `deck_cards` (e.g. "can I build deck X from my collection" is an inventory⋈deck-version
anti-join; "value of free binder" joins printings to a future price dim).

**Derived DuckDB tables** (declared in a new `collection/store.py`, NOT in `ingestion/store.py` — keep
ownership clean, mirroring how `store.py`'s header explicitly disclaims tables it doesn't own):
```
inventory_entries(owner, name, printing, condition, foil, count)            -- PK (owner,name,printing,condition,foil)
user_decks(id, owner, name, archetype_hint, current_version_id, created, updated)  -- PK id
deck_versions(id, deck_id, version, label, created, note)                   -- PK id
deck_version_cards(version_id, board, name, printing, count)                -- FK version_id
```
`collection rebuild` drops + reloads these from the JSON files (same shape as `store.rebuild`). Every
table carries `owner`; every query filters on it (defaulted to `LOCAL_OWNER`).

### Cloud-ready-later shape (how migration stays a non-rewrite)

- **Ids:** `UserDeck.id` / `DeckVersion.id` are UUIDs minted at creation, never derived from name. A
  hosted import keeps the same ids; references (current_version_id, FK joins) survive.
- **Owner key:** present on every row + every Pydantic doc, threaded through every `collection/` query
  signature as a param (`owner: str = LOCAL_OWNER`). Going multi-tenant = pass real ids + the WHERE is
  already there. No table reshape.
- **No singletons:** code never assumes "the one inventory"; the API is `load_inventory(owner)` /
  `list_decks(owner)`. The CLI binds `owner=LOCAL_OWNER`.
- **Timestamps:** UTC ISO-8601 strings (matches the `date`/string convention already in the schema).
- **Append-only versions:** server-side concurrent edits append; they never mutate a shipped version.
- **File layout maps to rows:** `inventory.json`→`inventory_entries`, `decks/<id>.json`→
  `user_decks`+`deck_versions`+`deck_version_cards`. A future blob/Postgres store reuses the same
  normalized shape.

### New module: `collection/` (the seam)

```
src/legacy_engine/collection/
  __init__.py
  store.py        # DuckDB DDL + load/fetch/rebuild for the 4 collection tables (peer of ingestion/store.py)
  persist.py      # JSON SSOT read/write: load/save Inventory + UserDeck docs under data/collection/
  inventory.py    # Inventory domain ops: import (text/CSV), add/remove, aggregate counts, owner-scoped
  decks.py        # UserDeck domain ops: save (new deck / new version), load, list, show, switch-version
  allocation.py   # PURE derived views: buildability (can I build deck X?), free-binder, contention
```

**Seam rationale (objective-search-split pattern):** `allocation.py` is a **pure** function layer —
it takes plain dicts (inventory counts, deck card maps) and returns buildability/contention reports,
with the DuckDB value-computation done once in `store.py` and injected. This makes the
buildability/contention logic unit-testable with hand-built inputs and no DB, exactly as
`objective-search-split` prescribes. `persist.py` ⇄ `store.py` is the file-SSOT ⇄ derived-cache split
that mirrors `ingestion/` (parse raw → load DuckDB).

Decklist text reuse: `decks.import_text` calls `advisory.report._parse_decklist` (promote it to a
non-underscore `parse_decklist` in a shared spot — see Risks) and `deck export` calls
`generation.export.format_decklist`. No new decklist parser.

### Interfaces (the public functions a future web layer / other modules call)

```python
# collection/persist.py
def load_inventory(owner: str = LOCAL_OWNER) -> Inventory
def save_inventory(inv: Inventory) -> None
def load_user_deck(deck_id: str) -> UserDeck | None
def save_user_deck(deck: UserDeck) -> None
def list_user_decks(owner: str = LOCAL_OWNER) -> list[UserDeck]

# collection/inventory.py
def import_inventory(text_or_rows, *, owner=LOCAL_OWNER, merge=True) -> Inventory   # text/CSV → Inventory
def owned_count(inv: Inventory, name: str, *, printing=None) -> int

# collection/decks.py
def save_deck(name, mainboard, sideboard, *, owner=LOCAL_OWNER, deck_id=None, note="") -> UserDeck
    # deck_id=None → new UserDeck; else append a new DeckVersion
def current_cards(deck: UserDeck) -> tuple[dict[str,int], dict[str,int]]   # (main, side) of current version

# collection/allocation.py  (PURE — dicts in, reports out, no DB)
def buildability(deck_main, deck_side, owned_counts) -> BuildabilityReport   # missing cards + shortfall
def free_binder(owned_counts, allocated_counts) -> dict[str,int]
def contention(per_deck_current_cards, owned_counts) -> list[Contention]     # overlapping claims

# collection/store.py  (DuckDB derived; mirrors ingestion/store.py API)
def init_schema(con); def rebuild_collection(con, owner=LOCAL_OWNER); def load_inventory_rows(con, inv); ...
```

### CLI command surface (new `collection` group + `deck` group)

Per the cli-nested-groups pattern (fail-loud stubs first, `_setup_logging(verbose)` first line, lazy
imports inside leaves):

```
legacy collection import --file owned.txt|.csv [--merge/--replace] [--printing-aware]
legacy collection show [--free-only] [--card NAME]          # binder view: owned, allocated, free
legacy collection status                                    # buildability + contention summary across decks
legacy collection rebuild                                   # drop+reload DuckDB from data/collection/ JSON

legacy deck save   --name "my Dimir Tempo" --deck list.txt [--note "..."]   # new deck OR new version
legacy deck load   --name "my Dimir Tempo" [--version N] [--format moxfield] # → decklist text (stdout/--out)
legacy deck list                                            # all my decks + current version + archetype
legacy deck show   --name ... [--version N]                 # the 75 + version history
legacy deck versions --name ...                             # version log (evolution over time)
legacy deck buildable --name ...                            # can I build this from my collection? (gap list)
```

**Integration with existing commands (additive, gated):** the decklist-consuming leaves
(`advise positioning|sideboard|whattoplay|report`, `generate tune`, `export deck`) gain an **optional**
`--my-deck NAME` alternative to `--deck FILE` that resolves a `UserDeck`'s current version. This is the
"register/load my deck instead of passing /tmp/*.txt" win. Per the **gated-additive-augmentation**
pattern: `--my-deck` is purely additive, `--deck FILE` is byte-identical to today when `--my-deck` is
absent, and existing tests (which always pass `--deck`) exercise the unchanged path untouched. **This
integration is split into its own child story** (see below) so the core persistence ships first.

### Units in build order (trickiest first within the core)

1. **U1 — models + persist (JSON SSOT).** `models/collection.py` + `collection/persist.py` +
   `config.py` paths (`COLLECTION_DIR`, `INVENTORY_PATH`, `DECKS_DIR`, `LOCAL_OWNER`). UUID minting,
   append-only version logic, UTC timestamps. *Trickiest* (the versioning/owner invariants are the
   load-bearing cloud-ready decisions) → first. Tests: round-trip docs; new-deck vs new-version;
   id stability across rename.
2. **U2 — allocation (pure).** `collection/allocation.py`: buildability, free-binder, contention, on
   hand-built dicts. No DB, no files. Tests are pure-function tables (objective-search-split).
3. **U3 — DuckDB derived store.** `collection/store.py`: DDL, load-from-Inventory/UserDeck, rebuild,
   owner-scoped fetch + the inventory⋈deck-version queries that feed allocation. Tests: `:memory:`
   load → query; rebuild idempotency.
4. **U4 — inventory import + CLI `collection` group.** `collection/inventory.py` (text/CSV import,
   merge/replace) + `collection import|show|status|rebuild`. Reuse `_parse_decklist` for the text path.
5. **U5 — deck ops + CLI `deck` group.** `collection/decks.py` + `deck save|load|list|show|versions|
   buildable`. Reuse `format_decklist` for `deck load`.

(Child story **U6 — `--my-deck` integration** into the 6 existing leaves; held separately so core
persistence is reviewable/shippable independently.)

### Test plan

- **Pure (no DB/FS):** allocation buildability/contention/free-binder over hand-built dicts; version
  append logic; owner threading defaults. (pytest factory fixtures: `_make_inventory(**kw)`,
  `_make_user_deck(**kw)` closures in `conftest.py`, deterministic.)
- **Persistence round-trip:** save → load Inventory/UserDeck; id stability across `name` change;
  `decks/<id>.json` file naming; merge vs replace import.
- **DuckDB (`:memory:`):** load rows → buildability query matches the pure-layer result; `rebuild`
  reloads from JSON with no data loss; owner filter isolates rows (seed two owners, query one).
- **Decklist reuse:** `format_decklist(current_cards(deck))` round-trips back through `parse_decklist`
  to the same board maps (extends the existing export round-trip contract).
- **CLI:** `CliRunner` over each leaf; `collection import` then `deck save` then `deck buildable`
  end-to-end on a temp `COLLECTION_DIR`; fail-loud on unknown deck name.
- **Regression (U6):** existing `--deck FILE` invocations byte-identical with `--my-deck` absent.

### Risks

- **`_parse_decklist` lives in `advisory/report.py` as a private fn.** Reusing it from `collection/`
  would make `collection → advisory` a dependency (wrong direction; `collection` is a low layer).
  *Mitigation:* promote the parser to a neutral home (e.g. `collection/decklist_text.py` or a small
  `models/decklist.py` helper) and have `advisory.report` import it, OR duplicate the ~40-line parser.
  Lightweight move preferred; flag for the implementer. (Decided: promote to a shared low-layer home
  so both `advisory` and `collection` depend *down*, not sideways.)
- **Printing/condition granularity vs simplicity.** Full printing-aware allocation (which exact `mh3:62`
  copy is in which deck) is powerful but heavier. *Mitigation:* `printing`/`condition` are **optional**
  and default `None`; the name-level path (own/allocate by oracle name) is the always-works baseline,
  printing-awareness is the gated refinement (gated-additive-augmentation). Buildability/contention work
  name-only when printings are absent.
- **No price dimension yet.** The Dismember-value lesson motivates printing tracking but a price feed
  is out of scope here. *Mitigation:* model `printing` now (cheap), defer valuation to the acquisition
  advisor; this feature just makes printing *recordable*.
- **Contention is reported, not enforced.** Two decks can both "use" the same physical copy. This is a
  deliberate honesty choice (no write-time locking against the append-only model), but a user could be
  surprised. *Mitigation:* `collection status` + `deck buildable` surface overlaps loudly.
- **DuckDB schema co-tenancy with `ingestion/store.py`.** Two modules now create tables in the same
  `legacy.duckdb`. *Mitigation:* `collection/store.py` owns only its 4 tables and documents that in its
  header (mirroring `ingestion/store.py`'s existing disclaimer); `init_schema` is `IF NOT EXISTS`.

### PROPOSED ARCHITECTURE.md addition (apply at implement time)

> Do NOT apply now — ARCHITECTURE.md is held for human review with this feature. Drafted block:

Add a new module-map section after `ingestion/`:

```markdown
### `collection/` — the user's personal layer (local single-user; schema cloud-ready)
The user's own card inventory and decks as first-class persistent entities. Raw JSON under
`data/collection/` is the source of truth (user-authored, precious, git-/hand-editable); DuckDB tables
are the rebuildable derived cache for allocation/buildability joins — same SSOT split as `ingestion/`.
Every owned row carries an `owner` key (defaulted `LOCAL_OWNER="local"`) and every persistent entity a
stable UUID, so a future hosted/multi-user surface migrates without a schema rewrite. CLI-first; no web
UI (deferred to its own research).

| File | Responsibility |
|---|---|
| `persist.py` | JSON SSOT read/write for `Inventory` + `UserDeck` docs under `data/collection/` |
| `store.py` | DuckDB DDL + load/fetch/rebuild for `inventory_entries`, `user_decks`, `deck_versions`, `deck_version_cards` (owns only these 4 tables) |
| `inventory.py` | Inventory domain ops (text/CSV import, merge/replace, owner-scoped counts) |
| `decks.py` | UserDeck ops: save (new deck / append version), load, list, show, version log |
| `allocation.py` | Pure derived views: buildability, free-binder, contention (objective-search-split) |
```

Update the layer diagram: `collection/` sits beside `ingestion/` (a data/persistence layer beneath
analytics/advisory/generation). Add to the `data/` box: `data/collection/inventory.json` +
`data/collection/decks/<id>.json` (raw SSOT) and the 4 derived DuckDB tables.

Add to **Domain Entities** (already in SPEC.md; reference from ARCHITECTURE models/ list):
`Inventory`, `InventoryEntry`, `UserDeck`, `DeckVersion`, `DeckCardRef` in `models/collection.py`.

Add CLI to the Conventions block: `collection import|show|status|rebuild`, `deck save|load|list|show|
versions|buildable`, plus the optional `--my-deck NAME` alternative to `--deck FILE` on the
decklist-consuming leaves.

### Child stories

This feature genuinely spans separable units. Two child stories are created at stage `drafting` (held
under the same review). The core (U1–U5) stays in this feature body; the integration is split out:

- `personal-inventory-and-decks-my-deck-integration` — wire optional `--my-deck NAME` into the 6
  existing decklist-consuming leaves (gated-additive; depends on this feature's U1+U5).
- `personal-inventory-and-decks-printing-aware-allocation` — promote printing/condition from
  recordable to fully allocation-aware (which exact copy in which deck), with value hooks for the
  later acquisition advisor (depends on this feature's U1–U5).

## Implementation notes

Implemented 2026-06-13.  All units U1–U5 shipped; U6 (--my-deck integration) remains in
child story `personal-inventory-and-decks-my-deck-integration`.

**Files created:**
- `src/legacy_engine/models/collection.py` — Inventory, InventoryEntry, UserDeck, DeckVersion, DeckCardRef
- `src/legacy_engine/models/decklist.py` — promoted `parse_decklist` (canonical public function)
- `src/legacy_engine/collection/__init__.py`, `persist.py`, `store.py`, `inventory.py`, `decks.py`, `allocation.py`
- `tests/test_collection_models.py`, `test_collection_allocation.py`, `test_collection_persist.py`, `test_collection_store.py`, `test_collection_decks.py`, `test_collection_cli.py`

**`_parse_decklist` promotion:** moved implementation to `models/decklist.py` as `parse_decklist`;
`advisory/report.py` now re-exports it as `_parse_decklist` (backward-compat alias) — all 63 existing
tests that import it continue to pass.

**DuckDB DDL deviation:** `printing` and `condition` are nullable in the model, so the original
design's `PRIMARY KEY (owner, name, printing, condition, foil)` would fail DuckDB's NOT NULL
constraint on PK columns.  Fixed by dropping the composite PK; idempotency is achieved via the
existing delete-before-reinsert pattern per owner.  Column renamed `condition` → `condition_kw`
to avoid collision with DuckDB reserved word.

**Test count:** 86 new tests, 1634 total (all green).

**ARCHITECTURE.md:** rolled forward — `collection/` module-map section added, layer diagram updated,
`data/collection/` added to data box, `models/` section updated for collection entities +
`models/decklist.py`, Conventions CLI list updated.


## Review findings (bounce 1)
BLOCKING: `cli.py` `collection show --free-only` is broken by operator chaining: `if free_only and free_cnt > 0 == 0:` parses as `free_only and (free_cnt>0) and (0==0)` so it `continue`s on every card that HAS free copies → `--free-only` shows nothing. FIX the predicate (should skip cards with free_cnt==0 under --free-only) and add a spec-derived regression test (own N, allocate 0 → --free-only shows N). Round-trip + model + ARCHITECTURE roll-forward all verified good.
