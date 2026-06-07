---
id: epic-advisory-output-honesty-whattoplay-honesty
kind: feature
stage: implementing
tags: [advisory]
parent: epic-advisory-output-honesty
depends_on: [epic-advisory-output-honesty-positioning-coverage]
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Honest "What to Play" Output

## Brief

Fix two ways the "what to play" advisor misleads or omits. First, `best_deck_vs_best_call` uses hard
cutoffs (spread_hi=0.02, mean_hi=0.52) that create cliff effects — Death & Taxes was the best field
pick yet got labeled "neither" because it sat the wrong side of a threshold. Second, `whattoplay`
prints proactivity, vulnerability tags, and the best-deck-call but omits the positioning `S` (expected
win rate) — the single number a user most wants from the advisor.

Covers: replacing the best-call threshold cliffs with a continuous/gradient signal (so near-boundary
decks aren't mislabeled); surfacing the positioning S in the whattoplay output. The S surfaced here is
the **coverage-aware S** from the positioning-coverage feature, so the advisor never prints an
imputation-prior number without its coverage context.

Does NOT cover: the positioning math/coverage itself (that's the dependency); sideboard output.

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: consumer of `positioning-coverage` (surfaces its coverage-aware S).

## Inherited design decisions
- **Surface the coverage-aware S** from `epic-advisory-output-honesty-positioning-coverage` — do not
  recompute a bare full-field S in the whattoplay surface.
- Best-call gradient replaces the hard spread_hi/mean_hi cutoffs; near-threshold decks get a
  continuous signal rather than a binary "neither".

## Foundation references
- `docs/SPEC.md` — Pillar 4 "What to play" advisor; "no unlabeled headline numbers" NFR
- `src/legacy_engine/advisory/whattoplay.py`, `advisory/report.py`, `cli.py`

## Design decisions
- **Gradient form**: keep the `BEST_DECK`/`BEST_CALL`/`neither` label strings (backward-compatible with
  consumers + existing test assertions), but **drop the `variance > spread_hi` gate on `BEST_CALL`**
  (the cliff that mislabeled D&T) and **add continuous `best_deck_score` + `best_call_score` ∈ [0,1]**
  rendered beside the label so a borderline 0.515 reads as borderline, not a binary fail.
- **Robustness score**: `best_deck_score = clamp(unweighted_mean − √spread_variance, 0, 1)` — the
  robust floor (rewards decks whose worse matchups are still okay). `best_call_score = field_weighted_mean`.
- **Surface S**: `advise whattoplay` always computes `positioning_score` and renders the coverage-aware
  S, reusing the foundation feature's restricted / not-computable presentation (so whattoplay never
  prints a bare imputation-prior S).

## Architectural choice

The best-call fix is a **minimal, backward-compatible widening** (Phase 5a alternatives: (A) keep
labels + add scores + drop the BEST_CALL variance gate; (B) fully continuous lean descriptor replacing
the labels; (C) just lower the thresholds). **Chosen: A.** It fixes the exact reported cliff (D&T low-
variance + field-favored → was `neither`, now `BEST_CALL`) without churning the label vocabulary that
`report.py`/`cli.py`/`test_whattoplay.py` depend on, and the added continuous scores deliver the
"gradient" so near-threshold decks are legible. B was rejected as needless test/consumer churn for this
epic; C doesn't remove the cliff, just moves it. Surfacing S reuses the already-honest
`positioning_score` (no new positioning logic) — pure consumer wiring, per SSOT.

## Implementation Units

### Unit 1: best-call gradient — scores + de-cliffed label
**File**: `src/legacy_engine/advisory/whattoplay.py`

```python
@dataclass
class BestDeckCall:
    archetype: str
    label: str                      # "BEST_DECK" | "BEST_CALL" | "neither" (unchanged vocabulary)
    spread_variance: float
    field_weighted_mean: float
    unweighted_mean: float
    best_deck_score: float = 0.0    # NEW: clamp(unweighted_mean − √variance, 0, 1) — robust floor
    best_call_score: float = 0.0    # NEW: field_weighted_mean — good-vs-THIS-field
```

**Implementation Notes**:
- Label logic (removes the BEST_CALL variance cliff):
  ```python
  if variance <= spread_hi and unweighted_mean >= mean_hi:
      label = "BEST_DECK"
  elif field_weighted_mean >= mean_hi:      # was: variance > spread_hi AND field_weighted_mean >= mean_hi
      label = "BEST_CALL"
  else:
      label = "neither"
  ```
- `best_deck_score = max(0.0, min(1.0, unweighted_mean - math.sqrt(variance)))`; `best_call_score = field_weighted_mean`.
- Both early-return paths (missing archetype, no qualifying cells) set the two scores to `0.0`.

**Acceptance Criteria**:
- [ ] Existing labels preserved: low-var+high-mean → `BEST_DECK`; high-var+high-field-mean → `BEST_CALL`; low-mean → `neither`; n<30-only row → `neither`.
- [ ] **Cliff fixed**: low-variance (≤ spread_hi) + `field_weighted_mean ≥ mean_hi` + `unweighted_mean < mean_hi` → `BEST_CALL` (was `neither`).
- [ ] `best_deck_score` ∈ [0,1] equals `unweighted_mean − √variance` clamped; a spiky deck scores below a flat deck of equal mean.
- [ ] `best_call_score == field_weighted_mean`.

---

### Unit 2: render best-call scores
**File**: `src/legacy_engine/advisory/report.py` (`_render_whattoplay`, audit line)

**Implementation Notes**:
- Best-deck-call render line gains the two scores:
  `Best-deck-call: {label}  (best_deck={best_deck_score:.3f}, best_call={best_call_score:.3f}, spread_var={spread_variance:.4f})`.
- Mirror into the audit line in `build_field_read_report`.

**Acceptance Criteria**:
- [ ] whattoplay output shows both continuous scores beside the label.
- [ ] `advise report` carries the same.

---

### Unit 3: surface coverage-aware positioning S in whattoplay
**File**: `src/legacy_engine/cli.py` (`advise_whattoplay`), `src/legacy_engine/advisory/report.py` (`_render_whattoplay`)

**Implementation Notes**:
- In `advise_whattoplay`, compute `pos = positioning_score(matrix, field, resolved_archetype, seed=seed)` and pass it into the `FieldReadReport` (replacing `positioning=None`). (Add a `--seed` option mirroring `advise positioning`, default per existing convention.)
- `_render_whattoplay` renders an S line at the top of the "What to play" block when `report.positioning` is present, reusing the foundation feature's presentation: `s_computable=False` → "S: not computable (no covered matchups)"; `restricted` → "S (vs covered sub-field): X (coverage Y%)"; else "S: X".
- Keep the `positioning=None` path working (renders no S line) for any caller that doesn't supply it.

**Acceptance Criteria**:
- [ ] `advise whattoplay` prints the coverage-aware positioning S (restricted/coverage-labeled, matching `advise positioning`).
- [ ] Zero-coverage archetype prints "not computable", not a fabricated S.
- [ ] `_render_whattoplay` with `positioning=None` still renders (no S line, no crash).

## Implementation Order
1. **Unit 1** (scores + label) — the domain change; others render/consume it.
2. **Unit 2** (render scores) — depends on Unit 1's new fields.
3. **Unit 3** (surface S) — independent of 1/2 but shares `_render_whattoplay`; do last to integrate cleanly.

## Testing
- `tests/test_whattoplay.py` — keep all existing label assertions green; ADD: the cliff-fix case (low-variance field-favored → `BEST_CALL`); `best_deck_score` robust-floor math (spiky vs flat at equal mean); score-on-`neither` returns 0.0.
- CLI/integration — `advise whattoplay` smoke test asserts an "S" line appears and reflects coverage labeling against a low-coverage field; `positioning=None` render path still works.

## Risks
- **Existing best-call test expectations** — the de-cliffed label could flip a borderline fixture. **Fallback**: the three documented label tests are construction-based with controlled win-rates; re-verify each still lands its intended label (BEST_DECK/BEST_CALL/neither unchanged for their constructed inputs; only the new low-variance-field-favored case changes). Add the cliff-fix case explicitly.
- **whattoplay now always runs the MC** (positioning_score) — small added cost per `advise whattoplay`. **Fallback**: it already builds the matrix + field; the MC is the same one `advise positioning` runs. Acceptable.
