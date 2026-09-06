---
id: story-readme-repo-currency
kind: story
stage: implementing
tags: [docs]
parent: null
depends_on: [feature-deck-rankings, feature-doomsday-variant-rankings]
release_binding: null
gate_origin: null
created: 2026-08-01
updated: 2026-09-05
---

# README full review + repo currency check (completion gate for the superarchetype arc)

## Brief

**the maintainer's directive (2026-08-01):** whenever all of this is done — including the HTML doc
additions (the three-level best-call page) — make sure the GitHub repo is up to date, and update
the README. **Review the README in its entirety** and make sure the whole thing is still
descriptive of the project and its output — not a patch, a full read-through.

Grounding at capture time (so the executor knows the gap): README.md is 293 lines, last rolled
forward 2026-07-12 (PR #50, pre-dating everything after the stable-era epic). Keyword check
2026-08-01: `superarchetype` 0 mentions, `multi-split` 0, `lint catalog` 0, `agency` 0 — i.e. the
README predates the entire superarchetype layer (three-level taxonomy, pooling/imputation,
licensed leans), the multi-split matrix (one-pass camp builds, ~26x), the curated-catalog lint,
era-alarm hygiene, incremental camp assignment, the matchup-plan land exemption, the acquire
color filter, and the best-call agency page's current shape (which VISION/SPEC now treat as a
headline surface).

Scope:
1. `git rev-list --left-right --count origin/main...main` == 0/0 and no unpushed branches/
   worktrees left dangling; open PRs merged or accounted for.
2. Full README read-through against the CURRENT capability set (docs/SPEC.md's built list is the
   checklist) — rewrite sections that describe the project's output stale-ly; rolling-foundation
   rules apply (present intent, no historical prose). Cover: what the engine is, the three-level
   taxonomy, the analytics/advisory surfaces, the best-call page + agency methodology + the new
   three-level tables/maps, honest-degrade philosophy, and how to run the standard loops
   (refresh/label/discover/eras/superarchetype/ranking refresh).
3. Cross-check README claims against reality the way the docs gate would (no assertions the code
   doesn't back); knowledge index regenerated if frontmatter changes.

Do NOT execute before the three-level page ships and passes its quality review — this story is
deliberately the LAST item of the arc so the README describes the finished state once, not three
intermediate ones.


## Integration scope (2026-09-05)
The maintainer authorized bringing the accumulated repository history through PRs
into main and completing repository hygiene. Reuse this existing completion item;
its original page dependency is satisfied by the archived Deck Rankings and
Doomsday Variant Rankings features.

Execution: one host owns branch integration and bounded inline story review;
a documentation edit agent checks README/related claims. Review weight: standard,
standalone-story lane. No new product architecture or UI work.

Acceptance:
- Preserve the tested accumulated history and merge through a green PR into main.
- Account for all local branch tips; preserve any content not yet represented.
- Review README in full, correct verified drift, and regenerate knowledge indexes
  if indexed documents change.
- Align the tracked lockfile with pyproject's supported Python range without
  upgrading package versions as a side effect.
- Keep other-session working files intact, and bring local main to the remote tip.
- Inspect existing operational alerts and distinguish data/model pending work
  from Git hygiene; do not dismiss evidence alerts to create a clean status.

Simplification: retire the stacked integration boundary once its complete history
is on main; archive this previously dangling completion item. Existing analytical
bugs remain tracked work, not an instruction to drain the product backlog.

Initial inventory: origin/main is an ancestor of the tested Deck Rankings +
Doomsday head (394 unlanded commits, no main-only commits). Every local branch is
contained except decks/energy-dnt-tron-specs: 14 of its 15 files are byte-identical,
and its remaining backlog file has later additions. Hogaak files are uncommitted
in the shared checkout; integration uses an isolated worktree.
