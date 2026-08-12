#!/usr/bin/env python3
"""Refresh every evidence input and write the Best Deck / Best Call ranking last."""

from __future__ import annotations

import argparse
from pathlib import Path

from legacy_engine.config import DUCKDB_PATH, OPS_LOCK_DIR
from legacy_engine.ingestion.card_coverage import card_coverage_audit_lines
from legacy_engine.workflows.decision_refresh import (
    DefaultDecisionRefreshPorts,
    RefreshStepStatus,
    decision_refresh_audit_lines,
    run_decision_refresh,
)
from legacy_engine.ops.scheduled_refresh import (
    LockUnavailable,
    decision_refresh_lock_path,
    exclusive_file_lock,
)


DEFAULT_OUT = Path(__file__).parent.parent / "decks" / "best-deck-best-call-ranking.html"


def run_manual_refresh(*, db_path: Path, out_path: Path, lock_dir: Path, ports):
    """Run the manual adapter under the same artifact lock as scheduled refreshes."""
    lock_path = decision_refresh_lock_path(db_path, out_path, lock_dir=lock_dir)
    with exclusive_file_lock(lock_path):
        return run_decision_refresh(ports, db_path=db_path, out_path=out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DUCKDB_PATH))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    out_path = Path(args.out).resolve()
    try:
        result = run_manual_refresh(
            db_path=db_path,
            out_path=out_path,
            lock_dir=OPS_LOCK_DIR,
            ports=DefaultDecisionRefreshPorts(),
        )
    except LockUnavailable as exc:
        print(f"// ⚠ decision-data refresh skipped: {exc}")
        raise SystemExit(75) from exc
    for line in decision_refresh_audit_lines(result):
        print(line)
    for line in card_coverage_audit_lines(result.card_coverage, verbose=args.verbose):
        print(line)
    if any(step.status is RefreshStepStatus.FAILED for step in result.steps):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
