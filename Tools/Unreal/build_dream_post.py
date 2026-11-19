"""FoA dream post-process stack (post-process lane), under /Game/FoA/PostProcess. Runs INSIDE the open editor:
  python Tools/Unreal/ue_remote.py Tools/Unreal/build_dream_post.py FOA_STEP=all
Steps (FOA_STEP, comma separated): mpc, functions, materials, volume, bubbles, stats, all.

Two after-tonemapping passes on the unbound volume PP_DreamMono, every intensity driven by MPC_Dream:
  M_PP_DreamMono (priority 0)  GlitchUV > Tear > TimeEcho > InkEdges > MonoTone   (aligned with the scene buffers)
  M_PP_DreamLens (priority 1)  Lens (barrel, edge haze, halation, chroma) > PixelSort > FilmFinish (vignette, grain)
Re-running a step rebuilds the graphs in place (same assets), so the volume and placed actors keep working.
Comment boxes are added once with Hayba's material_add_comment (Python can't reach EditorComments); they survive
rebuilds because node positions are fixed here. `bubbles` turns on their title bubbles.
"""
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import build_vfx as V  # noqa: E402  (graph helpers; importing builds nothing)

B, MEL, EAL = V.B, V.MEL, V.EAL
PP = "/Game/FoA/PostProcess"
FN = PP + "/Functions"
MPC_PATH = PP + "/MPC_Dream"
F1, F2, F3 = V.F1, V.F2, V.F3
log = B.log

# ---------- MPC_Dream: trigger scalars stay scalars (gameplay / Sequencer / settings); look values packed ----------
SCALARS = {
    "HueDrift": 0.0,        # 0..1 across the story: night > dawn > day > dusk
    "EchoStrength": 0.08,   # keep room and character detail readable; story beats can push it to 1+
    "GlitchAmount": 0.0,    # scanline jitter, pixel-sort streaks, chroma spikes
    "MoshAmount": 0.0,      # datamosh macroblocks
    "MoshStart": -1000.0,   # menu datamosh: game time the burst began (BP_DreamDirector, menu mode only); blocks drag 0.5-1.2 s
    "MoshSeed": 0.0,        # menu datamosh: which blocks drag this burst (BP_DreamDirector picks a new one per burst)
    "TearAmount": 0.0,      # horizontal tear on Custom Stencil 2
    "StutterAmount": 0.0,   # frame-slip look; BP_DreamDirector also holds the world with time dilation
    "Breath": 0.5,          # 0 exhale .. 1 inhale (BP_DreamDirector, 4.5 s cycle)
    "ReduceMotion": 0.0,    # accessibility: 1 disables echo, glitch, mosh, tear, stutter, lens breathing, boil, weave
    "InkBoil": 0.0,         # hand-drawn line boil, 0..1 (<= 0.45 px, 2-4 steps a second); raise it in Suspicious / Open beats
    "GateWeave": 0.0,       # optional slow film-gate drift, 0..1 (~0.2 px)
    "Letterbox": 0.0,       # 2.39:1 bars for cinematic beats only (T9, L7), 0..1 slides them in
    "SandFXAmount": 0.8,    # sand-only FX on Custom Stencil 5 (echo, mosh, split, banding, flicker); high by request
    "LookIndex": 0.0,       # look-dev look: 0 A Silver print, 1 B Etched, 2 C Smoke nocturne, 3 D Time slip
    "OpenTier": 0.0,        # 0 Plausible .. 1 Open: lerps the look toward its Open-tier values (BP_DreamDirector.SetTier)
    "FocusDist": 350.0,     # cm, the ink thins out of focus around it (matches the volume's DOF focal distance)
}
VECTORS = {
    "EchoShape": (1.5, 0.6, 0.72, 0.35),   # x frames of motion per ghost, y static slip, z decay per ghost, w ghost gain
    "EchoDir": (0.0, 1.0, 0.0, 0.0),       # screen direction the echoes slip along (xy); vertical by default
    "RetroMix": (0.0, 0.0, 0.0, 0.0),      # T8 battle styles: x pixel art, y dither, z CRT, w glitch wipe (BP_DreamDirector)
    "PlayerPos": (0.0, 0.0, -10000.0, 0.0),  # sand-crawl contract: xyz player feet (world cm), w influence radius (BP_FoAPlayer, 30 Hz)
    "FaceOrigin": (0.0, 0.0, -10000.0, 0.0),  # animated face center; w vertical radius (same30Hz publisher)
    "FaceForward": (0.0, 1.0, 0.0, 3.2),     # front direction; w front-surface half-depth, excludes ears/rear
    "FaceRight": (1.0, 0.0, 0.0, 5.6),       # right direction; w horizontal radius, excludes side hair/ears
    "ShiftStreak": (0.25, 0.0, 0.0, 1.2),   # Hail Mary shift streak: x length, y angle deg (0 vertical), z intensity 0..5, w threshold
    "ShiftStreakFx": (0.0, 1.0, 0.3, 2.0),  # x symmetric, y wrap at the edges, z length jitter, w jitter speed
    "LensLook": (0.08, 0.10, 0.16, 0.08),   # x halation / diffusion, y edge softness, z barrel distortion, w chroma split
    "FilmLook": (0.25, 0.0, 0.0, 0.2),     # x vignette, y shader grain (0: UE film grain does it), z free, w ink contrast
    "InkLook": (0.85, 0.35, 1.0, 0.4),     # x line strength, y shadow hatching, z line weight, w albedo hairlines
    "ShadowTint": (1.04, 1.00, 0.86, 1.0),   # warm split tone, aged paper / lamplight (HueDrift 0 = tutorial)
    "HighlightTint": (1.06, 1.03, 0.90, 1.0),
}


def mpc():
    m = unreal.load_asset(MPC_PATH)
    scalars = list(m.get_editor_property("scalar_parameters"))   # keep existing entries (and their ids)
    vectors = list(m.get_editor_property("vector_parameters"))
    have = {str(p.get_editor_property("parameter_name")) for p in scalars + vectors}
    for name, value in SCALARS.items():
        if name not in have:
            p = unreal.CollectionScalarParameter()
            p.set_editor_property("parameter_name", name)
            p.set_editor_property("default_value", value)
            scalars.append(p)
    for name, v in VECTORS.items():
        if name not in have:
            p = unreal.CollectionVectorParameter()
            p.set_editor_property("parameter_name", name)
            vectors.append(p)
    for p in vectors:  # the look values are this lane's; re-running re-applies them
        name = str(p.get_editor_property("parameter_name"))
        if name in VECTORS:
            p.set_editor_property("default_value", unreal.LinearColor(*VECTORS[name]))
    m.set_editor_property("scalar_parameters", scalars)
    m.set_editor_property("vector_parameters", vectors)
    EAL.save_asset(MPC_PATH, only_if_is_dirty=False)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for p in scalars:  # the editor world's MPC instance keeps values set at runtime: put it back on the defaults
        unreal.MaterialLibrary.set_scalar_parameter_value(world, m, p.get_editor_property("parameter_name"), p.get_editor_property("default_value"))
    for p in vectors:
        unreal.MaterialLibrary.set_vector_parameter_value(world, m, p.get_editor_property("parameter_name"), p.get_editor_property("default_value"))
    log("MPC_Dream", [str(p.get_editor_property("parameter_name")) for p in scalars + vectors])
    return m


