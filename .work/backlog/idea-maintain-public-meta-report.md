---
id: idea-maintain-public-meta-report
created: 2026-06-28
tags: [reporting, outreach]
---

# Maintain & improve the public Boulder-vs-global meta report

A public shareable report was published to share back with the Boulder tournament organizer
(in Discord). Keep it current and grow it over time rather than letting it become a one-off snapshot.

- **Live:** https://andromedus1.github.io/legacy-meta-reports/
- **Repo (public, source of truth for the rendered report):** `andromedus1/legacy-meta-reports` — `index.html`, Pages from `main` root.
- **Dev copy / build:** `legacy-engine/decks/boulder-vs-global-meta-report.html` (gitignored). Deploy flow + data provenance captured in the `boulder-meta-public-report` memory.

## Improvement roadmap (raw notes — not yet scoped)

- **Confirm the two flagged archetype mappings** with the organizer (Saga Storm→TES; Affinity Combo + Stompy→Blue Artifacts) and re-run — they affect how the storm/artifact rows read.
- **Monthly re-pull** for longitudinal tracking — a single snapshot is a photo; the trend over time is the real value. Add time-series / trend charts across snapshots once there are ≥2.
- **Reduce the manual deploy.** Consider a CLI/script that regenerates the report HTML from engine analysis (global `report meta` + `match_results` MWP + a supplied local field file) so re-runs are one command, then a thin publish step to the public repo.
- **Generalize beyond Boulder.** If other organizers share local data, the same engine-side machinery (local field file + global corpus) produces a report for any meta — the public repo can host several.
- **Hold the honesty line.** Prevalence is reliable; MWP samples are thin (CIs overlap). Any future automation must keep sample sizes + CIs visible and never let the report overclaim win rates.

Related memory: `boulder-meta-public-report`.
