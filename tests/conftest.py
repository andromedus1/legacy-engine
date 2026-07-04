"""Shared test fixtures and factory helpers.

Establishes the project test idiom: factory fixtures returning `_make_X(**kwargs)`
builders with sensible defaults, overridable per test (per
.claude/rules/patterns.md test-factory-patterns).
"""

from __future__ import annotations

import pytest

from legacy_engine.advisory.field import FieldDistribution, build_custom_field
from legacy_engine.advisory.linchpins import Linchpin
from legacy_engine.advisory.sideboard import HoserCard
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.config import VL_SCHEMA_URL
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Plain (non-fixture) shared helpers — gate-cruft-test-helper-duplication.
#
# `_con`, `_make_field`, and `_make_card` were byte-identical, independently
# maintained copies in tests/test_sideboard.py, tests/test_whattoplay.py, and
# tests/test_linchpins.py. Unlike the `make_X(**kwargs)` factory FIXTURES below
# (which model discrete test DATA objects meant for per-test override via pytest's
# DI), these three are plain zero/one-arg infra helpers also called from inside
# non-test `@staticmethod` corpus builders (e.g. `TestRedundancyDecay._gy_field_corpus`)
# that pytest never collects and so cannot receive injected fixtures. Converting them
# to `@pytest.fixture`s would force rewriting every one of their 100+ call sites (and
# restructuring those static builders) for no behavior change — out of scope for a
# structural dedup. Kept as plain functions and imported via `from tests.conftest import
# ...` (precedent: `assert_renders` below, already imported this way from
# test_viz_render.py) — call-site signatures are untouched.
# ---------------------------------------------------------------------------

def _con():
    """In-memory DuckDB connection with schema initialized."""
    from legacy_engine.ingestion import store

    con = store.connect(":memory:")
    store.init_schema(con)
    return con


def _make_field(shares: dict[str, float]) -> FieldDistribution:
    """Build a FieldDistribution from raw shares (normalizes automatically)."""
    return build_custom_field(shares)


def _make_card(**kwargs) -> Card:
    """Construct a Card with defaults for unspecified fields."""
    defaults = dict(name="Test Card", type_line="Instant", oracle_text="", cmc=1.0)
    defaults.update(kwargs)
    return Card(**defaults)


@pytest.fixture
def make_confidence():
    """Return a builder for ConfidenceMetadata with overridable defaults."""

    def _make(**kwargs) -> ConfidenceMetadata:
        defaults: dict = {
            "level": "established",
            "production": "hand-written",
            "source": "user",
        }
        defaults.update(kwargs)
        return ConfidenceMetadata(**defaults)

    return _make


@pytest.fixture
def make_hoser():
    """Return a builder for HoserCard with overridable defaults (feature-sb-field-weighted-scorer)."""

    def _make(**kwargs) -> HoserCard:
        defaults: dict = {
            "name": "Test Hoser",
            "attacks": frozenset({"graveyard-recursion"}),
            "colors": frozenset({"B"}),
            "max_copies": 4,
            "swing": 0.20,
        }
        defaults.update(kwargs)
        return HoserCard(**defaults)

    return _make


@pytest.fixture
def make_linchpin():
    """Return a builder for Linchpin with overridable defaults (feature-sb-field-weighted-scorer)."""

    def _make(**kwargs) -> Linchpin:
        defaults: dict = {
            "archetype": "Test Archetype",
            "name": "Test Linchpin",
            "role": "combo-engine",
            "centrality": 1.0,
            "neutralized_by": frozenset({"artifact-removal"}),
        }
        defaults.update(kwargs)
        return Linchpin(**defaults)

    return _make


