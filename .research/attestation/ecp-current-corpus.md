---
source_handle: ecp-current-corpus
fetched: 2026-08-03
source_path: data/legacy.duckdb
provenance: source-direct
substrate_confidence: source-direct
---

# Current Legacy corpus attestation

## Source structure

The DuckDB analytical store contains `tournaments`, `decks`, and `deck_cards` tables. Tournament
rows carry date, source, provenance, and URI; deck rows carry the assigned archetype; card rows
carry main/side board, card name, and count. The observations below were read directly from the
database in read-only mode.

## Key passages

1. **Window and coverage.** Querying decks joined to tournaments with
   `substr(t.date,1,10) >= '2026-05-18'` returns 4,847 deck records across 204 tournaments, spanning
   2026-05-18 through 2026-07-30. Provenance is 3,566 online deck records and 1,281 paper deck
   records; source labels are MTGO (3,566) and MTGmelee (1,281).

2. **Ranked archetype counts.** With the same date predicate, excluding `Unknown`, grouping by
   assigned archetype and ordering by deck count gives: Tron 320 (6.60% of all 4,847 records), Show
   and Tell 307 (6.33%), Izzet Delver 305 (6.29%), Energy 288 (5.94%), Dimir Tempo 284 (5.86%),
   Doomsday 268 (5.53%), Blue Artifacts 266 (5.49%), Grixis Reanimator 216 (4.46%), Azorius
   Midrange 214 (4.42%), Dimir Midrange 203 (4.19%), Lands 184 (3.80%), Death & Taxes 158 (3.26%),
   TES 101 (2.08%), Jeskai Midrange 97 (2.00%), Eldrazi 90 (1.86%), Mystic Forge Combo 80 (1.65%),
   White Beanstalk 70 (1.44%), Cradle Control 69 (1.42%), Izzet Midrange 69 (1.42%), Aluren 67
   (1.38%), Golgari Landfall 57 (1.18%), Dredge 55 (1.13%), Painter 51 (1.05%), and Oops! All
   Spells 45 (0.93%). `Unknown` has 82 records (1.69%) and was not promoted to an archetype.

3. **Tron through Energy, representative main-deck cores.** Deck-level inclusion counts in the
   same window show: Tron universally includes Planar Nexus, Karn, the Great Creator, Kozilek's
   Command, and the three Urza lands; The One Ring appears in 319/320. Show and Tell universally
   includes Show and Tell and Ancient Tomb, with Emrakul (303/307), Force of Will (302), Stock Up
   (299), Omniscience (296), and Atraxa (292). Izzet Delver universally includes Lightning Bolt,
   Force of Will, Brainstorm, Wasteland, and Dragon's Rage Channeler, with Ponder and Mishra's
   Bauble in 304/305 and Flow State in 297. Energy universally includes Guide of Souls and Ocelot
   Pride, with Wasteland (285/288), Swords to Plowshares (279), Voice of Victory (276), Ajani,
   Nacatl Pariah (272), and Amped Raptor (265).

4. **Dimir Tempo through Grixis Reanimator, representative main-deck cores.** Dimir Tempo
   universally includes Wasteland, Force of Will, Brainstorm, Underground Sea, Polluted Delta,
   Ponder, Thoughtseize, and Undercity Sewers; Fatal Push appears in 282/284, Orcish Bowmasters in
   278, Tamiyo in 277, and Daze in 271. Doomsday universally includes Force of Will, Dark Ritual,
   Doomsday, Brainstorm, Polluted Delta, and Ponder, with Lotus Petal in all 268 and Thassa's Oracle
   in all 268. Blue Artifacts most often includes Lotus Petal (264/266), Mox Opal (260), Urza's
   Saga (258), Mishra's Bauble (239), Skateboard (222), Emry (221), and Urza's Bauble (220).
   Grixis Reanimator universally includes Unmask, Dark Ritual, Animate Dead, Reanimate, Griselbrand,
   Atraxa, and Badlands; Lotus Petal appears in every list with a 3.9-copy mean.

