---
description: "How do you discover play-pattern subarchetypes WITHIN a flat parent label at corpus scale, decide which splits are real vs sampling noise, and feed a variant dimension into the matchup matrix + card win-rate without breaking the confidence-tier honesty gates? Read before designing epic-subarchetype-resolution."
type: brief
kind: research
slug: subarchetype-discovery
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-11
blocks_phase: epic-subarchetype-resolution
summary: |
  Curates the method for full-unsupervised, statistically-self-validating subarchetype discovery for
  legacy-engine. Grounds representation, distance, clustering-algorithm, and validation choices in the
  real corpus (within a parent the effective vocabulary is ~120-260 cards, stratified into a
  ubiquitous core / a ~20-30-card flex band where splits live / a rare noise tail) and in the closest
  MTG prior art (Lucky Paper's Jaccard→UMAP→HDBSCAN pipeline). Specifies how a variant dimension keys
  into the matchup matrix and per-card win-rate while preserving the Beta-Binomial shrinkage + tier gates.
key_findings:
  - "Within a single parent archetype the effective feature space is small (~120-260 distinct main cards, not the ~40k global oracle) and stratifies into ubiquitous core (no signal) / ~20-30 flex cards (all the split signal) / a long rare tail (noise) — cluster on the flex band, not raw card-space."
  - "The closest production precedent (Lucky Paper's Commander/Cube Map) matches the recommended shape: deck-card matrix → Jaccard distance → UMAP reduction → HDBSCAN (self-determines k, labels noise) → human-readable validation; recommend TruncatedSVD/LSA or UMAP to ~10-50 dims first because HDBSCAN degrades past ~50-100 dims."
  - "Copy counts carry real signal (the validated Doomsday split is bimodal on Tamiyo 3.70 vs 0.98 copies), so prefer count/TF-IDF representations + cosine/Bray-Curtis over pure binary presence where the split is a quantity difference."
  - "A discovered split is 'real' only if it clears BOTH statistical gates (resampling stability >0.9 / prediction strength >0.8; internal indices as a weak secondary) AND the domain gate the engine already trusts (both camps reach evolving+ sample tier; large signature-card inclusion/copy divergence)."
  - "Naive significance testing on clustered data is the double-dipping trap — type I error is extremely inflated even across independent datasets; validate on a held-out split or selective-inference test, never a plain t-test on the same data used to form the clusters."
  - "A statistical cluster-count criterion can disagree with the human-intuitive archetype count (an MDL criterion picked 3 clusters where 5 was 'obvious'); because color identity is the loudest low-dimensional signal, drop color-defining lands/duals so splits key on strategy — clustering within an already-color-fixed parent largely pre-empts this."
  - "Integration: match_results.py keys on decks.archetype only; add an OPTIONAL variant dimension on one side of a cell (subject_variant × opponent_parent), reusing the existing Beta-Binomial shrinkage + speculative/evolving/established gates unchanged — every split cell surfaces at its own honest tier, never hidden, never blended."
---

# Brief: Data-Driven Subarchetype Discovery

## Purpose

Unblocks `epic-subarchetype-resolution`. The epic's locked decisions are **full-unsupervised,
statistically-self-validating discovery** (the pilot cannot reliably hand-confirm a hybrid registry,
so clusters must earn their split from statistics, with a human-confirm promotion hook preserved for
later), **discovery-first** sequencing, and **speculative-tier split cells surfaced-and-labeled,
never hidden**. This brief gives the builder the representation, distance, algorithm, validation, and
integration decisions needed to build the discovery engine correctly — grounded in the real corpus
and in the (thin but real) prior art. It does **not** dictate module structure — that is
`epic-design`'s job.

---

## 1. The problem in data terms

The Legacy archetype layer assigns one flat label per deck (a ported rule-based matcher; the
production standard it mirrors, MTGOArchetypeParser, is likewise a hand-authored rules engine, not a
discovery system `[mtgo-archetype-parser]{2}`). Decks that share a label but play differently get
pooled — into one matchup row and one card-win-rate denominator — which is precisely what distorted
this project's own analysis three times (the Doomsday Murktide/non-Murktide camps; the WU
Phelia/Riddler deck fragmenting across three labels; the Dimir Tempo Bauble keep/cut). See the epic
for those cases.

