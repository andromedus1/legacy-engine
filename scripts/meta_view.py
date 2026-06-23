#!/usr/bin/env python3
"""Render the Legacy meta-landscape report (self-contained HTML, offline).

A deck-agnostic "meta view": where the metagame is, how it's moving, and which
decks are best-positioned over time. Companion to the deck-focused
``deck_vs_cohort_viz.py`` ("my deck" view). Prototype for the planned
``feature-deck-doctor-viz`` family.

Two sections:
  1. Meta composition + trends — weekly stacked-area of the Top-N archetypes
     (each panel ordered by that window's prevalence, biggest at the bottom),
     EMA trend lines on a secondary axis, ban-regime boundary markers, three
     time panels (full history / last 12 mo / current regime), plus a
     biggest-meta-share-movers table (with each mover's WR / best-deck Ū /
     best-call S).
  2. Best deck vs best call positioning over time — Ū(D) (quality regardless of
     field) and S(D) (field-weighted expected win %) for the Top-N best-
     positioned decks per window, a current-regime snapshot table, and a
     positioning-movers table.

Charts render to inline SVG via vl_convert (no Chrome/Node/CDN). Every figure
carries its confidence tier honestly; thin matchup samples are faded/flagged.

Usage:
  .venv/bin/python scripts/meta_view.py --out decks/meta.html
  # also emit the deck-specific matchups view ("my deck" overlay):
  .venv/bin/python scripts/meta_view.py --out decks/meta.html \
      --deck "Dimir Tempo" --matchups-out decks/dimir-tempo-matchups.html

Knobs: --bands-top (Section 1 bands, default 12), --pos-top (Section 2
positioning decks, default 20), --ema-span (default 6), --ema-lines (default 7),
--last-months (default 12), --min-week-total (default 25),
--regime-min-matches (default 200), --db.
"""
from __future__ import annotations

import argparse
import colorsys
import html as _html
import json
import re
from datetime import date, timedelta
from pathlib import Path

import duckdb
import vl_convert as vlc

from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.analytics.matchup import build_matrix, lookup_head_to_head
from legacy_engine.analytics.trends import compute_trends, regime_windows
from legacy_engine.confidence import tier_for_sample
from legacy_engine.config import DUCKDB_PATH

PALETTE = ['#56B4E9', '#E69F00', '#009E73', '#D55E00', '#CC79A7', '#0072B2',
           '#8DD3C7', '#BC80BD', '#FB8072', '#80B1D3', '#B3DE69', '#FCCDE5']
DARK = {"background": "#15181C", "view": {"stroke": "transparent"},
        "axis": {"labelColor": "#9AA0A6", "titleColor": "#E6E6E6", "gridColor": "#23272C",
                 "domainColor": "#3A3F45", "tickColor": "#3A3F45"},
        "legend": {"labelColor": "#E6E6E6", "titleColor": "#E6E6E6"}, "title": {"color": "#E6E6E6"}}


def gen_colors(n: int) -> list[str]:
    out = []
    for i in range(n):
        h = (i * 0.6180339887) % 1.0
        l = 0.62 if i % 2 == 0 else 0.74
        sat = 0.5 if i % 3 == 0 else 0.72
        r, g, b = colorsys.hls_to_rgb(h, l, sat)
        out.append('#%02x%02x%02x' % (round(r * 255), round(g * 255), round(b * 255)))
    return out


# ── data helpers (deck-agnostic) ──────────────────────────────────────────────
def weights(con, since, until):
    q = ("SELECT d.archetype, count(distinct d.tournament_id||d.deck_idx) n "
         "FROM decks d JOIN tournaments t ON d.tournament_id=t.id "
         "WHERE d.archetype IS NOT NULL AND d.archetype<>'Unknown' AND t.date>=? "
         + ("AND t.date<? " if until else "") + "GROUP BY 1")
    rows = con.execute(q, [since or '2000-01-01'] + ([until] if until else [])).fetchall()
    tot = sum(n for _, n in rows) or 1
    return {a: n / tot for a, n in rows}


def archs(m):
    return sorted(a for a in {a for (a, _b) in m.cells} if a != 'Unknown')


