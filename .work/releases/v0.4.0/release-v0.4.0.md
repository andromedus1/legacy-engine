---
id: release-v0.4.0
kind: release
stage: released
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

## Shipped items

Bodies live in git history — `git show <git ref>:<former active path>` recovers any pruned body.

| id | title | kind | archived_atop | git ref |
|----|-------|------|---------------|---------|
| `epic-stable-era-windows` | Per-entity stable-era detection → maximal solid windows everywhere | epic | — | `01d8576` |
| `epic-superarchetype-layer` | Superarchetype layer — pool strategy clusters so every row gets signal | epic | — | `01d8576` |
| `epic-sb-advisor-correctness-matchup-plan-flex` | Matchup-plan flex — unlock the OUT side, gate the IN side on axis relevance | feature | — | `01d8576` |
| `epic-stable-era-windows-consumption` | stable_since as the default horizon across all regime-windowed surfaces | feature | — | `01d8576` |
| `epic-stable-era-windows-detection` | Per-entity disturbance detection engine | feature | — | `01d8576` |
| `epic-stable-era-windows-discovery-gate` | Discovery temporal gate: stable-window clustering + era-mixing detection | feature | — | `01d8576` |
| `epic-stable-era-windows-era-ledger` | Era ledger: persistence, attribution, drift alarm, explainability | feature | — | `01d8576` |
| `epic-stable-era-windows-shrinkage` | Hierarchical cell shrinkage: parent-anchored + cross-era priors as default | feature | — | `01d8576` |
| `epic-superarchetype-layer-aggregation` | Random-effects pooled cluster cell — n_eff, the two gates, the intra-cluster flag | feature | — | `01d8576` |
| `epic-superarchetype-layer-best-call-fallback` | Per-cell superarchetype fallback + provenance chip on the best-call page | feature | — | `01d8576` |
| `epic-superarchetype-layer-chain` | Superarchetype rung — cluster-pooled cells in the matrix and in the shrinkage chain | feature | — | `01d8576` |
| `epic-superarchetype-layer-clustering` | Superarchetype taxonomy — cluster archetypes into strategy families, derived + curated | feature | — | `01d8576` |
| `epic-superarchetype-layer-three-level-page` | Three-level best-call page + superarchetype agency map | feature | — | `01d8576` |
| `feature-camp-incremental-assignment` | Incremental camp assignment for post-staging decks | feature | — | `01d8576` |
| `feature-era-alarm-hygiene` | Era-alarm hygiene — registered-ban awareness + same-date multi-ban attribution | feature | — | `01d8576` |
| `feature-multi-split-matrix` | Multi-split advisory matrix — one pass across all camp splits | feature | — | `01d8576` |
| `feature-refresh-keyed-reload` | Refresh: keyed reload that preserves labels for unchanged decks | feature | v0.3.0 | `ba9b3ad` |
| `feature-strategic-plan-best-call-viz` | Strategic-plan table in Best Deck / Best Call | feature | — | `01d8576` |
| `epic-card-semantics-ir-fix-graveyard-regex` | Fix _RE_GRAVEYARD to match the "their graveyard" oracle template (Exhume) | story | — | `01d8576` |
| `epic-card-semantics-ir-fix-greedy-manabase-axis` | Fix greedy-manabase axis category error (attack vs protection: FoV/Krosan Grip) | story | — | `01d8576` |
| `epic-card-semantics-ir-fix-ld-mislabel` | Fix _derive_attacks_for_promoted land-destruction mislabel (Wasteland/Ghost Quarter) | story | — | `01d8576` |
| `epic-card-semantics-ir-fix-pitch-blast-nits` | Fix _PITCH_SPELL_RE escaped-paren bug + blast-capability nit | story | — | `01d8576` |
| `epic-data-autonomy-catalog-lint` | Catalog lint: cross-check curated card data against the DB | story | — | `01d8576` |
| `epic-sb-advisor-correctness-acquire-color-filter` | Color-identity filter for advise acquire + sideboard candidate pool | story | — | `01d8576` |
| `epic-sb-advisor-correctness-fourof-guard` | Combined main+SB 4-of legality guard in recommend/considering paths | story | — | `01d8576` |
| `epic-sb-advisor-correctness-sweep-polish` | Sweep report polish: near-duplicate clusters + Σ-adoption formatting | story | — | `01d8576` |
| `epic-stable-era-windows-consumption-adapter` | Era-horizon adapter + field era resolver | story | — | `01d8576` |
| `epic-stable-era-windows-consumption-consensus` | Consensus family era windows + golden re-pins | story | — | `01d8576` |
| `epic-stable-era-windows-consumption-matrix` | Adaptive matrix horizon injection + window/audit swap | story | — | `01d8576` |
| `epic-stable-era-windows-detection-bocpd` | Beta-Binomial BOCPD recursion (analytics/eras/bocpd.py) | story | — | `01d8576` |
| `epic-stable-era-windows-detection-detectors` | Signal detectors S1-S4 (analytics/eras/detect.py) | story | — | `01d8576` |
| `epic-stable-era-windows-detection-ensemble` | Ensemble + FDR + floors + stable_since, ruptures dep, calibration fixtures (analytics/eras/ensemble.py) | story | — | `01d8576` |
| `epic-stable-era-windows-detection-series` | Entity series builder (analytics/eras/series.py) | story | — | `01d8576` |
| `epic-stable-era-windows-discovery-gate-core` | Gate C temporal-mixing in the discovery core | story | — | `01d8576` |
| `epic-stable-era-windows-discovery-gate-surface` | Era-default discovery window + report/staging surfacing | story | — | `01d8576` |
| `epic-stable-era-windows-era-ledger-cli` | eras CLI group (run|list|explain|confirm) | story | — | `01d8576` |
| `epic-stable-era-windows-era-ledger-run` | Attribution + eras run pass + drift alarm | story | — | `01d8576` |
| `epic-stable-era-windows-era-ledger-store` | BAN_EVENTS curated-JSON migration + entity_eras store | story | — | `01d8576` |
| `epic-stable-era-windows-mixed-horizon-consumers` | Align the two un-audited build_adaptive_matrix consumers with era windows | story | — | `01d8576` |
| `epic-stable-era-windows-shrinkage-goldens` | Golden re-pins + prior-source surfacing | story | — | `01d8576` |
| `epic-stable-era-windows-shrinkage-hierarchy` | Hierarchical + cross-era cell priors | story | — | `01d8576` |
| `epic-superarchetype-layer-era-core-pools` | Per-entity era core pools for superarchetype clustering | story | — | `01d8576` |
| `feature-multi-split-matrix-adaptive-window` | Adaptive multi-split builder + window entry point | story | — | `01d8576` |
| `feature-multi-split-matrix-best-call-onepass` | Best-call page one-pass migration + cross-camp P(best) | story | — | `01d8576` |
| `feature-multi-split-matrix-core-tally` | Multi-split core: maximal tally + pooling + uniform builder | story | — | `01d8576` |
| `feature-strategic-plan-best-call-viz-data-contract` | Strategic-plan registry, aggregation, and payload contract | story | — | `01d8576` |
| `feature-strategic-plan-best-call-viz-render-report` | Strategic-plan table, portrait, and generated report | story | — | `01d8576` |
| `fix-shrinkage-triple-display` | Shrinkage triple-display: raw WR always travels with the shrunk estimate | story | — | `01d8576` |
| `gate-docs-readme-suite-count-drift` | README asserted a stale suite size and mischaracterized the UMAP state | story | — | `01d8576` |
| `story-cleanup-nits-batch` | Cleanup-nits batch — four small low-risk polish items | story | — | `01d8576` |
| `story-deep-review-followups` | Deep-review follow-ups (2026-08-01, 7-feature post-merge review) | story | — | `01d8576` |
| `story-fix-blowouts-use-raw-win-rate` | Restore raw-win-rate blowout classification | story | — | `01d8576` |
| `story-positive-matchup-edge-highlights` | Add positive matchup edge highlights to Best Call ledgers | story | — | `01d8576` |

## Ship record

- **Date shipped**: 2026-08-05
- **Mapping**: tag-based — merged to `main` via PR #79 with CI green, tagged `v0.4.0`
- **Items shipped**: 53 (2 epics, 15 features, 35 stories incl. 1 gate-produced, 1 late-bound
  archived stub)
- **Gate findings**: 3 total — 1 fixed in-gate and bound (`gate-docs-readme-suite-count-drift`),
  2 Low routed to the unbound backlog (`gate-tests-stale-xfail-docstring`,
  `gate-patterns-multi-split-one-pass-sweep`). 0 blockers.
- **Retention**: `delete-refs` (CONVENTIONS has no terminal-tier retention key) — bound item
  bodies pruned from disk; the shipped-items table's git refs recover any of them.
- **CI note**: the first CI run on the release PR failed with 2 tests that had never been
  exercised remotely (the branch carried 27 unpushed commits). Both were real defects, not
  flakes: a CLI test reading the default database instead of a `--db` tmp file, and a golden
  asserting full-precision floats that differ by one ULP across interpreter versions. Fixed in
  `379ed34`; second run green.

