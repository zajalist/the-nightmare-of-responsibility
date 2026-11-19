"""Jumpscare support assets (idempotent, edit in place):
  - /Game/FoA/Audio/SFX/Horror/SFX_Horror_Stinger_01, SFX_Horror_TensionBed_Loop_01: SC_SFX, the bed loops
  - /Game/FoA/Audio/Mix/SMX_Jumpscare_Hush: SC_Ambience to 30%, 3 s in, 4 s out (pushed for the dread, popped on release)
  - /Game/FoA/Gameplay/Jumpscare/CS_Jumpscare: LegacyCameraShake, 0.55 s hit shake (docs/design/horror/jumpscare.md)
  $env:FOA_AREAS='Gameplay,Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/build_assets.py"""
import unreal

EAL = unreal.EditorAssetLibrary
SFX = '/Game/FoA/Audio/SFX/Horror/'
SMX = '/Game/FoA/Audio/Mix/SMX_Jumpscare_Hush'
CS = '/Game/FoA/Gameplay/Jumpscare/CS_Jumpscare'


def osc(amp, freq):
    o = unreal.FOscillator()
    o.set_editor_property('amplitude', amp)
    o.set_editor_property('frequency', freq)
    o.set_editor_property('initial_offset', unreal.InitialOscillatorOffset.EOO_OFFSET_RANDOM)
    return o


def sounds():
    sc = unreal.load_asset('/Game/FoA/Audio/Mix/SC_SFX')
    for name, loop in (('SFX_Horror_Stinger_01', False), ('SFX_Horror_TensionBed_Loop_01', True)):
        w = unreal.load_asset(SFX + name)
        w.set_editor_property('sound_class_object', sc)
        w.set_editor_property('looping', loop)
        EAL.save_asset(SFX + name, only_if_is_dirty=False)
        print('wave', name, 'loop', loop, round(w.get_editor_property('duration'), 2))


def mix():
    m = unreal.load_asset(SMX)
    if not m:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset('SMX_Jumpscare_Hush', '/Game/FoA/Audio/Mix', unreal.SoundMix, unreal.SoundMixFactory())
    adj = unreal.SoundClassAdjuster()
    adj.set_editor_property('sound_class_object', unreal.load_asset('/Game/FoA/Audio/Mix/SC_Ambience'))
    adj.set_editor_property('volume_adjuster', 0.3)
    adj.set_editor_property('apply_to_children', True)
    m.set_editor_property('sound_class_effects', [adj])
    m.set_editor_property('fade_in_time', 3.0)
    m.set_editor_property('fade_out_time', 4.0)
    m.set_editor_property('duration', -1.0)
    EAL.save_asset(SMX, only_if_is_dirty=False)
    print('mix', SMX)


def shake():
    bp = unreal.load_asset(CS)
    if not bp:
        f = unreal.BlueprintFactory()
        f.set_editor_property('parent_class', unreal.LegacyCameraShake)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('CS_Jumpscare', '/Game/FoA/Gameplay/Jumpscare', unreal.Blueprint, f)
    cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(CS))
    rot = unreal.ROscillator()
    rot.set_editor_property('pitch', osc(2.5, 22.0))
    rot.set_editor_property('yaw', osc(2.0, 17.0))
    rot.set_editor_property('roll', osc(4.0, 9.0))
    loc = unreal.VOscillator()
    loc.set_editor_property('x', osc(4.0, 12.0))
    for k, v in (('oscillation_duration', 0.55), ('oscillation_blend_in_time', 0.0), ('oscillation_blend_out_time', 0.35),
                 ('rot_oscillation', rot), ('loc_oscillation', loc)):
        cdo.set_editor_property(k, v)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_asset(CS, only_if_is_dirty=False)
    print('shake', CS, cdo.get_editor_property('oscillation_duration'))


def main():
    sounds()
    mix()
    shake()


main()
