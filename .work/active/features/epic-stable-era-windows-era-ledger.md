---
id: epic-stable-era-windows-era-ledger
kind: feature
stage: drafting
tags: [analytics, ingestion]
parent: epic-stable-era-windows
depends_on: [epic-stable-era-windows-detection]
release_binding: null
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
