"""FoAGraphTools self-test, plus the usage note for agents. Run it after the editor has restarted with the plugin:
    python Tools/Unreal/ue_remote.py Tools/Unreal/graphtools_selftest.py
It returns at once. A few seconds later Saved/GraphShots/graphtools_selftest.txt says PASS or FAIL, next to the PNGs
graphtools_selftest_{bp,bp_view,wbp,mat}.png. Look at the PNGs.

USAGE (editor Python; plugin source in Plugins/FoAGraphTools)
    L = unreal.FoAGraphToolsLibrary
    L.capture_graph_png(asset, "EventGraph", "P:/FoA/Saved/GraphShots/x.png", True)
        Opens the asset's editor with that graph in front (Widget Blueprints switch to Graph mode) and zooms it to fit.
        About 1.5 s later it renders the graph off-screen to the PNG:
          zoom_to_fit=True: the whole graph at 1:1 zoom, scaled down only past 6144 px, so text stays readable;
          zoom_to_fit=False: the editor's current view, at the tab's size.
        Works for Blueprints, Widget Blueprints, Materials and Material Functions. For materials pass graph_name "".
    t3d = L.export_nodes_text(bp, "EventGraph")
        Every node in the graph as T3D, exactly what Ctrl+C would copy. Read-only: use it to inspect a graph or diff it.
    To build graphs, use the engine's own Python API (UE 5.8). There is no T3D import.
        ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
        ev = ed.add_custom_event_node("OnThing")
        pr = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        BEL = unreal.BlueprintEditorLibrary
        BEL.set_node_pos(pr, unreal.IntPoint(320, 0))
        unreal.BlueprintGraphPinLibrary.try_create_connection(BEL.find_then_pin(ev), BEL.find_execute_pin(pr))
        unreal.BlueprintGraphPinLibrary.set_pin_value(BEL.find_input_pin(pr, "InString"), "hi")
        ed.add_comment_to_nodes("What this group does", [ev, pr], 50)

GOTCHAS
  - capture_graph_png returns before the PNG exists; a later editor tick writes it. Your Python blocks those ticks, so
    never sleep-wait for the file in the same script. Finish the script, then poll from outside (a second ue_remote run,
    or plain Python), or poll from unreal.register_slate_post_tick_callback as this test does.
  - The call deletes any old file at png_path first, so "file exists" means "fresh capture". The file only appears
    once it is complete, because it is written to <png>.tmp and then renamed.
  - Use absolute PNG paths. A relative path resolves against the engine's Binaries folder.
  - The faint "Zoom 1:1" label in the top-right corner is the stock graph-editor overlay, not a defect.
  - zoom_to_fit=False copies the view of the editor tab that is in front. Capture other assets first, then this one.
  - A bad argument (missing graph, no editor) raises RuntimeError and lists the graphs the Blueprint has. A failure
    during the later write goes to the Output Log under LogFoAGraphTools, and no PNG appears.
"""
import os
import struct
import time

import unreal

DIR = "/Game/FoA/Dev/_GraphToolsTest"
SHOTS = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "GraphShots/"
RESULT = SHOTS + "graphtools_selftest.txt"
L = unreal.FoAGraphToolsLibrary
BEL = unreal.BlueprintEditorLibrary
PINS = unreal.BlueprintGraphPinLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDITORS = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
failures = []


def check(ok, what):
    if not ok:
        failures.append(what)
    unreal.log(("ok   " if ok else "FAIL ") + what)


