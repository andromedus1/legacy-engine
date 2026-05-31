---
description: Read before designing epic-gap-discovery's card-adjacency-model + discovery-tuning — how to pick novel swap-in candidates a shell doesn't run yet, score them by transferred per-card value, and gate the exploration honestly.
type: brief
kind: research
research_method: /brief
updated: 2026-05-31
summary: |
  Curates the approach for "discovery" deck tuning (deck-generation mode 3, card-gap half): an adjacency
  model that nominates cards a shell does NOT already run (role/color/CMC + decklist co-occurrence), a
  cross-archetype transfer of the shipped per-card×matchup value so the nominations are evidence-backed, and
  a confidence-gating scheme that keeps exploratory picks honest without the (deferred) goldfish pillar.
key_findings:
  - "All adjacency inputs already exist in-repo — reuse whattoplay._card_roles (oracle-text role classifier), card_tags (staple roles + mana-base tags), Card.colors/cmc/type_line, and deck_cards for co-occurrence. No new NLP needed for v1."
  - "Recommended v1 adjacency = role-match ∩ color-legal ∩ CMC-band, RANKED by decklist co-occurrence lift (PMI over the 63k-deck corpus). It is the heuristic, auditable analogue of card2vec — embeddings are a later upgrade, not a v1 requirement."
  - "Cross-archetype value transfer is valid for ANSWER/HOSER roles (a card's lift vs a combo deck is largely pilot-independent) and INVALID for synergy/engine cards (value is deck-context-dependent). Gate transfer by role: transfer answers, never transfer engine pieces."
  - "Discovery is exploratory: gate on the EXISTING ConfidenceMetadata tiers but require cross-field n at the established tier (≥100) for a transferred recommendation, and ALWAYS label it presence-correlational + not-yet-goldfish-validated. A confidence-gated v1 ships without goldfish."
  - "The archetype-gap half (high positioning-S, low meta-share) is mechanical: rank archetypes by S − f(share); no research needed beyond the existing positioning + metashare surfaces."
  - "Prior art (card2vec, 17Lands generalised representations, oracle-text sentence-transformer clustering) confirms decklist co-occurrence alone yields strong similarity, but is archetype-confounded — which is exactly why our role/color gating + value-transfer-by-role is the honest layer on top."
---

# Brief: Card-Level Adjacency & Discovery for Deck Tuning

## Purpose

Unblocks **`epic-gap-discovery`** (deck-generation mode 3), specifically the `card-adjacency-model` and
`discovery-tuning` child features. The shipped field-tuner (`generation/tuning.py`) deliberately scopes its
swap-in candidate pool to **cards the archetype already plays** (bounded, faithful, low-risk). This brief
covers the opposite end: nominating cards the shell does **not** run yet — *role/color/synergy-adjacent*
candidates — and scoring them honestly. It answers four questions: (1) what makes a card an adjacency
candidate; (2) how to transfer the per-card×matchup value we now compute across archetype contexts; (3) how
to gate exploration so we don't fabricate edges; (4) the (light) archetype-gap half.

This is **research/curation**, not design. `/epic-design` after this brief realizes the features.

---

## 0. What we already have (ground truth — reuse, don't rebuild)

The adjacency inputs are all in-repo. Do not introduce new infrastructure for v1.

| Input | Source | Use for adjacency |
|---|---|---|
| **Analytical roles** (removal / counter / threat / card-advantage / …) | `advisory/whattoplay.py::_card_roles(card)` — oracle-text regex classifier + `card_tags` | "same role" matching: a counter-spell shell wants other counters |
| **Staple roles** (curated) | `card_tags.py::staple_role(name)` (`_STAPLE_ROLES`) | high-precision role tags for known staples |
| **Mana-base tags** | `card_tags.py::mana_base_tags(card)` | land/fixing adjacency |
| **Colors / CMC / type_line** | `models/card.py` `Card.colors`, `Card.cmc`, `Card.type_line` (now layout-aware front-face for DFCs) | color-legality + curve-band filters |
| **Decklist co-occurrence** | `deck_cards` table (63k decks); `generation/consensus.card_frequencies` already does `GROUP BY dc.name` | "cards that appear alongside this shell's cards" — the data-driven similarity signal |
| **Per-card×matchup value** | `analytics/card_value.py` (`card_values_vs` → `CardValue.lift/.tier/.n`) + `match_results.compute_card_winrates` | the evidence that an adjacent card is actually *good vs the field* |
| **Confidence tiers** | `confidence.py::tier_for_sample` (speculative <30 / evolving 30–99 / established ≥100) | gating exploratory picks |

**Key consequence:** a credible discovery v1 is a *composition of existing primitives*, not an ML project.

---

## 1. The adjacency model — what makes a card a candidate

### 1.1 Prior art (and why we don't need it yet)