# ---------- graph helpers (positions are fixed so Hayba-made comment boxes stay valid across rebuilds) ----------

def put(e, x, y):
    e.set_editor_property("material_expression_editor_x", int(x))
    e.set_editor_property("material_expression_editor_y", int(y))
    return e


def scene_tex(g, sid, x, y):
    return put(V.node(g, unreal.MaterialExpressionSceneTexture, scene_texture_id=B.enum(unreal.SceneTextureId, sid)), x, y)


def mpc_param(g, name, x, y):
    return put(V.node(g, unreal.MaterialExpressionCollectionParameter, collection=unreal.load_asset(MPC_PATH),
                      parameter_name=name), x, y)


SAMPLE = """ClampSceneTextureUV(ViewportUVToSceneTextureUV({uv}, {id}), {id}), {id}"""


def tex(uv, sid, filtered):
    """HLSL: scene texture fetch at a viewport UV (handles editor buffers larger than the view)."""
    return f"SceneTextureLookup(Parameters, {SAMPLE.format(uv=uv, id=sid)}, {'true' if filtered else 'false'})"


def fn_in(f, name, kind, preview, prio):
    v = tuple(preview) if isinstance(preview, tuple) else (preview,)
    pv = unreal.Vector4f()  # 5.8: PreviewValue is FVector4f, whose script constructor takes no arguments
    for axis, value in zip("xyzw", v + (0.0,) * (4 - len(v))):
        pv.set_editor_property(axis, value)
    return V.node(f, unreal.MaterialExpressionFunctionInput, input_name=name, sort_priority=prio,
                  input_type=B.enum(unreal.FunctionInputType, "FUNCTION_INPUT_" + kind),
                  use_preview_value_as_default=True, preview_value=pv)


def fresh_graph(path, cls, factory, **props):
    """Crash safety (editor-rules): close the asset's editor, then delete nodes from a snapshot list
    (delete_all_* skips about half). Comment boxes live outside the expression list, so they survive."""
    a = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if a is None:
        name, folder = path.rsplit("/", 1)[1], path.rsplit("/", 1)[0]
        a = V.AT.create_asset(name, folder, cls, factory)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
    fn = isinstance(a, unreal.MaterialFunction)
    listed = MEL.get_material_function_expressions if fn else MEL.get_material_expressions
    delete = MEL.delete_material_expression_in_function if fn else MEL.delete_material_expression
    for _ in range(500):  # one node per fresh listing: no Python wrapper outlives the node it points to
        exprs = listed(a)
        if not exprs:
            break
        delete(a, exprs[0])
        del exprs
    left = MEL.get_num_material_expressions_in_function(a) if fn else MEL.get_num_material_expressions(a)
    assert left == 0, f"{path}: {left} expressions survived the wipe"
    for k, v in props.items():
        a.set_editor_property(k, v)
    return a


def mf(name, desc, inputs, binds, title, out_type, code, outputs):
    """A material function = inputs (+ scene-texture binds that make the compiler bind those buffers)
    -> one Custom HLSL node -> outputs. outputs: [(name, channels or None)]."""
    only = ONLY
    if only and name not in only.split(","):
        return None
    path = f"{FN}/{name}"
    if EAL.does_asset_exist(path):  # same pins: swap the HLSL in place, so calls keep their pin ids (no material rebuild)
        f = unreal.load_asset(path)
        exprs = MEL.get_material_function_expressions(f)
        have = [str(e.get_editor_property("input_name")) for e in exprs if isinstance(e, unreal.MaterialExpressionFunctionInput)]
        customs = [e for e in exprs if isinstance(e, unreal.MaterialExpressionCustom)]
        if sorted(have) == sorted(i[0] for i in inputs) and len(customs) == 1:
            unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(f)
            customs[0].set_editor_property("code", code.strip())
            customs[0].set_editor_property("description", title)
            f.set_editor_property("description", desc)
            del exprs, customs
            MEL.update_material_function(f)
            EAL.save_asset(path, only_if_is_dirty=False)
            log("updated code", name)
            return f
        del exprs, customs
    f = fresh_graph(f"{FN}/{name}", unreal.MaterialFunction, unreal.MaterialFunctionFactoryNew(),
                    description=desc, expose_to_library=True)
    pins = {}
    y = 0
    for prio, (pin, kind, preview) in enumerate(inputs):
        pins[pin] = put(fn_in(f, pin, kind, preview, prio), -1000, y)
        y += 110
    y += 40
    for pin, sid in binds:
        pins[pin] = (scene_tex(f, sid, -1000, y), "Color")
        y += 130
    c = put(V.custom(f, title, out_type, code, **pins), -560, 0)
    for prio, (out, ch) in enumerate(outputs):
        src = put(V.mask(f, c, ch), -260, 140 * prio) if ch else c
        V.wire(src, put(V.node(f, unreal.MaterialExpressionFunctionOutput, output_name=out, sort_priority=prio),
                        -60, 140 * prio))
    MEL.update_material_function(f)
    EAL.save_asset(f"{FN}/{name}", only_if_is_dirty=False)
    log("saved", name)
    return f


# ---------- HLSL ----------

GLITCH_UV = f"""
// Signal damage as a UV offset, so one later fetch moves the whole picture:
//   Hiccup  : every 8-15 s, for ~3 frames, a few rows tear and some 16 px blocks fail to refresh (always on, rare)
//   Glitch  : tears plus scanline jitter that lives in the shadows (0 = off; story beats raise it)
//   Stutter : a splice line; under it the picture jumps as if from another frame
//   Mosh    : macroblocks drag the picture along their motion vector (datamosh), also a little in each hiccup
float cell = floor(View.GameTime / 11.5);                                  // dream hiccup clock (shared by every glitch):
float at = View.GameTime - cell * 11.5 - (2.0 + 3.5 * frac(sin(cell * 12.9898 + 7.1 * 78.233) * 43758.5453));
float hic = (at > 0.0 && at < 0.05 ? 1.0 : 0.0) * (1.0 - saturate(ReduceMotion));   // ~3 frames, every 8-15 s
float m = 1.0 - saturate(ReduceMotion);
float g = Glitch * m, mo = max(Mosh * m, hic * 0.35), st = Stutter * m;
if (g + mo + st + hic < 0.001) return UV;
float2 vs = View.ViewSizeAndInvSize.xy;
float res = vs.y / 1080.0;
float2 px = UV * vs;
float f = fmod(floor(View.GameTime * 24.0), 997.0);
#define GUV_H(p) frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453)
float2 uv = UV;
float band = floor(px.y / (40.0 * res));
uv.x += step(1.0 - max(0.12 * hic, 0.5 * g), GUV_H(float2(band, f))) * (GUV_H(float2(band, f + 17.0)) - 0.5) * 0.08 * max(g, hic);
if (g > 0.001)
{{
    float L = dot({tex("UV", "PPI_PostProcessInput0", False)}.rgb, float3(0.2126, 0.7152, 0.0722));
    uv.x += (GUV_H(float2(floor(px.y / (2.0 * res)), f)) - 0.5) * 0.006 * g * (1.0 - smoothstep(0.05, 0.25, L));
}}
float below = step(GUV_H(float2(f, 5.0)), UV.y) * st;
uv += below * float2((GUV_H(float2(f, 13.0)) - 0.5) * 0.02, 0.015 + 0.03 * GUV_H(float2(f, 9.0)));
if (mo > 0.001)
{{
    float B = 16.0 * res;
    float2 blk = floor(px / B);
    float2 v = {tex("(blk + 0.5) * B / vs", "PPI_Velocity", False)}.xy * float2(0.5, -0.5);
    float fb = fmod(floor(View.GameTime * 12.0), 997.0);
    float stuck = step(1.0 - (0.3 + 0.7 * mo), GUV_H(blk + fb * 0.37));
    float2 jit = (float2(GUV_H(blk + fb + 11.0), GUV_H(blk + fb + 23.0)) - 0.5) * B / vs;
    uv -= stuck * mo * (v * 12.0 + jit * 1.5);
}}
#undef GUV_H
return uv;
"""

