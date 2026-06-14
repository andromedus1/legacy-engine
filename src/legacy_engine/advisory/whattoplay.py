"""What-to-play advisor — proactivity, vulnerability tags, hate-equity, best-deck/best-call, plan-clash.

A shared ``_card_roles`` oracle-text classifier feeds four analytical surfaces:
  1. ``proactivity_score`` / ``ProactivityProfile`` — composition-derived [0,1] proactivity
  2. ``vulnerability_tags`` / ``vulnerability_tags_for_deck`` — archetype vulnerability classes
  3. ``hate_equity`` / ``covered_share`` / ``field_vulnerability_tags`` — sideboard-weighting input
  4. ``best_deck_vs_best_call`` / ``BestDeckCall`` — matchup-spread variance classification
  5. ``plan_clash`` — readable rule-table WHY strings layered over empirical matchup numbers

Heuristics are transparent curated regexes / thresholds (NOT a learned weight matrix) so every
output is auditable per PRINCIPLES #7.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass

import duckdb

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.analytics.matchup import MatchupMatrix
from legacy_engine.card_tags import is_free_spell, mana_base_tags, staple_role
from legacy_engine.ingestion.store import fetch_card, init_schema
from legacy_engine.models.card import Card

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Analytical role type alias
# ---------------------------------------------------------------------------

Role = str  # "counter" | "removal" | "stax" | "card_advantage" | "protection"
            # | "fast_mana" | "ritual" | "tutor" | "graveyard_recursion" | "storm"
            # | "threat"
            # (compact_combo is deck-level, not single-card)

# ---------------------------------------------------------------------------
# Curated threat overrides — Legacy staples whose proactive value raw stats miss
# (cheap planeswalkers, evasive threats, cards whose text understates them).
# The general signal (cmc ≤ 2 and power ≥ 2 creature) does the heavy lifting;
# this list handles edge cases (variable power, non-creature threats, etc.).
# ---------------------------------------------------------------------------

_THREAT_CARDS: frozenset[str] = frozenset(
    {
        # Creature threats — covered by the general rule too, listed for explicitness
        "Dragon's Rage Channeler",
        "Murktide Regent",
        "Tarmogoyf",
        "Nethergoyf",
        "Barrowgoyf",
        "Goblin Guide",
        "Death's Shadow",
        "Orcish Bowmasters",
        "Ajani Nacatl Pariah // Ajani, Nacatl Avenger",
        "Ajani Nacatl Pariah",
        "Amped Raptor",
        "Voice of Victory",
        # Ocelot Pride — low-MV token generator, proactive even at P=1
        "Ocelot Pride",
        # Cheap planeswalkers — proactive threats raw P/T stats cannot capture
        "Wrenn and Six",
        "Ragavan, Nimble Pilferer",
    }
)

# ---------------------------------------------------------------------------
# Unit 1 — Regex constants for _card_roles
# ---------------------------------------------------------------------------

_RE_COUNTER = re.compile(r"counter target", re.IGNORECASE)
_RE_REMOVAL = re.compile(
    r"destroy target|exile target (?:creature|permanent)|deals?\s+\d+\s+damage to",
    re.IGNORECASE,
)
_RE_RITUAL = re.compile(
    r"add \{[wubrgc]\}.*?\{[wubrgc]\}",
    re.IGNORECASE | re.DOTALL,
)
_RE_TUTOR = re.compile(
    r"search your library for (?:a|an|up to)",
    re.IGNORECASE,
)
_RE_STORM = re.compile(r"\bstorm\b", re.IGNORECASE)
_RE_GRAVEYARD = re.compile(
    # "return ... from [your/a/the] graveyard" or "from [a/the/your] graveyard to the battlefield"
    r"return .+? from (?:your|a|the) graveyard"
    r"|from (?:your|a|the) graveyard to (?:the battlefield|your hand|your library)"
    r"|put .+? from (?:a|any|your) graveyard (?:onto the battlefield|into your hand)",
    re.IGNORECASE,
)
_RE_PROTECTION = re.compile(
    r"hexproof|protection from|can't be countered",
    re.IGNORECASE,
)
_RE_STAX = re.compile(
    r"costs?\s*\{?\d+\}?\s*more|don't untap|players? can't",
    re.IGNORECASE,
)
_RE_CARD_ADVANTAGE = re.compile(
    r"draw (?:a card|\w+ cards)",
    re.IGNORECASE,
)

# Instant/Sorcery type check for ritual detection (net-positive mana)
_RE_INSTANT_SORCERY = re.compile(r"\b(?:Instant|Sorcery)\b", re.IGNORECASE)


def _card_roles(card: Card) -> set[str]:
    """Classify a Card into analytical roles via oracle-text regexes + card_tags + type_line.

    Reuses ``staple_role`` / ``is_free_spell`` / ``mana_base_tags``; adds regex detection
    for counter, removal, stax/taxing, card-advantage, protection, ritual, tutor, storm,
    graveyard-recursion.

    Pure function — auditable from card text.  A card may carry several roles.
    Lands return an empty set (rely on ``mana_base_tags`` at deck level for greedy-manabase).
    ``compact_combo`` is a deck-level signal (Unit 3), not a single-card role.
    """
    if card.is_land:
        return set()

    roles: set[str] = set()
    text = card.oracle_text or ""
    type_line = card.type_line or ""
    sr = staple_role(card.name)

    # --- fast_mana ---
    if sr == "fast_mana":
        roles.add("fast_mana")
    # Mox / Lotus style — is_free_spell covers pitch spells; also check produced mana
    if is_free_spell(card) and sr == "free_interaction":
        # free interaction cards (FoW, Daze, FoN) are NOT fast mana — they're counters
        pass
    # Check for artifact fast mana patterns from mana_base_tags on non-lands
    # (Ancient Tomb / City of Traitors are lands; Chrome Mox / Lotus Petal are not)
    if sr == "fast_mana" or (
        "Artifact" in type_line
        and re.search(r"add \{[cC]\}\{[cC]\}|add \{[wubrgWUBRG]\}", text)
        and not card.is_land
    ):
        roles.add("fast_mana")

    # --- counter ---
    if sr == "free_interaction":
        # free_interaction staples include FoW, Daze, FoN, FoV, Pyroblast, REB
        # FoV is removal/hate, not a counter — check oracle_text
        if _RE_COUNTER.search(text):
            roles.add("counter")
    if _RE_COUNTER.search(text):
        roles.add("counter")

    # --- removal ---
    if _RE_REMOVAL.search(text):
        roles.add("removal")

    # --- ritual (net-positive mana, instant/sorcery) ---
    if _RE_INSTANT_SORCERY.search(type_line) and _RE_RITUAL.search(text):
        roles.add("ritual")

    # --- tutor ---
    if _RE_TUTOR.search(text):
        roles.add("tutor")

    # --- storm ---
    if _RE_STORM.search(text):
        roles.add("storm")

    # --- graveyard_recursion ---
    if _RE_GRAVEYARD.search(text):
        roles.add("graveyard_recursion")

    # --- protection ---
    if _RE_PROTECTION.search(text):
        roles.add("protection")

    # --- stax / taxing ---
    if sr == "lock_piece" or _RE_STAX.search(text):
        roles.add("stax")

    # --- card_advantage ---
    if sr == "cantrip" or _RE_CARD_ADVANTAGE.search(text):
        roles.add("card_advantage")

    # --- discard (proactively strips opponent's hand — proactive disruption) ---
    if sr == "discard":
        roles.add("discard")

    # --- threat (aggressive/proactive creature or permanent threat) ---
    # General rule: a Creature at cmc ≤ 2 with power ≥ 2 is a proactive clock.
    # Curated override: _THREAT_CARDS catches threats raw stats miss (variable
    # power, token generators, cheap planeswalkers).
    if card.name in _THREAT_CARDS:
        roles.add("threat")
    elif (
        "Creature" in type_line
        and card.cmc <= 2.0
        and card.power_int() is not None
        and card.power_int() >= 2  # type: ignore[operator]
    ):
        roles.add("threat")

    return roles


# ---------------------------------------------------------------------------
# Unit 2 — proactivity_score + ProactivityProfile
# ---------------------------------------------------------------------------

# Sigmoid steepness constant: centered at avg_nonland_MV=2.0
_LOW_CURVE_K = 0.5

# Archetype fair/unfair classification for computed-vs-tag disagreement detection
# "fair" archetypes expected proactivity ≤ 0.55; "unfair" expected > 0.55
_FAIR_TAGS = frozenset({"control", "fair", "midrange"})
_UNFAIR_TAGS = frozenset({"combo", "storm", "reanimator", "unfair", "prison"})
_FAIR_THRESHOLD = 0.55  # above this is "unexpectedly proactive" for fair archetypes
_UNFAIR_THRESHOLD = 0.45  # below this is "unexpectedly reactive" for unfair archetypes


def _sigmoid(x: float, center: float = 2.0, k: float = _LOW_CURVE_K) -> float:
    """Sigmoid centered at ``center`` with steepness ``k``.  Returns [0,1]."""
    return 1.0 / (1.0 + math.exp((x - center) / k))


@dataclass
class ProactivityProfile:
    """Composition-derived proactivity for a deck.

    ``score`` is in [0,1] (0.5 when composition has no signals).
    ``proactive_mass`` / ``reactive_mass`` are the raw weighted signal sums.
    ``low_curve_score`` is the sigmoid over nonland average MV.
    ``findings`` records computed-vs-archetype-tag disagreements.
    """

    score: float
    proactive_mass: float
    reactive_mass: float
    low_curve_score: float
    findings: tuple[str, ...]


def _load_deck_cards(
    con: duckdb.DuckDBPyConnection,
    maindeck: dict[str, int],
) -> list[tuple[Card, int]]:
    """Resolve a name→count maindeck dict to (Card, count) pairs.

    Unknown card names are skipped with a ``log.warning``; the caller sees only
    cards that exist in the ``cards`` table.

    Reconstructs ``Card`` objects from the stored row, handling the joined-string
    serialization of ``colors`` and ``produced_mana`` (``store.load_cards`` stores
    them as concatenated strings: ``"".join(c.colors)``).
    """
    init_schema(con)
    result: list[tuple[Card, int]] = []
    for name, count in maindeck.items():
        row = fetch_card(con, name)
        if row is None:
            log.warning("whattoplay: unknown card %r — skipping", name)
            continue
        # Reconstruct colors and produced_mana from stored joined strings.
        # store.load_cards serializes: "".join(c.colors) → e.g. "UB" for ["U","B"].
        # We split back into single-char lists.
        # power and toughness are stored as plain VARCHAR strings (or NULL) — pass through as-is.
        colors_raw = row.get("colors") or ""
        produced_raw = row.get("produced_mana") or ""
        row["colors"] = list(colors_raw) if colors_raw else []
        row["produced_mana"] = list(produced_raw) if produced_raw else []
        # power/toughness: already plain strings from the DB; Card.model_validate handles None
        card = Card.model_validate(row)
        result.append((card, count))
    return result


def _avg_nonland_mv(cards_with_counts: list[tuple[Card, int]]) -> float:
    """Compute the average mana value across all non-land cards in the list.

    Returns 2.0 (sigmoid center) when there are no non-land cards, so the
    low_curve_score contributes a neutral 0.5 rather than skewing the score.
    This is the single shared computation used by both ``_proactivity_from_cards``
    (low_curve_score term) and ``_vulnerability_from_composition`` (low-curve tag),
    ensuring they fire on the same threshold.
    """
    total_count = 0
    total_mv = 0.0
    for card, count in cards_with_counts:
        if card.is_land:
            continue
        total_count += count
        total_mv += card.cmc * count
    return total_mv / total_count if total_count > 0 else 2.0


def _proactivity_from_cards(cards_with_counts: list[tuple[Card, int]]) -> ProactivityProfile:
    """Pure proactivity computation from (Card, count) pairs (no DB needed).

    Advisory-methods §4 formula (updated):
      proactive_mass = Σ count * (fast_mana + ritual + tutor + discard + threat)
                       + low_curve_score  (deck-level signal, added once)
      reactive_mass  = Σ count * (counter + removal + stax + card_advantage + protection)
      score = proactive / (proactive + reactive)   [0.5 when both zero]

    ``threat`` role: low-MV creature with a real body, or a card in _THREAT_CARDS.
    ``low_curve_score``: sigmoid over avg nonland MV (shared with vulnerability low-curve tag).
    """
    proactive_slots = 0.0
    reactive_slots = 0.0

    for card, count in cards_with_counts:
        if card.is_land:
            continue
        roles = _card_roles(card)
        for role in roles:
            if role in ("fast_mana", "ritual", "tutor", "discard"):
                proactive_slots += count
            elif role == "threat":
                # Threats are weighted 1.5× — a low-MV threat does double duty:
                # it advances the proactive plan AND forces reactive answers, making
                # each copy more impactful than a single ritual or discard slot.
                proactive_slots += count * 1.5
            if role in ("counter", "removal", "stax", "card_advantage", "protection"):
                reactive_slots += count

    # low_curve_score: deck-level signal (sigmoid over avg nonland MV), added once.
    # Uses the shared _avg_nonland_mv helper so this fires on the same threshold as
    # the "low-curve" vulnerability tag (avg MV < 2.0).
    avg_mv = _avg_nonland_mv(cards_with_counts)
    low_curve_score = _sigmoid(avg_mv)
    proactive_mass = proactive_slots + low_curve_score
    reactive_mass = reactive_slots

    if proactive_mass + reactive_mass == 0:
        score = 0.5
    else:
        score = proactive_mass / (proactive_mass + reactive_mass)

    score = max(0.0, min(1.0, score))
    return ProactivityProfile(
        score=score,
        proactive_mass=proactive_mass,
        reactive_mass=reactive_mass,
        low_curve_score=low_curve_score,
        findings=(),
    )


def proactivity_score(
    con: duckdb.DuckDBPyConnection,
    maindeck: dict[str, int],
    *,
    archetype_tag: str | None = None,
) -> ProactivityProfile:
    """Composition-derived proactivity in [0,1] (advisory-methods §4 formula).

    Resolves cards via ``store.fetch_card``, delegates to ``_proactivity_from_cards``,
    then checks computed score against ``archetype_tag`` and appends findings on
    disagreement.
    """
    cards_with_counts = _load_deck_cards(con, maindeck)
    profile = _proactivity_from_cards(cards_with_counts)

    findings: list[str] = list(profile.findings)
    if archetype_tag is not None:
        tag_lower = archetype_tag.lower()
        if any(t in tag_lower for t in _FAIR_TAGS) and profile.score > _FAIR_THRESHOLD:
            findings.append(
                f"Computed proactivity {profile.score:.2f} is unexpectedly high for a "
                f"'{archetype_tag}' archetype (expected ≤{_FAIR_THRESHOLD}); "
                "deck may be mis-labeled or unusually proactive."
            )
        elif any(t in tag_lower for t in _UNFAIR_TAGS) and profile.score < _UNFAIR_THRESHOLD:
            findings.append(
                f"Computed proactivity {profile.score:.2f} is unexpectedly low for a "
                f"'{archetype_tag}' archetype (expected >{_UNFAIR_THRESHOLD}); "
                "deck may be mis-labeled or unusually reactive."
            )

    return ProactivityProfile(
        score=profile.score,
        proactive_mass=profile.proactive_mass,
        reactive_mass=profile.reactive_mass,
        low_curve_score=profile.low_curve_score,
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Unit 3 — Vulnerability tags
# ---------------------------------------------------------------------------

VulnerabilityTag = str  # graveyard-reliant | combo | low-curve | greedy-manabase
                        # | creature-based | low-interaction | storm-reliant | ramp

# Thresholds for vulnerability classification (documented, module constants)
_GY_RECURSION_DENSITY = 0.08   # graveyard_recursion slots / total maindeck >= threshold → gy-reliant
_CREATURE_DENSITY = 0.25       # creature slots / total maindeck >= threshold → creature-based
_LOW_INTERACTION_MAX = 0.08    # (counter + removal) / total <= threshold → low-interaction
_COMBO_AVG_MV_MAX = 2.5        # avg nonland MV must be below this for combo tag
_COMBO_TUTOR_DENSITY = 0.05    # tutor slots / total maindeck >= threshold for combo
_GREEDY_MANABASE_MIN_FAST = 4  # cards with fast_mana/dual land tags >= threshold → greedy manabase
_GREEDY_NONBASIC_MIN = 8       # nonbasic lands count >= threshold → greedy manabase
_STORM_DENSITY = 0.08          # storm slots / total nonland >= threshold → storm-reliant
                               # (density gate kills false positives from stray storm cards in aggregates)
_RAMP_BIGMANA_LAND_MIN = 4     # big-mana land copies >= threshold → ramp tag
                               # (Urzatron: 12 pieces; Cloudpost: 4+; Eldrazi: 4+)

# Named lands that are diagnostic of colorless big-mana / ramp strategies.
# Urzatron pieces, Cloudpost/Glimmerpost, Eldrazi accelerants.
# Detection by name (not oracle text) — these cards have no common textual signature.
# Kept tight to archetypes that specifically exploit colorless ramp (not general fast-mana lands
# like Ancient Tomb, which already seed greedy-manabase via fast_mana_cards).
_BIGMANA_LAND_NAMES: frozenset[str] = frozenset({
    # Urzatron
    "Urza's Tower",
    "Urza's Mine",
    "Urza's Power Plant",
    # Cloudpost / Loam-Post
    "Cloudpost",
    "Glimmerpost",
    "Vesuva",        # used to copy Cloudpost / Urza pieces in those strategies
    # Eldrazi accelerants (lands)
    "Eldrazi Temple",
    "Eye of Ugin",
})


def _archetype_composition(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    provenance: str | None = None,
) -> dict[str, int]:
    """Aggregate the most-common cards across corpus decks labeled ``archetype``.

    Returns a name→total_count dict (sum of copies across all decks of this archetype).
    Only maindeck cards are considered (board='main').
    """
    init_schema(con)
    if provenance is not None:
        rows = con.execute(
            """
            SELECT dc.name, SUM(dc.count) AS total
            FROM deck_cards dc
            JOIN decks d ON dc.tournament_id = d.tournament_id AND dc.deck_idx = d.deck_idx
            JOIN tournaments t ON d.tournament_id = t.id
            WHERE d.archetype = ?
              AND dc.board = 'main'
              AND t.provenance = ?
            GROUP BY dc.name
            ORDER BY total DESC
            """,
            [archetype, provenance],
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT dc.name, SUM(dc.count) AS total
            FROM deck_cards dc
            JOIN decks d ON dc.tournament_id = d.tournament_id AND dc.deck_idx = d.deck_idx
            WHERE d.archetype = ?
              AND dc.board = 'main'
            GROUP BY dc.name
            ORDER BY total DESC
            """,
            [archetype],
        ).fetchall()
    return {name: int(total) for name, total in rows}


