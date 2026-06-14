"""Per-card copy-count distribution + deck-doctor diff (mode 2b of deck-gen).

Architecture (option B from feature spec):
  1. ``card_count_distributions`` — DB primitive (runs ONCE). Returns the full
     per-count distribution dict for every card in an archetype+board over a window.
     Crucially the 0-bucket (decks that DON'T run the card) is included so fractions
     sum to ~1.0 over the whole archetype pool.
  2. ``diff_deck_vs_field`` — PURE comparison (no DB). Compares the user's counts
     against the field distributions and emits ``CardCountDelta`` records.
  3. ``build_deck_doctor_report`` — orchestrator: wires 1 + 2 per board.

Window semantics: defaults to the latest ban regime via the SAME
``_latest_regime_window()`` that ``generate consensus`` uses — single SSOT.
The parallel is deliberate: both surfaces are deck-based, both window the same way.

Design doc: .work/active/features/feature-card-count-outlier-advisor.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Outlier-floor calibration note
# ---------------------------------------------------------------------------
# Four hand-validated examples drive the default:
#   - Orcish Bowmasters at 4 → 23% of field: user should be ON CONSENSUS (23% is a real camp).
#   - Murktide Regent at 2 → 79% of field: clearly on consensus.
#   - Lands at 18 → 5% of field: clearly an outlier.
#   - Daze at 2 → 18% of field: the design doc says "flagged as the one off-consensus count."
#
# With floor=0.15: Daze at 18% would NOT be flagged (18 >= 15), which contradicts the item.
# With floor=0.20: Daze at 18% IS flagged (18 < 20), and Bowmasters at 23% is NOT flagged
#   (23 >= 20 — "a real camp").  This satisfies all four examples simultaneously.
#
# Choice: 0.20. Bowmasters stays on-consensus (23% > 20%); Daze is flagged (18% < 20%);
# Lands is flagged (5% << 20%); Murktide is on-consensus (79% >> 20%).
#
_OUTLIER_SHARE_FLOOR: float = 0.20


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CardCountDist:
    """Field copy-count distribution for one card in one archetype+board over a window.

    ``dist`` maps copy_count -> fraction of the archetype's decks running EXACTLY that many.
    Counts of 0 (decks that DON'T run the card) ARE included so fractions sum to 1.0 over the
    full archetype pool — this is what makes "11% run 0 copies" (Murktide) expressible.
    ``modal_count`` = the count with the highest share (ties -> higher count, matching CardFreq).
    ``decks_total`` = archetype deck count in the window (the denominator / sample_n).
    """
    name: str
    board: str                     # "main" | "side"
    dist: dict[int, float]         # copy_count -> fraction (sums to ~1.0 incl. the 0 bucket)
    modal_count: int
    decks_total: int


@dataclass(frozen=True)
class CardCountDelta:
    """One card's user-count-vs-field comparison."""
    name: str
    board: str
    user_count: int                # copies in the user's list (0 if absent but field runs it)
    field_modal: int               # field's modal count
    field_dist: dict[int, float]   # the full distribution (for rendering "68% at 3 / 23% at 4")
    delta: int                     # user_count - field_modal (signed magnitude)
    user_share: float              # fraction of field running EXACTLY user_count (0.0 if none)
    is_outlier: bool               # user's count is below the outlier-share gate (see policy)
    decks_total: int               # denominator (drives the confidence tier)


@dataclass(frozen=True)
class DeckDoctorReport:
    archetype: str
    window: tuple[str | None, str | None]
    decks_total: int               # sample_n for the whole report
    deltas: list[CardCountDelta]   # sorted: outliers first (by |delta| desc), then on-consensus
    not_in_field: list[str]        # user cards the field never runs in this archetype+board
    board: str


# ---------------------------------------------------------------------------
# Unit 1 — DB primitive
# ---------------------------------------------------------------------------

def card_count_distributions(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    board: str,
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    apply_default_window: bool = True,
) -> dict[str, CardCountDist]:
    """Heavy DB path (runs ONCE). Per-card full copy-count distribution for an archetype+board.

    Window defaults to the latest ban regime when since AND until are both None and
    ``apply_default_window=True`` (same trigger as ``card_frequencies``). Pass
    ``apply_default_window=False`` for an explicit full-corpus query.

    The 0-bucket is computed as ``decks_total - sum(running_freq)`` / ``decks_total`` so the
    distribution is over the WHOLE archetype pool, not just decks that run the card.

    Returns ``{}`` when the archetype has no decks in the window.

    The SQL CTE shape mirrors ``card_frequencies`` exactly for consistent windowing semantics.
    """
    if since is None and until is None and apply_default_window:
        from legacy_engine.generation.consensus import _latest_regime_window
        since, until = _latest_regime_window()

    # Count distinct archetype decks in the window (the denominator).
    arch_count_row = con.execute(
        """
        SELECT count(DISTINCT (d.tournament_id, d.deck_idx))
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        WHERE d.archetype = ?
          AND (? IS NULL OR t.provenance = ?)
          AND (? IS NULL OR t.date >= ?)
          AND (? IS NULL OR t.date < ?)
        """,
        [archetype, provenance, provenance, since, since, until, until],
    ).fetchone()
    decks_total = int(arch_count_row[0]) if arch_count_row else 0

    if decks_total == 0:
        return {}

    # Per-card: ALL (count, freq) rows — NOT collapsed to modal — so we keep the full distribution.
    rows = con.execute(
        """
        WITH deck_pool AS (
            SELECT d.tournament_id, d.deck_idx
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE d.archetype = ?
              AND (? IS NULL OR t.provenance = ?)
              AND (? IS NULL OR t.date >= ?)
              AND (? IS NULL OR t.date < ?)
        ),
        card_counts AS (
            SELECT dc.name,
                   dc.count,
                   count(*) AS freq
            FROM deck_pool dp
            JOIN deck_cards dc
              ON dc.tournament_id = dp.tournament_id
             AND dc.deck_idx      = dp.deck_idx
            WHERE dc.board = ?
            GROUP BY dc.name, dc.count
        )
        SELECT name, count, freq
        FROM card_counts
        ORDER BY name, count
        """,
        [archetype, provenance, provenance, since, since, until, until, board],
    ).fetchall()

    # Group rows by card name.
    from collections import defaultdict
    raw: dict[str, dict[int, int]] = defaultdict(dict)  # name -> {count -> freq}
    for name, count, freq in rows:
        raw[name][int(count)] = int(freq)

    result: dict[str, CardCountDist] = {}
    for name, count_freqs in raw.items():
        # Build fractions (over the WHOLE deck pool, including the 0-bucket).
        running_total = sum(count_freqs.values())
        zero_bucket_count = decks_total - running_total

        dist: dict[int, float] = {}
        for cnt, freq in sorted(count_freqs.items()):
            dist[cnt] = freq / decks_total
        if zero_bucket_count > 0:
            dist[0] = zero_bucket_count / decks_total

        # Modal count = the count with the highest fraction; ties -> higher count.
        modal_count = max(
            dist.keys(),
            key=lambda c: (dist[c], c),
        )

        result[name] = CardCountDist(
            name=name,
            board=board,
            dist=dist,
            modal_count=modal_count,
            decks_total=decks_total,
        )

    log.debug(
        "card_count_distributions: archetype=%r board=%r window=[%s,%s) cards=%d decks_total=%d",
        archetype, board, since, until, len(result), decks_total,
    )
    return result


# ---------------------------------------------------------------------------
# Unit 2 — pure comparison (no DB)
# ---------------------------------------------------------------------------

def diff_deck_vs_field(
    user_counts: dict[str, int],          # parsed mainboard OR sideboard (name -> copies)
    dists: dict[str, CardCountDist],      # from card_count_distributions (same board)
    *,
    board: str,
    outlier_floor: float = _OUTLIER_SHARE_FLOOR,
) -> tuple[list[CardCountDelta], list[str]]:
    """PURE comparison (no DB). Returns (deltas, not_in_field).

    For every card in EITHER the user's list or the field dists:
      - field_dist/modal/decks_total from dists[name] (or skip if user-only -> not_in_field).
      - user_share = field_dist.get(user_count, 0.0).
      - is_outlier = (name in dists) AND user_share < outlier_floor AND user_count != field_modal.
    A card the user runs that the field never runs in this archetype goes to not_in_field
    (never an 'outlier' — there's no distribution to be off of).
    Deterministic ordering for stable output (sort by name within each group).
    """
    deltas: list[CardCountDelta] = []
    not_in_field: list[str] = []

    # All cards: union of user cards and field cards, but treat user-only cards separately.
    all_names = sorted(set(user_counts) | set(dists))

    for name in all_names:
        user_count = user_counts.get(name, 0)
        if name not in dists:
            # User runs a card the field never runs → not_in_field (only if user actually runs it).
            if user_count > 0:
                not_in_field.append(name)
            continue

        dist_obj = dists[name]
        field_modal = dist_obj.modal_count
        field_dist = dist_obj.dist
        decks_total = dist_obj.decks_total
        user_share = field_dist.get(user_count, 0.0)
        delta = user_count - field_modal
        is_outlier = user_share < outlier_floor and user_count != field_modal

        deltas.append(CardCountDelta(
            name=name,
            board=board,
            user_count=user_count,
            field_modal=field_modal,
            field_dist=field_dist,
            delta=delta,
            user_share=user_share,
            is_outlier=is_outlier,
            decks_total=decks_total,
        ))

    # Sort: outliers first (by |delta| desc, then name), then on-consensus (by |delta| desc).
    outliers = sorted(
        [d for d in deltas if d.is_outlier],
        key=lambda d: (-abs(d.delta), d.name),
    )
    on_consensus = sorted(
        [d for d in deltas if not d.is_outlier],
        key=lambda d: (-abs(d.delta), d.name),
    )

    return outliers + on_consensus, sorted(not_in_field)


# ---------------------------------------------------------------------------
# Unit 3 — orchestrator
# ---------------------------------------------------------------------------

def build_deck_doctor_report(
    con: duckdb.DuckDBPyConnection,
    user_main: dict[str, int],
    user_side: dict[str, int],
    archetype: str,
    *,
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    board: str = "main",
    apply_default_window: bool = True,
) -> DeckDoctorReport:
    """Orchestrator: runs card_count_distributions ONCE per requested board, wires diff_deck_vs_field,
    assembles the report.

    When ``apply_default_window=True`` (the default), resolves the window via
    ``_latest_regime_window()`` when both since and until are None — giving the
    same default as ``generate consensus``. Pass ``apply_default_window=False``
    when the caller has explicitly chosen a full-corpus window (e.g. CLI ``--all-time``),
    so (None, None) is passed to the DB unchanged.
    """
    # Resolve the default window so the report's window field is always populated.
    effective_since = since
    effective_until = until
    if effective_since is None and effective_until is None and apply_default_window:
        from legacy_engine.generation.consensus import _latest_regime_window
        effective_since, effective_until = _latest_regime_window()

    user_counts = user_main if board == "main" else user_side

    dists = card_count_distributions(
        con,
        archetype,
        board=board,
        since=effective_since,
        until=effective_until,
        provenance=provenance,
        # When the orchestrator's default window was disabled, the effective_since/until
        # may both be None (full corpus intent) — tell the DB primitive not to re-apply
        # the default either.
        apply_default_window=False,  # orchestrator has already resolved (or chosen full corpus)
    )

    # decks_total from any distribution (all share the same denominator) or 0 if empty.
    decks_total = next(iter(dists.values())).decks_total if dists else 0

    deltas, not_in_field = diff_deck_vs_field(user_counts, dists, board=board)

    return DeckDoctorReport(
        archetype=archetype,
        window=(effective_since, effective_until),
        decks_total=decks_total,
        deltas=deltas,
        not_in_field=not_in_field,
        board=board,
    )
