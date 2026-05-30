"""DuckDB store — schema, idempotent load, fetch, rebuild. Uses an in-memory DB."""

from __future__ import annotations

from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


def _con():
    return store.connect(":memory:")


class TestStore:
    def test_init_schema_idempotent(self):
        con = _con()
        store.init_schema(con)
        store.init_schema(con)  # second call must not raise
        assert con.execute("SELECT count(*) FROM cards").fetchone()[0] == 0
        con.close()

    def test_load_and_fetch(self):
        con = _con()
        n = store.load_cards(
            con, [Card(name="Underground Sea", type_line="Land — Island Swamp", produced_mana=["U", "B"])]
        )
        assert n == 1
        row = store.fetch_card(con, "Underground Sea")
        assert row["produced_mana"] == "UB"
        assert row["is_land"] is True
        con.close()

    def test_load_is_idempotent_on_name(self):
        con = _con()
        store.load_cards(con, [Card(name="Brainstorm", type_line="Instant", cmc=1.0)])
        store.load_cards(con, [Card(name="Brainstorm", type_line="Instant", cmc=1.0, oracle_text="Draw three.")])
        assert con.execute("SELECT count(*) FROM cards").fetchone()[0] == 1  # no dup
        assert store.fetch_card(con, "Brainstorm")["oracle_text"] == "Draw three."  # updated
        con.close()

    def test_fetch_miss_returns_none(self):
        con = _con()
        store.init_schema(con)
        assert store.fetch_card(con, "Nonexistent") is None
        con.close()

    def test_rebuild_empties(self):
        con = _con()
        store.load_cards(con, [Card(name="X", type_line="Instant")])
        store.rebuild(con)
        assert con.execute("SELECT count(*) FROM cards").fetchone()[0] == 0
        con.close()
