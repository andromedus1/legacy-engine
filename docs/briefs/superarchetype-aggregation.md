---
description: "How do you derive an honest win rate against a STRATEGY CLUSTER when almost no per-archetype matchup cell clears its sample gate — which clustering works at ~30-45 archetypes, which estimator pools member cells, and which gates stop pooling from smuggling in bias worse than the thin cell it replaced? Read before designing epic-superarchetype-layer."
type: brief
kind: research
slug: superarchetype-aggregation
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-31
blocks_phase: epic-superarchetype-layer
status: draft
summary: |
  Curates the method for the superarchetype (strategy-cluster) layer: clustering archetypes by card
  composition at small N, aggregating member matchup cells into one cluster cell, and gating that
  cell for representativeness and pooling validity. Grounds every choice in the real corpus (in the
  2026-05-11 window only 4 of 1190 directed archetype cells clear n>=30; opponent-side pooling into
  ~8 clusters lifts that to ~16% and to 70% of cluster-vs-cluster cells) and in the hierarchical-
  models, paired-comparison, concentration-index and meta-analysis literatures. Specifies a
  random-effects pooled estimator, an effective-member concentration gate, an I-squared
  heterogeneity gate, the intra-cluster flag rule, and the exact rung the superarchetype occupies
  in the existing camp -> leave-camp-out parent' -> marginal' -> 0.5 shrinkage chain.
key_findings:
  - "The epic's premise is confirmed and worse than stated: in the 2026-05-11 window only 4 of 1190 directed archetype-vs-archetype cells reach n>=30 (0.3%), none reach n=100, 17.8% are literally n=0, and the median cell holds 2 matches — Cradle Control's largest opponent cell is n=10 across 82 matches."
  - "Clustering must happen one level up in FEATURE space too: at the archetype level the format staples (Force of Will, Brainstorm, Ponder, Daze, Wasteland, the fetches, Underground Sea, Flow State — 14 cards that are core to >=30% of archetypes) dominate the similarity and fuse 16 of 34 archetypes into one 'blue' mega-cluster; TF-IDF's soft down-weighting is NOT enough (cosine on IDF-weighted centroids still fuses 14 of 30) — the staples must be HARD-removed, which is the format-level analogue of the camp layer's flex band."
  - "HDBSCAN should not be the primary algorithm here, on one decisive ground: any archetype pushed into the noise class gets no superarchetype at all — a coverage failure aimed precisely at the thin archetypes the epic exists to serve. (The secondary 'no density contrast at ~30 objects' argument is author's judgment — neither sourced nor measured.) Average-linkage agglomerative on a precomputed Jaccard dissimilarity assigns every archetype, and pvclust-style multiscale-bootstrap AU p-values computed over the CARD features rather than the archetypes are the proposed small-N branch validator."
  - "Coverage rises monotonically with coarser clusters and so does the risk of pooling unlike things: opponent-side pooled cells reaching n>=30 go 4.5% (K=17) -> 10.4% (K=11) -> 15.8% (K=8) -> 24.5% (K=6) -> 36.8% (K=4), and cluster-vs-cluster cells go 12.8% -> 70.3% at K=8 -> 93.8% at K=4. Granularity must be chosen by a heterogeneity criterion, never by a coverage target."
  - "Random-effects inverse-variance pooling is the estimator that self-degrades correctly: with tau-squared = 0 (58.7% of poolable cells measured exactly zero) its weights reduce to plain inverse variance, which for binomial cells is close to the intuitive pooled-counts answer, and as members disagree its weights flatten toward equality, automatically defusing the one-dominant-member problem instead of needing a separate rule."
  - "Both gates fire on the epic's own motivating pair, which is the strongest possible validation: Dimir Tempo is 4-9 (30.8%, n=13) vs Aluren and 24-5 (82.8%, n=29) vs Show and Tell; the pooled cell reads 28-14 (66.7%, n=42) and would clear the display gate, but HHI=0.573 (1.75 effective members, one member supplying 69% of n) and I-squared=0.89 both refuse it."
  - "I-squared is one-sided evidence here: median I-squared across poolable cells is exactly 0.000 and only 4.0% exceed 0.75, but Cochran's Q has low power when units are few and small, and I-squared depends on the precision of the units — so a HIGH value is a reliable stop signal while a LOW value is never proof of exchangeability."
  - "Superarchetype membership does NOT need era-scoping the way camps do: co-membership agreement across the Jan-Apr and Apr-Jul 2026 windows is 0.957 on the 26 archetypes present in both, spanning both the Flow State adoption step and the Candelabra ban. Recompute membership on the same window the matrix is sourced over, surface churn as a diagnostic, and keep cluster identity stable."
---

# Brief: Superarchetype Aggregation

## Purpose

