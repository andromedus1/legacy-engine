"""Archetype linchpin model — hybrid derive + curated overrides.

Unit 4 of ``feature-sb-effect-tagging-model`` (epic-sideboard-scoring-model). A "linchpin" is
an archetype's critical point of failure: the card (or small set of cards) whose removal breaks
the deck's plan, as opposed to a redundant piece (a Mox, a cantrip) the deck can shrug off. This
is the ``centrality`` input Feature B's impact score will consume — hitting a linchpin should
score very differently from hitting a redundant piece.

Hybrid design (chosen over pure-derive or pure-curated):
  - **Derive** candidate linchpins from composition — a card that's near-mandatory (high
    inclusion%) AND plays a combo-critical role (tutor/engine/payoff) is auto-flagged at a
    conservative default centrality (``_DERIVED_CENTRALITY``). Transparent, auditable, and scales
    to archetypes nobody has hand-curated yet.
  - **Curate** overrides for the archetypes experts know cold — e.g. Painter's Grindstone is
    THE linchpin (removing it fully breaks the Painter/Stone kill, not just weakens it), which
    a generic inclusion-threshold heuristic cannot express as centrality 1.0 vs 0.6. Curated
    entries win on name match; unmatched derived linchpins are kept.

``neutralized_by`` capability vocabulary (NEW — owned by this model)
---------------------------------------------------------------------
Describes HOW a linchpin can be answered, in terms of the *type of removal effect* required —
deliberately NOT the hoser ``attacks`` tag space (which describes what a card hoses, e.g.
``plays-red``, ``graveyard-recursion``). Bridging a hoser's ``attacks`` to a linchpin's
``neutralized_by`` (i.e. "does this sideboard card actually answer this linchpin") and folding
that into the centrality/impact score are Feature B's job, not this story's.

Initial token set (extend here + update this docstring if a curated entry needs a new one):
  - ``artifact-ability-lock``  — a tapper/bounce/counter effect that stops an artifact's activated
                                  ability from being used (without removing the permanent).
  - ``artifact-bounce``        — returns the artifact to hand (resets state; e.g. clears counters).
  - ``artifact-removal``       — destroys/exiles the artifact outright.
  - ``exile-graveyard``        — exiles the card (or its graveyard) so it can't be recurred.
  - ``counter-on-cast``        — must be answered on the stack; once it resolves the effect is done
                                  (classic one-shot Sorcery/Instant combo pieces — Show and Tell).
  - ``board-sweep``            — a mass-removal effect that catches it as a creature among others.
  - ``creature-removal``       — single-target creature removal.
  - ``enchantment-removal``    — destroys/exiles the enchantment outright.

Role-name mapping for derivation
---------------------------------
``Linchpin.role`` uses the label vocabulary from the parent feature's design
(``"combo-engine"`` | ``"combo-tutor"`` | ``"key-payoff"`` | ...). ``whattoplay._card_roles``
does not define those labels directly (its vocabulary is oracle-text-classification roles:
``fast_mana``, ``counter``, ``removal``, ``ritual``, ``tutor``, ``storm``, ``graveyard_recursion``,
``graveyard_fuel``, ``protection``, ``stax``, ``card_advantage``, ``discard``, ``threat``), so
``derive_linchpins`` maps the closest existing roles onto the linchpin vocabulary, in priority
order (a card can carry several ``_card_roles``; the first matching entry below wins):

  1. ``tutor``      -> ``"combo-tutor"``   — "search your library for a/an/up to ..." is the
                                              textbook combo-tutor effect (Demonic Tutor, etc.).
  2. ``storm``       -> ``"key-payoff"``   — the storm-count payoff spell itself (Tendrils of
                                              Agony, Grapeshot) is what the deck is building to
                                              cast; it is the plan's payoff, not its engine.
  3. ``ritual``      -> ``"combo-engine"`` — net-positive-mana rituals (Dark Ritual, Cabal Ritual)
                                              are the engine that powers the rest of the combo.
  4. ``fast_mana``   -> ``"combo-engine"`` — Moxen / fast-mana artifacts play the same engine
                                              role as rituals (accelerate into the combo turn).

This mapping is intentionally conservative: many true archetype linchpins (Grindstone, Show and
Tell) have oracle text that doesn't match ANY of these roles at all, which is exactly why the
hybrid model exists — the curated overrides catch what composition-only derivation can't.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from legacy_engine.advisory.whattoplay import _card_roles
from legacy_engine.models.card import Card

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Linchpin dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Linchpin:
    """A single critical point of failure for an archetype.

    ``archetype``:     the archetype this linchpin belongs to.
    ``name``:           card name (or a mechanic label for a curated multi-card combo piece).
    ``role``:           ``"combo-engine"`` | ``"combo-tutor"`` | ``"key-payoff"`` | ... — see
                        module docstring for the derivation role-mapping; curated entries may use
                        any descriptive role label (e.g. ``"lock-piece"``).
    ``centrality``:     in ``(0, 1]`` — how much removing it breaks the plan. 1.0 = the deck
                        cannot function without it; lower values are partial/soft linchpins.
    ``neutralized_by``: frozenset of capability tokens describing HOW it can be answered (see
                        module docstring's vocabulary). This is a NEW vocabulary distinct from
                        the hoser ``attacks`` tag space — bridging the two is Feature B's job.
    """

    archetype: str
    name: str
    role: str
    centrality: float
    neutralized_by: "frozenset[str]"


# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

_LINCHPIN_INCLUSION = 0.90  # near-mandatory inclusion% to auto-qualify a card as derived
_DERIVED_CENTRALITY = 0.6   # default centrality for a derived (non-curated) linchpin


# ---------------------------------------------------------------------------
# Curated JSON SSOT loader — mirrors load_hoser_catalog (curated-json-resource-loader pattern).
# ---------------------------------------------------------------------------

def load_linchpin_overrides(path: "Path | str") -> "dict[str, list[Linchpin]]":
    """Load + validate curated per-archetype linchpin overrides from a JSON data file.

    Format: ``{"version": 1, "linchpins": {"<archetype>": [ {...}, ... ], ...}}``.

    Each entry must have:
      ``name``            (str, non-empty)
      ``role``             (str, non-empty)
      ``centrality``       (number in (0, 1])
      ``neutralized_by``   (list of strings; may be empty)

    Raises ``ValueError`` naming the offending archetype/entry on any schema violation
    (missing/empty ``name``/``role``, ``centrality`` outside ``(0, 1]``, non-list
    ``neutralized_by``), or when the top-level ``linchpins`` key is absent/not a dict.
    Raises ``FileNotFoundError`` when ``path`` does not exist.

    Standalone and path-taking (no config import) so it is hand-testable with a tmp file and
    reused by ``_load_default_linchpin_overrides``.
    """
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    linchpins_raw = raw.get("linchpins")
    if not isinstance(linchpins_raw, dict):
        raise ValueError(f"load_linchpin_overrides: 'linchpins' must be an object in {path}")

    result: "dict[str, list[Linchpin]]" = {}
    for archetype, entries in linchpins_raw.items():
        if not isinstance(entries, list):
            raise ValueError(
                f"load_linchpin_overrides: {archetype!r} entries must be a list in {path}"
            )

        built: "list[Linchpin]" = []
        for idx, entry in enumerate(entries):
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError(
                    f"load_linchpin_overrides: {archetype!r}[{idx}] missing or empty 'name' "
                    f"in {path}"
                )

            role = entry.get("role")
            if not isinstance(role, str) or not role:
                raise ValueError(
                    f"load_linchpin_overrides: {archetype!r}/{name!r} missing or empty 'role' "
                    f"in {path}"
                )

            centrality_raw = entry.get("centrality")
            if not isinstance(centrality_raw, (int, float)) or isinstance(centrality_raw, bool):
                raise ValueError(
                    f"load_linchpin_overrides: {archetype!r}/{name!r} 'centrality' must be a "
                    f"number in {path}"
                )
            centrality = float(centrality_raw)
            if not (0.0 < centrality <= 1.0):
                raise ValueError(
                    f"load_linchpin_overrides: {archetype!r}/{name!r} centrality={centrality} "
                    f"out of (0, 1] in {path}"
                )

            neutralized_by_raw = entry.get("neutralized_by", [])
            if not isinstance(neutralized_by_raw, list):
                raise ValueError(
                    f"load_linchpin_overrides: {archetype!r}/{name!r} 'neutralized_by' must be "
                    f"a list in {path}"
                )
            neutralized_by = frozenset(str(t) for t in neutralized_by_raw)

            built.append(
                Linchpin(
                    archetype=archetype,
                    name=name,
                    role=role,
                    centrality=centrality,
                    neutralized_by=neutralized_by,
                )
            )

        result[archetype] = built

    return result


def _load_default_linchpin_overrides() -> "dict[str, list[Linchpin]]":
    """Load LINCHPIN_OVERRIDES from the shipped data file; degrade to {} on error."""
    try:
        from legacy_engine.config import LINCHPINS_REGISTRY_PATH
        return load_linchpin_overrides(LINCHPINS_REGISTRY_PATH)
    except Exception as exc:
        log.error(
            "LINCHPIN_OVERRIDES: failed to load from data file — returning empty overrides: %s",
            exc,
        )
        return {}


LINCHPIN_OVERRIDES: "dict[str, list[Linchpin]]" = _load_default_linchpin_overrides()


# ---------------------------------------------------------------------------
# Derivation — pure, no DB (objective-search-split: caller resolves Card objects +
# inclusion_pct once; this function only does arithmetic + regex classification over them).
# ---------------------------------------------------------------------------

# Priority-ordered role mapping: whattoplay._card_roles label -> Linchpin.role label.
# See module docstring "Role-name mapping for derivation" for the rationale behind each entry.
# Order matters: a card carrying several roles is labeled by the FIRST match below.
_LINCHPIN_ROLE_PRIORITY: "tuple[tuple[str, str], ...]" = (
    ("tutor", "combo-tutor"),
    ("storm", "key-payoff"),
    ("ritual", "combo-engine"),
    ("fast_mana", "combo-engine"),
)

# Reminder text ("(...)") can contain a colon-shaped example without being an activated
# ability (e.g. "({C} represents colorless mana.)" has no colon, but some reminders do);
# strip it before checking for the "Cost: Effect" activated-ability shape.
_RE_REMINDER_TEXT = re.compile(r"\([^)]*\)")


def _has_activated_ability(oracle_text: str) -> bool:
    """Heuristic: an activated ability reads as ``Cost: Effect`` — a bare colon outside
    reminder text. Not a full rules parser; good enough to distinguish Grindstone-shaped
    artifacts (``"{3}, {T}: Target player mills two cards."``) from static/triggered ones."""
    stripped = _RE_REMINDER_TEXT.sub("", oracle_text or "")
    return ":" in stripped


def _infer_neutralized_by(card: Card) -> "frozenset[str]":
    """Infer capability tokens (module docstring vocabulary) from a linchpin card's own
    type_line/oracle_text — how it can plausibly be answered, not what it answers.

    Pure, oracle-text-grounded heuristic (auditable per PRINCIPLES #7), deliberately simple:
      - Artifact (non-creature) with an activated ability (e.g. Grindstone) ->
        {artifact-ability-lock, artifact-bounce, artifact-removal}: tap/bounce effects stop the
        activation; outright removal works too.
      - Any artifact without a detected activated ability -> {artifact-removal} only (no
        activation to lock/bounce away from).
      - Creature -> {creature-removal, board-sweep}: single-target removal or a sweeper both
        answer it.
      - Enchantment -> {enchantment-removal}.
      - Graveyard-recursion role (recurs from its own graveyard) -> {exile-graveyard}.
      - Instant/Sorcery (a one-shot effect; once it resolves the effect already happened) ->
        {counter-on-cast}: the only window to stop it is on the stack.

    Returns the union of every branch that applies (a card can be answered multiple ways).
    Returns an empty frozenset when nothing is inferable — an honest "unknown" rather than a
    guessed default; Feature B treats bridging as its own job.
    """
    type_line = card.type_line or ""
    text = card.oracle_text or ""
    roles = _card_roles(card)

    tags: "set[str]" = set()

    is_artifact = "Artifact" in type_line
    is_creature = "Creature" in type_line
    is_enchantment = "Enchantment" in type_line
    is_instant_sorcery = "Instant" in type_line or "Sorcery" in type_line

    if is_artifact:
        if _has_activated_ability(text):
            tags.update({"artifact-ability-lock", "artifact-bounce", "artifact-removal"})
        else:
            tags.add("artifact-removal")

    if is_creature:
        tags.update({"creature-removal", "board-sweep"})

    if is_enchantment:
        tags.add("enchantment-removal")

    if "graveyard_recursion" in roles:
        tags.add("exile-graveyard")

    if is_instant_sorcery:
        tags.add("counter-on-cast")

    return frozenset(tags)


def derive_linchpins(
    archetype: str,
    cards_with_counts: "list[tuple[Card, int]]",
    inclusion_pct: "dict[str, float]",
) -> "list[Linchpin]":
    """Auto-detect candidate linchpins from composition (PURE — no DB).

    A card qualifies when BOTH:
      1. ``inclusion_pct[card.name] >= _LINCHPIN_INCLUSION`` (near-mandatory — the card is
         basically always in the 75, so its absence is a real gap, not a flex slot); AND
      2. ``whattoplay._card_roles(card)`` intersects the role-priority map above (the card
         plays a combo-critical role: tutor, storm payoff, or mana-engine piece).

    Cards missing from ``inclusion_pct`` are treated as 0% (never qualify) rather than raising —
    ``inclusion_pct`` is expected to come from real archetype frequency data and may legitimately
    omit cards absent from that archetype's corpus sample.

    Qualifying cards are emitted at the flat ``_DERIVED_CENTRALITY`` default (0.6) — deliberately
    below any curated centrality of 1.0, so an over-eager derivation is a small scoring error, not
    a blowup (see the parent feature's "Linchpin derivation false positives" risk note).

    ``archetype`` is stamped onto every emitted ``Linchpin`` (there is no cross-archetype
    inference here — this is per-archetype composition analysis).
    """
    result: "list[Linchpin]" = []
    for card, _count in cards_with_counts:
        pct = inclusion_pct.get(card.name, 0.0)
        if pct < _LINCHPIN_INCLUSION:
            continue

        roles = _card_roles(card)
        label = None
        for role_key, mapped_label in _LINCHPIN_ROLE_PRIORITY:
            if role_key in roles:
                label = mapped_label
                break
        if label is None:
            continue

        result.append(
            Linchpin(
                archetype=archetype,
                name=card.name,
                role=label,
                centrality=_DERIVED_CENTRALITY,
                neutralized_by=_infer_neutralized_by(card),
            )
        )

    return result


def _merge_linchpins(
    derived: "list[Linchpin]",
    curated: "list[Linchpin]",
) -> "list[Linchpin]":
    """Merge curated overrides over derived candidates: curated WINS by name (case-insensitive);
    unmatched derived entries are kept as-is. Pure — split out from ``linchpins_for_archetype``
    so the merge logic is directly unit-testable without depending on the module-level registry."""
    curated_names_lower = {lp.name.lower() for lp in curated}
    merged = list(curated)
    merged.extend(d for d in derived if d.name.lower() not in curated_names_lower)
    return merged


def linchpins_for_archetype(
    archetype: str,
    cards_with_counts: "list[tuple[Card, int]]",
    inclusion_pct: "dict[str, float]",
) -> "list[Linchpin]":
    """The public entry point: derive candidates, then merge curated overrides on top.

    Curated overrides (from the shipped ``LINCHPIN_OVERRIDES``, keyed by ``archetype``) win by
    name over anything ``derive_linchpins`` would produce for the same card — even a curated
    centrality that disagrees with what derivation would compute. Derived linchpins with no
    curated counterpart are kept unchanged.
    """
    derived = derive_linchpins(archetype, cards_with_counts, inclusion_pct)
    curated = LINCHPIN_OVERRIDES.get(archetype, [])
    return _merge_linchpins(derived, curated)
