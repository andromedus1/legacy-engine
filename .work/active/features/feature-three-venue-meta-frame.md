---
id: feature-three-venue-meta-frame
kind: feature
stage: done
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

Standardize meta analysis as a default **three-lens read** rather than one global field:

1. **Online meta** — MTGO/online-derived field (today: `--provenance online`).
2. **Local meta** — a specific locality the user actually plays (e.g. the maintainer's local paper meta).
3. **Regional / travel-tournament meta** — large events people travel to (Eternal Weekend,
   Champs, regional opens).

"We should always approach meta this way." The point is that these three fields diverge sharply
and tuning should be done against the venue you're actually attending. Concrete evidence from the
2026-06-13 session (current Undercity Informer regime): online is **Tron-dominated (12.9%,
established tier)**, while paper has **Tron at 2.2%** and a long fair-deck tail (Izzet Delver,
Show and Tell, Painter, Dimir Delver, Aluren, Beanstalk, Stoneblade, Cradle Control). The
online/paper split alone already changes the deck-tuning answer.

**Gap:** the engine does online-vs-paper via `--provenance`, but it **cannot isolate a specific
locality (the local meta)** or an **event-tier (regional / large traveled-to events)** from global paper.
Delivering this frame motivates:
- `epic-local-meta-support` phase-2 geo/location dimension (filter by region natively), AND
- a **new event-tier / event-size dimension** (distinguish a 200-person regional from a weekly local).

Make "online / local / regional" a first-class, repeatable analysis frame across reports + advise.
Links to [[epic-local-meta-support]].

## Design

### Scope decision (what ships now vs deferred)

The three-lens vision names three venues: **online**, **local** (a specific locality, e.g.
the local meta), and **regional** (large traveled-to events). Of these, only the **online / paper**
split is computable on the data we have today — `tournaments.provenance` is the one venue
dimension that exists. The **local** and **regional** lenses require dimensions that are NOT
built:

- **local** needs a geographic/location field on tournaments → `epic-local-meta-support` Phase 2
  (`engine-geo-dimension`). Not built.
- **regional** needs an event-tier / event-size dimension (distinguish a 200-person regional
  open from a weekly local) → a NEW dimension that does not yet exist in any epic. Not built.

**Decision: ship the buildable part now as a first-class, repeatable two-lens (online vs paper)
comparison frame, architected so adding local/regional later is additive.** We do NOT block this
feature on either dimension. The design fixes a `Venue` abstraction whose member set is
data-derived: today it resolves to `{online, paper}`; when the geo/event-tier dimensions land,
the same surface gains `{local:<region>, regional}` members with zero call-site churn at the
comparison layer.

Rationale (logged per autopilot instruction): the feature's *distinctive* value over what already
exists is the **side-by-side comparison surface** — running the same read across venues at once
and surfacing the divergence (the 2026-06-13 evidence: online Tron 12.9% vs paper Tron 2.2%). The
underlying per-venue plumbing (`compute_metashare(provenance=…)`, `build_global_field(provenance=…)`,
`build_advisory_inputs(provenance=…)`) already exists and already accepts `provenance`. So this
feature is mostly a **composition + presentation** layer, not new analytics.

### Relationship to epic-local-meta-support (no blocking dependency)

`epic-local-meta-support` Phase 1 has a member `advise-provenance-flag` (thread bare `--provenance`
through the advise leaves). This feature deliberately does **not** depend on it and does **not**
duplicate it:

- That member adds a single-basis `--provenance online|paper` selector to each advise leaf (pick ONE
  venue). This feature adds a multi-basis `--venues` comparison (run SEVERAL venues side by side).
  They are complementary surfaces over the same already-provenance-aware functions.
- This feature calls the provenance-accepting functions directly with an internal per-venue loop, so
  it needs no change to the advise leaves' own signatures. If `advise-provenance-flag` ships first,
  nothing here changes; if this ships first, that member is unaffected.
- `depends_on: []` stays. The local/regional venue members are a **forward seam**, recorded here and
  in the epic, not a build dependency.

### The Venue abstraction (new, small)

New module `src/legacy_engine/analytics/venue.py` (analytics, no advisory import — mirrors the
`affectedness.py` placement rule so both `analytics` and `advisory` can consume it without a cycle).

```python
# analytics/venue.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Venue:
    """One lens in the meta frame. `provenance` is the DuckDB filter today; `key`/`label`
    are stable identifiers for display and dict keys. Future local/regional venues set
    `provenance=None` and carry their own filter predicate (added in the geo/event-tier phase)."""
    key: str            # "online" | "paper"  (later: "local:local", "regional")
    label: str          # "Online (MTGO)" | "Paper"
    provenance: str | None   # "online" | "paper"  (the only filter axis available today)

# The data-derived member set. Today: hardcoded to the two provenance values that exist.
# resolve_venues() probes the corpus so an empty side (e.g. no paper data) is reported, not crashed.
ONLINE = Venue(key="online", label="Online (MTGO)", provenance="online")
PAPER  = Venue(key="paper",  label="Paper",         provenance="paper")
DEFAULT_VENUES = (ONLINE, PAPER)

def resolve_venues(con, requested: list[str] | None = None) -> list[Venue]:
    """Map requested venue keys → Venue objects, defaulting to DEFAULT_VENUES.
    Unknown keys raise ValueError listing the available keys (fail-loud per the CLI pattern).
    A requested venue with zero decks in the corpus is KEPT (its panel renders an explicit
    'no data for this venue' note) — absence is information in a divergence frame."""
```

Why a `Venue` object rather than passing raw `provenance` strings around: it is the **seam** that
makes local/regional additive. The comparison surface iterates `list[Venue]` and never branches on
"is this online or paper"; when a `local` venue arrives it carries a different filter but the same
shape, so the comparison code is untouched (Evolve Additively / Match-API-to-Consumer moves).

### Unit 1 — `compute_venue_metashare` (analytics/venue.py)

Pure composition over the existing `compute_metashare`.

```python
@dataclass
class VenueMetaShare:
    venue: Venue
    report: MetaShareReport | None   # None when the venue has zero decks (panel shows 'no data')

def compute_venue_metashare(
    con, venues: list[Venue], *,
    definition: str = "raw", min_share: float = 0.02,
    since: str | None = None, until: str | None = None,
) -> list[VenueMetaShare]:
    """One MetaShareReport per venue, computed via compute_metashare(provenance=venue.provenance).
    Empty-corpus venues return report=None rather than an empty report so the renderer can
    distinguish 'no data' from 'data, but everything below floor'."""
```

No new SQL — `compute_metashare` already takes `provenance`/`since`/`until`. This is the analytics
half of the frame: the share table per venue.

### Unit 2 — `venue_divergence` (analytics/venue.py)

The headline value-add: quantify how far the venues diverge so the user sees *why* venue choice
matters, not just two tables.

```python
@dataclass
class ArchetypeDivergence:
    archetype: str
    shares: dict[str, float]      # venue.key -> share (0.0 if absent in that venue)
    tiers: dict[str, str]         # venue.key -> confidence tier (worst-case backs the gap)
    spread: float                 # max(share) - min(share) across venues
    max_venue: str                # venue.key with the highest share
    min_venue: str

@dataclass
class VenueDivergence:
    venues: list[Venue]
    rows: list[ArchetypeDivergence]   # sorted desc by spread
    definition: str
    notes: list[str]                  # e.g. "paper has 0 decks; divergence vs online not meaningful"

def venue_divergence(
    venue_shares: list[VenueMetaShare], *, min_spread: float = 0.0,
) -> VenueDivergence:
    """Union the archetypes across venue reports; per archetype, collect each venue's share
    (use group_other=False shares so 'Other' rolling doesn't mask a real per-venue gap),
    compute spread, sort desc. Confidence tiers carried through: a high spread backed by a
    speculative-tier sample on one side is flagged in `notes`, not hidden."""
```

Honesty rule (PRINCIPLES + confidence-metadata pattern): a divergence row whose larger share rests
on a `speculative`/`evolving` tier is annotated, never silently presented as established fact. This
is the same discipline the rest of advisory follows.

### Unit 3 — CLI: `report meta --venues` (cli.py)

Augment the EXISTING `report meta` command (it already loops provenance bases when `--provenance all`).
Add a `--venues` flag that switches it from the current "print each basis sequentially" mode into a
**comparison** mode with a divergence summary.

```
report meta [--venues online,paper] [--definition raw|topcut|wrw|all]
            [--min-spread 0.0] [--db ...] <window opts> <verbose>
```

- `--venues` accepts a comma-separated list of venue keys; default unset = current behavior
  (backward compatible — existing tests untouched, gated-additive-augmentation pattern).
- When `--venues` is set: resolve venues → `compute_venue_metashare` → render each venue's table
  (reusing `_print_metashare_report`) → then render a **Divergence** block from `venue_divergence`
  (top-N by spread, the "online Tron 12.9% / paper 2.2%" surface).
- `--provenance` and `--venues` are mutually exclusive (raise `click.ClickException` if both given) —
  `--provenance` picks one basis, `--venues` compares many; mixing is ambiguous.
- `wrw` under `--venues`: same existing guard — skip wrw with the existing note (win-rate weights are
  full-corpus only); raw/topcut compare fine.

New renderer `_print_venue_divergence(div: VenueDivergence)` next to `_print_metashare_report`.

### Unit 4 — CLI: `advise report --venues` (cli.py)

The advisory half of the frame — "tune against the venue you're actually attending." Augment the
EXISTING `advise report` leaf (the full Field Read). Add `--venues`:

```
advise report --deck FILE [--venues online,paper] [--archetype ...] [--reserved N]
              [--seed N] [--db ...] <window opts> <verbose>
```

- Default unset = current single-field behavior (backward compatible).
- When `--venues` is set: for each venue, build advisory inputs with that venue's provenance
  (`build_advisory_inputs(con, win, provenance=venue.provenance)` — already supported) and the
  matching field (`_load_field(..., provenance=venue.provenance, ...)`), then
  `build_field_read_report(...)` per venue. Render each venue's Field Read under a clear
  `── Venue: Online (MTGO) ──` banner, then a compact **cross-venue positioning delta** footer:
  the deck's positioning S and best-deck-call per venue side by side (the decision-relevant
  divergence — "your deck is well-positioned online but poorly in paper").
