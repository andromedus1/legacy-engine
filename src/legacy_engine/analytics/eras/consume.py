"""Era-horizon adapter — the consumption seam between the persisted ``entity_eras`` ledger
(``analytics/eras/store.py``) and the two remaining regime-windowed surfaces that read it: the
adaptive matchup matrix (``analytics/matchup.py::build_adaptive_matrix``) and the global field
window (``advisory/window.py::build_advisory_inputs``). Neither consumer touches ``entity_eras``
directly — everything routes through this module's ``era_horizons``/``resolve_field_era`` so the
resolution-order semantics live in exactly one place.

**Resolution order per entity label** (epic decision):
  1. EXACT match in ``entity_eras`` — a camp's own row, or a parent archetype's own row.
  2. PARENT match — camp labels (``f"{parent} [{variant}]"``, the same convention
     ``series.build_entity_series`` and ``match_results.effective_label`` both use) fall back to
     their parent archetype's ``entity_eras`` row when the camp itself has no row of its own.
  3. BAN-ONLY fallback (``analytics.affectedness.archetype_valid_since``) when the entity —
     parent included — has no ``entity_eras`` row at all (never analyzed: below the detection
     floors, or ``eras run`` hasn't covered it).

Present-with-``None`` (an analyzed, undisturbed entity) means full history is solid — this
WIDENS that entity beyond the current regime relative to the pre-epic ban-only behavior; that
widening is the epic's intended payoff, not a bug.

**Whole-path degrade**: when ``entity_eras`` is missing/empty entirely, every label falls to
"ban-only" and one audit line names the degrade ("run `eras run`") — never a silently different
number.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from legacy_engine.analytics.eras.store import StoredEntityEras, read_entity_eras

# Field-era self-heal gate (epic design decision): below this many decks in the candidate
# [field_since, now) window, the detection-derived field era is too thin to trust — degrade back
# to the ban-regime start with a labeled banner. Decks-based (not rounds-based, unlike
# advisory/window.py's `_THIN_ROUNDS_FLOOR`) since field share is a deck/metashare concept.
_FIELD_THIN_DECKS_FLOOR: int = 500

_FIELD_MIN_SHARE_DEFAULT: float = 0.02


def _parent_label(label: str, split_variant: str | None) -> str:
    """Strip a variant-camp suffix so a camp label resolves to its parent archetype.

    Duplicated (not imported) from ``analytics.matchup._base_archetype``: ``matchup.py`` imports
    ``era_horizons`` from this module for its own default resolution, so importing
    ``_base_archetype`` back would create an ``eras -> matchup -> eras`` import cycle. Same shape
    as ``attribution.py``'s own duplicated-constant precedent (``_BAN_AFFECT_THRESHOLD``) for the
    identical reason — a one-line rule doesn't warrant a cross-module private import.
    """
    if split_variant is not None and label.startswith(f"{split_variant} ["):
        return split_variant
    return label


@dataclass(frozen=True)
class EraHorizon:
    """One entity's resolved adaptive-matrix horizon.

    ``since``: the horizon date, or ``None`` for full history.
    ``source``: ``"era"`` (the entity's own ``entity_eras`` row) | ``"era-parent"`` (inherited via
    camp -> parent fallback) | ``"ban-only"`` (no ``entity_eras`` row at all — the pre-epic
    fallback, via ``archetype_valid_since``).
    ``trigger``: the human-readable cause of the horizon (a ban/release/unattributed detail from
    the winning boundary's attribution), or ``None`` when there is no disturbance to name
    (undisturbed entity, or a ban-only horizon with no affecting ban).
    ``alarm``: the entity's drift-alarm note when its alarm fired, else ``None``.
    """

    since: str | None
    source: str
    trigger: str | None
    alarm: str | None


def _winning_boundary_trigger(stored: StoredEntityEras) -> str | None:
    """The attribution detail of the boundary that set ``stored.stable_since``.

    ``None`` when ``stable_since`` is ``None`` (no accepted boundary — undisturbed) or the
    winning boundary's attribution wasn't recorded (shouldn't normally happen — every accepted
    boundary is attributed by ``eras run``, even if only to "unattributed disturbance").
    """
    if stored.stable_since is None:
        return None
    for b in stored.boundaries:
        if b.bh_accepted and not b.floor_rejected and b.date == stored.stable_since:
            return b.attribution.detail if b.attribution is not None else None
    return None


def era_horizons(
    con: duckdb.DuckDBPyConnection,
    archetypes: list[str],
    *,
    provenance: str | None = None,
    split_variant: str | None = None,
    affect_threshold: float = 0.25,
) -> tuple[dict[str, EraHorizon], tuple[str, ...]]:
    """Resolve every label in ``archetypes`` to an ``EraHorizon`` (exact -> parent -> ban-only).

    ``archetypes`` may be plain parent-archetype labels or ``f"{split_variant} [{variant}]"`` camp
    labels (``split_variant`` names which archetype's camps these are — the same convention
    ``matchup.build_adaptive_matrix`` itself uses). Returns ``(horizons, audit_preamble)`` where
    ``audit_preamble`` is empty unless ``entity_eras`` is missing/empty entirely, in which case it
    carries exactly one whole-path-degrade line.
    """
    from legacy_engine.analytics.affectedness import archetype_valid_since

    stored = read_entity_eras(con)
    no_era_data = not stored

    horizons: dict[str, EraHorizon] = {}
    need_ban_only: list[str] = []

    for label in archetypes:
        entry = stored.get(label)
        if entry is not None:
            horizons[label] = EraHorizon(
                since=entry.stable_since,
                source="era",
                trigger=_winning_boundary_trigger(entry),
                alarm=(entry.alarm_note if entry.alarm_fired else None),
            )
            continue

        parent = _parent_label(label, split_variant)
        parent_entry = stored.get(parent) if parent != label else None
        if parent_entry is not None:
            horizons[label] = EraHorizon(
                since=parent_entry.stable_since,
                source="era-parent",
                trigger=_winning_boundary_trigger(parent_entry),
                alarm=(parent_entry.alarm_note if parent_entry.alarm_fired else None),
            )
            continue

        need_ban_only.append(label)

    if need_ban_only:
        base_labels = sorted({_parent_label(a, split_variant) for a in need_ban_only})
        base_valid_since = archetype_valid_since(
            con, base_labels, provenance=provenance, affect_threshold=affect_threshold,
        )
        for label in need_ban_only:
            base = _parent_label(label, split_variant)
            since = base_valid_since.get(base)
            horizons[label] = EraHorizon(
                since=since,
                source="ban-only",
                trigger=(f"ban: valid_since {since}" if since else None),
                alarm=None,
            )

    audit: tuple[str, ...] = ()
    if no_era_data:
        audit = ("// eras: no era data — ban-only horizons; run `eras run`",)

    return horizons, audit


def resolve_field_era(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    min_share: float = _FIELD_MIN_SHARE_DEFAULT,
) -> tuple[str | None, str]:
    """The global field-era boundary: ``max(current ban-regime start, latest accepted boundary
    among PARENT entities holding >= min_share full-corpus field share)``.

    Self-healing: when the resulting ``[field_since, now)`` window has fewer than
    ``_FIELD_THIN_DECKS_FLOOR`` decks, degrades back to the ban-regime start with a labeled
    banner rather than trust a thin detection-derived window (epic self-heal gate).

    "Parent" entities only (``entity_eras`` rows where ``parent == entity``) — field share is a
    metagame-slice concept, not a sub-camp one; folding camps in would double-count their
    parent's share. One cheap deck-count query for the share proxy (``provenance`` is NOT
    threaded through it deliberately — the field-era boundary is a global, corpus-wide gate, not
    a per-basis one; every other regime-windowed surface in this feature keeps ``provenance`` as
    a matrix/window-level filter, not a field-share one).
    """
    from legacy_engine.analytics.trends import resolve_regime

    ban_since, _ban_until = resolve_regime("current")

    stored = read_entity_eras(con)
    parent_rows = {e.entity: e for e in stored.values() if e.parent == e.entity}
    if not parent_rows:
        return ban_since, "ban regime (no era data)"

    names = sorted(parent_rows)
    placeholders = ",".join("?" for _ in names)
    total_row = con.execute("SELECT count(*) FROM decks WHERE archetype IS NOT NULL").fetchone()
    total = int(total_row[0]) if total_row else 0
    if total <= 0:
        return ban_since, "ban regime (no deck data)"

    share_rows = con.execute(
        f"""
        SELECT archetype, count(*) FROM decks
        WHERE archetype IN ({placeholders})
        GROUP BY archetype
        """,  # noqa: S608 — placeholders are '?' marks, values bound below
        names,
    ).fetchall()
    share_by_entity = {a: n / total for a, n in share_rows}

    candidates = [
        e.stable_since for e in parent_rows.values()
        if e.stable_since is not None and share_by_entity.get(e.entity, 0.0) >= min_share
    ]
    if not candidates:
        return ban_since, "ban regime (no high-share disturbance)"

    latest_boundary = max(candidates)
    if latest_boundary <= (ban_since or ""):
        return ban_since, "ban regime (no boundary later than the ban regime start)"

    field_since = latest_boundary
    count_row = con.execute(
        """
        SELECT count(*) FROM decks dk JOIN tournaments t ON t.id = dk.tournament_id
        WHERE (? IS NULL OR t.date >= ?)
        """,
        [field_since, field_since],
    ).fetchone()
    n_decks = int(count_row[0]) if count_row else 0
    if n_decks < _FIELD_THIN_DECKS_FLOOR:
        return (
            ban_since,
            f"⚠ thin field window since {field_since} ({n_decks} decks < floor "
            f"{_FIELD_THIN_DECKS_FLOOR}) — degraded to ban regime",
        )

    return field_since, f"detection-derived (latest high-share boundary {latest_boundary})"