Unblocks `epic-superarchetype-layer`. The epic's locked decisions: **data-driven clustering of
archetypes by card composition with a curated override layer** (hybrid-derived-curated-registry);
**intra-cluster matches count but carry an intra-cluster flag**; **per-cell labeled fallback** on the
best-call page (archetype cell when it clears its gate, superarchetype cell when it does not, with a
provenance chip). This brief answers the epic's five open method questions — representation and
distance, aggregation estimator, uneven coverage inside a cluster, validity of pooling, and
era-scoping — with concrete recommendations and thresholds calibrated against the real corpus. It
does **not** dictate module structure (that is `epic-design`'s job).

Read alongside `docs/briefs/subarchetype-discovery.md` (the camp layer — the same problem one level
DOWN; §2 below states exactly what transfers) and `docs/briefs/change-point-detection.md` (era
windows — §9).

---

## 0. Recommended method at a glance

| Decision | Recommendation |
|---|---|
| Representation | Per-archetype **core set** = maindeck cards at >=50% inclusion in that archetype's in-window decks, **minus format staples** (cards core to >=30% of cluster-defining archetypes) |
| Distance | **Jaccard dissimilarity** on the staple-stripped core sets `[jaccard-index]{15}` |
| Algorithm | **Average-linkage agglomerative** (linkage criterion per `[sklearn-clustering]{13}`) on the precomputed dissimilarity; every archetype gets a cluster (no noise class) |
| Cut selection | Branch-level **multiscale-bootstrap AU p-value > 0.95** `[superarchetype-pvclust]{11}`, resampling card features rather than archetypes (our port — see §3.4), cross-checked with co-membership stability `[cluster-stability-review]{18}` |
| Membership floor | Archetypes with >=30 decks and >=8 core cards may **define** a cluster; everything else is **assigned** by nearest centroid but never defines one |
| Curated layer | Curated cluster assignments win by key; derived fills gaps (hybrid-derived-curated-registry) |
| Estimator | **Random-effects inverse-variance pooled proportion** `[superarchetype-meta-pooling]{7}` on continuity-corrected logits, with `tau^2` by the DerSimonian-Laird moment estimator (§4.3) |
| Sample gate | Tier and display gate read **`n_eff`** derived from the random-effects variance, never the raw pooled n (our construction — §4.4) |
| Concentration gate | **Effective members `m_eff` = 1/HHI** `[superarchetype-hhi]{8}`, gated at **>= 2.0** with max member share **<= 0.60** — both cutoffs are ours, calibrated in §5.2; the antitrust bands deliberately do not transfer |
| Heterogeneity gate | Boundaries taken from Cochrane's rough-guide I-squared bands `[superarchetype-cochrane-heterogeneity]{5}`; the actions are ours — **<= 0.40** pool freely; **0.40-0.75** pool with a `heterogeneous pool` label; **> 0.75** refuse the pooled number and show the member split |
| Intra-cluster | Sibling matches **count**, flagged; exact self-mirror excluded from the rate but its n reported |
| Chain position | New rung **between** the leave-camp-out parent cell and the subject marginal, computed **leave-opponent-out** |
| Era scoping | Recompute membership per window; do **not** era-partition the taxonomy |

---

## 1. The problem in data terms (measured)

All figures below are measured on the corpus on 2026-07-31 over the current advisory window
`[2026-05-11, 2026-07-30]` unless stated otherwise.

**The field is long-tailed.** 5,233 decks carry 183 distinct archetype labels. Only 14 labels hold
>=2% field share, 25 hold >=1%, 33 hold >=0.5%, and 46 hold >=0.25%. This is the "small N" that
governs every clustering choice below: the camp layer clusters hundreds-to-thousands of *decks*
inside one parent; the superarchetype layer clusters a few dozen *archetypes*.

**The matchup matrix is essentially empty.** Over the 35 rows that clear `min_row_share=0.005`,
there are 1,190 directed non-mirror cells:

| Measure | Value |
|---|---|
| Cells reaching `DISPLAY_GATE_N` (n>=30) | **4 (0.3%)** |
| Cells reaching established tier (n>=100) | **0** |
| Cells with n = 0 | 212 (17.8%) |
| Median cell n | **2** |

Per-row it is starker: the four qualifying cells belong to Show and Tell, Izzet Delver, Blue
Artifacts and Dimir Tempo — one each. **Thirty-one of thirty-five ranked archetypes have zero
displayable matchup cells.** The epic's headline cases check out: `Cradle Control` has 104 marginal
matches, 82 of them against ranked opponents, and its largest single opponent cell is **n=10**;
`Aluren` has 135 marginal matches, 118 against ranked opponents, largest cell **n=19**.

This is not a presentation problem and no honesty gate can fix it. Every mechanism the project has
built makes the thinness *legible*; only adding a level that borrows information across entities
makes it *smaller*. That is precisely the structural argument for a group level: a no-pooling model
"does not allow a county's radon level to be estimated using data from other counties"
`[superarchetype-gelman-multilevel]{1}`, so it cannot even be cross-validated at the group level —
while partial pooling "gives more accurate predictions than the no-pooling and complete-pooling
regressions, especially when predicting group averages" `[superarchetype-gelman-multilevel]{1}`.

**The closest published analogue does exactly this.** A 2024 study of PvP team-composition balance
faces the same combinatorics — in their League of Legends data the maximum possible compositions
reaches 359,933,112 while only 348,498 unique compositions actually appeared, making the full
pairwise table unbuildable — and its remedy is structurally identical to this epic: "we propose a more manageable
M×M counter table that serves as an approximation of the full N×N relationships, where M represents
a manageable number of discrete categories" `[superarchetype-pvp-counter-clustering]{12}`. Note what
that paper claims and does not claim: its stated gain is tractability ("reduces the space complexity
of analyzing strength relations for N compositions from O(N²) to O(N+M²)"
`[superarchetype-pvp-counter-clustering]{12}`), not estimation accuracy under sparse samples. The
accuracy argument has to come from the hierarchical-models side (§4), not from this precedent. The
same paper supplies the reason the grouped object must stay a *table* rather than collapsing to a
rating: "The phenomenon of cyclic dominance or intransitivity of win values, a common challenge in
analyzing game balance, introduces further complications"
`[superarchetype-pvp-counter-clustering]{12}`.

---

## 2. What transfers from the camp layer — and what does not

`docs/briefs/subarchetype-discovery.md` solved the same shape one level down. The transfer is
partial, and the parts that do *not* transfer are the ones that will silently produce a wrong
taxonomy.

### Transfers unchanged

- **Strip the signal-free band before measuring similarity.** The camp brief's core insight — the
  ubiquitous chassis carries zero split signal because it is present in everything — is the single
  most load-bearing idea here (§3.1), but the band is defined at a different level.
- **Copy counts and abundance-aware distances matter where a split is a quantity difference** (the
  camp brief's own finding); Bray-Curtis is the abundance-aware dissimilarity for that case
  `[bray-curtis]{16}`, and cosine on sparse vectors is cheap because "only the non-zero coordinates
  need to be considered" `[cosine-similarity]{17}`.
- **Two-gate validation.** Statistical validity plus a domain read — recognizing a cluster's theme
  "requires some domain knowledge, and is therefore, hard to verify independently"
  `[kritschgau-hypergraph]{20}`. Making the domain read the *final arbiter* is this project's
  choice rather than the source's claim, and it is why the epic's **curated override layer** is not
  optional (§3.5).
- **Co-membership stability as the resampling check**: "If the clustering is stable, then the
  clusters from the original data will be preserved in the perturbed data clustering"
  `[cluster-stability-review]{18}`.
- **The MTG deck-clustering precedent** (Jaccard over deck-card sets, then density clustering,
  then human validation) `[luckypaper-commander-map]{21}`.

### Does NOT transfer

- **HDBSCAN as the primary algorithm.** Two reasons, of unequal strength. (a) *Little density
  contrast expected at this N* — **author's judgment: neither sourced nor measured.** HDBSCAN's
  parameters are defined relative to a population — `min_cluster_size` is "the smallest size
  grouping that you wish to consider a cluster" and larger `min_samples` means "more points will be
  declared as noise" `[hdbscan-docs]{14}`; with ~30 objects the band of settings that could separate
  dense from sparse regions is narrow. But the *attested* HDBSCAN limitation is dimensional (it
  "can do well on up to around 50 or 100 dimensional data") `[hdbscan-docs]{14}`, not small-N, so
  treat (a) as a prior to be checked, never as a result. (b) *The noise class is a coverage bug
  here* — this reason carries the decision on its own.
  A deck that HDBSCAN calls noise inside a parent is genuinely a brew and losing it costs nothing;
  an **archetype** that HDBSCAN calls noise gets **no superarchetype at all** — and it will be a
  thin, unusual archetype, i.e. exactly the row the epic exists to give coverage to. Use a method
  that assigns every object: agglomerative clustering recursively merges pairs under a linkage
  criterion (Ward / complete / average / single) `[sklearn-clustering]{13}` and terminates with
  every object placed.
- **TF-IDF soft down-weighting as the de-staple mechanism.** Measured: cosine on IDF-weighted
  per-archetype centroid copy-count vectors still fuses **14 of 30** archetypes into one blue
  mega-cluster (Aluren, Azorius Midrange, Azorius Stoneblade, Cephalid Breakfast, the four Dimir
  labels, Doomsday, both Izzet labels, Jeskai Midrange, Show and Tell, White Beanstalk). IDF is a
  weight, not a removal, and four Brainstorms plus four Force of Wills plus eight fetchlands
  dominate the L2 norm regardless. **The staples must be hard-removed** (§3.1).
- **Clustering inside a color-fixed parent.** The camp brief could largely dismiss the
  color-confound risk because discovery runs within an already-color-consistent parent. At the
  superarchetype level there is no such pre-emption, and the confound is the dominant failure mode
  (§3.1). This is the concrete instance of the warning that a statistical cluster criterion can
  disagree with the human-intuitive archetype count `[kritschgau-hypergraph]{20}`.
- **The double-dipping hazard, in its camp-level form.** The camp layer risked forming groups from
  a table and then testing outcome differences on the same table, where "applying a classical test
  yields an extremely inflated type I error rate" `[gao-selective-inference]{19}`. Here the
  clustering input is **decklist composition** (`deck_cards`) and the evaluation target is **match
  outcomes** (`rounds`) — two disjoint *measurements*, not merely two disjoint samples. That
  distinction is what carries the argument, and it must be stated because the same source warns the
  inflation "persists even if two separate and independent data sets are used to define the groups
  and to test for a difference in their means" `[gao-selective-inference]{19}`: a fresh sample of
  the *same* variables buys no escape, only a different variable does. Under that reading the trap
  is largely side-stepped. It returns the moment anyone tunes the dendrogram cut to maximize coverage or minimize I-squared on
  the same match data the cells are drawn from. **Fix the cut on composition evidence alone**
  (§3.4) and treat the outcome-side statistics purely as gates, never as objectives.

---

## 3. Clustering ~30-45 archetypes

### 3.1 Representation — strip the format staples, not the parent chassis

Build one row per archetype. The unit is the archetype's **core set**: maindeck cards appearing in
>=50% of that archetype's in-window decks (the same "core" the epic's own Aluren/Show-and-Tell
worked example used). Then remove the **format staples**: cards that are core to >=30% of the
cluster-defining archetypes.

Measured on the current window, that staple list is exactly 14 cards:

> Brainstorm, Daze, Flooded Strand, Flow State, Force of Will, Island, Lotus Petal, Misty
> Rainforest, Polluted Delta, Ponder, Scalding Tarn, Thoughtseize, Underground Sea, Wasteland

**This step is the difference between a taxonomy and a color chart.** With the staples left in,
average-linkage on core-Jaccard produces a single cluster containing 16 of 34 archetypes — Aluren,
Azorius Midrange, Azorius Stoneblade, Cephalid Breakfast, Dimir Death's Shadow, Dimir Delver, Dimir
Midrange, Dimir Tempo, Doomsday, Grixis Midrange, Izzet Delver, Izzet Midrange, Jeskai Midrange,
Show and Tell, Stiflenought, White Beanstalk — i.e. "plays blue". With them removed at the 30%
threshold, the same algorithm returns interpretable families and, notably, **recovers the epic's
motivating pair `Aluren` + `Show and Tell` as its own branch without being told to**.

Note the exact correspondence to the camp layer: there, the signal-free band is the *parent's*
ubiquitous core; here it is the *format's* ubiquitous core. Same idea, one level up, and it must be
recomputed at the format level or it does nothing.

**Maindeck vs full 75.** Measured: repeating the whole pipeline with `main+side` instead of
maindeck-only changes almost nothing — co-membership agreement is **0.972** at K=8 across the 30
common archetypes (the visible difference is Red Stompy relocating from the Show-and-Tell branch to
the artifact/stompy branch, which is arguably an improvement). Recommend **maindeck-only as the
default** — it is the cheaper, more stable signal and sideboards encode what a deck expects to
*fight* rather than what it *is* (author's engineering judgment; the 0.972 agreement is measured).
Keep main+side as a one-line ablation.

**Copy counts.** Unlike the camp layer, copy counts are *not* needed here: superarchetype splits are
package-level ("does it run the Show and Tell engine"), not quantity-level ("3.70 vs 0.98 Tamiyo").
Set-valued cores are sufficient and are what the measured results above use. If a future case
demands abundance, Bray-Curtis is the right dissimilarity — but it "is not a distance since it does
not satisfy triangle inequality" `[bray-curtis]{16}`, so it must be fed to agglomerative or k-medoids,
never to a metric-assuming method.

### 3.2 Distance — Jaccard on the stripped cores

`J(A,B) = |A∩B|/|A∪B|` `[jaccard-index]{15}` over the staple-stripped core sets, used as the
dissimilarity `1 - J`. This is the metric the epic's own worked example already speaks in (core
Jaccard 0.54 for Aluren vs Show and Tell), it is the choice of the closest MTG prior art
`[luckypaper-commander-map]{21}`, and it is directly auditable — a human can read the shared and
disjoint core cards behind any pairwise number.

**Caution on internal validity indices.** Measured on this corpus: the cophenetic correlation of the
recommended Jaccard/average clustering is 0.916 (complete linkage 0.887), while TF-IDF-cosine/average
scores **higher** at 0.944 — despite producing the useless 14-member blue mega-cluster. An internal index
happily rewards a clean hierarchy over a wrong one. Use cophenetic correlation as a regression
tripwire on method changes, never as the arbiter between representations.

### 3.3 Algorithm — average-linkage agglomerative

Average linkage "minimizes the average of the distances between all observations of pairs of
clusters" `[sklearn-clustering]{13}`, which is the right behaviour for package-overlap data where a
family is defined by broad mutual similarity rather than by a single nearest neighbour — single
linkage "minimizes the distance between the closest observations of pairs of clusters"
`[sklearn-clustering]{13}`, so one shared card can bridge two families — or by the worst pair, since
complete linkage "minimizes the maximum distance between observations of pairs of clusters"
`[sklearn-clustering]{13}` and fragments more here (measured cophenetic 0.887). It accepts a
precomputed dissimilarity matrix (`scipy.cluster.hierarchy.linkage` over a condensed matrix), so
Jaccard feeds it directly, and it assigns every archetype.

Measured linkage comparison on the staple-stripped cores: average gives cophenetic 0.916 with clean
family structure; complete gives 0.887 and fragments more; Ward is not applicable to a precomputed
non-Euclidean dissimilarity and scored 0.609 when forced.

### 3.4 Cut selection and validation at N≈30

The cut height is the one free parameter, and coverage pressure will push it upward. **Measured
coverage as a function of granularity** (opponent-side pooled cells reaching n>=30, and
cluster-vs-cluster cells reaching n>=30):

| Cut | K | Cluster sizes (top) | Subject×cluster cells n>=30 | Cluster×cluster cells n>=30 |
|---|---|---|---|---|
| 0.86 | 17 | 7, 6, 3, 3, 2, 2 | 26/578 (4.5%) | 37/289 (12.8%) |
| 0.90 | 11 | 8, 8, 4, 3, 2, 2 | 39/374 (10.4%) | 37/121 (30.6%) |
| **0.93** | **8** | 8, 8, 4, 4, 3, 3, 2, 2 | **43/272 (15.8%)** | **45/64 (70.3%)** |
| 0.95 | 6 | 10, 8, 7, 4, 3, 2 | 50/204 (24.5%) | 33/36 (91.7%) |
| 0.97 | 4 | 14, 9, 8, 3 | 50/136 (36.8%) | 15/16 (93.8%) |

Coverage is monotone in coarseness. **Therefore coverage cannot be the selection criterion** — it
selects K=1. Select the cut from **composition evidence only**, then let the §5/§6 gates decide
which cells are usable:

- **Primary — branch support by multiscale bootstrap.** Compute an AU (approximately unbiased)
  p-value per dendrogram branch by resampling the *card feature vocabulary*, recomputing the
  Jaccard matrix, and re-clustering. "For a cluster with AU p-value > 0.95, the hypothesis that 'the
  cluster does not exist' is rejected with significance level 0.05... these highlighted clusters
  does not only 'seem to exist' caused by sampling error, but may stably be observed if we increase
  the number of observation" `[superarchetype-pvclust]{11}`. AU is preferred over the plain
  bootstrap probability because it "is a better approximation to unbiased p-value than BP value
  computed by normal bootstrap resampling" `[superarchetype-pvclust]{11}`. **The critical detail for
  small N: resample the card-feature vocabulary, not the archetypes being clustered** — with ~30
  archetypes but hundreds of core cards, the bootstrap has plenty to work with. *Sourcing note:* the
  attestation for `[superarchetype-pvclust]{11}` carries the AU interpretation rule but no passage
  on the resampling axis, so the feature-axis port is this brief's design decision — confirm it
  against pvclust's own documentation before implementing. The source states its rule for a *single*
  cluster, so applying it across a whole dendrogram is a further extension of ours: accept the
  deepest cut at which every retained branch has AU > 0.95, and record that no multiplicity
  correction is applied across branches.
- **Secondary — co-membership stability.** Represent the clustering as a binary co-membership matrix
  and require stability above 0.9 under perturbation — the value Yu et al. (2019) *suggest* for
  selecting k, as reported by `[cluster-stability-review]{18}`.
- **Sanity band.** The measured K=8 cut (0.93) is the operating point the rest of this brief uses,
  and it happens to sit where cluster sizes stay under ~8 members. Treat K in roughly 6-12 as the
  plausible band and let the AU criterion pick inside it.

### 3.5 Archetypes too small to cluster, and the curated override

Two distinct populations, two rules (author's integration design; the cutoffs below are *chosen*,
the coverage figures beside them are *measured*):

- **Definers** — >=30 decks in window AND >=8 core cards. Measured: **30 archetypes, covering 83.7%
  of the field.** Only these enter the distance matrix and the dendrogram. This keeps a 4-deck brew
  from inventing a branch.
- **Assignees** — everything else with >=5 core cards. Measured: **182 archetypes, covering 98.3% of
  the field, with zero archetypes unassignable.** Assign by nearest cluster centroid over the
  staple-stripped cores. An assignee inherits a cluster but never defines one, and its provenance
  says `assigned` rather than `derived`.

**The curated override layer is required, and the data says exactly why.** The derived K=8
clustering is right about the headline families (Aluren + Show and Tell; Dredge + Oops! All Spells;
Mystic Forge Combo + Post + Tron; Cradle Control + Golgari Landfall + Smallpox + Lands; Izzet Delver
+ Izzet Midrange; Blue Artifacts + Painter) and wrong in identifiable, chassis-driven ways: Doomsday
lands with the fair Dimir decks, Cephalid Breakfast with the fair Azorius decks, Grixis Reanimator
with TES, and (maindeck-only) Red Stompy with Show and Tell. Every one of those is a residual
shell/color artifact, i.e. the same failure the closest published study hit when a statistical
criterion was allowed the final word — its information criterion picked a cluster count that
disagreed with the "obvious" one `[kritschgau-hypergraph]{20}`. Curated entries win by key; derived fills gaps
(hybrid-derived-curated-registry). Each curated override should record the derived assignment it
overrode so the divergence is auditable rather than invisible.

---

## 4. The aggregation estimator

### 4.1 Why not pooled raw counts

Summing member wins and losses is complete pooling within the cluster, and complete pooling "gives
identical estimates for all counties, which is particularly inappropriate for this application"
`[superarchetype-gelman-multilevel]{1}` — Gelman's application being one whose goal is to identify
*which specific groups* are extreme, which is exactly the best-call page's goal. Worse, at unequal
member exposure it is exposed to the named reversal: a trend "appears in several groups of data but
disappears or reverses when the groups are combined", which the article says "can occur when there
are large differences in the number of at bats between the years"
`[superarchetype-simpsons-paradox]{10}` — here, large differences in member match counts. The
*exposure condition* is not hypothetical: §6.3 shows one member supplying 69% of a pooled cell's n.
A completed reversal has not yet been observed in this corpus.

### 4.2 Why not a Bradley-Terry model with a group random effect

The paired-comparison literature's own answer to "put a level above competitors" is a structured
Bradley-Terry model: replace each competitor's free ability parameter with a linear predictor over
competitor-level covariates plus a random effect, where "the inclusion of the prediction error Uᵢ
allows for variability between players with equal covariate values and induces correlation between
comparisons with a common player" `[superarchetype-bradley-terry2]{4}`; the result "is then a
generalized linear mixed model, which the BTm function currently fits by using the penalized
quasi-likelihood algorithm of Breslow and Clayton" `[superarchetype-bradley-terry2]{4}`.

**Recommend against it for v1**, for a reason specific to this domain rather than to convenience.
Bradley-Terry assumes "the odds that i beats j are αᵢ/αⱼ" `[superarchetype-bradley-terry2]{4}` — a
single ability scalar per competitor, hence a transitive ordering. A metagame is the canonical
intransitive system: "cyclic dominance or intransitivity of win values" is "a common challenge in
analyzing game balance" `[superarchetype-pvp-counter-clustering]{12}`. A BT fit would smooth away the
rock-paper-scissors structure that the matchup matrix exists to expose, and it would replace an
auditable cell (here are the 42 matches) with a model coefficient. Keep BT filed as the parametric
alternative if a future surface needs a full dense matrix; it is not the right first move for a
cell-level, per-number-auditable page.

### 4.3 Recommended — random-effects inverse-variance pooling

Treat each member archetype's cell as one "study" of the subject's win rate against that strategy
family, and pool them the way meta-analysis pools studies.

**Step 1 — per-member effect and variance.** For member k with `wins_k` in `n_k` matches, use the
continuity-corrected logit `y_k = log((w_k + 0.5)/(n_k - w_k + 0.5))` with
`v_k = 1/(w_k + 0.5) + 1/(n_k - w_k + 0.5)`. The correction is mandatory at these counts — 0-for-3
cells are routine and the raw logit is undefined.

**Step 2 — between-member variance.** Estimate `tau^2` by the DerSimonian-Laird method of moments
from Cochran's Q, where `Q = Σ w_k (θ̂_k − θ̂)²` with inverse-variance weights
`[superarchetype-meta-heterogeneity]{6}`; `tau^2` "quantifies the variance of the true effect sizes
underlying our data" `[superarchetype-meta-heterogeneity]{6}`. *Sourcing note:* the DL moment
estimator itself — `tau² = max(0, (Q − (K−1)) / (Σw_k − Σw_k²/Σw_k))` — is **not** attested in this
corpus; the sources here supply `Q` and the *definition* of `tau²`, not the estimator. Pin the exact
expression against a primary reference at implementation time.

**Step 3 — pool.** Weight `w*_k = 1/(s²_k + tau²)` `[superarchetype-meta-pooling]{7}` and take the
weighted mean `θ̂ = Σ θ̂_k w_k / Σ w_k` `[superarchetype-meta-pooling]{7}`; map back to a probability.

**Why this estimator and not a simpler one.** It has exactly the self-degrading behaviour this
project's honesty discipline demands, and it gets it for free rather than by a bolted-on rule:

- **When members agree it is essentially the simple answer.** With `tau² = 0` the weights reduce to
  plain inverse variance, which for binomial cells is close to size weighting — near enough to the
  intuitive pooled-counts number to be explainable (the continuity correction and the logit scale
  keep it from being exactly equal). Measured: **58.7% of poolable cells have I-squared exactly 0.000** (§6), so
  the majority of cells get the obvious answer and nobody has to defend a black box.
- **When members disagree it automatically stops trusting the biggest one.** Adding `tau²` to every
  denominator compresses the weight ratio between a large member and a small one, so a random-effects
  pool "pays more attention to small studies" `[superarchetype-meta-pooling]{7}`. The dominant-member
  problem is dampened by the estimator itself, before the §5 gate is even consulted.
- **It matches the field's own default.** Fixed-effect pooling is defensible only "when we could not
  detect any between-study heterogeneity **and** when we have very good reasons to assume that the
  true effect is fixed" `[superarchetype-meta-pooling]{7}` — a bar a metagame cluster cannot clear.
- **It is the same shrinkage logic already in the codebase.** The James-Stein estimator dominates
  least squares in *total* MSE whenever three or more parameters are estimated jointly, even
  substantively unrelated ones `[superarchetype-james-stein]{3}` — the formal precedent for
  shrinking a thin cell toward its group, though that dominance result is a property of *that
  estimator*, not of shrinkage in general. It carries the caveat the project must respect in its UI: the
  guarantee is on total risk and "any particular component... would improve for some parameter
  values, and deteriorate for others" `[superarchetype-james-stein]{3}`. Hence the raw member split
  must remain reachable behind every pooled number.

### 4.4 The sample gate must read effective n, not pooled n

This is the load-bearing integration move. A pooled cell must not buy its way past
`DISPLAY_GATE_N = 30` by stacking members that disagree.

Define `n_eff = 1 / (Var(θ̂) · p̄(1 − p̄))`, where `Var(θ̂) = 1/Σ w*_k` is the random-effects variance
on the logit scale and `p̄` the pooled probability; clamp `n_eff <= Σ n_k` (the continuity
correction can otherwise nudge it a point or two above the true total). **This construction is the
author's, not a sourced formula.** When `tau² = 0` **and** the members' observed rates coincide it
returns `Σ n_k` — the honest full pooled sample. When members' rates differ it sits *below* `Σ n_k`
even at `tau² = 0`, because `Σ n_k p̂_k(1−p̂_k) <= Σ n_k · p̄(1−p̄)` by concavity; it falls further as
heterogeneity grows. The direction of that error is the safe one: `n_eff` is never more generous
than the raw pooled count. Feed
`n_eff` to the existing `tier_for_sample()` and to the existing `display` gate — **no new gate
machinery, just a more honest argument**. This is the same discipline as the survey-sampling design
effect, where "n_eff = n/deff" discounts nominal sample for unequal contribution
`[superarchetype-kish-deff]{9}`.

### 4.5 Setting the prior strength from the group-level variance

When the superarchetype cell is used as a **prior** (§8) rather than as a displayed value, it needs
a strength, and `SHRINK_STRENGTH = 15` is a constant that knows nothing about how coherent the
cluster is. The hierarchical-modelling rule is explicit: "The more variable the (estimate of the)
population, the less pooling is applied" `[superarchetype-stan-pooling]{2}`, because "a hierarchical
model introduces an estimation bias toward the population mean and the stronger the bias, the less
variance there is in the estimates for the units" `[superarchetype-stan-pooling]{2}`.

Recommend deriving the strength by moment-matching a Beta prior to the pooled mean `μ` and the
between-member variance mapped to the probability scale
(`tau²_p = tau² · (μ(1−μ))²`):

```
s = μ(1 − μ) / tau²_p − 1,     clamped to [5, 30]
```

- `tau² = 0` (no *detectable* between-member spread) → `s` is unbounded → clamp at **30**, tying the
  maximum influence of a superarchetype prior to exactly one displayable cell's worth of evidence
  (`DISPLAY_GATE_N`).
- Large `tau²` (incoherent cluster) → `s` collapses → floor at **5**, so an incoherent cluster still
  beats a bare 0.5 prior but barely nudges the cell.

The ceiling is project-grounded — it *equals* `DISPLAY_GATE_N`. The floor of 5 is a chosen minimum
with a stated intent but no calibration behind it; validate it against the existing
`SHRINK_STRENGTH = 15` before shipping. Both are auditable in the prior_source label.

**Carry §6.4's one-sided-evidence rule into this formula.** `taû² = 0` is measured on 58.7% of
poolable cells, and §6.4 establishes that at these member sizes a zero mostly means "we cannot see
spread", not "there is none". Reading `taû² = 0` as *coherent* therefore hands the **maximum** prior
strength to the majority of cells on the **weakest** evidence — the exact inversion the heterogeneity
gate exists to prevent. Condition the ceiling on the cell having had the power to detect spread had
it existed (the same `>= 2 members with n >= 5` computability floor as §6.2), and fall back toward
the floor when it did not.

---

## 5. Concentration gate — "is this really one member's record?"

### 5.1 The measure

Let `n_k` be member k's contribution to the pooled cell and `HHI = Σ (n_k/Σn)²`. HHI "is calculated
by squaring the market share of each competing firm in the industry and then summing the resulting
numbers" `[superarchetype-hhi]{8}` and ranges from 1/N to 1.0. Report its reciprocal: "in the more
general case of unequal market share, 1/H is called 'equivalent (or effective) number of firms'"
`[superarchetype-hhi]{8}`. Call it **`m_eff` — the effective number of member archetypes behind this
cell**.

`m_eff` is algebraically the same object as Kish's effective sample size applied to the member
counts as weights — `deff_K = 1 + CV²(w)` and `n_eff = n/deff` `[superarchetype-kish-deff]{9}` — which
is a useful cross-check but comes with its own honest caveat: Kish's formula "is derived under some
extremely restrictive assumptions" `[superarchetype-kish-deff]{9}`, so treat `m_eff` as an
interpretable concentration diagnostic, not as a literal variance correction (that job belongs to
`tau²` in §4).

### 5.2 The threshold

**Gate: a pooled cell may be labeled a cluster read only if `m_eff >= 2.0` (equivalently
`HHI <= 0.50`) AND no single member supplies more than 60% of n.** Both cutoffs are this project's,
not the source's — `[superarchetype-hhi]{8}` supplies the *measure*, never these values. The
paragraphs below state exactly what grounding each cutoff has.

Below that, the cell is still served — coverage is the point of the epic — but it is labeled
**`dominated by <member>`** and the audit line names the member and its share. A cell with exactly
one contributing member is not a pool at all; label it as that member's cell, surfaced at cluster
granularity.

**Rationale for 2.0, and why the antitrust bands do not transfer.** The DOJ bands (unconcentrated
below 0.15, highly concentrated above 0.25 `[superarchetype-hhi]{8}`) are calibrated to markets with
many participants: a perfectly even **four**-member cluster sits exactly at 0.25, i.e. "highly
concentrated", which would fail almost every cluster we have. Borrow the effective-number reading,
discard the thresholds. `m_eff >= 2.0` is the minimum claim the label makes — "at least two
archetypes' worth of evidence stands behind this number."

**The `m_eff` threshold is calibrated on measured data, not picked round.** Across multi-member
pooled cells with n>0: median HHI is exactly **0.500** (`m_eff` 2.00), p25 0.320, p75 0.722, and
**46.0% exceed 0.50**. So the gate bisects the population — it is a live constraint, not a rubber
stamp. Restricted to the cells that pooling actually *unlocks* (n>=30), median HHI is 0.258
(`m_eff` 3.9) and **7 of 25 (28%) fail the gate** — a targeted, meaningful minority.

**The 60% member-share cap has no separate calibration, and it is not redundant.** At K=2 it is
slack (a 60/40 split already gives `m_eff` 1.92 and fails the concentration gate on its own), but at
K>=3 it is the *binding* constraint — a 60/20/20 split gives `m_eff` 2.27, which passes `m_eff` and
fails only the cap. So it is a live, uncalibrated parameter carrying real decisions. Re-derive it
from the measured member-share distribution before it ships.

---

## 6. Heterogeneity gate — "does pooling smuggle in worse bias than the thin cell?"

This is the epic's sharpest open question, and meta-analysis is the field that formalized exactly
this trade.

### 6.1 The measure

Compute Cochran's Q across the member cells and
`I² = (Q − (K − 1))/Q` `[superarchetype-meta-heterogeneity]{6}` — "the percentage of variability in
the effect sizes that is not caused by sampling error"
`[superarchetype-meta-heterogeneity]{6}`; equivalently, "the percentage of the variability in effect
estimates that is due to heterogeneity rather than sampling error (chance)"
`[superarchetype-cochrane-heterogeneity]{5}`. `Q` and `tau²` come free from the §4 estimator.

### 6.2 The thresholds

Cochrane's published bands — offered as a rough guide, and deliberately overlapping — are "0% to
40%: might not be important; 30% to 60%: may represent moderate heterogeneity; 50% to 90%: may
represent substantial heterogeneity; 75% to 100%: considerable heterogeneity"
`[superarchetype-cochrane-heterogeneity]{5}`. The band *edges* below are taken from that guidance;
the **actions attached to them are this project's**, mapped onto its three-state honesty vocabulary:

| I-squared | Action |
|---|---|
| **<= 0.40** | Pool and display normally (chip: `superarchetype`) |
| **0.40 - 0.75** | Pool, but the random-effects `n_eff` (§4.4) already widens the interval; add a `heterogeneous pool` note naming the spread |
| **> 0.75** | **Refuse the pooled number.** Do not display a cluster win rate; show the per-member split instead and leave the cell in its honest unmeasured state |

Plus two guards that do not depend on I-squared:

- **Direction/spread guard.** Cochrane is explicit that "thresholds for the interpretation of the I2
  statistic can be misleading, since the importance of inconsistency depends on several factors" —
  the magnitude and direction of effects `[superarchetype-cochrane-heterogeneity]{5}`. Concretely:
  among members with n>=10, if `max p̂ − min p̂ >= 0.25`, treat the cell as if I-squared exceeded 0.75
  regardless of what I-squared says (author's engineering rule, grounded in that caveat).
- **Minimum computability.** Q and I-squared are undefined below two members; we additionally
  require each of those members to have n>=5 (author's rule — a 1-match member carries no usable
  variance). With fewer, no heterogeneity claim may be made in either direction; the cell falls back
  to the concentration labeling of §5.

### 6.3 The worked example — both gates fire on the epic's own motivating pair

Measured, current window, subject **Dimir Tempo** against the derived `Aluren + Show and Tell`
cluster:

| Opponent | Record | n | Raw |
|---|---|---|---|
| Aluren | 4-9 | 13 | 30.8% |
| Show and Tell | 24-5 | 29 | 82.8% |
| **Pooled** | **28-14** | **42** | **66.7%** |

The pooled cell **clears `DISPLAY_GATE_N` on raw pooled n** and, under naive count-pooling, would
render as a confident 66.7% edge. It is a lie: the two members disagree by 52 percentage points, and
one of them supplies 69% of the sample.

- Concentration: **HHI = 0.573**, `m_eff` = **1.75** → fails the §5 gate (< 2.0), and the top member
  share 0.69 also fails the 0.60 cap.
- Heterogeneity: **I-squared = 0.89**, Q = 9.1 on K = 2 → "considerable heterogeneity"
  `[superarchetype-cochrane-heterogeneity]{5}` → fails the §6 gate.
- Spread guard: 0.828 − 0.308 = 0.52 >= 0.25 → fails independently.
- Effective sample: at I-squared = 0.89 the §4.4 `n_eff` also falls well below the raw 42, so the
  existing display gate refuses the cell before §5/§6 are consulted (exact value not computed here).

**This is the single most important validation in the brief.** The family that motivated the epic is
also the family where naive pooling is least safe against a specific subject, and every independent
gate catches it. The correct surface behaviour is: no pooled number, show
`vs Show and Tell 82.8% (n=29, speculative) / vs Aluren 30.8% (n=13, speculative)` and say the
family does not behave as one against this deck — divergence-as-diagnostic, not a blended number.

### 6.4 The honesty caveat that must reach the UI

Measured across the 75 poolable cells at K=8: median I-squared **0.000**, mean 0.150, **58.7% exactly
zero**, 8.0% above 0.50, only **4.0% above 0.75**. Read naively, "pooling is almost always fine."
That reading is wrong, and the literature says why:

- Cochran's Q "has low power in the (common) situation of a meta-analysis when studies have small
  sample size or are few in number" `[superarchetype-cochrane-heterogeneity]{5}`.
- "Q increases both when the number of studies K, and when the precision (i.e. the sample size of a
  study) increases. Therefore, Q and whether it is significant highly depends on the size of your
  meta-analysis" `[superarchetype-meta-heterogeneity]{6}`.
- "I² is not an absolute measure of heterogeneity, and its value still heavily depends on the
  precision of the included studies" `[superarchetype-meta-heterogeneity]{6}`.

So at n=2-to-30 per member, **a low I-squared mostly means "we cannot see heterogeneity", not "there
is none."** Treat the gate as **one-sided evidence**: a high value is the trustworthy direction (the
observed spread has exceeded a generous sampling-error allowance) and is a stop signal; a low value
is never a certificate of exchangeability. The consequence for the surface is that a pooled
cell that merely *passes* the gate is still a superarchetype-sourced estimate and must carry its
provenance chip — passing the heterogeneity gate never promotes it to the status of a measured
archetype cell.

