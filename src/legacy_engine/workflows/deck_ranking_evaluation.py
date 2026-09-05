"""Freeze and score the served Deck Rankings model on later outcomes.

This workflow is deliberately smaller than the recurrent validation framework.
It owns one parent-only, retrospective fixed-taxonomy experiment and shares the
production ranking projection.  Forecasts are persisted before heldout rows are
read, which makes the temporal boundary an artifact property rather than a
caller convention.
"""

from __future__ import annotations

from collections import defaultdict
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
import hashlib
import json
import math
import random
from pathlib import Path
import subprocess
from typing import Any

import duckdb

from legacy_engine.advisory.deck_ranking_projection import project_ranking_rows
from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkFold,
    CardMetadataPolicy,
    HeldoutOutcomes,
    atomic_write_canonical,
    content_sha256,
)
from legacy_engine.advisory.plan_borrowing import build_plan_borrowing_priors
from legacy_engine.analytics.eras.consume import AnalysisClock
from legacy_engine.analytics.amplification.corpus import build_interval_evidence_corpus
from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.analytics.strategy_plan import load_strategic_plan_registry
from legacy_engine.config import COLOR_SPLITS_REGISTRY_PATH
from legacy_engine.workflows.ranking_benchmark import (
    build_origin_snapshot,
    load_heldout_outcomes,
)

DEFAULT_PRIOR_SCALES: tuple[float, ...] = (1.0, 0.5, 2.0)
DEFAULT_DRAWS = 2_000
DEFAULT_GROUND_N = 8
DEFAULT_TOP_K = 8
DEFAULT_COVER_MIN = 0.8
DEFAULT_MIN_ROW_SHARE = 0.001
DEFAULT_PLAN_PRIOR_STRENGTH_CAP = 15.0
DEFAULT_CARD_METADATA_POLICY = CardMetadataPolicy(
    mode="quarantine-unresolved-decks", max_deck_fraction=0.005, max_round_fraction=0.02,
)
PLAN_BORROWING_METHOD = "opponent-plan-prior-v1"
_LOG_EPSILON = 1e-12
_SCALE_DIGITS = 12

# These declarations are part of the experiment identity.  They are available
# as a CLI default so an operator cannot accidentally tune origins from results.
DECLARED_ORIGINS: tuple[tuple[str, str, str], ...] = (
    ("2026-07-13", "2026-07-20", "2026-06-29"),
    ("2026-07-20", "2026-07-27", "2026-06-29"),
    ("2026-07-27", "2026-08-03", "2026-06-29"),
    ("2026-08-17", "2026-08-24", "2026-08-10"),
    ("2026-08-24", "2026-08-31", "2026-08-10"),
    ("2026-08-31", "2026-09-04", "2026-08-10"),
)
DEVELOPMENT_ORIGINS = DECLARED_ORIGINS[:3]
CONFIRMATION_ORIGINS = DECLARED_ORIGINS[3:]


def _date(value: object, *, name: str) -> date:
    try:
        parsed = date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an ISO date") from exc
    return parsed


def _scale_key(value: float) -> str:
    return f"{value:g}"


def _validate_scales(scales: Sequence[float]) -> tuple[float, ...]:
    if not scales:
        raise ValueError("prior_scales must contain at least one scale")
    result: list[float] = []
    for raw in scales:
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("prior_scales must be finite and positive") from exc
        if value <= 0.0 or not math.isfinite(value):
            raise ValueError("prior_scales must be finite and positive")
        if any(abs(value - existing) <= 10 ** -_SCALE_DIGITS for existing in result):
            raise ValueError("prior_scales must not contain duplicates")
        result.append(value)
    if not any(abs(value - 1.0) <= 10 ** -_SCALE_DIGITS for value in result):
        raise ValueError("prior_scales must include the production scale 1")
    return tuple(result)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _code_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _fold(cutoff: str, evaluation_until: str, regime_start: str) -> BenchmarkFold:
    cutoff_date = _date(cutoff, name="cutoff")
    until_date = _date(evaluation_until, name="evaluation_until")
    regime_date = _date(regime_start, name="regime_start")
    if until_date <= cutoff_date:
        raise ValueError("evaluation_until must be after cutoff")
    if regime_date > cutoff_date:
        raise ValueError("regime_start must be on or before cutoff")
    return BenchmarkFold(
        fold_id=f"{cutoff_date.isoformat()}--{until_date.isoformat()}",
        cutoff=cutoff_date.isoformat(), evaluation_until=until_date.isoformat(),
        regime_start=regime_date.isoformat(), regime_end=None, event_dates=(),
    )


def _protocol_hash(
    fold: BenchmarkFold, scales: Sequence[float], draws: int,
) -> str:
    registry = load_strategic_plan_registry()
    return content_sha256({
        "protocol_id": "deck-ranking-evaluation-v1",
        "fold": fold.model_dump(mode="json"),
        "prior_scales": list(scales), "draws": draws,
        "plan_prior": {
            "method": PLAN_BORROWING_METHOD,
            "strength_cap": DEFAULT_PLAN_PRIOR_STRENGTH_CAP,
            "registry_sha256": _registry_sha256(registry),
        },
        "card_metadata_policy": DEFAULT_CARD_METADATA_POLICY.model_dump(mode="json"),
        "color_splits_sha256": _file_sha256(COLOR_SPLITS_REGISTRY_PATH),
        "taxonomy_mode": "retrospective-fixed-parent",
        "ground_n": DEFAULT_GROUND_N, "top_k": DEFAULT_TOP_K,
        "cover_min": DEFAULT_COVER_MIN, "min_row_share": DEFAULT_MIN_ROW_SHARE,
    })


def _registry_sha256(registry: object) -> str:
    """Hash the semantic primary-plan registry that binds the challenger."""
    return content_sha256({
        "schema_version": registry.schema_version,
        "plans": [
            {"id": item.id, "label": item.label, "description": item.description}
            for item in registry.plans
        ],
        "assignments": [
            {
                "archetype": item.archetype,
                "primary": item.primary,
                "secondary": list(item.secondary),
            }
            for item in registry.assignments
        ],
    })


def _refresh_module():
    # The production generator is a script by design.  Importing it lazily keeps
    # this workflow usable by tests and by the installed package CLI.
    from scripts import refresh_best_call_ranking
    return refresh_best_call_ranking