def dscore(m, w, D):
    """Return (S best-call, Ubar best-deck, matchup-n) for deck D in matrix m."""
    wr, sw, ss, nt = [], 0.0, 0.0, 0
    for a in archs(m):
        if a == D:
            continue
        c = m.cells.get((D, a))
        if not c or c.n == 0 or c.p_shrunk is None:
            continue
        wr.append(c.p_shrunk); nt += c.n; wa = w.get(a, 0); sw += wa; ss += wa * c.p_shrunk
    if not wr:
        return (None, None, 0)
    return (ss / sw if sw > 0 else None, sum(wr) / len(wr), nt)


def compute(con, args):
    """Compute everything the report needs; returns a dict of JSON-able data."""
    maxdate = con.execute("SELECT max(date) FROM tournaments").fetchone()[0][:10]
    # --- Section 1: shown archetypes (Top-N by overall count) ---
    shown = [r[0] for r in con.execute(
        "SELECT archetype, count(*) n FROM decks WHERE archetype IS NOT NULL AND archetype<>'Unknown' "
        "GROUP BY archetype ORDER BY n DESC LIMIT ?", [args.bands_top]).fetchall()]
    # weekly shares (shown + Other)
    rows = con.execute(
        "SELECT date_trunc('week', CAST(substr(date,1,10) AS DATE)) wk, d.archetype, "
        "count(distinct d.tournament_id||d.deck_idx) n "
        "FROM decks d JOIN tournaments t ON d.tournament_id=t.id WHERE d.archetype IS NOT NULL GROUP BY 1,2").fetchall()
    tot, byweek = {}, {}
    for wk, a, n in rows:
        k = str(wk)[:10]; tot[k] = tot.get(k, 0) + n; byweek.setdefault(k, {})[a] = n
    weeks = sorted(w for w in tot if tot[w] >= args.min_week_total)
    area, series = [], {a: [] for a in shown}
    for w in weeks:
        for a in shown:
            s = byweek.get(w, {}).get(a, 0) / tot[w]
            area.append({'week': w, 'archetype': a, 'share': round(100 * s, 3)}); series[a].append(s)
    ema_set = shown[:args.ema_lines]
    alpha = 2 / (args.ema_span + 1); ema = []
    for a in ema_set:
        e = None
        for i, w in enumerate(weeks):
            x = series[a][i]; e = x if e is None else alpha * x + (1 - alpha) * e
            ema.append({'week': w, 'archetype': a, 'ema': round(100 * e, 3)})
    w0, w1 = weeks[0], weeks[-1]
    regimes = [{'date': str(rw.since), 'label': '+'.join(rw.opening_events)[:34]}
               for rw in regime_windows() if rw.since and w0 <= str(rw.since) <= w1]
    cur_since = max((str(rw.since) for rw in regime_windows() if rw.since), default=None)

    # --- meta-share movers (per regime transition) via compute_trends ---
    ts = compute_trends(con, min_share=0.0)
    tscale = 100 if max((c.share for c in ts.cells.values()), default=0) <= 1.001 else 1
    sh = lambda lbl, a: (ts.cells.get((lbl, a)).share if ts.cells.get((lbl, a)) else 0.0) * tscale
    winmap = {str(rw.since): (str(rw.until) if rw.until else None) for rw in regime_windows() if rw.since}

    def deck_stat(mr, mat, w, a):
        rec = mr.archetypes.get(a); raw = 100 * rec.wins / rec.n if rec and rec.n else None
        S, U, nt = dscore(mat, w, a)
        return {'deck': a, 'wr': round(raw, 1) if raw is not None else None,
                'u': round(100 * U, 1) if U is not None else None,
                's': round(100 * S, 1) if S is not None else None,
                'tier': str(tier_for_sample(nt)), 'wr_n': (rec.n if rec else 0)}

    movers = []
    for i in range(1, len(ts.regimes)):
        rp, rc = ts.regimes[i - 1], ts.regimes[i]
        deltas = [(a, sh(rp.label, a), sh(rc.label, a)) for a in ts.archetypes
                  if not (sh(rp.label, a) == 0 and sh(rc.label, a) == 0)]
        risers = sorted(deltas, key=lambda x: -(x[2] - x[1]))[:3]
        fallers = sorted(deltas, key=lambda x: (x[2] - x[1]))[:3]
        since = str(rc.since); until = winmap.get(since)
        mr = compute_match_results(con, since=since, until=until)
        mat = build_matrix(con, since=since, until=until); w = weights(con, since, until)
        movers.append({
            'to_date': since, 'ban': ('+'.join(rc.opening_events) if rc.opening_events else since),
            'risers': [{'a': a, 'p': round(p, 1), 'c': round(c, 1), 'd': round(c - p, 1)} for a, p, c in risers if c - p > 0],
            'fallers': [{'a': a, 'p': round(p, 1), 'c': round(c, 1), 'd': round(c - p, 1)} for a, p, c in fallers if c - p < 0],
        })
        movers[-1]['rs_list'] = [deck_stat(mr, mat, w, x['a']) for x in movers[-1]['risers']]
        movers[-1]['fs_list'] = [deck_stat(mr, mat, w, x['a']) for x in movers[-1]['fallers']]

    # --- Section 2: positioning per regime ---
    regs = []
    for rw in regime_windows():
        if not rw.since:
            continue
        m = build_matrix(con, since=str(rw.since), until=str(rw.until) if rw.until else None)
        if m.total_matches >= args.regime_min_matches:
            regs.append((str(rw.since), str(rw.until) if rw.until else None))
    reg_dates = [s for s, _ in regs]
    last_cut = (date.fromisoformat(maxdate) - timedelta(days=int(args.last_months * 30.44))).isoformat()

    def topN(since, n):
        m = build_matrix(con, since=since, until=None); w = weights(con, since, None)
        sc = [(D, dscore(m, w, D)[0]) for D in archs(m)]
        sc = [(D, s) for D, s in sc if s is not None]; sc.sort(key=lambda x: -x[1])
        return [D for D, _ in sc[:n]]

    WIN = [('Full history', None, reg_dates),
           (f'Last {args.last_months} mo', last_cut, [x for x in reg_dates if x >= last_cut])]
    win_decks = {lbl: topN(since, args.pos_top) for lbl, since, _ in WIN}
    cur_decks = topN(cur_since, args.pos_top) if cur_since else []
    need = sorted({x for v in win_decks.values() for x in v} | set(cur_decks))
    reg_pos = {}
    for since, until in regs:
        m = build_matrix(con, since=since, until=until); w = weights(con, since, until)
        mr = compute_match_results(con, since=since, until=until)
        for D in archs(m):
            S, U, nt = dscore(m, w, D); rec = mr.archetypes.get(D)
            reg_pos[(since, D)] = {'u': round(100 * U, 1) if U is not None else None,
                                   's': round(100 * S, 1) if S is not None else None,
                                   'wr': round(100 * rec.wins / rec.n, 1) if rec and rec.n else None,
                                   'n': nt, 'tier': str(tier_for_sample(nt))}
    windows = []
    for lbl, since, dates in WIN:
        pts = [{'deck': D, 'date': dt, **reg_pos[(dt, D)]} for D in win_decks[lbl] for dt in dates
               if reg_pos.get((dt, D)) and (reg_pos[(dt, D)]['u'] is not None or reg_pos[(dt, D)]['s'] is not None)]
        windows.append({'label': lbl, 'since': since, 'dates': dates, 'decks': win_decks[lbl], 'pts': pts})
    union = sorted({p['deck'] for w in windows for p in w['pts']} | set(cur_decks))
    cur = [{'deck': D, **reg_pos[(cur_since, D)]} for D in cur_decks
           if reg_pos.get((cur_since, D)) and reg_pos[(cur_since, D)]['s'] is not None]
    cur.sort(key=lambda x: -x['s'])

    # positioning movers (ΔŪ best-deck, ΔS best-call)
    def pmovers(metric, i):
        pa, pb = reg_dates[i - 1], reg_dates[i]; deltas = []
        for D in {D for (dt, D) in reg_pos if dt in (pa, pb)}:
            a = reg_pos.get((pa, D), {}).get(metric); b = reg_pos.get((pb, D), {}).get(metric)
            if a is None or b is None:
                continue
            deltas.append((D, round(b - a, 1)))
        R = sorted(deltas, key=lambda x: -x[1])[:3]; F = sorted(deltas, key=lambda x: x[1])[:3]
        pack = lambda lst, pos: [{'deck': D, 'delta': dl, **{k: reg_pos[(pb, D)][k] for k in ('wr', 'u', 's', 'tier')}}
                                 for D, dl in lst if (dl > 0) == pos]
        return pack(R, True), pack(F, False)
    bans = {s: ('+'.join(rw.opening_events) if rw.opening_events else s)
            for rw in regime_windows() if rw.since for s in [str(rw.since)]}
    pos_movers = []
    for i in range(1, len(reg_dates)):
        bd_r, bd_f = pmovers('u', i); bc_r, bc_f = pmovers('s', i)
        pos_movers.append({'to_date': reg_dates[i], 'ban': bans.get(reg_dates[i], ''),
                           'bd_r': bd_r, 'bd_f': bd_f, 'bc_r': bc_r, 'bc_f': bc_f})

    data = {'maxdate': maxdate, 'shown': shown, 'weeks': weeks, 'area': area, 'ema': ema,
            'ema_set': ema_set, 'span': args.ema_span, 'regimes': regimes, 'cur_since': cur_since,
            'movers': movers, 'pos3': {'union': union, 'windows': windows}, 'cur_table': cur,
            'pos_movers': pos_movers, 'pos_top': args.pos_top}

    # --- optional deck-specific matchups (the "my deck" overlay) ---
    if args.deck:
        m_cur = build_matrix(con, since=cur_since); m_all = build_matrix(con)
        mu = []
        for opp in shown:
            if opp == args.deck:
                continue
            for win, mm in [('current', m_cur), ('all-time', m_all)]:
                c = lookup_head_to_head(mm, args.deck, opp)
                if not c or c.n == 0:
                    mu.append({'opp': opp, 'window': win, 'wr': None, 'n': 0, 'tier': 'none', 'display': False})
                else:
                    p = c.p_shrunk if c.p_shrunk is not None else c.p_raw
                    mu.append({'opp': opp, 'window': win, 'wr': round(100 * p, 1) if p is not None else None,
                               'n': c.n, 'tier': str(c.tier), 'display': bool(c.display)})
        data['matchups'] = mu
    return data


