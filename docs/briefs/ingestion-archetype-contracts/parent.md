---
description: Read first for the ingestion + archetype-parser data layer — the synthesized contracts and build plan for legacy-engine's ingestion/ and archetype/ modules. Navigation hub for the 7 specialist briefs.
type: program-parent
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Synthesizes a 7-specialist deep-research campaign into one buildable design for legacy-engine's
  ingestion/ and archetype/ modules. Legacy decks arrive as bare 75-card lists with no commander key,
  so archetype labeling is a classification problem — solved by wrapping Badaro's MTGOFormatData rules
  (vendored as pinned JSON) and reimplementing the ~600-line MTGOArchetypeParser matcher in Python.
  The campaign pins every data contract end-to-end: the fbettega PascalCase CacheItem JSON, the rule
  schema (conditions/variants/fallbacks), the exact matching algorithm, the C#→Python port + golden-test
  plan, the Scryfall card/color contract, and the ops/meta-% layer. The single most important seam: the
  card-data layer's reuse verdict is contested — CARD-CONTRACT says extend edh-engine's hand-rolled
  scryfall.py while PRIOR-ART says adopt Scrython/mtg_parser; this must be resolved at design time.
key_findings:
  - "Archetype labeling is a CLASSIFICATION problem, not a key-lookup. Unlike cEDH (commander = the key), Legacy decks are bare 75-card lists. The decision is made: wrap Badaro/MTGOFormatData rules + port the MTGOArchetypeParser matcher to Python — and no maintained Python port of that matcher exists, so this is genuinely net-new code (PRIOR-ART)."
  - "Own the matcher, rent the rules. Vendor MTGOFormatData JSON as a git-subtree pinned to a recorded SHA (data/archetype_rules/ + RULES_MANIFEST.json); reimplement ONLY the ~600-line matcher; reject shelling-out to the archived C# binary and .NET interop (PORT). The C# engine was archived 2025-09-24 — a frozen, lockable port target (PORT, CLASSIFY)."
  - "Deck color = INTERSECTION of lands' produced_mana (minus C) and nonlands' colors — NOT color_identity, NOT Scryfall colors-of-everything. A color is in the deck name only if it appears in BOTH a land source and a nonland card. edh-engine correctly uses color_identity for cEDH; legacy-engine must NOT (CARD-CONTRACT, CLASSIFY §5)."
  - "The fbettega schema is PascalCase CacheItem {Tournament, Decks[], Rounds[], Standings[]} with cards as {Count, CardName} — the README example is STALE (lowercase keys, Formats as list). Build against to_dict()/live files. Formats is a bare string in live files but typed List[str] — normalize defensively (INGEST)."
  - "Provenance (online vs paper) is NOT a field — derive it at ingest from the source DIRECTORY (MTGO/Manatraders→online; MTGmelee/Topdeck→paper) plus the Tournament.Uri host. Keep the provenance tag on every deck row; online and paper metagames diverge materially and meta-% must split on it (INGEST §3, SERVE/OPS §5)."
  - "Coverage is structurally BIMODAL and this gates what's computable. MTGO Challenges + paper Melee carry Rounds (per-match pairings) + Standings → we CAN compute our own matchup matrix (no dependence on the 403-blocked mtgdecks.net). MTGO 5-0 Leagues are decklist-only (Rounds=[], Standings=[]) → they feed raw-count meta-% but NOT matchup cells or win-rate weighting. Empty Rounds/Standings is NORMAL, never an error (INGEST §6, SERVE/OPS §4)."
  - "Fidelity is the dominant port risk. The golden gate replays the archived C# parser's own labels over a frozen fbettega corpus at the same pinned rules SHA and asserts ≥99% per-deck label agreement (target 100%) as a CI check; every disagreement is a port bug, never silently accepted (PORT §4)."
  - "Drift is handled fail-fast, edh-consistent. A new archetype = zero code (data-driven); a new condition Type RAISES at load time (UnknownConditionTypeError) and the `legacy refresh rules` sync scan exits non-zero — a silently-skipped condition would mislabel decks and corrupt the meta-% the platform exists to produce (PORT §5)."
  - "Index the WHOLE oracle pool, don't pre-resolve a fixed pool. Legacy's card pool (~30k+ Oracle IDs, a Modern superset) dwarfs cEDH's ~3,148 cards; a new tournament can introduce any legal card, so the resolver must fall back to the full Scryfall oracle_cards bulk index, not a card_pool.json subset (CARD-CONTRACT §4)."
  - "Mirror-and-decouple is non-negotiable. The source layer is one community scrape (fbettega) over an upstream WotC actively destabilizes (Badaro's predecessor died 2025-06-10; MTGO degraded 2024-06-20; a Feb-2026 cut was rolled back in days). Vendor both repos pinned behind an ingestion/ port; analytics never reads live upstream; a staleness health-check degrades, never outages (SERVE/OPS §1-2)."
  - "Card-name matching is exact, case-sensitive string equality with NO normalization in the matcher — split/DFC/'//' handling is entirely an ingest/card-contract responsibility. The scraper already normalizes CardName to Scryfall-canonical form, but its map is runtime-built and drifts, so validate every name against our own mirror and route misses to an unmatched bucket, never drop the deck (INGEST §6, CLASSIFY §6, CARD-CONTRACT §2)."
