#!/usr/bin/env python3
"""Render the self-contained Doomsday variant field guide from verified research JSON."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = (
    PROJECT_ROOT
    / ".research/analysis/campaigns/doomsday-variant-experiments/report-content.json"
)
DEFAULT_TEMPLATE = PROJECT_ROOT / "scripts/doomsday_variant_report_template.html"
DEFAULT_OUT = PROJECT_ROOT / "decks/doomsday-variant-field-guide.html"
DATA_MARKER = "__DOOMSDAY_REPORT_DATA__"


def _browser_safe_json(payload: dict) -> str:
    """Serialize JSON without allowing data to terminate its script element."""
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        encoded.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_report(*, input_path: Path, template_path: Path, out_path: Path) -> dict:
    payload = json.loads(input_path.read_text())
    required = {
        "title",
        "cutoff",
        "headline",
        "recommendation_cards",
        "comparison_rows",
        "playstyle_rows",
        "break_even_rows",
        "experiments",
        "limitations",
        "next_tests",
        "provenance",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"report content missing required keys: {', '.join(missing)}")

    template = template_path.read_text()
    marker_count = template.count(DATA_MARKER)
    if marker_count != 1:
        raise ValueError(
            f"template must contain {DATA_MARKER!r} exactly once; found {marker_count}"
        )
    rendered = template.replace(DATA_MARKER, _browser_safe_json(payload), 1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=out_path.parent, delete=False
        ) as handle:
            handle.write(rendered)
            temp_path = Path(handle.name)
        os.replace(temp_path, out_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    return {
        "output": str(out_path),
        "bytes": out_path.stat().st_size,
        "candidates": len(payload["comparison_rows"])
        + len(payload.get("secondary_rows", [])),
        "corpus_max": payload["cutoff"]["corpus_max"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    audit = render_report(
        input_path=args.input.resolve(),
        template_path=args.template.resolve(),
        out_path=args.out.resolve(),
    )
    print(
        "wrote {output}: {bytes} bytes, {candidates} candidates, corpus_max={corpus_max}".format(
            **audit
        )
    )


if __name__ == "__main__":
    main()
