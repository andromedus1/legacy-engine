"""Outcome-free recurrent-era discovery.

The public discovery core in this module intentionally accepts a frozen
``OutcomeFreeCorpus`` rather than a database connection.  ``discovery_source``
is the only adapter which is allowed to know about the tournament database;
this keeps round results, standings, and conversion facts outside the
candidate-generation contract.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import duckdb
import numpy as np
from pydantic import ConfigDict, Field, field_validator, model_validator

from legacy_engine.models.base import LegacyEngineModel

BoundaryKind = Literal["legality", "taxonomy", "source-contract"]
DiscoveryStatus = Literal["candidate", "no-recurrence", "degraded"]
DiscoveryReason = Literal[
    "insufficient-subject-decks",
    "insufficient-reference-buckets",
    "insufficient-reference-decks",
    "insufficient-reference-events",
    "insufficient-historical-decks",
    "insufficient-historical-events",
    "main-shift",
    "sideboard-shift",
    "mixed-configuration",
    "field-shift",
    "source-shift",
    "contract-incompatible",
    "complete-link-conflict",
    "no-historical-segment",
]


class OutcomeFreeModel(LegacyEngineModel):
    """Frozen, closed models at the outcome firewall."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True, validate_assignment=True
    )


class DiscoveryCard(OutcomeFreeModel):
    name: str
    copies: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def _card_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("card name must be non-empty")
        return value


class DiscoveryDeck(OutcomeFreeModel):
    event_id: str
    event_date: date
    deck_idx: int = Field(ge=0)
    pilot_key: str | None
    parent_archetype: str
    source: str
    provenance: str
    mainboard: tuple[DiscoveryCard, ...]
    sideboard: tuple[DiscoveryCard, ...]

    @field_validator("event_id", "parent_archetype", "source", "provenance")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must be non-empty")
        return value

    @field_validator("pilot_key")
    @classmethod
    def _pilot(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().casefold()
        return value or None

    @field_validator("mainboard", "sideboard")
    @classmethod
    def _ordered_cards(cls, cards: tuple[DiscoveryCard, ...]) -> tuple[DiscoveryCard, ...]:
        # Cards are canonicalized at the model boundary as well as by the SQL
        # adapter.  This makes hand-built corpora hash-identical to adapter
        # output and gives callers a deterministic round-trip.
        return tuple(sorted(cards, key=lambda c: (c.name.casefold(), c.name, c.copies)))


class DiscoveryBoundary(OutcomeFreeModel):
    boundary_id: str
    effective_on: date
    kind: BoundaryKind
    hard: bool
    detail: str

    @field_validator("boundary_id", "detail")
    @classmethod
    def _boundary_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("boundary text must be non-empty")
        return value


class DistanceThresholds(OutcomeFreeModel):
    main_js_max: float = Field(ge=0)
    side_js_max: float = Field(ge=0)
    mixture_energy_max: float = Field(ge=0)
    field_js_max: float = Field(ge=0)
    source_js_max: float = Field(ge=0)

    @model_validator(mode="after")
    def _finite(self) -> "DistanceThresholds":
        for key, value in self.model_dump().items():
            if not math.isfinite(value):
                raise ValueError(f"threshold {key} must be finite (got {value!r})")
        return self


class SegmentationWeights(OutcomeFreeModel):
    main: float = Field(ge=0)
    side: float = Field(ge=0)
    field: float = Field(ge=0)
    source: float = Field(ge=0)
    subject_share: float = Field(ge=0)

    @model_validator(mode="after")
    def _valid_weights(self) -> "SegmentationWeights":
        values = self.model_dump()
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError(f"segmentation weights must be finite: {values!r}")
        total = sum(values.values())
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"segmentation weights must sum to 1.0 (got {total!r})")
        return self


class DiscoveryCalibration(OutcomeFreeModel):
    calibration_id: str
    method_id: Literal["segment-fingerprint-complete-link-v1"]
    bucket_days: int = Field(gt=0)
    min_segment_buckets: int = Field(gt=0)
    min_segment_decks: int = Field(gt=0)
    min_segment_events: int = Field(gt=0)
    min_subject_decks: int = Field(gt=0)
    pelt_penalty: float = Field(ge=0)
    smoothing_alpha: float = Field(gt=0)
    weights: SegmentationWeights
    thresholds: DistanceThresholds

    @field_validator("calibration_id")
    @classmethod
    def _calibration_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("calibration_id must be non-empty")
        return value

    @model_validator(mode="after")
    def _finite_values(self) -> "DiscoveryCalibration":
        for key in ("pelt_penalty", "smoothing_alpha"):
            if not math.isfinite(getattr(self, key)):
                raise ValueError(f"calibration {key} must be finite")
        return self


