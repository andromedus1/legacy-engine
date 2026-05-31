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

To document new patterns, use `/extract-patterns`.
