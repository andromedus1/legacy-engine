---
id: epic-sb-advisor-correctness-matchup-plan-flex
kind: feature
stage: done
tags: [advisory]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Matchup-plan flex — unlock the OUT side, gate the IN side on axis relevance

## Brief

`_plan_matchups` (`src/legacy_engine/advisory/sideboard.py:2576`) builds the per-opponent OUT/IN
swap plans, and both sides are broken for a consensus-tight deck. The OUT side locks every maindeck
card at `lock_threshold = 0.65` archetype adoption (`:2584`, `:2640-2642`), which for Dimir Tempo
leaves FETCHLANDS as the only flex — so the data-driven plans proposed cutting 2-3 lands (Scalding
Tarn, Bloodstained Mire) for spells vs Izzet / Jeskai / the mirror. Cutting lands is not a
sideboarding decision a real pilot makes; it is what an unconstrained optimizer does when the only
unlocked slots happen to be lands. The IN side is gated on correlational card value alone
(`:2700-2708`: gate tier + `lift > 0`), with no check that the card's answer axis is even present
in the matchup — which is how the mirror plan boarded Hydroblast into a UB deck.

This feature fixes both sides. OUT: hard-exempt lands from the flex/OUT pool and degrade honestly
when no legal non-land flex remains — say "no flex slots at this consensus level" rather than
manufacturing land cuts. IN: gate candidates on the coverage model's axis relevance (a `plays-red`
answer needs a red target in the matchup) in addition to lift, so correlational noise cannot
promote an inert card. Both changes are subtractive on the recommendation side and additive on the
audit side; the honest-degrade path is a first-class output, not a failure.

Does NOT cover: lowering `lock_threshold` globally (rejected — see inherited decisions); the
coverage model / element weights (`per-deck-castability`, `hate-self-cost`); the composition of the
15 itself; measuring whether a given slot actually pulls weight in its matchup (that is
`epic-sb-config-evaluation-matchup-slot-test`'s territory — this feature only decides which cards
are ELIGIBLE to swap, never how much a swap is worth empirically).

## Epic context

- Parent epic: `epic-sb-advisor-correctness`
- Position in epic: independent capability — `_plan_matchups` output is not part of the backtest's
  recommended-board partition, so this feature neither depends on nor perturbs the divergence
  ratchet. Fully parallelizable with the coverage-model arc.

## Inherited design decisions

- **Calibration philosophy** (epic): mechanism fixes only; observed adoption stays a diagnostic and
  is NEVER blended into scores. Note the subtlety: the `lock_threshold` IS an adoption reading, but
  it is a legality/identity constraint on which cards may be cut, not a score input — this feature
  keeps it in that role and does not let adoption reach the ranking.
- **OUT-side form** (epic `## Design decisions`): hard-exempt lands and degrade honestly, rather
  than lowering `lock_threshold`. Lowering the threshold would unlock spells indiscriminately
  across every archetype; the land exemption is targeted at the verified failure and preserves the
  consensus-core protection the threshold exists for.

## Research briefs

- `docs/briefs/advisory-methods.md` — advisory surface conventions and the per-matchup plan
  contract.
- `docs/briefs/sideboard-core-and-hedge.md` — how the chosen 15 reaches `_plan_matchups`.
- Audit trail for the finding: the Dimir primer session (2026-07-04) used judgment plans with the
  engine's signals cited and explicitly rejected — the IN side had real signal (Consign vs Izzet
  n=71, Hydroblast vs Doomsday n=30 corroborated judgment), the OUT side did not.

## Foundation references

- `docs/ARCHITECTURE.md` — the `sideboard.py` row's per-matchup OUT/IN plan description
  (post-board exactly-60, copy-capped, locked-core protected).
- `docs/SPEC.md` — Pillar 4 + the HONEST-DEGRADE NFR.
- Patterns: `.agents/skills/patterns/honest-degrade-marker.md` (the no-legal-flex path must carry a
  named reason and suppress the magnitude, matching the existing `MatchupPlan.degraded=True` note
  shape at `sideboard.py:2666-2675`); `.agents/skills/patterns/audit-echo-comment-lines.md` (any new
  provenance line uses the `// ...` prefix);
  `.agents/skills/patterns/divergence-as-diagnostic-surface.md` (where the engine declines to
  recommend a swap the correlational signal favors, say so — do not silently drop it).

