"""Anim lane groom diagnosis (editor world, nothing saved): four TMP_anim_ copies of BP_FoAPlayer, each with a different
groom LOD forced, head shots of each to Saved/AnimShots/gv_<n>.png, then everything TMP_anim_ is destroyed.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/groom_variants.py FOA_ACTORS_NEW=TMP_anim_
v0 ours as built | v1 BP_MHC_Protagonist turned yaw 270 | v2 ours, Face on the capsule | v3 ours, body mesh unrotated"""
import math
import time

import unreal

OUT = "P:/FoA/Saved/AnimShots"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
BASE = unreal.Vector(-200.0, 0.0, -3000.0)  # 30 m under the floor: out of every shot (cine renders the level)
assert time.localtime().tm_min % 10 > 3, "minutes :x0-:x3 are cine's MRQ windows (PIE copies the editor world): wait"


def sweep():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith("TMP_anim_"):
            EAS.destroy_actor(a)


def _variant(i, p, face, body):
    if i == 2:  # Face (and its grooms) re-parented from CharacterMesh0 to the capsule, same world transform
        face.attach_to_component(p.get_root_component(), "", unreal.AttachmentRule.KEEP_WORLD,
                                 unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    if i == 3:  # the body mesh unrotated (yaw 0 instead of 270)
        body.set_editor_property("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0))


sweep()
try:
  world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
  cls = unreal.EditorAssetLibrary.load_blueprint_class("/Game/FoA/Characters/Player/BP_FoAPlayer")
  pawns = []
  MHC = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/"
  mh_cls = unreal.EditorAssetLibrary.load_blueprint_class(MHC + "BP_MHC_Protagonist")
  ch02 = unreal.LightingChannels(channel0=True, channel1=False, channel2=True)
  print("GV groom api", [n for n in dir(unreal.GroomComponent) if "sim" in n.lower() or "reset" in n.lower()])
  for i in range(4):  # our BP_FoAPlayer; each copy changes how the body is posed
      if i == 1:  # the working MetaHuman BP, turned like our mesh (yaw 270)
          p = EAS.spawn_actor_from_class(mh_cls, BASE + unreal.Vector(0, i * 90.0, 0), unreal.Rotator(0, 270, 0))
          p.set_actor_label(f"TMP_anim_V{i}")
          pawns.append(p)
          continue
      p = EAS.spawn_actor_from_class(cls, BASE + unreal.Vector(0, i * 90.0, 90), unreal.Rotator(0, 0, 0))
      p.set_actor_label(f"TMP_anim_V{i}")
      sk = {c.get_name(): c for c in p.get_components_by_class(unreal.SkeletalMeshComponent)}
      face, body = sk["Face"], sk["CharacterMesh0"]
      try:
        _variant(i, p, face, body)
      except Exception as e:
        print("GV variant", i, "failed", repr(e))
      pawns.append(p)
  cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, BASE, unreal.Rotator())
  cap.set_actor_label("TMP_anim_Cap")
  lt = EAS.spawn_actor_from_class(unreal.PointLight, BASE + unreal.Vector(150, 130, 200), unreal.Rotator())
  lt.set_actor_label("TMP_anim_Light")
  lt.point_light_component.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
  lt.point_light_component.set_editor_property("intensity", 40.0)
  lt.point_light_component.set_editor_property("attenuation_radius", 700.0)
  comp = cap.capture_component2d
  rt = unreal.RenderingLibrary.create_render_target2d(world, 640, 640, unreal.TextureRenderTargetFormat.RTF_RGBA8)
  comp.set_editor_property("texture_target", rt)
  comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
  comp.set_editor_property("capture_every_frame", False)
  comp.set_editor_property("always_persist_rendering_state", True)
  comp.set_editor_property("fov_angle", 35)
  pp = comp.get_editor_property("post_process_settings")
  for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
               ("override_auto_exposure_apply_physical_camera_exposure", True),
               ("auto_exposure_apply_physical_camera_exposure", False), ("override_auto_exposure_bias", True),
               ("auto_exposure_bias", 2.0)):
      pp.set_editor_property(k, v)
  comp.set_editor_property("post_process_settings", pp)
except Exception:
    sweep()
    raise
st = {"t0": time.time(), "h": None, "busy": False}


def tick(_dt):
    if st["busy"] or time.time() - st["t0"] < 7:
        return
    st["busy"] = True
    unreal.unregister_slate_post_tick_callback(st["h"])
    try:
        for i, p in enumerate(pawns):
            head = p.get_actor_location() + unreal.Vector(0, 0, 72 if i != 1 else 162)
            frm = head + unreal.Vector(math.cos(0.3) * 110, math.sin(0.3) * 110, 10)
            cap.set_actor_location_and_rotation(frm, unreal.MathLibrary.find_look_at_rotation(frm, head), False, True)
            for _ in range(3):
                comp.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"gv_{i}.png")
            print("GV", i, "head", head)
    finally:
        sweep()
        print("GV done")


st["h"] = unreal.register_slate_post_tick_callback(tick)
print("GV scheduled")
