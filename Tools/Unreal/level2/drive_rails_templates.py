"""Editor Python (python_exec_file inside the Drive lease): component templates for the rails drive.
Sand props on BP_L2RoadNetwork (Lux3D splat meshes, hidden until placed), the extra traffic sedans with paint
variants, and the meteor's falling sand trail. Idempotent; the parent step compiles and saves."""
import importlib
import sys
import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
import drive_data as D
importlib.reload(D)

ROOT = '/Game/FoA/Level2/Drive'
EAL = unreal.EditorAssetLibrary


def templates(path):
    bp = unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
    comps = {n: lib.get_object_for_blueprint(lib.get_data(h), bp) for n, h in handles.items()}
    return bp, sds, handles, comps


def quiet(c):
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    c.set_editor_property('cast_shadow', False)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)


bp, sds, handles, comps = templates(ROOT + '/BP_L2RoadNetwork')
for i, (mesh, material, scale) in enumerate(D.PROPS):
    c = comps[f'SandProp{i}']
    assert sds.attach_subobject(handles['Root'], handles[f'SandProp{i}'])
    c.set_static_mesh(unreal.load_asset(mesh)); c.set_material(0, unreal.load_asset(material))
    c.set_editor_property('relative_scale3d', unreal.Vector(scale, scale, scale))
    c.set_editor_property('absolute_location', True); c.set_editor_property('absolute_rotation', True)
    c.set_editor_property('render_custom_depth', True); c.set_editor_property('custom_depth_stencil_value', 5)  # sand pass
    quiet(c); c.set_visibility(False)
for i, name in enumerate(D.TRAFFIC_NAMES):
    if name.endswith('Collision'):
        continue
    c = comps[name]
    assert sds.attach_subobject(handles['Root'], handles[name])
    # their models and materials are drive_cars_signs.py's (FOA_STEP=cars): the Lux3D hatchback, van and sedan
    c.set_editor_property('absolute_location', True); c.set_editor_property('absolute_rotation', True)
    quiet(c); c.set_visibility(False)  # ApplyTrafficLimit shows them when a leg starts; StepTraffic places them
# Round 3 set-piece: the Nightmare (Lux3D splats, the prop's own material) at road scale, hidden until a long leg.
c = comps['SetPiece']
assert sds.attach_subobject(handles['Root'], handles['SetPiece'])
mesh, material, _ = D.PROPS[3]
c.set_static_mesh(unreal.load_asset(mesh)); c.set_material(0, unreal.load_asset(material))
c.set_editor_property('relative_scale3d', unreal.Vector(D.SET_PIECE_SCALE, D.SET_PIECE_SCALE, D.SET_PIECE_SCALE))
c.set_editor_property('absolute_location', True); c.set_editor_property('absolute_rotation', True)
c.set_editor_property('render_custom_depth', True); c.set_editor_property('custom_depth_stencil_value', 5)
quiet(c); c.set_visibility(False)
assert EAL.save_loaded_asset(bp, False)

def sand_look(name, parent, sand):
    """A child of an existing sand instance that only changes Sand (albedo, glint share, roughness, jitter)."""
    path = f'{ROOT}/{name}'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, ROOT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_parent(mi, unreal.load_asset(parent))
    mel.set_material_instance_vector_parameter_value(mi, 'Sand', unreal.LinearColor(*sand))
    mel.update_material_instance(mi)
    assert EAL.save_loaded_asset(mi, False)
    return mi


# The meteor read as a dark tree against the black sky (coordinator, DR2d 01:50): a pale sand stream behind it and a
# glinting body. Same meshes and motion; only the sand's albedo (0.02 elsewhere) and its glint share change.
TRAIL_MI = sand_look('MI_L2MeteorTrail', D.V + '/Instances/MI_Sand_Stream', (0.8, 0.02, 0.5, 0.3))
BODY_MI = sand_look('MI_L2MeteorBody', D.V + '/Instances/MI_Sand_AlarmClock', (0.3, 0.08, 0.5, 0.3))
bp, sds, handles, comps = templates(ROOT + '/BP_Meteor')
trail = comps['Trail']
assert sds.attach_subobject(handles['Shadow'], handles['Trail'])
trail.set_static_mesh(unreal.load_asset(D.V + '/Meshes/SM_SandStream'))
trail.set_material(0, TRAIL_MI)
comps['Shadow'].set_material(0, BODY_MI)
# A 1.5 m ball read as a pebble near the horizon (DR 03:00): twice the size, and the trail it carries scales with it.
comps['Shadow'].set_editor_property('relative_scale3d', unreal.Vector(2, 2, 2))
# The stream hangs down from its origin; stretched above the falling meteor it reads as the sand it drags down.
trail.set_editor_property('relative_location', unreal.Vector(0, 0, 700))
trail.set_editor_property('relative_scale3d', unreal.Vector(1.6, 1.6, 4.5))
quiet(trail)
assert EAL.save_loaded_asset(bp, False)
print('DRIVE_TEMPLATES props', [comps_name for comps_name in (f'SandProp{i}' for i in range(4))], 'traffic', len(D.TRAFFIC_NAMES))
