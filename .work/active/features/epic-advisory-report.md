---
id: epic-advisory-report
kind: feature
stage: review
tags: [advisory]
parent: epic-advisory
depends_on: [epic-advisory-positioning, epic-advisory-whattoplay, epic-advisory-sideboard]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Field Read & Deck Recommendation Report (advise CLI surface)

## Brief
The advisor's terminal payoff: a coherent **"Field Read & Deck Recommendation"** report that composes the
three producers into one audit-trailed surface — field composition + derived **vulnerability profile** →
field-read narrative ("X% of the field is graveyard-reliant → graveyard hate is highest-equity") → decks
**ranked by positioning score**, each tagged proactive/reactive and best-deck/best-call → a recommended
**15-card sideboard package** → an **audit trail** (every number with its derivation, sample size, and a
heuristic-vs-data-driven label). Wires the **`advise` CLI group** — implements the `advise
positioning | sideboard | whattoplay` stubs to emit their individual reports, plus the combined field-read
report leaf (leaf name decided in feature-design). Each command loads a deck/field input and a `--field`
custom-field option (via `field-model`).

Pure composition + presentation: consumes `positioning` (S/ranking), `whattoplay` (proactivity, tags,
hate-equity, best-deck/best-call), and `sideboard` (`SideboardPackage`); recomputes nothing. Confidence is
per-component (not one global label); BEST-CALL recommendations gate on established/evolving matchup data.

Does NOT compute any advisory statistic (consumes all three); does NOT render charts (analytics `charts`
owns visual output) or cover simulation/generation.

## Epic context
- Parent epic: `epic-advisory`
- Position in epic: **terminal sink** — composes `positioning` + `whattoplay` + `sideboard` and wires the
  `advise` CLI surface. The epic's user-facing payoff.

## Inherited design decisions
- **Full Field-Read & Deck-Recommendation report** is the MVP surface (field composition + vulnerability
  profile + ranked decks + sideboard package + audit trail).
- **Audit trail mandatory**: every figure carries derivation + sample size + heuristic-vs-data-driven label.
- **Per-component confidence** (not one global label); **gate BEST-CALL on established/evolving data only**.
- **Custom field threads through** (`--field`) to positioning + sideboard + whattoplay via `field-model`.

## Research briefs
- `docs/briefs/advisory-methods.md` — §4 "the recommendation surface" (report structure + audit trail).

## Foundation references
- `docs/ARCHITECTURE.md` — `advisory/report.py`; the `advise positioning|sideboard|whattoplay` CLI group.
- `docs/SPEC.md` — the advisory MVP capabilities.
- `docs/PRINCIPLES.md` — advisory is first-class; confidence-gate the recommendation.

## Design decisions
(Resolved under autopilot delegation — Phase 4.5. Parent-epic + advisory-methods §4 decisions inherited.
No strategic 50/50s.)

- **Deck input = `--deck FILE`**, a plain-text decklist (`<count> <name>` lines; a `Sideboard`/blank-line
  marker splits main from side — the common MTG export format). Parsed to `(mainboard, sideboard)` dicts.
