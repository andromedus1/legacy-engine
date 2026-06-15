---
id: document-bundle-patterns
kind: story
stage: done
tags: [patterns]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: patterns
created: 2026-06-13
updated: 2026-06-14
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

## Resolution

Wrote 4 pattern docs to `.agents/skills/patterns/`:
- `advisory-window-resolution-block.md` — the 5-step spine with step roles, ~13 call sites, and
  canonical examples from cli.py:1970 and cli.py:2586.
- `audit-echo-comment-lines.md` — the `// ` comment-prefix convention, 7 categories with line refs,
  ~53 uses in cli.py (actual count via grep).
- `honest-degrade-marker.md` — all 5 instantiations of the pattern (thin-regime banner, degraded
  matchup plan, PRE-DATA FORECAST, all_null prices, venue divergence) with exact file:line citations
  from window.py:113, sideboard.py:1451, speculation.py:71, prices.py:392, cli.py:1579.
- `json-ssot-rebuildable-duckdb-table.md` — the split contract, 4-function shape, 3 canonical
  instances (ingestion/store.py:318+378, collection/store.py:202).

Added digest entries for all 4 patterns to `.claude/rules/patterns.md` (no `.agents/rules/patterns.md`
exists in this project — only `.claude/rules/` is present).

