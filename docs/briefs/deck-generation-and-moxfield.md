---
description: How should legacy-engine generate/tune decklists from its meta + advisory layers, and surface them to Moxfield? Read before designing epic-deck-generation.
type: brief
kind: research
research_method: /brief
updated: 2026-05-30
blocks_phase: epic-deck-generation
status: draft
summary: |
  Unblocks the deferred deck-generation pillar. Two halves: (1) the Moxfield integration path — there is
  NO official public API, the unofficial endpoints are Cloudflare-gated and ToS-restricted, so the engine
  should treat Moxfield as an EXPORT target (emit importable decklist text / deep links) rather than push
  programmatically; sanctioned read access is via support@moxfield.com for a custom User-Agent. (2) A
  deck-generation/tuning approach that consumes the already-built meta-share, matchup matrix, positioning
  score, and sideboard recommender — consensus-baseline → field-tuning → gap discovery — gated on first
  fixing the advisory heuristic limitations surfaced by real-data use this session.
key_findings:
  - "Moxfield has NO official public/write API. Unofficial api2.moxfield.com (v2/v3) is Cloudflare-protected and reverse-engineered; community libraries (cloudscraper-based) are read-only. Scraping violates Moxfield ToS; the sanctioned path for tools is emailing support@moxfield.com to register a custom User-Agent (read access)."
  - "Programmatic deck CREATE/UPDATE requires an authenticated user session (bearer + Cloudflare) and is undocumented + ToS-gray + fragile. Do NOT build a native push for MVP. Treat Moxfield as an export sink: emit standard importable decklist text and/or a prefilled deep link the user pastes/imports."
  - "Moxfield import format is the MTG-standard '<qty> <Card Name> [(SET) collector#]' one per line, with a 'Sideboard' section header. The engine's consensus lists already import as-is — no format work needed for export."
  - "Deck generation should consume existing layers, not reinvent: positioning S(D)/Ū rank candidate shells; the matchup matrix tunes the maindeck against the field; the sideboard recommender builds the 15; the version-stamped ban list validates legality (banlist.validate_deck)."
  - "Three generation modes: (a) consensus baseline (modal cards per archetype — already prototyped), (b) field-tuning (optimize a shell's 60+15 against the current/projected field), (c) gap discovery (shells with high positioning S but low field share, or cards over-performing on win-rate yet under-played)."
  - "HARD PREREQUISITE: the advisory heuristic gaps found via real-data use (proactivity mis-rating creature-tempo, P(best) thin-data bias, sideboard binary-coverage budget under-fill, vulnerability-tag presence inflation) must be fixed first — a generator built on them inherits and amplifies the errors. Deck-gen depends_on those improvement items."
  - "Goldfish-simulation (speed/consistency/mulligan) is a SEPARATE deferred pillar; a mature generator should goldfish-validate candidates, but that integration is out of this brief's scope."
---

# Brief: Deck Generation & Moxfield Surfacing

## Purpose

Unblocks **`epic-deck-generation`** (currently `[needs-brief]`). Answers two builder questions: *how does the
engine put a generated list in front of the user on Moxfield?* and *how does it generate/tune a list from the
meta + advisory layers we already shipped?* Grounded in `docs/briefs/advisory-methods.md` and the real-data
limitations found exercising the advisory pillar on the 2,449-tournament corpus this session.

---

## Part 1 — Moxfield integration (the surfacing path)

### 1.1 The hard constraint: no official API, write access is off-limits

- **There is no official public Moxfield API.** The site is served by an unofficial, undocumented JSON API at
  `api2.moxfield.com` (`/v2/...`, `/v3/...`), fronted by **Cloudflare** (JS challenge). Community wrappers
  (e.g. `spoved/moxfield.cr`, `Aleqsd/moxfield-api`, `MarioMH8/moxfield-api`) reach it via `cloudscraper`-style
  challenge bypass and are **read-only** (deck/card retrieval).
- **Scraping violates Moxfield's ToS.** Their stated developer path is to **email `support@moxfield.com` to
  request a custom `User-Agent`** for *read* access — i.e. sanctioned consumption, not a write API.
- **Programmatic deck create/update** would require an authenticated *user session* (bearer token captured from
  a logged-in browser + Cloudflare clearance). It is undocumented, brittle (breaks on Cloudflare/endpoint
  changes), and ToS-gray. **Do not build a native push for the MVP.**