---

## 7. Intra-cluster matches

The epic fixes the policy — they count, flagged. The statistics fix the details.

**In the displayed cluster cell** (subject S versus cluster G, where S ∈ G):

- **Sibling matches count.** S vs its non-self cluster-mates enter wins/n normally. They are real
  matches against real decks that play the family's strategy.
- **The exact self-mirror is excluded from the rate, and its n is reported.** A mirror is 0.5 by
  symmetry and carries zero information about an edge — the codebase already encodes this
  (`build_mirror_cell` sets a fixed 0.5 and no CI). Folding self-mirrors into the numerator would
  mechanically drag every intra-family cell toward 50% in proportion to the subject's own field
  share. Report `mirror_n` alongside so the coverage stays fully auditable.
- **The cell carries `intra_cluster = True` and `intra_cluster_share`** = (matches vs siblings +
  self-mirror) / total n. When that share is high, the surface says so plainly: *"most of this edge
  is against your own family."* Measured example: `Aluren` vs `Show and Tell` is 11-8 (n=19, 57.9%)
  in the current window — under a superarchetype view that is an intra-family cell, not an edge
  against a distinct strategy.
- Intra-cluster members are **not** exempt from §5/§6. A sibling that disagrees violently with the
  rest of the family is exactly what the heterogeneity gate is for.