TEAR = f"""
// Horizontal tear on Custom Stencil 2 (the Nightmare): bands of rows shred into spikes. Each pixel looks back along
// its row for a stencil-2 pixel within the band's smear length and copies it; the ink darkens toward the tip.
// Recipe adapted from the VFX lane's M_PP_NightmareGlitch (Tools/Unreal/build_vfx.py). Out: xy = source UV, z = shade.
float a = Tear * (1.0 - saturate(ReduceMotion));
if (a < 0.001) return float3(UV, 1.0);
float t = fmod(floor(View.GameTime * 12.0), 997.0);                       // smears hold on twos
float by = UV.y * 18.0;
float h = frac(sin(floor(by) * 12.9898 + t * 78.233) * 43758.5453);       // per band, per step
if (h < 1.0 - 0.55 * saturate(a * 2.0)) return float3(UV, 1.0);           // this band holds still
float hr = frac(sin(floor(by * 6.0) * 4.1414 + t * 1.618) * 24634.6345);  // finer rows shred the spike
float prof = 1.0 - abs(frac(by) * 2.0 - 1.0);                             // long mid-band, 0 at its edges
float len = a * 0.12 * prof * (0.4 + 0.6 * hr);                           // smear length, viewport UV
float dir = frac(h * 37.719) > 0.5 ? 1.0 : -1.0;
float tear = a * (hr - 0.5) * 0.03;                                       // small row shift inside the body
[loop] for (int i = 0; i <= 10; i++)
{{
    float2 q = UV + float2(tear - dir * len * i / 10.0, 0.0);
    if (abs({tex("q", "PPI_CustomStencil", False)}.r - 2.0) < 0.5) return float3(q, 1.0 - 0.35 * i / 10.0);
}}
return float3(UV, 1.0);
"""

TIME_ECHO = f"""
// Time-shift echo, the hero effect, running VERTICALLY (the user's pick): ghosts slip along Dir (MPC EchoDir, screen
// Y by default) like a film frame slipping in the gate, or a vertical slit-scan. A small static slip is always there;
// motion (velocity magnitude) and story beats (Strength) stretch it. Offsets are fixed, so a still frame stays still.
// Shape: x frames of motion per ghost, y static slip, z decay per ghost, w ghost gain. Dark ghosts blend, light ones glow.
#define TE_COL(p) {tex("p", "PPI_PostProcessInput0", True)}.rgb
float3 base = TE_COL(UV);
float s = Strength * (1.0 - saturate(ReduceMotion));
if (s < 0.001) return base;
float2 vel = {tex("UV", "PPI_Velocity", False)}.xy * float2(0.5, -0.5) / clamp(View.DeltaTime * 60.0, 0.5, 4.0);
float2 stepUV = Dir.xy / max(length(Dir.xy), 1e-4) * (Shape.y * 0.004 + length(vel) * Shape.x);
int n = clamp((int)Taps, 2, 8);
float3 acc = 0.0;
float wsum = 0.0, w = 1.0;
[loop] for (int k = 1; k <= n; k++)
{{
    w *= Shape.z;
    acc += TE_COL(UV + stepUV * k) * w;
    wsum += w;
}}
float3 gh = acc / wsum;
float op = saturate(wsum * Shape.w * s);
#undef TE_COL
return base + (gh - base) * op + max(gh - base, 0.0) * op * 0.6;
"""

INK = """
// Hand-inked lines, drawn BEFORE TSR (After DOF) so the temporal upscaler resolves them like geometry: no per-frame
// crawl or blinking. Silhouettes (depth steps) get a bold stroke, creases (depth kinks, strong normal breaks) a thin
// one, albedo detail a hairline up close (GBuffer base colour, so light gradients never make lines). Strokes fade
// with distance and never touch the sky or the translucent light shafts, which composite after this pass.
// Boil wobbles the strokes <= 0.45 px, 2-4 steps a second (InkBoil, default 0). Dream hiccup: every 8-15 s for
// ~3 frames (and often with GlitchAmount) the drawing slips: a doubled stroke and a few torn rows.
// Ink: x strength, y shadow hatching, z line weight, w albedo hairlines. Quality 0 = depth only.
#define DI_D(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_SceneDepth), PPI_SceneDepth), PPI_SceneDepth, false).r
#define DI_N(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_WorldNormal), PPI_WorldNormal), PPI_WorldNormal, false).rgb
#define DI_B(p) dot(SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_BaseColor), PPI_BaseColor), PPI_BaseColor, false).rgb, float3(0.2126, 0.7152, 0.0722))
#define DI_H(p) frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453)
float3 col = SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(UV, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, false).rgb;
if (Ink.x < 0.001) return col;
float m = 1.0 - saturate(ReduceMotion);
float2 texel = View.ViewSizeAndInvSize.zw;
float res = max(View.ViewSizeAndInvSize.y / 1080.0, 0.5);
float t = View.GameTime;
float cell = floor(t / 11.5);
float at = t - cell * 11.5 - (2.0 + 3.5 * frac(sin(cell * 12.9898 + 7.1 * 78.233) * 43758.5453));
float hic = (at > 0.0 && at < 0.05 ? 1.0 : 0.0) * m;
float slip = saturate(hic + Glitch * m * step(0.6, DI_H(float2(floor(t * 3.0), 3.3))));
float bf = floor(t * (2.0 + 2.0 * Boil));
float2 cu = UV * float2(6.0, 3.5) + bf * 1.37;
float2 i0 = floor(cu), f0 = smoothstep(0.0, 1.0, frac(cu));
float2 wob = float2(lerp(lerp(DI_H(i0), DI_H(i0 + float2(1, 0)), f0.x), lerp(DI_H(i0 + float2(0, 1)), DI_H(i0 + 1.0), f0.x), f0.y),
                   lerp(lerp(DI_H(i0 + 9.1), DI_H(i0 + float2(10.1, 9.1)), f0.x), lerp(DI_H(i0 + float2(9.1, 10.1)), DI_H(i0 + 10.1), f0.x), f0.y)) - 0.5;
float2 base = UV + wob * 0.9 * saturate(Boil) * m * texel;
float row = floor(UV.y / (10.0 * res * texel.y));
float torn = slip * step(0.82, DI_H(float2(row, bf + cell)));
base.x += torn * (DI_H(float2(row, cell + 2.0)) - 0.5) * 14.0 * texel.x;
float ink = 0.0;
int passes = slip > 0.0 ? 2 : 1;
[loop] for (int k = 0; k < passes; k++)
{
    float2 p = base + (k == 0 ? float2(0.0, 0.0) : float2(2.5, -1.5) * res * texel);
    float d0 = DI_D(p);
    float near = saturate(1.0 - (d0 - 800.0) / 2200.0);
    if (near <= 0.0) continue;
    float w = lerp(2.2, 1.2, saturate(d0 / 1500.0)) * res * Ink.z;
    float2 ox = float2(w * texel.x, 0.0), oy = float2(0.0, w * texel.y);
    float sil = (abs(DI_D(p - ox) + DI_D(p + ox) - 2.0 * d0) + abs(DI_D(p - oy) + DI_D(p + oy) - 2.0 * d0)) / d0;
    float2 tx = float2(res * texel.x, 0.0), ty = float2(0.0, res * texel.y);
    float crease = smoothstep(0.004, 0.012, (abs(DI_D(p - tx) + DI_D(p + tx) - 2.0 * d0) + abs(DI_D(p - ty) + DI_D(p + ty) - 2.0 * d0)) / d0);
    float detail = 0.0;
    if (Quality > 0.5)
    {
        float nb = (1.0 - dot(DI_N(p - tx), DI_N(p + tx))) + (1.0 - dot(DI_N(p - ty), DI_N(p + ty)));
        crease = max(crease, smoothstep(0.25, 0.5, nb));
        float lb = abs(DI_B(p - tx) - DI_B(p + tx)) + abs(DI_B(p - ty) - DI_B(p + ty));
        detail = smoothstep(0.18, 0.35, lb) * saturate(1.0 - d0 / 450.0) * Ink.w;
    }
    float stroke = max(smoothstep(0.05, 0.12, sil), max(crease * 0.7, detail)) * near;
    ink = max(ink, stroke * (k == 0 ? 1.0 : 0.75));
}
ink *= 1.0 - 0.6 * torn * step(0.5, DI_H(float2(row, 5.0)));
float L = dot(col * View.PreExposure, float3(0.2126, 0.7152, 0.0722));
float2 px = UV / texel / res;
float hatch = max(step(0.82, frac((px.x + px.y) / 7.0)) * (1.0 - smoothstep(0.03, 0.10, L)),
                  step(0.82, frac((px.x - px.y) / 7.0)) * (1.0 - smoothstep(0.01, 0.03, L))) * Ink.y * 0.35;
#undef DI_D
#undef DI_N
#undef DI_B
#undef DI_H
return col * (1.0 - saturate(ink * Ink.x)) * (1.0 - hatch);
"""

