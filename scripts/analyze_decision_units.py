#!/usr/bin/env python3
"""Run the decision-unit diagnostic against an existing report and DB.

The command only opens DuckDB read-only and never refreshes or relabels the
corpus.  By default it prints JSON; ``--format markdown`` is a compact audit
view suitable for attaching to the local feature record.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb

from legacy_engine.advisory.decision_units import analyze_decision_units

# Importing the reader is safe: it parses the embedded JSON and never executes
# the report's JavaScript.
try:
    from scripts.refresh_best_call_ranking import read_published_ranking
except ModuleNotFoundError:  # direct ``python scripts/analyze_decision_units.py``
    from refresh_best_call_ranking import read_published_ranking


def _default_window(blob: dict[str, Any]) -> tuple[str, str]:
    meta = blob.get("meta", {})
    model = meta.get("deck_rankings", {}) if isinstance(meta, dict) else {}
    field = model.get("field", {}) if isinstance(model, dict) else {}
    since = field.get("since") or meta.get("field_since")
    until = field.get("until")
    if not until and meta.get("corpus_max"):
        until = (dt.date.fromisoformat(meta["corpus_max"]) + dt.timedelta(days=1)).isoformat()
    if not since or not until:
        raise ValueError("report does not declare a complete field window; pass --since and --until")
    return str(since)[:10], str(until)[:10]


def _pct(value: Any) -> str:
    try:
        return f"{100 * float(value):.2f}%"
    except (TypeError, ValueError):
        return "—"


def _pp(value: Any) -> str:
    try:
        number = 100 * float(value)
        return f"{number:+.2f}pp"
    except (TypeError, ValueError):
        return "—"


def _md(result: dict[str, Any]) -> str:
    window = result["window"]
    lines = [
        "# Decision-unit diagnostic",
        "",
        f"Window: `{window['since']}` through `{window['until']}` (exclusive)",
        "",
        "Descriptive diagnostic only; taxonomy and ranking authority are unchanged.",
        "",
        "| Parent | Current share | Camps | Opponent coverage | Pooling uplift | Parent − camp floor | Attention |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in result.get("parents", ()):
        floor = item.get("floor_comparison", {})
        parent = str(item.get("parent", "")).replace("|", "\\|")
        lines.append(
            f"| {parent} | {_pct(item.get('current_parent_share'))} "
            f"| {item.get('camp_count', 0)} | {_pct(floor.get('common_opponent_coverage'))} "
            f"| {_pp(floor.get('pooling_uplift'))} "
            f"| {_pp(floor.get('parent_minus_weighted_camp_floor'))} "
            f"| {_pct(item.get('attention'))} |"
        )
    if not result.get("parents"):
        lines.append("| No staged parent has two current camps | — | — | — | — | — | — |")
    lines.extend([
        "",
        f"Parents analyzed: {result['summary']['parents_analyzed']}; "
        f"with common comparison: {result['summary']['parents_with_comparison']}; "
        f"top attention: {result['summary']['top_attention'] or '—'}.",
    ])
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], *, output: Path | None, out_dir: Path | None) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() in {".md", ".markdown"}:
            output.write_text(_md(result), encoding="utf-8")
        else:
            output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "decision-units.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        (out_dir / "decision-units.md").write_text(_md(result), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="DuckDB source (opened read-only)")
    parser.add_argument("--report", type=Path, required=True, help="Published Deck Rankings HTML")
    parser.add_argument("--since", help="Inclusive ISO date; defaults to the report field window")
    parser.add_argument("--until", help="Exclusive ISO date; defaults to the report field window")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Write one JSON or .md audit file")
    parser.add_argument("--out-dir", type=Path, help="Write decision-units.json and decision-units.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    blob = read_published_ranking(args.report)
    if blob is None:
        raise SystemExit(f"report has no published ranking payload: {args.report}")
    default_since, default_until = _default_window(blob)
    since, until = args.since or default_since, args.until or default_until
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        result = analyze_decision_units(con, blob, since=since, until=until)
    finally:
        con.close()
    _write_outputs(result, output=args.output, out_dir=args.out_dir)
    if args.format == "markdown":
        print(_md(result), end="")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
