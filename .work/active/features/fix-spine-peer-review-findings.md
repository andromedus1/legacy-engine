---
id: fix-spine-peer-review-findings
kind: feature
stage: review
tags: [ingestion, archetype, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Ingestion + archetype-spine findings (cross-model peer review, Codex xhigh)

## Brief
Cross-model deep peer review (peeragent → Codex xhigh, ran the suite: 92 passed) of the ingestion +
archetype spine on 2026-05-30. No blockers; verified against code + the ingestion-archetype-contracts
briefs. Sound areas confirmed: `parse_rounds` flat/nested shapes, null-bye coercion, per-URI
`load_tournament` idempotency, `banlist_as_of` `<=` boundary, fail-fast unknown condition types + lenient
trailing-comma loading, `compute_deck_colors` model.

## Findings

### Classifier faithfulness (affects label accuracy)
1. **Variant `IncludeColorInName=false` overridden by a color-prefixed parent** (`matcher.py:90`) via
   `v.include_color_in_name or arch.include_color_in_name` — mislabels rules like Delver's `Temur Delver`
   variant. **Fix:** use the variant's own flag when a variant matches.
2. **Conflict labels lose color prefixes** (`matcher.py:100`) — built from raw names, sorted+deduped.
   **Fix:** build `Conflict(...)` from each match's final `_label(...)`, preserve matcher order.
3. **Fallback scoring diverges from the Badaro contract** (`matcher.py:117`) — uses maindeck only and divides
   by total maindeck copies; the contract scores main+side and divides by *distinct deck entries*. Can turn
   valid fallback decks into `Unknown`. **Fix:** pass sideboard into `_fallback`; match the documented
   denominator. *(Could reduce the ~4.7% unresolved rate.)*
4. **Condition semantics not fully faithful** (`matcher.py:43`) — `In*`/`DoesNotContain*` use all `Cards`
   while Badaro uses `Cards[0]`; empty `Cards` should be skipped; `TwoOrMoreInMainOrSideboard` should count a
   card in both zones as two hits. Latent (current vendored rules don't exercise the multi-card single-card
   types) but a contract gap. **Fix:** align to the rule-schema brief.

### Reproducibility / completeness
5. **`refresh_rules` doesn't pin to an input SHA** (`rules_vendor.py:30`) — records whatever HEAD was
   cloned/pulled. **Fix:** fetch/checkout a configured SHA and fail if unresolvable (true pinning).
6. **`_coerce_format` on a multi-format list picks the first** (`cache.py:78`) — `["Modern","Legacy"]` →
   `"Modern"`, so discovery skips the event. **Host-verified: zero impact on the current cache (no
   multi-format list entries), so no Legacy events were dropped** — but latent. **Fix:** normalize Formats to
   a collection and test membership for `"Legacy"`.

### Validation
7. **`validate_deck` never enforces `CATEGORY_BANS` and accepts nonpositive counts** (`banlist.py:107`) —
   an ante card not name-listed, or `{"Brainstorm": -1}`, produces no error. **Fix:** validate counts > 0;
   enforce category bans (needs card metadata for category predicates, or name-enumerate).

### Nits
8. **Scryfall name normalization is incomplete** (`scryfall.py:34`) — handles curly apostrophes but not
   Unicode/accents, and index keys aren't normalized; `card_faces[].name` isn't indexed. Risks resolution
   misses for accented names (e.g. "Khazad-dûm", "Æther"). **Fix:** Unicode-normalize keys + lookups; index
   face names.
9. **Fallback `tournament_id` can collide** (`store.py:111`) for no-URI events sharing source/name/date —
   full-refresh deletes then merge events. **Fix:** include file path or a content/player-set hash when URI
   is absent.

## How to apply
Classifier faithfulness (1–4) most affects label quality; route through `/agile-workflow:fix` with rule-based
regression tests grounded in the rule-schema brief. 5 (SHA pinning) and 7 (validate_deck) are correctness;
6/8/9 are latent/edge hardening.

## Design decisions
Captured via `/feature-design --only-questions` (interactive, 2026-05-30). These are fixed inputs for the
full design + implement pass — autopilot inherits them and should not re-decide.

- **Finding #1 (variant color flag)** — no fork; straight contract fix. When a variant matches, use the
  variant's own `include_color_in_name` (replace `v.include_color_in_name or arch.include_color_in_name`
  at `matcher.py:90` with `v.include_color_in_name`). Contract: label is color-prefixed iff the *matched*
  entry's flag is set (matching-algorithm brief line 25).
