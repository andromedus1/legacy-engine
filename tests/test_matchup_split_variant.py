"""Tests for variant-conditioned matchup cells (epic-subarchetype-resolution-matchup-cells).

Covers Units 1-5: ``effective_label`` (pure), ``split_variant`` passthrough on
``compute_match_results`` / ``build_matrix`` / ``build_adaptive_matrix``, force-included camp rows,
the adaptive-horizon strip-suffix fallback (``_base_archetype``), and the CLI ``--split-variant``
flag + audit-echo line. House style: module-level raw dicts -> ``parse_cache_item`` ->
``store.load_tournament`` into ``:memory:`` (or a tmp DuckDB file for CLI tests); labels pinned via
direct SQL ``UPDATE``; ``TestX`` classes; deterministic.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.analytics import (
    build_adaptive_matrix,
    build_matrix,
    compute_match_results,
    effective_label,
)
from legacy_engine.analytics.matchup import _base_archetype
from legacy_engine.cli import main
from legacy_engine.confidence import tier_for_sample
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# Shared corpus: one Doomsday archetype split into three camps vs one Control
# opponent, all within a single tournament (rounds reference the same 4 deck
# rows repeatedly — the same pattern test_matchup.py's `_LARGE` fixture uses).
#
#   p0  Doomsday / variant "Murktide"   beats Control 32x  -> n=32 (evolving tier)
#   p1  Doomsday / variant "Painter"    beats Control 1x   -> n=1  (below the
#                                                              default 0.02 row-share floor)
#   p2  Doomsday / variant NULL         beats Control 2x, loses 1x -> n=3 (unlabeled residue)
#   p3  Control (not split)             the shared opponent
#
# Unsplit: Doomsday marginal n = 32+1+3 = 36 (wins=35, losses=1); Control marginal n = 36.
# denom = 2*36 = 72. Split shares: Murktide 32/72=.444, Painter 1/72=.014 (<.02!), unlabeled
# 3/72=.042, Control 36/72=.5.
# ---------------------------------------------------------------------------

_CAMP_MAIN = [{"Count": 4, "CardName": "Lion's Eye Diamond"}, {"Count": 2, "CardName": "Duress"}]
_CONTROL_MAIN = [{"Count": 4, "CardName": "Brainstorm"}, {"Count": 4, "CardName": "Swords to Plowshares"}]


def _deck(player: str, mainboard: list[dict]) -> dict:
    return {"Player": player, "Result": "1st Place", "Mainboard": mainboard, "Sideboard": []}


def _camp_corpus_raw() -> dict:
    rounds = (
        [{"Player1": "p0", "Player2": "p3", "Result": "2-1"} for _ in range(32)]
        + [{"Player1": "p1", "Player2": "p3", "Result": "2-1"}]
        + [{"Player1": "p2", "Player2": "p3", "Result": "2-1"} for _ in range(2)]
        + [{"Player1": "p3", "Player2": "p2", "Result": "2-1"}]
    )
    return {
        "Tournament": {
            "Name": "Camp Split Test",
            "Date": "2026-06-01",
            "Uri": "https://example.test/camp-split",
            "Formats": "Legacy",
        },
        "Decks": [
            _deck("p0", _CAMP_MAIN),
            _deck("p1", _CAMP_MAIN),
            _deck("p2", _CAMP_MAIN),
            _deck("p3", _CONTROL_MAIN),
        ],
        "Rounds": rounds,
        "Standings": [],
    }


def _build_camp_corpus(con) -> str:
    """Load the camp-split corpus into ``con``; pin archetype/variant via direct SQL UPDATE."""
    tid = store.load_tournament(con, parse_cache_item(_camp_corpus_raw(), "MTGO"))
    con.execute(
        "UPDATE decks SET archetype='Doomsday', variant='Murktide' "
        "WHERE tournament_id=? AND player='p0'",
        [tid],
    )
    con.execute(
        "UPDATE decks SET archetype='Doomsday', variant='Painter' "
        "WHERE tournament_id=? AND player='p1'",
        [tid],
    )
    con.execute(
        "UPDATE decks SET archetype='Doomsday' WHERE tournament_id=? AND player='p2'",
        [tid],
    )
    con.execute(
        "UPDATE decks SET archetype='Control' WHERE tournament_id=? AND player='p3'",
        [tid],
    )
    return tid


def _con():
    return store.connect(":memory:")


# ---------------------------------------------------------------------------
# Unit 1 — effective_label (pure)
# ---------------------------------------------------------------------------


class TestEffectiveLabel:
    def test_matching_archetype_with_variant(self):
        assert effective_label("Doomsday", "Murktide", "Doomsday") == "Doomsday [Murktide]"

    def test_matching_archetype_null_variant_becomes_unlabeled(self):
        assert effective_label("Doomsday", None, "Doomsday") == "Doomsday [unlabeled]"

    def test_split_variant_none_is_identity(self):
        assert effective_label("Doomsday", "Murktide", None) == "Doomsday"

    def test_non_matching_archetype_unchanged(self):
        assert effective_label("Control", "SomeVariant", "Doomsday") == "Control"

    def test_none_archetype_passes_through(self):
        assert effective_label(None, "Murktide", "Doomsday") is None


# ---------------------------------------------------------------------------
# Unit 2 — compute_match_results(split_variant=...)
# ---------------------------------------------------------------------------


class TestComputeMatchResultsSplitVariant:
    def test_unsplit_default_keeps_bare_archetype(self):
        con = _con()
        _build_camp_corpus(con)
        res = compute_match_results(con)
        assert "Doomsday [Murktide]" not in res.archetypes
        assert res.archetypes["Doomsday"].wins == 35
        assert res.archetypes["Doomsday"].losses == 1
        con.close()

    def test_split_produces_camp_labels_both_sides(self):
        con = _con()
        _build_camp_corpus(con)
        res = compute_match_results(con, split_variant="Doomsday")
        assert "Doomsday" not in res.archetypes  # parent label fully replaced
        assert res.archetypes["Doomsday [Murktide]"].wins == 32
        assert res.archetypes["Doomsday [Painter]"].wins == 1
        assert res.archetypes["Doomsday [unlabeled]"].wins == 2
        assert res.archetypes["Doomsday [unlabeled]"].losses == 1
        # Opponent (not split) is unaffected
        assert res.archetypes["Control"].wins == 1
        assert res.archetypes["Control"].losses == 35
        con.close()

    def test_split_directed_cells_keyed_by_camp(self):
        con = _con()
        _build_camp_corpus(con)
        res = compute_match_results(con, split_variant="Doomsday")
        assert res.matchups[("Doomsday [Murktide]", "Control")].wins == 32
        assert res.matchups[("Control", "Doomsday [Murktide]")].losses == 32
        con.close()

    def test_cross_camp_pairing_is_directed_cell_not_mirror(self):
        """Two camps of the SAME parent are distinct effective labels: their pairing must
        produce directed cells, not count as a mirror (review follow-up, PR #37)."""
        con = _con()
        tid = _build_camp_corpus(con)
        # p0 (Doomsday [Murktide]) beats p1 (Doomsday [Painter]) 2-0
        con.execute(
            "INSERT INTO rounds VALUES (?, ?, 'p0', 'p1', '2-0')",
            [tid, 9900],
        )
        res = compute_match_results(con, split_variant="Doomsday")
        assert res.matchups[("Doomsday [Murktide]", "Doomsday [Painter]")].wins == 1
        assert res.matchups[("Doomsday [Painter]", "Doomsday [Murktide]")].losses == 1
        # not credited as a mirror for either camp label
        assert res.mirror_n.get("Doomsday [Murktide]", 0) == 0
        assert res.mirror_n.get("Doomsday [Painter]", 0) == 0
        # UNSPLIT run: the same pairing IS a parent-label mirror (both sides 'Doomsday')
        res_unsplit = compute_match_results(con)
        assert res_unsplit.mirror_n.get("Doomsday", 0) >= 1
        con.close()

    def test_split_variant_no_op_when_archetype_absent(self):
        """split_variant naming an archetype that doesn't appear in the corpus is a no-op."""
        con = _con()
        _build_camp_corpus(con)
        res = compute_match_results(con, split_variant="NoSuchArchetype")
        assert res.archetypes.keys() == {"Doomsday", "Control"}
        con.close()


# ---------------------------------------------------------------------------
# Unit 3 — build_matrix(split_variant=...): row inclusion + force-include
# ---------------------------------------------------------------------------


class TestBuildMatrixSplitVariant:
    def test_golden_no_flag_output_unaffected_by_variant_presence(self):
        """(a) The no-flag path must be byte-identical even though decks.variant is populated."""
        con = _con()
        _build_camp_corpus(con)
        matrix = build_matrix(con)
        assert matrix.archetypes == ["Control", "Doomsday"]
        cell = matrix.cells[("Doomsday", "Control")]
        assert (cell.wins, cell.n) == (35, 36)
        assert tier_for_sample(cell.n) == "evolving"
        # No camp label leaks into the default path
        assert not any("[" in a for a in matrix.archetypes)
        con.close()

    def test_split_flag_parent_row_absent_camp_rows_present(self):
        """(b) Flagged run: parent row gone, camp rows present with correct n/tier."""
        con = _con()
        _build_camp_corpus(con)
        matrix = build_matrix(con, split_variant="Doomsday")
        assert "Doomsday" not in matrix.archetypes
        assert "Doomsday [Murktide]" in matrix.archetypes
        murktide_cell = matrix.cells[("Doomsday [Murktide]", "Control")]
        assert (murktide_cell.wins, murktide_cell.n) == (32, 32)
        assert murktide_cell.tier == tier_for_sample(32) == "evolving"
        con.close()

    def test_unlabeled_residue_row_appears(self):
        """(c) NULL-variant decks stay visible as '<archetype> [unlabeled]', not dropped."""
        con = _con()
        _build_camp_corpus(con)
        matrix = build_matrix(con, split_variant="Doomsday")
        assert "Doomsday [unlabeled]" in matrix.archetypes
        cell = matrix.cells[("Doomsday [unlabeled]", "Control")]
        assert (cell.wins, cell.n) == (2, 3)
        con.close()

    def test_force_include_below_min_row_share_floor(self):
        """(d) Painter's camp (share ~1.4% < the 2% default floor) is force-included."""
        con = _con()
        _build_camp_corpus(con)
        # Sanity: Painter's marginal share is indeed below the default floor.
        res = compute_match_results(con, split_variant="Doomsday")
        painter_share = res.archetypes["Doomsday [Painter]"].n / (
            2 * (res.coverage.decisive_matched + res.coverage.mirror_matches)
        )
        assert painter_share < 0.02

        matrix = build_matrix(con, split_variant="Doomsday", min_row_share=0.02)
        assert "Doomsday [Painter]" in matrix.archetypes
        cell = matrix.cells[("Doomsday [Painter]", "Control")]
        assert (cell.wins, cell.n) == (1, 1)
        con.close()

    def test_non_split_archetype_still_respects_floor(self):
        """A fringe, non-split archetype below the floor is still excluded (force-include is scoped
        to the split archetype's camps only, not a blanket relaxation)."""
        con = _con()
        _build_camp_corpus(con)
        # One decisive (non-mirror) match between two unrelated fringe archetypes: negligible
        # share of the combined corpus, and NOT a mirror (mirror-only archetypes get an honest
        # inclusion path of their own — see test_matchup.py::TestMirrorInclusion — so this must be
        # a decisive cross-archetype match to isolate the min_row_share floor itself).
        raw = _camp_corpus_raw()
        raw["Tournament"]["Name"] = "Fringe Tournament"
        raw["Tournament"]["Uri"] = "https://example.test/fringe"
        raw["Decks"] = [_deck("f1", _CAMP_MAIN), _deck("f2", _CAMP_MAIN)]
        raw["Rounds"] = [{"Player1": "f1", "Player2": "f2", "Result": "2-1"}]
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute("UPDATE decks SET archetype='Fringe1' WHERE tournament_id=? AND player='f1'", [tid])
        con.execute("UPDATE decks SET archetype='Fringe2' WHERE tournament_id=? AND player='f2'", [tid])

        matrix = build_matrix(con, split_variant="Doomsday", min_row_share=0.02)
        assert "Fringe1" not in matrix.archetypes
        assert "Fringe2" not in matrix.archetypes
        assert "Doomsday [Painter]" in matrix.archetypes  # still force-included
        con.close()


# ---------------------------------------------------------------------------
# Unit 3 — _base_archetype (pure) + build_adaptive_matrix(split_variant=...)
# ---------------------------------------------------------------------------


class TestBaseArchetype:
    def test_camp_label_strips_to_split_variant(self):
        assert _base_archetype("Doomsday [Murktide]", "Doomsday") == "Doomsday"

    def test_unlabeled_camp_strips_to_split_variant(self):
        assert _base_archetype("Doomsday [unlabeled]", "Doomsday") == "Doomsday"

    def test_non_camp_label_unchanged(self):
        assert _base_archetype("Control", "Doomsday") == "Control"

    def test_split_variant_none_is_identity(self):
        assert _base_archetype("Doomsday [Murktide]", None) == "Doomsday [Murktide]"

    def test_different_archetype_bracket_label_unchanged(self):
        """A label that happens to contain brackets but isn't THIS split's camp is untouched."""
        assert _base_archetype("Some [Other] Thing", "Doomsday") == "Some [Other] Thing"


def _tournament(name: str, date: str, decks: list[dict], rounds: list[dict]) -> dict:
    return {
        "Tournament": {"Name": name, "Date": date, "Uri": f"https://example.test/{name}",
                       "Formats": "Legacy"},
        "Decks": decks, "Rounds": rounds, "Standings": [],
    }


def _build_adaptive_split_corpus(pre_n: int = 10, post_n: int = 10):
    """Doomsday (variant "Murktide", running Entomb pre-ban) vs Control — mirrors
    test_adaptive_regime.py's two-regime corpus, but Doomsday's decks all carry a variant so the
    camp label ``"Doomsday [Murktide]"`` is what ``archetype_valid_since`` must resolve for, via
    the parent archetype fallback (Unit 3's ``_base_archetype``)."""
    con = store.connect(":memory:")

    def load(name, date, idx, doomsday_main):
        decks = [_deck(f"dd{idx}", [{"Count": 4, "CardName": c} for c in doomsday_main]),
                  _deck(f"ctrl{idx}", _CONTROL_MAIN)]
        rounds = [{"Player1": f"dd{idx}", "Player2": f"ctrl{idx}", "Result": "2-1"}]
        tid = store.load_tournament(con, parse_cache_item(_tournament(name, date, decks, rounds), "MTGO"))
        con.execute(
            "UPDATE decks SET archetype='Doomsday', variant='Murktide' "
            "WHERE tournament_id=? AND player=?",
            [tid, f"dd{idx}"],
        )
        con.execute("UPDATE decks SET archetype='Control' WHERE tournament_id=? AND player=?",
                    [tid, f"ctrl{idx}"])

    idx = 0
    for _ in range(pre_n):   # pre-ban: Doomsday runs Entomb (the to-be-banned card)
        load(f"pre{idx}", "2025-06-01", idx, ["Entomb", "Reanimate", "Griselbrand"])
        idx += 1
    for _ in range(post_n):  # post-ban: Doomsday no longer runs Entomb
        load(f"post{idx}", "2026-01-01", idx, ["Reanimate", "Griselbrand", "Archon of Cruelty"])
        idx += 1
    return con


class TestBuildAdaptiveMatrixSplitVariant:
    def test_camp_inherits_parent_valid_since(self):
        """(e) The camp label's ban-affectedness horizon falls back to the parent archetype's."""
        con = _build_adaptive_split_corpus(pre_n=10, post_n=10)
        adaptive = build_adaptive_matrix(con, min_row_share=0.0, split_variant="Doomsday")
        assert "Doomsday [Murktide]" in adaptive.valid_since
        assert adaptive.valid_since["Doomsday [Murktide]"] == "2025-11-10"
        assert adaptive.valid_since["Control"] is None
        assert adaptive.cell_windows[("Doomsday [Murktide]", "Control")] == "2025-11-10"

        # The windowed cell must be a strict post-ban subset of the full-corpus cell.
        full = build_matrix(con, min_row_share=0.0, split_variant="Doomsday")
        adaptive_n = adaptive.matrix.cells[("Doomsday [Murktide]", "Control")].n
        full_n = full.cells[("Doomsday [Murktide]", "Control")].n
        assert 0 < adaptive_n < full_n
        con.close()


# ---------------------------------------------------------------------------
# Unit 4 — CLI: `report matchups --split-variant`
# ---------------------------------------------------------------------------


class TestGoldenReportMatchupsDefault:
    """Gate-tests F1 (v0.3.0): the no-flag `report matchups` body is pinned byte-for-byte —
    the load-bearing gated-additive golden the feature prose promised. A pure formatting or
    rounding regression to the default output must fail here, not slip past substring checks.

    Re-pinned for epic-stable-era-windows-shrinkage (Unit 3): the hierarchical cell prior
    replaces the flat-0.5 prior for every cell, so the shrunk% halves of this 2-archetype grid
    move (Control's own marginal is entirely self-referential in this fixture — its single
    opponent IS its whole marginal — so its cell's prior pulls harder than flat 0.5 did: a known,
    documented, accepted EB simplification the project already ships in `card_value.py`'s own
    two-level chain). ``_GRID_PRE_HIERARCHY`` is kept alongside the new ``_GRID`` so
    ``test_repin_only_shrunk_values_moved_raw_n_identical`` can prove, mechanically, that this
    re-pin changed ONLY the shrunk%/prior_source halves — raw% and n= are byte-identical.
    """

    _SECTION = (
        "=== Matchup Matrix [{prov}] ===\n"
        "Total decisive matches: {n}\n"
        "Caveat: Matchup data is computed only from rounds-bearing events (Challenges + paper); "
        "matchup-n is a separate, smaller sample than meta-share-n. Cells with n<30 are hidden.\n"
    )
    # Pre-epic-stable-era-windows-shrinkage golden (flat-0.5 prior) — retained ONLY so the re-pin
    # diff can be mechanically verified below; not used as an expectation anywhere else.
    _GRID_PRE_HIERARCHY = (
        "Cells: shrunk%|raw% n=matches — the raw record always travels with the estimate; "
        "small n is pulled toward 50%.\n"
        "          Control               Doomsday            \n"
        "----------------------------------------------------\n"
        "Control   n=0 (mirror)          17%|3% n=36         \n"
        "Doomsday  83%|97% n=36          n=0 (mirror)        \n"
        "// window: full-corpus\n"
    )
    _GRID = (
        "Cells: shrunk%|raw% n=matches — the raw record always travels with the estimate; "
        "small n is pulled toward 50%.\n"
        "          Control               Doomsday            \n"
        "----------------------------------------------------\n"
        "Control   n=0 (mirror)          7%|3% n=36          \n"
        "Doomsday  93%|97% n=36          n=0 (mirror)        \n"
        "// window: full-corpus\n"
    )
    GOLDEN = (
        _SECTION.format(prov="all", n=36) + _GRID + "\n"
        + _SECTION.format(prov="online", n=36) + _GRID + "\n"
        + _SECTION.format(prov="paper", n=0)
        + "(no archetypes meet the row-inclusion threshold)\n"
    )

    def test_default_body_byte_identical(self, tmp_path):
        from click.testing import CliRunner
        from legacy_engine.cli import main
        runner = CliRunner()
        db = TestReportMatchupsSplitVariantCLI()._build_db(tmp_path)
        result = runner.invoke(main, ["report", "matchups", "--db", db, "--all-time"])
        assert result.exit_code == 0, result.output
        body = result.output.split("\n\n", 1)[1]
        assert body == self.GOLDEN, (
            f"report matchups default output changed!\n--- expected ---\n{self.GOLDEN!r}\n"
            f"--- got ---\n{body!r}"
        )

    def test_repin_only_shrunk_values_moved_raw_n_identical(self):
        """Mechanical proof the re-pin is honest: every cell's raw%/n= token is byte-identical
        between the pre-hierarchy and post-hierarchy goldens; only the shrunk% token (and the
        fact that they now differ) changed."""
        import re

        cell_re = re.compile(r"(?P<shrunk>\d+)%\|(?P<raw>\d+)% n=(?P<n>\d+)")
        old_cells = cell_re.findall(self._GRID_PRE_HIERARCHY)
        new_cells = cell_re.findall(self._GRID)
        assert old_cells and new_cells
        assert len(old_cells) == len(new_cells)
        for (old_shrunk, old_raw, old_n), (new_shrunk, new_raw, new_n) in zip(old_cells, new_cells):
            assert (old_raw, old_n) == (new_raw, new_n), "raw%/n must be byte-identical across the re-pin"
        # The whole point of the re-pin: at least one cell's shrunk% actually moved.
        assert [s for s, _, _ in old_cells] != [s for s, _, _ in new_cells]


class TestReportMatchupsSplitVariantCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _build_db(self, tmp_path):
        db_path = str(tmp_path / "split_variant_test.duckdb")
        con = store.connect(db_path)
        try:
            _build_camp_corpus(con)
        finally:
            con.close()
        return db_path

    def test_no_flag_output_has_no_camp_labels(self, runner, tmp_path):
        """(a) CLI-level golden check: no --split-variant -> no bracketed camp labels anywhere,
        even though decks.variant is populated in the DB."""
        db_path = self._build_db(tmp_path)
        result = runner.invoke(main, ["report", "matchups", "--db", db_path, "--all-time"])
        assert result.exit_code == 0, result.output
        assert "Murktide" not in result.output
        assert "Painter" not in result.output
        assert "unlabeled" not in result.output
        assert "split-variant" not in result.output

    def test_split_flag_shows_camp_rows_and_audit_line(self, runner, tmp_path):
        db_path = self._build_db(tmp_path)
        result = runner.invoke(
            main,
            ["report", "matchups", "--db", db_path, "--all-time", "--split-variant", "Doomsday"],
        )
        assert result.exit_code == 0, result.output
        assert "// split-variant: Doomsday" in result.output
        assert "Doomsday [Murktide]" in result.output
        assert "Doomsday [Painter]" in result.output
        assert "Doomsday [unlabeled]" in result.output

    def test_split_flag_camp_rows_show_prior_labels(self, runner, tmp_path):
        """Unit 3 AC (epic-stable-era-windows-shrinkage): --split-variant camp rows surface their
        hierarchical prior_source as a grep-able `// prior: <camp> vs <opponent>: <source>` line —
        the LCO-parent chain for the real (non-split) opponent, the marginal fallback for a
        cross-camp pairing."""
        db_path = self._build_db(tmp_path)
        result = runner.invoke(
            main,
            ["report", "matchups", "--db", db_path, "--all-time", "--split-variant", "Doomsday"],
        )
        assert result.exit_code == 0, result.output
        assert "// prior: Doomsday [Murktide] vs Control: parent cell (leave-camp-out)" in result.output
        assert "// prior: Doomsday [Murktide] vs Doomsday [Painter]: marginal" in result.output
        # No-flag output never gets these audit lines (byte-identical to pre-epic rendering).
        no_flag = runner.invoke(main, ["report", "matchups", "--db", db_path, "--all-time"])
        assert "// prior:" not in no_flag.output

    def test_head_to_head_accepts_camp_label(self, runner, tmp_path):
        db_path = self._build_db(tmp_path)
        result = runner.invoke(
            main,
            [
                "report", "matchups", "--db", db_path, "--all-time",
                "--split-variant", "Doomsday",
                "--a", "Doomsday [Murktide]", "--b", "Control",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Head-to-Head" in result.output
        assert "prior          = parent cell (leave-camp-out)" in result.output
        assert "n              = 32" in result.output

    def test_help_documents_split_variant(self, runner):
        result = runner.invoke(main, ["report", "matchups", "--help"])
        assert result.exit_code == 0
        assert "--split-variant" in result.output

    def test_split_flag_with_no_staged_candidate_adds_no_provenance_line(self, runner, tmp_path, monkeypatch):
        """No staged candidate for the split parent (the normal case) -> no provenance echo;
        the flagged path stays additive-only, never spuriously flags a confirmed/curated split."""
        db_path = self._build_db(tmp_path)
        monkeypatch.setattr(
            "legacy_engine.config.DISCOVERED_VARIANTS_PATH", str(tmp_path / "no-such-file.json"),
        )
        result = runner.invoke(
            main,
            ["report", "matchups", "--db", db_path, "--all-time", "--split-variant", "Doomsday"],
        )
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output

    def test_split_flag_with_staged_candidate_adds_provenance_line(self, runner, tmp_path, monkeypatch):
        """Finding 1: a STAGED (unpromoted) candidate split for the flagged parent must surface
        an honest speculative-provenance note after the existing split-variant audit line."""
        from legacy_engine.archetype.discovered import save_discovered
        from legacy_engine.models.variant import DiscoveredCamp, DiscoveredRegistry, DiscoveredSplitRecord

        db_path = self._build_db(tmp_path)
        staged = tmp_path / "discovered.json"
        save_discovered(
            DiscoveredRegistry(
                version="1",
                splits=[
                    DiscoveredSplitRecord(
                        parent="Doomsday",
                        generated_from="test",
                        params={},
                        camps=[
                            DiscoveredCamp(name="Murktide", signature_cards=["Lion's Eye Diamond"], n=32, tier="evolving"),
                            DiscoveredCamp(name="non-Murktide", signature_cards=[], n=1, tier="speculative"),
                        ],
                        stability=0.95,
                    )
                ],
            ),
            staged,
        )
        monkeypatch.setattr("legacy_engine.config.DISCOVERED_VARIANTS_PATH", str(staged))

        result = runner.invoke(
            main,
            ["report", "matchups", "--db", db_path, "--all-time", "--split-variant", "Doomsday"],
        )
        assert result.exit_code == 0, result.output
        assert "// split-variant: Doomsday" in result.output
        assert (
            "// provenance: Doomsday has a STAGED (unpromoted) candidate split — variant "
            "labels may be speculative-provenance" in result.output
        )

    def test_promoted_staged_record_adds_no_provenance_line(self, runner, tmp_path, monkeypatch):
        """A staged record that has already been promoted (status != candidate) is no longer
        speculative — must not echo the staged-provenance note."""
        from legacy_engine.archetype.discovered import save_discovered
        from legacy_engine.models.variant import DiscoveredCamp, DiscoveredRegistry, DiscoveredSplitRecord

        db_path = self._build_db(tmp_path)
        staged = tmp_path / "discovered.json"
        save_discovered(
            DiscoveredRegistry(
                version="1",
                splits=[
                    DiscoveredSplitRecord(
                        parent="Doomsday",
                        generated_from="test",
                        params={},
                        camps=[
                            DiscoveredCamp(name="Murktide", signature_cards=["Lion's Eye Diamond"], n=32, tier="evolving"),
                        ],
                        stability=0.95,
                        status="promoted",
                    )
                ],
            ),
            staged,
        )
        monkeypatch.setattr("legacy_engine.config.DISCOVERED_VARIANTS_PATH", str(staged))

        result = runner.invoke(
            main,
            ["report", "matchups", "--db", db_path, "--all-time", "--split-variant", "Doomsday"],
        )
        assert result.exit_code == 0, result.output
        assert "// provenance:" not in result.output

    def test_provenance_check_never_breaks_report_on_malformed_registry(self, runner, tmp_path, monkeypatch):
        """The provenance lookup wraps in try/except any — a corrupt staging file must never
        break `report matchups`."""
        db_path = self._build_db(tmp_path)
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        monkeypatch.setattr("legacy_engine.config.DISCOVERED_VARIANTS_PATH", str(bad))

        result = runner.invoke(
            main,
            ["report", "matchups", "--db", db_path, "--all-time", "--split-variant", "Doomsday"],
        )
        assert result.exit_code == 0, result.output
        assert "// split-variant: Doomsday" in result.output
