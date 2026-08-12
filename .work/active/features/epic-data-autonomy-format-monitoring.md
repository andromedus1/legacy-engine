---
id: epic-data-autonomy-format-monitoring
kind: feature
stage: review
tags: [ingestion, infra]
parent: epic-data-autonomy
depends_on: [epic-data-autonomy-local-refresh-operations]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-12
---

# Ban/restricted and new-release change monitoring

## Brief

Add a local monitoring step around the scheduled decision-data refresh so format-changing events
do not depend on memory or an ad hoc manual check. Detect candidate Legacy legality changes and new
card releases from attributable upstream evidence, compare them with the engine's last accepted
state, and surface durable pending/clear/unavailable status.

Monitoring is detection, not authority: it must never silently rewrite the B&R ledger, taxonomy,
ranking regime, or card truth. A human must confirm format changes before they become accepted
engine state. Preserve last-good evidence through upstream failures and distinguish “no change”
from “could not check.” This feature does not implement the deferred hot-spare data pipeline,
vendor pricing, rules IR, sideboard modeling, or Modern deployment.

## Acceptance boundary

- Candidate changes retain source, observed-at time, effective/release date when available, and a
  stable identity suitable for acknowledgement.
- Repeated checks are idempotent and do not re-alert acknowledged unchanged evidence.
- Upstream ambiguity or failure produces a loud unavailable/pending state, never a false clear.
- Status integrates with the local refresh operator surface and is covered by hermetic adapters.

## Design decisions

- **Authority boundary**: the monitor writes machine-observed operational evidence only. It never
  calls `append_ban_event`, edits `data/banlist/events.json`, or changes a regime. `eras confirm`
  remains the sole acceptance path for a newly banned card. A confirmed candidate is retired on the
  next monitor run by comparing it with the curated ledger.
- **Two-signal semantics**: a Scryfall Legacy-legality transition opens a candidate immediately as
  detection evidence; a WotC Legacy announcement enriches the same candidate with attribution and
  effective date. Signal-one-only evidence stays explicitly `detected`, not corroborated. WotC
  “no changes” is clear only after the expected page parsed successfully.
- **Machine state, not curated truth**: the last-good legality baseline, WotC calendar cursor,
  release observations, candidates, and acknowledgement hashes live in one atomically replaced
  `data/ops/state/format-monitor.json`. This file is recoverable operational state and is never
  mixed into the fail-loud curated ban ledger.
- **Stable identity and acknowledgement**: a legality candidate id is SHA-256 over
  `legacy`, canonical oracle identity (falling back to normalized name), prior legality, and new
  legality; observation time is not part of the key. Acknowledgement records the candidate's
  current evidence hash. Unchanged evidence remains suppressed; materially new evidence (for
  example WotC corroboration) changes the hash and resurfaces the candidate.
- **Transition coverage**: detect every change among Scryfall's closed legality vocabulary. The
  current confirmation path supports `legal -> banned` only. Reversals or unexpected Legacy
  `restricted` transitions remain pending with an explicit “unsupported acceptance path” action;
  the monitor must not force them into the cumulative ban model.
- **No false clear**: each signal reports `clear`, `pending`, `not_due`, or `unavailable` separately.
  Fetch, schema, parse, and baseline errors retain the prior last-good observation and render
  unavailable; they never advance the baseline or become a zero-change result.
- **Release ownership**: retain `ingestion.releases` as the set scanner and the card-table ingest
  diff as authoritative new-card evidence. Extend the composed refresh result additively with typed
  release observations so monitoring does not issue a duplicate `/sets` request.
- **Scheduling and concurrency**: monitoring runs inside the existing scheduled-refresh `flock`,
  after the composed decision refresh has produced its source observation and before terminal job
  status is published. It has no second LaunchAgent, lock, scheduler, or independent daemon.
- **WotC adapter**: use a small standard-library HTML/text extractor around fixed Legacy/effective/
  next-announcement phrases, not a new parser dependency. Zero matching Legacy blocks, ambiguous
  card actions, or missing expected structure is a named parser-contract failure. A stored next
  announcement date controls probing; before it the state is `not_due`, while due-date URL probes
  use a bounded date window and fail unavailable rather than treating 404 as “no changes.”
