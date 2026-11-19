"""Hayba C++ call batches for the sand material graphs (material graphs are Hayba-only), written as JSONL for
Tools/Unreal/hayba_call.py --batch, so long node code goes straight from Tools/Splats/hlsl/*.hlsl into the editor.
  python Tools/Splats/hayba_batches.py OUT_DIR
  -> OUT_DIR/spill_grain.jsonl   M_SandSpill: the baked-grain node (T_SandGrain), title-only comments
     OUT_DIR/morph_mf.jsonl      MF_SplatMorph: the morph offset and look nodes and their parameters
     OUT_DIR/morph_master.jsonl  M_SplatMesh: the Morph static switch between MF_SplatFlow and MF_SplatMorph
     OUT_DIR/slim_flow.jsonl     MF_SplatFlow: one 'Motion' node (offset, offset one shutter ago, look) replaces three copies
     OUT_DIR/slim_master.jsonl   M_SplatMesh: Masked like every instance, the second MF_SplatFlow call removed
     OUT_DIR/lens_sand.jsonl     MF_Dream_Lens: visible black sand (stencil 5) gets no haze, Pro-Mist or halation
     OUT_DIR/spill_sheen.jsonl   M_SandSpill: light-only sheen, glints and rim through a per-pixel Specular (Sheen param)
     OUT_DIR/echo_sand.jsonl     MF_Dream_TimeEcho: visible sand keeps a fifth of the echo, so glints don't trail
     OUT_DIR/lens_night.jsonl    MF_Dream_Lens + M_PP_DreamLens: MPC CineNight, the cinematic night grade (0 = off)
  python Tools/Splats/hayba_batches.py OUT_DIR slim_flow slim_master   # only the named batches
Node ids of nodes these batches add are the editor's next free ids (ClassName_N); check with material_get_info first."""
import json
import os
import sys

H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hlsl")
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SPILL, MESH, MORPH = "/Game/FoA/VFX/Sand/M_SandSpill", "/Game/FoA/VFX/Splats/M_SplatMesh", "/Game/FoA/VFX/Splats/MF_SplatMorph"


def code(name):
    return open(os.path.join(H, name), encoding="utf-8").read()


def write(name, calls):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        for cmd, params in calls:
            fh.write(json.dumps({"cmd": cmd, "params": params}) + "\n")
    print(name, len(calls), "calls")


def link(path, a, b, to_input=None, out=None, out_index=None, to_property=None, fn=False):
    p = {("function_path" if fn else "material_path"): path, "from_node": a}
    if out is not None:
        p["from_output"] = out
    if out_index is not None:
        p["from_output_index"] = out_index
    if to_property:
        p["to_property"] = to_property
    else:
        p["to_node"], p["to_input"] = b, to_input
    return ("material_connect_nodes", p)


def spill_grain():
    m = SPILL
    calls = [("material_add_node", {"material_path": m, "expression_class": "MaterialExpressionTextureObject",
                                    "node_pos": [-1150, 1240],
                                    "properties": {"Texture": "/Game/FoA/VFX/Sand/Textures/T_SandGrain.T_SandGrain"}}),
             ("material_set_node", {"material_path": m, "node_id": "MaterialExpressionCustom_0",
                                    "properties": {"Inputs": [{"InputName": n} for n in ("WP", "Nv", "VC", "Spill", "T", "O", "Tex")],
                                                   "Code": code("spill_grain.hlsl")}}),
             link(m, "MaterialExpressionWorldPosition_0", "MaterialExpressionCustom_0", "WP", out="XYZ"),
             link(m, "MaterialExpressionVertexNormalWS_0", "MaterialExpressionCustom_0", "Nv"),
             link(m, "MaterialExpressionVertexColor_0", "MaterialExpressionCustom_0", "VC", out_index=0),
             link(m, "MaterialExpressionVectorParameter_0", "MaterialExpressionCustom_0", "Spill", out="RGBA"),
             link(m, "MaterialExpressionTime_0", "MaterialExpressionCustom_0", "T"),
             link(m, "MaterialExpressionObjectPositionWS_0", "MaterialExpressionCustom_0", "O", out_index=0),
             link(m, "MaterialExpressionTextureObject_0", "MaterialExpressionCustom_0", "Tex")]
    for i in range(3):                                      # the user's rule: no description bubbles on nodes
        calls.append(("material_set_node", {"material_path": m, "node_id": f"MaterialExpressionVectorParameter_{i}", "properties": {"Desc": ""}}))
    for i, title in enumerate(("Inputs", "Grain sheen and glints", "Feathered rim", "Edge rim")):
        calls.append(("material_set_comment", {"material_path": m, "comment_id": f"MaterialExpressionComment_{i}", "text": title}))
    calls += [("material_validate", {"material_path": m}), ("material_compile", {"material_path": m})]
    write("spill_grain.jsonl", calls)


