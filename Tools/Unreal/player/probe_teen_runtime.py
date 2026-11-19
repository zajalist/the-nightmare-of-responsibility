"""Read-only inventory for the player swap, including the head frame and cloth sections."""
import json
from pathlib import Path
import unreal
E = unreal.EditorAssetLibrary
P = '/Game/FoA/Characters/Player'
bp = unreal.load_asset(P + '/BP_FoAPlayer')
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
components = {}
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h); n = str(lib.get_variable_name(d)); obj = lib.get_object_for_blueprint(d,bp)
    if not obj:
        continue
    components.setdefault(n, dict(path=obj.get_path_name(), cls=obj.get_class().get_name()))
meshes = {}
for part in ('Body','Head','Polo','Pants','Socks','Suit','Shoes'):
    mesh = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_' + part)
    meshes[part] = dict(path=mesh.get_path_name(), skeleton=mesh.get_editor_property('skeleton').get_path_name(),
        slots=[str(m.material_slot_name) for m in mesh.materials])
ref = unreal.AnimPoseExtensions.get_reference_pose(unreal.load_asset(meshes['Body']['skeleton']))
names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(ref)]
head = unreal.AnimPoseExtensions.get_bone_pose(ref,'head',unreal.AnimPoseSpaces.WORLD)
anim = unreal.load_asset(P + '/ABP_FoAPlayer_MH')
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(anim,'AnimGraph')
retarget = next(n for n in ed.list_all_nodes() if 'RetargetPoseFromMesh' in n.get_class().get_name())
out = dict(components=components,meshes=meshes,bones=names,head_transform=head.export_text(),retarget_node=retarget.get_path_name())
Path('P:/FoA/Saved/AnimShots/teen_runtime_inventory.json').write_text(json.dumps(out,indent=1))
print('Inventory saved', names, out['head_transform'])
