#!/usr/bin/env python3
"""Refresh Deck Rankings as a self-contained, regenerable HTML report.

The decision projection uses one posterior per matchup, recency-weighted current
field shares, full-field performance, and the lowest non-mirror matchup mean.
Compatible clean history is admitted once per pair; evidence labels never gate
estimates. Frozen legacy metrics remain available to historical evaluators.

Run after ingestion, labeling, staged camps, and era certification:
    .venv/bin/python scripts/refresh_best_call_ranking.py

Runbook: docs/analysis/best-call-ranking.md
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
from hashlib import sha256
import json
import os
import tempfile
import time
from pathlib import Path

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_custom_field, build_transition_field
from legacy_engine.advisory.field_scenario import FieldScenario, load_field_scenario
from legacy_engine.advisory.best_call_evidence import (
    best_available_direct_view,
    build_report_evidence,
    canonical_json,
)
from legacy_engine.advisory.best_call_targets import (
    ReportDataAudit,
    ReportDataSectionAudit,
    ReportTarget,
    confirmed_bans_before,
    target_regime,
)
from legacy_engine.advisory.ranking_benchmark import BenchmarkEvaluationSummary, content_sha256
from legacy_engine.advisory.positioning import (
    _COVERAGE_RESTRICT_THRESHOLD,
    _DEFAULT_DRAWS,
    _PBEST_SUPPRESS_COVERAGE,
    _compute_data_coverage,
    ranking_evidence_payload,
    practical_recommendation_order,
    rank_decks,
)
from legacy_engine.advisory.ranking_changes import (
    RankingSnapshotError,
    compare_ranking_snapshots,
    ranking_snapshot,
)
from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.amplification import (
    build_interval_evidence_corpus,
    read_amplification_run,
)
from legacy_engine.analytics.eras.certificate_store import read_certification_run
from legacy_engine.analytics.eras.consume import AnalysisClock, clamp_pair_window
from legacy_engine.analytics.matchup import (
    DISPLAY_GATE_N,
    MatchupMatrix,
    build_adaptive_matrix,
    build_interval_adaptive_matrix,
    build_matrix,
    build_multi_split_adaptive,
    build_multi_split_matrix,
)
from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.analytics.strategy_plan import (
    StrategicPlanResult,
    aggregate_archetype_vs_plan_results,
    aggregate_strategic_plan_results,
    load_strategic_plan_registry,
)
from legacy_engine.analytics.superarchetype.aggregate import I2_ONE_SIDED_NOTE
from legacy_engine.analytics.superarchetype.registry import read_superarchetype_members
from legacy_engine.archetype.discovered import staged_split_parents
from legacy_engine.config import DUCKDB_PATH
from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.advisory.ranking_measurement import (
    LEAN_DRAWS,
    LEAN_PRECISION_SCALE,
    LEAN_SEED,
    LEAN_TEMPERATURE,
    GroundingCellState,
    RankingCellMeasurement,
    RankingCellSource,
    grounding_cell_states,
    measure_lean_agency,
    measure_ranking_row,
    measure_variant_row,
    methodology_variant_specs,
    plan_path_to_grounding,
    production_recommendation_order,
    rank_variant_rows,
    select_ranking_cell,
)
from legacy_engine.workflows.decision_refresh import RankingUtilitySummary, validate_ranking_utility
from legacy_engine.models.matchup import MatchupCell
from legacy_engine.confidence import tier_for_sample

TEMPLATE_PATH = Path(__file__).parent / "best_call_ranking_template.html"
DEFAULT_OUT = Path(__file__).parent.parent / "decks" / "deck-rankings.html"

# Fixed MC seed so the cross-camp P(best) column is reproducible run-to-run on the same
# corpus (rank_decks is deterministic under a fixed seed; a refresh changes numbers only
# because the DATA changed, never because the sampler did).
RANK_SEED = 20260731


def benchmark_validation_payload(summary_path: Path | None) -> dict[str, str | None]:
    """Load reviewed benchmark evidence or expose the honest not-run default."""
    if summary_path is None:
        return {
            "status": "not-run", "artifact_id": None, "protocol_hash": None,
            "reason": "no benchmark summary artifact supplied to page generation",
        }
    summary = BenchmarkEvaluationSummary.model_validate_json(summary_path.read_bytes())
    return {
        "status": summary.status, "artifact_id": content_sha256(summary),
        "protocol_hash": summary.protocol_hash,
        "reason": "; ".join(summary.reasons) if summary.reasons else None,
    }


def _atomic_write_text(path: Path, text: str) -> None:
    """Write a complete sibling temporary file before atomically replacing *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _json_for_script(value: object, *, compact: bool = False) -> str:
    """Serialize JSON without permitting HTML/script parser breakouts."""
    separators = (",", ":") if compact else None
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=compact, separators=separators)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


class PublishedRankingPayloadError(ValueError):
    """Raised when an existing ranking page has a recognized but malformed payload."""


