"""Advisory window resolution + thin-regime degrade policy (epic-regime-aware-advisory, v1).

The CLI advisory/report surfaces let the user pick a ban-regime window (`--regime`), an explicit
`--since/--until`, or full corpus (`--all-time`, the v1 default). `resolve_advisory_window` turns
those flags into a concrete half-open `[since, until)` window and applies the inherited honesty
policy: when the requested window is too thin for reliable matchup/positioning math, **degrade to
full corpus and carry a loud banner** rather than return a thin or empty result silently.

Thinness is gated on a cheap rounds-count proxy (one `COUNT(*)`), not a full match-results build —
matchup data lives in rounds-bearing events, so the in-window round count tracks matchup-data volume
closely enough for a thin/not-thin gate; the banner reports the actual count honestly. Deck-based
surfaces (e.g. `report meta`) pass `thin_floor=0` to DISABLE the rounds-degrade — their thinness is
conveyed by per-row confidence tiers, not the rounds-bearing matchup population.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from legacy_engine.analytics.trends import resolve_regime

_THIN_ROUNDS_FLOOR: int = 500  # below this many in-window rounds → degrade to full corpus + banner


@dataclass(frozen=True)
class WindowResolution:
    """The resolved advisory window plus any degrade banner and a label for the header echo.

    ``mode`` drives matrix-consumer behavior (matchups/positioning/gaps): ``"adaptive"`` (the v2
    default — per-cell ban-aware matrix + current-regime field), ``"uniform"`` (an explicit
    ``--regime``/``--since`` window applied to both legs, the v1 path), or ``"full"`` (full corpus,
    via ``--all-time``). Deck-based surfaces like ``report meta`` ignore ``mode`` and just use
    ``since``/``until``.
    """

    since: str | None
    until: str | None
    banner: str | None        # set only when a thin requested window was degraded to full corpus
    requested_label: str      # "full-corpus" | "regime: <name>" | "<since>..<until>"
    mode: str = "full"        # "adaptive" | "uniform" | "full"


def _count_rounds(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str | None,
    until: str | None,
    provenance: str | None,
) -> int:
    """Cheap in-window rounds count (half-open [since, until)), the thinness proxy."""
    row = con.execute(
        """
        SELECT count(*)
        FROM rounds r
        JOIN tournaments t ON t.id = r.tournament_id
        WHERE (? IS NULL OR t.provenance = ?)
          AND (? IS NULL OR t.date >= ?)
          AND (? IS NULL OR t.date <  ?)
        """,
        [provenance, provenance, since, since, until, until],
    ).fetchone()
    return int(row[0]) if row else 0


def resolve_advisory_window(
    con: duckdb.DuckDBPyConnection,
    *,
    regime: str | None = None,
    since: str | None = None,
    until: str | None = None,
    all_time: bool = False,
    provenance: str | None = None,
    thin_floor: int = _THIN_ROUNDS_FLOOR,
    adaptive_default: bool = True,
) -> WindowResolution:
    """Resolve advisory window flags into a concrete window, degrading thin regimes to full corpus.

    Precedence (most → least specific): ``all_time`` > ``regime`` > ``since/until`` > default
    (full corpus, the v1 default). A resolved non-full window with fewer than ``thin_floor`` rounds
    degrades to full corpus and carries a banner reporting the count. ``all_time`` / full-corpus
    never degrade. ``thin_floor <= 0`` disables the rounds-degrade entirely — use it for deck-based
    surfaces like ``report meta`` whose thinness is conveyed by per-row confidence tiers, not the
    rounds-bearing matchup population.
    """
    # Explicit full corpus.
    if all_time:
        return WindowResolution(None, None, None, "full-corpus", mode="full")

    # Default (no flags) → adaptive per-cell windowing for matrix consumers (v2 default).
    # Deck-based surfaces (report meta) pass adaptive_default=False → full corpus default.
    if regime is None and since is None and until is None:
        if adaptive_default:
            return WindowResolution(None, None, None, "adaptive", mode="adaptive")
        return WindowResolution(None, None, None, "full-corpus", mode="full")

    if regime is not None:
        win_since, win_until = resolve_regime(regime)
        label = f"regime: {regime}"
        # resolve_regime("all"/"all-time") → (None, None): treat as full corpus.
        if win_since is None and win_until is None:
            return WindowResolution(None, None, None, "full-corpus", mode="full")
    else:
        win_since, win_until = since, until
        label = f"{since or '—'}..{until or '—'}"

    if thin_floor <= 0:
        # Degrade disabled (deck-based surface): honor the window as-is.
        return WindowResolution(win_since, win_until, None, label, mode="uniform")

    n_rounds = _count_rounds(con, since=win_since, until=win_until, provenance=provenance)
    if n_rounds < thin_floor:
        banner = (
            f"⚠ requested window ({label}) is THIN: {n_rounds} rounds < floor {thin_floor} — "
            f"showing FULL-CORPUS data (matchup/positioning math is unreliable on a window this small)"
        )
        # Degraded to full corpus, but the request was an explicit uniform window.
        return WindowResolution(None, None, banner, label, mode="uniform")

    return WindowResolution(win_since, win_until, None, label, mode="uniform")


@dataclass(frozen=True)
class AdvisoryInputs:
    """Resolved matchup matrix + the field window to pair with it, plus audit lines to echo.

    In adaptive mode the matrix is per-cell ban-aware and the field window is the CURRENT regime
    (so dead decks fall out via ≈0 current share); in uniform/full mode both legs share one window.
    """

    matrix: object                 # analytics.matchup.MatchupMatrix
    field_since: str | None
    field_until: str | None
    audit: tuple[str, ...]


def _adaptive_audit(
    horizon_meta: "dict[str, object]", audit_preamble: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Audit lines naming every disturbed entity + its trigger, counting ban-only entities, and
    noting undisturbed entities fall back to full corpus — plus one ``// ⚠`` line per
    alarm-flagged entity (alarms never truncate; they only add lines) and the whole-path
    no-era-data degrade preamble when present. ``horizon_meta`` values are
    ``analytics.eras.consume.EraHorizon`` (typed loosely here to avoid a hard import at module
    load; ``window.py`` already imports the matrix builder lazily inside ``build_advisory_inputs``
    for the same reason).
    """
    named = sorted(
        (a, h.since, h.trigger) for a, h in horizon_meta.items()
        if h.source in ("era", "era-parent") and h.since is not None
    )
    n_ban_only = sum(1 for h in horizon_meta.values() if h.source == "ban-only")

    if not named and not n_ban_only:
        lines: tuple[str, ...] = ("// adaptive: no entity disturbed — all cells use full corpus",)
    else:
        parts = [
            f"{a} since {since}" + (f" ({trigger})" if trigger else "")
            for a, since, trigger in named
        ]
        if n_ban_only:
            parts.append(f"{n_ban_only} entities ban-only")
        summary = "; ".join(parts) + "; all others full-corpus"
        lines = (f"// adaptive: per-entity era windows — {summary}",)

    alarm_lines = tuple(
        f"// ⚠ {a}: {h.alarm}" for a, h in sorted(horizon_meta.items()) if h.alarm
    )
    return audit_preamble + lines + alarm_lines


