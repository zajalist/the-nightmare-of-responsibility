# Hayba lane handoff (restart 11 on UE 5.9 installed), 2026-11-11

## Codex recovery, 2026-11-11
- The original UE 5.9 build completed successfully after Claude hit its usage limit. Codex finished the MCP build, live tests and installation.
- Installed from `O:\Projects\SoftwareIncubator\Saved\hayba-restart11-ue59-bin\install.ps1 -WithMcp`; DLL, PDB, engine BuildId and MCP distribution hashes verified. Previous files are `*.r10ue59` and `dist.r10ue59`.
- Source is `O:\Projects\SoftwareIncubator\hayba-bpfl`, branch `integrate/restart11-ue59`, plus an uncommitted capture fix: UE 5.9 requires the capture component visible and not hidden-in-game. Its owning helper actor stays hidden. The user's asset-delete overlay remains preserved in the built copies and untouched in the original checkout.
- MCP suite: 235 files, 2809 tests passed, 1 skipped. Fresh scratch-editor gates passed for graph batching, graph paging beyond 50, object/class variables, editor/PIE capture, actor_find, PIE input with Alt held, function-library compilation, strict parameters/leases, component attachment, UI TCP wrappers, forced asset save, spawn nodes and background audio.
- Evidence: `Saved\hayba-lane-host-59\codex_*.log` and `build_codex_capture.log` under `O:\Projects\SoftwareIncubator`; MCP log is `Saved\hayba-restart11-mcp\mcp-tools\hayba-mcp\test_codex.log`.
- Start a fresh Claude/Codex MCP connection to load the installed server distribution. Do not rebuild Hayba from the original checkout's older source: use the integration worktree/build host above or the missing-command regression returns.
- No commit or push performed. Historical notes below describe earlier installs.

Restart 7 (`integrate/restart7` d4975653) is installed in FoA since 14:25 on 2026-11-09. Restart 8 is built and gated but not installed.

## Branches (pushed, never main)
- `feat/foa-tool-gaps` at a9b08448. On top of restart 7 it adds:
  - 10314d17: UI slot values parse the UE forms and report what doesn't parse in unknown_slot_props; `input_key` nodes; Text pin literals.
  - a9b08448: audio_active_sounds reads the PIE world's audio device during PIE (`world: auto|pie|editor`).
- `integrate/restart8` at 2621024e: restart 7 merged with 10314d17 (dd36a871), then with a9b08448.

## Built and passing
- DLL: `O:\Projects\SoftwareIncubator\Saved\hayba-restart8-bin` (SHA256SUMS.txt beside it). It's built from integrate/restart8 plus the user's uncommitted asset_delete overlay. The overlay is applied to the build copy only.
  - dll SHA256 `A3688B7FB0D3FE09AC1353956D69955C0456F9CE9C62F62A1855F2B14FD1B45F`
  - pdb SHA256 `FFFA105DFEBC6FB1D3AD40A289C403512F36B2A3A3C19DB884C2AE9D0D3438EB`
  - UnrealEditor.modules is the same as restart 7's.
- Live gate `Saved\hayba-lane-host\Tools\test_restart8.py`. It runs on a scratch host pinned to 52401, minimized, `-unattended`, with a watcher that acts on its own PID only.
  - PASSED on restart 8, on a fresh host (`Saved\hayba-lane-host\r8_green_restart8.log`).
  - FAILED on restart 7 (`r8_red_restart7.log`):
    - input_key is an unknown node type;
    - the Text pin doesn't verify;
    - the slot reads back Fill / 0 padding / Automatic;
    - "Sideways" is reported as applied;
    - audio_active_sounds lists nothing during PIE;
    - world "pie" isn't refused without PIE.
  - During PIE the PIE world has its own audio device (id 2 or 4, against 1 for the editor), as in FoA. So the red audio result is a real failure, not a shared-device artifact.
- TS contract tests `ui-slot-values-contract.test.ts` and `audio-active-sounds-world-contract.test.ts`: 8/8 fail on restart-7 sources (`r8_ts_red_restart7.log`) and 8/8 pass on restart 8 (`r8_ts_green_restart8.log`).
- MCP dist: `Saved\hayba-restart8-mcp\mcp-tools\hayba-mcp\dist`. It's restart 8 plus the TS overlay: 2117 files, manifest `0126AC2E073A4CAFC9DA6646B1CDB7C28AC19B9CECA19A26DC96EB809EEBFA87`.
  - All tests pass. The first full run had 4 tests time out while the machine was paging; they pass on a rerun (`vitest_r8_rerun.log`).

## Not installed yet
- The install script is `scratchpad\install_hayba_restart8.ps1`, next to the restart-7 one. It's SHA-pinned and hasn't been run.
- Use `-WithMcp`: audio_active_sounds gained `world`, and the restart-7 dist's strict schema rejects it.

