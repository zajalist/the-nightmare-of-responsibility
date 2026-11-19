"""Creates/updates the sand VFX material instances of M_SplatMesh from P:/FoA-Assets/splatmesh/sand_vfx_params.json
(written by make_sand_splats.py), so geometry constants never drift from the meshes they describe.

  python Tools/Unreal/ue_remote.py Tools/Splats/sand_instances.py

Packed parameters (see the comment boxes in M_SplatMesh / MF_SplatFlow):
  Mode     0 stream, 1 mound, 2 assemble, 3 static
  TimeCfg  (dream time scale, time offset s, shutter s (<= 0: no streaks), loop period s)
  Flow     (wind xyz cm/s mesh-local, curl turbulence cm)
  Shape    mound() constants (apex, 6 rnd1, 6 rnd2, 6 rnd3);  Place (centre x, y, scale, yaw rad) in mesh-local
  Tune     stream (drop, throw cm/s, slide cm, slide height) | mound (avalanche cm/s, breath cm, wisp rise cm/s,
           wisp growth) | assemble (mound base z, vent radius, object height, vents)
  Splat    (radius scale, min width px, gaussian hardness, density: the share of splats kept, survivors grown by
           density^-1/4);  Light (key light world pos, emissive rim intensity; keep low on broad silhouettes)
  Sand     (albedo, glint share, goo roughness, grain normal jitter): pitch-black goo lit by the real lights
"""
import json

import unreal

P = json.load(open("P:/FoA-Assets/splatmesh/sand_vfx_params.json", encoding="utf-8"))
MEL, EAL = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
DIR = "/Game/FoA/VFX/Splats/Instances"
DESK_LAMP, MOON_BAY, HALLWAY = (-330.5, 151.0, 123.0), (-60.0, -520.0, 240.0), (435.0, 87.5, 40.0)
SAND = (0.015, 0.002, 0.4, 0.3)  # albedo, glint share (a few pin-point flashes a second per mound), roughness, grain jitter

clock_wind = (0.0, 0.0, 0.0)
INST = {
    "MI_Sand_Stream": {"Mode": 0, "TimeCfg": (0.45, 0.0, 0.02, 2.6), "Flow": (0.0, 0.0, 0.0, 1.0),
                       "Shape": P["stream"]["Shape"], "Place": P["stream"]["Place"], "Tune": P["stream"]["Tune"],
                       "Splat": (0.8, 1.0, 2.0, 0.7), "Light": (*DESK_LAMP, 3.3), "Sand": SAND,  # fine grains: ~1/3 the area of the first goo pass
                       "Spec": 0.17},  # a thin pour is all silhouette: a third of the spill's rim and specular, or it reads white
    "MI_Sand_Clock": {"Mode": 2, "TimeCfg": (1.0, 0.0, 0.025, 12.0), "Flow": (*clock_wind, 1.5),
                      "Shape": P["clock"]["Shape"], "Place": P["clock"]["Place"], "Tune": P["clock"]["Tune"],
                      "Splat": (2.2, 0.9, 1.0, 0.8), "Light": (*DESK_LAMP, 8.0), "Sand": SAND, "masked": True},  # 32k of 40k, finer: ~12 layers, not 32
}
# The night mare (mech_flow plays it at the day rollover, drives the scalar "Dissolve" 0 -> 1 on a MID).
# Gallop in place: stride 0.9 s (a real gallop is ~0.45 s: dream slow motion), 45 cm leg swing, 6 cm bob, 2.75 m tall,
# 35% of the mane/tail splats loop off as tendrils. Light from above the room centre: its placement is mech_flow's.
INST["MI_Splat_NightMare"] = {"Mode": 4, "TimeCfg": (1.0, 0.0, 0.02, 0.9), "Flow": (0.0, 0.0, 0.0, 6.0),
                              "Shape": (24.0, 0.0, 0.0, 0.0), "Place": (0.0, 0.0, 1.0, 0.0), "Tune": (45.0, 6.0, 275.0, 0.35),
                              "Splat": (2.49, 1.0, 1.8, 1.0), "Light": (0.0, 0.0, 280.0, 5.0), "Sand": SAND,
                              "mesh": "/Game/FoA/VFX/Splats/Meshes/SM_TheNightMare"}
# Pooled bursts and steps (BP_SandFX, Mode 5): SandEvent comes from the component; Tune = (speed, up bias, gravity,
# dust lift). Face drift (Mode 6): Flow.xyz = local acceleration for the head socket's axes, w curl.
CEILING = (0.0, -45.0, 290.0)
INST["MI_Sand_Burst"] = {"Mode": 5, "TimeCfg": (1.0, 0.0, 0.02, 1.0), "Flow": (0.0, 0.0, 0.0, 3.0), "Shape": (24.0, 0.0, 0.0, 0.0),
                         "Place": (0.0, 0.0, 1.0, 0.0), "Tune": (1.0, 0.6, 1.0, 10.0), "Splat": (1.6, 1.0, 2.0, 1.0),
                         "Light": (*CEILING, 10.0), "Sand": SAND}
INST["MI_Sand_Step"] = {**INST["MI_Sand_Burst"], "Flow": (0.0, 0.0, 0.0, 1.5), "Tune": (0.35, 0.15, 1.0, 4.0),
                        "Splat": (1.4, 1.0, 2.0, 1.0)}
