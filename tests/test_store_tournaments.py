"""DuckDB tournament tables — load, idempotency, League-decks-only, archetype NULL."""

from __future__ import annotations

from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

CHALLENGE = {
    "Tournament": {"Name": "Legacy Challenge 32", "Date": "2026-05-24",
                   "Uri": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-05-24", "Formats": "Legacy"},
    "Decks": [
        {"Player": "alice", "Result": "1st Place",
         "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}, {"Count": 4, "CardName": "Ponder"}],
         "Sideboard": [{"Count": 2, "CardName": "Surgical Extraction"}]},
        {"Player": "bob", "Result": "2nd Place",
         "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []},
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [{"Rank": 1, "Player": "alice", "Points": 18}, {"Rank": 2, "Player": "bob", "Points": 15}],
}

LEAGUE = {
    "Tournament": {"Name": "Legacy League", "Date": "2026-05-24",
                   "Uri": "https://www.mtgo.com/decklist/legacy-league-2026-05-24", "Formats": "Legacy"},
    "Decks": [{"Player": "carol", "Result": "5-0", "Mainboard": [{"Count": 4, "CardName": "Ponder"}], "Sideboard": []}],
    "Rounds": [],
    "Standings": [],
}


def _con():
    return store.connect(":memory:")


def _count(con, table, tid):
    return con.execute(f"SELECT count(*) FROM {table} WHERE tournament_id = ?", [tid]).fetchone()[0]


class TestLoadTournament:
    def test_loads_all_tables(self):
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(CHALLENGE, "MTGO"))
        assert con.execute("SELECT count(*) FROM tournaments").fetchone()[0] == 1
        assert _count(con, "decks", tid) == 2
        assert _count(con, "deck_cards", tid) == 4  # 2+1 main rows + 1 side row
        assert _count(con, "rounds", tid) == 1
        assert _count(con, "standings", tid) == 2
        con.close()

    def test_idempotent_reload(self):
        con = _con()
        tr = parse_cache_item(CHALLENGE, "MTGO")
        store.load_tournament(con, tr)
        store.load_tournament(con, tr)  # re-ingest
        tid = store.tournament_id(tr)
        assert con.execute("SELECT count(*) FROM tournaments").fetchone()[0] == 1
        assert _count(con, "decks", tid) == 2  # not 4
        assert _count(con, "deck_cards", tid) == 4
        con.close()

    def test_league_loads_decks_only(self):
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(LEAGUE, "MTGO"))
        assert _count(con, "decks", tid) == 1
        assert _count(con, "rounds", tid) == 0
        assert _count(con, "standings", tid) == 0
        con.close()

    def test_archetype_null_until_labeled(self):
        con = _con()
        store.load_tournament(con, parse_cache_item(CHALLENGE, "MTGO"))
        assert con.execute("SELECT archetype FROM decks LIMIT 1").fetchone()[0] is None
        con.close()

    def test_provenance_persisted(self):
        con = _con()
        tid = store.load_tournament(con, parse_cache_item(CHALLENGE, "MTGO"))
        prov = con.execute("SELECT provenance FROM tournaments WHERE id = ?", [tid]).fetchone()[0]
        assert prov == "online"
        con.close()
