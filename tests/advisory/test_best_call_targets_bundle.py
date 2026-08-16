from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from legacy_engine.advisory import best_call_bundle as bundle_module
from legacy_engine.advisory.best_call_bundle import generate_ranking_bundle
from legacy_engine.advisory.best_call_targets import ReportTarget


def _target(
    target_id: str,
    *,
    cutoff: date,
    field_since: date,
    card: str,
    current: bool,
    label: str | None = None,
) -> ReportTarget:
    return ReportTarget(
        target_id=target_id,
        label=label or target_id,
        mode="current" if current else "retrospective-current-model",
        mode_label="Current" if current else "Today's model",
        data_until=None if current else cutoff,
        effective_data_until=cutoff,
        knowledge_as_of=datetime(2026, 8, 16, tzinfo=UTC),
        field_since=field_since,
        regime_card=card,
    )


@pytest.fixture
def report_targets() -> tuple[ReportTarget, ReportTarget]:
    historical = _target(
        "before-candelabra",
        cutoff=date(2026, 6, 29),
        field_since=date(2026, 5, 18),
        card="Undercity Informer",
        current=False,
        label="Before Candelabra </script>",
    )
    current = _target(
        "current",
        cutoff=date(2026, 8, 17),
        field_since=date(2026, 8, 10),
        card="The Fantasticar",
        current=True,
    )
    return historical, current


def _fake_generator(*, out_path: Path, target: ReportTarget, **_kwargs) -> dict:
    out_path.write_text(
        f'<body data-target="{target.target_id}"><script>\nconst D = {{}};</script></body>',
        encoding="utf-8",
    )
    return {}


class TestReportTarget:
    def test_cutoff_day_ban_is_excluded_from_the_retrospective_regime(self):
        target = _target(
            "before-informer",
            cutoff=date(2026, 5, 18),
            field_since=date(2025, 11, 10),
            card="Entomb",
            current=False,
        )
        assert target.field_since == date(2025, 11, 10)
        assert target.regime_card == "Entomb"

    @pytest.mark.parametrize(
        "updates",
        [
            {"mode_label": "Current"},
            {"data_until": None},
            {"field_since": date(2026, 6, 29)},
            {"regime_card": "future-card"},
        ],
    )
    def test_retrospective_invariants_fail_closed(self, updates):
        payload = {
            "target_id": "historical",
            "label": "Historical",
            "mode": "retrospective-current-model",
            "mode_label": "Today's model",
            "data_until": date(2026, 6, 29),
            "effective_data_until": date(2026, 6, 29),
            "knowledge_as_of": datetime(2026, 8, 16, tzinfo=UTC),
            "field_since": date(2026, 5, 18),
            "regime_card": "Undercity Informer",
        }
        payload.update(updates)
        with pytest.raises(ValidationError):
            ReportTarget(**payload)


class TestBundlePublication:
    def test_each_page_gets_selected_manifest_and_hostile_json_is_safe(
        self, tmp_path, monkeypatch, report_targets
    ):
        monkeypatch.setattr(bundle_module, "_generate_ranking", _fake_generator)
        out = tmp_path / "best-call.html"
        manifest = generate_ranking_bundle(
            db_path=tmp_path / "db.duckdb",
            out_path=out,
            targets=report_targets,
            generated_at=datetime(2026, 8, 16, tzinfo=UTC),
        )
        historical = tmp_path / "best-call--before-candelabra.html"
        assert manifest.selected_target_id == "current"
        assert out.exists() and historical.exists()
        assert '"selected_target_id":"current"' in out.read_text()
        text = historical.read_text()
        assert '"selected_target_id":"before-candelabra"' in text
        assert "Before Candelabra </script>" not in text
        assert "Before Candelabra \\u003c/script\\u003e" in text
        first_bytes = {path.name: path.read_bytes() for path in (out, historical)}
        generate_ranking_bundle(
            db_path=tmp_path / "db.duckdb",
            out_path=out,
            targets=report_targets,
            generated_at=datetime(2026, 8, 16, tzinfo=UTC),
        )
        assert {path.name: path.read_bytes() for path in (out, historical)} == first_bytes

    def test_one_replace_failure_restores_every_last_good_artifact(
        self, tmp_path, monkeypatch, report_targets
    ):
        monkeypatch.setattr(bundle_module, "_generate_ranking", _fake_generator)
        out = tmp_path / "best-call.html"
        historical = tmp_path / "best-call--before-candelabra.html"
        out.write_text("old-current")
        historical.write_text("old-historical")
        real_replace = bundle_module._replace_path
        calls = 0

        def fail_once(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                real_replace(source, destination)
                raise OSError("injected replacement failure")
            real_replace(source, destination)

        monkeypatch.setattr(bundle_module, "_replace_path", fail_once)
        with pytest.raises(OSError, match="injected"):
            generate_ranking_bundle(
                db_path=tmp_path / "db.duckdb",
                out_path=out,
                targets=report_targets,
            )
        assert out.read_text() == "old-current"
        assert historical.read_text() == "old-historical"

    def test_unavailable_target_is_disabled_without_href(
        self, tmp_path, monkeypatch, report_targets
    ):
        monkeypatch.setattr(bundle_module, "_generate_ranking", _fake_generator)
        manifest = generate_ranking_bundle(
            db_path=tmp_path / "db.duckdb",
            out_path=tmp_path / "best-call.html",
            targets=report_targets,
            unavailable_reasons={"before-candelabra": ("exact evidence not assessed",)},
        )
        entry = manifest.targets[0]
        assert entry.status == "unavailable"
        assert entry.href is None
        assert entry.reasons == ("exact evidence not assessed",)
