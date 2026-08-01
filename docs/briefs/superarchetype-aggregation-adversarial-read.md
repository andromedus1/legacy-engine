---
description: "Adversarial passage-level source-support audit of docs/briefs/superarchetype-aggregation.md — read this before trusting any numeric threshold, method-transfer claim, or literature attribution in that brief, and before an epic-design session treats one of its gate values as sourced."
type: brief
kind: research
slug: superarchetype-aggregation-adversarial-read
research_method: adversarial-reader
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-31
status: complete
audits: docs/briefs/superarchetype-aggregation.md
summary: |
  Fresh-context adversarial read of all 83 citations in the superarchetype-aggregation brief against
  the 21 attestation files they resolve to. Verdict APPROVE-WITH-FIXES: 68 SUPPORTED, 13 OVERSTATED,
  2 MISATTRIBUTED, 0 UNSUPPORTED, plus 9 UNCITED-CRITICAL load-bearing claims. No defect touches the
  recommended method — every finding is a sourcing/labeling defect or an over-precise derivation
  whose correction makes the gates MORE conservative, not less. All clear-cut findings were applied
  as narrowing edits to the brief in the same pass.
key_findings:
  - "Zero UNSUPPORTED citations across 83. Every cited passage is real, quoted accurately, and bears on its neighbourhood — the failure mode in this brief is strength and labeling, not fabrication."
  - "The dominant defect shape is a project-calibrated threshold sitting adjacent to a source citation that does not endorse that value: m_eff >= 2.0, the 0.60 member-share cap, the I-squared action bands, and the AU >= 0.95 dendrogram rule all read as sourced in the at-a-glance table while the body correctly labels most of them as ours."
  - "The 60% max-member-share cap was the only gate parameter with NO grounding of any kind — no source, no measurement, no stated calibration — and it is the binding constraint at K>=3 (60/20/20 gives m_eff 2.27, which passes the concentration gate and fails only the cap)."
  - "Section 4.4's claim that n_eff returns Sigma n_k when tau-squared = 0 is not exactly true: tau-hat-squared = 0 means undetected dispersion, not identical rates, and n_eff falls below Sigma n_k whenever member rates differ, by concavity of p(1-p). The error direction is safe — the gate is stricter than advertised."
  - "The pvclust feature-axis resampling claim — the entire justification for AU p-values working at N about 30 — rests on the attestation's unquoted summary, not on any quoted passage. Same for the HDBSCAN 'no density contrast at N about 30' argument, which is neither sourced (the attested HDBSCAN limitation is dimensional) nor measured, in a brief that measures everything else."
  - "The gao-selective-inference citation was used to raise the double-dipping hazard while the same attestation's next passage ('persists even if two separate and independent data sets are used') was left unquoted — the one passage that most directly challenges the brief's escape argument. The escape argument survives on the disjoint-variables-vs-disjoint-samples distinction, but that distinction had to be stated."
  - "Coherence defect worth a design change: section 4.5 reads tau-hat-squared = 0 as 'coherent cluster' and awards the maximum prior strength of 30, while section 6.4 establishes that at these member sizes a zero mostly means 'we cannot see spread'. That hands maximum prior strength to 58.7% of cells on the weakest evidence — the exact inversion the heterogeneity gate exists to prevent."
---

# Adversarial Source-Support Read: `superarchetype-aggregation.md`

**Scope.** Passage-level groundedness gate. Every one of the 83 `[handle]{N}` citations in
`docs/briefs/superarchetype-aggregation.md` (725 lines, 21 handles) read against the actual quoted
passages in `.research/attestation/superarchetype-*.md` (12 files) plus the 9 handles cross-listed
from the `subarchetype-discovery` corpus. This is the check `/citation-lint` cannot do: the lint
proves each handle resolves; this asks whether the passage says what the claim says.

Codebase assertions were verified against source (`matchup.py`, `discovery.py`, `pyproject.toml`) —
those are reported in §4 below. Corpus measurements were **not** recomputed; only their presentation
and labeling were audited.

---

## Verdict

> ## APPROVE-WITH-FIXES
>
> **The recommended method survives intact.** Not one finding undermines the clustering choice, the
> aggregation estimator, or any of the three gates. Every defect is one of: (a) a project
> calibration presented in sourced clothing, (b) a strength escalation over what the passage carries,
> or (c) an over-precise derivation whose correction makes the gate *stricter*. All clear-cut cases
> were applied as narrowing edits in this pass (§5).
>
> One finding rises above presentation and warrants a design change before implementation: the
> §4.5 / §6.4 coherence inversion (F-13).

