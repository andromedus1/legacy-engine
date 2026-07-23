---
id: feature-refresh-keyed-reload
kind: feature
stage: review
tags: [ingestion, hygiene]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-12
updated: 2026-07-23
---

# Refresh: keyed reload that preserves labels for unchanged decks

## Brief

Every `refresh all` run — including fully no-op runs where the cache mirror reports
"Already up to date" — silently wipes the label layers: `decks.archetype` drops to ~3
rows and `decks.variant` to 0. Everything downstream (camps, eras consumption,
split-variant reports) silently degrades to fallbacks until a manual recovery of
`label` + 29× `discover apply` + `eras run` (~10 min wall clock). Three documented
recurrences: 2026-07-12, 2026-07-13, 2026-07-20.

Root cause: `ingest_cache` (src/legacy_engine/ingestion/cache.py:148) calls
`load_tournament` (src/legacy_engine/ingestion/store.py:458) for **every** discovered
cache event on every refresh. `load_tournament` is "idempotent" via DELETE + re-insert
of the tournament's child rows, and re-inserts decks with `archetype=NULL,
variant=NULL` — so labels are destroyed even when the underlying cache file is
byte-identical to what was already ingested.

The fix is a keyed (incremental) reload: skip `load_tournament` entirely for cache
events whose content is unchanged since the last ingest, so their deck rows — and the
labels on them — are never touched. Only new or changed events reload (those decks
legitimately need relabeling). Plus honest audit output: refresh must report how many
events were skipped-unchanged vs reloaded, and how many labeled rows were dropped by
the reload, with a loud `// ⚠` checklist line (label + discover apply + eras run)
whenever labeled rows were lost.

## Strategic decisions
- **Fix approach**: option (b) keyed reload preserving labels for unchanged decks,
  plus honest audit output on label loss — pinned by Andrew 2026-07-20. Options (a)
  auto-run recovery and (c) audit-line-only were considered in the backlog note;
  (a) may still fall out cheaply as the `// ⚠` checklist line, but auto-running
  recovery is not in scope.
- **Guarantee to keep**: staged-registry membership persistence (data/variants/
  discovered.json) made every manual recovery lossless — the fix must not regress it.

## Original backlog note (for provenance)

**`refresh all` can silently wipe the label layers.** The 2026-07-12 run did a full
cache reload (65,785 decks reloaded; archetype labels dropped to 3, decks.variant to
0) — everything downstream (camps, eras consumption, split-variant reports) silently
degraded to fallbacks until a manual `label` + per-archetype `discover apply` (29
splits) + `eras run` recovery. Ideas: (a) `refresh all` should detect a labels-wiped
state and either auto-run `label` (+ re-apply staged splits + `eras run`) or print a
loud `// ⚠ labels wiped — run: label && discover apply … && eras run` checklist;
(b) make ingestion preserve labels for unchanged decks (keyed reload instead of full
reload); (c) at minimum an audit line in refresh output stating how many labeled rows
were lost. The staged-registry membership persistence made recovery lossless — keep
that guarantee.

**Recurred 2026-07-13:** the wipe happens even on a NO-OP refresh — cache said
"Already up to date", zero new tournaments (deck count and max date unchanged), yet
the reload still dropped labels to 3 and variants to 0. Manual recovery (label + 29×
discover apply + eras run) worked again but took ~10 min of wall clock. This fires on
every refresh, not just data-bearing ones — raises the priority of option (b) (keyed
reload preserving labels for unchanged decks).

**Recurred 2026-07-20:** third occurrence, again on a fully no-op refresh (upstream
fbettega/MTG_decklistcache stalled since 2026-07-02, so zero new data). Labels
65,785→3, variants 21,484→0; recovered via label + 29× discover apply + eras run.

**Recurred 2026-07-21 (fourth):** no-op refresh, label wiped again; recovery = label +
29× discover apply (eras reused, corpus identical).

## Design decisions

Resolved autonomously 2026-07-23 (strategic decision already pinned; these are
mechanism-level). Cross-model advisory pass skipped — small hygiene feature, no
large/risky architectural decision open.