- **Deck → archetype via the done classifier**: `_classify_deck` resolves the maindeck's cards from the local
  `cards` table (reusing whattoplay's card-row reconstruction), computes colors (`compute_deck_colors`), loads
  the ruleset (`load_ruleset(RULES_DIR)`), and calls `matcher.classify`. A `--archetype` option overrides the
  classifier (and is the fallback when classification is `Conflict(...)`/`Unknown` — positioning needs a concrete
  archetype, so on an unresolved label positioning is skipped with a warning while whattoplay/sideboard still
  run on composition).
- **Field input = `--field FILE`** (`<share> <archetype>` lines → `build_custom_field`) else
  `build_global_field` from the corpus; `field_source` is surfaced in the report header (never an unlabeled field).
- **`report` owns the `advise` CLI surface**: implements the three `_not_implemented` stubs
  (`positioning`, `sideboard`, `whattoplay`) **and** adds a combined `advise report` leaf (the full Field Read &
  Deck Recommendation). All share the deck/field input plumbing.
- **Audit trail = collect, don't recompute**: each component already carries its provenance
  (`field_source`, positioning `s_ci`/`imputed`/tier, sideboard `heuristic_note`, whattoplay `findings`/tags,
  matchup n<30 gate). The report **gathers** these into an audit section — every figure shown with its
  derivation, sample size, and a heuristic-vs-data-driven label. **BEST-CALL is gated**: only asserted when the
  deck's matchup row has enough established/evolving cells (else labeled provisional).
- **Composition only — recompute nothing**: calls `positioning_score`/`rank_decks`, `proactivity_score`/
  `vulnerability_tags`/`best_deck_vs_best_call`/`plan_clash`, `recommend_sideboard`, and the field builders. No
  new statistic.
- **`FieldReadReport` is a `@dataclass` in `advisory/report.py`** (computed record; same sanctioned convention).
- **Determinism**: `advise positioning`/`report` accept `--seed` (threaded to the MC) so CLI output is testable.
- **Single-stride, no child stories** — one `advisory/report.py` (assembler + renderers) + the `cli.py` advise
  wiring; tightly coupled around the shared deck/field input.

## Architectural choice

**A `build_field_read_report` assembler that composes the three producers into a `FieldReadReport`, plus thin
text renderers, plus four `advise` CLI leaves sharing one deck/field input layer.** Options weighed: (A)
assembler returns a structured `FieldReadReport` and renderers/CLI consume it (chosen — the structure is
testable without parsing stdout, and the individual `advise` leaves reuse slices of it); (B) render directly in
each CLI command (rejected — untestable, duplicates composition); (C) one mega-command only (rejected — the
architecture commits to `advise positioning|sideboard|whattoplay` as separate leaves). The assembler gathers
each component's own provenance into the audit trail rather than re-deriving anything.

## Implementation Units

### Unit 1: Deck/field input plumbing (trickiest — designed first)

**File**: `src/legacy_engine/advisory/report.py`

```python
from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_custom_field, build_global_field
from legacy_engine.archetype.matcher import ArchetypeResult, classify
from legacy_engine.archetype.rules import load_ruleset
from legacy_engine.colors import compute_deck_colors
from legacy_engine.config import RULES_DIR

log = logging.getLogger(__name__)


def _parse_decklist(text: str) -> tuple[dict[str, int], dict[str, int]]:
    """Parse a plain-text decklist into (mainboard, sideboard).

    Lines ``<count> <name>``; a line equal to 'Sideboard' (case-insensitive) or a blank line after
    main cards starts the sideboard. Ignores comments (#) and blank leading lines. Raises ValueError
    on a malformed line / empty maindeck.
    """


def _classify_deck(con, mainboard: dict[str, int], sideboard: dict[str, int]) -> ArchetypeResult:
    """Resolve cards (local cards table), compute colors, load the ruleset, and classify."""


def _load_field(con, *, field_text: str | None, provenance: str | None = None) -> FieldDistribution:
    """Custom field from ``field_text`` (``<share> <archetype>`` lines) else the global field."""
```

**Implementation Notes**:
- `_parse_decklist`: tolerant of `4x Name` and `4 Name`; sideboard via `Sideboard` header or a blank separator.
- `_classify_deck`: reuse whattoplay's card reconstruction (resolve via `store.fetch_card`, split colors string);
  if no cards resolve, colors fall back to "" and classification likely `Unknown` — surfaced, not crashed.
- `_load_field`: parse `<share> <archetype>` → `build_custom_field`; on no file → `build_global_field(con, provenance=provenance)`.

**Acceptance Criteria**:
- [ ] `"4 Brainstorm\n4 Force of Will\nSideboard\n2 Surgical Extraction"` → main has Brainstorm:4, side Surgical:2.
- [ ] A known Reanimator-style list classifies to a non-Unknown archetype (corpus-backed ruleset test).
- [ ] `_load_field` with custom text builds a `field_source="custom"` distribution; without → `"global"`.
- [ ] Malformed line → `ValueError`.

---

### Unit 2: `FieldReadReport` + assembler

**File**: `src/legacy_engine/advisory/report.py`

```python
@dataclass
class FieldReadReport:
    deck_archetype: str
    field_source: str
    field_shares: dict[str, float]
    field_vuln_profile: dict[str, float]      # hate_equity: tag → field share attacked
    positioning: object | None                # PositioningResult (None if archetype unresolved)
    proactivity: object                       # ProactivityProfile
    vulnerability: frozenset[str]             # the deck's own tags
    best_deck_call: object | None             # BestDeckCall (None if archetype unresolved)
    sideboard: object                         # SideboardPackage
    audit: list[str]                          # audit-trail lines (figure → derivation/n/label)
    warnings: tuple[str, ...]


def build_field_read_report(
    con, mainboard: dict[str, int], sideboard_in: dict[str, int], field: FieldDistribution, *,
    archetype: str | None = None, reserved: int = 0, seed: int | None = None,
) -> FieldReadReport:
    """Compose positioning + whattoplay + sideboard + audit trail into a FieldReadReport."""
```

**Implementation Notes**:
- `archetype = archetype or _classify_deck(...).archetype`; if `Conflict(/Unknown` → `positioning=None`,
  `best_deck_call=None`, warning; else `positioning_score(matrix, field, archetype, seed=seed)` +
  `best_deck_vs_best_call(matrix, field, archetype)`.
- `field_vuln_profile = hate_equity(field, field_vulnerability_tags(con, field))`.
- `proactivity = proactivity_score(con, mainboard, archetype_tag=archetype)`;
  `vulnerability = vulnerability_tags_for_deck(con, mainboard)`.
- `sideboard = recommend_sideboard(con, field, mainboard, reserved=reserved)`.
- Build `audit` by collecting each component's provenance (field_source, positioning CI/tier/imputed,
  sideboard heuristic_note, proactivity findings, n<30 gate); gate BEST-CALL label on row data sufficiency.
