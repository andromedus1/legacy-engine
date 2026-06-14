---
id: personal-inventory-and-decks-my-deck-integration
kind: story
stage: done
tags: [advisory, data-model, foundation, hold-for-review]
parent: feature-personal-inventory-and-decks
depends_on: [feature-personal-inventory-and-decks]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

# `--my-deck NAME` integration into the existing decklist-consuming leaves

## Scope
Wire an **optional** `--my-deck NAME` alternative to the existing `--deck FILE` option into the six
decklist-consuming CLI leaves: `advise positioning`, `advise sideboard`, `advise whattoplay`,
`advise report`, `generate tune`, and `export deck`. `--my-deck` resolves a persisted `UserDeck`'s
current version (via `collection.decks.current_cards`) into the same `(mainboard, sideboard)` maps the
leaves already consume — so the user registers/loads "my Dimir Tempo" instead of passing
`/tmp/*.txt` files every time.

## Design notes
- Per **gated-additive-augmentation**: `--my-deck` is purely additive. With it absent, the
  `--deck FILE` path is **byte-identical** to today. Make `--deck` and `--my-deck` mutually exclusive
  with a clear error if both/neither given (where the leaf currently requires `--deck`).
- Resolution: `--my-deck NAME` → `collection.persist.list_user_decks` lookup by `name` (owner-scoped,
  `LOCAL_OWNER`) → `current_cards(deck)`. Fail loud (`click.ClickException`) on unknown name.
- No new parsing: the resolved board maps enter the existing pipeline at the same point
  `_parse_decklist(...)` output does today.

## Acceptance criteria
- Each of the 6 leaves accepts `--my-deck NAME` and produces the same result as exporting that deck to
  a file and passing `--deck FILE`.
- Existing `--deck FILE` invocations are unchanged (regression: existing CLI tests pass untouched).
- Unknown `--my-deck NAME` raises a clear `ClickException`; supplying both `--deck` and `--my-deck`
  (or neither) errors clearly.
- Tests: `CliRunner` parametrized over the 6 leaves, `--my-deck` vs equivalent `--deck` parity.

## Implementation notes

**Helper added**: `_resolve_deck_boards(deck, my_deck, command_label)` in `cli.py` (before the `advise` group) centralises the mutual-exclusion guard, the "neither supplied" guard, the `find_deck_by_name` lookup, and the `current_cards` extraction. The `--deck FILE` code path is byte-identical to before when `my_deck is None`.

**Decorator**: `_my_deck_opt(f)` attaches `--my-deck NAME` to a command; used on all 6 + `advise refresh`.

**7 leaves modified** (the 6 named in the story + `advise refresh` which also had `required=True --deck`):
- `advise positioning`, `advise sideboard`, `advise whattoplay`, `advise report`, `advise refresh` — all in the `advise` group
- `generate tune`
- `export deck`

Each leaf: `--deck` changed from `required=True` to `default=None`; `--my-deck` added; function signature gains `my_deck: str | None`; `Path(deck).read_text() + _parse_decklist(...)` replaced by `_resolve_deck_boards(deck, my_deck, ...)`.

**Tests**: `tests/test_my_deck_integration.py` — 24 tests via CliRunner:
- Mutual-exclusion guard (both flags → error)
- Neither-supplied guard (no flags → error)
- Unknown name → fail loud "No deck named ..."
- Happy-path `export deck` parity (lightest leaf — no DB needed): `--my-deck` produces same card names as equivalent `--deck FILE`
- `--deck FILE` alone still works (regression guard)
