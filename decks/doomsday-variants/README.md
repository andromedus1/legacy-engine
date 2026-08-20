# Current Doomsday comparison candidates

These four files are exact post-ban registrations selected for a comparative learning program:
the Dimir creature-transform control, Esper Teferi/Swords, light green-white, and full
green-white/four-color shield directions. Import any file as a normal Moxfield-style list with
`N Card Name` lines and the `Sideboard` marker.

The machine-readable candidate authority is [`manifest.json`](manifest.json). It binds each file
to its fetched source record, attestation handle, canonical board hash, observed construction axes,
and fetchlands-only compatibility deltas against the current Dimir control. The lists are
observational registrations: their published finishes establish playable source examples, not
package-level superiority, matchup rates, or causal strategic outcomes.

The manifest records both the 2026-08-10 ban snapshot used for historical reproducibility and the
repository's current snapshot checked when the contract tests run. A later ban-list change should
make the candidate stale loudly rather than silently changing its contents.

## Paired playtest program

The complete 15-list registry in [`manifest.json`](manifest.json) is the sole list-id authority for
the preregistered comparison. Use [`playtest-protocol.md`](playtest-protocol.md) before recording
games in [`playtest-log.csv`](playtest-log.csv), then validate and summarize with:

```bash
.venv/bin/python scripts/doomsday_variant_results.py decks/doomsday-variants/playtest-log.csv
```

The command reports descriptive denominators and paired deltas only; it does not rank lists or
merge published finishes into playtest outcomes.
