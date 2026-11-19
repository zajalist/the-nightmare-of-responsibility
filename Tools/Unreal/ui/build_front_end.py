"""BP_FoAFrontEnd: the one UI flow manager, placed in L_Tutorial_Bedroom next to BP_MenuCamera. Run via ue_remote.py.
Flow: BeginPlay -> menu camera + looping LS_MainMenu_Camera + dream menu preset -> splash -> title -> main menu.
WakeUp fades to black; on the first start the story plays (StoryClass), then FinishWake hands over to gameplay and
BP_BeatDirector.BeginMorning (LS_WakeUp owns the camera). Every UI sound goes through PlayUISound; no level loading.
Widgets reach it through their Host variable and call one public function per user intent (WakeUp, OpenSettings,
RequestQuit, Resume...), so there is no string switch to keep in sync.
Layout rule: exec flows left to right on one row per function; getters sit under the node that reads them."""
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py').read())
import os
import unreal

PATH = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
W = '/Game/FoA/UI/Widgets'
UWBL = '/Script/UMG.WidgetBlueprintLibrary'
GS = '/Script/Engine.GameplayStatics'
PCC = '/Script/Engine.PlayerController'
UW = '/Script/UMG.UserWidget'
KSL = '/Script/Engine.KismetSystemLibrary'
KML = '/Script/Engine.KismetMathLibrary'
SELF = lambda f: self_call(PATH, f)  # noqa: E731

bp = unreal.load_asset(PATH + '.BP_FoAFrontEnd')
if not bp:
    fac = unreal.BlueprintFactory()
    fac.set_editor_property('parent_class', unreal.Actor)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_FoAFrontEnd', '/Game/FoA/UI/Framework',
                                                                 unreal.Blueprint, fac)
assert bp
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)

UWC = class_ref(unreal.UserWidget)
SCREENS = [  # var, default class (may not exist yet; set later by the screen builders)
    ('SplashClass', f'{W}/Menus/WBP_BootSplash.WBP_BootSplash_C'), ('TitleClass', f'{W}/Menus/WBP_Title.WBP_Title_C'),
    ('MainMenuClass', f'{W}/Menus/WBP_MainMenu.WBP_MainMenu_C'),
    ('SettingsClass', f'{W}/Menus/WBP_Settings.WBP_Settings_C'), ('CreditsClass', f'{W}/Menus/WBP_Credits.WBP_Credits_C'),
    ('PauseClass', f'{W}/Menus/WBP_Pause.WBP_Pause_C'), ('ConfirmClass', f'{W}/Common/WBP_ConfirmDialog.WBP_ConfirmDialog_C'),
    ('HUDClass', '/Game/FoA/UI/Game/WBP_HUD.WBP_HUD_C'),
]
SFX = '/Game/FoA/Audio/SFX/UI_FrontEnd'
CUES = {  # slot -> the audio lane's cue (table of 2026-11-05); a missing asset leaves the slot empty, so it stays silent
    'SndBootSwell': 'SFX_FE_BootSwell', 'SndSplashThump': 'SFX_FE_SplashThump', 'SndSandForm': 'SFX_FE_SandForm',
    'SndSandScatter': 'SFX_FE_SandScatter', 'SndTitleReveal': 'SFX_FE_TitleReveal', 'SndTitleBed': 'SFX_FE_TitleBed',
    'SndGlitchStinger': 'SFX_FE_GlitchStinger', 'SndBack': 'SFX_FE_Back', 'SndWakeUpPress': 'SFX_FE_WakeUpPress',
    'SndHeartbeatBlack': 'SFX_FE_HeartbeatBlack', 'SndPanelTransition': 'SFX_FE_PanelTransition',
    'SndStoryBed': 'SFX_FE_StoryBed', 'SndEyelids': 'SFX_FE_Eyelids', 'SndPauseIn': 'SFX_FE_PauseIn',
    'SndPauseOut': 'SFX_FE_PauseOut', 'SndConfirm': 'SFX_FE_Confirm'}
SOUNDS = list(CUES)
WAKE_PRESS_SECONDS = 0.15  # Respond immediately; the press sound can finish under black.
ensure_vars(PATH, [
    ('MenuCamera', ptype(unreal.CineCameraActor), '', 'Front End', True),
    ('MenuSequence', ptype(unreal.LevelSequenceActor), '', 'Front End', True),
    ('bSkipFrontEnd', ptype('bool'), 'false', 'Front End', True),
] + [(n, UWC, '', 'Front End|Screens', True) for n, _ in SCREENS] + [
    ('PC', ptype(unreal.PlayerController), '', 'Front End|State', False),
    ('Screen', ptype(unreal.UserWidget), '', 'Front End|State', False),
    ('Overlay', ptype(unreal.UserWidget), '', 'Front End|State', False),
    ('PauseMenu', ptype(unreal.UserWidget), '', 'Front End|State', False),
    ('HUD', ptype(unreal.UserWidget), '', 'Front End|State', False),
    ('bInGameplay', ptype('bool'), 'false', 'Front End|State', False),
    ('PendingConfirm', ptype('name'), 'None', 'Front End|State', False),
    ('ConfirmTitle', ptype('text'), '', 'Front End|State', False),
    ('ConfirmBody', ptype('text'), '', 'Front End|State', False),
    ('ConfirmLabel', ptype('text'), '', 'Front End|State', False),
    ('StoryClass', UWC, '', 'Front End|Screens', True),       # first-start story (look-dev lane); None skips it
    ('Story', ptype(unreal.UserWidget), '', 'Front End|State', False),
    ('Bed', ptype(unreal.AudioComponent), '', 'Front End|State', False),     # the looping title or story bed
    ('WakeBlackSeconds', ptype('real'), '1.5', 'Front End', True),         # heartbeat in the dark before the story/wake
    ('BlackOverlay', ptype(unreal.UserWidget), '', 'Front End|State', False),  # the cut to black (UMG: always reaches the screen)
    ('bWaking', ptype('bool'), 'false', 'Front End|State', False),            # Wake up runs once per press
] + [(n, ptype(unreal.SoundBase), '', 'Front End|Sound', True) for n in SOUNDS])
if 'WakeBlendTime' in [str(n) for n in BEL.list_member_variable_names(bp)]:  # blend era, superseded by the hard cut
    GE.get_graph_editor_by_name(bp, 'EventGraph').remove_member_variable('WakeBlendTime')
# Screen classes are class defaults: Hayba blueprint_set_defaults sets them after the Hayba compile (no Python CDO write)
DEFAULTS = {n: cls_path for n, cls_path in SCREENS if unreal.load_class(None, cls_path)}
STORY = '/Game/FoA/UI/Intro/WBP_IntroStory.WBP_IntroStory_C'  # look-dev lane's story; set once its graph compiles
if unreal.load_class(None, STORY):
    DEFAULTS['StoryClass'] = STORY
DEFAULTS.update({slot: f'{SFX}/{cue}.{cue}' for slot, cue in CUES.items()
                 if unreal.EditorAssetLibrary.does_asset_exist(f'{SFX}/{cue}')})

FUNCS = ['FinishWake', 'HandleBack', 'FocusUI', 'ShowScreen', 'OpenOverlay', 'SetDreamMenuMode', 'PlayMenuCamera', 'StartFrontEnd',
         'EnterGameplay', 'StopMenuSequence', 'OnSplashFinished', 'OnTitleConfirmed', 'WakeUp', 'OpenSettings',
         'OpenCredits', 'CloseOverlay', 'TogglePause', 'Resume', 'AskConfirm', 'RequestQuit', 'RequestRestartDay',
         'RequestQuitToTitle', 'ConfirmPending', 'RestartDay', 'ReturnToTitle', 'PlayUISound', 'OnSplashCue', 'TitleGlitch',
         'AfterWakeFade', 'OnStoryFinished', 'StartBed', 'StopBed', 'CutToBlack', 'OpenPhone', 'ClosePhone',
         'EndOfLevel', 'AfterEndFade']
for f in FUNCS:
    drop_function(PATH, f)
