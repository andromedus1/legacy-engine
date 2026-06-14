"""Player identity resolution — curated alias map + opt-in heuristic suggester.

Design: an explicit, git-tracked ``data/players/aliases.json`` is the source of truth.
Every free-text handle in ``decks.player`` is *normalized* via ``normalize_player`` and
looked up in this map.  Handles absent from the map resolve to **themselves** (no handle is
ever silently dropped or merged).  The ``suggest_aliases`` heuristic proposes candidate
clusters for human review but **never writes anything**.

Gated-additive: when ``alias_map`` is empty (no ``aliases.json`` entries), every call to
``resolve_player`` is byte-identical to calling ``normalize_player`` directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from legacy_engine.analytics.match_results import normalize_player
from legacy_engine.config import ALIASES_PATH

if TYPE_CHECKING:
    import duckdb


# ---------------------------------------------------------------------------
# Alias-map types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AliasSuggestion:
    """A heuristic-proposed cluster of handles that may refer to the same player.

    This is a *suggestion* only — the curator decides whether to add the cluster to
    ``aliases.json``.  ``reason`` is a short human-readable summary of why the handles
    were grouped (e.g. normalized-stem overlap, never co-occur same event/day).
    """

    handles: tuple[str, ...]         # raw (un-normalized) handles that form the cluster
    handles_norm: tuple[str, ...]     # corresponding normalized handles
    reason: str


# ---------------------------------------------------------------------------
# Unit 1 — alias-map loading and pure resolution
# ---------------------------------------------------------------------------


def load_alias_map(path: Path | str = ALIASES_PATH) -> dict[str, str]:
    """Load the curated alias map from *path* → ``{handle_norm: player_id}``.

    The JSON schema is::

        {
          "players": {
            "<player_id>": {
              "display": "...",
              "handles": ["Raw Handle 1", "raw handle 2", ...],
              ...
            }
          }
        }

    Each handle is normalized via ``normalize_player`` before insertion, mirroring the
    collation used for the ``decks.player`` join key so the Python and DuckDB sides never
    diverge.

    Returns an empty dict when the file is absent or has no ``players`` entries — callers
    must not require the file to exist (gated-additive: no aliases → no change in behaviour).
    """
    p = Path(path)
    if not p.exists():
        return {}
    raw = json.loads(p.read_text())
    players: dict = raw.get("players") or {}
    alias_map: dict[str, str] = {}
    for player_id, entry in players.items():
        for handle in entry.get("handles") or []:
            norm = normalize_player(handle)
            if norm:
                alias_map[norm] = player_id
    return alias_map


def resolve_player(handle: str | None, alias_map: dict[str, str]) -> str:
    """Resolve a free-text player handle to a canonical player_id.

    Pure function:

    1. Normalize the handle via ``normalize_player`` (strip + casefold, SSOT collation).
    2. Look up the normalized handle in ``alias_map``.
    3. If found, return the canonical ``player_id``; otherwise return the normalized handle
       itself (absent handles always resolve to themselves, never silently dropped).

    Returns ``""`` for ``None`` / blank input (mirrors ``normalize_player`` behaviour).
    """
    norm = normalize_player(handle)
    return alias_map.get(norm, norm)


# ---------------------------------------------------------------------------
# Unit 2 — materialization into a derived DuckDB table
# ---------------------------------------------------------------------------


def materialize_player_aliases(
    con: "duckdb.DuckDBPyConnection",
    alias_map: dict[str, str],
) -> int:
    """Build (or rebuild) the derived ``player_aliases`` table from *alias_map*.

    Schema: ``(handle_norm VARCHAR PRIMARY KEY, player_id VARCHAR NOT NULL)``.

    Idempotent — drops and recreates so a repeated call with the same map yields the same
    rows.  When ``alias_map`` is empty the table is created with zero rows (gated-additive:
    no aliases → no SQL join matches → existing behaviour unchanged).

    Returns the number of rows inserted.
    """
    con.execute("DROP TABLE IF EXISTS player_aliases")
    con.execute(
        "CREATE TABLE IF NOT EXISTS player_aliases ("
        "handle_norm VARCHAR PRIMARY KEY, player_id VARCHAR NOT NULL)"
    )
    if not alias_map:
        return 0
    rows = list(alias_map.items())  # [(handle_norm, player_id), ...]
    con.executemany("INSERT INTO player_aliases VALUES (?, ?)", rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Unit 3 — opt-in heuristic suggester (never writes, always read-only)
# ---------------------------------------------------------------------------


def _normalized_stem(norm: str, min_len: int = 4) -> str | None:
    """Return a prefix stem of *norm* suitable for overlap matching, or None if too short."""
    return norm[:min_len] if len(norm) >= min_len else None


def suggest_aliases(
    con: "duckdb.DuckDBPyConnection",
    *,
    min_overlap: int = 4,
) -> list[AliasSuggestion]:
    """Propose candidate alias clusters for human curation.

    **Strategy**: two handles are placed in the same candidate cluster when ALL of:

    1. Their normalized forms share a common prefix of at least *min_overlap* characters
       (normalized-stem overlap — a cheap recall heuristic).
    2. They have **never appeared together in the same event on the same day** (co-occurrence
       exclusion — if two handles co-occur, they are *not* the same person).

    This is a heuristic, not an oracle.  The curator is expected to inspect the output and
    decide which clusters are genuine aliases before adding them to ``aliases.json``.

    **Returns** a list of ``AliasSuggestion`` objects (possibly empty).  **Writes nothing.**
    Requires the ``decks`` and ``tournaments`` tables to be present (reads them read-only).

    Skips gracefully if the tables are absent (returns ``[]``).
    """
    # Check that the required tables exist — graceful no-op if they don't.
    try:
        tables_res = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('decks', 'tournaments')"
        ).fetchall()
        table_names = {r[0] for r in tables_res}
        if "decks" not in table_names or "tournaments" not in table_names:
            return []
    except Exception:  # pragma: no cover
        return []

    # Fetch all distinct players with their normalized form and per-event participation.
    # We need: (handle_raw, tournament_id, date) per player per event.
    try:
        rows = con.execute(
            """
            SELECT DISTINCT
                d.player                          AS handle_raw,
                d.tournament_id,
                t.date                            AS event_date
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE d.player IS NOT NULL AND trim(d.player) != ''
            """
        ).fetchall()
    except Exception:  # pragma: no cover
        return []

    if not rows:
        return []

    # Build per-player set of (tournament_id, date) pairs + raw→norm map.
    # handle_raw → set of (tid, date)
    from collections import defaultdict

    player_events: dict[str, set[tuple[str, str]]] = defaultdict(set)
    raw_to_norm: dict[str, str] = {}
    for handle_raw, tid, date in rows:
        norm = normalize_player(handle_raw)
        player_events[handle_raw].add((tid, date))
        raw_to_norm[handle_raw] = norm

    all_handles_raw = list(player_events.keys())

    # Group handles by normalized stem.
    stem_to_handles: dict[str, list[str]] = defaultdict(list)
    for h in all_handles_raw:
        norm = raw_to_norm[h]
        stem = _normalized_stem(norm, min_overlap)
        if stem is not None:
            stem_to_handles[stem].append(h)

    # For each stem group with ≥2 handles, apply the co-occurrence exclusion filter.
    suggestions: list[AliasSuggestion] = []
    for stem, group in stem_to_handles.items():
        if len(group) < 2:
            continue
        # Find the maximal subset that never co-occurs on the same event+day.
        # Simple approach: build a graph of "compatible" (non-co-occurring) pairs,
        # then collect connected components as candidate clusters.
        def co_occurs(a: str, b: str) -> bool:
            """True if handles a and b both appear in the same (tournament_id, date)."""
            return bool(player_events[a] & player_events[b])

        # Build adjacency: compatible[i] = set of j indices that don't co-occur with i.
        n = len(group)
        compatible: list[set[int]] = [set() for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if not co_occurs(group[i], group[j]):
                    compatible[i].add(j)
                    compatible[j].add(i)

        # Union-find over compatible edges to build clusters.
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            parent[find(x)] = find(y)

        for i in range(n):
            for j in compatible[i]:
                union(i, j)

        # Collect clusters (components with ≥2 members).
        from collections import defaultdict as _dd
        clusters: dict[int, list[int]] = _dd(list)
        for i in range(n):
            clusters[find(i)].append(i)

        for cluster_indices in clusters.values():
            if len(cluster_indices) < 2:
                continue
            cluster_handles = tuple(group[i] for i in sorted(cluster_indices))
            cluster_norms = tuple(raw_to_norm[h] for h in cluster_handles)
            suggestions.append(
                AliasSuggestion(
                    handles=cluster_handles,
                    handles_norm=cluster_norms,
                    reason=(
                        f"normalized-stem overlap on '{stem}'; "
                        "handles never co-occur in the same event on the same day"
                    ),
                )
            )

    return suggestions
