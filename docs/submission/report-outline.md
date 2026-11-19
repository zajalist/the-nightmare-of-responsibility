# FoA – The Nightmare of Responsibility: report outline

15 slides, 16:9, exported to PDF (keep the PPT as well). The deadline is Nov 19 2026 at 06:00 EST (11:00 UTC). Capture IDs (L, B, G, P, V) refer to `capture-checklist.md`, and shot numbers refer to `demo-shot-list.md`.

Rules for every slide:

- Label every image *in-engine*, *Lux3D output*, *editor* or *concept (Canva AI)*. A concept frame must never pass for the game, because completeness is judged on whether "the submitted materials accurately reflect the project".
- Numbers come from captures. Anything marked **to build**, **to run** (a Lux3D task not run yet) or **to capture** stays off the slides until it exists.
- Slide 2 is the slide judges read in ten seconds. Write it first, then reuse its three lines in the video title card and the X posts.

State on Nov 5 at 16:06 ET:

- **Lux3D:** 29 text-to-3D tasks (26 done, 3 running) and 1 image-to-3D task.
- **Built:** bedroom level v3, with the monochrome post-process (`M_PP_DreamMono` + `MPC_Dream`) and black-sand mounds.
- **Imported:** the Poly Haven furniture and 4 Lux3D props (bedding, door, key, hanger).
- **To build:** gameplay, the character, splat meshes, light shafts, time-shift blur, audio and a packaged build.

---

## 1 · FoA – The Nightmare of Responsibility

- **Message:** A third-person puzzle game about the scariest monster of all: an ordinary morning. It takes place in a black-and-white dream made of black sand, and every dream object in it comes from Aholo Lux3D.
- **Visual:** One full-bleed in-engine frame. The hooded figure stands in a light shaft while a Lux3D clock forms out of the black-sand mound behind it (B04 at 50 %). Footer: video link and QR code, then "Team of 2 · Unreal Engine 5.8 · Aholo Lux3D". The character, light shafts and splat material are all **to build**.
- **Serves:** First impression for Fun (25 %) and Use of Manycore tools (30 %).

## 2 · Why it's worth trying

- **Message:** Three lines, nothing else:
  1. Getting dressed is a boss fight. Everyday chores, filmed sincerely.
  2. Lux3D objects pour out of black sand and collapse back into it.
  3. A room full of AI-generated 3D that runs on a low-end PC in under 1 GB. *Keep this line only if P01 and P03 prove it.*
- **Visual:** Three in-engine stills or GIFs side by side: the Shirt encounter (V-take of shot 10), the clock materializing (B04), and the packaged build running with its fps and size visible (P01, P03).
- **Serves:** Fun 25, Innovation 20, Completeness 20.

## 3 · The idea

- **Message:** In a dream, absurd things feel deadly serious. Every obstacle starts as plausible bad luck and slowly turns into dream logic. Small wins are staged like action-movie climaxes.
- **Visual:** On the left, a screenshot of the concept board's escalation strip ("The level at a glance": Plausible → Suspicious → Open → Payoff). On the right, Fuseli's *The Nightmare* (1781, public domain), the source of the black-sand horse. Below them, one line each on the other two references: Twelve Minutes (the loop) and Coraline (the comfortable trap).
- **Serves:** Innovation 20. This slide starts the idea → result story the brief asks for.

## 4 · The look: five moods, one style

- **Message:** Photoreal black and white is the base, with inked graphic contrast and smoke-and-sand tendrils on top. The game is fully monochrome and the sand is black. Color appears only when you earn it.
- **Visual:** Top row: moods A, C, D and E from `P:\FoA-Assets\storyboard\moods`, labeled *concept (Canva AI)* and tagged "A contrast + C base + D tendrils; E for payoffs only". Bottom row: the same bedroom in-engine from `Shot_Wide` (B01).
- **Serves:** Innovation 20, Completeness 20.

## 5 · How you play: one ordinary morning

- **Message:** The goal is to get dressed and leave the house. You can look, take, use and combine. If you fail, the day rolls over: the house resets, but what you learned stays.
- **Visual:** A beat strip from T0 to T10. Each cell shows an in-engine still if the beat ships (V-takes). If it doesn't ship, the cell shows the storyboard frame greyed out and labeled "concept, not in build". Under each cell goes one line saying what the figure wants and what it gets.
- **Serves:** Fun 25, Completeness 20.

## 6 · Lux3D under every dream object

