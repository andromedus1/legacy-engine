"""Composed refresh for every input consumed by the Best Deck / Best Call ranking."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

from legacy_engine.ingestion.card_coverage import CardCoverageReport
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.card import CardAliasManifest
from legacy_engine.ingestion.releases import SetRelease


class RefreshStepStatus(StrEnum):
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"
    NOT_RUN = "not_run"


class RefreshStepResult(LegacyEngineModel):
    name: str
    status: RefreshStepStatus
    summary: str
    reason: str | None = None


class FormatAwareness(LegacyEngineModel):
    latest_registered_ban_date: str | None
    latest_registered_ban_card: str | None
    upcoming_releases: tuple[str, ...] = ()
    recent_releases: tuple[str, ...] = ()
    era_alarms: tuple[str, ...] = ()


class SourceRefreshResult(LegacyEngineModel):
    new_card_names: frozenset[str] = frozenset()
    alias_manifest: CardAliasManifest | None = None
    alias_snapshot_reason: str | None = None
    upcoming_releases: tuple[str, ...] = ()
    recent_releases: tuple[str, ...] = ()
    upcoming_release_records: tuple[SetRelease, ...] = ()
    recent_release_records: tuple[SetRelease, ...] = ()
    release_scan_reason: str | None = None
    summary: str


class CampApplyResult(LegacyEngineModel):
    parents: tuple[str, ...] = ()
    labeled: int = 0
    incrementally_assigned: int = 0
    degraded_reasons: tuple[str, ...] = ()


class EraRunResult(LegacyEngineModel):
    entities: int = 0
    alarms: tuple[str, ...] = ()


class RankingUtilitySummary(LegacyEngineModel):
    """Typed publication contract for the generated ranking's evidence usefulness."""

    observed_field_n: int
    effective_field_n: int
    prior_strength: int
    affected_clamp_count: int
    supported_rows: int
    transition_prior_rows: int
    grounded_rows: int
    estimated_rows: int = 0
    visible_estimate_cells: int = 0
    localized_history_matches: int = 0
    affected_estimate_cells: int = 0
    unaffected_estimate_cells: int = 0
    practical_call: str | None
    proof_grade_call: str | None
    # Backward-compatible status field. The dedicated shortlist UI was removed; new
    # artifacts serialize zero while older status snapshots remain readable.
    rendered_shortlist_rows: int
    status: Literal["useful", "degraded", "unavailable"]
    reasons: tuple[str, ...] = ()
    practical_ranked_actions: tuple[str, ...] = ()


def validate_ranking_utility(summary: RankingUtilitySummary) -> None:
    """Reject contradictory generation metadata before a ranking artifact is published."""
    for name in (
        "observed_field_n", "effective_field_n", "prior_strength", "affected_clamp_count",
        "supported_rows", "transition_prior_rows", "grounded_rows", "estimated_rows",
        "visible_estimate_cells", "localized_history_matches", "affected_estimate_cells",
        "unaffected_estimate_cells", "rendered_shortlist_rows",
    ):
        if getattr(summary, name) < 0:
            raise ValueError(f"ranking utility {name} must be non-negative")
    if summary.effective_field_n != summary.observed_field_n + summary.prior_strength:
        raise ValueError("ranking utility effective field counts do not reconcile")
    if summary.grounded_rows > summary.supported_rows:
        raise ValueError("ranking utility grounded rows exceed supported rows")
    if summary.transition_prior_rows > summary.supported_rows:
        raise ValueError("ranking utility transition-prior rows exceed supported rows")
    if (
        summary.affected_estimate_cells + summary.unaffected_estimate_cells
        != summary.visible_estimate_cells
    ):
        raise ValueError("ranking utility estimate-cell provenance counts do not reconcile")
    if (summary.grounded_rows > 0) != (summary.proof_grade_call is not None):
        raise ValueError(
            "ranking utility proof-grade call must exist iff grounded rows exist"
        )
    if summary.supported_rows and summary.practical_call is None:
        raise ValueError("ranking utility has supported rows but no practical call")
    if (
        summary.practical_call is not None
        and summary.practical_ranked_actions
        and summary.practical_call != summary.practical_ranked_actions[0]
    ):
        raise ValueError("ranking utility practical call does not lead the practical ranking")
    if summary.status == "useful" and summary.practical_call is None:
        raise ValueError("useful ranking utility must publish a practical call")
    useful_rows = max(summary.grounded_rows, summary.estimated_rows)
    if summary.status == "useful" and useful_rows < summary.supported_rows:
        raise ValueError("useful ranking utility requires an estimate for every supported row")
    if summary.status == "degraded" and summary.supported_rows and useful_rows >= summary.supported_rows:
        raise ValueError("degraded ranking utility contradicts complete visible estimate support")
    if summary.status == "unavailable" and summary.supported_rows:
        raise ValueError("unavailable ranking utility cannot report supported rows")


