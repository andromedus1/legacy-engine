---
id: idea-decklist-parser-skip-comments
created: 2026-06-01
tags: [cli, ergonomics]
---

`generate consensus` (and `export deck text`) emit `// ...` comment header lines, but
`advisory.report._parse_decklist` raises `ValueError: malformed line` on any `//` line — so you
cannot pipe a generated consensus list straight into `generate tune --deck`/`advise` without manually
stripping comments. Make `_parse_decklist` skip blank lines and `//`/`#` comment lines (and ignore a
trailing "Sideboard" marker is already handled) so the generate→tune round-trip is seamless. Small,
pre-existing ergonomics bug surfaced while validating `generate tune --discover` end-to-end.
