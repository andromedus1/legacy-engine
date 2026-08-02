# Generated current deck packages

Corpus-backed online/MTGO packages generated on 2026-08-02 from data through 2026-07-30.

Each `*-moxfield.txt` file is a legal 60-card maindeck plus 15-card sideboard accepted by
`legacy-engine export deck --format moxfield`. Each paired primer records the stable-window sample,
game plan, sideboard roles, and whether matchup guidance cleared the engine's evidence gate.

| Archetype | Moxfield import | Primer | Sample |
|---|---|---|---|
| Ad Nauseam Tendrils | `ant-current-moxfield.txt` | `ant-current-primer.md` | 142, established |
| The Epic Storm | `tes-current-moxfield.txt` | `tes-current-primer.md` | 83, evolving |
| Aluren | `aluren-current-moxfield.txt` | `aluren-current-primer.md` | 129, established |
| Grixis Reanimator | `grixis-reanimator-current-moxfield.txt` | `grixis-reanimator-current-primer.md` | 234, established |

Generation path:

1. `legacy-engine generate consensus --archetype <name> --export moxfield`
2. `legacy-engine advise refresh --deck <file> --archetype <name> --venues online`
3. Retain the unchanged consensus maindeck and replace its sideboard with the refresh's recommended
   current-online 15. Preserve confidence/degradation notes in the paired primer.

These are import files, not hosted Moxfield deck URLs. The project intentionally makes no Moxfield
write/API calls; upload the text through Moxfield's import UI to create hosted decks.
