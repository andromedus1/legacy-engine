"""Matchup matrix — Wilson/Jeffreys CIs, Beta-Binomial shrinkage, cell builder, matrix builder.

This module is the consumer of ``match_results.compute_match_results``.  It
turns raw ``{wins, losses, n}`` tallies into fully-computed ``MatchupCell``
objects and assembles them into a ``MatchupMatrix`` that carries both the cells
and provenance metadata.

Units covered:
- Unit 2: Stats primitives — ``wilson_or_jeffreys_ci``, ``beta_binomial_shrink``
- Unit 4: Cell builder — ``build_cell``, ``build_mirror_cell``
- Unit 5: Matrix builder — ``MatchupMatrix``, ``build_matrix``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from statsmodels.stats.proportion import proportion_confint

from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.confidence import tier_for_sample
from legacy_engine.models.matchup import MatchupCell

if TYPE_CHECKING:
    from legacy_engine.analytics.eras.consume import EraHorizon

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


def build_cell(archetype_a: str, archetype_b: str, wins: int, n: int) -> MatchupCell:
    """Build a directed ``MatchupCell`` for ``archetype_a`` vs ``archetype_b``.

    Computes raw win-rate, shrunk estimate, CI, tier, and display flag in one
    place so consumers (charts, advisory) never re-derive the gate logic.
    Both ``p_raw`` and ``p_shrunk`` are always populated when ``n > 0`` (the
    brief forbids showing shrinkage without the raw number).
    """
    tier = tier_for_sample(n)
    display = n >= DISPLAY_GATE_N
    if n > 0:
        p_raw: float | None = wins / n
        p_shrunk: float | None = beta_binomial_shrink(wins, n)
        ci_low, ci_high = wilson_or_jeffreys_ci(wins, n)
    else:
        p_raw = None
        p_shrunk = None
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

    # ── Populate cells ───────────────────────────────────────────────────────
    cells: dict[tuple[str, str], MatchupCell] = {}

    for a in included:
        # Mirror cell
        cells[(a, a)] = build_mirror_cell(a, mr.mirror_n.get(a, 0))

        for b in included:
            if a == b:
                continue
            tally = mr.matchups.get((a, b))
            if tally is not None:
                cells[(a, b)] = build_cell(a, b, tally.wins, tally.n)
            else:
                # Unobserved pair — emit n=0 cell to keep matrix rectangular
                cells[(a, b)] = build_cell(a, b, 0, 0)

    return MatchupMatrix(
        cells=cells,
        provenance=provenance,
        total_matches=total_matches,
        archetypes=included,
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
            tally = mr_by_since[s_ab].matchups.get((a, b))
            cells[(a, b)] = build_cell(a, b, tally.wins, tally.n) if tally else build_cell(a, b, 0, 0)
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
