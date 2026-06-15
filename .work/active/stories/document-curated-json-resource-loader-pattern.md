---
id: document-curated-json-resource-loader-pattern
kind: story
stage: done
tags: [patterns]
parent: null
depends_on: []
release_binding: null
gate_origin: patterns
created: 2026-06-14
updated: 2026-06-15
---

# Document `curated-json-resource-loader` pattern (gate-patterns)
New recurring shape (3 occurrences, distinct from json-ssot-rebuildable-duckdb-table): a curated human-editable JSON shipped as a package resource (path = a `config.py` `*_PATH` under PACKAGE_DATA_DIR), read by a standalone `load_X(path) -> validated structure` that validates per-entry + raises ValueError with the offending path/index, plus a module-level `_load_default_*()` that resolves the config path and degrades to empty on error.
Occurrences: `advisory/sideboard.py:301` load_hoser_catalog (+_load_default @574), `archetype/variants.py:25` load_variant_registry, `analytics/players/identity.py:51` load_alias_map. Add to `.agents/skills/patterns/` + the `.claude/rules/patterns.md` digest.

## Resolution (2026-06-15)
Wrote `.agents/skills/patterns/curated-json-resource-loader.md` (full frontmatter + shape +
3-occurrence table + when/when-not, cross-linked to json-ssot-rebuildable-duckdb-table and
constants-only-config) and added the one-line digest entry to `.claude/rules/patterns.md`. No
`.claude/skills/patterns/` mirror exists, so none to sync; patterns live outside `docs/` so the
knowledge index is unaffected.
