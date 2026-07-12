---
id: epic-stable-era-windows-consumption
kind: feature
stage: implementing
tags: [analytics, advisory]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-era-ledger]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# stable_since as the default horizon across all regime-windowed surfaces

## Brief

The consumption swap: `stable_since` replaces ban-only `valid_since` as the adaptive-matrix
horizon (`build_adaptive_matrix` cells source over `[max(stable_since(a), stable_since(b)), now)`),
with honest degrade to the ban-only horizon when detection is thin/uncertain for an entity. Camp
labels resolve to their OWN stable_since where the camp cleared detection's density floor,
falling back to the parent's (today `_base_archetype` always falls back — per-camp horizons are
new capability). Every cell carries its detected window + named trigger; the `_adaptive_audit`
line and the advisory-window-resolution block's `// audit` output extend to name disturbances
("Doomsday since 2026-04-20: Flow State adoption"). Scope reaches ALL regime-windowed surfaces
(epic decision): the ~15 advisory-window call sites in cli.py, the `_latest_regime_window`
consensus/card-frequency family (a new-era archetype's consensus windows at its stable_since),
and the FIELD: `build_global_field`'s "current regime" boundary becomes detection-derived (a
confirmed high-share disturbance opens a new global field era) instead of BAN_EVENTS-only.

Display estimates keep the existing flat-0.5 shrinkage in this feature — the hierarchical prior
lands in `-shrinkage` (same release, one user-visible shift; in-tree goldens may re-pin twice).
Discovery's windowing is NOT here (see `-discovery-gate`).

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: the consumer swap — the epic's user-visible payoff; depends on the persisted
  era ledger.

## Inherited design decisions

- stable_since is the NEW DEFAULT horizon, honest degrade (scope decision).
- Scope reach: ALL regime-windowed surfaces (scope decision).
- Field window — global, detection-derived (design decision).
- Self-heal gate — auto-truncate, labeled (design decision).

## Research briefs

- `docs/briefs/change-point-detection.md` §7 (consumption seam, audit-line extension, fallback
  asymmetry: uncertainty degrades the WINDOW claim, never silently changes the number).

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/matchup.py (`build_adaptive_matrix`, `AdaptiveMatrix.
  cell_windows`), advisory/window.py (`resolve_advisory_window`, `build_advisory_inputs`),
  advisory/field.py (`build_global_field`), generation/consensus.py (`_latest_regime_window`).
- Patterns: advisory-window-resolution-block (the ~15-site block being re-pointed),
  audit-echo-comment-lines, honest-degrade-marker, freshness-stripped-cli-body-golden (goldens
  will re-pin), opt-in-analytics-overlay (contrast: this is deliberately NOT opt-in — epic
  decision).

## Design decisions

Resolved with judgment under autopilot (2026-07-11):

- **The swap concentrates in window.py/matchup.py.** The ~15 advisory CLI sites all route through
  `resolve_advisory_window` + `build_advisory_inputs`; changing the adaptive branch there updates
  every site without touching them individually. Only the `_latest_regime_window` consensus/
  card-frequency family (4 cli.py sites) needs per-site edits.
