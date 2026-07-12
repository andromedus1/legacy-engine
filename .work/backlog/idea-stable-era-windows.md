---
id: idea-stable-era-windows
created: 2026-07-11
tags: [analytics, archetype, methodology]
---

# Per-archetype (and per-camp) stable-era detection → maximal solid matchup windows

**Andrew's framing (2026-07-11, verbatim intent):** when we look for deck matchups, look across
card-release and ban notices to identify STABLE ERAS per archetype and subarchetype — grab the
longest-running package of data that's in the entity's CURRENT era, where "current era" is a
per-archetype-and-subarchetype definition. Need a way to assess whether an archetype was DISTURBED:
play-rate shifts, win-rate shifts, cards directly removed by ban, cards suddenly appearing via
release. It's like the subarchetype clustering, but subarchetypes OVER TIME — and matchup
comparisons then use this to grab the biggest possible window of solid data.

**Why this is the right generalization (unifies three open threads):**
- `build_adaptive_matrix` already does per-archetype windows but ONLY from ban-affectedness
  (`valid_since`) — it is blind to RELEASE-driven disturbance (Flow State rebuilt Doomsday/Izzet/
  Dimir with no ban; the 07-11 era audit showed camps ARE list generations).
- [[idea-discovery-temporal-gate]] proposed per-regime discovery + a temporal-mixing gate — this
  idea subsumes it: detect each entity's change-points FIRST, then discover camps within stable
  windows (or equivalently: camps over time = the change-points).
- [[bug-banlist-regime-gap]] showed global regime tables lag reality (Candelabra); per-entity
  disturbance detection from the CORPUS ITSELF (play-rate cliff, list-composition jump) catches
  what announcement feeds miss, automatically.

**Disturbance signals to detect (change-point detection on per-entity weekly series):**
1. composition drift: distance between adjacent windows' consensus vectors / card-inclusion
   distributions (the same flex-band representation discovery already builds) — a jump = new era;
2. cards vanishing (ban: presence → 0 overnight) and cards appearing (release: 0 → adopted);
3. play-rate share shifts (Tron 59/wk → 1) and win-rate shifts (regime-scoped marginals);
4. cross-check against known ban/release dates (labels for detected change-points, not the source
   of truth).

**Consumption:** `stable_since(entity) = last change-point`; matchup cells source over
`[max(stable_since(a), stable_since(b)), now]` — the adaptive-matrix mechanism with a better
horizon function. Honesty: every cell carries its detected window + the triggering disturbance
("window since 2026-06-20: Flow State adoption jump"); thin post-disturbance windows degrade
honestly rather than silently pooling across a break.

**Prior art in-repo:** advisory-window-resolution-block, affectedness.py (ban horizons),
discovery.py flex-band representation (reuse for composition distance), the era-audit's
median-date/%current diagnostics (the manual version of this).
