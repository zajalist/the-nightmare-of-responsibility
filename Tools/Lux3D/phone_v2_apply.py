"""Smartphone v2 (Lux3D task 5395323) into the game, replacing SM_Phone in place. Phases (FOA_PHONE=...):
  import   (FOA_AREAS=/Game/FoA/Props/Phone)  P:/FoA-Assets/lux3d/smartphone_v2/SM_Phone.glb (phone_v2_prep.py +
           phone_screen_slot.py) -> /Game/FoA/Props/Phone/V2; textures capped at 1K; Nanite off; slots set to the existing
           MI_Phone_Body / MI_Phone_Screen; sockets Palm_L, Thumb_Rest, Screen. Writes nothing outside Props/Phone/V2.
  swap     (FOA_EXCLUSIVE=1, PIE window)  consolidate the V2 mesh into SM_Phone's references (BP_Phone), rename it to
           /Game/FoA/Props/Phone/SM_Phone, point MI_Phone_Body at the V2 textures and rename those to T_Phone_*.
Frame (unchanged from the old SM_Phone, so BP_Phone / nightstand / intro transforms hold): pivot at the centre,
+X up the screen, -Z out of the glass (screen normal), -Y to the screen's right as seen from the front; 14.7 x 7.1 x 0.98 cm."""
import os

import unreal

EAL = unreal.EditorAssetLibrary

def refs(path):
    """Package referencers from the asset registry (EAL.find_package_referencers_for_asset can come back empty)."""
    return [str(r) for r in (unreal.AssetRegistryHelpers.get_asset_registry().get_referencers(
        str(path).split('.')[0], unreal.AssetRegistryDependencyOptions()) or [])]

MEL = unreal.MaterialEditingLibrary
SRC = 'P:/FoA-Assets/lux3d/smartphone_v2/SM_Phone.glb'
V2 = '/Game/FoA/Props/Phone/V2'
OLD = '/Game/FoA/Props/Phone/SM_Phone'
BODY_MI, SCREEN_MI = '/Game/FoA/Props/Phone/Materials/MI_Phone_Body', '/Game/FoA/Props/Phone/Materials/MI_Phone_Screen'
GLASS_Z = -0.49    # cm: the glass face; the screen quad sits 0.02 cm in front of it (-0.51)
BACK_Z = 0.36     # cm: the back plate (the camera bump rises to +0.49 at X 4.0..6.7, Y -2.7..-1.7)
SOCKETS = {        # name: (location cm, rotation (pitch, yaw, roll)); X axis of each socket documented in the docstring
    'Screen': ((0.0, 0.0, GLASS_Z - 0.02), (-90.0, 0.0, 0.0)),        # X out of the glass (-Z), Z up the screen (+X)
    'Thumb_Rest': ((-2.6, -1.4, GLASS_Z - 0.02), (-90.0, 0.0, 0.0)),  # lower right of centre, seen from the front
    'Palm_L': ((-1.5, 0.0, BACK_Z), (-90.0, 0.0, 0.0)),              # back centre, lower half (anim: all three sockets X out of the screen face, Z to the top)
}


def v2_assets():
    out = {}
    for p in EAL.list_assets(V2, recursive=True, include_folder=False):
        out.setdefault(EAL.load_asset(p).get_class().get_name(), []).append(p.split('.')[0])
    return out


