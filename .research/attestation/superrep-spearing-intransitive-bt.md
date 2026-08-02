---
source_handle: superrep-spearing-intransitive-bt
fetched: 2026-08-01
source_url: https://arxiv.org/abs/2103.12094
provenance: source-direct
substrate_confidence: source-direct
---

# Modelling Intransitivity in Pairwise Comparisons with Application to Baseball Data

## Summary

Spearing, Tawn, Irons, and Paulden extend Bradley–Terry by adding an antisymmetric
pair-specific intransitivity adjustment on the log-odds scale. Rather than estimating an
unrestricted adjustment for every pair, the model assigns pair effects to a learned number of
discrete intransitivity levels and assigns competitors to a learned number of skill levels. A
Bayesian reversible-jump sampler infers both counts and allocations. The classical
Bradley–Terry model is nested as the zero-intransitivity case. Simulation results show that
recovering the intransitivity structure becomes more reliable as repeated round robins increase;
the paper also reports out-of-sample gains over Bradley–Terry in simulated and American League
baseball data. An identification constraint fixes the pair effects involving one reference team,
so those fixed zeros are not substantively interpretable.

## Key passages

- Abstract and §1: the method allocates object pairs to one of a random number of intransitivity
  levels and objects to one of a random number of skill levels; it anticipates parsimony when the
  learned number of levels is smaller than the object count.
- §3.1, equation (6): the pair adjustment multiplies Bradley–Terry odds by
  `exp(theta_ik)`, equivalently adding `theta_ik` on the log-odds scale.
- §4.3.2: intransitivity levels are updated in reflected pairs because their signs reverse when
  the comparison direction reverses.
- §5, Figure 1 discussion: the posterior has difficulty recovering the correct number of levels
  in a lower-information scenario, while agreement with the simulated truth improves as the
  number of round robins grows.
- §6.2, Figure 4 discussion: pair effects satisfy `theta_ij = -theta_ji`; effects involving the
  reference team are fixed at zero for identifiability and are explicitly said not to describe a
  real property of that team.
- §6.2: once pair interactions are admitted, the authors state that there is no single obvious
  way to rank the teams.

## Structural metadata

Peer-reviewed version published in the *Journal of Computational and Graphical Statistics*
(2023), DOI 10.1080/10618600.2023.2177299. The fetched arXiv record provides the full paper text
with section anchors; version 2 corresponds to the publication period.