- **Scryfall prerequisite**: repair the live `jsonl_download_uri` gzipped-JSONL contract before
  implementing the monitor. The oracle and prices paths share one streamed, validated, atomic
  download helper; legacy JSON-array fixtures remain readable, but the removed metadata field is
  not silently assumed.
- **UI**: no mockups. This extends the existing `ops status` audit-line surface and adds an
  acknowledgement CLI leaf; it creates no visual screen or user flow.
- **Scope guard**: no Modern profile or ingestion, hot spare, Card Kingdom prices, rules IR,
  sideboard model, or automatic B&R registration enters this feature.

## Architectural choice

Three shapes were considered. Folding all monitoring into `ingestion.scryfall` would make external
adapters own acknowledgement and operator state. A separate monitor daemon/status system would
duplicate the sibling feature's scheduling, locking, and health semantics. Choose a small
`legacy_engine.ops.format_monitor` orchestration module over pure detectors in `ingestion`: external
Scryfall/WotC/release observations enter through typed ports, candidate/state transitions are pure,
and the existing scheduled runner owns persistence and projection.

The trickiest unit is the two-generation legality transaction. A successful candidate snapshot is
fully parsed and validated before diffing; candidates are merged without losing acknowledgements;
then the new last-good baseline and merged candidates are published in one atomic state write. Any
download, decompression, validation, or write failure leaves the prior baseline intact and returns
`unavailable`. This makes “no transition” affirmative evidence from two valid generations, not an
absence accidentally manufactured by an upstream failure.

## Implementation Units

### Unit 1: Repair the Scryfall bulk JSONL contract

**Files**: `src/legacy_engine/ingestion/scryfall.py`, `tests/test_scryfall.py`

**Story**: `epic-data-autonomy-format-monitoring-scryfall-jsonl-contract`

```python
def _bulk_download_uri(meta: dict[str, object]) -> str: ...
def _download_bulk_jsonl(
    client: httpx.Client, *, meta: dict[str, object], destination: Path,
) -> tuple[int, str | None]: ...
def iter_bulk_rows(path: Path) -> Iterator[dict[str, object]]: ...
```

**Implementation Notes**:

- Require non-empty `jsonl_download_uri`, validate its Scryfall-owned host, stream raw gzip bytes to
  a same-directory temporary file, validate every nonblank JSONL row as an object, then atomically
  replace the raw mirror. Continue reading existing JSON arrays so checked-in/test caches remain
  usable during migration.
- Reuse the helper for oracle, all-cards, and prices downloads without changing their public paths
  or metadata provenance. Do not load the 77 MB compressed prices payload into memory.
- A missing URI, corrupt gzip, invalid row, or implausibly empty payload raises a specific error and
  leaves the prior mirror and metadata untouched.

**Acceptance Criteria**:

- [ ] Recorded metadata containing only `jsonl_download_uri` refreshes oracle and price mirrors.
- [ ] Gzipped JSONL and legacy JSON-array mirrors iterate to identical ordered card objects.
- [ ] Host validation occurs before download and corrupt/incomplete candidates never replace the
      last-good mirror or metadata.

### Unit 2: Typed monitor state and pure legality candidate transitions

**Files**: `src/legacy_engine/ops/format_monitor.py`, `src/legacy_engine/config.py`,
`tests/test_format_monitor.py`

**Story**: `epic-data-autonomy-format-monitoring-legality-state-diff`

