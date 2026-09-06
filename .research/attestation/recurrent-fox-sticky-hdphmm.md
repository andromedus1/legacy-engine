---
source_handle: recurrent-fox-sticky-hdphmm
fetched: 2026-08-13
source_url: https://ics.uci.edu/~sudderth/papers/icml08.pdf
provenance: source-direct
source_class: primary-paper
substrate_confidence: source-direct
---

# Fox et al. — HDP-HMM with state persistence

## Summary

Fox, Sudderth, Jordan, and Willsky present a sticky extension of the hierarchical Dirichlet process
hidden Markov model. The HDP prior allows an unknown state-space size, while an added
self-transition parameter counters the base model's tendency to split persistent regimes into
redundant, rapidly alternating states. The model maps each time point to a latent state and lets the
same state recur after intervening states.

## Key details

1. The HDP-HMM places a prior over a countably infinite state space and supports posterior inference
   over the number of states rather than fixing the cardinality in advance. — p. 1, introduction.
2. The authors show that the ordinary HDP-HMM can assign high posterior probability to unrealistically
   fast switching among redundant states when observations vary within a persistent state. — pp. 1–2,
   introduction and Figure 1.
3. In the sticky model, latent state `z_t` evolves according to a state-specific transition distribution
   and observation `y_t` is emitted from the parameter indexed by `z_t`. A positive `kappa` adds prior
   mass specifically to self-transition; setting `kappa = 0` recovers the ordinary HDP-HMM. — p. 3,
   Section 3 and Figure 3.
4. The paper also permits multimodal state emissions through per-state Dirichlet-process mixtures,
   while noting substantial posterior uncertainty if rapid state switching and multiple emission
   components are both unconstrained. — p. 6, Section 4.

## Structural metadata

Emily B. Fox, Erik B. Sudderth, Michael I. Jordan, and Alan S. Willsky, “An HDP-HMM for Systems
with State Persistence,” Proceedings of the 25th International Conference on Machine Learning,
Helsinki, 2008. Eight-page author-hosted conference paper.
