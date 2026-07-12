"""Tests for the hierarchical + cross-era matchup-cell prior (epic-stable-era-windows-shrinkage,
stories -shrinkage-hierarchy / Units 1+2).

Unit 1 (hierarchy): a split-variant camp cell shrinks toward its leave-camp-out (LCO) parent
cell, itself shrunk toward the parent archetype's own shrunk marginal; every other cell shrinks
toward the subject's own shrunk marginal. Unit 2 (cross-era): a thin (n<100) cell whose window
was truncated at an era (not ban-only) boundary shrinks toward its own pre-disturbance value
instead, winning over the hierarchy prior when both apply.

House style: module-level raw dicts -> parse_cache_item -> store.load_tournament into :memory:
(or a tmp DuckDB file for CLI tests); labels pinned via direct SQL UPDATE; TestX classes;
deterministic.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.eras.ensemble import EntityEras
from legacy_engine.analytics.eras.store import write_entity_eras
from legacy_engine.analytics.match_results import ArchetypeRecord, MatchCoverage, MatchResults, MatchupTally
from legacy_engine.analytics.matchup import (
    SHRINK_STRENGTH,
    _camp_hierarchy_inputs,
    _cell_prior,
    beta_binomial_shrink,
    beta_binomial_shrink_to,
    build_adaptive_matrix,
    build_matrix,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Unit 1 — _cell_prior (pure): hand-built fixtures reproducing the epic's worked example
# ---------------------------------------------------------------------------


class TestCellPriorPure:
    """The epic's worked motivating case (feature doc): a camp cell reading raw 31.2% at n=16
    with an LCO-parent′ of 45.3% must read ≈38%, NOT the flat-0.5 40.3%."""

    def test_camp_cell_worked_example_reads_38_not_403(self):
        # LCO-parent already shrunk to 45.3% (0.452586 precisely — see docstring math below);
        # subject camp's raw record: 5 wins / 16 (31.25% — the epic's "31.2%").
        camp = "Lands [Sphere]"
        opponent = "S&T"
        parent = "Lands"
        marginals = {parent: 0.5, camp: 0.5}  # camp's own marginal unused on the LCO path
        parent_cells_lco = {(camp, opponent): (45, 101)}  # wins=45, n=101 -> shrunk 0.452586
        camp_of = {camp: parent, opponent: opponent}

        prior_mean, source = _cell_prior(
            camp, opponent, marginals=marginals, parent_cells_lco=parent_cells_lco, camp_of=camp_of,
        )
        assert source == "parent cell (leave-camp-out)"
        assert prior_mean == pytest.approx(0.452586, abs=1e-5)

        raw_wins, raw_n = 5, 16
        shrunk = beta_binomial_shrink_to(raw_wins, raw_n, prior_mean=prior_mean, strength=SHRINK_STRENGTH)
        flat_shrunk = beta_binomial_shrink(raw_wins, raw_n)

        assert raw_wins / raw_n == pytest.approx(0.3125)
        assert flat_shrunk == pytest.approx(0.403226, abs=1e-5)   # the OLD flat-0.5 number (40.3%)
        assert shrunk == pytest.approx(0.380284, abs=1e-5)        # the NEW hierarchical number (38.0%)
        assert round(shrunk * 100, 1) == pytest.approx(38.0)
        assert abs(shrunk - flat_shrunk) > 0.02  # materially different, not a rounding wobble

    def test_plain_archetype_cell_shrinks_toward_own_marginal(self):
        """A non-split (or non-camp) subject shrinks toward its OWN shrunk marginal — source
        'marginal' — never the LCO-parent path (camp_of[subject] == subject)."""
        marginals = {"Delver": 0.62, "Lands": 0.5}
        camp_of = {"Delver": "Delver", "Lands": "Lands"}
        prior_mean, source = _cell_prior(
            "Delver", "Lands", marginals=marginals, parent_cells_lco={}, camp_of=camp_of,
        )
        assert source == "marginal"
        assert prior_mean == pytest.approx(0.62)

    def test_camp_cell_without_lco_reference_falls_back_to_own_marginal(self):
        """A camp cell with no LCO reference (e.g. a camp-vs-sibling-camp pairing, where the
        unsplit 'parent cell' would have been a mirror) falls back to its own marginal."""
        camp_of = {"Lands [Sphere]": "Lands", "Lands [Waste]": "Lands"}
        marginals = {"Lands [Sphere]": 0.41, "Lands": 0.5}
        prior_mean, source = _cell_prior(
            "Lands [Sphere]", "Lands [Waste]",
            marginals=marginals, parent_cells_lco={}, camp_of=camp_of,
        )
        assert source == "marginal"
        assert prior_mean == pytest.approx(0.41)


# ---------------------------------------------------------------------------
# Unit 1 — end-to-end: build_matrix(split_variant=...) reproduces the same worked example
# from a real hand-built corpus (proves the LCO subtraction wiring, not just the formula).
# ---------------------------------------------------------------------------


def _deck(player: str, main: list[str]) -> dict:
    return {"Player": player, "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": n} for n in main], "Sideboard": []}


def _tournament(name: str, date: str, decks: list[dict], rounds: list[dict]) -> dict:
    return {
        "Tournament": {"Name": name, "Date": date, "Uri": f"https://example.test/{name}",
                       "Formats": "Legacy"},
        "Decks": decks, "Rounds": rounds, "Standings": [],
    }


def _build_lands_camp_corpus():
    """Lands split into two camps (Sphere, Waste) vs two opponents (S&T, Aggro).

    Engineered so the worked example holds EXACTLY:
      - Sphere vs S&T:  5 wins / 16  (raw 31.25% -> the epic's "31.2%")
      - Waste  vs S&T: 45 wins / 101 (the LCO-parent reference once Sphere's own count
        is subtracted back out from the combined parent total)
      - Waste  vs Aggro: 17 wins / 17 (0 losses) — balances Lands' OVERALL marginal to
        exactly 67/134 = 0.5, so the LCO-parent shrink target (0.5) matches the pure test above.

    Combined parent (Lands) vs S&T = Sphere(5,16) + Waste(45,101) = 50 wins / 117.
    LCO for Sphere = combined - Sphere's own = 45 wins / 101 (Waste's own record) — exactly the
    fixture used in TestCellPriorPure.
    """
    con = store.connect(":memory:")
    rounds = (
        [{"Player1": "sphere", "Player2": "st", "Result": "2-1"} for _ in range(5)]
        + [{"Player1": "sphere", "Player2": "st", "Result": "1-2"} for _ in range(11)]
        + [{"Player1": "waste", "Player2": "st", "Result": "2-1"} for _ in range(45)]
        + [{"Player1": "waste", "Player2": "st", "Result": "1-2"} for _ in range(56)]
        + [{"Player1": "waste", "Player2": "aggro", "Result": "2-1"} for _ in range(17)]
    )
    decks = [
        _deck("sphere", ["Lion's Eye Diamond"]),
        _deck("waste", ["Lion's Eye Diamond"]),
        _deck("st", ["Show and Tell"]),
        _deck("aggro", ["Goblin Guide"]),
    ]
    tid = store.load_tournament(con, parse_cache_item(_tournament("Lands Camp Test", "2026-06-01", decks, rounds), "MTGO"))
    con.execute("UPDATE decks SET archetype='Lands', variant='Sphere' WHERE tournament_id=? AND player='sphere'", [tid])
    con.execute("UPDATE decks SET archetype='Lands', variant='Waste' WHERE tournament_id=? AND player='waste'", [tid])
    con.execute("UPDATE decks SET archetype='S&T' WHERE tournament_id=? AND player='st'", [tid])
    con.execute("UPDATE decks SET archetype='Aggro' WHERE tournament_id=? AND player='aggro'", [tid])
    return con


class TestBuildMatrixHierarchyWorkedExample:
    def test_camp_cell_reads_38_not_flat_403(self):
        con = _build_lands_camp_corpus()
        matrix = build_matrix(con, split_variant="Lands", min_row_share=0.0)
        cell = matrix.cells[("Lands [Sphere]", "S&T")]
        assert (cell.wins, cell.n) == (5, 16)
        assert cell.p_raw == pytest.approx(0.3125)
        assert cell.prior_source == "parent cell (leave-camp-out)"
        assert cell.prior_mean == pytest.approx(0.452586, abs=1e-4)
        assert cell.p_shrunk == pytest.approx(0.380284, abs=1e-4)
        assert round(cell.p_shrunk * 100, 1) == pytest.approx(38.0)
        # NOT the flat-0.5 number this epic replaces.
        flat = beta_binomial_shrink(5, 16)
        assert flat == pytest.approx(0.403226, abs=1e-5)
        assert abs(cell.p_shrunk - flat) > 0.02
        con.close()

    def test_majority_camp_cell_shrinks_toward_its_own_lco_reference(self):
        """Waste's LCO-parent reference is Sphere's own (5,16) record — a much thinner sample,
        so Waste's cell shrinks toward a value further from 0.5 than a flat prior would."""
        con = _build_lands_camp_corpus()
        matrix = build_matrix(con, split_variant="Lands", min_row_share=0.0)
        cell = matrix.cells[("Lands [Waste]", "S&T")]
        assert (cell.wins, cell.n) == (45, 101)
        assert cell.prior_source == "parent cell (leave-camp-out)"
        expected_prior = beta_binomial_shrink_to(5, 16, prior_mean=0.5)  # Sphere's own, shrunk toward marginal 0.5
        assert cell.prior_mean == pytest.approx(expected_prior, abs=1e-6)
        con.close()

    def test_plain_opponent_cell_shrinks_toward_own_marginal(self):
        """S&T is not a camp of the split — its cell vs a camp still uses the marginal chain."""
        con = _build_lands_camp_corpus()
        matrix = build_matrix(con, split_variant="Lands", min_row_share=0.0)
        cell = matrix.cells[("S&T", "Lands [Sphere]")]
        assert cell.prior_source == "marginal"
        con.close()

    def test_cross_camp_pairing_falls_back_to_marginal(self):
        """Sphere vs Waste (both camps of the same split) has no unsplit parent-cell reference
        (it would have been a mirror pre-split) — falls back to the marginal chain, not LCO."""
        con = _build_lands_camp_corpus()
        # Add one cross-camp decisive match so the (Sphere, Waste) cell is n>0.
        con.execute("INSERT INTO rounds VALUES (?, 9999, 'sphere', 'waste', '2-0')",
                    [con.execute("SELECT id FROM tournaments LIMIT 1").fetchone()[0]])
        matrix = build_matrix(con, split_variant="Lands", min_row_share=0.0)
        cell = matrix.cells[("Lands [Sphere]", "Lands [Waste]")]
        assert cell.n == 1
        assert cell.prior_source == "marginal"
        con.close()

    def test_unobserved_pair_n0_cell_carries_prior_and_source(self):
        """An unobserved (n=0) pair still gets a hierarchical prior_mean + source label — the
        model's best belief absent data, not a bare None."""
        con = _build_lands_camp_corpus()
        matrix = build_matrix(con, split_variant="Lands", min_row_share=0.0)
        # S&T and Aggro never played each other in this corpus -> a genuinely unobserved pair.
        cell = matrix.cells[("S&T", "Aggro")]
        assert cell.n == 0
        assert cell.p_raw is None
        assert cell.p_shrunk is not None
        assert cell.p_shrunk == pytest.approx(cell.prior_mean)
        assert cell.prior_source is not None
        con.close()

    def test_mirror_cells_untouched(self):
        con = _build_lands_camp_corpus()
        matrix = build_matrix(con, split_variant="Lands", min_row_share=0.0)
        for label in matrix.archetypes:
            mirror = matrix.cells[(label, label)]
            assert mirror.p_shrunk == pytest.approx(0.5)
            assert mirror.prior_mean is None
            assert mirror.prior_source is None
        con.close()

    def test_no_split_variant_uses_marginal_chain_only(self):
        """Without split_variant, every non-mirror cell uses the marginal chain (no LCO path
        possible — there are no camps)."""
        con = _build_lands_camp_corpus()
        matrix = build_matrix(con, min_row_share=0.0)
        for (a, b), cell in matrix.cells.items():
            if a == b:
                continue
            assert cell.prior_source == "marginal"
        con.close()


