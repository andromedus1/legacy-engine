"""Tests for the config/transform comparator (advisory/compare.py).

Hand-built matrix + field (deterministic). Covers point EV, transform max + chosen_mode, lift
overlay + break-even (ahead / feasible / infeasible), coverage/imputation, and the MC base layer
(seeded determinism, dominating→P≈1, identical→P≈0.5, CI shrinks with n).
"""

from __future__ import annotations

from legacy_engine.advisory.compare import (
    ConfigMode,
    DeckConfig,
    compare_configs,
)
from legacy_engine.advisory.field import build_custom_field
from legacy_engine.analytics.matchup import MatchupMatrix, build_cell


def _matrix(winrates: dict[tuple[str, str], tuple[int, int]]) -> MatchupMatrix:
    """Build a MatchupMatrix from {(a, b): (wins, n)} (directed)."""
    cells = {(a, b): build_cell(a, b, w, n) for (a, b), (w, n) in winrates.items()}
    archs = sorted({a for a, _ in winrates} | {b for _, b in winrates})
    return MatchupMatrix(
        cells=cells, provenance=None,
        total_matches=sum(n for _, n in winrates.values()) // 2,
        archetypes=archs, caveat="test",
    )


# Large n → p_shrunk ≈ p_raw, so point assertions are clean.
N = 1000
WR = {
    ("TempoA", "X"): (600, N), ("TempoA", "Y"): (400, N),
    ("ComboB", "X"): (400, N), ("ComboB", "Y"): (700, N),
}
FIELD = {"X": 0.5, "Y": 0.5}


