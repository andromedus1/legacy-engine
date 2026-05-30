---
description: What Scryfall card fields the Legacy archetype classifier keys on, how MTGOArchetypeParser derives deck colors, how decklist names resolve to canonical cards, and whether edh-engine's Scryfall layer can be reused as-is. Read before designing the Card model, the name index, or the color-prefix step of the classifier.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  The CARD-DATA CONTRACT for legacy-engine's archetype classifier. Pins down which Scryfall
  fields feed deck-color naming (the surprise: MTGOArchetypeParser does NOT use Scryfall colors
  OR color_identity — it intersects hand-curated land-colors with nonland-card-colors, which map
  to Scryfall produced_mana for lands and colors for nonlands, never color_identity). Specifies a
  multi-key name index that handles split / DFC / adventure cards, the Scryfall bulk-data choice
  (oracle_cards) and access rules, how the Legacy-specific staple_role / is_free_spell / mana-base
  tags derive from Scryfall fields, and a Card Pydantic model in the edh-engine idiom. Verdict on
  reuse: extend, don't fork.
key_findings:
  - "MTGOArchetypeParser color naming = INTERSECTION of (colors present in the deck's LANDS) and (colors present in the deck's NONLAND cards); a color is in the deck's name only if it appears in BOTH sets (ArchetypeAnalyzer.GetColors, lines 120-124). This is NOT Scryfall colors and NOT color_identity."
  - "Map to Scryfall: land color contribution -> `produced_mana` (Underground Sea: colors=[], produced_mana=[B,U]); nonland color contribution -> `colors` (the mana-cost colors). NEVER color_identity — it folds in rules-text/hybrid symbols and would mis-name decks (e.g. a deck splashing a card with off-color text symbols)."
  - "Badaro derives those colors from a hand-curated card_colors.json (auto-generated from MTGJSON, split into `Lands` and `NonLands`) plus color_overrides.json — NOT from Scryfall. The Python port can replace that file with a Scryfall-derived computation: lands=produced_mana minus {C}, nonlands=colors. RULES sibling owns the rule Cards arrays; this brief owns name->card+colors resolution."
  - "Name resolution: index by full name AND each face name; split/adventure use ' // ' joined names and top-level `colors`/`mana_cost`; DFC/MDFC put per-face `colors`/`mana_cost` on card_faces[] with top-level mana_cost null. Reuse edh-engine's split-on-' // ' indexing; add face-name keys and curly-apostrophe + accent normalization."
  - "Bulk file = `oracle_cards` (one object per Oracle ID, ~173 MB, regenerated ~daily). Correct for a classifier that keys on name+colors+type+legality. Bulk download = no rate limit; REST fallback <=10 req/s with a 50-100ms delay; required headers User-Agent + Accept: application/json (edh-engine already sets these)."
  - "legalities.legacy is one of {legal, banned, not_legal, restricted} — but RULES/legality validation should treat Legacy as a BLACKLIST (per legacy-foundations.md): trust a version-stamped banned-list set, not Scryfall's `legacy` flag alone (Scryfall lags B&R announcements by hours-to-days)."
  - "REUSE VERDICT: EXTEND, don't fork. edh-engine/ingestion/scryfall.py transfers wholesale (bulk download, name index, batch /cards/collection fallback). Add: (a) load the FULL oracle pool not a meta-scoped subset — Legacy's card pool dwarfs a cEDH meta's ~3,148 cards (~30k+ oracle IDs), so resolve-by-name against the whole index, don't pre-resolve a fixed pool; (b) a Card model with derived colors_of_lands/colors_of_nonlands + Legacy staple_role/is_free_spell tags; (c) a colors-of-deck helper implementing GetColors."
  - "staple_role / is_free_spell / mana-base tags are NOT in Scryfall — derive them: is_free_spell from oracle_text alt-cost patterns ('without paying its mana cost', 'exile ... from your hand', 'rather than pay'); land mana-base tags from type_line ('Land'), produced_mana, oracle_text ('enters tapped', 'Search your library ... land'); staple_role from a curated name->role table seeded by legacy-foundations.md's staples table."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/prior-art-scan.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-foundations.md, relationship: depends-on}
---

# Brief: Scryfall Card-Data Contract for the Legacy Archetype Classifier

