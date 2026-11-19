"""M_FoA_BeddingSettle through Hayba's C++ material tools (editor-rules: no Python material-graph edits).
  python Tools/Unreal/player/hayba_bed_material.py      (plain Python over TCP; hold the Characters lease first)
The duvet keeps a body-shaped dent while he lies in bed and relaxes when MPC_FoAPlayer.BedSettleStart passes:
world-space ellipse on upward faces -> WPO down + a slight crease darkening (reads in black and white), eased (1-t)^3.
Run Tools/Unreal/player/build_bed_settle.py FOA_STEP=mpc first (the collection), FOA_STEP=assign after."""
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
from hayba_call import call  # noqa: E402

PKG = "/Game/FoA/Characters/Player/Bed"
MAT = PKG + "/M_FoA_BeddingSettle"
MPC = "/Game/FoA/Characters/Player/MPC_FoAPlayer"
TEX = "/Game/FoA/Lux3D/bedding_fixed/T_Lux3D_Bedding_BaseColor"
X = "MaterialExpression"
# key: (class, [x, y], properties)
NODES = {
    "wp": ("WorldPosition", [-1700, 0], {}),
    "ctr": ("VectorParameter", [-1700, 140], {"ParameterName": "BodyCenter", "DefaultValue": [270.0, -191.0, 0.0, 0.0]}),
    "d": ("Subtract", [-1480, 40], {}),
    "dxy": ("ComponentMask", [-1300, 40], {"R": True, "G": True, "B": False, "A": False}),
    "size": ("VectorParameter", [-1480, 240], {"ParameterName": "BodyHalfSize", "DefaultValue": [85.0, 30.0, 0.0, 0.0]}),
    "sxy": ("ComponentMask", [-1300, 240], {"R": True, "G": True, "B": False, "A": False}),
    "uv": ("Divide", [-1120, 100], {}),
    "r2": ("DotProduct", [-960, 100], {}),
    "inside": ("OneMinus", [-800, 100], {}),
    "sat": ("Saturate", [-660, 100], {}),
    "soft": ("Multiply", [-520, 100], {}),
    "nz": ("VertexNormalWS", [-800, 280], {}),
    "up": ("ComponentMask", [-660, 280], {"R": False, "G": False, "B": True, "A": False}),
    "upc": ("Saturate", [-520, 280], {}),
    "foot": ("Multiply", [-360, 180], {}),
    "tm": ("Time", [-1700, 560], {}),
    "start": ("CollectionParameter", [-1700, 660], {"Collection": MPC, "ParameterName": "BedSettleStart"}),
    "el": ("Subtract", [-1480, 600], {}),
    "secs": ("ScalarParameter", [-1480, 740], {"ParameterName": "SettleSeconds", "DefaultValue": 2.4}),
    "frac": ("Divide", [-1300, 640], {}),
    "t": ("Saturate", [-1140, 640], {}),
    "rem": ("OneMinus", [-1000, 640], {}),
    "cube": ("Power", [-860, 640], {"ConstExponent": 3.0}),
    "amt": ("Multiply", [-200, 300], {}),
    "depth": ("ScalarParameter", [-200, 460], {"ParameterName": "DentDepth", "DefaultValue": 6.0}),
    "dz": ("Multiply", [-20, 380], {}),
    "down": ("Multiply", [160, 380], {"ConstB": -1.0}),
    "zero2": ("Constant2Vector", [160, 520], {"R": 0.0, "G": 0.0}),
    "wpo": ("AppendVector", [340, 440], {}),
    "tex": ("TextureSampleParameter2D", [-200, -260], {"ParameterName": "BaseColor", "Texture": TEX}),
    "shade": ("LinearInterpolate", [160, -160], {"ConstA": 1.0, "ConstB": 0.72}),
    "col": ("Multiply", [360, -200], {}),
    "rough": ("Constant", [360, -40], {"R": 0.85}),
}
WIRES = [  # (from, from_output, to, to_input)
    ("wp", "", "d", "A"), ("ctr", "", "d", "B"), ("d", "", "dxy", "Input"), ("size", "", "sxy", "Input"),
    ("dxy", "", "uv", "A"), ("sxy", "", "uv", "B"), ("uv", "", "r2", "A"), ("uv", "", "r2", "B"),
    ("r2", "", "inside", "Input"), ("inside", "", "sat", "Input"), ("sat", "", "soft", "A"), ("sat", "", "soft", "B"),
    ("nz", "", "up", "Input"), ("up", "", "upc", "Input"), ("soft", "", "foot", "A"), ("upc", "", "foot", "B"),
    ("tm", "", "el", "A"), ("start", "", "el", "B"), ("el", "", "frac", "A"), ("secs", "", "frac", "B"),
    ("frac", "", "t", "Input"), ("t", "", "rem", "Input"), ("rem", "", "cube", "Base"),
    ("foot", "", "amt", "A"), ("cube", "", "amt", "B"), ("amt", "", "dz", "A"), ("depth", "", "dz", "B"),
    ("dz", "", "down", "A"), ("zero2", "", "wpo", "A"), ("down", "", "wpo", "B"),
    ("amt", "", "shade", "Alpha"), ("tex", "RGB", "col", "A"), ("shade", "", "col", "B"),
]
OUTPUTS = [("col", "base_color"), ("rough", "roughness"), ("wpo", "world_position_offset")]
COMMENTS = [  # title only (the user's rule), one colour per group
    ("Body footprint", [-1740, -60], [1440, 420], [0.38, 0.22, 0.45]),
    ("Settle timing", [-1740, 480], [1060, 340], [0.42, 0.30, 0.14]),
    ("Dent and crease", [-240, -320], [800, 940], [0.22, 0.40, 0.20]),
]


def result(r):
    """Hayba replies either flat or MCP-style ({result: {content: [{text: json}]}}); return the payload dict."""
    import json
    body = r.get("result", r) if isinstance(r, dict) else r
    if isinstance(body, dict) and "content" in body:
        try:
            return json.loads(body["content"][0]["text"])
        except (ValueError, KeyError, IndexError, TypeError):
            return body
    return body


def must(r, what):
    body = result(r)
    if (isinstance(r, dict) and r.get("ok") is False) or (isinstance(body, dict) and body.get("ok") is False):
        sys.exit(f"FAILED {what}: {r}")
    return body


def main():
    must(call("material_create", {"package_path": PKG, "name": "M_FoA_BeddingSettle"}), "create")
    ids = {}
    for key, (cls, pos, props) in NODES.items():
        body = must(call("material_add_node", {"material_path": MAT, "expression_class": X + cls, "node_pos": pos,
                                               "properties": props}), f"node {key}")
        ids[key] = body["node_id"]
        if body.get("unknown_props"):
            print("  unknown props on", key, body["unknown_props"])
    for a, out, b, inp in WIRES:
        must(call("material_connect_nodes", {"material_path": MAT, "from_node": ids[a], "from_output": out,
                                             "to_node": ids[b], "to_input": inp}), f"wire {a}->{b}.{inp}")
    for key, prop in OUTPUTS:
        must(call("material_connect_nodes", {"material_path": MAT, "from_node": ids[key], "to_property": prop}), f"out {prop}")
    for text, pos, size, color in COMMENTS:
        must(call("material_add_comment", {"material_path": MAT, "text": text, "node_pos": pos, "size": size,
                                           "color": color, "font_size": 20}), f"comment {text}")
    print("validate", result(call("material_validate", {"material_path": MAT})))
    print("compile", result(call("material_compile", {"material_path": MAT})))
    print("nodes:", len(ids))


main()
