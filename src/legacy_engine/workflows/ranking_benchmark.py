"""Filesystem and DuckDB adapters for future-only ranking benchmark artifacts."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import os
from pathlib import Path
import tempfile
import subprocess

import duckdb

from legacy_engine.advisory.ranking_benchmark import (
    ESTIMATOR_REGISTRY,
    BenchmarkFold,
    BenchmarkProtocol,
    FrozenMatchupPrediction,
    FrozenOriginPredictions,
    FrozenRecommendation,
    HeldoutMatch,
    SnapshotManifest,
    TaxonomySnapshotManifest,
    content_sha256,
    project_matchup_probability,
    protocol_sha256,
    validate_snapshot_manifest,
)
from legacy_engine.advisory.ranking_measurement import (
    RankingCellMeasurement,
    RankingCellSource,
    measure_lean_agency,
    measure_ranking_row,
    measure_variant_row,
    methodology_variant_specs,
    select_ranking_cell,
)
from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.eras.consume import clamp_pair_window
from legacy_engine.analytics.eras.run import run_eras
from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.analytics.match_results import normalize_player, parse_match_result
from legacy_engine.analytics.matchup import build_adaptive_matrix, build_matrix
from legacy_engine.archetype.labeler import label_decks
from legacy_engine.archetype.matcher import classify
from legacy_engine.archetype.rules import load_ruleset
from legacy_engine.colors import compute_deck_colors
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


def validate_frozen_taxonomy(
    predictions: FrozenOriginPredictions,
    taxonomy_snapshot: Path | None,
) -> None:
    """Bind held-out classification to the taxonomy identity frozen at prediction time."""
    if predictions.taxonomy_mode == "retrospective-fixed-parent":
        if taxonomy_snapshot is not None:
            raise ValueError("retrospective benchmark does not accept a taxonomy snapshot")
        return
    if taxonomy_snapshot is None:
        raise ValueError("contemporaneous evaluation requires a taxonomy snapshot")
    manifest, _rules_path = _load_taxonomy_snapshot(taxonomy_snapshot, predictions.fold.cutoff)
    if (
        manifest.effective_at != predictions.taxonomy_effective_at
        or manifest.rules_sha256 != predictions.rules_sha256
    ):
        raise ValueError("evaluation taxonomy identity does not match frozen predictions")


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
        if taxonomy_mode == "contemporaneous":
            if not rules_path.is_dir():
                raise ValueError("contemporaneous taxonomy rules payload must be a rules directory")
            ruleset = load_ruleset(rules_path)
            label_decks(destination, ruleset, lambda name: store.load_card(destination, name))
        destination.execute("UPDATE decks SET variant = NULL")
        _validate_closure(destination)
        events_as_of = tuple(event for event in BAN_EVENTS if event[0] <= date.fromisoformat(cutoff))
        run_eras(destination, ban_events=events_as_of)

        event_ids = [row[0] for row in facts["tournaments"]]
        labels = destination.execute(
            "SELECT tournament_id, deck_idx, archetype FROM decks ORDER BY 1, 2"
        ).fetchall()
        if taxonomy_mode == "contemporaneous" and taxonomy.labels_sha256 is not None:
            if content_sha256(labels) != taxonomy.labels_sha256:
                raise ValueError("taxonomy precomputed label hash mismatch")
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


def _benchmark_rows(con: duckdb.DuckDBPyConnection, protocol: BenchmarkProtocol, manifest: SnapshotManifest):
    """Assemble parent-only rows through the production measurement ledger."""
    cutoff = date.fromisoformat(manifest.fold.cutoff)
    field_since = manifest.fold.regime_start
    field_rows = con.execute(
        "SELECT archetype, count(*) FROM decks d JOIN tournaments t ON t.id=d.tournament_id "
        "WHERE d.archetype IS NOT NULL AND substr(t.date,1,10)>=? AND substr(t.date,1,10)<? "
        "GROUP BY archetype ORDER BY archetype",
        [field_since, cutoff.isoformat()],
    ).fetchall()
    total = sum(row[1] for row in field_rows)
    shares = {str(label): count / total for label, count in field_rows} if total else {}
    actions = tuple(sorted(label for label, share in shares.items() if share >= protocol.action_min_share))
    if not actions:
        raise ValueError("origin snapshot has no eligible parent archetypes in its frozen field")

    ban_events = tuple((date.fromisoformat(d), card, reason) for d, card, reason in manifest.ban_events_as_of)
    horizons = archetype_valid_since(con, list(actions), ban_events=ban_events)
    adaptive = build_adaptive_matrix(
        con, min_row_share=protocol.action_min_share, horizons=horizons,
    )
    fallback_dates = {None} | {value for value in horizons.values() if value is not None}
    fallback = {
        since: build_matrix(con, min_row_share=protocol.action_min_share, since=since).cells
        for since in sorted(fallback_dates, key=lambda value: value or "")
    }
    rows: dict[str, tuple[tuple[RankingCellMeasurement, ...], object]] = {}
    top_k = min(8, len(actions))
    for subject in actions:
        cells: list[RankingCellMeasurement] = []
        strict: dict[str, RankingCellSource] = {}
        for opponent in actions:
            window_since = adaptive.cell_windows.get((subject, opponent))
            window = clamp_pair_window(
                subject, opponent, subject_since=adaptive.valid_since.get(subject),
                opponent_since=adaptive.valid_since.get(opponent), requested_since=window_since,
            )
            era_cell = adaptive.matrix.cells.get((subject, opponent))
            era_source = (
                RankingCellSource(kind="era", since=window_since, cell=era_cell, pair_window=window)
                if era_cell is not None else None
            )
            fallback_since = max(
                (value for value in (horizons.get(subject), horizons.get(opponent)) if value is not None),
                default=None,
            )
            fallback_cell = fallback[fallback_since].get((subject, opponent))
            fallback_window = clamp_pair_window(
                subject, opponent, subject_since=horizons.get(subject),
                opponent_since=horizons.get(opponent), requested_since=fallback_since,
            )
            fallback_source = (
                RankingCellSource(
                    kind="ban-fallback" if fallback_since else "full-corpus",
                    since=fallback_since, cell=fallback_cell, pair_window=fallback_window,
                ) if fallback_cell is not None else None
            )
            measurement = select_ranking_cell(
                subject, opponent, shares[opponent], era=era_source, fallback=fallback_source,
                ground_n=8,
            )
            cells.append(measurement)
            if measurement.selected is not None:
                strict[opponent] = measurement.selected
        typed_cells = tuple(cells)
        row = measure_ranking_row(
            subject, typed_cells, top_k=top_k, cover_min=0.8, strict_common_sources=strict,
        )
        rows[subject] = (typed_cells, row)
    return actions, shares, rows


def _baseline_inputs(con: duckdb.DuckDBPyConnection, protocol: BenchmarkProtocol, manifest: SnapshotManifest):
    cutoff = date.fromisoformat(manifest.fold.cutoff)
    recent_since = (cutoff - timedelta(days=28)).isoformat()
    recent = compute_match_results(con, since=recent_since, until=cutoff.isoformat())
    full = compute_match_results(con, until=cutoff.isoformat())
    conversion_rows = con.execute(
        """
        WITH event_size AS (
          SELECT tournament_id, count(*) AS n FROM decks GROUP BY tournament_id
        ), labeled AS (
          SELECT d.archetype, d.tournament_id, s.rank, e.n
          FROM decks d JOIN event_size e ON e.tournament_id=d.tournament_id
          LEFT JOIN standings s ON s.tournament_id=d.tournament_id
            AND lower(trim(s.player))=lower(trim(d.player))
          WHERE d.archetype IS NOT NULL
        )
        SELECT archetype, count(*) FILTER (WHERE rank <= ceil(n/4.0)), count(*)
        FROM labeled GROUP BY archetype ORDER BY archetype
        """
    ).fetchall()
    conversion = {label: top / count if count else 0.0 for label, top, count in conversion_rows}
    return recent, full, conversion


def _record_probability(results, subject: str, opponent: str, *, jeffreys: bool) -> float:
    tally = results.matchups.get((subject, opponent))
    if tally is None or tally.n == 0:
        record = results.archetypes.get(subject)
        if record is None or record.n == 0:
            return 0.5
        return (record.wins + 0.5) / (record.n + 1.0) if jeffreys else record.wins / record.n
    return (tally.wins + 0.5) / (tally.n + 1.0) if jeffreys else tally.wins / tally.n


def _ranked_recommendation(estimator, scores, *, served=True, reason=None):
    ranked = tuple(sorted(scores, key=lambda action: (
        scores[action] is None, -(scores[action] or 0.0), action,
    )))
    eligible = tuple(action for action in ranked if scores[action] is not None)
    return FrozenRecommendation(
        estimator=estimator, chosen_action=eligible[0] if eligible and served else None,
        ranked_actions=eligible, scores=scores, served=bool(eligible) and served,
        refusal_reason=None if eligible and served else reason or "no frozen eligible action",
    )


def freeze_origin_predictions(
    snapshot_db: Path,
    *,
    protocol: BenchmarkProtocol,
    manifest: SnapshotManifest,
) -> FrozenOriginPredictions:
    """Issue every preregistered forecast using only the origin snapshot."""
    expected_protocol_hash = protocol_sha256(protocol)
    if manifest.protocol_hash != expected_protocol_hash:
        raise ValueError("snapshot manifest protocol hash does not match protocol")
    con = duckdb.connect(str(snapshot_db), read_only=True)
    try:
        actions, shares, rows = _benchmark_rows(con, protocol, manifest)
        recent, full, conversion = _baseline_inputs(con, protocol, manifest)
    finally:
        con.close()

    predictions: list[FrozenMatchupPrediction] = []
    methodology: dict[str, dict[str, object]] = {}
    variant_specs = methodology_variant_specs(8)
    variant_scores: dict[str, dict[str, float | None]] = {
        "production-raw": {}, "production-ci-gated": {},
        "production-ban-scoped": {}, "production-era-only": {}, "production-lean": {},
    }
    for subject in actions:
        cells, row = rows[subject]
        row_method: dict[str, object] = {}
        for spec in variant_specs:
            projection = measure_variant_row(cells, spec=spec, top_k=min(8, len(actions)), cover_min=0.8)
            estimator = {
                "raw": "production-raw", "ci-gated": "production-ci-gated",
                "ban-scoped": "production-ban-scoped", "era-only": "production-era-only",
            }[spec.id]
            variant_scores[estimator][subject] = projection.agency
            row_method[spec.id] = projection.model_dump(mode="json")
            predictions.extend(project_matchup_probability(cell, spec=spec) for cell in cells)
        lean = measure_lean_agency(cells, seed=protocol.seed)
        variant_scores["production-lean"][subject] = lean.q25
        row_method["lean"] = lean.model_dump(mode="json")
        row_method["canonical"] = row.model_dump(mode="json")
        methodology[subject] = row_method
        for cell in cells:
            source = cell.era if cell.era is not None else cell.fallback
            resolved = source is not None and source.cell.n > 0 and source.cell.p_raw is not None
            predictions.append(FrozenMatchupPrediction(
                estimator="production-lean", subject=subject, opponent=cell.opponent,
                probability=float(source.cell.p_raw) if resolved else 0.5,
                served=resolved, source_kind=source.kind if source is not None else "unresolved",
                imputed=not resolved,
                refusal_reason=None if resolved else "no frozen matchup evidence; explicit 0.5 forecast",
            ))

    baseline_scores = {
        "coin-50": {action: 0.5 for action in actions},
        "recent-raw-wr": {
            action: _record_probability(recent, action, action, jeffreys=False) for action in actions
        },
        "field-share": dict(shares),
        "top-finish-conversion": {action: conversion.get(action, 0.0) for action in actions},
        "simple-jeffreys-shrinkage": {
            action: _record_probability(full, action, action, jeffreys=True) for action in actions
        },
    }
    for subject in actions:
        for opponent in actions:
            for estimator in ("coin-50", "field-share", "top-finish-conversion"):
                predictions.append(FrozenMatchupPrediction(
                    estimator=estimator, subject=subject, opponent=opponent, probability=0.5,
                    served=estimator == "coin-50", source_kind="uninformative-0.5",
                    imputed=estimator != "coin-50",
                    refusal_reason=None if estimator == "coin-50" else "ranking-only baseline",
                ))
            for estimator, results, jeffreys in (
                ("recent-raw-wr", recent, False),
                ("simple-jeffreys-shrinkage", full, True),
            ):
                pair = results.matchups.get((subject, opponent))
                modeled = pair is not None and pair.n > 0
                predictions.append(FrozenMatchupPrediction(
                    estimator=estimator, subject=subject, opponent=opponent,
                    probability=_record_probability(results, subject, opponent, jeffreys=jeffreys),
                    served=modeled, source_kind="pair" if modeled else "marginal-fallback",
                    imputed=not modeled, refusal_reason=None if modeled else "pair absent; marginal fallback",
                ))

    recommendations = [
        _ranked_recommendation(estimator, scores)
        for estimator, scores in {**baseline_scores, **variant_scores}.items()
    ]
    # Preserve the deployed primary ordering: evidence stratum first, then Agency and stable id.
    canonical = {action: rows[action][1] for action in actions}
    primary_ranked = tuple(sorted(actions, key=lambda action: (
        0 if canonical[action].grounded else 2,
        -(canonical[action].agency if canonical[action].agency is not None else -1.0), action,
    )))
    primary = next(item for item in recommendations if item.estimator == "production-ci-gated")
    recommendations[recommendations.index(primary)] = primary.model_copy(update={
        "chosen_action": primary_ranked[0] if primary_ranked else None,
        "ranked_actions": primary_ranked,
        "served": bool(primary_ranked),
        "refusal_reason": None if primary_ranked else "no frozen eligible action",
    })
    try:
        code_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        code_commit = "unknown"
    return FrozenOriginPredictions(
        protocol_hash=expected_protocol_hash,
        snapshot_manifest_sha256=content_sha256(manifest), fold=manifest.fold,
        taxonomy_mode=manifest.taxonomy_mode,
        taxonomy_effective_at=manifest.taxonomy_effective_at,
        taxonomy_sha256=manifest.taxonomy_sha256,
        rules_sha256=manifest.rules_sha256,
        generated_at=protocol.created_at, code_commit=code_commit,
        estimator_registry=ESTIMATOR_REGISTRY, action_universe=actions,
        field_shares={action: shares[action] for action in actions},
        matchup_predictions=tuple(sorted(
            predictions, key=lambda item: (item.estimator, item.subject, item.opponent),
        )),
        recommendations=tuple(sorted(recommendations, key=lambda item: item.estimator)),
        methodology=methodology, seeds={"benchmark": protocol.seed, "lean": protocol.seed},
    )


def _classified_labels(
    con: duckdb.DuckDBPyConnection, taxonomy_snapshot: Path, cutoff: str,
) -> dict[tuple[str, int], str]:
    _manifest, rules_path = _load_taxonomy_snapshot(taxonomy_snapshot, cutoff)
    if not rules_path.is_dir():
        raise ValueError("contemporaneous taxonomy rules payload must be a rules directory")
    ruleset = load_ruleset(rules_path)
    labels: dict[tuple[str, int], str] = {}
    for tournament_id, deck_idx in con.execute(
        "SELECT tournament_id, deck_idx FROM decks ORDER BY 1, 2"
    ).fetchall():
        main: dict[str, int] = {}
        side: dict[str, int] = {}
        cards = []
        for board, name, count in con.execute(
            "SELECT board, name, count FROM deck_cards WHERE tournament_id=? AND deck_idx=?",
            [tournament_id, deck_idx],
        ).fetchall():
            target = main if board == "main" else side
            target[name] = target.get(name, 0) + count
            card = store.load_card(con, name)
            if card is not None:
                cards.append(card)
        labels[(str(tournament_id), int(deck_idx))] = classify(
            main, side, ruleset, compute_deck_colors(cards),
        ).archetype
    return labels


def load_heldout_matches(
    source_db: Path, fold: BenchmarkFold, *, taxonomy_snapshot: Path | None = None,
) -> tuple[HeldoutMatch, ...]:
    """Read and orient future outcomes; player identity remains evaluation-only metadata."""
    con = duckdb.connect(str(source_db), read_only=True)
    try:
        classified = (
            _classified_labels(con, taxonomy_snapshot, fold.cutoff)
            if taxonomy_snapshot is not None else None
        )
        rows = con.execute(
            """
            WITH dup AS (
              SELECT tournament_id, lower(trim(player)) AS norm
              FROM decks GROUP BY tournament_id, lower(trim(player)) HAVING count(*) > 1
            )
            SELECT t.id, substr(t.date,1,10), coalesce(t.provenance,''),
                   r.player1, r.player2, r.result,
                   d1.deck_idx, d2.deck_idx, d1.archetype, d2.archetype,
                   du1.norm IS NOT NULL, du2.norm IS NOT NULL
            FROM rounds r JOIN tournaments t ON t.id=r.tournament_id
            LEFT JOIN decks d1 ON d1.tournament_id=r.tournament_id
              AND lower(trim(d1.player))=lower(trim(r.player1))
            LEFT JOIN decks d2 ON d2.tournament_id=r.tournament_id
              AND lower(trim(d2.player))=lower(trim(r.player2))
            LEFT JOIN dup du1 ON du1.tournament_id=r.tournament_id
              AND du1.norm=lower(trim(r.player1))
            LEFT JOIN dup du2 ON du2.tournament_id=r.tournament_id
              AND du2.norm=lower(trim(r.player2))
            WHERE substr(t.date,1,10)>=? AND substr(t.date,1,10)<?
            ORDER BY t.date, t.id, r.match_idx
            """,
            [fold.cutoff, fold.evaluation_until],
        ).fetchall()
    finally:
        con.close()
    heldout: list[HeldoutMatch] = []
    for (
        event_id, event_date, provenance, player1, player2, result,
        deck1, deck2, arch1, arch2, amb1, amb2,
    ) in rows:
        if classified is not None:
            arch1 = classified.get((str(event_id), int(deck1))) if deck1 is not None else None
            arch2 = classified.get((str(event_id), int(deck2))) if deck2 is not None else None
        outcome = parse_match_result(result)
        reason = None
        if amb1 or amb2:
            reason = "ambiguous-player"
        elif outcome is None or outcome.winner is None or not (player2 and str(player2).strip()):
            reason = "bye-draw-invalid"
        elif arch1 is None or arch2 is None:
            reason = "unclassified"
        if arch1 is not None and arch2 is not None and str(arch2) < str(arch1):
            subject, opponent = str(arch2), str(arch1)
            subject_player, opponent_player = player2, player1
            subject_won = outcome is not None and outcome.winner == "p2"
        else:
            subject = str(arch1) if arch1 is not None else None
            opponent = str(arch2) if arch2 is not None else None
            subject_player, opponent_player = player1, player2
            subject_won = outcome is not None and outcome.winner == "p1"
        heldout.append(HeldoutMatch(
            event_id=str(event_id), event_date=str(event_date), provenance=str(provenance),
            subject=subject, opponent=opponent,
            subject_player_key=normalize_player(subject_player) or None,
            opponent_player_key=normalize_player(opponent_player) or None,
            subject_won=subject_won if reason is None else None,
            exclusion_reason=reason,
        ))
    return tuple(heldout)
