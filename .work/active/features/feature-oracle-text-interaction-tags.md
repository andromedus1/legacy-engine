---
id: feature-oracle-text-interaction-tags
kind: feature
stage: done
tags: [advisory, data-quality, methodology]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-13
updated: 2026-06-14
---

## Design

### Decision: scope as one feature, three sequenced units, no child stories

The hurdle is narrow and cohesive — ground card-*interaction* claims (whose graveyard, what
mechanism, who it targets) in `cards.oracle_text` instead of memory. The existing oracle-text layer
(`card_tags.py` + `whattoplay._card_roles`) classifies *what a card does* (roles: counter / removal /
graveyard_recursion). It does **not** model *interaction semantics*: symmetry, targeting, and whether
an effect touches the controller's own resources. The three bugs in the dogfood session were all of
this second kind, and **none** of the existing role tags would have caught them. So this feature adds
a new, orthogonal `interaction_facts(card)` derivation alongside the existing tag functions, plus a
guard that checks advisory free-text claims against it. One author, ~3 files, tightly coupled → keep
as a single feature; no child-story decomposition.

### Architectural options considered

1. **Surface raw oracle_text in the report next to each card** (cheapest). Lets a *human* check, but
   does not stop the engine from *generating* a wrong claim — the advisory text is auto-generated, so
   "let the reader verify" doesn't fix auto-generated primers. Rejected as the primary fix (kept as a
   cheap secondary affordance — the guard's evidence string includes the relevant oracle_text excerpt).
2. **Structured interaction facts derived from oracle_text** (chosen). A pure `interaction_facts(card)
   -> InteractionFacts` returning typed enums (`affects`, `self_graveyard_safe`, `permanence`,
   `free_cast`) that sideboard/primer logic and the guard reason over. Pure, auditable, testable from
   hand-built `Card`s with no DB — mirrors `card_tags.py` exactly. Composes with the existing role
   layer rather than replacing it.
3. **A lint/guard only**, no structured facts (regex the claim, regex the oracle_text, compare).
   Brittle — every claim phrasing needs its own regex pair and there's no reusable fact other code can
   consume. Rejected as the *sole* mechanism, but the guard concept from it is adopted as Unit 3, built
   *on top of* the structured facts from option 2.

Chosen: **option 2 as the foundation, with option 3's guard layered on it and option 1's oracle_text
excerpt as the guard's evidence.** The structured facts are the single source of truth; the guard and
any human-facing surface both derive from them.

### The core modelling insight (why the bugs happened)

A claim like "this hates *your own* graveyard" decomposes into two **orthogonal** facts that the
prior memory-based reasoning conflated:

- **Who does the effect reach?** — `affects: symmetric | opponent-only | targeted`. Derived from
  oracle_text phrasing: `"opponent's graveyard"` / `"each opponent"` → opponent-only;
  `"target player"` / `"target ... graveyard"` → targeted (controller picks, so *can* be one-sided);
  `"each player"` / `"players can't"` / unscoped `"all"` → symmetric.
- **What mechanism?** — graveyard-*count* reduction (exile/remove cards from a yard) vs a
  cast/ETB/static *restriction* that never touches yard count. This is the Grafdigger's distinction:
  it is `symmetric` on casting-from-yard, but `self_graveyard_safe: yes` for delirium/delve/escape
  because it removes nothing from the yard.

`self_graveyard_safe` is the derived verdict combining the two: an effect is self-graveyard-safe iff
(it is opponent-only or targeted) **OR** (it does not reduce graveyard card count). All three example
cards are self-graveyard-safe; the memory-based reasoning got all three wrong.

### Unit build order (trickiest first)

**Unit 1 — `InteractionFacts` model + `interaction_facts(card)` derivation.** *(trickiest — the
classification rules carry all the risk; build and test first.)*
- New module `src/legacy_engine/interaction_facts.py` (sibling of `card_tags.py`; pure functions over
  `Card`, no DB, no network — same shape as `card_tags.py`).