# Pre-create every function so later graphs can call ones defined after them.
for f, ins in (('FocusUI', [('Target', ptype(unreal.UserWidget))]), ('ShowScreen', [('ScreenClass', UWC)]),
               ('OpenOverlay', [('OverlayClass', UWC)]), ('SetDreamMenuMode', [('bMenu', ptype('bool'))]),
               ('AskConfirm', [('Action', ptype('name')), ('Title', ptype('text')), ('Body', ptype('text')),
                               ('ConfirmText', ptype('text'))]),
               ('PlayUISound', [('Cue', ptype(unreal.SoundBase))]), ('OnSplashCue', [('Index', ptype('int'))]),
               ('StartBed', [('Loop', ptype(unreal.SoundBase))])):
    Graph.function(PATH, f, inputs=ins)
for f in FUNCS:
    if f not in ('FocusUI', 'ShowScreen', 'OpenOverlay', 'SetDreamMenuMode', 'AskConfirm', 'PlayUISound', 'OnSplashCue',
                 'StartBed'):
        Graph.function(PATH, f)


def fn(name):
    g = Graph(PATH, name)
    e = g.at(entry_node(g), 0, 0)
    return g, e


def get_pc(g, x, y):
    return g.get('PC', x, y)


def cursor(g, x, y, show):
    """PlayerController.bShowMouseCursor setter (a property, not a function)."""
    n = g.set('bShowMouseCursor', x, y, class_path='/Script/Engine.PlayerController')
    g.default(n, 'bShowMouseCursor', show)
    return n


def remove_if_valid(g, var, x, y):
    """Branch(IsValid(var)) -> RemoveFromParent. Wire exec into .br; both rm 'then' and br 'False' go on."""
    get = g.get(var, x - 64, y + 160)
    ok = g.call(f'{KSL}:IsValid', x - 64, y + 240)
    br = g.branch(x, y)
    rm = g.call('/Script/UMG.Widget:RemoveFromParent', x + 256, y - 96)
    g.link(get, var, ok, 'Object'); g.link(ok, 'ReturnValue', br, 'Condition')
    g.link(br, 'True', rm, 'execute'); g.link(get, var, rm, 'self')
    return br, rm, [get, ok, br, rm]


def then_both(g, br, rm, nxt):
    g.link(rm, 'then', nxt, 'execute'); g.link(br, 'False', nxt, 'execute')


def director_call(g, func, x, y):
    """GetActorOfClass(BP_BeatDirector) -> Cast -> func, or None when the director lacks func (events included)."""
    BDC = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
    if not unreal.load_class(None, BDC):
        return None
    raw = g.ed.add_call_function_node(BDC + ':' + func)
    if not raw:
        return None
    call = g.at(raw, x + 704, y)
    find = g.call(f'{GS}:GetActorOfClass', x, y, ActorClass=BDC)
    casts = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToBP_BeatDirector')]
    cast = g.at(g.ed.create_node_from_name(casts[0], V2(x + 352, y), []), x + 352, y)
    g.link(find, 'then', cast, 'execute'); g.link(find, 'ReturnValue', cast, 'Object')
    g.link(cast, 'then', call, 'execute'); g.link(cast, 'AsBP_BeatDirector', call, 'self')
    return find, cast, call


def sound(g, var, x, y):
    """PlayUISound(<var>) at (x, y), its getter underneath; returns (call, getter)."""
    get = g.get(var, x - 64, y + 160)
    call = g.call(SELF('PlayUISound'), x, y)
    g.link(get, var, call, 'Cue')
    return call, get


# ---- PlayUISound(Cue): the one place UI sounds start (2D, plays while paused); a None cue is silent
g, e = fn('PlayUISound')
ps = g.call(f'{GS}:PlaySound2D', 288, 0, bIsUISound='true')
g.exec_chain(e, ps); g.link(e, 'Cue', ps, 'Sound')
g.comment('Play a UI sound', 'Every front-end cue goes through here: 2D, UI sound (audible while paused), None = silent',
          [e, ps], C_VISUAL)

# ---- StartBed(Loop) / StopBed: the title and story beds (loops, routed to SMX_FE_Bed by the cue); one at a time
g, e = fn('StopBed')
bed = g.get('Bed', 224, 160)
ok = g.call(f'{KSL}:IsValid', 288, 160)
br = g.branch(512, 0)
bed2 = g.get('Bed', 704, 160)
fo = g.call('/Script/Engine.AudioComponent:FadeOut', 768, 0, FadeOutDuration=1.5, FadeVolumeLevel=0.0)
g.exec_chain(e, br); g.link(bed, 'Bed', ok, 'Object'); g.link(ok, 'ReturnValue', br, 'Condition')
g.link(br, 'True', fo, 'execute'); g.link(bed2, 'Bed', fo, 'self')
g.comment('Stop the bed', 'Fade the running loop out over 1.5 s (it destroys itself when silent)', [e, bed, ok, br, bed2, fo],
          C_VISUAL)

g, e = fn('StartBed')
stop = g.call(SELF('StopBed'), 288, 0)
sp = g.call(f'{GS}:SpawnSound2D', 576, 0, bAutoDestroy='true')
setb = g.set('Bed', 928, 0)
g.exec_chain(e, stop, sp, setb); g.link(e, 'Loop', sp, 'Sound'); g.link(sp, 'ReturnValue', setb, 'Bed')
g.comment('Start a bed', 'Any running bed fades out first; the new loop is kept so it can be stopped', [e, stop, sp, setb],
          C_VISUAL)


def bed(g, var, x, y):
    """StartBed(<var>) at (x, y), its getter underneath; returns (call, getter)."""
    get = g.get(var, x - 64, y + 160)
    call = g.call(SELF('StartBed'), x, y)
    g.link(get, var, call, 'Loop')
    return call, get


# ---- OnSplashCue(Index): the splash calls it at each fade (0 UE in, 1 UE out, 2 Lux3D in, 3 out, 4 Hayba form, 5 dissolve)
g, e = fn('OnSplashCue')
odd = g.call(f'{KML}:Percent_IntInt', 224, 224); g.default(odd, 'B', 2)
even = g.call(f'{KML}:EqualEqual_IntInt', 448, 224); g.default(even, 'B', 0)
hay = g.call(f'{KML}:GreaterEqual_IntInt', 224, 416); g.default(hay, 'B', 4)
cue_in = g.call(f'{KML}:SelectObject', 704, 288)
cue_out = g.call(f'{KML}:SelectObject', 704, 480)
pick = g.call(f'{KML}:SelectObject', 960, 224)
gets = [g.get(v, 448, y) for v, y in (('SndSandForm', 320), ('SndSplashThump', 384), ('SndSandScatter', 512))]
casts = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToSoundBase')]
cast = g.at(g.ed.create_node_from_name(casts[0], V2(1216, 0), []), 1216, 0)
play = g.call(SELF('PlayUISound'), 1568, 0)
g.exec_chain(e, cast); g.link(cast, 'then', play, 'execute')
g.link(e, 'Index', odd, 'A'); g.link(odd, 'ReturnValue', even, 'A'); g.link(e, 'Index', hay, 'A')
g.link(gets[0], 'SndSandForm', cue_in, 'A'); g.link(gets[1], 'SndSplashThump', cue_in, 'B'); g.link(hay, 'ReturnValue', cue_in, 'bSelectA')
g.link(gets[2], 'SndSandScatter', cue_out, 'A')  # B left empty: the UE and Lux3D fade-outs are silent
g.link(hay, 'ReturnValue', cue_out, 'bSelectA')
g.link(cue_in, 'ReturnValue', pick, 'A'); g.link(cue_out, 'ReturnValue', pick, 'B'); g.link(even, 'ReturnValue', pick, 'bSelectA')
g.link(pick, 'ReturnValue', cast, 'Object'); g.link(cast, 'AsSoundBase', play, 'Cue')
g.comment('Splash cue', 'Even index: a card fades up (thump); odd: it fades out (silent); 4 and 5: the Hayba sand form and scatter',
          [e, odd, even, hay, cue_in, cue_out, pick, cast, play] + gets, C_VISUAL)