MONO = f"""
// Monochrome split tone: luminance, the ink contrast (Film.w: black point + contrast around a night mid-grey, the
// A-style punch without flattening low-key frames like the moodboard's (L-0.07)/0.88 crush did) and the ink lines, tinted
// from ShadowTint to HighlightTint. HueDrift (0..1 over the story) walks warm keys: soft yellow > honey > amber > ochre
// as luminance-neutral multipliers on those (unit-luminance) tints: the hue moves, the brightness never does.
// Stencil 1 (where visible) or ColorReveal keep real color; 2 (tear), 4 (face blur), 5 (sand) stay mono; 3 (focus) gets a soft warm rim.
const float3 lw = float3(0.2126, 0.7152, 0.0722);
float L = dot(Color, lw);
float Lc = saturate((L - 0.006) / 0.994);
L = lerp(L, saturate(0.12 * pow(Lc / 0.12, 1.0 + 0.4 * Film.w)), saturate(Film.w)) * (1.0 - Ink);
float p = saturate(HueDrift) * 3.0;
float3 sk = p < 1.0 ? lerp(float3(1.04, 1.00, 0.86), float3(1.06, 1.00, 0.82), p)
          : p < 2.0 ? lerp(float3(1.06, 1.00, 0.82), float3(1.08, 0.99, 0.78), p - 1.0)
                    : lerp(float3(1.08, 0.99, 0.78), float3(1.11, 0.98, 0.72), p - 2.0);
float3 hk = p < 1.0 ? lerp(float3(1.06, 1.03, 0.90), float3(1.07, 1.03, 0.87), p)
          : p < 2.0 ? lerp(float3(1.07, 1.03, 0.87), float3(1.08, 1.02, 0.84), p - 1.0)
                    : lerp(float3(1.08, 1.02, 0.84), float3(1.10, 1.01, 0.79), p - 2.0);
float3 sd = sk / float3(1.04, 1.00, 0.86);
float3 hd = hk / float3(1.06, 1.03, 0.90);
sd /= dot(sd, lw);
hd /= dot(hd, lw);
float3 hiTint = HighlightTint.rgb * hd;
hiTint /= max(hiTint.r, max(hiTint.g, hiTint.b));                              // highlights: hue only, never gain above 1
float3 mono = L * lerp(ShadowTint.rgb / dot(ShadowTint.rgb, lw) * sd, hiTint, saturate(L));
float2 suv = GetViewportUV(Parameters);                                       // unwarped: kept colour misregisters under glitches
#define MT_ST(id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(suv, id), id), id, false).r
// custom stencil/depth draw without the scene's depth test: a stencil only counts where that mesh is the visible surface
#define MT_AT(uv, id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(uv, id), id), id, false).r
#define MT_VS(uv) (MT_AT(uv, PPI_CustomDepth) <= MT_AT(uv, PPI_SceneDepth) + 2.0 ? MT_AT(uv, PPI_CustomStencil) : 0.0)
float st = MT_VS(suv);
// focus highlight (contract: Custom Stencil 3 on the focused mesh): a soft warm-white rim on both sides of its edge
float2 ro = 4.0 * max(View.ViewSizeAndInvSize.y / 1080.0, 0.5) * View.ViewSizeAndInvSize.zw;
float n3 = 0.0;
[unroll] for (int i = 0; i < 8; i++)
    n3 += abs(MT_VS(suv + float2(cos(i * 0.785398), sin(i * 0.785398)) * ro) - 3.0) < 0.5 ? 0.125 : 0.0;   // visible taps only: no grid through occluders
float rim = abs(st - 3.0) < 0.5 ? 1.0 - n3 : n3;
mono += hiTint * saturate(rim * 1.6) * 0.2;
float keep = max(abs(st - 1.0) < 0.5 ? 1.0 : 0.0, saturate(ColorReveal));   // 1 only: 2 tear, 3 focus, 4 face, 5 sand stay mono
return lerp(mono, Color, keep);
#undef MT_VS
#undef MT_AT
#undef MT_ST
"""

