"""Decomposed per-(hoser, opponent) impact score — Units B1 + B2 of
``feature-sb-field-weighted-scorer`` (epic-sideboard-scoring-model).

PURE / DB-FREE (objective-search-split pattern): every function here takes already-resolved
inputs (a ``HoserCard``, an opponent's ``Linchpin`` list, a vulnerability-tag frozenset, a
color frozenset, a copy count) and returns plain floats / a frozen dataclass. No DuckDB
connection, no I/O. This is what makes the module hand-testable with hand-built inputs
(``tests/test_impact.py``) and keeps the eventual ILP wiring (Unit B3/B4, a separate story)
free to call these functions from inside a tight per-element loop.

Design decisions (locked at the parent feature, ``feature-sb-field-weighted-scorer`` §
"Design decisions"):
  - **Multiplicative combination with hard gates.** ``impact = centrality × symmetry ×
    castability × draw_prob``. Any factor at (or near) 0 zeroes the whole score — a
    fully-symmetric self-hoser or an uncastable card is worthless regardless of how much
    field it nominally covers. This is deliberately harsher than an additive/weighted-average
    combination and is the entire point of the model (see the feature's "Multiplicative
    over-zeroing" risk note — floors on centrality/symmetry exist precisely to keep a
    *mildly* awkward card from cratering to literal 0; only true uncastability and a
    literal-0-copies board hard-gate to exactly 0.0).

Unit B2 — the hoser -> linchpin ``neutralized_by`` capability bridge — is deliberately left
unimplemented as anything fancier than a curated lookup (see ``hoser_capabilities`` below).
``linchpins.py`` explicitly deferred this bridge to Feature B (see its module docstring); this
module owns it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from legacy_engine.advisory.linchpins import Linchpin

if TYPE_CHECKING:
    # HoserCard lives in advisory.sideboard, which is a future consumer of THIS module
    # (Unit B3/B4, a separate story). Importing it only for type-checking avoids creating a
    # runtime circular import once sideboard.py starts importing from here.
    from legacy_engine.advisory.sideboard import HoserCard


# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

_CENTRALITY_BASELINE = 0.5
"""Default centrality when a hoser doesn't neutralize any known opponent linchpin.
Non-linchpin coverage still counts (a hoser can be broadly useful without answering the
opponent's single most critical card) — it's simply valued at half of a full linchpin hit."""

_SYMMETRY_FLOOR = 0.15
"""Floor value for a symmetric hoser that self-hoses (shares the hosed axis with my own
deck). Deliberately > 0: a fully self-hosing symmetric card (e.g. Grafdigger's Cage in a
graveyard-recursion deck) is a near-trap, not a literal zero — sequencing/timing (cast it
after your own graveyard plan already paid off, or only board it in when you're not on the
recursion plan that game) can still occasionally rescue some value. See the parent feature's
"Multiplicative over-zeroing" risk note: floors exist so a merely-awkward card doesn't crater
to a hard 0 the way a genuinely uncastable card does."""

_BO3_CARDS_SEEN = 24
"""Cards seen, across a full Bo3 match, that are meaningfully "eligible" to have drawn a
boarded-in sideboard card. Reasoning (the taper SHAPE this drives matters far more than the
exact constant — see the parent feature's "Draw-prob assumptions" risk note):
  - A sideboard card is live for the games you actually have it in your 75 — you sideboard
    after game 1, so call that ~2 of the 3 possible games (you always get game 2; you get
    game 3 only if the set goes the distance). Modeling "2 live games" is the simple,
    documented approximation used here.
  - Per game, cards seen = a 7-card opening hand + draws before the game is typically
    decided. Legacy games are fast (free spells, low curves, combo/tempo plans); a game
    commonly resolves by around turn 8-10. Splitting play/draw evenly gives ~5 draw steps
    by the time a typical game is decided, i.e. ~12 cards seen per game (7 + 5).
  - 2 live games x 12 cards/game = 24.
This is a named, documented, tunable constant precisely so it can be revisited without
touching the hypergeometric math itself.
"""


@dataclass(frozen=True)
class ImpactBreakdown:
    """The four decomposed impact factors for one (hoser, opponent-archetype, my-deck) triple.

    Each factor is in ``[0, 1]``. ``score()`` is the multiplicative combination the parent
    feature locked in as the objective's per-card impact term — kept as a method (rather than
    a bare float) so every recommendation stays explainable: the pilot can see WHY a card
    scored the way it did, factor by factor (Unit B5, a later story, surfaces this breakdown
    in ``advise sideboard`` output).
    """

    centrality: float
    symmetry: float
    castability: float
    draw_prob: float

    def score(self) -> float:
        """Multiplicative combination — hard gates. Any factor at 0 zeroes the whole score."""
        return self.centrality * self.symmetry * self.castability * self.draw_prob


def _clamp01(value: float) -> float:
    """Clamp to [0, 1]. Inputs are already contractually in range (Linchpin.centrality is
    validated to (0, 1] at load time); this is a defensive guard, not the primary contract."""
    return min(max(value, 0.0), 1.0)


# ---------------------------------------------------------------------------
# Unit B2 — hoser -> linchpin `neutralized_by` capability bridge
# ---------------------------------------------------------------------------

# Curated, oracle-text-grounded per-card capability map (name, case-insensitive -> capability
# tokens from linchpins.py's `neutralized_by` vocabulary: artifact-ability-lock,
# artifact-bounce, artifact-removal, exile-graveyard, counter-on-cast, board-sweep,
# creature-removal, enchantment-removal).
#
# Mirrors the existing hard-coded-map precedent in advisory/sideboard.py
# (`is_anti_synergistic`'s known-self-harming-hosers table) rather than a new JSON resource —
# this table is small, hand-curated, and reviewed alongside the catalog it describes.
#
# Grounded by reading each catalog card's oracle_text in data/legacy.duckdb at authoring time
# (READ-ONLY; this module never opens the DB itself). Deliberately conservative: a card is
# only credited with a capability its text clearly supports, per these rules —
#
#   - "exile target card(s) from a graveyard" / "exile ... put into an opponent's graveyard"
#     -> exile-graveyard. Extended (documented, not literal) to effects that remove a
#     linchpin's ACCESS to its own graveyard without literal exile wording — Endurance
#     (bottom-of-library reset), Containment Priest (exiles a would-be-recursion target as it
#     tries to cheat into play), and Grafdigger's Cage (locks casting/entering from graveyard
#     or library outright) all deny a graveyard-recursion linchpin's plan just as thoroughly
#     as a literal exile effect, even though the mechanism differs. `exile-graveyard` is the
#     closest available token in the fixed 8-token vocabulary for "denies GY-recursion
#     access"; adding a finer-grained token is out of scope for this story.
#   - "counter target spell" / "counter ... unless" / "exile target spell(s)" (a
#     stack-timed answer that must be applied before the spell resolves) -> counter-on-cast.
#     Chalice of the Void's static "counter that spell" ability is included on the same
#     reasoning even though it isn't a spell itself.
#   - "destroy/exile target artifact" -> artifact-removal; same for enchantment ->
#     enchantment-removal; a sweeper that hits many nonland permanents at once also earns
#     board-sweep in addition to the specific-type token(s) it demonstrably destroys.
#   - "activated abilities of artifacts/[a named source] can't be activated" -> only
#     artifact-ability-lock (removes the permanent's activation, not the permanent itself).
#   - Hand disruption (Thoughtseize, Duress), protection (Veil of Summer), taxes (Defense
#     Grid, Damping Sphere), mana-denial without removal (Blood Moon, Back to Basics,
#     Harbinger of the Seas, Carpet of Flowers), and land destruction (Wasteland — the
#     vocabulary has no land-removal token) get NO capability credit: none of the 8 tokens
#     describe what they do. This is an honest "unknown/not-applicable", mirroring
#     `linchpins._infer_neutralized_by`'s own empty-frozenset convention — these cards still
#     score at `_CENTRALITY_BASELINE` rather than being penalized.
#   - Edict effects (Sheoldred's Edict: "each opponent sacrifices a ... of their choice") get
#     NO capability credit — the OPPONENT chooses what to lose, so the effect cannot reliably
#     be credited with answering one SPECIFIC named linchpin the way a targeted removal spell
#     can. This is the single most deliberate under-crediting choice in this table.
_CAPABILITY_BY_NAME: "dict[str, frozenset[str]]" = {
    "surgical extraction": frozenset({"exile-graveyard"}),
    "faerie macabre": frozenset({"exile-graveyard"}),
    "leyline of the void": frozenset({"exile-graveyard"}),
    "endurance": frozenset({"exile-graveyard"}),
    "containment priest": frozenset({"exile-graveyard"}),
    "grafdigger's cage": frozenset({"exile-graveyard"}),
    "nihil spellbomb": frozenset({"exile-graveyard"}),
    "dauthi voidwalker": frozenset({"exile-graveyard"}),
    "force of will": frozenset({"counter-on-cast"}),
    "flusterstorm": frozenset({"counter-on-cast"}),
    "mindbreak trap": frozenset({"counter-on-cast"}),
    "consign to memory": frozenset({"counter-on-cast"}),
    "force of vigor": frozenset({"artifact-removal", "enchantment-removal"}),
    "krosan grip": frozenset({"artifact-removal", "enchantment-removal"}),
    "pyroblast": frozenset(
        {"counter-on-cast", "artifact-removal", "creature-removal", "enchantment-removal"}
    ),
    "hydroblast": frozenset(
        {"counter-on-cast", "artifact-removal", "creature-removal", "enchantment-removal"}
    ),
    "blue elemental blast": frozenset(
        {"counter-on-cast", "artifact-removal", "creature-removal", "enchantment-removal"}
    ),
    "red elemental blast": frozenset(
        {"counter-on-cast", "artifact-removal", "creature-removal", "enchantment-removal"}
    ),
    "chalice of the void": frozenset({"counter-on-cast"}),
    "engineered explosives": frozenset(
        {"board-sweep", "artifact-removal", "creature-removal", "enchantment-removal"}
    ),
    "toxic deluge": frozenset({"board-sweep", "creature-removal"}),
    "pithing needle": frozenset({"artifact-ability-lock"}),
    "null rod": frozenset({"artifact-ability-lock"}),
}


def hoser_capabilities(hoser: "HoserCard") -> "frozenset[str]":
    """Map a hoser to the linchpin ``neutralized_by`` capability vocabulary.

    Curated lookup by card name (case-insensitive) — see ``_CAPABILITY_BY_NAME`` above for
    the full rule set and per-card grounding notes. Cards absent from the table (uncataloged,
    freshly-promoted-from-empirical-data, or simply not yet reviewed) return an empty
    frozenset — an honest "unknown", not a guessed default. ``centrality_factor`` treats an
    empty capability set as "no confirmed linchpin hit", which degrades gracefully to
    ``_CENTRALITY_BASELINE`` rather than wrongly zeroing or wrongly crediting the card.

    Pure — takes the ``HoserCard`` only; does not open a DB connection. Grounding new cards
    into this table (reading their oracle_text) is a maintenance-time activity, not a
    runtime one.
    """
    return _CAPABILITY_BY_NAME.get(hoser.name.lower(), frozenset())


# ---------------------------------------------------------------------------
# Unit B1 — the four decomposed factors
# ---------------------------------------------------------------------------


def centrality_factor(
    hoser: "HoserCard",
    opp_archetype: str,
    opp_linchpins: "list[Linchpin]",
) -> float:
    """How much of the opponent's plan this hoser demonstrably breaks.

    The max ``centrality`` among ``opp_linchpins`` (filtered to ``opp_archetype``, defensively
    — callers are expected to already pass a per-archetype list from
    ``linchpins_for_archetype``) whose ``neutralized_by`` intersects this hoser's
    ``hoser_capabilities()``. Falls back to ``_CENTRALITY_BASELINE`` when the hoser doesn't
    confirmed-neutralize any linchpin (either because it genuinely doesn't, or because
    ``hoser_capabilities`` doesn't yet have it graded — both cases degrade to "unknown",
    not "zero").
    """
    caps = hoser_capabilities(hoser)
    if not caps:
        return _CENTRALITY_BASELINE

    hits = [
        lp.centrality
        for lp in opp_linchpins
        if lp.archetype == opp_archetype and lp.neutralized_by & caps
    ]
    if not hits:
        return _CENTRALITY_BASELINE
    return _clamp01(max(hits))


def symmetry_factor(hoser: "HoserCard", my_vulnerability_tags: "frozenset[str]") -> float:
    """Penalize a symmetric hoser that hits my own deck on the same axis it hits the opponent.

    ``hoser.attacks`` and the vulnerability-tag vocabulary (``whattoplay.VulnerabilityTag``)
    are the SAME tag space (graveyard-recursion, graveyard-fuel, plays-<color>, combo,
    low-curve, greedy-manabase, creature-based, low-interaction, storm-reliant, ramp) — a
    symmetric hoser "shares the hosed axis" with my deck exactly when
    ``hoser.attacks & my_vulnerability_tags`` is non-empty (e.g. a symmetric
    graveyard-recursion hoser boarded in by a deck that ALSO carries the graveyard-recursion
    vulnerability tag is self-hosing on that axis).

    - ``"asymmetric"`` -> always 1.0 (only hits the opponent/their stuff, by construction).
    - ``"symmetric"`` and axis shared -> ``_SYMMETRY_FLOOR`` (near-trap, not a hard 0 — see
      the constant's docstring).
    - ``"symmetric"`` and axis NOT shared (I'm not exposed to what this card also hits on my
      side) -> 1.0 (fully asymmetric IN PRACTICE for this particular deck).
    """
    if hoser.symmetry != "symmetric":
        return 1.0
    if hoser.attacks & my_vulnerability_tags:
        return _SYMMETRY_FLOOR
    return 1.0


_PLAINS_NAMES: "frozenset[str]" = frozenset({"Plains", "Snow-Covered Plains"})


def _opp_controls_plains(opp_cards: "object | None") -> bool:
    """Conservative literal-name check over an opponent's known card names.

    Accepts anything name-iterable: a ``frozenset[str]``/``set[str]``/``list[str]`` of card
    names, or a ``dict[str, int]`` composition (its keys are used). Matches the two literal
    basic-Plains names. Does NOT resolve card types, so a Plains-producing dual/fetchland
    (e.g. Flooded Strand can fetch a Plains, but Flooded Strand itself is not one) is not
    credited — a documented conservative gap, consistent with this module never touching the
    DB to look up type_line.
    """
    if not opp_cards:
        return False
    names = opp_cards.keys() if isinstance(opp_cards, dict) else opp_cards
    return any(name in _PLAINS_NAMES for name in names)


def castability_factor(
    hoser: "HoserCard",
    my_colors: "frozenset[str]",
    opp_archetype: str,
    opp_cards: "object | None" = None,
) -> float:
    """Hard-gate castability in this specific matchup. Returns 1.0 or 0.0 — never a
    partial value; castability is a binary gate by design (the parent feature's locked
    "multiplicative hard gates" decision).

    ``opp_archetype`` is accepted (not currently branched on) for signature parity with the
    feature design and to leave room for a future archetype-keyed ``cast_requires`` token —
    the only token defined today (``"opp_controls_plains"``) is opponent-composition-keyed,
    not archetype-keyed, but resolving it still requires knowing which opponent we're facing.

    Ordering / precedent: a ``cast_requires`` token is treated the same way
    ``castable_any_color`` already is — an ALTERNATIVE cast path that supersedes the ordinary
    color-subset check, not an additional constraint layered on top of it. This mirrors the
    ``HoserCard.castable_any_color`` docstring ("the color pre-filter is bypassed"): a card
    like Massacre is a sideboard consideration specifically FOR its free-cast clause, so its
    printed color identity shouldn't gate it once that clause's condition is being evaluated.
      - ``cast_requires == "opp_controls_plains"``: 1.0 only when ``opp_cards`` is supplied
        AND indicates a Plains; otherwise 0.0. We chose the hard-gate (0.0), not a low
        nonzero value, for the unsatisfied case — a conditional free-cast that provably can't
        fire in this specific matchup is modeled as uncastable here, not merely weaker,
        consistent with the parent feature's multiplicative hard-gate philosophy. This errs
        conservative: better to omit a candidate than recommend a card whose entire premise
        (working around a bad manabase / an otherwise-unplayable cost) doesn't apply here.
      - No ``cast_requires``: 1.0 when ``castable_any_color`` or ``hoser.colors`` is a subset
        of ``my_colors``; else 0.0 (the ordinary color hard gate).
    """
    if hoser.cast_requires == "opp_controls_plains":
        return 1.0 if _opp_controls_plains(opp_cards) else 0.0

    if hoser.castable_any_color:
        return 1.0
    if hoser.colors.issubset(my_colors):
        return 1.0
    return 0.0


def draw_probability(
    copies: int,
    deck_size: int = 60,
    cards_seen: int = _BO3_CARDS_SEEN,
) -> float:
    """P(draw >= 1 of ``copies`` identical cards in ``cards_seen`` draws from a
    ``deck_size``-card deck), hypergeometric, no replacement.

    ``1 - C(deck_size - copies, cards_seen) / C(deck_size, cards_seen)``. Monotonically
    increasing in ``copies`` (more copies -> strictly higher or equal chance to see one), and
    the per-copy MARGINAL (``draw_probability(k) - draw_probability(k-1)``) is positive and
    concave (tapering) over the copy counts a sideboard card can actually run at (1-4) — this
    is the shape Unit B4 (a separate, later story) will feed into the ILP so a card's 2nd,
    3rd, 4th copy contributes progressively less to the objective, naturally discouraging
    over-committing slots to one answer.

    ``copies <= 0`` -> 0.0 (a card that isn't in the board can never be drawn — this is the
    natural "hard gate" a 0-copy element contributes nothing to ``ImpactBreakdown.score()``).
    ``copies`` and ``cards_seen`` are clamped to ``deck_size`` defensively (seeing more cards
    than exist in the deck, or running more copies than the deck size, isn't meaningful).
    """
    if copies <= 0:
        return 0.0

    copies = min(copies, deck_size)
    seen = min(max(cards_seen, 0), deck_size)
    if seen == 0:
        return 0.0

    total_hands = math.comb(deck_size, seen)
    if total_hands == 0:
        return 0.0

    miss_hands = math.comb(deck_size - copies, seen)
    return _clamp01(1.0 - miss_hands / total_hands)


def impact(
    hoser: "HoserCard",
    opp_archetype: str,
    *,
    opp_linchpins: "list[Linchpin]",
    my_vulnerability_tags: "frozenset[str]",
    my_colors: "frozenset[str]",
    copies: int,
    opp_cards: "object | None" = None,
) -> ImpactBreakdown:
    """Combine the four factors into an explainable ``ImpactBreakdown``.

    Pure orchestration — computes each factor exactly once and hands back the full
    breakdown (not just the product) so a caller (Unit B5's CLI render, a later story) can
    show the pilot WHY a card scored the way it did, not just the final number.
    """
    return ImpactBreakdown(
        centrality=centrality_factor(hoser, opp_archetype, opp_linchpins),
        symmetry=symmetry_factor(hoser, my_vulnerability_tags),
        castability=castability_factor(hoser, my_colors, opp_archetype, opp_cards),
        draw_prob=draw_probability(copies),
    )
