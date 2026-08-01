---
id: epic-superarchetype-layer-aggregation
kind: feature
stage: implementing
tags: [analytics]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-clustering]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-01
---

# Random-effects pooled cluster cell — n_eff, the two gates, the intra-cluster flag

## Brief

Delivers the **estimator**: given a subject's per-member matchup tallies against the archetypes of
one cluster, produce a single pooled cell that is honest about how much evidence actually stands
behind it. The method is pinned by the brief: treat each member archetype's cell as one "study",
compute the continuity-corrected logit `y_k = log((w_k+0.5)/(n_k-w_k+0.5))` with
`v_k = 1/(w_k+0.5) + 1/(n_k-w_k+0.5)` (the correction is mandatory — 0-for-3 cells are routine),
estimate between-member variance `tau^2` by **DerSimonian-Laird** from Cochran's Q, and pool with
random-effects weights `1/(s_k^2 + tau^2)`. The estimator was chosen because it self-degrades
correctly for free rather than by a bolted-on rule: with `tau^2 = 0` (58.7% of poolable cells
measured exactly zero) its weights reduce to plain inverse variance, which for binomial cells is
close to the intuitive size-weighted pooled-counts answer, and as members disagree its weights
flatten toward equality, defusing the one-dominant-member problem before any gate is consulted.

The load-bearing integration move is **`n_eff`**, not a new tier system: define
`n_eff = 1/(Var(theta_hat) * p_bar(1-p_bar))` from the random-effects variance, clamp it to
`<= sum(n_k)`, and hand *that* to the existing `tier_for_sample()` and display gate. The brief flags
this construction as **its author's, not a sourced formula**, and states its behaviour precisely:
it returns the honest full pooled sample only when `tau^2 = 0` **and** the member rates coincide;
whenever the rates differ it sits below `sum(n_k)` even at `tau^2 = 0` (by concavity of
`p(1-p)`), and falls further as heterogeneity grows. The error direction is the safe one — `n_eff`
is never more generous than the raw pooled count — but the design must pin this behaviour in tests
rather than assume the `tau^2 = 0` case is an identity. On top sit two gates and two guards, all
thresholds calibrated
against the real corpus rather than picked round: **concentration** — effective members
`m_eff = 1/HHI >= 2.0` AND max member share <= 0.60, below which the cell is still served but
labeled `dominated by <member>` (the gate bisects the measured population: median HHI is exactly
0.500, 46% exceed it); **heterogeneity** — `I^2 <= 0.40` pool freely, `0.40-0.75` pool with a
`heterogeneous pool` note naming the spread, `> 0.75` **refuse the pooled number** and emit the
per-member split instead; a **direction/spread guard** (among members with n>=10, `max p̂ - min p̂
>= 0.25` forces the top band regardless of I²); and a **minimum-computability rule** (no
heterogeneity claim in either direction without >=2 members at n>=5). All three fire on the epic's
own motivating pair — Dimir Tempo pools to 28-14 (66.7%, n=42) against the Aluren + Show and Tell
cluster and would clear the display gate, but `m_eff` = 1.75, top share 0.69, `I^2` = 0.89 and
spread 0.52 each refuse it independently. This feature also owns the **intra-cluster** rule (sibling
matches count and carry `intra_cluster` + `intra_cluster_share`; the exact self-mirror is excluded
from the rate with its `n` reported), and the **prior strength** derivation for when the cluster
cell is used as a prior rather than a display value: moment-match a Beta to the pooled mean and
`tau^2`, `s = mu(1-mu)/tau^2_p - 1` clamped to `[5, 30]` — the ceiling deliberately equal to one
displayable cell's worth of evidence, the floor deliberately above a bare 0.5 prior.

