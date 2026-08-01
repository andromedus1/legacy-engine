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
    apply_split,
    assign_incremental,
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

    def test_carries_gate_c_temporal_fields(self):
        """epic-stable-era-windows-discovery-gate Unit 2: median_date/pct_current per camp and
        the split-level temporal_mixing/temporal_note ride the record additively."""
        camp_a = Camp(
            name="Murktide Regent", member_keys=[("t1", 0)], signature_cards=[("X", 1.0)],
            n=40, tier="evolving", median_date="2025-06-01", pct_current=0.1,
        )
        camp_b = Camp(
            name="non-Murktide Regent", member_keys=[("t1", 1)], signature_cards=[("X", -1.0)],
            n=120, tier="established", median_date="2026-05-01", pct_current=0.9,
        )
        split = DiscoveredSplit(
            parent="Doomsday", camps=[camp_a, camp_b], n_noise=3,
            stability=0.95, silhouette=0.8, passed=True, reasons=["ok"],
            temporal_mixing=True, temporal_note="camps may be list generations",
        )
        record = record_from_split(split, generated_from="t", params={})
        assert record.temporal_mixing is True
        assert record.temporal_note == "camps may be list generations"
        assert [c.median_date for c in record.camps] == ["2025-06-01", "2026-05-01"]
        assert [c.pct_current for c in record.camps] == [0.1, 0.9]

    def test_gate_c_fields_default_absent_on_untouched_split(self):
        """The pre-epic call shape (no Gate C fields on the DiscoveredSplit/Camp) still
        produces a valid record — additive-defaults contract."""
        record = record_from_split(self._split(), generated_from="t", params={})
        assert record.temporal_mixing is False
        assert record.temporal_note is None
        assert all(c.median_date is None for c in record.camps)
        assert all(c.pct_current is None for c in record.camps)

    def test_carries_centroid_and_flex_cards(self):
        """The frozen representation incremental assignment reads rides the record additively."""
        camp_a = Camp(
            name="A", member_keys=[("t1", 0)], signature_cards=[("X", 1.0)],
            n=40, tier="evolving", centroid=[1.0, 0.0],
        )
        camp_b = Camp(
            name="B", member_keys=[("t1", 1)], signature_cards=[("X", -1.0)],
            n=120, tier="established", centroid=[0.0, 1.0],
        )
        split = DiscoveredSplit(
            parent="Doomsday", camps=[camp_a, camp_b], n_noise=0,
            stability=0.95, silhouette=0.8, passed=True, reasons=["ok"],
            flex_cards=["Card A1", "Card B1"],
        )
        record = record_from_split(split, generated_from="t", params={})
        assert record.flex_cards == ["Card A1", "Card B1"]
        assert [c.centroid for c in record.camps] == [[1.0, 0.0], [0.0, 1.0]]

    def test_centroid_and_flex_cards_default_absent_on_untouched_split(self):
        record = record_from_split(self._split(), generated_from="t", params={})
        assert record.flex_cards == []
        assert all(c.centroid is None for c in record.camps)

    def test_centroid_floats_survive_the_json_round_trip(self, tmp_path):
        camp = Camp(
            name="A", member_keys=[("t1", 0)], signature_cards=[("X", 1.0)],
            n=40, tier="evolving", centroid=[0.7071067811865476, 0.7071067811865476],
        )
        split = DiscoveredSplit(
            parent="Doomsday", camps=[camp, camp], n_noise=0, stability=0.95,
            silhouette=None, passed=True, reasons=[], flex_cards=["B", "A"],
        )
        record = record_from_split(split, generated_from="t", params={})
        path = tmp_path / "discovered.json"
        save_discovered(DiscoveredRegistry(version="1", splits=[record]), path)

        loaded = load_discovered(path).splits[0]
        assert loaded.flex_cards == ["B", "A"]   # vocabulary ORDER is load-bearing, not a set
        assert loaded.camps[0].centroid == pytest.approx([0.7071067811865476] * 2)

    def test_old_shape_json_without_the_new_keys_still_loads(self, tmp_path):
        """A staged record written before this feature (no centroid/flex_cards keys at all)
        loads unchanged — the honest-degrade precondition assign_incremental keys off."""
        path = tmp_path / "discovered.json"
        path.write_text(json.dumps({
            "version": "1",
            "splits": [{
                "parent": "Doomsday",
                "generated_from": "discover run @ 2026-01-01 (pre-feature)",
                "params": {},
                "camps": [
                    {"name": "A", "signature_cards": ["X"], "n": 40, "tier": "evolving",
                     "member_keys": [["t1", 0]]},
                    {"name": "B", "signature_cards": ["Y"], "n": 35, "tier": "evolving",
                     "member_keys": [["t1", 1]]},
                ],
                "stability": 0.95,
                "status": "candidate",
            }],
        }, indent=2))

        loaded = load_discovered(path).splits[0]
        assert loaded.flex_cards == []
        assert all(c.centroid is None for c in loaded.camps)


