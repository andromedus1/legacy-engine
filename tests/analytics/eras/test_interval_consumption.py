"""Adversarial contracts for the exercised interval-consumption boundary."""

from datetime import UTC, date, datetime

import pytest

from legacy_engine.analytics.eras.consume import (
    AnalysisClock,
    EligibilityAtom,
    EligibilitySourceRef,
    build_evidence_views,
    normalize_atoms,
)
from legacy_engine.analytics.match_results import (
    PairEligibility,
    ResolvedMatch,
    SelectedMatch,
    select_pair_matches,
)


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