def build_advisory_inputs(
    con: duckdb.DuckDBPyConnection,
    win: WindowResolution,
    *,
    provenance: str | None = None,
    min_row_share: float = 0.02,
    split_variant: str | None = None,
):
    """Build the matchup matrix (+ field window + audit) per the resolved window mode.

    - ``adaptive`` → ``build_adaptive_matrix`` (era-aware per-entity horizons) + the
      detection-derived global field era (``analytics.eras.consume.resolve_field_era`` —
      ``max(current ban-regime start, latest accepted boundary among >=2% field-share
      entities)``, self-healing to the ban-regime start on a thin resulting window).
    - ``uniform``  → ``build_matrix`` over ``win.since/until``; field shares that same window.
    - ``full``     → full-corpus matrix + full-corpus field.

    ``split_variant`` (opt-in, default ``None``) passes through to the matrix builder so
    ``split_variant``'s decks are relabeled to their ``decks.variant`` camps; ``None`` is
    byte-identical to the pre-split behavior.
    """
    from legacy_engine.analytics.eras.consume import resolve_field_era
    from legacy_engine.analytics.matchup import build_adaptive_matrix, build_matrix

    if win.mode == "adaptive":
        adaptive = build_adaptive_matrix(
            con, provenance=provenance, min_row_share=min_row_share, split_variant=split_variant,
        )
        field_since, field_label = resolve_field_era(con, provenance=provenance)
        audit = _adaptive_audit(adaptive.horizon_meta, adaptive.audit_preamble)
        audit = (*audit, f"// field: since {field_since or 'open'} ({field_label})")
        return AdvisoryInputs(
            matrix=adaptive.matrix,
            field_since=field_since,
            field_until=None,
            audit=audit,
        )

    matrix = build_matrix(
        con, provenance=provenance, min_row_share=min_row_share,
        since=win.since, until=win.until, split_variant=split_variant,
    )
    return AdvisoryInputs(matrix=matrix, field_since=win.since, field_until=win.until, audit=())
