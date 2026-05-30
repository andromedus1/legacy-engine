---
description: The C#→Python port strategy for the archetype classifier — vendor Badaro's MTGOFormatData JSON rules as a pinned data dependency, reimplement only the matcher in Python, and gate fidelity with a golden-test harness against the frozen C# parser's labels.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Recommends vendoring MTGOFormatData (the archetype rules-as-JSON) as a versioned, pinned data
  dependency synced via a git subtree/submodule + a `refresh` CLI step, while reimplementing ONLY
  MTGOArchetypeParser's matching engine (~11 condition types, archetype→variant→fallback order,
  color_overrides) as a pure Python function in `archetype/`. The C# parser was archived 2025-09-24,
  so the matcher spec is a frozen, ~600-line target — ideal to port once and lock with golden tests.
  Fidelity is the dominant risk: a golden harness replays the archived C# parser's published JSON
  labels over a fixed corpus of fbettega/MTGODecklistCache tournaments and asserts ≥99% label
  agreement as a CI gate. Drift in the JSON data (new archetypes/condition types, monthly Legacy
  updates) is handled fail-fast — an unknown condition Type raises, mirroring edh-engine's
  fail-fast-on-unknown-role convention.
key_findings:
  - "HEADLINE: vendor the JSON rules as a pinned data dependency + reimplement ONLY the matcher in Python. Do NOT shell out to the C# binary, do NOT .NET-interop, do NOT rewrite the rule data. The data is the asset; the matcher is ~600 lines of frozen, well-understood logic."
  - "The C# MTGOArchetypeParser was ARCHIVED 2025-09-24 (.NET 8). A frozen reference implementation is the best possible port target: the spec stops moving, so a one-time port + golden lock is durable. The companion DATA (MTGOFormatData) keeps changing — that's exactly what we vendor and sync, not reimplement."
  - "Matcher scope is small and bounded: ~11 condition Types (InMainboard, InSideboard, InMainOrSideboard, plus OneOrMore/TwoOrMore × M/S/M-or-S, DoesNotContain), match order archetype→variant→fallback-by-card-overlap (≥10% threshold), color from decklist + color_overrides.json, IncludeColorInName naming."
  - "Vendor mechanism: git subtree (preferred) of the upstream rules repo into `data/archetype_rules/`, pinned to a commit SHA recorded in a manifest; a `legacy refresh rules` CLI command pulls upstream, diffs, and surfaces new archetypes/condition-types BEFORE they reach the matcher. Submodule is the fallback; fetch-on-build is rejected (non-deterministic, violates 'no runtime network calls')."
  - "Fidelity gate: golden test replays the archived C# parser's own published `mtgo_data_*.json` label outputs over a frozen tournament corpus from fbettega/MTGODecklistCache; assert per-deck label agreement ≥99% (target 100% on the locked rules SHA); CI fails below threshold. Disagreements are triaged as port bugs, never silently accepted."
  - "Drift handling is fail-fast, sibling-consistent: an unknown condition `Type` in vendored JSON raises `UnknownConditionTypeError` at load time (not at match time, not a silent skip) — mirrors edh-engine's fail-fast-on-unknown-role. New archetypes need no code change (data-driven); new condition Types need a matcher addition + a golden re-lock."
  - "Effort estimate: ~3–5 focused days. Matcher port + Pydantic models (~1.5d), vendor/subtree + refresh CLI + manifest (~1d), golden harness + corpus capture + CI gate (~1.5d). Top risks: (1) silent label divergence from subtle C# semantics, (2) upstream data-schema drift after archival, (3) color-detection edge cases (color_overrides + lands)."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md, relationship: extends}
  - {slug: docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md, relationship: extends}
  - {slug: docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/prior-art-scan.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md, relationship: parallel-to}
---

# C#→Python Port Strategy for the Archetype Classifier

The decision to **wrap Badaro's MTGOFormatData rules, ported to Python** is made. This brief decides *how*
to engineer that port — the build-vs-vendor split, the sync mechanism, the Python design, the fidelity
gate, and drift handling. It does **not** re-document the rule schema (see the RULES sibling) or the
matching algorithm pseudocode (see the CLASSIFY sibling); it relies on their specs and decides the
engineering.

