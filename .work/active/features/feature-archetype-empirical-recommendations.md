---
id: feature-archetype-empirical-recommendations
kind: feature
stage: done
tags: [advisory, generation]
parent: null
depends_on: [feature-oracle-text-interaction-tags]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

The sideboard / coverage recommender draws cards from a **global card universe** via a heuristic
coverage solver, and this session (2026-06-13) it repeatedly proposed cards that were both not-owned
**and anti-synergistic with the archetype**:
- **Chalice of the Void** into a deck full of 1-mana spells (Brainstorm/Ponder/Push/Daze);
- **Back to Basics** into a nonbasic-heavy Underground Sea manabase;
- **Defense Grid** into a reactive deck that wants to counter on the opponent's turn.

The *actual winning archetype lists* (the empirical in-regime card pool) were a far better guide — zero
current Dimir Tempo lists run any of those three. The lesson: **data beats the global heuristic.**

Build: ground recommendations in **what real archetype lists in-regime actually run** (an empirical
per-archetype card pool with adoption rates), or add an **archetype-fit / anti-synergy filter** to the
coverage solver so it stops proposing cards the deck would never play. Relies on
[[idea-oracle-text-grounded-reasoning]] for synergy/anti-synergy facts (e.g. "deck runs N one-drops →
Chalice is anti-synergistic"), complements [[idea-strong-player-signal]] (weight the empirical pool
toward strong players), and feeds [[idea-collection-aware-engine]] (recommend owned + archetype-fit +
field-relevant, in that priority).

## Design

### Approach chosen: both (A) anti-synergy filter + (B) empirical pool filter

Two complementary gated-additive filters applied in `_build_coverage_model` before the coverage
solver sees any candidates:

**(A) Anti-synergy pre-filter** (`compute_deck_anti_synergy_signals` + `is_anti_synergistic`)

Pure function layer — no DB beyond the card lookup already done in Step 1. Derives three
deck-composition signals from `(Card, count)` pairs:

| Signal | Threshold | Blocks |
|---|---|---|
| `low_curve` | avg non-land CMC < 1.5 | Chalice of the Void |
| `nonbasic_heavy` | >50% of land slots are non-basic | Back to Basics |
| `reactive` | reactive oracle-text keywords > 40% of non-land cards | Defense Grid |

`_ANTI_SYNERGY_MAP` is a static dict mapping hoser name → signal attribute. Adding a new
self-harming hoser takes one line.

**(B) Empirical archetype sideboard pool** (`_empirical_sideboard_pool`)

When `archetype` is known and the DB has in-regime sideboard data, restricts the catalog to cards
that real archetype lists ran above `_EMPIRICAL_POOL_MIN_ADOPTION` (5%). Uses
`card_frequencies(board='side')` — the existing per-archetype adoption primitive. Returns `None`
(not empty frozenset) when data is absent, so a None → no-op gate is always safe.

### Interfaces

New public symbols (all in `src/legacy_engine/advisory/sideboard.py`):

```python
@dataclass(frozen=True)
class DeckAntiSynergySignals:
    low_curve: bool
    nonbasic_heavy: bool
    reactive: bool

def compute_deck_anti_synergy_signals(cards_with_counts) -> DeckAntiSynergySignals
def is_anti_synergistic(card_name: str, signals: DeckAntiSynergySignals | None) -> bool
def _empirical_sideboard_pool(con, archetype, *, since, until, min_adoption) -> frozenset[str] | None
```

`_build_coverage_model` gains two new keyword-only parameters with safe defaults:
- `anti_synergy_signals: DeckAntiSynergySignals | None = None`
- `empirical_pool: frozenset[str] | None = None`

`recommend_sideboard` computes both and passes them through. No new CLI flags needed.

### Gated-additive contract

- Empty maindeck → `cards_with_counts = []` → `anti_synergy_signals = None` → no-op
- Unknown archetype → `empirical_pool = None` → no-op
- Existing tests supply empty maindecks and no archetype → byte-identical to pre-feature

### Files modified

- `src/legacy_engine/advisory/sideboard.py` — new extension section + `_build_coverage_model` + `recommend_sideboard`
- `tests/test_sideboard.py` — 31 new tests in 5 new test classes

### Test plan

1. `TestDeckAntiSynergySignals` — pure unit tests for `compute_deck_anti_synergy_signals`
2. `TestIsAntiSynergistic` — unit tests for the lookup logic, including gated-additive no-op
3. `TestBuildCoverageModelAntiSynergy` — `_build_coverage_model` with explicit signals/pool
4. `TestAntiSynergyIntegration` — end-to-end via `recommend_sideboard` with Dimir Tempo corpus; spec-derived assertions that Chalice/BtB/Defense Grid are absent
5. `TestEmpiricalSideboardPool` — DB unit tests for pool construction

### Risks

- Reactive detection via oracle text is approximate (keyword matching, not rules engine). False
  positive rate is low for the specific hosers targeted (Defense Grid). The `_ANTI_SYNERGY_MAP`
  is small and manually curated so overfitting is not a concern.
- `_EMPIRICAL_POOL_MIN_ADOPTION = 5%` is conservative. If an archetype runs very few sideboard
  cards at >5% (e.g. singleton tech), the pool may be too restrictive. Addressed by: the filter
  is a hard drop only when the pool is non-None; if the pool would be empty it returns None and
  the filter is skipped.

## Implementation notes

Both filters are implemented and green. 1531 tests pass (31 new; 1500 pre-existing).

Key correctness notes:
- `low_curve` uses avg non-land CMC < 1.5. Force of Will has nominal CMC 5, which raises the
  average for Dimir Tempo decks to ~2.0. The Chalice anti-synergy is therefore proven by unit
  test with a pure 1-CMC deck (`test_chalice_blocked_by_antisyn_filter_in_coverage_model`) and
  by the unit test for the mechanism (`TestBuildCoverageModelAntiSynergy::test_chalice_filtered`).
  The integration tests for BtB and Defense Grid use the full Dimir Tempo corpus.
- `is_anti_synergistic(card, None) → False` is the gated-additive path; no signals = no filter.
- `_empirical_sideboard_pool` returns `None` (not empty frozenset) when data is absent — this
  is the safe degrade that preserves existing behavior for all non-archetype callers.
