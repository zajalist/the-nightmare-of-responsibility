"""BPC_Inventory: four slots of Item IDs on the player. Runs INSIDE the editor (rebuilds its graphs in place):
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/build_inventory.py
  Add(Item) -> bAdded        Remove(Item) -> bRemoved     Has(Item) -> bHas (pure)     Select(Index)
  GetHeld() -> Item (pure)   IsFull() -> bFull (pure)     UseUp(Item): becomes its DT_Items UsedBecomes (Key -> KeyStub)
  Combine(A, B) -> Result    dispatcher OnInventoryChanged() after every change (the HUD re-reads Items and Selected)"""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/gameplay")
import gp  # noqa: E402

importlib.reload(gp)
G, T = gp.G, gp.T
KAL, KML = gp.KAL, gp.KML
DT = gp.D + "/DT_Items.DT_Items"


def build():
    bp = gp.asset("BPC_Inventory")
    gp.close(bp)
    name, integer, boolean = T("name"), T("int"), T("bool")
    names = BEL_array(name)
    gp.ensure_vars(bp, [("Items", names, "", False), ("Selected", integer, "-1", False),
                        ("Capacity", integer, "4", True)], "Inventory")
    gp.ensure_dispatcher(bp, "OnInventoryChanged", [])
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    SIGS = {  # every function signature, declared up front so graphs can call each other in any order
        "Add": gp.sig([("Item", name)], [("bAdded", boolean)]),
        "Remove": gp.sig([("Item", name)], [("bRemoved", boolean)]),
        "Has": gp.sig([("Item", name)], [("bHas", boolean)], pure=True),
        "Select": gp.sig([("Index", integer)], []),
        "GetHeld": gp.sig([], [("Item", name)], pure=True),
        "IsFull": gp.sig([], [("bFull", boolean)], pure=True),
        "UseUp": gp.sig([("Item", name)], []),
        "Combine": gp.sig([("A", name), ("B", name)], [("Result", name)]),
    }
    gp.declare(bp, SIGS)

    # ---- Add ----
    g = G.function(bp, "Add", **SIGS["Add"])
    e = g.entry(0, 0)
    n_len = g.call(KAL + ":Array_Length", 220, 160)
    g.link(g.get("Items", 20, 180), "", n_len, "TargetArray")
    room = g.call(KML + ":Less_IntInt", 440, 160)
    g.link(n_len, "ReturnValue", room, "A")
    g.link(g.get("Capacity", 260, 260), "", room, "B")
    real = g.call(KML + ":NotEqual_NameName", 440, 300, B="None")
    g.link(e, "Item", real, "A")
    ok = g.call(KML + ":BooleanAND", 660, 200)
    g.link(room, "ReturnValue", ok, "A")
    g.link(real, "ReturnValue", ok, "B")
    br = g.branch(860, 0)
    g.link(e, None, br, None)
    g.link(ok, "ReturnValue", br, "Condition")
    first = len(g.nodes)
    add = g.call(KAL + ":Array_Add", 1100, -120)
    g.link(g.get("Items", 880, -160), "", add, "TargetArray")
    g.link(e, "Item", add, "NewItem")
    sel = g.set("Selected", 1380, -120)
    g.link(add, "ReturnValue", sel, "Selected")
    bc = g.pal(1640, -120, "Call", "OnInventoryChanged")
    r1 = g.ret(1900, -120)
    g.val(r1, "bAdded", True)
    r0 = g.ret_new(1100, 160)
    g.val(r0, "bAdded", False)
    g.link(br, "Then", add, None)
    g.chain(add, sel, bc, r1)
    g.link(br, "Else", r0, None)
    g.box("Room left?", "A real item and a free slot (Capacity, 4 by default).", g.nodes[:first], "logic")
    g.box("Store and hold it", "A new item goes in the next slot and becomes the held one, so it is ready to Use.",
          g.nodes[first:], "state")

    # ---- Remove ----
    g = G.function(bp, "Remove", **SIGS["Remove"])
    e = g.entry(0, 0)
    rm = g.call(KAL + ":Array_RemoveItem", 260, 0)
    g.link(g.get("Items", 40, 160), "", rm, "TargetArray")
    g.link(e, "Item", rm, "Item")
    valid = g.call(KAL + ":Array_IsValidIndex", 520, 200)
    g.link(g.get("Items", 300, 200), "", valid, "TargetArray")
    g.link(g.get("Selected", 300, 290), "", valid, "IndexToTest")
    pick = g.call(KML + ":SelectInt", 760, 200, B=-1)
    g.link(g.get("Selected", 540, 330), "", pick, "A")
    g.link(valid, "ReturnValue", pick, "bPickA")
    sel = g.set("Selected", 1000, 0)
    g.link(pick, "ReturnValue", sel, "Selected")
    bc = g.pal(1260, 0, "Call", "OnInventoryChanged")
    r = g.ret(1520, 0)
    g.link(rm, "ReturnValue", r, "bRemoved")
    g.chain(e, rm, sel, bc, r)
    g.box("Remove", "Drop the item; if the held slot no longer exists, hold nothing.", g.nodes, "state")

    # ---- Has (pure) ----
    g = G.function(bp, "Has", **SIGS["Has"])
    e = g.entry(0, 0)
    has = g.call(KAL + ":Array_Contains", 260, 60)
    g.link(g.get("Items", 40, 140), "", has, "TargetArray")
    g.link(e, "Item", has, "ItemToFind")
    r = g.ret(520, 0)
    g.link(e, None, r, None)
    g.link(has, "ReturnValue", r, "bHas")
    g.box("Has", "True when the item is in any slot.", g.nodes, "data")

    # ---- Select ----
    g = G.function(bp, "Select", **SIGS["Select"])
    e = g.entry(0, 0)
    valid = g.call(KAL + ":Array_IsValidIndex", 260, 160)
    g.link(g.get("Items", 40, 200), "", valid, "TargetArray")
    g.link(e, "Index", valid, "IndexToTest")
    pick = g.call(KML + ":SelectInt", 500, 160, B=-1)
    g.link(e, "Index", pick, "A")
    g.link(valid, "ReturnValue", pick, "bPickA")
    sel = g.set("Selected", 740, 0)
    g.link(pick, "ReturnValue", sel, "Selected")
    bc = g.pal(1000, 0, "Call", "OnInventoryChanged")
    g.chain(e, sel, bc)
    g.box("Select", "Hold the item in that slot; an empty slot or -1 means the bare hand.", g.nodes, "state")

    # ---- GetHeld (pure) ----
    g = G.function(bp, "GetHeld", **SIGS["GetHeld"])
    e = g.entry(0, 0)
    valid = g.call(KAL + ":Array_IsValidIndex", 220, 160)
    g.link(g.get("Items", 20, 160), "", valid, "TargetArray")
    g.link(g.get("Selected", 20, 250), "", valid, "IndexToTest")
    br = g.branch(460, 0)
    g.link(e, None, br, None)
    g.link(valid, "ReturnValue", br, "Condition")
    get = g.call(KAL + ":Array_Get", 700, 160)
    g.link(g.get("Items", 480, 200), "", get, "TargetArray")
    g.link(g.get("Selected", 480, 290), "", get, "Index")
    r1 = g.ret(960, -60)
    g.link(br, "Then", r1, None)
    g.link(get, "Item", r1, "Item")
    r0 = g.ret_new(960, 120)
    g.link(br, "Else", r0, None)
    g.val(r0, "Item", "None")
    g.box("Held item", "The selected slot's Item ID, or None for the bare hand.", g.nodes, "data")

    # ---- IsFull (pure) ----
    g = G.function(bp, "IsFull", **SIGS["IsFull"])
    e = g.entry(0, 0)
    n_len = g.call(KAL + ":Array_Length", 220, 120)
    g.link(g.get("Items", 20, 140), "", n_len, "TargetArray")
    full = g.call(KML + ":GreaterEqual_IntInt", 440, 120)
    g.link(n_len, "ReturnValue", full, "A")
    g.link(g.get("Capacity", 240, 220), "", full, "B")
    r = g.ret(660, 0)
    g.link(e, None, r, None)
    g.link(full, "ReturnValue", r, "bFull")
    g.box("Full?", "Every slot taken.", g.nodes, "data")

    # ---- UseUp ----
    g = G.function(bp, "UseUp", **SIGS["UseUp"])
    e = g.entry(0, 0)
    row = g.pal(260, 0, "Get Data Table Row")
    g.val(row, "DataTable", DT)  # a literal table types Out Row as S_Item
    g.link(e, "Item", row, "RowName")
    g.link(e, None, row, None)
    brk = g.pal(560, 200, "Break", "S_Item")
    g.link(row, "ReturnValue", brk, "S_Item")
    becomes = gp.find_pin_name(brk, "UsedBecomes")
    changed = g.call(KML + ":NotEqual_NameName", 860, 200, B="None")
    g.link(brk, becomes, changed, "A")
    br = g.branch(1080, 0)
    g.link(row, "then", br, None)
    g.link(changed, "ReturnValue", br, "Condition")
    find = g.call(KAL + ":Array_Find", 1080, 260)
    g.link(g.get("Items", 860, 330), "", find, "TargetArray")
    g.link(e, "Item", find, "ItemToFind")
    put = g.call(KAL + ":Array_Set", 1340, 0)
    g.link(g.get("Items", 1120, -80), "", put, "TargetArray")
    g.link(find, "ReturnValue", put, "Index")
    g.link(brk, becomes, put, "Item")
    bc = g.pal(1640, 0, "Call", "OnInventoryChanged")
    g.link(br, "Then", put, None)
    g.chain(put, bc)
    g.box("Use it up", "After a successful Use, an item may become something else in its slot (DT_Items UsedBecomes: "
          "the key snaps into KeyStub). Tools keep their row empty and stay as they are.", g.nodes, "state")

    # ---- Combine ----
    g = G.function(bp, "Combine", **SIGS["Combine"])
    e = g.entry(0, 0)
    row = g.pal(260, 0, "Get Data Table Row")
    g.val(row, "DataTable", DT)  # a literal table types Out Row as S_Item
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
          "result comes in. Taught in Find a Job (the CV beat).", g.nodes, "state")

    ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    gp.save(bp)
    graphs = ["Add", "Remove", "Has", "Select", "GetHeld", "IsFull", "UseUp", "Combine"]
    print("BPC_Inventory compiled", ok, "shots", gp.capture(bp, graphs, "BPC_Inventory"))


def BEL_array(t):
    return unreal.BlueprintEditorLibrary.get_array_type(t)


build()
