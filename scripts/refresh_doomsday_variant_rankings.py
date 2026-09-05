#!/usr/bin/env python3
"""Publish the read-only Doomsday variant comparison report.

The global Deck Rankings HTML is an input artifact.  It is parsed before the
DuckDB read begins and is never overwritten; the variant page is replaced only
after the complete payload and template have been validated.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

import duckdb

from legacy_engine.advisory.doomsday_variants import build_variant_report
from legacy_engine.config import DUCKDB_PATH

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = Path(__file__).with_name("doomsday_variant_rankings_template.html")
DEFAULT_FIELD_REPORT = ROOT / "decks" / "deck-rankings.html"
DEFAULT_OUT = ROOT / "decks" / "doomsday-variant-rankings.html"
DATA_MARKER = "__DOOMSDAY_VARIANT_DATA__"


def _json_for_script(value: object) -> str:
    """Serialize JSON so text cannot terminate the script element."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _load_global_payload(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        raise ValueError(f"field report does not exist: {path}")
    raw = path.read_bytes()
    marker = b"const D ="
    position = raw.find(marker)
    if position < 0:
        raise ValueError(f"field report has no embedded const D payload: {path}")
    encoded = raw[position + len(marker):].lstrip()
    try:
        payload, _end = json.JSONDecoder().raw_decode(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"field report payload is malformed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("field report payload must be an object")
    return payload, sha256(raw).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def render_report(payload: dict, *, template: str | None = None) -> str:
    """Inject a validated report object into the standalone template."""
    source = TEMPLATE_PATH.read_text(encoding="utf-8") if template is None else template
    if source.count(DATA_MARKER) != 1:
        raise ValueError("variant template must contain exactly one data marker")
    return source.replace(DATA_MARKER, _json_for_script(payload), 1)


def build_published_payload(
    db_path: Path,
    field_report: Path,
    *,
    since: str,
    draws: int = 10_000,
) -> dict:
    global_payload, field_sha = _load_global_payload(field_report)
    with duckdb.connect(str(db_path), read_only=True) as con:
        payload = build_variant_report(con, global_payload, since=since, draws=draws)
    payload["meta"]["field_report_path"] = str(field_report)
    payload["meta"]["field_report_sha256"] = field_sha
    payload["meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DUCKDB_PATH)
    parser.add_argument("--field-report", type=Path, default=DEFAULT_FIELD_REPORT)
    parser.add_argument("--since", default="2026-01-01")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--draws", type=int, default=10_000, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        db_path = args.db.resolve()
        field_path = args.field_report.resolve()
        out_path = args.out.resolve()
        if out_path == field_path:
            raise ValueError("--out must not overwrite --field-report")
        if out_path == db_path:
            raise ValueError("--out must not overwrite the read-only DuckDB input")
        # The canonical global report is protected even when a caller passes a
        # different path spelling or a custom output under decks/.
        if out_path == DEFAULT_FIELD_REPORT.resolve():
            raise ValueError("--out must not overwrite the canonical global field report")
        if out_path == TEMPLATE_PATH.resolve():
            raise ValueError("--out must not overwrite the report template")
        payload = build_published_payload(db_path, field_path, since=args.since, draws=args.draws)
        rendered = render_report(payload)
        if DATA_MARKER in rendered or "const D =" not in rendered:
            raise ValueError("rendered variant report failed payload validation")
        _atomic_write_text(out_path, rendered)
    except (OSError, ValueError, duckdb.Error) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