class DecisionRefreshResult(LegacyEngineModel):
    steps: tuple[RefreshStepResult, ...]
    card_coverage: CardCoverageReport
    format_awareness: FormatAwareness
    ranking_output: str | None = None
    source_observation: SourceRefreshResult | None = None
    ranking_utility: RankingUtilitySummary | None = None


class DecisionRefreshPorts(Protocol):
    def refresh_sources(self, db_path: Path) -> SourceRefreshResult: ...
    def reconcile_cards(
        self, db_path: Path, source_result: SourceRefreshResult,
    ) -> CardCoverageReport: ...
    def label(self, db_path: Path) -> int: ...
    def apply_staged_camps(self, db_path: Path) -> CampApplyResult: ...
    def run_eras(self, db_path: Path) -> EraRunResult: ...
    def write_ranking(self, db_path: Path, out_path: Path) -> RankingUtilitySummary | None: ...


_STEP_NAMES = ("sources", "card_coverage", "label", "staged_camps", "eras", "ranking")


def _empty_coverage(reason: str) -> CardCoverageReport:
    return CardCoverageReport(
        distinct_names=0,
        affected_decks=0,
        alias_snapshot_degraded=True,
        alias_snapshot_reason=reason,
    )


def _format_awareness() -> FormatAwareness:
    """Read the curated B&R ledger independently of every external refresh source."""
    from legacy_engine.ingestion.banlist import BAN_EVENTS

    if not BAN_EVENTS:
        return FormatAwareness(
            latest_registered_ban_date=None,
            latest_registered_ban_card=None,
        )
    latest = max(BAN_EVENTS, key=lambda event: event[0])
    return FormatAwareness(
        latest_registered_ban_date=latest[0].isoformat(),
        latest_registered_ban_card=latest[1],
    )


def _propagate_alias_currency_uncertainty(source: SourceRefreshResult) -> SourceRefreshResult:
    if source.release_scan_reason is None or source.alias_manifest is None:
        return source
    uncertainty = (
        "alias snapshot currency uncertain because the release scan was unavailable; "
        f"retained last-good aliases: {source.release_scan_reason}"
    )
    if source.alias_snapshot_reason:
        uncertainty = f"{source.alias_snapshot_reason}; {uncertainty}"
    return source.model_copy(update={"alias_snapshot_reason": uncertainty})


