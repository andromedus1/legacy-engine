---
id: epic-subarchetype-resolution-discovery
kind: feature
stage: drafting
tags: [analytics, archetype]
parent: epic-subarchetype-resolution
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Subarchetype discovery engine

## Brief

The research-gated core of the epic: a data-driven engine that discovers play-pattern subarchetypes
*within* a single parent archetype at corpus scale, validates them statistically, auto-names them from
signature cards, and stages the survivors as **candidate** variant splits for human promotion. It
delivers a `discover` CLI surface (report candidate splits for an archetype, with per-camp stats) and a
`promote` step that moves a confirmed split into the curated `data/variants/legacy.json`. It does NOT
change any existing analytics output — that is the two consumer features. It does NOT silently rewrite
the curated taxonomy — discovery only ever produces candidates in a staging registry.

Method is fully pinned by the attested brief `docs/briefs/subarchetype-discovery.md`: build the
per-parent feature matrix over the **flex band** (drop the ubiquitous core and rare tail by inclusion
thresholds), TF-IDF/count representation, reduce (TruncatedSVD/UMAP), cluster with **HDBSCAN**
(self-determines k, labels outlier brews as noise) on the reduced embedding, then gate each split
through BOTH a statistical gate (resampling stability >0.9 / prediction strength >0.8; internal indices
secondary) AND the domain gate the engine already trusts (both camps reach evolving tier n≥30; large
signature-card inclusion/copy divergence). Guard against the double-dipping trap (no naive significance
test on the clustered data). Auto-name from top signature cards.

## Epic context

- Parent epic: `epic-subarchetype-resolution`
- Position in epic: **foundation feature** — both consumer features (`-matchup-cells`, `-card-winrate`)
  depend on the `decks.variant` labels this engine produces (discovery-first, per the epic decision).

## Inherited design decisions

From the parent epic's `## Design decisions` (fixed inputs — do not re-ask):
- **Deps**: scikit-learn **+ umap-learn** (sklearn ships HDBSCAN ≥1.3, TruncatedSVD, TF-IDF, silhouette;
  umap-learn adds the UMAP reduction — accept the numba build weight). Add to `pyproject.toml`.
- **Human-confirm hook**: `discover` → **staging registry** → `promote`. Candidates land in a staging
  registry (status: candidate) that analytics can read as labeled-speculative; `promote` moves a
  confirmed split into curated `data/variants/legacy.json`. Never auto-rewrite the curated taxonomy.
- Honesty: candidate splits and their camps carry sample-tier labels; nothing thin is hidden.

## Research briefs

- `docs/briefs/subarchetype-discovery.md` (attested) — the method SSOT: §2 representation, §3 distance,
  §4 algorithm (HDBSCAN primary), §5 two-gate validation + double-dipping guard, §6 auto-naming, §8
  implementation notes (build on `subgroup.py`, `variants.py`, `decks.variant`; runs offline as a
  labeling pass sibling to `label`).

## Foundation references

- `docs/ARCHITECTURE.md` — `archetype/` subsystem (`variants.py` curated registry; the discovery
  engine is its data-driven front-end) and `analytics/subgroup.py` (`report subgroup` — the existing
  single-axis discovery front-end this generalizes; already computes signature-card divergence).
- `data/variants/legacy.json` — the curated registry (promotion target); `decks.variant` — persistence.

## Notes for /feature-design

- Split into child stories if it exceeds one implement pass: candidate seams are (a) feature-matrix +
  representation + reduction, (b) HDBSCAN + validation gates, (c) auto-naming + staging registry +
  `discover`/`promote` CLI. Keep the pure clustering/validation logic DB-free and unit-testable with
  hand-built inputs (objective-search-split pattern).
- Reuse `subgroup.py`'s divergence computation for Gate B. New CLI leaves follow the nested-group +
  fail-loud-stub pattern; audit-echo `// ...` provenance lines for the discovery report.
- Hermetic CLI tests pass `--db <tmp>`, never the default DB.
