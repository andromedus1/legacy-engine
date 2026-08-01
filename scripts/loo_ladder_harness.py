"""LOO ladder-order harness — the measured decision behind ``chain.FAMILY_FIRST_KINDS``
(epic-superarchetype-layer-chain Unit 2; era addendum #2 rule 5).

Question it answers, per attribution kind: for a subject whose stable era just reset, which
predicts the cell's eventual post-era value better — its OWN pre-disturbance anchor (what
``build_multi_split_adaptive``'s cross-era prior serves today) or FAMILY-CURRENT imputation
(the definer+curated siblings' pooled rate, leave-subject-out — what ``aggregate.impute_cell``
serves)? Hypothesis under test: family-first for composition-disturbed subjects (ban/release),
anchor-first for drift-only (unattributed). Do not assert; measure.

Design (mirrors serving, per the feature design):

- one row per (disturbed parent entity E, opponent O): E has an accepted ``stable_since`` B with
  a winning-boundary attribution kind, a family in the serving registry, and at least one
  contributor sibling; O is a parent entity outside E's family;
- **truth** = E vs O raw rate over the SERVING window ``[max(B, O_since), None)`` with
  ``n >= --truth-min`` (the cell's eventual mature value);
- **anchor** = ``beta_binomial_shrink_to(pre_w, pre_n, prior_mean=shrunk pre-marginal of E)``
  over ``[None, B)`` — the ``_cross_era_prior`` construction at parent level (no pre-n floor:
  serving has none either; the median pre-n is reported so thinness stays visible);
- **family** = contributor siblings' pooled rate vs O, each sibling pairwise-windowed
  ``[max(sibling_since, O_since), None)`` (member's current stable era — era addendum #2 rule 2),
  pool floor ``--pool-min``;
- **marginal** (context column only) = E's own truth-window marginal rate — the incumbent the
  epic's 2026-08-01 probe beat; reported so the family column has a familiar reference.

Read-only: opens the DB with ``read_only=True`` and never writes anything. This is a measurement
instrument, not the serving path — the serving path draws member tallies from the adaptive
multi-split build; the harness reproduces the same windows with direct parent-level scans.

Decision rule (fixed BEFORE looking at the numbers): a kind is encoded family-first when it has
at least ``--min-cells`` comparable cells AND family MAE < anchor MAE. A kind below the cell
floor keeps the existing anchor order, named as too thin. The winner is ENCODED in
``analytics/superarchetype/chain.py``; this script is the reproducible receipt.

Run: ``.venv/bin/python scripts/loo_ladder_harness.py [--db data/legacy.duckdb]``
"""

from __future__ import annotations

import argparse
import sys
from statistics import median

import duckdb

from legacy_engine.analytics.match_results import compute_match_results
from legacy_engine.analytics.matchup import (
    beta_binomial_shrink,
    beta_binomial_shrink_to,
)
from legacy_engine.analytics.superarchetype.registry import read_superarchetype_members
from legacy_engine.config import DUCKDB_PATH

TRUTH_MIN_DEFAULT = 20
POOL_MIN_DEFAULT = 40
MIN_CELLS_PER_KIND_DEFAULT = 10

_CONTRIBUTOR_PROVENANCE = frozenset({"derived", "curated"})


def _winning_kind(entry) -> str | None:
    if entry.stable_since is None:
        return None
    for b in entry.boundaries:
        if b.bh_accepted and not b.floor_rejected and b.date == entry.stable_since:
            return b.attribution.kind if b.attribution is not None else None
    return None


