"""Deterministic explanations for successive published Deck Rankings snapshots.

The ranking page is its own small analytical publication.  This module keeps the
refresh comparison equally small: it reads the already published field weights
and matchup estimates, and does not recalculate either one.  In particular, a
missing matchup is never replaced with a prior or with a re-normalised field
share.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any


_SNAPSHOT_VERSION = 1
_MIRROR_MEAN = 0.5
_MAX_INSIGHTS = 3


class RankingSnapshotError(ValueError):
    """Raised when a published ranking payload cannot be read as a snapshot."""


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _ordered_unique(values: Sequence[object]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _decision(row: Mapping[str, Any]) -> Mapping[str, Any]:
    decision = _mapping(row.get("decision"))
    return decision if decision else row


def _field_shares(blob: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    meta = _mapping(blob.get("meta"))
    deck_rankings = _mapping(meta.get("deck_rankings"))
    field = _mapping(deck_rankings.get("field"))
    raw = field.get("shares")
    if isinstance(raw, Mapping):
        shares = {
            str(label): value
            for label, raw_value in raw.items()
            if (value := _number(raw_value)) is not None and value >= 0
        }
        if shares:
            return shares
    shares = {}
    for row in rows:
        subject = _text(row.get("subject"))
        if subject is None:
            continue
        value = _number(_decision(row).get("field_share"))
        if value is not None and value >= 0:
            shares[subject] = value
    return shares


def _rows(blob: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_rows = blob.get("arch")
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        return []
    return [row for row in raw_rows if isinstance(row, Mapping)]


def _snapshot_shape(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept the public snapshot shape and a previously embedded report blob."""
    if not isinstance(snapshot, Mapping):
        raise RankingSnapshotError("ranking snapshot is not an object")
    if (
        snapshot.get("snapshot_version") == _SNAPSHOT_VERSION
        and all(key in snapshot for key in (
            "field_shares", "eligible_candidates", "candidates", "cell_means", "calls",
        ))
    ):
        return snapshot
    if "meta" in snapshot or "arch" in snapshot:
        return ranking_snapshot(snapshot)
    raise RankingSnapshotError("ranking snapshot lacks its recognized analytical fields")


