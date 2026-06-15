---
id: epic-deck-generation-per-card-value
kind: feature
stage: done
tags: [generation, analytics]
parent: epic-deck-generation
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-31
updated: 2026-06-14
---

# Per-card win-rate (overall + per-card×matchup)

## Brief

The deferred per-card win-rate data extension — the real fix that unblocks credible field-tuning and the
maindeck-aware sideboard. Extend `analytics/match_results.py` to compute, per card, how a deck's win-rate
relates to running that card: an **overall inclusion-lift** (P(win | deck runs card X) vs the archetype's
baseline win-rate) AND a **per-card×matchup** slice (P(win | deck runs X, vs opposing archetype M)).

**Feasibility (confirmed):** `deck_cards(tournament_id, deck_idx, board, name, count)` stores the full 75
of every deck; `rounds(tournament_id, match_idx, player1, player2, result)` gives match-level player-vs-player
outcomes; `decks(tournament_id, deck_idx, player, result, archetype)` maps player → archetype. Join
round → both players' decks → archetypes → card lists to aggregate per-card outcomes, sliced by opponent
archetype.

**Honesty bound (load-bearing — do not overclaim):** this is **presence-correlational, NOT causal.** We see
the *registered 75*, not what was actually drawn or sided in game-to-game, so "decks running X win more vs M"
is confounded by deck/pilot selection. Per-card×matchup cells get sparse fast. Therefore:
- **prior + signal** model: the overall inclusion-lift is the **Bayesian prior**; the per-card×matchup rate is
  the **signal**, used only where its `n` clears the sample gate, **shrunk toward the prior** (empirical-Bayes /
  beta-binomial shrinkage) for thin cells.
- gate every emitted number by the existing `ConfidenceMetadata` / `tier_for_sample(n)` tiers
  (speculative <30 / evolving 30-99 / established ≥100); **suppress** cells below the display gate rather than
  fabricate — consistent with the project "never fabricate meta numbers" rule.
- callers (sideboard, tuning) receive a value PLUS its confidence tier and can degrade to the coverage
  heuristic when the per-card signal is absent.

## Epic context
- Parent epic: `epic-deck-generation`. This is the new prerequisite that the parent's `## Decomposition`
  flagged as "needs a per-card win-rate match-results extension" — now un-deferred per Andrew's 2026-05-31
  decision.
- Consumers: `epic-deck-generation-sideboard-maindeck` (depends_on this) and the reworked
  `epic-deck-generation-tuning`.

## Foundation references
- `src/legacy_engine/analytics/match_results.py` — extend here (reuse `parse_match_result`,
  `normalize_player`, the round/deck/archetype joins already proven by `compute_match_results`).
- `src/legacy_engine/analytics/matchup.py` — matchup-matrix join patterns + cardinality-safe rounds CTEs
  (dup/uniq_decks) to mirror; do not re-introduce the fan-out bugs fixed in `fix-analytics-peer-review-findings`.
- `.claude/rules/patterns.md` → confidence-metadata pattern (`ConfidenceMetadata`, `tier_for_sample`).

## Design decisions (locked 2026-05-31 — do not re-decide)
- **Card value = prior + signal**, confidence-tiered, presence-correlational (above).
- **Granularity:** both overall inclusion-lift (denser prior) and per-card×matchup (the sideboard-relevant
  signal). Board-aware (main vs side) so the sideboard rework can ask "value of X *in the maindeck* vs M".
- **Shrinkage** toward the archetype/overall prior for thin matchup cells; the exact estimator (beta-binomial
  empirical-Bayes vs simpler additive smoothing) is a `/feature-design` unit-level choice — pick the simplest
  that's honest and document it.
- **Output is a typed record** (dataclass in `analytics/`, same convention as the other analytics records),
  carrying value + n + ConfidenceMetadata tier, queryable by (card[, opposing_archetype][, board]).

## Acceptance (sketch — feature-design fleshes into units + tests)
- Per-card overall inclusion-lift computed from real round/deck joins, archetype-baselined.
- Per-card×matchup win-rate computed, shrunk toward the prior, gated by `tier_for_sample`.
- Thin cells (n < gate) suppressed/flagged, never fabricated.
- Cardinality-safe joins (no standings/round fan-out double-count — regression-test against the
  fix-analytics-peer-review-findings cases).