def _production_inputs(snapshot_db: Path, fold: BenchmarkFold, *, draws: int):
    refresh = _refresh_module()
    cutoff = fold.cutoff
    bans = tuple(
        (event[0], event[1], event[2])
        for event in BAN_EVENTS if event[0].isoformat() < cutoff
    )
    regime_card = next(
        (event[1] for event in bans if event[0].isoformat() == fold.regime_start),
        None,
    )
    con = duckdb.connect(str(snapshot_db), read_only=True)
    try:
        blob = refresh.compute_blob(
            con,
            field_since=fold.regime_start,
            ground_n=DEFAULT_GROUND_N,
            top_k=DEFAULT_TOP_K,
            cover_min=DEFAULT_COVER_MIN,
            min_row_share=DEFAULT_MIN_ROW_SHARE,
            regime_card=regime_card,
            parents=(),
            superarchetypes=None,
            data_until=cutoff,
            ban_events=bans,
            include_plans=False,
        )
        # The interval constructor has a deliberate no-certificate path that
        # delegates to the same current matrix.  Passing it through the
        # publisher exercises the exact positive-n interval override seam used
        # by the served report.
        interval = refresh.build_interval_adaptive_matrix(
            con,
            clock=AnalysisClock(
                data_until=date.fromisoformat(cutoff),
                knowledge_as_of=datetime.combine(
                    date.fromisoformat(cutoff), datetime.min.time(), tzinfo=timezone.utc,
                ),
                knowledge_mode="retrospective-current-model",
            ),
            certificate_run_id=None,
            min_row_share=DEFAULT_MIN_ROW_SHARE,
            until=cutoff,
            ban_events=bans,
        )
        # This is the production report projection, including its corpus-max+1
        # recency anchor, transition pseudo-count construction, interval source
        # selection, and positive-n overrides.
        interval_corpus = build_interval_evidence_corpus(interval)
        refresh._publish_deck_rankings(con, blob, parent_interval=interval)
        handoff = blob.get("_deck_ranking_projection_inputs", {}).get("arch")
        if not handoff:
            raise ValueError("production ranking publisher did not expose its parent projection handoff")
        rows = handoff["rows"]
        shares = {str(label): float(value) for label, value in handoff["shares"].items()}
        counts = {str(label): float(value) for label, value in handoff["counts"].items()}
        presence = {str(label): float(value) for label, value in handoff["candidate_presence"].items()}
        registry = load_strategic_plan_registry()
        primary_plans = {
            assignment.archetype: assignment.primary
            for assignment in registry.assignments
        }
        target_pairs = tuple(
            (subject, opponent)
            for subject in rows
            for opponent in shares
            if subject != opponent
        )
        plan_priors = build_plan_borrowing_priors(
            interval_corpus, primary_plans, target_pairs,
            strength_cap=DEFAULT_PLAN_PRIOR_STRENGTH_CAP,
        )
        plan_context = {
            "corpus": interval_corpus,
            "registry": registry,
            "primary_plans": primary_plans,
            "registry_sha256": _registry_sha256(registry),
            "target_pairs": target_pairs,
            "priors": plan_priors,
        }
        return blob, rows, shares, counts, presence, handoff, plan_context
    finally:
        con.close()