- **Finding #2 (Conflict label) → Contract-faithful.** Build `Conflict(...)` from each match's final
  color-prefixed `_label(...)`, in matcher (ruleset) order, **no sort, no dedupe** — exactly Badaro's
  `Conflict({String.Join(",", matches.Select(m => GetArchetype(m, color)))})` (brief line 123).
  *Implication:* existing `Conflict(...)` analytics keys change (raw sorted → color-prefixed ruleset-order).
  Acceptable — faithfulness is the feature's purpose. A re-label of stored data picks up the new keys; flag
  in implementation notes that downstream analytics reading old Conflict keys should expect the change.
- **Finding #3 (fallback math) → Full fidelity, including the quirk.** Pass sideboard into `_fallback`;
  weight = sum of *copies* of distinct main+side entries present in a pile's `common_cards`; **denominator =
  number of distinct deck entries (main+side rows), NOT total copies** (brief lines 201-204). This replicates
  Badaro's row-count denominator and shifts the effective 0.10 threshold semantics. `> MIN_FALLBACK_SIMILARITY`
  stays strict `>`.
- **Finding #4 (latent condition semantics) → Fix now, with regression tests.** Align all of
  `evaluate_condition` to the rule-schema brief even though no current vendored rule exercises these:
  single-card types (`InMainboard`/`InSideboard`/`InMainOrSideboard`/`DoesNotContain*`) use `Cards[0]` only;
  empty `Cards` lists are skipped (treated as non-constraining / no match per brief); `TwoOrMoreInMainOrSideboard`
  counts a card present in both zones as **two** hits (sum main-entry count + side-entry count, brief lines
  107-109) rather than `>= 2` over `main | side`. Cover with synthetic-ruleset regression tests grounded in
  the rule-schema brief.
- **Scope → All 9 findings, split into child stories.** Group as: **classifier** (1-4, the label-accuracy
  core), **correctness** (5 SHA-pinning `rules_vendor.py`, 7 `validate_deck` counts>0 + CATEGORY_BANS), and
  **hardening** (6 multi-format `_coerce_format`, 8 Scryfall Unicode/face-name normalization, 9 fallback
  `tournament_id` collision). Declare `depends_on` only where real (likely none cross-group; classifier
  stories may share the matcher edit and should serialize). Trickiest unit = finding #3 (fallback denominator
  + main/side threading) — design it first in the full pass.

## Architectural choice

**Fix-in-place, contract-faithful, split by disjoint file-group into 3 independently-implementable stories.**
The findings are localized corrections to existing functions, not new subsystems — so the architecture is
"edit the cited functions to match the Badaro/rule-schema contract, with regression tests grounded in the
briefs." The only non-trivial design choices are the contract semantics (locked in `## Design decisions`)
and the two implementation hooks resolved below.

The three story groups touch **disjoint files** and have no shared edits, so they carry `depends_on: []`
and can be implemented in parallel:
- **classifier** (1-4) → `archetype/matcher.py`
- **correctness** (5,7) → `ingestion/rules_vendor.py` + `config.py` + `ingestion/banlist.py` + `models/banlist.py`
- **hardening** (6,8,9) → `ingestion/cache.py` + `ingestion/scryfall.py` + `ingestion/store.py`

Rejected alternative: one single-stride edit. Rejected because the three groups have genuinely different
test surfaces (synthetic-ruleset matcher tests / git-runner + validation tests / normalization + id tests)
and gate cleanly per-story; parallel implementation is faster with zero merge risk given disjoint files.

Two implementation hooks (autopilot judgment, consistent with Ports & Adapters + Fail Fast):
- **#7 category-ban enforcement** — domain `validate_deck` must not import the store/Scryfall. Enforce
  ante + offensive bans via a name-enumerated `CATEGORY_BANNED_NAMES` frozenset in `models/banlist.py`
  (these can't be derived from `type_line` and are mostly already Legacy-illegal); optionally flag
  Conspiracy/Attraction/Sticker via an injected `type_line_of: Callable[[str], str | None] | None`
  resolver (skipped, documented, when absent — those types never appear in real Legacy data).
- **#4 empty `Cards`** — a condition with empty `Cards` is non-constraining (returns `True`, i.e. skipped
  from the AND). Defensive only; real vendored rules never emit empty `Cards`.

## Implementation Units

### Unit 1: Matcher contract fidelity (findings 1-4)

**File**: `src/legacy_engine/archetype/matcher.py`
**Story**: `fix-spine-peer-review-findings-classifier`