- `--field` (custom field file) + `--venues` is mutually exclusive (a custom field has no venue
  axis) → `click.ClickException`.
- Reuses `build_field_read_report` unchanged; this is pure orchestration in the CLI command.

A small shared helper `_render_cross_venue_positioning(reports: dict[str, FieldReadReport])` lives in
`advisory/report.py` (text renderer, no recompute — mirrors the existing `_render_*` renderers).

### Unit order (trickiest first)

1. **Unit 2 `venue_divergence`** — the trickiest: union/spread/tier-carry logic with the honesty
   annotations and empty-venue handling. Hand-built `VenueMetaShare` inputs make it unit-testable
   with no DB (objective-search-split spirit: pure function over plain inputs).
2. **Unit 1 `compute_venue_metashare`** + the `Venue` abstraction — thin once Unit 2's shape is fixed.
3. **Unit 3 `report meta --venues`** — wire analytics + the new divergence renderer.
4. **Unit 4 `advise report --venues`** — wire advisory per-venue + the cross-venue positioning footer.

### Test plan

New `tests/analytics/test_venue.py`:
- `compute_venue_metashare`: two synthetic provenance-split corpora → one report per venue; an
  empty paper side → `report=None`. Reuses the conftest factory fixtures (pytest-factory-fixtures).
