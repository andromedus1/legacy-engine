---
id: gate-patterns-v0.1.0
kind: story
stage: done
tags: [patterns]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: patterns
created: 2026-06-14
updated: 2026-06-14
---

# Patterns extracted for v0.1.0

## New patterns codified
- `viz-spec-render-write-tail` — viz leaf commands end with `spec_*(_*_model(...))` → mkdir →
  suffix-dispatch `render_html_tile`/`render_png` → wrap `ValueError` as
  `ClickException("Render failed: …")` (4 occurrences in cli.py).
- `file-backed-cli-test-db-builder` — CLI tests build a tmp DuckDB via `_build_*_db(tmp_path)->str`
  (connect→init_schema→load_tournament→`UPDATE decks SET archetype`→close→return path) and always
  invoke with `--db <that path>`, never the default DB (6+ builder occurrences; 60+ `--db` invokes).

## Inconsistencies flagged
None. Bundle code is consistent with all 12 prior documented patterns.

## Pattern files written
- `.agents/skills/patterns/viz-spec-render-write-tail.md`
- `.agents/skills/patterns/file-backed-cli-test-db-builder.md`
- `.agents/skills/patterns/SKILL.md` (index regenerated — was stale at 5 entries, now lists all 14)
- `.claude/rules/patterns.md` (hook-loaded digest — 2 new entries appended)

## Note
The tracked candidate `document-curated-json-resource-loader-pattern` (deferred, unbound) was NOT
re-surfaced here — it remains on the queue for a later release.
