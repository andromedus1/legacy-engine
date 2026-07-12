"""Consensus baseline deck generation (mode 1).

Aggregates the field for an archetype: for each card, inclusion-% across that
archetype's decks in the target window × its modal count, then fills exactly
``main_size`` maindeck + ≤ ``side_size`` sideboard via a reconciliation pass.

Design (from feature spec § Architectural choice):
  1. Query per-board card frequencies (inclusion_pct, modal_count).
  2. Rank each board's cards by (inclusion_pct DESC, modal_count DESC).
  3. Assign modal counts top-down; when the running total would cross the cap,
     take the partial count that lands exactly on the cap.
  4. De-dupe cross-board: a card appearing in both boards keeps only the board
     where its inclusion_pct is higher (tie-breaks to maindeck).
  5. Validate via ``ingestion.banlist.validate_deck``.

The default window is the latest ban-regime (re-uses ``trends.regime_windows``).

Player filter (gated-additive — feature-strong-player-signal story 3):
  ``card_frequencies`` / ``build_consensus`` accept an optional ``players``
  (a ``set[str]`` of canonical player_ids) and ``alias_map``.  When both are
  ``None``, behaviour is byte-identical to the pre-filter baseline — no new SQL
  predicate is emitted.  When ``players`` is supplied, the ``deck_pool`` CTE gains:
    ``AND lower(trim(d.player)) IN (<resolved handle set>)``
  The player filter is applied *on top of* the existing window; no window widening
  ever occurs (regime-safety guarantee).  Thin strong+windowed pools degrade
  honestly: low ``sample_n`` + speculative tier + a loud banner on the
  ``GeneratedDeck``; the caller decides what to do with it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb

from legacy_engine.generation.models import GeneratedDeck
from legacy_engine.ingestion.banlist import current_banlist, validate_deck

log = logging.getLogger(__name__)

# Thin-pool floor for honest-degrade banner (same as confidence.py "evolving" gate).
_THIN_SAMPLE_FLOOR: int = 30


# ---------------------------------------------------------------------------
# Unit 2 — per-archetype card-frequency record + query
# ---------------------------------------------------------------------------

@dataclass
class CardFreq:
    """Per-card frequency stats for one archetype + board.

    ``inclusion_pct`` = decks_running / archetype_deck_count in the window.
    ``modal_count``   = the most common copy count across those decks
                        (ties resolved by taking the higher count).
    ``decks_running`` = raw count for the audit trail.
    """

    name: str
    inclusion_pct: float   # 0.0 .. 1.0
    modal_count: int       # ≥ 1
    decks_running: int     # how many archetype decks ran this card


def _latest_regime_window() -> tuple[str | None, str | None]:
    """Return (since, until) for the current (latest) ban-list regime.

    Reuses ``trends.regime_windows`` — the SSOT for dated B&R partitioning.
    The current regime is the last entry (since=last_ban_date, until=None).
    """
    from legacy_engine.analytics.trends import regime_windows

    windows = regime_windows()
    # The last window is always the "current" regime (until=None).
    latest = windows[-1]
    since = latest.since.isoformat() if latest.since else None
    until = latest.until.isoformat() if latest.until else None
    return since, until


def entity_era_window(con: duckdb.DuckDBPyConnection, archetype: str) -> tuple[str | None, str | None, str]:
    """Era-aware default window for one archetype's consensus/card-frequency generation
    (epic-stable-era-windows-consumption Unit 4 — the consensus/card-frequency family's own
    default, distinct from `analytics.eras.consume.era_horizons`'s ban-only-via-
    `archetype_valid_since` fallback used by the adaptive MATCHUP matrix).

    Resolution:
      - Absent entirely from `entity_eras` (never analyzed — no era run has covered this
        archetype, or the table itself is missing/empty) -> the EXACT pre-epic fallback:
        `_latest_regime_window()`, byte-for-byte identical to today's behavior; label =
        ``"ban regime"``.
      - Present with a `stable_since` date -> ``[stable_since, now)``; label = the winning
        boundary's attribution trigger (a ban:/release:/unattributed detail).
      - Present with `stable_since=None` (analyzed, undisturbed) -> full corpus (``None, None``)
        — undisturbed composition IS solid (S2-checked); label = ``"undisturbed — full corpus"``.

    Returns ``(since, until, label)``; ``until`` is always ``None`` (open-ended: "now").
    """
    from legacy_engine.analytics.eras.store import read_entity_eras

    stored = read_entity_eras(con).get(archetype)
    if stored is None:
        since, until = _latest_regime_window()
        return since, until, "ban regime"
    if stored.stable_since is None:
        return None, None, "undisturbed — full corpus"

    trigger: str | None = None
    for b in stored.boundaries:
        if b.bh_accepted and not b.floor_rejected and b.date == stored.stable_since:
            trigger = b.attribution.detail if b.attribution is not None else None
            break
    return stored.stable_since, None, (trigger or "disturbance detected")


def _resolve_player_handles(
    players: set[str],
    alias_map: dict[str, str] | None,
) -> set[str]:
    """Expand a set of player_ids into the full set of normalized handles to match.

    For each player_id in ``players``, collect all handle_norm keys in ``alias_map``
    that map to it, plus the player_id itself (which may be a normalized handle in the
    un-curated case).  Returns the union of all resolved handles — these are what
    ``lower(trim(d.player))`` is compared against in the SQL CTE.

    When ``alias_map`` is None or empty, each player_id in ``players`` is treated as
    its own handle (identity resolution: no aliases → direct match).
    """
    from legacy_engine.analytics.match_results import normalize_player

    handles: set[str] = set()
    for pid in players:
        # The player_id itself, normalized, is always a valid match key.
        norm_pid = normalize_player(pid)
        if norm_pid:
            handles.add(norm_pid)
        # Plus any alias handles that resolve to this player_id.
        if alias_map:
            for handle_norm, mapped_pid in alias_map.items():
                if mapped_pid == pid:
                    handles.add(handle_norm)
    return handles


def card_frequencies(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    board: str,
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    variant: str | None = None,
    players: set[str] | None = None,
    alias_map: dict[str, str] | None = None,
) -> list[CardFreq]:
    """Per-card inclusion frequency for ``archetype`` in ``board`` over a date window.

    ``board`` must be ``"main"`` or ``"side"`` (the values stored in ``deck_cards.board``).

    Window defaults to the latest ban-regime when both ``since`` and ``until`` are
    ``None`` (caller passes both as None to trigger the default).

    ``variant`` optionally filters to decks with ``decks.variant = variant`` (exact match).
    ``None`` → no variant filter (unchanged, gated-additive contract).

    ``players`` optionally restricts the pool to decks registered by a specific set of
    canonical player_ids.  ``alias_map`` (``{handle_norm: player_id}``) is used to expand
    each player_id into its full set of normalized handles.  When ``players`` is ``None``,
    behaviour is **byte-identical** to the pre-filter baseline — no predicate added.

    Returns a list of ``CardFreq``, sorted by inclusion_pct DESC then modal_count DESC.
    Empty list when the archetype has no decks in the window.

    AC: a card run by 8/10 archetype decks at 4 copies →
        ``inclusion_pct=0.8, modal_count=4``.
    """
    if since is None and until is None:
        since, until, _window_label = entity_era_window(con, archetype)

    # Resolve the player filter into a flat set of normalized handles.
    # When players is None, player_handles stays None (no SQL predicate).
    player_handles: set[str] | None = None
    if players is not None:
        player_handles = _resolve_player_handles(players, alias_map)
        if not player_handles:
            # Players set is non-None but resolved to nothing → empty result.
            log.debug(
                "card_frequencies: players=%r resolved to zero handles; returning []",
                players,
            )
            return []

    # Build the player predicate snippet + param list.
    # Gated-additive: when player_handles is None, no predicate and no extra params.
    if player_handles is not None:
        # Build "lower(trim(d.player)) IN (?, ?, ...)" with one ? per handle.
        ph_list = list(player_handles)
        ph_placeholders = ", ".join(["?" for _ in ph_list])
        player_clause = f" AND lower(trim(d.player)) IN ({ph_placeholders})"
    else:
        ph_list = []
        player_clause = ""

    # Count distinct archetype decks in the window (the denominator).
    arch_count_params = [
        archetype, provenance, provenance, since, since, until, until, variant, variant
    ] + ph_list
    arch_count_row = con.execute(
        f"""
        SELECT count(DISTINCT (d.tournament_id, d.deck_idx))
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        WHERE d.archetype = ?
          AND (? IS NULL OR t.provenance = ?)
          AND (? IS NULL OR t.date >= ?)
          AND (? IS NULL OR t.date < ?)
          AND (? IS NULL OR d.variant = ?)
          {player_clause}
        """,
        arch_count_params,
    ).fetchone()
    archetype_deck_count = int(arch_count_row[0]) if arch_count_row else 0

    if archetype_deck_count == 0:
        return []

    # Per-card: decks_running + modal_count (mode of dc.count across those decks).
    # We compute the mode as the count value with the highest frequency; ties go
    # to the higher count (ORDER BY freq DESC, dc.count DESC LIMIT 1 per card).
    pool_params = [
        archetype, provenance, provenance, since, since, until, until, variant, variant
    ] + ph_list + [board]
    rows = con.execute(
        f"""
        WITH deck_pool AS (
            SELECT d.tournament_id, d.deck_idx
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE d.archetype = ?
              AND (? IS NULL OR t.provenance = ?)
              AND (? IS NULL OR t.date >= ?)
              AND (? IS NULL OR t.date < ?)
              AND (? IS NULL OR d.variant = ?)
              {player_clause}
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
        ),
        modal AS (
            SELECT name,
                   first_value(count) OVER (
                       PARTITION BY name
                       ORDER BY freq DESC, count DESC
                       ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                   ) AS modal_count,
                   sum(freq) OVER (PARTITION BY name) AS decks_running
            FROM card_counts
        )
        SELECT DISTINCT name, modal_count, decks_running
        FROM modal
        ORDER BY decks_running DESC, modal_count DESC
        """,
        pool_params,
    ).fetchall()

    result: list[CardFreq] = []
    for name, modal_count, decks_running in rows:
        result.append(
            CardFreq(
                name=name,
                inclusion_pct=decks_running / archetype_deck_count,
                modal_count=int(modal_count),
                decks_running=int(decks_running),
            )
        )

    # Sort: inclusion_pct DESC, then modal_count DESC (stable for deterministic output).
    result.sort(key=lambda cf: (-cf.inclusion_pct, -cf.modal_count))
    return result


# ---------------------------------------------------------------------------
# Unit 3 — exactly-60 reconciliation + cross-board de-dupe (trickiest unit)
# ---------------------------------------------------------------------------

def _fill_board(freqs: list[CardFreq], target: int) -> dict[str, int]:
    """Greedy-fill a board to exactly ``target`` cards using ranked CardFreq.

    Algorithm (spec §Architectural choice):
      - Rank by (inclusion_pct DESC, modal_count DESC) — already sorted by caller.
      - Walk top-down assigning modal counts.
      - When the running total + modal_count would exceed the target, assign only
        the remaining slots (partial stack).
      - Stop when target is reached or the pool is exhausted.

    Returns a ``dict[str, int]`` summing to ≤ ``target``.  The caller validates
    that ≥60 cards were available; if the pool is exhausted before the target,
    the returned dict will sum to less than ``target`` (thin archetype).
    """
    board: dict[str, int] = {}
    remaining = target
    for cf in freqs:
        if remaining <= 0:
            break
        copies = min(cf.modal_count, remaining)
        if copies > 0:
            board[cf.name] = copies
            remaining -= copies
    return board


def _dedupe_cross_board(
    main: dict[str, int],
    side: dict[str, int],
    main_freqs: list[CardFreq],
    side_freqs: list[CardFreq],
) -> tuple[dict[str, int], dict[str, int]]:
    """Remove a card from the board where its inclusion_pct is lower.

    Tie-breaks to keeping the card in the maindeck (removes from sideboard).
    Returns ``(main, side)`` after de-duplication.
    """
    main_pct: dict[str, float] = {cf.name: cf.inclusion_pct for cf in main_freqs}
    side_pct: dict[str, float] = {cf.name: cf.inclusion_pct for cf in side_freqs}

    dupes = set(main) & set(side)
    for name in dupes:
        m_pct = main_pct.get(name, 0.0)
        s_pct = side_pct.get(name, 0.0)
        # Keep in the board where inclusion_pct is higher; tie → keep in main.
        if s_pct > m_pct:
            # Remove from main, keep in side.
            del main[name]
        else:
            # Remove from side, keep in main (default for ties).
            del side[name]

    return main, side


def build_consensus(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    main_size: int = 60,
    side_size: int = 15,
    variant: str | None = None,
    players: set[str] | None = None,
    alias_map: dict[str, str] | None = None,
) -> GeneratedDeck:
    """Build a consensus baseline deck for ``archetype``.

    Uses the windowed latest ban-regime as the default window (overridable via
    ``since``/``until``).  The returned ``GeneratedDeck`` has:

    * ``maindeck`` summing to exactly ``main_size`` (or less if the archetype pool
      is too thin — surface via low ``sample_n``).
    * ``sideboard`` summing to ≤ ``side_size``; may be empty for thin archetypes.
    * ``legality_errors`` from ``validate_deck``; empty = legal.

    ``variant`` optionally scopes the pool to decks with ``decks.variant = variant`` (exact
    match).  ``None`` → no variant filter (unchanged, gated-additive contract).

    ``players`` optionally restricts the pool to a set of canonical player_ids (strong-player
    filter).  ``alias_map`` resolves player_ids to their normalized handles.  When ``players``
    is ``None``, behaviour is **byte-identical** to the pre-filter baseline.

    When the player-filtered + windowed pool is thin (``sample_n`` < ``_THIN_SAMPLE_FLOOR``),
    a loud banner is added to ``legality_errors`` (the audit trail) and the ``GeneratedDeck``
    carries a low ``sample_n``; the window is **never** silently widened.

    Raises ``click.ClickException`` (via caller) for unknown archetypes — this
    function returns a ``GeneratedDeck`` with ``sample_n=0`` and a legality error.

    AC:
    - ``maindeck`` sums to exactly 60.
    - ``sideboard`` ≤ 15.
    - No card exceeds its copy limit.
    - No card double-listed across boards.
    - ``legality_errors == []`` for a real archetype (when unfiltered or pool not thin).
    - Thin archetype still returns a legal list and a low ``sample_n``.
    - ``players=None`` → byte-identical to the unfiltered call.
    """
    # Resolve the effective window.
    if since is None and until is None:
        effective_since, effective_until, _window_label = entity_era_window(con, archetype)
    else:
        effective_since, effective_until = since, until

    # Query card frequencies for each board.
    main_freqs = card_frequencies(
        con, archetype, board="main",
        since=effective_since, until=effective_until, provenance=provenance,
        variant=variant, players=players, alias_map=alias_map,
    )
    side_freqs = card_frequencies(
        con, archetype, board="side",
        since=effective_since, until=effective_until, provenance=provenance,
        variant=variant, players=players, alias_map=alias_map,
    )

    # Derive sample_n from main-board query (decks with at least one main card).
    # Use the max decks_running * (1 / inclusion_pct) approximation — or re-query.
    # Simpler: take the first CardFreq's decks_running / inclusion_pct if available.
    if main_freqs:
        # Reconstruct archetype_deck_count from the most-played card.
        sample_n = round(main_freqs[0].decks_running / main_freqs[0].inclusion_pct)
    elif side_freqs:
        sample_n = round(side_freqs[0].decks_running / side_freqs[0].inclusion_pct)
    else:
        sample_n = 0

    log.debug(
        "build_consensus: archetype=%r window=[%s, %s) sample_n=%d "
        "main_pool=%d side_pool=%d players_filter=%s",
        archetype, effective_since, effective_until, sample_n,
        len(main_freqs), len(side_freqs),
        f"{len(players)} player(s)" if players is not None else "none",
    )

    if sample_n == 0:
        # Unknown archetype or player-filtered pool is empty —
        # return an empty deck with a legality error.
        if players is not None:
            error_msg = (
                f"archetype {archetype!r} has no decks in the window "
                f"for the requested player set ({len(players)} player(s)); "
                "window NOT widened (regime-safety guarantee) — use --all-time for an "
                "explicit wider window, or remove the player filter"
            )
        else:
            error_msg = f"archetype {archetype!r} has no decks in the window"
        return GeneratedDeck(
            archetype=archetype,
            maindeck={},
            sideboard={},
            window=(effective_since, effective_until),
            sample_n=0,
            legality_errors=[error_msg],
        )

    # Fill each board greedily to the target.
    main = _fill_board(main_freqs, main_size)
    side = _fill_board(side_freqs, side_size)

    # De-dupe cross-board: keep a card only in the board where it has higher inclusion_pct.
    main, side = _dedupe_cross_board(main, side, main_freqs, side_freqs)

    # After de-dupe the maindeck may be short (removed cards freed slots).
    # Top-up from the remaining main_freqs (cards not yet in main, preserving ranking).
    # CRITICAL: exclude cards currently in the OTHER board, or top-up re-introduces the very
    # cross-board duplicate _dedupe_cross_board just removed.
    in_main = set(main)
    remaining_main = [cf for cf in main_freqs if cf.name not in in_main and cf.name not in side]
    current_main_total = sum(main.values())
    if current_main_total < main_size and remaining_main:
        top_up = _fill_board(remaining_main, main_size - current_main_total)
        main.update(top_up)

    # Similarly top-up the sideboard after de-dupe — excluding cards now in main (incl. any
    # just added by the main top-up above) so the boards stay disjoint.
    in_side = set(side)
    remaining_side = [cf for cf in side_freqs if cf.name not in in_side and cf.name not in main]
    current_side_total = sum(side.values())
    if current_side_total < side_size and remaining_side:
        top_up = _fill_board(remaining_side, side_size - current_side_total)
        side.update(top_up)

    # Validate against the current ban snapshot.
    snapshot = current_banlist()
    errors = validate_deck(main, side, snapshot)

    # Thin-pool honest-degrade banner (gated on player filter being active).
    # When the player-filtered pool is below the evolving floor, attach a loud banner
    # to the legality_errors list so every caller surfaces it.  The window is NEVER
    # widened — that invariant is the regime-safety guarantee.
    if players is not None and sample_n < _THIN_SAMPLE_FLOOR:
        banner = (
            f"⚠ THIN PLAYER-FILTERED POOL: only {sample_n} deck(s) in window "
            f"[{effective_since or 'open'}, {effective_until or 'current'}) "
            f"for {len(players)} player(s) — modal card choices are speculative; "
            "window NOT widened (use --all-time to explicitly widen)"
        )
        log.warning("build_consensus: %s", banner)
        errors = list(errors) + [banner]

    return GeneratedDeck(
        archetype=archetype,
        maindeck=main,
        sideboard=side,
        window=(effective_since, effective_until),
        sample_n=sample_n,
        legality_errors=errors,
    )