```python
# Finding #1 — variant uses its OWN color flag (matcher.py:90)
matches.append((v.name, v.name, v.include_color_in_name))          # was: v.include_color_in_name or arch.include_color_in_name

# Finding #2 — Conflict from each match's final color-prefixed label, matcher order, no sort/dedupe
if len(matches) > 1:
    label = ",".join(_label(base, inc, deck_colors) for base, _bn, inc in matches)
    return ArchetypeResult(archetype=f"Conflict({label})", color=deck_colors, kind="conflict")

# Finding #3 — fallback weights main+side copies; denominator = # distinct entries (rows)
def _fallback(mainboard, sideboard, ruleset, deck_colors) -> ArchetypeResult: ...
    weight = (sum(c for n, c in mainboard.items() if n in common)
              + sum(c for n, c in sideboard.items() if n in common))
    total_entries = len(mainboard) + len(sideboard)
    # accept iff best is not None and total_entries > 0 and best_weight / total_entries > MIN_FALLBACK_SIMILARITY
# classify() call site: _fallback(mainboard, sideboard, ruleset, deck_colors)

# Finding #4 — single-card types use Cards[0]; empty Cards -> True (skip); TwoOrMoreInMainOrSideboard double-counts both zones
def evaluate_condition(cond, main, side) -> bool:
    t, cards = cond.type, cond.cards
    if not cards:
        return True                                                 # empty Cards: non-constraining
    c0 = cards[0]
    if t in ("InMainboard",): return c0 in main
    if t in ("InSideboard",): return c0 in side
    if t in ("InMainOrSideboard",): return c0 in main or c0 in side
    if t == "OneOrMoreInMainboard": return _present(cards, main) >= 1
    if t == "OneOrMoreInSideboard": return _present(cards, side) >= 1
    if t == "OneOrMoreInMainOrSideboard": return _present(cards, main | side) >= 1
    if t == "TwoOrMoreInMainboard": return _present(cards, main) >= 2
    if t == "TwoOrMoreInSideboard": return _present(cards, side) >= 2
    if t == "TwoOrMoreInMainOrSideboard": return _present(cards, main) + _present(cards, side) >= 2
    if t == "DoesNotContain": return c0 not in main and c0 not in side
    if t == "DoesNotContainMainboard": return c0 not in main
    if t == "DoesNotContainSideboard": return c0 not in side
    raise UnknownConditionTypeError(t)
```

**Implementation Notes**:
- `In*` single-card types are `Cards[0]` only per the rule-schema brief (lines 92-103); `OneOrMore*` and
  `TwoOrMore*` keep whole-list semantics.
- `TwoOrMoreInMainOrSideboard` sums per-zone hit counts so a card in both zones counts twice (brief 107-109).
- Conflict labels now color-prefixed in matcher order — **changes existing `Conflict(...)` analytics keys**;
  note this in the implementation summary so a downstream re-label is expected.

**Acceptance Criteria**:
- [ ] A variant with `IncludeColorInName=false` under a color-prefixed parent is labeled without a color prefix.
- [ ] A two-match deck yields `Conflict(<colorlabelA>,<colorlabelB>)` in ruleset order, no dedupe/sort.
- [ ] Fallback similarity = (main+side matching copies) / (main rows + side rows); sideboard cards count.
- [ ] `TwoOrMoreInMainOrSideboard` passes when one matching card is in main and a different one in side, and when the *same* card is in both zones.
- [ ] Single-card `In*`/`DoesNotContain*` use `Cards[0]`; a second card in the list is ignored.
- [ ] Empty `Cards` condition evaluates `True` (non-constraining).

### Unit 2: Rules SHA pinning (finding 5)

**File**: `src/legacy_engine/ingestion/rules_vendor.py`, `src/legacy_engine/config.py`

```python
# config.py
MTGOFORMATDATA_SHA = "e056bc7d63c0138091986ce1696c705bc7dee296"  # pinned current vendored rules

# rules_vendor.py — refresh to a configured SHA and fail if unresolvable
def refresh_rules(repo=MTGOFORMATDATA_REPO, dest=RULES_DIR, sha=MTGOFORMATDATA_SHA, runner=subprocess.run) -> str:
    # clone (full, not --depth 1, so an arbitrary sha is reachable) or fetch; then:
    runner(["git", "-C", str(dest), "checkout", sha], check=True)
    resolved = _resolve_sha(dest, runner)
    if resolved != sha:
        raise RuntimeError(f"rules pin mismatch: wanted {sha}, got {resolved!r}")
    # write manifest {repo, sha}
```

