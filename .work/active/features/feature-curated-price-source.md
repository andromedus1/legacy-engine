---
id: feature-curated-price-source
kind: feature
stage: done
tags: [ingestion, generation]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-04
updated: 2026-06-14
---

Cost/overlap/pivot-budget analysis was unreliable because the Scryfall oracle bulk has usd:null for exactly the expensive cards — reserved-list duals (Underground Sea), and even Null Rod. Add a curated/secondary price source (e.g. Scryfall per-printing prices, TCGplayer, or a maintained override table for reserved-list staples) so deck-cost and pivot-cost features are trustworthy.

## Design

### Problem confirmed (root cause)
The bug is not "Scryfall has no prices" — it's that the *oracle_cards* bulk is **one object per Oracle ID** and carries the `prices` of a single, arbitrarily-chosen printing. Verified against the mirrored `data/scryfall/oracle_cards.json` (updated 2026-05-31):

- **Underground Sea** → resolves to the *Vintage Masters* printing: `{usd: null, usd_foil: null, tix: "13.74", eur: null}`. The `13.74` is **MTGO tickets**, not paper dollars; the real paper Revised dual is hundreds of dollars. So the engine sees `usd: null` for a $400 card.
- **Dismember** → resolves to *one* printing at `usd: 5.32`. To catch the motivating mispricing (a **$33 Secret Lair** Dismember vs **$1–2** alternative printings) you must see *all* printings and take the min — the oracle bulk physically cannot represent that; it's a single row.
- Measured: **6,071 of 37,474** oracle-bulk cards have `usd: null`, concentrated on exactly the reserved-list / old-border staples a Legacy player cares about.

**Conclusion: per-printing granularity (required by the item) is structurally impossible from `oracle_cards`.** The fix is a different bulk type, ingested as its own mirrored source.

### Source choice + rationale
**Chosen: Scryfall `default_cards` bulk** (one object *per printing*, English/printed-language; ~547 MB), mirrored once like every other ingestion source, behind a dedicated price-ingestion path.

Options weighed:

| Option | Per-printing? | Network at analysis time | Maintenance | Verdict |
|---|---|---|---|---|
| **A. `default_cards` bulk** (chosen) | Yes — one row per printing, each with its own `prices` | None (fetched-once, mirrored, same pattern as oracle bulk) | Zero hand-curation; `legacy seed prices` re-pulls | **Chosen** — already on our existing dependency (Scryfall), satisfies per-printing, honors the no-runtime-network NFR |
| B. Stay on `oracle_cards.prices` | No (single printing) | None | Zero | Rejected — this *is* the bug |
| C. `all_cards` bulk (2.5 GB) | Yes, but adds every non-English language | None | Zero | Rejected — 5× the size for languages we never price on; `default_cards` is the English-printed subset, exactly our need |
| D. TCGplayer API | Yes | **Yes** unless we mirror, plus API key/secret + rate limits | Auth surface | Rejected — adds a secret/auth surface the project explicitly has none of (CONVENTIONS omits the security gate "no auth/secrets surface"); violates simplicity. Scryfall's `prices.usd` is already TCGplayer-derived |
| E. Hand-curated reserved-list override table | Only what's curated | None | **High, perpetual** | Rejected as *primary*; retained as a thin **optional override layer** (see below) for the rare case Scryfall is null on a card we care about — data-driven-over-curated (global rule #12) keeps it a fallback, not the source |

Rationale, in one line: **extend the existing Scryfall ingestion port with a second bulk type rather than add a new external integration** — cheapest path that satisfies per-printing + no-runtime-network + reproducible, and reuses the exact mirror-and-decouple machinery already shipped.

