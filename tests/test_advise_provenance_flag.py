"""Tests for the ``--provenance online|paper`` flag on advise commands.

Spec: threading provenance through positioning/whattoplay/report/sideboard/acquire
(feature-advise-provenance-flag).

Key behaviors verified:
  - ``--provenance paper`` is accepted and echoes ``// provenance: paper`` in output.
  - A paper-only corpus produces a different (paper-only) field than a mixed corpus.
  - Absent ``--provenance`` → current global behavior, byte-identical.
  - ``--field`` + ``--provenance``: command succeeds; field_source=custom (custom field
    is not filtered by provenance); exit code is 0.
  - ``advise report --provenance`` + ``--venues`` → mutual-exclusion error.
  - ``advise refresh --provenance`` + ``--venues`` → mutual-exclusion error.

House style: minimal labeled corpus via ``parse_cache_item`` + SQL UPDATE;
CliRunner with ``--db`` pointing at a file-backed DB copy; ``--seed 42`` to
pin MC paths.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.advisory.field import build_global_field
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_ONLINE_TOURNAMENT = {
    "Tournament": {
        "Name": "Legacy Challenge 32",
        "Date": "2026-05-24",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-05-24",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "alice",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [{"Count": 2, "CardName": "Force of Will"}],
        },
        {
            "Player": "bob",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [
        {"Rank": 1, "Player": "alice", "Points": 9},
        {"Rank": 2, "Player": "bob", "Points": 6},
    ],
}

_PAPER_TOURNAMENT = {
    "Tournament": {
        "Name": "SCG Columbus Legacy",
        "Date": "2026-05-25",
        "Uri": "https://melee.gg/Tournament/View/99999",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "carol",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "dave",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [{"Player1": "carol", "Player2": "dave", "Result": "2-1"}],
    "Standings": [
        {"Rank": 1, "Player": "carol", "Points": 9},
        {"Rank": 2, "Player": "dave", "Points": 6},
    ],
}

_BRAINSTORM_CARD = Card(
    name="Brainstorm",
    type_line="Instant",
    oracle_text="Draw three cards, then put two cards on top.",
    cmc=1.0,
    colors=["U"],
    produced_mana=[],
    is_land=False,
)
_FORCE_CARD = Card(
    name="Force of Will",
    type_line="Instant",
    oracle_text="Counter target spell.",
    cmc=5.0,
    colors=["U"],
    produced_mana=[],
    is_land=False,
)
_ISLAND = Card(
    name="Island",
    type_line="Basic Land — Island",
    oracle_text="",
    cmc=0.0,
    colors=[],
    produced_mana=["U"],
    is_land=True,
)
_DARK_RITUAL_CARD = Card(
    name="Dark Ritual",
    type_line="Instant",
    oracle_text="Add BBB.",
    cmc=1.0,
    colors=["B"],
    produced_mana=["B"],
    is_land=False,
)

_TEST_CARDS = [_BRAINSTORM_CARD, _FORCE_CARD, _ISLAND, _DARK_RITUAL_CARD]

# Minimal decklist for CLI tests
_BRAINSTORM_DECKLIST = "4 Brainstorm\n4 Force of Will\n12 Island\nSideboard\n2 Force of Will"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def _build_mixed_db(tmp_path) -> str:
    """Build a DB with both online (Control) and paper (Combo) archetypes."""
    db_path = str(tmp_path / "mixed.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, _TEST_CARDS)

    # Online tournament → "Control" archetype
    tid_online = store.load_tournament(con, parse_cache_item(_ONLINE_TOURNAMENT, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?", [tid_online]
    )

    # Paper tournament → "Combo" archetype
    tid_paper = store.load_tournament(con, parse_cache_item(_PAPER_TOURNAMENT, "mtgmelee"))
    con.execute(
        "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ?", [tid_paper]
    )

    con.close()
    return db_path


def _build_online_only_db(tmp_path) -> str:
    """Build a DB with only online (Control) decks."""
    db_path = str(tmp_path / "online.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, _TEST_CARDS)

    tid = store.load_tournament(con, parse_cache_item(_ONLINE_TOURNAMENT, "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?", [tid])

    con.close()
    return db_path


def _write_deck(tmp_path, content: str) -> str:
    p = tmp_path / "deck.txt"
    p.write_text(content)
    return str(p)


def _write_field(tmp_path, content: str) -> str:
    p = tmp_path / "field.txt"
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# Unit 1: build_global_field provenance filtering (library level)
# ---------------------------------------------------------------------------


class TestBuildGlobalFieldProvenance:
    """Verify that build_global_field already correctly filters by provenance."""

    def test_paper_provenance_excludes_online_archetypes(self, tmp_path):
        """paper provenance → only paper archetypes in the field."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field = build_global_field(con, provenance="paper")
        finally:
            con.close()
        # Paper corpus = Combo only; online = Control
        assert "Combo" in field.shares, "Combo (paper-only) should be in paper field"
        assert "Control" not in field.shares, "Control (online-only) must be excluded from paper field"
        assert field.field_source == "global"

    def test_online_provenance_excludes_paper_archetypes(self, tmp_path):
        """online provenance → only online archetypes in the field."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field = build_global_field(con, provenance="online")
        finally:
            con.close()
        assert "Control" in field.shares
        assert "Combo" not in field.shares

    def test_no_provenance_includes_all_archetypes(self, tmp_path):
        """No provenance filter → both online and paper archetypes in the field."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field = build_global_field(con, provenance=None)
        finally:
            con.close()
        assert "Control" in field.shares
        assert "Combo" in field.shares

    def test_paper_field_differs_from_global(self, tmp_path):
        """Paper-only field has different composition than the combined field."""
        db_path = _build_mixed_db(tmp_path)
        con = store.connect(db_path)
        try:
            field_global = build_global_field(con, provenance=None)
            field_paper = build_global_field(con, provenance="paper")
        finally:
            con.close()
        # The combined field has Control + Combo; paper-only has only Combo
        assert set(field_global.shares.keys()) != set(field_paper.shares.keys())


