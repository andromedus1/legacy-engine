"""Confidence metadata — the project-wide provenance/trust signal.

Every derived stat the platform emits carries a confidence tier so consumers
know how much to trust it. Adapted from edh-engine's confidence pattern.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

ConfidenceLevel = Literal["established", "evolving", "speculative"]
Production = Literal["hand-written", "template-generated", "template+llm-enriched"]
Source = Literal["user", "llm-synthesis", "heuristic"]


class ConfidenceMetadata(BaseModel):
    """How confident we are in a piece of derived knowledge, and where it came from.

    - ``level``: trust tier (decays toward speculative if not refreshed).
    - ``production``: how the artifact was produced.
    - ``source``: origin of the underlying signal.
    - ``updated``: when it was last refreshed (None = unknown).
    """

    level: ConfidenceLevel = "speculative"
    production: Production = "template-generated"
    source: Source = "heuristic"
    updated: date | None = None


def tier_for_sample(
    n: int,
    *,
    evolving_min: int = 30,
    established_min: int = 100,
) -> ConfidenceLevel:
    """Map a sample size to a confidence tier.

    Thresholds follow the advisory-methods brief: a Wilson 95% half-width at
    p=0.5 is ~±0.17 at n=30 and ~±0.096 at n=100, so n<30 is too noisy to show
    (speculative), 30–99 is provisional (evolving), and n>=100 is established.
    """
    if n >= established_min:
        return "established"
    if n >= evolving_min:
        return "evolving"
    return "speculative"
