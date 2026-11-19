"""Devlog capture step. Runs inside the editor through Tools/Unreal/ue_remote.py; build_devlog.py drives it.
Read-only on assets: it opens asset editors and renders graphs, and never edits, compiles or saves anything.
It deliberately avoids FoAGraphToolsLibrary.export_nodes_text: that calls PrepareForCopying on every node without the
matching PostCopyNode, which re-parents state-machine and collapsed sub-graphs.
Env (always pass every key, empty when unused, because os.environ persists inside the editor between runs):
  FOA_CLOSE  asset path whose editors to close first (the previous capture, once its PNG exists)
  FOA_ASSET  asset path to capture, FOA_GRAPH graph name (empty for materials), FOA_PNG absolute PNG path
  FOA_META   absolute JSON path for the asset's facts (node count, functions used, graph names, ...)
"""
import json
import os
from collections import Counter

import unreal

env = os.environ
if env.get("FOA_CLOSE"):
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(env["FOA_CLOSE"]))

asset = unreal.load_asset(env["FOA_ASSET"]) if env.get("FOA_ASSET") else None
if asset is not None and env.get("FOA_META"):
    M = unreal.MaterialEditingLibrary
    meta = {"class": asset.get_class().get_name()}
    if isinstance(asset, (unreal.Material, unreal.MaterialFunction)):
        is_fn = isinstance(asset, unreal.MaterialFunction)
        exprs = M.get_material_function_expressions(asset) if is_fn else M.get_material_expressions(asset)
        meta["nodes"] = len(exprs)
        meta["node_classes"] = dict(Counter(e.get_class().get_name().replace("MaterialExpression", "") for e in exprs))
        meta["functions"] = sorted({e.get_editor_property("material_function").get_name() for e in exprs
                                    if isinstance(e, unreal.MaterialExpressionMaterialFunctionCall)
                                    and e.get_editor_property("material_function")})
        if is_fn:
            meta["description"] = str(asset.get_editor_property("description"))
            meta["inputs"] = [str(e.get_editor_property("input_name")) for e in exprs
                              if isinstance(e, unreal.MaterialExpressionFunctionInput)]
            meta["outputs"] = [str(e.get_editor_property("output_name")) for e in exprs
                               if isinstance(e, unreal.MaterialExpressionFunctionOutput)]
        else:
            meta["domain"] = str(asset.get_editor_property("material_domain")).split(".")[-1]
            meta["blend"] = str(asset.get_editor_property("blend_mode")).split(".")[-1]
    elif isinstance(asset, unreal.Blueprint):
        try:  # an unknown graph name makes the plugin fail before touching anything and list the real graphs
            unreal.FoAGraphToolsLibrary.capture_graph_png(asset, "__devlog_list_graphs__", env["FOA_META"] + ".png", True)
        except Exception as err:
            msg = str(err)
            meta["graphs"] = msg.split("It has: ", 1)[1].split(", ") if "It has: " in msg else []
        try:
            meta["parent"] = asset.get_editor_property("parent_class").get_name()
        except Exception:
            pass
    with open(env["FOA_META"], "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)

if asset is not None and env.get("FOA_PNG"):
    unreal.FoAGraphToolsLibrary.capture_graph_png(asset, env.get("FOA_GRAPH") or "", env["FOA_PNG"], True)
print(json.dumps({"asset": env.get("FOA_ASSET"), "loaded": asset is not None, "png": env.get("FOA_PNG")}))