def _vulnerability_from_composition(
    con: duckdb.DuckDBPyConnection,
    composition: dict[str, int],
) -> frozenset[str]:
    """Derive vulnerability tags from a name→count composition aggregate.

    Tag rules (advisory-methods §4, updated):
    - graveyard-reliant: graveyard_recursion density ≥ threshold
    - storm-reliant: storm slots / total nonland ≥ _STORM_DENSITY threshold
      (density gate — presence alone caused false positives on aggregated compositions
       where a stray storm card appeared in an otherwise non-storm archetype aggregate)
    - combo: low avg MV + tutors + storm-or-graveyard signal
    - low-curve: avg nonland MV < 2.0 (same computation as proactivity low_curve_score)
    - creature-based: creature slot density ≥ threshold
    - greedy-manabase: high fast/dual lands + nonbasic heavy
    - low-interaction: low (counter + removal) density
    """
    if not composition:
        return frozenset()

    total_cards = sum(composition.values())
    gy_slots = 0
    storm_slots = 0
    tutor_slots = 0
    counter_removal_slots = 0
    creature_slots = 0
    fast_mana_cards = 0
    nonbasic_land_count = 0
    bigmana_land_count = 0   # copies of diagnostic big-mana / ramp lands
    total_nonland = 0
    total_nonland_mv = 0.0

    for name, count in composition.items():
        row = fetch_card(con, name)
        if row is None:
            continue
        colors_raw = row.get("colors") or ""
        produced_raw = row.get("produced_mana") or ""
        row["colors"] = list(colors_raw)
        row["produced_mana"] = list(produced_raw)
        card = Card.model_validate(row)
        roles = _card_roles(card)

        if card.is_land:
            mb_tags = mana_base_tags(card)
            if mb_tags & {"dual", "fast_mana_land", "fetchland"}:
                fast_mana_cards += count
            # Nonbasic land detection: not a Plains/Island/Swamp/Mountain/Forest basic
            type_line_lower = (card.type_line or "").lower()
            if "land" in type_line_lower and not (
                "basic" in type_line_lower
                or card.name in {"Plains", "Island", "Swamp", "Mountain", "Forest"}
            ):
                nonbasic_land_count += count
            # Big-mana / ramp land detection: named diagnostic lands (Urzatron, Cloudpost, Eldrazi)
            if card.name in _BIGMANA_LAND_NAMES:
                bigmana_land_count += count
        else:
            total_nonland += count
            total_nonland_mv += card.cmc * count
            # Creature detection via type_line
            if "Creature" in (card.type_line or ""):
                creature_slots += count

        # Role tallies (apply to all cards)
        if "graveyard_recursion" in roles:
            gy_slots += count
        if "storm" in roles:
            storm_slots += count
        if "tutor" in roles:
            tutor_slots += count
        if "counter" in roles or "removal" in roles:
            counter_removal_slots += count
        if "fast_mana" in roles:
            fast_mana_cards += count

    # avg nonland MV — shared threshold with proactivity low_curve_score sigmoid center
    avg_mv = total_nonland_mv / total_nonland if total_nonland > 0 else 3.0
    tags: set[str] = set()

    # graveyard-reliant
    if total_cards > 0 and gy_slots / total_cards >= _GY_RECURSION_DENSITY:
        tags.add("graveyard-reliant")

    # storm-reliant: density gate (not mere presence) to avoid false positives on aggregates
    if total_nonland > 0 and storm_slots / total_nonland >= _STORM_DENSITY:
        tags.add("storm-reliant")

    # combo: low avg MV + tutors + some broken signal (storm/gy/fast mana)
    has_broken_signal = storm_slots > 0 or (
        total_cards > 0 and gy_slots / total_cards >= _GY_RECURSION_DENSITY
    ) or fast_mana_cards >= _GREEDY_MANABASE_MIN_FAST
    if (
        avg_mv < _COMBO_AVG_MV_MAX
        and total_cards > 0
        and tutor_slots / total_cards >= _COMBO_TUTOR_DENSITY
        and has_broken_signal
    ):
        tags.add("combo")

    # low-curve: uses the same avg nonland MV computation as proactivity low_curve_score
    if avg_mv < 2.0:
        tags.add("low-curve")

    # creature-based
    if total_cards > 0 and creature_slots / total_cards >= _CREATURE_DENSITY:
        tags.add("creature-based")

    # greedy-manabase
    if fast_mana_cards >= _GREEDY_MANABASE_MIN_FAST or nonbasic_land_count >= _GREEDY_NONBASIC_MIN:
        tags.add("greedy-manabase")

    # low-interaction
    if total_cards > 0 and counter_removal_slots / total_cards <= _LOW_INTERACTION_MAX:
        tags.add("low-interaction")

    # ramp (big-mana): significant density of colorless big-mana lands (Urzatron / Cloudpost / Eldrazi)
    # Gated-additive: fires only when bigmana_land_count clears the threshold; no other tag is affected.
    if bigmana_land_count >= _RAMP_BIGMANA_LAND_MIN:
        tags.add("ramp")

    return frozenset(tags)


