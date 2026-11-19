"""Read-only: what lights and materials does his first-person arm get? Lights on BP_FoAPlayer (class defaults) and
the materials the Body/Face/garment components actually render (override or mesh slot).
  python Tools/Unreal/integration/run_read.py Tools/Unreal/face/probe_fp_arm.py   -> Saved/FaceShots/probe_fp_arm.json"""
import json

import unreal


def run():
    bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    out = {'lights': {}, 'materials': {}}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object_for_blueprint(lib.get_data(h), bp)
        name = str(lib.get_variable_name(lib.get_data(h)))
        if isinstance(o, unreal.LightComponent):
            row = {'class': o.get_class().get_name(), 'intensity': o.get_editor_property('intensity'),
                   'visible': o.get_editor_property('visible'), 'cast_shadows': o.get_editor_property('cast_shadows'),
                   'units': str(o.get_editor_property('intensity_units')) if hasattr(o, 'intensity_units') else None,
                   'channels': str(o.get_editor_property('lighting_channels'))}
            for k in ('attenuation_radius', 'source_radius', 'indirect_lighting_intensity', 'specular_scale'):
                try:
                    row[k] = o.get_editor_property(k)
                except Exception:
                    pass
            out['lights'][name] = row
        if isinstance(o, unreal.SkeletalMeshComponent) and name in ('Body', 'Face', 'StartOutfit', 'Shirt'):
            mesh = o.get_editor_property('skeletal_mesh_asset')
            ov = [m.get_path_name() if m else None for m in o.get_editor_property('override_materials')]
            slots = [m.get_editor_property('material_interface').get_path_name() if m.get_editor_property('material_interface') else None
                     for m in mesh.get_editor_property('materials')] if mesh else []
            out['materials'][name] = {'override': ov, 'slots': slots,
                                      'channels': str(o.get_editor_property('lighting_channels'))}
    with open('P:/FoA/Saved/FaceShots/probe_fp_arm.json', 'w') as f:
        json.dump(out, f, indent=1, default=str)
    print('wrote probe_fp_arm.json', list(out['lights']))


run()
