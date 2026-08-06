"""Superarchetype clustering — the pure, DB-free core (objective-search-split).

Method pinned by ``docs/briefs/superarchetype-aggregation.md`` §3:

- **Representation** (Unit 2): per-archetype maindeck **core set** (cards at >=50% inclusion in that
  archetype's in-window decks) **minus format staples** (cards core to >=30% of the cluster-defining
  archetypes). Hard removal, not TF-IDF down-weighting: soft weighting leaves 14 of 30 definers fused
  into one "plays blue" cluster (brief §2).
- **Distance** (Unit 2): Jaccard dissimilarity ``1 - |A n B| / |A u B|`` over the stripped cores.
- **Algorithm** (Unit 1/3): average-linkage agglomerative on the precomputed dissimilarity. Every
  archetype is placed — there is no noise class, which is the decisive reason HDBSCAN is rejected
  here: an archetype called noise gets no superarchetype at all, and it would be a thin unusual
  archetype, i.e. exactly the row the layer exists to cover.
- **Cut** (Unit 1): multiscale-bootstrap AU p-values over resampled CARD features, pvpick-style
  descent retaining the largest supported branch on each path.
- **Membership** (Unit 3): definers (>=30 decks AND >=8 core cards) form the dendrogram; everything
  else with >=5 core cards is assigned to the nearest cluster.

**No match outcomes enter this module.** ``ArchetypeDeck`` carries card names and nothing else, and
the single corpus query at the bottom reads ``decks``/``deck_cards``/``tournaments`` only. Tuning the
cut against the matchup coverage it unlocks is therefore not expressible here, which is what keeps
the taxonomy clear of the selective-inference trap (brief §2, epic decomposition risk 2).

**Two sourcing caveats, discharged rather than inherited** (epic instruction):

(a) pvclust resamples the ROWS of its input matrix — the axis it is not clustering (it clusters
    columns). Our objects are archetypes and our features are cards, so resampling the card
    vocabulary is pvclust's own axis. The brief flagged this as its own port; it is the faithful
    reading. The only adaptation is that the per-column statistic is a set-Jaccard, not a
    correlation.
(b) pvclust states the AU rule for a SINGLE cluster. Applying it to every branch of a dendrogram is
    an extension, and **no multiplicity correction is applied across branches** — the count of
    supported branches is optimistic in the usual multiple-comparisons direction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

__all__ = [
    "ArchetypeComposition",
    "ArchetypeDeck",
    "BranchSupport",
    "ClusterMember",
    "ClusterSolution",
    "DerivedCluster",
    "au_pvalues",
    "build_compositions",
    "cluster_archetypes",
    "comembership_stability",
    "jaccard_dissimilarity",
    "load_archetype_decks",
    "select_supported_clusters",
    "weighted_jaccard_matrix",
]


# ---------------------------------------------------------------------------
# Calibration constants
#
# Every value in this block is an author's CALIBRATION CHOICE, not a sourced result — the brief is
# explicit about which of its numbers are measured, which are sourced, and which are judgment, and
# these are all the third kind. They live here as named constants so recalibration after dogfooding
# is a one-line change, and every one is exposed as a CLI flag on `superarchetype run`.
# ---------------------------------------------------------------------------

_CORE_INCLUSION: float = 0.50
"""Maindeck inclusion rate at or above which a card is 'core' to an archetype."""

_STAPLE_DEFINER_FRACTION: float = 0.30
"""A card core to at least this fraction of DEFINERS is a format staple and is hard-removed."""

_DEFINER_MIN_DECKS: int = 30
_DEFINER_MIN_CORE_CARDS: int = 8
"""An archetype may DEFINE a cluster only above both floors. Measured: 30 archetypes, 83.8% field."""

_ASSIGNEE_MIN_CORE_CARDS: int = 5
"""Below this an archetype is left unassigned with a named reason rather than placed on noise."""

_AU_SCALES: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4)
"""Multiscale-bootstrap resample sizes as a fraction of the card vocabulary."""

_AU_MIN: float = 0.95
"""Branch AU p-value floor. Compared STRICTLY (``au > _AU_MIN``) per the brief's citation audit."""

