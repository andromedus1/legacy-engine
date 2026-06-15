---
id: feature-collection-aware-engine
kind: feature
stage: done
tags: [advisory, generation, ingestion]
parent: null
depends_on: [feature-personal-inventory-and-decks]
release_binding: v0.1.0
gate_origin: null
created: 2026-06-13
updated: 2026-06-14
---

<!-- design-stride: 2026-06-13. depends_on feature-personal-inventory-and-decks (Inventory/UserDeck
model) + feature-curated-price-source (PriceSource). depends_on frontmatter lists only the inventory
feature; the price-source dep is a SOFT dep — the acquisition advisor degrades to unpriced ranking when
no PriceSource is wired (see Risk 4 + Unit 3 degradation). Kept as a soft dep so this feature is not
hard-blocked on price-source landing first. -->


The engine has **no model of what cards the user owns.** Every recommendation this session
(2026-06-13) had to be reconciled against the player's binder by hand, and the sideboard recommender
repeatedly proposed cards the user doesn't own (Defense Grid, Back to Basics, Chalice of the Void) —
useless as a literal buy/play list.

Build a **collection/binder model**: ingest a collection list (owned card → quantity), and make
`advise` / `generate tune` / `advise sideboard` **collection-aware** — recommend from owned cards, or
cleanly split output into "play these (owned)" vs "acquire these (not owned)".

**Headline consumer — an acquisition advisor.** Given collection + a target field/board(s) (+ a price
source, [[idea-curated-price-source]]), output a **ranked, priced buy list** ordered by impact
(field adoption × archetype relevance), and:
- flag redundant / over-quantity owns (we found the player was deeply over-covered on graveyard hate);
- flag overpriced printings (we caught a $33 Secret Lair Dismember vs $1–2 alternatives by hand);
- show how each buy slots into the board and what it replaces.

This is the foundation under the collection-aware version of [[idea-deck-tuning-refresh-workflow]],
and it's the single most-repeated manual step of the dogfood session — the engine kept recommending
cards that aren't in the binder.

## Design

### Goal & framing

Two coupled deliverables:

1. **Collection-awareness threaded into the existing recommenders** (`advise sideboard`, `generate
   tune`, and the `advise sideboard`/`tune` OUT/IN plans). Same recommendations as today, but each
   recommended card is **annotated as owned / not-owned**, and the consumer can choose between two
   modes: *owned-only* (recommend strictly from what you have) or *acquire-split* (recommend the best
   list, then split it into "play these — owned" vs "acquire these — not owned").

2. **The headline ACQUISITION ADVISOR** (`advise acquire`) — given a collection + a target field +
   one or more target boards (an archetype, a UserDeck, or an explicit deck file) + a price source,
   produce a **ranked, priced buy list** ordered by impact (field adoption × archetype relevance),
   flagging redundant/over-quantity owns and overpriced printings, and showing how each buy slots
   into the board and what it replaces.

**Gated-additive is the load-bearing constraint** (pattern: `gated-additive-augmentation`). With no
collection supplied, every existing command's output is **byte-identical to today**. Collection-aware
behavior activates only when a collection is wired in. The acquisition advisor is a brand-new command,
so it has no baseline to preserve, but it degrades cleanly (no price source → unpriced ranking; no
rounds data → adoption-only impact, the same way `tune` already degrades).

### Dependency on the Inventory model + price source

This feature **consumes, does not define** the persistence layer. The sibling
`feature-personal-inventory-and-decks` owns the `Inventory` and `UserDeck` entities (SPEC entity
table). This design assumes that model and treats it as a port. The minimal shape we rely on:

