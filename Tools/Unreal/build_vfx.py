"""FoA sand VFX as cheap material effects (no Niagara), all under /Game/FoA/VFX. Runs INSIDE the open editor.

Steps (one per editor call keeps each run short; other agents share the editor):
  sand()         T_VFX_Noise, SM_SandFall, M_SandFall + M_SandImpact and their MIs
  dissolve()     MF_SandDissolve + M_Demo_SandDissolve / MI_Demo_SandDissolve
  glitch()       MPC_VFX + M_PP_NightmareGlitch
  timeshift()    RT_TimeShift_*, M_TimeShiftAccumulate, MI_TimeShiftCopy, M_PP_TimeShift
  splats(names)  P:/FoA-Assets/splatmesh/<name>.gltf -> Splats/Meshes, M_SplatMesh, MI_Splat_<name>
  lab() / clear_lab()   test actors in outliner folder VFX_Lab at X >= 4600 (never touches the bedroom)
  stats()        instruction / sampler counts of every VFX material
Sources: Tools/Unreal/make_vfx_sources.py. Docs: docs/vfx-sand.md. Re-running a step rebuilds its graphs in
place (same assets), so MIs and placed actors keep working.
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import build_bedroom as B  # noqa: E402  (helper library; importing builds nothing)

MEL, EAL, AT, EAS = B.MEL, B.EAL, B.AT, B.EAS
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
MP = unreal.MaterialProperty
VFX = "/Game/FoA/VFX"
SRC = "P:/FoA-Assets/vfx"
SPLAT_SRC = "P:/FoA-Assets/splatmesh"
F1, F2, F3, F4 = (getattr(unreal.CustomMaterialOutputType, f"CMOT_FLOAT{i}") for i in range(1, 5))
LINEAR = B.enum(unreal.MaterialSamplerType, "SAMPLERTYPE_LINEAR_COLOR")
MASKED = unreal.BlendMode.BLEND_MASKED
SAND_BLACK = (0.006, 0.0055, 0.005)  # = M_DarkSand SandColor
log = B.log


# ---------- graph helpers ----------

def material(name, path, **props):
    """Existing asset: wipe its graph and rebuild in place (keeps references). New: create."""
    full = f"{path}/{name}"
    m = unreal.load_asset(full) if EAL.does_asset_exist(full) else None
    if m:
        MEL.delete_all_material_expressions(m)
    else:
        m = AT.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    for k, v in props.items():
        B.setp(m, k, v)
    return m


def node(graph, cls, **props):
    if isinstance(graph, unreal.MaterialFunction):
        e = MEL.create_material_expression_in_function(graph, cls, 0, 0)
    else:
        e = MEL.create_material_expression(graph, cls, 0, 0)
    for k, v in props.items():
        B.setp(e, k, v)
    return e


def wire(src, dst, pin=""):
    e, out = src if isinstance(src, tuple) else (src, "")
    B.link(e, out, dst, pin)


def op(g, cls, a, b=None):
    e = node(g, cls)
    for val, pin, const in ((a, "A", "const_a"), (b, "B", "const_b")):
        if isinstance(val, (int, float)):
            B.setp(e, const, float(val))
        elif val is not None:
            wire(val, e, pin)
    return e


def lerp(g, a, b, alpha):
    e = node(g, unreal.MaterialExpressionLinearInterpolate)
    for val, pin, const in ((a, "A", "const_a"), (b, "B", "const_b"), (alpha, "Alpha", "const_alpha")):
        if isinstance(val, (int, float)):
            B.setp(e, const, float(val))
        else:
            wire(val, e, pin)
    return e


def mask(g, src, ch):
    e = node(g, unreal.MaterialExpressionComponentMask, r="r" in ch, g="g" in ch, b="b" in ch, a="a" in ch)
    wire(src, e)
    return e


def custom(g, desc, out_type, code, **inputs):
    e = node(g, unreal.MaterialExpressionCustom, description=desc, output_type=out_type, code=code.strip())
    pins = []
    for n in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        pins.append(ci)
    e.set_editor_property("inputs", pins)
    for n, src in inputs.items():
        wire(src, e, n)
    return e


def sp(g, name, value):
    return node(g, unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(value))


def vp(g, name, v):
    return node(g, unreal.MaterialExpressionVectorParameter, parameter_name=name,
                default_value=unreal.LinearColor(*v, *([1.0] * (4 - len(v)))))


def uvs(g, index=0):
    return node(g, unreal.MaterialExpressionTextureCoordinate, coordinate_index=index)


def tex(g, texture, uv, param=None):
    e = node(g, unreal.MaterialExpressionTextureSampleParameter2D if param else unreal.MaterialExpressionTextureSample,
             texture=texture, sampler_type=LINEAR, **({"parameter_name": param} if param else {}))
    wire(uv, e, "UVs")
    return e


def out(src, prop):
    e, o = src if isinstance(src, tuple) else (src, "")
    if not MEL.connect_material_property(e, o, prop):
        log("WARN property link failed", e.get_name(), "->", prop)


def finish(m):
    MEL.layout_material_expressions(m)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def instance(name, path, parent, scalars=None, vectors=None, switches=None, textures=None):
    full = f"{path}/{name}"
    mi = unreal.load_asset(full) if EAL.does_asset_exist(full) else \
        AT.create_asset(name, path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v, *([1.0] * (4 - len(v)))))
    for k, v in (switches or {}).items():
        MEL.set_material_instance_static_switch_parameter_value(mi, k, v)
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(mi, k, v)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    return mi


# Stochastic alpha shared by every masked VFX: no sorting; TSR/TAA resolves it, without them it reads as grain.
# Seed decorrelates overlapping layers (same recipe as Tools/Splats/README.md).
DITHER = "return Alpha > InterleavedGradientNoise(Parameters.SvPosition.xy + Seed * 117.0, View.StateFrameIndexMod8) ? 1.0 : 0.0;"


def dither(g, alpha, seed=0.0):
    return custom(g, "Dithered alpha (IGN)", F1, DITHER, Alpha=alpha, Seed=node(g, unreal.MaterialExpressionConstant, r=seed)
                  if isinstance(seed, float) else seed)


# ---------- imported sources ----------

def import_file(src, dest, name=None):
    t = unreal.AssetImportTask()
    for k, v in (("filename", src), ("destination_path", dest), ("automated", True), ("replace_existing", True), ("save", True)):
        t.set_editor_property(k, v)
    if name:
        t.set_editor_property("destination_name", name)
    AT.import_asset_tasks([t])
    return [unreal.load_asset(p) for p in t.get_editor_property("imported_object_paths")]


def noise_texture():
    full = VFX + "/Textures/T_VFX_Noise"
    if EAL.does_asset_exist(full):
        return unreal.load_asset(full)
    t = next(o for o in import_file(SRC + "/T_VFX_Noise.png", VFX + "/Textures", "T_VFX_Noise") if isinstance(o, unreal.Texture2D))
    B.setp(t, "srgb", False)
    # uncompressed BGRA8 (256 KB + mips): BC1/BC7 blocks would bleed the three independent channels into each other
    B.setp(t, "compression_settings", B.enum(unreal.TextureCompressionSettings, "TC_VECTOR_DISPLACEMENTMAP"))
    EAL.save_loaded_asset(t)
    return t


def import_mesh(src, folder, name, ext_pos=(0, 0, 0), ext_neg=(0, 0, 0), material=None):
    """glTF -> one classic (non-Nanite) StaticMesh in `folder`; drops the material Interchange makes from the glTF."""
    full = f"{folder}/{name}"
    if not EAL.does_asset_exist(full):
        tmp = f"{folder}/_import_{name}"  # Interchange writes <dest>/<scene>/StaticMeshes|Materials/...
        import_file(src, tmp)
        found = [p for p in EAL.list_assets(tmp, recursive=True, include_folder=False)
                 if isinstance(unreal.load_asset(p), unreal.StaticMesh)]
        if not found:
            raise RuntimeError("import failed: " + src)
        unreal.load_asset(found[0]).set_material(0, material or B.CUBE.get_material(0))  # drop the glTF material
        EAL.rename_asset(found[0], full)
        EAL.delete_directory(tmp)
    mesh = unreal.load_asset(full)
    ns = SMES.get_nanite_settings(mesh)
    ns.set_editor_property("enabled", False)  # Interchange builds Nanite by default; WPO + masked is cheaper classic
    SMES.set_nanite_settings(mesh, ns, True)
    bs = SMES.get_lod_build_settings(mesh, 0)
    for k, v in (("recompute_normals", False), ("recompute_tangents", False),  # keep the imported frame (splat anisotropy)
                 ("generate_lightmap_u_vs", False),  # all 8 UV channels carry data; lightmap UVs would overwrite one
                 ("distance_field_resolution_scale", 0.0)):  # no SDF: VFX never feed Lumen / DF shadows
        bs.set_editor_property(k, v)
    SMES.set_lod_build_settings(mesh, 0, bs)
    # WPO grows the geometry past its vertices: extend bounds so it is not culled at screen edges
    B.setp(mesh, "positive_bounds_extension", unreal.Vector(*ext_pos))
    B.setp(mesh, "negative_bounds_extension", unreal.Vector(*ext_neg))
    if material:
        mesh.set_material(0, material)
    EAL.save_loaded_asset(mesh)
    return mesh


# ---------- 1. sand fall + impact ----------

def sand():
    noise = noise_texture()
    path = VFX + "/Sand"

    m = material("M_SandFall", path, blend_mode=MASKED, two_sided=True, opacity_mask_clip_value=0.5)
    speed, width, dens, spread = sp(m, "Speed", 1.0), sp(m, "Width", 2.5), sp(m, "Density", 0.65), sp(m, "Spread", 1.5)
    color = vp(m, "SandColor", SAND_BLACK)
    uv = uvs(m)
    out(custom(m, "Width + flare toward the floor (WPO)", F3, """
