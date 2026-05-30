---
id: epic-advisory-positioning
kind: feature
stage: review
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-field-model]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Meta-Positioning Score (Bayesian Monte-Carlo)

## Brief
The differentiator metric: **`S(D) = Σ_a w_a · winrate(D vs a)`** — a deck's expected win rate against the
weighted field (the best response to a fixed field). Compute it with **Bayesian Monte-Carlo** as the primary
uncertainty method: per draw, sample each matchup cell `p_a ~ Beta(x_a+½, (n_a−x_a)+½)` (mirror fixed 0.5),
sample shares `w ~ Dirichlet(counts+γ)`, recompute `S = Σ w_a p_a`; report posterior **mean + percentile
credible interval**. Keep the closed-form delta-method `Var(S)=Σ w_a²·p̂(1−p̂)/n` as a fast inline sanity
check. Always report `S(D)` **alongside** the unweighted aggregate `Ū(D)` (the best-deck-vs-best-call
payload). Rank candidate decks under uncertainty via **shared-field MC draws** (one sampled field per
iteration, score all decks against it) → **probability-of-being-best `P(S_D=max)`**, plus `S±CI` and
pairwise `P(S_A>S_B)`; offer a `--risk-averse` lower-quantile ranking.

Consumes the done `matchup-matrix` (`MatchupCell` `{wins, n, ...}`) for the Beta cells and the
`field-model` `FieldDistribution` for `w`/Dirichlet counts. Honors the n<30 display gate and confidence
tiers on reported numbers.