def vulnerability_tags(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
) -> frozenset[str]:
    """Derive the archetype's vulnerability classes from its aggregate composition.

    Derived from all corpus decks labeled ``archetype`` (deck_cards ⋈ decks).
    """
    composition = _archetype_composition(con, archetype)
    if not composition:
        log.warning("vulnerability_tags: no corpus decks for archetype %r", archetype)
        return frozenset()
    return _vulnerability_from_composition(con, composition)


def vulnerability_tags_for_deck(
    con: duckdb.DuckDBPyConnection,
    maindeck: dict[str, int],
) -> frozenset[str]:
    """Same vulnerability classification over a specific decklist."""
    return _vulnerability_from_composition(con, maindeck)


# ---------------------------------------------------------------------------
# Unit 4 — Hate-equity (coverage)
# ---------------------------------------------------------------------------


def hate_equity(
    field: FieldDistribution,
    archetype_tags: dict[str, frozenset[str]],
) -> dict[str, float]:
    """Per vulnerability tag, the field share attacking it.

    For each vulnerability tag, sums field_share(a) across all archetypes ``a``
    that carry that tag.  Per-tag equity is a direct share sum.

    Coverage semantics: for a *package* spanning multiple tags, the combined
    equity is the union of field share attacked — use ``covered_share`` for that
    (a deck carrying two attacked tags is counted once, not twice).
    """
    equity: dict[str, float] = {}
    for archetype, share in field.shares.items():
        tags = archetype_tags.get(archetype, frozenset())
        for tag in tags:
            equity[tag] = equity.get(tag, 0.0) + share
    return equity


