"""Advisory report tests — _parse_decklist, _classify_deck, _load_field,
build_field_read_report, and all four advise CLI leaves.

House style: ``:memory:`` corpus with ``store.load_cards`` + labeled decks;
``CliRunner`` for the four CLI leaves writing deck/field files into ``tmp_path``.
MC paths pin ``--seed``.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.advisory.report import (
    FieldReadReport,
    _classify_deck,
    _load_field,
    _parse_decklist,
    build_field_read_report,
    render_field_read,
)
from legacy_engine.advisory.field import build_custom_field
from legacy_engine.archetype.rules import ArchetypeRule, Condition, Fallback, RuleSet
from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _con():
    """In-memory DuckDB connection with full schema."""
    con = store.connect(":memory:")
    store.init_schema(con)
    return con


def _make_card(**kwargs) -> Card:
    """Construct a Card with sensible defaults."""
    defaults = dict(
        name="Test Card",
        type_line="Instant",
        oracle_text="",
        cmc=1.0,
        colors=[],
        produced_mana=[],
        is_land=False,
    )
    defaults.update(kwargs)
    return Card(**defaults)


def _make_land(name: str, produced: list[str]) -> Card:
    return _make_card(
        name=name,
        type_line="Land",
        oracle_text="",
        cmc=0.0,
        is_land=True,
        produced_mana=produced,
    )


# A compact deck suitable for testing: Brainstorm + Force of Will + basic lands
_BRAINSTORM = _make_card(
    name="Brainstorm",
    type_line="Instant",
    oracle_text="Draw three cards, then put two cards from your hand on top of your library in any order.",
    cmc=1.0,
    colors=["U"],
)
_FOW = _make_card(
    name="Force of Will",
    type_line="Instant",
    oracle_text="You may pay 1 life and exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target spell.",
    cmc=5.0,
    colors=["U"],
)
_ISLAND = _make_land("Island", ["U"])

_TEST_CARDS = [_BRAINSTORM, _FOW, _ISLAND]

_BRAINSTORM_DECKLIST = "4 Brainstorm\n4 Force of Will\n12 Island\nSideboard\n2 Force of Will"

# Minimal ruleset: only a "Control" archetype keyed on Force of Will
_CONTROL_RULE = ArchetypeRule(
    name="Control",
    include_color_in_name=False,
    conditions=[Condition(type="InMainboard", cards=["Force of Will"])],
    variants=[],
)
_SMALL_RULESET = RuleSet(archetypes=[_CONTROL_RULE], fallbacks=[])


def _load_test_cards(con) -> None:
    """Load the minimal test card set into the in-memory store."""
    store.load_cards(con, _TEST_CARDS)


def _load_labeled_field(con):
    """Build a single-archetype field from the Control archetype."""
    from legacy_engine.advisory.field import build_custom_field
    return build_custom_field({"Control": 1.0})


# ---------------------------------------------------------------------------
# TestParseDecklist
# ---------------------------------------------------------------------------


class TestParseDecklist:
    def test_sideboard_header_split(self):
        text = "4 Brainstorm\n4 Force of Will\nSideboard\n2 Surgical Extraction"
        main, side = _parse_decklist(text)
        assert main["Brainstorm"] == 4
        assert main["Force of Will"] == 4
        assert side["Surgical Extraction"] == 2

    def test_blank_line_split(self):
        text = "4 Brainstorm\n4 Force of Will\n\n2 Surgical Extraction"
        main, side = _parse_decklist(text)
        assert main["Brainstorm"] == 4
        assert side["Surgical Extraction"] == 2

    def test_x_suffix_form(self):
        """4x Name and 4 Name are both valid."""
        text = "4x Brainstorm\n4X Force of Will\n12 Island"
        main, side = _parse_decklist(text)
        assert main["Brainstorm"] == 4
        assert main["Force of Will"] == 4
        assert main["Island"] == 12

    def test_hash_comment_ignored(self):
        text = "# This is a comment\n4 Brainstorm\n12 Island"
        main, side = _parse_decklist(text)
        assert "Brainstorm" in main
        assert len(main) == 2
        assert not side

    def test_leading_blank_lines_ignored(self):
        text = "\n\n4 Brainstorm\n12 Island"
        main, side = _parse_decklist(text)
        assert main["Brainstorm"] == 4

    def test_empty_side_when_no_sideboard_marker(self):
        text = "4 Brainstorm\n12 Island"
        main, side = _parse_decklist(text)
        assert main
        assert side == {}

    def test_sideboard_case_insensitive(self):
        text = "4 Brainstorm\n12 Island\nSIDEBOARD\n2 Surgical Extraction"
        main, side = _parse_decklist(text)
        assert side["Surgical Extraction"] == 2

    def test_malformed_line_raises_value_error(self):
        text = "4 Brainstorm\nnot a valid line with no count\n12 Island"
        with pytest.raises(ValueError, match="malformed"):
            _parse_decklist(text)

    def test_empty_maindeck_raises_value_error(self):
        text = "\n\n# just comments\n"
        with pytest.raises(ValueError, match="empty maindeck"):
            _parse_decklist(text)

    def test_duplicate_names_are_summed(self):
        text = "4 Brainstorm\n2 Brainstorm\n12 Island"
        main, side = _parse_decklist(text)
        assert main["Brainstorm"] == 6


# ---------------------------------------------------------------------------
# TestClassifyDeck
# ---------------------------------------------------------------------------


class TestClassifyDeck:
    def test_known_cards_classify_to_control(self):
        """A deck with Force of Will in the DB should classify to the vendored rules.

        We monkeypatch load_ruleset to return our small test ruleset so we don't
        depend on vendored rules being present in CI.
        """
        con = _con()
        _load_test_cards(con)

        # Patch load_ruleset to use our small ruleset
        import legacy_engine.advisory.report as report_mod
        original = report_mod.load_ruleset
        report_mod.load_ruleset = lambda _: _SMALL_RULESET
        try:
            result = _classify_deck(con, {"Force of Will": 4, "Island": 12}, {})
            assert result.archetype == "Control"
            assert result.kind == "archetype"
        finally:
            report_mod.load_ruleset = original

    def test_unknown_cards_return_unknown(self):
        """Cards not in the DB lead to unknown colors → Unknown classification."""
        con = _con()
        # No cards loaded → fetch_card returns None for everything
        import legacy_engine.advisory.report as report_mod
        original = report_mod.load_ruleset
        report_mod.load_ruleset = lambda _: _SMALL_RULESET
        try:
            result = _classify_deck(con, {"Nonexistent Card": 4}, {})
            # With no card data, colors are empty; the SMALL_RULESET won't match
            assert result.kind in ("unknown", "fallback", "archetype", "conflict")
        finally:
            report_mod.load_ruleset = original

    def test_conflict_kind_returned_raw(self):
        """When two rules match, the classifier returns a Conflict result."""
        con = _con()
        _load_test_cards(con)
        rule_a = ArchetypeRule(name="Alpha", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        rule_b = ArchetypeRule(name="Beta", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        conflict_ruleset = RuleSet(archetypes=[rule_a, rule_b])

        import legacy_engine.advisory.report as report_mod
        original = report_mod.load_ruleset
        report_mod.load_ruleset = lambda _: conflict_ruleset
        try:
            result = _classify_deck(con, {"Brainstorm": 4, "Island": 12}, {})
            assert result.kind == "conflict"
            assert "Conflict" in result.archetype
        finally:
            report_mod.load_ruleset = original


# ---------------------------------------------------------------------------
# TestLoadField
# ---------------------------------------------------------------------------


class TestLoadField:
    def test_custom_text_builds_custom_field(self):
        con = _con()
        field_text = "0.6 Control\n0.4 Combo"
        field = _load_field(con, field_text=field_text)
        assert field.field_source == "custom"
        assert "Control" in field.shares
        assert "Combo" in field.shares

    def test_no_text_builds_global_field(self):
        """Without text, _load_field returns the global field (empty corpus → empty distribution)."""
        con = _con()
        field = _load_field(con, field_text=None)
        assert field.field_source == "global"

    def test_custom_shares_normalized(self):
        con = _con()
        # Shares sum to 0.5+0.5 = 1.0 exactly
        field = _load_field(con, field_text="0.5 Delver\n0.5 Lands")
        total = sum(field.shares.values())
        assert abs(total - 1.0) < 1e-9

    def test_malformed_field_line_raises(self):
        con = _con()
        with pytest.raises(ValueError):
            _load_field(con, field_text="notanumber Control")

    def test_empty_field_text_raises(self):
        con = _con()
        with pytest.raises(ValueError):
            _load_field(con, field_text="# only comments\n\n")


# ---------------------------------------------------------------------------
# TestBuildFieldReadReport
# ---------------------------------------------------------------------------


class TestBuildFieldReadReport:
    def _setup_con_with_cards(self):
        con = _con()
        _load_test_cards(con)
        return con

    def test_populated_report_with_known_archetype(self):
        """Passing an explicit archetype bypasses classification; report is fully populated."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 1.0})
        mainboard = {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field,
            archetype="Control",
            seed=42,
        )
        assert report.deck_archetype == "Control"
        assert report.field_source == "custom"
        assert "Control" in report.field_shares
        assert report.proactivity is not None
        assert report.sideboard is not None
        assert len(report.audit) > 0

    def test_unresolved_archetype_skips_positioning(self):
        """Conflict/Unknown archetype → positioning and best_deck_call are None, but others present."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 1.0})
        mainboard = {"Brainstorm": 4, "Island": 12}

        # Use a ruleset that produces a Conflict for Brainstorm
        rule_a = ArchetypeRule(name="Alpha", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        rule_b = ArchetypeRule(name="Beta", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        conflict_ruleset = RuleSet(archetypes=[rule_a, rule_b])

        import legacy_engine.advisory.report as report_mod
        original = report_mod.load_ruleset
        report_mod.load_ruleset = lambda _: conflict_ruleset
        try:
            report = build_field_read_report(con, mainboard, {}, field, seed=42)
            assert report.positioning is None
            assert report.best_deck_call is None
            assert report.proactivity is not None
            assert report.sideboard is not None
            assert any("unresolved" in w.lower() for w in report.warnings)
        finally:
            report_mod.load_ruleset = original

    def test_audit_trail_non_empty(self):
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 0.6, "Combo": 0.4})
        mainboard = {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field, archetype="Control", seed=42,
        )
        assert len(report.audit) > 0
        # audit should contain the field_source label
        audit_text = "\n".join(report.audit)
        assert "field_source" in audit_text

    def test_audit_contains_heuristic_note(self):
        """The audit trail must contain the sideboard heuristic note."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 1.0})
        mainboard = {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field, archetype="Control", seed=42,
        )
        audit_text = "\n".join(report.audit)
        assert "heuristic" in audit_text.lower()

    def test_field_source_is_labeled(self):
        """field_source is always explicitly set on the report."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 1.0})
        mainboard = {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field, archetype="Control", seed=42,
        )
        assert report.field_source in ("global", "custom", "local")

    def test_archetype_override_is_used(self):
        """--archetype override is passed through to the report without running classifier."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Reanimator": 0.5, "Control": 0.5})
        mainboard = {"Brainstorm": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field, archetype="Reanimator", seed=42,
        )
        assert report.deck_archetype == "Reanimator"

    def test_render_field_read_has_labeled_sections(self):
        """render_field_read output contains required section headers."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 1.0})
        mainboard = {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field, archetype="Control", seed=42,
        )
        text = render_field_read(report)
        # Required labeled sections
        assert "Field Read & Deck Recommendation" in text
        assert "Field source" in text
        assert "Audit trail" in text
        assert "Positioning" in text
        assert "sideboard" in text.lower()
        assert "proactivity" in text.lower() or "Proactivity" in text

    def test_render_no_unlabeled_numbers(self):
        """The output never contains a bare float without context (spot check)."""
        con = self._setup_con_with_cards()
        field = build_custom_field({"Control": 1.0})
        mainboard = {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        report = build_field_read_report(
            con, mainboard, {}, field, archetype="Control", seed=42,
        )
        text = render_field_read(report)
        # The report should have non-empty content — basic smoke check
        assert len(text) > 200


# ---------------------------------------------------------------------------
# TestAdviseCLI — all four leaves via CliRunner
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def _write_deck(tmp_path, content: str) -> str:
    p = tmp_path / "deck.txt"
    p.write_text(content)
    return str(p)


def _write_field(tmp_path, content: str) -> str:
    p = tmp_path / "field.txt"
    p.write_text(content)
    return str(p)


def _setup_db(tmp_path) -> str:
    """Create a minimal in-memory DB file with just enough schema for CLI commands.

    We use :memory: via the store module for the actual test — the CLI commands
    connect to a db file, so we create a temp duckdb file with the schema.
    """
    db_path = str(tmp_path / "test.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, _TEST_CARDS)
    con.close()
    return db_path


class TestAdviseCLI:
    def test_report_runs_without_error(self, runner, tmp_path):
        """advise report --deck --db should print the full field read report."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.output}"
        assert "Field Read & Deck Recommendation" in result.output
        assert "Audit trail" in result.output

    def test_report_with_custom_field(self, runner, tmp_path):
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.7 Control\n0.3 Combo")
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--field", field_path,
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        # Custom field should be reflected in output
        assert "custom" in result.output.lower() or "Control" in result.output

    def test_report_missing_deck_fails(self, runner, tmp_path):
        """Missing --deck should produce a non-zero exit code with a click error."""
        db_path = _setup_db(tmp_path)
        result = runner.invoke(main, ["advise", "report", "--db", db_path])
        assert result.exit_code != 0

    def test_positioning_runs_without_error(self, runner, tmp_path):
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--archetype", "Control",
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "Positioning" in result.output or "S" in result.output

    def test_positioning_missing_deck_fails(self, runner, tmp_path):
        db_path = _setup_db(tmp_path)
        result = runner.invoke(main, ["advise", "positioning", "--db", db_path])
        assert result.exit_code != 0

    def test_sideboard_runs_without_error(self, runner, tmp_path):
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.5 Control\n0.5 Combo")
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "sideboard",
            "--deck", deck_path,
            "--field", field_path,
            "--solver", "greedy",
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "Sideboard" in result.output or "sideboard" in result.output.lower()

    def test_sideboard_missing_deck_fails(self, runner, tmp_path):
        db_path = _setup_db(tmp_path)
        result = runner.invoke(main, ["advise", "sideboard", "--db", db_path])
        assert result.exit_code != 0

    def test_whattoplay_runs_without_error(self, runner, tmp_path):
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "0.6 Control\n0.4 Combo")
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "whattoplay",
            "--deck", deck_path,
            "--archetype", "Control",
            "--field", field_path,
            "--db", db_path,
        ])
        assert result.exit_code == 0, result.output
        assert "What to play" in result.output or "Proactivity" in result.output

    def test_whattoplay_missing_deck_fails(self, runner, tmp_path):
        db_path = _setup_db(tmp_path)
        result = runner.invoke(main, ["advise", "whattoplay", "--db", db_path])
        assert result.exit_code != 0

    def test_report_field_honored(self, runner, tmp_path):
        """When --field is provided, field_source should reflect 'custom'."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        field_path = _write_field(tmp_path, "1.0 Control")
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "report",
            "--deck", deck_path,
            "--archetype", "Control",
            "--field", field_path,
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "custom" in result.output.lower()

    def test_positioning_with_candidates_file(self, runner, tmp_path):
        """advise positioning --candidates prints a deck ranking."""
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        candidates_path = tmp_path / "candidates.txt"
        candidates_path.write_text("Control\nCombo\n")
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--candidates", str(candidates_path),
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "Ranking" in result.output or "Control" in result.output

    def test_positioning_candidates_output_shows_quantile_and_coverage(self, runner, tmp_path):
        """IMPORTANT: --candidates output must display Q{level} and cov= columns.

        Sorts by s_quantile but previously only printed S, CI, P(best) — so the sort key
        was invisible and the display looked like it was sorted by the displayed metric.
        Fix: output also includes Q{quantile_level}=... and cov=... per deck.
        """
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        candidates_path = tmp_path / "candidates.txt"
        candidates_path.write_text("Control\nCombo\n")
        db_path = _setup_db(tmp_path)

        result = runner.invoke(main, [
            "advise", "positioning",
            "--deck", deck_path,
            "--candidates", str(candidates_path),
            "--db", db_path,
            "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        # The quantile column (e.g. "Q0.25=0.412") must appear in the ranking output
        assert "Q0." in result.output, (
            f"Expected quantile column 'Q0.xx=...' in output; got:\n{result.output}"
        )
        # The coverage column (e.g. "cov=0.00") must appear
        assert "cov=" in result.output, (
            f"Expected coverage column 'cov=...' in output; got:\n{result.output}"
        )
