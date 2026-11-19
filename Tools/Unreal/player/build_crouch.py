"""Hold Ctrl to crouch; native movement owns capsule clearance, animation owns eye height.

Run under the Characters scoped editor lease, then native-compile both Blueprints.
Enhanced Input event and animation pose nodes are the editor-Python gaps.
"""
import sys
import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import graph_style as G

P = '/Game/FoA/Characters/Player'
EAL, BEL, BGE, PIN = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
bp = unreal.load_asset(P+'/BP_FoAPlayer')
abp = unreal.load_asset(P+'/ABP_FoAPlayer')
action = unreal.load_asset(P+'/Input/IA_Crouch')
assert action, 'Create/map the Boolean action with native input tools first'
movement = unreal.get_default_object(bp.generated_class()).get_editor_property('character_movement')
nav = movement.get_editor_property('nav_agent_props')
nav.set_editor_property('can_crouch', True)
movement.set_editor_property('nav_agent_props', nav)
movement.set_editor_property('crouched_half_height', 55.0)
movement.set_editor_property('max_walk_speed_crouched', 65.0)

ed = BGE.get_graph_editor_by_name(bp, 'EventGraph')
if not any('IA_Crouch' in str(BEL.get_node_title(n)) for n in ed.list_all_nodes()):
    entry = next(str(s) for s in ed.list_available_nodes([]) if str(s).endswith('|IA_Crouch'))
    event = ed.create_node_from_name(entry, unreal.Vector2D(0, 4800), [])
    crouch = ed.add_call_function_node('/Script/Engine.Character:Crouch')
    release = ed.add_call_function_node('/Script/Engine.Character:UnCrouch')
    guard = ed.add_branch_node()
    controller = ed.add_call_function_node('/Script/Engine.Pawn:GetController')
    ignored = ed.add_call_function_node('/Script/Engine.Controller:IsMoveInputIgnored')
    cinematic = ed.add_get_member_variable_node('bCinematic', '')
    interaction = ed.add_get_member_variable_node('bInteractionLocked', '')
    busy = ed.add_call_function_node('/Script/Engine.KismetMathLibrary:BooleanOR')
    locked = ed.add_call_function_node('/Script/Engine.KismetMathLibrary:BooleanOR')
    G.link(controller, 'ReturnValue', ignored, 'self')
    G.link(cinematic, 'bCinematic', busy, 'A'); G.link(interaction, 'bInteractionLocked', busy, 'B')
    G.link(busy, 'ReturnValue', locked, 'A'); G.link(ignored, 'ReturnValue', locked, 'B')
    G.link(locked, 'ReturnValue', guard, 'Condition'); G.link(event, 'Started', guard, None)
    G.link(guard, 'else', crouch, None)
    for pin in ('Completed', 'Canceled'): G.link(event, pin, release, None)
    nodes = [event, guard, crouch, release, controller, ignored, cinematic, interaction, busy, locked]
    for i, n in enumerate(nodes): G.at(n, (i%4)*340, 4800+(i//4)*240)
    G.box(ed, 'Hold to crouch', '', nodes, 'input')

ag = BGE.get_graph_editor_by_name(abp, 'AnimGraph')
if not any(BEL.get_comment_text(c)=='Crouched locomotion' for c in ag.list_comment_nodes()):
    slot = next(n for n in ag.list_all_nodes() if str(BEL.get_node_title(n)).startswith("Slot 'DefaultSlot'"))
    inlet = G.pin_in(slot, 'Source')
    previous = list(PIN.list_connected_pins(inlet)); assert len(previous)==1
    blend = ag.create_node_from_name('Animation|Blends|BlendPosesbybool', unreal.Vector2D(-500, 2000), [])
    moveblend = ag.create_node_from_name('Animation|Blends|BlendPosesbybool', unreal.Vector2D(-900, 1800), [])
    for n in (blend, moveblend):
        data = n.get_editor_property('node'); data.set_editor_property('blend_time', [.22,.22]); n.set_editor_property('node', data)
    clips = []
    for i, name in enumerate(('UAL_Crouch_Fwd_Loop', 'UAL_Crouch_Idle_Loop')):
        clip = ag.create_node_from_name("Animation|Sequences|Play'"+name+"'", unreal.Vector2D(-1400, 1600+i*260), [])
        assert clip, name
        data = clip.get_editor_property('node'); data.set_editor_property('loop_animation', True); clip.set_editor_property('node', data)
        G.link(clip, 'Pose', moveblend, 'BlendPose_'+str(i)); clips.append(clip)
    moving = ag.add_get_member_variable_node('ShouldMove', '')
    character = ag.add_get_member_variable_node('Character', '')
    crouched = ag.add_get_member_variable_node('bIsCrouched', '/Script/Engine.Character')
    G.link(character, 'Character', crouched, 'self')
    G.link(crouched, 'bIsCrouched', blend, 'bActiveValue'); G.link(moving, 'ShouldMove', moveblend, 'bActiveValue')
    G.link(moveblend, 'Pose', blend, 'BlendPose_0')
    assert PIN.try_create_connection(previous[0], G.pin_in(blend, 'BlendPose_1'))
    PIN.break_pin_links(inlet)
    G.link(blend, 'Pose', slot, 'Source')
    G.box(ag, 'Crouched locomotion', '', [blend,moveblend,*clips,moving,character,crouched], 'anim')
for a in (bp, abp): assert EAL.save_loaded_asset(a, False)
print('Crouch capsule, input and animated pose saved; native compile and runtime checks pending')
