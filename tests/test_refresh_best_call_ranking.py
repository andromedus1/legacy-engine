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
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from legacy_engine.advisory.ranking_benchmark import BenchmarkEvaluationSummary, content_sha256
from legacy_engine.advisory.best_call_targets import ReportTarget

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
from test_matchup_superarchetype import (  # noqa: E402
    _hero_con,
    _hero_registry,
)

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "refresh_best_call_ranking.py"
_spec = importlib.util.spec_from_file_location("refresh_best_call_ranking", _SCRIPT_PATH)
rbcr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rbcr)


def test_benchmark_validation_payload_has_honest_default_and_artifact_identity(tmp_path):
    assert rbcr.benchmark_validation_payload(None) == {
        "status": "not-run", "artifact_id": None, "protocol_hash": None,
        "reason": "no benchmark summary artifact supplied to page generation",
    }
    summary = BenchmarkEvaluationSummary(
        protocol_hash="protocol", folds=(), evaluable_folds=0, represented_regimes=0,
        paired_differences={}, status="not-evaluable", reasons=("support unavailable",),
    )
    path = tmp_path / "summary.json"
    path.write_text(summary.model_dump_json())
    payload = rbcr.benchmark_validation_payload(path)
    assert payload == {
        "status": "not-evaluable", "artifact_id": content_sha256(summary),
        "protocol_hash": "protocol", "reason": "support unavailable",
    }
    template = rbcr.TEMPLATE_PATH.read_text()
    assert "future-only validation: ${validation.status}" in template
    assert "artifact ${validation.artifact_id || \"none\"}" in template


def test_detailed_diagnostics_are_bounded_to_top_field_opponents():
    rows = [{
        "subject": "A",
        "ranking_evidence": {"eligible": True},
        "cells": [
            {"opp": f"O{index}", "share": share}
            for index, share in enumerate((0.05, 0.40, 0.10, 0.30, 0.15))
        ],
    }]

    assert rbcr._diagnostic_pair_keys(rows, limit=3) == {
        ("A", "O1"), ("A", "O3"), ("A", "O4"),
    }
    rows[0]["ranking_evidence"]["eligible"] = False
    assert rbcr._diagnostic_pair_keys(rows, limit=3) == set()


