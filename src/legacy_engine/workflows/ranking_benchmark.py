"""Filesystem and DuckDB adapters for future-only ranking benchmark artifacts."""

from __future__ import annotations

from datetime import date
import hashlib
import os
from pathlib import Path
import tempfile

import duckdb

from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkFold,
    SnapshotManifest,
    TaxonomySnapshotManifest,
    content_sha256,
    validate_snapshot_manifest,
)
from legacy_engine.analytics.eras.run import run_eras
from legacy_engine.config import RULES_DIR
from legacy_engine.ingestion import store
from legacy_engine.ingestion.banlist import BAN_EVENTS

_RAW_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "tournaments": ("id", "name", "date", "uri", "format", "source", "provenance"),
    "decks": ("tournament_id", "deck_idx", "player", "result", "archetype", "variant"),
    "deck_cards": ("tournament_id", "deck_idx", "board", "name", "count"),
    "rounds": ("tournament_id", "match_idx", "player1", "player2", "result"),
    "standings": ("tournament_id", "rank", "player", "points", "wins", "losses", "draws"),
}


def _rows(con: duckdb.DuckDBPyConnection, table: str, columns: tuple[str, ...], cutoff: str):
    joined = table != "tournaments"
    event_column = "x.tournament_id" if joined else "x.id"
    query = (
        f"SELECT {', '.join('x.' + column for column in columns)} FROM {table} x "
        f"JOIN tournaments t ON t.id = {event_column} " if joined else
        f"SELECT {', '.join('x.' + column for column in columns)} FROM tournaments x "
    )
    if joined:
        query += "WHERE substr(t.date, 1, 10) < ? "
    else:
        query += "WHERE substr(x.date, 1, 10) < ? "
    query += "ORDER BY " + ", ".join(f"{index + 1}" for index in range(len(columns)))
    return con.execute(query, [cutoff]).fetchall()


def _tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        digest.update(b"absent")
        return digest.hexdigest()
    for item in sorted(file for file in path.rglob("*") if file.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_taxonomy_snapshot(path: Path, cutoff: str) -> tuple[TaxonomySnapshotManifest, Path]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"taxonomy snapshot missing manifest.json: {path}")
    manifest = TaxonomySnapshotManifest.model_validate_json(manifest_path.read_bytes())
    if date.fromisoformat(manifest.effective_at[:10]) > date.fromisoformat(cutoff):
        raise ValueError("taxonomy snapshot is later than the benchmark cutoff")
    rules_path = path / manifest.rules_manifest
    if not rules_path.exists():
        raise ValueError(f"taxonomy rules payload is missing: {rules_path}")
    actual = _tree_hash(rules_path) if rules_path.is_dir() else hashlib.sha256(rules_path.read_bytes()).hexdigest()
    if actual != manifest.rules_sha256:
        raise ValueError("taxonomy rules hash mismatch")
    return manifest, rules_path


def _copy_training_facts(
    source: duckdb.DuckDBPyConnection,
    destination: duckdb.DuckDBPyConnection,
    cutoff: str,
) -> dict[str, list[tuple]]:
    facts: dict[str, list[tuple]] = {}
    for table, columns in _RAW_TABLE_COLUMNS.items():
        rows = _rows(source, table, columns, cutoff)
        facts[table] = rows
        if rows:
            placeholders = ",".join("?" for _ in columns)
            destination.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows,
            )
    referenced_cards = destination.execute(
        "SELECT DISTINCT name FROM deck_cards ORDER BY name"
    ).fetchall()
    cards: list[tuple] = []
    if referenced_cards:
        names = [row[0] for row in referenced_cards]
        placeholders = ",".join("?" for _ in names)
        cards = source.execute(
            f"SELECT name, mana_cost, cmc, type_line, colors, produced_mana, oracle_text, "
            f"layout, is_land, power, toughness FROM cards WHERE name IN ({placeholders}) ORDER BY name",
            names,
        ).fetchall()
        if cards:
            destination.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", cards)
    facts["cards"] = cards
    return facts