**Implementation Notes**:
- Drop `--depth 1` (a shallow clone can't reach an arbitrary historical SHA) or use
  `git fetch --depth 1 origin <sha>` then `git checkout FETCH_HEAD`. Prefer the fetch form to stay shallow.
- Keep the injected `runner` so tests assert the git call sequence without the network.

**Acceptance Criteria**:
- [ ] `refresh_rules` checks out the configured SHA and writes it to the manifest.
- [ ] If the post-checkout HEAD ≠ configured SHA, it raises (no silent drift).
- [ ] Test asserts the checkout/verify call sequence via a fake runner.

### Unit 3: validate_deck — counts + category bans (finding 7)

**File**: `src/legacy_engine/ingestion/banlist.py`, `src/legacy_engine/models/banlist.py`

```python
# models/banlist.py — ante + offensive bans not derivable from type_line and not already in BASELINE_BANS
CATEGORY_BANNED_NAMES: frozenset[str] = frozenset({
    "Amulet of Quoz", "Bronze Tablet", "Contract from Below", "Darkpact", "Demonic Attorney",
    "Jeweled Bird", "Rebirth", "Tempest Efreet", "Timmerian Fiends",          # ante
    "Invoke Prejudice", "Cleanse", "Stone-Throwing Devils", "Pradesh Gypsies",
    "Jihad", "Imprison", "Crusade",                                            # offensive
})

# banlist.py
def validate_deck(maindeck, sideboard=None, snapshot=None,
                  type_line_of: Callable[[str], str | None] | None = None) -> list[str]:
    # counts must be positive integers
    for name, count in combined.items():
        if count <= 0:
            errors.append(f"{name}: nonpositive count ({count})")
        ...
        if name in CATEGORY_BANNED_NAMES:
            errors.append(f"{name} is banned by category (ante/offensive)")
        if type_line_of is not None:
            tl = type_line_of(name) or ""
            if any(k in tl for k in ("Conspiracy", "Attraction", "Sticker")):
                errors.append(f"{name} is not Legacy-legal (category: {tl})")
```

**Implementation Notes**:
- `type_line_of` is optional and injected (Ports & Adapters — domain doesn't import Scryfall/store);
  when `None`, type_line predicates are skipped (documented). Name-enumerated bans always fire.

**Acceptance Criteria**:
- [ ] `{"Brainstorm": -1}` and `{"Brainstorm": 0}` produce a nonpositive-count error.
- [ ] A `CATEGORY_BANNED_NAMES` card (e.g. "Contract from Below") is flagged even if not name-listed in the snapshot.
- [ ] With an injected `type_line_of` returning a Conspiracy/Attraction/Sticker line, the card is flagged; with `None`, no crash and no type-line error.

### Unit 4: _coerce_format multi-format (finding 6)

**File**: `src/legacy_engine/ingestion/cache.py`

```python
def _coerce_format(value) -> str:
    if isinstance(value, list):
        if "Legacy" in value:
            return "Legacy"
        return value[0] if value else ""
    return value or ""
```

**Acceptance Criteria**:
- [ ] `["Modern", "Legacy"]` → `"Legacy"` (event not skipped by Legacy discovery).
- [ ] Single-format string and single-element list behavior unchanged.

### Unit 5: Scryfall Unicode + face-name indexing (finding 8)

**File**: `src/legacy_engine/ingestion/scryfall.py`

```python
import unicodedata
def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFC", name.replace("’", "'").replace("‘", "'")).strip()

def load_card_index(self) -> dict[str, dict]:
    ...
    for card in cards:
        name = card.get("name", "")
        if not name: continue
        index[normalize_name(name)] = card
        if " // " in name:
            for face in name.split(" // "):
                index.setdefault(normalize_name(face), card)
        for face in card.get("card_faces", []) or []:
            fname = face.get("name", "")
            if fname:
                index.setdefault(normalize_name(fname), card)
```

**Implementation Notes**:
- Index keys AND the `get_card` query are both `normalize_name`-d so accented names (e.g. "Khazad-dûm")
  resolve regardless of NFC/NFD encoding in the decklist source.

**Acceptance Criteria**:
- [ ] An NFD-encoded "Troll of Khazad-dûm" query resolves to the NFC index entry.
- [ ] A DFC's individual `card_faces[].name` resolves to the parent card.
- [ ] Curly-apostrophe behavior preserved.

### Unit 6: tournament_id collision (finding 9)

**File**: `src/legacy_engine/ingestion/store.py`

```python
import hashlib
def tournament_id(tr: TournamentResult) -> str:
    if tr.uri:
        return tr.uri
    players = "|".join(sorted(d.player for d in tr.decks))
    digest = hashlib.sha1(players.encode()).hexdigest()[:8]
    return f"{tr.source}:{tr.name}:{tr.date}:{digest}"
```

**Implementation Notes**:
- Deterministic (sorted player set) so repeated full-refresh of the same event yields the same id —
  preserves `load_tournament` idempotency (the delete-then-insert keys on this id).

**Acceptance Criteria**:
- [ ] Two no-URI events with identical source/name/date but different player sets get distinct ids.
- [ ] The same no-URI event re-ingested yields the same id (idempotent refresh still works).
- [ ] URI-bearing events are unchanged.

## Implementation Order

1. **Unit 1 (matcher, finding #3 first)** — trickiest: the fallback denominator + main/side threading. If
   the row-count denominator interacts badly with the 0.10 floor on real data, revisit before the rest.
2. **Units 2-3 (correctness story)** — independent of Unit 1.
3. **Units 4-6 (hardening story)** — independent of both.

(Units 1 / 2-3 / 4-6 are the three child stories; order within a story matters, across stories does not.)

## Testing

### Unit tests
- `tests/test_matcher.py` — synthetic `RuleSet`s exercising: variant-own-color-flag; two-match conflict
  ordering/no-dedupe; fallback with sideboard cards + row-count denominator; `TwoOrMore*` both-zone
  double-count; `Cards[0]` single-card semantics; empty-`Cards` neutrality. Grounded in the rule-schema brief.
- `tests/test_rules_vendor.py` — fake `runner` asserting fetch/checkout/verify sequence; mismatch raises.
- `tests/test_banlist.py` — nonpositive counts; `CATEGORY_BANNED_NAMES`; injected `type_line_of`; `None` path.
- `tests/test_cache_parser.py` — `_coerce_format(["Modern","Legacy"])` → `"Legacy"`.
- `tests/test_scryfall.py` — NFD→NFC resolution; `card_faces[].name` indexing; curly apostrophe preserved.
- `tests/test_store.py` — collision distinctness + idempotent re-ingest + URI passthrough.

### Integration points
- Matcher changes feed the labeler (`label` CLI) and analytics; the Conflict-key change is the only
  cross-module ripple — flagged for downstream re-label. No schema change.

## Risks

- **Conflict analytics-key change** (finding #2): existing stored `Conflict(...)` labels differ from new
  color-prefixed keys. **Fallback**: a re-label pass over stored decks picks up new keys; no migration needed
  since labels are derived, not authored.
- **Fallback denominator quirk** (finding #3): the row-count denominator shifts the effective 0.10 threshold;
  a few decks may flip fallback↔Unknown. **Fallback**: this is the contract-faithful behavior by decision;
  if it regresses real labels materially, surface as a follow-up rather than reverting (decision is locked).
- **Full clone for SHA pin** (finding #5): dropping `--depth 1` increases clone size. **Fallback**: use
  `git fetch --depth 1 origin <sha>` + `checkout FETCH_HEAD` to stay shallow.

## Implementation run summary
All 3 child stories implemented and at `stage: review` (2026-05-30, autopilot wave). Full suite green.
- **classifier** (#1-4): matcher.py contract fidelity; +31 tests. **Conflict analytics keys changed**
  (color-prefixed, ruleset order) — a re-label pass over stored decks picks up the new keys (derived, no migration).
- **correctness** (#5,7): rules_vendor.py true SHA pinning (fetch+checkout+verify, raises on mismatch) +
  config `MTGOFORMATDATA_SHA`; validate_deck nonpositive-count + `CATEGORY_BANNED_NAMES` + optional
  `type_line_of` resolver; +17 tests.
- **hardening** (#6,8,9): `_coerce_format` Legacy-in-list; Scryfall NFC + `card_faces[]` indexing;
  `tournament_id` player-set hash for no-URI collisions; +~22 tests.
Verification: full `pytest` 745 passed (was 654). No cross-story integration issues.

## Notes
Reviewer: peeragent → Codex (session 019e7b6d-79db), effort xhigh, in-repo; ran the spine test subset
(92 passed). Companion: [[fix-analytics-peer-review-findings]], [[fix-advisory-peer-review-bugs]].