// the mesh is a 1 cm tube; push it out to Width/2, widening by (1 + Spread v^2) as the sand spreads
return Normal * (0.5 * Width * (1.0 + Spread * UV.y * UV.y) - 1.0);""",
               UV=uv, Normal=node(m, unreal.MaterialExpressionVertexNormalWS), Width=width, Spread=spread),
        MP.MP_WORLD_POSITION_OFFSET)
    drop = op(m, unreal.MaterialExpressionSubtract, mask(m, node(m, unreal.MaterialExpressionObjectPositionWS), "b"),
              mask(m, node(m, unreal.MaterialExpressionWorldPosition), "b"))
    fall = custom(m, "Fall UVs (gravity)", F4, """
// texture the stream by EMISSION TIME: sand at drop d left the edge tf seconds ago (d = v0 t + g t^2 / 2,
// v0 = 30 cm/s, g = 980 cm/s^2), so grains accelerate and stretch into streaks like real falling sand.
// Speed scales dream time: 0.5 = true slow motion (same spacing, half the velocity).
float tf = (sqrt(900.0 + 1960.0 * max(Drop, 0.0)) - 30.0) / 980.0;
float age = T - tf;
return float4(UV.x * 0.125, age * 0.9, 0.37, age * 0.31);    // xy: grain (R), zw: clumps (G)""",
                  UV=uv, Drop=drop, T=op(m, unreal.MaterialExpressionMultiply, node(m, unreal.MaterialExpressionTime), speed))
    grain = mask(m, tex(m, noise, mask(m, fall, "rg")), "r")
    clump = mask(m, tex(m, noise, mask(m, fall, "ba")), "g")
    alpha = custom(m, "Stream coverage", F1, """
float dens = Density * (1.0 - 0.3 * V);                    // thins out as it spreads
float core = saturate(abs(dot(N, Cam)) * 1.6);             // dense core, grainy silhouette
float s = Grain * 0.7 + Clump * 0.3;
return saturate((s - (1.0 - dens * (0.5 + 0.5 * core))) * 12.0);   // crisp grains, not soft fog""",
                   Grain=grain, Clump=clump, Density=dens, V=mask(m, uv, "g"),
                   N=node(m, unreal.MaterialExpressionVertexNormalWS), Cam=node(m, unreal.MaterialExpressionCameraVectorWS))
    out(dither(m, alpha), MP.MP_OPACITY_MASK)
    out(op(m, unreal.MaterialExpressionMultiply, color, op(m, unreal.MaterialExpressionAdd, grain, 0.5)), MP.MP_BASE_COLOR)
    out(lerp(m, 0.1, 0.35, clump), MP.MP_ROUGHNESS)  # wet, oily
    out(node(m, unreal.MaterialExpressionConstant, r=0.8), MP.MP_SPECULAR)
    finish(m)

    imp = material("M_SandImpact", path, blend_mode=MASKED, opacity_mask_clip_value=0.5)
    speed, dens, color = sp(imp, "Speed", 1.0), sp(imp, "Density", 0.65), vp(imp, "SandColor", SAND_BLACK)
    uv = uvs(imp)
    polar = custom(imp, "Polar UVs (spray moves outward)", F4, """
float2 p = UV * 2.0 - 1.0;
float r = length(p);
float a = atan2(p.y, p.x) * 0.15915494 + 0.5;      // one texture tile around: no seam
return float4(a, r * 0.12 - T * 0.12, r, 0.0);""",
                   UV=uv, T=op(imp, unreal.MaterialExpressionMultiply, node(imp, unreal.MaterialExpressionTime), speed))
    grain = mask(imp, tex(imp, noise, mask(imp, polar, "rg")), "r")
    clump = mask(imp, tex(imp, noise, op(imp, unreal.MaterialExpressionMultiply, uv, 0.3)), "g")
    alpha = custom(imp, "Heap + spray coverage", F1, """
float heap  = saturate((0.3 - R + (Clump - 0.5) * 0.3) * 10.0);                     // where the stream lands
float spray = saturate((Grain - 1.0 + Density * saturate(1.0 - R) * 0.9) * 6.0);   // thrown grains, thinning to the rim
return R < 1.0 ? max(heap, spray) : 0.0;""",
                   Grain=grain, Clump=clump, R=mask(imp, polar, "b"), Density=dens)
    out(dither(imp, alpha), MP.MP_OPACITY_MASK)
    out(op(imp, unreal.MaterialExpressionMultiply, color, op(imp, unreal.MaterialExpressionAdd, grain, 0.5)), MP.MP_BASE_COLOR)
    out(lerp(imp, 0.1, 0.35, clump), MP.MP_ROUGHNESS)
    out(node(imp, unreal.MaterialExpressionConstant, r=0.8), MP.MP_SPECULAR)
    finish(imp)

    mi = instance("MI_SandFall", path, m, {"Speed": 1.0, "Width": 2.5, "Density": 0.65, "Spread": 1.5})
    instance("MI_SandImpact", path, imp, {"Speed": 1.0, "Density": 0.65})
    import_mesh(SRC + "/SM_SandFall.gltf", path + "/Mesh", "SM_SandFall", (10, 10, 0), (10, 10, 0), mi)
    log("sand OK")


