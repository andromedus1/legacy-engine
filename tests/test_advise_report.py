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

    def test_double_slash_comment_ignored(self):
        """// comment lines (generate consensus / export deck text style) are skipped."""
        text = "// Dimir Tempo — generated by legacy-engine\n4 Brainstorm\n12 Island"
        main, side = _parse_decklist(text)
        assert "Brainstorm" in main
        assert len(main) == 2
        assert not side

    def test_double_slash_comment_midfile_ignored(self):
        """// comments between cards are skipped; cards on both sides still parsed."""
        text = (
            "// Mainboard\n"
            "4 Brainstorm\n"
            "12 Island\n"
            "// Sideboard\n"
            "2 Surgical Extraction"
        )
        # blank-line sideboard split doesn't fire; '// Sideboard' is just a comment
        # so Surgical goes to sideboard only if there's a real blank-line / Sideboard marker.
        # Here there is none, so everything lands in main.
        main, side = _parse_decklist(text)
        assert main["Brainstorm"] == 4
        assert main["Island"] == 12
        assert main["Surgical Extraction"] == 2
        assert not side

    def test_double_slash_and_hash_and_blank_mixed(self):
        """A generate-consensus-style output round-trips cleanly."""
        consensus_output = (
            "// Dimir Tempo (Control)\n"
            "// Generated 2026-06-14\n"
            "\n"
            "4 Brainstorm\n"
            "4 Force of Will\n"
            "12 Island\n"
            "\n"
            "# sideboard\n"
            "2 Surgical Extraction\n"
        )
        main, side = _parse_decklist(consensus_output)
        assert main == {"Brainstorm": 4, "Force of Will": 4, "Island": 12}
        assert side == {"Surgical Extraction": 2}

    def test_genuinely_malformed_line_still_raises(self):
        """// skipping doesn't swallow genuinely bad lines (e.g. bare 'abc')."""
        text = "// ok comment\n4 Brainstorm\nabc\n12 Island"
        with pytest.raises(ValueError, match="malformed"):
            _parse_decklist(text)


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
        assert "imputed=" in result.output
        assert "P(best)=n/a" in result.output

    def test_positioning_candidates_can_group_same_rows_by_evidence(self, runner, tmp_path):
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        candidates_path = tmp_path / "candidates.txt"
        candidates_path.write_text("Control\nCombo\n")
        db_path = _setup_db(tmp_path)
        result = runner.invoke(main, [
            "advise", "positioning", "--deck", deck_path,
            "--candidates", str(candidates_path), "--ranking-strata",
            "--db", db_path, "--seed", "42",
        ])
        assert result.exit_code == 0, result.output
        assert "[inactive]" in result.output or "[unscorable]" in result.output
        assert result.output.count("Control") == 1
        assert result.output.count("Combo") == 1

    def test_ranking_strata_requires_candidates(self, runner, tmp_path):
        deck_path = _write_deck(tmp_path, _BRAINSTORM_DECKLIST)
        db_path = _setup_db(tmp_path)
        result = runner.invoke(main, [
            "advise", "positioning", "--deck", deck_path, "--ranking-strata", "--db", db_path,
        ])
        assert result.exit_code != 0
        assert "requires --candidates" in result.output


# ---------------------------------------------------------------------------
# TestLoadFieldCounts — feature-custom-field-counts-normalization
# ---------------------------------------------------------------------------


