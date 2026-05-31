"""DuckDB store — schema, idempotent load, fetch, rebuild. Uses an in-memory DB."""

from __future__ import annotations

import pytest

from legacy_engine.ingestion import store
from legacy_engine.models.card import Card
from legacy_engine.models.tournament import Deck, TournamentResult


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

    def test_power_toughness_round_trip(self):
        """Cards with power/toughness survive a load→fetch round-trip with values intact."""
        con = _con()
        goyf = Card(
            name="Tarmogoyf",
            type_line="Creature — Lhurgoyf",
            cmc=2.0,
            power="*",
            toughness="*+1",
        )
        goblin = Card(
            name="Goblin Guide",
            type_line="Creature — Goblin Scout",
            cmc=1.0,
            power="2",
            toughness="2",
        )
        store.load_cards(con, [goyf, goblin])

        row_goyf = store.fetch_card(con, "Tarmogoyf")
        assert row_goyf["power"] == "*"
        assert row_goyf["toughness"] == "*+1"

        row_goblin = store.fetch_card(con, "Goblin Guide")
        assert row_goblin["power"] == "2"
        assert row_goblin["toughness"] == "2"

        con.close()

    def test_power_toughness_none_stored_as_null(self):
        """Cards without power/toughness store NULL and fetch back as None."""
        con = _con()
        store.load_cards(con, [Card(name="Brainstorm", type_line="Instant", cmc=1.0)])
        row = store.fetch_card(con, "Brainstorm")
        assert row["power"] is None
        assert row["toughness"] is None
        con.close()

    def test_migration_old_9column_schema_gains_power_toughness(self):
        """BLOCKER regression: an EXISTING 9-column cards table (pre-power/toughness) must be
        migrated by init_schema() so load_cards() can store and retrieve power/toughness.

        Simulates the real-DB scenario: table already exists without the new columns, then
        init_schema is called (e.g. on next run) and the insert must succeed.
        """
        import duckdb

        # Build an OLD-style 9-column table without power/toughness.
        con = duckdb.connect(":memory:")
        con.execute(
            """CREATE TABLE cards (
                name VARCHAR PRIMARY KEY,
                mana_cost VARCHAR,
                cmc DOUBLE,
                type_line VARCHAR,
                colors VARCHAR,
                produced_mana VARCHAR,
                oracle_text VARCHAR,
                layout VARCHAR,
                is_land BOOLEAN
            )"""
        )
        # Verify it really only has 9 columns before migration.
        cols_before = [d[0] for d in con.execute("DESCRIBE cards").fetchall()]
        assert "power" not in cols_before, "Pre-condition: old schema should lack 'power'"
        assert "toughness" not in cols_before, "Pre-condition: old schema should lack 'toughness'"

        # Call init_schema — must add power/toughness idempotently.
        store.init_schema(con)

        cols_after = [d[0] for d in con.execute("DESCRIBE cards").fetchall()]
        assert "power" in cols_after, "After migration 'power' column must exist"
        assert "toughness" in cols_after, "After migration 'toughness' column must exist"

        # load_cards must succeed and round-trip power/toughness correctly.
        tarmogoyf = Card(
            name="Tarmogoyf",
            type_line="Creature — Lhurgoyf",
            cmc=2.0,
            power="*",
            toughness="*+1",
        )
        count = store.load_cards(con, [tarmogoyf])
        assert count == 1

        row = store.fetch_card(con, "Tarmogoyf")
        assert row is not None
        assert row["power"] == "*"
        assert row["toughness"] == "*+1"
        con.close()


# ── tournament_id collision tests (finding #9) ─────────────────────────────


@pytest.fixture
def make_tournament():
    """Factory fixture: build a TournamentResult with overridable fields."""

    def _make(
        *,
        name="Eternal Weekend",
        date="2026-05-30",
        source="MTGmelee",
        uri=None,
        players=("alice", "bob"),
    ) -> TournamentResult:
        decks = [Deck(Player=p, Result="") for p in players]
        return TournamentResult(
            Name=name,
            Date=date,
            Uri=uri,
            source=source,
            provenance="paper",
            decks=decks,
        )

    return _make


