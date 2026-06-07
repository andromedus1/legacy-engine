---
id: epic-advisory-output-honesty-field-consistency
kind: feature
stage: implementing
tags: [analytics, archetype, correctness]
parent: epic-advisory-output-honesty
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Field & Regime Consistency

## Brief

Make "what counts as the current field" consistent across the toolset. Two inconsistencies mislead
today. First, `report tiers` defaults to the full corpus (all-time), so it crowned Dimir Reanimator
#1 — a deck dead in the current regime — while the advisory layer already defaults to the current
regime; the two surfaces contradict each other. Second, 'Unknown' is treated as a real opponent in
some surfaces (matchup rows, meta-share) while already excluded from positioning fields, so the same
~8.5%-share placeholder is handled three different ways.

Covers: flipping `report tiers` to default to the current ban regime (with `--all-time` escape),
matching the regime-aware advisory default; applying consistent 'Unknown' semantics everywhere —
**bucket Unknown into the 'Other' tail in fields/positioning (where it's already excluded), but keep
it visible in meta-share as a labeled data-quality signal**.

Does NOT cover: the positioning coverage math (separate feature); sub-archetype variant splitting
(separate backlog item).

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: independent capability — parallelizable with positioning-coverage and transparency.

## Inherited design decisions
- **Tiers default**: flip to current-regime (with `--all-time` escape) for consistency with the
  shipped regime-aware advisory default.
- **Unknown semantics**: bucket into 'Other' in fields/positioning; keep visible + labeled as a
  data-quality signal in meta-share. Apply the same rule across matchup rows so Unknown isn't a
  silent real-opponent anywhere.

## Foundation references
- `docs/SPEC.md` — "Source transparency"; regime-awareness (epic-regime-aware-advisory, done)
- `src/legacy_engine/analytics/metashare.py` (`_is_never_other`), `advisory/window.py` (`resolve_advisory_window` + `resolve_regime`), `cli.py` (`report_tiers`, `_print_metashare_report`, `_print_matchup_matrix`)

## Design decisions
- **Tiers default**: `report tiers` gains the full `_window_opts` set and defaults to the **current
  ban regime** (reusing `resolve_advisory_window`/`resolve_regime` SSOT) with `--all-time` as the
  escape. Intentional divergence from `report meta` (descriptive → full-corpus default): tiers is an
  advisory "what to play now" surface, so a dead-deck crown is the bug.
- **Unknown display**: keep Unknown/Conflict rows in place but **label them** with a `‡` marker + a
  one-line footnote ("‡ unclassified — not positionable; excluded from advisory fields") in BOTH
  meta-share and the matchup matrix. Display-only; reuse the existing `_is_never_other` predicate as
  the SSOT for "unclassified". Fields/positioning already exclude these (no change there).
- **Matchup Unknown**: keep the row/col (the data is real), label it unclassified — no matrix-builder
  / data change.

## Architectural choice

Two display-layer changes plus tiers windowing, all in `cli.py`, reusing existing SSOT helpers
(Phase 5a: (A) reuse `resolve_advisory_window` + `_is_never_other`; (B) inline a tiers-specific window
resolver + a new unclassified predicate; (C) push labeling into the metashare/matchup data layer).
**Chosen: A.** Tiers windowing reuses `resolve_advisory_window` with `thin_floor=0` (deck-based, never
degrades) and `regime="current"` injected when no window flag is given — no new resolver, consistent
with `report meta`'s flag surface. Unknown labeling reuses `_is_never_other` (already the SSOT for
"these labels stay their own rows") so the predicate can't drift. B duplicates SSOT; C would change
data the descriptive reports are meant to show faithfully (the decision is explicitly display-only).

## Implementation Units

### Unit 1: `report tiers` defaults to current regime (trickiest — windowing)
**File**: `src/legacy_engine/cli.py` (`report_tiers`)

**Implementation Notes**:
- Add `@_window_opts` to the command; add `since/until/regime/all_time` params to the signature.
- Resolve the window, defaulting to current regime:
  ```python
  from legacy_engine.advisory.window import resolve_advisory_window
  if not (regime or since or until or all_time):
      regime = "current"          # tiers default (the fix)
  win = resolve_advisory_window(con, regime=regime, since=since, until=until,
                                all_time=all_time, thin_floor=0)  # deck-based: never degrade
  click.echo(f"// window: {win.requested_label}")
  ```
- Pass `since=win.since, until=win.until` into each `compute_metashare(...)` call (the 3 provenance bases).
- Trickiest because it must default-to-current WITHOUT breaking explicit `--all-time` (→ full corpus) or `--regime X`; verify precedence via the resolver (all_time > regime > since/until > injected-current).

**Acceptance Criteria**:
- [ ] `report tiers` with no window flags windows to the current regime (`compute_metashare` receives the current-regime `since`, not `None`).
- [ ] `report tiers --all-time` uses the full corpus (`since=None, until=None`).
- [ ] `report tiers --regime <X>` / `--since/--until` honor the explicit window.
- [ ] The window label is echoed in the header.

---

### Unit 2: label Unknown/Conflict as unclassified in meta-share + matchup
**File**: `src/legacy_engine/cli.py` (`_print_metashare_report`, `_print_matchup_matrix`)

**Implementation Notes**:
- Reuse `from legacy_engine.analytics.metashare import _is_never_other`.
- Meta-share: for rows where `_is_never_other(entry.archetype)`, append a `‡` marker to the row; after the loop, if any such row was printed, echo the footnote `‡ unclassified — not positionable; excluded from advisory fields`.
- Matchup: mark the row label (and, implicitly, the same name as a column) with `‡` when `_is_never_other(row_arch)`; echo the same footnote once if any unclassified archetype is present in `matrix.archetypes`.
- Keep the existing `*` fringe/speculative marker independent (the two markers coexist).

**Acceptance Criteria**:
- [ ] An `Unknown` (or `Conflict(...)`) row in meta-share shows the `‡` marker; a non-unclassified row does not.
- [ ] The footnote prints exactly once when ≥1 unclassified row is present, and not at all when none.
- [ ] The matchup matrix marks the `Unknown` row label `‡` and prints the footnote; numeric cells are unchanged.

## Implementation Order
1. **Unit 1** (tiers windowing) — independent; the headline fix.
2. **Unit 2** (Unknown labeling) — independent display change; do after.

## Testing
- `tests/` (cli/render) — construct a `MetaShareReport` with an `Unknown` entry + a normal entry; call `_print_metashare_report` and assert (capsys) the `‡` appears on Unknown only + the footnote prints once. Same shape for `_print_matchup_matrix` with an `Unknown` archetype. A no-unclassified report prints no footnote.
- Tiers windowing: a CLI/seam test (CliRunner over the seeded DB, or a resolver-level assertion) that no-flags → current-regime `since` is passed to `compute_metashare`, and `--all-time` → `None`. If a full DB invocation is heavy, assert at the `resolve_advisory_window(regime="current", thin_floor=0)` seam that `win.since is not None` and `--all-time` yields `win.since is None`.

## Risks
- **Existing `report tiers` output/tests change** — the default window flips from full-corpus to current-regime, so any snapshot/expectation of tiers content shifts. **Fallback**: `--all-time` reproduces the old behavior exactly; update expectations and document the intentional default change in the header echo.
- **`‡` is a non-ASCII glyph** — could surprise a strict-ASCII terminal/test. **Fallback**: it's display-only; if a test environment dislikes it, swap to an ASCII marker like `(unclassified)` — the footnote already spells it out.
