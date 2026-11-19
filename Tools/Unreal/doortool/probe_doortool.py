"""Door-tool lane: read-only probe of the screwdriver path (BP_Door, BP_FoAPlayer tool vars, ABP_FoAPlayer_MH).
  $env:HAYBA_AGENT_ID='doortool'; $env:FOA_AREAS='Gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/doortool/probe_doortool.py
Writes Saved/QA/lanes/doortool/probe.json."""
import json
from pathlib import Path
import unreal

BEL = unreal.BlueprintEditorLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
out = {}


def s(v):
    return str(v)


def comps(bp):
    r = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object_for_blueprint(d, bp)
        if not o:
            continue
        row = dict(cls=o.get_class().get_name())
        if isinstance(o, unreal.SceneComponent):
            row['rel'] = s(o.get_editor_property('relative_location')) + ' ' + s(o.get_editor_property('relative_rotation'))
            row['scale'] = s(o.get_editor_property('relative_scale3d'))
            p = o.get_attach_parent()
            row['parent'] = p.get_name() if p else None
            row['socket'] = s(o.get_attach_socket_name())
        if isinstance(o, unreal.StaticMeshComponent):
            m = o.get_editor_property('static_mesh')
            row['mesh'] = m.get_path_name() if m else None
            row['mats'] = [m2.get_path_name() if m2 else None for m2 in o.get_editor_property('override_materials')]
        if isinstance(o, unreal.SkeletalMeshComponent):
            m = o.get_skeletal_mesh_asset()
            row['mesh'] = m.get_path_name() if m else None
            row['anim'] = s(o.get_editor_property('anim_class'))
        if isinstance(o, unreal.LightComponentBase):
            row['intensity'] = o.get_editor_property('intensity')
        r[s(lib.get_variable_name(d))] = row
    return r


door = unreal.load_asset('/Game/FoA/Gameplay/BP_Door')
out['door_components'] = comps(door)
out['door_graphs'] = [s(n) for n in BEL.list_graph_names(door)]
cdo = unreal.get_default_object(door.generated_class())
dv = {}
for v in BEL.list_member_variable_names(door):
    v = s(v)
    if v.startswith('Tool') or 'Screw' in v:
        try:
            dv[v] = s(cdo.get_editor_property(v))[:400]
        except Exception as e:  # noqa: BLE001
            dv[v] = 'ERR ' + repr(e)[:80]
out['door_vars'] = dv
drv = cdo.get_editor_property('ToolDriverMesh')
if drv:
    bb = drv.get_bounding_box()
    out['driver'] = dict(path=drv.get_path_name(), min=s(bb.min), max=s(bb.max))
player = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
pc = unreal.get_default_object(player.generated_class())
pv = {}
for v in BEL.list_member_variable_names(player):
    v = s(v)
    if any(k in v for k in ('Tool', 'Screw', 'Grip', 'Held')):
        try:
            pv[v] = s(pc.get_editor_property(v))[:300]
        except Exception as e:  # noqa: BLE001
            pv[v] = 'ERR ' + repr(e)[:80]
out['player_vars'] = pv
out['player_components'] = {k: v for k, v in comps(player).items() if k in ('Body', 'Mesh', 'HeldTool', 'HeldToolGrip', 'FirstPersonCamera', 'FollowCamera', 'CharacterMesh0')}
abp = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer_MH')
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(abp, 'AnimGraph')
out['abp_mh_nodes'] = [f'{n.get_class().get_name()}|{BEL.get_node_title(n)}' for n in ed.list_all_nodes()]
out['abp_mh_vars'] = [s(v) for v in BEL.list_member_variable_names(abp)]
out['abp_mh_graphs'] = [s(n) for n in BEL.list_graph_names(abp)]
Path('P:/FoA/Saved/QA/lanes/doortool').mkdir(parents=True, exist_ok=True)
Path('P:/FoA/Saved/QA/lanes/doortool/probe.json').write_text(json.dumps(out, indent=1))
print('PROBE ok', len(out))
