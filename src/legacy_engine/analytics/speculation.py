"""No-history speculation — forecast a zero-data card before tournament data exists.

Two independent estimates fused into a single, always-speculative SpeculativeForecast:

  (A) Intrinsic feature score — a transparent, additive heuristic over Card fields +
      interaction_facts + card_tags. Deliberately NOT a learned model. Each component
      is logged with its contribution so the number is fully auditable.

  (B) Analogous-card borrowed prior — k nearest existing cards by structural feature
      similarity (no oracle-text embedding). Their empirical card_value lift is borrowed
      as the prior for the new card, gated to established/evolving analogues only.

The central honesty guarantee: the forecast confidence is ALWAYS level="speculative",
source="heuristic". Borrowing an established neighbour's data does NOT upgrade the
forecast tier — the analogy itself is the unproven assumption. This is asserted in tests.

Lives in analytics/ but is NOT card_value.py: card_value.py is presence-correlational
over observed rounds; speculation.py is a deliberate, separately-labelled forecasting
path that consumes card_value read-only (for the analogue prior) and adds nothing to it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.card import Card

if TYPE_CHECKING:
    from legacy_engine.analytics.match_results import CardWinRates

# ── Similarity weights (auditable module constants — not inline magic numbers) ──

#: Colour-set Jaccard similarity weight.
W_COLOR = 0.25
#: CMC proximity weight: 1/(1+|cmc_a - cmc_b|).
W_CMC = 0.25
#: Shared card-tags role overlap (Jaccard).
W_ROLE = 0.25
#: Shared keyword Jaccard weight.
W_KEYWORD = 0.25

# Intrinsic score component weights
_CMC_WEIGHT = 0.35
_INTERACTION_WEIGHT = 0.30
_ROLE_WEIGHT = 0.25
_STAT_WEIGHT = 0.10

# Gate tier vocabulary (mirrors tier_for_sample thresholds; explicit here for readability)
_GATED_TIERS = frozenset({"established", "evolving"})

# Fusion weight: how much to lean on the borrowed prior when analogues are present.
# A good empirical neighbour signal (real data) outweighs pure heuristic intrinsic.
_PRIOR_BLEND = 0.65   # prior weight when gated analogues exist
_INTRINSIC_BLEND = 1.0 - _PRIOR_BLEND

# Keyword patterns extracted from oracle_text / type_line for similarity
_KEYWORD_PATTERNS = [
    "flying", "first strike", "double strike", "deathtouch", "lifelink",
    "vigilance", "trample", "haste", "flash", "hexproof", "indestructible",
    "islandwalk", "swampwalk", "forestwalk", "mountainwalk", "landwalk",
    "protection from", "cycling", "kicker", "flashback", "delve", "escape",
    "annihilator", "cascade", "convoke", "affinity", "phasing", "shadow",
    "threshold", "storm",
]
_KEYWORD_RE = re.compile("|".join(re.escape(k) for k in _KEYWORD_PATTERNS), re.IGNORECASE)

# PRE-DATA banner — must appear in every SpeculativeForecast.label
PRE_DATA_BANNER = "PRE-DATA FORECAST — no tournament data yet"


# ── Card-type bucket extraction ────────────────────────────────────────────────

def _type_bucket(type_line: str) -> str | None:
    """Return the primary card-type bucket for similarity matching.

    Returns one of: creature, instant, sorcery, enchantment, artifact, land, planeswalker,
    or None for non-gameplay / unrecognised type lines.
    """
    tl = (type_line or "").lower()
    for bucket in ("creature", "planeswalker", "enchantment", "artifact", "land", "instant", "sorcery"):
        if bucket in tl:
            return bucket
    return None


# ── Role-tag extraction ────────────────────────────────────────────────────────

def _role_tags(card: Card) -> frozenset[str]:
    """Return the union of card_tags roles and interaction_facts signals for a card.

    Gated-additive: interaction_facts is consumed when available; degrades to card_tags
    signal alone when the module is absent or raises. This is a pure function — no DB.
    """
    from legacy_engine.card_tags import is_free_spell, mana_base_tags, staple_role

    tags: set[str] = set()

    role = staple_role(card.name)
    if role:
        tags.add(role)

    if is_free_spell(card):
        tags.add("free_spell")

    mb = mana_base_tags(card)
    tags.update(mb)

    # Interaction facts — gated: if unavailable, degrade silently (no crash)
    try:
        from legacy_engine.interaction_facts import interaction_facts as _iacts

        facts = _iacts(card)
        if facts.free_cast:
            tags.add("free_cast")
        if facts.permanence == "static":
            tags.add("static_effect")
        if facts.affects in ("opponent-only", "targeted"):
            tags.add("one_sided_disruption")
        elif facts.affects == "symmetric":
            tags.add("symmetric_effect")
    except Exception:
        pass  # interaction_facts absent or errored — degrade to card_tags only

    return frozenset(tags)


def _keywords(card: Card) -> frozenset[str]:
    """Return the set of keyword cues present in oracle_text + type_line."""
    text = (card.oracle_text or "") + " " + (card.type_line or "")
    return frozenset(m.group(0).lower() for m in _KEYWORD_RE.finditer(text))


def _effective_cmc(card: Card) -> float:
    """Return the effective CMC: 0 for free spells, else card.cmc."""
    from legacy_engine.card_tags import is_free_spell

    return 0.0 if is_free_spell(card) else card.cmc


# ── Analogue (Unit 1 / child story) ──────────────────────────────────────────


@dataclass(frozen=True)
class Analogue:
    """A nearest existing card to the forecast target, with its similarity score.

    The empirical borrowed signal (card_value lift + tier) is attached by
    speculate_card (Unit 3) after the matcher runs, not by analogous_cards itself.

    ``similarity``: float in [0,1]. Transparent: each component's weight is an
    auditable module constant above.
    """

    card: str
    similarity: float          # [0,1]
    borrowed_lift: float | None = None    # card_value marginal lift, None until attached
    borrowed_tier: str | None = None      # tier of the analogue's card_value, None until attached


def _card_similarity(
    target: Card,
    candidate: Card,
    *,
    target_bucket: str | None,
    target_roles: frozenset[str],
    target_keywords: frozenset[str],
    target_cmc: float,
) -> float | None:
    """Compute structural similarity between target and candidate.

    Returns None when the card-type hard filter rejects the pair (different buckets).
    Returns a float in [0,1] otherwise — the weighted sum of colour Jaccard, CMC
    proximity, role overlap, and keyword overlap.
    """
    cand_bucket = _type_bucket(candidate.type_line)
    if target_bucket != cand_bucket:
        return None  # hard filter: different card-type buckets

    # Colour-set Jaccard
    target_colors = frozenset(target.colors)
    cand_colors = frozenset(candidate.colors)
    union_c = target_colors | cand_colors
    color_sim = len(target_colors & cand_colors) / len(union_c) if union_c else 1.0

    # CMC proximity
    cand_cmc = _effective_cmc(candidate)
    cmc_sim = 1.0 / (1.0 + abs(target_cmc - cand_cmc))

    # Role tag Jaccard
    cand_roles = _role_tags(candidate)
    union_r = target_roles | cand_roles
    role_sim = len(target_roles & cand_roles) / len(union_r) if union_r else 1.0

    # Keyword Jaccard
    cand_keywords = _keywords(candidate)
    union_k = target_keywords | cand_keywords
    kw_sim = len(target_keywords & cand_keywords) / len(union_k) if union_k else 1.0

    score = (
        W_COLOR * color_sim
        + W_CMC * cmc_sim
        + W_ROLE * role_sim
        + W_KEYWORD * kw_sim
    )
    # Clamp to [0,1] to be safe against floating-point edge cases
    return max(0.0, min(1.0, score))


def analogous_cards(
    target: Card,
    pool: Iterable[Card],
    *,
    k: int = 5,
) -> list[Analogue]:
    """Return the k nearest existing cards to target by transparent feature distance.

    Card-type bucket is a HARD filter: a new creature's analogues are creatures,
    never instants (a cross-bucket pair is excluded, not down-weighted). Within
    the same bucket the similarity is: colour Jaccard + CMC proximity + shared
    role tags + shared keywords — all weighted by auditable module constants.

    Pure function — no DB, no network. Deterministic: ties broken by card name
    ascending so ordering is stable across runs.

    Args:
        target: The new/zero-data card to find analogues for.
        pool: Iterable of existing cards to search. May include target itself
              (it will be excluded via name equality).
        k: Maximum number of analogues to return.

    Returns:
        List of Analogue objects sorted by (−similarity, name), length ≤ k.
        Empty list when pool is empty or no card clears the type-bucket filter.
    """
    target_bucket = _type_bucket(target.type_line)
    target_roles = _role_tags(target)
    target_keywords = _keywords(target)
    target_cmc = _effective_cmc(target)

    scored: list[tuple[float, str, Card]] = []
    for candidate in pool:
        if candidate.name == target.name:
            continue  # exclude self
        sim = _card_similarity(
            target,
            candidate,
            target_bucket=target_bucket,
            target_roles=target_roles,
            target_keywords=target_keywords,
            target_cmc=target_cmc,
        )
        if sim is None:
            continue  # hard-filtered out
        scored.append((sim, candidate.name, candidate))

    # Sort by (−similarity, name) for stable deterministic ordering
    scored.sort(key=lambda t: (-t[0], t[1]))

    return [
        Analogue(card=name, similarity=sim)
        for sim, name, _ in scored[:k]
    ]


# ── Intrinsic feature score (Unit 2) ─────────────────────────────────────────


@dataclass(frozen=True)
class IntrinsicScoreBreakdown:
    """Per-component contribution to the intrinsic score (auditable)."""

    cmc_band: float          # CMC heuristic contribution
    interaction: float       # interaction_facts contribution
    role_match: float        # card_tags role-match contribution
    stat_efficiency: float   # creature power-vs-CMC contribution


@dataclass(frozen=True)
class IntrinsicScore:
    """Heuristic, data-free "Legacy playability" score in [0, 1].

    Each component is broken out in ``breakdown`` so the composite is fully
    auditable — no black-box number. Always carries level="speculative",
    source="heuristic".
    """

    score: float
    breakdown: IntrinsicScoreBreakdown
    confidence: ConfidenceMetadata


def _cmc_band_score(card: Card) -> float:
    """CMC-band heuristic: Legacy rewards low cost. Free spells treated as CMC 0.

    Band:         score
      0 (free)    1.0
      1           0.9
      2           0.7
      3           0.5
      4           0.3
      5           0.15
      6+          0.05
    """
    cmc = _effective_cmc(card)
    bands = [(0, 1.0), (1, 0.9), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.15)]
    for threshold, score in bands:
        if cmc <= threshold:
            return score
    return 0.05


def _interaction_score(card: Card) -> float:
    """Interaction-profile score derived from interaction_facts.

    Consumes the DONE interaction_facts module read-only. Degrades to 0.0 (neutral)
    when interaction_facts is unavailable (gated-additive).

    High-value signals (add): free_cast, one-sided disruption, static lock effect.
    Low-value signals (subtract): symmetric self-harm.
    """
    try:
        from legacy_engine.interaction_facts import interaction_facts as _iacts

        facts = _iacts(card)
    except Exception:
        return 0.0  # degrade to neutral when unavailable

    score = 0.0

    if facts.free_cast:
        score += 0.4   # free spells are enormously powerful in Legacy

    if facts.affects in ("opponent-only", "targeted"):
        score += 0.2   # one-sided disruption is good
    elif facts.affects == "symmetric" and facts.graveyard_count_reduction:
        score -= 0.1   # symmetric self-harm (e.g. Tormod's Crypt in a graveyard deck)

    if facts.permanence == "static":
        score += 0.2   # static lock effects are high-impact in Legacy

    return max(-1.0, min(1.0, score))


def _role_match_score(card: Card) -> float:
    """Role-match score: does this card match known high-value Legacy roles?

    Reuses card_tags role detection + staple_role. Matching a curated staple role
    adds; interaction_facts grounding provides the gated-additive enhancement.
    """
    from legacy_engine.card_tags import is_free_spell, staple_role

    score = 0.0

    # Curated staple role (highest signal)
    role = staple_role(card.name)
    if role in ("free_interaction", "cantrip"):
        score += 0.5
    elif role in ("discard", "lock_piece", "fast_mana", "land_denial"):
        score += 0.3
    elif role in ("dual_land", "fetchland"):
        score += 0.2

    # Oracle-text cantrip signal (draw a card at no net card-disadvantage)
    if is_free_spell(card):
        score += 0.2

    oracle = (card.oracle_text or "").lower()

    # Cantrip pattern
    if re.search(r"draw a card|draw two cards", oracle):
        score += 0.15

    # Discard / hand disruption
    if re.search(r"discard|target player discards", oracle):
        score += 0.1

    # Counter magic
    if re.search(r"counter target|counter spell", oracle):
        score += 0.15

    # Tutor
    if re.search(r"search your library", oracle):
        score += 0.1

    return max(0.0, min(1.0, score))


def _stat_efficiency_score(card: Card) -> float:
    """Stat efficiency for creatures: power relative to CMC. Non-creatures return 0.

    A cheap beater (high power at low CMC) is historically strong in Legacy.
    Normalised to [0, 1].
    """
    if "Creature" not in (card.type_line or ""):
        return 0.0
    power_int = card.power_int()
    if power_int is None:
        return 0.0
    cmc = max(1.0, card.cmc)  # avoid division by zero; treat 0-CMC creatures as 1-CMC for ratio
    ratio = power_int / cmc
    # Normalise: ratio ≥ 3 → 1.0; ratio ~1 → ~0.3; <1 → near 0
    return max(0.0, min(1.0, ratio / 3.0))


def intrinsic_score(card: Card) -> IntrinsicScore:
    """Compute the intrinsic Legacy-playability score for a card.

    A transparent, additive rubric over Card fields + interaction_facts + card_tags.
    Each component is logged in the breakdown. Always confidence level="speculative",
    source="heuristic" — this is a data-free heuristic, not an empirical estimate.

    Degrades gracefully when interaction_facts returns nothing: the interaction
    component defaults to 0.0 (neutral), and the other components are unaffected.
    """
    cmc = _cmc_band_score(card)
    interaction = _interaction_score(card)
    role = _role_match_score(card)
    stat = _stat_efficiency_score(card)

    # Clamp interaction to non-negative before computing the composite so a penalised
    # card doesn't drag others below zero — the penalty is relative within a card.
    raw_interaction_contribution = _INTERACTION_WEIGHT * interaction
    composite = (
        _CMC_WEIGHT * cmc
        + raw_interaction_contribution
        + _ROLE_WEIGHT * role
        + _STAT_WEIGHT * stat
    )
    # Normalise: the max composite if all weights hit 1.0 is 1.0 (weights sum to 1).
    # Clamp to [0, 1] — interaction can go slightly negative.
    score = max(0.0, min(1.0, composite))

    breakdown = IntrinsicScoreBreakdown(
        cmc_band=_CMC_WEIGHT * cmc,
        interaction=raw_interaction_contribution,
        role_match=_ROLE_WEIGHT * role,
        stat_efficiency=_STAT_WEIGHT * stat,
    )
    confidence = ConfidenceMetadata(
        level="speculative",
        production="template-generated",
        source="heuristic",
    )
    return IntrinsicScore(score=score, breakdown=breakdown, confidence=confidence)


# ── Forecast fusion (Unit 3) ─────────────────────────────────────────────────


@dataclass(frozen=True)
class SpeculativeForecast:
    """Fused pre-data forecast for a zero-history card.

    Transparency: the breakdown shows which components contributed what.
    The analogues table shows the borrowed signal openly (not hidden behind one number).

    HONESTY GUARANTEE: ``confidence.level`` is ALWAYS ``"speculative"`` regardless of
    how established the analogue data is. Borrowing a neighbour's established tier does
    NOT upgrade the new card's confidence — the analogy itself is the unproven assumption.
    """

    card: str
    intrinsic: IntrinsicScore              # data-free rubric + breakdown
    analogues: tuple[Analogue, ...]        # k nearest cards, each with borrowed lift + tier
    borrowed_prior: float | None           # similarity-weighted analogue lift; None if no gated analogues
    forecast: float                        # fused estimate in [0,1] (roughly normalised lift above baseline)
    confidence: ConfidenceMetadata         # ALWAYS level="speculative", source="heuristic"
    label: str                             # e.g. PRE_DATA_BANNER + extra context


def speculate_card(
    target: Card,
    pool: Iterable[Card],
    card_winrates: "CardWinRates | None",
    *,
    k: int = 5,
    board: str = "main",
) -> SpeculativeForecast:
    """Forecast a new card's Legacy value before any tournament data exists.

    Step 1: compute analogous_cards (Unit 1 — pure feature similarity, no DB).
    Step 2: compute intrinsic_score (Unit 2 — pure heuristic, no DB).
    Step 3: attach empirical borrowed_lift to each analogue (card_value_marginal,
            read-only) gated to established/evolving analogues.
    Step 4: fuse intrinsic score and borrowed prior into a SpeculativeForecast.

    The confidence is ALWAYS level="speculative". If no analogue clears the
    established/evolving gate, borrowed_prior is None and the forecast equals
    the intrinsic score alone (honest degrade — identical to no-signal-skip).

    Args:
        target: The new/zero-data card to forecast.
        pool: The existing card pool for analogue matching.
        card_winrates: The CardWinRates corpus (for borrowing analogue lift).
                       May be None (degrades to intrinsic-only).
        k: Number of analogues to fetch.
        board: Board slot for card_value_marginal lookup (default "main").
    """
    from legacy_engine.analytics.card_value import card_value_marginal

    # ── Step 1: analogues ────────────────────────────────────────────────────
    raw_analogues = analogous_cards(target, pool, k=k)

    # ── Step 2: intrinsic score ──────────────────────────────────────────────
    intr = intrinsic_score(target)

    # ── Step 3: attach empirical signal to analogues, gate by tier ──────────
    gated: list[tuple[Analogue, float, float]] = []  # (analogue, similarity, lift)
    enriched: list[Analogue] = []

    for analogue in raw_analogues:
        if card_winrates is not None:
            cv = card_value_marginal(card_winrates, analogue.card, board)
            tier = cv.tier
            lift = cv.lift
        else:
            tier = "speculative"
            lift = 0.0

        enriched_analogue = Analogue(
            card=analogue.card,
            similarity=analogue.similarity,
            borrowed_lift=lift,
            borrowed_tier=tier,
        )
        enriched.append(enriched_analogue)

        if tier in _GATED_TIERS:
            gated.append((enriched_analogue, analogue.similarity, lift))

    # ── Step 4: fusion ──────────────────────────────────────────────────────
    if gated:
        total_sim = sum(sim for _, sim, _ in gated)
        if total_sim > 0:
            borrowed_prior: float | None = sum(
                (sim / total_sim) * lift for _, sim, lift in gated
            )
        else:
            borrowed_prior = 0.0

        # Blend intrinsic score + borrowed prior (both are "lift above baseline"
        # signals in roughly the same range [-0.5, 0.5]; intrinsic score is in
        # [0, 1] — we translate it to a lift by subtracting 0.5 so the blend
        # is in the same space, then report as-is for interpretability).
        # Design choice: keep both in their natural units and report the blend
        # as a [0, 1] score similar to the intrinsic score.
        intrinsic_as_lift = intr.score - 0.5  # centre: 0.5 is "neutral"
        blended_lift = _PRIOR_BLEND * borrowed_prior + _INTRINSIC_BLEND * intrinsic_as_lift
        forecast = max(0.0, min(1.0, blended_lift + 0.5))  # translate back to [0, 1]
        label = f"{PRE_DATA_BANNER} — {len(gated)} gated analogue(s) used as prior"
    else:
        borrowed_prior = None
        forecast = intr.score
        label = f"{PRE_DATA_BANNER} — intrinsic score only (no gated analogues)"

    confidence = ConfidenceMetadata(
        level="speculative",
        production="template-generated",
        source="heuristic",
    )

    return SpeculativeForecast(
        card=target.name,
        intrinsic=intr,
        analogues=tuple(enriched),
        borrowed_prior=borrowed_prior,
        forecast=forecast,
        confidence=confidence,
        label=label,
    )