def morph_mf():
    f = MORPH
    fp = {"function_path": f}
    calls = [("material_function_create", {"package_path": "/Game/FoA/VFX/Splats", "name": "MF_SplatMorph"})]
    for i, (name, typ, y) in enumerate((("Index", "FunctionInput_Scalar", 0), ("RadiusSeed", "FunctionInput_Vector2", 100),
                                       ("Rest", "FunctionInput_Vector3", 200))):
        calls += [("material_add_node", {**fp, "expression_class": "MaterialExpressionFunctionInput", "node_pos": [-900, y],
                                         "properties": {"InputName": name, "InputType": typ, "SortPriority": i}})]
    calls += [("material_add_node", {**fp, "expression_class": "MaterialExpressionTime", "node_pos": [-900, 300], "properties": {}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionTextureObjectParameter", "node_pos": [-900, 400],
                                     "properties": {"ParameterName": "MorphTex"}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionVectorParameter", "node_pos": [-900, 560],
                                     "properties": {"ParameterName": "MorphCfg", "DefaultValue": {"R": 6, "G": 128, "B": 26, "A": 2.5}}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionVectorParameter", "node_pos": [-900, 720],
                                     "properties": {"ParameterName": "SandEvent", "bUseCustomPrimitiveData": True, "PrimitiveDataIndex": 0}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionCustom", "node_pos": [-500, 100],
                                     "properties": {"Description": "Morph", "OutputType": "CMOT_Float3", "Code": code("morph_offset.hlsl"),
                                                    "Inputs": [{"InputName": n} for n in ("Idx", "RadiusSeed", "Rest", "Clock", "Ev", "Cfg", "Tex")]}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionCustom", "node_pos": [-500, 500],
                                     "properties": {"Description": "Morph look", "OutputType": "CMOT_Float4", "Code": code("morph_look.hlsl"),
                                                    "Inputs": [{"InputName": n} for n in ("Idx", "Clock", "Ev", "Cfg", "Tex")]}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionFunctionOutput", "node_pos": [-150, 100],
                                     "properties": {"OutputName": "Offset", "SortPriority": 0}}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionFunctionOutput", "node_pos": [-150, 500],
                                     "properties": {"OutputName": "Look", "SortPriority": 1}})]
    C0, C1 = "MaterialExpressionCustom_0", "MaterialExpressionCustom_1"
    I0, I1, I2 = (f"MaterialExpressionFunctionInput_{i}" for i in range(3))
    T, TX, CFG, EV = "MaterialExpressionTime_0", "MaterialExpressionTextureObjectParameter_0", "MaterialExpressionVectorParameter_0", "MaterialExpressionVectorParameter_1"
    for c, ins in ((C0, (("Idx", I0, None), ("RadiusSeed", I1, None), ("Rest", I2, None), ("Clock", T, None), ("Ev", EV, "RGBA"),
                         ("Cfg", CFG, "RGBA"), ("Tex", TX, None))),
                   (C1, (("Idx", I0, None), ("Clock", T, None), ("Ev", EV, "RGBA"), ("Cfg", CFG, "RGBA"), ("Tex", TX, None)))):
        for pin, src, out in ins:
            calls.append(link(f, src, c, pin, out=out, fn=True))
    calls += [("material_connect_nodes", {**fp, "from_node": C0, "to_node": "MaterialExpressionFunctionOutput_0", "to_input_index": 0}),
              ("material_connect_nodes", {**fp, "from_node": C1, "to_node": "MaterialExpressionFunctionOutput_1", "to_input_index": 0}),
              ("material_add_comment", {**fp, "text": "Morph", "node_pos": [-940, -60], "size": [1000, 900], "color": [0.3, 0.22, 0.1]}),
              ("material_validate", fp), ("material_compile", fp)]
    write("morph_mf.jsonl", calls)


