"""Adversarial contracts for the exercised interval-consumption boundary."""

from datetime import UTC, date, datetime

import duckdb
import pytest

from legacy_engine.analytics import matchup as matchup_module
from legacy_engine.analytics.affectedness import exposure_boundary_authorities
from legacy_engine.analytics.eras.certificate_store import write_certification_run
from legacy_engine.analytics.eras.certification import (
    ContextOverlapEvidence,
    EquivalenceEvidence,
    HalfOpenInterval,
    PartitionManifest,
    SemanticGuardEvidence,
    SupportEvidence,
    payload_sha256,
)
from legacy_engine.analytics.eras.certification_run import (
    CERTIFICATION_FEATURE_ALLOWLIST,
    CertificationManifest,
    CertificationRun,
    EntityCertificationResult,
    EraCertificate,
    certification_run_identity,
)
from legacy_engine.analytics.eras.consume import (
    AnalysisClock,
    EligibilityAtom,
    EligibilitySourceRef,
    build_entity_eligibility,
    build_evidence_views,
    normalize_atoms,
)
from legacy_engine.analytics.eras.store import init_eras_schema
from legacy_engine.analytics.match_results import (
    PairEligibility,
    ResolvedMatch,
    SelectedMatch,
    resolve_match_records,
    select_pair_matches,
    selected_rows_for_pair,
)
from legacy_engine.advisory.best_call_evidence import build_report_evidence
from legacy_engine.ingestion.store import init_schema


_HISTORY = HalfOpenInterval(start=date(2026, 1, 1), end=date(2026, 2, 1))
_REFERENCE = HalfOpenInterval(start=date(2026, 3, 1), end=date(2026, 4, 1))


def _clock(*, mode="retrospective-current-model", knowledge=datetime(2026, 8, 1, tzinfo=UTC)):
    return AnalysisClock(
        data_until=date(2026, 4, 1), knowledge_as_of=knowledge, knowledge_mode=mode,
    )


def _atom(start, end, entity, segment):
    source = EligibilitySourceRef(source="scalar-current", entity=entity, segment_id=segment)
    return EligibilityAtom(component_id=segment, start=start, end=end, sources=(source,))


def _db():
    con = duckdb.connect(":memory:")
    init_schema(con)
    init_eras_schema(con)
    return con


def _insert_match(con, event_id, when, left, right, *, result="2-0", variants=(None, None)):
    con.execute(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [event_id, event_id, when.isoformat(), "", "Legacy", "mtgo", "online"],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [
            (event_id, 0, f"{event_id}-left", "", left, variants[0]),
            (event_id, 1, f"{event_id}-right", "", right, variants[1]),
        ],
    )
    con.execute(
        "INSERT INTO rounds VALUES (?, ?, ?, ?, ?)",
        [event_id, 0, f"{event_id}-left", f"{event_id}-right", result],
    )


def _insert_card(con, event_id, deck_idx, name):
    con.execute(
        "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
        [event_id, deck_idx, "main", name, 4],
    )


def _certificate(entity, *, status="certified", profile="promoted-v1", cert_id=None,
                 certification_as_of=date(2026, 4, 1)):
    partition = PartitionManifest(
        plan_id="held-out-v1", rule_sha256="1" * 64,
        discovery_event_ids_sha256="2" * 64,
        certification_event_ids_sha256="3" * 64,
        discovery_events=3, certification_events=3,
    )
    return EraCertificate(
        certificate_id=cert_id or f"cert-{entity}", entity=entity,
        candidate_id=f"candidate-{entity}", historical_segment_id=f"{entity}-history",
        reference_segment_id=f"{entity}-current", historical_interval=_HISTORY,
        reference_interval=_REFERENCE, certification_as_of=certification_as_of,
        discovery_run_id="discovery-exact", status=status, reasons=(),
        feature_schema_version="recurrent-certification-features-v1",
        calibration_profile_id=profile, partition=partition,
        semantic=SemanticGuardEvidence(
            disposition="pass", crossed_fact_ids=(), confirmed_veto_ids=(),
            unresolved_fact_ids=(), reasons=(),
        ),
        support=SupportEvidence(
            disposition="pass", candidate_decks=3, reference_decks=3,
            candidate_events=3, reference_events=3, time_buckets=3,
            effective_events=3.0, max_event_share=1 / 3, max_source_share=1.0,
            reasons=(),
        ),
        context_overlap=ContextOverlapEvidence(
            disposition="pass", effective_events=3.0, max_stabilized_weight=1.0,
            unsupported_reference_share=0.0, vocabulary_sha256="4" * 64, reasons=(),
        ),
        equivalence=EquivalenceEvidence(
            disposition="pass", family_id="family", method_id="bootstrap",
            family_alpha=0.05, bootstrap_replicates=399, critical_value=1.0,
            channels=(), reasons=(),
        ),
    )


