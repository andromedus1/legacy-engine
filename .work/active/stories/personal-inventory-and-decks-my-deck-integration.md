---
id: personal-inventory-and-decks-my-deck-integration
kind: story
stage: drafting
tags: [advisory, data-model, foundation, hold-for-review]
parent: feature-personal-inventory-and-decks
depends_on: [feature-personal-inventory-and-decks]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

> **Held for human review** alongside the parent feature. Design-only until then.

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

## Hold
Design complete at parent; this child is held for human review before implementation. Stage stays
`drafting`.
