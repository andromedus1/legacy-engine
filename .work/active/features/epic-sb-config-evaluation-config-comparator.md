---
id: epic-sb-config-evaluation-config-comparator
kind: feature
stage: done
tags: [advisory]
parent: epic-sb-config-evaluation
depends_on: [epic-sb-config-evaluation-matchup-slot-test]
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# Configuration / transform comparator (general engine, transform-first)

## Brief

A general engine that computes **field-weighted EV for a deck configuration**, with
**per-matchup sideboard-lift adjustments**, and **compares two configurations** against the
field — surfacing a per-matchup contribution diff and a **break-even**. The motivating special
case is a **transform-alternate**: one 75 modeled in two modes (e.g. Doomsday-tempo that
sideboards into Dimir Tempo), scored as `max(mode_A_native, mode_B_with_stripped_SB)` per
matchup, against the alternative of "base deck + a dedicated silver-bullet sideboard."

Generalizes `advisory/positioning.py::score(deck, field)` from one deck to two configs. The
engine is general internally either way — you cannot compute the transform envelope without
computing each config's full per-matchup vector, which *is* the general two-config comparison.

### Delivery sequence (per the epic's strategic decision — design carves child stories)
1. **Transform break-even first** (the validated need, robust to thin data): model the
   transform-alternate, output per-config field EV + per-matchup diff + the break-even — "the
   hate package must lift its target matchups by ≥X points to beat transforming." Break-even is
   the deliverable that stays decision-useful under the data ceiling, because the operator
   supplies confidence in the SB cards from play experience.
2. **General two-config comparison surface second**, exposing the same engine for
   build-A-vs-build-B / pre-tune-vs-post-tune comparisons.

Design the "config" abstraction grounded in **both** uses (transform + build-A-vs-B) so it's
pinned by ≥2 real uses, not one.

## What's new vs reused
- **Reuses** positioning's field-EV / Bayesian-MC machinery (Beta cells + Dirichlet shares).
- **New**: (a) a per-matchup **SB-adjustment layer** that applies measured lifts (consuming the
  `matchup-slot-test` feature where reliable) or operator-supplied assumptions where thin;
  (b) **two-config diff**; (c) **transform-alternate modeling** — `max` per matchup + the
  **stripped-SB** model (mode B plays *without* the silver bullets you spent on the transform
  package, so its bad matchups stay bad); (d) the **break-even solver**.

## Subsumes backlog idea `idea-sb-transformational-sideboarding`

That idea flagged that the sideboard recommender's coverage model is structurally blind to
**transformational sideboarding** — crediting *threats* (e.g. board in Barrowgoyf, dodge
removal, grind better vs control/midrange), not just *answers* to vulnerability tags (it even
mis-tagged Barrowgoyf `combo` via the promoted-card fallback). This feature is where
threat-swap / transform packages become representable and valued: a "config" can be a
threat-swapped or transformed 75, and the comparator scores it on field EV rather than
answer-coverage. Design should connect the transform-alternate model back to
`advisory/sideboard.py`'s OUT/IN plans so a recommended transform reads as a coherent package.

## Known constraint
Honors the parent epic's data ceiling. The break-even framing is the robust deliverable
*because* the underlying SB-lift numbers are presence-correlational proxies on thin samples —
the tool structures the operator's judgment rather than claiming the data decides.

## Reference finding (what the tool should reproduce)
Session hand-calc over the n≥30 Boulder field: Config A (Dimir + hate SB) ≈ 52.7% (the hate SB
added only +0.7 field-EV points — only Toxic Deluge vs D&T moved, and D&T is 5.6% of field);
Config B (Doomsday-transform) ≈ 56.1%. Break-even: the hate package would need to lift each of
D&T/Energy/Artifacts by ~32 points to match transforming; measured best was Toxic Deluge at
+11. The comparator should make this calculation first-class, repeatable, and honest about its
assumptions.

