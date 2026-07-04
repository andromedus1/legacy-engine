---
id: fix-decklist-parser-skip-comments
kind: story
stage: done
tags: [cli, ergonomics]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-06-01
updated: 2026-06-15
---

`generate consensus` (and `export deck text`) emit `// ...` comment header lines, but
`advisory.report._parse_decklist` raises `ValueError: malformed line` on any `//` line — so you
cannot pipe a generated consensus list straight into `generate tune --deck`/`advise` without manually
stripping comments. Make `_parse_decklist` skip blank lines and `//`/`#` comment lines (and ignore a
trailing "Sideboard" marker is already handled) so the generate→tune round-trip is seamless. Small,
pre-existing ergonomics bug surfaced while validating `generate tune --discover` end-to-end.

## Resolution (2026-06-15)
Already fixed in code: when `_parse_decklist` was promoted to `models/decklist.py::parse_decklist`
(after this idea was filed), `//`/`#` comment + blank-line skipping came with it (decklist.py:39-47).
The bug no longer reproduces. Locked it against regression: strengthened `test_round_trips_through_parser`
to parse a generated block directly (no manual `//` stripping) and added `TestParserCommentSkipping`
(both comment styles + leading-comments-don't-start-sideboard). Test-only change.
