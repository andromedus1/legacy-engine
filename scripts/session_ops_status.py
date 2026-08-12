#!/usr/bin/env python3
"""Print the no-network scheduled-refresh health line for session orientation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from legacy_engine.config import OPS_STATUS_DIR
from legacy_engine.ops.scheduled_refresh import JOB_NAME
from legacy_engine.ops.status import job_status_audit_lines, read_job_status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-dir", default=str(OPS_STATUS_DIR))
    args = parser.parse_args()
    path = Path(args.status_dir).resolve() / f"{JOB_NAME}.json"
    view = read_job_status(path, now=datetime.now(timezone.utc))
    for line in job_status_audit_lines(view, brief=True):
        print(line)


if __name__ == "__main__":
    main()
