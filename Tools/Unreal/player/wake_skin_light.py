"""World's wake-film white-skin fix (main approved, 2026-11-10; proven by world in PIE: masked character luma 0.56 -> 0.45 in
the push-in, the arm 0.60-0.63 -> 0.39-0.43 in the hit). Applied to anim's assets:
- BP_FoAPlayer: every mesh component that received lighting channel 2 (the sand-only channel: SandRim_Light, 1.2 lux,
  hit him in every shot) now receives channel 0 only.
- LS_WakeUp spawnable lights: L6_SandRim and L6_Dial on channel 2 only (the sand and the dial keep them: world put the
  clock parts on channels 0+2); L6_HitKey 0.07 -> 0.025 cd; L5_MoonBack 2.5 -> 1.2 cd; L5_DoorRim 5.0 -> 3.0 cd.
Compile BP_FoAPlayer through Hayba afterwards.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/wake_skin_light.py FOA_AREAS=Characters,Cinematics"""
import unreal

MESHES = ('Body', 'Face', 'Hair', 'StartOutfit', 'Shirt', 'Trousers', 'Socks', 'Tie', 'Suit', 'Eyebrows', 'BootsWornMesh')
LIGHTS = {'L6_SandRim': ('ch2', None), 'L6_Dial': ('ch2', None), 'L6_HitKey': (None, 0.025), 'L5_MoonBack': (None, 1.2),
          'L5_DoorRim': (None, 3.0)}


def channels(c0, c2):
    lc = unreal.LightingChannels()
    lc.set_editor_property('channel0', c0)
    lc.set_editor_property('channel1', False)
    lc.set_editor_property('channel2', c2)
    return lc


report = []
bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
seen = set()
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = lib.get_data(h)
    name = str(lib.get_variable_name(d))
    if name in MESHES and name not in seen:
        c = lib.get_object_for_blueprint(d, bp)
        before = c.get_editor_property('lighting_channels')
        c.set_editor_property('lighting_channels', channels(True, False))
        seen.add(name)
        report.append((name, 'ch2 was', before.get_editor_property('channel2')))
assert seen == set(MESHES), ('missing components', set(MESHES) - seen)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
done = set()
for b in seq.get_bindings():
    n = str(b.get_display_name())
    if n not in LIGHTS:
        continue
    tpl = b.get_object_template()
    lc = unreal.find_object(None, tpl.get_path_name() + '.LightComponent0') if tpl else None  # templates list no components
    for prop in ('point_light_component', 'spot_light_component', 'rect_light_component'):
        if lc is None and tpl:
            try:
                lc = tpl.get_editor_property(prop)
            except Exception:  # noqa: BLE001
                pass
    assert lc, ('no light component on', n)
    ch, cd = LIGHTS[n]
    if ch == 'ch2':
        lc.set_editor_property('lighting_channels', channels(False, True))
    if cd is not None:
        before = lc.get_editor_property('intensity')
        lc.set_editor_property('intensity', cd)
        report.append((n, 'cd', before, '->', cd))
    else:
        report.append((n, 'channel 2 only'))
    done.add(n)
assert done == set(LIGHTS), ('missing lights', set(LIGHTS) - done)
assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
print('WAKE_SKIN_LIGHT', report)
