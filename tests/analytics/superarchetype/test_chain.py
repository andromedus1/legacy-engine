"""Unit tests for the pure superarchetype chain kernel (hand-built dicts, no DB anywhere).

The kernel's job is selection, not estimation: given the adaptive build's windowed tally dicts it
must pick the right PAIRWISE bucket per member, exclude the right tallies BY NAME, walk the fixed
rung order, and resolve the display ladder — the estimator itself is ``aggregate.py``'s and is
tested there. Every fixture here is a literal dict.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from legacy_engine.analytics.superarchetype.aggregate import (
    ImputationLicense,
    MemberTally,
    aggregate_cluster_cell,
    impute_cell,
)
from legacy_engine.analytics.superarchetype.chain import (
    FAMILY_FIRST_KINDS,
    LadderEntry,
    cluster_view,
    draw_cluster_pair_tallies,
    draw_pool_tallies,
    draw_row_tallies,
    registry_audit_lines,
    resolve_ladder,
    rung_prior,
    subject_base,
)
from legacy_engine.analytics.superarchetype.cluster import ClusterMember
from legacy_engine.analytics.superarchetype.registry import (
    RegistryCluster,
    SuperarchetypeRegistry,
)

# ---------------------------------------------------------------------------
# Registry factories (hand-built — no clustering in tests)
# ---------------------------------------------------------------------------


def _member(archetype: str, provenance: str = "derived") -> ClusterMember:
    return ClusterMember(archetype=archetype, provenance=provenance, n_decks=40, note=None)


def _cluster(cluster_id: str, label: str, members: list[ClusterMember]) -> RegistryCluster:
    return RegistryCluster(
        id=cluster_id, label=label, members=tuple(members),
        au=None, height=None, bp_at_unit_scale=None, curated=False,
    )


def _registry(
    clusters: list[RegistryCluster],
    *,
    window_since: str | None = "2026-05-11",
    degraded: bool = False,
) -> SuperarchetypeRegistry:
    return SuperarchetypeRegistry(
        clusters=tuple(clusters),
        staples=(),
        unassigned=(),
        window_since=window_since,
        window_until=None,
        derived_at="2026-08-01T00:00:00+00:00",
        stability=0.95,
        cophenetic=0.9,
        degraded=degraded,
        reasons=(),
        seed=0,
        n_boot=200,
    )


@pytest.fixture
def combo_registry() -> SuperarchetypeRegistry:
    """One two-cluster registry: a combo family (B, C, D derived; A2 assigned) and a fair family
    (P, Q derived)."""
    return _registry([
        _cluster("sa-combo", "Combo", [
            _member("B"), _member("C"), _member("D"), _member("A2", "assigned"),
        ]),
        _cluster("sa-fair", "Fair", [_member("P"), _member("Q")]),
    ])


# ---------------------------------------------------------------------------
# ClusterView / registry consumption
# ---------------------------------------------------------------------------


class TestClusterView:
    def test_none_and_empty_registries_yield_no_view(self):
        assert cluster_view(None) is None
        assert cluster_view(_registry([])) is None

    def test_maps_cover_all_members_but_contributors_exclude_assignees(self, combo_registry):
        view = cluster_view(combo_registry)
        assert view is not None
        assert view.cluster_of == {
            "B": "sa-combo", "C": "sa-combo", "D": "sa-combo", "A2": "sa-combo",
            "P": "sa-fair", "Q": "sa-fair",
        }
        assert view.label_of == {"sa-combo": "Combo", "sa-fair": "Fair"}
        assert view.members["sa-combo"] == ("B", "C", "D", "A2")
        assert view.contributors["sa-combo"] == frozenset({"B", "C", "D"})
        assert view.cluster_ids == ("sa-combo", "sa-fair")

    def test_subject_base_resolves_camps_through_the_explicit_map(self):
        camp_parent = {"Doomsday [Murktide]": "Doomsday"}
        assert subject_base("Doomsday [Murktide]", camp_parent) == "Doomsday"
        assert subject_base("Delver", camp_parent) == "Delver"


class TestRegistryAuditLines:
    def test_windowed_registry_echoes_window_and_contributor_count(self, combo_registry):
        lines = registry_audit_lines(combo_registry, regime_start="2026-05-11")
        assert len(lines) == 1
        assert "2 clusters (5 contributors)" in lines[0]
        assert "window 2026-05-11..open" in lines[0]

    def test_full_corpus_registry_warns_exploratory(self, combo_registry):
        registry = _registry(list(combo_registry.clusters), window_since=None)
        lines = registry_audit_lines(registry, regime_start="2026-05-11")
        assert any("FULL-CORPUS registry" in line for line in lines)

    def test_stale_window_warns_mismatch(self, combo_registry):
        registry = _registry(list(combo_registry.clusters), window_since="2026-01-01")
        lines = registry_audit_lines(registry, regime_start="2026-05-11")
        assert any("predates the current regime start 2026-05-11" in line for line in lines)

    def test_degraded_registry_warns(self, combo_registry):
        registry = _registry(list(combo_registry.clusters), degraded=True)
        lines = registry_audit_lines(registry, regime_start=None)
        assert any("DEGRADED taxonomy" in line for line in lines)


# ---------------------------------------------------------------------------
# Era-windowed drawing
# ---------------------------------------------------------------------------

W1 = "2026-05-01"
W2 = "2026-06-01"


@pytest.fixture
def view(combo_registry):
    return cluster_view(combo_registry)


class TestDrawPoolTallies:
    def test_each_member_reads_its_own_pairwise_bucket(self, view):
        pooled_by_since = {
            None: {("S", "B"): (10, 20), ("S", "C"): (99, 99)},
            W2: {("S", "C"): (5, 12)},
        }
        valid_since = {"S": None, "B": None, "C": W2, "D": None}
        drawn = draw_pool_tallies(
            "S", "sa-combo", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            subject_cluster_id=None,
        )
        by_name = {t.archetype: t for t in drawn.tallies}
        assert (by_name["B"].wins, by_name["B"].n) == (10, 20)
        assert (by_name["C"].wins, by_name["C"].n) == (5, 12)  # W2 bucket, never the full one
        assert "D (no matches in window full)" in drawn.window_note

    def test_below_floor_member_is_named_not_silently_dropped(self, view):
        drawn = draw_pool_tallies(
            "S", "sa-combo", view,
            pooled_by_since={None: {("S", "B"): (10, 20)}},
            valid_since={"S": None, "B": None},  # C, D, A2 unresolved
            subject_cluster_id=None,
        )
        assert [t.archetype for t in drawn.tallies] == ["B"]
        assert "C (below the row floor — no resolved horizon)" in drawn.window_note

    def test_leave_opponent_out_excludes_the_opponent_member_entirely(self, view):
        pooled_by_since = {None: {("S", "B"): (10, 20), ("S", "C"): (10, 20)}}
        valid_since = {"S": None, "B": None, "C": None, "D": None}
        drawn = draw_pool_tallies(
            "S", "sa-combo", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            subject_cluster_id=None, exclude_opponent="B",
        )
        assert [t.archetype for t in drawn.tallies] == ["C"]

    def test_assignee_tally_is_drawn_with_definer_false(self, view):
        pooled_by_since = {None: {("S", "A2"): (3, 6), ("S", "B"): (10, 20)}}
        valid_since = {"S": None, "A2": None, "B": None, "C": None, "D": None}
        drawn = draw_pool_tallies(
            "S", "sa-combo", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            subject_cluster_id=None,
        )
        flags = {t.archetype: t.definer for t in drawn.tallies}
        assert flags == {"A2": False, "B": True}

    def test_intra_family_pool_flags_members_and_injects_the_self_mirror(self, view):
        pooled_by_since = {None: {("B", "C"): (8, 16), ("B", "D"): (7, 14)}}
        valid_since = {"B": None, "C": None, "D": None}
        drawn = draw_pool_tallies(
            "B", "sa-combo", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            subject_cluster_id="sa-combo", subject_mirror_n=10,
        )
        by_name = {t.archetype: t for t in drawn.tallies}
        assert by_name["B"].n == 10  # the injected self-mirror; estimator reports it as mirror_n
        assert all(t.intra_cluster for t in drawn.tallies)
        cell = aggregate_cluster_cell("B", "sa-combo", drawn.tallies)
        assert cell.mirror_n == 10
        assert cell.intra_cluster_share == pytest.approx((16 + 14 + 10) / (16 + 14 + 10))

    def test_camp_subject_never_injects_a_mirror(self, view):
        pooled_by_since = {None: {("B [X]", "C"): (8, 16)}}
        valid_since = {"B [X]": None, "C": None, "D": None}
        drawn = draw_pool_tallies(
            "B [X]", "sa-combo", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            subject_cluster_id="sa-combo", subject_mirror_n=0,
        )
        assert [t.archetype for t in drawn.tallies] == ["C"]

    def test_current_regime_share_reads_the_regime_bucket_for_older_windows(self, view):
        pooled_by_since = {
            None: {("S", "B"): (10, 20), ("S", "C"): (6, 12)},
            W1: {("S", "B"): (2, 5)},   # the regime-start bucket
            W2: {("S", "C"): (6, 12)},
        }
        valid_since = {"S": None, "B": None, "C": W2, "D": None}
        drawn = draw_pool_tallies(
            "S", "sa-combo", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            subject_cluster_id=None, regime_start=W1,
        )
        # B window is full -> current n read at the W1 bucket (5); C window W2 >= W1 -> fully
        # current (12). Share = (5 + 12) / (20 + 12).
        assert drawn.current_regime_share == pytest.approx((5 + 12) / (20 + 12))
        assert "member windows:" in drawn.window_note

    def test_empty_draw_has_no_share_and_names_everything(self, view):
        drawn = draw_pool_tallies(
            "S", "sa-fair", view,
            pooled_by_since={None: {}}, valid_since={"S": None, "P": None, "Q": None},
            subject_cluster_id=None,
        )
        assert drawn.tallies == ()
        assert drawn.current_regime_share is None
        assert "P (no matches" in drawn.window_note and "Q (no matches" in drawn.window_note


class TestDrawRowTallies:
    def test_split_parent_rows_sum_over_camps_within_the_member_bucket(self):
        pooled_by_since = {
            None: {("M [a]", "O"): (3, 7), ("M [b]", "O"): (2, 5), ("N", "O"): (4, 9)},
        }
        drawn, not_drawn = draw_row_tallies(
            ["M", "N"], "O",
            pooled_by_since=pooled_by_since,
            valid_since={"M": None, "N": None, "O": None},
            camps_of={"M": ("M [a]", "M [b]")},
        )
        assert drawn["M"][:2] == (5, 12)
        assert drawn["N"][:2] == (4, 9)
        assert not_drawn == []

    def test_unresolved_member_is_named(self):
        drawn, not_drawn = draw_row_tallies(
            ["M"], "O", pooled_by_since={None: {}}, valid_since={"O": None}, camps_of={},
        )
        assert drawn == {}
        assert not_drawn == ["M (below the row floor — no resolved horizon)"]


class TestDrawClusterPairTallies:
    def test_leaves_subject_and_opponent_out_and_skips_self_pairs(self, view):
        pooled_by_since = {
            None: {
                ("C", "P"): (5, 10), ("C", "Q"): (6, 10),
                ("D", "P"): (4, 10), ("D", "Q"): (5, 10),
                ("B", "P"): (9, 9),  # must NOT appear: B is the subject (leave-S-out)
            },
        }
        valid_since = {"B": None, "C": None, "D": None, "P": None, "Q": None}
        drawn = draw_cluster_pair_tallies(
            "B", "sa-combo", "sa-fair", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            camp_parent={}, camps_of={},
        )
        by_name = {t.archetype: (t.wins, t.n) for t in drawn.tallies}
        assert by_name == {"C": (11, 20), "D": (9, 20)}

    def test_opponent_member_left_out(self, view):
        pooled_by_since = {
            None: {("C", "P"): (5, 10), ("C", "Q"): (6, 10), ("D", "P"): (4, 10)},
        }
        valid_since = {"B": None, "C": None, "D": None, "P": None, "Q": None}
        drawn = draw_cluster_pair_tallies(
            "B", "sa-combo", "sa-fair", view,
            pooled_by_since=pooled_by_since, valid_since=valid_since,
            camp_parent={}, camps_of={}, exclude_opponent="Q",
        )
        by_name = {t.archetype: (t.wins, t.n) for t in drawn.tallies}
        assert by_name == {"C": (5, 10), "D": (4, 10)}

    def test_singleton_subject_family_draws_nothing(self, view):
        drawn = draw_cluster_pair_tallies(
            "P", "sa-fair", "sa-combo", view,
            pooled_by_since={None: {("Q", "B"): (5, 10)}},
            valid_since={"P": None, "Q": None, "B": None},
            camp_parent={}, camps_of={}, exclude_opponent=None,
        )
        # Q is the only other contributor; P excluded as subject — Q's tallies remain, so the
        # pool has ONE member and the estimator refuses it as "not a pool at all".
        assert [t.archetype for t in drawn.tallies] == ["Q"]
        cell = aggregate_cluster_cell("P", "sa-fair×sa-combo", drawn.tallies)
        assert cell.pooled_p is None
        assert "single-member cluster" in cell.refused_reason


# ---------------------------------------------------------------------------
# Rung resolution
# ---------------------------------------------------------------------------


def _flat(pairs: dict[tuple[str, str], tuple[int, int]]):
    return {None: pairs}


_ALL_NONE = {"S": None, "B": None, "C": None, "D": None, "P": None, "Q": None, "A2": None}


class TestRungPrior:
    def test_no_opponent_cluster_means_no_rung(self, view):
        assert rung_prior(
            "S", "Zed", view,
            pooled_by_since=_flat({}), valid_since=_ALL_NONE, camp_parent={}, camps_of={},
        ) is None

    def test_rung_1_admissible_yields_loo_prior_with_label_and_bounded_strength(self, view):
        pooled = _flat({
            ("S", "B"): (10, 20), ("S", "C"): (11, 20), ("S", "D"): (9, 20),
        })
        prior = rung_prior(
            "S", "B", view,
            pooled_by_since=pooled, valid_since=_ALL_NONE, camp_parent={}, camps_of={},
        )
        assert prior is not None and prior.rung == 1
        # LOO: B (the opponent) is excluded — the pool is C + D only.
        assert {s.archetype for s in prior.cell.member_split} == {"C", "D"}
        assert prior.source.startswith("superarchetype cell (leave-opponent-out; sa-combo, ")
        assert "m_eff 2.0" in prior.source and "I²=" in prior.source
        assert 5.0 <= prior.strength <= 30.0
        assert prior.mean == pytest.approx(prior.cell.pooled_p)

    def test_rung_1_gate_failure_falls_through_to_rung_2(self, view):
        # Opponent cluster sa-combo: S's tallies vs C/D diverge hard (0.9 vs 0.1 at n=20) ->
        # the spread guard refuses rung 1. Subject P's family sa-fair has Q as the only other
        # contributor -> rung 2 is a single-member pool -> refused too -> None. Then widen the
        # fair family to make rung 2 pass.
        pooled = _flat({
            ("P", "B"): (2, 4),
            ("P", "C"): (18, 20), ("P", "D"): (2, 20),
            ("Q", "C"): (10, 20), ("Q", "D"): (10, 20),
        })
        prior = rung_prior(
            "P", "B", view,
            pooled_by_since=pooled, valid_since=_ALL_NONE, camp_parent={}, camps_of={},
        )
        assert prior is None  # rung 1 refused; rung 2 single-member -> refused

        three_fair = _registry([
            _cluster("sa-combo", "Combo", [_member("B"), _member("C"), _member("D")]),
            _cluster("sa-fair", "Fair", [_member("P"), _member("Q"), _member("R")]),
        ])
        view3 = cluster_view(three_fair)
        pooled3 = _flat({
            ("P", "C"): (18, 20), ("P", "D"): (2, 20),
            ("Q", "C"): (10, 20), ("Q", "D"): (10, 20),
            ("R", "C"): (11, 20), ("R", "D"): (10, 20),
        })
        prior3 = rung_prior(
            "P", "B", view3,
            pooled_by_since=pooled3,
            valid_since={**_ALL_NONE, "R": None},
            camp_parent={}, camps_of={},
        )
        assert prior3 is not None and prior3.rung == 2
        assert prior3.source.startswith("cluster × cluster (leave-S-out, leave-O-out; sa-fair×sa-combo, ")
        # Q and R contribute 40 each vs C+D (B is left out of the opponent side).
        assert {s.archetype for s in prior3.cell.member_split} == {"Q", "R"}
        assert {s.n for s in prior3.cell.member_split} == {40}

    def test_not_computable_heterogeneity_is_not_a_pass(self, view):
        # Two members at n < 5 each: pooled cell SERVES (labelled fallback) but the het band is
        # not-computable — an independent prior needs a positive verdict, so no rung.
        pooled = _flat({("S", "C"): (2, 3), ("S", "D"): (1, 4)})
        prior = rung_prior(
            "S", "B", view,
            pooled_by_since=pooled, valid_since=_ALL_NONE, camp_parent={}, camps_of={},
        )
        assert prior is None
        cell = aggregate_cluster_cell(
            "S", "sa-combo",
            [MemberTally("C", 2, 3), MemberTally("D", 1, 4)],
        )
        assert cell.pooled_p is not None  # served for display…
        assert cell.heterogeneity.band == "not-computable"  # …but never as a prior


class TestFamilyFirstKinds:
    def test_measured_verdict_is_anchor_first_everywhere(self):
        # The LOO harness (scripts/loo_ladder_harness.py, 2026-08-01) found every attribution
        # kind too thin at the preregistered floors AND the anchor winning the sensitivity
        # buckets — the hypothesis was not forced. Recalibration is a one-line change here.
        assert FAMILY_FIRST_KINDS == frozenset()


# ---------------------------------------------------------------------------
# Display-ladder resolution
# ---------------------------------------------------------------------------


def _license(granted: bool = True) -> ImputationLicense:
    return ImputationLicense(
        cluster_id="sa-fair", cols_evaluated=4, sig_divergent_cols=0,
        tau_profile=0.08, granted=granted,
        reason="license granted: 4 evaluable column(s)" if granted else "divergent profile",
    )


def _imputed(granted: bool = True):
    tallies = [MemberTally("P", 14, 25), MemberTally("Q", 13, 25)]
    return impute_cell(
        "S", "O", _license(granted=granted), tallies,
        window_note="member windows: full x2", current_regime_share=1.0,
    ), tallies


def _pooled_cell(n_each: int = 20):
    tallies = [
        MemberTally("B", n_each // 2, n_each),
        MemberTally("C", n_each // 2 + 1, n_each),
        MemberTally("D", n_each // 2 - 1, n_each),
    ]
    return aggregate_cluster_cell("S", "sa-combo", tallies)


class TestResolveLadder:
    def test_measured_cell_short_circuits(self):
        entry = resolve_ladder(
            "S", "O", measured_n=45, display_gate_n=30,
            opponent_cluster_id="sa-combo", pooled=None, imputed=None,
        )
        assert entry.kind == "measured"
        assert entry.token == "measured (n=45)"
        assert entry.reasons == ()

    def test_imputed_wins_over_pooled_as_the_finer_question(self):
        imputed, tallies = _imputed()
        assert imputed.p is not None
        entry = resolve_ladder(
            "S", "O", measured_n=4, display_gate_n=30,
            opponent_cluster_id="sa-combo", pooled=_pooled_cell(), imputed=imputed,
            imputed_tallies=tallies,
        )
        assert entry.kind == "imputed"
        assert entry.cluster_id == "sa-fair"
        assert entry.token == "imputed from sa-fair (2 sibs, pool n=50)"
        assert entry.reasons == ("measured cell below the display gate (n=4 < 30)",)
        assert [s.archetype for s in entry.sibling_split] == ["P", "Q"]

    def test_refused_imputation_falls_to_pooled_with_the_refusal_named(self):
        imputed, tallies = _imputed(granted=False)
        pooled = _pooled_cell()
        assert pooled.pooled_p is not None and pooled.n_eff >= 30
        entry = resolve_ladder(
            "S", "O", measured_n=0, display_gate_n=30,
            opponent_cluster_id="sa-combo", pooled=pooled, imputed=imputed,
            imputed_tallies=tallies,
        )
        assert entry.kind == "pooled"
        assert entry.token.startswith("pooled vs sa-combo (n_eff ")
        assert any(r.startswith("imputation refused: no license") for r in entry.reasons)
        assert entry.sibling_split  # the family-range display stays renderable

    def test_everything_refused_resolves_none_with_every_reason(self):
        imputed, tallies = _imputed(granted=False)
        thin_pooled = _pooled_cell(n_each=6)  # n_eff far below the display gate
        entry = resolve_ladder(
            "S", "O", measured_n=2, display_gate_n=30,
            opponent_cluster_id="sa-combo", pooled=thin_pooled, imputed=imputed,
            imputed_tallies=tallies,
        )
        assert entry.kind == "none"
        assert entry.token == "no displayable fallback"
        assert len(entry.reasons) == 3
        assert entry.reasons[0].startswith("measured cell below")
        assert entry.reasons[1].startswith("imputation refused")
        assert entry.reasons[2].startswith("pooled cell below the display gate")

    def test_no_registry_coverage_reasons_are_named(self):
        entry = resolve_ladder(
            "S", "O", measured_n=0, display_gate_n=30,
            opponent_cluster_id=None, pooled=None, imputed=None,
        )
        assert entry.kind == "none"
        assert "imputation not attempted: subject has no cluster in the registry" in entry.reasons
        assert "no pooled cell: opponent has no cluster in the registry" in entry.reasons

    def test_ladder_kind_vocabulary_is_closed(self):
        with pytest.raises(ValueError, match="must be one of"):
            LadderEntry(
                subject="S", opponent="O", kind="blended", cluster_id=None,
                token="", reasons=(),
            )


# ---------------------------------------------------------------------------
# DB-freeness tripwire (same spirit as test_no_rounds.py's source scan, AST-precise)
# ---------------------------------------------------------------------------


class TestChainStaysDbFree:
    def test_chain_never_imports_duckdb_or_registry_at_runtime(self):
        """Registry types may appear only under TYPE_CHECKING; duckdb never — the kernel takes
        plain dicts so it stays unit-testable without a DB (objective-search-split)."""
        import legacy_engine.analytics.superarchetype.chain as chain_module

        tree = ast.parse(Path(chain_module.__file__).read_text())
        exempt: set[int] = set()
        for node in tree.body:
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Name)
                and node.test.id == "TYPE_CHECKING"
            ):
                for child in ast.walk(node):
                    exempt.add(id(child))
        offenders: list[str] = []
        for node in ast.walk(tree):
            if id(node) in exempt or not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            modules = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            offenders.extend(
                m for m in modules if "duckdb" in m or m.rsplit(".", 1)[-1] == "registry"
            )
        assert offenders == []
