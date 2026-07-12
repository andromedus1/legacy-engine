"""Shared fixtures for `analytics.eras` detector/ensemble tests.

House style: factory fixtures returning `_make_X(**kwargs)` closures (pytest-factory-fixtures
pattern), `TestX` classes in the consuming modules, fully deterministic (no unseeded RNG, no real
clock). Frozen real-corpus ledger fixtures (measured 2026-07-11, corpus through 2026-07-01) are
literal data here — never touch the default DB, never re-derive from `build_entity_series`; the
whole point of `detect.py`/`ensemble.py` being pure numpy is that they're testable on hand-built
`EntitySeries` without DuckDB.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from legacy_engine.analytics.eras.detect import CandidateBoundary
from legacy_engine.analytics.eras.series import Bucket, EntitySeries


def _dates(start: date, n: int) -> list[str]:
    return [(start + timedelta(weeks=i)).isoformat() for i in range(n)]


# ---------------------------------------------------------------------------
# Generic factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_bucket():
    def _make(**kwargs):
        defaults = dict(
            start="2026-01-05", complete=True, decks=10, field_decks=100,
            wins=5, losses=5, card_incl={},
        )
        defaults.update(kwargs)
        return Bucket(**defaults)
    return _make


@pytest.fixture
def make_entity_series():
    def _make(**kwargs):
        defaults = dict(
            entity="Test", parent="Test", bucket_weeks=1, flex_cards=(), buckets=(),
        )
        defaults.update(kwargs)
        return EntitySeries(**defaults)
    return _make


# ---------------------------------------------------------------------------
# Fixture 1 — Flow State adoption (S1 ground truth #2, brief §1)
# ---------------------------------------------------------------------------


def _weekly_card_series(
    entity: str, weekly: list[tuple[int, int]], *, start: date, field_decks: int,
    flex_card: str = "Flow State",
) -> EntitySeries:
    """Build an EntitySeries from `(decks, with_card)` weekly tuples. The last bucket is always
    the trailing partial week (`complete=False`) — every real weekly fixture in this module ends
    mid-corpus, matching the brief §1 "the trailing week is partial" finding."""
    n = len(weekly)
    starts = _dates(start, n)
    buckets = tuple(
        Bucket(
            start=starts[i],
            complete=(i < n - 1),
            decks=decks,
            field_decks=field_decks,
            wins=0,
            losses=0,
            card_incl={flex_card: with_card} if with_card else {},
        )
        for i, (decks, with_card) in enumerate(weekly)
    )
    return EntitySeries(
        entity=entity, parent=entity, bucket_weeks=1, flex_cards=(flex_card,), buckets=buckets,
    )


@pytest.fixture
def flow_state_series() -> dict[str, EntitySeries]:
    """Frozen real-corpus fixture (measured 2026-07-11): Flow State's one-week adoption step
    across three archetypes, weekly (decks, with_flow_state), 2026-01-26 -> 2026-06-29 (23 weeks,
    last partial). `docs/briefs/change-point-detection.md` §1 ground truth #2 — the competitive
    population rebuilt three archetypes essentially overnight (week of 2026-04-20), no ban, no
    `valid_since` change; every S1 detector on this project must recover it."""
    start = date(2026, 1, 26)
    doomsday = [
        (3, 0), (23, 0), (7, 0), (16, 0), (6, 0), (22, 0), (8, 0), (10, 0), (15, 0), (15, 0),
        (20, 0), (15, 0), (19, 18), (22, 21), (21, 20), (15, 14), (17, 16), (29, 27), (13, 12),
        (22, 21), (20, 20), (27, 14), (6, 2),
    ]
    izzet = [
        (6, 0), (33, 0), (28, 0), (17, 0), (18, 0), (14, 0), (14, 0), (9, 0), (18, 0), (15, 0),
        (27, 0), (17, 5), (39, 35), (39, 38), (44, 44), (30, 29), (36, 35), (49, 46), (36, 35),
        (43, 43), (33, 33), (31, 31), (7, 7),
    ]
    dimir = [
        (15, 0), (64, 0), (47, 0), (41, 0), (31, 0), (60, 0), (46, 0), (28, 0), (58, 0), (39, 0),
        (45, 0), (35, 1), (52, 37), (25, 21), (33, 31), (23, 23), (19, 19), (22, 22), (17, 17),
        (22, 22), (18, 18), (24, 23), (3, 3),
    ]
    return {
        "Doomsday": _weekly_card_series("Doomsday", doomsday, start=start, field_decks=400),
        "Izzet Delver": _weekly_card_series("Izzet Delver", izzet, start=start, field_decks=400),
        "Dimir Tempo": _weekly_card_series("Dimir Tempo", dimir, start=start, field_decks=400),
    }


# ---------------------------------------------------------------------------
# Fixture 2 — Tron / Candelabra cliff (S1+S3 ground truth #1, brief §1)
# ---------------------------------------------------------------------------


@pytest.fixture
def tron_cliff_series() -> EntitySeries:
    """Frozen real-corpus fixture: the Candelabra ban cliff, weekly Tron deck counts,
    2026-03-02 -> 2026-06-29 (18 weeks, last partial). `docs/briefs/change-point-detection.md` §1
    ground truth #1 — left side is the release-driven growth ramp, right side the ban collapse.
    Every deck in this fixture runs Candelabra of Tawnos (`card_incl[...] == decks` every bucket)
    so its FRACTION is a constant 1.0 throughout: this is deliberately a pure share collapse
    (the decks vanish, not the card) — `detect_presence` must stay silent on it while
    `detect_share` fires."""
    start = date(2026, 3, 2)
    weekly_decks = [2, 5, 12, 34, 23, 42, 37, 41, 52, 20, 28, 36, 50, 58, 59, 59, 20, 1]
    n = len(weekly_decks)
    starts = _dates(start, n)
    buckets = tuple(
        Bucket(
            start=starts[i],
            complete=(i < n - 1),
            decks=decks,
            field_decks=420,
            wins=0,
            losses=0,
            card_incl={"Candelabra of Tawnos": decks},
        )
        for i, decks in enumerate(weekly_decks)
    )
    return EntitySeries(
        entity="Tron", parent="Tron", bucket_weeks=1,
        flex_cards=("Candelabra of Tawnos",), buckets=buckets,
    )


# ---------------------------------------------------------------------------
# Fixture 3 — stable non-event (false-alarm-rate half of calibration)
# ---------------------------------------------------------------------------

_STABLE_DECK_CYCLE = [13, 15, 11, 14, 12]
_STABLE_FRAC_CYCLE = [
    [0.30, 0.50, 0.70, 0.40, 0.60],
    [0.32, 0.48, 0.72, 0.38, 0.62],
    [0.28, 0.52, 0.68, 0.42, 0.58],
    [0.31, 0.49, 0.71, 0.39, 0.61],
    [0.29, 0.51, 0.69, 0.41, 0.59],
]
_STABLE_FLEX_CARDS = ("Card A", "Card B", "Card C", "Card D", "Card E")


def _stable_series(entity: str, *, start: date, n_buckets: int = 30, field_decks: int = 300) -> EntitySeries:
    """Deterministic period-5 deck/fraction wobble, exactly repeating — no true disturbance
    anywhere in the series (verified during calibration: an EXACTLY periodic series gives PELT/
    KernelCPD no sustained variance to recover from any split, at any penalty tested down to
    1/1000th of the pinned operating points)."""
    starts = _dates(start, n_buckets)
    buckets = []
    for i in range(n_buckets):
        decks = _STABLE_DECK_CYCLE[i % 5]
        fracs = _STABLE_FRAC_CYCLE[i % 5]
        card_incl = {card: round(frac * decks) for card, frac in zip(_STABLE_FLEX_CARDS, fracs)}
        buckets.append(Bucket(
            start=starts[i], complete=True, decks=decks, field_decks=field_decks,
            wins=6, losses=6, card_incl=card_incl,
        ))
    return EntitySeries(
        entity=entity, parent=entity, bucket_weeks=1,
        flex_cards=_STABLE_FLEX_CARDS, buckets=tuple(buckets),
    )


@pytest.fixture
def stable_nonevent_series() -> EntitySeries:
    """Synthetic stable non-event: 30 buckets, deterministic deck/fraction wobble, no disturbance.
    Every detector must return zero candidates at the pinned operating point."""
    return _stable_series("Lands", start=date(2026, 1, 5))


@pytest.fixture
def stationary_fleet_series():
    """100 synthetic stationary entities (same generator as `stable_nonevent_series`) for the
    ensemble's fleet-wide detector-integration null: run the REAL detectors over all 100 ->
    `derive_eras` must accept 0 boundaries fleet-wide."""
    def _make(n: int = 100) -> dict[str, EntitySeries]:
        return {
            f"Entity{i:03d}": _stable_series(f"Entity{i:03d}", start=date(2026, 1, 5))
            for i in range(n)
        }
    return _make


# ---------------------------------------------------------------------------
# Fixture 4 — composition rebalance (S2 synthetic ground truth)
# ---------------------------------------------------------------------------

_REBALANCE_FLEX_CARDS = tuple(f"Flex{i:02d}" for i in range(12))
# Buckets 0-17: vector A. Buckets 18-29: vector B. Cards 0-3 shift 0.40-0.55 (both directions);
# cards 4-11 hold constant. Every value stays inside [0.10, 0.90] so S1's 0.05/0.25 crossing
# thresholds can NEVER fire (S1 must stay silent; S2 must fire at bucket 18 +/- 1, p < 0.05).
_REBALANCE_A = [0.50, 0.50, 0.30, 0.70, 0.20, 0.35, 0.45, 0.55, 0.65, 0.75, 0.40, 0.60]
_REBALANCE_B = [0.90, 0.10, 0.85, 0.15, 0.20, 0.35, 0.45, 0.55, 0.65, 0.75, 0.40, 0.60]


@pytest.fixture
def composition_rebalance_series() -> EntitySeries:
    """Synthetic S2 ground truth: 30 buckets, 12 flex cards, a 4-card rebalance at bucket 18."""
    start = date(2026, 1, 5)
    n = 30
    starts = _dates(start, n)
    buckets = []
    for i in range(n):
        fracs = _REBALANCE_A if i < 18 else _REBALANCE_B
        decks = 20  # exact multiple-of-0.05 fractions -> zero rounding error at this deck count
        card_incl = {
            card: round(frac * decks) for card, frac in zip(_REBALANCE_FLEX_CARDS, fracs)
        }
        buckets.append(Bucket(
            start=starts[i], complete=True, decks=decks, field_decks=400,
            wins=10, losses=10, card_incl=card_incl,
        ))
    return EntitySeries(
        entity="Rebalance", parent="Rebalance", bucket_weeks=1,
        flex_cards=_REBALANCE_FLEX_CARDS, buckets=tuple(buckets),
    )


# ---------------------------------------------------------------------------
# Null-fleet candidate generator (ensemble BH-FDR test, bypassing real detectors)
# ---------------------------------------------------------------------------


@pytest.fixture
def make_null_candidates():
    """Seeded synthetic `CandidateBoundary` noise, 1-2 candidates per entity, p-values drawn from
    `[0.02, 1.0)` — representative of a 199-permutation scheme's smallest achievable p
    (`1/200 = 0.005`), so the floor is not artificially generous. Bypasses the real detectors
    entirely (see `stationary_fleet_series` for the detector-integration null) — this is the
    fast, purely-statistical BH-FDR null test.

    Dates are drawn from a 30-week window (`weeks 0-29` off `2026-01-05`) matching
    `stable_nonevent_series`/`stationary_fleet_series`'s own bucket grid, so callers can pair this
    generator's candidates with those series (bucket-distance lookups resolve exactly rather than
    falling back to a day-based estimate).
    """
    def _make(
        n_entities: int = 20, seed: int = 0, entity_names: list[str] | None = None,
    ) -> list[CandidateBoundary]:
        names = entity_names if entity_names is not None else [
            f"Null{i:03d}" for i in range(n_entities)
        ]
        rng = np.random.default_rng(seed)
        out: list[CandidateBoundary] = []
        for name in names:
            n_cands = int(rng.integers(1, 3))  # 1 or 2 candidates
            for _ in range(n_cands):
                p = float(rng.uniform(0.02, 1.0))
                wk = int(rng.integers(0, 30))
                out.append(CandidateBoundary(
                    entity=name,
                    date=(date(2026, 1, 5) + timedelta(weeks=wk)).isoformat(),
                    signal="share",
                    magnitude=float(rng.uniform(0.01, 0.1)),
                    pvalue=p,
                    evidence="synthetic null noise",
                    trigger_card=None,
                ))
        return out
    return _make
