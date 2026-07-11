# Opt-in analytics overlay with byte-identical default

A shipped analytics function (or CLI leaf) gains a new, richer computation that a caller must
*explicitly ask for* via a flag/param defaulting to off (`False`/`None`). When off, the code path is
the literal identity of the pre-flag behavior — proven by a *dedicated pinned full-body golden* on
the default path (see [freshness-stripped-cli-body-golden](freshness-stripped-cli-body-golden.md)),
with flag-on behavior covered by separate tests.

Distinct from [gated-additive-augmentation](gated-additive-augmentation.md), which gates on **data
presence** derived from the corpus and is verified by leaving old tests untouched. Here the gate is
**explicit caller intent**, and the contract is enforced by a *new* golden test.

## Examples

- `src/legacy_engine/analytics/match_results.py:490` — `compute_card_winrates(...,
  deck_archetype=None, deck_variant=None)`: conditioning is a no-op `WHERE (? IS NULL OR ...)`
  guard; docstring pins "Both `None` (the default) is byte-identical". Drives `report cards
  --conditioned` (cli.py:1661).
- `src/legacy_engine/analytics/subgroup.py:99` — `subgroup_compositions(..., with_winrates=False)`:
  `if with_winrates:` guards a second DB pass, else the four win-rate fields stay `None`. Drives
  `report subgroup --winrates`.
- `src/legacy_engine/analytics/match_results.py:257` — `compute_match_results(...,
  split_variant=None)` with the `effective_label` identity path; threaded through
  `advisory/window.py:154` + `analytics/matchup.py`. Drives `report matchups --split-variant`.
- Predating the bundle, same shape: `analytics/metashare.py:194` `group_by_variant=False`;
  `advise positioning --list-granular` (weaker function-identity variant, no body golden).

## When to Use
- Adding a heavier or narrower analytical view (conditioning, extra pass, label-split) to a surface
  whose current output is relied upon.

## When NOT to Use
- The new behavior should always run (plain conditional).
- The gate is corpus/data availability, not caller intent → gated-additive-augmentation.
- The default output legitimately changes → redesign, don't bolt on.

## Common Violations
- Making the new computation run by default and "fixing" the golden to match (hides the regression).
- Guarding inside the new branch so the no-op path isn't the literal identity path.
- Shipping the flag with no pinned-body golden on the off path (byte-identity unverified).