related:
  - {slug: docs/briefs/legacy-metagame.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-foundations.md, relationship: depends-on}
---

# Parent: Ingestion + Archetype-Parser Data Contracts for legacy-engine

Read this first. It is the navigation hub and synthesized design for legacy-engine's `ingestion/` and
`archetype/` modules, distilled from a 7-specialist deep-research campaign. The specialist briefs in this
directory carry the field-by-field detail; this brief stitches them into one end-to-end pipeline and flags
where they disagree.

## Context

legacy-engine is a Python 3.11 CLI Magic: The Gathering **Legacy** analytics platform, a sibling to
edh-engine. The two share a stack and a knowledge layer, but the data layer has a fundamental architectural
delta that triggered this campaign:

**In cEDH, the commander IS the archetype key** — edh-engine can key analytics off the commander pair
directly (`canonical_commander_key` pattern). **In Legacy, there is no such key.** A tournament deck is a
bare 75-card list (60 main + 15 side) with a player and a finish, and nothing that names what it *is*.
Turning "4 Delver of Secrets, 4 Daze, …" into the label **"Dimir Tempo"** is a genuine **classification
problem**. This is the "key novel subsystem" the architecture calls out: `archetype/`.

The community already solved labeling — with two C#/JSON tools by Badaro: **MTGOFormatData** (the
archetype rules, as JSON data) and **MTGOArchetypeParser** (the C# engine that evaluates those rules
against a decklist). The standing decision is to **wrap MTGOFormatData's rules, ported to Python**, so the
taxonomy stays aligned with the community's and remains auditable (PRINCIPLES §4: "knowledge is compiled,
not re-derived"). The campaign's job was to pin every data contract along that pipeline precisely enough to
design `ingestion/` and `archetype/` without guessing — because the C# matcher is archived (frozen, but
unmaintained) and the data lives in community repos with no SLA.

## Decomposition

The campaign ran 7 specialists at depth 1, mapped to the ingest→classify→serve pipeline:

- **INGEST** — [fbettega-cache-schema.md](fbettega-cache-schema.md): the tournament-data JSON schema,
  repo layout, provenance encoding, cadence, and how to consume it.
- **RULES** — [mtgoformatdata-rule-schema.md](mtgoformatdata-rule-schema.md): the archetype rule-as-data
  schema — conditions, variants, fallbacks, color flags, the Legacy taxonomy.
- **CLASSIFY** — [archetype-matching-algorithm.md](archetype-matching-algorithm.md): the exact
  MTGOArchetypeParser matching algorithm, edge cases, and Python pseudocode.
- **PORT** — [csharp-python-port-strategy.md](csharp-python-port-strategy.md): the C#→Python port plan
  (vendor rules + reimplement matcher), the golden-test fidelity gate, drift handling.
- **CARD-CONTRACT** — [scryfall-card-contract.md](scryfall-card-contract.md): the Scryfall card-data +
  color-resolution contract, the Card model, name resolution.
- **SERVE/OPS** — [ingestion-ops-and-metashare.md](ingestion-ops-and-metashare.md): source fragility +
  mirroring, the three meta-% definitions, matchup-matrix feasibility, online/paper split.
- **PRIOR-ART** — [prior-art-scan.md](prior-art-scan.md): existing tools/ports and reuse verdicts.

