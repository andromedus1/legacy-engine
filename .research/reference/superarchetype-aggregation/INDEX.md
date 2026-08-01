# Bibliography — superarchetype-aggregation corpus

Append-only. `N` is the human-readable index; the citation lint resolves by `handle`.

| N | handle | source | url |
|---|--------|--------|-----|
| 1 | superarchetype-gelman-multilevel | Gelman, "Multilevel (hierarchical) modeling: what it can and can't do" (2005) | https://people.eecs.berkeley.edu/~russell/classes/cs294/f05/papers/gelman-2005.pdf |
| 2 | superarchetype-stan-pooling | rstanarm vignette, "Hierarchical Partial Pooling for Repeated Binary Trials" | https://mc-stan.org/rstanarm/articles/pooling.html |
| 3 | superarchetype-james-stein | "James–Stein estimator" (Wikipedia) — dominance, total-vs-individual risk | https://en.wikipedia.org/wiki/James%E2%80%93Stein_estimator |
| 4 | superarchetype-bradley-terry2 | Turner & Firth, BradleyTerry2 vignette (JSS 48(9) companion) — structured BT + player random effects | https://cran.r-project.org/web/packages/BradleyTerry2/vignettes/BradleyTerry.html |
| 5 | superarchetype-cochrane-heterogeneity | Cochrane Handbook ch.10 §10.10 — Chi² test power, I² bands, threshold caveat | https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10 |
| 6 | superarchetype-meta-heterogeneity | Harrer et al., "Doing Meta-Analysis in R" — Q, I², τ² formulas + caveats | https://doing-meta.guide/heterogeneity.html |
| 7 | superarchetype-meta-pooling | Harrer et al., "Doing Meta-Analysis in R" — inverse-variance + random-effects weights | https://doing-meta.guide/pooling-es.html |
| 8 | superarchetype-hhi | "Herfindahl–Hirschman index" (Wikipedia) — Σ shares², 1/H effective number, DOJ bands | https://en.wikipedia.org/wiki/Herfindahl%E2%80%93Hirschman_index |
| 9 | superarchetype-kish-deff | PracTools vignette, "Design Effects and Effective Sample Size" — Kish deff, n_eff | https://cran.r-project.org/web/packages/PracTools/vignettes/Design-effects.html |
| 10 | superarchetype-simpsons-paradox | "Simpson's paradox" (Wikipedia) — pooled-rate reversal under unequal exposure | https://en.wikipedia.org/wiki/Simpson%27s_paradox |
| 11 | superarchetype-pvclust | pvclust (Suzuki & Shimodaira) — multiscale-bootstrap AU p-values on dendrogram branches | https://github.com/shimo-lab/pvclust |
| 12 | superarchetype-pvp-counter-clustering | "Identifying and Clustering Counter Relationships of Team Compositions in PvP Games" (arXiv 2408.17180) | https://arxiv.org/html/2408.17180v1 |
| 13 | sklearn-clustering | scikit-learn clustering guide — agglomerative linkage criteria; DBSCAN vs HDBSCAN density assumption (first attested in the `subarchetype-discovery` corpus) | https://scikit-learn.org/stable/modules/clustering.html |
| 14 | hdbscan-docs | HDBSCAN docs — `min_cluster_size` / `min_samples` semantics and noise labelling (first attested in `subarchetype-discovery`) | https://hdbscan.readthedocs.io/en/latest/parameter_selection.html |
| 15 | jaccard-index | "Jaccard index" (Wikipedia) — set-overlap similarity on core-card sets (first attested in `subarchetype-discovery`) | https://en.wikipedia.org/wiki/Jaccard_index |
| 16 | bray-curtis | "Bray–Curtis dissimilarity" (Wikipedia) — abundance dissimilarity; not a metric (first attested in `subarchetype-discovery`) | https://en.wikipedia.org/wiki/Bray%E2%80%93Curtis_dissimilarity |
| 17 | cosine-similarity | "Cosine similarity" (Wikipedia) — sparse-vector similarity (first attested in `subarchetype-discovery`) | https://en.wikipedia.org/wiki/Cosine_similarity |
| 18 | cluster-stability-review | Stability estimation review (WIREs 2023) — co-membership stability thresholds (first attested in `subarchetype-discovery`) | https://pmc.ncbi.nlm.nih.gov/articles/PMC9787023/ |
| 19 | gao-selective-inference | Gao, Bien & Witten (JASA 2024) — double-dipping / post-clustering inference (first attested in `subarchetype-discovery`) | https://arxiv.org/abs/2012.02936 |
| 20 | kritschgau-hypergraph | Kritschgau et al. (Sci. Reports 2024) — statistical vs human-intuitive cluster count; domain verification (first attested in `subarchetype-discovery`) | https://www.nature.com/articles/s41598-024-52298-8 |
| 21 | luckypaper-commander-map | Lucky Paper, "Mapping the Magic Landscape" — MTG deck-clustering prior art (first attested in `subarchetype-discovery`) | https://luckypaper.co/articles/mapping-the-magic-landscape/ |

Entries 13-21 are sources already attested for the sibling `subarchetype-discovery` corpus. They are
listed here so this corpus's bibliography is readable standalone; the attestation files are shared
(one attestation per handle, never duplicated) and `/citation-lint` resolves them by handle.