**The honesty item that must survive out of this feature and into the UI:** `I^2` is **one-sided
evidence**. Median I² across poolable cells is exactly 0.000 and only 4.0% exceed 0.75, which reads
naively as "pooling is almost always fine" — and that reading is wrong, because Cochran's Q has low
power when units are few and small and I² depends on the precision of the units. A high value is a
reliable stop signal; a low value is **never** a certificate of exchangeability. A pooled cell that
merely *passes* the gate is still a superarchetype-sourced estimate. This must reach the label, not
only the docstring.

**Not covered here.** No DB access, no clustering, no matrix wiring, no rendering. Per
objective-search-split this is a pure kernel over hand-buildable inputs — member tallies in, one
labeled pooled cell out — which is exactly what makes the brief's worked examples reproducible as
fixtures. Where the pooled cell sits in the shrinkage chain and how it is displayed belong to
`-chain` and `-best-call-fallback`.

## Epic context

- Parent epic: `epic-superarchetype-layer`
- Position in epic: **estimator feature** — consumes `-clustering`'s membership types, produces the
  pooled-cell type + `n_eff` + gate verdicts that `-chain` wires into the matrix and
  `-best-call-fallback` renders. Pure and DB-free, so it is the feature whose correctness is
  provable in isolation.

## Inherited design decisions

From the epic's `## Strategic decisions` and `## Design decisions`. Fixed inputs:

- **Intra-cluster matches count, flagged** — never silently excluded. Self-mirror excluded from the
  rate, its `n` reported. Sibling members are NOT exempt from the concentration/heterogeneity gates.
- **`n_eff` is the only integration seam into the tier system.** Do not add a new tier vocabulary,
  do not change `tier_for_sample`'s thresholds, do not introduce a parallel display gate — compute a
  more honest argument and pass it to the existing machinery.
- **Refusal is a first-class output, with a name.** `I^2 > 0.75`, `m_eff < 2.0`, single-member
  cluster, spread-guard trip, non-computable heterogeneity — each emits a labeled reason string a
  surface can print verbatim (honest-degrade-marker), and a refused pool emits the **member split**
  (divergence-as-diagnostic), never a blended number and never a silent suppression.
- **The I² one-sidedness caveat is a deliverable, not a comment.** It travels on the pooled cell as
  structured provenance so `-best-call-fallback` can render it; a design that leaves it only in
  prose has not met the acceptance bar.
- **DerSimonian-Laird, closed form.** REML is more accurate and is explicitly deferred — DL's closed
  form is the right first move at these K. Bradley-Terry with a cluster random effect is rejected
  for v1 (a single-ability-scalar model smooths away the intransitivity the matchup matrix exists to
  expose, and replaces an auditable "here are the 42 matches" with a coefficient).
- **Prior strength is derived, not constant.** `SHRINK_STRENGTH = 15` knows nothing about cluster
  coherence; the moment-matched `[5, 30]` clamp ties strength to measured coherence. The **ceiling**
  is project-grounded — it equals `DISPLAY_GATE_N`, i.e. one displayable cell's worth of evidence.
  The **floor of 5 is uncalibrated** (the brief says so); validate it against the existing
  `SHRINK_STRENGTH = 15` before shipping and record the check.
- **Where the brief flags its own claim as author's judgment rather than sourced or measured
  (`n_eff`'s construction, the `m_eff >= 2.0` and `<= 0.60` cutoffs, the I² band *actions*, the
  spread and computability guards, the prior floor), the design carries that provenance forward** —
  those are the parameters most likely to need recalibration after dogfooding, and they should be
  named constants with the rationale at the definition site, not inline literals.

## Research briefs

