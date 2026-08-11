"""Tests for analytics.eras.consume — the era-horizon adapter (Unit 1, epic-stable-era-windows-
consumption-adapter).

House style: hermetic in-memory DuckDB (`:memory:`), hand-built EntityEras/EraBoundary fixtures
written via `write_entity_eras` (mirrors `tests/analytics/eras/test_store.py`'s `make_boundary`/
`make_eras` factory idiom), real corpus decks loaded via `ingestion.store`/`parse_cache_item` for
`resolve_field_era`'s deck-count queries. Deterministic; never touches the default DB.
"""

from __future__ import annotations

from legacy_engine.analytics.eras.attribution import Attribution
from legacy_engine.analytics.eras.consume import (
    EraHorizon,
    clamp_pair_window,
    era_horizons,
    resolve_field_era,
)
from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary
from legacy_engine.analytics.eras.store import write_entity_eras
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from tests.conftest import in_current_regime


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _write(con, eras: dict, attributions: dict | None = None, alarms: dict | None = None, *, parent: dict | None = None):
    write_entity_eras(
        con, eras, attributions or {}, alarms or {},
        run_meta={
            "provenance": None, "alpha": 0.05, "run_at": "2026-07-11T00:00:00+00:00",
            "post_boundary_decks": {}, "parent": parent or {e: e for e in eras},
        },
    )


def _deck(player: str, main: list[str]) -> dict:
    return {"Player": player, "Result": "1st Place",
            "Mainboard": [{"Count": 1, "CardName": c} for c in main], "Sideboard": []}


def _tournament(name: str, dt: str, decks: list[dict]) -> dict:
    return {
        "Tournament": {"Name": name, "Date": dt, "Uri": f"https://example.test/{name}",
                       "Formats": "Legacy"},
        "Decks": decks, "Rounds": [], "Standings": [],
    }


def _load_decks(con, *, archetype: str, n: int, dt: str, name_prefix: str) -> None:
    decks = [_deck(f"{name_prefix}{i}", []) for i in range(n)]
    tid = store.load_tournament(con, parse_cache_item(_tournament(f"{name_prefix}-{dt}", dt, decks), "MTGO"))
    con.execute("UPDATE decks SET archetype = ? WHERE tournament_id = ?", [archetype, tid])


# ---------------------------------------------------------------------------
# Pair windows
# ---------------------------------------------------------------------------


class TestPairWindow:
    def test_later_entity_horizon_clamps_requested_bound(self):
        window = clamp_pair_window(
            "Subject", "Opponent", requested_since="2026-01-01",
            subject_since="2026-03-01", opponent_since="2026-04-01",
        )
        assert window.effective_since == "2026-04-01"
        assert window.clamped is True
        assert "opponent horizon (Opponent)" in window.reason

    def test_later_requested_bound_never_widens(self):
        window = clamp_pair_window(
            "Subject", "Opponent", requested_since="2026-05-01",
            subject_since="2026-03-01", opponent_since="2026-04-01",
        )
        assert window.effective_since == "2026-05-01"
        assert window.clamped is False
        assert "requested lower bound" in window.reason

    def test_no_bounds_names_full_corpus(self):
        window = clamp_pair_window(
            "Subject", "Opponent", subject_since=None, opponent_since=None,
        )
        assert window.effective_since is None
        assert window.reason == "full corpus: no requested or entity horizon"


# ---------------------------------------------------------------------------
# era_horizons — resolution order
# ---------------------------------------------------------------------------


