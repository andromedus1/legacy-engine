---
id: feature-ranking-benchmark-residual-quarantine
kind: feature
stage: drafting
tags: [analytics, advisory, testing, data-quality]
parent: null
depends_on: [feature-ranking-future-only-benchmark, feature-card-name-reconciliation-closure]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Outcome-blind residual quarantine for ranking benchmarks

## Brief

Add an explicitly versioned benchmark policy for the small set of tournament decks whose card
metadata remains unresolvable after authoritative Scryfall aliases, verified provider serialization,
and exact evidence-backed exceptions. The original frozen protocol and its fail-closed result remain
immutable. A new protocol may exclude an entire corrupt deck and every match involving that deck,
using only pre-outcome card-dimension completeness, while recording exact names, providers, events,
deck identities, match counts, fractions, hashes, and censor reasons.

The current reconciled corpus has at most 26 affected training decks among 67,477 decks and 100
affected rounds among 81,167 at the last planned cutoff. This feature must set small, round-number
support ceilings before evaluation, refuse folds that exceed them, and distinguish a historical
sensitivity replay from a genuinely prospective validation protocol. It must never infer a card
identity, silently drop a row, overwrite the preregistered v1 protocol, or promote descriptive
results into a validated headline.

## Strategic decisions

- **Immutable evidence**: preserve protocol v1, its hashes, and its not-evaluable/partial artifacts.
  Every quarantine-capable run uses a new protocol id and content hash.
- **Outcome blindness**: quarantine eligibility depends only on deck-card closure against the
  cutoff-safe card dimension. Results, standings, win rates, archetype labels, and downstream scores
  cannot affect which deck or match is removed.
- **Whole-unit removal**: exclude the complete deck and all rounds involving its tournament-local
  player identity. Never delete only the unknown card row and then classify a partial deck.
- **Claim separation**: replaying already-opened historical folds is a labeled sensitivity analysis,
  not prospective validation. A separately frozen future protocol is the only path to a new
  predictive-validation claim.
- **Modern remains out of scope**: this work changes only the Legacy benchmark contract and does not
  extract a format core, create a Modern profile/database, or deploy another format.

## Simplification opportunity

Replace serial fail-stop discoveries and speculative name repair with one reusable, typed exclusion
ledger at the benchmark snapshot/evaluation boundary. Retain strict card-name preflight as the
default and keep the quarantine policy opt-in and protocol-bound.