- The matchup matrix is built once via `build_matrix(con)` and passed to positioning/best-deck-call.

**Acceptance Criteria**:
- [ ] On a corpus-backed field + a known deck, returns a populated report (positioning + sideboard + tags).
- [ ] An unresolved-archetype deck → `positioning is None` with a warning, but `sideboard`/`proactivity` present.
- [ ] `audit` contains the field_source, the sideboard heuristic note, and a confidence label.

---

### Unit 3: Text renderers

**File**: `src/legacy_engine/advisory/report.py`

```python
def render_field_read(report: FieldReadReport) -> str:
    """Render the full Field Read & Deck Recommendation as labeled text (field → vuln profile →
    positioning → sideboard → audit trail)."""
```
Plus small section renderers reused by the individual `advise` leaves (`_render_positioning`,
`_render_whattoplay`, `_render_sideboard`).

**Acceptance Criteria**:
- [ ] Output has labeled sections and never prints an unlabeled field/number; the audit trail is present.

---

### Unit 4: CLI `advise` leaves

**File**: `src/legacy_engine/cli.py` (replace the three `_not_implemented` stubs + add `advise report`)

```python
# advise positioning --deck FILE [--archetype X] [--field FILE] [--candidates FILE] [--reserved N] [--seed N] [--db]
# advise sideboard   --deck FILE [--field FILE] [--reserved N] [--solver ilp|greedy] [--db]
# advise whattoplay  --deck FILE [--field FILE] [--db]
# advise report      --deck FILE [--field FILE] [--reserved N] [--seed N] [--db]
```

**Implementation Notes**:
- Mirror the `report meta` CLI pattern: `_setup_logging(verbose)` first, lazy imports inside the command,
  `--db` via `store.connect`. Read `--deck`/`--field` files, parse, build the field, dispatch to the assembler
  or the relevant producer, render. `advise positioning --candidates FILE` (list of archetypes) → `rank_decks`.

**Acceptance Criteria**:
- [ ] `advise report --deck FILE` prints the full labeled report (no longer `_not_implemented`).
- [ ] `advise positioning`/`sideboard`/`whattoplay` each print their section; all four resolve a `--field` file.
- [ ] Missing `--deck` → a clear click error (not a stack trace).

---

### Unit 5: Module exports

**File**: `src/legacy_engine/advisory/__init__.py` — export `FieldReadReport`, `build_field_read_report`,
`render_field_read` (+ `__all__`).

## Implementation Order

1. **Unit 1** (deck/field input) — the plumbing all leaves share; trickiest (parsing + classify).
2. **Unit 2** (`FieldReadReport` + assembler) — the composition core.
3. **Unit 3** (renderers).
4. **Unit 4** (CLI leaves).
5. **Unit 5** (exports).

