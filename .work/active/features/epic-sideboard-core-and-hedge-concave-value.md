---
id: epic-sideboard-core-and-hedge-concave-value
kind: feature
stage: review
tags: [advisory, sideboard]
parent: epic-sideboard-core-and-hedge
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Concave per-copy value model

## Brief

Replace the sideboard solver's linear-in-copies element value with a concave per-copy
marginal-value function, so the k-th copy of a hoser is correctly worth less than the first. This
is the foundation feature — every other feature in the epic builds on the value it produces. Per
the brief's **key correction**, the model is `Δvalue(C, k) = share(e) · swing(C,e) · ΔP_access(k) ·
U_redundancy(k)`: `ΔP_access` is the (mildly concave) hypergeometric access increment, and
`U_redundancy(k)` — the sharply-decaying redundant-DRAWN-copy utility — is the term that actually
produces saturation (the access curve alone is too gently concave to stop padding).

Lands in `advisory/sideboard.py::_build_coverage_model`, changing how element weights scale with
copies. Recommend the brief's defaults (hypergeometric `1 − C(60−k, seen)/C(60, seen)` at a
turn-N "cards seen" default; `U_redundancy` ≈ 1.0 / 0.5–0.6 / ≤0.25 at copies 1/2/3, tunable). The
product of concave terms must stay **submodular** so the greedy solver keeps 1−1/e and the ILP
stays valid via piecewise-linear concave segments.

Does NOT cover the natural-budget stop (that's the dedicated-core feature), the output contract, or
the hedge — only the per-(card,copy) marginal-value primitive they all consume.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: foundation feature — the dedicated-core, output-contract, and hedge features all
  consume this value model. First in the v1 wave.

## Inherited design decisions
- Recommend the brief's defaults for the access curve + redundancy decay (strong evidence); keep the
  curve parameters tunable, no hardcoded per-card cap.
- Preserve submodularity (greedy 1−1/e; ILP piecewise-linear concavity) — not a solver-class change.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §2 (the access-probability curve + the U_redundancy
  correction; the computed hypergeometric table; calibration inputs).
- `docs/briefs/advisory-methods.md` §3 (inherited max-coverage / submodular-greedy / ILP — do not
  re-derive).

## Foundation references
- `docs/ARCHITECTURE.md` — `sideboard.py` row (weighted submodular max-coverage).
- Patterns: [[objective-search-split]] (heavy DB compute → dict → pure scored loop — the seam to
  keep the value model unit-testable with hand-built inputs), [[confidence-metadata]].

## Design decisions
- **`U_redundancy` is PER-CARD-COPY, not per-element** (brief §1/§2: "the 2nd copy *in hand* is a dead
  draw"). The existing per-element `g(cov_e) = 1−(1−p)^n` already models cross-answer coverage
  reliability (≈ the brief's `ΔP_access`); what the solver lacks is a penalty on stacking copies of
  the *same* card. This feature adds exactly that. (Rejected: replacing `g` with a per-card
  hypergeometric — bigger, drops the cross-answer reliability the existing `g` correctly models;
  element-level redundancy — double-counts with `g`.)
- **Composed as an ADDITIVE per-copy penalty, not a multiplicative factor** — so the greedy and the
  ILP share one identical objective. A multiplicative `U_redundancy(k) × coverage_marginal` is
  coverage-dependent (depends on other cards' `cov_e`) and therefore NOT exactly LP-representable;
  an additive `penalty(k)` on the k-th copy is a constant coefficient → exact in the ILP and
  identical in greedy. The ILP stays primary/exact, greedy stays the consistent explainable trace.
- **Gated-additive default = no-op.** A `redundancy_decay` switch (off by default) makes
  `penalty(k)=0 ∀k` → byte-identical to today's forced-15 output. The gating feature wires the CLI
  flag to it; this feature just threads the switchable parameter.

## Architectural choice

Add a per-card-copy redundancy penalty to the shared saturating-coverage objective. Today the
objective (both `_greedy_solve` and `_ilp_solve`) is `max Σ_{e,t} weight_e·Δg(t)·y_e^t`. The
per-element saturation `g(n)=1−(1−p)^n` already gives diminishing returns *across answers to an
element*, but copies of the **same** card are only bounded by `max_copies` and by element
saturation — never by the redundant-draw disutility the brief identifies. The 4-Hydroblast pathology
is exactly same-card stacking that element-saturation doesn't fully punish, plus the forced-15
budget (the latter is the dedicated-core feature's `τ` stop, not this feature).

New shared objective:

```
max  Σ_{e,t} weight_e·Δg(t)·y_e^t  −  Σ_c Σ_{k≥2} penalty(k)·z_c^k
```

where `z_c^k ∈ {0,1}` is "card c has ≥ k copies" (incremental copy variables, monotone-filled
exactly like the existing `y_a^t` tiers; `x_c = Σ_k z_c^k`), and `penalty(k) = REDUNDANCY_STRENGTH ·
(1 − U_redundancy(k))` with `penalty(1)=0`. The greedy uses the identical per-copy marginal:
`Σ_e weight_e·Δg(cov_e+1) − penalty(current_copies+1)`. Both solvers therefore agree.

## Implementation Units

### Unit 1 (trickiest — design first): redundancy curve + penalty primitive

**File**: `src/legacy_engine/advisory/sideboard.py`

```python
# Default redundancy curve (brief §2): utility of the k-th DRAWN copy.
_U_REDUNDANCY_DEFAULT: tuple[float, ...] = (1.0, 0.55, 0.25, 0.10)  # k=1,2,3,4; clamp ≥4 to last
# Penalty scale in coverage-value units; calibrated so the 2nd copy of a typical card competes
# with covering a fresh element. Tunable; see Risks (calibration).
_REDUNDANCY_STRENGTH: float = 0.10

