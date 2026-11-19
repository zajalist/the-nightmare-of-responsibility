# The Nightmare of Responsibility

A short narrative game about the scariest monster of all: an ordinary morning. Getting dressed is a boss fight, and every fear is made of black sand generated with Aholo Lux3D.

Made in Unreal Engine 5.9, entirely in Blueprints, for the Aholo 3D AI hackathon (November 2026).

This repository holds the code and tooling behind the game, shared for the judges. The playable Windows build and the project report are part of the hackathon submission.

## What is here

| Folder | What it does |
|---|---|
| `Tools/Lux3D` | Batch generation against the Aholo Lux3D API: prompt tables in, GLB meshes, Gaussian-splat PLYs, auto-rigged characters and retargeted motion out. The API key is read from the user's home folder and never stored here. |
| `Tools/Splats` | `ply_to_splatmesh.py` turns a Lux3D or Aholo SpatialGen splat file into one static mesh, one camera-facing quad per splat, drawn by a single masked material. A 4.5 million-splat object ships as 14,000 to 24,000 quads. See `Tools/Splats/README.md`. |
| `Tools/Unreal` | Editor automation used to build the game: Blueprint graph builders, level and cinematic setup, material and UI passes, the Level 2 job hunt, the ending. Most of it drives the editor through Hayba, an MCP toolkit for Unreal. |
| `Tools/Unreal/gameplay/pie_play.py`, `Tools/QA` | Automated playthroughs. Each plan boots the real front end in Play In Editor and plays the game through its own inputs, filming every beat and checking the result. |
| `Tools/Perf` | Packaging from a mirror, cooked-build drivers, PSO cache recording, frame-time and size reports. |
| `Plugins/FoAGraphTools` | A small C++ editor plugin that renders any Blueprint, widget or material graph to a PNG, used to review every graph we built. |
| `Config` | Engine, game and scalability settings, including the per-preset dynamic resolution and the bundled shader pipeline cache. |
| `docs` | Design notes, the Lux3D prompt tables, editor rules for the agent lanes, and submission planning. |

## What is not here

`Content/` (the Unreal assets, several GB of binary files) is not included. It contains MetaHuman, licensed music and other third-party assets that cannot be redistributed in a public repository. The packaged build shows all of it.

## How it was built

Several AI agent lanes worked in parallel on one shared Unreal editor through Hayba. Each lane leased only the assets and actors it changed, editor writes went through Hayba's native tools with compile, save and rollback in one call, and every change was proven by rendering or by an automated playthrough before it was kept.

## Credits

Aholo Lux3D and Aholo SpatialGen by Manycore. Unreal Engine and MetaHuman by Epic Games. Poly Haven (CC0). Quaternius animation (CC0). Natural Resources Canada CanElevation LiDAR and City of Toronto 3D Massing (Open Government Licences). Darker Grotesque and IBM Plex Sans (SIL Open Font License). Sound from Sonniss and Kenney. Full credits, including music, are in the game.
