"""Meta-share computation — three labeled definitions over the DuckDB archetype corpus.

Implements §3a raw entry share, §3b top-cut presence share, and §3c win-rate-weighted
share per PRINCIPLES #6 (never an unlabeled blended number).  Every emitted share
states its ``(definition, provenance basis)``.  Confidence tiers are attached to
every entry via ``tier_for_sample(n)``.

Does **not** compute matchup cells (that's ``matchup-matrix``), trends (``trends``),
or render charts (``charts``).  The win-rate input for §3c comes from
``compute_match_results`` in ``match_results``, not recomputed here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb

from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unit 1 — Top-cut counts
# ---------------------------------------------------------------------------

_TOPCUT_SQL = """
SELECT d.archetype AS archetype, count(*) AS n
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
JOIN standings s ON s.tournament_id = d.tournament_id
               AND lower(trim(s.player)) = lower(trim(d.player))
WHERE d.archetype IS NOT NULL
  AND s.rank <= ?
  AND (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date < ?)
GROUP BY d.archetype
"""


def _topcut_counts(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None,
    cut_size: int,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, int]:
    """Per-archetype count of decks finishing within the event's top cut (standings.rank <= cut_size).

    Decks with no standings row (e.g. MTGO League 5-0 dumps) are excluded from
    definition (b)'s numerator AND denominator — top-cut is undefined for them.
    """
    rows = con.execute(
        _TOPCUT_SQL, [cut_size, provenance, provenance, since, since, until, until]
    ).fetchall()
    return {archetype: n for archetype, n in rows}


# ---------------------------------------------------------------------------
# Unit 2 — Raw counts
# ---------------------------------------------------------------------------

_RAW_SQL = """
SELECT d.archetype AS archetype, count(*) AS n
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
WHERE d.archetype IS NOT NULL
  AND (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date < ?)
GROUP BY d.archetype
"""

_UNLABELED_SQL = """
SELECT count(*) AS n
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
WHERE d.archetype IS NULL
  AND (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date < ?)
"""


def _raw_counts(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, int]:
    """Per-archetype deck count over labeled decks (archetype IS NOT NULL)."""
    rows = con.execute(
        _RAW_SQL, [provenance, provenance, since, since, until, until]
    ).fetchall()
    return {archetype: n for archetype, n in rows}


def _unlabeled_count(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None,
    since: str | None = None,
    until: str | None = None,
) -> int:
    """Decks with NULL archetype (labeler not yet run / failed) — surfaced as coverage, not counted."""
    row = con.execute(
        _UNLABELED_SQL, [provenance, provenance, since, since, until, until]
    ).fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# Unit 3 — Win-rate-weighted weights
# ---------------------------------------------------------------------------


def _wrw_weights(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None
) -> tuple[dict[str, float], dict[str, int]]:
    """Return (weight_by_archetype, matchup_n_by_archetype).

    weight(a) = share_raw(a) * wr(a), where wr(a) = wins/(wins+losses) from
    match_results' per-archetype marginal.  Only archetypes with match data
    (n>0) get a weight — archetypes that appear in deck counts but have zero
    rounds (the bimodal-coverage gap) are dropped from the weighted numerator
    and reported via matchup_n=0.  The caller renormalises weights to sum to 1.
    """
    # Import here to avoid circular deps at module load time
    from legacy_engine.analytics.match_results import compute_match_results

    raw = _raw_counts(con, provenance=provenance)
    total_decks = sum(raw.values())

    if total_decks == 0:
        return {}, {}

    match_res = compute_match_results(con, provenance=provenance)

    weights: dict[str, float] = {}
    matchup_n: dict[str, int] = {}

    for archetype, deck_count in raw.items():
        share_raw = deck_count / total_decks
        rec = match_res.archetypes.get(archetype)
        if rec is None or rec.n == 0:
            # Bimodal-coverage gap: archetype has deck count but zero match data
            matchup_n[archetype] = 0
            log.debug(
                "wrw: %s has deck count but no match data — excluded from weighted numerator",
                archetype,
            )
            continue
        wr = rec.wins / rec.n
        weights[archetype] = share_raw * wr
        matchup_n[archetype] = rec.n

    return weights, matchup_n


# ---------------------------------------------------------------------------
# Unit 4 — Share record types + shared assembler
# ---------------------------------------------------------------------------

Definition = str  # "raw" | "topcut" | "wrw"


@dataclass
class MetaShareEntry:
    """One archetype's share in a labeled definition+provenance context."""

    archetype: str
    share: float  # 0..1, within (definition, provenance) basis
    n: int  # backing sample: deck count (raw/topcut) or matchup-n (wrw)
    tier: ConfidenceLevel  # tier_for_sample(n)
    fringe: bool  # share < min_share (grouped under "Other" in headline views)