def covered_share(
    field: FieldDistribution,
    archetypes_attacked: set[str],
) -> float:
    """Field share attacked by a hate package targeting ``archetypes_attacked``.

    Union-of-shares semantics: each archetype in the field is counted at most
    once, regardless of how many tags it carries that overlap with the package.
    This avoids double-counting multi-tag archetypes.
    """
    total = 0.0
    for archetype in archetypes_attacked:
        total += field.shares.get(archetype, 0.0)
    return total


def field_vulnerability_tags(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
) -> dict[str, frozenset[str]]:
    """Convenience: ``vulnerability_tags(a)`` for every archetype in the field."""
    return {archetype: vulnerability_tags(con, archetype) for archetype in field.shares}


# ---------------------------------------------------------------------------
# Unit 5 — best-deck vs best-call
# ---------------------------------------------------------------------------


@dataclass
class BestDeckCall:
    """Classification of an archetype's matchup profile.

    ``label`` is one of "BEST_DECK" | "BEST_CALL" | "neither".
    ``spread_variance`` is the variance of win-rates (p_shrunk) across the known
    non-mirror cells in the archetype's row.
    ``field_weighted_mean`` is Σ field_share(b) * p_shrunk(a,b) over known cells.
    ``unweighted_mean`` is the simple mean across known cells.
    ``best_deck_score`` is the continuous robust floor ``clamp(unweighted_mean −
    √spread_variance, 0, 1)`` — high when the deck is good across the field AND
    not spiky.  ``best_call_score`` is ``field_weighted_mean`` — how good the deck
    is vs THIS field.  The two scores give a gradient so near-threshold decks read
    as borderline rather than as a binary label flip.
    """

    archetype: str
    label: str  # "BEST_DECK" | "BEST_CALL" | "neither"
    spread_variance: float
    field_weighted_mean: float
    unweighted_mean: float
    best_deck_score: float = 0.0  # robust floor: clamp(unweighted_mean − √variance, 0, 1)
    best_call_score: float = 0.0  # field_weighted_mean — good-vs-THIS-field


