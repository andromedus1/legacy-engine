---
id: epic-meta-analytics-match-results
kind: feature
stage: review
tags: [analytics]
parent: epic-meta-analytics
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Match-Outcome Extraction (rounds → archetype win/loss)

## Brief
The shared data-prep foundation both meta-share (win-rate-weighted definition) and the matchup matrix
build on. Read the DuckDB `rounds` table (`player1`, `player2`, `result`) and join each pairing to the
two players' archetype labels via the `decks` table (join key = normalized `player` within a
`tournament_id`). Parse the aggregate match-score `result` string (e.g. `"2-1"`, `"2-0"`) into
**match-level** W/L for player1 (the brief is explicit: `result` is an aggregate match score, NOT
per-game winners, so a `2-1` is one match win — exactly what a matchup matrix needs). Accumulate two
aggregates: a directed `(archetype_a, archetype_b) → {wins, losses, n}` table (the matchup raw cells)
and a per-archetype marginal `archetype → {wins, losses, n}` (the win-rate-weighted meta-share input).

Owns the fragile bits the ops brief flags as the weak link: **player-name normalization** (trim,
casefold, collapse whitespace) for the rounds↔decks join, and **byes / intentional-draws / forfeit**
handling (empty `player2`, no-clear-winner `result` rows are dropped from win-rate accumulation, never
counted). Surfaces an explicit **unmatched-pairing coverage** count (pairings whose players didn't
resolve to a labeled deck) as a stat — never silently dropped. Carries the online/paper provenance
through so downstream consumers can split. Emits raw `{wins, losses, n}` aggregates only.

