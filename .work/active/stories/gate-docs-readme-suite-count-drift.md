---
id: gate-docs-readme-suite-count-drift
kind: story
stage: done
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.4.0
gate_origin: docs
created: 2026-08-05
updated: 2026-08-05
---

# README asserted a stale suite size and mischaracterized the UMAP state

## Finding

`README.md:39` and `README.md:309` both asserted **"3,532 passing, with one existing UMAP
warning and no xfails"**. On the v0.4.0 bundle the suite is **3,540 passing with one skip**, and
the UMAP condition is a *skip* (the optional `discovery` extra is unimportable when numba's
NumPy cap is exceeded), not a warning.

This is rolling-foundation drift: a false present-tense assertion about the repo's state, in the
first document an outside contributor reads — and the repo went public in this same cycle.

## Resolution

Fixed in-gate; both lines now read 3,540 passing with one optional-extra skip. The underlying
environment cause is tracked separately as `idea-local-ci-python-drift`.
