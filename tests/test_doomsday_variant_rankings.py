"""Hermetic contracts for the Doomsday variant report.

The report reads the same five fact tables as production, but these tests use a
small in-memory DuckDB fixture.  In particular, no test opens the live corpus
or relies on the shipped HTML report.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from legacy_engine.advisory.doomsday_variants import (
    build_variant_report,
    classify_variant,
)
from scripts.refresh_doomsday_variant_rankings import (
    _atomic_write_text,
    render_report,
)


def _metadata() -> dict[str, dict[str, object]]:
    return {
        "Island": {"is_land": True, "produced_mana": "U", "oracle_text": ""},
        "Swamp": {"is_land": True, "produced_mana": "B", "oracle_text": ""},
        "Mountain": {"is_land": True, "produced_mana": "R", "oracle_text": ""},
        "Forest": {"is_land": True, "produced_mana": "G", "oracle_text": ""},
        "Plains": {"is_land": True, "produced_mana": "W", "oracle_text": ""},
        "Underground Sea": {"is_land": True, "produced_mana": "UB", "oracle_text": ""},
        "Bayou": {"is_land": True, "produced_mana": "BG", "oracle_text": ""},
        "Tropical Island": {"is_land": True, "produced_mana": "GU", "oracle_text": ""},
        "Tundra": {"is_land": True, "produced_mana": "WU", "oracle_text": ""},
        "Volcanic Island": {"is_land": True, "produced_mana": "RU", "oracle_text": ""},
        "Polluted Delta": {
            "is_land": True,
            "produced_mana": "",
            "oracle_text": "{T}, Pay 1 life: Search your library for an Island or Swamp card.",
        },
        "Cavern of Souls": {
            "is_land": True,
            "produced_mana": "WUBRG",
            "oracle_text": "As Cavern of Souls enters the battlefield, choose a creature type.",
        },
        "City of Brass": {"is_land": True, "produced_mana": "WUBRG", "oracle_text": ""},
        "Edge of Autumn": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Lotus Petal": {"is_land": False, "produced_mana": "WUBRG", "oracle_text": ""},
        "Doomsday": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Veil of Summer": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Teferi, Time Raveler": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Hexing Squelcher": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Carpet of Flowers": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Witherbloom Charm": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Voice of Victory": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Brainstorm": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "The Fantasticar": {"is_land": False, "produced_mana": "", "oracle_text": ""},
        "Lightning Bolt": {"is_land": False, "produced_mana": "", "oracle_text": ""},
    }


def test_classifier_uses_actual_lands_and_package_cards_without_rainbow_false_positives():
    metadata = _metadata()

    assert classify_variant(
        {"Underground Sea": 4, "Polluted Delta": 4, "Cavern of Souls": 1,
         "Lotus Petal": 4, "Edge of Autumn": 1},
        {"Veil of Summer": 1}, metadata,
    ).variant_id == "dimir"
    assert classify_variant({"Bayou": 1, "Tropical Island": 1}, {"Veil of Summer": 1}, metadata).variant_id == "sultai_veil"
    assert classify_variant({"Tundra": 1}, {"Teferi, Time Raveler": 1}, metadata).variant_id == "esper_teferi"
    assert classify_variant({"Volcanic Island": 1}, {"Hexing Squelcher": 1}, metadata).variant_id == "grixis_squelcher"
    assert classify_variant({"Plains": 1, "Forest": 1}, {"Voice of Victory": 1}, metadata).variant_id == "four_color_white_green"
    assert classify_variant({"Plains": 1}, {}, metadata).variant_id == "white_no_teferi"
    assert classify_variant({"Forest": 1}, {}, metadata).variant_id == "green_no_veil"
    assert classify_variant({"Mountain": 1}, {}, metadata).variant_id == "red_no_squelcher"
    assert classify_variant({"City of Brass": 1}, {"Veil of Summer": 1}, metadata).variant_id == "dimir"


def test_classifier_excludes_unknown_card_facts_instead_of_guessing_dimir():
    result = classify_variant({"Underground Sea": 1, "Mystery Card": 1}, {}, _metadata())
    assert result.variant_id == "unclassifiable"
    assert result.status == "unclassifiable"
    assert result.missing_metadata == ("Mystery Card",)


def _fixture_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE tournaments (id VARCHAR, name VARCHAR, date VARCHAR, uri VARCHAR, format VARCHAR, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, result VARCHAR, archetype VARCHAR, variant VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, board VARCHAR, name VARCHAR, count INTEGER)")
    con.execute("CREATE TABLE rounds (tournament_id VARCHAR, match_idx INTEGER, player1 VARCHAR, player2 VARCHAR, result VARCHAR)")
    con.execute("CREATE TABLE standings (tournament_id VARCHAR, rank INTEGER, player VARCHAR, points INTEGER, wins INTEGER, losses INTEGER, draws INTEGER)")
    con.execute("CREATE TABLE cards (name VARCHAR, is_land BOOLEAN, produced_mana VARCHAR, oracle_text VARCHAR)")
    con.executemany("INSERT INTO cards VALUES (?, ?, ?, ?)", [
        (name, bool(facts["is_land"]), str(facts["produced_mana"]), str(facts["oracle_text"]))
        for name, facts in _metadata().items()
    ])

    def event(event_id: str, event_date: str, name: str = "Challenge") -> None:
        con.execute("INSERT INTO tournaments VALUES (?, ?, ?, ?, 'Legacy', 'fixture', 'online')", [event_id, name, event_date, f"https://fixture/{event_id}"])

    def deck(event_id: str, idx: int, player: str, archetype: str, main: dict[str, int], side: dict[str, int] | None = None, result: str = "4-0") -> None:
        con.execute("INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)", [event_id, idx, player, result, archetype])
        for board, cards in (("main", main), ("side", side or {})):
            for card, count in cards.items():
                con.execute("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [event_id, idx, board, card, count])

    def round_row(event_id: str, idx: int, p1: str, p2: str, result: str) -> None:
        con.execute("INSERT INTO rounds VALUES (?, ?, ?, ?, ?)", [event_id, idx, p1, p2, result])

    def standing(event_id: str, rank: int, player: str, wins: int, losses: int, draws: int = 0) -> None:
        con.execute("INSERT INTO standings VALUES (?, ?, ?, ?, ?, ?, ?)", [event_id, rank, player, wins * 3 + draws, wins, losses, draws])

    sultai = {"Island": 4, "Swamp": 2, "Bayou": 1, "Tropical Island": 1, "Doomsday": 4, "Brainstorm": 4}
    tes = {"Island": 4, "Brainstorm": 4}
    event("old", "2026-08-01")
    deck("old", 0, "OldPilot", "Doomsday", sultai, {"Veil of Summer": 1})
    deck("old", 1, "OldTES", "TES", tes)
    round_row("old", 0, "OldPilot", "OldTES", "2-0")

    event("e1", "2026-08-20")
    deck("e1", 0, "Doomer", "Doomsday", sultai, {"Veil of Summer": 1, "Carpet of Flowers": 2})
    deck("e1", 1, "TESPilot", "TES", tes)
    deck("e1", 2, "BannedOpp", "TES", {**tes, "The Fantasticar": 1})
    deck("e1", 3, "NoList", "TES", {})
    deck("e1", 4, "OtherDoom", "Doomsday", sultai, {"Veil of Summer": 1})
    round_row("e1", 0, "Doomer", "TESPilot", "2-0")
    round_row("e1", 1, "TESPilot", "Doomer", "2-1")
    round_row("e1", 2, "Doomer", "TESPilot", "2-1")
    round_row("e1", 3, "Doomer", "TESPilot", "2-0")
    round_row("e1", 3, "Doomer", "TESPilot", "2-0")  # duplicate physical row / match id
    round_row("e1", 4, "Doomer", "BannedOpp", "2-0")
    round_row("e1", 5, "Doomer", "NoList", "2-0")
    round_row("e1", 6, "Doomer", "OtherDoom", "2-0")
    standing("e1", 1, "Doomer", 3, 1)

    # Same list and same day, but a distinct event id: it remains an observation.
    event("e2", "2026-08-20", "Challenge 2")
    deck("e2", 0, "Doomer2", "Doomsday", sultai, {"Veil of Summer": 1})
    deck("e2", 1, "TESPilot2", "TES", tes)
    round_row("e2", 0, "TESPilot2", "Doomer2", "2-0")
    standing("e2", 1, "Doomer2", 2, 1)

    # League 5-0 is registration/standings evidence only; it has no rounds.
    event("league", "2026-08-22", "Legacy League 5-0")
    deck("league", 0, "LeagueDoom", "Doomsday", sultai, {"Veil of Summer": 1}, "5-0")
    standing("league", 1, "LeagueDoom", 5, 0)

    event("banned-subject", "2026-08-23")
    deck("banned-subject", 0, "BadDoom", "Doomsday", {**sultai, "The Fantasticar": 1}, {"Veil of Summer": 1})
    deck("banned-subject", 1, "TES3", "TES", tes)
    round_row("banned-subject", 0, "BadDoom", "TES3", "2-0")
    standing("banned-subject", 1, "BadDoom", 4, 0)

    event("banned-opponent", "2026-08-24")
    deck("banned-opponent", 0, "GoodDoom", "Doomsday", sultai, {"Veil of Summer": 1})
    deck("banned-opponent", 1, "Banned", "TES", {**tes, "The Fantasticar": 1})
    round_row("banned-opponent", 0, "GoodDoom", "Banned", "2-0")
    standing("banned-opponent", 1, "GoodDoom", 1, 2)

    event("ambiguous", "2026-08-25")
    deck("ambiguous", 0, "Ambig", "Doomsday", sultai, {"Veil of Summer": 1})
    deck("ambiguous", 1, "ambig", "Doomsday", sultai, {"Veil of Summer": 1})
    deck("ambiguous", 2, "TES4", "TES", tes)
    round_row("ambiguous", 0, "Ambig", "TES4", "2-0")
    standing("ambiguous", 1, "Ambig", 2, 0)

    event("nondoom", "2026-08-26")
    deck("nondoom", 0, "TES5", "TES", tes)
    deck("nondoom", 1, "TES6", "Control", tes)
    round_row("nondoom", 0, "TES5", "TES6", "2-0")
    return con


def _global_payload() -> dict[str, object]:
    return {
        "meta": {"deck_rankings": {"field": {
            "since": "2026-08-10", "until": "2026-09-04",
            "shares": {"TES": 0.4, "Doomsday": 0.2, "Conflict(Doomsday,TES)": 0.1, "Unknown": 0.3},
            "effective_counts": {"TES": 40, "Doomsday": 20, "Conflict(Doomsday,TES)": 10, "Unknown": 30},
        }}},
    }


def _row(report: dict[str, object], view: str, subject: str) -> dict[str, object]:
    rows = report["views"][view]["rows"]
    return next(row for row in rows if row["subject"] == subject)


def test_report_separates_standings_from_legal_physical_rounds_and_audits_exclusions():
    report = build_variant_report(_fixture_db(), _global_payload(), draws=40)
    sultai = _row(report, "all", "sultai_veil")
    current = _row(report, "current", "sultai_veil")
    assert sultai["standings"]["record"] == "6-4-0"
    assert sultai["standings"]["record_count"] == 3
    assert sultai["standings"]["decisive_win_rate"] == pytest.approx(0.6)
    assert sultai["decision"]["round_n"] == 6  # 1 old + 4 e1 + 1 e2, duplicate collapsed
    assert sultai["decision"]["raw_wins"] == 4
    assert sultai["decision"]["raw_losses"] == 2
    assert current["decision"]["round_n"] == 5
    assert current["standings"]["record"] == "6-4-0"
    assert _row(report, "all", "dimir")["decision"]["prior_only"] is True

    counts = report["views"]["all"]["round_audit"]["counts"]
    assert counts["duplicate_match_ids"] == 1
    assert counts["banned_subject"] >= 1
    assert counts["banned_opponent"] >= 1
    assert counts["doomsday_mirror"] >= 1
    assert counts["ambiguous_registration"] >= 1
    assert counts["missing_opponent_list"] >= 1
    assert counts["not_doomsday"] >= 1
    assert report["audit"]["banned_registrations"] >= 2
    assert report["audit"]["banned_doomsday_registrations"] == 1


def test_field_mass_keeps_unknown_and_conflict_and_is_deterministic():
    first = build_variant_report(_fixture_db(), _global_payload(), draws=32)
    second = build_variant_report(_fixture_db(), _global_payload(), draws=32)
    field = first["field"]
    assert field["removed_labels"] == ["Doomsday"]
    assert "Conflict(Doomsday,TES)" in field["shares"]
    assert "Unknown" in field["shares"]
    assert sum(field["shares"].values()) == pytest.approx(1.0)
    assert field["removed_mass"] == pytest.approx(0.2)
    assert field["counts"]["TES"] == pytest.approx(40)
    assert sum(field["counts"].values()) == pytest.approx(80)
    assert first == second


def test_template_json_is_escaped_and_atomic_writer_replaces_file(tmp_path: Path):
    payload = {"unsafe": "</script><script>alert('x')\u2028"}
    rendered = render_report(payload, template="<body>__DOOMSDAY_VARIANT_DATA__</body>")
    assert "</script>" not in rendered
    assert "\\u2028" in rendered
    output = tmp_path / "report.html"
    _atomic_write_text(output, rendered)
    assert output.read_text(encoding="utf-8") == rendered
    assert not list(tmp_path.glob(".report.html.*.tmp"))


def _copy_event(con, original, target, *, event_date='2026-08-20'):
    con.execute("INSERT INTO tournaments SELECT ?, name, ?, ?, format, source, provenance FROM tournaments WHERE id=?", [target, event_date, target, original])
    for table in ('decks', 'deck_cards', 'standings', 'rounds'):
        con.execute(f"INSERT INTO {table} SELECT ?, * EXCLUDE(tournament_id) FROM {table} WHERE tournament_id=?", [target, original])


def test_verified_whole_event_alias_is_counted_once_but_distinct_events_remain():
    con = _fixture_db()
    canonical = 'https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-2012345678'
    alias = 'https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-1812345678'
    distinct = 'https://www.mtgo.com/decklist/legacy-challenge-32-2026-08-2087654321'
    for target in (canonical, alias, distinct):
        _copy_event(con, 'e2', target)
    report = build_variant_report(con, _global_payload(), draws=20)
    row = _row(report, 'all', 'sultai_veil')
    assert report['audit']['event_aliases'] == {alias: canonical}
    assert row['decision']['round_n'] == 8  # baseline six + two genuinely distinct events
    assert row['standings']['record'] == '10-6-0'
    assert report['views']['all']['round_audit']['counts']['excluded_event_alias'] == 1
    # An inconsistent publication cannot establish exact duplication.
    con.execute('UPDATE standings SET wins=5 WHERE tournament_id=? AND rank=1', [alias])
    report = build_variant_report(con, _global_payload(), draws=20)
    assert report['audit']['event_aliases'] == {}
    assert _row(report, 'all', 'sultai_veil')['decision']['round_n'] == 9


def test_cutoff_is_exclusive_and_unseen_cells_keep_the_declared_weak_prior():
    con = _fixture_db()
    _copy_event(con, 'e2', 'future', event_date='2026-09-04')
    report = build_variant_report(con, _global_payload(), draws=20)
    row = _row(report, 'all', 'sultai_veil')
    assert row['decision']['round_n'] == 6
    cells = {c['opponent']: c for c in row['decision']['cells']}
    assert cells['TES']['mean'] == pytest.approx(5 / 8)
    assert cells['Unknown']['mean'] == .5
    assert [cells['Unknown']['ci_low'], cells['Unknown']['ci_high']] == pytest.approx([.025, .975])
    assert row['decision']['performance'] == pytest.approx(.5625)
    assert cells['TES']['date_max'] == '2026-08-20'


def test_failed_atomic_publication_preserves_previous_report(tmp_path, monkeypatch):
    output = tmp_path / 'report.html'
    output.write_text('previous')
    def fail_replace(self, target):
        raise OSError('publication failure')
    monkeypatch.setattr(Path, 'replace', fail_replace)
    with pytest.raises(OSError, match='publication failure'):
        _atomic_write_text(output, 'new')
    assert output.read_text() == 'previous'
    assert not list(tmp_path.glob('.report.html.*.tmp'))


def test_publisher_refuses_to_replace_its_database(tmp_path):
    from scripts.refresh_doomsday_variant_rankings import main
    database = tmp_path / 'input.duckdb'
    database.write_bytes(b'database sentinel')
    with pytest.raises(SystemExit):
        main(['--db', str(database), '--out', str(database)])
    assert database.read_bytes() == b'database sentinel'


@pytest.mark.parametrize('bad_share', [-.1, float('nan'), float('inf')])
def test_invalid_field_mass_is_rejected(bad_share):
    payload = _global_payload()
    payload['meta']['deck_rankings']['field']['shares']['Unknown'] = bad_share
    with pytest.raises(ValueError, match='finite and non-negative'):
        build_variant_report(_fixture_db(), payload, draws=10)


def test_missing_field_cutoff_cannot_silently_use_newer_database_dates():
    payload = _global_payload()
    del payload['meta']['deck_rankings']['field']['until']
    with pytest.raises(ValueError, match='exclusive until'):
        build_variant_report(_fixture_db(), payload, draws=10)