# ---------------------------------------------------------------------------
# stage_split
# ---------------------------------------------------------------------------

class TestStageSplit:
    def test_append_new_parent(self):
        reg = DiscoveredRegistry(version="1", splits=[])
        out, replaced = stage_split(reg, _split_record())
        assert len(out.splits) == 1
        assert reg.splits == []   # purity: input untouched
        assert replaced is None   # fresh append, nothing replaced

    def test_upsert_replaces_same_parent_in_place(self):
        reg = DiscoveredRegistry(
            version="1",
            splits=[_split_record(parent="Doomsday"), _split_record(parent="Lands")],
        )
        newer = _split_record(parent="Doomsday", stability=0.99)
        out, replaced = stage_split(reg, newer)
        assert [s.parent for s in out.splits] == ["Doomsday", "Lands"]
        assert out.splits[0].stability == 0.99
        assert replaced is not None
        assert replaced.parent == "Doomsday"
        assert replaced.stability == 0.97   # the prior record, not the new one

    def test_different_parents_coexist(self):
        reg = DiscoveredRegistry(version="1", splits=[_split_record(parent="Doomsday")])
        out, replaced = stage_split(reg, _split_record(parent="Lands"))
        assert [s.parent for s in out.splits] == ["Doomsday", "Lands"]
        assert replaced is None


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


# ---------------------------------------------------------------------------
# apply_split
# ---------------------------------------------------------------------------

def _con_with_doomsday_decks():
    """In-memory DB: two 'Doomsday' decks (one w/ Murktide Regent, one without) + one
    'Control' deck — the Control deck is the untouched-by-apply control."""
    from legacy_engine.ingestion import store

    con = store.connect(":memory:")
    store.init_schema(con)
    con.execute(
        "INSERT INTO tournaments VALUES ('t1', 'T', '2026-01-01', NULL, 'Legacy', 'src', 'online')"
    )
    decks = [
        ("t1", 0, "p0", "1st", "Doomsday", None),
        ("t1", 1, "p1", "2nd", "Doomsday", None),
        ("t1", 2, "p2", "3rd", "Control", None),
    ]
    cards = [
        ("t1", 0, "main", "Murktide Regent", 3),
        ("t1", 0, "main", "Brainstorm", 4),
        ("t1", 1, "main", "Dark Ritual", 4),
        ("t1", 2, "main", "Swords to Plowshares", 4),
    ]
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", decks)
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", cards)
    return con


