"""Intro panel layers (lookdev lane): stage a shot, then capture it as separate layers with alpha. Runs INSIDE the
open editor, one panel per run; every temporary actor (staged props, the capture) is TMP_lookdev_* and destroyed
before the run returns.
  python Tools/Unreal/ue_remote.py Tools/LookDev/capture_layers.py NAME=Test POSE=x,y,z,pitch,yaw,fov
      LAYERS='{"near": ["Boot_"], "mid": ["Bed"], "fx": ["LightShaft_"], "far": "rest"}'
      [STAGE='[{"asset": "/Game/...", "loc": [x,y,z], "yaw": 0, "height": 210, "anim": "/Game/...", "anim_t": 0.5,
               "layer": "mid"}]'] [SIZE=2304x1296]
ONLY=stage only stages (a posed skeletal figure needs one editor tick); the next run reuses the staged actors,
captures (ONLY=mid,far or all) and destroys them. Layers list actor-label prefixes; "rest" renders everything not claimed by another layer. Per layer it writes
<NAME>_<layer>_{color,alpha,depth,normal,base}_0.exr to Saved/LookDev/panels/layers_src: colour is SCS_FinalColorHDR
(TSR-resolved), alpha is 1 - the inverse opacity of SCS_SceneColorHDR. Show flags as capture_passes.py (no PP materials)."""
import json
import os

import unreal

E = {k: os.environ.pop(k) for k in ("NAME", "POSE", "LAYERS", "STAGE", "SIZE", "OUT", "ONLY") if k in os.environ}
OUT = E.get("OUT", "P:/FoA/Saved/LookDev/panels/layers_src")
W, H = (int(v) for v in E.get("SIZE", "2304x1296").split("x"))
OFF = ("PostProcessMaterial", "Grain", "Vignette", "Bloom", "LensFlares", "SceneColorFringe", "MotionBlur", "DepthOfField")


def run():
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        print("PIE_ACTIVE: another lane is playing; nothing staged, retry later")  # editor actor calls refuse in PIE
        return
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    x, y, z, pitch, yaw, fov = (float(v) for v in E["POSE"].split(","))
    layers = json.loads(E["LAYERS"])
    temp = []
    try:
        existing = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
        for s in json.loads(E.get("STAGE", "[]")):  # staged props: spawned, sized, posed; reused by a later run
            label = "TMP_lookdev_" + s["asset"].rsplit("/", 1)[-1]
            a = existing.get(label)
            if a is None:
                a = eas.spawn_actor_from_object(unreal.load_asset(s["asset"]), unreal.Vector(*s["loc"]),
                                                unreal.Rotator(roll=0.0, pitch=0.0, yaw=s.get("yaw", 0.0)))
                a.set_actor_label(label)
                if s.get("anim"):  # a skeletal figure holds one animation frame; the editor tick applies the pose,
                    sk = a.get_editor_property("skeletal_mesh_component")  # so stage in one run, capture in the next
                    sk.set_update_animation_in_editor(True)
                    sk.override_animation_data(unreal.load_asset(s["anim"]), True, False, s.get("anim_t", 0.0), 0.0)
                    sk.set_position(s.get("anim_t", 0.0), False)  # single-node SetPosition ticks and refreshes the pose
                if s.get("height"):
                    _o, ext = a.get_actor_bounds(False)
                    a.set_actor_scale3d(unreal.Vector(1, 1, 1) * (s["height"] / max(2 * ext.z, 1.0)))
                    o, ext = a.get_actor_bounds(False)  # stand it on the floor
                    a.set_actor_location(a.get_actor_location() + unreal.Vector(0, 0, s["loc"][2] - (o.z - ext.z)),
                                         False, False)
            if E.get("ONLY") != "stage":
                temp.append(a)  # destroyed when this run ends
            layers.setdefault(s["layer"], []).append(label)
            print("staged", label, a.get_actor_bounds(False))
        if E.get("ONLY") == "stage":
            return
        actors = [a for a in eas.get_all_level_actors() if not isinstance(a, unreal.SceneCapture2D)]
        claimed = {}
        for name, prefixes in layers.items():
            if prefixes != "rest":
                claimed[name] = [a for a in actors if any(a.get_actor_label().startswith(p) for p in prefixes)]
                print(name, len(claimed[name]), sorted(a.get_actor_label() for a in claimed[name])[:12])
        taken = [a for v in claimed.values() for a in v]
        cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(x, y, z),
                                         unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
        cap.set_actor_label("TMP_lookdev_Capture")
        temp.append(cap)
        c = cap.capture_component2d
        flags = []
        for n in OFF:
            f = unreal.EngineShowFlagsSetting()
            f.set_editor_property("show_flag_name", n)
            f.set_editor_property("enabled", False)
            flags.append(f)
        for k, v in (("capture_every_frame", False), ("capture_on_movement", False), ("fov_angle", fov),
                     ("always_persist_rendering_state", True), ("show_flag_settings", flags)):
            c.set_editor_property(k, v)
        F, S, M = unreal.TextureRenderTargetFormat, unreal.SceneCaptureSource, unreal.SceneCapturePrimitiveRenderMode
        passes = [("color", F.RTF_RGBA16F, S.SCS_FINAL_COLOR_HDR, 12), ("alpha", F.RTF_RGBA16F, S.SCS_SCENE_COLOR_HDR, 2),
                  ("depth", F.RTF_RGBA32F, S.SCS_SCENE_DEPTH, 2), ("normal", F.RTF_RGBA16F, S.SCS_NORMAL, 2),
                  ("base", F.RTF_RGBA16F, S.SCS_BASE_COLOR, 2)]
        for name, prefixes in layers.items():
            if E.get("ONLY") and name not in E["ONLY"].split(","):  # one layer per run keeps each run under ~30 s
                continue
            c.clear_show_only_components()  # the actor lists are weak pointers Python can't set: use the calls
            c.clear_hidden_components()
            if prefixes == "rest":
                c.set_editor_property("primitive_render_mode", M.PRM_RENDER_SCENE_PRIMITIVES)
                for a in taken:
                    c.hide_actor_components(a)
            else:
                c.set_editor_property("primitive_render_mode", M.PRM_USE_SHOW_ONLY_LIST)
                for a in claimed[name]:
                    c.show_only_actor_components(a)
            for p, fmt, src, settle in passes:
                c.set_editor_property("texture_target", unreal.RenderingLibrary.create_render_target2d(world, W, H, fmt))
                c.set_editor_property("capture_source", src)
                for _ in range(settle):
                    c.capture_scene()
                unreal.RenderingLibrary.export_render_target(world, c.get_editor_property("texture_target"), OUT,
                                                             f"{E['NAME']}_{name}_{p}_0.exr")
            print("layer", name, "written")
    finally:
        for a in temp:
            eas.destroy_actor(a)
        print("destroyed", len(temp), "temporary actors")


run()
