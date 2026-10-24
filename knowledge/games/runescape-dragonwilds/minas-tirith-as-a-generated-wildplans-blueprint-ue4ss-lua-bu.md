---
kind: game
title: Minas Tirith as a generated WildPlans blueprint (UE4SS Lua building mod)
game: 'RuneScape: Dragonwilds'
games_also: []
game_version: 1.0 (post-1.0 piece tables, WildPlans v0.1.4 data, 2026-09-30); not run by us
platform: windows
engine: unreal
route: loader-api
tools:
- UE4SS (Dragonwilds build, Nexus mod 4)
- WildPlans v0.1.4 (UE4SS Lua, github.com/kaedon78/WildPlans)
- Python 3.10 + Pillow (generator and preview)
anti_cheat: none known; Jagex's modding guidelines allow mods for your own play, not cheating in shared play
status: in-progress
agents:
- Claude Code (Opus 5.5)
humans: []
date: '2026-10-23'
links:
- https://github.com/kaedon78/WildPlans
- https://www.nexusmods.com/runescapedragonwilds/mods/4
- https://legal.jagex.com/docs/policies/runescape-dragonwilds-community-modding-guidelines
- examples/dragonwilds-minas-tirith
tags:
- building
- blueprint
- procedural
- ue4ss
- lua
---
# Minas Tirith as a generated WildPlans blueprint (UE4SS Lua building mod)

> We generated a 2,615-piece Minas Tirith for RuneScape: Dragonwilds as a WildPlans blueprint (`.wplan`).
> It's built only from the game's own Castle-kit building pieces, so it places, saves and loads like a
> hand-made base. The work was done from a cloud container with no copy of the game, so it is **not yet
> verified in game**. The format, piece numbers and sizes come from WildPlans' shipped data, and offline
> tests check the plan's geometry. The code is in `examples/dragonwilds-minas-tirith`.

## Setup
- **Game:** RuneScape: Dragonwilds, Unreal Engine 5, Steam, Windows. The game install is
  `steamapps\common\RSDragonwilds\RSDragonwilds\Binaries\Win64\RSDragonwilds-Win64-Shipping.exe`.
- **Saves:** `%LOCALAPPDATA%\RSDragonwilds\Saved\SaveGames\*.sav`.
- **UE4SS:** the Dragonwilds build from Nexus mod 4.
  - Its `dwmapi.dll` and `ue4ss\` go next to the shipping exe, and Lua mods go in
    `Win64\ue4ss\Mods\<Mod>\`.
  - Mod authors disagree on which build works: "UE4SS Steam (latest)", built against 3.0.1-gf6d5f942,
    or a UE 5.6 experimental build. If `UE4SS.log` says "Fatal Error", the build is too old.
  - The CurseForge app can silently reinstall an old UE4SS.
- **WildPlans v0.1.4** (MIT): one in-game panel that captures any player-built structure into a text
  blueprint and places it again. It can place free ghosts in any world, or real pieces in Creative worlds
  only. Blueprints live in `%LOCALAPPDATA%\RSDragonwilds\Saved\WildPlans\blueprints\`.

## Route and why
We generated a blueprint for an existing placement mod instead of writing our own spawner. WildPlans
already handles the hard parts:
- **Spawning:** the server RPC `Server_SpawnBuilding(int32 BuildingPieceDataIndex, const FTransform&,
  bool bSpawnGhost, const TArray<UInventoryComponent*>&)`.
- **Placement order:** lowest Z first, then by piece type; doors and props go last.
- **Retries:** passes that re-read the piece registry and retry whatever didn't land.
- **Pacing:** on the server, so big placements don't crash it.
- **Preview and undo:** a one-ghost placement preview, and removal of a placement.

We ruled out two alternatives:
- **Editing the world `.sav` directly:** the format isn't documented, and a bad write can corrupt a
  world. Jagex's guidelines specifically prohibit mods that damage saves.
- **A pak mod with a new mesh:** Minas Tirith as a single static mesh wouldn't be buildable or
  walkable, and it would need the matching UE editor.

## How the game works (what we had to learn)
**Building pieces**
- Every building piece is a `BuildingPieceData` asset under
  `/Game/Gameplay/BaseBuilding_New/BuildingPieces/<Tier>/...`.
- The spawn RPC takes its `BuildingPieceDataIndex`. About 840 pieces ship with the game.
- That index is **per installed content**, not stable. A mod that adds pieces (Custom Builder)
  renumbers almost all of them. WildPlans therefore keys pieces by asset path and writes
  `piecedata <index> <path>` lines. A generated file can use the shipped indices; WildPlans maps them.

**The kits**
- Tier1_Brynmoor is the Cabin set and Tier2_Ghornfell the Cottage set.
- Tier3_Fellhollow is the **Castle** set: stone, with castle doorframes, arrow slits and stained glass.
- Tier4_UmbralSands is **Kharidian**, the desert sandstone set.
- Guides say mixed sets don't align well.

**Sizes and pivots** (from WildPlans' `data/piece_bounds.txt`, the game's `BuildingPieceLocalBounds`)

| Piece | Size (cm) | Pivot |
|---|---|---|
| Large foundation | 300 x 300 x 300 | top centre (bounds z -300..0) |
| Large floor | 300 x 300 x 37.5 | top centre |
| Large wall | 300 x 100 x 300 | bottom centre; runs along local X |
| Medium wall | 150 x 150 | bottom centre |
| Straight stairs | 150 x 150 run | centre (bounds z -100..75) |
| Vertical beam | 300 tall | centre |

- The building grid is 150 cm. Yaw 90 turns local X onto world +Y.

**`.wplan` v2 format** (plain text)
- Header lines: `version 2`, `name`, `grid 150.0`, `origin x y z`, `origin_yaw`, `count`.
- Then one line per piece: `piece <index> <dx> <dy> <dz> <yaw> <sx> <sy> <sz> [ghost]`.
  Offsets are in centimetres, in the structure's own frame.
- `#` starts a comment.
- A piece line must not gain fields, or the reader rejects it.

