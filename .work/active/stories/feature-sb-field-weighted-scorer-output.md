---
id: feature-sb-field-weighted-scorer-output
kind: story
stage: done
tags: [advisory]
parent: feature-sb-field-weighted-scorer
depends_on: [feature-sb-field-weighted-scorer-wiring]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Explainable breakdown + coverage% diagnostic + field-share uncertainty

## Brief

Make the score auditable and honest: surface each recommended card's `ImpactBreakdown`
(centrality/symmetry/castability/draw-prob) in the `advise sideboard` output; render coverage% as a
labeled DIAGNOSTIC line (not the objective); apply Dirichlet field-share uncertainty (reuse
`advise positioning`'s machinery) to shrink tiny-share matchup weights and annotate confidence
tier; keep thin/uncovered field honest-degrade-labeled.

## Implementation

Covers parent feature **Unit B5** — see `feature-sb-field-weighted-scorer` § Implementation Units.
Files: `src/legacy_engine/advisory/sideboard.py` + the `advise sideboard` CLI render in
`src/legacy_engine/cli.py`. Tests: explainable-breakdown presence + coverage% diagnostic render in
`tests/test_sideboard.py`; uncertainty shrink/annotate behavior.

## Implementation notes (2026-07-03)

**Files changed**: `src/legacy_engine/advisory/sideboard.py` (production — new Unit B5 section +
`SideboardPackage` additive fields + wiring in `recommend_sideboard`), `src/legacy_engine/cli.py`
(`advise sideboard` render), `tests/test_sideboard.py` (17 new tests), `tests/test_cli.py` (3 new
CLI render tests). `src/legacy_engine/advisory/impact.py`, `linchpins.py`, and `positioning.py`
were read-only inputs — not modified (this story is output/explainability only; Units B1–B4's
scoring math is byte-identical before and after).

**Scope discipline**: everything new is computed from the ALREADY-SOLVED `final_cards` at the end
of `recommend_sideboard` and is purely additive to `SideboardPackage` (mirrors every other
gated-additive field already on that dataclass). `_build_coverage_model`'s `element_weight`
computation — the ILP/greedy objective, and therefore which cards get recommended — is untouched.
Confirmed empirically: `_ilp_solve`/`_greedy_solve`/`_build_coverage_model` show no diff in this
story; all 303 pre-existing `tests/test_sideboard.py` tests pass with zero changes.

**1. Explainable per-card breakdown** — new `CardImpactAnnotation` dataclass (breakdown,
reference_archetype, reference_share, confidence, brittle) + `_build_impact_annotations()`. For
each recommended card, picks the highest-field-share archetype among those its `attacks` tags are
relevant against (`_relevant_field_archetypes`) as the single "reference" opponent to anchor the
breakdown to — impact is inherently per-(card, opponent), never a flat score, so one concrete
anchor beats averaging across unrelated matchups into a meaningless composite. Recomputes
`impact()` at the card's ACTUAL recommended copy count (not the `copies=1` Unit B3 uses for the
element-weight multiplier) — a display-only recomputation, so it can show the more informative,
copy-count-accurate draw probability without touching the objective. Gated on `opponent_linchpins
is not None` (same gate B3 uses) — `{}` when no impact data exists; never a fabricated breakdown.
Counter-hosers (`"_hate"` in `attacks`) and cards with zero relevant archetypes are skipped (no
single coherent opponent to anchor to).

**2. Coverage% diagnostic** — `_relevant_field_archetypes` / `_card_coverage_pct` /
`_board_coverage_pct`, independent of impact-data availability (needs only `field` +
`archetype_tags`, the same tag-overlap test `_build_coverage_model` already uses internally).
Board-level is a UNION across recommended cards (an archetype double-covered by two cards
contributes its share once, not twice) — verified by a dedicated test
(`test_board_coverage_pct_is_union_not_sum`). Rendered in the CLI as a clearly-labeled diagnostic
block: `// coverage diagnostic — NOT the optimization objective (...)`, per the parent feature's
locked decision.