# ---------- 3. dissolve ----------

def function(name, path, desc):
    full = f"{path}/{name}"
    f = unreal.load_asset(full) if EAL.does_asset_exist(full) else None
    if f:
        MEL.delete_all_material_expressions_in_function(f)
    else:
        f = AT.create_asset(name, path, unreal.MaterialFunction, unreal.MaterialFunctionFactoryNew())
    B.setp(f, "description", desc)
    B.setp(f, "expose_to_library", True)
    return f


def fn_in(f, name, kind, preview, prio):
    t = B.enum(unreal.FunctionInputType, "FUNCTION_INPUT_" + kind)
    v = preview if isinstance(preview, tuple) else (preview, 0.0, 0.0)
    return node(f, unreal.MaterialExpressionFunctionInput, input_name=name, input_type=t, sort_priority=prio,
                use_preview_value_as_default=True, preview_value=unreal.Vector4(v[0], v[1], v[2], 0.0))


def fn_out(f, name, src, prio):
    o = node(f, unreal.MaterialExpressionFunctionOutput, output_name=name, sort_priority=prio)
    wire(src, o)


def dissolve():
    noise = noise_texture()
    path = VFX + "/Dissolve"
    f = function("MF_SandDissolve", path, "Dissolve any prop into black sand. Material must be Masked. "
                 "Amount 0 = intact, 1 = gone. Wire WorldPositionOffset only if you want the crumble.")
    amount = fn_in(f, "Amount", "SCALAR", 0.5, 0)
    base = fn_in(f, "BaseColor", "VECTOR3", (0.5, 0.5, 0.5), 1)
    rough = fn_in(f, "Roughness", "SCALAR", 0.5, 2)
    scale = fn_in(f, "NoiseScale", "SCALAR", 0.016, 3)      # noise tiles per cm of the object's local space
    edge = fn_in(f, "EdgeWidth", "SCALAR", 0.12, 4)
    crumble = fn_in(f, "CrumbleDistance", "SCALAR", 25.0, 5)  # cm the burn edge sags down (WPO)
    local = node(f, unreal.MaterialExpressionTransformPosition,
                 transform_source_type=B.enum(unreal.MaterialPositionTransformSource, "TRANSFORMPOSSOURCE_WORLD"),
                 transform_type=B.enum(unreal.MaterialPositionTransformSource, "TRANSFORMPOSSOURCE_LOCAL"))
    wire(node(f, unreal.MaterialExpressionWorldPosition), local)
    uv = custom(f, "Skewed local projection", F2, """
// one sample, no stretching on any axis-aligned face (the pattern sticks to the object as it moves)
return float2(P.x + 0.5 * P.y, P.z + 0.7 * P.y) * Scale;""", P=local, Scale=scale)
    n = tex(f, noise, uv)
    core = custom(f, "Threshold + burn edge", F3, """
float t = Amount * (1.0 + Edge) - Edge;          // edge band is empty at Amount 0 and 1
float s = N.g + (N.r - 0.5) * Edge * 0.6;        // grain roughens the boundary
return float3(s > t ? 1.0 : 0.0, saturate(1.0 - (s - t) / Edge), N.r);   // visible, edge, grain""",
                  N=n, Amount=amount, Edge=edge)
    sand_col = custom(f, "Black sand (grainy)", F3, f"return float3{SAND_BLACK} * (0.3 + 1.4 * G);", G=mask(f, core, "b"))
    e = mask(f, core, "g")
    fn_out(f, "BaseColor", lerp(f, base, sand_col, e), 0)
    fn_out(f, "Roughness", lerp(f, rough, 0.15, e), 1)          # the edge is wet, oily
    fn_out(f, "OpacityMask", mask(f, core, "r"), 2)
    fn_out(f, "WorldPositionOffset", custom(f, "Crumble down (WPO)", F3, """
float t = Amount * (1.0 + Edge) - Edge;
float e = saturate(1.0 - (N.g - t) / Edge);      // per vertex: 0 intact .. 1 at / past the edge
return float3(0.0, 0.0, -Crumble * e * e);""", N=n, Amount=amount, Edge=edge, Crumble=crumble), 3)
    MEL.layout_material_function_expressions(f)
    MEL.update_material_function(f)
    EAL.save_loaded_asset(f)

    m = material("M_Demo_SandDissolve", path, blend_mode=MASKED, two_sided=True)
    call = node(m, unreal.MaterialExpressionMaterialFunctionCall)
    call.set_material_function(f)
    wire(sp(m, "Dissolve", 0.45), call, "Amount")
    wire(vp(m, "Color", (0.25, 0.25, 0.25)), call, "BaseColor")
    wire(sp(m, "Roughness", 0.6), call, "Roughness")
    wire(sp(m, "CrumbleDistance", 25.0), call, "CrumbleDistance")
    for pin, prop in (("BaseColor", MP.MP_BASE_COLOR), ("Roughness", MP.MP_ROUGHNESS),
                      ("OpacityMask", MP.MP_OPACITY_MASK), ("WorldPositionOffset", MP.MP_WORLD_POSITION_OFFSET)):
        out((call, pin), prop)
    finish(m)
    instance("MI_Demo_SandDissolve", path, m, {"Dissolve": 0.45})
    log("dissolve OK")


