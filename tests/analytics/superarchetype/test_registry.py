"""Tests for the superarchetype registry: curated loader, merge, identity, churn, persistence."""

from __future__ import annotations

import json

import duckdb
import pytest

from legacy_engine.analytics.superarchetype.cluster import (
    ClusterMember,
    ClusterSolution,
    DerivedCluster,
    cluster_archetypes,
)
from legacy_engine.analytics.superarchetype.registry import (
    CuratedCluster,
    RegistryCluster,
    SuperarchetypeRegistry,
    init_superarchetype_schema,
    load_curated_superarchetypes,
    match_identities,
    membership_churn,
    merge_curated,
    read_derived_registry,
    read_superarchetype_members,
    rebuild_superarchetype_members,
    write_derived_registry,
)


@pytest.fixture
def make_solution():
    def _make(clusters=None, **kwargs):
        defaults = dict(
            clusters=tuple(clusters or ()),
            staples=("Brainstorm",),
            definers=("A", "B"),
            unassigned=(),
            stability=0.95,
            cophenetic=0.9,
            reasons=("baseline",),
            degraded=False,
            seed=0,
            n_boot=10,
        )
        defaults.update(kwargs)
        return ClusterSolution(**defaults)
    return _make


@pytest.fixture
def make_cluster():
    def _make(key, labels, *, au=0.99, height=0.3, bp=0.9):
        return DerivedCluster(
            key=key,
            label=" + ".join(labels),
            members=tuple(
                ClusterMember(archetype=a, provenance="derived", n_decks=40) for a in labels
            ),
            au=au, height=height, bp_at_unit_scale=bp,
        )
    return _make


@pytest.fixture
def make_registry():
    def _make(clusters, **kwargs):
        defaults = dict(
            clusters=tuple(clusters),
            staples=(),
            unassigned=(),
            window_since="2026-01-01",
            window_until="2026-06-30",
            derived_at="2026-07-31T00:00:00+00:00",
            stability=0.95,
            cophenetic=0.9,
            degraded=False,
            reasons=(),
            seed=0,
            n_boot=10,
        )
        defaults.update(kwargs)
        return SuperarchetypeRegistry(**defaults)
    return _make


@pytest.fixture
def registry_cluster():
    def _make(cluster_id, labels, *, curated=False):
        return RegistryCluster(
            id=cluster_id,
            label=" + ".join(labels),
            members=tuple(
                ClusterMember(
                    archetype=a, provenance="curated" if curated else "derived", n_decks=40
                )
                for a in labels
            ),
            au=None if curated else 0.99, height=None if curated else 0.3,
            bp_at_unit_scale=None if curated else 0.9, curated=curated,
        )
    return _make