def morph_master():
    m = MESH
    mp = {"material_path": m}
    F0 = "MaterialExpressionMaterialFunctionCall_0"           # MF_SplatFlow (now)
    F1 = "MaterialExpressionMaterialFunctionCall_1"           # MF_SplatFlow (one shutter ago)
    BB = "MaterialExpressionMaterialFunctionCall_2"           # MF_SplatBillboard
    MF = "MaterialExpressionMaterialFunctionCall_4"           # MF_SplatMorph (new)
    SH = "MaterialExpressionCustom_0"                         # Shade splat
    S_OFF, S_PREV, S_LOOK = (f"MaterialExpressionStaticSwitchParameter_{i}" for i in range(3))
    calls = [("material_add_node", {**mp, "expression_class": "MaterialExpressionTextureCoordinate", "node_pos": [-2320, 420],
                                    "properties": {"CoordinateIndex": 2}}),
             ("material_add_node", {**mp, "expression_class": "MaterialExpressionComponentMask", "node_pos": [-2160, 420],
                                    "properties": {"R": True, "G": False, "B": False, "A": False}}),
             ("material_add_node", {**mp, "expression_class": "MaterialExpressionMaterialFunctionCall", "node_pos": [-2000, 400],
                                    "properties": {"MaterialFunction": f"{MORPH}.MF_SplatMorph"}})]
    for i, y in enumerate((-60, 120, 260)):
        calls.append(("material_add_node", {**mp, "expression_class": "MaterialExpressionStaticSwitchParameter", "node_pos": [-1700, y],
                                            "properties": {"ParameterName": "Morph", "DefaultValue": False}}))
    TC, CM = "MaterialExpressionTextureCoordinate_6", "MaterialExpressionComponentMask_3"
    calls += [link(m, TC, CM, "Input"),
              ("material_connect_nodes", {**mp, "from_node": CM, "to_node": MF, "to_input_index": 0}),
              ("material_connect_nodes", {**mp, "from_node": "MaterialExpressionTextureCoordinate_0", "to_node": MF, "to_input_index": 1}),
              ("material_connect_nodes", {**mp, "from_node": "MaterialExpressionLocalPosition_0", "from_output": "XYZ", "to_node": MF, "to_input_index": 2}),
              # switches: True = morph, False = flow
              link(m, MF, S_OFF, "True", out="Offset"), link(m, F0, S_OFF, "False", out="Offset"),
              link(m, MF, S_PREV, "True", out="Offset"), link(m, F1, S_PREV, "False", out="Offset"),
              link(m, MF, S_LOOK, "True", out="Look"), link(m, F0, S_LOOK, "False", out="Look"),
              # consumers now read the switches
              ("material_connect_nodes", {**mp, "from_node": S_OFF, "to_node": BB, "to_input_index": 2}),
              ("material_connect_nodes", {**mp, "from_node": S_PREV, "to_node": BB, "to_input_index": 3}),
              ("material_connect_nodes", {**mp, "from_node": S_LOOK, "to_node": BB, "to_input_index": 4}),
              link(m, S_LOOK, SH, "Look"), link(m, S_OFF, SH, "Offset"),
              link(m, S_LOOK, "MaterialExpressionComponentMask_0", "Input"),
              ("material_add_comment", {**mp, "text": "Morph or flow", "node_pos": [-2340, 380], "size": [760, 260], "color": [0.12, 0.26, 0.16]}),
              ("material_validate", mp), ("material_compile", mp)]
    write("morph_master.jsonl", calls)


