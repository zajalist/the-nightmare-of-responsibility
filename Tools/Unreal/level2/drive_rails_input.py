"""Editor Python (python_exec_file, Drive lease): dodge keys. D-pad left opens the C.V. while driving, so the
gamepad dodges move to the shoulders; the arrow keys join A and D. Idempotent; saves IMC_L2Drive."""
import unreal

FOLDER = '/Game/FoA/Level2/Drive/Input'
WANT = {'IA_L2Left': ('A', 'Left', 'Gamepad_LeftShoulder'), 'IA_L2Right': ('D', 'Right', 'Gamepad_RightShoulder')}
DROP = ('Gamepad_DPad_Left', 'Gamepad_DPad_Right')


def key(name):
    k = unreal.Key(); k.set_editor_property('key_name', name); return k


imc = unreal.load_asset(FOLDER + '/IMC_L2Drive')
for action_name, keys in WANT.items():
    action = unreal.load_asset(f'{FOLDER}/{action_name}')
    mapped = {str(m.key.get_editor_property('key_name')) for m in
              imc.get_editor_property('default_key_mappings').get_editor_property('mappings') if m.action == action}
    for name in DROP:
        if name in mapped:
            imc.unmap_key(action, key(name))
    for name in keys:
        if name not in mapped:
            imc.map_key(action, key(name))
rows = sorted((str(m.action.get_name()), str(m.key.get_editor_property('key_name')))
              for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings'))
assert not any(k in DROP for a, k in rows if a in WANT), rows
assert unreal.EditorAssetLibrary.save_loaded_asset(imc, False)
print('DRIVE_INPUT', rows)