- **Change detection**: content-hash ledger (`ingest_ledger` DuckDB table keyed by
  cache-relative path, sha256 of file bytes) — NOT git-diff of the mirror. Robust to
  how the mirror updates, hermetic-testable without git, and lives in the same .duckdb
  file so a fresh/rebuilt DB naturally gets a full ingest (empty ledger).
- **Migration/first-run**: seed clause — when a file has no ledger row but its
  `tournament_id` already exists in `tournaments`, write the ledger row and SKIP the
  reload. Avoids one final full label wipe on the first post-feature refresh. The
  theoretical hole (file changed upstream after its last pre-feature ingest) is empty
  in practice (upstream stalled since 2026-07-02) and covered by the escape hatch.
- **Escape hatch**: `refresh all --full` forces reload of every event (bypasses both
  the hash skip and the seed clause) and still reports label drops honestly.
- **API shape**: `ingest_cache` returns an `IngestStats` dataclass (events partitioned
  new/changed/unchanged/seeded/bad + labeled-row before/after counts) instead of a bare
  int. Only two call sites exist (cli.py, tests) — update both, no compat shim.
- **Label-drop accounting**: global `count(archetype IS NOT NULL)` /
  `count(variant IS NOT NULL)` before vs after the ingest loop (exact, cheap), not
  per-event accumulation.
- **No child stories**: single-stride, tightly cohesive (~4 files); stories would be
  pure overhead.

## Architectural choice

**Content-hash ledger with seed clause** (over (i) git-diff-driven incremental ingest —
couples correctness to mirror mechanics and is untestable without git fixtures; and
(ii) label save/restore around the existing full reload — preserves the wasteful
rewrite of 65k rows and breaks silently if deck_idx assignment ever shifts). The ledger
makes "unchanged" a first-class, queryable fact; unchanged events are never touched, so
label preservation is structural rather than compensating.

## Implementation Units

### Unit 1: `ingest_ledger` schema (store.py)

**File**: `src/legacy_engine/ingestion/store.py`

```python
INGEST_LEDGER_DDL = """\
CREATE TABLE IF NOT EXISTS ingest_ledger (
    path          VARCHAR PRIMARY KEY,   -- cache-relative POSIX path of the event file
    content_hash  VARCHAR NOT NULL,      -- sha256 hex of the file bytes
    tournament_id VARCHAR NOT NULL,      -- tid loaded from this file
    ingested_at   VARCHAR NOT NULL       -- ISO-8601 UTC of the last load/seed
)\
"""
```

Executed in `init_schema` (after `PLAYER_ALIASES_DDL`). Derived state: rebuilding the
DB drops it implicitly (same file), which is exactly right — empty ledger ⇒ full ingest.

**Acceptance Criteria**:
- [ ] `init_schema` on a fresh DB creates `ingest_ledger`; idempotent on re-run
- [ ] existing DBs gain the table on next connect+init (CREATE IF NOT EXISTS)

### Unit 2: keyed `ingest_cache` + `IngestStats` (cache.py) — trickiest unit

**File**: `src/legacy_engine/ingestion/cache.py`

```python
@dataclass
class IngestStats:
    total: int = 0            # discovered Legacy events
    new: int = 0              # no ledger row, tid not in tournaments -> loaded
    changed: int = 0          # ledger row present, hash differs -> reloaded
    unchanged: int = 0        # ledger row present, hash matches -> skipped
    seeded: int = 0           # no ledger row, tid already in tournaments -> ledger seeded, skipped
    bad: int = 0              # unreadable/parse/load failure -> logged, skipped
    labels_before: int = 0    # decks with archetype IS NOT NULL before the loop
    labels_after: int = 0
    variants_before: int = 0  # decks with variant IS NOT NULL before the loop
    variants_after: int = 0

    @property
    def loaded(self) -> int: ...          # new + changed
    @property
    def labels_dropped(self) -> int: ...  # max(0, before - after), archetype
    @property
    def variants_dropped(self) -> int: ...

def ingest_cache(con, cache_dir: Path = CACHE_DIR, *, full: bool = False) -> IngestStats:
```

**Implementation Notes**:
- Per event: `blob = path.read_bytes()`; `digest = hashlib.sha256(blob).hexdigest()`;
  ledger lookup by `path.relative_to(cache_dir).as_posix()`.