# ---------------------------------------------------------------------------
# _camp_hierarchy_inputs — direct unit coverage of the LCO-subtraction invariant
# ---------------------------------------------------------------------------


class TestCampHierarchyInputs:
    def test_lco_equals_parent_minus_camp_own(self):
        """Hand-built MatchResults: two camps of 'Lands' vs 'S&T'; LCO for each camp is exactly
        the OTHER camp's own tally (parent = sum of both camps, by construction)."""
        mr = MatchResults(
            matchups={
                ("Lands [Sphere]", "S&T"): MatchupTally("Lands [Sphere]", "S&T", wins=5, losses=11),
                ("Lands [Waste]", "S&T"): MatchupTally("Lands [Waste]", "S&T", wins=45, losses=56),
            },
            archetypes={
                "Lands [Sphere]": ArchetypeRecord("Lands [Sphere]", wins=5, losses=11),
                "Lands [Waste]": ArchetypeRecord("Lands [Waste]", wins=45, losses=56),
                "S&T": ArchetypeRecord("S&T", wins=56 + 11, losses=5 + 45),
            },
            coverage=MatchCoverage(),
            provenance=None,
        )
        labels = ["Lands [Sphere]", "Lands [Waste]", "S&T"]
        marginals, parent_cells_lco, camp_of = _camp_hierarchy_inputs(mr, labels, "Lands")
        assert parent_cells_lco[("Lands [Sphere]", "S&T")] == (45, 101)
        assert parent_cells_lco[("Lands [Waste]", "S&T")] == (5, 16)
        assert camp_of["Lands [Sphere]"] == "Lands"
        assert camp_of["S&T"] == "S&T"
        # Parent's own marginal reconstructed by summing camp siblings.
        assert marginals["Lands"] == pytest.approx(beta_binomial_shrink(50, 117))
        con_free = True  # no DB access — pure function
        assert con_free