# ---------- 4. glitch ----------

def mpc_vfx():
    full = VFX + "/MPC_VFX"
    mpc = unreal.load_asset(full) if EAL.does_asset_exist(full) else \
        AT.create_asset("MPC_VFX", VFX, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    params = []
    for name in ("GlitchAmount", "TimeShiftAmount"):  # gameplay pulses these (Set Scalar Parameter Value)
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", name)
        p.set_editor_property("default_value", 0.0)
        params.append(p)
    mpc.set_editor_property("scalar_parameters", params)
    EAL.save_loaded_asset(mpc)
    return mpc


GLITCH = """
// Horizontal tear/smear on Custom Stencil 2 (the Nightmare). Bands of rows shred into spikes: each pixel looks
// back along its row for a stencil-2 pixel within the band's smear length and copies it (nearest tap wins).
float3 col = SceneColor.rgb;
if (Amount <= 0.001) return col;
float2 uv = GetViewportUV(Parameters);
float t = floor(Time * Rate);                                         // animated on 'twos', like smear frames
float by = uv.y * Bands;
float h = frac(sin(floor(by) * 12.9898 + t * 78.233) * 43758.5453);    // per band, per step
if (h < 1.0 - Density * saturate(Amount * 2.0)) return col;           // this band holds still
float hr = frac(sin(floor(by * 6.0) * 4.1414 + t * 1.618) * 24634.6345);   // finer rows shred the spike
float prof = 1.0 - abs(frac(by) * 2.0 - 1.0);                         // spike: long mid-band, 0 at its edges
float len = Amount * MaxSmear * ViewSize.x * prof * (0.4 + 0.6 * hr); // smear length, pixels
float dir = frac(h * 37.719) > 0.5 ? 1.0 : -1.0;
float tear = Amount * (hr - 0.5) * 0.03 * ViewSize.x;                  // small row shift inside the body
if (len < 1.0 && abs(Stencil.r - 2.0) < 0.5) return col;
const int TAPS = 10;
[loop] for (int i = 0; i <= TAPS; i++)
{
    float2 o = float2(tear - dir * len * i / TAPS, 0.0);
    if (abs(SceneTextureFetch(PPI_CustomStencil, o).r - 2.0) < 0.5)
        return SceneTextureFetch(PPI_PostProcessInput0, o).rgb * (1.0 - 0.35 * i / TAPS);  // ink darkens to the tip
}
return col;
"""


def glitch():
    mpc = mpc_vfx()
    m = material("M_PP_NightmareGlitch", VFX + "/Glitch", material_domain=unreal.MaterialDomain.MD_POST_PROCESS,
                 blendable_location=B.enum(unreal.BlendableLocation, "BL_SCENE_COLOR_AFTER_TONEMAPPING"),
                 blendable_priority=1)  # after M_PP_DreamMono (priority 0): smears copy the final mono image
    st = lambda i: node(m, unreal.MaterialExpressionSceneTexture, scene_texture_id=B.enum(unreal.SceneTextureId, i))  # noqa: E731
    g = custom(m, "Stencil-2 smear / tear", F3, GLITCH,
               SceneColor=(st("PPI_POST_PROCESS_INPUT0"), "Color"), Stencil=(st("PPI_CUSTOM_STENCIL"), "Color"),
               Amount=node(m, unreal.MaterialExpressionCollectionParameter, collection=mpc, parameter_name="GlitchAmount"),
               Time=node(m, unreal.MaterialExpressionTime), ViewSize=node(m, unreal.MaterialExpressionViewSize),
               MaxSmear=sp(m, "MaxSmear", 0.12), Bands=sp(m, "Bands", 18.0), Rate=sp(m, "Rate", 12.0),
               Density=sp(m, "Density", 0.55))
    out(g, MP.MP_EMISSIVE_COLOR)
    finish(m)
    log("glitch OK")


# ---------- 5. time-shift echoes ----------

def render_target(name, w, h, fmt):
    path = VFX + "/TimeShift"
    full = f"{path}/{name}"
    rt = unreal.load_asset(full) if EAL.does_asset_exist(full) else \
        AT.create_asset(name, path, unreal.TextureRenderTarget2D, unreal.TextureRenderTargetFactoryNew())
    for k, v in (("size_x", w), ("size_y", h), ("render_target_format", fmt),
                 ("clear_color", unreal.LinearColor(0, 0, 0, 1)), ("auto_generate_mips", False)):
        B.setp(rt, k, v)
    EAL.save_loaded_asset(rt)
    return rt


def timeshift():
    mpc = mpc_vfx()
    path = VFX + "/TimeShift"
    F = unreal.TextureRenderTargetFormat
    cap = render_target("RT_TimeShift_Capture", 960, 540, F.RTF_RGBA8)   # half-res SceneCapture2D target
    rt_b = render_target("RT_TimeShift_B", 960, 540, F.RTF_RGBA16F)       # accumulate writes here
    rt_a = render_target("RT_TimeShift_A", 960, 540, F.RTF_RGBA16F)       # copy of B; the post process reads it
    m = material("M_TimeShiftAccumulate", path, shading_model=unreal.MaterialShadingModel.MSM_UNLIT)
    uv = uvs(m)
    cur = tex(m, cap, uv, "Current")
    hist_uv = custom(m, "History UV (per-step drift / zoom)", F2,
                     "return (UV - 0.5) * (1.0 - Zoom) + 0.5 - Drift;",
                     UV=uv, Zoom=sp(m, "StepZoom", 0.0), Drift=mask(m, vp(m, "StepDrift", (0.0, 0.0, 0.0)), "rg"))
    hist = tex(m, rt_a, hist_uv, "History")
    # stepped EMA: updated every ~0.1 s, so the history holds discrete fading copies = multiple exposures
    out(lerp(m, mask(m, cur, "rgb"), mask(m, hist, "rgb"), sp(m, "Persistence", 0.6)), MP.MP_EMISSIVE_COLOR)
    finish(m)
    instance("MI_TimeShiftCopy", path, m, {"Persistence": 0.0}, textures={"Current": rt_b})

    pp = material("M_PP_TimeShift", path, material_domain=unreal.MaterialDomain.MD_POST_PROCESS,
                  blendable_location=B.enum(unreal.BlendableLocation, "BL_SCENE_COLOR_AFTER_TONEMAPPING"),
                  blendable_priority=-1)  # before M_PP_DreamMono, so the echoes go mono with the scene
    scene = node(pp, unreal.MaterialExpressionSceneTexture,
                 scene_texture_id=B.enum(unreal.SceneTextureId, "PPI_POST_PROCESS_INPUT0"))
    duv = custom(pp, "Echo UV (slight live drift)", F2, "return UV + Drift * (0.6 + 0.4 * sin(T * 0.8));",
                 UV=(node(pp, unreal.MaterialExpressionScreenPosition), "ViewportUV"),
                 Drift=mask(pp, vp(pp, "Drift", (0.003, -0.004, 0.0)), "rg"), T=node(pp, unreal.MaterialExpressionTime))
    echo = tex(pp, rt_a, duv, "History")
    amount = op(pp, unreal.MaterialExpressionMultiply,
                node(pp, unreal.MaterialExpressionCollectionParameter, collection=mpc, parameter_name="TimeShiftAmount"),
                sp(pp, "EchoMix", 0.6))
    out(lerp(pp, mask(pp, (scene, "Color"), "rgb"), mask(pp, echo, "rgb"), amount), MP.MP_EMISSIVE_COLOR)
    finish(pp)
    log("timeshift OK")


# ---------- 2. splat meshes ----------

SPLAT_WPO = """
// Tools/Splats/README.md recipe; dissolve progress also drives the gravity drift (scrub back = sand flows up)
float3 right = ResolvedView.ViewToTranslatedWorld[0].xyz;          // camera right (world)
float3 up    = ResolvedView.ViewToTranslatedWorld[1].xyz;          // camera up (world)
float d = Dissolve * (1.0 + Soft) - Soft;                           // 1 = every splat, 0 = none
float p = saturate((Seed - d) / max(Soft, 1e-4));                   // this splat's dissolve progress
float3 wpo = (right * Corner.x + up * Corner.y) * (RadiusCm * RadiusScale * length(ObjZ) * (1.0 - p)); // collapsed = no pixels
float t = p * FallTime;
return wpo + Wind * t - float3(0.0, 0.0, 0.5 * Gravity * t * t);   // UE world: Z up, cm
"""
SPLAT_SH = """
float3 d = normalize(DirLocal).xzy;                 // UE local (x,y,z) -> glTF (x,z,y)
float3 R = float3(SH2.x, SH2.y, SH3.x);
float3 G = float3(SH3.y, SH4.x, SH4.y);
float3 Bv = float3(SH5.x, SH5.y, SH6.x);
return 0.4886025 * float3(dot(R, d), dot(G, d), dot(Bv, d));   // C1; zero for SH-less PLYs
"""
SPLAT_COLOR = """
float3 lin = pow(saturate(Rgb + SH), 2.2);          // 3DGS colors are display space; emissive is linear
float lum = dot(lin, float3(0.2126, 0.7152, 0.0722));
return lerp(lin, Tint + Sheen * lum, Mono);         // FoA: black, keeping a little (view-dependent) luminance as sheen
"""
SPLAT_ALPHA = """
float a = Opacity * exp(-2.0 * dot(Corner, Corner));    // gaussian; quad edge = 2 sigma
float n = InterleavedGradientNoise(Parameters.SvPosition.xy + Seed * 117.0, View.StateFrameIndexMod8);
return a > n ? 1.0 : 0.0;
"""
FALL_TIME, GRAVITY = 0.35, 980.0  # max drop = 0.5 g t^2 = 60 cm


def splat_master():
    path = VFX + "/Splats"
    m = material("M_SplatMesh", path, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, blend_mode=MASKED, two_sided=True)
    uv0, uv1 = uvs(m, 0), uvs(m, 1)
    loop = custom(m, "Loop: materialize <-> dissolve", F1,
                  "return saturate(0.5 + 0.7 * cos(6.2831853 * T / max(Period, 0.01)));",
                  T=node(m, unreal.MaterialExpressionTime), Period=sp(m, "LoopPeriod", 6.0))
    dis = node(m, unreal.MaterialExpressionStaticSwitchParameter, parameter_name="Loop", default_value=False)
    wire(loop, dis, "True")
    wire(sp(m, "Dissolve", 1.0), dis, "False")
    objz = node(m, unreal.MaterialExpressionTransform,
                transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(node(m, unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(0, 0, 1, 0)), objz)
    out(custom(m, "Billboard + dissolve + gravity drift (WPO)", F3, SPLAT_WPO,
               Corner=mask(m, uv0, "rg"), RadiusCm=mask(m, uv1, "r"), Seed=mask(m, uv1, "g"), ObjZ=objz,
               RadiusScale=sp(m, "RadiusScale", 3.0), Dissolve=dis, Soft=sp(m, "DissolveSoftness", 0.15),
               FallTime=sp(m, "FallTime", FALL_TIME), Gravity=sp(m, "Gravity", GRAVITY),
               Wind=mask(m, vp(m, "Wind", (0.0, 0.0, 0.0)), "rgb")),
        MP.MP_WORLD_POSITION_OFFSET)
    wp = node(m, unreal.MaterialExpressionWorldPosition,
              world_position_shader_offset=B.enum(unreal.WorldPositionIncludedOffsets, "WPT_EXCLUDE_ALL_SHADER_OFFSETS"))
    to_local = node(m, unreal.MaterialExpressionTransform,
                    transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                    transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    wire(op(m, unreal.MaterialExpressionSubtract, wp, node(m, unreal.MaterialExpressionCameraPositionWS)), to_local)
    sh = custom(m, "SH degree 1 (vertex)", F3, SPLAT_SH, DirLocal=to_local,
                **{f"SH{i}": mask(m, uvs(m, i), "rg") for i in range(2, 7)})
    vi = node(m, unreal.MaterialExpressionVertexInterpolator)
    wire(sh, vi)
    vc = node(m, unreal.MaterialExpressionVertexColor)
    out(custom(m, "Color: mono tint + sheen", F3, SPLAT_COLOR, Rgb=mask(m, vc, "rgb"), SH=vi,
               Tint=mask(m, vp(m, "Tint", (0.0, 0.0, 0.0)), "rgb"), Sheen=sp(m, "Sheen", 0.25), Mono=sp(m, "Mono", 1.0)),
        MP.MP_EMISSIVE_COLOR)
    out(custom(m, "Gaussian x opacity, dithered", F1, SPLAT_ALPHA, Corner=mask(m, uv0, "rg"),
               Opacity=(vc, "A"), Seed=mask(m, uv1, "g")), MP.MP_OPACITY_MASK)
    return finish(m)


def splats(names=None):
    master = unreal.load_asset(VFX + "/Splats/M_SplatMesh") or splat_master()
    names = names or sorted(f[:-5] for f in os.listdir(SPLAT_SRC) if f.endswith(".gltf"))
    for name in names:
        side = json.load(open(f"{SPLAT_SRC}/{name}.splatmesh.json", encoding="utf-8"))
        rs = side["radius_scale_hint"]
        mi = instance(f"MI_Splat_{name}", VFX + "/Splats", master, {"RadiusScale": rs},
                      switches={"Loop": name == "fear_of_adulthood_clock"})  # the alarm clock keeps (de)materializing
        pad = side["radius_cm"]["max"] * rs + 2.0
        drop = 0.5 * GRAVITY * FALL_TIME ** 2
        import_mesh(f"{SPLAT_SRC}/{name}.gltf", VFX + "/Splats/Meshes", name, (pad, pad, pad), (pad, pad, pad + drop), mi)
        log("splat", name, "RadiusScale", rs)


# ---------- stats ----------

def stats():
    rows = []
    for p in EAL.list_assets(VFX, recursive=True, include_folder=False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.Material):
            s = MEL.get_statistics(a)
            rows.append(f"{a.get_name():<26} VS {s.num_vertex_shader_instructions:>4}  PS {s.num_pixel_shader_instructions:>4}  "
                        f"samplers {s.num_samplers}  tex(PS) {s.num_pixel_texture_samples}  tex(VS) {s.num_vertex_texture_samples}  "
                        f"interp {s.num_interpolator_scalars}")
    print("\n".join(rows))
    return rows


# ---------- test lab (temporary, X >= 4600, outliner folder VFX_Lab) ----------

LAB = "VFX_Lab"


def clear_lab():
    doomed = [a for a in EAS.get_all_level_actors() if str(a.get_folder_path()).startswith(LAB)]
    EAS.destroy_actors(doomed)
    log("lab cleared", len(doomed))


def lab_actor(cls, label, loc, rot=(0, 0, 0)):
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=rot[2], pitch=rot[1], yaw=rot[0]))
    a.set_actor_label(label)
    a.set_folder_path(LAB)
    return a


def lab_mesh(label, mesh, loc, scale=(1, 1, 1), yaw=0.0, mat=None):
    a = lab_actor(unreal.StaticMeshActor, label, loc, (yaw, 0, 0))
    c = a.get_editor_property("static_mesh_component")
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_static_mesh(unreal.load_asset(mesh) if isinstance(mesh, str) else mesh)
    a.set_actor_scale3d(unreal.Vector(*scale))
    if mat:
        for i in range(max(1, c.get_num_materials())):
            c.set_material(i, mat)
    return a


def lab_light(label, loc, lumens, temp=3200.0, radius=700.0):
    a = lab_actor(unreal.PointLight, label, loc)
    c = a.get_editor_property("point_light_component")
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    B.setp(c, "intensity_units", unreal.LightUnits.LUMENS)
    for k, v in (("intensity", lumens), ("use_temperature", True), ("temperature", temp), ("attenuation_radius", radius),
                 ("source_radius", 5.0)):
        B.setp(c, k, v)
    return a


def lab_cam(label, loc, target, fov=50.0):
    rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*target))
    a = lab_actor(unreal.CameraActor, label, loc)
    a.set_actor_rotation(rot, False)
    B.setp(a.get_editor_property("camera_component"), "field_of_view", fov)
    return a