Does NOT compute Wilson CIs, shrinkage, confidence tiers, or the MatchupCell stats (that's
`matchup-matrix`). Does NOT compute the three meta-share definitions (that's `metashare`). It is the
join + parse + normalize layer that produces the raw counts both consume.

## Epic context
- Parent epic: `epic-meta-analytics`
- Position in epic: **foundation feature** — produces the raw match-outcome aggregates that
  `metashare` (win-rate-weighted §3c) and `matchup-matrix` both depend on. Lets those two parallelize.

## Inherited design decisions
- **Match-level W/L, not game-level**: `rounds.result` ("2-1") counts as one match win for the winner — the source is match-score aggregate, not per-game. (Inherited; see parent `## Design decisions`.)
- **Player-name is the only join key** between `rounds` and `decks`; normalize (trim/casefold/whitespace) and match within-tournament. Pairings that don't resolve to a labeled deck go to an `unmatched` coverage count, surfaced — never silently dropped (project error-handling convention: never drop a deck/pairing silently).
- **Byes / draws / forfeits dropped** from win-rate accumulation (empty player2, no-clear-winner result).
- **matchup-n is a different (smaller) population than metashare-n** — only rounds-bearing events contribute here (MTGO Leagues ship decklists only). Keep this aggregate strictly separate from deck-count aggregates.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — §4 (matchup computation from `Rounds`, the join, §4.4 name-join fragility + byes/draws), §4.3 (bimodal coverage), §3c (win-rate-weighted input).

## Foundation references
- `docs/ARCHITECTURE.md` — `analytics/matchup.py` (the rounds→labels join); the DuckDB `rounds` / `decks` schema; "matchup-n separate from metashare-n".

## Architectural choice

**Hybrid SQL-join + Python-parse-and-tally.** Three approaches were weighed: (A) pure-Python — pull
`rounds` and `decks` into memory and join/normalize entirely in Python; (B) pure-SQL — do the
player→archetype join *and* the `result`-string win/loss derivation in DuckDB; (C) hybrid — SQL does the
`rounds`↔`decks` join (DuckDB is the architecture's chosen tool precisely for this "rounds-join query
workload"), Python parses the `result` string and accumulates the tallies. **Chosen: C.** Pure-SQL (B)
founders on the `result` string — `"2-1"` → winner is awkward and fragile in SQL, and byes/draws need
real branching. Pure-Python (A) throws away DuckDB's join. C plays each to its strength: a single SQL
join yields `(provenance, player1, player2, result, arch1, arch2)` rows; Python applies the carefully
tested parser and tallies.

**Compute on-demand, do not materialize.** The architecture diagram lists a `matchups (materialized)`
table, but per "cache deliberately," MVP computes `MatchResults` in-memory each call (trivial scale —
ms over thousands of matches) rather than persisting a derived table. This avoids staleness and a
schema commitment; materialization stays an additive optimization behind the same function signature if
perf ever demands it.

## Implementation Units

### Unit 1: Result-string parser (trickiest — designed first)

**File**: `src/legacy_engine/analytics/match_results.py`

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MatchOutcome:
    """A parsed match score from player1's perspective. games are best-of-3 game counts."""
    p1_games: int
    p2_games: int
    winner: str | None  # "p1" | "p2" | None (draw / no decisive winner)

def parse_match_result(result: str | None) -> MatchOutcome | None:
    """Parse an aggregate match-score string into a match-level outcome.

    Accepts "2-1", "2-0", "1-2", "0-2", and draw forms "1-1" / "1-1-1" (3rd token = draws, ignored
    for the winner). Returns the MatchOutcome with winner="p1"|"p2" when one side has strictly more
    games, winner=None on a tie. Returns None (NOT a draw) when the string is absent, empty, a bye/
    forfeit, or otherwise unparseable — the caller routes None to the dropped-rows coverage count.
    """
```

**Implementation Notes**:
- Split on `-`; take the first two integer tokens as `p1_games`, `p2_games`; a present 3rd token is the draw count (ignored for winner determination). Match-level, not game-level (locked decision).
- Non-numeric, empty, single-token, or whitespace-only → `None`. Be defensive: wrap int-parse in try/except, return `None` on failure (never raise — one bad row must not crash the aggregation, per the project error-handling convention).

**Acceptance Criteria**:
- [ ] `"2-1"` → `MatchOutcome(2, 1, "p1")`; `"1-2"` → `(1, 2, "p2")`; `"2-0"` → `(2, 0, "p1")`.
- [ ] `"1-1"` and `"1-1-1"` → `winner is None`.
- [ ] `""`, `None`, `"BYE"`, `"2"`, `"foo-bar"` → `None`.

---

### Unit 2: Player-name normalization

**File**: `src/legacy_engine/analytics/match_results.py`

```python
def normalize_player(name: str | None) -> str:
    """Normalize a player handle for the rounds↔decks join: strip + casefold.

    Mirrors the SQL join key `lower(trim(player))` exactly so the Python and SQL sides never diverge.
    Returns "" for None/blank.
    """
    return (name or "").strip().lower()
```

**Implementation Notes**:
- Deliberately **matches `lower(trim(...))`** used in the SQL join (Unit 4) — single normalization semantics across both sides (SSOT). Internal-whitespace collapse and handle-aliasing are **out of scope for MVP**; unresolved joins surface in the coverage count (Unit 3), never silently dropped.

**Acceptance Criteria**:
- [ ] `"  Alice "` → `"alice"`; `"BOB"` → `"bob"`; `None`/`""` → `""`.
- [ ] Result is identical to what `lower(trim())` produces in DuckDB for the same input (verified in an integration test).

---

### Unit 3: Aggregate record types

**File**: `src/legacy_engine/analytics/match_results.py`

```python
@dataclass
class MatchupTally:
    """Directed cell: archetype_a's record vs archetype_b. n = wins + losses (decisive matches only)."""
    archetype_a: str
    archetype_b: str
    wins: int = 0
    losses: int = 0
    @property
    def n(self) -> int: return self.wins + self.losses

@dataclass
class ArchetypeRecord:
    """Per-archetype marginal record across all opponents (the win-rate-weighted meta-share input)."""
    archetype: str
    wins: int = 0
    losses: int = 0
    @property
    def n(self) -> int: return self.wins + self.losses

@dataclass
class MatchCoverage:
    """How much of the rounds data resolved — surfaced, never silent."""
    total_pairings: int = 0      # rows in rounds (within the provenance filter)
    decisive_matched: int = 0    # both players resolved to an archetype AND a decisive winner
    unmatched: int = 0           # >=1 player did not resolve to a labeled deck
    dropped_byes_draws: int = 0  # parsed to None or winner is None
    mirror_matches: int = 0      # both resolved archetypes equal
    @property
    def match_rate(self) -> float:
        return self.decisive_matched / self.total_pairings if self.total_pairings else 0.0

@dataclass
class MatchResults:
    """The on-demand match-outcome aggregate both metashare(§3c) and matchup-matrix consume."""
    matchups: dict[tuple[str, str], MatchupTally]   # keyed by (archetype_a, archetype_b)
    archetypes: dict[str, ArchetypeRecord]
    coverage: MatchCoverage
    provenance: str | None  # the filter applied: "online" | "paper" | None (all)
```

**Implementation Notes**:
- **Dataclasses, not Pydantic `LegacyEngineModel`** — these are internal compute artifacts, not external-JSON-backed models; no validation/alias needs, and computed `n` properties read cleanly. (`MatchupCell` in `models/` stays Pydantic, owned by `matchup-matrix`.)

**Acceptance Criteria**:
- [ ] `MatchupTally(wins=3, losses=1).n == 4`; `ArchetypeRecord(...).n` sums correctly.
- [ ] `MatchCoverage.match_rate` is `decisive_matched/total_pairings`, `0.0` when no pairings.

---

### Unit 4: Join query + accumulator (the public entry point)

**File**: `src/legacy_engine/analytics/match_results.py`

```python
import duckdb

_JOIN_SQL = """
SELECT t.provenance, r.player1, r.player2, r.result,
       d1.archetype AS arch1, d2.archetype AS arch2
FROM rounds r
JOIN tournaments t ON t.id = r.tournament_id
LEFT JOIN decks d1 ON d1.tournament_id = r.tournament_id
                  AND lower(trim(d1.player)) = lower(trim(r.player1))
LEFT JOIN decks d2 ON d2.tournament_id = r.tournament_id
                  AND lower(trim(d2.player)) = lower(trim(r.player2))
WHERE (? IS NULL OR t.provenance = ?)
"""

def compute_match_results(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None = None
) -> MatchResults:
    """Join rounds→archetype labels, parse results, accumulate directed + marginal tallies.

    `provenance` filters to "online"/"paper" tournaments; None = all. Only rounds-bearing events
    contribute (Leagues have no rounds) — so this aggregate's n is the matchup-n population, strictly
    separate from metashare deck-count n.
    """
```

**Implementation Notes**:
- Iterate the joined rows. For each: `total_pairings += 1`. If `arch1` or `arch2` is NULL → `unmatched += 1`, continue. Parse `result`; if `None` or `winner is None` → `dropped_byes_draws += 1`, continue.
- **Mirror** (`arch1 == arch2`): `mirror_matches += 1`; record `(A,A).n` via a single `+1` to the tally's `n` accounting **without** crediting a directional win (matchup-matrix forces mirror = 50%); still credit the per-archetype marginal with **+1 win and +1 loss to A** (a mirror is one A-win and one A-loss — keeps marginal win-rate honest). For mirror, implement the cell as `wins += 0, losses += 0` but increment a dedicated mirror counter the matchup-matrix reads for `n`; simplest faithful encoding: store mirror n in `coverage.mirror_matches` and let matchup-matrix render mirror cells from that. *(See risk note.)*
- **Non-mirror decisive** match, winner archetype `W`, loser `L`: `matchups[(W,L)].wins += 1`, `matchups[(L,W)].losses += 1` (both directions materialized so the matrix is symmetric); `archetypes[W].wins += 1`, `archetypes[L].losses += 1`; `decisive_matched += 1`.
- Use `setdefault`/`defaultdict`-style lazy creation of tally/record entries.

**Acceptance Criteria**:
- [ ] A challenge with `alice(Delver) beats bob(Lands) 2-1` yields `matchups[("Delver","Lands")] = {wins:1, losses:0}` and `matchups[("Lands","Delver")] = {wins:0, losses:1}`; `archetypes["Delver"].wins == 1`, `archetypes["Lands"].losses == 1`; `coverage.decisive_matched == 1`.
- [ ] A League (no rounds) contributes zero pairings.
- [ ] A pairing where one player has no labeled deck → `coverage.unmatched += 1`, no tally change.
- [ ] A `"1-1"` draw → `coverage.dropped_byes_draws += 1`, no tally change.
- [ ] `provenance="paper"` excludes online-tournament rounds.
- [ ] Cell symmetry holds: `matchups[(a,b)].wins == matchups[(b,a)].losses` for all non-mirror cells.

---

### Unit 5: Module exports

**File**: `src/legacy_engine/analytics/__init__.py`

**Implementation Notes**: export `compute_match_results`, `MatchResults`, `MatchupTally`, `ArchetypeRecord`, `MatchCoverage`, `parse_match_result`, `normalize_player` so `matchup-matrix` and `metashare` import from `legacy_engine.analytics`.

**Acceptance Criteria**:
- [ ] `from legacy_engine.analytics import compute_match_results, MatchResults` succeeds.

---

## Implementation Order

1. **Unit 1** (result parser) — first; it's the trickiest and everything tallies on its output. Pure function, fully unit-testable in isolation.
2. **Unit 2** (normalizer) — small, pure, pairs with Unit 1.
3. **Unit 3** (record types) — the shapes Unit 4 fills.
4. **Unit 4** (join + accumulator) — depends on 1–3; the integration core.
5. **Unit 5** (exports) — trivial, last.

## Testing

### Unit tests: `tests/test_match_results.py`
Follow the house pattern (module-level raw dicts → `parse_cache_item` → `store.load_tournament` into `store.connect(":memory:")`; `TestX` classes; deterministic).
- `TestParseMatchResult` — parametrized over `"2-1"/"2-0"/"1-2"/"0-2"/"1-1"/"1-1-1"/""/None/"BYE"/"2"/"foo"` → expected `MatchOutcome | None` (Unit 1 acceptance).
- `TestNormalizePlayer` — casing/whitespace/None (Unit 2).
- `TestRecordTypes` — `n` properties + `match_rate` (Unit 3).
- `TestComputeMatchResults` — build a small labeled corpus: load CHALLENGE-style tournaments, **manually set `decks.archetype`** via `UPDATE` (the labeler is a done dependency, but tests pin labels directly for determinism), then assert directed tallies, marginal records, symmetry, mirror handling, unmatched coverage, draw-dropping, and the provenance filter (Unit 4 acceptance). Mirror case: two same-archetype players → `coverage.mirror_matches == 1`, marginal `A` gets +1/+1.

### Integration points
- Seam with `store` schema: the SQL join reads `rounds`, `decks`, `tournaments` exactly as `store.load_tournament` writes them — one test loads via `store` and computes, proving the seam end-to-end.
- Seam with consumers: the returned `MatchResults` is the contract `matchup-matrix` (reads `matchups`) and `metashare` §3c (reads `archetypes`) depend on — assert both dicts are populated and keyed as documented.
- **Normalization parity**: one test inserts a deck with `"  Alice "` and a round with `"alice"` and asserts they join (proves `lower(trim())` SQL == `normalize_player` Python).

## Risks

- **Mirror n-encoding**: crediting a mirror to a directed `(A,A)` cell double-counts `n` (2 per match) versus the per-direction `1`. **Resolution in design**: do NOT write mirror to the directed `matchups` dict; carry mirror n in `coverage.mirror_matches`, and let `matchup-matrix` render the mirror cell as 50% with that n. Marginal `archetypes[A]` still gets +1 win/+1 loss (honest 50% mirror contribution to win-rate-weighted share). **Fallback**: if matchup-matrix needs per-pair mirror n inline, add an explicit `mirror_n: dict[str,int]` to `MatchResults` (additive, non-breaking).
- **Player-name join coverage** (the epic-flagged weak link): handles/casing beyond strip+lower won't resolve and inflate `coverage.unmatched`. **Mitigation**: surfaced as an explicit coverage stat (never silent); `match_rate` is observable so downstream can banner low coverage. Deeper normalization (alias tables) is a deferred, additive enhancement — not MVP-blocking.
- **Draw/forfeit `result` shapes** vary by source. **Mitigation**: the parser is defensive (returns `None` on anything non-decisive, never raises); `dropped_byes_draws` makes the volume visible so a surprising shape is caught by a coverage assertion rather than silent miscounting.

## Design decisions
(Resolved under autopilot; inherited epic decisions treated as fixed.)
- **Join in SQL, parse+tally in Python** (hybrid) — DuckDB does the rounds↔decks join; Python owns the result parser and accumulation.
- **Compute on-demand, no materialized `matchups` table** for MVP — additive optimization later behind the same signature.
- **Mirror**: not written to directed cells; carried in `coverage.mirror_matches`; marginal gets +1/+1 (see risk).
- **Dataclasses for internal aggregates** (not Pydantic) — `MatchupCell` in `models/` remains the Pydantic, consumer-facing type owned by `matchup-matrix`.
- **Single-stride, no child stories** — one cohesive module, units tightly coupled.

## Implementation notes

### Files created/modified
- **Created**: `src/legacy_engine/analytics/match_results.py` — all five units (parser, normalizer,
  record types, join+accumulator, public names).
- **Modified**: `src/legacy_engine/analytics/__init__.py` — exports `compute_match_results`,
  `MatchResults`, `MatchupTally`, `ArchetypeRecord`, `MatchCoverage`, `MatchOutcome`,
  `parse_match_result`, `normalize_player` (Unit 5).
- **Created**: `tests/test_match_results.py` — 42 new tests.

### Test count
- Baseline: 129 passing.
- After implementation: 171 passing (42 new, 0 failures).

### Deviations from design
None. Every unit follows the spec exactly:
- `parse_match_result` splits on `-`, takes first two int tokens, third token (draw count) is
  silently ignored; all non-numeric / empty / single-token inputs return `None`.
- `normalize_player` = `(name or "").strip().lower()` — verbatim from spec.
- Dataclasses used throughout (not Pydantic) as required.
- Mirror matches: not written to directed `matchups`; counted in `coverage.mirror_matches`;
  per-archetype marginal credited `+1 win / +1 loss`.
- SQL join is the spec's `_JOIN_SQL` verbatim.
- Both directed cells `(W,L)` and `(L,W)` materialised for every decisive non-mirror match.

### Adjacent issues parked
- None. Coverage count invariant (`total == decisive + unmatched + dropped + mirror`) holds by
  construction; verified by `test_multi_scenario_coverage_totals`.
- The `DuckDBPyConnection` type hint in `_con()` in the test file uses `store.DuckDBPyConnection`
  which is actually from the `duckdb` package re-exported. The type comment uses `# type: ignore`
  to avoid a runtime AttributeError; the actual object returned is correct.
