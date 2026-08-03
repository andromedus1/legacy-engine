"""Curated strategic-plan taxonomy and decisive-match aggregation.

Strategic plans describe what a deck is trying to do.  They intentionally sit
above, and remain independent from, composition-derived superarchetypes.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Collection, Mapping

from legacy_engine.analytics.match_results import MatchResults
from legacy_engine.analytics.matchup import SHRINK_STRENGTH, beta_binomial_shrink_to
from legacy_engine.config import PACKAGE_DATA_DIR


PLAN_IDS = frozenset({"disrupt-pressure", "go-off", "go-over", "go-wide", "lock-outlast"})
STRATEGIC_PLANS_PATH = PACKAGE_DATA_DIR / "strategy_plans" / "legacy.json"


@dataclass(frozen=True)
class StrategicPlan:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class ArchetypePlanAssignment:
    archetype: str
    primary: str
    secondary: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategicPlanRegistry:
    schema_version: int
    plans: tuple[StrategicPlan, ...]
    assignments: tuple[ArchetypePlanAssignment, ...]

    def assignment_for(self, archetype: str) -> ArchetypePlanAssignment | None:
        return next((item for item in self.assignments if item.archetype == archetype), None)


@dataclass(frozen=True)
class StrategicPlanCell:
    subject_id: str
    opponent_id: str
    wins: int
    losses: int
    n: int
    raw: float | None
    shrunk: float | None
    measured: bool
    structural_same_plan: bool
    observed_n: int
    mirror_n: int


@dataclass(frozen=True)
class StrategicPlanResult:
    plans: tuple[StrategicPlan, ...]
    assignments: tuple[ArchetypePlanAssignment, ...]
    cells: Mapping[tuple[str, str], StrategicPlanCell]
    decisive_matches: int
    same_plan_matches: int
    omitted_matches: int
    since: str | None
    until: str | None
    provenance: str | None


@dataclass(frozen=True)
class ArchetypeStrategicPlanCell:
    archetype: str
    opponent_id: str
    wins: int
    losses: int
    mirror_n: int
    n: int
    raw: float | None
    shrunk: float | None
    measured: bool


def _plan_token(value: object, *, field: str) -> str:
    token = str(value)
    if token not in PLAN_IDS:
        raise ValueError(f"unknown {field} plan id {token!r}; allowed: {sorted(PLAN_IDS)}")
    return token


def load_strategic_plan_registry(
    path: Path | str = STRATEGIC_PLANS_PATH,
) -> StrategicPlanRegistry:
    """Load and validate the curated registry; no file is read at import time."""
    raw = json.loads(Path(path).read_text())
    version = raw.get("schema_version")
    if version != 1:
        raise ValueError(f"unsupported strategic-plan schema_version {version!r}; expected 1")

    plans: list[StrategicPlan] = []
    seen_plans: set[str] = set()
    for item in raw.get("plans", []):
        plan_id = _plan_token(item.get("id"), field="registry")
        if plan_id in seen_plans:
            raise ValueError(f"duplicate strategic plan id {plan_id!r}")
        label = str(item.get("label", "")).strip()
        description = str(item.get("description", "")).strip()
        if not label or not description:
            raise ValueError(f"strategic plan {plan_id!r} requires nonblank label and description")
        seen_plans.add(plan_id)
        plans.append(StrategicPlan(plan_id, label, description))
    if seen_plans != PLAN_IDS:
        raise ValueError(f"registry plans must equal allowed ids {sorted(PLAN_IDS)}")

    assignments: list[ArchetypePlanAssignment] = []
    seen_archetypes: set[str] = set()
    for item in raw.get("assignments", []):
        archetype = str(item.get("archetype", "")).strip()
        if not archetype:
            raise ValueError("strategic-plan assignment requires a nonblank archetype")
        if archetype in seen_archetypes:
            raise ValueError(f"duplicate strategic-plan assignment for {archetype!r}")
        primary = _plan_token(item.get("primary"), field="primary")
        secondary = tuple(_plan_token(value, field="secondary") for value in item.get("secondary", []))
        if primary in secondary:
            raise ValueError(f"secondary plans for {archetype!r} repeat primary {primary!r}")
        if len(set(secondary)) != len(secondary):
            raise ValueError(f"repeated secondary plan for {archetype!r}: {secondary!r}")
        seen_archetypes.add(archetype)
        assignments.append(ArchetypePlanAssignment(archetype, primary, secondary))
    return StrategicPlanRegistry(version, tuple(plans), tuple(assignments))


def validate_current_plan_coverage(
    registry: StrategicPlanRegistry,
    current_archetypes: Collection[str],
) -> None:
    assigned = {item.archetype for item in registry.assignments}
    missing = sorted(set(current_archetypes) - assigned)
    if missing:
        raise ValueError("unassigned current-field archetypes: " + ", ".join(missing))


def aggregate_strategic_plan_results(
    match_results: MatchResults,
    registry: StrategicPlanRegistry,
    *,
    current_archetypes: Collection[str],
    ground_n: int,
    since: str | None,
    until: str | None = None,
    provenance: str | None = None,
) -> StrategicPlanResult:
    """Map archetype tallies to primary plans without averaging rendered rates."""
    if ground_n < 1:
        raise ValueError("ground_n must be >= 1")
    validate_current_plan_coverage(registry, current_archetypes)
    primary = {item.archetype: item.primary for item in registry.assignments}
    totals: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    same_observed: dict[str, int] = defaultdict(int)
    same_mirrors: dict[str, int] = defaultdict(int)
    omitted = 0
    included_external = 0

    # Matchups are directed.  Canonical lexical pairs count each real match once,
    # while both directions are retained in the plan cells below.
    for (a, b), tally in match_results.matchups.items():
        if a >= b:
            continue
        pa, pb = primary.get(a), primary.get(b)
        if pa is None or pb is None:
            omitted += tally.n
            continue
        if pa == pb:
            same_observed[pa] += tally.n
            continue
        included_external += tally.n
        totals[(pa, pb)][0] += tally.wins
        totals[(pa, pb)][1] += tally.losses
        totals[(pb, pa)][0] += tally.losses
        totals[(pb, pa)][1] += tally.wins

    for archetype, n in match_results.mirror_n.items():
        plan = primary.get(archetype)
        if plan is None:
            omitted += n
        else:
            same_mirrors[plan] += n

    cells: dict[tuple[str, str], StrategicPlanCell] = {}
    for subject in registry.plans:
        for opponent in registry.plans:
            key = (subject.id, opponent.id)
            if subject.id == opponent.id:
                cells[key] = StrategicPlanCell(
                    subject.id, opponent.id, 0, 0, 0, 0.5, 0.5, False, True,
                    same_observed[subject.id], same_mirrors[subject.id],
                )
                continue
            wins, losses = totals[key]
            n = wins + losses
            cells[key] = StrategicPlanCell(
                subject.id,
                opponent.id,
                wins,
                losses,
                n,
                wins / n if n else None,
                beta_binomial_shrink_to(
                    wins, n, prior_mean=0.5, strength=SHRINK_STRENGTH
                ) if n else None,
                n >= ground_n,
                False,
                n,
                0,
            )

    for a in registry.plans:
        for b in registry.plans:
            if a.id >= b.id:
                continue
            ab, ba = cells[(a.id, b.id)], cells[(b.id, a.id)]
            if ab.n != ba.n or ab.wins != ba.losses or ab.losses != ba.wins:
                raise AssertionError(f"non-complementary strategic-plan cells: {a.id}, {b.id}")
            if ab.shrunk is not None and abs((ab.shrunk + ba.shrunk) - 1.0) > 1e-12:
                raise AssertionError(f"non-complementary strategic-plan rates: {a.id}, {b.id}")

    same_total = sum(same_observed.values()) + sum(same_mirrors.values())
    return StrategicPlanResult(
        registry.plans,
        registry.assignments,
        MappingProxyType(cells),
        included_external + same_total,
        same_total,
        omitted,
        since,
        until,
        provenance if provenance is not None else match_results.provenance,
    )


def aggregate_archetype_vs_plan_results(
    match_results: MatchResults,
    registry: StrategicPlanRegistry,
    *,
    current_archetypes: Collection[str],
    ground_n: int,
) -> Mapping[tuple[str, str], ArchetypeStrategicPlanCell]:
    """Aggregate each current archetype directly against the five opponent plans.

    Archetype mirrors are real same-plan context. They contribute one physical match
    at structural 50% (half a win) without pretending to be an observed directional win.
    """
    if ground_n < 1:
        raise ValueError("ground_n must be >= 1")
    validate_current_plan_coverage(registry, current_archetypes)
    primary = {item.archetype: item.primary for item in registry.assignments}
    tallies: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for (subject, opponent), tally in match_results.matchups.items():
        if subject not in current_archetypes:
            continue
        opponent_plan = primary.get(opponent)
        if opponent_plan is not None:
            tallies[(subject, opponent_plan)][0] += tally.wins
            tallies[(subject, opponent_plan)][1] += tally.losses

    out: dict[tuple[str, str], ArchetypeStrategicPlanCell] = {}
    for archetype in current_archetypes:
        assignment = primary[archetype]
        for plan in registry.plans:
            wins, losses = tallies[(archetype, plan.id)]
            mirrors = match_results.mirror_n.get(archetype, 0) if plan.id == assignment else 0
            n = wins + losses
            out[(archetype, plan.id)] = ArchetypeStrategicPlanCell(
                archetype=archetype,
                opponent_id=plan.id,
                wins=wins,
                losses=losses,
                mirror_n=mirrors,
                n=n,
                raw=wins / n if n else None,
                shrunk=beta_binomial_shrink_to(
                    wins, n, prior_mean=0.5, strength=SHRINK_STRENGTH
                ) if n else None,
                measured=n >= ground_n,
            )
    return MappingProxyType(out)
