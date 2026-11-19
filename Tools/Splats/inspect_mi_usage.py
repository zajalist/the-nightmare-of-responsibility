"""Read-only: every VFX material instance's base-property overrides (UE 5.8 keeps MI usage flags there too), the
masters' matching values, and who references M_SplatMesh.
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/inspect_mi_usage.py   -> Saved/PPShots/mi_usage.txt"""
import unreal

FIELDS = ("override_usage_flags", "usage_flags", "override_blend_mode", "blend_mode", "override_shading_model", "shading_model",
          "override_two_sided", "two_sided", "override_opacity_mask_clip_value", "opacity_mask_clip_value",
          "override_dithered_lod_transition", "dithered_lod_transition", "override_cast_dynamic_shadow_as_masked",
          "cast_dynamic_shadow_as_masked", "override_is_thin_surface", "is_thin_surface")
MASTER = ("blend_mode", "shading_model", "two_sided", "opacity_mask_clip_value", "dithered_lod_transition",
          "cast_dynamic_shadow_as_masked", "is_thin_surface", "automatically_set_usage_in_editor")


def probe(obj, names):
    vals = []
    for name in names:
        try:  # these UPROPERTYs are not BlueprintVisible, so some names may not resolve: probe each
            vals.append("%s=%s" % (name, obj.get_editor_property(name)))
        except Exception:
            vals.append("%s=?" % name)
    return " ".join(vals)


def run():
    out = []
    for path in ("/Game/FoA/VFX/Splats/M_SplatMesh", "/Game/FoA/VFX/Sand/M_SandSpill", "/Game/FoA/VFX/Sand/M_SandFall"):
        out.append("MASTER %s %s" % (path, probe(unreal.load_asset(path), MASTER)))
        out.append("REFS %s %s" % (path, unreal.EditorAssetLibrary.find_package_referencers_for_asset(path, False)))
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for ad in reg.get_assets_by_path("/Game/FoA/VFX", True):
        if str(ad.asset_class_path.asset_name) != "MaterialInstanceConstant":
            continue
        mi = ad.get_asset()
        parent = mi.get_editor_property("parent")
        out.append("%s parent=%s %s" % (ad.package_name, parent.get_name() if parent else None,
                                        probe(mi.get_editor_property("base_property_overrides"), FIELDS)))
    open(unreal.Paths.project_saved_dir() + "PPShots/mi_usage.txt", "w").write(chr(10).join(out))


run()
