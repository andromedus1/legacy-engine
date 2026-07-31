---
description: "What should the validated card-semantics IR look like — schema, extraction tiers, validation architecture — so the ~28 advisory regexes become consumers of typed facts instead of pattern-matching oracle text? Read before epic-design decomposes epic-card-semantics-ir's strategic track."
type: brief
kind: research
slug: card-semantics-ir
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-31
blocks_phase: epic-card-semantics-ir
summary: |
  Curates the design space for a validated card-semantics intermediate representation (IR)
  replacing regex+memory in the new semantics/ module. Grounds the schema in the actual
  28-regex inventory and the four tag vocabularies the advisory layer consumes, in the
  Comprehensive Rules' own template vocabulary (cost templates, keyword enumerations), and in
  prior art (Forge/XMage capability DSLs, Scryfall keywords/Tagger, grammar-parser attempts).
  Recommends clause-scoped typed facts over a closed capability vocabulary, extracted in
  tiers (deterministic templates → batched LLM → curated overrides), validated by golden
  fixtures per semantic cluster plus a full-corpus classification census.
key_findings:
  - "Every production machine-readable MTG semantics system converged on the same shape: a closed vocabulary of parameterized capability predicates maintained as reviewable per-card data (Forge's `A:SP$ Counter | ValidTgts$ Card.nonCreature` script DSL, XMage's typed ability/cost/filter component library) — none parse free text at runtime, and full-grammar attempts stall (a published ANTLR4 grammar covers exactly one 273-card set with documented ambiguity failures; demystify remains a perpetual project)."
  - "Scryfall's `keywords` array is free structured semantics for keyword mechanics only — Murktide Regent returns ['Flying','Delve'] but Force of Negation (pitch) and Leyline of the Void (opening-hand) return [] — precisely the templates the advisory bugs live in; ingest the field (the Card model currently drops it) but it cannot replace text-derived facts."
  - "The 28-regex layer fails on four MISSING DIMENSIONS, not 28 bad patterns: owner-scope (Exhume's 'their graveyard'), object-type ('destroy target land' → creature-based), clause-role (FoN's cost-clause 'exile' + replacement-clause 'graveyard' → graveyard-hate false positive), and polarity (FoV carrying attacks={greedy-manabase} when it PROTECTS greedy manabases; the catalog's '_hate' pseudo-tag is the same missing axis) — every verified bug maps to one, so the IR schema must carry all four as first-class typed fields."
  - "The highest-value templates are CR-canonical, not folklore: CR 118.9 names the exact alternative-cost phrasings ('You may [action] rather than pay [this object's] mana cost' / 'without paying its mana cost'), and the cost/effect split is a rules concept (118.8/118.9 + casting rule 601.2b), so tier-1 deterministic extractors can be specified against the rulebook; CR 701/702 enumerate 69 keyword actions and 194 keyword abilities as a closed vocabulary (MTGJSON ships it as data: 78/220 incl. variants)."
  - "Oracle text is a retroactively re-templated corpus — Wizards rewrote 'his or her' to 'their' across Oracle in 2018 — so extraction must be versioned against a dated card snapshot, golden fixtures must pin verbatim oracle text (a re-template then breaks loudly), and possessive-scope vocabularies must include 'their'."
  - "Recommended IR: clause-scoped typed facts over a CLOSED capability enum (~20 capabilities cover the advisory-consumed scope) with typed params (object_type, owner_scope, polarity, clause_role, timing, condition, magnitude) + verbatim evidence quote + provenance + confidence per fact; all four consumer vocabularies (hoser attacks, whattoplay vulnerability/roles, linchpin neutralized_by, InteractionFacts) become pure derivations over facts."
  - "Validation: hand-curated golden fixtures per semantic cluster are the ONLY correctness gate; a full-corpus classification census over all 39,452 cards (35,698 with oracle text) pins per-capability membership counts as the drift regression; Scryfall Tagger via `otag:` search queries is a divergence DIAGNOSTIC (community data, never gating); Forge's card-script corpus is GPL-3.0 — read-only prior art, no bulk import."
---

# Brief: Card-Semantics IR

## Purpose

Unblocks the strategic track of `epic-card-semantics-ir`. The epic's fixed inputs (not
revisited here): the IR lives in a **new `semantics/` bounded context** with
`interaction_facts.py` demoted to a consumer; **internal hand-curated golden fixtures against
verbatim oracle text are the validation authority** (external tag sources seed candidates,
never gate correctness); **advisory-consumed semantics first**, schema extensible to
goldfish/trainer semantics later. This brief supplies what the builder needs: the exact
regex/tag surface being replaced, the template linguistics that make extraction tractable,
the IR-shape decision with prior-art grounding, and the validation architecture.

