"""Superarchetype chain kernel — registry consumption, era-windowed member-tally drawing, the
prior rungs, and the display-ladder resolution (epic-superarchetype-layer-chain).

Position in the layer: ``aggregate.py`` is the pure estimator over ``MemberTally`` rows; THIS
module is the pure bridge between a built adaptive multi-split matrix's windowed tally dicts and
that estimator. ``matchup.build_multi_split_adaptive`` computes ``pooled_by_since``/
``valid_since``/``camp_parent`` once and hands plain dicts here (objective-search-split), so
every rule in this file is unit-testable with hand-built inputs and NO DB.

Era discipline (epic addendum #2, binding):

- a member's tally enters a pool only at its PAIRWISE window ``max(valid_since[subject],
  valid_since[member])`` — always an existing scan bucket, since the max of two horizon dates is
  one of them. The kernel never re-windows; it selects buckets the builder already scanned.
- contributors are registry members with provenance ``derived``/``curated``; ``assigned`` members
  carry ``definer=False`` and are excluded BY THE ESTIMATOR with a named exclusion
  (contribute-vs-receive). Members absent from the matrix's entity set (below the row floor)
  cannot be pairwise-windowed and are excluded BY NAME here instead.
- freshness rides every pooled/imputed cell: a window-mix note plus the pool's current-regime
  share (``n`` at ``max(pair window, regime start)`` over pool ``n``), computed here and passed
  through the estimator untouched.

**This module is DB-free and never imports duckdb** (asserted by a test, same discipline as the
clustering side's no-rounds test). Registry types appear only under ``TYPE_CHECKING``; runtime
inputs are plain mappings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from legacy_engine.analytics.superarchetype.aggregate import (
    MemberSplit,
    MemberTally,
    PooledCell,
    aggregate_cluster_cell,
)
from legacy_engine.confidence import tier_for_sample

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from legacy_engine.analytics.superarchetype.registry import SuperarchetypeRegistry

__all__ = [
    "FAMILY_FIRST_KINDS",
    "ClusterView",
    "DrawnPool",
    "LadderEntry",
    "RungPrior",
    "cluster_view",
    "draw_cluster_pair_tallies",
    "draw_pool_tallies",
    "draw_row_tallies",
    "registry_audit_lines",
    "resolve_ladder",
    "rung_prior",
    "subject_base",
]

_CONTRIBUTOR_PROVENANCE = frozenset({"derived", "curated"})
"""Registry provenance values that may contribute tallies to pools (era addendum #2 rule 1);
``assigned`` members receive imputation but never contribute."""

_PRIOR_BANDS = frozenset({"free", "labelled"})
"""Heterogeneity bands under which a pooled cell may anchor a prior. ``refused`` fails the gate
outright; ``not-computable`` is NOT a pass — an independent prior rung needs a positive verdict,
and the rung label's ``I²=`` slot must carry a number."""

FAMILY_FIRST_KINDS: frozenset[str] = frozenset()
"""MEASURED, not asserted (era addendum #2 rule 5 — the ladder-order decision this feature owns).

``scripts/loo_ladder_harness.py`` over the real corpus (2026-08-01, serving registry window
2026-05-11, read-only): for young-era cells, predict each disturbed subject's eventual post-era
cell value with (a) its own pre-disturbance anchor (the cross-era prior construction) vs (b)
family-current imputation (contributor siblings' pooled rate, leave-subject-out), per winning-
boundary attribution kind. Preregistered floors truth n>=20 / sibling pool n>=40 / >=10 cells per
kind to decide:

- ban:          1 cell  — too thin (anchor MAE 0.0156 vs family 0.1188 on that cell)
- release:      4 cells — too thin (anchor MAE 0.1510 vs family 0.1741, family wins 2/4)
- unattributed: 0 cells — too thin

Sensitivity at the serving floors (truth n>=15, pool n>=25 = ``_IMPUTE_MIN_POOL``): 14 cells,
still <10 per kind, and the ANCHOR wins the pooled composition bucket (MAE 0.1138 vs 0.1282,
family 4/10) and unattributed (0.1578 vs 0.3119, family 0/4). Family DID beat the marginal
(0.1282 vs 0.1359 composition), consistent with the epic's 2026-08-01 probe — but the own-past
anchor is the stronger incumbent for young-era cells, so the hypothesis ("family-first for
composition-disturbed") is NOT supported on today's corpus and every kind keeps the existing
anchor-first order. Empty set = the cross-era prior keeps precedence everywhere it applies; the
mechanism below stays wired so a future re-measure is a one-line recalibration."""


# ---------------------------------------------------------------------------
# Registry consumption
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClusterView:
    """The registry flattened for matrix consumption.

    ``cluster_of`` covers EVERY member (assignees included — they receive); ``contributors``
    lists only ``derived``/``curated`` members (they alone contribute tallies). ``members``
    preserves registry order per cluster; lookups are by parent-archetype label (camps resolve
    through ``subject_base`` first — a camp inherits its parent's cluster, brief §9).
    """

    cluster_of: dict[str, str]
    label_of: dict[str, str]
    members: dict[str, tuple[str, ...]]
    contributors: dict[str, frozenset[str]]

    @property
    def cluster_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.members))