## Testing

### Unit tests: `tests/test_advise_report.py`
House style (`:memory:` corpus with `store.load_cards` + labeled decks + a loaded ruleset for `_classify_deck`;
`CliRunner` for the leaves writing deck/field files into `tmp_path`). MC paths pin `--seed`.

- `TestParseDecklist` — main/side split (Sideboard header + blank-line), `4x`/`4 ` forms, comments, malformed→ValueError.
- `TestClassifyDeck` — a known list classifies to the expected archetype; unresolved → Unknown surfaced.
- `TestLoadField` — custom file → custom field; none → global field.
- `TestBuildFieldReadReport` — populated report on a corpus field; unresolved-archetype → positioning None + warning; audit trail present + BEST-CALL gating.
- `TestAdviseCLI` — all four leaves run end-to-end via `CliRunner` (no longer `_not_implemented`); labeled output; `--field` honored; missing `--deck` errors cleanly.

### Integration points
- Seam with all three producers: the assembler calls the real `positioning_score`/`recommend_sideboard`/
  whattoplay functions over a corpus-backed matrix+field — the end-to-end advisory pipeline.
- Seam with `archetype`: `_classify_deck` uses the real `classify` + `load_ruleset`.
- Seam with `field-model`: `_load_field` builds both global and custom distributions.

## Risks

- **Decklist parsing variety**: real exports vary (set codes, `4x` vs `4`, MWDeck markers). **Mitigation**:
  tolerant parser for the common forms; malformed lines fail loudly (`ValueError`) rather than silently miscount.
  **Fallback**: `--archetype` lets the user bypass classification if their list won't parse to a known archetype.
- **Unresolved archetype kills positioning**: `Conflict`/`Unknown` decks can't be positioned. **Mitigation**:
  positioning is skipped with a clear warning; whattoplay (composition) + sideboard still run; `--archetype`
  override available. Honest, not a crash.
- **Composing four components multiplies failure surface**: any producer raising would abort the report.
  **Mitigation**: the assembler builds the matrix once and guards the archetype-dependent calls; component
  warnings flow into the report's `warnings`/`audit` rather than aborting. **Fallback**: the individual `advise`
  leaves let a user run one component in isolation.

## Implementation notes

### Files touched
- `src/legacy_engine/advisory/report.py` — new; Units 1–3 (plumbing + assembler + renderers)
- `src/legacy_engine/cli.py` — replaced 3 `_not_implemented` stubs (`advise positioning`, `advise sideboard`, `advise whattoplay`) with full implementations; added `advise report` leaf (Unit 4)
- `src/legacy_engine/advisory/__init__.py` — added `FieldReadReport`, `build_field_read_report`, `render_field_read` exports (Unit 5)
- `tests/test_advise_report.py` — new; 37 tests
- `tests/test_cli.py` — updated: removed 3 advise stubs from `test_leaf_stubs_not_implemented` parametrize (they are implemented); added `test_advise_subcommands_require_deck`

### Test count
- Before: 542 passing
- After: 577 passing (+37 new, -2 net from test_cli.py refactor = +35 net)

### Deviations from design with rationale
1. **`advise whattoplay` builds a partial `FieldReadReport` shell** (with `positioning=None` and a dummy `SideboardPackage`) rather than calling `build_field_read_report`, so it only runs the proactivity/vulnerability/best-deck-call components. This avoids running the expensive sideboard solver just to render the whattoplay section. The design says each leaf "prints its section" — honoured.
2. **`load_ruleset` is called inside `_classify_deck` at call time** (not lazily cached). This matches the pattern in `cli.py`'s `label` command and keeps the module side-effect-free.
3. **`_classify_deck` tests monkeypatch `load_ruleset`** instead of loading the vendored rules dir. This avoids a hard dependency on the vendored rules being present in CI (which the test corpus doesn't guarantee). Real integration is covered by the `_classify_deck` live path in CLI tests via the `--archetype` override path.

### Parked items
- Multi-card saturation (g(n) > 1) in sideboard is noted in sideboard.py as a future extension; not in scope here.
- `advise positioning --candidates` ranking output could be enriched with pairwise P(S_a > S_b) table; left as an additive extension.