## Design decisions

<!-- resolved 2026-07-31 during feature-design (autopilot delegation, judgment-resolved;
     no AskUserQuestion — rationale recorded here per the delegation contract) -->

- **Land test = `type_line` contains `"Land"`, NOT the `cards.is_land` column.** Verified against
  the corpus (`data/legacy.duckdb`, 39,452 cards / 67,581 decks) — see `## Corpus grounding` below.
  The `is_land` column is TRUE for modal-DFC *spell* face-aliases (`store.py:213` sets
  `any_face_land` for both-castable layouts), so gating on it would exempt **Sink into Stupor**
  (3,377 corpus maindecks), Shatterskull Smashing, Fell the Profane, Agadeem's Awakening and 30
  more spells from ever being sided out. That is a worse bug than the one being fixed.
- **Land exemption is unconditional, not flag-gated.** `opt-in-analytics-overlay` is the wrong
  pattern here: an off-by-default flag would keep proposing land cuts as the DEFAULT answer, and
  the epic's locked OUT-side form says "hard-exempt". The *diagnostics* added alongside are
  additive (default-empty tuples), so no existing caller's behavior changes except that land cuts
  stop being emitted.
- **The IN axis gate is data-presence gated (`gated-additive`), the OUT land exemption is not.**
  The land test is derivable from the `con` `_plan_matchups` already holds; opponent axis sets are
  not (they need the `FieldDistribution`, which only the caller has). So `opponent_axes=None` →
  gate inactive and *named as inactive*; `land_names=None` → resolved from `con`, gate always on.
- **An opponent with an EMPTY axis set never suppresses.** "No vulnerability tags derived for this
  opponent" is absence of evidence, not evidence of irrelevance. Suppressing on it would convert a
  data gap into a silent recommendation change — the exact anti-pattern honest-degrade exists to
  prevent. Recorded as `opponent-axes-unknown`.
- **`_hate` cards are axis-relevant for every opponent.** `_hate:<tag>` pseudo-elements in
  `_build_coverage_model` are keyed by the DECK's own vulnerability tags and weighted by field-wide
  `interactive_share` — they carry **no archetype key** (`sideboard.py:1700-1712` docstring). There
  is therefore no per-opponent axis for a `_hate`-only card (Veil of Summer, Defense Grid, Carpet of
  Flowers) to be tested against, and a strict intersection gate would ban all three from every plan
  forever. Allowing them with the explicit reason `hate-axis-field-wide` states the model's own
  semantics instead of fabricating a distinction it does not make.
- **Permissive on unknown card axes.** A card with no catalog entry and no injected axes cannot be
  assessed; allow + record `card-axes-unknown`. In the production path this is unreachable (every
  member of the 15 was selected by the coverage model, so it covers ≥1 element and therefore has
  non-empty `attacks`) — it exists for hand-built and direct-caller inputs.
- **"No flex" is structural, computed before any lift/tier reading.** The flex pool is
  `maindeck − locked_core − lands` on *slot eligibility alone*. If it is empty, no amount of data
  could ever produce a legal cut — that is the honest degrade. If it is non-empty but nothing
  cleared the gate, that is a real answer ("no dead cards"), not a degrade. Conflating the two is
  what made the current `out_total == 0` note say "no flex dead cards found (or no high-lift
  sideboard IN candidates)" — an `or` that names neither cause.

## Corpus grounding

Read-only queries against `data/legacy.duckdb` (oracle text quoted verbatim from `cards.oracle_text`,
type lines from `cards.type_line`):

**Land-creatures.** Exactly one appears in corpus maindecks: **Dryad Arbor**, `type_line =
'Land Creature — Forest Dryad'`, 4,155 decks / 5,279 copies. Oracle text verbatim:

> `(This land isn't a spell, it's affected by summoning sickness, and it has "{T}: Add {G}.")`