**In the prior chain** (§8) the rule is different and stricter: the superarchetype prior for cell
(S, O) must be computed **leave-opponent-out** — exclude the (S, O) tally itself from the pooled
aggregate. Otherwise the cell's own data appears inside the prior it shrinks toward, which
double-counts the evidence and understates the shrinkage. This is the direct analogue of the
leave-camp-out construction already in `matchup._camp_hierarchy_inputs`, and the same subtraction
discipline (assert non-negative; a negative result means the member counts are not a partition) should
apply. Symmetrically, when a cluster-level marginal anchors one of its own members, that member's
contribution is left out.

---

## 8. Where the superarchetype sits in the shrinkage chain

Today `matchup._cell_prior` implements: **camp cell → leave-camp-out parent cell → parent's shrunk
marginal → 0.5**, with `build_adaptive_matrix`'s cross-era prior overriding for thin era-truncated
cells. The superarchetype is a **new rung, inserted between the parent cell and the marginal**, and
it coarsens the *opponent* axis rather than the subject axis.

```
(camp S, archetype O)                                        finest, existing
  ↓ shrink toward
(parent S, archetype O)          leave-camp-out              existing
  ↓ shrink toward
(parent S, cluster G(O))         leave-opponent-out          ← NEW rung 1
  ↓ shrink toward
(cluster G(S), cluster G(O))     leave-S-out, leave-O-out    ← NEW rung 2 (optional)
  ↓ shrink toward
(parent S, field)                subject marginal'           existing
  ↓ shrink toward
0.5                                                          existing
```