_AU_MIN_BP: float = 0.30
"""Raw bootstrap-probability floor at scale 1.0, required IN ADDITION to the AU cut.

Not specified by the brief; added on measured evidence. AU is a bias-corrected extrapolation of BP,
and near-root branches on the real corpus show BP ~0.02-0.15 that is flat across all ten scales.
With no scale signal the fit returns curvature d ~ 0 and AU collapses to Phi(v), handing 0.93-0.97
to branches observed in under a tenth of resamples — extrapolation without evidence, in exactly the
direction that manufactures a mega-cluster. This guard states the minimum claim plainly: the branch
was also observed as a branch in at least this fraction of same-size resamples.
"""

_DEFAULT_N_BOOT: int = 200
"""Resamples per scale. 10 scales x 200 over 30 objects x ~256 cards runs in a few seconds."""

_STABILITY_MIN: float = 0.90
"""Co-membership stability cross-check. Annotates the run; never empties the taxonomy (the AU cut
already refuses unsupported branches, and failing twice on the same evidence would leave the layer
with nothing to serve)."""

_LINKAGE_METHOD = "average"
"""Average linkage: a family is broad mutual similarity, not one shared bridge card (single) and not
the worst pair (complete). Ward is not applicable to a precomputed non-Euclidean dissimilarity."""

_VALID_PROVENANCE = frozenset({"derived", "assigned", "curated"})
"""Closed vocabulary (closed-vocabulary-fail-fast-token)."""

_UNSUPPORTED_SINGLETON_NOTE = "au-unsupported singleton"
_NO_MULTIPLICITY_CORRECTION_NOTE = (
    "AU is computed per branch with NO multiplicity correction across branches — the supported-branch "
    "count is optimistic in the usual multiple-comparisons direction"
)

_EPS = 1e-9


# ---------------------------------------------------------------------------
# Unit 2 — representation (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchetypeDeck:
    """One deck's maindeck card NAMES under its archetype label.

    Copy counts are discarded at construction: superarchetype splits are package-level ("does it run
    the Show and Tell engine"), not quantity-level, and dropping counts makes the abundance confound
    structurally impossible rather than merely unused. Carries no outcome field of any kind.
    """

    archetype: str
    key: tuple[str, int]
    cards: frozenset[str]


@dataclass(frozen=True)
class ArchetypeComposition:
    """One archetype's core set before and after format-staple removal."""

    archetype: str
    n_decks: int
    core: frozenset[str]
    stripped_core: frozenset[str]
    is_definer: bool
    tier: ConfidenceLevel


def build_compositions(
    decks: Sequence[ArchetypeDeck],
    *,
    core_inclusion: float = _CORE_INCLUSION,
    staple_fraction: float = _STAPLE_DEFINER_FRACTION,
    definer_min_decks: int = _DEFINER_MIN_DECKS,
    definer_min_core: int = _DEFINER_MIN_CORE_CARDS,
) -> tuple[dict[str, ArchetypeComposition], tuple[str, ...]]:
    """Core sets, definer flags, and the derived format-staple list.

    The ordering is fixed and non-circular: raw cores for every archetype -> definers by the two
    floors -> staples as cards core to ``staple_fraction`` of the DEFINERS -> strip staples from
    every archetype's core (definer or not, so assignees live in the same space).

    Returns ``({archetype: ArchetypeComposition}, staples)``. Empty input -> ``({}, ())``.
    """
    by_arch: dict[str, list[frozenset[str]]] = {}
    for deck in decks:
        by_arch.setdefault(deck.archetype, []).append(deck.cards)
    if not by_arch:
        return {}, ()

    cores: dict[str, frozenset[str]] = {}
    for archetype, decklists in by_arch.items():
        n = len(decklists)
        counts: dict[str, int] = {}
        for cards in decklists:
            for card in cards:
                counts[card] = counts.get(card, 0) + 1
        cores[archetype] = frozenset(
            card for card, hits in counts.items() if hits / n >= core_inclusion
        )

    definers = {
        archetype
        for archetype, core in cores.items()
        if len(by_arch[archetype]) >= definer_min_decks and len(core) >= definer_min_core
    }

    staple_counts: dict[str, int] = {}
    for archetype in definers:
        for card in cores[archetype]:
            staple_counts[card] = staple_counts.get(card, 0) + 1
    staples = (
        tuple(
            sorted(
                card
                for card, hits in staple_counts.items()
                if hits / len(definers) >= staple_fraction
            )
        )
        if definers
        else ()
    )
    staple_set = frozenset(staples)

    compositions = {
        archetype: ArchetypeComposition(
            archetype=archetype,
            n_decks=len(by_arch[archetype]),
            core=core,
            stripped_core=core - staple_set,
            is_definer=archetype in definers,
            tier=tier_for_sample(len(by_arch[archetype])),
        )
        for archetype, core in cores.items()
    }
    return compositions, staples