- **Message:** N Lux3D generations, M of them placed in the shipped level: dream and sand objects, set dressing, story props and the player's garments. The realistic furniture is CC0 Poly Haven, and the room shell is built in-engine.
- **Visual:**
  - (a) A pipeline diagram: the prompt table (`docs/lux3d-bedroom-prompts.md`) → `Tools/Lux3D/lux3d_batch.py` → the Lux3D API (G1 mesh, G1-Turbo splat, image-to-3D; add retopology and articulation only if you run them) → GLB or PLY → Unreal import or the splat-mesh bake → the level.
  - (b) A contact sheet of every Lux3D output, each with its task ID (L02).
  - (c) A bar chart of placed actors by source (L07).
- **Serves:** Use of Manycore tools 30.

## 7 · Pipeline A, mesh: the bed linen

- **Message:** One prompt, one Lux3D task, one dressed bed: the Lux3D bedding sits on a CC0 iron bed frame.
- **Visual:** Four panels side by side, all from the same three-quarter angle:
  1. The prompt text (the Bedding row) and its task: 4725687, G1, faceCount 30000.
  2. The splat (**to run**). The bedding ran on G1 with GLB output only, so no splat exists. Run the same prompt on G1-Turbo with `outputFormat ["ply"]` to fill this panel, or drop the panel.
  3. The raw GLB: 28,356 triangles, two 2048² textures (base color and metallic-roughness), 4.86 MB (L02).
  4. In-engine on `old_bed_frame` with the monochrome post-process on, from `Shot_ThirdPerson` (B06).

  An optional fifth panel shows the retopology wireframe at the ~10k target from the prompts table (**to run**).
- **Serves:** Use of Manycore tools 30, Completeness 20.

## 8 · Pipeline B, splat mesh: the alarm clock

- **Message:** Each Lux3D Gaussian splat becomes a quad in a single static mesh, and the material does the rest: the object pours out of the sand mound and collapses back into it. No particles are involved.
- **Visual:** Five panels:
  1. The prompt: "Fear of adulthood (clock)", task 4726033, G1-Turbo PLY.
  2. The raw splat: 1,175,936 splats, 80 MB (L02).
  3. The baked splat mesh in wireframe, with its quad count and size (G07).
  4. A thumbnail of the material graph (G02).
  5. The object materializing in-game at 0 %, 33 %, 66 % and 100 % (B04).

  Panels 3 to 5 are **to build**.
- **Serves:** Innovation 20, Use of Manycore tools 30.

---

## Asset iteration (slides 9–11)

## 9 · Iteration: the protagonist

- **Message:** We generated the whole character with Lux3D twice, then switched to Lux3D garments on Unreal's mannequin for reliable animation. *Confirm with the team that this is the real reason before you write it.*
- **Visual:** Five columns:
  1. Turnaround v1, four views (concept: `P:\FoA-Assets\character\turnaround\front.png`, `side.png`, `back.png`, `three_quarter.png`).
  2. Lux3D image-to-3D G1, task 4725873. Those four views went in. Out came 28,680 triangles and a 388,768-splat PLY, in 5 min 43 s (L02).
  3. Lux3D text-to-3D "The Nightmare", task 4725792: 28,602 triangles (L02).
  4. Turnaround v2, with a heavier hood, a strap harness and an angular mask (concept: the `*_v2.png` files).
  5. The final version in-engine and mid-walk: Manny wearing Heavy Hood (4726065), Strap Harness (4726070) and Faceless Mask (4726076) (B05). The skinning is **to build**.
- **Serves:** Use of Manycore tools 30 (this is the "comparisons of key asset iterations" the brief asks for), Completeness 20.

## 10 · Iteration: props across versions

- **Message:** What we changed between Lux3D runs, and why.
- **Visual:** A grid with one row per asset. Each cell holds a still, the prompt change, the task ID and the triangle or splat count.
  - **Alarm clock:** "Fear of adulthood (clock)" 4726033 (1,175,936 splats) vs "Alarm Clock Splat" 4726209 (827,600 splats; the prompt adds "small cracks"). Show which one you kept.
  - **Mound object:** the clock (4726033) vs the briefcase (4726056, 1,950,992 splats, 133 MB), compared on how well each reads as black sand.
  - **Bed:** "Single bed" (frame and bedding in one prompt) was never run and was dropped for the CC0 frame. It became "Bedding" (4725687) on `old_bed_frame`.
  - **Door:** raw G1 (4725669) → articulation hinge (**to run**) → in-game.
  - **Face budget:** the default 300,000 faces vs our 30,000 (actual 28k–30k). Include this row only if you pay for one 300k comparison run.