```python
class SignalState(StrEnum):
    CLEAR = "clear"
    PENDING = "pending"
    NOT_DUE = "not_due"
    UNAVAILABLE = "unavailable"

class CandidateDisposition(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CONFIRMED = "confirmed"

class LegalityObservation(LegacyEngineModel):
    oracle_id: str | None
    name: str
    legacy: Literal["legal", "not_legal", "restricted", "banned"]

class MonitorEvidence(LegacyEngineModel):
    source: Literal["scryfall", "wotc", "scryfall_sets", "card_diff"]
    source_url: str
    observed_at: datetime
    effective_date: date | None = None
    detail: str

class FormatCandidate(LegacyEngineModel):
    candidate_id: str
    kind: Literal["legality", "release"]
    subject_id: str
    subject_name: str
    prior_value: str | None
    current_value: str
    disposition: CandidateDisposition
    evidence: tuple[MonitorEvidence, ...]
    evidence_hash: str
    acknowledged_evidence_hash: str | None = None
    unsupported_acceptance_reason: str | None = None

class FormatMonitorState(LegacyEngineModel):
    schema_version: Literal[1] = 1
    last_good_legalities: tuple[LegalityObservation, ...] = ()
    candidates: tuple[FormatCandidate, ...] = ()
    next_wotc_announcement: date | None = None
    last_good_wotc_url: str | None = None
    updated_at: datetime

def extract_legacy_legalities(rows: Iterable[dict[str, object]]) -> tuple[LegalityObservation, ...]: ...
def merge_legality_observation(
    state: FormatMonitorState, *, observed: tuple[LegalityObservation, ...],
    evidence: MonitorEvidence, registered_events: tuple[tuple[date, str, str], ...],
) -> FormatMonitorState: ...
def acknowledge_candidate(state: FormatMonitorState, candidate_id: str) -> FormatMonitorState: ...
def load_monitor_state(path: Path) -> FormatMonitorState | None: ...
def write_monitor_state(path: Path, state: FormatMonitorState) -> None: ...
```

**Implementation Notes**:

- Validate duplicate oracle ids/names and the closed legality vocabulary before diffing. First run
  establishes a labeled baseline without inventing historical candidates.
- Merge evidence deterministically and preserve acknowledgements only while the evidence hash is
  unchanged. A registered `(effective_date, card)` retires the matching ban candidate; no fuzzy
  name matching mutates state.
- Use the sibling status module's atomic same-directory writer mechanics (extract a generic bytes
  helper if needed), but keep monitor state separate from `JobStatus`.

**Acceptance Criteria**:

- [ ] First valid snapshot is baseline-only; successive legal-to-banned, banned-to-legal, and
      unexpected-vocabulary cases have explicit deterministic outcomes.
- [ ] Repeating identical evidence creates no duplicate candidate and preserves acknowledgement;
      added WotC evidence resurfaces it once.
- [ ] Invalid/unavailable observations leave the exact previous state readable and cannot report
      clear.
- [ ] A matching operator-confirmed ledger event retires a ban candidate, while unsupported
      reversals remain visible rather than being coerced into `append_ban_event`.

### Unit 3: WotC attribution, release observation, and monitor composition

**Files**: `src/legacy_engine/ingestion/ban_monitor.py`,
`src/legacy_engine/ingestion/releases.py`, `src/legacy_engine/workflows/decision_refresh.py`,
`src/legacy_engine/ops/format_monitor.py`, `tests/test_ban_monitor.py`,
`tests/test_releases.py`, `tests/test_decision_refresh.py`, `tests/test_format_monitor.py`

**Story**: `epic-data-autonomy-format-monitoring-attribution-release`

```python
class WotcLegacyAction(LegacyEngineModel):
    card: str
    action: Literal["banned", "unbanned", "restricted", "unrestricted"]

class WotcAnnouncement(LegacyEngineModel):
    source_url: str
    effective_date: date
    legacy_actions: tuple[WotcLegacyAction, ...]
    legacy_no_changes: bool
    next_announcement: date | None = None

class FormatMonitorPorts(Protocol):
    def oracle_rows(self) -> Iterable[dict[str, object]]: ...
    def fetch_wotc(self, url: str) -> str: ...

class FormatMonitorResult(LegacyEngineModel):
    legality_state: SignalState
    wotc_state: SignalState
    release_state: SignalState
    candidates: tuple[FormatCandidate, ...]
    pending_actions: tuple[str, ...]
    unavailable_reasons: tuple[str, ...]

def parse_wotc_legacy_announcement(html: str, *, source_url: str) -> WotcAnnouncement: ...
def run_format_monitor(
    ports: FormatMonitorPorts, *, state_path: Path, observed_at: datetime,
    release_scan: ReleaseScan | None, release_scan_reason: str | None,
    card_diff: IngestDiff | None, registered_events: tuple[tuple[date, str, str], ...],
) -> FormatMonitorResult: ...
```

**Implementation Notes**:

- Parse normalized text scoped to the Legacy section; require exactly one effective-date result
  and either explicit no-change text or unambiguous actions. The adapter supplies HTTP timeout,
  user agent, resolved source URL, and response status; pure parsing never performs I/O.
