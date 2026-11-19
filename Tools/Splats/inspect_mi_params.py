"""Read-only: the parameter overrides of every splat and sand material instance.
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/inspect_mi_params.py   -> Saved/PPShots/mi_params.txt"""
import unreal


def run():
    out = []
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for root in ("/Game/FoA/VFX/Splats/Instances", "/Game/FoA/VFX/Sand"):
        for ad in reg.get_assets_by_path(root, False):
            if str(ad.asset_class_path.asset_name) != "MaterialInstanceConstant":
                continue
            mi = ad.get_asset()
            s = ["%s=%.4g" % (p.parameter_info.name, p.parameter_value) for p in mi.get_editor_property("scalar_parameter_values")]
            v = ["%s=(%.4g,%.4g,%.4g,%.4g)" % (p.parameter_info.name, p.parameter_value.r, p.parameter_value.g,
                                               p.parameter_value.b, p.parameter_value.a) for p in mi.get_editor_property("vector_parameter_values")]
            out.append("%s | %s | %s" % (ad.asset_name, " ".join(s), " ".join(v)))
    open(unreal.Paths.project_saved_dir() + "PPShots/mi_params.txt", "w").write(chr(10).join(out))


run()