## Design decisions
- **Config input (CLI)**: Named-archetype + modifier flags. `advise compare --field <f> --a "<archA>"
  --b "<archB>" [--a-transform "<arch>"] [--b-transform "<arch>"] [--a-lift "opp=+d,..."]
  [--b-lift ...] [--a-lift-slot "card@opp" ...]`. Matchup data is archetype-keyed, so a decklist
  adds nothing the engine uses; flags are explicit + scriptable; transform = a second mode flag.
- **Lift source**: Both. User-supplied deltas (`--a-lift`) are the base (you assert the lift →
  break-even framing); an optional slot-test auto-pull (`--a-lift-slot "Toxic Deluge@Death & Taxes"`)
  reuses Piece 1 (`card_matchup_contrast`) to pull the measured full-corpus diff as the lift.
- **Stats depth**: Both, clearly separated. A Bayesian-MC layer on the BASE (no-lift) numbers gives
  per-config field-EV CIs + P(Config A beats Config B); a point-estimate overlay applies the lifts
  deterministically (no false precision on hand-asserted deltas) and drives the break-even.
- **Break-even definition**: solve for the uniform additional per-matchup lift `L*` on Config A's
  target matchups (declared-lift matchups, or `--break-even-matchups`) such that point-EV(A)==EV(B),
  computed from Config A's BASE WRs: `L* = (EV_b_adj − EV_a_base) / Σ_{targets} share`. `L* ≤ 0` →
  "A already ahead, no lift needed"; `L*` infeasible within [0,1] → "not achievable".

## Architectural choice

Three options (Phase 5a):
- **(A · chosen)** New module `advisory/compare.py` (a `DeckConfig`/`ConfigMode` model + a pure-ish
  `compare_configs(matrix, field, a, b)` returning a `ComparisonResult`) surfaced by a new
  `advise compare` leaf. Reuses the matchup matrix cells, `field.py` (custom `--field`), and
  positioning's MC primitives (Beta cells + Dirichlet shares) **generalized** to take a per-matchup
  `max` over modes. Clean separation; the transform is just the 2-mode case of one engine.
- **(B · rejected)** Extend `positioning.py` to score multiple configs. Rejected — positioning is
  single-deck S; two-config + transform-max + lift overlay + break-even is a distinct concern that
  would bloat it.
- **(C · rejected)** Point-estimate only, no MC. Rejected per the stats decision (both layers).

The engine is general either way: a `DeckConfig` is a list of `ConfigMode`s, and a config's
per-opponent WR is `max` over its modes. A plain deck + hate SB is one mode with `lifts`; a
transform-alternate is two modes with no lifts on the second (the stripped sideboard). Shared
`(archetype, opponent)` cells are sampled ONCE per MC draw and reused across configs so a shared
mode (e.g. both configs containing a Dimir mode) is correctly correlated.

## Implementation Units

### Unit 1: Config model + point-estimate engine (Story: -engine)

**File**: `src/legacy_engine/advisory/compare.py` (new)

```python
from dataclasses import dataclass, field as dc_field
from legacy_engine.confidence import ConfidenceLevel

@dataclass
class ConfigMode:
    archetype: str
    lifts: dict[str, float] = dc_field(default_factory=dict)   # opponent -> additive WR delta (overlay only)

@dataclass
class DeckConfig:
    label: str
    modes: list[ConfigMode]              # 1 = plain deck (+optional hate lifts); 2 = transform (per-matchup max)

@dataclass
class MatchupContribution:
    opponent: str
    share: float
    wr_a_base: float; wr_b_base: float        # max-over-modes base p_shrunk (point)
    wr_a_adj: float;  wr_b_adj: float         # base + lifts (clamped [0,1])
    chosen_mode_a: str; chosen_mode_b: str    # which mode won the max (transform readout)
    imputed_a: bool; imputed_b: bool          # no measured cell for the chosen mode → 0.5 impute
    contribution_diff: float                  # share * (wr_a_adj - wr_b_adj)

@dataclass
class ComparisonResult:
    a_label: str; b_label: str; field_source: str
    rows: list[MatchupContribution]           # sorted by abs(contribution_diff) desc
    ev_a_base: float; ev_b_base: float        # point EV, no lifts
    ev_a_adj: float;  ev_b_adj: float         # point EV, with lifts
    ev_a_base_ci: tuple[float, float]; ev_b_base_ci: tuple[float, float]   # MC layer
    p_a_beats_b_base: float                   # P(S_a_base > S_b_base), paired draws
    n_draws: int
    breakeven_lift: float | None              # uniform per-target lift for parity (None if A ahead)
    breakeven_targets: list[str]
    breakeven_feasible: bool                  # False if L* would exceed [0,1]
    coverage_a: float; coverage_b: float      # share-mass with measured cells
    warnings: list[str]

def compare_configs(
    matrix, field, config_a: DeckConfig, config_b: DeckConfig, *,
    n_draws: int = 20_000, seed: int | None = None,
    breakeven_targets: list[str] | None = None,
) -> ComparisonResult: ...
```