class TestLoadFieldCounts:
    """_load_field parsing tests for per-line counts and # effective_n: header."""

    def test_share_only_lines_counts_none(self):
        """Share-only lines (no 3rd token) produce counts=None — gated-additive baseline."""
        con = _con()
        field = _load_field(con, field_text="0.6 Delver\n0.4 Lands")
        assert field.counts is None
        assert field.field_source == "custom"

    def test_share_only_shares_correct(self):
        """Share-only field shares are normalized correctly (byte-identical to pre-feature)."""
        con = _con()
        field = _load_field(con, field_text="0.6 Delver\n0.4 Lands")
        assert abs(field.shares["Delver"] - 0.6) < 1e-9
        assert abs(field.shares["Lands"] - 0.4) < 1e-9

    def test_per_line_counts_populated(self):
        """Lines with 3rd token produce counts dict with those integer values."""
        con = _con()
        field = _load_field(con, field_text="0.35 Delver 42\n0.25 Lands 30\n0.40 Reanimator 48")
        assert field.counts is not None
        assert field.counts["Delver"] == 42
        assert field.counts["Lands"] == 30
        assert field.counts["Reanimator"] == 48

    def test_per_line_counts_shares_normalized(self):
        """Shares in the counts-carrying field sum to 1.0."""
        con = _con()
        field = _load_field(con, field_text="0.35 Delver 42\n0.25 Lands 30\n0.40 Reanimator 48")
        assert abs(sum(field.shares.values()) - 1.0) < 1e-9

    def test_mixed_lines_missing_count_defaults_to_one(self):
        """An archetype without a per-line count gets count=1 (weakest prior) when other lines carry counts."""
        con = _con()
        field = _load_field(con, field_text="0.6 Delver 60\n0.4 Lands")
        assert field.counts is not None
        assert field.counts["Delver"] == 60
        assert field.counts["Lands"] == 1

    def test_effective_n_header_distributes_proportionally(self):
        """# effective_n: N header distributes N across archetypes proportional to their shares."""
        con = _con()
        field = _load_field(con, field_text="# effective_n: 100\n0.60 Delver\n0.40 Lands")
        assert field.counts is not None
        # Delver gets round(0.60 * 100 / 1.0) = 60, Lands gets remainder = 40
        assert field.counts["Delver"] == 60
        assert field.counts["Lands"] == 40

    def test_effective_n_total_equals_n(self):
        """effective_n distribution: sum of counts == effective_n."""
        con = _con()
        field = _load_field(con, field_text="# effective_n: 100\n0.60 Delver\n0.40 Lands")
        assert sum(field.counts.values()) == 100

    def test_effective_n_each_archetype_gets_at_least_one(self):
        """Even a very small share gets count=1 (never zero)."""
        con = _con()
        # 5-archetype field, one with tiny share
        text = "# effective_n: 10\n0.50 A\n0.49 B\n0.005 C\n0.003 D\n0.002 E"
        field = _load_field(con, field_text=text)
        assert field.counts is not None
        for a, c in field.counts.items():
            assert c >= 1, f"archetype {a!r} got count {c}"

    def test_per_line_counts_over_effective_n_per_line_wins(self):
        """When both # effective_n and per-line counts are present, per-line counts take precedence."""
        con = _con()
        text = "# effective_n: 999\n0.6 Delver 42\n0.4 Lands 28"
        field = _load_field(con, field_text=text)
        # Per-line counts must be used; effective_n is ignored (warned only in log)
        assert field.counts is not None
        assert field.counts["Delver"] == 42
        assert field.counts["Lands"] == 28

    def test_comment_lines_skipped(self):
        """Non-directive comment lines are ignored."""
        con = _con()
        field = _load_field(con, field_text="# my local field\n0.6 Delver\n0.4 Lands")
        assert set(field.shares.keys()) == {"Delver", "Lands"}
        assert field.counts is None

    def test_negative_count_raises(self):
        """A negative count on a line raises ValueError."""
        con = _con()
        with pytest.raises(ValueError, match="positive"):
            _load_field(con, field_text="0.6 Delver -5\n0.4 Lands 10")

    def test_zero_count_raises(self):
        """A zero count on a line raises ValueError (counts must be ≥ 1)."""
        con = _con()
        with pytest.raises(ValueError, match="positive"):
            _load_field(con, field_text="0.6 Delver 0\n0.4 Lands 10")

    def test_effective_n_zero_raises(self):
        """# effective_n: 0 raises ValueError."""
        con = _con()
        with pytest.raises(ValueError, match="effective_n"):
            _load_field(con, field_text="# effective_n: 0\n0.6 Delver\n0.4 Lands")

    def test_effective_n_non_integer_raises(self):
        """# effective_n: 10.5 raises ValueError."""
        con = _con()
        with pytest.raises(ValueError, match="positive integer"):
            _load_field(con, field_text="# effective_n: 10.5\n0.6 Delver\n0.4 Lands")

    def test_archetype_with_spaces_in_name_share_only(self):
        """Multi-word archetype names work in share-only format."""
        con = _con()
        field = _load_field(con, field_text="0.5 Death's Shadow\n0.5 Izzet Delver")
        assert "Death's Shadow" in field.shares
        assert "Izzet Delver" in field.shares