class _ScanCache:
    """One ``compute_match_results`` per distinct (since, until) — never per cell."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con
        self._cache: dict[tuple[str | None, str | None], object] = {}

    def get(self, since: str | None, until: str | None):
        key = (since, until)
        if key not in self._cache:
            self._cache[key] = compute_match_results(self._con, since=since, until=until)
        return self._cache[key]


def _tally(mr, a: str, b: str) -> tuple[int, int]:
    t = mr.matchups.get((a, b))
    return (t.wins, t.n) if t is not None else (0, 0)


def _pairwise_since(*dates: str | None) -> str | None:
    return max(d or "" for d in dates) or None


def run_harness(
    db: str,
    *,
    truth_min: int = TRUTH_MIN_DEFAULT,
    pool_min: int = POOL_MIN_DEFAULT,
    min_cells: int = MIN_CELLS_PER_KIND_DEFAULT,
) -> int:
    from legacy_engine.analytics.eras.store import read_entity_eras

    con = duckdb.connect(db, read_only=True)
    try:
        registry = read_superarchetype_members(con)
        if registry is None:
            print("no superarchetype registry in this DB — run `superarchetype run` first")
            return 1
        stored = read_entity_eras(con)
        if not stored:
            print("no entity_eras rows — run `eras run` first")
            return 1

        cluster_of: dict[str, str] = {}
        contributors: dict[str, list[str]] = {}
        for cluster in registry.clusters:
            contributors[cluster.id] = [
                m.archetype for m in cluster.members
                if m.provenance in _CONTRIBUTOR_PROVENANCE
            ]
            for m in cluster.members:
                cluster_of[m.archetype] = cluster.id

        parent_since = {
            e.entity: e.stable_since for e in stored.values() if e.parent == e.entity
        }

        scans = _ScanCache(con)
        full = scans.get(None, None)
        opponents = sorted(a for a in full.archetypes if " [" not in a)

        rows: list[dict] = []
        n_disturbances = 0
        for entity in sorted(stored):
            entry = stored[entity]
            if entry.parent != entry.entity or entry.stable_since is None:
                continue
            kind = _winning_kind(entry)
            if kind is None:
                continue
            family = cluster_of.get(entity)
            if family is None:
                continue
            siblings = [s for s in contributors.get(family, []) if s != entity]
            if not siblings:
                continue
            n_disturbances += 1
            boundary = entry.stable_since

            pre = scans.get(None, boundary)
            rec_pre = pre.archetypes.get(entity)
            marg_pre = beta_binomial_shrink(
                rec_pre.wins if rec_pre else 0, rec_pre.n if rec_pre else 0
            )

            in_family = {m.archetype for c in registry.clusters if c.id == family
                         for m in c.members}
            for opponent in opponents:
                if opponent == entity or opponent in in_family:
                    continue
                o_since = parent_since.get(opponent)
                truth_mr = scans.get(_pairwise_since(boundary, o_since), None)
                t_wins, t_n = _tally(truth_mr, entity, opponent)
                if t_n < truth_min:
                    continue
                truth = t_wins / t_n

                pre_w, pre_n = _tally(pre, entity, opponent)
                anchor = beta_binomial_shrink_to(pre_w, pre_n, prior_mean=marg_pre)

                pool_w = pool_n = 0
                for sibling in siblings:
                    s_since = parent_since.get(sibling)
                    s_mr = scans.get(_pairwise_since(s_since, o_since), None)
                    w, n = _tally(s_mr, sibling, opponent)
                    pool_w += w
                    pool_n += n
                if pool_n < pool_min:
                    continue
                family_p = pool_w / pool_n

                rec_truth = truth_mr.archetypes.get(entity)
                marginal = (rec_truth.wins / rec_truth.n) if rec_truth and rec_truth.n else 0.5

                rows.append({
                    "entity": entity, "opponent": opponent, "kind": kind,
                    "boundary": boundary, "truth": truth, "truth_n": t_n,
                    "anchor": anchor, "pre_n": pre_n,
                    "family": family_p, "pool_n": pool_n, "family_id": family,
                    "marginal": marginal,
                })

        print(f"// loo-ladder-harness: db={db} (read-only)")
        print(f"// registry: {len(registry.clusters)} clusters, "
              f"window {registry.window_since or 'FULL'}..{registry.window_until or 'open'}")
        print(f"// disturbances with a contributing family: {n_disturbances}; "
              f"comparable cells: {len(rows)} "
              f"(truth n>={truth_min}, sibling pool n>={pool_min})")
        if rows:
            print(f"// median pre-disturbance cell n behind the anchor: "
                  f"{median(r['pre_n'] for r in rows):.0f}")

        verdict: dict[str, bool] = {}
        for kind in ("ban", "release", "unattributed"):
            sub = [r for r in rows if r["kind"] == kind]
            _report_bucket(kind, sub)
            verdict[kind] = _decide(kind, sub, min_cells)
        composition = [r for r in rows if r["kind"] in ("ban", "release")]
        _report_bucket("composition (ban+release)", composition)

        family_first = sorted(k for k, v in verdict.items() if v)
        print(f"\nFAMILY_FIRST_KINDS verdict: {family_first or '(none — anchor-first everywhere)'}")
        print("// encode this frozenset in analytics/superarchetype/chain.py with these numbers "
              "at the definition site")

        for r in sorted(rows, key=lambda r: (r["kind"], r["entity"], r["opponent"]))[:200]:
            print(
                f"  [{r['kind']:12s}] {r['entity']} vs {r['opponent']} (since {r['boundary']}): "
                f"truth {r['truth']:.3f} (n={r['truth_n']}) | anchor {r['anchor']:.3f} "
                f"(pre n={r['pre_n']}) | family {r['family']:.3f} "
                f"({r['family_id']}, pool n={r['pool_n']}) | marginal {r['marginal']:.3f}"
            )
        return 0
    finally:
        con.close()


def _mae(rows: list[dict], key: str) -> float:
    return sum(abs(r[key] - r["truth"]) for r in rows) / len(rows)


def _report_bucket(name: str, rows: list[dict]) -> None:
    if not rows:
        print(f"\n{name}: 0 comparable cells — too thin to measure")
        return
    wins_family = sum(1 for r in rows if abs(r["family"] - r["truth"]) < abs(r["anchor"] - r["truth"]))
    print(
        f"\n{name}: {len(rows)} cells | MAE anchor {_mae(rows, 'anchor'):.4f} vs "
        f"family {_mae(rows, 'family'):.4f} (marginal {_mae(rows, 'marginal'):.4f}) | "
        f"family wins {wins_family}/{len(rows)}"
    )


def _decide(kind: str, rows: list[dict], min_cells: int) -> bool:
    if len(rows) < min_cells:
        print(f"  -> {kind}: {len(rows)} < {min_cells} cells — TOO THIN; "
              "keep the existing anchor order (named, honest)")
        return False
    family_first = _mae(rows, "family") < _mae(rows, "anchor")
    print(f"  -> {kind}: {'FAMILY-FIRST' if family_first else 'ANCHOR-FIRST'} by MAE")
    return family_first


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--db", default=str(DUCKDB_PATH))
    parser.add_argument("--truth-min", type=int, default=TRUTH_MIN_DEFAULT)
    parser.add_argument("--pool-min", type=int, default=POOL_MIN_DEFAULT)
    parser.add_argument("--min-cells", type=int, default=MIN_CELLS_PER_KIND_DEFAULT)
    args = parser.parse_args()
    return run_harness(
        args.db, truth_min=args.truth_min, pool_min=args.pool_min, min_cells=args.min_cells,
    )


if __name__ == "__main__":
    sys.exit(main())
