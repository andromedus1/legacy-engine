---
id: feature-strong-player-signal
kind: feature
stage: drafting
tags: [analytics, generation]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

Use **strong players as the best/strongest signal for archetype tuning.** A consensus over the whole
field averages in weak and netdecked lists; the sharpest read on how to build/tune a specific
archetype right now comes from the small set of players who pilot it at a high level. We want a way
to weight (or filter) tuning + consensus toward those players' lists.

To do that the engine needs to **identify, validate, and track players across the corpus:**
- **Identify** — resolve player identity across sources and handle variants (this session found the
  same person as `Bosh N Roll`, `BoshNRoll_Brian`, `Bosh95`; `Andrea Mengucci` as itself). Player
  strings are currently free-text on `decks.player` with no canonical identity.
- **Validate** — define "strong" defensibly: sustained results (top finishes / win-rates across
  events), not a single 5-0. Needs a per-player track record built from standings + results.
- **Track** — follow a player's archetype choices and list evolution over time and across regimes,
  so their tuning signal can feed `generate consensus` / `generate tune` (e.g. a `--players` or
  expertise-weighted field).

Open question to resolve at scope time: weight by player strength vs. hard-filter to a curated
expert set, and how this interacts with ban-regime windowing (a strong player's list from the prior
regime is still stale — see [[idea-ban-regime-everywhere]]).
