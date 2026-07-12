"""Tests for adaptive regime-aware advisory v2 — affectedness + adaptive matrix + mode wiring.

Builds a two-regime corpus straddling the Entomb ban (2025-11-10): an "Reanimator" archetype runs
Entomb in the pre-ban window (→ affected, valid_since 2025-11-10); "Control" never does (→ None).
Matches exist in BOTH the pre-ban (2025-06-01) and post-ban (2026-01-01) windows, so the adaptive
Reanimator-vs-Control cell (windowed to post-ban) has strictly fewer matches than the full-corpus cell.
"""

from __future__ import annotations

from legacy_engine.analytics import matchup as matchup_mod
from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.matchup import build_adaptive_matrix, build_matrix
from legacy_engine.advisory.window import resolve_advisory_window
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


def _deck(player: str, main: list[str]) -> dict:
    return {"Player": player, "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": n} for n in main], "Sideboard": []}


def _tournament(name: str, date: str, decks: list[dict], rounds: list[dict]) -> dict:
    return {
        "Tournament": {"Name": name, "Date": date, "Uri": f"https://example.test/{name}",
                       "Formats": "Legacy"},
        "Decks": decks, "Rounds": rounds, "Standings": [],
    }


def _build_two_regime_corpus(pre_n: int = 10, post_n: int = 10):
    """Reanimator (runs Entomb pre-ban) vs Control, with matches in both regimes."""
    con = store.connect(":memory:")

    def load(name, date, idx, reanimator_main):
        decks = [_deck(f"rean{idx}", reanimator_main), _deck(f"ctrl{idx}", ["Brainstorm", "Swords to Plowshares"])]
        rounds = [{"Player1": f"rean{idx}", "Player2": f"ctrl{idx}", "Result": "2-1"}]  # Reanimator beats Control
        tid = store.load_tournament(con, parse_cache_item(_tournament(name, date, decks, rounds), "MTGO"))
        con.execute("UPDATE decks SET archetype='Reanimator' WHERE tournament_id=? AND player=?", [tid, f"rean{idx}"])
        con.execute("UPDATE decks SET archetype='Control' WHERE tournament_id=? AND player=?", [tid, f"ctrl{idx}"])

    idx = 0
    for _ in range(pre_n):   # pre-ban: Reanimator runs Entomb (the to-be-banned card)
        load(f"pre{idx}", "2025-06-01", idx, ["Entomb", "Reanimate", "Griselbrand"])
        idx += 1
    for _ in range(post_n):  # post-ban: Reanimator no longer runs Entomb
        load(f"post{idx}", "2026-01-01", idx, ["Reanimate", "Griselbrand", "Archon of Cruelty"])
        idx += 1
    return con


class TestArchetypeValidSince:
    def test_entomb_runner_affected_others_not(self):
        con = _build_two_regime_corpus()
        vs = archetype_valid_since(con, ["Reanimator", "Control"])
        assert vs["Reanimator"] == "2025-11-10"   # Entomb banned 2025-11-10; ran it pre-ban
        assert vs["Control"] is None              # never ran a banned card
        con.close()

    def test_threshold_below_floor_not_affected(self):
        con = store.connect(":memory:")
        # 10 Reanimator decks, only 1 runs Entomb (10% < 25% threshold) → not affected.
        for i in range(10):
            main = ["Entomb", "Reanimate"] if i == 0 else ["Reanimate", "Griselbrand"]
            decks = [_deck(f"r{i}", main)]
            tid = store.load_tournament(con, parse_cache_item(_tournament(f"t{i}", "2025-06-01", decks, []), "MTGO"))
            con.execute("UPDATE decks SET archetype='Reanimator' WHERE tournament_id=?", [tid])
        vs = archetype_valid_since(con, ["Reanimator"])
        assert vs["Reanimator"] is None
        con.close()


