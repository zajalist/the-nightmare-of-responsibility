"""One UV-based cloth master for the free fitted suit, built with Hayba C++ material tools."""
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc

FOLDER = "/Game/FoA/Characters/Player/Clothing"
MASTER = FOLDER + "/M_CharacterCloth"
OWNER = "character_resume"


def call(command, **params):
    reply = hc.call(command, params, owner=OWNER, timeout=45)
    assert reply.get("ok"), reply
    data = reply.get("data", {})
    assert data.get("ok", True), data
    return data


def main():
    assert not call("editor_get_state")["pie_running"], "Exit PIE before editing clothing materials"
    lease = hc.lease_acquire(OWNER, ["asset:/Game/FoA/Characters"], ttl_s=120, wait_s=20)
    try:
        existing = {a["name"] for a in call("asset_registry_query", path_prefix=FOLDER, limit=50)["assets"]}
        stage = Path(tempfile.gettempdir()) / "hayba-asset-connectors/FoA/character_materials"
        stage.mkdir(parents=True, exist_ok=True)
        source = Path("P:/FoA-Assets/character/suit_fit_final")
        for name, filename in (
                ("T_Suit_Reference_BaseColor", "T_Suit_Reference_BaseColor.png"),
                ("T_Suit_Normal", "T_SK_Garment_Suit_Worn_uniform_1001_normal_png.png"),
                ("T_Suit_Button_Normal", "T_SK_Garment_Suit_Worn_Button_1061_Button_normal_png.png")):
            disk = Path("P:/FoA/Content/FoA/Characters/Player/Clothing") / (name + ".uasset")
            if name not in existing:
                shutil.copy2(source / filename, stage / (name + ".png"))
                call("asset_import", source_file=str(stage / (name + ".png")), destination_path=FOLDER, asset_type="texture")
            if "Normal" in name:
                call("texture_set_settings", path=FOLDER + "/" + name, properties={
                    "compression_settings": "Normalmap", "srgb": False, "flip_green_channel": True})
        disk = Path("P:/FoA/Content/FoA/Characters/Player/Clothing/M_CharacterCloth.uasset")
        if "M_CharacterCloth" not in existing:
            call("material_create", package_path=FOLDER, name="M_CharacterCloth")
        info = call("material_get_info", path=MASTER)
        call("material_set_property", material_path=MASTER, properties={"two_sided": True})
        call("material_set_property", material_path=MASTER, properties={"used_with_skeletal_meshes": True})
        nodes = {}
        for name, cls, xy, props in (
                ("albedo", "MaterialExpressionTextureSampleParameter2D", [-700, 0], {"ParameterName": "Albedo", "Texture": FOLDER + "/T_Suit_Reference_BaseColor.T_Suit_Reference_BaseColor"}),
                ("tint", "MaterialExpressionVectorParameter", [-700, 260], {"ParameterName": "Tint", "DefaultValue": [1, 1, 1, 1]}),
                ("color", "MaterialExpressionMultiply", [-400, 0], {}),
                ("normal", "MaterialExpressionTextureSampleParameter2D", [-400, 220], {"ParameterName": "Normal", "Texture": FOLDER + "/T_Suit_Normal.T_Suit_Normal", "SamplerType": "SAMPLERTYPE_Normal"}),
                ("rough", "MaterialExpressionScalarParameter", [-150, 500], {"ParameterName": "Roughness", "DefaultValue": 0.82}),
                ("spec", "MaterialExpressionScalarParameter", [-150, 680], {"ParameterName": "Specular", "DefaultValue": 0.25}),
                ("metal", "MaterialExpressionScalarParameter", [-150, 860], {"ParameterName": "Metallic", "DefaultValue": 0})):
            previous = next((e for e in info["expressions"] if e.get("class", "").endswith(cls)
                             and [e.get("x"), e.get("y")] == xy), None)
            nodes[name] = previous["id"] if previous else call("material_add_node", material_path=MASTER, expression_class=cls, node_pos=xy, properties=props)["node_id"]
        for a, b, pin in (("albedo", "color", "A"), ("tint", "color", "B")):
            call("material_connect_nodes", material_path=MASTER, from_node=nodes[a], from_output_index=0, to_node=nodes[b], to_input=pin)
        for name, output in (("color", "base_color"), ("normal", "normal"), ("rough", "roughness"), ("spec", "specular"), ("metal", "metallic")):
            call("material_connect_nodes", material_path=MASTER, from_node=nodes[name], from_output_index=0, to_property=output)
        if not info.get("comments"):
            call("material_add_comment", material_path=MASTER, text="Cloth texture", node_pos=[-760, -60], size=[700, 480], color=[0.22, 0.4, 0.2])
            call("material_add_comment", material_path=MASTER, text="Surface response", node_pos=[-220, 450], size=[420, 620], color=[0.3, 0.3, 0.3])
        assert len(call("material_get_info", path=MASTER)["expressions"]) == 7, "Cloth master is incomplete"
        valid = call("material_validate", material_path=MASTER)
        assert not valid.get("problems"), valid
        compiled = call("material_compile", material_path=MASTER)
        assert not compiled.get("has_errors") and not compiled.get("errors"), compiled
        for name, texture, normal, tint, rough in (
                ("MI_Suit_Cloth", FOLDER + "/T_Suit_Reference_BaseColor", FOLDER + "/T_Suit_Normal", [1, 1, 1, 1], 0.82),
                ("MI_Suit_ButtonDark", "/Engine/EngineResources/WhiteSquareTexture", FOLDER + "/T_Suit_Button_Normal", [0.035, 0.035, 0.035, 1], 0.5),
                ("MI_Suit_ButtonGreen", "/Engine/EngineResources/WhiteSquareTexture", FOLDER + "/T_Suit_Button_Normal", [0.035, 0.38, 0.10, 1], 0.4)):
            call("material_create_instance", parent_material_path=MASTER, package_path=FOLDER, name=name)
            for param, value in (("Albedo", texture), ("Normal", normal), ("Tint", tint), ("Roughness", rough)):
                call("material_set_param", instance_path=FOLDER + "/" + name, param_name=param, value=value)
        print("Suit cloth master compiled; UV atlas and original normals shared by cloth/buttons")
        assets = call("asset_registry_query", path_prefix=FOLDER, limit=50)["assets"]
        call("asset_save", asset_paths=[a["path"] for a in assets])
    finally:
        hc.release(OWNER, lease)


if __name__ == "__main__":
    main()
