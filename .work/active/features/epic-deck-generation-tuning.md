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

## Design decisions
Captured via `/feature-design --only-questions` (interactive, 2026-05-30). Fixed inputs for the full design
pass — do not re-decide.

- **Swap signal → reuse the sideboard recommender's coverage model.** Don't invent per-card matchup scoring
  (we have no per-card win-rate data — that's the deferred extension). Extend `advisory/sideboard.py`'s
  weighted saturating-coverage model — `g(n) = 1 − (1−p)^n` over field threat-elements weighted by share,
  with the matchup matrix informing which matchups are weak — to the **flexible maindeck slots**, the same
  card-aware primitive that already builds the 15.
- **Flex vs locked slots → by inclusion-% in the archetype consensus.** Cards run by ≥ a threshold of the
  archetype's decks (in the target window) are locked core; the rest are the flexible slots the tuner may
  swap. Data-driven, no manual annotation. (Locking the proactive core also guards against the
  coverage objective stripping the gameplan in favor of reactive answers.)
- **Search → greedy, one swap at a time, sequential main → sideboard.** Make the single best flex swap,
  recompute, stop when no swap improves field-weighted equity (or when positioning `S` / gameplan starts
  degrading). Tune the maindeck flex first, then **re-run the sideboard recommender** so the 15 accounts for
  the tuned maindeck. Emit a swap log + before/after positioning `S` (audit-trail principle). Rationale: the
  coverage objective is submodular, so greedy is near-optimal here; ILP's exact optimum buys little raw
  quality while costing the audit narrative, per-step legality re-checks, and gameplan protection. The
  **joint main+sideboard ILP co-optimization** is a deferrable later enhancement (avoids over-covering a
  threat in both boards) — file it if greedy proves limiting.
- **Candidate pool → cards the archetype already plays** (its observed card pool in-window). Bounded,
  faithful to "what wins now." **Parked future expansion:** [[idea-tuning-adjacent-card-discovery]] —
  consider role/color/synergy-adjacent cards the deck has NOT run (discovery-flavored tuning); deferred
  because it needs the per-card win-rate extension + an adjacency model + confidence-gating, overlapping the
  deferred gap-discovery (mode 3) epic.