The chain is a monotone coarsening: each rung conditions on strictly less information than the one
above it, and every rung is more specific than the subject's overall win rate. That is exactly the
intermediate level the epic identified as missing — it sits above the archetype cell and below the
marginal, and nothing else in the chain moves.

**Why opponent-side coarsening comes first.** Rung 2 (coarsening the subject too) buys more sample —
pooling `Aluren` with `Show and Tell` takes the strategy's deck pool from 71 to 405 in the current
window — but it changes *whose* win rate is being reported, and the best-call page's row IS the
user's deck. Opponent-side coarsening is the strictly less lossy step, so it goes first. Fixing the
order (rather than picking per-cell whichever gives more n) keeps the audit trail deterministic; the
gates decide whether a rung is *allowed*, never which rung comes *first*.

**Prior strength per rung** comes from §4.5, so a coherent cluster anchors harder than an incoherent
one. **A rung that fails its §5/§6 gates is skipped**, and the chain falls through to the next — the
existing `prior_source` string carries which rung was used (e.g. `superarchetype cell
(leave-opponent-out; m_eff 3.9, I²=0.11)`).

**Display fallback is separate from the prior chain** (the epic's locked decision). For display, walk
the same ladder and take the **finest rung whose `n_eff` clears `DISPLAY_GATE_N`**, then render it
with a provenance chip alongside the existing BA/FC/era chips. Two differences from the prior path:
the displayed cluster cell **includes** the opponent's own matches (it is the best estimate of "S vs
this family", not a prior that must stay independent), and it carries the intra-cluster flag of §7.

**The cross-era prior keeps precedence.** `build_adaptive_matrix` currently overrides the hierarchy
prior with a cell's own pre-disturbance value for thin era-truncated cells. That override is more
specific to the cell than any cluster aggregate and should continue to win; the superarchetype rung
applies where no cross-era prior exists.

---

## 9. Interaction with stable eras

**Measured answer: superarchetype membership does not need era-scoping the way camps do.** Running
the full pipeline independently on 2026-01-01→2026-04-15 (34 definers) and 2026-04-15→2026-07-31 (33
definers) gives **co-membership agreement 0.957** on the 26 archetypes present in both — across a
span containing both the Flow State one-week adoption step and the Candelabra ban (see
`docs/briefs/change-point-detection.md` §1 for those ground truths). This is intuitive: a ban or a
new card changes which cards a deck plays, but rarely which family of strategy it belongs to.

Recommended handling:

- **Recompute membership on the same window the matrix is sourced over.** ~30 objects and a few
  hundred features is milliseconds; there is no reason to cache a stale taxonomy. This also means a
  cluster cell never pools composition from before an entity's `stable_since` — the existing
  per-entity windowing already bounds the data and the clustering simply inherits it.
- **Do not era-partition cluster identity.** Curated cluster ids and names must be stable across
  windows or every consuming surface churns. Membership is the thing that moves.
- **Surface churn as a diagnostic.** When an archetype's cluster changes between refreshes, that is a
  finding (a deck has been rebuilt into a different strategy) and belongs in the audit output, not
  silently in a new number. Measured baseline: expect ~0.96 co-membership agreement window-over-
  window; a materially lower figure is itself the alarm.
- **Camps inherit their parent's cluster.** A camp is a build of a parent archetype; it belongs to
  whatever family the parent does unless a curated override says otherwise.

---

## 10. Implementation notes

- **Reuse, don't rebuild.** `analytics/discovery.py` already owns the "build feature matrix → reduce →
  cluster → validate → name" shape and the `objective-search-split` structure (DB-free pure core, thin
  DB wrapper). The superarchetype pipeline is the same shape with different parameters: rows are
  archetypes not decks, the band is format-level not parent-level, the algorithm is agglomerative not
  HDBSCAN, and the validator is branch AU p-values not co-membership bootstrap alone.