---

## 1. The problem in code terms — what the IR replaces

### 1.1 The 28-regex inventory

28 compiled module-level regexes (plus a handful of inline `re.search` calls) currently carry
card semantics into the advisory layer. Measured by `rg -n "re.compile" src/legacy_engine/`:

| File | n | What they claim to detect |
|---|---|---|
| `advisory/whattoplay.py` | 13 | counter, removal, ritual, tutor, storm, graveyard-recursion, delve/delirium/threshold (graveyard-fuel), protection, stax, card-advantage, instant/sorcery type |
| `interaction_facts.py` | 9 | graveyard scope (opp-only/targeted/self-only/symmetric), count-reduction (×2), activation, trigger, static restriction |
| `advisory/sideboard.py` | 5 | pitch spells, red/blue blasts, noncreature counter, colorless counter |
| `card_tags.py` | 1 | free/alternative-cost spells (6-alternation pattern) |

Excluded from scope (not card semantics): `models/decklist.py` count parsing,
`archetype/rules.py` JSON comma cleanup, `advisory/linchpins.py` reminder-text stripping,
`analytics/speculation.py` keyword hype scan.

### 1.2 The tag vocabularies the advisory layer consumes

These are the IR's **output contracts** — the advisory layer keeps consuming these shapes,
only their derivation changes:

- **Vulnerability tags** (`whattoplay.py` `VulnerabilityTag`, 16 values): `graveyard-recursion`,
  `graveyard-fuel`, `plays-{white,blue,black,red,green}`, `combo`, `low-curve`,
  `greedy-manabase`, `creature-based`, `low-interaction`, `storm-reliant`, `ramp`,
  `noncreature-reliant`, `colorless-reliant`. Derived per archetype from composition
  aggregates over per-card roles.
- **Card roles** (`whattoplay._card_roles`, 13 values): `fast_mana`, `counter`, `removal`,
  `ritual`, `tutor`, `storm`, `graveyard_recursion`, `graveyard_fuel`, `protection`, `stax`,
  `card_advantage`, `discard`, `threat`.
- **Hoser `attacks` tags** (`data/hosers/legacy.json`, 37 entries; measured 2026-07-31):
  `combo`(10), `storm-reliant`(10), `graveyard-recursion`(8), `greedy-manabase`(7),
  `graveyard-fuel`(4), `ramp`(4), `_hate`(3), `plays-blue`(3), `creature-based`(3),
  `noncreature-reliant`(2), `plays-red`(2), `colorless-reliant`(1), `low-curve`(1) — plus
  per-entry `swing`, `symmetry` (`_VALID_SYMMETRY`), `castable_any_color`, `cast_requires`
  (`_VALID_CAST_REQUIRES`), `max_copies`.
- **Linchpin `neutralized_by` capability tokens** (8, per `impact.py` Unit B2):
  `artifact-ability-lock`, `artifact-bounce`, `artifact-removal`, `exile-graveyard`,
  `counter-on-cast`, `board-sweep`, `creature-removal`, `enchantment-removal` — bridged today
  by the hand-curated 24-card `_CAPABILITY_BY_NAME` table.
- **InteractionFacts** (`interaction_facts.py`): `affects` (symmetric | opponent-only |
  targeted | self-only | none), `permanence` (static | activated | triggered | one-shot),
  `self_graveyard_safe`, `touches_graveyard`, `graveyard_count_reduction`, `free_cast`,
  `evidence`, `confidence`.

### 1.3 The verified bug classes map to four missing dimensions

Each dogfooding-verified bug is a **dimension the flat regex layer cannot represent**, not a
tunable pattern:

| Bug (child story / finding) | Failure | Missing IR dimension |
|---|---|---|
| `_RE_GRAVEYARD` misses Exhume ("Each player puts a creature card from **their** graveyard onto the battlefield" — verified in DB) | possessive set `(a|any|your)` predates the 2018 their-templating `[card-semantics-ir-wotc-they]{2}` | **owner_scope** as an enum, not a possessive-word list |
| Wasteland/Ghost Quarter labeled `creature-based` | `"destroy target"` substring is object-blind ("destroy target **land**") | **object_type** of the affected object |
| FoN derive quirk: tagged as graveyard hate | `"graveyard" AND "exile"` co-occurrence spans clauses — FoN's "exile a blue card from your hand" is a *cost*, "…into its owner's graveyard" is a replacement destination | **clause_role** (cost vs effect vs condition) + clause-local matching |
| FoV/Krosan Grip carry `attacks={greedy-manabase}` | destroying artifacts/enchantments *protects* your greedy manabase from Blood Moon/Chalice; the attacks vocabulary has no direction | **polarity** (answers / protects / exploits) |
| `_PITCH_SPELL_RE` escaped-paren bug | `\(its|their\)` makes the parens literal — the alternation can never match real text | (mechanical, but shows unreviewable inline patterns) |
| Defense Grid false positive (symmetric self-tax recommended into an instant-speed deck) | symmetry detected but **self-impact** never priced; catalog resorts to a `_hate` pseudo-tag for direction inversion | **owner_scope × polarity** composed |

The IR schema must therefore carry `owner_scope`, `object_type`, `clause_role`, and
`polarity` as first-class typed fields on every fact. This matches the epic's original park
(clause-level cost/effect segmentation, subject/object types, owner scope, timing, zones).

---

## 2. Prior art — what exists, what it teaches

### 2.1 The rulebook is a semantic vocabulary source

The Comprehensive Rules (effective 2026-06-19) enumerate two closed vocabularies: rule 701
defines keyword actions — "specialized verbs … whose meanings may not be clear. These
'keywords' are game terms" `[card-semantics-ir-cr]{1}` — with 69 numbered subsections, and
rule 702 defines keyword abilities ("the object lists only the name of the ability as a
'keyword'") `[card-semantics-ir-cr]{1}` with 194 subsections. MTGJSON ships the same
vocabulary as versioned JSON (`Keywords.json`, build 5.3.0+20260731: 78 keyword actions, 220
keyword abilities, 69 ability words — larger than the CR counts because variant/funny-set
keywords are included) `[card-semantics-ir-mtgjson-keywords]{7}`.

More importantly for this project, **cost semantics are CR-templated**:

> "Alternative costs are usually phrased, 'You may [action] rather than pay [this object's]
> mana cost,' or 'You may cast [this object] without paying its mana cost.'" — CR 118.9
> `[card-semantics-ir-cr]{1}`

and additional costs are the distinct rules concept "that its controller must pay at the same
time they pay the spell's mana cost" (CR 118.8) `[card-semantics-ir-cr]{1}`. The pitch
detection that `_FREE_SPELL_RE`/`_PITCH_SPELL_RE` approximate is not folklore — the exact
phrasing surface is normative, so a tier-1 deterministic extractor can be specified against
the rulebook, and cost-vs-effect segmentation (the FoN fix) is a rules distinction, not a
heuristic.

### 2.2 Scryfall: `keywords` is free but covers only keyword mechanics

Scryfall card objects carry `keywords` — "An array of keywords that this card uses, such as
'Flying' and 'Cumulative upkeep'" `[card-semantics-ir-scryfall-docs]{3}` — plus `oracle_id`
("consistent across reprinted card editions") as the natural stable key for derived
semantics `[card-semantics-ir-scryfall-docs]{3}`. Live checks (2026-07-31) show the exact
boundary: Murktide Regent returns `["Flying", "Delve"]`, while Force of Negation (pitch
alternative cost) and Leyline of the Void (opening-hand + graveyard replacement) both return
`[]` `[card-semantics-ir-scryfall-obs]{4}`. So the field is reliable seed data for the
keyword-mechanic facet (delve/flash/ward/storm…) and structurally silent on the templated
prose where all four advisory bugs live. The engine's `Card` model currently drops the field
(`models/card.py` defines no `keywords`; `extra="ignore"` discards it) — ingesting it is a
free early win, but it cannot replace text-derived facts.

MTGJSON's Card (Atomic) adds pre-parsed type decomposition (`types`/`subtypes`/`supertypes`,
"A list of card subtypes found after em-dash") and the same keyword list per card
`[card-semantics-ir-mtgjson-atomic]{6}` — useful cross-checks, no functional tagging.

### 2.3 Scryfall Tagger: reachable as a diagnostic, never ground truth