def best_deck_vs_best_call(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    archetype: str,
    *,
    spread_hi: float = 0.02,
    mean_hi: float = 0.52,
) -> BestDeckCall:
    """Classify via matchup-spread variance.

    BEST_DECK: low spread (variance ≤ spread_hi) AND high unweighted mean (≥ mean_hi)
               → robust across the field.
    BEST_CALL: high field-weighted mean (≥ mean_hi) but not robust-strong
               → field-specific pick (preys on the current meta).  NOTE: this no
               longer requires high variance — a consistent, field-favored deck
               (low spread, high field-weighted mean, sub-threshold unweighted mean)
               is correctly a BEST_CALL, not "neither".  Removing that variance gate
               is the cliff fix (Death & Taxes used to fall through to "neither").
    neither: field-weighted mean below threshold and not robust-strong.

    Also reports continuous ``best_deck_score`` / ``best_call_score`` for a gradient
    read independent of the discrete label.

    Uses ``p_shrunk`` of known (n>0, non-mirror) cells in the archetype's row.
    Missing archetype → returns a "neither" cell with zeroed stats and a warning.
    """
    if archetype not in matrix.archetypes:
        log.warning("best_deck_vs_best_call: archetype %r not in matrix", archetype)
        return BestDeckCall(
            archetype=archetype,
            label="neither",
            spread_variance=0.0,
            field_weighted_mean=0.0,
            unweighted_mean=0.0,
            best_deck_score=0.0,
            best_call_score=0.0,
        )

    # Collect known non-mirror cells — restrict to display-grade (n>=30) so the
    # BEST_DECK / BEST_CALL classification is data-driven (n<30 speculative cells
    # are not eligible to drive the label).
    winrates: list[float] = []
    weighted_sum = 0.0
    weight_total = 0.0
    low_n_skipped: int = 0

    for opp in matrix.archetypes:
        if opp == archetype:
            continue
        cell = matrix.cells.get((archetype, opp))
        if cell is None or cell.n == 0 or cell.p_shrunk is None:
            continue
        if not cell.display:
            # n < 30 — speculative; exclude from classification
            low_n_skipped += 1
            continue
        winrates.append(cell.p_shrunk)
        w = field.shares.get(opp, 0.0)
        weighted_sum += w * cell.p_shrunk
        weight_total += w

    if low_n_skipped:
        log.debug(
            "best_deck_vs_best_call(%r): skipped %d cell(s) with n<30 (speculative)",
            archetype, low_n_skipped,
        )

    if not winrates:
        return BestDeckCall(
            archetype=archetype,
            label="neither",
            spread_variance=0.0,
            field_weighted_mean=0.0,
            unweighted_mean=0.0,
            best_deck_score=0.0,
            best_call_score=0.0,
        )

    unweighted_mean = sum(winrates) / len(winrates)
    field_weighted_mean = weighted_sum / weight_total if weight_total > 0 else unweighted_mean
    variance = sum((r - unweighted_mean) ** 2 for r in winrates) / len(winrates)

    # De-cliffed label: BEST_CALL no longer requires high variance, so a consistent,
    # field-favored deck (low spread, field-weighted mean ≥ threshold, but unweighted
    # mean below threshold) is correctly a BEST_CALL rather than "neither".
    if variance <= spread_hi and unweighted_mean >= mean_hi:
        label = "BEST_DECK"
    elif field_weighted_mean >= mean_hi:
        label = "BEST_CALL"
    else:
        label = "neither"

    # Continuous gradient scores (independent of the discrete label).
    best_deck_score = max(0.0, min(1.0, unweighted_mean - math.sqrt(variance)))
    best_call_score = field_weighted_mean

    return BestDeckCall(
        archetype=archetype,
        label=label,
        spread_variance=variance,
        field_weighted_mean=field_weighted_mean,
        unweighted_mean=unweighted_mean,
        best_deck_score=best_deck_score,
        best_call_score=best_call_score,
    )


