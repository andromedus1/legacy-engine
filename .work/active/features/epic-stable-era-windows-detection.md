---
id: epic-stable-era-windows-detection
kind: feature
stage: done
tags: [analytics, methodology]
parent: epic-stable-era-windows
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Per-entity disturbance detection engine

## Brief

The pure-analytics core: given the corpus, derive each entity's (parent archetype, and camp where
sample permits) detected era boundaries. Builds per-entity weekly (or pooled-bucket) series — share
of field, flex-band composition vectors, per-card inclusion — and runs the brief's signal-typed
detector ensemble: S1 presence rules for ban cliffs / release ramps (threshold crossings with
consecutive-bucket confirmation), S2 kernel/energy change-point detection on composition vectors
(PELT + RBF/cosine cost, or E-Divisive with permutation p-values), S3 share-shift and S4 win-rate
corroboration via exact Beta-Binomial likelihoods (in-project conjugate BOCPD recursion — no
existing Python package covers count/proportion likelihoods). Candidate boundaries merge across
signals (±1-2 week tolerance), pass fleet-level false-positive control (Benjamini-Hochberg FDR over
per-boundary p-values + a minimum-segment floor expressed in DECKS, tied to the evolving-tier
floor of 30), and yield `stable_since(entity)` = the last accepted boundary. Adds the `ruptures`
dependency. Per-entity adaptivity: bucket width and signal subset scale with weekly density
(camps below the density floor inherit their parent's boundaries).

This feature does NOT persist anything, attribute triggers, or touch any consumer — output is
pure data structures. Calibration IS in scope: the penalty/threshold operating point is chosen by
sweeping against the labeled disturbance ledger (12 BAN_EVENTS × affectedness cases, the
Candelabra/Tron cliff, the Flow State three-archetype adoption step, and known stable non-event
stretches) and the chosen operating point ships as a pinned test fixture. Never trust CPD
defaults — the brief's benchmark evidence says defaults lose to a zero-detector.

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: foundation feature — everything else depends on its detected boundaries.

## Inherited design decisions

- Self-heal gate — auto-truncate, labeled: the detector's accepted boundaries are authoritative
  even when unattributed; design the acceptance bar (FDR + floors) knowing its output truncates
  windows without human review.
- Known ban/release dates are labels/priors, never the source of truth (epic Brief).

## Research briefs

- `docs/briefs/change-point-detection.md` (load-bearing; attested) — §1 data shapes + ground
  truths, §2 signal taxonomy, §3 method selection, §4 FP control, §5 calibration ledger, §6
  small-sample playbook.
- `docs/briefs/subarchetype-discovery.md` — the flex-band representation reused for composition
  vectors.

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/ module map (affectedness.py is the mechanism being
  generalized; discovery.py owns the flex-band builders).
- Patterns: objective-search-split (heavy DB scan once → pure detector loop, unit-testable
  without DB); confidence-metadata (tier floors); closed-vocabulary fail-fast (signal/trigger
  enums).

## Design decisions

Resolved with judgment under autopilot (2026-07-11); cross-model advisory skipped — the attested
brief + epic `--only-questions` pass already pin the directional choices; Codex runs at epic
completion per the standing pipeline.

- **Package, not single module**: `analytics/eras/` mirrors the `analytics/players/` package
  precedent — `series.py` / `bocpd.py` / `detect.py` / `ensemble.py`. The four responsibilities
  have distinct test surfaces and detect/ensemble must be importable without DuckDB.
- **Entity vocabulary**: parents = every `decks.archetype` with ≥100 corpus decks (established
  floor — below that, eras aren't decidable and full history stands); camps = `"{parent}
  [{variant}]"` labels (the matchup camp-label convention) where the camp clears the density
  floor, else the camp inherits its parent's boundaries.
- **Bucket width by density**: weekly when the entity's median weekly deck count ≥10; 2-week when
  ≥5; else 4-week. The trailing incomplete bucket is dropped from rate/composition signals and
  retained (flagged) for presence rules only.
- **S2 significance**: candidate boundaries from ruptures PELT/KernelCPD (cosine kernel on
  per-bucket flex-band inclusion vectors; penalty from the calibration fixture), then a
  per-boundary segment-permutation p-value (permute bucket order across the two adjacent
  segments, compare cost gain) so every candidate carries a p-value for fleet BH-FDR — ruptures
  emits none natively (brief §4 requires per-detection p-values).
- **BOCPD is the online half only**: `bocpd.py` (Beta-Binomial conjugate recursion, in-project —
  no Python package covers it) feeds the era-ledger feature's drift alarm; offline stable_since
  derivation uses S1 presence rules + S2 composition + S3 share (same permutation scheme on the
  share series) + S4 win-rate corroboration.
- **Acceptance bar**: BH-FDR at α=0.05 across ALL candidate boundaries fleet-wide per run; a
  boundary is additionally rejected unless the new era already contains ≥30 subject decks (the
  evolving-tier floor, expressed in decks not weeks). stable_since = date of the last accepted
  boundary; no accepted boundary → None (full history — valid_since semantics preserved).
- **Operating-point constants live in the modules and are pinned by calibration tests** against
  the frozen ledger fixtures (Tron cliff, Flow State step, stable non-events, null fleet); a
  constant change that breaks recall/false-alarm targets fails the suite.

## Architectural choice

Options considered: (a) one `analytics/eras.py` module (affectedness.py precedent) — rejected,
four detectors + series builders + ensemble in one file makes the pure/DB seam and the test
surfaces mushy; (b) bolt detectors onto `analytics/discovery.py` — rejected, discovery clusters
decks within a window, eras segments windows over time; shared flex-band REPRESENTATION is reused
via constants/helpers, not by merging modules; (c) `analytics/eras/` package with a hard
objective-search-split: `series.py` owns the single batched DuckDB scan producing plain
dataclasses, everything downstream is pure numpy — chosen. Detection must be unit-testable on
hand-built series (the calibration fixtures ARE hand-frozen series), and the players/ package is
the in-repo precedent for a multi-file analytics subsystem.

## Implementation Units

### Unit 1: Entity series builder

**File**: `src/legacy_engine/analytics/eras/series.py`
**Story**: `epic-stable-era-windows-detection-series`

```python
@dataclass(frozen=True)
class Bucket:
    start: str                    # ISO date, bucket start (Monday)
    complete: bool                # False for the trailing partial bucket
    decks: int                    # entity decks in bucket
    field_decks: int              # all labeled decks in bucket (share denominator)
    wins: int                     # entity match wins in bucket (marginal, rounds-derived)
    losses: int
    card_incl: dict[str, int]     # flex-band card -> decks running it (inclusion counts)

@dataclass(frozen=True)
class EntitySeries:
    entity: str                   # "Doomsday" or "Dimir Tempo [Barrowgoyf]"
    parent: str                   # == entity for parents
    bucket_weeks: int             # 1 | 2 | 4 (density-adaptive)
    flex_cards: tuple[str, ...]   # the entity's flex band (10-95% inclusion over its pool)
    buckets: tuple[Bucket, ...]   # chronological

def build_entity_series(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    min_entity_decks: int = 100,
) -> dict[str, EntitySeries]: ...
```

**Implementation Notes**:
- One batched scan per table (decks×tournaments, deck_cards, rounds), then pure Python bucketing —
  objective-search-split; no per-entity queries.
- Flex band per entity over its full pool, same 0.10/0.95 thresholds as
  `discovery.build_feature_matrix` (import the constants or mirror them as named constants with a
  cross-reference comment).
- Camp entities read `decks.variant`; only variants with ≥30 total decks get a series.
- Trailing bucket: `complete=False` when the corpus max date < bucket end − 1 day.

**Acceptance Criteria**:
- [ ] Dimir Tempo weekly series matches hand-computed corpus numbers for 3 spot weeks
- [ ] Entity below `min_entity_decks` absent from output
- [ ] Rank-25-density entity gets `bucket_weeks > 1`
- [ ] Trailing partial bucket has `complete=False`
- [ ] Hermetic: runs against a tmp DB built by the existing `_build_*_db` test builders

### Unit 2: Beta-Binomial BOCPD recursion

**File**: `src/legacy_engine/analytics/eras/bocpd.py`
**Story**: `epic-stable-era-windows-detection-bocpd`

```python
@dataclass(frozen=True)
class BocpdResult:
    p_change: np.ndarray          # per-bucket posterior P(run length resets)
    map_run_length: np.ndarray    # per-bucket MAP run length

def beta_binomial_bocpd(
    successes: np.ndarray,        # int, per bucket (entity decks / wins)
    trials: np.ndarray,           # int, per bucket (field decks / matches)
    *,
    hazard_lambda: float = 25.0,  # constant hazard 1/25 buckets
    prior_a: float = 1.0,
    prior_b: float = 1.0,
) -> BocpdResult: ...
```

**Implementation Notes**:
- Adams–MacKay recursion with Beta–Binomial predictive; conjugate hyperparameter bookkeeping per
  run-length hypothesis; log-space accumulation; truncate run-length distribution below 1e-9 mass.
- Pure numpy/scipy; zero-trial buckets pass through with prior predictive (missing-week safe).

**Acceptance Criteria**:
- [ ] On a synthetic step (p 0.05→0.30 at t=20, n=40/bucket) `p_change` peaks within ±1 bucket
- [ ] On stationary noise, max `p_change` stays below the alarm bar
- [ ] Zero-trial buckets neither crash nor spike `p_change`
- [ ] Deterministic (no RNG)

### Unit 3: Signal detectors

**File**: `src/legacy_engine/analytics/eras/detect.py`
**Story**: `epic-stable-era-windows-detection-detectors`

```python
SIGNAL_TYPES = frozenset({"presence-vanish", "presence-adopt", "composition", "share", "winrate"})

@dataclass(frozen=True)
class CandidateBoundary:
    entity: str
    date: str                     # ISO, first bucket of the new era
    signal: str                   # ∈ SIGNAL_TYPES (fail-fast on unknown)
    magnitude: float              # signal-specific effect size
    pvalue: float                 # permutation p (S1 uses exact two-proportion p)
    evidence: str                 # human line: "Flow State 0%→95% (n 15→19)"
    trigger_card: str | None     # S1 only

def detect_presence(s: EntitySeries) -> list[CandidateBoundary]: ...
def detect_composition(s: EntitySeries, *, pen: float = _PELT_PEN, n_perm: int = 199) -> list[CandidateBoundary]: ...
def detect_share(s: EntitySeries, *, n_perm: int = 199) -> list[CandidateBoundary]: ...
def corroborate_winrate(s: EntitySeries, cands: list[CandidateBoundary]) -> list[CandidateBoundary]: ...
```

**Implementation Notes**:
- S1: per flex card, inclusion fraction crossing (≥0.25 → <0.05 = vanish; <0.05 → ≥0.25 = adopt);
  one-bucket confirm when the jump ≥0.50, else two consecutive buckets; exact binomial
  two-proportion p-value; trigger card recorded.
- S2: ruptures `KernelCPD(kernel="cosine")`/`Pelt` on per-bucket inclusion-fraction vectors
  (min_size from the deck-floor, jump=1), then segment-permutation p per boundary. Buckets with
  <10 entity decks are pooled upstream by series.py, so vectors are estimable.
- S3: same permutation scheme on the share series (arcsine-transformed for the L2 cost).
- S4 never creates boundaries — it up/down-weights existing candidates' evidence lines only.
- RNG: `numpy.random.default_rng(seed)` with seed threaded from caller; deterministic given seed.

**Acceptance Criteria**:
- [ ] Flow State fixture (frozen Doomsday/Izzet/Dimir weekly tables): S1 adopt fires week
      2026-04-20 ±1 bucket on all three, trigger_card == "Flow State"
- [ ] Tron fixture: S1 vanish + S3 share collapse both fire at 2026-06-22/29 ±1 bucket
- [ ] Stable non-event fixture (Lands mid-regime): zero candidates at operating point
- [ ] Unknown signal string raises ValueError naming token and sorted allowed set

### Unit 4: Ensemble, FDR, floors, stable_since

**File**: `src/legacy_engine/analytics/eras/ensemble.py`
**Story**: `epic-stable-era-windows-detection-ensemble`

```python
@dataclass(frozen=True)
class EraBoundary:
    date: str
    signals: tuple[CandidateBoundary, ...]   # merged evidence
    pvalue: float                            # min component p (pre-BH), bh_accepted: bool

@dataclass(frozen=True)
class EntityEras:
    entity: str
    stable_since: str | None                 # None = full history
    boundaries: tuple[EraBoundary, ...]
    inherited_from_parent: bool              # camps below density floor

def derive_eras(
    series: dict[str, EntitySeries],
    candidates: list[CandidateBoundary],
    *,
    alpha: float = 0.05,
    merge_tolerance_buckets: int = 2,
    min_new_era_decks: int = 30,
) -> dict[str, EntityEras]: ...
```

**Implementation Notes**:
- Merge candidates within tolerance per entity (multi-signal boundaries strengthen: keep min p,
  concat evidence). BH-FDR across the merged fleet-wide list. Then the deck floor: reject a
  surviving boundary if the entity has <`min_new_era_decks` decks after it.
- Camp entities without their own series (density floor) copy the parent's accepted boundaries
  with `inherited_from_parent=True`.
- Pure; no DB, no persistence (the era-ledger feature owns storage/attribution).

**Acceptance Criteria**:
- [ ] Null fleet (100 synthetic stationary entities): 0 accepted boundaries at α=0.05
- [ ] Tron fixture boundary survives FDR + floor; a p=0.04 singleton among 99 nulls does not
- [ ] Thin post-break era (<30 decks) → boundary rejected, stable_since unchanged
- [ ] Camp below floor inherits parent boundaries with flag

### Unit 5: Dependency + calibration fixtures

**File**: `pyproject.toml` (+ `tests/analytics/eras/` fixtures)
**Story**: `epic-stable-era-windows-detection-ensemble` (same story)

Add `ruptures>=1.1` to core dependencies. Freeze the ledger fixtures as literal data in
`tests/analytics/eras/conftest.py`: the Tron weekly counts, the three Flow State weekly
inclusion tables (real corpus numbers), a stable stretch, and a null-fleet generator (seeded).

**Acceptance Criteria**:
- [ ] `uv pip install -e .` (CI path) resolves ruptures; import is lazy inside detect.py
- [ ] Calibration suite pins the operating point at the measured WINDOW EDGES (the safe windows are wide, so ±50% is inside them): guards assert detection is lost beyond the measured upper edges of `_PELT_PEN` and `_SHARE_PEN`

---

## Implementation Order

1. Unit 1 (series) and Unit 2 (bocpd) — independent, parallelizable
2. Unit 3 (detectors) — needs series shapes; trickiest unit (S2 permutation significance),
   design-first target
3. Unit 4+5 (ensemble + calibration) — needs detectors; the calibration fixtures close the loop

## Testing

- `tests/analytics/eras/test_series.py` — hermetic tmp-DB builder (existing conftest pattern),
  spot-week assertions, density bucketing, partial-bucket flag.
- `tests/analytics/eras/test_bocpd.py` — synthetic step/stationary/zero-trial cases.
- `tests/analytics/eras/test_detect.py` — frozen real fixtures (Flow State ×3, Tron), stable
  non-event, determinism-given-seed, closed-vocab fail-fast.
- `tests/analytics/eras/test_ensemble.py` — null-fleet FDR, merge tolerance, deck floor, camp
  inheritance.
- Integration seam: one test drives `build_entity_series` → detectors → `derive_eras` end-to-end
  on the tmp DB and asserts a stable_since dict shape consumable by the era-ledger feature.

## Risks

- **S2 permutation p-values on short series may be coarse** (199 perms, ~30-80 buckets) —
  **Fallback**: S1+S3 alone recover both ground-truth cases; S2 can ship conservative (higher
  pen) and loosen later.
- **Operating-point calibration may not satisfy both recall (ledger hits) and null-fleet zero**
  — **Fallback**: per-signal α split (S1 exact tests are cheap and sharp; spend FDR budget
  there), documented in the calibration test.
- **ruptures API drift** — pinned `>=1.1,<2` and lazy import keeps failures loud and local.

## Implementation summary (2026-07-11)

All 4 stories implemented on `feature/stable-era-detection` (commits ae0f643, dcdcb70, 6bfa906,
095f10b), suite 2809 passed + 1 xfail, ruff clean on the new package. Notable as-built deviations
(each documented in the story bodies + module docstrings):
- bocpd: literal P(run_length=0) is provably constant under constant hazard; `p_change` is
  P(run_length <= 1) with full derivation in the docstring.
- detect: S3 `_SHARE_MIN_SIZE=2` (min_size=3 provably cannot date a cliff in the last two
  complete buckets — the Candelabra case); operating points pinned by the frozen fixtures
  (_PELT_PEN=0.5, _SHARE_PEN=0.003).
- ensemble: `floor_rejected` audit field added; Tron stable_since honestly None at this corpus
  edge (confirmation asymmetry — drift alarm is the immediate-flag path); Dimir carries a real
  second accepted boundary (2026-05-11 share settling).
Local venv note: dep re-resolution bumped numpy to 2.5 breaking the optional umap smoke test
(numba cap); pinned back to numpy<2.5 locally; CI unaffected (umap not installed there).

## Review (2026-07-11, fresh-context deep review)

Verdict APPROVE (no Critical/High). All 5 findings fixed in-tree post-review:
- S3 magnitude/evidence now segment-level means (was adjacent-bucket 0.0 no-op on the cliff).
- Calibration AC replaced by measured window-edge guard tests (±50% was inside the safe window).
- Camp max-rule now appends the parent's winning boundary so stable_since always resolves to a
  boundary present in the entity's own tuple (explain-surface contract).
- NEW stochastic null-fleet test exposed a real anti-conservatism: the permutation null now
  re-MAXIMIZES gain over admissible splits per permutation (selection correction), and S1
  regime checks pool ≥4 buckets / ≥40 decks per side — fleet acceptances on stationary noise:
  11 → 0. Consequence: Dimir's marginal 2026-05-11 settling boundary no longer clears BH
  (recorded, rejected); Dimir stable_since = 2026-04-20 adoption.
- Tron hold-back note corrected: only the p-value defense fires (boundary placement leaves 80
  decks, floor untouched).
