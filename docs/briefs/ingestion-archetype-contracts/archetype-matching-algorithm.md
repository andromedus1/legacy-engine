---
description: The exact C# matching algorithm of Badaro/MTGOArchetypeParser — how a decklist + rule set produces an archetype label — specified for a faithful Python reimplementation of legacy-engine's archetype/ module.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Reverse-engineers the CLASSIFY stage: the archived Badaro/MTGOArchetypeParser C# engine that
  consumes MTGOFormatData rules + a decklist and emits an archetype label. The core is a single
  static method, ArchetypeAnalyzer.Detect, that AND-tests every specific archetype's conditions,
  collects ALL matches (no tie-break by default — it emits a "Conflict(...)" label), nests variant
  resolution inside the matched parent, falls back to a most-shared-cards "generic/fallback" pile
  with a 10% similarity floor, and computes colors from the intersection of land-color and
  nonland-color evidence. Card matching is exact case-sensitive string equality on MTGO CardName.
  Includes Python-ready pseudocode and the full input/output contract.
key_findings:
  - "Core is one method — ArchetypeAnalyzer.Detect(mainboard, sideboard, format, minSimilarity=0.1, conflictMode=None). It tests EVERY specific archetype; a rule matches only if ALL its conditions pass (logical AND over conditions, short-circuit on first failure). All matches are collected, not just the first."
  - "There is NO built-in tie-break by default (ConflictSolvingMode.None): if 2+ archetypes match, the App emits the literal string Conflict(NameA,NameB). Only with PreferSimpler does it pick the match with the FEWEST conditions (GetComplexity = Conditions.Length, archetype + variant summed). 'Specificity' = condition count, lower wins under PreferSimpler."
  - "Variants are nested: a variant is only tested if its parent archetype already matched (variant conditions are an ADDITIONAL AND-block). Every passing variant produces its own ArchetypeMatch; if none pass, the bare parent matches. A parent with N passing variants yields N matches (a conflict)."
  - "Fallback only fires when zero specific archetypes match. It scores each Generic/Fallback by SUM of Count of distinct deck cards present in its CommonCards, picks max (ties broken by SHORTEST CommonCards list), and accepts only if similarity (max_weight / total_card_count) > minSimilarity (0.1). Otherwise the App labels the deck 'Unknown'."
  - "Colors are computed by intersection of two independent tallies: a color is included ONLY IF it appears in at least one LAND (per Lands map) AND at least one NONLAND (per NonLands map), across main+sideboard. Result is a fixed ArchetypeColor enum (C, mono, guild, shard/wedge, 4c, WUBRG). Cards absent from both maps contribute nothing."
  - "Card-name matching is exact, case-sensitive C# string equality (c.Name == rule card). No normalization, no fuzzy match, no split/DFC/adventure '//' handling in the engine — names must already be in MTGO canonical form upstream. This is a hard contract on the INGEST/CARD-CONTRACT boundary, not the algorithm."
  - "Companion is detected separately (sideboard-only scan against a hardcoded 10-card map) and returned alongside, NOT folded into archetype matching. Empty/partial lists do not crash: empty mainboard/sideboard arrays simply fail membership tests → typically Unknown."
  - "Output contract: ArchetypeResult { Matches[], Color, Companion? }; the App flattens to RecordArchetype { Archetype:string, Color:string, Companion:string } where Archetype is the variant name if a variant matched, else the parent name, color-prefixed iff IncludeColorInName, PascalCase split into words."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md, relationship: parallel-to}
---

# Brief: The Archetype-Matching Algorithm (Badaro/MTGOArchetypeParser)

## Purpose & scope
legacy-engine maps deck archetypes onto raw tournament decklists by **wrapping Badaro's MTGOFormatData
rules**. The rules are data; the **algorithm** that consumes them lives in the separate, now-archived
[Badaro/MTGOArchetypeParser](https://github.com/Badaro/MTGOArchetypeParser) C# repo (archived 2025-09-24,
read-only). This brief specifies that algorithm in enough detail to **reimplement it in Python** for the
`archetype/` module. All file paths below are within that repo unless noted.

This is the **CLASSIFY** stage. Sibling scope (avoided here): INGEST (fbettega cache), RULES (the rule
DATA schema), PORT (vendor-vs-rewrite engineering), CARD-CONTRACT (Scryfall fields), SERVE/OPS, PRIOR-ART.
Format context (tiers, archetypes) is in `docs/briefs/legacy-metagame.md` — not duplicated.

