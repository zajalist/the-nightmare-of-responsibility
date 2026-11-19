"""Editor-world look at SM_Jumpscare_Monster in the jumpscare framing. Spawns TMP_horror_* actors (the monster, its two
lights, a SceneCapture2D), shoots, then destroys them all. PNGs go to Saved/HorrorShots/monster/<FOA_TAG>_*.png.
  $env:FOA_ACTORS_NEW='TMP_horror_'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/shoot_monster.py FOA_TAG=look_a
Env: FOA_MAT (material for slot 0), FOA_OVERLAY (overlay material), FOA_DIST (camera to pivot cm, default 38),
FOA_KEY / FOA_RIM ('fwd,right,up,candela' in camera space, the same numbers BP_Jumpscare uses), FOA_FOV (default 78).
The monster's front is +Y, so the camera sits on +Y looking -Y; 'sides' also shoots the four sides."""
import os

import unreal

OUT = 'P:/FoA/Saved/HorrorShots/monster'
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MESH = '/Game/FoA/Gameplay/Jumpscare/SM_Jumpscare_Monster'
SAND = '/Game/FoA/Gameplay/Jumpscare/Sand/SM_SandMonster/StaticMeshes/SM_SandMonster'
EYE = 10.0  # cm above the mesh pivot: the eye line goes to screen centre


def env(k, d):
    return [float(v) for v in os.environ.get(k, d).split(',')]


def main():
    os.makedirs(OUT, exist_ok=True)
    tag = os.environ.get('FOA_TAG', 'look')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    spawned = []
    try:
        m = EAS.spawn_actor_from_object(unreal.load_asset(MESH), unreal.Vector(0, 0, 150), unreal.Rotator(0, 0, 0))
        m.set_actor_label('TMP_horror_Monster')
        spawned.append(m)
        smc = m.static_mesh_component
        if os.environ.get('FOA_MAT'):
            smc.set_material(0, unreal.load_asset(os.environ['FOA_MAT']))
        if os.environ.get('FOA_OVERLAY'):
            smc.set_overlay_material(unreal.load_asset(os.environ['FOA_OVERLAY']))
        if os.environ.get('FOA_SAND'):  # the black-sand shell: splat mesh with its base at z 0, so it sits 19.91 cm lower
            sand = EAS.spawn_actor_from_object(unreal.load_asset(SAND), unreal.Vector(0, 0, 150 - 19.91), unreal.Rotator(0, 0, 0))
            sand.set_actor_label('TMP_horror_Sand')
            spawned.append(sand)
            sand.static_mesh_component.set_material(0, unreal.load_asset(os.environ['FOA_SAND']))
            sand.static_mesh_component.set_editor_property('cast_shadow', False)
        if os.environ.get('FOA_HIDE_SOLID'):
            smc.set_visibility(False)
        dist = float(os.environ.get('FOA_DIST', '38'))
        cam = unreal.Vector(0, dist, 150 + EYE)

        def to_world(f, r, u):  # camera looks -Y; its right is +X
            return unreal.Vector(cam.x + r, cam.y - f, cam.z + u)

        for name, key, dflt in (('Key', 'FOA_KEY', '12,8,-22,4'), ('Rim', 'FOA_RIM', '60,-18,22,30')):
            f, r, u, cd = env(key, dflt)
            lt = EAS.spawn_actor_from_class(unreal.PointLight, to_world(f, r, u), unreal.Rotator(0, 0, 0))
            lt.set_actor_label('TMP_horror_' + name)
            spawned.append(lt)
            c = lt.point_light_component
            c.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            c.set_editor_property('intensity', cd)
            c.set_editor_property('attenuation_radius', 90.0)
            c.set_editor_property('cast_shadows', False)
            c.set_editor_property('source_radius', 6.0)
            c.set_editor_property('volumetric_scattering_intensity', 0.0)
        rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        shots = {'face': ((cam.x, cam.y, cam.z), -90, float(os.environ.get('FOA_FOV', '78')))}
        if os.environ.get('FOA_SIDES'):
            shots.update({'side_posX': ((90, 0, 160), 180, 60), 'side_negY': ((0, -90, 160), 90, 60)})
        for name, (loc, yaw, fov) in shots.items():
            cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(*loc), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
            cap.set_actor_label('TMP_horror_Capture')
            spawned.append(cap)
            c = cap.capture_component2d
            for k, v in (('texture_target', rt), ('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                         ('capture_every_frame', False), ('capture_on_movement', False), ('fov_angle', fov)):
                c.set_editor_property(k, v)
            c.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, rt, OUT, f'{tag}_{name}.png')
        print('shots', OUT, tag)
    finally:
        for a in spawned:
            a.destroy_actor()


main()