INST["MI_Sand_FaceDrift"] = {"Mode": 6, "Glitch": 0.24, "TimeCfg": (1.0, 0.0, -1.0, 3.2), "Flow": (-4.0, 0.0, -7.0, 1.2),
                             "Shape": (24.0, 0.0, 0.0, 0.0), "Place": (0.0, 0.0, 1.0, 0.0), "Tune": (0.0, 0.0, 0.0, 0.0),
                             "Splat": (1.4, 1.0, 2.0, 1.0), "Light": (*CEILING, 8.0), "Sand": SAND,
                             "mesh": "/Game/FoA/VFX/Splats/Meshes/SM_SandFaceDrift"}
# The wake-up alarm clock (Lux3D alarm_clock_splat, 12k of 828k splats): formed and still (Mode 3) until
# BP_SandMaterialize.Dissolve crumbles it in the hand. Tune.z = its height (centre-ray normals); 60% density, 13 layers.
INST["MI_Sand_AlarmClock"] = {"Mode": 3, "TimeCfg": (1.0, 0.0, 0.02, 12.0), "Flow": (0.0, 0.0, 0.0, 1.5),
                              "Shape": (24.0, 0.0, 0.0, 0.0), "Place": (0.0, 0.0, 1.0, 0.0), "Tune": (0.0, 0.0, 42.1, 0.0),
                              "Splat": (2.6, 0.9, 1.0, 0.9), "Light": (*CEILING, 8.0), "Sand": SAND,
                              "mesh": "/Game/FoA/VFX/Splats/Meshes/SM_AlarmClockSplats/SM_AlarmClockSplats/StaticMeshes/SM_AlarmClockSplats"}
# Blooms (Mode 7, BP_SandFX pool): a puddle wells up, spreads, holds, recedes or crumbles; reuses mound mesh B and its
# mound() constants. Tune = (dome height cm, -, strand reach cm, -); SandEvent from BP_SandFX.Bloom.
_mb = next(m for m in P["mounds"].values() if m["mesh"].endswith("_B"))
INST["MI_Sand_Bloom"] = {"Mode": 7, "TimeCfg": (1.0, 0.0, -1.0, 10.0), "Flow": (0.0, 0.0, 0.0, 1.2), "Shape": _mb["Shape"],
                         "Place": _mb["Place"], "Tune": (6.0, 0.0, 10.0, 0.0), "Splat": (0.9, 1.0, 1.8, 1.0),
                         "Light": (*CEILING, 8.0), "Sand": SAND}
# Crumbs (Mode 1, creep role): loose grains around the floor spills, 0.5-2 px at 1080p, inching along the boards.
# Place.z ~ 0 flattens mound() to the floor; no avalanche, breath or strands.
INST["MI_Sand_Crumbs"] = {"Mode": 1, "TimeCfg": (1.0, 0.0, -1.0, 10.0), "Flow": (2.0, 1.0, 0.0, 0.3), "Shape": (0.0, 0.0, 0.0, 0.0),
                          "Place": (0.0, 0.0, 0.001, 0.0), "Tune": (0.0, 0.0, 0.0, 0.0), "Splat": (1.0, 0.5, 1.8, 1.0),
                          "Light": (-60.0, -900.0, 140.0, 10.0), "Sand": SAND}
LIGHTS = {"OnCommode": DESK_LAMP, "Bay": MOON_BAY, "Hearth": (-120.0, -430.0, 220.0), "Path": HALLWAY}
for k, (label, m) in enumerate(P["mounds"].items()):
    INST[f"MI_Sand_Mound_{label}"] = {
        "Mode": 1, "TimeCfg": (1.0, 3.7 * k, -1.0, 10.0), "Flow": (*[0.3 * w for w in m["Flow_wind_local"][:3]], 1.5),
        "Shape": m["Shape"], "Place": m["Place"], "Tune": (1.2, 1.5, 16.0, 0.0),  # slump cm/s, bulge cm, strand reach cm
        "Splat": (0.8, 1.0, 1.8, 1.0), "Light": (*LIGHTS[label], 10.0), "Sand": SAND}  # fine grains; the mound mesh fills any gap

def run():
    PARENT = unreal.load_asset("/Game/FoA/VFX/Splats/M_SplatMesh")
    for name, v in INST.items():
        path = f"{DIR}/{name}"
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, PARENT)
        MEL.set_material_instance_scalar_parameter_value(mi, "Mode", float(v["Mode"]))
        if 'Glitch' in v:
            MEL.set_material_instance_scalar_parameter_value(mi, "Glitch", float(v['Glitch']))
        MEL.set_material_instance_scalar_parameter_value(mi, "Specular", float(v.get("Spec", 0.5)))
        for p in ("TimeCfg", "Flow", "Shape", "Place", "Tune", "Splat", "Light", "Sand"):
            MEL.set_material_instance_vector_parameter_value(mi, p, unreal.LinearColor(*[float(x) for x in v[p]]))
        o = mi.get_editor_property("base_property_overrides")
        # every sand instance renders dithered Masked: it writes custom depth / stencil 5 (the sand-only post pass),
        # sorts against itself and gives TSR velocities; the master's Translucent default stays for previews
        o.set_editor_property("override_blend_mode", True)
        o.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        mi.set_editor_property("base_property_overrides", o)
        MEL.update_material_instance(mi)
        EAL.save_asset(path, only_if_is_dirty=False)
        if v.get("mesh") and EAL.does_asset_exist(v["mesh"]):  # soft-referenced mesh renders right with no extra setup
            m = unreal.load_asset(v["mesh"])
            m.set_material(0, mi)
            EAL.save_asset(v["mesh"], only_if_is_dirty=False)
        print(name, "ok")


run()  # in a function: no asset wrappers left behind
