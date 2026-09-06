from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from legacy_engine.analytics.players.diagnostic import (
    PilotRegistration,
    PlayerDiagnosticProtocol,
    measure_pilot_stickiness,
    measure_player_accessibility,
    scoped_player_key,
)


@dataclass(frozen=True)
class Match:
    event_id: str
    provenance: str
    subject: str
    opponent: str
    subject_player_key: str | None
    opponent_player_key: str | None
    exclusion_reason: str | None = None


def _protocol(**updates) -> PlayerDiagnosticProtocol:
    values = {
        "protocol_id": "player-test", "created_at": "2026-01-01T00:00:00Z",
        "benchmark_protocol_hash": "benchmark", "min_repeat_players": 1,
        "min_familiarity_pairs": 1, "privacy_min_group": 1,
    }
    values.update(updates)
    return PlayerDiagnosticProtocol(**values)


def test_scoped_identity_is_provenance_local_unless_curated():
    online = scoped_player_key(" Same Handle ", "online", {})
    paper = scoped_player_key("same handle", "paper", {})
    assert online == ("handle:online:same handle", "provenance-local-handle")
    assert paper == ("handle:paper:same handle", "provenance-local-handle")
    assert online != paper
    aliases = {"same handle": "curated-person"}
    assert scoped_player_key("same handle", "online", aliases) == (
        "alias:curated-person", "curated-alias",
    )
    assert scoped_player_key("same handle", "paper", aliases)[0] == "alias:curated-person"


def test_repeat_and_familiarity_gates_are_independent():
    matches = []
    for index in range(30):
        matches.append(Match(
            event_id=f"e{index % 3}", provenance="online", subject="A", opponent="B",
            subject_player_key="repeat", opponent_player_key=None,
        ))
    registrations = tuple(PilotRegistration(
        event_id=f"e{index}", event_date=f"2025-12-0{index + 1}", provenance="online",
        parent="A", configuration="A::one", player_key="repeat",
        identity_basis="provenance-local-handle", exclusion_reason=None,
    ) for index in range(3))
    report = measure_player_accessibility(registrations, tuple(matches), _protocol())
    online = next(item for item in report if item.provenance == "online")
    assert online.repeat_players == 1
    assert online.familiarity_pairs == 1

    one_event = tuple(match.__class__(
        event_id="one", provenance=match.provenance, subject=match.subject,
        opponent=match.opponent, subject_player_key=match.subject_player_key,
        opponent_player_key=match.opponent_player_key,
    ) for match in matches)
    assert next(
        item for item in measure_player_accessibility(registrations, one_event, _protocol())
        if item.provenance == "online"
    ).repeat_players is None


def test_stickiness_is_deterministic_aggregate_and_privacy_suppressed():
    registrations = []
    for configuration in ("A::one", "A::two"):
        for player in range(10):
            for event in range(2):
                registrations.append(PilotRegistration(
                    event_id=f"{configuration}:{event}", event_date="2025-12-01",
                    provenance="online", parent="A", configuration=configuration,
                    player_key=f"p{player}", identity_basis="provenance-local-handle",
                    exclusion_reason=None,
                ))
    protocol = _protocol()
    first = measure_pilot_stickiness(tuple(registrations), protocol)
    assert first == measure_pilot_stickiness(tuple(registrations), protocol)
    assert first[0].shared_identities == 10
    assert first[0].jaccard == 1.0
    assert first[0].bootstrap_ci is not None
    assert "verdict" not in first[0].model_dump()

    thin = tuple(row for row in registrations if row.player_key in {"p0", "p1", "p2"})
    suppressed = measure_pilot_stickiness(thin, protocol)[0]
    assert suppressed.shared_identities is None
    assert suppressed.identities_a is None
    assert suppressed.identities_b is None
    assert suppressed.repeat_identities is None
    assert suppressed.reason == "configuration identity support below display floor"


def test_stickiness_event_bootstrap_preserves_replacement_multiplicity(monkeypatch):
    registrations = tuple(PilotRegistration(
        event_id=event, event_date="2025-12-01", provenance="online", parent="A",
        configuration=configuration, player_key="shared",
        identity_basis="provenance-local-handle", exclusion_reason=None,
    ) for configuration in ("A::one", "A::two") for event in ("e0", "e1"))

    class DuplicateFirstEvent:
        def choice(self, values, size, replace):
            assert replace is True
            return np.asarray([values[0]] * size)

    monkeypatch.setattr(np.random, "default_rng", lambda _seed: DuplicateFirstEvent())
    result = measure_pilot_stickiness(tuple(registrations), _protocol(
        stickiness_min_identities_per_configuration=1,
        stickiness_min_repeat_identities=1,
    ))[0]
    assert result.bootstrap_ci == (1.0, 1.0)


def test_accessibility_counts_ambiguous_sides_and_recomputes_support_by_venue():
    matches = tuple(
        Match(
            event_id=f"online-{index % 3}", provenance="online", subject="A", opponent="B",
            subject_player_key="online-repeat", opponent_player_key=None,
            exclusion_reason="ambiguous-player" if index == 0 else None,
        ) for index in range(31)
    ) + tuple(
        Match(
            event_id=f"paper-{index % 3}", provenance="paper", subject="A", opponent="B",
            subject_player_key="paper-thin", opponent_player_key=None,
        ) for index in range(2)
    )
    registrations = tuple(PilotRegistration(
        event_id=row.event_id, event_date="2025-12-01", provenance=row.provenance,
        parent="A", configuration="A::one", player_key=row.subject_player_key,
        identity_basis="provenance-local-handle", exclusion_reason=None,
    ) for row in matches)
    report = measure_player_accessibility(registrations, matches, _protocol())
    online = next(item for item in report if item.provenance == "online")
    paper = next(item for item in report if item.provenance == "paper")
    assert online.match_sides == 62
    assert online.unambiguous_match_rate == 0.5
    assert online.repeat_players == 1
    assert paper.repeat_players is None
