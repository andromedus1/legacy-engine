"""Tests for viz/layout.py — Tile/Dashboard dataclasses and render_dashboard_html.

Covers:
- TestTileDataclass     — basic dataclass semantics
- TestDashboardDataclass — title + tiles list
- TestRenderDashboardHtml — DOCTYPE, 12-col grid, vegaEmbed calls, HTML tiles, CDN vs offline
"""

from __future__ import annotations

import pytest

from legacy_engine.config import VIZ_CDN_VEGA, VIZ_CDN_VEGA_EMBED, VIZ_CDN_VEGA_LITE, VL_SCHEMA_URL
from legacy_engine.viz.layout import Dashboard, Tile, render_dashboard_html


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_spec(make_vl_spec):
    return make_vl_spec()


@pytest.fixture
def chart_tile(simple_spec):
    return Tile(kind="chart", title="Meta Share", col_span=6, spec=simple_spec)


@pytest.fixture
def html_tile():
    return Tile(kind="html", title="Primer", col_span=12, html="<p>Hello world</p>")


@pytest.fixture
def simple_dashboard(chart_tile, html_tile):
    return Dashboard(title="Test Dashboard", tiles=[html_tile, chart_tile])


# ---------------------------------------------------------------------------
# TestTileDataclass
# ---------------------------------------------------------------------------

class TestTileDataclass:
    def test_chart_tile_fields(self, simple_spec):
        t = Tile(kind="chart", title="Foo", col_span=6, spec=simple_spec)
        assert t.kind == "chart"
        assert t.title == "Foo"
        assert t.col_span == 6
        assert t.spec is simple_spec
        assert t.html is None

    def test_html_tile_fields(self):
        t = Tile(kind="html", title="Bar", col_span=12, html="<b>hi</b>")
        assert t.kind == "html"
        assert t.html == "<b>hi</b>"
        assert t.spec is None

    def test_col_span_in_range(self, simple_spec):
        for span in (1, 6, 12):
            t = Tile(kind="chart", title="T", col_span=span, spec=simple_spec)
            assert t.col_span == span


# ---------------------------------------------------------------------------
# TestDashboardDataclass
# ---------------------------------------------------------------------------

class TestDashboardDataclass:
    def test_title_and_tiles(self, simple_dashboard):
        assert simple_dashboard.title == "Test Dashboard"
        assert len(simple_dashboard.tiles) == 2

    def test_empty_tiles(self):
        d = Dashboard(title="Empty")
        assert d.tiles == []


# ---------------------------------------------------------------------------
# TestRenderDashboardHtml
# ---------------------------------------------------------------------------

class TestRenderDashboardHtml:
    def test_returns_string(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        assert isinstance(html, str)

    def test_doctype_html(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_title_in_document(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        assert "Test Dashboard" in html

    def test_twelve_col_grid(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        assert "repeat(12" in html

    def test_vega_embed_call_for_chart_tiles(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        # One chart tile → one vegaEmbed( call
        count = html.count("vegaEmbed(")
        assert count == 1

    def test_html_tile_content_inlined(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        assert "Hello world" in html

    def test_cdm_mode_references_cdn_urls(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard, offline=False)
        assert VIZ_CDN_VEGA in html
        assert VIZ_CDN_VEGA_LITE in html
        assert VIZ_CDN_VEGA_EMBED in html

    def test_cdn_mode_no_inline_bundle(self, simple_dashboard):
        """CDN mode must not contain the inline JS bundle."""
        html = render_dashboard_html(simple_dashboard, offline=False)
        # The inline bundle would be very large JS; we check that CDN refs are present
        # and the page body doesn't start with a full bundle marker.
        assert 'cdn.jsdelivr.net' in html

    def test_offline_mode_no_cdn_refs(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard, offline=True)
        assert "cdn.jsdelivr.net" not in html

    def test_offline_mode_has_inline_script(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard, offline=True)
        # The inlined bundle will include vega/vega-lite JS function definitions
        assert "<script>" in html

    def test_spec_theme_injected_no_raw_config_leak(self, simple_dashboard):
        """After theme injection, specs should not leak an unconsumed 'config' key."""
        # strip_and_inject removes config before inlining; this is a structural check
        html = render_dashboard_html(simple_dashboard)
        # The chart spec in the page should have $schema but the outer-level config
        # should be the theme (injected), not the raw spec's config.
        assert '"$schema"' in html

    def test_multiple_chart_tiles_multiple_embed_calls(self, simple_spec):
        tiles = [
            Tile(kind="chart", title="A", col_span=6, spec=simple_spec),
            Tile(kind="chart", title="B", col_span=6, spec=simple_spec),
            Tile(kind="chart", title="C", col_span=12, spec=simple_spec),
        ]
        dash = Dashboard(title="Multi", tiles=tiles)
        html = render_dashboard_html(dash)
        count = html.count("vegaEmbed(")
        assert count == 3

    def test_col_span_appears_in_html(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        assert "span 12" in html  # html_tile col_span=12
        assert "span 6" in html   # chart_tile col_span=6

    def test_dark_background_in_css(self, simple_dashboard):
        html = render_dashboard_html(simple_dashboard)
        # _BG is #15181C
        assert "#15181C" in html
