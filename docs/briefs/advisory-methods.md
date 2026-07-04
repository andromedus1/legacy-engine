---
description: What statistical and optimization methods power the Meta Attack/Advisory pillar — matchup-matrix estimation, the meta-positioning score, the sideboard recommender, and the what-to-play advisor? Read before designing the advisory/ module.
type: brief
kind: research
research_method: /research
updated: 2026-07-04
status: draft
summary: |
  Methods brief for legacy-engine's advisory/ module (the Legacy-specific differentiator). Pins down:
  (1) matchup-matrix estimation from sparse round data (Wilson CIs, Beta-Binomial shrinkage, confidence
  tiers, the bimodal-coverage caveat); (2) the meta-positioning score S(D)=Σ field_share·winrate with
  Bayesian Monte-Carlo uncertainty (Beta cells + Dirichlet shares) and best-deck-vs-best-call;
  (3) the sideboard recommender as weighted submodular max-coverage solved by ILP (PuLP/CBC) with a
  greedy (1-1/e) explainable fallback, plus the anti-hate second order; (4) the what-to-play advisor —
  a composition-derived proactivity score, transparent plan-clash heuristics, and vulnerability-tag-driven
  hate-equity. All framed for scipy/numpy + PuLP and edh-engine's established/evolving/speculative confidence tiers.
key_findings:
  - "Matchup cells: Wilson score CI as the single default (Jeffreys for n<=40); shrink low-n cells with a Beta-Binomial prior centered at 50% (strength alpha+beta~=10-20); mirror fixed at 50%; ALWAYS show cell n."
  - "Confidence tiers by matchup-cell n: speculative n<30 (hide the rate, show n), evolving 30<=n<100, established n>=100 (Wilson half-width at p=0.5 is +-0.17 at n=30, +-0.096 at n=100). Display gate is n<30, NOT n<100."
  - "Bimodal-coverage caveat is mandatory: matchups come ONLY from rounds-bearing events (Challenges + paper); MTGO Leagues feed meta-share but not matchups. Keep matchup-sample and meta-share-sample as separate labeled fields — never conflate."
  - "Meta-positioning score S(D)=Σ_a w_a·winrate(D vs a) = expected WR vs the weighted field; use Bayesian Monte-Carlo (Beta posteriors on cells + Dirichlet posterior on shares) as primary uncertainty method; rank decks by probability-of-being-best from shared-field draws. Always report S(D) AND the unweighted aggregate (best-call vs best-deck)."
  - "Sideboard recommender = weighted MAXIMUM-COVERAGE (budget 15 slots), NOT set-cover; value = field_share x matchup-swing with a SATURATING (submodular) coverage function; solve EXACTLY with an ILP (PuLP/CBC, trivial scale) and keep greedy (1-1/e guarantee) as the explainable fallback. Bounded-integer copies; color/deck-fit pre-filter; anti-hate counter-hosers modeled as expected-opposing-hate pseudo-elements in one unified pass."
  - "What-to-play: derive a continuous PROACTIVITY score from card composition (reactive mass = counters+removal+stax+draw+protection; proactive mass = fast-mana+ritual+tutor+low-curve+compact-combo), tag archetypes with VULNERABILITY classes (graveyard-recursion, graveyard-fuel, plays-<color>, combo, low-curve, greedy-manabase, creature-based, low-interaction, storm-reliant, ramp, noncreature-reliant, colorless-reliant), compute hate-equity = field share each hate category attacks (coverage, not naive sum), and classify best-deck (low matchup-spread, robust) vs best-call (high-spread, field-specific gamble)."
  - "No published prior art formulates sideboard-as-optimization (one NIU thesis 403-blocked, flagged for manual pull); the OR theory (max-coverage, NWF 1978 submodular greedy) is load-bearing and the MTG community confirms the inputs (matchup matrix + field share) are the right primitives."
related:
  - {slug: docs/briefs/legacy-metagame.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md, relationship: depends-on}
  - {slug: docs/ARCHITECTURE.md, relationship: refines}
---

# Brief: Advisory Statistics & Optimization Methods

