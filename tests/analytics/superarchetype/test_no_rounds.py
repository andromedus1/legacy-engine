"""The architectural guarantee: the superarchetype taxonomy never reads match outcomes.

Coverage of the matchup matrix is monotone in cluster coarseness, so any pressure to "get more
cells" pushes the dendrogram cut upward — and tuning that cut against the same match data the
pooled cells are drawn from is the selective-inference trap the brief warns about. The defence is
architectural rather than procedural: the clustering package cannot reach `rounds` at all.

Two independent proofs:

1. A **source tripwire** over the package's executable source (comments and docstrings stripped by
   `tokenize`, so the prose above and the design notes in the modules do not trip it).
2. A **runtime SQL spy** — a proxy connection recording every statement text — driven by a real
   end-to-end `run_superarchetypes` against a tmp DuckDB whose `rounds` table is populated. If the
   pipeline ever grew an outcome read, the recorded statements would name it.

The spy is the load-bearing one: the tripwire can be worked around by a rename, the spy cannot.
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import duckdb
import pytest

from legacy_engine.analytics.superarchetype import cluster as cluster_module
from legacy_engine.analytics.superarchetype import registry as registry_module
from legacy_engine.analytics.superarchetype.registry import run_superarchetypes

_FORBIDDEN_TOKENS = ("rounds", "match_results", "wins", "losses", "winrate")
_FORBIDDEN_SQL = ("rounds", "match_results")


def _skipped_token_types() -> frozenset[int]:
    """Comment/string token types, including the 3.12+ f-string parts.

    Python 3.12 split f-strings out of ``STRING`` into ``FSTRING_START``/``FSTRING_MIDDLE``/
    ``FSTRING_END``; without those the literal text of every f-string leaks into the scan and the
    tripwire fires on ordinary prose.
    """
    types = {tokenize.COMMENT, tokenize.STRING}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        token_type = getattr(tokenize, name, None)
        if token_type is not None:
            types.add(token_type)
    return frozenset(types)


_SKIPPED = _skipped_token_types()


def _executable_source(path: Path) -> str:
    """Module source with comments and string literals (f-strings included) removed."""
    kept: list[str] = []
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type in _SKIPPED:
                continue
            kept.append(token.string)
    return " ".join(kept)


class _RecordingConnection:
    """Proxy that records every statement text before delegating to the real connection."""

    def __init__(self, con):
        self._con = con
        self.statements: list[str] = []

    def execute(self, sql, *args, **kwargs):
        self.statements.append(sql)
        return self._con.execute(sql, *args, **kwargs)

    def executemany(self, sql, *args, **kwargs):
        self.statements.append(sql)
        return self._con.executemany(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._con, name)


def _build_corpus_with_rounds(tmp_path) -> str:
    """A tmp DuckDB carrying decks, deck_cards, tournaments AND a populated `rounds` table.

    The outcome table is deliberately present and non-empty: a spy over a corpus with no `rounds`
    at all would prove nothing.
    """
    db_path = str(tmp_path / "no_rounds.duckdb")
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE tournaments (id VARCHAR, name VARCHAR, date VARCHAR, "
                "uri VARCHAR, format VARCHAR, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, "
                "result VARCHAR, archetype VARCHAR, variant VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, "
                "board VARCHAR, name VARCHAR, count INTEGER)")
    con.execute("CREATE TABLE rounds (tournament_id VARCHAR, round_name VARCHAR, "
                "player1 VARCHAR, player2 VARCHAR, wins INTEGER, losses INTEGER)")

    con.execute(
        "INSERT INTO tournaments VALUES ('t1', 'Test', '2026-06-01', '', 'Legacy', 'x', 'online')"
    )
    staples = ["Brainstorm", "Force of Will", "Ponder", "Wasteland"]
    families = {
        "Combo A": ["Show and Tell", "Omniscience", "Emrakul", "Atraxa", "Ancient Tomb", "Petal A"],
        "Combo B": ["Show and Tell", "Omniscience", "Emrakul", "Atraxa", "Ancient Tomb", "Petal B"],
        "Fair A": ["Swords", "Stoneforge", "Batterskull", "Plains", "Thalia", "Sword A"],
        "Fair B": ["Swords", "Stoneforge", "Batterskull", "Plains", "Thalia", "Sword B"],
    }
    deck_idx = 0
    for archetype, package in families.items():
        for _ in range(40):
            con.execute(
                "INSERT INTO decks VALUES ('t1', ?, ?, '5-0', ?, NULL)",
                [deck_idx, f"p{deck_idx}", archetype],
            )
            for card in staples + package:
                con.execute(
                    "INSERT INTO deck_cards VALUES ('t1', ?, 'main', ?, 4)", [deck_idx, card]
                )
            deck_idx += 1

    for i in range(50):
        con.execute("INSERT INTO rounds VALUES ('t1', 'R1', ?, ?, 2, 1)", [f"p{i}", f"p{i + 1}"])
    con.close()
    return db_path


class TestSourceTripwire:
    @pytest.mark.parametrize("module", [cluster_module, registry_module])
    def test_no_outcome_token_in_executable_source(self, module):
        source = _executable_source(Path(module.__file__))
        offenders = [token for token in _FORBIDDEN_TOKENS if token in source]
        assert offenders == [], (
            f"{Path(module.__file__).name} references match-outcome token(s) {offenders} in "
            "executable source — the superarchetype taxonomy must never read match results"
        )

    def test_the_tripwire_would_actually_fire(self, tmp_path):
        planted = tmp_path / "planted.py"
        planted.write_text('# rounds in a comment is fine\nx = "SELECT * FROM rounds"\ny = rounds\n')
        source = _executable_source(planted)
        assert "rounds" in source

    def test_the_tripwire_ignores_comments_docstrings_and_fstrings(self, tmp_path):
        clean = tmp_path / "clean.py"
        clean.write_text(
            '"""Never reads rounds."""\n'
            "# also never rounds\n"
            "n = 1\n"
            'msg = f"this prose mentions rounds and wins but is not a read {n}"\n'
        )
        source = _executable_source(clean)
        assert "rounds" not in source
        assert "wins" not in source


class TestRuntimeSqlSpy:
    def test_the_full_pass_never_names_an_outcome_table(self, tmp_path):
        db_path = _build_corpus_with_rounds(tmp_path)
        con = duckdb.connect(db_path)
        spy = _RecordingConnection(con)
        try:
            result = run_superarchetypes(
                spy, since="2026-01-01", until="2026-12-31", seed=0, n_boot=10,
                curated={}, derived_path=tmp_path / "derived.json", write=True,
            )
        finally:
            con.close()

        assert spy.statements, "the spy recorded nothing — the pass did not run"
        joined = "\n".join(spy.statements).lower()
        for forbidden in _FORBIDDEN_SQL:
            assert forbidden not in joined, (
                f"a statement referenced {forbidden!r}:\n{joined}"
            )
        # And the pass really did produce a taxonomy over this corpus.
        assert result.n_definers == 4
        assert result.registry.clusters

    def test_the_spy_would_actually_fire(self, tmp_path):
        db_path = _build_corpus_with_rounds(tmp_path)
        con = duckdb.connect(db_path)
        spy = _RecordingConnection(con)
        try:
            spy.execute("SELECT count(*) FROM rounds")
        finally:
            con.close()
        assert any("rounds" in s.lower() for s in spy.statements)


class TestTypeStructural:
    def test_the_core_input_type_carries_no_outcome_field(self):
        fields = set(cluster_module.ArchetypeDeck.__dataclass_fields__)
        assert fields == {"archetype", "key", "cards"}

    def test_no_type_in_the_package_exposes_an_outcome_field(self):
        outcome_names = {"wins", "losses", "result", "winrate", "matches", "rounds"}
        for module in (cluster_module, registry_module):
            for name in dir(module):
                obj = getattr(module, name)
                fields = getattr(obj, "__dataclass_fields__", None)
                if fields is None:
                    continue
                assert not (set(fields) & outcome_names), (
                    f"{module.__name__}.{name} exposes an outcome field"
                )
