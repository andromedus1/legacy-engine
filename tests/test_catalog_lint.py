"""Tests for `legacy_engine.catalog_lint` (epic-data-autonomy-catalog-lint).

House style: file-backed hermetic DuckDB via `_build_lint_db(tmp_path, cards=...) -> str`
(file-backed-cli-test-db-builder pattern) — every test opens its own tmp DuckDB and never
touches the default DB. Per-check tests write small crafted hoser/linchpin JSON files to
`tmp_path` and pass them to `lint_catalogs` via the `hosers_path`/`linchpins_path` overrides;
the golden test (`TestShippedCatalogsLintClean`) is the CI gate — it loads the REAL shipped
curated JSON (default paths) against a frozen fixture of every card those files name and
asserts zero error-severity findings, so a typo'd curated entry fails the suite.

`tests/data/catalog_lint_cards.json` was generated once from the real
`data/legacy.duckdb` (read-only) with a one-off script pulling
`name, mana_cost, cmc, type_line, colors, produced_mana, oracle_text, layout, is_land, power,
toughness` for every card name appearing in either shipped curated JSON at authoring time. It is
committed and must be regenerated (same query) if either curated file gains a new card name.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from legacy_engine.catalog_lint import lint_catalogs
from legacy_engine.config import HOSERS_REGISTRY_PATH, LINCHPINS_REGISTRY_PATH
from legacy_engine.ingestion import store

_FIXTURE_PATH = Path(__file__).parent / "data" / "catalog_lint_cards.json"
_FIXTURE_CARDS: "list[dict]" = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

_CARDS_COLS = (
    "name, mana_cost, cmc, type_line, colors, produced_mana, oracle_text, layout, is_land, "
    "power, toughness"
)


def _build_lint_db(tmp_path, cards: "list[dict] | None" = None) -> str:
    """File-backed hermetic DuckDB: a ``cards`` table seeded from the frozen fixture (default)
    or a caller-supplied card-row list (crafted bad-entry tests)."""
    db_path = str(tmp_path / "catalog_lint.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    rows = _FIXTURE_CARDS if cards is None else cards
    con.executemany(
        f"INSERT INTO cards ({_CARDS_COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c["name"],
                c.get("mana_cost", ""),
                c.get("cmc", 0.0),
                c.get("type_line", ""),
                c.get("colors", ""),
                c.get("produced_mana", ""),
                c.get("oracle_text", ""),
                c.get("layout", "normal"),
                c.get("is_land", False),
                c.get("power"),
                c.get("toughness"),
            )
            for c in rows
        ],
    )
    con.close()
    return db_path


def _write_hosers(tmp_path, entries: "list[dict]", name: str = "hosers.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"version": "test", "hosers": entries}), encoding="utf-8")
    return path


def _write_linchpins(tmp_path, linchpins: dict, name: str = "linchpins.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"version": 1, "linchpins": linchpins}), encoding="utf-8")
    return path


def _empty_hosers(tmp_path) -> Path:
    return _write_hosers(tmp_path, [])


def _empty_linchpins(tmp_path) -> Path:
    return _write_linchpins(tmp_path, {})


def _findings_for(findings, check: str) -> list:
    return [f for f in findings if f.check == check]


@pytest.fixture
def con_factory(tmp_path):
    """Returns a zero-arg callable that connects to a tmp DB seeded with the base card fixture
    (Wasteland only, by default) — most per-check tests only need one or two real cards."""

    def _make(cards: "list[dict] | None" = None):
        db_path = _build_lint_db(tmp_path, cards=cards)
        return store.connect(db_path)

    return _make


_WASTELAND = {
    "name": "Wasteland",
    "mana_cost": "",
    "cmc": 0.0,
    "type_line": "Land",
    "colors": "",
    "produced_mana": "C",
    "oracle_text": "{T}: Add {C}.\n{T}, Sacrifice this land: Destroy target nonbasic land.",
    "layout": "normal",
    "is_land": True,
}

_NULL_ROD = {
    "name": "Null Rod",
    "mana_cost": "{2}",
    "cmc": 2.0,
    "type_line": "Artifact",
    "colors": "",
    "produced_mana": "",
    "oracle_text": "Activated abilities of artifacts can't be activated.",
    "layout": "normal",
    "is_land": False,
}


class TestNameExists:
    def test_hoser_nonexistent_name_errors(self, tmp_path, con_factory):
        con = con_factory([_WASTELAND])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Not A Real Card", "attacks": ["_hate"], "colors": [], "max_copies": 4,
             "swing": "soft"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        name_errors = _findings_for(findings, "name_exists")
        assert len(name_errors) == 1
        assert name_errors[0].severity == "error"
        assert name_errors[0].entry == "Not A Real Card"

    def test_linchpin_nonexistent_name_errors(self, tmp_path, con_factory):
        con = con_factory([_WASTELAND])
        linchpins_path = _write_linchpins(tmp_path, {
            "Fake Archetype": [
                {"name": "Not A Real Card", "role": "combo-engine", "centrality": 1.0,
                 "neutralized_by": []},
            ],
        })
        findings = lint_catalogs(con, hosers_path=_empty_hosers(tmp_path), linchpins_path=linchpins_path)
        con.close()

        name_errors = _findings_for(findings, "name_exists")
        assert len(name_errors) == 1
        assert name_errors[0].severity == "error"
        assert name_errors[0].entry == "Not A Real Card"
        assert "Fake Archetype" in name_errors[0].message

    def test_existing_names_no_error(self, tmp_path, con_factory):
        con = con_factory([_WASTELAND])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Wasteland", "attacks": ["nonbasic-manabase"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "asymmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "name_exists") == []


class TestColorsMatch:
    def test_wrong_colors_errors(self, tmp_path, con_factory):
        """The Null Rod bug, reproduced: curated ["G"] on an actually-colorless card."""
        con = con_factory([_NULL_ROD])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Null Rod", "attacks": ["artifact-mana-reliant"], "colors": ["G"], "max_copies": 4,
             "swing": "soft", "symmetry": "symmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        color_errors = _findings_for(findings, "colors_match")
        assert len(color_errors) == 1
        assert color_errors[0].severity == "error"
        assert color_errors[0].entry == "Null Rod"
        assert "['G']" in color_errors[0].message

    def test_correct_colors_no_finding(self, tmp_path, con_factory):
        con = con_factory([_NULL_ROD])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Null Rod", "attacks": ["artifact-mana-reliant"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "symmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "colors_match") == []

    def test_missing_card_skips_colors_check(self, tmp_path, con_factory):
        """A nonexistent name already errors on name_exists; colors_match must not also fire
        (there's no card row to compare against)."""
        con = con_factory([_WASTELAND])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Not A Real Card", "attacks": ["_hate"], "colors": ["G"], "max_copies": 4,
             "swing": "soft"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "colors_match") == []


