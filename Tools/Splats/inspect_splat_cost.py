"""Read-only: the splat meshes' Nanite flag and triangle count, and M_SplatMesh's usage flags and shader stats.
  $env:FOA_AREAS='VFX'; python Tools/Unreal/ue_remote.py Tools/Splats/inspect_splat_cost.py"""
import unreal

OUT = []
print = lambda *a: OUT.append(" ".join(str(x) for x in a))  # ue_remote truncates long output

MEL = unreal.MaterialEditingLibrary
USAGE = ("used_with_nanite", "used_with_skeletal_mesh", "used_with_mesh_deformer", "used_with_editor_compositing",
         "used_with_particle_sprites", "used_with_beam_trails", "used_with_mesh_particles", "used_with_niagara_sprites",
         "used_with_niagara_ribbons", "used_with_niagara_mesh_particles", "used_with_geometry_cache", "used_with_static_lighting",
         "used_with_morph_targets", "used_with_spline_meshes", "used_with_instanced_static_meshes",
         "used_with_geometry_collections", "used_with_clothing", "used_with_water", "used_with_hair_strands",
         "used_with_lidar_point_cloud", "used_with_virtual_heightfield_mesh", "used_with_voxels", "used_with_curves")  # Material.h, UE 5.8


def run():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for root in ("/Game/FoA/VFX/Splats", "/Game/FoA/VFX/Sand"):
        for ad in reg.get_assets_by_path(root, True):
            if str(ad.asset_class_path.asset_name) != "StaticMesh":
                continue
            sm = ad.get_asset()
            ns = sm.get_editor_property("nanite_settings")
            mats = [str(m.get_editor_property("material_interface").get_path_name()).rsplit(".", 1)[-1]
                    if m.get_editor_property("material_interface") else None for m in sm.get_editor_property("static_materials")]
            print("MESH", ad.package_name, "nanite=", ns.get_editor_property("enabled"),
                  "tris=", sm.get_num_triangles(0), "mats=", mats)
    for path in ("/Game/FoA/VFX/Splats/M_SplatMesh", "/Game/FoA/VFX/Sand/M_SandSpill", "/Game/FoA/VFX/Sand/M_SandFall"):
        m = unreal.load_asset(path)
        on = [u for u in USAGE if m.get_editor_property(u)]  # names checked against UE 5.8 UMaterial
        print("MAT", path, "usage_on=", on, "blend=", m.get_editor_property("blend_mode"),
              "shading=", m.get_editor_property("shading_model"))
        st = MEL.get_statistics(m)
        print("STATS", path, st)
        print("SWITCHES", MEL.get_static_switch_parameter_names(m))
        print("SCALARS", MEL.get_scalar_parameter_names(m))
        print("VECTORS", MEL.get_vector_parameter_names(m))
        print("EXPR_COUNT", MEL.get_num_material_expressions(m))
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if sm and "/VFX/" in sm.get_path_name():
                mats = [mi.get_name() if mi else None for mi in c.get_materials()]
                print("ACTOR", a.get_actor_label(), type(c).__name__, sm.get_name(), mats)


run()
open(unreal.Paths.project_saved_dir() + "PPShots/splat_cost.txt", "w").write(chr(10).join(OUT))
