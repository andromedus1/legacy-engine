---
id: epic-bigmana-coverage-sideboard-fidelity
kind: epic
stage: done
tags: [advisory, archetype, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Big-Mana Coverage & Sideboard Fidelity

## Brief

The hate model and sideboard recommender have two blind spots that surfaced acutely during
Boulder-meta Dimir Tempo prep (2026-06-06), where the local field is big-mana-heavy (Lands, Tron,
Post, Eldrazi). First, colorless big-mana / ramp decks are **completely outside the model**: there's
no `ramp`/`big-mana` vulnerability tag, so Tron — the post-Undercity-Informer regime's #1 deck at
9.1% — is uncovered by both the matchup matrix and the hate-equity analysis, and its dedicated
answers (Harbinger of the Seas, Null Rod, Pithing Needle) map to nothing. Second, the
`HOSER_CATALOG` knows only ~25 cards and is blind to most real sideboard tech, so the ILP solver
recommends only the generic hosers it happens to know while ignoring the cards a user actually runs.
Third, the per-tag swing magnitudes that drive solver ordering are curated constants, not empirical.

This epic widens the hate model to cover the modern field and grounds the sideboard recommender in
real card data. `/epic-design` decomposes the findings below.

## Member findings (absorbed from backlog — full text in git history)

- **bigmana-ramp-archetype-tag** [advisory, archetype]: add a `ramp`/`big-mana` composition tag
  (Urzatron / Cloudpost / Eldrazi-temple signatures, colorless utility-land density, low colored-pip
  requirement) + corresponding hoser mappings, so Tron/Post/Eldrazi are covered by the hate model.
  Currently they fall through the cracks between greedy-manabase and uncovered.
- **hoser-catalog-expansion** [advisory, generation]: `HOSER_CATALOG` (~25 cards) is missing staples
  (Null Rod, Pithing Needle, Consign to Memory, Engineered Explosives, Sheoldred's Edict, Toxic
  Deluge, Dauthi Voidwalker, Harbinger of the Seas). Expand it — ideally data-driven from cards that
  appear in winning sideboards (`report cards --board side`) — and move it to an editable data file.
- **empirical-sideboard-swings** [advisory]: the recommender's per-tag swing magnitudes
  (_SWING_DEDICATED=0.20, _SWING_SOFT=0.10) are curated heuristic constants, not derived from
  before/after-sideboard win-rate data. Replace with empirical swings where the data supports it;
  keep the caveat where it doesn't.
- **considering-cards** [generation, advisory]: deck/sideboard generation should emit a larger
  (~30-card) "considering" pool rather than only the final 15, so the user can see the flex options
  and meta-call alternatives the engine weighed.
