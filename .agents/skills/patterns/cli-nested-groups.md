---
description: How the CLI is structured in legacy-engine — Click nested groups, _setup_logging first, fail-loud stubs for unimplemented leaves. Read before adding a command.
type: pattern
kind: planning
updated: 2026-05-29
summary: |
  cli.py uses @main.group() per domain (seed/report/advise/...), leaf commands call _setup_logging(verbose)
  first, and not-yet-implemented leaves raise click.ClickException("not implemented: <cmd>") via a
  _not_implemented helper. The full command surface is declared up front and filled in feature by feature.
decisions:
  - "One @main.group() per domain; leaf commands are kebab-ish names under the group."
  - "Every leaf calls _setup_logging(verbose) as its first line; reuse the shared _verbose option decorator."
  - "Unimplemented leaves raise click.ClickException via _not_implemented(cmd) — never a silent no-op or TODO."
---

# Pattern: Click Nested Groups with Fail-Loud Stubs

The CLI declares its whole command surface as nested Click groups; unimplemented leaves fail loudly.

## Rationale
Declaring the full surface (`seed`, `refresh`, `label`, `report`, `advise` + subcommands) up front makes
the platform's shape discoverable from `--help` on day one, while implementations land feature by
feature. A stub that raises is honest — `legacy-engine seed cache` tells you it's not built yet rather
than silently doing nothing. Lazy imports inside command bodies (per the edh-engine idiom) keep startup
fast.

## Example (canonical)
**File**: `src/legacy_engine/cli.py`
```python
_verbose = click.option("-v", "--verbose", is_flag=True, help="Verbose logging")

@main.group()
def seed() -> None:
    """Fetch and cache external data."""

@seed.command("cards")
@_verbose
def seed_cards(verbose: bool) -> None:
    _setup_logging(verbose)
    _not_implemented("seed cards")

def _not_implemented(command: str) -> NoReturn:
    raise click.ClickException(f"not implemented: {command}")
```
When a leaf is implemented, replace `_not_implemented(...)` with a lazy import + call:
`from legacy_engine.ingestion.scryfall import seed_cards as _impl; _impl()`.

## When to use
- Every CLI command. New domains get a new `@main.group()`; new actions get a leaf under their group.

## When NOT to use
- One-off scripts (not part of the shipped CLI surface).

## Common violations
- A leaf that no-ops or prints "TODO" instead of raising `_not_implemented`.
- Heavy top-level imports in cli.py (do them lazily inside the command body).
- Forgetting `_setup_logging(verbose)` as the first line of a leaf.
