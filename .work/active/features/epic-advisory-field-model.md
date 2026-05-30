---
id: epic-advisory-field-model
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Field Distribution Model (global + custom field)

## Brief
The shared SSOT for "what is the field" that the positioning score, sideboard recommender, and
what-to-play advisor all consume. Build a `FieldDistribution` (archetype→expected-share map) two ways:
**global** — derived from `metashare`'s `compute_metashare` over the labeled corpus (carrying the backing
per-archetype counts so positioning can form a Dirichlet posterior) — and **custom** — a user-supplied
`archetype→share` map (the "best metagame call for MY room" headline). Custom-field handling: auto-normalize
(warn if shares don't sum to 1), warn + impute on archetypes with no/low matchup data, keep **Other/rogue
as an explicit archetype** with imputed wide-uncertainty, include the **mirror at its field share**, and
stamp a `field_source: global | custom | local` label on every distribution.

Extracted as a foundation feature (not in the architecture's 4-file advisory table) because all three
advisory consumers need the same field semantics; owning it once is the SSOT that avoids three
re-implementations of custom-field normalization / Other-handling / Dirichlet-count carrying — the same
rationale that extracted `match-results` ahead of `metashare`/`matchup-matrix` in `epic-meta-analytics`.

Does NOT compute the positioning score, sideboard, or what-to-play signals (those consume this); does NOT
recompute meta-share (reads `compute_metashare`).

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: **foundation feature** — `positioning`, `whattoplay`, and `sideboard` depend on its
  `FieldDistribution` type. Consumes the done `epic-meta-analytics` (`compute_metashare`).

## Inherited design decisions
- **Custom field included in MVP** (archetype→share map; auto-normalize; warn on no-data archetypes) — the
  "best metagame call for MY room" headline, not just global-meta scoring.
- **Other/rogue is an explicit archetype** with imputed wide-uncertainty; **mirror included at field share**
  (p=0.5, zero variance) for headline scoring (per advisory-methods §2 conventions).
- **`field_source` label** (`global | custom | local`) on every distribution — never an unlabeled field.

## Research briefs
- `docs/briefs/advisory-methods.md` — §2 conventions (normalize w to 1; Other/rogue explicit; mirror at
  share; Dirichlet `counts+γ`); custom-field semantics (normalize/warn/impute, `field_source`).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/` module; `analytics/metashare.py` (`compute_metashare`/`MetaShareReport`).
- `docs/PRINCIPLES.md` — #6 never an unlabeled meta-% (field is labeled by source); #7 confidence-gate.

<!-- feature-design fills in: the FieldDistribution type, global/custom builders, normalize/impute logic, test approach. -->