def _validate_closure(con: duckdb.DuckDBPyConnection) -> None:
    for table in ("decks", "deck_cards", "rounds", "standings"):
        count = con.execute(
            f"SELECT count(*) FROM {table} x LEFT JOIN tournaments t "
            "ON t.id = x.tournament_id WHERE t.id IS NULL"
        ).fetchone()[0]
        if count:
            raise ValueError(f"snapshot referential closure failed for {table}: {count} orphan rows")
    card_orphans = con.execute(
        "SELECT count(*) FROM deck_cards dc LEFT JOIN cards c ON c.name=dc.name WHERE c.name IS NULL"
    ).fetchone()[0]
    if card_orphans:
        raise ValueError(f"snapshot has {card_orphans} deck-card rows without observed card metadata")


def build_origin_snapshot(
    source_db: Path,
    destination_db: Path,
    *,
    fold: BenchmarkFold,
    protocol_hash: str,
    taxonomy_mode: str = "retrospective-fixed-parent",
    taxonomy_snapshot: Path | None = None,
) -> SnapshotManifest:
    """Build an atomic, raw-facts-only pre-cutoff corpus and recompute its era ledger."""
    if source_db.resolve() == destination_db.resolve():
        raise ValueError("source and destination snapshot paths must differ")
    cutoff = fold.cutoff
    taxonomy_effective_at: str | None = None
    if taxonomy_mode == "contemporaneous":
        if taxonomy_snapshot is None:
            raise ValueError("contemporaneous taxonomy mode requires a dated taxonomy snapshot")
        taxonomy, rules_path = _load_taxonomy_snapshot(taxonomy_snapshot, cutoff)
        taxonomy_effective_at = taxonomy.effective_at
        rules_hash = taxonomy.rules_sha256
    elif taxonomy_mode == "retrospective-fixed-parent":
        if taxonomy_snapshot is not None:
            raise ValueError("retrospective-fixed-parent does not accept a taxonomy snapshot")
        rules_path = RULES_DIR
        rules_hash = _tree_hash(rules_path)
    else:
        raise ValueError(f"unknown taxonomy mode: {taxonomy_mode}")

    destination_db.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination_db.name}.", dir=destination_db.parent)
    os.close(fd)
    Path(temporary_name).unlink()
    source = duckdb.connect(str(source_db), read_only=True)
    destination = store.connect(temporary_name)
    try:
        store.init_schema(destination)
        facts = _copy_training_facts(source, destination, cutoff)
        destination.execute("UPDATE decks SET variant = NULL")
        _validate_closure(destination)
        events_as_of = tuple(event for event in BAN_EVENTS if event[0] <= date.fromisoformat(cutoff))
        run_eras(destination, ban_events=events_as_of)

        event_ids = [row[0] for row in facts["tournaments"]]
        labels = sorted((row[0], row[1], row[4]) for row in facts["decks"])
        card_names = [row[0] for row in facts["cards"]]
        max_date = max(row[2][:10] for row in facts["tournaments"]) if facts["tournaments"] else ""
        decisive = sum(
            bool(row[4]) and str(row[4]).strip().lower() not in {"0-0", "draw", "id", "bye"}
            for row in facts["rounds"]
        )
        serialized_bans = tuple((d.isoformat(), card, reason) for d, card, reason in events_as_of)
        manifest = SnapshotManifest(
            protocol_hash=protocol_hash,
            fold=fold,
            training_source_fingerprint=content_sha256({"tables": facts}),
            training_facts_sha256=content_sha256(facts),
            training_event_ids_sha256=content_sha256(event_ids),
            training_events=len(facts["tournaments"]),
            training_decks=len(facts["decks"]),
            training_decisive_matches=decisive,
            max_training_event_date=max_date,
            ban_ledger_sha256=content_sha256(serialized_bans),
            ban_events_as_of=serialized_bans,
            taxonomy_mode=taxonomy_mode,
            taxonomy_effective_at=taxonomy_effective_at,
            taxonomy_sha256=content_sha256(labels),
            rules_sha256=rules_hash,
            card_availability_sha256=content_sha256(card_names),
            degraded=taxonomy_mode == "retrospective-fixed-parent",
            reasons=(
                "retrospective fixed parent ontology; camps and families disabled",
                "card availability is observed-by-cutoff because release dates are unavailable",
            ) if taxonomy_mode == "retrospective-fixed-parent" else (
                "card availability is observed-by-cutoff because release dates are unavailable",
            ),
        )
        validate_snapshot_manifest(manifest)
        destination.execute("CHECKPOINT")
        destination.close()
        destination = None
        os.replace(temporary_name, destination_db)
        return manifest
    finally:
        source.close()
        if destination is not None:
            destination.close()
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()
