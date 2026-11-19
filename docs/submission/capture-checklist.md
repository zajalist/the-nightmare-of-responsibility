# FoA: capture checklist

Capture as you build so the report and the video assemble themselves. The IDs below are referenced from `report-outline.md` (slides) and `demo-shot-list.md` (shots).

How to capture:

- Save captures in `P:\FoA-Assets\capture\`, outside the repo because they are large. Name them `MMDD_<ID>_<subject>_<state>.png`, for example `1109_B04_clock_066.png`.
- Screenshots are 1920×1080 PNG. Recordings are OBS at 1080p60.
- Take every before/after pair from the same camera: a `Shot_*` CameraActor or a saved viewport bookmark.
- Add one line per capture to `capture\log.csv` (date, ID, file, note). Dated captures are your evidence of the process.
- The editor is also recorded continuously at 5 fps by `Tools/Capture/record_editor.sh` into `P:\FoA-Devlog\recordings\`. The devlog (`P:\FoA-Devlog\index.html`) cuts clips from those recordings.

When to capture:

- **Now:** Nov 5–7.
- **When built:** as each feature lands.
- **Freeze:** Nov 17.
- **Submit:** Nov 18–19.

Already on disk, so there's nothing to recapture:

- Storyboard frames F01–F15 are in `P:\FoA-Assets\storyboard\frames`, and moods A–E are in `P:\FoA-Assets\storyboard\moods`. All are concepts made with Canva AI.
- Character turnarounds v1 and v2 are in `P:\FoA-Assets\character\turnaround`.
- Raw Lux3D outputs are in `P:\FoA-Assets\lux3d\<item>\` and `P:\FoA-Assets\character\lux3d\`. Their task IDs are in `_state.json` and `tasks.json`.
- The bedroom v3 top-down shot is `P:\FoA\Saved\Screenshots\WindowsEditor\FoA_Shot_TopDown.png`. It is the earliest dated in-engine frame, so keep it for B02.

## 1. Lux3D generations (L)

This is a snapshot from Nov 5. Refresh it from `_state.json` at the freeze.

| Kind | Items (task ID) |
|---|---|
| G1 mesh, faceCount 30000 | Bedroom door 4725669 · Door key 4725680 · Bedding 4725687 · Wire hanger 4725694 · The Shirt 4725759 · Suit 4725770 · The Nightmare 4725792 · Window frame 4725887 · Curtains 4725892 · Rug 4725898 · Ceiling light 4725955 · Radiator 4725977 · Picture frame 4726001 · Heavy Hood 4726065 · Strap Harness 4726070 · Faceless Mask 4726076 · Sand Door 4726213 · Bedside Book Stack 4726233 · Glass Of Water 4726238 · Coat Hook Rail 4726271 |
| G1-Turbo PLY splat | Sand hand 4725644 · The night mare 4725817 · Fear of adulthood (clock) 4726033 · Fear of adulthood (briefcase) 4726056 · Sand Hourglass 4726151 · Melting Calendar 4726172 · Unpaid Bills 4726175 · Necktie Serpent 4726187 · Sand Crow 4726206 · Alarm Clock Splat 4726209 |
| Image-to-3D G1, GLB + PLY | The Nightmare from turnaround v1, 4725873 |
| In progress | Character v3 (Lux3D direct mesh, several variants) |
| Not run | Sand piles (the procedural `SM_SandMound` meshes stand in for them) · Shoe, Single bed, Wardrobe, Chest of drawers, Writing desk, Desk lamp, Chair, Screwdriver (all covered by Poly Haven) |

- [ ] **L01 (now): batch process.** Screenshot the prompt table, the output of `lux3d_batch.py --dry-run`, and a terminal from a real batch run that shows task IDs and polling. *(Slide 6)*
- [ ] **L02 (now, for each shipped asset): stills and turntables.**
  - Meshes: one still on a neutral grey background, with the same light and three-quarter angle for every asset, plus a wireframe version with the triangle count.
  - Splats: a still from a splat viewer at the same angle, with the splat count.
  - Every asset: a 4-second turntable, for the asset wall in shot 5e and on slide 6.
  - Check whether Aholo Viewer (Manycore's 3DGS viewer) opens local PLY files. If it does, use it, because that puts a second Manycore tool on screen.

  *(Slides 6–11, shots 5b and 5e)*
- [ ] **L03 (every new run): timings.** Note when each task was created and when it finished. `_state.json` has no timestamps and the docs give no typical durations, so these notes are your only timing evidence. The only timing measured so far: image-to-3D task 4725873 took 5 min 43 s. *(Slides 6 and 9)*
- [ ] **L04 (now): iteration sets.** Lay out each set side by side at one angle:
  - The character: turnaround v1 → 4725873 → 4725792 → turnaround v2 → garments 4726065, 4726070 and 4726076 → v3 direct-mesh variants.
  - The clock: 4726033 vs 4726209.
  - The mound object: the clock vs the briefcase (4726056).

  *(Slides 9 and 10)*
- [ ] **L05 (when run): Lux3D post-processing.** Capture before and after for each, and record the task ID:
  - Retopology: wireframes and face counts, compared with the targets in the prompt table.
  - Articulation on the door: a clip of the hinge working.
  - Part splitting, if you use it.

  *(Slides 6, 7 and 10)*
- [ ] **L06 (optional, to run): bedding splat.** Run the bedding prompt on G1-Turbo with `outputFormat ["ply"]` to fill the splat panel on slide 7. *(Slide 7)*
- [ ] **L07 (freeze): asset census.** Count the placed actors in `L_Tutorial_Bedroom`, grouped by source path: `/Game/FoA/Lux3D`, the splat meshes, `/Game/FoA/Props` and `/Game/FoA/Procedural`. Use a Hayba query or the editor's Statistics window. *(Slide 6)*

## 2. Before and after (B)

- [ ] **B01 (as each beat is built): concept vs in-engine.** Pair each storyboard frame (F03–F08, moods C and E) with an in-engine still from a camera set to the same framing. *(Slides 4 and 5)*
- [ ] **B02 (now, then at each milestone): bedroom evolution.** `Tools/Unreal/shoot_live.py` shoots the four cameras `Shot_ThirdPerson`, `Shot_Wide`, `Shot_Window` and `Shot_TopDown`. Take a set at each stage: v3 on Nov 5, props dressed, after the lighting pass, final. *(Slides 5 and 12)*
- [ ] **B03 (when built): the look stack.** From one camera, change one thing at a time: post-process off (raw color) → split-toned mono → add ink contrast → add light shafts → add time-shift echoes → `ColorReveal` at 1. *(Slide 12)*
- [ ] **B04 (when built): the clock materializing on the mound.** Stills at 0, 33, 66 and 100 %, plus wireframe vs shaded. *(Slides 1, 2 and 8)*
- [ ] **B05 (when built): the character.** Each version of the character → in the room. Add a walk-cycle clip that shows whether the garments clip. *(Slide 9)*
- [ ] **B06 (now): the bed.** `old_bed_frame` on its own, then with the Lux3D bedding, with the monochrome post-process on. *(Slide 7)*
- [ ] **B07 (freeze): scalability.** The same frame at your shipped preset and at Epic. In stock UE5 scalability, Lumen GI and reflections are allowed only at High and Epic. Check what 5.8 does at your low-end preset and show the honest result. *(Slide 13)*

## 3. Editor graphs (G)

For each graph, capture the whole graph at a zoom where every comment-box title is legible at 1920×1080. Then capture one crop per comment box. `Tools/Capture/capture_window.ps1` screenshots the editor window into `P:\FoA\Saved\GraphShots\`.

- [ ] **G01 (when built): `M_LightShaft`.** The light shafts are additive, unlit cards. Each factor gets its own labeled comment box, matching the user's reference layout: "Object Position Random - Start Time", "Texture", "Gradient Falloff", "Depth Fade", "CameraDepthFade", "Fresnel". Also capture `T_Lines` in the Texture Editor, with R, G and B shown one at a time. `T_Lines` is 128×1024, generated by `Tools/Textures/make_light_lines.py`. *(Slide 12)*
- [ ] **G02 (when built): the splat-mesh material.** One comment box each for:
  - vertex color → base color
  - vertex alpha → opacity
  - Gaussian falloff from the quad UVs
  - the flow/curl-noise motion
  - the dissolve mask (noise, height, threshold parameter)
  - depth fade

  *(Slide 8)*
- [ ] **G03 (now): the dream post-process.** `M_PP_DreamMono`, the new dream stack, and `MPC_Dream` (ShadowTint, HighlightTint, ColorReveal, plus the echo and glitch scalars). *(Slide 12)*
- [ ] **G04 (when built): echoes and glitch.** The time-shift blur and echo setup, and the horizontal tear glitch. *(Slide 12)*
- [ ] **G05 (when built): gameplay logic.** One readable screenshot each of interaction, the dream director (moving the door), the encounter's turn logic and the day rollover. *(Slides 5 and 14)*
- [ ] **G06 (when built): payoff Sequencer.** The T9 Sequencer with the `ColorReveal` curve visible. *(Slide 12 and shot 14)*
- [ ] **G07 (when built): splat-mesh converter output.** For every splat asset, record the splats in, the quads kept, the MB out and the time taken. The 11 raw PLYs total 1.19 GB, so this table is your proof that the game fits the budget. *(Slides 11 and 13)*
- [ ] **G08 (optional): Multi-User session.** Both of you working in the level at once, as evidence of how a team of two built it. *(Slide 15)*

## 4. Profiler stats (P)

Shipping builds compile stats out. Measure on a Development or Test build, and quote the size of the Shipping build.

- [ ] **P00 (now): the reference PC.** Pick the weakest PC you can get, and take a dxdiag or Task Manager screenshot showing its CPU, GPU, VRAM, RAM and driver. Every performance number in the report names this PC. Agree on the fps target with your teammate. *(Slide 13)*
- [ ] **P01 (freeze): build size.** The Shipping build's folder properties showing its size on disk, plus the size of the zipped download. The target is under 1 GB. *(Slides 2 and 13, shot 12c)*
- [ ] **P02 (freeze): size breakdown.** Use Size Map and the Asset Audit window, and group the results into Lux3D meshes, splat meshes, Poly Haven, textures, audio and engine. *(Slide 13)*
- [ ] **P03 (freeze, on P00): frame rate.** `stat fps` and `stat unit` at 1080p and at 720p, on the preset you ship, in the heaviest view. *(Slides 2 and 13, shot 12c)*
- [ ] **P04 (freeze, on P00): Unreal Insights trace.**
  1. Start `UnrealInsights.exe`.
  2. Launch the Development build with `-trace=default,gpu -tracehost=localhost -statnamedevents`.
  3. Play the same 60-second route every time.
  4. Screenshot the frame-time track with the worst spike labeled.
  5. Note the average fps and the worst frame.

  *(Slide 13)*
- [ ] **P05 (freeze): GPU cost.** `stat gpu` in the heaviest view, with light shafts, a splat dissolve and echoes all on screen. *(Slide 13)*
- [ ] **P06 (freeze): draw calls.** `stat rhi` (draw calls and triangles) in the same view. *(Slide 13)*
- [ ] **P07 (when splats and shafts exist): overdraw.** The Quad Overdraw and Shader Complexity view modes, on a splat dissolve and on the light shafts. Translucent quads are where overdraw will hurt. *(Slide 13)*
- [ ] **P08 (freeze): memory.** `memreport -full`, which writes to `Saved/Profiling/MemReports`. Record the total texture memory. *(Slide 13)*
- [ ] **P09 (freeze, on P00): stability.** Record one uninterrupted playthrough of everything that ships. It proves stability and also gives you gameplay takes. *(Slide 14)*

## 5. Video takes (V) and submission (S)

- [ ] **V01–V14 (as each beat is built): video takes.** One folder per shot in `demo-shot-list.md`, with 2–3 takes each. Record in real time from the packaged Development build, with no debug text except in shot 12c.
- [ ] **S01 (submit): records.** Screenshot the live X post, the ModelScope page (logged out) and the confirmation on the hackathon's "My Submission" page.