**Implementation Notes**:
- **Per-opponent base WR for a config** = `max` over its modes of the matrix cell `p_shrunk`
  (mirror cell → 0.5; missing/n=0 cell → 0.5 impute + `imputed=True`). `chosen_mode` = the
  argmax mode (for the transform readout: "vs D&T you're in Doomsday mode").
- **Point EV** = `Σ_opp share·wr` over field shares (from `FieldDistribution.shares`). `_adj`
  applies `lifts` to the chosen mode's WR (clamp [0,1]) before the max — actually apply lift per
  mode then max, so a lift can change which mode wins.
- **Break-even**: `targets` defaults to the union of Config A's declared-lift opponents; else
  `breakeven_targets`. `L* = (ev_b_adj − ev_a_base) / Σ_{t in targets} share`. `≤0` → None (A
  ahead). If `min(ev_a_base_per_target_capped...)` pushing past 1.0 → `breakeven_feasible=False`.
- Coverage = Σ share over opponents with a measured (non-imputed) cell for the config.

**Acceptance Criteria**:
- [ ] One-mode config EV == `Σ share·p_shrunk` on a hand-built matrix/field (matches by hand).
- [ ] Transform config WR per opponent == max of the two modes' cells; `chosen_mode` correct.
- [ ] Lifts shift `wr_*_adj` and can change the winning mode; clamped to [0,1].
- [ ] Break-even `L*` solves `ev_a_base + L*·Σtargets share == ev_b_adj`; `None` when A already ahead;
      `breakeven_feasible=False` when infeasible.
- [ ] Imputed opponents flagged and excluded from coverage.

### Unit 2: Bayesian-MC base layer (trickiest — design-first; Story: -engine)

**File**: `src/legacy_engine/advisory/compare.py` (same module)

