---
id: idea-card-semantics-rules-layer
created: 2026-07-03
tags: [advisory, ingestion, needs-research]
---

# Card-semantics rules layer — replace regex+memory with a validated semantic IR

Andrew's observation (2026-07-03, model-switch review): the model has repeatedly misinterpreted
card rules and card impact — "something about the overall understanding in the rules engine is
off." Root cause analysis: card semantics currently enter the engine through THREE fragile layers:

1. **Hand-curated JSON** (hosers/linchpins) — typo-prone at authoring, silently drifts
   (Hydroblast/Pyroblast mis-tags, Null Rod colors ["G"]).
2. **Regex-over-oracle-text heuristics** (`_card_roles`, `_derive_attacks_for_promoted`) — surface
   pattern-matching with no notion of sentence structure: cost-vs-effect ("as an additional cost…
   exile" ≠ graveyard hate — the FoN derive quirk), object type ("destroy target **land**" ≠
   creature removal — the Wasteland mislabel), owner scope (each/all vs opponent — symmetry).
3. **Model judgment at design/curation time** — reasons from memory unless disciplined to query
   oracle text (the standing ground-in-oracle-text rule exists because of prior incidents).

## Layered fix (candidate arcs — scope/design later)

- **L0 (quick win, separate item):** [[idea-catalog-lint-vs-db]] — CI cross-check of curated JSON
  vs DB facts.
- **L1 (the core): semantic IR extracted at ingest.** One-time, batched LLM extraction per
  Legacy-relevant card, run against the ACTUAL oracle text into a validated JSON schema — clause-level:
  cost vs effect segmentation, subject/object types, owner scope (self/opponent/each), timing
  (instant-speed/flash/trigger/static/activated), zones touched, targets, castability conditions.
  Stored as data (JSON per card, like the linchpin registry), golden-tested against a hand-verified
  set, versioned with the card refresh. The regex heuristics demote to fallback; the hoser catalog
  becomes hybrid derived+curated (same pattern as linchpins). Also: ingest Scryfall's `keywords`
  field (Delve/Flash/Ward/etc.) which the current Card model drops — free structured semantics we
  already download. Key property: interpretation happens ONCE, against source text, with schema
  validation + spot-check — not per-session from model memory.
- **L2: rules-research corpus.** /research (or /deep-research) on MTG oracle-text templating + CR
  semantics: cost-vs-effect wording conventions, owner-scope templates ("each player" vs "target
  opponent"), replacement effects, layers, timing words. Produces briefs that ground BOTH the L1
  extractor schema and future design-time reasoning. (This item carries [needs-research] for this.)
- **L3: external cross-validation oracle (divergence-as-diagnostic, again).** Audit our derived
  semantics against community sources — Scryfall Tagger functional tags; possibly Forge/XMage card
  scripts (mature machine-readable per-card semantics; LICENSE CHECK needed, GPL) — via a divergence
  report. Never auto-import; divergences flagged for human review. Same philosophy as the backtest:
  consensus is a diagnostic, not a prior.

## Connects to

The deferred `epic-goldfish-simulation` (mana solver / mulligan sim) will need exactly this IR —
L1 is a prerequisite investment that pays twice. Fresh evidence for the problem class: the Defense
Grid false positive (symmetric self-tax on our own instant-speed deck, recommended at 0% winner
adoption), the FoN derive quirk, [[idea-derive-attacks-land-destruction-mislabel]],
[[idea-consign-to-memory-tag-differentiation]].
