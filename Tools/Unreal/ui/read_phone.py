"""Read-only: what the diegetic phone (step 5) has to fit. SM_Phone's bounds, sockets and material slots; placed actors
using SM_Phone or BP_Phone; BP_Phone's component templates; the Nightstand. Run via ue_remote.py
(FOA_AREAS=/Game/FoA/UI/Game/BP_Phone)."""
import unreal


def main():
    sm = unreal.load_asset('/Game/FoA/Props/Phone/SM_Phone')
    b = sm.get_bounding_box()
    print('SM_Phone box', [round(v, 2) for v in (b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z)])
    print('slots', [(str(m.get_editor_property('material_slot_name')),
                     m.get_editor_property('material_interface').get_name() if m.get_editor_property('material_interface') else None)
                    for m in sm.get_editor_property('static_materials')])
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        c = a.get_class().get_name()
        lab = a.get_actor_label()
        uses = False
        for comp in a.get_components_by_class(unreal.StaticMeshComponent):
            if comp.get_editor_property('static_mesh') == sm:
                uses = True
        if uses or 'Phone' in c or 'Phone' in lab or lab.startswith('Nightstand'):
            p, r = a.get_actor_location(), a.get_actor_rotation()
            o, e = a.get_actor_bounds(False)
            print(f'ACTOR {lab} | {c} | loc {p.x:.1f},{p.y:.1f},{p.z:.1f} | rot {r.pitch:.0f},{r.yaw:.0f},{r.roll:.0f} | top z {o.z + e.z:.1f}')
    bp = unreal.load_asset('/Game/FoA/UI/Game/BP_Phone')
    cdo = unreal.get_default_object(bp.generated_class())
    for comp in cdo.get_components_by_class(unreal.SceneComponent):
        print('CDO comp', comp.get_name(), comp.get_class().get_name(), comp.get_editor_property('relative_location'),
              comp.get_editor_property('relative_rotation'))


main()
