# legacy-engine — Agent Instructions

A Magic: The Gathering **Legacy** format analytics platform — sibling to edh-engine (cEDH). Python
3.11+ Click CLI. Four pillars: Meta & Performance, Deck Mechanics (goldfish), Deck Generation, and
Meta Attack/Advisory. See `docs/VISION.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/PRINCIPLES.md`.

## Start every session
The terse `docs/knowledge-index.yaml` auto-loads at session start (titles, types, consumer hints).
For full per-doc detail (summary, decisions, key_findings), read `docs/knowledge-index-detail.yaml`
on demand. When you add or modify docs, run `/research-pipeline:knowledge-index` to regenerate both
layers from frontmatter. **Do not hand-edit the index files** — they're derived from doc frontmatter.

## Build process
Follow the methodology at `~/dev/skills-v2/plugins/research-pipeline/docs/build-process.md`.
Project knowledge lives under `docs/` (`architecture/`, `briefs/`, `designs/`, `programs/`). Parent
`CLAUDE.md` files ship the pipeline and shared key rules — don't duplicate them here.

<!-- agile-workflow:start -->
## Agile-Workflow Substrate

Work tracked in `.work/` as markdown items with YAML frontmatter
(`kind, stage, tags, parent, depends_on, release_binding`).
Layout: `.work/active/{epics,features,stories}/`, `.work/backlog/`,
`.work/releases/<version>/`, `.work/archive/`.

**Primary query tool:** `.work/bin/work-view` filters by stage, tag, kind,
parent, and dependency. Common patterns:
- `work-view --ready` — items ready to work (deps satisfied)
- `work-view --stage review` — items waiting on user
- `work-view --parent <id>` / `--blocking <id>` — hierarchy / sequencing
- `work-view --help` for the full flag set

Foundation docs in `docs/` describe the system NOW — never add legacy notes;
git history is the audit trail. Item files are the durable state: update the
body with implementation discoveries, review findings, blockers, and decisions
instead of relying on chat history.

Project-level agent rules live in AGENTS.md. Do not create or maintain
`.claude/rules/patterns.md` as a source of truth; reusable structural patterns
belong in `.agents/skills/patterns/`.

Project-specific refactor style conventions belong in AGENTS.md under
`## Refactor Style Conventions`. Detailed refactor convention references belong
in `.agents/skills/refactor-conventions/` and extend `refactor-design`'s
defaults; they do not replace the built-in scan and they do not create
standalone plan docs.

### Tag semantics

The `tags` field on items routes them to the right design skill. One tag has
load-bearing semantics — get this one right:

- **`[refactor]`** — behavior-preserving structural change ONLY. Apply the
  black-box test: would any observable behavior change for a caller of the
  public surface? If yes, this is NOT a refactor — drop the tag and let the
  item route through `feature-design`.
  - Counts as refactor: extract a helper to dedupe, split a god file, rename
    for clarity, remove dead code, inline a one-call abstraction.
  - Does NOT count as refactor (even if it feels "structural"): change an API
    signature, swap a storage backend with different consistency guarantees,
    replace a silent failure with an explicit error, split a function in a
    way that changes call-site contracts, "major rework of X."
- **`[perf]`** — performance work. Routes to `perf-design`.

All other tags are project-specific (see `.work/CONVENTIONS.md`) and do not
affect skill routing.

### Test integrity

When running, writing, or modifying tests:

- **File real production bugs as backlog items.** When a test failure
  surfaces an actual product bug (not a stale fixture, drifted assertion,
  or broken mock), park it via `/agile-workflow:park` instead of silently
  fixing it inline mid-test-pass. The backlog item is the audit trail.
- **Fix bad tests in-session.** Stale fixtures, drifted assertions, broken
  mocks, and outdated snapshots are test debt, not product bugs. Repair
  them as you go so the suite stays meaningful.
- **Then drain small backlog bugs with a full pass.** Once tests are
  green again, if a parked production bug is small enough for a single
  stride, pick it up immediately as `/agile-workflow:scope` → design →
  implement. Larger bugs stay in backlog for prioritization.
- **NEVER game a test to make it pass.** A failing test that documents
  *why* it fails — an inline comment naming the bug, a `skip` linked to a
  backlog id, an `xfail` with a reason — is more honest than a green test
  that lies. No `expect(true).toBe(true)`, no asserting on whatever the
  code happens to return, no deleting a test as "flaky" without
  root-causing first.

Broad entry points:
`/agile-workflow:ideate`, `/agile-workflow:epicize`,
autopilot goals such as "Use agile-workflow autopilot to drain --all",
and `/agile-workflow:release-deploy`.
<!-- agile-workflow:end -->

## Imported Claude Code Instructions
(Imported from the project `CLAUDE.md`, which remains in place as a Claude Code entrypoint.)
Frontmatter convention: every doc ships `description`, `type`, `summary`, `updated`, and
`decisions:`/`key_findings:` per kind — see `~/dev/skills/knowledge-index/SKILL.md` for the schema.

## Imported Claude Pattern Rules
(Imported from `.claude/rules/patterns.md`, which remains in place.)
Established code patterns: follow existing patterns when writing new code. Use
`/research-pipeline:knowledge-index` and the patterns skills to discover/document patterns;
reusable structural patterns belong in `.agents/skills/patterns/`.