def cluster_view(registry: "SuperarchetypeRegistry | None") -> ClusterView | None:
    """Flatten a registry, or ``None`` when there is nothing to consume (absent or clusterless
    registry — the gated-additive data-presence gate; the caller-intent gate is the builder's
    ``superarchetypes=None`` default)."""
    if registry is None or not registry.clusters:
        return None
    cluster_of: dict[str, str] = {}
    label_of: dict[str, str] = {}
    members: dict[str, tuple[str, ...]] = {}
    contributors: dict[str, frozenset[str]] = {}
    for cluster in registry.clusters:
        label_of[cluster.id] = cluster.label
        members[cluster.id] = tuple(m.archetype for m in cluster.members)
        contributors[cluster.id] = frozenset(
            m.archetype for m in cluster.members if m.provenance in _CONTRIBUTOR_PROVENANCE
        )
        for m in cluster.members:
            cluster_of[m.archetype] = cluster.id
    return ClusterView(
        cluster_of=cluster_of, label_of=label_of, members=members, contributors=contributors,
    )


def subject_base(label: str, camp_parent: "Mapping[str, str]") -> str:
    """A camp label's parent archetype (itself for plain labels) — the registry's key space."""
    return camp_parent.get(label, label)


def registry_audit_lines(
    registry: "SuperarchetypeRegistry", *, regime_start: str | None
) -> tuple[str, ...]:
    """The loud consumption-side provenance echo (epic decision 3: a window mismatch between
    registry and matrix is an audit line, never silent staleness).

    The per-subject churn flag is NOT reconstructible here — the persisted registry carries no
    previous-run diff — so churn stays a run-side audit concern (named gap, feature design
    decision 11)."""
    n_contributors = sum(
        1 for c in registry.clusters for m in c.members
        if m.provenance in _CONTRIBUTOR_PROVENANCE
    )
    lines = [
        (
            f"// superarchetype: {len(registry.clusters)} clusters "
            f"({n_contributors} contributors), "
            f"window {registry.window_since or 'FULL CORPUS'}..{registry.window_until or 'open'}, "
            f"derived {registry.derived_at[:10]}"
        )
    ]
    if registry.window_since is None:
        lines.append(
            "// superarchetype: ⚠ FULL-CORPUS registry — exploratory taxonomy serving a windowed "
            "matrix (era-mix risk); re-run `superarchetype run --since <regime start>`"
        )
    elif regime_start is not None and registry.window_since < regime_start:
        lines.append(
            f"// superarchetype: ⚠ registry window {registry.window_since} predates the current "
            f"regime start {regime_start} — stale taxonomy (window mismatch)"
        )
    if registry.degraded:
        lines.append(
            "// superarchetype: ⚠ DEGRADED taxonomy — see `superarchetype run` for the named "
            "reasons"
        )
    return tuple(lines)


# ---------------------------------------------------------------------------
# Era-windowed tally drawing (pure — selects buckets the builder already scanned)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DrawnPool:
    """Member tallies for one pool plus the freshness provenance computed at draw time.

    ``window_note`` names the pairwise-window mix of the CONTRIBUTING tallies and every member
    that could not be drawn (below the row floor / no matches) — nothing is silently absent.
    ``current_regime_share`` is ``None`` only when nothing contributed.
    """

    tallies: tuple[MemberTally, ...]
    window_note: str
    current_regime_share: float | None