## Purpose
The archetype classifier (a Python port of Badaro's MTGOArchetypeParser + MTGOFormatData) needs
card reference data for two jobs: (1) compute a deck's **colors** so it can emit color-prefixed
archetype names ("Dimir Tempo", "Mono-Red Prison", "5C Zenith"), and (2) **normalize decklist card
names** to canonical card objects that the rule matcher's `Cards` arrays resolve against. This brief
defines that card-data contract and states whether edh-engine's `ingestion/scryfall.py` can be reused.

Scope boundary (see cross-references at end): **INGEST** owns the decklist JSON source; this brief
owns the card reference data those names resolve *to*. **RULES** owns the rule schema and references
the resolved Cards; this brief owns *how* a name becomes a card object + its colors. **CLASSIFY**
owns the matcher; this brief is its card/color input contract. **PORT** owns the Python design; this
brief hands them the Card model.

---

## 1. How MTGOArchetypeParser derives deck colors (the load-bearing finding)

The intuition "deck colors = `color_identity` of the cards" is **wrong** for this classifier, and so
is "deck colors = `colors` of all cards." The authoritative algorithm is
`ArchetypeAnalyzer.GetColors` ([source](https://raw.githubusercontent.com/Badaro/MTGOArchetypeParser/master/MTGOArchetypeParser/Data/ArchetypeAnalyzer.cs), lines 84-127):

```
colorsInLands[c]    += count   for each color c of each LAND card (from format.Lands map)
colorsInNonLands[c] += count   for each color c of each NONLAND card (from format.NonLands map)

finalColor = ""
for c in [W,U,B,R,G]:
    if colorsInLands[c] > 0  AND  colorsInNonLands[c] > 0:   # INTERSECTION
        finalColor += c
return finalColor or "C"
```

The deck's color is the **intersection** of (colors its *lands* can produce) and (colors its
*nonland* cards cost). A color is in the deck name **only if it appears in both sets**. This elegantly
filters splashes that have a source but no payoff (or a payoff but no source) and excludes colorless
fixing. The result maps to an `ArchetypeColor` enum (C, W, U, B, R, G, WU=Azorius, UB=Dimir, …,
WUBRG) — the prefix CLASSIFY prepends to the archetype name.

**Badaro's data source for those colors:** a hand-curated `card_colors.json` (auto-generated from
MTGJSON, split into `Lands` and `NonLands` properties) plus a `color_overrides.json` whose stated
main use is "multi-color lands strongly associated with 5C decks"
([MTGOFormatData](https://github.com/Badaro/MTGOFormatData)). The Python port should **replace this
curated file with a Scryfall-derived computation** (single source of truth — see PRINCIPLES.md),
because Scryfall already carries the needed fields:

| GetColors input | Scryfall field | Why (verified live 2026-05-29) |
|---|---|---|
| Land's colors | **`produced_mana`** minus `{C}` | Underground Sea: `colors=[]`, `color_identity=[B,U]`, **`produced_mana=[B,U]`**. A land's `colors` is empty; `color_identity` would work for duals but mis-handles colorless utility lands and is conceptually wrong. `produced_mana` is exactly "what colors this land can make." Wasteland: `produced_mana=[C]` → contributes nothing (correct). |
| Nonland card's colors | **`colors`** | Murktide Regent (delve dragon): `colors=[U]`. Force of Will: `colors=[U]`. This is the mana-cost colors. **Not `color_identity`** — that adds rules-text/hybrid symbols and would over-color a deck. |

So the Python `compute_deck_colors(deck)` is: collect `produced_mana - {C}` over lands, collect
`colors` over nonlands, intersect per WUBRG, format as the enum. Lands are identified by
`'Land' in type_line` (see §5).

> Why not `color_identity` anywhere: `color_identity` is the **Commander** construct (mana cost +
> color indicator + every mana symbol in rules text + color-setting CDAs). It would, e.g., paint a
> deck running a card with an off-color activated-ability symbol as that color even with no source
> and no intent. Archetype naming wants *cast intent* (`colors`) gated by *mana availability*
> (`produced_mana`). edh-engine correctly uses `color_identity` for cEDH; **legacy-engine must not.**
> ([Scryfall colors docs](https://scryfall.com/docs/api/colors), [Color identity, MTG Wiki](https://mtg.fandom.com/wiki/Color_identity).)

Other fields the matcher and downstream stages key on: `name` (rule matching + dedup), `type_line`
(land detection, creature/instant counts), `mana_cost` / `cmc` (curve, free-spell heuristics),
`layout` (face handling — §2), `oracle_text` (tag derivation — §5), `legalities.legacy` (§3).

---

## 2. Card-name normalization & the name→card index

Decklist names (MTGO `.txt`, Moxfield, MTGGoldfish exports) must resolve to one Scryfall object.
The hazards, all verified live:

- **Split cards** (`layout: "split"`, e.g. *Fire // Ice*): name = `"Fire // Ice"`; top-level
  `colors=[R,U]`, `mana_cost="{1}{R} // {1}{U}"`, `type_line="Instant // Instant"`. Per-face
  `card_faces[].colors` is **null** — so for color computation use the **top-level** `colors`.
- **Adventure** (`layout: "adventure"`, e.g. *Brazen Borrower // Petty Theft*): name =
  `"Brazen Borrower // Petty Theft"`; top-level `colors=[U]`; `card_faces[].mana_cost` is populated,
  `card_faces[].colors` null. MTGO decklists usually list just `"Brazen Borrower"`.
- **DFC / MDFC** (`layout: "transform"` / `"modal_dfc"`): top-level `mana_cost` is null; per-face
  `card_faces[].colors` and `card_faces[].mana_cost` are populated. Top-level `colors` still carries
  the combined color set, so **always prefer top-level `colors` for the color computation** and fall
  back to merging `card_faces[].colors` only if top-level is empty.
- **Unicode**: curly apostrophes (`'` U+2019, e.g. *Urza's Saga*, *Minsc & Boo*) and accents
  (*Lim-Dûl's Vault*, *Troll of Khazad-dûm*). edh-engine already fixes the curly apostrophe; add NFC
  accent handling so MTGO's ASCII-ish names match.

**Index construction** (extends edh-engine's `load_card_index`):
1. Key on the full `name` (`"Fire // Ice"`).
2. **Also key on each face name** for `" // "` names AND for `card_faces[].name` (so `"Fire"`,
   `"Ice"`, `"Brazen Borrower"` all resolve). edh-engine splits on `" // "` for split/DFC but does
   not index `card_faces[].name` for cards whose top-level name lacks `//` — add that.
3. Apply `normalize_name()` (curly→straight apostrophe, trim) to keys and lookups; extend with accent
   normalization.
4. On collision (two cards claim a face name), prefer the full-card entry; never overwrite a full
   name with a face alias (edh-engine's `if face_name not in index` guard is right).

This single index is the shared resolution surface for both INGEST's decklist parser and CLASSIFY's
rule matcher. Scryfall name fields: `name` (Oracle name), `card_faces[].name` (per face),
`printed_name` (localized — ignore; oracle_cards is English/canonical).
([Card Objects](https://scryfall.com/docs/api/cards).)

---

## 3. Scryfall access (confirm bulk file, limits, headers, cadence)

- **Bulk file = `oracle_cards`** — "one Scryfall card object for each Oracle ID." Verified live
  2026-05-29: ~173 MB, `updated_at` 2026-05-29T21:05Z. This is the correct file: the classifier keys
  on Oracle-level facts (name, colors, type, oracle_text, legality), not on specific printings, so one
  canonical object per card is exactly right. `default_cards` (~539 MB, every English printing) and
  `all_cards` (~2.5 GB, all languages) are unnecessary bloat for this use.
- **Cadence**: bulk files regenerate roughly **daily** (the live `updated_at` was ~hours old).
  edh-engine's `updated_at`-comparison skip is the right refresh trigger; a weekly cron suffices for a
  classifier, but refresh after each B&R / set release.
- **Rate limits**: bulk downloads have **no rate limit** (CDN-served). REST fallback (`/cards/named`,
  `POST /cards/collection`) wants **≤10 requests/second**; Scryfall asks for a **50-100 ms delay**
  between requests. (Search endpoints are slower; not needed here.) edh-engine's `SCRYFALL_API_DELAY=0.1`
  (100 ms) is conservative-correct.
- **Required headers**: `User-Agent` (identifying your app — Scryfall returns 403 to generic agents;
  this is why automated doc-page fetches fail but the JSON API works with a UA) and
  `Accept: application/json`. edh-engine sets `User-Agent: EDHEngine/0.1.0`; legacy-engine should use
  its own UA, e.g. `legacy-engine/0.1`. Add the `Accept` header explicitly (edh-engine relies on the
  default; making it explicit is harmless and matches Scryfall's guidance).
- **Batch fallback**: `POST /cards/collection` resolves up to **75 identifiers** per request — edh's
  `_batch_lookup` already does this. For Legacy, the full oracle bulk will resolve essentially every
  name locally, so the API fallback fires only for brand-new cards between bulk refreshes.

([Bulk Data Files](https://scryfall.com/docs/api/bulk-data), [Bulk Data Updates / cadence blog](https://scryfall.com/blog/updates-to-bulk-data-and-cards-deprecation-notice-217), live `https://api.scryfall.com/bulk-data`.)

---

## 4. Reuse assessment — edh-engine's `ingestion/scryfall.py`

**Verdict: EXTEND, do not fork.** `edh_engine/ingestion/scryfall.py` is a clean fit and most of it
transfers verbatim:

| Capability | Status for legacy-engine |
|---|---|
| `download_bulk_data(force)` with `updated_at` freshness skip | **Reuse as-is.** Same bulk type (`oracle_cards`). |
| `load_card_index()` name→card dict | **Reuse + extend** (index `card_faces[].name`, add accent normalization — §2). |
| `_batch_lookup()` (`POST /cards/collection`, 75/req, delay) | **Reuse as-is.** |
| `normalize_name()` | **Reuse + extend** (accents). |
| `resolve_card_pool(card_names)` → fixed pool dict | **Change the contract.** See below. |
| Moxfield-metadata-key filtering | Reuse if Moxfield is an INGEST source; otherwise drop. |

**The one real divergence — pool scope (call this out for PORT/INGEST):** edh-engine resolves a
**meta-scoped subset** — the ~3,148 distinct cards that appear across the cEDH metagame's decklists —
and persists it as `card_pool.json`. Legacy's card pool is the **entire eternal pool** (every set ever
printed minus the ban list — the second-largest in Magic, a superset of Modern; ~30k+ Oracle IDs).
Two implications:

1. **Index the whole oracle bulk; don't pre-resolve a fixed pool.** Keep the full name index in memory
   (oracle_cards is ~173 MB JSON; the name→object index is the practical working set) and resolve
   names on demand. A persisted `card_pool.json` of "cards seen in decklists" is still useful as an
   ingest-time cache/manifest, but it must not be the *authority* — a new tournament can introduce any
   legal card, so the resolver must fall back to the full index, then to the API.
2. **Memory/perf**: holding the full oracle set is fine for a CLI (hundreds of MB), but PORT may want a
   lazy/streamed index or a slimmed projection (keep only the fields in §6) to cut footprint. Flag for
   PORT.

Net: copy the module, rename the UA, broaden the index, swap the fixed-pool resolver for a
whole-index resolver, and add the Card model + tagging pass (§5–6).

---

## 5. Legacy-specific card tags (derive from Scryfall; not native fields)

`staple_role`, `is_free_spell`, and the mana-base tags from `legacy-foundations.md` §3 are **not**
Scryfall fields. Derive them in a tagging pass over resolved cards (reference, don't duplicate, the
foundations staples table):

- **`is_free_spell: bool`** — the single most analytically valuable Legacy tag (foundations §3).
  Heuristic on `oracle_text` (case-insensitive): alternative-cost phrases — `"without paying its mana
  cost"`, `"rather than pay"`, `"you may exile a"` + `"from your hand"` + `"rather than pay this
  spell's mana cost"` (Force of Will / Force of Negation / Force of Vigor pattern), `"if you control"`
  + `"return"` + `"to its owner's hand"` (Daze), pitch/Phyrexian-mana. Seed-and-verify against the
  foundations free-interaction list (Force of Will, Force of Negation, Daze, Force of Vigor,
  Pyroblast). Keep a curated allow/deny override for false positives.
- **`staple_role: str | None`** — enum aligned to foundations' staple table (`dual_land`,
  `fetchland`, `land_denial`, `fast_mana`, `free_interaction`, `cantrip`, `discard`, `engine`,
  `combo_enabler`, `lock_piece`). Best sourced from a **curated name→role table** seeded directly from
  the foundations staples table, not pattern-matched from oracle text (these are meta-judgment
  categories). Lives as data the tagging pass joins onto the Card.
- **Mana-base tags** (lands only; gate on `'Land' in type_line`):
  - `produces_colors: list[str]` ← `produced_mana` minus `{C}`.
  - `enters_tapped: bool` ← `"enters tapped"` / `"enters the battlefield tapped"` in `oracle_text`.
  - `is_fetchland: bool` ← `oracle_text` has `"Search your library for a"` + land-type words +
    `"put it onto the battlefield"` + a life/pay cost (fetch pattern).
  - `is_original_dual: bool` ← `type_line` has two basic land types AND no `enters_tapped` AND no
    activation cost (the ABU dual pattern); or curated set.
  - `is_fast_mana_land` / `is_denial_land` ← curated (Ancient Tomb, City of Traitors / Wasteland,
    Rishadan Port) from foundations.
  - `is_fetchable_by: list[str]` ← derivable from `type_line` land subtypes, but curated is safer.

Pattern-derived tags should be cheap and re-runnable on each bulk refresh; curated tags live in a
small versioned data file. (Single Source of Truth — PRINCIPLES.md.)

---

## 6. The Card Pydantic model (edh-engine idiom)

edh-engine's `CardEntry` is a `@dataclass` of deck-level role flags (goldfish.py: `name`, `role`,
`cmc`, `type_line`, `oracle_text`, `produces`, `enters_tapped`, `is_fetch`…). The legacy classifier's
Card is a *reference-data* object (one per Oracle ID, populated from Scryfall + the tagging pass),
distinct from a deck-entry. Sketch (Pydantic, the project's stated model layer):

```python
class Card(BaseModel):
    # --- identity ---
    name: str                      # Scryfall `name` (Oracle, canonical; "Fire // Ice")
    oracle_id: str                 # stable key across printings
    face_names: list[str] = []     # card_faces[].name, for the resolver index
    layout: str                    # normal|split|transform|modal_dfc|adventure|...

    # --- color computation inputs (see §1) ---
    colors: list[str] = []         # Scryfall `colors`  -> NONLAND contribution
    produced_mana: list[str] = []  # Scryfall `produced_mana` -> LAND contribution (minus C)
    color_identity: list[str] = [] # carried for reference ONLY; not used for archetype naming

    # --- cost / type ---
    mana_cost: str | None = None   # top-level (null for DFC); "{1}{R} // {1}{U}" for split
    cmc: float = 0.0
    type_line: str = ""
    oracle_text: str = ""

    # --- type flags (derived from type_line) ---
    is_land: bool = False
    is_creature: bool = False
    is_instant: bool = False
    is_artifact: bool = False

    # --- legality (see §3) ---
    legacy_legality: str = "legal"  # legal|banned|not_legal|restricted (Scryfall view)

    # --- Legacy-specific tags (derived; see §5) ---
    staple_role: str | None = None
    is_free_spell: bool = False
    # mana-base (lands only)
    enters_tapped: bool = False
    is_fetchland: bool = False
    is_original_dual: bool = False
    is_fast_mana_land: bool = False
    is_denial_land: bool = False
    is_fetchable_by: list[str] = []
```

Plus a module-level helper the classifier calls:

```python
def compute_deck_colors(cards_with_counts) -> str:
    """MTGOArchetypeParser GetColors: intersection of land produced_mana and nonland colors.
    Returns the WUBRG-ordered enum string ('UB', 'WUBRG', or 'C')."""
```

Legality nuance for RULES/legality validation: the `legacy_legality` field reflects Scryfall's view,
which **lags B&R announcements**. Per `legacy-foundations.md` §3, treat Legacy as a **blacklist** —
validate against a version-stamped `banned_cards` set (with `banned_date` + `ban_reason`) so a deck
can be checked against the legality snapshot at a historical tournament date. Don't make Scryfall's
`legacy` flag the sole authority.

---

## Suggested cross-references to sibling subdomains

- **INGEST (decklist JSON):** Decklist card names arrive from your source; they resolve against the
  name index defined in §2 (full name + face names + normalization). Tell me your exact name format
  (MTGO `//` convention? "Brazen Borrower" short form?) so the index keys cover it. The persisted
  `card_pool.json` becomes an ingest-time cache, not the authority (§4).
- **RULES (rule schema):** Your rule `Cards`/`InOneOrMoreOf` arrays reference card *names*; this brief
  owns how those names resolve to objects + colors. The color enum your color-prefix rules consume is
  produced by `compute_deck_colors` (§1, §6). Legality should use a version-stamped banned set, not
  Scryfall's `legacy` flag (§3, §6).
- **CLASSIFY (the matcher):** Your color prefix = `ArchetypeColor` enum from §1's intersection
  algorithm — wire it to `compute_deck_colors`, not to Scryfall `colors`/`color_identity`. The Card
  fields you key on (name, type_line, colors, produced_mana) are in §6.
- **PORT (Python design):** Card model + `compute_deck_colors` are in §6. The reuse delta from
  edh-engine is in §4 — broaden the index to the whole oracle pool (don't pre-resolve a fixed pool),
  and decide on lazy/slimmed indexing for the ~173 MB bulk. Tagging pass is §5.
- **PRIOR-ART:** MTGOArchetypeParser `ArchetypeAnalyzer.GetColors` and MTGOFormatData
  `card_colors.json` / `color_overrides.json` are the upstream color logic this brief ports; the
  Python port replaces the curated color files with Scryfall-derived computation.