- `venue_divergence`: hand-built `VenueMetaShare` list →
  - spread computed and sorted desc;
  - archetype present in one venue only → share 0.0 on the other, spread = its share;
  - a high-spread row backed by a speculative tier → annotated in `notes`;
  - empty-venue (`report=None`) → note emitted, not a crash;
  - the 2026-06-13 regression fixture: online Tron 0.129 / paper Tron 0.022 → spread ≈ 0.107,
    `max_venue=online`.
- `resolve_venues`: default → `(online, paper)`; unknown key → `ValueError` listing valid keys;
  empty-corpus venue kept.

New `tests/test_cli_venues.py` (or extend existing CLI tests):
- `report meta --venues online,paper` over a seeded test DB → both tables + a Divergence block;
  asserts the divergence ordering.
- `--provenance` + `--venues` together → non-zero exit / `ClickException`.
- `advise report --venues online,paper --deck <fixture>` → per-venue Field Read banners + the
  cross-venue positioning footer.
- `--field` + `--venues` together → `ClickException`.
- Backward-compat: `report meta` and `advise report` WITHOUT `--venues` produce byte-identical
  output to before (gated-additive-augmentation; assert against existing snapshots/expectations).

### Risks

- **Empty paper corpus today.** If the local DB has little/no paper data, the divergence frame is
  thin. Mitigation: `report=None` + explicit per-venue 'no data' note; tier annotations keep it
  honest. This is a *data* limitation, not a design flaw — surfaced, not hidden.