## Synthesized build plan

This walks a raw tournament JSON through to a labeled, archetyped, meta-% / matchup-matrix output, pulling
the load-bearing facts from each brief into one design.

### 1. Mirror the inputs (SERVE/OPS, RULES, PORT)

Two upstream repos are vendored as pinned, versioned local inputs — analytics **never** reads live upstream
(the source is a single-maintainer scrape over a WotC upstream that has already died once):

```
data/
  upstream/decklistcache/   # fbettega/MTG_decklistcache — tournament facts
  archetype_rules/          # Badaro/MTGOFormatData (git subtree) — the rules
    Formats/Legacy/{metas.json, color_overrides.json, Archetypes/*.json, Fallbacks/*.json}
  RULES_MANIFEST.json       # { source_repo, pinned_sha, pulled_at, format: "Legacy" }
  MANIFEST.yaml             # per-mirror { repo, commit_sha, fetched_at, newest_tournament_date }
```

Rules are vendored by **git subtree** pinned to a SHA (subtree preferred over submodule; fetch-on-build
rejected as non-deterministic). A `legacy refresh rules` CLI does the monthly sync, diffs the archetype
set, and **scans for unknown condition Types, exiting non-zero** if any appear — so taxonomy drift surfaces
in a reviewed PR, not in production. Cache refreshes daily; rules weekly + on every B&R. A staleness
health-check emits GREEN/YELLOW/RED and, on RED, **freezes the curated layer at last-good and keeps
serving** — degradation, not outage.

### 2. Ingest a tournament JSON behind a port (INGEST, SERVE/OPS)

Each cache file is one **`CacheItem`**: PascalCase top-level keys `{Tournament, Decks[], Rounds[],
Standings[]}`. `Tournament = {Date, Name, Uri, Formats}`; `Deck = {Date, Player, Result, AnchorUri,
Mainboard[], Sideboard[]}` with cards as `{Count, CardName}`; `Standing = {Rank, Player, Points, Wins,
Losses, Draws, OMWP, GWP, OGWP}`; a `Round = {RoundName, Matches:[{Player1, Player2, Result}]}`. **Build
against `to_dict()`/live files — the README example is stale** (lowercase keys, list Formats).

The `FbettegaCacheAdapter` (the only code that knows the raw schema) emits OUR port type — a
`TournamentRecord{event_id, source, online_or_paper, date, format, decks[], rounds[]?, standings[]?}`.
Nothing above `ingestion/` imports the raw cache schema (ports & adapters, mirroring edh-engine's Scryfall
boundary). Three derivations happen at ingest:

- **Filter to Legacy** on `Tournament.Formats` (normalize `str | list[str]`), not the filename — paper
  Melee slugs are free-text.
- **Synthesize provenance**: `online` if source ∈ {MTGO, Manatraders} else `paper`, corroborated by Uri
  host. Tag every deck row with it.
- **Tolerate the bimodal shape**: empty `Rounds`/`Standings` (MTGO Leagues) is normal; `Deck.Date` is
  `null` on Melee (fall back to `Tournament.Date`); `Sideboard` may be `[]`.

Stable keys: `Tournament.Uri` for events, `AnchorUri` for decks; incremental detection diffs the day-folder
file listing against ingested paths.

### 3. Resolve cards + compute colors (CARD-CONTRACT)

Card reference data comes from the Scryfall **`oracle_cards`** bulk file (~173 MB, one object per Oracle ID,
daily cadence, no rate limit on the CDN download). Build a name→card index keyed on full `name` **and** each
`card_faces[].name`, with `' // '` split handling plus curly-apostrophe + accent normalization. Crucially,
**index the whole oracle pool and resolve on demand** — Legacy's pool (~30k+ Oracle IDs) dwarfs cEDH's, and
any legal card can appear, so a fixed `card_pool.json` is a cache, never the authority; misses fall through
to the `POST /cards/collection` API, then to an unmatched bucket (never drop a deck).