_FAERIE_MACABRE = {
    "name": "Faerie Macabre",
    "mana_cost": "{1}{B}{B}",
    "cmc": 3.0,
    "type_line": "Creature — Faerie Rogue",
    "colors": "B",
    "produced_mana": "",
    "oracle_text": "Flying\nDiscard this card: Exile up to two target cards from graveyards.",
    "layout": "normal",
    "is_land": False,
}

_SURGICAL_EXTRACTION = {
    "name": "Surgical Extraction",
    "mana_cost": "{B/P}",
    "cmc": 1.0,
    "type_line": "Instant",
    "colors": "B",
    "produced_mana": "",
    "oracle_text": (
        "({B/P} can be paid with either {B} or 2 life.)\nChoose target card in a graveyard "
        "other than a basic land card."
    ),
    "layout": "normal",
    "is_land": False,
}

_DAUTHI_VOIDWALKER = {
    "name": "Dauthi Voidwalker",
    "mana_cost": "{B}{B}",
    "cmc": 2.0,
    "type_line": "Creature — Dauthi Rogue",
    "colors": "B",
    "produced_mana": "",
    "oracle_text": (
        "Shadow\nIf a card would be put into an opponent's graveyard from anywhere, instead "
        "exile it with a void counter on it.\n{T}, Sacrifice this creature: Choose an exiled "
        "card an opponent owns with a void counter on it."
    ),
    "layout": "normal",
    "is_land": False,
    "power": "3",
    "toughness": "2",
}