# ---- TitleGlitch (timer on the title and main menu): a datamosh burst of 0.5-1.2 s with its stinger, every 4.5-9.5 s
g, e = fn('TitleGlitch')
DD = '/Game/FoA/PostProcess/BP_DreamDirector'
if unreal.load_class(None, DD + '.BP_DreamDirector_C'):
    find = g.call(f'{GS}:GetActorOfClass', 224, 0, ActorClass=DD + '.BP_DreamDirector_C')
    dcasts = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToBP_DreamDirector')]
    dcast = g.at(g.ed.create_node_from_name(dcasts[0], V2(576, 0), []), 576, 0)
    st = g.call(f'{KML}:RandomFloatInRange', 672, 224, Min=0.75, Max=1.0)
    secs = g.call(f'{KML}:RandomFloatInRange', 672, 352, Min=0.5, Max=1.2)
    burst = g.call(DD + '.BP_DreamDirector_C:TriggerGlitchBurst', 928, 0)
    sting, sget = sound(g, 'SndGlitchStinger', 1280, 0)
    again = g.call(f'{KML}:RandomFloatInRange', 1504, 224, Min=4.5, Max=9.5)
    rearm = g.call(f'{KSL}:K2_SetTimer', 1568, 0, FunctionName='TitleGlitch')
    g.exec_chain(e, find, dcast); g.link(find, 'ReturnValue', dcast, 'Object')
    g.link(dcast, 'then', burst, 'execute'); g.link(dcast, 'AsBP_DreamDirector', burst, 'self')
    g.link(st, 'ReturnValue', burst, 'Strength'); g.link(secs, 'ReturnValue', burst, 'Seconds')
    g.exec_chain(burst, sting, rearm); g.link(again, 'ReturnValue', rearm, 'Time')
    g.comment('Title datamosh', 'Blocks of the frame drag for 0.5-1.2 s, then snap clean; stinger on the same frame; '
              'ReduceMotion disables mosh in the dream stack', [e, find, dcast, st, secs, burst, sting, sget, again, rearm],
              C_VISUAL)
else:
    g.comment('Title datamosh', 'Hook: BP_DreamDirector.TriggerGlitchBurst once the pp lane ships it', [e], C_VISUAL)


# ---- FocusUI(Target): menus own focus; Game+UI so keys a widget leaves unhandled (Esc, B) reach HandleBack
g, e = fn('FocusUI')
pc = get_pc(g, 224, 160)
mode = g.call(f'{UWBL}:SetInputMode_GameAndUIEx', 288, 0, bHideCursorDuringCapture='false')
pc2 = get_pc(g, 640, 160)
cur = cursor(g, 704, 0, 'true')
pc3 = get_pc(g, 960, 160)
mv = g.call('/Script/Engine.Controller:SetIgnoreMoveInput', 1024, 0, bNewMoveInput='true')
pc4 = get_pc(g, 1280, 160)
lk = g.call('/Script/Engine.Controller:SetIgnoreLookInput', 1344, 0, bNewLookInput='true')
# no cursor over the boot cards or the title (the page shows none); menus and overlays get it
tc = g.call(f'{GS}:GetObjectClass', 448, 320)
sc = g.get('SplashClass', 448, 400); ttc = g.get('TitleClass', 448, 464)
is_s = g.call(f'{KML}:EqualEqual_ClassClass', 640, 320); is_t = g.call(f'{KML}:EqualEqual_ClassClass', 640, 416)
either = g.call(f'{KML}:BooleanOR', 832, 352); show = g.call(f'{KML}:Not_PreBool', 960, 352)
g.link(e, 'Target', tc, 'Object'); g.link(tc, 'ReturnValue', is_s, 'A'); g.link(sc, 'SplashClass', is_s, 'B')
g.link(tc, 'ReturnValue', is_t, 'A'); g.link(ttc, 'TitleClass', is_t, 'B')
g.link(is_s, 'ReturnValue', either, 'A'); g.link(is_t, 'ReturnValue', either, 'B'); g.link(either, 'ReturnValue', show, 'A')
g.link(show, 'ReturnValue', cur, 'bShowMouseCursor')
g.exec_chain(e, mode, cur, mv, lk)
g.link(pc, 'PC', mode, 'PlayerController'); g.link(e, 'Target', mode, 'InWidgetToFocus')
g.link(pc2, 'PC', cur, 'self'); g.link(pc3, 'PC', mv, 'self'); g.link(pc4, 'PC', lk, 'self')
g.comment('Focus UI', 'Focus the screen, cursor only in menus, the hidden pawn ignores move/look; unhandled keys reach Back',
          [e, pc, mode, pc2, cur, pc3, mv, pc4, lk, tc, sc, ttc, is_s, is_t, either, show], C_LOGIC)

# ---- ShowScreen(ScreenClass): replace the full-screen widget (splash, title, main menu)
g, e = fn('ShowScreen')
br, rm, guard = remove_if_valid(g, 'Screen', 224, 0)
cw = g.node('UserInterface|CreateWidget', 832, 0)
pc = get_pc(g, 768, 192)
setv = g.set('Screen', 1152, 0)
add = g.call(f'{UW}:AddToViewport', 1408, 0, ZOrder=10)
foc = g.call(SELF('FocusUI'), 1696, 0)
g.exec_chain(e, br); then_both(g, br, rm, cw); g.exec_chain(cw, setv, add, foc)
old = guard[0]
g.link(e, 'ScreenClass', cw, 'Class'); g.link(pc, 'PC', cw, 'OwningPlayer')
g.link(cw, 'ReturnValue', setv, 'Screen'); g.link(setv, 'Screen', add, 'self'); g.link(setv, 'Screen', foc, 'Target')
g.comment('Show screen', 'Swap the full-screen widget (the old one is removed only when there is one)',
          [e] + guard + [cw, pc, setv, add, foc], C_VISUAL)

# ---- OpenOverlay(OverlayClass): settings, credits or a confirm dialog on top of the current screen
g, e = fn('OpenOverlay')
okc = g.call(f'{KSL}:IsValidClass', 160, 160)
br = g.branch(288, 0)  # Settings / Credits not built yet: a quiet no-op, not Accessed None
cw = g.node('UserInterface|CreateWidget', 544, 0)
pc = get_pc(g, 480, 192)
setv = g.set('Overlay', 864, 0)
add = g.call(f'{UW}:AddToViewport', 1120, 0, ZOrder=20)
foc = g.call(SELF('FocusUI'), 1408, 0)
g.exec_chain(e, br); g.link(e, 'OverlayClass', okc, 'Class'); g.link(okc, 'ReturnValue', br, 'Condition')
g.link(br, 'True', cw, 'execute'); g.exec_chain(cw, setv, add, foc)
g.link(e, 'OverlayClass', cw, 'Class'); g.link(pc, 'PC', cw, 'OwningPlayer')
g.link(cw, 'ReturnValue', setv, 'Overlay'); g.link(setv, 'Overlay', add, 'self'); g.link(setv, 'Overlay', foc, 'Target')
g.comment('Open overlay', 'One overlay at a time above screens (Z 20); a missing overlay class does nothing',
          [e, okc, br, cw, pc, setv, add, foc], C_VISUAL)

# ---- SetDreamMenuMode(bMenu): the post-process lane's BP_DreamDirector.SetMenuMode (skips quietly if absent)
g, e = fn('SetDreamMenuMode')
DD = '/Game/FoA/PostProcess/BP_DreamDirector'
if unreal.load_class(None, DD + '.BP_DreamDirector_C'):
    find = g.call(f'{GS}:GetActorOfClass', 224, 160, ActorClass=DD + '.BP_DreamDirector_C')
    casts = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToBP_DreamDirector')]
    cast = g.at(g.ed.create_node_from_name(casts[0], V2(576, 0), []), 576, 0)
    menu = g.call(DD + '.BP_DreamDirector_C:SetMenuMode', 928, 0)
    g.exec_chain(e, find, cast)
    g.link(find, 'ReturnValue', cast, 'Object'); g.link(cast, 'then', menu, 'execute')
    g.link(cast, 'AsBP_DreamDirector', menu, 'self'); g.link(e, 'bMenu', menu, 'Enabled')
    g.comment('Dream menu preset', 'Stronger echoes, breathing vignette and grain while menus are up; no-op if absent',
              [e, find, cast, menu], C_VISUAL)
else:
    g.comment('Dream menu preset', 'Hook: BP_DreamDirector.SetMenuMode(bMenu) once the pp lane ships it', [e], C_VISUAL)