**Deck color** is the load-bearing card-contract finding: `compute_deck_colors` = the **intersection** of
(lands' `produced_mana` minus `{C}`) and (nonlands' `colors`), formatted WUBRG. **NOT `color_identity`**
(that is the Commander construct edh-engine uses; it over-colors a Legacy deck) and **NOT** Scryfall
`colors` of everything. This replaces Badaro's hand-curated `card_colors.json` with a Scryfall-derived
computation (single source of truth). Legacy-specific tags (`is_free_spell`, `staple_role`, mana-base flags)
are derived in a tagging pass — pattern-matched from `oracle_text`/`type_line` or curated, seeded from
`legacy-foundations.md`'s staples table.

### 4. Classify each deck (RULES, CLASSIFY, PORT)

The ported matcher is a **pure function** `classify(decklist, ruleset, card_colors) -> ArchetypeResult`.
Rules load via Pydantic from the vendored JSON (a separate loader owns fail-fast validation; the matcher
does no I/O). The algorithm faithfully reproduces MTGOArchetypeParser:

- **A rule matches iff ALL its conditions pass** (AND across conditions; OR within a condition's `Cards`
  array). 12 condition Types: `In{Main,Side,MainOrSide}board`, the `OneOrMore*`/`TwoOrMore*` count trios,
  and `DoesNotContain{,Mainboard,Sideboard}`. `TwoOrMore*` counts **distinct listed card NAMES present**,
  not copies. An empty-`Cards` condition is **skipped** (vacuous), a real footgun.
- **Variants are nested**: tested only if the parent matched; each passing variant emits its own match
  (multiple → a conflict). "Dimir Tempo" arises here: Delver base (`IncludeColorInName:true`) + Tempo
  variant + computed `UB` color → guild table `UB→Dimir` (the guild table is NOT in MTGOFormatData and must
  be reimplemented) → "Dimir Tempo".
- **Fallback** fires only when zero specific archetypes match: score each fallback pile by SUM of `Count`
  of distinct deck cards in its `CommonCards`, pick max (ties → shortest pile), accept only if
  `weight / (len(main)+len(side)) > 0.1` (the 10% floor; denominator is **rows**, not copies — preserve
  for fidelity). Below the floor → "Unknown".
- **Conflicts**: default mode (`None`) emits the literal `Conflict(A,B)` string — a deliberate
  non-resolution. `PreferSimpler` picks the FEWEST-conditions match. Determinism requires loading rule files
  in **sorted filename order** + a stable sort.
- **Companion** is a separate sideboard-only scan against a 10-card map; never folds into archetype matching.

Fidelity is locked by a **golden test**: replay the archived C# parser's own labels over a frozen fbettega
corpus at the same pinned SHA; assert ≥99% per-deck `display_name` agreement (target 100%) as a CI gate.
On every rules sync, regenerate the golden fixture in the same PR. Drift is fail-fast: a new condition Type
raises at load; a new archetype needs zero code.

### 5. Serve meta-% and matchups (SERVE/OPS, CLASSIFY)

With every deck labeled and provenance-tagged, the analytics layer computes:

- **Three labeled meta-% definitions** (never an unlabeled blend — PRINCIPLES §6): (a) raw entry share,
  (b) top-cut presence share, (c) win-rate-weighted share. Published MTGO data is itself success-filtered,
  so even "raw" over a Challenge-only corpus over-counts winners — every emitted share states
  (definition, online/paper basis, window).
- **Our own matchup matrix**, computed from `Rounds[].Matches[]` joined on player name to each side's
  archetype — feasible **only for the subset of events that carry Rounds** (Challenges + paper Melee).
  Leagues are excluded from matchup cells. The 403-blocked mtgdecks.net matrix is a validation cross-check,
  not a source.
- **Online/paper split by default**, blend only as labeled opt-in.
- **Confidence-gate everything** (PRINCIPLES §7): archetype share <2% → "Other"/fringe; matchup cell n<100
  → low-n flag + wide CI (Wilson interval); attach `established|evolving|speculative` + raw n as metadata on
  the stat object itself.

## Key findings

See the frontmatter `key_findings` for the cross-cutting list. The five that most shape the build:

1. **Classification, not lookup** — the entire reason `archetype/` exists; no commander key in Legacy
   (Context; PRIOR-ART confirms no Python port exists, so it is net-new).
2. **Own the matcher, rent the rules** — vendor pinned JSON + reimplement the frozen ~600-line matcher;
   golden-test to ≥99% agreement (PORT, CLASSIFY).
3. **Color = produced_mana ∩ nonland colors, never color_identity** — the one place legacy-engine must
   diverge from edh-engine's color model (CARD-CONTRACT, CLASSIFY §5).