**Implementation Notes**:
- Generalizes positioning's `_sample_S` to multi-mode `max` + two configs with **shared cell draws**.
  Per draw `d`: (1) sample field shares — Dirichlet from `field` counts if present, else fixed point
  shares (mirror positioning's handling, gamma=0.5); (2) for every DISTINCT `(archetype, opponent)`
  cell needed by either config, draw one `Beta(wins+½, losses+½)` WR (Jeffreys), reused across both
  configs so shared modes correlate; mirror=0.5, imputed=0.5 fixed; (3) `S_a_d = Σ_opp share_d ·
  max_{mode∈A} wr_d[(mode.arch, opp)]`, same for B; **no lifts in the MC** (base layer only).
- `p_a_beats_b_base = mean(S_a_d > S_b_d)`; CIs = 2.5/97.5 percentiles of each S sample.
- Reuse `analytics.matchup` cell access for wins/n; reuse positioning's RNG seeding idiom
  (`np.random.default_rng(seed)`) for determinism.

**Acceptance Criteria**:
- [ ] Deterministic given `seed`.
- [ ] A config strictly dominating another (every cell higher) → `p_a_beats_b ≈ 1.0`.
- [ ] Two identical configs → `p_a_beats_b ≈ 0.5` and CIs overlap (shared cell draws ⇒ near-degenerate diff).
- [ ] CI widths shrink as cell `n` grows (Beta concentration).

### Unit 3: slot-test lift auto-pull helper (Story: -engine)

**File**: `src/legacy_engine/advisory/compare.py`

```python
def slot_lift(con, archetype: str, card: str, opponent: str, *, board: str = "side") -> float | None:
    """Full-corpus measured WR diff (with − without) for `card` in the `archetype` vs `opponent`
    matchup, via Piece 1's card_matchup_contrast. None if the cell has no computable diff."""
```

**Acceptance Criteria**:
- [ ] Returns the `card_matchup_contrast` full-corpus cell `diff` for the (card, opponent).
- [ ] Returns `None` when either cohort is empty (no diff).

### Unit 4: `advise compare` CLI leaf + rendering (Story: -cli)

**File**: `src/legacy_engine/cli.py` (new leaf under the `advise` group)

**Implementation Notes**:
- Flags per the Config-input decision; parse `--a-lift "opp=+0.11,opp2=-0.03"` → dict; `--a-lift-slot
  "Card@Opponent"` (repeatable) → `slot_lift(...)` merged into the mode's lifts (user-supplied wins
  on conflict, with a note). **Fail-fast** (`ClickException`) if `--a`/`--b` missing or a lift opp
  isn't in the field.
- Build matrix+field via `build_advisory_inputs` + `build_custom_field` (the advisory-window-
  resolution-block + audit-echo `// ...` patterns); `--field` required for a meaningful comparison
  (else global field). Construct the two `DeckConfig`s, call `compare_configs`, render.
- Render: a header EV summary (base EV ± CI, P(A>B), adjusted EV); the per-matchup table
  (opponent | share | A wr (mode) | B wr (mode) | contribution diff); the break-even line; honesty
  banners (presence-correlational lift overlay; thin-cell tiers; imputed/coverage; data ceiling).

**Acceptance Criteria**:
- [ ] `advise compare` without `--a`/`--b` → clear `ClickException`.
- [ ] `--b-transform` adds a second mode; the table shows the chosen mode per matchup.
- [ ] `--a-lift-slot` pulls a measured diff and folds it into Config A's lifts.
- [ ] Output prints the base MC P(A>B), the adjusted point EVs, and the break-even line.
- [ ] Lift overlay + data-ceiling banners always print.

## Implementation Order

1. **Unit 1** (config model + point engine) — foundation; everything reads its types.
2. **Unit 2** (MC base layer) — trickiest; validate the max-over-modes draw early.
3. **Unit 3** (slot-test pull) — small; depends on Unit 1 types only.
4. **Unit 4** (CLI) — depends on Units 1-3.

## Testing

### Unit tests: `tests/advisory/test_compare.py`
- Hand-built `MatchupMatrix` + `FieldDistribution` (small, deterministic) — assert one-mode EV, transform `max` + chosen_mode, lift application + mode-flip, break-even `L*` (ahead / feasible / infeasible), coverage + imputation.
- MC: seeded determinism; dominating config → P≈1; identical configs → P≈0.5; CI shrinks with n.
- `slot_lift` against the hermetic slot-test corpus (reuse the Piece-1 builder shape): returns the diff; None on empty cohort.

### CLI tests: `tests/test_cli.py` (extend)
- File-backed DB + `--db`, `--field <tmp>`: fail-fast without `--a`/`--b`; transform mode shown; `--a-lift` parsed; `--a-lift-slot` folds a measured diff; break-even + P(A>B) + banners present.

## Risks

- **Lift overlay invites over-trust** (data ceiling): a hand-asserted `--a-lift` is an assumption,
  not data. **Mitigation**: lifts only ever touch the point-estimate overlay (never the MC base);
  the break-even framing + mandatory banner keep it judgment-structuring, not "proven".