# ---- PlayMenuCamera: view through the menu camera, loop its drift
g, e = fn('PlayMenuCamera')
pc = get_pc(g, 224, 192)
cam = g.get('MenuCamera', 224, 272)
vt = g.call(f'{PCC}:SetViewTargetWithBlend', 288, 0, BlendTime=0.0)
seqa = g.get('MenuSequence', 640, 160)
player = g.call('/Script/LevelSequence.LevelSequenceActor:GetSequencePlayer', 704, 160)
play = g.call('/Script/MovieScene.MovieSceneSequencePlayer:Play', 1024, 0)
g.exec_chain(e, vt, play)
g.link(pc, 'PC', vt, 'self'); g.link(cam, 'MenuCamera', vt, 'NewViewTarget')
g.link(seqa, 'MenuSequence', player, 'self'); g.link(player, 'ReturnValue', play, 'self')
g.comment('Menu camera', 'View through BP_MenuCamera and loop LS_MainMenu_Camera (24 s drift + focus breathing)',
          [e, pc, cam, vt, seqa, player, play], C_VISUAL)

# ---- StartFrontEnd: camera, dream preset, splash
g, e = fn('StartFrontEnd')
cam = g.call(SELF('PlayMenuCamera'), 288, 0)
pcx = get_pc(g, 512, 192)
pawn = g.call('/Script/Engine.Controller:K2_GetPawn', 576, 192)
pawn_valid = g.call(f'{KSL}:IsValid', 768, 192)
can_hide = g.branch(768, 0)
hide = g.call('/Script/Engine.Actor:SetActorHiddenInGame', 1024, 96, bNewHidden='true')
dream = g.call(SELF('SetDreamMenuMode'), 576, 0, bMenu='true')
cls = g.get('SplashClass', 800, 160)
show = g.call(SELF('ShowScreen'), 864, 0)
swell, swget = sound(g, 'SndBootSwell', 1760, 0)
g.exec_chain(e, cam, can_hide); g.exec_chain(hide, dream, show, swell)
g.link(can_hide, 'True', hide, 'execute'); g.link(can_hide, 'False', dream, 'execute')
g.link(pawn, 'ReturnValue', pawn_valid, 'Object'); g.link(pawn_valid, 'ReturnValue', can_hide, 'Condition')
g.link(cls, 'SplashClass', show, 'ScreenClass')
g.link(pcx, 'PC', pawn, 'self'); g.link(pawn, 'ReturnValue', hide, 'self')
g.at(dream, 1184, 0); g.at(cls, 1408, 160); g.at(show, 1472, 0)
g.comment('Start front end', 'Menu camera on the empty bed (pawn hidden), stronger dream look, then the boot splash',
          [e, cam, pcx, pawn, pawn_valid, can_hide, hide, dream, cls, show, swell, swget], C_EVENT)

# ---- EnterGameplay: game input, HUD
g, e = fn('EnterGameplay')
flag = g.set('bInGameplay', 256, 0); g.default(flag, 'bInGameplay', 'true')
pcx = get_pc(g, 1664, 192)
pawn0 = g.call('/Script/Engine.Controller:K2_GetPawn', 1728, 192)
show_p = g.call('/Script/Engine.Actor:SetActorHiddenInGame', 1984, 0, bNewHidden='false')
pc = get_pc(g, 448, 192)
mode = g.call(f'{UWBL}:SetInputMode_GameOnly', 512, 0)
cur = cursor(g, 832, 0, 'false')
pc2 = get_pc(g, 768, 192)
cw = g.node('UserInterface|CreateWidget', 1152, 0)
hcls = g.get('HUDClass', 1088, 192); pc3 = get_pc(g, 1088, 272)
seth = g.set('HUD', 1472, 0)
add = g.call(f'{UW}:AddToViewport', 1728, 0, ZOrder=0)
rst = g.call('/Script/Engine.Controller:ResetIgnoreInputFlags', 2240, 0)
pcr = get_pc(g, 2176, 160)
g.exec_chain(e, flag, mode, cur, cw, seth, add, show_p, rst)
g.link(pcr, 'PC', rst, 'self')
g.link(pcx, 'PC', pawn0, 'self'); g.link(pawn0, 'ReturnValue', show_p, 'self')
g.link(pc, 'PC', mode, 'PlayerController'); g.link(pc2, 'PC', cur, 'self')
g.link(hcls, 'HUDClass', cw, 'Class'); g.link(pc3, 'PC', cw, 'OwningPlayer')
g.link(cw, 'ReturnValue', seth, 'HUD'); g.link(seth, 'HUD', add, 'self')
g.comment('Enter gameplay', 'Game-only input, hide the cursor, show the HUD', [e, flag, pc, mode, cur, pc2, cw, hcls, pc3,
                                                                               seth, add, pcx, pawn0, show_p, rst, pcr], C_LOGIC)
pm = g.get('PauseMenu', 2496, 160)
pmok = g.call(f'{KSL}:IsValid', 2560, 160)
pbr = g.branch(2752, 0)
pcw = g.node('UserInterface|CreateWidget', 3008, 96)
pcls = g.get('PauseClass', 2944, 288); ppc = get_pc(g, 2944, 368)
psv = g.set('PauseMenu', 3328, 96)
padd = g.call(f'{UW}:AddToViewport', 3584, 96, ZOrder=15)
phide = g.call('/Script/UMG.Widget:SetVisibility', 3840, 96, InVisibility='Collapsed')
g.link(rst, 'then', pbr, 'execute'); g.link(pm, 'PauseMenu', pmok, 'Object'); g.link(pmok, 'ReturnValue', pbr, 'Condition')
g.link(pbr, 'False', pcw, 'execute'); g.exec_chain(pcw, psv, padd, phide)
g.link(pcls, 'PauseClass', pcw, 'Class'); g.link(ppc, 'PC', pcw, 'OwningPlayer')
g.link(pcw, 'ReturnValue', psv, 'PauseMenu'); g.link(psv, 'PauseMenu', padd, 'self'); g.link(psv, 'PauseMenu', phide, 'self')
g.comment('Pause menu ready', 'Built once under the wake-up black, collapsed: opening it loads nothing',
          [pm, pmok, pbr, pcw, pcls, ppc, psv, padd, phide], C_LOGIC)

# ---- StopMenuSequence: free the sequence once the wake blend has finished
g, e = fn('StopMenuSequence')
seqa = g.get('MenuSequence', 224, 160)
player = g.call('/Script/LevelSequence.LevelSequenceActor:GetSequencePlayer', 288, 160)
stop = g.call('/Script/MovieScene.MovieSceneSequencePlayer:Stop', 640, 0)
g.exec_chain(e, stop); g.link(seqa, 'MenuSequence', player, 'self'); g.link(player, 'ReturnValue', stop, 'self')
g.comment('Stop menu camera', 'Runs from a timer after the wake blend', [e, seqa, player, stop], C_VISUAL)

# ---- Intents called by widgets
for name, var in (('OnSplashFinished', 'TitleClass'), ('OnTitleConfirmed', 'MainMenuClass')):
    g, e = fn(name)
    cls = g.get(var, 224, 160)
    show = g.call(SELF('ShowScreen'), 288, 0)
    g.link(cls, var, show, 'ScreenClass')
    nodes = [e, cls, show]
    if name == 'OnSplashFinished':  # the world fades up from black with the title (the widget fades itself)
        pcm = g.call('/Script/Engine.GameplayStatics:GetPlayerCameraManager', 512, 160, PlayerIndex=0)
        up = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 576, 0, FromAlpha=1.0, ToAlpha=0.0, Duration=2.2)  # page v3.1: the room fades up over 2.2 s
        rev, rget = sound(g, 'SndTitleReveal', 928, 0)
        tbed, tget = bed(g, 'SndTitleBed', 1216, 0)
        arm = g.call(f'{KSL}:K2_SetTimer', 1504, 0, FunctionName='TitleGlitch', Time=2.5)
        # Only from the splash: its own timer still fires FinishAt after a skip, which put the title back over gameplay
        scr = g.get('Screen', -320, 224); oc = g.call(f'{GS}:GetObjectClass', -256, 224)
        spl = g.get('SplashClass', -256, 320); same = g.call(f'{KML}:EqualEqual_ClassClass', -64, 224)
        only = g.branch(96, 0)
        g.exec_chain(e, only); g.link(only, 'True', show, 'execute'); g.exec_chain(show, up, rev, tbed, arm)
        g.link(scr, 'Screen', oc, 'Object'); g.link(oc, 'ReturnValue', same, 'A'); g.link(spl, 'SplashClass', same, 'B')
        g.link(same, 'ReturnValue', only, 'Condition'); g.link(pcm, 'ReturnValue', up, 'self')
        nodes += [scr, oc, spl, same, only, pcm, up, rev, rget, tbed, tget, arm]
        desc = 'Only from the splash: title fades up from black, reveal sound, the title bed; glitches 2.5 s later'
    else:
        g.link(e, 'then', show, 'execute')
        desc = 'The main menu (the datamosh glitches keep running until Wake up)'
    g.comment(words(name), desc, nodes, C_EVENT)