class TestApplySplit:
    def _staged(self, tmp_path, split: DiscoveredSplitRecord | None = None) -> str:
        disc_path = str(tmp_path / "discovered.json")
        save_discovered(
            DiscoveredRegistry(version="1", splits=[split or _split_record()]), disc_path
        )
        return disc_path

    def test_applies_camp_labels_without_promoting_or_touching_curated_registry(self, tmp_path):
        con = _con_with_doomsday_decks()
        disc_path = self._staged(tmp_path)

        n = apply_split(con, "Doomsday", discovered_path=disc_path)
        assert n == 2   # both Doomsday decks resolve: positive rule + default complement

        rows = dict(
            con.execute("SELECT deck_idx, variant FROM decks WHERE tournament_id = 't1'").fetchall()
        )
        assert rows[0] == "Murktide Regent"
        assert rows[1] == "non-Murktide Regent"
        assert rows[2] is None   # Control deck untouched — different archetype

        # Not a promotion: staged record status is unchanged.
        disc = load_discovered(disc_path)
        assert disc.splits[0].status == "candidate"
        con.close()

    def test_membership_path_labels_exact_members_and_leaves_noise_null(self, tmp_path):
        """Regression (found dogfooding the real Doomsday 3-camp split): camps whose
        signature staples OVERLAP (a deck runs both camps' top cards) tripped
        resolve_variant's ambiguity fail-fast under the transient-rules path. With
        member_keys persisted, apply labels by exact cluster membership instead —
        overlap is irrelevant and noise decks stay NULL ([unlabeled] downstream)."""
        con = _con_with_doomsday_decks()
        split = _split_record(camps=[
            # overlapping signatures: both camps' top cards appear in deck 0
            _camp_record(
                name="Tamiyo, Inquisitive Student",
                signature_cards=["Tamiyo, Inquisitive Student"],
                member_keys=[("t1", 0)],
            ),
            _camp_record(
                name="Personal Tutor",
                signature_cards=["Personal Tutor"],
                member_keys=[("t1", 1)],
            ),
            _camp_record(
                name="Flow State",
                signature_cards=["Flow State"],
                member_keys=[],   # a camp whose members were all elsewhere (edge)
            ),
        ])
        # make deck 0 run BOTH top cards — the exact ambiguity trigger
        con.execute(
            "INSERT INTO deck_cards VALUES ('t1', 0, 'main', 'Tamiyo, Inquisitive Student', 4)"
        )
        con.execute(
            "INSERT INTO deck_cards VALUES ('t1', 0, 'main', 'Personal Tutor', 1)"
        )
        disc_path = self._staged(tmp_path, split=split)

        n = apply_split(con, "Doomsday", discovered_path=disc_path)
        assert n == 2

        rows = dict(
            con.execute("SELECT deck_idx, variant FROM decks WHERE tournament_id = 't1'").fetchall()
        )
        assert rows[0] == "Tamiyo, Inquisitive Student"   # membership, not rule matching
        assert rows[1] == "Personal Tutor"
        assert rows[2] is None                            # Control untouched
        con.close()

    def test_membership_path_archetype_guard_skips_relabeled_decks(self, tmp_path):
        """A stale staged record whose member deck was since relabeled off the parent
        must not touch that deck (the UPDATE carries an archetype guard)."""
        con = _con_with_doomsday_decks()
        split = _split_record(camps=[
            _camp_record(name="A", signature_cards=["Murktide Regent"], member_keys=[("t1", 0)]),
            _camp_record(name="B", signature_cards=["Dark Ritual"], member_keys=[("t1", 1)]),
        ])
        con.execute("UPDATE decks SET archetype='Reanimator' WHERE tournament_id='t1' AND deck_idx=1")
        disc_path = self._staged(tmp_path, split=split)

        n = apply_split(con, "Doomsday", discovered_path=disc_path)
        assert n == 1   # only deck 0 still belongs to the parent
        rows = dict(
            con.execute("SELECT deck_idx, variant FROM decks WHERE tournament_id = 't1'").fetchall()
        )
        assert rows[0] == "A"
        assert rows[1] is None
        con.close()

    def test_no_staged_split_fails_fast(self, tmp_path):
        con = _con_with_doomsday_decks()
        disc_path = str(tmp_path / "empty.json")
        with pytest.raises(ValueError, match="no staged candidate split for parent 'Doomsday'"):
            apply_split(con, "Doomsday", discovered_path=disc_path)
        con.close()

    def test_no_signature_card_anywhere_fails_fast(self, tmp_path):
        con = _con_with_doomsday_decks()
        split = _split_record(camps=[
            _camp_record(signature_cards=[]),
            _camp_record(name="other", signature_cards=[]),
        ])
        disc_path = self._staged(tmp_path, split=split)
        with pytest.raises(ValueError, match="nothing to apply"):
            apply_split(con, "Doomsday", discovered_path=disc_path)
        con.close()

    def test_promote_still_works_after_apply(self, tmp_path):
        """apply_split doesn't flip status, so promote_split can still run afterward."""
        con = _con_with_doomsday_decks()
        disc_path = self._staged(tmp_path)
        apply_split(con, "Doomsday", discovered_path=disc_path)
        con.close()

        reg_path = _curated_registry_file(tmp_path)
        rule = promote_split("Doomsday", "Murktide Regent", disc_path, reg_path)
        assert rule.name == "Murktide Regent"

        disc = load_discovered(disc_path)
        assert disc.splits[0].status == "promoted"