def spill_specular():
    """A Specular parameter on M_SandSpill (default 0.12, a third of the engine's 0.5): at grazing views a wet-looking
    lobe under the moonbeam read as grey fill; black sand should give a thin rim and a dim grain sheen only."""
    m = SPILL
    write("spill_specular.jsonl", [
        ("material_add_node", {"material_path": m, "expression_class": "MaterialExpressionScalarParameter", "node_pos": [-1150, 1340],
                               "properties": {"ParameterName": "Specular", "DefaultValue": 0.12}}),
        ("material_connect_nodes", {"material_path": m, "from_node": "MaterialExpressionScalarParameter_0", "to_property": "specular"}),
        ("material_set_comment", {"material_path": m, "comment_id": "MaterialExpressionComment_0", "size": [330, 1500]}),
        ("material_validate", {"material_path": m}), ("material_compile", {"material_path": m})])


def slim_flow():
    """MF_SplatFlow's offset node ran twice (now, and one shutter ago for streaks) and its look node re-ran the same
    behaviour code: three inlined copies, ~8.4k vertex instructions. flow_eval.hlsl does all three in one [loop] body
    (Tools/Splats/hlsl/bench: 9287 -> 4422 DXIL instructions), with OffsetPrev and Look as additional outputs."""
    f = "/Game/FoA/VFX/Splats/MF_SplatFlow"
    fp = {"function_path": f}
    C = "MaterialExpressionCustom_0"
    pins = (("RestPos", "MaterialExpressionFunctionInput_1", None), ("RadiusSeed", "MaterialExpressionFunctionInput_2", None),
            ("Clock", "MaterialExpressionTime_0", None), ("Mode", "MaterialExpressionAppendVector_1", None),
            ("TimeCfg", "MaterialExpressionVectorParameter_0", "RGBA"), ("Flow", "MaterialExpressionVectorParameter_1", "RGBA"),
            ("Shape", "MaterialExpressionVectorParameter_2", "RGBA"), ("Place", "MaterialExpressionVectorParameter_3", "RGBA"),
            ("Tune", "MaterialExpressionVectorParameter_4", "RGBA"), ("Dissolve", "MaterialExpressionVectorParameter_5", "RGBA"))
    calls = [("material_set_node", {**fp, "node_id": C, "properties": {
                 "Description": "Motion", "OutputType": "CMOT_Float3", "Code": code("gen/MF_SplatFlow_Motion.compact.hlsl"),
                 "Inputs": [{"InputName": n} for n, _, _ in pins],
                 "AdditionalOutputs": [{"OutputName": "OffsetPrev", "OutputType": "CMOT_Float3"},
                                       {"OutputName": "Look", "OutputType": "CMOT_Float4"}]}})]
    calls += [link(f, src, C, pin, out=out, fn=True) for pin, src, out in pins]
    calls += [("material_delete_node", {**fp, "node_id": "MaterialExpressionCustom_1"}),        # the old look node
              ("material_delete_node", {**fp, "node_id": "MaterialExpressionFunctionInput_0"}),  # 'Previous'
              ("material_set_node", {**fp, "node_id": "MaterialExpressionFunctionOutput_1", "node_pos": [-340, 270]}),
              ("material_add_node", {**fp, "expression_class": "MaterialExpressionFunctionOutput", "node_pos": [-340, 150],
                                     "properties": {"OutputName": "OffsetPrev", "SortPriority": 2}}),
              ("material_connect_nodes", {**fp, "from_node": C, "from_output_index": 1, "to_node": "MaterialExpressionFunctionOutput_2", "to_input_index": 0}),
              ("material_connect_nodes", {**fp, "from_node": C, "from_output_index": 2, "to_node": "MaterialExpressionFunctionOutput_1", "to_input_index": 0}),
              ("material_delete_comment", {**fp, "comment_id": "MaterialExpressionComment_3"})]
    for cid, title in (("MaterialExpressionComment_0", "Splat inputs"), ("MaterialExpressionComment_1", "Motion parameters"),
                       ("MaterialExpressionComment_2", "Motion")):            # the user's rule: titles only
        calls.append(("material_set_comment", {**fp, "comment_id": cid, "text": title}))
    calls.append(("material_compile", fp))
    write("slim_flow.jsonl", calls)


