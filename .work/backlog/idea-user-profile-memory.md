---
id: idea-user-profile-memory
created: 2026-06-22
tags: [memory, personalization, advisory]
---

For legacy-engine to work for **other people** (not just Andrew), it needs a
per-user **memory of who's using it** — the typical LLM-memory-style thing:
what decks they have/play, their location/local meta, their play style and
preferences, their collection/binder, etc. Advice should be grounded in the
specific person's situation, persisted across sessions, the way an LLM assistant
remembers a user.

**Relationship to other parked work:** likely adjacent to / pairs with
[[idea-live-meta-knowledge-system]] — that one is a persisted, agent-accessible
memory of the *meta* (global state the engine produces); this one is a persisted
memory of the *user* (personal state). Together they're the two halves of
"ground every recommendation in current knowledge": global meta + individual
context.

**Raw notes (not a design):**
- Kinds of user state worth remembering: owned/registered decks (versioned 75s),
  collection/binder, home location + local/venue meta, play style and archetype
  preferences, prior advice given and decisions made.
- Some of this already has primitives in the engine (`deck` command for named
  versioned 75s, `collection`/binder, `--venues`, player identity/strength) —
  the idea is a coherent *per-user memory layer* over those, not necessarily
  net-new data plumbing.
- Open question for scope/design: where user memory lives and how it's scoped
  per-user (single-user local files today vs multi-user), and how the agent
  loads it at session start (parallel to how the doc knowledge-index auto-loads).