- Probe only when due according to the stored calendar cursor. Use the documented slug with a
  bounded date window; before due return `not_due`. Once due, exhaustion, ambiguity, or page-shape
  drift is `unavailable`, not no-change.
- Evolve `SourceRefreshResult`/`FormatAwareness` additively with typed release scan/card-diff
  evidence. A set crossing into recent plus actual new card names creates/updates a release
  candidate; set metadata alone stays advisory. Preserve source URL, observed time, and release date.

**Acceptance Criteria**:

- [ ] Hermetic WotC fixtures cover Legacy ban, explicit no-change, next-date extraction, unrelated
      formats, ambiguous actions, missing effective date, 404 window exhaustion, and phrasing drift.
- [ ] Signal-one-only candidates are pending/detected; matching WotC attribution enriches the same
      stable candidate rather than duplicating it.
- [ ] Release status distinguishes upcoming metadata, recent-with-no-card-diff, and confirmed new
      card ingest, while unavailable set scans preserve last-good evidence.
- [ ] No monitor path imports or calls `append_ban_event`.

### Unit 4: Scheduled-runner, status, acknowledgement, and documentation integration

**Files**: `src/legacy_engine/ops/scheduled_refresh.py`, `src/legacy_engine/ops/status.py`,
`src/legacy_engine/cli.py`, `tests/test_scheduled_refresh.py`, `tests/test_ops_status.py`,
`tests/test_ops_cli.py`, `README.md`, `docs/ARCHITECTURE.md`

**Story**: `epic-data-autonomy-format-monitoring-ops-integration`

```python
def format_monitor_audit_lines(result: FormatMonitorResult, *, brief: bool = False) -> tuple[str, ...]: ...

@ops.group("monitor")
def ops_monitor() -> None: ...

@ops_monitor.command("acknowledge")
def ops_monitor_acknowledge(candidate_id: str, state_path: str | None, verbose: bool) -> None: ...
```

**Implementation Notes**:

- Invoke `run_format_monitor` while the scheduled-refresh lock is held. Merge open/unacknowledged
  candidate summaries and every unavailable reason into terminal `JobStatus.pending_actions`;
  monitor unavailability makes an otherwise-successful refresh `degraded`, never failed after a
  last-good ranking was safely written.
- Extend full/brief `ops status` output with per-signal state and attributable candidate ids. The
  acknowledgement leaf changes only monitor state, uses exact ids, and writes atomically.
- Document detection versus authority, how to acknowledge, how `eras confirm` resolves a supported
  candidate, and how to diagnose unavailable WotC/Scryfall/release signals. Regenerate knowledge
  indexes through the owning workflow after docs change.

**Acceptance Criteria**:

- [ ] The monitor executes under the same lock before terminal status publication and adds no
      launchd job or overlapping network run.
- [ ] Clear, not-due, pending, acknowledged, unavailable, and confirmed/retired cases render
      distinct `// ` audit lines; brief session output never hides unavailable signals.
- [ ] Exact acknowledgement suppresses only unchanged evidence and an unknown id fails loudly.
- [ ] A monitor outage preserves the ranking result but produces degraded job health with a named
      recovery action.

## Implementation Order

1. **Scryfall JSONL contract** — first because both refresh and legality detection otherwise fail at
   the external boundary.
2. **Monitor state/diff core** — establishes stable identity, atomic last-good, and acknowledgement
   semantics before adding another external parser.
3. **Attribution/release composition** — enriches the proven core with WotC and existing release
   observations.
4. **Operations integration** — exposes the settled result under the sibling's lock/status surface,
   then aligns current documentation.

## Testing

- `tests/test_scryfall.py`: recorded bulk metadata, streamed gzip JSONL, legacy-array compatibility,
  URI validation, atomic prior-mirror preservation, and corrupt/empty candidates.
- `tests/test_format_monitor.py`: pure snapshot/candidate transitions, stable ids, evidence hashing,
  acknowledgement/resurface, confirmed retirement, unsupported reversal, atomic persistence, and
  all signal-state combinations with an injected clock.
- `tests/test_ban_monitor.py`: fixture-driven parser and URL-window scheduling; no network.
- `tests/test_releases.py` / `tests/test_decision_refresh.py`: typed release evidence passes through
  the existing single `/sets` scan and card diff without changing the required-step ordering.
