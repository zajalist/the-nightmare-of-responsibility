"""SG_FoASettings (SaveGame) + BPFL_FoASettings (function library). Run via ue_remote.py.
Graphics live in the engine's GameUserSettings (saved to GameUserSettings.ini and re-applied by the engine at boot);
everything else (audio, controls, accessibility) lives in the "Settings" save slot and is applied here.
Audio uses the audio lane's /Game/FoA/Audio/Mix/SCM_Settings + SC_Master/SC_SFX/SC_Ambience/SC_UI.
Reduce motion is written to MPC_UI (UI materials) and MPC_Dream (post-process lane) so both honour it."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import unreal

AT = unreal.AssetToolsHelpers.get_asset_tools()
SG = '/Game/FoA/UI/Framework/SG_FoASettings'
LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings'
GS = '/Script/Engine.GameplayStatics'
MIX = '/Game/FoA/Audio/Mix'


def make_bp(path, parent, factory_cls=unreal.BlueprintFactory):
    name = path.rsplit('/', 1)[1]
    bp = unreal.load_asset(f'{path}.{name}')
    if not bp:
        fac = factory_cls()
        if factory_cls is unreal.BlueprintFactory:
            fac.set_editor_property('parent_class', parent)
        bp = AT.create_asset(name, path.rsplit('/', 1)[0], unreal.Blueprint, fac)
    assert bp, path
    return bp


make_bp(SG, unreal.SaveGame)
ensure_vars(SG, [
    ('MasterVolume', ptype('real'), '1.0', 'Audio', True), ('EffectsVolume', ptype('real'), '1.0', 'Audio', True),
    ('AmbienceVolume', ptype('real'), '1.0', 'Audio', True), ('InterfaceVolume', ptype('real'), '1.0', 'Audio', True),
    ('MouseSensitivity', ptype('real'), '1.0', 'Controls', True), ('bInvertY', ptype('bool'), 'false', 'Controls', True),
    ('bSubtitles', ptype('bool'), 'true', 'Accessibility', True), ('SubtitleSize', ptype('int'), '1', 'Accessibility', True),
    ('bReduceMotion', ptype('bool'), 'false', 'Accessibility', True),
    ('bShowPhotoWarning', ptype('bool'), 'true', 'Accessibility', True),
    ('bSeenIntro', ptype('bool'), 'false', 'Progress', False),
    ('IntroVersionSeen', ptype('int'), '0', 'Progress', False),  # old saves get the actual-room intro once
])
compile_save(SG)
SG_C = SG + '.SG_FoASettings_C'
T_SG = ptype(unreal.load_class(None, SG_C))

make_bp(LIB, None, unreal.BlueprintFunctionLibraryFactory)
for f in ('LoadSettings', 'SaveSettings', 'ApplySettings', 'LoadAndApplySettings'):
    drop_function(LIB, f)
Graph.function(LIB, 'LoadSettings', outputs=[('Settings', T_SG)])
Graph.function(LIB, 'SaveSettings', inputs=[('Settings', T_SG)])
Graph.function(LIB, 'ApplySettings', inputs=[('Settings', T_SG)])
Graph.function(LIB, 'LoadAndApplySettings', outputs=[('Settings', T_SG)])


def result(g):
    return g.ed.list_nodes_of_class(unreal.K2Node_FunctionResult)[0]


def cast_to_sg(g, x, y):
    names = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToSG_FoASettings')]
    return g.at(g.ed.create_node_from_name(names[0], V2(x, y), []), x, y)


# LoadSettings: load the slot, or start from defaults on first run
g = Graph(LIB, 'LoadSettings')
e = g.at(entry_node(g), 0, 0)
exists = g.call(f'{GS}:DoesSaveGameExist', 224, 160, SlotName='Settings', UserIndex=0)
br = g.branch(288, 0)
load = g.call(f'{GS}:LoadGameFromSlot', 544, -128, SlotName='Settings', UserIndex=0)
make = g.call(f'{GS}:CreateSaveGameObject', 544, 128, SaveGameClass=SG_C)
c1 = cast_to_sg(g, 896, -128); c2 = cast_to_sg(g, 896, 128)
ret = g.at(result(g), 1248, -128)
ret2 = g.at(g.ed.add_return_node(), 1248, 128)
g.exec_chain(e, exists, br); g.link(exists, 'ReturnValue', br, 'Condition')  # impure: must be on the exec line
g.link(br, 'True', load, 'execute'); g.link(br, 'False', make, 'execute')
g.link(load, 'then', c1, 'execute'); g.link(load, 'ReturnValue', c1, 'Object')
g.link(make, 'then', c2, 'execute'); g.link(make, 'ReturnValue', c2, 'Object')
g.link(c1, 'then', ret, 'execute'); g.link(c1, 'AsSG_FoASettings', ret, 'Settings')
g.link(c2, 'then', ret2, 'execute'); g.link(c2, 'AsSG_FoASettings', ret2, 'Settings')
g.comment('Load settings', 'The "Settings" slot, or fresh defaults on first run', [e, exists, br, load, make, c1, c2, ret, ret2],
          C_DATA)

# SaveSettings
g = Graph(LIB, 'SaveSettings')
e = g.at(entry_node(g), 0, 0)
save = g.call(f'{GS}:SaveGameToSlot', 288, 0, SlotName='Settings', UserIndex=0)
g.exec_chain(e, save); g.link(e, 'Settings', save, 'SaveGameObject')
g.comment('Save settings', 'Writes the "Settings" slot', [e, save], C_DATA)

# ApplySettings: four volume overrides on one sound mix, then reduce motion on both MPCs
g = Graph(LIB, 'ApplySettings')
e = g.at(entry_node(g), 0, 0)
prev, nodes = e, [e]
for i, (cls, var) in enumerate((('SC_Master', 'MasterVolume'), ('SC_SFX', 'EffectsVolume'),
                                ('SC_Ambience', 'AmbienceVolume'), ('SC_UI', 'InterfaceVolume'))):
    x = 320 + i * 384
    vol = g.get(var, x - 64, 224, class_path=SG_C)
    g.link(e, 'Settings', vol, 'self')
    ov = g.call(f'{GS}:SetSoundMixClassOverride', x, 0, InSoundMixModifier=f'{MIX}/SCM_Settings.SCM_Settings',
                InSoundClass=f'{MIX}/{cls}.{cls}', FadeInTime=0.1)
    g.link(prev, 'then', ov, 'execute'); g.link(vol, var, ov, 'Volume')
    prev = ov
    nodes += [vol, ov]
push = g.call(f'{GS}:PushSoundMixModifier', 1856, 0, InSoundMixModifier=f'{MIX}/SCM_Settings.SCM_Settings')
g.link(prev, 'then', push, 'execute')
g.comment('Audio volumes', 'Four volume overrides on SCM_Settings (audio lane), then push the mix', nodes + [push], C_DATA)
rm = g.get('bReduceMotion', 2112, 224, class_path=SG_C); g.link(e, 'Settings', rm, 'self')
rmf = g.call('/Script/Engine.KismetMathLibrary:Conv_BoolToDouble', 2176, 320)
ui = g.call('/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue', 2240, 0,
            Collection='/Game/FoA/UI/Style/MPC_UI.MPC_UI', ParameterName='ReduceMotion')
g.link(push, 'then', ui, 'execute'); g.link(rm, 'bReduceMotion', rmf, 'InBool'); g.link(rmf, 'ReturnValue', ui, 'ParameterValue')
acc = [rm, rmf, ui]
if unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream'):
    dream = g.call('/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue', 2592, 0,
                   Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream', ParameterName='ReduceMotion')
    g.link(ui, 'then', dream, 'execute'); g.link(rmf, 'ReturnValue', dream, 'ParameterValue')
    acc.append(dream)
g.comment('Reduce motion', 'One flag for UI sand (MPC_UI) and the dream post-process (MPC_Dream)', acc, C_DATA)

# Look settings apply immediately on a possessed player; startup without a pawn safely skips the cast.
player = g.call(f'{GS}:GetPlayerCharacter', 2912, 224, PlayerIndex=0)
names = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToBP_ThirdPersonCharacter')]
assert names, 'BP_ThirdPersonCharacter must expose ApplyLookSettings first'
cast = g.at(g.ed.create_node_from_name(names[0], V2(3200, 0), []), 3200, 0)
look = g.call('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C:ApplyLookSettings', 3552, 0)
g.link(player, 'ReturnValue', cast, 'Object'); g.exec_chain(acc[-1], cast, look)
g.link(cast, 'AsBP_ThirdPersonCharacter', look, 'self'); g.link(e, 'Settings', look, 'Settings')
g.comment('Apply look settings', 'Sensitivity and invert take effect without a new day', [player, cast, look], C_DATA)

# LoadAndApplySettings: called by BP_FoAFrontEnd at BeginPlay
g = Graph(LIB, 'LoadAndApplySettings')
e = g.at(entry_node(g), 0, 0)
load = g.call(self_call(LIB, 'LoadSettings'), 288, 0)
apply_ = g.call(self_call(LIB, 'ApplySettings'), 608, 0)
ret = g.at(result(g), 928, 0)
g.exec_chain(e, load, apply_); g.link(apply_, 'then', ret, 'execute')
g.link(load, 'Settings', apply_, 'Settings'); g.link(load, 'Settings', ret, 'Settings')
g.comment('Load and apply', 'Boot path: read the slot and apply audio + accessibility', [e, load, apply_, ret], C_DATA)
compile_save(LIB)