Tagger's community-maintained functional tags are queryable through the ordinary public
search API: "You can use function:, otag:, or oracletag: to find 'Oracle' tags which describe
the function of the card. Data for these two features comes from the Tagger project"
`[card-semantics-ir-scryfall-tagger]{5}`. A live query (`otag:removal name:"Swords to
Plowshares"`) resolves through `api.scryfall.com/cards/search`
`[card-semantics-ir-scryfall-tagger]{5}`. Access is per-tag set membership — card objects
carry no tag list `[card-semantics-ir-scryfall-obs]{4}` — so the natural integration is an
**audit job**: for each IR capability, pick the nearest Tagger tag, pull its membership for
the Legacy-relevant card pool, and emit a divergence report (divergence-as-diagnostic
pattern). Crowd-sourced, unversioned data: exactly what the epic's fixed input relegates to
candidate-seeding, never gating.

### 2.4 Rules engines: both mature systems chose parameterized capability vocabularies

Forge implements every card as a plain-text script over a typed effect API — Force of
Negation is one `S:` line declaring `Mode$ AlternativeCost | Cost$
ExileFromHand<1/Card.Blue+Other> | Condition$ NotPlayerTurn` and one `A:SP$ Counter |
ValidTgts$ Card.nonCreature | Destination$ Exile` line `[card-semantics-ir-forge-script]{8}`.
XMage builds the same card from library components: `AlternativeCostSourceAbility(new
ExileFromHandCost(...), NotMyTurnCondition.instance, ...)` plus
`CounterTargetWithReplacementEffect(PutCards.EXILED)` with a typed target filter
`[card-semantics-ir-xmage-fon]{10}`. Neither parses oracle text at runtime; both maintain a
**closed, named, parameterized capability vocabulary** instantiated per card as reviewable
data/code, with the oracle text kept adjacent (Forge's `Oracle:` line, XMage's comments) so a
human can diff claim against source — precisely the mechanical-grounding shape this project
already enforces via `evidence` fields.

Licensing: Forge is GPL-3.0 (GitHub license API: `"spdx_id": "GPL-3.0"`)
`[card-semantics-ir-forge-license]{9}` — read as prior art, never bulk-import script content.
XMage is MIT (`"spdx_id": "MIT"`) `[card-semantics-ir-xmage-fon]{10}`, permissively usable as
a cross-validation reference.

### 2.5 Grammar and NLP attempts: full parsing is a research project

- A published ANTLR4 grammar effort covers "all 273 cards of Guilds of Ravnica" — one
  Standard set — and documents the canonical failure modes: referent ambiguity ("those
  creatures" mis-resolved on Beamsplitter Mage), templating exceptions ("I thought that the
  template '[object] gains [abilities] until [something happens]' would work for all
  ability-gaining abilities, but Chance for Glory reads, 'Creatures you control gain
  indestructible.' There's no 'until.'"), and compound-noun ambiguity, plus seven cards
  needing bespoke workarounds within even that scope `[card-semantics-ir-mtg-grammar-blog]{11}`.
- Demystify — "an attempt to make it possible for a computer to understand what general
  Magic: The Gathering cards do" (ANTLR 3.5 + Python) — has run for a decade without reaching
  general coverage `[card-semantics-ir-demystify]{12}`.
- mtgencode is explicit that its machine-readable card format is surface normalization: "The
  purpose of this code is mostly to wrangle text between various human and machine readable
  formats" `[card-semantics-ir-mtgencode]{13}` — the neural-generation lineage never yields a
  queryable semantic representation.
- Ling et al. (ACL 2016) frame per-card semantics as supervised generation of "programming
  code from a mixed natural language and structured specification," creating the MTG
  card2code dataset `[card-semantics-ir-card2code]{14}` — i.e., even the academic track
  treats oracle-text→semantics as a learned extraction problem against a capability DSL, not
  as grammar parsing.

**Lesson:** for a 35k-card corpus consumed by an advisory layer, extract **facets you can
validate** rather than parse trees you can't. The grammar failure modes (referents, template
exceptions) are exactly where curation is unavoidable; the IR should budget for it
structurally (curated-override tier) instead of pretending the extractor will be total.

---

## 3. Template linguistics — how far templates go before curation

### 3.1 High-consistency template families (deterministic extraction is safe)

