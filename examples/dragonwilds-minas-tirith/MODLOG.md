# MODLOG: Minas Tirith in RuneScape: Dragonwilds

## 2026-10-23: Session 1 (cloud container, no game install)

**Request:** build Minas Tirith in Dragonwilds, for personal use, and give step-by-step instructions.

**Knowledge base:** no Dragonwilds notes yet.

**Recon** (web only):
- The game is Unreal Engine 5.
- UE4SS has a Dragonwilds build (Nexus mod 4).
- Jagex's Community Modding Guidelines allow mods for your own play, but not cheating in shared play and
  not paid mods.
- Dedicated and co-op servers are player-hosted.

**Route:**
- **WildPlans** (MIT, UE4SS Lua) already captures and places whole buildings from a text `.wplan`, and
  supports generated files written with shipped piece indices. We generate a blueprint for it instead of
  writing a spawner.
- Rejected: editing the `.sav` directly (no documented format; risk of corrupting the world).

**Reading WildPlans v0.1.4** (release zip, read as reference):
- the format, from `capture.lua` (`M.write` / `M.read`);
- piece IDs, from `pieceid.lua` and `derivedpaths.lua`;
- piece kinds and types, from `piecekinds.lua` and `piecetags.lua`;
- sizes, from `data/piece_bounds.txt`;
- placement rules, from `placemode.lua` and `replay.lua`.

**Piece set:** Tier 3 (Fellhollow) is the stone Castle set. We use:

| Piece | Index |
|---|---|
| Large foundation | 299 |
| Large wall | 399 |
| Plain medium wall (merlons) | 158 |
| Arrow slit | 829 |
| Castle doorframe | 495 |
| Straight stairs | 340 |
| Large floor | 49 |
| Window frame | 832 |
| Stained glass | 824 |
| Thick vertical beam (spire) | 12 |
| Wintumber tree prop | 432 |

The Kharidian (Tier 4) set is offered as `--style kharidian`.

**Generator:**
- 7 tiers rasterised on the 3 m grid, as stacked foundations.
- A wall, plus a merlon, on every edge where the ground steps down.
- One gate per tier, with stairs.
- The prow, with tunnels.
- The White Tower on a 3x3 footprint.
- A mountain ridge behind the city.

**Bugs found by the tests and fixed:**
- Neighbouring prow tunnels left the upper prow disconnected.
- One tunnel opened onto the wrong tier.
- At a 3.5 m step, the small size had terraces that only touched corner to corner.

Now every size passes all of the checks: the file parses, nothing is doubled, every foundation connects
to the ground, and the road reaches the Citadel.

**Outputs:**
- `MinasTirith.wplan`: 2,615 pieces.
- `MinasTirith_small.wplan`: 1,977 pieces.
- The preview and the plan.

**Not verified in game.** To check on the first run:
1. Which way the stairs face, and their height (`--stairs-flip`, `--stair-z`).
2. Whether all ~2,600 pieces land.
3. Whether it's stable without Architect.