def do_import():
    if not EAL.list_assets(V2, recursive=True):
        t = unreal.AssetImportTask()
        for k, v in (('filename', SRC), ('destination_path', V2), ('automated', True), ('replace_existing', True), ('save', False)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    A = v2_assets()
    print('imported', {k: [x.rsplit('/', 1)[1] for x in v] for k, v in A.items()})
    sm = EAL.load_asset(A['StaticMesh'][0])
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    ns = smes.get_nanite_settings(sm)
    ns.set_editor_property('enabled', False)
    smes.set_nanite_settings(sm, ns, True)
    for p in A.get('Texture2D', []):
        tex = EAL.load_asset(p)
        tex.set_editor_property('max_texture_size', 1024)
        EAL.save_asset(p, only_if_is_dirty=False)
    mats = []   # array elements are copies in Python: rebuild the list. Body first, Screen second; old slot names and MIs
    for i, m in enumerate(sm.get_editor_property('static_materials')):
        is_screen = 'screen' in str(m.get_editor_property('material_slot_name')).lower()
        m.set_editor_property('material_interface', unreal.load_asset(SCREEN_MI if is_screen else BODY_MI))
        m.set_editor_property('material_slot_name', 'MI_Phone_Screen' if is_screen else 'MI_Phone_Body')
        mats.append(m)
    sm.set_editor_property('static_materials', mats)
    for name, (loc, (p, y, r)) in SOCKETS.items():
        s = sm.find_socket(name)
        if not s:
            s = unreal.StaticMeshSocket(sm)
            s.set_editor_property('socket_name', name)
            sm.add_socket(s)
        s.set_editor_property('relative_location', unreal.Vector(*loc))
        s.set_editor_property('relative_rotation', unreal.Rotator(roll=r, pitch=p, yaw=y))
    EAL.save_asset(A['StaticMesh'][0], only_if_is_dirty=False)
    b = sm.get_bounding_box()
    print('V2 mesh', A['StaticMesh'][0], 'box cm', [round(v, 2) for v in (b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z)],
          'tris', sm.get_num_triangles(0), 'slots', [str(m.get_editor_property('material_slot_name')) for m in sm.get_editor_property('static_materials')],
          'sockets', [n for n in SOCKETS if sm.find_socket(n)])


def swap():
    """Run 1 of 3 (EXCLUSIVE): MI_Phone_Body onto the V2 textures (taken from the V2 Interchange MI), then consolidate."""
    A = v2_assets()
    v2mi = EAL.load_asset([p for p in A['MaterialInstanceConstant'] if 'Screen' not in p][0])
    body = EAL.load_asset(BODY_MI)
    for prm in ('BaseColorTexture', 'MetallicRoughnessTexture'):
        MEL.set_material_instance_texture_parameter_value(body, prm, MEL.get_material_instance_texture_parameter_value(v2mi, prm))
    EAL.save_asset(BODY_MI, only_if_is_dirty=False)
    print('consolidate', EAL.consolidate_assets(EAL.load_asset(A['StaticMesh'][0]), [EAL.load_asset(OLD)]))
    print('BP_Phone refs now', refs(A['StaticMesh'][0]))


def rename():
    """Run 2 of 3: the V2 mesh to SM_Phone's path, the V2 textures to T_Phone_BaseColor_V2 / T_Phone_MR_V2."""
    A = v2_assets()
    body = EAL.load_asset(BODY_MI)
    names = {'BaseColorTexture': 'T_Phone_BaseColor_V2', 'MetallicRoughnessTexture': 'T_Phone_MR_V2'}
    for prm, name in names.items():
        t = MEL.get_material_instance_texture_parameter_value(body, prm)
        print('rename', t.get_path_name(), EAL.rename_asset(t.get_path_name().split('.')[0], '/Game/FoA/Props/Phone/Textures/' + name))
    print('rename mesh', EAL.rename_asset(A['StaticMesh'][0], OLD))


def orphans():
    """Run 3 of 3, read-only: what is left unreferenced (old T_Phone_*, the V2 Interchange MIs) for the delete run."""
    for p in ['/Game/FoA/Props/Phone/Textures/T_Phone_BaseColor', '/Game/FoA/Props/Phone/Textures/T_Phone_ORM'] +              [x for x in v2_assets().get('MaterialInstanceConstant', [])]:
        print('ORPHAN' if not refs(p) else 'USED', p)


def cleanup_delete():
    """EXCLUSIVE run A: delete the redirector left at SM_Phone's path and the orphans (old T_Phone_*, the V2 MIs),
    each only after a live referencer check."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    if [str(a.asset_class_path.asset_name) for a in reg.get_assets_by_package_name(OLD)] == ['ObjectRedirector'] and             not refs(OLD):
        print('delete redirector', OLD, EAL.delete_asset(OLD))
    for p in ['/Game/FoA/Props/Phone/Textures/T_Phone_BaseColor', '/Game/FoA/Props/Phone/Textures/T_Phone_ORM'] +              [x for x in v2_assets().get('MaterialInstanceConstant', [])]:
        if EAL.does_asset_exist(p) and not refs(p):
            print('delete orphan', p, EAL.delete_asset(p))


def cleanup_rename():
    """EXCLUSIVE run B: the V2 mesh to SM_Phone's path and the V2 textures to the canonical T_Phone_* names."""
    A = v2_assets()
    print('rename mesh', EAL.rename_asset(A['StaticMesh'][0], OLD))
    for a, b in (('T_Phone_BaseColor_V2', 'T_Phone_BaseColor'), ('T_Phone_MR_V2', 'T_Phone_MR')):
        src = '/Game/FoA/Props/Phone/Textures/' + a
        if EAL.does_asset_exist(src):
            print('rename', a, EAL.rename_asset(src, '/Game/FoA/Props/Phone/Textures/' + b))


def cleanup_fixup():
    """EXCLUSIVE run C: point every referencer past the redirectors the renames left, then drop them."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reds = []
    for root in ('/Game/FoA/Props/Phone',):
        for p in EAL.list_assets(root, recursive=True, include_folder=False):
            pk = p.split('.')[0]
            if [str(a.asset_class_path.asset_name) for a in reg.get_assets_by_package_name(pk)] == ['ObjectRedirector']:
                reds.append(unreal.load_asset(pk))
    if reds:
        unreal.AssetToolsHelpers.get_asset_tools().fixup_referencers(reds)
    print('fixed redirectors', len(reds), 'mesh refs', refs(OLD))


{'import': do_import, 'swap': swap, 'rename': rename, 'orphans': orphans, 'cleanup_delete': cleanup_delete,
 'cleanup_rename': cleanup_rename, 'cleanup_fixup': cleanup_fixup}[os.environ.get('FOA_PHONE', 'import')]()
