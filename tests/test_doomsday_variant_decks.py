"""Data-contract tests for the four current Doomsday comparison registrations."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from legacy_engine.card_tags import staple_role
from legacy_engine.ingestion.banlist import banlist_as_of, current_banlist, validate_deck
from legacy_engine.models.banlist import BASIC_LAND_NAMES
from legacy_engine.models.decklist import parse_decklist


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "decks/doomsday-variants/manifest.json"
FIXTURE_DIR = ROOT / "tests/fixtures/doomsday_variants"
HISTORICAL_SNAPSHOT = banlist_as_of(date(2026, 8, 10))

EXPECTED_IDS = frozenset({
    "current-dimir-creature-transform",
    "current-esper-teferi-swords",
    "current-light-green-white",
    "current-four-color-shield",
})
EXPECTED_HASHES = {
    "current-dimir-creature-transform": "02eb0b378efbd7861e7be9e9b5aac61e34e83fc842af627bf061ba48262d62ab",
    "current-esper-teferi-swords": "e0237b790a3c7579331903611147df3f32892afcf1b1bce3cf7a9c090fdf7620",
    "current-light-green-white": "dbd444ab43279a87d82d58fc1eef244f5451116451797c017a5057d7bf4b0f98",
    "current-four-color-shield": "4109763e425cb4db5cf2b41cc1e2b9214aa56573b393cf3ab1930fb5a71480fe",
}
EXPECTED_SOURCE = {
    "current-dimir-creature-transform": {
        "cache_path": "data/cache/Tournaments/MTGO/2026/08/16/legacy-challenge-32-2026-08-1612851673.json",
        "tournament_id": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-1612851673",
        "deck_idx": 9,
        "event_date": "2026-08-16",
        "event_name": "Legacy Challenge 32",
        "player": "2plus2isfive",
        "result": "10th Place",
        "attestation_handle": "ddv-compare-current-corpus",
    },
    "current-esper-teferi-swords": {
        "cache_path": "data/cache/Tournaments/MTGO/2026/08/12/legacy-league-2026-08-1210967.json",
        "tournament_id": "https://www.mtgo.com/decklist/legacy-league-2026-08-1210967",
        "deck_idx": 3,
        "event_date": "2026-08-12",
        "event_name": "Legacy League",
        "player": "Battlegrounds",
        "result": "5-0",
        "attestation_handle": "ddv-packages-list-esper-battlegrounds",
    },
    "current-light-green-white": {
        "cache_path": "data/cache/Tournaments/MTGO/2026/08/15/legacy-challenge-32-2026-08-1512851657.json",
        "tournament_id": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-1512851657",
        "deck_idx": 16,
        "event_date": "2026-08-15",
        "event_name": "Legacy Challenge 32",
        "player": "wizardpasta",
        "result": "17th Place",
        "attestation_handle": "ddv-packages-list-green-white-wizardpasta",
    },
    "current-four-color-shield": {
        "cache_path": "data/cache/Tournaments/MTGO/2026/08/14/legacy-league-2026-08-1410967.json",
        "tournament_id": "https://www.mtgo.com/decklist/legacy-league-2026-08-1410967",
        "deck_idx": 9,
        "event_date": "2026-08-14",
        "event_name": "Legacy League",
        "player": "wakame",
        "result": "5-0",
        "attestation_handle": "ddv-packages-list-four-color-wakame",
    },
}

# This is the small deterministic card-dimension fixture used by the contract tests. It keeps
# CI independent of the mutable DuckDB while retaining the local curated fetchland dimension.
NONFETCH_LAND_NAMES = frozenset({
    "Cavern of Souls", "Island", "Scrubland", "Snow-Covered Island", "Snow-Covered Swamp",
    "Swamp", "Tropical Island", "Tundra", "Undercity Sewers", "Underground Sea",
})

FIXTURE_PATHS = {
    candidate_id: FIXTURE_DIR / f"{candidate_id}.json" for candidate_id in EXPECTED_IDS
}


def load_source_fixture(candidate_id: str) -> dict[str, Any]:
    """Load the tracked immutable source row; never consult the gitignored cache in CI."""
    value = json.loads(FIXTURE_PATHS[candidate_id].read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"source fixture for {candidate_id!r} must be an object")
    return value


def _card_dimension_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for candidate_id in EXPECTED_IDS:
        deck = load_source_fixture(candidate_id)["deck"]
        for name in set(deck["mainboard"]) | set(deck["sideboard"]):
            if name in NONFETCH_LAND_NAMES or name in BASIC_LAND_NAMES or staple_role(name) == "fetchland":
                names[name] = "land"
            else:
                names[name] = "spell"
    return names


CARD_DIMENSION = _card_dimension_names()
CARD_DIMENSION_ALLOWED = frozenset({"land", "spell"})
assert set(CARD_DIMENSION.values()) <= CARD_DIMENSION_ALLOWED


def load_candidate_manifest(path: Path) -> dict[str, object]:
    """Load the manifest without consulting the local card or tournament stores."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("candidate manifest root must be an object")
    return value