The entire engine is **~210 lines in one file**: `MTGOArchetypeParser/Data/ArchetypeAnalyzer.cs`. It is a
pure, static, deterministic function. Porting it is low-risk; the subtlety is in the edge cases below.

---

## 1. The core matching procedure

Entry point — `ArchetypeAnalyzer.Detect` (`ArchetypeAnalyzer.cs:25`):

```csharp
public static ArchetypeResult Detect(Card[] mainboardCards, Card[] sideboardCards,
    ArchetypeFormat format, double minSimiliarity = 0.1,
    ConflictSolvingMode conflictSolvingMode = ConflictSolvingMode.None)
```

The procedure, in order:

1. **Partition the rule set** (lines 31–32). From `format.Archetypes` it pulls:
   - `specificArchetypes` = items that are `ArchetypeSpecific` **but not** `ArchetypeVariant` (top-level
     rule archetypes; variants are reached *through* their parent, not iterated here).
   - `genericArchetypes` = items that are `ArchetypeGeneric` (the fallback "piles").
   (Type comes from which folder the JSON loaded from — see §8 loader.)
2. **Compute companion** (line 34) and **compute color** (line 35) once, up front (§5, §7).
3. **Test every specific archetype** (lines 38–56). For each, call `Test(...)`. If it matches:
   - Iterate its `Variants`; **each passing variant** adds an `ArchetypeMatch{ Archetype=parent,
     Variant=variant, Similarity=1 }`.
   - If **no** variant passed, add `ArchetypeMatch{ Archetype=parent, Variant=null, Similarity=1 }`.
4. **If `results.Count == 0`** (lines 58–62): run the **fallback** path (`GetBestGenericArchetype`) and
   accept its match only if `Similarity > minSimiliarity`.
5. **Else** (lines 63–69): if more than one match **and** `conflictMode == PreferSimpler`, reduce to the
   single simplest. Otherwise **leave all matches** in the result (a conflict).
6. Return `ArchetypeResult{ Matches[], Color, Companion }` (line 71).

**"A rule matches" = ALL conditions pass.** `Test` (`ArchetypeAnalyzer.cs:129`) loops the archetype's
`Conditions` and `return false` on the **first** unsatisfied one; only if the loop completes does it
`return true`. This is a hard logical-AND with short-circuit. A condition with an empty/null `Cards`
array is **skipped** (line 133), not failed — so a broken condition silently weakens a rule.

### The 12 condition types
`ArchetypeConditionType.cs` + the `switch` in `Test` (lines 135–175). Each condition carries a
`Cards: string[]`. Behavior verified against `ConditionTests.cs`:

| Type | Meaning (fails the rule unless…) | Uses |
|---|---|---|
| `InMainboard` | `Cards[0]` present in mainboard | `Cards[0]` only |
| `InSideboard` | `Cards[0]` present in sideboard | `Cards[0]` only |
| `InMainOrSideboard` | `Cards[0]` present in either | `Cards[0]` only |
| `OneOrMoreInMainboard` | ≥1 of `Cards` present in mainboard | whole list |
| `OneOrMoreInSideboard` | ≥1 of `Cards` present in sideboard | whole list |
| `OneOrMoreInMainOrSideboard` | ≥1 of `Cards` in main OR ≥1 in side | whole list |
| `TwoOrMoreInMainboard` | ≥2 **distinct** `Cards` names in mainboard | whole list |
| `TwoOrMoreInSideboard` | ≥2 distinct `Cards` names in sideboard | whole list |
| `TwoOrMoreInMainOrSideboard` | (main count + side count) ≥ 2 | whole list |
| `DoesNotContain` | `Cards[0]` absent from both | `Cards[0]` only |
| `DoesNotContainMainboard` | `Cards[0]` absent from mainboard | `Cards[0]` only |
| `DoesNotContainSideboard` | `Cards[0]` absent from sideboard | `Cards[0]` only |

**Counting nuance.** `TwoOrMore*` counts **distinct deck entries whose Name is in `Cards`**, i.e. it
counts how many *different* listed cards appear (`mainboardCards.Where(c => Cards.Contains(c.Name)).Count()`),
**not** how many physical copies. `TwoOrMoreInMainOrSideboard` sums the main-entry count and side-entry
count, so the same card present in both main and side counts twice (confirmed by the test on line 183–188:
Card 1 main + Card 4 side → succeeds). `Count` (copies) is **never** consulted by conditions — only by
color tallying and fallback weighting.