def _run(
    entities=("A", "B", "C"), *, profile="promoted-v1",
    certificate_profile=None,
    status_by_entity=None, duplicate_entity=None,
    certification_as_of=date(2026, 4, 1),
    knowledge_available_at=datetime(2026, 4, 2, tzinfo=UTC),
):
    status_by_entity = status_by_entity or {}
    manifest = CertificationManifest(
        discovery_run_id="discovery-exact", discovery_results_sha256="5" * 64,
        certification_as_of=certification_as_of, certification_source_sha256="6" * 64,
        feature_schema_version="recurrent-certification-features-v1",
        calibration_profile_id=profile, calibration_sha256="7" * 64,
        partition_sha256="8" * 64, semantic_facts_sha256="9" * 64,
        format_observation_sha256=None,
        outcome_feature_allowlist=CERTIFICATION_FEATURE_ALLOWLIST, seed=17,
    )
    results = []
    for entity in entities:
        cert = _certificate(
            entity, status=status_by_entity.get(entity, "certified"),
            profile=certificate_profile or profile,
            certification_as_of=certification_as_of,
        )
        certificates = (cert, cert) if entity == duplicate_entity else (cert,)
        results.append(EntityCertificationResult(
            entity=entity, reference_segment_id=f"{entity}-current",
            reference_interval=_REFERENCE, discovery_status="candidate",
            candidate_id=f"candidate-{entity}", certificates=certificates, reasons=(),
        ))
    status = "complete"
    reasons = ()
    run_id = certification_run_identity(manifest, status, reasons)
    results_sha256 = payload_sha256([result.model_dump(mode="json") for result in results])
    return CertificationRun(
        run_id=run_id, manifest=manifest, results_sha256=results_sha256,
        status=status, reasons=reasons, results=tuple(results),
        knowledge_available_at=knowledge_available_at,
    )


def _matrix_db():
    con = _db()
    _insert_match(con, "ab-history", date(2026, 1, 10), "A", "B")
    _insert_match(con, "ab-gap", date(2026, 2, 10), "A", "B")
    _insert_match(con, "ab-current", date(2026, 3, 10), "B", "A")
    _insert_match(con, "ac-history", date(2026, 1, 12), "A", "C")
    _insert_match(con, "ac-current", date(2026, 3, 12), "A", "C")
    _insert_match(con, "bc-history", date(2026, 1, 14), "B", "C", result="0-2")
    _insert_match(con, "bc-current", date(2026, 3, 14), "B", "C", result="0-2")
    return con


def test_open_start_does_not_borrow_later_provenance():
    atoms = normalize_atoms((
        _atom(None, date(2020, 1, 1), "a", "open"),
        _atom(date(2021, 1, 1), date(2022, 1, 1), "a", "later"),
    ))
    assert [(atom.start, atom.end, tuple(source.segment_id for source in atom.sources)) for atom in atoms] == [
        (None, date(2020, 1, 1), ("open",)),
        (date(2021, 1, 1), date(2022, 1, 1), ("later",)),
    ]


