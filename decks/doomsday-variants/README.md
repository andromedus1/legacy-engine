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

## Pilot's Manual field guide

Regenerate the self-contained comparison report from the verified campaign data, then open the
result directly in a browser:

```bash
.venv/bin/python scripts/render_doomsday_variant_report.py
open decks/doomsday-variant-field-guide.html
```

The generated [`decks/doomsday-variant-field-guide.html`](../doomsday-variant-field-guide.html) is
gitignored. Its source of truth is
[`report-content.json`](../../.research/analysis/campaigns/doomsday-variant-experiments/report-content.json),
rendered through `scripts/doomsday_variant_report_template.html`. The guide keeps observed records,
deterministic list math, inferred scenarios, and prospective playtests separate. It is a build-and-
test priority guide, not a causal matchup ranking; reconstructed lists and unplayed experiments
remain labeled as such.

## Moxfield imports

Paste any clean import file into Moxfield's **Bulk Edit / Import** surface:

- [BUG Veil/Carpet](moxfield/bug-veil-carpet.txt) — inferred legal reconstruction, **not** a current
  observed 75.
- [Esper Teferi/Swords](moxfield/esper-teferi-swords.txt) — exact observed registration.
- [Personal Tutor Turbo Dimir](moxfield/turbo-dimir-personal-tutor.txt) — exact observed artifact.
- [Dimir Creature Juke](moxfield/dimir-creature-juke.txt) — exact observed registration.

See the [Moxfield export notes](moxfield/README.md) for the precise source and normalization posture.

## Paired playtest program

The complete corpus has 15 artifacts but 14 unique 75s: the Battlegrounds Esper and Bilbo/Tamiyo
files are the same registration, so the manifest aliases them to one experimental arm. The 14-list
registry in [`manifest.json`](manifest.json) is the sole list-id authority for the preregistered comparison. Use [`playtest-protocol.md`](playtest-protocol.md) before recording
games in [`playtest-log.csv`](playtest-log.csv), then validate and summarize with:

```bash
.venv/bin/python scripts/doomsday_variant_results.py decks/doomsday-variants/playtest-log.csv
```

The command reports descriptive denominators and paired deltas only; it does not rank lists or
merge published finishes into playtest outcomes.
