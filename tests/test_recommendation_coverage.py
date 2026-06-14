"""Coverage for the two highest-value gaps from fix-recommendation-test-coverage:

1. The overpriced-printing flag FIRING path in the `acquire_plan` orchestrator (the
   $33 Secret-Lair vs $2 NPH Dismember case) — previously only asserted negatively
   in the pure core (`_rank_acquisitions`), never positively through the DB path.
2. Interaction-fact `evidence` CONTENT — that the quoted oracle line matches the
   classified scope (opponent-only vs targeted), not merely that evidence is non-empty.

Remaining gaps (tune collection/strong-player threading, generate-doctor no-archetype
branch, report subgroup/variants CLI smoke) are tracked in idea-recommendation-coverage-rest.
"""

import duckdb

from legacy_engine.advisory.acquire import acquire_plan
from legacy_engine.advisory.collection import CollectionView, OwnedPrinting
from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.ingestion import store
from legacy_engine.interaction_facts import interaction_facts
from legacy_engine.models.card import Card


def _field() -> FieldDistribution:
    return FieldDistribution(
        shares={"Dimir Tempo": 1.0},
        field_source="global",
        counts=None,
        no_data=frozenset(),
        warnings=(),
    )


def _seed_prices(con, rows):
    """rows: list of (scryfall_id, name, set_code, usd, is_paper)."""
    store.init_prices_schema(con)
    for sid, name, setc, usd, paper in rows:
        con.execute(
            "INSERT INTO card_prices (scryfall_id, name, set_code, usd, is_paper) "
            "VALUES (?, ?, ?, ?, ?)",
            [sid, name, setc, usd, paper],
        )


class TestOverpricedPrintingFiringPath:
    """The orchestrator-level per-printing overpriced flag (acquire_plan), positive + inverse."""

    def test_fires_for_owned_expensive_printing(self):
        con = duckdb.connect(":memory:")
        store.init_schema(con)
        _seed_prices(con, [
            ("id-sld", "Dismember", "sld", 33.0, True),   # owned Secret Lair
            ("id-nph", "Dismember", "nph", 2.0, True),    # cheap alternative
        ])
        cv = CollectionView(
            {"Dismember": 1},
            {"Dismember": [OwnedPrinting(set_code="sld", collector_number="1", condition="NM", qty=1)]},
        )
        plan = acquire_plan(
            con, _field(),
            deck={"Dismember": 1},
            collection=cv,
            price_fn=lambda name: 2.0,   # cheapest = $2
            overprice_factor=3.0,
        )
        overpriced = [f for f in plan.flags if f.kind == "overpriced-printing"]
        assert any(f.card == "Dismember" for f in overpriced), (
            "owning the $33 Secret Lair printing while $2 is available should fire "
            "an overpriced-printing flag (33 >= 3.0 x 2 and 2 < 33)"
        )

    def test_not_fired_when_owned_printing_is_fairly_priced(self):
        con = duckdb.connect(":memory:")
        store.init_schema(con)
        _seed_prices(con, [("id-nph", "Dismember", "nph", 2.0, True)])  # own the cheap one
        cv = CollectionView(
            {"Dismember": 1},
            {"Dismember": [OwnedPrinting(set_code="nph", collector_number="1", condition="NM", qty=1)]},
        )
        plan = acquire_plan(
            con, _field(),
            deck={"Dismember": 1},
            collection=cv,
            price_fn=lambda name: 2.0,
            overprice_factor=3.0,
        )
        overpriced = [f for f in plan.flags if f.kind == "overpriced-printing"]
        assert not any(f.card == "Dismember" for f in overpriced), (
            "owning the $2 printing at the cheapest price should NOT fire overpriced"
        )


class TestInteractionEvidenceContent:
    """Evidence must quote the oracle line that carries the classified scope."""

    def test_leyline_evidence_quotes_opponent_scope(self):
        card = Card(
            name="Leyline of the Void",
            type_line="Enchantment",
            oracle_text=(
                "If this card is in your opening hand, you may begin the game with it on the battlefield.\n"
                "If a card would be put into an opponent's graveyard from anywhere, exile it instead."
            ),
        )
        facts = interaction_facts(card)
        assert facts.affects == "opponent-only"
        assert any("opponent's graveyard" in line for line in facts.evidence), (
            "evidence should quote the opponent-scope oracle line, not just be non-empty"
        )

    def test_nihil_evidence_quotes_target_player_scope(self):
        card = Card(
            name="Nihil Spellbomb",
            type_line="Artifact",
            oracle_text=(
                "{T}, Sacrifice this artifact: Exile target player's graveyard.\n"
                "When this artifact is put into a graveyard from the battlefield, you may pay {B}. "
                "If you do, draw a card."
            ),
        )
        facts = interaction_facts(card)
        assert facts.affects == "targeted"
        assert any("target player's graveyard" in line for line in facts.evidence)
