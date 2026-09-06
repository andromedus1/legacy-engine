---
id: idea-affected-component-parent-reconstruction
created: 2026-08-12
updated: 2026-08-12
tags: [analytics, advisory, honesty]
---

# Reconstruct an affected parent from surviving subarchetypes

When a B&R event or other tectonic shift materially affects only one subarchetype, do not erase the
credible matchup history of the entire parent archetype. Reconstruct the parent's current estimate
from its children: unaffected subarchetypes retain their independently admissible windows, while the
affected child uses only post-shift evidence. Combine the child estimates using current or
transition-field composition weights, with full uncertainty and provenance.

The motivating example is Doomsday after The Fantasticar ban. If the Fantasticar camp is the only
directly affected child, its pre-ban evidence and field weight must not leak forward. Non-Fantasticar
Doomsday camps may still carry credible history if their own era checks remain clear. The parent
Doomsday row could therefore remain informative as the weighted mixture of surviving builds instead
of being globally reset.

This is a reverse direction from the existing hierarchy: today a thin camp can shrink toward a
leave-camp-out parent/sibling reference, but an affected parent is not rebuilt from independently
valid children. Treat child-to-parent reconstruction as aggregation, not as independent pseudo-data
or a generic prior injected into the affected child.

Useful safety constraints from the discussion:

- Start with the narrow case where exactly one child is attributable as affected.
- Require a trustworthy child partition, including explicit unlabeled residue.
- Preserve subject and opponent era clamps for every child matchup cell.
- Give the affected child no pre-shift evidence; a banned/disappeared child gets no carry-forward
  composition weight.
- Do not assume siblings are stable merely because they did not contain the banned card; their own
  era detector may still reset them.
- Propagate uncertainty in child matchup estimates and composition weights rather than averaging
  point estimates.
- Label the parent as reconstructed, including contributing children, weights, windows, exclusions,
  and refusal reasons.
- Refuse reconstruction when the partition, coverage, composition, or sibling heterogeneity cannot
  support it; retain the current degraded parent result in that case.
- Let direct post-shift parent evidence take over as it accumulates.

This should eventually be evaluated against the existing credible-window, pair-window,
leave-camp-out hierarchy, and future-only benchmark contracts. It is intentionally parked rather
than activated while the new transition-field ranking behavior settles through dogfooding.
