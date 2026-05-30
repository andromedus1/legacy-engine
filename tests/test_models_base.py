"""LegacyEngineModel base behavior — ignores unknown keys, enforces declared fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from legacy_engine.models import LegacyEngineModel


class _Sample(LegacyEngineModel):
    name: str
    count: int = 0


def test_ignores_extra_keys():
    # External JSON (e.g. Scryfall) carries fields we don't model; they're dropped.
    obj = _Sample(name="Brainstorm", count=4, oracle_text="Draw three cards", foo="bar")
    assert obj.name == "Brainstorm"
    assert obj.count == 4
    assert not hasattr(obj, "oracle_text")


def test_required_field_enforced():
    with pytest.raises(ValidationError):
        _Sample(count=1)


def test_defaults_apply():
    assert _Sample(name="Ponder").count == 0
