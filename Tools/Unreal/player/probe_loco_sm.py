"""Read-only: nodes of every state and transition graph in ABP_FoAPlayer. Writes Saved/AnimShots/loco_sm.txt."""
import unreal
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
a = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer')
rows = []
for g in BEL.list_graphs(a):
    k = g.get_class().get_name()
    if k not in ('AnimationStateGraph', 'AnimationTransitionGraph'):
        continue
    owner = g.get_outer()
    sm = owner.get_outer().get_name()
    ed = unreal.BlueprintGraphEditor.get_graph_editor(g)
    names = [str(BEL.get_node_title(n)).replace('\n', ' ')[:60] for n in ed.list_all_nodes()]
    extra = ''
    if k == 'AnimationTransitionGraph':
        extra = (f"logic={owner.get_editor_property('logic_type')} xfade={owner.get_editor_property('crossfade_duration')} "
                 f"auto={owner.get_editor_property('automatic_rule_based_on_sequence_player_in_state')}")
    rows.append(' | '.join([sm, k[9:], g.get_name(), owner.get_name(), str(names), extra]))
open('P:/FoA/Saved/AnimShots/loco_sm.txt', 'w').write('\n'.join(rows))
print('SM rows', len(rows))
