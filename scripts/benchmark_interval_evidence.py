#!/usr/bin/env python3
"""Measure current-corpus parent/camp interval-ledger construction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter_ns, process_time_ns

import duckdb

from legacy_engine.analytics.eras.consume import AnalysisClock
from legacy_engine.analytics.matchup import build_interval_adaptive_matrix
from legacy_engine.archetype.discovered import staged_split_parents
from legacy_engine.ingestion.banlist import BAN_EVENTS
from refresh_best_call_ranking import current_report_target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/legacy.duckdb"))
    parser.add_argument("--mode", choices=("parent", "camp", "both"), default="both")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")

    target = current_report_target(args.db)
    clock = AnalysisClock(
        data_until=target.effective_data_until,
        knowledge_as_of=target.knowledge_as_of,
        knowledge_mode="retrospective-current-model",
    )
    ban_events = tuple(event for event in BAN_EVENTS if event[0] < clock.data_until)
    modes = ("parent", "camp") if args.mode == "both" else (args.mode,)
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        for iteration in range(1, args.repeat + 1):
            for mode in modes:
                wall_start = perf_counter_ns()
                cpu_start = process_time_ns()
                result = build_interval_adaptive_matrix(
                    con,
                    clock=clock,
                    certificate_run_id=target.certificate_run_id,
                    min_row_share=0.001,
                    until=clock.data_until.isoformat(),
                    split_variants=staged_split_parents() if mode == "camp" else None,
                    ban_events=ban_events,
                )
                print(json.dumps({
                    "iteration": iteration,
                    "mode": mode,
                    "wall_seconds": round((perf_counter_ns() - wall_start) / 1e9, 3),
                    "cpu_seconds": round((process_time_ns() - cpu_start) / 1e9, 3),
                    "directed_pairs": len(result.evidence),
                    "selected_rows": len(result.selected_outcomes.rows),
                    "ledger_sha256": result.selected_outcomes.content_sha256,
                }, sort_keys=True))
    finally:
        con.close()


if __name__ == "__main__":
    main()
