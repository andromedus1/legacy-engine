# legacy-engine

<!-- One-line description — fill in after /ideate produces the north star. -->

## Process

Use `agile-workflow` for durable delivery state in `.work/`, `research-pipeline` for
discovery/planning/architecture/knowledge, and `agentic-research` for grounded research execution.
Workbench is not active in this project; never mix its substrate schemas into this process.

## Session orientation

The compact `docs/knowledge-index-nav.yaml` and `.work/` snapshot load at session start. Read
`docs/knowledge-index.yaml` for the full catalog and `docs/knowledge-index-detail.yaml` for
summaries, decisions, findings, and relationships.

Run `/research-pipeline:knowledge-index` after changing planning or research artifacts. All three
index files are generated from frontmatter; do not edit them by hand.

## Frontmatter convention
Every doc this project produces (north-star, architecture, roadmap, brief, design, etc.) ships with structured frontmatter:

- `description:` — "when do I read this?" hook (becomes consumer_hint in the terse index)
- `type:` — north-star | architecture | roadmap | brief | program-parent | program-report | design | features | ideate | workon
- `summary:` — 1-2 sentences on what's in the doc
- `decisions:` — required for `kind: planning` (5-9 highest-leverage commitments)
- `key_findings:` — required for `kind: research`
- `kind:` — usually derived from `type:` + `status:`; set explicitly to override
- `updated:` — YYYY-MM-DD

Use `/research-pipeline:knowledge-index` for the current schema and lint contract.

## Build process
Follow the global methodology at `~/dev/skills-v2/plugins/research-pipeline/docs/build-process.md`. Project knowledge lives under `docs/`:

- `docs/VISION.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/PRINCIPLES.md` — the live foundation docs
- `docs/research-plan.md` — research routing and background context
- `docs/briefs/` — domain briefs from `/research` and `/brief`
- `docs/designs/` — phase implementation specs from `/design`
- `docs/programs/` — `/research-program` output
- `.work/` — delivery substrate for active, backlog, and release-bound work items

Parent `CLAUDE.md` files ship the pipeline and shared key rules — do not duplicate them here. This file is for project-specific context only.

## Research

Use the retained pipeline intents (`scout`, `research`, `brief`, `deep-research`,
`research-program`). They commission `agentic-research`, which owns source attestations,
synthesis, `.research/` paths, and verification. Existing legacy research paths remain readable;
migrate them only through the operator-confirmed `agentic-research:convert` flow.
