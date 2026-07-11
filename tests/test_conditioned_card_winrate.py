"""CLI tests for epic-subarchetype-resolution-card-winrate.

Covers Unit 5 of the feature design:
  (a) golden byte-identical defaults — `report cards` w/o --conditioned and `report subgroup`
      w/o --winrates must render EXACTLY the same text as before this feature landed.
  (b) the Bauble-shaped sign-conflict scenario end-to-end via `report cards --conditioned`.
  (c) `--variant` narrows the conditioned denominator further.
  (d) `report subgroup --winrates` renders per-camp win% + match-n + tier + thin note.

All DB access is hermetic (`--db <tmp file>`), never the default DB.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


@pytest.fixture
def runner():
    return CliRunner()


def _card(name: str, count: int = 4) -> dict:
    return {"CardName": name, "Count": count}


def _deck(player: str, main: list[dict]) -> dict:
    return {"Player": player, "Result": "1st", "Mainboard": main, "Sideboard": []}


# ---------------------------------------------------------------------------
# (a) Golden byte-identical defaults
# ---------------------------------------------------------------------------


@pytest.fixture
def golden_db_path(tmp_path):
    """A small, deterministic corpus used ONLY to pin the pre-feature default output.

    Mirrors the shape of tests/conftest.py's make_rounds_corpus (Control beats Combo
    twice, one mirror, one draw) but written directly to a file-backed DB so both
    `report cards` and `report subgroup` can run against it.
    """
    raw = {
        "Tournament": {
            "Name": "Golden Corpus", "Date": "2026-05-01",
            "Uri": "https://www.mtgo.com/decklist/golden-corpus-2026-05-01",
            "Formats": "Legacy",
        },
        "Decks": [
            _deck("alice", [_card("Brainstorm"), _card("Mishra's Bauble", 1)]),
            _deck("alice2", [_card("Brainstorm"), _card("Mishra's Bauble", 1)]),
            _deck("bob", [_card("Dark Ritual")]),
            _deck("bob2", [_card("Dark Ritual")]),
        ],
        "Rounds": [
            {"Player1": "alice", "Player2": "bob", "Result": "2-1"},
            {"Player1": "alice2", "Player2": "bob2", "Result": "2-1"},
            {"Player1": "alice", "Player2": "alice2", "Result": "2-1"},
            {"Player1": "alice", "Player2": "bob", "Result": "1-1"},
        ],
        "Standings": [],
    }
    db_path = tmp_path / "golden.duckdb"
    con = store.connect(str(db_path))
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player IN ('alice','alice2')",
        [tid],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player IN ('bob','bob2')",
        [tid],
    )
    con.close()
    return str(db_path)


class TestGoldenReportCardsDefault:
    """`report cards` without --conditioned must render exactly as it did pre-feature."""

    GOLDEN = (
        "=== Card Win-Rates [board=main (marginal), tier=all] ===\n"
        "NOTE: presence-correlational — NOT causal. See registered 75, not game-by-game play.\n"
        "Window: 2025-01-01 → now  |  decisive matches in window: 2\n"
        f"{'Card':<35}  {'Board':<5}  {'n':>6}  {'p_raw':>7}  {'p_shrunk':>8}  {'lift':>7}  {'tier':<12}\n"
        + "-" * 90 + "\n"
        "Brainstorm                           main        2    1.000     0.559   +0.059  speculative \n"
        "Dark Ritual                          main        2    0.000     0.441   -0.059  speculative \n"
        "Mishra's Bauble                      main        2    1.000     0.559   +0.059  speculative \n"
    )

    def test_golden_output_byte_identical(self, runner, golden_db_path):
        result = runner.invoke(
            main,
            ["report", "cards", "--db", golden_db_path, "--board", "main", "--since", "2025-01-01"],
        )
        assert result.exit_code == 0, result.output
        # Strip the leading freshness-echo lines (data-dependent on "today"), compare the rest.
        body = result.output.split("\n\n", 1)[1]
        assert body == self.GOLDEN, (
            f"report cards default output changed!\n--- expected ---\n{self.GOLDEN!r}\n"
            f"--- got ---\n{body!r}"
        )

    def test_no_conditioned_columns_or_sign_conflict_lines_leak_into_default(self, runner, golden_db_path):
        result = runner.invoke(
            main,
            ["report", "cards", "--db", golden_db_path, "--board", "main", "--since", "2025-01-01"],
        )
        assert "conditioned" not in result.output
        assert "sign conflict" not in result.output
        assert "lift_marg" not in result.output


class TestGoldenReportSubgroupDefault:
    """`report subgroup` without --winrates must render exactly as it did pre-feature."""

    def test_no_winrate_lines_by_default(self, runner, golden_db_path):
        result = runner.invoke(
            main,
            [
                "report", "subgroup",
                "--archetype", "Control", "--signature", "Mishra's Bauble",
                "--since", "2025-01-01", "--until", "2027-01-01",
                "--db", golden_db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "win%" not in result.output
        assert "thin win-rate" not in result.output

    def test_default_header_and_subgroup_counts_unchanged(self, runner, golden_db_path):
        result = runner.invoke(
            main,
            [
                "report", "subgroup",
                "--archetype", "Control", "--signature", "Mishra's Bauble",
                "--since", "2025-01-01", "--until", "2027-01-01",
                "--db", golden_db_path,
            ],
        )
        assert "=== Subgroup Diff: 'Control' split on \"Mishra's Bauble\" (mainboard) ===" in result.output
        # Both Control decks (alice, alice2) run Mishra's Bauble — with=2, without=0.
        assert "with-subgroup:    n=2" in result.output
        assert "without-subgroup: n=0" in result.output


# ---------------------------------------------------------------------------
# (b) + (c) `report cards --conditioned [--variant]` — the Bauble sign-conflict scenario
# ---------------------------------------------------------------------------


def _build_bauble_signconflict_tournament() -> dict:
    """Mishra's Bauble is run by BOTH a strong archetype (Dimir Tempo) and a weak one
    (Weak Aggro). Dimir Tempo's own Bauble decks win 3/4; Weak Aggro's Bauble decks win
    1/6 — pooling both makes the marginal read negative even though Dimir Tempo's own
    number is clearly positive.  This is the motivating cross-archetype-contamination bug.
    """
    decks: list[dict] = []
    rounds: list[dict] = []

    # Dimir Tempo camps: split further into CampA (2 wins) / CampB (1 win, 1 loss) so
    # --variant narrowing has something distinct to prove.
    dt_camp_a = [("dtA1", "oppA1"), ("dtA2", "oppA2")]
    dt_camp_b_win = [("dtB1", "oppB1")]
    dt_camp_b_loss = [("dtB2", "oppB2")]
    wa_win = [("wa1", "oppW1")]
    wa_loss = [("wa2", "oppW2"), ("wa3", "oppW3"), ("wa4", "oppW4"), ("wa5", "oppW5"), ("wa6", "oppW6")]

    for hero, opp in dt_camp_a + dt_camp_b_win + wa_win:
        decks.append(_deck(hero, [_card("Mishra's Bauble", 1)]))
        decks.append(_deck(opp, [_card("Filler")]))
        rounds.append({"Player1": hero, "Player2": opp, "Result": "2-0"})
    for hero, opp in dt_camp_b_loss + wa_loss:
        decks.append(_deck(hero, [_card("Mishra's Bauble", 1)]))
        decks.append(_deck(opp, [_card("Filler")]))
        rounds.append({"Player1": opp, "Player2": hero, "Result": "2-0"})

    return {
        "Tournament": {
            "Name": "Bauble Sign Conflict", "Date": "2026-06-01",
            "Uri": "https://test.com/bauble-sign-conflict", "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": rounds,
        "Standings": [],
    }, dt_camp_a, dt_camp_b_win, dt_camp_b_loss, wa_win, wa_loss


@pytest.fixture
def sign_conflict_db_path(tmp_path):
    raw, dt_camp_a, dt_camp_b_win, dt_camp_b_loss, wa_win, wa_loss = _build_bauble_signconflict_tournament()
    db_path = tmp_path / "sign_conflict.duckdb"
    con = store.connect(str(db_path))
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))

    camp_a_players = [h for h, _ in dt_camp_a]
    camp_b_players = [h for h, _ in dt_camp_b_win + dt_camp_b_loss]
    wa_players = [h for h, _ in wa_win + wa_loss]
    opp_players = [o for _, o in dt_camp_a + dt_camp_b_win + dt_camp_b_loss + wa_win + wa_loss]

    con.execute(
        "UPDATE decks SET archetype = 'Dimir Tempo', variant = 'CampA' "
        "WHERE tournament_id = ? AND player = ANY(?)", [tid, camp_a_players],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Dimir Tempo', variant = 'CampB' "
        "WHERE tournament_id = ? AND player = ANY(?)", [tid, camp_b_players],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Weak Aggro' "
        "WHERE tournament_id = ? AND player = ANY(?)", [tid, wa_players],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Opponent Pool' "
        "WHERE tournament_id = ? AND player = ANY(?)", [tid, opp_players],
    )
    con.close()
    return str(db_path)


class TestReportCardsConditioned:
    def test_conditioned_requires_archetype(self, runner, sign_conflict_db_path):
        result = runner.invoke(
            main, ["report", "cards", "--conditioned", "--db", sign_conflict_db_path],
        )
        assert result.exit_code != 0
        assert "--conditioned requires --archetype" in result.output

    def test_variant_requires_conditioned(self, runner, sign_conflict_db_path):
        result = runner.invoke(
            main,
            [
                "report", "cards", "--archetype", "Dimir Tempo", "--variant", "CampA",
                "--db", sign_conflict_db_path,
            ],
        )
        assert result.exit_code != 0
        assert "--variant requires --conditioned" in result.output

    def test_conditioned_rejects_vs_loudly(self, runner, sign_conflict_db_path):
        """Completion-review finding: --conditioned + --vs used to silently ignore --vs
        (opponent-specific conditioned values aren't implemented) — must fail loud instead."""
        result = runner.invoke(
            main,
            [
                "report", "cards", "--archetype", "Dimir Tempo", "--conditioned",
                "--vs", "Weak Aggro", "--db", sign_conflict_db_path,
            ],
        )
        assert result.exit_code != 0
        assert "--conditioned does not support --vs yet" in result.output

    def test_conditioned_exits_zero_and_shows_both_lifts(self, runner, sign_conflict_db_path):
        result = runner.invoke(
            main,
            [
                "report", "cards", "--archetype", "Dimir Tempo", "--conditioned",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--db", sign_conflict_db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Mishra's Bauble" in result.output
        assert "lift_marg" in result.output
        assert "lift_cond" in result.output

    def test_sign_conflict_line_fires_for_bauble(self, runner, sign_conflict_db_path):
        """The core scenario: pooled marginal negative, Dimir-Tempo-conditioned positive."""
        result = runner.invoke(
            main,
            [
                "report", "cards", "--archetype", "Dimir Tempo", "--conditioned",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--db", sign_conflict_db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "// sign conflict: Mishra's Bauble" in result.output
        assert "must not use the marginal alone" in result.output

    def test_variant_narrows_denominator(self, runner, sign_conflict_db_path):
        """--variant CampA (2/2 wins) vs --variant CampB (1/2 wins) produce different conditioned lifts."""
        result_a = runner.invoke(
            main,
            [
                "report", "cards", "--archetype", "Dimir Tempo", "--conditioned", "--variant", "CampA",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--db", sign_conflict_db_path,
            ],
        )
        result_b = runner.invoke(
            main,
            [
                "report", "cards", "--archetype", "Dimir Tempo", "--conditioned", "--variant", "CampB",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--db", sign_conflict_db_path,
            ],
        )
        assert result_a.exit_code == 0, result_a.output
        assert result_b.exit_code == 0, result_b.output
        assert "Dimir Tempo [CampA]" in result_a.output
        assert "Dimir Tempo [CampB]" in result_b.output

        # CampA is 2 wins / 0 losses (all-win); CampB is 1 win / 1 loss — the rows must differ.
        row_a = next(line for line in result_a.output.splitlines() if line.strip().startswith("Mishra's Bauble"))
        row_b = next(line for line in result_b.output.splitlines() if line.strip().startswith("Mishra's Bauble"))
        assert row_a != row_b


# ---------------------------------------------------------------------------
# (d) `report subgroup --winrates`
# ---------------------------------------------------------------------------


class TestReportSubgroupWinrates:
    @pytest.fixture
    def camp_db_path(self, tmp_path):
        decks = [
            _deck("bauble_0", [_card("Mishra's Bauble"), _card("Brainstorm")]),
            _deck("bauble_1", [_card("Mishra's Bauble"), _card("Brainstorm")]),
            _deck("bauble_2", [_card("Mishra's Bauble"), _card("Brainstorm")]),
            _deck("nobauble_0", [_card("Barrowgoyf"), _card("Brainstorm")]),
            _deck("nobauble_1", [_card("Barrowgoyf"), _card("Brainstorm")]),
            _deck("nobauble_2", [_card("Barrowgoyf"), _card("Brainstorm")]),
            _deck("opp_0", [_card("Filler")]),
            _deck("opp_1", [_card("Filler")]),
            _deck("opp_2", [_card("Filler")]),
            _deck("opp_3", [_card("Filler")]),
            _deck("opp_4", [_card("Filler")]),
            _deck("opp_5", [_card("Filler")]),
        ]
        rounds = [
            {"Player1": "bauble_0", "Player2": "opp_0", "Result": "2-0"},
            {"Player1": "bauble_1", "Player2": "opp_1", "Result": "2-0"},
            {"Player1": "opp_2", "Player2": "bauble_2", "Result": "2-0"},
            {"Player1": "opp_3", "Player2": "nobauble_0", "Result": "2-0"},
            {"Player1": "opp_4", "Player2": "nobauble_1", "Result": "2-0"},
            {"Player1": "nobauble_2", "Player2": "opp_5", "Result": "2-0"},
        ]
        raw = {
            "Tournament": {
                "Name": "Camp Winrate CLI Test", "Date": "2026-06-01",
                "Uri": "https://test.com/camp-winrate-cli", "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": rounds,
            "Standings": [],
        }
        db_path = tmp_path / "camp_winrate.duckdb"
        con = store.connect(str(db_path))
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Dimir Tempo' WHERE tournament_id = ? "
            "AND player IN ('bauble_0','bauble_1','bauble_2','nobauble_0','nobauble_1','nobauble_2')",
            [tid],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Opponent Pool' WHERE tournament_id = ? "
            "AND player IN ('opp_0','opp_1','opp_2','opp_3','opp_4','opp_5')",
            [tid],
        )
        con.close()
        return str(db_path)

    def test_winrates_flag_renders_win_pct_and_match_n(self, runner, camp_db_path):
        result = runner.invoke(
            main,
            [
                "report", "subgroup",
                "--archetype", "Dimir Tempo", "--signature", "Mishra's Bauble",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--winrates", "--db", camp_db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "with-subgroup win%:    0.667  (matches n=3)" in result.output
        assert "without-subgroup win%: 0.333  (matches n=3)" in result.output

    def test_winrates_flag_renders_thin_note(self, runner, camp_db_path):
        result = runner.invoke(
            main,
            [
                "report", "subgroup",
                "--archetype", "Dimir Tempo", "--signature", "Mishra's Bauble",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--winrates", "--db", camp_db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "thin win-rate sample" in result.output

    def test_without_winrates_flag_no_win_pct_lines(self, runner, camp_db_path):
        result = runner.invoke(
            main,
            [
                "report", "subgroup",
                "--archetype", "Dimir Tempo", "--signature", "Mishra's Bauble",
                "--since", "2026-01-01", "--until", "2027-01-01",
                "--db", camp_db_path,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "win%" not in result.output
