"""ILP determinism — equal-objective boards must not vary run-to-run.

Drains idea-ilp-tiebreak-nondeterminism. Root cause (reproduced on the real corpus,
2026-07-04): `_build_ilp_problem` iterates `CoverageModel` dicts whose insertion order
upstream is run-to-run unstable (DuckDB's multithreaded row emission; str-hash randomization
across processes). PuLP name-sorts VARIABLES when writing the model file, but CONSTRAINT rows
keep insertion order — and CBC's tie resolution is sensitive to row order, so equal-objective
boards flipped between runs on identical inputs (Snuff Out vs Sheoldred's Edict on the same
Dimir Tempo model; a model-content dump under both runs was byte-identical, isolating order as
the only difference). The fix sorts every construction loop.

The regression guard asserts the construction invariant directly: the same model CONTENTS
supplied in different dict insertion orders must yield an identical formulation (constraint
order included). This fails against the pre-fix construction and is deterministic —
solve-level tests can't reliably trip the bug because CBC often lands on the same tie
resolution for small/symmetric models.
"""

from __future__ import annotations

import random

from legacy_engine.advisory.sideboard import (
    CoverageModel,
    HoserCard,
    _build_ilp_problem,
    _ilp_solve,
)


def _hoser(name: str, attacks: frozenset[str], max_copies: int = 4) -> HoserCard:
    return HoserCard(
        name=name,
        attacks=attacks,
        colors=frozenset(),
        max_copies=max_copies,
        swing=0.20,
    )


def _model_from_orders(
    weight_items: list[tuple[str, float]],
    cover_items: list[tuple[str, frozenset[str]]],
) -> CoverageModel:
    """CoverageModel whose dict insertion order follows the given item lists."""
    return CoverageModel(
        element_weight=dict(weight_items),
        candidate_covers=dict(cover_items),
        candidate_meta={name: _hoser(name, elems) for name, elems in cover_items},
        warnings=(),
    )


# Asymmetric, multi-coverage contents (distinct weights, overlapping covers) so the
# formulation has heterogeneous rows — the shape where row order actually matters to CBC.
_WEIGHTS = [
    ("delver", 0.31),
    ("lands", 0.22),
    ("reanimator", 0.17),
    ("storm", 0.13),
    ("_hate:graveyard", 0.09),
    ("eldrazi", 0.08),
]
_COVERS = [
    ("Surgical Extraction", frozenset({"reanimator", "storm", "_hate:graveyard"})),
    ("Leyline of the Void", frozenset({"reanimator", "_hate:graveyard"})),
    ("Blast Zone", frozenset({"delver", "eldrazi"})),
    ("Toxic Deluge", frozenset({"delver", "eldrazi", "lands"})),
    ("Flusterstorm", frozenset({"storm", "delver"})),
    ("Blood Moon", frozenset({"lands", "eldrazi"})),
]
_BONUS = [("Toxic Deluge", 0.013), ("Flusterstorm", 0.021), ("Blood Moon", 0.008)]


def _orderings(items: list) -> list[list]:
    """Identity, reversal, and three seeded shuffles of the item list."""
    orders = [list(items), list(reversed(items))]
    for seed in (1, 2, 3):
        shuffled = list(items)
        random.Random(seed).shuffle(shuffled)
        orders.append(shuffled)
    return orders


def _formulation_text(model: CoverageModel, bonus: dict[str, float]) -> str:
    """Full formulation (objective + constraints, in insertion order) as text."""
    prob, _x_vars = _build_ilp_problem(
        model, budget=5, redundancy_strength=0.5, tau=0.01, option_value_bonus=bonus
    )
    return str(prob)


class TestIlpConstructionOrderInvariance:
    def test_formulation_identical_across_input_insertion_orders(self):
        texts = []
        for w_order, c_order, b_order in zip(
            _orderings(_WEIGHTS), _orderings(_COVERS), _orderings(_BONUS), strict=True
        ):
            model = _model_from_orders(w_order, c_order)
            texts.append(_formulation_text(model, dict(b_order)))
        assert all(t == texts[0] for t in texts)
        # Sanity: the formulation is real (has the budget row and some y-level terms).
        assert "budget" in texts[0]
        assert "y_" in texts[0]

    def test_solutions_identical_across_input_insertion_orders(self):
        results = []
        for w_order, c_order, b_order in zip(
            _orderings(_WEIGHTS), _orderings(_COVERS), _orderings(_BONUS), strict=True
        ):
            model = _model_from_orders(w_order, c_order)
            results.append(
                _ilp_solve(
                    model,
                    budget=5,
                    redundancy_strength=0.5,
                    tau=0.01,
                    option_value_bonus=dict(b_order),
                )
            )
        assert all(r == results[0] for r in results), results
        assert sum(results[0].values()) > 0


class TestIlpStability:
    def test_repeated_solves_of_same_model_are_identical(self):
        model = _model_from_orders(_WEIGHTS, _COVERS)
        first = _ilp_solve(model, budget=3)
        for _ in range(4):
            assert _ilp_solve(model, budget=3) == first

    def test_sorted_construction_does_not_change_objective_quality(self):
        # Non-tied model: the unique optimum must be found regardless of insertion order.
        for weights, covers in (
            (
                [("big", 10.0), ("small", 1.0)],
                [("Answer Big", frozenset({"big"})), ("Answer Small", frozenset({"small"}))],
            ),
            (
                [("small", 1.0), ("big", 10.0)],
                [("Answer Small", frozenset({"small"})), ("Answer Big", frozenset({"big"}))],
            ),
        ):
            model = _model_from_orders(weights, covers)
            assert _ilp_solve(model, budget=1) == {"Answer Big": 1}
