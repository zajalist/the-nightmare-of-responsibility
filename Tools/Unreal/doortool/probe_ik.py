"""Door-tool lane: read-only, the right-hand two-bone IK's settings in ABP_FoAPlayer_MH."""
import unreal

abp = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer_MH')
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(abp, 'AnimGraph')
for n in ed.list_all_nodes():
    t = unreal.BlueprintEditorLibrary.get_node_title(n)
    if 'Two Bone IK' in t:
        node = n.get_editor_property('node')
        out = {}
        for k in ('effector_location_space', 'joint_target_location_space', 'allow_stretching', 'take_rotation_from_effector_space',
                  'maintain_effector_rel_rot', 'allow_twist', 'effector_target', 'joint_target', 'ik_bone'):
            try:
                out[k] = str(node.get_editor_property(k))[:120]
            except Exception as e:  # noqa: BLE001
                out[k] = 'n/a'
        print('IK', t, out)
