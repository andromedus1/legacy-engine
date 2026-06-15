"""Acquisition advisor — ranked, priced buy list for a target field/board.

Built objective-search-split style (pattern: ``objective-search-split``):
  - ``acquire_plan`` is the orchestrator that does one heavy DB scan
    (``compute_card_winrates`` + ``card_frequencies`` per board) and hands
    plain dicts to the pure core.
  - ``_rank_acquisitions`` is the DB-free pure ranking function: takes plain
    dicts + an injected ``CollectionView`` + an injected ``price_fn``.
    Fully unit-testable with hand-built dicts + a stub ``price_fn``.

Gated-additive degradations:
  - No price source (``price_fn=None``) → all prices ``None``, ``total_cost=None``,
    ranking by impact only; every buy row flagged ``price: unavailable``.
  - No win-rate signal → ``impact_basis="adoption (no win-rate signal)"``,
    impact = field_adoption × archetype_relevance (same honesty as ``tune``'s
    ``no-signal-skip``).
  - Over-cover factor / overprice factor are curated constants surfaced in
    ``heuristic_note``; flags are advisory and labeled, not silent auto-cuts.

Named regressions covered by tests:
  - Defense Grid / Chalice: field-good but not owned / low archetype relevance
    → sink in the ranking + clearly flagged not-owned.
  - Dismember: $33 Secret Lair vs $2 NPH → overpriced-printing flag fires.
  - Graveyard-hate over-cover: >2× field demand → redundant-own flag fires.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    import duckdb

    from legacy_engine.advisory.collection import CollectionView
    from legacy_engine.advisory.field import FieldDistribution

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Curated heuristic constants (labeled — same discipline as sideboard swings)
# ---------------------------------------------------------------------------

# Cards owned at > (over_cover_factor × field_demand) copies are flagged redundant.
_DEFAULT_OVER_COVER_FACTOR: float = 2.0

# Owned/default printing is flagged overpriced when:
#   owned_price >= overprice_factor × cheapest_price  AND  cheapest_price exists.
# 3.0 catches $33 SL vs $1–2 Dismember; $2 vs $2 is NOT flagged (ratio = 1.0 < 3.0).
_DEFAULT_OVERPRICE_FACTOR: float = 3.0

_HEURISTIC_NOTE = (
    "over_cover_factor=2.0 and overprice_factor=3.0 are curated heuristic constants. "
    "Flags are advisory (labeled), not auto-cuts. "
    "Impact = field_relevance × archetype_relevance; "
    "field_relevance falls back to field-adoption when win-rate signal is absent."
)

# ---------------------------------------------------------------------------
# Output records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BuyItem:
    """One entry in the buy list.

    ``impact``: field_relevance × archetype_relevance (higher = buy first).
    ``impact_basis``: "win-rate" | "adoption (no win-rate signal)".
    ``price``: cheapest legal printing USD (None when no price source).
    ``slots_into``: board location / covered element.
    ``replaces``: flex card displaced (None when data is thin or not applicable).
    ``notes``: advisory annotations (e.g. "anti-synergy: low-curve deck").
    """

    card: str
    acquire_copies: int
    impact: float
    impact_basis: str
    field_relevance: float
    archetype_relevance: float
    price: Optional[float]
    price_source: Optional[str]
    slots_into: str
    replaces: Optional[str]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class CollectionFlag:
    """A collection health finding (redundant / over-quantity / overpriced)."""

    card: str
    kind: str   # "redundant-own" | "over-quantity" | "overpriced-printing"
    detail: str


@dataclass(frozen=True)
class AcquisitionPlan:
    """Complete output of the acquisition advisor.

    ``buy_list``: cards to acquire, ranked by impact DESC, price ASC tie-break.
    ``flags``:    collection health findings (over-cover, overpriced printings).
    ``total_cost``: Σ price×copies; None when any buy is unpriced and source absent.
    ``impact_basis``: overall label for the impact column.
    ``window``: (since, until) used for win-rate data.
    ``heuristic_note``: surfaced constants reminder.
    ``warnings``: any degradation / data-quality notes.
    """

    buy_list: tuple[BuyItem, ...]
    flags: tuple[CollectionFlag, ...]
    total_cost: Optional[float]
    field_source: str
    impact_basis: str
    window: tuple[str | None, str | None]
    heuristic_note: str
    warnings: tuple[str, ...]


# ---------------------------------------------------------------------------
# split_recommendation — owned/acquire post-filter (consumer policy)
# ---------------------------------------------------------------------------

def split_recommendation(
    cards: dict[str, int],
    cv: "CollectionView",
) -> tuple[dict[str, int], dict[str, int]]:
    """Split a recommended card dict into (play_owned, acquire) partitions.

    ``play_owned``: cards where ``owned_qty >= recommended_copies``.
    ``acquire``:    cards where the user needs to buy at least 1 copy.

    This is the consumer-facing post-filter for ``--owned-only`` mode.
    The optimizer/recommender are never filtered by ownership (that would
    break the byte-identical contract and change recommendations).  The
    CLI ``--owned-only`` flag simply renders only ``play_owned`` and notes
    the suppressed acquire-list count.
    """
    play_owned: dict[str, int] = {}
    acquire: dict[str, int] = {}
    for card, copies in cards.items():
        if cv.owned_qty(card) >= copies:
            play_owned[card] = copies
        else:
            acquire[card] = copies
    return play_owned, acquire


# ---------------------------------------------------------------------------
# _rank_acquisitions — pure DB-free core (the unit-test surface)
# ---------------------------------------------------------------------------

def _rank_acquisitions(
    candidates: dict[str, int],          # card → recommended_copies (target board)
    field_weighted: dict[str, float],     # card → field-weighted value (0.0 when thin)
    archetype_incl: dict[str, float],     # card → archetype inclusion_pct (0.0 if absent)
    field_adoption: dict[str, float],     # card → Σ_opp shares * inclusion_pct (fallback)
    owned: "CollectionView",
    price_fn: "Callable[[str], Optional[object]] | None",
    *,
    slots_into_map: dict[str, str] | None = None,   # card → board slot description
    replaces_map: dict[str, str | None] | None = None,  # card → displaced card name
    over_cover_factor: float = _DEFAULT_OVER_COVER_FACTOR,
    field_source: str = "unknown",
    window: tuple[str | None, str | None] = (None, None),
    # Per-tag field demand for over-cover check: tag → field-weighted demand fraction.
    # Built by the orchestrator from HOSER_CATALOG + field shares.
    tag_field_demand: dict[str, float] | None = None,
    # Per-card tag map for over-cover: card → frozenset[tag].
    card_tags: dict[str, frozenset[str]] | None = None,
) -> AcquisitionPlan:
    """Pure ranking core: no DB, no IO.

    **Impact score**: ``impact = field_relevance × archetype_relevance``.

    - ``field_relevance``: ``field_weighted[card]`` when non-zero (win-rate basis);
      else ``field_adoption[card]`` (adoption fallback, labeled).
    - ``archetype_relevance``: ``archetype_incl[card]``.
    - ``impact_basis``: "win-rate" when any card has a non-zero ``field_weighted``
      value; "adoption (no win-rate signal)" otherwise.

    Only cards with ``to_acquire > 0`` enter the buy list.  Cards the user
    already fully owns are excluded (they may appear in the flags section as
    over-quantity or overpriced findings instead).

    Ranking: impact DESC, price ASC (cheaper buys first on ties), card name ASC
    (final lex tie-break for determinism).

    Flags (this core emits ``over-quantity`` only; ``overpriced-printing`` is emitted by the
    orchestrator ``acquire_plan``, which owns the price comparison):
    - ``over-quantity``: owned_qty > recommended_copies AND (tag-level field
      demand is over-covered at over_cover_factor×demand OR raw per-card over-cover).
    """
    warnings: list[str] = []

    # ── Determine impact basis ──────────────────────────────────────────────
    has_winrate_signal = any(v != 0.0 for v in field_weighted.values())
    if has_winrate_signal:
        impact_basis_global = "win-rate"
    else:
        impact_basis_global = "adoption (no win-rate signal)"
        if not field_adoption:
            warnings.append(
                "no win-rate signal and no adoption data — all impact scores are 0.0; "
                "ranking is by archetype relevance only"
            )

    buy_items: list[BuyItem] = []
    flags: list[CollectionFlag] = []

    for card, recommended_copies in candidates.items():
        owned_qty = owned.owned_qty(card)
        to_acquire = max(0, recommended_copies - owned_qty)

        # ── Field + archetype relevance ──────────────────────────────────────
        if has_winrate_signal:
            field_rel = field_weighted.get(card, 0.0)
            card_basis = "win-rate"
        else:
            field_rel = field_adoption.get(card, 0.0)
            card_basis = "adoption (no win-rate signal)"
        arch_rel = archetype_incl.get(card, 0.0)
        impact = field_rel * arch_rel

        # ── Price lookup (soft dep) ─────────────────────────────────────────
        price: Optional[float] = None
        price_source_str: Optional[str] = None
        if price_fn is not None:
            try:
                quote = price_fn(card)
                if quote is not None:
                    # quote may be a PriceQuote (with cheapest_usd) or a plain float
                    if hasattr(quote, "cheapest_usd"):
                        price = quote.cheapest_usd
                        if price is not None and hasattr(quote, "source"):
                            price_source_str = quote.source
                    elif isinstance(quote, (int, float)):
                        price = float(quote)
                        price_source_str = "injected"
            except Exception as exc:
                log.debug("_rank_acquisitions: price_fn(%r) raised: %s", card, exc)

        # ── Slots / replaces ────────────────────────────────────────────────
        slots = (slots_into_map or {}).get(card, "sideboard")
        replaces = (replaces_map or {}).get(card, None)

        # ── Buy list: cards with to_acquire > 0 ────────────────────────────
        if to_acquire > 0:
            buy_items.append(BuyItem(
                card=card,
                acquire_copies=to_acquire,
                impact=impact,
                impact_basis=card_basis,
                field_relevance=field_rel,
                archetype_relevance=arch_rel,
                price=price,
                price_source=price_source_str,
                slots_into=slots,
                replaces=replaces,
                notes=(),
            ))
        else:
            # Fully owned — check for over-quantity / overpriced findings.

            # ── Over-quantity flag ───────────────────────────────────────────
            # Fire when: owned_qty > recommended_copies AND the card is over-covering
            # a vulnerability tag at over_cover_factor × field demand.
            # Also fire on raw over-quantity (owned > 2× recommended) as a simple guard.
            is_over_quantity = False
            over_qty_reason = ""

            if owned_qty > recommended_copies:
                # Simple raw over-quantity check.
                if owned_qty >= math.ceil(recommended_copies * over_cover_factor):
                    is_over_quantity = True
                    over_qty_reason = (
                        f"own {owned_qty} copies; only {recommended_copies} recommended "
                        f"(over_cover_factor={over_cover_factor})"
                    )

                # Tag-level over-cover check.
                if (
                    not is_over_quantity
                    and tag_field_demand is not None
                    and card_tags is not None
                ):
                    card_tag_set = card_tags.get(card, frozenset())
                    for tag in card_tag_set:
                        demand = tag_field_demand.get(tag, 0.0)
                        if demand <= 0.0:
                            continue
                        # Compute total owned answers for this tag.
                        tag_owned = sum(
                            owned.owned_qty(c)
                            for c, tags in card_tags.items()
                            if tag in tags
                        )
                        threshold = math.ceil(demand * over_cover_factor)
                        if tag_owned > threshold:
                            is_over_quantity = True
                            over_qty_reason = (
                                f"tag '{tag}': own {tag_owned} total answers; "
                                f"field demand ≈ {demand:.1f}; threshold = {threshold} "
                                f"(over_cover_factor={over_cover_factor})"
                            )
                            break

            if is_over_quantity:
                flags.append(CollectionFlag(
                    card=card,
                    kind="over-quantity",
                    detail=over_qty_reason,
                ))

    # ── Sort buy list: impact DESC, price ASC, card ASC ────────────────────
    def _sort_key(item: BuyItem) -> tuple:
        price_val = item.price if item.price is not None else float("inf")
        return (-item.impact, price_val, item.card)

    buy_items.sort(key=_sort_key)

    # ── Total cost ──────────────────────────────────────────────────────────
    total_cost: Optional[float] = None
    if buy_items:
        if price_fn is not None:
            # Compute if every priced item has a price; otherwise None.
            cost_sum = 0.0
            all_priced = True
            for item in buy_items:
                if item.price is not None:
                    cost_sum += item.price * item.acquire_copies
                else:
                    all_priced = False
                    break
            if all_priced:
                total_cost = cost_sum

    return AcquisitionPlan(
        buy_list=tuple(buy_items),
        flags=tuple(flags),
        total_cost=total_cost,
        field_source=field_source,
        impact_basis=impact_basis_global,
        window=window,
        heuristic_note=_HEURISTIC_NOTE,
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# acquire_plan — orchestrator (DB-heavy setup → pure core)
# ---------------------------------------------------------------------------

def acquire_plan(
    con: "duckdb.DuckDBPyConnection",
    field: "FieldDistribution",
    *,
    archetype: str | None = None,
    deck: dict[str, int] | None = None,
    collection: "CollectionView",
    price_fn: "Callable[[str], Optional[object]] | None" = None,
    since: str | None = None,
    until: str | None = None,
    over_cover_factor: float = _DEFAULT_OVER_COVER_FACTOR,
    overprice_factor: float = _DEFAULT_OVERPRICE_FACTOR,
) -> AcquisitionPlan:
    """Orchestrate the acquisition advisor: DB scan → pure _rank_acquisitions.

    **Step A** — Candidate universe: union of:
    - consensus maindeck + sideboard cards for the target archetype (via
      ``card_frequencies``).
    - HOSER_CATALOG candidates relevant to the field (via ``recommend_sideboard``
      with a dummy empty maindeck to capture the hoser candidates).

    When ``deck`` is provided instead of ``archetype``, it is used as the target
    board; ``archetype`` may still be provided for the consensus inclusion lookup.

    **Step B** — Impact scores: reuse ``field_weighted_values`` for the win-rate
    term; fall back to per-card field adoption when signal is absent.

    **Step C** — Ownership join + flags: calls ``_rank_acquisitions`` (pure).

    **Step D** — Slot-in / replaces: populated from the sideboard trace for SB
    cards; None for maindeck candidates (thin data degrade).

    Soft degradations:
    - No win-rate signal → adoption fallback, labeled.
    - No price_fn → all prices None, total_cost None.
    - No archetype + no deck → empty candidate universe, returns empty plan.
    """
    from legacy_engine.advisory.sideboard import HOSER_CATALOG, recommend_sideboard
    from legacy_engine.generation.consensus import _latest_regime_window, card_frequencies
    from legacy_engine.generation.tuning import field_weighted_values

    warnings: list[str] = []

    # ── Resolve window ──────────────────────────────────────────────────────
    if since is None and until is None:
        try:
            since, until = _latest_regime_window()
        except Exception:
            pass  # keep both None (open window)

    # ── Step A: Candidate universe ─────────────────────────────────────────
    candidates: dict[str, int] = {}  # card → recommended copies

    # From explicit deck.
    if deck is not None:
        for card, copies in deck.items():
            candidates[card] = max(candidates.get(card, 0), copies)

    # From archetype consensus (main + side).
    if archetype is not None:
        try:
            main_freqs = card_frequencies(
                con, archetype, board="main", since=since, until=until
            )
            for cf in main_freqs:
                modal = max(1, round(cf.modal_count)) if hasattr(cf, "modal_count") else 1
                candidates[cf.name] = max(candidates.get(cf.name, 0), modal)
        except Exception as exc:
            log.debug("acquire_plan: card_frequencies(main) failed: %s", exc)
            warnings.append(f"consensus maindeck unavailable: {exc}")

        try:
            side_freqs = card_frequencies(
                con, archetype, board="side", since=since, until=until
            )
            for cf in side_freqs:
                modal = max(1, round(cf.modal_count)) if hasattr(cf, "modal_count") else 1
                candidates[cf.name] = max(candidates.get(cf.name, 0), modal)
        except Exception as exc:
            log.debug("acquire_plan: card_frequencies(side) failed: %s", exc)
            warnings.append(f"consensus sideboard unavailable: {exc}")

    # From HOSER_CATALOG (always include as candidates; filtered by color/anti-synergy
    # inside recommend_sideboard, but we want them in the candidate universe so the
    # advisor can surface "acquire Leyline of the Void" etc.).
    for card_name, hoser in HOSER_CATALOG.items():
        if card_name not in candidates:
            candidates[card_name] = hoser.max_copies

    if not candidates:
        warnings.append("empty candidate universe — no archetype, no deck, no catalog")
        return AcquisitionPlan(
            buy_list=(),
            flags=(),
            total_cost=None,
            field_source=field.field_source,
            impact_basis="adoption (no win-rate signal)",
            window=(since, until),
            heuristic_note=_HEURISTIC_NOTE,
            warnings=tuple(warnings),
        )

    all_cards = list(candidates.keys())

    # ── Step B: Impact scores ─────────────────────────────────────────────
    # Win-rate-based field relevance (heavy scan, runs once).
    try:
        fwv = field_weighted_values(
            con, field, all_cards, since=since, until=until
        )
    except Exception as exc:
        log.debug("acquire_plan: field_weighted_values failed: %s", exc)
        fwv = {card: 0.0 for card in all_cards}
        warnings.append(f"win-rate signal unavailable: {exc}")

    # Adoption-based field relevance (fallback): Σ_opp share × inclusion_pct(card in opp decks).
    field_adoption: dict[str, float] = {card: 0.0 for card in all_cards}
    try:
        for opp, share in field.shares.items():
            if share <= 0.0:
                continue
            try:
                opp_freqs = card_frequencies(
                    con, opp, board="main", since=since, until=until
                )
                incl_map = {cf.name: cf.inclusion_pct for cf in opp_freqs}
                for card in all_cards:
                    field_adoption[card] = (
                        field_adoption.get(card, 0.0) + share * incl_map.get(card, 0.0)
                    )
            except Exception:
                pass  # skip this opp if data unavailable
    except Exception as exc:
        log.debug("acquire_plan: field_adoption computation failed: %s", exc)

    # Archetype inclusion (archetype relevance for each candidate).
    archetype_incl: dict[str, float] = {card: 0.0 for card in all_cards}
    if archetype is not None:
        try:
            main_freqs = card_frequencies(
                con, archetype, board="main", since=since, until=until
            )
            for cf in main_freqs:
                archetype_incl[cf.name] = cf.inclusion_pct
            side_freqs = card_frequencies(
                con, archetype, board="side", since=since, until=until
            )
            for cf in side_freqs:
                # Take max of main+side inclusion (a card in both gets the higher pct).
                archetype_incl[cf.name] = max(
                    archetype_incl.get(cf.name, 0.0), cf.inclusion_pct
                )
        except Exception as exc:
            log.debug("acquire_plan: archetype_incl failed: %s", exc)
            warnings.append(f"archetype inclusion data unavailable: {exc}")
    else:
        # No archetype — use field adoption as a proxy for archetype relevance.
        archetype_incl = dict(field_adoption)

    # ── Per-tag field demand (for over-cover check) ────────────────────────
    # Σ_opp field.shares[opp] for each archetype tag the opp carries, where
    # the tag matches a HOSER_CATALOG coverage tag.
    tag_field_demand: dict[str, float] = {}
    card_tags: dict[str, frozenset[str]] = {}
    try:
        from legacy_engine.advisory.whattoplay import field_vulnerability_tags
        archetype_tags = field_vulnerability_tags(con, field)
        for opp, share in field.shares.items():
            for tag in archetype_tags.get(opp, frozenset()):
                tag_field_demand[tag] = tag_field_demand.get(tag, 0.0) + share
        # card_tags: card → frozenset of tags from HOSER_CATALOG.
        for card_name, hoser in HOSER_CATALOG.items():
            card_tags[card_name] = frozenset(
                t for t in hoser.attacks if t != "_hate"
            )
    except Exception as exc:
        log.debug("acquire_plan: tag_field_demand computation failed: %s", exc)

    # ── Slots / replaces from sideboard trace ────────────────────────────────
    # Run recommend_sideboard on an empty maindeck to capture the hoser slots.
    slots_into_map: dict[str, str] = {}
    replaces_map: dict[str, str | None] = {}
    try:
        sb_pkg = recommend_sideboard(
            con, field,
            deck if deck else {},
            since=since, until=until,
        )
        for trace_item in sb_pkg.trace:
            covered_str = ", ".join(sorted(trace_item.newly_covered)) or "general coverage"
            slots_into_map[trace_item.card] = f"sideboard ({covered_str})"
    except Exception as exc:
        log.debug("acquire_plan: recommend_sideboard trace failed: %s", exc)

    # For archetype consensus cards not covered by the sideboard trace,
    # default to "maindeck" or "sideboard" based on candidate source.
    if archetype is not None:
        try:
            side_names = {
                cf.name
                for cf in card_frequencies(
                    con, archetype, board="side", since=since, until=until
                )
            }
        except Exception:
            side_names = set()
        for card in all_cards:
            if card not in slots_into_map:
                if card in side_names:
                    slots_into_map[card] = "sideboard"
                else:
                    slots_into_map[card] = "maindeck"

    # ── Overpriced-printing flags (orchestrator-level, injected into plan) ────
    # The pure core doesn't have access to per-printing prices; the orchestrator
    # checks priced candidates against their cheapest alternative and builds flags
    # to inject into the final plan.
    extra_flags: list[CollectionFlag] = []
    if price_fn is not None:
        for card in all_cards:
            owned_qty = collection.owned_qty(card)
            if owned_qty == 0:
                continue
            try:
                quote = price_fn(card)
                if quote is None:
                    continue
                cheapest: Optional[float] = None
                if hasattr(quote, "cheapest_usd"):
                    cheapest = quote.cheapest_usd
                elif isinstance(quote, (int, float)):
                    cheapest = float(quote)
                if cheapest is None or cheapest <= 0.0:
                    continue
                # Get the owned printing price.  We don't have per-printing price
                # data from the text path, so we can't determine the exact owned price.
                # However the advisor can still surface the spread by comparing the
                # cheapest available price against what the user might have paid for a
                # known expensive printing (e.g. if the user explicitly annotated their
                # inventory entry with a printing that has a price in the DB).
                # For now: no per-printing price available from text import → no flag.
                # The flag fires when an owned_printing has a set_code that we can
                # look up in the price DB.
                owned_printings = collection.printings(card)
                for op in owned_printings:
                    if op.set_code is None:
                        continue
                    # Look up the price for this specific printing.
                    try:
                        row = con.execute(
                            """
                            SELECT COALESCE(usd, usd_foil, usd_etched)
                            FROM card_prices
                            WHERE name = ? AND set_code = ? AND is_paper = TRUE
                              AND (usd IS NOT NULL OR usd_foil IS NOT NULL OR usd_etched IS NOT NULL)
                            ORDER BY COALESCE(usd, usd_foil, usd_etched) ASC
                            LIMIT 1
                            """,
                            [card, op.set_code],
                        ).fetchone()
                        if row is None or row[0] is None:
                            continue
                        owned_price = float(row[0])
                        if owned_price >= overprice_factor * cheapest and cheapest < owned_price:
                            extra_flags.append(CollectionFlag(
                                card=card,
                                kind="overpriced-printing",
                                detail=(
                                    f"owned printing ({op.set_code}) costs ~${owned_price:.2f}; "
                                    f"cheapest printing is ~${cheapest:.2f} "
                                    f"(overprice_factor={overprice_factor})"
                                ),
                            ))
                    except Exception as exc2:
                        log.debug("acquire_plan: per-printing price lookup failed for %r: %s", card, exc2)
            except Exception as exc:
                log.debug("acquire_plan: price_fn(%r) raised: %s", card, exc)

    # ── Call pure core ───────────────────────────────────────────────────────
    plan = _rank_acquisitions(
        candidates=candidates,
        field_weighted=fwv,
        archetype_incl=archetype_incl,
        field_adoption=field_adoption,
        owned=collection,
        price_fn=price_fn,
        slots_into_map=slots_into_map,
        replaces_map=replaces_map,
        over_cover_factor=over_cover_factor,
        field_source=field.field_source,
        window=(since, until),
        tag_field_demand=tag_field_demand if tag_field_demand else None,
        card_tags=card_tags if card_tags else None,
    )

    # Merge orchestrator-level flags with pure-core flags.
    if extra_flags:
        merged_flags = tuple(plan.flags) + tuple(extra_flags)
        plan = AcquisitionPlan(
            buy_list=plan.buy_list,
            flags=merged_flags,
            total_cost=plan.total_cost,
            field_source=plan.field_source,
            impact_basis=plan.impact_basis,
            window=plan.window,
            heuristic_note=plan.heuristic_note,
            warnings=plan.warnings + tuple(warnings),
        )
    elif warnings:
        plan = AcquisitionPlan(
            buy_list=plan.buy_list,
            flags=plan.flags,
            total_cost=plan.total_cost,
            field_source=plan.field_source,
            impact_basis=plan.impact_basis,
            window=plan.window,
            heuristic_note=plan.heuristic_note,
            warnings=plan.warnings + tuple(warnings),
        )

    return plan
