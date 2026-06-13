---
id: feature-new-set-ingestion-and-speculation
kind: feature
stage: drafting
tags: [ingestion, analytics, methodology, hold-for-review]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

## Design

> Status: design complete, held for human review. See the `## Hold` note at the end. Stage stays
> `drafting`; no code written.

### Decision: one feature, two cohesive sub-systems, ONE child story spun out

The feature has two genuinely separable mechanisms that share almost no code:

1. **Release-aware ingestion** — a scheduled scan + a "new cards since last ingest" diff that flows
   newly-printed cards into the `cards` table. Pure ingestion-layer plumbing; no analytics.
2. **No-history speculation** — a forecasting path that scores a zero-data card by intrinsic features
   and an analogous-card empirical prior, labelled speculative. Pure analytics/advisory; no network.

They are coupled only by *intent* (a new set is the moment you most want both), not by code. The diff
from (1) is the **trigger and input** for (2): the set of new card names is exactly the candidate list
the speculator forecasts on. That is a data hand-off (a `list[str]` of new names), not a code
dependency — so I keep them in one feature but build them as independently-shippable units.

**Child-story decomposition:** the speculation method's **analogous-card nearest-neighbour matcher**
(Unit 4) is the one piece with real algorithmic risk and standalone testability — it is a pure
similarity function over `Card` + tags that deserves its own behaviour-derived test suite and could be
reused later (e.g. by gap-discovery adjacency). I spin it out as a child story
`new-set-ingestion-and-speculation-analogous-matcher` at `drafting` (held). Everything else is
plumbing or thin composition and stays inline as units in this feature body.

The insight the item records — **a new set is a soft ban-regime shift with no historical data** — is
the design's north star for the honesty posture: just as `affectedness.py` truncates matchup history
at a ban, a new card has *no* valid history at all, so its only honest confidence floor is
`speculative` with an explicit "pre-data forecast" label. We never let a forecast masquerade as an
empirical estimate.

---

### Part 1 — Release-aware ingestion

#### What "release-aware" actually requires (and what it does NOT)

Scryfall's `oracle_cards` bulk **already contains** every card the moment it is in Scryfall's
database — which is typically on or shortly before a set's official release (preview/prerelease
windows aside). So we do **not** need a separate "release calendar" feed to *get* the cards: a forced
bulk re-download already pulls them. What we lack today is:

- **A trigger** — `seed cards` is run by hand; nothing prompts a re-pull when a set drops.
- **A diff** — `seed cards` does a `store.rebuild()` (drop + full reload), so we never learn *which*
  cards are new. The diff is the load-bearing artifact: it is both the human-facing "new cards to test
  this week" signal and the input list for the speculator.