- **Transform max optimism**: `max` over modes assumes you always end in the better mode post-board
  and ignores the Game-1-in-the-wrong-mode tax. **Mitigation**: document it in the output banner;
  it's the optimistic ceiling (consistent with how the session analysis framed the envelope).
- **MC cost** (two configs × cells × 20k draws): acceptable (positioning runs the same scale), but
  cap `n_draws` and reuse one cell-draw across configs. **Fallback**: lower default draws if slow.
- **Imputation dominance**: a config whose mode has little field coverage gets a 0.5-heavy EV.
  **Mitigation**: report `coverage_*` and warn when low (mirror positioning's coverage honesty).

## Implementation notes
- **Files changed**: `src/legacy_engine/advisory/compare.py` (new — config model, point engine,
  MC base layer, break-even, `slot_lift`); `src/legacy_engine/cli.py` (new `advise compare` leaf +
  `_parse_lift_spec`/`_apply_slot_lifts`/`_echo_comparison` helpers).
- **Tests added**: `tests/advisory/test_compare.py` (13 — point EV, transform max + chosen_mode,
  lift overlay + clamp, break-even ahead/feasible/infeasible, coverage/imputation, MC determinism /
  dominating→P≈1 / identical→P≈0.5 / CI-shrinks-with-n, `slot_lift`); `tests/test_cli.py::
  TestAdviseCompare` (6). Full suite green: **2278 passed**.
- **Stories**: engine + cli both done.
- **Validated on real data**: `advise compare --field boulder-field-current.txt --a "Dimir Tempo"
  --a-lift-slot "Toxic Deluge@Death & Taxes" --b "Doomsday" --b-transform "Dimir Tempo"` →
  P(A beats B)=0.00 (transform-into-Dimir weakly dominates plain Dimir by construction), Doomsday
  mode chosen for D&T (68.8%), break-even = +35 pts on D&T to tie vs the +10.7 Toxic Deluge
  delivers — reproduces the session's opportunity-cost verdict.
- **Discrepancies from design**:
  - `p_a_beats_b` splits ties (`>` + 0.5·`==`) so identical configs read 0.5 not 0.0 (shared
    per-draw cell draws make identical configs element-wise equal).
  - `compare_configs` ignores a lift opponent absent from the field; the CLI fail-fasts on it
    (validation belongs at the boundary, not the pure engine).
- **Adjacent issues parked**: none.

## Review record
- **Verdict**: Approve with comments (deep lane, fresh-context reviewer). No blockers.
- **Verified correct**: MC shares field weights + reuses one Beta draw per distinct cell across
  configs (shared modes correlate); lifts kept strictly out of the MC; tie-split `p_a_beats_b`;
  Beta/Dirichlet params + imputation consistent with positioning; no numpy leakage; advisory-window
  + audit-echo patterns followed.
- **Findings — all resolved in-session before advancing**:
  - *Important #1 (bug)*: `_config_point` set `wr_base` to the adj-winning mode's base, not the
    max-over-modes base — understated `ev_a_base` and overstated the break-even for `--a-transform`
    + `--a-lift`. Fixed: `wr_base` is now an independent max over modes' base WRs. Regression test
    added (`TestBaseDecoupledFromAdjWinner`).
  - *Important #2*: coverage ignored the n≥30 display gate (a thin n=5 cell counted as measured).
    Fixed: `_row_point_wr` returns cell `n`; coverage uses `n>=_DISPLAY_N`. Test added.
  - *Important #3*: missing thin-cell honesty marker (unmet AC). Fixed: cells now render `*`
    (imputed) / `~` (0<n<30 thin) with a legend line.
  - *Important #4*: ARCHITECTURE.md drift — added `compare` to the `advise` enumerations
    (CLI box, leaf list, `--provenance` list) + a descriptive bullet.
  - *Nit #5*: break-even `None` message disambiguated (A-ahead vs no-targets, via `ev_a_base`
    vs `ev_b_adj`).
  - *Nit #6*: dropped a stray f-string.
- Full suite green after fixes: **2280 passed**.
