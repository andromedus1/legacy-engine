---
id: idea-parity-test-mutations-must-be-one-sided
created: 2026-08-01
tags: [testing, methodology]
---

**Mutation-testing a PARITY test must anchor the mutation to ONE side only.** Found by the
adaptive-window implementation (2026-07-31/08-01) while proving its parity assertions were
non-vacuous.

The agent's first attempt at one mutation used a plain `str.replace` on a shared code line — which
silently patched BOTH `build_multi_split_adaptive` and `build_adaptive_matrix`, because the two
implementations contain the identical line. Mutating both sides of a parity assertion symmetrically
keeps the assertion GREEN, which reads as "the test is robust" when in fact the test was never
exercised. The agent caught it, re-ran the mutation scoped to one function, and it went red as
expected (3 assertions).

Why this generalizes: parity tests are now a load-bearing pattern in this project — the multi-split
work rests entirely on "new fast path == old slow path, field-for-field", and the superarchetype
chain will want the same shape. Every one of those tests is vulnerable to the same false-confidence
failure, and the failure is silent by construction.

Candidate rule for the testing conventions / a pattern file: when mutating to prove a parity test
bites, edit the function under test by name (or via a temporary monkeypatch on that one symbol) —
never by text substitution that could match the reference implementation too. Consider whether a
tiny helper could make one-sided mutation the easy path.

Related: the 7-mutation non-vacuity evidence on `feature-multi-split-matrix-adaptive-window`, and
the 3-mutation evidence on `feature-multi-split-matrix-core-tally`. Also relates to the two vacuous
tests self-caught on 2026-07-31 (`matchup-plan-flex` looping over a fixture that produced zero plans;
the semantics band's considering-pool test with an empty pool in both arms) — same family of defect:
a test that passes while proving nothing.
