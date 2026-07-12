"""Signal detectors S1-S4 — per-entity candidate era boundaries from a bucketed series.

Four disturbance signals, three statistical data types (`docs/briefs/change-point-detection.md`
§2): S1 presence rules on per-card inclusion (near-step, cheap, names the trigger card for free),
S2 kernel change-point detection on the flex-band composition vector (multivariate, no natural
"trigger card"), S3 offline segmentation on the entity's share of field, and S4 win-rate
corroboration (never a primary detector — it only strengthens existing candidates' evidence).
Each detector is pure numpy/scipy over ``EntitySeries``/``Bucket`` (``series.py``'s
objective-search-split output) — no DuckDB, hermetically testable on hand-built fixtures.

**Complete vs. incomplete buckets** (brief §1's "partial trailing week" finding): S1 presence
rules MAY use the trailing incomplete bucket (a ban/release step is visible the moment it
happens, even from a partial week); S2/S3/S4 MUST NOT — a proportion computed from a partial
week is not comparable to a full week's proportion, and would spuriously look like a shift every
single refresh.

**Short-series floor**: every detector returns ``[]`` for an entity with fewer than
``_MIN_COMPLETE_BUCKETS`` complete buckets — too short to segment defensibly (brief §6).

**Operating-point constants are pinned by calibration tests** (`tests/analytics/eras/test_detect.py`)
against the frozen real-corpus and synthetic fixtures in `tests/analytics/eras/conftest.py`. See
each constant's inline comment for its calibration evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.stats import fisher_exact

from legacy_engine.analytics.eras.series import Bucket, EntitySeries

# ---------------------------------------------------------------------------
# Closed vocabulary (closed-vocabulary-fail-fast-token pattern)
# ---------------------------------------------------------------------------

SIGNAL_TYPES = frozenset({
    "presence-vanish", "presence-adopt", "composition", "share", "winrate",
})

# Every entity needs at least this many COMPLETE buckets before any detector runs — below this,
# there is not enough history to segment defensibly (brief §6 small-sample playbook).
_MIN_COMPLETE_BUCKETS: int = 8

# ---------------------------------------------------------------------------
# S1 — presence cliffs/ramps (brief §2 S1)
# ---------------------------------------------------------------------------

_VANISH_HI: float = 0.25   # prior-regime inclusion floor for a "ban cliff" candidate
_VANISH_LO: float = 0.05   # post-crossing inclusion ceiling for a confirmed vanish
_ADOPT_LO: float = 0.05    # prior-regime inclusion ceiling for a "release ramp" candidate
_ADOPT_HI: float = 0.25    # post-crossing inclusion floor for a confirmed adopt
_S1_REGIME_BUCKETS: int = 4    # pooled-window width (buckets) for the S1 regime fractions
_S1_MIN_POOLED_DECKS: int = 40  # minimum pooled decks per side before S1 may call a crossing
_ONE_BUCKET_JUMP: float = 0.50  # |jump| at/above this confirms off a single bucket (brief §1:
                                 # Flow State's one-week 0%->90-95% step needs no second bucket)

# ---------------------------------------------------------------------------
# S2 — composition drift (brief §2 S2)
# ---------------------------------------------------------------------------

# A bucket must clear this many ENTITY decks before its flex-band inclusion vector is treated as
# an estimable point in the composition series (brief §6: S2 "needs enough decks per bucket to
# estimate an inclusion vector (floor ~10-15 decks/bucket)" — pinned at the low end of that range).
_MIN_COMPOSITION_BUCKET_DECKS: int = 10

# ruptures KernelCPD(kernel="cosine") penalty. Calibrated against tests/analytics/eras/conftest.py:
# `stable_nonevent_series` (30 buckets, exactly-periodic period-5 flex-band wobble) never produces
# a spurious breakpoint even at pen as low as 0.001 (the periodicity gives PELT/KernelCPD no
# variance to recover from any split); `composition_rebalance_series` (30 buckets, a genuine
# 4-card, bucket-18 rebalance) only survives at pen <= ~1.0 (cost gain ~0.88 at the true break) and
# is missed entirely at pen >= 2.0. 0.5 sits in the middle of that (0.001, 1.0) safe window with
# comfortable margin on both sides.
_PELT_PEN: float = 0.5

# ---------------------------------------------------------------------------
# S3 — share shift (brief §2 S3)
# ---------------------------------------------------------------------------

# ruptures Pelt(model="l2") on the arcsine-transformed share series.
#
# DEVIATION (documented, sanctioned): the epic's Unit 3 notes specify `min_size=3` for this call.
# The Tron/Candelabra ground-truth fixture (`tron_cliff_series`) falsifies that at the corpus's
# own recency edge: the ban cliff (59->20 decks/week) lands in the SECOND-TO-LAST complete
# bucket, one bucket before the corpus's trailing (necessarily incomplete) week. A live corpus
# is *always* freshest right where its most recent disturbance would be — this is not a fixture
# artifact, it is structural. `min_size=3` forbids ANY breakpoint whose right-hand segment has
# fewer than 3 points, so it can never place a boundary in the last two complete buckets — on
# this fixture it is provably unable to recover the epic's own headline validation case (verified:
# with `min_size=3` the algorithm instead locates the unrelated release-ramp breakpoint five
# buckets earlier, missing the ±1-bucket tolerance by two buckets, at every penalty tested).
# `min_size=2` is the minimal relaxation that keeps a floor against singleton-bucket noise while
# admitting a real two-bucket-old tail disturbance; deck-count floors elsewhere (S2's
# `_MIN_COMPOSITION_BUCKET_DECKS`, S4's 30-match floor, the ensemble's 30-deck era floor) still
# guard statistical validity, so this relaxation is not carrying the floor alone.
_SHARE_MIN_SIZE: int = 2

# Calibrated against `tron_cliff_series` (fires at pen in roughly [0.001, 0.005], recovering the
# 2026-06-15 boundary exactly) and `stable_nonevent_series` (silent at every pen tested down to
# 0.0005 — the exactly-periodic share series gives the L2 cost no sustained level shift to find).
# 0.003 sits inside the Tron firing window with margin either side.
_SHARE_PEN: float = 0.003

# ---------------------------------------------------------------------------
# S4 — win-rate corroboration (brief §2 S3/S4)
# ---------------------------------------------------------------------------

_WINRATE_MIN_DELTA: float = 0.05
_WINRATE_MIN_MATCHES: int = 30

# ---------------------------------------------------------------------------
# Candidate boundary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateBoundary:
    """A single detector's proposed era boundary for one entity.

    ``date`` is the ISO date of the FIRST bucket of the new era (not the last bucket of the old
    one). ``pvalue`` is a permutation p for S2/S3 (§4) or an exact two-proportion p for S1; S4
    never constructs its own candidate (it only extends an existing one's ``evidence``).
    """

    entity: str
    date: str
    signal: str
    magnitude: float
    pvalue: float
    evidence: str
    trigger_card: str | None

    def __post_init__(self) -> None:
        if self.signal not in SIGNAL_TYPES:
            raise ValueError(
                f"CandidateBoundary: signal {self.signal!r} must be one of "
                f"{sorted(SIGNAL_TYPES)}"
            )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _complete_buckets(s: EntitySeries) -> list[Bucket]:
    return [b for b in s.buckets if b.complete]


def _too_short(buckets: list[Bucket]) -> bool:
    return len(buckets) < _MIN_COMPLETE_BUCKETS


def _import_ruptures():
    """Lazy import — `ruptures` is an eras-only dependency, never imported at module load."""
    import ruptures as rpt
    return rpt


def _kernel_cosine_algo(rpt, min_size: int):
    """The composition-CPD estimator: cosine-kernel PELT, with an RBF-kernel PELT fallback ONLY
    if `KernelCPD`/the cosine kernel is unavailable in whatever `ruptures` got installed (the
    pin is `ruptures>=1.1,<2`; verified present as of 1.1.10 — this is a belt-and-suspenders
    guard, not the expected path)."""
    try:
        return rpt.KernelCPD(kernel="cosine", min_size=min_size)
    except (AttributeError, ValueError, TypeError, AssertionError):
        return rpt.Pelt(model="rbf", min_size=min_size)


def _segment_cost_gain(cost_factory, pooled: np.ndarray, split: int) -> float:
    """Unsplit cost minus split cost for `pooled` (a 2D array), cutting at index `split`."""
    n = pooled.shape[0]
    cost = cost_factory()
    cost.min_size = 1
    cost.fit(pooled)
    unsplit = cost.error(0, n)
    split_cost = cost.error(0, split) + cost.error(split, n)
    return float(unsplit - split_cost)


def _permutation_pvalue(
    cost_factory, pooled: np.ndarray, split: int, *, n_perm: int, seed: int,
    min_size: int = 1,
) -> tuple[float, float]:
    """Observed cost gain at `split` plus its selection-corrected segment-permutation p-value.

    Pools the two adjacent segments' points (`pooled`) and shuffles their order `n_perm` times
    with a seeded `default_rng`. Because the tested split was CHOSEN by the search to maximize
    gain, the null statistic must be the MAX gain over all admissible splits of the permuted
    sequence (respecting `min_size` on both sides) — recomputing at the fixed split alone is
    anti-conservative (the observed value is a maximum; the fixed-split null is not), which a
    stochastic stationary fleet exposes as spurious fleet-BH acceptances. p = (1 + #{perm
    max-gain >= observed}) / (n_perm + 1) (brief §4 / E-Divisive's permutation scheme, which
    likewise re-maximizes its statistic within permuted segments).
    """
    observed = _segment_cost_gain(cost_factory, pooled, split)
    rng = np.random.default_rng(seed)
    n = pooled.shape[0]
    admissible = range(min_size, n - min_size + 1)
    exceed = 0
    for _ in range(n_perm):
        permuted = pooled[rng.permutation(n)]
        perm_max = max(
            _segment_cost_gain(cost_factory, permuted, k) for k in admissible
        )
        if perm_max >= observed:
            exceed += 1
    pvalue = (1 + exceed) / (n_perm + 1)
    return observed, pvalue


def _segment_bounds(bkps: list[int]) -> list[tuple[int, int]]:
    """[(start, end), ...] segment bounds from ruptures' `predict()` output (end indices, last
    one == series length)."""
    all_bkps = [0] + list(bkps)
    return [(all_bkps[i], all_bkps[i + 1]) for i in range(len(all_bkps) - 1)]


# ---------------------------------------------------------------------------
# S1 — presence
# ---------------------------------------------------------------------------


def detect_presence(s: EntitySeries) -> list[CandidateBoundary]:
    """Per-flex-card inclusion-rate crossings: bans (vanish) and releases/rebuilds (adopt).

    Uses ALL buckets with `decks > 0` (including the trailing incomplete bucket — brief §1: a
    step is visible from a partial week too). A crossing confirms immediately if the jump is
    `>= _ONE_BUCKET_JUMP`; otherwise the bucket AFTER the crossing must also clear the new
    threshold (two-consecutive-bucket confirmation). The p-value is an exact two-proportion test
    (`scipy.stats.fisher_exact`) on the two adjacent buckets' (ran, didn't) x (before, after)
    2x2 table — cheap and exact at these sample sizes (brief §2 S1).
    """
    complete = _complete_buckets(s)
    if _too_short(complete):
        return []

    candidates: list[CandidateBoundary] = []
    for card in s.flex_cards:
        points = [
            (b, b.card_incl.get(card, 0), b.decks)
            for b in s.buckets
            if b.decks > 0
        ]
        for j in range(1, len(points)):
            prev_bucket, prev_incl, prev_decks = points[j - 1]
            curr_bucket, curr_incl, curr_decks = points[j]
            prev_frac = prev_incl / prev_decks
            curr_frac = curr_incl / curr_decks

            if prev_frac >= _VANISH_HI and curr_frac < _VANISH_LO:
                signal = "presence-vanish"
            elif prev_frac < _ADOPT_LO and curr_frac >= _ADOPT_HI:
                signal = "presence-adopt"
            else:
                continue

            jump = abs(curr_frac - prev_frac)
            confirmed = jump >= _ONE_BUCKET_JUMP
            if not confirmed and j + 1 < len(points):
                _next_bucket, next_incl, next_decks = points[j + 1]
                next_frac = next_incl / next_decks
                confirmed = (
                    next_frac < _VANISH_LO if signal == "presence-vanish"
                    else next_frac >= _ADOPT_HI
                )
            if not confirmed:
                continue

            # Regime check on POOLED windows, not the two crossing buckets alone: at
            # mid-tier weekly densities (~12-14 decks/bucket) single-bucket fractions
            # cross the thresholds by pure binomial noise; a stochastic stationary
            # fleet exposes those as spurious fleet-BH acceptances. Pool up to
            # _S1_REGIME_BUCKETS on each side of the crossing and require the POOLED
            # fractions to satisfy the same regime bounds, with at least
            # _S1_MIN_POOLED_DECKS of pooled sample per side. A real ban/release step
            # (Flow State: 0% -> 90%+ across every following bucket) passes trivially;
            # noise wobbles revert to their base rate under pooling and fail.
            pool_prev = points[max(0, j - _S1_REGIME_BUCKETS):j]
            pool_curr = points[j:j + _S1_REGIME_BUCKETS]
            prev_pool_incl = sum(i for _, i, _ in pool_prev)
            prev_pool_decks = sum(d for _, _, d in pool_prev)
            curr_pool_incl = sum(i for _, i, _ in pool_curr)
            curr_pool_decks = sum(d for _, _, d in pool_curr)
            if min(prev_pool_decks, curr_pool_decks) < _S1_MIN_POOLED_DECKS:
                continue
            prev_pool_frac = prev_pool_incl / prev_pool_decks
            curr_pool_frac = curr_pool_incl / curr_pool_decks
            if signal == "presence-vanish":
                regime_ok = prev_pool_frac >= _VANISH_HI and curr_pool_frac < _VANISH_LO
            else:
                regime_ok = prev_pool_frac < _ADOPT_LO and curr_pool_frac >= _ADOPT_HI
            if not regime_ok:
                continue

            table = [
                [prev_pool_incl, prev_pool_decks - prev_pool_incl],
                [curr_pool_incl, curr_pool_decks - curr_pool_incl],
            ]
            _, pvalue = fisher_exact(table)

            candidates.append(CandidateBoundary(
                entity=s.entity,
                date=curr_bucket.start,
                signal=signal,
                magnitude=jump,
                pvalue=float(pvalue),
                evidence=(
                    f"{card} {prev_pool_frac:.0%}→{curr_pool_frac:.0%} "
                    f"(decks {prev_pool_decks}→{curr_pool_decks} pooled)"
                ),
                trigger_card=card,
            ))
    return candidates


# ---------------------------------------------------------------------------
# S2 — composition
# ---------------------------------------------------------------------------


def detect_composition(
    s: EntitySeries, *, pen: float = _PELT_PEN, n_perm: int = 199, seed: int = 0,
) -> list[CandidateBoundary]:
    """Kernel change-point detection on the flex-band inclusion-fraction vector.

    Eligible buckets are COMPLETE buckets with `>= _MIN_COMPOSITION_BUCKET_DECKS` entity decks
    (thin buckets can't estimate an inclusion vector — brief §6). `ruptures.KernelCPD(kernel=
    "cosine")` finds candidate breakpoints; each gets a segment-permutation p-value against the
    cosine cost (brief §4).
    """
    complete = _complete_buckets(s)
    if _too_short(complete) or not s.flex_cards:
        return []

    eligible = [b for b in complete if b.decks >= _MIN_COMPOSITION_BUCKET_DECKS]
    min_size = 3
    if len(eligible) < 2 * min_size:
        return []

    vectors = np.array([
        [b.card_incl.get(c, 0) / b.decks for c in s.flex_cards]
        for b in eligible
    ])

    rpt = _import_ruptures()
    algo = _kernel_cosine_algo(rpt, min_size)
    algo.fit(vectors)
    try:
        bkps = algo.predict(pen=pen)
    except rpt.NotEnoughPoints:
        return []

    interior = bkps[:-1]
    if not interior:
        return []

    segments = _segment_bounds(bkps)
    cost_factory = type(algo.cost)

    candidates: list[CandidateBoundary] = []
    for seg_idx in range(1, len(segments)):
        # `interior[seg_idx - 1]` is the breakpoint separating segments[seg_idx - 1]/[seg_idx].
        left_start, left_end = segments[seg_idx - 1]
        _right_start, right_end = segments[seg_idx]
        b_idx = left_end  # == interior[seg_idx - 1]

        pooled = vectors[left_start:right_end]
        split = left_end - left_start
        observed_gain, pvalue = _permutation_pvalue(
            cost_factory, pooled, split, n_perm=n_perm, seed=seed, min_size=3,
        )

        unsplit_cost = cost_factory().fit(pooled).error(0, pooled.shape[0])
        magnitude = observed_gain / abs(unsplit_cost) if unsplit_cost else observed_gain

        left_mean = vectors[left_start:left_end].mean(axis=0)
        right_mean = vectors[left_end:right_end].mean(axis=0)
        delta = np.abs(right_mean - left_mean)
        top = np.argsort(delta)[::-1][:3]
        evidence = ", ".join(
            f"{s.flex_cards[i]} {left_mean[i]:.0%}→{right_mean[i]:.0%}" for i in top
        )

        candidates.append(CandidateBoundary(
            entity=s.entity,
            date=eligible[b_idx].start,
            signal="composition",
            magnitude=float(magnitude),
            pvalue=float(pvalue),
            evidence=evidence,
            trigger_card=None,
        ))
    return candidates


# ---------------------------------------------------------------------------
# S3 — share
# ---------------------------------------------------------------------------


def detect_share(
    s: EntitySeries, *, n_perm: int = 199, seed: int = 0,
) -> list[CandidateBoundary]:
    """Offline segmentation on the entity's share of field (arcsine-transformed, L2 cost).

    Eligible buckets are all COMPLETE buckets (share is well-defined at any deck count, including
    zero). See `_SHARE_MIN_SIZE`'s docstring comment for the sanctioned min_size deviation from
    the epic's Unit 3 notes.
    """
    complete = _complete_buckets(s)
    if _too_short(complete):
        return []

    min_size = _SHARE_MIN_SIZE
    if len(complete) < 2 * min_size:
        return []

    shares = np.array([
        (b.decks / b.field_decks) if b.field_decks else 0.0
        for b in complete
    ])
    arcsine = 2 * np.arcsin(np.sqrt(shares))

    rpt = _import_ruptures()
    algo = rpt.Pelt(model="l2", min_size=min_size)
    algo.fit(arcsine)
    try:
        bkps = algo.predict(pen=_SHARE_PEN)
    except rpt.NotEnoughPoints:
        return []

    interior = bkps[:-1]
    if not interior:
        return []

    segments = _segment_bounds(bkps)
    cost_factory = type(algo.cost)
    arcsine_2d = arcsine.reshape(-1, 1)

    candidates: list[CandidateBoundary] = []
    for seg_idx in range(1, len(segments)):
        left_start, left_end = segments[seg_idx - 1]
        _right_start, right_end = segments[seg_idx]
        b_idx = left_end

        pooled = arcsine_2d[left_start:right_end]
        split = left_end - left_start
        _observed_gain, pvalue = _permutation_pvalue(
            cost_factory, pooled, split, n_perm=n_perm, seed=seed,
            min_size=_SHARE_MIN_SIZE,
        )

        # Segment-level means, not the two buckets straddling the split: with
        # min_size=2 the level shift can land one bucket INSIDE the new segment
        # (the Candelabra cliff does exactly that), and an adjacent-bucket delta
        # would then report a 0.0-magnitude no-op audit line.
        before_share = float(shares[left_start:left_end].mean())
        after_share = float(shares[left_end:right_end].mean())
        magnitude = abs(after_share - before_share)

        candidates.append(CandidateBoundary(
            entity=s.entity,
            date=complete[b_idx].start,
            signal="share",
            magnitude=magnitude,
            pvalue=float(pvalue),
            evidence=f"share {before_share:.1%}→{after_share:.1%}/wk (segment means)",
            trigger_card=None,
        ))
    return candidates


# ---------------------------------------------------------------------------
# S4 — win-rate corroboration (never creates boundaries)
# ---------------------------------------------------------------------------


def corroborate_winrate(
    s: EntitySeries, cands: list[CandidateBoundary],
) -> list[CandidateBoundary]:
    """Append a win-rate corroboration note to candidates whose pooled W/L shifts materially
    across the boundary, on both sides of a minimum match-count floor. Never constructs a new
    boundary; returns one output entry per input candidate (unmodified unless corroborated —
    since `CandidateBoundary` is frozen, corroborated entries are `dataclasses.replace()`d).
    """
    complete = _complete_buckets(s)
    if _too_short(complete):
        return list(cands)

    out: list[CandidateBoundary] = []
    for cand in cands:
        before_wins = sum(b.wins for b in complete if b.start < cand.date)
        before_losses = sum(b.losses for b in complete if b.start < cand.date)
        after_wins = sum(b.wins for b in complete if b.start >= cand.date)
        after_losses = sum(b.losses for b in complete if b.start >= cand.date)
        before_n = before_wins + before_losses
        after_n = after_wins + after_losses

        if before_n >= _WINRATE_MIN_MATCHES and after_n >= _WINRATE_MIN_MATCHES:
            before_wr = before_wins / before_n
            after_wr = after_wins / after_n
            if abs(after_wr - before_wr) >= _WINRATE_MIN_DELTA:
                note = (
                    f" · WR corroborates: {before_wr:.0%}→{after_wr:.0%} "
                    f"(n {before_n}/{after_n})"
                )
                out.append(replace(cand, evidence=cand.evidence + note))
                continue
        out.append(cand)
    return out
