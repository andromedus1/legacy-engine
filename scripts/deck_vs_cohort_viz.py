#!/usr/bin/env python3
"""Render a decklist against a cohort's per-card copy-count distribution (HTML).

Prototype / template for the planned `feature-deck-doctor-viz` (see
.work/active/features/feature-deck-doctor-viz.md). Overlays a specific 75 against
a field cohort: for every card, the user's count vs the cohort's 0x/1x/2x/3x/4x
histogram, inclusion%, on-mode / off-distribution / missing tags, grouped by card
type and alphabetical. Carries the confidence tier (speculative/evolving/established)
as a visible banner — honest-degrade by default.

Sections: Maindeck · Sideboard (your cards only) · Sideboard — other cards the field
runs (cohort SB cards not in your list, above an inclusion floor).

The cohort defaults to the current ban regime (via the engine's
`_latest_regime_window()`); narrow it with --since / --require.

Usage:
  .venv/bin/python scripts/deck_vs_cohort_viz.py \
      --deck decks/dimir-tempo-current.txt \
      --archetype "Dimir Tempo" \
      --require "Flow State>=1" --require "Nethergoyf=3" \
      --out decks/dimir-tempo-vs-cohort.html

  # whole archetype in the current regime, no sub-filter:
  .venv/bin/python scripts/deck_vs_cohort_viz.py --deck <file> --archetype "<arch>" --out <html>

Notes:
  - --require takes "Card=N" (exact maindeck count) or "Card>=N" (at least N), repeatable.
    Used to carve a sub-cohort (e.g. the exact-3-Nethergoyf builds).
  - --since YYYY-MM-DD overrides the regime window start (default: current regime).
  - Decklist format: "<n> <Card Name>" lines; a line of "Sideboard" / "SIDEBOARD:"
    (any case, optional colon) starts the sideboard.
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import duckdb

from legacy_engine.config import DUCKDB_PATH
from legacy_engine.generation.consensus import _latest_regime_window

# copy-count colorway (Okabe-Ito-aligned; all readable with black text)
COL = {0: "#CC79A7", 1: "#56B4E9", 2: "#009E73", 3: "#E69F00", 4: "#D55E00"}
BG, TEXT, AXIS = "#15181C", "#E6E6E6", "#9AA0A6"
TYPE_ORDER = ["Creature", "Planeswalker", "Instant", "Sorcery", "Artifact",
              "Enchantment", "Battle", "Land", "Other"]
PLURAL = {"Sorcery": "Sorceries"}


def parse_deck(path: Path) -> tuple[dict[str, int], dict[str, int]]:
    main: dict[str, int] = {}
    side: dict[str, int] = {}
    cur = main
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        if re.fullmatch(r"sideboard:?", s, re.IGNORECASE):
            cur = side
            continue
        m = re.match(r"(\d+)\s+(.+)", s)
        if m:
            cur[m.group(2).strip()] = int(m.group(1))
    return main, side


def parse_requires(reqs: list[str]) -> list[tuple[str, str, int]]:
    out = []
    for r in reqs:
        m = re.match(r"(.+?)(>=|=)(\d+)$", r.strip())
        if not m:
            raise SystemExit(f"bad --require '{r}' (want 'Card=N' or 'Card>=N')")
        out.append((m.group(1).strip(), m.group(2), int(m.group(3))))
    return out


def primary_type(type_line: str) -> str:
    for t in TYPE_ORDER:
        if t != "Other" and t in type_line:
            return t
    return "Other"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deck", required=True, type=Path, help="decklist file")
    ap.add_argument("--archetype", required=True, help="cohort archetype label")
    ap.add_argument("--require", action="append", default=[],
                    help="cohort sub-filter 'Card=N' or 'Card>=N' (repeatable)")
    ap.add_argument("--since", default=None, help="window start YYYY-MM-DD (default: current regime)")
    ap.add_argument("--until", default=None, help="window end YYYY-MM-DD (default: open)")
    ap.add_argument("--db", default=str(DUCKDB_PATH), help="DuckDB path")
    ap.add_argument("--floor", type=float, default=9.0,
                    help="inclusion%% floor for the 'other cards' section (default 9)")
    ap.add_argument("--out", required=True, type=Path, help="output .html path")
    args = ap.parse_args()

    since, until = args.since, args.until
    if since is None and until is None:
        since, until = _latest_regime_window()
    requires = parse_requires(args.require)
    um, us = parse_deck(args.deck)

    con = duckdb.connect(args.db, read_only=True)
    where = ["d.archetype = ?", "t.date >= ?"]
    params: list = [args.archetype, since or "0000-01-01"]
    if until:
        where.append("t.date < ?")
        params.append(until)
    for name, op, n in requires:
        cmp = "= ?" if op == "=" else ">= ?"
        where.append(
            "EXISTS (SELECT 1 FROM deck_cards x WHERE x.tournament_id=d.tournament_id "
            "AND x.deck_idx=d.deck_idx AND x.name=? AND x.board='main' AND x.count " + cmp + ")")
        params.extend([name, n])
    con.execute(
        f"CREATE TEMP TABLE sub AS SELECT d.tournament_id, d.deck_idx "
        f"FROM decks d JOIN tournaments t ON d.tournament_id=t.id "
        f"WHERE {' AND '.join(where)} GROUP BY d.tournament_id, d.deck_idx", params)
    n = con.execute("SELECT count(*) FROM sub").fetchone()[0]
    if n == 0:
        raise SystemExit("cohort is empty — loosen --archetype / --require / --since")
    tier = "established" if n >= 100 else "evolving" if n >= 30 else "speculative"

    def dist(board: str) -> dict[str, dict[int, int]]:
        h: dict[str, dict[int, int]] = {}
        for name, cnt, c in con.execute(
            f"SELECT dc.name, dc.count, count(*) FROM deck_cards dc "
            f"JOIN sub ON dc.tournament_id=sub.tournament_id AND dc.deck_idx=sub.deck_idx "
            f"WHERE dc.board='{board}' GROUP BY dc.name, dc.count").fetchall():
            h.setdefault(name, {})[cnt] = c
        return h

    mh, sh = dist("main"), dist("side")
    names = set(mh) | set(sh) | set(um) | set(us)
    tl = {nm: (con.execute("SELECT type_line FROM cards WHERE name=?", [nm]).fetchone() or [""])[0] or ""
          for nm in names}
    con.close()

    def seg(h: dict[int, int], you: int) -> str:
        zero = n - sum(h.values())
        parts = []
        for k in (0, 1, 2, 3, 4):
            v = zero if k == 0 else h.get(k, 0)
            if not v:
                continue
            pct = 100 * v / n
            border = "box-shadow:inset 0 0 0 2px #E6E6E6;z-index:2;" if k == you else ""
            lab = f"{k}x // {pct:.0f}%" if pct >= 15 else (f"{pct:.0f}%" if pct >= 7 else "")
            parts.append(f'<div class="seg" style="width:{pct:.2f}%;background:{COL[k]};{border}" '
                         f'title="{k}x: {pct:.0f}% ({v}/{n})">{lab}</div>')
        return "".join(parts)

    def row(name: str, you: int, h: dict[int, int]) -> str:
        run = sum(h.values())
        incl = 100 * run / n
        at_you = (n - run) if you == 0 else h.get(you, 0)
        tag = ""
        if you == 0 and incl >= 40:
            tag = '<span class="tag miss">not in your list</span>'
        elif you > 0 and incl >= 40 and 100 * at_you / n < 10:
            tag = '<span class="tag off">off-distribution</span>'
        elif you > 0 and 100 * at_you / n >= 30:
            tag = '<span class="tag ok">on the mode</span>'
        return (f'<div class="row"><div class="name">{html.escape(name)}</div>'
                f'<div class="you">{you}</div><div class="bar">{seg(h, you)}</div>'
                f'<div class="incl">{incl:.0f}%</div><div class="status">{tag}</div></div>')

    def typed(cand: dict[str, tuple[int, dict[int, int]]]) -> str:
        out = []
        for t in TYPE_ORDER:
            g = sorted([nm for nm in cand if primary_type(tl.get(nm, "")) == t], key=str.lower)
            if g:
                title = PLURAL.get(t, t + ("s" if not t.endswith("s") else ""))
                out.append(f'<div class="grp">{title} <span class="cnt">{len(g)}</span></div>'
                           + "".join(row(nm, *cand[nm]) for nm in g))
        return "".join(out)

    def section(ulist: dict[str, int], H: dict[str, dict[int, int]], only_yours: bool) -> str:
        cand = {}
        for nm in set(ulist) | set(H):
            h = H.get(nm, {})
            you = ulist.get(nm, 0)
            if you == 0 and (only_yours or 100 * sum(h.values()) / n < 25):
                continue
            cand[nm] = (you, h)
        return typed(cand)

    main_sec = section(um, mh, only_yours=False)
    side_sec = section(us, sh, only_yours=True)
    others = {nm: (0, h) for nm, h in sh.items()
              if nm not in us and 100 * sum(h.values()) / n >= args.floor}
    below = sum(1 for nm, h in sh.items()
                if nm not in us and 100 * sum(h.values()) / n < args.floor)
    other_sec = typed(others)

    legend = " ".join(f'<span class="lg"><i style="background:{COL[k]}"></i>'
                      f'{k} cop{"y" if k == 1 else "ies"}</span>' for k in (0, 1, 2, 3, 4))
    head = (f'<div class="head"><div>Card</div><div>You</div>'
            f'<div>Cohort distribution (% of {n} decks at each copy count)</div>'
            f'<div>Run</div><div></div></div>')
    win = f"{since or '—'} → {until or 'now'}"
    req_txt = (" · cohort filter: " + ", ".join(f"{nm}{op}{v}" for nm, op, v in requires)) if requires else ""
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(args.archetype)} — deck vs cohort</title>
<style>
 body{{background:{BG};color:{TEXT};font:14px 'Helvetica Neue',Arial,system-ui,sans-serif;margin:0;padding:32px 40px}}
 h1{{font-size:20px;font-weight:600;margin:0 0 4px}} h2{{font-size:16px;font-weight:600;margin:34px 0 2px;padding-top:18px;border-top:2px solid #2A2E33}}
 .sub{{color:{AXIS};font-size:13px;margin-bottom:14px}} .sub2{{color:{AXIS};font-size:12.5px;margin:2px 0 12px}}
 .banner{{background:#3a2f12;border-left:3px solid #E69F00;color:#f0d9a0;padding:8px 12px;border-radius:4px;font-size:12.5px;margin-bottom:18px}}
 .note{{color:{AXIS};font-size:12px;font-style:italic;margin:10px 0 0}}
 .legend{{margin:0 0 14px;color:{AXIS};font-size:12px}} .lg{{margin-right:14px}} .lg i{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
 .head,.row{{display:grid;grid-template-columns:180px 30px 1fr 46px 132px;align-items:center;gap:10px}}
 .head{{color:{AXIS};font-size:11px;text-transform:uppercase;letter-spacing:.5px;padding-bottom:6px;border-bottom:1px solid #2A2E33;margin-bottom:6px}}
 .row{{padding:3px 0}} .grp{{margin:16px 0 6px;font-size:12px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#56B4E9;border-bottom:1px solid #2A2E33;padding-bottom:4px}} .grp .cnt{{color:{AXIS};font-weight:400}}
 .name{{font-size:13px}} .you{{text-align:center;font-weight:700;font-size:14px}}
 .bar{{display:flex;height:20px;border-radius:3px;overflow:hidden;background:#101316}} .seg{{display:flex;align-items:center;justify-content:center;font-size:10px;color:#0c0e10;font-weight:700;overflow:hidden;white-space:nowrap}}
 .incl{{text-align:right;color:{AXIS};font-size:12px}} .tag{{font-size:10.5px;padding:2px 7px;border-radius:10px;font-weight:600}}
 .miss{{background:#5a1f1f;color:#ffb3b3}} .off{{background:#5a4410;color:#ffd98a}} .ok{{background:#13352a;color:#7fe3c0}}
</style></head><body>
<h1>{html.escape(args.archetype)} — your deck vs the cohort</h1>
<div class="sub">window {win}{req_txt} · grouped by card type, alphabetical</div>
<div class="banner">⚠ {tier.upper()} confidence — cohort is n={n} decks. {'Directional, not settled.' if tier != 'established' else 'Sample is robust.'}</div>
<div class="legend">{legend} &nbsp; · &nbsp; white outline = <b>your</b> count</div>
<h2>Maindeck</h2><div class="sub2">your maindeck vs the cohort · field staples you don't run are flagged</div>{head}{main_sec}
<h2>Sideboard — your cards</h2><div class="sub2">only the cards in your sideboard · 0-copy share is over all {n} cohort decks</div>{head}{side_sec}
<h2>Sideboard — other cards the field runs</h2><div class="sub2">cohort sideboard cards not in your list (inclusion ≥ {args.floor:.0f}%)</div>{head}{other_sec}
<div class="note">{below} rarer cards (&lt;{args.floor:.0f}%) omitted as singletons.</div>
</body></html>"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(doc)
    print(f"wrote {args.out}  (cohort n={n}, tier={tier})")


if __name__ == "__main__":
    main()