- Deterministic, seeded tests with a **rounds-bearing fixture** (the gap that made tuning's greedy path
  untestable — this fixture is the shared asset that unblocks tuning #2).

## Architectural choice

**Phase 5a — options considered:**
1. **Pure-SQL aggregation** — extend `_JOIN_SQL` with a `deck_cards` join for both players + parse the result
   string in SQL (`TRY_CAST(split_part(...))`), `GROUP BY (card, board, opponent)`. Fast (columnar), but
   **forks the result parser** — a second SQL parser would diverge from `parse_match_result` (SSOT violation,
   the exact class of bug the analytics peer-review caught).
2. **Python accumulator reusing `parse_match_result` (CHOSEN)** — two queries: (a) the existing cardinality-safe
   `dup`/`uniq_decks` join to get resolved decisive non-mirror matches (winner/loser player+archetype), reusing
   `parse_match_result` for winner determination; (b) a `deck_cards`→`decks` map of `(tournament_id, norm) →
   [(board, name)]` restricted to players appearing in resolved matches. Then attribute, per resolved match, a
   win to each card in the winner's deck vs the loser's archetype and a loss to each card in the loser's deck
   vs the winner's archetype.
3. **Refactor `compute_match_results` to expose per-match rows** — cleanest data flow but reopens a `done`,
   widely-depended-on function; unjustified blast radius.

**Chosen: option 2.** Zero parser divergence (reuses `parse_match_result` + the proven dup/uniq guards),
consistent with this module's existing all-Python-loop profile, no churn to `compute_match_results`. Heavy
lifting that stays in SQL is just the two joins; per-card attribution is a Python loop (~matches × cards/deck).

**Module placement** respects the existing seam: `match_results.py` stays raw-aggregates-only;
stats primitives live in `matchup.py`; a **new `analytics/card_value.py`** owns the confidence-rated value
builders (imports `tier_for_sample` + the generalized shrink from `matchup.py`). This avoids a circular
import (`matchup` already imports `match_results`; `card_value` imports both).

## Implementation Units

### Unit 1: Raw per-card aggregate — `match_results.py`
**File**: `src/legacy_engine/analytics/match_results.py`
```python
@dataclass
class CardMatchupRecord:           # (card, board, opponent) directed cell
    card: str; board: str; opponent: str
    wins: int = 0; losses: int = 0
    @property
    def n(self) -> int: return self.wins + self.losses

@dataclass
class CardMarginalRecord:          # (card, board) across all opponents — the prior
    card: str; board: str
    wins: int = 0; losses: int = 0
    @property
    def n(self) -> int: return self.wins + self.losses

@dataclass
class CardWinRates:
    matchup: dict[tuple[str, str, str], CardMatchupRecord]   # (card, board, opponent)
    marginal: dict[tuple[str, str], CardMarginalRecord]      # (card, board)
    baseline_winrate: float          # global decisive win-rate (grand prior; ~0.5 by symmetry)
    coverage: MatchCoverage          # SAME resolution counters as compute_match_results
    provenance: str | None

def compute_card_winrates(
    con, *, provenance: str | None = None, since: str | None = None, until: str | None = None,
) -> CardWinRates:
    # 1. Resolved matches via the EXISTING dup/uniq_decks CTEs + parse_match_result (reuse, do not refork).
    #    Apply byes/ambiguous/unmatched/draw/mirror guards identically; window by t.date (since/until, ISO).
    #    Yields rows: (tournament_id, winner_norm, loser_norm, winner_arch, loser_arch).
    # 2. deck_cards map: SELECT dc.board, dc.name, lower(trim(d.player)) AS norm, dc.tournament_id
    #      FROM deck_cards dc JOIN decks d USING (tournament_id, deck_idx)
    #    restricted to (tournament_id, norm) pairs present in resolved matches. board normalized main|side.
    # 3. Attribute: winner's cards += win vs loser_arch; loser's cards += loss vs winner_arch; and the
    #    board-aware marginal. baseline_winrate = decisive_matched wins / total decisive (== 0.5 by construction
    #    since every match credits one win+one loss globally — store it explicitly for the shrink prior anyway).
```
**Implementation Notes**: reuse `_JOIN_SQL`'s `dup`/`uniq_decks` CTEs verbatim (extract a shared CTE constant
so both functions reference one source). Restrict the deck_cards map to resolved players to bound memory.
Normalize `board` to `"main"`/`"side"` (cache stores `Mainboard`/`Sideboard`). **Invariant to assert in
tests:** Σ over a card's matchup cells of `n` ≤ (number of resolved matches its decks played) — no fan-out
double-count.
**Acceptance Criteria**:
- [ ] Each resolved decisive non-mirror match attributes exactly one win-set (winner's cards) and one loss-set
  (loser's cards), board-aware, keyed by the *opponent's* archetype.
- [ ] Byes/draws/mirrors/ambiguous/unmatched are excluded identically to `compute_match_results`
  (`coverage` counters match for the same corpus + window).
- [ ] `since`/`until` window by `tournaments.date`.
- [ ] No cardinality fan-out: a deck running card X once in a match contributes exactly 1 to that cell's n.

### Unit 2: Generalized shrink primitive — `matchup.py`
**File**: `src/legacy_engine/analytics/matchup.py`
```python
def beta_binomial_shrink_to(wins: int, n: int, *, prior_mean: float, strength: float = SHRINK_STRENGTH) -> float:
    """Posterior-mean shrinkage toward an ARBITRARY prior_mean: (a+wins)/(a+b+n), a=prior_mean*strength."""
    a = prior_mean * strength; b = (1.0 - prior_mean) * strength
    return (a + wins) / (a + b + n) if (a + b + n) else prior_mean
# refactor existing beta_binomial_shrink to delegate: beta_binomial_shrink_to(wins, n, prior_mean=0.5, strength=2*SHRINK_ALPHA)
```
**Implementation Notes**: `SHRINK_STRENGTH` = the existing `2*SHRINK_ALPHA` (=15) so default behavior is
byte-identical. Existing `beta_binomial_shrink` keeps its signature + results (regression-covered).
**Acceptance Criteria**:
- [ ] `beta_binomial_shrink_to(w, n, prior_mean=0.5)` ≡ old `beta_binomial_shrink(w, n)` for all inputs.
- [ ] `n=0` → returns `prior_mean`.

### Unit 3: Confidence-rated card-value builder — `card_value.py` (NEW)
**File**: `src/legacy_engine/analytics/card_value.py`
```python
@dataclass(frozen=True)
class CardValue:
    card: str; board: str; opponent: str | None     # None = overall marginal
    p_raw: float | None        # wins/n, None when n==0
    p_shrunk: float            # two-level empirical-Bayes posterior mean
    prior_mean: float          # what we shrank toward (baseline for marginal; marginal-p for matchup)
    lift: float                # p_shrunk - prior_mean (matchup-specific edge; or above-baseline for marginal)
    n: int
    tier: ConfidenceLevel      # tier_for_sample(n) — speculative/evolving/established

def card_value_marginal(r: CardWinRates, card: str, board: str) -> CardValue:
    # prior_mean = r.baseline_winrate; shrink the marginal cell toward it; lift = p_shrunk - baseline.
def card_value_matchup(r: CardWinRates, card: str, board: str, opponent: str) -> CardValue:
    # prior_mean = card_value_marginal(...).p_shrunk; shrink the (card,board,opponent) cell toward it;
    # lift = p_shrunk - prior_mean (how much better/worse this card does vs THIS opponent than overall).
def card_values_vs(r, cards: list[str], board: str, opponent: str, *, gate=("evolving","established")) -> dict[str, CardValue]:
    # convenience for consumers (sideboard/tuning): value each card vs opponent; callers gate on .tier.
```
**Implementation Notes**: two-level shrinkage — matchup cell shrinks toward the card's shrunk marginal, which
shrinks toward the global baseline. `card_values_vs` does NOT itself suppress; it returns values + tiers so
the consumer decides whether to trust (and degrade to its coverage heuristic when all are below `gate`).
**Acceptance Criteria**:
- [ ] A card with strong vs-M record (high n) yields `lift > 0`, `tier="established"`.
- [ ] A thin vs-M cell (n<30) yields `tier="speculative"` and `p_shrunk` close to the marginal prior (shrinkage
  dominates).
- [ ] `card_value_matchup` for an unseen (card, opponent) → `n=0`, `p_raw=None`, `p_shrunk==prior_mean`, speculative.

### Unit 4: Rounds-bearing fixture — `conftest.py` (the shared asset)
**File**: `tests/conftest.py`
```python
@pytest.fixture
def make_rounds_corpus():
    """Factory: build an in-memory DuckDB con with a deterministic rounds+deck_cards+labels corpus.
    Knobs: n_repeats (scale match counts above/below tier gates), archetypes, a 'tech' card with a
    KNOWN elevated win-rate vs a KNOWN opponent archetype. Returns (con, facts) where facts pins the
    expected wins/n for the seeded signal so tests assert exact values."""
```
**Implementation Notes**: build via the existing idiom (raw cache-dicts → `parse_cache_item` →
`store.load_tournament`, labels pinned by SQL UPDATE). Seed ≥2 archetypes, decks with distinct mainboards +
sideboards, rounds with fixed results so e.g. "DeckA running Surgical beats Combo k of m times". `n_repeats`
duplicates tournaments to push the seeded cell across the 30/100 tier boundaries. **This fixture is reused by
the tuning rework to exercise its greedy path (tuning bug #2).**
**Acceptance Criteria**:
- [ ] `make_rounds_corpus()` yields a con where `compute_card_winrates` returns the pinned wins/n for the
  seeded tech-card-vs-opponent cell.
- [ ] `n_repeats` knob moves the seeded cell's tier across speculative→evolving→established.

### Unit 5 (optional, thin): `report cards` CLI leaf — `cli.py`
**File**: `src/legacy_engine/cli.py`
```python
@report.command("cards")
@click.option("--archetype", default=None)   # restrict to cards an archetype plays (via card_frequencies)
@click.option("--vs", "opponent", default=None)  # show per-matchup value vs this opponent; else marginal
@click.option("--board", default="main"); --since --until --db --min-tier --verbose
# prints a confidence-gated table: card | board | n | p_shrunk | lift | tier; hides below --min-tier.
```
**Implementation Notes**: pure read; reuse `generation.consensus.card_frequencies` to scope `--archetype`.
Gives Andrew a way to eyeball the (correlational) numbers on real data — auditability for "never fabricate".
**Acceptance Criteria**:
- [ ] `report cards --archetype X --vs Y` prints values vs Y for X's cards; `--min-tier established` hides
  speculative rows; thin data prints a "below gate — suppressed" note rather than fabricating.

## Implementation Order
1. **Unit 1** (`compute_card_winrates`) — trickiest; the cardinality-safe attribution is the load-bearing
   risk. Build + prove the no-fan-out invariant first.
2. **Unit 4** (fixture) — needed to test Unit 1 on known signal; co-developed with it.
3. **Unit 2** (generalized shrink) — tiny, regression-guarded.
4. **Unit 3** (`card_value.py`) — builds on 1+2.
5. **Unit 5** (CLI) — last, thin surface.

## Testing

### Unit tests
- `tests/test_card_winrates.py` — `compute_card_winrates` on `make_rounds_corpus`: pinned wins/n per cell;
  the no-fan-out invariant (Σ cell n vs resolved matches); byes/draws/mirror/ambiguous exclusion parity with
  `compute_match_results`; `since`/`until` windowing; board-awareness (main vs side counted separately).
- `tests/test_matchup.py` (extend) — `beta_binomial_shrink_to` ≡ old shrink at prior_mean=0.5; `n=0` path.
- `tests/test_card_value.py` — marginal + matchup `CardValue`: lift sign, tier transitions across the gate
  (driven by `n_repeats`), unseen-cell prior fallback, two-level shrinkage direction.
- `tests/test_cli.py` (extend) — `report cards` happy path + `--min-tier` suppression note.

### Integration points
- Seam to consumers: `card_values_vs` is the contract `epic-deck-generation-sideboard-maindeck` and the tuning
  rework consume. Test that its return shape (dict[card → CardValue] with tiers) supports gate-then-degrade.

## Risks
- **Presence-correlational, not causal** (design honesty bound): a card's vs-M win-rate is confounded by deck/
  pilot selection — we see the registered 75, not game-by-game play. **Mitigation**: shrinkage toward prior +
  confidence tiers + consumers degrade to the coverage heuristic; never claimed as causal. Documented in the
  module docstring + surfaced in the CLI.
- **Perf on full corpus** (~matches × cards/deck Python iterations, ~5–6M on 77k rounds). **Mitigation**:
  restrict the deck_cards map to resolved players; acceptable for an on-demand analytics call. **Fallback**:
  push attribution into SQL `GROUP BY` with a `TRY_CAST` parser cross-checked against `parse_match_result`
  (golden table test pins the two parsers together) if it proves too slow.
- **Sparsity of matchup cells**: most (card, opponent) cells will be speculative. **Mitigation**: the prior+
  signal design expects this — the marginal prior carries cells with thin matchup data; gate filters the rest.

## Implementation discovery

**All 5 units delivered as designed. No design flaws encountered.**

### Units delivered

1. **Unit 1 — `compute_card_winrates` + record types** (`match_results.py`): `CardMatchupRecord`, `CardMarginalRecord`, `CardWinRates` dataclasses added; `_DUP_UNIQ_CTE` extracted as a module constant so `_JOIN_SQL` and `_CARD_WINRATES_SQL` both reference one source. `compute_card_winrates` added with the two-query Python-accumulator pattern (option 2 from Architectural choice). Board normalized to `"main"`/`"side"` via `_BOARD_NORM` dict.

2. **Unit 2 — `beta_binomial_shrink_to`** (`matchup.py`): `SHRINK_STRENGTH = 2 * SHRINK_ALPHA` constant added; `beta_binomial_shrink_to(wins, n, *, prior_mean, strength=SHRINK_STRENGTH)` added; `beta_binomial_shrink` refactored to delegate with `prior_mean=0.5` — outputs byte-identical.

3. **Unit 3 — `card_value.py`** (NEW): `CardValue` frozen dataclass + `card_value_marginal`, `card_value_matchup`, `card_values_vs`. Two-level empirical-Bayes shrinkage implemented as designed.

4. **Unit 4 — `make_rounds_corpus` fixture** (`conftest.py`): factory fixture returning `(con, facts)` with `n_repeats` knob; seeded Control vs Combo corpus with Surgical Extraction (side) as the tech card; `facts` dict pins expected wins/n at exact values.

5. **Unit 5 — `report cards` CLI leaf** (`cli.py`): `--archetype`, `--vs`, `--board`, `--min-tier`, `--since`, `--until`, `--db`, `--verbose`; suppression note shown (never fabricates); presence-correlational disclaimer in header.

### Exports registered

All new symbols exported via `src/legacy_engine/analytics/__init__.py`: `CardMatchupRecord`, `CardMarginalRecord`, `CardWinRates`, `compute_card_winrates`, `beta_binomial_shrink_to`, `CardValue`, `card_value_marginal`, `card_value_matchup`, `card_values_vs`.

### Deviations from design

- **`baseline_winrate` computation**: the design says "≈0.5 by construction" — implementation computes it as `decisive_matched_wins / (decisive_matched * 2)` which is exactly 0.5 when all matches are decisive (one win + one loss attributed per match). Stored explicitly as specified.
- **Empty corpus guard**: `compute_card_winrates` returns early with `baseline_winrate=0.5` and empty dicts when no resolved matches exist — clean sentinel values, no divide-by-zero.
- **`_con()` in test_card_winrates.py**: the "empty corpus" test explicitly calls `store.init_schema()` first (the project idiom is to always load at least one tournament via `store.load_tournament` which calls `init_schema`; using a bare connection without schema causes a DuckDB catalog error, as confirmed by testing).

### Test counts

- Baseline: **846 passing**
- After implementation: **913 passing** (+67 new)
- New test files: `tests/test_card_winrates.py` (26 tests), `tests/test_card_value.py` (24 tests)
- Extended: `tests/test_matchup.py` (+9 shrink delegation tests), `tests/test_cli.py` (+8 report cards tests)
- Regressions: **0**


## Review findings (deep review, 2026-05-31) — APPROVED

Fresh-context deep review (same-model Claude, Opus; **cross-model deferred — Codex out of credits**, a true
cross-model pass is owed before epic closure). Verdict: **Approve with comments — no blockers.** All six
correctness-critical invariants verified by direct code tracing (not just the green suite):
1. No cardinality fan-out — `compute_card_winrates` attributes 1 per (deck,match), never per `count`; the
   `_DUP_UNIQ_CTE` constant is genuinely shared (SSOT), `parse_match_result` reused (no forked SQL parser).
2. Coverage parity with `compute_match_results` (identical bye→ambiguous→unmatched→draw→mirror guard order).
3. `beta_binomial_shrink` byte-identical after delegating to `beta_binomial_shrink_to`.
4. Two-level empirical-Bayes sound; lift/tier/unseen-cell handling correct.
5. Honesty bound upheld — values carry tiers, thin cells suppressed not fabricated.
6. `since`/`until` window correct. Tests genuinely assert the invariants on the rounds-bearing fixture
   (non-vacuous, n_repeats drives tier transitions).

**Findings — all resolved in-session (no items filed):**
- **[Important] CLI window mismatch** (`cli.py report cards`): `--archetype` scoped the card *list* to the
  latest ban regime (via `card_frequencies` default) while values used the all-time corpus. FIXED — the
  effective window is resolved once and passed to both `compute_card_winrates` and `card_frequencies`;
  defaults to the latest regime (consistent with `report meta`); the active window is now printed in the
  header. 5 CLI tests made window-explicit (`--since 2025-01-01`) so they're deterministic regardless of
  real ban dates.
- **[Nit] dead `total_decisive`/`total_wins` + misleading baseline comment** (`match_results.py`): FIXED —
  removed; `baseline_winrate` set directly to the match-level symmetric prior 0.5 with an honest comment.
- **[Nit] EB prior contains the cell's own signal** (`card_value.py`): FIXED — added a clarifying comment;
  accepted EB simplification matching the locked design.
- **[Nit] unused `gate` param** (`card_value.py card_values_vs`): KEPT — documented as the recommended
  consumer trust-threshold; covered by a non-suppression test; in the locked design contract.

Suite green at 913. Advanced review → done.
