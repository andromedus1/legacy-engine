---
id: epic-sb-advisor-correctness-sweep-polish
kind: story
stage: review
tags: [advisory, cli]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-31
---

# Sweep report polish: near-duplicate clusters + Σ-adoption formatting


# Sweep report polish — near-duplicate clusters + Σ-adoption formatting

Two cosmetic findings from the first validated `advise sweep` runs (2026-07-04):

1. **Near-duplicate clusters**: `combo` and `storm-reliant` winners-only clusters share
   almost identical membership (cards tagged with both), so one root cause renders twice.
   Consider merging clusters whose member sets are (near-)identical, or reporting the tag
   pair as one cluster key.
2. **Σ adoption formatting**: summed adoption renders as e.g. "Σ adoption 5904%" (59.04
   summed fractions × 100). Display as a unitless sum or average instead.

Diagnostic-surface behavior is correct; this is readability only.

## Implementation notes

**Files:** `src/legacy_engine/advisory/sweep.py`, `src/legacy_engine/cli.py`, `tests/test_sweep.py`.

**1. Near-duplicate clusters — merged by Jaccard similarity, not exact equality.**

`cluster_divergences` (sweep.py) now runs a post-process fold, `_merge_near_duplicate_clusters`,
over the per-tag clusters it builds: within each direction (directions never merge), it computes
the Jaccard similarity of two clusters' full member sets (`ClusterMember` — card + archetype +
adoption + confidence, not just card names) and unions them (union-find, so the merge is
transitive across 3+ mutually-similar tags) when similarity is >= `_MERGE_JACCARD_THRESHOLD`.
Merged clusters get a deterministic `tagA+tagB` key (tags sorted) and deduplicated members (a
card that attacks both merged tags was the same `ClusterMember` object in both buckets, so an
ordinary Python `set` collapses it — no double-counted adoption).

Threshold picked from the curated catalog, not guessed: `src/legacy_engine/data/hosers/legacy.json`
has 10 cards tagged `combo` and 10 tagged `storm-reliant`, with 9 shared — the realistic worst
case (exactly one catalog-only outlier diverging on each side, e.g. Engineered Explosives vs.
Damping Sphere) is Jaccard 9/11 ≈ 0.818. Picked `_MERGE_JACCARD_THRESHOLD = 0.8`: high enough
that unrelated tags never accidentally fold together, low enough to reliably catch the reported
combo/storm-reliant pair (and any future pair with the same near-total-overlap shape) even when
that worst case occurs. Extracted a shared `_cluster_from_members` helper so the initial per-tag
build and the merge step compute `n_archetypes` / `tier_breakdown` / `total_adoption` identically.

**2. Σ-adoption formatting — switched to the per-member average, in the CLI render only.**

`DivergenceCluster.total_adoption` (the Σ) is unchanged — it's still what `rank_clusters` sorts
on and still what the `--json` payload emits. Only the human-readable line in
`cli.py::advise_sweep._render_clusters` changed: `Σ adoption {total*100:.0f}%` →
`avg adoption {total/len(members):.0%}`. Rationale: the sum is unitless mass that trivially grows
with cluster size (hence "5904%"), while the mean stays bounded 0-100% and reads as an honest
percentage; cluster breadth is already conveyed by the adjacent "N archetype(s)" figure, so
nothing is lost by not also displaying the sum. A unitless-sum display (e.g. "adoption mass 59.0")
was the other option on the table but was rejected as less self-explanatory than a bounded percent
that matches the styling of every other adoption figure already on that line.

**Tests:** `tests/test_sweep.py` — new `TestMergeNearDuplicateClusters` (identical-membership
merge + sorted tag key, member dedup / no double-counted adoption, below-threshold pairs staying
separate, and a union-find transitivity case: three tags pairwise-similar at exactly the 0.8 floor
where the first and last tag alone are only ~0.636 similar, still collapse into one cluster via
the middle tag). Updated `test_multi_tag_card_contributes_to_every_tag` — it was asserting the
literal pre-fix "renders twice" shape, now split with an extra fixture card so the merge and the
per-tag-membership mechanic are each visible in isolation. Added
`test_cluster_line_shows_average_not_summed_adoption` (CLI) pinning a concrete case from the
existing hermetic backtest fixture where Σ (100%) and mean (50%) actually diverge. No golden
files pin sweep CLI output (`rg -n "GOLDEN" tests/ | rg -i sweep` — no hits), so no re-pin was
needed.

**Evidence:** `tests/test_sweep.py` 24/24 passed standalone; full suite 2983 passed, 1 skipped,
1 xfailed (`.venv/bin/python -m pytest -q`, Python 3.13.13, worktree-local venv).