def lab():
    clear_lab()
    M = lambda n: unreal.load_asset("/Game/FoA/Materials/" + n)  # noqa: E731  (read-only use of bedroom materials)
    V = lambda p: unreal.load_asset(VFX + p)  # noqa: E731
    B.place("VFXLab_Floor", LAB, (6500, 0, -10), (3800, 800, 20), M("MI_Floor_OldWood"))
    B.place("VFXLab_Wall", LAB, (6500, 315, 150), (3800, 30, 300), M("MI_Wall_Plaster"))

    # 1. sand fall: a stand-in for the bedroom commode (same top, front edge and mound), shifted +5150 in X
    ox = 5150.0
    B.place("VFXLab_Commode", LAB, (-149.9 + ox, 268.9, 60.6), (120.2, 58.0, 121.2), M("MI_Wood_Dark"))
    mound = lambda k: f"/Game/FoA/Procedural/SM_SandMound_{k}/SM_SandMound_{k}/StaticMeshes/SM_SandMound_{k}"  # noqa: E731
    lab_mesh("VFXLab_Mound", mound("A"), (-150.0 + ox, 266.0, 121.2),
             (0.42, 0.42, 0.42), 343.0, M("MI_DarkSand_Black"))
    lab_mesh("VFXLab_SandFall", V("/Sand/Mesh/SM_SandFall"), (-150.0 + ox, 238.5, 121.4), (1, 1, 1.214),
             mat=V("/Sand/MI_SandFall")).get_editor_property("static_mesh_component").set_cast_shadow(False)
    lab_mesh("VFXLab_Heap", mound("C"), (-150.0 + ox, 238.5, 0.0),
             (0.16, 0.16, 0.16), 0.0, M("MI_DarkSand_Black"))
    lab_mesh("VFXLab_Impact", "/Engine/BasicShapes/Plane.Plane", (-150.0 + ox, 238.5, 0.4), (0.34, 0.34, 1.0),
             mat=V("/Sand/MI_SandImpact")).get_editor_property("static_mesh_component").set_cast_shadow(False)
    lab_light("VFXLab_SandKey", (ox - 70, 120, 210), 600.0)
    lab_light("VFXLab_SandRim", (ox - 230, 200, 60), 150.0, 4500.0)
    lab_cam("VFXLab_Cam_SandFall", (ox, 69, 95), (ox - 150, 245, 60), 60.0)
    lab_cam("VFXLab_Cam_SandClose", (ox - 90, 194, 115), (ox - 150, 239, 95), 45.0)
    lab_cam("VFXLab_Cam_SandImpact", (ox - 80, 169, 45), (ox - 150, 239, 2), 50.0)
    log("lab built")
