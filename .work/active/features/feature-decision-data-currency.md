---
id: feature-decision-data-currency
kind: feature
stage: review
tags: [ingestion, infra, analytics]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Decision-data currency — reproducible runtime, card coverage, and refresh cycle

## Brief

Keep the evidence behind the ranking current and make gaps visible. Align the supported local
Python environment with CI, normalize recoverable localized card names to English, distinguish
localized/new-set/unrecoverable card-dimension misses, emit a compact coverage summary, and provide
one repeatable refresh cycle for tournament data, labels, discoveries, eras, and ranking output
with B&R/new-release awareness.

This feature absorbs the focused scope of `idea-local-ci-python-drift` and
`bug-card-dimension-localized-and-new-card-gaps`, plus the scheduled refresh/format-monitoring
member of `epic-data-autonomy`. It explicitly excludes the upstream tournament hot spare,
Card Kingdom pricing, and unrelated catalog enrichment.

## Strategic decisions

- Raw provider data remains the source of truth; DuckDB remains rebuildable.
- Exact localized aliases may normalize automatically with provenance; ambiguous/truncated names
  remain unresolved and counted rather than guessed.
- Refresh automation is local and repeatable; no cloud service or protected-branch push is part of
  this feature.

## Simplification opportunity

Replace the multi-command operator runbook with one composition command while retaining the
individual commands as testable primitives. Consolidate warning spam into one coverage result plus
drill-down detail.

## Design decisions

- **Supported runtime**: Python 3.13 is the maintainer/runtime pin and the CI interpreter. Keep the
  package's claimed compatibility at `>=3.11,<3.14`, test the lower bound and the pinned runtime in
  CI, and make `.python-version` + contributor documentation point at 3.13. Python 3.14 is not
  supported until the scientific/discovery dependency stack is green there.
