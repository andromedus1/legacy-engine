"""Tests for analytics.eras.store — the entity_eras persisted ledger (Unit B).

House style: hermetic in-memory DuckDB (`:memory:`), hand-built EntityEras/EraBoundary fixtures
(no need for the real detectors/DB corpus — this module is a pure persistence layer). Attribution
and AlarmFlag don't exist yet at this story's layer (`-run` builds them next), so tests use local
duck-typed doubles carrying the same `kind`/`card`/`detail` and `p_change`/`note` shape the real
`analytics.eras.attribution.Attribution` / `analytics.eras.run.AlarmFlag` dataclasses will have.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pytest

from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary
from legacy_engine.analytics.eras.store import (
    init_eras_schema,
    read_entity_eras,
    stable_since_map,
    write_entity_eras,
)


@dataclass(frozen=True)
class _FakeAttribution:
    kind: str
    card: str | None
    detail: str


@dataclass(frozen=True)
class _FakeAlarm:
    p_change: float
    note: str


def _con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


@pytest.fixture
def make_boundary():
    def _make(**kwargs):
        defaults = dict(date="2026-05-18", signals=(), pvalue=0.01, bh_accepted=True, floor_rejected=False)
        defaults.update(kwargs)
        return EraBoundary(**defaults)
    return _make


@pytest.fixture
def make_eras():
    def _make(**kwargs):
        defaults = dict(entity="Tron", stable_since="2026-05-18", boundaries=(), inherited_from_parent=False)
        defaults.update(kwargs)
        return EntityEras(**defaults)
    return _make


class TestInitSchema:
    def test_idempotent(self):
        con = _con()
        init_eras_schema(con)
        init_eras_schema(con)  # second call must not raise
        assert con.execute("SELECT count(*) FROM entity_eras").fetchone()[0] == 0
        con.close()


class TestWriteReadRoundTrip:
    def test_round_trips_every_field(self, make_boundary, make_eras):
        con = _con()
        boundary = make_boundary(date="2026-05-18", pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {"Tron": make_eras(boundaries=(boundary,))}
        attributions = {
            ("Tron", "2026-05-18"): _FakeAttribution(
                kind="ban", card="Undercity Informer", detail="ban: Undercity Informer (2026-05-18)",
            )
        }
        alarms = {}
        write_entity_eras(
            con, eras, attributions, alarms,
            run_meta={
                "provenance": "paper", "alpha": 0.05, "run_at": "2026-07-11T00:00:00+00:00",
                "post_boundary_decks": {"Tron": 42}, "parent": {"Tron": "Tron"},
            },
        )

        rows = read_entity_eras(con)
        assert set(rows) == {"Tron"}
        row = rows["Tron"]
        assert row.entity == "Tron"
        assert row.parent == "Tron"
        assert row.stable_since == "2026-05-18"
        assert row.inherited_from_parent is False
        assert row.post_boundary_decks == 42
        assert row.alarm_fired is False
        assert row.alarm_p_change is None
        assert row.alarm_note is None
        assert row.run_provenance == "paper"
        assert row.run_alpha == 0.05
        assert row.run_at == "2026-07-11T00:00:00+00:00"

        assert len(row.boundaries) == 1
        b = row.boundaries[0]
        assert b.date == "2026-05-18"
        assert b.pvalue == 0.001
        assert b.bh_accepted is True
        assert b.floor_rejected is False
        assert b.attribution is not None
        assert b.attribution.kind == "ban"
        assert b.attribution.card == "Undercity Informer"
        con.close()

    def test_round_trips_signals_within_a_boundary(self, make_boundary, make_eras):
        from legacy_engine.analytics.eras.detect import CandidateBoundary

        con = _con()
        sig = CandidateBoundary(
            entity="Tron", date="2026-05-18", signal="share", magnitude=0.66,
            pvalue=0.02, evidence="share 14%->5%", trigger_card=None,
        )
        boundary = make_boundary(signals=(sig,))
        eras = {"Tron": make_eras(boundaries=(boundary,))}
        write_entity_eras(
            con, eras, {}, {},
            run_meta={"provenance": None, "alpha": 0.05, "run_at": "t", "post_boundary_decks": {}, "parent": {}},
        )
        row = read_entity_eras(con)["Tron"]
        assert len(row.boundaries[0].signals) == 1
        s = row.boundaries[0].signals[0]
        assert s.signal == "share"
        assert s.magnitude == 0.66
        assert s.evidence == "share 14%->5%"
        assert s.trigger_card is None
        con.close()

    def test_round_trips_alarm_fields(self, make_eras):
        con = _con()
        eras = {"Tron": make_eras(boundaries=())}
        alarms = {"Tron": _FakeAlarm(p_change=0.87, note="unattributed disturbance")}
        write_entity_eras(
            con, eras, {}, alarms,
            run_meta={"provenance": None, "alpha": 0.05, "run_at": "t", "post_boundary_decks": {}, "parent": {}},
        )
        row = read_entity_eras(con)["Tron"]
        assert row.alarm_fired is True
        assert row.alarm_p_change == 0.87
        assert row.alarm_note == "unattributed disturbance"
        con.close()

    def test_boundary_without_attribution_round_trips_as_none(self, make_boundary, make_eras):
        con = _con()
        eras = {"Tron": make_eras(boundaries=(make_boundary(),))}
        write_entity_eras(
            con, eras, {}, {},
            run_meta={"provenance": None, "alpha": 0.05, "run_at": "t", "post_boundary_decks": {}, "parent": {}},
        )
        row = read_entity_eras(con)["Tron"]
        assert row.boundaries[0].attribution is None
        con.close()

    def test_camp_inherits_parent_field(self, make_eras):
        con = _con()
        eras = {
            "Tron": make_eras(entity="Tron", boundaries=()),
            "Tron [Karn]": make_eras(entity="Tron [Karn]", stable_since=None, inherited_from_parent=True, boundaries=()),
        }
        write_entity_eras(
            con, eras, {}, {},
            run_meta={
                "provenance": None, "alpha": 0.05, "run_at": "t", "post_boundary_decks": {},
                "parent": {"Tron": "Tron", "Tron [Karn]": "Tron"},
            },
        )
        rows = read_entity_eras(con)
        assert rows["Tron [Karn]"].parent == "Tron"
        assert rows["Tron [Karn]"].inherited_from_parent is True
        con.close()


class TestRebuildIdempotence:
    def test_second_write_fully_replaces_the_first(self, make_eras):
        con = _con()
        write_entity_eras(
            con, {"Old": make_eras(entity="Old")}, {}, {},
            run_meta={"provenance": None, "alpha": 0.05, "run_at": "t1", "post_boundary_decks": {}, "parent": {}},
        )
        assert set(read_entity_eras(con)) == {"Old"}

        write_entity_eras(
            con, {"New": make_eras(entity="New")}, {}, {},
            run_meta={"provenance": None, "alpha": 0.05, "run_at": "t2", "post_boundary_decks": {}, "parent": {}},
        )
        rows = read_entity_eras(con)
        assert set(rows) == {"New"}, "a stale entity from the prior run must not survive a rebuild"
        con.close()

    def test_write_with_no_entities_leaves_table_empty(self):
        con = _con()
        write_entity_eras(
            con, {}, {}, {},
            run_meta={"provenance": None, "alpha": 0.05, "run_at": "t", "post_boundary_decks": {}, "parent": {}},
        )
        assert read_entity_eras(con) == {}
        con.close()


class TestStableSinceMap:
    def test_matches_ensemble_output(self, make_eras):
        con = _con()
        eras = {
            "Tron": make_eras(entity="Tron", stable_since="2026-05-18"),
            "Doomsday": make_eras(entity="Doomsday", stable_since=None),
        }
        write_entity_eras(
            con, eras, {}, {},
            run_meta={
                "provenance": None, "alpha": 0.05, "run_at": "t", "post_boundary_decks": {},
                "parent": {"Tron": "Tron", "Doomsday": "Doomsday"},
            },
        )
        mapping = stable_since_map(con)
        assert mapping == {"Tron": "2026-05-18", "Doomsday": None}
        con.close()

    def test_empty_before_any_run(self):
        con = _con()
        assert stable_since_map(con) == {}
        con.close()

    def test_empty_on_a_table_that_was_never_created(self):
        # No init_eras_schema call at all — must degrade honestly, not raise.
        con = _con()
        assert stable_since_map(con) == {}
        assert read_entity_eras(con) == {}
        con.close()