def run_decision_refresh(
    ports: DecisionRefreshPorts,
    *,
    db_path: Path,
    out_path: Path,
) -> DecisionRefreshResult:
    """Run required steps in dependency order and retain last-good ranking on failure."""
    steps: list[RefreshStepResult] = []
    source: SourceRefreshResult | None = None
    coverage = _empty_coverage("card reconciliation not run")
    awareness = _format_awareness()
    era_result = EraRunResult()
    ranking_utility: RankingUtilitySummary | None = None

    actions = (
        ("sources", lambda: ports.refresh_sources(db_path)),
        ("card_coverage", lambda: ports.reconcile_cards(db_path, source)),  # type: ignore[arg-type]
        ("label", lambda: ports.label(db_path)),
        ("staged_camps", lambda: ports.apply_staged_camps(db_path)),
        ("eras", lambda: ports.run_eras(db_path)),
        ("ranking", lambda: ports.write_ranking(db_path, out_path)),
    )
    failed = False
    for index, (name, action) in enumerate(actions):
        if failed:
            steps.append(RefreshStepResult(
                name=name, status=RefreshStepStatus.NOT_RUN,
                summary="not run because a prerequisite failed",
            ))
            continue
        try:
            value = action()
            status = RefreshStepStatus.COMPLETED
            reason = None
            summary = "completed"
            if name == "sources":
                source = _propagate_alias_currency_uncertainty(value)
                assert isinstance(source, SourceRefreshResult)
                reasons = tuple(filter(None, (source.release_scan_reason, source.alias_snapshot_reason)))
                if reasons:
                    status = RefreshStepStatus.DEGRADED
                    reason = "; ".join(reasons)
                summary = source.summary
            elif name == "card_coverage":
                coverage = value
                assert isinstance(coverage, CardCoverageReport)
                if coverage.alias_snapshot_degraded:
                    status = RefreshStepStatus.DEGRADED
                    reason = coverage.alias_snapshot_reason
                summary = f"{coverage.distinct_names} names; {coverage.unresolved_count} unresolved"
            elif name == "label":
                summary = f"{value} decks labeled"
            elif name == "staged_camps":
                assert isinstance(value, CampApplyResult)
                if value.degraded_reasons:
                    status = RefreshStepStatus.DEGRADED
                    reason = "; ".join(value.degraded_reasons)
                summary = f"{len(value.parents)} parents; {value.labeled} exact + {value.incrementally_assigned} incremental"
            elif name == "eras":
                era_result = value
                assert isinstance(era_result, EraRunResult)
                summary = f"{era_result.entities} entities; {len(era_result.alarms)} alarms"
            elif name == "ranking":
                if isinstance(value, RankingUtilitySummary):
                    validate_ranking_utility(value)
                    ranking_utility = value
                    summary = f"{out_path}; utility={value.status}"
                    if value.status in {"degraded", "unavailable"}:
                        status = RefreshStepStatus.DEGRADED
                        reason = "; ".join(value.reasons) or f"ranking utility {value.status}"
                else:
                    summary = str(out_path)
            steps.append(RefreshStepResult(name=name, status=status, summary=summary, reason=reason))
        except Exception as exc:
            failed = True
            steps.append(RefreshStepResult(
                name=name, status=RefreshStepStatus.FAILED,
                summary="required step failed", reason=str(exc),
            ))

    if source is not None:
        awareness = awareness.model_copy(update={
            "upcoming_releases": source.upcoming_releases,
            "recent_releases": source.recent_releases,
            "era_alarms": era_result.alarms,
        })
    # A degraded ranking is still a written, candid artifact.  Only failed or
    # not-run ranking steps should be reported as unwritten.
    ranking_output = (
        str(out_path)
        if steps and steps[-1].status in {RefreshStepStatus.COMPLETED, RefreshStepStatus.DEGRADED}
        else None
    )
    return DecisionRefreshResult(
        steps=tuple(steps), card_coverage=coverage,
        format_awareness=awareness, ranking_output=ranking_output,
        source_observation=source,
        ranking_utility=ranking_utility,
    )