- **`beta_binomial_shrink_to` is untouched.** The superarchetype contributes a `prior_mean` and a
  `strength`; the primitive already takes both. The only change to `_cell_prior` is one more rung and
  one more `prior_source` label — the additive, byte-identical-when-absent shape the codebase already
  uses for the camp hierarchy and the cross-era prior (gated-additive-augmentation).
- **`n_eff` is the integration seam.** Do not add a new tier system. Compute `n_eff` in the
  aggregation module and hand it to the existing `tier_for_sample()` / `display` gate. Every existing
  honesty guarantee then applies to cluster cells unchanged.
- **Persist the taxonomy like discovery persists camps.** A cluster registry (derived + curated, with
  the derived assignment recorded even when overridden) written by an offline labeling pass, never
  computed in a query hot path. The curated half is a hand-authored JSON resource under
  `PACKAGE_DATA_DIR` with a fail-fast loader (curated-json-resource-loader), matching how the variant
  registry and hoser catalog already work.
- **New dependency surface is zero.** `scipy.cluster.hierarchy` (linkage/fcluster/cophenet) covers
  the clustering and `scipy>=1.11` is already a core dep (`pyproject.toml`); the AU p-value
  computation is a bootstrap loop in numpy (pvclust itself is R `[superarchetype-pvclust]{11}` —
  port the criterion, not the package); DerSimonian-Laird is a closed-form moment estimator, ~15
  lines. Note the camp layer added no heavyweight dependency either — it clusters with
  `sklearn.cluster.HDBSCAN` (a core dep, `analytics/discovery.py`) and only reaches for the
  optional, lazily-imported `umap-learn` extra.
