---
id: epic-deck-generation-consensus
kind: feature
stage: implementing
tags: [generation]
parent: epic-deck-generation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Consensus baseline deck generation

## Brief

Generate a faithful "what wins now" decklist for an archetype by aggregating the field: for each card,
inclusion-% across that archetype's decks in the target window × its modal count, greedily filling 60
maindeck + 15 sideboard. This is generation **mode 1** (the floor, pure data aggregation over existing
analytics — no advisory heuristics, so it ships independently of the tuning feature). Establishes the
net-new `src/legacy_engine/generation/` module seam and the `generate` CLI group that the tuning feature
extends.

The known mode-1 limitation must be handled here: modal-count greedy fill can over/undershoot 60 and
double-list flex cards across main/side — the generator **reconciles to a legal, exactly-60 maindeck +
≤15 sideboard, de-duped list**, validated via `ingestion/banlist.validate_deck` against the as-of-date ban
snapshot. Generates against the windowed latest ban-regime by default (overridable).

Does NOT cover field-tuning (mode 2) or gap-discovery (mode 3, deferred from this epic).

## Epic context
- Parent epic: `epic-deck-generation`
- Position in epic: foundation feature — establishes `generation/` + the `generate` CLI group; the
  field-tuning feature depends on it.

## Inherited design decisions
From the parent epic `## Design decisions` (fixed inputs):
- **Module seam**: net-new `src/legacy_engine/generation/` composing `analytics/` (`metashare` + `deck_cards`
  aggregates) + `ingestion/banlist`; CLI under a `generate` group.
- **Field default**: windowed latest ban-regime (reuse `trends` regime windowing); user-overridable.
- **Legality**: always `validate_deck` against the as-of-date ban snapshot; output must be exactly-60 + de-duped.
- Pure, offline, reproducible — zero network calls.

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` §2.1–2.2 (mode 1), §2.4 (data-quality realities).
- `docs/briefs/advisory-methods.md` — the layers consumed.

## Foundation references
- `docs/ARCHITECTURE.md` — the deferred `generation/` seam.
- `src/legacy_engine/analytics/metashare.py`, `deck_cards` aggregates; `src/legacy_engine/ingestion/banlist.py`.

## Architectural choice

Net-new `src/legacy_engine/generation/` package composing existing analytics + banlist; **no new external
deps, zero network calls** (Ports & Adapters: a query layer reads DuckDB, a pure assembler builds the list,
the CLI is the adapter). Consensus establishes the package + the `generate` CLI group that
`epic-deck-generation-tuning` extends. Single-stride feature — one coherent module, no child stories.

Chosen approach for the exactly-60 reconciliation (the trickiest unit): **rank flex candidates by
`inclusion_pct × modal_count`-weighted score, fill to the target board sizes, then reconcile** — lock cards
by descending inclusion-%, assign each its modal count, and when the running total would cross 60 (main) /
15 (side), take the partial count that lands exactly on the cap; de-dupe a card appearing in both boards by
keeping it in the board where its inclusion-% is higher. Rejected alternative: pure greedy add of whole
modal stacks (the prototype's bug — over/undershoots 60 and double-lists flex), which is exactly what this
feature must fix.

## Implementation Units

### Unit 1: Generation package skeleton + result type
**File**: `src/legacy_engine/generation/__init__.py`, `src/legacy_engine/generation/models.py`
```python
@dataclass
class GeneratedDeck:
    archetype: str
    maindeck: dict[str, int]      # name -> count, sums to 60
    sideboard: dict[str, int]     # name -> count, sums to <= 15
    window: tuple[str | None, str | None]   # (since, until) the corpus was drawn from
    sample_n: int                 # # archetype decks the consensus was built from
    legality_errors: list[str]    # from validate_deck; empty = legal
```
**AC**: importable; `GeneratedDeck` carries the corpus window + sample size for the audit trail.

### Unit 2: Per-archetype card-frequency query
**File**: `src/legacy_engine/generation/consensus.py`
```python
def card_frequencies(con, archetype: str, *, board: str, since=None, until=None,
                     provenance=None) -> list[CardFreq]:
    # CardFreq(name, inclusion_pct, modal_count, decks_running)
    # over decks d JOIN deck_cards dc ... WHERE d.archetype = ? AND dc.board = ?
    #   AND window/provenance filters; inclusion_pct = decks_running / archetype_deck_count;
    #   modal_count = most common dc.count for that card.
```
**Notes**: window defaults to the latest ban-regime (reuse the `trends` regime-window helper); pass `(since,
until)` through. **AC**: a card run by 8/10 archetype decks at 4 copies → `inclusion_pct=0.8, modal_count=4`.

### Unit 3: Consensus assembly + exactly-60 reconciliation (trickiest — build first)
**File**: `src/legacy_engine/generation/consensus.py`
```python
def build_consensus(con, archetype, *, since=None, until=None, provenance=None,
                    main_size=60, side_size=15) -> GeneratedDeck:
    # rank main/side CardFreq by (inclusion_pct desc, modal_count desc); assign modal counts;
    # reconcile to exactly main_size / <= side_size (partial last stack to hit the cap);
    # de-dupe cross-board by higher inclusion_pct; then validate_deck(as-of latest ban snapshot).
```
**AC**: maindeck sums to exactly 60; sideboard ≤ 15; no card exceeds its copy limit; no card double-listed
across boards; `legality_errors == []` for a real archetype; thin archetype (sample_n small) still returns a
legal list and a low `sample_n`.

### Unit 4: `generate` CLI group + `generate consensus` leaf
**File**: `src/legacy_engine/cli.py`
```python
@main.group()
def generate() -> None: ...
@generate.command("consensus")
@click.option("--archetype", required=True) ... --since --until --provenance --db --verbose
# prints the list as <qty> <name> + Sideboard, plus sample_n / window / legality footer.
```
**AC**: `legacy-engine generate consensus --archetype "Izzet Delver"` prints a legal 60+≤15 list with a
corpus-window + sample-size footer; unknown archetype → clean `ClickException`.

## Implementation Order
1. Unit 3 reconciliation logic (spike the exactly-60 + de-dupe on a fixture first — the rest hangs on it).
2. Units 1-2 (skeleton + query), 4 (CLI) follow.

## Testing
- `tests/test_generation_consensus.py` — fixture archetype with known card frequencies: assert exactly-60,
  ≤15 side, copy-limit respect, cross-board de-dupe, `legality_errors==[]`, thin-sample still legal,
  window filtering. Reuse `tests/conftest.py` DuckDB fixtures.
- CLI test in `tests/test_cli.py` — `generate consensus` happy path + unknown archetype.

## Risks
- **Reconciliation edge cases** (archetype whose modal counts can't sum to 60 cleanly): partial-stack-to-cap
  handles it; if a board can't reach 60 from the observed pool, fill remaining with the next-highest
  inclusion cards and flag low `sample_n`. **Fallback**: return best-effort legal list + surface `sample_n`.
- **Window with too few decks**: `sample_n` surfaced; consensus still returns (gated downstream by tuning's
  bimodal fallback).
