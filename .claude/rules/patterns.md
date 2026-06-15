# Project Patterns (index)

Dense one-line pointers to legacy-engine's reusable code structures. Full pattern files live in
`.agents/skills/patterns/` (canonical) and auto-load via the `patterns` skill. Follow these when
writing new code; if deviating, justify it.

- **Pydantic base model**: shared models subclass `LegacyEngineModel` (Pydantic, `extra="ignore"`, `populate_by_name`) — drop unmodeled external JSON fields, don't fail → [.agents/skills/patterns/pydantic-base-model.md](../../.agents/skills/patterns/pydantic-base-model.md)
- **Constants-only config**: `src/legacy_engine/config.py` = paths/URLs/constants, **zero import side effects**; paths root at `PROJECT_ROOT` → [.agents/skills/patterns/constants-only-config.md](../../.agents/skills/patterns/constants-only-config.md)
- **CLI nested groups + fail-loud stubs**: `@main.group()` per domain; leaf calls `_setup_logging(verbose)` first; unimplemented leaves raise `click.ClickException` via `_not_implemented(cmd)` → [.agents/skills/patterns/cli-nested-groups.md](../../.agents/skills/patterns/cli-nested-groups.md)
- **pytest factory fixtures**: shared builders are `@pytest.fixture`-returned `_make_X(**kwargs)` closures in `conftest.py`; `TestX` classes; deterministic → [.agents/skills/patterns/pytest-factory-fixtures.md](../../.agents/skills/patterns/pytest-factory-fixtures.md)
- **Confidence metadata**: every derived stat carries `ConfidenceMetadata` + `tier_for_sample(n)` (speculative <30 / evolving 30-99 / established ≥100); gate by tier → [.agents/skills/patterns/confidence-metadata.md](../../.agents/skills/patterns/confidence-metadata.md)

- **Gated additive augmentation**: extend a shipped module with a new optional signal — gate all new behavior on data presence; no-op path is byte-identical to baseline; existing tests stay green untouched → [.agents/skills/patterns/gated-additive-augmentation.md](../../.agents/skills/patterns/gated-additive-augmentation.md)
- **Objective-search split**: run heavy DB value computation once → plain dict; pass dict + injected `legal_swap` callable into a pure loop; loop is unit-testable with hand-built inputs, no DB → [.agents/skills/patterns/objective-search-split.md](../../.agents/skills/patterns/objective-search-split.md)
- **Two-level empirical Bayes**: `beta_binomial_shrink_to` is the primitive; chain: shrink per-card marginal toward global baseline, then shrink matchup cell toward the SHRUNK marginal (not raw prior) → [.agents/skills/patterns/two-level-empirical-bayes.md](../../.agents/skills/patterns/two-level-empirical-bayes.md)

- **Advisory window resolution block**: every regime-windowed command follows `con→resolve_advisory_window→_echo_window→build_advisory_inputs→finally:close` (~13 call sites in cli.py); deviating bypasses the thin-regime degrade and the audit header → [.agents/skills/patterns/advisory-window-resolution-block.md](../../.agents/skills/patterns/advisory-window-resolution-block.md)
- **Audit-echo comment lines**: all provenance/window/status/degradation output uses `click.echo("// ...")` prefix so it is grep-able and visually distinct from data rows (~53 uses in cli.py) → [.agents/skills/patterns/audit-echo-comment-lines.md](../../.agents/skills/patterns/audit-echo-comment-lines.md)
- **Honest degrade marker**: thin/absent signal → labeled banner/degraded flag/explicit null + named reason + suppressed magnitude (window.py thin-regime banner, sideboard/primer `degraded=True` note, speculation `PRE-DATA FORECAST` label, prices `all_null` flag, venue divergence) — the defining honesty shape of the project → [.agents/skills/patterns/honest-degrade-marker.md](../../.agents/skills/patterns/honest-degrade-marker.md)
- **JSON SSOT + rebuildable DuckDB table**: raw JSON is the source of truth; DuckDB tables are derived caches with a `rebuild_*(con)` = DROP→schema→reload idempotent path (collection, prices, cards) → [.agents/skills/patterns/json-ssot-rebuildable-duckdb-table.md](../../.agents/skills/patterns/json-ssot-rebuildable-duckdb-table.md)

- **Viz spec-render-write tail**: every `viz` leaf ends `spec = spec_*(_*_model(...))` → `mkdir` → suffix-dispatch `render_html_tile`/`render_png` → wrap render `ValueError` as `click.ClickException("Render failed: …")`; spec built only after `con.close()` (4 sites in cli.py) → [.agents/skills/patterns/viz-spec-render-write-tail.md](../../.agents/skills/patterns/viz-spec-render-write-tail.md)
- **File-backed hermetic CLI test DB builder**: CLI tests stand up a tmp DuckDB via `_build_*_db(tmp_path)->str` (connect→init_schema→load_tournament→`UPDATE decks SET archetype`→close→return path) and ALWAYS invoke with `--db <that path>`, never the default DB (the green-local/red-CI trap) → [.agents/skills/patterns/file-backed-cli-test-db-builder.md](../../.agents/skills/patterns/file-backed-cli-test-db-builder.md)

To document new patterns, use `/extract-patterns`.
