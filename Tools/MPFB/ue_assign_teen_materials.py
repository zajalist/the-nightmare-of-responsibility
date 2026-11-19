"""Assign owned morph-capable skin and masked card materials without changing slot order.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/MPFB/ue_assign_teen_materials.py
The cloth lane assigns garment materials under Teen/Cloth/."""
import unreal

HEAD = "/Game/FoA/Characters/Teen/Mesh/SK_Teen_Head"
BY_SLOT = {"short01": "/Game/FoA/Characters/Teen/Hair/MI_Teen_Hair_Short01",
           "eyebrow001": "/Game/FoA/Characters/Teen/Hair/MI_Teen_Brows",
           "high-poly": "/Game/FoA/Characters/Teen/Hair/MI_Teen_Eyes"}  # masked: the cornea layer cuts away
BY_SLOT.update({'Skin':'/Game/FoA/Characters/Teen/Materials/MI_Teen_Skin',
                'tongue01':'/Game/FoA/Characters/Teen/Materials/MI_Teen_Tongue',
                'mindfront_eyelashes_02':'/Game/FoA/Characters/Teen/Materials/MI_Teen_Lashes'})

mesh = unreal.load_asset(HEAD)
mats = list(mesh.materials)
done = []
for m in mats:
    slot = str(m.material_slot_name)
    for key, mi in BY_SLOT.items():
        if key in slot:
            material = unreal.load_asset(mi)
            assert material, mi
            m.material_interface = material
            done.append((slot, mi))
mesh.set_editor_property("materials", mats)
unreal.EditorAssetLibrary.save_asset(HEAD, only_if_is_dirty=False)
print("TEEN_MATS", done, [str(m.material_slot_name) for m in mesh.materials])
body=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
slots=list(body.materials)
skin=unreal.load_asset('/Game/FoA/Characters/Teen/Materials/MI_Teen_Skin')
assert skin
for slot in slots:
    slot.material_interface=skin
body.set_editor_property('materials',slots)
unreal.EditorAssetLibrary.save_loaded_asset(body,only_if_is_dirty=False)
for asset in unreal.EditorAssetLibrary.list_assets('/Game/FoA/Characters/Teen/Materials',recursive=True,include_folder=False):
    unreal.EditorAssetLibrary.save_asset(asset,only_if_is_dirty=True)
print('TEEN_BODY_PHYSICS',body.physics_asset.get_path_name() if body.physics_asset else None)