for name, var in (('OpenSettings', 'SettingsClass'), ('OpenCredits', 'CreditsClass')):
    g, e = fn(name)
    cls = g.get(var, 224, 160)
    ov = g.call(SELF('OpenOverlay'), 288, 0)
    g.exec_chain(e, ov); g.link(cls, var, ov, 'OverlayClass')
    g.comment(words(name), f'Overlay: {var[:-5]}', [e, cls, ov], C_EVENT)

# WakeUp: acknowledge the press with a prompt cut to black while its sound continues.
g, e = fn('WakeUp')
# SetIsEnabled(false) drew the whole menu in the disabled (grey) look for 3 s; hit-test invisible keeps the type as it is
waking = g.get('bWaking', 96, 160); wbr = g.branch(160, 0)
setw = g.set('bWaking', 224, -96); g.default(setw, 'bWaking', 'true')
scr = g.get('Screen', 224, 160)
freeze = g.call('/Script/UMG.Widget:SetVisibility', 448, 0, InVisibility='HitTestInvisible')
noglitch = g.call(f'{KSL}:K2_ClearTimer', 736, 0, FunctionName='TitleGlitch')
press, pget = sound(g, 'SndWakeUpPress', 1024, 0)
stopb = g.call(SELF('StopBed'), 1312, 0)
tmr = g.call(f'{KSL}:K2_SetTimer', 1600, 0, FunctionName='CutToBlack', Time=WAKE_PRESS_SECONDS)
g.exec_chain(e, wbr); g.link(waking, 'bWaking', wbr, 'Condition'); g.link(wbr, 'False', setw, 'execute')
g.exec_chain(setw, freeze, noglitch, press, stopb, tmr); g.link(scr, 'Screen', freeze, 'self')
g.comment('Wake up', 'Once only, menu stops taking clicks, glitches off, then black after 0.15 s',
          [e, waking, wbr, setw, scr, freeze, noglitch, press, pget, stopb, tmr], C_EVENT)

# CutToBlack (timer): hard cut, menu gone, heartbeat in the dark, then the story or the wake-up
g, e = fn('CutToBlack')
pcm = g.call(f'{GS}:GetPlayerCameraManager', 224, 160, PlayerIndex=0)
cut = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 288, 0, FromAlpha=1.0, ToAlpha=1.0, Duration=0.01,
             bHoldWhenFinished='true')
clear_all = g.call('/Script/UMG.WidgetLayoutLibrary:RemoveAllWidgets', 576, 0)
forget = [g.set(v, 864 + i * 256, 0) for i, v in enumerate(('Screen', 'Overlay', 'PauseMenu'))]  # all None now
dream = g.call(SELF('SetDreamMenuMode'), 1664, 0, bMenu='false')
beat, bget = sound(g, 'SndHeartbeatBlack', 1952, 0)
wait = g.get('WakeBlackSeconds', 2176, 160)
tmr = g.call(f'{KSL}:K2_SetTimer', 2240, 0, FunctionName='AfterWakeFade')
BLACK_C = '/Game/FoA/UI/Widgets/Common/WBP_Black.WBP_Black_C'
bcw = g.node('UserInterface|CreateWidget', 2368, 0)
assert PIN.set_pin_value(g.pin(bcw, 'Class', 'in'), BLACK_C)
bpc = get_pc(g, 2304, 192)
sblk = g.set('BlackOverlay', 2688, 0)
badd = g.call(f'{UW}:AddToViewport', 2944, 0, ZOrder=200)
g.link(bpc, 'PC', bcw, 'OwningPlayer'); g.link(bcw, 'ReturnValue', sblk, 'BlackOverlay'); g.link(sblk, 'BlackOverlay', badd, 'self')
g.exec_chain(e, cut, clear_all, *forget, bcw, sblk, badd, dream, beat, tmr)
g.link(pcm, 'ReturnValue', cut, 'self'); g.link(wait, 'WakeBlackSeconds', tmr, 'Time')
g.comment('Cut to black', 'Every front-end widget leaves the viewport under black',
          [e, pcm, cut, clear_all] + forget + [bcw, bpc, sblk, badd, dream, beat, bget, wait, tmr], C_EVENT)

# AfterWakeFade: explicit menu Wake Up always shows the intro; morning rollover bypasses this route.
g, e = fn('AfterWakeFade')
LIBC = '/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C'
SGC = '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'
scls = g.get('StoryClass', 448, 160)
valid = g.call(f'{KSL}:IsValidClass', 512, 160)
br = g.branch(1024, 0)
cw = g.node('UserInterface|CreateWidget', 1792, -160)
scls2 = g.get('StoryClass', 1728, 32); pcs = get_pc(g, 1728, 96)
sets = g.set('Story', 2112, -160)
adds = g.call(f'{UW}:AddToViewport', 2368, -160, ZOrder=40)
reveal = g.call(SELF('DropBlackOverlay'), 2640, -160)
sbed, sget = bed(g, 'SndStoryBed', 2940, -160)
wake = g.call(SELF('FinishWake'), 1280, 160)
g.exec_chain(e, br)
g.link(scls, 'StoryClass', valid, 'Class'); g.link(valid, 'ReturnValue', br, 'Condition')
g.link(br, 'True', cw, 'execute')
g.exec_chain(cw, sets, adds, reveal, sbed)
g.link(scls2, 'StoryClass', cw, 'Class'); g.link(pcs, 'PC', cw, 'OwningPlayer')
g.link(cw, 'ReturnValue', sets, 'Story'); g.link(sets, 'Story', adds, 'self')
g.link(br, 'False', wake, 'execute')
g.comment('Story after Wake Up', '',
          [e, scls, valid, br, cw, scls2, pcs, sets, adds, reveal, sbed, sget, wake], C_EVENT)

# OnStoryFinished: the story widget calls it (or Skip); drop it and wake (LS_WakeUp next)
g, e = fn('OnStoryFinished')
stopb = g.call(SELF('StopBed'), 288, 0)
sty = g.get('Story', 512, 160)
srm = g.call('/Script/UMG.Widget:RemoveFromParent', 576, 0)
fw = g.call(SELF('FinishWake'), 864, 0)
g.at(e,-1700,0)
load = g.call(LIBC + ':LoadSettings', -1400, 0)
version = g.set('IntroVersionSeen', -1100, 0, class_path=SGC); g.default(version,'IntroVersionSeen',2)
mark = g.set('bSeenIntro', -800, 0, class_path=SGC); g.default(mark,'bSeenIntro',True)
save = g.call(LIBC + ':SaveSettings', -500, 0)
g.link(load,'Settings',version,'self');g.link(load,'Settings',mark,'self');g.link(load,'Settings',save,'Settings')
g.exec_chain(e,load,version,mark,save,stopb,srm,fw);g.link(sty,'Story',srm,'self')
g.comment('Remember a finished intro','',[load,version,mark,save],C_EVENT)
g.comment('Story finished', 'Called by the story widget when its last panel ends or is skipped: bed out, then wake',
          [e, stopb, sty, srm, fw], C_EVENT)

# FinishWake (timer, 0.6 s): stop the menu camera, gameplay with the HUD hidden, then the beat director begins
g, e = fn('FinishWake')
stop = g.call(SELF('StopMenuSequence'), 288, 0)
play = g.call(SELF('EnterGameplay'), 576, 0)
hud = g.get('HUD', 800, 160)
hide = g.call('/Script/UMG.Widget:SetRenderOpacity', 864, 0, InOpacity=0.0)
bo = g.get('BlackOverlay', 1088, 352); bok = g.call(f'{KSL}:IsValid', 1088, 416); bbr = g.branch(1088, 192)
brm = g.call('/Script/UMG.Widget:RemoveFromParent', 1280, 192)
wf = g.set('bWaking', 1536, 192); g.default(wf, 'bWaking', 'false')
g.exec_chain(e, stop, play, hide)
g.link(hud, 'HUD', hide, 'self')
nodes = [e, stop, play, hud, hide, bo, bok, bbr, brm]
BD = '/Game/FoA/Gameplay/BP_BeatDirector'
if unreal.load_class(None, BD + '.BP_BeatDirector_C'):
    find = g.call(f'{GS}:GetActorOfClass', 1152, 0, ActorClass=BD + '.BP_BeatDirector_C')
    casts = [n for n in g.ed.list_available_nodes([]) if n.endswith('CastToBP_BeatDirector')]
    cast = g.at(g.ed.create_node_from_name(casts[0], V2(1504, 0), []), 1504, 0)
    begin = g.call(BD + '.BP_BeatDirector_C:BeginMorning', 1856, 0)
    g.link(hide, 'then', find, 'execute'); g.link(find, 'then', cast, 'execute'); g.link(find, 'ReturnValue', cast, 'Object')
    g.link(cast, 'then', begin, 'execute'); g.link(cast, 'AsBP_BeatDirector', begin, 'self')
    nodes += [find, cast, begin]
    g.link(begin, 'then', bbr, 'execute')
