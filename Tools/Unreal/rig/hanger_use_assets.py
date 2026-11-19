"""Rig lane, editor Python (short runs): the parts of the hanger-use assets Hayba has no command for.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/rig/hanger_use_assets.py FOA_STEP=override|meshes|defaults
override  AN_FoA_HangerUse gets its Received_Notify override (the graph is a Hayba batch: hanger_use_build.py notify).
meshes    BP_FoAHangerUse's component templates: Hanger = SM_Lux3D_WireHanger, Proxy = SM_Lux3D_ShirtEnemy; no collision,
          no shadows from the proxy's hidden state.
defaults  the children's class defaults from Saved/RigShots/hanger_use/keys.json: KeysA/B/W/P, KeyCount, Dt, Stance,
          SlideTime, ProxyHideAt, Montage, HandInAnchor (grip_bake.json Hanger hand_in_object)."""
import json
import os

import unreal

D = '/Game/FoA/Characters/Player/Hanger'
BP = D + '/BP_FoAHangerUse'
KEYS = json.load(open('P:/FoA/Saved/RigShots/hanger_use/keys.json'))
EAL = unreal.EditorAssetLibrary


def xf(loc, q):
    return unreal.Transform(unreal.Vector(*loc), unreal.Quat(*q).rotator(), unreal.Vector(1, 1, 1))


def step_override():
    bp = unreal.load_asset(D + '/AN_FoA_HangerUse')
    if 'Received_Notify' not in [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)]:
        unreal.BlueprintEditorLibrary.add_function_override(bp, 'Received_Notify')
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
    print('OVERRIDE', [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)])


def step_meshes():
    bp = unreal.load_asset(BP)
    gen = bp.generated_class()
    for comp, mesh in (('Hanger', '/Game/FoA/Lux3D/wire_hanger/SM_Lux3D_WireHanger'),
                       ('Proxy', '/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy')):
        t = unreal.find_object(None, gen.get_path_name() + ':' + comp + '_GEN_VARIABLE')
        assert t, comp
        t.set_editor_property('static_mesh', unreal.load_asset(mesh))
        t.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        t.set_editor_property('can_character_step_up_on', unreal.CanBeCharacterBase.ECB_NO)
        t.set_editor_property('generate_overlap_events', False)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
    print('MESHES set')


def step_defaults():
    hio = json.load(open('P:/FoA/Saved/AnimShots/grip_bake.json'))['Hanger']['hand_in_object']
    for use, montage in (('door', 'AM_FoA_HangerDoor'), ('bed', 'AM_FoA_HangerBed')):
        k = KEYS[use]
        path = f'{D}/BP_FoAHangerUse_{use.capitalize()}'
        bp = unreal.load_asset(path)
        cdo = unreal.get_default_object(bp.generated_class())
        rows = k['rows']
        cdo.set_editor_property('KeysA', [xf(*r['A']) for r in rows])
        cdo.set_editor_property('KeysB', [xf(*r['B']) for r in rows])
        cdo.set_editor_property('KeysW', [float(r['W']) for r in rows])
        cdo.set_editor_property('KeysP', [xf(*r['P']) for r in rows])
        cdo.set_editor_property('KeyCount', len(rows))
        cdo.set_editor_property('Dt', float(KEYS['dt']))
        cdo.set_editor_property('Stance', unreal.Vector(*k['stance']))
        cdo.set_editor_property('SlideTime', float(k['slide']))
        cdo.set_editor_property('ProxyHideAt', float(k['proxy_hide']))
        cdo.set_editor_property('HandInAnchor', xf(hio['loc'], hio['quat']))
        m = unreal.load_asset(f'/Game/FoA/Characters/Player/Montages/{montage}')
        assert m, montage
        cdo.set_editor_property('Montage', m)
        bp.modify()
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        cdo = unreal.get_default_object(bp.generated_class())
        assert len(cdo.get_editor_property('KeysB')) == len(rows), 'defaults lost on compile'
        EAL.save_loaded_asset(bp, False)
        print('DEFAULTS', use, len(rows), 'keys', cdo.get_editor_property('Montage').get_name(), cdo.get_editor_property('Stance'))


assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'PIE running'
{'override': step_override, 'meshes': step_meshes, 'defaults': step_defaults}[os.environ['FOA_STEP']]()
