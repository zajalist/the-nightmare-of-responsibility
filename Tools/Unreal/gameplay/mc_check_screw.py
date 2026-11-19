"""mech_core: is the imported screwdriver mesh real (vertices, bounds)? Read-only."""
import unreal

m = unreal.load_asset("/Game/FoA/Props/screwdriver/screwdriver_1k/StaticMeshes/screwdriver_1k")
print("mesh", m, "lods", m.get_num_lods() if m else None, "verts", m.get_num_vertices(0) if m else None,
      "bounds", m.get_bounds().box_extent if m else None, "nanite", m.get_editor_property("nanite_settings").enabled if m else None)