**The corpus makes the problem tractable in a way the raw ~40,000-card oracle vocabulary suggests it
is not.** Measured on the current corpus (decks since 2024-12-16), *within a single parent* the
effective vocabulary is small and cleanly stratified:

| Parent | decks | distinct main cards | ubiquitous (≥95%) | **flex (10–95%)** | rare (<10%) |
|---|---|---|---|---|---|
| Doomsday | 1170 | 157 | 16 | **25** | 116 |
| Izzet Delver | 1996 | 118 | 10 | **18** | 90 |
| Dimir Tempo | 2447 | 135 | 12 | **19** | 104 |
| Death & Taxes | 955 | 260 | 9 | **32** | 219 |
| Lands | 1169 | 166 | 16 | **24** | 126 |
| Eldrazi | 1446 | 134 | 9 | **24** | 101 |

Three bands, each with a different role for discovery:

- **Ubiquitous core** (~10–16 cards at ≥95% inclusion) — the shared chassis. Carries **zero** split
  signal (present in every deck ⇒ zero variance). Drop it.
- **Flex band** (~18–32 cards, 10–95% inclusion) — **this is where every subarchetype split lives.**
  The engine plan-B packages, the tempo-vs-combo commitments, the color splashes.
- **Rare tail** (~90–220 cards, <10%) — one-off tech and singleton pet cards. Mostly noise; down-weight
  or drop, or it will dominate a distance metric that treats all cards equally.

**Implication (load-bearing):** cluster on the **flex band of a single parent**, not on the global
card space. The effective dimensionality is ~20–35, not ~40,000 — which moves the problem out of the
worst of the curse of dimensionality `[sklearn-clustering]{5}` and into a regime where the standard
toolchain works well.

### Worked example — the validated Doomsday split

Splitting the 1170 Doomsday decks on Murktide Regent presence yields **292 with / 878 without**. The
camps separate cleanly on flex-band **copy counts**, not just presence:

| Card | Murktide camp (avg copies) | non-Murktide camp | Δ |
|---|---|---|---|
| Tamiyo, Inquisitive Student | 3.70 | 0.98 | **+2.72** |
| Wasteland | 2.21 | 0.06 | **+2.15** |
| Personal Tutor | 0.10 | 1.87 | −1.77 |
| Lotus Petal | 1.88 | 3.23 | −1.35 |
| Orcish Bowmasters | 1.10 | 0.10 | +1.00 |
| Cabal Ritual | 0.03 | 0.74 | −0.71 |

The Murktide camp is a tempo/mana-denial build (Tamiyo + Wasteland + Bowmasters); the non-Murktide
camp is all-in ritual mana (Personal Tutor + Cabal Ritual + extra Lotus Petals). Two lessons for the
builder: (1) the signal is **bimodal on copy count** (Tamiyo is ~4-of or ~0-of, rarely in between) —
a discovery method that ignores copy counts throws away this structure; (2) a single well-chosen
signature card already recovers the split, so discovery's job is to *find* that axis automatically
and confirm it, not to invent structure that a human marker rule couldn't.

---

## 2. Representation — how to vectorize a decklist

Build the feature matrix **per parent**, over that parent's own flex band, not globally.

- **Rows** = decks in the parent's in-window pool. **Columns** = the flex-band cards (drop ubiquitous
  and rare by inclusion thresholds — start at drop ≥95% and <~5–10%; expose as parameters).
- **Cell value — prefer copy counts over binary presence.** The Doomsday example shows the split is a
  *quantity* difference (Tamiyo 3.70 vs 0.98). The closest prior art (Lucky Paper) used binary
  presence `[luckypaper-commander-map]{1}`, which is simpler and robust but blind to 1-of-vs-4-of
  intent. Recommend counts as the default; keep binary as a fallback/ablation.