g.link(bo, 'BlackOverlay', bok, 'Object'); g.link(bok, 'ReturnValue', bbr, 'Condition'); g.link(bo, 'BlackOverlay', brm, 'self')
g.link(bbr, 'True', brm, 'execute'); g.link(brm, 'then', wf, 'execute'); g.link(bbr, 'False', wf, 'execute')
if not PIN.list_connected_pins(g.pin(bbr, 'execute')):  # no beat director: straight after the HUD
    g.link(hide, 'then', bbr, 'execute')
nodes.append(wf)  # the chain's tail (the fallback fade below continues from it)
# Until the wake-up lane's LS_WakeUp exists nobody fades the camera back in, so fall back to a 1 s fade here.
# Rebuild after BP_WakeUpCinematic lands and this branch disappears (the cinematic owns the fade then).
if not [a for a in unreal.EditorAssetLibrary.list_assets('/Game/FoA', True, False) if a.endswith('.BP_WakeUpCinematic')]:
    pcm2 = g.call('/Script/Engine.GameplayStatics:GetPlayerCameraManager', 2176, 192, PlayerIndex=0)
    unfade = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 2240, 0, FromAlpha=1.0, ToAlpha=0.0, Duration=1.0)
    g.link(nodes[-1], 'then', unfade, 'execute'); g.link(pcm2, 'ReturnValue', unfade, 'self')
    nodes += [pcm2, unfade]
g.comment('Finish waking', 'Gameplay input, HUD at 0 (it fades in on the first OnBeatChanged), BeginMorning starts T0',
          nodes, C_EVENT)

# CloseOverlay: remove it and give focus back to whatever is underneath (pause menu in game, else the screen)
g, e = fn('CloseOverlay')
ov = g.get('Overlay', 224, 160)
valid = g.call(f'{KSL}:IsValid', 224, 256)
guard = g.branch(160, -96)
rm = g.call('/Script/UMG.Widget:RemoveFromParent', 288, 0)
clear = g.set('Overlay', 480, 0)
ing = g.get('bInGameplay', 576, 160)
br = g.branch(640, 0)
pm = g.get('PauseMenu', 864, 112)
f1 = g.call(SELF('FocusUI'), 928, -64)
scr = g.get('Screen', 864, 288)
f2 = g.call(SELF('FocusUI'), 928, 176)
g.exec_chain(e, guard); g.link(ov, 'Overlay', valid, 'Object'); g.link(valid, 'ReturnValue', guard, 'Condition')
g.link(guard, 'True', rm, 'execute'); g.link(guard, 'False', br, 'execute'); g.exec_chain(rm, clear, br)
g.link(ov, 'Overlay', rm, 'self'); g.link(ing, 'bInGameplay', br, 'Condition')
g.link(br, 'True', f1, 'execute'); g.link(pm, 'PauseMenu', f1, 'Target')
g.link(br, 'False', f2, 'execute'); g.link(scr, 'Screen', f2, 'Target')
refocus = g.call(f'{KSL}:K2_SetTimer', 1216, 176, FunctionName='FocusDefault', Time=0.05)
g.link(f2, 'then', refocus, 'execute'); g.link(scr, 'Screen', refocus, 'Object')
g.comment('Close overlay', 'Back from settings, credits or a dialog: focus returns to what is underneath',
          [e, ov, valid, guard, rm, clear, ing, br, pm, f1, scr, f2, refocus], C_LOGIC)

# TogglePause (in gameplay only): pause + menu, or resume
g, e = fn('TogglePause')
paused = g.call(f'{GS}:IsGamePaused', 224, 160)
br = g.branch(288, 0)
res = g.call(SELF('Resume'), 576, -96)
setp = g.call(f'{GS}:SetGamePaused', 576, 96, bPaused='true')
pm = g.get('PauseMenu', 800, 288)
show = g.call('/Script/UMG.Widget:SetVisibility', 864, 96, InVisibility='Visible')
foc = g.call(SELF('FocusUI'), 1152, 96)
g.exec_chain(e, br)
g.link(paused, 'ReturnValue', br, 'Condition')
g.link(br, 'True', res, 'execute'); g.link(br, 'False', setp, 'execute')
psnd, pget = sound(g, 'SndPauseIn', 1440, 96)
g.exec_chain(setp, show, foc, psnd)
g.link(pm, 'PauseMenu', show, 'self'); g.link(pm, 'PauseMenu', foc, 'Target')
g.comment('Toggle pause', 'Esc / Start: freeze the world and show the ready pause menu, or resume',
          [e, paused, br, res, setp, pm, show, foc, psnd, pget], C_LOGIC)

# Resume
g, e = fn('Resume')
pmg = g.get('PauseMenu', 160, 160)
pok = g.call(f'{KSL}:IsValid', 224, 224)
br = g.branch(288, 0)
rm = g.call('/Script/UMG.Widget:SetVisibility', 384, -96, InVisibility='Collapsed')  # kept for the next pause
g.link(pmg, 'PauseMenu', pok, 'Object'); g.link(pok, 'ReturnValue', br, 'Condition')
g.link(br, 'True', rm, 'execute'); g.link(pmg, 'PauseMenu', rm, 'self')
guard = [pmg, pok, br, rm]
setp = g.call(f'{GS}:SetGamePaused', 576, 0, bPaused='false')
pc = get_pc(g, 800, 192)
mode = g.call(f'{UWBL}:SetInputMode_GameOnly', 864, 0)
pc2 = get_pc(g, 1120, 192)
cur = cursor(g, 1184, 0, 'false')
rst = g.call('/Script/Engine.Controller:ResetIgnoreInputFlags', 1472, 0)
pc3 = get_pc(g, 1408, 160)
pout, poget = sound(g, 'SndPauseOut', 1760, 0)
g.exec_chain(e, br); then_both(g, br, rm, setp); g.exec_chain(setp, mode, cur, rst, pout)
g.link(pc, 'PC', mode, 'PlayerController'); g.link(pc2, 'PC', cur, 'self')
g.link(pc3, 'PC', rst, 'self')
g.comment('Resume play', 'Unpause, hand input back to the game, pause-out sound',
          [e] + guard + [setp, pc, mode, pc2, cur, rst, pc3, pout, poget], C_LOGIC)

# AskConfirm(Action, Title, Body, ConfirmText) + the three requests that use it
g, e = fn('AskConfirm')
s1 = g.set('PendingConfirm', 256, 0); s2 = g.set('ConfirmTitle', 512, 0)
s3 = g.set('ConfirmBody', 768, 0); s4 = g.set('ConfirmLabel', 1024, 0)
ccls = g.get('ConfirmClass', 1216, 160)
ov = g.call(SELF('OpenOverlay'), 1280, 0)
g.exec_chain(e, s1, s2, s3, s4, ov)
g.link(e, 'Action', s1, 'PendingConfirm'); g.link(e, 'Title', s2, 'ConfirmTitle')
g.link(e, 'Body', s3, 'ConfirmBody'); g.link(e, 'ConfirmText', s4, 'ConfirmLabel')
g.link(ccls, 'ConfirmClass', ov, 'OverlayClass')
g.comment('Ask to confirm', 'Store the action and its copy; WBP_ConfirmDialog reads them from Host',
          [e, s1, s2, s3, s4, ccls, ov], C_LOGIC)
