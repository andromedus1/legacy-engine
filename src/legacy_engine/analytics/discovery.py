"""Subarchetype discovery engine — data-driven flex-band clustering within a parent archetype.

Generalizes ``analytics/subgroup.py`` (human names one signature card) into "algorithm proposes
the axis, statistics confirm it." Follows the **objective-search-split** pattern: a DB-free pure
core (matrix build -> reduce -> cluster -> validate -> name) fed by a thin DB-reading wrapper.

Method is pinned by the attested brief ``docs/briefs/subarchetype-discovery.md``:

- **Representation** (Unit 1): per-parent flex-band feature matrix (drop the ubiquitous core and
  the rare tail by inclusion thresholds), TF-IDF over counts, L2-normalized.
- **Reduction** (Unit 2): TruncatedSVD by default (deterministic, seeded), UMAP opt-in.
- **Clustering + validation + naming** (Unit 3): HDBSCAN on the reduced embedding; a two-gate
  validation (Gate A statistical: bootstrap co-membership stability; Gate B domain: both-camp
  evolving-tier + signature-card divergence reusing ``subgroup.diff_compositions``); auto-naming
  from the top divergent signature card.
- **DB wrapper** (Unit 4): read-only query of a parent's in-window mainboard deck-card rows into
  plain ``DeckVector`` rows, then delegate to the pure pipeline.

Double-dipping guard (load-bearing, per brief §5): validation never runs a plain significance test
(t-test/chi-square) on the clustered data — only bootstrap-resampling stability, which is robust to
the double-dipping trap that inflates Type I error when a classical test is applied to
clustering-derived groups.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date as _date

import numpy as np

from legacy_engine.analytics.subgroup import CardDiff, diff_compositions
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

__all__ = [
    "DeckVector",
    "FeatureMatrix",
    "build_feature_matrix",
    "project_flex_vector",
    "camp_centroid",
    "NearestCampResult",
    "nearest_camp",
    "DEFAULT_MIN_SIMILARITY",
    "reduce_dims",
    "Camp",
    "DiscoveredSplit",
    "cluster_and_validate",
    "discover_subarchetypes",
]


# ---------------------------------------------------------------------------
# Unit 1 — flex-band feature matrix (pure, DB-free)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeckVector:
    """One deck's mainboard composition, keyed for stable ordering.

    ``key`` is ``(tournament_id, deck_idx)`` — the same identity used by the ``decks`` table.
    ``counts`` maps mainboard card name -> copies (0 or absent both mean "not in this deck").
    ``date`` is the deck's tournament date (``t.date``, ISO ``YYYY-MM-DD``), additive for Gate C
    temporal-mixing detection — ``None`` when unknown (older/hand-built fixtures never set it,
    and clustering/naming never reads it; only Gate C's per-camp stats do).
    """

    key: tuple[str, int]
    counts: dict[str, int]
    date: str | None = None


@dataclass(frozen=True)
class FeatureMatrix:
    """A parent archetype's flex-band deck-card matrix, TF-IDF-weighted and L2-normalized."""

    keys: list[tuple[str, int]]   # row order (sorted by key)
    cards: list[str]              # flex-band column order (sorted by name)
    X: "np.ndarray"               # shape (n_decks, n_flex)


def build_feature_matrix(
    decks: list[DeckVector],
    *,
    flex_lo: float = 0.10,
    flex_hi: float = 0.95,
) -> FeatureMatrix:
    """Build the per-parent flex-band feature matrix.

    Drops cards outside ``[flex_lo, flex_hi]`` inclusion rate (the ubiquitous chassis and the
    rare tail carry no split signal — see brief §1). Rows are sorted by ``key`` for determinism.
    Cell values are TF-IDF over raw copy counts, L2-normalized per row.

    Degrades to an empty ``FeatureMatrix`` when fewer than 2 flex cards survive the band filter —
    the caller is responsible for emitting the honest "no separable structure" message.
    """
    if not decks:
        return FeatureMatrix(keys=[], cards=[], X=np.zeros((0, 0)))

    sorted_decks = sorted(decks, key=lambda d: d.key)
    n = len(sorted_decks)

    inclusion_counts: dict[str, int] = {}
    for deck in sorted_decks:
        for card, copies in deck.counts.items():
            if copies > 0:
                inclusion_counts[card] = inclusion_counts.get(card, 0) + 1

    flex_cards = sorted(
        card
        for card, cnt in inclusion_counts.items()
        if flex_lo <= (cnt / n) <= flex_hi
    )

    if len(flex_cards) < 2:
        return FeatureMatrix(keys=[], cards=[], X=np.zeros((0, 0)))

    count_matrix = np.array(
        [[deck.counts.get(card, 0) for card in flex_cards] for deck in sorted_decks],
        dtype=float,
    )

    from sklearn.feature_extraction.text import TfidfTransformer

    tfidf = TfidfTransformer(norm="l2")
    X = tfidf.fit_transform(count_matrix).toarray()

    return FeatureMatrix(keys=[d.key for d in sorted_decks], cards=flex_cards, X=X)


# ---------------------------------------------------------------------------
# Frozen flex-band projection + nearest-camp assignment (pure, DB-free)
#
# The representation a *post-staging* deck is compared against. Deliberately simpler than the
# clustering embedding above: raw L2-normalized counts over the split's frozen flex vocabulary,
# no TF-IDF reweighting and no SVD reduction — neither the fitted `idf_` vector nor the SVD
# `components_` matrix is persisted, so neither is reproducible at assignment time. Validated by
# the reconstruction-accuracy floor in tests/analytics/test_discovery.py (nearest-centroid must
# recover a split's own members' camp labels); if real-corpus dogfooding shows misassignment,
# `idf_` can be persisted additively alongside `flex_cards` without a breaking schema change.
# ---------------------------------------------------------------------------

DEFAULT_MIN_SIMILARITY = 0.35
# Uncalibrated initial default — cosine-similarity floor on raw L2-normalized flex-band vectors.
# Unlike _TEMPORAL_GAP_DAYS this has no calibration fixture: no real staged split carried a
# centroid before this path existed. CLI-tunable (`discover apply --min-similarity`) until a
# real-corpus pass calibrates it; err conservative (false-unlabeled beats false-camp).


def project_flex_vector(counts: dict[str, int], flex_cards: list[str]) -> "np.ndarray":
    """Project raw mainboard ``counts`` onto the frozen ``flex_cards`` vocabulary, L2-normalized.

    Missing cards count as 0. Returns an all-zero vector (never raises, never NaN) when the deck
    shares no card with ``flex_cards`` — ``nearest_camp`` reads an all-zero vector as "no
    similarity to anything", never a fabricated match.
    """
    vec = np.array([float(counts.get(card, 0)) for card in flex_cards], dtype=float)
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        return vec
    return vec / norm


def camp_centroid(member_counts: list[dict[str, int]], flex_cards: list[str]) -> list[float]:
    """Mean of a camp's members' L2-normalized flex vectors, renormalized.

    Goes through the SAME ``project_flex_vector`` a candidate deck is projected through — the
    invariant nearest-camp assignment rests on: centroid and candidate always live in the
    identical representation by construction, never two independently-derived spaces.
    Empty ``member_counts`` -> a zero vector (degenerate camp; ``nearest_camp`` can never assign
    to it, since cosine similarity against a zero vector is 0.0).
    """
    if not flex_cards:
        return []
    if not member_counts:
        return [0.0] * len(flex_cards)
    stacked = np.array(
        [project_flex_vector(counts, flex_cards) for counts in member_counts], dtype=float
    )
    mean = stacked.mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm == 0.0:
        return [0.0] * len(flex_cards)
    return (mean / norm).tolist()


@dataclass(frozen=True)
class NearestCampResult:
    """Outcome of one candidate deck's nearest-camp lookup.

    ``camp`` is ``None`` when the honest-degrade floor isn't cleared — ``reason`` names why,
    always. ``runner_up`` is the second-nearest camp, a diagnostic only: it never gates.
    """

    camp: str | None
    best_similarity: float
    runner_up: str | None
    reason: str


def nearest_camp(
    counts: dict[str, int],
    flex_cards: list[str],
    centroids: dict[str, list[float]],
    *,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> NearestCampResult:
    """Assign ``counts`` to the nearest camp centroid in the frozen flex-band space, or decline.

    Both sides are pre-L2-normalized (``project_flex_vector`` / ``camp_centroid``), so a plain
    dot product IS the cosine similarity — no renormalization here.

    Empty ``flex_cards``/``centroids`` (a staged record written before this path existed) ->
    honest decline with a named reason, nothing fabricated. A centroid whose length disagrees
    with ``flex_cards`` is corrupt persisted state, not thin data: fail fast.
    """
    if not flex_cards:
        return NearestCampResult(
            camp=None, best_similarity=0.0, runner_up=None,
            reason="staged split carries no frozen flex vocabulary",
        )
    if not centroids:
        return NearestCampResult(
            camp=None, best_similarity=0.0, runner_up=None,
            reason="staged split carries no camp centroid",
        )

    vec = project_flex_vector(counts, flex_cards)
    if not vec.any():
        return NearestCampResult(
            camp=None, best_similarity=0.0, runner_up=None,
            reason="deck shares no card with the staged split's frozen flex vocabulary",
        )

    scored: list[tuple[float, str]] = []
    for name, centroid in centroids.items():
        if len(centroid) != len(flex_cards):
            raise ValueError(
                f"nearest_camp: camp {name!r} centroid has {len(centroid)} dimension(s) but the "
                f"frozen flex vocabulary has {len(flex_cards)} — re-run `discover run` for this "
                "parent to restage a consistent split"
            )
        scored.append((float(np.dot(vec, np.asarray(centroid, dtype=float))), name))

    # Name as the secondary key so ties resolve deterministically rather than by dict order.
    scored.sort(key=lambda s: (-s[0], s[1]))
    best_similarity, best_name = scored[0]
    runner_up = scored[1][1] if len(scored) > 1 else None

    if best_similarity < min_similarity:
        return NearestCampResult(
            camp=None, best_similarity=best_similarity, runner_up=runner_up,
            reason=(
                f"best similarity {best_similarity:.3f} < min_similarity {min_similarity} "
                f"(nearest was {best_name!r})"
            ),
        )
    return NearestCampResult(
        camp=best_name, best_similarity=best_similarity, runner_up=runner_up,
        reason=f"cosine similarity {best_similarity:.3f} >= min_similarity {min_similarity}",
    )


# ---------------------------------------------------------------------------
# Unit 2 — reducer (pure, injectable)
# ---------------------------------------------------------------------------

def reduce_dims(
    X: "np.ndarray",
    *,
    method: str = "svd",
    n_components: int = 10,
    seed: int = 0,
) -> "np.ndarray":
    """Reduce ``X`` to at most ``n_components`` dimensions before clustering.

    ``method="svd"`` (default): ``TruncatedSVD`` — deterministic given ``random_state=seed``, no
    numba dependency, safe for CI. ``method="umap"``: lazy-imported (only reached when explicitly
    requested) so the core discovery path never requires ``umap-learn`` to be installed.

    When the feature space is already at or below ``n_components``, passes ``X`` through
    unreduced — reduction adds no value and would just be an identity-ish transform.
    """
    X = np.asarray(X)
    n_features = X.shape[1] if X.ndim == 2 else 0

    if n_features <= n_components:
        return X

    if method == "svd":
        from sklearn.decomposition import TruncatedSVD

        svd = TruncatedSVD(n_components=min(n_components, n_features - 1), random_state=seed)
        return svd.fit_transform(X)

    if method == "umap":
        import umap  # lazy import — optional dependency (pyproject `discovery` extra)

        reducer = umap.UMAP(n_components=n_components, random_state=seed)
        return reducer.fit_transform(X)

    raise ValueError(f"reduce_dims: unknown method {method!r} (expected 'svd' or 'umap')")


# ---------------------------------------------------------------------------
# Unit 3 — cluster + validate + name (pure — the trickiest unit)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Camp:
    """One discovered camp (cluster) within a parent archetype."""

    name: str
    member_keys: list[tuple[str, int]]
    signature_cards: list[tuple[str, float]]   # (card, delta) vs the rest, sorted |delta| desc
    n: int
    tier: ConfidenceLevel
    # Gate C temporal fields (additive, default-safe — existing hand-built Camp() calls in
    # tests/callers stay green). median_date is the camp's member decks' median tournament date
    # (None when no member deck carries a date). pct_current is the fraction of the camp's
    # decks dated >= a caller-supplied `current_since` (None-safe: None when current_since
    # wasn't given — an honest "we don't know" rather than a fabricated 0%/100%).
    median_date: str | None = None
    pct_current: float | None = None
    # Mean L2-normalized flex vector over this camp's member decks (see camp_centroid), in the
    # exact space nearest_camp projects candidate decks into. None on hand-built Camp()s and on
    # any camp formed before this field existed — incremental assignment declines rather than
    # comparing against a fabricated position.
    centroid: list[float] | None = None


@dataclass(frozen=True)
class DiscoveredSplit:
    """Result of clustering + validating a parent archetype's flex-band decks."""

    parent: str
    camps: list[Camp]
    n_noise: int
    stability: float           # mean bootstrap co-membership agreement (Gate A)
    silhouette: float | None   # secondary diagnostic only — never gates (HDBSCAN is non-convex)
    passed: bool               # Gate A AND Gate B
    reasons: list[str]         # honest-degrade: why passed / failed, verbatim
    # Gate C temporal-mixing flag (additive, default-safe). Unlike Gate A/B this NEVER fails the
    # split — a statistically-valid split whose camps separate strongly by date is still
    # `passed` (if A+B pass); it's flagged so downstream (`discover apply`/`promote`) can warn or
    # refuse, per the epic's honesty convention (surface, don't silently hide or auto-fail).
    temporal_mixing: bool = False
    temporal_note: str | None = None
    # The frozen flex-band vocabulary this split clustered on (FeatureMatrix.cards) — the fixed
    # column space Camp.centroid lives in and nearest-camp assignment projects new decks into.
    # Empty on the degenerate paths (no separable structure) and on hand-built splits.
    flex_cards: list[str] = dataclasses.field(default_factory=list)


_DOUBLE_DIPPING_GUARD_NOTE = (
    "validation guard: statistical validity is bootstrap co-membership stability only — "
    "no significance test (t-test/chi-square) is ever run on the clustered data "
    "(double-dipping would inflate Type I error; brief §5)"
)

# Gate C — temporal-mixing threshold (brief absorbed idea-discovery-temporal-gate; epic
# epic-stable-era-windows-discovery-gate Unit 1). Pinned by the two synthetic calibration
# fixtures in tests/analytics/test_discovery.py::TestClusterAndValidateGateC:
#   - old-camp median 2025-06-01 vs new-camp median 2026-05-01 (~334 days apart) -> FLAGS.
#   - both camps drawn from the same ~30-day window -> does NOT flag.
# 120 days sits comfortably below the flagging fixture's gap and above the non-flagging one; a
# real two-sample distributional test can replace this heuristic later without an API change
# (DiscoveredSplit.temporal_mixing/temporal_note are the stable contract, not this constant).
_TEMPORAL_GAP_DAYS = 120
_TEMPORAL_MIXING_NOTE = "camps may be list generations"


def _median_date(dates: list[str]) -> str | None:
    """Median ISO date over ``dates`` (empty -> None).

    Works in ordinal-day space so an even count averages to the nearest real calendar day
    (rather than picking an arbitrary one of the two middle dates).
    """
    if not dates:
        return None
    # Real-corpus dates mix plain ISO dates with full timestamps (MTGO events carry
    # "2024-11-09T10:00:00"); date.fromisoformat rejects the time component, so take the
    # date portion only — the same date-portion normalization corpus_freshness uses.
    ordinals = sorted(_date.fromisoformat(d[:10]).toordinal() for d in dates)
    n = len(ordinals)
    mid = n // 2
    if n % 2 == 1:
        med_ordinal = ordinals[mid]
    else:
        med_ordinal = round((ordinals[mid - 1] + ordinals[mid]) / 2)
    return _date.fromordinal(med_ordinal).isoformat()


def _camp_temporal_stats(
    decks_by_key: dict[tuple[str, int], "DeckVector"],
    keys: list[tuple[str, int]],
    current_since: str | None,
) -> tuple[str | None, float | None]:
    """Per-camp median deck date + %-current, both None-safe (honest-degrade-marker).

    ``pct_current`` is the fraction of the camp's decks (the full membership, not just the
    dated ones) whose date is present and >= ``current_since`` — a deck with no date never
    counts as current. ``None`` when ``current_since`` wasn't supplied (caller doesn't know a
    reference date, so no fabricated fraction is reported).
    """
    if not keys:
        return None, None
    dates = [decks_by_key[k].date for k in keys if decks_by_key[k].date is not None]
    median_date = _median_date(dates)
    if current_since is None:
        return median_date, None
    n_current = sum(1 for k in keys if (decks_by_key[k].date or "") >= current_since)
    return median_date, n_current / len(keys)


def _avg_copies(decks_by_key: dict[tuple[str, int], DeckVector], keys: list[tuple[str, int]],
                 cards: list[str]) -> dict[str, float]:
    """Average per-card copies (restricted to ``cards``) over the decks named by ``keys``."""
    if not keys:
        return {}
    totals = dict.fromkeys(cards, 0.0)
    for key in keys:
        counts = decks_by_key[key].counts
        for card in cards:
            totals[card] += counts.get(card, 0)
    m = len(keys)
    return {card: total / m for card, total in totals.items()}


def _gate_b_domain(
    camps: list[Camp],
    *,
    min_delta: float = 0.75,
    min_sig_cards: int = 2,
) -> tuple[bool, list[str]]:
    """Domain gate — the honesty gates the engine already trusts (brief §5 Gate B).

    Every camp must clear the evolving-tier floor (n>=30) AND show at least
    ``min_sig_cards`` flex-band cards with ``|delta| >= min_delta`` vs the rest of the pool
    (signature divergence, computed by the reused ``subgroup.diff_compositions``).

    Pure and directly unit-testable with hand-built ``Camp`` objects (no clustering needed) —
    this is deliberate: HDBSCAN's own ``min_cluster_size`` floor (Unit 3's
    ``max(30, round(0.10*n))``) already prevents a below-floor camp from ever being *formed*, so
    the "camp below evolving floor" failure mode can only be exercised directly against this gate.
    """
    if len(camps) < 2:
        return False, ["gate B: fewer than 2 camps — no split to validate"]

    reasons: list[str] = []
    overall_ok = True
    for camp in camps:
        tier_ok = camp.tier != "speculative"
        sig_count = sum(1 for _, delta in camp.signature_cards if abs(delta) >= min_delta)
        sig_ok = sig_count >= min_sig_cards
        camp_ok = tier_ok and sig_ok

        if not tier_ok:
            reasons.append(
                f"gate B[{camp.name}]: n={camp.n} below evolving floor "
                f"(tier={camp.tier}) — FAIL"
            )
        if not sig_ok:
            reasons.append(
                f"gate B[{camp.name}]: only {sig_count} flex card(s) with |Δ|>={min_delta} "
                f"(need >={min_sig_cards}) — FAIL"
            )
        if camp_ok:
            reasons.append(
                f"gate B[{camp.name}]: n={camp.n} (tier={camp.tier}), "
                f"{sig_count} signature card(s) |Δ|>={min_delta} — PASS"
            )
        overall_ok = overall_ok and camp_ok

    return overall_ok, reasons


def _bootstrap_stability(
    Xred: "np.ndarray",
    base_labels: "np.ndarray",
    *,
    min_cluster_size: int,
    min_samples: int,
    seed: int,
    n_boot: int,
) -> float:
    """Gate A — bootstrap co-membership stability (brief §5).

    Resample rows with replacement ``n_boot`` times, re-cluster each resample, and average the
    pairwise co-membership agreement against the base labeling — restricted to pairs that are
    non-noise in both the base and the resampled labeling. A split that dissolves under
    resampling is noise, not a real subarchetype.
    """
    from sklearn.cluster import HDBSCAN

    n = len(base_labels)
    base_labels = np.asarray(base_labels)
    non_noise = base_labels != -1

    if n_boot <= 0 or non_noise.sum() < 2:
        # Degenerate input (≤1 non-noise point): nothing to destabilize.
        return 1.0

    same_base = base_labels[:, None] == base_labels[None, :]
    scores: list[float] = []

    for b in range(n_boot):
        rng = np.random.default_rng(seed + b + 1)
        idx = rng.integers(0, n, size=n)
        Xb = Xred[idx]
        # Mirror the base run's parameters exactly — Gate A must stress the same clusterer,
        # or stability measures a different algorithm than the one that proposed the split.
        boot_sample_labels = HDBSCAN(
            min_cluster_size=min_cluster_size, min_samples=min_samples, copy=True,
        ).fit_predict(Xb)

        # Map bootstrap labels back onto original indices (first occurrence wins for repeats —
        # a resampled duplicate row gets an (essentially) identical cluster assignment anyway).
        labels_full = np.full(n, -1, dtype=int)
        present = np.zeros(n, dtype=bool)
        for pos in range(n):
            orig = idx[pos]
            if not present[orig]:
                labels_full[orig] = boot_sample_labels[pos]
                present[orig] = True

        mask = present & non_noise & (labels_full != -1)
        pair_mask = mask[:, None] & mask[None, :]
        np.fill_diagonal(pair_mask, False)  # self-pairs always agree — exclude, or stability biases upward
        if not pair_mask.any():
            continue

        same_boot = labels_full[:, None] == labels_full[None, :]
        agreement = (same_boot == same_base)[pair_mask]
        scores.append(float(agreement.mean()))

    return float(np.mean(scores)) if scores else 0.0


def cluster_and_validate(
    fm: FeatureMatrix,
    decks: list[DeckVector],
    *,
    reducer=reduce_dims,
    seed: int = 0,
    n_boot: int = 50,
    stability_min: float = 0.90,
    min_delta: float = 0.75,
    min_sig_cards: int = 2,
    min_samples: int = 10,
    current_since: str | None = None,
) -> DiscoveredSplit:
    """Cluster a parent archetype's flex-band matrix into validated, named camps.

    Pipeline: reduce (injected ``reducer``) -> HDBSCAN (self-determines k; noise = -1) -> Gate A
    (bootstrap stability) -> Gate B (both-camp evolving tier + signature divergence) -> Gate C
    (temporal mixing) -> naming. ``passed`` is Gate A AND Gate B — Gate C never gates ``passed``,
    it only sets ``temporal_mixing``/``temporal_note`` (honest-degrade-marker: flag, don't hide
    or silently fail). ``reasons`` records every gate outcome verbatim — nothing thin is hidden.

    ``current_since`` (optional) is the reference date Gate C's per-camp ``pct_current`` is
    computed against (typically the caller's era-window ``since``); ``None`` leaves
    ``pct_current`` honestly ``None`` on every camp rather than fabricating a fraction against
    an unknown reference.

    ``parent`` is left as ``""`` here — the pure core has no notion of the archetype label; the
    DB wrapper (``discover_subarchetypes``) stamps it via ``dataclasses.replace`` once it knows
    which archetype it queried.
    """
    reasons: list[str] = [_DOUBLE_DIPPING_GUARD_NOTE]

    if len(fm.cards) < 2 or fm.X.shape[0] == 0:
        return DiscoveredSplit(
            parent="",
            camps=[],
            n_noise=0,
            stability=0.0,
            silhouette=None,
            passed=False,
            reasons=reasons + ["no separable structure: fewer than 2 flex-band cards"],
            flex_cards=list(fm.cards),
        )

    from sklearn.cluster import HDBSCAN
    from sklearn.metrics import silhouette_score

    sorted_decks = sorted(decks, key=lambda d: d.key)
    decks_by_key = {d.key: d for d in sorted_decks}
    n = fm.X.shape[0]

    Xred = np.asarray(reducer(fm.X, seed=seed))
    min_cluster_size = max(30, round(0.10 * n))
    # min_samples is decoupled from min_cluster_size (sklearn defaults it to min_cluster_size,
    # which at corpus scale — e.g. 117 for a 1170-deck parent — makes the density requirement so
    # conservative that real camps dissolve into noise; hdbscan docs: larger min_samples => "more
    # points will be declared as noise"). A small explicit default keeps camp *size* gated by
    # min_cluster_size while letting density form. allow_single_cluster stays False (sklearn's
    # default): the root-cluster bias it introduces swallowed a validated real-world split; a
    # homogeneous parent honestly reports "no separable structure" via the k<2 branches below
    # (all-noise or one dense cluster — both FAIL with a named reason).
    base_labels = np.asarray(
        HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min(min_samples, min_cluster_size),
            copy=True,
        ).fit_predict(Xred)
    )
    n_noise = int(np.sum(base_labels == -1))
    unique_camps = sorted(int(c) for c in set(base_labels.tolist()) if c != -1)

    camp_keys: dict[int, list[tuple[str, int]]] = {c: [] for c in unique_camps}
    for i, lbl in enumerate(base_labels):
        if lbl != -1:
            camp_keys[int(lbl)].append(fm.keys[i])
    for c in camp_keys:
        camp_keys[c].sort()

    camps: list[Camp] = []
    if len(unique_camps) == 2:
        a, b = unique_camps
        avg_a = _avg_copies(decks_by_key, camp_keys[a], fm.cards)
        avg_b = _avg_copies(decks_by_key, camp_keys[b], fm.cards)
        diffs_a = diff_compositions(avg_a, avg_b)   # delta = a - b
        top: CardDiff = diffs_a[0]
        if top.delta > 0:
            name_a, name_b = top.name, f"non-{top.name}"
        else:
            name_a, name_b = f"non-{top.name}", top.name
        diffs_b = diff_compositions(avg_b, avg_a)
        camps.append(Camp(
            name=name_a, member_keys=camp_keys[a],
            signature_cards=[(d.name, d.delta) for d in diffs_a],
            n=len(camp_keys[a]), tier=tier_for_sample(len(camp_keys[a])),
        ))
        camps.append(Camp(
            name=name_b, member_keys=camp_keys[b],
            signature_cards=[(d.name, d.delta) for d in diffs_b],
            n=len(camp_keys[b]), tier=tier_for_sample(len(camp_keys[b])),
        ))
    elif len(unique_camps) >= 3:
        taken: set[str] = set()
        for idx, c in enumerate(unique_camps):
            other_keys = [k for cc, ks in camp_keys.items() if cc != c for k in ks]
            avg_c = _avg_copies(decks_by_key, camp_keys[c], fm.cards)
            avg_rest = _avg_copies(decks_by_key, other_keys, fm.cards)
            diffs_c = diff_compositions(avg_c, avg_rest)
            positives = [d for d in diffs_c if d.delta > 0]
            name_c = positives[0].name if positives else f"camp-{idx}"
            # Distinct camps can share a top signature card (two prison Lands builds both led
            # by Sphere of Resistance): a name collision would merge their decks.variant labels
            # on apply, silently undoing the split the validator just certified. Disambiguate
            # with the next positive signature card; deterministic numeric suffix as last resort.
            if name_c in taken:
                for d in positives[1:]:
                    cand = f"{name_c} / {d.name}"
                    if cand not in taken:
                        name_c = cand
                        break
                else:
                    name_c = f"{name_c} ({idx})"
            taken.add(name_c)
            camps.append(Camp(
                name=name_c, member_keys=camp_keys[c],
                signature_cards=[(d.name, d.delta) for d in diffs_c],
                n=len(camp_keys[c]), tier=tier_for_sample(len(camp_keys[c])),
            ))
    elif len(unique_camps) == 1:
        c = unique_camps[0]
        camps.append(Camp(
            name="single-cluster", member_keys=camp_keys[c], signature_cards=[],
            n=len(camp_keys[c]), tier=tier_for_sample(len(camp_keys[c])),
        ))
    # len(unique_camps) == 0 -> camps stays [] (all noise).

    # Gate C prerequisite: stamp each camp's median date / %-current now that member_keys are
    # final. Noise decks are excluded by construction — camp_keys only ever holds non-noise
    # cluster members (label != -1), so noise never enters a Gate C comparison.
    #
    # The camp centroid — the frozen-space position incremental assignment compares fresh decks
    # against — is stamped in the same pass, over the same final membership.
    enriched_camps: list[Camp] = []
    for camp in camps:
        median_date, pct_current = _camp_temporal_stats(
            decks_by_key, camp.member_keys, current_since,
        )
        centroid = camp_centroid(
            [decks_by_key[k].counts for k in camp.member_keys], fm.cards,
        )
        enriched_camps.append(
            dataclasses.replace(
                camp, median_date=median_date, pct_current=pct_current, centroid=centroid,
            )
        )
    camps = enriched_camps

    stability = _bootstrap_stability(
        Xred, base_labels, min_cluster_size=min_cluster_size,
        min_samples=min(min_samples, min_cluster_size), seed=seed, n_boot=n_boot,
    )

    silhouette: float | None = None
    if len(unique_camps) >= 2:
        non_noise_mask = base_labels != -1
        try:
            silhouette = float(silhouette_score(Xred[non_noise_mask], base_labels[non_noise_mask]))
        except ValueError:
            silhouette = None

    gate_a_pass = stability >= stability_min
    reasons.append(
        f"gate A stability: {stability:.3f} {'>=' if gate_a_pass else '<'} {stability_min} "
        f"({'PASS' if gate_a_pass else 'FAIL'}) over {n_boot} bootstrap resamples "
        "(silhouette is a secondary diagnostic only — not a gate)"
    )

    temporal_mixing = False
    temporal_note: str | None = None

    if len(unique_camps) == 0:
        reasons.append("no separable structure: no dense clusters found (all decks labeled noise)")
        passed = False
    elif len(unique_camps) == 1:
        reasons.append("single cluster: no separable structure (need >=2 camps)")
        passed = False
    else:
        gate_b_pass, gate_b_reasons = _gate_b_domain(
            camps, min_delta=min_delta, min_sig_cards=min_sig_cards,
        )
        reasons.extend(gate_b_reasons)
        passed = gate_a_pass and gate_b_pass

        # Gate C — temporal mixing (flags, never fails; noise already excluded from `camps`).
        dated_camps = [c for c in camps if c.median_date is not None]
        if len(dated_camps) >= 2:
            gap_days = max(
                abs(
                    (_date.fromisoformat(a.median_date) - _date.fromisoformat(b.median_date)).days
                )
                for i, a in enumerate(dated_camps)
                for b in dated_camps[i + 1:]
            )
            temporal_mixing = gap_days >= _TEMPORAL_GAP_DAYS
            if temporal_mixing:
                temporal_note = _TEMPORAL_MIXING_NOTE
                reasons.append(
                    f"gate C temporal: max camp median-date gap {gap_days}d "
                    f">= {_TEMPORAL_GAP_DAYS}d (FLAG — {_TEMPORAL_MIXING_NOTE})"
                )
            else:
                reasons.append(
                    f"gate C temporal: max camp median-date gap {gap_days}d "
                    f"< {_TEMPORAL_GAP_DAYS}d — no temporal mixing detected"
                )
        else:
            reasons.append(
                "gate C temporal: insufficient dated decks to compare camp date distributions"
            )

    return DiscoveredSplit(
        parent="",
        camps=camps,
        n_noise=n_noise,
        stability=stability,
        silhouette=silhouette,
        passed=passed,
        reasons=reasons,
        temporal_mixing=temporal_mixing,
        temporal_note=temporal_note,
        flex_cards=list(fm.cards),
    )


# ---------------------------------------------------------------------------
# Unit 4 — DB wrapper (thin, read-only)
# ---------------------------------------------------------------------------

_MATRIX_PARAM_NAMES = frozenset({"flex_lo", "flex_hi"})


def discover_subarchetypes(
    con,
    archetype: str,
    *,
    since: str | None = None,
    **params,
) -> DiscoveredSplit:
    """Discover candidate subarchetype camps within ``archetype``'s in-window mainboard pool.

    One DB pass (objective-search-split): pull every mainboard ``deck_cards`` row for the
    archetype's decks (optionally windowed by ``since``) into plain ``DeckVector`` rows, then
    hand off to the pure ``build_feature_matrix`` -> ``cluster_and_validate`` pipeline. Read-only.

    ``**params`` are split between ``build_feature_matrix`` (``flex_lo``/``flex_hi``) and
    ``cluster_and_validate`` (``reducer``/``seed``/``n_boot``/``stability_min``/``min_delta``/
    ``min_sig_cards``/``current_since``) by keyword name. ``t.date`` rides along on every row so
    each ``DeckVector`` carries its tournament date for Gate C's temporal-mixing check.
    """
    rows = con.execute(
        """
        SELECT d.tournament_id, d.deck_idx, t.date, dc.name, dc.count
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        JOIN deck_cards dc
          ON dc.tournament_id = d.tournament_id
         AND dc.deck_idx      = d.deck_idx
        WHERE d.archetype = ?
          AND dc.board = 'main'
          AND (? IS NULL OR t.date >= ?)
        """,
        [archetype, since, since],
    ).fetchall()

    decks_map: dict[tuple[str, int], dict[str, int]] = {}
    dates_map: dict[tuple[str, int], str | None] = {}
    for tournament_id, deck_idx, deck_date, name, count in rows:
        key = (tournament_id, deck_idx)
        decks_map.setdefault(key, {})[name] = count
        dates_map[key] = deck_date
    deck_vectors = [
        DeckVector(key=key, counts=counts, date=dates_map.get(key))
        for key, counts in decks_map.items()
    ]

    matrix_kwargs = {k: v for k, v in params.items() if k in _MATRIX_PARAM_NAMES}
    cluster_kwargs = {k: v for k, v in params.items() if k not in _MATRIX_PARAM_NAMES}

    fm = build_feature_matrix(deck_vectors, **matrix_kwargs)
    split = cluster_and_validate(fm, deck_vectors, **cluster_kwargs)
    return dataclasses.replace(split, parent=archetype)