def _pair_window(a: str | None, b: str | None) -> str | None:
    return max(a or "", b or "") or None


def _regime_n(
    pooled_by_since: "Mapping[str | None, Mapping[tuple[str, str], tuple[int, int]]]",
    key: tuple[str, str],
    window: str | None,
    n: int,
    regime_start: str | None,
) -> int:
    """The share of a drawn tally's ``n`` that falls inside the current regime.

    A tally whose pairwise window already starts at/after the regime start is entirely current;
    otherwise the same pair is read at the regime-start bucket (the builder guarantees that
    bucket exists whenever ``regime_start`` is not ``None``)."""
    if regime_start is None or (window is not None and window >= regime_start):
        return n
    return pooled_by_since[regime_start].get(key, (0, 0))[1]


def _mix_note(window_counts: "Mapping[str | None, int]", not_drawn: "Sequence[str]") -> str:
    mix = ", ".join(
        f"{window or 'full'} x{count}"
        for window, count in sorted(window_counts.items(), key=lambda kv: (kv[0] or "", kv[1]))
    )
    note = f"member windows: {mix}" if mix else "member windows: (none)"
    if not_drawn:
        note += f"; not drawn: {'; '.join(not_drawn)}"
    return note


def draw_pool_tallies(
    subject: str,
    cluster_id: str,
    view: ClusterView,
    *,
    pooled_by_since: "Mapping[str | None, Mapping[tuple[str, str], tuple[int, int]]]",
    valid_since: "Mapping[str, str | None]",
    subject_cluster_id: str | None,
    subject_mirror_n: int = 0,
    exclude_opponent: str | None = None,
    regime_start: str | None = None,
) -> DrawnPool:
    """Draw the subject's tallies against one cluster's members, pairwise-windowed.

    ``exclude_opponent`` is the leave-opponent-out discipline for the PRIOR rung: the opponent's
    own tally is excluded by MEMBER EXCLUSION — structurally exact, nothing to subtract or clamp
    (brief §7's subtraction discipline lives where counts are actually summed, i.e. the
    split-parent partition sums in ``draw_row_tallies``). The display pool passes ``None`` and
    includes the opponent's own matches (brief §8's stated difference).

    ``subject_mirror_n`` injects the subject's self-mirror count when the subject's base label is
    inside the cluster — the estimator excludes it from the rate and reports it as ``mirror_n``
    (brief §7). Camp subjects never inject: their family-internal matches are the deliberately
    absent ``(camp, own_parent)`` pairs, so they are not in the pool at all.
    """
    subject_since = valid_since[subject]
    intra = subject_cluster_id == cluster_id
    tallies: list[MemberTally] = []
    not_drawn: list[str] = []
    window_counts: dict[str | None, int] = {}
    pool_n = 0
    pool_n_current = 0

    for member in view.members[cluster_id]:
        if member == exclude_opponent:
            continue
        if member == subject:
            if subject_mirror_n > 0:
                tallies.append(MemberTally(
                    archetype=subject, wins=subject_mirror_n // 2, n=subject_mirror_n,
                    intra_cluster=True, definer=member in view.contributors[cluster_id],
                ))
            continue
        member_since = valid_since.get(member, _MISSING)
        if member_since is _MISSING:
            not_drawn.append(f"{member} (below the row floor — no resolved horizon)")
            continue
        window = _pair_window(subject_since, member_since)
        key = (subject, member)
        wins, n = pooled_by_since[window].get(key, (0, 0))
        if n == 0:
            not_drawn.append(f"{member} (no matches in window {window or 'full'})")
            continue
        definer = member in view.contributors[cluster_id]
        tallies.append(MemberTally(
            archetype=member, wins=wins, n=n, intra_cluster=intra, definer=definer,
        ))
        if definer:
            window_counts[window] = window_counts.get(window, 0) + 1
            pool_n += n
            pool_n_current += _regime_n(pooled_by_since, key, window, n, regime_start)

    share = (pool_n_current / pool_n) if pool_n else None
    return DrawnPool(
        tallies=tuple(tallies),
        window_note=_mix_note(window_counts, not_drawn),
        current_regime_share=share,
    )


_MISSING = object()