COPY = {  # plain sentences, no separators
    'RequestQuit': ('Quit', 'Quit to the desktop?', 'The day ends here. What you learned stays with you.', 'Quit'),
    'RequestRestartDay': ('RestartDay', 'Restart the day?', 'You will wake up in bed again. What you learned stays with you.',
                          'Restart'),
    'RequestQuitToTitle': ('QuitToTitle', 'Return to the title?', 'The day ends here. What you learned stays with you.',
                           'Return'),
}
for name, (action, title, body, label) in COPY.items():
    g, e = fn(name)
    ask = g.call(SELF('AskConfirm'), 288, 0, Action=action, Title=title, Body=body, ConfirmText=label)
    g.exec_chain(e, ask)
    g.comment(words(name), f'Confirm first: {title}', [e, ask], C_EVENT)

# ConfirmPending: run the confirmed action
g, e = fn('ConfirmPending')
close = g.call(SELF('CloseOverlay'), 288, 0)
csnd, cget = sound(g, 'SndConfirm', 288, -224)
g.exec_chain(e, close, csnd)
rows = [csnd, cget]
prev = (csnd, 'then')
for i, (action, target) in enumerate((('Quit', None), ('RestartDay', 'RestartDay'), ('QuitToTitle', 'ReturnToTitle'))):
    x = 576 + i * 416
    pend = g.get('PendingConfirm', x - 64, 192)
    eq = g.call(f'{KML}:EqualEqual_NameName', x - 64, 272)
    br = g.branch(x, 0)
    if target:
        act = g.call(SELF(target), x + 224, -160)
    else:
        act = g.call(f'{KSL}:QuitGame', x + 224, -160)
        pc = get_pc(g, x + 160, -256)
        g.link(pc, 'PC', act, 'SpecificPlayer')
    g.link(prev[0], prev[1], br, 'execute')
    g.link(pend, 'PendingConfirm', eq, 'A'); g.default(eq, 'B', action); g.link(eq, 'ReturnValue', br, 'Condition')
    g.link(br, 'True', act, 'execute')
    prev = (br, 'False')
    rows += [pend, eq, br, act]
g.comment('Run the confirmed action', 'Quit to desktop, restart the day, or back to the title',
          [e, close] + rows, C_LOGIC)

# RestartDay: the beat director's RestartDay (a custom event there); reload the level only if the director is missing
g, e = fn('RestartDay')
res = g.call(SELF('Resume'), 288, 0)
dc = director_call(g, 'RestartDay', 576, 0)
lvl = g.call(f'{GS}:GetCurrentLevelName', 1280, 224)
open_ = g.call(f'{GS}:OpenLevel', 1568, 160)
g.link(lvl, 'then', open_, 'execute'); g.link(lvl, 'ReturnValue', open_, 'LevelName')
nodes = [e, res, lvl, open_]
if dc:
    find, cast, call = dc
    g.exec_chain(e, res, find); g.link(cast, 'CastFailed', lvl, 'execute')
    nodes += [find, cast, call]
else:
    g.exec_chain(e, res, lvl)
g.comment('Restart the day', 'BP_BeatDirector.RestartDay(); the level reloads only without a director', nodes, C_LOGIC)

# ReturnToTitle: back to the menu camera and the title, no level load
g, e = fn('ReturnToTitle')
res = g.call(SELF('Resume'), 288, 0)
hud = g.get('HUD', 512, 160)
rm = g.call('/Script/UMG.Widget:RemoveFromParent', 576, 0)
flag = g.set('bInGameplay', 864, 0); g.default(flag, 'bInGameplay', 'false')
cam = g.call(SELF('PlayMenuCamera'), 1120, 0)
dream = g.call(SELF('SetDreamMenuMode'), 1408, 0, bMenu='true')
tcls = g.get('TitleClass', 1632, 160)
show = g.call(SELF('ShowScreen'), 1696, 0)
g.exec_chain(e, res, rm, flag, cam, dream, show)
g.link(hud, 'HUD', rm, 'self'); g.link(tcls, 'TitleClass', show, 'ScreenClass')
BDC = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
title_tail = show
dc = director_call(g, 'ResetToTitle', 1952, 0)
if dc:
    find, cast, reset = dc
    g.link(show, 'then', find, 'execute')
    title_tail = reset
    g.comment('Reset the house', 'BP_BeatDirector.ResetToTitle(): player back in bed, beats before T0 (no new day)',
              [find, cast, reset], C_EVENT)
pcm = g.call(f'{GS}:GetPlayerCameraManager', 2944, 192, PlayerIndex=0)
up = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 2976, 0, FromAlpha=1.0, ToAlpha=0.0, Duration=2.2)  # page v3.1: the room fades up over 2.2 s
rev, rget = sound(g, 'SndTitleReveal', 3264, 0)
tbed, tget = bed(g, 'SndTitleBed', 3552, 0)
arm = g.call(f'{KSL}:K2_SetTimer', 3840, 0, FunctionName='TitleGlitch', Time=2.5)
g.link(pcm, 'ReturnValue', up, 'self')
g.exec_chain(title_tail, up, rev, tbed, arm)
g.comment('Title again', 'Fade up from black, reveal sound, title bed; glitches 2.5 s later',
          [pcm, up, rev, rget, tbed, tget, arm], C_VISUAL)
g.comment('Quit to title', 'Unpause, drop the HUD, menu camera and dream preset, then the title screen',
          [e, res, hud, rm, flag, cam, dream, tcls, show], C_EVENT)

# ---- OpenPhone / ClosePhone: the phone is diegetic (BP_Phone: WBP_Phone on the phone's screen, a camera push-in);
# the front end routes to it and hides the HUD meanwhile. Never a 2D overlay (the user's direction).
PHONE_C = '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'
for name, vis in (('OpenPhone', 'Collapsed'), ('ClosePhone', 'HitTestInvisible')):
    g, e = fn(name)
    if unreal.load_class(None, PHONE_C):
        find = g.call(f'{GS}:GetActorOfClass', 224, 0, ActorClass=PHONE_C)
        pcasts = [n for n in g.ed.list_available_nodes([]) if n.replace(' ', '').endswith('CastToBP_Phone')]
        pcast = g.at(g.ed.create_node_from_name(pcasts[0], V2(576, 0), []), 576, 0)
        raw = g.ed.add_call_function_node(PHONE_C + ':' + name)  # by path only: the palette would find our own OpenPhone
        assert raw, f'BP_Phone.{name} missing: run wire_bp_phone.py first'
        go = g.at(raw, 928, 0)
        hud = g.get('HUD', 1216, 192); hok = g.call(f'{KSL}:IsValid', 1280, 256)
        hbr = g.branch(1472, 0)
        hv = g.call('/Script/UMG.Widget:SetVisibility', 1728, 0, InVisibility=vis)
        g.exec_chain(e, find, pcast); g.link(find, 'ReturnValue', pcast, 'Object')
        g.link(pcast, 'then', go, 'execute'); g.link(pcast, 'AsBP_Phone', go, 'self')
        g.link(go, 'then', hbr, 'execute'); g.link(hud, 'HUD', hok, 'Object'); g.link(hok, 'ReturnValue', hbr, 'Condition')
        g.link(hbr, 'True', hv, 'execute'); g.link(hud, 'HUD', hv, 'self')
        g.comment(words(name), 'BP_Phone does the camera and input; the HUD hides while the phone is up',
                  [e, find, pcast, go, hud, hok, hbr, hv], C_EVENT)
    else:
        g.comment(words(name), 'Hook: BP_Phone (UI/Game) once it exists', [e], C_EVENT)

# ---- EndOfLevel (BP_BeatDirector after T10 WalkedOut): fade to black, then the credits over the title, or the title
g, e = fn('EndOfLevel')
pcm = g.call(f'{GS}:GetPlayerCameraManager', 224, 160, PlayerIndex=0)
fade = g.call('/Script/Engine.PlayerCameraManager:StartCameraFade', 288, 0, FromAlpha=1.0, ToAlpha=1.0, Duration=1.5,  # the director already holds black
              bHoldWhenFinished='true')
tmr = g.call(f'{KSL}:K2_SetTimer', 640, 0, FunctionName='AfterEndFade', Time=1.6)
g.exec_chain(e, fade, tmr); g.link(pcm, 'ReturnValue', fade, 'self')
g.comment('End of level', 'Fade to black over 1.5 s, then the title', [e, pcm, fade, tmr], C_EVENT)