def test_localized_exposure_authority_recovers_clean_pre_and_post_ban_history():
    con = _db()
    _insert_match(con, "before", date(2026, 6, 1), "A", "B")
    _insert_match(con, "exposed", date(2026, 6, 20), "A", "B")
    _insert_card(con, "exposed", 0, "The Fantasticar")
    _insert_match(con, "after", date(2026, 8, 11), "A", "B")
    bans = ((date(2026, 8, 10), "The Fantasticar", "banned"),)
    authority = exposure_boundary_authorities(con, ("A", "B"), ban_events=bans)
    assert authority["B"] == ()
    assert len(authority["A"]) == 1
    boundary = authority["A"][0]
    assert (
        boundary.clean_pre_exposure_end,
        boundary.contaminated_start,
        boundary.contaminated_end,
        boundary.clean_post_ban_start,
        boundary.provenance,
        boundary.materiality_scope,
        boundary.cards,
    ) == (
        date(2026, 6, 20),
        date(2026, 6, 20),
        date(2026, 8, 10),
        date(2026, 8, 10),
        "corpus-first-seen",
        "same-date-card-union",
        ("The Fantasticar",),
    )

    clock = AnalysisClock(
        data_until=date(2026, 8, 17),
        knowledge_as_of=datetime(2026, 8, 17, tzinfo=UTC),
        knowledge_mode="retrospective-current-model",
    )
    eligibility = build_entity_eligibility(
        con, "A", clock=clock, ban_events=bans,
    )
    assert [(atom.start, atom.end) for atom in eligibility.current] == [
        (date(2026, 8, 10), date(2026, 8, 17)),
    ]
    assert [(atom.start, atom.end) for atom in eligibility.expanded] == [
        (None, date(2026, 6, 20)),
        (date(2026, 8, 10), date(2026, 8, 17)),
    ]
    assert eligibility.status == "localized-expanded"
    assert any(reason.startswith("localized-ban-gap:The Fantasticar") for reason in eligibility.reasons)

    interval = matchup_module.build_interval_adaptive_matrix(
        con, clock=clock, certificate_run_id=None, min_row_share=0.0, ban_events=bans,
    )
    pair = interval.evidence[("A", "B")]
    assert pair.current_only.concentration.event_counts == {"after": 1}
    assert pair.certified_expanded.concentration.event_counts == {"before": 1, "after": 1}
    assert pair.added_history.concentration.event_counts == {"before": 1}
    assert "exposed" not in pair.certified_expanded.concentration.event_counts
    assert len(pair.certified_expanded.match_ids) == len(set(pair.certified_expanded.match_ids))
    assert set(pair.current_only.match_ids).isdisjoint(pair.added_history.match_ids)
    ledger_rows = selected_rows_for_pair(interval.selected_outcomes, "A", "B")
    assert len({(row.view, row.match.match_id) for row in ledger_rows}) == len(ledger_rows)
    report_pair = build_report_evidence(
        interval, None, authority_payload={"production": "unchanged"},
    ).pairs['["A","B"]']
    assert report_pair.best_available_basis == "localized-clean-direct"
    assert report_pair.best_available_direct.n == 2
    assert any(
        source.source == "localized-pre-exposure"
        and source.card == "The Fantasticar"
        and source.exposure_start == date(2026, 6, 20)
        and source.ban_date == date(2026, 8, 10)
        for component in report_pair.interval_components
        for source in component.sources
    )


def test_same_date_multi_card_materiality_emits_one_union_cohort_gap():
    con = _db()
    for index, when in enumerate((date(2026, 6, 1), date(2026, 6, 10), date(2026, 6, 20), date(2026, 7, 1))):
        event_id = f"event-{index}"
        _insert_match(con, event_id, when, "A", "B")
        if index == 1:
            _insert_card(con, event_id, 0, "Card One")
        if index == 2:
            _insert_card(con, event_id, 0, "Card Two")
    bans = (
        (date(2026, 8, 10), "Card One", "banned"),
        (date(2026, 8, 10), "Card Two", "banned"),
    )
    rows = exposure_boundary_authorities(
        con, ("A",), ban_events=bans, affect_threshold=0.4,
    )["A"]
    assert len(rows) == 1
    assert rows[0].cards == ("Card One", "Card Two")
    assert rows[0].contaminated_start == date(2026, 6, 10)
    assert rows[0].material_decks == 2
    assert rows[0].pre_ban_decks == 4
    assert rows[0].ban_event_inclusion_rate == 0.5


def test_selection_excludes_gap_and_keeps_pair_component_constant():
    subject = (
        _atom(date(2020, 1, 1), date(2020, 2, 1), "a", "a1"),
        _atom(date(2020, 3, 1), date(2020, 4, 1), "a", "a2"),
    )
    pair = PairEligibility("a", "b", subject, subject, _clock())
    rows = tuple(ResolvedMatch(
        f"m{i}", "e", event_date, "online", "a", "b", None, None, True,
    ) for i, event_date in enumerate((
        date(2020, 1, 2), date(2020, 1, 15), date(2020, 2, 15), date(2020, 3, 2),
    )))
    selected = select_pair_matches(rows, pair)
    assert [row.match.match_id for row in selected if row.view == "current-only"] == ["m0", "m1", "m3"]
    assert [row.match.match_id for row in selected if row.view == "certified-expanded"] == ["m0", "m1", "m3"]
    assert selected[0].pair_component_id == selected[1].pair_component_id


