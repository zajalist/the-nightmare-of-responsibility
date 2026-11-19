"""Native Hayba only: validate the saved teen assets, then swap Face and existing grooms without touching graphs."""
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc

P = "/Game/FoA/Characters/Player/BP_FoAPlayer"
ROOT = "/Game/FoA/Characters/Protagonist/Teen/Built_N"
OWNER = "codex-character-teen"
DATA = json.loads(Path("P:/FoA/Saved/CharacterShots/teen_runtime_assets.json").read_text())
TRACE = []
TOKEN = None


def call(name, **params):
    response = hc.call(name, params, owner=OWNER, lease=TOKEN)
    TRACE.append({"name": name, "params": params, "response": response})
    assert response.get("ok"), response
    result = response.get("data", {})
    assert result.get("ok", True), result
    if name == "asset_save":
        assert not result.get("failed"), result
    return result


def prop(path, names):
    return call("object_get_property", path=path, names=names)["properties"]


def reference(value):
    if value in (None, "None", ""):
        return None
    match = re.search(r"'([^']+)'", value)
    return match.group(1) if match else value


def template(name):
    return P + ".BP_FoAPlayer_C:" + name + "_GEN_VARIABLE"


def main():
    global TOKEN
    assert not call("editor_get_state")["pie_running"], "Exit PIE before swapping a face"
    TOKEN = hc.lease_acquire(OWNER, ["asset:" + P, "asset:" + ROOT], ttl_s=120, wait_s=20)
    before = {}
    try:
        if "--prepare" in sys.argv:
            head_path = ROOT + "/MHC_Face_N_Head"
            source = prop("/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/SKM_MHC_Protagonist_FaceMesh",
                          ["Skeleton", "PostProcessAnimBlueprint"])
            call("object_set_property", path=head_path,
                 properties={key: reference(value) for key, value in source.items()})
            assert prop(head_path, list(source)) == source
            call("asset_save", asset_paths=[head_path])
            print("PASS new head uses project face skeleton and RigLogic postprocess")
            return
        # Read the shipped bindings directly; preview bindings need the same source surface for RBF transfer.
        for name, folder, original in (("Hair", "Hair", "Hair_S_SideSweptFringe_Binding"),
                                        ("Eyebrows", "Eyebrows", "Eyebrows_M_Natural_Binding")):
            source = prop("/MetaHumanCharacter/Optional/Grooms/Bindings/" + folder + "/" + original,
                          ["SourceSkeletalMesh"])
            binding = DATA["grooms"][name]["binding"]
            call("object_set_property", path=binding, properties={"SourceSkeletalMesh": reference(source["SourceSkeletalMesh"])})
            call("asset_save", asset_paths=[binding])
            actual = prop(binding, ["Groom", "TargetSkeletalMesh", "SourceSkeletalMesh"])
            assert reference(actual["TargetSkeletalMesh"]) == DATA["head"]
            assert reference(actual["Groom"]) == DATA["grooms"][name]["groom"]
            assert reference(actual["SourceSkeletalMesh"]) == reference(source["SourceSkeletalMesh"])

        dependencies = {}
        for file in Path("P:/FoA/Content/FoA/Characters/Protagonist/Teen/Built_N").rglob("*.uasset"):
            package = "/Game/" + file.relative_to("P:/FoA/Content").with_suffix("").as_posix()
            deps = call("asset_get_dependencies", path=package)["dependencies"]
            assert not any("/Transient" in item for item in deps), (package, deps)
            dependencies[package] = deps
        head = prop(DATA["head"], ["Skeleton", "PostProcessAnimBlueprint", "AssetUserData"])
        original = prop("/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/SKM_MHC_Protagonist_FaceMesh",
                        ["Skeleton", "PostProcessAnimBlueprint"])
        assert head["Skeleton"] == original["Skeleton"] and head["PostProcessAnimBlueprint"] == original["PostProcessAnimBlueprint"]
        assert "DNAAssetUserData" in head["AssetUserData"]
        dna = prop(DATA["head"] + ":DNAAssetUserData_0", ["DNAAsset"])
        assert reference(dna["DNAAsset"]) == ROOT + "/DNA/MHC_Face_N_Head.MHC_Face_N_Head", "Export facial rig DNA before swapping"
        body_before = prop(template("Body"), ["SkeletalMeshAsset", "AnimClass"])
        before["Face"] = prop(template("Face"), ["SkeletalMeshAsset"])
        for name in DATA["grooms"]:
            before[name] = prop(template(name), ["GroomAsset", "BindingAsset", "OverrideMaterials"])
        call("object_set_property", path=template("Face"), properties={"SkeletalMeshAsset": DATA["head"]})
        for name, data in DATA["grooms"].items():
            call("object_set_property", path=template(name), properties={"GroomAsset": data["groom"],
                 "BindingAsset": data["binding"], "OverrideMaterials": data["materials"]})
        compiled = call("blueprint_compile", path=P)
        assert compiled.get("error_count", 0) == 0 and compiled.get("warning_count", 0) == 0, compiled
        assert prop(template("Body"), ["SkeletalMeshAsset", "AnimClass"]) == body_before
        assert reference(prop(template("Face"), ["SkeletalMeshAsset"])["SkeletalMeshAsset"]) == DATA["head"]
        for name in DATA["grooms"]:
            groom = prop(template(name), ["bRenderCustomDepth", "CustomDepthStencilValue", "BindingAsset"])
            assert str(groom["bRenderCustomDepth"]).lower() == "false" and int(groom["CustomDepthStencilValue"]) == 0, groom
        call("asset_save", asset_paths=[P])
        Path("P:/FoA/Saved/CharacterShots/teen_native_audit.json").write_text(json.dumps(
            {"passed": True, "head": head, "body_preserved": body_before, "packages": dependencies, "compile": compiled}, indent=2))
        print("PASS native teen Face/groom swap; original Body/ABP/Skeleton retained; no transient package dependencies")
    except Exception:
        for name, values in before.items():
            values = {key: re.findall(r"'([^']+)'", value) if key == "OverrideMaterials" else reference(value)
                      for key, value in values.items()}
            call("object_set_property", path=template(name), properties=values)
        if before:
            call("blueprint_compile", path=P)
            call("asset_save", asset_paths=[P])
        raise
    finally:
        Path("P:/FoA/Saved/CharacterShots/teen_native_trace.json").write_text(json.dumps(TRACE, indent=2))
        hc.release(OWNER, TOKEN)


if __name__ == "__main__":
    main()
