#!/usr/bin/env bash
# deck-prep.sh — reusable Legacy deck-prep recipe chaining the legacy-engine CLI.
#
# Codifies the dogfooding workflow: expand the meta read, build a coverage-restricted
# (or local-meta) field, get a MEANINGFUL positioning score, and pull the sideboard +
# per-card signals — in one shot, re-runnable whenever the meta shifts.
#
# Why a coverage-restricted field? `advise positioning` imputes opponents with no
# matchup data, and against a broad field S collapses to the ~0.50 imputation prior.
# Restricting the field to archetypes that actually have matchup data (or supplying a
# hand-built local-meta field) is the only way to get a positioning number that means
# something. See backlog: idea-positioning-field-coverage-gap.
#
# Usage:
#   scripts/deck-prep.sh <deck.txt> [field.txt] [regime]
#     <deck.txt>   plain-text 60-card maindeck (one "N Cardname" per line)
#     [field.txt]  optional "<share> <archetype>" field file (e.g. your local meta).
#                  If omitted, prints the current-regime field so you can build one.
#     [regime]     matchup window: a regime substring (default "Entomb" = last stable
#                  regime w/ Energy covered), "current", or "all-time".
#
# Examples:
#   scripts/deck-prep.sh decks/dimir-tempo.txt
#   scripts/deck-prep.sh decks/dimir-tempo.txt decks/boulder-field.txt Entomb
set -euo pipefail

DECK="${1:?usage: deck-prep.sh <deck.txt> [field.txt] [regime]}"
FIELD="${2:-}"
REGIME="${3:-Entomb}"
SEED=42

# Activate venv if present (project .venv is python3.13).
if [[ -f .venv/bin/activate ]]; then source .venv/bin/activate; fi

hr() { printf '\n=== %s ===\n' "$1"; }

# 1. EXPAND THE META — current-regime field down to a 1% floor (beyond the default top-10).
hr "1. CURRENT-REGIME META (raw share, floor 1%)"
legacy-engine report meta --regime current --definition raw --provenance all --min-share 0.01

# 2. REGIME TRENDS — where is the field heading vs prior regimes?
hr "2. META TRENDS ACROSS BAN REGIMES"
legacy-engine report trends

# 3. COVERAGE — which archetypes actually have matchup data (the only ones S can score)?
hr "3. MATCHUP COVERAGE (window=$REGIME) — Dimir/your row + covered columns"
if [[ "$REGIME" == "all-time" ]]; then
  legacy-engine report matchups --all-time --provenance all | sed -n '1,7p'
else
  legacy-engine report matchups --regime "$REGIME" --provenance all | sed -n '1,7p'
fi

# 4. POSITIONING — meaningful only with a restricted/local field.
if [[ -n "$FIELD" ]]; then
  hr "4. POSITIONING vs supplied field ($FIELD), matchups=$REGIME"
  WINDOW_FLAG=(--regime "$REGIME"); [[ "$REGIME" == "all-time" ]] && WINDOW_FLAG=(--all-time)
  legacy-engine advise positioning --deck "$DECK" --field "$FIELD" "${WINDOW_FLAG[@]}" --seed "$SEED" \
    | grep -ivE "imputed|warn"

  hr "5. SIDEBOARD SOLVER vs supplied field"
  legacy-engine advise sideboard --deck "$DECK" --field "$FIELD" \
    | grep -ivE "warn|disclaimer"
  echo "  NOTE: solver is limited to its HOSER_CATALOG (~25 cards) — cross-check"
  echo "        against 'report cards --board side' below for cards it can't see."
else
  hr "4. (no field file given)"
  echo "  Build a field file from section 1 above: '<share> <archetype>' per line,"
  echo "  keeping only archetypes that appear as covered columns in section 3."
  echo "  Then re-run:  scripts/deck-prep.sh $DECK <field.txt> $REGIME"
fi

# 6. PER-CARD SIGNALS — presence-correlational lift for main + side (cross-check the solver).
hr "6. PER-CARD LIFT — maindeck (presence-correlational, NOT causal)"
ARCH="$(legacy-engine advise positioning --deck "$DECK" --field "${FIELD:-/dev/null}" --all-time --seed "$SEED" 2>/dev/null \
        | sed -n 's/^Classified archetype: \(.*\) (kind.*/\1/p' | head -1)"
ARCH="${ARCH:-Dimir Tempo}"
legacy-engine report cards --archetype "$ARCH" --board main --min-tier speculative | head -40
hr "7. PER-CARD LIFT — sideboard"
legacy-engine report cards --archetype "$ARCH" --board side --min-tier speculative | head -40

hr "DONE"
echo "Reminders:"
echo "  - Positioning S is archetype-granular: two lists of the same deck score the same."
echo "  - ~28% of the current field (incl. Tron, the #1 deck) has NO matchup data — uncovered."
echo "  - Per-card lift is correlational; treat as a soft signal, not a verdict."
