"""Exact card-name reconciliation and compact card-dimension coverage reporting."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal
import unicodedata
from datetime import datetime

import duckdb

from legacy_engine.ingestion.scryfall import normalize_alias_key
from legacy_engine.ingestion.store import fetch_card_alias_candidates, init_card_alias_schema
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.card import (
    CardAliasManifest,
    CardCoverageCutoff,
    CardCoverageGap,
    CardNameResolution,
    CardNameStatus,
)

logger = logging.getLogger(__name__)


class ProviderSerializationRule(LegacyEngineModel):
    """One evidence-backed provider grammar admitted at reconciliation time."""

    kind: Literal["set_prefix", "duplicated_name", "duplicated_final_face", "localized_faces"]
    provider: str
    evidence: str
    prefixes: tuple[str, ...] = ()


def _load_provider_card_name_registry(
    path: Path | str,
) -> tuple[dict[str, dict[str, str]], tuple[ProviderSerializationRule, ...]]:
    """Load exact exceptions and narrowly typed provider serialization rules."""
    source = Path(path)
    raw = json.loads(source.read_text())
    if (
        not isinstance(raw, dict)
        or not set(raw).issubset({"schema_version", "aliases", "serialization_rules"})
        or raw.get("schema_version") != 1
        or not isinstance(raw.get("aliases"), list)
        or not isinstance(raw.get("serialization_rules", []), list)
    ):
        raise ValueError(f"load_provider_card_aliases: invalid schema in {source}")
    aliases: dict[str, dict[str, str]] = {}
    required = ("observed_name", "canonical_name", "provider", "oracle_id", "evidence")
    for index, item in enumerate(raw["aliases"]):
        if (
            not isinstance(item, dict)
            or set(item) != set(required)
            or any(
                not isinstance(item.get(field), str) or not item[field].strip()
                for field in required
            )
        ):
            raise ValueError(
                f"load_provider_card_aliases: alias[{index}] lacks required provenance in {source}"
            )
        observed = item["observed_name"]
        if observed == item["canonical_name"] or observed in aliases:
            raise ValueError(
                f"load_provider_card_aliases: invalid or duplicate observed name {observed!r} "
                f"in {source}"
            )
        aliases[observed] = {field: item[field] for field in required if field != "observed_name"}

    rules: list[ProviderSerializationRule] = []
    seen_rule_keys: set[tuple[str, str]] = set()
    admitted_prefixes: set[tuple[str, str]] = set()
    allowed_rule_fields = {"kind", "provider", "evidence", "prefixes"}
    for index, item in enumerate(raw.get("serialization_rules", [])):
        if not isinstance(item, dict) or not set(item).issubset(allowed_rule_fields):
            raise ValueError(
                f"load_provider_card_aliases: serialization_rules[{index}] has unknown fields"
            )
        try:
            rule = ProviderSerializationRule.model_validate(item)
        except Exception as exc:
            raise ValueError(
                f"load_provider_card_aliases: invalid serialization_rules[{index}] in {source}"
            ) from exc
        if not rule.provider.strip() or not rule.evidence.strip():
            raise ValueError(
                f"load_provider_card_aliases: serialization_rules[{index}] lacks provenance"
            )
        rule_key = (rule.provider, rule.kind)
        if rule_key in seen_rule_keys:
            raise ValueError(
                f"load_provider_card_aliases: duplicate serialization rule {rule_key!r}"
            )
        seen_rule_keys.add(rule_key)
        if rule.kind == "set_prefix":
            if not rule.prefixes or any(
                not prefix.strip()
                or prefix != prefix.strip()
                or (rule.provider, prefix) in admitted_prefixes
                for prefix in rule.prefixes
            ):
                raise ValueError(
                    f"load_provider_card_aliases: invalid or duplicate set prefix in rule[{index}]"
                )
            admitted_prefixes.update((rule.provider, prefix) for prefix in rule.prefixes)
        elif rule.prefixes:
            raise ValueError(
                "load_provider_card_aliases: prefixes are only valid for set_prefix rules"
            )
        rules.append(rule)
    return aliases, tuple(rules)


def load_provider_card_aliases(path: Path | str) -> dict[str, dict[str, str]]:
    """Load verified historical provider names keyed by their exact observed spelling."""
    return _load_provider_card_name_registry(path)[0]


def _load_default_provider_card_name_registry(
) -> tuple[dict[str, dict[str, str]], tuple[ProviderSerializationRule, ...]]:
    try:
        from legacy_engine.config import CARD_NAME_ALIASES_PATH

        return _load_provider_card_name_registry(CARD_NAME_ALIASES_PATH)
    except Exception as exc:
        logger.error("provider card aliases unavailable; exact reconciliation only: %s", exc)
        return {}, ()


PROVIDER_CARD_ALIASES, PROVIDER_SERIALIZATION_RULES = _load_default_provider_card_name_registry()


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


def load_coverage_preflight_protocol(path: Path | str) -> tuple[tuple[str, ...], str]:
    """Read only the immutable schedule fields needed by card-coverage preflight."""
    source = Path(path)
    try:
        raw = json.loads(source.read_text())
        folds = raw["planned_folds"]
        final_until = raw["final_evaluation_until"]
        cutoffs = tuple(fold["cutoff"] for fold in folds)
        parsed_cutoffs = tuple(datetime.strptime(value, "%Y-%m-%d").date() for value in cutoffs)
        parsed_final = datetime.strptime(final_until, "%Y-%m-%d").date()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid benchmark protocol schedule in {source}") from exc
    if (
        not cutoffs
        or len(cutoffs) != len(set(cutoffs))
        or parsed_cutoffs != tuple(sorted(parsed_cutoffs))
        or parsed_final <= parsed_cutoffs[-1]
    ):
        raise ValueError(
            "benchmark protocol requires non-empty ordered unique planned_folds cutoffs "
            "and a later final_evaluation_until"
        )
    return cutoffs, final_until


def unresolved_card_coverage_by_cutoff(
    con: duckdb.DuckDBPyConnection,
    *,
    cutoffs: tuple[str, ...],
    final_evaluation_until: str,
) -> tuple[CardCoverageCutoff, ...]:
    """Group unresolved observed metadata gaps by their first future training cutoff."""
    rows = con.execute(
        """SELECT dc.name,
                  count(*) AS row_count,
                  count(DISTINCT dc.tournament_id || ':' || CAST(dc.deck_idx AS VARCHAR)),
                  min(t.date),
                  list(DISTINCT t.source ORDER BY t.source) FILTER (WHERE t.source IS NOT NULL),
                  list(DISTINCT t.uri ORDER BY t.uri) FILTER (WHERE t.uri IS NOT NULL)
           FROM deck_cards dc
           JOIN tournaments t ON t.id = dc.tournament_id
           LEFT JOIN cards c ON c.name = dc.name
           WHERE c.name IS NULL AND t.date < ?
           GROUP BY dc.name
           ORDER BY min(t.date), dc.name""",
        [final_evaluation_until],
    ).fetchall()
    grouped: dict[str | None, list[CardCoverageGap]] = {cutoff: [] for cutoff in cutoffs}
    grouped[None] = []
    for observed, row_count, deck_count, first_date, providers, event_uris in rows:
        cohort = next((cutoff for cutoff in cutoffs if first_date < cutoff), None)
        grouped[cohort].append(
            CardCoverageGap(
                observed_name=observed,
                row_count=row_count,
                deck_count=deck_count,
                first_event_date=first_date,
                providers=tuple(providers or ()),
                event_uris=tuple(event_uris or ()),
            )
        )
    return tuple(
        CardCoverageCutoff(cutoff=cutoff, gaps=tuple(grouped[cutoff]))
        for cutoff in (*cutoffs, None)
    )


def card_coverage_preflight_lines(
    cohorts: tuple[CardCoverageCutoff, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    for cohort in cohorts:
        label = cohort.cutoff or "no-later-training-cutoff"
        names = ", ".join(gap.observed_name for gap in cohort.gaps) or "none"
        lines.append(
            f"// coverage preflight: cutoff={label}; rows={sum(g.row_count for g in cohort.gaps)}; "
            f"names={len(cohort.gaps)}; decks={sum(g.deck_count for g in cohort.gaps)}; "
            f"observed={names}"
        )
    return tuple(lines)


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


def provider_serialization_candidate(
    con: duckdb.DuckDBPyConnection,
    observed_name: str,
    *,
    providers: frozenset[str],
    canonical_names: frozenset[str],
    rules: tuple[ProviderSerializationRule, ...],
    resolved_at: datetime,
) -> CardNameResolution | None:
    """Resolve only an admitted provider serialization shape with an exact target."""
    if len(providers) != 1:
        return None
    provider = next(iter(providers))
    parts = tuple(part.strip() for part in observed_name.split(" // "))

    for rule in rules:
        if rule.provider != provider:
            continue
        canonical: str | None = None
        reason = ""
        if rule.kind == "set_prefix":
            for prefix in rule.prefixes:
                marker = f"[{prefix}] "
                if observed_name.startswith(marker):
                    candidate = observed_name[len(marker):]
                    if candidate in canonical_names:
                        canonical = candidate
                        reason = f"verified [{prefix}] set-prefix serialization"
                    break
        elif rule.kind == "duplicated_name":
            if len(parts) == 2 and parts[0] == parts[1] and parts[0] in canonical_names:
                canonical = parts[0]
                reason = "verified duplicated-name serialization"
        elif rule.kind == "duplicated_final_face":
            if len(parts) == 3 and parts[0] == parts[2]:
                candidate = " // ".join(parts[:2])
                if candidate in canonical_names:
                    canonical = candidate
                    reason = "verified duplicated-final-face serialization"
        elif rule.kind == "localized_faces" and len(parts) == 2:
            resolved_faces: list[str] = []
            for face in parts:
                candidates = {
                    item.canonical_name for item in fetch_card_alias_candidates(con, face)
                }
                if len(candidates) != 1:
                    break
                resolved_faces.append(next(iter(candidates)))
            if len(resolved_faces) == 2:
                candidate = " // ".join(resolved_faces)
                if candidate in canonical_names:
                    canonical = candidate
                    reason = "verified independently unique localized-face composition"

        if canonical is not None:
            return _resolution(
                observed_name,
                CardNameStatus.CANONICAL,
                resolved_at,
                reason,
                canonical=canonical,
                source=f"provider_serialization:{provider}",
            )
    return None


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
        """SELECT dc.name,
                  count(DISTINCT dc.tournament_id || ':' || CAST(dc.deck_idx AS VARCHAR)),
                  list(DISTINCT t.source ORDER BY t.source) FILTER (WHERE t.source IS NOT NULL)
           FROM deck_cards dc
           LEFT JOIN tournaments t ON t.id = dc.tournament_id
           GROUP BY dc.name ORDER BY dc.name"""
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

    for observed, _deck_count, provider_rows in observed_rows:
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
            provider_alias = PROVIDER_CARD_ALIASES.get(observed)
            if provider_alias is not None:
                canonical = provider_alias["canonical_name"]
                if canonical not in exact:
                    raise ValueError(
                        f"provider card alias {observed!r} targets absent canonical card "
                        f"{canonical!r}"
                    )
                source = f"curated:{provider_alias['provider']}"
                scryfall_id = provider_alias["oracle_id"]
                status = CardNameStatus.CANONICAL
                reason = "verified historical provider name mapped to the current oracle name"
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
                    provider_resolution = provider_serialization_candidate(
                        con,
                        observed,
                        providers=frozenset(provider_rows or ()),
                        canonical_names=frozenset(exact),
                        rules=PROVIDER_SERIALIZATION_RULES,
                        resolved_at=resolved_at,
                    )
                    if provider_resolution is not None:
                        canonical = provider_resolution.canonical_name
                        source = provider_resolution.source
                        status = provider_resolution.status
                        reason = provider_resolution.reason
                    alias_candidates = fetch_card_alias_candidates(con, observed)
                    alias_canonicals = {item.canonical_name for item in alias_candidates}
                if status is not None:
                    pass
                elif len(alias_canonicals) == 1:
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
