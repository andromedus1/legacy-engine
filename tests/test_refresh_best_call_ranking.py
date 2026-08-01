"""Hermetic tests for ``scripts/refresh_best_call_ranking.py`` (multi-split one-pass migration).

The headline is **the script-level parity test**: the one-pass camp sweep (ONE
``build_multi_split_adaptive`` + one ``build_multi_split_matrix`` per distinct ban-scoped
fallback date) must reproduce the retired per-parent path — 30 ``split_variant`` builds —
field-for-field on every camp row: cells (p/raw/ci/n/window/tier/measured per opponent),
row stats, era window, horizon text, and row order.  The old path is reconstructed verbatim
in ``_old_path_camp_rows`` below (same shared context, same ``make_cells``/``row_stats``),
so a regression in the migration — e.g. the per-pair ``max(subj_ban, opp_ban)`` Nadu-rule
fallback selection — fails this diff, not a downstream eyeball.

The fixture extends the shared two-parent corpus with a PRE-BAN, rounds-bearing Painter
tournament (Painter ran Entomb before its 2025-11-10 ban) plus a camp-exact era row for
``Painter [Grindstone]``, so the ban-scoped fallback windows carry real numeric weight: the
``(Painter [Grindstone], Control)`` cell reads n=15 under the correct ``BA 2025-11-10``
window and would read n=30 if anything ever let the full corpus leak in.

Also covered: the additive cross-camp P(best) fields (candidacy gated by the same coverage
threshold that gates display), whole-blob determinism under the fixed seed, the audit
lines, and a hermetic ``main()`` end-to-end render against a tmp file DB (never the
default DB).
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

from legacy_engine.analytics.affectedness import archetype_valid_since
from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary
from legacy_engine.analytics.eras.store import write_entity_eras
from legacy_engine.analytics.matchup import build_adaptive_matrix, build_matrix
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

from test_match_results_multi_split import (  # noqa: E402  (sibling test module, sys.path via rootdir)
    LATE_DATE,
    PARENTS,
    build_two_parent_corpus,
)
from test_matchup_multi_split import (  # noqa: E402
    MID_DATE,
    _load_pre_ban_delver_decks,
)

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "refresh_best_call_ranking.py"
_spec = importlib.util.spec_from_file_location("refresh_best_call_ranking", _SCRIPT_PATH)
rbcr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rbcr)

# The additive cross-camp ranking fields — everything else must match the old path exactly.
_ADDITIVE_FIELDS = {"p_best", "s_q", "s_cov", "s_caveated"}

# Field window covering both fixture tournaments but neither pre-ban load.
_FIELD_SINCE = "2026-01-01"

_PRE_BAN_MATCH_DATE = "2025-10-01"  # inside [2025-03-31, 2025-11-10): the pre-Entomb regime


def _era_boundary(date: str) -> EraBoundary:
    return EraBoundary(
        date=date, signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False,
    )


def _load_pre_ban_painter_matches(con) -> None:
    """A rounds-BEARING pre-ban tournament: Painter decks running Entomb.

    Two effects, both essential to the Nadu-rule surface this file tests:
    (1) Painter's decks ran a banned card in >=25% of pre-ban lists, so
        ``archetype_valid_since`` dates Painter at 2025-11-10 — camp labels inherit it;
    (2) 15 real ``Painter [Grindstone]`` vs ``Control`` matches that ONLY a full-corpus
        window can see — the ban-scoped ``BA 2025-11-10`` fallback must exclude them.
    """
    roster = {
        "pp1": ("Painter", "Grindstone"),
        "pp2": ("Painter", "Welder"),
        "pp3": ("Painter", None),
        "cc1": ("Control", None),
    }
    raw = {
        "Tournament": {
            "Name": "best-call-pre-ban", "Date": _PRE_BAN_MATCH_DATE,
            "Uri": "https://example.test/best-call-pre-ban", "Formats": "Legacy",
        },
        "Decks": [
            {
                "Player": player, "Result": "1st Place",
                "Mainboard": [{"Count": 4, "CardName": "Entomb" if arch == "Painter" else "Brainstorm"}],
                "Sideboard": [],
            }
            for player, (arch, _variant) in roster.items()
        ],
        "Rounds": [
            *({"Player1": "pp1", "Player2": "cc1", "Result": "2-1"} for _ in range(10)),
            *({"Player1": "cc1", "Player2": "pp1", "Result": "2-0"} for _ in range(5)),
        ],
        "Standings": [],
    }
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
    for player, (arch, variant) in roster.items():
        con.execute(
            "UPDATE decks SET archetype=?, variant=? WHERE tournament_id=? AND player=?",
            [arch, variant, tid, player],
        )


_LATE2_DATE = "2026-05-25"  # after LATE_DATE: keeps every era window pinned by the rows below


def _load_murktide_control_reinforcement(con) -> None:
    """One more current tournament so (Doomsday [Murktide], Control) crosses the n>=30
    display gate INSIDE its era window (since MID_DATE) — giving the fixture at least one
    camp whose measured coverage clears the P(best) candidacy gate."""
    raw = {
        "Tournament": {
            "Name": "best-call-late2", "Date": _LATE2_DATE,
            "Uri": "https://example.test/best-call-late2", "Formats": "Legacy",
        },
        "Decks": [
            {"Player": "d1", "Result": "1st Place",
             "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []},
            {"Player": "c1", "Result": "2nd Place",
             "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []},
        ],
        "Rounds": [
            *({"Player1": "d1", "Player2": "c1", "Result": "2-1"} for _ in range(12)),
            *({"Player1": "c1", "Player2": "d1", "Result": "2-0"} for _ in range(4)),
        ],
        "Standings": [],
    }
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype='Doomsday', variant='Murktide' "
        "WHERE tournament_id=? AND player='d1'", [tid],
    )
    con.execute(
        "UPDATE decks SET archetype='Control', variant=NULL "
        "WHERE tournament_id=? AND player='c1'", [tid],
    )


def _build_fixture(con) -> None:
    """Corpus + pre-ban loads + reinforcement, shared by the :memory: and file-DB paths."""
    build_two_parent_corpus(con)
    _load_pre_ban_delver_decks(con)
    _load_pre_ban_painter_matches(con)
    _load_murktide_control_reinforcement(con)


def script_con():
    """Two-parent corpus + pre-ban loads + era rows covering all three horizon sources.

    ``Painter [Grindstone]`` gets its OWN era row at MID_DATE so its era cells truncate
    HARDER than its ban date — that is what forces the ban-scoped fallback into actual use
    for its pairs (era cell empty at MID, ``BA 2025-11-10`` cell measured).
    """
    con = store.connect(":memory:")
    _build_fixture(con)
    eras = {
        "Doomsday": EntityEras(
            entity="Doomsday", stable_since=LATE_DATE,
            boundaries=(_era_boundary(LATE_DATE),), inherited_from_parent=False,
        ),
        "Doomsday [Murktide]": EntityEras(
            entity="Doomsday [Murktide]", stable_since=MID_DATE,
            boundaries=(_era_boundary(MID_DATE),), inherited_from_parent=False,
        ),
        "Painter [Grindstone]": EntityEras(
            entity="Painter [Grindstone]", stable_since=MID_DATE,
            boundaries=(_era_boundary(MID_DATE),), inherited_from_parent=False,
        ),
        "Control": EntityEras(
            entity="Control", stable_since=None, boundaries=(), inherited_from_parent=False,
        ),
    }
    write_entity_eras(
        con, eras, {}, {},
        run_meta={
            "provenance": None, "alpha": 0.05, "run_at": "2026-07-31T00:00:00+00:00",
            "post_boundary_decks": {},
            "parent": {
                "Doomsday": "Doomsday",
                "Doomsday [Murktide]": "Doomsday",
                "Painter [Grindstone]": "Painter",
                "Control": "Control",
            },
        },
    )
    return con


def _blob(con, *, ground_n=3, min_row_share=0.001):
    return rbcr.compute_blob(
        con, field_since=_FIELD_SINCE, ground_n=ground_n, top_k=8, cover_min=0.8,
        min_row_share=min_row_share, regime_card=None, parents=sorted(PARENTS),
    )


# ---------------------------------------------------------------------------
# The retired per-parent path, reconstructed verbatim (the parity reference)
# ---------------------------------------------------------------------------


def _old_path_camp_rows(con, *, field_since, ground_n, top_k, cover_min, min_row_share,
                        parents):
    """The pre-migration camp sweep: one ``build_adaptive_matrix(split_variant=p)`` + one
    ``build_matrix(split_variant=p, since=d)`` per needed fallback date, PER PARENT — with
    the same shared context (shares, camp fractions, ban dates, field opponents) and the
    same ``make_cells``/``row_stats``/``horizon_text`` the script uses."""
    corpus_max = con.execute("select max(substr(date,1,10)) from tournaments").fetchone()[0]
    current_4wk = (dt.date.fromisoformat(corpus_max) - dt.timedelta(days=28)).isoformat()
    win_rows = con.execute(
        "select k.archetype, count(*) from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ? and k.archetype is not null and k.archetype <> '' "
        "group by 1", [field_since]).fetchall()
    field_decks = con.execute(
        "select count(*) from decks k join tournaments t on k.tournament_id=t.id "
        "where substr(t.date,1,10) >= ?", [field_since]).fetchone()[0]
    shares = {a: n / field_decks for a, n in win_rows} if field_decks else {}
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

    ad = build_adaptive_matrix(con, min_row_share=min_row_share)
    rows = ad.matrix.archetypes
    ban_since = archetype_valid_since(con, list(rows))
    field_opps = sorted((a for a in rows if shares.get(a, 0) > 0),
                        key=lambda a: shares[a], reverse=True)
    sh = {a: shares.get(a, 0.0) for a in [*rows, *field_opps]}

    camps_out = []
    for parent in parents:
        adp = build_adaptive_matrix(con, min_row_share=min_row_share, split_variant=parent)
        p_ban = ban_since.get(parent)
        p_dates = {max((d for d in (p_ban, ban_since.get(o)) if d), default=None)
                   for o in field_opps}
        fbp = {d: build_matrix(con, min_row_share=min_row_share, split_variant=parent,
                               since=d).cells for d in p_dates}
        prefix = f"{parent} ["
        for lbl in (r for r in adp.matrix.archetypes if r.startswith(prefix)):
            camp = lbl[len(prefix):-1]
            cells = rbcr.make_cells(lbl, field_opps, sh, adp.matrix.cells, fbp, ban_since,
                                    ground_n, subj_ban=p_ban)
            frac = camp_frac.get((parent, camp), 0.0)
            camps_out.append({
                "subject": lbl, **rbcr.row_stats(cells, top_k, cover_min),
                "since": adp.valid_since.get(lbl),
                "horizon": rbcr.horizon_text(adp.horizon_meta.get(lbl)),
                "cells": cells,
                "parent": parent, "camp": camp,
                "field_share": rbcr.r4(shares.get(parent, 0.0) * frac),
                "camp_fraction_current": rbcr.r4(frac),
                "recent_4wk": camp_recent.get((parent, camp), 0),
                "_idx": len(camps_out),
            })
    return camps_out


# ---------------------------------------------------------------------------
# Fixture substrate checks (what the Nadu-rule surface rests on)
# ---------------------------------------------------------------------------


class TestFixtureSubstrate:
    def test_painter_is_ban_affected_and_doomsday_is_not(self):
        con = script_con()
        valid = archetype_valid_since(con, ["Painter", "Doomsday", "Control", "Delver"])
        con.close()
        assert valid["Painter"] == "2025-11-10"  # ran Entomb pre-ban
        assert valid["Delver"] == "2025-11-10"
        assert valid["Doomsday"] is None
        assert valid["Control"] is None

    def test_all_three_window_sources_are_in_actual_use(self):
        """era / BA / FC all appear among USED camp cells — the parity diff below is
        covering every window-selection branch, not just the era-preferred happy path."""
        con = script_con()
        blob = _blob(con)
        con.close()
        windows = {c["window"] for r in blob["camps"] for c in r["cells"]}
        assert "era" in windows
        assert "BA 2025-11-10" in windows
        assert "FC" in windows


# ---------------------------------------------------------------------------
# THE PARITY TEST — one-pass camp rows == the retired per-parent path's
# ---------------------------------------------------------------------------


class TestScriptParity:
    @pytest.mark.parametrize(("min_row_share", "ground_n"), [
        (0.001, 3),
        (0.001, 8),
        (0.02, 3),
    ])
    def test_camp_rows_equal_the_per_parent_path(self, min_row_share, ground_n):
        con = script_con()
        old = _old_path_camp_rows(
            con, field_since=_FIELD_SINCE, ground_n=ground_n, top_k=8, cover_min=0.8,
            min_row_share=min_row_share, parents=sorted(PARENTS),
        )
        blob = _blob(con, ground_n=ground_n, min_row_share=min_row_share)
        con.close()
        new = blob["camps"]
        assert len(old) == len(new)
        assert len(old) >= 6  # both parents' camps + unlabeled residues
        for old_row, new_row in zip(old, new):
            assert _ADDITIVE_FIELDS <= new_row.keys(), (
                f"additive ranking fields missing on {new_row['subject']!r}"
            )
            stripped = {k: v for k, v in new_row.items() if k not in _ADDITIVE_FIELDS}
            assert stripped == old_row, f"camp row parity broken for {new_row['subject']!r}"

    def test_nadu_rule_fallback_excludes_pre_ban_matches(self):
        """The exact protection the per-pair max(subj_ban, opp_ban) selection provides:
        (Painter [Grindstone], Control) has an empty era cell at its MID horizon, so the
        fallback is used — and it must be the ban-scoped BA 2025-11-10 cell (n=15), never
        the full corpus (n=30 — the 15 pre-ban Entomb-era matches would leak in)."""
        con = script_con()
        blob = _blob(con)
        con.close()
        row = next(r for r in blob["camps"] if r["subject"] == "Painter [Grindstone]")
        cell = next(c for c in row["cells"] if c["opp"] == "Control")
        assert cell["window"] == "BA 2025-11-10"
        assert cell["n"] == 15
        assert cell["measured"] is True


# ---------------------------------------------------------------------------
# Cross-camp P(best): the additive fields + their honesty gates
# ---------------------------------------------------------------------------


class TestCrossCampRanking:
    def test_candidacy_gate_matches_the_display_convention(self):
        """Every camp row carries the additive fields; a row below the suppression
        coverage is EXCLUDED from candidacy (p_best None, its coverage explaining why),
        a ranked row carries a probability and the S* caveat flag at the 0.85 rule."""
        con = script_con()
        blob = _blob(con)
        con.close()
        suppress = blob["meta"]["rank"]["suppress_cov"]
        caveat = blob["meta"]["rank"]["caveat_cov"]
        ranked = 0
        for r in blob["camps"]:
            assert _ADDITIVE_FIELDS <= r.keys()
            assert r["s_cov"] is not None
            if r["s_cov"] < suppress:
                assert r["p_best"] is None and r["s_q"] is None
            else:
                ranked += 1
                assert 0.0 <= r["p_best"] <= 1.0
                assert r["s_q"] is not None
                assert r["s_caveated"] == (r["s_cov"] < caveat)
        assert ranked >= 1  # the gate is not vacuous on this fixture
        assert ranked < len(blob["camps"])  # ...and neither is the suppression

    def test_p_best_mass_is_a_shared_budget(self):
        """Camp p_best values live in ONE argmax budget with the unsplit candidates —
        their sum can never exceed 1."""
        con = script_con()
        blob = _blob(con)
        con.close()
        mass = sum(r["p_best"] for r in blob["camps"] if r["p_best"] is not None)
        assert 0.0 <= mass <= 1.0 + 1e-9

    def test_whole_blob_is_deterministic_under_the_fixed_seed(self):
        con = script_con()
        first = _blob(con)
        second = _blob(con)
        con.close()
        assert first == second

    def test_meta_rank_params_and_audit_lines(self):
        con = script_con()
        blob = _blob(con)
        con.close()
        rank = blob["meta"]["rank"]
        assert rank["seed"] == rbcr.RANK_SEED
        assert rank["candidates"] <= rank["potential"]
        assert rank["basis"].startswith("page-used cells")
        audit = blob["meta"]["audit"]
        assert any(line.startswith("// multi-split: one pass over") for line in audit)
        assert any(line.startswith("// cross-camp P(best):") for line in audit)


# ---------------------------------------------------------------------------
# main() end-to-end against a tmp FILE DB (never the default DB)
# ---------------------------------------------------------------------------


class TestMainEndToEnd:
    def test_main_renders_the_page_from_a_tmp_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "best-call.duckdb"
        con = store.connect(str(db_path))
        try:
            # The full fixture build against the file-backed DB (never the default DB).
            _build_fixture(con)
        finally:
            con.close()
        out_path = tmp_path / "page.html"
        monkeypatch.setattr(rbcr, "staged_split_parents", lambda: sorted(PARENTS))
        monkeypatch.setattr(sys, "argv", [
            "refresh_best_call_ranking.py",
            "--db", str(db_path),
            "--out", str(out_path),
            "--field-since", _FIELD_SINCE,
            "--ground-n", "3",
        ])
        rbcr.main()
        html = out_path.read_text()
        assert "__D_BLOB__" not in html  # the blob was spliced
        assert '"p_best"' in html
        assert "// multi-split: one pass over" in html
        assert "P(best)" in html  # the camp table column ships in the template