4. **Schema reality ≠ README** — PascalCase CacheItem, stale README; provenance derived from dir+host
   (INGEST).
5. **Bimodal coverage gates computability** — matchups only where Rounds exist; Leagues are decklist-only
   (SERVE/OPS §4, INGEST §6).

## Contradictions & tensions

These are flagged explicitly, not smoothed over. The first is material and must be resolved at design time.

1. **CARD-CONTRACT vs PRIOR-ART — the Scryfall library decision (MATERIAL, UNRESOLVED).** CARD-CONTRACT's
   reuse verdict is "**EXTEND, do not fork** — edh-engine's hand-rolled `ingestion/scryfall.py` transfers
   wholesale" (httpx + bulk download + a hand-built name index). PRIOR-ART's verdict is the opposite for the
   card layer: "**ADOPT Scrython** (rate-limited Scryfall wrapper) and **mtg_parser** rather than
   hand-rolling as edh-engine did … the scrython/mtg_parser adopt decision is the one place to break from
   edh-engine's hand-roll habit." These are in direct conflict: extend the hand-roll vs. replace it with
   libraries. Both are defensible — CARD-CONTRACT optimizes for sibling-stack consistency and an already-
   working module; PRIOR-ART optimizes for not maintaining a Scryfall client. The design decision must pick
   one. (Note a partial reconciliation: Scrython solves only API resolution, which CARD-CONTRACT shows is a
   rare fallback once the full bulk index is in memory; mtg_parser solves decklist-text parsing, which may
   be moot if the only source is fbettega JSON — so the practical conflict may shrink to "is it worth a new
   dependency for the fallback path." Still, the briefs assert opposite verdicts and the design owes an
   explicit call.)

2. **CLASSIFY vs PRIOR-ART — should there even be an ML fallback tier?** PRIOR-ART recommends "strongly
   consider videre's Naive-Bayes as a statistical fallback tier above the pile heuristic" and studying j6e's
   KNN fallback. CLASSIFY/PORT specify a faithful port whose fallback is exactly Badaro's `CommonCards`-pile
   heuristic, with "Unknown" below the 10% floor — and the golden gate asserts ≥99% agreement with the C#
   labels, which an ML tier would by construction break. These aren't strictly contradictory (an ML tier
   could sit *below* "Unknown" as a separate, non-golden-gated suggestion), but they pull in opposite
   directions on scope and on what the fidelity gate even means. Flag for the design: any ML fallback is a
   net-new tier outside the golden contract, not part of the port.

3. **README-vs-real-schema staleness (agreement, but a live hazard).** INGEST and SERVE/OPS both describe
   the cache schema, but INGEST is explicit that the README example is **stale** (lowercase keys, `Formats`
   as a list, a `json_file`/`id` field that `to_dict()` omits) while SERVE/OPS §4.1 quotes the README's
   lowercase field names (`player1`, `card_name`, `round_name`) verbatim as "confirmed." They do not
   contradict on substance — SERVE/OPS is reading field *semantics* off the README and INGEST is reading the
   *serialized casing* off live files — but a builder who takes SERVE/OPS §4.1's casing literally will write
   a parser against the wrong keys. **INGEST's PascalCase, to_dict()-derived schema is authoritative**; treat
   SERVE/OPS's field list as semantic, not literal. Same for `Rounds.Matches[].Result` being a match-score
   string (e.g. `"2-1"`), not per-game.

4. **Matchup-matrix feasibility — the caveat the headline can hide.** SERVE/OPS's "we CAN compute our own
   matchup matrix" is real but load-bearingly conditional, and INGEST independently corroborates the catch:
   Rounds are present for Challenges + paper Melee and **absent for MTGO Leagues**, and the MTGO 2024-06-20
   degradation means even Challenge Rounds/Standings are thinner on newer events. So the matrix's effective
   sample is a *smaller, more challenge/paper-skewed population* than the play-rate sample, and it shrinks
   over time for policy reasons. The two briefs agree; the tension is between SERVE/OPS's confident headline
   and its own §4.3 catch — surface the catch wherever the matrix is presented.

