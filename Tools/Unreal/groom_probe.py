"""Read-only: hair-strand CVars and the protagonist grooms' LOD setup (strands vs cards per LOD, screen sizes).

  FOA_AREAS=/Game/FoA/Characters/Protagonist python Tools/Unreal/ue_remote.py Tools/Unreal/groom_probe.py
"""
import unreal

for cv in ("r.HairStrands.Enable", "r.HairStrands.Strands", "r.HairStrands.Cards", "r.HairStrands.Meshes",
           "r.HairStrands.Binding", "r.HairStrands.Simulation", "r.HairStrands.LODMode", "r.HairStrands.ForceLOD",
           "r.HairStrands.Visibility.MSAA.SamplePerPixel", "r.HairStrands.DeepShadow.Resolution"):
    try:
        print("GROOM_CVAR", cv, unreal.SystemLibrary.get_console_variable_float_value(cv))
    except Exception as e:
        print("GROOM_CVAR", cv, "<", e, ">")
G = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Grooms/"
for name in ("Hair_S_Messy", "Eyebrows_M_Thick"):
    g = unreal.load_asset(G + name)
    if g is None:
        print("GROOM_ASSET missing", name)
        continue
    for prop in ("hair_groups_lod", "hair_groups_cards", "hair_groups_meshes", "lod_mode", "auto_lod_bias",
                 "enable_global_interpolation", "hair_interpolation_type"):
        try:
            v = g.get_editor_property(prop)
            if isinstance(v, unreal.Array) or isinstance(v, list):
                out = []
                for it in v:
                    try:
                        lods = it.get_editor_property("lods")
                        out.append([(str(l.get_editor_property("geometry_type")), round(l.get_editor_property("screen_size"), 3))
                                    for l in lods])
                    except Exception:
                        out.append(str(it)[:200])
                print("GROOM_ASSET", name, prop, out)
            else:
                print("GROOM_ASSET", name, prop, v)
        except Exception as e:
            print("GROOM_ASSET", name, prop, "<", str(e)[:120], ">")