---

## 2. Precedence / specificity / tie-breaking

**Default (`ConflictSolvingMode.None`): there is no winner-picking.** Every matching archetype stays in
`Matches[]`. The App layer then renders the conflict explicitly (`RecordLoader.GetArchetype`,
`RecordLoader.cs:139-140`):

```csharp
if (detectionResult.Matches.Length == 1) archetypeID = GetArchetype(matches.First(), color);
if (detectionResult.Matches.Length > 1)
    archetypeID = $"Conflict({String.Join(",", matches.Select(m => GetArchetype(m, color)))})";
```

So an ambiguous deck is labeled, literally, `Conflict(Burn,Boros Aggro)`. This is a **deliberate
non-resolution** — Badaro's rule-authoring workflow treats conflicts as a signal to tighten rules, not as
something the engine should silently resolve.

**Optional (`ConflictSolvingMode.PreferSimpler`)** (lines 65–68): when `Matches.Count > 1`, order by
**complexity ascending** and take the first:

```csharp
results = results.OrderBy(r => r.Archetype.GetComplexity()
    + (r.Variant != null ? r.Variant.GetComplexity() : 0)).Take(1).ToList();
```

`ArchetypeSpecific.GetComplexity()` returns `Conditions.Length` (`Archetype.cs:120-123`). So **specificity
= number of conditions**, and *fewer* conditions wins. (Note: counter-intuitive — "simpler" = fewer rules,
i.e. the *more general* archetype is preferred when both match. This is `OrderBy` so it is a stable sort;
on a complexity tie the **iteration order** of the archetype list wins, which derives from
`Directory.GetFiles` ordering — effectively filename/OS order. Not a documented guarantee.)
`ConflictSolvingMode` has exactly two values: `None`, `PreferSimpler` (`ConflictSolvingMode.cs`).

---

## 3. Variant resolution (nested)

Variants are **strictly nested under their matched parent** (`ArchetypeAnalyzer.cs:42-54`):

```csharp
if (Test(..., archetype)) {                  // parent matched
    bool isVariant = false;
    if (archetype.Variants != null)
        foreach (ArchetypeSpecific variant in archetype.Variants)
            if (Test(..., variant)) {        // variant tested ONLY because parent matched
                isVariant = true;
                results.Add(new ArchetypeMatch { Archetype=archetype, Variant=variant, Similarity=1 });
            }
    if (!isVariant) results.Add(new ArchetypeMatch { Archetype=archetype, Variant=null, Similarity=1 });
}
```

Key facts for the port:
- A variant's conditions are an **additional** AND-block evaluated against the full deck (not against the
  parent's conditions — they re-scan the same main/side arrays). The "core + delta" semantics come purely
  from how rule authors write them; the engine just runs both condition lists.
- **Multiple variants can match the same parent** → multiple `ArchetypeMatch` entries → a conflict (handled
  by §2). The engine does **not** pick "best variant."
- `ArchetypeVariant : ArchetypeSpecific` (`Archetype.cs:126`) — a variant is structurally identical to an
  archetype (it can even nest its own `Variants` property, though that is not exercised in practice).
- The final displayed name uses the **variant's** name when a variant matched, else the parent's
  (`RecordLoader.cs:150-158`).

---

## 4. Fallback logic (generic piles + "Unknown")

`GetBestGenericArchetype` (`ArchetypeAnalyzer.cs:181-208`) runs **only when no specific archetype matched**:

```csharp
foreach (ArchetypeGeneric g in genericArchetypes) {
    weights[g] = 0;
    foreach (var card in mainboardCards.Concat(sideboardCards).Distinct())   // distinct by reference!
        if (g.CommonCards.Contains(card.Name)) weights[g] += card.Count;     // weight by COPIES
}
if (weights.All(v => v == 0)) return null;                                    // no fallback shares anything
int max = weights.Max(v => v.Value);
var best = weights.Where(v => v.Value == max).OrderBy(k => k.Key.CommonCards.Length).First();  // ties → shortest pile
return new ArchetypeMatch {
    Archetype = best.Key, Variant = null,
    Similarity = (double)max / (mainboardCards.Length + sideboardCards.Length)   // weight / #entries
};
```