### 1.2 Recommended path: Moxfield as an *export sink*, not a push target

Treat surfacing as **"emit something the user imports,"** not "the engine writes to their account":

1. **Decklist text export (primary).** Emit the standard MTG import format Moxfield accepts:
   ```
   <qty> <Card Name>          # e.g. "4 Brainstorm"   (optional: "(SET) collector#")
   ... maindeck ...

   Sideboard
   <qty> <Card Name>
   ```
   One card per line; a `Sideboard` header splits the boards. The engine's consensus lists already conform —
   **no format work needed.** Write to a `.txt` and/or stdout; the user pastes into **Moxfield → New Deck →
   Import**.
2. **Deep link (convenience).** Optionally produce a Moxfield import/new-deck URL or a "copy to clipboard"
   block in CLI output so the hop is one paste.
3. **Sanctioned read (optional, later).** If the engine ever needs to *pull* a user's Moxfield deck/collection
   to tune against, do it through the support@moxfield.com custom-User-Agent path, rate-limited and sequential
   (community norm: serial requests, no parallel hammering), behind the existing `ingestion/` port so it's
   swappable.
4. **Native push (only if sanctioned).** If a true "publish to my Moxfield" feature is wanted, gate it on
   obtaining explicit Moxfield permission; otherwise ship export + deep-link and stop. **Flag this as a product
   decision, not an engineering default.**

