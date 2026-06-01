---
id: epic-regime-aware-advisory-adaptive
kind: feature
stage: done
tags: [advisory, analytics, correctness]
parent: epic-regime-aware-advisory
depends_on: [epic-regime-aware-advisory-windowing-core, epic-regime-aware-advisory-cli-surface]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Adaptive Per-Cell Windowing (v2)

## Brief

The smart layer: instead of one uniform window for everyone, give each archetype its own valid
history horizon based on whether recent bans actually touched it, then pool each pairwise matchup
cell over the maximally-valid window.

- **Affectedness → `valid_since` per archetype.** For each ban regime boundary, an archetype is
  "affected" if it ran a banned card above an inclusion threshold in the pre-ban regime
  (data-derived from `generation/consensus.card_frequencies` × the banlist `current_banlist()` ×
  `regime_windows`). `valid_since(archetype)` = the date of the **most recent** ban that affected it
  (or the corpus start if none). Validated: affectedness is starkly bimodal (Entomb = 100% of Dimir
  Reanimator / ~0% else; Undercity Informer = 99.9% of Oops! / 0% else), so a simple threshold
  classifies cleanly. Be **conservative** where an archetype's lists churn even without a direct hit
  (the classifier catches direct hits, not indirect rebuilds).
- **Per-cell windowing.** A pairwise cell `A vs B` pools data back to
  `max(valid_since(A), valid_since(B))`. Unaffected×unaffected cells keep full history (established
  tier); ban-affected cells truncate honestly. **Positioning always weights by the *current* field
  shares** — so dead decks (current share ≈ 0) fall out regardless of how strong their old cells were.
- **Flip the default to adaptive** (the inherited decision): the matrix-build default and the CLI
  default become the adaptive per-cell window; `--all-time` (from `cli-surface`) remains the explicit
  full-corpus escape; `--regime`/`--since` still force a uniform window.
- **Surface the window each cell used** (auditability) — the per-cell `valid_since`/window must be
  inspectable in output, not hidden.

Does NOT cover goldfish validation; does not attempt to fix field-level power shifts beyond using
current field shares (that is the intended honest estimate).

## Epic context
- Parent epic: `epic-regime-aware-advisory`
- Position in epic: v2 — the target design; depends on `windowing-core` (the plumbing) and
  `cli-surface` (the window/default UX it re-defaults).

## Inherited design decisions
- **v2 flips the default to the adaptive per-cell window** (max valid data per matchup, current-field
  weighting); `--all-time` stays the explicit full-corpus escape.
- **Affectedness is data-derived** (banned-card inclusion), conservative when lists churn; **always
  surface the per-cell window** (audit-everything).
- **Thin-regime = degrade + loud caveat** still applies (fall back to the adaptive window / wider data
  with a banner when a forced narrow window is too thin).

## Known limits to design around (from the epic analysis)
- Card-inclusion catches **direct** ban hits, not **indirect** field-driven rebuilds — treat-as-affected
  / shorten the window when an archetype churns; surface the window so it's auditable.
- Archetype-label drift — pooling assumes "same deck" across the window; strongest for stable decks.
- **Performance**: per-cell windows mean the matrix can't be one single windowed scan. Feature-design
  must choose an efficient shape (e.g. group cells by distinct `valid_since` boundary and scan per
  group, or compute over the union then filter per-cell) — flagged as the riskiest unit.

## Research briefs
- The epic body (`## Strategic decisions`, `## Known limits`); `docs/briefs/card-adjacency-and-discovery.md`
  (`card_frequencies` inclusion as the affectedness signal; the two-level-empirical-Bayes shrink primitive).

## Foundation references
- `src/legacy_engine/ingestion/banlist.py` — `current_banlist` (banned cards × `as_of`).
- `src/legacy_engine/analytics/trends.py` — `regime_windows` (ban-date boundaries).
- `src/legacy_engine/generation/consensus.py` — `card_frequencies` (per-archetype-per-regime inclusion =
  the affectedness input).
- `windowing-core` (windowed `compute_match_results`/`build_matrix`), `advisory/positioning.py`,
  `advisory/gaps.py`, `cli-surface` (the default/flag UX to re-default).

## Design decisions
Resolved with judgment (autopilot); the strategic frame (adaptive default; current-field weighting;
data-derived affectedness; surface the window) is inherited and fixed.
- **Affectedness source = `BAN_EVENTS`** (dated `(date, card, reason)` tuples in `ingestion/banlist.py`),
  NOT `current_banlist()` (which is a single as-of snapshot). For each ban date `d`, the cards banned at
  `d` + the pre-ban regime `[prev_d, d)` give the inclusion check.