- **`wrw` + window/venue incoherence.** Already-existing guard; reused, not re-litigated.
- **Scope creep toward local/regional.** Hard boundary: no geo/event-tier code here. The `Venue`
  seam is the only forward-looking surface, and it is inert (two hardcoded provenance venues) until
  those dimensions land.
- **Mutual-exclusion ergonomics.** `--provenance`/`--field` vs `--venues` clashes are caught at the
  CLI layer with a clear message rather than producing a confusing blended result.

### Decomposition

No child stories. Four tightly-coupled units in two files (`analytics/venue.py`, `cli.py`) plus two
small renderers in `advisory/report.py` — well under the spawn threshold, single-stride implementable.

### Forward seam to record in epic-local-meta-support

When `engine-geo-dimension` (Phase 2) lands, extend `analytics/venue.py`'s member set with
`local:<region>` and `regional` venues (the latter gated on the new event-tier dimension) and
`resolve_venues` to accept those keys. The comparison/divergence/CLI layers consume `list[Venue]`
and need no change. (Recorded as a forward note on the epic, not a dependency edge.)

## Implementation notes

**Files created:**
- `src/legacy_engine/analytics/venue.py` — `Venue` abstraction, `ONLINE`/`PAPER` singletons,
  `resolve_venues`, `VenueMetaShare`, `compute_venue_metashare`, `ArchetypeDivergence`,
  `VenueDivergence`, `venue_divergence`. Pure analytics layer, no advisory import.
- `tests/analytics/__init__.py` — package marker for new analytics test subdirectory.
- `tests/analytics/test_venue.py` — 19 tests (pure venue_divergence hand-built inputs incl.
  2026-06-13 regression fixture; compute_venue_metashare with in-memory split corpus;
  resolve_venues edge cases).
- `tests/test_cli_venues.py` — 18 tests (report meta --venues comparison mode;
  advise report --venues per-venue Field Read + cross-venue footer; mutual exclusion guards;
  backward-compat assertions confirming no-`--venues` paths are unaffected).

**Files modified:**
- `src/legacy_engine/advisory/report.py` — added `render_cross_venue_positioning` renderer
  (pure text, no recompute; placed before `render_field_read`; does not disturb
  `_interaction_annotation` or any existing renderer).
- `src/legacy_engine/cli.py` — augmented `report meta` with `--venues`, `--min-spread`;
  augmented `advise report` with `--venues`; added `_print_venue_divergence` renderer.
  All edits additive and localized — legacy code paths byte-identical when `--venues` unset.
- `.work/active/features/feature-three-venue-meta-frame.md` — `stage: implementing → review`.

**Test counts:** 1390 total (1353 baseline + 37 new); all pass.

**Deviations from design:**
- `resolve_venues` accepts `con=None` for the pure lookup path (con not yet used; kept in
  signature for forward compatibility per the design's "probe corpus" note).
- `_print_venue_divergence` renders tier markers inline (? speculative, ~ evolving) rather
  than a separate column — simpler and readable given the table width constraint.
- `render_cross_venue_positioning` uses right-aligned column format with a fixed col_w=14;
  label truncation at col_w characters keeps wide labels from breaking alignment.