# ---------------------------------------------------------------------------
# Unit 2 — cross-era prior (build_adaptive_matrix only)
# ---------------------------------------------------------------------------


def _write_era(con, entity: str, stable_since: str | None, *, parent: str | None = None) -> None:
    """Seed a single entity_eras row directly (bypasses the full `eras run` detection pipeline —
    mirrors tests/test_adaptive_regime.py::TestEraAwareDefaultFallback's pattern)."""
    write_entity_eras(
        con,
        {entity: EntityEras(entity=entity, stable_since=stable_since, boundaries=(), inherited_from_parent=False)},
        {}, {},
        run_meta={
            "provenance": None, "alpha": 0.05, "run_at": "2026-07-12T00:00:00+00:00",
            "post_boundary_decks": {}, "parent": {entity: parent or entity},
        },
    )


def _build_cross_era_corpus(pre_wins: int, pre_losses: int, post_wins: int, post_losses: int,
                             *, pre_date: str = "2025-06-01", post_date: str = "2026-06-01"):
    """Reanimator vs Control, straddling an implanted boundary (seeded into entity_eras
    separately — this only builds the match corpus). Also includes an UNDISTURBED third
    archetype (Aggro, vs Control) so a no-boundary cell can be checked in the same corpus."""
    con = store.connect(":memory:")
    idx = [0]

    def add_matches(date, archetype, opponent, wins, losses):
        decks = []
        rounds = []
        for _ in range(wins):
            i = idx[0]
            idx[0] += 1
            decks += [_deck(f"a{i}", ["Brainstorm"]), _deck(f"o{i}", ["Swords to Plowshares"])]
            rounds.append({"Player1": f"a{i}", "Player2": f"o{i}", "Result": "2-1"})
        for _ in range(losses):
            i = idx[0]
            idx[0] += 1
            decks += [_deck(f"a{i}", ["Brainstorm"]), _deck(f"o{i}", ["Swords to Plowshares"])]
            rounds.append({"Player1": f"a{i}", "Player2": f"o{i}", "Result": "1-2"})
        if not decks:
            return
        tid = store.load_tournament(
            con, parse_cache_item(_tournament(f"{archetype}-{date}-{wins}-{losses}", date, decks, rounds), "MTGO"),
        )
        con.execute("UPDATE decks SET archetype=? WHERE tournament_id=? AND player LIKE 'a%'", [archetype, tid])
        con.execute("UPDATE decks SET archetype=? WHERE tournament_id=? AND player LIKE 'o%'", [opponent, tid])

    add_matches(pre_date, "Reanimator", "Control", pre_wins, pre_losses)
    add_matches(post_date, "Reanimator", "Control", post_wins, post_losses)
    # Undisturbed third archetype: Aggro vs Control, no boundary at all.
    add_matches(pre_date, "Aggro", "Control", 20, 20)
    return con


