"""Read-only: each protagonist groom's LOD list (geometry type, screen size, visible) and its cards/meshes counts.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/groom_lods.py FOA_AREAS=/Game/FoA/Characters/Player"""
import unreal

G = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Grooms/"
L = []
for name in ("Hair_S_Messy", "Eyebrows_M_Thick"):
    g = unreal.load_asset(G + name)
    for gi, grp in enumerate(g.get_editor_property("hair_groups_lod")):
        for li, lod in enumerate(grp.get_editor_property("lods")):
            L.append(f"{name} group{gi} lod{li} {lod.get_editor_property('geometry_type')} "
                     f"screen={lod.get_editor_property('screen_size'):.3f} visible={lod.get_editor_property('visible')}")
    for prop in ("hair_groups_cards", "hair_groups_meshes", "lod_mode", "auto_lod_bias"):
        try:
            v = g.get_editor_property(prop)
            L.append(f"{name} {prop}: {len(v) if hasattr(v, '__len__') else v}")
        except Exception as e:
            L.append(f"{name} {prop} ? {str(e)[:120]}")
with open("P:/FoA/Saved/AnimShots/groom_lods.txt", "w") as f:
    f.write("\n".join(L) + "\n")
print(len(L), "lines")