def _u_redundancy(k: int, curve: tuple[float, ...] = _U_REDUNDANCY_DEFAULT) -> float:
    """Utility weight of the k-th drawn copy of a card (1.0 at k=1, decaying). k clamps to len(curve)."""

def _redundancy_penalty(k: int, *, strength: float = _REDUNDANCY_STRENGTH,
                        curve: tuple[float, ...] = _U_REDUNDANCY_DEFAULT) -> float:
    """Additive penalty for the k-th copy: strength·(1 − _u_redundancy(k)). penalty(1) == 0.0."""
```

**Notes**: pure functions, no DB — unit-testable with hand inputs ([[objective-search-split]]).
`penalty(1)` MUST be exactly 0.0 (first copy never penalized). Monotonic non-decreasing in k.

**Acceptance**:
- [ ] `_redundancy_penalty(1) == 0.0`; `penalty(k)` strictly increasing for k=2,3,4.
- [ ] `_u_redundancy(k)` clamps k>len(curve) to the last value (no IndexError at k=5).
- [ ] With `strength=0.0`, `penalty(k)==0.0 ∀k` (the no-op baseline).

### Unit 2: thread the gated `redundancy_decay` parameter

**File**: `src/legacy_engine/advisory/sideboard.py` (`recommend_sideboard`, `_build_coverage_model` or a small `SolveParams`)

Add a `redundancy_decay: bool = False` (or `redundancy_strength: float = 0.0`) parameter carried
from `recommend_sideboard` into both solvers. Default OFF → `penalty(k)=0` → byte-identical. Do NOT
add a CLI flag here (the gating feature owns that).

**Acceptance**:
- [ ] Default call path produces byte-identical `SideboardPackage` to pre-change (existing tests green).
- [ ] Parameter reaches both `_greedy_solve` and `_ilp_solve`.

### Unit 3: greedy integration

**File**: `src/legacy_engine/advisory/sideboard.py` (`_greedy_solve`)

In the per-card gain loop, subtract `_redundancy_penalty(current_copies + 1, strength=...)` from the
card's coverage marginal before the argmax. A copy whose coverage gain < its penalty has negative
marginal and is not picked (a soft same-card cap; the hard `τ` natural-budget stop is dedicated-core).

**Acceptance**:
- [ ] With decay on, a field dominated by one tag stops stacking the top hoser past ~2-3 copies and
      spreads to the next-best distinct answer (the 4/4/4 → balanced fix), on a hand-built model.
- [ ] With decay off, greedy output identical to today on the same model.

### Unit 4: ILP integration

**File**: `src/legacy_engine/advisory/sideboard.py` (`_ilp_solve`)

Introduce incremental copy variables `z_c^k ∈ {0,1}` (k=1..max_copies) with `x_c = Σ_k z_c^k` and
monotone fill `z_c^k ≥ z_c^{k+1}` (mirrors the `y_a^t` pattern; the existing decreasing-coefficient
trick keeps fill ordered). Subtract `Σ_c Σ_{k≥2} penalty(k)·z_c^k` from the objective. When
`strength==0`, omit the z-vars/penalty entirely so the model is byte-identical to today.

**Notes**: this is the unit with linearization risk — verify the z-monotone constraint and that the
penalty competes correctly with `weight_e·Δg`. Keep `_ILP_T_CAP` behavior unchanged.

**Acceptance**:
- [ ] ILP and greedy agree (same card multiset) on a hand-built model with decay on (consistency).
- [ ] With decay off, ILP output identical to today.
- [ ] CBC still returns Optimal at the realistic candidate/budget scale.

## Implementation Order
1. **Unit 1** — primitives first; everything calibrates against them.
2. **Unit 2** — thread the gated parameter (no-op default) so the baseline path is provably unchanged.
3. **Unit 3** — greedy integration (the explainable trace; easiest to validate the spread behavior).
4. **Unit 4** — ILP integration (hardest; validate it agrees with greedy).

## Testing
### Unit tests: `tests/test_sideboard.py`
- `_u_redundancy` / `_redundancy_penalty`: penalty(1)==0, monotonic, k-clamp, strength=0 no-op (Unit 1 ACs).
- Greedy spread: hand-built `CoverageModel` with one dominant tag + a top hoser at `max_copies=4`;
  decay-off picks 4 of it, decay-on stops at ~2-3 and spreads — assert the copy counts (Unit 3).
- ILP/greedy consistency on the same hand-built model with decay on (Unit 4).
- **Byte-identical regression**: the whole existing `TestRecommendSideboard` / swing-path suite must
  stay green with the default (decay off) — this is the gated-additive guarantee.

### Integration
- `recommend_sideboard(..., redundancy_decay=True)` on a `make_rounds_corpus`-style hermetic DB:
  the Boulder-like over-concentration no longer produces 4/4/4. (Full <15 + curve is the
  downstream features; here just assert the copy spread changes.)

## Risks
- **Penalty calibration (`_REDUNDANCY_STRENGTH`)** — if too small, no effect (still pads); too large,
  it suppresses legitimate 3-4-of dedicated swaps the brief says are correct. **Fallback**: expose it
  as the tunable it already is; default conservative; the dedicated-core feature's `τ` is the real
  budget control, so this only needs to *shape* copies, not gate them. Pin the default against a
  hand-built model where a 3-of dedicated swap survives but a 4th overlapping copy doesn't.
- **ILP linearization (Unit 4)** — `z_c^k` monotone-fill + penalty could mis-rank vs greedy.
  **Fallback**: greedy is already the explainable trace and a valid solver; if the ILP form proves
  unstable, gate decay to the greedy path and treat ILP-with-decay as a follow-up (note it loudly).
- **Submodularity** — coverage(g) is submodular; subtracting a per-copy penalty that is
  non-decreasing in k keeps each card's marginal non-increasing → greedy's 1−1/e intent holds.
  Verify no card's marginal *increases* with copies.

## Implementation notes
- Files changed: `src/legacy_engine/advisory/sideboard.py` (Unit 1 primitives `_u_redundancy` + `_redundancy_penalty` + constants `_U_REDUNDANCY_DEFAULT`/`_REDUNDANCY_STRENGTH`; Unit 2 `redundancy_strength` param threaded `recommend_sideboard` → both solvers; Unit 3 greedy subtracts the per-copy penalty; Unit 4 ILP adds incremental `z_c^k` copy vars + monotone fill + negative penalty terms).
- Tests added: `tests/test_sideboard.py::TestRedundancyDecay` (9 tests — penalty primitives, greedy stacks-off/spreads-on, ILP/greedy consistency with decay, ILP byte-identical when off, recommend_sideboard integration).
- Discrepancies from design: none. Built exactly to the design's additive-penalty form.
- Verification: full suite 2219 passed (243 in test_sideboard.py, incl. the existing suite byte-identical with decay off); `ruff check` introduces zero new errors in src/ (sideboard.py clean) or the new test class.
- Gated-additive confirmed: `redundancy_strength=0.0` (default) → `penalty(k)=0 ∀k`, ILP omits the z-vars entirely → byte-identical to the forced-15 baseline.
- Adjacent issues parked: none. (Noted but NOT fixed: pre-existing ruff debt in tests/test_sideboard.py — unused imports / E402 / F841 `con` — predates this work; CI lints src/ only and is non-blocking.)
- Downstream: the dedicated-core feature adds the τ natural-budget stop on top of these per-copy marginals; the gating feature wires a CLI flag to `redundancy_strength`.