# ---------------------------------------------------------------------------
# Unit 6 — plan_clash WHY strings
# ---------------------------------------------------------------------------


def plan_clash(
    deck_profile: ProactivityProfile,
    opp_profile: ProactivityProfile,
    cell,
    *,
    hate_present: bool = False,
) -> tuple[str, bool]:
    """Return (why_string, heuristic_data_disagreement).

    Rule table (advisory-methods §4) layered over the empirical ``cell``:
    - proactive vs reactive (low hate) → proactive wins on tempo
    - proactive vs reactive (hate/protection present) → reactive wins on answers
    - proactive vs proactive → faster clock wins (lower avg MV proxy = score)
    - reactive vs reactive → more card advantage wins

    ``heuristic_data_disagreement`` is True when the heuristic favorite contradicts
    ``cell.p_shrunk`` (heuristic says A but cell shows p<0.5 for A).
    Possible confound: pilot skill, low-n sample.
    """
    deck_score = deck_profile.score
    opp_score = opp_profile.score

    # Classify matchup archetype
    PROACTIVE_THRESHOLD = 0.58
    REACTIVE_THRESHOLD = 0.45

    deck_proactive = deck_score >= PROACTIVE_THRESHOLD
    opp_proactive = opp_score >= PROACTIVE_THRESHOLD
    deck_reactive = deck_score <= REACTIVE_THRESHOLD
    opp_reactive = opp_score <= REACTIVE_THRESHOLD

    # Determine heuristic winner (True = deck wins, False = opp wins, None = unclear)
    heuristic_deck_favored: bool | None

    if deck_proactive and opp_reactive:
        if hate_present:
            why = (
                f"Proactive deck (score={deck_score:.2f}) faces a reactive deck (score="
                f"{opp_score:.2f}) with hate/protection — reactive answers likely neutralize the "
                "proactive plan; reactive deck favored."
            )
            heuristic_deck_favored = False
        else:
            why = (
                f"Proactive deck (score={deck_score:.2f}) vs reactive deck (score="
                f"{opp_score:.2f}) without hate — proactive deck wins on tempo."
            )
            heuristic_deck_favored = True
    elif deck_reactive and opp_proactive:
        if hate_present:
            why = (
                f"Reactive deck (score={deck_score:.2f}) with hate/protection vs proactive deck "
                f"(score={opp_score:.2f}) — reactive answers likely neutralize the proactive plan; "
                "reactive deck favored."
            )
            heuristic_deck_favored = True
        else:
            why = (
                f"Reactive deck (score={deck_score:.2f}) vs proactive deck (score="
                f"{opp_score:.2f}) without hate — proactive opponent wins on tempo."
            )
            heuristic_deck_favored = False
    elif deck_proactive and opp_proactive:
        if deck_score > opp_score:
            why = (
                f"Both decks proactive (deck={deck_score:.2f}, opp={opp_score:.2f}) — "
                "faster clock favors the deck with lower curve/higher proactivity."
            )
            heuristic_deck_favored = True
        elif opp_score > deck_score:
            why = (
                f"Both decks proactive (deck={deck_score:.2f}, opp={opp_score:.2f}) — "
                "faster clock favors the opponent (higher proactivity score)."
            )
            heuristic_deck_favored = False
        else:
            why = (
                f"Both decks equally proactive (score={deck_score:.2f}) — "
                "faster clock race; outcome unclear from composition alone."
            )
            heuristic_deck_favored = None
    elif deck_reactive and opp_reactive:
        if deck_profile.reactive_mass > opp_profile.reactive_mass:
            why = (
                f"Both decks reactive (deck={deck_score:.2f}, opp={opp_score:.2f}) — "
                "more card advantage / answers favors the deck with higher reactive mass."
            )
            heuristic_deck_favored = True
        elif opp_profile.reactive_mass > deck_profile.reactive_mass:
            why = (
                f"Both decks reactive (deck={deck_score:.2f}, opp={opp_score:.2f}) — "
                "more card advantage / answers favors the opponent (higher reactive mass)."
            )
            heuristic_deck_favored = False
        else:
            why = (
                f"Both decks equally reactive (score={deck_score:.2f}) — "
                "mirror-style matchup; card advantage edge unclear from composition alone."
            )
            heuristic_deck_favored = None
    else:
        # Mixed / midrange matchup
        why = (
            f"Mixed proactivity matchup (deck={deck_score:.2f}, opp={opp_score:.2f}) — "
            "no clear heuristic advantage; consult empirical matchup data."
        )
        heuristic_deck_favored = None

    # Check heuristic vs data disagreement
    disagreement = False
    if heuristic_deck_favored is not None and cell is not None:
        p = getattr(cell, "p_shrunk", None)
        if p is not None:
            if heuristic_deck_favored and p < 0.5:
                disagreement = True
                why += (
                    f" [NOTE: heuristic favors this deck but empirical cell shows p_shrunk={p:.2f} "
                    "— possible pilot-skill or low-n confound.]"
                )
            elif not heuristic_deck_favored and p > 0.5:
                disagreement = True
                why += (
                    f" [NOTE: heuristic favors the opponent but empirical cell shows p_shrunk={p:.2f} "
                    "— possible pilot-skill or low-n confound.]"
                )

    return why, disagreement
