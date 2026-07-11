"""Tests for archetype/discovered.py — staging registry loader/staging/promotion (Unit 5).

All tests are file-backed under tmp_path (no DB). Covers:
- load_discovered: absent file -> empty registry; malformed file -> fail-fast ValueError
- save/load round-trip
- record_from_split: positive-delta-only signature cards, capped at TOP_SIGNATURE_CARDS
- stage_split: upsert by parent (replace in place / append), purity
- promote_split: happy-path round-trip (rule appended, complement default set, status flipped,
  result loadable by load_variant_registry and resolvable by resolve_variant)
- promote_split fail-fast paths: unknown parent / unknown camp / already promoted /
  already in curated registry / no signature cards
"""

from __future__ import annotations

import json

import pytest

from legacy_engine.analytics.discovery import Camp, DiscoveredSplit
from legacy_engine.archetype.discovered import (
    TOP_SIGNATURE_CARDS,
    load_discovered,
    promote_split,
    record_from_split,
    save_discovered,
    stage_split,
)
from legacy_engine.archetype.variants import load_variant_registry, resolve_variant
from legacy_engine.models.variant import (
    DiscoveredCamp,
    DiscoveredRegistry,
    DiscoveredSplitRecord,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _camp_record(name: str = "Murktide Regent", n: int = 40, **kwargs) -> DiscoveredCamp:
    defaults: dict = {
        "name": name,
        "signature_cards": ["Murktide Regent", "Tamiyo, Inquisitive Student"],
        "n": n,
        "tier": "evolving",
    }
    defaults.update(kwargs)
    return DiscoveredCamp(**defaults)


def _split_record(parent: str = "Doomsday", **kwargs) -> DiscoveredSplitRecord:
    defaults: dict = {
        "parent": parent,
        "generated_from": "test",
        "params": {"seed": 0},
        "camps": [
            _camp_record(),
            _camp_record(name="non-Murktide Regent", signature_cards=["Personal Tutor"]),
        ],
        "stability": 0.97,
    }
    defaults.update(kwargs)
    return DiscoveredSplitRecord(**defaults)


def _curated_registry_file(tmp_path, variants: list[dict] | None = None) -> str:
    """Write a minimal curated legacy.json-shaped registry under tmp_path."""
    data = {
        "version": "test",
        "variants": variants or [],
        "defaults": {},
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(data, indent=2))
    return str(path)


# ---------------------------------------------------------------------------
# load_discovered / save_discovered
# ---------------------------------------------------------------------------

class TestLoadDiscovered:
    def test_absent_file_returns_empty_registry(self, tmp_path):
        reg = load_discovered(tmp_path / "nope.json")
        assert reg.splits == []

    def test_malformed_file_fails_fast_citing_path(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text('{"version": 1, "splits": "not-a-list"}')
        with pytest.raises(ValueError, match=str(p)):
            load_discovered(p)

    def test_save_load_round_trip(self, tmp_path):
        reg = DiscoveredRegistry(version="1", splits=[_split_record()])
        p = tmp_path / "sub" / "discovered.json"   # parent dir created at write time
        save_discovered(reg, p)
        loaded = load_discovered(p)
        assert loaded == reg


# ---------------------------------------------------------------------------
# record_from_split
# ---------------------------------------------------------------------------

class TestRecordFromSplit:
    def _split(self) -> DiscoveredSplit:
        camp_a = Camp(
            name="Murktide Regent",
            member_keys=[("t1", 0)],
            signature_cards=[
                ("Murktide Regent", 1.0),
                ("Wasteland", 0.9),
                ("Personal Tutor", -1.7),       # negative -> excluded
                ("Card D", 0.5),
                ("Card E", 0.4),
                ("Card F", 0.3),
                ("Card G", 0.2),                # 6th positive -> cut by the cap
            ],
            n=40,
            tier="evolving",
        )
        camp_b = Camp(
            name="non-Murktide Regent",
            member_keys=[("t1", 1)],
            signature_cards=[("Personal Tutor", 1.7), ("Murktide Regent", -1.0)],
            n=120,
            tier="established",
        )
        return DiscoveredSplit(
            parent="Doomsday", camps=[camp_a, camp_b], n_noise=3,
            stability=0.95, silhouette=0.8, passed=True, reasons=["ok"],
        )

    def test_positive_delta_cards_only_capped(self):
        record = record_from_split(self._split(), generated_from="t", params={})
        camp = record.camps[0]
        assert "Personal Tutor" not in camp.signature_cards
        assert len(camp.signature_cards) == TOP_SIGNATURE_CARDS
        assert camp.signature_cards[0] == "Murktide Regent"

    def test_carries_parent_stability_and_camp_stats(self):
        record = record_from_split(self._split(), generated_from="run-x", params={"seed": 7})
        assert record.parent == "Doomsday"
        assert record.stability == 0.95
        assert record.status == "candidate"
        assert record.generated_from == "run-x"
        assert record.params == {"seed": 7}
        assert [c.n for c in record.camps] == [40, 120]
        assert [c.tier for c in record.camps] == ["evolving", "established"]


# ---------------------------------------------------------------------------
# stage_split
# ---------------------------------------------------------------------------

class TestStageSplit:
    def test_append_new_parent(self):
        reg = DiscoveredRegistry(version="1", splits=[])
        out = stage_split(reg, _split_record())
        assert len(out.splits) == 1
        assert reg.splits == []   # purity: input untouched

    def test_upsert_replaces_same_parent_in_place(self):
        reg = DiscoveredRegistry(
            version="1",
            splits=[_split_record(parent="Doomsday"), _split_record(parent="Lands")],
        )
        newer = _split_record(parent="Doomsday", stability=0.99)
        out = stage_split(reg, newer)
        assert [s.parent for s in out.splits] == ["Doomsday", "Lands"]
        assert out.splits[0].stability == 0.99

    def test_different_parents_coexist(self):
        reg = DiscoveredRegistry(version="1", splits=[_split_record(parent="Doomsday")])
        out = stage_split(reg, _split_record(parent="Lands"))
        assert [s.parent for s in out.splits] == ["Doomsday", "Lands"]


# ---------------------------------------------------------------------------
# promote_split
# ---------------------------------------------------------------------------

class TestPromoteSplit:
    def _staged(self, tmp_path) -> tuple[str, str]:
        """Stage a 2-camp Doomsday split + a minimal curated registry; return both paths."""
        disc_path = str(tmp_path / "discovered.json")
        save_discovered(DiscoveredRegistry(version="1", splits=[_split_record()]), disc_path)
        reg_path = _curated_registry_file(tmp_path)
        return disc_path, reg_path

    def test_promotion_appends_rule_and_default(self, tmp_path):
        disc_path, reg_path = self._staged(tmp_path)
        rule = promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)

        assert rule.parent == "Doomsday"
        assert rule.name == "Murktide Regent"
        assert rule.conditions[0].type == "InMainboard"
        assert rule.conditions[0].cards == ["Murktide Regent"]

        registry = load_variant_registry(reg_path)
        assert [v.name for v in registry.for_parent("Doomsday")] == ["Murktide Regent"]
        # 2-camp split: the complement camp becomes the parent default.
        assert registry.defaults["Doomsday"] == "non-Murktide Regent"

    def test_promoted_registry_resolves_decks(self, tmp_path):
        disc_path, reg_path = self._staged(tmp_path)
        promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)
        registry = load_variant_registry(reg_path)

        with_sig = resolve_variant("Doomsday", {"Murktide Regent": 2}, {}, registry)
        without_sig = resolve_variant("Doomsday", {"Dark Ritual": 4}, {}, registry)
        assert with_sig == "Murktide Regent"
        assert without_sig == "non-Murktide Regent"

    def test_promotion_flips_staged_status(self, tmp_path):
        disc_path, reg_path = self._staged(tmp_path)
        promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)
        disc = load_discovered(disc_path)
        assert disc.splits[0].status == "promoted"

    def test_unknown_parent_fails_fast(self, tmp_path):
        disc_path, reg_path = self._staged(tmp_path)
        with pytest.raises(ValueError, match="no staged split for parent 'Nope'"):
            promote_split("Nope", "Murktide Regent", disc_path, reg_path)

    def test_unknown_camp_fails_fast_listing_available(self, tmp_path):
        disc_path, reg_path = self._staged(tmp_path)
        with pytest.raises(ValueError, match="no camp 'Bogus'"):
            promote_split("Doomsday", "Bogus", disc_path, reg_path)

    def test_already_promoted_fails_fast(self, tmp_path):
        disc_path, reg_path = self._staged(tmp_path)
        promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)
        with pytest.raises(ValueError, match="already promoted"):
            promote_split("Doomsday", "non-Murktide Regent", disc_path, reg_path)

    def test_rule_already_in_curated_registry_fails_fast(self, tmp_path):
        disc_path = str(tmp_path / "discovered.json")
        save_discovered(DiscoveredRegistry(version="1", splits=[_split_record()]), disc_path)
        reg_path = _curated_registry_file(tmp_path, variants=[
            {
                "parent": "Doomsday",
                "name": "Murktide Regent",
                "conditions": [{"Type": "InMainboard", "Cards": ["Murktide Regent"]}],
            }
        ])
        with pytest.raises(ValueError, match="already exists"):
            promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)

    def test_camp_without_signature_cards_fails_fast(self, tmp_path):
        disc_path = str(tmp_path / "discovered.json")
        split = _split_record(camps=[
            _camp_record(signature_cards=[]),
            _camp_record(name="other"),
        ])
        save_discovered(DiscoveredRegistry(version="1", splits=[split]), disc_path)
        reg_path = _curated_registry_file(tmp_path)
        with pytest.raises(ValueError, match="no over-represented signature card"):
            promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)

    def test_promotion_preserves_existing_registry_entries(self, tmp_path):
        disc_path = str(tmp_path / "discovered.json")
        save_discovered(DiscoveredRegistry(version="1", splits=[_split_record()]), disc_path)
        reg_path = _curated_registry_file(tmp_path, variants=[
            {
                "parent": "Dimir Tempo",
                "name": "Bauble",
                "conditions": [{"Type": "InMainboard", "Cards": ["Mishra's Bauble"]}],
            }
        ])
        promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)
        registry = load_variant_registry(reg_path)
        assert [v.name for v in registry.for_parent("Dimir Tempo")] == ["Bauble"]
        assert [v.name for v in registry.for_parent("Doomsday")] == ["Murktide Regent"]
