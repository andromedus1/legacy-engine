---
id: gate-cruft-low-v030
created: 2026-07-11
tags: [cleanup]
---

Low-confidence cruft note from the v0.3.0 gate (awareness, keep-leaning): advisory/sweep.py:326
wraps `backtest_board` (documented never-raises) in a belt-and-braces except that converts a
hypothetical failure into per-entry skipped_reason + warning. Textbook "except around can't-throw"
shape, BUT consistent with the honest-degrade batch posture (one archetype must not abort the
sweep). Recommendation: keep; revisit only if the never-raises contract is ever formalized.
