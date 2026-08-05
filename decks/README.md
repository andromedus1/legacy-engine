# decks/

Working decklists and field files for deck-prep (`scripts/deck-prep.sh`).

## Generated review artifact

- `best-deck-best-call-ranking.html` — local, git-ignored Best Deck / Best Call review page.
  Refresh it with `.venv/bin/python scripts/refresh_best_call_ranking.py`; it is generated from
  the local analytics data and should be reviewed, not hand-edited.

## Decklists (plain text: `N Cardname` per line, maindeck only)
- `dimir-tempo.txt` — the primary build: grindy/disruptive (2 Hymn to Tourach + 2 Baleful Strix
  over the consensus velocity package). Off-meta in those slots, but pointed at a big-mana meta.
- `dimir-tempo.sb.txt` — its 15-card sideboard.
- `dimir-tempo-reference.txt` — a leaner velocity reference build (3 Daze, 3 Nethergoyf, 4 Ponder,
  no Hymn/Strix). Better in fair/tempo fields; weaker vs big-mana. Kept for list-vs-list comparison.

## Field files (`<share> <archetype>` per line; shares need not sum to 1 — the engine normalizes)
- `current-covered-field.txt` — current-regime shares restricted to archetypes that actually have
  matchup data (so positioning S is meaningful, not dominated by the imputation prior).
- `local-field.txt` — the maintainer's local local meta: big-mana-weighted (Lands/Eldrazi/Post up).
  Hand-built estimate; edit the shares as the local meta moves.

## Usage
```bash
scripts/deck-prep.sh decks/dimir-tempo.txt decks/local-field.txt Entomb
```
See `scripts/deck-prep.sh` header for the full recipe and caveats.