- **card2vec** ([afreefaw/MTG-card2vec](https://github.com/afreefaw/MTG-card2vec)) learns card embeddings from
  decklists alone (word2vec over "decks as sentences"), receiving *no* card attributes — similarity emerges
  purely from co-occurrence. It works, but the embedding is **archetype-confounded** (cards cluster by deck,
  so "similar" often means "played in the same decks," not "interchangeable role").
- **Generalised card representations** ([arXiv:2407.05879](https://arxiv.org/html/2407.05879v1)) and
  **oracle-text sentence-transformer clustering** add semantic signal from card text — the natural later
  upgrade when heuristic roles prove too coarse.
- Deckbuilding toolkits ([GrimoireML](https://github.com/AdamProbert/GrimoireML),
  [mtg_ai_deck_builder](https://github.com/georgejieh/mtg_ai_deck_builder)) and draft LLMs
  ([UrzaGPT, arXiv:2508.08382](https://arxiv.org/html/2508.08382v1)) confirm the space but target
  draft/standard, not Legacy field-tuning.

**Takeaway:** co-occurrence captures real signal, but raw embeddings are confounded and unauditable. Our
edge is *auditability* (every recommendation explainable from role + co-occurrence + value), so v1 uses an
explicit heuristic; embeddings are a documented later lever, not a dependency.

### 1.2 Recommended v1 — gated co-occurrence

A card `X` is an **adjacency candidate** for shell `D` (archetype `A`, color identity `C(D)`) when ALL hold:

1. **Not already in the deck** (`X ∉ D` — discovery, not re-suggestion).
2. **Color-legal**: `X.colors ⊆ C(D)` (front-face colors; uses the layout-aware card rows from
   `fix-scryfall-face-indexing-db`). Colorless always legal.
3. **Role-relevant**: `_card_roles(X) ∩ roles_the_shell_wants ≠ ∅`. Default "wants" = the role distribution
   of `D`'s flexible (non-locked) slots — a shell heavy in interaction wants interaction.
4. **CMC-band**: `X.cmc` within the shell's flexible-slot curve band (e.g. ±1 of the median flex CMC) — keep
   the curve intact.

Then **rank** survivors by a **co-occurrence lift** — how much more often `X` appears with `D`'s core than
chance — computed over the corpus:

```
PMI(X, core(A)) = log [ P(X, core) / (P(X) · P(core)) ]
```

where `P(X)` = fraction of in-window decks running `X`, `P(X, core)` = fraction running `X` AND ≥k of the
archetype's locked-core cards. This is the heuristic, auditable analogue of card2vec (decklist co-occurrence)
without the opaque embedding. Reuse `card_frequencies` + a `deck_cards` self-join for the counts; gate `P(X)`
by the same windowing the tuner uses (latest ban regime).

**Why this shape:** steps 1–4 guarantee the candidate is *playable* in the shell (legal, on-role, on-curve);
the PMI rank surfaces cards the field has *empirically* paired with this strategy. Neither half alone is
enough — co-occurrence without role/color gating reproduces the archetype confound; gating without
co-occurrence has no ranking signal.

### 1.3 Later upgrade (note, don't build)

Swap the PMI rank for a learned embedding (card2vec over our `deck_cards`, or oracle-text sentence
embeddings) when: (a) PMI is too sparse for niche cards, or (b) we want *semantic* adjacency ("does the same
thing") beyond *co-occurrence* adjacency ("played together"). Embeddings need a training/refresh pipeline and
lose auditability — defer until the heuristic demonstrably limits.

---

## 2. Cross-archetype value transfer — the key unlock

The hard problem: an adjacency candidate is by definition **under-played in this shell**, so its
per-card×matchup signal *in archetype A's context* is thin → fails the confidence gate exactly where we need
it. The unlock: the card may be **proven vs the same field threats in OTHER decks**.

`card_value` already aggregates per-`(card, board, opponent)` **across all decks** (it is NOT conditioned on
the running deck's archetype — see `compute_card_winrates`). So the transferable quantity already exists:
`card_values_vs(rates, [X], board, opponent=M)` gives `X`'s lift vs `M` pooled over every deck that ran `X`.

**But transfer is only honest for some roles.** Decompose by what drives the card's value:

| Role class | Transfer valid? | Why |
|---|---|---|
| **Answers / hosers** (Surgical, Force of Will, removal, sweepers) | **YES** | Value vs a threat is largely pilot/shell-independent — Surgical is good vs graveyard combo whoever runs it. This is the same assumption `advisory/sideboard` already makes with its hoser catalog. |
| **Generic card advantage / cantrips** | **MOSTLY** | Brainstorm is good broadly; transfer with mild shrinkage. |
| **Synergy / engine pieces** (combo enablers, payoff cards, deck-specific build-arounds) | **NO** | Value is deck-context-dependent (a payoff with no enablers is dead). Pooled lift is meaningless out of context. |

**Recommendation:** gate transfer **by role** — transfer the matchup lift for answer/hoser/generic roles
(via the existing `_card_roles` classification), and for synergy/engine roles either (a) refuse to transfer
(omit from discovery v1) or (b) require in-shell evidence (the normal, un-transferred gate). Encode this as a
`TRANSFERABLE_ROLES` allow-list, mirroring how `sideboard.HOSER_CATALOG` already treats answers as
archetype-independent.

**Shrinkage:** when transferring, treat the cross-field lift as a prior and shrink toward 0 (no-edge) by the
cross-field `n` — reuse `matchup.beta_binomial_shrink_to` (see the `two-level-empirical-bayes` pattern). A
card with established cross-field evidence keeps most of its lift; a thin one regresses to "no edge."

---

## 3. Risk & validation — keeping discovery honest

Discovery shifts tuning from "proven, auditable" (swap within the observed pool) to "exploratory" (suggest
the untried). The project rule — **never fabricate meta numbers, gate every derived stat** — applies with
extra force here.

### 3.1 Confidence gating (v1, no goldfish)

- **Tier the recommendation** on the *transferred* cross-field `n` via `tier_for_sample`. Require the
  **established** tier (≥100) for a discovery suggestion to surface by default — a higher bar than in-pool
  tuning (which accepts evolving), because the candidate is unproven *in this shell*.
- **Always label** discovery picks: `presence-correlational, transferred from cross-field data, NOT
  goldfish-validated`. Reuse the disclaimer wording already in `report cards` / `advise sideboard`.
- **Separate the surfaces**: discovery suggestions are a *distinct, clearly-flagged* output section, never
  silently mixed into the proven in-pool swap log. The tuner's audit trail must show "proven swap" vs
  "exploratory suggestion" distinctly.
- **Cap exploration**: suggest at most a few discovery candidates; never let discovery swaps drive the
  greedy objective the way proven per-card value does (that protects the existing no-hollowing guarantee).

### 3.2 What v1 can and cannot claim

- **Can**: "Decks that ran X vs the field threats you're weak to (M, N) have an established above-baseline
  win-rate; X is on-role, color-legal, on-curve, and the field pairs it with your shell — consider testing
  it." (Evidence + adjacency + explicit uncertainty.)
- **Cannot**: "X improves your win-rate." (No causal/goldfish evidence; correlational only.)

### 3.3 Where goldfish validation fits (later)

The deferred `epic-goldfish-simulation` pillar is the eventual confidence layer: simulate the shell with the
candidate swapped in (consistency, clock, mana) to confirm the change doesn't break the deck before
recommending. Until then, discovery is **suggest-and-label**, not **validate-and-recommend**. Design the
discovery output so a future goldfish gate slots in as an additional filter (candidate → goldfish-passes? →
promote from "suggestion" to "validated"), not a rewrite.

---

## 4. The archetype-gap half (light)

The other half of mode 3 is mechanical and needs no research: surface **under-explored archetypes** — high
positioning `S` (well-positioned vs the field per `advisory/positioning`) but low meta-share (per
`analytics/metashare`). Rank by a gap score, e.g. `S − g(share)` (reward strong position, penalize already-popular),
gate by the same confidence tiers (don't surface an archetype with `S` computed from thin matchup data).
This reuses two shipped surfaces directly; the only design choices are the gap-score shape and the
display/threshold. No external research required.

---

## Implementation Notes

- **New module placement**: a `generation/discovery.py` (adjacency + transfer + gating) consuming
  `card_tags`, `whattoplay._card_roles`, `card_value`, `consensus.card_frequencies`, and a `deck_cards`
  co-occurrence query. Keep it OUT of `tuning.py` (tuning stays the proven-swap engine); discovery composes
  alongside it and emits a clearly-separated suggestion list.
- **Reuse, don't fork**: `_card_roles` is the role source (already feeds whattoplay/sideboard); the
  `TRANSFERABLE_ROLES` allow-list is new but small and curated like `HOSER_CATALOG`.
- **Windowing**: all corpus stats (co-occurrence, transferred value) use the tuner's window
  (latest ban regime) for consistency — thread the same `since/until`, and reuse one `CardWinRates`
  aggregate (see `fix-tuning-sideboard-winrate-reuse`).
- **Confidence-gating is the load-bearing safety**: the established-tier bar + role-gated transfer +
  explicit labels are what make this shippable without goldfish. Do not relax them for coverage.
- **Edge cases**: candidate already in the sideboard (not the maindeck) — still a valid discovery for the 60;
  multi-face cards (resolve via the layout-aware front-face rows); colorless cards (always color-legal);
  cards with no role match (excluded — no basis to suggest); thin co-occurrence (PMI undefined for never-paired
  cards → exclude, don't impute).

## Sources

- card2vec — decklist co-occurrence embeddings: <https://github.com/afreefaw/MTG-card2vec>
- Learning With Generalised Card Representations for MTG (arXiv 2407.05879): <https://arxiv.org/html/2407.05879v1>
- UrzaGPT: LoRA-tuned LLM for CCG card selection (arXiv 2508.08382): <https://arxiv.org/html/2508.08382v1>
- GrimoireML deckbuilding toolkit: <https://github.com/AdamProbert/GrimoireML>
- mtg_ai_deck_builder: <https://github.com/georgejieh/mtg_ai_deck_builder>
- Internal: `docs/briefs/deck-generation-and-moxfield.md` §2.2 (mode 3), `docs/briefs/advisory-methods.md`,
  `src/legacy_engine/analytics/card_value.py`, `src/legacy_engine/generation/tuning.py`,
  `src/legacy_engine/advisory/whattoplay.py` (`_card_roles`), `src/legacy_engine/card_tags.py`.
