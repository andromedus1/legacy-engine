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

import numpy as np

from legacy_engine.analytics.subgroup import CardDiff, diff_compositions
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

__all__ = [
    "DeckVector",
    "FeatureMatrix",
    "build_feature_matrix",
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
    """

    key: tuple[str, int]
    counts: dict[str, int]


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


_DOUBLE_DIPPING_GUARD_NOTE = (
    "validation guard: statistical validity is bootstrap co-membership stability only — "
    "no significance test (t-test/chi-square) is ever run on the clustered data "
    "(double-dipping would inflate Type I error; brief §5)"
)


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
        boot_sample_labels = HDBSCAN(min_cluster_size=min_cluster_size).fit_predict(Xb)

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
) -> DiscoveredSplit:
    """Cluster a parent archetype's flex-band matrix into validated, named camps.

    Pipeline: reduce (injected ``reducer``) -> HDBSCAN (self-determines k; noise = -1) -> Gate A
    (bootstrap stability) -> Gate B (both-camp evolving tier + signature divergence) -> naming.
    ``passed`` is Gate A AND Gate B. ``reasons`` records every gate outcome verbatim — nothing
    thin is hidden (honest-degrade-marker).

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
        )

    from sklearn.cluster import HDBSCAN
    from sklearn.metrics import silhouette_score

    sorted_decks = sorted(decks, key=lambda d: d.key)
    decks_by_key = {d.key: d for d in sorted_decks}
    n = fm.X.shape[0]

    Xred = np.asarray(reducer(fm.X, seed=seed))
    min_cluster_size = max(30, round(0.10 * n))
    base_labels = np.asarray(HDBSCAN(min_cluster_size=min_cluster_size).fit_predict(Xred))
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
        for idx, c in enumerate(unique_camps):
            other_keys = [k for cc, ks in camp_keys.items() if cc != c for k in ks]
            avg_c = _avg_copies(decks_by_key, camp_keys[c], fm.cards)
            avg_rest = _avg_copies(decks_by_key, other_keys, fm.cards)
            diffs_c = diff_compositions(avg_c, avg_rest)
            positive = next((d for d in diffs_c if d.delta > 0), None)
            name_c = positive.name if positive is not None else f"camp-{idx}"
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

    stability = _bootstrap_stability(
        Xred, base_labels, min_cluster_size=min_cluster_size, seed=seed, n_boot=n_boot,
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

    if len(unique_camps) == 0:
        reasons.append("no clusters found: all decks labeled noise")
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

    return DiscoveredSplit(
        parent="",
        camps=camps,
        n_noise=n_noise,
        stability=stability,
        silhouette=silhouette,
        passed=passed,
        reasons=reasons,
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
    ``min_sig_cards``) by keyword name.
    """
    rows = con.execute(
        """
        SELECT d.tournament_id, d.deck_idx, dc.name, dc.count
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
    for tournament_id, deck_idx, name, count in rows:
        decks_map.setdefault((tournament_id, deck_idx), {})[name] = count
    deck_vectors = [DeckVector(key=key, counts=counts) for key, counts in decks_map.items()]

    matrix_kwargs = {k: v for k, v in params.items() if k in _MATRIX_PARAM_NAMES}
    cluster_kwargs = {k: v for k, v in params.items() if k not in _MATRIX_PARAM_NAMES}

    fm = build_feature_matrix(deck_vectors, **matrix_kwargs)
    split = cluster_and_validate(fm, deck_vectors, **cluster_kwargs)
    return dataclasses.replace(split, parent=archetype)