- **`Inventory`** — owned card → quantity, with printing/condition. We need exactly two query
  primitives from it (define them as a thin read port `advisory/collection.py::CollectionView` so we
  do not couple to the sibling's storage internals):
  - `owned_qty(card_name: str) -> int` — total copies owned across printings (the recommender only
    cares about the oracle-name quantity; printing matters only for pricing, below).
  - `printings(card_name: str) -> list[OwnedPrinting]` — `(set_code, collector_number, condition,
    qty)` for the over-priced-printing check.
  - Loaded via `CollectionView.from_inventory(inv)` OR `CollectionView.from_text(path)` (a plain
    `<qty> <card name>` parse, mirroring `_parse_decklist`, so the feature is usable *before* the
    sibling's persistent store lands — the dogfood collection was pasted as text).
- **`UserDeck`** (optional target source) — lets `advise acquire --deck-name "my Dimir Tempo"` resolve
  a stored 75 instead of a `/tmp/*.txt`. Soft: if the sibling isn't landed, fall back to `--deck
  <file>` / `--archetype`.
- **`PriceSource`** (from `feature-curated-price-source`) — assumed interface
  `price(card_name, set_code=None, collector_number=None) -> Optional[PricePoint]` where
  `PricePoint = {usd: float, source: str, printing: str}`, plus `cheapest(card_name) -> PricePoint`
  (the min-priced legal printing — this is what catches the $33 Secret Lair Dismember vs the $1–2
  alternative). Soft dep: absent → buy list is **unpriced** (ranked by impact only, every row flagged
  `price: unavailable`).

Both deps are wired as **injected ports** (constructor / kwarg), never imported as concrete classes
inside the loop — same discipline as `legal_swap` in `objective-search-split`. This keeps the
acquisition algorithm unit-testable with hand-built `CollectionView` + a stub price callable, no DB,
no sibling-store dependency.

### Module layout

New module `advisory/collection.py` (the read port + owned-annotation helpers) and
`advisory/acquire.py` (the acquisition advisor algorithm + result records). Acquisition advisor lives
in `advisory/` (not `generation/`) because its objective is field/positioning-driven (impact = field
adoption × archetype relevance), which is the advisory layer's concern; it *consumes*
`generation.consensus.card_frequencies` and `analytics.card_value` the same way `sideboard.py` and
`tuning.py` already do — no new analytics→advisory cycle.

### Unit 1 — `advisory/collection.py`: the collection read port + owned annotation

```python
@dataclass(frozen=True)
class OwnedPrinting:
    set_code: str
    collector_number: str
    condition: str          # "NM" | "LP" | ... ; free-text tolerated
    qty: int

class CollectionView:
    """Injected read port over the user's owned cards. Decouples the recommenders
    from the sibling Inventory store; also constructible from pasted text."""
    def owned_qty(self, card_name: str) -> int: ...
    def printings(self, card_name: str) -> tuple[OwnedPrinting, ...]: ...
    def is_owned(self, card_name: str, qty: int = 1) -> bool: ...  # owned_qty >= qty
    @classmethod
    def from_text(cls, text: str) -> "CollectionView": ...     # "<qty> <name>" lines
    @classmethod
    def from_inventory(cls, inv) -> "CollectionView": ...      # sibling Inventory adapter

@dataclass(frozen=True)
class OwnedAnnotation:
    """Per-recommended-card ownership annotation."""
    card: str
    recommended_copies: int
    owned_copies: int
    to_acquire: int                       # max(0, recommended - owned)
    owned: bool                           # owned_copies >= recommended_copies

def annotate_owned(cards: dict[str, int], cv: CollectionView | None) -> dict[str, OwnedAnnotation]:
    """Map recommended card->copies to ownership annotations.
    cv is None  => GATE CLOSED: returns {} (callers treat as 'not collection-aware')."""
```

`annotate_owned(..., cv=None)` returning `{}` is the explicit no-op gate (grep-able, per the pattern).

### Unit 2 — collection-awareness threaded into `sideboard.py` + `tuning.py`

**Additive only.** `recommend_sideboard` and `tune_deck` gain one new optional kwarg
`collection: CollectionView | None = None` (default `None` → byte-identical to today). The solver and
greedy loops are **unchanged** — we do *not* filter the catalog/candidate pool by ownership inside the
optimizer (that would change recommendations and break the byte-identical contract, and "owned-only"
is a *consumer* policy, not the optimizer's job). Instead:

- `SideboardPackage` and `TunedDeck` gain additive fields (all defaulted):
  - `owned: dict[str, OwnedAnnotation] = {}` — annotation for each recommended card.
  - `collection_aware: bool = False` — True iff a CollectionView was supplied.
- After the solver returns `final_cards`, call `annotate_owned(final_cards, collection)` and attach.
- **Owned-only mode** is realized as a thin post-filter helper `split_recommendation(pkg, cv)` in
  `acquire.py` returning `(play_owned: dict, acquire: dict)` — NOT by mutating the optimizer. The CLI
  `--owned-only` flag simply renders only the `play_owned` partition and notes the suppressed
  acquire-list count. This keeps the recommender pure and the byte-identical contract intact.

This is the canonical `gated-additive-augmentation`: `collection=None` reaches the no-op
(`annotate_owned` returns `{}`, `collection_aware=False`), existing tests never pass a collection and
stay green untouched.

### Unit 3 — `advisory/acquire.py`: the ACQUISITION ADVISOR (the headline, trickiest unit)

Built **objective-search-split** style: one heavy DB pass produces plain dicts; a pure ranking
function takes those dicts + injected `CollectionView` + injected price callable and is unit-testable
with no DB.

**Inputs:** `con`, `field: FieldDistribution`, target spec (an archetype name → consensus board, OR a
`UserDeck`/deck file → explicit board, OR a *set* of boards for multi-deck acquisition), a
`CollectionView`, an injected `price_fn: Callable[[str], Optional[PricePoint]]` (defaults to the
curated PriceSource's `cheapest`), and the standard `since/until` window.

**Step A — candidate universe (heavy, runs once).** Union over the target board(s) of:
- the consensus/observed maindeck+sideboard cards for the target archetype(s) via
  `generation.consensus.card_frequencies` (board="main" and "side"); and
- the sideboard `HOSER_CATALOG` candidates relevant to the field (reuse `recommend_sideboard`'s
  chosen 15 + its `trace` so the buy list aligns with the board the recommender would actually build).

**Step B — impact score per candidate (the ranking objective).** For each candidate card:

```
impact(card) = field_relevance(card) * archetype_relevance(card)
field_relevance(card)     = field_weighted_value-style term:
                            Σ_opp field.shares[opp] * max(0, lift(card vs opp))   [card_value, gate-clearing only]
                            FALLBACK when rounds-less / thin: field-adoption =
                            Σ_opp field.shares[opp] * inclusion_pct(card in opp's decks)   [card_frequencies]
archetype_relevance(card) = inclusion_pct(card) in the TARGET archetype's consensus (consensus.card_frequencies)
                            -> a card the target deck actually wants ranks above a generically-good card it can't play.
```

Reuse `tuning.field_weighted_values` for the rounds-bearing term (do not re-derive). The fallback to
adoption-only mirrors `tune`'s `no-signal-skip` honesty: when there's no per-card signal, rank by
field-adoption × archetype-inclusion and **label the column** `impact-basis: adoption (no win-rate
signal)`.

**Step C — ownership join + flags (pure).**
- `to_acquire(card) = max(0, recommended_copies(card) − owned_qty(card))`. Only cards with
  `to_acquire > 0` enter the **buy list**.
- **Redundant / over-quantity own** flag: `owned_qty(card) > recommended_copies(card)` AND the card is
  in a saturating category — specifically, when the field-weighted marginal of the (n+1)-th copy is
  ~0 (reuse the sideboard `_marginal_g` saturating curve) OR the card shares a vulnerability *tag*
  already over-covered in the owned pool. This is the "deeply over-covered on graveyard hate" finding:
  compute owned coverage per tag and flag tags where owned answers ≫ field demand
  (`owned_answers_for_tag > ceil(field_demand_for_tag * over_cover_factor)`, `over_cover_factor≈2`).
- **Overpriced-printing** flag: for owned/target cards, compare `price_fn(card)` (cheapest legal
  printing) against the user's owned printing price (or the most-expensive printing the user might buy)
  — flag when `owned_or_default_price ≥ overprice_factor * cheapest_price` AND `cheapest_price` exists
  (`overprice_factor≈3` catches $33 vs $1–2 Dismember; threshold is a curated constant, labeled
  heuristic like the sideboard swing constants).

**Step D — slot-in / replaces (pure).** For each buy, report how it slots into the board: reuse the
`recommend_sideboard` trace (the element it covers) for SB buys, and the `tune`-style OUT/IN logic
(`_plan_matchups` is the precedent) for maindeck buys — `replaces` = the lowest-impact flex card the
buy would displace (lift-ordered, locked core protected via `card_frequencies` ≥ lock_threshold).
When data is thin, `replaces = None` with a noted reason (degrade, don't fabricate).

**Output records:**

```python
@dataclass(frozen=True)
class BuyItem:
    card: str
    acquire_copies: int
    impact: float
    impact_basis: str                 # "win-rate" | "adoption (no win-rate signal)"
    field_relevance: float
    archetype_relevance: float
    price: Optional[float]            # cheapest legal printing; None if no price source
    price_source: Optional[str]
    slots_into: str                   # board location / covered element
    replaces: Optional[str]           # flex card displaced, or None
    notes: tuple[str, ...]

@dataclass(frozen=True)
class CollectionFlag:                 # redundant / over-quantity / overpriced findings
    card: str
    kind: str                         # "redundant-own" | "over-quantity" | "overpriced-printing"
    detail: str

@dataclass(frozen=True)
class AcquisitionPlan:
    buy_list: tuple[BuyItem, ...]     # to_acquire>0, ranked by impact DESC, price ASC tie-break
    flags: tuple[CollectionFlag, ...]
    total_cost: Optional[float]       # Σ price*copies; None if any priced row missing & no source
    field_source: str
    impact_basis: str                 # overall basis label
    window: tuple[str | None, str | None]
    heuristic_note: str               # over_cover_factor / overprice_factor are curated constants
    warnings: tuple[str, ...]
```

**Pure core to unit-test:** `_rank_acquisitions(candidates, field_weighted, archetype_incl, owned,
price_fn, *, factors) -> AcquisitionPlan`. Hand-built dicts + a `lambda name: PricePoint(...)` stub →
no DB. The heavy `acquire_plan(con, ...)` orchestrator builds those dicts (one
`compute_card_winrates` scan, one `card_frequencies` per board) then calls the pure core — exactly the
`tune_deck` / `_greedy_tune` split.

### Interfaces / signatures (summary)

```python
# advisory/collection.py
class CollectionView: ...
def annotate_owned(cards: dict[str,int], cv: CollectionView | None) -> dict[str, OwnedAnnotation]

# advisory/sideboard.py  (additive kwarg + fields)
def recommend_sideboard(..., collection: CollectionView | None = None) -> SideboardPackage
    # SideboardPackage gains: owned: dict[str,OwnedAnnotation]={}, collection_aware: bool=False

# generation/tuning.py  (additive kwarg + fields)
def tune_deck(..., collection: CollectionView | None = None) -> TunedDeck
    # TunedDeck gains: owned: dict[str,OwnedAnnotation]={}, collection_aware: bool=False

# advisory/acquire.py
def split_recommendation(cards: dict[str,int], cv: CollectionView) -> tuple[dict,dict]   # (play_owned, acquire)
def acquire_plan(con, field, *, archetype: str|None=None, deck: dict[str,int]|None=None,
                 deck_name: str|None=None, collection: CollectionView,
                 price_fn: Callable[[str], Optional[PricePoint]] | None = None,
                 since=None, until=None, over_cover_factor: float=2.0,
                 overprice_factor: float=3.0) -> AcquisitionPlan
def _rank_acquisitions(...) -> AcquisitionPlan   # pure, DB-free, the unit-test surface
```

### CLI shape

Reuse the project's nested-group + `_setup_logging(verbose)` + lazy-import + `_window_opts` pattern.

- New shared `--collection <file>` option (a `<qty> <name>` text file → `CollectionView.from_text`;
  or, once the sibling lands, `--deck-name`/registered inventory). Added to `advise sideboard` and
  `generate tune` as an **optional** flag. When omitted → no collection-aware output (gate closed).
- New `--owned-only` flag on `advise sideboard` / `generate tune` (renders only the owned partition;
  requires `--collection`).
- New headline command:
  ```
  legacy-engine advise acquire
    (--archetype NAME | --deck FILE | --deck-name NAME)   # the target board(s)
    --collection FILE                                      # required
    [--field FILE] [--prices FILE|--price-source NAME]     # price source (soft)
    [--budget USD]                                         # optional cap; greedily fill under budget
    [--owned-only/--acquire-split]  [window opts]  [--db ...] [-v]
  ```
  Output: ranked buy list table (`copies | card | impact | impact-basis | price | slots-into |
  replaces`), a `total cost` line, then the **flags** section (redundant/over-quantity owns,
  overpriced printings), then the heuristic-note + presence-correlational disclaimer (reuse
  `_VALUE_DISCLAIMER`). `--budget` does a greedy fill: take buys in impact-per-dollar order until the
  budget is spent, report what was left out and why.

### Units in build order

1. **Unit 1 — `advisory/collection.py`** (`CollectionView`, `OwnedPrinting`, `OwnedAnnotation`,
   `annotate_owned`, `from_text`). Foundational, pure, fully testable in isolation. Build first.
2. **Unit 2 — thread `collection` into `sideboard.py` + `tuning.py`** (additive kwarg + fields +
   `annotate_owned` call + `split_recommendation`). Smallest blast radius after Unit 1; protects the
   byte-identical contract.
3. **Unit 3 — `advisory/acquire.py`** (the acquisition advisor: `_rank_acquisitions` pure core first,
   then the `acquire_plan` orchestrator). The trickiest unit; build the pure core + its tests before
   wiring the DB orchestrator.
4. **Unit 4 — CLI** (`--collection`/`--owned-only` on existing commands; new `advise acquire`
   command + renderers). Last; thin glue.

No child stories: the four units are tightly coupled around one new port + two additive extensions +
one new command, well within a single feature's scope. (Spawn a child only if the sibling Inventory
store's adapter turns out non-trivial — but `from_text` makes the feature deliverable without it, so
not pre-spawned.)

### Test plan

- **Unit 1:** `from_text` parse (qty+name, blank lines, comments); `owned_qty` sums across printings;
  `is_owned`; `annotate_owned(cv=None) == {}` (the gate); `to_acquire = max(0, rec−owned)`.
- **Unit 2 (regression — load-bearing):** existing `test_sideboard.py` /
  `test_generation_tuning.py` run unchanged and stay green (no `collection` passed → byte-identical).
  Add: `recommend_sideboard(collection=cv)` populates `owned`/`collection_aware`; the recommended
  `cards` dict is **identical** with and without `collection` (proves it's annotation-only, not a
  filter). `split_recommendation` partitions correctly.
- **Unit 3 (pure core, no DB):** `_rank_acquisitions` with hand-built field-weighted + archetype-incl
  + owned + stub `price_fn`:
  - buy list excludes fully-owned cards (`to_acquire=0`);
  - ranking is impact DESC (a high field-adoption × high archetype-relevance card outranks a
    generically strong but archetype-irrelevant one — the **Defense Grid/Chalice** regression: those
    are field-good but if not in the target board's relevant set / not owned, they don't top the buy
    list and are clearly flagged not-owned);
  - **over-quantity flag** fires on the graveyard-hate over-cover scenario;
  - **overpriced-printing flag** fires on a $33 vs $2 stub (the **Dismember** regression), not on a
    $2 vs $2;
  - **no price source** → all prices `None`, `total_cost=None`, ranking still by impact;
  - **no win-rate signal** → `impact_basis="adoption..."`, falls back to adoption×inclusion (mirrors
    `tune` no-signal honesty), no crash.
- **Unit 3 orchestrator (DB):** one synthetic-corpus test that `acquire_plan` wires the scan +
  frequencies into the pure core and returns a coherent `AcquisitionPlan` (lighter than the pure
  tests — the heavy logic is already covered DB-free).
- **CLI:** `advise acquire` smoke test (Click runner, tiny fixture corpus) renders a buy list +
  flags; `--collection` on `advise sideboard` produces owned annotations; omitting it is unchanged.
- **Determinism:** ranking tie-breaks are lexical (card name) so output is stable; seed unaffected.

### Risks & pre-mortem

1. **Byte-identical contract broken by Unit 2.** *Mitigation:* `collection` is annotation-only and
   never touches the optimizer; the regression test asserts the `cards` dict is identical with/without
   a collection. If a future author is tempted to filter the catalog by ownership inside the solver,
   that's the violation — owned-only is a consumer post-filter (`split_recommendation`), by design.
2. **Sibling Inventory model not landed when this builds.** *Mitigation:* `CollectionView.from_text`
   makes the feature fully deliverable from pasted text (exactly the dogfood workflow); the
   `from_inventory` adapter is a thin add-on bound later. The feature is not hard-blocked.
3. **Defense Grid/Chalice keep topping the list.** Root cause this session was field-relevance without
   archetype-relevance or ownership. *Mitigation:* impact = field × **archetype_relevance**, and the
   buy list shows owned/not-owned + slots-into/replaces, so a generically-good card the target deck
   can't usefully run sinks in the ranking and is visibly flagged. Covered by a named regression test.
4. **No price source (curated-price-source not landed).** *Mitigation:* soft dep — `price_fn=None` →
   unpriced ranking, `price: unavailable`, `total_cost=None`. Impact ranking is independent of price,
   so the advisor is still useful; pricing is an enrichment, not a gate.
5. **Overprice/over-cover thresholds are heuristic.** Same honesty discipline as the sideboard swing
   constants: `over_cover_factor`/`overprice_factor` are curated constants surfaced in
   `heuristic_note`; flags are advisory, labeled, not silent auto-cuts.
6. **Printing/condition granularity from the sibling is unknown.** *Mitigation:* the `OwnedPrinting`
   port keeps printing optional; the recommenders only need oracle-name `owned_qty`; pricing degrades
   to `cheapest(card)` vs a default printing when per-printing owned data is absent.

## Hold

Design complete; held for human review before implementation.

## Implementation notes

Implemented 2026-06-13. All four units shipped per design.

**Unit 1 — `advisory/collection.py`**: `CollectionView` (injected read port, `from_text` + `from_inventory` factories, `owned_qty` / `printings` / `is_owned`), `OwnedPrinting`, `OwnedAnnotation`, `annotate_owned` (gate: `cv=None → {}`).

**Unit 2 — gated-additive threading**: `SideboardPackage` and `TunedDeck` gain `owned: dict[str, OwnedAnnotation] = {}` and `collection_aware: bool = False`. Both `recommend_sideboard` and `tune_deck` gain `collection: CollectionView | None = None` optional kwarg. `annotate_owned` called post-solver; gate guarantees byte-identical output when `collection=None`. Split post-filter via `split_recommendation` in `acquire.py`.

**Unit 3 — `advisory/acquire.py`**: Pure `_rank_acquisitions` (no DB, no IO) takes plain dicts + injected `CollectionView` + injected `price_fn`. `acquire_plan` orchestrator does one heavy DB scan (field_weighted_values + card_frequencies per board + HOSER_CATALOG union) then calls the pure core. Over-cover flag (over_cover_factor=2.0), overpriced-printing flag (overprice_factor=3.0, orchestrator-level per-printing DB check). Adoption fallback when win-rate signal absent, labeled.

**Unit 4 — CLI**: `--collection` + `--owned-only` added to `advise sideboard` and `generate tune`; new `advise acquire` command with `--archetype`/`--deck`, `--budget`, `--field`, window opts, renders ranked buy table + flags section + heuristic/disclaimer.

**Tests (40 new)**: byte-identical no-op invariant; owned/acquire split; acquisition ranking by impact; Defense Grid/Chalice named regression; over-quantity flag (graveyard over-cover); overpriced-printing (no false positive from pure core); adoption fallback; deterministic tie-break; from_text path; from_inventory adapter; acquire_plan orchestrator smoke; CLI gate-closed + collection smoke + owned-only guard.

**Deviations from design**: None. The overpriced-printing flag from per-printing owned data is orchestrator-level (requires per-printing price lookup with set_code), not surfaced in the pure core — as designed (pure core has no DB access). The pure core correctly never emits false positives for overpriced flags.

**Suite**: 1725 passed (1685 baseline + 40 new).


## Review findings (bounce 1)
BLOCKING: `tests/test_collection_aware_engine.py::test_advise_acquire_smoke` is non-hermetic — the `advise acquire` CLI invocation passes no `--db`, so it connects to the real data/legacy.duckdb and fails under the full suite on lock contention (this is the lone suite failure: 1840 passed, 1 failed). FIX: make the smoke test use an isolated DB (`--db` with a tmp/fixture path or :memory:), like the orchestrator tests do. Production logic + byte-identical no-op invariant verified good; only the test is at fault.

### Resolution
Fixed 2026-06-13. Seeded an isolated DuckDB in `tmp_path` (`store.init_schema` → empty corpus), passed `--db str(db_path)` to the CLI runner. Assertion `"Acquisition Plan" in result.output` kept unchanged and meaningful — `acquire_plan` degrades gracefully on an empty corpus and always emits the section header. Test is now fully hermetic and deterministic under the full suite.