def decision_refresh_audit_lines(result: DecisionRefreshResult) -> tuple[str, ...]:
    lines = [
        f"// refresh step: {step.name} — {step.status.value}"
        + (f" — {step.reason}" if step.reason else "")
        for step in result.steps
    ]
    fmt = result.format_awareness
    if fmt.latest_registered_ban_date and fmt.latest_registered_ban_card:
        lines.append(
            f"// B&R ledger: {fmt.latest_registered_ban_card} registered "
            f"{fmt.latest_registered_ban_date} (operator-confirmed; no announcement scrape)"
        )
    else:
        lines.append("// B&R ledger: unavailable — no operator-confirmed event loaded")
    lines.append(f"// releases: recent={len(fmt.recent_releases)}, upcoming={len(fmt.upcoming_releases)}")
    lines.extend(f"// era alarm: {alarm}" for alarm in fmt.era_alarms)
    if result.ranking_output:
        lines.append(f"// ranking: {result.ranking_output}")
    if result.ranking_utility is not None:
        utility = result.ranking_utility
        lines.append(
            f"// ranking utility: {utility.status}; observed={utility.observed_field_n}, "
            f"effective={utility.effective_field_n}, prior={utility.prior_strength}, "
            f"supported={utility.supported_rows}, grounded={utility.grounded_rows}, "
            f"practical={utility.practical_call or 'none'}"
        )
        lines.extend(f"// ranking utility reason: {reason}" for reason in utility.reasons)
    return tuple(lines)