class TestTournamentId:
    """Finding #9 — fallback tournament_id uses a player-set hash to prevent collision."""

    def test_uri_event_uses_uri(self, make_tournament):
        """URI-bearing events use the URI as the id (unchanged)."""
        tr = make_tournament(uri="https://melee.gg/Tournament/View/42")
        assert store.tournament_id(tr) == "https://melee.gg/Tournament/View/42"

    def test_no_uri_id_is_deterministic(self, make_tournament):
        """The same no-URI event always produces the same id (idempotent refresh)."""
        tr1 = make_tournament(players=("alice", "bob"))
        tr2 = make_tournament(players=("alice", "bob"))
        assert store.tournament_id(tr1) == store.tournament_id(tr2)

    def test_distinct_player_sets_produce_distinct_ids(self, make_tournament):
        """Two no-URI events with the same source/name/date but different players get distinct ids."""
        tr_ab = make_tournament(players=("alice", "bob"))
        tr_cd = make_tournament(players=("carol", "dave"))
        assert store.tournament_id(tr_ab) != store.tournament_id(tr_cd)

    def test_player_order_independent(self, make_tournament):
        """Player ordering does not affect the id (digest sorts the set)."""
        tr1 = make_tournament(players=("alice", "bob", "carol"))
        tr2 = make_tournament(players=("carol", "alice", "bob"))
        assert store.tournament_id(tr1) == store.tournament_id(tr2)

    def test_no_uri_id_includes_source_name_date(self, make_tournament):
        """Fallback id encodes source, name, and date for human readability."""
        tr = make_tournament(source="MTGmelee", name="Eternal Weekend", date="2026-05-30")
        tid = store.tournament_id(tr)
        assert tid.startswith("MTGmelee:Eternal Weekend:2026-05-30:")

    def test_no_uri_digest_is_8_chars(self, make_tournament):
        """The player-set digest appended to the fallback id is exactly 8 hex characters."""
        tr = make_tournament(players=("alice", "bob"))
        tid = store.tournament_id(tr)
        digest = tid.rsplit(":", 1)[-1]
        assert len(digest) == 8
        assert all(c in "0123456789abcdef" for c in digest)

    def test_idempotent_load_with_no_uri(self, make_tournament):
        """load_tournament is idempotent for no-URI events (re-ingest yields one row)."""
        con = store.connect(":memory:")
        tr = make_tournament(players=("alice", "bob"))
        store.load_tournament(con, tr)
        store.load_tournament(con, tr)
        count = con.execute("SELECT count(*) FROM tournaments").fetchone()[0]
        assert count == 1
        con.close()


