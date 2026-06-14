---
id: document-bundle-patterns
kind: story
stage: drafting
tags: [patterns]
parent: null
depends_on: []
release_binding: null
gate_origin: patterns
created: 2026-06-13
updated: 2026-06-13
---

# Document 4 new patterns (gate-patterns)

Propose to `.agents/skills/patterns/` (+ digest in .agents/rules/patterns.md):
1. advisory-window-resolution-block — the per-leaf con→resolve_advisory_window→_echo_window→
   build_advisory_inputs→finally:close spine (13 call sites).
2. audit-echo-comment-lines — `//`-prefixed stdout provenance/degrade/window lines (35 uses).
3. honest-degrade-marker — thin/absent signal → labeled banner/note/degraded-flag/explicit-null, named
   reason, suppressed magnitude (window.py banner, primer/sideboard degraded note, speculation PRE-DATA
   banner, prices all_null/unpriced, venue divergence note) — the defining shape of the epic.
4. json-ssot-rebuildable-duckdb-table — raw JSON SSOT + drop→schema→reload idempotent rebuild (collection,
   prices, cards).

