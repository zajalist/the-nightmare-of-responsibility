"""Import the inspected reused Poly Haven boot pair; no textures/material assets are created."""
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc
from build_suit_materials import call, OWNER, FOLDER
from import_modular_clothes import extent

assert not call("editor_get_state")["pie_running"]
lease = hc.lease_acquire(OWNER, ["asset:" + FOLDER + "/SK_FoA_Boots_Worn"], ttl_s=120, wait_s=15)
try:
    name = "SK_FoA_Boots_Worn"
    path = FOLDER + "/" + name
    known = call("asset_registry_query", path_prefix=FOLDER, name_contains=name, limit=10)["assets"]
    skeleton = "/Game/FoA/Characters/Protagonist/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel.metahuman_base_skel"
    if not known:
        stage = Path(tempfile.gettempdir()) / "hayba-asset-connectors/FoA/player_boots"
        stage.mkdir(parents=True, exist_ok=True)
        source = Path("P:/FoA-Assets/character/units_cm/SK_FoA_Boots_Worn.fbx")
        shutil.copy2(source, stage / source.name)
        call("asset_import", source_file=str(stage / source.name), destination_path=FOLDER, asset_type="skeletal_mesh",
             options={"skeleton": skeleton, "create_physics_asset": False, "import_animations": False,
                      "import_materials": False, "import_textures": False, "normal_import_method": "import"})
    data = call("object_get_property", path=path, names=["ImportedBounds", "Skeleton"])["properties"]
    assert skeleton in data["Skeleton"]
    x,y,z = extent(data["ImportedBounds"])
    assert 15<x<30 and 12<y<25 and 15<z<25, (x,y,z)
    call("object_set_property", path=path, properties={"Materials": [{
        "MaterialInterface": "/Game/FoA/Props/rubber_boots/rubber_boots_1k/Materials/rubber_boots_dirty.rubber_boots_dirty",
        "MaterialSlotName": "rubber_boots_dirty", "ImportedMaterialSlotName": "rubber_boots_dirty"}]})
    materials = call("object_get_property", path=path, names=["Materials"])["properties"]["Materials"]
    assert "rubber_boots_dirty.rubber_boots_dirty" in materials
    call("asset_save", asset_paths=[path])
    print("PASS boots imported in centimetres on original MH skeleton, existing rubber material", (x,y,z))
finally:
    hc.release(OWNER, lease)