def read_published_ranking(path: Path) -> dict | None:
    """Read the embedded ranking object without executing the published HTML.

    A page from before the Deck Rankings payload was introduced has no recognized
    ``deck_rankings`` method and is treated as a baseline.  Once that marker is
    present, malformed JSON is surfaced to the comparison layer instead of being
    mistaken for a clean first publication.
    """
    if not path.is_file():
        return None
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PublishedRankingPayloadError(
            f"cannot read previous ranking page: {exc}"
        ) from exc
    marker = "const D ="
    position = html.find(marker)
    if position < 0:
        return None
    encoded = html[position + len(marker):].lstrip()
    try:
        payload, _end = json.JSONDecoder().raw_decode(encoded)
    except (json.JSONDecodeError, TypeError) as exc:
        raise PublishedRankingPayloadError(
            f"previous ranking payload JSON is malformed: {exc.msg if isinstance(exc, json.JSONDecodeError) else exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PublishedRankingPayloadError("previous ranking payload is not an object")
    meta = payload.get("meta")
    deck_rankings = meta.get("deck_rankings") if isinstance(meta, dict) else None
    if not isinstance(deck_rankings, dict) or not deck_rankings.get("method_id"):
        return None
    try:
        ranking_snapshot(payload)
    except RankingSnapshotError as exc:
        raise PublishedRankingPayloadError(
            f"previous ranking payload is not a valid snapshot: {exc}"
        ) from exc
    return payload


def _authority_payload(blob: dict) -> dict:
    """Return the complete mature ranking contract, excluding additive diagnostics/audits."""
    payload = {}
    for key, value in blob.items():
        if key in {"evidence", "report_target"}:
            continue
        if key in {"arch", "camps", "plans"}:
            payload[key] = [
                {
                    row_key: copy.deepcopy(row_value)
                    for row_key, row_value in row.items()
                    if row_key not in {
                        "diagnostic_evidence", "best_available_estimate", "decision",
                        "decision_units",
                    }
                }
                for row in value
            ]
        else:
            payload[key] = copy.deepcopy(value)
    meta = payload.get("meta", {})
    meta.pop("target_data_audit", None)
    meta.pop("evidence_audit", None)
    meta.pop("report_utility", None)
    meta.pop("deck_rankings", None)
    meta.pop("refresh_changes", None)
    meta.pop("decision_units", None)
    return payload


def current_report_target(
    db_path: Path, *, knowledge_as_of: dt.datetime | None = None,
) -> ReportTarget:
    """Resolve one exact current target without a latest-run alias.

    A single amplification artifact at the exact corpus cutoff may provide the full frozen clock.
    Otherwise a single certification artifact whose as-of equals that cutoff may enrich the direct
    path.  Multiple exact candidates are ambiguous and fail loudly; absent artifact tables are the
    normal typed direct-evidence path with ``certificate_run_id=None``.
    """

    supplied_knowledge = knowledge_as_of or dt.datetime.now(dt.UTC)
    if supplied_knowledge.tzinfo is None or supplied_knowledge.utcoffset() is None:
        raise ValueError("current report knowledge clock must be timezone-aware")
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        maximum = con.execute(
            "SELECT max(cast(substr(date,1,10) AS DATE)) FROM tournaments"
        ).fetchone()[0]
        if maximum is None:
            raise ValueError("current target requires a non-empty tournament corpus")
        cutoff = maximum + dt.timedelta(days=1)
        amplification_matches = []
        try:
            run_ids = tuple(
                row[0] for row in con.execute(
                    "SELECT run_id FROM amplification_runs ORDER BY run_id"
                ).fetchall()
            )
        except duckdb.CatalogException:
            run_ids = ()
        for run_id in run_ids:
            run = read_amplification_run(con, run_id)
            if run is not None and run.corpus.clock.data_until == cutoff:
                amplification_matches.append(run)
        if len(amplification_matches) > 1:
            raise ValueError(
                "multiple exact current amplification artifacts; pass an exact run id"
            )
        if amplification_matches:
            amplification = amplification_matches[0]
            if amplification.corpus.clock.knowledge_as_of > supplied_knowledge:
                raise ValueError("exact current amplification artifact is not yet knowledge-available")
            selected_knowledge = amplification.corpus.clock.knowledge_as_of
            certificate_run_id = amplification.corpus.certificate_run_id
            amplification_run_id = amplification.run_id
        else:
            try:
                cert_ids = tuple(
                    row[0] for row in con.execute(
                        "SELECT run_id FROM era_certification_runs WHERE as_of = ? ORDER BY run_id",
                        [cutoff],
                    ).fetchall()
                )
            except duckdb.CatalogException:
                cert_ids = ()
            certification_matches = []
            for run_id in cert_ids:
                run = read_certification_run(con, run_id)
                if (
                    run is not None
                    and run.knowledge_available_at is not None
                    and run.knowledge_available_at <= supplied_knowledge
                ):
                    certification_matches.append(run)
            if len(certification_matches) > 1:
                raise ValueError(
                    "multiple exact current certification artifacts; pass an exact run id"
                )
            certificate_run_id = (
                certification_matches[0].run_id if certification_matches else None
            )
            amplification_run_id = None
            selected_knowledge = supplied_knowledge
    finally:
        con.close()
    boundary, cards = target_regime(cutoff)
    return ReportTarget(
        target_id="current",
        label="Current",
        mode="current",
        mode_label="Current",
        data_until=None,
        effective_data_until=cutoff,
        knowledge_as_of=selected_knowledge,
        field_since=boundary,
        regime_card=cards[0],
        certificate_run_id=certificate_run_id,
        amplification_run_id=amplification_run_id,
    )


def _digest_rows(rows: object) -> str:
    return sha256(canonical_json(rows).encode()).hexdigest()


def _source_payload(con, *, since: str | None, until: str | None, cards: bool) -> dict:
    bounds = "(? IS NULL OR substr(t.date,1,10) >= ?) AND (? IS NULL OR substr(t.date,1,10) < ?)"
    params = [since, since, until, until]
    tournaments = con.execute(
        f"SELECT t.id, substr(t.date,1,10), t.provenance, t.format, t.source "
        f"FROM tournaments t WHERE {bounds} ORDER BY 1", params,
    ).fetchall()
    decks = con.execute(
        f"SELECT d.tournament_id, d.deck_idx, d.player, d.archetype, d.variant "
        f"FROM decks d JOIN tournaments t ON t.id=d.tournament_id "
        f"WHERE {bounds} ORDER BY 1,2", params,
    ).fetchall()
    rounds = con.execute(
        f"SELECT r.tournament_id, r.match_idx, r.player1, r.player2, r.result "
        f"FROM rounds r JOIN tournaments t ON t.id=r.tournament_id "
        f"WHERE {bounds} ORDER BY 1,2", params,
    ).fetchall()
    payload = {"tournaments": tournaments, "decks": decks, "rounds": rounds}
    if cards:
        payload["deck_cards"] = con.execute(
            f"SELECT dc.tournament_id, dc.deck_idx, dc.board, dc.name, dc.count "
            f"FROM deck_cards dc JOIN tournaments t ON t.id=dc.tournament_id "
            f"WHERE {bounds} ORDER BY 1,2,3,4", params,
        ).fetchall()
    return payload


def _section_audit(
    con, section: str, *, since: str | None, until: str | None, cards: bool = False,
) -> ReportDataSectionAudit:
    payload = _source_payload(con, since=since, until=until, cards=cards)
    max_row = con.execute(
        "SELECT max(cast(substr(date,1,10) AS DATE)) FROM tournaments "
        "WHERE (? IS NULL OR substr(date,1,10) >= ?) "
        "AND (? IS NULL OR substr(date,1,10) < ?)",
        [since, since, until, until],
    ).fetchone()
    return ReportDataSectionAudit(
        section=section,
        row_count=sum(len(rows) for rows in payload.values()),
        max_event_date=max_row[0] if max_row else None,
        input_sha256=_digest_rows(payload),
    )


def _report_data_audit(
    con,
    *,
    requested_until: str | None,
    effective_until: str,
    field_since: str,
    recent_since: str,
    interval_sha256: str | None = None,
) -> ReportDataAudit:
    sections = [
        _section_audit(con, "corpus", since=None, until=effective_until),
        _section_audit(con, "field", since=field_since, until=effective_until),
        _section_audit(con, "recent", since=recent_since, until=effective_until),
        _section_audit(con, "camps", since=field_since, until=effective_until),
        _section_audit(con, "matchups", since=None, until=effective_until),
        _section_audit(con, "plans", since=field_since, until=effective_until),
        _section_audit(
            con, "affectedness", since=None, until=effective_until, cards=True
        ),
    ]
    if interval_sha256 is not None:
        sections.append(
            ReportDataSectionAudit(
                section="interval-evidence",
                row_count=0,
                max_event_date=max((item.max_event_date for item in sections), default=None),
                input_sha256=interval_sha256,
            )
        )
    payload = {
        "requested_data_until": requested_until,
        "effective_data_until": effective_until,
        "sections": [item.model_dump(mode="json") for item in sections],
    }
    return ReportDataAudit(
        requested_data_until=dt.date.fromisoformat(requested_until)
        if requested_until
        else None,
        effective_data_until=dt.date.fromisoformat(effective_until),
        sections=tuple(sections),
        audit_sha256=_digest_rows(payload),
    )


def r4(x: float | None) -> float | None:
    return None if x is None else round(x, 4)


def horizon_text(h) -> str:
    if h is None:
        return "ban-only"
    return f"{h.source}: {h.trigger}" if h.trigger else h.source


def _typed_cell(cell, subject: str, opponent: str) -> MatchupCell:
    """Normalize legacy test doubles at the report boundary; production cells pass through."""
    if isinstance(cell, MatchupCell):
        return cell
    n = int(cell.n)
    raw = getattr(cell, "p_raw", None)
    return MatchupCell(
        archetype_a=subject,
        archetype_b=opponent,
        wins=round((raw or 0.0) * n),
        n=n,
        p_raw=raw,
        p_shrunk=getattr(cell, "p_shrunk", None),
        ci_low=getattr(cell, "ci_low", None),
        ci_high=getattr(cell, "ci_high", None),
        tier=getattr(cell, "tier", "speculative"),
        display=n >= DISPLAY_GATE_N,
        concentration=getattr(cell, "concentration", None),
    )


def make_cells(subj, field_opps, shares, ad_cells, fb_by_date, ban_since, ground_n,
               subj_ban=None, out_used=None, ad_windows=None, valid_since=None):
    """One row's cells vs every current-field opponent (mirror excluded).

    ``fb_by_date`` maps a window-start ISO date (or ``None`` = full corpus) to that
    window's ``MatchupMatrix`` cells. Each pair's fallback window starts at the later
    of the two decks' ban-affectedness dates (``subj_ban``/``ban_since[opp]``) — the
    Nadu rule: a banned engine's matches never blend into a fallback cell.

    ``out_used`` (optional): a dict this function populates ``{opp: MatchupCell}`` with
    the cell actually used per opponent — the cross-camp shared-field MC ranks on
    exactly these page-used cells, so its numbers share the ledger's window selection.
    """
    cells = []
    for opp in field_opps:
        if opp == subj:
            continue
        ec = ad_cells.get((subj, opp))
        fallback_window = clamp_pair_window(
            subj, opp, subject_since=subj_ban, opponent_since=ban_since.get(opp),
        )
        fb_date = fallback_window.effective_since
        fc = fb_by_date[fb_date].get((subj, opp)) if fb_date in fb_by_date else None
        ec = _typed_cell(ec, subj, opp) if ec is not None else None
        fc = _typed_cell(fc, subj, opp) if fc is not None else None
        fb_label = f"BA {fb_date}" if fb_date else "FC"
        era_since = (ad_windows or {}).get((subj, opp))
        era_window = clamp_pair_window(
            subj,
            opp,
            subject_since=(valid_since or {}).get(subj),
            opponent_since=(valid_since or {}).get(opp),
            requested_since=era_since if valid_since is None else None,
        )
        era_source = (
            RankingCellSource(
                kind="era", since=era_since, cell=ec,
                pair_window=era_window,
            ) if ec is not None else None
        )
        fallback_source = None
        if fc is not None:
            fallback_source = RankingCellSource(
                kind="ban-fallback" if fb_date else "full-corpus",
                since=fb_date,
                cell=fc,
                pair_window=fallback_window,
            )
        def with_concentration(source):
            if source is None:
                return None
            warning = select_ranking_cell(
                subj, opp, shares[opp], era=source, fallback=None, ground_n=1,
            ).concentration_warning
            return source.model_copy(update={"concentration_warning": warning})

        era_source = with_concentration(era_source)
        fallback_source = with_concentration(fallback_source)

        def canonical_source(source):
            if source is None:
                return None
            cell = source.cell.model_copy(update={
                name: r4(getattr(source.cell, name))
                for name in ("p_raw", "p_shrunk", "ci_low", "ci_high")
            })
            return source.model_copy(update={"cell": cell})

        era_source = canonical_source(era_source)
        fallback_source = canonical_source(fallback_source)
        measurement = select_ranking_cell(
            subj, opp, r4(shares[opp]), era=era_source, fallback=fallback_source, ground_n=ground_n,
        )
        use = measurement.selected.cell if measurement.selected is not None else None
        win = (
            "era" if measurement.selected_kind == "era" else fb_label
        )
        def source_payload(source, window):
            if source is None:
                return None
            cell = source.cell
            return {
                "p": r4(cell.p_shrunk), "raw": r4(cell.p_raw),
                "ci_low": r4(cell.ci_low), "ci_high": r4(cell.ci_high),
                "n": cell.n, "window": window, "tier": str(cell.tier),
                "concentration_warning": source.concentration_warning,
            }

        # Keep both candidates so the offline page can faithfully re-run the
        # era-preferred / ban-scoped-fallback selection at an interactive n gate.
        sources = {
            "era": source_payload(era_source, "era"),
            "fallback": source_payload(fallback_source, fb_label),
        }
        if use is None:  # pair absent from the matrix (e.g. camp vs its own parent)
            cells.append({"opp": opp, "share": r4(shares[opp]), "p": None, "raw": None,
                          "n": 0, "window": "era", "tier": "speculative", "measured": False,
                          "sources": sources, "ledger": measurement.model_dump(mode="json")})
            continue
        if out_used is not None:
            out_used[opp] = use
        cells.append({
            "opp": opp, "share": r4(shares[opp]), "p": r4(use.p_shrunk), "raw": r4(use.p_raw),
            "ci_low": r4(use.ci_low), "ci_high": r4(use.ci_high),
            "n": use.n, "window": win, "tier": str(use.tier),
            "measured": use.n >= ground_n,
            "sources": sources,
            "concentration_warning": measurement.concentration_warning,
            "ledger": measurement.model_dump(mode="json"),
        })
    return cells


def _split_json(split):
    """Per-member records behind a pooled/imputed/range lean (divergence-as-diagnostic)."""
    return [
        {"a": s.archetype, "w": s.wins, "n": s.n, "p": r4(s.p_hat),
         "tier": str(s.tier), "intra": s.intra_cluster}
        for s in split
    ]


def _sa_payload(subj, opp, msa, label_of):
    """One page-unmeasured cell's superarchetype fallback, or ``None`` (render as today).

    Ledger-only content: the caller attaches it as an ADDITIVE ``sa`` key and never touches
    the pre-existing cell fields, so adj/floor/agency/coverage/grounded/P(best) compute from
    bit-identical inputs whether the layer is on or off (the design's isolation decision).
    Kinds mirror the engine ladder: ``imputed`` (licensed family evidence, tau-widened CI),
    ``pooled`` (subject vs the opponent's whole family, engine display gate ``n_eff >= 30``),
    ``range`` (refused/unlicensed/vetoed: the member split ONLY — no point estimate).
    """
    entry = msa.ladder.get((subj, opp))
    if entry is None:
        return None
    imputed = msa.imputed_cells.get((subj, opp))
    pooled = (
        msa.cluster_cells.get((subj, entry.cluster_id))
        if entry.cluster_id is not None else None
    )

    if entry.kind == "imputed":
        if imputed is None:
            raise AssertionError(f"imputed ladder entry has no ImputedCell: {(subj, opp)!r}")
        lic = imputed.license
        return {
            "kind": "imputed",
            "p": r4(imputed.p), "ci_low": r4(imputed.ci_low), "ci_high": r4(imputed.ci_high),
            "pool_n": imputed.pool_n, "k": len(imputed.siblings),
            "family": label_of.get(lic.cluster_id, lic.cluster_id),
            "cluster_id": lic.cluster_id,
            "cur": r4(imputed.current_regime_share), "window_note": imputed.window_note,
            "license": lic.reason, "tau": r4(lic.tau_profile),
            # Imputation is licensed by a profile-level divergence test rather than a
            # per-cell Heterogeneity value, but the feature contract requires the same
            # one-sided evidence warning on every family-sourced point estimate. Import the
            # estimator's SSOT constant; never duplicate or parse display prose here.
            "one_sided_note": I2_ONE_SIDED_NOTE,
            "split": _split_json(entry.sibling_split),
            "reasons": list(entry.reasons),
        }

    if entry.kind == "pooled":
        if pooled is None:
            raise AssertionError(f"pooled ladder entry has no PooledCell: {(subj, opp)!r}")
        conc, het = pooled.concentration, pooled.heterogeneity
        # Serialize the TYPED verdict fields directly. ``PooledCell.provenance`` is display
        # prose, not a semantic contract, and can contradict refused/not-computable verdicts.
        return {
            "kind": "pooled",
            "p": r4(pooled.pooled_p), "ci_low": r4(pooled.ci_low), "ci_high": r4(pooled.ci_high),
            "n_eff": round(pooled.n_eff, 1), "tier": str(pooled.tier),
            "family": label_of.get(entry.cluster_id, entry.cluster_id),
            "cluster_id": entry.cluster_id,
            "m_eff": round(conc.m_eff, 2) if conc is not None else None,
            "concentration_passed": conc.passed if conc is not None else None,
            "concentration_label": conc.label if conc is not None else None,
            "i2": r4(het.i2) if het is not None else None,
            "i2_band": het.band if het is not None else None,
            "heterogeneity_note": het.note if het is not None else None,
            "heterogeneity_reason": het.reason if het is not None else None,
            "one_sided_note": het.one_sided_note if het is not None else None,
            "intra_share": r4(pooled.intra_cluster_share),
            "cur": r4(pooled.current_regime_share), "window_note": pooled.window_note,
            "split": _split_json(pooled.member_split),
            "reasons": list(entry.reasons),
        }

    # kind == "none": a family-range display when any split exists; nothing to add otherwise.
    # The named refusal comes from the TYPED fields (ImputedCell.reason /
    # PooledCell.refused_reason), never parsed out of display strings.
    if entry.sibling_split:
        # sibling_split rides an ATTEMPTED imputation (resolve_ladder attaches it only
        # then), so the family, refusal, and freshness come from the imputation side.
        if imputed is None:
            raise AssertionError(f"sibling split has no ImputedCell: {(subj, opp)!r}")
        fam_id = imputed.license.cluster_id
        reason = f"imputation refused: {imputed.reason}"
        cur = r4(imputed.current_regime_share)
        wnote = imputed.window_note
        split, source = entry.sibling_split, "siblings"
    elif pooled is not None and pooled.member_split:
        fam_id = entry.cluster_id
        if pooled.refused_reason is not None:
            reason = f"pooled cell refused: {pooled.refused_reason}"
        else:
            reason = (
                f"pooled cell below the engine display gate "
                f"(n_eff {pooled.n_eff:.0f} < {DISPLAY_GATE_N})"
            )
        cur = r4(pooled.current_regime_share)
        wnote = pooled.window_note
        split, source = pooled.member_split, "members"
    else:
        return None
    return {
        "kind": "range",
        "family": label_of.get(fam_id, fam_id) if fam_id else None,
        "cluster_id": fam_id,
        "source": source,
        "reason": reason,
        "cur": cur, "window_note": wnote,
        "one_sided_note": (
            pooled.heterogeneity.one_sided_note
            if pooled is not None and pooled.heterogeneity is not None else None
        ),
        "split": _split_json(split),
        "reasons": list(entry.reasons),
    }


def _floor_eligible(c) -> bool:
    """Every cell that clears the page's measured-evidence gate can set the floor."""
    return c["measured"]


def ranking_row_payload(row):
    """Stable report projection of the package-owned row measurement."""
    return {
        "adj": r4(row.adjusted_field_wr),
        "floor": r4(row.floor),
        "floor_opp": row.floor_opponent,
        "agency": r4(row.agency),
        "coverage": r4(row.measured_coverage),
        "grounded": row.grounded,
        "topk_ok": row.top_k_measured,
        "floor_observability": row.floor_observability.model_dump(mode="json"),
        "reconciliation": row.reconciliation.model_dump(mode="json"),
    }


def ranking_evidence_for_row(row, *, measured_share, resolved_cells):
    """Classify presence from the unrounded field share, never its display projection."""
    return ranking_evidence_payload(
        field_share=row["field_share_raw"],
        observed_field_share=row.get("observed_field_share"),
        decision_field_share=row.get("decision_field_share"),
        transition_prior=(
            row.get("observed_field_share", row["field_share_raw"]) <= 0
            and row.get("decision_field_share", row["field_share_raw"]) > 0
        ),
        measured_share=measured_share,
        resolved_cells=resolved_cells,
        grounded=row["grounded"],
    )


def row_stats(
    cells, top_k, cover_min, *, strict_common_sources=None, strict_common_since=None,
):
    measurements = []
    for cell in cells:
        if "ledger" in cell:
            measurements.append(RankingCellMeasurement.model_validate(cell["ledger"]))
            continue
        source = RankingCellSource(
            kind="era",
            since=None,
            pair_window=clamp_pair_window(
                "row", cell["opp"], subject_since=None, opponent_since=None,
            ),
            cell=MatchupCell(
                archetype_a="row", archetype_b=cell["opp"],
                wins=round(cell["p"] * cell["n"]), n=cell["n"],
                p_raw=cell["p"], p_shrunk=cell["p"], ci_low=None, ci_high=None,
                tier="speculative", display=cell["measured"],
            ),
        )
        measurements.append(RankingCellMeasurement(
            subject="row", opponent=cell["opp"], field_share=cell["share"],
            era=source, fallback=None, selected_kind="era", selected=source,
            selection_reason="legacy payload", measured=cell["measured"],
            concentration_warning=None,
        ))
    subject = measurements[0].subject if measurements else ""
    row = measure_ranking_row(
        subject,
        measurements,
        top_k=top_k,
        cover_min=cover_min,
        strict_common_sources=strict_common_sources or {},
        strict_common_since=strict_common_since,
    )
    return ranking_row_payload(row)


def _row_measurements(row) -> tuple[RankingCellMeasurement, ...]:
    return tuple(
        RankingCellMeasurement.model_validate(cell["ledger"])
        for cell in row["cells"]
    )


def methodology_payload(
    rows,
    *,
    peer_key: str,
    ground_n: int,
    top_k: int,
    cover_min: float,
    lean_draws: int = LEAN_DRAWS,
    lean_seed: int = LEAN_SEED,
):
    """Build immutable methodology diagnostics from canonical typed row ledgers."""
    specs = methodology_variant_specs(ground_n)
    variants_by_row = {}
    eligible_by_row = {}
    payload = {}
    for row in rows:
        label = row["subject"]
        measurements = _row_measurements(row)
        variants = {
            spec.id: measure_variant_row(
                measurements, spec=spec, top_k=top_k, cover_min=cover_min,
            )
            for spec in specs
        }
        canonical = variants["ci-gated"]
        expected = {
            "adj": r4(canonical.adjusted_field_wr),
            "floor": r4(canonical.floor),
            "agency": r4(canonical.agency),
            "coverage": r4(canonical.measured_coverage),
            "topk_ok": canonical.top_k_measured,
            "grounded": (
                canonical.top_k_measured and canonical.measured_coverage >= cover_min
            ),
        }
        actual = {key: row[key] for key in expected}
        if actual != expected:
            raise AssertionError(
                f"{peer_key} canonical methodology mismatch for {label!r}: "
                f"row={actual!r}, projection={expected!r}"
            )
        variants_by_row[label] = variants
        eligible_by_row[label] = {
            variant_id: ranking_evidence_payload(
                field_share=row["field_share_raw"],
                measured_share=variant.measured_coverage,
                resolved_cells=variant.resolved_cells,
                grounded=(
                    variant.top_k_measured
                    and variant.measured_coverage >= cover_min
                ),
            )["eligible"]
            for variant_id, variant in variants.items()
        }
        payload[label] = {
            "lean": measure_lean_agency(
                measurements, draws=lean_draws, seed=lean_seed,
            ).model_dump(mode="json"),
            "variants": {
                variant_id: variant.model_dump(mode="json")
                for variant_id, variant in variants.items()
            },
            "grounding": plan_path_to_grounding(
                grounding_cell_states(measurements),
                ground_n=ground_n, top_k=top_k, cover_min=cover_min,
            ).model_dump(mode="json"),
        }

    stability = rank_variant_rows(variants_by_row, eligible=eligible_by_row)
    for label, result in stability.items():
        payload[label]["stability"] = result.model_dump(mode="json")
    return payload


def plan_grounding_payload(plan, *, ground_n: int, top_k: int, cover_min: float):
    """Adapt direct external plan evidence to the shared rate-free planner."""
    states = tuple(
        GroundingCellState(
            opponent=cell["opponent"],
            field_share=cell["share"],
            era_n=cell["n"],
            fallback_n=cell["n"],
            measured=cell["measured"],
        )
        for cell in plan["cells"]
        if not cell["structural_same_plan"]
    )
    return plan_path_to_grounding(
        states, ground_n=ground_n, top_k=min(top_k, len(states)), cover_min=cover_min,
    ).model_dump(mode="json")


def build_strategic_plan_payload(
    result: StrategicPlanResult,
    archetype_rows,
    *,
    top_k: int,
    cover_min: float,
):
    """Adapt typed match-level plan results for the self-contained report."""
    by_subject = {row["subject"]: row for row in archetype_rows}
    assignments = {item.archetype: item for item in result.assignments}
    members_by_plan = {plan.id: [] for plan in result.plans}
    for archetype, row in by_subject.items():
        assignment = assignments[archetype]
        members_by_plan[assignment.primary].append({
            "archetype": archetype,
            "primary": assignment.primary,
            "secondary": list(assignment.secondary),
            "field_share": row["field_share"],
            "recent_4wk": row["recent_4wk"],
        })
    for members in members_by_plan.values():
        members.sort(key=lambda item: (-item["field_share"], item["archetype"]))

    shares = {
        plan_id: sum(member["field_share"] for member in members)
        for plan_id, members in members_by_plan.items()
    }
    out = []
    for plan in result.plans:
        external = []
        cells = []
        for opponent in result.plans:
            cell = result.cells[(plan.id, opponent.id)]
            share = shares[opponent.id]
            payload = {
                "opponent_id": opponent.id,
                "opponent": opponent.label,
                "share": r4(share),
                "wins": cell.wins,
                "losses": cell.losses,
                "n": cell.n,
                "observed_n": cell.observed_n,
                "mirror_n": cell.mirror_n,
                "raw": r4(cell.raw),
                "p": r4(cell.shrunk),
                "measured": cell.measured,
                "structural_same_plan": cell.structural_same_plan,
                "reason": (
                    "structural same-plan expectation"
                    if cell.structural_same_plan else
                    (None if cell.measured else
                     ("no decisive matches" if cell.n == 0 else
                     f"n={cell.n} below measured gate")
                    )
                ),
            }
            if not cell.structural_same_plan:
                external.append(payload)
            cells.append(payload)

        # Structural mirrors contribute exactly 50%; external cells contribute only
        # once measured.  Unmeasured magnitudes remain visible in the ledger, not metrics.
        weighted = [(shares[plan.id], 0.5)] + [
            (cell["share"], cell["p"]) for cell in external if cell["measured"]
        ]
        weight = sum(item[0] for item in weighted)
        adj = sum(w * p for w, p in weighted) / weight if weight else None
        measured = [cell for cell in external if cell["measured"]]
        floor_cell = min(measured, key=lambda cell: cell["p"]) if measured else None
        external_share = sum(cell["share"] for cell in external)
        coverage = sum(cell["share"] for cell in measured) / external_share if external_share else 0.0
        top = sorted(external, key=lambda cell: (-cell["share"], cell["opponent_id"]))[
            : min(top_k, len(external))
        ]
        grounded = bool(top) and all(cell["measured"] for cell in top) and coverage >= cover_min
        floor = floor_cell["p"] if floor_cell else None
        out.append({
            "id": plan.id,
            "label": plan.label,
            "description": plan.description,
            "field_share": r4(shares[plan.id]),
            "recent_4wk": sum(member["recent_4wk"] for member in members_by_plan[plan.id]),
            "adj": r4(adj),
            "floor": r4(floor),
            "floor_opp": floor_cell["opponent"] if floor_cell else None,
            "agency": r4(min(adj, floor)) if adj is not None and floor is not None else None,
            "coverage": r4(coverage),
            "grounded": grounded,
            "members": members_by_plan[plan.id],
            "cells": cells,
            "decisive_matches": result.decisive_matches,
            "same_plan_matches": result.same_plan_matches,
            "since": result.since,
            "until": result.until,
            "provenance": result.provenance,
        })
    return out


def build_family_payload(registry, cluster_cells, archetype_rows, *, top_k, cover_min):
    """Build the exploratory family hierarchy + S×S agency-map payload.

    The opponent-axis values are the engine's typed ``PooledCell`` outputs.  The subject axis is
    summarized across current-field member archetypes using their field shares; a refused or
    below-display-gate pool never becomes a number.  This payload is presentation-only and is not
    consumed by archetype Best Call, camp P(best), or their grounding strata.
    """
    if registry is None or not registry.clusters:
        return []

    def display_label(label):
        parts = label.split(" + ")
        if len(label) <= 56 or len(parts) <= 2:
            return label
        return f"{parts[0]} + {parts[1]} + {len(parts) - 2} more"

    by_subject = {row["subject"]: row for row in archetype_rows}
    clusters = []
    for cluster in registry.clusters:
        members = [
            by_subject[name] for name in cluster.archetypes
            if name in by_subject and by_subject[name]["field_share"] > 0
        ]
        share = sum(row["field_share"] for row in members)
        if not members or share <= 0:
            continue
        clusters.append((cluster, members, share))

    family_shares = {cluster.id: share for cluster, _members, share in clusters}
    total_family_share = sum(family_shares.values())
    out = []
    for cluster, members, share in clusters:
        leading = sorted(members, key=lambda row: (-row["field_share"], row["subject"]))[:3]
        leading_names = [row["subject"] for row in leading]
        if len(leading_names) == 1:
            anchors = leading_names[0]
        elif len(leading_names) == 2:
            anchors = " and ".join(leading_names)
        else:
            anchors = ", ".join(leading_names[:-1]) + f", and {leading_names[-1]}"
        origin = "curated strategy" if cluster.curated else "composition-derived"
        description = (
            f"A {origin} family anchored in the current field by {anchors}. "
            f"Its member archetypes represent {share:.1%} of published decks in this field window."
        )
        cells = []
        for opponent, _opponent_members, opponent_share in clusters:
            accepted = []
            refused = []
            for member in members:
                pooled = cluster_cells.get((member["subject"], opponent.id))
                if pooled is None:
                    refused.append(f"{member['subject']}: no pooled evidence")
                elif pooled.pooled_p is None:
                    refused.append(f"{member['subject']}: {pooled.refused_reason}")
                elif pooled.n_eff < DISPLAY_GATE_N:
                    refused.append(
                        f"{member['subject']}: n_eff {pooled.n_eff:.0f} < {DISPLAY_GATE_N}"
                    )
                else:
                    accepted.append((member["field_share"], pooled))

            accepted_weight = sum(weight for weight, _pooled in accepted)
            support = accepted_weight / share if share else 0.0
            p = (
                sum(weight * pooled.pooled_p for weight, pooled in accepted)
                / accepted_weight
                if accepted_weight else None
            )
            n_eff = sum(pooled.n_eff for _weight, pooled in accepted)
            current_weight = sum(
                weight * pooled.current_regime_share
                for weight, pooled in accepted
                if pooled.current_regime_share is not None
            )
            current_den = sum(
                weight for weight, pooled in accepted
                if pooled.current_regime_share is not None
            )
            window_notes = sorted({pooled.window_note or "unknown" for _weight, pooled in accepted})
            cells.append({
                "opponent_id": opponent.id,
                "opponent": display_label(opponent.label),
                "share": r4(opponent_share / total_family_share) if total_family_share else 0.0,
                "p": r4(p),
                "n_eff": r4(n_eff),
                "accepted_members": len(accepted),
                "subject_members": len(members),
                "support": r4(support),
                "intra_family": cluster.id == opponent.id,
                "current_regime_share": r4(current_weight / current_den) if current_den else None,
                "window_notes": window_notes,
                "refused_reason": "; ".join(refused) if not accepted else None,
                "support_reason": "; ".join(refused) if refused else None,
            })

        # A family explains its internal diversity in the map, but its decision floor is against
        # OTHER strategies (the epic's agency definition). The intra-family cell never ranks it.
        external = [cell for cell in cells if not cell["intra_family"]]
        measurable = [cell for cell in external if cell["p"] is not None]
        den = sum(cell["share"] for cell in external)
        coverage = sum(cell["share"] * cell["support"] for cell in measurable) / den if den else 0.0
        adj = (
            sum(cell["share"] * cell["support"] * cell["p"] for cell in measurable)
            / sum(cell["share"] * cell["support"] for cell in measurable)
            if measurable else None
        )
        floor_cell = min(measurable, key=lambda cell: cell["p"]) if measurable else None
        floor = floor_cell["p"] if floor_cell else None
        top = sorted(external, key=lambda cell: cell["share"], reverse=True)[:top_k]
        grounded = bool(top) and all(
            cell["p"] is not None and cell["support"] >= cover_min for cell in top
        ) and coverage >= cover_min
        vals = [value for value in (adj, floor) if value is not None]
        out.append({
            "id": cluster.id,
            "label": display_label(cluster.label),
            "full_label": cluster.label,
            "curated": cluster.curated,
            "description": description,
            "field_share": r4(share),
            "recent_4wk": sum(row["recent_4wk"] for row in members),
            "adj": r4(adj),
            "floor": r4(floor),
            "floor_opp": floor_cell["opponent"] if floor_cell else None,
            "agency": r4(min(vals)) if vals else None,
            "coverage": r4(coverage),
            "grounded": grounded,
            "members": [
                {
                    "archetype": member["subject"],
                    "field_share": member["field_share"],
                    "provenance": next(
                        registry_member.provenance
                        for registry_member in cluster.members
                        if registry_member.archetype == member["subject"]
                    ),
                }
                for member in members
            ],
            "cells": cells,
        })

    # Registry order is stable identity order; presentation order is current field share.
    out.sort(key=lambda family: (-family["field_share"], family["label"]))
    return out


def compute_blob(con, *, field_since, ground_n, top_k, cover_min, min_row_share,
                 regime_card, parents, superarchetypes=None, benchmark_validation=None,
                 data_until: str | None = None, ban_events=None,
                 include_plans: bool = True):
    date_clause = " where substr(date,1,10) < ?" if data_until else ""
    corpus_max = con.execute(f"select max(substr(date,1,10)) from tournaments{date_clause}", [data_until] if data_until else []).fetchone()[0]
    if corpus_max is None:
        raise ValueError("report target has no tournaments before data_until")
    current_4wk = (dt.date.fromisoformat(corpus_max) - dt.timedelta(days=28)).isoformat()
    corpus_decks, corpus_events = con.execute(
        "select (select count(*) from decks d join tournaments t on t.id=d.tournament_id "
        "where (? is null or substr(t.date,1,10) < ?)), "
        "(select count(*) from tournaments t where (? is null or substr(t.date,1,10) < ?))",
        [data_until, data_until, data_until, data_until],
    ).fetchone()
    field_events = con.execute(
        "select count(*) from tournaments where substr(date,1,10) >= ? "
        "and (? is null or substr(date,1,10) < ?)",
        [field_since, data_until, data_until],
    ).fetchone()[0]

    all_labels = [row[0] for row in con.execute(
        "select distinct d.archetype from decks d join tournaments t on t.id=d.tournament_id "
        "where d.archetype is not null and d.archetype <> '' "
        "and (? is null or substr(t.date,1,10) < ?) order by d.archetype",
        [data_until, data_until],
    ).fetchall()]
    ban_since = archetype_valid_since(con, all_labels, ban_events=ban_events)
    transition = build_transition_field(
        con,
        current_ban_since=field_since,
        until=data_until,
        affected_since=ban_since,
    )
    field_decks = transition.observed.deck_n
    shares = transition.shares
    recent = dict(con.execute(
        "select k.archetype, count(*) from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? and (? is null or substr(t.date,1,10) < ?) "
        "group by 1", [current_4wk, data_until, data_until]).fetchall())

    camp_win = con.execute(
        "select k.archetype, coalesce(nullif(k.variant,''),'unlabeled'), count(*) "
        "from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? and (? is null or substr(t.date,1,10) < ?) "
        "group by 1,2", [field_since, data_until, data_until]).fetchall()
    camp_recent = {(a, v): n for a, v, n in con.execute(
        "select k.archetype, coalesce(nullif(k.variant,''),'unlabeled'), count(*) "
        "from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? and (? is null or substr(t.date,1,10) < ?) "
        "group by 1,2", [current_4wk, data_until, data_until]).fetchall()}
    parent_win_tot: dict[str, int] = {}
    for a, _v, n in camp_win:
        parent_win_tot[a] = parent_win_tot.get(a, 0) + n
    camp_frac = {(a, v): n / parent_win_tot[a] for a, v, n in camp_win}
    camp_prior_frac: dict[tuple[str, str], float] = {}
    if transition.prior is not None:
        prior_rows = con.execute(
            "select k.archetype, coalesce(nullif(k.variant,''),'unlabeled'), count(*) "
            "from decks k join tournaments t on k.tournament_id=t.id "
            "where substr(t.date,1,10) >= ? and substr(t.date,1,10) < ? "
            "and (? is null or substr(t.date,1,10) < ?) group by 1,2",
            [transition.prior.since, field_since, data_until, data_until],
        ).fetchall()
        prior_tot: dict[str, int] = {}
        for a, _v, n in prior_rows:
            prior_tot[a] = prior_tot.get(a, 0) + n
        camp_prior_frac = {
            (a, v): n / prior_tot[a] for a, v, n in prior_rows if prior_tot.get(a, 0)
        }

    # ── Archetype level ──
    print("building archetype matrices...", flush=True)
    ad = build_adaptive_matrix(
        con, min_row_share=min_row_share, until=data_until, ban_events=ban_events,
    )
    rows = ad.matrix.archetypes
    field_opps = sorted((a for a in rows if shares.get(a, 0) > 0),
                        key=lambda a: shares[a], reverse=True)
    sh = {a: shares.get(a, 0.0) for a in [*rows, *field_opps]}
    # Fallback matrices, one per distinct ban-affectedness window (the Nadu rule) + true FC.
    fb_dates = {None} | {d for d in ban_since.values() if d}
    fb_by_date = {}
    for d in sorted(fb_dates, key=lambda x: x or ""):
        print(f"  fallback matrix since={d or 'full corpus'}...", flush=True)
        fb_by_date[d] = build_matrix(con, min_row_share=min_row_share, since=d, until=data_until).cells
    arch_out = []
    arch_used: dict[str, dict] = {}
    strict_arch_cache: dict[str | None, dict] = {}
    for i, subj in enumerate(rows):
        arch_used[subj] = {}
        cells = make_cells(subj, field_opps, sh, ad.matrix.cells, fb_by_date, ban_since,
                           ground_n, subj_ban=ban_since.get(subj), out_used=arch_used[subj],
                           ad_windows=ad.cell_windows, valid_since=ad.valid_since)
        strict_since = max(
            (window.effective_since for opp in field_opps
             if (window := clamp_pair_window(
                 subj, opp, subject_since=ad.valid_since.get(subj),
                 opponent_since=ad.valid_since.get(opp),
             )).effective_since is not None),
            default=None,
        )
        if strict_since not in strict_arch_cache:
            strict_arch_cache[strict_since] = build_matrix(
                con, min_row_share=min_row_share, since=strict_since, until=data_until,
            ).cells
        strict_sources = {
            opp: RankingCellSource(
                kind="strict-common-era", since=strict_since,
                cell=strict_arch_cache[strict_since][(subj, opp)],
                pair_window=clamp_pair_window(
                    subj, opp, subject_since=ad.valid_since.get(subj),
                    opponent_since=ad.valid_since.get(opp), requested_since=strict_since,
                ),
            )
            for opp in field_opps if (subj, opp) in strict_arch_cache[strict_since]
        }
        arch_out.append({
            "subject": subj, **row_stats(
                cells, top_k, cover_min, strict_common_sources=strict_sources,
                strict_common_since=strict_since,
            ),
            "since": ad.valid_since.get(subj),
            "horizon": horizon_text(ad.horizon_meta.get(subj)),
            "cells": cells,
            "field_share": r4(shares.get(subj, 0.0)),
            "field_share_raw": shares.get(subj, 0.0),
            "observed_field_share": (
                transition.observed.counts.get(subj, 0) / field_decks if field_decks else 0.0
            ),
            "decision_field_share": shares.get(subj, 0.0),
            "observed_count": transition.observed.counts.get(subj, 0),
            "prior_count": transition.effective_counts.get(subj, 0) - transition.observed.counts.get(subj, 0),
            "decision_share": shares.get(subj, 0.0),
            "field_evidence_kind": transition.kind,
            "recent_4wk": recent.get(subj, 0),
            "_idx": i,
        })
    print(f"  {len(arch_out)} archetype rows, {len(field_opps)} field opponents", flush=True)

    # ── Camp level: ONE multi-split pass over every staged parent ──
    # Camp cells are field-for-field identical to the per-parent split builds (the
    # engine's parity tests carry that guarantee); this is a batching win, not a
    # methodology change.
    t_camp = time.perf_counter()
    print(f"building multi-split matrices for {len(parents)} staged parents...", flush=True)
    msa = build_multi_split_adaptive(
        con, parents=parents, min_row_share=min_row_share, superarchetypes=superarchetypes,
        apply_superarchetype_priors=False,
        ban_events=ban_events,
        until=data_until,
    )
    camp_parent = msa.multi.camp_parent
    camp_labels = [s for s in msa.multi.subjects if s in camp_parent]
    # Fallback windows (the Nadu rule): each pair pools since max(parent_ban, opp_ban) —
    # camp labels inherit the parent's ban-affectedness date. One multi-split matrix per
    # DISTINCT date serves every parent's pairs at that date.
    camp_fb_dates = {
        clamp_pair_window(
            c, o, subject_since=ban_since.get(camp_parent[c]),
            opponent_since=ban_since.get(o),
        ).effective_since
        for c in camp_labels for o in field_opps
    }
    camp_fb = {}
    for d in sorted(camp_fb_dates, key=lambda x: x or ""):
        print(f"  multi-split fallback since={d or 'full corpus'}...", flush=True)
        camp_fb[d] = build_multi_split_matrix(
            con, parents=parents, min_row_share=min_row_share, since=d, until=data_until).cells
    t_rank = time.perf_counter()
    print(f"  camp matrices: {t_rank - t_camp:.1f}s ({len(camp_labels)} camp rows, "
          f"{len(camp_fb)} ban-scoped fallback windows)", flush=True)

    camps_out = []
    camp_used: dict[str, dict] = {}
    strict_camp_cache: dict[str | None, dict] = {}
    for parent in parents:
        p_ban = ban_since.get(parent)
        prefix = f"{parent} ["
        for lbl in (c for c in camp_labels if camp_parent[c] == parent):
            camp = lbl[len(prefix):-1]
            camp_used[lbl] = {}
            cells = make_cells(lbl, field_opps, sh, msa.multi.cells, camp_fb, ban_since,
                               ground_n, subj_ban=p_ban, out_used=camp_used[lbl],
                               ad_windows=msa.cell_windows, valid_since=msa.valid_since)
            strict_since = max(
                (window.effective_since for opp in field_opps
                 if (window := clamp_pair_window(
                     lbl, opp, subject_since=msa.valid_since.get(lbl),
                     opponent_since=msa.valid_since.get(opp),
                 )).effective_since is not None),
                default=None,
            )
            if strict_since not in strict_camp_cache:
                strict_camp_cache[strict_since] = build_multi_split_matrix(
                    con, parents=parents, min_row_share=min_row_share, since=strict_since, until=data_until,
                ).cells
            strict_sources = {
                opp: RankingCellSource(
                    kind="strict-common-era", since=strict_since,
                    cell=strict_camp_cache[strict_since][(lbl, opp)],
                    pair_window=clamp_pair_window(
                        lbl, opp, subject_since=msa.valid_since.get(lbl),
                        opponent_since=msa.valid_since.get(opp), requested_since=strict_since,
                    ),
                )
                for opp in field_opps if (lbl, opp) in strict_camp_cache[strict_since]
            }
            parent_prior_only = (
                transition.observed.counts.get(parent, 0) == 0
                and transition.effective_counts.get(parent, 0) > 0
            )
            current_frac = camp_frac.get((parent, camp), 0.0)
            frac = current_frac
            if parent_prior_only:
                frac = camp_prior_frac.get((parent, camp), 0.0)
            camp_row = {
                "subject": lbl, **row_stats(
                    cells, top_k, cover_min, strict_common_sources=strict_sources,
                    strict_common_since=strict_since,
                ),
                "since": msa.valid_since.get(lbl),
                "horizon": horizon_text(msa.horizon_meta.get(lbl)),
                "cells": cells,
                "parent": parent, "camp": camp,
                "field_share": r4(shares.get(parent, 0.0) * frac),
                "field_share_raw": shares.get(parent, 0.0) * frac,
                "camp_fraction_current": r4(current_frac),
                "camp_fraction_decision": r4(frac),
                "recent_4wk": camp_recent.get((parent, camp), 0),
                "_idx": len(camps_out),
            }
            camp_row.update({
                "observed_count": 0 if parent_prior_only else round(
                    transition.observed.counts.get(parent, 0) * frac
                ),
                "prior_count": (
                    transition.effective_counts.get(parent, 0)
                    - transition.observed.counts.get(parent, 0)
                ) if parent_prior_only else 0,
                "decision_share": shares.get(parent, 0.0) * frac,
                "field_evidence_kind": transition.kind,
            })
            camps_out.append(camp_row)

    if set(camp_used) != set(camp_labels):
        missing = sorted(set(camp_labels) - set(camp_used))
        unexpected = sorted(set(camp_used) - set(camp_labels))
        raise AssertionError(
            f"camp page-used ledger key mismatch: missing={missing!r}, unexpected={unexpected!r}"
        )

    arch_methodology = methodology_payload(
        arch_out, peer_key="archetype", ground_n=ground_n, top_k=top_k,
        cover_min=cover_min,
    )
    camp_methodology = methodology_payload(
        camps_out, peer_key="camp", ground_n=ground_n, top_k=top_k,
        cover_min=cover_min,
    )
    for row in arch_out:
        row["methodology"] = arch_methodology[row["subject"]]
        canonical = row["methodology"]["variants"]["ci-gated"]
        row["ranking_evidence"] = ranking_evidence_payload(
            field_share=row["field_share_raw"],
            observed_field_share=row.get("observed_field_share"),
            decision_field_share=row.get("decision_field_share"),
            transition_prior=(
                row.get("observed_field_share", row["field_share_raw"]) <= 0
                and row.get("decision_field_share", row["field_share_raw"]) > 0
            ),
            measured_share=canonical["measured_coverage"],
            resolved_cells=canonical["resolved_cells"],
                grounded=(
                    canonical["top_k_measured"]
                    and canonical["measured_coverage"] >= cover_min
                ),
        )
    for row in camps_out:
        row["methodology"] = camp_methodology[row["subject"]]

    # ── Cross-camp P(best): ONE shared-field MC over all camps + unsplit archetypes ──
    # Every candidate is scored against the same sampled parent-level Dirichlet field, so
    # P(best) is comparable across camps of DIFFERENT parents (the per-parent matrices
    # never were). The MC ranks on the PAGE-USED cells — the same era-preferred,
    # ban-scoped-fallback selection the ledger shows (raw era-windowed camp cells are
    # near-universally n<30, which would suppress the whole column as imputation noise).
    # Candidacy is gated by the SAME coverage threshold that gates display: a candidate
    # below _PBEST_SUPPRESS_COVERAGE has (near-)zero measured cells, its S is pure
    # imputation, and in the shared argmax such candidates spuriously absorb the entire
    # P(best) mass (observed: 100% of mass on suppressed rows when they are included) —
    # so they are excluded from candidacy, not just from display, and their rows carry
    # p_best=None with the coverage that explains why. A camp's cell vs its own parent
    # is absent by design and imputed by the MC — data_coverage counts that hole.
    field_counts = dict(transition.effective_counts)
    rank_field = build_custom_field(
        {o: shares[o] for o in field_opps},
        counts={o: field_counts[o] for o in field_opps},
    )
    split_set = set(msa.multi.parents)
    potential = [*camp_labels, *(o for o in field_opps if o not in split_set)]
    used_by_subject = {**arch_used, **camp_used}  # label sets are disjoint by construction
    if not set(potential) <= set(used_by_subject):
        raise AssertionError(
            f"ranking subjects missing page-used ledgers: {sorted(set(potential) - set(used_by_subject))!r}"
        )
    rank_cells = {
        (subj, opp): cell
        for subj in potential
        for opp, cell in used_by_subject.get(subj, {}).items()
    }
    rank_matrix = MatchupMatrix(
        cells=rank_cells, provenance=None, total_matches=ad.matrix.total_matches,
        archetypes=sorted({*potential, *field_opps}), caveat=ad.matrix.caveat,
    )
    coverage = {
        d: _compute_data_coverage(rank_matrix, rank_field, d, min_n=ground_n)
        for d in potential
    }
    row_by_subject = {row["subject"]: row for row in [*arch_out, *camps_out]}
    evidence = {}
    audit_warnings: list[str] = []
    for subject in potential:
        row = row_by_subject[subject]
        resolved = sum(cell.n >= 1 for cell in used_by_subject[subject].values())
        evidence[subject] = ranking_evidence_for_row(
            row,
            measured_share=coverage[subject],
            resolved_cells=resolved,
        )
        if resolved == 0:
            warning = (
                f"// [warn] ranking subject {subject}: no resolved page-used matchup cells; "
                "P(best)=n/a"
            )
            audit_warnings.append(warning)
            print(warning, flush=True)
    candidates = [d for d in potential if evidence[d]["eligible"]]
    ranking = rank_decks(
        rank_matrix,
        rank_field,
        candidates,
        coverage_min_n=ground_n,
        seed=RANK_SEED,
    )
    for subject in candidates:
        if abs(ranking.data_coverage[subject] - coverage[subject]) > 1e-12:
            raise AssertionError(
                f"ranking/page coverage mismatch for {subject!r}: "
                f"ranking={ranking.data_coverage[subject]:.12f}, page={coverage[subject]:.12f}"
            )
    for r in camps_out:
        lbl = r["subject"]
        ranked = lbl in ranking.p_best
        # Additive cross-camp columns (the pre-existing row fields are untouched).
        r["p_best"] = r4(ranking.p_best[lbl]) if ranked else None
        r["s_q"] = r4(ranking.s_quantile[lbl]) if ranked else None
        r["s_cov"] = r4(coverage[lbl])
        r["s_caveated"] = coverage[lbl] < _COVERAGE_RESTRICT_THRESHOLD
        r["ranking_evidence"] = evidence[lbl]
    inactive_count = sum(item["stratum"] == "inactive" for item in evidence.values())
    quarantined_count = sum(not item["eligible"] for item in evidence.values()) - inactive_count
    ranking_summary = (
        f"// ranking evidence: {len(candidates)} eligible, {inactive_count} inactive, "
        f"{quarantined_count} quarantined"
    )
    print(ranking_summary, flush=True)
    print(f"  shared-field ranking: {time.perf_counter() - t_rank:.1f}s "
          f"({len(candidates)} candidates, {_DEFAULT_DRAWS:,} draws)", flush=True)
    print(f"  camp sweep total: {time.perf_counter() - t_camp:.1f}s "
          f"({len(camps_out)} camp rows)", flush=True)

    # Strategic intent is a separate curated semantic layer.  Retrospective
    # parent-only evaluation explicitly disables it: a strategy-plan registry
    # is current composition knowledge, not an origin-local parent taxonomy.
    if include_plans:
        plan_registry = load_strategic_plan_registry()
        plan_matches = compute_match_results(con, since=field_since, until=data_until)
        plan_result = aggregate_strategic_plan_results(
            plan_matches,
            plan_registry,
            current_archetypes=[row["subject"] for row in arch_out],
            ground_n=ground_n,
            since=field_since,
        )
        archetype_plan_cells = aggregate_archetype_vs_plan_results(
            plan_matches,
            plan_registry,
            current_archetypes=[row["subject"] for row in arch_out],
            ground_n=ground_n,
        )
        assignment_by_archetype = {
            assignment.archetype: assignment for assignment in plan_registry.assignments
        }
        for row in arch_out:
            assignment = assignment_by_archetype[row["subject"]]
            row["strategic_plan"] = {
                "primary": assignment.primary,
                "secondary": list(assignment.secondary),
            }
            row["plan_cells"] = []
            for plan in plan_registry.plans:
                cell = archetype_plan_cells[(row["subject"], plan.id)]
                row["plan_cells"].append({
                    "opponent_id": plan.id,
                    "opponent": plan.label,
                    "wins": cell.wins,
                    "losses": cell.losses,
                    "mirror_n": cell.mirror_n,
                    "n": cell.n,
                    "raw": r4(cell.raw),
                    "p": r4(cell.shrunk),
                    "measured": cell.measured,
                    "same_primary_plan": plan.id == assignment.primary,
                    "since": field_since,
                    "provenance": plan_matches.provenance,
                })
        plans = build_strategic_plan_payload(
            plan_result, arch_out, top_k=top_k, cover_min=cover_min,
        )
        for plan in plans:
            plan["methodology"] = {
                "grounding": plan_grounding_payload(
                    plan, ground_n=ground_n, top_k=top_k, cover_min=cover_min,
                )
            }
    else:
        plan_registry = None
        plan_result = None
        plans = []
        for row in arch_out:
            row["strategic_plan"] = {"primary": None, "secondary": []}
            row["plan_cells"] = []

    production_order = production_recommendation_order({
        row["subject"]: (row["grounded"], row["recent_4wk"], row["agency"])
        for row in arch_out
    })
    practical_order = practical_recommendation_order({
        row["subject"]: row for row in arch_out if row.get("ranking_evidence")
    })
    supported_rows = sum(
        bool(row.get("ranking_evidence", {}).get("eligible")) for row in arch_out
    )
    grounded_rows = sum(
        row.get("ranking_evidence", {}).get("stratum") == "grounded" for row in arch_out
    )
    transition_prior_rows = sum(
        row.get("ranking_evidence", {}).get("stratum") == "transition-prior" for row in arch_out
    )
    utility_status = (
        "unavailable" if not supported_rows else
        "degraded" if grounded_rows < supported_rows else "useful"
    )
    utility_reasons: list[str] = []
    if grounded_rows < supported_rows:
        utility_reasons.append(
            f"{grounded_rows}/{supported_rows} supported rows are proof-grade grounded; "
            "practical lean remains available as a labeled lower-confidence view"
        )
    if not practical_order:
        utility_reasons.append("no supported row has a serialized posterior lean")
    utility = RankingUtilitySummary(
        observed_field_n=transition.observed.deck_n,
        effective_field_n=sum(transition.effective_counts.values()),
        prior_strength=transition.prior_strength,
        affected_clamp_count=sum(
            1 for horizon in ad.horizon_meta.values() if horizon.clamped_by_confirmed_ban
        ),
        supported_rows=supported_rows,
        transition_prior_rows=transition_prior_rows,
        grounded_rows=grounded_rows,
        practical_call=practical_order[0] if practical_order else None,
        proof_grade_call=production_order[0] if grounded_rows and production_order else None,
        rendered_shortlist_rows=0,
        status=utility_status,
        reasons=tuple(utility_reasons),
        practical_ranked_actions=practical_order,
    )
    validate_ranking_utility(utility)
    strategic_audit = (
        (
            f"// strategic plans: registry v{plan_registry.schema_version}, "
            f"{len(plan_registry.assignments)} assignments; "
            f"{plan_result.decisive_matches} decisive matches "
            f"({plan_result.same_plan_matches} same-plan), "
            f"{plan_result.omitted_matches} omitted; window since {field_since}",
            f"// archetype vs strategic plans: {len(arch_out)} archetypes × "
            f"{len(plan_registry.plans)} primary opponent plans from underlying decisive "
            "matches; archetype mirrors contribute structural 50% context",
        )
        if plan_registry is not None and plan_result is not None
        else ("// strategic plans: disabled for retrospective parent-only evaluation",)
    )

    blob = {
        "meta": {
            "field_since": field_since, "field_decks": field_decks,
            "observed_field_n": transition.observed.deck_n,
            "effective_field_n": sum(transition.effective_counts.values()),
            "prior_strength": transition.prior_strength,
            "field_evidence_kind": transition.kind,
            "transition_reason": transition.reason,
            "affected_clamp_count": sum(
                1 for horizon in ad.horizon_meta.values() if horizon.clamped_by_confirmed_ban
            ),
            "practical_recommendation": {
                "chosen_action": practical_order[0] if practical_order else None,
                "ranked_actions": list(practical_order),
                "basis": "existing posterior lean q25, then median, then label",
            },
            "ranking_utility": utility.model_dump(mode="json"),
            "regime_card": regime_card,
            "ground_n": ground_n, "top_k": top_k, "cover_min": cover_min,
            "min_row_share": min_row_share, "current_4wk": current_4wk,
            "corpus_max": corpus_max,
            "production_recommendation": {
                "chosen_action": production_order[0] if production_order else None,
                "ranked_actions": list(production_order),
                "basis": "shared grounded/current/Agency ordering",
            },
            "benchmark_validation": benchmark_validation or benchmark_validation_payload(None),
            # data-shape stats for the page's audit header (all counts, no method prose)
            "corpus_decks": corpus_decks, "corpus_events": corpus_events,
            "field_events": field_events, "field_archetypes": len(shares),
            "matches_total": ad.matrix.total_matches,
            # Cross-camp ranking parameters (the template's P(best) column reads these).
            "rank": {
                "seed": RANK_SEED, "n_draws": _DEFAULT_DRAWS,
                "quantile": ranking.quantile_level,
                "suppress_cov": _PBEST_SUPPRESS_COVERAGE,
                "caveat_cov": _COVERAGE_RESTRICT_THRESHOLD,
                "candidates": len(candidates), "potential": len(potential),
                "pbest_total": sum(ranking.p_best.values()),
                "camp_pbest_total": sum(
                    ranking.p_best.get(label, 0.0) for label in camp_labels
                ),
                "basis": "page-used cells (era preferred, ban-scoped fallback)",
            },
            "methodology": {
                "lean": {
                    "seed": LEAN_SEED,
                    "draws": LEAN_DRAWS,
                    "temperature": LEAN_TEMPERATURE,
                    "precision_scale": LEAN_PRECISION_SCALE,
                    "basis": "era preferred without n cliff; absent-era fallback; weak unresolved prior",
                    "authority": "diagnostic only; gated agency remains headline",
                },
                "variants": [spec.model_dump(mode="json") for spec in methodology_variant_specs(ground_n)],
            },
            "audit": [
                f"// multi-split: one pass over {len(parents)} staged parents — "
                f"{len(camp_labels)} camp rows, {len(camp_fb)} ban-scoped fallback windows",
                f"// cross-camp P(best): shared-field MC over {len(candidates)} of "
                f"{len(potential)} candidates (camps + unsplit archetypes with >= "
                f"{_PBEST_SUPPRESS_COVERAGE:.0%} measured coverage) on the page-used "
                f"cells, {_DEFAULT_DRAWS:,} draws, seed {RANK_SEED}",
                ranking_summary,
                *audit_warnings,
                f"// methodology diagnostics: posterior smooth floor, {LEAN_DRAWS:,} draws, "
                f"seed {LEAN_SEED}, temperature {LEAN_TEMPERATURE:.2f}, precision scale "
                f"{LEAN_PRECISION_SCALE:.0f}; raw / CI-gated / ban-scoped / era-only "
                "rank stability; gated agency remains authoritative",
                *strategic_audit,
            ],
        },
        "arch": arch_out,
        "camps": camps_out,
        "plans": plans,
    }
    return blob


def _publish_visible_best_estimates(
    blob: dict, *, parent_interval, camp_interval,
) -> None:
    """Publish direct useful estimates while keeping them outside ranking authority."""

    estimated_supported_rows = visible_cells = affected_cells = unaffected_cells = 0
    for is_camp, rows in ((False, blob["arch"]), (True, blob["camps"])):
        interval = camp_interval if is_camp else parent_interval
        for row in rows:
            cells = []
            for cell in row.get("cells", ()):
                if interval is None:
                    continue
                direct, basis = best_available_direct_view(
                    interval, row["subject"], cell["opp"],
                )
                if direct is not None and direct.cell is not None and direct.cell.n > 0:
                    cells.append((cell, direct, basis))
            denominator = sum(float(cell.get("share", 0.0)) for cell in row.get("cells", ()))
            measured_mass = sum(float(cell.get("share", 0.0)) for cell, _direct, _basis in cells)
            estimate = (
                sum(
                    float(cell.get("share", 0.0)) * float(direct.cell.p_shrunk)
                    for cell, direct, _basis in cells
                ) / measured_mass
                if measured_mass > 0 else None
            )
            direct_n = sum(int(direct.cell.n) for _cell, direct, _basis in cells)
            history_n = sum(
                int(interval.evidence[(row["subject"], cell["opp"])].added_history.cell.n)
                for cell, _direct, _basis in cells
            ) if interval is not None else 0
            bases = tuple(dict.fromkeys(basis for _cell, _direct, basis in cells))
            basis = (
                "localized-clean-direct" if "localized-clean-direct" in bases
                else "certified-direct" if "certified-direct" in bases
                else "current-direct" if "current-direct" in bases
                else "unavailable"
            )
            row["best_available_estimate"] = {
                "estimate": r4(estimate),
                "direct_match_n": direct_n,
                "added_history_n": history_n,
                "estimated_cells": len(cells),
                "total_cells": len(row.get("cells", ())),
                "field_coverage": r4(measured_mass / denominator) if denominator else 0.0,
                "basis": basis,
                "bases": list(bases),
                "confidence": tier_for_sample(direct_n),
                "proof_grade": bool(row.get("grounded")),
                "authority": "diagnostic-only",
            }
            if not is_camp:
                visible_cells += len(cells)
                affected_cells += sum(
                    basis == "localized-clean-direct"
                    for _cell, _direct, basis in cells
                )
                unaffected_cells += sum(
                    basis in {"current-direct", "certified-direct"}
                    for _cell, _direct, basis in cells
                )
                if row.get("ranking_evidence", {}).get("eligible") and estimate is not None:
                    estimated_supported_rows += 1

    current_ids = {
        row.match.match_id for row in parent_interval.selected_outcomes.rows
        if row.view == "current-only"
    }
    recovered_physical = len({
        row.match.match_id for row in parent_interval.selected_outcomes.rows
        if row.view == "certified-expanded" and row.match.match_id not in current_ids
    })
    # Some library callers supply a deliberately minimal authority projection
    # (for example, exact-run composition tests).  The per-row estimate is
    # still useful there, but a report-level utility statement requires the
    # generator's complete ranking-utility contract.
    raw = blob["meta"].get("ranking_utility")
    if raw is None:
        return
    supported = int(raw["supported_rows"])
    status = (
        "unavailable" if not supported
        else "useful" if estimated_supported_rows >= supported
        else "degraded"
    )
    utility = RankingUtilitySummary.model_validate({
        **raw,
        "estimated_rows": estimated_supported_rows,
        "visible_estimate_cells": visible_cells,
        "localized_history_matches": recovered_physical,
        "affected_estimate_cells": affected_cells,
        "unaffected_estimate_cells": unaffected_cells,
        "status": status,
        "reasons": (
            f"{estimated_supported_rows}/{supported} supported rows show a best available direct "
            f"estimate across {visible_cells} visible matchup cells",
            f"{raw['grounded_rows']}/{supported} supported rows are proof-grade grounded; proof "
            "remains separate from diagnostic usefulness",
        ),
    })
    validate_ranking_utility(utility)
    blob["meta"]["report_utility"] = utility.model_dump(mode="json")


REPORT_DIAGNOSTIC_OPPONENTS = 4


def _diagnostic_pair_keys(rows: list[dict], *, limit: int) -> set[tuple[str, str]]:
    """Bound detailed disclosure to supported rows' highest-share field opponents."""
    result = set()
    for row in rows:
        if not row.get("ranking_evidence", {}).get("eligible"):
            continue
        opponents = sorted(
            (
                cell for cell in row.get("cells", ())
                if cell["opp"] != row["subject"]
            ),
            key=lambda cell: (-float(cell.get("share", 0.0)), cell["opp"]),
        )
        result.update(
            (row["subject"], cell["opp"])
            for cell in opponents[:limit]
        )
    return result



def _publish_deck_rankings(
    con,
    blob,
    *,
    parent_interval=None,
    camp_interval=None,
    field_override: FieldDistribution | None = None,
    field_scenario: FieldScenario | None = None,
):
    """Project the current decision model after the frozen legacy evidence ledger."""
    from legacy_engine.advisory.deck_ranking_projection import project_ranking_rows
    from legacy_engine.advisory.recent_field import build_recent_field
    from legacy_engine.analytics.matchup import build_cell

    meta = blob["meta"]
    until = (dt.date.fromisoformat(meta["corpus_max"]) + dt.timedelta(days=1)).isoformat()
    recent = build_recent_field(con, since=meta["field_since"], until=until)
    # Exact prior pseudo-counts were already bounded and ban-filtered by the transition builder.
    prior_counts = {row["subject"]: row.get("prior_count", 0) for row in blob["arch"]}
    counts = dict(recent.effective_counts)
    for label, value in prior_counts.items():
        if value > 0:
            counts[label] = counts.get(label, 0.0) + value
    total = sum(counts.values())
    shares = {label: n / total for label, n in counts.items() if n > 0} if total else {}

    if field_override is not None and field_scenario is None:
        raise ValueError("field_override requires its validated field_scenario identity")

    def scenario_for_rows(key: str) -> FieldDistribution | None:
        """Map parent scenario shares onto camp rows without losing unknown mass."""
        if field_override is None:
            return None
        if key == "arch":
            return field_override
        camp_shares: dict[str, float] = {}
        camp_counts: dict[str, int] | None = {} if field_override.counts is not None else None
        for label, share in field_override.shares.items():
            camp_rows = [
                row for row in blob.get("camps", ())
                if row.get("parent") == label
            ]
            if not camp_rows:
                # Preserve a positive scenario mass when this taxonomy label
                # has no current camp breakdown.  Its cells will be explicit
                # weak priors rather than silently disappearing.
                camp_shares[label] = camp_shares.get(label, 0.0) + share
                if camp_counts is not None:
                    camp_counts[label] = field_override.counts.get(label, 0)
                continue
            fractions = recent.camp_fractions.get(label, {})
            allocated = 0.0
            for row in camp_rows:
                camp = row["camp"]
                fraction = float(fractions.get(camp, 0.0))
                camp_shares[camp] = camp_shares.get(camp, 0.0) + share * fraction
                allocated += fraction
                if camp_counts is not None:
                    parent_count = field_override.counts.get(label, 0)
                    camp_counts[camp] = camp_counts.get(camp, 0) + round(parent_count * fraction)
            if allocated < 1.0 - 1e-12:
                # The remainder is unknown camp composition and must stay in
                # the modeled field for floor/performance weighting.
                unknown = f"{label} (unmapped camp)"
                camp_shares[unknown] = camp_shares.get(unknown, 0.0) + share * (1.0 - allocated)
                if camp_counts is not None:
                    camp_counts[unknown] = max(1, round(field_override.counts.get(label, 0) * (1.0 - allocated)))
        no_data = frozenset(
            label for label in camp_shares
            if label in field_override.no_data or "(unmapped camp)" in label
        )
        return FieldDistribution(
            shares=camp_shares,
            field_source=field_override.field_source,
            counts=camp_counts,
            no_data=no_data,
            warnings=field_override.warnings,
            regime_currency=field_override.regime_currency,
        )

    def normalized(raw, row, source_notes, *, local_shares=None, global_presence=None):
        toughest = next((c for c in raw["cells"] if c["opponent"] == raw["worst_opponent"]), None)
        is_scenario = local_shares is not None
        scenario_share = float(local_shares.get(row["subject"], 0.0)) if is_scenario else raw["subject_field_share"]
        global_share = raw["subject_field_share"] if global_presence is None else float(global_presence.get(row["subject"], 0.0))
        result = {
            "performance": raw["performance"], "floor": raw["floor"],
            "performance_low": raw["performance_interval"][0],
            "performance_high": raw["performance_interval"][1],
            "floor_low": raw["floor_interval"][0] if raw["floor_interval"] else None,
            "floor_high": raw["floor_interval"][1] if raw["floor_interval"] else None,
            "worst_opponent": raw["worst_opponent"],
            "worst_low": toughest["ci_low"] if toughest else None,
            "worst_high": toughest["ci_high"] if toughest else None,
            "coverage": raw["nonmirror_coverage"],
            "field_share": scenario_share,
            "active": global_share > 0,
            "eligible": raw["eligible"],
            "pareto": raw["pareto"],
            "p_above_even": raw["p_performance_gt_0_5"],
            "bad_matchup_share": raw["bad_matchup_field_exposure"],
            "cells": [],
        }
        if is_scenario:
            result["scenario_field_share"] = scenario_share
            result["global_field_share"] = global_share
        for cell in raw["cells"]:
            if cell["is_mirror"]:
                continue
            result["cells"].append({
                "opponent": cell["opponent"], "share": cell["field_share"],
                "mean": cell["mean"], "low": cell["ci_low"],
                "high": cell["ci_high"], "wins": cell["wins"], "n": cell["n"],
                "prior_source": cell["prior_source"],
                "prior_mean": cell["prior_mean"], "prior_strength": cell["prior_strength"],
                "prior_strength_original": cell.get("prior_strength_original", cell["prior_strength"]),
                "prior_strength_effective": cell.get("prior_strength_effective", cell["prior_strength"]),
                "prior_contribution_fraction": cell.get("prior_contribution_fraction"),
                "source": source_notes.get((row["subject"], cell["opponent"]), cell["source_kind"]),
            })
        return result

    projection_inputs = {}
    scenario_comparisons: dict[str, dict[str, object]] = {}

    def projection_calls(projection):
        eligible = [
            row for row in projection["rows"].values()
            if row.get("eligible")
        ]
        performance = sorted(
            eligible,
            key=lambda row: (-row["performance"], row["subject"]),
        )
        floor = sorted(
            (row for row in eligible if row.get("floor") is not None),
            key=lambda row: (-row["floor"], -row["performance"], row["subject"]),
        )
        return {
            "performance": performance[0]["subject"] if performance else None,
            "floor": floor[0]["subject"] if floor else None,
        }

    for key, interval in (("arch", parent_interval), ("camps", camp_interval)):
        rows = blob[key]
        overrides, notes, override_identities, presence = {}, {}, {}, {}
        details = {}
        for row in rows:
            subject = row["subject"]
            if key == "camps":
                fraction = recent.camp_fractions.get(row["parent"], {}).get(row["camp"], 0.0)
                presence[subject] = shares.get(row["parent"], 0.0) * fraction
            else:
                presence[subject] = shares.get(subject, 0.0) if recent.exact_counts.get(subject, 0) else 0.0
            # Classifier residue is field mass, never a deck recommendation.
            if subject in {"Unknown", "Conflict"} or subject.startswith("Conflict("):
                presence[subject] = 0.0
            for cell in row["cells"]:
                source = cell.get("ledger", {}).get("era") or cell.get("ledger", {}).get("fallback")
                if source:
                    notes[(subject, cell["opp"])] = "since " + (source.get("since") or "full history")
            if interval is not None:
                interval_labels = dict(shares)
                if field_override is not None:
                    interval_labels.update(field_override.shares)
                for opponent in interval_labels:
                    if (subject, opponent) not in interval.evidence:
                        continue
                    direct, basis = best_available_direct_view(interval, subject, opponent)
                    if direct is not None and direct.cell is not None and direct.cell.n > 0:
                        overrides[(subject, opponent)] = direct.cell
                        notes[(subject, opponent)] = basis
                        from legacy_engine.analytics.match_results import intersect_pair_eligibility
                        pair = intersect_pair_eligibility(
                            interval.selected_outcomes.entity_eligibility[subject],
                            interval.selected_outcomes.entity_eligibility[opponent],
                        )
                        atoms = pair.expanded if direct.kind == "certified-expanded" else pair.current
                        admitted = set(direct.pair_component_ids)
                        ranges = [f"[{atom.start or 'start'}, {atom.end})" for atom in atoms if atom.component_id in admitted]
                        selected_views = interval.evidence[(subject, opponent)]
                        override_identities[(subject, opponent)] = {
                            "view": direct.kind,
                            "basis": basis,
                            "clock": selected_views.clock.model_dump(mode="json"),
                            "match_ids_sha256": direct.prior.observation_match_ids_sha256,
                            "match_n": len(direct.match_ids),
                            "pair_component_ids": list(direct.pair_component_ids),
                            "certificate_ids": list(direct.certificate_ids),
                            "windows": ranges,
                            "status": direct.status,
                            "concentration": (
                                direct.concentration.model_dump(mode="json")
                                if direct.concentration is not None else None
                            ),
                        }
                        concentration = direct.concentration
                        details[(subject, opponent)] = {
                            "intervals": ", ".join(ranges),
                            "concentration_warning": (
                                f"{concentration.max_event_share:.0%} from event {concentration.max_event_id}"
                                if concentration.max_event_share is not None and concentration.max_event_share >= .4 else None
                            ),
                        }
        row_field_override = scenario_for_rows(key)
        row_shares = row_field_override.shares if row_field_override is not None else shares
        if row_shares:
            row_measurements = {row["subject"]: _row_measurements(row) for row in rows}
            projection = project_ranking_rows(
                row_measurements,
                shares,
                field_override=row_field_override,
                counts=counts,
                candidate_presence=presence,
                cell_overrides=overrides,
                override_sources={k: notes[k] for k in overrides},
                override_identities=override_identities,
            )
            if row_field_override is not None:
                global_projection = project_ranking_rows(
                    row_measurements,
                    shares,
                    counts=counts,
                    candidate_presence=presence,
                    cell_overrides=overrides,
                    override_sources={k: notes[k] for k in overrides},
                    override_identities=override_identities,
                )
                scenario_comparisons[key] = {
                    "global": projection_calls(global_projection),
                    "scenario": projection_calls(projection),
                }
            for row in rows:
                row["decision"] = normalized(
                    projection["rows"][row["subject"]], row, notes,
                    local_shares=row_shares if row_field_override is not None else None,
                    global_presence=presence,
                )
                for cell in row["decision"]["cells"]:
                    cell.update(details.get((row["subject"], cell["opponent"]), {}))
                # Retain classifier residue visibly at its true field share, but ineligible.
                if row["subject"] in shares and presence[row["subject"]] == 0:
                    row["decision"]["field_share"] = (
                        row_shares.get(row["subject"], 0.0)
                        if row_field_override is not None else shares[row["subject"]]
                    )
                    row["decision"]["active"] = recent.exact_counts.get(row["subject"], 0) > 0
            projection_inputs[key] = {
                "rows": row_measurements,
                "shares": dict(shares),
                "counts": dict(counts),
                "candidate_presence": dict(presence),
                "cell_overrides": dict(overrides),
                # Keep this mapping aligned with cell_overrides.  The ranking
                # kernel rejects provenance labels for cells it was not given;
                # era/fallback notes for untouched cells belong to the report,
                # not to the evaluator handoff.
                "override_sources": {k: notes[k] for k in overrides},
                "override_identities": dict(override_identities),
                "field_override": row_field_override,
            }

    # Private handoff for the evaluator: the production projection has already
    # resolved interval overrides above, so a challenger can replay precisely
    # those typed inputs without duplicating publisher selection logic.
    blob["_deck_ranking_projection_inputs"] = projection_inputs

    # Strategy-plan cells are direct aggregates, not averages of archetype estimates.
    plans = blob.get("plans", [])
    plan_assignments = {
        m["archetype"] for p in plans for m in p.get("members", ())
    }
    scenario_unmapped = (
        tuple(sorted(label for label in field_override.shares if label not in plan_assignments))
        if field_override is not None else ()
    )
    plan_field_shares = field_override.shares if field_override is not None else shares
    plan_shares = {p["id"]: sum(plan_field_shares.get(m["archetype"], 0.0) for m in p["members"]) for p in plans}
    plan_counts = None
    if field_override is not None and field_override.counts is not None and not scenario_unmapped:
        plan_counts = {
            p["id"]: sum(field_override.counts.get(m["archetype"], 0) for m in p["members"])
            for p in plans
        }
    plan_cells = {}
    plan_labels = {p["id"]: p["label"] for p in plans}
    for plan in plans:
        for cell in plan["cells"]:
            if not cell["structural_same_plan"]:
                plan_cells[(plan["id"], cell["opponent_id"])] = build_cell(
                    plan["id"], cell["opponent_id"], cell["wins"], cell["n"],
                )
    if field_override is None and sum(plan_shares.values()) > 0:
        plan_projection = project_ranking_rows(
            {p["id"]: () for p in plans}, plan_shares, counts=plan_counts,
            cell_overrides=plan_cells,
        )
        for plan in plans:
            raw = plan_projection["rows"][plan["id"]]
            plan["decision"] = normalized(raw, {"subject": plan["id"]}, {})
            plan["decision"]["worst_opponent"] = plan_labels.get(raw["worst_opponent"], raw["worst_opponent"])
            for cell in plan["decision"]["cells"]:
                cell["opponent"] = plan_labels.get(cell["opponent"], cell["opponent"])
                cell["source"] = "since " + meta["field_since"]
    elif field_override is not None:
        reason = "unavailable: custom field plan cells lack a coherent composition-specific aggregate"
        if scenario_unmapped:
            reason += "; unmapped positive scenario mass: " + ", ".join(scenario_unmapped)
        for plan in plans:
            plan["decision"] = None
            plan["scenario_unavailable"] = reason

    eligible = [r for r in blob["arch"] if r.get("decision", {}).get("eligible")]
    ordered = sorted(eligible, key=lambda r: (-r["decision"]["performance"], r["subject"]))
    best = ordered[0] if ordered else None
    floor_candidates = [r for r in ordered if r["decision"]["floor"] is not None]
    floor_order = sorted(floor_candidates, key=lambda r: (-r["decision"]["floor"], -r["decision"]["performance"], r["subject"]))
    sources = ", ".join(f"{name}: {entry.exact_decks} lists" for name, entry in recent.source_breakdown.items())
    field_payload = {
        **recent.as_dict(), "shares": shares, "prior_counts": prior_counts,
        "description": f"Published-list field, {recent.half_life_days:g}-day recency half-life (provisional). "
            f"{recent.exact_observed_decks} observed lists; effective observed sample {recent.effective_sample_size:.0f}; "
            f"{sum(prior_counts.values())} historical pseudo-lists. Source coverage is not a census of entrants. {sources}",
    }
    if field_override is not None:
        field_payload.update({
            "shares": dict(field_override.shares),
            "counts": None if field_override.counts is None else dict(field_override.counts),
            "scenario": True,
            "description": (
                f"Scenario field: {field_scenario.label}; supplied field shares are used for "
                "posterior weighting. Global published-list observations remain separate."
            ),
            "global_shares": shares,
        })
    meta["deck_rankings"] = {
        "method_id": "deck-rankings-v1", "performance_call": best["subject"] if best else None,
        "floor_call": floor_order[0]["subject"] if floor_order else None,
        "performance_order": [r["subject"] for r in ordered],
        "floor_order": [r["subject"] for r in floor_order],
        "field": field_payload,
    }
    if field_scenario is not None:
        scenario_payload = field_scenario.model_dump()
        scenario_payload["global_observed_field"] = {
            "shares": dict(shares),
            "counts": dict(counts),
            "observed_lists": recent.exact_observed_decks,
        }
        scenario_payload["global_vs_scenario"] = scenario_comparisons
        meta["field_scenario"] = scenario_payload
    old_utility = meta.get("report_utility") or meta.get("ranking_utility")
    if old_utility is not None:
        # Update operational usefulness from the same decisions actually rendered above.
        visible_cells = [c for r in blob["arch"] for c in r.get("decision", {}).get("cells", []) if c["n"] > 0]
        visible = len(visible_cells)
        affected = sum(c["source"] == "localized-clean-direct" for c in visible_cells)
        utility = RankingUtilitySummary.model_validate({
            **old_utility, "supported_rows": len(eligible), "estimated_rows": len(eligible),
            "observed_field_n": recent.exact_observed_decks,
            "observed_field_ess": recent.effective_sample_size,
            "prior_strength": int(sum(prior_counts.values())),
            "effective_field_n": recent.exact_observed_decks + int(sum(prior_counts.values())),
            "grounded_rows": 0, "proof_grade_call": None, "transition_prior_rows": 0,
            "visible_estimate_cells": visible, "affected_estimate_cells": affected,
            "unaffected_estimate_cells": visible - affected,
            "practical_call": best["subject"] if best else None,
            "practical_ranked_actions": tuple(r["subject"] for r in ordered),
            "rendered_shortlist_rows": len({r["subject"] for r in (best, floor_order[0] if floor_order else None) if r}),
            "status": "useful" if eligible else "unavailable",
            "reasons": (f"{len(eligible)} supported performance/floor estimates; uncertainty is shown per row",),
        })
        validate_ranking_utility(utility)
        meta["report_utility"] = utility.model_dump(mode="json")


def generate_ranking(
    *,
    db_path: Path,
    out_path: Path,
    field_path: Path | None = None,
    field_label: str | None = None,
    field_since: str | None = None,
    ground_n: int = 8,
    top_k: int = 8,
    cover_min: float = 0.8,
    min_row_share: float = 0.001,
    include_superarchetypes: bool = True,
    benchmark_summary_path: Path | None = None,
    data_until: str | None = None,
    target: ReportTarget | None = None,
) -> dict:
    """Compute and write the ranking page; the CLI is only argument presentation."""
    if field_path is not None and Path(out_path).resolve() == DEFAULT_OUT.resolve():
        raise ValueError(
            "custom field reports require a separate output path; the canonical global report is protected"
        )
    if target is not None and data_until is not None:
        raise ValueError("pass target or data_until, not both")
    if target is not None and field_since is not None and field_since != target.field_since.isoformat():
        raise ValueError("field_since differs from the typed report target")
    requested_until = target.data_until.isoformat() if target and target.data_until else data_until
    if target is not None:
        effective_until = target.effective_data_until.isoformat()
        effective_since = target.field_since.isoformat()
        regime_card = target.regime_card
        ban_events = confirmed_bans_before(target.effective_data_until)
    else:
        cutoff = dt.date.fromisoformat(data_until) if data_until else dt.date.max
        ban_events = tuple(event for event in BAN_EVENTS if event[0] < cutoff)
        latest_ban = max(ban_events, key=lambda event: event[0])
        effective_since = field_since or latest_ban[0].isoformat()
        regime_card = latest_ban[1] if effective_since == latest_ban[0].isoformat() else None
        effective_until = data_until
    parents = staged_split_parents()
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        if target is not None and target.mode == "current":
            corpus_max = con.execute(
                "SELECT max(cast(substr(date,1,10) AS DATE)) FROM tournaments"
            ).fetchone()[0]
            if (
                corpus_max is None
                or target.effective_data_until != corpus_max + dt.timedelta(days=1)
            ):
                raise ValueError(
                    "current target effective cutoff must be one day after the frozen corpus maximum"
                )
        field_scenario = (
            load_field_scenario(con, Path(field_path), label=field_label)
            if field_path is not None else None
        )
        superarchetypes = None if not include_superarchetypes else read_superarchetype_members(con)
        blob = compute_blob(
            con, field_since=effective_since, ground_n=ground_n, top_k=top_k,
            cover_min=cover_min, min_row_share=min_row_share,
            regime_card=regime_card, parents=parents, superarchetypes=superarchetypes,
            benchmark_validation=benchmark_validation_payload(benchmark_summary_path),
            data_until=requested_until,
            ban_events=ban_events,
        )
        parent_interval = camp_interval = None
        if target is not None:
            evidence_started = time.perf_counter()
            authority_payload = _authority_payload(blob)
            before = canonical_json(authority_payload)
            clock = AnalysisClock(
                data_until=target.effective_data_until,
                knowledge_as_of=target.knowledge_as_of,
                knowledge_mode="retrospective-current-model",
            )
            parent_interval = build_interval_adaptive_matrix(
                con,
                clock=clock,
                certificate_run_id=target.certificate_run_id,
                min_row_share=min_row_share,
                until=target.effective_data_until.isoformat(),
                ban_events=ban_events,
            )
            camp_interval = None
            if parents:
                camp_interval = build_interval_adaptive_matrix(
                    con,
                    clock=clock,
                    certificate_run_id=target.certificate_run_id,
                    min_row_share=min_row_share,
                    until=target.effective_data_until.isoformat(),
                    split_variants=parents,
                    ban_events=ban_events,
                )
            interval_seconds = time.perf_counter() - evidence_started
            projection_started = time.perf_counter()
            amplification = None
            if target.amplification_run_id is not None:
                amplification = read_amplification_run(con, target.amplification_run_id)
                if amplification is None:
                    raise ValueError(
                        f"amplification run not found: {target.amplification_run_id}"
                    )
            parent_corpus_id = build_interval_evidence_corpus(parent_interval).corpus_id
            camp_corpus_id = (
                build_interval_evidence_corpus(camp_interval).corpus_id
                if camp_interval is not None
                else None
            )
            parent_amplification = (
                amplification
                if amplification is not None
                and amplification.corpus.corpus_id == parent_corpus_id
                else None
            )
            camp_amplification = (
                amplification
                if amplification is not None
                and amplification.corpus.corpus_id == camp_corpus_id
                else None
            )
            if amplification is not None and parent_amplification is None \
                    and camp_amplification is None:
                raise ValueError(
                    "amplification run corpus differs from both exact report interval corpora"
                )
            parent_display_pairs = _diagnostic_pair_keys(
                blob["arch"], limit=REPORT_DIAGNOSTIC_OPPONENTS,
            )
            camp_display_pairs = _diagnostic_pair_keys(
                blob["camps"], limit=REPORT_DIAGNOSTIC_OPPONENTS,
            )
            parent_attachment = build_report_evidence(
                parent_interval,
                parent_amplification,
                authority_payload=authority_payload,
                pair_keys=parent_display_pairs,
            )
            camp_attachment = (
                build_report_evidence(
                    camp_interval,
                    camp_amplification,
                    authority_payload=authority_payload,
                    pair_keys=camp_display_pairs,
                )
                if camp_interval is not None
                else None
            )
            primary_attachment = (
                camp_attachment if camp_amplification is not None else parent_attachment
            )
            assert primary_attachment is not None
            parent_payload = parent_attachment.model_dump(mode="json")
            camp_payload = (
                camp_attachment.model_dump(mode="json")
                if camp_attachment is not None else None
            )
            primary_payload = (
                camp_payload if camp_amplification is not None else parent_payload
            )
            parent_pairs = tuple(parent_payload["pairs"].values())
            camp_pairs = (
                tuple(camp_payload["pairs"].values())
                if camp_payload is not None
                else ()
            )
            for rows, source_pairs, attachment in (
                (blob["arch"], parent_pairs, parent_attachment),
                (blob["camps"], camp_pairs, camp_attachment),
            ):
                for row in rows:
                    row_pairs = tuple(
                        pair for pair in source_pairs if pair["subject"] == row["subject"]
                    )
                    row_reasons = tuple(
                        dict.fromkeys(reason for pair in row_pairs for reason in pair["reasons"])
                    )
                    row["diagnostic_evidence"] = {
                        "authority": "diagnostic-only",
                        "status": attachment.status if row_pairs and attachment is not None
                        else "not-assessed",
                        "reasons": row_reasons
                        if row_pairs
                        else ("no exact interval pair is available for this report row",),
                        "pairs": row_pairs,
                    }
            _publish_visible_best_estimates(
                blob,
                parent_interval=parent_interval,
                camp_interval=camp_interval,
            )
            blob["evidence"] = {
                key: value for key, value in primary_payload.items() if key != "pairs"
            }
            blob["evidence"].update({
                "pair_diagnostic_count": len(primary_payload["pairs"]),
                "pair_scope": (
                    f"top-{REPORT_DIAGNOSTIC_OPPONENTS}-current-field-opponents-"
                    "per-supported-row"
                ),
            })
            blob["report_target"] = target.model_dump(mode="json")
            interval_digest = _digest_rows(
                {
                    "parent": parent_attachment.interval_corpus_sha256,
                    "camp": camp_attachment.interval_corpus_sha256
                    if camp_attachment is not None
                    else None,
                }
            )
            blob["meta"]["evidence_audit"] = {
                "authority_payload_sha256": primary_attachment.authority_payload_sha256,
                "interval_corpus_sha256": interval_digest,
                "parent_interval_corpus_sha256": parent_attachment.interval_corpus_sha256,
                "camp_interval_corpus_sha256": camp_attachment.interval_corpus_sha256
                if camp_attachment is not None
                else None,
                "certificate_run_id": primary_attachment.certificate_run_id,
                "amplification_run_id": primary_attachment.amplification_run_id,
                "status": primary_attachment.status,
                "reasons": primary_attachment.reasons,
                "parent_diagnostic_pairs": len(parent_pairs),
                "camp_diagnostic_pairs": len(camp_pairs),
                "diagnostic_opponents_per_row": REPORT_DIAGNOSTIC_OPPONENTS,
            }
            blob["meta"]["target_data_audit"] = _report_data_audit(
                con,
                requested_until=requested_until,
                effective_until=effective_until,
                field_since=effective_since,
                recent_since=blob["meta"]["current_4wk"],
                interval_sha256=interval_digest,
            ).model_dump(mode="json")
            if canonical_json(_authority_payload(blob)) != before:
                raise RuntimeError("diagnostic attachment changed ranking authority bytes")
            print(f"  exact interval evidence: {interval_seconds:.1f}s")
            print(
                "  compact report projection: "
                f"{time.perf_counter() - projection_started:.1f}s"
            )
        _publish_deck_rankings(
            con,
            blob,
            parent_interval=parent_interval,
            camp_interval=camp_interval,
            field_override=(
                field_scenario.projection_field()
                if field_scenario is not None else None
            ),
            field_scenario=field_scenario,
        )
        # Build diagnostics consume the final projected rows so their matchup
        # labels and shares match the disclosure.  They are descriptive
        # additions and are excluded from the ranking authority payload above.
        from legacy_engine.advisory.decision_units import analyze_decision_units

        analysis_until = effective_until
        if analysis_until is None:
            corpus_max = blob.get("meta", {}).get("corpus_max")
            if corpus_max:
                analysis_until = (
                    dt.date.fromisoformat(corpus_max) + dt.timedelta(days=1)
                ).isoformat()
        if analysis_until is not None:
            decision_units = analyze_decision_units(
                con, blob, since=effective_since, until=analysis_until,
            )
            by_parent = decision_units["by_parent"]
            for row in blob.get("arch", ()):
                item = by_parent.get(row.get("subject"))
                if item is not None:
                    row["decision_units"] = item
            blob.setdefault("meta", {})["decision_units"] = {
                "version": decision_units["version"],
                "status": decision_units["status"],
                "window": decision_units["window"],
                "parents_analyzed": decision_units["summary"]["parents_analyzed"],
                "parents_with_comparison": decision_units["summary"]["parents_with_comparison"],
                "top_attention": decision_units["summary"]["top_attention"],
            }
        # The evaluator consumes this typed handoff directly when it calls the
        # publisher. It must never enter the JSON/page blob, since it contains
        # Pydantic source objects rather than browser data.
        blob.pop("_deck_ranking_projection_inputs", None)
    finally:
        con.close()

    from legacy_engine.workflows.deck_ranking_evaluation import served_evaluation_disclosure

    evaluation_path = Path(__file__).parent.parent / "data/benchmarks/deck-rankings-evaluation-v1/confirmation-summary.json"
    try:
        study = served_evaluation_disclosure(evaluation_path)
    except (ValueError, KeyError, TypeError) as exc:
        print(f"  historical evaluation disclosure unavailable: {exc}")
        study = None
    if study and study["method_id"] == blob.get("meta", {}).get("deck_rankings", {}).get("method_id"):
        blob["meta"]["served_evaluation"] = study

    current_snapshot = ranking_snapshot(blob)
    try:
        previous_blob = read_published_ranking(out_path)
        previous_changes = (
            previous_blob.get("meta", {}).get("refresh_changes", {})
            if previous_blob is not None and isinstance(previous_blob.get("meta"), dict)
            else {}
        )
        previous_snapshot = (
            previous_changes.get("snapshot")
            if isinstance(previous_changes, dict)
            and isinstance(previous_changes.get("snapshot"), dict)
            else ranking_snapshot(previous_blob) if previous_blob is not None else None
        )
        refresh_changes = compare_ranking_snapshots(current_snapshot, previous_snapshot)
    except (PublishedRankingPayloadError, RankingSnapshotError) as exc:
        reason = f"previous ranking comparison unavailable: {exc}"
        refresh_changes = compare_ranking_snapshots(current_snapshot, None)
        refresh_changes.update({
            "status": "unavailable",
            "reason": reason,
            "insights": [{
                "type": "unavailable",
                "text": f"Comparison unavailable: {reason}; the current publication remains usable.",
                "evidence": {"available": False, "reason": reason},
            }],
        })
    # The snapshot is the only persisted handoff needed by the next refresh.
    # Detailed per-candidate diagnostics remain in the selected insight evidence;
    # avoid carrying an unused decomposition table into every HTML page.
    refresh_changes["snapshot"] = current_snapshot
    refresh_changes["unavailable_attributions"] = refresh_changes.get(
        "unavailable_attributions", [],
    )[:3]
    blob["meta"]["refresh_changes"] = refresh_changes

    template = TEMPLATE_PATH.read_text()
    assert "__D_BLOB__" in template, f"placeholder missing in {TEMPLATE_PATH}"
    render_started = time.perf_counter()
    # Serialize the reading surface only. The returned analytical blob preserves
    # frozen diagnostics for evaluators; the offline page does not consume them.
    page_blob = dict(blob)
    for key in ("arch", "camps"):
        page_blob[key] = [
            {name: row[name] for name in (
                "subject", "_idx", "parent", "camp", "decision", "plan_cells",
                "decision_units",
            ) if name in row}
            for row in blob[key]
        ]
    page_blob["plans"] = [
        {name: row[name] for name in (
            "id", "label", "description", "members", "field_share", "decision",
            "scenario_unavailable",
        ) if name in row}
        for row in blob.get("plans", [])
    ]
    rendered = template.replace("__D_BLOB__", _json_for_script(page_blob), 1)
    _atomic_write_text(out_path, rendered)
    print(
        f"  report serialization/write: {time.perf_counter() - render_started:.1f}s "
        f"({len(rendered.encode('utf-8')):,} bytes)"
    )
    return blob


def _parse_aware_datetime(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("knowledge-as-of must include a timezone offset")
    return parsed


def _cli_target(args) -> ReportTarget | None:
    requested = any(
        (
            args.data_until,
            args.knowledge_as_of,
            args.certificate_run_id,
            args.amplification_run_id,
            args.target_id,
            args.target_label,
        )
    )
    # ``--field-since`` is the explicit legacy/non-target report surface.  A
    # completely unqualified invocation publishes the current typed target,
    # while this override preserves generate_ranking(..., field_since=...)
    # parity for callers that deliberately request the older authority-only
    # report.
    if not requested and args.field_since:
        return None
    if not requested:
        return current_report_target(Path(args.db))
    con = duckdb.connect(str(args.db), read_only=True)
    try:
        run = (
            read_amplification_run(con, args.amplification_run_id)
            if args.amplification_run_id
            else None
        )
        if args.amplification_run_id and run is None:
            raise ValueError(f"amplification run not found: {args.amplification_run_id}")
        if args.data_until:
            effective = dt.date.fromisoformat(args.data_until)
            mode = "retrospective-current-model"
        elif run is not None:
            effective = run.corpus.clock.data_until
            mode = "current"
        else:
            maximum = con.execute(
                "SELECT max(cast(substr(date,1,10) AS DATE)) FROM tournaments"
            ).fetchone()[0]
            if maximum is None:
                raise ValueError("current target requires a non-empty tournament corpus")
            effective = maximum + dt.timedelta(days=1)
            mode = "current"
    finally:
        con.close()
    if run is not None and run.corpus.clock.data_until != effective:
        raise ValueError("requested target cutoff differs from the exact amplification run")
    knowledge = (
        _parse_aware_datetime(args.knowledge_as_of)
        if args.knowledge_as_of
        else run.corpus.clock.knowledge_as_of
        if run is not None
        else None
    )
    if knowledge is None:
        raise ValueError("typed report generation requires --knowledge-as-of")
    boundary, cards = target_regime(effective)
    same_day_cards = tuple(card for when, card, _reason in BAN_EVENTS if when == effective)
    label = args.target_label or (
        "Current"
        if mode == "current"
        else f"Before {', '.join(same_day_cards) if same_day_cards else effective.isoformat()} · {effective.isoformat()}"
    )
    return ReportTarget(
        target_id=args.target_id
        or ("current" if mode == "current" else f"before-{effective.isoformat()}"),
        label=label,
        mode=mode,
        mode_label="Current" if mode == "current" else "Today's model",
        data_until=effective if mode != "current" else None,
        effective_data_until=effective,
        knowledge_as_of=knowledge,
        field_since=boundary,
        regime_card=cards[0],
        certificate_run_id=args.certificate_run_id
        or (run.corpus.certificate_run_id if run is not None else None),
        amplification_run_id=args.amplification_run_id,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(DUCKDB_PATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--field", default=None,
                    help="private expected-field file; requires an output path separate from the global report")
    ap.add_argument("--field-label", default=None,
                    help="visible label for --field (default: input filename stem)")
    ap.add_argument("--field-since", default=None,
                    help="legacy field-window override (typed targets derive their confirmed regime)")
    ap.add_argument("--ground-n", type=int, default=8)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--cover-min", type=float, default=0.8)
    ap.add_argument("--min-row-share", type=float, default=0.001)
    ap.add_argument("--no-superarchetypes", action="store_true",
                    help="omit the optional internal superarchetype registry input")
    ap.add_argument("--benchmark-summary", default=None,
                    help="reviewed benchmark summary JSON exposed on the page")
    ap.add_argument("--data-until", default=None,
                    help="exclusive retrospective cutoff; emits a Today's model target")
    ap.add_argument("--knowledge-as-of", default=None,
                    help="timezone-aware knowledge/configuration clock for a typed target")
    ap.add_argument("--certificate-run-id", default=None,
                    help="exact recurrent-era certificate run for interval evidence")
    ap.add_argument("--amplification-run-id", default=None,
                    help="exact amplification run; never resolved by latest-run lookup")
    ap.add_argument("--target-id", default=None,
                    help="filesystem-safe target id (default: current or before-YYYY-MM-DD)")
    ap.add_argument("--target-label", default=None,
                    help="visible report-target label")
    args = ap.parse_args()

    out = Path(args.out)
    target = _cli_target(args)
    blob = generate_ranking(
        db_path=Path(args.db), out_path=out,
        field_path=Path(args.field) if args.field else None,
        field_label=args.field_label,
        field_since=None if target is not None else args.field_since,
        ground_n=args.ground_n, top_k=args.top_k, cover_min=args.cover_min,
        min_row_share=args.min_row_share,
        include_superarchetypes=not args.no_superarchetypes,
        benchmark_summary_path=Path(args.benchmark_summary) if args.benchmark_summary else None,
        target=target,
    )
    print(f"wrote {out}: field={blob['meta']['field_decks']} decks since "
          f"{blob['meta']['field_since']}, corpus_max={blob['meta']['corpus_max']}, "
          f"{len(blob['arch'])} arch + {len(blob['camps'])} camp rows")


if __name__ == "__main__":
    main()