def draw_row_tallies(
    members: "Sequence[str]",
    opponent: str,
    *,
    pooled_by_since: "Mapping[str | None, Mapping[tuple[str, str], tuple[int, int]]]",
    valid_since: "Mapping[str, str | None]",
    camps_of: "Mapping[str, Sequence[str]]",
    regime_start: str | None = None,
) -> tuple[dict[str, tuple[int, int, str | None, int]], list[str]]:
    """Each member's SUBJECT-SIDE tally vs one parent-level opponent, pairwise-windowed.

    Returns ``{member: (wins, n, window, n_current)}`` plus the not-drawn names. A split parent's
    row does not exist at parent granularity (its decks are camp-labeled), so its tally is the
    partition sum over its camps within the member's own window bucket — exact by the camp
    partition property, and additions only (nothing to go negative).
    """
    out: dict[str, tuple[int, int, str | None, int]] = {}
    not_drawn: list[str] = []
    for member in members:
        member_since = valid_since.get(member, _MISSING)
        if member_since is _MISSING:
            not_drawn.append(f"{member} (below the row floor — no resolved horizon)")
            continue
        window = _pair_window(member_since, valid_since.get(opponent))
        pooled = pooled_by_since[window]
        rows = camps_of.get(member) or (member,)
        wins = n = n_current = 0
        for row in rows:
            key = (row, opponent)
            w, m = pooled.get(key, (0, 0))
            wins += w
            n += m
            if m:
                n_current += _regime_n(pooled_by_since, key, window, m, regime_start)
        if n == 0:
            not_drawn.append(f"{member} (no matches in window {window or 'full'})")
            continue
        out[member] = (wins, n, window, n_current)
    return out, not_drawn


def draw_cluster_pair_tallies(
    subject: str,
    gs_id: str,
    go_id: str,
    view: ClusterView,
    *,
    pooled_by_since: "Mapping[str | None, Mapping[tuple[str, str], tuple[int, int]]]",
    valid_since: "Mapping[str, str | None]",
    camp_parent: "Mapping[str, str]",
    camps_of: "Mapping[str, Sequence[str]]",
    exclude_opponent: str | None = None,
    regime_start: str | None = None,
) -> DrawnPool:
    """Rung 2's tallies: the SUBJECT family's contributors (leave-S-out), each contributing a
    count-pooled tally against the OPPONENT family's contributors (leave-O-out, skip self-pairs).

    The DL fit runs across the subject-side members — the axis the licensed-imputation probe
    validated — so the gates measure whether the subject's siblings agree about the opposing
    family. A singleton subject family yields no tallies and the estimator refuses ("not a pool
    at all"), which is correct: rung 1 already did the opponent side.
    """
    base = subject_base(subject, camp_parent)
    intra = gs_id == go_id
    opponent_members = [
        m for m in sorted(view.contributors[go_id]) if m != exclude_opponent
    ]
    tallies: list[MemberTally] = []
    not_drawn: list[str] = []
    window_counts: dict[str | None, int] = {}
    pool_n = 0
    pool_n_current = 0

    for member in sorted(view.contributors[gs_id]):
        if member == base:
            continue
        opponents = [o for o in opponent_members if o != member]
        wins = n = n_current = 0
        member_since = valid_since.get(member, _MISSING)
        if member_since is _MISSING:
            not_drawn.append(f"{member} (below the row floor — no resolved horizon)")
            continue
        rows = camps_of.get(member) or (member,)
        for opponent in opponents:
            window = _pair_window(member_since, valid_since.get(opponent))
            pooled = pooled_by_since[window]
            for row in rows:
                key = (row, opponent)
                w, m = pooled.get(key, (0, 0))
                wins += w
                n += m
                if m:
                    n_current += _regime_n(pooled_by_since, key, window, m, regime_start)
                    window_counts[window] = window_counts.get(window, 0) + 1
        if n == 0:
            not_drawn.append(f"{member} (no matches vs {go_id} contributors)")
            continue
        tallies.append(MemberTally(
            archetype=member, wins=wins, n=n, intra_cluster=intra, definer=True,
        ))
        pool_n += n
        pool_n_current += n_current

    share = (pool_n_current / pool_n) if pool_n else None
    return DrawnPool(
        tallies=tuple(tallies),
        window_note=_mix_note(window_counts, not_drawn),
        current_regime_share=share,
    )


