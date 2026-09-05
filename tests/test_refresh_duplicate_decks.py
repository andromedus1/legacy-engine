"""Regression coverage for refreshes that replace a tournament's deck lineup."""

from __future__ import annotations

import pytest

from legacy_engine.archetype.discovered import assign_incremental, save_discovered
from legacy_engine.ingestion import store
from legacy_engine.models.tournament import CardCount, Deck, TournamentResult
from legacy_engine.models.variant import (
    DiscoveredCamp,
    DiscoveredRegistry,
    DiscoveredSplitRecord,
)


def _tournament(date: str, players: tuple[str, ...]) -> TournamentResult:
    return TournamentResult(
        name="Legacy League",
        date=date,
        uri="https://www.mtgo.com/decklist/legacy-league-2026-08-0610831",
        format="Legacy",
        source="MTGO",
        provenance="online",
        decks=[
            Deck(
                Player=player,
                Result="5-0",
                Mainboard=[CardCount(CardName="Flex Card", Count=4)],
            )
            for player in players
        ],
    )


@pytest.fixture
def incremental_registry(tmp_path):
    path = tmp_path / "discovered.json"
    save_discovered(
        DiscoveredRegistry(
            version="1",
            splits=[
                DiscoveredSplitRecord(
                    parent="Current Archetype",
                    generated_from="regression",
                    camps=[
                        DiscoveredCamp(
                            name="Flex Camp",
                            signature_cards=["Flex Card"],
                            n=1,
                            tier="full",
                            member_keys=[],
                            centroid=[1.0],
                        )
                    ],
                    stability=1.0,
                    flex_cards=["Flex Card"],
                )
            ],
        ),
        path,
    )
    return path


def test_reloading_tournament_invalidates_stale_incremental_assignments(incremental_registry):
    """A changed duplicate-URI cache file must not leave assignments keyed to reused deck indexes."""
    con = store.connect(":memory:")
    old = _tournament("2026-07-05", ("old-0", "old-1", "old-2"))
    new = _tournament("2026-08-06", ("new-0", "new-1", "new-2"))
    tid = store.load_tournament(con, old)
    con.execute(
        """CREATE TABLE variant_incremental_assignments (
            tournament_id VARCHAR,
            deck_idx INTEGER,
            parent VARCHAR,
            camp VARCHAR,
            assigned_by VARCHAR,
            similarity DOUBLE,
            generated_from VARCHAR,
            assigned_at VARCHAR,
            PRIMARY KEY (tournament_id, deck_idx)
        )"""
    )
    con.execute(
        "INSERT INTO variant_incremental_assignments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [tid, 1, "Previous Archetype", "Previous Camp", "incremental", 1.0, "old", "2026-07-05"],
    )

    store.load_tournament(con, new)
    con.execute(
        "UPDATE decks SET archetype = 'Current Archetype' WHERE tournament_id = ? AND deck_idx = 1",
        [tid],
    )

    result = assign_incremental(con, "Current Archetype", discovered_path=incremental_registry)

    assert result.n_assigned == 1
    assert con.execute(
        "SELECT tournament_id, deck_idx, parent, camp FROM variant_incremental_assignments"
    ).fetchall() == [(tid, 1, "Current Archetype", "Flex Camp")]
    con.close()


def test_incremental_assignment_repairs_existing_stale_index(incremental_registry):
    """An unchanged-cache refresh must repair a pre-existing cross-parent assignment collision."""
    con = store.connect(":memory:")
    tournament = _tournament("2026-08-06", ("new-0", "new-1", "new-2"))
    tid = store.load_tournament(con, tournament)
    con.execute(
        """CREATE TABLE variant_incremental_assignments (
            tournament_id VARCHAR,
            deck_idx INTEGER,
            parent VARCHAR,
            camp VARCHAR,
            assigned_by VARCHAR,
            similarity DOUBLE,
            generated_from VARCHAR,
            assigned_at VARCHAR,
            PRIMARY KEY (tournament_id, deck_idx)
        )"""
    )
    con.execute(
        "INSERT INTO variant_incremental_assignments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [tid, 1, "Previous Archetype", "Previous Camp", "incremental", 1.0, "old", "2026-07-05"],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Current Archetype' WHERE tournament_id = ? AND deck_idx = 1",
        [tid],
    )

    result = assign_incremental(con, "Current Archetype", discovered_path=incremental_registry)

    assert result.n_assigned == 1
    assert con.execute(
        "SELECT tournament_id, deck_idx, parent, camp FROM variant_incremental_assignments"
    ).fetchall() == [(tid, 1, "Current Archetype", "Flex Camp")]
    con.close()
