"""Matchup matrix — Wilson/Jeffreys CIs, Beta-Binomial shrinkage, cell builder, matrix builder.

This module is the consumer of ``match_results.compute_match_results``.  It
turns raw ``{wins, losses, n}`` tallies into fully-computed ``MatchupCell``
objects and assembles them into a ``MatchupMatrix`` that carries both the cells
and provenance metadata.

Units covered:
- Unit 2: Stats primitives — ``wilson_or_jeffreys_ci``, ``beta_binomial_shrink``
- Unit 4: Cell builder — ``build_cell``, ``build_mirror_cell``
- Unit 5: Matrix builder — ``MatchupMatrix``, ``build_matrix``
- epic-stable-era-windows-shrinkage Units 1+2: hierarchical + cross-era cell prior —
  ``_cell_prior``, ``_camp_hierarchy_inputs`` (Unit 1); ``build_adaptive_matrix``'s
  ``_cross_era_prior`` (Unit 2)
- feature-multi-split-matrix Unit 2: pooling + multi-parent hierarchy —
  ``_pool_opponent_tallies``, ``_multi_hierarchy_inputs``, ``MultiSplitMatrix``,
  ``build_multi_split_matrix``
- feature-multi-split-matrix Unit 3: era-windowed multi-split —
  ``AdaptiveMultiSplitMatrix``, ``build_multi_split_adaptive``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from statsmodels.stats.proportion import proportion_confint

from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.confidence import tier_for_sample
from legacy_engine.models.matchup import MatchupCell

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from legacy_engine.analytics.eras.consume import EraHorizon
    from legacy_engine.analytics.match_results import MatchResults
    from legacy_engine.analytics.superarchetype.aggregate import ImputedCell, PooledCell
    from legacy_engine.analytics.superarchetype.chain import LadderEntry
    from legacy_engine.analytics.superarchetype.registry import SuperarchetypeRegistry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHRINK_ALPHA = 7.5  # Beta prior centered 0.5, strength α+β=15 (brief: α=β≈5–10)
SHRINK_BETA = 7.5
SHRINK_STRENGTH = 2 * SHRINK_ALPHA  # = 15; used by the generalized shrink primitive
JEFFREYS_MAX_N = 40  # use Jeffreys for n<=40; Wilson for n>40
DISPLAY_GATE_N = 30  # n<30 → speculative; hide the rate

_CAVEAT = (
    "Matchup data is computed only from rounds-bearing events (Challenges + paper); "
    "matchup-n is a separate, smaller sample than meta-share-n. Cells with n<30 are hidden."
)


# ---------------------------------------------------------------------------
# Unit 2: Stats primitives
# ---------------------------------------------------------------------------


def wilson_or_jeffreys_ci(
    wins: int, n: int, *, alpha: float = 0.05
) -> tuple[float, float]:
    """95% CI for wins/n.  Jeffreys for n<=40 (coherent with the shrinkage prior); Wilson otherwise.

    Returns ``(low, high)`` in [0, 1].  ``n==0`` → ``(0.0, 1.0)`` (no information).
    Delegates to ``statsmodels.stats.proportion.proportion_confint``; Wald is
    never used (the brief forbids it — it can produce intervals outside [0, 1]).
    """
    if n == 0:
        return (0.0, 1.0)
    method = "jeffreys" if n <= JEFFREYS_MAX_N else "wilson"
    low, high = proportion_confint(wins, n, alpha=alpha, method=method)
    # Clamp to [0,1] as a safety net (both methods stay in-range, but be explicit)
    return (max(0.0, float(low)), min(1.0, float(high)))


def beta_binomial_shrink_to(
    wins: int,
    n: int,
    *,
    prior_mean: float,
    strength: float = SHRINK_STRENGTH,
) -> float:
    """Posterior-mean shrinkage toward an arbitrary ``prior_mean``.

    Prior is parameterized as ``a = prior_mean * strength``,
    ``b = (1 - prior_mean) * strength``.  Posterior mean is
    ``(a + wins) / (a + b + n)``.

    ``n == 0`` → returns ``prior_mean`` (the prior, no data).
    With ``prior_mean=0.5`` and ``strength=15`` this is byte-identical to
    the original ``beta_binomial_shrink``.
    """
    a = prior_mean * strength
    b = (1.0 - prior_mean) * strength
    denom = a + b + n
    return (a + wins) / denom if denom else prior_mean


def beta_binomial_shrink(
    wins: int,
    n: int,
    *,
    a: float = SHRINK_ALPHA,
    b: float = SHRINK_BETA,
) -> float:
    """Posterior-mean shrinkage toward 0.5: ``(a + wins) / (a + b + n)``.

    ``n==0`` → ``0.5`` (the prior mean, no data).  With the default prior
    (α=β=7.5, strength 15): a 3–1 cell reads ~0.553 (not 0.75); a 120–80
    cell reads ~0.558 (essentially unshrunk).

    Delegates to ``beta_binomial_shrink_to`` with ``prior_mean=0.5`` so
    outputs are byte-identical (regression-critical).
    """
    return beta_binomial_shrink_to(wins, n, prior_mean=0.5, strength=a + b)


# ---------------------------------------------------------------------------
# Unit 4: Cell builder
# ---------------------------------------------------------------------------


def build_cell(
    archetype_a: str,
    archetype_b: str,
    wins: int,
    n: int,
    *,
    prior_mean: float = 0.5,
    prior_source: str | None = None,
    prior_strength: float = SHRINK_STRENGTH,
) -> MatchupCell:
    """Build a directed ``MatchupCell`` for ``archetype_a`` vs ``archetype_b``.

    Computes raw win-rate, shrunk estimate, CI, tier, and display flag in one
    place so consumers (charts, advisory) never re-derive the gate logic.
    ``p_raw`` is always populated when ``n > 0`` (the brief forbids showing
    shrinkage without the raw number — but the ``display`` gate, not ``p_raw``
    presence, is what hides speculative cells from the UI).

    ``prior_mean``/``prior_source`` (epic-stable-era-windows-shrinkage, additive default
    ``prior_mean=0.5``/``prior_source=None`` — byte-identical to the pre-hierarchy flat prior
    for any caller that doesn't pass one): the Beta prior ``p_shrunk`` shrinks toward, and its
    human-readable provenance label. ``build_matrix``/``build_adaptive_matrix`` always pass an
    explicit hierarchical prior (see ``_cell_prior``); direct callers (tests, other consumers
    building hand-made cells) keep the flat-0.5 default.

    ``prior_strength`` (epic-superarchetype-layer-chain, additive default ``SHRINK_STRENGTH`` —
    byte-identical for every caller that doesn't pass one): the Beta prior's total strength. The
    superarchetype rungs supply the estimator's evidence-gated ``[5, 30]`` strength so a coherent
    cluster anchors harder than an incoherent one; every other rung keeps the default 15.

    ``n == 0``: ``p_raw``/``ci_low``/``ci_high`` stay ``None`` (no observations — an honest "no
    data" for the raw record), but ``p_shrunk`` becomes ``prior_mean`` itself (design decision:
    "n=0 cells return the prior mean with the source label" — never ``None``-only, since the
    prior IS the model's best belief absent data). This is never shown as a confident number to
    users because ``display`` is already ``False`` for ``n < 30`` (which includes ``n == 0``);
    the raw-must-travel-with-shrunk honesty rule is enforced at the ``display`` gate, not by
    hiding ``p_shrunk``.
    """
    tier = tier_for_sample(n)
    display = n >= DISPLAY_GATE_N
    if n > 0:
        p_raw: float | None = wins / n
        p_shrunk: float | None = beta_binomial_shrink_to(
            wins, n, prior_mean=prior_mean, strength=prior_strength,
        )
        ci_low, ci_high = wilson_or_jeffreys_ci(wins, n)
    else:
        p_raw = None
        p_shrunk = prior_mean
        ci_low, ci_high = (None, None)
    return MatchupCell(
        archetype_a=archetype_a,
        archetype_b=archetype_b,
        wins=wins,
        n=n,
        p_raw=p_raw,
        p_shrunk=p_shrunk,
        ci_low=ci_low,
        ci_high=ci_high,
        tier=tier,
        is_mirror=False,
        display=display,
        prior_mean=prior_mean,
        prior_source=prior_source,
    )


def build_mirror_cell(archetype: str, n: int) -> MatchupCell:
    """Build a mirror ``MatchupCell`` for ``archetype`` vs itself.

    Mirror matches have a fixed 50% rate by symmetry — no CI is meaningful.
    ``wins`` is set to ``n // 2`` cosmetically (half the mirror matches "won").
    ``display`` follows the same n<30 gate as non-mirror cells.
    """
    return MatchupCell(
        archetype_a=archetype,
        archetype_b=archetype,
        wins=n // 2,
        n=n,
        p_raw=0.5,
        p_shrunk=0.5,
        ci_low=None,
        ci_high=None,
        tier=tier_for_sample(n),
        is_mirror=True,
        display=n >= DISPLAY_GATE_N,
    )


# ---------------------------------------------------------------------------
# Hierarchical + cross-era cell prior (epic-stable-era-windows-shrinkage, Units 1+2)
# ---------------------------------------------------------------------------


def _camp_hierarchy_inputs(
    mr: "MatchResults",
    labels: "list[str]",
    split_variant: str | None,
) -> "tuple[dict[str, float], dict[tuple[str, str], tuple[int, int]], dict[str, str]]":
    """Derive one window's hierarchy inputs (marginals, LCO parent cells, camp_of) from ``mr``.

    Everything is computed from the SAME ``MatchResults`` scan the cells themselves are drawn
    from (never a different/wider window) so the prior stays internally consistent with the data
    it anchors — using a full-corpus marginal to shrink a truncated post-era cell would silently
    reintroduce the stale-era mixing this epic exists to remove.

    ``marginals``: ``label -> shrunk marginal WR`` (``beta_binomial_shrink`` toward 0.5, strength
    ``SHRINK_STRENGTH``) for every label in ``labels`` PLUS — when ``split_variant`` is set — the
    parent archetype itself (``split_variant``, which never appears in ``labels`` once split,
    since its row is replaced by camp rows). The parent's raw wins/losses are the exact sum over
    every camp sibling's own ``ArchetypeRecord`` in ``mr.archetypes`` (a camp label always starts
    ``f"{split_variant} ["`` — this includes camps below the row-inclusion floor, since
    ``compute_match_results`` tallies every label regardless of inclusion): because a match
    between two DIFFERENT camps of the same split is a directed win/loss pair at the camp level
    but a mirror (+1 win AND +1 loss to the SAME label) at the unsplit parent level, summing wins
    and losses separately across all camp siblings reproduces the unsplit parent's marginal
    exactly, with zero extra DB scans.

    ``parent_cells_lco``: ``(camp_label, opponent) -> (lco_wins, lco_n)`` for every camp sibling
    of ``split_variant`` against every OTHER label in ``labels`` that is not itself a sibling camp
    (a camp-vs-camp pairing has no meaningful unsplit "parent cell" — it was a mirror pre-split —
    so it is simply absent here; ``_cell_prior`` falls back to the marginal chain for it). Parent
    totals vs ``opponent`` are the sum of every sibling's ``(sibling, opponent)`` tally in
    ``mr.matchups``; LCO = parent totals minus the camp's own tally. Asserted ``>= 0`` (never
    silently clamped) — a negative result would mean camp counts aren't a true partition of the
    parent's, a data-integrity bug worth crashing loudly on.

    ``camp_of``: ``label -> _base_archetype(label, split_variant)`` for every label in ``labels``.
    """
    marginals: dict[str, float] = {}
    for label in labels:
        rec = mr.archetypes.get(label)
        w, n = (rec.wins, rec.n) if rec is not None else (0, 0)
        marginals[label] = beta_binomial_shrink(w, n)

    camp_of = {label: _base_archetype(label, split_variant) for label in labels}

    parent_cells_lco: dict[tuple[str, str], tuple[int, int]] = {}
    if split_variant is not None:
        camp_prefix = f"{split_variant} ["
        siblings = sorted(a for a in mr.archetypes if a.startswith(camp_prefix))
        if siblings:
            p_wins = sum(mr.archetypes[s].wins for s in siblings)
            p_losses = sum(mr.archetypes[s].losses for s in siblings)
            marginals[split_variant] = beta_binomial_shrink(p_wins, p_wins + p_losses)

            sibling_set = set(siblings)
            for opponent in labels:
                if opponent in sibling_set:
                    continue  # camp-vs-camp: no unsplit parent-cell reference (see docstring)
                parent_wins = sum(
                    mr.matchups[(s, opponent)].wins
                    for s in siblings if (s, opponent) in mr.matchups
                )
                parent_n = sum(
                    mr.matchups[(s, opponent)].n
                    for s in siblings if (s, opponent) in mr.matchups
                )
                for camp in siblings:
                    tally = mr.matchups.get((camp, opponent))
                    camp_wins = tally.wins if tally is not None else 0
                    camp_n = tally.n if tally is not None else 0
                    lco_wins = parent_wins - camp_wins
                    lco_n = parent_n - camp_n
                    assert lco_wins >= 0 and lco_n >= 0, (
                        f"LCO subtraction went negative for {camp!r} vs {opponent!r}: "
                        f"parent=({parent_wins},{parent_n}) camp=({camp_wins},{camp_n}) — "
                        "camp counts are not a partition of the parent's"
                    )
                    parent_cells_lco[(camp, opponent)] = (lco_wins, lco_n)

    return marginals, parent_cells_lco, camp_of


def _cell_prior(
    subject: str,
    opponent: str,
    *,
    marginals: "dict[str, float]",
    parent_cells_lco: "dict[tuple[str, str], tuple[int, int]]",
    camp_of: "dict[str, str]",
) -> tuple[float, str]:
    """Resolve the hierarchical prior (mean, source label) for the directed cell ``subject`` vs
    ``opponent`` (epic-stable-era-windows-shrinkage's cell-prior chain).

    Camp cell (``camp_of[subject] != subject``) WITH a leave-camp-out parent reference: shrinks
    toward that LCO-parent cell (itself shrunk toward the parent archetype's own shrunk marginal)
    — source ``"parent cell (leave-camp-out)"``. Every other case (a plain, non-split archetype
    cell; or a camp cell with no LCO reference, e.g. a camp-vs-sibling-camp pairing) shrinks
    toward the subject's OWN shrunk marginal — source ``"marginal"``.

    Pure — no DB access; ``marginals``/``parent_cells_lco``/``camp_of`` are the precomputed
    outputs of ``_camp_hierarchy_inputs`` over one window's ``MatchResults``.
    """
    base = camp_of.get(subject, subject)
    if base != subject:
        lco = parent_cells_lco.get((subject, opponent))
        if lco is not None:
            lco_wins, lco_n = lco
            lco_shrunk = beta_binomial_shrink_to(lco_wins, lco_n, prior_mean=marginals[base])
            return lco_shrunk, "parent cell (leave-camp-out)"
    return marginals[subject], "marginal"


# ---------------------------------------------------------------------------
# Unit 5: Matrix builder
# ---------------------------------------------------------------------------


@dataclass
class MatchupMatrix:
    """Assembled matchup matrix: a complete rectangular grid of ``MatchupCell``s.

    ``cells`` is keyed ``(archetype_a, archetype_b)`` and includes mirror cells
    ``(a, a)`` for every included archetype.  The matrix is always rectangular
    (n=0 cells emitted for unobserved pairs) so downstream consumers can index
    without a missing-key guard.

    ``archetypes`` is the sorted list of included archetypes (those that meet
    the ``min_row_share`` threshold).  ``total_matches`` is the decisive-match
    count from ``coverage.decisive_matched``.  ``caveat`` is the mandatory
    bimodal-coverage provenance warning.
    """

    cells: dict[tuple[str, str], MatchupCell]
    provenance: str | None
    total_matches: int
    archetypes: list[str]
    caveat: str


def build_matrix(
    con,
    *,
    provenance: str | None = None,
    min_row_share: float = 0.02,
    since: str | None = None,
    until: str | None = None,
    split_variant: str | None = None,
) -> MatchupMatrix:
    """Build a ``MatchupMatrix`` from the DuckDB connection.

    ``since``/``until`` window the underlying matches by ``tournaments.date``
    (half-open ``[since, until)``); both ``None`` (default) = full corpus.

    ``split_variant`` (opt-in, default ``None``): passed through to
    ``compute_match_results`` so ``split_variant``'s decks are relabeled to their
    ``decks.variant`` camp on both sides of a pairing (see ``effective_label``).
    ``None`` is byte-identical to the pre-split behavior.

    Row inclusion: archetype ``a`` is included if its marginal involvement
    ``mr.archetypes[a].n / (2 * (decisive_matched + mirror_matches))`` ≥
    ``min_row_share``.  Each decisive match contributes to two marginal counts
    (winner + loser); each mirror match similarly credits the archetype with
    +1 win and +1 loss.  The denominator therefore includes mirror matches so
    the numerator and denominator both count mirror involvement.  Per the locked
    "count mirrors on both sides" decision, a mirror-only archetype is included
    via this honest mirror-aware ratio; ``total_matches`` is the decisive-match
    headline and may legitimately be 0 for such a degenerate corpus.

    When ``split_variant`` is set, its camp rows (labels starting with
    ``f"{split_variant} ["``) are force-included regardless of ``min_row_share`` —
    they are the entire point of the split — while every other row keeps the
    normal floor.

    For included archetypes every ordered pair ``(a, b)`` with ``a != b`` gets
    a cell (n=0 if the pair was never observed), and ``(a, a)`` gets a mirror
    cell whose ``n`` comes from the additive ``MatchResults.mirror_n`` field.

    Every non-mirror cell's ``prior_mean``/``prior_source`` come from the hierarchical cell-prior
    chain (epic-stable-era-windows-shrinkage): a split-variant camp cell shrinks toward its
    leave-camp-out parent cell (itself shrunk toward the parent's own shrunk marginal); every
    other cell shrinks toward the subject archetype's own shrunk marginal. See ``_cell_prior``/
    ``_camp_hierarchy_inputs``. (No cross-era prior here — that only applies in
    ``build_adaptive_matrix``, which alone carries per-entity horizon provenance.)
    """
    mr = compute_match_results(
        con, provenance=provenance, since=since, until=until, split_variant=split_variant,
    )
    total_matches = mr.coverage.decisive_matched

    # ── Row inclusion ────────────────────────────────────────────────────────
    # Denominator is 2*(decisive_matched + mirror_matches) because each match
    # (decisive or mirror) appears in two marginal records via archetypes[a].n.
    # Including mirror_matches keeps the ratio consistent with the numerator,
    # which already credits mirrors to .n via +1 win and +1 loss per mirror.
    _denom_base = total_matches + mr.coverage.mirror_matches
    denom = 2 * _denom_base if _denom_base > 0 else 1
    _force_prefix = f"{split_variant} [" if split_variant is not None else None
    included = sorted(
        arch
        for arch, rec in mr.archetypes.items()
        if rec.n / denom >= min_row_share
        or (_force_prefix is not None and arch.startswith(_force_prefix))
    )

    # ── Hierarchical cell prior (epic-stable-era-windows-shrinkage, Unit 1) ─────
    # Computed once from this same `mr` scan — see `_camp_hierarchy_inputs`.
    marginals, parent_cells_lco, camp_of = _camp_hierarchy_inputs(mr, included, split_variant)

    # ── Populate cells ───────────────────────────────────────────────────────
    cells: dict[tuple[str, str], MatchupCell] = {}

    for a in included:
        # Mirror cell
        cells[(a, a)] = build_mirror_cell(a, mr.mirror_n.get(a, 0))

        for b in included:
            if a == b:
                continue
            prior_mean, prior_source = _cell_prior(
                a, b, marginals=marginals, parent_cells_lco=parent_cells_lco, camp_of=camp_of,
            )
            tally = mr.matchups.get((a, b))
            if tally is not None:
                cells[(a, b)] = build_cell(
                    a, b, tally.wins, tally.n, prior_mean=prior_mean, prior_source=prior_source,
                )
            else:
                # Unobserved pair — emit n=0 cell to keep matrix rectangular
                cells[(a, b)] = build_cell(
                    a, b, 0, 0, prior_mean=prior_mean, prior_source=prior_source,
                )

    return MatchupMatrix(
        cells=cells,
        provenance=provenance,
        total_matches=total_matches,
        archetypes=included,
        caveat=_CAVEAT,
    )


# ---------------------------------------------------------------------------
# feature-multi-split-matrix Unit 2: pooling + multi-parent hierarchy + uniform builder
# ---------------------------------------------------------------------------


def _pool_opponent_tallies(
    mr: "MatchResults", camp_parent: "Mapping[str, str]",
) -> dict[tuple[str, str], tuple[int, int]]:
    """Pool a maximal camp×camp tally's OPPONENT side back to parent level.

    Returns ``(subject_label, parent_opponent) -> (wins, n)``.  ``subject_label`` keeps whatever
    granularity the scan produced (camp labels for split parents, plain labels otherwise);
    ``parent_opponent`` is ``camp_parent.get(b, b)`` — camps of a split parent Q collapse back
    onto Q.

    Exact by the camp-partition property: every deck of a split parent maps to exactly one camp
    (``NULL`` variant → ``"unlabeled"``), so summing a subject's tallies over Q's camps
    reproduces the tally that a ``split_variant=<subject's parent>``-only scan would have
    recorded against the unsplit Q.

    Pairs whose opponent pools to the SUBJECT's own parent are excluded — the ``(camp,
    own_parent)`` cell is deliberately absent (feature decision 2), matching per-parent
    behavior where the parent label does not exist at all.

    Pure — no DB access.
    """
    pooled: dict[tuple[str, str], tuple[int, int]] = {}
    for (a, b), tally in mr.matchups.items():
        parent_b = camp_parent.get(b, b)
        if camp_parent.get(a) == parent_b:
            continue
        wins, n = pooled.get((a, parent_b), (0, 0))
        pooled[(a, parent_b)] = (wins + tally.wins, n + tally.n)
    return pooled


def _multi_split_inclusion(
    mr: "MatchResults", min_row_share: float,
) -> tuple[list[str], list[str], list[str]]:
    """Row/column inclusion for one maximal camp-granularity scan → ``(subjects, opponents,
    parents)``.

    ``subjects``: every observed camp (force-included, the single-split semantics — a split
    parent's pooled row is replaced by its camp rows) plus every unsplit archetype clearing
    ``min_row_share``.  ``opponents``: the PLAIN matrix's row-inclusion set — parent-level
    labels only, with each split parent's record reconstructed as the sum over its camps.
    ``parents``: the split parents actually observed in this window.

    Inclusion matches the plain/per-parent builds exactly: a parent's reconstructed wins/losses
    equal its unsplit record (a cross-camp match is a directed camp-level win/loss pair but a
    parent-level mirror, i.e. +1 win AND +1 loss, so summing wins and losses separately is
    exact), and the ``2 * (decisive + mirror)`` denominator is relabel-invariant (a cross-camp
    pairing moves from the mirror counter to the decisive counter; the sum is fixed).
    """
    camp_parent = mr.camp_parent
    parent_records: dict[str, tuple[int, int]] = {}
    for label, rec in mr.archetypes.items():
        key = camp_parent.get(label, label)
        wins, losses = parent_records.get(key, (0, 0))
        parent_records[key] = (wins + rec.wins, losses + rec.losses)

    _denom_base = mr.coverage.decisive_matched + mr.coverage.mirror_matches
    denom = 2 * _denom_base if _denom_base > 0 else 1

    camps = sorted(a for a in mr.archetypes if a in camp_parent)
    parents = sorted({camp_parent[c] for c in camps})
    parent_set = set(parents)

    opponents = sorted(
        label
        for label, (wins, losses) in parent_records.items()
        if (wins + losses) / denom >= min_row_share
    )
    subjects = sorted(
        camps
        + [
            label
            for label, (wins, losses) in parent_records.items()
            if label not in parent_set and (wins + losses) / denom >= min_row_share
        ]
    )
    return subjects, opponents, parents


def _multi_hierarchy_inputs(
    mr: "MatchResults",
    subjects: list[str],
    opponents: list[str],
    camp_parent: "Mapping[str, str]",
    pooled: dict[tuple[str, str], tuple[int, int]],
) -> "tuple[dict[str, float], dict[tuple[str, str], tuple[int, int]], dict[str, str]]":
    """``_camp_hierarchy_inputs`` generalized to MANY split parents at once.

    Same three outputs, same semantics, consumed by the UNCHANGED ``_cell_prior``:

    ``marginals``: ``label -> shrunk marginal WR`` for every subject, plus every observed split
    parent, whose raw wins/losses are the exact sum over its camp siblings' own
    ``ArchetypeRecord``s (see ``_camp_hierarchy_inputs`` for why summing wins and losses
    separately is exact).  Sibling sets come from the explicit ``camp_parent`` map, never prefix
    parsing — the registry contains both ``Painter`` and ``Blue Painter``.

    ``parent_cells_lco``: ``(camp, parent_opponent) -> (lco_wins, lco_n)``, the parent's pooled
    totals vs that opponent minus the camp's own pooled tally, for every camp × every opponent
    that is not the camp's own parent.  Asserted ``>= 0`` (never clamped) — a negative result
    means the camp tallies are not a partition of the parent's, a data-integrity bug.

    ``camp_of``: ``subject -> parent-or-self``.

    Pure — no DB access; ``pooled`` is ``_pool_opponent_tallies``'s output over the SAME scan.
    """
    marginals: dict[str, float] = {}
    for label in subjects:
        rec = mr.archetypes.get(label)
        w, n = (rec.wins, rec.n) if rec is not None else (0, 0)
        marginals[label] = beta_binomial_shrink(w, n)

    camp_of = {label: camp_parent.get(label, label) for label in subjects}

    siblings_by_parent: dict[str, list[str]] = {}
    for label in sorted(mr.archetypes):
        parent = camp_parent.get(label)
        if parent is not None:
            siblings_by_parent.setdefault(parent, []).append(label)

    parent_cells_lco: dict[tuple[str, str], tuple[int, int]] = {}
    for parent, siblings in siblings_by_parent.items():
        p_wins = sum(mr.archetypes[s].wins for s in siblings)
        p_losses = sum(mr.archetypes[s].losses for s in siblings)
        marginals[parent] = beta_binomial_shrink(p_wins, p_wins + p_losses)

        for opponent in opponents:
            if opponent == parent:
                continue  # own-parent column is absent by design — no reference cell to build
            parent_wins = sum(pooled.get((s, opponent), (0, 0))[0] for s in siblings)
            parent_n = sum(pooled.get((s, opponent), (0, 0))[1] for s in siblings)
            for camp in siblings:
                camp_wins, camp_n = pooled.get((camp, opponent), (0, 0))
                lco_wins = parent_wins - camp_wins
                lco_n = parent_n - camp_n
                assert lco_wins >= 0 and lco_n >= 0, (
                    f"LCO subtraction went negative for {camp!r} vs {opponent!r}: "
                    f"parent=({parent_wins},{parent_n}) camp=({camp_wins},{camp_n}) — "
                    "camp counts are not a partition of the parent's"
                )
                parent_cells_lco[(camp, opponent)] = (lco_wins, lco_n)

    return marginals, parent_cells_lco, camp_of


@dataclass
class MultiSplitMatrix:
    """Every split parent's camps and every unsplit archetype in ONE rectangular matrix.

    ``cells`` is keyed ``(subject, parent_opponent)`` plus ``(subject, subject)`` mirrors.  The
    matrix is RECTANGULAR, not square: ``subjects`` are all observed camps (force-included) +
    the included unsplit archetypes; ``opponents`` are parent-level labels only (the plain
    matrix's row-inclusion set).  ``(camp, own_parent)`` is deliberately ABSENT — the per-parent
    ``split_variant`` build has no parent label either, so the pair has never had a cell.

    ``camp_parent`` maps each camp subject back to its parent; ``parents`` are the split parents
    actually observed.  ``total_matches`` is the decisive-match count at CAMP granularity — it
    differs from the plain matrix's (a cross-camp pairing counts as decisive here and as a
    mirror there); the sum ``decisive + mirror`` is what stays invariant.

    Every camp cell is field-for-field identical to ``build_matrix(split_variant=parent)``'s and
    every unsplit-subject cell to the plain ``build_matrix``'s (parity test:
    tests/test_matchup_multi_split.py).
    """

    cells: dict[tuple[str, str], MatchupCell]
    subjects: list[str]
    opponents: list[str]
    camp_parent: dict[str, str]
    parents: list[str]
    provenance: str | None
    total_matches: int
    caveat: str

    def ranking_view(self) -> MatchupMatrix:
        """A ``MatchupMatrix`` view for the shared-field MC rankers (``rank_decks`` /
        ``positioning_score``), which only ever do ``cells.get(...)`` plus field iteration.

        ``archetypes`` is ``sorted(subjects | opponents)`` and ``cells`` is THIS object's dict —
        so the view is NOT square and has no cell for ``(camp, own_parent)``.  Never feed it to
        a square-matrix consumer (``best_deck_vs_best_call``, the matrix printers): they index
        ``archetypes × archetypes`` and would KeyError or silently mis-render.
        """
        return MatchupMatrix(
            cells=self.cells,
            provenance=self.provenance,
            total_matches=self.total_matches,
            archetypes=sorted(set(self.subjects) | set(self.opponents)),
            caveat=self.caveat,
        )


def build_multi_split_matrix(
    con,
    *,
    parents: "Collection[str]",
    provenance: str | None = None,
    min_row_share: float = 0.02,
    since: str | None = None,
    until: str | None = None,
) -> MultiSplitMatrix:
    """Build a ``MultiSplitMatrix`` over a uniform window — every parent split in ONE scan.

    One ``compute_match_results(split_variants=parents)` call produces the maximal camp×camp
    tally; the opponent side is then pooled back to parent level (``_pool_opponent_tallies``)
    and the hierarchy inputs are reconstructed from camp sums (``_multi_hierarchy_inputs``) and
    fed to the UNCHANGED ``_cell_prior``.  The result is numerically identical to running
    ``build_matrix(split_variant=P)`` once per parent and the plain ``build_matrix`` for the
    unsplit rows — this is a batching win, not a methodology change.

    ``since``/``until`` window by ``tournaments.date`` (half-open) exactly as ``build_matrix``.
    Parents absent from the corpus (or from this window) are dropped gracefully — they simply
    contribute no camps, mirroring the single-split no-op precedent.  An empty ``parents`` is
    the plain rectangular matrix.

    No cross-era prior here — that belongs to the adaptive builder, which alone carries
    per-entity horizon provenance.
    """
    mr = compute_match_results(
        con, provenance=provenance, since=since, until=until, split_variants=parents,
    )
    subjects, opponents, observed_parents = _multi_split_inclusion(mr, min_row_share)
    pooled = _pool_opponent_tallies(mr, mr.camp_parent)
    marginals, parent_cells_lco, camp_of = _multi_hierarchy_inputs(
        mr, subjects, opponents, mr.camp_parent, pooled,
    )

    cells: dict[tuple[str, str], MatchupCell] = {}
    for subject in subjects:
        cells[(subject, subject)] = build_mirror_cell(subject, mr.mirror_n.get(subject, 0))
        own_parent = mr.camp_parent.get(subject)
        for opponent in opponents:
            if opponent == subject or opponent == own_parent:
                continue
            prior_mean, prior_source = _cell_prior(
                subject, opponent, marginals=marginals,
                parent_cells_lco=parent_cells_lco, camp_of=camp_of,
            )
            wins, n = pooled.get((subject, opponent), (0, 0))
            cells[(subject, opponent)] = build_cell(
                subject, opponent, wins, n, prior_mean=prior_mean, prior_source=prior_source,
            )

    return MultiSplitMatrix(
        cells=cells,
        subjects=subjects,
        opponents=opponents,
        camp_parent=dict(mr.camp_parent),
        parents=observed_parents,
        provenance=provenance,
        total_matches=mr.coverage.decisive_matched,
        caveat=_CAVEAT,
    )


def lookup_head_to_head(
    matrix: MatchupMatrix,
    archetype_a: str,
    archetype_b: str,
) -> MatchupCell | None:
    """Return the directed ``MatchupCell`` for archetype_a vs archetype_b.

    Returns ``None`` when either archetype is not included in the matrix (below
    the row-inclusion threshold).  The returned cell may have ``display=False``
    when ``n < DISPLAY_GATE_N`` (speculative data is present-and-honest, not
    hidden).

    Pure function over ``MatchupMatrix`` — no DB access.
    """
    if archetype_a not in matrix.archetypes or archetype_b not in matrix.archetypes:
        return None
    return matrix.cells.get((archetype_a, archetype_b))


@dataclass
class AdaptiveMatrix:
    """A matchup matrix whose cells are sourced over per-pair ban-aware windows.

    ``matrix`` is a normal ``MatchupMatrix`` (rectangular, same row set as the full-corpus
    ``min_row_share`` inclusion). ``valid_since[a]`` is each archetype's resolved horizon (ISO
    date or ``None`` = full history) — since epic-stable-era-windows-consumption, this is the
    per-entity ``stable_since`` horizon (era-aware, honest-degrading to the pre-epic ban-only
    ``archetype_valid_since`` when there is no era data) rather than a ban-only horizon alone.
    ``cell_windows[(a, b)]`` records the ``since`` actually used for that ordered cell —
    ``max(valid_since[a], valid_since[b])`` — for auditability. ``horizon_meta[a]`` carries the
    full ``EraHorizon`` (source/trigger/alarm) behind each ``valid_since[a]`` value — defaults to
    ``{}`` so pre-epic direct-construction call sites (tests building an ``AdaptiveMatrix`` by
    hand) stay valid without updating. ``audit_preamble`` carries the whole-path degrade line
    (``entity_eras`` missing/empty entirely) when the default era-aware path detected it — empty
    when ``horizons`` was supplied explicitly, or when era data exists (even if incomplete for
    some individual entities — that degrades silently per-entity, not as a whole-path banner).
    """

    matrix: MatchupMatrix
    valid_since: dict[str, str | None]
    cell_windows: dict[tuple[str, str], str | None]
    horizon_meta: "dict[str, EraHorizon]" = field(default_factory=dict)
    audit_preamble: tuple[str, ...] = ()


def _base_archetype(label: str, split_variant: str | None) -> str:
    """Strip a variant-camp suffix so a camp label resolves to its parent's ban-affectedness horizon.

    ``archetype_valid_since`` only knows plain ``decks.archetype`` values, never the synthetic
    ``f"{split_variant} [{variant}]"`` camp labels ``effective_label`` produces. A camp label always
    starts with ``f"{split_variant} ["`` (by construction), so stripping back to ``split_variant``
    lets the adaptive matrix fall back to the parent archetype's horizon for every camp. Non-camp
    labels (including everything when ``split_variant`` is ``None``) pass through unchanged.
    """
    if split_variant is not None and label.startswith(f"{split_variant} ["):
        return split_variant
    return label


def build_adaptive_matrix(
    con,
    *,
    provenance: str | None = None,
    min_row_share: float = 0.02,
    affect_threshold: float = 0.25,
    split_variant: str | None = None,
    horizons: dict[str, str | None] | None = None,
) -> AdaptiveMatrix:
    """Build a matchup matrix where each pairwise cell pools data over the maximally-valid window.

    Each archetype has a ``valid_since`` horizon (``None`` = full history). By default (``horizons
    is None``) this is resolved per-entity via ``analytics.eras.consume.era_horizons`` — the
    epic-stable-era-windows-consumption default: an entity's own persisted ``stable_since``
    (exact -> parent camp -> ban-only ``archetype_valid_since`` fallback when there is no era
    data at all). A cell ``(a, b)`` pools matches back to ``max(valid_since[a], valid_since[b])``,
    so unaffected×undisturbed cells keep full history (established tier) while disturbed cells
    truncate honestly. Row inclusion + marginals + mirror counts come from the full-corpus scan
    (stable); only per-cell data sourcing is windowed. Cost: one ``compute_match_results`` per
    distinct horizon value (≤ #distinct dates), not per cell.

    ``horizons`` (advanced/testing hook, default ``None``): an explicit ``{label: since}`` map
    that BYPASSES ``era_horizons`` entirely and is used verbatim as ``valid_since`` — this is how
    a caller pins the exact pre-epic ``archetype_valid_since``-only behavior (passing its output
    directly reproduces the byte-identical old numbers, since the default era-aware path's own
    ban-only fallback branch calls the very same ``archetype_valid_since`` with the same
    arguments when there is no era data). ``horizon_meta`` is empty when ``horizons`` is supplied
    explicitly (no per-entity source/trigger/alarm metadata to report).

    ``split_variant`` (opt-in, default ``None``): passed through to every
    ``compute_match_results`` call so ``split_variant``'s camp rows are force-included (see
    ``build_matrix``) and its labels use ``f"{split_variant} [{variant}]"``. Since
    ``archetype_valid_since`` cannot look up a synthetic camp label, each camp's ban-only horizon
    is resolved via its parent archetype (``_base_archetype``) before the lookup, then mapped
    back — every camp of the same parent shares that parent's ban-only ``valid_since`` (era-aware
    camps, when a camp clears its OWN detection floor, get their own horizon instead — see
    ``era_horizons``). ``None`` is byte-identical to the pre-split behavior (``_base_archetype``
    is then the identity function).

    Every non-mirror cell's ``prior_mean``/``prior_source`` (epic-stable-era-windows-shrinkage)
    come from the hierarchical chain (``_cell_prior`` over that cell's OWN window bucket — see
    ``_camp_hierarchy_inputs``), further overridden by the cross-era prior when a thin (``n<100``)
    cell's window was truncated at an era (not ban-only) boundary — see ``_cross_era_prior``.
    """
    # 1. Full-corpus scan → row inclusion (min_row_share) + marginals + mirror_n (stable basis).
    full = compute_match_results(con, provenance=provenance, split_variant=split_variant)
    total_matches = full.coverage.decisive_matched
    _denom_base = total_matches + full.coverage.mirror_matches
    denom = 2 * _denom_base if _denom_base > 0 else 1
    _force_prefix = f"{split_variant} [" if split_variant is not None else None
    included = sorted(
        a
        for a, rec in full.archetypes.items()
        if rec.n / denom >= min_row_share
        or (_force_prefix is not None and a.startswith(_force_prefix))
    )

    # 2. Horizon per included archetype: explicit override, or the era-aware adapter default.
    horizon_meta: "dict[str, EraHorizon]" = {}
    audit_preamble: tuple[str, ...] = ()
    if horizons is not None:
        valid_since = {a: horizons.get(a) for a in included}
    else:
        from legacy_engine.analytics.eras.consume import era_horizons

        horizon_meta, audit_preamble = era_horizons(
            con, included, provenance=provenance, split_variant=split_variant,
            affect_threshold=affect_threshold,
        )
        valid_since = {a: horizon_meta[a].since for a in included}

    # 3. One scan per distinct valid_since (None reuses the full-corpus scan). s_ab is always one of
    #    these values (max of two members), so this set covers every cell window.
    mr_by_since = {None: full}
    for s in set(valid_since.values()):
        if s is not None and s not in mr_by_since:
            mr_by_since[s] = compute_match_results(
                con, provenance=provenance, since=s, split_variant=split_variant,
            )

    # 3b. Hierarchical cell prior inputs (Unit 1), one per distinct since bucket — reuses the
    # scans above (zero extra compute_match_results calls). Each bucket's marginals/LCO parent
    # cells are derived from ITS OWN windowed MatchResults (see _camp_hierarchy_inputs), so a
    # truncated post-boundary cell is never anchored to a wider/stale-era population.
    hierarchy_by_since = {
        s: _camp_hierarchy_inputs(mr, included, split_variant) for s, mr in mr_by_since.items()
    }

    # 3c. Cross-era prior (Unit 2). Lazily populated per distinct PRE-boundary date — computed
    # only for boundaries actually used below by a thin (n<100) era-sourced cell, never for every
    # date up front. `pre_mr_cache`/`pre_hierarchy_cache` batch by boundary date so a boundary
    # shared by many cells costs exactly one extra `compute_match_results` + one hierarchy-inputs
    # pass, never one per cell.
    pre_mr_cache: "dict[str, MatchResults]" = {}
    pre_hierarchy_cache: dict = {}

    def _era_sourced_boundary(a: str, b: str, s_ab: str) -> bool:
        """True when `s_ab` is the horizon of an era/era-parent-sourced entity (not ban-only).

        `s_ab` is `max(valid_since[a], valid_since[b])`; the entity that contributed it (one or
        both, when both sides truncate to the same date) determines whether this is an era
        boundary or merely a ban-only one. Ban-only-truncated cells never get a cross-era prior
        (there is no "pre-disturbance" era to compute — the ban regime IS the whole known history
        for that horizon source).
        """
        return any(
            valid_since[x] == s_ab and horizon_meta.get(x) is not None
            and horizon_meta[x].source in ("era", "era-parent")
            for x in (a, b)
        )

    def _cross_era_prior(a: str, b: str, boundary: str) -> tuple[float, str]:
        """The pre-boundary hierarchical value for (a, b) — the cross-era prior mean + label.

        Computes (once per distinct `boundary`, cached) the SAME directed cell over the
        PRE-boundary window `[None, boundary)`, then shrinks it per the normal hierarchy chain
        using PRE-boundary marginals/LCO cells (never the post-boundary or full-corpus ones —
        the whole point is an honest "what this matchup looked like before the disturbance").
        """
        if boundary not in pre_mr_cache:
            pre_mr_cache[boundary] = compute_match_results(
                con, provenance=provenance, until=boundary, split_variant=split_variant,
            )
            pre_hierarchy_cache[boundary] = _camp_hierarchy_inputs(
                pre_mr_cache[boundary], included, split_variant,
            )
        pre_mr = pre_mr_cache[boundary]
        pre_marginals, pre_lco, pre_camp_of = pre_hierarchy_cache[boundary]
        pre_tally = pre_mr.matchups.get((a, b))
        pre_wins, pre_n = (pre_tally.wins, pre_tally.n) if pre_tally is not None else (0, 0)
        pre_prior_mean, pre_source = _cell_prior(
            a, b, marginals=pre_marginals, parent_cells_lco=pre_lco, camp_of=pre_camp_of,
        )
        cross_era_mean = beta_binomial_shrink_to(pre_wins, pre_n, prior_mean=pre_prior_mean)
        label = f"pre-disturbance value (window < {boundary}); hierarchy: {pre_source}"
        return cross_era_mean, label

    # 4. Assemble: each cell from the scan at max(valid_since[a], valid_since[b]).
    cells: dict[tuple[str, str], MatchupCell] = {}
    cell_windows: dict[tuple[str, str], str | None] = {}
    for a in included:
        s_a = valid_since[a]
        cells[(a, a)] = build_mirror_cell(a, mr_by_since[s_a].mirror_n.get(a, 0))
        cell_windows[(a, a)] = s_a
        for b in included:
            if a == b:
                continue
            s_ab = max(valid_since[a] or "", valid_since[b] or "") or None
            mr_ab = mr_by_since[s_ab]
            marginals, parent_cells_lco, camp_of = hierarchy_by_since[s_ab]
            tally = mr_ab.matchups.get((a, b))
            wins, n = (tally.wins, tally.n) if tally is not None else (0, 0)
            prior_mean, prior_source = _cell_prior(
                a, b, marginals=marginals, parent_cells_lco=parent_cells_lco, camp_of=camp_of,
            )
            # Cross-era prior (Unit 2): a thin (n<100) cell truncated at an era (not ban-only)
            # boundary shrinks toward its own pre-disturbance value instead of the hierarchy mean
            # — the more specific, more honest prior for a young post-boundary era. Wins over the
            # hierarchy prior when both apply (per the locked design decision); the label carries
            # both.
            if s_ab is not None and n < 100 and _era_sourced_boundary(a, b, s_ab):
                prior_mean, prior_source = _cross_era_prior(a, b, s_ab)
            cells[(a, b)] = build_cell(
                a, b, wins, n, prior_mean=prior_mean, prior_source=prior_source,
            )
            cell_windows[(a, b)] = s_ab

    matrix = MatchupMatrix(
        cells=cells,
        provenance=provenance,
        total_matches=total_matches,
        archetypes=included,
        caveat=_CAVEAT,
    )
    return AdaptiveMatrix(
        matrix=matrix, valid_since=valid_since, cell_windows=cell_windows,
        horizon_meta=horizon_meta, audit_preamble=audit_preamble,
    )


# ---------------------------------------------------------------------------
# feature-multi-split-matrix Unit 3: era-windowed multi-split builder
# ---------------------------------------------------------------------------


@dataclass
class AdaptiveMultiSplitMatrix:
    """``AdaptiveMatrix``'s shape for the rectangular multi-split matrix.

    ``multi`` is the assembled ``MultiSplitMatrix`` (camp subjects + unsplit subjects × parent-level
    opponents). ``valid_since`` covers subjects AND opponents — an opponent that is a split parent
    carries the PARENT-level horizon, which is exactly what a per-parent
    ``build_adaptive_matrix(split_variant=P)`` build resolves for that same unsplit label.
    ``cell_windows[(subject, opponent)]`` is the ``since`` actually used for that emitted cell
    (``max`` of the two members' horizons); ``horizon_meta``/``audit_preamble`` carry the same
    per-entity ``EraHorizon`` provenance and whole-path degrade line ``AdaptiveMatrix`` does.

    Superarchetype overlay (epic-superarchetype-layer-chain; ALL empty unless the build was passed
    a non-empty registry — the byte-identical default). Three DISTINCT cell kinds, never blended
    into ``multi.cells``:

    - ``cluster_cells[(subject, cluster_id)]`` — the display pool "subject vs that strategy
      family" (opponent's own matches INCLUDED, refusals first-class, full gate/freshness
      provenance on the ``PooledCell``);
    - ``imputed_cells[(subject, opponent)]`` — licensed family imputation attempts for
      sub-display cells (grants AND refusals; license/veto/window provenance on the
      ``ImputedCell``);
    - ``ladder[(subject, opponent)]`` — the resolved display fallback (measured -> imputed ->
      pooled -> none) for every sub-display cell, every finer refusal named. Rendering is
      -best-call-fallback's job; this is the data.
    """

    multi: MultiSplitMatrix
    valid_since: dict[str, str | None]
    cell_windows: dict[tuple[str, str], str | None]
    horizon_meta: "dict[str, EraHorizon]" = field(default_factory=dict)
    audit_preamble: tuple[str, ...] = ()
    cluster_cells: "dict[tuple[str, str], PooledCell]" = field(default_factory=dict)
    imputed_cells: "dict[tuple[str, str], ImputedCell]" = field(default_factory=dict)
    ladder: "dict[tuple[str, str], LadderEntry]" = field(default_factory=dict)


def build_multi_split_adaptive(
    con,
    *,
    parents: "Collection[str]",
    provenance: str | None = None,
    min_row_share: float = 0.02,
    affect_threshold: float = 0.25,
    horizons: dict[str, str | None] | None = None,
    superarchetypes: "SuperarchetypeRegistry | None" = None,
    apply_superarchetype_priors: bool = True,
) -> AdaptiveMultiSplitMatrix:
    """``build_adaptive_matrix`` for every split parent at once — one scan per distinct horizon.

    Same skeleton as ``build_adaptive_matrix``: a full maximal (camp×camp) scan fixes row/column
    inclusion, each entity resolves a ``valid_since`` horizon, one ``compute_match_results`` runs
    per DISTINCT horizon (never per cell, never per parent), each cell is sourced from the scan at
    ``max(valid_since[subject], valid_since[opponent])``, and a thin (``n<100``) cell truncated at
    an ERA (not ban-only) boundary shrinks toward its own pre-disturbance value via a lazily-cached
    pre-boundary scan. The only difference is granularity: every scan is pooled back to parent-level
    opponents (``_pool_opponent_tallies``) and its hierarchy inputs are reconstructed from camp sums
    for many parents at once (``_multi_hierarchy_inputs``), feeding the UNCHANGED ``_cell_prior``.

    That makes the result a batching win, not a methodology change: every camp cell — value,
    ``cell_windows`` entry and cross-era ``prior_source`` label included — is identical to
    ``build_adaptive_matrix(split_variant=<that camp's parent>)``'s, and every unsplit-subject cell
    identical to the plain ``build_adaptive_matrix``'s (parity test:
    tests/test_matchup_multi_split.py::TestAdaptiveParity). The scan count is the number of
    DISTINCT horizons across all parents, not parents × horizons.

    Camp horizons resolve exact ``entity_eras`` row -> parent row -> ban-only through the explicit
    ``camp_parent`` map (never prefix parsing — the registry holds both ``Painter`` and ``Blue
    Painter``). ``horizons`` (advanced/testing hook, default ``None``) bypasses ``era_horizons``
    entirely and is used verbatim, exactly as in ``build_adaptive_matrix``; ``horizon_meta`` is then
    empty, which also means no cell can take the cross-era prior (no era-sourced boundary to detect).

    ``superarchetypes`` (opt-in, default ``None`` — epic-superarchetype-layer-chain): a
    ``SuperarchetypeRegistry`` READ by the caller (``read_superarchetype_members``; never computed
    here — epic decision 3). ``None`` or an empty registry is BYTE-IDENTICAL to the pre-layer
    build (opt-in-analytics-overlay + gated-additive; pinned by
    tests/test_matchup_superarchetype_golden.py). With a non-empty registry:

    - the prior chain gains the superarchetype rungs on the marginal-fallthrough branch —
      ``camp -> LCO parent' -> superarchetype cell (leave-opponent-out) -> cluster × cluster
      (leave-S-out, leave-O-out; prior only) -> marginal' -> 0.5`` — with ``prior_source`` naming
      the rung and the estimator's evidence-gated strength anchoring the shrink; a rung that
      fails its concentration/heterogeneity gate is skipped (never blended). The cross-era prior
      keeps precedence on thin era-truncated cells (``chain.FAMILY_FIRST_KINDS`` is the measured
      young-era exception set — empty on today's corpus, see the LOO harness);
    - the result carries the ``cluster_cells``/``imputed_cells``/``ladder`` overlay maps (see
      ``AdaptiveMultiSplitMatrix``) and the registry-provenance ``//`` lines in
      ``audit_preamble`` (window mismatch is loud, never silent).

    ``apply_superarchetype_priors=False`` is the typed overlay-only consumer seam: the registry
    still produces all three display maps and audit lines in the SAME pass, while ``multi.cells``
    retains the baseline hierarchy exactly. It exists for surfaces such as the best-call page
    whose explicit contract is ledger-only family leans with byte-identical headline inputs.

    Member tallies for every pool are drawn from THIS build's pairwise-windowed tally buckets
    (era addendum #2: a member contributes only from its current stable era), which is why the
    layer exists on the adaptive builder only — a uniform window cannot honor that rule.
    """
    # 1. Full maximal scan → subjects/opponents/parents inclusion (stable basis, as in the plain
    #    adaptive builder: only per-cell data sourcing is windowed).
    full = compute_match_results(con, provenance=provenance, split_variants=parents)
    subjects, opponents, observed_parents = _multi_split_inclusion(full, min_row_share)
    camp_parent = dict(full.camp_parent)
    entities = sorted(set(subjects) | set(opponents))

    # 2. Horizon per entity: explicit override, or the era-aware adapter default.
    horizon_meta: "dict[str, EraHorizon]" = {}
    audit_preamble: tuple[str, ...] = ()
    if horizons is not None:
        valid_since = {a: horizons.get(a) for a in entities}
    else:
        from legacy_engine.analytics.eras.consume import era_horizons

        horizon_meta, audit_preamble = era_horizons(
            con, entities, provenance=provenance, camp_parent=camp_parent,
            affect_threshold=affect_threshold,
        )
        valid_since = {a: horizon_meta[a].since for a in entities}

    # 3. One maximal scan per distinct valid_since (None reuses the full scan) — s_ab is always one
    #    of these values, so this set covers every cell window.
    mr_by_since = {None: full}
    for s in set(valid_since.values()):
        if s is not None and s not in mr_by_since:
            mr_by_since[s] = compute_match_results(
                con, provenance=provenance, since=s, split_variants=parents,
            )

    # 3b. Per-window pooling + hierarchy inputs, derived from each window's OWN scan (never a wider
    # one — the whole point of era windows). Each window pools with ITS OWN camp_parent map: a camp
    # absent from the window is absent from that map, which makes `_cell_prior` fall back to the
    # camp's marginal exactly as `_camp_hierarchy_inputs` does when the camp has no sibling tally.
    pooled_by_since = {
        s: _pool_opponent_tallies(mr, mr.camp_parent) for s, mr in mr_by_since.items()
    }
    hierarchy_by_since = {
        s: _multi_hierarchy_inputs(mr, subjects, opponents, mr.camp_parent, pooled_by_since[s])
        for s, mr in mr_by_since.items()
    }

    # 3b'. Superarchetype layer setup (opt-in; view is None on the byte-identical default path).
    # Everything below the view check reads the SAME pairwise-windowed buckets the cells use.
    view = None
    sa_audit: tuple[str, ...] = ()
    regime_start: str | None = None
    camps_of: dict[str, list[str]] = {}
    sa_licenses: dict = {}
    if superarchetypes is not None:
        from legacy_engine.analytics.superarchetype import chain as _chain
        from legacy_engine.analytics.superarchetype.aggregate import (
            imputation_license,
            impute_cell,
        )
        from legacy_engine.analytics.trends import resolve_regime

        view = _chain.cluster_view(superarchetypes)
        if view is None:
            sa_audit = ("// superarchetype: registry empty — layer off",)
        else:
            regime_start, _regime_until = resolve_regime("current")
            sa_audit = _chain.registry_audit_lines(superarchetypes, regime_start=regime_start)
            for camp, parent in camp_parent.items():
                camps_of.setdefault(parent, []).append(camp)
            # Freshness shares read the regime-start bucket for pre-regime windows — scan it
            # once if no entity horizon already produced it.
            if regime_start is not None and regime_start not in pooled_by_since:
                regime_mr = compute_match_results(
                    con, provenance=provenance, since=regime_start, split_variants=parents,
                )
                pooled_by_since[regime_start] = _pool_opponent_tallies(
                    regime_mr, regime_mr.camp_parent,
                )
            sa_licenses = {
                cluster_id: imputation_license(cluster_id, _chain.family_profile(
                    cluster_id, view,
                    opponents=opponents, pooled_by_since=pooled_by_since,
                    valid_since=valid_since, camps_of=camps_of,
                ))
                for cluster_id in view.cluster_ids
            }

    def _impute_for(subject: str, opponent: str):
        """(ImputedCell | None, drawn tallies, skip reason | None) for one sub-display cell."""
        base = _chain.subject_base(subject, camp_parent)
        gs_id = view.cluster_of.get(base)
        if gs_id is None:
            return None, (), None  # resolve_ladder's default reason covers the no-cluster case
        if view.cluster_of.get(opponent) == gs_id:
            return None, (), (
                f"imputation not attempted: {opponent} is inside {subject}'s own family {gs_id}"
            )
        drawn = _chain.draw_family_tallies(
            base, gs_id, opponent, view,
            pooled_by_since=pooled_by_since, valid_since=valid_since, camps_of=camps_of,
            regime_start=regime_start,
        )
        cell = impute_cell(
            base, opponent, sa_licenses[gs_id], drawn.tallies,
            window_note=drawn.window_note, current_regime_share=drawn.current_regime_share,
        )
        return cell, drawn.tallies, None

    # 3c. Cross-era prior, lazily populated per distinct PRE-boundary date. One extra maximal scan
    # per boundary serves EVERY parent's cells at that boundary — the per-parent builds pay one
    # such scan each.
    pre_pooled_cache: dict = {}
    pre_hierarchy_cache: dict = {}

    def _era_sourced_boundary(a: str, b: str, s_ab: str) -> bool:
        """True when ``s_ab`` is the horizon of an era/era-parent-sourced entity (not ban-only).

        Verbatim from ``build_adaptive_matrix`` — a ban-only-truncated cell never gets a cross-era
        prior, because the ban regime IS the whole known history for that horizon source.
        """
        return any(
            valid_since[x] == s_ab and horizon_meta.get(x) is not None
            and horizon_meta[x].source in ("era", "era-parent")
            for x in (a, b)
        )

    def _subject_boundary_kind(subject: str, s_ab: str) -> str | None:
        """The winning-boundary attribution kind when the SUBJECT's own era set this cell's
        window — the young-era ladder-order rule keys on the subject's reset, never the
        opponent's (era addendum #2 rule 5)."""
        hm = horizon_meta.get(subject)
        if hm is not None and valid_since[subject] == s_ab and hm.source in ("era", "era-parent"):
            return hm.attribution_kind
        return None

    def _cross_era_prior(a: str, b: str, boundary: str) -> tuple[float, str]:
        """The pooled pre-boundary hierarchical value for (a, b) — cross-era prior mean + label."""
        if boundary not in pre_pooled_cache:
            pre_mr = compute_match_results(
                con, provenance=provenance, until=boundary, split_variants=parents,
            )
            pre_pooled_cache[boundary] = _pool_opponent_tallies(pre_mr, pre_mr.camp_parent)
            pre_hierarchy_cache[boundary] = _multi_hierarchy_inputs(
                pre_mr, subjects, opponents, pre_mr.camp_parent, pre_pooled_cache[boundary],
            )
        pre_marginals, pre_lco, pre_camp_of = pre_hierarchy_cache[boundary]
        pre_wins, pre_n = pre_pooled_cache[boundary].get((a, b), (0, 0))
        pre_prior_mean, pre_source = _cell_prior(
            a, b, marginals=pre_marginals, parent_cells_lco=pre_lco, camp_of=pre_camp_of,
        )
        cross_era_mean = beta_binomial_shrink_to(pre_wins, pre_n, prior_mean=pre_prior_mean)
        label = f"pre-disturbance value (window < {boundary}); hierarchy: {pre_source}"
        return cross_era_mean, label

    # 4. Assemble: each cell from the window at max(valid_since[subject], valid_since[opponent]).
    cells: dict[tuple[str, str], MatchupCell] = {}
    cell_windows: dict[tuple[str, str], str | None] = {}
    for subject in subjects:
        s_a = valid_since[subject]
        cells[(subject, subject)] = build_mirror_cell(
            subject, mr_by_since[s_a].mirror_n.get(subject, 0),
        )
        cell_windows[(subject, subject)] = s_a
        own_parent = camp_parent.get(subject)
        for opponent in opponents:
            if opponent == subject or opponent == own_parent:
                continue
            s_ab = max(valid_since[subject] or "", valid_since[opponent] or "") or None
            marginals, parent_cells_lco, camp_of = hierarchy_by_since[s_ab]
            wins, n = pooled_by_since[s_ab].get((subject, opponent), (0, 0))
            prior_mean, prior_source = _cell_prior(
                subject, opponent, marginals=marginals,
                parent_cells_lco=parent_cells_lco, camp_of=camp_of,
            )
            prior_strength_value = SHRINK_STRENGTH
            # Superarchetype rungs (epic-superarchetype-layer-chain) engage on the marginal-
            # fallthrough branch only — a camp cell with an LCO parent reference keeps the finer
            # existing anchor (the fixed chain order as anchor precedence; feature design
            # decision 2). Gate-failing rungs are skipped inside `rung_prior`.
            if apply_superarchetype_priors and view is not None and prior_source == "marginal":
                rung = _chain.rung_prior(
                    subject, opponent, view,
                    pooled_by_since=pooled_by_since, valid_since=valid_since,
                    camp_parent=camp_parent, camps_of=camps_of, regime_start=regime_start,
                )
                if rung is not None:
                    prior_mean, prior_source = rung.mean, rung.source
                    prior_strength_value = rung.strength
            if s_ab is not None and n < 100 and _era_sourced_boundary(subject, opponent, s_ab):
                # The cross-era anchor keeps precedence (epic decision) — except for a young era
                # whose attribution kind measurably favors family-current imputation
                # (chain.FAMILY_FIRST_KINDS; EMPTY on today's corpus per the LOO harness, so the
                # anchor wins everywhere until a re-measure says otherwise).
                family_first = False
                if apply_superarchetype_priors and view is not None:
                    kind = _subject_boundary_kind(subject, s_ab)
                    if kind is not None and kind in _chain.FAMILY_FIRST_KINDS:
                        family_prior, _tallies, _skip = _impute_for(subject, opponent)
                        if family_prior is not None and family_prior.p is not None:
                            prior_mean = family_prior.p
                            prior_source = (
                                f"family-current imputation (young {kind} era; "
                                f"{family_prior.license.cluster_id}, "
                                f"pool n={family_prior.pool_n}; LOO-harness order)"
                            )
                            prior_strength_value = SHRINK_STRENGTH
                            family_first = True
                if not family_first:
                    prior_mean, prior_source = _cross_era_prior(subject, opponent, s_ab)
                    prior_strength_value = SHRINK_STRENGTH
            cells[(subject, opponent)] = build_cell(
                subject, opponent, wins, n, prior_mean=prior_mean, prior_source=prior_source,
                prior_strength=prior_strength_value,
            )
            cell_windows[(subject, opponent)] = s_ab

    # 5. Superarchetype overlay (view is None on the default path — all three maps stay empty).
    # Pooled display cells INCLUDE the opponent's own matches (unlike the leave-opponent-out
    # prior above); imputed cells and ladder entries exist for every sub-display cell, refusals
    # included — distinct cell kinds, never blended into `cells` (epic addendum #1).
    cluster_cells: "dict[tuple[str, str], PooledCell]" = {}
    imputed_cells: "dict[tuple[str, str], ImputedCell]" = {}
    ladder: "dict[tuple[str, str], LadderEntry]" = {}
    if view is not None:
        from legacy_engine.analytics.superarchetype.aggregate import (
            aggregate_cluster_cell,
        )

        for subject in subjects:
            base = _chain.subject_base(subject, camp_parent)
            subject_cluster_id = view.cluster_of.get(base)
            mirror = mr_by_since[valid_since[subject]].mirror_n.get(subject, 0)
            for cluster_id in view.cluster_ids:
                drawn = _chain.draw_pool_tallies(
                    subject, cluster_id, view,
                    pooled_by_since=pooled_by_since, valid_since=valid_since,
                    subject_cluster_id=subject_cluster_id, subject_mirror_n=mirror,
                    regime_start=regime_start,
                )
                if not drawn.tallies:
                    continue
                cluster_cells[(subject, cluster_id)] = aggregate_cluster_cell(
                    subject, cluster_id, drawn.tallies,
                    window_note=drawn.window_note,
                    current_regime_share=drawn.current_regime_share,
                )
            own_parent = camp_parent.get(subject)
            for opponent in opponents:
                if opponent == subject or opponent == own_parent:
                    continue
                measured_n = cells[(subject, opponent)].n
                if measured_n >= DISPLAY_GATE_N:
                    continue
                imputed, imputed_tallies, imputed_skip = _impute_for(subject, opponent)
                if imputed is not None:
                    imputed_cells[(subject, opponent)] = imputed
                go_id = view.cluster_of.get(opponent)
                ladder[(subject, opponent)] = _chain.resolve_ladder(
                    subject, opponent,
                    measured_n=measured_n, display_gate_n=DISPLAY_GATE_N,
                    opponent_cluster_id=go_id,
                    pooled=cluster_cells.get((subject, go_id)) if go_id is not None else None,
                    imputed=imputed, imputed_tallies=imputed_tallies,
                    imputed_skip=imputed_skip,
                )

    multi = MultiSplitMatrix(
        cells=cells,
        subjects=subjects,
        opponents=opponents,
        camp_parent=camp_parent,
        parents=observed_parents,
        provenance=provenance,
        total_matches=full.coverage.decisive_matched,
        caveat=_CAVEAT,
    )
    return AdaptiveMultiSplitMatrix(
        multi=multi, valid_since=valid_since, cell_windows=cell_windows,
        horizon_meta=horizon_meta, audit_preamble=(*audit_preamble, *sa_audit),
        cluster_cells=cluster_cells, imputed_cells=imputed_cells, ladder=ladder,
    )