- Decision tree: hash match and not `full` → `unchanged`, continue (NO parse, NO DB
  write). Ledger miss → parse, compute `tournament_id(tr)`; if tid exists in
  `tournaments` and not `full` → seed ledger row, `seeded`, continue (no reload).
  Otherwise (new / changed / `full`) → `load_tournament`, upsert ledger row
  (`INSERT OR REPLACE`), count as `new`/`changed` (under `full`, an unchanged-hash
  event counts `unchanged`? No — under `full` everything that loads counts as
  `changed` unless it was genuinely `new`; do NOT report force-reloads as unchanged).
- Parse the JSON from `blob` (`json.loads(blob)`) — do not re-read the file.
- Resilience NFR unchanged: any per-event exception → `bad`, log, continue; ledger row
  NOT updated on failure (so the next run retries it).
- Label counts: two scalar SELECTs before the loop, two after; populate the stats.
- Keep `discover_legacy_events` as-is (it stays the format filter / source deriver).

**Acceptance Criteria**:
- [ ] second ingest of an identical cache is a full skip: `unchanged == total`, zero
      DB writes to decks — archetype/variant labels set between the two runs survive
- [ ] a modified event file reloads: its labels drop (fresh NULL rows), all other
      events' labels survive; stats report `changed == 1`, correct drop counts
- [ ] a brand-new event file loads; `new == 1`
- [ ] pre-feature DB simulation (tournaments populated, ledger empty): ingest seeds
      the ledger, `seeded == total`, labels survive untouched
- [ ] `full=True` reloads everything (`loaded == total - bad`), labels drop, stats say so
- [ ] a bad event increments `bad`, doesn't abort the batch, and leaves no ledger row
- [ ] failed load leaves prior ledger row intact (retry on next run)

### Unit 3: refresh audit output (cli.py)

**File**: `src/legacy_engine/cli.py`

```python
def _refresh_cache_audit(stats: IngestStats) -> list[str]:
    """Pure formatter -> audit lines for refresh output (unit-testable)."""
```

`refresh all` gains `--full` flag; body becomes:

```
Refreshed tournament cache: {total} events — {new} new, {changed} changed, {unchanged} unchanged, {seeded} seeded{, N bad}
// labels: {labels_after:,} archetype / {variants_after:,} variant rows ({preserved|dropped} ...)
// ⚠ {labels_dropped:,} archetype + {variants_dropped:,} variant labels dropped on reloaded events — run: label && discover apply … && eras run
```

The `// ⚠` line appears ONLY when `labels_dropped + variants_dropped > 0` (follows
audit-echo-comment-lines + honest-degrade-marker patterns).