def canonical_deck_sha256(main: dict[str, int], side: dict[str, int]) -> str:
    """Hash sorted compact board pairs so formatting/order cannot change identity."""
    payload = {
        "main": sorted([[name, count] for name, count in main.items()]),
        "side": sorted([[name, count] for name, count in side.items()]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def board_delta(
    candidate: dict[str, int],
    baseline: dict[str, int],
    *,
    fetchland_names: frozenset[str],
) -> tuple[int, int, int]:
    """Return absolute multiset copy deltas as (spells, nonfetch lands, fetchlands)."""
    deltas = [0, 0, 0]
    for name in set(candidate) | set(baseline):
        difference = abs(candidate.get(name, 0) - baseline.get(name, 0))
        if name in fetchland_names:
            bucket = 2
        elif name in NONFETCH_LAND_NAMES or name in BASIC_LAND_NAMES:
            bucket = 1
        else:
            bucket = 0
        deltas[bucket] += difference
    return tuple(deltas)  # type: ignore[return-value]


def _copy_manifest(value: dict[str, object]) -> dict[str, object]:
    return copy.deepcopy(value)


def _candidate_entries(manifest: dict[str, object]) -> list[dict[str, Any]]:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("manifest 'candidates' must be a list")
    if len(candidates) != 4:
        raise ValueError(f"manifest must contain exactly four candidates, got {len(candidates)}")
    if not all(isinstance(candidate, dict) for candidate in candidates):
        raise ValueError("manifest candidates must be objects")
    return candidates  # type: ignore[return-value]


def _validate_manifest_shape(manifest: dict[str, object], *, root: Path = ROOT) -> list[dict[str, Any]]:
    if manifest.get("schema") != "doomsday-variant-candidates":
        raise ValueError("unknown manifest schema")
    if manifest.get("banlist_snapshot_as_of") != "2026-08-10":
        raise ValueError("manifest must pin the 2026-08-10 ban snapshot")
    if manifest.get("legality_checked_on") != "2026-08-20":
        raise ValueError("manifest legality_checked_on drifted")
    if manifest.get("shared_base_policy") != "fetchlands-only":
        raise ValueError("unknown shared_base_policy")

    candidates = _candidate_entries(manifest)
    ids = [candidate.get("id") for candidate in candidates]
    if any(candidate_id not in EXPECTED_IDS for candidate_id in ids):
        bad = next(candidate_id for candidate_id in ids if candidate_id not in EXPECTED_IDS)
        raise ValueError(f"unknown candidate id {bad!r}; allowed set is {sorted(EXPECTED_IDS)!r}")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate candidate id")
    if set(ids) != EXPECTED_IDS:
        raise ValueError("manifest candidate ids do not match the closed set")
    if manifest.get("compatibility_baseline_id") != "current-dimir-creature-transform":
        raise ValueError("manifest baseline id is not the Dimir control")

    paths: list[str] = []
    for candidate in candidates:
        candidate_id = candidate["id"]
        if candidate.get("status") != "exact-registration":
            raise ValueError(f"unknown status {candidate.get('status')!r}")
        path = candidate.get("path")
        if not isinstance(path, str) or not path.endswith(".txt"):
            raise ValueError(f"candidate {candidate_id!r} has invalid path")
        paths.append(path)
        if not (root / path).is_file():
            raise ValueError(f"candidate {candidate_id!r} file is absent: {path}")

        source = candidate.get("source")
        fixture = load_source_fixture(candidate_id)
        fixture_deck = fixture.get("deck")
        expected_source = {
            "cache_path": fixture.get("source_path"),
            "tournament_id": fixture.get("tournament_id"),
            "deck_idx": fixture.get("deck_idx"),
            "event_date": fixture.get("event_date"),
            "event_name": fixture.get("event_name"),
            "player": fixture_deck.get("player") if isinstance(fixture_deck, dict) else None,
            "result": fixture_deck.get("result") if isinstance(fixture_deck, dict) else None,
            "attestation_handle": EXPECTED_SOURCE[candidate_id]["attestation_handle"],
        }
        if not isinstance(source, dict) or source != expected_source:
            raise ValueError(f"candidate {candidate_id!r} source metadata drifted")
        try:
            date.fromisoformat(source["event_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"candidate {candidate_id!r} has invalid source event_date") from exc
        digest = candidate.get("canonical_deck_sha256")
        if digest != EXPECTED_HASHES[candidate_id] or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"candidate {candidate_id!r} has an unpinned canonical hash")

        axes = candidate.get("observed_axes")
        if not isinstance(axes, dict) or not isinstance(axes.get("chassis"), str):
            raise ValueError(f"candidate {candidate_id!r} has invalid observed chassis")
        for axis in ("protection", "interaction"):
            if (not isinstance(axes.get(axis), list) or not axes[axis]
                    or not all(isinstance(item, str) for item in axes[axis])):
                raise ValueError(f"candidate {candidate_id!r} has invalid observed {axis}")
        if not isinstance(axes.get("postboard_plan"), str):
            raise ValueError(f"candidate {candidate_id!r} has invalid observed postboard_plan")

        compatibility = candidate.get("shared_base_compatibility")
        if not isinstance(compatibility, dict):
            raise ValueError(f"candidate {candidate_id!r} has no compatibility object")
        allowed_statuses = {
            "baseline", "compatible", "incompatible-spells", "incompatible-nonfetch",
            "incompatible-spells-and-nonfetch",
        }
        if compatibility.get("status") not in allowed_statuses:
            raise ValueError(f"unknown compatibility status {compatibility.get('status')!r}")
        for field in ("spell_delta", "nonfetch_land_delta", "fetchland_delta"):
            if not isinstance(compatibility.get(field), int) or compatibility[field] < 0:
                raise ValueError(f"candidate {candidate_id!r} has invalid {field}")

    if len(set(paths)) != len(paths):
        raise ValueError("duplicate candidate path")

    parsed = {candidate["id"]: _validate_candidate_file(candidate, root=root) for candidate in candidates}
    baseline = parsed[manifest["compatibility_baseline_id"]][0]
    fetchlands = frozenset(
        name for main, _side in parsed.values() for name in main if staple_role(name) == "fetchland"
    )
    for candidate in candidates:
        main, _side = parsed[candidate["id"]]
        deltas = board_delta(main, baseline, fetchland_names=fetchlands)
        compatibility = candidate["shared_base_compatibility"]
        expected_status = (
            "baseline" if deltas == (0, 0, 0)
            else "compatible" if deltas[:2] == (0, 0)
            else "incompatible-spells" if deltas[0] and not deltas[1]
            else "incompatible-nonfetch" if deltas[1] and not deltas[0]
            else "incompatible-spells-and-nonfetch"
        )
        actual_deltas = tuple(compatibility[field] for field in (
            "spell_delta", "nonfetch_land_delta", "fetchland_delta",
        ))
        if actual_deltas != deltas or compatibility["status"] != expected_status:
            raise ValueError(
                f"candidate {candidate['id']!r} compatibility drifted: "
                f"expected status={expected_status!r}, deltas={deltas!r}"
            )
    return candidates


def _validate_candidate_file(
    candidate: dict[str, Any], *, root: Path = ROOT, verify_fixture: bool = True,
) -> tuple[dict[str, int], dict[str, int]]:
    path = root / candidate["path"]
    try:
        main, side = parse_decklist(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"unable to parse candidate {candidate['id']!r}: {exc}") from exc
    if sum(main.values()) != 60 or sum(side.values()) != 15:
        raise ValueError(f"candidate {candidate['id']!r} must contain exactly 60/15 cards")
    for snapshot in (HISTORICAL_SNAPSHOT, current_banlist()):
        errors = validate_deck(main, side, snapshot=snapshot)
        if errors:
            raise ValueError(f"candidate {candidate['id']!r} is illegal: {errors}")
    digest = canonical_deck_sha256(main, side)
    if digest != candidate["canonical_deck_sha256"]:
        raise ValueError(f"candidate {candidate['id']!r} canonical hash drifted")
    names = set(main) | set(side)
    unknown_names = names - CARD_DIMENSION.keys()
    if unknown_names:
        raise ValueError(f"card dimension missing names: {sorted(unknown_names)!r}")
    if verify_fixture:
        fixture_deck = load_source_fixture(candidate["id"])["deck"]
        if main != fixture_deck["mainboard"] or side != fixture_deck["sideboard"]:
            raise ValueError(f"candidate {candidate['id']!r} differs from tracked source fixture")
    observed = candidate["observed_axes"]
    observed_cards = names
    for axis in ("protection", "interaction"):
        missing = set(observed[axis]) - observed_cards
        if missing:
            raise ValueError(f"candidate {candidate['id']!r} observed {axis} missing cards: {sorted(missing)!r}")
    return main, side


class TestDoomsdayVariantManifest:
    def test_shipped_manifest_and_registrations(self):
        manifest = load_candidate_manifest(MANIFEST_PATH)
        candidates = _validate_manifest_shape(manifest)
        baseline: dict[str, int] | None = None
        fetchlands = frozenset(
            name for candidate in candidates
            for name in _validate_candidate_file(candidate)[0]
            if staple_role(name) == "fetchland"
        )
        for candidate in candidates:
            main, _side = _validate_candidate_file(candidate)
            if candidate["id"] == manifest["compatibility_baseline_id"]:
                baseline = main
            assert candidate["canonical_deck_sha256"] == EXPECTED_HASHES[candidate["id"]]
        assert baseline is not None
        for candidate in candidates:
            main, _side = _validate_candidate_file(candidate)
            deltas = board_delta(main, baseline, fetchland_names=fetchlands)
            compatibility = candidate["shared_base_compatibility"]
            assert deltas == (
                compatibility["spell_delta"],
                compatibility["nonfetch_land_delta"],
                compatibility["fetchland_delta"],
            )
            expected_status = (
                "baseline" if deltas == (0, 0, 0)
                else "compatible" if deltas[:2] == (0, 0)
                else "incompatible-spells" if deltas[0] and not deltas[1]
                else "incompatible-nonfetch" if deltas[1] and not deltas[0]
                else "incompatible-spells-and-nonfetch"
            )
            assert compatibility["status"] == expected_status

    def test_source_objects_are_pinned_to_attested_records(self):
        manifest = load_candidate_manifest(MANIFEST_PATH)
        for candidate in _validate_manifest_shape(manifest):
            fixture = load_source_fixture(candidate["id"])
            source = candidate["source"]
            deck = fixture["deck"]
            assert source["cache_path"] == fixture["source_path"]
            assert source["tournament_id"] == fixture["tournament_id"]
            assert source["deck_idx"] == fixture["deck_idx"]
            assert source["event_date"] == fixture["event_date"]
            assert source["event_name"] == fixture["event_name"]
            assert source["player"] == deck["player"]
            assert source["result"] == deck["result"]
            assert deck["anchor_uri"] == f"{source['tournament_id']}#deck_{source['player']}"
            assert Path(source["cache_path"]).parts[:2] == ("data", "cache")
            assert source["attestation_handle"] == EXPECTED_SOURCE[candidate["id"]]["attestation_handle"]

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("id", "unknown-candidate", "unknown candidate id"),
            ("status", "inferred-registration", "unknown status"),
        ],
    )
    def test_closed_vocabularies_fail_fast(self, field, value, message):
        manifest = _copy_manifest(load_candidate_manifest(MANIFEST_PATH))
        manifest["candidates"][0][field] = value
        with pytest.raises(ValueError, match=message):
            _validate_manifest_shape(manifest)

    @pytest.mark.parametrize("mutation", ["duplicate_id", "duplicate_path", "missing_file"])
    def test_manifest_identity_and_presence_guards(self, mutation):
        manifest = _copy_manifest(load_candidate_manifest(MANIFEST_PATH))
        if mutation == "duplicate_id":
            manifest["candidates"][1]["id"] = manifest["candidates"][0]["id"]
        elif mutation == "duplicate_path":
            manifest["candidates"][1]["path"] = manifest["candidates"][0]["path"]
        else:
            manifest["candidates"][0]["path"] = "decks/doomsday-variants/missing.txt"
        with pytest.raises(ValueError, match="duplicate|absent|candidate ids"):
            _validate_manifest_shape(manifest)

    def test_the_fantasticar_is_rejected_by_both_contract_snapshots(self):
        main = {"The Fantasticar": 1, "Island": 59}
        for snapshot in (HISTORICAL_SNAPSHOT, current_banlist()):
            assert any("The Fantasticar is banned" in error for error in validate_deck(main, snapshot=snapshot))


class TestDoomsdayVariantFiles:
    def test_parser_rejects_malformed_lines(self, tmp_path):
        path = tmp_path / "malformed.txt"
        path.write_text("4 Brainstorm\nnot a card line\n", encoding="utf-8")
        with pytest.raises(ValueError, match="malformed line"):
            parse_decklist(path.read_text(encoding="utf-8"))

    @pytest.mark.parametrize("mutation", ["count", "sideboard", "copy_limit", "banned", "hash"])
    def test_file_contract_rejects_drift(self, mutation, tmp_path):
        manifest = load_candidate_manifest(MANIFEST_PATH)
        candidate = _copy_manifest(manifest)["candidates"][0]
        source = (ROOT / candidate["path"]).read_text(encoding="utf-8")
        if mutation == "count":
            source = source.replace("1 Consider", "0 Consider", 1)
        elif mutation == "sideboard":
            source = source.replace("1 Snuff Out", "2 Snuff Out", 1)
        elif mutation == "copy_limit":
            source = source.replace("4 Brainstorm", "5 Brainstorm", 1).replace("1 Consider", "0 Consider", 1)
        elif mutation == "banned":
            source = source.replace("1 Consider", "1 The Fantasticar", 1)
        else:
            source = source.replace("1 Consider", "1 Cavern of Souls", 1)
        candidate["path"] = "candidate.txt"
        path = tmp_path / candidate["path"]
        path.write_text(source, encoding="utf-8")
        with pytest.raises(ValueError, match="60/15|illegal|canonical hash"):
            _validate_candidate_file(candidate, root=tmp_path, verify_fixture=False)

    def test_compatibility_delta_boundaries(self):
        baseline = {"Brainstorm": 4, "Island": 1, "Polluted Delta": 2}
        assert board_delta(
            {"Brainstorm": 4, "Island": 1, "Polluted Delta": 3},
            baseline,
            fetchland_names=frozenset({"Polluted Delta"}),
        ) == (0, 0, 1)
        assert board_delta(
            {"Brainstorm": 5, "Island": 1, "Polluted Delta": 2},
            baseline,
            fetchland_names=frozenset({"Polluted Delta"}),
        ) == (1, 0, 0)
        assert board_delta(
            {"Brainstorm": 4, "Island": 2, "Polluted Delta": 2},
            baseline,
            fetchland_names=frozenset({"Polluted Delta"}),
        ) == (0, 1, 0)

    def test_unknown_card_dimension_name_has_named_failure(self, tmp_path):
        manifest = load_candidate_manifest(MANIFEST_PATH)
        candidate = _copy_manifest(manifest)["candidates"][0]
        source = (ROOT / candidate["path"]).read_text(encoding="utf-8")
        source = source.replace("1 Consider", "1 Unmodeled Card", 1)
        candidate["path"] = "candidate.txt"
        path = tmp_path / candidate["path"]
        path.write_text(source, encoding="utf-8")
        main, side = parse_decklist(source)
        candidate["canonical_deck_sha256"] = canonical_deck_sha256(main, side)
        with pytest.raises(ValueError, match="card dimension missing names"):
            _validate_candidate_file(candidate, root=tmp_path, verify_fixture=False)
