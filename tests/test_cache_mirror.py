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
        stats = cache.ingest_cache(con, _build_cache(tmp_path))
        assert stats.loaded == 2
        assert stats.total == 2
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
            stats = cache.ingest_cache(con, tmp_path)
        assert stats.loaded == 2  # two good events load; the bad one is skipped, batch continues
        assert stats.bad == 1
        assert "skipping bad event" in caplog.text.lower()
        # the bad path never gets a ledger row, so the next run retries it
        assert con.execute(
            "SELECT count(*) FROM ingest_ledger WHERE path LIKE '%bad%'"
        ).fetchone()[0] == 0
        con.close()


class TestKeyedReload:
    """The core fix: an unchanged event on re-refresh must not wipe archetype/variant labels."""

    def _label_all(self, con) -> None:
        con.execute("UPDATE decks SET archetype = 'X', variant = 'Y'")

    def test_identical_second_ingest_is_a_full_skip(self, tmp_path):
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        first = cache.ingest_cache(con, cache_dir)
        assert first.loaded == first.total == 2
        self._label_all(con)

        second = cache.ingest_cache(con, cache_dir)

        assert second.unchanged == second.total == 2
        assert second.loaded == 0
        assert second.labels_dropped == 0
        assert second.variants_dropped == 0
        assert con.execute(
            "SELECT count(*) FROM decks WHERE archetype IS NOT NULL"
        ).fetchone()[0] == 2
        con.close()

    def test_modified_event_reloads_only_that_tournament(self, tmp_path):
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        cache.ingest_cache(con, cache_dir)
        self._label_all(con)

        # Rewrite the MTGO event with a different deck (changes its content hash).
        challenge_path = cache_dir / "Tournaments" / "MTGO" / "2026" / "05" / "24" / "challenge.json"
        modified = json.loads(challenge_path.read_text())
        modified["Decks"][0]["Mainboard"][0]["CardName"] = "Ponder"
        challenge_path.write_text(json.dumps(modified))

        stats = cache.ingest_cache(con, cache_dir)

        assert stats.changed == 1
        assert stats.unchanged == stats.total - 1
        assert stats.labels_dropped == 1  # the one previously-labeled deck on the reloaded event
        assert stats.variants_dropped == 1

        rows = con.execute(
            "SELECT t.uri, d.archetype, d.variant FROM decks d "
            "JOIN tournaments t ON t.id = d.tournament_id"
        ).fetchall()
        by_uri = {uri: (archetype, variant) for uri, archetype, variant in rows}
        assert by_uri[_CHALLENGE["Tournament"]["Uri"]] == (None, None)
        assert by_uri[_PAPER["Tournament"]["Uri"]] == ("X", "Y")
        con.close()

    def test_new_file_loads_without_disturbing_existing_labels(self, tmp_path):
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        cache.ingest_cache(con, cache_dir)
        self._label_all(con)

        third = {
            "Tournament": {"Name": "Legacy Trial", "Date": "2026-05-25",
                           "Uri": "https://www.mtgo.com/decklist/legacy-trial-2026-05-25", "Formats": "Legacy"},
            "Decks": [{"Player": "z", "Result": "1st", "Mainboard": [{"Count": 4, "CardName": "Daze"}], "Sideboard": []}],
            "Rounds": [], "Standings": [],
        }
        (cache_dir / "Tournaments" / "MTGO" / "2026" / "05" / "24" / "trial.json").write_text(json.dumps(third))

        stats = cache.ingest_cache(con, cache_dir)

        assert stats.new == 1
        assert stats.labels_dropped == 0
        assert stats.variants_dropped == 0
        assert con.execute(
            "SELECT count(*) FROM decks WHERE archetype IS NOT NULL"
        ).fetchone()[0] == 2
        con.close()

    def test_seed_path_when_ledger_is_absent_but_data_exists(self, tmp_path):
        """Simulates a pre-feature DB: tournaments already loaded, ledger never populated."""
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        cache.ingest_cache(con, cache_dir)
        self._label_all(con)
        con.execute("DELETE FROM ingest_ledger")

        stats = cache.ingest_cache(con, cache_dir)

        assert stats.seeded == stats.total == 2
        assert stats.loaded == 0
        assert stats.labels_dropped == 0
        assert con.execute(
            "SELECT count(*) FROM decks WHERE archetype IS NOT NULL"
        ).fetchone()[0] == 2
        assert con.execute("SELECT count(*) FROM ingest_ledger").fetchone()[0] == 2
        con.close()

    def test_seed_path_verifies_content_and_reloads_a_changed_file(self, tmp_path):
        """A ledger-less file whose content DIVERGED from the DB must reload, never be blessed.

        Codex review finding (2026-07-23): seeding on tid-existence alone would record the NEW
        file's hash while the DB kept the OLD rows — every later refresh would then hash-match
        and skip it, so the new content would never load.
        """
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        cache.ingest_cache(con, cache_dir)
        self._label_all(con)
        con.execute("DELETE FROM ingest_ledger")  # simulate a pre-feature DB

        # The file changes AFTER its pre-ledger ingest (same Uri -> same tournament_id).
        challenge_path = cache_dir / "Tournaments" / "MTGO" / "2026" / "05" / "24" / "challenge.json"
        modified = json.loads(challenge_path.read_text())
        modified["Decks"][0]["Mainboard"][0]["CardName"] = "Ponder"
        challenge_path.write_text(json.dumps(modified))

        stats = cache.ingest_cache(con, cache_dir)

        assert stats.changed == 1  # the diverged file reloads
        assert stats.seeded == stats.total - 1  # the untouched file still seeds
        # The DB now holds the NEW content, and the reloaded event's labels are honestly reset.
        cards = {r[0] for r in con.execute(
            "SELECT dc.name FROM deck_cards dc JOIN tournaments t ON t.id = dc.tournament_id "
            "WHERE t.uri = ?", [_CHALLENGE["Tournament"]["Uri"]]
        ).fetchall()}
        assert cards == {"Ponder"}
        assert stats.labels_dropped == 1
        # A second refresh now hash-matches and preserves everything.
        second = cache.ingest_cache(con, cache_dir)
        assert second.unchanged == second.total
        con.close()

    def test_full_reload_wipes_labels_and_reloads_everything(self, tmp_path):
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        cache.ingest_cache(con, cache_dir)
        self._label_all(con)

        stats = cache.ingest_cache(con, cache_dir, full=True)

        assert stats.loaded == stats.total == 2
        assert stats.unchanged == 0
        assert stats.labels_dropped > 0
        assert con.execute(
            "SELECT count(*) FROM decks WHERE archetype IS NOT NULL"
        ).fetchone()[0] == 0
        con.close()

    def test_failed_reload_retries_next_run(self, tmp_path):
        """A previously-ingested event that becomes unparseable is skipped, not un-ledgered."""
        con = store.connect(":memory:")
        cache_dir = _build_cache(tmp_path)
        cache.ingest_cache(con, cache_dir)

        challenge_path = cache_dir / "Tournaments" / "MTGO" / "2026" / "05" / "24" / "challenge.json"
        old_row = con.execute(
            "SELECT content_hash FROM ingest_ledger WHERE path LIKE '%challenge.json'"
        ).fetchone()
        assert old_row is not None
        old_hash = old_row[0]

        # Valid JSON, still Formats=Legacy (discovery keeps it), but a malformed Standing makes
        # parse_cache_item raise — same shape as TestIngestResilience's bad event.
        corrupted = json.loads(challenge_path.read_text())
        corrupted["Standings"] = [{"Rank": "not-an-int", "Player": "a"}]
        challenge_path.write_text(json.dumps(corrupted))

        stats = cache.ingest_cache(con, cache_dir)

        assert stats.bad == 1
        row = con.execute(
            "SELECT content_hash FROM ingest_ledger WHERE path LIKE '%challenge.json'"
        ).fetchone()
        assert row is not None
        assert row[0] == old_hash  # the OLD (pre-corruption) ledger row survives untouched
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
