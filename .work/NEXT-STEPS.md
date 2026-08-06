# Next steps — post-v0.4.0 (2026-08-05)

State at the cut: `main` is green, tagged **v0.4.0**, 53 items collapsed into
`.work/releases/v0.4.0/`. Corpus refreshed through **2026-08-05**. Review queue empty.
Repo is **public**, MIT-licensed, and its history is rewritten to the pseudonymous identity.

## Do these first (cheap, unblock everything else)

1. **Delete the 17 stale merged remote branches.** Deletion was permission-blocked during the
   public-repo cleanup, so `origin` still carries every merged `impl/*` branch. One-liner:
   `git branch -r --merged origin/main | grep -v 'HEAD\|origin/main$' | sed 's|origin/||' |
   xargs -n1 git push origin --delete`
2. **Fix the CHANGELOG section order.** It currently reads v0.4.0, v0.2.0, v0.3.0, v0.1.0 —
   v0.2.0 and v0.3.0 are transposed. Cosmetic, but it is a public-facing doc now.
3. **`gh auth switch --user andromedus1` before any push here.** `gh` holds more than one account
   and the other one gets a 403 on this repo. Repo-local `git config` identity is already correct,
   but the *credential* is account-scoped and global, so it does not follow the repo.

## The arc I'd take next: make the advisor trustworthy

Three backlog items are one problem — the engine produces confident output that gets discarded
and rewritten by hand. Fixing them changes it from "generates a draft I rewrite" to "generates
the thing," and it is grounded in months of observed behavior rather than a hypothesis.

- `idea-sideboard-degenerate-board-guard` — the advisor spends slots on cards its own diagnostic
  prints as `~0% of field`, and silently under-fills boards (6 of 15). Four reproductions logged.
  The mechanism is named in the item: the objective is `tag-coverage × curated-swing-constant`,
  and **field relevance is never a term in it** — only a printed diagnostic. So the fix is a
  scoring question, not just a guard.
- `idea-consensus-blends-exclusive-build-clusters` — when a pool holds two mutually exclusive
  builds, per-card modes collapse them into a list nobody plays (emitted 1 Thoughtseize where all
  22 decks running it run 4, and zero run 1), reported as a clean 60/15 with `Legality: OK`.
- `bug-pbest-coverage-zero-for-most-camps` — P(best) resolves `s_cov` to *exactly* 0.0 for 80 of
  111 camps, including ones showing 30–69% coverage on the page. Verified pre-existing, not a
  regression from the one-pass migration. The column currently reads as if fringe camps were the
  format's best decks while the 2nd-biggest deck shows `n/a`.

## Landbase / color arc

`idea-landbase-comparison-table` is not standalone — it shares a foundation with
`idea-discovery-color-identity-feature` and `idea-color-variant-conditioned-matchup-cells`.
All three need a color dimension the engine lacks. Build it once.

**Before scoping it, read the fetchland section in the landbase item.** `is_land` exists and
`produced_mana` is populated for 96% of 1,436 land cards — but fetchlands produce nothing, so a
naive classifier reads a fetch-dense Legacy manabase as mostly-colorless, inverting the exact
comparison the table exists to make. Resolving a fetch to what it can reach means parsing oracle
text, which is a slice of `epic-card-semantics-ir`. Decide deliberately between that dependency
and a curated fetch→types table.

## Unbuilt pillars (all `[needs-brief]` — research before design)

- `epic-card-semantics-ir` — the rules-engine arc. Historically the stated priority, its error map
  is ready, and the color/landbase work leans on it.
- `epic-goldfish-simulation` — the last unbuilt pillar (deck speed/consistency). Deferred.
- `epic-data-autonomy` — less urgent since upstream recovered 2026-07-28.
- `epic-persistent-coach`, `epic-sb-config-evaluation`.
- `epic-local-meta-support` phase 2 is still blocked on a real geo data source. Do **not** build
  the heuristic place-name parser (false precision).

## Known-open smaller items

- `idea-local-ci-python-drift` — the dev `.venv` is Python 3.14 / NumPy 2.5 while CI pins 3.13 and
  `pyproject` declares only `>=3.11`. This cycle it produced two real CI failures that a local
  green suite had hidden, and it makes the optional `discovery` extra unusable locally.
- `gate-tests-stale-xfail-docstring` — `test_whattoplay.py:169` documents a sibling test as
  xfailing that has no marker and passes; `epic-card-semantics-ir-fix-graveyard-regex` may be
  obsolete work.
- `gate-patterns-multi-split-one-pass-sweep` — a 6-call-site shape worth documenting; the point
  worth writing down is the *parity proof* discipline, not the speedup.
- `bug-tron-candelabra-cliff-not-detected`, `bug-camp-autoname-picks-shared-not-discriminating-card`
  (today's re-discovery already improved the latter), `story-readme-repo-currency`.

## Operational reminder

Camp labels rot between refreshes. `discover apply` alone is not enough — re-run `discover run`
per parent every cycle or new decks land `[unlabeled]` (it was ~17% of field share before this
cycle's re-discovery; 0.83% after). Full order:
`refresh all` → `label` → `discover run` (all parents) → `discover apply` (all) → `eras run` →
`scripts/refresh_best_call_ranking.py`.