class TestFaceAliases:
    """Multi-face cards (A // B) resolve by each face name + the combined name, with
    LAYOUT-AWARE per-face attributes (2026-05-31).

    The front face you cast carries its own type/cmc/P-T. Colors: front-cast layouts
    (transform/flip) use the front face's own colors (you only pay the front to cast it,
    the back is reached in play); both-castable layouts (adventure/split/modal_dfc) use
    the union color identity. Modal-DFC with a land face is land-capable under its front name.
    """

    def test_transform_front_face_uses_own_attrs_and_own_colors(self):
        con = _con()
        # Synthetic transform with DIFFERENT face colors to prove front-only (not union) colors.
        store.load_cards(con, [Card(
            name="Front Caster // Back Beast", layout="transform", cmc=1.0, colors=[],
            type_line="Legendary Creature — Frog // Legendary Planeswalker",
            card_faces=[
                {"name": "Front Caster", "colors": ["U"], "type_line": "Legendary Creature — Frog",
                 "mana_cost": "{U}", "cmc": 1.0, "power": "1", "toughness": "1"},
                {"name": "Back Beast", "colors": ["R"], "type_line": "Legendary Planeswalker"},
            ],
        )])
        front = store.fetch_card(con, "Front Caster")
        assert front is not None
        assert front["colors"] == "U"          # front-cast → front face's OWN colors, NOT union "RU"
        assert "Creature" in front["type_line"]
        assert front["power"] == "1"
        assert front["is_land"] is False
        # Combined row carries the UNION color identity (never empty-colored).
        assert sorted(store.fetch_card(con, "Front Caster // Back Beast")["colors"]) == ["R", "U"]

    def test_adventure_uses_union_colors_for_both_faces(self):
        con = _con()
        store.load_cards(con, [Card(
            name="Brazen Borrower // Petty Theft", layout="adventure", cmc=3.0, colors=["U"],
            type_line="Creature — Faerie Rogue // Instant — Adventure",
            card_faces=[
                {"name": "Brazen Borrower", "colors": ["U"], "type_line": "Creature — Faerie Rogue",
                 "mana_cost": "{1}{U}{U}", "power": "3", "toughness": "1"},
                {"name": "Petty Theft", "colors": ["U"], "type_line": "Instant — Adventure", "mana_cost": "{1}{U}"},
            ],
        )])
        assert store.fetch_card(con, "Brazen Borrower")["colors"] == "U"  # union (both castable)
        assert store.fetch_card(con, "Brazen Borrower")["is_land"] is False
        assert store.fetch_card(con, "Petty Theft") is not None

    def test_modal_dfc_with_land_face_is_land_capable_under_front_name(self):
        con = _con()
        # Front = spell (U), back = land that taps U. Modal-DFC → either side castable.
        store.load_cards(con, [Card(
            name="Sea Gate Restoration // Sea Gate, Reborn", layout="modal_dfc", cmc=7.0, colors=["U"],
            type_line="Sorcery // Land",
            card_faces=[
                {"name": "Sea Gate Restoration", "colors": ["U"], "type_line": "Sorcery", "mana_cost": "{5}{U}{U}"},
                {"name": "Sea Gate, Reborn", "colors": [], "type_line": "Land", "produced_mana": ["U"]},
            ],
        )])
        front = store.fetch_card(con, "Sea Gate Restoration")
        assert front["is_land"] is True            # land-capable: a face is a land (modal-DFC flex land)
        assert front["colors"] == "U"              # union identity
        assert "U" in front["produced_mana"]       # the land face's production surfaces under the front name
        assert store.fetch_card(con, "Sea Gate, Reborn")["is_land"] is True

    def test_art_series_face_does_not_shadow_real_front_face(self):
        con = _con()
        # An art card shares the real transform card's face name; it must NOT generate an alias
        # (regression: the Tamiyo art_series card was shadowing the real front face with empty attrs).
        # Art card listed FIRST to prove order-independence of the exclusion.
        store.load_cards(con, [
            Card(name="Tamiyo, Inquisitive Student // Tamiyo, Inquisitive Student", layout="art_series",
                 type_line="Card // Card", colors=[],
                 card_faces=[{"name": "Tamiyo, Inquisitive Student", "colors": [], "type_line": "Card"},
                             {"name": "Tamiyo, Inquisitive Student", "colors": [], "type_line": "Card"}]),
            Card(name="Tamiyo, Inquisitive Student // Tamiyo, Seasoned Scholar", layout="transform", cmc=1.0,
                 colors=[], type_line="Legendary Creature — Moonfolk Wizard // Legendary Planeswalker — Tamiyo",
                 card_faces=[
                     {"name": "Tamiyo, Inquisitive Student", "colors": ["U"],
                      "type_line": "Legendary Creature — Moonfolk Wizard", "mana_cost": "{U}", "power": "0", "toughness": "3"},
                     {"name": "Tamiyo, Seasoned Scholar", "colors": ["G", "U"], "type_line": "Legendary Planeswalker — Tamiyo"},
                 ]),
        ])
        front = store.fetch_card(con, "Tamiyo, Inquisitive Student")
        assert front["colors"] == "U"                       # the REAL transform front face, not the art card's ""
        assert "Creature" in front["type_line"]
        assert front["layout"] == "transform"

    def test_alias_never_clobbers_real_standalone_card(self):
        con = _con()
        # A genuine standalone card whose name collides with a face alias must win.
        store.load_cards(con, [
            Card(name="Fire", type_line="Instant", cmc=1.0, colors=["R"], oracle_text="real Fire"),
            Card(name="Fire // Ice", layout="split", type_line="Instant // Instant", cmc=2.0, colors=["R", "U"],
                 card_faces=[
                     {"name": "Fire", "colors": ["R"], "type_line": "Instant", "mana_cost": "{1}{R}"},
                     {"name": "Ice", "colors": ["U"], "type_line": "Instant", "mana_cost": "{1}{U}"},
                 ]),
        ])
        assert store.fetch_card(con, "Fire")["oracle_text"] == "real Fire"  # standalone not clobbered
        assert store.fetch_card(con, "Ice")["colors"] == "RU"              # split alias → union identity
