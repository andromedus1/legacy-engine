---
id: epic-superarchetype-layer-aggregation
kind: feature
stage: drafting
tags: [analytics]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-clustering]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
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