def jaccard_dissimilarity(a: frozenset[str], b: frozenset[str]) -> float:
    """``1 - |a n b| / |a u b|``. An empty union is maximally dissimilar (1.0), never ``0/0``."""
    union = len(a | b)
    if union == 0:
        return 1.0
    return 1.0 - len(a & b) / union


def weighted_jaccard_matrix(M: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Pairwise Jaccard dissimilarity over binary rows of ``M`` under per-column ``weights``.

    ``weights`` is the multiplicity vector of one feature-vocabulary resample (a card drawn twice
    counts twice), which is the exact generalisation of set Jaccard under column resampling. With
    ``weights`` all-ones this is plain set Jaccard on the rows.
    """
    A = M * weights
    inter = A @ M.T
    row = A.sum(axis=1)
    union = row[:, None] + row[None, :] - inter
    sim = np.where(union > 0, inter / np.where(union > 0, union, 1.0), 0.0)
    D = np.clip(1.0 - sim, 0.0, 1.0)
    np.fill_diagonal(D, 0.0)
    return D


# ---------------------------------------------------------------------------
# Unit 1 — multiscale-bootstrap AU p-values + cut selection (pure — the trickiest unit)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchSupport:
    """One dendrogram branch's bootstrap support.

    ``bp`` is the raw bootstrap probability per scale in ``_AU_SCALES`` order; ``bp_at_unit_scale``
    is the entry at r=1.0, kept beside ``au`` everywhere it is rendered because AU is an
    extrapolation OF that number and the pair together is what makes it auditable. ``v``/``d`` are
    the fitted signed distance and curvature, ``None`` when the curve was unfittable (BP saturated
    at 0 or 1 on every scale).
    """

    node: int
    members: tuple[str, ...]
    height: float
    bp: tuple[float, ...]
    bp_at_unit_scale: float
    au: float
    v: float | None
    d: float | None


def _node_leaf_sets(Z: np.ndarray, n: int) -> dict[int, tuple[frozenset[int], float]]:
    """Internal-node index -> (leaf-index set, merge height) for a scipy linkage matrix."""
    sets: dict[int, frozenset[int]] = {i: frozenset((i,)) for i in range(n)}
    out: dict[int, tuple[frozenset[int], float]] = {}
    for k in range(Z.shape[0]):
        left, right, height = int(Z[k, 0]), int(Z[k, 1]), float(Z[k, 2])
        idx = n + k
        sets[idx] = sets[left] | sets[right]
        out[idx] = (sets[idx], height)
    return out


def _linkage_from(D: np.ndarray) -> np.ndarray:
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    return linkage(squareform(D, checks=False), method=_LINKAGE_METHOD)


_MIN_FIT_POINTS: int = 3
"""Usable scale points required before the two-parameter multiscale model is fitted.

A branch whose BP saturates at 0 or 1 contributes no ``psi``, and fitting ``(v, d)`` through two
surviving points is an interpolation dressed as an extrapolation — it produced AU 0.70 for a branch
present in ~99% of every resample. Below this floor the branch is scored by its mean BP instead,
which is the conservative direction (AU is normally at or above BP)."""


def _fit_au(
    bps: Sequence[float], scales: Sequence[float], n_boot: int
) -> tuple[float, float | None, float | None]:
    """Shimodaira's multiscale model: ``psi(r) = v/sqrt(r) + d*sqrt(r)``, ``AU = 1 - Phi(d - v)``.

    Weighted least squares with pvclust's BP-variance weights. Scales whose BP saturated at 0 or 1
    carry no usable ``psi`` and are dropped; below ``_MIN_FIT_POINTS`` survivors the branch is
    scored by its mean BP and the fit is reported as ``None`` rather than invented.
    """
    from scipy.stats import norm

    xs: list[list[float]] = []
    ys: list[float] = []
    ws: list[float] = []
    for r, p in zip(scales, bps, strict=True):
        if p <= _EPS or p >= 1.0 - _EPS:
            continue
        psi = float(-norm.ppf(p))
        xs.append([1.0 / np.sqrt(r), np.sqrt(r)])
        ys.append(psi)
        ws.append(n_boot * (float(norm.pdf(psi)) ** 2) / (p * (1.0 - p)))

    if len(xs) < _MIN_FIT_POINTS:
        return float(np.mean(bps)), None, None

    X = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    sw = np.sqrt(np.asarray(ws, dtype=float))
    coef, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    v, d = float(coef[0]), float(coef[1])
    return float(1.0 - norm.cdf(d - v)), v, d


def au_pvalues(
    M: np.ndarray,
    labels: Sequence[str],
    *,
    seed: int = 0,
    n_boot: int = _DEFAULT_N_BOOT,
    scales: tuple[float, ...] = _AU_SCALES,
) -> dict[int, BranchSupport]:
    """Per-branch AU p-values by multiscale bootstrap over the CARD feature vocabulary.

    ``M`` is the ``(n_archetypes, n_cards)`` binary stripped-core indicator; ``labels`` names its
    rows. For each scale the card vocabulary is resampled with replacement at ``round(r*n_cards)``,
    the weighted Jaccard matrix is rebuilt, average linkage is rerun, and a base branch scores a hit
    when its exact leaf set is a node of the bootstrap dendrogram.

    Determinism: each replicate's generator is seeded from ``(seed, scale_index, replicate_index)``,
    never a shared stream, so results are independent of iteration order and reproduce exactly.
    """
    n_rows, n_cards = M.shape
    if n_rows < 2 or n_cards == 0:
        return {}

    base = _node_leaf_sets(_linkage_from(weighted_jaccard_matrix(M, np.ones(n_cards))), n_rows)
    hits: dict[int, list[int]] = {node: [] for node in base}

    for scale_idx, r in enumerate(scales):
        size = max(1, round(r * n_cards))
        scale_hits = dict.fromkeys(base, 0)
        for boot_idx in range(n_boot):
            rng = np.random.default_rng([seed, scale_idx, boot_idx])
            weights = np.bincount(
                rng.integers(0, n_cards, size=size), minlength=n_cards
            ).astype(float)
            boot_sets = {
                leaves
                for leaves, _height in _node_leaf_sets(
                    _linkage_from(weighted_jaccard_matrix(M, weights)), n_rows
                ).values()
            }
            for node, (leaves, _height) in base.items():
                if leaves in boot_sets:
                    scale_hits[node] += 1
        for node in base:
            hits[node].append(scale_hits[node])

    unit_scale_idx = scales.index(1.0) if 1.0 in scales else len(scales) // 2
    support: dict[int, BranchSupport] = {}
    for node, (leaves, height) in base.items():
        bps = tuple(h / n_boot for h in hits[node])
        au, v, d = _fit_au(bps, scales, n_boot)
        support[node] = BranchSupport(
            node=node,
            members=tuple(sorted(labels[i] for i in leaves)),
            height=height,
            bp=bps,
            bp_at_unit_scale=bps[unit_scale_idx],
            au=au,
            v=v,
            d=d,
        )
    return support


def select_supported_clusters(
    Z: np.ndarray,
    labels: Sequence[str],
    support: Mapping[int, BranchSupport],
    *,
    au_min: float = _AU_MIN,
    min_bp: float = _AU_MIN_BP,
) -> tuple[list[list[str]], list[str], list[str]]:
    """pvpick-style cut: descend from the root, retain the largest supported branch on each path.

    A branch is eligible when ``au > au_min`` AND ``bp_at_unit_scale >= min_bp`` (see ``_AU_MIN_BP``
    for why the second condition exists). **The root is excluded from candidacy** — "every archetype
    is one cluster" makes no claim and has BP = 1.0 by construction. Leaves reached without being
    covered by a retained branch become singletons, never dropped.

    Returns ``(clusters, singletons, reasons)`` where ``clusters`` is a list of member-label lists
    and every label appears exactly once across the two.
    """
    n = len(labels)
    reasons: list[str] = [_NO_MULTIPLICITY_CORRECTION_NOTE]
    if n == 0:
        return [], [], reasons
    if n == 1:
        return [], [labels[0]], reasons + ["single definer: nothing to cluster"]

    children = {n + k: (int(Z[k, 0]), int(Z[k, 1])) for k in range(Z.shape[0])}
    root = n + Z.shape[0] - 1

    clusters: list[list[str]] = []
    singletons: list[str] = []
    stack: list[int] = list(children[root])
    while stack:
        node = stack.pop()
        if node < n:
            singletons.append(labels[node])
            continue
        branch = support.get(node)
        if branch is not None and branch.au > au_min and branch.bp_at_unit_scale >= min_bp:
            clusters.append(list(branch.members))
        else:
            stack.extend(children[node])

    clusters.sort(key=lambda members: (-len(members), members))
    singletons.sort()

    reasons.append(
        f"cut: {len(clusters)} branch(es) cleared AU > {au_min} and BP@1.0 >= {min_bp}; "
        f"{len(singletons)} definer(s) left as {_UNSUPPORTED_SINGLETON_NOTE}"
    )
    if not clusters:
        reasons.append(
            "no branch cleared the AU cut — every definer is its own superarchetype "
            "(taxonomy carries no pooling benefit; lower --au-min or add curated clusters)"
        )
    return clusters, singletons, reasons


# ---------------------------------------------------------------------------
# Unit 3 — pipeline: assignment, stability, solution (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClusterMember:
    """One archetype's membership in a cluster, with how it got there."""

    archetype: str
    provenance: str
    n_decks: int
    note: str | None = None

    def __post_init__(self) -> None:
        if self.provenance not in _VALID_PROVENANCE:
            raise ValueError(
                f"ClusterMember: provenance {self.provenance!r} must be one of "
                f"{sorted(_VALID_PROVENANCE)}"
            )


@dataclass(frozen=True)
class DerivedCluster:
    """One derived strategy cluster. ``key`` is a content key over the sorted definer members —
    stable identity across refreshes is the registry's job (max-overlap matching), not this one's."""

    key: str
    label: str
    members: tuple[ClusterMember, ...]
    au: float | None
    height: float | None
    bp_at_unit_scale: float | None


@dataclass(frozen=True)
class ClusterSolution:
    """The full result of one pure clustering pass."""

    clusters: tuple[DerivedCluster, ...]
    staples: tuple[str, ...]
    definers: tuple[str, ...]
    unassigned: tuple[tuple[str, str], ...]
    stability: float
    cophenetic: float
    reasons: tuple[str, ...]
    degraded: bool
    seed: int
    n_boot: int


def _cluster_key(definers: Sequence[str]) -> str:
    return "|".join(sorted(definers))


def _label_for(definers: Sequence[str]) -> str:
    return " + ".join(sorted(definers))


def comembership_stability(
    M: np.ndarray,
    base_partition: Sequence[int],
    *,
    seed: int,
    n_boot: int,
) -> float:
    """Mean pairwise co-membership agreement between the base partition and re-clusterings of
    feature-vocabulary resamples cut to the same K.

    Cross-check only (brief §3.4 "secondary"): it annotates the run, it never empties the taxonomy.
    Degenerate inputs (<2 rows, K<2, no replicates) return 1.0 — nothing to destabilise.
    """
    from scipy.cluster.hierarchy import fcluster

    n_rows, n_cards = M.shape
    base = np.asarray(base_partition)
    k = len(set(base.tolist()))
    if n_rows < 2 or k < 2 or n_boot <= 0:
        return 1.0

    same_base = base[:, None] == base[None, :]
    triu = np.triu_indices(n_rows, k=1)
    scores: list[float] = []
    for boot_idx in range(n_boot):
        rng = np.random.default_rng([seed, 9_999, boot_idx])
        weights = np.bincount(
            rng.integers(0, n_cards, size=n_cards), minlength=n_cards
        ).astype(float)
        boot_labels = fcluster(
            _linkage_from(weighted_jaccard_matrix(M, weights)), t=k, criterion="maxclust"
        )
        same_boot = boot_labels[:, None] == boot_labels[None, :]
        scores.append(float((same_boot == same_base)[triu].mean()))
    return float(np.mean(scores))


def _assign_remainder(
    compositions: Mapping[str, ArchetypeComposition],
    cluster_definers: Sequence[Sequence[str]],
    *,
    assignee_min_core: int,
) -> tuple[dict[int, list[tuple[str, int]]], list[tuple[str, str]]]:
    """Place every non-definer archetype on the cluster whose definers it is closest to.

    Distance is the MEAN Jaccard dissimilarity to the cluster's definer members — average linkage's
    own criterion, so an assignee is placed by the same rule that formed the cluster it joins. (The
    brief says "nearest centroid"; a literal mean vector is metric-inconsistent with Jaccard, which
    is not an inner-product space, so the average-linkage form is used and recorded as a deviation.)
    Ties break on ``(distance, cluster index)`` for determinism.

    Returns ``({cluster_index: [(archetype, n_decks)]}, [(archetype, reason)])``.
    """
    assigned: dict[int, list[tuple[str, int]]] = {i: [] for i in range(len(cluster_definers))}
    unassigned: list[tuple[str, str]] = []

    for archetype in sorted(compositions):
        comp = compositions[archetype]
        if comp.is_definer:
            continue
        if len(comp.core) < assignee_min_core:
            unassigned.append((
                archetype,
                f"below assignee core floor ({len(comp.core)} core card(s) < {assignee_min_core})",
            ))
            continue
        if not comp.stripped_core:
            unassigned.append((
                archetype,
                "no core cards survive format-staple removal — indistinguishable from the format",
            ))
            continue
        if not cluster_definers:
            unassigned.append((archetype, "no clusters exist to assign to"))
            continue

        scored = [
            (
                float(
                    np.mean([
                        jaccard_dissimilarity(comp.stripped_core, compositions[d].stripped_core)
                        for d in members
                    ])
                ),
                idx,
            )
            for idx, members in enumerate(cluster_definers)
        ]
        scored.sort()
        best_distance, best_idx = scored[0]
        if best_distance >= 1.0:
            unassigned.append((
                archetype,
                "shares no stripped-core card with any cluster (Jaccard dissimilarity 1.0)",
            ))
            continue
        assigned[best_idx].append((archetype, comp.n_decks))

    return assigned, unassigned


def cluster_archetypes(
    decks: Sequence[ArchetypeDeck],
    *,
    seed: int = 0,
    n_boot: int = _DEFAULT_N_BOOT,
    au_min: float = _AU_MIN,
    min_bp: float = _AU_MIN_BP,
    core_inclusion: float = _CORE_INCLUSION,
    staple_fraction: float = _STAPLE_DEFINER_FRACTION,
    definer_min_decks: int = _DEFINER_MIN_DECKS,
    definer_min_core: int = _DEFINER_MIN_CORE_CARDS,
    assignee_min_core: int = _ASSIGNEE_MIN_CORE_CARDS,
    scales: tuple[float, ...] = _AU_SCALES,
) -> ClusterSolution:
    """The pure pipeline: cores -> staples -> Jaccard -> average linkage -> AU cut -> assignment.

    Every refusal carries a named reason in ``reasons`` and sets ``degraded`` (honest-degrade-marker):
    no definers at all, every definer's stripped core empty, or no branch clearing the AU cut. The
    result is never a silently empty taxonomy.
    """
    from scipy.cluster.hierarchy import cophenet
    from scipy.spatial.distance import squareform

    compositions, staples = build_compositions(
        decks,
        core_inclusion=core_inclusion,
        staple_fraction=staple_fraction,
        definer_min_decks=definer_min_decks,
        definer_min_core=definer_min_core,
    )
    reasons: list[str] = []

    all_definers = sorted(a for a, c in compositions.items() if c.is_definer)
    if not all_definers:
        no_definers = (
            f"no definer archetypes: 0 of {len(compositions)} clear >={definer_min_decks} decks "
            f"AND >={definer_min_core} core cards"
        )
        return ClusterSolution(
            clusters=(), staples=staples, definers=(),
            unassigned=tuple((a, no_definers) for a in sorted(compositions)),
            stability=0.0, cophenetic=0.0,
            reasons=(f"{no_definers} — no taxonomy derivable",),
            degraded=True, seed=seed, n_boot=n_boot,
        )

    definers = [a for a in all_definers if compositions[a].stripped_core]
    dropped = [a for a in all_definers if not compositions[a].stripped_core]
    for archetype in dropped:
        reasons.append(
            f"definer {archetype!r} excluded: no core cards survive format-staple removal"
        )
    if not definers:
        return ClusterSolution(
            clusters=(), staples=staples, definers=(),
            unassigned=tuple(
                (a, "no core cards survive format-staple removal") for a in sorted(compositions)
            ),
            stability=0.0, cophenetic=0.0,
            reasons=tuple(
                reasons
                + ["staple stripping removed every definer's core — no taxonomy derivable"]
            ),
            degraded=True, seed=seed, n_boot=n_boot,
        )

    vocabulary = sorted(set().union(*(compositions[a].stripped_core for a in definers)))
    M = np.array(
        [[1.0 if card in compositions[a].stripped_core else 0.0 for card in vocabulary]
         for a in definers],
        dtype=float,
    )

    if len(definers) < 2:
        cluster_definers: list[list[str]] = []
        singletons = list(definers)
        support: dict[int, BranchSupport] = {}
        cophenetic = 0.0
        reasons.append("single definer: nothing to cluster")
    else:
        D = weighted_jaccard_matrix(M, np.ones(len(vocabulary)))
        condensed = squareform(D, checks=False)
        Z = _linkage_from(D)
        # Undefined when every pairwise distance is identical (zero variance in either the original
        # or the cophenetic distances) — report 0.0 with a named reason rather than a NaN that would
        # propagate into the persisted registry.
        with np.errstate(invalid="ignore"):
            raw_cophenetic = float(cophenet(Z, condensed)[0])
        if np.isfinite(raw_cophenetic):
            cophenetic = raw_cophenetic
        else:
            cophenetic = 0.0
            reasons.append(
                "cophenetic correlation undefined (all pairwise distances identical) — "
                "reported as 0.0"
            )
        support = au_pvalues(M, definers, seed=seed, n_boot=n_boot, scales=scales)
        cluster_definers, singletons, cut_reasons = select_supported_clusters(
            Z, definers, support, au_min=au_min, min_bp=min_bp
        )
        reasons.extend(cut_reasons)

    groups: list[list[str]] = [list(g) for g in cluster_definers] + [[s] for s in singletons]
    groups.sort(key=lambda members: (-len(members), members))

    assigned, unassigned = _assign_remainder(
        compositions, groups, assignee_min_core=assignee_min_core
    )

    support_by_key = {tuple(b.members): b for b in support.values()}
    clusters: list[DerivedCluster] = []
    for idx, definer_members in enumerate(groups):
        branch = support_by_key.get(tuple(sorted(definer_members)))
        members = [
            ClusterMember(
                archetype=a,
                provenance="derived",
                n_decks=compositions[a].n_decks,
                note=None if len(definer_members) > 1 else _UNSUPPORTED_SINGLETON_NOTE,
            )
            for a in sorted(definer_members)
        ]
        members.extend(
            ClusterMember(archetype=a, provenance="assigned", n_decks=n)
            for a, n in sorted(assigned[idx])
        )
        clusters.append(DerivedCluster(
            key=_cluster_key(definer_members),
            label=_label_for(definer_members),
            members=tuple(members),
            au=branch.au if branch is not None else None,
            height=branch.height if branch is not None else None,
            bp_at_unit_scale=branch.bp_at_unit_scale if branch is not None else None,
        ))
    clusters.sort(key=lambda c: c.key)

    group_of = {a: idx for idx, members in enumerate(groups) for a in members}
    stability = comembership_stability(
        M, [group_of[a] for a in definers], seed=seed, n_boot=n_boot
    )
    reasons.append(
        f"co-membership stability {stability:.3f} "
        f"{'>=' if stability >= _STABILITY_MIN else '<'} {_STABILITY_MIN} "
        "(cross-check only — never gates the taxonomy)"
    )
    reasons.append(
        f"cophenetic correlation {cophenetic:.3f} (regression tripwire on method changes only — "
        "never an arbiter between representations)"
    )

    degraded = not cluster_definers or bool(dropped)
    return ClusterSolution(
        clusters=tuple(clusters),
        staples=staples,
        definers=tuple(definers),
        unassigned=tuple(unassigned),
        stability=stability,
        cophenetic=cophenetic,
        reasons=tuple(reasons),
        degraded=degraded,
        seed=seed,
        n_boot=n_boot,
    )


# ---------------------------------------------------------------------------
# Unit 4 — DB wrapper (thin, read-only)
#
# The ONLY corpus query in this package. It names `decks`, `deck_cards` and `tournaments` and
# nothing else — in particular it never touches `rounds` or `match_results`, which is what makes
# tuning the cut against matchup coverage structurally unreachable from here.
# ---------------------------------------------------------------------------


def load_archetype_decks(
    con,
    *,
    since: str | None = None,
    until: str | None = None,
    since_by_archetype: Mapping[str, str | None] | None = None,
) -> list[ArchetypeDeck]:
    """Read every labeled deck's maindeck card NAMES in the window into plain ``ArchetypeDeck`` rows.

    Read-only, one pass. Copy counts are dropped here rather than downstream so no consumer of this
    module can reintroduce an abundance signal by accident.
    """
    rows = con.execute(
        """
        SELECT d.archetype, d.tournament_id, d.deck_idx, dc.name, t.date
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        JOIN deck_cards dc
          ON dc.tournament_id = d.tournament_id
         AND dc.deck_idx      = d.deck_idx
        WHERE dc.board = 'main'
          AND dc.count > 0
          AND d.archetype IS NOT NULL
          AND d.archetype <> ''
          AND (? IS NULL OR t.date >= ?)
          AND (? IS NULL OR t.date <= ?)
        """,
        [since, since, until, until],
    ).fetchall()

    staged: dict[tuple[str, int], tuple[str, set[str]]] = {}
    for archetype, tournament_id, deck_idx, name, tournament_date in rows:
        entity_since = (
            since_by_archetype.get(archetype) if since_by_archetype is not None else None
        )
        if entity_since is not None and str(tournament_date)[:10] < entity_since:
            continue
        key = (tournament_id, deck_idx)
        entry = staged.get(key)
        if entry is None:
            staged[key] = (archetype, {name})
        else:
            entry[1].add(name)

    return [
        ArchetypeDeck(archetype=archetype, key=key, cards=frozenset(cards))
        for key, (archetype, cards) in sorted(staged.items())
    ]