def _run_template_javascript(blob: dict, probe: str) -> dict:
    """Execute the tracked report script with a minimal DOM and return a JSON probe."""
    template = rbcr.TEMPLATE_PATH.read_text()
    script = template.split("<script>", 1)[1].split("</script>", 1)[0]
    script = script.replace("__D_BLOB__", json.dumps(blob), 1)
    harness = r"""
const fs = require("fs");
const vm = require("vm");
class Element {
  constructor() {
    this.attrs = {}; this.listeners = {}; this.textContent = ""; this.innerHTML = "";
    this.value = ""; this.disabled = false; this.title = ""; this.style = {};
    this.dataset = {}; this.children = []; this.selected = false; this.hidden = false;
  }
  append(child) { this.children.push(child); }
  get selectedOptions() { return this.children.filter(child => child.selected); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  focus() {}
}
const elements = new Map();
const document = {
  getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
  createElement() { return new Element(); },
  querySelectorAll() { return []; },
  querySelector() { return null; },
};
const saved = new Map();
const localStorage = {
  getItem(key) { return saved.has(key) ? saved.get(key) : null; },
  setItem(key, value) { saved.set(key, String(value)); },
};
const window = {location: {href: ""}};
const context = vm.createContext({document, localStorage, window,
  CSS: {escape: value => String(value)}});
vm.runInContext(fs.readFileSync(0, "utf8"), context);
const result = vm.runInContext(process.argv[1], context);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", harness, probe], input=script, text=True,
        capture_output=True, check=True,
    )
    return json.loads(completed.stdout)

# The additive cross-camp ranking fields — everything else must match the old path exactly.
_ADDITIVE_FIELDS = {
    "p_best", "s_q", "s_cov", "s_caveated", "floor_observability", "reconciliation",
    "ranking_evidence", "field_share_raw", "methodology", "observed_count", "prior_count",
    "decision_share", "field_evidence_kind", "camp_fraction_decision",
}

# Field window covering both fixture tournaments but neither pre-ban load.
_FIELD_SINCE = "2026-01-01"

_PRE_BAN_MATCH_DATE = "2025-10-01"  # inside [2025-03-31, 2025-11-10): the pre-Entomb regime


def test_every_measured_cell_can_set_the_floor():
    cells = [
        {"opp": "bad", "share": .4, "p": .39, "n": 8, "measured": True},
        {"opp": "good", "share": .6, "p": .58, "n": 20, "measured": True},
    ]

    stats = rbcr.row_stats(cells, top_k=2, cover_min=.8)

    assert stats["floor"] == .39
    assert stats["floor_opp"] == "bad"
    assert stats["agency"] == .39


def test_ranking_row_payload_carries_reconciliation_and_floor_observability():
    payload = rbcr.row_stats(
        [{"opp": "bad", "share": 1.0, "p": .39, "n": 8, "measured": True}],
        top_k=1,
        cover_min=.8,
    )
    assert payload["reconciliation"]["headline_eligible"] is True
    assert payload["reconciliation"]["parity_delta"] == 0.0
    assert payload["floor_observability"]["floor_observed"] is False
    assert "absence of bad cells" in payload["floor_observability"]["reason"]


def test_positive_raw_presence_below_display_rounding_is_not_inactive():
    row = {"field_share": 0.0, "field_share_raw": 0.000049, "grounded": False}
    evidence = rbcr.ranking_evidence_for_row(
        row, measured_share=0.10, resolved_cells=1,
    )
    assert evidence["stratum"] != "inactive"
    assert evidence["eligible"] is True


def test_exact_zero_raw_presence_is_inactive():
    row = {"field_share": 0.0, "field_share_raw": 0.0, "grounded": True}
    evidence = rbcr.ranking_evidence_for_row(
        row, measured_share=1.0, resolved_cells=10,
    )
    assert evidence["stratum"] == "inactive"
    assert evidence["reason"] == "no current-field presence"


def test_make_cells_embeds_both_sources_for_interactive_sample_gate():
    def cell(n, p):
        return SimpleNamespace(
            n=n, p_shrunk=p, p_raw=p, ci_low=p - .1, ci_high=p + .1,
            tier="speculative",
        )

    cells = rbcr.make_cells(
        "Hero", ["Villain"], {"Villain": 1.0},
        {("Hero", "Villain"): cell(5, .45)},
        {None: {("Hero", "Villain"): cell(12, .55)}},
        {"Villain": None}, 8,
    )

    assert cells[0]["window"] == "FC" and cells[0]["n"] == 12
    assert cells[0]["sources"]["era"]["n"] == 5
    assert cells[0]["sources"]["fallback"]["n"] == 12


def test_make_cells_ledger_is_canonical_browser_projection_at_same_gate():
    def cell(n, p):
        return SimpleNamespace(
            n=n, p_shrunk=p, p_raw=p, ci_low=p - .123456, ci_high=p + .123456,
            tier="speculative", concentration=None,
        )

    cells = rbcr.make_cells(
        "Hero", ["Villain"], {"Villain": 1 / 3},
        {("Hero", "Villain"): cell(8, .555555)},
        {None: {("Hero", "Villain"): cell(20, .444444)}},
        {"Villain": None}, 8,
    )
    rendered = cells[0]
    ledger = rendered["ledger"]
    assert ledger["field_share"] == rendered["share"] == 0.3333
    assert ledger["selected"]["cell"]["p_shrunk"] == rendered["p"] == 0.5556
    stats = rbcr.row_stats(cells, top_k=1, cover_min=0.0)
    assert stats["adj"] == rendered["p"]


def test_interactive_sources_carry_their_own_concentration_warning():
    from legacy_engine.models.matchup import CellConcentration

    def cell(n, p, event):
        concentration = CellConcentration(
            event_id=event, event_n=n, event_share=1.0,
            month="2026-07", month_n=n, month_share=1.0,
        )
        return SimpleNamespace(
            n=n, p_shrunk=p, p_raw=p, ci_low=p - .1, ci_high=p + .1,
            tier="speculative", concentration=concentration,
        )

    rendered = rbcr.make_cells(
        "Hero", ["Villain"], {"Villain": 1.0},
        {("Hero", "Villain"): cell(5, .45, "era-event")},
        {None: {("Hero", "Villain"): cell(12, .55, "fallback-event")}},
        {"Villain": None}, 8,
    )[0]
    assert "era-event" in rendered["ledger"]["era"]["concentration_warning"]
    assert "fallback-event" in rendered["ledger"]["fallback"]["concentration_warning"]
    assert "fallback-event" in rendered["concentration_warning"]


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
        "pp4": ("Painter", "Relic"),
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
            *({"Player1": "pp4", "Player2": "cc1", "Result": "2-1"} for _ in range(2)),
            {"Player1": "cc1", "Player2": "pp4", "Result": "2-0"},
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


def _current_target() -> ReportTarget:
    return ReportTarget(
        target_id="current",
        label="Current </script><script>alert(1)</script>",
        mode="current",
        mode_label="Current",
        data_until=None,
        effective_data_until=dt.date(2026, 5, 26),
        knowledge_as_of=dt.datetime(2026, 8, 16, tzinfo=dt.UTC),
        field_since=dt.date(2026, 5, 18),
        regime_card="Undercity Informer",
    )


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
                                    ground_n, subj_ban=p_ban, ad_windows=adp.cell_windows,
                                    valid_since=adp.valid_since)
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
            old_stripped = {k: v for k, v in old_row.items() if k not in _ADDITIVE_FIELDS}
            assert stripped == old_stripped, f"camp row parity broken for {new_row['subject']!r}"

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

    def test_selected_cells_surface_event_or_month_concentration(self):
        con = script_con()
        blob = _blob(con, ground_n=3)
        con.close()
        warnings = [
            cell["concentration_warning"]
            for row in [*blob["arch"], *blob["camps"]]
            for cell in row["cells"]
            if cell.get("concentration_warning")
        ]
        assert warnings
        assert any("selected window" in warning and "matches" in warning for warning in warnings)


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
        caveat = blob["meta"]["rank"]["caveat_cov"]
        ranked = 0
        for r in blob["camps"]:
            assert _ADDITIVE_FIELDS <= r.keys()
            assert r["s_cov"] is not None
            if not r["ranking_evidence"]["eligible"]:
                assert r["p_best"] is None and r["s_q"] is None
            else:
                ranked += 1
                assert 0.0 <= r["p_best"] <= 1.0
                assert r["s_q"] is not None
                assert r["s_caveated"] == (r["s_cov"] < caveat)
        assert ranked >= 1  # the gate is not vacuous on this fixture
        assert any(
            not item["eligible"]
            for item in [
                *(row["ranking_evidence"] for row in blob["camps"]),
            ]
        ) or blob["meta"]["rank"]["candidates"] < blob["meta"]["rank"]["potential"]

    def test_p_best_mass_is_a_shared_budget(self):
        """Camp p_best values live in ONE argmax budget with the unsplit candidates —
        their sum can never exceed 1."""
        con = script_con()
        blob = _blob(con)
        con.close()
        mass = sum(r["p_best"] for r in blob["camps"] if r["p_best"] is not None)
        assert 0.0 <= mass <= 1.0 + 1e-9
        assert blob["meta"]["rank"]["camp_pbest_total"] == pytest.approx(mass, abs=1e-3)
        assert blob["meta"]["rank"]["pbest_total"] == pytest.approx(1.0)

    def test_inactive_zero_cell_camp_is_visible_but_excluded_with_warning(self):
        con = script_con()
        blob = _blob(con)
        con.close()
        row = next(r for r in blob["camps"] if r["subject"] == "Painter [Relic]")
        assert row["field_share"] == 0.0
        assert row["ranking_evidence"]["stratum"] == "inactive"
        assert row["ranking_evidence"]["reason"] == "no current-field presence"
        assert row["p_best"] is None and row["s_q"] is None
        assert any(
            line.startswith("// [warn] ranking subject Painter [Relic]: no resolved")
            for line in blob["meta"]["audit"]
        )

    def test_ranker_and_page_coverage_are_identical_at_generated_gate(self):
        con = script_con()
        blob = _blob(con, ground_n=8)
        con.close()
        for row in blob["camps"]:
            assert row["s_cov"] == pytest.approx(row["coverage"], abs=5e-5)

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
        assert any(line.startswith("// ranking evidence:") for line in audit)


class TestMethodologyDiagnostics:
    def test_rows_carry_deterministic_lean_variants_stability_and_grounding(self):
        con = script_con()
        first = _blob(con)
        second = _blob(con)
        con.close()
        assert first["meta"]["methodology"] == second["meta"]["methodology"]
        assert first["meta"]["methodology"]["lean"] == {
            "seed": rbcr.LEAN_SEED,
            "draws": rbcr.LEAN_DRAWS,
            "temperature": rbcr.LEAN_TEMPERATURE,
            "precision_scale": rbcr.LEAN_PRECISION_SCALE,
            "basis": "era preferred without n cliff; absent-era fallback; weak unresolved prior",
            "authority": "diagnostic only; gated agency remains headline",
        }
        for left, right in zip(
            [*first["arch"], *first["camps"]],
            [*second["arch"], *second["camps"]],
        ):
            assert left["methodology"] == right["methodology"]
            method = left["methodology"]
            assert set(method["variants"]) == {
                "raw", "ci-gated", "ban-scoped", "era-only",
            }
            assert method["variants"]["ci-gated"]["agency"] == pytest.approx(
                left["agency"], abs=5e-5,
            )
            assert 0.0 <= method["lean"]["q25"] <= 1.0
            assert "stability" in method and "grounding" in method

    def test_stability_uses_exact_positive_presence_not_display_rounding(self):
        class Cell:
            n = 12
            p_raw = 0.5
            p_shrunk = 0.5
            ci_low = 0.3
            ci_high = 0.7
            tier = "speculative"
            concentration = None

        cells = rbcr.make_cells(
            "Tiny", ["Opp"], {"Opp": 1.0}, {("Tiny", "Opp"): Cell()},
            {None: {("Tiny", "Opp"): Cell()}}, {"Opp": None}, 8,
        )
        stats = rbcr.row_stats(cells, top_k=1, cover_min=0.8)
        base = {
            "subject": "Tiny", **stats, "cells": cells, "field_share": 0.0,
            "field_share_raw": 0.000049, "recent_4wk": 1, "_idx": 0,
        }
        active = rbcr.methodology_payload(
            [base], peer_key="test", ground_n=8, top_k=1, cover_min=0.8,
            lean_draws=100, lean_seed=3,
        )["Tiny"]["stability"]
        assert active["rank_span"] == 0
        assert active["missing_variants"] == []

        inactive = rbcr.methodology_payload(
            [{**base, "field_share_raw": 0.0}], peer_key="test", ground_n=8,
            top_k=1, cover_min=0.8, lean_draws=100, lean_seed=3,
        )["Tiny"]["stability"]
        assert inactive["rank_span"] is None
        assert set(inactive["missing_variants"]) == {
            "raw", "ci-gated", "ban-scoped", "era-only",
        }

    def test_plan_grounding_adapter_excludes_structural_diagonal(self):
        plan = {
            "cells": [
                {
                    "opponent": "Self", "share": 0.9, "n": 100,
                    "measured": False, "structural_same_plan": True,
                },
                {
                    "opponent": "Other", "share": 0.1, "n": 2,
                    "measured": False, "structural_same_plan": False,
                },
            ],
        }
        path = rbcr.plan_grounding_payload(
            plan, ground_n=8, top_k=8, cover_min=0.8,
        )
        assert [action["opponent"] for action in path["actions"]] == ["Other"]
        assert path["actions"][0]["additional_matches"] == 6

    def test_methodology_audit_names_authority_and_variants(self):
        con = script_con()
        blob = _blob(con)
        con.close()
        line = next(
            line for line in blob["meta"]["audit"]
            if line.startswith("// methodology diagnostics:")
        )
        assert "raw / CI-gated / ban-scoped / era-only" in line
        assert "gated agency remains authoritative" in line


# ---------------------------------------------------------------------------
# Strategic-plan dropdown evidence remains independent of the composition overlay.
# ---------------------------------------------------------------------------

_HERO_FIELD_SINCE = "2020-01-01"  # covers both hero tournaments (field basis, not cell windows)


def _hero_blob(con, superarchetypes=None):
    return rbcr.compute_blob(
        con, field_since=_HERO_FIELD_SINCE, ground_n=8, top_k=8, cover_min=0.8,
        min_row_share=0.001, regime_card=None, parents=[], superarchetypes=superarchetypes,
    )


def _cell(blob, subj, opp):
    row = next(r for r in blob["arch"] if r["subject"] == subj)
    return next(c for c in row["cells"] if c["opp"] == opp)


@pytest.fixture(scope="module")
def hero_blobs():
    con = _hero_con()
    off = _hero_blob(con)
    on = _hero_blob(con, superarchetypes=_hero_registry())
    con.close()
    return off, on


class TestSuperarchetypeIsolation:
    def test_rows_are_identical_when_composition_overlay_is_present(self, hero_blobs):
        off, on = hero_blobs
        for table in ("arch", "camps"):
            assert len(on[table]) == len(off[table])
            for r_on, r_off in zip(on[table], off[table]):
                assert r_on == r_off

    def test_meta_has_no_superarchetype_presentation_audit(self, hero_blobs):
        off, on = hero_blobs
        assert on["meta"] == off["meta"]
        assert not any("superarchetype fallback" in line for line in on["meta"]["audit"])

    def test_camp_rows_do_not_gain_family_lean_payloads(self):
        con = _hero_con()
        con.execute(
            "update decks set variant=case "
            "when player='h1' then 'Alpha' when player='h2' then 'Beta' else variant end "
            "where archetype='Hero'"
        )
        kwargs = dict(
            field_since=_HERO_FIELD_SINCE, ground_n=8, top_k=8, cover_min=0.8,
            min_row_share=0.001, regime_card=None, parents=["Hero"],
        )
        off = rbcr.compute_blob(con, **kwargs)
        on = rbcr.compute_blob(con, superarchetypes=_hero_registry(), **kwargs)
        con.close()

        assert len(on["camps"]) == len(off["camps"]) == 2
        for r_on, r_off in zip(on["camps"], off["camps"]):
            assert r_on == r_off
            assert all("sa" not in cell for cell in r_on["cells"])


class TestStrategicPlanPresentation:
    def test_strategic_plan_payload_is_independent_of_composition_overlay(self, hero_blobs):
        off, on = hero_blobs
        assert on["plans"] == off["plans"]
        assert [plan["id"] for plan in on["plans"]] == [
            "disrupt-pressure", "go-off", "go-over", "go-wide", "lock-outlast",
        ]
        hero_plan = on["plans"][0]
        assert hero_plan["members"][0]["archetype"] == "Hero"
        assert hero_plan["members"][0]["secondary"] == ["go-off"]
        assert len(hero_plan["cells"]) == 5
        same = next(cell for cell in hero_plan["cells"] if cell["structural_same_plan"])
        assert same["p"] == .5 and not same["measured"]
        assert (same["wins"], same["losses"], same["n"]) == (0, 0, 0)
        assert same["observed_n"] >= 0 and same["mirror_n"] >= 0

    def test_archetype_rows_lead_with_exact_plan_cells_and_no_family_leans(self, hero_blobs):
        _off, on = hero_blobs
        hero = next(row for row in on["arch"] if row["subject"] == "Hero")
        assert hero["strategic_plan"] == {
            "primary": "disrupt-pressure", "secondary": ["go-off"],
        }
        assert [cell["opponent_id"] for cell in hero["plan_cells"]] == [
            "disrupt-pressure", "go-off", "go-over", "go-wide", "lock-outlast",
        ]
        assert all({"wins", "losses", "mirror_n", "n", "raw", "p", "measured",
                    "same_primary_plan", "since", "provenance"} <= cell.keys()
                   for cell in hero["plan_cells"])
        assert all("sa" not in cell for row in on["arch"] for cell in row["cells"])


# ---------------------------------------------------------------------------
# main() end-to-end against a tmp FILE DB (never the default DB)
# ---------------------------------------------------------------------------


class TestMainEndToEnd:
    def test_atomic_write_failure_preserves_last_good_ranking(self, tmp_path, monkeypatch):
        out_path = tmp_path / "ranking.html"
        out_path.write_bytes(b"last-good-ranking")
        temp_path = tmp_path / ".ranking.html.injected.tmp"

        class FailingTemp:
            name = str(temp_path)
            def __enter__(self):
                temp_path.write_bytes(b"partial")
                return self
            def write(self, text):
                raise OSError("disk full")
            def __exit__(self, *args):
                return None

        monkeypatch.setattr(rbcr.tempfile, "NamedTemporaryFile", lambda **kwargs: FailingTemp())

        with pytest.raises(OSError, match="disk full"):
            rbcr._atomic_write_text(out_path, "replacement")

        assert out_path.read_bytes() == b"last-good-ranking"
        assert not temp_path.exists()

    def test_generate_ranking_callable_matches_cli_defaults(self, tmp_path, monkeypatch):
        db_path = tmp_path / "callable.duckdb"
        con = store.connect(str(db_path))
        try:
            _build_fixture(con)
        finally:
            con.close()
        direct_path = tmp_path / "direct.html"
        cli_path = tmp_path / "cli.html"
        monkeypatch.setattr(rbcr, "staged_split_parents", lambda: sorted(PARENTS))
        rbcr.generate_ranking(
            db_path=db_path, out_path=direct_path, field_since=_FIELD_SINCE, ground_n=3,
        )
        monkeypatch.setattr(sys, "argv", [
            "refresh_best_call_ranking.py", "--db", str(db_path), "--out", str(cli_path),
            "--field-since", _FIELD_SINCE, "--ground-n", "3",
        ])
        rbcr.main()
        assert direct_path.read_bytes() == cli_path.read_bytes()

    def test_blowouts_are_classified_from_raw_measured_win_rate(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "if (!c.measured || c.raw == null" in template
        assert "if (c.raw < 0.40)" in template
        assert "else if (c.raw < 0.45)" in template
        assert "if (c.p != null && c.p < 0.40)" not in template
        assert "else if (c.p != null && c.p < 0.45)" not in template

    def test_positive_matchup_highlights_use_symmetric_raw_wr_bands(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "else if (c.raw > 0.60)" in template
        assert 'class=\\"edge-dominant\\"' in template
        assert "else if (c.raw >= 0.55)" in template
        assert 'class=\\"edge\\"' in template
        assert "dominant (&gt;60%)" in template
        assert "edge (55–60%)" in template

    def test_measurement_honesty_surfaces_are_rendered(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "fixed generated-threshold reconciliation" in template
        assert "display-grade floor" in template
        assert "floorObservabilityHtml" in template
        assert "c.concentration_warning" in template
        assert 'title="${escA(c.concentration_warning)}">⚠ concentrated</span>' in template
        assert '<div class="evidence-warn">${escT(c.concentration_warning)}</div>' not in template

    def test_interactive_gate_labels_generated_evidence_and_disables_grouping(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "function rankingEvidenceIsCurrent(r)" in template
        assert "function canGroupRankingEvidence(rows)" in template
        assert "generated n=${D.meta.ground_n}" in template
        assert "control.disabled = stale" in template
        assert "groupByRankingEvidence = false" in template
        assert "camp && groupByRankingEvidence && generatedEvidenceCurrent" in template

    def test_executed_browser_defaults_ties_and_disclosure_state(self):
        cell = {
            "opp": "Opponent", "share": 1.0, "p": 0.55, "raw": 0.55,
            "ci_low": 0.4, "ci_high": 0.7, "n": 8, "tier": "speculative",
            "measured": True, "window": "era", "concentration_warning": None,
        }
        camp = {
            "_idx": 0, "parent": "Parent", "camp": "Camp", "subject": "Parent [Camp]",
            "grounded": True, "recent_4wk": 10, "agency": 0.55, "adj": 0.55,
            "floor": 0.55, "floor_opp": "Opponent", "coverage": 1.0,
            "field_share": 0.1, "since": None, "cells": [cell], "p_best": 0.2,
            "s_cov": 1.0, "s_q": 0.55, "s_caveated": False,
            "ranking_evidence": {
                "stratum": "grounded", "measured_share": 1.0,
                "imputed_share": 0.0, "eligible": True, "reason": None,
            },
            "reconciliation": None, "floor_observability": None, "methodology": {},
            "best_available_estimate": {
                "estimate": 0.56, "direct_match_n": 19, "added_history_n": 11,
                "estimated_cells": 1, "total_cells": 2, "field_coverage": 0.63,
                "basis": "localized-clean-direct", "confidence": "moderate",
                "proof_grade": False,
            },
        }
        arch = {
            **camp, "subject": "Parent", "parent": None, "camp": None,
        }
        blob = {
            "meta": {
                "ground_n": 8, "top_k": 1, "cover_min": 0.5, "rank": {"quantile": 0.25},
                "field_since": "2026-01-01", "field_decks": 100, "corpus_max": "2026-01-31",
                "regime_card": None, "audit": [
                    "// ranking evidence: 1 eligible, 1 quarantined",
                    "// [warn] ranking subject Empty Camp: no resolved page-used matchup cells; P(best)=n/a",
                ],
            },
            "arch": [arch], "camps": [camp], "plans": [],
            "report_target": {
                "target_id": "before-test", "label": "Before hostile </option>",
                "mode_label": "Today's model", "data_until": "2026-01-31",
                "effective_data_until": "2026-01-31",
                "knowledge_as_of": "2026-08-16T00:00:00+00:00",
            },
        }
        result = _run_template_javascript(blob, r"""