@dataclass
class MetaShareReport:
    """A fully-labeled meta-share result for one (definition, provenance) basis.

    ``definition`` and ``provenance`` are ALWAYS set (PRINCIPLES #6).
    """

    definition: Definition  # "raw" | "topcut" | "wrw"  — ALWAYS labeled
    provenance: str | None  # "online" | "paper" | None  — the basis, ALWAYS labeled
    entries: list[MetaShareEntry]  # sorted desc by share; "Other" row last when grouped
    total_decks: int  # denominator basis (labeled decks / top-cut decks)
    unlabeled: int  # NULL-archetype decks (coverage, raw/topcut only)
    min_share: float  # the inclusion floor applied (default 0.02)


# Labels that must never be folded into the "Other" fringe bucket
_NEVER_OTHER = {"Unknown", "Conflict"}


def _is_never_other(archetype: str) -> bool:
    """True for classifier labels that must remain their own rows (Unknown, Conflict(...))."""
    return archetype in _NEVER_OTHER or archetype.startswith("Conflict(")


def _assemble(
    counts_or_weights: dict[str, float],
    *,
    definition: Definition,
    provenance: str | None,
    n_by_arch: dict[str, int],
    total: int | float,
    unlabeled: int,
    min_share: float,
    group_other: bool,
    display_total: int | None = None,
) -> MetaShareReport:
    """Turn per-archetype numerators into labeled, confidence-tagged, floor-applied shares.

    ``counts_or_weights`` maps archetype → raw numerator value (integer counts or
    pre-normalised weights).  The assembler normalises over ``total``.
    ``display_total`` overrides ``total_decks`` on the returned report (used for wrw
    where ``total=1`` for normalised weights but ``total_decks`` should be matchup-n).
    """
    if total == 0:
        return MetaShareReport(
            definition=definition,
            provenance=provenance,
            entries=[],
            total_decks=display_total if display_total is not None else 0,
            unlabeled=unlabeled,
            min_share=min_share,
        )

    # Compute shares
    entries_raw: list[MetaShareEntry] = []
    for archetype, numerator in counts_or_weights.items():
        share = numerator / total
        n = n_by_arch.get(archetype, 0)
        fringe = share < min_share
        entries_raw.append(
            MetaShareEntry(
                archetype=archetype,
                share=share,
                n=n,
                tier=tier_for_sample(n),
                fringe=fringe,
            )
        )

    # Sort descending by share
    entries_raw.sort(key=lambda e: e.share, reverse=True)

    if not group_other:
        return MetaShareReport(
            definition=definition,
            provenance=provenance,
            entries=entries_raw,
            total_decks=total,
            unlabeled=unlabeled,
            min_share=min_share,
        )

    # Group fringe entries (excl. Never-Other labels) into "Other"
    main_entries: list[MetaShareEntry] = []
    fringe_entries: list[MetaShareEntry] = []

    for entry in entries_raw:
        if entry.fringe and not _is_never_other(entry.archetype):
            fringe_entries.append(entry)
        else:
            main_entries.append(entry)

    if fringe_entries:
        other_share = sum(e.share for e in fringe_entries)
        other_n = sum(e.n for e in fringe_entries)
        other_entry = MetaShareEntry(
            archetype="Other",
            share=other_share,
            n=other_n,
            tier=tier_for_sample(other_n),
            fringe=True,
        )
        entries = main_entries + [other_entry]
    else:
        entries = main_entries

    return MetaShareReport(
        definition=definition,
        provenance=provenance,
        entries=entries,
        total_decks=display_total if display_total is not None else int(total),
        unlabeled=unlabeled,
        min_share=min_share,
    )