class TestCastableAnyColorSignal:
    def test_declared_true_without_signal_warns(self, tmp_path, con_factory):
        """Dauthi Voidwalker requires BB to cast — no Phyrexian mana, no free-hand ability —
        so declaring castable_any_color=True on it should warn."""
        con = con_factory([_DAUTHI_VOIDWALKER])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Dauthi Voidwalker", "attacks": ["graveyard-recursion"], "colors": ["B"],
             "max_copies": 4, "swing": "dedicated", "symmetry": "asymmetric",
             "castable_any_color": True},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        warns = _findings_for(findings, "castable_any_color_signal")
        assert len(warns) == 1
        assert warns[0].severity == "warn"

    def test_phyrexian_mana_not_declared_warns(self, tmp_path, con_factory):
        con = con_factory([_SURGICAL_EXTRACTION])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Surgical Extraction", "attacks": ["graveyard-recursion"], "colors": ["B"],
             "max_copies": 2, "swing": "dedicated", "symmetry": "asymmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        warns = _findings_for(findings, "castable_any_color_signal")
        assert len(warns) == 1
        assert "Phyrexian" in warns[0].message

    def test_phyrexian_mana_declared_no_warning(self, tmp_path, con_factory):
        con = con_factory([_SURGICAL_EXTRACTION])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Surgical Extraction", "attacks": ["graveyard-recursion"], "colors": ["B"],
             "max_copies": 2, "swing": "dedicated", "symmetry": "asymmetric",
             "castable_any_color": True},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "castable_any_color_signal") == []

    def test_free_hand_activation_declared_no_warning(self, tmp_path, con_factory):
        con = con_factory([_FAERIE_MACABRE])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Faerie Macabre", "attacks": ["graveyard-recursion"], "colors": ["B"],
             "max_copies": 2, "swing": "dedicated", "symmetry": "asymmetric",
             "castable_any_color": True},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "castable_any_color_signal") == []


class TestSymmetryWording:
    def test_symmetric_wording_declared_asymmetric_warns(self, tmp_path, con_factory):
        card = dict(_NULL_ROD, name="Fake Symmetric Card",
                    oracle_text="Each player discards a card at the beginning of their upkeep.")
        con = con_factory([card])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Fake Symmetric Card", "attacks": ["_hate"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "asymmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        warns = _findings_for(findings, "symmetry_wording")
        assert len(warns) == 1
        assert warns[0].severity == "warn"

    def test_opponent_scoped_wording_no_warning(self, tmp_path, con_factory):
        card = dict(_NULL_ROD, name="Fake Asymmetric Card",
                    oracle_text="Each opponent discards a card at the beginning of their upkeep.")
        con = con_factory([card])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Fake Asymmetric Card", "attacks": ["_hate"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "asymmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "symmetry_wording") == []

    def test_symmetric_declared_no_warning_even_with_wording(self, tmp_path, con_factory):
        card = dict(_NULL_ROD, name="Fake Symmetric Card 2",
                    oracle_text="Each player discards a card at the beginning of their upkeep.")
        con = con_factory([card])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Fake Symmetric Card 2", "attacks": ["_hate"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "symmetric"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "symmetry_wording") == []


