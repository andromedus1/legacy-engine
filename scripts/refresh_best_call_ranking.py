#!/usr/bin/env python3
"""Refresh the Best Deck / Best Call agency ranking page (self-contained HTML, offline).

Recomputes the page's embedded data blob from the DuckDB corpus and renders it
through ``scripts/best_call_ranking_template.html`` (the tracked template; the
output page in ``decks/`` is gitignored and fully regenerable).

Method (the page's definitional card is the authoritative prose):
  - Field basis: the current ban-regime window (default ``--field-since`` = the
    latest confirmed ban event date); shares = archetype window decks / window decks.
  - Rows: ``build_adaptive_matrix``/``build_matrix`` inclusion at
    ``--min-row-share`` (share of marginal match involvement, NOT meta share).
  - Cells vs every current-field opponent: era-windowed cell preferred when its
    n >= ``--ground-n``; else the fallback cell when ITS n >= ground-n; else the era
    cell kept honestly thin. measured = n >= ground-n.
  - Fallback window (the Nadu rule): the fallback pools matches since the LAST BAN THAT
    AFFECTED EITHER DECK in the pair (``archetype_valid_since`` — ran a banned card in
    >=25% of pre-ban decks), labeled ``BA <date>``; a true full-corpus ``FC`` cell exists
    only when neither deck was ever ban-affected. A banned engine's matches (Nadu
    Cephalid, Candelabra Forge) can never inflate a row — in either direction.
  - adj field WR = field-share-weighted p_shrunk over n>=1 cells (normalized).
  - floor = min p_shrunk over every measured cell (n >= ``--ground-n``); agency =
    min(adj, floor). Coverage + the upper-bound label carry incomplete-floor uncertainty.
  - coverage = measured share-mass / total opponent share-mass; grounded = the
    top-``--top-k`` field opponents all measured AND coverage >= ``--cover-min``.
  - Methodology diagnostics: a seeded precision-weighted posterior smooth floor with no
    sample cliff, complete-only rank spans across four predeclared projections, and a
    rate-free path-to-grounding agenda. Gated agency and P(best) remain authoritative.
  - Camps: ONE multi-split adaptive matrix over every staged parent in the discovery
    registry (``build_multi_split_adaptive`` — camp cells field-for-field identical to
    the per-parent split builds, parity-tested), plus one multi-split fallback matrix
    per distinct ban-scoped window date serving all parents at once; camp field share =
    parent share x camp fraction among the parent's window decks.
  - Cross-camp P(best): ONE shared-field MC (``rank_decks``) with candidates = all camp
    labels + unsplit field archetypes and a parent-level Dirichlet field (fixed seed) —
    P(best) is comparable across camps of DIFFERENT parents because every candidate is
    scored against the same sampled field. The MC ranks on the PAGE-USED cells (the
    ledger's own era-preferred, ban-scoped-fallback selection), so the column shares the
    page's Nadu-rule windows and its coverage-suppression honesty gates.
  - Strategic plans: curated primary-plan assignments aggregate decisive matches directly;
    plan rows and each archetype's five plan cells never average rendered archetype rates.
    Same-plan diagonals are structural 50% context, not measured evidence or floor inputs.
  - Superarchetypes remain internal matrix context only: the page emits no family payload,
    lean, range, or ranking input. ``apply_superarchetype_priors=False`` keeps the page's
    archetype/camp row metrics independent of that optional registry.

Run after every data refresh cycle (refresh all -> label -> discover apply x N ->
eras run) — the matchup matrices read eras + variants, so refresh THIS page LAST:

  .venv/bin/python scripts/refresh_best_call_ranking.py

Runbook: docs/analysis/best-call-ranking.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
import time
from pathlib import Path

import duckdb

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.ranking_benchmark import BenchmarkEvaluationSummary, content_sha256
from legacy_engine.advisory.positioning import (
    _COVERAGE_RESTRICT_THRESHOLD,
    _DEFAULT_DRAWS,
    _PBEST_SUPPRESS_COVERAGE,
    _compute_data_coverage,
    ranking_evidence_payload,
    rank_decks,
)
from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.eras.consume import clamp_pair_window
from legacy_engine.analytics.matchup import (
    DISPLAY_GATE_N,
    MatchupMatrix,
    build_adaptive_matrix,
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
from legacy_engine.models.matchup import MatchupCell

TEMPLATE_PATH = Path(__file__).parent / "best_call_ranking_template.html"
DEFAULT_OUT = Path(__file__).parent.parent / "decks" / "best-deck-best-call-ranking.html"

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
                 regime_card, parents, superarchetypes=None, benchmark_validation=None):
    corpus_max = con.execute("select max(substr(date,1,10)) from tournaments").fetchone()[0]
    current_4wk = (dt.date.fromisoformat(corpus_max) - dt.timedelta(days=28)).isoformat()
    corpus_decks, corpus_events = con.execute(
        "select (select count(*) from decks), (select count(*) from tournaments)").fetchone()
    field_events = con.execute(
        "select count(*) from tournaments where substr(date,1,10) >= ?", [field_since]).fetchone()[0]

    win_rows = con.execute(
        "select k.archetype, count(*) from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? and k.archetype is not null and k.archetype <> '' "
        "group by 1", [field_since]).fetchall()
    field_decks = con.execute(
        "select count(*) from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ?", [field_since]).fetchone()[0]
    shares = {a: n / field_decks for a, n in win_rows} if field_decks else {}
    recent = dict(con.execute(
        "select k.archetype, count(*) from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? group by 1", [current_4wk]).fetchall())

    camp_win = con.execute(
        "select k.archetype, coalesce(nullif(k.variant,''),'unlabeled'), count(*) "
        "from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? group by 1,2", [field_since]).fetchall()
    camp_recent = {(a, v): n for a, v, n in con.execute(
        "select k.archetype, coalesce(nullif(k.variant,''),'unlabeled'), count(*) "
        "from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? group by 1,2", [current_4wk]).fetchall()}
    parent_win_tot: dict[str, int] = {}
    for a, _v, n in camp_win:
        parent_win_tot[a] = parent_win_tot.get(a, 0) + n
    camp_frac = {(a, v): n / parent_win_tot[a] for a, v, n in camp_win}

    # ── Archetype level ──
    print("building archetype matrices...", flush=True)
    ad = build_adaptive_matrix(con, min_row_share=min_row_share)
    rows = ad.matrix.archetypes
    ban_since = archetype_valid_since(con, list(rows))
    field_opps = sorted((a for a in rows if shares.get(a, 0) > 0),
                        key=lambda a: shares[a], reverse=True)
    sh = {a: shares.get(a, 0.0) for a in [*rows, *field_opps]}
    # Fallback matrices, one per distinct ban-affectedness window (the Nadu rule) + true FC.
    fb_dates = {None} | {d for d in ban_since.values() if d}
    fb_by_date = {}
    for d in sorted(fb_dates, key=lambda x: x or ""):
        print(f"  fallback matrix since={d or 'full corpus'}...", flush=True)
        fb_by_date[d] = build_matrix(con, min_row_share=min_row_share, since=d).cells
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
                con, min_row_share=min_row_share, since=strict_since,
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
            con, parents=parents, min_row_share=min_row_share, since=d).cells
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
                    con, parents=parents, min_row_share=min_row_share, since=strict_since,
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
            frac = camp_frac.get((parent, camp), 0.0)
            camps_out.append({
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
                "camp_fraction_current": r4(frac),
                "recent_4wk": camp_recent.get((parent, camp), 0),
                "_idx": len(camps_out),
            })

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
    field_counts = dict(win_rows)
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

    # Strategic intent is a separate curated semantic layer. Recompute it from
    # decisive match tallies rather than averaging any rendered row statistic.
    plan_registry = load_strategic_plan_registry()
    plan_matches = compute_match_results(con, since=field_since)
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

    production_order = production_recommendation_order({
        row["subject"]: (row["grounded"], row["recent_4wk"], row["agency"])
        for row in arch_out
    })

    return {
        "meta": {
            "field_since": field_since, "field_decks": field_decks,
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
                f"// strategic plans: registry v{plan_registry.schema_version}, "
                f"{len(plan_registry.assignments)} assignments; "
                f"{plan_result.decisive_matches} decisive matches "
                f"({plan_result.same_plan_matches} same-plan), "
                f"{plan_result.omitted_matches} omitted; window since {field_since}",
                f"// archetype vs strategic plans: {len(arch_out)} archetypes × "
                f"{len(plan_registry.plans)} primary opponent plans from underlying decisive "
                "matches; archetype mirrors contribute structural 50% context",
            ],
        },
        "arch": arch_out,
        "camps": camps_out,
        "plans": plans,
    }


def generate_ranking(
    *,
    db_path: Path,
    out_path: Path,
    field_since: str | None = None,
    ground_n: int = 8,
    top_k: int = 8,
    cover_min: float = 0.8,
    min_row_share: float = 0.001,
    include_superarchetypes: bool = True,
    benchmark_summary_path: Path | None = None,
) -> dict:
    """Compute and write the ranking page; the CLI is only argument presentation."""
    latest_ban = max(BAN_EVENTS, key=lambda e: e[0])
    effective_since = field_since or latest_ban[0].isoformat()
    regime_card = latest_ban[1] if effective_since == latest_ban[0].isoformat() else None
    parents = staged_split_parents()
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        superarchetypes = None if not include_superarchetypes else read_superarchetype_members(con)
        blob = compute_blob(
            con, field_since=effective_since, ground_n=ground_n, top_k=top_k,
            cover_min=cover_min, min_row_share=min_row_share,
            regime_card=regime_card, parents=parents, superarchetypes=superarchetypes,
            benchmark_validation=benchmark_validation_payload(benchmark_summary_path),
        )
    finally:
        con.close()

    template = TEMPLATE_PATH.read_text()
    assert "__D_BLOB__" in template, f"placeholder missing in {TEMPLATE_PATH}"
    rendered = template.replace("__D_BLOB__", json.dumps(blob, ensure_ascii=False), 1)
    _atomic_write_text(out_path, rendered)
    return blob


def main() -> None:
    latest_ban = max(BAN_EVENTS, key=lambda e: e[0])
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(DUCKDB_PATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--field-since", default=latest_ban[0].isoformat(),
                    help="field-window start (default: latest confirmed ban event date)")
    ap.add_argument("--ground-n", type=int, default=8)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--cover-min", type=float, default=0.8)
    ap.add_argument("--min-row-share", type=float, default=0.001)
    ap.add_argument("--no-superarchetypes", action="store_true",
                    help="omit the optional internal superarchetype registry input")
    ap.add_argument("--benchmark-summary", default=None,
                    help="reviewed benchmark summary JSON exposed on the page")
    args = ap.parse_args()

    out = Path(args.out)
    blob = generate_ranking(
        db_path=Path(args.db), out_path=out, field_since=args.field_since,
        ground_n=args.ground_n, top_k=args.top_k, cover_min=args.cover_min,
        min_row_share=args.min_row_share,
        include_superarchetypes=not args.no_superarchetypes,
        benchmark_summary_path=Path(args.benchmark_summary) if args.benchmark_summary else None,
    )
    print(f"wrote {out}: field={blob['meta']['field_decks']} decks since "
          f"{blob['meta']['field_since']}, corpus_max={blob['meta']['corpus_max']}, "
          f"{len(blob['arch'])} arch + {len(blob['camps'])} camp rows")


if __name__ == "__main__":
    main()
