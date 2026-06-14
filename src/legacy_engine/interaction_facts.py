"""Interaction facts derived from oracle_text — symmetry, targeting, graveyard-safety.

A pure ``interaction_facts(card) -> InteractionFacts`` function that classifies a Card's
interaction semantics from its oracle_text via regex/substring matching.  Companion
function ``verify_graveyard_claim`` checks advisory text claims about a card against the
derived facts.

This is an *orthogonal* layer alongside ``card_tags.py``'s role classification — it models
*who* an effect reaches and *what mechanism* it uses, not *what a card does*.  The three
bugs that prompted this module were all about graveyard-hate symmetry / targeting:

- Grafdigger's Cage: symmetric *restriction* (can't cast/enter from graveyard), but
  does NOT reduce graveyard card count → delirium/delve/escape unaffected.
- Leyline of the Void: opponent-only (``"opponent's graveyard"``).
- Nihil Spellbomb: targeted (``"target player's graveyard"`` → controller aims at opponent).

``self_graveyard_safe`` is the verdict: an effect is safe for the controller's own
graveyard iff it is opponent-only, targeted, self-only, or ``none``, OR if it does not
reduce graveyard card count.  All three example cards are self_graveyard_safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from legacy_engine.card_tags import is_free_spell
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.card import Card

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Affects = Literal["symmetric", "opponent-only", "targeted", "self-only", "none"]
Permanence = Literal["static", "activated", "triggered", "one-shot"]

# ---------------------------------------------------------------------------
# InteractionFacts model
# ---------------------------------------------------------------------------


class InteractionFacts(LegacyEngineModel):
    """Structured interaction semantics derived from a card's oracle_text.

    Fields are heuristic (regex-derived), not authoritative rules-engine outputs.
    Each fact carries a ``confidence`` rating; ``speculative`` means conflicting
    scope signals were found and the verdict is low-trust.

    ``evidence`` quotes the oracle_text line(s) each fact was derived from so
    advisory surfaces can include a human-readable oracle-text excerpt.
    """

    affects: Affects = "none"              # whose resources the effect reaches
    self_graveyard_safe: bool = True       # does NOT reduce the controller's own graveyard count
    touches_graveyard: bool = False        # the effect references a graveyard at all
    graveyard_count_reduction: bool = False  # exiles/removes cards FROM a graveyard
    permanence: Permanence = "one-shot"    # static | activated | triggered | one-shot
    free_cast: bool = False                # castable without paying mana cost
    evidence: tuple[str, ...] = ()         # oracle_text line(s) each fact was derived from
    confidence: ConfidenceMetadata = ConfidenceMetadata()


# ---------------------------------------------------------------------------
# ClaimCheck — guard result
# ---------------------------------------------------------------------------


@dataclass
class ClaimCheck:
    """Result of ``verify_graveyard_claim``.

    ``ok``: True when the claim is consistent with oracle_text (or unverifiable).
    ``claim``: the claim string passed to the guard.
    ``card``: card name.
    ``reason``: why the guard (dis)agrees with oracle_text.
    ``evidence``: oracle_text line(s) consulted.
    """

    ok: bool
    claim: str
    card: str
    reason: str
    evidence: tuple[str, ...]


# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

# Graveyard-scope detection (precedence order: opponent-only > targeted > self-only > symmetric > none)

# Opponent-only scope signals
_RE_OPP_ONLY = re.compile(
    r"opponent's\s+graveyard"
    r"|each\s+opponent"
    r"|target\s+opponent(?:'s)?(?:\s+graveyard)?",
    re.IGNORECASE,
)

# Targeted scope: controller chooses (can always point at opponent)
# "target player's graveyard", "target player", "target ... graveyard"
_RE_TARGETED = re.compile(
    r"target\s+player(?:'s)?"
    r"|target\s+\w+(?:\s+\w+)*\s+graveyard",
    re.IGNORECASE,
)

# Self-only scope: controller's own yard, proactive engine (delve, escape, Snapcaster-style)
# "your graveyard", "your hand" with no opponent/target scoping
_RE_SELF_ONLY = re.compile(
    r"\byour\s+graveyard\b"
    r"|\bfrom\s+your\s+graveyard\b",
    re.IGNORECASE,
)

# Symmetric scope: explicit "each player", "players can't", "all graveyards", or unscoped global
_RE_SYMMETRIC = re.compile(
    r"\beach\s+player"
    r"|\bplayers\s+can't"
    r"|\ball\s+graveyards"
    r"|\beveryone"
    r"|\byour\s+opponents'",
    re.IGNORECASE,
)

# Graveyard count-reduction verbs acting on the graveyard
# exile/remove from graveyard / shuffle into library (removes the cards)
_RE_COUNT_REDUCTION = re.compile(
    r"exile\s+(?:all\s+)?(?:cards?\s+)?(?:in\s+)?(?:each|all|target|your|a|the|it|them|those)"
    r"|exile\s+\w+(?:\s+\w+)*\s+from\s+(?:a|the|your|each|all|target|an?\s+opponent's)\s+graveyard"
    r"|remove\s+.+?\s+from\s+(?:a|the|your|each|all|target|an?\s+opponent's)?\s+graveyard"
    r"|shuffle\s+(?:a|the|your|each|all|it|them|those)\s+(?:graveyard|graveyards|\w+\s+graveyard)",
    re.IGNORECASE | re.DOTALL,
)

# Alternative count-reduction: "exile target player's graveyard", "exile all cards in all graveyards"
_RE_COUNT_REDUCTION_ALT = re.compile(
    r"exile\s+(?:target\s+player's\s+graveyard|all\s+cards?\s+in\s+(?:all|each)\s+graveyard)"
    r"|exile\s+(?:all|each|target|it)\b",
    re.IGNORECASE,
)

# Permanence detection
# Activated: a line ending in ":" that starts with mana/tap/sacrifice cost.
# Covers "{T}:" (single), "{T}, Sacrifice X:" (multi-part), "{B}:" etc.
# The pattern looks for a ":" that terminates a cost clause on the same line.
_RE_ACTIVATION = re.compile(
    # Case 1: simple {cost}: — e.g. "{T}:", "{B}:", "{0}:"
    r"\{[^}]+\}\s*:"
    # Case 2: {cost}, text: — e.g. "{T}, Sacrifice X:", "{T}, Pay 1 life:"
    r"|\{[^}]+\}[^:\n]+:",
    re.IGNORECASE,
)
_RE_TRIGGERED = re.compile(r"\b(?:when|whenever|at\s+the)\b", re.IGNORECASE)
_RE_STATIC_RESTRICTION = re.compile(
    r"\bcan't\b"
    r"|\bcosts?\s*(?:\{[^}]+\}|\d+)\s*(?:more|less)\b"
    r"|\bdon't\s+untap\b"
    r"|\bplayers?\s+can't\b"
    # Replacement effects: "exile it instead", "... instead of ...", "if ... would ... exile it instead"
    r"|\binstead\b"
    r"|\bif\s+\w+\s+would\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _graveyard_lines(oracle_text: str) -> list[str]:
    """Return the lines from oracle_text that reference 'graveyard'."""
    return [
        line
        for line in oracle_text.splitlines()
        if re.search(r"graveyard", line, re.IGNORECASE)
    ]


def _classify_affects(gy_lines: list[str], all_lines: list[str]) -> tuple[Affects, bool]:
    """Classify ``affects`` from graveyard-referencing lines.

    Returns (affects, has_conflict).  A conflict exists when multiple lines carry
    different scopes (e.g. opponent-only on one line, symmetric on another).
    """
    if not gy_lines:
        # Check non-graveyard lines for symmetric restrictions that mention graveyards indirectly
        for line in all_lines:
            if _RE_SYMMETRIC.search(line):
                return "symmetric", False
        return "none", False

    scopes_found: set[str] = set()

    for line in gy_lines:
        # Precedence: opponent-only > targeted > self-only > symmetric
        if _RE_OPP_ONLY.search(line):
            scopes_found.add("opponent-only")
        elif _RE_TARGETED.search(line):
            scopes_found.add("targeted")
        elif _RE_SELF_ONLY.search(line) and not _RE_SYMMETRIC.search(line):
            scopes_found.add("self-only")
        elif _RE_SYMMETRIC.search(line):
            scopes_found.add("symmetric")
        else:
            # Unscoped graveyard line (no per-player scoping marker) → symmetric (conservative).
            # Both static-restriction and bare unscoped lines resolve to symmetric; the
            # _RE_STATIC_RESTRICTION check was redundant (both branches added "symmetric").
            scopes_found.add("symmetric")

    has_conflict = len(scopes_found) > 1

    # Resolve to dominant scope — precedence order
    if "opponent-only" in scopes_found and len(scopes_found) == 1:
        return "opponent-only", False
    if "targeted" in scopes_found and len(scopes_found) == 1:
        return "targeted", False
    if "self-only" in scopes_found and len(scopes_found) == 1:
        return "self-only", False
    if "symmetric" in scopes_found and len(scopes_found) == 1:
        return "symmetric", False

    # Multiple scopes detected: return the highest-priority one found, flag conflict
    for priority_scope in ("opponent-only", "targeted", "self-only", "symmetric"):
        if priority_scope in scopes_found:
            return priority_scope, True  # type: ignore[return-value]

    return "none", False


def _classify_permanence(card: Card) -> Permanence:
    """Classify how the card's effect is delivered: static | activated | triggered | one-shot."""
    type_line = card.type_line or ""
    text = card.oracle_text or ""

    # One-shot: instants and sorceries are ephemeral
    if re.search(r"\b(?:Instant|Sorcery)\b", type_line, re.IGNORECASE):
        return "one-shot"

    # Activated: has a "{cost}:" pattern
    if _RE_ACTIVATION.search(text):
        return "activated"

    # Triggered: has when/whenever/at
    if _RE_TRIGGERED.search(text):
        return "triggered"

    # Static: enchantment/artifact/creature with a continuous restriction
    if _RE_STATIC_RESTRICTION.search(text):
        return "static"

    return "one-shot"


