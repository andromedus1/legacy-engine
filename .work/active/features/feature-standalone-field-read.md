---
id: feature-standalone-field-read
kind: feature
stage: done
tags: [advisory]
parent: epic-local-meta-support
depends_on: [feature-advise-provenance-flag]
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Standalone field-read (no deck required)

## Brief
The most insightful advisory output — field composition + field-vulnerability / hate-equity profile —
is currently gated behind supplying a full `--deck`. Expose a standalone field-read that takes just a
field (global, `--provenance`, or custom `--field`) and prints the composition + vulnerability/hate-equity
profile with no deck. Likely a new `advise field` leaf (or `--no-deck` mode). Reuse the existing
field-vulnerability/hate-equity computation from the report path; just decouple it from the deck input.

## Design

### CLI surface: `advise field`

A new `advise field` leaf registered on the existing `@advise` group. Accepts:
- `--field FILE` — custom `<share> <archetype>` file; absent → global corpus field
- `--provenance online|paper` — filters the global field to a venue
- `--since`/`--until`/`--regime`/`--all-time` — window the global field (via `resolve_advisory_window`)
- `--db FILE` — alternate DB path
- `-v/--verbose`

No `--deck`, `--archetype`, `--seed`, `--reserved`, or `--venues`. The command is additive — the
existing `advise report` path is completely unchanged.

### Reuse vs decouple

| Component | Reused from | Notes |
|---|---|---|
| `_load_field` | `advisory/report.py` | Already handles global/custom/provenance/window |
| `_provenance_opt` | `cli.py` | Decorator, shared with other leaves |
| `_window_opts` | `cli.py` | Decorator, shared with other leaves |
| `field_vulnerability_tags` | `advisory/whattoplay.py` | Pure `vulnerability_tags(a)` for each field archetype |
| `hate_equity` | `advisory/whattoplay.py` | Per-tag field-share sum, deck-independent |
| `resolve_advisory_window` | `advisory/window.py` | Shared window resolution |

Rendering is inline in the CLI handler rather than a shared function — the `_render_field_section`
in `report.py` takes a full `FieldReadReport` (deck-dependent dataclass) so we render the same
information directly, avoiding coupling to that dataclass.

### Output structure

```
// data as of <date> (<N> decks)        ← _echo_data_freshness
// window: ...                          ← _echo_window
// field warning: ...                   ← field.warnings (thin-data banners)

=== Field Read (field_source=global) ===
Field composition (N archetypes):
  <archetype>                     <share%>  [<tags>]
  ...

Field vulnerability profile (hate-equity):
  (interpretation banner)
  <tag>                  field share attacked: <equity%>
  ...
```

Archetype rows include vulnerability tags inline (adjacent to each archetype) so the reader can
see why a tag appears in the profile. If the corpus is empty or has no tagged archetypes, honest
degradation messages are emitted.

## Implementation notes

- **Files touched**: `src/legacy_engine/cli.py` (new `advise_field` command, ~80 lines inserted
  between `advise_whattoplay` and `advise_report`), `tests/test_advise_field.py` (new, 28 tests).
- **Gated-additive**: `advise report` and all existing leaves are byte-identical — no shared
  code was changed. The only change to `cli.py` is the addition of `advise_field`.
- **Reused exactly**: `_load_field` from `report.py` handles all three field sources
  (global/provenance/custom) with no modification. `field_vulnerability_tags` +  `hate_equity`
  from `whattoplay.py` are the same functions used inside `build_field_read_report`.
- **Honest output**: field warnings (thin-data banners, normalization) are echoed as `//` comments.
  Empty corpus degrades gracefully (existing `_load_field` + `build_global_field` handle it).
- **Tests**: 28 tests in 6 classes — help surface, global field, provenance filtering, custom
  file, library-level parity (archetypes + hate_equity match what the library computes directly),
  and gated-additive regression guard. Full suite: 2067 passed (2039 + 28).
