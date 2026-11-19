"""Read-only: does AS_FoA_Slap_Thumb_R hold the slap thumb, and is the ABP_FoAPlayer_MH layer wired to it? Prints the
thumb_01..03_r local rotations in the asset versus the Teen reference pose, and the layer node's sequence, branch
filter and weight pin source.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/slap_thumb_probe.py FOA_AREAS=Characters"""
import unreal

AP = unreal.AnimPoseExtensions
seq = unreal.load_asset('/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Slap_Thumb_R')
skel = unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body').get_editor_property('skeleton')
ref = AP.get_reference_pose(skel)
o = unreal.AnimPoseEvaluationOptions()
pose = AP.get_anim_pose_at_frame(seq, 0, o)
for b in ('thumb_01_r', 'thumb_02_r', 'thumb_03_r'):
    a, r = AP.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL).rotation, AP.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL).rotation
    print('SLAP_PROBE', b, 'asset', [round(v, 4) for v in (a.x, a.y, a.z, a.w)], 'ref', [round(v, 4) for v in (r.x, r.y, r.z, r.w)])
print('SLAP_PROBE tracks', [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(seq)])
bp = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer_MH')
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'AnimGraph')
for n in ed.list_all_nodes():
    if n.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator' and n.get_editor_property('node').get_editor_property('sequence') == seq:
        out = [unreal.BlueprintGraphPinLibrary.get_owning_node(p) for p in unreal.BlueprintGraphPinLibrary.list_connected_pins(
            next(p for p in unreal.BlueprintEditorLibrary.list_output_pins(n)))]
        for layer in out:
            node = layer.get_editor_property('node')
            filt = [(str(f.get_editor_property('bone_name')), f.get_editor_property('blend_depth')) for s in node.get_editor_property('layer_setup')
                    for f in s.get_editor_property('branch_filters')]
            pins = {str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)): [unreal.BlueprintEditorLibrary.get_node_title(
                unreal.BlueprintGraphPinLibrary.get_owning_node(q)) for q in unreal.BlueprintGraphPinLibrary.list_connected_pins(p)]
                for p in unreal.BlueprintEditorLibrary.list_input_pins(layer)}
            outs = [unreal.BlueprintEditorLibrary.get_node_title(unreal.BlueprintGraphPinLibrary.get_owning_node(q)) for p in
                    unreal.BlueprintEditorLibrary.list_output_pins(layer) for q in unreal.BlueprintGraphPinLibrary.list_connected_pins(p)]
            print('SLAP_PROBE layer', unreal.BlueprintEditorLibrary.get_node_title(layer), 'filters', filt, 'mesh space rot',
                  node.get_editor_property('mesh_space_rotation_blend'), 'inputs', pins, 'feeds', outs)
