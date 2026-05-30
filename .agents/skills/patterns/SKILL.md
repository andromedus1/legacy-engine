---
name: patterns
description: "Project code patterns and conventions for legacy-engine. Auto-loads when implementing,
  designing, verifying, or reviewing code. Provides detailed pattern definitions with code examples."
user-invocable: false
allowed-tools: Read, Glob, Grep
---

# legacy-engine Patterns Reference

Detailed pattern documentation for this project — the conventions established by the foundation
(`package-skeleton`) feature, to be followed by all downstream work. See each file for full context
and concrete code examples.

Available patterns:
- [pydantic-base-model.md](pydantic-base-model.md) — shared models subclass `LegacyEngineModel` (Pydantic, `extra="ignore"`)
- [constants-only-config.md](constants-only-config.md) — `config.py` is constants only, zero import side effects
- [cli-nested-groups.md](cli-nested-groups.md) — Click nested groups, `_setup_logging` first, fail-loud `_not_implemented` stubs
- [pytest-factory-fixtures.md](pytest-factory-fixtures.md) — factory fixtures returning `_make_X(**kwargs)` builders; `TestX` classes; deterministic
- [confidence-metadata.md](confidence-metadata.md) — every derived stat carries `ConfidenceMetadata` + `tier_for_sample(n)`
