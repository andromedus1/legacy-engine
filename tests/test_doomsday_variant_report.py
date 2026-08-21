from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts/render_doomsday_variant_report.py"
)
SPEC = importlib.util.spec_from_file_location(
    "render_doomsday_variant_report", SCRIPT_PATH
)
report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(report)


def test_render_report_emits_complete_self_contained_field_guide(tmp_path):
    out = tmp_path / "guide.html"

    audit = report.render_report(
        input_path=report.DEFAULT_INPUT,
        template_path=report.DEFAULT_TEMPLATE,
        out_path=out,
    )

    rendered = out.read_text()
    assert audit["candidates"] == 14
    assert audit["corpus_max"] == "2026-08-19"
    assert report.DATA_MARKER not in rendered
    assert "Pilot portraits" in rendered
    assert "What this report refuses to claim" in rendered
    assert "@media(max-width:760px)" in rendered
    assert "@media(prefers-reduced-motion:reduce)" in rendered
    assert 'class="skip" href="#main"' in rendered
    assert 'id="report-data" type="application/json"' in rendered


def test_render_report_escapes_script_terminators(tmp_path):
    payload = json.loads(report.DEFAULT_INPUT.read_text())
    payload["title"] = "</script><script>alert(1)</script>"
    input_path = tmp_path / "content.json"
    input_path.write_text(json.dumps(payload))
    out = tmp_path / "guide.html"

    report.render_report(
        input_path=input_path,
        template_path=report.DEFAULT_TEMPLATE,
        out_path=out,
    )

    rendered = out.read_text()
    data_blob = rendered.split('<script id="report-data" type="application/json">', 1)[
        1
    ].split("</script>", 1)[0]
    assert "</script><script>" not in data_blob
    assert json.loads(data_blob)["title"] == "</script><script>alert(1)</script>"


def test_render_report_rejects_incomplete_content(tmp_path):
    input_path = tmp_path / "content.json"
    input_path.write_text(json.dumps({"title": "incomplete"}))

    with pytest.raises(ValueError, match="missing required keys"):
        report.render_report(
            input_path=input_path,
            template_path=report.DEFAULT_TEMPLATE,
            out_path=tmp_path / "guide.html",
        )