- **Horizon resolution order** (per entity label): exact era entry ("Parent [variant]" camp labels
  match the eras entity vocabulary) → parent's era entry (camps) → ban-only `valid_since`
  (absent key = never analyzed, per stable_since_map's documented semantics) . Present-with-None
  = full history (analyzed, undisturbed — the epic's maximal-solid-window payoff).
- **Whole-path degrade**: entity_eras table missing/empty → the adaptive path falls back to
  ban-only horizons with one loud audit line ("// eras: no era data — ban-only horizons; run
  `eras run`"). Never silently different.
- **Audit lines carry triggers**: "Doomsday since 2026-04-20 (release: Flow State adoption)";
  unattributed accepted boundaries carry the unregistered-B&R wording; alarm-flagged entities
  emit `// ⚠` lines. Alarms alone never truncate (accepted boundaries do — epic self-heal gate).
- **Field era (detection-derived, global)**: field_since = max(current ban-regime start, latest
  accepted boundary among entities with ≥2% field share), with thin-window degrade back to the
  ban regime + banner. One global window (analysis-gates convention), self-healing.
- **Consensus windows per entity**: `generate consensus`/card-frequency surfaces window at
  [stable_since(entity), now) — None = full corpus (undisturbed composition IS solid, S2-checked);
  absent from map → current ban-regime fallback (today's behavior). Echo the window + trigger.
- **Goldens re-pin once here** (freshness-stripped CLI-body goldens change because audit lines
  and windows change); they re-pin again at `-shrinkage` — accepted in the epic pre-mortem.

## Implementation Units

### Unit 1: era-horizon adapter
**File**: `src/legacy_engine/analytics/eras/consume.py`
**Story**: `epic-stable-era-windows-consumption-adapter`
```python
@dataclass(frozen=True)
class EraHorizon:
    since: str | None          # the horizon date (None = full history)
    source: str                # "era" | "era-parent" | "ban-only"
    trigger: str | None        # "ban: X" / "release: X adoption" / "unattributed ..." / None
    alarm: str | None          # alarm note when the entity's alarm_fired

def era_horizons(con, archetypes: list[str], *, provenance=None, split_variant=None,
                 affect_threshold=0.25) -> tuple[dict[str, EraHorizon], tuple[str, ...]]:
    ...  # returns per-label horizons + audit preamble lines (incl. the no-era-data degrade line)

def resolve_field_era(con, *, provenance=None, min_share=0.02) -> tuple[str | None, str]:
    ...  # (field_since, label) — max(ban-regime start, latest accepted high-share boundary)
```
Reads `read_entity_eras`/`stable_since_map` + falls back to `archetype_valid_since`. Camp label
resolution: exact → parent → ban-only. Pure given the store reads; hermetic tmp-DB tests.
**AC**: all resolution-order branches tested; no-era-data path returns ban-only + degrade line;
field era = max rule with thin-degrade; deterministic.

### Unit 2: adaptive matrix horizon injection
**File**: `src/legacy_engine/analytics/matchup.py`
**Story**: `epic-stable-era-windows-consumption-matrix`
`build_adaptive_matrix(..., horizons: dict[str, str | None] | None = None)` — when None (default),
resolve via `era_horizons` (era-aware with ban-only fallback), preserving the existing
`archetype_valid_since`-only behavior ONLY through the adapter's fallback (no separate code path).
`AdaptiveMatrix` gains `horizon_meta: dict[str, EraHorizon]` next to `valid_since` (kept, now =
resolved horizons) and `cell_windows` unchanged. `_base_archetype` fallback still applies for camp
labels absent from both maps.
**AC**: with an empty eras table the matrix is byte-identical to pre-change output on the same
corpus (proven by a test computing both paths); with a seeded eras table the cells re-window and
`cell_windows` reflects max(horizon_a, horizon_b); existing matchup tests stay green.

### Unit 3: window resolution + audit
**File**: `src/legacy_engine/advisory/window.py`
**Story**: `epic-stable-era-windows-consumption-matrix`
`build_advisory_inputs` adaptive branch: matrix from Unit 2; field window from `resolve_field_era`
(replacing `resolve_regime("current")`); `_adaptive_audit` extended to render source/trigger/alarm
("// adaptive: per-entity era windows — Doomsday since 2026-04-20 (release: Flow State adoption);
…; 3 entities ban-only; all others full-corpus" + `// ⚠` alarm lines + the degrade preamble).
**AC**: audit lines named-trigger formatted; alarm lines surface; field window follows the max
rule; thin field degrade banner; existing advisory-window tests updated only where audit text
changed.

### Unit 4: consensus/card-frequency family
**Files**: `src/legacy_engine/generation/consensus.py`, `src/legacy_engine/cli.py` (4 call sites)
**Story**: `epic-stable-era-windows-consumption-consensus`
New `entity_era_window(con, archetype) -> tuple[since, until, label]` in consensus.py (era-aware
with `_latest_regime_window` fallback); the 4 cli.py `_latest_regime_window` sites switch to it
and echo `// window: since <date> (<trigger|'ban regime'>)` audit lines.
**AC**: undisturbed entity widens to full corpus; disturbed entity truncates at stable_since;
no-era-data = exact current behavior; hermetic CLI tests with --db tmp.

### Unit 5: golden re-pins + integration
**Files**: the pinned full-body golden tests (report matchups/subgroup defaults + any advisory
golden that includes audit lines)
**Story**: `epic-stable-era-windows-consumption-consensus`
Re-pin per the freshness-stripped-cli-body-golden pattern AFTER verifying the new bodies are
correct by inspection (window lines present, numbers plausible, no error text). Note: on a tmp
test DB with an empty eras table the goldens may be unchanged — verify which goldens actually
move and why before re-pinning.
**AC**: full suite green; each re-pinned golden's diff is explainable by (a) audit lines or
(b) window changes, never silent number drift.

## Implementation Order
1. Unit 1 (adapter) — everything hangs on the resolution semantics
2. Units 2+3 (matrix + window) — the core swap
3. Units 4+5 (consensus family + goldens) — the remaining surfaces

## Risks
- **Byte-identical fallback claim (Unit 2 AC)**: the strongest guard against silent regression —
  if it can't be met, that's a design flaw to surface, not to soften.
- **Golden churn masking real drift**: mitigated by the explainable-diff AC on Unit 5.
- **Full-history widening for undisturbed entities changes established numbers** (cells gain
  pre-regime data where no disturbance was detected): this is the epic's INTENDED semantics —
  every such cell's window is auditable via cell_windows + explain.
