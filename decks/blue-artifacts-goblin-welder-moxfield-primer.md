# Blue Artifacts — Goblin Welder

An import-ready 75 generated from the current Goblin Welder camp (`n=63`, evolving tier). I prefer
this over Thoughtcast for the present field, though the choice is close and metagame-dependent.

## Welder versus Thoughtcast

Thoughtcast is the linear blue build: Ancient Tomb, Force of Will, free artifacts, Thoughtcast and
Thought Monitor generate velocity toward Kappa Cannoneer or The Fantasticar. It is faster, has
maindeck stack interaction, and should be structurally better when the field is dominated by
noncreature combo. Its costs are a higher density of air, reliance on maintaining artifact count,
and fewer ways to recover after the first threat or artifact board is answered.

Welder is the recursive engine build. Twelve one-mana engine creatures—Emry, Engineer, and
Welder—turn Baubles, Saga targets, and graveyard artifacts into repeated cards and battlefield
value. It is slower and more exposed to creature removal and graveyard hate, but it has more live
topdecks, more tutor-like access to singleton artifacts, and a much stronger long game.

The current field contains enough tempo and midrange that the recursive plan makes more sense as a
default. The data agrees, but does not close the case:

| Camp | Adjusted field WR | Agency | Floor coverage | Camp sample |
|---|---:|---:|---:|---:|
| Goblin Welder | 53.47% | 45.62% | 50.08% | 63 |
| Thoughtcast | 52.93% | 49.87% | 21.40% | 19 |

Thoughtcast's higher nominal agency is based on only three measured opponents: Izzet Delver
49.87% (`n=8`), Doomsday 56.91% (`n=8`), and Dimir Tempo 58.71% (`n=9`). Welder has nine measured
opponents. It is especially strong against Dimir Midrange (74.98%, `n=17`), Dimir Tempo (63.79%,
`n=10`), and Izzet Delver (61.17%, `n=13`), while remaining approximately even against Show and
Tell (49.92%, `n=20`) and Doomsday (48.16%, `n=11`). That broader evidence makes Welder the more
defensible selection today. Thoughtcast becomes preferable if fast combo rises sharply.

## Game plan

Treat cheap artifacts as resources, not permanent possessions. Emry recasts them, Engineer bins
the exact artifact needed, and Welder exchanges an expendable artifact for the best artifact in a
graveyard. Urza's Saga supplies both pressure and a toolbox piece without asking you to stop
developing the engine.

Sequence around summoning sickness. A turn-one Welder or Engineer that survives often matters
more than maximizing immediate artifact count. Against removal decks, diversify engines rather
than committing every creature into the same answer. Against combo, reverse priorities: establish
a clock quickly and preserve mana for sideboard interaction.

Welder targets both the battlefield artifact and graveyard artifact. If either becomes illegal,
the exchange does not occur. Use that fact defensively, and account for opposing graveyard
interaction before activating.

## Mulligans

- Keep hands with mana, an engine creature, and at least one cheap artifact or Saga.
- A hand of mana and artifacts without Emry, Engineer, Welder, Saga, or a meaningful payoff is
  usually a mulligan.
- Against unknown opponents, favor resilient development over a hand that only produces one fast
  threat.
- Against combo, aggressively seek a fast clock plus Spell Pierce, Flusterstorm, Consign, or Flute
  after sideboarding.
- Against Wasteland, fetch basics or lead on a redundant colored source when the hand permits it;
  the engine requires colored mana more than the Thoughtcast build does.

## Sideboard map

The board is a toolbox, so sideboard by opposing mechanism rather than card type alone.

### Doomsday, TES, and spell combo

Bring in Flusterstorm, Spell Pierce, and Disruptor Flute. Surgical Extraction is useful when it can
pair with interaction or remove a deterministic combo resource, but it is not a substitute for a
counterspell. Trim slow artifact bullets and removal. Consign to Memory joins against colorless
payoffs or relevant triggers, not merely because the opponent is a combo deck.

### Show and Tell and colorless bombs

Bring in Flusterstorm, Spell Pierce, Disruptor Flute, and Consign to Memory where its targets and
triggers matter. Into the Flood Maw can buy the critical turn against a permanent already in play.
Keep a clock; a hand containing only answers gives them time to rebuild.

### Reanimator and graveyard decks

Bring in Tormod's Crypt and Surgical Extraction. Crypt is especially attractive because Engineer,
Welder, and Emry can find or reuse it. Be aware that graveyard hate aimed at the opponent may also
invite broader hate that weakens your own recursion plan.

### Tempo and midrange

This is why we selected Welder. Sideboard minimally and force them to answer engines repeatedly.
Portable Hole, Ratchet Bomb, Twinshot Sniper, or Rip Apart come in according to the threats shown.
Do not dilute the recursion core with too many reactive singletons.

### Artifacts, enchantments, and permanent locks

Use Haywire Mite, Rip Apart, Into the Flood Maw, Pithing Needle, and Ratchet Bomb according to the
specific permanent. Engineer turns singleton answers into accessible tools; Welder and Emry can
make them repeatable. Name the exact activated ability with Needle rather than boarding it as a
generic answer.

## What would change the verdict

Thoughtcast needs measured cells against Show and Tell, Reanimator, Azorius Midrange, and the
nonblue creature decks. If it retains a near-50% floor while coverage rises past roughly 40%, its
speed and Force of Will would make it the stronger field choice. Today, its 49.87% floor is best
read as an exciting upper-bound hypothesis; Welder's 45.62% floor is the more credible result.
