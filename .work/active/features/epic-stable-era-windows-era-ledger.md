---
id: epic-stable-era-windows-era-ledger
kind: feature
stage: done
tags: [analytics, ingestion]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-detection]
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Era ledger: persistence, attribution, drift alarm, explainability

## Brief

Turns the detection engine's output into the engine's persistent, explainable era layer. An
offline labeling pass (sibling to `label` and `discover run`, re-run at refresh) persists
per-entity `stable_since` + full boundary metadata (date, signal type, magnitude,
p-value/posterior, attribution, confidence) as a rebuildable derived store with staged-candidate
provenance discipline. Attribution snaps each accepted boundary to the ban/release ledger within
tolerance ("ban: Candelabra of Tawnos" / "release: Flow State adoption") and labels the rest
"unattributed disturbance — possible unregistered B&R change". The drift alarm is the unattributed
case on a high-share entity: it surfaces loudly at refresh time and in affected outputs, and the
human confirmation loop (confirm → append to BAN_EVENTS → regime table heals) closes the absorbed
bug-banlist-regime-gap — Candelabra is the first ground-truth case and its confirmed registration
lands here. Explainability surface mirrors `report affectedness`: a CLI leaf that walks an
entity's boundary derivations (per-signal evidence, the exact `explain_valid_since` shape), plus
per-entity era listing.

Does NOT change any consumer's windowing (that is `-consumption`) and does not decide camp
discovery behavior (that is `-discovery-gate`).

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: the persistence/attribution layer between detection and every consumer.

## Inherited design decisions

- Self-heal gate — auto-truncate, labeled: confirmation upgrades labels and updates BAN_EVENTS;
  it never gates truncation.
- Honest-degrade: every boundary carries named trigger + confidence; unattributed = loud label,
  not a block.

## Research briefs

- `docs/briefs/change-point-detection.md` §7 (integration: persistence as offline labeling pass,
  the banlist-currency loop, explain-stable_since shape).

## Foundation references

- `docs/ARCHITECTURE.md` — ingestion/banlist.py (BAN_EVENTS SSOT), analytics/trends.py
  (regime_windows derives from BAN_EVENTS), analytics/affectedness.py (`explain_valid_since` — the
  explanation-record model).
- Patterns: json-ssot-rebuildable-duckdb-table (boundary store), audit-echo-comment-lines (alarm +
  provenance output), honest-degrade-marker, curated-json-resource-loader (if ledger confirmations
  are curated JSON).

## Design decisions

Resolved with judgment under autopilot (2026-07-11):

- **BAN_EVENTS migrates to package-shipped curated JSON** (`curated-json-resource-loader` pattern,
  same location convention as the hoser catalog) with the module API unchanged — `BAN_EVENTS`
  stays importable, now bound once at import from the JSON. This gives the confirmation loop a
  data path (`eras confirm` appends an event) instead of editing Python; regime_windows +
  affectedness heal automatically since both derive from BAN_EVENTS. Candelabra's 2026-06-29
  registration lands through exactly this path as the validation case.
- **Derived store = rebuildable DuckDB table `entity_eras`** (JSON-SSOT-rebuildable pattern:
  the corpus is the source of truth; `eras run` = DROP→schema→recompute→load idempotent pass,
  sibling of `label`/`discover run`). Row = entity, parent, stable_since, inherited flag, plus a
  serialized boundaries payload (date, signals, magnitude, p, bh_accepted, floor_rejected,
  attribution, evidence).
- **Attribution tolerance**: a detected boundary snaps to a BAN_EVENTS date or a recent-release
  window within ±14 days ("ban: <card>" when the entity ran the card ≥25% pre-ban — reuse the
  affectedness threshold; "release: <card> adoption" when an S1 adopt trigger card's printing is
  in the window); otherwise "unattributed disturbance — possible unregistered B&R change".
- **Drift alarm = BOCPD tail check at `eras run` time** for entities above 2% field share:
  Beta-Binomial BOCPD on the share series; alarm when recent p_change exceeds the alarm bar
  AND no attributed accepted boundary already covers it. Alarm prints as `// ⚠` audit lines and
  is persisted on the entity row so consumers can degrade honestly.
- **CLI**: new `eras` group — `eras run|list|explain|confirm` per the nested-groups pattern
  (`_setup_logging` first, `--db`, `--provenance` where meaningful, audit `//` lines).
  `explain <entity>` mirrors `report affectedness`'s per-event derivation walk.

## Implementation Units

