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
    """The resolved advisory window plus any degrade banner and a label for the header echo."""

    since: str | None
    until: str | None
    banner: str | None        # set only when a thin requested window was degraded to full corpus
    requested_label: str      # "full-corpus" | "regime: <name>" | "<since>..<until>"


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
) -> WindowResolution:
    """Resolve advisory window flags into a concrete window, degrading thin regimes to full corpus.

    Precedence (most → least specific): ``all_time`` > ``regime`` > ``since/until`` > default
    (full corpus, the v1 default). A resolved non-full window with fewer than ``thin_floor`` rounds
    degrades to full corpus and carries a banner reporting the count. ``all_time`` / full-corpus
    never degrade. ``thin_floor <= 0`` disables the rounds-degrade entirely — use it for deck-based
    surfaces like ``report meta`` whose thinness is conveyed by per-row confidence tiers, not the
    rounds-bearing matchup population.
    """
    # Full corpus — explicit or default. No degrade.
    if all_time or (regime is None and since is None and until is None):
        return WindowResolution(since=None, until=None, banner=None, requested_label="full-corpus")

    if regime is not None:
        win_since, win_until = resolve_regime(regime)
        label = f"regime: {regime}"
        # resolve_regime("all"/"all-time") → (None, None): treat as full corpus.
        if win_since is None and win_until is None:
            return WindowResolution(None, None, None, "full-corpus")
    else:
        win_since, win_until = since, until
        label = f"{since or '—'}..{until or '—'}"

    if thin_floor <= 0:
        # Degrade disabled (deck-based surface): honor the window as-is.
        return WindowResolution(since=win_since, until=win_until, banner=None, requested_label=label)

    n_rounds = _count_rounds(con, since=win_since, until=win_until, provenance=provenance)
    if n_rounds < thin_floor:
        banner = (
            f"⚠ requested window ({label}) is THIN: {n_rounds} rounds < floor {thin_floor} — "
            f"showing FULL-CORPUS data (matchup/positioning math is unreliable on a window this small)"
        )
        return WindowResolution(since=None, until=None, banner=banner, requested_label=label)

    return WindowResolution(since=win_since, until=win_until, banner=None, requested_label=label)