def slim_master():
    """M_SplatMesh: Masked (all ten instances overrode Translucent to Masked, so the Translucent map was compiled for
    nothing), and the shutter-ago MF_SplatFlow call replaced by the merged node's OffsetPrev output."""
    m = MESH
    mp = {"material_path": m}
    write("slim_master.jsonl", [
        ("material_set_property", {**mp, "properties": {"blend_mode": "Masked"}}),
        ("material_connect_nodes", {**mp, "from_node": "MaterialExpressionMaterialFunctionCall_0", "from_output": "OffsetPrev",
                                    "to_node": "MaterialExpressionMaterialFunctionCall_2", "to_input_index": 3}),
        ("material_delete_node", {**mp, "node_id": "MaterialExpressionMaterialFunctionCall_1"}),
        ("material_delete_node", {**mp, "node_id": "MaterialExpressionConstant_0"}),
        ("material_validate", mp), ("material_compile", mp)])


def lens_sand():
    """MF_Dream_Lens (post, after tonemapping): the Pro-Mist screen and halation of a bright moonbeam lifted the black
    sand inside it by ~0.07 luma. Stencil 5, depth-gated as in MF_Dream_SandWarp, opts sand out of the glow.
    Take M_PP_DreamLens off PP_DreamMono before running this (editor rules), put it back after."""
    f = "/Game/FoA/PostProcess/Functions/MF_Dream_Lens"
    fp = {"function_path": f}
    C = "MaterialExpressionCustom_0"
    calls = []
    for i, (sid, y) in enumerate((("PPI_CustomStencil", 830), ("PPI_SceneDepth", 960), ("PPI_CustomDepth", 1090)), 1):
        calls.append(("material_add_node", {**fp, "expression_class": "MaterialExpressionSceneTexture", "node_pos": [-1000, y],
                                            "properties": {"SceneTextureId": sid}}))
    pins = [("UV", "MaterialExpressionFunctionInput_0"), ("Look", "MaterialExpressionFunctionInput_1"),
            ("Glitch", "MaterialExpressionFunctionInput_2"), ("Breath", "MaterialExpressionFunctionInput_3"),
            ("ReduceMotion", "MaterialExpressionFunctionInput_4"), ("Taps", "MaterialExpressionFunctionInput_5"),
            ("SceneColor", "MaterialExpressionSceneTexture_0"), ("Stencil", "MaterialExpressionSceneTexture_1"),
            ("Depth", "MaterialExpressionSceneTexture_2"), ("CDepth", "MaterialExpressionSceneTexture_3")]
    calls.append(("material_set_node", {**fp, "node_id": C, "properties": {"Inputs": [{"InputName": n} for n, _ in pins],
                                                                            "Code": code("pp_lens.hlsl")}}))
    calls += [("material_connect_nodes", {**fp, "from_node": src, "from_output_index": 0, "to_node": C, "to_input": pin}) for pin, src in pins]
    calls += [("material_compile", fp), ("material_compile", {"material_path": "/Game/FoA/PostProcess/M_PP_DreamLens"})]
    write("lens_sand.jsonl", calls)


