"""Props art pass (world lane): the level actors still wearing M_Greybox children (MI_Trim_Paint, MI_Metal) get real
textured materials. Per-actor slot overrides only; no shared material is edited.
  $env:FOA_ACTORS='<labels>'; $env:FOA_AREAS='/Game/FoA/Props'; python Tools/Unreal/ue_remote.py Tools/Lux3D/fix_greybox_materials.py
- Door_Bedroom (BP_Door, instance override) and DoorFrame_Bedroom: MI_Prop_DoorPaint (scuffed painted wood, the
  baseboard's family with a flat ornament normal: the door's UVs carry no trim profile) and, for the knob, hinges
  and strike, the Lux3D lock plate's aged-brass material.
- Window sills, sashes and muntins (trims-family meshes): MI_Trim_PaintedWood, the same as their casings."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PAINT = unreal.load_asset('/Game/FoA/Props/Door/MI_Prop_DoorPaint')
BRASS = unreal.load_asset('/Game/FoA/Props/DoorLock/MI_DoorLockPlate')
TRIM = unreal.load_asset('/Game/FoA/Materials/MI_Trim_PaintedWood')
GREY = ('MI_Trim_Paint', 'MI_Metal')
by = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}


def swap(comp, slot, mat):
    old = comp.get_material(slot)
    if old and old.get_name() in GREY:
        comp.modify()
        comp.set_material(slot, mat)
        return f'{old.get_name()} -> {mat.get_name()}'
    return f'kept {old.get_name() if old else None}'


# The door is a Blueprint instance: an override edit re-runs its construction script, so set the whole list once
door = by['Door_Bedroom']
mesh = next(c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Mesh')
mesh.modify()
mesh.set_editor_property('override_materials', [PAINT, BRASS])
mesh = next(c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Mesh')
print('Door_Bedroom.Mesh', [m.get_name() if m else None for m in mesh.get_editor_property('override_materials')])
frame = by['DoorFrame_Bedroom'].static_mesh_component
print('DoorFrame_Bedroom', swap(frame, 0, PAINT), swap(frame, 1, BRASS))
n = 0
for label, a in by.items():
    if label.startswith(('Sill_window_', 'Sash_window_', 'Muntin_window_')):
        r = swap(a.static_mesh_component, 0, TRIM)
        n += r.startswith('MI_')
print('window parts repainted', n)
