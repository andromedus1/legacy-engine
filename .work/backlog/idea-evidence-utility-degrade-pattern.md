---
id: idea-evidence-utility-degrade-pattern
created: 2026-08-12
updated: 2026-08-12
tags: [analytics, advisory, honesty, testing]
---

# Evidence utility and graceful claim degradation pattern

Capture the broader lesson from the credible-window ranking failure as a reusable project pattern,
not only as one feature's postmortem. The system has strong provenance, windowing, uncertainty, and
validation structure, but can turn proof-grade gates into speaking gates: admissible evidence is
suppressed until the product says almost nothing, making the analysis technically honest but
practically useless.

Update or complement `.agents/skills/patterns/honest-degrade-marker.md` with the stronger principle:

> Use all admissible evidence. Degrade confidence and claim strength before suppressing output;
> suppress only invalid or genuinely unscorable results.

Preserve these implications for later scoping:

- Keep invalid, contaminated, and inadmissible evidence excluded.
- Reuse admissible evidence through explicit priors, hierarchy, transition models, or other
  uncertainty-bearing estimates when appropriate.
- Label observation, imputation, prior contribution, confidence, and validation status separately.
- Treat proof-grade grounding as a confidence tier or badge rather than an automatic existence gate.
- Prefer a useful lower-confidence estimate with a named reason over a silent or nearly empty output.
- Do not fabricate magnitude when no defensible estimate exists; explicit unavailable/null behavior
  remains correct for truly unscorable cases.
- Add usefulness and non-vacuity regression contracts alongside numerical correctness tests so a
  file that exists but communicates no actionable result cannot silently count as success.
- Review existing patterns and analytics consumers for language that could incorrectly encourage
  broad suppression whenever data is merely thin.

This idea is parked for later pattern/design work. It should not reopen the completed credible-window
feature or weaken any existing evidence-integrity gate.
