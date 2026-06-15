"""Cache mirror — git clone/pull branch, Legacy-event discovery, ingest into DuckDB. No network/git."""

from __future__ import annotations

import json

from legacy_engine.ingestion import cache, store

_CHALLENGE = {
    "Tournament": {"Name": "Legacy Challenge", "Date": "2026-05-24",
                   "Uri": "https://www.mtgo.com/decklist/legacy-challenge-2026-05-24", "Formats": "Legacy"},
    "Decks": [{"Player": "a", "Result": "1st", "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}], "Sideboard": []}],
    "Rounds": [{"Player1": "a", "Player2": "b", "Result": "2-1"}],
    "Standings": [{"Rank": 1, "Player": "a", "Points": 18}],
}
_PAPER = {
    "Tournament": {"Name": "Eternal Weekend", "Date": "2026-05-24",
                   "Uri": "https://melee.gg/Tournament/View/1", "Formats": "Legacy"},
    "Decks": [{"Player": "c", "Result": "Top 8", "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []}],
    "Rounds": [], "Standings": [],
}
_STANDARD = {"Tournament": {"Name": "Standard Challenge", "Formats": "Standard"}, "Decks": [], "Rounds": [], "Standings": []}


def _build_cache(tmp_path):
    root = tmp_path / "Tournaments"
    (root / "MTGO" / "2026" / "05" / "24").mkdir(parents=True)
    (root / "MTGmelee" / "2026" / "05" / "24").mkdir(parents=True)
    (root / "MTGO" / "2026" / "05" / "24" / "challenge.json").write_text(json.dumps(_CHALLENGE))
    (root / "MTGO" / "2026" / "05" / "24" / "standard.json").write_text(json.dumps(_STANDARD))
    (root / "MTGmelee" / "2026" / "05" / "24" / "ew.json").write_text(json.dumps(_PAPER))
    return tmp_path


class TestDiscoverLegacyEvents:
    def test_finds_legacy_skips_others(self, tmp_path):
        events = cache.discover_legacy_events(_build_cache(tmp_path))
        assert {s for _p, s in events} == {"MTGO", "MTGmelee"}  # 2 Legacy events; Standard skipped
        assert len(events) == 2

    def test_empty_when_no_tournaments_dir(self, tmp_path):
        assert cache.discover_legacy_events(tmp_path) == []


class TestIngestCache:
    def test_ingests_all_legacy_events(self, tmp_path):
        con = store.connect(":memory:")
        n = cache.ingest_cache(con, _build_cache(tmp_path))
        assert n == 2
        assert con.execute("SELECT count(*) FROM tournaments").fetchone()[0] == 2
        # the paper event is tagged paper, the MTGO one online
        provs = {r[0] for r in con.execute("SELECT provenance FROM tournaments").fetchall()}
        assert provs == {"online", "paper"}
        con.close()


class TestIngestResilience:
    """Resilience NFR: one bad event is logged and skipped; the batch continues."""

    def test_one_bad_event_does_not_abort_the_batch(self, tmp_path, caplog):
        root = tmp_path / "Tournaments"
        (root / "MTGO" / "2026" / "05" / "24").mkdir(parents=True)
        (root / "MTGmelee" / "2026" / "05" / "24").mkdir(parents=True)
        (root / "MTGO" / "2026" / "05" / "24" / "good1.json").write_text(json.dumps(_CHALLENGE))
        # Valid JSON, Formats=Legacy (so discovery includes it), but a malformed Standing makes
        # parse_cache_item raise at the EVENT level (standings aren't per-row tolerated).
        bad = {
            "Tournament": {"Name": "Bad", "Date": "2026-05-24", "Formats": "Legacy"},
            "Decks": [{"Player": "x", "Mainboard": [{"Count": 4, "CardName": "Foo"}]}],
            "Rounds": [], "Standings": [{"Rank": "not-an-int", "Player": "x"}],
        }
        (root / "MTGO" / "2026" / "05" / "24" / "bad.json").write_text(json.dumps(bad))
        (root / "MTGmelee" / "2026" / "05" / "24" / "good2.json").write_text(json.dumps(_PAPER))

        con = store.connect(":memory:")
        with caplog.at_level("WARNING"):
            n = cache.ingest_cache(con, tmp_path)
        assert n == 2  # two good events load; the bad one is skipped, batch continues
        assert "skipping bad event" in caplog.text.lower()
        con.close()


class TestMirrorCache:
    def test_clones_when_absent(self, tmp_path):
        calls = []
        cache.mirror_cache(repo="REPO", dest=tmp_path / "mirror", runner=lambda cmd, **kw: calls.append(cmd))
        assert calls and calls[0][:2] == ["git", "clone"]

    def test_pulls_when_present(self, tmp_path):
        dest = tmp_path / "mirror"
        (dest / ".git").mkdir(parents=True)
        calls = []
        cache.mirror_cache(dest=dest, runner=lambda cmd, **kw: calls.append(cmd))
        assert "pull" in calls[0]