---

## 1. Count summary (out of 83 citations)

| Classification | Count | Share |
|---|---:|---:|
| **SUPPORTED** | **68** | 82% |
| **OVERSTATED** | **13** | 16% |
| **MISATTRIBUTED** | **2** | 2% |
| **UNSUPPORTED** | **0** | 0% |
| *(separately)* **UNCITED-CRITICAL** | **9** | — |

Of the 83, 21 are bibliography entries in `## Sources` (lines 702-721); all 21 describe their
attestations accurately and are counted SUPPORTED. The 62 in-body citations break down 47 SUPPORTED
/ 13 OVERSTATED / 2 MISATTRIBUTED / 0 UNSUPPORTED.

**The zero matters.** No passage was fabricated, no quote was invented, and no citation pointed at a
source that has nothing to do with its claim. Verbatim quotes were checked character-by-character
against the attestations and are accurate throughout, with one exception (F-06, quote marks around a
paraphrase). The brief's failure mode is *strength and labeling*, not grounding.

---

## 2. Non-SUPPORTED findings

Line numbers refer to the **pre-edit** brief (725 lines). "Fix applied" marks findings narrowed in
this pass; see §5 for the exact edits.

| # | Claim (quoted, line) | Handle | Class | What the source actually supports | Supported rewording |
|---|---|---|---|---|---|
| F-01 | "**Average-linkage agglomerative** on the precomputed dissimilarity `[13]`; every archetype gets a cluster (no noise class)" (L58) | `sklearn-clustering` | OVERSTATED | Only the linkage-criterion definitions ("Average linkage minimizes the average of the distances between all observations of pairs of clusters"). Nothing about precomputed affinity; nothing about full assignment. | "Average-linkage agglomerative (linkage criterion per `[13]`) on the precomputed dissimilarity" — move the cite onto the criterion. *Fix applied.* |
| F-02 | "multiscale-bootstrap AU p-value **>= 0.95** over resampled card features `[11]`" (L59) | `superarchetype-pvclust` | OVERSTATED | The source's rule is `> 0.95`, stated for **one** cluster. The "over resampled card features" qualifier appears in no quoted passage — only in the attestation's unquoted Summary. | "AU p-value **> 0.95** `[11]`, resampling card features rather than archetypes (our port — see §3.4)". *Fix applied.* |
| F-03 | "**Random-effects (DerSimonian-Laird) inverse-variance pooled proportion** on continuity-corrected logits `[7]`" (L62) | `superarchetype-meta-pooling` | OVERSTATED | `w*_k = 1/(s²_k+τ²)` and the weighted mean. The source **never names DerSimonian-Laird**, and the continuity correction is attested nowhere in the corpus. | Split the cite: "Random-effects inverse-variance pooled proportion `[7]` on continuity-corrected logits, with `tau^2` by the DL moment estimator (§4.3)". *Fix applied.* |
| F-04 | "**Effective members `m_eff` = 1/HHI >= 2.0** AND max member share <= 0.60 `[8]`" (L64) | `superarchetype-hhi` | OVERSTATED | Σ shares², and "1/H is called 'equivalent (or effective) number of firms'". The source endorses **neither 2.0 nor 0.60**; its only thresholds are the DOJ bands, which §5.2 correctly says do not transfer. The glance table borrows authority the body disclaims. | "`m_eff` = 1/HHI `[8]`, gated at >= 2.0 with max member share <= 0.60 — both cutoffs are ours, calibrated in §5.2". *Fix applied.* |
| F-05 | "**I-squared <= 0.40** pool freely; **0.40-0.75** … **> 0.75** refuse … `[5]`" (L65) | `superarchetype-cochrane-heterogeneity` | OVERSTATED | The band *edges* 0.40 and 0.75 are genuinely Cochrane's, quoted verbatim and correctly at L478-480. But Cochrane offers them as a rough guide with deliberately **overlapping** bands and attaches no actions; "pool freely / label / refuse" is entirely the project's. | "Boundaries taken from Cochrane's rough-guide bands `[5]`; the actions are ours". *Fix applied.* |
| F-06 | "in their League of Legends data \"the maximum possible compositions reaches 359,933,112, yet only 348,498 unique compositions appeared\"" (L108-110) | `superarchetype-pvp-counter-clustering` | OVERSTATED | The attestation records these figures as the **attester's paraphrase**, unquoted — unlike the four passages beside it, which are quoted. The brief adds quotation marks the attestation does not license. Numbers themselves are attested. | Drop the quote marks; state the figures as reported values. *Fix applied.* |
| F-07 | "Copy counts and abundance-aware distances matter where a split is a quantity difference `[16]`" (L134-135) | `bray-curtis` | **MISATTRIBUTED** | The source defines Bray-Curtis as an abundance-aware dissimilarity for species counts. It says nothing about *when a split is a quantity difference* — that is the camp brief's own finding, inherited here as analytical-tier framing wearing a Wikipedia citation. | "…matter where a split is a quantity difference (the camp brief's own finding); Bray-Curtis is the abundance-aware dissimilarity for that case `[16]`". *Fix applied.* |
| F-08 | "Statistical validity plus a domain read, **with the domain read as final arbiter** — certifying a cluster 'requires some domain knowledge…' `[20]`" (L137-140) | `kritschgau-hypergraph` | OVERSTATED | The passage says *recognizing a cluster's themes* requires domain knowledge and is hard to verify independently. It does not make the human the **arbiter** — that is a governance decision the source does not take. | Quote as-is, then: "Making the domain read the *final arbiter* is this project's choice rather than the source's claim." *Fix applied.* |
| F-09 | "with ~30 objects **there is no setting that separates dense from sparse regions meaningfully**" (L149-153) | `hdbscan-docs` | OVERSTATED | `min_cluster_size` / `min_samples` semantics and noise labeling — all accurately quoted. But the attested HDBSCAN *limitation* is **dimensional** ("up to around 50 or 100 dimensional data"), not small-N. The small-N failure is an inference the passages do not carry, and the brief supplies no measurement for it either (see UC-05). | "Little density contrast expected at this N — author's judgment, neither sourced nor measured … treat as a prior to be checked, never as a result." *Fix applied.* |
| F-10 | "two disjoint measurements — so the trap is **largely side-stepped**" (L171-176) | `gao-selective-inference` | OVERSTATED | The quoted inflation passage is accurate. But the attestation's **next** passage — "this problem persists even if two separate and independent data sets are used to define the groups and to test for a difference in their means" — is the one passage that most directly challenges the escape argument, and the brief neither quotes nor rebuts it. Job (c): a smoothed contradiction. | State the distinction the argument actually rests on: disjoint **variables**, not disjoint **samples**, and quote the caveat while distinguishing it. *Fix applied — the argument survives, but it now shows its work.* |
| F-11 | "**require** stability above 0.9 under perturbation `[18]`" (L278-279) | `cluster-stability-review` | OVERSTATED | "Yu et al. (2019) **suggest** using stability values above 0.9 for the selection of k" — one cited study's suggestion for a k-selection procedure, reported in a review, converted here into a requirement stated in the review's own voice. | "…above 0.9 — the value Yu et al. (2019) *suggest* for selecting k, as reported by `[18]`". *Fix applied.* |
| F-12 | "the failure **the literature predicts** when a statistical criterion is allowed the final word `[20]`" (L302-303) | `kritschgau-hypergraph` | OVERSTATED | One documented instance (MDL picked 3, "5 is in some sense the 'obvious' number"). An observation in one study, not a predictive law. The specific *colour-artifact* form the brief invokes appears only in the attestation's unquoted Summary. | "…the same failure the closest published study hit … its information criterion picked a cluster count that disagreed with the 'obvious' one `[20]`". *Fix applied.* |
| F-13 | "complete pooling 'gives identical estimates for all counties, **which is particularly inappropriate for this application**' `[1]`" (L313-315) | `superarchetype-gelman-multilevel` | OVERSTATED | Verbatim accurate, but "this application" indexes Gelman's radon study, "whose goal is to identify the locations in which residents are at high risk". The brief transplants the verdict without naming the referent, implying generality. Job (e): the quote is accurate, the frame carries a qualifier the source's context held. | Name the referent — and the transplant is legitimate, because the best-call page's goal *is* to identify which specific opponents are extreme. *Fix applied.* |
| F-14 | "which **happens** 'when there are large differences in the number of at bats' `[10]`. **That is not hypothetical here — see §6.3.**" (L316-318) | `superarchetype-simpsons-paradox` | **MISATTRIBUTED** | Two defects. (a) Modality: the source says the phenomenon "**can occur** when…", the brief says "happens". (b) **§6.3 does not exhibit Simpson's paradox.** The pooled 66.7% lies *between* the members' 30.8% and 82.8% — that is a dominance-weighted average, not a reversal. The Simpson's citation is carried into an example that does not instantiate it. | "…which the article says '**can occur** when there are large differences in the number of at bats between the years' `[10]` … The *exposure condition* is not hypothetical: §6.3 shows one member supplying 69% of a pooled cell's n. A completed reversal has not yet been observed in this corpus." *Fix applied.* |
| F-15 | "**Shrinking many noisy estimates toward a common centre lowers total error** whenever three or more quantities are estimated jointly `[3]`" (L372-374) | `superarchetype-james-stein` | OVERSTATED | The dominance result is a property of **the James-Stein estimator specifically** ("the James–Stein estimator has a lower mean squared error than the 'ordinary' least squares estimator for all θ"), under its stated conditions. It is not a theorem about shrinkage in general — an arbitrary shrinkage toward an arbitrary centre carries no such guarantee. | "The James-Stein estimator dominates least squares in *total* MSE whenever three or more parameters are estimated jointly `[3]` … though that dominance result is a property of *that estimator*, not of shrinkage in general." *Fix applied.* |

