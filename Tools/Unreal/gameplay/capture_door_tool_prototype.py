"""Native editor prototype frames: actual shipping door/tool components/camera. Does not claim hand/runtime proof.
Restores the tool component and destroys the temporary capture; no level/asset writes.
"""
import json
from pathlib import Path
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eas.select_nothing()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
door = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == 'Door_Bedroom')
parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
tool, pivot, camera = parts['ToolMesh'], parts['ToolPivot'], parts['ToolCamera']
defaults = unreal.get_default_object(door.get_class())
saved = dict(mesh=tool.get_editor_property('static_mesh'), transform=tool.get_relative_transform(),
             visible=tool.get_editor_property('visible'), pivot=pivot.get_relative_transform())
made = []
out = Path('P:/FoA/Saved/Integration/door_tools')
out.mkdir(parents=True, exist_ok=True)
try:
    capture = eas.spawn_actor_from_class(unreal.SceneCapture2D, camera.get_world_location(), camera.get_world_rotation())
    capture.set_actor_label('TMP_toolproof_Capture'); made.append(capture)
    comp = capture.capture_component2d
    comp.capture_every_frame = False
    comp.capture_on_movement = False
    comp.always_persist_rendering_state = True
    comp.fov_angle = camera.field_of_view
    comp.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1600, 1000, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    comp.texture_target = rt
    for name, meshvar, transformvar in (('key', 'ToolKeyMesh', 'ToolKeyTransform'), ('screwdriver', 'ToolDriverMesh', 'ToolDriverTransform')):
        tool.set_static_mesh(defaults.get_editor_property(meshvar))
        tool.set_relative_transform(defaults.get_editor_property(transformvar), False, True)
        tool.set_visibility(True, False)
        for _ in range(12):
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, str(out), 'prototype_' + name + '.png')
    (out / 'prototype_geometry.json').write_text(json.dumps(dict(actual_shipping_components=True, hands_rendered=False,
        runtime_input_verified=False, camera=str(camera.get_world_location()), contact=str(parts['ToolContact'].get_world_location())), indent=1))
    print('DOOR_NATIVE_PROTOTYPE', str(out), 'geometry/camera only; hands/input require PIE proof')
finally:
    tool.set_static_mesh(saved['mesh'])
    tool.set_relative_transform(saved['transform'], False, True)
    tool.set_visibility(saved['visible'], False)
    pivot.set_relative_transform(saved['pivot'], False, True)
    eas.select_nothing()
    for a in made:
        eas.destroy_actor(a)
