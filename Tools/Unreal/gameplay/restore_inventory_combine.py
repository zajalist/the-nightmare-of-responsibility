"""Puts BPC_Inventory.Combine back exactly as build_inventory.py builds it (main, 2026-11-10: keep it as dead code for
Level 2's C.V beat), without rebuilding the other graphs (Add and IsFull carry the carried-set patch).
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/restore_inventory_combine.py   (FOA_AREAS=/Game/FoA/Gameplay/BPC_Inventory)"""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/gameplay")
import gp  # noqa: E402

importlib.reload(gp)
G, T = gp.G, gp.T
KML = gp.KML
DT = gp.D + "/DT_Items.DT_Items"

bp = gp.asset("BPC_Inventory")
gp.close(bp)
if "Combine" in [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)] if hasattr(unreal.BlueprintEditorLibrary, "list_graph_names") else []:
    print("combine already there")
    sys.exit(0)
name = T("name")
SIGS = {"Combine": gp.sig([("A", name), ("B", name)], [("Result", name)])}
gp.declare(bp, SIGS)
g = G.function(bp, "Combine", **SIGS["Combine"])
e = g.entry(0, 0)
row = g.pal(260, 0, "Get Data Table Row")
g.val(row, "DataTable", DT)
g.link(e, "A", row, "RowName")
g.link(e, None, row, None)
brk = g.pal(560, 200, "Break", "S_Item")
g.link(row, "ReturnValue", brk, "S_Item")
match = g.call(KML + ":EqualEqual_NameName", 860, 200)
g.link(brk, gp.find_pin_name(brk, "CombineWith"), match, "A")
g.link(e, "B", match, "B")
br = g.branch(1080, 0)
g.link(row, "then", br, None)
g.link(match, "ReturnValue", br, "Condition")
ra = g.selfcall("Remove", 1320, -60)
g.link(e, "A", ra, "Item")
rb = g.selfcall("Remove", 1580, -60)
g.link(e, "B", rb, "Item")
ad = g.selfcall("Add", 1840, -60)
into = gp.find_pin_name(brk, "CombineInto")
g.link(brk, into, ad, "Item")
r1 = g.ret(2100, -60)
g.link(brk, into, r1, "Result")
r0 = g.ret_new(1320, 200)
g.val(r0, "Result", "None")
g.link(br, "Then", ra, None)
g.chain(ra, rb, ad, r1)
g.link(br, "Else", r0, None)
g.link(row, "RowNotFound", r0, None)
g.box("Combine", "A's DT_Items row names its partner (CombineWith) and the result (CombineInto). Both go, the "
      "result comes in. Kept for Level 2 (main, 2026-11-10).", g.nodes, "state")
print("combine restored, compile", unreal.BlueprintEditorLibrary.compile_blueprint(bp))
gp.save(bp)
