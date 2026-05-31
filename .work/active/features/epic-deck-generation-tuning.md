---
id: epic-deck-generation-tuning
kind: feature
stage: drafting
tags: [generation]
parent: epic-deck-generation
depends_on: [epic-deck-generation-consensus]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Field-tuning (optimize a shell against the field)

## Brief

The core generation feature (**mode 2**): given a shell (a consensus list or a user-supplied decklist),
optimize the 60+15 against the **current or projected** field. Swap maindeck flex slots toward cards/configs
with better field-weighted matchup equity (matchup matrix × field share), then run the existing sideboard
recommender for the 15. Validate legality at every step. Report the **before/after positioning `S`** so the
tuning is auditable (audit-trail principle). Now unblocked: the advisory-heuristic prerequisites
(`improve-whattoplay-proactivity-threat-signal`, `improve-positioning-pbest-uneven-sample`,
`improve-sideboard-realdata-quality`) all landed in `epic-advisory-hardening`.

Generates against the windowed latest ban-regime by default. **Bimodal-coverage fallback**: where matchup-n
< 30 the tuner falls back to consensus + legality and says so — never fabricates a tuned edge from imputed
cells.

Does NOT cover gap-discovery (mode 3, deferred from this epic) or goldfish-validation of the tuned candidate
(separate pillar).

## Epic context
- Parent epic: `epic-deck-generation`
- Position in epic: consumer of `epic-deck-generation-consensus` — depends on the `generation/` module +
  `generate` CLI group it establishes, and tunes a consensus (or user) shell.

## Inherited design decisions
From the parent epic `## Design decisions` (fixed inputs):
- **Field default**: windowed latest ban-regime (reuse `trends` regime windowing); user-overridable.
- **Bimodal fallback**: matchup-n < 30 → fall back to consensus + legality, and surface that it did.
- **Legality**: `validate_deck` against the as-of-date ban snapshot at every tuning step.
- Composes `advisory/` (positioning S, field model, sideboard recommender) + `analytics/matchup` — reinvent
  nothing.

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` §2.2 (mode 2), §2.3 (prerequisites — now satisfied), §2.4.
- `docs/briefs/advisory-methods.md` — positioning / matchup / sideboard methods orchestrated here.

## Foundation references
- `docs/ARCHITECTURE.md` — `generation/` seam.
- `src/legacy_engine/advisory/positioning.py`, `advisory/field.py`, `advisory/sideboard.py`,
  `analytics/matchup.py`, `ingestion/banlist.py`.
