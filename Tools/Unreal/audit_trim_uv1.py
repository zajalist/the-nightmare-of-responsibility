"""Read-only audit (world lane): every level primitive wearing M_PaintedWoodTrim (any instance) whose static mesh has no
UV1. The trim material samples its carving normal (T_TrimOrnament_N) with UV1; a mesh without UV1 falls back to UV0 and
stamps egg-and-dart / bead columns across flat faces (the bay sill, 2026-11-10).
  python Tools/Unreal/integration/run_read.py Tools/Unreal/audit_trim_uv1.py"""
import unreal

MASTER = '/Game/FoA/Materials/M_PaintedWoodTrim.M_PaintedWoodTrim'


def is_trim(m):
    while m:
        if m.get_path_name() == MASTER:
            return True
        m = m.get_editor_property('parent') if isinstance(m, unreal.MaterialInstance) else None
    return False


bad = []
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property('static_mesh')
        if not sm:
            continue
        uvs = unreal.EditorStaticMeshLibrary.get_num_uv_channels(sm, 0)
        mats = [c.get_material(i) for i in range(c.get_num_materials())]
        if uvs < 2 and any(is_trim(m) for m in mats if m):
            bad.append((a.get_actor_label(), c.get_name(), sm.get_name(), uvs))
print('TRIM_NO_UV1 count', len(bad))  # first: the remote log truncates long output
print('TRIM_NO_UV1', ' '.join(sorted({f'{r[0]}:{r[2]}' for r in bad})))
