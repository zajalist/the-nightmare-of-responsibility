"""Read-only: print the parent chain and parameters (scalar, vector, texture, static switch) of materials.

  python Tools/Unreal/ue_remote.py Tools/Unreal/mat_params.py FOA_ASSETS=/Game/A/MI_X,/Game/B/M_Y
"""
import os
import unreal


def run():
    mel = unreal.MaterialEditingLibrary
    for path in filter(None, os.environ["FOA_ASSETS"].split(",")):
        m = unreal.load_asset(path)
        if m is None:
            print("MAT_PARAMS missing", path)
            continue
        chain, p = [], m
        while isinstance(p, unreal.MaterialInstance):
            chain.append(p.get_path_name())
            p = p.get_editor_property("parent")
        chain.append(p.get_path_name() if p else None)
        print("MAT_PARAMS", path, "chain", chain)
        for kind, fn in (("scalar", mel.get_scalar_parameter_names), ("vector", mel.get_vector_parameter_names),
                         ("texture", mel.get_texture_parameter_names),
                         ("switch", mel.get_static_switch_parameter_names)):
            try:
                names = [str(n) for n in fn(m)]
            except Exception as e:
                names = [f"<{e}>"]
            if kind == "texture" and isinstance(m, unreal.MaterialInstance):
                names = [f"{n}={(lambda t: t.get_name() if t else None)(mel.get_material_instance_texture_parameter_value(m, n))}"
                         for n in names]
            print("MAT_PARAMS", path, kind, names)


run()
