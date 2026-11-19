"""Editor Python (python_exec_file inside the Drive lease), the drive lane's cars and hiring signs pass (11-18):
  FOA_STEP=import  the six Lux3D GLBs (P:/FoA-Assets/lux3d/drive_cars_signs) into /Game/FoA/Level2/Drive/Cars and
                   /Signs: standing on Z=0, centred, nose or panel facing +X (offsets from _measure.json, written by
                   drive_lux3d_inspect.py), Nanite off, three LODs (100/50/25%), textures capped (cars 1024, signs 512)
  FOA_STEP=apply   BP_L2Car's Body shows the new sedan (its NoCollision visual only: the Collision box, handling, camera
                   and steering are untouched); the 14 traffic cars take the three models round robin, standing on the
                   road; each stop's job board becomes a real sign beside the road with its lettering on the panel,
                   unlit and glowing (M_DreamExitText); the old free-drive shelter labels stay hidden.
The parent step compiles and saves the Blueprints. Idempotent."""
import importlib
import json
import math
import os
import sys

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
import drive_data as D  # noqa: E402
importlib.reload(D)
from job_route import BOSS, NAMES  # noqa: E402

EAL = unreal.EditorAssetLibrary
MEASURE = json.load(open(D.LUX_DRIVE + '/_measure.json'))
TEXT_MATERIAL = '/Game/FoA/Level2/Dream/M_DreamExitText'


def dest(item):
    return (D.CARS_DIR if not item.startswith('sign') else D.SIGNS_DIR) + '/' + item


def offsets(item):
    """Import rotation (yaw) and translation so the asset stands on Z=0, centred, with its long axis (car) or its panel
    width (sign) on Y for a sign / X for a car; a car's nose direction comes from CAR_NOSE (set after looking)."""
    m = MEASURE[item]
    sx, sy = m['size'][0], m['size'][1]
    # _measure.json is in glb_preview's axes, whose Y is Unreal's -Y after Interchange (seen in PIE 13:42: a turn
    # meant for the preview's -Y put the sedan's nose backwards); a face on the preview's -Y is on Unreal's +Y
    if item.startswith('sign'):
        yaw = 0.0 if m['wide_axis'] == 'Y' else -90.0      # panel width on Y, its face (preview -Y) on +X
    else:
        yaw = 0.0 if sx >= sy else 90.0                     # the car's length on X
        yaw += CAR_NOSE.get(item, 0.0)
    c = m['centre']
    r = math.radians(yaw)
    cx, cy = c[0] * math.cos(r) - c[1] * math.sin(r), c[0] * math.sin(r) + c[1] * math.cos(r)
    return yaw, unreal.Vector(-cx, -cy, -m['min'][2])


CAR_NOSE = json.loads(os.environ.get('FOA_CAR_NOSE', '{}'))  # extra yaw (0 or 180) per car, decided from the previews
REIMPORT = [x for x in os.environ.get('FOA_REIMPORT', '').split(',') if x]  # replace these in place (references kept)


