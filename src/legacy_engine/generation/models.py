"""Generation result types.

``GeneratedDeck`` is the canonical output of all generation modes (consensus, tuning).
It carries the corpus window and sample size for the audit trail, plus legality errors
from ``ingestion.banlist.validate_deck``.

Advisory/analytics result records follow the same ``@dataclass`` pattern used in
``advisory/`` — they live in their own module, not in ``models/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GeneratedDeck:
    """A generated decklist with audit trail and legality annotation.

    ``maindeck`` sums to exactly ``main_size`` (default 60).
    ``sideboard`` sums to at most ``side_size`` (default 15).
    ``window`` is the ``(since, until)`` half-open date range the corpus was drawn from
    (either bound ``None`` = open-ended).
    ``sample_n`` is the number of archetype decks the consensus was built from.
    ``legality_errors`` mirrors ``validate_deck`` output; empty = legal.
    """

    archetype: str
    maindeck: dict[str, int]          # name → count, sums to main_size
    sideboard: dict[str, int]         # name → count, sums to ≤ side_size
    window: tuple[str | None, str | None]  # (since, until) the corpus was drawn from
    sample_n: int                      # number of archetype decks the consensus used
    legality_errors: list[str] = field(default_factory=list)  # empty = legal
