"""Bounded read-only asset audit; no actors, asset mutation, compilation or playback."""
import json
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Never run editor Python during user PIE'
B = unreal.BlueprintEditorLibrary
G = unreal.BlueprintGraphEditor
P = unreal.BlueprintGraphPinLibrary
out = {}
for name in ('ABP_FoAPlayer', 'ABP_FoAPlayer_MH'):
    bp = unreal.load_asset('/Game/FoA/Characters/Player/' + name)
    rows = []
    for graph in B.list_graphs(bp):
        ed = G.get_graph_editor(graph)
        for n in ed.list_all_nodes() if ed else []:
            cls = n.get_class().get_name()
            if cls in ('AnimGraphNode_SequencePlayer', 'AnimGraphNode_StrideWarping', 'AnimGraphNode_RetargetPoseFromMesh'):
                rows.append(dict(graph=graph.get_name(), title=B.get_node_title(n), type=cls,
                    data=n.get_editor_property('node').export_text(),
                    pins={str(P.get_pin_name(p)): str(P.get_pin_value(p)) for p in B.list_all_pins(n)}))
    out[name] = rows
seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
out['wake_bindings'] = [dict(name=str(b.get_display_name()), id=str(b.get_id()), parent=str(b.get_parent().get_id()) if b.get_parent() else None,
    tracks=[dict(type=t.get_class().get_name(), sections=[s.get_path_name() for s in t.get_sections()]) for t in b.get_tracks()]) for b in seq.get_bindings()]
clip = unreal.load_asset('/Game/FoA/Characters/Player/Anims/Loco/AS_FoA_Walk_Brisk')
out['walk_clip'] = dict(length=clip.get_play_length(), root_motion=clip.get_editor_property('enable_root_motion'),
    skeleton=clip.get_editor_property('skeleton').get_path_name())
Path('P:/FoA/Saved/CharacterShots/locomotion_sleep_assets.json').write_text(json.dumps(out, indent=2))
print('READ ONLY locomotion, wake binding and face curve audit saved')