class TestBuildAdaptiveMatrix:
    def test_affected_cell_windows_to_post_ban(self):
        con = _build_two_regime_corpus(pre_n=10, post_n=10)
        adaptive = build_adaptive_matrix(con, min_row_share=0.0)
        assert adaptive.valid_since["Reanimator"] == "2025-11-10"
        assert adaptive.valid_since["Control"] is None
        # Cell touching the affected archetype is windowed to [2025-11-10, …) → post-ban only.
        assert adaptive.cell_windows[("Reanimator", "Control")] == "2025-11-10"
        full = build_matrix(con, min_row_share=0.0)
        adaptive_n = adaptive.matrix.cells[("Reanimator", "Control")].n
        full_n = full.cells[("Reanimator", "Control")].n
        assert 0 < adaptive_n < full_n   # post-ban subset, strictly fewer matches
        assert adaptive.matrix.archetypes == full.archetypes  # stable full-corpus row inclusion
        con.close()

    def test_scan_count_bounded_by_distinct_valid_since(self, monkeypatch):
        con = _build_two_regime_corpus()
        calls = {"n": 0}
        real = matchup_mod.compute_match_results

        def counting(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        monkeypatch.setattr(matchup_mod, "compute_match_results", counting)
        build_adaptive_matrix(con, min_row_share=0.0)
        # distinct valid_since = {None (Control), 2025-11-10 (Reanimator)} → 1 full scan + 1 boundary scan.
        assert calls["n"] == 2
        con.close()


class TestEraAwareDefaultFallback:
    """epic-stable-era-windows-consumption Unit 2: with no `entity_eras` table at all, the new
    default era-aware path (`era_horizons`) must produce a BYTE-IDENTICAL matrix to the pre-epic
    `archetype_valid_since`-only path — proven by computing both paths on the same corpus and
    comparing full cell dicts, not by comparing a dict to itself."""

    def test_byte_identical_fallback_no_eras_table(self):
        from legacy_engine.analytics.affectedness import archetype_valid_since

        con = _build_two_regime_corpus(pre_n=10, post_n=10)

        # "Old path": horizons computed exactly as the pre-epic implementation did internally
        # (archetype_valid_since over the included archetypes), passed in explicitly so the
        # matrix builder bypasses era_horizons entirely.
        old_horizons = archetype_valid_since(con, ["Control", "Reanimator"])
        old = build_adaptive_matrix(con, min_row_share=0.0, horizons=old_horizons)

        # "New path": the default (no `horizons` kwarg) on a connection with NO `entity_eras`
        # table at all -> era_horizons degrades every entity to "ban-only", which internally
        # calls the very same archetype_valid_since with the same arguments.
        new = build_adaptive_matrix(con, min_row_share=0.0)

        assert new.valid_since == old.valid_since
        assert new.cell_windows == old.cell_windows
        assert new.matrix.cells == old.matrix.cells
        assert new.matrix.archetypes == old.matrix.archetypes
        assert new.matrix.total_matches == old.matrix.total_matches
        assert new.matrix.provenance == old.matrix.provenance
        # Confirm horizon_meta was genuinely populated via era_horizons (not silently skipped) —
        # every entity resolved through the whole-path ban-only degrade.
        assert new.horizon_meta and all(h.source == "ban-only" for h in new.horizon_meta.values())
        con.close()

    def test_explicit_horizons_bypass_era_horizons_and_report_no_meta(self):
        con = _build_two_regime_corpus(pre_n=5, post_n=5)
        adaptive = build_adaptive_matrix(
            con, min_row_share=0.0,
            horizons={"Reanimator": "2025-11-10", "Control": None},
        )
        assert adaptive.horizon_meta == {}
        assert adaptive.valid_since == {"Reanimator": "2025-11-10", "Control": None}
        con.close()

    def test_default_path_resolves_via_persisted_era_when_present(self):
        """A seeded entity_eras row changes valid_since relative to the ban-only fallback,
        proving the default path actually consults the store (not just always falling through)."""
        from legacy_engine.analytics.eras.ensemble import EntityEras
        from legacy_engine.analytics.eras.store import write_entity_eras

        con = _build_two_regime_corpus(pre_n=5, post_n=5)
        eras = {
            "Control": EntityEras(entity="Control", stable_since="2025-08-01", boundaries=(), inherited_from_parent=False),
        }
        write_entity_eras(
            con, eras, {}, {},
            run_meta={
                "provenance": None, "alpha": 0.05, "run_at": "2026-07-11T00:00:00+00:00",
                "post_boundary_decks": {}, "parent": {"Control": "Control"},
            },
        )
        adaptive = build_adaptive_matrix(con, min_row_share=0.0)
        assert adaptive.valid_since["Control"] == "2025-08-01"
        assert adaptive.horizon_meta["Control"].source == "era"
        # Reanimator has no entity_eras row -> still ban-only fallback for that entity alone.
        assert adaptive.horizon_meta["Reanimator"].source == "ban-only"
        con.close()


class TestWindowMode:
    def test_default_is_adaptive(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        assert resolve_advisory_window(con).mode == "adaptive"
        con.close()

    def test_all_time_is_full(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        assert resolve_advisory_window(con, all_time=True).mode == "full"
        con.close()

    def test_regime_is_uniform(self, make_rounds_corpus):
        con, _ = make_rounds_corpus(n_repeats=1)
        res = resolve_advisory_window(con, since="2025-01-01", until="2026-01-01", thin_floor=0)
        assert res.mode == "uniform"
        con.close()


class TestArchetypeValidSincePooling:
    """Assert that archetype_valid_since + max() logic correctly resolves per-sideboard windows."""

    def test_max_of_two_valid_since_values(self):
        """When deck_arch has valid_since A and opponent has valid_since B,
        the correct sideboard window is max(A, B) — the later date wins."""
        con = _build_two_regime_corpus(pre_n=5, post_n=5)
        vs = archetype_valid_since(con, ["Reanimator", "Control"])

        # Reanimator affected by Entomb ban (2025-11-10); Control unaffected (None).
        arch_vs = vs["Reanimator"]   # 2025-11-10
        opp_vs = vs["Control"]       # None

        # The sideboard pools to max(arch_vs, opp_vs): None means full-history,
        # so max(2025-11-10, None) = 2025-11-10 (the non-None date wins).
        both = [s for s in (arch_vs, opp_vs) if s is not None]
        pooled = max(both) if both else None

        assert arch_vs == "2025-11-10"
        assert opp_vs is None
        assert pooled == "2025-11-10", (
            f"max(valid_since[deck], valid_since[opp]) should be 2025-11-10 "
            f"(the non-None date); got {pooled!r}"
        )
        con.close()

    def test_both_none_means_full_corpus(self):
        """When both deck_arch and opponent have valid_since=None, pooled window is full corpus."""
        con = _build_two_regime_corpus(pre_n=5, post_n=5)
        vs = archetype_valid_since(con, ["Control"])

        # Control is not affected by any ban.
        deck_vs = vs["Control"]   # None
        opp_vs = None             # hypothetical unaffected opponent

        both = [s for s in (deck_vs, opp_vs) if s is not None]
        pooled = max(both) if both else None

        assert pooled is None, (
            f"Both None → full corpus (pooled=None); got {pooled!r}"
        )
        con.close()