**Implementation note.** Export is a pure presentation concern — it belongs next to the advisory `report`
surface (a `--moxfield` / `export deck` output), reuses the existing decklist representation, and makes **zero
network calls**. This keeps the whole generation pipeline offline-reproducible (the project's core principle).

### 1.3 Portability hedge

Emit the same standard text for **Archidekt / TappedOut / MTGGoldfish / .dec** too (they share the
`<qty> <name>` shape). One exporter, many targets — avoids coupling the engine to Moxfield specifically given
the API uncertainty.

---

## Part 2 — Deck generation & tuning (consume what we built)

### 2.1 Principle: orchestrate the existing layers, reinvent nothing

The advisory pillar already provides every primitive a generator needs:

| Need | Existing engine layer |
|---|---|
| What's the field? | `advisory/field.py` — `FieldDistribution` (global from meta-share + custom/projected) |
| Is a deck well-positioned? | `advisory/positioning.py` — `S(D)` (best-call), `Ū` (best-deck), `rank_decks` |
| How does a deck fare card-by-card? | `analytics/matchup.py` — `MatchupCell` matrix (Wilson/Jeffreys + shrinkage, n-gated) |
| What 15 to bring? | `advisory/sideboard.py` — weighted max-coverage ILP + greedy |
| Is the list legal? | `ingestion/banlist.py` — `validate_deck(maindeck, sideboard, snapshot)` against the version-stamped ban list |
| What does the field play? | `analytics/metashare.py` + `deck_cards` aggregates (consensus skeleton) |

Generation = a new `generation/` module that *composes* these, per the architecture's deferred seam.

### 2.2 Three generation modes (build in this order)

1. **Consensus baseline (prototyped this session).** For an archetype, take each card's inclusion-% across that
   archetype's decks in the target window × its modal count, greedily fill 60 main + 15 side. Cheap, faithful
   to "what wins now." *Known limitation:* modal-count greedy fill can over/undershoot 60 and double-list flex
   cards across main/side — the generator must reconcile to a legal, exactly-60 list and de-dupe. This is the
   floor, not the goal.
2. **Field-tuning (the core feature).** Given a shell (consensus or user-supplied), optimize the 60+15 against
   the **current or projected** field: swap maindeck flex slots toward cards/configs with better field-weighted
   matchup equity (matchup matrix × field share), then run the sideboard recommender for the 15. Validate
   legality every step. Report the *before/after* positioning `S` so the tuning is auditable (per the
   audit-trail principle).
3. **Gap discovery (the differentiator).** Surface *under-explored* opportunities:
   - **Archetype gaps:** shells with **high positioning `S` but low field share** (good vs the field, few
     people on it) — the "best call nobody's making."
   - **Card gaps:** cards with **above-replacement win-rate signal but low play-rate** within a shell (needs
     per-card win-rate, a future match-results extension), or hosers whose `field_share × swing` is high but
     under-sided.
   Frame these as *candidates with evidence*, never as proven decks — gate on confidence tiers.

### 2.3 HARD prerequisite — fix the advisory heuristic gaps first

Real-data use this session showed the advisory heuristic layer is not yet accurate enough to *generate* on
(a generator amplifies its inputs' errors). Deck-gen **depends_on** these filed items:

- `improve-whattoplay-proactivity-threat-signal` — proactivity mis-rates creature-tempo (no threat signal);
  vulnerability tags use presence not density (false positives).
- `improve-positioning-pbest-uneven-sample` — `P(best)` is biased toward thin-matchup-data decks; ranking must
  gate/weight by data sufficiency.
- `improve-sideboard-realdata-quality` — binary coverage under-fills the 15-slot budget (needs the saturating
  `g(n)` objective); tag inflation (`greedy-manabase` read 100% of field).

Until these land, a generator's "tune" and "discover" outputs will be confidently wrong. The **consensus
baseline (mode 1) is safe to ship first** because it's pure data aggregation, not heuristic.

### 2.4 Data-quality realities to design around

- **Bimodal coverage:** matchup tuning is only reliable where matchup-n ≥ 30; for a thin shell, the generator
  must fall back to consensus + legality and *say so* (don't fabricate a tuned edge from imputed cells).
- **Regime sensitivity:** generate against a *windowed* field (post-latest-ban), not the year aggregate — the
  session showed bans rewrite the meta (Reanimator 14.7%→0.1% on the Entomb ban). Reuse the trends regime
  windowing to scope the generation corpus.
- **Legality is live data:** always `validate_deck` against the as-of-date ban snapshot — a generated list must
  not run a banned card (e.g. post-2026-05-18 lists must drop Undercity Informer).

### 2.5 Out of scope (separate pillars)

- **Goldfish simulation** (speed/consistency/mulligan, London-mulligan modeling) is its own deferred pillar.
  A mature generator *should* goldfish-validate a candidate's clock/consistency, but that integration is a
  later cross-pillar concern — not this brief.
- **Collection-aware building** (own-only / budget) needs the Moxfield *read* path (§1.2.3) and is post-MVP.

---

## Implementation Notes (for `generation/` + export)

- **Module seam:** `src/legacy_engine/generation/` (per ARCHITECTURE's deferred seam) composing `advisory/` +
  `analytics/` + `banlist`; a CLI surface under a `generate` group (`generate tune --deck --field`,
  `generate discover --field`) mirroring the `advise` group's input plumbing (deck/field files, `--db`).
- **Export:** an `export deck --format moxfield|archidekt|text` leaf (or a `--moxfield` flag on generate/advise
  output) emitting the standard `<qty> <name>` + `Sideboard` text. Pure, offline, reuses the decklist type.
- **Dependencies:** `depends_on` the three advisory-improvement items for modes 2–3; mode 1 (consensus) +
  export can ship independently.
- **No new external deps** for export. For any *sanctioned* Moxfield read: an `httpx`-based client behind the
  `ingestion/` port, serial + custom User-Agent, never parallel — and only after support@moxfield.com sign-off.

## Sources

- Moxfield FAQ / help (import-by-text, importing): [moxfield.com/help/faq](https://moxfield.com/help/faq),
  [Import by Text List (Moxfield Feedback)](https://moxfield.nolt.io/1141),
  [Open API for deck info (Moxfield Feedback)](https://moxfield.nolt.io/1431)
- Unofficial API wrappers (read-only, Cloudflare bypass): [Aleqsd/moxfield-api](https://github.com/Aleqsd/moxfield-api),
  [spoved/moxfield.cr](https://github.com/spoved/moxfield.cr), [MarioMH8/moxfield-api](https://github.com/MarioMH8/moxfield-api)
- ToS / developer-access (custom User-Agent via support@moxfield.com): Moxfield FAQ + community notes (mtg_parser PyPI).
- Internal: `docs/briefs/advisory-methods.md` (positioning, matchup, sideboard methods); session real-data findings
  (`.work/active/features/improve-whattoplay-proactivity-threat-signal.md`,
  `improve-positioning-pbest-uneven-sample.md`, `improve-sideboard-realdata-quality.md`);
  `docs/ARCHITECTURE.md` (`generation/` deferred seam); `src/legacy_engine/ingestion/banlist.py`.
</content>
</invoke>