def _detect_count_reduction(gy_lines: list[str]) -> tuple[bool, list[str]]:
    """Return (graveyard_count_reduction, evidence_lines) from graveyard-referencing text lines."""
    evidence: list[str] = []
    found = False
    for line in gy_lines:
        if _RE_COUNT_REDUCTION.search(line) or _RE_COUNT_REDUCTION_ALT.search(line):
            evidence.append(line)
            found = True
    return found, evidence


# ---------------------------------------------------------------------------
# Public API — Unit 1
# ---------------------------------------------------------------------------


def interaction_facts(card: Card) -> InteractionFacts:
    """Derive structured interaction semantics from a Card's oracle_text.

    Pure function — no DB, no network.  All facts are heuristic regex-over-oracle_text
    derivations.  Confidence defaults to ``evolving``; downgrades to ``speculative`` when
    conflicting scope signals appear on different graveyard-referencing lines.

    The ``evidence`` field quotes the oracle_text line(s) each key fact was derived from.
    """
    text = card.oracle_text or ""
    all_lines = text.splitlines()

    # ── touches_graveyard ────────────────────────────────────────────────────
    touches_graveyard = bool(re.search(r"graveyard", text, re.IGNORECASE))

    gy_lines = _graveyard_lines(text) if touches_graveyard else []

    # ── graveyard_count_reduction ────────────────────────────────────────────
    graveyard_count_reduction, count_reduction_lines = _detect_count_reduction(gy_lines)

    # ── affects ──────────────────────────────────────────────────────────────
    affects, has_conflict = _classify_affects(gy_lines, all_lines)

    # ── self_graveyard_safe ──────────────────────────────────────────────────
    # Safe iff: (opponent-only or targeted or self-only or none) OR (no count reduction)
    # Targeted is safe because the controller always aims it at the opponent.
    safe_affects = {"opponent-only", "targeted", "self-only", "none"}
    self_graveyard_safe = (affects in safe_affects) or (not graveyard_count_reduction)

    # ── permanence ───────────────────────────────────────────────────────────
    permanence = _classify_permanence(card)

    # ── free_cast ────────────────────────────────────────────────────────────
    free_cast = is_free_spell(card)

    # ── evidence ─────────────────────────────────────────────────────────────
    # Collect the most informative lines: graveyard lines + count-reduction lines
    evidence_set: list[str] = []
    for line in gy_lines:
        if line not in evidence_set:
            evidence_set.append(line)
    for line in count_reduction_lines:
        if line not in evidence_set:
            evidence_set.append(line)
    evidence = tuple(evidence_set)

    # ── confidence ───────────────────────────────────────────────────────────
    # Heuristic source (no sample n).  Downgrade to speculative on conflicting scope.
    level = "speculative" if has_conflict else "evolving"
    confidence = ConfidenceMetadata(level=level, production="template-generated", source="heuristic")

    return InteractionFacts(
        affects=affects,
        self_graveyard_safe=self_graveyard_safe,
        touches_graveyard=touches_graveyard,
        graveyard_count_reduction=graveyard_count_reduction,
        permanence=permanence,
        free_cast=free_cast,
        evidence=evidence,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Public API — Unit 3: verify_graveyard_claim guard
# ---------------------------------------------------------------------------


def verify_graveyard_claim(card: Card, claims_self_harm: bool) -> ClaimCheck:
    """Check whether a claim that a card harms the controller's own graveyard is consistent
    with the card's oracle_text.

    When ``claims_self_harm=True``: the advisory text asserts this card "bricks/hurts your
    own graveyard/yard".  The guard returns ``ok=False`` with an explanation + evidence when
    the card is actually ``self_graveyard_safe``.

    For ``speculative``-confidence facts, the guard returns a softer "could not confirm"
    annotation rather than a contradiction (per PRINCIPLES "label, don't assert").
    The guard is always *advisory* — never raises an exception.

    When ``claims_self_harm=False``, the guard confirms: if the card is self-graveyard-safe,
    ``ok=True``; if it is actually symmetric-count-reduction, ``ok=True`` (the claim is
    also correct about self-harm).
    """
    facts = interaction_facts(card)
    card_name = card.name

    if not claims_self_harm:
        # Claim: card does NOT hurt own yard.  Check if it's actually safe.
        if facts.self_graveyard_safe:
            return ClaimCheck(
                ok=True,
                claim="does not harm own graveyard",
                card=card_name,
                reason=f"oracle_text confirms self_graveyard_safe: affects={facts.affects!r}, "
                       f"graveyard_count_reduction={facts.graveyard_count_reduction}",
                evidence=facts.evidence,
            )
        else:
            return ClaimCheck(
                ok=False,
                claim="does not harm own graveyard",
                card=card_name,
                reason=f"oracle_text suggests self-harm: affects={facts.affects!r}, "
                       f"graveyard_count_reduction={facts.graveyard_count_reduction}",
                evidence=facts.evidence,
            )

    # claims_self_harm=True
    if not facts.self_graveyard_safe:
        # Claim is correct — this card is indeed symmetric / self-affecting
        return ClaimCheck(
            ok=True,
            claim="hurts own graveyard",
            card=card_name,
            reason=f"oracle_text confirms self-harm: affects={facts.affects!r}, "
                   f"graveyard_count_reduction={facts.graveyard_count_reduction}",
            evidence=facts.evidence,
        )

    # self_graveyard_safe=True → the self-harm claim appears wrong
    if facts.confidence.level == "speculative":
        # Soft annotation: conflicting scope signals — can't definitively contradict
        return ClaimCheck(
            ok=False,
            claim="hurts own graveyard",
            card=card_name,
            reason=(
                f"could not confirm self-harm claim for {card_name!r}: "
                f"oracle_text has conflicting scope signals (confidence=speculative); "
                f"affects={facts.affects!r}, "
                f"graveyard_count_reduction={facts.graveyard_count_reduction} "
                "— review oracle_text manually"
            ),
            evidence=facts.evidence,
        )

    # High-confidence contradiction
    return ClaimCheck(
        ok=False,
        claim="hurts own graveyard",
        card=card_name,
        reason=(
            f"oracle_text contradicts self-harm claim for {card_name!r}: "
            f"affects={facts.affects!r} (self_graveyard_safe=True), "
            f"graveyard_count_reduction={facts.graveyard_count_reduction} — "
            "this card does NOT reduce the controller's own graveyard count"
        ),
        evidence=facts.evidence,
    )