- **Affected test** = the archetype ran ANY card banned at `d` in ≥ `affect_threshold` (default **0.25**)
  of its decks in `[prev_d, d)` (either board). 0.25 is conservative-but-decisive given the observed
  bimodality (≈100% vs ≈0%); a card in a quarter of an archetype's lists is clearly core to it.
  `valid_since(A)` = the LATEST `d` that affected `A` (ISO string), or `None` if never affected.
- **Multi-scan assembly, not per-cell scan** — run `compute_match_results(since=s)` ONCE per distinct
  `valid_since` value `s` (≤ #ban-dates ≈ 8 scans), then for ordered cell `(A,B)` pull the tally from
  the scan keyed by `since_AB = max(valid_since(A), valid_since(B))` (None = full corpus = earliest, so
  it sorts first; `max("" for None) → None`). This is O(#distinct-boundaries) scans, not O(cells).
- **Row inclusion + marginals from the FULL-corpus scan** (stable, matches `build_matrix`'s
  `min_row_share` rule); only the per-cell *data sourcing* is adaptive. Mirror cell for `A` comes from
  the `valid_since(A)` scan's `mirror_n`.
- **Default flip = matrix-adaptive + field-current** (for matchup consumers only): with NO window flags,
  `report matchups`/`report gaps`/`advise positioning|whattoplay|report` build the **adaptive matrix**
  AND weight by the **current-regime field** (`build_global_field` over `resolve_regime("current")`).
  This is what drops dead decks: Reanimator's old cells survive in the matrix, but its ≈0 current-field
  share zeroes its positioning weight. `--all-time` → full-corpus matrix + full-corpus field (v1 escape);
  `--regime`/`--since` → uniform window (v1 behavior, both legs). **`report meta` is deck-based and
  unaffected by the flip** — its default stays full-corpus (no matchup matrix to make adaptive).
- **Audit surfacing** = the adaptive matrix carries a `cell_windows: dict[(a,b)->since|None]`; the CLI
  prints a compact per-archetype `valid_since` summary (not every cell) under the window header.
- **Thin current-regime field** uses the existing deck-based `thin_floor=0` path (tiers convey thinness);
  the matrix is adaptive (always has data), so the v1 rounds-degrade banner is not needed in adaptive mode.

## Architectural choice
Adaptive windowing is a **cell-sourcing** layer over the v1 windowed `compute_match_results`, not a new
query path: it reuses windowed scans (≤8 of them, one per distinct `valid_since`) and stitches the
matrix cell-by-cell from the right scan. Rejected: (A) per-cell SQL windows — O(cells) scans, slow and
complex; (B) recency-weighting instead of hard per-cell windows — softer but opaque/unauditable (the
epic explicitly defers it). The default-flip separates the two contamination sources cleanly — pairwise
cells get maximally-valid data; the field is always current — which is the whole point of the epic.

## Implementation Units

### Unit 1: affectedness classifier
**File**: `src/legacy_engine/advisory/regime_affectedness.py` (new)
```python
def archetype_valid_since(
    con, archetypes: list[str], *, provenance: str | None = None, affect_threshold: float = 0.25,
) -> dict[str, str | None]:
    """valid_since[A] = ISO date of the LATEST ban that materially affected A (ran a banned card in
    ≥ affect_threshold of its pre-ban decks), or None if never affected. Uses BAN_EVENTS + a
    per-(archetype, pre-ban-window) deck-inclusion query (either board)."""
```
**Implementation Notes**: group `BAN_EVENTS` by date → `{d: [cards]}`; pre-ban window for `d` = `[prev_d, d)`
(prev_d = previous ban date or None). One inclusion query per (archetype, d) over `decks ⋈ deck_cards`
(any board) — or batch per d. Conservative: when an archetype has < a few decks in the pre-ban window,
leave it unaffected at that d (can't judge) but document. Returns only the requested archetypes.
**Acceptance Criteria**:
- [ ] On the real corpus, `valid_since["Dimir Reanimator"] == "2025-11-10"` (Entomb) and
      `valid_since["Oops! All Spells"] == "2026-05-18"` (Undercity Informer).
- [ ] An archetype that ran no banned card → `None`.
- [ ] Threshold honored (a card in < threshold of pre-ban decks does not flag).

### Unit 2 (trickiest): adaptive matrix assembly
**File**: `src/legacy_engine/analytics/matchup.py`
```python
@dataclass
class AdaptiveMatrix:
    matrix: MatchupMatrix
    valid_since: dict[str, str | None]          # per archetype
    cell_windows: dict[tuple[str, str], str | None]  # since used per ordered cell

def build_adaptive_matrix(
    con, *, provenance=None, min_row_share=0.02, affect_threshold=0.25,
) -> AdaptiveMatrix: ...
```
**Implementation Notes**: (1) full-corpus `compute_match_results` for row inclusion (`min_row_share`) +
marginals + `mirror_n`; (2) `archetype_valid_since(included)`; (3) `boundaries = sorted(set(vs.values()))`
→ `mr_by_since[s] = compute_match_results(since=s, provenance)` for each distinct `s` (None handled =
full corpus); (4) for each ordered `(a,b)`: `since_ab = max(vs[a] or "", vs[b] or "") or None`; tally =
`mr_by_since[since_ab].matchups.get((a,b))` → `build_cell` (n=0 if missing); mirror `(a,a)` from
`mr_by_since[vs[a]].mirror_n`. Record `cell_windows[(a,b)] = since_ab`.
**Acceptance Criteria**:
- [ ] ≤ (#distinct valid_since) calls to `compute_match_results` (assert via a spy/counter on a fixture).
- [ ] A cell between two unaffected archetypes uses the full-corpus window; a cell touching an affected
      archetype uses `max` of the two valid_since dates.
- [ ] `matrix.archetypes` == the full-corpus `min_row_share` row set (stable inclusion).
- [ ] Hand-built multi-regime fixture: an affected archetype's cell pulls from the post-ban scan (fewer n).

### Unit 3: default-flip wiring (matrix consumers)
**File**: `src/legacy_engine/cli.py` + `advisory/window.py`
**Implementation Notes**: add `mode` to `WindowResolution` (`"adaptive" | "uniform" | "full"`):
default → `adaptive`; `--all-time` → `full`; `--regime`/`--since`/`--until` → `uniform` (v1 path, may
degrade). `report matchups`/`report gaps`/`advise positioning|whattoplay|report`: if `mode=="adaptive"`
→ `build_adaptive_matrix(...)` + field over `resolve_regime("current")`; else v1 (`build_matrix(since,
until)` + windowed/full field). `report meta` keeps `thin_floor=0` and is NOT switched to adaptive.
Echo the mode + a compact `valid_since` summary in adaptive mode.
**Acceptance Criteria**:
- [ ] No-flags `report matchups` uses the adaptive matrix + current field (mode line shown).
- [ ] `--all-time` → full-corpus matrix + full field (v1 escape), no adaptive.
- [ ] `--regime current` → uniform v1 path (may degrade) — adaptive is the DEFAULT, regime is explicit-uniform.
- [ ] `advise positioning` (no flags) over the real DB no longer ranks dead-but-historically-strong decks
      at the top (Reanimator's current share ≈ 0 zeroes its weight).

### Unit 4: audit echo
**File**: `src/legacy_engine/cli.py`
**Implementation Notes**: extend `_echo_window` (or a sibling) to print, in adaptive mode, a one-line
per-affected-archetype `valid_since` summary (e.g. `// adaptive: Dimir Reanimator since 2025-11-10; Oops!
All Spells since 2026-05-18; others full-corpus`). Don't dump all cells.
**Acceptance Criteria**:
- [ ] Adaptive output names the affected archetypes + their valid_since; unaffected summarized as full-corpus.

## Implementation Order
1. Unit 1 (affectedness) — independent, real-data-verifiable first.
2. Unit 2 (adaptive matrix) — the core; depends on Unit 1.
3. Unit 3 (default-flip wiring) + Unit 4 (audit echo).

## Testing
### Unit tests: `tests/test_regime_affectedness.py`, `tests/test_adaptive_matrix.py`, `tests/test_advisory_window.py` (mode), CLI
- `archetype_valid_since`: real-DB Reanimator→2025-11-10, Oops!→2026-05-18, an unaffected→None; threshold boundary.
- `build_adaptive_matrix`: hand-built 2-regime corpus (a card banned mid-corpus that one archetype ran) →
  affected cell pulls post-ban (smaller n), unaffected cell pulls full; scan-count ≤ distinct boundaries
  (counter spy); row set == full-corpus inclusion.
- `WindowResolution.mode`: default→adaptive, --all-time→full, --regime→uniform.
- CLI: no-flags matchups shows adaptive + valid_since summary; --all-time full; real-DB `advise positioning`
  default drops Reanimator from the top (integration, seeded real DB) — or a synthetic equivalent.
### Integration
- Real-DB `advise positioning` (no flags) → top deck is a CURRENTLY-played archetype, not Dimir Reanimator;
  the audit line shows Reanimator's valid_since.

## Risks
- **Affectedness misses indirect rebuilds** (catches direct banned-card hits only) — conservative + audited;
  documented epic-level limit. **Fallback**: a curated override list later if needed.
- **Scan count** — ≤ ~8 `compute_match_results` per adaptive build (one per distinct valid_since). Each is a
  full-corpus-ish scan; acceptable for a CLI tool, but note it. **Fallback**: cache `mr_by_since` within a
  single command; memoize if a hot path emerges.
- **Default-flip is a behavior change** — `--all-time` is the documented escape; communicate in the mode
  line. **Fallback**: none; this is the inherited strategic decision.
- **Pre-ban window too thin to judge affectedness** for a niche archetype → left unaffected (full history).
  Acceptable (niche decks have little data either way); audited via the valid_since summary.

## Implementation notes
- Files changed: `analytics/affectedness.py` (new — `archetype_valid_since`, batched 1 query/ban-date), `analytics/matchup.py` (`AdaptiveMatrix` + `build_adaptive_matrix`: ≤(#distinct valid_since) scans, per-cell `max(vs)` sourcing), `advisory/window.py` (`WindowResolution.mode` + `AdvisoryInputs` + `build_advisory_inputs` + `_adaptive_audit` + `adaptive_default` param), `cli.py` (`_window_opts`/`_echo_window` mode-aware; default-flip wired into report matchups/gaps + advise positioning/whattoplay/report; `report meta` opts out via `adaptive_default=False`), `advisory/report.py` (`build_field_read_report` matrix injection), `advisory/gaps.py` (`compute_archetype_gaps` matrix+field injection).
- Affectedness placed in `analytics/` (not advisory) to keep `analytics → advisory` acyclic — `build_adaptive_matrix` (analytics) consumes it.
- Tests added: `tests/test_adaptive_regime.py` (7: affectedness×2, adaptive-matrix×2 incl scan-count spy, mode×3). Updated `test_gaps.py` (gaps CLI now needs `--all-time` for full-corpus) + `test_advisory_window.py` (matchups default = adaptive).
- Suite: 1043 passing (was 1020 at epic start, +23 net for v2). ruff clean on all new/changed non-cli files.
- Discrepancies from design: none material. Built Units 1–4. One refinement: added `adaptive_default=False` so `report meta` (deck-based) keeps full-corpus default + correct label, rather than inheriting the adaptive default it doesn't use.
- **End-to-end validated on real DB**: `advise positioning` (default=adaptive) now ranks Lands/Show and Tell/Doomsday/Death & Taxes/Izzet Delver at the top — **Dimir Reanimator dropped out** (≈0 current-regime share zeroes its weight despite strong historical cells); the audit line shows per-archetype valid_since (Reanimator since 2025-11-10 = Entomb). The stale-after-ban best-deck artifact is fixed. `--all-time` restores the full-corpus view.
- Adjacent issues parked: none.

## Review record
- **Verdict: Approve** (deep lane, fresh-context Opus sub-agent — NOT cross-model; Codex out of credits). 201 tests green across touched + downstream consumer suites (matchup/positioning incl.).
- Verified: affectedness pre-ban window `[prev_d,d)` + latest-ban-wins iteration + inclusion ratio + param order (no bug); adaptive `s_ab=max(...)` provably always a `mr_by_since` key (no KeyError path); mirror sourcing; full-corpus row inclusion (stable); scan count ≤ #distinct valid_since; default-flip modes distinct; `report meta` opts out (deck-based); current-regime field + adaptive matrix (dead decks drop); matrix/field injection additive (un-injected callers byte-identical); no analytics→advisory cycle; conservative thin-sample (decks==0 → unaffected); non-vacuous tests.
- No Blockers, no Important. 1 nit: design Unit headers name `advisory/regime_affectedness.py` vs shipped `analytics/affectedness.py` — already reconciled in the impl notes (analytics-placement rationale). Doc-only.
