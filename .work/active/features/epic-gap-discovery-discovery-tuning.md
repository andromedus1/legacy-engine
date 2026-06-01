---
id: epic-gap-discovery-discovery-tuning
kind: feature
stage: implementing
tags: [generation, discovery]
parent: epic-gap-discovery
depends_on: [epic-gap-discovery-adjacency]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Discovery Tuning (value transfer + gated suggestion surface)

## Brief

The evidence + honesty layer on top of the adjacency model: takes the nominated candidates
from `epic-gap-discovery-adjacency` and decides which to surface as exploratory swap-in
suggestions, with explicit uncertainty. This is the **key unlock** — a candidate is by
definition under-played in the shell, so its in-shell per-card signal is thin; the fix is
**cross-archetype value transfer**. `analytics/card_value` already pools per-`(card, board,
opponent)` lift across ALL decks (not conditioned on the running deck's archetype), so
`card_values_vs([X], board, opponent=M)` gives `X`'s lift vs threat `M` over every deck that
ran it. Transfer that lift, shrunk toward no-edge by the cross-field `n`
(`matchup.beta_binomial_shrink_to`, the two-level-empirical-Bayes pattern).

**Transfer is role-gated** (a new small, curated `TRANSFERABLE_ROLES` allow-list, mirroring
how `sideboard.HOSER_CATALOG` treats answers as archetype-independent): transfer the matchup
lift for answer/hoser/generic-cantrip roles where it is honest; for **synergy/engine roles**
(combo enablers, payoffs, build-arounds) the pooled lift is meaningless out of context, so
those candidates are still nominated but must clear the **normal un-transferred in-shell
confidence gate** (no transfer credit) to surface — per the inherited decision below.

Surfaces via a new **`--discover` flag on `generate tune`**: when set, the command appends a
**distinct, clearly-flagged exploratory-suggestion section** after the proven in-pool swap log
— never silently mixed in. Discovery suggestions NEVER drive the greedy swap objective (that
preserves the existing no-gameplan-hollowing guarantee); they are suggest-and-label only.
Every suggestion is gated at the **established tier (≥100 cross-field n)** by default and
labeled `presence-correlational, transferred from cross-field data, NOT goldfish-validated`
(reuse the `report cards` / `advise sideboard` disclaimer wording). Exploration is capped at a
few candidates.

Does NOT cover the adjacency/nomination logic (that's the dependency) nor goldfish validation
(the deferred `epic-goldfish-simulation` pillar slots in later as a candidate → goldfish-passes?
→ promote-from-suggestion filter; design the output so that filter drops in without a rewrite).

## Epic context

- Parent epic: `epic-gap-discovery`
- Position in epic: consumer of `epic-gap-discovery-adjacency` — the riskiest feature in the
  epic (it is where exploration could fabricate edges), so the confidence gating is load-bearing.

## Inherited design decisions

- **Card-discovery CLI surface = `--discover` flag on `generate tune`** (not a separate
  `generate discover` command) — one command, two clearly-flagged output blocks; proven swaps
  first, exploratory suggestions in a distinct labeled section after.
- **Synergy/engine-piece candidates = include, but require in-shell evidence (option b)** —
  they are nominated by the adjacency model but get NO cross-field transfer credit; they must
  clear the normal un-transferred in-shell confidence gate to surface (in practice they rarely
  will, since they are under-played in the shell by definition — but the path is general).
- **Transfer is role-gated** via a new curated `TRANSFERABLE_ROLES` allow-list (answers / hosers
  / generic cantrips), mirroring `sideboard.HOSER_CATALOG`.
- **Shrinkage**: transferred lift is a prior shrunk toward 0 (no-edge) by cross-field `n` via
  `beta_binomial_shrink_to`.
- **Confidence bar = established tier (≥100 cross-field n)** for a discovery suggestion to
  surface by default — a HIGHER bar than in-pool tuning (which accepts evolving), because the
  candidate is unproven in this shell. Do not relax for coverage.
- **Honesty invariants** (load-bearing, non-negotiable): distinct flagged section, never in the
  proven swap log; never drives the greedy objective; explicit correlational + not-goldfish
  labels; capped exploration count.
- **Windowing / reuse**: thread the tuner's latest-ban-regime window; reuse ONE `CardWinRates`
  aggregate across tune + discovery (per `fix-tuning-sideboard-winrate-reuse`, and the open
  backlog perf note `idea-tuning-sideboard-winrate-reuse`).

## Research briefs

- `docs/briefs/card-adjacency-and-discovery.md` §2 (cross-archetype value transfer — the role
  decomposition + shrinkage), §3 (risk & validation — confidence gating, what v1 can/cannot
  claim, where goldfish fits later), §Implementation Notes.

## Foundation references

- `src/legacy_engine/analytics/card_value.py` — `card_values_vs` / `CardValue` (the transferable
  per-card×matchup quantity).
- `src/legacy_engine/analytics/matchup.py` — `beta_binomial_shrink_to` (shrinkage primitive).
- `src/legacy_engine/advisory/sideboard.py` — `HOSER_CATALOG` (the archetype-independent-answers
  precedent `TRANSFERABLE_ROLES` mirrors).
- `src/legacy_engine/generation/tuning.py` — `tune_deck` / `TunedDeck` (the command this flag
  extends; discovery composes alongside, does not enter, the greedy objective).
- `src/legacy_engine/cli.py` — `@generate.command("tune")` (~line 1232).

## Design decisions

Resolved with judgment during feature-design (autopilot delegation). The strategic forks
(`--discover` flag, synergy=option-b, transfer-by-role, established gate, honesty invariants)
were locked at the epic and are inherited above; these are the mechanical realizations:

- **Transfer reuses the already-shrunk `CardValue.lift`** — `compute_card_winrates` produces a
  two-level empirical-Bayes `lift = p_shrunk − prior_mean` that already regresses to ~0 as `n→0`.
  So the brief's "shrink the transferred lift toward 0 by cross-field n" is **subsumed**: I use
  `lift` directly and gate on `tier == "established"`. No separate `beta_binomial_shrink_to` re-shrink
  (it would double-shrink). This is the honest, SSOT reuse of the shipped machinery.
- **`TRANSFERABLE_ROLES = {counter, removal, protection, card_advantage, discard}`** — answers /
  disruption / generic card-advantage, where cross-archetype value is pilot-independent (brief §2
  table). NON-transferable (synergy/engine): `threat, ritual, storm, tutor, graveyard_recursion,
  stax, fast_mana`. Curated like `sideboard.HOSER_CATALOG`. A candidate is "transferable" iff
  `matched_roles ∩ TRANSFERABLE_ROLES ≠ ∅` (the answer aspect carries it).
- **Synergy/engine candidates (epic option b, faithfully)**: they ARE nominated by adjacency and
  the in-shell gate IS attempted, but v1 has **no archetype-conditioned per-card value source**
  (`card_value` pools cross-field; transferring it to a synergy card is invalid per the brief). So
  the in-shell gate cannot be satisfied in v1 → these candidates never surface and are **reported**
  (count + names: "omitted — synergy role, needs in-shell/goldfish validation"). This is option (b)
  (path exists, rarely fires — exactly as predicted), NOT option (a) (which wouldn't nominate them).
  The future `epic-goldfish-simulation` is precisely the in-shell signal that lets them surface.
- **Transfer target = field-weighted over all field opponents** — `transferred_value =
  Σ_M field.shares[M] · lift(X vs M)` over gate-clearing (`established`, `lift > 0`) cells,
  mirroring `tuning.field_weighted_values`. Weak-to-specific targeting (only the matchups the deck
  is losing) is a documented later refinement, not v1.
- **Established-tier gate by default** (`discovery_gate = ("established",)`, n≥100) — a HIGHER bar
  than in-pool tuning (which accepts `evolving`), because the candidate is unproven in this shell.
- **CardWinRates reuse** — add an additive `card_winrates: CardWinRates | None = None` param to
  `tune_deck` (default None = current behavior; threads into its internal `field_weighted_values`).
  The `--discover` CLI path computes `compute_card_winrates` ONCE and passes the same instance to
  both `tune_deck` and `discover_candidates` (partially closes `idea-tuning-sideboard-winrate-reuse`).
- **Surface** — `--discover` flag on `generate tune`; a DISTINCT labeled section printed AFTER the
  proven swap log / matchup plans; discovery NEVER enters the greedy objective (the no-hollowing
  guarantee is untouched). Capped at `--discover-cap` (default 5) by `transferred_value`; the
  capped-out + below-gate + synergy-omitted counts are all reported (no silent caps). Each suggestion
  carries the presence-correlational + transferred + NOT-goldfish-validated label.

## Architectural choice

Discovery is a read-only *suggestion* layer bolted onto `generate tune`, never a swap driver — this
is the load-bearing safety choice (protects the shipped no-gameplan-hollowing guarantee). Two shapes
were weighed for *where* the scoring lives: (A) extend `tuning.py` with discovery logic — rejected,
the brief explicitly says keep discovery OUT of `tuning.py` (tuning stays the proven-swap engine);
(B) **put discovery in `generation/discovery.py` alongside the adjacency model it consumes** (chosen)
— the candidate nomination and its scoring live together, `tune_deck` stays untouched except for the
additive `card_winrates` injection, and the CLI composes the two. The scoring itself is split
objective-search style: a pure `_transfer_from_values(values, field, gate)` (testable with hand-built
`CardValue`s, no DB) under the DB-driven `discover_candidates`.

## Implementation Units

### Unit 1: roles allow-list + result records

**File**: `src/legacy_engine/generation/discovery.py` (extend)

```python
TRANSFERABLE_ROLES: frozenset[str] = frozenset(
    {"counter", "removal", "protection", "card_advantage", "discard"}
)

@dataclass(frozen=True)
class DiscoverySuggestion:
    name: str
    matched_roles: frozenset[str]
    transferred_value: float                 # Σ field.shares[M]·lift over gate-clearing M
    per_opponent: dict[str, CardValue]       # opp → the gate-clearing CardValue (audit trail)
    n_total: int                             # Σ cv.n over kept opponents
    pmi: float                               # carried from the AdjacencyCandidate
    cmc: float
    in_sideboard: bool

@dataclass(frozen=True)
class DiscoveryResult:
    suggestions: list[DiscoverySuggestion]   # capped, sorted transferred_value DESC
    n_considered: int                        # adjacency candidates examined
    omitted_below_gate: int                  # transferable cands with no established lift>0 cell
    omitted_synergy: list[str]               # synergy-role cands (need in-shell/goldfish)
    capped_out: int                          # surfaced-eligible beyond the cap
    gate: tuple[str, ...]
    disclaimer: str
```

**Acceptance Criteria**:
- [ ] `TRANSFERABLE_ROLES` excludes `threat`/`ritual`/`storm`/`tutor`/`graveyard_recursion`/`stax`/`fast_mana`.
- [ ] Frozen dataclasses; `suggestions` sorted by `transferred_value` DESC.

---

### Unit 2 (trickiest): transfer scoring — pure core + orchestrator

**File**: `src/legacy_engine/generation/discovery.py`

```python
def _transfer_from_values(
    values: dict[str, CardValue],          # opponent → CardValue (from card_values_vs)
    field: FieldDistribution,
    *,
    gate: tuple[str, ...],
) -> tuple[float, dict[str, CardValue]]:
    """PURE: field-weighted positive transferred lift over gate-clearing established cells.

    Keeps opp iff cv.tier in gate AND cv.lift > 0 AND opp in field.shares;
    contribution = field.shares[opp] · cv.lift. Returns (total, kept_values).
    """

def discover_candidates(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
    field: FieldDistribution | None = None,
    *,
    rates: "CardWinRates | None" = None,
    cap: int = 5,
    gate: tuple[str, ...] = ("established",),
    lock_threshold: float = 0.65,
    cooccur_floor: int = 5,
    adjacency_limit: int | None = None,
    since: str | None = None,
    until: str | None = None,
) -> DiscoveryResult:
    """Nominate (adjacency) → role-split → transfer/gate → assemble the suggestion list."""
```

**Implementation Notes**:
- `field` None → `build_global_field(con)`; `rates` None → `compute_card_winrates(con, since, until)`.
- `cands = adjacency_candidates(con, archetype, maindeck, sideboard, lock_threshold=…,
  cooccur_floor=…, limit=adjacency_limit, since=…, until=…)`.
- For each `c`: if `c.matched_roles & TRANSFERABLE_ROLES`: `values = card_values_vs(rates, [c.name],
  "main", M)` per field opponent M (or one call per M — `card_values_vs` is per-opponent), build the
  `opp→CardValue` dict, then `_transfer_from_values(...)`. If `total > 0` → `DiscoverySuggestion`
  (basis transferred). Else `omitted_below_gate += 1`. If NOT transferable → `omitted_synergy.append(name)`.
- Sort eligible by `transferred_value` DESC (tie `n_total` DESC, then name); `capped_out =
  max(0, len(eligible) − cap)`; keep top `cap`.
- `disclaimer` = the `report cards` / `advise sideboard` wording: presence-correlational, transferred
  from cross-field data, NOT goldfish-validated.

**Acceptance Criteria**:
- [ ] A transferable candidate with an established `lift>0` cell vs a field opponent surfaces with the
      correct field-weighted `transferred_value`.
- [ ] A candidate whose only cells are `evolving`/`speculative` is omitted (counted in `omitted_below_gate`).
- [ ] A synergy-role-only candidate is omitted and named in `omitted_synergy` (never surfaced).
- [ ] `cap` honored; `capped_out` reports the remainder (no silent cap).
- [ ] Determinism across two calls with the same inputs.

---

### Unit 3: `tune_deck` CardWinRates injection (additive)

**File**: `src/legacy_engine/generation/tuning.py`

```python
def tune_deck(con, archetype, maindeck, sideboard, *, field=None, since=None, until=None,
              lock_threshold=…, max_swaps=…, card_winrates=None) -> TunedDeck:
```

**Implementation Notes**:
- Add the param; at the internal compute site (≈ line 679) use the injected `card_winrates` when
  provided, else compute as today. Backward-compatible: existing callers/tests pass nothing → byte-
  identical behavior. NO other tuning logic changes.

**Acceptance Criteria**:
- [ ] `tune_deck(..., card_winrates=r)` does not recompute; result identical to the un-injected call
      on the same corpus.
- [ ] Existing tuning tests pass unchanged.

---

### Unit 4: `--discover` flag + `_print_discovery`

**File**: `src/legacy_engine/cli.py` (`generate tune` command)

```python
@click.option("--discover", is_flag=True, default=False,
              help="Also suggest adjacent swap-in candidates (exploratory; labeled, never auto-swapped).")
@click.option("--discover-cap", type=int, default=5, show_default=True,
              help="Max exploratory discovery suggestions to show.")
def _print_discovery(result: "DiscoveryResult") -> None: ...
```

**Implementation Notes**:
- When `--discover`: compute `compute_card_winrates` ONCE in the command; pass to BOTH `tune_deck`
  (new param) and `discover_candidates`. Print a clearly-fenced `// === Discovery (exploratory) ===`
  section AFTER the swap log + matchup plans. List each suggestion (name, transferred_value, matched
  roles, top opponents w/ lift+n+tier, `[in SB]` flag). Then the honest footer: omitted_below_gate
  count, omitted_synergy names, capped_out count, and the NOT-goldfish-validated disclaimer.
- Without `--discover`: behavior byte-identical to today (no extra scan).

**Acceptance Criteria**:
- [ ] `generate tune --discover --help` shows `--discover` + `--discover-cap`.
- [ ] With `--discover` the output contains a distinct Discovery section + disclaimer; without it, none.
- [ ] The proven swap log/plans are unchanged by the flag (discovery never enters the greedy path).

## Implementation Order

1. **Unit 1** records + `TRANSFERABLE_ROLES`.
2. **Unit 2** `_transfer_from_values` (pure, test first) then `discover_candidates`.
3. **Unit 3** `tune_deck` injection (additive; run existing tuning tests to prove no drift).
4. **Unit 4** CLI flag + renderer + the one-scan wiring.

## Testing

### Unit tests: `tests/test_discovery_tuning.py`
- `_transfer_from_values` (pure, hand-built `CardValue`s + `FieldDistribution`): established+lift>0
  counted with correct field weighting; evolving/speculative rejected under `gate=("established",)`;
  `lift<=0` rejected; opponent absent from field ignored.
- `discover_candidates` (corpus + injected `rates`): transferable card surfaces; evolving-only card
  → `omitted_below_gate`; synergy-role card → `omitted_synergy`; `cap`/`capped_out`; determinism.
  Reuse the `make_rounds_corpus` deck/rounds fixture + a seeded cards table (Surgical/Brainstorm etc.).
- `tune_deck` injection: result with injected `rates` equals the un-injected result (no drift).
- CLI: `generate tune --discover` against an in-memory `--db` — Discovery section + disclaimer present;
  absent without the flag; swap log identical with/without.

### Integration
- End-to-end on the seeded corpus: a deck weak to a field threat gets an on-role, color-legal,
  established-lift candidate suggested, clearly labeled and separate from the proven swaps.

## Risks

- **Double-shrink avoided** — using `CardValue.lift` (already EB-shrunk) instead of re-applying
  `beta_binomial_shrink_to` is deliberate; re-shrinking would understate real edges. **Fallback**:
  if `established` proves too sparse on real data, the gate is a param (could admit `evolving` with a
  louder label) — but NOT relaxed in v1.
- **Synergy candidates never surface in v1** — by design (no in-shell source); reported honestly.
  **Risk**: users read "omitted" as a bug. **Mitigation**: the omitted line states the reason +
  goldfish path. **Fallback**: none needed.
- **Two corpus scans in the non-injected path** — mitigated by the `card_winrates` injection on the
  `--discover` path; the residual (tune + discover both scanning when called separately) is the
  existing `idea-tuning-sideboard-winrate-reuse` backlog item, not regressed here.
- **`card_values_vs` per-opponent call volume** — one lookup per field opponent per candidate; field
  is small (≤~30 archetypes) and `rates` is precomputed, so it's dict lookups, not scans. Fine.