So Part 1 is two narrow additions: a **set-release scan** (so the trigger is informed, not a blind
periodic full re-pull) and a **diff-producing ingest** (so re-ingest yields a typed "new since last
ingest" delta instead of silently rebuilding).

#### Mechanism

**Release scan (`ingestion/releases.py`, new).** Scryfall exposes `GET /sets` — a list of every set
with `code`, `name`, `released_at` (ISO date), `set_type`, and `card_count`. This is the release
calendar, already in our existing source; no new external integration, no new auth.

```python
class SetRelease(LegacyEngineModel):       # subclasses LegacyEngineModel (extra="ignore")
    code: str
    name: str
    released_at: date | None = None
    set_type: str = ""
    card_count: int = 0

def fetch_sets(client: ScryfallClient) -> list[SetRelease]: ...
    # GET {SCRYFALL_API_BASE}/sets, parse .data[] → SetRelease, drop unmodeled keys.

def upcoming_and_recent(sets, *, today, horizon_days=30, lookback_days=14) -> ReleaseScan: ...
    # Pure split: upcoming = released_at in (today, today+horizon];
    #             recently_released = released_at in [today-lookback, today].
    # No legality filter here — Scryfall set_type doesn't encode Legacy-legality, and a "supplemental"
    # product (Secret Lair, Commander precon) can still contain Legacy-legal reprints/new cards.
    # Legality is decided downstream per-card by the existing BanListSnapshot path, not per-set.
```

`ReleaseScan` is a small frozen dataclass `{upcoming: list[SetRelease], recently_released:
list[SetRelease], scanned_at: date}`. It is purely informational — it tells the operator (and a future
scheduler) *that* a set just dropped or is imminent, so the bulk re-pull is informed rather than a
blind nightly full download. **It does not gate ingestion**: the diff (below) is the authoritative
"what's new" signal, because Scryfall's set-release date and bulk-availability date don't always
coincide (digital-only cards, staggered previews).

**Diff-producing ingest (`ingestion/store.py` + `scryfall.py`, extended).** Today `seed cards` calls
`store.rebuild()` then `load_cards()`. We add a non-destructive path that computes the delta:

```python
# store.py — new
def existing_card_names(con) -> set[str]:
    """Set of card names currently in the cards table (empty if table absent)."""

@dataclass(frozen=True)
class IngestDiff:
    new_names: tuple[str, ...]       # in bulk, absent from table before this load
    total_after: int
    scryfall_updated_at: str | None  # the bulk file's updated_at (provenance)

def load_cards_diff(con, cards) -> IngestDiff:
    """INSERT OR REPLACE all cards (idempotent, as today) but first capture the
    set difference of names so callers learn what was newly printed. Reuses the
    exact load_cards body; only adds the pre-read of existing_card_names()."""
```

The diff is computed from the `cards` table itself (names present before vs after), so it is robust to
*how* the bulk changed — a new set, an oracle erratum that adds a face alias, or a Secret Lair drop all
surface as new names without us modelling set membership in the table.

**`updated_at` already gives us the freshness anchor.** `download_bulk_data(force=...)` already compares
the cached `metadata.json` `updated_at` against the remote bulk metadata and skips if unchanged. The
release scan's job is to decide *when to force=True* (a set in `recently_released` ⇒ force a re-pull
even within the normal skip window). We persist the last-ingest provenance (the `updated_at` we
ingested + `scanned_at`) into `metadata.json` so the diff and the "new this week" report are
reproducible across runs.

#### CLI shape (Part 1)

Wire the currently-stubbed `refresh` command (it is a `_not_implemented` today) and add a scan
sub-command under `seed`/`report`:

- `legacy refresh cards [--force] [--horizon-days N] [--lookback-days N]` — run the release scan,
  force a bulk re-pull iff a set is in the recent/upcoming window (or `--force`), ingest with
  `load_cards_diff`, print the diff (`N new cards: ...`) and which set(s) triggered it. This is the
  scheduler entry point (cron/launchd later; out of scope to *install* the schedule — we ship the
  idempotent command the schedule would call, per the "ship the command, not the cron" convention).
- `legacy report new-cards [--since DATE] [--limit N]` — show the cards added in the most recent
  ingest diff (read from persisted provenance), each with its release set — the "new cards to test
  this week" surface the item names as a future consumer.

`seed cards` is left intact (full rebuild) as the from-scratch path; `refresh cards` is the
incremental, diff-aware path. Both share `load_cards`/`load_cards_diff`.

---

### Part 2 — No-history speculation

#### The problem, precisely

A brand-new card has **zero rows** in `deck_cards`/`rounds`, so `card_value_marginal` returns the
`n=0`, `lift=0.0`, `tier="speculative"` sentinel forever — it sits at the floor and carries no signal.
The normal presence-correlational machinery is structurally blind to it (there is nothing to
correlate). We need a *deliberate, separate* forecasting path that is explicitly NOT the empirical
estimator and is labelled as such.

#### Method: intrinsic feature score + analogous-card borrowed prior, fused, speculative-labelled

The forecast for a new card is a blend of two independent estimates, both clearly pre-data:

**(A) Intrinsic feature score** — a heuristic, data-free "does this look playable in Legacy?" signal
derived entirely from `Card` fields + the existing tag layers. It leans on the sibling
`feature-oracle-text-interaction-tags` (`interaction_facts(card)`) for structured facts and on
`card_tags.py` (`is_free_spell`, `mana_base_tags`, `staple_role`) for roles. Concretely a small,
auditable additive rubric (each component logged with its contribution — no black-box number):

- **CMC band** — Legacy rewards low cost; cards at CMC ≤ 1 score highest, decaying upward (the format's
  empirical curve, from `legacy-foundations`/`legacy-metagame` briefs). For a "free" spell
  (`is_free_spell`) the effective cost is treated as 0.
- **Interaction profile** — from `interaction_facts`: `free_cast`, a static/`permanence` lock effect,
  one-sided (`affects in {opponent-only, targeted}`) disruption all add; symmetric self-harm subtracts.
  This is exactly the structured-fact grounding the item calls for — we do NOT re-reason oracle_text
  from scratch, we consume the sibling feature's typed verdicts.
