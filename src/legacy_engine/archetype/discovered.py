"""Discovered-variant staging registry — loader, staging, and promotion.

The human-confirm surface of the discovery engine (``analytics/discovery.py``). Validated
candidate splits are staged in ``data/variants/discovered.json`` (derived side —
``DISCOVERED_VARIANTS_PATH``) as ``DiscoveredSplitRecord``s with ``status: "candidate"``.
``promote_split`` converts a confirmed camp into a curated ``VariantRule`` appended to the
package-shipped ``data/variants/legacy.json`` (+ a ``defaults`` complement) — discovery never
silently rewrites the curated taxonomy. ``apply_split`` is the labeled-speculative middle
ground: it writes a staged (still-unpromoted) split's camps directly onto ``decks.variant`` so
analytics can read them before a human confirms the split — the staged record's ``status``
never changes and the curated registry is never touched.

Loader shape follows the curated-json-resource-loader pattern (path-taking, validating,
fail-fast citing the offending path), with one deliberate divergence: the staging file is a
*derived* artifact under ``DATA_DIR`` (not a package resource), so an absent file is the normal
"nothing staged yet" state and loads as an empty registry rather than an error. A *malformed*
file still fails fast — a corrupt staging registry is a bug, not an author edit.
"""

from __future__ import annotations

import json
from pathlib import Path

from legacy_engine.analytics.discovery import DiscoveredSplit
from legacy_engine.archetype.rules import Condition, _loads_lenient
from legacy_engine.archetype.variants import load_variant_registry, resolve_variant
from legacy_engine.models.variant import (
    DiscoveredCamp,
    DiscoveredRegistry,
    DiscoveredSplitRecord,
    VariantRegistry,
    VariantRule,
)

# How many over-represented signature cards a staged camp carries (display + promotion source;
# the full divergence list lives only in the in-memory DiscoveredSplit, not the staging file).
TOP_SIGNATURE_CARDS = 5

_REGISTRY_VERSION = "1"


def load_discovered(path: Path | str) -> DiscoveredRegistry:
    """Load the staging registry from ``path``.

    Absent file → empty registry (normal pre-first-``discover run`` state).
    Malformed file → ``ValueError`` citing the path (fail-fast; the file is machine-written,
    so corruption is a bug to surface, never to half-load).
    """
    path = Path(path)
    if not path.exists():
        return DiscoveredRegistry(version=_REGISTRY_VERSION, splits=[])
    try:
        raw = _loads_lenient(path.read_text())
        return DiscoveredRegistry.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"load_discovered: malformed staging registry at {path}: {exc}") from exc


