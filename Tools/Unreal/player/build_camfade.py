"""Camera too close: when the boom's collision pulls the camera within NEAR cm of his head (a wall or wardrobe behind
him), his visible parts go Owner No See, so the player never looks out through his back. Owner No See is separate from
visibility, so gameplay's outfit show/hide is untouched. Only flips when the state changes (bCameraClose). Re-runnable.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_camfade.py FOA_AREAS=/Game/FoA/Characters/Player
then compile with Hayba blueprint_compile."""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link, value = graph_style.at, graph_style.box, graph_style.link, graph_style.value
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
NEAR = 45.0
PARTS = ("Body", "Face", "Hair", "Eyebrows", "StartOutfit", "Shirt", "Trousers", "Socks", "Tie", "Suit", "FaceDrift", "BodyDrift")
X, Y = 0, 3600  # own row under the interaction lock

bp = unreal.load_asset("/Game/FoA/Characters/Player/BP_FoAPlayer")
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
graph_style.ensure_variable(bp, "bCameraClose", BEL.get_basic_type_by_name("bool"), "false")
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
tick = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).replace(" ", "") == "EventTick")
for n in list(ed.list_all_nodes()):  # re-runnable: this row only (the Tick event stays)
    if Y - 100 <= BEL.get_node_pos(n).y < Y + 700 and n != tick:
        ed.remove_nodes([n])
for c in list(ed.list_comment_nodes()):
    if BEL.get_comment_text(c) == "Camera too close":
        ed.remove_comment_node(c)
assert not PIN.list_connected_pins(BEL.find_then_pin(tick)), "Event Tick already drives something: append instead"
tick = at(tick, X, Y)
cam = at(ed.add_get_member_variable_node("FollowCamera", ""), X + 40, Y + 200)
cam_loc = at(ed.add_call_function_node("/Script/Engine.SceneComponent:K2_GetComponentLocation"), X + 260, Y + 200)
body = at(ed.add_get_member_variable_node("Body", ""), X + 40, Y + 340)
head = at(ed.add_call_function_node("/Script/Engine.SceneComponent:GetSocketLocation"), X + 260, Y + 340)
dist = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance"), X + 540, Y + 260)
less = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble"), X + 760, Y + 260)
was = at(ed.add_get_member_variable_node("bCameraClose", ""), X + 760, Y + 420)
diff = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_BoolBool"), X + 980, Y + 300)
br = at(ed.add_branch_node(), X + 1200, Y)
st = at(ed.add_set_member_variable_node("bCameraClose", ""), X + 1440, Y)
link(cam, "FollowCamera", cam_loc, "self")
link(body, "Body", head, "self")
value(head, "InSocketName", "head")
link(cam_loc, "ReturnValue", dist, "V1")
link(head, "ReturnValue", dist, "V2")
link(dist, "ReturnValue", less, "A")
value(less, "B", NEAR)
link(less, "ReturnValue", diff, "A")
link(was, "bCameraClose", diff, "B")
link(tick, None, br, None)
link(diff, "ReturnValue", br, "Condition")
link(br, "Then", st, None)
link(less, "ReturnValue", st, "bCameraClose")
made, prev = [cam, cam_loc, body, head, dist, less, was, diff, br, st], st
flag = at(ed.add_get_member_variable_node("bCameraClose", ""), X + 1680, Y + 420)
made.append(flag)
for i, name in enumerate(PARTS):
    g = at(ed.add_get_member_variable_node(name, ""), X + 1680 + i * 260, Y + 200)
    c = at(ed.add_call_function_node("/Script/Engine.PrimitiveComponent:SetOwnerNoSee"), X + 1680 + i * 260, Y)
    link(prev, None, c, None)
    link(g, name, c, "self")
    link(flag, "bCameraClose", c, "bNewOwnerNoSee")
    prev = c
    made += [g, c]
box(ed, "Camera too close", "", made, "camera")
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print("camera fade: Tick -> OwnerNoSee on", PARTS, "under", NEAR, "cm")
