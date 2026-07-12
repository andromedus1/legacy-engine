---
description: "How do you detect, per archetype and per camp, WHEN a deck was disturbed (ban, release, rebuild) from short weekly count/composition series — and control false positives across ~50-150 entities — so stable_since(entity) can replace ban-only valid_since? Read before designing epic-stable-era-windows."
type: brief
kind: research
slug: change-point-detection
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-11
blocks_phase: epic-stable-era-windows
summary: |
  Curates change-point detection methods for legacy-engine's per-entity stable-era detection.
  Grounds the method choice in the real corpus (weekly series of 30-130 points; mid-tier archetypes
  at 2-8 decks/week; camps at 2-12/week; two measured ground-truth disturbances — the Candelabra ban
  cliff and the one-week Flow State adoption step) and in the CPD literature: signal-typed detector
  ensemble (presence rules for cliffs/ramps, kernel/energy CPD for composition drift, Beta-Binomial
  models for shares/win-rates), PELT + penalty as the offline segmenter, BOCPD/CUSUM for the online
  drift alarm, permutation p-values + BH-FDR + min-segment floors for fleet-level false-positive
  control, and the ban/release ledger as the calibration ground truth.
key_findings:
  - "This corpus's disturbances are LOUD: Flow State went 0%→90-95% inclusion in ONE week across three archetypes, and the Candelabra ban collapsed Tron 59→1 decks/week in two — simple per-card presence rules (release ramp, ban cliff) detect the sharpest era boundaries with ~1-2 weeks latency; generic CPD is only needed for the gradual composition-drift residual."
  - "Never trust CPD defaults: on real-world benchmarks the trivial zero-changepoint detector outperforms many published methods at default parameters, and textbook penalties (AIC/BIC) are calibrated to correctly-specified models and 'lack robustness … in the presence of model mis-specification' — calibrate the penalty against the project's own labeled ban/release ledger."
  - "The penalty IS the false-positive knob ('adding a changepoint always reduces the overall cost'); across ~50-150 entity series, use per-change-point permutation p-values (E-Divisive's #{q_r ≥ q_0}/(R+1)) corrected with Benjamini-Hochberg FDR, plus a minimum-segment floor tied to the engine's sample tiers (E-Divisive's own default is min.size=30 observations)."
  - "Weekly counts are too small for normal-approximation monitoring (NIST: Poisson normal approx needs mean ≥5; mid-tier archetypes run 2-8 decks/week) — use share-of-field proportions and exact Beta-Binomial/Poisson-Gamma likelihoods (BOCPD), never raw-count z-scores; guard the partial trailing week, which drops EVERY entity's raw count."
  - "Composition drift is a multivariate distribution change on the discovery flex-band vectors: kernel-cost CPD ('can be combined with any kernel … not just R^d-valued signals') or energy-statistic E-Divisive ('able to detect any type of distributional change') both fit; PELT gives exact penalized segmentation at trivial cost on 30-130-point series."
  - "No Python BOCPD package ships count-data likelihoods (the reference implementation has only StudentT/MultivariateT — verified against source); the Poisson-Gamma/Beta-Binomial conjugate recursions must be implemented in-project as a small module (scipy is already a core dep); ruptures is the offline dependency to add — it has no Poisson cost either, so count signals route through proportions or a custom cost."
  - "Known ban/release dates are labels and priors, never the source of truth: snap detected change points to announcements within a tolerance to NAME the trigger; a detected cliff with NO matching announcement is the drift alarm (banlist-currency check) — the mechanism that would have caught Candelabra 2 days after the ban instead of 6 weeks later."
---

# Brief: Change-Point Detection for Per-Entity Stable Eras

## Purpose