**3. Dirichlet field-share uncertainty — annotate + light shrink, not live reweighting.** Reused
`advise positioning`'s Dirichlet model verbatim: imported `positioning._DIRICHLET_GAMMA` and
`positioning._DEFAULT_RISK_QUANTILE` directly (the same private-constant-import precedent
`compare.py` already establishes) rather than re-declaring constants. New
`_dirichlet_share_lower_bound()` computes a lower-quantile risk-adjusted share per archetype —
but via the exact closed-form marginal (`scipy.stats.beta.ppf`; each Dirichlet component's
marginal is exactly `Beta(alpha_i, alpha_0 - alpha_i)`), not positioning's joint Monte-Carlo
`rng.dirichlet` draw. Positioning's MC exists to preserve cross-archetype CORRELATION for an
honest `P(best)` across competing decks (`rank_decks`); nothing here needs that correlation — only
an independent per-archetype conservative bound — so the lighter, deterministic, seed-free closed
form is the right-sized tool. Verified empirically against a synthetic field (200/188/3-deck
counts at ~50/47/3% shares): the thin 3-deck archetype's lower-quantile share drops to ~18% of its
point estimate, while the two well-sampled archetypes stay at ~98-99% — confirming the shrink only
bites where the field's own uncertainty is real.

  **Judgment call — confidence-tier + brittle-flag ANNOTATION, not a live reweighting of
  `element_weight`.** The parent feature's design note allows either "a light shrink of very-small-
  share cells" OR annotation as the conservative default; this story's own read-first framing is
  explicit that Unit B5 "does NOT change the scoring math." I resolved the tension toward the
  latter: the Dirichlet shrink IS real and computed (not just a label — see the empirical numbers
  above), but its output feeds a per-card `brittle: bool` flag (`brittle = True` when the
  lower-quantile share falls below `_BRITTLE_SHARE_SHRINK_RATIO` (0.5) of the point share) and a
  `confidence: ConfidenceLevel | None` tier (`tier_for_sample(field.counts[reference_archetype])`,
  reusing the project's standard confidence-metadata pattern rather than inventing a new one) —
  never fed back into `_build_coverage_model`'s `element_weight` or the ILP/greedy objective. A
  live reweighting would require re-baselining the ILP/greedy candidate-selection tests, which the
  parent feature's own "Core-replacement regression" risk note flags as exactly the failure mode
  to avoid, and Units B1–B4 already locked/reviewed that scoring core on main. This keeps the
  change 100% output-layer, zero-blast-radius to the solver, and still gives the pilot a concrete,
  numeric, honest signal ("this card's headline matchup is thin data — don't over-commit") rather
  than a vague qualitative warning.

**CLI render** (`src/legacy_engine/cli.py`, `advise_sideboard`): two new blocks after the card list
(gated on `display_cards` so `--owned-only` filtering is respected identically to the existing
card-list loop) — the coverage% diagnostic block, and the impact-breakdown block, e.g.:
```
  // coverage diagnostic — NOT the optimization objective (field-share relevance, not a measured win-rate lift):
    // Hydroblast: ~85% of field
  // board coverage diagnostic: ~92% of field addressed by this board (union across cards, not additive)
  // impact breakdown (auditable factors — see advisory/impact.py):
    // Hydroblast vs Izzet Delver (11.7% share): centrality=0.50 symmetry=1.00 castability=1.00 draw=0.79 → impact=0.396  [confidence=speculative]
```
Both follow the audit-echo comment-line convention (`click.echo("// ...")`) and the honest-degrade
marker convention (`[BRITTLE — ...]` note only when `brittle=True`; `confidence=no-data` — never a
guessed tier — when `field.counts` is unavailable). Manually smoke-tested end-to-end against the
real `data/legacy.duckdb` + a real deck (`decks/doomsday-tempo-boulder.txt`) and the live Boulder
field snapshot (`decks/boulder-field-current.txt`): renders cleanly, all reference-archetype
confidence tiers show `speculative` (consistent with the documented ~36%-of-matchups-thin Boulder
field), no crashes, no BRITTLE flags fired on this particular board (the reference archetypes
picked all had shares ≥6.8%, not thin enough to trip the 0.5 ratio in this snapshot).

**Tests added**: `tests/test_sideboard.py` — `TestRelevantFieldArchetypesAndCoveragePct` (tag
overlap, per-card and board-level union, counter-hosers score 0%), `TestDirichletShareLowerBound`
(None when `counts` is absent; thin-vs-established shrink magnitude; quantile monotonicity;
single-archetype degeneracy), `TestBuildImpactAnnotations` (no-impact-data path returns `{}`;
breakdown/reference/confidence populate correctly against a hand-built field+linchpins; `_hate`
and no-relevant-archetype cards skipped; brittle flag fires on a thin reference archetype; no
fabricated confidence/brittle when `field.counts` is absent), `TestRecommendSideboardOutputFieldsIntegration`
(real, non-mocked `recommend_sideboard` end-to-end: `Painter`'s curated `LINCHPIN_OVERRIDES` entry
— composition-independent — used to force a real non-None `opponent_linchpins` path without
needing to hand-derive linchpins from corpus composition; a parallel test confirms coverage%
populates even when `impact_annotations` stays the empty no-data dict). `tests/test_cli.py` —
`TestSideboardOutputDiagnostics` (coverage diagnostic + impact-breakdown render exact-format
assertions via a monkeypatched `recommend_sideboard` return value; brittle honest-degrade note
renders; the no-impact-data path renders no breakdown block on a real, non-mocked corpus).

**Verification**: `.venv/bin/python -m pytest -q` → **2419 passed** (2399 pre-existing + 20 new: 17
in `test_sideboard.py`, 3 in `test_cli.py`), zero re-baselining required anywhere in the suite.

**Deviations from the story sketch**: none requiring an escape hatch. The one interpretive
judgment call (annotate-only vs. live-reweighting for the Dirichlet shrink) is documented above
with its rationale; it stays within the design note's stated fallback ("annotate confidence + a
light shrink of very-small-share cells, not a full robust-optimization rewrite") and honors this
story's own explicit "does NOT change the scoring math" scope boundary.