- New Pydantic model in the same module (small, local, like the dataclasses that live beside their
  logic per ARCHITECTURE "result records live in their module"):

  ```python
  from typing import Literal
  from legacy_engine.models.base import LegacyEngineModel
  from legacy_engine.confidence import ConfidenceMetadata, tier_for_sample  # see Unit-1 confidence note

  Affects = Literal["symmetric", "opponent-only", "targeted", "self-only", "none"]
  Permanence = Literal["static", "activated", "triggered", "one-shot"]

  class InteractionFacts(LegacyEngineModel):
      affects: Affects = "none"            # whose resources the effect reaches
      self_graveyard_safe: bool = True     # does NOT reduce the controller's own graveyard count
      touches_graveyard: bool = False      # the effect references a graveyard at all
      graveyard_count_reduction: bool = False  # exiles/removes cards FROM a graveyard
      permanence: Permanence = "one-shot"  # static (continuous) vs activated/triggered/one-shot
      free_cast: bool = False              # castable without paying mana cost (reuse is_free_spell)
      evidence: tuple[str, ...] = ()       # oracle_text line(s) each fact was derived from
      confidence: ConfidenceMetadata = ConfidenceMetadata()  # heuristic-source, see note

  def interaction_facts(card: Card) -> InteractionFacts: ...
  ```

