"""Builds M_Fireplace with Hayba's C++ material commands only (editor-rules: Python never mutates a material graph).

  $env:HAYBA_AGENT_ID='fireplace'; python Tools/Fireplace/build_fireplace_material.py          # build (resumable)
  python Tools/Fireplace/build_fireplace_material.py --selftest                                 # graph sanity, offline

Runs OUTSIDE the editor and talks to Hayba over TCP (Tools/Unreal/hayba_call.py), so it needs no editor Python. Every
created node id is written to Saved/FoA_fireplace_material.json as it goes, so a dropped connection resumes there.
The graph is deliberately lean (the wear maths is baked into MaskTex offline by build_fireplace_blender.py):
  base   = lerp(lerp(BaseColorTex * Tint * (1 - dirt), WearColor, Wear), GrimeColor, Grime) * lerp(1, AO, AOStrength)
           then lerp(.., SootColor, Soot)
  rough  = (RoughnessTex * Tint.a + (grunge.b - 0.5) * RoughVar) -> lerp WearColor.a, GrimeColor.a, SootColor.a
  metal  = lerp(Metallic, Shape.a, Wear);  normal = NormalTex
  Soot   = saturate(2 - VertexColor.r - Mask.a)      (vertex-colour soot in the firebox + baked smoke stain)
MaskTex (UV1) = R AO, G wear, B grime, A 1 - stain. Shape = dirt, roughness variation, AO strength, worn-area metallic.
"""
import json
import os
import sys
import time

sys.path.insert(0, "P:/FoA/Tools/Unreal")

MAT = "/Game/FoA/Fireplace/Materials/M_Fireplace"
TEX = "/Game/FoA/Fireplace/Textures/"
STATE = "P:/FoA/Saved/FoA_fireplace_material.json"

# id: (class, (x, y), properties)
NODES = {
    "uv1": ("MaterialExpressionTextureCoordinate", (-2300, 160), {"CoordinateIndex": 1}),
    "t_base": ("MaterialExpressionTextureSampleParameter2D", (-2050, -980),
               {"ParameterName": "BaseColorTex", "Texture": "/Engine/EngineResources/WhiteSquareTexture", "SamplerType": "SAMPLERTYPE_Color"}),
    "t_rough": ("MaterialExpressionTextureSampleParameter2D", (-2050, -420),
                {"ParameterName": "RoughnessTex", "Texture": TEX + "T_FP_White", "SamplerType": "SAMPLERTYPE_LinearGrayscale"}),
    "t_grunge": ("MaterialExpressionTextureSampleParameter2D", (-2050, -700),
                 {"ParameterName": "GrungeTex", "Texture": TEX + "T_FP_Grunge", "SamplerType": "SAMPLERTYPE_Masks"}),
    "t_mask": ("MaterialExpressionTextureSampleParameter2D", (-2050, 120),
               {"ParameterName": "MaskTex", "Texture": TEX + "T_FP_MaskNeutral", "SamplerType": "SAMPLERTYPE_Masks"}),
    "t_normal": ("MaterialExpressionTextureSampleParameter2D", (-2050, 700),
                 {"ParameterName": "NormalTex", "Texture": "/Engine/EngineMaterials/FlatNormal", "SamplerType": "SAMPLERTYPE_Normal"}),
    "vc": ("MaterialExpressionVertexColor", (-2050, 440), {}),
    # masks group
    "soot_add": ("MaterialExpressionAdd", (-1700, 420), {}),
    "soot_sub": ("MaterialExpressionSubtract", (-1550, 420), {"ConstA": 2.0}),
    "soot_sat": ("MaterialExpressionSaturate", (-1400, 420), {}),
    # base colour group
    "tint": ("MaterialExpressionVectorParameter", (-1300, -1100), {"ParameterName": "Tint", "DefaultValue": {"R": 1, "G": 1, "B": 1, "A": 0.5}}),
    "shape": ("MaterialExpressionVectorParameter", (-1300, -820), {"ParameterName": "Shape", "DefaultValue": {"R": 0.25, "G": 0.15, "B": 0.6, "A": 0.0}}),
    "b_tint": ("MaterialExpressionMultiply", (-1080, -1020), {}),
    "b_dirt": ("MaterialExpressionMultiply", (-1080, -820), {}),
    "b_clean": ("MaterialExpressionOneMinus", (-930, -820), {}),
    "b_dirty": ("MaterialExpressionMultiply", (-780, -960), {}),
    "wearcol": ("MaterialExpressionVectorParameter", (-780, -1180), {"ParameterName": "WearColor", "DefaultValue": {"R": 0.1, "G": 0.08, "B": 0.06, "A": 0.75}}),
    "b_wear": ("MaterialExpressionLinearInterpolate", (-560, -980), {}),
    "grimecol": ("MaterialExpressionVectorParameter", (-560, -1200), {"ParameterName": "GrimeColor", "DefaultValue": {"R": 0.19, "G": 0.15, "B": 0.085, "A": 0.7}}),
    "b_grime": ("MaterialExpressionLinearInterpolate", (-340, -1000), {}),
    "b_ao": ("MaterialExpressionLinearInterpolate", (-340, -760), {"ConstA": 1.0}),
    "b_occl": ("MaterialExpressionMultiply", (-160, -920), {}),
    "sootcol": ("MaterialExpressionVectorParameter", (-160, -1160), {"ParameterName": "SootColor", "DefaultValue": {"R": 0.006, "G": 0.0055, "B": 0.005, "A": 0.97}}),
    "b_soot": ("MaterialExpressionLinearInterpolate", (40, -960), {}),
    # roughness + metallic group
    "r_base": ("MaterialExpressionMultiply", (-1080, -420), {}),
    "r_streak": ("MaterialExpressionSubtract", (-1080, -280), {"ConstB": 0.5}),
    "r_var": ("MaterialExpressionMultiply", (-930, -280), {}),
    "r_sum": ("MaterialExpressionAdd", (-780, -360), {}),
    "r_wear": ("MaterialExpressionLinearInterpolate", (-560, -380), {}),
    "r_grime": ("MaterialExpressionLinearInterpolate", (-340, -380), {}),
    "r_soot": ("MaterialExpressionLinearInterpolate", (-160, -380), {}),
    "r_sat": ("MaterialExpressionSaturate", (40, -360), {}),
    "metallic": ("MaterialExpressionScalarParameter", (-560, -140), {"ParameterName": "Metallic", "DefaultValue": 0.0}),
    "m_wear": ("MaterialExpressionLinearInterpolate", (-340, -140), {}),
}
# named reroutes: name -> (source node, pin, pos, colour)
DECLS = {"Wear": ("t_mask", "G", (-1700, 120), [0.9, 0.7, 0.2]), "Grime": ("t_mask", "B", (-1700, 200), [0.6, 0.45, 0.25]),
         "Soot": ("soot_sat", "", (-1250, 420), [0.25, 0.25, 0.25])}