## Next step
Run the install at the next planned FoA restart, then relaunch the MCP servers.

## Caveats
- Scratch-host watchers must leave untitled windows alone. Minimizing an untitled Slate popup (a toast or a menu) trips FWindowsWindow's `SetWindowRgn` assert. That crashed the scratch host once on 2026-11-09 (crash log in its Saved\Crashes). host.py and test_restart8.py now touch titled windows only.
- The first full green run (on the host started right after that crash) saw a non-modal "Message Log" window during PIE. The game thread kept answering. Two later full runs, one of them on a fresh host, opened no window at all.
- Scratch hosts: always `HAYBA_MCP_PORT` 52400 or higher (host.py `--pin`), minimized, `-unattended` for green runs. Kill only your own PIDs. Never touch FoA (52342).

## After restart 8
- Restart 9 is installed in FoA (the coordinator, 2026-11-09 ~23:00). It's `fix/bp-names-pie-guard` a69b0fef: restart 8 plus the freeze fix. It's DLL-only: `Saved\hayba-namesfix-bin`, dll `F6A87B33...`.
  - blueprint_add_function, blueprint_add_variable and blueprint_add_component refuse member-name clashes ([HCR-BP-NAME-001]).
  - editor_start_pie, and python scripts that call editor_request_begin_play or editor_play_simulate, refuse while a loaded Blueprint fails to compile ([HCR-PIE-001]).
  - Gate `Tools\test_names_pie.py`: red on restart 8 (`n9_red_restart8.log`, where the modal opened 3 times) and green on the fix (`n9_green_attended.log`).
- `fix/asset-save-force` 8b5edb1d (on top of a69b0fef): asset_save gains `force: true` and a `skipped_not_dirty` list. It needs the MCP dist swapped, because asset_save's TS schema gained `force`.
  - Gate `Tools\test_asset_save_force.py`: red on restart 9 (`as_red_restart9.log`) and green on the fix (`as_green.log`). Binaries are in `Saved\hayba-assetsave-bin`. Not installed.
  - The finding: editor-Python AnimationLibrary notify edits leave the package clean.