Framing per [ARCHITECTURE.md](../../ARCHITECTURE.md): `archetype/` is "the key novel subsystem (no
commander to key on); it consumes ported MTGOFormatData rules + card data and emits Archetype labels,"
and the project mandate is to treat "archetype rules + cache as versioned local inputs." Per
[PRINCIPLES.md](../../PRINCIPLES.md) §4, "knowledge is compiled, not re-derived … the archetype taxonomy
is … ported from a maintained community ruleset so it stays aligned and auditable." This brief is the
concrete realization of those two statements.

## 0. What the two repos actually are (confirmed)

| Repo | What it is | Status | Our relationship |
|------|-----------|--------|------------------|
| [`Badaro/MTGOFormatData`](https://github.com/Badaro/MTGOFormatData) | **DATA.** Archetype rules-as-JSON per format: `Formats/Legacy/{metas.json, color_overrides.json, Archetypes/*.json, Fallbacks/*.json}`. Legacy maintained by Jiliac; updated ~monthly (B&R + meta shifts). | Live, community-maintained | **Vendor & sync.** This is the asset. |
| [`Badaro/MTGOArchetypeParser`](https://github.com/Badaro/MTGOArchetypeParser) | **CODE.** .NET 8 / C# rules engine that reads the data + a decklist and emits a label. Outputs console / CSV / JSON (`mtgo_data_yyyy_mm_dd.{csv,json}`). | **ARCHIVED 2025-09-24** — no longer maintained | **Reimplement the matcher only.** A frozen spec. |
| [`Badaro/MTGODecklistCache`](https://github.com/Badaro/MTGODecklistCache) | Tournament JSON (MTGO/Melee/Topdeck/Manatraders). Original mtgo.com scraper died 2025-06-10. | Superseded by fbettega mirror | Golden-test corpus source (INGEST sibling owns the schema). |

The archival of the *engine* (2025-09-24) while the *data* keeps moving is the single most important
fact for this decision: **we are porting against a frozen target.** The matcher's behavior will never
change upstream again, so a one-time faithful port plus a golden lock is durable — there is no treadmill
of chasing engine updates. All ongoing change lives in the JSON, which we vendor rather than reimplement.

## 1. Decision: vendor the rules, reimplement only the matcher

**Recommendation: vendor MTGOFormatData's Legacy JSON as a pinned data dependency, and reimplement ONLY
the MTGOArchetypeParser matching engine in pure Python.** Reject the three alternatives.

### Why this split

The system cleanly factors into *data* (the rules, which change ~monthly and encode the community's
evolving taxonomy) and *code* (the matcher, ~600 lines, frozen). Porting the data into Python types
would fork us off the community taxonomy and forfeit PRINCIPLES §4's "stays aligned and auditable" —
every monthly update would become a manual re-port. Porting the code is a one-time, bounded, lockable
effort against an archived spec. So: **own the matcher, rent the rules.**

### Alternatives considered and rejected

| Option | Verdict | Why |
|--------|---------|-----|
| **Vendor rules + port matcher** | **CHOSEN** | One-time bounded port against a frozen engine; data stays upstream-aligned; pure-Python, no runtime deps; testable to label-parity. |
| Rewrite the rules too (model archetypes as Python) | Reject | Forks us off the maintained taxonomy; every monthly upstream update becomes a manual re-port; violates "compiled, not re-derived" and "data-driven over hand-curated." |
| Shell out to the archived C# binary | Reject | Adds a .NET 8 runtime dependency to a Python CLI; brittle subprocess boundary; the binary is unmaintained and won't track future .NET; defeats "mirror edh-engine's stack exactly." Useful ONLY as a one-time golden-oracle (see §4), not in the runtime. |
| .NET interop (Python.NET / pythonnet) | Reject | Worst of both — a heavyweight runtime dependency AND a fragile FFI boundary, for logic we can port in days. |

This matches the architecture's "swap a new upstream source behind the `ingestion/` boundary without
touching analytics/advisory" instinct: the matcher is *our* code with a stable interface; the rules are
a swappable, versioned input.

## 2. How to vendor the rules

**Mechanism: git subtree of the upstream rules repo into `data/archetype_rules/`, pinned to a recorded
commit SHA, refreshed via a CLI command.**

```
data/
  archetype_rules/                 # git subtree of MTGOFormatData (or fork)
    Formats/Legacy/
      metas.json
      color_overrides.json
      Archetypes/*.json
      Fallbacks/*.json
    RULES_MANIFEST.json            # { source_repo, pinned_sha, pulled_at, format: "Legacy" }
```

### subtree vs submodule vs fetch-on-build

- **git subtree (preferred).** The JSON is physically present in our repo and history — tests and the
  matcher work on a fresh clone with **no extra fetch step**, no `.gitmodules` footgun, no detached-HEAD
  surprises. Updating is an explicit `git subtree pull` recorded as a normal commit, which gives a clean
  diff of "what archetypes changed this month" in our own PR review. This is the deterministic, offline-
  friendly choice the architecture demands ("no runtime network calls").
- **git submodule (fallback).** Acceptable but worse DX: contributors must `--recurse-submodules`, CI
  must init submodules, and the pointer is easy to leave stale. Choose only if the vendored tree is large
  enough that subtree bloats history (Legacy is small — a few hundred small JSON files — so subtree wins).
- **fetch-on-build (rejected).** Pulling upstream at build/install time is non-deterministic, breaks
  offline/air-gapped runs, and means two builds of the same SHA can classify differently. Violates the
  determinism principle inherited from edh-engine.

### Pinning, drift detection, and the sync workflow

A `RULES_MANIFEST.json` records the exact upstream `pinned_sha`, the source repo URL, and `pulled_at`.
The matcher loads rules *only* from the vendored tree at that SHA — never from a moving `master`. A CLI
command drives the monthly sync and makes drift loud:

```
legacy refresh rules            # git subtree pull upstream; update RULES_MANIFEST; then:
                                #   - diff archetype set (added / removed / renamed)
                                #   - scan all Conditions for any Type not in our matcher's enum
                                #   - print a human summary; exit non-zero if unknown Types appear
```

The sync is a reviewed PR (per the project's all-code-through-PRs rule), so a human sees the taxonomy
diff before it ships. Critically, the refresh step runs the **unknown-condition-type scan at sync time**,
so a new condition Type is caught in the refresh PR — not at classification time in production.

**Source-repo choice:** pin to `Badaro/MTGOFormatData` if it continues receiving Legacy updates; if the
community canonical fork has moved (the engine is archived; the data's long-term home should be confirmed
by the PRIOR-ART/INGEST siblings, e.g. an fbettega/Videre-Project mirror), point the subtree remote at
the live fork. The manifest's `source_repo` field makes this a one-line, auditable change.

## 3. Python design (edh-engine idiom)

The matcher is a **pure function** over typed inputs, living in `archetype/`. Rules are Pydantic models
loaded once from the vendored JSON; the classifier takes no I/O.

```python
# models/archetype_rules.py  — typed mirror of the vendored JSON (RULES sibling owns field semantics)
from enum import Enum
from pydantic import BaseModel

class ConditionType(str, Enum):
    IN_MAINBOARD                  = "InMainboard"
    IN_SIDEBOARD                  = "InSideboard"
    IN_MAIN_OR_SIDEBOARD          = "InMainOrSideboard"
    ONE_OR_MORE_IN_MAINBOARD      = "OneOrMoreInMainboard"
    ONE_OR_MORE_IN_SIDEBOARD      = "OneOrMoreInSideboard"
    ONE_OR_MORE_IN_MAIN_OR_SIDE   = "OneOrMoreInMainOrSideboard"
    TWO_OR_MORE_IN_MAINBOARD      = "TwoOrMoreInMainboard"
    TWO_OR_MORE_IN_SIDEBOARD      = "TwoOrMoreInSideboard"
    TWO_OR_MORE_IN_MAIN_OR_SIDE   = "TwoOrMoreInMainOrSideboard"
    DOES_NOT_CONTAIN              = "DoesNotContain"
    # NOTE: the precise upstream set is the RULES sibling's deliverable. Pydantic's str-Enum
    # parse on an unrecognized value MUST raise (fail-fast) — see §5.

class Condition(BaseModel):
    type: ConditionType
    cards: list[str]

class Archetype(BaseModel):
    name: str
    include_color_in_name: bool = False
    conditions: list[Condition]
    variants: list["Archetype"] = []     # variants share the archetype shape

class Fallback(BaseModel):
    name: str
    include_color_in_name: bool = False
    common_cards: list[str]              # similarity computed against these

class Ruleset(BaseModel):
    format: str                          # "Legacy"
    pinned_sha: str                      # from RULES_MANIFEST
    archetypes: list[Archetype]
    fallbacks: list[Fallback]
    color_overrides: dict[str, str]      # card name -> color identity override
```

```python
# archetype/classifier.py  — the ported matcher, a pure function
from models import Decklist
from models.archetype_rules import Ruleset

class ArchetypeResult(BaseModel):
    archetype: str                       # base archetype name
    variant: str | None                  # variant name if matched
    color: str | None                    # derived color string (when IncludeColorInName)
    display_name: str                    # final label, color-prefixed per the rules
    match_kind: Literal["archetype", "variant", "fallback"]
    matched_fallback_overlap: float | None  # set only when match_kind == "fallback"

def classify(
    decklist: Decklist,
    ruleset: Ruleset,
    card_colors: dict[str, str],         # CARD-CONTRACT sibling owns this Scryfall-derived map
) -> ArchetypeResult:
    """Faithful Python port of MTGOArchetypeParser's matching engine.
    Order: try each Archetype (all Conditions must pass) → resolve best Variant →
    if none match, fall back to the Fallback with the highest card overlap (≥10%).
    Pure: no I/O, deterministic, side-effect free. Algorithm spec: CLASSIFY sibling."
    ...
```

Design notes:
- **`card_colors` is injected, not fetched** — the matcher is pure and the color source is the
  CARD-CONTRACT sibling's Scryfall map, overlaid with `ruleset.color_overrides`. Keeps `archetype/`
  free of network/Scryfall coupling (ports-and-adapters per inherited engineering principles).
- **The function signature mandated by the task — `classify(decklist, ruleset, card_colors) ->
  ArchetypeResult` — is honored exactly.**
- Rule loading is a separate `archetype/rules_loader.py` (`load_ruleset(path) -> Ruleset`) so the matcher
  stays pure and the loader owns the fail-fast validation (§5).
- Placement in `archetype/`: `rules_loader.py` (load+validate JSON), `classifier.py` (the `classify`
  pure fn), `models/archetype_rules.py` (typed rules). The existing `models/` hosts `Archetype` /
  `ArchetypeResult` per the architecture's models table.

## 4. Testing the port for fidelity

**The dominant risk is silent divergence from upstream labels.** A subtly wrong condition evaluation or
fallback tie-break produces a *plausible but wrong* archetype on a fraction of decks — invisible without
a reference oracle. The gate is a **golden test against the archived C# parser's own outputs.**

### Golden harness

1. **Freeze a corpus.** Select a fixed set of known Legacy tournaments from
   [`fbettega`/MTGODecklistCache](https://github.com/Badaro/MTGODecklistCache) (INGEST sibling owns the
   cache schema) — target a few thousand decks spanning multiple meta windows and at least one B&R
   boundary, so every archetype, several variants, and the fallback path are exercised.
2. **Generate the oracle once.** Run the archived C# `MTGOArchetypeParser` (a one-time, throwaway use of
   the .NET binary — *not* a runtime dependency) over that corpus at the **same pinned rules SHA**, and
   capture its `mtgo_data_*.json` per-deck labels as a committed golden fixture
   (`tests/golden/legacy_labels_<sha>.json`). If running .NET is impractical, fall back to the parser's
   *published* labeled outputs for those events; the C# binary is the gold standard, MTGGoldfish/MTGO
   site labels are a weaker secondary check (they may use different rule snapshots).
3. **Assert agreement.** The Python `classify()` runs over the identical corpus + same SHA; the test
   asserts per-deck `display_name` agreement. **Target 100% on the locked SHA** (same rules, same decks,
   faithful port ⇒ identical labels); set the **CI gate at ≥99%** to absorb genuine known-ambiguous
   fallback ties, with every disagreement enumerated in the failure output and triaged as a port bug —
   never silently accepted by raising the threshold.
4. **Re-lock on every rules sync.** When `legacy refresh rules` bumps the SHA, regenerate the golden
   fixture against the new SHA in the same PR, so the golden always reflects the vendored rules. The diff
   in the golden fixture *is* the human-reviewable record of how the taxonomy moved.

### CI gate

- A `test_archetype_fidelity` test, marked as a required check, fails the build below the agreement
  threshold. This is the contract that the port stays faithful.
- Plus ordinary unit tests per condition Type and a hand-built decklist per archetype/variant/fallback
  path (test-factory `_make_decklist(**kwargs)` builders per the project's test-factory pattern).

## 5. Handling upstream drift

Mirror edh-engine's **fail-fast-on-unknown-role** convention (PRINCIPLES §3/§4 spirit: never
wrong-but-fast, never silently degrade).

| Upstream change | Behavior | Where caught |
|-----------------|----------|--------------|
| **New archetype / variant / fallback** | No code change — data-driven. Loads and classifies via existing condition logic. Golden fixture updates in the sync PR. | Sync PR review (taxonomy diff) |
| **New condition `Type`** the matcher doesn't implement | **FAIL FAST.** `load_ruleset` raises `UnknownConditionTypeError(type, archetype, file)` at load time; the `refresh rules` scan also flags it and exits non-zero. The classifier never silently skips an unknown condition (which would mislabel decks). Fix = add the Type to `ConditionType` + the matcher branch + re-lock golden. | Sync-time scan + load-time validation |
| **Renamed / removed archetype** | Loads fine; golden diff shows the label change; reviewed in sync PR. | Golden diff |
| **Schema change** (new field, restructure) | Pydantic load raises on unexpected structure (strict models). | Load-time validation |

Rationale for **fail-fast over graceful-fallback on unknown Types:** a silently-skipped condition can
flip a deck into the wrong archetype with no signal, which directly corrupts the meta-% analytics the
whole platform exists to produce — and PRINCIPLES §6 forbids unlabeled/untrustworthy meta numbers. A
loud failure in a monthly sync PR is cheap; a quietly-wrong tier list is the exact failure mode the
project is built to avoid. New *archetypes* are graceful (data-driven, zero code); only new *condition
types* fail fast, because they are the one case requiring matcher code we don't yet have.

## 6. Effort estimate & risks

**Estimate: ~3–5 focused days** (one build session plus a fidelity-hardening session).

| Work | Size |
|------|------|
| Matcher port (`classifier.py`) + Pydantic rules models + loader | ~1.5d |
| Vendor subtree + `RULES_MANIFEST` + `legacy refresh rules` CLI + unknown-Type scan | ~1d |
| Golden harness: corpus capture, one-time C# oracle run, fixture commit, CI gate | ~1.5d |
| Unit tests per condition Type + per match path | folded into above |

The port is small precisely because the target is **frozen and bounded** (~11 condition types, a fixed
match order, ~600 lines of C#).

**Top 3 risks:**
1. **Silent label divergence** from subtle C# semantics (tie-breaks in fallback overlap, condition
   evaluation order, case/diacritic handling in card-name matching, split/MDFC name normalization).
   *Mitigation:* the golden gate at ≥99% with full disagreement enumeration; treat every mismatch as a
   bug, not noise.
2. **Upstream data home / schema drift after engine archival.** The engine is archived; the data's
   canonical maintained location must be confirmed (coordinate with PRIOR-ART/INGEST). If the live fork
   adds fields or condition Types, our fail-fast catches it but it costs matcher work. *Mitigation:*
   `source_repo` in the manifest + the sync-time scan make the migration auditable and the breakage loud.
3. **Color-detection edge cases.** `IncludeColorInName` + `color_overrides.json` + land-color handling
   are where faithful labels most often diverge (e.g. whether a deck's color string counts lands, or how
   overrides interact with Scryfall identity from the CARD-CONTRACT sibling). *Mitigation:* dedicated
   color unit tests and explicit golden coverage of color-named archetypes.

## Suggested cross-references to sibling subdomains

- **RULES (rule DATA schema):** owns the authoritative JSON schema for `metas.json`,
  `color_overrides.json`, `Archetypes/*.json`, `Fallbacks/*.json` and the exact, complete condition-`Type`
  set. My `models/archetype_rules.py` is the typed mirror of *their* schema — reconcile the `ConditionType`
  enum against their canonical list before locking.
- **CLASSIFY (algorithm pseudocode):** owns the precise matching order, all-conditions-must-pass
  semantics, variant resolution, and the fallback ≥10%-overlap tie-break. My `classify()` is the Python
  realization of their spec; the golden gate (§4) verifies the realization matches the C# they
  pseudocoded.
- **CARD-CONTRACT (Scryfall fields):** owns the `card_colors` map (and name normalization for
  split/MDFC/diacritics) that I inject into `classify()`. Risk #3 (color edge cases) lives at this seam.
- **INGEST (cache schema):** owns the fbettega/MTGODecklistCache tournament JSON shape — the source of
  my golden-test corpus (§4) and of the decklists fed to `classify()` at runtime.
- **PRIOR-ART (existing ports):** owns the search for any existing Python port/fork worth adopting. My
  default recommendation is **build the matcher** (it's small and the C# is a frozen reference); if they
  find a faithful, maintained Python port that already passes a label-parity check, adopting it is
  reasonable — but it must clear the same §4 golden gate before we trust it.
- **SERVE/OPS:** owns where `legacy refresh rules` and the fidelity CI check slot into the ops/CI surface.
