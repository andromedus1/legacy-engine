"""Discovered-variant staging registry — loader, staging, and promotion.

The human-confirm surface of the discovery engine (``analytics/discovery.py``). Validated
candidate splits are staged in ``data/variants/discovered.json`` (derived side —
``DISCOVERED_VARIANTS_PATH``) as ``DiscoveredSplitRecord``s with ``status: "candidate"``.
``promote_split`` converts a confirmed camp into a curated ``VariantRule`` appended to the
package-shipped ``data/variants/legacy.json`` (+ a ``defaults`` complement) — discovery never
silently rewrites the curated taxonomy.

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
from legacy_engine.archetype.variants import load_variant_registry
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


def stage_split(reg: DiscoveredRegistry, split: DiscoveredSplitRecord) -> DiscoveredRegistry:
    """Upsert ``split`` into ``reg`` by ``parent`` (replace in place, else append).

    Pure — returns a new registry, never mutates ``reg``.
    """
    splits = list(reg.splits)
    for i, existing in enumerate(splits):
        if existing.parent == split.parent:
            splits[i] = split
            break
    else:
        splits.append(split)
    return DiscoveredRegistry(version=reg.version, splits=splits)


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
    save_discovered(stage_split(disc, promoted), discovered_path)
    return rule


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
