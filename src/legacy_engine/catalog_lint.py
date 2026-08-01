"""Catalog lint — cross-checks curated card-data JSON against the ``cards`` table.

Hand-curated JSON (hosers, linchpins) records facts about specific Magic cards — colors,
castability, symmetry, functional grouping — that live independently of the Scryfall-derived
``cards`` table. Those facts drift silently: Hydroblast/Pyroblast shipped with swapped attack
tags, and Null Rod was curated as ``["G"]`` when the card is actually colorless. Nothing
cross-checked the JSON against ground truth, so both slipped through review.

``lint_catalogs(con)`` is pure: it loads the two curated JSON files (paths default to
``legacy_engine.config``, overridable so tests never touch the shipped files), looks up each
named card in ``cards`` on the given DuckDB connection, and returns a list of ``LintFinding``.
No file is written and no process exits — the CLI leaf (``legacy-engine lint catalog``) owns
echo/exit-code behavior.

Checks, by id:
  ``name_exists``                (error) — curated ``name`` is an exact-spelling row in ``cards``.
                                   Runs against BOTH catalogs.
  ``colors_match``                (error) — hoser ``colors`` == the card's actual ``colors`` set.
  ``castable_any_color_signal``   (warn)  — hoser ``castable_any_color`` vs a Phyrexian-mana /
                                   free-hand-activation signal in mana_cost/oracle_text.
  ``symmetry_wording``            (warn)  — hoser declared ``asymmetric`` but oracle_text reads
                                   "each/all/a player" with no "opponent" scoping (may hit its own
                                   controller too — the shape of the Blood Moon / Null Rod family).
  ``functional_group_coherence``  (warn)  — functional_group members' oracle_text (color words
                                   stripped) aren't textually similar enough to plausibly be the
                                   same effect.

``colors_match``/``castable_any_color_signal``/``symmetry_wording``/``functional_group_coherence``
only run over the hoser catalog — the linchpin schema (``advisory/linchpins.py``) has no
``colors``/``castable_any_color``/``symmetry``/``functional_group`` fields to check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb

from legacy_engine.advisory.linchpins import load_linchpin_overrides
from legacy_engine.advisory.sideboard import HoserCard, load_hoser_catalog
from legacy_engine.config import HOSERS_REGISTRY_PATH, LINCHPINS_REGISTRY_PATH


@dataclass(frozen=True)
class LintFinding:
    """One cross-check result.

    ``source``: the curated JSON file path (str) the entry came from.
    ``entry``:  the curated card name — or, for the group-level ``functional_group_coherence``
                check, the group's member names joined by ``" / "``.
    ``check``:  the check id (module docstring).
    """

    severity: Literal["error", "warn"]
    source: str
    entry: str
    check: str
    message: str


# ---------------------------------------------------------------------------
# Heuristic regexes + tunables
# ---------------------------------------------------------------------------

# Phyrexian mana notation, e.g. "{B/P}" — castable for life regardless of a deck's colors.
_PHYREXIAN_MANA_RE = re.compile(r"\{[^}]*/P\}")

# A zero-mana ability usable straight from hand (Faerie Macabre: "Discard this card: ...") —
# never requires casting the spell at all, so any deck can get value from it regardless of color.
_FREE_HAND_ACTIVATION_RE = re.compile(r"\b(?:discard|sacrifice|exile) this card\b", re.IGNORECASE)

# Literal owner-unrestricted phrasing (module docstring's "each/all/a player" example).
_SYMMETRIC_WORDING_RE = re.compile(r"\b(?:each player|all players|a player)\b", re.IGNORECASE)

_COLOR_WORDS = frozenset({"white", "blue", "black", "red", "green"})
_WORD_RE = re.compile(r"[a-z0-9']+")

# Minimum pairwise Jaccard similarity (color words stripped) for a functional_group's members
# to count as "plausibly the same effect". Tuned so Hydroblast/Blue Elemental Blast and
# Pyroblast/Red Elemental Blast (near-verbatim reprints of each other) land well clear of it.
_FUNCTIONAL_GROUP_SIMILARITY_THRESHOLD = 0.4


def _has_any_color_signal(mana_cost: "str | None", oracle_text: "str | None") -> bool:
    """True when the card's own text plausibly makes it usable regardless of a deck's color
    identity: a Phyrexian-mana cast cost, or a free hand-activation ability that never requires
    casting the spell at all."""
    if _PHYREXIAN_MANA_RE.search(mana_cost or ""):
        return True
    return bool(_FREE_HAND_ACTIVATION_RE.search(oracle_text or ""))


def _has_symmetric_wording(oracle_text: "str | None") -> bool:
    """True when the text reads as owner-unrestricted (module docstring's "each/all/a player"
    phrasing) with no "opponent" scoping anywhere in the text to narrow it."""
    text = oracle_text or ""
    if "opponent" in text.lower():
        return False
    return bool(_SYMMETRIC_WORDING_RE.search(text))


def _effect_tokens(oracle_text: "str | None") -> "set[str]":
    """Lowercased word tokens with WUBRG color names stripped, so e.g. Hydroblast and Blue
    Elemental Blast (mirrored "if it's red" / "target red spell" phrasing) compare structurally
    rather than being penalized for which color they name."""
    words = _WORD_RE.findall((oracle_text or "").lower())
    return {w for w in words if w not in _COLOR_WORDS}


def _jaccard(a: "set[str]", b: "set[str]") -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _fetch_card_row(con: duckdb.DuckDBPyConnection, name: str) -> "dict | None":
    """Fetch one card's linted columns as a dict, or None if the name isn't in ``cards``."""
    cur = con.execute(
        "SELECT name, colors, mana_cost, oracle_text FROM cards WHERE name = ?", [name]
    )
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def lint_catalogs(
    con: duckdb.DuckDBPyConnection,
    hosers_path: "Path | str" = HOSERS_REGISTRY_PATH,
    linchpins_path: "Path | str" = LINCHPINS_REGISTRY_PATH,
) -> "list[LintFinding]":
    """Cross-check the curated hoser + linchpin catalogs against ``cards`` on ``con``.

    Loads both curated JSON files via their existing schema-validating loaders (a malformed
    entry still raises ``ValueError``/``FileNotFoundError`` there, before any cross-check runs),
    looks up every named card in ``cards``, and returns every ``LintFinding`` produced by the
    checks in the module docstring. Order is not significant — callers sort/group as needed.
    """
    findings: "list[LintFinding]" = []

    hosers_source = str(hosers_path)
    linchpins_source = str(linchpins_path)

    hosers = load_hoser_catalog(hosers_path)
    linchpin_overrides = load_linchpin_overrides(linchpins_path)

    # ── hosers: name_exists, colors_match, castable_any_color_signal, symmetry_wording ──
    for hoser in hosers.values():
        row = _fetch_card_row(con, hoser.name)
        if row is None:
            findings.append(LintFinding(
                severity="error",
                source=hosers_source,
                entry=hoser.name,
                check="name_exists",
                message=f"{hoser.name!r} not found in cards (exact spelling)",
            ))
            continue

        db_colors = frozenset(row["colors"] or "")
        if db_colors != hoser.colors:
            findings.append(LintFinding(
                severity="error",
                source=hosers_source,
                entry=hoser.name,
                check="colors_match",
                message=(
                    f"declared colors {sorted(hoser.colors)} != actual {sorted(db_colors)} "
                    f"(cards.colors={row['colors']!r})"
                ),
            ))

        signal = _has_any_color_signal(row["mana_cost"], row["oracle_text"])
        if hoser.castable_any_color and not signal:
            findings.append(LintFinding(
                severity="warn",
                source=hosers_source,
                entry=hoser.name,
                check="castable_any_color_signal",
                message=(
                    "castable_any_color=True but no Phyrexian-mana cost or free hand-activation "
                    "text found in mana_cost/oracle_text"
                ),
            ))
        elif not hoser.castable_any_color and _PHYREXIAN_MANA_RE.search(row["mana_cost"] or ""):
            findings.append(LintFinding(
                severity="warn",
                source=hosers_source,
                entry=hoser.name,
                check="castable_any_color_signal",
                message=(
                    f"mana_cost {row['mana_cost']!r} has Phyrexian mana notation but "
                    "castable_any_color is not set"
                ),
            ))

        if hoser.symmetry == "asymmetric" and _has_symmetric_wording(row["oracle_text"]):
            findings.append(LintFinding(
                severity="warn",
                source=hosers_source,
                entry=hoser.name,
                check="symmetry_wording",
                message=(
                    'declared asymmetric but oracle_text reads "each/all/a player" with no '
                    '"opponent" scoping — may hit its own controller too'
                ),
            ))

    # ── hosers: functional_group_coherence ──
    groups: "dict[str, list[HoserCard]]" = {}
    for hoser in hosers.values():
        if hoser.functional_group:
            groups.setdefault(hoser.functional_group, []).append(hoser)

    for group, members in groups.items():
        if len(members) < 2:
            continue
        token_sets: "dict[str, set[str]]" = {}
        for member in members:
            row = _fetch_card_row(con, member.name)
            if row is not None:
                token_sets[member.name] = _effect_tokens(row["oracle_text"])

        names = sorted(token_sets)
        if len(names) < 2:
            continue

        min_sim = 1.0
        for i, name_a in enumerate(names):
            for name_b in names[i + 1:]:
                min_sim = min(min_sim, _jaccard(token_sets[name_a], token_sets[name_b]))

        if min_sim < _FUNCTIONAL_GROUP_SIMILARITY_THRESHOLD:
            findings.append(LintFinding(
                severity="warn",
                source=hosers_source,
                entry=" / ".join(names),
                check="functional_group_coherence",
                message=(
                    f"functional_group {group!r} members don't look textually similar enough to "
                    f"plausibly share an effect (min pairwise similarity {min_sim:.2f} < "
                    f"{_FUNCTIONAL_GROUP_SIMILARITY_THRESHOLD})"
                ),
            ))

    # ── linchpins: name_exists only (the linchpin schema has no colors/symmetry/etc. fields) ──
    for archetype, entries in linchpin_overrides.items():
        for linchpin in entries:
            row = _fetch_card_row(con, linchpin.name)
            if row is None:
                findings.append(LintFinding(
                    severity="error",
                    source=linchpins_source,
                    entry=linchpin.name,
                    check="name_exists",
                    message=(
                        f"{linchpin.name!r} (archetype {archetype!r}) not found in cards "
                        "(exact spelling)"
                    ),
                ))

    return findings