Unblocks `epic-stable-era-windows`. The epic's locked decisions: per-archetype AND per-camp
disturbance detection from the corpus itself; `stable_since(entity)` replaces ban-only
`valid_since` as the DEFAULT adaptive-matrix horizon with honest degrade; scope reaches all
regime-windowed surfaces; the Candelabra ban is the first ground-truth validation case; thin
post-disturbance cells get hierarchical shrinkage. This brief gives the builder the
signal-taxonomy, method-selection, false-positive-control, and calibration decisions — grounded in
the real corpus and the CPD literature. It does **not** dictate module structure (that is
`epic-design`'s job).

---

## 1. The problem in data terms

The unit of detection is an **entity** (a parent archetype or a discovered camp) and its **weekly
series**. Measured on the corpus (2023-12-31 → 2026-07-01; 79 distinct weeks since 2025-01-01):

| Entity tier | weekly decks (median) | example |
|---|---|---|
| Top-15 archetypes | 8–45/week (p10 ≈ 3–13, p90 ≈ 19–77) | Dimir Tempo: med 24, max 108 |
| Ranks 16–40 | 2–8.5/week | most of the ranked field |
| Camps (post-discovery) | 2–12/week | Dimir Tempo [Barrowgoyf]: med 12; [Nethergoyf]: med 2 |

Three properties shape everything downstream:

- **Series are short.** ≤ ~130 weekly points per entity, often 30–80 (younger decks, camps).
  Asymptotic guarantees are irrelevant; small-sample behavior and false-positive control dominate.
- **Counts are small.** A mid-tier archetype's weekly count sits well below the mean-≥5 floor
  where normal-approximation count monitoring is adequate `[nist-count-charts]{9}`. Camp-level
  weekly counts are single digits — rate statistics per week are hopeless there without pooling.
- **The trailing week is partial.** The corpus ends mid-week (2026-07-01), so EVERY entity's raw
  count drops in the last bucket (Dimir Tempo 24→3 "decks"). A raw-count detector flags the whole
  fleet every refresh. Use **share of the weekly field**, not raw counts, and exclude or
  down-weight the incomplete trailing bucket (measured on corpus; engineering requirement, not a
  sourced claim).

### Ground truth #1 — the Candelabra ban cliff (play-rate signal)

Tron weekly deck counts, measured on corpus: `2, 5, 12, 34, 23, 42, 37, 41, 52, 20, 28, 36, 50,
58, 59, 59, 20, 1` (weeks of 2026-03-02 → 2026-06-29). The left side is the RELEASE-driven growth
ramp (Candelabra reprint), the right side the ban collapse (banned 2026-06-29; the 06-22 drop
reflects the announcement landing intra-week; 06-29 is the partial trailing week). The engine's
regime table missed this ban for ~6 weeks (rules pin stale); the corpus fingerprint was
unmistakable within days — this asymmetry is the epic's reason to exist.

### Ground truth #2 — the Flow State adoption step (composition + release signal)

Weekly share of decks running Flow State, measured on corpus:

| Week | Doomsday | Izzet Delver | Dimir Tempo |
|---|---|---|---|
| 2026-04-06 | 0% | 0% | 0% |
| 2026-04-13 | 0% | 29% | 3% |
| 2026-04-20 | **95%** | **90%** | **71%** |
| 2026-04-27 → 06-15 | 92–100% | 94–100% | 84–100% |

Adoption is a **one-week step function**, not a gradual ramp — the competitive population rebuilt
three archetypes essentially overnight, with no ban and therefore no `valid_since` change. Every
matchup cell touching these archetypes silently pools across this break today.

**Implication (load-bearing for method choice):** the sharpest era boundaries in this corpus are
*near-degenerate steps on a single card's inclusion rate*. A per-card presence rule detects them
with 1–2 weeks latency and names the trigger card for free. Generic multivariate CPD is needed for
what the rules can't see: multi-card rebalances, gradual composition drift, and win-rate/share
shifts without a signature card.

---

## 2. Signal taxonomy — four disturbance signals, three data types

The epic names four signals. They reduce to three statistical data types, each with a different
appropriate detector family. This mapping is the core design decision.

| # | Signal | Data type | Detector family |
|---|---|---|---|
| S1 | Cards vanishing (ban) / appearing (release) | per-card weekly inclusion proportion, near-step | **rule-based presence detector** (threshold crossings on exact binomial proportions) |
| S2 | Composition drift (multi-card rebalance) | weekly flex-band inclusion/copy vector (multivariate) | **kernel/energy CPD** (PELT+RBF-or-cosine cost, or E-Divisive) |
| S3 | Play-rate share shift | weekly share of field (binomial proportion) | **Beta-Binomial BOCPD** (online alarm) + penalized offline segmentation |
| S4 | Win-rate shift | weekly W/L record (binomial, small n) | same as S3; corroborating only, never primary (weakest signal-to-noise) |

### S1 — presence cliffs and ramps (the cheap, high-yield detector)

For each entity, compute the weekly inclusion rate of each flex-band card (the representation
`analytics/discovery.py` already builds). A **ban cliff** is inclusion ≥ x% collapsing to ~0; a
**release ramp** is 0 jumping to ≥ y% (ground truth #2 shows one-week 0→90% jumps — even crude
thresholds with a 2-consecutive-week confirmation are reliable here). Two side-inputs sharpen it:
`ingestion/releases.py` already knows recent set releases (a 0→adopted card whose printing date is
within the window is labeled a release trigger), and `BAN_EVENTS` labels vanishing cards. The
detected boundary is dated from the DATA (the week the step happens), the announcement only names
it. This detector alone recovers both ground truths, with the trigger card attached — it should
run first, and generic CPD should treat its output as candidate change points with named causes.

### S2 — composition drift (the genuinely multivariate case)

Build per-entity, per-window (weekly, or pooled 2–4-week buckets for thin entities) flex-band
inclusion vectors — the same stratified representation the discovery brief established (ubiquitous
core carries no signal; the ~20–30-card flex band carries all of it; see
`docs/briefs/subarchetype-discovery.md` §2). A composition era-break is a change in the
DISTRIBUTION of these vectors. Two attested method families fit:

- **Kernel change-point detection** — CPD cost functions compose with "any kernel to accommodate
  various types of data (not just R^d-valued signals)" `[truong-cpd-review]{1}`. ruptures
  implements this as `KernelCPD` with linear, Gaussian-RBF, and cosine kernels; the RBF cost "is
  able to detect changes in the distribution of an iid sequence of random variables" and is
  non-parametric, with γ set by the median heuristic `[ruptures-docs]{3}`. Cosine is the natural
  kernel for the (TF-IDF-style, L2-normalized) inclusion vectors this project already uses.
- **Energy-statistic E-Divisive** — hierarchical bisection on the Székely–Rizzo energy divergence;
  suitable "for both univariate and multivariate observations" and "able to detect any type of
  distributional change within the data", assuming only independence and finite α-th absolute
  moments `[ecp-jss]{4}`. Its distinguishing feature: each candidate change point gets a
  **permutation-test p-value** — "p̂ = #{r : q_r ≥ q_0}/(R + 1)" `[ecp-jss]{4}` — which is exactly
  the per-detection significance the fleet-level FDR control in §4 needs. (Reference
  implementation is the R package; the algorithm — bisect on max energy divergence, permutation
  test, recurse — is straightforwardly implementable in Python; its divisive estimates are
  strongly consistent for independent observations `[ecp-jss]{4}`.)

### S3/S4 — rates and proportions (small-count discipline)

Weekly deck counts fail the classic count-chart adequacy floor — "the normal approximation to the
Poisson is adequate when the mean of the Poisson is at least 5" `[nist-count-charts]{9}`, and
below a mean of ~9 a c-chart has no lower control limit at all `[nist-count-charts]{9}` — so
z-score-style monitoring on raw weekly counts is out for most of the fleet. Instead: model the
weekly **share** (deck count / total field that week) as binomial and the win-rate as
Beta-Binomial, using exact-likelihood methods (§3). Win-rate (S4) is the noisiest signal (weekly
match n is small and win-rate shifts lag composition shifts); treat it as corroboration for a
boundary detected by S1/S2/S3, not as a primary detector (author's engineering judgment, not a
sourced claim).

---

## 3. Method selection — offline segmenter + online alarm

The epic needs BOTH modes: an **offline segmentation** (rerun at every `refresh`/`label`, derives
`stable_since(entity)` from the full series) and an **online alarm** (the drift/banlist-currency
check — "did something break THIS week?"). These are different problems with different tools:
offline detection is retrospective segmentation of the full series `[truong-cpd-review]{1}`, while
BOCPD is the online formulation `[adams-mackay-bocpd]{5}`.

### Offline: PELT over a penalized cost, per signal type

Offline CPD methods decompose into "a cost function, a search method and a constraint on the
number of changes" `[truong-cpd-review]{1}`. Choices:

- **Search: PELT.** Exact — its pruning "does not affect the exactness of the resulting
  segmentation" `[killick-pelt]{2}` — and fast (average O(CKn) `[ruptures-docs]{3}`; at n≈30–130
  everything is instant, so exactness is free — take it over Binseg's greedy sequential splitting
  `[ruptures-docs]{3}`, which measurably degrades segmentation accuracy `[killick-pelt]{2}`).