- **TF-IDF weighting** is a natural fit: a deck-card matrix is a term-document matrix — the same object
  LSA operates on `[sklearn-decomposition]{7}`. TF-IDF's inverse-document-frequency term then
  down-weights cards ubiquitous across the parent (the residual chassis) and up-weights the
  differentiating cards — exactly the split signal (standard TF-IDF behavior, not a claim of the cited
  source). L2-normalize rows so cosine distance and Euclidean distance induce the same neighbor ranking.
- **Dimensionality reduction before clustering.** Even on the flex band (~20–35 dims) reduction helps,
  and is *mandatory* if you widen the feature set. TruncatedSVD on the (TF-IDF) deck-card matrix is
  latent semantic analysis and is documented to combat the sparsity that gives term-document matrices
  poor cosine similarity `[sklearn-decomposition]{7}`. UMAP is an effective preprocessing step to
  boost density-based clustering and, for clustering (not plotting), you reduce to ~10 dimensions
  rather than 2 `[umap-clustering]{8}`. **Load-bearing caution:** UMAP does not fully preserve density
  and can create "false tears" — finer clustering than is actually present `[umap-clustering]{8}` — so
  any UMAP+HDBSCAN split MUST clear the §5 validation bar, not just look separated in a plot.

**Steer away from color.** A statistical cluster-count criterion can disagree with the human-intuitive
archetype count — in an MTG draft study a minimum-description-length criterion picked 3 clusters where
5 was "in some sense the obvious number" `[kritschgau-hypergraph]{3}`. The practical risk for
decklists (author's engineering caution, **not** a sourced claim): color identity is the loudest
low-dimensional signal, so an under-resolved clustering can key on colors rather than play pattern.
Because discovery runs *within* an already-color-consistent parent this is mostly pre-empted — but if
a parent spans a splash (e.g. a UB deck with a WUB variant), drop color-defining lands/duals from the
feature set so the split keys on strategy, not mana base.

---

## 3. Distance / similarity

| Metric | Copy-aware? | True metric? | Pairs with | Use when |
|---|---|---|---|---|
| **Jaccard** `[jaccard-index]{11}` | no (sets) | yes | agglomerative, k-medoids | coarse "shares the package" grouping; the Lucky Paper choice |
| **Cosine** `[cosine-similarity]{10}` | yes | (similarity) | k-means/GMM/Ward/HDBSCAN on reduced embedding | default for TF-IDF/count vectors; cheap on sparse data (only non-zero coords matter) |
| **Bray–Curtis** `[bray-curtis]{12}` | yes (abundance) | **no** | agglomerative avg/complete, k-medoids | when 1x-vs-4x is the whole point; NOT with metric-assuming methods |
| **Hellinger** | yes (as distribution) | yes | centroid methods | decks normalized to relative-frequency distributions |

Cosine similarity's advantage on this data is explicit: "only the non-zero coordinates need to be
considered" `[cosine-similarity]{10}` — cheap even before reduction. **Recommended default: TF-IDF +
L2 + cosine on a TruncatedSVD/UMAP embedding.** Where a split is a pure abundance difference and you
want to skip reduction, Bray–Curtis on raw counts is the honest choice — but remember it is a
dissimilarity, not a metric `[bray-curtis]{12}`, so feed it to agglomerative/k-medoids, never to
k-means.

---

## 4. Clustering algorithm — must self-determine k and tolerate noise

The epic requires no pre-specified k and robustness to outlier decks (a corpus is full of one-off brews
that should be *noise*, not forced into a camp). Ranked for this problem:

### HDBSCAN — recommended primary

Density-based; self-determines the number of clusters and explicitly labels low-density points as
noise. It "alleviates [DBSCAN's globally-homogeneous-density] assumption and explores all possible
density scales" `[sklearn-clustering]{5}`, which matters because a parent's camps differ in
popularity (a dominant camp is dense, a fringe camp sparse). This is the algorithm the
closest MTG precedent settled on, "designed to handle clusters of different densities"
`[luckypaper-commander-map]{1}`.

Tuning: `min_cluster_size` = "the smallest size grouping that you wish to consider a cluster"
`[hdbscan-docs]{4}` — **tie this to the honesty gates**: set it no smaller than the evolving-tier
floor (30 decks) so a "camp" can never be born below a defensible sample. `min_samples` controls
conservatism — "the larger the value... the more conservative the clustering – more points will be
declared as noise" `[hdbscan-docs]{4}`; it defaults to `min_cluster_size` `[hdbscan-docs]{4}`. **Run
it on a reduced embedding**: HDBSCAN "can do well on up to around 50 or 100 dimensional data, but
performance can see significant decreases beyond that" `[hdbscan-docs]{4}`.

### GMM + BIC — secondary, for soft membership

Model-based; BIC selects the component count "in an efficient way" but "recovers the true number of
components only in the asymptotic regime" and assumes Gaussian-generated data `[sklearn-mixture]{6}`.
Attractive because it yields **soft** membership (a deck can be 0.6 tempo / 0.4 turbo) — useful for
blended camps. **Load-bearing failure mode at our sample sizes:** "when one has insufficiently many
points per mixture... the algorithm is known to diverge and find solutions with infinite likelihood
unless one regularizes" `[sklearn-mixture]{6}` — so for small parents or small camps, GMM needs
covariance regularization or it will blow up. Without BIC/held-out data it "will always use all the
components it has access to" `[sklearn-mixture]{6}`.

### Agglomerative + dendrogram, and k-medoids — tertiary

Agglomerative clustering pairs with any distance matrix, so it takes Jaccard/Bray–Curtis directly;
its Ward / complete / average / single linkage criteria are defined in the sklearn guide
`[sklearn-clustering]{5}`.
k-medoids accepts a precomputed dissimilarity and centers on real decks. Both need k chosen externally
(silhouette/gap, §5). Cutting a dendrogram "by eye" is the subjective, over-fitting-prone step to
avoid — prefer HDBSCAN's automatic extraction or a validated cut.

**Recommendation:** HDBSCAN primary (auto-k, noise labels, density-robust, prior-art-proven); GMM+BIC
as the soft-membership option when a parent's camps genuinely blend; agglomerative/k-medoids as the
distance-matrix fallback for Jaccard/Bray–Curtis experiments.

---

## 5. Validation — when is a split real vs noise?

A discovered split must clear **two independent gates**. Statistical validity alone is not enough
(a stable cluster can still be strategically meaningless); domain validity alone is the hand-authoring
the epic is trying to escape.

### Gate A — statistical

- **Resampling stability is the primary bar.** Represent a clustering as a binary co-membership matrix;
  "if the clustering is stable, then the clusters from the original data will be preserved in the
  perturbed data clustering" `[cluster-stability-review]{14}`. Require stability **> 0.9** (Yu et al.
  2019) or prediction strength **> 0.8** `[cluster-stability-review]{14}`. A split that dissolves under
  resampling is noise.