# usages: (reroute, pos, target node, target input)
USAGES = [("Wear", (-760, -880), "b_wear", "Alpha"), ("Grime", (-560, -880), "b_grime", "Alpha"),
          ("Soot", (-160, -820), "b_soot", "Alpha"), ("Wear", (-760, -300), "r_wear", "Alpha"),
          ("Grime", (-560, -300), "r_grime", "Alpha"), ("Soot", (-340, -300), "r_soot", "Alpha"),
          ("Wear", (-560, -60), "m_wear", "Alpha")]
# links: (from node, from pin, to node, to input)
LINKS = [
    ("uv1", "", "t_mask", "Coordinates"),
    ("vc", "R", "soot_add", "A"), ("t_mask", "A", "soot_add", "B"), ("soot_add", "", "soot_sub", "B"),
    ("soot_sub", "", "soot_sat", ""),
    ("t_base", "RGB", "b_tint", "A"), ("tint", "RGB", "b_tint", "B"),
    ("shape", "R", "b_dirt", "A"), ("t_grunge", "G", "b_dirt", "B"), ("b_dirt", "", "b_clean", ""),
    ("b_tint", "", "b_dirty", "A"), ("b_clean", "", "b_dirty", "B"),
    ("b_dirty", "", "b_wear", "A"), ("wearcol", "RGB", "b_wear", "B"),
    ("b_wear", "", "b_grime", "A"), ("grimecol", "RGB", "b_grime", "B"),
    ("t_mask", "R", "b_ao", "B"), ("shape", "B", "b_ao", "Alpha"),
    ("b_grime", "", "b_occl", "A"), ("b_ao", "", "b_occl", "B"),
    ("b_occl", "", "b_soot", "A"), ("sootcol", "RGB", "b_soot", "B"),
    ("t_rough", "R", "r_base", "A"), ("tint", "A", "r_base", "B"),
    ("t_grunge", "B", "r_streak", "A"), ("r_streak", "", "r_var", "A"), ("shape", "G", "r_var", "B"),
    ("r_base", "", "r_sum", "A"), ("r_var", "", "r_sum", "B"),
    ("r_sum", "", "r_wear", "A"), ("wearcol", "A", "r_wear", "B"),
    ("r_wear", "", "r_grime", "A"), ("grimecol", "A", "r_grime", "B"),
    ("r_grime", "", "r_soot", "A"), ("sootcol", "A", "r_soot", "B"),
    ("r_soot", "", "r_sat", ""),
    ("metallic", "", "m_wear", "A"), ("shape", "A", "m_wear", "B"),
]
OUTPUTS = [("b_soot", "", "base_color"), ("r_sat", "", "roughness"), ("m_wear", "", "metallic"), ("t_normal", "RGB", "normal")]
COMMENTS = [  # (title, pos, size, colour)
    ("Textures: surface maps on UV0, baked wear map on UV1 (R AO, G wear, B grime, A 1 - smoke stain)",
     (-2340, -1040), (520, 1980), [0.2, 0.35, 0.6]),
    ("Masks: named Wear, Grime and Soot (vertex-colour soot + baked stain = saturate(2 - VC.r - Mask.a))",
     (-1740, 80), (600, 460), [0.6, 0.4, 0.15]),
    ("Base colour: texture x Tint x (1 - dirt), worn edges, grime in recesses, baked AO, then soot",
     (-1320, -1240), (1560, 500), [0.2, 0.5, 0.25]),
    ("Roughness and metallic: per-surface roughness with streaks, then the same wear / grime / soot masks",
     (-1100, -460), (1340, 460), [0.45, 0.25, 0.55]),
]


