---
id: fix-recommendation-test-coverage
kind: story
stage: drafting
tags: [testing]
parent: null
depends_on: []
release_binding: null
gate_origin: tests
created: 2026-06-13
updated: 2026-06-13
---

# Recommendation-quality + threading test gaps (gate-tests, Medium)

- Overpriced-printing flag FIRING path (`acquire.py` orchestrator $33-vs-$2) only asserted negatively;
  add a positive test via `acquire_plan` with seeded card_prices.
- `tune_deck(collection=)` threading untested (populated-owned + gated byte-identical).
- `tune_deck(players=/--strong)` threading + `--players`-beats-`--strong` precedence untested end-to-end.
- `report meta --venues` default-window behavior untested + spec/code divergence (defaults full-corpus,
  not current regime — see fix-venues-regime-default).
- `generate doctor` no-archetype classify branch + Δ-rendering; `report subgroup`/`report variants` CLI
  smoke; interaction-fact evidence content (scope substring), not just non-emptiness.