## Purpose
Pin the quantitative methods behind legacy-engine's **Meta Attack/Advisory pillar** — the
Legacy-specific differentiator — so `/architecture` can specify the `advisory/` module. Four areas:
the **matchup matrix** (estimation under sparse data), the **meta-positioning score** (expected WR vs
the field), the **sideboard recommender** (15-slot optimization), and the **what-to-play advisor**
(proactive/reactive, best-deck vs best-call, hating-out-the-field). Inputs are the archetype-labeled
tournament data (ingestion + archetype-parser campaign) and the matchup matrix we compute ourselves
from the fbettega cache's `Rounds`. Framed for Python (scipy/numpy/statsmodels + PuLP) and edh-engine's
`established | evolving | speculative` confidence-metadata pattern.

> **Legacy framing:** Legacy is 1v1, best-of-3, with a real **15-card sideboard** — so the sideboard
> recommender targets an actual sideboard (unlike the cEDH sibling, where the analog is maindeck flex
> slots). Matchups are clean head-to-head (no 4-player pod marginalization).

---

## 1. Matchup-matrix estimation

Each cell is a win rate `p̂ = wins/n` for (deck A vs archetype B), computed by joining `Rounds`
pairings (`player1`, `player2`, match result like "2-1") to archetype labels. Per-cell `n` varies
enormously (thousands to single digits).