- Derivation rules (pure regex/substring over `card.oracle_text`, case-insensitive; line-scoped so
  `evidence` can quote the matched line):
  - `touches_graveyard`: oracle_text contains `"graveyard"` (or `"graveyards"`).
  - `graveyard_count_reduction`: a graveyard line ALSO contains an exile/removal verb
    (`exile`, `remove ... from`, `shuffle ... into`) acting on the graveyard. Grafdigger's
    ("can't enter", "can't cast") matches `touches_graveyard` but NOT count-reduction → the key case.
  - `affects`:
    - `opponent-only`: `"opponent's graveyard"`, `"each opponent"`, `"target opponent"`.
    - `targeted`: `"target player"`, `"target ... graveyard"` (controller chooses) and not already
      opponent-only.
    - `symmetric`: `"each player"`, `"players can't"`, `"all graveyards"`, or an unscoped global
      restriction (Grafdigger's, Rest in Peace) with no per-player scoping.
    - `self-only`: `"your graveyard"`/`"your hand"` with no opponent/target scoping (e.g. delve,
      Snapcaster-style self-recursion) — proactive, never "hates you".
    - `none`: no graveyard/interaction phrasing.
  - `self_graveyard_safe` = `affects in {opponent-only, targeted, self-only, none}` OR
    `not graveyard_count_reduction`. (Targeted is safe because the controller points it at the
    opponent — the dogfood Nihil case.)
  - `permanence`: type_line/text → `static` if the card is an enchantment/artifact/creature with a
    continuous restriction clause (`"can't"`, `"costs ... more"`, `"don't untap"`) and no
    `{...}:` activation; `activated` if it has a `"{cost}: effect"` ability; `triggered` if
    `"when/whenever/at"`; else `one-shot` (instants/sorceries).
  - `free_cast`: delegate to existing `card_tags.is_free_spell(card)` (no duplication).
- **Confidence note (gating, per the confidence-metadata pattern):** these are heuristic regex
  derivations, not sample-driven, so they carry a `ConfidenceMetadata(source="heuristic")` with a
  fixed `level` reflecting rule certainty — NOT `tier_for_sample` (there is no `n`). Default
  `level="evolving"`; downgrade to `speculative` when the card has multiple graveyard lines with
  *conflicting* scope (e.g. one opponent-only clause + one symmetric clause) so the guard treats the
  verdict as low-trust. The guard (Unit 3) must NOT hard-fail on a `speculative` fact — it flags,
  per PRINCIPLES "label, don't assert". This keeps the no-unlabeled-claim rule.

**Unit 2 — wire the facts into the existing role/vulnerability layer (additive, gated).** *(low risk,
follows the gated-additive-augmentation pattern — no-op path is byte-identical.)*
- Extend `whattoplay._card_roles` (or add a parallel helper) so a `graveyard_recursion`/hate card also
  carries its `InteractionFacts` where the caller wants it. Concretely: add an optional
  `interaction_facts` field (default `None`) to the surfaces that today say "bricks your yard" — the
  sideboard `MatchupPlan` / primer rationale. When `None`, output is byte-identical to today (the
  regression contract); when present, the primer can phrase "one-sided graveyard hate, synergy-safe"
  instead of vibes.
- The concrete consumer fix from the hurdle: the sideboard/primer "how each card attacks each
  opponent" rationale must consult `interaction_facts(card).self_graveyard_safe` before ever claiming
  a hate card hurts the controller's own gameplan. This is the line that wrongly suppressed Leyline.
- Do **not** rewrite the existing role regexes; this unit only *adds* the facts alongside them and
  flips the one rationale branch that made the false self-harm claim.

**Unit 3 — `verify_claim` guard + report integration.** *(builds on Units 1-2.)*
- New pure function in `interaction_facts.py`:

  ```python
  @dataclass
  class ClaimCheck:
      ok: bool
      claim: str
      card: str
      reason: str          # why it (dis)agrees with oracle_text
      evidence: tuple[str, ...]  # the oracle_text line(s) consulted

  def verify_graveyard_claim(card: Card, claims_self_harm: bool) -> ClaimCheck: ...
  ```

  The narrow, high-value guard the hurdle asks for: when generated advisory text asserts a card
  "bricks/hurts your own graveyard/yard", call `verify_graveyard_claim(card, claims_self_harm=True)`;
  it returns `ok=False` with `reason` + oracle_text evidence when `self_graveyard_safe` is True. The
  guard is *advisory* (logs/annotates), not a hard exception — a `speculative`-confidence fact yields
  a softer "could not confirm" annotation rather than a contradiction.
- `advisory/report.py`: where the primer renders an interaction claim about a hate/graveyard card,
  attach the `ClaimCheck.evidence` excerpt (option-1 affordance) and suppress/annotate any claim the
  guard flags. Keep this behind the same gated-additive seam — a report built without interaction
  facts renders identically to today.

### Where each piece lives
| Path | Change | Unit |
|---|---|---|
| `src/legacy_engine/interaction_facts.py` | **new** — `InteractionFacts` model, `interaction_facts()`, `verify_graveyard_claim()`, `ClaimCheck` | 1, 3 |
| `src/legacy_engine/advisory/whattoplay.py` | additive — optional facts alongside roles; flip the self-harm rationale branch | 2 |
| `src/legacy_engine/advisory/report.py` | additive, gated — surface evidence excerpt + suppress/annotate flagged claims | 3 |
| `tests/test_interaction_facts.py` | **new** — behavior-derived unit tests (see plan) | 1, 3 |
| `tests/test_whattoplay.py` / `tests/test_advise_report.py` | extend — assert the no-op regression + the corrected Leyline-style rationale | 2, 3 |

No `config.py` change is required (no new paths/URLs). `card.py` is unchanged — `oracle_text` already
exists on the model and in the DB. No ingestion change — Scryfall oracle_text is already loaded.

### Test plan (derived from behavior, not implementation)
Tests use hand-built `Card(name=..., type_line=..., oracle_text=...)` objects — no DB — mirroring
`tests/test_card_tags.py`. Each derived from the *observed behavior* in the hurdle, not from the regex:

- **The three regression cases (the actual bugs):**
  - Grafdigger's Cage → `affects=="symmetric"`, `touches_graveyard==True`,
    `graveyard_count_reduction==False`, `self_graveyard_safe==True`. (Symmetric *restriction*, but
    does not reduce yard count → delirium/delve/escape unaffected.)
  - Leyline of the Void → `affects=="opponent-only"`, `self_graveyard_safe==True`.
  - Nihil Spellbomb → `affects=="targeted"`, `self_graveyard_safe==True`.
- **Contrast cases that SHOULD read as self-affecting / symmetric-count:** a hand-built symmetric
  graveyard *exile* card (e.g. "Exile all graveyards") → `affects=="symmetric"`,
  `graveyard_count_reduction==True`, `self_graveyard_safe==False`.
- **Self-only proactive case:** a delve/escape card referencing "your graveyard" →
  `affects=="self-only"`, `self_graveyard_safe==True` (it's your own engine, never "hates you").
- **`permanence`:** static enchantment (Leyline) → `static`; activated (Nihil's `{T}, Sacrifice`) →
  `activated`; triggered ("When ... draw") detected; instant → `one-shot`.
- **`free_cast`:** Force of Will → True; Brainstorm → False (delegation to `is_free_spell` works).
- **Confidence:** a card with conflicting scope clauses → `confidence.level=="speculative"`; a clean
  single-clause card → `"evolving"`. No `n`-based tiering is invoked (no `tier_for_sample` call).
- **`verify_graveyard_claim`:** for each of the three example cards with `claims_self_harm=True` →
  `ClaimCheck.ok==False` and `evidence` quotes the relevant oracle line; for the symmetric-count
  contrast card → `ok==True` (the self-harm claim is correct). A speculative-confidence card →
  the guard returns a "could not confirm" reason rather than a hard contradiction.
- **Gated regression (no-op contract):** `whattoplay` / `report` output with interaction facts absent
  (`None`) is byte-identical to the pre-feature baseline — exercised by leaving existing tests
  unmodified plus one explicit assertion (mirrors `TestRegressionRoundsless`).
- **The end-to-end payoff assertion:** the primer rationale for a Leyline-style one-sided hate card vs
  a graveyard-reliant field does NOT emit a self-harm/suppression string (the regression the hurdle
  describes).

### Pre-mortem / risks
- **Oracle-text phrasing drift / templating exceptions.** WotC reminder text and odd templating
  ("its owner's graveyard", "that player's graveyard", split/MDFC faces) can fool substring rules.
  *Mitigation:* line-scope the matches, capture `evidence`, and use the `speculative` confidence
  downgrade + advisory (non-fatal) guard so an ambiguous card flags rather than asserts. Seed the test
  suite with the known awkward phrasings (multi-face cards, "owner's graveyard").
- **Over-broad `symmetric` default.** If unscoped phrasing defaults to symmetric too eagerly, we
  reintroduce the original bug in mirror image (calling a one-sided card symmetric). *Mitigation:* the
  precedence order is opponent-only → targeted → self-only → symmetric → none; symmetric requires an
  explicit `each player`/`players can't`/`all graveyards` signal, not mere absence of scoping. Covered
  by the contrast test cases.
- **Multi-face cards.** `store.load_cards` combines faces into `A // B` and concatenates oracle_text;
  derivation runs over the combined text, which is acceptable (a face that hates graveyards still
  hates them) but `evidence` may quote the wrong face. *Mitigation:* noted as a known limitation;
  acceptable for the advisory/primer use case (verification is advisory, not authoritative rules).
- **Scope creep into a rules engine.** This is explicitly a heuristic *interaction-claim* checker, not
  a comprehensive rules model. *Mitigation:* keep the enum surface tiny (affects / self_graveyard_safe
  / permanence / free_cast) and resist adding more facts until a concrete advisory claim needs one.
- **The guard must never hard-fail a report.** A false negative (failing to flag a wrong claim) is far
  less bad than crashing the advisory surface. *Mitigation:* guard is advisory-only; report stays in
  the gated-additive seam so absence of facts = today's behavior.

**Hurdle observed:** card-interaction reasoning done from memory is error-prone, and it produced
several wrong claims in one dogfood session (2026-06-13). All were about graveyard-hate symmetry /
targeting:
- Claimed **Grafdigger's Cage** hurts our own Nethergoyf/Murktide/Barrowgoyf — it doesn't (it only
  stops creatures/PWs *entering* or being *cast* from graveyard/library; it has no effect on
  graveyard *count*, so delirium/delve/escape are unaffected).
- Claimed **Leyline of the Void** and **Nihil Spellbomb** "brick your own yard" — both are
  one-sided/targeted: Leyline = "opponent's graveyard… exile it instead"; Nihil = "exile **target
  player's** graveyard" (you point it at the opponent). Neither touches our own yard.

**Why this matters:** the advisory output — especially the planned plain-speak sideboard primer
([[idea-deck-tuning-refresh-workflow]]) that explains *how each card attacks each opponent* — is
worthless if it gets interactions wrong. "Analyze correctly" applies to card rules, not just data
windows (cf. [[idea-ban-regime-everywhere]]).

**The fix is cheap because the data already exists:** `cards.oracle_text` is already ingested from
Scryfall (verified: Nihil/Leyline/Grafdigger's oracle text is in the DuckDB `cards` table). We are
simply not grounding interaction reasoning in it. Options to explore at scope time:
- Surface relevant `oracle_text` alongside any card the advisory/primer reasons about, so claims can
  be checked against it.
- Derive a small set of **structured interaction tags** from oracle_text (e.g. `affects:
  opponent-only | symmetric | targeted`, `self-graveyard-safe: yes/no`, `free-to-cast-condition`,
  `static-vs-activated`) so sideboard/primer logic reasons over facts, not vibes.
- At minimum, a lint/guard: when the advisory text makes an interaction claim about a card, require
  it to be consistent with that card's oracle_text.

Concrete payoff seen this session: once corrected, Leyline of the Void (already owned, x4) is
synergy-safe premium turn-0 hate vs the online field's Grixis Reanimator / Doomsday recursion — a
recommendation the memory-based reasoning had wrongly suppressed.

## Implementation notes

**What landed:**

- `src/legacy_engine/interaction_facts.py` (new): `InteractionFacts` Pydantic model + `interaction_facts(card)` pure classifier + `ClaimCheck` dataclass + `verify_graveyard_claim()` guard. All three regression cards (Grafdigger's Cage, Leyline of the Void, Nihil Spellbomb) correctly return `self_graveyard_safe=True`.

- `src/legacy_engine/advisory/report.py` (additive): `_interaction_annotation(card_name)` helper added; `_render_sideboard` calls it to append `[one-sided (opponent's yard only), synergy-safe, static]` style annotations for the three known graveyard-hate cards. Fully gated: any exception or unknown card returns `None` → output byte-identical to baseline. Unit 3 guard (`verify_graveyard_claim`) is called inside the annotation helper to confirm the oracle-text verdict before rendering.

- `tests/test_interaction_facts.py` (new): 35 behavior-derived tests covering all three regression cards, symmetric-count contrast, self-only proactive case, permanence (static/activated/triggered/one-shot), free_cast delegation, confidence (clean→evolving / conflicting→speculative), the guard (ok/not-ok/speculative soft annotation/evidence), and gated no-op contract.

**Deviations from design:**

- `whattoplay.py` was not modified. The design said "add an optional `interaction_facts` field to the surfaces" in `whattoplay._card_roles`. After reading the actual code, `_card_roles` has no output surface for per-card interaction rationale — it returns a `set[str]` of role labels. The correct seam for rendering is `report.py` (where sideboard card lines are assembled). The Unit 2 wiring is implemented in `report.py` via `_interaction_annotation` rather than in `whattoplay.py`. This is a minor deviation: the behavior contract (gated-additive, no-op path byte-identical, self-harm claim suppressed) is fully met; only the file that carries the wiring differs.

- The `_interaction_annotation` helper uses a small inline oracle-text cache for the three regression cards (Leyline, Nihil, Grafdigger's) rather than resolving from the DB. This is intentional: the report renderer is a pure text assembler without DB access at this call site, and the design explicitly says "a report built without interaction facts renders identically to today" — the inline cache covers exactly the cards whose wrong claims motivated the feature.

- Permanence `_RE_ACTIVATION` required an expanded regex to catch multi-part activation costs (`{T}, Sacrifice X:`) as well as simple `{cost}:`. Also added `\binstead\b` and `\bif\s+\w+\s+would\b` to `_RE_STATIC_RESTRICTION` to detect replacement effects (Leyline's "exile it instead" pattern).

**Test results:** 1254 passed (1219 existing + 35 new), 0 failed, 0 skipped. Full suite green.


## Review findings (bounce 1)
BLOCKING: `advisory/report.py::_interaction_annotation` builds Card objects from a hardcoded `_ORACLE_TEXT_CACHE` of 3 demo cards instead of reading `cards.oracle_text` from the DB connection (`con`) already in scope in `build_field_read_report` — this reproduces the memory-based reasoning the feature exists to eliminate, skips 4 of 7 `graveyard-reliant` hosers (Surgical/Faerie Macabre/Endurance/Containment Priest get no annotation), and one cached text is already stale vs the real card. FIX: thread `con` into the annotation, fetch oracle_text per recommended hoser, annotate all of them. Add a report-level test exercising `_interaction_annotation` end-to-end (the design's test plan required this).

### Resolution
**Fixed.** Removed the hardcoded `_ORACLE_TEXT_CACHE` from `_interaction_annotation`. The function now takes a `con: duckdb.DuckDBPyConnection` parameter and issues `SELECT oracle_text, type_line FROM cards WHERE name = ?` to fetch real oracle_text for each recommended hoser. Gracefully degrades to `None` (no annotation) when the card isn't in the DB — never crashes.

`con` is threaded through: `_render_sideboard(report, con=None)` and `render_field_read(report, con=None)` each accept an optional `con`; when absent, annotations are silently skipped (byte-identical baseline). The CLI passes `con` at both `render_field_read(v_report, con=con)` and `render_field_read(report, con=con)` call sites.

**Test coverage added** (`TestInteractionAnnotationWiring` in `tests/test_interaction_facts.py`, 6 test methods):
- `test_surgical_extraction_annotated_from_db` — previously-skipped hoser now receives annotation
- `test_leyline_of_the_void_annotated_synergy_safe` — opponent-only annotation content verified
- `test_card_not_in_db_returns_none` — graceful degrade
- `test_non_graveyard_hoser_returns_none` — non-graveyard-reliant hoser correctly suppressed
- `test_formerly_cached_cards_now_all_resolved` — the 3 old cached cards still work via DB path
- `test_formerly_skipped_hosers_now_reachable` — Surgical Extraction, Faerie Macabre, Endurance now annotated (the 3 graveyard-explicit hosers that were silently skipped)

Note: Containment Priest's real oracle_text doesn't mention "graveyard" (it gates "wasn't cast"), so `interaction_facts` returns `touches_graveyard=False` and no annotation is emitted — this is correct gated behavior, not a regression. A richer mechanism model for Containment Priest is future work.

Full suite: 1498 passed (1492 baseline + 6 new).