| Template family | Canonical surface | Basis |
|---|---|---|
| Alternative/pitch cost | "you may [action] rather than pay [this object's] mana cost", "without paying its mana cost" | CR-normative phrasing `[card-semantics-ir-cr]{1}` |
| Additional cost | "As an additional cost to cast this spell, [action]" | CR 118.8 concept `[card-semantics-ir-cr]{1}`; clause always sentence-initial in the cost position |
| Keyword line | bare keyword tokens, comma-separated | closed vocab, and Scryfall pre-extracts it `[card-semantics-ir-scryfall-obs]{4}` |
| Owner scope possessives | "your graveyard" / "their graveyard" / "an opponent's graveyard" / "each player" / "each opponent" / "target player" | small closed set — but MUST include post-2018 "their" `[card-semantics-ir-wotc-they]{2}` |
| Color-conditional (blasts) | "target red spell", "destroy target blue permanent", "if it's red" | the existing `_RE_BLAST_*` family already exploits this |
| Activated ability | "[cost]: [effect]" line shape | CR-structural; `_RE_ACTIVATION` approximates it |
| Trigger | line begins "When/Whenever/At" | CR-structural |
| Opening-hand | "If this card is in your opening hand, you may begin the game with it on the battlefield" | verbatim on Leyline `[card-semantics-ir-scryfall-obs]{4}`; drives k_min≈4 copy semantics (see §6) |

### 3.2 Templating drift is a first-class hazard

Oracle text is retroactively re-templated: in 2018 Wizards replaced "he or she"/"his or her"
with singular "they/their" across card text — Duress went from "Target opponent reveals his
or her hand" to "Target opponent reveals their hand" `[card-semantics-ir-wotc-they]{2}`. The
Exhume bug is this exact drift biting a possessive-word list six years later.
Consequences for the design:

1. **Version the IR against a dated card snapshot** (the card refresh already exists;
   semantics inherit its date).
2. **Pin verbatim oracle text in every golden fixture** so a Scryfall re-template fails the
   fixture loudly instead of silently shifting classifications (the fixture asserts both
   "this text produces these facts" and "this card still has this text").
3. Owner-scope extraction operates on an **enum** derived from a maintained possessive
   vocabulary — adding a new surface form is a one-line vocab change with a fixture, not a
   regex rewrite across four files.

### 3.3 Where curation is unavoidable

