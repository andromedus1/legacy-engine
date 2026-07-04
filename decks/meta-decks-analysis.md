# Meta decks — 4 engine-built lists (the local meta + online, 2026-07-04)

Stage 2 of the deck-prep arc. Corpus through 2026-07-01, current regime (2026-05-18+),
deterministic solver (PR #35). Lists: [meta-local-dimir-tempo](meta-local-dimir-tempo.txt),
[meta-online-dimir-tempo](meta-online-dimir-tempo.txt),
[meta-local-bestpick-painter](meta-local-bestpick-painter.txt),
[meta-online-bestpick-doomsday](meta-online-bestpick-doomsday.txt).

## Best-pick rankings (advise positioning --candidates, seed 42; leans, never verdicts)

**local field** (sort = Q0.25, risk-adjusted): Painter S*=0.528 (P(best)=0.093, cov 0.48) >
Death & Taxes 0.514 (cov 0.62) > Blue Artifacts 0.509 > **Dimir Tempo 0.508** > White Beanstalk
0.506 > Doomsday 0.498. All CIs overlap heavily (width ~±0.10); five archetypes' P(best) sum to
under 0.27 — the honest read is "the local field has no dominant call; Dimir Tempo is
coin-flip-competitive with the best". Shift since 2026-06-27: D&T topped then; Painter tops the
refreshed corpus. Midrange piles (Black/Azorius/Jeskai/Esper, Saga Storm, Energy) rank with
cov≈0 — no per-cell matchup data vs this field composition; their S*=0.500 is the uninformed
prior, not evidence.

**Online field**: Doomsday S*=0.580 > Death & Taxes 0.564 > **Dimir Tempo 0.534** > Tron 0.530 >
Lands 0.521. Coverage is cov≈0 for most (online-filtered matchup cells are thin) — Doomsday's
top slot is a lean with the widest caveat, but it is consistent with the 2026-06-27 finding
(Doomsday > Dimir on regime-clean data) and now clears it by a larger margin on 3× the corpus.

**Best-pick collision rule** (epic decision): Dimir Tempo topped neither meta, so no collision —
best-picks are Painter (the local meta) and Doomsday (online).

## The four lists — construction + honesty notes

| List | Consensus n | Tier | Board (natural budget) | Overrides applied |
|---|---|---|---|---|
| Dimir Tempo (the local meta) | 125 (all prov.) | established | 15 (6 dedicated) | −2 Defense Grid, −1 Damping Sphere |
| Dimir Tempo (online) | 86 (online) | evolving | 15 (9 dedicated) | −2 Defense Grid, −1 Damping Sphere |
| Painter (the local meta) | 37 (all prov.) | evolving | **7 (2 dedicated)** | −2 Defense Grid |
| Doomsday (online) | 112 (online) | established | 15 (8 dedicated) | −1 Defense Grid |

- **Painter's 7-slot board is honest, not broken**: the natural-budget τ stop found only 2
  dedicated slots worth committing against this field, the hedge added 5 insurance picks, and
  the considering pool ran dry after the Defense Grid override. The engine declines to pad; the
  remaining 8 slots are pilot preference. Thinnest list (n=37) — treat as a sketch.
- **Refills after overrides** (by considering residual, labeled in each file header): Toxic
  Deluge + Barrowgoyf + Brazen Borrower (Dimir the local meta), Toxic Deluge + Thoughtseize + Barrowgoyf
  (Dimir online), Barrowgoyf (Doomsday online).
- **Known scorer bias carried into these lists**: the hedge spreads 1-ofs across pitch-class
  counters (FoN 1, Consign 1, Flusterstorm 1 …) where winners' copy modes are 2-3 — the
  copy-count study's valley-at-1 finding (feature-min-viable-copy-count tracks the model fix).
  the maintainer's personal board (dimir-tempo-optimized.txt) hand-corrects this; these four meta
  reference lists deliberately show the engine's raw shape + mechanical overrides only, so the
  before/after remains visible for the arc's final study.
- Barrowgoyf/Brazen Borrower enter via the promoted-empirical-pool with fallback tag attribution
  (warnings preserved) — the same catalog gap idea-hoser-catalog-new-card-gap tracks.

## Reproduce

`generate consensus --archetype <A> [--provenance online]` + `recommend_sideboard` (smart,
hedge=expected) vs the meta's field; overrides + refills per file headers. Positioning:
`advise positioning --deck decks/dimir-tempo-current.txt --field decks/local-field-since-518.txt
--candidates <field archetypes> --seed 42` (online: `--provenance online`).