def spill_sheen():
    """M_SandSpill: the goo has no specular; sparse sparkle cells, rare glints and a geometric rim carry it (Sheen
    vector), so the sand only shows where real light falls. The grain node's alpha becomes the Specular input."""
    m = SPILL
    mp = {"material_path": m}
    C = "MaterialExpressionCustom_0"
    RGB, A = "MaterialExpressionComponentMask_0", "MaterialExpressionComponentMask_1"
    pins = (("WP", "MaterialExpressionWorldPosition_0", "XYZ"), ("Nv", "MaterialExpressionVertexNormalWS_0", None),
            ("VC", "MaterialExpressionVertexColor_0", 0), ("Spill", "MaterialExpressionVectorParameter_0", "RGBA"),
            ("T", "MaterialExpressionTime_0", None), ("O", "MaterialExpressionObjectPositionWS_0", 0),
            ("Tex", "MaterialExpressionTextureObject_0", None), ("V", "MaterialExpressionCameraVectorWS_0", None),
            ("Sheen", "MaterialExpressionVectorParameter_3", "RGBA"), ("Rim", "MaterialExpressionVectorParameter_2", "RGBA"),
            ("VA", "MaterialExpressionVertexColor_0", 4))
    calls = [("material_add_node", {**mp, "expression_class": "MaterialExpressionVectorParameter", "node_pos": [-1150, 1420],
                                    "properties": {"ParameterName": "Sheen", "DefaultValue": {"R": 0.12, "G": 0.6, "B": 0.004, "A": 0.8}}}),
             ("material_add_node", {**mp, "expression_class": "MaterialExpressionComponentMask", "node_pos": [-540, 160],
                                    "properties": {"R": True, "G": True, "B": True, "A": False}}),
             ("material_add_node", {**mp, "expression_class": "MaterialExpressionComponentMask", "node_pos": [-540, 320],
                                    "properties": {"R": False, "G": False, "B": False, "A": True}}),
             ("material_set_node", {**mp, "node_id": C, "properties": {"Inputs": [{"InputName": n} for n, _, _ in pins],
                                                                        "Code": code("spill_grain.hlsl")}})]
    calls += [link(m, src, C, pin, out=out if isinstance(out, str) else None, out_index=out if isinstance(out, int) else None)
              for pin, src, out in pins]
    calls += [("material_connect_nodes", {**mp, "from_node": C, "to_node": RGB, "to_input_index": 0}),
              ("material_connect_nodes", {**mp, "from_node": C, "to_node": A, "to_input_index": 0}),
              ("material_connect_nodes", {**mp, "from_node": RGB, "to_node": "MaterialExpressionNormalize_0", "to_input_index": 0}),
              ("material_connect_nodes", {**mp, "from_node": RGB, "to_node": "MaterialExpressionDotProduct_0", "to_input_index": 0}),
              ("material_connect_nodes", {**mp, "from_node": RGB, "to_node": "MaterialExpressionDotProduct_0", "to_input_index": 1}),
              ("material_connect_nodes", {**mp, "from_node": A, "to_property": "specular"}),
              ("material_delete_node", {**mp, "node_id": "MaterialExpressionScalarParameter_0"}),
              ("material_set_comment", {**mp, "comment_id": "MaterialExpressionComment_0", "size": [330, 1580]}),
              ("material_set_comment", {**mp, "comment_id": "MaterialExpressionComment_1", "size": [700, 300]}),
              ("material_validate", mp), ("material_compile", mp)]
    write("spill_sheen.jsonl", calls)