LENS = f"""
// The dream lens, one pass over the finished mono image (one shared radius and tap disc, so one function):
//   barrel    edges bow out like an old wide lens, corners stay in frame, the breath swells it a hair
//   edge haze vision goes soft and milky toward the edges (golden-angle disc, wider toward the corners)
//   halation  highlights bleed a soft glow (bright pass of the same disc)
//   chroma    the palette splits at the edges: a warm copy pushed out, a cold one pulled in; Glitch spikes it
// Look: x halation, y edge haze, z barrel, w chroma split.
#define DL_COL(p) {tex("p", "PPI_PostProcessInput0", True)}.rgb
const float3 lw = float3(0.2126, 0.7152, 0.0722);
float m = 1.0 - saturate(ReduceMotion);
float2 asp = float2(View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w, 1.0);
float2 d = (UV - 0.5) * asp;
float r = sqrt(dot(d, d) / dot(0.5 * asp, 0.5 * asp));                       // 0 centre, 1 corner
float k = Look.z * (0.18 + 0.04 * Breath * m);
float2 uv = 0.5 + (UV - 0.5) * (1.0 + k * r * r) / (1.0 + k);
float3 c0 = DL_COL(uv);
float e = saturate((r - 0.25) / 0.75);
e *= e;
float2 rad = View.ViewSizeAndInvSize.zw * (View.ViewSizeAndInvSize.y / 1080.0) * (18.0 + 18.0 * e);
int n = clamp((int)Taps, 4, 16);
float3 blur = 0.0;
[loop] for (int i = 0; i < n; i++)
{{
    float a = i * 2.3999632;
    blur += DL_COL(uv + float2(cos(a), sin(a)) * sqrt((i + 0.5) / n) * rad);
}}
blur /= n;
float3 col = lerp(c0, blur, e * Look.y);
col += Look.y * 0.012 * (1.0 - col);                                      // faint milky veil (old film base), even across the frame
col = 1.0 - (1.0 - col) * (1.0 - blur * Look.x * 0.45);                     // Pro-Mist diffusion: screen the soft copy
col += max(blur - 0.45, 0.0) * Look.x * 1.2;                               // halation: highlights bleed further
float sh = (Look.w * 0.004 + 0.02 * Glitch * m) * r * r;
float2 dir = d / max(length(d), 1e-4) / asp;
float l0 = dot(c0, lw);
col += float3(1.0, 0.72, 0.42) * (dot(DL_COL(uv + dir * sh), lw) - l0) + float3(0.0, 0.28, 0.58) * (dot(DL_COL(uv - dir * sh), lw) - l0);
#undef DL_COL
return col;
"""

SORT = f"""
// Pixel-sort streaks: for a frame or two, bright pixels run down a few thin columns below bright edges, like a
// sorted span. Dream hiccups (every 8-15 s) and GlitchAmount trigger it; lighten only.
float cell = floor(View.GameTime / 11.5);                                  // dream hiccup clock (shared by every glitch):
float at = View.GameTime - cell * 11.5 - (2.0 + 3.5 * frac(sin(cell * 12.9898 + 7.1 * 78.233) * 43758.5453));
float hic = (at > 0.0 && at < 0.05 ? 1.0 : 0.0) * (1.0 - saturate(ReduceMotion));   // ~3 frames, every 8-15 s
float g = max(Glitch, hic * 0.5) * (1.0 - saturate(ReduceMotion));
if (g < 0.05) return Color;
float2 vs = View.ViewSizeAndInvSize.xy;
float f = fmod(floor(View.GameTime * 12.0), 997.0);
float c = floor(UV.x * vs.x / (3.0 * vs.y / 1080.0));
float h = frac(sin(c * 12.9898 + f * 78.233) * 43758.5453);
if (h < 1.0 - 0.06 * g) return Color;
float len = (0.05 + 0.35 * frac(h * 91.17)) * g;
const float3 lw = float3(0.2126, 0.7152, 0.0722);
float3 best = Color;
[loop] for (int k = 1; k <= 8; k++)
{{
    float3 s = {tex("UV - float2(0.0, len * k / 8.0)", "PPI_PostProcessInput0", True)}.rgb * (1.0 - k / 12.0);
    best = dot(s, lw) > max(dot(best, lw), 0.45) ? s : best;     // only bright edges bleed
}}
return best;
"""

FILM = """
// Film finish: the breathing vignette closes in on the inhale, then fine 24 fps grain, strongest in the mid-tones.
// Film: x vignette, y grain. UV is the undistorted screen UV, so the vignette stays round.
float2 asp = float2(View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w, 1.0);
float2 d = (UV - 0.5) * asp;
float r = sqrt(dot(d, d) / dot(0.5 * asp, 0.5 * asp));
float v = smoothstep(lerp(0.55, 0.35, Breath), 1.2, r);
float3 col = Color * (1.0 - Film.x * v * (0.75 + 0.25 * Breath));
uint3 h = Rand3DPCG16(int3(int2(UV * View.ViewSizeAndInvSize.xy), int(fmod(View.GameTime * 24.0, 65535.0))));
float L = dot(col, float3(0.2126, 0.7152, 0.0722));
return col + (h.x / 65535.0 - 0.5) * Film.y * 0.08 * (0.3 + 2.8 * L * (1.0 - L));
"""

RETRO = """
// T8 battle styles: the dream loses resolution. Mix (MPC RetroMix, BP_DreamDirector blends it):
//   x pixel art : snap to a screen-anchored virtual grid, 180 rows (square pixels), nearest neighbour; a still camera
//                 never shimmers because the grid is fixed to the screen. Partial x drops the resolution gradually.
//   y dither    : 4x4 Bayer ordered dither into 6 warm tones, soot to bone (on the virtual pixel grid when x is on)
//   z CRT       : slight curvature + scanlines on the virtual rows
//   w wipe      : glitch transition 0..1: a vertical slip plus a band of scrambled blocks (off under ReduceMotion)
// A Color-in stage of the lens pass (no extra full-screen pass): returns Color untouched while RetroMix is 0.
#define DR_COL(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, false).rgb
float4 mx = saturate(Mix);
if (dot(mx, 1.0) < 0.001) return Color;
float2 vs = View.ViewSizeAndInvSize.xy;
float2 uv = UV;
float2 cd = uv - 0.5;
uv = 0.5 + cd * (1.0 + mx.z * 0.12 * dot(cd, cd));                                      // CRT curvature
float wipe = mx.w * (1.0 - saturate(ReduceMotion));
if (wipe > 0.001)
{
    float edge = frac(View.GameTime * 3.1) ;                                              // the wipe line sweeps down
    float rowB = floor(uv.y * 24.0), colB = floor(uv.x * 40.0), f = floor(View.GameTime * 30.0);
    float near = 1.0 - saturate(abs(uv.y - edge) * 6.0);
    float h = frac(sin(dot(float2(colB, rowB) + f, float2(12.9898, 78.233))) * 43758.5453);
    uv.y += wipe * (uv.y < edge ? 0.04 : -0.02);                                          // vertical slip
    uv += wipe * near * step(0.5, h) * (float2(frac(h * 7.1), frac(h * 3.7)) - 0.5) * float2(0.1, 0.06);   // block scramble
}
float rows = lerp(vs.y, 180.0, mx.x * mx.x);                                              // resolution drop
float2 grid = float2(rows * vs.x / vs.y, rows);
float2 cell = floor(uv * grid);
float2 puv = mx.x > 0.001 ? (cell + 0.5) / grid : uv;
float3 col = DR_COL(puv);
if (mx.y > 0.001)
{
    const float B[16] = { 0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5 };
    uint2 bp = uint2(mx.x > 0.5 ? cell : floor(UV * vs / 2.0)) & 3;                       // 2x2 screen px per dot at full res
    float L = dot(col, float3(0.2126, 0.7152, 0.0722));
    float q = saturate(floor(L * 5.0 + (B[bp.y * 4 + bp.x] + 0.5) / 16.0) / 5.0);       // 6 tones
    float3 soot = float3(0.055, 0.045, 0.035), bone = float3(0.93, 0.89, 0.79);
    col = lerp(col, lerp(soot, bone, q * q * (3.0 - 2.0 * q) * 0.35 + q * 0.65), mx.y);
}
if (mx.z > 0.001)
{
    float scan = 0.78 + 0.22 * cos((uv.y * rows) * 6.2831853);                            // one dark line per virtual row
    float inside = step(0.0, uv.x) * step(uv.x, 1.0) * step(0.0, uv.y) * step(uv.y, 1.0);
    col = lerp(col, col * scan * inside * 1.12, mx.z);
}
#undef DR_COL
return lerp(Color, col, saturate(max(mx.x, max(mx.y, mx.z)) + mx.w));
"""