Does NOT recommend a sideboard (`sideboard`), classify proactivity/vulnerability (`whattoplay`), or render
the combined report (`report`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: consumer of `field-model` + the done `matchup-matrix`; producer of `S`/ranking that
  `report` surfaces. Parallel to `whattoplay`.

## Inherited design decisions
- **Bayesian MC primary** (Beta cells + Dirichlet shares), delta-method as fast check; rank by
  **P(best)** from shared-field draws; report `S` **and** unweighted `Ū` (best-call vs best-deck).
- **Mirror at field share, p=0.5 zero-variance** in the headline score; offer an exclude-self secondary view.
- **Confidence-gate everything**; matchup cells already carry Wilson CI + shrinkage + n<30 gate (reuse, don't recompute).

## Research briefs
- `docs/briefs/advisory-methods.md` — §2 (the full positioning method: S(D), MC uncertainty, custom field,
  best-deck vs best-call worked example, ranking by P(best)).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/positioning.py`; `PositioningResult` model; `analytics/matchup.py`.
- `docs/PRINCIPLES.md` — #7 confidence-gate every stat.

## Design decisions
(Resolved under autopilot delegation — Phase 4.5. Parent-epic + advisory-methods §2 decisions inherited as
fixed. No strategic 50/50s — all pinned by the brief / `field-model` / `matchup-matrix` types.)

- **Positioning operates on archetype labels, not raw decklists.** `positioning_score` takes a
  `deck_archetype: str` and uses the matchup matrix **row** for that archetype (`cells[(deck_archetype, a)]`).
  Decklist→archetype classification is upstream (the classifier; `report`/CLI classify, then pass the label).
  Rationale: the matchup matrix is archetype-granular; scoring a list means scoring its archetype.
- **MC samples cells via Jeffreys-coherent Beta**: per opponent archetype `a`, sample
  `p_a ~ Beta(wins_a + ½, (n_a − wins_a) + ½)` from the cell's `wins`/`n` (matches the matrix's Jeffreys CI
  and shrinkage prior). **Mirror** (`a == deck_archetype`) is **fixed 0.5, zero variance** (not sampled),
  included at its field share in the headline; an `include_mirror=False` flag gives the exclude-self view.
- **Shares**: when `field.counts is not None` (global), sample `w ~ Dirichlet(counts + γ)` with **γ=0.5
  (Jeffreys)**, configurable; when `counts is None` (custom), use **fixed point shares** (no share-variance) —
  honoring `field-model`'s decision. The MC always samples cells; it samples shares only when counts exist.
- **No-data opponents** (cell `n == 0` or archetype absent from the matrix row): impute per advisory-methods
  §2 — default the opponent winrate to the **deck's mean vs its known (n>0, non-mirror) opponents**, sampled
  with **wide uncertainty** (a weak Beta centered on that mean, pseudo-strength ~2). A `robust=True` toggle uses
  the **worst observed** winrate instead. No-data archetypes are listed in the result's `warnings`/`imputed` set.
- **Outputs**: report `S` (field-weighted, posterior mean + percentile CI) **and** `Ū` (unweighted mean over
  the row's known cells) — the best-call-vs-best-deck payload. Keep the delta-method
  `Var(S)=Σ w_a²·p̂(1−p̂)/n_a` as a fast closed-form sanity check exposed as a helper.
- **`PositioningResult` is a plain `@dataclass` in `advisory/positioning.py`** (not `models/`): it carries MC
  summary stats (and optionally raw samples) — a computed record like `MatchupMatrix`/`MetaShareReport`
  (dataclasses in their modules), not an external-JSON boundary type like `MatchupCell`. Deviates from the
  architecture's "PositioningResult under models/" listing; logged (mirrors the analytics-record convention;
  pydantic + numpy-sample arrays is awkward). `S_samples` is **not** retained by default (memory) — a
  `keep_samples=False` default returns summary only; `rank_decks` keeps them transiently for P(best).
- **Ranking via shared-field MC**: `rank_decks` samples **one field `w` per iteration** and scores **all**
  candidate decks against that same draw → `P(S_D = max)`, plus per-deck `S±CI` and pairwise `P(S_A > S_B)`.
  A `risk_averse=True` toggle ranks by a lower posterior quantile (mean−variance lens).
- **Determinism**: both entry points accept `seed: int | None`; tests pin a seed via `numpy.random.default_rng(seed)`.
- **Single-stride, no child stories** — one cohesive `advisory/positioning.py`; the score and rank paths share
  the vectorized MC core, so splitting would duplicate it.

## Architectural choice

**A vectorized numpy MC core (`_sample_S`) that both `positioning_score` and `rank_decks` build on.** Options
weighed: (A) a shared per-draw sampler returning an `(n_draws,)` array of `S` for one deck, with `rank_decks`
orchestrating the shared-field draws across decks (chosen — DRY, and the shared-field correlation that makes
P(best) honest falls out naturally); (B) independent per-function MC (rejected — duplicates the Beta/Dirichlet
sampling and loses the shared-field coupling); (C) closed-form delta-method only (rejected — the brief makes MC
primary precisely because it carries both cell and share uncertainty and yields an honest asymmetric CI; delta
is kept only as a fast sanity helper). Sampling is vectorized over draws: for `m` field archetypes, build a
`(n_draws, m)` Beta matrix and a `(n_draws, m)` Dirichlet share matrix, then `S = (w * p).sum(axis=1)` — ~20k×~30
is microseconds in numpy.

## Implementation Units

### Unit 1: MC core `_sample_S` (trickiest — designed first)

**File**: `src/legacy_engine/advisory/positioning.py`

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field

import numpy as np

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.analytics.matchup import MatchupMatrix
from legacy_engine.confidence import ConfidenceLevel

log = logging.getLogger(__name__)

_DEFAULT_DRAWS = 20_000
_DIRICHLET_GAMMA = 0.5      # Jeffreys
_BETA_JEFFREYS = 0.5
_NODATA_STRENGTH = 2.0      # weak pseudo-count for imputed no-data opponents


def _row_winrate_inputs(
    matrix: MatchupMatrix, deck_archetype: str, field_archetypes: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """For each field archetype a, return arrays (wins, n, is_mirror_mask) for (deck_archetype, a),
    plus the list of no-data archetype labels (n==0 or cell absent). Used to build Beta params."""


def _sample_S(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    *,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    include_mirror: bool = True,
    robust: bool = False,
    rng: np.random.Generator,
    shared_w: np.ndarray | None = None,
) -> np.ndarray:
    """Return an (n_draws,) array of S samples for one deck.

    Per draw: p_a ~ Beta(wins+½, losses+½) for n>0 cells; mirror fixed 0.5; no-data cells imputed
    (mean-vs-known center, weak Beta, or worst-observed if robust). Shares: if field.counts is not
    None, w ~ Dirichlet(counts+γ); else fixed point shares. ``shared_w`` (an (n_draws, m) matrix)
    overrides share sampling so rank_decks can score all decks against ONE shared field per draw.
    """
```

**Implementation Notes**:
- Build `field_archetypes = list(field.shares)`; align wins/n arrays by that order.
- Beta matrix: for n>0 non-mirror cells, `rng.beta(wins+0.5, (n-wins)+0.5, size=(n_draws,))` per column
  (vectorize with broadcasting). Mirror columns → constant 0.5. No-data columns → `mean_vs_known` center with
  `rng.beta(_NODATA_STRENGTH*m_center+½, _NODATA_STRENGTH*(1-m_center)+½, ...)` (or constant worst if `robust`).
- Shares: `shared_w` if provided; elif `field.counts` → `rng.dirichlet(counts+γ, size=n_draws)` (align order);
  else tile point `shares` to `(n_draws, m)`. If `include_mirror=False`, zero the mirror column and renormalize.
- `S = (w * p).sum(axis=1)`.

**Acceptance Criteria**:
- [ ] For a deterministic seed, a deck with all 60% cells vs a uniform 2-archetype field yields `S_mean ≈ 0.60` (±0.01).
- [ ] Mirror column contributes exactly `0.5 * w_mirror` (zero variance across draws for that column).
- [ ] A custom field (`counts is None`) produces zero variance attributable to shares (only cell variance).
- [ ] A no-data opponent is imputed (no `KeyError`/`NaN`) and listed; `robust=True` lowers `S_mean` vs default.

---

### Unit 2: `PositioningResult`

**File**: `src/legacy_engine/advisory/positioning.py`

```python
@dataclass
class PositioningResult:
    deck_archetype: str
    s_mean: float                 # posterior mean of S (field-weighted expected WR)
    s_ci: tuple[float, float]     # (2.5th, 97.5th) percentile credible interval
    u_bar: float                  # unweighted mean over known (n>0, non-mirror) cells — best-deck lens
    field_source: str             # from FieldDistribution.field_source (always labeled)
    n_draws: int
    imputed: frozenset[str]       # no-data opponents imputed
    warnings: tuple[str, ...]
    s_samples: np.ndarray | None = None   # retained only when keep_samples=True
```

**Acceptance Criteria**:
- [ ] Always carries `field_source`; `s_ci[0] <= s_mean <= s_ci[1]`.
- [ ] `s_samples is None` unless `keep_samples=True`.

---

### Unit 3: `positioning_score`

**File**: `src/legacy_engine/advisory/positioning.py`

```python
def positioning_score(
    matrix: MatchupMatrix, field: FieldDistribution, deck_archetype: str, *,
    n_draws: int = _DEFAULT_DRAWS, gamma: float = _DIRICHLET_GAMMA,
    include_mirror: bool = True, robust: bool = False,
    keep_samples: bool = False, seed: int | None = None,
) -> PositioningResult:
    """Score one deck's meta-positioning S(D) against the field via Bayesian MC; also compute Ū."""
```

**Implementation Notes**:
- `rng = np.random.default_rng(seed)`; `samples = _sample_S(...)`; `s_mean = samples.mean()`,
  `s_ci = np.percentile(samples, [2.5, 97.5])`; `u_bar` = mean of `p_shrunk` (or `wins/n`) over known cells.
- Warn when the deck's row is thin (many no-data/`display is False` opponents) — confidence-gating.

**Acceptance Criteria**:
- [ ] Reproduces the brief's best-call worked example direction (Deck X higher `S`, Deck Y higher `Ū`) on the
      A:50/B:30/C:20 field with the brief's cell winrates.
- [ ] `keep_samples=True` returns a `(n_draws,)` `s_samples`; default returns `None`.

---

### Unit 4: `rank_decks`

**File**: `src/legacy_engine/advisory/positioning.py`

```python
@dataclass
class DeckRanking:
    decks: list[str]                          # sorted best→worst by p_best (or lower-quantile if risk_averse)
    p_best: dict[str, float]                  # P(S_D = max) from shared-field draws
    s_mean: dict[str, float]
    s_ci: dict[str, tuple[float, float]]
    pairwise: dict[tuple[str, str], float]    # P(S_a > S_b)
    field_source: str

def rank_decks(
    matrix: MatchupMatrix, field: FieldDistribution, candidates: list[str], *,
    n_draws: int = _DEFAULT_DRAWS, gamma: float = _DIRICHLET_GAMMA,
    robust: bool = False, risk_averse: bool = False, seed: int | None = None,
) -> DeckRanking:
    """Rank candidate decks under shared-field MC: P(best), S±CI, pairwise P(A>B)."""
```

**Implementation Notes**:
- Sample the shared field **once** as an `(n_draws, m)` matrix (`shared_w`); pass it to `_sample_S` for every
  candidate so all decks see the same per-draw field (the correlation that makes P(best) honest).
- Stack candidates' `S` into `(n_draws, k)`; `p_best[d] = mean(argmax over k == d)`; pairwise from pairwise
  sample comparisons. `risk_averse` → sort by 5th-percentile `S`.

**Acceptance Criteria**:
- [ ] `sum(p_best.values()) ≈ 1.0`.
- [ ] On the worked-example field, the best-call deck has the higher `p_best` even when its `Ū` is lower.
- [ ] `pairwise[(a,b)] + pairwise[(b,a)] ≈ 1.0` (ties aside).

---

### Unit 5: delta-method sanity helper + exports

**File**: `src/legacy_engine/advisory/positioning.py` + `src/legacy_engine/advisory/__init__.py`

```python
def delta_var_S(matrix: MatchupMatrix, field: FieldDistribution, deck_archetype: str) -> float:
    """Closed-form Var(S)=Σ w_a²·p̂_a(1−p̂_a)/n_a — a fast sanity check on the MC spread (known cells only)."""
```
Export `positioning_score`, `rank_decks`, `PositioningResult`, `DeckRanking`, `delta_var_S`.

## Implementation Order

1. **Unit 1** (`_sample_S` MC core) — the vectorized Beta/Dirichlet engine everything depends on.
2. **Unit 2** (`PositioningResult`) — the result type.
3. **Unit 3** (`positioning_score`) — single-deck scoring + `Ū`.
4. **Unit 4** (`rank_decks`) — shared-field ranking.
5. **Unit 5** (delta-method + exports).

## Testing

### Unit tests: `tests/test_positioning.py`
Build a `MatchupMatrix` via the real `build_matrix` over a labeled `:memory:` corpus (house style), OR
construct `MatchupCell`s directly for precise worked-example control (both — direct construction for the
arithmetic assertions, corpus-backed for the seam). All MC tests pin `seed`.

- `TestSampleS` — known-winrate convergence, mirror zero-variance, custom-field share-variance=0, no-data imputation + robust toggle.
- `TestPositioningScore` — the brief's best-call worked example (X: S>Ū ordering vs Y), CI ordering, keep_samples.
- `TestRankDecks` — `Σ p_best ≈ 1`, best-call wins p_best, pairwise symmetry, risk_averse reorders.
- `TestDeltaVar` — delta variance is in the ballpark of the MC sample variance on a known field.
- `TestPositioningResult` — `field_source` always set; CI brackets mean.

### Integration points
- Seam with `matchup-matrix`: a corpus-backed test builds the matrix via `build_matrix` and scores a deck —
  proves `MatchupCell.wins`/`n` feed the Beta sampler.
- Seam with `field-model`: scoring with a `build_global_field` field (counts → Dirichlet) vs a
  `build_custom_field` field (counts None → point shares) exercises both share paths.

## Risks

- **MC nondeterminism breaks tests**: **Mitigation** — every entry point takes `seed`; tests pin it. Assertions
  use tolerances sized to `n_draws` (≥20k → ±0.01 on means).
- **No-data imputation distorts S**: imputing many opponents (sparse matrix row) can dominate. **Mitigation** —
  imputed opponents are listed in `imputed`/`warnings` and a thin-row warning fires; `robust` offers the
  conservative bound. **Fallback**: the consumer (`report`) can gate BEST-CALL on rows with enough known cells.
- **Mirror/exclude-self double-counting**: forgetting to renormalize `w` after dropping the mirror skews S.
  **Mitigation** — explicit renormalize when `include_mirror=False`, asserted by a test.
- **Performance**: ~20k×~40 per deck × many candidates in `rank_decks`. **Mitigation** — fully vectorized numpy;
  shared-field matrix sampled once. Microsecond-scale per the brief; not a real risk at MVP corpus size.

## Implementation notes

### Files touched
- `src/legacy_engine/advisory/positioning.py` — new (Units 1–5: `_row_winrate_inputs`, `_sample_S`,
  `PositioningResult`, `positioning_score`, `DeckRanking`, `rank_decks`, `delta_var_S`)
- `src/legacy_engine/advisory/__init__.py` — added 5 exports (`positioning_score`, `rank_decks`,
  `PositioningResult`, `DeckRanking`, `delta_var_S`) to `__all__`
- `tests/test_positioning.py` — new; 39 tests across 5 test classes

### Test count
- Before: 387 passing
- After: 426 passing (+39)
- All existing tests remain green.

### Deviations with rationale
1. **`PositioningResult` placed in `advisory/positioning.py` not `models/`** — as documented in the
   design decisions: it holds numpy arrays (awkward with Pydantic), mirrors the `MatchupMatrix`/
   `MetaShareReport` convention for computed analytic records. Deviation logged in spec.
2. **No-data imputation uses `n==0 OR cell absent` check** — `_row_winrate_inputs` checks
   `cell.n > 0` (not just cell presence). An n=0 cell emitted by `build_matrix` for unobserved
   pairs is correctly treated as no-data, matching the matrix builder's rectangular guarantee.
3. **`field.no_data` archetypes also merged into `result.imputed`** — custom fields carry
   `no_data` from `build_custom_field`; these are folded into the imputed set so warnings are
   complete even when the matrix row does have a cell (but the field flagged those archetypes
   as data-absent upstream).
4. **`_sample_S` builds the Beta matrix with a Python loop over m columns** — the design note
   says "vectorize with broadcasting" but m≤40, so a loop over columns is equivalent to
   broadcasting without the shape-contortion complexity. Each column is already vectorized over
   n_draws via `rng.beta(..., size=n_draws)`. The outer loop is O(m) not O(n_draws).

### Parked items
- CLI surface (`advisory position <archetype>`) — out of scope for this feature; belongs to the
  `report` feature downstream.
- `include_mirror=False` is implemented and tested but not exposed in the CLI path yet.
