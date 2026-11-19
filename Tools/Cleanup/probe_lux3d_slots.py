"""READ-ONLY: which texture feeds which parameter on the Lux3D material instances, to name set-B moves correctly.
  python Tools/Unreal/integration/run_read.py Tools/Cleanup/probe_lux3d_slots.py
"""
import unreal


def main():
    out = []
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    for ad in ar.get_assets_by_path("/Game/FoA/Lux3D", recursive=True):
        if str(ad.asset_class_path.asset_name) != "MaterialInstanceConstant":
            continue
        mi = ad.get_asset()
        for v in mi.get_editor_property("texture_parameter_values") or []:
            tex = v.get_editor_property("parameter_value")
            name = v.get_editor_property("parameter_info").get_editor_property("name")
            tail = tex.get_path_name().split(".")[-1] if tex else None
            out.append(f"{str(ad.package_name).split('/')[4]}: {name}={tail}")
    path = unreal.Paths.project_saved_dir() + "Cleanup/lux3d_slots.txt"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("LUX3D", len(out), "bindings ->", path)


main()
