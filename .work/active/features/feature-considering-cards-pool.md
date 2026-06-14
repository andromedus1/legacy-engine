---
id: feature-considering-cards-pool
kind: feature
stage: review
tags: [generation, advisory]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Emit a ~30-card "considering" pool, not just the final 15

## Brief
Deck/sideboard generation emits only the final 15. Surface a larger (~30-card) "considering" pool — the
flex options and meta-call alternatives the engine weighed (next-best by coverage/value, ranked, labeled)
— so the user sees what was on the bubble. Additive output on the sideboard recommender / `advise refresh`
/ `advise acquire` surfaces; the chosen 15 is unchanged.

## Design

**Problem:** The solver (ILP/greedy) produces a final 15, but the user has no visibility into what
candidates were on the bubble — what the engine would have picked 16th, 17th, etc. These are the
flex slots and meta-call alternatives the user may want to manually adjust.

**Approach — residual marginal gain ranking:**

After solving for `final_cards`, compute the coverage state (element → copies covered). For every
candidate NOT at max_copies in the final solution, evaluate its residual marginal gain given that
coverage state: `Σ_e weight_e × marginal_g(cov_e + 1)`. This is exactly the "what would greedy pick
next" computation — a pure function over the existing model, requiring no additional DB work.

Rank all residual-gain > 0 candidates by that gain DESC, card name ASC (deterministic tie-break).
Cap at `_CONSIDERING_CAP = 15` (chosen 15 + considering 15 ≈ 30 total context).

**New symbols:**
- `ConsideringCard` (frozen dataclass): `card`, `marginal_gain`, `covers_elements`, `label`, `promoted`.
- `_rank_considering_pool(model, final_cards, *, cap, promoted_names)` — pure, no DB.
- `_considering_label(card_name, element_ids, model, cov_counts)` — formats coverage label for top-2 elements.
- `SideboardPackage.considering: tuple[ConsideringCard, ...]` — additive field, default `()`.

**Gated-additive:** `final_cards`, `trace`, `covered_weight`, and all existing fields are byte-identical
to pre-feature. The considering pool is purely additive output. Early-return paths (empty model) default
to `considering=()`.

**Render surfaces:**
- `advise sideboard` CLI (`cli.py`): "Considering (flex / meta-call alternatives)" section after the chosen 15,
  showing card name, gain, empirical tag, and label.
- `refresh.py _render_venue_package`: same section after the Sideboard (15) block, sourced from
  `td.sideboard_pkg.considering` (the full `SideboardPackage` added as additive field `TunedDeck.sideboard_pkg`).

**`TunedDeck.sideboard_pkg`** — new additive field (`object | None`, default `None`) carrying the full
`SideboardPackage` from `recommend_sideboard`. Set at both `TunedDeck` constructor sites in `tuning.py`.

## Implementation notes

Files touched:
- `src/legacy_engine/advisory/sideboard.py`: added `ConsideringCard`, `_rank_considering_pool`,
  `_considering_label`, `_CONSIDERING_CAP`; added `considering` field to `SideboardPackage`;
  call `_rank_considering_pool` in `recommend_sideboard` Step 6c.
- `src/legacy_engine/advisory/__init__.py`: exported `ConsideringCard`.
- `src/legacy_engine/advisory/refresh.py`: rendered considering pool in `_render_venue_package`,
  sourced from `td.sideboard_pkg.considering`.
- `src/legacy_engine/generation/tuning.py`: added `sideboard_pkg` additive field to `TunedDeck`;
  populated at both `TunedDeck(...)` constructor sites.
- `src/legacy_engine/cli.py`: rendered considering pool in `advise_sideboard` after the chosen 15.
- `tests/test_sideboard.py`: added `TestConsideringPool` (12 tests).

Test suite: 2162 passing (was 2150 before; 12 new tests added).
Ruff: no issues.
