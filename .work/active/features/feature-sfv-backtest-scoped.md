---
id: feature-sfv-backtest-scoped
kind: feature
stage: review
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Field/window-scoped backtest as the acceptance harness

## Brief

Enhance `advise backtest` (advisory/backtest.py) to be filterable to a **field + time window** so validation is Boulder-specific rather than global all-time Dimir (670 decks polluted by graveyard-meta tech like Surgical/Grafdigger's that isn't right for Boulder). This is the epic's **acceptance/regression oracle**: it should let us confirm FoN/Consign move winners-only→overlap and the Damping Sphere false-positive drops, scoped to the actual field the fixes target. Land early (no deps) so the other features validate against it. Frame divergence as a signal to investigate, never a pass/fail verdict (unchanged from the shipped backtest ethos).

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: acceptance harness — no deps; land early so attachments/weights/breadth/option-value validate against it

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Sharpens the backtest from global-Dimir to field-scoped (the brief's caveat). The epic's acceptance gate.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

## Design (2026-07-03)

### Architectural choice — how field-scoping filters the top-finisher set

Forced 2-3 options:

1. **Filter decks by field-archetype membership, at the TOURNAMENT level (chosen).** For
   every candidate top-finisher deck (already rank + target-archetype + window filtered),
   compute the archetype composition of the *whole tournament* it came from, and keep the
   deck only if at least `_FIELD_OVERLAP_MIN` (0.5, majority) of that tournament's labeled
   decks belong to an archetype present in the caller's `--field`. This directly
   operationalizes "the field the recommendation targets": a tournament that was
   6/8 Reanimator does not represent a Boulder field, so its top-finishing Boulder deck's
   sideboard (e.g. Grafdigger's Cage) is dropped even though the deck itself passes the
   rank cut. Cross-sectional (what was actually in the room), not calendar-era — this
   turned out to matter: it structurally captures "graveyard-meta tech that isn't relevant
   to Boulder" without needing a ban-regime time default (see the window sub-decision
   below).
2. **Re-weight instead of filter (soft field-similarity).** Compute a continuous
   similarity score (e.g. cosine distance) between each tournament's realized metagame and
   the target field, and weight each deck's contribution to `observed_frequency`
   continuously instead of a hard in/out cut. Rejected: breaks the integer "N winning
   decks" story `tier_for_sample`/the confidence tiering and the honest-degrade banner
   depend on; harder to read/test; risks silently smoothing away exactly the off-field
   pollution the feature exists to surface.
3. **Window-only, no explicit field filter.** Rely solely on `--since/--until`. Rejected:
   doesn't satisfy the acceptance criteria ("field-scoped sample excludes out-of-field
   archetypes" — window alone can't do this), and a calendar window is a coarser/less
   precise proxy for "was this tournament's metagame like the target field" than directly
   measuring the metagame.

Implemented as an **objective-search-split** (existing project pattern): `_tournament_archetype_counts`
does the one heavy, archetype-agnostic DB read (`{tournament_id: {archetype: n_decks}}`);
`_apply_field_scope` is a pure function over plain dicts that decides in/out and returns
`(kept_deck_keys, n_considered, n_excluded)` — unit-testable with hand-built dicts, no DB.

### Window sub-decision — did NOT add a "default to current ban-regime" behavior

Verified `--since`/`--until` already thread through `_qualifying_top_finisher_decks`,
`card_frequencies`, and `recommend_sideboard` correctly (existing code, confirmed by a new
explicit test — previously untested). Considered but **rejected** auto-defaulting
`since=None, until=None` to `generation.consensus._latest_regime_window()` (the convention
`card_frequencies` itself already uses internally when given no window) to fix the latent
asymmetry where the modal-maindeck computation implicitly regime-windows while the
top-finisher query does not. Rejected because: (a) field-scoping (chosen above) already
structurally excludes off-field-era tournaments by composition, which is a more precise
mechanism than a ban-regime date bucket; (b) auto-defaulting would piggyback this
diagnostic's behavior on an unrelated module's regime SSOT, and silently change `None`'s
meaning from "full corpus" (the documented `analytics.match_results` convention this
module's SQL already follows) to "current regime only" — a surprising, higher-risk change
for a diagnostic tool whose whole point is transparency; (c) it would have required
rewriting the test fixture's dates to track a moving ban-regime SSOT (`BAN_EVENTS`'
latest entry is `2026-05-18`, already after this fixture's Jan-2026 dates), trading a
self-contained, deterministic test corpus for one that silently breaks whenever a new ban
lands. `None` stays "full corpus, no window filter" — explicit, documented, unsurprising.

### Implementation units

- `advisory/backtest.py`:
  - `_FIELD_OVERLAP_MIN = 0.5` — module constant (same tier as `_TOP_FINISHER_QUANTILE`/
    `_OBSERVED_THRESHOLD`; not CLI-tunable, by convention).
  - `_tournament_archetype_counts(con, tournament_ids) -> dict[str, dict[str, int]]` — heavy DB half.
  - `_apply_field_scope(deck_keys, archetype_counts, field_archetypes, *, min_overlap=_FIELD_OVERLAP_MIN) -> (kept, n_considered, n_excluded)` — pure half.
  - `backtest_board(..., field_scope: bool = True)` — wires the filter in before
    `_observed_sideboard_frequency`; new `BoardBacktest` fields `field_scope`,
    `n_tournaments_considered`, `n_tournaments_excluded` (all with safe defaults so the
    dataclass stays backward-compatible for existing keyword construction).
- `cli.py` `advise backtest` leaf:
  - New `--field-scope/--no-field-scope` flag (default on).
  - New audit-echo lines: field-scope ON/OFF banner with considered/excluded counts;
    a specific honest-degrade message when field-scoping excludes every candidate
    tournament (distinct from the generic "no data" message), naming the reason and
    suggesting `--no-field-scope` or a broader `--field` to diagnose.
  - The unconditional divergence caveat and "never a verdict" ethos are untouched.

### Testing

`tests/test_backtest.py`: extended the shared DB fixture with a third, off-field
tournament (6/8 Reanimator, 2/8 Boulder, distinct sideboard signal "Grafdigger's Cage").
Added: `TestApplyFieldScopePure` (6 hand-built-dict unit tests: majority-kept,
minority-excluded, exact-boundary-kept, missing/zero-evidence-excluded, multi-tournament
partition, empty-input no-op); `TestBacktestBoardFieldScope` (default-on excludes
off-field tournament; `field_scope=False` reproduces the prior global sample; a field
disjoint from every candidate degrades to honest n=0/confidence=None with named counts,
not a crash; an explicit `--since/--until` window test — previously missing coverage;
field-scope + window composing together). 3 new CLI tests covering the default banner +
counts, `--no-field-scope`, and the field-scope-exhausted-specific degrade message. 21 new
tests total, all passing; the pre-existing classification/CLI tests are unaffected because
the added off-field tournament is excluded by the new default (byte-identical outcome for
those assertions).

### Risks

- **Shared threshold (`_FIELD_OVERLAP_MIN=0.5`) is a judgment call**, not derived from
  data. Documented as a module constant (same footing as the pre-existing
  `_TOP_FINISHER_QUANTILE`/`_OBSERVED_THRESHOLD` constants) rather than hidden; revisit if
  real-world field files produce surprising exclusions.
- **Concurrent sibling-feature work in the shared working tree.** At implementation time,
  `sideboard.py`/`whattoplay.py`/`data/hosers/legacy.json`/`test_sideboard.py`/
  `test_whattoplay.py` had pre-existing uncommitted changes from sibling features
  (`feature-sfv-attachments`/`feature-sfv-weights`), left in a state with 7 failing tests
  in `test_sideboard.py` unrelated to this feature. Per this feature's isolation contract
  those files were not touched. Verified this feature's changes are fully green in
  isolation (`git stash` of the sibling files, full suite: 2478 passed = 2457 baseline +
  21 new; sibling files restored unchanged afterward) before committing only this
  feature's files.

### Escape hatch

Not triggered — no design gap found; implementation matches the brief/epic's intent.