def save_discovered(reg: DiscoveredRegistry, path: Path | str) -> None:
    """Write the staging registry to ``path`` (mkdir at write time, never on import)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg.model_dump(), indent=2) + "\n")


def record_from_split(
    split: DiscoveredSplit,
    *,
    generated_from: str,
    params: dict,
) -> DiscoveredSplitRecord:
    """Convert an in-memory ``DiscoveredSplit`` (analytics result) into a staging record.

    Each camp keeps only its top ``TOP_SIGNATURE_CARDS`` *over-represented* cards (positive
    delta vs the rest) — the first is what promotion turns into an ``InMainboard`` condition.
    """
    camps = [
        DiscoveredCamp(
            name=camp.name,
            signature_cards=[
                name for name, delta in camp.signature_cards if delta > 0
            ][:TOP_SIGNATURE_CARDS],
            n=camp.n,
            tier=camp.tier,
        )
        for camp in split.camps
    ]
    return DiscoveredSplitRecord(
        parent=split.parent,
        generated_from=generated_from,
        params=params,
        camps=camps,
        stability=split.stability,
    )


def stage_split(
    reg: DiscoveredRegistry, split: DiscoveredSplitRecord
) -> tuple[DiscoveredRegistry, DiscoveredSplitRecord | None]:
    """Upsert ``split`` into ``reg`` by ``parent`` (replace in place, else append).

    Pure — returns ``(new_registry, replaced)``; ``reg`` is never mutated. ``replaced`` is the
    record that previously occupied ``split.parent`` (``None`` on a fresh append) — callers use
    it to surface an honest "you just overwrote a staged candidate" echo (``discover run``).
    """
    splits = list(reg.splits)
    replaced: DiscoveredSplitRecord | None = None
    for i, existing in enumerate(splits):
        if existing.parent == split.parent:
            replaced = existing
            splits[i] = split
            break
    else:
        splits.append(split)
    return DiscoveredRegistry(version=reg.version, splits=splits), replaced


def promote_split(
    parent: str,
    camp_name: str,
    discovered_path: Path | str,
    registry_path: Path | str,
) -> VariantRule:
    """Promote the staged camp ``camp_name`` of ``parent`` into the curated variant registry.

    Builds a ``VariantRule`` with an ``InMainboard`` condition on the camp's top signature card
    (mirroring the shipped Bauble/Loam entries) and appends it to ``registry_path``. In the
    2-camp case the other camp's name becomes ``defaults[parent]`` — the complement tag for
    decks that don't match the positive condition. The staged split's ``status`` flips to
    ``"promoted"``.

    Fail-fast ``ValueError`` on: no staged split for ``parent``; no camp named ``camp_name``;
    split already promoted; a ``(parent, camp_name)`` rule already present in the curated
    registry; or a camp with no over-represented signature card to build a condition from.

    Returns the appended ``VariantRule`` (for the CLI to echo).
    """
    disc = load_discovered(discovered_path)
    split = next((s for s in disc.splits if s.parent == parent), None)
    if split is None:
        staged = ", ".join(sorted(s.parent for s in disc.splits)) or "(none)"
        raise ValueError(
            f"promote_split: no staged split for parent {parent!r} in {discovered_path} "
            f"(staged parents: {staged})"
        )
    if split.status == "promoted":
        raise ValueError(
            f"promote_split: split for {parent!r} is already promoted (status={split.status!r})"
        )
    camp = next((c for c in split.camps if c.name == camp_name), None)
    if camp is None:
        available = ", ".join(sorted(c.name for c in split.camps))
        raise ValueError(
            f"promote_split: no camp {camp_name!r} staged for {parent!r} "
            f"(available: {available})"
        )
    if not camp.signature_cards:
        raise ValueError(
            f"promote_split: camp {camp_name!r} has no over-represented signature card "
            "to build an InMainboard condition from"
        )

    registry = load_variant_registry(registry_path)
    if any(v.parent == parent and v.name == camp_name for v in registry.variants):
        raise ValueError(
            f"promote_split: variant {parent!r}/{camp_name!r} already exists in {registry_path}"
        )

    rule = VariantRule(
        parent=parent,
        name=camp_name,
        conditions=[Condition(Type="InMainboard", Cards=[camp.signature_cards[0]])],
    )

    new_defaults = dict(registry.defaults)
    other_camps = [c for c in split.camps if c.name != camp_name]
    if len(other_camps) == 1:
        # 2-camp split: the complement camp becomes the parent's default tag.
        new_defaults[parent] = other_camps[0].name

    new_registry = VariantRegistry(
        version=registry.version,
        variants=[*registry.variants, rule],
        defaults=new_defaults,
    )
    _write_variant_registry(new_registry, registry_path)

    promoted = split.model_copy(update={"status": "promoted"})
    new_disc, _replaced = stage_split(disc, promoted)
    save_discovered(new_disc, discovered_path)
    return rule


def apply_split(
    con,
    parent: str,
    *,
    discovered_path: Path | str | None = None,
) -> int:
    """Apply a staged (unpromoted) candidate split's camps directly onto ``decks.variant``.

    The labeled-speculative analytics overlay from the epic's human-confirm-hook design
    decision: an explicit, user-invoked action that lets analytics (``report matchups
    --split-variant``, ``report cards --conditioned --variant``) read a staged split's camps
    *before* a human confirms/promotes it, rather than forcing a promotion just to look.

    Builds the SAME transient ``VariantRule`` set ``promote_split`` would install — each camp's
    top over-represented signature card becomes an ``InMainboard`` condition, and (mirroring
    ``promote_split`` exactly) a complement default is only added in the 2-camp case: the camp
    with a signature card gets the explicit rule, the other camp becomes
    ``defaults[parent]``. For 3+-camp splits every camp with a signature card gets its own rule
    and no default is added (matching ``promote_split``'s ``len(other_camps) == 1`` check).

    Resolves every deck currently labeled ``parent`` against this transient registry via
    ``resolve_variant`` and writes ``decks.variant`` for decks that resolve to a camp name.
    Decks that don't match any camp are left untouched — they stay whatever they were (normally
    NULL) and surface honestly as ``[unlabeled]`` downstream; nothing is fabricated.

    Does NOT touch the curated registry (``data/variants/legacy.json``) and does NOT change the
    staged record's ``status`` — the candidate stays ``status: "candidate"``. This is an
    explicit analytical overlay, not a taxonomy promotion.

    Fail-fast ``ValueError`` on: no staged split for ``parent``; or no camp in the split has an
    over-represented signature card to build a condition from (nothing could be applied).

    Returns the count of decks labeled.
    """
    from legacy_engine.config import DISCOVERED_VARIANTS_PATH

    path = discovered_path if discovered_path is not None else DISCOVERED_VARIANTS_PATH
    disc = load_discovered(path)
    split = next((s for s in disc.splits if s.parent == parent), None)
    if split is None:
        staged = ", ".join(sorted(s.parent for s in disc.splits)) or "(none)"
        raise ValueError(
            f"apply_split: no staged candidate split for parent {parent!r} in {path} "
            f"(staged parents: {staged})"
        )

    rules: list[VariantRule] = []
    defaults: dict[str, str] = {}
    camps = split.camps
    if len(camps) == 2:
        with_sig = [c for c in camps if c.signature_cards]
        if with_sig:
            promoted_camp = with_sig[0]
            other_camp = next(c for c in camps if c is not promoted_camp)
            rules.append(
                VariantRule(
                    parent=parent,
                    name=promoted_camp.name,
                    conditions=[
                        Condition(Type="InMainboard", Cards=[promoted_camp.signature_cards[0]])
                    ],
                )
            )
            defaults[parent] = other_camp.name
    else:
        for camp in camps:
            if camp.signature_cards:
                rules.append(
                    VariantRule(
                        parent=parent,
                        name=camp.name,
                        conditions=[Condition(Type="InMainboard", Cards=[camp.signature_cards[0]])],
                    )
                )

    if not rules:
        raise ValueError(
            f"apply_split: no camp in the staged split for {parent!r} has an over-represented "
            "signature card to build a condition from — nothing to apply"
        )

    registry = VariantRegistry(version="transient", variants=rules, defaults=defaults)

    deck_keys = con.execute(
        "SELECT tournament_id, deck_idx FROM decks WHERE archetype = ?", [parent]
    ).fetchall()

    labeled = 0
    for tid, idx in deck_keys:
        rows = con.execute(
            "SELECT board, name, count FROM deck_cards WHERE tournament_id = ? AND deck_idx = ?",
            [tid, idx],
        ).fetchall()
        mainboard: dict[str, int] = {}
        sideboard: dict[str, int] = {}
        for board, name, count in rows:
            target = mainboard if board == "main" else sideboard
            target[name] = target.get(name, 0) + count

        variant = resolve_variant(parent, mainboard, sideboard, registry)
        if variant is not None:
            con.execute(
                "UPDATE decks SET variant = ? WHERE tournament_id = ? AND deck_idx = ?",
                [variant, tid, idx],
            )
            labeled += 1

    return labeled


def _write_variant_registry(reg: VariantRegistry, path: Path | str) -> None:
    """Serialize the curated registry back to JSON in the shipped file's shape.

    ``by_alias=True`` keeps conditions in the ``Type``/``Cards`` casing the loader and the
    hand-edited file use; ``exclude_defaults=True`` per rule keeps promotion from spraying
    default fields (``include_in_label``) into a hand-curated file.
    """
    data = {
        "version": reg.version,
        "variants": [
            rule.model_dump(by_alias=True, exclude_defaults=True) for rule in reg.variants
        ],
        "defaults": reg.defaults,
    }
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