STREAK = """
// Shift streak, Project Hail Mary's shutter-timing error (the "RE timing shift box"): the film pulls down while the
// shutter is still open, so ONLY the highlights smear across the frame and keep their colour. This pass runs before
// TSR (After DOF, HDR): per-pixel interleaved-gradient jitter on the tap offsets is resolved by TSR into a smooth
// streak with Taps (12 High / 8 Low) instead of 32 taps + a 5-stage cascade.
// Streak: x length (fraction of the frame), y angle in degrees (0 = vertical), z intensity 0..5, w highlight threshold
//         (exposed luminance).  Fx: x symmetric, y wrap at the frame edges like a real gate, z length jitter, w jitter speed.
// Letterbox 0..1 slides 2.39:1 bars in BEFORE the streaks are added, so the streaks cross the bars. StreaksOnly 1 = debug.
#define SS_COL(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, false).rgb
float3 col = SS_COL(UV);
float aspect = View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w;
float bar = 0.5 * saturate(1.0 - aspect / 2.39) * saturate(Letterbox);
col *= (UV.y < bar || UV.y > 1.0 - bar) ? 0.0 : 1.0;
float m = 1.0 - saturate(ReduceMotion);
float jt = View.GameTime * Fx.w + 17.31;
float n0 = frac(sin(floor(jt) * 12.9898) * 43758.5453), n1 = frac(sin((floor(jt) + 1.0) * 12.9898) * 43758.5453);
float len = Streak.x * (1.0 + Fx.z * m * (lerp(n0, n1, smoothstep(0.0, 1.0, frac(jt))) - 0.5) * 2.0);
if (Streak.z < 0.001 || len <= 0.0) return StreaksOnly > 0.5 ? float3(0.0, 0.0, 0.0) : col;
float a = radians(Streak.y);
float2 dir = float2(sin(a) / aspect, cos(a)) * len;
int n = clamp((int)Taps, 4, 16);
float j = InterleavedGradientNoise(Parameters.SvPosition.xy, View.StateFrameIndexMod8);
float3 acc = 0.0;
[loop] for (int k = 0; k < n; k++)
{
    float t = (k + j) / n;                                                   // 0..1 along the pull
    t = Fx.x > 0.5 ? t * 2.0 - 1.0 : t;                                     // symmetric: both ways
    float2 q = UV - dir * t;
    q = Fx.y > 0.5 ? frac(q) : q;                                           // wrap like a real gate
    float3 h = SS_COL(q);
    float L = dot(h, float3(0.2126, 0.7152, 0.0722)) * View.PreExposure;
    acc += h * smoothstep(Streak.w, Streak.w * 2.0 + 0.25, L) * pow(1.0 - abs(t), 2.0);
}
float3 streak = acc / n * Streak.z * Mask * Tint.rgb;
#undef SS_COL
return StreaksOnly > 0.5 ? streak : col + streak;
"""


SAND = """
// Sand FX (Custom Stencil 5, set by the sandvfx lane): the black sand is where the dream frays most. Inside the mask
// (dilated ~6 px sideways and along the trail below, so trails spill past the silhouette):
//   intense vertical time echo that runs even with a still camera (4 ghosts on slowly breathing offsets)
//   datamosh: 12 px macroblocks hold an offset for a few frames, then jump (a missing I-frame); rare big tears
//   a little RGB split on the edges, posterized dither banding in the mass, rare one-frame inverted flickers
// Amount (MPC SandFXAmount) + Glitch scale it; ReduceMotion keeps 25% and drops the flicker. A Color-in stage of the
// lens pass (no extra full-screen pass): off the sand it returns Color after one stencil read + 5 dilation reads.
#define SF_COL(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, true).rgb
// custom stencil is drawn without the scene's depth test: only sand that is actually visible counts (no FX through
// the bed, the dresser or the player in front of it)
#define SF_ST(p, id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, id), id), id, false).r
#define SF_S5(p) ((abs(SF_ST(p, PPI_CustomStencil) - 5.0) < 0.5 && SF_ST(p, PPI_CustomDepth) <= SF_ST(p, PPI_SceneDepth) + 2.0) ? 1.0 : 0.0)
#define SF_H(p) frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453)
float3 base = Color;
float rm = saturate(ReduceMotion);
float a = saturate(Amount + Glitch) * (1.0 - 0.75 * rm);
if (a < 0.001) return base;
float t = View.GameTime;
float br = 0.5 + 0.5 * sin(t * 0.9);                                           // the trail breathes
float trail = (0.012 + 0.01 * br) * 4.0 * a;                                  // UV length of the 4 ghosts
float2 px = 6.0 * max(View.ViewSizeAndInvSize.y / 1080.0, 0.5) * View.ViewSizeAndInvSize.zw;
float mask = SF_S5(UV);
if (mask < 0.5)
{
    mask = max(max(SF_S5(UV + float2(px.x, 0.0)), SF_S5(UV - float2(px.x, 0.0))), SF_S5(UV + float2(0.0, px.y))) * 0.8;
    mask = max(mask, max(SF_S5(UV + float2(0.0, trail * 0.5)), SF_S5(UV + float2(0.0, trail))) * 0.7);
}
if (mask <= 0.0) return base;
float2 vs = View.ViewSizeAndInvSize.xy;
float B = 12.0 * max(vs.y / 1080.0, 0.5);
float2 blk = floor(UV * vs / B);
float hold = floor(t * 7.5);                                                  // hold ~4 frames, then jump
float h = SF_H(blk + hold);
float2 off = (float2(SF_H(blk * 1.7 + hold), SF_H(blk * 2.3 + hold + 5.0)) - 0.5) * (B / vs) * 3.0;
off.y += h > 0.93 ? (SF_H(blk.yy + hold) - 0.5) * 0.08 : 0.0;                // occasional big tear
float2 uvm = UV + off * step(0.35, h) * a;
float3 col = SF_COL(uvm);
float3 acc = 0.0;
float wsum = 0.0, w = 1.0;
[unroll] for (int k = 1; k <= 4; k++)
{
    w *= 0.68;
    acc += SF_COL(uvm + float2(0.004 * sin(t * 0.7 + k), trail * k / 4.0)) * w;   // ghosts of what is below: sand smears up
    wsum += w;
}
col = lerp(col, acc / wsum, 0.55 * a);
float2 rg = float2(2.0, 0.0) * View.ViewSizeAndInvSize.zw * a;
col = float3(SF_COL(uvm + rg).r, col.g, SF_COL(uvm - rg).b) * (1.0 - mask) + col * mask;   // RGB split where the mask fades
const float Bm[16] = { 0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5 };
uint2 bp = uint2(UV * vs / 2.0) & 3;
float L = dot(col, float3(0.2126, 0.7152, 0.0722));
float q = floor(L * 6.0 + (Bm[bp.y * 4 + bp.x] + 0.5) / 16.0) / 6.0;
col = lerp(col, col * (q / max(L, 1e-3)), 0.5 * a);                           // posterized dither banding
float flick = (1.0 - rm) * step(0.985, SF_H(float2(floor(t * 24.0), 3.7)));
col = lerp(col, 1.0 - col, flick * 0.8 * a);                                  // rare one-frame negative
#undef SF_COL
#undef SF_S5
#undef SF_ST
#undef SF_H
return lerp(base, col, mask * saturate(a * 1.5));
"""


