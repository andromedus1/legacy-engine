---
id: idea-ilp-tiebreak-nondeterminism
created: 2026-07-03
tags: [advisory, sideboard]
---

# ILP tie-break nondeterminism — recommendations vary run-to-run

Observed during feature-sfv-breadth-objective validation (one run surfaced Nihil Spellbomb instead
of Dauthi Voidwalker; noted as pre-existing, then left untracked — filed now per review). The CBC
ILP has no deterministic tie-break, so equal-objective boards can differ across runs. For an engine
whose ethos is auditability, recommendations should be reproducible: add a deterministic tie-break
(e.g. lexicographic secondary objective or stable ordering into the solver) or at minimum an
audit-echo line acknowledging ties. The greedy path already tie-breaks by name.