**Placement and stability limits** (from WildPlans' own notes)
- Placement reach is about 175 m from the player.
- A ground foundation may float about 4.5 cm at most. A foundation that's held by the rest of the
  structure doesn't need to touch the ground.
- Props must be sunk about 4.5 cm into their surface, or the stability pass removes them. WildPlans
  does this itself.
- Doors placed into a ghosted frame crash the client, so the city has no doors, only doorframes.
- Stability counts outward from foundations and beams. Guides quote caps of about 5 high for ash and
  8 high for oak.
- The Architect mod removes the stability checks and raises the height cap.

## Build steps
1. Run `python examples/dragonwilds-minas-tirith/make_minas_tirith.py` (`--size small|medium|large`,
   `--style castle|kharidian`). It writes `MinasTirith.wplan`, an isometric preview and a top-down plan.
2. Copy the `.wplan` into `%LOCALAPPDATA%\RSDragonwilds\Saved\WildPlans\blueprints\`.
3. In a Creative world, press **N**, click the blueprint, then **REPLAY > PLACE**. Turn it to face the
   way you want, then press **O** for real pieces (or **N** for ghosts).

The example's README has the full player-facing steps.

## Verification
**Offline only** (`tests/test_minas_tirith.py`):
- the file parses with WildPlans' own piece-line pattern;
- nothing is doubled, and there's one wall-like piece per edge slot;
- every foundation connects face to face to the ground layer;
- only tunnel roofs overhang open air;
- every tier has a gate, a landing and two flights of stairs;
- a walk from the Great Gate along the terraces, up the gates and through the prow's tunnels reaches the
  Citadel.

**In game (2026-10-23, the human's PC):**
- UE4SS loaded, and WildPlans' panel listed both generated blueprints.
- The small city began placing in a Creative world, without Architect.

**Not yet verified:** how the finished placement looks. That includes the stairs' facing and pivot
height, whether all the pieces landed, and whether the tower and top tiers pass stability without
Architect.

## Gotchas
1. **Tunnels through the prow cut it loose.** On narrow tiers, tunnels on neighbouring prow slices formed
   a diagonal cut, and the prow's upper block had no connection to the ground. **Cause:** each tunnel
   roof leaned on a slice that had its own tunnel at that height. **Fix:** a tunnel's roof must rest on an
   intact slice just outside it. If a tier can't have a tunnel, the next gate stays on the same side
   instead of alternating.
2. **A tunnel opened onto the wrong terrace.** **Cause:** on a rasterised circle, the prow's centre line
   and its sides fall on different tiers. **Fix:** require the tier on both sides (j = ±2), not just the
   centre line.
3. **Terraces narrower than about 1.5 cells aren't walkable.** Rasterised rings that thin touch only
   corner to corner. **Fix:** a 4.5 m tier step at every size. The road test catches this.
4. **Generated blueprints have no real origin**, so REPLAY > IN PLACE would build at the map's origin.
   Use PLACE only.
5. **WildPlans didn't start, though its `enabled.txt` was present** (UE4SS for Dragonwilds, UE 5.6,
   2026-10-23). **Cause:** UE4SS started only the mods listed in `Mods\mods.txt`. **Fix:** add
   `WildPlans : 1` to `mods.txt`. The log is the check: a running WildPlans prints `[WildPlans] loading`,
   then `blueprints in <path>`.
6. **The blueprints folder wasn't created.** WildPlans makes
   `%LOCALAPPDATA%\RSDragonwilds\Saved\WildPlans\blueprints\` with `os.execute("mkdir ...")`, but on
   one install the folder never appeared. **Fix:** create it by hand; the panel lists whatever `.wplan`
   files are in it.
7. **Architect didn't work on that game build.** The log filled with `Tried setting member variable
   'MinStability' / 'MaxStability' / 'VerticalLoss' / 'HorizontalLoss' but UObject instance is nullptr`,
   then `Architect\Scripts\main.lua:203: attempt to get length of a UObject value (local 'profiles')`.
   **Cause:** the stability data it patches has moved, most likely since a game update. **Fix:** none
   yet. Set `Architect : 0` and expect the tallest parts to be limited by stability.
8. **Players look for the blueprint folder in the game's install folder.** It's in the user's
   `%LOCALAPPDATA%` on C:, not under `steamapps`. Give the Win+R path, not a description.

## Assets
None generated. The city is the game's own pieces, and the preview is drawn by the script with Pillow.

## Cost and time
One session, about two hours, all offline. No API spend.

## Open questions
- Which way does `DA_T3_Stairs_Straight` rise (+X assumed), and is its pivot 75 cm above its landing? The
  generator has `--stairs-flip` and `--stair-z`.
- Will a 2,600-piece placement go through WildPlans cleanly? Its largest tested placement was about
  1,150 pieces; the default pacing is 300 ms per piece and 2 s every 25.
- Do eight-high stacked foundations and the 12-storey tower stand without Architect?
- Houses on the terraces would make it read much more like a city.
