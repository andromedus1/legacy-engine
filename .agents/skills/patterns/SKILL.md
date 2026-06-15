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
- [gated-additive-augmentation.md](gated-additive-augmentation.md) — extend a shipped module with an optional signal; no-op path byte-identical to baseline
- [objective-search-split.md](objective-search-split.md) — heavy DB compute once → dict; pure loop with injected `legal_swap` callable
- [two-level-empirical-bayes.md](two-level-empirical-bayes.md) — `beta_binomial_shrink_to` primitive; shrink marginal then cell toward the shrunk marginal
- [advisory-window-resolution-block.md](advisory-window-resolution-block.md) — `con→resolve_advisory_window→_echo_window→build_advisory_inputs→finally:close`
- [audit-echo-comment-lines.md](audit-echo-comment-lines.md) — provenance/window/status output via `click.echo("// ...")`
- [honest-degrade-marker.md](honest-degrade-marker.md) — thin/absent signal → labeled banner/degraded flag/explicit null + named reason
- [json-ssot-rebuildable-duckdb-table.md](json-ssot-rebuildable-duckdb-table.md) — raw JSON is SSOT; DuckDB tables are derived caches with `rebuild_*(con)`
- [viz-spec-render-write-tail.md](viz-spec-render-write-tail.md) — viz leaf ends `spec_*(_*_model(...))` → mkdir → suffix-dispatch render → wrap `ValueError` as `ClickException("Render failed: …")`
- [file-backed-cli-test-db-builder.md](file-backed-cli-test-db-builder.md) — CLI tests build a tmp DB via `_build_*_db(tmp_path)->str` and always invoke with `--db <that path>`, never the default DB