class TestPointEngine:
    def test_single_mode_ev_matches_field_weighted_pshrunk(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        a = DeckConfig("TempoA", [ConfigMode("TempoA")])
        b = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r = compare_configs(m, f, a, b, n_draws=2000, seed=1)
        assert abs(r.ev_a_base - 0.5) < 0.02     # (0.6 + 0.4)/2
        assert abs(r.ev_b_base - 0.55) < 0.02     # (0.4 + 0.7)/2

    def test_transform_takes_per_matchup_max_and_records_chosen_mode(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        transform = DeckConfig("Transform", [ConfigMode("TempoA"), ConfigMode("ComboB")])
        single = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r = compare_configs(m, f, transform, single, n_draws=2000, seed=1)
        assert abs(r.ev_a_adj - 0.65) < 0.02      # max(.6,.4)=.6 vs X, max(.4,.7)=.7 vs Y
        by_opp = {row.opponent: row for row in r.rows}
        assert by_opp["X"].chosen_mode_a == "TempoA"
        assert by_opp["Y"].chosen_mode_a == "ComboB"

    def test_lift_overlay_raises_adjusted_ev(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        a = DeckConfig("TempoA+hate", [ConfigMode("TempoA", {"Y": 0.30})])  # 0.4 → 0.7 vs Y
        b = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r = compare_configs(m, f, a, b, n_draws=2000, seed=1)
        assert r.ev_a_adj > r.ev_a_base
        assert abs(r.ev_a_adj - 0.65) < 0.02      # (0.6 + 0.7)/2

    def test_lift_clamped_to_one(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        a = DeckConfig("A", [ConfigMode("TempoA", {"X": 0.95})])  # 0.6 + 0.95 → clamp 1.0
        b = DeckConfig("B", [ConfigMode("ComboB")])
        r = compare_configs(m, f, a, b, n_draws=1000, seed=1)
        wr_x = next(row.wr_a_adj for row in r.rows if row.opponent == "X")
        assert wr_x == 1.0


class TestBreakEven:
    def test_breakeven_lift_for_parity(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        # A base EV ≈ 0.50; B ≈ 0.55. Declare a (zero) lift on Y so Y is the target matchup.
        a = DeckConfig("TempoA", [ConfigMode("TempoA", {"Y": 0.0})])
        b = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r = compare_configs(m, f, a, b, n_draws=2000, seed=1)
        # L* = (ev_b_adj − ev_a_base) / target_share ≈ (0.55 − 0.50) / 0.5 ≈ 0.10
        assert r.breakeven_lift is not None
        assert abs(r.breakeven_lift - 0.10) < 0.02
        assert r.breakeven_targets == ["Y"]
        assert r.breakeven_feasible is True

    def test_breakeven_none_when_a_already_ahead(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        a = DeckConfig("ComboB", [ConfigMode("ComboB", {"X": 0.0})])  # EV ≈ 0.55
        b = DeckConfig("TempoA", [ConfigMode("TempoA")])              # EV ≈ 0.50
        r = compare_configs(m, f, a, b, n_draws=1000, seed=1)
        assert r.breakeven_lift is None

    def test_breakeven_infeasible_flagged(self):
        # A far behind, single thin-share target → required L* pushes the target past 1.0.
        m = _matrix({("Lo", "X"): (10, N), ("Lo", "Y"): (10, N),
                     ("Hi", "X"): (900, N), ("Hi", "Y"): (900, N)})
        f = build_custom_field({"X": 0.9, "Y": 0.1})
        a = DeckConfig("Lo", [ConfigMode("Lo", {"Y": 0.0})])   # target = Y (share 0.1)
        b = DeckConfig("Hi", [ConfigMode("Hi")])               # EV ≈ 0.9
        r = compare_configs(m, f, a, b, n_draws=1000, seed=1)
        assert r.breakeven_lift is not None
        assert r.breakeven_feasible is False                   # +L on Y alone can't close an ~0.8 gap


class TestCoverage:
    def test_imputed_opponent_excluded_from_coverage(self):
        # No cell for TempoA vs Z → imputed; Z share drops out of coverage.
        m = _matrix(WR)
        f = build_custom_field({"X": 0.4, "Y": 0.4, "Z": 0.2})
        a = DeckConfig("TempoA", [ConfigMode("TempoA")])
        b = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r = compare_configs(m, f, a, b, n_draws=1000, seed=1)
        assert abs(r.coverage_a - 0.8) < 1e-9                  # X + Y measured; Z imputed
        z = next(row for row in r.rows if row.opponent == "Z")
        assert z.imputed_a is True


class TestMonteCarlo:
    def test_deterministic_given_seed(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        a = DeckConfig("TempoA", [ConfigMode("TempoA")])
        b = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r1 = compare_configs(m, f, a, b, n_draws=3000, seed=42)
        r2 = compare_configs(m, f, a, b, n_draws=3000, seed=42)
        assert r1.p_a_beats_b_base == r2.p_a_beats_b_base
        assert r1.ev_a_base_ci == r2.ev_a_base_ci

    def test_dominating_config_p_near_one(self):
        m = _matrix({("Hi", "X"): (900, N), ("Hi", "Y"): (900, N),
                     ("Lo", "X"): (100, N), ("Lo", "Y"): (100, N)})
        f = build_custom_field(FIELD)
        hi = DeckConfig("Hi", [ConfigMode("Hi")])
        lo = DeckConfig("Lo", [ConfigMode("Lo")])
        r = compare_configs(m, f, hi, lo, n_draws=4000, seed=7)
        assert r.p_a_beats_b_base > 0.99

    def test_identical_configs_p_half(self):
        m = _matrix(WR)
        f = build_custom_field(FIELD)
        a = DeckConfig("A", [ConfigMode("TempoA")])
        b = DeckConfig("B", [ConfigMode("TempoA")])  # same archetype → shared draws → all ties
        r = compare_configs(m, f, a, b, n_draws=4000, seed=7)
        assert abs(r.p_a_beats_b_base - 0.5) < 1e-9

    def test_ci_shrinks_with_sample_size(self):
        thin = _matrix({("TempoA", "X"): (12, 20), ("TempoA", "Y"): (8, 20),
                        ("ComboB", "X"): (8, 20), ("ComboB", "Y"): (14, 20)})
        thick = _matrix({("TempoA", "X"): (1200, 2000), ("TempoA", "Y"): (800, 2000),
                         ("ComboB", "X"): (800, 2000), ("ComboB", "Y"): (1400, 2000)})
        f = build_custom_field(FIELD)
        a = DeckConfig("TempoA", [ConfigMode("TempoA")])
        b = DeckConfig("ComboB", [ConfigMode("ComboB")])
        r_thin = compare_configs(thin, f, a, b, n_draws=4000, seed=3)
        r_thick = compare_configs(thick, f, a, b, n_draws=4000, seed=3)
        width = lambda ci: ci[1] - ci[0]
        assert width(r_thin.ev_a_base_ci) > width(r_thick.ev_a_base_ci)


class TestSlotLift:
    def test_slot_lift_returns_diff_and_none(self):
        import duckdb
        from legacy_engine.advisory.compare import slot_lift
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.cache import parse_cache_item

        con = store.connect(":memory:")
        raw = {
            "Tournament": {"Name": "t", "Date": "2026-03-01",
                           "Uri": "https://www.mtgo.com/decklist/slot-lift-1", "Formats": "Legacy"},
            "Decks": [
                {"Player": "hw", "Result": "1st",
                 "Mainboard": [{"Count": 1, "CardName": "Bolt"}],
                 "Sideboard": [{"Count": 1, "CardName": "Tech"}]},
                {"Player": "hp", "Result": "2nd",
                 "Mainboard": [{"Count": 1, "CardName": "Bolt"}], "Sideboard": []},
                {"Player": "f1", "Result": "3rd",
                 "Mainboard": [{"Count": 1, "CardName": "Rock"}], "Sideboard": []},
                {"Player": "f2", "Result": "4th",
                 "Mainboard": [{"Count": 1, "CardName": "Rock"}], "Sideboard": []},
            ],
            "Rounds": [
                {"Player1": "hw", "Player2": "f1", "Result": "2-0"},   # WITH wins
                {"Player1": "hp", "Player2": "f2", "Result": "0-2"},   # WITHOUT loses
            ],
            "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        for p, arch in {"hw": "Tempo", "hp": "Tempo", "f1": "Foe", "f2": "Foe"}.items():
            con.execute("UPDATE decks SET archetype=? WHERE tournament_id=? AND player=?", [arch, tid, p])

        # WITH wins (1/1), WITHOUT loses (0/1) → diff = +1.0
        assert slot_lift(con, "Tempo", "Tech", "Foe") == 1.0
        # A card no Tempo deck runs → empty WITH cohort → no diff → None
        assert slot_lift(con, "Tempo", "Ghost", "Foe") is None
        con.close()
