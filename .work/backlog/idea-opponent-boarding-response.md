---
id: idea-opponent-boarding-response
created: 2026-07-05
tags: []
---

Model opponent sideboarding response in matchup/card-value signals.

Current state: all winrates are match-level Bo3 (post-board games included), so the
*average* opponent boarding is priced in — but there is no pre/post-board split and no
adversarial response modeling. When the sideboard advisor tunes our 15 toward the field,
opponents' counter-adaptation to our new configuration isn't modeled; the signal is
corpus-equilibrium, presence-correlational, and explicitly labeled "NOT before/after-board"
in `advisory/sideboard.py` + `analytics/card_value.py`.

Candidate direction (from the capture conversation): condition card values on the opponent
archetype's typical side-in package against our macro-archetype (derive per-archetype
boarding tendencies from registered 75s' side compositions vs field), and surface the delta
as a diagnostic (divergence-as-diagnostic pattern), not a blended number.

Surfaced while answering "does the winrate account for opponent sideboarding?" during
best-call/best-deck analysis.