def _candidate_map(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates = snapshot.get("candidates")
    if isinstance(candidates, Mapping):
        return candidates
    recommendations = snapshot.get("recommendations")
    return recommendations if isinstance(recommendations, Mapping) else {}


def _eligible_candidates(snapshot: Mapping[str, Any]) -> list[str]:
    raw = snapshot.get("eligible_candidates")
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return _ordered_unique(raw)
    return _ordered_unique(
        subject
        for subject, detail in _candidate_map(snapshot).items()
        if isinstance(detail, Mapping) and detail.get("eligible")
    )


def _cell_means(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = snapshot.get("cell_means")
    return raw if isinstance(raw, Mapping) else {}


def _mean_for(snapshot: Mapping[str, Any], candidate: str, opponent: str) -> float | None:
    if candidate == opponent:
        # Mirrors are a structural part of the published field calculation even
        # though the compact decision ledger omits them.
        return _MIRROR_MEAN
    row = _mapping(_cell_means(snapshot).get(candidate))
    return _number(row.get(opponent))


def _support(snapshot: Mapping[str, Any], candidate: str) -> set[str]:
    shares = _mapping(snapshot.get("field_shares"))
    return {
        str(opponent)
        for opponent, value in shares.items()
        if _number(value) is not None and float(value) > 0 and str(opponent) != candidate
    }


def _positive_support(snapshot: Mapping[str, Any]) -> set[str]:
    shares = _mapping(snapshot.get("field_shares"))
    return {
        str(opponent)
        for opponent, value in shares.items()
        if _number(value) is not None and float(value) > 0
    }


def _recommendation(snapshot: Mapping[str, Any], candidate: str) -> Mapping[str, Any]:
    detail = _mapping(_candidate_map(snapshot).get(candidate))
    return detail


def _call_map(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    calls = snapshot.get("calls")
    if isinstance(calls, Mapping):
        return calls
    return {}


def _date(snapshot: Mapping[str, Any], key: str) -> str | None:
    value = _text(snapshot.get(key))
    return value


def _period(snapshot: Mapping[str, Any], previous: Mapping[str, Any] | None = None) -> dict[str, str | None]:
    return {
        "from": _date(previous, "corpus_max") if previous is not None else None,
        "to": _date(snapshot, "corpus_max"),
        "field_since": _date(snapshot, "field_since"),
    }


def _insight(kind: str, text: str, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"type": kind, "text": text, "evidence": dict(evidence or {})}


def _rounded_movement(value: float) -> bool:
    """Return whether a proportion is visible at the report's one-decimal pp scale."""
    return round(value * 100, 1) != 0.0


def _pp(value: float) -> str:
    return f"{value * 100:+.1f}pp"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _decompose_candidate(
    current: Mapping[str, Any], previous: Mapping[str, Any], candidate: str,
) -> dict[str, Any]:
    current_shares = _mapping(current.get("field_shares"))
    previous_shares = _mapping(previous.get("field_shares"))
    union = sorted({
        str(opponent)
        for opponent, value in (*current_shares.items(), *previous_shares.items())
        if _number(value) is not None and float(value) > 0
    })
    missing = [
        opponent
        for opponent in union
        if _mean_for(previous, candidate, opponent) is None
        or _mean_for(current, candidate, opponent) is None
    ]
    if missing:
        return {
            "available": False,
            "candidate": candidate,
            "required_opponents": union,
            "missing_opponents": missing,
            "reason": "missing matchup forecast(s): " + ", ".join(missing),
        }

    field_contribution = 0.0
    matchup_contribution = 0.0
    weighted_previous = 0.0
    weighted_current = 0.0
    for opponent in union:
        w0 = _number(previous_shares.get(opponent)) or 0.0
        w1 = _number(current_shares.get(opponent)) or 0.0
        p0 = _mean_for(previous, candidate, opponent)
        p1 = _mean_for(current, candidate, opponent)
        assert p0 is not None and p1 is not None
        weighted_previous += w0 * p0
        weighted_current += w1 * p1
        field_contribution += (w1 - w0) * (p0 + p1) / 2
        matchup_contribution += (w0 + w1) * (p1 - p0) / 2
    delta = weighted_current - weighted_previous
    # Keep the identity visible in the payload.  Do not round the values used by
    # the identity; rendering is the only place where values are shortened.
    return {
        "available": True,
        "candidate": candidate,
        "old_performance": weighted_previous,
        "new_performance": weighted_current,
        "performance_delta": delta,
        "field_contribution": field_contribution,
        "matchup_contribution": matchup_contribution,
        "identity_error": field_contribution + matchup_contribution - delta,
        "required_opponents": union,
        "support_changed": _support(previous, candidate) != _support(current, candidate),
    }


def ranking_snapshot(blob: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the small, deterministic analytical input used by refresh comparisons.

    The snapshot deliberately excludes generated timestamps, audit strings, and
    browser filter defaults.  It contains global archetype rows only; camps and
    strategic plans are separate report surfaces and do not change the global
    calls being explained here.
    """
    if not isinstance(blob, Mapping):
        raise RankingSnapshotError("ranking report payload is not an object")
    meta = _mapping(blob.get("meta"))
    deck_rankings = _mapping(meta.get("deck_rankings"))
    rows = _rows(blob)
    if not deck_rankings and not rows:
        raise RankingSnapshotError("ranking report has no recognized deck-ranking payload")
    shares = _field_shares(blob, rows)
    cell_means: dict[str, dict[str, float]] = {}
    candidates: dict[str, dict[str, Any]] = {}
    for row in rows:
        subject = _text(row.get("subject"))
        if subject is None:
            continue
        decision = _decision(row)
        cells = decision.get("cells")
        means: dict[str, float] = {}
        if isinstance(cells, Sequence) and not isinstance(cells, (str, bytes)):
            for cell in cells:
                if not isinstance(cell, Mapping):
                    continue
                opponent = _text(cell.get("opponent") or cell.get("opp"))
                mean = _number(cell.get("mean") if "mean" in cell else cell.get("p"))
                if opponent is not None and mean is not None:
                    means[opponent] = mean
        cell_means[subject] = dict(sorted(means.items()))
        candidates[subject] = {
            "eligible": bool(decision.get("eligible")),
            "performance": _number(decision.get("performance")),
            "floor": _number(decision.get("floor")),
            "worst_opponent": _text(decision.get("worst_opponent") or decision.get("floor_opp")),
            "support": sorted(
                opponent for opponent, value in shares.items()
                if value > 0 and opponent != subject
            ),
        }
    calls = {
        "performance": _text(deck_rankings.get("performance_call")),
        "floor": _text(deck_rankings.get("floor_call")),
    }
    method_id = _text(deck_rankings.get("method_id")) or _text(meta.get("method_id"))
    field_since = _text(meta.get("field_since"))
    corpus_max = _text(meta.get("corpus_max"))
    scenario = (
        _text(meta.get("scenario"))
        or _text(meta.get("scenario_id"))
        or _text(deck_rankings.get("scenario"))
        or "global"
    )
    regime = _text(meta.get("regime_card")) or _text(meta.get("regime"))
    observed_field_n = _number(meta.get("observed_field_n"))
    if observed_field_n is None:
        field = _mapping(_mapping(meta.get("deck_rankings")).get("field"))
        observed_field_n = _number(field.get("exact_observed_decks"))
    return {
        "snapshot_version": _SNAPSHOT_VERSION,
        "method_id": method_id,
        "scenario": scenario,
        "regime": regime,
        "field_since": field_since,
        "corpus_max": corpus_max,
        "observed_field_n": observed_field_n,
        "field_shares": dict(sorted(shares.items())),
        "eligible_candidates": sorted(
            subject for subject, detail in candidates.items() if detail["eligible"]
        ),
        "candidates": dict(sorted(candidates.items())),
        "cell_means": dict(sorted(cell_means.items())),
        "calls": calls,
    }


def _compatibility_reason(current: Mapping[str, Any], previous: Mapping[str, Any]) -> str | None:
    checks = (
        ("method", "method_id"),
        ("scenario", "scenario"),
        ("regime", "regime"),
        ("field start", "field_since"),
    )
    for label, key in checks:
        old = previous.get(key)
        new = current.get(key)
        if old != new:
            return f"{label} changed ({old or 'unavailable'} → {new or 'unavailable'})"
    return None


def _comparison_dates(current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    period = _period(current, previous)
    return {
        "from": period["from"],
        "to": period["to"],
        "field_since": period["field_since"],
    }


def _unavailable_insight(reason: str) -> dict[str, Any]:
    return _insight("unavailable", reason, {"available": False, "reason": reason})


def _previous_observed_field_is_empty(snapshot: Mapping[str, Any]) -> bool:
    shares = _mapping(snapshot.get("field_shares"))
    observed = _number(snapshot.get("observed_field_n"))
    if observed == 0:
        return True
    if any((_number(value) or 0.0) > 0 for value in shares.values()):
        return False
    return observed == 0 or not shares


def _analytical_equal(current: Mapping[str, Any], previous: Mapping[str, Any]) -> bool:
    """Compare inputs while treating the corpus cutoff as the period label."""
    return {
        key: value for key, value in current.items() if key != "corpus_max"
    } == {
        key: value for key, value in previous.items() if key != "corpus_max"
    }


def compare_ranking_snapshots(
    current: Mapping[str, Any], previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Compare two compatible published snapshots and return up to three insights."""
    current = _snapshot_shape(current)
    if previous is not None:
        previous = _snapshot_shape(previous)
    result: dict[str, Any] = {
        "status": "baseline" if previous is None else "changed",
        "comparison": _comparison_dates(current, previous),
        "insights": [],
    }
    if previous is None:
        result["reason"] = "no prior recognized ranking snapshot"
        result["insights"] = [_insight(
            "baseline",
            "Baseline published; the next compatible refresh will show movement.",
            {"available": True},
        )]
        return result

    reason = _compatibility_reason(current, previous)
    if reason is not None:
        result["status"] = "incompatible"
        result["reason"] = reason
        result["insights"] = [_unavailable_insight(
            f"Comparison unavailable: {reason}; this publication starts a new baseline."
        )]
        return result

    if _previous_observed_field_is_empty(previous):
        result["status"] = "unavailable"
        result["reason"] = "previous publication has zero observed field"
        result["insights"] = [_unavailable_insight(
            "Field movement unavailable: the previous publication had zero observed field; this publication starts the comparison."
        )]
        return result

    if _analytical_equal(current, previous):
        result["status"] = "unchanged"
        result["reason"] = "analytical snapshot unchanged"
        result["insights"] = [_insight(
            "unchanged",
            "No ranking changes since the previous refresh.",
            {"available": True},
        )]
        return result

    current_shares = _mapping(current.get("field_shares"))
    previous_shares = _mapping(previous.get("field_shares"))
    movements = []
    for name in sorted({*current_shares, *previous_shares}):
        old = _number(previous_shares.get(name)) or 0.0
        new = _number(current_shares.get(name)) or 0.0
        delta = new - old
        if _rounded_movement(delta):
            movements.append((abs(delta), name, old, new, delta))
    movements.sort(key=lambda item: (-item[0], item[1]))
    insights: list[dict[str, Any]] = []
    if movements:
        _absolute, name, old, new, delta = movements[0]
        direction = "gained" if delta > 0 else "lost"
        insights.append(_insight(
            "field_movement",
            f"{name} {direction} {abs(delta) * 100:.1f}pp ({_pct(old)} → {_pct(new)}).",
            {"archetype": name, "old_share": old, "new_share": new, "delta": delta},
        ))

    candidates = sorted({
        *_eligible_candidates(previous), *_eligible_candidates(current),
    })
    decompositions = {
        candidate: _decompose_candidate(current, previous, candidate)
        for candidate in candidates
    }
    gains = [
        value for value in decompositions.values()
        if value.get("available") and _rounded_movement(float(value.get("performance_delta", 0)))
        and float(value["performance_delta"]) > 0
    ]
    gains.sort(key=lambda value: (-float(value["performance_delta"]), str(value["candidate"])))
    if gains:
        value = gains[0]
        insights.append(_insight(
            "beneficiary",
            f"{value['candidate']} improved {float(value['performance_delta']) * 100:.1f}pp in modeled performance; field weights contributed {_pp(float(value['field_contribution']))} and matchup estimates {_pp(float(value['matchup_contribution']))}.",
            value,
        ))

    old_calls = _call_map(previous)
    new_calls = _call_map(current)
    changed_calls = [
        key for key in ("performance", "floor")
        if old_calls.get(key) != new_calls.get(key)
    ]
    if changed_calls:
        parts = []
        evidence: dict[str, Any] = {"calls": {}}
        for key in changed_calls:
            old_call = old_calls.get(key)
            new_call = new_calls.get(key)
            parts.append(f"{key} call {old_call or '—'} → {new_call or '—'}")
            evidence["calls"][key] = {"old": old_call, "new": new_call}
            if key == "performance" and isinstance(new_call, str):
                unavailable_call = {
                    "available": False,
                    "reason": "call candidate is absent from both snapshots",
                }
                old_detail = _recommendation(previous, old_call) if isinstance(old_call, str) else {}
                new_detail = _recommendation(current, new_call) if isinstance(new_call, str) else {}
                evidence["calls"][key].update({
                    "old_attribution": decompositions.get(old_call, unavailable_call),
                    "new_attribution": decompositions.get(new_call, unavailable_call),
                    "performance_attribution": decompositions.get(new_call, unavailable_call),
                    "old_performance": old_detail.get("performance"),
                    "new_performance": new_detail.get("performance"),
                })
            if key == "floor":
                old_detail = _recommendation(previous, old_call) if isinstance(old_call, str) else {}
                new_detail = _recommendation(current, new_call) if isinstance(new_call, str) else {}
                old_support = _positive_support(previous)
                new_support = _positive_support(current)
                old_worst = _text(old_detail.get("worst_opponent"))
                new_worst = _text(new_detail.get("worst_opponent"))
                if old_worst != new_worst:
                    parts.append(f"minimum pairing {old_worst or '—'} → {new_worst or '—'}")
                elif old_support != new_support:
                    parts.append("positive-support opponents changed")
                else:
                    parts.append("minimum pairing support was unchanged")
                evidence["calls"][key].update({
                    "old_floor": old_detail.get("floor"),
                    "new_floor": new_detail.get("floor"),
                    "floor_delta": (
                        new_detail.get("floor") - old_detail.get("floor")
                        if isinstance(new_detail.get("floor"), (int, float))
                        and isinstance(old_detail.get("floor"), (int, float))
                        else None
                    ),
                    "old_worst_opponent": old_worst,
                    "new_worst_opponent": new_worst,
                    "support_changed": old_support != new_support,
                    "performance_attribution": decompositions.get(
                        new_call,
                        {"available": False, "reason": "call candidate is absent from both snapshots"},
                    ) if isinstance(new_call, str) else {
                        "available": False, "reason": "new floor call is unavailable",
                    },
                })
        insights.append(_insight("recommendation", "; ".join(parts) + ".", evidence))

    # If an exact beneficiary decomposition was requested by the changed data
    # but a newly positive opponent lacks a forecast, retain that gap visibly.
    unavailable = [
        value for value in decompositions.values() if not value.get("available")
    ]
    result["unavailable_attributions"] = unavailable
    if unavailable:
        result["status"] = "unavailable"
        result["reason"] = unavailable[0].get(
            "reason", "required matchup forecast is missing"
        )
        unavailable_text = (
            "Performance attribution unavailable: "
            + str(result["reason"])
            + "."
        )
        if not any(item["type"] == "unavailable" for item in insights):
            if len(insights) >= _MAX_INSIGHTS:
                insights[-1] = _unavailable_insight(unavailable_text)
            else:
                insights.append(_unavailable_insight(unavailable_text))
    if not insights:
        result["reason"] = "analytical values changed below the report's one-decimal percentage-point scale"
        insights.append(_insight(
            "unchanged",
            "No changes large enough to report at the 0.1pp display scale; calls are unchanged.",
            {"available": True, "threshold": "0.0pp display movement"},
        ))
    result["insights"] = insights[:_MAX_INSIGHTS]
    return result
