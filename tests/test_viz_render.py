"""Integration tests for viz/render.py — structural-validation gate via vl_convert.

These tests exercise the real Vega-Lite compiler through vl_convert, covering all
three render acceptance criteria from the feature spec. ``assert_renders`` (in conftest)
is the shared helper downstream viz features reuse for every builder.
"""

from __future__ import annotations

import pytest

from legacy_engine.viz import render_html_tile, render_png
from tests.conftest import assert_renders


class TestRenderPng:
    def test_returns_png_magic_bytes(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_png(spec)
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG", f"Expected PNG magic, got {result[:4]!r}"

    def test_returns_non_empty_bytes(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_png(spec)
        assert len(result) > 0

    def test_conflicting_config_still_renders(self, make_vl_spec):
        # strip_and_inject removes the conflicting config; render must succeed
        spec = make_vl_spec(config={"background": "white", "invalid_key": True})
        result = render_png(spec)
        assert result[:4] == b"\x89PNG"

    def test_assert_renders_helper(self, make_vl_spec):
        # Verify the shared conftest helper works correctly
        assert_renders(make_vl_spec())

    def test_print_variant_renders(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_png(spec, variant="print")
        assert result[:4] == b"\x89PNG"

    def test_custom_scale_renders(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_png(spec, scale=1.0)
        assert result[:4] == b"\x89PNG"


class TestRenderHtmlTile:
    def test_returns_string(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_html_tile(spec)
        assert isinstance(result, str)

    def test_contains_doctype(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_html_tile(spec)
        assert "<!DOCTYPE html>" in result or "<!doctype html>" in result.lower(), (
            "HTML output must contain a DOCTYPE declaration"
        )

    def test_contains_chart_data(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_html_tile(spec)
        # The data values should appear in the bundled HTML
        assert '"a"' in result or "test bar" in result, (
            "HTML output should contain spec content (data or description)"
        )

    def test_conflicting_config_still_renders(self, make_vl_spec):
        spec = make_vl_spec(config={"background": "white", "invalid_key": True})
        result = render_html_tile(spec)
        assert "<!DOCTYPE html>" in result or "<!doctype html>" in result.lower()

    def test_screen_variant_by_default(self, make_vl_spec):
        # Should not raise; screen is the default
        spec = make_vl_spec()
        result = render_html_tile(spec)
        assert len(result) > 0

    def test_print_variant_renders(self, make_vl_spec):
        spec = make_vl_spec()
        result = render_html_tile(spec, variant="print")
        assert "<!DOCTYPE html>" in result or "<!doctype html>" in result.lower()