5. **`TwoOrMore*` copy-vs-name semantics — RULES flagged ambiguous, CLASSIFY resolved it.** RULES §1.3
   explicitly flags the copy-vs-distinct-name count as "the one place the data alone is ambiguous — resolve
   against parser source." CLASSIFY §1 resolves it from the C# source: it counts **distinct listed card
   names present**, not copies (`TwoOrMoreInMainOrSideboard` sums main-entry + side-entry counts). Not a
   contradiction — a baton correctly passed — but the resolution lives in CLASSIFY, so the port must take the
   count rule from CLASSIFY, not RULES.

Beyond these, the specialists are notably coherent: the PascalCase schema, the AND/OR condition semantics,
the intersection-color algorithm, the vendor-the-rules/port-the-matcher split, the fail-fast drift posture,
and the mirror-and-decouple ops stance are all consistent across every brief that touches them.

## Coverage assessment

**Solid (build on directly):** the fbettega JSON schema (verified against live files), the rule schema and
condition table (verbatim from README + real files), the matching algorithm (reverse-engineered from C#
source with line cites and Python pseudocode), the color-computation algorithm and its Scryfall field
mapping, the port/vendor/golden-test engineering plan, and the source-fragility/mirroring ops contract.
These are detailed enough to start designing `ingestion/` and `archetype/` now.

**Thin / needs a follow-up:**

- **The matchup-matrix statistics need their own treatment.** SERVE/OPS establishes *feasibility* and names
  Wilson intervals and an n<100 gate, but the actual matrix estimator (shrinkage toward a prior for sparse
  cells, handling the bimodal-coverage population bias, mirror-match policy) is unspecified and deserves a
  dedicated stats brief before the matchup module is designed.
- **Advisory methods.** The "positioning score" that consumes win-rate-weighted share and the matchup matrix
  (referenced in `legacy-metagame.md` §7) has no method brief yet — the advisory `/research` is still
  pending. The data contracts here are its inputs; the scoring method is out of scope for this campaign.
- **The Scryfall-library decision (Contradiction #1)** is a design-time call this campaign surfaced but did
  not settle; it wants an explicit ADR.
- **The guild-name table** (UB→Dimir, etc.) is asserted as "shared, stable MTG convention" to be
  reimplemented, but no brief vendors or specifies it concretely. Low-risk, but it is net-new code the
  classifier needs and nobody owns it yet.
- **`is_free_spell`/`staple_role` derivation** is specified as heuristic-plus-curated but the curated tables
  don't exist; they depend on `legacy-foundations.md`'s staples table as the seed.

## Brief index

| Brief | Role | One line |
|---|---|---|
| [fbettega-cache-schema.md](fbettega-cache-schema.md) | INGEST | The PascalCase CacheItem JSON schema, repo layout, provenance-by-directory, cadence, and Python consumption — README is stale, build against live files. |
| [mtgoformatdata-rule-schema.md](mtgoformatdata-rule-schema.md) | RULES | The archetype rule-as-data schema: Name + Conditions (AND) + Variants + Fallbacks + IncludeColorInName; ~174 Legacy archetypes; color naming is the consumer's job. |
| [archetype-matching-algorithm.md](archetype-matching-algorithm.md) | CLASSIFY | The exact MTGOArchetypeParser algorithm — AND-of-conditions, nested variants, conflict/Unknown sentinels, intersection colors — with Python pseudocode. |
| [csharp-python-port-strategy.md](csharp-python-port-strategy.md) | PORT | Vendor the JSON (pinned git subtree) + reimplement only the ~600-line matcher; golden-test to ≥99% label agreement; fail-fast on unknown condition Types. |
| [scryfall-card-contract.md](scryfall-card-contract.md) | CARD-CONTRACT | Color = produced_mana ∩ nonland colors (never color_identity); whole-oracle name index; the Card model; verdict: extend edh-engine's scryfall.py. |
| [ingestion-ops-and-metashare.md](ingestion-ops-and-metashare.md) | SERVE/OPS | Mirror-and-decouple behind an ingestion/ port; three labeled meta-% definitions; matchup matrix computable from Rounds (bimodal coverage); confidence-gate all stats. |
| [prior-art-scan.md](prior-art-scan.md) | PRIOR-ART | No maintained Python port of the matcher exists (net-new); adopt MTGOFormatData data + fbettega scraper/cache; adopt Scrython/mtg_parser; learn from videre NB + j6e. |
