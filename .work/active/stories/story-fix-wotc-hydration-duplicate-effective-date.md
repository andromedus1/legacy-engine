---
id: story-fix-wotc-hydration-duplicate-effective-date
kind: story
stage: review
tags: [bug, ingestion]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Ignore WotC hydration data when parsing visible announcement text

## Symptom

Installed refresh attempt `70fcac2f0fa14ae081cb23b7c106954c` completed with the WotC monitor
unavailable: `expected exactly one WotC effective date, found 2` for the resolved August 10, 2026
B&R announcement URL.

## Root cause

The captured 200 response contains the rendered article and a Nuxt hydration `<script>` with a
serialized copy of article content. `_TextExtractor.handle_data` includes script bodies, so the
visible `Changes effective as of August 10, 2026` line and its non-visible serialized copy both
reach the strict effective-date regex. The same payload also duplicates format headings.

## Fix approach

Exclude non-visible `script`, `style`, `template`, and `noscript` subtrees at the HTML extraction
boundary. Preserve H2 markers so the parser selects the actual Legacy format section rather than a
summary-table or table-of-contents label. Keep the existing strict requirement for exactly one
visible effective date and Legacy H2 section; do not deduplicate arbitrary matches or weaken
conflicting-content detection.

## Regression test

`tests/test_ban_monitor.py::TestWotcAnnouncementParser::test_ignores_nuxt_hydration_copy_of_live_article`
captures the exact relevant rendered-plus-hydration shape and fails with the reported exception
before the fix. A paired test asserts two conflicting visible dates still fail closed.

## Implementation notes

Execution capability: direct focused repair. The defect is isolated to pure HTML extraction and
section selection, with no public or persistent contract change.

Changed `src/legacy_engine/ingestion/ban_monitor.py` and `tests/test_ban_monitor.py`. The extractor
now omits non-visible script/style/template/noscript subtrees and preserves H2 markers. The section
parser requires exactly one Legacy H2 and ends at the next H2, ignoring the live page's summary
`<strong>` and TOC `<a>` labels without weakening effective-date or action ambiguity checks.

Regression-first evidence: the rendered-plus-Nuxt fixture failed with `expected exactly one WotC
effective date, found 2` before the fix. The corrected parser returns the captured live page's
August 10 effective date, The Fantasticar Legacy ban, October 12 next announcement, and exact source
URL. A conflicting second visible effective date still raises. Changed-file Ruff is clean and the
focused monitor/ops slice is `68 passed`. No live scheduler run or adjacent issue was bundled.