Then in `Detect` (line 61): `if (genericArchetype != null && genericArchetype.Similarity > minSimiliarity)`
add it — `minSimiliarity` defaults to **0.1** (the "≥10% matching cards" rule from the README; strictly
`>`, not `>=`).

Pin down the math for the port:
- **Weight = sum of `Count` (copies)** of distinct deck entries whose Name is in the pile's `CommonCards`.
- **Similarity denominator = `mainboardCards.Length + sideboardCards.Length`** — the number of *distinct
  deck entries* (rows), **not** total card count. A 75-row list of 1-ofs and a 15-row list of 4-ofs scale
  very differently. This is arguably a quirk to preserve for fidelity.
- **Tie-break**: highest weight wins; on a weight tie, the pile with the **fewest** `CommonCards` wins
  (most specific pile). On a further tie, dictionary/insertion order (filename order).
- `.Distinct()` on line 188 dedupes `Card` objects by reference, so it is effectively a no-op (each entry
  is a distinct object); treat it as "iterate all entries."

**"Unknown"** is produced in the App, not the engine: if `Matches.Length == 0` after Detect (no specific
match and fallback rejected/empty), `archetypeID` stays `"Unknown"` (`RecordLoader.cs:137`).

---

## 5. Color computation

`GetColors` (`ArchetypeAnalyzer.cs:84-127`). Inputs: the deck (main+side) and two reference maps from the
format — `Lands: Dict<string,ArchetypeColor>` and `NonLands: Dict<string,ArchetypeColor>` (loaded from
`card_colors.json` + per-format `color_overrides.json`, §8). **It is NOT card color identity from
Scryfall** — it is a curated card→color lookup, split into a lands table and a nonlands table.

Algorithm:
1. Init two `{W,U,B,R,G}→int` tallies: `colorsInLands`, `colorsInNonLands`.
2. For each deck entry (main ∪ side): if its Name is a key in `Lands`, add its `Count` to each color letter
   in `Lands[name]`; if its Name is in `NonLands`, add its `Count` to each color letter in `NonLands[name]`.
   (A card can be in both maps; both tallies update.)
3. **A color is in the final identity ONLY IF it has >0 in lands AND >0 in nonlands** (lines 120–124):
   ```csharp
   if (colorsInLands['W'] > 0 && colorsInNonLands['W'] > 0) finalColor += "W"; // …repeat U,B,R,G
   ```
4. Parse the assembled string (e.g. `"UB"`) into the `ArchetypeColor` enum; empty → `ArchetypeColor.C`
   (colorless).

**Consequences to preserve:** a color produced only by spells (no colored land/dual that taps for it) is
dropped, and vice-versa. This is why off-color splashes and basic-light manabases sometimes lose a color.
The enum has a **fixed canonical ordering** WUBRG (`ArchetypeColor.cs`), so `"BU"` can never form — the
build order guarantees WUBRG sequence. The enum enumerates all 31 non-empty combos + `C` and maps them to
guild/shard/wedge/4c names in `GetColorName` (`Archetype.cs:43-112`).

---

## 6. Card-name handling

- **Matching is exact, case-sensitive, ordinal `string ==`** everywhere: conditions
  (`c.Name == condition.Cards[0]`, `condition.Cards.Contains(c.Name)`), companion (`c.Name == key`), color
  (`Dictionary.ContainsKey(card.Name)`), fallback (`CommonCards.Contains(card.Name)`). **No normalization,
  trimming, case-folding, or fuzzy matching exists in the engine.**
- **Split / DFC / adventure / MDFC names are NOT handled by the engine.** There is no `//` logic, no
  front-face fallback. The name in the deck must already equal the name in the rules. In MTGO data the
  `CardName` field is the canonical MTGO form (full `"A // B"` for splits, front-face for DFCs), and rule
  authors hand-write names to match that exact form. **For the Python port this is a contract on INGEST /
  CARD-CONTRACT**: whatever feeds `Card.Name` must use the same canonical naming as the rule files, or
  matches silently fail. (The MTGOFormatData README documents the rule *format* but gives no `//`
  convention — confirming the engine offloads naming entirely to the data.)
- A name appearing 0 times simply makes membership tests false; there is no error.

---

## 7. Edge cases

- **Rogue / unmatched deck**: no specific match + fallback rejected (or no piles) → `Matches=[]` →
  App label `"Unknown"`. Color and companion are still computed and returned.