It is a land drop and occupies a mana-base slot, so exempting it is correct. The other 25
land-creature rows in the corpus (`Jasconian Isle`, `Gobland`, `Forest Dryad` token, transform
gods, MDFC creature fronts) appear in **zero** maindecks. No special handling needed beyond the
type-line rule.

**MDFC / modal land backs — the case that decides the test.** 34 distinct cards appear in corpus
maindecks where `cards.is_land = TRUE` but `type_line` contains no `"Land"`. These are modal-DFC
face-alias rows whose *front* face is a spell and whose *back* is a land. The five largest:

| card | `type_line` | `is_land` | decks |
|---|---|---|---|
| Sink into Stupor | `Instant` | TRUE | 3,377 |
| Shatterskull Smashing | `Sorcery` | TRUE | 3,228 |
| Boggart Trawler | `Creature — Goblin` | TRUE | 2,654 |
| Fell the Profane | `Instant` | TRUE | 2,346 |
| Agadeem's Awakening | `Sorcery` | TRUE | 2,140 |

Sink into Stupor's oracle text verbatim:

> `Return target spell or nonland permanent an opponent controls to its owner's hand.`

That is a spell a pilot sides out routinely. **The `type_line` rule leaves all 34 in the flex pool
and exempts none of them — which is correct.** The `is_land` column would have exempted every one.

**Transform backs.** `Ojer Pakpatiq, Deepest Epoch` (`type_line = 'Legendary Creature — God'`,
`is_land = FALSE`) is cast as a creature and only becomes `Temple of Cyclical Time` after dying —
correctly NOT exempt. `Westvale Abbey` (`type_line = 'Land'`, layout `transform`) is a land you play
as a land drop — correctly exempt. The type-line rule gets both.

**The reported failure.** `Scalding Tarn`, `type_line = 'Land'`, oracle verbatim:

> `{T}, Pay 1 life, Sacrifice this land: Search your library for an Island or Mountain card, put it onto the battlefield, then shuffle.`

Exempt under the rule. 480 distinct cards in corpus maindecks carry `"Land"` in `type_line`.

## Architectural choice

**Chosen: Option B — filter at candidate-construction time inside `_plan_matchups`, with the
eligibility inputs injected by the caller and DB-resolved as fallback.**

*Option A — post-filter the produced plan.* Let `_plan_matchups` run unchanged, then strip land
entries out of `side_out` afterwards. Rejected on two counts. It breaks the conservation invariant
the planner's own docstring asserts (`side_out` and `side_in` must carry equal total copies; a 60
must stay a 60), so it would have to re-pair the survivors — i.e. re-run the pairing loop anyway,
just with worse information. And it structurally cannot tell "the flex pool was empty" from "the
flex pool was live but nothing was dead", so the honest-degrade reason could never be *named* —
only the magnitude could be suppressed, which is half the pattern.