class DefaultDecisionRefreshPorts:
    """Production adapters; orchestration above remains independently testable."""

    def refresh_sources(self, db_path: Path) -> SourceRefreshResult:
        from legacy_engine.ingestion import cache, store
        from legacy_engine.ingestion.releases import fetch_sets, upcoming_and_recent
        from legacy_engine.ingestion.rules_vendor import refresh_rules
        from legacy_engine.ingestion.scryfall import ScryfallClient
        from legacy_engine.models.card import Card, CardAliasManifest

        cache.mirror_cache()
        con = store.connect(db_path)
        try:
            cache_stats = cache.ingest_cache(con)
        finally:
            con.close()
        refresh_rules()

        scan_reason = None
        alias_reason = None
        upcoming = ()
        recent = ()
        recent_codes: tuple[str, ...] = ()
        with ScryfallClient() as client:
            try:
                scan = upcoming_and_recent(fetch_sets(client), today=date.today())
                upcoming = tuple(f"{item.code}: {item.name}" for item in scan.upcoming)
                recent = tuple(f"{item.code}: {item.name}" for item in scan.recently_released)
                recent_codes = tuple(item.code for item in scan.recently_released)
            except Exception as exc:
                scan_reason = f"release scan unavailable: {exc}"
            client.download_bulk_data(force=bool(recent_codes))
            index = client.load_card_index()
            cards = [Card.from_scryfall(raw) for raw in {raw["name"]: raw for raw in index.values()}.values()]
            con = store.connect(db_path)
            try:
                from legacy_engine.ingestion.scryfall import METADATA_PATH
                updated_at = json.loads(METADATA_PATH.read_text()).get("updated_at") if METADATA_PATH.exists() else None
                diff = store.load_cards_diff(con, cards, scryfall_updated_at=updated_at)
                store.persist_ingest_diff(diff)
                manifest = store.load_card_alias_manifest(con)
                if store.alias_snapshot_needs_refresh(manifest, recent_codes):
                    try:
                        alias_path = client.download_all_cards_bulk(force=True)
                        from legacy_engine.config import SCRYFALL_ALL_CARDS_META_PATH
                        alias_meta = json.loads(SCRYFALL_ALL_CARDS_META_PATH.read_text())
                        candidate = CardAliasManifest(
                            source_updated_at=alias_meta.get("updated_at") or "unknown",
                            built_at=datetime.now(timezone.utc),
                            release_codes=tuple(sorted(set((manifest.release_codes if manifest else ()) + recent_codes))),
                            alias_count=0,
                            ambiguous_key_count=0,
                        )
                        manifest = store.rebuild_card_aliases(
                            con, client.iter_printed_aliases(alias_path), manifest=candidate,
                        )
                    except Exception as exc:
                        alias_reason = f"alias snapshot refresh unavailable; retained last-good: {exc}"
                        manifest = store.load_card_alias_manifest(con)
            finally:
                con.close()
        return SourceRefreshResult(
            new_card_names=frozenset(diff.new_names), alias_manifest=manifest,
            alias_snapshot_reason=alias_reason, upcoming_releases=upcoming,
            recent_releases=recent, release_scan_reason=scan_reason,
            upcoming_release_records=tuple(scan.upcoming) if scan_reason is None else (),
            recent_release_records=tuple(scan.recently_released) if scan_reason is None else (),
            summary=f"{cache_stats.loaded} events reloaded; {len(diff.new_names)} new card names",
        )

    def reconcile_cards(self, db_path: Path, source_result: SourceRefreshResult) -> CardCoverageReport:
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.card_coverage import reconcile_card_dimension

        con = store.connect(db_path)
        try:
            return reconcile_card_dimension(
                con, new_card_names=source_result.new_card_names,
                alias_manifest=source_result.alias_manifest,
                alias_snapshot_reason=source_result.alias_snapshot_reason,
                resolved_at=datetime.now(timezone.utc),
            )
        finally:
            con.close()

    def label(self, db_path: Path) -> int:
        from legacy_engine.archetype.color_splits import load_color_split_registry
        from legacy_engine.archetype.labeler import label_decks
        from legacy_engine.archetype.rules import load_ruleset
        from legacy_engine.archetype.variants import load_variant_registry
        from legacy_engine.config import COLOR_SPLITS_REGISTRY_PATH, RULES_DIR, VARIANTS_REGISTRY_PATH
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.scryfall import ScryfallClient

        rules = load_ruleset(RULES_DIR)
        variants = load_variant_registry(VARIANTS_REGISTRY_PATH) if VARIANTS_REGISTRY_PATH.exists() else None
        colors = load_color_split_registry(COLOR_SPLITS_REGISTRY_PATH) if COLOR_SPLITS_REGISTRY_PATH.exists() else None
        con = store.connect(db_path)
        try:
            with ScryfallClient() as client:
                client.load_card_index()
                return label_decks(con, rules, client.get_card, registry=variants, color_splits=colors)
        finally:
            con.close()

    def apply_staged_camps(self, db_path: Path) -> CampApplyResult:
        from legacy_engine.archetype.discovered import apply_split, assign_incremental, staged_split_parents
        from legacy_engine.ingestion import store

        parents = tuple(sorted(staged_split_parents()))
        labeled = 0
        incremental = 0
        degraded: list[str] = []
        con = store.connect(db_path)
        try:
            for parent in parents:
                labeled += apply_split(con, parent)
                result = assign_incremental(con, parent)
                incremental += result.n_assigned
                if result.degraded and result.note:
                    degraded.append(result.note)
        finally:
            con.close()
        return CampApplyResult(
            parents=parents, labeled=labeled, incrementally_assigned=incremental,
            degraded_reasons=tuple(degraded),
        )

    def run_eras(self, db_path: Path) -> EraRunResult:
        from legacy_engine.analytics.eras.run import run_eras
        from legacy_engine.ingestion import store

        con = store.connect(db_path)
        try:
            result = run_eras(con)
        finally:
            con.close()
        return EraRunResult(
            entities=result.n_entities,
            alarms=tuple(result.alarms[key].note for key in sorted(result.alarms)),
        )

    def write_ranking(self, db_path: Path, out_path: Path) -> RankingUtilitySummary | None:
        from legacy_engine.advisory.best_call_generator import (
            current_report_target,
            generate_ranking,
        )

        blob = generate_ranking(
            db_path=db_path,
            out_path=out_path,
            target=current_report_target(db_path),
        )
        utility = blob.get("meta", {}).get("report_utility") or blob.get("meta", {}).get(
            "ranking_utility"
        )
        return RankingUtilitySummary.model_validate(utility) if utility is not None else None
