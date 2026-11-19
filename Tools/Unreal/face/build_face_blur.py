"""M_PP_FaceBlur: the always-on face blur (post-process, after tonemapping, priority 2 = after M_PP_DreamLens).
Hayba C++ material calls only, written as JSONL for hayba_call.py --batch. HLSL lives in hlsl/pp_face_blur.hlsl.
  python Tools/Unreal/face/build_face_blur.py create   # new material + graph (run once, on an empty material)
  python Tools/Unreal/face/build_face_blur.py code     # push the HLSL into the existing Custom node, compile
  python Tools/Unreal/face/build_face_blur.py wire     # reconnect the Custom node pins (after an Inputs change)
  python Tools/Unreal/face/build_face_blur.py v10      # once: add the FaceForward/FaceRight inputs for the face-only mask
Then: python Tools/Unreal/hayba_call.py --batch Saved/FaceShots/face_blur_<phase>.jsonl (inside a lease on the asset).
Never compile it while it is a blendable on the editor PP_DreamMono: take it off first (editor-rules 9)."""
import json
import os
import sys

M = os.environ.get("FOA_MAT", "/Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur")  # FOA_MAT: a TMP_ preview copy
MP = {"material_path": M}
MPC = "/Game/FoA/PostProcess/MPC_Dream.MPC_Dream"
C = "MaterialExpressionCustom_0"
HERE = os.path.dirname(os.path.abspath(__file__))
CODE = open(os.path.join(HERE, "hlsl", "pp_face_blur.hlsl"), encoding="utf-8").read()
# Custom node pin, source node, source output, node class, properties, graph position
PINS = [("UV", "MaterialExpressionScreenPosition_0", "ViewportUV", "MaterialExpressionScreenPosition", {}, (-700, 0)),
        ("SceneColor", "MaterialExpressionSceneTexture_0", 0, "MaterialExpressionSceneTexture", {"SceneTextureId": "PPI_PostProcessInput0"}, (-700, 110)),
        ("Stencil", "MaterialExpressionSceneTexture_1", 0, "MaterialExpressionSceneTexture", {"SceneTextureId": "PPI_CustomStencil"}, (-700, 220)),
        ("Depth", "MaterialExpressionSceneTexture_2", 0, "MaterialExpressionSceneTexture", {"SceneTextureId": "PPI_SceneDepth"}, (-700, 330)),
        ("CDepth", "MaterialExpressionSceneTexture_3", 0, "MaterialExpressionSceneTexture", {"SceneTextureId": "PPI_CustomDepth"}, (-700, 440)),
        ("CamPos", "MaterialExpressionCameraPositionWS_0", 0, "MaterialExpressionCameraPositionWS", {}, (-700, 550)),
        ("Amount", "MaterialExpressionCollectionParameter_0", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "FaceSlip"}, (-700, 660)),
        ("FaceOrigin", "MaterialExpressionCollectionParameter_1", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "FaceOrigin"}, (-700, 770)),
        ("ReduceMotion", "MaterialExpressionCollectionParameter_2", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "ReduceMotion"}, (-700, 880)),
        ("Breath", "MaterialExpressionCollectionParameter_3", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "Breath"}, (-700, 990)),
        ("LensLook", "MaterialExpressionCollectionParameter_4", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "LensLook"}, (-700, 1100)),
        ("FaceForward", "MaterialExpressionCollectionParameter_5", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "FaceForward"}, (-700, 1210)),
        ("FaceRight", "MaterialExpressionCollectionParameter_6", 0, "MaterialExpressionCollectionParameter", {"ParameterName": "FaceRight"}, (-700, 1320))]
CUSTOM = {"Inputs": [{"InputName": p[0]} for p in PINS], "Code": CODE, "OutputType": "CMOT_Float3", "Description": "FaceBlur"}


def create():
    calls = [("material_create", {"package_path": os.path.dirname(M), "name": os.path.basename(M)}),
             ("material_set_property", {**MP, "properties": {"domain": "MD_PostProcess"}}),
             ("object_set_property", {"path": M, "properties": {"BlendableLocation": "BL_SceneColorAfterTonemapping",
                                                                 "BlendablePriority": 2}})]
    for pin, node, out, cls, props, pos in PINS:
        if cls == "MaterialExpressionCollectionParameter":
            props = {"Collection": MPC, **props}
        calls.append(("material_add_node", {**MP, "expression_class": cls, "node_pos": list(pos), "properties": props}))
    calls.append(("material_add_node", {**MP, "expression_class": "MaterialExpressionCustom", "node_pos": [-300, 0],
                                        "properties": CUSTOM}))
    calls += wires()
    calls += [("material_connect_nodes", {**MP, "from_node": C, "from_output_index": 0, "to_property": "EmissiveColor"}),
              ("material_add_comment", {**MP, "text": "Scene and MPC inputs", "node_pos": [-760, -60], "size": [380, 1260],
                                        "color": [0.12, 0.2, 0.3]}),
              ("material_add_comment", {**MP, "text": "Face blur", "node_pos": [-340, -60], "size": [300, 200],
                                        "color": [0.3, 0.18, 0.12]}),
              ("material_validate", MP), ("material_compile", MP)]
    return calls


def wires():
    calls = []
    for pin, node, out, *_ in PINS:
        p = {**MP, "from_node": node, "to_node": C, "to_input": pin}
        p["from_output" if isinstance(out, str) else "from_output_index"] = out
        calls.append(("material_connect_nodes", p))
    return calls


def code():
    """Code only: setting Inputs again recreates the pins and drops their wires (then run 'wire')."""
    return [("material_set_node", {**MP, "node_id": C, "properties": {"Code": CODE}}), ("material_validate", MP),
            ("material_compile", MP)]


def wire():
    return wires() + [("material_validate", MP), ("material_compile", MP)]


def rollback():
    """Back to the last good shader (Saved/FaceShots/pp_face_blur_v8.hlsl.bak) on the same pins, compile."""
    old = open("P:/FoA/Saved/FaceShots/pp_face_blur_v8.hlsl.bak", encoding="utf-8").read()
    return ([("material_set_node", {**MP, "node_id": C, "properties": {**CUSTOM, "Code": old}})] + wires()
            + [("material_validate", MP), ("material_compile", MP)])


def v10():
    """Face-only mask: add the FaceForward and FaceRight MPC nodes, new Inputs + Code (recreates the pins), rewire,
    grow the inputs comment over them, compile."""
    calls = []
    for pin, node, out, cls, props, pos in PINS[-2:]:
        calls.append(("material_add_node", {**MP, "expression_class": cls, "node_pos": list(pos),
                                            "properties": {"Collection": MPC, **props}}))
    calls.append(("material_set_node", {**MP, "node_id": C, "properties": CUSTOM}))
    calls += wires()
    calls += [("material_set_comment", {**MP, "comment_id": "MaterialExpressionComment_0", "size": [380, 1480]}),
              ("material_validate", MP), ("material_compile", MP)]
    return calls


if __name__ == "__main__":
    phase = sys.argv[1]
    calls = {"create": create, "code": code, "wire": wire, "v10": v10, "rollback": rollback}[phase]()
    out = f"P:/FoA/Saved/FaceShots/face_blur_{phase}{'_' + os.path.basename(M) if 'FOA_MAT' in os.environ else ''}.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for cmd, params in calls:
            fh.write(json.dumps({"cmd": cmd, "params": params}) + "\n")
    print(out, len(calls), "calls")