def selftest():
    names = set(NODES)
    for a, _, b, _ in LINKS:
        assert a in names and b in names, (a, b)
    for _, _, t, _ in USAGES:
        assert t in names
    for src, _, _, _ in DECLS.values():
        assert src in names
    fed = {(b, i) for _, _, b, i in LINKS} | {(t, i) for _, _, t, i in USAGES}
    assert len(fed) == len(LINKS) + len(USAGES), "an input is wired twice"
    for n in ("b_wear", "b_grime", "b_soot", "r_wear", "r_grime", "r_soot", "m_wear"):
        assert {"A", "B", "Alpha"} <= {i for (b, i) in fed if b == n}, n
    print("selftest OK:", len(NODES) + len(DECLS) + len(USAGES), "nodes,", len(LINKS) + len(USAGES) + len(OUTPUTS), "wires")


def main():
    from hayba_call import call
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"ids": {}, "done": []}

    def save():
        json.dump(state, open(STATE, "w"), indent=1)

    def run(cmd, params, key=None):
        if key and key in state["done"]:
            return state.get("res", {}).get(key)
        for attempt in range(8):
            try:
                resp = call(cmd, params, timeout=60)
            except (ConnectionError, OSError) as e:
                print("  retry", cmd, e)
                time.sleep(5 + 5 * attempt)
                continue
            if not resp.get("ok"):
                raise RuntimeError(f"{cmd} {params} -> {resp.get('error')}")
            data = resp.get("data") or {}
            if key:
                state["done"].append(key)
                state.setdefault("res", {})[key] = data
                save()
            return data
        raise RuntimeError(f"{cmd}: Hayba unreachable")

    base = {"material_path": MAT}
    for key, (cls, pos, props) in NODES.items():
        data = run("material_add_node", dict(base, expression_class=cls, node_pos=list(pos), properties=props), "node:" + key)
        state["ids"][key] = data["node_id"]
        save()
    for name, (src, pin, pos, col) in DECLS.items():
        data = run("material_add_reroute_declaration", dict(base, name=name, node_pos=list(pos), color=col), "decl:" + name)
        state["ids"]["decl:" + name] = data["node_id"]
        p = dict(base, from_node=state["ids"][src], to_node=data["node_id"])
        if pin:
            p["from_output"] = pin
        run("material_connect_nodes", p, "declwire:" + name)
    ids = state["ids"]
    for i, (name, pos, target, pin) in enumerate(USAGES):
        data = run("material_add_reroute_usage", dict(base, declaration_id=ids["decl:" + name], node_pos=list(pos)), f"use:{i}")
        run("material_connect_nodes", dict(base, from_node=data["node_id"], to_node=ids[target], to_input=pin), f"usewire:{i}")
    for i, (a, pin, b, inp) in enumerate(LINKS):
        p = dict(base, from_node=ids[a], to_node=ids[b])
        if pin:
            p["from_output"] = pin
        if inp:
            p["to_input"] = inp
        run("material_connect_nodes", p, f"link:{i}")
    for a, pin, prop in OUTPUTS:
        p = dict(base, from_node=ids[a], to_property=prop)
        if pin:
            p["from_output"] = pin
        run("material_connect_nodes", p, "out:" + prop)
    for i, (text, pos, size, col) in enumerate(COMMENTS):
        run("material_add_comment", dict(base, text=text, node_pos=list(pos), size=list(size), color=col, font_size=18), f"comment:{i}")
    v = run("material_validate", base)
    print("validate:", json.dumps(v)[:400])
    if v.get("ok") is False:
        sys.exit("validation failed; not compiling")
    c = run("material_compile", base)
    print("compile:", json.dumps(c)[:600])


if __name__ == "__main__":
    selftest()
    if "--selftest" not in sys.argv:
        main()
