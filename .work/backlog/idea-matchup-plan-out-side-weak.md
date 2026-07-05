---
id: idea-matchup-plan-out-side-weak
created: 2026-07-04
tags: [advisory, sideboard]
---

# Matchup-plan OUT side is adoption-locked into fetchland cuts

Found while grounding the Dimir primer (2026-07-04): `_plan_matchups`' OUT selection locks
every card at >=65% archetype adoption, which for a consensus-tight deck leaves only
FETCHLANDS as flex — its data-driven plans proposed cutting 2-3 lands (Scalding Tarn,
Bloodstained Mire) for spells vs Izzet/Jeskai/mirror, and the mirror plan boarded Hydroblast
into a UB deck (correlational card-value noise). The IN side had real signal (Consign vs
Izzet n=71, Hydroblast vs Doomsday n=30 corroborated judgment). Candidate fixes: exempt
lands from the flex pool (or cap land cuts at 0-1), and/or gate INs on the coverage model's
axis relevance (Hydroblast needs a red target in the matchup), not correlation alone. The
primers used judgment plans with engine signals cited/rejected explicitly — the audit trail
for this item.