class OutcomeFreeCorpus(OutcomeFreeModel):
    as_of: date
    taxonomy_version: str
    legality_version: str
    provenance_filter: str | None
    semantic_boundaries: tuple[DiscoveryBoundary, ...]
    decks: tuple[DiscoveryDeck, ...]
    source_sha256: str

    @field_validator("taxonomy_version", "legality_version")
    @classmethod
    def _version(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("version must be non-empty")
        return value

    @field_validator("provenance_filter")
    @classmethod
    def _provenance_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("source_sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
        return value


def canonical_json(value: object) -> str:
    """Serialize typed payloads without whitespace or runtime-dependent ordering."""

    if isinstance(value, OutcomeFreeModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_discovery_calibration(path: Path | str) -> DiscoveryCalibration:
    """Load and validate a calibration file, retaining path context on failure."""

    calibration_path = Path(path)
    try:
        raw = json.loads(calibration_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid discovery calibration {calibration_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"invalid discovery calibration {calibration_path}: expected object")
    try:
        return DiscoveryCalibration.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"invalid discovery calibration {calibration_path}: {exc}") from exc


def _canonical_corpus_payload(
    *,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    provenance_filter: str | None,
    semantic_boundaries: tuple[DiscoveryBoundary, ...],
    decks: tuple[DiscoveryDeck, ...],
) -> dict:
    return {
        "as_of": as_of.isoformat(),
        "taxonomy_version": taxonomy_version,
        "legality_version": legality_version,
        "provenance_filter": provenance_filter,
        "semantic_boundaries": [b.model_dump(mode="json") for b in semantic_boundaries],
        "decks": [d.model_dump(mode="json") for d in decks],
    }


def load_outcome_free_corpus(
    con: duckdb.DuckDBPyConnection,
    *,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
) -> OutcomeFreeCorpus:
    """Project the three outcome-free source tables into a closed corpus.

    The SQL intentionally names only ``tournaments``, ``decks`` and
    ``deck_cards`` columns required to describe construction.  In particular it
    does not select ``decks.result`` and never touches ``rounds`` or
    ``standings``.  Querying in two batches also means removing those relations
    cannot alter this adapter's behavior.
    """

    boundaries = tuple(sorted(semantic_boundaries, key=lambda b: (b.effective_on, b.boundary_id)))
    # Validate the supplied boundary models even when an empty corpus is returned.
    for boundary in boundaries:
        if boundary.kind not in ("legality", "taxonomy", "source-contract"):
            raise ValueError(f"invalid boundary kind {boundary.kind!r}")
    taxonomy_version = taxonomy_version.strip()
    legality_version = legality_version.strip()
    if not taxonomy_version:
        raise ValueError("taxonomy_version must be non-empty")
    if not legality_version:
        raise ValueError("legality_version must be non-empty")
    provenance = provenance.strip() if provenance is not None else None
    if provenance == "":
        provenance = None

    deck_rows = con.execute(
        """
        SELECT t.id, CAST(t.date AS DATE), t.source, t.provenance,
               dk.deck_idx, dk.player, dk.archetype
        FROM decks AS dk
        JOIN tournaments AS t ON t.id = dk.tournament_id
        WHERE CAST(t.date AS DATE) <= ?
          AND (? IS NULL OR t.provenance = ?)
          AND dk.archetype IS NOT NULL
        ORDER BY CAST(t.date AS DATE), t.id, dk.deck_idx
        """,
        [as_of, provenance, provenance],
    ).fetchall()

    selected: dict[tuple[str, int], dict] = {}
    for event_id, event_date, source, event_provenance, deck_idx, player, parent in deck_rows:
        event_id = str(event_id).strip()
        if not event_id or parent is None:
            continue
        parent = " ".join(str(parent).split())
        if not parent:
            continue
        source = "unknown" if source is None or not str(source).strip() else str(source).strip()
        event_provenance = (
            "unknown"
            if event_provenance is None or not str(event_provenance).strip()
            else str(event_provenance).strip()
        )
        player_text = " ".join(str(player).split()).casefold() if player is not None else ""
        selected[(event_id, int(deck_idx))] = {
            "event_id": event_id,
            "event_date": event_date,
            "deck_idx": int(deck_idx),
            "pilot_key": f"{event_id}:{player_text}" if player_text else None,
            "parent_archetype": parent,
            "source": source,
            "provenance": event_provenance,
            "mainboard": {},
            "sideboard": {},
        }

    if selected:
        card_rows = con.execute(
            """
            SELECT dc.tournament_id, dc.deck_idx, dc.board, dc.name, dc.count
            FROM deck_cards AS dc
            JOIN tournaments AS t ON t.id = dc.tournament_id
            WHERE CAST(t.date AS DATE) <= ?
              AND (? IS NULL OR t.provenance = ?)
            ORDER BY dc.tournament_id, dc.deck_idx, dc.board, dc.name
            """,
            [as_of, provenance, provenance],
        ).fetchall()
        for event_id, deck_idx, board, name, copies in card_rows:
            key = (str(event_id).strip(), int(deck_idx))
            deck = selected.get(key)
            if deck is None:
                continue
            board_key = str(board or "").strip().casefold()
            if board_key in {"main", "mainboard"}:
                board_key = "mainboard"
            elif board_key in {"side", "sideboard"}:
                board_key = "sideboard"
            else:
                raise ValueError(f"invalid board {board!r} for deck {key!r}")
            copies = int(copies)
            if copies <= 0:
                raise ValueError(f"card copies must be positive for deck {key!r}: {copies}")
            card_name = " ".join(str(name).split())
            if not card_name:
                raise ValueError(f"card name must be non-empty for deck {key!r}")
            bucket: dict[str, tuple[str, int]] = deck[board_key]
            norm_name = card_name.casefold()
            old = bucket.get(norm_name)
            bucket[norm_name] = (old[0], old[1] + copies) if old else (card_name, copies)

    decks = tuple(
        DiscoveryDeck(
            event_id=raw["event_id"],
            event_date=raw["event_date"],
            deck_idx=raw["deck_idx"],
            pilot_key=raw["pilot_key"],
            parent_archetype=raw["parent_archetype"],
            source=raw["source"],
            provenance=raw["provenance"],
            mainboard=tuple(DiscoveryCard(name=name, copies=copies) for name, copies in raw["mainboard"].values()),
            sideboard=tuple(DiscoveryCard(name=name, copies=copies) for name, copies in raw["sideboard"].values()),
        )
        for raw in sorted(selected.values(), key=lambda d: (d["event_date"], d["event_id"], d["deck_idx"]))
    )
    payload = _canonical_corpus_payload(
        as_of=as_of,
        taxonomy_version=taxonomy_version,
        legality_version=legality_version,
        provenance_filter=provenance,
        semantic_boundaries=boundaries,
        decks=decks,
    )
    return OutcomeFreeCorpus(
        as_of=as_of,
        taxonomy_version=taxonomy_version,
        legality_version=legality_version,
        provenance_filter=provenance,
        semantic_boundaries=boundaries,
        decks=decks,
        source_sha256=payload_sha256(payload),
    )


class NamedMass(OutcomeFreeModel):
    key: str
    mass: float = Field(ge=0)

    @field_validator("key")
    @classmethod
    def _mass_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("mass key must be non-empty")
        return value

    @field_validator("mass")
    @classmethod
    def _mass_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("mass must be finite")
        return value


class SegmentSupport(OutcomeFreeModel):
    decks: int = Field(ge=0)
    events: int = Field(ge=0)
    pilots: int = Field(ge=0)
    buckets: int = Field(ge=0)
    max_event_share: float | None = Field(default=None, ge=0, le=1)
    max_pilot_share: float | None = Field(default=None, ge=0, le=1)
    missing_bucket_fraction: float = Field(ge=0, le=1)


class SegmentFingerprint(OutcomeFreeModel):
    segment_id: str
    entity: str
    start: date
    end: date
    reference: bool
    contract_epoch: str
    crossed_boundary_ids: tuple[str, ...]
    support: SegmentSupport
    deck_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    main_slots: tuple[NamedMass, ...]
    side_slots: tuple[NamedMass, ...]
    field_context: tuple[NamedMass, ...]
    source_mix: tuple[NamedMass, ...]
    deck_vectors_sha256: str

    @field_validator("segment_id", "entity", "contract_epoch")
    @classmethod
    def _segment_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("segment text must be non-empty")
        return value

    @model_validator(mode="after")
    def _segment_interval(self) -> "SegmentFingerprint":
        if self.end <= self.start:
            raise ValueError("segment end must be after start")
        if len(self.deck_vectors_sha256) != 64:
            raise ValueError("deck_vectors_sha256 must be a SHA-256 digest")
        return self


class SegmentDistances(OutcomeFreeModel):
    main_js: float = Field(ge=0)
    side_js: float = Field(ge=0)
    mixture_energy: float = Field(ge=0)
    field_js: float = Field(ge=0)
    source_js: float = Field(ge=0)
    normalized_max: float = Field(ge=0)


class SegmentComparison(OutcomeFreeModel):
    comparison_id: str
    left_segment_id: str
    right_segment_id: str
    distances: SegmentDistances | None
    compatible: bool
    reasons: tuple[DiscoveryReason, ...]


class RecurrentCandidateGroup(OutcomeFreeModel):
    candidate_id: str
    reference_segment_id: str
    historical_segment_ids: tuple[str, ...]
    comparison_ids: tuple[str, ...]


class EntityDiscoveryResult(OutcomeFreeModel):
    entity: str
    status: DiscoveryStatus
    reference_segment_id: str | None
    segments: tuple[SegmentFingerprint, ...]
    comparisons: tuple[SegmentComparison, ...]
    candidate: RecurrentCandidateGroup | None
    reasons: tuple[DiscoveryReason, ...]


def _week_start(value: date) -> date:
    return value - timedelta(days=value.isoweekday() - 1)


def _is_subject_label(value: str) -> bool:
    normalized = value.strip().casefold()
    return bool(normalized) and normalized != "unknown" and not normalized.startswith("conflict(")


def _deck_id(deck: DiscoveryDeck) -> str:
    return f"{deck.event_id}:{deck.deck_idx}"


def _card_vector(deck: DiscoveryDeck, board: str, vocabulary: tuple[str, ...]) -> np.ndarray:
    cards = deck.mainboard if board == "main" else deck.sideboard
    values = {card.name.casefold(): card.copies for card in cards}
    vector = np.array([values.get(name, 0) for name in vocabulary], dtype=float)
    total = float(vector.sum())
    return vector / total if total else np.zeros(len(vocabulary), dtype=float)


def _mass_distribution(keys: Sequence[str], alpha: float) -> tuple[NamedMass, ...]:
    counts = Counter(keys)
    if not counts:
        return ()
    names = tuple(sorted(counts))
    denominator = sum(counts.values()) + alpha * len(names)
    return tuple(NamedMass(key=name, mass=(counts[name] + alpha) / denominator) for name in names)


def _board_distribution(decks: Sequence[DiscoveryDeck], board: str, alpha: float) -> tuple[NamedMass, ...]:
    keys: list[str] = []
    for deck in decks:
        cards = deck.mainboard if board == "main" else deck.sideboard
        total = sum(card.copies for card in cards)
        if total:
            # Copy-weighted slot distributions, with every deck contributing
            # the same total mass after normalization.
            keys.extend(card.name.casefold() for card in cards for _ in range(card.copies))
    return _mass_distribution(keys, alpha)


def _distribution_from_values(values: Sequence[str], alpha: float) -> tuple[NamedMass, ...]:
    return _mass_distribution(values, alpha)


def _distribution_map(values: Sequence[NamedMass]) -> dict[str, float]:
    return {value.key: value.mass for value in values}


def _js_distance(left: Sequence[NamedMass], right: Sequence[NamedMass], alpha: float) -> float | None:
    """Base-2 Jensen-Shannon distance over the union vocabulary.

    A missing channel is distinct from a zero distance: callers use ``None``
    to retain an inspectable refusal instead of turning absent evidence into a
    deceptively perfect match.
    """

    if not left or not right:
        return None
    names = sorted(set(v.key for v in left) | {v.key for v in right})
    p = np.array([_distribution_map(left).get(name, alpha) for name in names], dtype=float)
    q = np.array([_distribution_map(right).get(name, alpha) for name in names], dtype=float)
    p /= p.sum()
    q /= q.sum()
    midpoint = (p + q) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        kl_p = np.where(p > 0, p * np.log2(p / midpoint), 0.0).sum()
        kl_q = np.where(q > 0, q * np.log2(q / midpoint), 0.0).sum()
    return float(max(0.0, (kl_p + kl_q) / 2.0))


def _segment_vector(segment: SegmentFingerprint, vocabulary: tuple[str, ...]) -> np.ndarray:
    # The fingerprint stores pooled board distributions; the ledger retains
    # exact per-deck vector membership separately through its digest.  This
    # compact pooled vector is used only as a deterministic fallback if a
    # caller compares hand-built fingerprints without source decks.
    main = _distribution_map(segment.main_slots)
    side = _distribution_map(segment.side_slots)
    return np.array([main.get(key, 0.0) for key in vocabulary] + [side.get(key, 0.0) for key in vocabulary])


def _mixture_energy(
    corpus: OutcomeFreeCorpus,
    left: SegmentFingerprint,
    right: SegmentFingerprint,
) -> float | None:
    by_id = {_deck_id(deck): deck for deck in corpus.decks}
    all_cards = tuple(sorted({card.name.casefold() for deck in corpus.decks for card in (*deck.mainboard, *deck.sideboard)}))
    if not all_cards or not left.deck_ids or not right.deck_ids:
        return None

    def vectors(ids: Sequence[str]) -> np.ndarray:
        out = []
        for deck_id in ids:
            deck = by_id[deck_id]
            out.append(np.concatenate((_card_vector(deck, "main", all_cards), _card_vector(deck, "side", all_cards))))
        return np.asarray(out, dtype=float)

    x, y = vectors(left.deck_ids), vectors(right.deck_ids)
    # Energy distance; the factor is normalized by its maximal Euclidean
    # range for concatenated probability vectors, resulting in [0, 1].
    cross = np.linalg.norm(x[:, None, :] - y[None, :, :], axis=2).mean()
    within_x = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2).mean()
    within_y = np.linalg.norm(y[:, None, :] - y[None, :, :], axis=2).mean()
    value = max(0.0, 2.0 * cross - within_x - within_y)
    return float(min(1.0, value / math.sqrt(2.0)))


def _hard_epoch(boundaries: Sequence[DiscoveryBoundary], start: date) -> str:
    relevant = [b.boundary_id for b in boundaries if b.hard and b.effective_on <= start]
    return "epoch:" + (relevant[-1] if relevant else "initial")


def _crossed_hard_boundaries(
    boundaries: Sequence[DiscoveryBoundary], start: date, end: date
) -> tuple[str, ...]:
    return tuple(b.boundary_id for b in boundaries if b.hard and start < b.effective_on < end)


def _feature_signature(
    decks: Sequence[DiscoveryDeck],
    field_decks: Sequence[DiscoveryDeck],
    entity: str,
    calibration: DiscoveryCalibration,
) -> tuple[np.ndarray, tuple[NamedMass, ...], tuple[NamedMass, ...], tuple[NamedMass, ...], tuple[NamedMass, ...]]:
    vocab = tuple(sorted({card.name.casefold() for deck in field_decks for card in (*deck.mainboard, *deck.sideboard)}))
    main = _board_distribution(decks, "main", calibration.smoothing_alpha)
    side = _board_distribution(decks, "side", calibration.smoothing_alpha)
    field = _distribution_from_values(
        [deck.parent_archetype.casefold() for deck in field_decks if _is_subject_label(deck.parent_archetype) and deck.parent_archetype != entity],
        calibration.smoothing_alpha,
    )
    source = _distribution_from_values([deck.source.casefold() for deck in decks], calibration.smoothing_alpha)
    subject_share = len(decks) / len(field_decks) if field_decks else 0.0
    main_vec = np.array([_distribution_map(main).get(name, 0.0) for name in vocab], dtype=float)
    side_vec = np.array([_distribution_map(side).get(name, 0.0) for name in vocab], dtype=float)
    field_vec = np.array([_distribution_map(field).get(name, 0.0) for name in sorted({v.key for v in field})], dtype=float)
    source_vec = np.array([_distribution_map(source).get(name, 0.0) for name in sorted({v.key for v in source})], dtype=float)
    vector = np.concatenate((main_vec, side_vec, field_vec, source_vec, np.array([subject_share])))
    return vector, main, side, field, source


def _segment_distance_for_weeks(
    left: Sequence[DiscoveryDeck], right: Sequence[DiscoveryDeck], field_left: Sequence[DiscoveryDeck], field_right: Sequence[DiscoveryDeck],
    entity: str, calibration: DiscoveryCalibration,
) -> float:
    _, left_main, left_side, left_field, left_source = _feature_signature(left, field_left, entity, calibration)
    _, right_main, right_side, right_field, right_source = _feature_signature(right, field_right, entity, calibration)
    channels = (
        (_js_distance(left_main, right_main, calibration.smoothing_alpha), calibration.weights.main),
        (_js_distance(left_side, right_side, calibration.smoothing_alpha), calibration.weights.side),
        (_js_distance(left_field, right_field, calibration.smoothing_alpha), calibration.weights.field),
        (_js_distance(left_source, right_source, calibration.smoothing_alpha), calibration.weights.source),
    )
    score = sum((value or 0.0) * weight for value, weight in channels)
    return float(score)


def _make_segment(
    corpus: OutcomeFreeCorpus,
    entity: str,
    start: date,
    end: date,
    reference: bool,
    bucket_decks: Sequence[Sequence[DiscoveryDeck]],
    all_bucket_decks: Sequence[Sequence[DiscoveryDeck]],
    calibration: DiscoveryCalibration,
) -> SegmentFingerprint:
    decks = [deck for bucket in bucket_decks for deck in bucket]
    field_decks = [deck for bucket in all_bucket_decks for deck in bucket]
    main = _board_distribution(decks, "main", calibration.smoothing_alpha)
    side = _board_distribution(decks, "side", calibration.smoothing_alpha)
    field = _distribution_from_values(
        [deck.parent_archetype.casefold() for deck in field_decks if _is_subject_label(deck.parent_archetype) and deck.parent_archetype != entity],
        calibration.smoothing_alpha,
    )
    source = _distribution_from_values([deck.source.casefold() for deck in decks], calibration.smoothing_alpha)
    event_ids = tuple(sorted({deck.event_id for deck in decks}))
    pilot_ids = {deck.pilot_key for deck in decks if deck.pilot_key}
    event_counts = Counter(deck.event_id for deck in decks)
    pilot_counts = Counter(deck.pilot_key for deck in decks if deck.pilot_key)
    total_decks = len(decks)
    support = SegmentSupport(
        decks=total_decks,
        events=len(event_ids),
        pilots=len(pilot_ids),
        buckets=len(bucket_decks),
        max_event_share=max(event_counts.values(), default=0) / total_decks if total_decks else None,
        max_pilot_share=max(pilot_counts.values(), default=0) / total_decks if total_decks and pilot_counts else None,
        missing_bucket_fraction=(sum(not bucket for bucket in bucket_decks) / len(bucket_decks)) if bucket_decks else 1.0,
    )
    vectors_payload = []
    all_cards = tuple(sorted({card.name.casefold() for deck in corpus.decks for card in (*deck.mainboard, *deck.sideboard)}))
    for deck in sorted(decks, key=lambda d: (d.event_date, d.event_id, d.deck_idx)):
        vectors_payload.append({
            "id": _deck_id(deck),
            "main": _card_vector(deck, "main", all_cards).round(12).tolist(),
            "side": _card_vector(deck, "side", all_cards).round(12).tolist(),
        })
    vector_digest = payload_sha256(vectors_payload)
    crossed = _crossed_hard_boundaries(corpus.semantic_boundaries, start, end)
    segment_payload = {
        "entity": entity,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "reference": reference,
        "source_sha256": corpus.source_sha256,
        "method_id": calibration.method_id,
    }
    segment_id = "segment-" + payload_sha256(segment_payload)[:24]
    return SegmentFingerprint(
        segment_id=segment_id,
        entity=entity,
        start=start,
        end=end,
        reference=reference,
        contract_epoch=_hard_epoch(corpus.semantic_boundaries, start),
        crossed_boundary_ids=crossed,
        support=support,
        deck_ids=tuple(item["id"] for item in vectors_payload),
        event_ids=event_ids,
        main_slots=main,
        side_slots=side,
        field_context=field,
        source_mix=source,
        deck_vectors_sha256=vector_digest,
    )


def segment_parent_archetype(
    corpus: OutcomeFreeCorpus,
    entity: str,
    calibration: DiscoveryCalibration,
    *,
    seed: int = 0,
) -> tuple[SegmentFingerprint, ...]:
    """Build deterministic weekly fingerprints for one parent archetype."""

    del seed  # The v1 method is deterministic; retained in the contract for future challengers.
    if not _is_subject_label(entity):
        return ()
    subject = [deck for deck in corpus.decks if deck.parent_archetype == entity]
    if len(subject) < calibration.min_subject_decks:
        return ()
    all_labeled = [deck for deck in corpus.decks if _is_subject_label(deck.parent_archetype)]
    if not all_labeled:
        return ()
    first = _week_start(min(deck.event_date for deck in corpus.decks))
    final = corpus.as_of + timedelta(days=1)
    # Calendar buckets are never extended past the explicit cutoff.  The final
    # bucket is consequently the current reference interval ending at as_of+1.
    starts: list[date] = []
    cursor = first
    while cursor < final:
        starts.append(cursor)
        cursor += timedelta(days=calibration.bucket_days)
    bucket_subject = [
        [deck for deck in subject if start <= deck.event_date < min(start + timedelta(days=calibration.bucket_days), final)]
        for start in starts
    ]
    bucket_field = [
        [deck for deck in all_labeled if start <= deck.event_date < min(start + timedelta(days=calibration.bucket_days), final)]
        for start in starts
    ]
    if not starts:
        return ()

    # A small dynamic boundary detector.  The score is the weighted change in
    # channel distributions at a prospective cut.  PELT's penalty is applied
    # as a minimum gain over the local neighboring score, which avoids
    # over-segmenting sparse weekly noise while remaining fully reproducible.
    boundaries: set[int] = set()
    min_size = calibration.min_segment_buckets
    if len(starts) >= 2 * min_size:
        local_scores = []
        for index in range(1, len(starts)):
            local_scores.append(_segment_distance_for_weeks(
                bucket_subject[index - 1], bucket_subject[index],
                bucket_field[index - 1], bucket_field[index], entity, calibration,
            ))
        for index, score in enumerate(local_scores, start=1):
            if index < min_size or len(starts) - index < min_size:
                continue
            neighborhood = local_scores[max(0, index - 2):min(len(local_scores), index + 1)]
            baseline = float(np.median(neighborhood)) if neighborhood else 0.0
            if score > max(0.08, baseline + calibration.pelt_penalty * 0.10):
                boundaries.add(index)
    # Hard semantic boundaries are exact, inclusive for the new interval.
    for boundary in corpus.semantic_boundaries:
        if not boundary.hard:
            continue
        if first < boundary.effective_on < final:
            index = max(0, min(len(starts), (boundary.effective_on - first).days // calibration.bucket_days))
            if min_size <= index <= len(starts) - min_size:
                boundaries.add(index)

    cuts = [0] + sorted(boundaries) + [len(starts)]
    segments: list[SegmentFingerprint] = []
    for start_index, end_index in zip(cuts, cuts[1:]):
        # Preserve all nominated slices, including thin segments: downstream
        # comparison emits typed floor refusals rather than hiding evidence.
        start = starts[start_index]
        end = final if end_index == len(starts) else starts[end_index]
        segments.append(_make_segment(
            corpus, entity, start, end, end == final,
            bucket_subject[start_index:end_index], bucket_field[start_index:end_index], calibration,
        ))
    return tuple(segments)


def compare_segment_fingerprints(
    corpus: OutcomeFreeCorpus,
    left: SegmentFingerprint,
    right: SegmentFingerprint,
    calibration: DiscoveryCalibration,
) -> SegmentComparison:
    """Compare two fingerprints and retain all channel-level refusal reasons."""

    comparison_id = "comparison-" + payload_sha256({"left": left.segment_id, "right": right.segment_id})[:24]
    reasons: list[DiscoveryReason] = []
    if left.contract_epoch != right.contract_epoch or left.crossed_boundary_ids or right.crossed_boundary_ids:
        return SegmentComparison(
            comparison_id=comparison_id,
            left_segment_id=left.segment_id,
            right_segment_id=right.segment_id,
            distances=None,
            compatible=False,
            reasons=("contract-incompatible",),
        )
    if left.support.decks < calibration.min_segment_decks or right.support.decks < calibration.min_segment_decks:
        reasons.append("insufficient-historical-decks")
    if left.support.events < calibration.min_segment_events or right.support.events < calibration.min_segment_events:
        reasons.append("insufficient-historical-events")
    main = _js_distance(left.main_slots, right.main_slots, calibration.smoothing_alpha)
    side = _js_distance(left.side_slots, right.side_slots, calibration.smoothing_alpha)
    field = _js_distance(left.field_context, right.field_context, calibration.smoothing_alpha)
    source = _js_distance(left.source_mix, right.source_mix, calibration.smoothing_alpha)
    mixture = _mixture_energy(corpus, left, right)
    if main is None:
        reasons.append("main-shift")
    if side is None:
        reasons.append("sideboard-shift")
    if field is None:
        reasons.append("field-shift")
    if source is None:
        reasons.append("source-shift")
    if mixture is None:
        reasons.append("mixed-configuration")
    if reasons and any(reason in {"main-shift", "sideboard-shift", "field-shift", "source-shift", "mixed-configuration"} for reason in reasons):
        return SegmentComparison(
            comparison_id=comparison_id,
            left_segment_id=left.segment_id,
            right_segment_id=right.segment_id,
            distances=None,
            compatible=False,
            reasons=tuple(dict.fromkeys(reasons)),
        )
    assert main is not None and side is not None and field is not None and source is not None and mixture is not None
    normalized_max = max(
        main / max(calibration.thresholds.main_js_max, 1e-12),
        side / max(calibration.thresholds.side_js_max, 1e-12),
        mixture / max(calibration.thresholds.mixture_energy_max, 1e-12),
        field / max(calibration.thresholds.field_js_max, 1e-12),
        source / max(calibration.thresholds.source_js_max, 1e-12),
    )
    distances = SegmentDistances(
        main_js=main, side_js=side, mixture_energy=mixture,
        field_js=field, source_js=source, normalized_max=normalized_max,
    )
    if main > calibration.thresholds.main_js_max:
        reasons.append("main-shift")
    if side > calibration.thresholds.side_js_max:
        reasons.append("sideboard-shift")
    if mixture > calibration.thresholds.mixture_energy_max:
        reasons.append("mixed-configuration")
    if field > calibration.thresholds.field_js_max:
        reasons.append("field-shift")
    if source > calibration.thresholds.source_js_max:
        reasons.append("source-shift")
    return SegmentComparison(
        comparison_id=comparison_id,
        left_segment_id=left.segment_id,
        right_segment_id=right.segment_id,
        distances=distances,
        compatible=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def discover_recurrent_states(
    corpus: OutcomeFreeCorpus,
    calibration: DiscoveryCalibration,
    *,
    seed: int = 0,
) -> tuple[EntityDiscoveryResult, ...]:
    """Nominate complete-link historical groups for every eligible parent."""

    entities = sorted({deck.parent_archetype for deck in corpus.decks if _is_subject_label(deck.parent_archetype)})
    results: list[EntityDiscoveryResult] = []
    for entity in entities:
        subject_count = sum(deck.parent_archetype == entity for deck in corpus.decks)
        if subject_count < calibration.min_subject_decks:
            continue
        segments = segment_parent_archetype(corpus, entity, calibration, seed=seed)
        if not segments:
            results.append(EntityDiscoveryResult(
                entity=entity, status="degraded", reference_segment_id=None,
                segments=(), comparisons=(), candidate=None,
                reasons=("insufficient-subject-decks",),
            ))
            continue
        reference = next((segment for segment in reversed(segments) if segment.reference), None)
        if reference is None:
            results.append(EntityDiscoveryResult(
                entity=entity, status="degraded", reference_segment_id=None,
                segments=segments, comparisons=(), candidate=None,
                reasons=("no-historical-segment",),
            ))
            continue
        current_reasons: list[DiscoveryReason] = []
        if reference.support.buckets < calibration.min_segment_buckets:
            current_reasons.append("insufficient-reference-buckets")
        if reference.support.decks < calibration.min_segment_decks:
            current_reasons.append("insufficient-reference-decks")
        if reference.support.events < calibration.min_segment_events:
            current_reasons.append("insufficient-reference-events")
        comparisons: list[SegmentComparison] = []
        historical = [segment for segment in segments if not segment.reference]
        direct: list[tuple[SegmentFingerprint, SegmentComparison]] = []
        for candidate in historical:
            comparison = compare_segment_fingerprints(corpus, reference, candidate, calibration)
            comparisons.append(comparison)
            if comparison.compatible and candidate.support.decks >= calibration.min_segment_decks and candidate.support.events >= calibration.min_segment_events:
                direct.append((candidate, comparison))
        direct.sort(key=lambda item: (item[1].distances.normalized_max if item[1].distances else float("inf"), item[0].start, item[0].segment_id))
        group: list[SegmentFingerprint] = []
        accepted_comparisons: list[str] = []
        for candidate, direct_comparison in direct:
            conflict = False
            for admitted in group:
                pair = compare_segment_fingerprints(corpus, admitted, candidate, calibration)
                comparisons.append(pair)
                if not pair.compatible:
                    conflict = True
            if conflict:
                # Keep the direct comparison and attach a persisted reason to
                # the pair that could not satisfy complete-link membership.
                comparisons.append(direct_comparison.model_copy(update={
                    "reasons": tuple(dict.fromkeys((*direct_comparison.reasons, "complete-link-conflict"))),
                    "compatible": False,
                }))
                continue
            group.append(candidate)
            accepted_comparisons.append(direct_comparison.comparison_id)
        comparisons = sorted({comparison.comparison_id: comparison for comparison in comparisons}.values(), key=lambda c: c.comparison_id)
        if current_reasons:
            status: DiscoveryStatus = "degraded"
            result_reasons = tuple(dict.fromkeys(current_reasons))
            candidate_group = None
        elif not group:
            status = "no-recurrence"
            result_reasons = ("no-historical-segment",)
            candidate_group = None
        else:
            hist_ids = tuple(segment.segment_id for segment in sorted(group, key=lambda s: (s.start, s.segment_id)))
            candidate_id = "candidate-" + payload_sha256({"reference": reference.segment_id, "historical": hist_ids})[:24]
            candidate_group = RecurrentCandidateGroup(
                candidate_id=candidate_id,
                reference_segment_id=reference.segment_id,
                historical_segment_ids=hist_ids,
                comparison_ids=tuple(sorted(accepted_comparisons)),
            )
            status = "candidate"
            result_reasons = ()
        results.append(EntityDiscoveryResult(
            entity=entity, status=status, reference_segment_id=reference.segment_id,
            segments=segments, comparisons=tuple(comparisons), candidate=candidate_group,
            reasons=result_reasons,
        ))
    return tuple(results)