---

## 3. UNCITED-CRITICAL — load-bearing claims carrying no citation that need one

| # | Claim (line) | Why it is load-bearing | Disposition |
|---|---|---|---|
| **UC-01** | "**no single member supplies more than 60% of n**" (L440, L64) | A hard gate parameter. It has **no source, no measurement, and no stated calibration** — the "calibrated on measured data" paragraph beneath it calibrates only `m_eff >= 2.0` (median HHI 0.500, 46% exceed). It is not decorative: at K=2 it is slack (60/40 → `m_eff` 1.92, already fails the concentration gate), but at **K>=3 it is the binding constraint** (60/20/20 → `m_eff` 2.27, passes `m_eff`, fails only the cap). | Labeled as uncalibrated and flagged for re-derivation from the measured member-share distribution before shipping. *Fix applied.* |
| **UC-02** | "**the resampling is over features, not over the objects being clustered**" (L275-277) | This single sentence is the *entire* justification for AU p-values working at N≈30 — the brief's answer to its hardest validation question. It sits inside a pvclust bullet and reads as sourced. The attestation asserts it **only in its unquoted Summary**; no Key passage bears on the resampling axis. Job (h): substantively thin. | Labeled as this brief's design decision with an explicit instruction to confirm against pvclust's documentation before implementing. *Fix applied.* |
| **UC-03** | "Estimate `tau^2` by the **DerSimonian-Laird method of moments**" (L350-353) | An implementer cannot compute `tau²` from what is attested. The corpus supplies `Q` and the *definition* of `tau²`; the DL estimator expression appears nowhere. Everything downstream (`w*_k`, `n_eff`, the §4.5 prior strength, both gates) depends on it. | The expression `tau² = max(0, (Q − (K−1)) / (Σw_k − Σw_k²/Σw_k))` written into §4.3 with an explicit note that it is **not attested here** and must be pinned against a primary reference. *Fix applied.* |
| **UC-04** | "When `tau² = 0` this **returns `Σ n_k`** (the honest full pooled sample)" (L385-386) | Uncited derivation, and **not exactly true**. `taû² = 0` under DL means `Q <= K−1` — dispersion below what chance explains — **not** that member rates coincide. When rates differ, `Σ n_k p̂_k(1−p̂_k) <= Σ n_k · p̄(1−p̄)` by concavity, so `n_eff < Σ n_k` even at `taû² = 0`. Separately, the continuity correction can push the raw expression slightly *above* `Σ n_k` (hence the existing clamp, which is correct). | Corrected to state both conditions, with the concavity reason, and the note that **the error direction is safe** — `n_eff` is never more generous than the raw pooled count, so the gate is stricter than the brief claimed, not looser. *Fix applied.* |
| **UC-05** | "HDBSCAN does not transfer: at ~30 cluster-defining archetypes **there is no density contrast**" (frontmatter key_finding 3; L149-153) | Stated as a finding in the frontmatter, in a brief where every other comparative claim carries a "Measured:" prefix and a number (TF-IDF fuses 14 of 30; cophenetic 0.916 vs 0.887; co-membership 0.957/0.972). This one carries **no measurement at all** — no "HDBSCAN assigned N of 30 to noise". It reads as measured by adjacency. | Frontmatter and body both narrowed: reason (b), the noise-class coverage failure, is stated as carrying the decision on its own (and it is genuinely sourced); reason (a) is labeled author's judgment. **The algorithm choice is unaffected.** *Fix applied.* |
| **UC-06** | "Both bounds are **project-grounded rather than arbitrary**" — the Beta clamp `[5, 30]` (L406-414) | The ceiling genuinely is grounded (30 = `DISPLAY_GATE_N`, verified `matchup.py:45`). The **floor of 5 has a stated intent but no calibration** — no source, no measurement, no comparison against the existing `SHRINK_STRENGTH = 15` (verified `matchup.py:43`). "Both bounds" overstates by exactly one bound. | Split: ceiling grounded, floor labeled chosen and flagged for validation against `SHRINK_STRENGTH = 15`. *Fix applied.* |
| **UC-07** | "**Q/I-squared require** at least two members with **n>=5**" (L496-498) | Presented as a property of the statistics. `K >= 2` is definitional; **`n >= 5` is the author's rule** and gates whether any heterogeneity claim may be made at all. | "Q and I-squared are undefined below two members; we additionally require each of those members to have n>=5 (author's rule…)". *Fix applied.* |
| **UC-08** | "Restricted-maximum-likelihood estimation of `tau²` is **more accurate than** DerSimonian-Laird" (L694-695) | An uncited comparative between two named estimators, stated flatly. Non-load-bearing (it sits in the out-of-scope long-tail section) but it is exactly the shape job (b) hunts. | Hedged to "commonly reported as less biased … (**not attested in this corpus** — verify before relying on the comparison)". *Fix applied.* |
| **UC-09** | Cophenetic correlation as a validity index (L231-235, L245-247) | Introduced, given four numeric values, and assigned a role ("regression tripwire") with **no source and no definition**. Mitigated by the brief explicitly *demoting* it ("never as the arbiter between representations") — which is the honest move — so this is non-critical. | "Measured on this corpus:" prefix added to the §3.2 first mention (§3.3's was already labeled). No source added; the demotion carries it. *Fix applied.* |

---

## 4. Coherence and cross-reference findings (job c) — and codebase verification

### 4.1 The one finding that is not presentational

**§4.5 inverts §6.4's own rule.** §4.5 reads `taû² = 0` as "coherent cluster" and awards the
**maximum** prior strength (clamped 30). §6.4 establishes — correctly, and from three quoted
passages — that at these member sizes `I² = 0` mostly means *"we cannot see heterogeneity"*, not
*"there is none"*, and instructs that a low value is "never a certificate of exchangeability".
`taû² = 0` and `I² = 0` are the same event under DL (both hold iff `Q <= K−1`), and the brief
measures it on **58.7% of poolable cells**.

So the prior-strength derivation hands maximum influence to the majority of cells precisely where
the brief's own honesty analysis says the evidence is weakest. The one-sided-evidence discipline was
applied to the display gate and not carried into §4.5.

This is a **design** defect, not a sourcing one, and it is the only finding in this audit that
should change behaviour rather than wording. A paragraph was added to §4.5 instructing that the
ceiling be conditioned on the cell having had power to detect spread (reusing §6.2's
`>= 2 members with n >= 5` computability floor), falling back toward the floor otherwise. Whether
that is the right correction is `epic-design`'s call; that it needs *a* correction is this audit's
finding.

### 4.2 Lesser coherence notes (all fixed)

- **§6.3 vs §4.4.** "The pooled cell clears `DISPLAY_GATE_N`" is true only of *raw* pooled n; §4.4's
  rule is that the gate reads `n_eff`, which at `I² = 0.89` would also refuse the cell. The brief's
  own best mechanism was invisible in its own showcase example. Qualified to "on raw pooled n", and
  the `n_eff` refusal added as a fourth bullet (no number invented — flagged "exact value not
  computed here").
- **§4.1 → §6.3.** Covered as F-14: §6.3 demonstrates dominance, not a Simpson's reversal.
- **§10 dependency contrast.** "No new heavyweight dependency, in contrast to the camp layer's
  `hdbscan`/`umap-learn`" overstates the contrast. Verified: `hdbscan` is **not** in
  `pyproject.toml`; the camp layer clusters with `sklearn.cluster.HDBSCAN`
  (`analytics/discovery.py:494,583`), a core dep, and `umap-learn` is an optional extra, lazily
  imported (`discovery.py:296-299`). Corrected.

### 4.3 Codebase assertions — all verified

Every internal claim the brief makes about the codebase checks out at source, which matters because
the integration recommendation ("no new gate machinery") rests on them:

| Brief claim | Verified at |
|---|---|
| `SHRINK_STRENGTH = 15` | `src/legacy_engine/analytics/matchup.py:43` |
| `DISPLAY_GATE_N = 30` | `src/legacy_engine/analytics/matchup.py:45` |
| `build_mirror_cell` sets fixed 0.5 and no CI | `matchup.py:181-200` (`p_raw=0.5`, `ci_low=None`, `ci_high=None`) |
| `_camp_hierarchy_inputs`, `_cell_prior`, `build_adaptive_matrix`, `beta_binomial_shrink_to` exist | `matchup.py:208, 288, 765, 75` |
| `tier_for_sample()` exists | `src/legacy_engine/confidence.py:34` |
| Chain is camp cell → leave-camp-out parent → shrunk marginal | `_cell_prior` docstring, `matchup.py:288-315` |
| `scipy` already a core dep | `pyproject.toml:13` (`scipy>=1.11`) |
| `analytics/discovery.py` owns the discovery pipeline shape | file present, 35 KB |

### 4.4 Jobs that surfaced nothing (silence is a finding)

- **Job (d), noise-domination / relevance-weighting.** No case found where a less-relevant source was
  cited while a more-relevant attestation went uncited. Two attested passages are *under*-used rather
  than mis-used, both of which would **strengthen** the brief: `superarchetype-meta-pooling`'s "it is
  therefore conventional to **always** use a random-effects model", and `kritschgau-hypergraph`'s note
  that statistical criteria tend to converge on *colour identity* rather than strategy — which is
  precisely §3.1's measured finding. Neither is a defect. (The kritschgau colour observation lives in
  the attestation Summary only, so it cannot be cited as a passage.)
- **Job (f), analytical-tier inheritance.** One instance (F-07, the camp brief's copy-count finding
  wearing a Bray-Curtis citation), now labeled. No `intra-program-resolved` handles in this brief —
  all 21 resolve to real attestations.
- **Job (g), line/section-reference walk.** The brief cites no section/¶ anchors; nothing to check.
- **Arithmetic spot-check of the worked example (§6.3).** Fully self-consistent: 4/13 = 30.8%,
  24/29 = 82.8%, 28/42 = 66.7%, HHI = (13/42)² + (29/42)² = 0.573, `m_eff` = 1.75, top share 0.690,
  spread 0.520, `I² = (9.1 − 1)/9.1 = 0.89`. The §6.4 percentages are integer-consistent against
  n = 75 cells. `Aluren` vs `Show and Tell` 11/19 = 57.9%. A perfectly even four-member cluster does
  sit at HHI 0.25. No arithmetic defect found anywhere in the brief.

---

## 5. Edits applied to the brief

23 narrowing edits, all in `docs/briefs/superarchetype-aggregation.md`. **No recommendation was
weakened or removed; no number was deleted.** Every edit either relabels a project calibration as
ours, narrows a claim to what the passage carries, or adds the qualifier that makes a derivation
true. Citation count rose 83 → 89 (six added: two extra `sklearn-clustering` cites for the
single/complete linkage definitions the brief was characterising without quoting, one extra
`hdbscan-docs` cite for the dimensional limitation, one extra `gao-selective-inference` cite for the
"persists across independent datasets" caveat, one extra `superarchetype-hhi` cite in §5.2, and one
extra `superarchetype-pvclust` cite in §3.4). All 89 resolve to existing attestations — no new
attestation is required.

**Frontmatter (2):** key_finding 3 (HDBSCAN) narrowed to lead with the sourced noise-class argument
and label the density-contrast argument as author's judgment; key_finding 5 softened from "collapses
to the intuitive pooled-counts answer" to "is close to".

**§0 glance table (4):** algorithm, cut-selection, estimator, sample-gate, concentration-gate and
heterogeneity-gate rows all re-attributed so that no project-chosen threshold sits adjacent to a
citation that does not endorse it.

**§1 (1):** pvp quote marks removed from the paraphrased composition figures.

**§2 (3):** Bray-Curtis claim narrowed; kritschgau "final arbiter" re-attributed; HDBSCAN reason (a)
labeled as unmeasured judgment; gao double-dipping escape argument now quotes and distinguishes the
"persists across independent datasets" caveat.

**§3 (5):** cophenetic figures labeled "Measured on this corpus"; single/complete linkage behaviours
now quoted rather than asserted; pvclust feature-axis resampling labeled as our port with a
verify-before-implementing instruction and the single-cluster-vs-dendrogram extension made explicit;
`>= 0.95` → `> 0.95`; stability threshold re-attributed to Yu et al. as a suggestion; definer/assignee
framing corrected from "thresholds measured" to "cutoffs chosen, coverage measured"; kritschgau
"literature predicts" narrowed.

**§4 (6):** Gelman quote referent named; Simpson's modality corrected and the §6.3 cross-reference
fixed; DL estimator expression added with an explicit not-attested-here note; "IS the simple answer"
softened; James-Stein generalization narrowed to the estimator; `n_eff` at `tau² = 0` corrected with
the concavity reason and the safe-direction note; §4.5 clamp grounding split and the §6.4 coherence
paragraph added.

**§5 (2):** gate statement now says both cutoffs are ours; the 60% cap given its own paragraph
stating it is uncalibrated, that it is binding at K>=3, and that it must be re-derived.

**§6 (4):** Cochrane bands labeled rough-guide with the actions attributed to the project; `n>=5`
computability rule labeled author's; "clears `DISPLAY_GATE_N`" qualified "on raw pooled n" with the
`n_eff` bullet added; "reliable stop signal" softened to "the trustworthy direction" with the reason.

**§10 (2):** dependency contrast corrected against `pyproject.toml` / `discovery.py`; REML-vs-DL
comparative hedged and marked not-attested.

---

## 6. Does the method survive?

**Yes, without qualification on the method itself.**

- **Clustering** (staple-stripped core sets → Jaccard → average-linkage agglomerative → AU-validated
  cut) is unaffected. The two soft spots — HDBSCAN's small-N argument (UC-05) and pvclust's
  feature-axis resampling (UC-02) — are *sourcing* defects. The HDBSCAN decision survives on its
  second, genuinely sourced reason: the noise class denies a superarchetype to exactly the thin
  archetypes the epic exists to serve. The pvclust port is very likely correct on the facts; it just
  needs one confirmation read before implementation.
- **Estimator** (random-effects inverse-variance on continuity-corrected logits) is the best-sourced
  part of the brief — every formula is quoted verbatim from `superarchetype-meta-pooling` /
  `superarchetype-meta-heterogeneity`. The only gap is that the DL `tau²` expression itself must be
  pinned to a primary reference (UC-03) — a bibliography chore, not a method risk.
- **Gates.** The `n_eff` correction (UC-04) makes the sample gate *stricter* than advertised, which
  is the safe direction and consistent with the project's honesty discipline. `m_eff >= 2.0` is
  genuinely calibrated on measured data. The 60% cap (UC-01) is the one gate parameter that needs
  actual derivation before it ships — but its failure mode is a mislabeled cluster read, not a wrong
  number, and it is redundant at K=2 where most cells live.
- **The one substantive item** is the §4.5 / §6.4 inversion (§4.1 above). It should be resolved
  during `epic-design`, not by revising this brief further.

**The brief's honesty discipline is real and mostly consistent.** It voluntarily disclaims the DOJ
HHI bands, labels the spread guard as an author's engineering rule, flags the PvP paper's claimed
gain as tractability rather than accuracy, closes with an explicit "these are project measurements,
not sourced claims" note, and marks the maindeck-vs-75 recommendation as engineering judgment. The
findings above are the places that discipline lapsed — mostly in the at-a-glance table, where
compression put chosen numbers next to citations that do not carry them. That is a real defect and
worth fixing, but it is a lapse *from* an unusually high standard, not an absence of one.