g, e = fn('AfterEndFade')
close = g.call(SELF('ClosePhone'), 288, 0)
title = g.call(SELF('ReturnToTitle'), 576, 0)  # ClosePhone first: the view leaves the phone before the title
ccls = g.get('CreditsClass', 800, 160)
valid = g.call(f'{KSL}:IsValidClass', 864, 160)
br = g.branch(1088, 0)
cred = g.call(SELF('OpenCredits'), 1344, -96)
g.exec_chain(e, close, title, br); g.link(ccls, 'CreditsClass', valid, 'Class'); g.link(valid, 'ReturnValue', br, 'Condition')
g.link(br, 'True', cred, 'execute')
g.comment('Title, then credits', 'Back to the title from black; the credits open on top when they exist',
          [e, close, title, ccls, valid, br, cred], C_EVENT)

# ---- HandleBack: Esc / gamepad B from any menu
g, e = fn('HandleBack')
ov = g.get('Overlay', 160, 192)
ovv = g.call('/Script/Engine.KismetSystemLibrary:IsValid', 224, 192)
br = g.branch(288, 0)
cl = g.call(SELF('CloseOverlay'), 544, -96)
paused = g.call(f'{GS}:IsGamePaused', 480, 224)
br2 = g.branch(544, 96)
res = g.call(SELF('Resume'), 800, 96)
g.exec_chain(e, br)
g.link(ov, 'Overlay', ovv, 'Object'); g.link(ovv, 'ReturnValue', br, 'Condition')
g.link(br, 'True', cl, 'execute'); g.link(br, 'False', br2, 'execute')
g.link(paused, 'ReturnValue', br2, 'Condition'); g.link(br2, 'True', res, 'execute')
b1, bg1 = sound(g, 'SndBack', 864, -96)
g.link(cl, 'then', b1, 'execute')
g.comment('Back key', 'Close the overlay if one is open, else resume if paused; the bare menu goes to the title below',
          [e, ov, ovv, br, cl, paused, br2, res, b1, bg1], C_LOGIC)
scr = g.get('Screen', 1000, 440)
cls = g.call(f'{GS}:GetObjectClass', 1220, 440)
menu = g.get('MainMenuClass', 1220, 580)
same = g.call(f'{KML}:EqualEqual_ClassClass', 1450, 440)
waking = g.get('bWaking', 1220, 710)
notwaking = g.call(f'{KML}:Not_PreBool', 1450, 710)
both = g.call(f'{KML}:BooleanAND', 1690, 440)
guard = g.branch(1920, 240)
title = g.get('TitleClass', 2100, 440)
show = g.call(SELF('ShowScreen'), 2200, 240)
g.link(scr, 'Screen', cls, 'Object'); g.link(cls, 'ReturnValue', same, 'A'); g.link(menu, 'MainMenuClass', same, 'B')
g.link(waking, 'bWaking', notwaking, 'A'); g.link(same, 'ReturnValue', both, 'A'); g.link(notwaking, 'ReturnValue', both, 'B')
g.link(both, 'ReturnValue', guard, 'Condition'); g.link(br2, 'False', guard, 'execute')
g.link(guard, 'True', show, 'execute'); g.link(title, 'TitleClass', show, 'ScreenClass')
g.comment('Back to title', 'Only the bare main menu, before Wake up starts',
          [scr, cls, menu, same, waking, notwaking, both, guard, title, show], C_LOGIC)

# ---- Event graph: BeginPlay and the pause keys
g = Graph(PATH).clear()
bp_ev = g.event('ReceiveBeginPlay', 0, 0)
getpc = g.call(f'{GS}:GetPlayerController', 224, 160)
setpc = g.set('PC', 288, 0)
inp = g.call('/Script/Engine.Actor:EnableInput', 544, 0)
nodes = [bp_ev, getpc, setpc, inp]
prev = inp
LIBP = '/Game/FoA/UI/Framework/BPFL_FoASettings'
if unreal.load_class(None, LIBP + '.BPFL_FoASettings_C'):
    st = g.call(LIBP + '.BPFL_FoASettings_C:LoadAndApplySettings', 832, 0)
    g.link(prev, 'then', st, 'execute'); prev = st; nodes.append(st)
skip = g.get('bSkipFrontEnd', 1088, 160)
br = g.branch(1152, 0)
play = g.call(SELF('EnterGameplay'), 1408, -96)
start = g.call(SELF('StartFrontEnd'), 1408, 96)
# Movie Render Queue (MoviePipelineGameMode) renders the level with no player at the menu: no front end, no menu look
gm = g.call(f'{GS}:GetGameMode', 1088, -320)
gmc = g.call(f'{GS}:GetObjectClass', 1088, -240)
gmn = g.call(f'{KSL}:GetClassDisplayName', 1088, -160)
mrq = g.call('/Script/Engine.KismetStringLibrary:Contains', 1088, -80, Substring='MoviePipeline')
render = g.branch(1024, 0)
g.exec_chain(bp_ev, setpc, inp)
g.link(prev, 'then', render, 'execute'); g.link(render, 'False', br, 'execute')
g.link(gm, 'ReturnValue', gmc, 'Object'); g.link(gmc, 'ReturnValue', gmn, 'Class'); g.link(gmn, 'ReturnValue', mrq, 'SearchIn')
g.link(mrq, 'ReturnValue', render, 'Condition')
g.at(br, 1280, 0); g.at(skip, 1216, 160); g.at(play, 1536, -96); g.at(start, 1536, 96)
g.link(getpc, 'ReturnValue', setpc, 'PC'); g.link(setpc, 'PC', inp, 'PlayerController')
g.link(skip, 'bSkipFrontEnd', br, 'Condition')
g.link(br, 'True', play, 'execute'); g.link(br, 'False', start, 'execute')
g.comment('Start up', 'Cache the controller, take input for the pause keys, apply saved settings, run the front end '
          '(never under a Movie Render Queue render)', nodes + [gm, gmc, gmn, mrq, render, skip, br, play, start], C_EVENT)

# Keys: Esc/Start pause while playing; Esc/B are Back in menus. They run while paused (pause menu, dialogs).
keys = []
ROWS = (('Escape', 'esc'), ('Gamepad_Special_Right', 'start'), ('Gamepad_FaceButton_Right', 'back'))
for i, (key, role) in enumerate(ROWS):
    y = 384 + i * 224
    names = [n for n in g.ed.list_available_nodes([]) if n.startswith('Input|')
             and n.split('|')[-1].replace(' ', '') in (key, key.replace('_', ''))]
    assert names, 'no InputKey node for ' + key
    ev = g.at(g.ed.create_node_from_name(names[0], V2(0, y), []), 0, y)
    for prop in ('execute_when_paused', 'b_execute_when_paused'):
        try:
            ev.set_editor_property(prop, True)
            break
        except Exception:
            pass
    ing = g.get('bInGameplay', 224, y + 112)
    paused = g.call(f'{GS}:IsGamePaused', 224, y + 176)
    playing = g.call('/Script/Engine.KismetMathLibrary:BooleanAND', 480, y + 128)
    notp = g.call('/Script/Engine.KismetMathLibrary:Not_PreBool', 352, y + 192)
    brk = g.branch(704, y)
    tp = g.call(SELF('TogglePause'), 960, y - 64) if role != 'back' else None
    back = g.call(SELF('HandleBack'), 960, y + 64) if role != 'start' else None
    g.link(ing, 'bInGameplay', playing, 'A'); g.link(paused, 'ReturnValue', notp, 'A'); g.link(notp, 'ReturnValue', playing, 'B')
    g.link(ev, 'Pressed', brk, 'execute'); g.link(playing, 'ReturnValue', brk, 'Condition')
    if tp:
        g.link(brk, 'True', tp, 'execute')
    if back:
        g.link(brk, 'False', back, 'execute')
    keys += [n for n in (ev, ing, paused, playing, notp, brk, tp, back) if n]
g.comment('Pause and Back keys', 'Playing: Esc/Start pause. In menus or paused: Esc/B go Back (B is a game action in play)',
          keys, C_EVENT)
compile_save(PATH, defaults=DEFAULTS)

# Preserve the optional read-only diagnostic overlay when rebuilding frontend input.
if unreal.EditorAssetLibrary.does_asset_exist('/Game/FoA/UI/Game/WBP_Debug'):
    exec(open('P:/FoA/Tools/Unreal/ui/install_debug_frontend.py').read())