def test_views_partition_ids_and_use_leave_cell_out_hierarchy():
    target = tuple(SelectedMatch(
        ResolvedMatch(mid, mid, date(2026, 3, 1), "online", "a", "b", "p", "q", won),
        view, "pair", "a", "b", (), (),
    ) for view in ("current-only", "certified-expanded") for mid, won in (("m1", True), ("m2", True)))
    marginal = tuple(SelectedMatch(
        ResolvedMatch("m3", "m3", date(2026, 3, 2), "online", "a", "c", "p", "r", False),
        view, "pair-ac", "a", "c", (), (),
    ) for view in ("current-only", "certified-expanded"))
    views = build_evidence_views(
        "a", "b", target, clock=_clock(), hierarchy_rows=(*target, *marginal),
    )
    assert views.current_only.cell.prior_mean < 0.5
    assert views.current_only.cell.prior_mean != 1.0
    assert views.current_only.prior.prior_match_ids == ("m3",)
    assert set(views.current_only.match_ids).isdisjoint(views.current_only.prior.prior_match_ids)
    assert views.current_only.prior.overlap_n == 0
    with pytest.raises(ValueError, match="prior"):
        build_evidence_views(
            "a", "b", target, clock=_clock(), hierarchy_rows=(*target, *marginal),
            prior_match_ids=("m2",),
        )


def test_valid_exact_store_governs_reference_and_certified_history():
    con = _db()
    run = _run(("A",))
    write_certification_run(con, run)
    eligibility = build_entity_eligibility(
        con, "A", clock=_clock(), certificate_run_id=run.run_id,
    )
    assert [(atom.start, atom.end) for atom in eligibility.current] == [
        (_REFERENCE.start, _REFERENCE.end),
    ]
    source = eligibility.current[0].sources[0]
    assert (source.source, source.segment_id, source.certificate_run_id) == (
        "current-reference", "A-current", run.run_id,
    )
    history = [
        atom for atom in eligibility.expanded
        if any(ref.source == "certified-history" for ref in atom.sources)
    ]
    assert [(atom.start, atom.end) for atom in history] == [(_HISTORY.start, _HISTORY.end)]
    assert history[0].sources[0].certificate_id == "cert-A"


@pytest.mark.parametrize(
    ("run_kwargs", "clock", "reason"),
    [
        ({"profile": "profile-candidate"}, _clock(), "unpromoted-calibration-profile"),
        ({"knowledge_available_at": datetime(2026, 9, 1, tzinfo=UTC)}, _clock(), "knowledge-available-after-knowledge_as_of"),
        ({"status_by_entity": {"A": "rejected"}}, _clock(), "certificate-cert-A-status-rejected"),
        ({"certificate_profile": "other-promoted"}, _clock(), "certificate-cert-A-profile-mismatch"),
        ({"duplicate_entity": "A"}, _clock(), "certificate-cert-A-duplicate"),
        (
            {"certification_as_of": date(2026, 9, 1)},
            _clock(mode="as-known-then"),
            "certificate-cert-A-future-source-evidence",
        ),
    ],
)
def test_certificate_refusals_preserve_current_without_admitting_history(run_kwargs, clock, reason):
    con = _db()
    run = _run(("A",), **run_kwargs)
    write_certification_run(con, run)
    eligibility = build_entity_eligibility(con, "A", clock=clock, certificate_run_id=run.run_id)
    assert reason in eligibility.reasons
    assert not any(
        ref.source == "certified-history"
        for atom in eligibility.expanded for ref in atom.sources
    )


def test_missing_and_digest_invalid_runs_refuse_with_typed_reasons():
    con = _db()
    missing = build_entity_eligibility(con, "A", clock=_clock(), certificate_run_id="missing")
    assert "certificate-run-not-found" in missing.reasons
    unavailable = _run(("B",), profile="promoted-unavailable")
    write_certification_run(con, unavailable)
    without_result = build_entity_eligibility(
        con, "A", clock=_clock(), certificate_run_id=unavailable.run_id,
    )
    assert "certificate-result-not-found" in without_result.reasons
    run = _run(("A",))
    write_certification_run(con, run)
    con.execute(
        "UPDATE era_certification_runs SET results_sha256 = ? WHERE run_id = ?",
        ["0" * 64, run.run_id],
    )
    invalid = build_entity_eligibility(con, "A", clock=_clock(), certificate_run_id=run.run_id)
    assert "certificate-run-invalid" in invalid.reasons