# ---------------------------------------------------------------------------
# The prior rungs (chain position fixed by the epic: camp -> LCO parent' ->
# superarchetype cell -> cluster x cluster -> marginal' -> 0.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RungPrior:
    """One admissible superarchetype prior: the mean/strength/label ``build_cell`` consumes plus
    the full ``PooledCell`` behind it (so refusal reasons and the I² one-sided note survive)."""

    mean: float
    strength: float
    source: str
    rung: int
    cell: PooledCell


def _admissible(cell: PooledCell) -> bool:
    """A rung that fails its concentration or heterogeneity gate is SKIPPED (brief §8); the chain
    falls through. ``not-computable`` heterogeneity is not a pass (design decision 5)."""
    return (
        cell.pooled_p is not None
        and cell.concentration is not None and cell.concentration.passed
        and cell.heterogeneity is not None and cell.heterogeneity.band in _PRIOR_BANDS
    )


def rung_prior(
    subject: str,
    opponent: str,
    view: ClusterView,
    *,
    pooled_by_since: "Mapping[str | None, Mapping[tuple[str, str], tuple[int, int]]]",
    valid_since: "Mapping[str, str | None]",
    camp_parent: "Mapping[str, str]",
    camps_of: "Mapping[str, Sequence[str]]",
    regime_start: str | None = None,
) -> RungPrior | None:
    """Resolve the superarchetype prior for one directed cell, or ``None`` (fall through to the
    marginal). Rung 1 — the subject vs the opponent's cluster, leave-opponent-out — is tried
    first; rung 2 (cluster × cluster, leave-S-out, leave-O-out; PRIOR ONLY per the epic's locked
    decision) only when rung 1 is inadmissible. Strength is the estimator's evidence-gated
    ``[5, 30]`` prior strength, never the raw pool size.
    """
    go_id = view.cluster_of.get(opponent)
    if go_id is None:
        return None

    subject_cluster_id = view.cluster_of.get(subject_base(subject, camp_parent))

    drawn = draw_pool_tallies(
        subject, go_id, view,
        pooled_by_since=pooled_by_since, valid_since=valid_since,
        subject_cluster_id=subject_cluster_id,
        exclude_opponent=opponent, regime_start=regime_start,
    )
    cell = aggregate_cluster_cell(
        subject, go_id, drawn.tallies,
        window_note=drawn.window_note, current_regime_share=drawn.current_regime_share,
    )
    if _admissible(cell):
        assert cell.pooled_p is not None and cell.prior is not None  # _admissible guarantees
        assert cell.concentration is not None and cell.heterogeneity is not None
        source = (
            f"superarchetype cell (leave-opponent-out; {go_id}, "
            f"m_eff {cell.concentration.m_eff:.1f}, I²={cell.heterogeneity.i2:.2f})"
        )
        return RungPrior(
            mean=cell.pooled_p, strength=cell.prior.strength, source=source, rung=1, cell=cell,
        )

    if subject_cluster_id is None:
        return None
    drawn2 = draw_cluster_pair_tallies(
        subject, subject_cluster_id, go_id, view,
        pooled_by_since=pooled_by_since, valid_since=valid_since,
        camp_parent=camp_parent, camps_of=camps_of,
        exclude_opponent=opponent, regime_start=regime_start,
    )
    pair_id = f"{subject_cluster_id}×{go_id}"
    cell2 = aggregate_cluster_cell(
        subject, pair_id, drawn2.tallies,
        window_note=drawn2.window_note, current_regime_share=drawn2.current_regime_share,
    )
    if _admissible(cell2):
        assert cell2.pooled_p is not None and cell2.prior is not None
        assert cell2.concentration is not None and cell2.heterogeneity is not None
        source = (
            f"cluster × cluster (leave-S-out, leave-O-out; {pair_id}, "
            f"m_eff {cell2.concentration.m_eff:.1f}, I²={cell2.heterogeneity.i2:.2f})"
        )
        return RungPrior(
            mean=cell2.pooled_p, strength=cell2.prior.strength, source=source, rung=2, cell=cell2,
        )
    return None


# ---------------------------------------------------------------------------
# Display-ladder resolution (data only — rendering is -best-call-fallback's job)
# ---------------------------------------------------------------------------