- **Empty / partial lists**: empty `mainboardCards`/`sideboardCards` arrays are valid; all membership tests
  return false, fallback denominator could be `0` → **division producing `NaN`/`Infinity`** if a list is
  fully empty but the other has matches; in practice both are populated. A fully empty deck → all-zero
  weights → fallback returns null → `"Unknown"`. The Python port should guard the
  `max / (len(main)+len(side))` division against zero.
- **Ties**: covered in §2 (specific) and §4 (fallback). Default mode surfaces specific-archetype ties as
  `Conflict(...)`; fallback ties never surface (always reduced to one).
- **Companion** (`GetCompanion`, `ArchetypeAnalyzer.cs:74-82`): scans **sideboard only** against a
  hardcoded 10-entry map (Gyruda, Jegantha, Kaheera, Keruga, Lurrus, Lutri, Obosh, Umori, Yorion, Zirda).
  **Last match wins** (no break) — if two companions are in the SB, the later iteration overwrites. Returned
  as a separate field; **never affects archetype matching**. For Legacy this is largely vestigial (companions
  rare) but must be ported for output-shape fidelity.
- **Sideboard role**: sideboard cards participate in color, companion, fallback weighting, and any
  `*Sideboard`/`*MainOrSideboard`/`DoesNotContain*` condition. Pure-mainboard conditions ignore them.
- **Broken condition** (empty `Cards`): skipped, not failed (§1) — a rule with only broken conditions
  matches *everything* (vacuous truth), a real footgun to replicate or deliberately reject.

---

## 8. Inputs / outputs contract

### Inputs
- **`Card`** (`Model/Card.cs`): `{ Name: string; Count: int }`. The engine's atomic unit. Built by the App
  from the cache's `DeckItem { Count, CardName }` (`Data/Model/DeckItem.cs`) via
  `new Card { Name = i.Card, Count = i.Count }` (`RecordLoader.cs:133`).
- **Deck** (cache shape, `Data/Model/Deck.cs`): `{ Date, Result, Player, AnchorUri, Mainboard: DeckItem[],
  Sideboard: DeckItem[] }`. The engine receives only the two `Card[]` arrays, not the Deck wrapper.
- **`ArchetypeFormat`** (`Model/ArchetypeFormat.cs`): `{ Archetypes: Archetype[]; Metas: ArchetypeMeta[];
  Lands: Dict<string,ArchetypeColor>; NonLands: Dict<string,ArchetypeColor> }`.
  - **`Archetype`** (abstract, `Model/Archetype.cs`): `{ Name: string; IncludeColorInName: bool }`.
    - `ArchetypeSpecific : Archetype` adds `{ Conditions: ArchetypeCondition[]; Variants: ArchetypeVariant[] }`.
    - `ArchetypeVariant : ArchetypeSpecific` (no new fields).
    - `ArchetypeGeneric : Archetype` adds `{ CommonCards: string[] }` (the fallback pile).
  - **`ArchetypeCondition`** (`Model/ArchetypeCondition.cs`): `{ Type: ArchetypeConditionType; Cards: string[] }`.
- **Loader** (`Formats.FromJson/Loader.cs`): `Archetypes/*.json` → `ArchetypeSpecific`,
  `Fallbacks/*.json` → `ArchetypeGeneric`; rejects archetype files with no conditions and fallback files
  with no `CommonCards`. Colors = `card_colors.json` (auto-generated from MTGJSON) **overlaid by**
  per-format `color_overrides.json` (override wins). `metas.json` → date-keyed meta windows (used only for
  bucketing output, not matching).

### Outputs
- **`ArchetypeResult`** (`Model/ArchetypeResult.cs`): `{ Matches: ArchetypeMatch[]; Color: ArchetypeColor;
  Companion: ArchetypeCompanion? }`.
- **`ArchetypeMatch`** (`Model/ArchetypeMatch.cs`): `{ Archetype; Variant; Similarity: double }`.
  `Similarity` is `1.0` for every specific/variant match and a fraction for a fallback match.
- **Flattened App view** — `RecordArchetype` (`App/RecordArchetype.cs`):
  `{ Archetype: string; Color: string; Companion: string }`, where `Archetype` is:
  - `"Unknown"` if no matches,
  - the single match's display name if exactly one,
  - `"Conflict(A,B,…)"` if more than one.