def test_db_backed_matrix_excludes_gap_and_exposes_digest_bound_physical_ledger():
    con = _matrix_db()
    run = _run()
    write_certification_run(con, run)
    result = matchup_module.build_interval_adaptive_matrix(
        con, clock=_clock(), certificate_run_id=run.run_id, min_row_share=0.0,
    )
    ab = result.evidence[("A", "B")]
    ba = result.evidence[("B", "A")]
    assert (ab.current_only.cell.wins, ab.current_only.cell.n) == (0, 1)
    assert (ab.certified_expanded.cell.wins, ab.certified_expanded.cell.n) == (1, 2)
    assert ab.added_history.match_ids == tuple(
        set(ab.certified_expanded.match_ids) - set(ab.current_only.match_ids)
    )
    assert "ab-gap" not in ab.certified_expanded.concentration.event_counts
    assert ab.current_only.match_ids == ba.current_only.match_ids
    assert ab.current_only.cell.wins + ba.current_only.cell.wins == ab.current_only.cell.n
    assert len(result.selected_outcomes.content_sha256) == 64
    physical_ids = [row.match.match_id for row in result.selected_outcomes.rows]
    assert len(physical_ids) == len(set((row.view, row.match.match_id) for row in result.selected_outcomes.rows))
    assert all(row.match.subject < row.match.opponent for row in result.selected_outcomes.rows)
    assert selected_rows_for_pair(result.selected_outcomes, "A", "B")[0].match.match_id == selected_rows_for_pair(result.selected_outcomes, "B", "A")[0].match.match_id
    assert ab.certified_expanded.prior.prior_match_ids
    assert set(ab.certified_expanded.match_ids).isdisjoint(ab.certified_expanded.prior.prior_match_ids)


def test_directed_resolver_normalizes_reverse_and_excludes_unrelated_rows():
    con = _matrix_db()
    forward = resolve_match_records(con, subject="A", opponent="B")
    reverse = resolve_match_records(con, subject="B", opponent="A")
    assert {row.event_id for row in forward} == {"ab-history", "ab-gap", "ab-current"}
    assert {row.event_id for row in reverse} == {row.event_id for row in forward}
    assert {row.match_id for row in reverse} == {row.match_id for row in forward}
    assert all((row.subject, row.opponent) == ("A", "B") for row in forward)
    assert all((row.subject, row.opponent) == ("B", "A") for row in reverse)
    assert all(
        left.subject_won != next(right.subject_won for right in reverse if right.match_id == left.match_id)
        for left in forward
    )


def test_resolver_normalizes_timezone_timestamp_event_date_to_calendar_date():
    con = _db()
    _insert_match(
        con, "timestamp-event", datetime(2025, 7, 20, 9, 0, tzinfo=UTC), "A", "B",
    )

    records = resolve_match_records(con, subject="A", opponent="B")

    assert len(records) == 1
    assert records[0].event_date == date(2025, 7, 20)


def test_single_and_multi_split_pass_explicit_camp_parent_and_never_inherit_parent_certificate():
    con = _db()
    _insert_match(con, "px-old", date(2026, 1, 10), "P", "O", variants=("x", None))
    _insert_match(con, "px-now", date(2026, 3, 10), "P", "O", variants=("x", None))
    _insert_match(con, "py-now", date(2026, 3, 11), "P", "O", variants=("y", None))
    _insert_match(con, "qu-now", date(2026, 3, 12), "Q", "O", variants=("u", None))
    run = _run(("P", "Q", "O"))
    write_certification_run(con, run)
    single = matchup_module.build_interval_adaptive_matrix(
        con, clock=_clock(), certificate_run_id=run.run_id,
        split_variant="P", min_row_share=0.0,
    )
    multi = matchup_module.build_interval_adaptive_matrix(
        con, clock=_clock(), certificate_run_id=run.run_id,
        split_variants=("P", "Q"), min_row_share=0.0,
    )
    for label in ("P [x]", "P [y]"):
        single_eligibility = single.selected_outcomes.entity_eligibility[label]
        multi_eligibility = multi.selected_outcomes.entity_eligibility[label]
        assert single_eligibility.reasons == ("camp-current-only",)
        assert multi_eligibility.reasons == ("camp-current-only",)
        assert single_eligibility.current == single_eligibility.expanded
        assert multi_eligibility.current == multi_eligibility.expanded
        assert not single.evidence[(label, "O")].certified_expanded.certificate_ids
        assert single.evidence[(label, "O")].current_only.cell.n == multi.evidence[(label, "O")].current_only.cell.n
    assert multi.current.multi.camp_parent == {
        "P [x]": "P", "P [y]": "P", "Q [u]": "Q",
    }


def test_scalar_projection_is_typed_refusal():
    result = matchup_module.scalar_interval_projection((
        _atom(date(2020, 1, 1), date(2020, 2, 1), "a", "a1"),
        _atom(date(2020, 3, 1), date(2020, 4, 1), "a", "a2"),
    ))
    assert result.refused is True
    assert result.value is None
    assert result.reason == "disjoint-intervals-not-scalar"