- **Internal indices are a weak secondary.** Silhouette ranges −1…+1 with rules of thumb "over 0.7…
  'strong', a value over 0.5 'reasonable', and over 0.25 'weak'" `[silhouette-clustering]{9}`, but it
  "is specialized for measuring cluster quality when the clusters are convex-shaped, and may not
  perform well if the data clusters have irregular shapes" `[silhouette-clustering]{9}` — so it is a
  **poor** validator for HDBSCAN's non-convex output and better suited to k-means/GMM/Ward. Use the
  gap statistic (observed vs null within-cluster dispersion `[tibshirani-gap]{15}`) to sanity-check k
  where an external-k method is used.
- **Avoid the double-dipping trap (load-bearing).** Do NOT confirm a split with a plain significance
  test on the same data used to form it: "when the groups are instead defined via clustering, then
  applying a classical test yields an extremely inflated type I error rate," and this "persists even
  if two separate and independent data sets are used" `[gao-selective-inference]{13}`. Use a
  held-out/resampling confirmation (which is what prediction strength mechanizes) or a
  selective-inference test calibrated to the clustering procedure.

### Gate B — domain (the honesty gates the engine already trusts)

- **Both camps must reach evolving tier (n ≥ 30).** A split into a 300-deck camp and a 12-deck camp is
  not a subarchetype discovery — it is a dominant build plus noise. Set HDBSCAN `min_cluster_size` to
  enforce this at discovery time.
