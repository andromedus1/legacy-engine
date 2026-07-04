---
id: epic-sb-config-evaluation-config-comparator-cli
kind: story
stage: done
tags: [advisory]
parent: epic-sb-config-evaluation-config-comparator
depends_on: [epic-sb-config-evaluation-config-comparator-engine]
release_binding: v0.2.0
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# `advise compare` CLI leaf + rendering

## Brief
The `advise compare` CLI surface over the engine: named-archetype + modifier flags (`--a`/`--b`,
`--a-transform`/`--b-transform`, `--a-lift`/`--b-lift`, `--a-lift-slot`/`--b-lift-slot`,
`--break-even-matchups`), building matrix+field via `build_advisory_inputs` + `build_custom_field`,
constructing the two `DeckConfig`s, calling `compare_configs`, and rendering the EV summary +
per-matchup table + break-even line + honesty banners (lift overlay is presence-correlational;
thin-cell tiers; imputed/coverage; transform-max optimism; data ceiling). Fail-fast on missing
`--a`/`--b` or a lift opponent not in the field.

## Implementation
Covers Unit 4 of the parent feature
`.work/active/features/epic-sb-config-evaluation-config-comparator.md`. Follows the
advisory-window-resolution-block + audit-echo `// ...` comment-line patterns.

Tests: extend `tests/test_cli.py` (file-backed DB + `--db` + `--field <tmp>`): fail-fast without
`--a`/`--b`; transform mode shown in the table; `--a-lift` parsed; `--a-lift-slot` folds a measured
diff; base MC P(A>B) + adjusted EVs + break-even line + banners present.
