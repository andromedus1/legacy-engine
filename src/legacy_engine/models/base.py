"""Shared Pydantic base for all legacy-engine models.

The project standardizes on Pydantic v2 for every shared model (a deliberate
divergence from edh-engine's dataclass/Pydantic mix) so types are uniform and
strict at module boundaries.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LegacyEngineModel(BaseModel):
    """Base model for the project.

    ``extra="ignore"`` because external JSON (notably Scryfall card objects)
    carries many fields we don't model; we keep what we declare and drop the
    rest rather than failing. ``populate_by_name`` lets a field be set by either
    its Python name or an alias (useful for PascalCase external schemas).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)