- **Role match** — keyword/text cues for the high-value Legacy roles (cantrip, free interaction,
  discard, lock piece, fast mana, land denial) reuse `card_tags` role detection; matching a known
  high-value role adds.
- **Stat efficiency** — for creatures, `power_int()` relative to CMC (a cheap beater clause).

The rubric emits an `IntrinsicScore` in `[0,1]` with a per-component breakdown. It is openly heuristic
and carries `ConfidenceMetadata(level="speculative", source="heuristic")`.

**(B) Analogous-card borrowed prior** — the empirical anchor. Find the *k* nearest existing cards by a
structural similarity over typed features (NOT oracle-text embedding — we have no model and the brief
posture is data-driven, auditable similarity), then borrow their established empirical signal as the
prior. This is the **child-story Unit 4** matcher:

```python
def analogous_cards(target: Card, pool: Iterable[Card], *, k=5) -> list[Analogue]:
    """k nearest existing cards by a transparent feature distance:
       same card-type bucket (creature/instant/sorcery/enchantment/artifact/land/PW) — hard filter;
       color-set Jaccard; CMC proximity; shared card_tags roles + interaction_facts affects/permanence;
       shared keywords. Each component weighted, summed → similarity in [0,1]. Pure, no DB."""
```

For each analogue we pull its existing `CardValue` (via `card_value_marginal` on the live corpus) —
this is the *only* place real tournament data enters the forecast, and it enters as the *neighbours'*
signal, never the new card's. The borrowed prior is the similarity-weighted mean of the analogues'
`p_shrunk` lift, **gated to established/evolving analogues only** (a speculative analogue carries no
information, mirroring the gate-then-degrade convention). If no analogue clears the gate the borrowed
prior is absent and the forecast falls back to the intrinsic score alone (honest degrade — same shape
as `tuning`'s no-signal-skip).

**Fusion.** `SpeculativeForecast` = a transparent, reported blend:

```python
@dataclass(frozen=True)
class SpeculativeForecast:
    card: str
    intrinsic: IntrinsicScore           # the data-free rubric + breakdown
    analogues: tuple[Analogue, ...]      # the nearest cards + their similarity + borrowed lift + tier
    borrowed_prior: float | None         # similarity-weighted analogue lift, None if no gated analogue
    forecast: float                      # fused estimate (intrinsic if no prior; else weighted blend)
    confidence: ConfidenceMetadata       # ALWAYS level="speculative", source="heuristic"
    label: str                           # e.g. "PRE-DATA FORECAST — no tournament data yet"
```

The fusion weight leans on the prior when present (real neighbour data > pure heuristic) but the result
is **always** `speculative` — borrowing a neighbour's established tier does NOT upgrade the new card's
confidence, because the analogy itself is the unproven assumption. This is the central honesty
guarantee and is asserted directly in tests.

#### Why a separate path, not a patch to `card_value`

`card_value.py` is presence-correlational over observed rounds; conflating a forecast into it would
violate its module contract ("Callers must not present these as causal win-rate claims" — and here
there's no observation at all). The speculator lives in a new `analytics/speculation.py`, consumes
`card_value` read-only for the analogue prior, and is surfaced through its own labelled CLI verb. This
keeps the gated-additive seam: nothing in the existing analytics/advisory output changes.

#### CLI shape (Part 2)

- `legacy report speculate <card-name> [--k 5]` — forecast a single named new card; prints the
  intrinsic breakdown, the k analogues with similarities + their borrowed lift/tier, the fused
  forecast, and the loud `PRE-DATA FORECAST` banner.
- `legacy report speculate --new` (or `legacy refresh cards --speculate`) — forecast **every** card in
  the latest ingest diff (the Part-1 → Part-2 hand-off): the "here are the new cards and our pre-data
  read on each" surface. Sorted by forecast, every row banner-labelled speculative.

Output formatting reuses the audit-trail convention from `advisory/report.py` (every number with its
derivation + heuristic-vs-data label) so the speculative provenance is never lost.

---

### Units in build order (trickiest first)

| # | Unit | Where | Risk | Story? |
|---|------|-------|------|--------|
| 1 | **Analogous-card matcher** `analogous_cards()` + `Analogue` | `analytics/speculation.py` (new) | **highest** — the similarity function is the algorithmic core; wrong neighbours ⇒ wrong prior | **child story** `…-analogous-matcher` (drafting, held) |
| 2 | **Intrinsic feature score** `intrinsic_score()` + `IntrinsicScore` | `analytics/speculation.py` | medium — rubric tuning; consumes interaction_facts + card_tags | inline |
| 3 | **Forecast fusion** `speculate_card()` + `SpeculativeForecast` | `analytics/speculation.py` | low — composes 1+2, borrows `card_value_marginal`, always-speculative label | inline |
| 4 | **Release scan** `fetch_sets()` / `upcoming_and_recent()` + `SetRelease`/`ReleaseScan` | `ingestion/releases.py` (new) | low — thin GET /sets parse + pure date split | inline |
| 5 | **Diff-producing ingest** `existing_card_names()` / `load_cards_diff()` + `IngestDiff`; persist provenance | `ingestion/store.py`, `scryfall.py` | low — additive over `load_cards` | inline |
| 6 | **CLI wiring** `refresh cards`, `report new-cards`, `report speculate [--new]` | `cli.py` | low — nested-group plumbing, lazy imports, `_setup_logging` first | inline |

Build order rationale: the matcher (1) carries all the risk and is independently testable from
hand-built `Card`s with no DB, so it goes first as the child story. The intrinsic score (2) and fusion
(3) layer on it. Ingestion (4-5) is independent plumbing — it can be built in parallel but is sequenced
after so the speculator's input contract (`list[str]` of new names) is already fixed. CLI (6) last.

### Interfaces summary (new public surface)

- `ingestion/releases.py`: `SetRelease`, `ReleaseScan`, `fetch_sets(client)`, `upcoming_and_recent(...)`
- `ingestion/store.py`: `existing_card_names(con)`, `load_cards_diff(con, cards) -> IngestDiff`, `IngestDiff`
- `analytics/speculation.py`: `Analogue`, `analogous_cards(target, pool, k)`, `IntrinsicScore`,
  `intrinsic_score(card)`, `SpeculativeForecast`, `speculate_card(target, pool, card_winrates, k)`
- `cli.py`: `refresh cards`, `report new-cards`, `report speculate`

All new models subclass `LegacyEngineModel`; all new result records are frozen dataclasses living
beside their logic (per ARCHITECTURE "result records live in their module"). `config.py` gains
`SCRYFALL_SETS_URL` + `RELEASE_HORIZON_DAYS`/`RELEASE_LOOKBACK_DAYS` constants (constants-only-config
pattern, no side effects).

### Test plan (behaviour-derived, no DB where possible)

- **Matcher (Unit 1):** hand-built `Card`s — a new "Brainstorm-like" cantrip finds the cantrip
  staples as nearest; a new dual land's analogues are dual lands not creatures (card-type hard filter);
  empty-pool and no-analogue-above-gate cases return `[]`. Similarity is symmetric-ish and bounded
  `[0,1]`. Deterministic ordering on ties (stable sort by name).
- **Intrinsic score (Unit 2):** a free counterspell (Force-of-Will-shaped hand-built Card) scores high;
  a vanilla 5-mana 3/3 scores low; a symmetric self-harm card is penalised. Each component's
  contribution is present in the breakdown (auditable). Delegates to `interaction_facts`/`is_free_spell`
  — verified by a card whose only signal is `free_cast`.
- **Fusion (Unit 3):** with gated analogues present, `borrowed_prior` is the similarity-weighted lift
  and `forecast` leans toward it; with no gated analogue, `borrowed_prior is None` and `forecast ==
  intrinsic.score` (honest degrade). **The honesty assertion:** `confidence.level == "speculative"`
  *always*, even when every analogue is `established` — borrowing established data does NOT upgrade the
  forecast's tier. The `label` always contains the pre-data banner string.
- **Release scan (Unit 4):** a fixed `today` + a synthetic `/sets` payload splits into upcoming /
  recently_released by date windows; a set with `released_at=None` (unscheduled) is excluded from both;
  no per-set legality filtering is applied (a Secret Lair appears like any set).
- **Diff ingest (Unit 5):** seed a `:memory:` store with cards A,B; `load_cards_diff` with A,B,C ⇒
  `IngestDiff.new_names == ("C",)`, `total_after == 3`; re-running with the same set ⇒ `new_names == ()`
  (idempotent, no phantom diffs). Provenance (`scryfall_updated_at`) round-trips.
- **CLI:** `report speculate <card>` prints the banner and the analogue table;
  `refresh cards --force` against a mock Scryfall (monkeypatched client) prints the diff. CliRunner,
  mocked network (no live Scryfall in tests — mirrors existing ingestion tests).
- **Regression / gated-additive:** existing `seed cards`, `card_value`, and report tests are unmodified
  and stay green — the speculator is a new module consuming `card_value` read-only, and `load_cards`
  is untouched (the diff path is a new function). Asserts no existing-output drift.

### Pre-mortem / risks

- **Bad analogies produce confident-looking garbage.** A structural-feature match can pair cards that
  play nothing alike (same CMC + colors, opposite role). *Mitigation:* the forecast is ALWAYS
  `speculative`-labelled and shows its analogues + similarities openly, so the human sees *why*; the
  borrowed prior is gated to established/evolving analogues and degrades to intrinsic-only when none
  clear. We surface the analogy, we don't hide it behind a single number.
- **Speculative output mistaken for empirical.** The whole point of the item's honesty insight.
  *Mitigation:* separate module, separate CLI verb, mandatory `level="speculative"` +
  `PRE-DATA FORECAST` banner that cannot be upgraded by neighbour data; the test suite asserts the
  tier-never-upgrades invariant directly.
- **Scryfall set-release date ≠ bulk-availability date.** Previews, digital-only staggering, oracle
  errata. *Mitigation:* the release scan is advisory-only (informs *when* to force a pull); the
  authoritative "what's new" is the table-vs-table diff, which is correct regardless of set metadata.
- **Set-type legality ambiguity.** Scryfall `set_type` doesn't encode Legacy legality; supplemental
  products can introduce Legacy-legal cards. *Mitigation:* do NOT filter by set; let the existing
  per-card `BanListSnapshot` path decide legality downstream. Over-ingesting a few non-Legacy cards is
  harmless (they simply never appear in tournament data).
- **Scope creep into a card-evaluation ML model.** *Mitigation:* the intrinsic rubric is a small,
  additive, fully-logged heuristic reusing existing tag layers — explicitly NOT a learned model. Resist
  adding components until a concrete forecast needs one (mirrors the interaction-tags "keep the enum
  tiny" discipline).
- **Sibling-feature timing.** `feature-oracle-text-interaction-tags` is `stage:implementing`, not done.
  The intrinsic score (Unit 2) consumes `interaction_facts`. *Mitigation:* Unit 2 imports it behind a
  thin accessor; if it lands first the score is richer, if not the score degrades to `card_tags`-only
  signal (gated-additive — `interaction_facts` contribution defaults to neutral when unavailable). No
  hard build-order coupling, but note `depends_on` could be added at scope time if the reviewer prefers
  a hard sequence.

---

**Regularly scan for upcoming set/edition releases and ingest their cards on release** — then provide
a way to **speculate on a new card's usefulness when there is no historical tournament data yet.**

Two parts:

1. **Release-aware ingestion.** Track the MTG release calendar (sets, Secret Lairs, supplemental
   products with Legacy-legal cards) and, on/after each release, pull the new cards into the `cards`
   table (Scryfall is already the ingestion source). Goal: the engine never reasons about a stale
   card universe and can recognize/parse decklists the moment new cards see play. Probably a
   scheduled scan + a "new cards since last ingest" diff.

2. **No-history speculation method.** A brand-new card has zero match results, so the engine's
   normal presence-correlational / matchup math is blind to it (it would sit at the `speculative`
   confidence floor forever — see confidence-metadata). We need a deliberate forecasting path:
   - score by intrinsic features derived from oracle_text + stats (CMC, card type, keywords, role
     tags) — leans on [[idea-oracle-text-grounded-reasoning]] for structured interaction facts;
   - compare to the nearest *analogous existing cards* and borrow their empirical signal as a prior;
   - clearly label all such output as **speculative / pre-data forecast**, never as established —
     consistent with the honesty posture in [[idea-ban-regime-everywhere]].

Why it matters: a new set can reshape the meta overnight, and that's exactly when the player most
wants guidance and exactly when historical data is absent. Also relevant: a new set IS effectively a
soft ban-regime shift in impact, even without a B&R announcement. Natural future consumer of the
[[idea-deck-tuning-refresh-workflow]] (flag "new cards to test this week").

## Hold

Design complete; held for human review before implementation.