@pytest.fixture
def make_rounds_corpus():
    """Factory: build an in-memory DuckDB connection with a deterministic rounds+deck_cards corpus.

    Returns a builder ``_make(n_repeats=1)`` that yields ``(con, facts)`` where
    ``facts`` pins the expected wins/n for the seeded signal cells so tests can
    assert exact values rather than approximate shapes.

    **Corpus design (deterministic)**::

        Archetypes: "Control" (alice + alice2) vs "Combo" (bob + bob2)
        Tech card:  "Surgical Extraction" in Control's sideboard
        Non-tech:   "Brainstorm" in Control's mainboard
        Combo cards: "Dark Ritual" (main), "Demonic Tutor" (side)

        Each repeat adds ONE tournament with:
          - alice beats bob   2-1   → Control win vs Combo  (1 decisive)
          - alice2 beats bob2 2-1   → Control win vs Combo  (1 decisive)
          - alice vs alice2   2-1   → mirror (excluded)
          - alice vs bob draw 1-1   → dropped

        Per repeat, seeded (Surgical Extraction, side, Combo) cell:
            wins += 2  (alice and alice2 each carry Surgical AND win vs Combo)
            losses += 0

        n_repeats moves the seeded cell across speculative→evolving→established:
            n_repeats=1  → n=2   (speculative, <30)
            n_repeats=15 → n=30  (evolving, ≥30)
            n_repeats=50 → n=100 (established, ≥100)

    The fixture is also used by the tuning rework to exercise its greedy path
    (unblocks epic-deck-generation-tuning bug #2).
    """
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.cache import parse_cache_item

    def _make(n_repeats: int = 1):
        con = store.connect(":memory:")

        for repeat in range(n_repeats):
            date = f"2026-01-{repeat + 1:02d}"
            uri = f"https://www.mtgo.com/decklist/rounds-corpus-{repeat + 1:03d}"

            raw = {
                "Tournament": {
                    "Name": f"Rounds Corpus {repeat + 1}",
                    "Date": date,
                    "Uri": uri,
                    "Formats": "Legacy",
                },
                "Decks": [
                    {
                        "Player": "alice",
                        "Result": "1st",
                        "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                        "Sideboard": [{"Count": 2, "CardName": "Surgical Extraction"}],
                    },
                    {
                        "Player": "alice2",
                        "Result": "2nd",
                        "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
                        "Sideboard": [{"Count": 2, "CardName": "Surgical Extraction"}],
                    },
                    {
                        "Player": "bob",
                        "Result": "3rd",
                        "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                        "Sideboard": [{"Count": 2, "CardName": "Demonic Tutor"}],
                    },
                    {
                        "Player": "bob2",
                        "Result": "4th",
                        "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
                        "Sideboard": [{"Count": 2, "CardName": "Demonic Tutor"}],
                    },
                ],
                "Rounds": [
                    # decisive: Control (alice) beats Combo (bob)
                    {"Player1": "alice", "Player2": "bob", "Result": "2-1"},
                    # decisive: Control (alice2) beats Combo (bob2)
                    {"Player1": "alice2", "Player2": "bob2", "Result": "2-1"},
                    # mirror: Control vs Control (excluded from card win-rate)
                    {"Player1": "alice", "Player2": "alice2", "Result": "2-1"},
                    # draw: dropped
                    {"Player1": "alice", "Player2": "bob", "Result": "1-1"},
                ],
                "Standings": [],
            }

            tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
            con.execute(
                "UPDATE decks SET archetype = 'Control' "
                "WHERE tournament_id = ? AND player IN ('alice', 'alice2')",
                [tid],
            )
            con.execute(
                "UPDATE decks SET archetype = 'Combo' "
                "WHERE tournament_id = ? AND player IN ('bob', 'bob2')",
                [tid],
            )

        # facts: pinned expected values for the seeded signal
        # Per repeat: alice carries Surgical in side AND wins vs Combo → +1 win
        #             alice2 also carries Surgical in side AND wins vs Combo → +1 win
        # Total per repeat: wins=2, losses=0 for (Surgical Extraction, side, Combo)
        # Brainstorm (main) vs Combo: same pattern — wins=2*n_repeats, losses=0
        # Combo's Dark Ritual (main) vs Control: losses=2*n_repeats, wins=0
        facts = {
            "surgical_vs_combo": {
                "card": "Surgical Extraction",
                "board": "side",
                "opponent": "Combo",
                "wins": 2 * n_repeats,
                "losses": 0,
                "n": 2 * n_repeats,
            },
            "brainstorm_vs_combo": {
                "card": "Brainstorm",
                "board": "main",
                "opponent": "Combo",
                "wins": 2 * n_repeats,
                "losses": 0,
                "n": 2 * n_repeats,
            },
            "dark_ritual_vs_control": {
                "card": "Dark Ritual",
                "board": "main",
                "opponent": "Control",
                "wins": 0,
                "losses": 2 * n_repeats,
                "n": 2 * n_repeats,
            },
            # resolved decisive matches per repeat: 2 (alice-bob, alice2-bob2)
            "decisive_per_repeat": 2,
            "total_decisive": 2 * n_repeats,
        }

        return con, facts

    return _make


@pytest.fixture
def make_vl_spec():
    """Return a builder for a minimal valid Vega-Lite v6 bar spec with overridable fields."""

    def _make(**kwargs) -> dict:
        spec = {
            "$schema": VL_SCHEMA_URL,
            "description": "test bar",
            "data": {"values": [{"a": "x", "b": 3}, {"a": "y", "b": 5}]},
            "mark": "bar",
            "encoding": {
                "x": {"field": "a", "type": "nominal"},
                "y": {"field": "b", "type": "quantitative"},
            },
        }
        spec.update(kwargs)
        return spec

    return _make


def assert_renders(spec: dict) -> None:
    """Structural-validation gate: render spec via vl_convert and assert non-empty PNG bytes.

    Shared helper for render tests across all viz features (foundation + charts-migration +
    dashboard). Uses the real Vega-Lite compiler via vl_convert — strictly stronger than
    schema-only validation.
    """
    from legacy_engine.viz import render_png

    result = render_png(spec)
    assert isinstance(result, bytes), "render_png must return bytes"
    assert result[:4] == b"\x89PNG", "render_png output must start with PNG magic bytes"
    assert len(result) > 0, "render_png must return non-empty bytes"
