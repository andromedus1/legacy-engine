---
id: feature-strong-player-signal
kind: feature
stage: review
tags: [analytics, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

Use **strong players as the best/strongest signal for archetype tuning.** A consensus over the whole
field averages in weak and netdecked lists; the sharpest read on how to build/tune a specific
archetype right now comes from the small set of players who pilot it at a high level. We want a way
to weight (or filter) tuning + consensus toward those players' lists.

To do that the engine needs to **identify, validate, and track players across the corpus:**
- **Identify** — resolve player identity across sources and handle variants (this session found the
  same person as `Bosh N Roll`, `BoshNRoll_Brian`, `Bosh95`; `Andrea Mengucci` as itself). Player
  strings are currently free-text on `decks.player` with no canonical identity.
- **Validate** — define "strong" defensibly: sustained results (top finishes / win-rates across
  events), not a single 5-0. Needs a per-player track record built from standings + results.
- **Track** — follow a player's archetype choices and list evolution over time and across regimes,
  so their tuning signal can feed `generate consensus` / `generate tune` (e.g. a `--players` or
  expertise-weighted field).

Open question to resolve at scope time: weight by player strength vs. hard-filter to a curated
expert set, and how this interacts with ban-regime windowing (a strong player's list from the prior
regime is still stale — see [[idea-ban-regime-everywhere]]).

---

## Design

### Summary

A new `analytics/players/` module that turns the free-text `decks.player` column into a queryable
**player identity → track record → archetype-history** layer, plus a thin **player-filtered
consensus** integration into `generation/`. The whole feature is **gated-additive** (the project's
canonical pattern): with no `--players` / `--strong` flag, every existing `generate` /
`metashare` / `match_results` path is byte-identical to today. New behaviour only activates when a
caller supplies a player filter or asks for the strong-player field.

Decomposed into **three child stories** that build in dependency order:

1. `feature-strong-player-signal-identity` — alias resolution (free-text → canonical player_id).
2. `feature-strong-player-signal-strength` — track-record scoring + the "strong" definition. Depends on (1).
3. `feature-strong-player-signal-consensus` — `--players` / `--strong` filter into `generate consensus`/`tune`, regime-safe. Depends on (1) and (2).

The three are separable: identity is reusable on its own (any per-player analytics needs it),
strength is a pure scoring function over standings, and the consensus integration is a filter layer.
Each ships with tests and is independently mergeable.

---

### Decision 1 — Player identity: **explicit curated alias table**, NOT pure heuristic

**Resolved: an explicit, version-controlled alias map seeded by an opt-in heuristic suggester — not
automatic fuzzy merging.**

The corpus has 12,306 distinct free-text handles over 64k decks across online (MTGO) and paper
(Melee/Topdeck) sources. Three failure modes make *automatic* fuzzy merging unsafe:

- **False merges are silent and poison the signal.** `Bosh N Roll` / `BoshNRoll_Brian` / `Bosh95`
  are one person, but `andrea` and `andrea_m` may be two. An auto-merge that fuses distinct strong
  players corrupts exactly the high-leverage cells this feature exists to sharpen. A wrong merge is
  worse than no merge.
- **Cross-source identity is genuinely ambiguous.** An MTGO handle (`Bosh95`) and a paper real-name
  (`Brian …`) have no string overlap; only human knowledge links them. No heuristic recovers that.
- **The strong set is small.** We only need identity resolution for the handful of players who clear
  the strength bar (Decision 2). Curating ~tens of aliases by hand is cheap; auto-merging 12k handles
  is a large surface for silent error.

**Approach — two layers:**

- **`data/players/aliases.json`** — a hand-curated, git-tracked alias map: `{canonical_id: {display, handles: [...], notes}}`. This is the **source of truth**, mirroring the project's "raw curated JSON is the source of truth; DuckDB is the derived cache" storage decision (banlist precedent). Every handle not in the map resolves to **itself** (identity) — no handle is ever silently dropped or merged.
- **`identify suggest`** — an *opt-in* heuristic suggester that proposes candidate merges for human review (normalized-prefix overlap + co-occurrence: handles that share a normalized stem AND never appear in the same event on the same day). It **emits suggestions to stdout for the curator to paste into `aliases.json`**; it never writes merges itself. This keeps the cheap heuristic value (surfacing the `Bosh*` cluster) without the silent-merge risk.

Resolution itself is a pure function `resolve_player(handle, alias_map) -> player_id` reusing the
existing `normalize_player` (`lower(trim(...))`) collation from `match_results` (SSOT — no
join-key divergence). The alias map is loaded once and materialized into a derived
`player_aliases(handle_norm, player_id)` DuckDB table so SQL joins can resolve identity, exactly
mirroring how `cards` is a derived table over raw JSON.

**Rejected:** pure-heuristic auto-merge (silent false-merge risk on the exact cells we care about);
fuzzy string distance at query time (non-deterministic, slow, and still wrong cross-source).

---

### Decision 2 — "Strong" definition: **sustained, tier-gated, never a single 5-0**

**Resolved: a per-player track record over `standings`, scored as a shrunk match-win-rate combined
with a sustained-volume floor, surfaced with the project's confidence tiers.**

The `standings` table carries exactly what we need per (player, event): `rank`, `wins`, `losses`,
`draws`, `points` (48,796 rows confirmed in the live corpus). A player's track record aggregates
these across all their events (after identity resolution):

```
PlayerRecord:
  player_id: str
  display: str
  events: int                  # distinct tournaments with a standings row
  match_wins / match_losses / match_draws: int   # summed across events
  top8_finishes / top_finishes(rank<=cut): int
  win_rate_shrunk: float       # beta_binomial_shrink_to(wins, wins+losses, prior=0.5)
  tier: ConfidenceLevel        # tier_for_sample(match_wins + match_losses)
```

**`strength_score`** = the shrunk match-win-rate, with a **hard sustained-volume gate**: a player is
eligible for "strong" only at **`evolving` tier or better** (≥30 decisive matches across events) AND
**≥`min_events` distinct events** (default 3). This directly answers the spec's "not a single 5-0":
one 5-0 is `events=1`, fails the event floor, and at n≈7 matches sits in `speculative` — gated out.
Shrinkage toward 0.5 means a 6-0 across two events still regresses to a believable number rather than
showing a spurious 1.0. We reuse `beta_binomial_shrink_to` and `tier_for_sample` verbatim (the
confidence-metadata + two-level-empirical-bayes patterns), so "strong" inherits the same honesty
discipline as every other emitted stat — no new ad-hoc threshold philosophy.

`is_strong(record, *, min_events=3, min_tier="evolving", min_win_rate=0.55)` is a pure predicate;
all three knobs are explicit and defaulted, surfaced as CLI flags. The strong **set** for a window
is `{p for p in records if is_strong(p)}`, computed over the same date window the consumer uses
(so "strong in the current regime" is expressible).

---

### Decision 3 — Tracking + integration: **player-filtered consensus, regime-windowed**, weight deferred

**Resolved: hard-filter via `--players` / `--strong` on the consensus corpus, NOT a continuous
expertise-weighted field, for v1.** Weighting is a clean follow-up once the filter proves out.

Rationale: the existing `card_frequencies` / `build_consensus` already takes a date window and a
provenance filter and aggregates over a *deck pool*. Restricting that pool to a set of players is the
**minimal, auditable** change — it slots into the existing `deck_pool` CTE as one extra
`WHERE player_norm IN (strong_set)` predicate. A continuous expertise weight would require reworking
the modal-count aggregation into a weighted mode (and choosing a weighting function), which is more
surface for less clarity. The hard filter also gives the cleaner dogfooding story ("show me the
consensus Dimir Tempo list among players who've proven they can pilot it").

**Tracking / list-evolution** is delivered as `player_archetype_history(player_id, window) ->
[(regime, archetype, deck_count)]`: per-regime archetype choices for a player, so the user can see a
player switch archetypes across ban regimes. This is the "follow a player's choices over time"
deliverable and is the read-side surface (`identify track <player>`).

**Regime-safety (the load-bearing interaction):** a strong player's *prior-regime* list is still
stale. The integration **does not bypass windowing** — the player filter is applied **on top of** the
existing window, and the default window stays the latest ban-regime (`_latest_regime_window`, the
consensus SSOT). So `generate consensus --strong` = "modal list among strong pilots **in the current
regime**". When the player-filtered + windowed pool is thin (the common case — few strong players ×
one regime), we **degrade honestly**: if the strong+windowed pool yields `sample_n` below an
`evolving` floor, emit a loud banner and the `GeneratedDeck.sample_n` already carries the
`speculative` tier the CLI prints. We do **not** silently widen the window to backfill — that would
reintroduce stale prior-regime lists, the exact failure the spec calls out. `--all-time` remains the
explicit escape hatch.

---

### Interfaces / signatures

**New module `analytics/players/` (3 files):**

```python
# analytics/players/identity.py   (story 1)
def load_alias_map(path: Path = ALIASES_PATH) -> dict[str, str]:
    """handle_norm -> player_id; handles absent from the curated map resolve to themselves."""

def resolve_player(handle: str | None, alias_map: dict[str, str]) -> str:
    """Pure: normalize_player(handle) then alias_map.get(norm, norm). SSOT collation."""

def materialize_player_aliases(con, alias_map) -> int:
    """Build the derived player_aliases(handle_norm VARCHAR, player_id VARCHAR) table. Idempotent."""

def suggest_aliases(con, *, min_overlap: int = 4) -> list[AliasSuggestion]:
    """Opt-in heuristic: normalized-stem clusters that never co-occur same-event-same-day.
       Returns suggestions for human review; writes nothing."""

# analytics/players/strength.py   (story 2)
@dataclass
class PlayerRecord: ...   # as above
def compute_player_records(con, *, alias_map, since=None, until=None,
                           provenance=None, cut_size=8) -> dict[str, PlayerRecord]:
    """Aggregate standings across events, identity-resolved, windowed. Reuses
       beta_binomial_shrink_to + tier_for_sample."""
def is_strong(rec: PlayerRecord, *, min_events=3, min_tier="evolving",
             min_win_rate=0.55) -> bool: ...
def strong_player_set(records, **gate) -> set[str]:   # set of player_ids

# analytics/players/history.py   (story 2, read surface)
def player_archetype_history(con, player_id, *, alias_map) -> list[ArchetypeRegimeRow]:
    """Per-regime (regime_label, archetype, deck_count) for one player. Uses trends.regime_windows."""
```

**Integration (story 3):**

```python
# consensus.py — additive optional param; None = byte-identical to today
def card_frequencies(con, archetype, *, board, since=None, until=None,
                     provenance=None, players: set[str] | None = None,
                     alias_map: dict | None = None) -> list[CardFreq]: ...
def build_consensus(con, archetype, *, ..., players: set[str] | None = None,
                    alias_map: dict | None = None) -> GeneratedDeck: ...
# tuning.py — same additive players/alias_map passthrough into consensus seed.
```

`players` resolves through `player_aliases` in the `deck_pool` CTE
(`AND lower(trim(d.player)) IN (SELECT handle_norm FROM player_aliases WHERE player_id = ANY(?))`,
or directly against the resolved handle set passed from Python). `None` → no predicate → existing SQL.

---

### CLI shape

```
identify suggest [--db] [--min-overlap N]          # story 1 — heuristic merge suggestions for curation
identify track <player> [--db]                      # story 2 — per-regime archetype history
identify strong --archetype <a> [--since/--until/--regime/--all-time]
                [--min-events 3] [--min-tier evolving] [--min-win-rate 0.55] [--db]   # story 2 — list strong pilots

generate consensus --archetype <a> [--players "h1,h2" | --strong]
                   [--min-events/--min-tier/--min-win-rate] [existing window flags]   # story 3
generate tune      --archetype <a> [--players | --strong] [...]                        # story 3
```

`identify` is a new nested group (CLI-nested-groups pattern; `_setup_logging(verbose)` first; lazy
imports inside leaves). `--strong` is sugar for "compute the strong set for this archetype+window and
use it as `--players`". `--players` + `--strong` together → `--players` wins (explicit beats derived),
log a note.

---

### Units in build order

**Story 1 — identity** (`analytics/players/identity.py`, `data/players/aliases.json`, `cli identify suggest`):
- U1 `resolve_player` + `load_alias_map` (pure; the seed `aliases.json` ships the `Bosh*` cluster as the worked example + a schema comment).
- U2 `materialize_player_aliases` derived table + `rebuild` hook in `store.init_schema` path.
- U3 `suggest_aliases` heuristic + `identify suggest` CLI leaf.

**Story 2 — strength** (`analytics/players/strength.py`, `history.py`, `cli identify strong|track`):
- U1 `PlayerRecord` + `compute_player_records` (standings aggregation, identity-resolved, windowed; reuse shrink + tier).
- U2 `is_strong` + `strong_player_set` (pure predicate + gate).
- U3 `player_archetype_history` (per-regime archetype rows) + `identify strong` / `identify track` CLI.

**Story 3 — consensus integration** (`consensus.py`, `tuning.py`, `cli generate consensus|tune`):
- U1 thread `players` / `alias_map` through `card_frequencies` `deck_pool` CTE (gated-additive; `None` = byte-identical).
- U2 thread through `build_consensus` + `tune_deck` seed; thin-pool honest-degrade banner.
- U3 `--players` / `--strong` CLI flags on `generate consensus|tune`; `--strong` wires to `strong_player_set`.

Trickiest unit first within each story: U1 of story 1 (collation SSOT), U1 of story 2 (the shrink/gate
honesty), U1 of story 3 (the gated-additive CTE that must stay byte-identical when `players is None`).

---

### Test plan

- **identity**: `resolve_player` maps the three `Bosh*` handles → one id and `Andrea Mengucci` → itself; unknown handle → itself; blank/None → `""`. `materialize_player_aliases` idempotent. `suggest_aliases` surfaces the `Bosh*` cluster from a synthetic corpus and **does not** propose merging two players who co-occur same-event-same-day. (pytest factory fixtures; in-memory DuckDB.)
- **strength**: a single 5-0 (events=1, n≈7) → `is_strong == False` (event floor + speculative tier). A 25-10 across 5 events → `True`. Shrinkage pulls a 6-0/2-event player below 1.0. `compute_player_records` sums correctly across events and respects the window. Determinism: same corpus → same scores.
- **consensus integration**: `build_consensus(..., players=None)` is **byte-identical** to the current output on a fixture corpus (the gated-additive invariant — assert equality against the un-filtered call). `players={strong}` narrows the pool and changes modal counts as expected on a hand-built corpus where a strong player runs a distinct flex card. Thin strong+windowed pool → `sample_n` low + speculative tier + banner; window is **not** silently widened.
- **regime-safety**: `generate consensus --strong` default window == latest regime; a strong player's prior-regime list does not leak into the current-regime consensus (fixture with one player strong across two regimes running different lists).

Test files mirror source: `tests/analytics/players/test_identity.py`, `test_strength.py`,
`test_history.py`, and additions to the existing consensus/tuning test modules.

---

### Risks

- **Curation burden / coverage.** The alias table only resolves what's curated; uncurated variants of a strong player split their record and may drop below the strength gate (false negative — conservative, acceptable). Mitigated by `identify suggest` surfacing clusters cheaply. The dogfooding loop (Andrew curates the Boulder-meta regulars he knows) is the intended workflow.
- **Standings coverage is bimodal.** MTGO League 5-0 dumps have no standings/rounds rows, so a player's online record may understate volume. `compute_player_records` is honest about `events` counted from standings only; documented, and the tier gate accounts for it (thin → not strong).
- **Cross-source identity unrecoverable by machine.** `Bosh95` (MTGO) ↔ paper real-name needs human input; the curated table is the only correct mechanism. Accepted by design (Decision 1).
- **Thin strong+regime pools.** The common case is few strong pilots × one regime → speculative sample. Handled by honest-degrade banner + tier, not silent window-widening (the explicit regime-safety guarantee). Weighting (deferred) would soften this later but is out of v1 scope.
- **Free-text join collation drift.** All identity resolution reuses `normalize_player` (`lower(trim)`) — the exact SSOT key `match_results` / `metashare` already join on. New code must not introduce a second collation; enforced by reusing the function, not re-implementing it.

### Rationale log (autopilot-resolved ambiguities)

- **Weight vs. filter** (the spec's open question): chose **hard-filter for v1**, weighting deferred — minimal auditable change into the existing pool-aggregation; weighting is a clean follow-up.
- **Heuristic vs. explicit alias table**: chose **explicit curated table + opt-in heuristic suggester** — silent false-merges poison the exact high-signal cells the feature targets; a wrong merge is worse than no merge.
- **Decomposed into 3 child stories** because identity, strength, and integration are independently testable and mergeable, and identity is reusable beyond this feature.
- **Regime interaction**: filter applies **on top of** windowing; default stays latest regime; no silent window-widening (directly honors [[idea-ban-regime-everywhere]]).


## Implementation notes
All three child stories implemented and at review: strong-player-signal-identity (alias resolution + curated aliases.json), strong-player-signal-strength (shrunk-WR strength scoring + per-regime history), strong-player-signal-consensus (--players/--strong filter into consensus/tune + `identify` CLI group). Full suite green (1492). Parent advanced to review per orchestrator Phase 9.