UV2 = ("UV", "VECTOR2", (0.5, 0.5, 0.0))


def functions():
    S = lambda n, p=0.0: (n, "SCALAR", p)  # noqa: E731
    V4 = lambda n, p: (n, "VECTOR4", p)  # noqa: E731
    mf("MF_Dream_GlitchUV", "Signal damage as a UV offset: scanline jitter (Glitch), frame slip (Stutter), "
       "datamosh macroblocks (Mosh). ReduceMotion 1 disables it.",
       [UV2, S("Glitch"), S("Mosh"), S("Stutter"), S("ReduceMotion")], [("Vel", "PPI_VELOCITY")],
       "Signal damage: jitter, slip, mosh", F2, GLITCH_UV, [("UV", None)])
    mf("MF_Dream_Tear", "Horizontal tear/smear spikes on Custom Stencil 2 (the Nightmare), triggered by TearAmount.",
       [UV2, S("Tear"), S("ReduceMotion")], [("Stencil", "PPI_CUSTOM_STENCIL")],
       "Stencil-2 tear", F3, TEAR, [("UV", "rg"), ("Shade", "b")])
    mf("MF_Dream_TimeEcho", "Vertical time-shift echo: decaying ghost copies slipping along Dir (EchoDir), longer "
       "with motion and Strength. Strength 0 = off.",
       [UV2, S("Strength", 0.35), V4("Shape", (1.5, 0.6, 0.72, 0.35)), S("ReduceMotion"), S("Taps", 6.0),
        ("Dir", "VECTOR2", (0.0, 1.0))],
       [("SceneColor", "PPI_POST_PROCESS_INPUT0"), ("Vel", "PPI_VELOCITY")],
       "Time-shift echo (ghost taps)", F3, TIME_ECHO, [("Color", None)])
    mf("MF_Dream_InkEdges", "Ink line mask from depth creases and normal breaks (Film.z = strength).",
       [UV2, V4("Film", (0.55, 0.4, 0.6, 0.6))], [("Depth", "PPI_SCENE_DEPTH"), ("Normal", "PPI_WORLD_NORMAL")],
       "Ink lines (depth + normal)", F1, INK, [("Ink", None)])
    mf("MF_Dream_MonoTone", "Monochrome split tone with ink crush, ink lines and HueDrift; stencil 1/3+ or ColorReveal "
       "keep color, stencil 2 stays mono.",
       [("Color", "VECTOR3", (0.5, 0.5, 0.5)), S("Ink"), V4("Film", (0.55, 0.4, 0.6, 0.6)), S("HueDrift"),
        V4("ShadowTint", (0.9, 0.95, 1.0, 1.0)), V4("HighlightTint", (1.0, 0.98, 0.94, 1.0)), S("ColorReveal")],
       [("Stencil", "PPI_CUSTOM_STENCIL"), ("Depth", "PPI_SCENE_DEPTH"), ("CDepth", "PPI_CUSTOM_DEPTH")],
       "Mono split tone + hue drift", F3, MONO, [("Color", None)])
    mf("MF_Dream_Lens", "Dream lens: barrel distortion, edge haze, halation and palette chroma split in one tap disc.",
       [UV2, V4("Look", (0.45, 0.55, 0.35, 0.45)), S("Glitch"), S("Breath", 0.5), S("ReduceMotion"), S("Taps", 16.0)],
       [("SceneColor", "PPI_POST_PROCESS_INPUT0")], "Dream lens: barrel, haze, halation, chroma", F3, LENS,
       [("Color", None)])
    mf("MF_Dream_PixelSort", "Pixel-sort streaks on a few columns while GlitchAmount is up (lighten only).",
       [("Color", "VECTOR3", (0.5, 0.5, 0.5)), UV2, S("Glitch"), S("ReduceMotion")],
       [("SceneColor", "PPI_POST_PROCESS_INPUT0")], "Pixel-sort streaks", F3, SORT, [("Color", None)])
    mf("MF_Dream_FilmFinish", "Breathing vignette (Film.x, Breath) and mid-tone weighted 24 fps grain (Film.y).",
       [("Color", "VECTOR3", (0.5, 0.5, 0.5)), UV2, V4("Film", (0.55, 0.4, 0.6, 0.6)), S("Breath", 0.5)], [],
       "Film finish: breathing vignette + grain", F3, FILM, [("Color", None)])
    log("functions OK")


# ---------- the two post-process materials ----------

def pp_material(path, priority):
    return fresh_graph(path, unreal.Material, unreal.MaterialFactoryNew(),
                       material_domain=unreal.MaterialDomain.MD_POST_PROCESS,
                       blendable_location=B.enum(unreal.BlendableLocation, "BL_SCENE_COLOR_AFTER_TONEMAPPING"),
                       blendable_priority=priority)


def call(m, fn, x, y, **ins):
    c = put(V.node(m, unreal.MaterialExpressionMaterialFunctionCall), x, y)
    c.set_material_function(unreal.load_asset(f"{FN}/{fn}"))
    for pin, src in ins.items():
        V.wire(src, c, pin)
    return c


def quality(m, low, default, x, y):
    """Tap budget per material quality level (scalability Shading): Low gets the cheap count."""
    q = put(V.node(m, unreal.MaterialExpressionQualitySwitch), x, y)
    V.wire(put(V.node(m, unreal.MaterialExpressionConstant, r=float(default)), x - 160, y), q, "Default")
    V.wire(put(V.node(m, unreal.MaterialExpressionConstant, r=float(low)), x - 160, y + 70), q, "Low")
    return q


def materials():
    # Pass A, aligned with the scene buffers: UV damage > tear > echo (x tear shade) > ink > mono
    if not ONLY or "M_PP_DreamMono" in ONLY:
        dream_mono()
    if not ONLY or "M_PP_DreamLens" in ONLY:
        dream_lens()