**Acceptance Criteria**:
- [ ] formatter emits the ⚠ checklist line iff labeled rows were dropped
- [ ] no-drop case emits a positive "labels preserved" audit line (silent success is
      not honest enough here — this is the bug's whole point)
- [ ] `--full` is wired through to `ingest_cache(full=True)`

### Unit 4: tests

**File**: `tests/test_cache_mirror.py` (extend existing classes/builders),
`tests/test_cli.py` (formatter unit test only)

Reuse the existing `_build_cache(tmp_path)` fixture-builder; all DB work on tmp-path
DuckDB per file-backed-cli-test-db-builder discipline (never the default DB). No CLI
invocation test of `refresh all` (it shells to git via `mirror_cache`; existing suite
has the same precedent) — the formatter is pure and the ingest behavior is covered at
the function level.

## Implementation Order
1. Unit 1 (schema) — everything hangs on the ledger existing
2. Unit 2 (keyed ingest_cache + IngestStats)
3. Unit 3 (CLI audit + --full)
4. Unit 4 (tests alongside each unit; final green run)

## Testing

Covered per-unit above. Integration seam: `ingest_cache` ↔ `load_tournament` (labels
wiped only for reloaded tids — proven by the modified-file test); `ingest_cache` ↔
ledger lifecycle (seed / upsert / retry-on-failure tests).

## Risks

- **Seed clause can mask a real upstream edit** that landed between the last
  pre-feature ingest and the first post-feature refresh. Window is empty in practice
  (upstream stalled since 2026-07-02); `--full` is the recovery. Documented in the
  CLI help for `--full`.
- **Hash is byte-exact**: a git-side line-ending or re-serialization change would read
  as "changed" and reload (labels for those decks wiped once, honestly reported).
  Fails in the safe direction.
- **`decks.variant` provenance**: labels dropped on genuinely-changed events are the
  legitimate cost; staged-registry membership persistence (data/variants/
  discovered.json) keeps `discover apply` recovery lossless for those decks —
  untouched by this feature (guarantee preserved: we only ever skip work, never alter
  the label/apply path).

## Implementation notes

Built exactly per the design above, all 4 units, no deviations.

- **Unit 1** — `INGEST_LEDGER_DDL` added to `src/legacy_engine/ingestion/store.py:102-111`
  (`ingest_ledger(path PK, content_hash, tournament_id, ingested_at)`); executed in
  `init_schema` at `store.py:138` right after `PLAYER_ALIASES_DDL`, with a comment
  stating the derived-state / empty-ledger-⇒-full-ingest constraint. `CREATE TABLE IF
  NOT EXISTS` makes this a no-op migration for existing DBs.
- **Unit 2** — `src/legacy_engine/ingestion/cache.py`: `IngestStats` dataclass
  (`cache.py:152-183`, with `loaded`/`labels_dropped`/`variants_dropped` properties) and
  the rewritten `ingest_cache(con, cache_dir=CACHE_DIR, *, full=False) -> IngestStats`
  (`cache.py:188`). Calls `store.init_schema(con)` up front so the before-counts and
  ledger table exist even on an all-skip run. Per event: read bytes once, sha256 hash,
  ledger lookup by `path.relative_to(cache_dir).as_posix()` (includes the
  `Tournaments/<Source>/...` prefix as specified). Decision tree implemented exactly:
  hash-match+not-full → `unchanged` (no parse/write); ledger-miss+tid-already-exists+
  not-full → seed (ledger row written, no reload); everything else →
  `store.load_tournament` + ledger upsert, classified `new` (no prior row, tid didn't
  exist) or `changed` (covers force-reloads under `full=True`, which never count as
  `unchanged`). Per-event exceptions caught, `bad` incremented, logged, ledger row left
  untouched (retry-next-run). `discover_legacy_events`, `parse_cache_item`,
  `mirror_cache` untouched.
- **Unit 3** — `src/legacy_engine/cli.py`: `refresh all` gained `--full` (dest
  `full_reload`) (`cli.py:306-308`); `_refresh_cache_audit(stats) -> list[str]` pure formatter
  (`cli.py:275-300`) emits the summary line (with `, N bad` suffix only when `bad > 0`),
  then either the `// labels preserved: ...` line (zero drops) or the `// ⚠ ... labels
  dropped ... — run: label && discover apply <archetype>… && eras run` line plus a `//
  labels: ... rows remain` line (drops > 0). `refresh_all` echoes each formatter line.
- **Unit 4** — `tests/test_cache_mirror.py`: updated the two existing `ingest_cache`
  assertions to the `IngestStats` shape (`stats.loaded`, `stats.bad`, plus a new
  assertion that a bad path never gets a ledger row) and added `TestKeyedReload` with 6
  new tests covering: full-skip on an identical second ingest; a modified event
  reloading only that tournament's labels; a new file loading without disturbing
  existing labels; the seed path for a pre-feature DB (tournaments populated, ledger
  empty); `full=True` wiping and reloading everything; and a failed reload leaving the
  prior ledger row (and its old hash) intact for retry. `tests/test_cli.py`: added
  `TestRefreshCacheAudit` (4 tests) exercising `_refresh_cache_audit` directly — bad
  suffix presence, preserved-line vs warning-line mutual exclusivity, and exact drop
  counts in the warning line.
- **Test count**: 6 new tests in `tests/test_cache_mirror.py` (`TestKeyedReload`) + 4 new
  tests in `tests/test_cli.py` (`TestRefreshCacheAudit`) = 10 new tests; 2 existing tests
  updated in place for the new return shape.
- **Full suite**: `2977 passed, 1 xfailed` — green.
- **No deviations** from the design; no design-flaw escape hatch triggered.
