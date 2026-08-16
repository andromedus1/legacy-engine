"""Adversarial contracts for the exercised interval-consumption boundary."""

from datetime import UTC, date, datetime

import pytest
import duckdb

from legacy_engine.analytics.eras.consume import (
    AnalysisClock,
    EligibilityAtom,
    EligibilitySourceRef,
    build_evidence_views,
    normalize_atoms,
)
from legacy_engine.analytics.eras.store import init_eras_schema
from legacy_engine.analytics.match_results import (
    PairEligibility,
    ResolvedMatch,
    SelectedMatch,
    select_pair_matches,
)
from legacy_engine.analytics import matchup as matchup_module


def _clock() -> AnalysisClock:
    return AnalysisClock(data_until=date(2025, 1, 1), knowledge_as_of=datetime(2025, 2, 1, tzinfo=UTC), knowledge_mode="retrospective-current-model")


def _atom(start, end, entity, segment):
    source = EligibilitySourceRef(source="scalar-current", entity=entity, segment_id=segment)
    return EligibilityAtom(component_id=segment, start=start, end=end, sources=(source,))


def test_open_start_does_not_borrow_later_provenance():
    atoms = normalize_atoms((_atom(None, date(2020, 1, 1), "a", "open"), _atom(date(2021, 1, 1), date(2022, 1, 1), "a", "later")))
    assert [(atom.start, atom.end, tuple(source.segment_id for source in atom.sources)) for atom in atoms] == [
        (None, date(2020, 1, 1), ("open",)),
        (date(2021, 1, 1), date(2022, 1, 1), ("later",)),
    ]


def test_selection_excludes_gap_and_keeps_pair_component_constant():
    subject = (_atom(date(2020, 1, 1), date(2020, 2, 1), "a", "a1"), _atom(date(2020, 3, 1), date(2020, 4, 1), "a", "a2"))
    pair = PairEligibility("a", "b", subject, subject, _clock())
    rows = tuple(ResolvedMatch(f"m{i}", "e", event_date, "online", "a", "b", None, None, True) for i, event_date in enumerate((date(2020, 1, 2), date(2020, 1, 15), date(2020, 2, 15), date(2020, 3, 2))))
    selected = select_pair_matches(rows, pair)
    assert [row.match.match_id for row in selected if row.view == "current-only"] == ["m0", "m1", "m3"]
    assert [row.match.match_id for row in selected if row.view == "certified-expanded"] == ["m0", "m1", "m3"]
    assert len({row.match.match_id for row in selected if row.view == "current-only"}) == 3
    assert selected[0].pair_component_id == selected[1].pair_component_id


def test_views_partition_ids_and_reject_prior_overlap():
    rows = tuple(SelectedMatch(ResolvedMatch(mid, mid, date(2020, 2, 1), "online", "a", "b", "p", "q", True), "certified-expanded", "pair", "a", "b", ("c",), ("d",)) for mid in ("m1", "m2"))
    current = (SelectedMatch(rows[0].match, "current-only", "pair", "a", "b", ("c",), ("d",)),)
    views = build_evidence_views("a", "b", (*current, *rows), clock=_clock())
    assert set(views.current_only.match_ids) == {"m1"}
    assert set(views.added_history.match_ids) == {"m2"}
    assert views.certified_expanded.concentration.raw_n == 2
    assert views.current_only.cell.n == 1
    assert views.certified_expanded.cell.n == 2
    assert views.added_history.cell.n == 1
    with pytest.raises(ValueError, match="prior"):
        build_evidence_views("a", "b", (*current, *rows), clock=_clock(), prior_match_ids=("m2",))


def test_scalar_projection_is_typed_refusal():
    result = matchup_module.scalar_interval_projection((_atom(date(2020, 1, 1), date(2020, 2, 1), "a", "a1"), _atom(date(2020, 3, 1), date(2020, 4, 1), "a", "a2")))
    assert result.refused is True
    assert result.value is None
    assert result.reason == "disjoint-intervals-not-scalar"


def test_db_backed_unavailable_certificate_cannot_change_current():
    con = duckdb.connect(":memory:")
    init_eras_schema(con)
    con.execute("CREATE TABLE tournaments (id VARCHAR, date DATE, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, archetype VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, name VARCHAR)")
    from legacy_engine.analytics.eras.consume import build_entity_eligibility
    result = build_entity_eligibility(con, "a", clock=_clock(), certificate_run_id="missing-run")
    assert len(result.current) == 1
    assert "certificate-run-not-found" in result.reasons
    assert all(source.source != "current-reference" for source in result.current[0].sources)


def test_interval_matrix_returns_populated_evidence(monkeypatch):
    from types import SimpleNamespace
    from legacy_engine.analytics.eras.consume import EntityEligibility

    matrix = SimpleNamespace(archetypes=["a", "b"], cells={}, audit_preamble=())
    adaptive = SimpleNamespace(matrix=matrix, audit_preamble=())
    monkeypatch.setattr(matchup_module, "build_adaptive_matrix", lambda *args, **kwargs: adaptive)
    atom_a = _atom(date(2020, 1, 1), date(2021, 1, 1), "a", "a1")
    atom_b = _atom(date(2020, 1, 1), date(2021, 1, 1), "b", "b1")
    monkeypatch.setattr(
        "legacy_engine.analytics.eras.consume.build_entity_eligibility",
        lambda _con, entity, **_kwargs: EntityEligibility(entity=entity, current=(atom_a if entity == "a" else atom_b,), expanded=(atom_a if entity == "a" else atom_b,), certificate_run_id=None, clock=_clock(), status="current-only", reasons=()),
    )
    rows = tuple(ResolvedMatch(f"m{i}", f"e{i}", date(2020, 1, i + 2), "online", "a", "b", "p", "q", i != 1) for i in range(3))
    monkeypatch.setattr("legacy_engine.analytics.match_results.resolve_match_records", lambda *args, **kwargs: rows)
    def selected(records, pair):
        return tuple(SelectedMatch(record, view, "pair", "a1", "b1", (), ()) for view in ("current-only", "certified-expanded") for record in records)
    monkeypatch.setattr("legacy_engine.analytics.match_results.select_pair_matches", selected)
    result = matchup_module.build_interval_adaptive_matrix(object(), clock=_clock())
    assert ("a", "b") in result.evidence
    assert result.evidence[("a", "b")].current_only.cell.n == 3
    assert result.evidence[("a", "b")].certified_expanded.cell.n == 3