- `tests/test_scheduled_refresh.py` / `tests/test_ops_status.py` / `tests/test_ops_cli.py`: same-lock
  ordering, degraded-not-failed monitor outages, pending-action projection, acknowledgement, and
  exact brief/full audit lines using temporary paths and injected ports.
- Run focused tests first, then the full suite. Live network calls and the operator's real state,
  database, LaunchAgent, and curated ban ledger are forbidden in tests.

## Risks

- **Scryfall identity gaps**: older fixtures or multiface rows may lack `oracle_id`.
  **Fallback**: normalized canonical name is an explicit lower-quality identity; collisions fail
  unavailable rather than merging silently.
- **Transient legality glitch**: a false flip can open a candidate that WotC never corroborates.
  **Fallback**: detection-only labeling plus exact acknowledgement suppresses the unchanged alert;
  it never changes accepted legality.
- **WotC markup/URL drift**: fixed phrasing or slug rules can change.
  **Fallback**: strict parser errors and due-window exhaustion remain unavailable, while Scryfall and
  era alarms continue as independent detection signals.
- **State loss or partial write**: corrupting the baseline could fabricate a large diff.
  **Fallback**: validated candidate snapshots plus atomic replace preserve last-good state; invalid
  state requires operator recovery and reports unavailable.
- **Evidence arrives out of order**: WotC may publish before Scryfall flips or vice versa.
  **Fallback**: stable candidate correlation merges later evidence and re-alerts exactly once when
  the evidence hash changes.
- **Acceptance-model mismatch**: Legacy could unban a card, which the cumulative ledger cannot
  represent. **Fallback**: keep the reversal pending with an unsupported-path reason and require a
  separately designed ledger evolution; never force it through `eras confirm`.
- **Least certain**: WotC's future announcement URL/date convention may drift despite the current
  stable examples. The bounded probe and loud unavailable state are intentionally more important
  than clever scraping recovery.

## Implementation result

All four child stories are complete. The composed implementation repairs Scryfall's live gzipped
JSONL contract, persists atomic last-good monitor state, correlates Scryfall/WotC evidence in either
arrival order, carries the existing typed release observation/card diff through the decision
refresh, and runs detection under the existing scheduler lock. Status preserves distinct
clear/pending/not-due/unavailable signals; exact acknowledgement suppresses only an unchanged
evidence hash. No monitor path mutates `data/banlist/events.json`, and `eras confirm` remains the
only supported acceptance authority.

No Modern deployment, additional scheduler, live LaunchAgent installation, hot spare, price
provider, rules IR, or sideboard model was added.

## Verification

- Focused format-monitor integration: `59 passed`.
- Full repository suite: `PYTHONPATH=. uv run pytest -q` → `3796 passed, 1 skipped`.
- Ruff on all changed modules except the pre-existing monolithic CLI findings: clean. The CLI's
  repository-wide F821/F541 findings predate and are outside this feature's exact changes.
- Knowledge-index regeneration: 0 errors; 6 existing structural warnings.

## Other agent review

A read-only different-model advisory pass challenged the design against the research and current
code. It identified the still-broken oracle JSONL path, the strings-only job pending-action seam,
candidate acknowledgement versus confirmation, reversal handling, WotC parser drift, and baseline
atomicity. The design accepts those findings through the first prerequisite story, a separate typed
monitor-state contract, evidence-hash acknowledgement, explicit unsupported transitions, and strict
unavailable semantics. It rejects a separate daemon and direct writes to curated ban truth because
both violate existing project boundaries.

## Review findings (2026-08-12)

Effective weight: standard; one independent GPT-5.6 Sol pass. Closure needs fix verification only,
not another independent pass.

Receiver-confirmed current-cycle blockers are tracked in child story
`epic-data-autonomy-format-monitoring-review-corrections`: reject truncated bulk candidates using
the provider's declared object count; serialize monitor acknowledgement with scheduled state
transactions; match confirmations by card and effective date; extend SIGTERM terminalization
through monitoring; persist candidate identities/dispositions in status; validate and retain the
resolved WotC URL; and correct the stale automated-detection/manual-acceptance architecture label.
All findings are resolved in the completed correction story; standard-weight closure requires only
the recorded focused and full verification, not another independent pass.