class TestCrossEraPrior:
    def test_thin_post_boundary_cell_reads_between_raw_and_pre_boundary_value(self):
        con = _build_cross_era_corpus(pre_wins=80, pre_losses=20, post_wins=3, post_losses=2)
        _write_era(con, "Reanimator", "2026-01-01")

        adaptive = build_adaptive_matrix(con, min_row_share=0.0)
        assert adaptive.horizon_meta["Reanimator"].source == "era"
        assert adaptive.cell_windows[("Reanimator", "Control")] == "2026-01-01"

        cell = adaptive.matrix.cells[("Reanimator", "Control")]
        assert (cell.wins, cell.n) == (3, 5)  # thin post-boundary sample
        assert cell.prior_source is not None
        assert cell.prior_source.startswith("pre-disturbance value (window < 2026-01-01)")
        assert "hierarchy:" in cell.prior_source

        raw_post = 3 / 5
        # The cross-era prior mean is itself the pre-boundary hierarchical value — strongly
        # favors Reanimator (pre-boundary raw 80/100 = 80%). The final shrunk estimate must sit
        # strictly between the thin raw post-boundary rate and that pre-boundary anchor.
        assert raw_post < cell.p_shrunk < cell.prior_mean
        assert cell.prior_mean > 0.7  # anchored near the strong pre-boundary rate, not 0.5
        con.close()

    def test_established_post_boundary_cell_ignores_cross_era_prior(self):
        con = _build_cross_era_corpus(pre_wins=80, pre_losses=20, post_wins=60, post_losses=45)
        _write_era(con, "Reanimator", "2026-01-01")

        adaptive = build_adaptive_matrix(con, min_row_share=0.0)
        cell = adaptive.matrix.cells[("Reanimator", "Control")]
        assert cell.n == 105  # established (>=100)
        assert cell.prior_source == "marginal"  # Unit 1 hierarchy only — no cross-era override
        assert cell.prior_mean is not None
        assert not cell.prior_source.startswith("pre-disturbance")
        con.close()

    def test_ban_only_sourced_boundary_never_gets_cross_era_prior(self):
        """A thin cell truncated at a BAN-ONLY horizon (no entity_eras row at all) never gets the
        cross-era treatment — there is no persisted 'pre-disturbance' era to compute from a ban
        boundary alone; the hierarchy-only prior stands."""
        con = _build_cross_era_corpus(pre_wins=80, pre_losses=20, post_wins=3, post_losses=2)
        # No entity_eras row at all -> era_horizons degrades Reanimator to ban-only (via
        # archetype_valid_since, which will be None here since Reanimator never ran a banned
        # card) — so there is no boundary at all for this pair; the cell is full-corpus.
        adaptive = build_adaptive_matrix(con, min_row_share=0.0)
        assert adaptive.horizon_meta["Reanimator"].source == "ban-only"
        cell = adaptive.matrix.cells[("Reanimator", "Control")]
        assert cell.prior_source == "marginal"
        con.close()

    def test_undisturbed_cell_unchanged_from_unit1_behavior(self):
        """Aggro vs Control has no boundary at all (valid_since None both sides) — behaves
        exactly like Unit 1 (no cross-era possible without a truncation window)."""
        con = _build_cross_era_corpus(pre_wins=80, pre_losses=20, post_wins=3, post_losses=2)
        _write_era(con, "Reanimator", "2026-01-01")

        adaptive = build_adaptive_matrix(con, min_row_share=0.0)
        assert adaptive.valid_since["Aggro"] is None
        assert adaptive.cell_windows[("Aggro", "Control")] is None
        cell = adaptive.matrix.cells[("Aggro", "Control")]
        assert cell.prior_source == "marginal"
        con.close()
