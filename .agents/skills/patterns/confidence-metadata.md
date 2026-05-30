---
description: How legacy-engine attaches trust to derived stats — ConfidenceMetadata + tier_for_sample. Read before emitting any computed metric (meta-share, matchup cell, positioning score).
type: pattern
kind: planning
updated: 2026-05-29
summary: |
  Every derived stat carries provenance/trust via ConfidenceMetadata (level/production/source/updated),
  and sample-size-driven stats map their n to a tier via tier_for_sample(n) (speculative <30, evolving
  30-99, established >=100). Low-confidence stats are gated/flagged, not silently shown as fact.
decisions:
  - "Derived stats carry a ConfidenceMetadata (established|evolving|speculative) — never an unlabeled number."
  - "Sample-size-driven tiers come from confidence.tier_for_sample(n); default cutoffs 30/100 from advisory-methods."
  - "Display/gate by tier: hide or heavily flag speculative (n<30); BEST-CALL recommendations only on established/evolving data."
---

# Pattern: Confidence Metadata

Derived knowledge carries a confidence tier and provenance; sample-driven stats derive their tier from n.

## Rationale
PRINCIPLES #6/#7: never emit an unlabeled meta-%; confidence-gate every derived stat. A matchup cell
from 8 matches and one from 800 must not look equally authoritative. Reuses edh-engine's
established/evolving/speculative pattern. The n→tier cutoffs (30/100) come from the advisory-methods
brief (Wilson half-width at p=0.5 is ±0.17 at n=30, ±0.096 at n=100).

## Example (canonical)
**File**: `src/legacy_engine/confidence.py`
```python
class ConfidenceMetadata(BaseModel):
    level: ConfidenceLevel = "speculative"          # established | evolving | speculative
    production: Production = "template-generated"
    source: Source = "heuristic"
    updated: date | None = None

def tier_for_sample(n, *, evolving_min=30, established_min=100) -> ConfidenceLevel:
    if n >= established_min: return "established"
    if n >= evolving_min:    return "evolving"
    return "speculative"
```
Downstream usage (analytics/advisory epics): a `MatchupCell` attaches `tier_for_sample(cell.n)`; the
report layer hides speculative cells (n<30) and only makes BEST-CALL recommendations on
established/evolving data.

## When to use
- Any emitted metric: meta-share %, matchup-cell win rate, positioning score, archetype tier, card tag
  derived by heuristic.

## When NOT to use
- Raw ingested facts (a decklist's card list isn't "confidence-rated" — it's data). Confidence is for
  *derived* knowledge.

## Common violations
- Emitting a win rate / meta-% without sample size + tier.
- Hand-rolling tier cutoffs instead of calling `tier_for_sample`.
- Showing a speculative (n<30) cell as if established.
