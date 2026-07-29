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
  - Camps: one split matrix per staged parent in the discovery registry; camp
    field share = parent share x camp fraction among the parent's window decks.

Run after every data refresh cycle (refresh all -> label -> discover apply x N ->
eras run) — the matchup matrices read eras + variants, so refresh THIS page LAST:

  .venv/bin/python scripts/refresh_best_call_ranking.py

Runbook: docs/analysis/best-call-ranking.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import duckdb

from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.matchup import build_adaptive_matrix, build_matrix
from legacy_engine.config import DISCOVERED_VARIANTS_PATH, DUCKDB_PATH
from legacy_engine.ingestion.banlist import BAN_EVENTS

TEMPLATE_PATH = Path(__file__).parent / "best_call_ranking_template.html"
DEFAULT_OUT = Path(__file__).parent.parent / "decks" / "best-deck-best-call-ranking.html"


def r4(x: float | None) -> float | None:
    return None if x is None else round(x, 4)


def horizon_text(h) -> str:
    if h is None:
        return "ban-only"
    return f"{h.source}: {h.trigger}" if h.trigger else h.source


def make_cells(subj, field_opps, shares, ad_cells, fb_by_date, ban_since, ground_n,
               subj_ban=None):
    """One row's cells vs every current-field opponent (mirror excluded).

    ``fb_by_date`` maps a window-start ISO date (or ``None`` = full corpus) to that
    window's ``MatchupMatrix`` cells. Each pair's fallback window starts at the later
    of the two decks' ban-affectedness dates (``subj_ban``/``ban_since[opp]``) — the
    Nadu rule: a banned engine's matches never blend into a fallback cell.
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
        cells.append({
            "opp": opp, "share": r4(shares[opp]), "p": r4(use.p_shrunk), "raw": r4(use.p_raw),
            "ci_low": r4(use.ci_low), "ci_high": r4(use.ci_high),
            "n": use.n, "window": win, "tier": str(use.tier),
            "measured": use.n >= ground_n,
        })
    return cells


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


def compute_blob(con, *, field_since, ground_n, top_k, cover_min, min_row_share,
                 regime_card):
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
    for i, subj in enumerate(rows):
        cells = make_cells(subj, field_opps, sh, ad.matrix.cells, fb_by_date, ban_since,
                           ground_n, subj_ban=ban_since.get(subj))
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

    # ── Camp level: one split matrix per staged parent ──
    parents = sorted({s["parent"] for s in json.load(open(DISCOVERED_VARIANTS_PATH))["splits"]})
    camps_out = []
    for p, parent in enumerate(parents):
        print(f"[{p + 1}/{len(parents)}] split matrices for {parent!r}...", flush=True)
        adp = build_adaptive_matrix(con, min_row_share=min_row_share, split_variant=parent)
        # Camp labels inherit the parent's ban-affectedness date; build only the fallback
        # windows this parent's pairs can actually need: max(parent_ban, opp_ban) per opponent.
        p_ban = ban_since.get(parent)
        p_dates = {max((d for d in (p_ban, ban_since.get(o)) if d), default=None)
                   for o in field_opps}
        fbp = {d: build_matrix(con, min_row_share=min_row_share, split_variant=parent,
                               since=d).cells for d in p_dates}
        prefix = f"{parent} ["
        for lbl in (r for r in adp.matrix.archetypes if r.startswith(prefix)):
            camp = lbl[len(prefix):-1]
            cells = make_cells(lbl, field_opps, sh, adp.matrix.cells, fbp, ban_since,
                               ground_n, subj_ban=p_ban)
            frac = camp_frac.get((parent, camp), 0.0)
            camps_out.append({
                "subject": lbl, **row_stats(cells, top_k, cover_min),
                "since": adp.valid_since.get(lbl),
                "horizon": horizon_text(adp.horizon_meta.get(lbl)),
                "cells": cells,
                "parent": parent, "camp": camp,
                "field_share": r4(shares.get(parent, 0.0) * frac),
                "camp_fraction_current": r4(frac),
                "recent_4wk": camp_recent.get((parent, camp), 0),
                "_idx": len(camps_out),
            })

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
            "audit": [],
        },
        "arch": arch_out,
        "camps": camps_out,
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
    args = ap.parse_args()

    regime_card = latest_ban[1] if args.field_since == latest_ban[0].isoformat() else None
    con = duckdb.connect(args.db, read_only=True)
    try:
        blob = compute_blob(
            con, field_since=args.field_since, ground_n=args.ground_n, top_k=args.top_k,
            cover_min=args.cover_min, min_row_share=args.min_row_share,
            regime_card=regime_card,
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
