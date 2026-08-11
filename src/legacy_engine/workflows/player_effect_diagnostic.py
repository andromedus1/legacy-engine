"""DuckDB and filesystem adapters for the experimental player-effect diagnostic."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import duckdb

from legacy_engine.analytics.match_results import normalize_player, parse_match_result
from legacy_engine.analytics.players.diagnostic import (
    IdentityReplayMode,
    PilotRegistration,
    PlayerIdentitySnapshotManifest,
    scoped_player_key,
)
from legacy_engine.models.base import LegacyEngineModel


class _PlayerTrainingMatch(LegacyEngineModel):
    match_id: str
    event_id: str
    event_date: str
    provenance: str
    subject: str
    opponent: str
    subject_player_key: str | None
    opponent_player_key: str | None
    subject_won: bool


def load_player_identity_snapshot(
    path: Path | None,
    *,
    mode: IdentityReplayMode,
    cutoff: str,
) -> tuple[dict[str, str], str | None]:
    """Load a dated curated alias snapshot or enforce provenance-local replay."""
    if mode == "provenance-local-handle":
        if path is not None:
            raise ValueError("provenance-local identity mode does not accept an alias snapshot")
        return {}, None
    if path is None:
        raise ValueError("dated-curated-alias mode requires an identity snapshot")
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"identity snapshot missing manifest.json: {path}")
    manifest = PlayerIdentitySnapshotManifest.model_validate_json(manifest_path.read_bytes())
    if date.fromisoformat(manifest.effective_at[:10]) > date.fromisoformat(cutoff):
        raise ValueError("identity snapshot is later than the diagnostic cutoff")
    aliases_path = path / manifest.aliases_file
    if not aliases_path.is_file():
        raise ValueError(f"identity alias payload is missing: {aliases_path}")
    payload = aliases_path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != manifest.aliases_sha256:
        raise ValueError("identity alias payload hash mismatch")
    raw = json.loads(payload)
    aliases: dict[str, str] = {}
    for player_id, entry in sorted((raw.get("players") or {}).items()):
        for handle in entry.get("handles") or ():
            normalized = normalize_player(handle)
            if not normalized:
                raise ValueError("identity snapshot contains a blank normalized handle")
            if normalized in aliases:
                raise ValueError(f"identity snapshot contains duplicate normalized handle: {normalized}")
            aliases[normalized] = str(player_id)
    return aliases, actual


def load_player_diagnostic_rows(
    db: Path,
    *,
    until: str,
    identity_mode: IdentityReplayMode,
    identity_snapshot: Path | None,
) -> tuple[tuple[PilotRegistration, ...], tuple[_PlayerTrainingMatch, ...], str | None]:
    """Load cutoff-safe registrations and decisive parent matches with scoped identity keys."""
    aliases, identity_sha = load_player_identity_snapshot(
        identity_snapshot, mode=identity_mode, cutoff=until,
    )
    con = duckdb.connect(str(db), read_only=True)
    try:
        deck_rows = con.execute(
            """
            SELECT d.tournament_id, substr(t.date,1,10), coalesce(t.provenance,''),
                   d.deck_idx, d.player, d.archetype, d.variant
            FROM decks d JOIN tournaments t ON t.id=d.tournament_id
            WHERE substr(t.date,1,10) < ?
            ORDER BY t.date, d.tournament_id, d.deck_idx
            """,
            [until],
        ).fetchall()
        round_rows = con.execute(
            """
            SELECT r.tournament_id, r.match_idx, substr(t.date,1,10),
                   coalesce(t.provenance,''), r.player1, r.player2, r.result
            FROM rounds r JOIN tournaments t ON t.id=r.tournament_id
            WHERE substr(t.date,1,10) < ?
            ORDER BY t.date, r.tournament_id, r.match_idx
            """,
            [until],
        ).fetchall()
    finally:
        con.close()

    normalized_counts: dict[tuple[str, str], int] = {}
    parent_by_handle: dict[tuple[str, str], str | None] = {}
    raw_counts: dict[tuple[str, str], int] = {}
    parent_by_raw: dict[tuple[str, str], str | None] = {}
    for event_id, _event_date, _provenance, _deck_idx, player, _parent, _variant in deck_rows:
        raw_key = (str(event_id), str(player or ""))
        raw_counts[raw_key] = raw_counts.get(raw_key, 0) + 1
        parent_by_raw[raw_key] = str(_parent) if _parent is not None else None
        normalized = normalize_player(player)
        if normalized:
            key = (str(event_id), normalized)
            normalized_counts[key] = normalized_counts.get(key, 0) + 1
            parent_by_handle[key] = str(_parent) if _parent is not None else None

    def identity(event_id: str, handle: str | None, provenance: str):
        normalized = normalize_player(handle)
        if not normalized:
            return None, None, "blank-handle"
        if normalized_counts.get((event_id, normalized), 0) > 1:
            return None, None, "ambiguous-within-event-handle"
        key, basis = scoped_player_key(handle, provenance, aliases)
        return key, basis, None

    registrations: list[PilotRegistration] = []
    for event_id, event_date, provenance, _deck_idx, player, parent, variant in deck_rows:
        key, basis, reason = identity(str(event_id), player, str(provenance))
        parent_label = str(parent) if parent is not None else "<unclassified>"
        if parent is None:
            reason = reason or "unclassified-parent"
        configuration = f"{parent_label}::{variant if variant is not None else 'unlabeled'}"
        registrations.append(PilotRegistration(
            event_id=str(event_id), event_date=str(event_date), provenance=str(provenance),
            parent=parent_label, configuration=configuration, player_key=key,
            identity_basis=basis, exclusion_reason=reason,
        ))

    matches: list[_PlayerTrainingMatch] = []
    for event_id, match_idx, event_date, provenance, p1, p2, result in round_rows:
        outcome = parse_match_result(result)
        key1_lookup = (str(event_id), normalize_player(p1))
        key2_lookup = (str(event_id), normalize_player(p2))
        a1 = parent_by_handle.get(key1_lookup) if normalized_counts.get(key1_lookup) == 1 else None
        a2 = parent_by_handle.get(key2_lookup) if normalized_counts.get(key2_lookup) == 1 else None
        if not normalize_player(p1):
            raw_key = (str(event_id), str(p1 or ""))
            a1 = parent_by_raw.get(raw_key) if raw_counts.get(raw_key) == 1 else None
        if not normalize_player(p2):
            raw_key = (str(event_id), str(p2 or ""))
            a2 = parent_by_raw.get(raw_key) if raw_counts.get(raw_key) == 1 else None
        if outcome is None or outcome.winner is None or a1 is None or a2 is None or a1 == a2:
            continue
        key1, _basis1, _reason1 = identity(str(event_id), p1, str(provenance))
        key2, _basis2, _reason2 = identity(str(event_id), p2, str(provenance))
        if str(a2) < str(a1):
            subject, opponent = str(a2), str(a1)
            subject_key, opponent_key = key2, key1
            won = outcome.winner == "p2"
        else:
            subject, opponent = str(a1), str(a2)
            subject_key, opponent_key = key1, key2
            won = outcome.winner == "p1"
        matches.append(_PlayerTrainingMatch(
            match_id=f"{event_id}:{match_idx}", event_id=str(event_id),
            event_date=str(event_date), provenance=str(provenance), subject=subject,
            opponent=opponent, subject_player_key=subject_key,
            opponent_player_key=opponent_key, subject_won=won,
        ))
    return tuple(registrations), tuple(matches), identity_sha
