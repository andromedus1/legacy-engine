#!/usr/bin/env python3
"""Descriptive chronological evaluation for the current deck-ranking inputs.

Each fold uses complete tournament calendar days.  The field is built from
``[start, cutoff)`` and scored on ``[cutoff, next_cutoff)``.  Consequently a
published list on the cutoff day cannot leak into its own prediction.  The
script compares fixed, predeclared half-lives (14, 28 and 56 days) with a
uniform weighting baseline.  It reports scores; it does not tune a method or
create a deployment gate.

The optional matchup pass builds one pre-cutoff adaptive posterior per fold
and scores the holdout's directed matchup cells once per *unordered* pair.
``compute_match_results`` emits both directions of a decisive match, so using
both directions here would double count it. Mirrors are reported as excluded
context because they have no directional outcome.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from legacy_engine.advisory.recent_field import build_recent_field

UNIFORM = None
METHODS: tuple[float | None, ...] = (14.0, 28.0, 56.0, UNIFORM)
_LOG_EPSILON = 1e-12


@dataclass(frozen=True)
class FieldForecastFold:
    cutoff: str
    holdout_until: str
    holdout_classified_decks: int
    holdout_unlabeled_decks: int
    logloss: float | None
    brier: float | None
    unseen_label_decks: int

@dataclass(frozen=True)
class FieldForecastScore:
    method: str
    half_life_days: float | None
    folds: tuple[FieldForecastFold, ...]
    scored_decks: int
    logloss: float | None
    brier: float | None

@dataclass(frozen=True)
class MatchForecastScore:
    cutoff: str
    holdout_until: str
    scored_matches: int
    scored_pairs: int
    unscored_pairs: int
    holdout_mirror_matches: int
    logloss: float | None
    brier: float | None
    available: bool = True
    unavailable_reason: str | None = None

@dataclass(frozen=True)
class ChronologicalEvaluation:
    since: str
    until: str
    provenance: str | None
    field_scores: tuple[FieldForecastScore, ...]
    match_scores: tuple[MatchForecastScore, ...]
    source_selection_note: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _date_only(value: object) -> date:
    text = str(value).strip()
    return date.fromisoformat(text[:10])


def _event_dates(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str,
    until: str,
    provenance: str | None,
) -> tuple[str, ...]:
    predicates = ["date IS NOT NULL", "substr(date, 1, 10) >= ?", "substr(date, 1, 10) < ?"]
    params: list[object] = [since, until]
    if provenance is not None:
        predicates.append("provenance = ?")
        params.append(provenance)
    rows = con.execute(
        f"SELECT DISTINCT substr(date, 1, 10) FROM tournaments WHERE {' AND '.join(predicates)} ORDER BY 1",
        params,
    ).fetchall()
    result: list[str] = []
    for (value,) in rows:
        try:
            result.append(_date_only(value).isoformat())
        except ValueError:
            continue
    return tuple(result)


def _fold_boundaries(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str,
    until: str,
    provenance: str | None,
) -> tuple[tuple[str, str], ...]:
    """Return ``(cutoff, holdout_until)`` pairs at complete day boundaries."""

    dates = _event_dates(con, since=since, until=until, provenance=provenance)
    # There must be at least one complete pre-cutoff day.  A final explicit
    # ``until`` includes the last date; otherwise callers infer max+1 day.
    if len(dates) < 2:
        return ()
    return tuple((dates[index], dates[index + 1]) for index in range(1, len(dates) - 1)) + (
        (dates[-1], until),
    )


def _field_scores_for_method(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str,
    provenance: str | None,
    half_life_days: float | None,
    boundaries: Sequence[tuple[str, str]],
) -> FieldForecastScore:
    method_name = "uniform" if half_life_days is None else f"half-life-{half_life_days:g}d"
    folds: list[FieldForecastFold] = []
    total_logloss = 0.0
    total_brier = 0.0
    total_n = 0

    for cutoff, holdout_until in boundaries:
        training = build_recent_field(
            con,
            since=since,
            until=cutoff,
            half_life_days=math.inf if half_life_days is None else half_life_days,
            provenance=provenance,
        )
        holdout = build_recent_field(
            con,
            since=cutoff,
            until=holdout_until,
            half_life_days=math.inf,
            provenance=provenance,
        )
        n = holdout.exact_classified_decks
        if n == 0:
            folds.append(
                FieldForecastFold(
                    cutoff=cutoff,
                    holdout_until=holdout_until,
                    holdout_classified_decks=0,
                    holdout_unlabeled_decks=holdout.exact_unlabeled_decks,
                    logloss=None,
                    brier=None,
                    unseen_label_decks=0,
                )
            )
            continue

        labels = set(training.shares) | set(holdout.exact_counts)
        unseen = sum(
            count for label, count in holdout.exact_counts.items() if label not in training.shares
        )
        fold_logloss = 0.0
        fold_brier = 0.0
        for actual, count in holdout.exact_counts.items():
            probability = max(_LOG_EPSILON, training.shares.get(actual, 0.0))
            fold_logloss += count * -math.log(probability)
            # Multiclass Brier score: one one-hot vector per observed deck.
            one_deck_brier = sum(
                (training.shares.get(label, 0.0) - (1.0 if label == actual else 0.0)) ** 2
                for label in labels
            )
            fold_brier += count * one_deck_brier
        fold_logloss /= n
        fold_brier /= n
        total_logloss += fold_logloss * n
        total_brier += fold_brier * n
        total_n += n
        folds.append(
            FieldForecastFold(
                cutoff=cutoff,
                holdout_until=holdout_until,
                holdout_classified_decks=n,
                holdout_unlabeled_decks=holdout.exact_unlabeled_decks,
                logloss=fold_logloss,
                brier=fold_brier,
                unseen_label_decks=unseen,
            )
        )

    return FieldForecastScore(
        method=method_name,
        half_life_days=half_life_days,
        folds=tuple(folds),
        scored_decks=total_n,
        logloss=total_logloss / total_n if total_n else None,
        brier=total_brier / total_n if total_n else None,
    )


def evaluate_field_methods(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str,
    until: str,
    provenance: str | None = None,
    half_lives: Iterable[float | None] = METHODS,
) -> tuple[FieldForecastScore, ...]:
    """Evaluate fixed recency methods on chronological complete-day folds."""

    start_date = _date_only(since)
    end_date = _date_only(until)
    if end_date <= start_date:
        raise ValueError("until must be after since")
    boundaries = _fold_boundaries(
        con,
        since=start_date.isoformat(),
        until=end_date.isoformat(),
        provenance=provenance,
    )
    return tuple(
        _field_scores_for_method(
            con,
            since=start_date.isoformat(),
            provenance=provenance,
            half_life_days=half_life,
            boundaries=boundaries,
        )
        for half_life in half_lives
    )


def _score_match_fold(
    con: duckdb.DuckDBPyConnection,
    *,
    cutoff: str,
    holdout_until: str,
    provenance: str | None,
) -> MatchForecastScore:
    """Score each decisive holdout match once, with a pre-cutoff matrix."""

    from legacy_engine.analytics.match_results import compute_match_results
    from legacy_engine.analytics.matchup import build_adaptive_matrix

    holdout = compute_match_results(
        con, provenance=provenance, since=cutoff, until=holdout_until,
    )
    try:
        # An explicit empty horizon map avoids consulting post-cutoff era
        # metadata whose as-of status may not be reproducible in old caches.
        posterior = build_adaptive_matrix(
            con,
            provenance=provenance,
            min_row_share=0.0,
            horizons={},
            until=cutoff,
        )
    except Exception as exc:  # optional pass: field scores remain usable
        return MatchForecastScore(
            cutoff=cutoff,
            holdout_until=holdout_until,
            scored_matches=0,
            scored_pairs=0,
            unscored_pairs=len({tuple(sorted(pair)) for pair in holdout.matchups}),
            holdout_mirror_matches=holdout.coverage.mirror_matches,
            logloss=None,
            brier=None,
            available=False,
            unavailable_reason=f"pre-cutoff matchup posterior unavailable: {exc}",
        )

    logloss_sum = 0.0
    brier_sum = 0.0
    scored_matches = 0
    scored_pairs = 0
    unscored_pairs = 0
    # A MatchResults scan materializes (a,b) and (b,a) for one match.  Lexical
    # ordering chooses exactly one direction for scoring and preserves that
    # direction's wins/losses perspective.
    for a, b in sorted(holdout.matchups):
        if a >= b:
            continue
        tally = holdout.matchups[(a, b)]
        cell = posterior.matrix.cells.get((a, b))
        if cell is None or cell.p_shrunk is None:
            unscored_pairs += 1
            continue
        n = tally.n
        if n <= 0:
            continue
        p = min(1.0 - _LOG_EPSILON, max(_LOG_EPSILON, float(cell.p_shrunk)))
        losses = n - tally.wins
        logloss_sum += -(tally.wins * math.log(p) + losses * math.log1p(-p))
        brier_sum += tally.wins * (1.0 - p) ** 2 + losses * p**2
        scored_matches += n
        scored_pairs += 1
    return MatchForecastScore(
        cutoff=cutoff,
        holdout_until=holdout_until,
        scored_matches=scored_matches,
        scored_pairs=scored_pairs,
        unscored_pairs=unscored_pairs,
        holdout_mirror_matches=holdout.coverage.mirror_matches,
        logloss=logloss_sum / scored_matches if scored_matches else None,
        brier=brier_sum / scored_matches if scored_matches else None,
    )


def evaluate_chronologically(
    con: duckdb.DuckDBPyConnection,
    *,
    since: str,
    until: str,
    provenance: str | None = None,
    half_lives: Iterable[float | None] = METHODS,
    include_matchups: bool = True,
) -> ChronologicalEvaluation:
    """Run descriptive field and optional shared-posterior evaluations."""

    start = _date_only(since).isoformat()
    end = _date_only(until).isoformat()
    boundaries = _fold_boundaries(con, since=start, until=end, provenance=provenance)
    field_scores = evaluate_field_methods(
        con,
        since=start,
        until=end,
        provenance=provenance,
        half_lives=half_lives,
    )
    match_scores = (
        tuple(
            _score_match_fold(
                con,
                cutoff=cutoff,
                holdout_until=holdout_until,
                provenance=provenance,
            )
            for cutoff, holdout_until in boundaries
        )
        if include_matchups else ()
    )
    return ChronologicalEvaluation(
        since=start,
        until=end,
        provenance=provenance,
        field_scores=field_scores,
        match_scores=match_scores,
        source_selection_note=(
            "Scores use the requested provenance filter and observed published lists. "
            "They do not verify that a source is complete or tune source selection; "
            "unlabeled decks are reported separately and omitted from categorical scores."
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="DuckDB path")
    parser.add_argument("--since", required=False, help="inclusive first event date")
    parser.add_argument("--until", required=False, help="exclusive final event date")
    parser.add_argument("--provenance", default=None, help="optional tournaments.provenance filter")
    parser.add_argument(
        "--no-matchups", action="store_true", help="skip the optional adaptive matchup pass"
    )
    parser.add_argument(
        "--served-model", action="store_true",
        help="freeze and score the current served Deck Rankings model on declared origins",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        help="artifact directory for --served-model (for example data/benchmarks/deck-rankings-evaluation-v1)",
    )
    parser.add_argument(
        "--origin", action="append", metavar="CUTOFF,UNTIL,REGIME_START",
        help="one predeclared served-model origin; repeat to replace the six defaults",
    )
    parser.add_argument(
        "--prior-scale", action="append", type=float, dest="prior_scales",
        help="fixed prior-strength sensitivity scale; repeat (defaults to 1,0.5,2)",
    )
    parser.add_argument(
        "--draws", type=int, default=2_000,
        help="posterior draws for --served-model (default: 2000)",
    )
    parser.add_argument("--json", action="store_true", help="emit one JSON document")
    return parser


def _parse_origin(value: str) -> tuple[str, str, str]:
    parts = tuple(part.strip() for part in value.split(","))
    if len(parts) != 3 or not all(parts):
        raise ValueError("--origin must be CUTOFF,UNTIL,REGIME_START")
    return parts


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.served_model:
        if args.output_dir is None:
            raise SystemExit("--served-model requires --output-dir")
        from legacy_engine.workflows.deck_ranking_evaluation import (
            DECLARED_ORIGINS,
            _markdown_summary,
            run_served_model_evaluation,
        )
        try:
            origins = (
                tuple(_parse_origin(value) for value in args.origin)
                if args.origin else DECLARED_ORIGINS
            )
            scales = tuple(args.prior_scales) if args.prior_scales else (1.0, 0.5, 2.0)
            summary = run_served_model_evaluation(
                args.db, args.output_dir, origins=origins,
                prior_scales=scales, draws=args.draws,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(_markdown_summary(summary))
        return 0
    if args.since is None or args.until is None:
        raise SystemExit("field diagnostics require --since and --until")
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        result = evaluate_chronologically(
            con,
            since=args.since,
            until=args.until,
            provenance=args.provenance,
            include_matchups=not args.no_matchups,
        )
    finally:
        con.close()
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print("chronological deck-ranking evaluation (descriptive; no tuning/deploy gate)")
        print(result.source_selection_note)
        for score in result.field_scores:
            print(
                f"{score.method}: folds={len(score.folds)} scored_decks={score.scored_decks} "
                f"logloss={score.logloss!r} brier={score.brier!r}"
            )
        for score in result.match_scores:
            if score.available:
                print(
                    f"matchups {score.cutoff}→{score.holdout_until}: "
                    f"pairs={score.scored_pairs} matches={score.scored_matches} "
                    f"logloss={score.logloss!r} brier={score.brier!r}"
                )
            else:
                print(f"matchups {score.cutoff}: unavailable ({score.unavailable_reason})")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke tests
    raise SystemExit(main())
