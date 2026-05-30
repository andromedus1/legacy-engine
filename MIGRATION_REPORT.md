# Migration Report — legacy-engine

**Date:** 2026-05-29
**Skill:** `/agile-workflow:convert` (bootstrap)
**Source shape:** `greenfield` (foundation docs + research only; no source code, no prior tracking artifacts)

## Foundation docs detected (preserved, read-only)
- `docs/VISION.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/PRINCIPLES.md`
- `docs/research-plan.md` + 4 research briefs (`legacy-foundations`, `legacy-metagame`,
  `advisory-methods`, and the `ingestion-archetype-contracts/` deep-research campaign)

## Items seeded
None. Greenfield bootstrap seeds an empty `.work/` skeleton. Epics are decomposed next via
`/research-pipeline:epicize` (or `/agile-workflow:epicize`) from the foundation docs.

## Substrate created
- `.work/active/{epics,features,stories}/`, `.work/backlog/`, `.work/releases/`, `.work/archive/`, `.work/bin/`
- `.work/bin/work-view` (copied from the agile-workflow plugin, executable)
- `.work/CONVENTIONS.md` (release mapping, tags, slugs, gates, design routing)
- `AGENTS.md` (canonical agent instructions, with the agile-workflow section)

## Conventions chosen
- **Release mapping:** tag-based
- **Tags:** ingestion, archetype, analytics, advisory, goldfish, generation, needs-brief, docs, infra + load-bearing refactor/perf
- **Gates:** tests, cruft, docs, patterns (security + infra omitted — local analytics CLI, no infra/secrets surface)
- **Design routing:** research-pipeline epic-design + feature-design (plugin installed)
- **Slugs:** kebab-case, parent-prefixed children; **stage overrides:** none

## Cleanup scope: `preserve-only`
Legacy/duplicate artifacts found and **preserved in place** (content imported into `AGENTS.md`):
- `CLAUDE.md` (regular file) — left as a Claude Code entrypoint; its frontmatter-convention content imported into AGENTS.md under "Imported Claude Code Instructions".
- `.claude/rules/patterns.md` (regular file) — left in place; pointer content imported under "Imported Claude Pattern Rules".

No files were deleted, moved, or replaced. Symlinks not created (preserve-only); `CLAUDE.md` and
`.claude/rules/patterns.md` remain independent files and are reported as duplicate entrypoints.

## Next steps
1. `/research-pipeline:epicize` — decompose the foundation docs into epics with `depends_on` chains.
2. Per epic: `/research-pipeline:epic-design` (briefs already cover the `[needs-brief]` domains).
3. Per feature: `/research-pipeline:feature-design` → `/agile-workflow:implement` → review.