def import_one(item):
    path = dest(item)
    if EAL.does_directory_exist(path) and EAL.list_assets(path, recursive=True) and item not in REIMPORT:
        print('IMPORT skip (exists)', item)
    else:
        yaw, move = offsets(item)
        pipeline = unreal.InterchangeGenericAssetsPipeline()
        pipeline.set_editor_property('import_offset_rotation', unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        pipeline.set_editor_property('import_offset_translation', move)
        pipeline.get_editor_property('mesh_pipeline').set_editor_property('build_nanite', False)
        stack = unreal.InterchangePipelineStackOverride(); stack.add_pipeline(pipeline)
        task = unreal.AssetImportTask()
        for k, v in (('filename', f'{D.LUX_DRIVE}/{item}/textured.glb'), ('destination_path', path), ('automated', True),
                     ('replace_existing', True), ('save', False), ('options', stack)):
            task.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    cap = 512 if item.startswith('sign') else 1024
    for p in EAL.list_assets(path, recursive=True, include_folder=False):
        a = EAL.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            ns = smes.get_nanite_settings(a); ns.set_editor_property('enabled', False); smes.set_nanite_settings(a, ns, True)
            opts = unreal.StaticMeshReductionOptions()
            opts.set_editor_property('auto_compute_lod_screen_size', False)
            opts.set_editor_property('reduction_settings', [
                unreal.StaticMeshReductionSettings(percent_triangles=1.0, screen_size=1.0),
                unreal.StaticMeshReductionSettings(percent_triangles=.5, screen_size=.35),
                unreal.StaticMeshReductionSettings(percent_triangles=.25, screen_size=.12)])
            smes.set_lods(a, opts)
            b = a.get_bounds()
            print('MESH', item, p, 'tris', [a.get_num_triangles(i) for i in range(a.get_num_lods())],
                  'origin (%.0f,%.0f,%.0f) size (%.0f,%.0f,%.0f)' % (b.origin.x, b.origin.y, b.origin.z,
                                                                    2 * b.box_extent.x, 2 * b.box_extent.y, 2 * b.box_extent.z))
        elif isinstance(a, unreal.Texture2D):
            a.set_editor_property('max_texture_size', cap)
        EAL.save_asset(p, only_if_is_dirty=False)


def mesh_of(item):
    meshes = [p for p in EAL.list_assets(dest(item), recursive=True, include_folder=False)
              if isinstance(EAL.load_asset(p), unreal.StaticMesh)]
    assert len(meshes) == 1, (item, meshes)
    return EAL.load_asset(meshes[0])


def templates(path):
    bp = unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    return bp, {str(lib.get_variable_name(lib.get_data(h))): lib.get_object_for_blueprint(lib.get_data(h), bp)
                for h in sds.k2_gather_subobject_data_for_blueprint(bp)}


def visual(component, mesh, length=None):
    """A visual-only mesh: the model's own materials, no collision, shadows on, scaled to `length` along X."""
    component.set_static_mesh(mesh)
    component.set_editor_property('override_materials', [])
    s = 1.0 if length is None else length / max(1.0, 2 * mesh.get_bounds().box_extent.x)
    component.set_editor_property('relative_scale3d', unreal.Vector(s, s, s))
    component.set_collision_profile_name('NoCollision')
    component.set_editor_property('cast_shadow', True)
    return s


def apply_cars():
    # The player's car: Body is a NoCollision visual (the Collision box is the car's collision): swap its mesh only.
    # The user's pick (2026-11-19): the player's car keeps the original SM_L2Sedan (car_revert_sedan.py), not the
    # Lux3D player_sedan; only the traffic below takes the Lux3D models.
    import car_visual_setup as cv
    bp, cs = templates(D.ROOT + '/BP_L2Car')
    cv.apply_to_components(cs, cv.find_sedan())
    assert EAL.save_loaded_asset(bp, False)

    bp, cs = templates(D.ROOT + '/BP_L2RoadNetwork')
    names = [n.replace('Collision', '') for n in D.TRAFFIC_NAMES]   # the five collision boxes carry a visual child
    for i, name in enumerate(names):
        model = D.TRAFFIC_MODELS[i % len(D.TRAFFIC_MODELS)]
        c = cs[name]
        visual(c, mesh_of(model), D.CAR_LENGTH[model])
        if name != D.TRAFFIC_NAMES[i]:  # a child of its collision box (at road height + 2 cm): stand on the road
            c.set_editor_property('relative_location', unreal.Vector(0, 0, -2))
    print('TRAFFIC', [(n, D.TRAFFIC_MODELS[i % 3]) for i, n in enumerate(names)])
    assert EAL.save_loaded_asset(bp, False)


def apply_signs():
    bp, cs = templates(D.ROOT + '/BP_L2RoadNetwork')
    text_material = unreal.load_asset(TEXT_MATERIAL)
    for i, (x, y, heading, side, model) in enumerate(D.SIGN_SPOTS):
        board, label = cs[f'JobBoard{i}'], cs[f'JobBoardText{i}']
        mesh = mesh_of(model)
        m = MEASURE[model]
        height = m['size'][2]
        scale = D.SIGN_HEIGHT[model] / height
        yaw = D.sign_yaw(heading, side)
        board.set_static_mesh(mesh)
        board.set_editor_property('override_materials', [])
        board.set_editor_property('relative_scale3d', unreal.Vector(scale, scale, scale))
        board.set_editor_property('relative_location', unreal.Vector(x, y, 0))
        board.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=0, yaw=yaw))
        board.set_collision_profile_name('NoCollision'); board.set_editor_property('cast_shadow', True)
        # lettering on the panel's front face (the panel faces +X after import), centred on the panel band
        z0, z1 = (z - m['min'][2] for z in m['panel_z'])
        # the panel's +X face after the import turn: wide on Y = no turn (thin axis X); wide on X = turned 90 degrees,
        # which maps the original -Y side to +X
        front = (m['panel_depth'][1] - m['centre'][0]) if m['wide_axis'] == 'Y' else (m['centre'][1] - m['panel_depth'][0])
        panel_w, panel_h = m['panel_width'] * scale, (z1 - z0) * scale
        f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
        out = front * scale + 4.0
        # centred a little above the band's middle: the band can hold a catwalk or ledge under the panel
        label.set_editor_property('relative_location', unreal.Vector(x + f[0] * out, y + f[1] * out, (z1 - .45 * (z1 - z0)) * scale))
        label.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=0, yaw=yaw))
        label.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
        # the job's name and HIRING (INTERVIEW for the boss): two lines on a wide panel, one word a line on a square one
        words = NAMES[i].upper().split() + ['INTERVIEW' if i == BOSS else 'HIRING']
        lines = [' '.join(words[:-1]), words[-1]] if panel_w >= 1.8 * panel_h else words
        label.set_text(unreal.Text('\n'.join(lines)))
        longest = max(len(t) for t in lines)
        size = min(panel_h * .78 / len(lines), panel_w * .86 / (longest * .62))
        label.set_world_size(size)
        label.set_text_material(text_material)
        label.set_text_render_color(unreal.Color(255, 255, 255, 255))
        label.set_editor_property('cast_shadow', False)
        print('SIGN', i, model, 'at (%.0f,%.0f) yaw %.0f scale %.3f panel %.0fx%.0f text %.0f' % (x, y, yaw, scale, panel_w, panel_h, size))
    for name in ('ShelterSouth', 'ShelterNorth', 'DestinationLabel'):  # free-drive leftovers: never floating text
        cs[name].set_editor_property('visible', False)
    assert EAL.save_loaded_asset(bp, False)


