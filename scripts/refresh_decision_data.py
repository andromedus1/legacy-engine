#!/usr/bin/env python3
"""Refresh every evidence input and write the Best Deck / Best Call ranking last."""

from __future__ import annotations

import argparse
from pathlib import Path

from legacy_engine.config import DUCKDB_PATH
from legacy_engine.ingestion.card_coverage import card_coverage_audit_lines
from legacy_engine.workflows.decision_refresh import (
    DefaultDecisionRefreshPorts,
    RefreshStepStatus,
    decision_refresh_audit_lines,
    run_decision_refresh,
)


DEFAULT_OUT = Path(__file__).parent.parent / "decks" / "best-deck-best-call-ranking.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DUCKDB_PATH))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = run_decision_refresh(
        DefaultDecisionRefreshPorts(), db_path=Path(args.db), out_path=Path(args.out),
    )
    for line in decision_refresh_audit_lines(result):
        print(line)
    for line in card_coverage_audit_lines(result.card_coverage, verbose=args.verbose):
        print(line)
    if any(step.status is RefreshStepStatus.FAILED for step in result.steps):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