# ---------------------------------------------------------------------------
# assign_incremental
# ---------------------------------------------------------------------------

def _con_with_clustered_doomsday_pool():
    """In-memory DB: a clean two-camp 'Doomsday' pool (35 + 35), the shape discovery clusters.

    Camp A runs Card A1/A2, camp B the mirror; ±1 copy of deterministic wobble keeps rows
    non-identical without touching separation (mirrors tests/analytics/test_discovery.py).
    """
    from legacy_engine.ingestion import store

    con = store.connect(":memory:")
    store.init_schema(con)
    con.execute(
        "INSERT INTO tournaments VALUES ('t1', 'T', '2026-01-01', NULL, 'Legacy', 'src', 'online')"
    )
    deck_rows = []
    card_rows = []
    for idx in range(70):
        pair = ("Card A1", "Card A2") if idx < 35 else ("Card B1", "Card B2")
        wobble = idx % 2
        deck_rows.append(("t1", idx, "p", "W", "Doomsday", None))
        card_rows += [
            ("t1", idx, "main", "Core Land", 4),
            ("t1", idx, "main", pair[0], 4 - wobble),
            ("t1", idx, "main", pair[1], 3 + wobble),
        ]
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", deck_rows)
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", card_rows)
    return con


def _insert_deck(con, deck_idx: int, counts: dict[str, int], archetype: str = "Doomsday") -> None:
    con.execute(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        ["t1", deck_idx, "p", "W", archetype, None],
    )
    for name, count in counts.items():
        con.execute(
            "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
            ["t1", deck_idx, "main", name, count],
        )


def _variants(con) -> dict[int, str | None]:
    return dict(
        con.execute("SELECT deck_idx, variant FROM decks WHERE tournament_id = 't1'").fetchall()
    )


