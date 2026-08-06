---
id: release-v0.4.0
kind: release
stage: quality-gate
tags: []
parent: null
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-08-05
updated: 2026-08-05
---

# Release v0.4.0

The stable-era release: every statistic windows to each archetype's (and camp's) own detected
stable era — the largest stretch of still-solid data — with the triggering disturbance named.
Also carries the composition-derived superarchetype layer, the one-pass multi-split camp matrix
with cross-camp P(best), and the strategic-plan view on the Best Deck / Best Call page.

## Bound items

52 items: 51 active done items (2 epics, 15 features, 34 stories) plus 1 late-bound archived
stub (`feature-refresh-keyed-reload`, `archived_atop: v0.3.0` — done atop the prior baseline and
never claimed by a release).

Epics: `epic-stable-era-windows`, `epic-superarchetype-layer`.

## Gate runs
- **gate-tests** (2026-08-05) — 1 finding (0 critical, 0 high, 0 medium, 1 low → backlog).
  Integrity pass clean: every `skip` carries a named reason, no tautological or self-comparing
  assertions, no test files deleted in the bundle's commits, zero xfails. Suite grew 2,578 →
  3,540. One Low ambient finding: `gate-tests-stale-xfail-docstring`.
- **gate-cruft** (2026-08-05) — 0 findings. Every `# noqa` in the bundle's new packages
  (`superarchetype/`, `eras/`) carries an inline justification; no TODO/FIXME/XXX markers, no
  dead code or compatibility shims found in the bundle's surface.
- **gate-docs** (2026-08-05) — 1 finding, fixed in-gate and bound:
  `gate-docs-readme-suite-count-drift` (README asserted 3,532 passing / "UMAP warning"; actual is
  3,540 passing / one optional-extra skip). Rolling-foundation drift in the first doc an outside
  contributor reads. CHANGELOG's Unreleased section is present and describes this release.
- **gate-patterns** (2026-08-05) — 1 finding (Low, ambient → backlog):
  `gate-patterns-multi-split-one-pass-sweep`, a 6-call-site recurring shape not covered by the 20
  documented patterns.

### Gate execution note — reduced isolation

All four gates ran **inline in the host context** rather than in source-read-only deep scanner
sub-agents, per each gate skill's documented fallback. Recorded here because it lowers the
isolation guarantee: the analysis shares context with the release orchestration rather than
coming from an independent reader. No gate produced a release-blocking finding; the single
release-relevant finding (README drift) was a factual correction applied and verified in-gate.

