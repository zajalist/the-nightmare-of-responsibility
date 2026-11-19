"""BP_FoAPlayer implements gameplay's BPI_InteractionHost: Event LockForInteraction(Seconds, Target) stops the capsule dead
(no slide into the montage), holds movement input, turns him to face Target over 0.25 s (a soft align: stands in for motion
warping), then EndInteraction runs after Seconds. BPC_Interactor plays the montage itself and sends this message.
  1. hayba object_set_property BP_FoAPlayer ImplementedInterfaces (Python cannot add interfaces), Hayba compile
  2. python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_host.py FOA_AREAS=/Game/FoA/Characters/Player
     (re-runnable: rebuilds its own row, keeps the event), then compile again"""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link, value = graph_style.at, graph_style.box, graph_style.link, graph_style.value
BEL = unreal.BlueprintEditorLibrary
BP_PATH = "/Game/FoA/Characters/Player/BP_FoAPlayer"
X, Y = 0, 2800  # own row under the BeginPlay chains
ALIGN_S = 0.25

bp = unreal.load_asset(BP_PATH)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
mine = lambda n: Y - 100 <= BEL.get_node_pos(n).y < Y + 700  # noqa: E731
event = [n for n in ed.list_all_nodes() if "LockForInteraction" in BEL.get_node_title(n).replace(" ", "")]
for n in list(ed.list_all_nodes()):  # re-runnable: keep the event (one per graph), rebuild the rest of the row
    if mine(n) and n not in event:
        ed.remove_nodes([n])
for c in list(ed.list_comment_nodes()):
    if BEL.get_comment_text(c) in ("Interaction lock", "Face the target"):
        ed.remove_comment_node(c)
if not event:
    hits = [str(a) for a in ed.list_available_nodes([]) if "LockForInteraction" in str(a).replace(" ", "") and "Event" in str(a)]
    assert hits, "no Event LockForInteraction in the palette: set ImplementedInterfaces and compile first"
    event = [ed.create_node_from_name(min(hits, key=len), unreal.Vector2D(X, Y), [])]
ev = at(event[0], X, Y)
# Lock: input off, velocity zeroed, unlock timer.
hold = graph_style.self_call(ed, "SetInteractionLocked", X + 300, Y)
cmc = at(ed.add_get_member_variable_node("CharacterMovement", ""), X + 600, Y + 200)
stop = at(ed.add_call_function_node("/Script/Engine.MovementComponent:StopMovementImmediately"), X + 600, Y)
timer = at(ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:K2_SetTimer"), X + 900, Y)
link(ev, None, hold, None)
value(hold, "bEnable", "true")
link(hold, None, stop, None)
link(cmc, "CharacterMovement", stop, "self")
link(stop, None, timer, None)
link(ev, "Seconds", timer, "Time")
value(timer, "FunctionName", "EndInteraction")
box(ed, "Interaction lock", "", [ev, hold, cmc, stop, timer], "anim")
# Face the target: yaw-only turn of the capsule, eased, in the montage's blend-in.
valid = at(ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid"), X + 1240, Y + 200)
br = at(ed.add_branch_node(), X + 1240, Y)
me = at(ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation"), X + 1240, Y + 340)
tgt = at(ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation"), X + 1240, Y + 480)
look = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:FindLookAtRotation"), X + 1520, Y + 400)
brk = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakRotator"), X + 1780, Y + 400)
mk = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator"), X + 2020, Y + 400)
cap = at(ed.add_get_member_variable_node("CapsuleComponent", ""), X + 2020, Y + 260)
move = at(ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MoveComponentTo"), X + 2300, Y)
link(timer, None, br, None)
link(ev, "Target", valid, "Object")
link(valid, "ReturnValue", br, "Condition")
link(ev, "Target", tgt, "self")
link(me, "ReturnValue", look, "Start")
link(tgt, "ReturnValue", look, "Target")
link(look, "ReturnValue", brk, "InRot")
link(brk, "Yaw", mk, "Yaw")
link(br, "Then", move, "Move")  # MoveAction expands into Move/Stop/Return execs
link(cap, "CapsuleComponent", move, "Component")
link(me, "ReturnValue", move, "TargetRelativeLocation")  # the capsule is the root: relative is world
link(mk, "ReturnValue", move, "TargetRelativeRotation")
value(move, "bEaseOut", "true")
value(move, "bEaseIn", "true")
value(move, "OverTime", ALIGN_S)
box(ed, "Face the target", "", [valid, br, me, tgt, look, brk, mk, cap, move], "anim")
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print("LockForInteraction wired:", BEL.get_node_title(ev), [str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)) for p in BEL.list_output_pins(ev)])
