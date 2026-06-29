---
id: idea-deck-findings-log
created: 2026-06-29
tags: [advisory]
---

A formal, engine-aware **per-deck critical-findings log** for decks we're intensely working
on (e.g. Dimir Tempo). When we sit down to work with such a deck, the engine should surface
the accumulated findings so we never start without the hard-won knowledge.

**Problem it solves:** session analysis produces durable, decision-relevant findings (e.g.
"transform into Doomsday beats a silver-bullet SB on net field EV; D&T 34.6%→71.8% and Energy
37.9%→59.6% are the reliable inversions; the Null Rod 'negative' vs artifacts was noise,
p=0.33"). Today these live only in conversation, ad-hoc memory, or buried in substrate item
bodies. There's no structured, deck-scoped store the engine reads when you start working a
deck — so knowledge has to be re-derived or re-remembered.

**Shape (rough, for scoping later):** a per-deck findings file (likely under the deck's
collection/`UserDeck` record or a sibling store) holding dated, sourced findings — claim,
evidence (n / CI / significance), confidence, and provenance (which analysis produced it).
The engine surfaces relevant entries when you run advisory/analysis for that deck (e.g. a
header block in `advise positioning`/`whattoplay`/`report`, or a `deck findings` view), the
way the knowledge-index nav auto-loads at session start. Honesty gates apply: a logged finding
carries its sample/CI so a thin finding reads as thin.

**Relationships:** distinct from `~/.claude` memory (which is assistant-scoped, not engine
data) and from the knowledge-index (project docs, not deck-empirical findings). Overlaps
conceptually with the parked `idea-subarchetype-discovery` (both are about richer deck
knowledge the engine should hold). Needs scoping — likely research + design (where does it
live, how does it bind to a deck/archetype, how does it surface, how does staleness/regime
windowing apply to a logged finding).
