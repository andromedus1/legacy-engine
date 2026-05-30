---
description: How tests are structured in legacy-engine — factory fixtures returning _make_X builders, TestX classes, deterministic. Read before writing tests.
type: pattern
kind: planning
updated: 2026-05-29
summary: |
  Shared test data is built by factory fixtures in tests/conftest.py — a @pytest.fixture returns a
  _make_X(**kwargs) closure with overridable defaults. Tests group into TestX classes and are
  deterministic (no Date.now/random without a fixed seed).
decisions:
  - "Shared builders are pytest fixtures returning a _make_X(**kwargs) closure with defaults (not bare importable functions)."
  - "Group related tests into TestX classes; parametrize boundary cases."
  - "Tests are deterministic; verify behavior/contracts, not implementation details."
---

# Pattern: pytest Factory Fixtures

Shared test objects are produced by factory fixtures with overridable defaults.

## Rationale
A fixture returning a builder closure (rather than a bare module-level function) is the robust pytest
idiom — no fragile `from tests.conftest import ...` cross-imports, and each test overrides only the
fields it cares about. Keeps tests terse and resilient to model changes (add a field with a default →
existing tests unaffected).

## Example (canonical)
**File**: `tests/conftest.py`
```python
@pytest.fixture
def make_confidence():
    def _make(**kwargs) -> ConfidenceMetadata:
        defaults = {"level": "established", "production": "hand-written", "source": "user"}
        defaults.update(kwargs)
        return ConfidenceMetadata(**defaults)
    return _make
```
Usage (`tests/test_confidence.py`):
```python
class TestConfidenceMetadata:
    def test_factory_fixture(self, make_confidence):
        assert make_confidence(level="evolving").level == "evolving"
```
Boundary cases use `@pytest.mark.parametrize` (see `TestTierForSample`). Tests mirror the `src/` layout
(`tests/test_<module>.py`).

## When to use
- Any shared test object that more than one test constructs (models, decklists, cards, fixtures).

## When NOT to use
- A one-off object used by a single test (build it inline).

## Common violations
- Bare `_make_X` functions imported across test modules (use a fixture-returned closure instead).
- Non-deterministic tests (unseeded random / real clock); assertions on incidental return values.
- `assert True`-style tests that don't verify a contract.