_VALID_LADDER_KINDS = frozenset({"measured", "pooled", "imputed", "none"})
"""Closed vocabulary (closed-vocabulary-fail-fast-token)."""


@dataclass(frozen=True)
class LadderEntry:
    """One sub-display cell's resolved fallback, with every finer refusal named.

    ``kind`` walks the fixed order measured -> imputed -> pooled -> none: the imputed cell keeps
    the CELL's own question (S vs O, borrowed subject-side evidence) and is finer than the pooled
    cell's coarsened question (S vs the family of O) — the epic addendum's display ladder.
    ``sibling_split`` carries the per-sibling records behind an attempted imputation so a refusal
    can render as the family-range display. The referenced ``ImputedCell``/``PooledCell`` live in
    the matrix's ``imputed_cells``/``cluster_cells`` maps — reasons, licenses, and the I²
    one-sided note ride there in full.
    """

    subject: str
    opponent: str
    kind: str
    cluster_id: str | None
    token: str
    reasons: tuple[str, ...]
    sibling_split: tuple[MemberSplit, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in _VALID_LADDER_KINDS:
            raise ValueError(
                f"LadderEntry: kind {self.kind!r} must be one of {sorted(_VALID_LADDER_KINDS)}"
            )


def _sibling_split(tallies: "Sequence[MemberTally]") -> tuple[MemberSplit, ...]:
    return tuple(
        MemberSplit(
            archetype=t.archetype, wins=t.wins, n=t.n, p_hat=t.p_hat,
            tier=tier_for_sample(t.n), intra_cluster=t.intra_cluster,
        )
        for t in sorted(tallies, key=lambda t: t.archetype)
    )


def resolve_ladder(
    subject: str,
    opponent: str,
    *,
    measured_n: int,
    display_gate_n: int,
    opponent_cluster_id: str | None,
    pooled: PooledCell | None,
    imputed,  # aggregate.ImputedCell | None
    imputed_tallies: "Sequence[MemberTally]" = (),
) -> LadderEntry:
    """Resolve one cell's display fallback per the fixed ladder, refusals named at every step."""
    if measured_n >= display_gate_n:
        return LadderEntry(
            subject=subject, opponent=opponent, kind="measured", cluster_id=None,
            token=f"measured (n={measured_n})", reasons=(),
        )

    reasons: list[str] = [f"measured cell below the display gate (n={measured_n} < {display_gate_n})"]

    if imputed is not None:
        if imputed.p is not None:
            return LadderEntry(
                subject=subject, opponent=opponent, kind="imputed",
                cluster_id=imputed.license.cluster_id,
                token=(
                    f"imputed from {imputed.license.cluster_id} "
                    f"({len(imputed.siblings)} sibs, pool n={imputed.pool_n})"
                ),
                reasons=tuple(reasons),
                sibling_split=_sibling_split(imputed_tallies),
            )
        reasons.append(f"imputation refused: {imputed.reason}")
    else:
        reasons.append("imputation not attempted: subject has no cluster in the registry")

    if pooled is not None and opponent_cluster_id is not None:
        if pooled.pooled_p is not None and pooled.n_eff >= display_gate_n:
            intra_note = ""
            if pooled.intra_cluster_share:
                intra_note = f", intra-family share {pooled.intra_cluster_share:.0%}"
            return LadderEntry(
                subject=subject, opponent=opponent, kind="pooled",
                cluster_id=opponent_cluster_id,
                token=(
                    f"pooled vs {opponent_cluster_id} "
                    f"(n_eff {pooled.n_eff:.0f}, tier {pooled.tier}{intra_note})"
                ),
                reasons=tuple(reasons),
                sibling_split=_sibling_split(imputed_tallies) if imputed is not None else (),
            )
        if pooled.refused_reason is not None:
            reasons.append(f"pooled cell refused: {pooled.refused_reason}")
        else:
            reasons.append(
                f"pooled cell below the display gate (n_eff {pooled.n_eff:.0f} < {display_gate_n})"
            )
    else:
        reasons.append("no pooled cell: opponent has no cluster in the registry")

    return LadderEntry(
        subject=subject, opponent=opponent, kind="none", cluster_id=opponent_cluster_id,
        token="no displayable fallback", reasons=tuple(reasons),
        sibling_split=_sibling_split(imputed_tallies) if imputed is not None else (),
    )
