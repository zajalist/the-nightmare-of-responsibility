"""Credits lane look-dev: one TMP BP_CreditsShowcase in the editor world 1 km above the map captures Lux3D meshes at a
few angles through its own capture and exports each frame as .hdr (linear scene colour; alpha in alpha.json), then is
destroyed in the same run. CaptureScene pushes end-of-frame render updates first, so each pose is captured at once.
  FOA_ACTORS_NEW=TMP_credits_ python Tools/Unreal/ue_remote.py Tools/Unreal/ui/credits_showcase_lookdev.py
      [FOA_OUT=<dir>] [FOA_ANGLES=0,120] [FOA_KEY=<cd>] [FOA_RIM=<cd>] [FOA_ONLY=<mesh name substring>,...]"""
import json
import math
import os

import unreal

OUT = os.environ.get('FOA_OUT', 'P:/FoA/Saved/Credits/lookdev')
ANGLES = [float(a) for a in os.environ.get('FOA_ANGLES', '0,120').split(',')]
ONLY = [s for s in os.environ.get('FOA_ONLY', '').split(',') if s]
LIGHTS = {n: float(os.environ[e]) for n, e in (('Key', 'FOA_KEY'), ('Rim', 'FOA_RIM')) if os.environ.get(e)}
FIT = 48.0
SIZE = int(os.environ.get('FOA_SIZE', '768'))
os.makedirs(OUT, exist_ok=True)


def axis(i):
    x, y = math.sin(i * 2.3) * 0.6, math.cos(i * 1.7) * 0.6
    return unreal.Vector(x, y, 1.0).normal()


def named(actor, cls, name):  # by name: in the editor the capture also owns a StaticMeshComponent (its camera proxy)
    return next(c for c in actor.get_components_by_class(cls) if c.get_name() == name)


def run():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cls = unreal.load_object(None, '/Game/FoA/UI/Credits/BP_CreditsShowcase.BP_CreditsShowcase_C')
    a = eas.spawn_actor_from_class(cls, unreal.Vector(0, 0, 100000), unreal.Rotator(0, 0, 0))
    rows = {}
    try:
        a.set_actor_label('TMP_credits_showcase')
        hero = named(a, unreal.StaticMeshComponent, 'Hero')
        cap = named(a, unreal.SceneCaptureComponent2D, 'Capture')
        if os.environ.get('FOA_SHADOWS') == '0':
            named(a, unreal.RectLightComponent, 'Key').set_cast_shadows(False)
        for name, value in LIGHTS.items():
            named(a, unreal.RectLightComponent, name).set_intensity(value)
        rt = unreal.RenderingLibrary.create_render_target2d(world, SIZE, SIZE, unreal.TextureRenderTargetFormat.RTF_RGBA16F,
                                                            unreal.LinearColor(0, 0, 0, 1))
        # NEVER notify: a notified edit re-runs the Blueprint's construction script and leaves these handles stale
        cap.set_editor_property('texture_target', rt, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        cap.show_only_component(hero)
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        meshes = sorted(str(x.package_name) for x in reg.get_assets_by_path('/Game/FoA/Lux3D', recursive=True)
                        if str(x.asset_class_path.asset_name) == 'StaticMesh')
        meshes = [m for m in meshes if not ONLY or any(s in m for s in ONLY)]
        for n, path in enumerate(meshes):
            mesh = unreal.load_asset(path)
            hero.set_static_mesh(mesh)
            fit = FIT / mesh.get_bounds().sphere_radius
            hero.set_relative_scale3d(unreal.Vector(fit, fit, fit))
            for angle in ANGLES:
                hero.set_relative_rotation(unreal.MathLibrary.rotator_from_axis_and_angle(axis(n), angle + n * 67), False, True)
                cap.capture_scene()
                name = path.rsplit('/', 1)[1].replace('SM_Lux3D_', '') + '_%03d' % angle
                unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + '.hdr')
                mid = unreal.RenderingLibrary.read_render_target_raw_pixel(world, rt, SIZE // 2, SIZE // 2)
                rows[name] = [round(v, 3) for v in (mid.r, mid.g, mid.b, mid.a)]
    finally:
        a.destroy_actor()
    rows['_left_behind'] = [x.get_actor_label() for x in eas.get_all_level_actors() if x.get_actor_label().startswith('TMP_credits_')]
    with open(OUT + '/alpha.json', 'w') as fh:
        json.dump(rows, fh, indent=1)
    print('lookdev frames', len(rows) - 1, 'TMP left', rows['_left_behind'])


run()
