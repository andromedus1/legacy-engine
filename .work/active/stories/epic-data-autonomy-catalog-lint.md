---
id: epic-data-autonomy-catalog-lint
kind: story
stage: review
tags: [advisory, infra]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Catalog lint: cross-check curated card data against the DB

## Brief
Promoted from `.work/backlog/idea-catalog-lint-vs-db.md`. Quick-win guard for the hand-curated
JSON layer (hosers, linchpins). A CI-gated lint that cross-checks every curated entry against
`cards` in DuckDB: name exists (exact spelling), declared `colors` match the card's actual colors
(would have caught Null Rod curated as `["G"]` — it's colorless), `castable_any_color` vs
Phyrexian/alt-cost oracle text, `symmetry` vs owner-restriction wording ("each/all/a player"
without "opponent" → warn if declared asymmetric), `functional_group` members plausibly share an
effect. Error-level for hard facts (existence, colors); warn-level for heuristics.

Motivation: Hydroblast/Pyroblast mis-tags and the Null Rod mis-color shipped silently in curated
JSON. Cheap to build; catches the whole data-typo class at commit time instead of at dogfooding
time.

## Implementation

**`src/legacy_engine/catalog_lint.py`** (new, pure module) — `lint_catalogs(con, hosers_path=
HOSERS_REGISTRY_PATH, linchpins_path=LINCHPINS_REGISTRY_PATH) -> list[LintFinding]`.
`LintFinding` is a frozen dataclass (`severity: Literal["error","warn"]`, `source` (file path),
`entry` (curated card name), `check` (check id), `message`). Reuses the existing schema-
validating loaders (`advisory.sideboard.load_hoser_catalog`, `advisory.linchpins.
load_linchpin_overrides`) rather than re-parsing raw JSON — a malformed curated entry still
fails fast there, before any cross-check runs.

Checks implemented:
- `name_exists` (error) — exact-spelling lookup in `cards`. Runs against BOTH catalogs (hosers
  and linchpins) since existence is the one property both schemas share.
- `colors_match` (error, hosers only) — declared `colors` frozenset vs the DB row's `colors`
  string parsed to a char set. The exact Null-Rod-shaped bug class.
- `castable_any_color_signal` (warn, hosers only) — heuristic: Phyrexian mana notation
  (`{X/P}`) in `mana_cost`, or a free hand-activation pattern (`Discard/Sacrifice/Exile this
  card:`) in `oracle_text`. Warns both directions (declared True with no signal; Phyrexian
  notation present but not declared).
- `symmetry_wording` (warn, hosers only) — literal "each player"/"all players"/"a player"
  phrasing (module docstring's example) with no "opponent" anywhere in the oracle text, warns
  only when `symmetry` is declared `"asymmetric"` (a declared-symmetric card is never flagged —
  the check is one-directional per the story's spec).
- `functional_group_coherence` (warn, hosers only) — groups hosers by `functional_group`,
  computes oracle-text word-token Jaccard similarity with WUBRG color words stripped (so
  Hydroblast/Blue Elemental Blast compare structurally instead of being penalized for which
  color they name), warns when the group's minimum pairwise similarity falls under 0.4.

**CLI** — `src/legacy_engine/cli.py`: new `lint` group, `lint catalog` leaf (fail-loud stub
pattern: `_setup_logging` first, `--db` option matching every other command). Opens the DB,
calls `lint_catalogs`, echoes every finding as a `// [severity] check source :: entry —
message` audit line, then a `// catalog lint: N error(s), M warning(s)` summary. Raises
`click.ClickException` (exit code 1) if any error-severity finding was produced; exit 0
otherwise (including the "0 findings" clean path, which prints `// catalog lint: clean (0
errors, 0 warnings)` instead of an empty summary line).

**CI fixture** — `tests/data/catalog_lint_cards.json`: 40 card rows (`name, mana_cost, cmc,
type_line, colors, produced_mana, oracle_text, layout, is_land, power, toughness` — the exact
`cards` table columns), one for every card name appearing in either shipped curated JSON.
Generated once via a read-only `duckdb.connect(".../data/legacy.duckdb", read_only=True)` query
against the real DB and committed; regenerate the same way if either curated file gains a new
card name (`tests/test_catalog_lint.py::TestShippedCatalogsLintClean::
test_fixture_covers_every_curated_name` fails loudly if the fixture falls behind).

## Implementation notes

**Real shipped-data error found and fixed**: `src/legacy_engine/data/hosers/legacy.json`'s
**Nihil Spellbomb** entry declared `"colors": ["B"]`. The card's actual cast cost is
`{1}` (colorless artifact) — the `{B}` only appears in an optional draw-a-card ability that
triggers when the artifact dies (`"you may pay {B}. If you do, draw a card."`), not in its mana
cost. This is the exact Null-Rod-shaped bug class the lint exists to catch (a curated color that
doesn't match the card's real cast cost), and it shipped silently — `colors_match` now fails
loudly on it. Fixed in the same commit: `"colors": []`, with a `_comment` explaining the
correction and citing this story. Verified the fix doesn't regress any consumer:
`tests/test_sideboard.py`'s `ub_legal_gy` coverage-model test derives color-legality dynamically
from `HOSER_CATALOG[n].colors` at run time (not hardcoded), so Nihil Spellbomb now qualifies via
the `not colors` (colorless) branch instead of the `colors.issubset(deck_colors)` branch — same
outcome, no test change needed. Ran the full sideboard/recommendation/collection-aware/
interaction-facts suites in isolation to confirm before running the full suite.

**Heuristic tuning against shipped data**: manually cross-checked all 40 curated names against
the real DB before writing any check logic (colors: 39/40 matched, 1 real error found above;
castable_any_color: both `true`-declared entries — Surgical Extraction's Phyrexian mana, Faerie
Macabre's free-discard activation — match their signal; symmetry: no asymmetric-declared entry
contains "each/all/a player" wording without "opponent" also present in the text;
functional_group: the two shipped groups — `red-blast` {Hydroblast, Blue Elemental Blast},
`blue-blast` {Pyroblast, Red Elemental Blast} — score ≈0.78 Jaccard, comfortably above the 0.4
threshold). Result: **the shipped catalogs lint fully clean at both error AND warn level** —
no accepted-warns list was needed (`TestShippedCatalogsLintClean::
test_shipped_catalogs_zero_warnings` asserts this directly, not just the error-level gate the
story required).

**Tests**: `tests/test_catalog_lint.py` (19 tests) — per-check unit tests with crafted
bad/good entries (nonexistent hoser/linchpin name errors; Null-Rod-shaped colors mismatch
reproduced and errors; missing-card short-circuit doesn't double-fire colors_match;
castable_any_color both directions; symmetry_wording all three branches including the
declared-symmetric no-op; functional_group_coherence dissimilar/similar/singleton-group cases)
plus the CI-gate golden tests against the real shipped catalogs + frozen fixture, plus a fixture-
integrity guard. `tests/test_cli_lint.py` (3 tests) — clean-exit, missing-card exit-1-and-report
(drops Wasteland from the tmp fixture rather than mutating curated JSON — a hermetic way to
exercise the real shipped-catalog failure path), and the `--db`-precedence-over-default-DB check
(mirrors `tests/test_cli_eras.py`'s technique: point `config.DUCKDB_PATH` at a location that
would get `mkdir`'d if ever touched, assert it wasn't). No production bugs found besides the
Nihil Spellbomb color fix above.

**Venv note**: this worktree had no `.venv` (worktrees don't inherit the parent repo's venv). Ran
`uv venv --python 3.13 .venv && uv pip install -e ".[dev]"` to stand up an isolated, correctly-
pathed editable install before running anything, rather than symlinking the parent repo's venv
(which resolves `legacy_engine` back to the parent working tree's `src/`, silently testing the
wrong code).

## Full suite
`.venv/bin/python -m pytest -q` → 3000 passed, 1 skipped, 1 xfailed (baseline before this story:
2978 passed, 1 skipped, 1 xfailed — the delta is exactly this story's 22 new tests). `ruff check`
clean on both new modules and the new test files; `cli.py`'s pre-existing 17 F821 forward-
reference false positives (documented in prior stories) are unrelated to the new `lint` group.