*Option C — pre-filter upstream and hand `_plan_matchups` a reduced maindeck.* Rejected because
`post_board` is reconstructed from `deck_maindeck`, which must remain the true 60 — a reduced
maindeck would silently produce a sub-60 post-board. More importantly the planner would never see
the cards it declined, so it could not report them; the divergence-as-diagnostic surface (the
explicit requirement that "where the engine declines a swap the correlational signal favors, say
so") would be lost entirely.

*Option B, chosen.* Eligibility is decided where the candidate lists are built, so the pairing loop
never sees an ineligible card and the 60-conservation invariant is untouched by construction. The
structural flex pool is computed **once per deck, before the opponent loop**, on slot eligibility
alone — which is what makes `no-legal-flex` distinguishable from `no-dead-cards`. Every decline is
recorded as a typed `(card, lift, reason)` tuple on the returned `MatchupPlan`, so the correlational
signal the engine overruled stays visible instead of vanishing. Heavy resolution (the `type_line`
query, the opponent axis sets) happens once at the call site and arrives as plain dicts, matching
`objective-search-split`; the DB fallback inside `_plan_matchups` exists so the correctness fix
cannot be bypassed by a caller that forgets to inject.

## Implementation Units

### Unit 4 (designed first — trickiest): `_plan_matchups` eligibility rework

`src/legacy_engine/advisory/sideboard.py` — rework of `_plan_matchups` (currently `:2576-2847`).

New signature (additions only, all keyword-only with safe defaults):

```python
def _plan_matchups(
    con, deck_maindeck, sideboard_15, opp_values, archetype,
    *,
    max_swaps: int = 4,
    lock_threshold: float = 0.65,
    since: str | None = None,
    until: str | None = None,
    catalog: Optional[dict[str, HoserCard]] = None,
    adaptive_windows: "dict[str, tuple[str | None, str | None]] | None" = None,
    land_names: "frozenset[str] | None" = None,          # NEW
    opponent_axes: "dict[str, frozenset[str]] | None" = None,  # NEW
    card_axes: "dict[str, frozenset[str]] | None" = None,      # NEW
) -> dict[str, MatchupPlan]:
```

Behavior, in order:

1. `land_names` resolution: `if land_names is None: land_names = _resolve_land_names(con, deck_maindeck)`.
   Never `frozenset()` by default — the exemption must not be opt-in.
2. Locked core computed exactly as today (unchanged; still `card_frequencies` ≥ `lock_threshold`).
3. **Structural flex pool, computed once, outside the opponent loop:**
   `flex_pool = frozenset(c for c, n in deck_maindeck.items() if n > 0 and c not in locked_core and c not in land_names)`.
4. Per opponent:
   - gate not cleared → unchanged degraded plan, but `plan_status="thin-data"` and the existing
     note text is preserved verbatim (no golden churn).
   - `flex_pool` empty → `plan_status="no-legal-flex"`, `degraded=True`, `side_out={} / side_in={}`,
     `post_board = dict(deck_maindeck)`, `n_basis=0`, `tier="speculative"`, and a note naming both
     causes with counts (locked-core size, land count) plus any declined-with-signal cards.
   - otherwise build OUT candidates: gate + `lift <= 0` + `copies > 0` first, THEN eligibility.
     A card failing eligibility is appended to `out_suppressed` with reason `"land"` or
     `"locked-core"` — recording only signal-bearing declines, never the whole locked core.
   - build IN candidates: gate + `lift > 0` + `copies > 0`, then `_in_axis_verdict`. Not-allowed →
     `in_suppressed` with the verdict reason.
   - pairing loop, `post_board` reconstruction, `n_basis`/`tier` derivation: **unchanged**.
   - zero swaps with a live flex pool → non-degraded, `plan_status` ∈
     {`no-dead-cards`, `no-in-candidates`, `no-legal-swap`} per which list was empty.
   - ≥1 swap → `plan_status="planned"`, note unchanged in shape.

Acceptance criteria:
- A maindeck whose only non-locked cards are lands yields `degraded=True`,
  `plan_status="no-legal-flex"`, empty `side_out`/`side_in`, `post_board == deck_maindeck`.
- No `MatchupPlan.side_out` key ever satisfies `"Land" in type_line` for the deck's cards.
- `sum(side_out.values()) == sum(side_in.values())` and `sum(post_board.values()) ==
  sum(deck_maindeck.values())` still hold on every non-degraded plan (existing invariants).
- An IN candidate with `lift > 0`, gate-clearing, whose axes are disjoint from a NON-EMPTY opponent
  axis set never appears in `side_in`; it appears in `in_suppressed` with reason `"off-axis"`.
- `opponent_axes=None` or an empty axis set for that opponent → zero suppression.

### Unit 1: plan-status vocabulary + `MatchupPlan` diagnostic fields

`src/legacy_engine/advisory/sideboard.py`, above the `MatchupPlan` dataclass (`:214`).

```python
_PLAN_STATUS_PLANNED       = "planned"
_PLAN_STATUS_THIN_DATA     = "thin-data"
_PLAN_STATUS_NO_FLEX       = "no-legal-flex"
_PLAN_STATUS_NO_DEAD_CARDS = "no-dead-cards"
_PLAN_STATUS_NO_IN         = "no-in-candidates"
_PLAN_STATUS_NO_LEGAL_SWAP = "no-legal-swap"

_VALID_PLAN_STATUSES: frozenset[str] = frozenset({...all six...})
_DEGRADED_PLAN_STATUSES: frozenset[str] = frozenset({_PLAN_STATUS_THIN_DATA, _PLAN_STATUS_NO_FLEX})
```

`closed-vocabulary-fail-fast-token`: `MatchupPlan.__post_init__` raises `ValueError` naming the
token and the sorted allowed set when `plan_status` is outside the vocabulary.

Three additive fields, all defaulted so every existing constructor keeps working:

```python
plan_status: str | None = None   # filled by __post_init__ when omitted
out_suppressed: tuple[tuple[str, float, str], ...] = ()   # (card, lift, reason)
in_suppressed:  tuple[tuple[str, float, str], ...] = ()   # (card, lift, reason)
```

`__post_init__` derives an omitted `plan_status` from `degraded` (`thin-data` / `planned`) via
`object.__setattr__` (frozen dataclass), so the field is always a valid token for consumers.

Acceptance criteria: existing 8-kwarg constructors still work and get a valid derived
`plan_status`; an invalid token raises `ValueError` naming it and the sorted allowed set.

### Unit 2: `_resolve_land_names` (the DB half of objective-search-split)

`src/legacy_engine/advisory/sideboard.py`, near `_plan_matchups`.

```python
def _resolve_land_names(
    con: duckdb.DuckDBPyConnection, names: "Iterable[str]"
) -> frozenset[str]:
    """Names among ``names`` whose ``cards.type_line`` contains "Land"."""
```

One parameterized `SELECT name FROM cards WHERE name IN (...) AND type_line ILIKE '%land%'`.
Returns `frozenset()` on any DB failure with a `log.debug` — an unresolvable card list must not
crash the planner, and the pre-existing behavior (no exemption) is the honest fallback.

Acceptance criteria: `Scalding Tarn`/`Dryad Arbor`/`Westvale Abbey` in, `Sink into Stupor`/
`Boggart Trawler`/`Ojer Pakpatiq, Deepest Epoch`/`Brainstorm` out; empty input → `frozenset()`;
missing `cards` table → `frozenset()`, no raise.

### Unit 3: `_in_axis_verdict` (pure)

`src/legacy_engine/advisory/sideboard.py`, near `_plan_matchups`.

```python
def _in_axis_verdict(
    card_axes: frozenset[str], opp_axes: frozenset[str]
) -> tuple[bool, str]:
    """(allowed, reason) for one IN candidate against one opponent's axis set."""
```

Order: `opp_axes` empty → `(True, "opponent-axes-unknown")`; `card_axes` empty →
`(True, "card-axes-unknown")`; intersection non-empty → `(True, "on-axis")`; `"_hate"` in
`card_axes` → `(True, "hate-axis-field-wide")`; else `(False, "off-axis")`.

Acceptance criteria: the five branches above return exactly those reasons; Hydroblast
(`{"plays-red"}`) vs a Dimir axis set (`{"plays-blue", "plays-black", ...}`) → `(False, "off-axis")`;
Consign to Memory (`{"combo","storm-reliant","colorless-reliant"}`) vs a combo axis set →
`(True, "on-axis")`; Veil of Summer (`{"_hate"}`) vs any non-empty set →
`(True, "hate-axis-field-wide")`.

### Unit 5: call-site wiring in `recommend_sideboard`

`src/legacy_engine/advisory/sideboard.py:4360` (Step 6b).

Pass `land_names=_resolve_land_names(con, deck_maindeck)` (resolved once, before the try-block that
wraps `_plan_matchups`), `opponent_axes=archetype_tags` (already computed at Step 3, `:3913`), and
`card_axes` built from `catalog` merged with `promoted_candidates` (curated/promoted entries both
carry `attacks`). No new DB round-trips beyond the one land query.

Acceptance criteria: `recommend_sideboard` on a hermetic corpus never emits a land in any
`side_out`; existing `recommend_sideboard` tests stay green.

### Unit 6: render honesty at the three plan-render sites

Two sites hardcode `"thin data — no per-matchup plan"` for **any** `plan.degraded`, which the new
`no-legal-flex` degrade would turn into a lie:

- `src/legacy_engine/cli.py:5336-5340` (`deck tune`) → render `plan.note`, `//`-prefixed per
  `audit-echo-comment-lines`.
- `src/legacy_engine/advisory/report.py:552-554` (`_render_sideboard_plans`) → render `plan.note`.

`src/legacy_engine/cli.py:3286-3287` (`advise sideboard`) already renders `plan.note` — unchanged.

Additive diagnostic line at each of the three sites when `in_suppressed`/`out_suppressed` is
non-empty: one compact `declined:` line naming at most the three strongest-signal entries plus a
residual count. Empty tuples → no line → byte-identical to today.

Acceptance criteria: a `no-legal-flex` plan never renders the word "thin" anywhere; plans with no
suppressions render byte-identically to the pre-feature output.

## Implementation Order

1. Unit 1 (vocabulary + dataclass fields) — everything else types against it.
2. Unit 2 + Unit 3 (the two small helpers) — independently unit-testable, no DB for Unit 3.
3. Unit 4 (`_plan_matchups` rework) — the substance.
4. Unit 5 (call-site wiring).
5. Unit 6 (renders).
6. Full suite + `ruff check src/`.

## Testing

### Unit tests: `tests/test_sideboard.py`, new `TestMatchupPlanFlex` class

Hand-built inputs, `objective-search-split` style — no default DB anywhere.

- `_in_axis_verdict`: one test per branch (5), plus the Hydroblast-vs-mirror regression named for
  the finding.
- `_resolve_land_names`: hermetic in-memory DuckDB seeded via `store.load_cards` with the six
  verified cards above (Scalding Tarn, Dryad Arbor, Westvale Abbey, Sink into Stupor,
  Boggart Trawler, Brainstorm) → asserts exactly the three type-line lands come back. This is the
  test that pins the corpus finding: **Sink into Stupor must NOT be exempt.**
- `_plan_matchups` land exemption: a maindeck of `{Brainstorm: 4, Scalding Tarn: 4}` with hand-built
  `_OppValues` giving Scalding Tarn the most-negative lift → Scalding Tarn never in `side_out`,
  appears in `out_suppressed` with reason `"land"`.
- `_plan_matchups` no-legal-flex degrade: maindeck of lands only → `degraded=True`,
  `plan_status="no-legal-flex"`, note names the reason, `post_board == maindeck`.
- `_plan_matchups` IN axis gate: hand-built `card_axes={"Hydroblast": {"plays-red"}}` and
  `opponent_axes={"Dimir Tempo": {"plays-blue"}}` → Hydroblast in `in_suppressed`, not `side_in`.
- `_plan_matchups` gate-inactive paths: `opponent_axes=None`, and an opponent mapped to
  `frozenset()` → zero suppression (guards the absence-of-evidence decision).
- `MatchupPlan`: legacy 8-kwarg construction still valid + derived `plan_status`; invalid token
  raises `ValueError` naming it.

### Integration tests: `tests/test_sideboard.py`

- `recommend_sideboard` on the existing `make_rounds_corpus` fixture: assert no `side_out` key is a
  land for the deck under test, and existing invariants (60-conservation, copies-equal) hold.

### Regression

Existing `TestPlanMatchups` (`tests/test_sideboard.py:2534`) must stay green untouched — including
`test_max_swaps_respected`, whose maindeck contains `{"Swamp": 8}` and which will now exercise the
land exemption incidentally.

## Risks (pre-mortem)

1. **The land exemption empties the flex pool for the very deck that motivated the feature, and the
   result reads as a regression.** Dimir Tempo's plans may go from "3 bad swaps" to "no legal flex".
   That IS the correct output and the epic asked for it — but it must be *labeled*, not silent.
   Mitigation: the `no-legal-flex` note names the locked-core size, the land count, and the declined
   cards with their lift, so the reader can see exactly what was suppressed and why.
2. **`is_land`-vs-`type_line` gets "fixed" back the wrong way by a later reader.** The DB column
   looks like the obvious test. Mitigation: the `_resolve_land_names` test seeds Sink into Stupor
   explicitly and asserts it is NOT a land, with a constraint comment naming the modal-DFC alias
   rows in `store.py:213`.
3. **The IN axis gate over-suppresses on thin tag derivation.** If `vulnerability_tags` returns a
   narrow set for an opponent, legitimate INs get declined. Mitigation: empty axis set → no
   suppression at all; and every decline is recorded in `in_suppressed` rather than dropped, so
   over-suppression is visible in the audit rather than invisible in the plan.
4. **Two render sites hardcode "thin data" and would mislabel the new degrade.** Caught in design
   (Unit 6); if a fourth site is added later it inherits the same bug. Mitigation: all sites render
   `plan.note`, which always carries its own named reason, rather than re-deriving prose from
   `degraded`.
5. **`plan_status` defaulting could mask a wiring miss.** If `_plan_matchups` forgets to set it on
   some branch, `__post_init__` silently fills `planned`/`thin-data`. Mitigation: every construction
   site inside `_plan_matchups` passes `plan_status` explicitly, and the unit tests assert the exact
   token per branch rather than only `degraded`.
6. **Scope creep into "which cards SHOULD be cut".** This feature only decides eligibility. It must
   not touch lift computation, `lock_threshold`, or the coverage model — that is
   `epic-sb-config-evaluation-matchup-slot-test`'s and `per-deck-castability`'s territory.


## Implementation notes

Stage: `drafting` → `implementing` (design commit) → `review` (this commit). Implemented to the
design above with no architectural deviation; three points where the design was tightened during
implementation are recorded below.

### What shipped

| Unit | Landing site |
|---|---|
| 1 — plan-status vocabulary + diagnostic fields | `src/legacy_engine/advisory/sideboard.py` (constants + `MatchupPlan.__post_init__`) |
| 2 — `_resolve_land_names` | `src/legacy_engine/advisory/sideboard.py` |
| 3 — `_in_axis_verdict` (+ `_format_suppressed`, `format_plan_declines`) | `src/legacy_engine/advisory/sideboard.py` |
| 4 — `_plan_matchups` eligibility rework | `src/legacy_engine/advisory/sideboard.py` |
| 5 — call-site wiring | `src/legacy_engine/advisory/sideboard.py` (`recommend_sideboard` Step 6b) |
| 6 — render honesty | `src/legacy_engine/cli.py` (2 sites), `src/legacy_engine/advisory/report.py` (2 sites) |

`docs/ARCHITECTURE.md`'s `sideboard.py` row was rolled forward to describe the land exemption, the
axis gate, the declined-candidate records, and the `no-legal-flex` degrade.

### Deviations from the design

1. **`format_plan_declines` was added as a public helper** (not in the unit list). Four render
   sites needed the same "what did this plan decline" string; three inlined copies would have
   drifted. `_format_suppressed` stayed private as the note-building primitive.
2. **A fourth render site was fixed** — `report.py`'s field-read AUDIT trail (`:420`), not just the
   three plan renders. It now carries `plan_status` and the declined list, which is where the
   audit reader will look when a plan comes back empty.
3. **The planned (≥1 swap) note also carries `declined off-axis IN`.** The design only put the
   declined summary on the zero-swap and degraded notes. A plan that swapped 2 cards while
   declining a higher-lift off-axis candidate is exactly the case where the reader needs to see
   the overruled signal, so it is surfaced there too.

### Honest-degrade path — how it is surfaced and tested

Surfaced three ways, all carrying the named reason rather than re-deriving prose from `degraded`:

- `MatchupPlan.plan_status == "no-legal-flex"` + `degraded=True` + `side_out`/`side_in` empty +
  `post_board == deck_maindeck` + `n_basis=0` / `tier="speculative"` (magnitude suppressed).
- `note` reads `vs <opp>: NO LEGAL FLEX — <N> card(s) locked core (≥65% archetype adoption);
  <M> land slot(s) exempt from cuts. No OUT/IN proposed; the 15's composition carries this
  matchup. Declined despite negative lift: <card> (lift -0.200, land), …`
- `out_suppressed` carries the full `(card, lift, reason)` list, rendered by every plan surface as
  a `declined:` / `[declined]` line.

Tested by `TestMatchupPlanFlex::test_no_legal_flex_degrades_honestly` (asserts the status, the
suppressed magnitude, the named reason, the declined records, and that the word "thin" does NOT
appear — the mislabel the two hardcoded render sites would have produced) and
`test_no_legal_flex_when_every_slot_is_ineligible` (proves the degrade is structural, fired on
slot eligibility before lift is read).

### Land-creature / MDFC finding

The corpus decided the test — see `## Corpus grounding`. Summary: `cards.is_land` is TRUE for 34
modal-DFC *spell* face-aliases that appear in corpus maindecks (Sink into Stupor 3,377 decks,
Shatterskull Smashing 3,228, Boggart Trawler 2,654, Fell the Profane 2,346, Agadeem's Awakening
2,140), so the column would have made all of them un-sideboardable. The `type_line` rule exempts
none of them and still catches Dryad Arbor (`'Land Creature — Forest Dryad'`, the only
land-creature in any corpus maindeck at 4,155 decks), transform lands whose front face is a land
(Westvale Abbey), and plain lands (Scalding Tarn). Transform cards whose land is the BACK face
(Ojer Pakpatiq, `'Legendary Creature — God'`) are correctly left eligible. No special-casing
beyond the type-line rule was needed. `test_resolve_land_names_uses_type_line_not_is_land_column`
pins this with the six verified rows and a constraint comment naming `store.py:213`.

### Goldens

No golden re-pins. The three `freshness-stripped CLI-body` goldens
(`test_conditioned_card_winrate.py`, `test_matchup_split_variant.py`) cover `report cards` /
`report subgroup` / `report matchups` and do not touch the matchup-plan render blocks. The two
hardcoded `"thin data — no per-matchup plan"` strings that changed had no test coverage asserting
them (verified by grep before editing).

### Verification

- `.venv/bin/python -m pytest -q` → **3218 passed, 1 skipped**. 26 new tests
  (`TestMatchupPlanFlex` 24, `TestMatchupPlanFlexIntegration` 2); zero existing tests modified.
- `.venv/bin/ruff check src/` → 527 findings, all pre-existing house style. Per-file delta against
  the base commit on the three touched files: `BLE001` +1 (the degrade-on-failure `except
  Exception` in `_resolve_land_names`, matching 27 existing) and `UP037` +6 (quoted annotations,
  matching 131 existing). No new class of finding. CI's ruff step is non-blocking (`|| true`).

### Test-integrity note

The first pass of the integration tests was a green lie: they looped over
`pkg.matchup_plans.items()` on a fixture that produces **zero** plans for an all-land maindeck (an
all-land deck has no nonland colors, so `compute_deck_colors` returns empty, no hoser is castable,
and `final_cards` is empty — `_plan_matchups` is never reached). They were replaced with two tests
that assert something real: a monkeypatch spy proving `recommend_sideboard` actually resolves and
passes `land_names` / `opponent_axes` / `card_axes` (the wiring the pure unit tests cannot reach),
and an end-to-end land sweep. Both now assert `pkg.matchup_plans` is non-empty first, so they fail
loudly rather than silently pass if the fixture ever stops producing plans.

### Known limitation (deliberate, out of scope here)

The `no-legal-flex` degrade cannot be exercised end-to-end through `recommend_sideboard` on the
existing hermetic fixture: an all-land maindeck can never reach the planner (no nonland colors →
no castable hosers → empty 15), and the fixture's `Control` archetype has too small a consensus
core to lock a mixed deck flat. The path is fully covered at the `_plan_matchups` level with
hand-built inputs. A corpus fixture with a consensus-tight archetype would close the gap; that
belongs with `epic-sb-advisor-correctness-backtest-ci-gate`'s hermetic backtest fixture, not here.