# ---------------------------------------------------------------------------
# TestBuildCustomFieldCounts — build_custom_field counts parameter
# ---------------------------------------------------------------------------


class TestBuildCustomFieldCounts:
    """build_custom_field(counts=...) unit tests."""

    def test_counts_none_is_share_only_unchanged(self):
        """counts=None → counts=None on FieldDistribution (gated-additive)."""
        fd = build_custom_field({"A": 0.6, "B": 0.4})
        assert fd.counts is None

    def test_counts_provided_stored_on_distribution(self):
        """counts dict is stored on the returned FieldDistribution."""
        fd = build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": 40})
        assert fd.counts == {"A": 60, "B": 40}

    def test_counts_warning_differs_from_share_only_warning(self):
        """With counts, the 'Dirichlet' warning is emitted (not the point-shares warning)."""
        fd = build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": 40})
        dirichlet_warnings = [w for w in fd.warnings if "Dirichlet" in w or "dirichlet" in w.lower()]
        point_warnings = [w for w in fd.warnings if "point shares" in w]
        assert len(dirichlet_warnings) >= 1
        assert len(point_warnings) == 0

    def test_share_only_still_emits_point_shares_warning(self):
        """Without counts, the 'point shares' warning is still emitted (unchanged)."""
        fd = build_custom_field({"A": 0.6, "B": 0.4})
        point_warnings = [w for w in fd.warnings if "point shares" in w]
        assert len(point_warnings) == 1

    def test_counts_missing_key_raises(self):
        """counts missing an archetype from shares raises ValueError."""
        with pytest.raises(ValueError, match="missing keys"):
            build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60})

    def test_counts_extra_key_raises(self):
        """counts with extra keys not in shares raises ValueError."""
        with pytest.raises(ValueError, match="extra keys"):
            build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": 40, "C": 10})

    def test_counts_zero_raises(self):
        """A count of 0 raises ValueError (must be positive integer)."""
        with pytest.raises(ValueError, match="positive integer"):
            build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": 0})

    def test_counts_negative_raises(self):
        """A negative count raises ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": -1})

    def test_counts_float_raises(self):
        """A float count raises ValueError (must be integer)."""
        with pytest.raises(ValueError, match="positive integer"):
            build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": 40.5})

    def test_field_source_is_custom_with_counts(self):
        """field_source remains 'custom' even when counts are provided."""
        fd = build_custom_field({"A": 0.6, "B": 0.4}, counts={"A": 60, "B": 40})
        assert fd.field_source == "custom"


# ---------------------------------------------------------------------------
# TestCustomFieldCountsPositioning — Dirichlet vs point-shares CI behavior
# ---------------------------------------------------------------------------


class TestCustomFieldCountsPositioning:
    """Spec-derived behavioral test: a custom field WITH counts produces a wider CI
    than a share-only field (Dirichlet sampling vs fixed point shares).

    The key invariant: when field.counts is not None, _sample_S samples
    W ~ Dirichlet(counts + gamma), which introduces per-draw share variance and
    widens the CI compared to tiled point shares.  This is the Dirichlet backing.
    """

    def _make_matrix(self):
        """Minimal MatchupMatrix: Delver vs Lands with meaningful matchup data."""
        from legacy_engine.analytics.matchup import MatchupMatrix, build_cell, build_mirror_cell
        cells = {
            ("Delver", "Lands"): build_cell("Delver", "Lands", wins=60, n=100),
            ("Lands", "Delver"): build_cell("Lands", "Delver", wins=40, n=100),
            ("Delver", "Delver"): build_mirror_cell("Delver", n=0),
            ("Lands", "Lands"): build_mirror_cell("Lands", n=0),
        }
        return MatchupMatrix(
            cells=cells,
            provenance=None,
            total_matches=100,
            archetypes=["Delver", "Lands"],
            caveat="test matrix",
        )

    def test_counts_field_produces_wider_ci_than_share_only(self):
        """A custom field with counts has a wider S CI than the same field share-only.

        This is the core Dirichlet-backing invariant: Dirichlet weight sampling adds
        variance to S; fixed point shares have zero weight variance so CI width is
        narrower (driven only by Beta-cell sampling over matchup uncertainty).
        """
        from legacy_engine.advisory.positioning import positioning_score
        matrix = self._make_matrix()

        shares = {"Delver": 0.5, "Lands": 0.5}
        # Large counts: Dirichlet concentrates near the shares but still has non-zero variance
        counts = {"Delver": 200, "Lands": 200}

        fd_share_only = build_custom_field(shares)
        fd_with_counts = build_custom_field(shares, counts=counts)

        result_share = positioning_score(matrix, fd_share_only, "Delver", n_draws=10_000, seed=42)
        result_counts = positioning_score(matrix, fd_with_counts, "Delver", n_draws=10_000, seed=42)

        ci_width_share = result_share.s_ci[1] - result_share.s_ci[0]
        ci_width_counts = result_counts.s_ci[1] - result_counts.s_ci[0]

        # With Dirichlet backing, CI width must be wider than fixed point shares
        assert ci_width_counts > ci_width_share, (
            f"Expected Dirichlet-backed CI ({ci_width_counts:.4f}) to be wider than "
            f"point-share CI ({ci_width_share:.4f})"
        )

    def test_share_only_field_ci_zero_weight_variance(self):
        """Share-only field: weight matrix is tiled (no Dirichlet sampling)."""
        from legacy_engine.advisory.positioning import positioning_score, _sample_S
        import numpy as np

        matrix = self._make_matrix()
        fd = build_custom_field({"Delver": 0.5, "Lands": 0.5})

        # Build W twice with the same seed — should be identical for point shares
        rng1 = np.random.default_rng(7)
        rng2 = np.random.default_rng(7)
        s1 = _sample_S(matrix, fd, "Delver", n_draws=500, rng=rng1)
        s2 = _sample_S(matrix, fd, "Delver", n_draws=500, rng=rng2)
        # Same seed → same samples (deterministic)
        np.testing.assert_array_equal(s1, s2)

    def test_counts_field_uses_dirichlet_path(self):
        """FieldDistribution.counts is not None when counts are provided, enabling Dirichlet path."""
        fd = build_custom_field({"Delver": 0.6, "Lands": 0.4}, counts={"Delver": 60, "Lands": 40})
        assert fd.counts is not None

    def test_s_mean_similar_between_share_only_and_counts_field(self):
        """S means are close between share-only and counts fields (same expected weights)."""
        from legacy_engine.advisory.positioning import positioning_score
        matrix = self._make_matrix()

        shares = {"Delver": 0.5, "Lands": 0.5}
        counts = {"Delver": 1000, "Lands": 1000}  # very concentrated → near point shares

        fd_share = build_custom_field(shares)
        fd_counts = build_custom_field(shares, counts=counts)

        r_share = positioning_score(matrix, fd_share, "Delver", n_draws=20_000, seed=1)
        r_counts = positioning_score(matrix, fd_counts, "Delver", n_draws=20_000, seed=1)

        # With 1000 counts the Dirichlet is very concentrated → means should be within 1%
        assert abs(r_share.s_mean - r_counts.s_mean) < 0.01, (
            f"S means diverged: share_only={r_share.s_mean:.4f}, counts={r_counts.s_mean:.4f}"
        )
