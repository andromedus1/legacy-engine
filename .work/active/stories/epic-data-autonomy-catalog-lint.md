---
id: epic-data-autonomy-catalog-lint
kind: story
stage: implementing
tags: [advisory, infra]
parent: epic-data-autonomy
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-31
---

# Catalog lint: cross-check curated card data against the DB


# Catalog lint: cross-check curated card data against the DB

Quick-win guard for the hand-curated JSON layer (hosers, linchpins). A CI-gated lint that
cross-checks every curated entry against `cards` in DuckDB: name exists (exact spelling), declared
`colors` match the card's actual colors (would have caught Null Rod `["G"]` — it's colorless),
`castable_any_color` vs Phyrexian/alt-cost text, `symmetry` vs owner-restriction wording
("each/all/a player" without "opponent" → warn if asymmetric), functional_group members actually
share an effect. Warn-level heuristics, error-level for hard facts (existence, colors).

Motivation: 2026-07-03 sessions found Hydroblast + Pyroblast mis-tagged, Null Rod mis-colored —
all silent, all in shipped curated JSON. Cheap to build; catches the whole data-typo class at
commit time instead of at dogfooding time.