def traffic_lods():
    """Perf lane (11-18 14:3x): the traffic-only models drop to 50% sooner (LOD1 below half the screen, LOD2 below a
    fifth); the sedan keeps its LODs, it is also the player's car right under the camera."""
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for item in ('traffic_hatchback', 'traffic_van'):
        mesh = mesh_of(item)
        opts = unreal.StaticMeshReductionOptions()
        opts.set_editor_property('auto_compute_lod_screen_size', False)
        opts.set_editor_property('reduction_settings', [
            unreal.StaticMeshReductionSettings(percent_triangles=1.0, screen_size=1.0),
            unreal.StaticMeshReductionSettings(percent_triangles=.5, screen_size=.5),
            unreal.StaticMeshReductionSettings(percent_triangles=.25, screen_size=.2)])
        smes.set_lods(mesh, opts)
        EAL.save_loaded_asset(mesh, False)
        print('LODS', item, [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())])


STEP = os.environ.get('FOA_STEP', '')
if STEP == 'import':
    for item in sorted(MEASURE):
        import_one(item)
elif STEP == 'cars':
    apply_cars()
elif STEP == 'signs':
    apply_signs()
elif STEP == 'lods':
    traffic_lods()
else:
    raise SystemExit('FOA_STEP=import|cars|signs')
