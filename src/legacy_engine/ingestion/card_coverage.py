"""Exact card-name reconciliation and compact card-dimension coverage reporting."""

from __future__ import annotations

import unicodedata
from datetime import datetime

import duckdb

from legacy_engine.ingestion.scryfall import normalize_alias_key, normalize_name
from legacy_engine.ingestion.store import fetch_card_alias_candidates, init_card_alias_schema
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.card import (
    CardAliasManifest,
    CardNameResolution,
    CardNameStatus,
)


class CardCoverageReport(LegacyEngineModel):
    distinct_names: int
    affected_decks: int
    localized_recovered: tuple[CardNameResolution, ...] = ()
    new_cards_recovered: tuple[CardNameResolution, ...] = ()
    normalized_existing: tuple[CardNameResolution, ...] = ()
    ambiguous: tuple[CardNameResolution, ...] = ()
    suspected_truncated: tuple[CardNameResolution, ...] = ()
    unresolved: tuple[CardNameResolution, ...] = ()
    alias_snapshot_updated_at: str | None = None
    alias_snapshot_degraded: bool = False
    alias_snapshot_reason: str | None = None

    @property
    def unresolved_count(self) -> int:
        return len(self.ambiguous) + len(self.suspected_truncated) + len(self.unresolved)


def _resolution(
    observed: str,
    status: CardNameStatus,
    resolved_at: datetime,
    reason: str,
    *,
    canonical: str | None = None,
    language: str | None = None,
    scryfall_id: str | None = None,
    source: str,
    source_updated_at: str | None = None,
) -> CardNameResolution:
    return CardNameResolution(
        observed_name=observed,
        normalized_name=normalize_alias_key(observed),
        status=status,
        canonical_name=canonical,
        language=language,
        scryfall_id=scryfall_id,
        source=source,
        source_updated_at=source_updated_at,
        resolved_at=resolved_at,
        reason=reason,
    )


def _is_non_latin_single_token(value: str) -> bool:
    if len(value.split()) != 1:
        return False
    letters = [ch for ch in value if ch.isalpha()]
    return bool(letters) and any("LATIN" not in unicodedata.name(ch, "") for ch in letters)


