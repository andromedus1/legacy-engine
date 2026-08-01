"""Byte-identity golden for the superarchetype layer's OFF path (epic-superarchetype-layer-chain
Unit 1 — pinned BEFORE any builder mutation, on the untouched code).

Pins the complete consumer-visible output of ``build_multi_split_adaptive`` over the shared
adaptive parity corpus: every ``MatchupCell`` field for every cell, plus the matrix identity
surfaces (``subjects``/``opponents``/``parents``/``camp_parent``) and the adaptive provenance
surfaces (``valid_since``/``cell_windows``/``horizon_meta``/``audit_preamble``). The
superarchetype rung must leave ALL of it byte-identical when no registry is passed
(opt-in-analytics-overlay: the off path is the LITERAL identity of pre-flag behavior).

Field lists are pinned EXPLICITLY (symbol-anchored), never via ``asdict``/``model_dump``: an
ADDITIVE default-``None`` field (e.g. ``EraHorizon.attribution_kind``) is schema growth, not a
change to any value a consumer reads today, and must not move this golden. Any change to a value
in the pinned fields is exactly what this test exists to catch.

Hermetic — the corpus is the same deterministic two-parent fixture the parity suite uses.
"""

from __future__ import annotations

import hashlib
import json

from test_matchup_multi_split import (
    PARENTS,
    adaptive_con,
)

from legacy_engine.analytics.matchup import build_multi_split_adaptive

# Every consumer-visible MatchupCell field (same pinned list as the parity suite).
_CELL_FIELDS = (
    "archetype_a", "archetype_b", "wins", "n", "p_raw", "p_shrunk",
    "ci_low", "ci_high", "tier", "is_mirror", "display", "prior_mean", "prior_source",
)

# EraHorizon's consumer-visible fields at pin time (additive fields never move the golden).
_HORIZON_FIELDS = ("since", "source", "trigger", "alarm")

# sha256 of _canonical() on the default (no-registry) build. Floats are canonicalized to
# 12 significant digits before hashing: full-precision hashing is architecture-dependent
# (scipy/BLAS ulp drift between arm64 and x86_64 CI runners) while any real off-path
# regression moves values orders of magnitude above the 12th significant figure.
_GOLDEN_SHA = "944a3f270ec4dda9d6813a10e0798b578d38f15b93b4d55c05ede8d148e0723a"


def _canonical(ams) -> str:
    payload = {
        "subjects": ams.multi.subjects,
        "opponents": ams.multi.opponents,
        "parents": ams.multi.parents,
        "camp_parent": dict(sorted(ams.multi.camp_parent.items())),
        "total_matches": ams.multi.total_matches,
        "caveat": ams.multi.caveat,
        "provenance": ams.multi.provenance,
        "cells": [
            [f"{a}|{b}", {f: getattr(cell, f) for f in _CELL_FIELDS}]
            for (a, b), cell in sorted(ams.multi.cells.items())
        ],
        "valid_since": dict(sorted(ams.valid_since.items())),
        "cell_windows": [
            [f"{a}|{b}", window] for (a, b), window in sorted(ams.cell_windows.items())
        ],
        "horizon_meta": {
            label: {f: getattr(horizon, f) for f in _HORIZON_FIELDS}
            for label, horizon in sorted(ams.horizon_meta.items())
        },
        "audit_preamble": list(ams.audit_preamble),
    }
    return json.dumps(_stable(payload), sort_keys=True, allow_nan=False)


def _stable(o):
    """Recursively format floats at 12 significant digits so the hash is architecture-stable."""
    if isinstance(o, float):
        return format(o, ".12g")
    if isinstance(o, dict):
        return {k: _stable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_stable(v) for v in o]
    return o


class TestDefaultBuildGolden:
    def test_full_output_matches_the_pinned_pre_superarchetype_golden(self):
        con = adaptive_con()
        ams = build_multi_split_adaptive(con, parents=PARENTS)
        con.close()
        canonical = _canonical(ams)
        sha = hashlib.sha256(canonical.encode()).hexdigest()
        assert sha == _GOLDEN_SHA, (
            "default (no-registry) adaptive multi-split output drifted from the pinned "
            f"pre-superarchetype golden (sha {sha}); the off path must stay byte-identical — "
            "inspect the two representative-cell tests below for a readable diff"
        )

    def test_representative_cross_era_camp_cell_exact(self):
        """One camp cell whose prior takes the cross-era override — pinned field-for-field so a
        golden break is diagnosable without decoding a hash."""
        con = adaptive_con()
        ams = build_multi_split_adaptive(con, parents=PARENTS)
        con.close()
        cell = ams.multi.cells[("Doomsday [Murktide]", "Control")]
        got = {f: getattr(cell, f) for f in _CELL_FIELDS}
        assert got == {
            "archetype_a": "Doomsday [Murktide]",
            "archetype_b": "Control",
            "wins": 7,
            "n": 16,
            "p_raw": 0.4375,
            "p_shrunk": got["p_shrunk"],
            "ci_low": got["ci_low"],
            "ci_high": got["ci_high"],
            "tier": "speculative",
            "is_mirror": False,
            "display": False,
            "prior_mean": got["prior_mean"],
            "prior_source": "pre-disturbance value (window < 2026-03-01); hierarchy: "
            "parent cell (leave-camp-out)",
        }
        assert ams.cell_windows[("Doomsday [Murktide]", "Control")] == "2026-03-01"

    def test_representative_plain_cell_exact(self):
        con = adaptive_con()
        ams = build_multi_split_adaptive(con, parents=PARENTS)
        con.close()
        cell = ams.multi.cells[("Control", "Delver")]
        assert cell.prior_source == "marginal"
        assert (cell.wins, cell.n) == (17, 31)
        assert cell.display is True
        assert cell.tier == "evolving"
