---
id: idea-positioning-field-coverage-gap
created: 2026-06-06
tags: [advisory, analytics, correctness]
---

When `advise positioning`/`advise report` runs against a broad field (e.g. the full-corpus 336-archetype field, or a thin window that falls back to full-corpus), the matchup matrix only covers ~15 archetypes, so the vast majority of opponents are imputed. The audit already warns "thin row: 322/335 opponent(s) imputed; S is dominated by the imputation prior" — but the headline `S` is still printed with the same authority as a well-covered score, and a casual reader treats 0.504 as a real positioning when it's essentially the 0.50 prior.

Surface a **field-coverage ratio** (share-weighted % of the field that has real matchup data) as a first-class headline number next to S, and degrade/flag S when coverage is low (e.g. "S=0.50 [LOW COVERAGE: 16% of field has matchup data — treat as prior]"). Discovered while dogfooding Dimir Tempo prep: the only way to get a meaningful S today is to hand-build a `--field` file restricted to covered archetypes, which a normal user wouldn't know to do. Consider auto-restricting (or offering a `--covered-only` flag) and reporting the excluded share. Related to [[idea-pbest-zero-coverage-flag]].