class TestAssignIncremental:
    """Real centroids throughout: the split is produced by an actual `discover_subarchetypes`
    run over the 70-deck pool, then post-staging decks are inserted — the exact sequence that
    leaves fresh decks camp-unlabeled when a discovery re-run fails its stability gate."""

    # Deck indices reserved for post-staging decks (outside the clustered pool's 0..69).
    CLOSE_TO_A = 100
    NO_OVERLAP = 101

    def _stage(self, con, tmp_path, record=None) -> tuple[str, DiscoveredSplitRecord]:
        from legacy_engine.analytics.discovery import discover_subarchetypes

        if record is None:
            split = discover_subarchetypes(con, "Doomsday", seed=0, n_boot=10)
            assert split.passed, split.reasons
            record = record_from_split(split, generated_from="gen-1", params={})
        disc_path = str(tmp_path / "discovered.json")
        save_discovered(DiscoveredRegistry(version="1", splits=[record]), disc_path)
        return disc_path, record

    def _camp_of(self, record: DiscoveredSplitRecord, deck_idx: int) -> str:
        return next(
            c.name for c in record.camps if ("t1", deck_idx) in (c.member_keys or [])
        )

    def _fixture(self, tmp_path):
        """Cluster + stage over 70 decks, then add the post-staging decks and apply membership."""
        con = _con_with_clustered_doomsday_pool()
        disc_path, record = self._stage(con, tmp_path)
        _insert_deck(con, self.CLOSE_TO_A, {"Core Land": 4, "Card A1": 4, "Card A2": 3})
        _insert_deck(con, self.NO_OVERLAP, {"Core Land": 4, "Weird Tech": 4})
        apply_split(con, "Doomsday", discovered_path=disc_path)
        return con, disc_path, record

    def test_assigns_post_staging_deck_to_its_nearest_camp(self, tmp_path):
        con, disc_path, record = self._fixture(tmp_path)
        camp_a = self._camp_of(record, 0)

        result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert result.degraded is False
        assert result.n_assigned == 1
        assert result.per_camp == {camp_a: 1}
        assert _variants(con)[self.CLOSE_TO_A] == camp_a
        con.close()

    def test_assignment_row_carries_incremental_provenance(self, tmp_path):
        con, disc_path, record = self._fixture(tmp_path)
        camp_a = self._camp_of(record, 0)

        assign_incremental(con, "Doomsday", discovered_path=disc_path)

        rows = con.execute(
            "SELECT tournament_id, deck_idx, parent, camp, assigned_by, similarity, "
            "generated_from FROM variant_incremental_assignments"
        ).fetchall()
        assert len(rows) == 1
        tid, idx, parent, camp, assigned_by, similarity, generated_from = rows[0]
        assert (tid, idx, parent, camp) == ("t1", self.CLOSE_TO_A, "Doomsday", camp_a)
        assert assigned_by == "incremental"
        assert generated_from == "gen-1"
        assert similarity > 0.9   # a near-exact camp-A list
        con.close()

    def test_deck_sharing_no_flex_card_stays_unlabeled(self, tmp_path):
        con, disc_path, _record = self._fixture(tmp_path)

        result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert result.n_declined == 1
        assert _variants(con)[self.NO_OVERLAP] is None
        assigned_idxs = [
            r[0] for r in con.execute(
                "SELECT deck_idx FROM variant_incremental_assignments"
            ).fetchall()
        ]
        assert self.NO_OVERLAP not in assigned_idxs
        con.close()

    def test_cluster_members_are_not_re_examined(self, tmp_path):
        """apply_split runs first, so every clustered member already carries its membership
        label — incremental assignment must only ever consider the leftovers."""
        con, disc_path, _record = self._fixture(tmp_path)

        result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert result.n_assigned + result.n_declined == 2   # the two post-staging decks only
        assert con.execute(
            "SELECT count(*) FROM variant_incremental_assignments"
        ).fetchone()[0] == 1
        con.close()

    def test_min_similarity_floor_is_honoured(self, tmp_path):
        con, disc_path, _record = self._fixture(tmp_path)

        result = assign_incremental(
            con, "Doomsday", discovered_path=disc_path, min_similarity=0.999999,
        )

        assert result.n_assigned == 0
        assert result.n_declined == 2
        assert _variants(con)[self.CLOSE_TO_A] is None
        con.close()

    def test_other_archetype_decks_are_never_touched(self, tmp_path):
        con = _con_with_clustered_doomsday_pool()
        disc_path, _record = self._stage(con, tmp_path)
        _insert_deck(con, self.CLOSE_TO_A, {"Core Land": 4, "Card A1": 4, "Card A2": 3})
        _insert_deck(con, 200, {"Core Land": 4, "Card A1": 4, "Card A2": 3}, archetype="Lands")
        apply_split(con, "Doomsday", discovered_path=disc_path)

        assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert _variants(con)[200] is None
        con.close()

    def test_record_without_the_frozen_representation_degrades_honestly(self, tmp_path):
        """The ~30 real staged splits predating this path: named reason, zero decks touched."""
        con = _con_with_clustered_doomsday_pool()
        _, record = self._stage(con, tmp_path)
        old_shape = record.model_copy(update={
            "flex_cards": [],
            "camps": [c.model_copy(update={"centroid": None}) for c in record.camps],
        })
        disc_path, _ = self._stage(con, tmp_path, record=old_shape)
        _insert_deck(con, self.CLOSE_TO_A, {"Core Land": 4, "Card A1": 4, "Card A2": 3})
        apply_split(con, "Doomsday", discovered_path=disc_path)

        result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert result.degraded is True
        assert result.note is not None
        assert "no frozen flex vocabulary" in result.note
        assert "discover run" in result.note          # names the fix, not just the failure
        assert result.n_assigned == 0
        assert _variants(con)[self.CLOSE_TO_A] is None
        assert con.execute(
            "SELECT count(*) FROM variant_incremental_assignments"
        ).fetchone()[0] == 0
        con.close()

    def test_rerun_against_the_same_generation_is_idempotent(self, tmp_path):
        con, disc_path, record = self._fixture(tmp_path)
        first = assign_incremental(con, "Doomsday", discovered_path=disc_path)
        second = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert second.n_cleared == first.n_assigned
        assert second.n_assigned == first.n_assigned
        assert second.per_camp == first.per_camp
        assert _variants(con)[self.CLOSE_TO_A] == self._camp_of(record, 0)
        assert con.execute(
            "SELECT count(*) FROM variant_incremental_assignments"
        ).fetchone()[0] == 1
        con.close()

    def test_new_generation_claiming_the_deck_supersedes_the_incremental_label(self, tmp_path):
        """The supersession contract: once a PASSing run clusters the deck for real, the
        incremental row is cleared and the membership label — not the stale one — stands."""
        con, disc_path, record = self._fixture(tmp_path)
        assign_incremental(con, "Doomsday", discovered_path=disc_path)
        camp_b = self._camp_of(record, 69)

        # Generation 2 clusters the previously-incremental deck into the OTHER camp.
        gen2_camps = [
            c.model_copy(update={"member_keys": [*(c.member_keys or []), ("t1", self.CLOSE_TO_A)]})
            if c.name == camp_b else c
            for c in record.camps
        ]
        gen2 = record.model_copy(update={"camps": gen2_camps, "generated_from": "gen-2"})
        disc_path, _ = self._stage(con, tmp_path, record=gen2)

        apply_split(con, "Doomsday", discovered_path=disc_path)
        result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert result.n_cleared == 1
        assert _variants(con)[self.CLOSE_TO_A] == camp_b    # real membership, not the old label
        assert con.execute(
            "SELECT count(*) FROM variant_incremental_assignments"
        ).fetchone()[0] == 0
        con.close()

    def test_new_generation_not_claiming_the_deck_reassigns_it_fresh(self, tmp_path):
        """The other supersession branch: still uncovered by membership, so the stale row is
        cleared and rewritten against the new generation — never left orphaned."""
        con, disc_path, record = self._fixture(tmp_path)
        assign_incremental(con, "Doomsday", discovered_path=disc_path)

        gen2 = record.model_copy(update={"generated_from": "gen-2"})
        disc_path, _ = self._stage(con, tmp_path, record=gen2)

        apply_split(con, "Doomsday", discovered_path=disc_path)
        result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert result.n_cleared == 1
        assert result.n_assigned == 1
        rows = con.execute(
            "SELECT deck_idx, generated_from FROM variant_incremental_assignments"
        ).fetchall()
        assert rows == [(self.CLOSE_TO_A, "gen-2")]
        con.close()

    def test_no_staged_split_fails_fast(self, tmp_path):
        con = _con_with_clustered_doomsday_pool()
        with pytest.raises(ValueError, match="no staged candidate split for parent 'Doomsday'"):
            assign_incremental(con, "Doomsday", discovered_path=str(tmp_path / "nope.json"))
        con.close()

    def test_refuses_to_clear_rows_it_did_not_write(self, tmp_path):
        """assigned_by is a closed vocabulary — a row outside it is state this path doesn't own
        and must never silently delete."""
        con, disc_path, _record = self._fixture(tmp_path)
        assign_incremental(con, "Doomsday", discovered_path=disc_path)
        con.execute(
            "UPDATE variant_incremental_assignments SET assigned_by = 'hand-curated'"
        )

        with pytest.raises(ValueError, match="hand-curated"):
            assign_incremental(con, "Doomsday", discovered_path=disc_path)
        assert con.execute(
            "SELECT count(*) FROM variant_incremental_assignments"
        ).fetchone()[0] == 1
        con.close()

    def test_supersession_sweep_is_scoped_to_its_own_parent(self, tmp_path):
        """The clear step keys on `parent` — re-running one archetype must never drop another
        archetype's incremental rows or reset its labels."""
        con, disc_path, record = self._fixture(tmp_path)
        assign_incremental(con, "Doomsday", discovered_path=disc_path)

        # A second parent with its own incremental row, staged into the same registry.
        _insert_deck(con, 300, {"Core Land": 4, "Card A1": 4, "Card A2": 3}, archetype="Lands")
        lands = record.model_copy(update={"parent": "Lands", "camps": [
            c.model_copy(update={"member_keys": []}) for c in record.camps
        ]})
        disc_path = str(tmp_path / "both.json")
        save_discovered(DiscoveredRegistry(version="1", splits=[record, lands]), disc_path)
        lands_result = assign_incremental(con, "Lands", discovered_path=disc_path)
        assert lands_result.n_assigned == 1

        doomsday_result = assign_incremental(con, "Doomsday", discovered_path=disc_path)

        assert doomsday_result.n_cleared == 1   # its own row only
        parents = con.execute(
            "SELECT parent, deck_idx FROM variant_incremental_assignments ORDER BY parent"
        ).fetchall()
        assert parents == [("Doomsday", self.CLOSE_TO_A), ("Lands", 300)]
        assert _variants(con)[300] is not None
        con.close()
