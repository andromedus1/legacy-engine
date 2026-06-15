---
id: epic-regime-aware-advisory-cli-surface
kind: feature
stage: done
tags: [advisory, analytics, correctness]
parent: epic-regime-aware-advisory
depends_on: [epic-regime-aware-advisory-windowing-core]
release_binding: v0.1.0
gate_origin: null
created: 2026-06-01
updated: 2026-06-14
---

# CLI Surface + Thin-Regime Degrade (v1 UX)

## Brief

The user-facing v1 surface on top of `windowing-core`: opt-in windowing flags + the honest
thin-regime fallback.

- **Flags** on the advisory/report surfaces that consume the matchup matrix / field — `report
  matchups`, `report meta` (currently un-windowed; only `trends` windows today), `report gaps`,
  and `advise *`: `--since`/`--until` (explicit window), `--regime [current|<named>]` (resolve via
  `windowing-core`'s regime resolver), and `--all-time` (explicit full-corpus). Mirror the existing
  Click option/`--db`/`try-finally`/`_setup_logging` conventions.
- **Thin-regime degrade + loud caveat** (the inherited policy): when the requested/current window is
  too thin for reliable matchup/positioning math (below a decisive-round / coverage floor — the
  12-day / 483-round post-Undercity-Informer case is the motivating example), fall back to the
  widest defensible window (full-corpus in v1) and print a **prominent banner** stating the regime
  was too thin (n=X, flagged evolving) and that wider data is shown. Always returns an answer; never
  silently, never empty.
- Echo **which window was actually used** in each command's header (auditability).

Default stays **full-corpus** in v1 (the default flip is v2). Does NOT cover the adaptive per-cell
window (→ `adaptive`) or the core plumbing (→ `windowing-core`).

## Epic context
- Parent epic: `epic-regime-aware-advisory`
- Position in epic: consumer of `windowing-core`; establishes the `--regime`/`--all-time`/window-banner
  UX that `adaptive` later re-defaults.

## Inherited design decisions
- **Full-corpus default in v1; windowing opt-in** via `--since`/`--regime`; `--all-time` is the explicit
  full-corpus escape (kept meaningful into v2 when the default flips).
- **Thin-regime = degrade + loud caveat** (fall back to widest defensible window + prominent banner;
  always returns an answer).

## Research briefs
- The epic body (`## Strategic decisions`); `docs/briefs/card-adjacency-and-discovery.md` for the
  honesty/disclaimer ethos to mirror.

## Foundation references
- `src/legacy_engine/cli.py` — `report matchups|meta|gaps`, `advise *` command group; the
  `report tiers`/`report gaps` option-shape precedent.
- `windowing-core`'s regime resolver + windowed `build_matrix`/`compute_archetype_gaps`.

## Carried-forward nit (from windowing-core review)
- `metashare.py` has stale text now that `compute_match_results` IS windowed: the module docstring (~line 4) and the windowed-`wrw` `NotImplementedError` message (~line 397) both say "match_results is not windowed". Behavior is still correct (the wrw guard stands); fix the wording during this feature's pass.

## Design decisions
Resolved with judgment (autopilot); mechanical CLI/UX choices:
- **Flag precedence** (most→least specific): `--all-time` → `(None, None)`, no degrade; else `--regime R` → `resolve_regime(R)`; else `--since/--until` (either/both); else **default = full-corpus** (v1; the default flip is v2). `--all-time` + a window flag together → `--all-time` wins (explicit escape).
- **Thin-regime gate = cheap rounds-count proxy**, not a full match-results build: `resolve_advisory_window` runs one `COUNT(*)` of rounds in the window; below `_THIN_ROUNDS_FLOOR` (default **500** — just above the observed 483 of the post-Undercity-Informer regime) → **degrade to full-corpus + banner** reporting the actual count. Round-count is a cheap honest proxy for matchup-data thinness; documented as such. `--all-time`/explicit-full-corpus never degrade.
- **Helper placement** = new `advisory/window.py::resolve_advisory_window(...)` (importable + unit-testable without the CLI; composes `analytics.trends.resolve_regime`).
- **Surfaced commands** = the matrix/field consumers: `report matchups`, `report meta`, `report gaps`, `advise positioning`, `advise report`, `advise whattoplay`. `advise sideboard` builds no matrix in the CLI (matchup work is internal to `recommend_sideboard`) → out of scope for v1 windowing; note in body.
- **Field windowing**: `_load_field` gains `since/until` threaded into its `build_global_field` (global path); a custom `--field` file is unaffected (user-specified shares).
- Each command **echoes the window used** in its header (`// window: <since>..<until>` or `full-corpus`) + the degrade banner when it fired (auditability + the inherited loud-caveat policy).

## Architectural choice
A single reusable Click option-stack (`_window_opts`, mirroring the existing `_verbose`) + one shared
`resolve_advisory_window` helper keep the 6 commands DRY and the degrade policy in ONE testable place.
Commands resolve the final window once, then build matrix/field over it (windowing-core already made
those windowable) — no per-command degrade logic. Rejected: per-command flag/degrade code (duplication,
drift); a build-then-check-then-rebuild degrade (wastes a full match-results scan — the cheap rounds
COUNT avoids it).

## Implementation Units

### Unit 1: `resolve_advisory_window` (degrade policy)
**File**: `src/legacy_engine/advisory/window.py` (new)
```python
@dataclass(frozen=True)
class WindowResolution:
    since: str | None
    until: str | None
    banner: str | None          # set when a thin requested window was degraded to full-corpus
    requested_label: str        # for the header echo ("regime: …", "2026-01-01..—", "full-corpus")

def resolve_advisory_window(
    con, *, regime: str | None = None, since: str | None = None, until: str | None = None,
    all_time: bool = False, provenance: str | None = None, thin_floor: int = 500,
) -> WindowResolution: ...
```
**Implementation Notes**: precedence per Design decisions. After resolving a non-full window, run
`SELECT count(*) FROM rounds r JOIN tournaments t ON t.id=r.tournament_id WHERE <half-open window + provenance>`;
if `< thin_floor` → return full-corpus `(None,None)` with a banner naming the count, floor, and the
degraded regime. Full-corpus / `--all-time` → no count, no banner. Reuse `trends.resolve_regime` for `--regime`.
**Acceptance Criteria**:
- [ ] `--all-time` → (None,None,banner=None).
- [ ] `--regime current` on a corpus where the current regime has < floor rounds → degrades to (None,None) with a banner reporting the count.
- [ ] A regime with ≥ floor rounds → returns its window, banner=None.
- [ ] Explicit `--since/--until` honored; precedence `all_time > regime > since/until`.

### Unit 2: `_window_opts` decorator + header echo helper
**File**: `src/legacy_engine/cli.py`
```python
def _window_opts(f):  # stacks --since/--until/--regime/--all-time (like _verbose)
    ...
def _echo_window(res: "WindowResolution") -> None:  # prints "// window: …" + banner if any
```
**Acceptance Criteria**:
- [ ] Decorated command `--help` shows `--since`, `--until`, `--regime`, `--all-time`.

### Unit 3: thread into the 6 commands
**File**: `src/legacy_engine/cli.py` (`report matchups|meta|gaps`, `advise positioning|report|whattoplay`)
**Implementation Notes**: each adds `@_window_opts`, calls `resolve_advisory_window(con, …)`, `_echo_window(res)`,
then builds with `since=res.since, until=res.until` (matrix via `build_matrix`; field via `_load_field`/`build_global_field`;
`report meta` via `compute_metashare`; `report gaps` via `compute_archetype_gaps`). `report meta` currently
loops provenance bases — thread the window into each basis call.
**Acceptance Criteria**:
- [ ] `report matchups --regime current` builds over the (possibly degraded) window and prints the window line.
- [ ] `report meta --since YYYY-MM-DD` narrows the share table.
- [ ] `advise positioning --regime <named>` ranks over that regime's matrix+field.
- [ ] No flags → full-corpus, output byte-equivalent to today (regression).

### Unit 4: `_load_field` window passthrough
**File**: `src/legacy_engine/advisory/report.py`
```python
def _load_field(con, *, field_text, provenance=None, since=None, until=None) -> FieldDistribution:
    if field_text is None:
        return build_global_field(con, provenance=provenance, since=since, until=until)
    ...  # custom field unchanged
```
**Acceptance Criteria**:
- [ ] Global field path windows; custom `--field` path unaffected.

### Unit 5: metashare doc-rot fix (carried nit)
**File**: `src/legacy_engine/analytics/metashare.py`
**Implementation Notes**: the module docstring + the windowed-`wrw` `NotImplementedError` text say
"match_results is not windowed" — now stale (it IS, as of windowing-core). Reword to: windowed `wrw` is
unsupported because `compute_match_results`' win-rate-weighting basis isn't recomputed per-window (the
guard stays). No behavior change.
**Acceptance Criteria**:
- [ ] No occurrence of the stale "match_results is not windowed" claim; the `wrw`+window guard still raises.

## Implementation Order
1. Unit 1 (`resolve_advisory_window`) — trickiest; the degrade policy.
2. Unit 4 (`_load_field`) + Unit 2 (decorator/echo) — plumbing.
3. Unit 3 (thread the 6 commands).
4. Unit 5 (doc-rot).

## Testing
### Unit tests: `tests/test_advisory_window.py` + `tests/test_cli.py` additions
- `resolve_advisory_window`: all-time; regime degrade-when-thin (build a file-db whose only regime is thin); regime not-thin; explicit since/until; precedence.
- CLI (CliRunner, file `--db`): `report matchups|meta --regime current` exit 0 + window line; `--all-time` no banner; a thin `--regime` prints the degrade banner; no-flags regression (window line says full-corpus).
- metashare: assert the stale string is gone; windowed-wrw still raises.
### Integration
- `advise positioning --regime <named>` on a seeded multi-regime file-db → ranks, prints the window, exit 0.

## Risks
- **Thin-floor = rounds-count proxy** (not decisive-matched) — slightly over-counts (draws/byes included). Acceptable for a thin/not-thin gate; the banner reports the proxy count honestly. **Fallback**: switch to a decisive count if the proxy ever mis-gates; floor is a constant.
- **Degrade hides a genuinely-current-but-thin signal** behind full-corpus — but that's the inherited policy (degrade + loud caveat), and v2's adaptive default supersedes it. **Fallback**: `--regime <name>` without degrade could be offered later; v1 keeps it simple.
- **`report meta` provenance-basis loop × window** — ensure the window threads into every basis iteration, not just the first.

## Implementation notes
- Files changed: `advisory/window.py` (new — `resolve_advisory_window` + `WindowResolution` + `_count_rounds`; `thin_floor<=0` disables degrade), `cli.py` (`_window_opts` decorator + `_echo_window`; threaded `--since/--until/--regime/--all-time` into `report matchups|meta|gaps` + `advise positioning|whattoplay|report`), `advisory/report.py` (`_load_field` + `build_field_read_report` window passthrough), `analytics/metashare.py` (doc-rot wording fix).
- Tests added: `tests/test_advisory_window.py` (15: resolve_advisory_window×7 incl thin-degrade + thin_floor=0, CLI×6, metashare-doc×2).
- Suite: 1035 passing (was 1020, +15). ruff clean on window.py/report.py/metashare.py/test; cli.py uses the established forward-ref+noqa pattern.
- Discrepancies from design: **one refinement caught by real-DB smoke** — `report meta` is deck-based, so it must NOT degrade on rounds-thinness (636 decks is plenty even when rounds are thin). Added `thin_floor<=0` to disable the rounds-degrade and applied it to `report meta`; matchup/positioning/gaps keep the default 500-round degrade. Net: `report meta --regime current` shows the honest current-regime share (tier-flagged), while `report matchups/advise --regime current` degrade with the loud banner.
- **End-to-end validated on real DB**: `report meta --regime current` → Tron 11.8% / Izzet Delver 8.5% / Energy 7.6% (evolving tier) over the post-Undercity-Informer regime; `report matchups --regime current` → "THIN: 49 rounds < floor 500 — showing FULL-CORPUS" banner. The engine now handles the new ban paradigm honestly instead of silently contradicting itself.
- Adjacent issues parked: none.

## Review record
- **Verdict: Approve** (deep lane, fresh-context Opus sub-agent — NOT cross-model; Codex out of credits). 126 tests green across touched + adjacent command suites.
- Verified: flag precedence (all_time > regime > since/until > default) incl all_time-beats-regime + resolve_regime("all")→full; degrade COUNT query byte-identical to the canonical matchup-rounds query (honest proxy); `thin_floor=0` meta carve-out sound (deck-based; per-row tiers convey thinness — not hidden); wrw-skip computed post-resolution (degraded→full correctly doesn't skip); ALL 6 command signatures carry since/until/regime/all_time (no Click TypeError); both-legs windowing (matrix + field) in all 3 advise commands; non-vacuous tests.
- No Blockers, no Important. 1 nit (module docstring didn't mention the thin_floor=0 carve-out) — fixed inline.