From the grammar-attempt failure modes `[card-semantics-ir-mtg-grammar-blog]{11}` and this
project's own incidents: cross-clause referents ("that spell", "it"), template exceptions,
mechanically heterogeneous vocabularies (the declined `trigger-reliant` axis), name-keyed
semantics with no textual signature (*goyf sizing, Urzatron lands — already name-matched
today), and judgment calls like Endurance counting as `exile-graveyard`-equivalent
(documented in `impact.py`'s curation notes). The IR must make curated facts **first-class
and precedence-ordered** (hybrid derived+curated registry pattern), not an embarrassment
bolted on later.

---

## 4. IR shape — options and recommendation

### 4.1 Options

**A. Open tagged-facts model.** Free-form typed predicates (`removes(target_type, condition)`,
`taxes(amount, scope)`) added as needed. Flexible, but the predicate space itself becomes
uncontrolled vocabulary — the current `_hate` pseudo-tag problem reborn one level up, and the
closed-vocabulary fail-fast pattern has nothing to check membership against.

**B. Closed capability vocabulary with typed parameters.** A frozen enum of capabilities
(extendable only by schema change + fixtures), each fact carrying the same typed dimension
fields. This is the shape both production rules engines converged on: Forge's named effect
APIs with `Key$ Value` params `[card-semantics-ir-forge-script]{8}` and XMage's named
component classes with typed arguments `[card-semantics-ir-xmage-fon]{10}` — proven to cover
the whole game, so the advisory-scoped subset is safely expressible.

**C. Full effect AST.** Clause trees with resolved referents. Required for a rules engine;
unjustified here — the grammar prior art shows referent resolution and template exceptions
make totality a research project `[card-semantics-ir-mtg-grammar-blog]{11}`
`[card-semantics-ir-demystify]{12}`, and no advisory consumer needs tree structure (every
consumer contract in §1.2 is a flat tag set or a small enum record).

**Recommendation: B**, as **clause-scoped typed facts** — option B's closed vocabulary, with
option A's predicate readability recovered through typed parameters, and one deliberate
borrowing from C: facts are extracted **per clause** with `clause_role` attached, because
clause-locality is what kills the FoN class of bug (§1.3). Goldfish/trainer extension later
adds capabilities and params (zones, timing detail) without changing the fact shape — the
schema axis is open, the vocabulary axis is closed per version.

### 4.2 Schema sketch

```jsonc
// semantics/data/facts/<snapshot-date>.json — JSON SSOT, rebuildable DuckDB table
{
  "schema_version": 1,
  "card_snapshot": "2026-07-31",
  "cards": {
    "<oracle_id>": {
      "name": "Force of Negation",
      "oracle_text_sha": "…",          // drift tripwire: re-template invalidates facts
      "facts": [
        {
          "capability": "free_cast",   // closed enum member
          "clause_role": "cost",       // cost | effect | condition | replacement
          "owner_scope": "self",       // self | opponent | each | targeted | none
          "polarity": "enables",       // answers | protects | exploits | enables | taxes
          "object_type": null,
          "params": {"mode": "pitch", "pitch": {"color": "U", "zone": "hand"},
                     "condition": "not_your_turn"},
          "timing": "instant_speed",
          "evidence": "you may exile a blue card from your hand rather than pay this spell's mana cost",
          "provenance": "template:alt-cost",   // template:<id> | llm:<batch> | curated:<file>
          "confidence": "established"
        },
        {
          "capability": "counters",
          "clause_role": "effect",
          "owner_scope": "targeted",
          "polarity": "answers",
          "object_type": "spell",
          "params": {"object_filter": {"noncreature": true}, "destination": "exile"},
          "timing": "instant_speed",
          "evidence": "Counter target noncreature spell.",
          "provenance": "template:counter-target",
          "confidence": "established"
        }
      ]
    }
  }
}
```

Candidate capability enum for the advisory scope (~20, closing over §1.2's consumers):
`counters`, `removes`, `exiles_graveyard`, `restricts_graveyard` (Cage-style, no count
reduction), `recurs_from_graveyard`, `fuels_from_graveyard` (delve/delirium/threshold/goyf),
`taxes`, `locks_ability`, `bounces`, `sweeps`, `discards`, `tutors`, `draws`, `adds_mana`
(ritual/fast-mana), `free_cast`, `protects`, `wins_attrition` (threat proxy), `storm`,
`opening_hand_start`, `land_denial`. Every enum (capability, clause_role, owner_scope,
polarity, object_type, timing, confidence) gets a module-level `frozenset` + fail-fast
membership check per the closed-vocabulary pattern.

### 4.3 Consumer derivations (the migration contract)

- `hoser.attacks` ← rule table over facts: e.g. `counters(object_filter.noncreature)` →
  `noncreature-reliant`; `removes(object_type=creature)` → `creature-based`;
  `removes(object_type∈{artifact,enchantment}, polarity=protects)` → **no attack tag**
  (fixes FoV) but feeds a new `protects` channel the coverage solver can use or ignore.
- `linchpin.neutralized_by` bridge ← capability+params map onto the 8 tokens (retiring the
  24-card `_CAPABILITY_BY_NAME` table into curated-tier facts).
- `InteractionFacts` ← direct projection (`affects` = owner_scope over graveyard-touching
  facts; `graveyard_count_reduction` = `exiles_graveyard` with count-reducing params;
  `permanence` from timing/clause structure; `free_cast` from `free_cast` fact).
- `_card_roles` / vulnerability densities ← role = presence of capability facts; the
  density thresholds in `whattoplay.py` stay untouched (they are calibration, not semantics).

### 4.4 Extraction pipeline (three tiers, precedence-ordered)

1. **Tier 1 — deterministic template extractors** for §3.1 families, specified against CR
   phrasings `[card-semantics-ir-cr]{1}` and run per clause (split on newline, then on
   sentence boundaries; cost clauses identified by CR-templated markers). Plus direct
   ingestion of Scryfall `keywords` `[card-semantics-ir-scryfall-obs]{4}` (requires adding
   the field to the Card model and the cards table).
2. **Tier 2 — batched LLM extraction** into the validated schema for Legacy-relevant cards
   the templates don't cover, run once per card snapshot against verbatim oracle text,
   schema-validated on load, `provenance: llm:<batch-id>`, confidence capped at `evolving`
   until a fixture or human review promotes it. (This is the epic's "interpretation happens
   ONCE, against source text" property; the card2code line of work is the precedent for
   text→DSL extraction at corpus scale `[card-semantics-ir-card2code]{14}`.)
3. **Tier 3 — curated overrides** (JSON under `PACKAGE_DATA_DIR`, curated-JSON-loader
   pattern): name/oracle_id-keyed facts that win by key over derived ones (hybrid
   derived+curated registry). Endurance-style judgment calls and name-keyed semantics live
   here permanently, with `_comment` grounding quotes as in the existing catalogs.

The 28 regexes then demote: tier-1 extractors subsume most; the remainder become consumers
of facts. Nothing in the advisory layer matches oracle text directly anymore.

---

## 5. Validation architecture

### 5.1 Golden fixtures per semantic cluster (the authority)

Organize fixtures by **semantic cluster** = one capability family + its known confusables,
because the bugs live at cluster boundaries (blast vs removal, cost-exile vs graveyard-hate):

```
tests/semantics/fixtures/
  pitch_free_cast.json      # FoW, FoN, Daze, Misdirection, FoV, Mindbreak Trap; confusables: Fireblast (sac cost), Snuff Out
  graveyard_scope.json      # Leyline of the Void, Nihil Spellbomb, Grafdigger's Cage, Surgical, Endurance; confusables: Exhume, Animate Dead, Snapcaster
  color_conditional.json    # Pyroblast, Hydroblast, REB/BEB, Mystical Dispute; confusables: generic counters
  counters.json             # Counterspell, FoN (noncreature), Consign (colorless+trigger), Flusterstorm (storm-restricted)
  removal_object_types.json # StP, Wasteland, Ghost Quarter, Krosan Grip, Meltdown; confusables: edicts (opponent chooses)
  taxes_locks.json          # Chalice, Trinisphere, Defense Grid (symmetric!), Thorn effects
  tutors_draw.json          # Brainstorm, Ponder, Demonic Tutor, Enlightened Tutor (restricted)
  graveyard_fuel.json       # Murktide (delve), goyfs (name-keyed), threshold/delirium cards
  opening_hand.json         # Leylines, Gemstone Caverns
```

Each fixture entry: `{name, oracle_id, oracle_text (verbatim, pinned), expected_facts:[…]}`.
The fixture asserts (a) extraction of the pinned text yields exactly the expected facts, and
(b) the live snapshot's text for that oracle_id still hashes to the pinned text — separating
"extractor regressed" from "Wizards re-templated" `[card-semantics-ir-wotc-they]{2}`, which
fail differently (the second updates the pin after review). Every verified bug card (Exhume,
Wasteland, FoN, FoV, Krosan Grip, Defense Grid) enters its cluster's fixture as a permanent
regression case. Factory-fixture + hermetic-DB conventions from `conftest.py` apply; fixtures
never read the default DB.

### 5.2 Corpus classification census (the drift regression)

A full sweep classifies all cards in the snapshot (39,452 cards, 35,698 with non-empty
oracle text — measured 2026-07-31 on `data/legacy.duckdb`) and pins a **census**: per
capability, the membership count and a small sorted sample of member names. The census file
is a committed golden; CI re-runs the sweep and diffs. Two failure modes it catches: an
extractor change that silently reclassifies thousands of cards (count moves outside a
declared tolerance band → the change must ship with an updated census and a human-readable
justification), and a card-snapshot refresh that shifts counts (expected, reviewed the same
way). This is the freshness-stripped-golden discipline applied at corpus scale, and it is
cheap: one pure pass over oracle text per CI run.

### 5.3 External divergence diagnostics (never gating)

- **Scryfall Tagger:** for each capability with a near-synonym tag, an offline audit pulls
  `otag:<tag>` membership via the public search API
  `[card-semantics-ir-scryfall-tagger]{5}` for the Legacy card pool and reports both
  directions of divergence (we-say-they-don't / they-say-we-don't) with oracle-text excerpts.
  Divergences are review queue items — the epic's fixed input forbids them gating.
- **Forge/XMage:** spot-check disagreements by reading the corresponding card script/class
  (Forge GPL-3.0: read-only, no import `[card-semantics-ir-forge-license]{9}`; XMage MIT
  `[card-semantics-ir-xmage-fon]{10}`). Highest value on the curated tier (Endurance-style
  judgment calls), where seeing how a full rules engine modeled the card disciplines our
  approximation.

### 5.4 Honest degrade

Cards with no facts get an explicit `unclassified` marker (with the fallback behavior the
consumer had before — e.g. promoted-candidate fallback tags), never a silent empty set;
`confidence` rides every fact (template-derived facts on fixture-covered clusters =
`established`; LLM-derived unreviewed = `evolving`; conflicting scope signals =
`speculative`, preserving `interaction_facts`' convention); advisory surfaces keep quoting
`evidence` verbatim (audit-echo lines), which the schema makes mandatory rather than
best-effort.

---

## 6. Implementation notes

- **Module boundary:** `semantics/` owns schema (Pydantic models on `LegacyEngineModel`),
  enums + fail-fast validators, tier-1 extractors, tier-2 batch runner, tier-3 curated
  loader, census tooling. Consumers (`interaction_facts.py`, `whattoplay.py`,
  `sideboard.py`, `card_tags.py`, `impact.py`) import facts and derivation helpers; nothing
  outside `semantics/` touches oracle text with a pattern. Storage follows JSON-SSOT +
  rebuildable-DuckDB-table (a `card_facts` table with a `rebuild_card_facts(con)` path) so
  SQL surfaces can join facts to corpus stats.
- **Migration order (suggested for epic-design):** (1) schema + enums + fixture harness;
  (2) tier-1 extractors for pitch/free-cast + graveyard scope + blasts (the bug clusters) and
  the InteractionFacts projection — this immediately re-fixes the four tactical bugs at the
  IR level with fixtures; (3) Scryfall `keywords` ingestion (Card model + cards table +
  keyword-facet facts); (4) hoser-attacks + neutralized_by derivations behind an opt-in flag
  with byte-identical no-op path (opt-in-analytics-overlay pattern), then flip after the
  census stabilizes; (5) tier-2 LLM batch for the Legacy pool remainder; (6) Tagger
  divergence audit job.
- **Early consumers beyond bug fixes:** `feature-min-viable-copy-count` needs exactly two
  facts this IR ships — `free_cast(mode=pitch)` ⇒ k_min=2 and `opening_hand_start` ⇒
  k_min≈4 (per the copy-count distribution study's mechanics-derived floors, see
  `docs/analysis/copy-count-distribution-study.md`); the deferred goldfish epic consumes
  `timing`/`adds_mana`/castability params later — the schema fields exist from day one, the
  extractors come later.
- **What NOT to build:** no runtime text parsing in consumers; no grammar/AST ambition
  (§2.5); no auto-calibration of divergences (§5.3); no reuse of the vulnerability-density
  thresholds as semantics (they stay in `whattoplay.py` as calibration).

## Sources

1. Magic: The Gathering Comprehensive Rules, effective 2026-06-19 (Wizards of the Coast) — https://media.wizards.com/2026/downloads/MagicCompRules%2020260619.txt
2. "Dominaria Frame, Template, and Rules Changes" (Wizards of the Coast, 2018-03-21) — https://magic.wizards.com/en/news/announcements/dominaria-frame-template-and-rules-changes-2018-03-21
3. Scryfall API documentation, Card Objects — https://scryfall.com/docs/api/cards
4. Scryfall REST API live card objects (Force of Negation / Murktide Regent / Leyline of the Void, fetched 2026-07-31) — https://api.scryfall.com/cards/named?exact=Force%20of%20Negation
5. Scryfall search-syntax documentation, Tagger Tags — https://scryfall.com/docs/syntax
6. MTGJSON data model, Card (Atomic) — https://mtgjson.com/data-models/card/card-atomic/
7. MTGJSON Keywords.json v5.3.0+20260731 — https://mtgjson.com/api/v5/Keywords.json
8. Forge card script, force_of_negation.txt (Card-Forge/forge) — https://raw.githubusercontent.com/Card-Forge/forge/master/forge-gui/res/cardsfolder/f/force_of_negation.txt
9. Card-Forge/forge license (GitHub license API) — https://api.github.com/repos/Card-Forge/forge/license
10. XMage ForceOfNegation.java (magefree/mage) — https://raw.githubusercontent.com/magefree/mage/master/Mage.Sets/src/mage/cards/f/ForceOfNegation.java
11. Petr Hudeček, "A formal grammar for Magic: the Gathering" — https://hudecekpetr.cz/a-formal-grammar-for-magic-the-gathering/
12. Demystify README (Zannick/demystify) — https://raw.githubusercontent.com/Zannick/demystify/master/README
13. mtgencode README (billzorn/mtgencode) — https://raw.githubusercontent.com/billzorn/mtgencode/master/README.md
14. Ling et al., "Latent Predictor Networks for Code Generation" (ACL 2016) — https://arxiv.org/abs/1603.06744

Internal grounding (code and data read 2026-07-31, no attestation needed — verifiable
in-repo): `src/legacy_engine/{card_tags,interaction_facts}.py`,
`src/legacy_engine/advisory/{whattoplay,sideboard,impact,linchpins}.py`,
`src/legacy_engine/models/card.py`, `src/legacy_engine/data/{hosers,linchpins}/legacy.json`,
`data/legacy.duckdb` (cards table), `docs/analysis/copy-count-distribution-study.md`,
`.work/active/epics/epic-card-semantics-ir.md`.