def build_print_graph(bp):
    """Custom event -> PrintString, framed by a comment: the shape of a real graph section."""
    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
    ev = ed.add_custom_event_node("FoA_SelfTest")
    pr = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    # New Blueprints already hold greyed-out default events at x=0, y=0/208/416, so build above them.
    BEL.set_node_pos(ev, unreal.IntPoint(0, -400))
    BEL.set_node_pos(pr, unreal.IntPoint(320, -400))
    check(PINS.try_create_connection(BEL.find_then_pin(ev), BEL.find_execute_pin(pr)), bp.get_name() + ": wire event -> print")
    PINS.set_pin_value(BEL.find_input_pin(pr, "InString"), "Hello from FoAGraphTools")
    check(ed.add_comment_to_nodes("Self-test: the event prints one line", [ev, pr], 50) is not None, bp.get_name() + ": comment")
    check(BEL.compile_blueprint(bp), bp.get_name() + ": compiles without errors")
    check(not ed.list_nodes_with_errors(), bp.get_name() + ": no nodes with errors")


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else None


if unreal.EditorAssetLibrary.does_directory_exist(DIR):
    unreal.EditorAssetLibrary.delete_directory(DIR)  # leftovers from an aborted run
if os.path.exists(RESULT):
    os.remove(RESULT)

bp_factory = unreal.BlueprintFactory()
bp_factory.set_editor_property("parent_class", unreal.Actor)
bp = TOOLS.create_asset("BP_GraphToolsTest", DIR, unreal.Blueprint, bp_factory)
wbp = TOOLS.create_asset("WBP_GraphToolsTest", DIR, unreal.WidgetBlueprint, unreal.WidgetBlueprintFactory())
mat = TOOLS.create_asset("M_GraphToolsTest", DIR, unreal.Material, unreal.MaterialFactoryNew())
build_print_graph(bp)
build_print_graph(wbp)
tint = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -320, 0)
unreal.MaterialEditingLibrary.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
unreal.MaterialEditingLibrary.recompile_material(mat)

t3d = L.export_nodes_text(bp, "EventGraph")
for needle in ("K2Node_CustomEvent", "FoA_SelfTest", "PrintString", "EdGraphNode_Comment", "LinkedTo=("):
    check(needle in t3d, "export_nodes_text contains " + needle)
try:
    L.export_nodes_text(bp, "NoSuchGraph")
    check(False, "a missing graph raises RuntimeError")
except RuntimeError as err:
    check("EventGraph" in str(err), "a missing graph raises RuntimeError that lists the graphs")

pending = {}
# bp_view goes last: it copies the live editor's view, so the Blueprint editor must be the tab in front.
for key, asset, graph, fit in (("bp", bp, "EventGraph", True), ("wbp", wbp, "EventGraph", True),
                               ("mat", mat, "", True), ("bp_view", bp, "EventGraph", False)):
    png = SHOTS + "graphtools_selftest_%s.png" % key
    try:
        L.capture_graph_png(asset, graph, png, fit)
        check(not os.path.exists(png), key + ": capture requested, old PNG cleared")
        pending[key] = png
    except RuntimeError as err:
        check(False, "%s: capture_graph_png raised %s" % (key, err))

started = time.time()


def finish(_delta):
    """Waits on editor ticks for the PNGs, then cleans up and writes the verdict."""
    done = {k: p for k, p in pending.items() if os.path.exists(p)}
    if len(done) < len(pending) and time.time() - started < 60:
        return
    unreal.unregister_slate_post_tick_callback(handle)
    try:
        for key, png in pending.items():
            size = png_size(png) if key in done else None
            check(bool(size) and size[0] >= 640 and size[1] >= 360, "%s: PNG written %s" % (key, size))
    finally:
        for asset in (bp, wbp, mat):
            EDITORS.close_all_editors_for_asset(asset)
        unreal.EditorAssetLibrary.delete_directory(DIR)
        verdict = ("FAIL: " + "; ".join(failures)) if failures else "PASS"
        with open(RESULT, "w", encoding="utf-8") as fh:
            fh.write(verdict + "\n" + "\n".join(pending.values()) + "\n")
        unreal.log("graphtools_selftest " + verdict)


handle = unreal.register_slate_post_tick_callback(finish)
print("graphtools_selftest: synchronous checks %s; waiting for %d captures -> %s"
      % ("FAILED: " + "; ".join(failures) if failures else "passed", len(pending), RESULT))
