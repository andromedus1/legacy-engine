---
id: epic-gap-discovery-adjacency
kind: feature
stage: done
tags: [generation, discovery]
parent: epic-gap-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Card-Adjacency Model (candidate nomination)

## Brief

The nomination engine for card-level discovery: given a shell `D` (archetype `A`, color
identity `C(D)`), produce the set of cards the deck does **not** already run but that are
plausible swap-in candidates. Per the brief's v1 recommendation, a card `X` is a candidate
when ALL hold: (1) not already in `D`; (2) color-legal (`X.colors ⊆ C(D)`, front-face colors
via the layout-aware card rows); (3) role-relevant (`_card_roles(X)` intersects the roles the
shell's flexible slots want); (4) within the shell's flexible-slot CMC band. Survivors are
then **ranked by decklist co-occurrence lift** — PMI of `X` against the archetype's locked
core over the corpus (`deck_cards`, 63k decks), the auditable heuristic analogue of card2vec.

Delivered as a new `src/legacy_engine/generation/discovery.py` module, kept deliberately
**out of `tuning.py`** (tuning stays the proven-swap engine; discovery composes alongside it).
It reuses, does not rebuild: `advisory/whattoplay._card_roles` (role classifier),
`card_tags` (staple roles + mana-base tags), `models/card.Card` colors/cmc/type_line, and a
`deck_cards` co-occurrence query (mirroring `generation/consensus.card_frequencies`). All
corpus stats use the tuner's window (latest ban regime).

Does NOT cover value scoring or confidence-gating of candidates — this feature only nominates
and ranks by adjacency/co-occurrence. The evidence layer (cross-archetype per-card value
transfer + the honest confidence gate + the CLI surface) is `epic-gap-discovery-discovery-tuning`,
which consumes this feature's candidate list.

## Epic context

- Parent epic: `epic-gap-discovery`
- Position in epic: foundation feature — `epic-gap-discovery-discovery-tuning` depends on the
  candidate-nomination types/output this feature defines.

## Inherited design decisions

- **Module placement = new `generation/discovery.py`**, separate from `tuning.py`.
- **Adjacency v1 = role-match ∩ color-legal ∩ CMC-band, RANKED by decklist co-occurrence (PMI)** —
  embeddings (card2vec / oracle-text sentence-transformers) are a documented later upgrade,
  not a v1 dependency.
- **Reuse `_card_roles`** as the single role source (already feeds whattoplay/sideboard).
- **Windowing**: corpus co-occurrence uses the tuner's latest-ban-regime window; thread the
  same `since/until` and reuse one `CardWinRates`/frequency aggregate where the sibling needs it
  (per `fix-tuning-sideboard-winrate-reuse`).
- **Edge cases (from brief §Implementation Notes)**: candidate already in the sideboard (not
  maindeck) is still a valid discovery for the 60; multi-face → front-face rows; colorless
  always color-legal; no role match → excluded (no basis); never-paired cards (PMI undefined) →
  exclude, do not impute.

## Research briefs

- `docs/briefs/card-adjacency-and-discovery.md` §0 (reuse inventory), §1 (the adjacency model —
  the four gating conditions + the PMI rank).

## Foundation references

- `src/legacy_engine/advisory/whattoplay.py` — `_card_roles(card)` (oracle-text role classifier).
- `src/legacy_engine/card_tags.py` — `staple_role`, `mana_base_tags`.
- `src/legacy_engine/models/card.py` — `Card.colors`, `Card.cmc`, `Card.type_line` (layout-aware).
- `src/legacy_engine/generation/consensus.py` — `card_frequencies` + `_latest_regime_window`
  (the corpus query + windowing pattern to mirror for co-occurrence).

## Design decisions

Resolved with judgment during feature-design (autopilot delegation); all are feature-level
mechanics, not strategic forks (those were locked at the epic):

- **Candidate universe = co-occurrence-derived, not whole-corpus**: candidates are drawn from
  cards that appear in decks running the archetype's locked core (≥ overlap threshold), not from
  every card in `deck_cards`. This naturally excludes never-paired cards (PMI undefined → the
  brief says exclude, don't impute) and bounds the scan to relevant cards.
- **"Runs the core" overlap threshold** `k = max(3, ceil(0.6 × |core|))` core cards present —
  a deck must run a clear majority of the locked core to count as "this shell" for co-occurrence.
- **Locked core** = archetype cards with `inclusion_pct ≥ 0.65` (reuse tuning's
  `_DEFAULT_LOCK_THRESHOLD` via `card_frequencies`), so "core" matches what the tuner locks.
- **Roles the shell wants** = the union of `_card_roles` over the deck's **flex** non-land cards
  (from `tuning.partition_flex`) — flex is the swappable surface, so its role mix defines demand.
  A candidate must share ≥1 role.
- **CMC band** = median flex non-land CMC ± 1 (brief §1.2), lands excluded from the median.
- **Co-occurrence floor**: require ≥ 5 decks running candidate-AND-core before computing PMI, so
  a lift isn't fabricated off one or two decks (below the floor → excluded, not imputed).
- **Card loader placement**: add a shared `load_card(con, name) -> Card | None` to
  `ingestion/store.py` (SSOT home for the colors/produced-mana serialization round-trip) rather
  than duplicate `whattoplay._load_deck_cards`'s private reconstruction. `whattoplay` can adopt it
  later (out of scope here).
- **Color identity `C(D)`** = union of `card.colors` over all of D's cards; colorless candidates
  (empty `colors`) are always color-legal.

## Architectural choice

Three shapes were considered for the candidate universe + ranking:

- **(A) Whole-corpus scan** — compute PMI(X, core) for every card in the window not in D.
  Complete but expensive (thousands of cards × a self-join) and forces handling of PMI-undefined
  never-paired cards.
- **(B) Co-occurrence-derived universe (chosen)** — start from the set of cards that appear in
  decks running ≥k of the archetype's locked core. PMI is well-defined for every member (they
  co-occur by construction), the scan is bounded to relevant cards, and the brief's
  "never-paired → exclude" falls out for free. One windowed self-join over `deck_cards`.
- **(C) Union of other archetypes' `candidate_pool`s** — misses cross-archetype cards the field
  pairs with this shell that aren't in any *named* archetype's observed pool — exactly the
  discovery signal we want. Rejected.

(B) is chosen: it is the auditable, bounded analogue of card2vec the brief calls for, and it
composes the existing `card_frequencies`/windowing primitives without new infrastructure.

## Implementation Units

### Unit 1: `load_card` shared loader

**File**: `src/legacy_engine/ingestion/store.py` (additive — next to `fetch_card`)

```python
def load_card(con: duckdb.DuckDBPyConnection, name: str) -> Card | None:
    """Resolve a card name to a fully reconstructed Card, or None if absent.

    SSOT for the cards-table round-trip: undoes the joined-string serialization
    of ``colors`` / ``produced_mana`` that ``load_cards`` applies. Mirrors the
    reconstruction currently inlined in ``whattoplay._load_deck_cards``.
    """
```

**Implementation Notes**:
- Wrap `fetch_card`; on `None` return `None`. Reconstruct `colors`/`produced_mana` from joined
  strings (`list(raw) if raw else []`); pass `power`/`toughness` through; `Card.model_validate(row)`.
- Do NOT refactor `whattoplay._load_deck_cards` in this feature — just provide the shared home.

**Acceptance Criteria**:
- [ ] `load_card(con, "Brainstorm")` returns a `Card` with `colors == ["U"]`.
- [ ] `load_card(con, "<absent>")` returns `None`.
- [ ] A multi-color card round-trips colors correctly (e.g. `["U","B"]`).

---

### Unit 2: `AdjacencyCandidate` dataclass

**File**: `src/legacy_engine/generation/discovery.py` (new module)

```python
@dataclass(frozen=True)
class AdjacencyCandidate:
    name: str
    card: Card
    roles: frozenset[str]          # _card_roles(card), intersected demand is non-empty
    matched_roles: frozenset[str]  # roles ∩ shell-wanted roles (the audit trail)
    cmc: float
    pmi: float                     # log lift vs the archetype core
    decks_running: int             # P(X) numerator (window decks running X)
    cooccur_decks: int             # decks running X AND core (≥ floor)
    in_sideboard: bool             # candidate already in D's sideboard (still a valid 60 discovery)
```

**Acceptance Criteria**:
- [ ] Frozen dataclass; `pmi` and counts populated by `adjacency_candidates`.

---

### Unit 3: shell profile — `_shell_profile`

**File**: `src/legacy_engine/generation/discovery.py`

```python
@dataclass(frozen=True)
class ShellProfile:
    core: frozenset[str]          # locked-core card names (inclusion ≥ lock_threshold)
    wanted_roles: frozenset[str]  # union of _card_roles over flex non-land cards
    cmc_lo: float                 # median flex non-land CMC − 1
    cmc_hi: float                 # median flex non-land CMC + 1
    color_identity: frozenset[str]  # union of card.colors over all of D

def _shell_profile(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    *,
    lock_threshold: float = 0.65,
    since: str | None = None,
    until: str | None = None,
) -> ShellProfile:
```

**Implementation Notes**:
- Core: `card_frequencies(con, archetype, board="main", ...)` filtered to `inclusion_pct ≥ lock_threshold`.
- Flex: `partition_flex(con, archetype, maindeck, ...)`; take the flex dict, load each via `load_card`,
  drop lands, union `_card_roles`; median CMC over flex non-lands (count-weighted is unnecessary —
  use distinct flex cards' CMCs for the band).
- `color_identity`: union of `card.colors` for every loaded card in `maindeck`.
- Empty flex (everything locked) → `wanted_roles` empty → no candidates surface (correct: nothing to swap).

**Acceptance Criteria**:
- [ ] A flex pool of {counter, removal} cards yields `wanted_roles ⊇ {counter, removal}`.
- [ ] `cmc_lo/hi` straddle the median flex CMC by ±1; lands excluded from the median.
- [ ] `color_identity` is the union of all maindeck cards' colors.

---

### Unit 4 (trickiest): co-occurrence PMI — `_cooccurrence`

**File**: `src/legacy_engine/generation/discovery.py`

```python
@dataclass(frozen=True)
class _CooccurCounts:
    total_decks: int                  # in-window decks (the universe denominator)
    core_decks: int                   # decks running ≥k core cards  → P(core)
    per_card: dict[str, tuple[int, int]]  # name -> (decks_running_X, decks_running_X_and_core)

def _cooccurrence(
    con: duckdb.DuckDBPyConnection,
    core: frozenset[str],
    *,
    k: int,
    since: str | None,
    until: str | None,
    cooccur_floor: int = 5,
) -> _CooccurCounts:
```

**Implementation Notes** (the trickiest unit — design it first):
- One windowed pass over `decks ⋈ tournaments` + `deck_cards` (board='main'). CTEs:
  - `deck_pool` — (tournament_id, deck_idx) for in-window decks (date/provenance filters, mirror
    `card_frequencies`); `total_decks = count(*)`.
  - `core_hits` — per deck, `count(*)` of distinct `dc.name IN core`; a deck "runs core" when that
    count `≥ k`. `core_decks = count of decks with core_hits ≥ k`.
  - `card_decks` — per `dc.name`: `decks_running_X = count(distinct deck)`, and
    `decks_running_X_and_core = count(distinct deck where that deck is a core-runner)`.
- Candidate universe = names appearing in a core-runner deck (so co-occurrence ≥ 1 by construction),
  then drop names with `decks_running_X_and_core < cooccur_floor`.
- Return raw counts; PMI is computed in Python (Unit 5) to keep the SQL count-only and testable.
- `k` from the caller (`max(3, ceil(0.6·|core|))`); guard `core` empty → return zero universe.

**Acceptance Criteria**:
- [ ] On a hand-built fixture (cores + co-runners), `core_decks` counts exactly the decks with ≥k core.
- [ ] `per_card[X]` reports the correct (running, running-with-core) deck counts.
- [ ] Cards below `cooccur_floor` co-occurrence are absent from `per_card`.

---

### Unit 5: public entry — `adjacency_candidates`

**File**: `src/legacy_engine/generation/discovery.py`

```python
def adjacency_candidates(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
    *,
    lock_threshold: float = 0.65,
    cooccur_floor: int = 5,
    limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[AdjacencyCandidate]:
    """Nominate + rank cards adjacent to deck D that D does not already run.

    Pipeline: shell profile → co-occurrence counts → for each universe card:
    gate (∉ D, color-legal, role-relevant, CMC-band), compute PMI, keep if defined,
    rank by PMI DESC. Returns at most ``limit`` candidates (all when None).
    """
```

**Implementation Notes**:
- `since/until` default to `_latest_regime_window()` when both None (mirror siblings).
- Build `ShellProfile`; `k = max(3, ceil(0.6 * len(core)))`; `_cooccurrence(...)`.
- For each `name` in `per_card` not in `maindeck`: `card = load_card(...)` (skip None);
  gates — color-legal (`set(card.colors) ⊆ color_identity` or colorless), role-relevant
  (`_card_roles(card) ∩ wanted_roles ≠ ∅`), CMC-band (`cmc_lo ≤ card.cmc ≤ cmc_hi`).
  - `PMI = log( (cnt_X_core/total) / ((cnt_X/total) * (core_decks/total)) )`.
  - `in_sideboard = name in (sideboard or {})`.
- Sort by `pmi` DESC, tie-break `cooccur_decks` DESC then `name` ASC for determinism. Apply `limit`.

**Acceptance Criteria**:
- [ ] A card already in `maindeck` never appears in the result.
- [ ] An off-color card (colors ⊄ C(D)) is excluded; a colorless card is allowed.
- [ ] A card whose roles don't intersect `wanted_roles` is excluded.
- [ ] A card outside the CMC band is excluded.
- [ ] Results are sorted by PMI DESC and respect `limit`.
- [ ] A candidate present in D's sideboard surfaces with `in_sideboard=True`.

## Implementation Order

1. **Unit 1 `load_card`** — shared dependency; nothing else loads cards without it.
2. **Unit 4 `_cooccurrence`** — trickiest; the SQL feasibility gates the whole feature.
3. **Unit 2 `AdjacencyCandidate`** + **Unit 3 `_shell_profile`** — the typed surfaces.
4. **Unit 5 `adjacency_candidates`** — composes 1–4 + the four gates + PMI + ranking.

## Testing

### Unit tests: `tests/generation/test_discovery.py`
- `load_card` (store): known card colors round-trip, absent → None, multicolor split. (May live in
  `tests/ingestion/test_store.py` next to `fetch_card` tests — place with its module.)
- `_shell_profile`: wanted-roles union over flex, CMC band ±1 (lands excluded), color identity union.
- `_cooccurrence`: hand-built in-memory DuckDB with `decks`/`tournaments`/`deck_cards` rows —
  verify core_decks (≥k), per_card counts, and cooccur_floor exclusion. Reuse the rounds/deck-corpus
  fixture style from `conftest.py` (the `make_rounds_corpus`-adjacent deck fixtures).
- `adjacency_candidates`: each gate (in-deck, color, role, CMC) excludes the right card; PMI ordering;
  `in_sideboard` flag; `limit` honored; empty flex → empty result.

### Integration tests
- End-to-end on a small seeded fixture: a known archetype + a plausible maindeck → returns
  on-role, color-legal, on-curve candidates not in the deck, ranked. Assert determinism
  (stable order across two calls).

## Risks

- **PMI sparsity for niche cards** — the `cooccur_floor` (≥5) drops thin candidates rather than
  imputing; acceptable for v1 (brief §1.3 flags embeddings as the later upgrade). **Fallback**:
  lower the floor or surface fewer candidates; no design change.
- **`k` too strict on small cores** — `max(3, …)` could exclude legitimate co-runners for tiny
  archetypes. **Fallback**: `k` is a parameter; the `0.6` fraction is tunable without restructuring.
- **Median-CMC band too tight** for bimodal curves (aggro-control). **Fallback**: band width is a
  constant (±1) easily widened; documented as a tuning lever, not load-bearing.

## Implementation notes
- Files changed: `src/legacy_engine/ingestion/store.py` (+`load_card`), `src/legacy_engine/generation/discovery.py` (new — Units 2–5).
- Tests added: `tests/test_generation_discovery.py` (15: ShellProfile×2, Cooccurrence×3, AdjacencyCandidates×6 + helpers), `tests/test_store.py` (+3 `load_card`).
- Suite: 982 passing (was 961, +21). `ruff check` clean on both touched files. mypy errors present are all pre-existing in other modules (report.py/charts.py) and not a CI gate.
- Discrepancies from design: none. Built exactly to Units 1–5. The empty-band sentinel (`cmc_lo=1.0, cmc_hi=-1.0`) makes an all-locked deck surface zero candidates as designed.
- Implementation detail: `_cooccurrence` uses three windowed CTE passes (universe per-card counts, total decks, core-deck count) rather than one mega-query — keeps each count independently assertable and matches `card_frequencies`' window-filter shape. PMI computed in Python from raw counts (SQL stays count-only, unit-testable).
- Adjacent issues parked: none.

## Review record
- **Verdict: Approve** (deep lane, fresh-context Opus sub-agent — NOT cross-model; Codex/peeragent out of credits).
- Verified: PMI formula + shared denominator + log/divide guards; the three `_cooccurrence` CTE passes (live-DuckDB check of `count(DISTINCT (a,b))` + CASE NULL exclusion); window filter matches `card_frequencies`; all four gates correct + non-vacuous; edge cases (empty core/flex, sentinel band, sideboard flag, cooccur_floor exclusion); determinism; hand-computed `log(41/37)` confirmed; `load_card` byte-faithful to whattoplay reconstruction.
- No Blockers, no Important. 3 nits (all design-sanctioned, no action): (1) flex partition inlined rather than via `partition_flex` — functionally identical, avoids a redundant `card_frequencies` call; (2) `provenance` filter omitted from `_cooccurrence` — no-op on the default path, corpus-wide co-occurrence intentionally un-narrowed; (3) `_card_roles` private cross-module import — explicitly directed by the brief.
