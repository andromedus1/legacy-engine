---
id: epic-superarchetype-layer-era-core-pools
kind: story
stage: done
tags: [analytics, archetype]
parent: epic-superarchetype-layer
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-08-01
updated: 2026-08-02
---

# Per-entity era core pools for superarchetype clustering

## Brief

`superarchetype run` computes every archetype's core set from ONE global `--since` window. The
principled endpoint per the era discipline (epic addendum #2) is per-entity pools: each
archetype's core computed from its OWN stable era (`entity_eras.stable_since`, ban-only fallback),
so a rebuilt archetype is represented by its current generation and an undisturbed archetype keeps
its full history. Keeps the one-window CLI as the explicit-override path. Note the known limit
this does NOT solve: behaviorally-kin families whose current compositions diverged (D&T+Energy)
stay separate — that is the curated layer's job. Design should reuse consume.py's horizon
resolution; the churn diagnostic must compare like-for-like across runs.

## Design

### Contract

- With no explicit `--since`, `superarchetype run` resolves every labeled parent archetype through
  `era_horizons`: exact stored era first, then the existing ban-only fallback. Each deck contributes
  to its archetype's core only when its tournament date is on or after that archetype's horizon.
- `--since` remains the explicit uniform-window override and takes precedence over era data. It is
  the reproducibility/diagnostic path, not the default serving policy.
- The clustering query remains composition-only: `decks`, `deck_cards`, `tournaments`, and the
  already-derived `entity_eras`/ban affectedness ledger. It never reads rounds or matchup outcomes.
- Persist the window policy and per-entity horizons in the registry. Consumers must distinguish an
  era-aware taxonomy from a full-corpus registry; `window_since=None` alone is no longer allowed to
  imply “full corpus.”
- A missing era ledger honestly degrades entity-by-entity to ban-only horizons and records the
  existing era audit warning in registry metadata.

### Offline comparison preview

Add a dry-run comparison mode that computes the era-aware candidate beside a named uniform-window
candidate without writing either. Report definer/assigned field share, cluster count, member moves,
co-membership agreement, staples, unassigned labels, and per-entity horizon provenance. The preview
is the evidence for selecting the serving taxonomy; matchup coverage remains deliberately absent so
the composition cut cannot be tuned against its downstream payoff.

### Tests

- Hermetic mixed-era corpus proving two archetypes receive different deck pools in one query.
- Explicit global `since` override remains field-compatible with the old loader.
- Missing era tables take the named ban-only degradation path.
- Registry JSON and DuckDB round trips retain the window policy/horizon audit metadata.
- CLI dry-run/compare never mutates the registry or derived cache.

## Implementation order

1. Add the dated, per-entity composition loader and typed window-policy metadata.
2. Thread default era-aware behavior and the explicit global override through the offline run.
3. Add comparison diagnostics and CLI rendering.
4. Run the real-corpus preview before writing the serving registry.

## Implementation notes — 2026-08-02

Implemented the era-aware core input as the default offline policy. `load_archetype_decks` accepts
a per-archetype horizon map and filters dated decks before core construction; an explicit `--since`
still selects the legacy uniform-window policy. `run_superarchetypes` resolves parent labels through
the shared `era_horizons` adapter, persists the typed window policy, per-entity `(label, since,
source)` ledger, and audit lines through both JSON SSOT and the DuckDB cache. Old cache schemas read
as `window_policy=global` until the next rebuild rather than failing during rollout.

`superarchetype run --dry-run --compare-since <date>` is a strictly non-writing comparison path.
It reports definer/placed field share, cluster counts, co-membership agreement, and moves. The normal
CLI and matrix audit distinguish `PER-ENTITY ERAS` from `FULL CORPUS`; missing era data retains the
named ban-only degradation. The best-call refresh runbook now calls `superarchetype run` without a
global start date, and the knowledge indexes were regenerated with zero lint errors.

### Real-corpus preview (seed 0, n_boot 200; read-only)

| policy | labels | definers | definer field | clusters | multi-member | placed | stability |
|---|---:|---:|---:|---:|---:|---:|---:|
| per-entity era | 593 | 106 | 87.39% | 65 | 64 | 98.52% | 0.9833 |
| uniform since 2026-05-11 | 183 | 30 | 83.79% | 21 | 19 | 98.45% | 0.9440 |
| uniform since 2026-06-29 | 128 | 15 | 70.72% | 3 | 3 | 99.15% | 0.8743 |

The era policy resolved 81 labels from stored eras and 634 through the named ban-only fallback.
Co-membership agreement was 0.932 against both the serving registry and the 2026-05-11 rerun, versus
0.476 against the thin current-regime rerun. The candidate was deliberately **not persisted**: 65
clusters is materially more granular than the serving taxonomy's 21 and needs product review before
it becomes the headline page registry. This is exactly why compare mode is non-writing.

### Verification

- Era-aware/superarchetype focused suite: 249 passed.
- Full project suite: 3,524 passed, 1 existing seeded-UMAP warning.
- Knowledge-index lint: 0 errors, 6 pre-existing warnings.
- `git diff --check`: clean.
