"""Read-only probe of the screwdriver hand path: player components, ABP graphs, the kneel montage and the door tool.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/probe_tool_grip.py
Writes Saved/AnimShots/screwdriver/probe.json."""
import json
from pathlib import Path
import unreal

BEL = unreal.BlueprintEditorLibrary
P = '/Game/FoA/Characters/Player/'
out = {}
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary


def comps(bp):
    r = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        o = lib.get_object_for_blueprint(d, bp)
        if not o:
            continue
        row = dict(cls=o.get_class().get_name())
        if isinstance(o, unreal.SkeletalMeshComponent):
            m = o.get_skeletal_mesh_asset()
            row.update(mesh=m.get_path_name() if m else None,
                       skel=m.get_editor_property('skeleton').get_path_name() if m else None,
                       anim=str(o.get_editor_property('anim_class')), visible=o.get_editor_property('visible'),
                       hidden=o.get_editor_property('hidden_in_game'))
        r[str(lib.get_variable_name(d))] = row
    return r


player = unreal.load_asset(P + 'BP_FoAPlayer')
out['player_components'] = comps(player)
out['player_graphs'] = [str(n) for n in BEL.list_graph_names(player)]
for abp in ('ABP_FoAPlayer', 'ABP_FoAPlayer_MH'):
    bp = unreal.load_asset(P + abp)
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'AnimGraph')
    out[abp] = dict(nodes=[f'{n.get_class().get_name()}|{BEL.get_node_title(n)}' for n in ed.list_all_nodes()],
                    vars=[str(v) for v in BEL.list_member_variable_names(bp)],
                    skeleton=bp.get_editor_property('target_skeleton').get_path_name())
m = unreal.load_asset(P + 'Montages/AM_FoA_KneelScrewdriver')
segs = m.get_editor_property('slot_anim_tracks')[0].get_editor_property('anim_track').get_editor_property('anim_segments')
out['montage'] = dict(length=m.get_play_length(), segments=[
    (s.get_editor_property('anim_reference').get_name(), s.get_editor_property('anim_start_time'),
     s.get_editor_property('anim_end_time'), s.get_editor_property('anim_play_rate'), s.get_editor_property('looping_count'))
    for s in segs], notifies=[(str(e.get_editor_property('notify').get_editor_property('notify_name')) if e.get_editor_property('notify') else '?',
                              unreal.AnimationLibrary.get_anim_notify_event_trigger_time(e))
                             for e in unreal.AnimationLibrary.get_animation_notify_events(m)])
door = unreal.load_asset('/Game/FoA/Gameplay/BP_Door')
cdo = unreal.get_default_object(door.generated_class())
out['door'] = dict(driver=str(cdo.get_editor_property('ToolDriverMesh').get_path_name()),
                   driver_xf=str(cdo.get_editor_property('ToolDriverTransform')),
                   key=str(cdo.get_editor_property('ToolKeyMesh').get_path_name()),
                   contact_times={str(k): v for k, v in cdo.get_editor_property('ToolContactTimes').items()})
drv = cdo.get_editor_property('ToolDriverMesh')
bb = drv.get_bounding_box()
out['door']['driver_bounds'] = [str(bb.min), str(bb.max)]
# Visible body: hand and finger bones, sockets.
for name, row in out['player_components'].items():
    if row.get('mesh') and name in ('Body', 'Mesh', 'CharacterMesh0'):
        sk = unreal.load_asset(row['mesh'])
        out[name + '_sockets'] = [str(sk.get_socket_by_index(i).get_editor_property('socket_name')) for i in range(sk.num_sockets())]
        names = [str(n) for n in unreal.AnimationLibrary.get_bone_names(sk.get_editor_property('skeleton'))] if hasattr(unreal.AnimationLibrary, 'get_bone_names') else []
        out[name + '_hand_bones'] = [n for n in names if n.endswith('_r') and any(k in n for k in ('hand', 'index', 'middle', 'ring', 'pinky', 'thumb', 'lowerarm', 'weapon', 'ik_hand'))]
Path('P:/FoA/Saved/AnimShots/screwdriver').mkdir(parents=True, exist_ok=True)
Path('P:/FoA/Saved/AnimShots/screwdriver/probe.json').write_text(json.dumps(out, indent=1))
print('PROBE ok', len(out))