- `docs/briefs/superarchetype-aggregation.md` — **primary**. §4.1/§4.2 (why not pooled raw counts —
  Simpson's-paradox reversal under unequal exposure; why not Bradley-Terry), §4.3 the recommended
  estimator with per-step formulas, §4.4 `n_eff` and the design-effect analogy, §4.5 prior strength
  from group-level variance, §5 concentration (HHI/`m_eff`, why the antitrust bands do NOT transfer,
  the measured calibration), §6 heterogeneity (Q/I², the Cochrane bands mapped onto this project's
  three-state honesty vocabulary, the two extra guards, §6.3 the worked Dimir Tempo example, §6.4
  the one-sidedness caveat), §7 intra-cluster rules.
- `docs/briefs/advisory-methods.md` — the existing shrinkage/CI conventions the pooled cell must sit
  beside without contradicting.

## Foundation references

- `docs/SPEC.md` — the confidence-gated-stats NFR and the honest-degrade NFR; the superarchetype
  capability bullet.
- `docs/ARCHITECTURE.md` — `analytics/superarchetype/` module rows; the confidence-everywhere
  convention.
- `.agents/skills/patterns/` — `two-level-empirical-bayes` (`beta_binomial_shrink_to` is the
  primitive and stays untouched; this feature supplies a `prior_mean` and a `strength`),
  `confidence-metadata`, `honest-degrade-marker`, `divergence-as-diagnostic-surface`,
  `objective-search-split`, `pytest-factory-fixtures`.
- Code to read before designing: `src/legacy_engine/confidence.py` (`tier_for_sample`),
  `src/legacy_engine/analytics/matchup.py` (`beta_binomial_shrink_to`, `wilson_or_jeffreys_ci`,
  `build_cell`, `MatchupCell` fields, `DISPLAY_GATE_N`), `src/legacy_engine/analytics/card_value.py`
  (the existing two-level EB chain this must not contradict).

## Must-resolve design inputs from the adversarial read (2026-07-31)

The brief passed its groundedness audit (68/83 SUPPORTED, **0 UNSUPPORTED**) — but three findings
land directly on this feature. Full report: `docs/briefs/superarchetype-aggregation-adversarial-read.md`.

1. **BEHAVIOR-CHANGING — the prior-strength derivation is inverted, do not implement §4.5 as written.**
   §4.5 reads `tau^2_hat = 0` as "coherent cluster" and awards the MAXIMUM prior strength (30).
   §6.4 establishes — correctly, from three quoted passages — that at these member sizes a zero mostly
   means "we cannot SEE spread", not that spread is absent. Under DerSimonian-Laird `tau^2_hat = 0`
   just means `Q <= K-1`. That event was measured on **58.7% of poolable cells**. So the derivation as
   written hands maximum prior influence to the majority of cells on the WEAKEST evidence — precisely
   the inversion the heterogeneity gate exists to prevent. Resolve at design time: gate prior strength
   on evidence sufficiency (member count and per-member n), not on `tau^2_hat = 0` alone; a zero
   computed from too few/too small members must map to LOW strength, not 30.

2. **`n_eff` does not equal `Sum(n_k)` when `tau^2_hat = 0`.** The brief's "returns Sum n_k" is false as
   written: `tau^2_hat = 0` does not imply member rates coincide, and when rates differ `n_eff` sits
   BELOW `Sum(n_k)` by concavity of `p(1-p)`. The error direction is safe (the gate is stricter than
   advertised, never more generous). Pin the real behavior in a test rather than asserting the identity.

3. **The `max member share <= 0.60` cap is ungrounded** — no source, no measurement, no stated
   calibration; the "calibrated on measured data" paragraph beneath it calibrates only `m_eff >= 2.0`.
   It is NOT decorative: at K=2 it is slack (60/40 already fails `m_eff`), but at **K>=3 it is the
   binding constraint** (60/20/20 gives `m_eff` 2.27 — passes concentration, fails only the cap).
   Ship it as a NAMED, commented calibration constant that is trivially re-tunable, and say in the
   audit output that it is a project calibration rather than a sourced threshold.

Also inherited: I2 is ONE-SIDED evidence — a high value is a reliable stop, a low value is NEVER a
certificate of exchangeability. That caveat must reach the UI, not just the code (it spans this
feature and `-best-call-fallback`; the epic's decomposition risks flag it as able to fall between them).

## Measured input from the shipped clustering layer (2026-07-31)

`epic-superarchetype-layer-clustering` shipped and was run against the real corpus. **The derived
taxonomy is more conservative than the brief's operating point, which directly narrows what this
feature can deliver — plan against these numbers, not the brief's coverage table.**

- The brief's coverage projections (opponent-pooled cells at n>=30: 4.5% at K=17 → 15.8% at K=8 →
  36.8% at K=4) were computed at **fixed height cuts**. The shipped pipeline cuts at the AU criterion
  instead, yielding **K=20 over 30 definers: 5 AU-supported multi-definer branches + 15
  au-unsupported singletons**. A singleton cluster pools nothing — it is a superarchetype of one, so
  those 15 rows get NO pooling benefit from the derived layer.
- Recompute the expected coverage gain at the ACTUAL cut before committing to gate thresholds. The
  brief's K=8 row is not the shipped configuration.
- The conservatism is in the right direction: the branches AU refuses are precisely the ones the brief
  flagged as chassis artifacts (Cephalid/Azorius 0.72, Red Stompy/Show and Tell 0.79, Grixis
  Reanimator/TES 0.88, Golgari Landfall+Smallpox 0.63). Red Stompy stays a singleton rather than
  mis-fusing — strictly better than the brief's own derived result.
- **Validated positive:** Aluren + Show and Tell recovered unprompted at AU 0.972 / BP 0.92 (`sa-001`),
  which is the pair this whole arc was motivated by. That cluster is real pooling headroom.
- **Known override candidate flagged by the clustering run:** `sa-007` pools Doomsday and TES with the
  fair Dimir decks at BP 0.39. If aggregation over that cluster produces a cell that fails the
  heterogeneity gate, the fix is a curated override in the registry (which ships empty deliberately so
  derived behaviour is observable first), not a threshold change here.
- Two one-line levers exist if coverage proves too thin in practice: `--au-min` / `--min-bp` on the
  clustering CLI, or curated entries. Prefer curated entries — they are auditable per key.

## First real-corpus pooling measurement (2026-07-31, run after clustering shipped)

Ran `superarchetype run` on the full corpus (70 clusters, 14 AU-supported multi-definer branches,
56 singletons, 4 unassigned with named reasons) and measured the ACTUAL opponent-axis pooling gain
by hand. **Temper expectations: this converts thin cells into evolving-tier leans, but on this corpus
it rarely creates a DISPLAYING cell (n>=30) that did not already exist.**

Subject `Cradle Control`, 2026 YTD, largest-member-alone → pooled-cluster:
| opponent cluster | largest member | pooled | gate after |
|---|---|---|---|
| Dimir family (sa-027) | 38.2% n=55 | 38.6% n=70 | displays (already did) |
| Delver family (sa-017) | 62.5% n=24 | 55.6% n=27 | evolving |
| Reanimator family (sa-003) | 9.1% n=11 | 12.5% n=16 | evolving |
| Stompy family (sa-001) | 40.0% n=10 | 50.0% n=20 | evolving |
| White creature (sa-024) | 57.1% n=7 | 47.8% n=23 | evolving |
| Colorless prison (sa-046) | 25.0% n=4 | 46.2% n=13 | evolving |

Subject `Aluren`: colorless prison n=3 → 12, white creature n=10 → 24, Stompy n=7 → 16.

**What this means for this feature:**
1. The multiplier is real and largest exactly where it should be — **2x to 4x on the thinnest cells**
   (n=3→12, n=4→13, n=7→23). Cells that were unmeasured or speculative become evolving-tier labeled
   leans. That IS the honesty win the epic promised.
2. But **almost nothing crosses n>=30 in this window**. Do not promise the page a new stratum of
   grounded rows; promise it labeled leans where it currently shows nothing. Re-derive the coverage
   claim on the SHIPPED taxonomy before `-best-call-fallback` writes any user-facing copy.
3. **The dilution the gates exist for is visible immediately.** Cradle vs colorless prison moves
   25.0% (n=4) → 46.2% (n=13); Aluren vs colorless prison 100% (n=3) → 50.0% (n=12). Those are large
   swings driven by adding a differently-shaped member (Tron alongside Mystic Forge). Run the
   heterogeneity and concentration gates on exactly these cells as acceptance fixtures — they are real,
   they are thin, and they are the shape that would otherwise ship a confident wrong number.
4. Combined with the singleton finding above (15 of 30 definers pool nothing), the realistic pitch for
   this arc is **"fewer blank cells and honest leans", not "the thin-data problem is solved"**.

## Architectural choice

**Chosen: one pure module `analytics/superarchetype/aggregate.py` exposing a single orchestrator over
five independently-testable helpers, taking plain per-member tallies and returning one typed result
that carries its own gate verdicts.** No DuckDB import; the caller (`-chain`) supplies tallies. This is
the objective-search-split shape the project already uses, and it is what makes the brief's worked
examples and today's real-corpus measurements usable directly as fixtures.

Options weighed:
1. *(chosen)* Pure kernel + typed result. Every gate is a pure predicate over the same inputs, so the
   headline "this pooled number is a lie" fixture is a two-line unit test.
2. *Estimator class holding config.* Rejected — the calibration constants are module-level and shared;
   a class adds lifecycle for no benefit and makes the constants harder to grep.
3. *Fold the gates into `matchup.py` cell construction.* Rejected — drags DB-shaped inputs into the
   estimator, puts superarchetype logic in a module `-chain` must edit anyway, and makes gate behaviour
   untestable without building a whole matrix.

**The result carries verdicts and never silently drops.** `aggregate_cluster_cell` always returns a
`PooledCell`; a refused pool sets `pooled_p=None` + `refused_reason` + `member_split` so the caller can
render the members. Honest-degrade, not an exception.

## Implementation Units

### Unit 1 (trickiest — build first): DL random-effects pool on continuity-corrected logits
**File**: `src/legacy_engine/analytics/superarchetype/aggregate.py`
```python
_CONTINUITY = 0.5          # calibration: Haldane-Anscombe correction for 0/n and n/n members
_TAU2_MIN_MEMBERS = 2      # below this tau^2 is not computable — never claim homogeneity

@dataclass(frozen=True)
class MemberTally:
    archetype: str
    wins: int
    n: int
    intra_cluster: bool = False   # epic decision: counts toward the cell, but flagged

@dataclass(frozen=True)
class RandomEffects:
    logit_mean: float
    tau2: float
    q: float
    df: int
    i2: float | None          # None when not computable (see _TAU2_MIN_MEMBERS)
    weights: tuple[float, ...]

def _logit_with_correction(wins: int, n: int) -> tuple[float, float]: ...
def dersimonian_laird(members: Sequence[MemberTally]) -> RandomEffects: ...
```
**Acceptance**
- [ ] Reproduces the brief's worked I² for the headline fixture to 2dp (0.89).
- [ ] A 0-win member and an n-win member both yield finite logit and finite variance.
- [ ] Single member → `tau2=0.0`, `i2=None`, `df=0` — the caller must not read that as homogeneous.
- [ ] Weights sum to 1 and flatten toward equality as `tau2` grows (assert monotone, not a fixed value).

### Unit 2: `n_eff` from the random-effects variance
```python
def effective_n(members: Sequence[MemberTally], re: RandomEffects) -> float: ...
```
**Acceptance**
- [ ] **PIN REAL BEHAVIOUR, NOT THE BRIEF'S IDENTITY.** `tau2 == 0` AND all member rates equal →
      `n_eff == sum(n)`. `tau2 == 0` with rates DIFFERING → `n_eff < sum(n)` strictly. Assert both; do
      not assert the false identity.
- [ ] `n_eff` non-increasing in `tau2` (property test over a grid).
- [ ] `n_eff <= sum(n)` always.

### Unit 3: concentration gate
```python
_MEFF_MIN = 2.0            # calibration: 1/HHI, the "effective number of members"
_MAX_MEMBER_SHARE = 0.60   # CALIBRATION, NOT SOURCED — binding at K>=3 (60/20/20 -> m_eff 2.27)

def concentration(members: Sequence[MemberTally]) -> Concentration: ...
```
`Concentration` carries `hhi`, `m_eff`, `top_share`, `top_member`, `passed`, and a `calibration_note`
naming the cap as a project calibration rather than a sourced threshold.
**Acceptance**
- [ ] Headline fixture (n=13 / n=29) → HHI 0.573, m_eff 1.75, **fails**.
- [ ] 60/20/20 passes `m_eff` (2.27) and fails on the cap alone — the K>=3 binding case.
- [ ] A failing cell is still SERVED, labelled `dominated by <member>` (assert the label, not a drop).

### Unit 4: heterogeneity gate + spread guard + computability
```python
_I2_FREE, _I2_REFUSE = 0.40, 0.75      # Cochrane interpretation bands
_SPREAD_FORCE, _SPREAD_MIN_N = 0.25, 10
_HET_MIN_MEMBERS, _HET_MIN_MEMBER_N = 2, 5

def heterogeneity(members: Sequence[MemberTally], re: RandomEffects) -> Heterogeneity: ...
```
`Heterogeneity.band ∈ {"free","labelled","refused","not-computable"}` — closed vocabulary, fail-fast on
anything else — plus `one_sided_note`: **I² is one-sided evidence; a high value is a reliable stop, a
low value is NEVER a certificate of exchangeability.** That string must ride on the result so the UI can
surface it (the epic flags this caveat as able to fall between features).
**Acceptance**
- [ ] Headline fixture → I²=0.89 → `refused`, `member_split` populated.
- [ ] Direction guard: two members with n>=10 whose rates differ by >=0.25 force `refused` even at low I².
- [ ] Fewer than 2 members with n>=5 → `not-computable`, with **no homogeneity claim in either
      direction** (assert `one_sided_note` present and band is not `free`).

### Unit 5: evidence-gated prior strength (REPLACES the brief's inverted §4.5)
```python
_PRIOR_MIN, _PRIOR_MAX = 5.0, 30.0
_PRIOR_FULL_MEMBERS, _PRIOR_FULL_N = 3, 30   # evidence sufficiency, NOT tau2 == 0

def prior_strength(members: Sequence[MemberTally], re: RandomEffects) -> PriorStrength: ...
```
Strength scales with **evidence sufficiency** (member count and per-member n), then is *reduced* by
observed dispersion. `tau2 == 0` alone never buys the maximum.
**Acceptance**
- [ ] Two tiny members with `tau2 == 0` → strength near `_PRIOR_MIN`, **not** `_PRIOR_MAX`; `reason`
      names the evidence rule. (This is the adversarial read's behavior-changing finding.)
- [ ] Many large coherent members → near `_PRIOR_MAX`.
- [ ] Strength non-increasing in `tau2` at fixed evidence.

### Unit 6: orchestrator
```python
def aggregate_cluster_cell(
    subject: str, cluster_id: str, members: Sequence[MemberTally],
) -> PooledCell: ...
```
Returns pooled rate + CI + `n_eff` + `tier_for_sample(round(n_eff))` + concentration + heterogeneity +
prior strength + `intra_cluster_n` + provenance. Refusal → `pooled_p=None`, `refused_reason`,
`member_split`.
**Acceptance**
- [ ] **HEADLINE: Dimir Tempo vs (Aluren 4-9, Show and Tell 24-5) is REFUSED** by both gates, and the
      66.7% / n=42 number never appears anywhere in the result.
- [ ] Dilution fixtures (Cradle vs colorless prison 25.0% n=4 → 46.2% n=13; Aluren vs same 100% n=3 →
      50.0% n=12) produce a labelled, non-`free` band.
- [ ] Tier derives from `n_eff`, never raw `sum(n)` — assert a case where the two differ.
- [ ] No NaN/inf escapes; every degenerate branch returns a named reason.

## Implementation Order
Unit 1 → 2 → 3 → 4 → 5 → 6. Unit 1 is trickiest and everything downstream reads its output.

## Testing
Hermetic and DB-free throughout — the estimator takes plain tallies, so no fixture DB is needed at all.
Fixtures come verbatim from the brief's worked examples and the real-corpus measurements recorded above.
Non-vacuity: mutate each gate's threshold **by symbol name** and confirm the matching test goes red —
never by text substitution (see `idea-parity-test-mutations-must-be-one-sided`; that trap produced a
falsely-green result earlier today). Property tests cover the monotonicity claims.

## Risks
- **Numerical.** DL `tau2` clamps at zero; logits blow up at 0/n without the correction; `i2` divides by
  Q. Each needs an explicit branch with a named reason — a NaN reaching a cell is worse than a refusal.
- **Over-refusal.** The gates may refuse so often that pooling adds nothing. Measured expectation is
  already modest; if the headline fixture refuses but almost nothing else pools, report that as a finding
  for `-best-call-fallback` rather than loosening thresholds.
- **Calibration drift.** Four constants are project calibrations, not sourced. All module-level, named,
  and commented as such; the audit output must say so.

### Unit 7 (ADDED 2026-08-01): profile-coherence imputation license
**File**: `src/legacy_engine/analytics/superarchetype/aggregate.py`
Implements the epic's subject-axis licensed-imputation addendum (see epic body — premise verified:
LOO MAE 0.075 family vs 0.107 marginal, 15/21 wins; 189/681 thin definer cells fillable).
```python
_LICENSE_MIN_COLS = 3       # calibration: opponent columns with >=2 members at n>=12
_LICENSE_SIG_MAX_FRAC = 0.25  # calibration: max share of significantly-divergent columns
_IMPUTE_MIN_POOL = 25       # calibration: pooled sibling n floor to impute a cell

@dataclass(frozen=True)
class ImputationLicense:
    cluster_id: str
    cols_evaluated: int
    sig_divergent_cols: int
    tau_profile: float | None   # dispersion summary across evaluable columns
    granted: bool
    reason: str                 # named, always — "insufficient shared columns (1 < 3)" etc.

def imputation_license(cluster_id: str, profile: Mapping[str, Sequence[MemberTally]]) -> ImputationLicense: ...

@dataclass(frozen=True)
class ImputedCell:
    subject: str
    opponent: str
    p: float | None             # None => refused; see reason
    ci_low: float | None
    ci_high: float | None       # widened by tau_profile — never a raw pooled CI
    pool_n: int
    siblings: tuple[str, ...]
    license: ImputationLicense
    reason: str | None          # named refusal: local-veto / intra-family / pool too thin / no license

def impute_cell(subject: str, opponent: str, license: ImputationLicense,
                sibling_tallies: Sequence[MemberTally]) -> ImputedCell: ...
```
**Acceptance**
- [ ] A sa-024-shaped profile (>=10 evaluable columns, median spread ~0.05, zero significant) → granted.
- [ ] A comparability-desert profile (<_LICENSE_MIN_COLS evaluable columns) → NOT granted, named reason;
      impute_cell then refuses with "no license" (the family-range display is the fallback, owned by
      -best-call-fallback).
- [ ] LOCAL VETO: a column whose members measurably diverge (chi2 p<.05 with >=2 members n>=12) refuses
      imputation for that cell even under a granted license, named reason.
- [ ] Intra-family target (opponent in subject's own cluster) → refused, named reason.
- [ ] Imputed CI is strictly wider than the raw pooled CI whenever tau_profile > 0 (assert the widening).
- [ ] p never appears without the license attached; no NaN/inf escapes.
- [ ] Non-vacuity: mutate _LICENSE_MIN_COLS / the veto predicate BY SYMBOL NAME and confirm the matching
      tests go red.
