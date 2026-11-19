# FoA agent rules (read before touching the editor)

## Project
- **FoA, "The Nightmare of Responsibility":** an Unreal 5.8 Blueprint-only project at `P:\FoA`.
- **Hackathon:** the Aholo/Manycore 3D AI hackathon, deadline Nov 19 2026. Judging gives 30% to using Lux3D (Aholo's 3D generator). The user wants to win.
- **The user's bar:** they watch the editor live and are impatient. They want visible, production-grade results in the open editor, not plans or offline-only work. Don't settle for mediocrity: compare against real references and iterate until it looks professional.

### Locked art direction
- Fully monochrome: a post-process (`PP_DreamMono` + `MPC_Dream`) turns everything black and white with a slight hue drift over the story.
- The base is photoreal B&W, with inked contrast and smoke-and-sand tendrils on top.
- The sand is BLACK.
- No Niagara for hero VFX. Use Gaussian-splat meshes plus materials (see `Tools/Splats/README.md`).
- Low-end PCs, and the build stays under 1 GB.
- Third-person camera, with top-down at times.
- Assets are realistic and take texel density seriously, about 1024 px/m.

## The level
- **Open level:** `/Game/FoA/Maps/L_Tutorial_Bedroom`. Units are cm, Z is up, the floor is at z=0 and the ceiling at z=300.
- **Room outline** (interior, clockwise): `[(-375,300),(375,300),(375,-300),(90,-300),(30,-390),(-150,-390),(-210,-300),(-375,-300)]`. The bay alcove runs from y=-300 to -390. Walls are 30 cm thick and sit outside the outline.
- **Openings** (`Tools/Unreal/bedroom_v3.py` OPENINGS, where s is cm along the segment from its first point):
  - **Door:** east wall x=375, from y=135 to y=40, z 0–215.
  - **Bay windows:** z 85–215 on segment 3 (s 26–82), segment 4 (y=-390, x -5 to -115) and segment 5 (s 26–82).
- **Chimney breast:** on the west wall, protruding to x=-330 between y=-80 and y=80. The firebox opening is ±45 wide and 85 tall. The mantel is at z=125.
- **Cameras** (pitch, yaw):

  | Camera | Location | Rotation |
  |---|---|---|
  | Shot_ThirdPerson | (-60,-60,175) | (-8.1, 18.7) |
  | Shot_Wide | (-340,280,270) | (-16.9, -50.3) |
  | Shot_Window | (250,100,160) | (-2, -124) |
  | Shot_TopDown | (0,-45,1500) | looking down |

- **Outliner folders:** Room/Walls, Room/Trim, Room/Windows, Room/Chimney, Room/Furniture, Interactables/*, Lighting, FX/*, Dev/ShotCameras.
- **The user's hand-placed furniture.** Never move or delete these unless your brief says so: Bed, Bedding_Lux3D, Desk, Chair, DeskLamp, Commode*, Wardrobe*, Nightstand, Boot_L/R, Key_Lux3D, WallClock*. Nothing may float: every prop sits on a surface.

## Assets on disk
- `P:\FoA-Assets\polyhaven\`: CC0 models and 2k texture sets (`MANIFEST.md` lists everything, including the set-dressing models and the rug textures).
- `P:\FoA-Assets\lux3d\<item>\`: Lux3D outputs, as GLB meshes (`textured.glb`) or splat PLYs (`gaussian.ply`). The prompts and task IDs are in `docs/lux3d-bedroom-prompts.md`.
- `P:\FoA-Assets\splatmesh\`: Lux3D splats converted to splat-mesh glTFs by `Tools/Splats`.
- `P:\FoA-Assets\procedural\`: procedural glTFs and `T_Lines.png`.

## Driving the editor
1. **Use Hayba.** Drive the editor with the Hayba MCP tools (`mcp__hayba-toolkit__*`). Find a tool with `hayba_search_tools`, read its parameters with `get_tool_signature`, then call `hayba_invoke`.
   - Plan Mode is OFF. Never call `hayba_propose_plan`.
   - The user watches Hayba's live tool stream, so use Hayba for everything they would see change.
2. **Python-backed Hayba tools are broken.** Many fail with `python_run policy_blocked [HCR-TIME-001]`, including `actor_batch_transform` and `asset_open_editor`.
   - Use the C++-backed tools: `actor_transform` (one actor per call), `actor_spawn_from_asset`, `actor_delete`, `actor_set_properties`, `physics_set_collision_profile`, `material_*`, `texture_set_settings`, `ui_*`, `blueprint_*`, `light_set`, `editor_capture_viewport`, `level_save`.
   - Hayba's own `python_run` may not contain `try` and must finish within 5 s.
3. **When you need editor Python Hayba can't run** (glTF/GLB import through Interchange, file IO):
   - Run `python Tools/Unreal/ue_remote.py <script.py> KEY=VALUE ...` from `P:\FoA`, with `$env:FOA_AGENT='<your lane>'`.
   - The script runs inside the same editor. The KEY=VALUE pairs reach it as `os.environ`.
   - It serializes on `Saved/FoA_editor.lock` with the other agents, so keep scripts short.
   - Import helpers to copy are in `Tools/Unreal/build_bedroom.py`.
4. **Hayba `asset_import`:**
   - It only accepts files staged under `%TEMP%\hayba-asset-connectors\<any>\<dir>\`, so copy them there first.
   - The asset name is the file's basename, and it never overwrites an existing asset.
   - Types: texture (PNG/JPG), sound_wave (WAV), static_mesh (binary FBX).
5. **Hands off the rest of the session.**
   - Never load or close another level, restart or quit the editor, or call `editor_save_all_and_quit`.
   - Stay inside your own lane's actors, assets and folders. Other agents are editing at the same time.
6. **Look at your work.** Screenshot it, look at it, and iterate.
   - **Level:** `editor_capture_viewport`. Save the user's camera with `editor_get_camera` first, and restore it afterwards with `editor_set_camera`.
   - **Graphs and asset editors:** run `python Tools/Unreal/ue_remote.py Tools/Unreal/open_asset.py FOA_ASSETS=/Game/Path/Asset`, then `powershell -File Tools/Capture/capture_window.ps1 -Title "FoA - Unreal Editor" -Out P:/FoA/Saved/GraphShots/<name>.png`, then Read the PNG. Asset editors open as tabs in the main window.
   - **Widgets:** `ui_render_widget_to_png`.
7. **Blueprint graph authoring.** Hayba's `blueprint_add_node` only makes 7 node types, but UE 5.8's built-in Python can author full graphs through `ue_remote.py`:
   - `unreal.BlueprintGraphEditor`: add_custom_event_node, create_node_from_name (any palette node, such as Create Widget), add_call_function_node, add_comment_node, add_comment_to_nodes, add_get/set_member_variable_node, add_branch_node, set_node_pos.
   - `unreal.BlueprintGraphPinLibrary`: try_create_connection, set_pin_value.
   - `unreal.BlueprintEditorLibrary`: add_event_override, add_event_dispatcher, the variable flags, set_comment_text and set_comment_color.
8. **Production-grade graphs** (the user's words): "no clutter of nodes and outgoing edges, everything is well-organized and commented just like real devs".
   - Material graphs: comment boxes per functional group, left-to-right flow, named reroutes instead of long wires. Move busy subgraphs into material functions.
   - Screenshot every graph you build and fix its layout until it reads cleanly.
   - Be lean (the user's words: "we need to be lean in our node usage while also making good quality production grade materials"). Sample a texture once and mix channels with one Dot. Pack related scalars into vector parameters. Prefer built-in nodes (DepthFade, CameraDepthFade). Don't hide three-node groups in functions. Give every comment box a short title only (see "Comment boxes: title only" below). Report node and instruction counts.
   - Comment style (the user's reference, M_LightShaft): every comment box has a clear title AND "Show Bubble When Zoomed" plus "Color Bubble" turned on, so a large title bubble floats above each box and stays readable when zoomed out. Size boxes snugly, never overlapping, with one consistent colour per group. The Blueprint equivalent: comment nodes with "Show Bubble When Zoomed" and "Color Bubble", via set_comment_text/set_comment_color and the comment node properties.
9. **Save and report.** Save new assets, and call `level_save` after placing actors. Report back briefly: what changed (asset paths and actor labels), the screenshot paths, and any failures. Don't write report or summary .md files.
10. **Licensing.** Use only CC0 assets, or permissive licenses with the attribution recorded (for example CC-BY or Sonniss royalty-free). Record the source and license of every downloaded file next to it, in `SOURCES.txt` or the existing `MANIFEST.md`.

## Crash safety (added after the 17:05 editor crash)
The editor crashed with an access violation in PythonScriptPlugin right after one lane saved material functions it had edited through Python. The widget-variable GUID ensure in the crash header was stale: it fired about 14 minutes earlier, when a widget tree was deleted and rebuilt. Edit widgets in place, never delete and rebuild them. When the editor crashes, every lane loses its unsaved work, so:
1. **Save right after every meaningful change.** Hayba `asset_save` is blocked, so save your own assets through `ue_remote.py` with `unreal.EditorAssetLibrary.save_asset('<path>')`, and save the level with Hayba `level_save` after placing actors.
2. **Close an asset's editor tab before you mutate its graph through Python** (`unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)`). Editing material expressions while the Material Editor has the asset open is a known crash source. Open it again afterwards only to take a screenshot.
3. **`MaterialEditingLibrary.delete_all_material_expressions(_in_function)` silently skips about half the nodes.** Delete from a snapshot list instead, then recompile.
4. **Widgets:** before deleting a widget that is a variable, remove its graph references, then compile and save. Never leave a Widget Blueprint uncompiled after removing widgets.
5. **Keep editor Python scripts short**, under 60 s, and never run unbounded loops or long-lived tick callbacks. If Hayba times out because another lane holds the editor lock, wait and retry with backoff; don't hammer it.
6. **PIE stalls every other lane.** Run it only in short bursts (45 s or less), and only when your brief allows it.
7. **Whole-graph screenshots:** after the restart, the `FoAGraphTools` plugin provides `unreal.FoAGraphToolsLibrary.capture_graph_png(asset, graph_name, png_path, zoom_to_fit=True)`. It writes the PNG about 1.5 s later; see the header of `Tools/Unreal/graphtools_selftest.py`. Opening a Blueprint to capture its graph can leave it BS_DIRTY: compile and save it right after the capture, because the QA pre-flight holds every lane's PIE burst while any Blueprint is dirty (2026-11-18).
8. **Tick callbacks must check what they touch on every tick** (added after the 22:40 freeze, world lane). In a `register_slate_post_tick_callback` driver, check `unreal.SystemLibrary.is_valid` on the PIE world and on every actor you cached before touching them. If PIE ended or was replaced, unregister without touching anything. Wrap the whole tick in try/except so that any error unregisters the callback. A destroyed actor's setters raise no Python error. They hit a C++ ensure: the world lane's `perf_driver.py` kept moving a destroyed CameraActor after PIE ended, the ensure hung in the crash reporter, and the editor was lost. The pattern is `world_alive()` plus `tick()` in the world lane's `perf_driver.py`.

## UI and on-screen text style (the user's hard rules)
- NEVER a middle dot "·" in any in-game text, widget or title card. No other decorative separators in its place either: no "•", "|", "/", "—" or "–" as separators.
- No divider lines (short horizontal rules) under titles or between sections.
- No generic web-template look: tiny tracked-out all-caps eyebrow labels strung together with separators. Use real hierarchy (size, weight, spacing, position) and plain sentences.
- The title is the game's real name, "The Nightmare of Responsibility", designed as a proper logotype. "FoA" is only the project codename and never appears as a player-facing title.

## Lean content (the user's rule)
The user's words: "try not to overburden the game content thing with thousands of things, let's be very critical about the assets we make and how we can reuse them and keep it lean and production, cleanup assets that have no use".
- Before creating an asset, check whether an existing one can be reused or parameterised: a material instance of an existing master, a shared material function, a shared texture set, or an existing mesh.
- One master material per surface family. Variations are material instances, never copied masters.
- Texture budget: 2k only for hero or close-up surfaces, 1k for props, 512 for small items. Share texture sets across assets.
- No test, temp or scratch assets left in /Game/FoA. Delete your own superseded versions as soon as the new one is verified and referenced, after checking with `unreal.EditorAssetLibrary.find_package_referencers_for_asset` that nothing still uses it.
- Every asset you keep must be used by the game (in a level, referenced by a Blueprint, or part of a shipped system). Name it by convention (SM_, M_, MI_, MF_, T_, BP_, WBP_, ABP_, DT_, DA_, S_ or SC_) in the right folder.

## Editor leases: lanes work at the same time (replaces the single-writer lock, 22:15, hayba lane)
The old single-writer lock is retired. The crashes it was built for were the python311 GC bug, which is fixed (see below). Lanes now hold Hayba leases on only what they change, and lanes on different areas or actors work at the same time.
1. **Identify yourself:** `$env:HAYBA_AGENT_ID='<lane>'` (FOA_AGENT still works). Use the same name every time.
2. **Hold only what you change, and release right after each batch.**
   - `python Tools/Unreal/editor_lock.py acquire <lane> --areas UI` blocks until granted. Other options: `--assets /Game/FoA/UI/WBP_X`, `--actors Bed,DeskLamp` for level actors you edit, and `--actors-new TMP_<lane>_` for actors you spawn.
   - Areas: VFX, UI, Characters, Gameplay, PostProcess, Audio, Materials, Cinematics. `Level` only for bulk work on arbitrary actors.
   - `python Tools/Unreal/editor_lock.py release <lane>`. `editor_lock.py status` shows holders and waiters.
   - A hold lapses after its ttl (default 600 s, max 900 s); `editor_lock.py renew <lane>` extends it. Never hold during offline work.
3. **EXCLUSIVE** (`acquire <lane>` with no areas) waits for every holder and stops everyone after it. Use it only for PIE, asset deletes, GC-heavy runs and restarts, and keep it short. MetaHuman builds run only in an announced EXCLUSIVE window (or on editor B).
4. **Level save:** `python Tools/Unreal/editor_lock.py save_level <lane>`. It queues behind actor holders, saves and releases; asset-only lanes never wait for it. Don't hold Level just to save.
5. **ue_remote.py:** ALWAYS set `$env:FOA_AREAS` (comma list), plus `FOA_ACTORS` / `FOA_ACTORS_NEW` for level actors. With none set and no hold of yours, the run takes EXCLUSIVE and stalls every lane. Inside your own hold it reuses it.
   - Keep each run under about 30 s: a run holds the editor's single game thread, so every lane's Hayba calls wait behind it. Chunk imports and builds; longer runs print a warning.
   - Each run gets a private namespace, KEY=VALUE env vars are removed afterwards, and GC runs after it. Keep asset references inside functions, and never delete or rename assets in the same run that loads or edits them.
6. **Single Hayba calls** (MCP or `Tools/Unreal/hayba_call.py`) need no lease: each one runs alone on the game thread. Multi-step edits of shared assets do.
7. **If Hayba is unreachable** (the editor is busy in a long command, or its connection slots are full), editor_lock keeps waiting. It falls back to the old file lock only when the editor is not running.
8. **Deleting or renaming assets:**
   - first close their editors (`AssetEditorSubsystem.close_all_editors_for_asset`) and check their referencers;
   - then delete in a separate short run, with `unreal.EditorAssetLibrary.delete_asset` or Hayba `asset_delete`;
   - never force-delete.
9. **Post-process materials:** never save or recompile a post-process material or function while it is an active blendable on PP_DreamMono. Take it off the volume, rebuild it, then put it back.
10. **Git Bash:** set `MSYS_NO_PATHCONV=1` when passing `/Game/...` arguments.
11. **Hayba quirks:**
   - `actor_batch_spawn` reads rotation as [pitch, yaw, roll];
   - `actor_spawn_from_asset`, `actor_inspect`, `editor_get_camera`, `asset_save`, `asset_open_editor`, `mesh_get_bounds` and `actor_batch_transform` are blocked by Hayba's Python policy;
   - `editor_capture_viewport` can come back black: capture with a temporary SceneCapture2D or `Tools/Unreal/shoot_live.py`.

## User-placed actors
The user edits the level by hand. Before changing any actor you didn't just create, compare its transform with what your lane last set. If it differs, the user moved it: leave it alone. Never re-run a full placement or build script over the level; touch only the specific actors you're fixing. Known user placements: the books (Nov 5), Bedding_Lux3D's fit on the bed, and the desk lamp and table positions.

## Material graphs: Hayba C++ tools only (added after the third material-Python crash)
This rule was written after three crashes (17:05, 17:26 and 17:57) that turned out to be the python311 GC bug described below, not material editing. It stays in force because Hayba comes first:
- Create, connect, delete, set, comment and compile material and material-function nodes ONLY with Hayba's C++ material tools: material_create, material_function_create, material_add_node, material_connect_nodes, material_disconnect, material_delete_node, material_set_node (which also moves nodes), material_add_comment, material_set_comment, material_add_reroute_*, material_set_property, material_validate, material_compile, material_create_instance, material_set_param.
- Python may READ material graphs (get_inputs_for_material_expression and so on) and set material-instance parameters, but never mutate a material graph.
- Run material_validate before material_compile. If a compile fails, fix it before saving, and never leave a material that fails to compile assigned in the level.

## No camera clutter in the level (the user's request)
Never leave cameras, scene captures or helper actors in the level. For captures, spawn a temporary camera or SceneCapture2D, take the shot, and destroy it in the same run. The user deletes camera clutter by hand (Shot_Wide and Shot_Window were removed on purpose): never recreate cameras. Capture from pose data with a temporary camera or SceneCapture2D, destroyed in the same run. The poses, as (x, y, z) and (pitch, yaw):

| Pose | Location | Rotation |
|---|---|---|
| ThirdPerson | (-60, -60, 175) | (-8.1, 18.7) |
| Wide | (-340, 280, 270) | (-16.9, -50.3) |
| Window | (250, 100, 160) | (-2, -124) |
| TopDown | (0, -45, 1500) | (-89.9, 0) |

Only game cameras that ship (for example BP_MenuCamera) persist.
- After an editor restart, the asset registry may not list newer folders (does_asset_exist and list_assets return nothing). Run `unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/FoA/<YourFolder>'], True)` first.

## Structural Blueprint edits (added after the 18:19 crash)
The editor crashed with a null pointer in the Level Editor right after a script removed and recompiled a function graph on BPC_Inventory.
- Build scripts must be idempotent and edit in place: create a function, variable or graph only if it's missing, and update its nodes. Never delete and recreate function graphs, variables or dispatchers on every run.
- Before any structural change (removing or renaming functions, variables or components, or reparenting): deselect all actors (`EditorActorSubsystem.select_nothing()`), close the Blueprint's editors, and make sure no actor in the level is mid-edit in the Details panel. Then compile once and save.
- If a Blueprint must be rebuilt from scratch, delete the whole asset in its own run (after the referencer check, with no instances in the level) and create it again, rather than gutting it in place.
- Never call LevelEditorSubsystem viewport functions (realtime, pilot, game view) from scripts. Use a temporary SceneCapture for captures instead.
- Exception to the material rule: Python may set only the two comment-bubble flags (Show Bubble When Zoomed and Color Bubble) on existing material comment expressions, with the asset's editor closed, then compile and save through Hayba `material_compile`.
- Shared layout tool: `Tools/Unreal/graph_layout.py` plans a clean, spaced layout and emits Hayba calls (`material_set_node`, `material_set_comment`). Run it at the end of any material build (see its docstring).
- Never call `BlueprintEditorLibrary.add_function_override` on Widget Blueprints. It crashed the editor at 18:53 (an access violation in BlueprintEditorLibrary) after working three times. Handle keys and events in Construct, with bound events or the existing input pattern, instead.

## Clean up after testing (the user's rule)
Leave the level and Content exactly as tidy as you found them, apart from your real deliverables. Before you release the lock after any test:
- Delete every temporary actor you placed: probe meshes, test lights, debug spheres, capture cameras, scratch sequences' spawned actors, markers. Check the outliner for anything with your lane's prefix or a Test/Tmp/Probe/Debug/Scratch name.
- Delete scratch assets: test materials and instances, throwaway widgets, temp render targets, duplicated "_old"/"_v1"/"_test" assets nobody references. Do it in a separate delete run, with editors closed.
- Restore anything you toggled: view modes, show flags, CVars, actor visibility, MPC values, Time Dilation, PIE settings.
- Keep screenshots and MP4s under Saved/, never in Content/.
Name temporary things `TMP_<lane>_*` from the start, so the cleanup is one search.

## Maintenance holds and relaunching (added 19:40)
- Never launch UnrealEditor yourself. Only the coordinator (main) relaunches it. A lock held by `main:MAINTENANCE-...` means the editor is deliberately closed (an engine install is running): keep working offline and wait.
- Don't create macro nodes (ForLoop, ForLoopWithBreak, ForEachLoop, WhileLoop) from script with create_node_from_name and then call BlueprintEditorLibrary on them. That crashed the editor at 19:30 (an access violation in BlueprintEditorLibrary). Loop with plain function nodes and an index counter instead.
- Impure nodes (GetActorOfClass, DoesSaveGameExist, GetGameUserSettings, Map Keys, and so on) must sit on the exec path. Wired as data only, the compiler prunes them and they return None without any error.
- Compile only when something actually changed.

## The python311 crashes: cause found and fixed (21:15, hayba lane)
Six crashes (17:05, 17:26, 17:27, 17:57, 20:29, 20:37) were one bug in Epic's PythonScriptPlugin, not in material editing, compiles or reinstancing:
- Every bound Unreal method (for example `BEL.get_array_type`, `unreal.EditorAssetLibrary.save_asset`) is an object whose type claims a weakref slot one slot past its own end.
- When such an object becomes cyclic garbage, Python's garbage collector writes through leftover memory and the editor dies with EXCEPTION_ACCESS_VIOLATION in python311.
- Any GC triggers it: gc.collect, Python's automatic GC, or Unreal's GC (each Blueprint compile runs one, which is why compiles looked guilty).
- The proof (minidumps, an offline repro and Hayba commit 8a715bbf) is in the Hayba repo, `tools/psp-weakref-repro`.

The fix is `hayba_psp_hotfix.py`:
- It was applied to the running editor at 21:11.
- It now runs at every editor start: a StartupScripts line in Config/DefaultEngine.ini, and the next Hayba DLL applies it too.
- The editor opened at 21:10 was patched live, and its Saved/Logs/FoA.log shows "LogPython: apply -> patched" (21:11:58).
- From the next editor start on, the log shows "Hayba PSP hotfix: patched" (or "ok"). If a restarted editor's log has neither, tell the hayba lane before running any Python.

What changes:
- `BlueprintEditorLibrary.compile_blueprint` from Python is allowed again, and so is writing a CDO before or after a compile.
- No ordering rule is needed. The "never compile from Python" ban and the "dangling wrapper types" explanation were wrong and are withdrawn.
- Hayba first still holds (below), so prefer `blueprint_compile`, `ui_compile_widget`, `anim_blueprint_compile` and `material_compile` when you are already using Hayba.
- Still good hygiene: keep scripts short, keep asset references inside functions, and don't delete or rename an asset in the same run that edits it.

## Hayba first (the user's rule, 20:42)
"People should prioritize using Hayba, which is safer than Python." Use a Hayba C++ tool whenever one exists for the job: actors, transforms, properties, materials, widgets, Blueprints (blueprint_* plus blueprint_compile), anim, audio, save, level_save, capture. Use editor Python only for what Hayba can't do yet, and keep those runs short and structural.

## Missing Hayba tool? Ask for it (the user's rule)
"If a feature is missing from Hayba, just have an agent add it." When your job needs editor Python because no Hayba tool covers it, message the hayba-tools lane (a6b746b19f023cf3a). Start the message with "Hayba gap:", then the exact operation, its inputs, and the asset or actor it acts on. It builds the tool, pushes it, and replies with the tool name. Until the tool ships, use the safest Python path under the rules above, and keep it short and structural.

## Document everything (the user's rule: "have everything ready for documentation and devlogs")
Every deliverable image, GIF, MP4 and graph capture goes under P:\FoA\Saved\ (or P:\FoA-Devlog\) with a descriptive name. Before and after pairs are named *_before / *_after. After each hold, append one line per deliverable to P:\FoA-Devlog\media_log.jsonl:
{"t":"<HH:MM>","lane":"<lane>","what":"<one plain sentence>","files":["<absolute paths>"]}
The devlog is cut later around the user's recorded voice-over from this log, so be specific about what changed. The desktop recorder runs continuously; don't stop it.

## Comment boxes: title only (the user's rule, 21:20)
"Don't add comments to graph nodes, the title is enough." Every comment box carries a short title, 2–5 words, such as "Combine" or "Resolve cost", and nothing else: no description sentences under it and no per-node comment bubbles. The graph's grouping and node names have to explain it. When you re-lay or touch an existing graph, strip the description text down to the title.

## Killing processes
Kill only processes you started, by the PID you recorded when you started them. Never kill by name or command-line pattern (bash, python, ffmpeg, sleep, UnrealEditor, ShaderCompileWorker): other lanes and the coordinator's recorder and watchdog run the same programs. If a process that isn't yours looks stuck, tell the coordinator.

## PIE windows and declared runs (2026-11-05 23:50)
- A waiting EXCLUSIVE blocks every later lease request, so each PIE burst stalled about 15 lanes. EXCLUSIVE now starts only in a PIE window: the first 3 minutes of every 10 (:00-:02, :10-:12, ...). `editor_lock.py acquire` waits for the window by itself. Keep every EXCLUSIVE hold to 60 s or less.
- `ue_remote.py` refuses a run that declares nothing. Set FOA_AREAS, FOA_ACTORS or FOA_ACTORS_NEW, or FOA_EXCLUSIVE=1 for PIE and deletes. It no longer falls back to EXCLUSIVE.
- Hold a lease for one editor step only: acquire, run, release.

## When the user plays
Each editor Python run stalls the game thread for 0.9 to 3 s (hitch hunt, 2026-11-06), which the user feels as lag spikes while playing. When PIE is running and no lane holds EXCLUSIVE, the user is playing: ue_remote.py now waits by itself until PIE ends. Prefer Hayba C++ commands for anything that must run then.

## Process hygiene (added 2026-11-09)
- **Stopping a background chain:** kill its whole process tree by PID (`taskkill /T /F /PID <root pid>`), your own processes only. Stopping a tool task kills only the wrapper shell, and orphaned chains kept driving PIE twice on 11-09. Write each chain's root PID to a file when it starts, and check with tasklist that no child survives before starting a new one.
- **PIE begin and end** go through `Tools/Unreal/ui/pie_call.py`. END only stops a PIE the caller started (`FOA_CALLER` is passed automatically; `FOA_FORCE=1` overrides).
- **EXCLUSIVE during a burst:** renew every 20–30 s (`editor_lock.py renew <owner> --ttl 70`) and stop driving if "<owner>: exclusive" is gone from status.
- **Git Bash:** export `MSYS_NO_PATHCONV=1` before passing /Game paths.
- **Never leave a Blueprint, widget or material failing to compile in memory.** Compile after every edit step, and on failure roll back your own nodes and recompile; save only at 0 errors. When any Blueprint is broken, `pie_call BEGIN` (editor_request_begin_play) opens a modal "Blueprint Asset Compilation Error" dialog. On 11-09 that froze the shared editor for about 6 h; it grew to 32 GB, starved the machine and dropped every lane. Runners compile-check the key Blueprints before starting PIE.
- **Referencer checks before a delete use the asset registry**, `unreal.AssetRegistryHelpers.get_asset_registry().get_referencers(pkg, unreal.AssetRegistryDependencyOptions())`. Do not use `EditorAssetLibrary.find_package_referencers_for_asset`: after the 11-09 21:50 relaunch it returned [] for in-use assets (M_Surface: 0 vs the registry's 3), so a delete gate built on it passes assets that are still used. `Tools/Cleanup/cleanup_worker.py` and `Tools/Unreal/delete_unused.py` are already switched (22:00).
- **Window watchers touch titled windows only.** Minimizing an untitled Slate popup crashed a Hayba scratch host with a SetWindowRgn assert (11-09, hayba lane). Any script that minimizes, moves or closes editor windows must match on a non-empty title.
- **No Python access to Blueprint delegate properties.** No `get_editor_property` on a multicast delegate (for example a button's OnClicked/OnSandClicked), and no broadcast from Python. At 22:10 on 11-09 a QA driver read WBP_Encounter's Btn_NextTarget.OnSandClicked during PIE. 3.4 s later the editor crashed with an access violation in PythonScriptPlugin/python311, with the PSP hotfix active. To "click" a button, call the widget's own bound handler event while the button is visible and enabled.
- **Builders clear only what they own.** A rebuild that wipes every notify track, socket, tag or component on an asset silently deletes other lanes' work. `build_montages.py` did this and dropped AN_FoA_InteractionContact from all five interaction montages, so every real-E montage interaction stopped committing (found 11-09 22:40). Remove only the tracks or items your script created, by name, and keep reruns idempotent (no duplicate events on a second run).
- **`editor_lock.py release <lane>` frees EVERYTHING that lane holds** (release_all plus a forced scan), including a parent run's EXCLUSIVE. Call it only at the very end of a top-level burst, never from a step nested inside another hold of the same lane. ue_remote itself releases only its own token. Restart 8 returns real lease tokens (checked 22:55: acquire and lease_status show `lease-<salt>-<seq>`), so the token-guessing code in hayba_call/editor_lock no longer runs. Before sending input, a long burst should confirm its hold with `lease_status` (UI's sweep_intro.py does this).
- **Never hold a Python delegate wrapper across frames or past PIE.** PythonScriptPlugin nulls object wrappers on GC but NOT delegate wrappers. A stale delegate still points into the destroyed widget, and touching it later reads freed memory (hayba lane red test 11-09, matching QA's 22:10 crash). Call the owning widget's handler event instead.
- **`blueprint_graph_batch` is not atomic.** If op N fails, ops before it stay applied, and the Blueprint can still compile 0/0 and save a half-wired graph (WBP_Encounter 22:55 dead-ended RefreshBattlePresentation). Before sending a batch, check every variable, pin and node it reads. After a failed batch, remove the ops that did apply, or finish them, before compiling and saving.
- **Props the player carries or stands next to must ignore Pawn.** BP_Phone's mesh blocked Pawn, so the capsule stepped up onto its own phone (QA's 1.7 m "boot carry" and the bed climb). Give carried and small props collision that ignores Pawn and Camera, keeps Visibility for interaction traces, and sets CanCharacterStepUpOn=No.
- **Proof drivers never touch the player's save.** Any PIE driver that runs game flow (beats, Restart Day, FailDay, rollover, equips) must first call `GI_FoA.SetProofProgressContext('FoA_QA_Play', ...)`, as Tools/Unreal/gameplay/pie_play.py does, so progress goes to the QA slot. On 11-10 at 00:13 a story Restart Day proof advanced the user's FoA.sav from the reset Day 18 to Day 20. It's backed up in Saved/SaveGames/_backup and was removed so the user's next run starts fresh.
- **SoundConcurrency assets made by script: turn platform scaling off.** UE 5.8's SoundConcurrencyFactory creates them with `enable_max_count_platform_scaling = True` and `PlatformMaxCount = 16`, and then GetMaxCount ignores MaxCount. Every cap horror made on 11-09 was really 16, and QA heard 4-10 stacked sand bursts. Set `enable_max_count_platform_scaling = False` (and PlatformMaxCount to the intended value), then read it back.
- **Python can't read `UserWidget.WidgetTree`** ("protected and cannot be read"), so a text check that walks a widget's tree silently finds nothing and can never fail (QA's HUD and banner checks, 11-10). Find live Text/RichText through the object iterator, keep those whose outer chain reaches the user widget, and prove the check with a positive control (it must see text you know is on screen) before trusting a clean result.
- **Class edits don't reach placed actors' overridden components.** A placed instance keeps its own per-instance component overrides (collision, custom depth, PP settings, widget size). PIE copies the editor actor and doesn't re-run the class's intent over those overrides. This hit BP_ViewFill (PP settings, 11-10) and Phone_Nightstand (screen stencil, collision, material). For settings that must hold, apply them in BeginPlay (as BP_Phone.ApplyScreen does), or reset the instance overrides and verify in PIE, not in the class defaults.
- **In PIE, never edit the pawn's or its components' properties with change notification.** A notified `set_editor_property` on a PIE actor re-runs its construction script. On BP_FoAPlayer that rebuilds FollowCamera on its template parent (the boom), and AttachFirstPersonCamera doesn't run again, so every later frame comes from the wrong camera (anim, 11-10). Pass `notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER`, or call the Blueprint's own setter function.
- **Never leave a Blueprint that fails to compile between lease windows** (11-10: a half-built BPFL_ItemInspect, loaded and dirty, made Hayba refuse every lane's PIE with HCR-PIE-001). Before releasing the lease, compile and save; if the body is not done, stub or disconnect it so it compiles. In a Blueprint Function Library, a call that needs a world (GetActorOfClass, SpawnActor) needs an Object input named WorldContextObject wired to its World Context Object pin.
- **A light-channel (or any lighting) audit must read every source, not just the level.** On 11-10 the face lane reported that no light used channel 1 or 2, and that was wrong. A level sweep never sees these:
  - Blueprint component templates: BP_Garment.ContactFill is on channel 1 only.
  - Sequence spawnables: LS_WakeUp's L6_SandRim and L6_Dial.
  - Channels changed at runtime: the jumpscare light.

  `EditorActorSubsystem.get_all_level_actors` itself is not the gap. Re-checked at 19:45, it returns every actor that `GameplayStatics.get_all_actors_of_class(<editor world>, Actor)` returns except 7 engine system actors: WorldSettings, the default Brush, DefaultPhysicsVolume, AbstractNavData, BuoyancyManager, GameplayDebuggerPlayerManager and one bare Actor. No sublevel or data layer is involved, and the sweep does include SandRim_Light (channel 2 only). Why the 19:21 read missed SandRim_Light is unexplained; the likeliest cause is that its in-memory channels changed between the two reads. Audit level actors, Blueprint templates and sequence spawnables, then confirm with a PIE dump.

## Map switches (Level 2 test maps; added 2026-11-10, world lane)
The shared editor has one open map, and every lane's actor scripts target it. Opening another map is therefore an editor-wide event. `load_level` drops the bedroom's unsaved actor edits, and a blind `save_level` commits another lane's half-done ones. Do it only like this; `Tools/Splats/l2_dream_switch.sh` is the reference:
1. **Prepare everything offline first** (imports, materials, the map's build script), so the hold contains only the switch: open, build or shoot, save, reopen.
2. **One EXCLUSIVE hold** (`editor_lock.py acquire <lane>`, PIE window, 60 s or less) for the whole switch, including the return. Two short holds (build, then shots) are better than one long one.
3. **Dirty check before switching.** Read `editor_get_state` dirty_packages. If any bedroom package (the map or its external actors) is dirty, do not save and do not switch: release, then report the dirty packages to the coordinator, who finds the owner. Save it yourself only if every dirty change is yours.
4. **Count, switch, return, verify.** Record the bedroom's actor count, Encounter_T8, a BP_BeatDirector and a PlayerStart before you switch. Reopen L_Tutorial_Bedroom in the same hold, check the same four values, then release. Every exit path (error, timeout, signal) must reopen the bedroom before it releases.
5. **Level 2 maps live in /Game/FoA/Level2/Maps.** Give them `GameModeBase` in World Settings, so the FoA flow (front end, beats, saves) doesn't start in a test PIE. Save them with `save_current_level` inside the hold (they are not the shared map, so `editor_lock.py save_level` doesn't apply). Nothing in a Level 2 switch touches Level 1 maps.
- **The user's playtest is sacred: no lane does anything in the editor while the user plays.** On 11-10 at 17:20 a lane was granted EXCLUSIVE during the user's PIE; its proof run restarted his session and then ended it. Now `editor_lock.acquire` refuses every lease while PIE runs without a lane's EXCLUSIVE (`user_playing()`), and the coordinator also sets the MAINTENANCE hold. Never call Hayba or ue_remote outside a lease, and never start or stop PIE you did not start inside your own EXCLUSIVE.
