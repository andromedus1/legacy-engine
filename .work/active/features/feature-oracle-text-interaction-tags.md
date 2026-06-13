---
id: feature-oracle-text-interaction-tags
kind: feature
stage: drafting
tags: [advisory, data-quality, methodology]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

**Hurdle observed:** card-interaction reasoning done from memory is error-prone, and it produced
several wrong claims in one dogfood session (2026-06-13). All were about graveyard-hate symmetry /
targeting:
- Claimed **Grafdigger's Cage** hurts our own Nethergoyf/Murktide/Barrowgoyf — it doesn't (it only
  stops creatures/PWs *entering* or being *cast* from graveyard/library; it has no effect on
  graveyard *count*, so delirium/delve/escape are unaffected).
- Claimed **Leyline of the Void** and **Nihil Spellbomb** "brick your own yard" — both are
  one-sided/targeted: Leyline = "opponent's graveyard… exile it instead"; Nihil = "exile **target
  player's** graveyard" (you point it at the opponent). Neither touches our own yard.

**Why this matters:** the advisory output — especially the planned plain-speak sideboard primer
([[idea-deck-tuning-refresh-workflow]]) that explains *how each card attacks each opponent* — is
worthless if it gets interactions wrong. "Analyze correctly" applies to card rules, not just data
windows (cf. [[idea-ban-regime-everywhere]]).

**The fix is cheap because the data already exists:** `cards.oracle_text` is already ingested from
Scryfall (verified: Nihil/Leyline/Grafdigger's oracle text is in the DuckDB `cards` table). We are
simply not grounding interaction reasoning in it. Options to explore at scope time:
- Surface relevant `oracle_text` alongside any card the advisory/primer reasons about, so claims can
  be checked against it.
- Derive a small set of **structured interaction tags** from oracle_text (e.g. `affects:
  opponent-only | symmetric | targeted`, `self-graveyard-safe: yes/no`, `free-to-cast-condition`,
  `static-vs-activated`) so sideboard/primer logic reasons over facts, not vibes.
- At minimum, a lint/guard: when the advisory text makes an interaction claim about a card, require
  it to be consistent with that card's oracle_text.

Concrete payoff seen this session: once corrected, Leyline of the Void (already owned, x4) is
synergy-safe premium turn-0 hate vs the online field's Grixis Reanimator / Doomsday recursion — a
recommendation the memory-based reasoning had wrongly suppressed.
