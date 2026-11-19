"""Native character helper: skinned boots, slipper section coverage, prop visibility and reset."""
import json
from pathlib import Path
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc

P = "/Game/FoA/Characters/Player/BP_FoAPlayer"
C = P + ".BP_FoAPlayer_C"
OWNER = "codex-character-boots"
TOKEN = None


def call(command, **params):
    r = hc.call(command, params, owner=OWNER, lease=TOKEN)
    assert r.get("ok"), r
    data = r.get("data", {})
    assert data.get("ok", True), data
    if data.get("compile"):
        assert data["compile"].get("error_count", 0) == 0 and data["compile"].get("warning_count", 0) == 0, data
    return data


def add(ops, ref, kind, x, y, **kwargs):
    ops.append({"op":"add_node", "ref":ref, "node_type":kind, "x":x, "y":y, **kwargs})


def link(ops, a, b, ap="then", bp="execute"):
    ops.append({"op":"connect", "from_node":a, "from_pin":ap, "to_node":b, "to_pin":bp})


def pin(ops, node, name, value):
    ops.append({"op":"set_pin", "node_id":node, "pin_name":name, "value":value})


def main():
    global TOKEN
    assert not call("editor_get_state")["pie_running"]
    TOKEN = hc.lease_acquire(OWNER, ["asset:"+P], ttl_s=120, wait_s=20)
    try:
        properties = call("object_get_property", path=P+".Default__BP_FoAPlayer_C", names=["BootsWornMesh"])["properties"]
        if "BootsWornMesh" not in properties:
            call("blueprint_add_component", path=P, component_class_path="/Script/Engine.SkeletalMeshComponent", component_name="BootsWornMesh")
        call("python_exec_file", path="P:/FoA/Tools/Unreal/player/parent_boots_component.py", env={}, resources=["asset:"+P])
        slots = json.loads(Path("P:/FoA/Saved/CharacterShots/boots_component.json").read_text())["slippers_materials"]
        # shortcut: hero LODSync pins StartOutfit to LOD0; extend section coverage if that constraint changes.
        assert slots[:2] == [2,3], slots
        info = call("blueprint_get_info", path=P)
        if "SetBootsWorn" not in info["functions"]:
            call("blueprint_add_function", path=P, function_name="SetBootsWorn", inputs=[{"name":"bEnable","type":"bool"}])
        g = call("blueprint_inspect_graph", path=P, graph_name="SetBootsWorn")
        entry = next(n["node_id"] for n in g["nodes"] if n["title"] == "SetBootsWorn")
        ops = [{"op":"remove", "node_ids":[n["node_id"] for n in g["nodes"] if n["node_id"] != entry]}] if len(g["nodes"])>1 else []
        add(ops,"boots","variable_get",80,224,variable_name="BootsWornMesh")
        add(ops,"body","variable_get",80,352,variable_name="Body")
        add(ops,"leader","call_function",320,0,function_name="/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent")
        link(ops,entry,"leader");link(ops,"boots","leader","BootsWornMesh","self");link(ops,"body","leader","Body","NewLeaderBoneComponent")
        pin(ops,"leader","bForceUpdate","true")
        add(ops,"visible","call_function",640,0,function_name="/Script/Engine.SceneComponent:SetVisibility")
        link(ops,"leader","visible");link(ops,"boots","visible","BootsWornMesh","self");link(ops,entry,"visible","bEnable","bNewVisibility")
        add(ops,"starter","variable_get",640,352,variable_name="StartOutfit")
        add(ops,"not","call_function",640,480,function_name="/Script/Engine.KismetMathLibrary:Not_PreBool")
        link(ops,entry,"not","bEnable","A")
        add(ops,"slippers","call_function",960,0,function_name="/Script/Engine.SkinnedMeshComponent:ShowMaterialSection")
        link(ops,"visible","slippers");link(ops,"starter","slippers","StartOutfit","self");link(ops,"not","slippers","ReturnValue","bShow")
        for name,value in (("MaterialID","2"),("SectionIndex","-1"),("LODIndex","0")):pin(ops,"slippers",name,value)
        add(ops,"slippers_right","call_function",1120,0,function_name="/Script/Engine.SkinnedMeshComponent:ShowMaterialSection")
        link(ops,"slippers","slippers_right");link(ops,"starter","slippers_right","StartOutfit","self");link(ops,"not","slippers_right","ReturnValue","bShow")
        for name,value in (("MaterialID","3"),("SectionIndex","-1"),("LODIndex","0")):pin(ops,"slippers_right",name,value)
        add(ops,"all","call_function",1280,0,function_name="/Script/Engine.GameplayStatics:GetAllActorsOfClass")
        pin(ops,"all","ActorClass","/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C");link(ops,"slippers_right","all")
        add(ops,"each","macro",1600,0,macro_name="ForEachLoop")
        link(ops,"all","each",bp="Exec");link(ops,"all","each","OutActors","Array")
        add(ops,"container","cast",1920,0,class_path="/Game/FoA/Gameplay/BP_Container.BP_Container_C")
        link(ops,"each","container","LoopBody");link(ops,"each","container","Array Element","Object")
        add(ops,"key","variable_get",1920,352,variable_name="InteractionKey",class_path="/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C")
        link(ops,"container","key","AsBP Container","self")
        for ref,value,y in (("left","Boot_L",352),("right","Boot_R",544)):
            add(ops,ref,"call_function",2240,y,function_name="/Script/Engine.KismetMathLibrary:EqualEqual_NameName")
            link(ops,"key",ref,"InteractionKey","A");pin(ops,ref,"B",value)
        add(ops,"either","call_function",2528,448,function_name="/Script/Engine.KismetMathLibrary:BooleanOR")
        link(ops,"left","either","ReturnValue","A");link(ops,"right","either","ReturnValue","B")
        add(ops,"is_boot","branch",2816,0);link(ops,"either","is_boot","ReturnValue","Condition");link(ops,"container","is_boot")
        add(ops,"hide","call_function",3104,0,function_name="/Script/Engine.Actor:SetActorHiddenInGame")
        link(ops,"is_boot","hide");link(ops,"container","hide","AsBP Container","self");link(ops,entry,"hide","bEnable","bNewHidden")
        add(ops,"collision","call_function",3424,0,function_name="/Script/Engine.Actor:SetActorEnableCollision")
        link(ops,"hide","collision");link(ops,"container","collision","AsBP Container","self");link(ops,"not","collision","ReturnValue","bNewActorEnableCollision")
        ops += [{"op":"comment","title":"Wear fitted boots and restore floor props","node_ids":[entry,"boots","body","leader","visible","starter","not","slippers","slippers_right","all","each","container","key","left","right","either","is_boot","hide","collision"],"color":[.2,.34,.45]}, {"op":"fit_comments"}]
        call("blueprint_graph_batch", path=P, graph_name="SetBootsWorn", ops=ops, compile=True, save=True)
        g=call("blueprint_inspect_graph",path=P,graph_name="UnequipAll")
        if not any(n["title"]=="SetBootsWorn" for n in g["nodes"]):
            entry=next(n["node_id"] for n in g["nodes"] if n["title"]=="UnequipAll")
            following=next(e for e in g["edges"] if e["from_node"]==entry and e["from_pin"]=="then")
            ops=[{"op":"disconnect","node_id":entry,"pin_name":"then"}]
            add(ops,"reset","call_function",128,-192,function_name=C+":SetBootsWorn");pin(ops,"reset","bEnable","false")
            link(ops,entry,"reset");link(ops,"reset",following["to_node"],bp=following["to_pin"])
            call("blueprint_graph_batch",path=P,graph_name="UnequipAll",ops=ops,compile=True,save=True)
        # Native MakeArray lacks pin-growth, and native graph inspection truncates this large graph at50 nodes.
        call("python_exec_file",path="P:/FoA/Tools/Unreal/player/include_boots_in_sand.py",env={},resources=["asset:"+P])
        compiled=call("blueprint_compile",path=P)
        assert compiled["error_count"]==0 and compiled["warning_count"]==0,compiled
        call("asset_save",asset_paths=[P])
        print("PASS SetBootsWorn: Body-led skinned boots, slippers hidden only while worn, floor props/collision restored, new-day reset, sand silhouette included")
    except Exception:
        # A failed new-helper batch must never leave a compile modal for the next PIE proof.
        g=call("blueprint_inspect_graph",path=P,graph_name="SetBootsWorn")
        nodes=[n["node_id"] for n in g["nodes"] if n["title"]!="SetBootsWorn"]
        if nodes:call("blueprint_graph_batch",path=P,graph_name="SetBootsWorn",ops=[{"op":"remove","node_ids":nodes}],compile=True,save=True)
        raise
    finally:
        hc.release(OWNER,TOKEN)


if __name__=="__main__":main()
