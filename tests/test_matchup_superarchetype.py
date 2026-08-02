"""Builder-level tests for the superarchetype layer in ``build_multi_split_adaptive``
(epic-superarchetype-layer-chain Unit 4).

Two hermetic corpora:

- a purpose-built seven-archetype corpus (``_hero_con``) whose tallies are tuned so BOTH rungs
  genuinely engage (rung 1 needs an even two-member LOO pool to clear ``m_eff >= 2.0``; rung 2
  needs the subject family's siblings to agree), the imputation license is earnable (three
  evaluable columns), and one intra-family thin cell exists;
- the shared adaptive parity corpus + a two-member-cluster registry, where every rung REFUSES
  (LOO always leaves one member) — proving engaged-rungs-only changes and camp/attribution
  plumbing on the corpus the golden pins.

The off path (``superarchetypes=None`` / empty registry) is asserted cell-for-cell against the
default build here; the pinned sha golden in ``test_matchup_superarchetype_golden.py`` is the
cross-session half of the same proof.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from conftest import in_current_regime
from test_matchup_multi_split import PARENTS, adaptive_con

from legacy_engine.analytics.matchup import DISPLAY_GATE_N, build_multi_split_adaptive
from legacy_engine.analytics.superarchetype.cluster import ClusterMember
from legacy_engine.analytics.superarchetype.registry import (
    RegistryCluster,
    SuperarchetypeRegistry,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.ingestion.cache import parse_cache_item

_CELL_FIELDS = (
    "archetype_a", "archetype_b", "wins", "n", "p_raw", "p_shrunk",
    "ci_low", "ci_high", "tier", "is_mirror", "display", "prior_mean", "prior_source",
)

_LAST_BAN = max(event_date for event_date, _card, _reason in BAN_EVENTS)
_PRE_REGIME_DATE = (_LAST_BAN - timedelta(days=30)).isoformat()  # before the current regime
_CURRENT_DATE = in_current_regime(7)

# player -> archetype (no camps; every archetype clears the default row floor)
_ROSTER = {
    "h1": "Hero", "h2": "Hero",
    "sa1": "SibA", "sb1": "SibB",
    "x1": "OppX", "y1": "OppY", "z1": "OppZ",
    "s1": "Solo",
}

_MAIN = [{"Count": 4, "CardName": "Brainstorm"}, {"Count": 4, "CardName": "Ponder"}]

# (player1 beats player2, result, repeat) — current-regime tournament.
_ROUNDS_CURRENT: list[tuple[str, str, str, int]] = [
    # Hero vs OppX: THIN (2-2, n=4) — the imputation/ladder target.
    ("h1", "x1", "2-1", 2), ("x1", "h1", "2-0", 2),
    # Hero vs OppY: 9-7 here (+2-2 pre-regime below = 11/20 total, even with OppZ's 20).
    ("h1", "y1", "2-0", 9), ("y1", "h1", "2-1", 7),
    # Hero vs OppZ: 9-11 (n=20).
    ("h1", "z1", "2-0", 9), ("z1", "h1", "2-1", 11),
    # Hero vs SibA: intra-family thin cell (4-2, n=6).
    ("h1", "sa1", "2-0", 4), ("sa1", "h1", "2-1", 2),
    # Hero mirror: n=10.
    ("h1", "h2", "2-1", 10),
    # Siblings vs the enemy family — the imputation pool and the license columns.
    ("sa1", "x1", "2-0", 14), ("x1", "sa1", "2-1", 11),
    ("sb1", "x1", "2-0", 13), ("x1", "sb1", "2-1", 12),
    ("sa1", "y1", "2-0", 8), ("y1", "sa1", "2-1", 7),
    ("sb1", "y1", "2-0", 7), ("y1", "sb1", "2-1", 8),
    ("sa1", "z1", "2-0", 7), ("z1", "sa1", "2-1", 7),
    ("sb1", "z1", "2-0", 7), ("z1", "sb1", "2-1", 7),
    # Solo: thin vs OppX, displayable pooled fallback via OppY/OppZ.
    ("s1", "x1", "2-1", 1), ("x1", "s1", "2-0", 2),
    ("s1", "y1", "2-0", 8), ("y1", "s1", "2-1", 8),
    ("s1", "z1", "2-0", 8), ("z1", "s1", "2-1", 8),
    # Solo vs Hero: displayable (n=32) — keeps the ladder's sub-display-only rule non-vacuous.
    ("s1", "h1", "2-0", 16), ("h1", "s1", "2-1", 16),
]

# Pre-regime tournament: 4 of Hero's 20 OppY matches — makes the current-regime share fractional.
_ROUNDS_OLD: list[tuple[str, str, str, int]] = [
    ("h1", "y1", "2-0", 2), ("y1", "h1", "2-1", 2),
]


def _raw(name: str, date: str, spec: list[tuple[str, str, str, int]]) -> dict:
    return {
        "Tournament": {
            "Name": name, "Date": date,
            "Uri": f"https://example.test/{name}", "Formats": "Legacy",
        },
        "Decks": [
            {"Player": p, "Result": "1st Place", "Mainboard": _MAIN, "Sideboard": []}
            for p in _ROSTER
        ],
        "Rounds": [
            {"Player1": a, "Player2": b, "Result": result}
            for a, b, result, repeat in spec for _ in range(repeat)
        ],
        "Standings": [],
    }


def _hero_con(path: str = ":memory:"):
    """The hero corpus, optionally file-backed (the script e2e needs a --db path)."""
    con = store.connect(path)
    for name, date, spec in (
        ("hero-old", _PRE_REGIME_DATE, _ROUNDS_OLD),
        ("hero-current", _CURRENT_DATE, _ROUNDS_CURRENT),
    ):
        tid = store.load_tournament(con, parse_cache_item(_raw(name, date, spec), "MTGO"))
        for player, archetype in _ROSTER.items():
            con.execute(
                "UPDATE decks SET archetype=? WHERE tournament_id=? AND player=?",
                [archetype, tid, player],
            )
    return con


def _member(archetype: str, provenance: str = "derived") -> ClusterMember:
    return ClusterMember(archetype=archetype, provenance=provenance, n_decks=40, note=None)


def _registry(clusters, *, window_since: str | None = _CURRENT_DATE) -> SuperarchetypeRegistry:
    return SuperarchetypeRegistry(
        clusters=tuple(clusters), staples=(), unassigned=(),
        window_since=window_since, window_until=None,
        derived_at="2026-08-01T00:00:00+00:00",
        stability=0.95, cophenetic=0.9, degraded=False, reasons=(), seed=0, n_boot=200,
    )


def _hero_registry() -> SuperarchetypeRegistry:
    return _registry([
        RegistryCluster(
            id="sa-fair", label="Fair",
            members=(_member("Hero"), _member("SibA"), _member("SibB")),
            au=None, height=None, bp_at_unit_scale=None, curated=False,
        ),
        RegistryCluster(
            id="sa-enemy", label="Enemy",
            members=(_member("OppX"), _member("OppY"), _member("OppZ")),
            au=None, height=None, bp_at_unit_scale=None, curated=False,
        ),
    ])


def _fields(cell) -> dict:
    return {f: getattr(cell, f) for f in _CELL_FIELDS}


_RUNG_MARKERS = ("superarchetype cell (leave-opponent-out;", "cluster × cluster (leave-S-out")


# ---------------------------------------------------------------------------
# The off path — byte-identical to the default build
# ---------------------------------------------------------------------------


class TestOffPathIdentity:
    def test_none_and_empty_registry_leave_every_field_identical(self):
        con = _hero_con()
        base = build_multi_split_adaptive(con, parents=())
        off = build_multi_split_adaptive(con, parents=(), superarchetypes=None)
        empty = build_multi_split_adaptive(con, parents=(), superarchetypes=_registry([]))
        con.close()

        for ams in (off, empty):
            assert set(ams.multi.cells) == set(base.multi.cells)
            for key, cell in base.multi.cells.items():
                assert _fields(ams.multi.cells[key]) == _fields(cell), key
            assert ams.cell_windows == base.cell_windows
            assert ams.valid_since == base.valid_since
            assert ams.cluster_cells == {} and ams.imputed_cells == {} and ams.ladder == {}

        assert off.audit_preamble == base.audit_preamble
        assert empty.audit_preamble == (
            *base.audit_preamble, "// superarchetype: registry empty — layer off",
        )


# ---------------------------------------------------------------------------
# The prior rungs — engaged cells change, everything else is untouched
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def builds():
    con = _hero_con()
    base = build_multi_split_adaptive(con, parents=())
    overlay = build_multi_split_adaptive(con, parents=(), superarchetypes=_hero_registry())
    con.close()
    return base, overlay


@pytest.fixture(scope="module")
def overlay(builds):
    _base, overlay = builds
    return overlay


class TestPriorRungs:
    def test_rung_1_engages_with_the_epic_label_shape(self, builds):
        _base, overlay = builds
        cell = overlay.multi.cells[("Hero", "OppX")]
        assert cell.prior_source == (
            "superarchetype cell (leave-opponent-out; sa-enemy, m_eff 2.0, I²=0.00)"
        )
        # The LOO pool is OppY (11/20) + OppZ (9/20) — pooled around 0.5, never OppX's own data.
        assert cell.prior_mean == pytest.approx(0.5, abs=0.02)

    def test_rung_2_engages_when_rung_1_fails_its_gate(self, builds):
        _base, overlay = builds
        cell = overlay.multi.cells[("Hero", "OppY")]
        assert cell.prior_source.startswith(
            "cluster × cluster (leave-S-out, leave-O-out; sa-fair×sa-enemy, m_eff 2.0"
        )

    def test_only_rung_labeled_cells_changed(self, builds):
        base, overlay = builds
        changed = {
            key for key, cell in base.multi.cells.items()
            if _fields(overlay.multi.cells[key]) != _fields(cell)
        }
        rung_labeled = {
            key for key, cell in overlay.multi.cells.items()
            if cell.prior_source and cell.prior_source.startswith(_RUNG_MARKERS)
        }
        assert changed == rung_labeled
        assert ("Hero", "OppX") in changed and ("OppY", "Hero") in changed

    def test_engaged_cells_change_only_the_prior_fields(self, builds):
        base, overlay = builds
        for key in (("Hero", "OppX"), ("Hero", "OppY")):
            got, want = overlay.multi.cells[key], base.multi.cells[key]
            for field_name in ("wins", "n", "p_raw", "ci_low", "ci_high", "tier", "display"):
                assert getattr(got, field_name) == getattr(want, field_name), (key, field_name)
            assert got.p_shrunk != want.p_shrunk

    def test_registry_audit_lines_ride_the_preamble(self, builds):
        _base, overlay = builds
        assert any(
            line.startswith("// superarchetype: 2 clusters (6 contributors), window ")
            for line in overlay.audit_preamble
        )


# ---------------------------------------------------------------------------
# Pooled display cells, imputed cells, ladder
# ---------------------------------------------------------------------------


class TestOverlayCells:
    def test_pooled_cell_includes_the_opponents_own_matches(self, overlay):
        pooled = overlay.cluster_cells[("Hero", "sa-enemy")]
        # Display pool = OppX (n=4) + OppY (n=20) + OppZ (n=20) — OppX's matches INCLUDED,
        # unlike the leave-opponent-out prior.
        assert {(s.archetype, s.n) for s in pooled.member_split} == {
            ("OppX", 4), ("OppY", 20), ("OppZ", 20),
        }
        assert pooled.pooled_p is not None
        assert pooled.n_eff >= DISPLAY_GATE_N
        assert pooled.window_note.startswith("member windows: full x3")
        # 4 of Hero-vs-OppY's 20 matches predate the current regime: share = 40/44.
        assert pooled.current_regime_share == pytest.approx(40 / 44)
        assert "one-sided" in pooled.heterogeneity.one_sided_note  # the I² caveat survives

    def test_intra_family_pool_reports_the_mirror_and_refuses_single_member(self, overlay):
        pooled = overlay.cluster_cells[("Hero", "sa-fair")]
        assert pooled.mirror_n == 10  # the Hero mirror rides the intra-family pool
        assert pooled.pooled_p is None
        assert "single-member cluster" in pooled.refused_reason  # only SibA has Hero tallies
        assert pooled.intra_cluster_share == 1.0

    def test_imputed_cell_carries_family_license_and_freshness(self, overlay):
        imputed = overlay.imputed_cells[("Hero", "OppX")]
        assert imputed.p == pytest.approx(27 / 50)  # SibA 14/25 + SibB 13/25, leave-Hero-out
        assert imputed.siblings == ("SibA", "SibB")
        assert imputed.pool_n == 50
        assert imputed.license.granted and imputed.license.cluster_id == "sa-fair"
        assert imputed.license.cols_evaluated == 3
        assert imputed.ci_low < 27 / 50 < imputed.ci_high  # CI widened by tau_profile
        assert imputed.window_note.startswith("member windows: full x2")
        assert imputed.current_regime_share == 1.0

    def test_ladder_prefers_imputed_over_pooled_for_the_same_cell(self, overlay):
        entry = overlay.ladder[("Hero", "OppX")]
        assert entry.kind == "imputed"
        assert entry.token == "imputed from sa-fair (2 sibs, pool n=50)"
        assert [s.archetype for s in entry.sibling_split] == ["SibA", "SibB"]
        assert entry.reasons == ("measured cell below the display gate (n=4 < 30)",)

    def test_intra_family_cell_never_imputes_and_names_it(self, overlay):
        assert ("Hero", "SibA") not in overlay.imputed_cells
        entry = overlay.ladder[("Hero", "SibA")]
        assert entry.kind == "none"
        assert (
            "imputation not attempted: SibA is inside Hero's own family sa-fair"
            in entry.reasons
        )
        assert any(r.startswith("pooled cell refused: single-member") for r in entry.reasons)

    def test_subject_without_a_family_falls_to_the_pooled_rung(self, overlay):
        entry = overlay.ladder[("Solo", "OppX")]
        assert entry.kind == "pooled"
        assert entry.cluster_id == "sa-enemy"
        assert entry.token.startswith("pooled vs sa-enemy (n_eff ")
        assert "imputation not attempted: subject has no cluster in the registry" in entry.reasons

    def test_ladder_covers_exactly_the_sub_display_cells(self, overlay):
        for (subject, opponent), entry in overlay.ladder.items():
            assert overlay.multi.cells[(subject, opponent)].n < DISPLAY_GATE_N, entry
        displayable = [
            key for key, cell in overlay.multi.cells.items()
            if key[0] != key[1] and cell.n >= DISPLAY_GATE_N
        ]
        assert displayable  # non-vacuous
        assert all(key not in overlay.ladder for key in displayable)


# ---------------------------------------------------------------------------
# The adaptive parity corpus: refusing rungs leave every cell untouched; camps and
# attribution kinds plumb through
# ---------------------------------------------------------------------------


def _two_member_registry() -> SuperarchetypeRegistry:
    return _registry([
        RegistryCluster(
            id="sa-blue", label="Fair blue",
            members=(_member("Control"), _member("Delver")),
            au=None, height=None, bp_at_unit_scale=None, curated=False,
        ),
        RegistryCluster(
            id="sa-combo", label="Combo",
            members=(_member("Doomsday"), _member("Painter")),
            au=None, height=None, bp_at_unit_scale=None, curated=False,
        ),
    ], window_since="2026-01-01")


@pytest.fixture(scope="module")
def adaptive_builds():
    con = adaptive_con()
    base = build_multi_split_adaptive(con, parents=PARENTS)
    overlay = build_multi_split_adaptive(
        con, parents=PARENTS, superarchetypes=_two_member_registry(),
    )
    con.close()
    return base, overlay


class TestAdaptiveCorpusOverlay:
    def test_two_member_clusters_never_engage_a_rung_so_cells_are_identical(self, adaptive_builds):
        base, overlay = adaptive_builds
        # Leave-opponent-out on a two-member cluster always leaves one member — "not a pool at
        # all" — and rung 2 likewise; every cell must therefore be field-for-field identical.
        for key, cell in base.multi.cells.items():
            assert _fields(overlay.multi.cells[key]) == _fields(cell), key

    def test_overlay_maps_still_serve_pools_and_ladders(self, adaptive_builds):
        _base, overlay = adaptive_builds
        pooled = overlay.cluster_cells[("Control", "sa-combo")]
        assert {s.archetype for s in pooled.member_split} == {"Doomsday", "Painter"}
        assert overlay.ladder  # sub-display cells resolved

    def test_camp_subject_pools_at_its_own_era_window(self, adaptive_builds):
        _base, overlay = adaptive_builds
        # Murktide's own era starts MID_DATE, so its member tallies come from the late window
        # only; the pool is uneven (Control 16, Delver 11) — the concentration gate fails and
        # the cell is SERVED with the label (honest-degrade, never suppression).
        camp_pool = overlay.cluster_cells[("Doomsday [Murktide]", "sa-blue")]
        assert {(s.archetype, s.n) for s in camp_pool.member_split} == {
            ("Control", 16), ("Delver", 11),
        }
        assert camp_pool.pooled_p is not None
        assert not camp_pool.concentration.passed
        assert any("dominated by Control" in note for note in camp_pool.provenance)
        assert "2026-03-01" in camp_pool.window_note
        # The camp's pool against its OWN family has nothing drawable: the own-parent column is
        # deliberately absent and no Murktide-vs-Painter match exists inside Murktide's era.
        assert ("Doomsday [Murktide]", "sa-combo") not in overlay.cluster_cells

    def test_stale_registry_window_warns_in_the_preamble(self, adaptive_builds):
        _base, overlay = adaptive_builds
        assert any(
            "predates the current regime start" in line for line in overlay.audit_preamble
        )

    def test_attribution_kinds_ride_horizon_meta(self, adaptive_builds):
        base, _overlay = adaptive_builds
        meta = base.horizon_meta
        assert meta["Doomsday"].attribution_kind == "release"
        assert meta["Doomsday [Murktide]"].attribution_kind == "ban"
        assert meta["Doomsday [Turbo]"].attribution_kind == "release"  # era-parent inheritance
        assert meta["Control"].attribution_kind is None  # undisturbed
        assert meta["Painter [Grindstone]"].attribution_kind is None  # ban-only source