class TestFunctionalGroupCoherence:
    def test_dissimilar_group_warns(self, tmp_path, con_factory):
        """Null Rod + Wasteland share nothing effect-wise — a nonsense functional_group pairing
        should warn."""
        con = con_factory([_NULL_ROD, _WASTELAND])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Null Rod", "attacks": ["artifact-mana-reliant"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "symmetric", "functional_group": "nonsense-group"},
            {"name": "Wasteland", "attacks": ["nonbasic-manabase"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "asymmetric", "functional_group": "nonsense-group"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        warns = _findings_for(findings, "functional_group_coherence")
        assert len(warns) == 1
        assert warns[0].severity == "warn"
        assert "nonsense-group" in warns[0].message

    def test_similar_group_no_warning(self, tmp_path, con_factory):
        """Hydroblast / Blue Elemental Blast: near-verbatim reprints of the same effect with the
        color swapped — must not warn."""
        hydroblast = {
            "name": "Hydroblast", "mana_cost": "{U}", "cmc": 1.0, "type_line": "Instant",
            "colors": "U", "produced_mana": "", "layout": "normal", "is_land": False,
            "oracle_text": "Choose one —\n• Counter target spell if it's red.\n• Destroy target permanent if it's red.",
        }
        blue_elemental_blast = {
            "name": "Blue Elemental Blast", "mana_cost": "{U}", "cmc": 1.0, "type_line": "Instant",
            "colors": "U", "produced_mana": "", "layout": "normal", "is_land": False,
            "oracle_text": "Choose one —\n• Counter target red spell.\n• Destroy target red permanent.",
        }
        con = con_factory([hydroblast, blue_elemental_blast])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Hydroblast", "attacks": ["plays-red"], "colors": ["U"], "max_copies": 4,
             "swing": "soft", "symmetry": "asymmetric", "functional_group": "red-blast"},
            {"name": "Blue Elemental Blast", "attacks": ["plays-red"], "colors": ["U"],
             "max_copies": 2, "swing": "soft", "symmetry": "asymmetric",
             "functional_group": "red-blast"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "functional_group_coherence") == []

    def test_singleton_group_no_finding(self, tmp_path, con_factory):
        """A functional_group with only one member has nothing to compare — never fires."""
        con = con_factory([_NULL_ROD])
        hosers_path = _write_hosers(tmp_path, [
            {"name": "Null Rod", "attacks": ["artifact-mana-reliant"], "colors": [], "max_copies": 4,
             "swing": "soft", "symmetry": "symmetric", "functional_group": "lonely-group"},
        ])
        findings = lint_catalogs(con, hosers_path=hosers_path, linchpins_path=_empty_linchpins(tmp_path))
        con.close()

        assert _findings_for(findings, "functional_group_coherence") == []


class TestShippedCatalogsLintClean:
    """The CI gate: the ACTUAL shipped curated JSON, cross-checked against a frozen fixture of
    every card it names, must produce zero error-severity findings. A future typo'd curated
    entry fails this test."""

    def test_shipped_catalogs_zero_errors(self, tmp_path):
        db_path = _build_lint_db(tmp_path)
        con = store.connect(db_path)
        try:
            findings = lint_catalogs(
                con, hosers_path=HOSERS_REGISTRY_PATH, linchpins_path=LINCHPINS_REGISTRY_PATH
            )
        finally:
            con.close()

        errors = [f for f in findings if f.severity == "error"]
        assert errors == [], f"shipped curated catalogs have error-severity lint findings: {errors}"

    def test_shipped_catalogs_zero_warnings(self, tmp_path):
        """Heuristics were tuned so the shipped set is warn-clean too (see story notes for the
        alternative of documenting accepted warns — none are needed here)."""
        db_path = _build_lint_db(tmp_path)
        con = store.connect(db_path)
        try:
            findings = lint_catalogs(
                con, hosers_path=HOSERS_REGISTRY_PATH, linchpins_path=LINCHPINS_REGISTRY_PATH
            )
        finally:
            con.close()

        warnings = [f for f in findings if f.severity == "warn"]
        assert warnings == [], f"shipped curated catalogs have warn-level lint findings: {warnings}"

    def test_fixture_covers_every_curated_name(self):
        """Guards the fixture itself: every name in either shipped curated JSON must be present
        in the frozen fixture, or the golden test above would silently degrade to a pile of
        name_exists errors instead of testing the intended checks."""
        import json as _json

        hosers_raw = _json.loads(HOSERS_REGISTRY_PATH.read_text(encoding="utf-8"))
        linchpins_raw = _json.loads(LINCHPINS_REGISTRY_PATH.read_text(encoding="utf-8"))

        curated_names = {e["name"] for e in hosers_raw["hosers"]}
        for entries in linchpins_raw["linchpins"].values():
            curated_names.update(e["name"] for e in entries)

        fixture_names = {c["name"] for c in _FIXTURE_CARDS}
        missing = curated_names - fixture_names
        assert missing == set(), f"fixture is missing curated names: {missing}"