def reconcile_card_dimension(
    con: duckdb.DuckDBPyConnection,
    *,
    new_card_names: frozenset[str],
    alias_manifest: CardAliasManifest | None,
    alias_snapshot_reason: str | None,
    resolved_at: datetime,
) -> CardCoverageReport:
    """Classify every observed deck-card name and apply only unique exact resolutions."""
    init_card_alias_schema(con)
    observed_rows = con.execute(
        """SELECT name, count(DISTINCT tournament_id || ':' || CAST(deck_idx AS VARCHAR))
           FROM deck_cards GROUP BY name ORDER BY name"""
    ).fetchall()
    canonical_names = tuple(row[0] for row in con.execute("SELECT name FROM cards").fetchall())
    exact = set(canonical_names)
    canonical_by_key: dict[str, set[str]] = {}
    for name in canonical_names:
        canonical_by_key.setdefault(normalize_alias_key(name), set()).add(name)
    alias_keys = tuple(
        row[0] for row in con.execute("SELECT DISTINCT normalized_alias FROM card_name_aliases").fetchall()
    )
    new_keys = {normalize_alias_key(name) for name in new_card_names}

    groups: dict[CardNameStatus, list[CardNameResolution]] = {
        status: [] for status in CardNameStatus
    }
    updates: list[tuple[str, str]] = []
    affected_names: set[str] = set()

    for observed, _deck_count in observed_rows:
        canonical: str | None = None
        status: CardNameStatus | None = None
        reason = ""
        language = None
        scryfall_id = None
        source = "oracle_cards"
        key = normalize_alias_key(observed)

        if observed in exact:
            if key in new_keys:
                canonical = observed
                status = CardNameStatus.NEW_CARD
                reason = "canonical card was added by the current oracle refresh"
            else:
                continue
        else:
            canonical_candidates = canonical_by_key.get(key, set())
            if len(canonical_candidates) == 1:
                canonical = next(iter(canonical_candidates))
                status = CardNameStatus.NEW_CARD if key in new_keys else CardNameStatus.CANONICAL
                reason = "exact normalized canonical name in the card dimension"
            elif len(canonical_candidates) > 1:
                status = CardNameStatus.AMBIGUOUS
                reason = "normalized canonical key maps to multiple English card names; no mapping applied"
            else:
                alias_candidates = fetch_card_alias_candidates(con, observed)
                alias_canonicals = {item.canonical_name for item in alias_candidates}
                if len(alias_canonicals) == 1:
                    candidate = alias_candidates[0]
                    canonical = candidate.canonical_name
                    language = candidate.language
                    scryfall_id = candidate.scryfall_id
                    source = "scryfall_all_cards"
                    status = CardNameStatus.LOCALIZED
                    reason = "exact localized printed-name alias resolved to one English card"
                elif len(alias_canonicals) > 1:
                    source = "scryfall_all_cards"
                    status = CardNameStatus.AMBIGUOUS
                    reason = "exact alias key maps to multiple English card names; no mapping applied"
                elif _is_non_latin_single_token(observed) and any(key in alias for alias in alias_keys):
                    source = "scryfall_all_cards"
                    status = CardNameStatus.SUSPECTED_TRUNCATED
                    reason = "single non-Latin token occurs inside a known localized alias; suspected truncation, no mapping applied"
                else:
                    status = CardNameStatus.UNRESOLVED
                    reason = "no exact canonical or localized alias match; no mapping applied"

        assert status is not None
        resolution = _resolution(
            observed,
            status,
            resolved_at,
            reason,
            canonical=canonical,
            language=language,
            scryfall_id=scryfall_id,
            source=source,
            source_updated_at=(alias_manifest.source_updated_at if source == "scryfall_all_cards" and alias_manifest else None),
        )
        groups[status].append(resolution)
        affected_names.add(observed)
        if canonical is not None and status in {
            CardNameStatus.CANONICAL,
            CardNameStatus.LOCALIZED,
            CardNameStatus.NEW_CARD,
        } and observed != canonical:
            updates.append((canonical, observed))

    affected_decks = 0
    if affected_names:
        placeholders = ", ".join("?" for _ in affected_names)
        affected_decks = con.execute(
            f"""SELECT count(DISTINCT tournament_id || ':' || CAST(deck_idx AS VARCHAR))
                FROM deck_cards WHERE name IN ({placeholders})""",
            sorted(affected_names),
        ).fetchone()[0]

    if updates:
        con.execute("BEGIN TRANSACTION")
        try:
            con.executemany("UPDATE deck_cards SET name = ? WHERE name = ?", updates)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    ordered = {status: tuple(sorted(items, key=lambda item: item.observed_name)) for status, items in groups.items()}
    return CardCoverageReport(
        distinct_names=len(observed_rows),
        affected_decks=affected_decks,
        localized_recovered=ordered[CardNameStatus.LOCALIZED],
        new_cards_recovered=ordered[CardNameStatus.NEW_CARD],
        normalized_existing=ordered[CardNameStatus.CANONICAL],
        ambiguous=ordered[CardNameStatus.AMBIGUOUS],
        suspected_truncated=ordered[CardNameStatus.SUSPECTED_TRUNCATED],
        unresolved=ordered[CardNameStatus.UNRESOLVED],
        alias_snapshot_updated_at=alias_manifest.source_updated_at if alias_manifest else None,
        alias_snapshot_degraded=alias_snapshot_reason is not None,
        alias_snapshot_reason=alias_snapshot_reason,
    )


def card_coverage_audit_lines(
    report: CardCoverageReport,
    *,
    verbose: bool = False,
) -> tuple[str, ...]:
    snapshot = report.alias_snapshot_updated_at or "absent"
    if report.alias_snapshot_degraded:
        snapshot += f" (degraded: {report.alias_snapshot_reason})"
    lines = [
        "// card dimension: "
        f"{report.distinct_names} distinct names; {report.affected_decks} affected decks; "
        f"recovered localized={len(report.localized_recovered)}, "
        f"new={len(report.new_cards_recovered)}, normalized={len(report.normalized_existing)}; "
        f"gaps ambiguous={len(report.ambiguous)}, "
        f"suspected_truncated={len(report.suspected_truncated)}, "
        f"unresolved={len(report.unresolved)}; aliases={snapshot}"
    ]
    if verbose:
        for items in (
            report.localized_recovered,
            report.new_cards_recovered,
            report.normalized_existing,
            report.ambiguous,
            report.suspected_truncated,
            report.unresolved,
        ):
            for item in items:
                lines.append(f"//   {item.status.value}: {item.observed_name} — {item.reason}")
    return tuple(lines)
