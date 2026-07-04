---
id: idea-docs-align-sideboard-scoring-model
created: 2026-07-03
tags: [documentation]
---

# Align foundation docs to the sideboard-scoring-model epic

`epic-sideboard-scoring-model` shipped a substantial change to the advisory subsystem that the
foundation docs don't yet reflect (flagged during Feature A + surfaced at the epic's final review):

- **`docs/ARCHITECTURE.md`** — references the retired `graveyard-reliant` vulnerability tag (now
  `graveyard-recursion` / `graveyard-fuel`); the advisory-methods section predates the decomposed
  impact scorer (`advisory/impact.py`: centrality × symmetry × castability × draw-prob, multiplicative
  gates), the linchpin model (`advisory/linchpins.py`), the maindeck-aware coverage discount, the
  slot-ROI/punt layer, and the board backtest (`advisory/backtest.py`).
- **`docs/briefs/advisory-methods.md`** — same drift: describes the pre-epic coverage/swing model.

Rolling-foundation principle: docs should describe present intent (no "previously"/migration prose).
This is correctly the **release docs gate's** job — it runs at `/agile-workflow:release-deploy` and
scans bound items for foundation-doc drift, so it will surface these when the epic is bound to a
version. Filed so the alignment isn't lost before then; also re-run `/knowledge-index` after editing.

Related shipped follow-ups from the epic: [[idea-scorer-element-weight-drawprob]],
[[idea-derive-attacks-land-destruction-mislabel]].
