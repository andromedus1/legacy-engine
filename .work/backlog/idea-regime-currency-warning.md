---
id: idea-regime-currency-warning
created: 2026-06-27
tags: [honesty, advisory]
---

**Surface a "regime-currency %" on field-load, and warn when a custom field's implied
window is dominated by a *prior* ban regime.**

Found dogfooding (2026-06-27): the maintainer's "last 4 months" local organizer data spans two ban
regimes — only **~29%** of it is the current (Undercity Informer, 2026-05-18→) regime;
**71%** is the prior post-Entomb/Nadu regime. We built a custom `--field` file from that
4-month aggregate and ran best-deck/best-call on it. The conclusion **flipped** under
regime correction: Dimir Tempo ranked *above* Doomsday on the polluted field (0.507 vs
0.488) but *below* it on a regime-clean current field (0.483 vs 0.501). Nothing in the
tool flagged that the field was ~1/3 quality.

What to add:
- When `_load_field` ingests a custom field with per-line counts (or when building the
  global field over a window), compute and print a **regime-currency %**: the share of
  the contributing data that falls in the current ban regime (use the same
  `regime_windows()` the trends/affectedness code already uses).
- **Emit an honest-degrade warning** when regime-currency < ~50% (e.g.
  `// [warn] field is 29% current-regime (71% prior regime 'after Entomb...'); composition
  may not reflect the current meta — consider windowing to the current regime`).
- Reinforce the existing guardrail in docs/help: **window the FIELD composition to the
  current regime, but keep the MATCHUP MATRIX adaptive** — `--regime current` on the matrix
  collapses coverage to ~0% (26-day window starves n≥30 cells). The two windows are
  independent and should be set independently.
- Stretch: a `--regime-window` flag on field-load that reweights a multi-regime custom
  field toward the current regime using the engine's own composition movers, for cases
  where the user only has a blended aggregate (the maintainer's local-meta data can't be split).

Related honesty gaps from the same session: [[idea-archetype-conditioned-card-winrate]],
idea-acquire-color-identity-filter. Methodology lives in the user-memory
`analysis-statistical-context-gates`.
