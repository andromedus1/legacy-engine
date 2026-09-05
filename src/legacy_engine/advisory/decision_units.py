"""Descriptive diagnostics for pilotable archetype decision units.

The ranking model remains the authority.  This module only compares the already
published parent and camp estimates and joins those rows to date-bounded deck
and deck-list facts.  In particular, absent matchup cells are missing evidence,
not zero-valued matchups.
"""

from __future__ import annotations

import datetime as dt
import itertools
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from legacy_engine.analytics.match_results import normalize_player

VERSION = "decision-units-v1"
_TOLERANCE = 1e-12


def _date_window(since: str, until: str) -> tuple[str, str]:
    try:
        start = dt.date.fromisoformat(since)
        end = dt.date.fromisoformat(until)
    except (TypeError, ValueError) as exc:
        raise ValueError("decision-unit dates must be ISO dates") from exc
    if end <= start:
        raise ValueError("decision-unit until must be after since")
    return start.isoformat(), end.isoformat()


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _label(row: Mapping[str, Any] | str) -> str:
    if isinstance(row, str):
        return row
    return str(row.get("subject") or row.get("label") or row.get("name") or "")


def _cells(row: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    decision = row.get("decision")
    if isinstance(decision, Mapping) and isinstance(decision.get("cells"), list):
        return (cell for cell in decision["cells"] if isinstance(cell, Mapping))
    raw = row.get("cells")
    return (cell for cell in raw if isinstance(cell, Mapping)) if isinstance(raw, list) else ()


def _cell_values(row: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for cell in _cells(row):
        opponent = cell.get("opponent", cell.get("opp"))
        if opponent is not None and str(opponent):
            mean = _finite(cell.get("mean", cell.get("p")))
            if mean is not None:
                result[str(opponent)] = cell
    return result


def _cell_mean(cell: Mapping[str, Any]) -> float:
    return float(cell.get("mean", cell.get("p")))


def _cell_n(cell: Mapping[str, Any]) -> int:
    value = cell.get("n", cell.get("support_n", 0))
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _share(row: Mapping[str, Any], shares: Mapping[str, Any], label: str) -> float:
    candidates: list[Mapping[str, Any]] = [row]
    decision = row.get("decision")
    if isinstance(decision, Mapping):
        candidates.append(decision)
    for source in candidates:
        for key in ("field_share", "field_share_raw", "decision_field_share"):
            value = _finite(source.get(key))
            if value is not None and value > 0:
                return value
    value = _finite(shares.get(label))
    return value if value is not None and value > 0 else 0.0


def _current_list_count(row: Mapping[str, Any]) -> int:
    for key in ("current_list_count", "list_count", "observed_count"):
        value = row.get(key)
        try:
            if value is not None:
                return max(0, int(value))
        except (TypeError, ValueError):
            pass
    return 0


def _toughest(cells: Mapping[str, Mapping[str, Any]], opponents: Iterable[str]) -> dict[str, Any] | None:
    choices = [
        (opponent, cells[opponent]) for opponent in opponents if opponent in cells
    ]
    if not choices:
        return None
    opponent, cell = min(choices, key=lambda item: (_cell_mean(item[1]), item[0]))
    return {
        "opponent": opponent,
        "mean": _cell_mean(cell),
        "n": _cell_n(cell),
        "prior_contribution_fraction": _finite(cell.get("prior_contribution_fraction")),
        "prior_fraction": _finite(cell.get("prior_contribution_fraction")),
        "prior_source": cell.get("prior_source"),
    }


def _camp_floor(camp: Mapping[str, Any], opponents: Iterable[str]) -> dict[str, Any] | None:
    opponents = tuple(opponents)
    cells = _cell_values(camp)
    toughest = _toughest(cells, opponents) if opponents and all(opp in cells for opp in opponents) else None
    return {
        "camp": _label(camp),
        "camp_name": camp.get("camp", _label(camp)),
        "parent": camp.get("parent"),
        "floor": toughest["mean"] if toughest else None,
        "toughest_pairing": toughest,
        "direct_n": toughest["n"] if toughest else None,
        "total_direct_n": sum(_cell_n(cells[opponent]) for opponent in opponents if opponent in cells),
        "current_list_count": _current_list_count(camp),
        "field_share": _finite(camp.get("field_share")) or 0.0,
        "field_share_raw": _finite(camp.get("field_share_raw")) or 0.0,
    }


def compare_build_floors(
    parent: Mapping[str, Any] | str,
    camps: Iterable[Mapping[str, Any]],
    shares: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare camp floors on the same positive-share external field.

    ``shares`` is the current parent field mapping.  The parent is removed from
    the candidate opponent set for every camp, including when a camp has the
    same label as a parent cell.  All returned estimates are point estimates;
    this diagnostic does not fit a second model or turn absent cells into 0%.
    """
    parent_label = _label(parent)
    camp_rows = list(camps)
    parent_cells = _cell_values(parent) if isinstance(parent, Mapping) else {}
    positive_external = {
        str(opponent): value
        for opponent, raw_share in shares.items()
        if (value := _finite(raw_share)) is not None
        and value > 0
        and str(opponent) != parent_label
    }
    candidate_opponents = tuple(sorted(positive_external))
    camp_weights_raw = {
        _label(camp): _share(camp, shares, _label(camp)) for camp in camp_rows
    }
    camp_weights_total = sum(camp_weights_raw.values())
    camp_weights = {
        label: value / camp_weights_total
        for label, value in camp_weights_raw.items()
        if value > 0 and camp_weights_total > 0
    }
    # A camp with no current share remains visible in composition output, but
    # cannot receive weight in the modeled parent vector or floor comparison.
    included_camps = [camp for camp in camp_rows if _label(camp) in camp_weights]
    camp_cells = {_label(camp): _cell_values(camp) for camp in included_camps}
    common = tuple(
        opponent for opponent in candidate_opponents
        if opponent in parent_cells
        and all(opponent in cells for cells in camp_cells.values())
    )
    missing = tuple(opponent for opponent in candidate_opponents if opponent not in common)
    external_mass = sum(positive_external.values())
    common_mass = sum(positive_external[opponent] for opponent in common)
    coverage = common_mass / external_mass if external_mass else 0.0

    floors = [_camp_floor(camp, candidate_opponents) for camp in included_camps]
    all_floors = [_camp_floor(camp, candidate_opponents) for camp in camp_rows]
    available = bool(common and not missing and len(included_camps) >= 2)
    parent_share = _share(parent, shares, parent_label) if isinstance(parent, Mapping) else (
        _finite(shares.get(parent_label)) or 0.0
    )
    base: dict[str, Any] = {
        "available": available,
        "parent": parent_label,
        "common_opponents": list(common),
        "missing_opponents": list(missing),
        "external_opponent_count": len(candidate_opponents),
        "common_opponent_count": len(common),
        "external_field_share": external_mass,
        "common_field_share": common_mass,
        "common_opponent_coverage": coverage,
        "camp_weights": camp_weights,
        "included_camp_count": len(included_camps),
        "current_camp_share": sum(camp_weights_raw.values()),
        "current_parent_share": parent_share,
        "current_camp_coverage": (
            sum(camp_weights_raw.values()) / parent_share if parent_share > 0 else None
        ),
        "camps": [item for item in all_floors if item is not None],
        "n0_cells_visible": any(
            _cell_n(cells[opponent]) == 0
            for cells in (parent_cells, *camp_cells.values())
            for opponent in common
        ),
    }
    if not available:
        base["unavailable_reason"] = (
            "fewer than two current builds" if len(included_camps) < 2 else
            "missing opponent cells: " + ", ".join(missing) if missing else
            "no positive-share external opponents"
        )
        return base

    camp_floor_by_label = {
        item["camp"]: item["floor"] for item in floors if item is not None
    }
    weighted_camp_floor = sum(
        camp_weights[label] * camp_floor_by_label[label]
        for label in camp_weights
    )
    mixed_vector = {
        opponent: sum(
            camp_weights[_label(camp)] * _cell_mean(camp_cells[_label(camp)][opponent])
            for camp in included_camps
        )
        for opponent in common
    }
    mixed_floor = min(mixed_vector.values())
    parent_floor = min(_cell_mean(parent_cells[opponent]) for opponent in common)
    raw_uplift = mixed_floor - weighted_camp_floor
    base.update({
        "weighted_camp_floor": weighted_camp_floor,
        "mixed_vector_floor": mixed_floor,
        "mixed_vector_toughest": min(
            mixed_vector.items(), key=lambda item: (item[1], item[0])
        )[0],
        "pooling_uplift_raw": raw_uplift,
        "pooling_uplift": max(0.0, raw_uplift) if raw_uplift > -_TOLERANCE else 0.0,
        "parent_floor_same_field": parent_floor,
        "parent_minus_weighted_camp_floor": parent_floor - weighted_camp_floor,
        "parent_minus_mixed_vector_floor": parent_floor - mixed_floor,
        "comparison_note": (
            "Pooling uplift isolates averaging; the parent gap can also reflect "
            "different priors or evidence windows."
        ),
    })
    return base


def _query_rows(con: Any, since: str, until: str, parents: tuple[str, ...]) -> list[tuple[Any, ...]]:
    if not parents:
        return []
    placeholders = ",".join("?" for _ in parents)
    return con.execute(
        f"""
        SELECT d.tournament_id, d.deck_idx, d.player, d.archetype,
               COALESCE(NULLIF(d.variant, ''), 'unlabeled'), t.source
        FROM decks AS d
        JOIN tournaments AS t ON t.id = d.tournament_id
        WHERE CAST(substr(t.date, 1, 10) AS DATE) >= CAST(? AS DATE)
          AND CAST(substr(t.date, 1, 10) AS DATE) < CAST(? AS DATE)
          AND d.archetype IN ({placeholders})
        ORDER BY d.tournament_id, d.deck_idx
        """,
        [since, until, *parents],
    ).fetchall()


def _query_cards(con: Any, since: str, until: str, parents: tuple[str, ...]) -> list[tuple[Any, ...]]:
    if not parents:
        return []
    placeholders = ",".join("?" for _ in parents)
    return con.execute(
        f"""
        SELECT dc.tournament_id, dc.deck_idx, lower(COALESCE(dc.board, 'main')),
               dc.name, dc.count
        FROM deck_cards AS dc
        JOIN decks AS d ON d.tournament_id = dc.tournament_id AND d.deck_idx = dc.deck_idx
        JOIN tournaments AS t ON t.id = dc.tournament_id
        WHERE CAST(substr(t.date, 1, 10) AS DATE) >= CAST(? AS DATE)
          AND CAST(substr(t.date, 1, 10) AS DATE) < CAST(? AS DATE)
          AND d.archetype IN ({placeholders})
        ORDER BY dc.tournament_id, dc.deck_idx, dc.board, dc.name
        """,
        [since, until, *parents],
    ).fetchall()


def _zone_summary(records: list[dict[str, Any]], zone: str) -> dict[str, Any]:
    vectors = [record["cards"].get(zone, {}) for record in records]
    known = [vector for vector in vectors if vector]
    if not known:
        return {
            "slot_distance": None,
            "within_radius": None,
            "card_lists": 0,
            "list_count": len(records),
            "card_coverage": None,
            "available": False,
        }
    names = sorted(set().union(*(vector.keys() for vector in known)))
    means = {name: sum(vector.get(name, 0.0) for vector in known) / len(known) for name in names}
    radius = sum(
        0.5 * sum(abs(vector.get(name, 0.0) - means[name]) for name in names)
        for vector in known
    ) / len(known)
    return {
        "slot_distance": None,
        "within_radius": radius,
        "card_lists": len(known),
        "list_count": len(records),
        "card_coverage": len(known) / len(records) if records else None,
        "available": True,
        "means": means,
    }


def _pair_zone(records_a: list[dict[str, Any]], records_b: list[dict[str, Any]], zone: str) -> dict[str, Any]:
    left = _zone_summary(records_a, zone)
    right = _zone_summary(records_b, zone)
    if left["available"] and right["available"]:
        names = sorted(set(left["means"]) | set(right["means"]))
        distance = 0.5 * sum(
            abs(left["means"].get(name, 0.0) - right["means"].get(name, 0.0))
            for name in names
        )
    else:
        distance = None
    return {
        "slot_distance": distance,
        "within_radius_a": left["within_radius"],
        "within_radius_b": right["within_radius"],
        "card_lists_a": left["card_lists"],
        "card_lists_b": right["card_lists"],
        "list_count_a": left["list_count"],
        "list_count_b": right["list_count"],
        "card_coverage_a": left["card_coverage"],
        "card_coverage_b": right["card_coverage"],
        "available": distance is not None,
    }


def _pilot_summary(records_a: list[dict[str, Any]], records_b: list[dict[str, Any]]) -> dict[str, Any]:
    def handles(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
        return {
            (record["source"], handle)
            for record in records
            if (handle := normalize_player(record.get("player")))
        }
    left, right = handles(records_a), handles(records_b)
    intersection = left & right
    union = left | right
    return {
        "scope": "source + normalize_player(handle)",
        "a": len(left),
        "b": len(right),
        "overlap": len(intersection),
        "union": len(union),
        "jaccard": len(intersection) / len(union) if left and right else None,
        "records_a": len(records_a),
        "records_b": len(records_b),
        "unknown_records_a": sum(not normalize_player(record.get("player")) for record in records_a),
        "unknown_records_b": sum(not normalize_player(record.get("player")) for record in records_b),
        "unknown_excluded": True,
    }


def _composition(
    groups: Mapping[str, list[dict[str, Any]]],
    parent: str,
    camps: list[Mapping[str, Any]],
) -> dict[str, Any]:
    labels = [_label(camp) for camp in camps]
    pairs = []
    for left, right in itertools.combinations(labels, 2):
        left_records, right_records = groups.get(left, []), groups.get(right, [])
        pairs.append({
            "camp_a": left,
            "camp_b": right,
            "main": _pair_zone(left_records, right_records, "main"),
            "side": _pair_zone(left_records, right_records, "side"),
            "pilot_overlap": _pilot_summary(left_records, right_records),
        })
    return {
        "parent": parent,
        "camps": [
            {
                "camp": label,
                "list_count": len(groups.get(label, [])),
                "main_card_lists": sum(bool(record["cards"].get("main")) for record in groups.get(label, [])),
                "side_card_lists": sum(bool(record["cards"].get("side")) for record in groups.get(label, [])),
            }
            for label in labels
        ],
        "camp_pairs": pairs,
    }


def _shares_from_blob(blob: Mapping[str, Any]) -> dict[str, Any]:
    meta = blob.get("meta")
    if isinstance(meta, Mapping):
        model = meta.get("deck_rankings")
        if isinstance(model, Mapping):
            field = model.get("field")
            if isinstance(field, Mapping) and isinstance(field.get("shares"), Mapping):
                return dict(field["shares"])
    shares: dict[str, Any] = {}
    for row in blob.get("arch", ()):
        if isinstance(row, Mapping):
            shares[_label(row)] = row.get("field_share", row.get("field_share_raw", 0.0))
    return shares


def analyze_decision_units(
    con: Any,
    blob: Mapping[str, Any],
    *,
    since: str,
    until: str,
) -> dict[str, Any]:
    """Return date-bounded, descriptive composition and floor diagnostics."""
    since, until = _date_window(since, until)
    all_camps = [row for row in blob.get("camps", ()) if isinstance(row, Mapping)]
    by_parent: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in all_camps:
        parent = str(row.get("parent") or "")
        if parent:
            by_parent[parent].append(row)
    parent_rows = {
        _label(row): row
        for row in blob.get("arch", ())
        if isinstance(row, Mapping) and _label(row)
    }
    parents = tuple(sorted(set(by_parent) & set(parent_rows)))
    deck_rows = _query_rows(con, since, until, parents)
    records: dict[tuple[str, int], dict[str, Any]] = {}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    expected_camps = {
        parent: {_label(camp) for camp in by_parent[parent]} for parent in parents
    }
    for tournament_id, deck_idx, player, archetype, variant, source in deck_rows:
        parent = str(archetype or "")
        camp_label = f"{parent} [{variant or 'unlabeled'}]"
        record = {
            "tournament_id": str(tournament_id),
            "deck_idx": int(deck_idx),
            "player": player,
            "source": str(source or "unknown"),
            "parent": parent,
            "camp": camp_label,
            "cards": {"main": {}, "side": {}},
        }
        records[(str(tournament_id), int(deck_idx))] = record
        if camp_label in expected_camps.get(parent, set()):
            groups[camp_label].append(record)
    for tournament_id, deck_idx, board, name, count in _query_cards(con, since, until, parents):
        record = records.get((str(tournament_id), int(deck_idx)))
        if record is None:
            continue
        zone = "main" if board == "main" else "side" if board == "side" else None
        if zone is None or name is None:
            continue
        try:
            copies = float(count or 0)
        except (TypeError, ValueError):
            continue
        if math.isfinite(copies):
            record["cards"][zone][str(name)] = copies

    shares = _shares_from_blob(blob)
    parents_out = []
    for parent in parents:
        camps = sorted(by_parent[parent], key=lambda row: _label(row))
        parent_for_compare = dict(parent_rows[parent])
        parent_for_compare["field_share"] = _share(parent_for_compare, shares, parent)
        parent_for_compare["current_list_count"] = sum(
            1 for record in records.values() if record["parent"] == parent
        )
        camps_for_compare = []
        for camp in camps:
            camp_copy = dict(camp)
            camp_copy["field_share"] = _share(camp_copy, shares, _label(camp_copy))
            camp_copy["field_share_raw"] = camp_copy["field_share"]
            camp_copy["current_list_count"] = len(groups.get(_label(camp), ()))
            camps_for_compare.append(camp_copy)
        comparison = compare_build_floors(parent_for_compare, camps_for_compare, shares)
        parent_share = _share(parent_for_compare, shares, parent)
        uplift = _finite(comparison.get("pooling_uplift")) or 0.0
        item = {
            "parent": parent,
            "current_parent_share": parent_share,
            "current_list_count": parent_for_compare["current_list_count"],
            "camp_count": len(camps),
            "floor_comparison": comparison,
            "composition": _composition(groups, parent, camps),
            "attention": parent_share * max(0.0, uplift),
        }
        parents_out.append(item)
    parents_out.sort(key=lambda item: (-item["attention"], item["parent"]))
    by_parent_out = {item["parent"]: item for item in parents_out}
    comparable = sum(item["floor_comparison"]["available"] for item in parents_out)
    return {
        "version": VERSION,
        "status": "descriptive",
        "window": {"since": since, "until": until, "until_exclusive": True},
        "method": {
            "external_field_excludes_parent": True,
            "missing_cells": "unavailable",
            "pooling_uplift": "min(weighted camp matchup vector) - weighted camp minima",
            "composition": "main and side 0.5 sum absolute mean-copy differences",
            "pilot_scope": "source-scoped normalize_player handles; unknown excluded",
        },
        "summary": {
            "parents_analyzed": len(parents_out),
            "parents_with_comparison": comparable,
            "top_attention": parents_out[0]["parent"] if parents_out else None,
        },
        "parents": parents_out,
        "by_parent": by_parent_out,
    }


__all__ = ["VERSION", "analyze_decision_units", "compare_build_floors"]
