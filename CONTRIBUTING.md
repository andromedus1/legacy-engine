# Contributing to legacy-engine

Thanks for taking a look. This is a data-analysis engine with strong opinions about honesty in
numbers, so the contribution bar is mostly about *evidence*, not ceremony.

## Getting a working checkout

Requires **Python 3.11–3.13**. Maintainer checkouts use Python **3.13** via `.python-version`, and
CI tests both the 3.11 lower bound and that pinned runtime. Python 3.14 is not supported until the
scientific/discovery dependency stack is green there.

The optional `discovery` extra pulls in `umap-learn` → `numba`. It is supported only on the
tested interpreters where that transitive NumPy/Numba stack installs and imports successfully.
The UMAP-specific test skips honestly when the optional stack is unavailable; the core suite does
not treat a missing optional dependency as evidence that discovery works.

```bash
git clone https://github.com/andromedus1/legacy-engine.git
cd legacy-engine
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q          # run the hermetic suite
```

The test suite is **hermetic** — it builds its own temporary DuckDB files and needs no network
and no seeded corpus. You can run it on a fresh clone before downloading any data.

To actually run the engine you need the data layer, which is fetched once and mirrored locally
(`data/` is git-ignored and fully rebuildable):

```bash
legacy-engine seed cards && legacy-engine seed cache && legacy-engine seed rules
legacy-engine seed banlist && legacy-engine label
```

## House rules

1. **Every number is labeled.** A statistic ships with its sample size, confidence tier, and the
   window it was computed over. Thin or absent signal is surfaced and named — never silently
   zeroed, blended, or imputed away. This is the project's defining constraint; see the
   `honest-degrade-marker` pattern.
2. **Tests ship with the change.** New behavior needs a test. CLI tests must pass an explicit
   `--db <tmp path>` and never touch the default database (see the
   `file-backed-cli-test-db-builder` pattern — this is the classic green-locally/red-in-CI trap).
3. **Follow the documented patterns.** `.agents/skills/patterns/` holds the project's reusable
   structures with concrete file:line examples. If you deviate, say why in the PR.
4. **Ground claims about card behavior in oracle text.** Don't reason about Magic interactions
   from memory — query `cards.oracle_text` in the local DuckDB and quote it.
5. **All changes go through a PR** with CI green. `ruff` runs non-blocking today (there's
   pre-existing debt); don't add new findings.
6. **No personal data.** Don't commit anything that links a player's handles across platforms,
   names private individuals, or identifies a local playgroup. `src/legacy_engine/data/players/aliases.json`
   ships empty on purpose — keep your local entries local.

## Where things live

| Path | What |
|---|---|
| `src/legacy_engine/` | the engine — ingestion, archetype, analytics, advisory, viz |
| `tests/` | hermetic pytest suite mirroring the source tree |
| `docs/` | vision, architecture, principles, domain briefs, analysis runbooks |
| `.agents/skills/patterns/` | documented code patterns, the convention source of truth |
| `.work/` | delivery substrate — epics, features, stories with frontmatter |
| `decks/` | decklists, primers, and field files used for dogfooding |
| `scripts/` | report generators (e.g. Deck Rankings and Doomsday Variant Rankings) |

## Reporting a data problem

Wrong numbers are the most valuable bug reports. Include the exact command, the audit `//` lines
it printed (they name the window, provenance, and any degradation), and what you expected instead.