### Unit A: BAN_EVENTS → curated JSON (banlist events loader)
**File**: `src/legacy_engine/ingestion/banlist.py` + `src/legacy_engine/data/banlist/events.json`
**Story**: `epic-stable-era-windows-era-ledger-store`
`events.json`: `[{"date": "YYYY-MM-DD", "card": str, "reason": str}, ...]` (the 12 current
BAN_EVENTS verbatim). Loader `load_ban_events(path) -> tuple[tuple[date, str, str], ...]`
fail-fast citing path/key; `_load_default_ban_events()` binds `BAN_EVENTS` at import
(curated-json-resource-loader). `append_ban_event(date, card, reason, *, path)` for the confirm
loop (validates no duplicate (date, card); keeps file sorted by date). Path constant in
config.py. ALL existing BAN_EVENTS consumers and tests stay green untouched.
**AC**: existing banlist/affectedness/trends tests pass unchanged; loader fail-fast test; append
round-trips.

### Unit B: entity_eras store
**File**: `src/legacy_engine/analytics/eras/store.py`
**Story**: `epic-stable-era-windows-era-ledger-store`
`init_eras_schema(con)`, `write_entity_eras(con, eras: dict[str, EntityEras], attributions, alarms, *, run_meta)` (DROP→CREATE→INSERT idempotent), `read_entity_eras(con) -> dict[str, StoredEntityEras]`, `stable_since_map(con) -> dict[str, str | None]` (the consumption feature's entry point). Boundaries+signals serialized as a JSON column; attribution + alarm flags first-class columns.
**AC**: write→read round-trip preserves everything; rebuild idempotent; stable_since_map matches ensemble output; hermetic tmp-DB tests.

### Unit C: attribution
**File**: `src/legacy_engine/analytics/eras/attribution.py`
**Story**: `epic-stable-era-windows-era-ledger-run`
`attribute_boundaries(eras, *, ban_events, releases, series, tolerance_days=14) -> dict[(entity, date), Attribution]`; Attribution = frozen dataclass {kind: "ban"|"release"|"unattributed", card: str|None, detail: str}. Ban: event within tolerance AND entity ran the card >=25% in pre-boundary buckets (compute from series card_incl when the card is in the flex band; else fall back to date-match only with detail noting unverified inclusion). Release: S1 adopt trigger_card whose set release date (injected list) is within tolerance. Closed-vocab kind.
**AC**: Candelabra-style cliff + injected event → "ban"; Flow-State-style adopt + injected release → "release"; no match → "unattributed"; tolerance boundary test.

### Unit D: eras run pass + drift alarm
**File**: `src/legacy_engine/analytics/eras/run.py`
**Story**: `epic-stable-era-windows-era-ledger-run`
`run_eras(con, *, provenance=None, alpha=0.05, seed=0) -> ErasRunResult` — build_entity_series → detectors (S1..S3 + S4 corroborate) → derive_eras → attribute_boundaries (ban_events from banlist.BAN_EVENTS, releases via injected callable defaulting to a no-network stub reading the cards table's release dates if available, else empty) → drift alarm (BOCPD p_change on the share series tail for entities with field share >= 2%; alarm if max p_change over the last 3 complete buckets >= _ALARM_BAR (calibrate on Tron fixture: must fire; stable fleet: must not) and not covered by an attributed accepted boundary within tolerance) → write_entity_eras. Returns a result object with per-entity summary + alarm list for the CLI to render.
**AC**: end-to-end on a hermetic tmp DB (synthetic corpus with an implanted cliff): boundary detected, attributed via injected event, persisted, alarm fires for an unattributed implant; deterministic.

### Unit E: eras CLI group
**File**: `src/legacy_engine/cli.py`
**Story**: `epic-stable-era-windows-era-ledger-cli`
`eras run [--db --provenance --alpha]` (renders per-entity lines + `// ⚠` alarms), `eras list [--db]` (entity, stable_since, trigger, tier of post-boundary sample), `eras explain ENTITY [--db]` (per-boundary derivation walk: signals, magnitude, p, BH verdict, floor, attribution — the explain_valid_since analog), `eras confirm DATE CARD REASON [--events-path]` (append_ban_event + echo the healed regime window; audit lines). All output uses `// ` audit-echo prefix for provenance/status lines.
**AC**: hermetic CLI tests via tmp-DB builder with --db (never default DB); confirm round-trip visible in a subsequent explain/attribution; unknown entity → clear ClickException.

## Implementation Order
1. Unit A+B (story -store) — the data paths everything else writes/reads
2. Unit C+D (story -run) — attribution + the pass + alarm
3. Unit E (story -cli) — the user surface

## Risks
- **Release-date source**: cards table may lack set release dates → attribution's release path
  degrades to trigger-card-only with detail noting the gap (honest-degrade), injected callable
  keeps it testable. Fallback: BAN_EVENTS-only attribution still covers the headline cases.
- **Alarm calibration**: single _ALARM_BAR constant pinned by the Tron fixture + stable fleet —
  same window-edge guard style as detection.