def echo_sand():
    """MF_Dream_TimeEcho: every highlight trails ~15 px of vertical ghosts; on the sand that turned each moon glint into
    a falling streak. Stencil 5 (depth-gated) keeps 20% of the echo there. Take M_PP_DreamMono off PP_DreamMono first."""
    f = "/Game/FoA/PostProcess/Functions/MF_Dream_TimeEcho"
    fp = {"function_path": f}
    C = "MaterialExpressionCustom_0"
    calls = [("material_add_node", {**fp, "expression_class": "MaterialExpressionSceneTexture", "node_pos": [-1000, y],
                                    "properties": {"SceneTextureId": sid}})
             for sid, y in (("PPI_CustomStencil", 1000), ("PPI_SceneDepth", 1130), ("PPI_CustomDepth", 1260))]
    pins = [("UV", "MaterialExpressionFunctionInput_0"), ("Strength", "MaterialExpressionFunctionInput_1"),
            ("Shape", "MaterialExpressionFunctionInput_2"), ("ReduceMotion", "MaterialExpressionFunctionInput_3"),
            ("Taps", "MaterialExpressionFunctionInput_4"), ("SceneColor", "MaterialExpressionSceneTexture_0"),
            ("Vel", "MaterialExpressionSceneTexture_1"), ("Dir", "MaterialExpressionFunctionInput_5"),
            ("Stencil", "MaterialExpressionSceneTexture_2"), ("Depth", "MaterialExpressionSceneTexture_3"),
            ("CDepth", "MaterialExpressionSceneTexture_4")]
    calls.append(("material_set_node", {**fp, "node_id": C, "properties": {"Inputs": [{"InputName": n} for n, _ in pins],
                                                                            "Code": code("pp_echo.hlsl")}}))
    calls += [("material_connect_nodes", {**fp, "from_node": src, "from_output_index": 0, "to_node": C, "to_input": pin}) for pin, src in pins]
    calls += [("material_compile", fp), ("material_compile", {"material_path": "/Game/FoA/PostProcess/M_PP_DreamMono"})]
    write("echo_sand.jsonl", calls)


def lens_night():
    """CineNight (MPC_Dream scalar, default 0; add it to the MPC first): a night grade in the lens pass that sequences
    key (LS_WakeUp), so gameplay exposure stays as approved. The new function input defaults to 0, so the material
    compiles before it is wired. Take M_PP_DreamLens off PP_DreamMono first."""
    f = "/Game/FoA/PostProcess/Functions/MF_Dream_Lens"
    fp = {"function_path": f}
    m = "/Game/FoA/PostProcess/M_PP_DreamLens"
    mp = {"material_path": m}
    C = "MaterialExpressionCustom_0"
    pins = [("UV", "MaterialExpressionFunctionInput_0"), ("Look", "MaterialExpressionFunctionInput_1"),
            ("Glitch", "MaterialExpressionFunctionInput_2"), ("Breath", "MaterialExpressionFunctionInput_3"),
            ("ReduceMotion", "MaterialExpressionFunctionInput_4"), ("Taps", "MaterialExpressionFunctionInput_5"),
            ("SceneColor", "MaterialExpressionSceneTexture_0"), ("Stencil", "MaterialExpressionSceneTexture_1"),
            ("Depth", "MaterialExpressionSceneTexture_2"), ("CDepth", "MaterialExpressionSceneTexture_3"),
            ("Night", "MaterialExpressionFunctionInput_6")]
    calls = [("material_add_node", {**fp, "expression_class": "MaterialExpressionFunctionInput", "node_pos": [-1000, 1220],
                                    "properties": {"InputName": "Night", "InputType": "FunctionInput_Scalar", "SortPriority": 6,
                                                   "bUsePreviewValueAsDefault": True, "PreviewValue": {"X": 0.0, "Y": 0.0, "Z": 0.0, "W": 0.0}}}),
             ("material_set_node", {**fp, "node_id": C, "properties": {"Inputs": [{"InputName": n} for n, _ in pins],
                                                                        "Code": code("pp_lens.hlsl")}})]
    calls += [("material_connect_nodes", {**fp, "from_node": src, "from_output_index": 0, "to_node": C, "to_input": pin}) for pin, src in pins]
    calls += [("material_compile", fp),
              ("material_add_node", {**mp, "expression_class": "MaterialExpressionCollectionParameter", "node_pos": [-1450, 520],
                                     "properties": {"Collection": "/Game/FoA/PostProcess/MPC_Dream.MPC_Dream", "ParameterName": "CineNight"}}),
              ("material_validate", mp)]
    write("lens_night.jsonl", calls)


BATCHES = {f.__name__: f for f in (spill_grain, morph_mf, morph_master, spill_specular, slim_flow, slim_master, lens_sand,
                                   spill_sheen, echo_sand, lens_night)}
for name in sys.argv[2:] or BATCHES:
    BATCHES[name]()
