---
id: idea-live-meta-knowledge-system
created: 2026-06-22
tags: [meta, knowledge, advisory]
---

For legacy-engine to give good advice, it needs to **ground itself in current meta
knowledge that persists and is accessible across sessions.** The engine can generate
meta analysis (meta-share, trends, tier lists, matchup data) during a session, but
that knowledge isn't maintained or made available to future sessions — so each
session re-derives it from scratch with ad-hoc queries. We want a maintained,
agent-accessible meta-knowledge layer that's kept current whenever the engine is in
use, so an agent picking up a later session starts from current meta state instead
of regenerating it.

**Motivating example (Dimir Tempo session, 2026-06-22):**
I recommended graveyard hate (Nihil Spellbomb) for the sideboard. the maintainer suspected
graveyard-heavy decks had fallen off — and the current-regime data confirmed it:
Dimir Reanimator was down to **4 decks** in the current regime after the Entomb +
Undercity Informer bans gutted the deck. Without a persisted meta-knowledge layer I
had to regenerate that meta-share/trend analysis live to discover this. With one, the
agent could have grounded the recommendation in current meta state immediately (and
might have de-prioritized graveyard hate from the start).

**The shape of the idea (raw notes, not a design):**
- Parallels the project's own `knowledge-index` pattern for docs — but for the *live
  meta state the engine produces* (meta-share, trends across ban regimes, tier lists,
  matchup matrices), not for documentation.
- Should stay current "when the engine is in use" — i.e. regenerated/refreshed as part
  of the normal data-refresh + analysis loop, not a one-off snapshot that goes stale.
- Should be agent-accessible at session start (the way `docs/knowledge-index.yaml`
  auto-loads), so advice is grounded without re-deriving.
- Open question for scope/design: what's the right artifact + freshness mechanism
  (auto-load file like the doc index? a `meta status` command? regime-stamped
  snapshot under `.work/` or `data/`?), and how it ties to the ban-regime windowing
  the engine already has.