- **Display name** — `Archetype.GetName(color)` (`Archetype.cs:16-31`): strips the literal substring
  `"Generic"` from `Name`; if `IncludeColorInName`, prepends the color word from `GetColorName` (Mono*,
  guild, shard/wedge, `5Color`, etc.); then **splits PascalCase into spaced words** via a regex. So rule
  `Name="BurnGeneric"` + `IncludeColorInName=false` → `"Burn"`; `Name="Tempo"`, color UB, IncludeColor →
  `"Dimir Tempo"`.

---

## Python reimplementation — pseudocode

```python
from dataclasses import dataclass, field
from enum import Enum

@dataclass(frozen=True)
class Card:           # one deck row
    name: str
    count: int

class Cond(Enum):     # = ArchetypeConditionType (12 values, same names)
    IN_MAIN=1; IN_SIDE=2; IN_MAIN_OR_SIDE=3
    ONE_MAIN=4; ONE_SIDE=5; ONE_MAIN_OR_SIDE=6
    TWO_MAIN=7; TWO_SIDE=8; TWO_MAIN_OR_SIDE=9
    NOT_CONTAIN=10; NOT_CONTAIN_MAIN=11; NOT_CONTAIN_SIDE=12

@dataclass
class Condition: type: Cond; cards: list[str]

@dataclass
class Archetype:                      # ArchetypeSpecific
    name: str; include_color: bool
    conditions: list[Condition]
    variants: list["Archetype"] = field(default_factory=list)
    def complexity(self): return len(self.conditions)

@dataclass
class Fallback: name: str; include_color: bool; common_cards: list[str]   # ArchetypeGeneric

@dataclass
class Match: archetype; variant; similarity: float

# --- condition evaluation: exact, case-sensitive name equality ---
def _has(cards, name):        return any(c.name == name for c in cards)
def _count(cards, names):     return sum(1 for c in cards if c.name in names)   # DISTINCT rows, not copies

def test(main, side, a: Archetype) -> bool:
    for cd in a.conditions:
        if not cd.cards:                      # broken condition -> skip (vacuous)
            continue
        t, cs = cd.type, cd.cards
        if   t==Cond.IN_MAIN          and not _has(main, cs[0]):                 return False
        elif t==Cond.IN_SIDE          and not _has(side, cs[0]):                 return False
        elif t==Cond.IN_MAIN_OR_SIDE  and not(_has(main,cs[0]) or _has(side,cs[0])): return False
        elif t==Cond.ONE_MAIN         and not any(c.name in cs for c in main):   return False
        elif t==Cond.ONE_SIDE         and not any(c.name in cs for c in side):   return False
        elif t==Cond.ONE_MAIN_OR_SIDE and not(any(c.name in cs for c in main) or
                                              any(c.name in cs for c in side)):  return False
        elif t==Cond.TWO_MAIN         and _count(main,cs) < 2:                   return False
        elif t==Cond.TWO_SIDE         and _count(side,cs) < 2:                   return False
        elif t==Cond.TWO_MAIN_OR_SIDE and (_count(main,cs)+_count(side,cs)) < 2: return False
        elif t==Cond.NOT_CONTAIN      and (_has(main,cs[0]) or _has(side,cs[0])): return False
        elif t==Cond.NOT_CONTAIN_MAIN and _has(main, cs[0]):                     return False
        elif t==Cond.NOT_CONTAIN_SIDE and _has(side, cs[0]):                     return False
    return True

# --- colors: a color counts only if present in BOTH a land AND a nonland ---
def get_colors(main, side, lands: dict, nonlands: dict) -> str:
    land_t   = dict.fromkeys("WUBRG", 0)
    spell_t  = dict.fromkeys("WUBRG", 0)
    for c in (*main, *side):
        for ch in lands.get(c.name, ""):    land_t[ch]  += c.count
        for ch in nonlands.get(c.name, ""): spell_t[ch] += c.count
    s = "".join(ch for ch in "WUBRG" if land_t[ch] > 0 and spell_t[ch] > 0)  # WUBRG order fixed
    return s or "C"

COMPANIONS = {"Gyruda, Doom of Depths":"Gyruda", ...}   # 10-entry map
def get_companion(side):
    found = None
    for c in side:                          # last match wins
        if c.name in COMPANIONS: found = COMPANIONS[c.name]
    return found

def best_fallback(main, side, fallbacks: list[Fallback]) -> Match | None:
    weights = {}
    for f in fallbacks:
        weights[f] = sum(c.count for c in (*main, *side) if c.name in f.common_cards)
    if not any(weights.values()): return None
    mx = max(weights.values())
    best = sorted([f for f,w in weights.items() if w==mx], key=lambda f: len(f.common_cards))[0]
    denom = len(main) + len(side)           # NOTE: # of rows, not copies
    sim = (mx / denom) if denom else 0.0     # guard /0 (C# would NaN)
    return Match(best, None, sim)

def detect(main, side, fmt, min_similarity=0.1, prefer_simpler=False) -> dict:
    color     = get_colors(main, side, fmt.lands, fmt.nonlands)
    companion = get_companion(side)
    results: list[Match] = []
    for a in fmt.archetypes:                 # top-level specifics only (variants reached via parent)
        if test(main, side, a):
            hit_variant = False
            for v in a.variants:
                if test(main, side, v):
                    hit_variant = True
                    results.append(Match(a, v, 1.0))
            if not hit_variant:
                results.append(Match(a, None, 1.0))

    if not results:
        fb = best_fallback(main, side, fmt.fallbacks)
        if fb and fb.similarity > min_similarity:   # strict >, default 0.1
            results.append(fb)
    elif len(results) > 1 and prefer_simpler:
        results.sort(key=lambda m: m.archetype.complexity()
                                  + (m.variant.complexity() if m.variant else 0))
        results = results[:1]                # fewest conditions wins

    return {"matches": results, "color": color, "companion": companion}

# --- App-layer flattening to the final label ---
def label(result) -> str:
    ms = result["matches"]; color = result["color"]
    def name(m):
        a = m.variant or m.archetype
        n = a.name.replace("Generic", "")
        if a.include_color: n = color_word(color) + n   # Mono*/guild/shard/4c/5Color
        return pascal_split(n)                            # regex PascalCase -> "Dimir Tempo"
    if len(ms) == 0: return "Unknown"
    if len(ms) == 1: return name(ms[0])
    return f"Conflict({','.join(name(m) for m in ms)})"
```

