---
id: gate-docs-v030-drift
kind: story
stage: done
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.3.0
gate_origin: docs
created: 2026-07-11
updated: 2026-07-11
---

# v0.3.0 doc drift: #35 sweep never rolled forward + stale pattern anchors

9 findings from the docs gate; root cause of 5 of them: the archetype-sweep backtest (#35)
never propagated into ARCHITECTURE (CLI diagram, Conventions list, advisory module table),
SPEC (Pillar 4 + frontmatter capability decisions), README, or CHANGELOG. Plus: discover
`apply` + #40 collision fix missing from CHANGELOG Unreleased; audit-echo pattern count badly
stale (59 → 94 actual) with 2 shifted cli.py anchors; window-resolution-block 2 shifted anchors
(count → ~15); ARCHITECTURE inline datestamp stale; README missing all v0.3.0 commands.
Brief §8 hdbscan-vs-sklearn note: Low, research-tier, no edit required.

## Implementation notes (2026-07-11)
All 8 actionable findings drained in one pass: ARCHITECTURE (advise sweep in diagram + conventions
+ advisory/sweep.py module row + datestamp), SPEC (Pillar 4 sweep bullet + frontmatter capability
decisions), CHANGELOG (broadened to PRs #35-#40: sweep, discover apply, collision fix), README
(capability rows + 8 command examples), pattern docs (audit-echo 59→94 + 2 anchors;
window-block 2 anchors + count ~15 + scope tightened + conformer list corrected), digest counts.
Finding 9 (brief hdbscan note): research-tier, no edit per the gate. Knowledge index regenerated.