- **Localized-name source**: do not pretend the `oracle_cards` bulk or `/cards/named?exact=` can
  supply localized aliases. The current mirror has zero Portuguese/Russian `printed_name` rows, and
  direct probes for observed Portuguese names return no match. Stream Scryfall's compressed
  `all_cards` bulk (the provider's every-printing/every-language artifact) into a compact exact-alias
  index. Persist canonical English name, printed spelling, language, sample Scryfall id, and bulk
  timestamp. Never use fuzzy resolution.
- **Derived-cache normalization**: keep provider JSON untouched as the raw source of truth. In the
  rebuildable DuckDB cache, rewrite exact resolved `deck_cards.name` values to the canonical English
  name; the alias table retains the raw spelling and provenance. Ambiguous mappings are never
  applied.
- **Gap taxonomy**: report exact localized recoveries, direct new-card recoveries, ambiguous aliases,
  conservatively suspected truncations, and unresolved names separately. `suspected_truncated` means
  an unresolved single non-Latin token that occurs inside one or more known localized aliases; it is
  a diagnosis label, not a resolution. All other misses remain `unresolved` rather than being guessed.
- **Refresh surface**: ship one repository-local composition script,
  `.venv/bin/python scripts/refresh_decision_data.py`, that calls reusable Python primitives in the
  fixed order cache/rules/cards → name coverage → label → staged-camp apply → eras → ranking. Do not
  compose Click commands or shell strings. The final ranking writer remains the existing tracked
  script/template path, exposed as a callable for the composition adapter.
- **Format awareness**: the refresh result shows the latest operator-confirmed B&R ledger event, era
  drift alarms, and the existing Scryfall upcoming/recent release scan. It does not scrape WotC or
  automatically mutate the curated B&R ledger; new B&R actions still require the existing
  `eras confirm` human-confirmed path.
- **Alias refresh cadence**: build the alias snapshot when absent and refresh it once when the release
  scan contains a recent set code not recorded in the alias manifest. Do not redownload the ~390 MB
  compressed all-cards artifact merely because Scryfall republishes it daily.
- **Failure contract**: mutating steps are idempotent and checkpointed in order. A required step
  failure stops before dependent steps, prints completed/failed/not-run audit lines, and exits
  non-zero. Advisory release-scan or per-name exact-lookup failures degrade into the coverage report
  and do not erase last-good data.
- **Explicit exclusions**: no upstream tournament hot spare, vendor pricing changes, unrelated card
  catalogs, cloud scheduler/state, git commit, or push behavior.

## Architectural choice

Three shapes were considered:

1. A shell runbook that invokes the existing CLI leaves in sequence. This is small, but failure
   state is inferred from process output, the steps are difficult to test as one contract, and card
   coverage would remain an after-the-fact warning parser.
2. A typed in-process workflow with a thin repository-local script adapter. This reuses the existing
   domain functions, makes step order/results testable, and lets the ranking script expose a callable
   without moving its large page builder into a second implementation.
3. A generic declarative workflow/manifest runner. It could serve future pipelines, but there is no
   second consumer and it would add a framework where a direct function is enough.

Choose option 2. The domain coverage calculation lives under `ingestion/`; orchestration owns only
ordering and audit status; the script owns process arguments/output. This keeps raw provider data and
the DuckDB derived cache in their existing roles and avoids a second ranking implementation.

For localized aliases, three sources were considered: the existing `default_cards` price bulk,
targeted exact-name API lookup, or Scryfall's compressed `all_cards` artifact. Local inspection showed
that `default_cards` contains very sparse non-English coverage, while live exact-name probes for
observed Portuguese spellings returned no match. Choose `all_cards`: Scryfall describes it as every
card object in every language, and its compressed stream can be reduced in one pass to only printed
name → canonical-name facts. A release-code manifest avoids paying the full download on ordinary daily
runs. This shares no price-table behavior and keeps the resulting runtime resolver local.

## Implementation Units

### Unit 1: Pin and test one supported Python contract

**Files**: `pyproject.toml`, `.python-version`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`,
`tests/test_runtime_contract.py`

```toml
requires-python = ">=3.11,<3.14"
```

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.13"]
```

**Story**: `feature-decision-data-currency-runtime-alignment`

**Implementation Notes**:

- `.python-version` contains `3.13`; CI's upper matrix member must match it. The lower-bound job proves
  the package claim rather than testing only the maintainer pin.
- Document that the optional `discovery` extra is supported only where its transitive NumPy/Numba
  stack installs; keep its existing honest skip behavior. Do not broaden the feature into dependency
  upgrades.
- Run the previously divergent super-archetype and sideboard tests on both CI interpreters. If a
  failure is a product bug, follow the project's park-then-fix test-integrity rule; do not weaken it.
- Update the lock's Python constraint only if required by the package tool, preserving any unrelated
  pre-existing `uv.lock` edit rather than overwriting it.

**Acceptance Criteria**:

- [ ] A fresh checkout selects Python 3.13 from `.python-version`, and contributor instructions name
      3.13 as the tested local runtime.
- [ ] Package metadata rejects Python 3.14 while accepting 3.11 through 3.13.
- [ ] CI runs the suite on 3.11 and 3.13; the declared upper tested runtime and `.python-version` agree.
- [ ] The optional discovery extra's unsupported-stack behavior is documented and remains an honest
      skip, not a false green assertion.

### Unit 2: Build and persist the exact localized-alias index (trickiest unit)

**Files**: `src/legacy_engine/config.py`, `src/legacy_engine/ingestion/scryfall.py`,
`src/legacy_engine/ingestion/store.py`, `src/legacy_engine/models/card.py`,
`tests/test_card_name_resolution.py`

```python
from enum import StrEnum
from datetime import datetime
from legacy_engine.models.base import LegacyEngineModel

class CardNameStatus(StrEnum):
    CANONICAL = "canonical"
    LOCALIZED = "localized"
    NEW_CARD = "new_card"
    AMBIGUOUS = "ambiguous"
    SUSPECTED_TRUNCATED = "suspected_truncated"
    UNRESOLVED = "unresolved"

class CardNameResolution(LegacyEngineModel):
    observed_name: str
    normalized_name: str
    status: CardNameStatus
    canonical_name: str | None = None
    language: str | None = None
    scryfall_id: str | None = None
    source: str
    source_updated_at: str | None = None
    resolved_at: datetime
    reason: str

class PrintedCardAlias(LegacyEngineModel):
    printed_name: str
    normalized_alias: str
    canonical_name: str
    language: str
    scryfall_id: str

class CardAliasManifest(LegacyEngineModel):
    source_updated_at: str
    built_at: datetime
    release_codes: tuple[str, ...]
    alias_count: int
    ambiguous_key_count: int

def normalize_alias_key(name: str) -> str: ...
def download_all_cards_bulk(self, *, force: bool = False) -> Path: ...
def iter_printed_aliases(
    self,
    path: Path | None = None,
) -> Iterator[PrintedCardAlias]: ...

def init_card_alias_schema(con: duckdb.DuckDBPyConnection) -> None: ...
def rebuild_card_aliases(
    con: duckdb.DuckDBPyConnection,
    aliases: Iterable[PrintedCardAlias],
    *,
    manifest: CardAliasManifest,
) -> CardAliasManifest: ...
def fetch_card_alias_candidates(
    con: duckdb.DuckDBPyConnection,
    observed_name: str,
) -> tuple[PrintedCardAlias, ...]: ...
def alias_snapshot_needs_refresh(
    manifest: CardAliasManifest | None,
    recent_release_codes: Iterable[str],
) -> bool: ...
```

**Story**: `feature-decision-data-currency-card-coverage`

**Implementation Notes**:

- Add `card_name_aliases(normalized_alias, canonical_name, printed_name, language,
  sample_scryfall_id, source_updated_at, PRIMARY KEY(normalized_alias, canonical_name, language))` and
  a single-row manifest table as derived DuckDB state. Retaining every canonical candidate is
  load-bearing: ambiguity is a query result, not information discarded during indexing.
- `normalize_alias_key` is intentionally broader than canonical `normalize_name`: Unicode NFKD,
  casefold, smart-apostrophe normalization, combining-mark removal, and whitespace collapse. It is
  used only to find alias candidates. A key resolves only when its rows reduce to one distinct
  canonical English name; accent/case folding that creates multiple targets becomes `AMBIGUOUS`.
- Stream gzip JSONL; never load the all-cards artifact into memory or into the `cards` dimension.
  Index top-level `printed_name` and face-level printed names when they differ from the canonical
  English name. Deduplicate repeated printings deterministically and keep a stable sample id.
- Download/build when no manifest exists or a recent release code is absent from the manifest. An
  unchanged release-code set reuses the local alias table even if Scryfall's daily bulk timestamp has
  advanced. A successful rebuild replaces aliases and manifest in one DuckDB transaction.
- Before alias lookup, resolve normalized canonical/face names already in `cards`. A canonical card
  from the current oracle refresh whose name appears in that refresh's `IngestDiff.new_names` is
  reported as `NEW_CARD` without using the alias index.
- Apply only `CANONICAL`, `LOCALIZED`, and `NEW_CARD` resolutions to the rebuildable
  `deck_cards.name`. Preserve provider JSON unchanged; provenance survives in `card_name_aliases`.
- The all-cards download is an external boundary. On timeout/5xx/corrupt gzip, retain the last-good
  alias table/manifest and mark the coverage result degraded; never replace it with an empty index.

**Acceptance Criteria**:

- [ ] Exact Portuguese/other localized printed names in a synthetic JSONL gzip resolve to the canonical
      English card and carry printed spelling, language, sample Scryfall id, provider timestamp, and
      local build timestamp.
- [ ] Curly apostrophe/NFC/case-only aliases resolve locally without a network call.
- [ ] Fuzzy, prefix, and multiple-target matches are never applied; colliding normalized keys return
      all candidates and become `AMBIGUOUS`.
- [ ] A canonical card added by the current oracle-card diff is reported as a new-card recovery.
- [ ] Re-running with no newly observed release code reuses persisted aliases and performs no all-cards
      download.
- [ ] Download/parse failures keep raw names and the last-good alias table/manifest untouched and mark
      the report degraded.

### Unit 3: Compute and render one compact card-dimension coverage contract

**Files**: `src/legacy_engine/ingestion/card_coverage.py`, `src/legacy_engine/cli.py`,
`tests/test_card_name_resolution.py`, `tests/test_card_coverage_cli.py`

```python
class CardCoverageReport(LegacyEngineModel):
    distinct_names: int
    affected_decks: int
    localized_recovered: tuple[CardNameResolution, ...]
    new_cards_recovered: tuple[CardNameResolution, ...]
    normalized_existing: tuple[CardNameResolution, ...]
    ambiguous: tuple[CardNameResolution, ...]
    suspected_truncated: tuple[CardNameResolution, ...]
    unresolved: tuple[CardNameResolution, ...]
    alias_snapshot_updated_at: str | None
    alias_snapshot_degraded: bool
    alias_snapshot_reason: str | None = None

    @property
    def unresolved_count(self) -> int: ...

def reconcile_card_dimension(
    con: duckdb.DuckDBPyConnection,
    *,
    new_card_names: frozenset[str],
    alias_manifest: CardAliasManifest | None,
    alias_snapshot_reason: str | None,
    resolved_at: datetime,
) -> CardCoverageReport: ...

def card_coverage_audit_lines(report: CardCoverageReport) -> tuple[str, ...]: ...
```

**Story**: `feature-decision-data-currency-card-coverage`

**Implementation Notes**:

- Snapshot observed names absent before the oracle refresh, then scan distinct `deck_cards.name` values
  after refresh, retaining the distinct affected-deck count. `new_card_names` from `IngestDiff` makes
  the recovered new-set gap visible even though it is now present in `cards`. Resolve/apply aliases in
  one transaction after all classifications are known.
- Classify an unresolved name as `SUSPECTED_TRUNCATED` only when it is one non-Latin lexical token and
  that token occurs within at least one known localized alias key; otherwise `UNRESOLVED`. The reason
  states the evidence and that no mapping was applied.
- Replace per-card warning spam on the decision-refresh path with one `// card dimension: ...` line and
  optional deterministic `//   <status>: <name> — <reason>` drill-down lines under `--verbose`.
  Existing standalone advisors may retain their warnings until they adopt the resolver; do not edit the
  deferred sideboard model in this feature.

**Acceptance Criteria**:

- [ ] The summary reports recovered localized/new-card counts plus unresolved ambiguous,
      suspected-truncated, and unresolved counts, affected decks, and alias-snapshot currency/degrade.
- [ ] Empty/full-coverage corpora emit an explicit zero-gap summary rather than silence.
- [ ] Ambiguous and truncated inputs remain unchanged and appear in deterministic drill-down output.
- [ ] CLI tests use a file-backed temporary DuckDB and a synthetic alias snapshot; they never read the
      default DB or make network calls.

### Unit 4: Compose the complete decision-data refresh

**Files**: `src/legacy_engine/workflows/__init__.py`,
`src/legacy_engine/workflows/decision_refresh.py`, `scripts/refresh_decision_data.py`,
`scripts/refresh_best_call_ranking.py`, `tests/test_decision_refresh.py`,
`tests/test_refresh_best_call_ranking.py`, `docs/analysis/best-call-ranking.md`

```python
class RefreshStepStatus(StrEnum):
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"
    NOT_RUN = "not_run"

class RefreshStepResult(LegacyEngineModel):
    name: str
    status: RefreshStepStatus
    summary: str
    reason: str | None = None

class FormatAwareness(LegacyEngineModel):
    latest_registered_ban_date: str
    latest_registered_ban_card: str
    upcoming_releases: tuple[str, ...]
    recent_releases: tuple[str, ...]
    era_alarms: tuple[str, ...]

class DecisionRefreshResult(LegacyEngineModel):
    steps: tuple[RefreshStepResult, ...]
    card_coverage: CardCoverageReport
    format_awareness: FormatAwareness
    ranking_output: str | None

class DecisionRefreshPorts(Protocol):
    def refresh_sources(self, db_path: Path) -> SourceRefreshResult: ...
    def reconcile_cards(
        self,
        db_path: Path,
        source_result: SourceRefreshResult,
    ) -> CardCoverageReport: ...
    def label(self, db_path: Path) -> int: ...
    def apply_staged_camps(self, db_path: Path) -> CampApplyResult: ...
    def run_eras(self, db_path: Path) -> EraRunResult: ...
    def write_ranking(self, db_path: Path, out_path: Path) -> None: ...

def run_decision_refresh(
    ports: DecisionRefreshPorts,
    *,
    db_path: Path,
    out_path: Path,
) -> DecisionRefreshResult: ...

def generate_ranking(
    *,
    db_path: Path,
    out_path: Path,
    field_since: str | None = None,
    ground_n: int = 8,
    top_k: int = 8,
    cover_min: float = 0.8,
    min_row_share: float = 0.001,
    include_superarchetypes: bool = True,
) -> dict: ...
```

**Story**: `feature-decision-data-currency-refresh-cycle`

**Implementation Notes**:

- The production adapter calls existing domain primitives directly. Extract reusable bodies from Click
  commands only where needed; Click remains a presentation adapter. No `CliRunner`, subprocess, shell,
  cloud, git, or scheduler behavior inside the workflow.
- Source refresh includes tournament cache + rules + release-aware oracle-card refresh, but not prices.
  It captures the existing release scan and refreshes the all-cards alias snapshot only when absent or
  a recent release code is not in its manifest.
- Apply every parent in `staged_split_parents()` in sorted order using the existing apply/incremental
  functions, then run eras. Ranking is strictly last because it consumes labels, variants, and eras.
- Refactor `scripts/refresh_best_call_ranking.py::main` into argument parsing plus the typed
  `generate_ranking` callable without changing the generated blob/page. Existing parity and determinism
  tests are the regression gate.
- Stop on required-step failure. Render one `// refresh step: <name> — <status>` line per step, including
  `not_run` dependents, then exit non-zero. A release scan failure or individual card lookup outage marks
  the relevant step degraded but continues with last-good inputs.

**Acceptance Criteria**:

- [ ] One documented command performs refresh → exact card reconciliation → label → all staged camp
      applies → eras → ranking in that order and writes the tracked ranking output only after prerequisites
      succeed.
- [ ] Re-running on unchanged inputs is safe and deterministic: no duplicate aliases/events and an
      unchanged ranking blob.
- [ ] A failed required step prevents every dependent step and produces named completed/failed/not-run
      audit lines plus a non-zero exit.
- [ ] Output includes card coverage, latest registered B&R, release awareness, era alarms, and ranking
      path; it never claims to have scraped or confirmed an unregistered B&R action.
- [ ] Existing individual CLI commands and ranking-script arguments remain usable and tested.

## Implementation Order

1. Unit 2 — exact alias contract and provenance first, because the absent localized data in the current
   oracle bulk is the feature's highest-uncertainty boundary.
2. Unit 3 — coverage classification/transaction and compact audit output on top of the resolver.
3. Unit 1 — runtime pin and CI matrix can proceed independently of Units 2–3.
4. Unit 4 — compose only after the card contract and supported runtime are verified.

## Testing

### Unit tests: `tests/test_card_name_resolution.py`

- Build tiny gzip JSONL fixtures for localized printed-name, printed-face, duplicate printing,
  accent-fold collision, corrupt stream, and source-timestamp cases.
- Parametrize NFC, smart-apostrophe, case-only, single-token Cyrillic, and ordinary unresolved names.
- Verify provenance fields, transaction atomicity, idempotent alias reuse, and no fuzzy application.

### Runtime contract: `tests/test_runtime_contract.py`

- Parse package metadata, `.python-version`, and CI matrix; assert the pin/matrix/package upper bound do
  not drift independently.
- CI itself remains the behavioral proof on both supported boundary interpreters.

### Workflow tests: `tests/test_decision_refresh.py`

- Inject recording ports and assert exact step order, required-failure short-circuit, advisory degrade,
  deterministic staged-parent ordering, and result/audit status.
- Add one file-backed integration test using a tiny corpus and fake network adapters. Pass every path
  explicitly; never touch the developer DB, Scryfall, upstream repos, or tracked ranking page.

### Ranking regression: `tests/test_refresh_best_call_ranking.py`

- Call `generate_ranking` against the existing hermetic fixture and assert byte-identical output with the
  legacy `main` path, fixed seed, and unchanged command-line defaults.

## Risks

- **Riskiest assumption — Scryfall printed-name coverage matches provider spellings**: even the complete
  printing corpus may not contain informal translations or provider-truncated spellings. **Fallback**:
  keep them unresolved and measured; add curated overrides only through separately reviewed evidence,
  never fuzzy matching.
- **False truncation diagnosis**: a legitimate one-word non-Latin card could be labeled suspected
  truncated. The label never changes data and explicitly says “suspected,” so correctness is unaffected.
  **Fallback**: collapse it into unresolved if observed false positives make the heuristic unhelpful.
- **Partial long refresh**: cache/card refresh can succeed before a later label/era/ranking failure.
  **Fallback**: every step is idempotent, the result names the resume point, and ranking remains last-good
  until all prerequisites succeed; no destructive rollback is attempted on rebuildable state.
- **Ranking-script seam**: exposing a callable could accidentally diverge from CLI defaults.
  **Fallback**: one callable is the source of truth and the existing whole-blob determinism/parity tests
  exercise both adapter and direct paths.
- **Least sure — external B&R awareness**: the agreed no-scraper scope means the workflow can show the
  registered ledger and data-driven era alarms, not guarantee discovery of a brand-new WotC announcement.
  This limitation must be explicit in output and docs; a reliable announcement source needs separate
  research before automation.

## Implementation summary

- Execution capability: frontier/high; selected by the caller for consequential external-data and
  runtime reproducibility contracts.
- Review weight: standard (caller); feature intentionally stops at review for independent assessment.
- Child stories completed:
  - `feature-decision-data-currency-card-coverage` — `79c7b44`
  - `feature-decision-data-currency-runtime-alignment` — `cfeba46`
  - `feature-decision-data-currency-refresh-cycle` — `21354e7`
- Delivered the Python 3.11–3.13 contract, collision-preserving every-language alias snapshot,
  exact derived-cache reconciliation with compact honest coverage, release-code refresh cadence,
  typed stop-on-failure refresh composition, B&R/release/era awareness, and ranking-last output.
- Simplification: one in-process command replaces the manual shell pipeline while preserving each
  focused CLI/script surface.
- Discrepancies from design: `generate_ranking` landed in concurrent ranking-foundation commit
  `60cebbf`; this feature owns its byte-parity regression and workflow integration. The alias parser
  accepts both provider JSON arrays and JSONL gzip fixtures. `uv.lock` remained untouched because it
  contains the user's unrelated pre-existing modification.
- Adjacent issues parked: none.

## Integrated verification

- `.venv/bin/python -m pytest -q` — 3,592 passed, 1 expected optional-stack skip in 191.94s.
- Focused ingestion/runtime/workflow/ranking suite — 168 passed.
- Python bytecode compilation of the new workflow, coverage, and script surfaces — passed.
- All three child stories are `stage: done`; the feature is ready for standard independent review.