# ---------------------------------------------------------------------------
# Unit 5 — Public compute entry points
# ---------------------------------------------------------------------------


def compute_metashare(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: Definition = "raw",
    provenance: str | None = None,
    min_share: float = 0.02,
    cut_size: int = 8,
    group_other: bool = True,
    since: str | None = None,
    until: str | None = None,
) -> MetaShareReport:
    """Compute meta-share for one definition and provenance basis.

    ``definition`` must be one of ``"raw"``, ``"topcut"``, or ``"wrw"``.
    ``provenance`` filters to ``"online"``/``"paper"``; ``None`` = all.
    ``since``/``until`` are ISO ``YYYY-MM-DD`` strings for a half-open ``[since, until)``
    date window against ``tournaments.date``; ``None`` = no bound.

    ``definition="wrw"`` with a date window raises ``NotImplementedError`` — windowed
    win-rate-weighted share is incoherent because ``compute_match_results`` is not windowed.

    Returns a fully-labeled ``MetaShareReport`` with confidence tiers and the
    inclusion floor applied.
    """
    if definition == "wrw" and (since is not None or until is not None):
        raise NotImplementedError(
            "windowed wrw is unsupported — match_results is not windowed; use raw/topcut for trends"
        )

    unlabeled = _unlabeled_count(con, provenance=provenance, since=since, until=until)

    if definition == "raw":
        counts = _raw_counts(con, provenance=provenance, since=since, until=until)
        total = sum(counts.values())
        n_by_arch = dict(counts)
        return _assemble(
            {k: float(v) for k, v in counts.items()},
            definition=definition,
            provenance=provenance,
            n_by_arch=n_by_arch,
            total=total,
            unlabeled=unlabeled,
            min_share=min_share,
            group_other=group_other,
        )

    elif definition == "topcut":
        counts = _topcut_counts(con, provenance=provenance, cut_size=cut_size, since=since, until=until)
        total = sum(counts.values())
        n_by_arch = dict(counts)
        return _assemble(
            {k: float(v) for k, v in counts.items()},
            definition=definition,
            provenance=provenance,
            n_by_arch=n_by_arch,
            total=total,
            unlabeled=0,  # top-cut: no standings row → excluded, not "unlabeled"
            min_share=min_share,
            group_other=group_other,
        )

    elif definition == "wrw":
        weights, matchup_n = _wrw_weights(con, provenance=provenance)
        # Renormalise weights to sum to 1.0
        weight_total = sum(weights.values())
        if weight_total == 0:
            return MetaShareReport(
                definition=definition,
                provenance=provenance,
                entries=[],
                total_decks=0,
                unlabeled=unlabeled,
                min_share=min_share,
            )
        normalised = {k: v / weight_total for k, v in weights.items()}
        # n_by_arch for wrw is matchup-n (honest: confidence bounded by smaller match sample)
        # total_decks on the report is the sum of matchup-n for archetypes in the weighted set
        total_matchup_n = sum(matchup_n[a] for a in weights)
        return _assemble(
            normalised,
            definition=definition,
            provenance=provenance,
            n_by_arch=matchup_n,
            total=1,  # already normalised — shares are the values; total=1 so share=value
            unlabeled=unlabeled,
            min_share=min_share,
            group_other=group_other,
            display_total=total_matchup_n,
        )

    else:
        raise ValueError(f"Unknown definition {definition!r}; must be 'raw', 'topcut', or 'wrw'")