- Restart 10 is installed in FoA (the coordinator ran install_hayba_restart10.ps1 -WithMcp; the editor relaunched 2026-11-10 00:34 on 52342 with the PSP hotfix ok). The installed DLL is `DCD0BC24...` and the dist manifest `362F3AE3...`; the restart-9 binaries are kept as `*.r9` and `dist.r9`.
  - Branch: `integrate/restart10` fa8b8967 (pushed) = a69b0fef + 8b5edb1d (asset_save force) + 700adf05 (`fix/spawn-node-order`) + fa8b8967 (`feat/background-audio-pie-recording`).
  - The background audio fix: an unfocused editor zeroes its volume every tick unless bAllowBackgroundAudio is set, so every PIE recording on an agent's editor was digital silence. `editor_set_background_audio {enabled}` sets it in memory and returns `previous` for restore. `audio_recording_start/stop` take `world: auto|pie|editor` (each PIE session has its own device), and stop reports `peak`, `peak_dbfs`, `rms`, `silent` and a `warning` naming the mute. Gate `Tools\test_background_audio.py` (the minimized host is made unfocused through a 1x1 off-screen sink window): red on 700adf05 (`ba_red_restart10.log`: a silent take, no level in the reply, no tool) and green (`ba_green.log`: the muted take reports peak 0 and silent with the cause, and the tool-on take peaks at 0.25 in both the reply and the WAV).
  - A device with nothing playing renders nothing: a take while no sound plays returns zero samples, and the error now says how many sounds were active.
  - The spawn fix: blueprint_add_node gives nodes their pins before PostPlacedNewNode, as UE's palette spawner does. spawn_actor_from_class had asserted at EdGraphNode.h:586 on every placement. Its class_path is now the class to spawn (concrete Actor classes only; anything else is refused). Red `sp_red_restart9.log` (the SEH guard tripped), green `sp_green.log`.
  - DLL: `Saved\hayba-restart10-bin`, dll `DCD0BC24...`, pdb `F2291A7A...`; .modules is unchanged. The 700adf05 build is kept as `hayba-restart10-bin.v1-700adf05`.
  - MCP dist: `Saved\hayba-restart10-mcp\mcp-tools\hayba-mcp\dist`, 2133 files, manifest `362F3AE3...` (the 700adf05 dist is kept as `hayba-restart10-mcp.v1-700adf05`). The overlay went on like this: user_ts.patch for index.ts (checked identical to restart 7's overlay), and the five untouched files copied from the restart-7 overlay. Vitest: 2476 pass, 1 skipped, 0 fail.
  - Full live gate on the restart-10 DLL (`r10b_test_*.log`): restart 8, names/PIE, asset_save, spawn and background audio all PASSED.
    - The first restart-8 run saw a non-modal "Message Log" window. It came from UE's validate-on-save after blueprint_create, in the scratch host's layout. The rerun on a fresh host passed. The gate now minimizes "Message Log" instead of counting it.
  - Install: `scratchpad\install_hayba_restart10.ps1 -WithMcp`. It's SHA-pinned (DLL, PDB, dist manifest), refuses while any UnrealEditor runs, and keeps `*.r9` and `dist.r9` backups. It hasn't been run.
- Building restart 10's MCP dist: index.ts is one of the six user-overlay TS files, and it changed in both the branch and the overlay. Apply `user_ts.patch` to it instead of copying the restart-7 overlaid file.
- Queued for restart 11, not installed (the coordinator schedules it): `feat/ui-tcp-wrappers` 96531a94, on integrate/restart10 fa8b8967. The 13 ui_* MCP wrappers (ui_set_text_style, ui_set_brush, ui_set_property, ui_set_visibility, ui_set_slot_layout, ui_get_widget_info, ui_search_widgets, ui_move / remove / rename / reparent / duplicate / replace_element) are native commands too, so hayba_call / ue_remote reach them with the MCP parameters. ui_copy_style, ui_set_default_font and ui_validate stay MCP-only (TS composites). It also fixes ui_set_text_style outline and shadow on both paths: they had never applied, because the keys were wrong. Gate `Tools\test_ui_tcp_tools.py`: red `ut_red_restart10.log`, green `ut_green.log`; restart 10's five gates still pass on it. Binaries are in `Saved\hayba-uitcp-bin` (dll `9CA82E6D...`). It needs an MCP dist swap for the TS outline/shadow fix.\n- Also queued for restart 11 (on `fix/bpfl-create`, on top of 96531a94; committed, not pushed until the live gates pass): ef59495b blueprint_create makes a BlueprintFunctionLibrary parent BPTYPE_FunctionLibrary (UI's BPFL_ItemInspect); 3ca07211 mutating commands refuse parameters they don't take ([HCR-PARAM-001]; first tranche: editor_start_pie / stop_pie, blueprint_create / add_component / add_variable / add_function, asset_save), and editor_start_pie is refused under another owner's exclusive global lease even with advisory enforcement (story's PIE, 16:51). Contract tests are red on restart 10 and green; live gates `Tools\test_bpfl.py` and `Tools\test_strict_params.py` wait for a quiet machine.\n- Splat runtime spike (`feat/splat-runtime-spike`, plugin `unreal/HaybaSplats`, uncommitted while it is unverified): design and provisional go/no-go in `docs/design/level2/splat_runtime_plugin.md`. GO on memory (16 B per splat, exact). The GPU bench `Tools\test_splat_bench.py` refuses under 5 GB of free RAM and waits for the coordinator's GO (the user was playtesting). The host .uproject now enables HaybaSplats (backup `HaybaLaneHost.uproject.bak`).\n- PSP delegates (QA's 22:10 crash): a delegate wrapper read from a PIE object outlives that object and keeps reading its freed memory (`Tools\test_psp_delegate.py`; on the scratch host, using it after PIE hung the game thread). The fix is the editor-rules rule: never hold delegate wrappers across frames or past PIE. Copy semantics were not shipped.
- Restart 11, more (hayba-bpfl, stacked fix/capture-viewport-actor-find -> feat/render-while-hidden -> fix/policy-and-pie-input; local, pushed after the live gates): 7fa9927d + b4e082a8 every python_run template (all *-py-tools, pcg, introspect) runs without try/with/getattr, so the native policy stops refusing them; the guard test scans every tools source file. 2b10f89b editor_set_render_while_hidden {allow}, held per owner (minimized editor ticks at full rate, not 3 fps). ea5427ad HCR-CONSOLE-001 catches unreal.SystemLibrary.execute_console_command and aliases; editor_cvar_set sets through the native editor_run_console_command. ca008171 editor_pie_* input uses explicit modifiers only (Alt+P teardown, story 18:53) and targets the PIE game viewport by default; new editor_get_keyboard_focus. C++ not yet compiled: the Idle build (MaxParallelActions=1) needs about 2 GB above the 5 GB floor and aborted at 4.8 GB with FoA open; it runs at the closed-editor window. Host Source is already synced (bpfl + user overlay; backup scratchpad host_src_uitcp). Live gates: test_capture_actorfind, test_bpfl, test_strict_params, test_render_while_hidden (host WITHOUT --unattended), test_pie_input_target (holds a real LeftAlt), plus live checks of hasattr-vs-docstring property probes, asset get_tag_value, mesh_get_sockets and seq_transform_keyframe time units (probably keys tick-resolution frames into a display-rate add_key).
- Startup race seen once: a client that connects while the editor is still at frame 0 is dropped after about 9 s ("Client workers stopped"). Retry once the editor ticks.