- **Scale.** 30-45 objects × a few hundred features × a bootstrap of a few hundred resamples is
  sub-second. Choose methods on statistical merit only.
- **Everything degrades with a name.** Cluster cells that fail a gate emit a labeled reason
  (`dominated by Show and Tell`, `heterogeneous pool I²=0.89`, `single-member cluster`), never a
  silently suppressed cell and never a quietly blended number (honest-degrade-marker).

### Long tail (out of scope, noted)

Soft/overlapping cluster membership (a deck that is 0.6 cheat-into-play, 0.4 fair blue) is the natural
refinement but adds a weighting layer to every cell; not v1. A full Bradley-Terry GLMM with a
cluster-level random effect `[superarchetype-bradley-terry2]{4}` is the parametric route to a dense
matrix and should be revisited if a surface ever needs *every* cell filled rather than
gated-and-labeled. Restricted-maximum-likelihood estimation of `tau²` is commonly reported as less
biased than DerSimonian-Laird but is iterative (**not attested in this corpus** — verify before
relying on the comparison); DL's closed form is the right first move at these K. Opponent-side
*camp* resolution remains impossible from tournament data and is unaffected by this epic.

---

## Sources

- Gelman (2005), "Multilevel (hierarchical) modeling: what it can and can't do" — partial pooling vs both extremes; cross-validated benefit; no-pooling cannot borrow across groups `[superarchetype-gelman-multilevel]{1}`
- rstanarm vignette, "Hierarchical Partial Pooling for Repeated Binary Trials" — pooling definitions; population variance controls the amount of pooling `[superarchetype-stan-pooling]{2}`
- "James–Stein estimator" (Wikipedia) — dominance in total MSE; the per-component caveat `[superarchetype-james-stein]{3}`
- Turner & Firth, BradleyTerry2 vignette — structured BT, player random effects, PQL fitting `[superarchetype-bradley-terry2]{4}`
- Cochrane Handbook ch.10 §10.10 — Chi² test low power; I² definition and interpretation bands; thresholds can mislead `[superarchetype-cochrane-heterogeneity]{5}`
- Harrer et al., "Doing Meta-Analysis in R" (heterogeneity) — Q, I², τ² formulas; I² is not absolute `[superarchetype-meta-heterogeneity]{6}`
- Harrer et al., "Doing Meta-Analysis in R" (pooling) — inverse-variance and random-effects weights; small-study attention; model choice `[superarchetype-meta-pooling]{7}`
- "Herfindahl–Hirschman index" (Wikipedia) — Σ shares²; 1/H as effective number; DOJ bands `[superarchetype-hhi]{8}`
- PracTools, "Design Effects and Effective Sample Size" — Kish deff, n_eff, restrictive assumptions `[superarchetype-kish-deff]{9}`
- "Simpson's paradox" (Wikipedia) — pooled-rate reversal under unequal exposure `[superarchetype-simpsons-paradox]{10}`
- pvclust (Suzuki & Shimodaira) — multiscale-bootstrap AU p-values; AU > 0.95 interpretation `[superarchetype-pvclust]{11}`
- "Identifying and Clustering Counter Relationships of Team Compositions in PvP Games" (arXiv 2408.17180) — grouped M×M counter table; intransitivity `[superarchetype-pvp-counter-clustering]{12}`

Reused from the `subarchetype-discovery` corpus (already attested; cited by handle above):
`[sklearn-clustering]{13}` (agglomerative linkage criteria; DBSCAN/HDBSCAN density assumption),
`[hdbscan-docs]{14}` (min_cluster_size / min_samples / noise labeling),
`[jaccard-index]{15}`, `[bray-curtis]{16}`, `[cosine-similarity]{17}` (similarity measures),
`[cluster-stability-review]{18}` (co-membership stability), `[gao-selective-inference]{19}`
(double-dipping), `[kritschgau-hypergraph]{20}` (statistical vs human cluster count; domain
verification), `[luckypaper-commander-map]{21}` (MTG deck-clustering prior art).

All corpus figures in this brief were measured on `data/legacy.duckdb` on 2026-07-31 over the window
`[2026-05-11, 2026-07-30]` unless another window is named; they are project measurements, not sourced
claims.