def _forecast_payload(projection: Mapping[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = projection["rows"]
    cells: list[dict[str, Any]] = []
    for subject in sorted(rows):
        row = rows[subject]
        for cell in row["cells"]:
            payload = {
                "subject": subject,
                "opponent": cell["opponent"],
                "probability": float(cell["mean"]),
                "support_n": int(cell["n"]),
                "served": True,
                "source_kind": cell["source_kind"],
                "source_identity": cell["source_identity"],
                "prior_source": cell["prior_source"],
                "prior_strength_original": float(cell["prior_strength_original"]),
                "prior_strength_effective": float(cell["prior_strength_effective"]),
                "prior_contribution_fraction": float(cell["prior_contribution_fraction"]),
                "is_mirror": bool(cell["is_mirror"]),
            }
            if cell.get("borrowed_prior") is not None:
                payload["borrowed_prior"] = cell["borrowed_prior"]
            cells.append(payload)
    floor_pairs = [
        {"subject": subject, "opponent": row["worst_opponent"],
         "support_n": next(
             (cell["n"] for cell in row["cells"] if cell["opponent"] == row["worst_opponent"]), 0,
         ), "available": row["worst_opponent"] is not None}
        for subject, row in sorted(rows.items())
        if row["worst_opponent"] is not None
    ]
    return {
        "prior_scale": float(projection["prior_scale"]),
        "field": projection["field"],
        "rows": rows,
        "cells": cells,
        "floor_pairings": floor_pairs,
    }


def freeze_ranking_origin(
    source_db: Path,
    output_dir: Path,
    *,
    cutoff: str,
    evaluation_until: str,
    regime_start: str,
    prior_scales: tuple[float, ...] = DEFAULT_PRIOR_SCALES,
    draws: int = DEFAULT_DRAWS,
) -> dict[str, Any]:
    """Freeze one origin's parent ranking grid before any heldout read."""
    if not isinstance(draws, int) or draws < 1:
        raise ValueError("draws must be a positive integer")
    scales = _validate_scales(prior_scales)
    fold = _fold(cutoff, evaluation_until, regime_start)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = output_dir / "snapshot.duckdb"
    manifest_path = output_dir / "snapshot-manifest.json"
    predictions_path = output_dir / "predictions.json"
    protocol_hash = _protocol_hash(fold, scales, draws)
    manifest = build_origin_snapshot(
        Path(source_db), snapshot, fold=fold, protocol_hash=protocol_hash,
        taxonomy_mode="retrospective-fixed-parent",
        card_metadata_policy=DEFAULT_CARD_METADATA_POLICY,
        color_splits_path=COLOR_SPLITS_REGISTRY_PATH,
        ban_events=tuple(
            (event[0].isoformat(), event[1], event[2])
            for event in BAN_EVENTS if event[0].isoformat() < fold.cutoff
        ),
    )
    manifest_sha = content_sha256(manifest)
    atomic_write_canonical(manifest_path, manifest)
    _blob, rows, shares, counts, presence, handoff, plan_context = _production_inputs(
        snapshot, fold, draws=draws,
    )
    projections = {
        _scale_key(scale): project_ranking_rows(
            rows, shares, counts=counts, candidate_presence=presence,
            cell_overrides=handoff["cell_overrides"],
            override_sources=handoff["override_sources"],
            override_identities=handoff.get("override_identities", {}),
            prior_scale=scale, draws=draws, seed=730_021,
        )
        for scale in scales
    }
    projections[PLAN_BORROWING_METHOD] = project_ranking_rows(
        rows, shares, counts=counts, candidate_presence=presence,
        cell_overrides=handoff["cell_overrides"],
        override_sources=handoff["override_sources"],
        override_identities=handoff.get("override_identities", {}),
        prior_overrides=plan_context["priors"],
        draws=draws, seed=730_021,
    )
    metadata = {
        "protocol_id": "deck-ranking-evaluation-v1",
        "protocol_hash": protocol_hash,
        "snapshot_manifest_sha256": manifest_sha,
        "snapshot_file_sha256": _file_sha256(snapshot),
        "training_facts_sha256": manifest.training_facts_sha256,
        "rules_sha256": manifest.rules_sha256,
        "color_splits_sha256": manifest.color_splits_sha256,
        "taxonomy_mode": "retrospective-fixed-parent",
        "card_metadata_policy": DEFAULT_CARD_METADATA_POLICY.model_dump(mode="json"),
        "training_card_metadata_quarantine": (
            manifest.card_metadata_quarantine.model_dump(mode="json")
            if manifest.card_metadata_quarantine is not None else None
        ),
        "plan_prior": {
            "method": PLAN_BORROWING_METHOD,
            "strength_cap": DEFAULT_PLAN_PRIOR_STRENGTH_CAP,
            "registry_sha256": plan_context["registry_sha256"],
            "corpus_id": plan_context["corpus"].corpus_id,
            "corpus_pair_evidence_sha256": plan_context["corpus"].pair_evidence_sha256,
            "target_pairs_sha256": content_sha256(plan_context["target_pairs"]),
            "prior_count": len(plan_context["priors"]),
        },
        "code_commit": _code_commit(),
        # The timestamp names the forecast cutoff rather than wall-clock run
        # time, keeping identical source/config replays content-addressable.
        "created_at": f"{fold.cutoff}T00:00:00+00:00",
        "config": {
            "prior_scales": list(scales), "draws": draws,
            "ground_n": DEFAULT_GROUND_N, "top_k": DEFAULT_TOP_K,
            "cover_min": DEFAULT_COVER_MIN, "min_row_share": DEFAULT_MIN_ROW_SHARE,
            "seed": 730_021,
            "color_splits_sha256": manifest.color_splits_sha256,
            "card_metadata_policy": DEFAULT_CARD_METADATA_POLICY.model_dump(mode="json"),
            "plan_prior": {
                "method": PLAN_BORROWING_METHOD,
                "strength_cap": DEFAULT_PLAN_PRIOR_STRENGTH_CAP,
                "registry_sha256": plan_context["registry_sha256"],
            },
        },
        "fold": fold.model_dump(mode="json"),
    }
    payload = {
        "metadata": metadata,
        "forecasts": {
            key: _forecast_payload(projections[key]) for key in sorted(projections)
        },
    }
    # The digest binds every projection and all source/config identities.  The
    # artifact is complete before the caller can request heldout outcomes.
    payload["artifact_sha256"] = content_sha256(payload)
    atomic_write_canonical(predictions_path, payload)
    return {
        **payload,
        "paths": {
            "snapshot": str(snapshot), "manifest": str(manifest_path),
            "predictions": str(predictions_path),
        },
    }


def _validate_frozen_predictions(forecasts: Mapping[str, Any]) -> None:
    if not isinstance(forecasts, Mapping):
        raise ValueError("forecasts must be a mapping")
    digest = forecasts.get("artifact_sha256")
    if not isinstance(digest, str) or not digest:
        raise ValueError("frozen ranking predictions are missing artifact digest")
    payload = {
        key: value for key, value in forecasts.items()
        if key not in {"artifact_sha256", "paths"}
    }
    if content_sha256(payload) != digest:
        raise ValueError("frozen ranking prediction artifact digest mismatch")
    metadata = forecasts.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("frozen ranking predictions are missing metadata")
    fold = metadata.get("fold")
    if not isinstance(fold, Mapping):
        raise ValueError("frozen ranking predictions are missing fold metadata")
    if metadata.get("taxonomy_mode") != "retrospective-fixed-parent":
        raise ValueError("ranking evaluation requires retrospective fixed-parent forecasts")
    methods = forecasts.get("forecasts")
    if not isinstance(methods, Mapping) or not methods:
        raise ValueError("frozen ranking predictions are missing methods")
    keys: set[tuple[str, str]] | None = None
    for method, value in methods.items():
        if (
            not isinstance(value, Mapping)
            or not isinstance(value.get("cells"), Sequence)
            or isinstance(value.get("cells"), (str, bytes))
        ):
            raise ValueError(f"frozen ranking method {method!r} has no cell grid")
        method_keys: list[tuple[str, str]] = []
        for cell in value["cells"]:
            if not isinstance(cell, Mapping):
                raise ValueError(f"frozen ranking method {method!r} has an invalid cell")
            if "subject" not in cell or "opponent" not in cell:
                raise ValueError(f"frozen ranking method {method!r} has an unidentified cell")
            method_keys.append((str(cell["subject"]), str(cell["opponent"])))
        if len(set(method_keys)) != len(method_keys):
            raise ValueError(f"frozen ranking method {method!r} has duplicate forecast cells")
        method_key_set = set(method_keys)
        if keys is None:
            keys = method_key_set
        elif method_key_set != keys:
            raise ValueError("frozen ranking methods do not share an identical cell grid")


def _outcome_rows(outcomes: HeldoutOutcomes | Mapping[str, Any] | Sequence[Any]) -> tuple[Any, ...]:
    if isinstance(outcomes, HeldoutOutcomes):
        return outcomes.matches
    if isinstance(outcomes, Mapping):
        rows = outcomes.get("matches", outcomes.get("outcomes"))
        if rows is None:
            raise ValueError("outcomes mapping is missing matches")
        return tuple(rows)
    return tuple(outcomes)


def _field(row: Any, name: str, default: Any = None) -> Any:
    return getattr(row, name, default) if not isinstance(row, Mapping) else row.get(name, default)


def _physical_matches(outcomes: Sequence[Any]) -> tuple[tuple[Any, str | None], ...]:
    """Return valid physical matches once, preserving exclusions separately."""
    result: list[tuple[Any, str | None]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, outcome in enumerate(outcomes):
        subject = _field(outcome, "subject")
        opponent = _field(outcome, "opponent")
        reason = _field(outcome, "exclusion_reason")
        if subject is not None and opponent is not None and subject == opponent:
            continue
        match_idx = _field(outcome, "match_idx")
        player_a = _field(outcome, "subject_player_key")
        player_b = _field(outcome, "opponent_player_key")
        event = str(_field(outcome, "event_id", ""))
        if match_idx is not None:
            # The source rounds table's match_idx is the only safe identity for
            # rematches between the same players in one event.
            key = (event, f"match_idx:{match_idx}", "")
            if key in seen:
                continue
            seen.add(key)
        elif player_a and player_b:
            # Hand-authored adapters predating match_idx retain the conservative
            # player-pair fallback; actual heldout rows always carry match_idx.
            key = (event, *sorted((str(player_a), str(player_b))))
            if key in seen:
                continue
            seen.add(key)
        result.append((outcome, reason))
    return tuple(result)


def _probability(value: Any) -> float | None:
    if value is None:
        return None
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    return probability if 0.0 <= probability <= 1.0 else None


def _score_probability(probability: float, actual: bool) -> tuple[float, float]:
    p = min(1.0 - _LOG_EPSILON, max(_LOG_EPSILON, probability))
    target = 1.0 if actual else 0.0
    return (-(math.log(p) if actual else math.log1p(-p)), (p - target) ** 2)


def _calibration(points: Sequence[tuple[float, bool, float]]) -> dict[str, Any]:
    if not points:
        return {
            "predictions": 0, "weighted_predictions": 0.0,
            "mean_predicted": None, "observed_rate": None, "bins": [],
        }
    bins: list[dict[str, Any]] = []
    for lower, upper in zip((0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
                            (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0000001), strict=True):
        selected = [(p, actual, weight) for p, actual, weight in points if lower <= p < upper]
        weight = sum(item[2] for item in selected)
        bins.append({
            "lower": lower, "upper": min(1.0, upper),
            "count": len(selected), "weight": weight,
            "mean_predicted": sum(p * w for p, _a, w in selected) / weight if weight else None,
            "observed_rate": sum(float(a) * w for _p, a, w in selected) / weight if weight else None,
        })
    return {
        "predictions": len(points),
        "weighted_predictions": sum(weight for _p, _a, weight in points),
        "mean_predicted": sum(p * weight for p, _a, weight in points) / sum(weight for _p, _a, weight in points),
        "observed_rate": sum(float(actual) * weight for _p, actual, weight in points) / sum(weight for _p, _a, weight in points),
        "bins": bins,
    }


def evaluate_ranking_origin(
    forecasts: Mapping[str, Any],
    outcomes: HeldoutOutcomes | Mapping[str, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Score one frozen origin with half weight for both directions of a match."""
    _validate_frozen_predictions(forecasts)
    methods = forecasts["forecasts"]
    outcome_rows = _outcome_rows(outcomes)
    heldout_quarantine = (
        outcomes.card_metadata_quarantine
        if isinstance(outcomes, HeldoutOutcomes) else None
    )
    mirror_count = sum(
        1 for item in outcome_rows
        if _field(item, "subject") is not None
        and _field(item, "subject") == _field(item, "opponent")
    )
    physical = _physical_matches(outcome_rows)
    exclusion_counts = Counter(
        str(reason) for _item, reason in physical if reason is not None
    )
    valid = [
        item for item, reason in physical
        if reason is None and _field(item, "subject_won") is not None
    ]
    total_matches = len(valid)
    evaluated: dict[str, dict[str, Any]] = {}
    baseline_event_scores: dict[str, float] = {}
    for method, payload in sorted(methods.items(), key=lambda item: str(item[0])):
        grid = {
            (str(cell["subject"]), str(cell["opponent"])): cell
            for cell in payload["cells"]
        }
        log_sum = brier_sum = weight_sum = 0.0
        scored_matches = common_case_matches = 0
        missing_directions = 0
        strata: dict[str, dict[str, float | int]] = {
            "n=0": {"directions": 0, "weight": 0.0, "log_loss": 0.0, "brier": 0.0},
            "n=1-7": {"directions": 0, "weight": 0.0, "log_loss": 0.0, "brier": 0.0},
            "n>=8": {"directions": 0, "weight": 0.0, "log_loss": 0.0, "brier": 0.0},
        }
        points: list[tuple[float, bool, float]] = []
        event_totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        reciprocal: list[float] = []
        for outcome in valid:
            subject = str(_field(outcome, "subject"))
            opponent = str(_field(outcome, "opponent"))
            won = bool(_field(outcome, "subject_won"))
            records = (grid.get((subject, opponent)), grid.get((opponent, subject)))
            pair_scored = 0
            pair_missing = 0
            pair_probs: list[float] = []
            for index, record in enumerate(records):
                probability = _probability(record.get("probability")) if record else None
                if probability is None:
                    missing_directions += 1
                    pair_missing += 1
                    continue
                actual = won if index == 0 else not won
                log_loss, brier = _score_probability(probability, actual)
                weight = 0.5
                log_sum += weight * log_loss
                brier_sum += weight * brier
                weight_sum += weight
                pair_scored += 1
                points.append((probability, actual, weight))
                support_n = int(record.get("support_n", 0))
                stratum = "n=0" if support_n == 0 else "n=1-7" if support_n < 8 else "n>=8"
                bucket = strata[stratum]
                bucket["directions"] = int(bucket["directions"]) + 1
                bucket["weight"] = float(bucket["weight"]) + weight
                bucket["log_loss"] = float(bucket["log_loss"]) + weight * log_loss
                bucket["brier"] = float(bucket["brier"]) + weight * brier
                event = str(_field(outcome, "event_id", ""))
                event_totals[event][0] += weight * log_loss
                event_totals[event][1] += weight
                pair_probs.append(probability)
            if pair_scored:
                scored_matches += 1
            if pair_scored == 2:
                common_case_matches += 1
            if pair_probs and len(pair_probs) == 2:
                reciprocal.append(abs(pair_probs[0] + pair_probs[1] - 1.0))
            if pair_missing == 0:
                event = str(_field(outcome, "event_id", ""))
                event_totals.setdefault(event, [0.0, 0.0])
        for bucket in strata.values():
            weight = float(bucket["weight"])
            bucket["log_loss"] = float(bucket["log_loss"]) / weight if weight else None
            bucket["brier"] = float(bucket["brier"]) / weight if weight else None
        event_means = {
            event: values[0] / values[1]
            for event, values in sorted(event_totals.items()) if values[1]
        }
        if str(method) == "1":
            baseline_event_scores = event_means
        evaluated[str(method)] = {
            "prior_scale": float(payload.get("prior_scale", method)),
            "total_support_matches": total_matches,
            "scored_matches": scored_matches,
            "common_case_matches": common_case_matches,
            "served_matches": scored_matches,
            "missing_forecast_directions": missing_directions,
            "log_loss": log_sum / weight_sum if weight_sum else None,
            "brier": brier_sum / weight_sum if weight_sum else None,
            "scored_directed_weight": weight_sum,
            "support_strata": strata,
            "calibration": _calibration(points),
            "reciprocity": {
                "pairs": len(reciprocal),
                "mean_absolute_discrepancy": sum(reciprocal) / len(reciprocal) if reciprocal else None,
                "max_absolute_discrepancy": max(reciprocal) if reciprocal else None,
            },
            "event_log_loss": event_means,
            "floor_pairings": payload.get("floor_pairings", []),
            "performance_order": [
                subject for subject, row in sorted(
                    payload.get("rows", {}).items(),
                    key=lambda item: (-float(item[1].get("performance", -1.0)), item[0]),
                ) if row.get("eligible")
            ],
            "floor_order": [
                subject for subject, row in sorted(
                    payload.get("rows", {}).items(),
                    key=lambda item: (
                        -(float(item[1]["floor"]) if item[1].get("floor") is not None else -1.0),
                        -float(item[1].get("performance", -1.0)), item[0],
                    ),
                ) if row.get("eligible") and row.get("floor") is not None
            ],
        }

    for method, result in evaluated.items():
        result["paired_event_log_loss_difference_vs_scale_1"] = {
            event: result["event_log_loss"].get(event, 0.0) - baseline_event_scores[event]
            for event in sorted(set(result["event_log_loss"]) & set(baseline_event_scores))
            if method != "1"
        }
    floor_evidence: list[dict[str, Any]] = []
    # The named-floor followup is descriptive evidence for every forecast
    # method.  It never replaces the fitted floor or makes an unavailable
    # pairing a zero-loss observation.
    for method, result in evaluated.items():
        for pairing in result["floor_pairings"]:
            subject, opponent = pairing["subject"], pairing["opponent"]
            matching = [
                outcome for outcome in valid
                if {str(_field(outcome, "subject")), str(_field(outcome, "opponent"))} == {subject, opponent}
            ]
            wins = sum(
                int(bool(_field(outcome, "subject_won")))
                if str(_field(outcome, "subject")) == subject
                else int(not bool(_field(outcome, "subject_won")))
                for outcome in matching
            )
            floor_evidence.append({
                "method": method,
                "subject": subject, "opponent": opponent,
                "available": bool(matching), "matches": len(matching),
                "subject_wins": wins, "subject_losses": len(matching) - wins,
                "support_note": "later outcomes are evidence for this named floor only; they do not redefine the sparse matrix minimum",
            })
    return {
        "fold": forecasts["metadata"]["fold"],
        "artifact_sha256": forecasts.get("artifact_sha256"),
        "total_support_matches": total_matches,
        "support": {
            "physical_rows": len(physical),
            "eligible_decisive_nonmirror_matches": total_matches,
            "mirrors_excluded": mirror_count,
            "exclusions": dict(sorted(exclusion_counts.items())),
        },
        "methods": evaluated,
        "floor_evidence": floor_evidence,
        "scoring": {
            "physical_match_weight": 1.0,
            "directed_match_weight": 0.5,
            "common_case_definition": "both directed forecast cells are present for one physical match",
            "mirrors": "excluded",
            "missing_forecasts": "unavailable and retained in total support; never a zero loss",
            "duplicate_physical_matches": (
                "deduplicated by event/match_idx; legacy hand adapters fall back to event/player pair"
            ),
        },
        "card_metadata": {
            "policy": DEFAULT_CARD_METADATA_POLICY.model_dump(mode="json"),
            "heldout_quarantine": (
                heldout_quarantine.model_dump(mode="json")
                if heldout_quarantine is not None else None
            ),
            "ledger_sha256": (
                heldout_quarantine.digest if heldout_quarantine is not None else None
            ),
        },
    }


def _markdown_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Deck Rankings served-model evaluation",
        "",
        f"Phase: {summary.get('phase', 'unknown')}; evidence status: {summary.get('status', 'unknown')}",
        f"Selected candidate: {summary.get('selected_candidate') or 'not sealed'}",
        "Fixed prior scales and retrospective parent taxonomy; forecasts were frozen before heldout outcomes were read.",
        "",
        "| Method | weighted matches | log loss | Brier |",
        "|---|---:|---:|---:|",
    ]
    methods = summary.get("methods", {})
    for method, aggregate in methods.items():
        weighted = aggregate.get("match_weighted", {})
        lines.append(
            f"| {method} | {weighted.get('weight', 0):g} | "
            f"{weighted.get('log_loss') if weighted.get('log_loss') is not None else 'n/a'} | "
            f"{weighted.get('brier') if weighted.get('brier') is not None else 'n/a'} |"
        )
    lines.extend([
        "", "Event-level comparison (equal event weight; negative favors the candidate):",
        "", "| Method | Mean log-loss difference [95% bootstrap interval] | Improved / worsened events |",
        "|---|---:|---:|",
    ])
    for method, aggregate in methods.items():
        if method == "1":
            continue
        paired = aggregate["event_paired_stability"]
        mean = paired["mean_log_loss_difference_vs_scale_1"]
        interval = paired.get("mean_difference_interval_95")
        estimate = f"{mean:+.5f}" if mean is not None else "unavailable"
        if interval is not None:
            estimate += f" [{interval[0]:+.5f}, {interval[1]:+.5f}]"
        else:
            estimate += " [interval unavailable]"
        lines.append(
            f"| {method} | {estimate} | {paired['improved_events']} / {paired['worsened_events']} |"
        )
    lines.extend(["", "Independent leaders across origins (counts are origins, not probabilities):", ""])
    for method, aggregate in methods.items():
        calls = []
        for objective in ("performance", "floor"):
            counts = aggregate[f"{objective}_order_sensitivity"]["top_call_counts"]
            names = ", ".join(f"{name} ({count})" for name, count in counts.items()) or "unavailable"
            calls.append(f"{objective}: {names}")
        lines.append(f"- {method} — " + "; ".join(calls))
    lines.extend(["", "| Origin | Method | total matches | common cases | log loss | Brier |", "|---|---|---:|---:|---:|---:|"])
    for origin in summary.get("origins", []):
        fold = origin["fold"]
        label = f"{fold['cutoff']}→{fold['evaluation_until']}"
        for scale, result in origin.get("methods", {}).items():
            lines.append(
                f"| {label} | {scale} | {result['total_support_matches']} | "
                f"{result['common_case_matches']} | {result['log_loss'] if result['log_loss'] is not None else 'n/a'} | "
                f"{result['brier'] if result['brier'] is not None else 'n/a'} |"
            )
    lines.extend([
        "", "Unknown labels or unavailable floor outcomes remain explicit support gaps. "
        "The table is descriptive evidence and does not select a production scale.", "",
    ])
    return "\n".join(lines)


def _artifact_body(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item for key, item in value.items()
        if key not in {"artifact_sha256", "paths"}
    }


def _read_sealed_json(path: Path, *, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read sealed {description}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"sealed {description} must be a JSON object")
    digest = value.get("artifact_sha256")
    if not isinstance(digest, str) or content_sha256(_artifact_body(value)) != digest:
        raise ValueError(f"sealed {description} has an invalid artifact digest")
    return value


def _freeze_all_origins(
    source_db: Path,
    root: Path,
    origins: Sequence[tuple[str, str, str]],
    *,
    scales: tuple[float, ...],
    draws: int,
) -> list[dict[str, Any]]:
    frozen: list[dict[str, Any]] = []
    for cutoff, evaluation_until, regime_start in origins:
        origin_dir = root / f"{cutoff}--{evaluation_until}"
        paths = (
            origin_dir / "snapshot.duckdb",
            origin_dir / "snapshot-manifest.json",
            origin_dir / "predictions.json",
        )
        if any(path.exists() for path in paths):
            frozen.append(_load_reusable_frozen_origin(
                root, (cutoff, evaluation_until, regime_start), scales=scales, draws=draws,
            ))
            continue
        frozen.append(freeze_ranking_origin(
            source_db, origin_dir, cutoff=cutoff, evaluation_until=evaluation_until,
            regime_start=regime_start, prior_scales=scales, draws=draws,
        ))
    return frozen


def _load_reusable_frozen_origin(
    root: Path,
    origin: tuple[str, str, str],
    *,
    scales: tuple[float, ...],
    draws: int,
) -> dict[str, Any]:
    cutoff, evaluation_until, regime_start = origin
    origin_dir = root / f"{cutoff}--{evaluation_until}"
    snapshot_path = origin_dir / "snapshot.duckdb"
    manifest_path = origin_dir / "snapshot-manifest.json"
    prediction_path = origin_dir / "predictions.json"
    paths = (snapshot_path, manifest_path, prediction_path)
    if not all(path.is_file() for path in paths):
        missing = ", ".join(path.name for path in paths if not path.is_file())
        raise ValueError(f"frozen ranking origin is incomplete ({missing}): {origin_dir}")
    artifact = _read_sealed_json(prediction_path, description="ranking predictions")
    _validate_frozen_predictions(artifact)
    metadata = artifact.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError(f"frozen ranking origin is missing metadata: {prediction_path}")
    expected_fold = _fold(cutoff, evaluation_until, regime_start)
    if metadata.get("fold") != expected_fold.model_dump(mode="json"):
        raise ValueError(f"frozen ranking origin identity does not match {prediction_path}")
    if metadata.get("protocol_hash") != _protocol_hash(expected_fold, scales, draws):
        raise ValueError(f"frozen ranking protocol does not match requested configuration: {prediction_path}")
    config = metadata.get("config")
    if not isinstance(config, Mapping):
        raise ValueError(f"frozen ranking origin is missing configuration: {prediction_path}")
    if list(config.get("prior_scales", ())) != list(scales) or config.get("draws") != draws:
        raise ValueError(f"frozen ranking configuration does not match request: {prediction_path}")
    if metadata.get("color_splits_sha256") != _file_sha256(COLOR_SPLITS_REGISTRY_PATH):
        raise ValueError(f"frozen ranking color registry does not match request: {prediction_path}")
    if config.get("color_splits_sha256") != metadata.get("color_splits_sha256"):
        raise ValueError(f"frozen ranking color registry configuration is inconsistent: {prediction_path}")
    if metadata.get("card_metadata_policy") != DEFAULT_CARD_METADATA_POLICY.model_dump(mode="json"):
        raise ValueError(f"frozen ranking card metadata policy does not match request: {prediction_path}")
    if config.get("card_metadata_policy") != metadata.get("card_metadata_policy"):
        raise ValueError(f"frozen ranking card metadata configuration is inconsistent: {prediction_path}")
    registry_hash = _registry_sha256(load_strategic_plan_registry())
    if metadata.get("plan_prior", {}).get("registry_sha256") != registry_hash:
        raise ValueError(f"frozen ranking plan registry does not match request: {prediction_path}")
    manifest = _read_json_object(manifest_path, description="snapshot manifest")
    if content_sha256(manifest) != metadata.get("snapshot_manifest_sha256"):
        raise ValueError(f"frozen ranking snapshot manifest digest mismatch: {manifest_path}")
    if _file_sha256(snapshot_path) != metadata.get("snapshot_file_sha256"):
        raise ValueError(f"frozen ranking snapshot digest mismatch: {snapshot_path}")
    artifact["paths"] = {
        "snapshot": str(snapshot_path), "manifest": str(manifest_path),
        "predictions": str(prediction_path),
    }
    return artifact


def _load_frozen_origins(
    root: Path,
    origins: Sequence[tuple[str, str, str]],
    *,
    scales: tuple[float, ...],
    draws: int,
) -> list[dict[str, Any]]:
    return [
        _load_reusable_frozen_origin(root, origin, scales=scales, draws=draws)
        for origin in origins
    ]


def _read_json_object(path: Path, *, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read {description}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a JSON object: {path}")
    return value


def _partition_origins(
    origins: Sequence[tuple[str, str, str]],
) -> tuple[tuple[tuple[str, str, str], ...], tuple[tuple[str, str, str], ...]]:
    if tuple(origins) == DECLARED_ORIGINS:
        return DEVELOPMENT_ORIGINS, CONFIRMATION_ORIGINS
    # Custom origins are still declared in order and split chronologically;
    # one-origin smoke runs remain useful development-only runs.
    development_count = max(1, (len(origins) + 1) // 2)
    return tuple(origins[:development_count]), tuple(origins[development_count:])


def _validate_origins(origins: Sequence[tuple[str, str, str]]) -> None:
    seen: set[tuple[str, str, str]] = set()
    previous: BenchmarkFold | None = None
    for origin in origins:
        if len(origin) != 3 or origin in seen:
            raise ValueError("origins must be unique cutoff/evaluation/regime triples")
        seen.add(origin)
        current = _fold(*origin)
        if previous is not None and (
            current.cutoff < previous.cutoff
            or current.cutoff < previous.evaluation_until
        ):
            raise ValueError("origins must be chronological and non-overlapping")
        previous = current


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _stdev(values: Sequence[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _event_mean_interval(differences: Sequence[float]) -> list[float] | None:
    """Bootstrap the event-average paired difference; no interval from one event."""
    if len(differences) < 2:
        return None
    rng = random.Random(730_022)
    means = sorted(
        sum(rng.choices(differences, k=len(differences))) / len(differences)
        for _ in range(2_000)
    )
    return [means[49], means[1_949]]


def _phase_evidence(evaluated: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    method_names = sorted({
        str(method)
        for origin in evaluated
        for method in origin.get("methods", {})
    })
    methods: dict[str, dict[str, Any]] = {}
    baseline_by_event: dict[str, dict[str, float]] = {}
    for origin in evaluated:
        baseline_by_event[origin["fold"]["fold_id"]] = {
            str(event): float(score)
            for event, score in origin.get("methods", {}).get("1", {}).get("event_log_loss", {}).items()
        }
    for method in method_names:
        scores = [
            origin["methods"][method]
            for origin in evaluated if method in origin.get("methods", {})
        ]
        weights = [float(score.get("scored_directed_weight", 0.0)) for score in scores]
        total_weight = sum(weights)
        weighted_log_loss = sum(
            float(score["log_loss"]) * weight
            for score, weight in zip(scores, weights, strict=True)
            if score.get("log_loss") is not None and weight > 0
        )
        weighted_brier = sum(
            float(score["brier"]) * weight
            for score, weight in zip(scores, weights, strict=True)
            if score.get("brier") is not None and weight > 0
        )
        event_differences: list[float] = []
        event_records: list[dict[str, Any]] = []
        for origin in evaluated:
            current = origin.get("methods", {}).get(method)
            baseline = baseline_by_event.get(origin["fold"]["fold_id"], {})
            if current is None:
                continue
            for event, value in sorted(current.get("event_log_loss", {}).items()):
                if method == "1" or event not in baseline:
                    continue
                difference = float(value) - baseline[event]
                event_differences.append(difference)
                event_records.append({
                    "fold_id": origin["fold"]["fold_id"],
                    "event_id": event,
                    "log_loss_difference_vs_scale_1": difference,
                })
        performance_orders = [
            {"fold_id": origin["fold"]["fold_id"], "order": origin["methods"][method].get("performance_order", [])}
            for origin in evaluated if method in origin.get("methods", {})
        ]
        floor_orders = [
            {"fold_id": origin["fold"]["fold_id"], "order": origin["methods"][method].get("floor_order", [])}
            for origin in evaluated if method in origin.get("methods", {})
        ]
        top_performance = Counter(
            order["order"][0] for order in performance_orders if order["order"]
        )
        top_floor = Counter(order["order"][0] for order in floor_orders if order["order"])
        followup = [
            {"fold_id": origin["fold"]["fold_id"], **item}
            for origin in evaluated
            for item in origin.get("floor_evidence", [])
            if item.get("method") == method
        ]
        methods[method] = {
            "origins": len(scores),
            "match_weighted": {
                "weight": total_weight,
                "log_loss": weighted_log_loss / total_weight if total_weight else None,
                "brier": weighted_brier / total_weight if total_weight else None,
            },
            "event_paired_stability": {
                "events": len(event_differences),
                "mean_log_loss_difference_vs_scale_1": _mean(event_differences),
                "stdev_log_loss_difference_vs_scale_1": _stdev(event_differences),
                "mean_difference_interval_95": _event_mean_interval(event_differences),
                "interval_method": "paired-event percentile bootstrap; equal event weight, 2000 draws",
                "improved_events": sum(value < 0 for value in event_differences),
                "worsened_events": sum(value > 0 for value in event_differences),
                "records": event_records,
            },
            "performance_order_sensitivity": {
                "by_origin": performance_orders,
                "top_call_counts": dict(sorted(top_performance.items())),
            },
            "floor_order_sensitivity": {
                "by_origin": floor_orders,
                "top_call_counts": dict(sorted(top_floor.items())),
            },
            "named_floor_followup": followup,
            "support_strata": [
                {"fold_id": origin["fold"]["fold_id"], "strata": origin["methods"][method].get("support_strata", {})}
                for origin in evaluated if method in origin.get("methods", {})
            ],
        }
    return methods


def _phase_status(
    methods: Mapping[str, Mapping[str, Any]], selected_method: str | None,
) -> str:
    if not methods or not any(
        item.get("match_weighted", {}).get("weight", 0.0) > 0 for item in methods.values()
    ):
        return "inconclusive"
    if selected_method is None or selected_method not in methods:
        return "tentative"
    selected = methods[selected_method]["match_weighted"]
    baseline = methods.get("1", {}).get("match_weighted", {})
    if selected_method == "1" or baseline.get("log_loss") is None:
        return "tentative"
    log_improves = selected.get("log_loss") is not None and selected["log_loss"] < baseline["log_loss"]
    brier_improves = selected.get("brier") is not None and (
        baseline.get("brier") is None or selected["brier"] < baseline["brier"]
    )
    return "supported" if log_improves and brier_improves else "tentative"


def _phase_summary(
    evaluated: Sequence[Mapping[str, Any]],
    *,
    phase: str,
    selected_method: str | None,
    origins_declared: Sequence[tuple[str, str, str]],
    scales: Sequence[float],
    draws: int,
) -> dict[str, Any]:
    methods = _phase_evidence(evaluated)
    return {
        "protocol_id": "deck-ranking-evaluation-v1",
        "phase": phase,
        "origins_declared": [list(item) for item in origins_declared],
        "prior_scales": list(scales), "draws": draws,
        "card_metadata_policy": DEFAULT_CARD_METADATA_POLICY.model_dump(mode="json"),
        "plan_prior": {
            "method": PLAN_BORROWING_METHOD,
            "strength_cap": DEFAULT_PLAN_PRIOR_STRENGTH_CAP,
            "registry_sha256": _registry_sha256(load_strategic_plan_registry()),
        },
        "selected_candidate": selected_method,
        "status": _phase_status(methods, selected_method),
        "status_note": "Descriptive evidence only; status does not impose a significance or publication gate.",
        "methods": methods,
        "origins": list(evaluated),
    }


def _write_digested(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["artifact_sha256"] = content_sha256(value)
    atomic_write_canonical(path, value)
    return value


def _seal_development_selection(
    root: Path,
    development_summary: Mapping[str, Any],
    *,
    selected_method: str | None,
    scales: Sequence[float],
) -> dict[str, Any]:
    if not selected_method:
        raise ValueError("confirmation requires --selected-method from development results")
    if selected_method not in development_summary.get("methods", {}):
        raise ValueError(f"selected method {selected_method!r} is absent from development results")
    if list(development_summary.get("prior_scales", [])) != list(scales):
        raise ValueError("confirmation prior scales do not match sealed development results")
    summary_path = root / "development-summary.json"
    if not summary_path.exists():
        raise ValueError("confirmation requires a sealed development-summary.json")
    selection = {
        "protocol_id": "deck-ranking-evaluation-v1",
        "selected_method": selected_method,
        "development_summary_sha256": _file_sha256(summary_path),
        "development_artifact_sha256": development_summary["artifact_sha256"],
        "prior_scales": list(scales),
        "development_origins": development_summary.get("origins_declared", []),
    }
    selection_path = root / "development-selection.json"
    expected = dict(selection)
    expected["artifact_sha256"] = content_sha256(expected)
    if selection_path.exists():
        existing = _read_sealed_json(selection_path, description="development selection")
        if _artifact_body(existing) != _artifact_body(expected):
            raise ValueError("development selection is already sealed with a different method or summary")
        return existing
    atomic_write_canonical(selection_path, expected)
    return expected


def _evaluate_frozen_origins(
    source_db: Path,
    root: Path,
    frozen: Sequence[Mapping[str, Any]],
    origins_to_score: Sequence[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    wanted = {
        (cutoff, evaluation_until) for cutoff, evaluation_until, _regime_start in origins_to_score
    }
    evaluated: list[dict[str, Any]] = []
    for artifact in frozen:
        fold = BenchmarkFold.model_validate(artifact["metadata"]["fold"])
        if (fold.cutoff, fold.evaluation_until) not in wanted:
            continue
        outcomes = load_heldout_outcomes(
            Path(source_db), fold,
            expected_rules_sha256=artifact["metadata"]["rules_sha256"],
            card_metadata_policy=DEFAULT_CARD_METADATA_POLICY,
            color_splits_path=COLOR_SPLITS_REGISTRY_PATH,
            expected_color_splits_sha256=artifact["metadata"]["color_splits_sha256"],
        )
        evaluation = evaluate_ranking_origin(artifact, outcomes)
        eval_path = root / f"{fold.cutoff}--{fold.evaluation_until}" / "evaluation.json"
        atomic_write_canonical(eval_path, evaluation)
        evaluated.append(evaluation)
    if len(evaluated) != len(wanted):
        raise ValueError("frozen ranking artifacts do not cover the requested evaluation phase")
    return evaluated


def run_served_model_evaluation(
    source_db: Path,
    output_dir: Path,
    *,
    origins: Sequence[tuple[str, str, str]] = DECLARED_ORIGINS,
    prior_scales: tuple[float, ...] = DEFAULT_PRIOR_SCALES,
    draws: int = DEFAULT_DRAWS,
    phase: str = "development",
    selected_method: str | None = None,
) -> dict[str, Any]:
    """Run the sealed freeze, development, or confirmation experiment phase.

    Development freezes every declared origin before reading the first three
    horizons.  Confirmation only consumes previously sealed predictions and
    requires a development selection artifact before it reads later outcomes.
    """
    scales = _validate_scales(prior_scales)
    if not origins:
        raise ValueError("at least one chronological origin must be declared")
    if phase not in {"freeze", "development", "confirmation", "all"}:
        raise ValueError("phase must be freeze, development, confirmation, or all")
    origins = tuple(tuple(origin) for origin in origins)
    _validate_origins(origins)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    frozen = (
        _load_frozen_origins(root, origins, scales=scales, draws=draws)
        if phase == "confirmation" else
        _freeze_all_origins(Path(source_db), root, origins, scales=scales, draws=draws)
    )
    if phase == "freeze":
        summary = _write_digested(root / "freeze-summary.json", {
            "protocol_id": "deck-ranking-evaluation-v1", "phase": "freeze",
            "origins_declared": [list(item) for item in origins],
            "prior_scales": list(scales), "draws": draws, "status": "frozen",
            "prediction_artifacts": [artifact.get("artifact_sha256") for artifact in frozen],
        })
        return summary

    development_origins, confirmation_origins = _partition_origins(origins)
    if phase == "confirmation":
        development_summary = _read_sealed_json(
            root / "development-summary.json", description="development summary",
        )
        if tuple(tuple(item) for item in development_summary.get("origins_declared", [])) != tuple(origins):
            raise ValueError("development summary origins do not match confirmation origins")
        selection = _seal_development_selection(
            root, development_summary, selected_method=selected_method, scales=scales,
        )
        evaluated = _evaluate_frozen_origins(Path(source_db), root, frozen, confirmation_origins)
        summary = _phase_summary(
            evaluated, phase="confirmation", selected_method=selection["selected_method"],
            origins_declared=origins, scales=scales, draws=draws,
        )
        summary.update({
            "development_summary_sha256": development_summary["artifact_sha256"],
            "development_selection": selection,
            "development": development_summary,
        })
        summary = _write_digested(root / "confirmation-summary.json", summary)
        # summary.json is the convenience output for a one-phase invocation;
        # development already owns that path in a two-phase run.
        if not (root / "summary.json").exists():
            atomic_write_canonical(root / "summary.json", summary)
    else:
        development_evaluated = _evaluate_frozen_origins(
            Path(source_db), root, frozen, development_origins,
        )
        development_summary = _phase_summary(
            development_evaluated, phase="development", selected_method=selected_method,
            origins_declared=origins, scales=scales, draws=draws,
        )
        development_summary = _write_digested(root / "development-summary.json", development_summary)
        if phase == "development":
            summary = development_summary
            atomic_write_canonical(root / "summary.json", summary)
        else:
            selection = _seal_development_selection(
                root, development_summary, selected_method=selected_method, scales=scales,
            )
            evaluated = _evaluate_frozen_origins(Path(source_db), root, frozen, confirmation_origins)
            summary = _phase_summary(
                evaluated, phase="all", selected_method=selection["selected_method"],
                origins_declared=origins, scales=scales, draws=draws,
            )
            summary.update({
                "development_summary_sha256": development_summary["artifact_sha256"],
                "development_selection": selection,
                "development": development_summary,
            })
            summary = _write_digested(root / "summary.json", summary)
    from legacy_engine.advisory.ranking_benchmark import atomic_write_text
    atomic_write_text(root / "summary.md", _markdown_summary(summary))
    return summary


__all__ = [
    "DEFAULT_CARD_METADATA_POLICY", "DEFAULT_PLAN_PRIOR_STRENGTH_CAP",
    "DEFAULT_PRIOR_SCALES", "DECLARED_ORIGINS", "DEVELOPMENT_ORIGINS",
    "CONFIRMATION_ORIGINS", "PLAN_BORROWING_METHOD",
    "evaluate_ranking_origin", "freeze_ranking_origin", "run_served_model_evaluation",
]