**Confidence intervals — use Wilson score as the single default.** Wald is forbidden (collapses near
p=0/1, escapes [0,1], erratic coverage even at large n). Wilson stays in [0,1], behaves at small n, and
has the smallest mean-absolute coverage error. Use **Jeffreys** (Beta(x+½, n−x+½) credible interval) as
the small-n alternative (n≤40) since it's coherent with the shrinkage prior below. `statsmodels.stats.
proportion.proportion_confint(wins, n, method='wilson'|'jeffreys')`. (Brown, Cai & DasGupta 2001; Agresti-Coull 1998.)

Wilson formula (95%, z=1.96): center `=(p̂ + z²/2n)/(1+z²/n)`, half-width `=(z/(1+z²/n))·√(p̂(1−p̂)/n + z²/4n²)`.

**Shrinkage for low-n cells — Beta-Binomial empirical Bayes.** Posterior `= Beta(α+wins, β+losses)`,
posterior mean `p̃ = (α+wins)/(α+β+n)`. Use a prior **centered at 50%** (the matchup null) with **modest
strength α=β≈5–10** (so α+β≈10–20): a 3–1 cell shows as ~54%, not 75%, while a 200-game cell is
essentially unshrunk. **Display both the raw p̂ (with n) and the shrunken estimate** — never let
shrinkage be the only number shown. Optionally fit the prior empirically (method-of-moments on the
pooled cell-rate distribution) once there's enough data.

**Mirror cells: fix at 50.0%, report n only** (any deviation is noise; don't compute a CI).

**Confidence tiers (Wilson half-width at the worst case p=0.5):**

| n | half-width @ p=0.5 | tier | display |
|---|---|---|---|
| <30 | > ±0.17 | **speculative** | **hide the rate; show "n=X, insufficient"** |
| 30–99 | ±0.10–0.17 | **evolving** | show shrunken rate + Wilson CI, flagged |
| ≥100 | ≤ ±0.096 | **established** | show rate + CI, full confidence |
| (400 → ±0.049; 1000 → ±0.031) | | | |

The hard **display gate is n<30** (not the ops brief's n<100 — that's the *established* floor; 30–99 carries usable directional signal the CI honestly bounds).

**Mandatory bimodal-coverage caveat.** Matchups are computed **only** from rounds-bearing events (MTGO
Challenges + paper Melee); MTGO 5-0 League dumps feed **meta-share** but contribute **zero** matchup
data. Consequences: (a) two different denominators — matchup-n ≪ meta-share-n; keep them as **separate
labeled fields**, never interchangeable; (b) the matchup sample is a competitive-event subpopulation
(selection bias the CI does *not* capture). Print cell-n and a provenance line on every matrix.

**Presentation prior art:** mtgdecks.net headlines total match count (e.g. "30,926 matches") and gates
matrix rows at **≥2% of matches**; 17lands suppresses cards under 500 samples. Combine: global
match-count headline + relative ≥2%-of-matches row inclusion + absolute per-cell n<30 hide + a CI on
every shown cell.

---

## 2. Meta-positioning score

The differentiator metric: **`S(D) = Σ_a w_a · winrate(D vs a) = E_{a~w}[winrate]`** — the expected win
rate of deck D against one random opponent drawn from field distribution `w`. It is the **best response
to a fixed field** (one row of the meta-game payoff matrix dotted with the field's mixed strategy).

**Conventions:** normalize `w` to sum to 1 over considered archetypes (it's a conditional expectation);
keep **"Other/rogue" as an explicit archetype** with an imputed wide-uncertainty win rate (default: the
deck's mean vs known archetypes; `--robust` toggle uses the worst observed); **include the mirror at its
field share with p=0.5** (zero variance) for the headline score, and offer an exclude-self secondary view.

**Uncertainty propagation — Bayesian Monte Carlo (primary).** Per draw: sample each cell
`p_a ~ Beta(x_a+½, (n_a−x_a)+½)` (mirror fixed 0.5), sample shares `w ~ Dirichlet(counts+γ)` (γ=1 or
Jeffreys ½), recompute `S = Σ w_a p_a`; report posterior mean + percentile credible interval. MC is
primary because it carries **both** matchup and field-share uncertainty, captures the negative
correlation between shares (Dirichlet enforces Σw=1), and yields an honest asymmetric CI. Keep the
closed-form delta-method `Var(S)=Σ w_a² · p̂_a(1−p̂_a)/n_a` as a fast inline sanity check. ~20k draws ×
~20–40 archetypes is microseconds in numpy.

**Custom field (headline feature):** the user supplies an `archetype→expected-share` map (their expected
local field). Auto-normalize (warn if shares don't sum to 1); warn + impute on archetypes with no/low
matchup data; flag `field_source: global | custom | local`. This swaps `w` (and the Dirichlet `counts`
in count-backed mode).

**Best-deck vs best-call (the conceptual payload):** report `S(D)` (field-weighted) **alongside** the
unweighted aggregate `Ū(D)=mean_a winrate` (or observed overall WR). They disagree when the field is far
from uniform. Worked example — field A:50%, B:30%, C:20%:

| | vs A | vs B | vs C | Ū (unweighted) | S (field-weighted) |
|---|---|---|---|---|---|
| Deck X | .62 | .60 | .20 | **.473** | **.530** |
| Deck Y | .42 | .45 | .85 | **.573** | **.515** |

Deck Y is the better *deck* (Ū) but Deck X is the better *call* (S) — X beats the 80% of the field that
is A+B; Y's crush vs the rare C is wasted. The product is the sentence: *"X is the best metagame call for
your field even though Y is stronger overall, because X beats Dimir Tempo and Lands (80% of your field)."*

**Ranking under uncertainty:** don't sort point estimates. Use **shared-field MC draws** (sample `w`
once per iteration, score all candidate decks against that same sampled field) and report
**probability-of-being-best** `P(S_D = max)`, plus `S±CI` and pairwise `P(S_A>S_B)`. Optional
`--risk-averse` ranks by a lower posterior quantile (mean–variance). Frame explicitly as
*best-response-to-a-fixed-field* ("best call if the field stays as you predict"); the Nash-equilibrium
view (every deck ~50%, no edge remains) is the complementary "field will adapt" lens.

---

## 3. Sideboard recommender

**Problem = weighted (budgeted) MAXIMUM-COVERAGE, not set-cover.** We have a hard 15-slot budget and want
to *maximize* weighted coverage of the field, not cover everything at min cost. Elements = archetypes
(+ hate pseudo-elements, below); sets = candidate sideboard cards (hosers) each attacking a set of
archetypes; **element weight `w_a = field_share(a) × Δ_a`** where `Δ_a` is the win-rate swing the
hoser(s) provide vs `a` (prefer covering a deck you can swing +20% over an equally-common deck you swing +3%).

**Value function = saturating/submodular**, so the 2nd anti-Reanimator card is worth less than the 1st:
`value(a) = w_a · g(n_a)` with `g` concave non-decreasing (e.g. `g(n)=1−(1−p)^n`, the prob ≥1 of your
answers appears). This spreads coverage across the field and preserves greedy's guarantee.

**Solver — ILP primary, greedy fallback.** Scale is trivial (~hundreds of candidate cards, 15 slots,
~20–40 archetypes), so an **ILP (PuLP + CBC, the default open-source solver) solves to exact optimum in
<1s**. Keep the **greedy** algorithm (add the max-marginal-gain card until 15 slots full) as a fast,
**explainable** preview — it carries the classic **(1−1/e)≈0.63** guarantee because the coverage value is
monotone submodular (Nemhauser-Wolsey-Fisher 1978), and its marginal-gain trace *is* the UI rationale.

ILP shape: binary/bounded-integer `x_c` per card (≤max copies → handles 2–3-ofs = multi-coverage),
indicators `y_a` (or incremental `y_a^t` for the saturating linearization), objective `max Σ_a w_a·y_a`,
budget `Σ_c x_c ≤ 15 − reserved`, link `y_a ≤ Σ_{c:a∈S_c} x_c`.

**Constraints:** color/deck-fit as a **pre-filter** (drop cards not castable in the deck's colors —
cleaner than LP rows); bounded-integer copies; `reserved` slots held for flex/maindeck-overlap; keep
curve/synergy in the eligibility scoring, not hard LP rows (a naive LP produces literal-but-bad lists).

**Anti-hate second order (counter-hosers):** Veil of Summer / Defense Grid / Force of Vigor point at
*enemy hate cards*, not archetypes. Model as a two-layer graph and fold into **one unified coverage pass**:
compute an **expected-opposing-hate vector** `h_k = Σ_a field_share(a)·P(a sideboards hate k vs you)`,
treat each significant `h_k` as a **pseudo-element** with weight, and let counter-hosers cover those
pseudo-elements. The optimizer then trades a hoser slot for a counter-hoser when the field's hate is the
bigger threat.

**Prior art is thin** — no published sideboard-as-optimization formulation (one NIU thesis "Mathematical
programming and MTG" is 403-blocked → **flagged for a manual human pull** before claiming full novelty).
The MTG community work is metagame *Nash-equilibrium deck selection* (complementary — picks the deck, not
the 15 cards) and a Limited deckbuilding LP (no metagame weighting). The OR theory (max-coverage,
submodular greedy) is load-bearing; the community confirms the *inputs* (matchup matrix + field share) are right.

---

## 4. What-to-play advisor

**Proactivity score (composition-derived, continuous [0,1]).** Derive from card composition rather than
the archetype tag alone (so it tracks a *specific* list and stays auditable from card counts), using the
Card model's Legacy role tags (`is_free_spell`, staple roles) + oracle-text role classification:

```
reactive_mass  = counters + removal + stax + card_advantage + protection densities
proactive_mass = fast_mana + ritual + tutor + low_curve_score + compact_combo
PROACTIVITY    = proactive_mass / (proactive_mass + reactive_mass)
```

`low_curve_score` (sigmoid centered ~avg MV 2.0) is the cleanest proactive signal and ties to the goldfish
clock. Calibrate so combo/Storm/Reanimator ≈ 0.75–0.9, tempo ≈ 0.5–0.6, control/D&T ≈ 0.15–0.4; **surface
disagreement** between computed score and the archetype's fair/unfair tag as a finding (a "tempo" list
running 18 reactive cards is functionally control). When the Deck Mechanics pillar ships goldfish clocks,
cross-check: proactive decks have a small payoff-to-win gap, reactive decks a large one.

**Plan-clash logic (transparent rule table → human-readable WHY strings layered over the empirical
matchup numbers, never replacing them):**

| Condition | Favors | WHY |
|---|---|---|
| Proactive vs reactive w/ LOW relevant hate | proactive | "Forces answers faster than opp can find them." |
| Proactive vs reactive w/ HIGH counters+protection | reactive | "Disruption outlasts an unprotected fast plan." |
| Proactive vs proactive | faster clock | "Race — lower-curve / more-acceleration deck wins the goldfish." |
| Reactive vs reactive | more card advantage | "Grind — more redundant engines reach inevitability first." |
| Deck w/ vulnerability tag vs opp carrying that hate | the hater | "Opp runs [hate]; you are [tag]-reliant → structural disadvantage." |

When heuristic and empirical disagree, **say so** (possible pilot-skill / low-n confound). Keep rules in a readable table, not a learned weight matrix.

**Vulnerability tags (the core deliverable for hating-out-the-field)** — derived from oracle-text roles +
the metagame brief's archetype data:

| Tag | Derivation | Exposes |
|---|---|---|
| graveyard-recursion | graveyard-recursion role / reanimate-escape-delve win-con | exile-graveyard hate (Surgical, Endurance, Leyline, RIP) |
| graveyard-fuel | graveyard-as-resource role (delve/threshold/flashback fuel, non-win-con) | weaker resource-denial GY hate (grindier answers than exile hate; less than a hard blowout) |
| plays-<color> | deck's color identity (white/blue/black/red/green), color-contingent | color-hosers (Hydroblast/Pyroblast-style; also the Blue/Red Elemental Blast catalog entries) |
| combo (compact) | compactness ≤3 + Thassa's Oracle/Tendrils line | free counters, Mindbreak Trap, stax |
| low-curve | avg MV <2.0 + Ad Naus/Necro | life pressure, sphere/Rule-of-Law |
| greedy-manabase | high fast-mana + nonbasic-heavy | Wasteland, Blood Moon, Back to Basics |
| creature-based | creature win-con / mana dorks | board wipes, Toxic Deluge |
| low-interaction | low counter+removal density | stax/sphere, taxing |
| storm-reliant | storm role present | spell-count taxes (Thalia, Defense Grid mirror) |
| ramp | mana-dork/ritual/land-ramp density above threshold | Wasteland/Blood Moon-style mana-denial, tempo disruption |
| noncreature-reliant | creature-slot density below `_NONCREATURE_RELIANT_MAX` — the plan lives on the stack (combo enablers, control finishers/wraths/planeswalkers), not the battlefield; independent of `combo`/`storm-reliant` | broad free/soft anti-noncreature interaction (Force of Negation, Spell Pierce — "counter target noncreature spell") |
| colorless-reliant | colorless-nonland-spell density at/above `_COLORLESS_RELIANT_DENSITY` — an archetype can be colorless-reliant while creature-dense (Eldrazi) or creature-light (Blue Artifacts); independent axis from `noncreature-reliant`/`creature-based` | the colorless-spell half of Consign to Memory ("counter target triggered ability or colorless spell") |

**Hate-equity = the field share each hate category attacks** (`Σ field_share(a) for a carrying the tag`).
Because a deck carries multiple tags, **use coverage, not a naive sum**, when ranking a *package*. This
vector is exactly the sideboard recommender's weighting input.

**Best-deck vs best-call classification:** compute the **variance of a deck's matchup spread** across the
field. Low spread + high mean = **BEST DECK** (robust, good vs everything — play if you can't read the
room). High spread + high mean-vs-this-field = **BEST CALL** (preys on specific shares — a metagame gamble).

**The recommendation surface** (the advisor's output): a "Field Read & Deck Recommendation" report —
field composition + derived vulnerability profile → field-read narrative ("X% of the field runs
graveyard-recursion win-cons → exile-graveyard hate is highest-equity") → decks ranked by positioning score, each tagged
proactive/reactive and best-deck/best-call → a recommended 15-card sideboard package → an **audit trail**
(every number with its derivation, sample size, and a heuristic-vs-data-driven label).

---

## Implementation Notes (for `advisory/`)
- Deps: `statsmodels` (Wilson/Jeffreys CIs) or hand-rolled Wilson; `scipy`/`numpy` (Beta/Dirichlet sampling); **`pulp`** (ILP via bundled CBC). All additions over edh-engine's base stack.
- `matchup_matrix` → cells `{wins, n, p_raw, p_shrunk, ci_low, ci_high, tier}`; mirror fixed 0.5; **separate `matchup_n` from `metashare_n`** in the data model.
- `positioning_score(deck, field, mode="bayesian")` → `{S_mean, S_ci, S_samples, field_source, warnings}`; always emit `Ū` too.
- `rank_decks(candidates, field)` → shared-field MC → `P(best)`, `S±CI`, pairwise matrix; `--risk-averse` toggle.
- `recommend_sideboard(deck, field)` → ILP (PuLP/CBC) primary + greedy explainable trace; bounded-integer copies, color pre-filter, `reserved` slots, unified anti-hate pseudo-elements.
- Confidence per output component (established/evolving/speculative), not one global label; reuse edh-engine's `ConfidenceMetadata`. Gate BEST-CALL recommendations on established/evolving matchup data only.

## Sources
Statistics: [Brown, Cai & DasGupta 2001 (binomial CIs)](https://projecteuclid.org/journals/statistical-science/volume-16/issue-2/Interval-Estimation-for-a-Binomial-Proportion/10.1214/ss/1009213286.full); [Agresti-Coull 1998](https://www.tandfonline.com/doi/abs/10.1080/00031305.1998.10480550); [binomial CI comparison (PMC2706447)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2706447/); [Wikipedia: binomial proportion CI](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval); [Beta-Binomial shrinkage (optimumsportsperformance)](https://optimumsportsperformance.com/blog/using-beta-binomial-regression-to-set-priors-for-different-sample-sizes/); [empirical Bayes (Variance Explained)](http://varianceexplained.org/r/beta_binomial_baseball/).
Positioning/uncertainty: [Dirichlet distribution (Wikipedia)](https://en.wikipedia.org/wiki/Dirichlet_distribution); [Dirichlet-multinomial Bayesian proportions (ericmjl)](https://ericmjl.github.io/bayesian-analysis-recipes/notebooks/dirichlet-multinomial-bayesian-proportions/); [delta method (Stephenson)](https://www.alexstephenson.me/post/2022-04-02-standard-errors-and-the-delta-method/); [weighted-coverage variance (PMC7101480)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7101480/); [zero-sum/minimax + best response (Roth AGT Lec 6)](https://www.cis.upenn.edu/~aaroth/courses/slides/agt17/lect06.pdf); [α-Rank under uncertainty (arXiv 2211.10317)](https://arxiv.org/pdf/2211.10317); [A Magic Game Theory (Eternal Central)](https://www.eternalcentral.com/a-magic-game-theory/); [Game Theory & Deck Choice (HSReplay)](https://articles.hsreplay.net/2020/05/22/game-theory-and-deck-choice/).
Optimization: [Maximum coverage problem (Wikipedia)](https://en.wikipedia.org/wiki/Maximum_coverage_problem); [Nemhauser, Wolsey & Fisher 1978](https://link.springer.com/article/10.1007/BF01588971); [submodular functions (Wikipedia)](https://en.wikipedia.org/wiki/Submodular_set_function); [maximum multi-coverage (arXiv 1905.00640)](https://arxiv.org/pdf/1905.00640); [PuLP docs](https://coin-or.github.io/pulp/main/includeme.html); [Optimizing MTG in R (Hernandez — only MTG deckbuilding LP, no metagame weighting)](https://troyhernandez.com/2018/09/28/optimizing-magic-the-gathering-in-r/); [Mathematical programming and MTG (NIU thesis — 403, NEEDS MANUAL PULL)](https://huskiecommons.lib.niu.edu/cgi/viewcontent.cgi?article=4902&context=allgraduate-thesesdissertations).
What-to-play: [Who's the Beatdown / role assignment (Bolt the Bird)](https://www.boltthebirdmtg.com/post/mtg-whos-the-beatdown-clarifying-consolidating-role-assignment-02-21-22); [proactive vs reactive (Quiet Speculation)](https://www.quietspeculation.com/2023/03/life-in-the-fast-lane-how-to-get-the-most-out-of-proactive-decks/); [best deck vs metagame call (Cardmarket)](https://cardmarket.com/en/Magic/Insight/Articles/Define-This-Metagame-and-Tiers); [metagame RPS (Spikes Academy)](https://spikesacademy.com/p/how-the-meta-works-in-mtg); [graveyard hate equity (Draftsim)](https://draftsim.com/mtg-graveyard-hate/).

**Open item:** the NIU thesis (403 on automated fetch) is the most likely direct prior art for sideboard/metagame MIP — recommend a manual pull before claiming full novelty in the design.