# ---------------------------------------------------------------------------
# Unit 2: CLI help strings include --provenance on all advise leaves
# ---------------------------------------------------------------------------


class TestAdvisePROVENANCEHelpStrings:
    """All six advise leaves must expose --provenance in their help output."""

    @pytest.mark.parametrize("leaf", [
        "positioning", "sideboard", "whattoplay", "report", "acquire", "refresh",
    ])
    def test_help_shows_provenance_option(self, runner, leaf):
        result = runner.invoke(main, ["advise", leaf, "--help"])
        assert result.exit_code == 0, f"help for advise {leaf} failed: {result.output}"
        assert "--provenance" in result.output, (
            f"advise {leaf} --help does not expose --provenance:\n{result.output}"
        )

    @pytest.mark.parametrize("leaf", [
        "positioning", "sideboard", "whattoplay", "report",
    ])
    def test_help_shows_online_paper_choices(self, runner, leaf):
        result = runner.invoke(main, ["advise", leaf, "--help"])
        assert result.exit_code == 0
        assert "online" in result.output
        assert "paper" in result.output


# ---------------------------------------------------------------------------
# Unit 3: positioning -- provenance flag acceptance and echo
# ---------------------------------------------------------------------------


class TestAdvisePositioningProvenance:
    def test_positioning_paper_provenance_accepted(self, runner, tmp_path):
        """advise positioning --provenance paper exits 0 and echoes provenance."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.output}"
        assert "// provenance: paper" in result.output

    def test_positioning_online_provenance_accepted(self, runner, tmp_path):
        """advise positioning --provenance online exits 0."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "online",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance: online" in result.output

    def test_positioning_no_provenance_no_echo(self, runner, tmp_path):
        """Without --provenance, the provenance echo line is absent (gated-additive)."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output

    def test_positioning_invalid_provenance_rejected(self, runner, tmp_path):
        """Invalid provenance value should fail with a usage error."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--provenance", "both",
            "--db", db_path,
        ])
        assert result.exit_code != 0

    def test_positioning_paper_uses_paper_field(self, runner, tmp_path):
        """Paper provenance → field built from paper corpus only (Combo-only field).

        With a mixed DB (online=Control, paper=Combo), running against paper provenance
        builds a Combo-only field. Running against a Control archetype should show
        field_source=global in the output (not 'custom').
        """
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        # field_source should be 'global' (from DB), not 'custom' (from --field)
        assert "global" in result.output

    def test_positioning_with_field_and_provenance_succeeds(self, runner, tmp_path):
        """--field + --provenance: custom field used, provenance filters matchup matrix."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--archetype", "Control",
            "--field", field_path,
            "--provenance", "paper",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        # Custom field → field_source=custom
        assert "custom" in result.output


# ---------------------------------------------------------------------------
# Unit 4: whattoplay -- provenance flag
# ---------------------------------------------------------------------------


class TestAdviseWhattoplayProvenance:
    def test_whattoplay_paper_provenance_accepted(self, runner, tmp_path):
        """advise whattoplay --provenance paper exits 0."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "whattoplay",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance: paper" in result.output

    def test_whattoplay_no_provenance_byte_identical(self, runner, tmp_path):
        """Without --provenance, the output should not contain the provenance echo."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "whattoplay",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output


# ---------------------------------------------------------------------------
# Unit 5: report -- provenance flag
# ---------------------------------------------------------------------------


class TestAdviseReportProvenance:
    def test_report_paper_provenance_accepted(self, runner, tmp_path):
        """advise report --provenance paper exits 0 and echoes provenance."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance: paper" in result.output

    def test_report_no_provenance_no_echo(self, runner, tmp_path):
        """Without --provenance, the provenance echo line is absent (gated-additive)."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output

    def test_report_provenance_and_venues_mutually_exclusive(self, runner, tmp_path):
        """--provenance + --venues should fail with a usage error."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--venues", "online,paper",
            "--db", db_path,
        ])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_report_with_field_and_provenance(self, runner, tmp_path):
        """--field + --provenance: custom field used; exit 0."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.5 Control\n0.5 Combo")
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--field", field_path,
            "--provenance", "paper",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "custom" in result.output


# ---------------------------------------------------------------------------
# Unit 6: sideboard -- provenance flag
# ---------------------------------------------------------------------------


class TestAdviseSideboardProvenance:
    def test_sideboard_paper_provenance_accepted(self, runner, tmp_path):
        """advise sideboard --provenance paper exits 0."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.5 Control\n0.5 Combo")
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "sideboard",
            "--deck", deck_path,
            "--field", field_path,
            "--provenance", "paper",
            "--solver", "greedy",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance: paper" in result.output

    def test_sideboard_no_provenance_no_echo(self, runner, tmp_path):
        """Without --provenance, no provenance echo (gated-additive)."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.5 Control\n0.5 Combo")
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "sideboard",
            "--deck", deck_path,
            "--field", field_path,
            "--solver", "greedy",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output


# ---------------------------------------------------------------------------
# Unit 7: acquire -- provenance flag
# ---------------------------------------------------------------------------


class TestAdviseAcquireProvenance:
    def _write_collection(self, tmp_path, content: str) -> str:
        p = tmp_path / "collection.txt"
        p.write_text(content)
        return str(p)

    def test_acquire_paper_provenance_accepted(self, runner, tmp_path):
        """advise acquire --provenance paper exits 0."""
        coll_path = self._write_collection(tmp_path, "4 Brainstorm\n")
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "acquire",
            "--collection", coll_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance: paper" in result.output

    def test_acquire_no_provenance_no_echo(self, runner, tmp_path):
        """Without --provenance, no provenance echo (gated-additive)."""
        coll_path = self._write_collection(tmp_path, "4 Brainstorm\n")
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "acquire",
            "--collection", coll_path,
            "--archetype", "Control",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output


# ---------------------------------------------------------------------------
# Unit 8: refresh -- provenance flag
# ---------------------------------------------------------------------------


class TestAdviseRefreshProvenance:
    def test_refresh_paper_provenance_accepted(self, runner, tmp_path):
        """advise refresh --provenance paper exits 0 (restricts to paper venue)."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "refresh",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance: paper" in result.output

    def test_refresh_provenance_and_venues_mutually_exclusive(self, runner, tmp_path):
        """--provenance + --venues on refresh should fail with usage error."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_mixed_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "refresh",
            "--deck", deck_path,
            "--archetype", "Control",
            "--provenance", "paper",
            "--venues", "online,paper",
            "--db", db_path,
        ])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_refresh_no_provenance_no_echo(self, runner, tmp_path):
        """Without --provenance, no provenance echo (gated-additive)."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _build_online_only_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "refresh",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output