class TestCuratedLoader:
    def _write(self, tmp_path, payload):
        path = tmp_path / "legacy.json"
        path.write_text(json.dumps(payload))
        return path

    def test_loads_a_valid_file(self, tmp_path):
        path = self._write(tmp_path, {
            "version": 1,
            "clusters": [{"id": "sa-x", "label": "Cheat", "archetypes": ["B", "A"]}],
        })
        loaded = load_curated_superarchetypes(path)
        assert loaded["sa-x"] == CuratedCluster(id="sa-x", label="Cheat", archetypes=("A", "B"))

    def test_the_shipped_file_parses(self):
        from legacy_engine.config import SUPERARCHETYPES_REGISTRY_PATH

        assert isinstance(load_curated_superarchetypes(SUPERARCHETYPES_REGISTRY_PATH), dict)

    @pytest.mark.parametrize(
        ("payload", "needle"),
        [
            ({"clusters": [{"label": "x", "archetypes": ["A"]}]}, "has no 'id'"),
            ({"clusters": [{"id": "sa-x", "archetypes": ["A"]}]}, "has no 'label'"),
            ({"clusters": [{"id": "sa-x", "label": "x", "archetypes": []}]}, "non-empty"),
            ({"clusters": [{"id": "sa-x", "label": "x"}]}, "non-empty"),
            ({"clusters": "nope"}, "must be a list"),
            ({"clusters": ["nope"]}, "must be an object"),
        ],
    )
    def test_fails_fast_citing_the_path(self, tmp_path, payload, needle):
        path = self._write(tmp_path, payload)
        with pytest.raises(ValueError) as exc:
            load_curated_superarchetypes(path)
        assert needle in str(exc.value)
        assert str(path) in str(exc.value)

    def test_duplicate_cluster_id_fails_fast(self, tmp_path):
        path = self._write(tmp_path, {"clusters": [
            {"id": "sa-x", "label": "one", "archetypes": ["A"]},
            {"id": "sa-x", "label": "two", "archetypes": ["B"]},
        ]})
        with pytest.raises(ValueError, match="duplicate cluster id"):
            load_curated_superarchetypes(path)

    def test_an_archetype_claimed_twice_fails_fast(self, tmp_path):
        path = self._write(tmp_path, {"clusters": [
            {"id": "sa-x", "label": "one", "archetypes": ["A"]},
            {"id": "sa-y", "label": "two", "archetypes": ["A"]},
        ]})
        with pytest.raises(ValueError, match="claimed by both"):
            load_curated_superarchetypes(path)

    def test_missing_file_raises_for_the_explicit_loader(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_curated_superarchetypes(tmp_path / "absent.json")


class TestMergeCurated:
    def test_curated_wins_by_key_and_records_what_it_replaced(
        self, make_solution, make_cluster
    ):
        solution = make_solution([make_cluster("A|B", ["A", "B"])])
        curated = {"sa-fam": CuratedCluster(id="sa-fam", label="Family", archetypes=("A", "C"))}
        registry = merge_curated(
            solution, curated, deck_counts={"A": 40, "B": 40, "C": 12},
            window_since=None, window_until=None, derived_at="now",
        )
        by_id = {c.id: c for c in registry.clusters}
        assert by_id["sa-fam"].curated is True
        assert {m.archetype for m in by_id["sa-fam"].members} == {"A", "C"}
        assert all(m.provenance == "curated" for m in by_id["sa-fam"].members)
        assert "derived assignment was A + B" in next(
            m.note for m in by_id["sa-fam"].members if m.archetype == "A"
        )
        assert "(unassigned)" in next(
            m.note for m in by_id["sa-fam"].members if m.archetype == "C"
        )
        # B survives in the derived cluster, which enters with no id yet.
        derived = [c for c in registry.clusters if not c.curated]
        assert [m.archetype for c in derived for m in c.members] == ["B"]

    def test_a_fully_claimed_derived_cluster_is_dropped_with_a_reason(
        self, make_solution, make_cluster
    ):
        solution = make_solution([make_cluster("A|B", ["A", "B"])])
        curated = {"sa-fam": CuratedCluster(id="sa-fam", label="F", archetypes=("A", "B"))}
        registry = merge_curated(
            solution, curated, deck_counts={}, window_since=None, window_until=None,
            derived_at="now",
        )
        assert [c.id for c in registry.clusters] == ["sa-fam"]
        assert any("dropped: every member claimed" in r for r in registry.reasons)

    def test_no_curated_entries_is_a_passthrough(self, make_solution, make_cluster):
        solution = make_solution([make_cluster("A|B", ["A", "B"])])
        registry = merge_curated(
            solution, {}, deck_counts={}, window_since=None, window_until=None, derived_at="now",
        )
        assert len(registry.clusters) == 1
        assert registry.clusters[0].curated is False
        assert [m.provenance for m in registry.clusters[0].members] == ["derived", "derived"]

    def test_curated_membership_removes_the_archetype_from_unassigned(
        self, make_solution, make_cluster
    ):
        solution = make_solution([make_cluster("A|B", ["A", "B"])], unassigned=(("Z", "thin"),))
        curated = {"sa-z": CuratedCluster(id="sa-z", label="Z fam", archetypes=("Z",))}
        registry = merge_curated(
            solution, curated, deck_counts={"Z": 3}, window_since=None, window_until=None,
            derived_at="now",
        )
        assert registry.unassigned == ()


class TestIdentity:
    def test_first_run_mints_sequential_ids(self, make_registry, registry_cluster):
        new = make_registry([
            RegistryCluster(id="", label="A + B", members=registry_cluster("x", ["A", "B"]).members,
                            au=0.9, height=0.2, bp_at_unit_scale=0.8, curated=False),
            RegistryCluster(id="", label="C", members=registry_cluster("y", ["C"]).members,
                            au=None, height=None, bp_at_unit_scale=None, curated=False),
        ])
        resolved, notes = match_identities(new, None)
        assert [c.id for c in resolved.clusters] == ["sa-001", "sa-002"]
        assert len(notes) == 2

    def test_max_overlap_keeps_the_identity(self, make_registry, registry_cluster):
        previous = make_registry([registry_cluster("sa-001", ["A", "B", "C"])])
        new = make_registry([
            RegistryCluster(id="", label="A + B", members=registry_cluster("x", ["A", "B"]).members,
                            au=0.9, height=0.2, bp_at_unit_scale=0.8, curated=False),
        ])
        resolved, notes = match_identities(new, previous)
        assert [c.id for c in resolved.clusters] == ["sa-001"]
        assert any("kept identity" in n for n in notes)

    def test_an_unmatched_cluster_mints_a_fresh_id(self, make_registry, registry_cluster):
        previous = make_registry([registry_cluster("sa-001", ["A"])])
        new = make_registry([
            RegistryCluster(id="", label="Z", members=registry_cluster("x", ["Z"]).members,
                            au=None, height=None, bp_at_unit_scale=None, curated=False),
        ])
        resolved, notes = match_identities(new, previous)
        assert [c.id for c in resolved.clusters] == ["sa-002"]
        assert any("new cluster" in n for n in notes)
        assert any("retired" in n for n in notes)

    def test_one_previous_id_is_claimed_by_at_most_one_new_cluster(
        self, make_registry, registry_cluster
    ):
        previous = make_registry([registry_cluster("sa-001", ["A", "B", "C", "D"])])
        new = make_registry([
            RegistryCluster(id="", label="A + B + C", curated=False, au=0.9, height=0.2,
                            bp_at_unit_scale=0.8,
                            members=registry_cluster("x", ["A", "B", "C"]).members),
            RegistryCluster(id="", label="D", curated=False, au=None, height=None,
                            bp_at_unit_scale=None, members=registry_cluster("y", ["D"]).members),
        ])
        resolved, _notes = match_identities(new, previous)
        ids = [c.id for c in resolved.clusters]
        assert len(set(ids)) == 2
        assert "sa-001" in ids

    def test_curated_ids_are_never_remapped(self, make_registry, registry_cluster):
        previous = make_registry([registry_cluster("sa-001", ["A", "B"])])
        new = make_registry([registry_cluster("sa-curated", ["A", "B"], curated=True)])
        resolved, _notes = match_identities(new, previous)
        assert [c.id for c in resolved.clusters] == ["sa-curated"]


class TestChurn:
    def test_first_derivation_reports_no_comparison(self, make_registry, registry_cluster):
        churn = membership_churn(make_registry([registry_cluster("sa-001", ["A"])]), None)
        assert churn.agreement is None
        assert "no previous registry" in churn.note

    def test_identical_membership_is_full_agreement(self, make_registry, registry_cluster):
        registry = make_registry([
            registry_cluster("sa-001", ["A", "B"]), registry_cluster("sa-002", ["C", "D"]),
        ])
        churn = membership_churn(registry, registry)
        assert churn.agreement == pytest.approx(1.0)
        assert churn.moves == ()

    def test_a_move_is_reported_and_lowers_agreement(self, make_registry, registry_cluster):
        previous = make_registry([
            registry_cluster("sa-001", ["A", "B"]), registry_cluster("sa-002", ["C"]),
        ])
        new = make_registry([
            registry_cluster("sa-001", ["A"]), registry_cluster("sa-002", ["B", "C"]),
        ])
        churn = membership_churn(new, previous)
        assert churn.agreement is not None and churn.agreement < 1.0
        assert ("B", "sa-001", "sa-002") in churn.moves

    def test_arrivals_and_departures_are_named(self, make_registry, registry_cluster):
        previous = make_registry([registry_cluster("sa-001", ["A", "Gone"])])
        new = make_registry([registry_cluster("sa-001", ["A", "Fresh"])])
        churn = membership_churn(new, previous)
        assert churn.arrivals == ("Fresh",)
        assert churn.departures == ("Gone",)

    def test_too_few_shared_archetypes_declines_to_fabricate_agreement(
        self, make_registry, registry_cluster
    ):
        previous = make_registry([registry_cluster("sa-001", ["A"])])
        new = make_registry([registry_cluster("sa-001", ["A"])])
        churn = membership_churn(new, previous)
        assert churn.agreement is None
        assert "agreement undefined" in churn.note


class TestPersistence:
    def test_json_round_trip(self, tmp_path, make_registry, registry_cluster):
        registry = make_registry(
            [registry_cluster("sa-001", ["A", "B"]), registry_cluster("sa-002", ["C"], curated=True)],
            staples=("Brainstorm", "Ponder"),
            unassigned=(("Z", "thin"),),
            reasons=("one", "two"),
        )
        path = tmp_path / "nested" / "derived.json"
        write_derived_registry(registry, path)
        assert read_derived_registry(path) == registry

    def test_absent_json_reads_as_none(self, tmp_path):
        assert read_derived_registry(tmp_path / "absent.json") is None

    def test_duckdb_round_trip(self, tmp_path, make_registry, registry_cluster):
        registry = make_registry(
            [registry_cluster("sa-001", ["A", "B"]), registry_cluster("sa-002", ["C"], curated=True)],
            staples=("Brainstorm",),
            unassigned=(("Z", "thin"),),
            reasons=("one",),
        )
        con = duckdb.connect(str(tmp_path / "t.duckdb"))
        try:
            rebuild_superarchetype_members(con, registry)
            assert read_superarchetype_members(con) == registry
            # Rebuild is a full replace, never an append.
            rebuild_superarchetype_members(con, registry)
            assert read_superarchetype_members(con) == registry
        finally:
            con.close()

    def test_missing_table_reads_as_none(self, tmp_path):
        con = duckdb.connect(str(tmp_path / "empty.duckdb"))
        try:
            assert read_superarchetype_members(con) is None
        finally:
            con.close()

    def test_empty_schema_reads_as_none(self, tmp_path):
        con = duckdb.connect(str(tmp_path / "schema.duckdb"))
        try:
            init_superarchetype_schema(con)
            assert read_superarchetype_members(con) is None
        finally:
            con.close()

    def test_cluster_of_finds_and_declines_honestly(self, make_registry, registry_cluster):
        registry = make_registry([registry_cluster("sa-001", ["A", "B"])])
        assert registry.cluster_of("A").id == "sa-001"
        assert registry.cluster_of("Nope") is None


class TestProvenanceVocabulary:
    def test_unknown_provenance_fails_fast_naming_the_allowed_set(self):
        with pytest.raises(ValueError) as exc:
            ClusterMember(archetype="A", provenance="guessed", n_decks=1)
        assert "guessed" in str(exc.value)
        assert "['assigned', 'curated', 'derived']" in str(exc.value)


class TestEndToEndPure:
    def test_solution_merges_and_persists(self, tmp_path, two_family_corpus):
        solution = cluster_archetypes(two_family_corpus, seed=0, n_boot=20)
        registry = merge_curated(
            solution, {}, deck_counts={a: 40 for a in solution.definers},
            window_since="2026-01-01", window_until="2026-06-30", derived_at="now",
        )
        registry, _notes = match_identities(registry, None)
        path = tmp_path / "derived.json"
        write_derived_registry(registry, path)
        assert read_derived_registry(path) == registry
        assert all(c.id.startswith("sa-") for c in registry.clusters)
