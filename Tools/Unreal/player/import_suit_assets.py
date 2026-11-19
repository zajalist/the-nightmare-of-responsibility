"""Import the inspected free suit and its masked body through Hayba; original MetaHuman assets stay intact."""
import json
import os
import subprocess
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc

DEST = "/Game/FoA/Characters/Player/Clothing"
SOURCE = Path("P:/FoA-Assets/character/units_cm")
BODY = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh"
OWNER = "character_resume"
log = []


def call(name, **params):
    reply = hc.call(name, params, owner=OWNER, timeout=45)
    log.append({"command": name, "params": params, "reply": reply})
    assert reply.get("ok"), reply
    data = reply.get("data", {})
    assert data.get("ok", True), data
    return data


def main():
    assert not call("editor_get_state")["pie_running"], "Exit PIE before importing clothing"
    lease = hc.lease_acquire(OWNER, ["asset:" + DEST], ttl_s=90, wait_s=20)
    created_suited = False
    try:
        props = call("object_get_property", path=BODY, names=["Skeleton", "PostProcessAnimBlueprint", "Materials"])["properties"]
        skeleton = props["Skeleton"].split("'")[1]
        stage = Path(tempfile.gettempdir()) / "hayba-asset-connectors/FoA/character_resume"
        stage.mkdir(parents=True, exist_ok=True)
        for name, source_name in (("SK_FoA_Suit", "SK_FoA_Suit"), ("SK_FoA_Body_Suited", "SK_FoA_Body_Suited")):
            disk = Path("P:/FoA/Content") / DEST.removeprefix("/Game/") / (name + ".uasset")
            if disk.is_file():
                continue
            source = SOURCE / (source_name + ".fbx")
            assert source.is_file() and source.stat().st_size > 100000
            target = stage / (name + ".fbx")
            shutil.copy2(source, target)
            call("asset_import", source_file=str(target), destination_path=DEST, asset_type="skeletal_mesh",
                 options={"skeleton": skeleton, "create_physics_asset": False, "import_animations": False,
                          "import_materials": False, "import_textures": False, "normal_import_method": "import"})
            created_suited = created_suited or name == "SK_FoA_Body_Suited"
        call("object_set_property", path=DEST + "/SK_FoA_Body_Suited", properties={
            "PostProcessAnimBlueprint": props["PostProcessAnimBlueprint"]})
        print("Imported suit geometry; preserving suited-body calibration before save")
    finally:
        hc.release(OWNER, lease)
        Path("P:/FoA/Saved/CharacterShots/suit_import.json").write_text(json.dumps(log, indent=2))
    if created_suited:
        # Hayba cannot construct instanced DNAAssetUserData yet; use the existing bounded structural helper.
        env = dict(os.environ, FOA_AGENT=OWNER, HAYBA_AGENT_ID=OWNER,
                   FOA_AREAS=DEST + "/SK_FoA_Body_Suited")
        subprocess.run([sys.executable, "P:/FoA/Tools/Unreal/ue_remote.py",
                        "P:/FoA/Tools/Unreal/player/preserve_suited_metadata.py"], env=env, check=True)
    call("asset_save", asset_paths=[DEST + "/SK_FoA_Suit", DEST + "/SK_FoA_Body_Suited"])
    print("Suit import complete with original skeleton/corrective AnimBP and original suited-body physics/DNA")


if __name__ == "__main__":
    main()