- **Constraint: penalized (unknown K).** The number of eras is unknown; use the linear-penalty
  form with the penalty as the explicit false-positive knob (§4). BIC-style β=p·log n is the
  textbook default `[killick-pelt]{2}` — but see §4 for why the default must be calibrated, not
  trusted.
- **Cost, by signal:** RBF/cosine kernel cost on composition vectors (S2); L2 on
  variance-stabilized share/win-rate series (S3/S4 offline — e.g. arcsine or Anscombe transforms;
  ruptures ships **no Poisson/count-family cost** `[ruptures-docs]{3}`, so raw counts must be
  transformed, routed through proportions, or given a custom cost). `min_size` "controls the
  minimum distance between change points" `[ruptures-docs]{3}` — the segment floor §4 ties to
  sample tiers.

### Online: BOCPD (primary) or CUSUM (simple fallback) for the drift alarm

**BOCPD** maintains the exact posterior over the current run length ("the probability distribution
of the length of the current 'run,' or time since the last changepoint, using a simple
message-passing algorithm" `[adams-mackay-bocpd]{5}`), is "highly modular so that the algorithm
may be applied to a variety of types of data" `[adams-mackay-bocpd]{5}`, and for
exponential-family models reduces to tracking conjugate hyperparameters per run-length hypothesis
— "we just need to keep track of the exponential family parameters by time t−1 to make a
prediction at time t" `[gundersen-bocpd]{6}`. That makes Beta-Binomial (weekly share, win-rate)
and Poisson-Gamma (counts, where means permit) drop-in likelihoods, and the output — a per-week
posterior probability that an era just ended — is the honest-degrade-friendly surface the epic
wants (report P(disturbed), don't just hard-flag). The hazard prior encodes expected era turnover
("Provided a changepoint has not occurred by run length τ, what is the probability that it will
occur at τ?" `[gundersen-bocpd]{6}`) — with ~4 known format-wide disturbances per year, a constant
hazard of roughly 1/20–1/30 weeks is the right starting order (author's calibration suggestion, to
be tuned on the ledger).

**Packaging reality (load-bearing negative):** the commonly-cited Python implementation
(`hildensia/bayesian_changepoint_detection`) implements ONLY `StudentT` and `MultivariateT`
likelihoods — no Poisson, Beta, or binomial classes exist in its source `[bocpd-python-pkg]{7}`.
Plan to implement the conjugate BOCPD recursion in-project as a small module (numpy/scipy are
already core deps) rather than adding a dependency that doesn't cover the needed likelihoods.

**CUSUM** is the simpler sequential alternative: it accumulates deviations from a baseline and is
"more efficient in detecting small shifts in the mean" than per-point charts, specifically for
shifts "2 sigma or less" `[nist-cusum]{8}`, signaling when a one-sided cumulative statistic
exceeds a decision limit h `[nist-cusum]{8}`. Its design vocabulary — high in-control ARL (few
false alarms), low out-of-control ARL (fast detection) `[nist-cusum]{8}` — is the honest way to
state the alarm's latency/false-alarm trade in docs. CUSUM is a reasonable v1 alarm if BOCPD is
deemed too much machinery; it lacks the per-week posterior probability output.

### Composition of the ensemble (recommendation)

Run per entity, in order: **S1 presence rules** (cheap, names triggers, catches steps) → **S2
kernel/energy CPD on composition** (catches multi-card rebuilds) → **S3 share-shift** detection →
**S4 win-rate** corroboration. Merge candidate change points across signals (within a ±1–2 week
tolerance), then attribute each accepted boundary: matching `BAN_EVENTS` date → "ban: <card>";
matching release window (`ingestion/releases.py`) + ramp card → "release: <card> adoption";
otherwise → "composition/rate shift (unattributed)" — the last category is what triggers the
banlist-currency check (an unattributed cliff = maybe an unregistered ban; degrade honestly until
confirmed). Announcements are labels and priors, **never the source of truth** (epic decision;
Candelabra is the proof case).

---

## 4. False-positive control — the make-or-break section

A spurious change point is not cosmetic here: it silently truncates an entity's data window,
throwing away real sample (the exact failure the honest-degrade policy exists to prevent). Four
attested defenses, to be used together:

1. **The penalty is the knob, and defaults are not trustworthy.** Penalized CPD overfits by
   construction — "adding a changepoint always reduces the overall cost" `[crops-penalty]{10}` —
   and the textbook penalties (AIC β=2p, SIC/BIC β=p·log n, Hannan–Quinn β=2p·log log n
   `[crops-penalty]{10}`) assume a correctly specified within-segment model. Under
   mis-specification they "lack robustness, and can produce poor segmentations"
   `[crops-penalty]{10}` — and weekly deck shares are emphatically not i.i.d. Gaussian. The
   real-data benchmark verdict is blunt: with default parameters, the trivial **zero-changepoint
   detector "outperforms many of the other methods"** `[vdburg-cpd-eval]{11}`, and CPD methods are
   "typically evaluated on simulated data and a small number of commonly-used series with
   unreliable ground truth" `[vdburg-cpd-eval]{11}`. **Calibrate the penalty on the project's own
   labeled disturbance ledger (§5)** — sweeping the penalty range (the CROPS idea: optimal
   segmentations "for all penalty values across a continuous range" `[crops-penalty]{10}`) and
   picking the region that recovers known bans/releases without fabricating extra eras.
2. **Per-detection significance + fleet-level FDR.** With ~50–150 entities screened per refresh,
   per-entity α accumulates. Prefer detectors that emit a per-change-point p-value (E-Divisive's
   permutation test `[ecp-jss]{4}`) and correct across the fleet with Benjamini–Hochberg: "find
   the largest k for which P(k) ≤ (k/m)α" and reject only those `[wikipedia-fdr]{12}`. BH (FDR)
   rather than Bonferroni (FWER) is the right stringency — FDR control trades a small expected
   fraction of false discoveries for materially greater power `[wikipedia-fdr]{12}`, and a missed
   real era-break (silent pooling across a disturbance) is also a real cost, so maximal
   conservatism is not free.
3. **Minimum segment length, tied to the tier gates.** Enforce a floor on era length so an "era"
   can never be born below a defensible sample: ruptures' `min_size` mechanism
   `[ruptures-docs]{3}`; precedent for the magnitude, E-Divisive's own default `min.size = 30`
   observations `[ecp-jss]{4}`. For legacy-engine, express the floor in DECKS, not weeks (e.g. a
   new era must contain ≥ the evolving-tier floor of 30 subject decks before it may truncate
   windows) — thin entities then naturally detect at coarser time resolution (pooled buckets),
   and camps below tier simply inherit their parent's boundaries (author's integration rule; the
   tier system is the project's own).
4. **Confirmation asymmetry in the consumer.** The epic's honest-degrade decision: when detection
   is uncertain (alarm fired but unconfirmed; post-break window still below tier), the consumer
   falls back to the ban-only `valid_since` horizon and LABELS the cell, rather than committing to
   an uncertain truncation. Detection uncertainty must degrade the WINDOW claim, never silently
   change the number.

---

## 5. Calibration & validation — the disturbance ledger is the ground truth

The project owns something the CPD literature says most evaluations lack — real labeled ground
truth `[vdburg-cpd-eval]{11}`:

- **12 ban events** (2022-01 → 2026-05 in `BAN_EVENTS`) × the affectedness classifier's per-ban
  inclusion rates = a labeled set of (entity, date, affected?) cliff cases — including validated
  bimodal cases (Entomb ≈100% of Dimir Reanimator; Undercity Informer ≈99.9% of Oops!, per
  `analytics/affectedness.py`'s docstring) — plus **Candelabra 2026-06-29** as the held-out
  headline case the current system missed.
- **Release rebuilds**: Flow State (three archetypes, one-week step, §1); the Fantasticar
  (2026-06-20 printing → 11.3% field); Tron's Candelabra-reprint growth ramp.
- **Known non-events**: long stable stretches (e.g. Lands/Death & Taxes mid-regime) that a
  well-calibrated detector must NOT segment.

Calibration procedure (recommendation): sweep the penalty/threshold per detector over its range
`[crops-penalty]{10}`; score each setting on (hit rate on ledger disturbances, median detection
latency in weeks, false eras per entity-year on the non-event stretches); pick the conservative
knee. Report the chosen operating point's expected latency and false-alarm rate in the epic's docs
using the ARL vocabulary `[nist-cusum]{8}`. Re-validate on every method change with the same
harness (this becomes a pinned test fixture — the ledger is small and frozen).

The era-audit diagnostics already built (per-camp %current, median date — the manual analysis that
motivated this epic) are the human-facing sanity check: after detection runs, every entity's
detected eras should be consistent with its %current/median-date profile.

---

## 6. Small-sample playbook (per-entity adaptivity)

Series length and weekly density vary ~20× across the fleet. One detector configuration cannot
serve Dimir Tempo (median 24/week) and a rank-35 archetype (median 3/week). Adapt along three
axes (author's integration design, grounded in §2's small-count constraints):

- **Bucket width**: weekly for entities sustaining ≥ ~10 decks/week; pool to 2- or 4-week buckets
  below that (restores per-bucket counts above the mean-≥5 adequacy floor
  `[nist-count-charts]{9}` for most ranked entities). Latency degrades gracefully and honestly —
  a thin entity's eras are simply known at coarser resolution; surface the resolution.
- **Signal availability**: S1 presence rules work at any density (they pool the whole bucket);
  S2 composition CPD needs enough decks per bucket to estimate an inclusion vector (floor ~10-15
  decks/bucket); S3/S4 rate detection needs the adequacy floor. An entity gets the subset of
  signals its density supports, and its detection provenance says which.
- **Camp granularity**: camps inherit the parent's detected boundaries by default; camp-specific
  detection (a camp can be disturbed when its parent is not — e.g. one camp's signature card is
  banned) runs only where the camp clears the density floors. Never let a 2-deck/week camp
  fabricate its own eras.

---

## 7. Implementation notes

- **Consumption seam is already built.** `build_adaptive_matrix` sources each cell over
  `[max(valid_since(a), valid_since(b)), now)`; the epic swaps `archetype_valid_since` (ban-only)
  for `stable_since` (detected) as the horizon function — same shape, richer derivation. The
  audit line pattern (`window.py::_adaptive_audit`) extends to name the triggering disturbance
  per entity ("Doomsday since 2026-04-20: Flow State adoption"). `explain_valid_since`'s
  per-ban-event explanation table is the model for `explain stable_since` — every detected
  boundary must be human-explainable (signal, magnitude, p-value/posterior, attribution).
- **Detection is an offline labeling pass**, sibling to `label` and `discover run` — rerun at
  refresh, persist per-entity `stable_since` + boundary metadata (date, signal, trigger,
  confidence) in a table/JSON with the same staged-provenance discipline discovery uses. Never
  detect in a query hot path.
- **Sequencing with discovery** (the absorbed temporal-gate): detect PARENT change points first;
  run camp discovery within stable windows (the default recommendation), keeping the
  temporal-mixing Gate C (camp date-distribution separation → "camps may be list generations"
  label) as the backstop for splits that still straddle a boundary. Per-camp %current + median
  date surface in the discover report regardless.
- **Dependencies**: add `ruptures` for PELT/KernelCPD `[ruptures-docs]{3}`;
  implement BOCPD's conjugate recursion in-project (`scipy` already core)
  `[bocpd-python-pkg]{7}`; the S1 presence rules and the E-Divisive permutation scheme (if chosen
  over kernel-PELT for its p-values) are plain numpy. No R bridge — the R packages (`ecp`, `ocp`,
  `bcp`) are prior art, not dependencies.
- **The banlist-currency loop closes here** (the absorbed bug): an unattributed detected cliff on
  a high-share entity triggers the drift alarm → surface "possible unregistered B&R change;
  windowing degraded pending confirmation" → human confirms → `BAN_EVENTS` + regime table update.
  The rules-pin refresh cadence question dissolves into this loop — staleness becomes detectable
  instead of silent.
- **Scale**: ~150 entities × ≤130 weekly points × a handful of detectors is milliseconds-to-
  seconds of compute per refresh; PELT's O(CKn) `[ruptures-docs]{3}` and E-Divisive's O(kT²)
  `[ecp-jss]{4}` are both trivial at this size. Choose methods on statistical merit only.

### Long tail (out of scope, noted)

Exact Bayesian OFFLINE segmentation (Fearnhead 2006; R packages `bcp`, `ocp`) would give posterior
probabilities per boundary position — attractive but unattested here (paywalled primary) and
redundant with E-Divisive's permutation p-values for the fleet-FDR purpose. Selective-inference
corrections for testing segment means AFTER segmentation (the post-detection analog of the
discovery brief's double-dipping guard) matter only if the epic later tests "did the win-rate
really change across this boundary" on the same data that placed the boundary — flag for
epic-design if that surface is added. Compositional-geometry-aware CPD (Aitchison/CLR transforms
before kernel costs) is a refinement with no attested precedent found; the cosine/RBF kernels on
normalized inclusion vectors are the pragmatic default.

---

## Sources

- Truong, Oudre & Vayatis (Signal Processing 2020) — offline CPD taxonomy; kernel costs beyond R^d `[truong-cpd-review]{1}`
- Killick, Fearnhead & Eckley (JASA 2012) — PELT exactness, linear cost, penalty forms `[killick-pelt]{2}`
- ruptures documentation — PELT/Binseg/KernelCPD/costs, min_size/jump/pen, no Poisson cost `[ruptures-docs]{3}`
- James & Matteson (JSS 2014) — E-Divisive energy CPD, permutation p-values, min.size=30, consistency `[ecp-jss]{4}`
- Adams & MacKay (2007) — BOCPD run-length posterior, modularity `[adams-mackay-bocpd]{5}`
- Gundersen (2019) — BOCPD hazard function + exponential-family conjugate bookkeeping `[gundersen-bocpd]{6}`
- hildensia/bayesian_changepoint_detection source — StudentT-only likelihood coverage (negative) `[bocpd-python-pkg]{7}`
- NIST/SEMATECH e-Handbook §6.3.2.3 — CUSUM small-shift sensitivity, tabular h/k, ARL `[nist-cusum]{8}`
- NIST/SEMATECH e-Handbook §6.3.3.1 — c-chart, Poisson normal-approximation floor `[nist-count-charts]{9}`
- Haynes, Eckley & Fearnhead (JCGS 2017) — CROPS penalty sweep; penalty defaults under mis-specification `[crops-penalty]{10}`
- van den Burg & Williams (2020) — real-data CPD benchmark; zero-detector finding `[vdburg-cpd-eval]{11}`
- "False discovery rate" (Wikipedia) — FDR definition, BH procedure, FDR-vs-FWER `[wikipedia-fdr]{12}`

Additional prior art consulted (context, not load-bearing; not attested): Matteson & James (JASA
2014, the E-Divisive theory paper backing the JSS implementation), Arlot–Celisse–Harchaoui (JMLR
2019, kernel multiple change-point via model selection), Gretton et al. (JMLR 2012, MMD two-sample
test), Fearnhead (2006, exact Bayesian multiple-changepoint inference), Page (1954, the original
CUSUM), Benjamini & Hochberg (1995, the primary FDR paper — paywalled), and the R packages
`ecp`/`ocp`/`bcp` as reference implementations.
