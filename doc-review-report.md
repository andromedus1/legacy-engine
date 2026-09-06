# Repository currency documentation review

Date: 2026-09-05. Scope: README, setup, CLI contracts and ranking references during
integration of the accumulated implementation into main.

A fresh bounded pass reviewed seven system/user documents and three relevant
module runbooks against Click definitions, pyproject metadata and publishing
scripts. Verdict: zero Critical/High findings. Two Medium findings were fixed:
README now names the separate online/paper default for `advise refresh`, and
ARCHITECTURE consistently states Python 3.11–3.13.

The initial full README pass also corrected `deck save --deck`, the exact
provenance-enabled serving command list and accepted values, stale tool labels,
and fixed test-count/runtime prose. All 85 documented CLI examples resolve to
real commands/options; 11 additional help checks passed in the fresh audit.
The ranking runbooks retain the separation between global rankings, specialized
Doomsday evidence, and the older positioning estimator.

Knowledge index regeneration reports zero errors and six existing warnings:
two large foundation decision lists and four documentation-directory README files
without frontmatter. The separate research-index discovery gap remains tracked
as `bug-knowledge-index-omits-research-analysis`.

This is a scoped documentation consistency review, not a new whole-code or
research-verification claim. Runtime, test, script, CI and package-definition trees
are unchanged from the fully green Doomsday commit `0caebfe`; the lockfile only
aligns Python compatibility and the local project version, preserving all third-
party package versions. PR #92 owns the final integration checks.
