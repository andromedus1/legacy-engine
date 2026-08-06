---
id: epic-stable-era-windows-discovery-gate
kind: feature
stage: done
tags: [analytics, archetype]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-era-ledger]
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery temporal gate: stable-window clustering + era-mixing detection

## Brief

Closes the era-cluster confound (the absorbed idea-discovery-temporal-gate): 27/46 ranked camps
from the 18-month discovery pool were TIME clusters — new-card signatures date-stamp clusters, so
"camps" were list generations, not coexisting builds. Three deliverables: (1) `discover run`
defaults its clustering pool to the parent's detected stable window (from the era ledger), with
the previous full-pool behavior available explicitly; (2) a temporal-mixing Gate C alongside the
existing statistical and domain gates — flag/fail splits whose camps' deck-date distributions
separate strongly (e.g. median-date gap / distribution-distance thresholds), with the
honest-degrade label "camps may be list generations"; (3) per-camp %current + median date
surfaced in the discover report (cheap, immediate, the era-audit's manual diagnostics made
first-class).

Re-running the full-meta discovery sweep and re-ranking best-build on stable windows is NOT in
this feature — that is the post-epic dogfooding payoff.

## Epic context

- Parent epic: `epic-stable-era-windows`
- Position in epic: consumer of the era ledger, independent of `-consumption` — parallelizable
  with it.

## Inherited design decisions

- Detect parent change points FIRST, then discover camps within stable windows; Gate C is the
  backstop for splits that still straddle a boundary (epic Brief + change-point brief §7).

## Research briefs

- `docs/briefs/change-point-detection.md` §7 (sequencing with discovery).
- `docs/briefs/subarchetype-discovery.md` — the gate architecture this extends (Gate A
  statistical / Gate B domain; Gate C is temporal).

## Foundation references

- `docs/ARCHITECTURE.md` — analytics/discovery.py + archetype/discovered.py (discover
  run|list|apply|promote).
- Patterns: honest-degrade-marker (Gate C label), confidence-metadata.

## Design decisions

Resolved with judgment under autopilot (2026-07-12):

- **Gate C FLAGS, never fails.** A statistically-valid split whose camps' date distributions
  separate strongly carries `temporal_mixing=True` + reason "camps may be list generations" —
  surfaced-and-labeled per the epic's honesty convention (the absorbed idea said "flag/fail";
  flagging preserves the audit trail and lets `discover apply` refuse or warn downstream).
- **Deck dates ride the existing pool query** (t.date already joined); `DeckVector` gains an
  optional `date: str | None = None` field (additive, frozen-safe). Gate C compares per-camp
  date distributions: median-date gap ≥ 120 days OR a two-sample separation heuristic.
- **Era-aware default pool**: `discover run`'s default window becomes the parent's
  `entity_era_window` (stable_since / full-when-undisturbed / ban-regime fallback) instead of
  the full corpus; `--since` and a new `--all-pool` flag override. Pool window echoed.
- **Per-camp %current + median date** computed against the parent's era window and persisted on
  staged records (additive staging fields) + rendered in `discover run`/`list` output.

## Implementation Units

### Unit 1: dates + Gate C in the pure core
**File**: `src/legacy_engine/analytics/discovery.py`
**Story**: `epic-stable-era-windows-discovery-gate-core`
`DeckVector.date: str | None = None`; pool query selects `t.date`. `cluster_and_validate` gains
Gate C: per-camp median date, pairwise max median gap, `temporal_mixing: bool`, reason string;
`DiscoveredSplit` (and its camp records) gain `median_date`, `pct_current` (fraction of camp
decks ≥ a `current_since` param, None-safe), `temporal_mixing`, `temporal_note` — all additive
with defaults so existing constructors/tests stay green.
**AC**: synthetic two-generation fixture (old camp median 2025-06, new camp 2026-05) flags with
the exact label; a contemporaneous split does not flag; existing discovery tests untouched-green.

### Unit 2: era-default window + surfacing + staging persistence
**Files**: `src/legacy_engine/cli.py` (discover leaves), `src/legacy_engine/archetype/discovered.py`
**Story**: `epic-stable-era-windows-discovery-gate-surface`
`discover run` default `since` = `entity_era_window(con, archetype)` with `// pool window:` echo
(+ `--all-pool` to restore full corpus); camp lines render `median <date> · <pct>% current` and
the Gate C warning; staged candidate records persist the new fields (additive JSON keys, old
records load fine); `discover list` renders them when present.
**AC**: hermetic CLI tests (--db tmp): era-windowed default vs --all-pool; Gate C label rendered;
staged round-trip with new fields; old staged records still load.

## Implementation Order
1. Unit 1 (core) 2. Unit 2 (surface)

## Risks
- **Gate C threshold** (120-day median gap) is a heuristic: pin it as a named constant with the
  synthetic fixtures as calibration source; a real two-sample test can replace it later without
  API change.

## Implementation summary + review (2026-07-12)

2 stories (commits e3ccbae core, ecc719f surface), +17 tests then review fixes; suite 2928+1xfail.
Fresh-context review: APPROVE. Findings fixed in-tree: --all-pool now anchors %current to the
entity's ERA since (the documented diagnostic — code had silently omitted it); empty windowed
pool gets an explicit `// ⚠ pool excludes every deck` line + `// pool: N decks` count (honest
empty-pool vs no-structure distinction); undisturbed echo de-awkwarded.
