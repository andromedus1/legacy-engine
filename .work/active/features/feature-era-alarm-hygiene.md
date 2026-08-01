---
id: feature-era-alarm-hygiene
kind: feature
stage: done
tags: [analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Era-alarm hygiene — registered-ban awareness + same-date multi-ban attribution

## Brief

Three related eras-surface findings: (1)+(2) the drift alarm's wording goes stale after a
ban is registered — post `eras confirm` (Candelabra), `eras run` still emits "possible
unregistered B&R change" even though the ban IS registered and the boundary is merely held
below acceptance; the alarm should consult the registered-events ledger and say so (two
parks merged — same defect). (3) Era-boundary attribution on a same-date double ban names
only the first matching card and can miss the load-bearing one (named Entomb, missed Nadu
— 91% of pre-ban Cephalid decks mained Nadu); attribution should consider all same-date
events and rank by entity relevance. Full member texts below.

## Member findings (absorbed from backlog)

---

### idea-alarm-registered-ban-wording


**Drift-alarm wording after a ban is registered but the era boundary is still held.** Post
`eras confirm` (Candelabra), the Tron alarm still reads "possible unregistered B&R change" —
technically stale: the ban IS registered; the era boundary is merely held below acceptance
(confirmation asymmetry, thin post-ban sample). The alarm's suppression/wording check should
also consult BAN_EVENTS directly: a registered ban date inside the recent window should render
"disturbance consistent with registered ban: <card> (<date>); era windows truncate via the ban
horizon until the new era accumulates sample" instead of the unregistered-B&R hint. Same for
the Grixis Reanimator [Shallow Grave] camp alarm if a parent-level attribution covers it.

---

### idea-eras-alarm-stale-after-registration


**Drift-alarm message is stale after ban registration.** Candelabra of Tawnos is registered in
`src/legacy_engine/data/banlist/events.json` (via `eras confirm` on 2026-07-12), but today's
`eras run` still emits `// ⚠ Tron: unattributed disturbance (p_change=0.929) — possible
unregistered B&R change` (same for Grixis Reanimator [Shallow Grave]). The alarm should consult
BAN_EVENTS and say something like "registered ban (Candelabra 2026-06-29) awaiting detectable
boundary — post-ban sample too thin" instead of implying no one has registered it.
Repro: `eras run` (2026-07-13), tail of output.

---

### bug-era-attribution-same-date-ban


Era-boundary attribution named Entomb and missed Nadu on the 2025-11-10 double ban for
Cephalid breakfast — its trigger reads "ban: Entomb (2025-11-10) — inclusion unverified
(not in this entity's flex band)" even though 91% of pre-ban Cephalid decks mained Nadu.
The attribution inclusion check only scans the entity's flex band, so it verified the
wrong same-date ban; `analytics.affectedness.archetype_valid_since` (any-card >=25%
pre-ban inclusion, either board) got it right. Align the attribution check: on
multi-card ban dates, verify inclusion per banned card across the full deck, and name
the card that actually hits.

## Design decisions
<!-- --only-questions pass 2026-07-31: no user-facing ambiguities — direction is pinned by
the absorbed member texts, parent-epic decisions, and existing project patterns. Full
feature-design may proceed without an interactive round. -->

## Architectural choice

**Chosen: one shared same-date-cohort ranking primitive in `attribution.py`, reused by both the
attribution fix (B) and the alarm-wording fix (A).** Both findings are really the same underlying
gap wearing two hats: "when several curated ban-ledger facts compete near one date/entity, which
one actually explains what we're looking at, and how do we say so honestly." `attribution.py`
already owns the ban/release/unattributed decision for era boundaries; I extend it with three new
public functions — `events_on_nearest_date` (which BAN_EVENTS date is closest, and every card
banned on it), `rank_same_date_cards` (rank that cohort by this entity's own pre-boundary
inclusion), and `is_plausible_ban` (the shared "not proven irrelevant" gate) — and rewrite
`_attribute_one` to use them (fixes B). `run.py`'s `compute_drift_alarms` gains a `ban_events`
parameter and calls the *same* three functions, anchored on the BOCPD tail's own peak date instead
of a boundary date, to decide whether an "unattributed" alarm should instead say a ban is
registered but pending (fixes A). `AlarmFlag` gains two backward-compatible fields (`kind`, `card`)
so the softened wording is structurally testable, not just a string to grep.

Verified empirically (not just by inspection) against the project's own existing hermetic fixture
(`tests/analytics/eras/test_run.py`'s `_build_corpus`/`_con` — Tron/Drift/Filler, real
Undercity-Informer-dated cliff) before committing to this shape: with the REAL shipped
`BAN_EVENTS`, every boundary in that 3-entity fixture is `bh_accepted=False` (expected — fleet-wide
BH-FDR has ~no power at n=3), so **today's code already fires "possible unregistered B&R change"
for Tron even though Tron's own boundary is correctly ban-attributed to Undercity Informer** — the
exact bug class Finding A describes, reproducible with zero new fixtures. Further, the alarm's own
weekly-forced BOCPD peak (`argmax` over the last 3 `p_change` values) landed on **2026-05-18** for
Tron/Drift/Filler alike — an exact, zero-day match to Undercity Informer's registered date —
confirming the peak-date anchor is a sound, precise signal to key the ledger lookup off, not a
hand-wavy heuristic.

Options considered:

1. **(chosen) Shared cohort-ranking primitive, reused by both findings.** Pros: one tier
   semantic ("verified+affecting" > "unverifiable/ubiquitous" > "verified+irrelevant") lives in
   one place and can't drift between the two call sites; the Tron/Candelabra "ubiquitous card
   excluded from its own flex band" nuance — the epic's own headline case — is easy to get subtly
   wrong twice if written twice. Cons: `run.py` takes a new dependency on three more names from
   `attribution.py` (already depends on two).
2. **Independent fixes — a bespoke lighter-weight nearest-ban lookup inside `run.py`'s alarm
   code, and a separate ranking fix inside `_attribute_one` that isn't exposed as a reusable
   primitive.** Rejected: duplicates the exact "which same-date card actually hit" logic in two
   places with no shared test surface, and the two implementations' notions of "plausible" would
   have no structural reason to agree (magic-number drift risk: Finding A needs the SAME
   ubiquitous-card exception Finding B needs, or the Tron repro breaks again in the alarm path
   even after B is fixed in the attribution path).
3. **Persist the alarm's structured verdict into `entity_eras`** (new `alarm_kind`/`alarm_card`
   DDL columns) so `eras list`/`eras explain`/`window.py`'s audit lines could query on kind, not
   just display free text. Rejected for this stride: no current consumer reads anything but
   `alarm_note`/`alarm_fired` back from a persisted run; persisting the corrected `.note` string
   (no schema change) already fixes every display site (`eras run`, `eras explain`, and
   `advisory/window.py`'s `// ⚠` audit lines via `consume.py`'s `HorizonMeta.alarm`, which all
   read `alarm_note` straight through). Flagged in Risks as a cheap future add — `write_entity_eras`
   already does a full DROP+recreate every run, so adding columns later needs no migration.

## Implementation Units

### Unit 1 (trickiest — design it first): same-date cohort ranking in attribution

**File**: `src/legacy_engine/analytics/eras/attribution.py`

Rename/generalize the private `_nearest_ban_event` (single closest event) into two public,
independently-testable steps, add the shared plausibility gate, and rewrite `_attribute_one` to
rank the WHOLE same-date cohort instead of picking whichever event a stable sort happened to place
first (today: alphabetical-by-card, since `load_ban_events` sorts `(date, card)` — which is exactly
why "Entomb" beat "Nadu, Winged Wisdom" on the 2025-11-10 double ban).

```python
# Public (was `_BAN_AFFECT_THRESHOLD`) — now shared with run.py's alarm-wording gate (Unit 2),
# not just this module's ban-attribution decision.
BAN_AFFECT_THRESHOLD: float = 0.25  # banned-card inclusion in pre-ban decks -> "affected"


def is_plausible_ban(inclusion_rate: float | None) -> bool:
    """True unless we have POSITIVE evidence this entity doesn't run the card enough for a
    nearby ban to explain its disturbance. ``None`` (not trackable in this entity's own flex
    band — e.g. a ubiquitous chassis card like Candelabra of Tawnos in Tron, or one this entity
    never runs at all) is plausible-by-default: unproven, not disproven. Only a MEASURED rate
    below ``BAN_AFFECT_THRESHOLD`` is disqualifying. Shared by `_attribute_one`'s ban/fall-through
    decision (Unit 1) and `run.compute_drift_alarms`'s wording gate (Unit 2) so the two call sites
    can never quietly disagree on what "plausible" means.
    """
    return inclusion_rate is None or inclusion_rate >= BAN_AFFECT_THRESHOLD


def events_on_nearest_date(
    ban_events: tuple[tuple[date, str, str], ...], boundary_date: date, tolerance_days: int,
) -> tuple[date, list[str]] | None:
    """The single BAN_EVENTS date closest to ``boundary_date`` within ``tolerance_days`` (ties
    broken by earliest date), plus EVERY card banned on that date — the same-date cohort a single
    boundary/disturbance must rank across, rather than the first card in list/alphabetical order.
    ``None`` when nothing is within tolerance.
    """
    candidates = [
        (abs((event_date - boundary_date).days), event_date)
        for event_date, _card, _reason in ban_events
        if abs((event_date - boundary_date).days) <= tolerance_days
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    _delta, nearest_date = candidates[0]
    cards = sorted({card for event_date, card, _r in ban_events if event_date == nearest_date})
    return nearest_date, cards


def rank_same_date_cards(
    cards: list[str], s: "EntitySeries | None", boundary_date: date,
) -> list[tuple[str, float | None]]:
    """Rank a same-date ban cohort by entity relevance, best-supported first:

    1. verified AND affecting (``inclusion_rate >= BAN_AFFECT_THRESHOLD``) — ranked by inclusion
       descending (the 2025-11-10 fix: Nadu's 91% must outrank Entomb here);
    2. unverifiable (``_card_inclusion_before`` returns ``None`` — not in this entity's own flex
       band, e.g. Candelabra in Tron) — unproven but not ruled out, so these outrank...
    3. verified BUT below threshold — this entity demonstrably does not run the card enough to be
       the cause of ITS OWN boundary (e.g. a 15%-inclusion card on an entity whose disturbance is
       something else entirely).

    A single-card cohort trivially returns that one card — this generalizes the existing
    single-candidate behavior rather than replacing it (every current test with exactly one
    same-date event gets byte-identical output).
    """
    scored = [(card, _card_inclusion_before(s, card, boundary_date)) for card in cards]

    def _tier(rate: float | None) -> int:
        if rate is not None and rate >= BAN_AFFECT_THRESHOLD:
            return 0
        if rate is None:
            return 1
        return 2

    def _key(item: tuple[str, float | None]) -> tuple[int, float, str]:
        card, rate = item
        return (_tier(rate), -(rate if rate is not None else 0.0), card)

    return sorted(scored, key=_key)


def _attribute_one(
    boundary, boundary_date: date, s: "EntitySeries | None", *,
    ban_events: tuple[tuple[date, str, str], ...], releases: dict[str, date],
    tolerance_days: int, corpus_first_seen: dict[str, date] | None = None,
) -> Attribution:
    nearest = events_on_nearest_date(ban_events, boundary_date, tolerance_days)
    if nearest is not None:
        event_date, cards = nearest
        ranked = rank_same_date_cards(cards, s, boundary_date)
        card, rate = ranked[0]
        secondaries = [c for c, _r in ranked[1:]]
        secondary_note = f"; also banned this date: {', '.join(secondaries)}" if secondaries else ""
        if rate is None:
            return Attribution(kind="ban", card=card, detail=(
                f"ban: {card} ({event_date.isoformat()}) — inclusion unverified "
                f"(not in this entity's flex band){secondary_note}"
            ))
        if rate >= BAN_AFFECT_THRESHOLD:
            return Attribution(kind="ban", card=card, detail=(
                f"ban: {card} ({event_date.isoformat()}, {rate:.0%} pre-boundary inclusion)"
                f"{secondary_note}"
            ))
        # Best-ranked same-date card is verified but below threshold -> none of this date's bans
        # explain this boundary; fall through to the release check, then unattributed (unchanged).

    for sig in boundary.signals:
        # ... release-check body UNCHANGED from today's implementation ...
        ...

    return Attribution(
        kind="unattributed", card=None,
        detail="unattributed disturbance — possible unregistered B&R change",
    )
```

`attribute_boundaries`'s own public signature is UNCHANGED — this is entirely an internal
rewrite plus two newly-public helper functions.

**Implementation Notes**:
- `_card_inclusion_before` (unchanged) already returns `None` for "not in this entity's flex
  band" AND "no pre-boundary sample" AND "`s is None`" — `rank_same_date_cards` doesn't need to
  distinguish these, matching existing behavior exactly.
- The tier ordering is the crux: unverifiable (tier 1) must rank ABOVE verified-but-below (tier
  2) — reversing this would make a merely-thin-but-measured card win over a ubiquitous,
  unmeasurable one, breaking the Tron/Candelabra headline case the moment it shares a date with
  any other ban.
- `events_on_nearest_date` restricts the cohort to cards sharing the single CLOSEST matching
  date (not every event anywhere within the tolerance window) — deliberately narrower than "rank
  every nearby event regardless of date," matching the finding's literal "same-date" framing and
  avoiding a tier ranking that could paradoxically prefer a well-supported but less-proximate
  event over a same-day one.

**Acceptance Criteria**:
- [ ] `events_on_nearest_date(ban_events, boundary_date, tolerance_days)` returns
      `(nearest_date, [all cards banned that date])`, sorted card list, or `None` outside tolerance.
- [ ] `rank_same_date_cards` orders a 2025-11-10-shaped cohort (Entomb unverifiable, Nadu 91%
      verified) with Nadu first.
- [ ] `is_plausible_ban(None) is True`; `is_plausible_ban(0.25) is True`;
      `is_plausible_ban(0.24) is False`.
- [ ] Every existing `tests/analytics/eras/test_attribution.py` test (15 tests as of this design)
      passes unmodified — single-candidate cohorts are byte-identical to today.
- [ ] A new same-date double-ban test (Entomb/Nadu-shaped) attributes to the higher-inclusion
      card and lists the other as a secondary in `.detail`.

---

### Unit 2: ban-ledger-aware drift-alarm wording

**File**: `src/legacy_engine/analytics/eras/run.py`

```python
from legacy_engine.analytics.eras.attribution import (
    Attribution,
    attribute_boundaries,
    events_on_nearest_date,
    is_plausible_ban,
    rank_same_date_cards,
)

_ALARM_KINDS = frozenset({"unattributed", "registered_pending"})


@dataclass(frozen=True)
class AlarmFlag:
    """One entity's drift alarm — the loud, human-facing half of the banlist-currency loop.

    ``kind="unattributed"`` (default, backward-compatible): no ban is registered near the
    disturbance (or one is, but this entity demonstrably doesn't run it enough to be its cause) —
    the classic "possible unregistered B&R change" case.
    ``kind="registered_pending"``: a ban IS registered in BAN_EVENTS near the disturbance's own
    peak date, but the era detector hasn't accepted/floor-cleared a boundary for it yet (thin
    post-ban sample) — the alarm still fires (there's no consumable `stable_since` boundary yet)
    but must not imply the ban itself is unregistered. ``card`` names the registered card when
    ``kind="registered_pending"``, else ``None``.
    """

    entity: str
    p_change: float
    note: str
    kind: str = "unattributed"
    card: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in _ALARM_KINDS:
            raise ValueError(
                f"AlarmFlag: kind {self.kind!r} must be one of {sorted(_ALARM_KINDS)}"
            )


def compute_drift_alarms(
    series: dict[str, EntitySeries],
    eras: dict[str, EntityEras],
    attributions: dict[tuple[str, str], Attribution],
    *,
    ban_events: tuple[tuple[date, str, str], ...] = (),
    tolerance_days: int = _ATTRIBUTION_TOLERANCE_DAYS,
) -> dict[str, AlarmFlag]:
    """... (docstring unchanged, plus:)

    ``ban_events``/``tolerance_days`` (new, both default to the prior no-ledger behavior):
    once a disturbance is confirmed (BOCPD bar cleared) and NOT already covered by an accepted,
    attributed boundary, check whether a ban is nonetheless registered near the disturbance's own
    BOCPD peak date (not `recent_start` — the peak pins the actual moment of surprise within the
    recent window). If a same-date cohort exists there and its best-ranked card is
    `is_plausible_ban`, the alarm still fires but with `kind="registered_pending"` wording naming
    that card instead of implying nothing has been registered. Default `ban_events=()` makes
    `events_on_nearest_date` always return `None`, so any caller that doesn't pass a ledger
    (all existing `TestAlarmCalibration` tests) gets today's `kind="unattributed"` output,
    byte-identical.
    """
    alarms: dict[str, AlarmFlag] = {}
    for entity, s in series.items():
        complete = [b for b in s.buckets if b.complete]
        if len(complete) < _ALARM_MIN_COMPLETE_BUCKETS:
            continue
        successes = np.array([b.decks for b in complete], dtype=float)
        trials = np.array([b.field_decks for b in complete], dtype=float)
        total_trials = float(trials.sum())
        if total_trials <= 0:
            continue
        recent_succ = successes[-_ALARM_SHARE_WINDOW_BUCKETS:]
        recent_tri = trials[-_ALARM_SHARE_WINDOW_BUCKETS:]
        if float(recent_tri.sum()) <= 0:
            continue
        share = float(recent_succ.sum() / recent_tri.sum())
        if share < _ALARM_SHARE_FLOOR:
            continue

        result = beta_binomial_bocpd(successes, trials)
        recent = result.p_change[-_ALARM_RECENT_BUCKETS:]
        max_p = float(recent.max())
        if max_p < _ALARM_BAR:
            continue

        recent_start = complete[-min(_ALARM_RECENT_BUCKETS, len(complete))].start
        entity_eras = eras.get(entity)
        covered = False
        if entity_eras is not None:
            covered = any(
                b.bh_accepted and not b.floor_rejected and b.date >= recent_start
                and attributions.get((entity, b.date), _UNATTRIBUTED_DEFAULT).kind != "unattributed"
                for b in entity_eras.boundaries
            )
        if covered:
            continue

        # NEW: even when uncovered, a ban may already be registered near the disturbance's own
        # peak — the boundary is simply held below acceptance (thin post-ban sample), not
        # evidence nobody has registered anything.
        recent_window = complete[-_ALARM_RECENT_BUCKETS:]
        peak_date = date.fromisoformat(recent_window[int(np.argmax(recent))].start)
        nearest = events_on_nearest_date(ban_events, peak_date, tolerance_days)
        if nearest is not None:
            event_date, cards = nearest
            ranked = rank_same_date_cards(cards, s, peak_date)
            card, rate = ranked[0]
            if is_plausible_ban(rate):
                secondaries = [c for c, _r in ranked[1:]]
                secondary_note = (
                    f" (also banned this date: {', '.join(secondaries)})" if secondaries else ""
                )
                alarms[entity] = AlarmFlag(
                    entity=entity, p_change=max_p, kind="registered_pending", card=card,
                    note=(
                        f"registered ban ({card} {event_date.isoformat()}) — boundary held "
                        f"pending confirmation data (p_change={max_p:.3f}){secondary_note}"
                    ),
                )
                continue
                # else: best-ranked card is verified-and-below-threshold (e.g. Drift's 15%
                # Undercity Informer inclusion) -> this entity's disturbance genuinely isn't
                # explained by that ban; fall through to the unattributed wording below.

        alarms[entity] = AlarmFlag(
            entity=entity, p_change=max_p, kind="unattributed", card=None,
            note=(
                f"unattributed disturbance (p_change={max_p:.3f}) — "
                "possible unregistered B&R change"
            ),
        )
    return alarms
```

`run_eras` gains one new keyword-only parameter and threads it to both consumers of the ledger:

```python
def run_eras(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    alpha: float = 0.05,
    seed: int = 0,
    release_source: "Callable[[duckdb.DuckDBPyConnection], dict[str, date]] | None" = None,
    ban_events: "tuple[tuple[date, str, str], ...] | None" = None,
) -> ErasRunResult:
    """... (docstring gains: ``ban_events`` defaults to ``None``, which resolves to the real,
    module-level `BAN_EVENTS` (byte-identical to today for the CLI and every existing caller);
    tests inject a synthetic tuple here for a fully hermetic same-date-ban / registered-pending
    end-to-end proof, never touching the shipped `events.json`.)
    """
    series = build_entity_series(con, provenance=provenance)
    events = ban_events if ban_events is not None else BAN_EVENTS
    ...
    attributions = attribute_boundaries(
        eras, ban_events=events, releases=releases, series=series,
        tolerance_days=_ATTRIBUTION_TOLERANCE_DAYS, corpus_first_seen=corpus_first_seen,
    )
    alarm_series = build_entity_series(con, provenance=provenance, force_bucket_weeks=1)
    alarms = compute_drift_alarms(alarm_series, eras, attributions, ban_events=events)
    ...
```

No changes needed to `cli.py`, `store.py`, or `advisory/window.py` / `analytics/eras/consume.py` —
every one of those reads `alarm.note` / the persisted `alarm_note` column straight through
(verified by direct grep: `cli.py:6984,7097` and `consume.py:123,134` all just interpolate the
note text), so fixing `.note`'s construction here fixes `eras run`, `eras explain`, and
`advisory/window.py`'s `// ⚠` audit lines with zero changes to any of those three files.

**Implementation Notes**:
- The peak-date anchor (`recent_window[argmax(recent)].start`) was empirically verified against
  the project's real `BAN_EVENTS` + the existing 3-entity hermetic fixture before writing this
  design: it lands EXACTLY on 2026-05-18 (Undercity Informer's registered date) for all three
  entities in that fixture — a 0-day delta, well inside any reasonable tolerance.
- `is_plausible_ban` gating is what keeps Drift's alarm (15% Undercity Informer inclusion, `rate
  < BAN_AFFECT_THRESHOLD`) honestly "unattributed" — the SAME nearby, registered ban that
  correctly softens Tron's wording must NOT soften Drift's, since Drift's own data shows it isn't
  the cause. Without this gate, Finding A's fix would silently break the project's own existing
  `TestErasExplain.test_walks_drift_boundary_derivation_unattributed_with_alarm` assertion.
- `kind`/`card` are NOT persisted to `entity_eras` (no DDL change) — only `.note` is (unchanged
  schema, `alarm_note VARCHAR`). This is a deliberate, documented scope cut (Option 3 above); the
  corrected wording is still visible everywhere it's ever displayed, live or replayed.
- `ban_events=()` / `tolerance_days=_ATTRIBUTION_TOLERANCE_DAYS` defaults on
  `compute_drift_alarms` and `ban_events=None` on `run_eras` are the gated-additive-augmentation
  no-op path: every existing call site (CLI, all current tests) is untouched and byte-identical.

**Acceptance Criteria**:
- [ ] `compute_drift_alarms(series, eras, attributions)` (no `ban_events`, exactly today's call
      shape) returns `kind="unattributed"` alarms with the unchanged note text — all 8 existing
      `TestAlarmCalibration` tests pass unmodified.
- [ ] Given the real `BAN_EVENTS` and the existing `_con()`/`_build_corpus()` fixture, `run_eras`'s
      `result.alarms["Tron"]` has `kind="registered_pending"`, `card="Undercity Informer"`, and
      `.note` contains "registered ban" and does NOT contain "possible unregistered".
- [ ] In that SAME run, `result.alarms["Drift"]` stays `kind="unattributed"` with "possible
      unregistered B&R change" in `.note` (proves the plausibility gate, not just presence of a
      nearby ban, drives the wording).
- [ ] `eras run` and `eras explain` CLI output for Tron shows `// ⚠ Tron: registered ban (...)`
      end-to-end (`tests/test_cli_eras.py`), sourced entirely from the existing `_build_eras_db`
      fixture (real Undercity Informer date) — no new CLI code paths touched.

## Implementation Order

1. **Unit 1 — `attribution.py`** (trickiest; the tier semantics are the load-bearing decision
   both units depend on). Land it green against all 15 existing + new same-date-cohort tests
   before touching `run.py` at all, since Unit 2 imports Unit 1's new public names directly.
2. **Unit 2 — `run.py`** (`AlarmFlag`, `compute_drift_alarms`, `run_eras`). Depends on Unit 1's
   `events_on_nearest_date` / `rank_same_date_cards` / `is_plausible_ban` existing and being
   correct — cannot start meaningfully before Unit 1 is done.
3. **Tests throughout** — per this project's convention each unit lands with its own tests in the
   same stride (not a separate trailing "testing" unit); see `## Testing` below for the full,
   file-by-file plan covering both units plus the CLI end-to-end proof (Finding C).

## Testing

All new/changed tests are hermetic: hand-built fixtures or `store.connect(":memory:")` /
`tmp_path`-backed DuckDB, exactly matching each file's existing house style. Nothing here ever
touches the default DB or the shipped `data/banlist/events.json` — synthetic same-date ban tuples
are passed directly as `ban_events=(...)` parameters (`attribute_boundaries` already takes this
injected; `run_eras` gains the same injection point in Unit 2).

### `tests/analytics/eras/test_attribution.py`
- `TestEventsOnNearestDate` (new): returns the full same-date cohort; `None` outside tolerance;
  picks the closer of two distinct dates when both are in tolerance.
- `TestRankSameDateCards` (new): verified-affecting outranks unverified; unverified outranks
  verified-below-threshold (the ordering Unit 1's docstring calls the crux); two verified cards
  rank by inclusion descending. Uses two new local hand-built helpers alongside the file's
  existing `_trackable_card_series`/`_ubiquitous_untracked_card_series`: `_two_card_series(entity,
  {card: rate, ...})` and a mixed verified+ubiquitous builder — same house style (no shared
  conftest dependency), local to this file per its own docstring convention.
- `TestIsPlausibleBan` (new): `None` -> `True`; `>= 0.25` -> `True`; `< 0.25` -> `False`.
- `TestSameDateMultiHitAttribution` (new) — the Finding B repro, generalized:
  - Entomb (unverifiable) + Nadu (91% verified) same date -> attributes to Nadu, lists Entomb as
    a secondary in `.detail`.
  - Two verified cards, different inclusion rates, same date -> higher-inclusion card named.
  - All same-date cards verified-and-below-threshold -> falls through to `unattributed` (never
    silently picks one at random).
  - An unverified card outranks a verified-but-below-threshold sibling on the same date.
- All 15 pre-existing tests in this file must still pass unmodified (single-candidate cohorts are
  a strict special case of the new ranking).

### `tests/analytics/eras/test_run.py`
- `TestAlarmCalibration` additions (direct `compute_drift_alarms` calls, no DB — matches the
  class's existing style):
  - a `tron_cliff_series`-shaped disturbance + an injected `ban_events` entry near the cliff date,
    with the series' own inclusion of that card at 100% (mirrors `_ubiquitous_untracked_card_series`'s
    shape) -> `kind="registered_pending"`, `card` set, "possible unregistered" absent from `.note`.
  - same shape but the card's tracked inclusion is 15% (`< BAN_AFFECT_THRESHOLD`) -> stays
    `kind="unattributed"`, unchanged note (the Drift-shaped case, proving the plausibility gate).
  - no `ban_events` argument at all (today's exact call shape) -> `kind="unattributed"`,
    byte-identical note — the gated-additive no-op proof.
  - two ban events on the same nearby date, one plausible one not -> alarm names the plausible one.
- `TestRunErasEndToEnd` additions, reusing the EXISTING module-scoped `run_result_and_rows`
  fixture (no new corpus — this fixture already uses the real `BAN_EVENTS`, and this design's own
  empirical check above showed it already reproduces Finding A verbatim):
  - `result.alarms["Tron"].kind == "registered_pending"`, `.card == "Undercity Informer"`,
    `"possible unregistered" not in .note`.
  - `result.alarms["Drift"].kind == "unattributed"` and `"possible unregistered B&R change" in
    .note` — unchanged from today, proving the fix doesn't over-fire on Drift's genuinely-unrelated
    disturbance.

### `tests/test_cli_eras.py`
- New `TestErasRunRegisteredBanWording` class, reusing the existing `_build_eras_db` builder
  (same corpus, real Undercity Informer date) — no new fixture machinery:
  - `eras run --db <path>` output contains `// ⚠ Tron: registered ban` and `Undercity Informer`,
    and still contains `// ⚠ Drift: unattributed disturbance` (both wordings visible in one run,
    proving the plausibility gate end-to-end through the CLI).
  - `eras explain Tron --db <path>` output's alarm line reads the corrected wording too (proves
    `eras explain`'s separate echo site, `cli.py:7097`, needed no code change — it was already
    reading `.alarm_note` straight through).

### Integration points
- `attribution.py` <-> `run.py`: the three new public functions are the seam; Unit 2's tests
  exercise them THROUGH `compute_drift_alarms`, not by re-deriving the ranking independently, so a
  future change to the tier semantics can't silently desync the two call sites without a test
  catching it.
- `run.py` <-> `cli.py` / `advisory/window.py` / `consume.py`: no code changes there, but the CLI
  and window.py tests above are the seam proof that `.note`/`alarm_note` propagation still works
  end-to-end after the internal `AlarmFlag` shape change.

## Risks

- **Peak-date anchor generalization** — the `argmax`-over-last-3-buckets peak-date heuristic was
  validated against exactly one real shape (a sharp single-week cliff, weekly-forced buckets). A
  slower multi-week decline, or a disturbance whose clearest BOCPD signal sits just outside the
  3-bucket recent window, could miss the ledger lookup and silently keep the old (safe, if
  imprecise) "unattributed" wording. **Fallback**: failure mode is graceful — worst case is no
  improvement for that entity this run, not a wrong claim; nothing regresses relative to today.
- **`is_plausible_ban`'s shared threshold reuse** — `BAN_AFFECT_THRESHOLD` (0.25) was calibrated
  for the FORMAL era-boundary "ban" attribution decision (Unit 1), not originally for a softer
  wording courtesy (Unit 2). Reusing one constant avoids a second magic number and keeps the two
  units from disagreeing, but hasn't been dogfooded specifically as an alarm-wording bar yet.
  **Fallback**: if real dogfooding shows the wording flips at the wrong sensitivity, split the
  constant (`ALARM_PLAUSIBILITY_THRESHOLD` distinct from `BAN_AFFECT_THRESHOLD`) — a small,
  localized change, not a redesign.
- **Unverified/ubiquitous fallback stays permissive** — Filler (a Filler entity that runs
  Undercity Informer 0% of the time) already gets attributed `kind="ban"` today via the existing
  "not in this entity's flex band" fallback (confirmed empirically), and will now ALSO get
  `kind="registered_pending"` alarm wording for the same reason. This is a **pre-existing**
  permissiveness in `_card_inclusion_before`'s "excluded from flex band = unverifiable, not
  disqualified" contract (documented as deliberate for the real Candelabra/Tron case), not a
  regression this feature introduces — flagged here so it isn't mistaken for new scope creep if
  noticed later.
- **Structured alarm state not persisted (Option 3, deferred)** — `kind`/`card` live only on the
  in-memory `ErasRunResult` from a fresh `run_eras` call, not in `entity_eras`. Any future consumer
  that wants to query "which entities are `registered_pending` right now" from a stored run (rather
  than re-running `eras run`) will need a small follow-up DDL addition — cheap given
  `write_entity_eras`'s full-rebuild-every-run contract, but out of scope here since nothing
  currently needs it.

## Child stories

None — single-stride. Both fixes touch two files (`attribution.py`, `run.py`) with a single,
shared seam (three new public functions), no parallelizable chunks, no cross-session sizing
concern, and one homogeneous test surface (pytest, hermetic DB/fixtures) — none of Phase 7's
spawn criteria hold.

## Implementation notes

Implemented exactly to design — no deviations from the architectural choice or unit signatures.

**Files touched**: `src/legacy_engine/analytics/eras/attribution.py`,
`src/legacy_engine/analytics/eras/run.py`, `tests/analytics/eras/test_attribution.py`,
`tests/analytics/eras/test_run.py`, `tests/test_cli_eras.py`.

**"No changes needed to cli.py/store.py/window.py/consume.py" — verified true.** Grepped and
read every alarm-note call site before writing code: `cli.py:6989-6991` (`eras run`) and
`cli.py:7103-7104` (`eras explain`) both do `f"// ⚠ {entity}: {result.alarms[entity].note}"` /
`f"\n// ⚠ {r.alarm_note}"` — plain string interpolation. `store.py` persists only
`alarm_fired`/`alarm_p_change`/`alarm_note` (no `kind`/`card` columns exist or were added — this
was a deliberate scope cut, Option 3 above). `consume.py:123,134` read `alarm_note` straight into
`HorizonMeta.alarm`. `advisory/window.py:168-169` formats `h.alarm` as a plain string in
`f"// ⚠ {a}: {h.alarm}"`. None of the four files were touched; all four were run through the full
test suite below to prove the claim, not just asserted by inspection.

**Test evidence**:
- `tests/analytics/eras/test_attribution.py`: 18 pre-existing + 14 new = 32 passed.
- `tests/analytics/eras/test_run.py`: 25 pre-existing + 6 new = 31 passed.
- `tests/test_cli_eras.py`: 15 pre-existing + 2 new = 17 passed.
- `tests/analytics/eras/test_store.py` + `tests/analytics/eras/test_consume.py` (AlarmFlag
  backward-compat check): 25 passed, unmodified.
- Full suite: `3027 passed, 1 skipped, 1 xfailed` (skip/xfail pre-existing, unrelated to this
  feature).
- `ruff check src/`: 23 pre-existing errors (none in `attribution.py`/`run.py`, confirmed by
  diffing against the pre-change baseline) — `attribution.py`/`run.py` individually clean.

**Empirical grounding note**: this feature's implementation was carried out against
`origin/main` at PR #62/#63 (catalog-lint, sweep-polish). The design doc for this feature had
been drafted on a locally-diverged `main` that never got pushed — see the commit note on this
same commit for the branch-divergence finding surfaced during implementation.