def compute_all(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    min_share: float = 0.02,
    cut_size: int = 8,
    group_other: bool = True,
) -> dict[Definition, MetaShareReport]:
    """Compute all three definitions for one provenance basis.

    Returns ``{'raw': ..., 'topcut': ..., 'wrw': ...}``.
    """
    return {
        defn: compute_metashare(
            con,
            definition=defn,
            provenance=provenance,
            min_share=min_share,
            cut_size=cut_size,
            group_other=group_other,
        )
        for defn in ("raw", "topcut", "wrw")
    }


def blend_shares(
    reports: dict[str, MetaShareReport],
    weights: dict[str, float],
) -> MetaShareReport:
    """OPT-IN weighted blend across provenance bases (e.g. ``{'online': 0.7, 'paper': 0.3}``).

    Warns (logs) if weights don't sum to 1.  The result is labeled
    ``provenance='blend(<weights>)'`` so it is **never** an unlabeled blended
    number (PRINCIPLES #6).  Inputs must share the same ``definition``.
    """
    if not reports:
        raise ValueError("blend_shares: reports dict must not be empty")

    # Validate all reports share the same definition
    definitions = {r.definition for r in reports.values()}
    if len(definitions) > 1:
        raise ValueError(
            f"blend_shares: mismatched definitions across inputs: {definitions!r}. "
            "All reports must use the same definition."
        )
    definition = next(iter(definitions))

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-9:
        log.warning(
            "blend_shares: weights sum to %.6f (expected 1.0) — result will be rescaled",
            weight_sum,
        )
        # Rescale to sum to 1
        weights = {k: v / weight_sum for k, v in weights.items()}

    # Collect all archetypes that appear in any report
    all_archetypes: set[str] = set()
    for prov, report in reports.items():
        if prov not in weights:
            continue
        for entry in report.entries:
            if entry.archetype != "Other":
                all_archetypes.add(entry.archetype)

    # Compute blended share per archetype
    blended: dict[str, float] = {}
    blended_n: dict[str, int] = {}

    for archetype in all_archetypes:
        blended_share = 0.0
        total_n = 0
        for prov, report in reports.items():
            w = weights.get(prov, 0.0)
            if w == 0:
                continue
            # Look up this archetype in the report (may not be present)
            entry_share = 0.0
            entry_n = 0
            for entry in report.entries:
                if entry.archetype == archetype:
                    entry_share = entry.share
                    entry_n = entry.n
                    break
            blended_share += w * entry_share
            total_n += entry_n
        blended[archetype] = blended_share
        blended_n[archetype] = total_n

    # Normalise blended shares
    share_total = sum(blended.values())
    if share_total > 0:
        normalised = {k: v / share_total for k, v in blended.items()}
    else:
        normalised = blended

    # Use the min_share from the first report
    first_report = next(iter(reports.values()))
    min_share = first_report.min_share
    total_decks = sum(r.total_decks for r in reports.values())
    unlabeled = sum(r.unlabeled for r in reports.values())

    # Build entries
    entries: list[MetaShareEntry] = []
    for archetype, share in normalised.items():
        n = blended_n[archetype]
        fringe = share < min_share
        entries.append(
            MetaShareEntry(
                archetype=archetype,
                share=share,
                n=n,
                tier=tier_for_sample(n),
                fringe=fringe,
            )
        )
    entries.sort(key=lambda e: e.share, reverse=True)

    # Format provenance label encoding the weights
    weight_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(weights.items()))
    provenance_label = f"blend({weight_str})"

    return MetaShareReport(
        definition=definition,
        provenance=provenance_label,
        entries=entries,
        total_decks=total_decks,
        unlabeled=unlabeled,
        min_share=min_share,
    )
