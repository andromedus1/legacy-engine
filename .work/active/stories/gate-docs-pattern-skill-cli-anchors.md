---
id: gate-docs-pattern-skill-cli-anchors
kind: story
stage: done
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: docs
created: 2026-06-14
updated: 2026-06-14
---

# Pattern-skill canonical examples cite stale cli.py line anchors (3 files, one root cause)

## Drift category
pattern-skill-staleness (High)

## Location
- `.agents/skills/patterns/audit-echo-comment-lines.md:54-71`
- `.agents/skills/patterns/advisory-window-resolution-block.md:71,85`
- `.agents/skills/patterns/honest-degrade-marker.md:42,90,114,126`

## Reality
cli.py grew across recent PRs; only the cli.py line citations drifted (module-relative refs like
`advisory/window.py`, `sideboard.py`, `primer.py`, `report.py`, `speculation.py`, `prices.py` all
still resolve). The described behaviors and the ~13-call-site / ~53-uses claims remain accurate.

Current correct anchors (verify each before committing — cli.py may shift again after the
gate-cruft unused-import removals land):
- `_echo_window` → cli.py:75 (was 58-64)
- `_echo_data_freshness` → cli.py:110 (was 101-106)
- `advise_sideboard` classification echo `// Classified archetype:` → cli.py:2516 (was 2151)
- `generate_tune` objective `// Δvalue =` → cli.py:4132 (was 3585)
- `advise_positioning` window block → cli.py:2197 (was 1970)
- `advise_refresh` window block → cli.py:3060 (was 2586)
- honest-degrade cli.py anchors: re-point `_echo_window` banner echo, speculation banner echo,
  `all_null` render, `_print_venue_divergence` to current lines.

Also: audit-echo-comment-lines cites "~53 uses" — actual count is now 59; update if cited.

## Required edit
Re-anchor ONLY the cli.py line references in the three pattern files (and the count). Leave
module-relative refs untouched. Best done AFTER gate-cruft-unused-imports lands (cli.py lines will
shift), and re-grep to confirm each anchor before finalizing.