5. **Azorius Midrange through Death & Taxes, representative main-deck cores.** Azorius Midrange
   universally includes Brainstorm, Force of Will, and Flooded Strand; Swords to Plowshares appears
   in 213/214, Ponder and Tundra in 212, Tamiyo in 203, and Wasteland in 201. Dimir Midrange most
   often includes Polluted Delta (202/203), Thoughtseize (202), Force of Will (201), Underground
   Sea (201), Undercity Sewers (201), Brainstorm (199), and Flow State (188). Lands universally
   includes Urza's Saga, Wasteland, Mox Diamond, Exploration, Life from the Loam, Thespian's Stage,
   Boseiju, Dark Depths, and Maze of Ith. Death & Taxes universally includes Karakas; Wasteland and
   Witch Enchanter appear in 157/158, while Swords to Plowshares, Aether Vial, Recruiter of the
   Guard, and Solitude appear in 152.

6. **TES through White Beanstalk, representative main-deck cores.** TES universally includes Dark
   Ritual, Lotus Petal, Lion's Eye Diamond, Burning Wish, Chrome Mox, Mox Opal, Beseech the Mirror,
   Echo of Eons, Gaea's Will, and Tendrils of Agony. Jeskai Midrange universally includes Swords to
   Plowshares, Brainstorm, Force of Will, Flooded Strand, Tundra, and Volcanic Island, with
   Prismatic Ending and Force of Negation in 91/97 and Flow State in 88. Eldrazi universally
   includes Lotus Petal, Eldrazi Linebreaker, Cavern of Souls, Kozilek's Command, Thought-Knot Seer,
   Eldrazi Temple, Ancient Tomb, and Glaring Fleshraker; Chalice is in 88/90. Mystic Forge Combo
   universally includes Ancient Tomb and Grim Monolith, with The One Ring in 78/80, Urza's Saga and
   Manifold Key in 76, and Mystic Forge in 58. White Beanstalk universally includes Flooded Strand,
   Swords to Plowshares, Brainstorm, Force of Will, Up the Beanstalk, Tundra, and Tropical Island;
   Leyline Binding appears in 62/70.

7. **Cradle Control through Aluren, representative main-deck cores.** Cradle Control universally
   includes Green Sun's Zenith, Wight of the Reliquary, Verdant Catacombs, Bayou, Gaea's Cradle,
   Forest, Talon Gates of Madara, and Dryad Arbor; Ignoble Hierarch appears in 68/69 and Once Upon a
   Time in 67. Izzet Midrange universally includes Force of Will, Brainstorm, Mishra's Bauble,
   Ponder, and Flow State; Cori-Steel Cutter appears in 68/69, Wasteland in 65, and Lightning Bolt
   in 65. Aluren universally includes Aluren, Misty Rainforest, Acererak, and Ancient Tomb; Force of
   Will, Brainstorm, Ponder, Tropical Island, and Hedge Maze appear in 66/67, Stock Up in 64, Lotus
   Petal in 60, and Veil of Summer in 60.

8. **Golgari Landfall through Oops, representative main-deck cores.** Every Golgari Landfall list
   includes Hogaak, Thoughtseize, Verdant Catacombs, Moonshadow, Wasteland, Stitcher's Supplier,
   Orcish Bowmasters, and Wight of the Reliquary. Dredge most often includes Cabal Therapy (53/55),
   Cephalid Coliseum, Stinkweed Imp, Golgari Grave-Troll, Narcomoeba, Bridge from Below, and
   Poxwalkers (52 each), and Otherworldly Gaze (51). Painter universally includes Ancient Tomb,
   Urza's Saga, Painter's Servant, and Grindstone; Pyroblast, Goblin Engineer, and Goblin Welder
   appear in 46/51. Oops universally includes Dark Ritual, Lotus Petal, Simian Spirit Guide,
   Balustrade Spy, Boggart Trawler, Cabal Therapy, and Dread Return; Thassa's Oracle appears in
   44/45.
