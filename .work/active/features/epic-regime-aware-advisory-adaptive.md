---
id: epic-regime-aware-advisory-adaptive
kind: feature
stage: drafting
tags: [advisory, analytics, correctness]
parent: epic-regime-aware-advisory
depends_on: [epic-regime-aware-advisory-windowing-core, epic-regime-aware-advisory-cli-surface]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Adaptive Per-Cell Windowing (v2)

## Brief

The smart layer: instead of one uniform window for everyone, give each archetype its own valid
history horizon based on whether recent bans actually touched it, then pool each pairwise matchup
cell over the maximally-valid window.

- **Affectedness → `valid_since` per archetype.** For each ban regime boundary, an archetype is
  "affected" if it ran a banned card above an inclusion threshold in the pre-ban regime
  (data-derived from `generation/consensus.card_frequencies` × the banlist `current_banlist()` ×
  `regime_windows`). `valid_since(archetype)` = the date of the **most recent** ban that affected it
  (or the corpus start if none). Validated: affectedness is starkly bimodal (Entomb = 100% of Dimir
  Reanimator / ~0% else; Undercity Informer = 99.9% of Oops! / 0% else), so a simple threshold
  classifies cleanly. Be **conservative** where an archetype's lists churn even without a direct hit
  (the classifier catches direct hits, not indirect rebuilds).
- **Per-cell windowing.** A pairwise cell `A vs B` pools data back to
  `max(valid_since(A), valid_since(B))`. Unaffected×unaffected cells keep full history (established
  tier); ban-affected cells truncate honestly. **Positioning always weights by the *current* field
  shares** — so dead decks (current share ≈ 0) fall out regardless of how strong their old cells were.
- **Flip the default to adaptive** (the inherited decision): the matrix-build default and the CLI
  default become the adaptive per-cell window; `--all-time` (from `cli-surface`) remains the explicit
  full-corpus escape; `--regime`/`--since` still force a uniform window.
- **Surface the window each cell used** (auditability) — the per-cell `valid_since`/window must be
  inspectable in output, not hidden.

Does NOT cover goldfish validation; does not attempt to fix field-level power shifts beyond using
current field shares (that is the intended honest estimate).

## Epic context
- Parent epic: `epic-regime-aware-advisory`
- Position in epic: v2 — the target design; depends on `windowing-core` (the plumbing) and
  `cli-surface` (the window/default UX it re-defaults).

## Inherited design decisions
- **v2 flips the default to the adaptive per-cell window** (max valid data per matchup, current-field
  weighting); `--all-time` stays the explicit full-corpus escape.
- **Affectedness is data-derived** (banned-card inclusion), conservative when lists churn; **always
  surface the per-cell window** (audit-everything).
- **Thin-regime = degrade + loud caveat** still applies (fall back to the adaptive window / wider data
  with a banner when a forced narrow window is too thin).

## Known limits to design around (from the epic analysis)
- Card-inclusion catches **direct** ban hits, not **indirect** field-driven rebuilds — treat-as-affected
  / shorten the window when an archetype churns; surface the window so it's auditable.
- Archetype-label drift — pooling assumes "same deck" across the window; strongest for stable decks.
- **Performance**: per-cell windows mean the matrix can't be one single windowed scan. Feature-design
  must choose an efficient shape (e.g. group cells by distinct `valid_since` boundary and scan per
  group, or compute over the union then filter per-cell) — flagged as the riskiest unit.

## Research briefs
- The epic body (`## Strategic decisions`, `## Known limits`); `docs/briefs/card-adjacency-and-discovery.md`
  (`card_frequencies` inclusion as the affectedness signal; the two-level-empirical-Bayes shrink primitive).

## Foundation references
- `src/legacy_engine/ingestion/banlist.py` — `current_banlist` (banned cards × `as_of`).
- `src/legacy_engine/analytics/trends.py` — `regime_windows` (ban-date boundaries).
- `src/legacy_engine/generation/consensus.py` — `card_frequencies` (per-archetype-per-regime inclusion =
  the affectedness input).
- `windowing-core` (windowed `compute_match_results`/`build_matrix`), `advisory/positioning.py`,
  `advisory/gaps.py`, `cli-surface` (the default/flag UX to re-default).
