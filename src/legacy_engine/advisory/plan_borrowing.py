"""A target-excluded opponent-plan prior for fixed model comparisons.

Donor pairs keep their own clean interval eligibility. Transferring their
results to another opponent with the same plan is a modeling assumption;
these observations never become direct target-matchup observations.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from legacy_engine.analytics.amplification.models import IntervalEvidenceCorpus


@dataclass(frozen=True)
class PlanBorrowingPrior:
    mean: float
    strength: float
    donor_wins: int
    donor_n: int
    donor_events: int
    donor_opponents: int
    history_donor_n: int
    source: str
    selection_sha256: str
    corpus_id: str


@dataclass
class _Tally:
    wins: int = 0
    n: int = 0
    history_n: int = 0
    events: Counter = field(default_factory=Counter)
    opponents: Counter = field(default_factory=Counter)

    def add(self, won: bool, event: str, opponent: str, historical: bool) -> None:
        self.wins += int(won)
        self.n += 1
        self.history_n += int(historical)
        self.events[event] += 1
        self.opponents[opponent] += 1


def build_plan_borrowing_priors(
    corpus: IntervalEvidenceCorpus,
    primary_plans: Mapping[str, str],
    target_pairs: Iterable[tuple[str, str]],
    *,
    strength_cap: float = 15.0,
) -> dict[tuple[str, str], PlanBorrowingPrior]:
    """Borrow from A's plan peers of B, excluding every A-versus-B outcome.

    Missing assignments or donors return no entry: callers retain the original
    fitted prior. Each physical match enters once per directed subject, even
    when both opponents share a plan. Secondary plans are deliberately absent.
    """
    if not math.isfinite(strength_cap) or strength_cap <= 0:
        raise ValueError("strength_cap must be finite and positive")
    groups: dict[tuple[str, str], _Tally] = defaultdict(_Tally)
    pairs: dict[tuple[str, str], _Tally] = defaultdict(_Tally)
    seen: set[str] = set()
    for row in corpus.outcomes:
        if row.match_id in seen:
            raise ValueError(f"duplicate physical donor match: {row.match_id}")
        if row.event_date >= corpus.clock.data_until:
            raise ValueError(f"donor match is outside the exclusive cutoff: {row.match_id}")
        if row.subject == row.opponent:
            raise ValueError("mirror matches cannot supply opponent-plan donors")
        seen.add(row.match_id)
        for subject, opponent, won in (
            (row.subject, row.opponent, row.subject_won),
            (row.opponent, row.subject, not row.subject_won),
        ):
            plan = primary_plans.get(opponent)
            if plan is not None:
                historical = row.origin == "certified-history"
                groups[subject, plan].add(won, row.event_id, opponent, historical)
                pairs[subject, opponent].add(won, row.event_id, opponent, historical)

    plans_sha = hashlib.sha256(
        json.dumps(dict(primary_plans), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    result = {}
    for subject, opponent in sorted(set(target_pairs)):
        plan = primary_plans.get(opponent)
        group = groups.get((subject, plan))
        if subject == opponent or group is None:
            continue
        target = pairs.get((subject, opponent), _Tally())
        n, wins = group.n - target.n, group.wins - target.wins
        if n == 0:
            continue
        selection = {
            "method": "opponent-plan-prior-v1", "corpus": corpus.corpus_id,
            "primary_plans_sha256": plans_sha, "subject": subject,
            "excluded_opponent": opponent, "strength_cap": strength_cap,
        }
        selection_sha = hashlib.sha256(
            json.dumps(selection, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        result[subject, opponent] = PlanBorrowingPrior(
            mean=(wins + 1) / (n + 2), strength=min(strength_cap, float(n)),
            donor_wins=wins, donor_n=n,
            donor_events=len(group.events - target.events),
            donor_opponents=len(group.opponents - target.opponents),
            history_donor_n=group.history_n - target.history_n,
            source=f"opponent-plan borrowing: {plan}; target opponent excluded",
            selection_sha256=selection_sha, corpus_id=corpus.corpus_id,
        )
    return result
