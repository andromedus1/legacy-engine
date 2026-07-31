---
id: epic-persistent-coach
kind: epic
stage: drafting
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Persistent coach — knowledge that survives the session, advice grounded in the user

## Brief

The engine produces excellent per-session analysis and then forgets it. This epic turns
legacy-engine from a per-session analysis tool into a persistent coach: (1) a live
meta-knowledge store that persists tier reads, matchup insight, and field trends across
sessions; (2) a per-deck critical-findings log surfaced automatically when working a deck;
(3) a curated, ban-regime-aware consensus-deck corpus with a primer per archetype —
leveraged as an input by other analyses; (4) a user profile (decks owned/played, collection,
local meta, preferences) that grounds advice; and (5) an archetype-ID trainer ("name that
deck") built on the persisted archetype knowledge.

The consensus corpus depends on `generate consensus` being ban-aware and shell-coherent —
that fix (absorbed below) is foundational and should be sequenced first by epic-design.

Related in-flight work: epic-local-meta-support owns the local-field prep workflow (the
meta-report feature was scoped under it, not here); feature-web-interface may eventually
surface this layer but is not a dependency.

## Strategic decisions
- **Audience framing (2026-07-31, scope gate)**: Andrew-first, multi-user-ready — build for
  Andrew's workflow now; schema/storage designed so per-user profiles are a config swap,
  not a rewrite. VISION.md rolled forward with the persistent-coach cross-cutting layer.

## Member findings (absorbed from backlog; full text below)

---

### idea-live-meta-knowledge-system


For legacy-engine to give good advice, it needs to **ground itself in current meta
knowledge that persists and is accessible across sessions.** The engine can generate
meta analysis (meta-share, trends, tier lists, matchup data) during a session, but
that knowledge isn't maintained or made available to future sessions — so each
session re-derives it from scratch with ad-hoc queries. We want a maintained,
agent-accessible meta-knowledge layer that's kept current whenever the engine is in
use, so an agent picking up a later session starts from current meta state instead
of regenerating it.

**Motivating example (Dimir Tempo session, 2026-06-22):**
I recommended graveyard hate (Nihil Spellbomb) for the sideboard. Andrew suspected
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

---

### idea-deck-findings-log


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

---

### idea-curated-consensus-deck-corpus


**Build out the full set of global consensus (ban-regime-aware) decklists, ordered by
meta share, with a primer for each — then leverage that curated corpus across the
engine's analyses.**

The vision: a maintained library of "the deck" for every meaningful archetype in the
current ban regime, so analyses can run against *actual curated decklists* instead of
only the archetype-level matchup matrix. Gives deep, format-wide understanding and a
much richer substrate for advisory output.

Arcs (raw notes — not a binding decomposition):

- **Generate + curate the lists.** Walk archetypes in descending meta share; for each,
  emit the current-regime consensus list via the existing `generate consensus` (already
  ban-regime-aware) and curate/sanity-check it. Tier by sample (some archetypes will be
  speculative — flag, don't fake). Keep them regime-aware and refresh when the regime
  rolls.
- **Write a primer per deck.** Same shape as the Dimir Tempo / Doomsday Tempo primers
  (`decks/*-moxfield-primer.md`): gameplan, card choices, matchup + sideboard guide,
  mulligan/play tips, honesty gates. This is the curated-knowledge layer.
- **Leverage the corpus in analyses.** Today the matchup matrix is archetype-level and
  positioning runs on archetype rows. With curated lists we could: doctor any user deck
  against the real consensus list (not just copy-count modes), run list-level positioning,
  reason about specific card interactions across the field, and ground advisory text in
  actual cards. Possibly feed the corpus back as a knowledge index the engine/agents read.
- **Ban / unban speculation.** With curated lists + the field model, speculate on what
  banning or unbanning a given card would do — which decks weaken/disappear, which rise,
  how the field re-shapes. Connects to the existing `report speculate` (pre-data forecast)
  and `report affectedness` (which bans drove an archetype's valid_since); this would
  extend that to forward-looking "what if X were banned/unbanned" across the whole field.

Why it matters: turns the engine from archetype-share + matchup-matrix reasoning into a
deck-aware system with curated ground truth — the foundation for everything from deck
doctoring to meta forecasting. Pairs with the honesty discipline in the methodology memory
(every consensus list carries its sample tier + regime currency).

Related: the curated-knowledge / live-meta ideas already parked (idea-live-meta-knowledge-system,
idea-user-profile-memory), and the consensus generator + affectedness/speculate tooling
that already exist.

---

### idea-consensus-ban-aware-shell-coherent


**`generate consensus` should be ban-aware and shell-coherent.** Two findings from the Mystic
Forge session (2026-07-13):

- `generate consensus --archetype "Mystic Forge Combo" --since 2026-04-20` emitted a 75
  containing banned Candelabra of Tawnos with only a footer `[LEGALITY]` warning. The pool
  should be legality-filtered (or default-clamp to the current ban regime, with the explicit
  window override loudly caveated).
- The post-ban n=5 pool spans three distinct shells (Chalice/City-of-Traitors vs
  Trinisphere/partial-Tron vs white splash) and the modal reconciliation produced a
  Franken-list (4 Chalice AND 4 Trinisphere AND 1 lone Urza's Tower — no real list looks
  like that). Consensus should cluster the pool for shell coherence first and refuse/branch
  when the pool is multimodal. Workaround used: shipped a single winner's exact 75 instead
  (`decks/mystic-forge-combo.txt`).

---

### idea-user-profile-memory


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

---

### idea-archetype-id-trainer


A live archetype-ID trainer / "name that deck" coach. The player feeds in the cards
an opponent has played so far during a game; the system predicts the opponent's deck
archetype from that partial card sequence, driven by the engine's existing archetype
knowledge.

Intended use: by the player (Andrew) while playing, to train himself to correctly ID
opponent decks faster and earlier in a game.

Raw notes on possible shape (not binding):
- Progressive prediction — refine the archetype guess as more cards are revealed.
- Training/coaching angle: compare the player's own guess against the model's, surface
  which revealed cards were the strongest signal, reward earlier correct IDs.