# ── rendering ─────────────────────────────────────────────────────────────────
def svg(spec):
    from legacy_engine.viz.render import VIZ_VL_VERSION
    return vlc.vegalite_to_svg(json.dumps(spec), vl_version=VIZ_VL_VERSION)


def render_meta(d, args):
    shown = d['shown']
    CS1 = {"domain": list(shown), "range": [PALETTE[i % len(PALETTE)] for i in range(len(shown))]}

    def comp_chart(width, title, since=None):
        area = [dict(a) for a in d['area'] if a['archetype'] != 'Other' and (since is None or a['week'] >= since)]
        ema = [e for e in d['ema'] if since is None or e['week'] >= since]
        regs = [{**r, 'slabel': r['label'][:16]} for r in d['regimes'] if since is None or r['date'] >= since]
        tot = {}
        for a in area:
            tot[a['archetype']] = tot.get(a['archetype'], 0) + a['share']
        wrank = {arch: i for i, arch in enumerate(sorted(tot, key=lambda x: -tot[x]))}
        for a in area:
            a['o'] = wrank.get(a['archetype'], 99)
        return {"title": {"text": title, "color": "#E6E6E6", "fontSize": 13, "anchor": "start"},
                "width": width, "height": 360, "layer": [
            {"data": {"values": area}, "mark": {"type": "area", "opacity": 0.78, "line": False},
             "encoding": {"x": {"field": "week", "type": "temporal", "title": None},
                          "y": {"field": "share", "type": "quantitative", "stack": "zero", "title": "share of field (%)"},
                          "color": {"field": "archetype", "type": "nominal", "scale": CS1, "legend": None},
                          "order": {"field": "o", "type": "quantitative", "sort": "ascending"}}},
            {"data": {"values": ema}, "mark": {"type": "line", "strokeWidth": 2.8, "opacity": 1.0, "interpolate": "monotone"},
             "encoding": {"x": {"field": "week", "type": "temporal"},
                          "y": {"field": "ema", "type": "quantitative", "scale": {"zero": False},
                                "axis": {"orient": "right", "title": "deck own-share, EMA (%)", "grid": False, "titleColor": "#AEB3B8"}},
                          "color": {"field": "archetype", "type": "nominal", "scale": CS1, "legend": None}}},
            {"data": {"values": regs}, "mark": {"type": "rule", "strokeDash": [4, 3], "color": "#E6E6E6", "opacity": 0.45},
             "encoding": {"x": {"field": "date", "type": "temporal"}}},
            {"data": {"values": regs}, "mark": {"type": "text", "angle": -90, "align": "left", "baseline": "middle",
                                                "dx": 2, "fontSize": 8, "color": "#AEB3B8"},
             "encoding": {"x": {"field": "date", "type": "temporal"}, "y": {"value": 354}, "text": {"field": "slabel"}}}
        ], "resolve": {"scale": {"y": "independent"}}}

    chart1 = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "background": "#15181C", "config": DARK,
              "hconcat": [comp_chart(440, "Full history"),
                          comp_chart(300, f"Last {args.last_months} months", since=_last_cut(d, args)),
                          comp_chart(230, f"Current regime (≥ {d['cur_since']})", since=d['cur_since'])],
              "resolve": {"scale": {"y": "independent", "color": "shared"}}}

    P3 = d['pos3']; UNION = P3['union']
    CSU = {"domain": list(UNION), "range": gen_colors(len(UNION))}

    def pos_cell(win, key, ytitle, show_y):
        pts = [{'deck': p['deck'], 'date': p['date'], 'val': p[key], 'tier': p['tier']} for p in win['pts'] if p.get(key) is not None]
        return {"title": {"text": win['label'], "color": "#E6E6E6", "fontSize": 12, "anchor": "start"},
                "width": 260, "height": 190, "layer": [
            {"mark": {"type": "rule", "color": "#5A6068", "strokeDash": [2, 2]}, "encoding": {"y": {"datum": 50}}},
            {"data": {"values": pts}, "mark": {"type": "line", "strokeWidth": 1.9, "point": {"size": 42, "filled": True}, "interpolate": "monotone"},
             "encoding": {"x": {"field": "date", "type": "temporal", "title": None},
                          "y": {"field": "val", "type": "quantitative", "title": (ytitle if show_y else None), "scale": {"zero": False}},
                          "color": {"field": "deck", "type": "nominal", "scale": CSU, "legend": None},
                          "opacity": {"condition": {"test": "datum.tier=='speculative'", "value": 0.5}, "value": 1.0}}}
        ]}

    def pos_row(key, ytitle):
        return {"hconcat": [pos_cell(w, key, ytitle, i == 0) for i, w in enumerate(P3['windows'][:2])],
                "resolve": {"scale": {"y": "shared"}}}
    chart3 = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "background": "#15181C", "config": DARK,
              "vconcat": [pos_row('u', 'Best deck Ū (win %)'), pos_row('s', 'Best call S (win %)')],
              "resolve": {"scale": {"color": "shared"}}}

    svg_meta, svg_pos = svg(chart1), svg(chart3)

    # tables + legends
    def sw(name, color):
        return f'<span class="sw"><i style="background:{color}"></i>{name}</span>'
    legend1 = ''.join(sw(n, c) for n, c in zip(CS1['domain'], CS1['range']))
    legend3 = ''.join(sw(n, c) for n, c in zip(CSU['domain'], CSU['range']))

    def cellmv(items, up):
        col = '#5fd0a8' if up else '#ef8a6b'
        out = [f'<span class="mv" style="color:{col}">{it["a"]} {"+" if it["d"]>0 else ""}{it["d"]}pp</span> '
               f'<span class="mvs">({it["p"]}→{it["c"]}%)</span>' for it in items[:3]]
        return '<br>'.join(out) if out else '<span class="mvs">—</span>'

    def rscells(lst):
        if not lst:
            return '<td class="mvs">—</td>' * 3
        fade = lambda r: ' style="opacity:.55"' if r.get('tier') == 'speculative' else ''
        v = lambda x, s='%': f'{x}{s}' if x is not None else '<span class="mvs">n/a</span>'
        wr = '<br>'.join(f'<span{fade(r)}><b>{v(r["wr"])}</b> <span class="mvs">n={r["wr_n"]}</span></span>' for r in lst)
        u = '<br>'.join(f'<span{fade(r)}>{v(r["u"])}</span>' for r in lst)
        s = '<br>'.join(f'<span{fade(r)}>{v(r["s"])}</span>' for r in lst)
        return f'<td>{wr}</td><td>{u}</td><td>{s}</td>'
    mrows = ''.join(
        f'<tr><td class="mvd"><b>{m["to_date"]}</b><br><span class="mvs">{m["ban"]}</span></td>'
        f'<td>{cellmv(m["risers"], True)}</td>{rscells(m.get("rs_list"))}'
        f'<td>{cellmv(m["fallers"], False)}</td>{rscells(m.get("fs_list"))}</tr>'
        for m in reversed(d['movers']))
    movers_html = (f'<table class="movers"><tr><th>Regime · ban</th><th>Biggest risers ↑</th>'
                   f'<th>Riser WR</th><th>Riser Ū</th><th>Riser S</th><th>Biggest fallers ↓</th>'
                   f'<th>Faller WR</th><th>Faller Ū</th><th>Faller S</th></tr>{mrows}</table>')

    ctcol = lambda dk: CSU['range'][CSU['domain'].index(dk)] if dk in CSU['domain'] else '#C9CDD2'
    ctrows = ''
    for r in d['cur_table']:
        fade = ' style="opacity:.7"' if r.get('tier') == 'speculative' else ''
        s = f'<i style="background:{ctcol(r["deck"])};display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px"></i>'
        ctrows += (f'<tr{fade}><td>{s}{r["deck"]}</td><td><b>{r["wr"]}%</b></td>'
                   f'<td>{r["u"]}%</td><td>{r["s"]}%</td><td class="mvs">{r["tier"]}</td></tr>')
    cur_table_html = (f'<table class="movers"><tr><th>Deck — current regime (by best-call S)</th>'
                      f'<th>WR</th><th>Best-deck Ū</th><th>Best-call S</th><th>tier</th></tr>{ctrows}</table>')

    def pmcell(items, up):
        if not items:
            return '<span class="mvs">—</span>'
        col = '#5fd0a8' if up else '#ef8a6b'; out = []
        fv = lambda x: f'{x}' if x is not None else '–'
        for it in items:
            fade = ' style="opacity:.6"' if it.get('tier') == 'speculative' else ''
            dd = f"+{it['delta']}" if it['delta'] > 0 else f"{it['delta']}"
            out.append(f'<div{fade}><span class="mv" style="color:{col}">{it["deck"]} {dd}</span> '
                       f'<span class="mvs">{fv(it["wr"])}/{fv(it["u"])}/{fv(it["s"])}</span></div>')
        return ''.join(out)
    pmrows = ''.join(
        f'<tr><td class="mvd"><b>{m["to_date"]}</b><br><span class="mvs">{m["ban"][:16]}</span></td>'
        f'<td>{pmcell(m["bd_r"], True)}</td><td>{pmcell(m["bd_f"], False)}</td>'
        f'<td>{pmcell(m["bc_r"], True)}</td><td>{pmcell(m["bc_f"], False)}</td></tr>'
        for m in reversed(d['pos_movers']))
    pos_movers_html = (f'<table class="movers"><tr><th>Regime · ban</th><th>Best-deck Ū risers ↑</th>'
                       f'<th>Best-deck Ū fallers ↓</th><th>Best-call S risers ↑</th>'
                       f'<th>Best-call S fallers ↓</th></tr>{pmrows}</table>')

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Legacy meta landscape</title>
<style>
 body{{background:#15181C;color:#E6E6E6;font:14px 'Helvetica Neue',Arial,system-ui,sans-serif;margin:0;padding:30px 42px;max-width:1320px}}
 h1{{font-size:21px;font-weight:600;margin:0 0 3px}} h2{{font-size:16px;font-weight:600;margin:30px 0 4px;padding-top:16px;border-top:2px solid #23272C}}
 .sub{{color:#9AA0A6;font-size:12.5px;margin-bottom:10px}} .cap{{color:#9AA0A6;font-size:12px;font-style:italic;margin:6px 0 8px}}
 .vega svg{{max-width:100%;height:auto}}
 .movers{{border-collapse:collapse;width:100%;font-size:11.5px;margin:6px 0 4px}}
 .movers th{{text-align:left;color:#9AA0A6;font-weight:600;border-bottom:1px solid #2A2E33;padding:5px 7px;text-transform:uppercase;font-size:9.5px;letter-spacing:.4px}}
 .movers td{{vertical-align:top;padding:7px 7px;border-bottom:1px solid #1d2126;line-height:1.7}}
 .mvd{{white-space:nowrap}} .mvs{{color:#7d838a}} .mv{{font-weight:600}}
 .figrow{{display:flex;gap:22px;align-items:flex-start}} .figrow .vega{{flex:1 1 auto;min-width:0}}
 .legv{{flex:0 0 auto;font-size:11.5px;color:#C9CDD2;padding-top:6px}}
 .legv .sw{{display:flex;align-items:center;margin:0 0 5px 0;white-space:nowrap}}
 .legv .sw i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:7px;flex:0 0 auto}}
</style></head><body>
<h1>Legacy meta landscape</h1>
<div class="sub">weekly meta-share · {len(d['weeks'])} weeks through {d['maxdate']} · EMA span {d['span']}w · dashed = ban-regime boundaries</div>

<h2>1 · Meta composition + trends over time</h2>
<div class="cap">Bands = each tracked archetype's share of the field (long-tail "Other" omitted; y autoscales; ordered biggest-at-bottom <i>per panel</i>). Bold lines = each top deck's own share, EMA-smoothed (right axis). Panels: full history · last {args.last_months} months · current regime. Legend at right.</div>
<div class="figrow"><div class="vega">{svg_meta}</div><div class="legv">{legend1}</div></div>
<div class="cap" style="margin-top:14px"><b>Biggest meta-share movements at each ban boundary</b> (most recent first) — Δ in percentage points, (before→after % share). The Riser/Faller WR/Ū/S columns profile each mover in that regime: raw match win %, best-deck Ū, best-call S. Faded = speculative; n/a = too thin.</div>
{movers_html}

<h2>2 · Best deck vs best call — positioning over time</h2>
<div class="cap">Two rows (<b>best deck Ū</b> = quality regardless of field · <b>best call S</b> = expected win % given the actual field) × two windows. Each panel shows the <b>{d['pos_top']} best-positioned decks within that window</b>; the legend at right covers all of them. Faded = speculative; 50% dashed reference. Current regime is a single datapoint → snapshot table below.</div>
<div class="figrow"><div class="vega">{svg_pos}</div><div class="legv">{legend3}</div></div>
<div class="cap" style="margin-top:16px"><b>Current-regime snapshot</b> — the {d['pos_top']} best-positioned decks now by best-call S, with raw match WR, best-deck Ū, best-call S.</div>
{cur_table_html}
<div class="cap" style="margin-top:16px"><b>Positioning movers per ban regime</b> — biggest risers/fallers in best-deck Ū and best-call S vs the prior regime (most recent first). Δ in points; inline = that regime's WR/Ū/S. Faded = speculative.</div>
{pos_movers_html}
</body></html>"""


def _last_cut(d, args):
    return (date.fromisoformat(d['maxdate']) - timedelta(days=int(args.last_months * 30.44))).isoformat()


def render_matchups(d, deck):
    mu = d['matchups']; byopp = {}
    for r in mu:
        byopp.setdefault(r['opp'], {})[r['window']] = r
    fav = lambda wr: 'na' if wr is None else ('favorable' if wr >= 53 else ('unfavorable' if wr <= 47 else 'even'))
    oo = sorted(byopp, key=lambda o: -(byopp[o].get('all-time', {}).get('wr') or 0))
    FAV = {"domain": ["favorable", "even", "unfavorable", "na"], "range": ["#009E73", "#9AA0A6", "#D55E00", "#3A3F45"]}

    def recs(win):
        out = []
        for o in oo:
            r = byopp[o].get(win, {}); wr = r.get('wr') if r.get('display') else None
            out.append({'opp': o, 'wr': wr, 'tier': r.get('tier', 'none'), 'fav': fav(wr),
                        'lab': (f"{wr:.0f}%  n={r.get('n', 0)}" if wr is not None else f"n={r.get('n', 0)} · insufficient")})
        return out

    def mu_chart(win, title):
        return {"title": {"text": title, "color": "#E6E6E6", "fontSize": 13, "anchor": "start"},
                "width": 300, "height": {"step": 26}, "data": {"values": recs(win)}, "layer": [
            {"mark": {"type": "rule", "color": "#5A6068"}, "encoding": {"x": {"datum": 50}}},
            {"mark": {"type": "bar", "height": 15}, "encoding": {
                "y": {"field": "opp", "type": "nominal", "sort": oo, "title": None},
                "x": {"field": "wr", "type": "quantitative", "scale": {"domain": [0, 100]}, "title": "win %"},
                "color": {"field": "fav", "type": "nominal", "scale": FAV, "legend": None},
                "opacity": {"condition": {"test": "datum.tier=='established'", "value": 1.0}, "value": 0.55}}},
            {"mark": {"type": "text", "align": "left", "dx": 4, "color": "#C9CDD2", "fontSize": 10},
             "encoding": {"y": {"field": "opp", "type": "nominal", "sort": oo}, "x": {"value": 2}, "text": {"field": "lab"}}}
        ]}
    chart = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "background": "#15181C", "config": DARK,
             "hconcat": [mu_chart('all-time', 'All-time'), mu_chart('current', f"Current regime (≥ {d['cur_since']})")]}
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{_html.escape(deck)} — matchups</title>
<style>
 body{{background:#15181C;color:#E6E6E6;font:14px 'Helvetica Neue',Arial,system-ui,sans-serif;margin:0;padding:30px 42px;max-width:900px}}
 h1{{font-size:21px;font-weight:600;margin:0 0 3px}} .sub{{color:#9AA0A6;font-size:12.5px;margin-bottom:10px}}
 .cap{{color:#9AA0A6;font-size:12px;font-style:italic;margin:6px 0 8px}}
 .banner{{background:#3a2f12;border-left:3px solid #E69F00;color:#f0d9a0;padding:8px 12px;border-radius:4px;font-size:12.5px;margin:10px 0 6px}}
 .vega svg{{max-width:100%;height:auto}}
</style></head><body>
<h1>{_html.escape(deck)} — matchups vs the field</h1>
<div class="sub">data through {d['maxdate']} · current ban regime vs all-time</div>
<div class="banner">⚠ Current-regime matchup samples are thin (most pairings n&lt;30) — shown honestly as "insufficient". All-time carries the reliable signal.</div>
<div class="cap">Win % is Beta-Binomial-shrunk; left of 50% = unfavorable (vermillion), right = favorable (green); faded = evolving/speculative. Sorted by all-time win %.</div>
<div class="vega">{svg(chart)}</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path, help="meta-view .html output path")
    ap.add_argument("--bands-top", type=int, default=12, help="Section 1 stacked-area archetypes (default 12)")
    ap.add_argument("--pos-top", type=int, default=20, help="Section 2 best-positioned decks per window (default 20)")
    ap.add_argument("--ema-span", type=int, default=6, help="EMA span in weeks (default 6)")
    ap.add_argument("--ema-lines", type=int, default=7, help="how many archetypes get EMA trend lines (default 7)")
    ap.add_argument("--last-months", type=int, default=12, help="span of the 'last N months' panel (default 12)")
    ap.add_argument("--min-week-total", type=int, default=25, help="drop weeks with fewer total decks (default 25)")
    ap.add_argument("--regime-min-matches", type=int, default=200, help="skip regimes below this match volume (default 200)")
    ap.add_argument("--deck", default=None, help="also emit a deck-specific matchups view for this archetype")
    ap.add_argument("--matchups-out", type=Path, default=None, help="matchups .html path (with --deck)")
    ap.add_argument("--db", default=str(DUCKDB_PATH))
    args = ap.parse_args()

    con = duckdb.connect(args.db, read_only=True)
    try:
        data = compute(con, args)
    finally:
        con.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_meta(data, args))
    print(f"wrote {args.out}")
    if args.deck:
        mout = args.matchups_out or args.out.with_name(re.sub(r'\W+', '-', args.deck.lower()).strip('-') + '-matchups.html')
        mout.parent.mkdir(parents=True, exist_ok=True)
        mout.write_text(render_matchups(data, args.deck))
        print(f"wrote {mout}")


if __name__ == "__main__":
    main()
