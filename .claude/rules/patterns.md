# Project Patterns (index)

Dense one-line pointers to legacy-engine's reusable code structures. Full pattern files live in
`.agents/skills/patterns/` (canonical) and auto-load via the `patterns` skill. Follow these when
writing new code; if deviating, justify it.

- **Pydantic base model**: shared models subclass `LegacyEngineModel` (Pydantic, `extra="ignore"`, `populate_by_name`) — drop unmodeled external JSON fields, don't fail → [.agents/skills/patterns/pydantic-base-model.md](../../.agents/skills/patterns/pydantic-base-model.md)
- **Constants-only config**: `src/legacy_engine/config.py` = paths/URLs/constants, **zero import side effects**; paths root at `PROJECT_ROOT` → [.agents/skills/patterns/constants-only-config.md](../../.agents/skills/patterns/constants-only-config.md)
- **CLI nested groups + fail-loud stubs**: `@main.group()` per domain; leaf calls `_setup_logging(verbose)` first; unimplemented leaves raise `click.ClickException` via `_not_implemented(cmd)` → [.agents/skills/patterns/cli-nested-groups.md](../../.agents/skills/patterns/cli-nested-groups.md)
- **pytest factory fixtures**: shared builders are `@pytest.fixture`-returned `_make_X(**kwargs)` closures in `conftest.py`; `TestX` classes; deterministic → [.agents/skills/patterns/pytest-factory-fixtures.md](../../.agents/skills/patterns/pytest-factory-fixtures.md)
- **Confidence metadata**: every derived stat carries `ConfidenceMetadata` + `tier_for_sample(n)` (speculative <30 / evolving 30-99 / established ≥100); gate by tier → [.agents/skills/patterns/confidence-metadata.md](../../.agents/skills/patterns/confidence-metadata.md)

To document new patterns, use `/extract-patterns`.