class TestEraHorizonsResolutionOrder:
    def test_exact_entry_present_with_date(self):
        con = store.connect(":memory:")
        boundary = EraBoundary(date="2026-04-20", signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {"Doomsday": EntityEras(entity="Doomsday", stable_since="2026-04-20", boundaries=(boundary,), inherited_from_parent=False)}
        attributions = {("Doomsday", "2026-04-20"): Attribution(kind="release", card="Flow State", detail="release: Flow State adoption (2026-04-20)")}
        _write(con, eras, attributions)

        horizons, audit = era_horizons(con, ["Doomsday"])
        assert audit == ()
        h = horizons["Doomsday"]
        assert h == EraHorizon(
            since="2026-04-20", source="era",
            trigger="release: Flow State adoption (2026-04-20)", alarm=None,
            attribution_kind="release",
        )
        con.close()

    def test_exact_entry_present_with_none_is_full_history(self):
        con = store.connect(":memory:")
        eras = {"Control": EntityEras(entity="Control", stable_since=None, boundaries=(), inherited_from_parent=False)}
        _write(con, eras)

        horizons, audit = era_horizons(con, ["Control"])
        assert audit == ()
        assert horizons["Control"] == EraHorizon(since=None, source="era", trigger=None, alarm=None)
        con.close()

    def test_camp_falls_back_to_parent_entry(self):
        con = store.connect(":memory:")
        boundary = EraBoundary(date="2026-04-20", signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {"Doomsday": EntityEras(entity="Doomsday", stable_since="2026-04-20", boundaries=(boundary,), inherited_from_parent=False)}
        attributions = {("Doomsday", "2026-04-20"): Attribution(kind="release", card="Flow State", detail="release: Flow State adoption (2026-04-20)")}
        _write(con, eras, attributions)

        # "Doomsday [Turbo]" has no row of its own -> falls back to "Doomsday"'s row.
        horizons, _audit = era_horizons(con, ["Doomsday [Turbo]"], split_variant="Doomsday")
        h = horizons["Doomsday [Turbo]"]
        assert h.source == "era-parent"
        assert h.since == "2026-04-20"
        assert h.trigger == "release: Flow State adoption (2026-04-20)"
        con.close()

    def test_camp_own_entry_wins_over_parent(self):
        con = store.connect(":memory:")
        camp_boundary = EraBoundary(date="2026-05-01", signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {
            "Doomsday": EntityEras(entity="Doomsday", stable_since="2026-04-20", boundaries=(), inherited_from_parent=False),
            "Doomsday [Turbo]": EntityEras(entity="Doomsday [Turbo]", stable_since="2026-05-01", boundaries=(camp_boundary,), inherited_from_parent=False),
        }
        _write(con, eras, parent={"Doomsday": "Doomsday", "Doomsday [Turbo]": "Doomsday"})

        horizons, _audit = era_horizons(con, ["Doomsday [Turbo]"], split_variant="Doomsday")
        h = horizons["Doomsday [Turbo]"]
        assert h.source == "era"
        assert h.since == "2026-05-01"
        con.close()

    def test_absent_entirely_falls_back_to_ban_only(self):
        con = store.connect(":memory:")
        # Entity_eras table exists (from a real run) but does not cover "Unseen".
        eras = {"Other": EntityEras(entity="Other", stable_since=None, boundaries=(), inherited_from_parent=False)}
        _write(con, eras)
        _load_decks(con, archetype="Unseen", n=5, dt="2025-06-01", name_prefix="p")

        horizons, audit = era_horizons(con, ["Unseen"])
        assert audit == ()  # table is NOT empty overall — only this entity is uncovered
        assert horizons["Unseen"].source == "ban-only"
        assert horizons["Unseen"].since is None  # never ran a banned card
        con.close()

    def test_no_era_data_at_all_degrades_every_label(self):
        con = store.connect(":memory:")
        _load_decks(con, archetype="Anything", n=5, dt="2025-06-01", name_prefix="p")

        horizons, audit = era_horizons(con, ["Anything"])
        assert audit == ("// eras: no era data — ban-only horizons; run `eras run`",)
        assert horizons["Anything"].source == "ban-only"
        con.close()

    def test_alarm_surfaces_only_when_fired(self):
        from legacy_engine.analytics.eras.run import AlarmFlag

        con = store.connect(":memory:")
        eras = {"Tron": EntityEras(entity="Tron", stable_since=None, boundaries=(), inherited_from_parent=False)}
        alarms = {"Tron": AlarmFlag(entity="Tron", p_change=0.97, note="unattributed disturbance (p_change=0.970) — possible unregistered B&R change")}
        _write(con, eras, alarms=alarms)

        horizons, _audit = era_horizons(con, ["Tron"])
        assert horizons["Tron"].alarm == "unattributed disturbance (p_change=0.970) — possible unregistered B&R change"
        con.close()

    def test_ban_only_still_derives_a_real_affected_horizon(self):
        """The ban-only fallback branch must still resolve a genuinely affected archetype's date
        (not just None) — proves era_horizons' fallback is a real archetype_valid_since call."""
        con = store.connect(":memory:")
        # Entomb banned 2025-11-10; 5/5 decks run it pre-ban -> affected.
        for i in range(5):
            decks = [_deck(f"r{i}", ["Entomb", "Reanimate"])]
            tid = store.load_tournament(
                con, parse_cache_item(_tournament(f"t{i}", "2025-06-01", decks), "MTGO"),
            )
            con.execute("UPDATE decks SET archetype = 'Reanimator' WHERE tournament_id = ?", [tid])

        horizons, audit = era_horizons(con, ["Reanimator"])
        assert audit == ("// eras: no era data — ban-only horizons; run `eras run`",)
        assert horizons["Reanimator"] == EraHorizon(
            since="2025-11-10", source="ban-only",
            trigger="ban: valid_since 2025-11-10", alarm=None,
        )
        con.close()


class TestEraHorizonsCampParentMap:
    """``camp_parent`` (feature-multi-split-matrix Unit 3): explicit camp -> parent resolution for
    the multi-split matrix, where a prefix rule cannot disambiguate many parents at once."""

    def _painter_pair_con(self):
        """``Painter`` has an era row; ``Blue Painter`` does not — the prefix trap."""
        con = store.connect(":memory:")
        boundary = EraBoundary(date="2026-04-20", signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {"Painter": EntityEras(entity="Painter", stable_since="2026-04-20", boundaries=(boundary,), inherited_from_parent=False)}
        attributions = {("Painter", "2026-04-20"): Attribution(kind="ban", card="Grindstone", detail="ban: Grindstone")}
        _write(con, eras, attributions)
        # The ban-only branch queries `decks`; give it a corpus so the fallback is a real lookup.
        _load_decks(con, archetype="Blue Painter", n=5, dt="2026-06-01", name_prefix="bp")
        return con

    def test_camp_with_no_row_inherits_its_mapped_parent(self):
        con = self._painter_pair_con()
        camp_parent = {"Painter [Welder]": "Painter", "Blue Painter [Welder]": "Blue Painter"}
        horizons, _audit = era_horizons(
            con, ["Painter [Welder]", "Blue Painter [Welder]"], camp_parent=camp_parent,
        )
        assert horizons["Painter [Welder]"].source == "era-parent"
        assert horizons["Painter [Welder]"].since == "2026-04-20"
        # "Blue Painter [Welder]" must NOT inherit "Painter"'s row via a prefix match.
        assert horizons["Blue Painter [Welder]"].source == "ban-only"
        assert horizons["Blue Painter [Welder]"].since is None
        con.close()

    def test_prefix_parsing_would_have_gotten_it_wrong(self):
        """The same call WITHOUT the map, using the single-split prefix rule, mis-resolves
        ``Blue Painter``'s camp — this is exactly why the explicit map exists."""
        con = self._painter_pair_con()
        horizons, _audit = era_horizons(
            con, ["Blue Painter [Welder]"], split_variant="Painter",
        )
        # Prefix rule can't see "Blue Painter" as the parent, so it falls to ban-only on the
        # WRONG base label — the map above resolves the parent by construction instead.
        assert horizons["Blue Painter [Welder]"].source == "ban-only"
        con.close()

    def test_camp_own_row_still_wins_over_the_mapped_parent(self):
        con = store.connect(":memory:")
        eras = {
            "Painter": EntityEras(entity="Painter", stable_since="2026-04-20", boundaries=(), inherited_from_parent=False),
            "Painter [Welder]": EntityEras(entity="Painter [Welder]", stable_since="2026-05-01", boundaries=(), inherited_from_parent=False),
        }
        _write(con, eras, parent={"Painter": "Painter", "Painter [Welder]": "Painter"})

        horizons, _audit = era_horizons(
            con, ["Painter [Welder]"], camp_parent={"Painter [Welder]": "Painter"},
        )
        assert horizons["Painter [Welder]"] == EraHorizon(
            since="2026-05-01", source="era", trigger=None, alarm=None,
        )
        con.close()

    def test_unmapped_label_falls_through_to_the_prefix_rule(self):
        """A map that covers only SOME labels leaves the rest on the untouched prefix path."""
        con = self._painter_pair_con()
        horizons, _audit = era_horizons(
            con, ["Painter [Welder]", "Painter [Grindstone]"],
            split_variant="Painter", camp_parent={"Painter [Welder]": "Painter"},
        )
        assert horizons["Painter [Welder]"].source == "era-parent"
        assert horizons["Painter [Grindstone]"].source == "era-parent"
        con.close()

    def test_ban_only_fallback_uses_the_mapped_parent(self):
        """The ban-only branch resolves its base label through the map too — a camp of an
        era-less parent must inherit that PARENT's ban date, not its own synthetic label."""
        con = store.connect(":memory:")
        eras = {"Other": EntityEras(entity="Other", stable_since=None, boundaries=(), inherited_from_parent=False)}
        _write(con, eras)
        for i in range(5):
            decks = [_deck(f"r{i}", ["Entomb", "Reanimate"])]
            tid = store.load_tournament(
                con, parse_cache_item(_tournament(f"t{i}", "2025-06-01", decks), "MTGO"),
            )
            con.execute("UPDATE decks SET archetype = 'Reanimator' WHERE tournament_id = ?", [tid])

        horizons, _audit = era_horizons(
            con, ["Reanimator [Turbo]"], camp_parent={"Reanimator [Turbo]": "Reanimator"},
        )
        assert horizons["Reanimator [Turbo]"] == EraHorizon(
            since="2025-11-10", source="ban-only",
            trigger="ban: valid_since 2025-11-10", alarm=None,
        )
        con.close()


# ---------------------------------------------------------------------------
# resolve_field_era
# ---------------------------------------------------------------------------


class TestResolveFieldEra:
    def test_no_era_data_degrades_to_ban_regime(self):
        con = store.connect(":memory:")
        since, label = resolve_field_era(con)
        from legacy_engine.analytics.trends import resolve_regime
        expected_since, _ = resolve_regime("current")
        assert since == expected_since
        assert "no era data" in label
        con.close()

    def test_high_share_entity_widens_field_since(self):
        con = store.connect(":memory:")
        # 600 decks total, "Big" is 60% share with an accepted boundary well after the
        # current ban regime start -> widens (truncates) the field window forward.
        # Dated AFTER the boundary so the resulting [boundary, now) window clears the thin floor.
        boundary_date = in_current_regime(28)
        decks_date = in_current_regime(33)  # 5 days after the boundary
        _load_decks(con, archetype="Big", n=600, dt=decks_date, name_prefix="b")
        _load_decks(con, archetype="Small", n=400, dt=decks_date, name_prefix="s")
        eras = {
            "Big": EntityEras(entity="Big", stable_since=boundary_date, boundaries=(), inherited_from_parent=False),
            "Small": EntityEras(entity="Small", stable_since=None, boundaries=(), inherited_from_parent=False),
        }
        _write(con, eras)

        since, label = resolve_field_era(con, min_share=0.02)
        assert since == boundary_date
        assert "detection-derived" in label
        con.close()

    def test_below_share_floor_entity_ignored(self):
        con = store.connect(":memory:")
        _load_decks(con, archetype="Tiny", n=5, dt="2026-06-01", name_prefix="t")
        _load_decks(con, archetype="Filler", n=995, dt="2026-06-01", name_prefix="f")
        eras = {
            "Tiny": EntityEras(entity="Tiny", stable_since="2026-06-15", boundaries=(), inherited_from_parent=False),
            "Filler": EntityEras(entity="Filler", stable_since=None, boundaries=(), inherited_from_parent=False),
        }
        _write(con, eras)

        from legacy_engine.analytics.trends import resolve_regime
        expected_since, _ = resolve_regime("current")
        since, label = resolve_field_era(con, min_share=0.02)
        assert since == expected_since
        assert "no high-share disturbance" in label
        con.close()

    def test_camp_rows_excluded_from_field_share(self):
        """A camp row (parent != entity) must never itself drive the field boundary."""
        con = store.connect(":memory:")
        _load_decks(con, archetype="Parent", n=600, dt="2026-06-01", name_prefix="p")
        _load_decks(con, archetype="Filler", n=400, dt="2026-06-01", name_prefix="f")
        eras = {
            "Parent": EntityEras(entity="Parent", stable_since=None, boundaries=(), inherited_from_parent=False),
            "Parent [Camp]": EntityEras(entity="Parent [Camp]", stable_since="2026-06-20", boundaries=(), inherited_from_parent=False),
        }
        _write(con, eras, parent={"Parent": "Parent", "Parent [Camp]": "Parent"})

        from legacy_engine.analytics.trends import resolve_regime
        expected_since, _ = resolve_regime("current")
        since, label = resolve_field_era(con, min_share=0.02)
        # "Parent [Camp]"'s boundary must be ignored (it's a camp row, parent != entity);
        # "Parent" itself is undisturbed (None) -> no candidates -> ban regime.
        assert since == expected_since
        con.close()

    def test_thin_resulting_window_degrades_with_banner(self):
        con = store.connect(":memory:")
        # Big has a very recent boundary (just after the current ban regime start) with
        # almost no decks after it.
        boundary_date = in_current_regime(10)
        _load_decks(con, archetype="Big", n=600, dt="2026-01-01", name_prefix="b")
        _load_decks(con, archetype="Big", n=5, dt=boundary_date, name_prefix="b2")
        _load_decks(con, archetype="Filler", n=400, dt="2026-01-01", name_prefix="f")
        eras = {
            "Big": EntityEras(entity="Big", stable_since=boundary_date, boundaries=(), inherited_from_parent=False),
            "Filler": EntityEras(entity="Filler", stable_since=None, boundaries=(), inherited_from_parent=False),
        }
        _write(con, eras)

        from legacy_engine.analytics.trends import resolve_regime
        expected_since, _ = resolve_regime("current")
        since, label = resolve_field_era(con, min_share=0.02)
        assert since == expected_since
        assert "thin field window" in label
        assert "degraded to ban regime" in label
        con.close()

    def test_boundary_not_later_than_ban_regime_stays_at_ban_regime(self):
        con = store.connect(":memory:")
        _load_decks(con, archetype="Big", n=600, dt="2026-06-01", name_prefix="b")
        _load_decks(con, archetype="Filler", n=400, dt="2026-06-01", name_prefix="f")
        # An accepted boundary from BEFORE the current ban regime start must not move the
        # field window backward.
        eras = {
            "Big": EntityEras(entity="Big", stable_since="2026-01-01", boundaries=(), inherited_from_parent=False),
            "Filler": EntityEras(entity="Filler", stable_since=None, boundaries=(), inherited_from_parent=False),
        }
        _write(con, eras)

        from legacy_engine.analytics.trends import resolve_regime
        expected_since, _ = resolve_regime("current")
        since, label = resolve_field_era(con, min_share=0.02)
        assert since == expected_since
        assert "no boundary later than" in label
        con.close()
