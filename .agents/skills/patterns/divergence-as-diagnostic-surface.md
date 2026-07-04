# Divergence-as-Diagnostic Surface

Compute the disagreement between two signals as a first-class typed output — a labeled
delta/partition plus a tier/confidence honesty annotation framing it as "investigate", not "error".

## Rationale

The engine's value is often in where two independent signals *disagree* (scorer vs winners, venue A
vs B, heuristic vs empirical). Rather than hiding this behind a single blended number, surface the
divergence itself as the deliverable, annotated with the sample tier so the user knows whether the
gap is real or noise. Distinct from `honest-degrade-marker` (which degrades on *thin* data); here
both signals are present and the *gap between them* is the product. Never auto-calibrate the gap
away — divergence is a flag for a human (missing mechanic OR a genuine edge).

## Examples

### Example 1: board backtest partition
**File**: `src/legacy_engine/advisory/backtest.py:79`
```python
overlap: tuple[str, ...]      # recommended AND commonly-played
scorer_only: tuple[str, ...]  # recommended but rarely played (candidate false positives)
winners_only: tuple[str, ...] # commonly played but NOT recommended (candidate blind spots)
confidence: "ConfidenceLevel | None"  # tier_for_sample(n_winning_decks), None if n==0
```

### Example 2: venue divergence
**File**: `src/legacy_engine/analytics/venue.py:153`
`ArchetypeDivergence` carries `spread = max(share) - min(share)` + `max_venue`/`min_venue`;
`venue_divergence()` (`:174`) sorts desc by spread with tier annotations (`:263`).

### Example 3: what-to-play heuristic vs empirical
**File**: `src/legacy_engine/advisory/whattoplay.py:998`
`_explain()` returns `(why, disagreement)`; sets the disagreement flag (`:1104`, `:1111`) with a
`[NOTE: …possible pilot-skill or low-n confound.]` when the heuristic favorite contradicts
empirical `p_shrunk`. Second surface: proactivity-score vs archetype-tag disagreements recorded
into `ProactivityProfile.findings` (`:233`/`:384`).

### Example 4: config comparator
**File**: `src/legacy_engine/advisory/compare.py:75`
`MatchupContribution.contribution_diff` + `ComparisonResult.p_a_beats_b_base` (`:87`) surface
per-matchup and overall config-A-vs-config-B disagreement.

## When to Use
- Two independently-derived signals can be compared and the user's decision hinges on where they
  disagree. Always pair the delta with a sample-tier annotation.

## When NOT to Use
- One signal is clearly authoritative (just use it).
- The disagreement is thin-data noise with no honesty gate (that's a degrade case →
  `honest-degrade-marker`).

## Common Violations
- Blending the two signals into one number so the divergence is invisible.
- Surfacing the delta without a tier/confidence annotation (implies unsupported precision).
- Framing divergence as proof of error rather than an investigation signal (repo convention:
  `cli.py:3157`, echoed in `tests/test_backtest.py:590`).
