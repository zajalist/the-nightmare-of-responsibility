"""Render proof for M_OpponentSway (it must not fall back to the default material). Two short steps, editor world:
  FOA_STEP=spawn    TMP_gameplay_SwayProbe: an engine cylinder with M_OpponentSway, tint in custom primitive data 1-3
  (then Hayba wait_for_shaders)
  FOA_STEP=shoot    two SceneCapture2D frames 0.5 s apart -> Saved/EncounterCaptures/sway_probe_{0,1}.png, then every
                    TMP_gameplay_ actor (probe and capture) is destroyed
Run each with FOA_ACTORS_NEW=TMP_gameplay_."""
import os
import time

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OUT = "P:/FoA/Saved/EncounterCaptures"
LOC = unreal.Vector(-60.0, 120.0, 60.0)  # open floor between the bed and the desk


def spawn():
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, LOC, unreal.Rotator(0, 0, 0))
    a.set_actor_label("TMP_gameplay_SwayProbe")
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cylinder"))
    c.set_material(0, unreal.load_asset("/Game/FoA/Gameplay/Encounter/M_OpponentSway"))
    a.set_actor_scale3d(unreal.Vector(0.6, 0.6, 1.2))
    for i, v in enumerate((1.0, 1.0, 1.0)):
        c.set_custom_primitive_data_float(1 + i, v)
    print("probe", a.get_actor_label(), c.get_material(0).get_name())


def shoot():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rt = unreal.RenderingLibrary.create_render_target2d(world, 960, 540, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, LOC + unreal.Vector(-170.0, 0.0, 10.0),
                                     unreal.Rotator(roll=0.0, pitch=-3.0, yaw=0.0))
    cap.set_actor_label("TMP_gameplay_SwayCapture")
    c = cap.capture_component2d
    for k, v in (("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR),
                 ("capture_every_frame", False), ("fov_angle", 50.0)):
        c.set_editor_property(k, v)
    for i in range(2):
        c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"sway_probe_{i}.png")
        time.sleep(0.5)
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_gameplay_"):
            EAS.destroy_actor(a)
    print("shot", OUT + "/sway_probe_0.png", "left", [a.get_actor_label() for a in EAS.get_all_level_actors()
                                                      if a.get_actor_label().startswith("TMP_gameplay_")])


{"spawn": spawn, "shoot": shoot}[os.environ.get("FOA_STEP", "spawn")]()
