---
id: fix-infra-ijson-and-ci-lint
kind: story
stage: drafting
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