- **Serves:** Use of Manycore tools 30.

## 11 · Iteration: from raw splats to shippable ones

- **Message:** Raw Lux3D splats run from 0.4 to 4.5 million per object, and the 11 PLYs on disk total 1.19 GB, which is more than the whole game budget. We cut each one to N quads and kept the silhouette.
- **Visual:** The night mare (task 4725817: 995,808 splats, 68 MB) at four decimation levels from the same camera: 100 %, 25 %, 10 % and the shipped level. Label each with its quad count and size, and add an in-game still. Beside them, a small chart compares raw MB with shipped MB for every splat asset. **To build** (G07).
- **Fact to state:** The Lux3D PLYs carry color as degree-0 SH only (`f_dc_0..2`, no `f_rest`; checked in the headers on Nov 5). Each quad therefore stores one flat color, and there is no source data for view-dependent SH.
- **Serves:** Innovation 20, Completeness 20.

## 12 · The look, in-engine

- **Message:** Three cheap tricks sell the dream on a low-end PC: banded light shafts, split-toned monochrome and time-shift echoes.
- **Visual:** Three before/after pairs, all from one camera (B03):
  - Light shafts off and on, with the `M_LightShaft` graph and its labeled comment boxes beside them (G01).
  - The post-process off and on: color → split-toned mono, using `MPC_Dream` ShadowTint and HighlightTint (G03).
  - Time-shift echoes off and on during T7.
- **Serves:** Innovation 20.

## 13 · Budget and low-end performance

- **Message:** "Under 1 GB, X fps on a low-end PC", using only measured numbers.
- **Visual:** The table below, plus a bar chart of raw vs shipped MB per category.

| Metric | Known on Nov 5 | Capture |
|---|---|---|
| Packaged Shipping build | not packaged yet | P01 |
| Size by category: Lux3D meshes, splat meshes, Poly Haven, textures, audio, engine | — | P02 |
| Lux3D G1 mesh, raw | 28k–30k triangles; 2 × 2048² PNG; 3.1–8.9 MB per GLB | P02: shipped size and texture resolution |
| Lux3D splats, raw | 11 PLYs, 17.5 M splats, 1.19 GB (0.39 M–4.5 M splats, 26–307 MB each) | G07: quads and MB after the bake |
| Poly Haven, raw | 57.5 MB (1k glTF models, 2k textures) | P02 |
| Uncooked `Content` folder | 215 MB (includes template content; not the shipped size) | — |
| Reference low-end PC | not picked yet | P00 |
| fps and frame time at 1080p and 720p, shipped preset | — | P03, P04 |
| GPU ms in the heaviest view (base pass, translucency, post) | — | P05 |
| Draw calls, triangles, memory | — | P06, P08 |

- **Serves:** Completeness 20 ("the demo runs reliably"), and Use of Manycore tools 30, because it shows that Lux3D assets are shippable.

## 14 · What's in the build, and what isn't

- **Message:** What you can play: the tutorial morning, about N minutes. Then the honest list of what is partial, what was cut and the known issues.
- **Visual:**
  - A beat table with three columns: beat, status (playable, partial or cut), and the Lux3D assets it uses.
  - The system requirements, download size and how to run the build.
  - A short "changed since the concept board" list:
    - Niagara sand became splat meshes.
    - The Lux3D-rigged protagonist became Manny wearing Lux3D garments.
    - Lux3D furniture became Poly Haven furniture.
    - The YaGS splat-renderer spike isn't needed, because splats render as meshes.
    - Level 1: *state what shipped.*
- **Serves:** Completeness 20.

## 15 · Credits and links

- **Message:** Made by a team of two in two weeks with Aholo Lux3D and Unreal Engine 5.8.
- **Visual:**
  - **Links:** the demo video, the build download, the source code, the ModelScope page, the X post, the storyboard (https://claude.ai/artifact/PLRgtmHY7UusSvT4R8B5Rr) and the concept board (https://claude.ai/artifact/9AHdPVWkh8ar5ZV7FSbnJg).
  - **Credits:** Aholo Lux3D (with the task count), each Poly Haven CC0 asset by name, Unreal Engine 5.8's Third Person template and mannequin, Canva AI (concept frames only), and the audio with its licenses (**to source**).
- **Check:** Artifacts start private. Open both artifact links while logged out. If they don't load, share them, or export them to PDF and attach the PDFs.
- **Serves:** Completeness 20, Reach 5.