- **Signature-card divergence must be large and interpretable.** The existing `report subgroup`
  primitive already computes per-card copy-count deltas between a with/without split; a real split
  looks like the Doomsday table in §1 (multiple flex cards at |Δ| ≳ 1 copy). This is also the
  published state of the art's ultimate arbiter: certifying a cluster as a real named archetype
  "requires some domain knowledge, and is therefore, hard to verify independently"
  `[kritschgau-hypergraph]{3}`.

**The human-confirm hook.** Because Gate B's naming step needs judgment the pilot may not have yet,
discovery produces *candidate* splits that pass Gate A + the mechanical parts of Gate B (both-camp
tier, divergence magnitude) and stages them for promotion into the curated registry — it does not
silently rewrite the taxonomy. As pilot expertise grows the confirm step tightens; until then the
statistics are the gate and unpromoted candidates stay labeled speculative.

---

## 6. Auto-naming clusters

Naming is post-hoc and mechanical-then-human. For each cluster, rank its cards by **signature score**
(inclusion-rate lift and copy-count delta vs the parent baseline — the `report subgroup` diff, already
built). The top 1–3 over-represented cards are the candidate name (the Doomsday example auto-names as
"Murktide / non-Murktide" or "Tempo / Turbo" straight from the divergence table). Emit the name as a
*proposal* with its signature cards attached; the human-confirm hook renames if the mechanical label is
strategically wrong. Prior art is unanimous that this final certification is human ("validate clusters
by seeing if the lists share design goals" `[luckypaper-commander-map]{1}`; "hard to verify
independently" without domain knowledge `[kritschgau-hypergraph]{3}`).

---

## 7. Integration — feeding the variant dimension into analytics

The persisted output of discovery is the existing **`decks.variant`** column (already populated for a
few parents: Dimir Tempo Bauble/non-Bauble, Smallpox Loam/non-Loam, Doomsday Tempo/Turbo). The
integration constraint is that `analytics/match_results.py` keys on `decks.archetype` **only**, so
writing `decks.variant` does not by itself split any downstream stat.

### Matchup matrix

Add an **optional variant dimension on one side of a cell**. Today a cell is
`(archetype_a, archetype_b)`; the variant-aware form is `((archetype_a, variant_a), archetype_b)` — the
*subject* is resolved to its camp, the *opponent* stays at parent granularity (opponent camps are
usually unobservable from tournament data anyway). Concretely: extend the `match_results` join to carry
the subject's variant, and let `build_matrix` accept a `variant` filter that narrows the subject pool.

**Preserve the tier gates unchanged.** The existing Beta-Binomial shrinkage + speculative(<30) /
evolving(30–99) / established(≥100) tiers apply per cell exactly as today — splitting a subject shrinks
each cell's n, so most split cells will land speculative/evolving, and they surface **at that tier with
the honesty label**, never hidden and never blended back into the parent (the epic's locked bar; the
project's honest-degrade policy). This is the same discipline already used when a parent's own cells are
thin — no new honesty machinery, just a finer partition subject to the same gates.

### Per-card win-rate

`compute_card_winrates` today mixes a card's results across every archetype that plays it — the
contamination that made Mishra's Bauble read as a cut for Dimir Tempo while the within-archetype
subgroup said keep. Restrict the W/L denominator to the archetype's (or camp's) own decks, and emit an
**honest-degrade sign-conflict warning** when a card's marginal (cross-archetype) lift disagrees in
sign with its within-archetype/within-camp win-rate. Surface the subgroup win% directly in
`report subgroup` (it currently shows only copy-count deltas).

---

## 8. Implementation notes

- **Build on, don't replace, the existing primitives.** `analytics/subgroup.py` (`report subgroup`) is
  already the manual, single-axis discovery front-end and already computes the signature-card divergence
  Gate B needs — the discovery engine generalizes it from "human names one card" to "algorithm proposes
  the axis, statistics confirm it." `archetype/variants.py` + `data/variants/legacy.json` is the
  promotion target (the curated registry the human-confirm hook writes into); `decks.variant` is the
  persistence column both discovery and the analytics integration read/write.
- **Discovery-first sequencing (epic decision).** The matchup-cell and card-win-rate slices depend on
  discovery output. They are technically computable off the existing hand-curated variants today, but
  the epic deliberately builds the classifier first.
- **New dependencies.** The recommended stack (`scikit-learn` for TF-IDF/TruncatedSVD/GMM/silhouette,
  `hdbscan` or `umap-learn` for the primary path) are new to the project — flag for the epic's
  cost/sequencing. All are pure-Python/numpy-compatible and fit the existing analytics layer; none
  requires a service.
- **Scale.** Per-parent pools are ~200–2500 decks over ~20–35 flex features after reduction — trivial
  for any of these algorithms; discovery runs offline as a labeling pass (sibling to `label`), not in a
  hot path.
- **Honest-degrade at split granularity.** Every discovered camp carries its sample tier; every
  variant-conditioned cell carries the same tier label as any other cell. A split that only reaches
  speculative tier is shown, labeled speculative — the user decides. Nothing is hidden for being thin;
  nothing thin is blended into the parent to look thicker.

### Long tail (out of scope, noted)

Soft/overlapping camps (a deck straddling two builds) are better modeled by GMM/LDA-style soft
membership than hard HDBSCAN labels — worth an experiment but not v1. Cross-parent embedding approaches
(card2vec / Siamese deck embeddings) are the academic frontier but target card *generalization*, not
within-parent camp discovery, and are not needed here. Opponent-side variant resolution is deferred
(tournament data rarely identifies the opponent's camp).

---

## Sources

- Lucky Paper, "Mapping the Magic Landscape" — the Jaccard→UMAP→HDBSCAN deck-clustering precedent `[luckypaper-commander-map]{1}`
- Badaró, MTGOArchetypeParser — rules-based production baseline `[mtgo-archetype-parser]{2}`
- Kritschgau et al. (Sci. Reports 2024) — hypergraph community detection on MTG draft; color-vs-strategy + domain-verification caveats `[kritschgau-hypergraph]{3}`
- HDBSCAN docs — parameters + high-dimensional limitation `[hdbscan-docs]{4}`
- scikit-learn clustering guide — curse of dimensionality, DBSCAN vs HDBSCAN, silhouette, linkage `[sklearn-clustering]{5}`
- scikit-learn mixture guide — GMM/BIC + small-sample divergence `[sklearn-mixture]{6}`
- scikit-learn decomposition guide — TruncatedSVD/LSA vs sparsity `[sklearn-decomposition]{7}`
- UMAP clustering docs — preprocessing + false-tears caution `[umap-clustering]{8}`
- Silhouette (Wikipedia) — range, thresholds, convexity bias `[silhouette-clustering]{9}`
- Cosine similarity (Wikipedia) — definition + sparse-vector advantage `[cosine-similarity]{10}`
- Jaccard index (Wikipedia) — definition `[jaccard-index]{11}`
- Bray–Curtis (Wikipedia) — count dissimilarity, not a metric `[bray-curtis]{12}`
- Gao, Bien & Witten (JASA 2024) — selective inference / double-dipping `[gao-selective-inference]{13}`
- Stability estimation review (WIREs 2023) — co-membership stability thresholds `[cluster-stability-review]{14}`
- Tibshirani, Walther & Hastie (2001) — gap statistic `[tibshirani-gap]{15}`

Additional prior art consulted (context, not load-bearing; not attested here): Hau/Plotkin/Tran
(Stanford CS229 2012, k-means on frequency vectors + manual validation), Bertram/Fürnkranz/Müller
(arXiv 2407.05879, Siamese deck/card embeddings; notes human play converges to "fewer than 100
archetypes" as an open problem), an LDA-topic-model deck-archetype writeup, and the card2vec project —
all corroborate the "hard clustering / soft topic model / embedding" families and the universal
reliance on human validation.
