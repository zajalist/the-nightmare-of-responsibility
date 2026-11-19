"""Phone hold pinned to the camera (main 2026-11-10; phone8/9 and QA's B3 T10: the grip layer starts at upperarm_l, so
the held phone inherited whatever the clavicle and spine did; it climbed 5-14 cm after the raise and sat at the bottom
edge at T10 after the payoff). ABP_FoAPlayer_MH gets a left two-bone IK on hand_l (world-space effector and elbow) and a
hand_l world-rotation replace, right after Local To Component, so they act on the phone layer's arm before the right
tool rig and the environment contact (which still win when they run). Alpha PhoneIKWeight. BP_FoAPlayer.UpdatePhoneHold
sets the targets every tick from the camera (phone_hold_attach_graphs.py: PhoneHandInEye / PhoneElbowInEye).
Idempotent. Compile and save with Hayba afterwards.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/phone_camera_ik.py FOA_AREAS=Characters"""
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

MH = '/Game/FoA/Characters/Player/ABP_FoAPlayer_MH'
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'PIE running'
ensure_vars(MH, [('PhoneHandTarget', ptype(unreal.Vector), '', 'Phone', False), ('PhoneElbowTarget', ptype(unreal.Vector), '', 'Phone', False),
                 ('PhoneHandRotation', ptype(unreal.Rotator), '', 'Phone', False), ('PhoneIKWeight', ptype('real'), '0.0', 'Phone', False)])
bp = unreal.load_asset(MH)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = GE.get_graph_editor_by_name(bp, 'AnimGraph')
nodes = list(ed.list_all_nodes())


def pin(n, name, output=False):
    return next(p for p in (BEL.list_output_pins(n) if output else BEL.list_input_pins(n)) if str(PIN.get_pin_name(p)) == name)


def wire(a, ap, b, bp_):
    assert PIN.try_create_connection(pin(a, ap, True), pin(b, bp_)), (ap, bp_)


def fed_by(n, name):
    src = list(PIN.list_connected_pins(pin(n, name)))
    return BEL.get_node_title(PIN.get_owning_node(src[0])).replace(' ', '') if src else ''


mine = [n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_TwoBoneIK' and fed_by(n, 'EffectorLocation') == 'GetPhoneHandTarget']
if mine:
    print('PHONE_CAMERA_IK already installed')
else:
    head = next(n for n in nodes if n.get_class().get_name() == 'AnimGraphNode_LocalToComponentSpace')
    out = pin(head, 'ComponentPose', True)
    after = list(PIN.list_connected_pins(out))
    assert len(after) == 1, len(after)
    pos = BEL.get_node_pos(head)
    palette = [str(n) for n in ed.list_available_nodes([])]

    def create(x, *terms):
        name = min((n for n in palette if all(t.lower() in n.replace(' ', '').lower() for t in terms)), key=len)
        return ed.create_node_from_name(name, V2(pos.x + x, pos.y + 700), [])
    ik, wrist = create(0, 'SkeletalControls', 'TwoBoneIK'), create(450, 'SkeletalControls', 'Modify')
    bone = unreal.BoneReference()
    bone.set_editor_property('bone_name', 'hand_l')
    n = ik.get_editor_property('node')
    for k, v in (('ik_bone', bone), ('effector_location_space', unreal.BoneControlSpace.BCS_WORLD_SPACE),
                 ('joint_target_location_space', unreal.BoneControlSpace.BCS_WORLD_SPACE), ('allow_stretching', False),
                 ('take_rotation_from_effector_space', False), ('maintain_effector_rel_rot', True), ('alpha', 0.0)):
        n.set_editor_property(k, v)
    ik.set_editor_property('node', n)
    n = wrist.get_editor_property('node')
    for k, v in (('bone_to_modify', bone), ('translation_mode', unreal.BoneModificationMode.BMM_IGNORE),
                 ('rotation_mode', unreal.BoneModificationMode.BMM_REPLACE), ('scale_mode', unreal.BoneModificationMode.BMM_IGNORE),
                 ('rotation_space', unreal.BoneControlSpace.BCS_WORLD_SPACE), ('alpha', 0.0)):
        n.set_editor_property(k, v)
    wrist.set_editor_property('node', n)
    PIN.break_pin_links(out)
    assert PIN.try_create_connection(out, pin(ik, 'ComponentPose'))
    wire(ik, 'Pose', wrist, 'ComponentPose')
    assert PIN.try_create_connection(pin(wrist, 'Pose', True), after[0])
    made = [ik, wrist]
    for i, (name, node, key) in enumerate((('PhoneHandTarget', ik, 'EffectorLocation'), ('PhoneElbowTarget', ik, 'JointTargetLocation'),
                                           ('PhoneIKWeight', ik, 'Alpha'), ('PhoneHandRotation', wrist, 'Rotation'))):
        v = ed.add_get_member_variable_node(name, '')
        BEL.set_node_pos(v, P(pos.x - 300 + (450 if node == wrist else 0), pos.y + 1000 + i * 150))
        wire(v, name, node, key)
        if name == 'PhoneIKWeight':
            wire(v, name, wrist, 'Alpha')
        made.append(v)
    c = ed.add_comment_to_nodes('Phone hand pinned to the camera', made, 48)
    BEL.set_comment_color(c, C_VISUAL)
    house_comment_flags(c)
    compile_save(MH)
    print('PHONE_CAMERA_IK installed after Local To Component')
