---
id: fix-infra-ijson-and-ci-lint
kind: story
stage: done
tags: [infra]
parent: null
depends_on: []
release_binding: null
gate_origin: infra
created: 2026-06-13
updated: 2026-06-13
---

# Infra: declare ijson; CI lint; path/SSRF hardening (gate-infra/security, Medium+Low)

- (Medium) `ijson` is imported in `scryfall.py:233` for the 547MB default_cards stream but is NOT a
  declared dependency — clean installs hit the `ImportError` fallback that loads the whole file into
  memory. Add `ijson` to `[project].dependencies`.
- (Low) CI job is named "Lint & test" but runs only pytest — add a `ruff check` (and optionally mypy) step.
- (Low) `collection/persist.py:71` `_deck_path` joins user `deck_id` with no validation (../ traversal,
  single-user local). Validate UUID/safe-slug or assert path stays within DECKS_DIR.
- (Low) `scryfall.py` follows redirects on the server-supplied bulk `download_uri`; validate host is
  scryfall.com/.io or disable redirect-following.
SQL injection + secrets audited CLEAN.

## Resolution

All items resolved.
- `pyproject.toml`: added `ijson>=3.2` to `[project].dependencies`; clean installs now get the
  streaming parser instead of the full-file-in-memory fallback.
- `.github/workflows/ci.yml`: added `ruff check src/` step before pytest. Non-blocking (`|| true`)
  with documented pre-existing debt: ~22 F401/F821 issues in cli.py (lazy-import type-annotation
  pattern) and 8 issues in other src files. A dedicated cleanup PR will make the step blocking.
- `collection/persist.py`: `_deck_path` now calls `.resolve()` and asserts the resolved path stays
  under `DECKS_DIR.resolve()` — raises `ValueError` on `../` traversal or absolute-path injection.
  Four new tests cover: normal id accepted, `../` rejected, `subdir/../../evil` rejected, absolute
  path rejected.
- `ingestion/scryfall.py`: added `_validate_scryfall_uri()` which checks the download_uri host
  against an allowlist (`scryfall.com`, `api.scryfall.com`, `c2.scryfall.com`, `*.scryfall.io`).
  Called before both `download_bulk_data` and `download_prices_bulk` fetches. 9 new parametrized
  tests cover allowed and rejected URIs. Fixed existing mock to use a valid Scryfall URI.
Full suite: 1882 passed (1869 + 13 new).