def dream_mono():
    path = PP + "/M_PP_DreamMono"
    m = pp_material(path, 0)
    uv0 = put(V.node(m, unreal.MaterialExpressionScreenPosition), -2900, 0)
    glitch = call(m, "MF_Dream_GlitchUV", -2400, 0, UV=(uv0, "ViewportUV"),
                  Glitch=mpc_param(m, "GlitchAmount", -2700, 110), Mosh=mpc_param(m, "MoshAmount", -2700, 190),
                  Stutter=mpc_param(m, "StutterAmount", -2700, 270), ReduceMotion=mpc_param(m, "ReduceMotion", -2700, 350))
    tear = call(m, "MF_Dream_Tear", -1950, 0, UV=(glitch, "UV"), Tear=mpc_param(m, "TearAmount", -2200, 110),
                ReduceMotion=mpc_param(m, "ReduceMotion", -2200, 190))
    echo = call(m, "MF_Dream_TimeEcho", -1450, 0, UV=(tear, "UV"),
                Strength=mpc_param(m, "EchoStrength", -1750, 260), Shape=mpc_param(m, "EchoShape", -1750, 340),
                ReduceMotion=mpc_param(m, "ReduceMotion", -1750, 420), Taps=quality(m, 3, 6, -1750, 520))
    ink = call(m, "MF_Dream_InkEdges", -1450, 640, UV=(tear, "UV"), Film=mpc_param(m, "FilmLook", -1750, 700))
    torn = put(V.op(m, unreal.MaterialExpressionMultiply, (echo, "Color"), (tear, "Shade")), -1100, 0)
    mono = call(m, "MF_Dream_MonoTone", -650, 0, Color=torn, Ink=(ink, "Ink"), Film=mpc_param(m, "FilmLook", -950, 200),
                HueDrift=mpc_param(m, "HueDrift", -950, 280), ShadowTint=mpc_param(m, "ShadowTint", -950, 360),
                HighlightTint=mpc_param(m, "HighlightTint", -950, 440), ColorReveal=mpc_param(m, "ColorReveal", -950, 520))
    V.out((mono, "Color"), V.MP.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_asset(path, only_if_is_dirty=False)
    log("saved M_PP_DreamMono")



def dream_lens():
    # Pass B, on the finished mono image: lens > pixel sort > film finish
    path = PP + "/M_PP_DreamLens"
    n = pp_material(path, 1)
    g = mpc_param(n, "GlitchAmount", -1450, 160)
    rm = mpc_param(n, "ReduceMotion", -1450, 320)
    br = mpc_param(n, "Breath", -1450, 240)
    lens = call(n, "MF_Dream_Lens", -1150, 0, UV=(put(V.node(n, unreal.MaterialExpressionScreenPosition), -1450, 0), "ViewportUV"),
                Look=mpc_param(n, "LensLook", -1450, 80), Glitch=g, Breath=br, ReduceMotion=rm,
                Taps=quality(n, 8, 16, -1450, 420))
    sort = call(n, "MF_Dream_PixelSort", -750, 0, Color=(lens, "Color"),
                UV=(put(V.node(n, unreal.MaterialExpressionScreenPosition), -1000, 260), "ViewportUV"), Glitch=g, ReduceMotion=rm)
    fin = call(n, "MF_Dream_FilmFinish", -400, 0, Color=(sort, "Color"),
               UV=(put(V.node(n, unreal.MaterialExpressionScreenPosition), -650, 200), "ViewportUV"),
               Film=mpc_param(n, "FilmLook", -650, 300), Breath=br)
    V.out((fin, "Color"), V.MP.MP_EMISSIVE_COLOR)
    MEL.recompile_material(n)
    EAL.save_asset(path, only_if_is_dirty=False)
    log("saved M_PP_DreamLens")


# ---------- the unbound volume ----------

def volume():
    ppv = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == "PP_DreamMono")
    s = ppv.get_editor_property("settings")
    blends = []
    for path in (PP + "/M_PP_DreamMono", PP + "/M_PP_DreamLens"):
        wb = unreal.WeightedBlendable()
        wb.set_editor_property("weight", 1.0)
        wb.set_editor_property("object", unreal.load_asset(path))
        blends.append(wb)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property("array", blends)
    s.set_editor_property("weighted_blendables", wbs)
    # our vignette breathes and our grain is mono + mid-tone weighted, so the tonemapper's versions go to zero
    for flag, prop, value in (("override_vignette_intensity", "vignette_intensity", 0.0),
                              ("override_film_grain_intensity", "film_grain_intensity", 0.0),
                              ("override_scene_fringe_intensity", "scene_fringe_intensity", 0.0)):
        s.set_editor_property(flag, True)
        s.set_editor_property(prop, value)
    ppv.set_editor_property("settings", s)
    log("volume", ppv.get_actor_label(), "unbound", ppv.get_editor_property("unbound"),
        [str(b.get_editor_property("object").get_name()) for b in blends])


EV100 = float(os.environ.pop("FOA_EV", "0.15"))  # locked exposure every lane judges against


def filmic():
    """UE's own film features on PP_DreamMono, so the look stays lean: motion blur (180-degree shutter at 24 fps),
    film grain, bloom for halation, a soft toe that crushes but never clips the blacks; the tonemapper's vignette
    and fringe stay off (ours breathe / stay in the palette)."""
    ppv = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == "PP_DreamMono")
    s = ppv.get_editor_property("settings")
    for prop, value in (("motion_blur_amount", 0.25), ("motion_blur_max", 3.0), ("motion_blur_target_fps", 24),  # beats push more
                        ("film_grain_intensity", 0.22),
                        # black Pro-Mist: a wide, low bloom lets highlights bleed softly into the shadows
                        ("bloom_intensity", 0.35), ("bloom_size_scale", 8.0), ("bloom_threshold", -1.0),
                        # no gameplay DOF (it blurred the floor around the player): focal distance 0 = off; cinematic
                        # beats focus with their CineCamera's own settings
                        ("depth_of_field_focal_distance", 0.0),
                        ("film_toe", 0.5), ("film_black_clip", 0.0), ("film_white_clip", 0.0), ("film_shoulder", 0.26),
                        ("vignette_intensity", 0.0), ("scene_fringe_intensity", 0.0),
                        # locked exposure (min == max): no eye adaptation blowing close-ups out; same frame for every lane
                        ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM), ("auto_exposure_bias", 0.0),
                        ("auto_exposure_min_brightness", EV100), ("auto_exposure_max_brightness", EV100)):
        s.set_editor_property("override_" + prop, True)
        s.set_editor_property(prop, value)
    ppv.set_editor_property("settings", s)
    # no extra sharpening anywhere (the crisp UE look): live now; Config/DefaultEngine.ini carries it for the build
    unreal.SystemLibrary.execute_console_command(None, "r.Tonemapper.Sharpen 0")
    log("filmic settings on", ppv.get_actor_label())


# ---------- comment bubbles (boxes come from Hayba's material_add_comment) ----------

def bubbles():
    n = 0
    for c in unreal.ObjectIterator(unreal.MaterialExpressionComment):
        if c.get_path_name().startswith(PP + "/"):
            c.set_editor_property("comment_bubble_visible_in_details_panel", True)
            c.set_editor_property("color_comment_bubble", True)
            n += 1
    log("comment bubbles on", n)


def stats():
    rows = []
    for p in sorted(EAL.list_assets(PP, recursive=True, include_folder=False)):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.Material):
            s = MEL.get_statistics(a)
            rows.append(f"{a.get_name():<22} nodes {MEL.get_num_material_expressions(a):>3}  PS instr "
                        f"{s.num_pixel_shader_instructions:>4}  samplers {s.num_samplers}")
        elif isinstance(a, unreal.MaterialFunction):
            rows.append(f"{a.get_name():<22} nodes {MEL.get_num_material_expressions_in_function(a):>3}")
    print("\n".join(rows))


STEPS = {"mpc": mpc, "functions": functions, "materials": materials, "volume": volume, "filmic": filmic, "bubbles": bubbles,
         "stats": stats}
first = len(B.LINES)  # B.LINES lives on across runs in the editor's Python session
ONLY = os.environ.pop("FOA_ONLY", "")  # ue_remote's env lives on in the editor: consume it
for step in os.environ.pop("FOA_STEP", "all").split(","):
    for name in (STEPS if step == "all" else [step]):
        STEPS[name]()
print("\n".join(B.LINES[first:]))
