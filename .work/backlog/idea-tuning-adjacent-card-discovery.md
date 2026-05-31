---
id: idea-tuning-adjacent-card-discovery
created: 2026-05-30
tags: [generation, discovery, needs-research]
---

Think outside the box on field-tuning: let the tuner consider cards **adjacent to, but not already seen in,
the deck** — not just the archetype's observed card pool. The `epic-deck-generation-tuning` feature
deliberately scoped its candidate pool to "cards this deck already plays" (bounded, faithful, low-risk). This
idea is the opposite end: surface genuinely novel swap candidates the field hasn't tried yet — cards that are
mechanically/role-adjacent (same role: counter / removal / threat / answer; same colors; similar mana/CMC;
synergy with the deck's existing engines) but under- or un-played in this shell. That turns "tuning" toward
"discovery" — the differentiator the brief frames as gap-discovery mode 3, but applied at the card level
inside an existing shell rather than at the archetype level.

Why parked, not built now: (1) it overlaps the **deferred gap-discovery (mode 3)** epic and its card-gap half
needs the **per-card win-rate match-results extension** that doesn't exist yet — without per-card signal,
recommending unproven adjacent cards is speculative; (2) it needs an "adjacency" model (role/color/CMC/synergy
similarity over the card pool, possibly embedding- or tag-based) that warrants its own research/brief; (3) it
changes tuning's risk profile from "proven, auditable" to "exploratory, needs confidence-gating + goldfish
validation." Revisit when designing the gap-discovery follow-up epic. Related:
`docs/briefs/deck-generation-and-moxfield.md` §2.2 (mode 3 card gaps), `epic-deck-generation-tuning`,
the deferred per-card win-rate extension, and `epic-goldfish-simulation` (validating exploratory candidates).
Promote via `/agile-workflow:scope` when ready.