(() => {
  const initial = {
    interactiveN: D.camps[0]._interactiveN,
    pbest: pbestHtml(D.camps[0]),
    sortValue: CAMP_COLS[5].get(D.camps[0]),
    row: rowHtml(D.camps[0], 0, true),
    campHeaders: CAMP_COLS.length,
    campCells: (rowHtml(D.camps[0], 0, true).match(/<td/g) || []).length,
    archHeaders: COLS.length,
    archCells: (rowHtml(D.arch[0], 0, false).match(/<td/g) || []).length,
  };
  const tied = {
    subject: "Deck", cells: [
      {opp:"Zulu",share:.5,p:.55,raw:.55,n:8,measured:true},
      {opp:"Alpha",share:.5,p:.55,raw:.55,n:7,measured:false},
    ], plan_cells: [],
  };
  recalcRow(tied, 8);
  const toggle = {attrs:{}, setAttribute(k,v){this.attrs[k]=String(v);}};
  setRowDisclosureState(toggle, true);
  const expanded = toggle.attrs["aria-expanded"];
  setRowDisclosureState(toggle, false);
  recalcRow(D.camps[0], 9);
  return {
    initial, tiedGrounded: tied.grounded, expanded,
    collapsed: toggle.attrs["aria-expanded"], stalePbest: pbestHtml(D.camps[0]),
    targetControlHidden: document.getElementById("target-control").hidden,
    targetOption: document.getElementById("report-target").children[0].textContent,
    targetMode: document.getElementById("target-mode").textContent,
    targetStatus: document.getElementById("target-status").textContent,
    headerAudit: document.getElementById("audit").textContent,
    warningSummary: document.getElementById("ranking-subject-warning-summary").textContent,
    warningLines: document.getElementById("ranking-subject-warning-lines").textContent,
  };
})()
""")
        assert result["initial"]["interactiveN"] == 8
        assert result["initial"]["sortValue"] == pytest.approx(0.2)
        assert result["initial"]["pbest"].startswith("20.0%")
        assert result["initial"]["campCells"] == result["initial"]["campHeaders"]
        assert result["initial"]["archCells"] == result["initial"]["archHeaders"]
        assert "56.0%" in result["initial"]["row"]
        assert "covered-field estimate" in result["initial"]["row"]
        assert "clean history + current" in result["initial"]["row"]
        assert "estimate shown · not proof-grade" in result["initial"]["row"]
        assert result["targetControlHidden"] is False
        assert "Before hostile </option>" in result["targetOption"]
        assert result["targetMode"] == "Today’s model"
        assert result["targetStatus"].startswith("Exclusive data cutoff")
        assert "ranking evidence: 1 eligible" in result["headerAudit"]
        assert "[warn] ranking subject" not in result["headerAudit"]
        assert result["warningSummary"] == "Ranking exclusions and diagnostics (1)"
        assert "[warn] ranking subject Empty Camp" in result["warningLines"]
        assert 'aria-expanded="false"' in result["initial"]["row"]
        assert 'aria-controls="row-detail-c-0"' in result["initial"]["row"]
        assert result["tiedGrounded"] is False
        assert result["expanded"] == "true"
        assert result["collapsed"] == "false"
        assert result["stalePbest"].startswith("n/a")

    def test_evidence_column_and_opt_in_grouping_are_accessible_and_value_preserving(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert 'id="ranking-strata"' in template
        assert 'aria-pressed="false"' in template
        assert "function evidenceHtml(r)" in template
        assert "groupByRankingEvidence" in template
        assert "visibleRows.filter(r => (r.ranking_evidence || {}).stratum === label)" in template
        assert "renderTable(\"t-camp\", D.camps, true)" in template

    def test_methodology_control_is_accessible_and_keeps_authority_boundaries(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert 'id="first-read"' not in template
        assert "renderPracticalFirstRead" not in template
        assert 'id="methodology-view"' in template
        assert 'aria-label="Ranking methodology view"' in template
        assert 'id="methodology-status" class="methodology-status" aria-live="polite"' in template
        assert "let usePosteriorLean = false" in template
        assert "Posterior lean diagnostic active; gated candidacy and P(best) unchanged" in template
        assert "tableState[\"t-arch\"].col = 2" in template
        assert "tableState[\"t-camp\"].col = 2" in template

    def test_methodology_copy_distinguishes_decision_field_and_direct_estimates(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "transition-stabilized decision field" in template
        assert "affected archetypes are" in template
        assert "excluded from that preceding-regime prior" in template
        assert "A field reset does not erase matchup history" in template
        assert "Direct matchup estimate is diagnostic" in template
        assert "exact union of eligible clean intervals" in template
        assert "does not change Agency, its floor, grounding" in template
        assert "P(best), or ordering" in template

    def test_ranking_subject_warnings_are_in_a_bottom_disclosure_not_the_header(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        warning_id = 'id="ranking-subject-warnings"'
        assert warning_id in template
        assert template.index("<h2>Subarchetypes (camps)</h2>") < template.index(warning_id)
        assert "const rankingSubjectWarnings = (M.audit || []).filter" in template
        assert "const headerAudit = (M.audit || []).filter" in template
        assert "document.getElementById(\"ranking-subject-warning-lines\").textContent" in template

    def test_stability_and_grounding_mark_generated_gate_staleness(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "function stabilityHtml(r)" in template
        assert "function groundingPathHtml(r)" in template
        assert "if (!rankingEvidenceIsCurrent(r))" in template
        assert "stale — generated at n=${D.meta.ground_n}" in template
        assert "additional cells not shown" in template
        assert "total additional matches" in template

    def test_lean_diagnostic_exposes_interval_imputation_and_divergence(self):
        template = rbcr.TEMPLATE_PATH.read_text()
        assert "function leanDetailHtml(r)" in template
        assert "Q25 diagnostic posterior" in template
        assert "95% ${fmtP(lean.ci_low)}–${fmtP(lean.ci_high)}" in template
        assert "resolved /" in template
        assert "gated−lean" in template

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
        assert 'position: sticky' in html
        assert 'id="coverage-arch"' in html
        assert 'id="coverage-camp"' in html
        assert 'id="sample-plan"' in html
        assert 'id="sample-arch"' in html
        assert 'id="sample-camp"' in html
        assert 'class="hint" role="note"' in html
        assert 'class="hint-label">Interactive tables' in html
        assert "function selectCell(c, minN)" in html
        assert "function recalcRow(r, minN)" in html
        assert "function recalcPlan(r, minN)" in html
        assert 'class="${cls} expander plan-expander"' in html
        assert 'el.querySelectorAll("tr.plan-expander")' in html
        assert "event.stopPropagation()" in html
        assert 'rows.filter(r => r.coverage >= st.minCoverage)' in html

    def _render(self, tmp_path, db_name, out_name, *, registry=None, extra_argv=(),
                monkeypatch=None):
        """Render the hero corpus through main() against a tmp FILE DB; the registry (when
        given) is served the production way — rebuilt DuckDB tables read back by main()."""
        from legacy_engine.analytics.superarchetype.registry import (
            rebuild_superarchetype_members,
        )

        db_path = tmp_path / db_name
        con = _hero_con(str(db_path))
        try:
            if registry is not None:
                rebuild_superarchetype_members(con, registry)
        finally:
            con.close()
        out_path = tmp_path / out_name
        monkeypatch.setattr(rbcr, "staged_split_parents", list)
        monkeypatch.setattr(sys, "argv", [
            "refresh_best_call_ranking.py",
            "--db", str(db_path), "--out", str(out_path),
            "--field-since", _HERO_FIELD_SINCE,
            *extra_argv,
        ])
        rbcr.main()
        return out_path.read_text()

    def test_main_omits_family_leans_and_serves_archetype_plan_evidence(self, tmp_path, monkeypatch):
        html = self._render(
            tmp_path, "hero-sa.duckdb", "on.html",
            registry=_hero_registry(), monkeypatch=monkeypatch,
        )
        assert '"plan_cells": [' in html
        assert '"strategic_plan": {' in html
        assert "Against strategic plans" in html
        assert "Exact archetype matchups" in html
        assert "saCellHtml" not in html
        assert '"sa":' not in html
        assert "// superarchetype fallback:" not in html
        assert ".table-scroll > table > thead > tr > th { position: sticky" in html
        assert ".plan-ledger thead" not in html
        assert 'id="coverage-plan"' in html
        assert 'id="t-plan"' in html
        assert 'class="plan-toggle"' in html
        assert 'aria-expanded=' in html and 'aria-controls=' in html
        assert 'function planDetailHtml' in html
        assert '"plans": [' in html
        assert 'id="taxonomy-root"' not in html
        assert 'id="family-heatmap"' not in html
        assert 'id="camp-heatmap"' not in html
        assert 'renderFamilyHeatmap' not in html
        assert 'renderCampHeatmap' not in html

    def test_no_superarchetypes_flag_equals_the_registry_absent_page(self, tmp_path, monkeypatch):
        """--no-superarchetypes on a registry-bearing DB must be byte-identical to the page
        from a DB with no registry tables at all — the baseline stays reachable."""
        absent = self._render(
            tmp_path, "hero-bare.duckdb", "bare.html", monkeypatch=monkeypatch,
        )
        flagged = self._render(
            tmp_path, "hero-flagged.duckdb", "flagged.html",
            registry=_hero_registry(), extra_argv=("--no-superarchetypes",),
            monkeypatch=monkeypatch,
        )
        assert flagged == absent
        assert '"sa"' not in flagged


class TestEvidenceTargetIntegration:
    def test_unqualified_cli_builds_typed_direct_evidence_without_artifact_tables(
        self, tmp_path, monkeypatch
    ):
        db_path = tmp_path / "ranking.duckdb"
        con = store.connect(db_path)
        _build_fixture(con)
        con.close()
        out_path = tmp_path / "current.html"
        captured = {}
        original = rbcr.generate_ranking

        def capture(**kwargs):
            captured["calls"] = captured.get("calls", 0) + 1
            captured["target"] = kwargs["target"]
            captured["blob"] = original(**kwargs)
            return captured["blob"]

        monkeypatch.setattr(rbcr, "generate_ranking", capture)
        monkeypatch.setattr(rbcr, "staged_split_parents", lambda: sorted(PARENTS))
        monkeypatch.setattr(sys, "argv", [
            "refresh_best_call_ranking.py", "--db", str(db_path), "--out", str(out_path),
            "--ground-n", "3",
        ])

        rbcr.main()

        target = captured["target"]
        blob = captured["blob"]
        assert target is not None
        assert target.certificate_run_id is None
        assert target.amplification_run_id is None
        assert captured["calls"] == 1
        assert blob["meta"]["report_utility"]["estimated_rows"] > 0
        assert all("best_available_estimate" in row for row in blob["arch"])
        rendered = out_path.read_text()
        assert "direct matchup estimate" in rendered
        assert "covered-field estimate" in rendered

    def test_current_target_attaches_diagnostics_without_changing_authority(
        self, tmp_path
    ):
        db_path = tmp_path / "ranking.duckdb"
        con = store.connect(db_path)
        _build_fixture(con)
        con.close()
        baseline = rbcr.generate_ranking(
            db_path=db_path,
            out_path=tmp_path / "baseline.html",
            field_since="2026-05-18",
            ground_n=3,
            data_until="2026-05-26",
        )
        target_path = tmp_path / "target.html"
        attached = rbcr.generate_ranking(
            db_path=db_path,
            out_path=target_path,
            target=_current_target(),
            ground_n=3,
        )
        assert rbcr.canonical_json(rbcr._authority_payload(attached)) == rbcr.canonical_json(
            baseline
        )
        assert attached["evidence"]["status"] == "not-assessed"
        assert "pairs" not in attached["evidence"]
        assert attached["evidence"]["pair_scope"] == (
            "top-4-current-field-opponents-per-supported-row"
        )
        assert attached["meta"]["report_utility"]["estimated_rows"] > 0
        utility = attached["meta"]["report_utility"]
        assert (utility["grounded_rows"] > 0) == (utility["proof_grade_call"] is not None)
        assert (
            utility["affected_estimate_cells"] + utility["unaffected_estimate_cells"]
            == utility["visible_estimate_cells"]
        )
        assert all("best_available_estimate" in row for row in attached["arch"])
        assert all("diagnostic_evidence" in row for row in attached["arch"])
        assert attached["camps"]
        for row in attached["camps"]:
            pairs = row["diagnostic_evidence"]["pairs"]
            if not row["ranking_evidence"]["eligible"]:
                assert not pairs
                continue
            assert pairs
            assert all(
                "camp-current-only" in pair["reasons"]
                and pair["current_only"]["match_ids_sha256"]
                == pair["certified_expanded"]["match_ids_sha256"]
                and pair["added_history"]["n"] == 0
                for pair in pairs
            )
        rendered = target_path.read_text()
        assert "Current </script><script>alert(1)</script>" not in rendered
        assert "\\u003c/script\\u003e" in rendered
        assert "Evidence diagnostics — diagnostic only" in rendered

    def test_retrospective_blob_is_invariant_to_cutoff_date_and_future_rows(
        self, tmp_path
    ):
        db_path = tmp_path / "ranking.duckdb"
        con = store.connect(db_path)
        _build_fixture(con)
        con.close()
        target = ReportTarget(
            target_id="before-informer",
            label="Before Undercity Informer",
            mode="retrospective-current-model",
            mode_label="Today's model",
            data_until=dt.date(2026, 5, 18),
            effective_data_until=dt.date(2026, 5, 18),
            knowledge_as_of=dt.datetime(2026, 8, 16, tzinfo=dt.UTC),
            field_since=dt.date(2025, 11, 10),
            regime_card="Entomb",
        )
        before = rbcr.generate_ranking(
            db_path=db_path,
            out_path=tmp_path / "before.html",
            target=target,
            ground_n=3,
        )
        con = store.connect(db_path)
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            ["future", "future", "2026-05-18", "", "Legacy", "mtgo", "online"],
        )
        con.executemany(
            "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("future", 0, "future-a", "", "Doomsday", "hostile </script>"),
                ("future", 1, "future-b", "", "Control", None),
            ],
        )
        con.execute(
            "INSERT INTO rounds VALUES (?, ?, ?, ?, ?)",
            ["future", 0, "future-a", "future-b", "2-0"],
        )
        con.execute(
            "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
            ["future", 0, "main", "Undercity Informer", 4],
        )
        con.close()
        after = rbcr.generate_ranking(
            db_path=db_path,
            out_path=tmp_path / "after.html",
            target=target,
            ground_n=3,
        )
        assert rbcr.canonical_json(before) == rbcr.canonical_json(after)
        audit = after["meta"]["target_data_audit"]
        assert all(
            section["max_event_date"] is None
            or section["max_event_date"] < "2026-05-18"
            for section in audit["sections"]
        )
        con = store.connect(db_path)
        con.execute("UPDATE tournaments SET date='2026-05-17' WHERE id='future'")
        con.close()
        moved_inside = rbcr.generate_ranking(
            db_path=db_path,
            out_path=tmp_path / "moved-inside.html",
            target=target,
            ground_n=3,
        )
        assert (
            moved_inside["meta"]["target_data_audit"]["audit_sha256"]
            != audit["audit_sha256"]
        )
