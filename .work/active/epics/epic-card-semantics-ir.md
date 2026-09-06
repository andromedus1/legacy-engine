---
id: epic-card-semantics-ir
kind: epic
stage: drafting
tags: [advisory, ingestion, needs-brief, deferred]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Card-semantics rules layer — validated semantic IR replacing regex+memory

> **DEFERRED 2026-08-11** — the full semantic/rules IR remains a large, correctness-sensitive
> undertaking. Continue shipping independently verified tactical fixes, but do not activate the
> strategic IR or use it as a prerequisite for current ranking/portability work without a new
> operator decision.

## Brief

Card semantics currently enter the engine through fragile layers — regex over oracle text,
model memory, and hand-curated JSON — and dogfooding has repeatedly caught the result:
misread rules, mislabeled interactions, category errors in tag derivation. Four verified
bugs from this class are promoted as immediate child stories (tactical track); the
strategic track replaces the fragile stack with a validated semantic intermediate
representation (IR) for card rules, per the original park (full text below). The epic is
tagged needs-brief: run /research-pipeline:brief on the IR design space before epic-design
decomposes the strategic track.

## Strategic decisions
- **Sequencing (2026-07-31, scope gate)**: Tactical fixes now, IR behind brief — the four
  verified bugs ship as stories immediately in the existing regex layer; the IR proceeds
  in parallel through brief → design. Bug fixes ship regardless of IR timeline.

## Child stories (tactical track, stage: implementing)
- epic-card-semantics-ir-fix-graveyard-regex — `_RE_GRAVEYARD` misses "their graveyard" (Exhume)
- epic-card-semantics-ir-fix-ld-mislabel — `_derive_attacks_for_promoted` labels Wasteland/Ghost Quarter creature-based
- epic-card-semantics-ir-fix-pitch-blast-nits — `_PITCH_SPELL_RE` escaped-paren bug + blast-capability nit
- epic-card-semantics-ir-fix-greedy-manabase-axis — FoV/Krosan Grip carry greedy-manabase as attack when it means protection

## Design decisions
<!-- captured 2026-07-31 via epic-design --only-questions; the /brief and feature-design treat these as fixed inputs -->
- **IR home**: a NEW `semantics/` module — a fresh bounded context for the validated
  semantic IR; `interaction_facts.py` becomes a consumer of its output (the maintainer's explicit
  call, chosen over extending InteractionFacts in place). The ~28 compiled regexes across
  whattoplay/sideboard/card_tags/interaction_facts migrate to consumers.
- **Validation ground truth**: internal hand-curated golden fixtures against verbatim
  oracle text are the validation authority (mechanical-grounding discipline); external tag
  sources (Scryfall Tagger, MTGJSON keywords) may seed candidates but never gate correctness.
- **Coverage scope (design-pass default, brief may revisit)**: advisory-consumed semantics
  first — the tag surface the advisory layer reads today — with a schema designed to extend
  to goldfish/trainer semantics later.

## Member findings (absorbed from backlog; full text below)

---

### idea-card-semantics-rules-layer


# Card-semantics rules layer — replace regex+memory with a validated semantic IR

the maintainer's observation (2026-07-03, model-switch review): the model has repeatedly misinterpreted
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