### Why a *separate* table/flow, not an extension of the `cards` table
The `cards` table is the **oracle dimension** (keyed by `name`, one row per playable name, with face-alias rows). Prices live at a **different cardinality** (one row per *printing* = set + collector number), refresh on a **different cadence** (Scryfall reprices `default_cards` daily; oracle text changes ~monthly), and are an **optional, gated** signal (collection-aware acquisition advisor is the only consumer, and it's a sibling feature still in drafting). Folding per-printing prices into the per-name `cards` table would break its primary key and its PK-based round-trip (`load_card`). So: **new `card_prices` table, new `seed prices` command, new raw mirror file** — the `cards` table and `seed cards` flow stay byte-identical (gated-additive-augmentation pattern at the ingestion layer; the no-price corpus behaves exactly as today).

### Ingestion / mirroring (mirror-and-decouple)
Extend `ingestion/scryfall.py` with a *second bulk type* (do **not** fork the client — ADR precedent is "extend, don't fork"):

- New constants in `config.py` (constants-only, no side effects):
  - `SCRYFALL_PRICES_BULK_TYPE = "default_cards"`
  - `SCRYFALL_PRICES_PATH = SCRYFALL_DIR / "default_cards.json"` (raw mirror = source of truth, alongside `oracle_cards.json`)
  - `SCRYFALL_PRICES_META_PATH = SCRYFALL_DIR / "prices_metadata.json"`
  - `PRICE_STALE_DAYS = 30` (advisory staleness threshold; see below)
  - `PRICE_OVERRIDE_PATH = DATA_DIR / "prices" / "overrides.json"` (optional curated layer; absent by default)
- Generalize `download_bulk_data` / `_fetch_bulk_metadata` to take a `bulk_type` + target paths (default args preserve the current oracle-only signature → no caller breaks), or add a thin `download_prices_bulk()` sibling. Same UA header, same `updated_at` skip-if-current check, same follow-redirects download. **No analysis-time network calls** — fetch-once-and-mirror, identical to oracle bulk.
- `default_cards` is large (~547 MB). Stream-parse on load (`ijson` or chunked) rather than holding the whole list in memory twice; we only keep the projected price columns.

### Per-printing price model
New DuckDB table in `ingestion/store.py` (`card_prices`), one row per printing:

```sql
CREATE TABLE IF NOT EXISTS card_prices (
    scryfall_id   VARCHAR PRIMARY KEY,   -- printing id (stable per printing)
    name          VARCHAR NOT NULL,      -- joins to cards.name (normalized)
    set_code      VARCHAR,
    set_name      VARCHAR,
    collector_number VARCHAR,
    finish        VARCHAR,               -- 'nonfoil' | 'foil' | 'etched' (the cheapest finish drives min)
    usd           DOUBLE,                -- prices.usd (NULL allowed; that's the point)
    usd_foil      DOUBLE,
    usd_etched    DOUBLE,
    eur           DOUBLE,
    promo         BOOLEAN,               -- Secret Lair / promo flag, so the advisor can prefer non-promo
    is_paper      BOOLEAN,               -- 'paper' in games[]; excludes MTGO-only printings (the Underground Sea/tix trap)
    price_date    VARCHAR                -- the bulk updated_at, for staleness
)
```

Derived query helpers (the public interface — pure functions over a connection, mirroring `fetch_card`/`load_card`):
- `cheapest_printing(con, name) -> PrintingPrice | None` — min non-null `usd` over paper printings of `name`; returns the printing identity + price so the advisor can say *"buy the $1.50 NPH copy, not the $33 Secret Lair"*. Min over `usd` with a foil/etched fallback only if no nonfoil price exists.
- `price_quote(con, name) -> PriceQuote` — `{name, cheapest_usd, cheapest_printing, n_priced_printings, all_null: bool, stale: bool, source}` — the confidence/honesty-carrying record (source-transparency NFR). `all_null=True` is an honest "we have no paper price" signal, not a silent 0.
- `printing_prices(con, name) -> list[PrintingPrice]` — every priced printing (so the advisor / a future viz can show the spread that exposed the Secret Lair gap).
- `deck_cost(con, card_counts) -> DeckCost` — sum of `cheapest_usd × count`, with an explicit list of `unpriced` names carried alongside (never silently dropped — matches the "never drop a deck" / honest-fallback conventions).

`PrintingPrice` / `PriceQuote` / `DeckCost` are dataclasses in a new `ingestion/prices.py` (computed records, not Pydantic dimension models — mirrors how advisory result records live beside their logic). Reuse the project's confidence framing: a quote built from ≥1 paper printing is trustworthy; `all_null` quotes are flagged, never imputed to 0.

### Optional curated override layer (data-driven-first, curation as fallback)
`data/prices/overrides.json` (absent by default; **not** committed unless a real gap is found): `{ "<card name>": {"usd": <float>, "note": "...", "as_of": "YYYY-MM-DD"} }`. Applied *after* the Scryfall min, only when Scryfall yields `all_null` for a card, or as an explicit manual override. Keeps global rule #12 (data-driven over hand-curated) honored — Scryfall is the pipeline; the override file is the documented escape hatch for the genuinely-unpriced reserved-list edge.

### Staleness / refresh handling
- Prices carry `price_date` (the bulk `updated_at`). `PriceQuote.stale = (today − price_date) > PRICE_STALE_DAYS`. The advisor surfaces a "prices as of YYYY-MM-DD (N days old)" banner — reuses the existing `_echo_data_freshness` CLI helper pattern (cli.py already does this for tournament data).
- `seed prices` re-pulls and the `updated_at`-equality short-circuit skips the download when current (same mechanism as `seed cards`). `refresh` (the incremental command) gains a prices step.
- Prices are **rebuildable**: the raw `default_cards.json` mirror is the source of truth; the `card_prices` table is dropped+rebuilt on re-seed (same `store.rebuild` discipline as `cards`). Deleting the DuckDB loses no price data.

### CLI shape
```
legacy seed prices            # download default_cards bulk → mirror → load card_prices table
legacy refresh                # (extended) also re-pulls prices if stale
legacy report prices <name>   # OPTIONAL diagnostic: print every paper printing + the chosen cheapest
```
`seed prices` follows the nested-group pattern: `_setup_logging(verbose)` first, lazy imports inside the command, echoes `"Loaded N printings ({M} priced) as of <date>"`. The acquisition-advisor consumption is the sibling `feature-collection-aware-engine`'s job — this feature only ships the priced data + the query interface it will call.

### Interfaces (the contract the sibling feature consumes)
```python
# ingestion/prices.py
def price_quote(con, name: str) -> PriceQuote          # cheapest paper usd + honesty flags
def cheapest_printing(con, name: str) -> PrintingPrice | None
def printing_prices(con, name: str) -> list[PrintingPrice]
def deck_cost(con, card_counts: Mapping[str,int]) -> DeckCost   # {total, lines, unpriced[]}
# ingestion/store.py
def load_prices(con, printings: Iterable[PrintingPrice]) -> int  # idempotent on scryfall_id
# ingestion/scryfall.py
def download_prices_bulk(self, force=False) -> Path
def iter_price_rows(self) -> Iterator[PrintingPrice]   # stream the mirrored default_cards.json
```

### Units in build order (trickiest first)
1. **`scryfall.py` prices-bulk download + stream parse** (trickiest: 547 MB stream, bulk-type generalization without breaking the oracle path; verify the `updated_at` skip + memory ceiling). Tests: mocked small `default_cards` fixture, multi-printing same-name, `is_paper` filter excludes the MTGO/tix printing.
2. **`store.py` `card_prices` table + `load_prices`** — DDL, idempotent upsert on `scryfall_id`, `rebuild` covers it. Tests: load multi-printing, idempotency, round-trip.
3. **`prices.py` query layer** — `cheapest_printing` (min over paper non-null), `price_quote` honesty flags, `printing_prices`, `deck_cost` with `unpriced`. Tests: Underground Sea (all-null paper → flagged, not 0), Dismember (Secret Lair $33 vs cheap printing → cheapest wins), foil-only fallback, deck-cost with an unpriced card.
4. **Override layer** — load + apply-after-min. Tests: override fills an all-null card; override ignored when Scryfall has a price unless explicit.
5. **`config.py` constants + `cli.py` `seed prices` / `refresh` wiring + freshness banner.** Tests: command smoke + staleness banner.

### Test plan
Unit, deterministic, mocked bulk fixtures (mirror `tests/test_scryfall.py::_write_bulk` + `tests/test_store.py` in-memory `:memory:` pattern). New `tests/test_prices.py`. **Golden honesty cases drawn from the motivating bug**: (a) Underground Sea paper-null → `all_null=True`, no silent 0; (b) Dismember multi-printing incl. a $33 Secret Lair → `cheapest_printing` returns the cheap one; (c) `deck_cost` lists unpriced cards rather than dropping. Regression: `seed cards` / `cards` table outputs unchanged when prices are never seeded (gated-additive contract). `test_config.py` extended: new constants are repo-rooted, import has no side effects.

### Risks
- **Bulk size (547 MB).** Mitigation: stream-parse, project only price columns; one-time download (already accepted cost for oracle bulk at 176 MB). Risk it grows; acceptable.
- **Name → printing join.** Decklists key on `name`; `default_cards` has both `name` and oracle id. Normalize names with the existing `normalize_name` so the join matches the `cards` table. Split/DFC printing names handled by the same face logic — but prices are a *card-level* concern, so we key the cheapest over the full `name`. Risk: token/art-series printings; filter by `is_paper` + exclude non-gameplay layouts (reuse `store._NON_GAMEPLAY_LAYOUTS`).
- **Foil-vs-nonfoil semantics.** The advisor wants the cheapest *playable* copy = cheapest nonfoil `usd`, foil only if nonfoil never exists. Documented in `cheapest_printing`; covered by a test.
- **Price staleness drift.** Daily Scryfall reprice vs our mirror cadence → the `stale` flag + freshness banner make it honest rather than silent. Acceptable for deck-budget granularity (not a trading tool).
- **Scope creep into the advisor.** This feature ships *data + query interface only*; ranking/impact ordering and the buy-list belong to `feature-collection-aware-engine`. Hard boundary kept.

### Decomposition
**No child stories.** Five tightly-coupled units in one module pair (`scryfall.py` + `store.py` + new `prices.py`) plus config/CLI glue — single-stride implementable, below the child-spawning threshold. Build order above doubles as the implementation checklist.

## Hold
Design complete; held for human review before implementation.

## Implementation notes

### What was built

**`src/legacy_engine/config.py`** — Five new constants: `SCRYFALL_PRICES_BULK_TYPE`, `SCRYFALL_PRICES_PATH`, `SCRYFALL_PRICES_META_PATH`, `PRICE_STALE_DAYS`, `PRICE_OVERRIDE_PATH`. Zero import side effects; all paths repo-rooted.

**`src/legacy_engine/ingestion/scryfall.py`** — Extended `ScryfallClient` with:
- `download_prices_bulk(force=False)` — streams the default_cards bulk into `data/scryfall/default_cards.json` (atomic tmp→rename); same `updated_at` skip-if-current as oracle bulk. Uses `httpx` streaming to avoid 547 MB in-memory.
- `_fetch_prices_metadata()` — queries the bulk-data endpoint for `type=default_cards`.
- `iter_price_rows(path=None)` — streams the mirrored JSON, injects `price_date` from metadata, delegates to `_raw_to_printing_price`; uses `ijson` when available with json.loads fallback.
- `prices_updated_at()` — reads updated_at from `prices_metadata.json`.
- Oracle/cards path is byte-identical; no existing callers were modified.

**`src/legacy_engine/ingestion/prices.py`** (new) — Core module:
- `PrintingPrice` dataclass — one row per printing; `cheapest_usd` property handles nonfoil→foil→etched fallback.
- `PriceQuote` dataclass — honesty-carrying record; `all_null` is the explicit "no paper price" signal.
- `DeckCostLine`, `DeckCost` dataclasses — `unpriced` list is explicit, never silently dropped.
- `_raw_to_printing_price(raw)` — converts a Scryfall default_cards object; skips non-gameplay layouts (`art_series`, `token`, etc.); sets `is_paper` from `games[]`; marks `promo=True` for `set_type=memorabilia` (Secret Lair).
- `cheapest_printing(con, name)` — SQL min over `usd` (paper rows only), foil/etched fallback.
- `price_quote(con, name, ...)` — assembles PriceQuote; applies override only when all-null.
- `printing_prices(con, name)` — all priced paper printings sorted cheapest first.
- `deck_cost(con, card_counts, ...)` — total + unpriced list; never drops a card.
- `_load_overrides(path)` — optional `overrides.json` fallback; absent = `{}`.
- `_is_stale(price_date, today)` — wall-clock-injectable staleness check.

**`src/legacy_engine/ingestion/store.py`** — Added:
- `CARD_PRICES_DDL` — DDL string for `card_prices` table (separate from `CARDS_DDL`).
- `init_prices_schema(con)` — idempotent; intentionally NOT called from `init_schema` (gated-additive).
- `load_prices(con, printings)` — `INSERT OR REPLACE` on `scryfall_id`; returns row count.
- `rebuild_prices(con)` — drop+recreate (same discipline as `rebuild`).

**`src/legacy_engine/cli.py`** — Added:
- `seed prices` command — downloads bulk, rebuilds table, echoes `"Loaded N printings (M priced) as of DATE"`.
- `refresh` — implemented (was a stub); refreshes cache + rules, optionally prices via `--prices` flag.
- `report prices <NAME>` — diagnostic; shows all priced printings + chosen cheapest.
- `_echo_price_freshness(updated_at)` — mirrors `_echo_data_freshness` for price data.

### Testing approach (no 547MB download)

All tests in `tests/test_prices.py` use hand-built fixture data:
- `_pp()` factory for `PrintingPrice` instances; `_con()` for in-memory DuckDB.
- `TestIterPriceRows` writes small JSON fixture files to `tmp_path` — no network, no real bulk.
- `TestRawToPrintingPrice` exercises the conversion logic directly.
- Golden honesty cases: Underground Sea (all-null paper printing → `all_null=True`), Dismember ($1.50 NPH vs $33 SL → cheapest wins), deck_cost unpriced list, foil-only fallback, staleness flag.

### Test counts

52 new tests in `test_prices.py`. Existing `test_config.py` and `test_cli.py` updated (3 assertions, 2 parametrize changes). Total suite: **1685 passing** (was 1634).

### Deviations from design

- `finish` column from the DDL sketch was dropped: the design called it `'nonfoil' | 'foil' | 'etched'` but the actual cheapest-finish logic is computed at query time by the `cheapest_usd` property + SQL fallback chain. The column added no value and would need derivation logic at ingest time. Replaced by the three separate `usd` / `usd_foil` / `usd_etched` columns (already in the design's DDL).
- `refresh` was fully implemented (cache + rules + optional prices) rather than left as a stub. The design spec said "extended"; the original stub just raised `_not_implemented`. Now it works.
- `iter_price_rows` signature takes an optional `path` argument for testability (not in the interface spec, which only showed `self`). This is additive and does not break the specified interface.
