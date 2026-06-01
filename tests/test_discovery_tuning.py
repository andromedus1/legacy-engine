"""Tests for the discovery-tuning layer (epic-gap-discovery-discovery-tuning).

Three layers:
- Pure `_transfer_from_values` over hand-built CardValue + FieldDistribution (gate/weight logic).
- `discover_candidates` over a purpose-built corpus + the role-split / transfer / omission accounting.
- `tune_deck` CardWinRates injection (no-drift) + the `generate tune --discover` CLI wiring.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.analytics.card_value import CardValue
from legacy_engine.cli import main
from legacy_engine.generation.discovery import (
    TRANSFERABLE_ROLES,
    _transfer_from_values,
    discover_candidates,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.models.card import Card

_SINCE, _UNTIL = "2026-01-01", "2026-12-31"


def _cv(opponent: str, lift: float, n: int, tier: str) -> CardValue:
    """Hand-build a CardValue (only opponent/lift/n/tier matter to the transfer logic)."""
    return CardValue(
        card="X", board="main", opponent=opponent,
        p_raw=0.5 + lift, p_shrunk=0.5 + lift, prior_mean=0.5, lift=lift, n=n, tier=tier,
    )


def _field(shares) -> FieldDistribution:
    return FieldDistribution(
        shares=shares, field_source="global",
        counts={k: int(v * 1000) for k, v in shares.items()},
        no_data=frozenset(), warnings=(),
    )


class TestTransferableRoles:
    def test_synergy_engine_roles_excluded(self):
        for r in ("threat", "ritual", "storm", "tutor", "graveyard_recursion", "stax", "fast_mana"):
            assert r not in TRANSFERABLE_ROLES
        for r in ("counter", "removal", "protection", "card_advantage", "discard"):
            assert r in TRANSFERABLE_ROLES


class TestTransferFromValues:
    def test_established_positive_lift_field_weighted(self):
        field = _field({"Combo": 0.4, "Storm": 0.1})
        values = {
            "Combo": _cv("Combo", lift=0.20, n=150, tier="established"),
            "Storm": _cv("Storm", lift=0.10, n=120, tier="established"),
        }
        total, kept = _transfer_from_values(values, field, gate=("established",))
        assert total == pytest.approx(0.4 * 0.20 + 0.1 * 0.10)
        assert set(kept) == {"Combo", "Storm"}

    def test_below_gate_tier_rejected(self):
        field = _field({"Combo": 0.4})
        values = {"Combo": _cv("Combo", lift=0.30, n=20, tier="evolving")}
        total, kept = _transfer_from_values(values, field, gate=("established",))
        assert total == 0.0 and kept == {}

    def test_nonpositive_lift_rejected(self):
        field = _field({"Combo": 0.4})
        values = {"Combo": _cv("Combo", lift=-0.10, n=200, tier="established")}
        total, kept = _transfer_from_values(values, field, gate=("established",))
        assert total == 0.0 and kept == {}

    def test_opponent_absent_from_field_ignored(self):
        field = _field({"Combo": 0.4})
        values = {"Ghost": _cv("Ghost", lift=0.30, n=200, tier="established")}
        total, kept = _transfer_from_values(values, field, gate=("established",))
        assert total == 0.0 and kept == {}


# ---------------------------------------------------------------------------
# Corpus for discover_candidates: UR Tempo whose flex wants {counter, threat}.
# Daze (counter, established lift vs Combo) → surfaces; Zurgo Bellstriker (threat)
# → synergy-omitted; Flusterstorm (counter but thin) → below-gate-omitted.
# ---------------------------------------------------------------------------

_DISCOVERY_CARDS = [
    Card(name="Brainstorm", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Draw three cards, then put two cards from your hand on top of your library."),
    Card(name="Force of Will", type_line="Instant", cmc=5.0, colors=["U"],
         oracle_text="Counter target spell."),
    Card(name="Ponder", type_line="Sorcery", cmc=1.0, colors=["U"],
         oracle_text="Look at the top three cards of your library, then draw a card."),
    Card(name="Spell Pierce", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Counter target noncreature spell unless its controller pays {2}."),
    Card(name="Goblin Guide", type_line="Creature — Goblin Scout", cmc=1.0, colors=["R"],
         power="2", toughness="2", oracle_text="Haste."),
    Card(name="Daze", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Counter target spell unless its controller pays {1}."),
    Card(name="Zurgo Bellstriker", type_line="Creature — Orc Warrior", cmc=1.0, colors=["R"],
         power="2", toughness="2", oracle_text="Dash {1}{R}."),
    Card(name="Flusterstorm", type_line="Instant", cmc=1.0, colors=["U"],
         oracle_text="Counter target instant or sorcery spell unless its controller pays {1}."),
    Card(name="Dark Ritual", type_line="Instant", cmc=1.0, colors=["B"], oracle_text="Add {B}{B}{B}."),
    Card(name="Chalice of the Void", type_line="Artifact", cmc=0.0, colors=[], oracle_text="..."),
]


def _deck(player: str, main: list[str]) -> dict:
    return {"Player": player, "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": n} for n in main], "Sideboard": []}


def _build_discovery_corpus(n_repeats: int = 100):
    con = store.connect(":memory:")
    store.load_cards(con, _DISCOVERY_CARDS)
    for r in range(n_repeats):
        tempo_main = ["Brainstorm", "Force of Will", "Ponder", "Daze", "Zurgo Bellstriker"]
        if r < 10:
            tempo_main.append("Flusterstorm")  # thin: only 10 decks → n<100 vs any opponent
        raw = {
            "Tournament": {"Name": f"T{r}", "Date": "2026-03-15",
                           "Uri": f"https://example.test/disc-{r}", "Formats": "Legacy"},
            "Decks": [
                _deck(f"tempo{r}", tempo_main),
                _deck(f"combo{r}", ["Dark Ritual"]),
                _deck(f"prison{r}", ["Chalice of the Void"]),
            ],
            "Rounds": [
                {"Player1": f"tempo{r}", "Player2": f"combo{r}", "Result": "2-1"},   # Tempo beats Combo
                {"Player1": f"prison{r}", "Player2": f"tempo{r}", "Result": "2-1"},  # Prison beats Tempo
            ],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for arch, prefix in (("Tempo", "tempo"), ("Combo", "combo"), ("Prison", "prison")):
            con.execute(
                "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
                [arch, tid, f"{prefix}{r}"],
            )
    return con


class TestDiscoverCandidates:
    _D_MAIN = {"Brainstorm": 4, "Force of Will": 4, "Ponder": 4, "Spell Pierce": 2, "Goblin Guide": 4}

    def test_transferable_surfaces_synergy_and_thin_omitted(self):
        con = _build_discovery_corpus(100)
        result = discover_candidates(con, "Tempo", self._D_MAIN, since=_SINCE, until=_UNTIL)
        names = [s.name for s in result.suggestions]
        assert "Daze" in names                                  # transferable, established lift>0
        assert "Zurgo Bellstriker" in result.omitted_synergy     # threat role → no honest transfer
        assert result.omitted_below_gate >= 1                    # Flusterstorm: thin (n<100)
        # Daze's transfer kept only the Combo cell (lift>0, established); Prison lift<0 dropped.
        daze = next(s for s in result.suggestions if s.name == "Daze")
        assert set(daze.per_opponent) == {"Combo"}
        assert daze.per_opponent["Combo"].tier == "established"
        assert daze.transferred_value > 0.0
        con.close()

    def test_cap_reports_capped_out(self):
        con = _build_discovery_corpus(100)
        result = discover_candidates(con, "Tempo", self._D_MAIN, cap=0, since=_SINCE, until=_UNTIL)
        assert result.suggestions == []
        assert result.capped_out >= 1
        con.close()

    def test_deterministic(self):
        con = _build_discovery_corpus(100)
        a = discover_candidates(con, "Tempo", self._D_MAIN, since=_SINCE, until=_UNTIL)
        b = discover_candidates(con, "Tempo", self._D_MAIN, since=_SINCE, until=_UNTIL)
        assert [s.name for s in a.suggestions] == [s.name for s in b.suggestions]
        assert a.omitted_synergy == b.omitted_synergy
        con.close()


class TestTuneDeckInjection:
    def test_injected_card_winrates_no_drift(self, make_rounds_corpus):
        from legacy_engine.analytics.match_results import compute_card_winrates
        from legacy_engine.generation.tuning import tune_deck

        con, _ = make_rounds_corpus(n_repeats=50)
        main = {"Brainstorm": 60}
        # Align windows: tune_deck's internal compute uses the passed since/until, so the
        # injected rates must cover the same window to prove no-drift (not a window diff).
        win = {"since": "2025-01-01", "until": "2027-01-01"}
        rates = compute_card_winrates(con, **win)
        plain = tune_deck(con, "Control", dict(main), {}, **win)
        injected = tune_deck(con, "Control", dict(main), {}, card_winrates=rates, **win)
        assert plain.swaps == injected.swaps
        assert plain.maindeck == injected.maindeck
        assert plain.value_after == pytest.approx(injected.value_after)
        con.close()


class TestGenerateTuneDiscoverCLI:
    @pytest.fixture
    def db_path(self, tmp_path, make_rounds_corpus):
        path = tmp_path / "disc.duckdb"
        con_mem, _ = make_rounds_corpus(n_repeats=5)
        con_file = store.connect(str(path))
        store.init_schema(con_file)
        for table in ("tournaments", "decks", "deck_cards", "rounds"):
            rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                ph = ", ".join(["?"] * len(rows[0]))
                con_file.executemany(f"INSERT INTO {table} VALUES ({ph})", rows)
        con_mem.close()
        con_file.close()
        return str(path)

    @pytest.fixture
    def deck_file(self, tmp_path):
        p = tmp_path / "shell.txt"
        p.write_text("4 Brainstorm\n")
        return str(p)

    def test_help_lists_discover_flags(self):
        result = CliRunner().invoke(main, ["generate", "tune", "--help"])
        assert result.exit_code == 0
        assert "--discover" in result.output
        assert "--discover-cap" in result.output

    def test_discover_section_present_with_flag(self, db_path, deck_file):
        result = CliRunner().invoke(
            main, ["generate", "tune", "--deck", deck_file, "--archetype", "Control",
                   "--db", db_path, "--discover"],
        )
        assert result.exit_code == 0, result.output
        assert "=== Discovery (exploratory" in result.output
        assert "disclaimer" in result.output

    def test_no_discover_section_without_flag(self, db_path, deck_file):
        result = CliRunner().invoke(
            main, ["generate", "tune", "--deck", deck_file, "--archetype", "Control", "--db", db_path],
        )
        assert result.exit_code == 0, result.output
        assert "=== Discovery" not in result.output

    def test_flag_does_not_change_swap_log(self, db_path, deck_file):
        """AC: discovery never enters the greedy path — the swap log is identical with/without it."""
        runner = CliRunner()
        base = ["generate", "tune", "--deck", deck_file, "--archetype", "Control", "--db", db_path]

        def swap_log(output: str) -> list[str]:
            lines = output.splitlines()
            start = next(i for i, ln in enumerate(lines) if "Swap log" in ln)
            end = next((i for i, ln in enumerate(lines) if "=== Discovery" in ln), len(lines))
            return [ln for ln in lines[start:end] if ln.startswith("//")]

        without = runner.invoke(main, base)
        with_flag = runner.invoke(main, [*base, "--discover"])
        assert without.exit_code == 0 and with_flag.exit_code == 0
        assert swap_log(without.output) == swap_log(with_flag.output)
