"""Import inspected, staged wardrobe parts after editor recovery; player coverage/visibility is a separate wiring step."""
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc
from build_suit_materials import call, OWNER, FOLDER, MASTER


def extent(text):
    match = re.search(r"BoxExtent=\(X=([-+0-9.eE]+),Y=([-+0-9.eE]+),Z=([-+0-9.eE]+)\)", text)
    assert match, text
    return tuple(float(v) for v in match.groups())


assert extent("(Origin=(X=0,Y=0,Z=0),BoxExtent=(X=23.8,Y=17,Z=46.2))") == (23.8, 17.0, 46.2)


def main():
    assert not call("editor_get_state")["pie_running"], "Wait for editor recovery and exit PIE"
    lease = hc.lease_acquire(OWNER, ["asset:/Game/FoA/Characters"], ttl_s=120, wait_s=20)
    try:
        known = {a["name"] for a in call("asset_registry_query", path_prefix=FOLDER, limit=50)["assets"]}
        original = call("object_get_property", path=FOLDER + "/SK_FoA_Suit", names=["Skeleton"])
        skeleton = original["properties"]["Skeleton"].split("'")[1]
        stage = Path(tempfile.gettempdir()) / "hayba-asset-connectors/FoA/modular_clothes"
        stage.mkdir(parents=True, exist_ok=True)
        imported = []
        for garment in ("Shirt", "Trousers", "Tie", "Socks"):
            name = "SK_FoA_" + garment
            path = FOLDER + "/" + name
            if name not in known:
                source = Path("P:/FoA-Assets/character/units_cm") / (name + ".fbx")
                assert source.is_file()
                target = stage / source.name
                shutil.copy2(source, target)
                call("asset_import", source_file=str(target), destination_path=FOLDER, asset_type="skeletal_mesh",
                     options={"skeleton": skeleton, "create_physics_asset": False, "import_animations": False,
                              "import_materials": False, "import_textures": False, "normal_import_method": "import"})
            data = call("object_get_property", path=path, names=["ImportedBounds", "Skeleton"])["properties"]
            x, y, z = extent(data["ImportedBounds"])
            assert data["Skeleton"] == original["properties"]["Skeleton"], garment
            assert ((1 < x < 15 and 8 < z < 35) if garment == "Tie" else
                    (10 < x < 40 and 4 < z < 20) if garment == "Socks" else
                    (10 < x < 40 and 20 < z < 70)), (garment, x, y, z)
            imported.append(path)
            print(garment, "centimetre extent", (x,y,z))
        call("material_create_instance", parent_material_path=MASTER, package_path=FOLDER, name="MI_Socks_Dark")
        for param,value in (("Albedo", "/Engine/EngineResources/WhiteSquareTexture"),
                            ("Normal", "/Engine/EngineMaterials/DefaultNormal"),
                            ("Tint", [.045,.045,.045,1]), ("Roughness", .9)):
            call("material_set_param", instance_path=FOLDER + "/MI_Socks_Dark", param_name=param, value=value)
        call("asset_save", asset_paths=imported + [FOLDER + "/MI_Socks_Dark"])
        print("Imported modular meshes only; assign materials and validate player coverage before enabling garment wins")
    finally:
        hc.release(OWNER, lease)


if __name__ == "__main__":
    main()
