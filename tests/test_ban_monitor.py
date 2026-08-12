from __future__ import annotations

from datetime import date

import pytest

from legacy_engine.ingestion.ban_monitor import (
    announcement_candidate_urls,
    parse_wotc_legacy_announcement,
)


def _page(legacy: str, *, next_date: str = "October 12, 2026") -> str:
    return f"""
    <article>
      <p>Changes effective as of August 12, 2026.</p>
      <h2>Modern</h2><p>Other Card is banned.</p>
      <h2>Legacy</h2><p>{legacy}</p>
      <h2>Vintage</h2><p>Nothing relevant.</p>
      <p>Next announcement: {next_date}.</p>
    </article>
    """


class TestWotcAnnouncementParser:
    def test_ignores_nuxt_hydration_copy_of_live_article(self):
        html = """
        <article>
          <p>Changes effective as of August 10, 2026.</p>
          <p><strong>Legacy</strong></p><p>The Fantasticar is banned.</p>
          <nav><a href="#Legacy">Legacy</a></nav>
          <h2>Legacy</h2><p>The Fantasticar is banned.</p>
          <h2>Vintage</h2><p>The Fantasticar is restricted.</p>
        </article>
        <script>
          window.__NUXT__={articleBody:"Changes effective as of August 10, 2026. "
          + "Legacy The Fantasticar is banned. Vintage The Fantasticar is restricted."};
        </script>
        """
        result = parse_wotc_legacy_announcement(
            html,
            source_url=(
                "https://magic.wizards.com/en/news/announcements/"
                "banned-and-restricted-august-10-2026"
            ),
        )
        assert result.effective_date == date(2026, 8, 10)
        assert [(item.card, item.action) for item in result.legacy_actions] == [
            ("The Fantasticar", "banned"),
        ]

    def test_extracts_only_legacy_action_dates_and_source(self):
        result = parse_wotc_legacy_announcement(
            _page("Example Card is banned."), source_url="https://magic.wizards.com/a",
        )
        assert [(item.card, item.action) for item in result.legacy_actions] == [
            ("Example Card", "banned"),
        ]
        assert result.effective_date == date(2026, 8, 12)
        assert result.next_announcement == date(2026, 10, 12)
        assert result.source_url.endswith("/a")

    def test_explicit_no_change_is_distinct_from_parser_failure(self):
        result = parse_wotc_legacy_announcement(
            _page("No changes."), source_url="https://magic.wizards.com/a",
        )
        assert result.legacy_no_changes
        assert result.legacy_actions == ()

    @pytest.mark.parametrize(
        "html",
        [
            "<h2>Legacy</h2><p>Example Card is banned.</p>",
            _page("Commentary without a machine-readable action."),
            _page("No changes. Example Card is banned."),
            _page("Example Card might be banned."),
            _page("Example Card is banned.").replace("<h2>Legacy</h2>", ""),
        ],
    )
    def test_ambiguous_or_drifted_page_fails_loudly(self, html):
        with pytest.raises(ValueError):
            parse_wotc_legacy_announcement(html, source_url="https://magic.wizards.com/a")

    def test_conflicting_visible_effective_dates_still_fail_loudly(self):
        html = _page("No changes.").replace(
            "<h2>Modern</h2>",
            "<p>Changes effective as of August 13, 2026.</p><h2>Modern</h2>",
        )
        with pytest.raises(ValueError, match="effective date, found 2"):
            parse_wotc_legacy_announcement(html, source_url="https://magic.wizards.com/a")

    def test_candidate_urls_are_bounded_and_deterministic(self):
        urls = announcement_candidate_urls(date(2026, 8, 12), radius_days=2)
        assert len(urls) == 5
        assert urls[0].endswith("august-12-2026")
        assert urls[1].endswith("august-11-2026")
        assert urls[2].endswith("august-13-2026")