**Determinism/order note for the port:** C# iterates archetypes in `Directory.GetFiles` order (OS/filename
order) and `PreferSimpler` uses a stable `OrderBy`. To reproduce labels bit-for-bit, load rule files in
**sorted filename order** and use a stable sort. The default mode does not depend on order (conflicts list
all matches), but the `Conflict(...)` string's internal order does.

---

## Suggested cross-references to sibling subdomains
- **RULES (rule DATA schema):** This brief is the *consumer* of their schema. The condition `Type` strings,
  `Cards` arrays, `Variants` nesting, `CommonCards`, `IncludeColorInName`, and the `Archetypes/` vs
  `Fallbacks/` folder split (which determines `ArchetypeSpecific` vs `ArchetypeGeneric`) are their domain —
  see §1 (condition table), §3 (variants), §4 (fallback), §8 (loader). They own field *meanings*; we own
  field *evaluation*.
- **CARD-CONTRACT (Scryfall fields):** §5 color computation does **not** use Scryfall color identity — it
  uses Badaro's `card_colors.json`/`color_overrides.json` land/nonland maps. CARD-CONTRACT should reconcile
  whether the port keeps those curated maps or derives Lands/NonLands tables from Scryfall
  `type_line`/`color_identity`. §6 naming: the exact-match contract means CARD-CONTRACT owns canonical card
  names (split `//`, DFC front-face) that must align with rule files.
- **INGEST (fbettega cache):** §8 input contract — the cache's `DeckItem{Count,CardName}` must map cleanly
  to `Card{name,count}`, and §6's exact-match requirement makes name normalization at ingest a hard
  dependency. The fbettega pipeline already labels with these same Badaro rules (see
  `docs/briefs/legacy-metagame.md`), so INGEST may be able to reuse or cross-check labels.
- **PORT (vendor-vs-rewrite):** The engine is ~210 LOC, pure, deterministic, well-tested (`ConditionTests.cs`
  ports 1:1 as a Python parametrized suite). This brief is the rewrite spec; PORT decides whether to rewrite
  in Python (recommended — trivial size, no .NET runtime dependency) or shell out to the archived binary.
- **SERVE/OPS:** Output contract (§8) defines the `RecordArchetype{Archetype,Color,Companion}` shape that
  downstream meta-share/matchup aggregation consumes; the `Conflict(...)` and `Unknown` sentinels need
  handling policy (drop, flag, or manual-review queue).
