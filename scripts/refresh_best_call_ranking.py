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
  - floor = min p_shrunk over floor-eligible cells: measured AND (n >= 20 OR the 95% CI
    upper bound < 50%) — a thin cell must prove its hole; agency = min(adj, floor).
  - coverage = measured share-mass / total opponent share-mass; grounded = the
    top-``--top-k`` field opponents all measured AND coverage >= ``--cover-min``.
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
  - Superarchetype fallback (LEDGER-ONLY): a page-unmeasured cell may carry an additive
    ``sa`` payload resolved by the engine's display ladder (measured -> imputed -> pooled
    -> family range), rendered as a labeled lean in the expanded ledger. Leans NEVER enter
    adj/floor/agency/coverage/strata or the MC — every row metric computes from
    bit-identical inputs with the layer on or off (the isolation decision in
    .work/active/features/epic-superarchetype-layer-best-call-fallback.md). The registry
    is read from the SAME --db (``superarchetype run``'s derived cache); absent tables =
    layer off; ``--no-superarchetypes`` regenerates the baseline.

Run after every data refresh cycle (refresh all -> label -> discover apply x N ->
eras run) — the matchup matrices read eras + variants, so refresh THIS page LAST:

  .venv/bin/python scripts/refresh_best_call_ranking.py

Runbook: docs/analysis/best-call-ranking.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import duckdb

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.positioning import (
    _COVERAGE_RESTRICT_THRESHOLD,
    _DEFAULT_DRAWS,
    _PBEST_SUPPRESS_COVERAGE,
    _compute_data_coverage,
    rank_decks,
)
from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.matchup import (
    DISPLAY_GATE_N,
    MatchupMatrix,
    build_adaptive_matrix,
    build_matrix,
    build_multi_split_adaptive,
    build_multi_split_matrix,
)
from legacy_engine.analytics.superarchetype.aggregate import I2_ONE_SIDED_NOTE
from legacy_engine.analytics.superarchetype.registry import read_superarchetype_members
from legacy_engine.archetype.discovered import staged_split_parents
from legacy_engine.config import DUCKDB_PATH
from legacy_engine.ingestion.banlist import BAN_EVENTS

TEMPLATE_PATH = Path(__file__).parent / "best_call_ranking_template.html"
DEFAULT_OUT = Path(__file__).parent.parent / "decks" / "best-deck-best-call-ranking.html"

# Fixed MC seed so the cross-camp P(best) column is reproducible run-to-run on the same
# corpus (rank_decks is deterministic under a fixed seed; a refresh changes numbers only
# because the DATA changed, never because the sampler did).
RANK_SEED = 20260731


def r4(x: float | None) -> float | None:
    return None if x is None else round(x, 4)


def horizon_text(h) -> str:
    if h is None:
        return "ban-only"
    return f"{h.source}: {h.trigger}" if h.trigger else h.source


def make_cells(subj, field_opps, shares, ad_cells, fb_by_date, ban_since, ground_n,
               subj_ban=None, out_used=None):
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
        fb_date = max((d for d in (subj_ban, ban_since.get(opp)) if d), default=None)
        fc = fb_by_date[fb_date].get((subj, opp)) if fb_date in fb_by_date else None
        fb_label = f"BA {fb_date}" if fb_date else "FC"
        if ec is not None and ec.n >= ground_n:
            use, win = ec, "era"
        elif fc is not None and fc.n >= ground_n:
            use, win = fc, fb_label
        else:
            use, win = (ec if ec is not None else fc), "era"
        if use is None:  # pair absent from the matrix (e.g. camp vs its own parent)
            cells.append({"opp": opp, "share": r4(shares[opp]), "p": None, "raw": None,
                          "n": 0, "window": "era", "tier": "speculative", "measured": False})
            continue
        if out_used is not None:
            out_used[opp] = use
        cells.append({
            "opp": opp, "share": r4(shares[opp]), "p": r4(use.p_shrunk), "raw": r4(use.p_raw),
            "ci_low": r4(use.ci_low), "ci_high": r4(use.ci_high),
            "n": use.n, "window": win, "tier": str(use.tier),
            "measured": use.n >= ground_n,
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


# A thin measured cell can set the row's floor only when even its optimistic bound is
# unfavorable — ambiguity is not a hole. Deep cells (n >= FLOOR_DEEP_N) qualify on their
# point estimate; thinner ones must have a 95% CI upper bound below 50%.
FLOOR_DEEP_N = 20
FLOOR_PROOF_CI = 0.50


def _floor_eligible(c) -> bool:
    return c["measured"] and (
        c["n"] >= FLOOR_DEEP_N
        or (c["ci_high"] is not None and c["ci_high"] < FLOOR_PROOF_CI)
    )


def row_stats(cells, top_k, cover_min):
    den_all = sum(c["share"] for c in cells)
    n1 = [c for c in cells if c["n"] >= 1 and c["p"] is not None]
    n1_mass = sum(c["share"] for c in n1)
    adj = (sum(c["share"] * c["p"] for c in n1) / n1_mass) if n1 and n1_mass else None
    meas = [c for c in cells if c["measured"]]
    eligible = [c for c in meas if _floor_eligible(c)]
    floor_c = min(eligible, key=lambda c: c["p"]) if eligible else None
    coverage = (sum(c["share"] for c in meas) / den_all) if den_all else 0.0
    topk = sorted(cells, key=lambda c: c["share"], reverse=True)[:top_k]
    topk_ok = bool(topk) and all(c["measured"] for c in topk)
    floor = floor_c["p"] if floor_c else None
    vals = [v for v in (adj, floor) if v is not None]
    return {
        "adj": r4(adj), "floor": r4(floor),
        "floor_opp": floor_c["opp"] if floor_c else None,
        "agency": r4(min(vals)) if vals else None,
        "coverage": r4(coverage),
        "grounded": topk_ok and coverage >= cover_min,
        "topk_ok": topk_ok,
    }


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
                 regime_card, parents, superarchetypes=None):
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
    for i, subj in enumerate(rows):
        arch_used[subj] = {}
        cells = make_cells(subj, field_opps, sh, ad.matrix.cells, fb_by_date, ban_since,
                           ground_n, subj_ban=ban_since.get(subj), out_used=arch_used[subj])
        arch_out.append({
            "subject": subj, **row_stats(cells, top_k, cover_min),
            "since": ad.valid_since.get(subj),
            "horizon": horizon_text(ad.horizon_meta.get(subj)),
            "cells": cells,
            "field_share": r4(shares.get(subj, 0.0)),
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
        max((d for d in (ban_since.get(camp_parent[c]), ban_since.get(o)) if d), default=None)
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
    for parent in parents:
        p_ban = ban_since.get(parent)
        prefix = f"{parent} ["
        for lbl in (c for c in camp_labels if camp_parent[c] == parent):
            camp = lbl[len(prefix):-1]
            camp_used[lbl] = {}
            cells = make_cells(lbl, field_opps, sh, msa.multi.cells, camp_fb, ban_since,
                               ground_n, subj_ban=p_ban, out_used=camp_used[lbl])
            frac = camp_frac.get((parent, camp), 0.0)
            camps_out.append({
                "subject": lbl, **row_stats(cells, top_k, cover_min),
                "since": msa.valid_since.get(lbl),
                "horizon": horizon_text(msa.horizon_meta.get(lbl)),
                "cells": cells,
                "parent": parent, "camp": camp,
                "field_share": r4(shares.get(parent, 0.0) * frac),
                "camp_fraction_current": r4(frac),
                "recent_4wk": camp_recent.get((parent, camp), 0),
                "_idx": len(camps_out),
            })

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
    rank_cells = {
        (subj, opp): cell
        for subj in potential
        for opp, cell in used_by_subject.get(subj, {}).items()
    }
    rank_matrix = MatchupMatrix(
        cells=rank_cells, provenance=None, total_matches=ad.matrix.total_matches,
        archetypes=sorted({*potential, *field_opps}), caveat=ad.matrix.caveat,
    )
    coverage = {d: _compute_data_coverage(rank_matrix, rank_field, d) for d in potential}
    candidates = [d for d in potential if coverage[d] >= _PBEST_SUPPRESS_COVERAGE]
    ranking = rank_decks(rank_matrix, rank_field, candidates, seed=RANK_SEED)
    for r in camps_out:
        lbl = r["subject"]
        ranked = lbl in ranking.p_best
        # Additive cross-camp columns (the pre-existing row fields are untouched).
        r["p_best"] = r4(ranking.p_best[lbl]) if ranked else None
        r["s_q"] = r4(ranking.s_quantile[lbl]) if ranked else None
        r["s_cov"] = r4(coverage[lbl])
        r["s_caveated"] = coverage[lbl] < _COVERAGE_RESTRICT_THRESHOLD
    print(f"  shared-field ranking: {time.perf_counter() - t_rank:.1f}s "
          f"({len(candidates)} candidates, {_DEFAULT_DRAWS:,} draws)", flush=True)
    print(f"  camp sweep total: {time.perf_counter() - t_camp:.1f}s "
          f"({len(camps_out)} camp rows)", flush=True)

    # ── Superarchetype fallback overlay (LEDGER-ONLY) ──
    # Additive `sa` keys on page-unmeasured cells; measured cells and every row-level field
    # are untouched, so adj/floor/agency/coverage/grounded/P(best) are bit-identical with the
    # layer on or off. Rung 1 (a measured cell) is the page's existing selection above.
    sa_audit: list[str] = []
    if superarchetypes is not None:
        label_of = {c.id: c.label for c in superarchetypes.clusters}
        sa_counts = {"imputed": 0, "pooled": 0, "range": 0}
        for row in (*arch_out, *camps_out):
            for c in row["cells"]:
                if c["measured"]:
                    continue
                payload = _sa_payload(row["subject"], c["opp"], msa, label_of)
                if payload is not None:
                    c["sa"] = payload
                    sa_counts[payload["kind"]] += 1
        sa_audit = [
            line for line in msa.audit_preamble if line.startswith("// superarchetype")
        ]
        sa_audit.append(
            f"// superarchetype fallback: {sa_counts['imputed']} imputed + "
            f"{sa_counts['pooled']} pooled + {sa_counts['range']} family-range leans in the "
            "expanded ledgers — leans never enter agency, adj, floor, coverage, or strata"
        )
        print(f"  superarchetype fallback: {sa_counts['imputed']} imputed, "
              f"{sa_counts['pooled']} pooled, {sa_counts['range']} range", flush=True)

    families = build_family_payload(
        superarchetypes, msa.cluster_cells, arch_out, top_k=top_k, cover_min=cover_min,
    )

    return {
        "meta": {
            "field_since": field_since, "field_decks": field_decks,
            "regime_card": regime_card,
            "ground_n": ground_n, "top_k": top_k, "cover_min": cover_min,
            "min_row_share": min_row_share, "current_4wk": current_4wk,
            "corpus_max": corpus_max,
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
                "basis": "page-used cells (era preferred, ban-scoped fallback)",
            },
            "audit": [
                f"// multi-split: one pass over {len(parents)} staged parents — "
                f"{len(camp_labels)} camp rows, {len(camp_fb)} ban-scoped fallback windows",
                f"// cross-camp P(best): shared-field MC over {len(candidates)} of "
                f"{len(potential)} candidates (camps + unsplit archetypes with >= "
                f"{_PBEST_SUPPRESS_COVERAGE:.0%} measured coverage) on the page-used "
                f"cells, {_DEFAULT_DRAWS:,} draws, seed {RANK_SEED}",
                *sa_audit,
            ],
        },
        "arch": arch_out,
        "camps": camps_out,
        "families": families,
    }


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
                    help="skip the family-fallback ledger overlay (baseline/audit regeneration)")
    args = ap.parse_args()

    regime_card = latest_ban[1] if args.field_since == latest_ban[0].isoformat() else None
    parents = staged_split_parents()
    con = duckdb.connect(args.db, read_only=True)
    try:
        # The registry rides the SAME DB (`superarchetype run`'s derived cache); absent
        # tables -> None -> the builder's byte-identical off path (gated-additive).
        superarchetypes = None if args.no_superarchetypes else read_superarchetype_members(con)
        blob = compute_blob(
            con, field_since=args.field_since, ground_n=args.ground_n, top_k=args.top_k,
            cover_min=args.cover_min, min_row_share=args.min_row_share,
            regime_card=regime_card, parents=parents, superarchetypes=superarchetypes,
        )
    finally:
        con.close()

    template = TEMPLATE_PATH.read_text()
    assert "__D_BLOB__" in template, f"placeholder missing in {TEMPLATE_PATH}"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template.replace("__D_BLOB__", json.dumps(blob, ensure_ascii=False), 1))
    print(f"wrote {out}: field={blob['meta']['field_decks']} decks since "
          f"{blob['meta']['field_since']}, corpus_max={blob['meta']['corpus_max']}, "
          f"{len(blob['arch'])} arch + {len(blob['camps'])} camp rows")


if __name__ == "__main__":
    main()
