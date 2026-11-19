"""ui lane: intro bug sweep. One EXCLUSIVE PIE burst in a new 960x540 window, recorded INSIDE the engine by sweep_rec.py
(a 'Shot showui' BMP per request, ~25/s; never a desktop grab: the editor sits on another virtual desktop, and a desktop
recorder captures whatever the user has in front instead). Frames the level editor viewport stole are dropped by size.
Driven by REAL key presses (Hayba editor_pie_press_key).
  python Tools/Unreal/ui/sweep_intro.py <out dir> cold    # cold boot to LS_WakeUp, no skips, Esc in the menu
  python Tools/Unreal/ui/sweep_intro.py <out dir> skip    # a key at every stage: cards, title fade, menu, black, film
  python Tools/Unreal/ui/sweep_intro.py <out dir> menu    # Settings, Credits, Quit confirm and back with Esc each time
Writes <out>/sweep.mp4, <out>/keys.json (every key: when, which widget had focus, whether UI handled it), and
<out>/frames/fNNNN.png (every recorded frame). Restores the user's PIE window size."""
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402

LANE = 'ui'
os.environ['HAYBA_AGENT_ID'] = os.environ['FOA_AGENT'] = LANE
PLAY = '/Script/UnrealEd.Default__LevelEditorPlaySettings'
W, H, FPS = 960, 540, 25  # requests per second; the kept rate is measured and written to keys.json
SHOTS = 'P:/FoA/Saved/Screenshots/WindowsEditor'
CLIENT = (3, 36)  # PIE window at (0,0): 3 px frame, title bar down to y=35 (measured from the 02:20 shots)
SCRIPTS = {  # (seconds after PIE start, key) ; the boot runs ~19.6 s, the title prompt shows 3.2 s later
    'cold': [(23.5, 'SpaceBar'), (26.5, 'Down'), (27.1, 'Up'), (28.5, 'Enter'), (42.0, 'Escape'), (46.0, None)],
    'skip': [(2.6, 'SpaceBar'), (4.2, 'SpaceBar'), (5.8, 'SpaceBar'), (7.4, 'SpaceBar'), (9.4, 'SpaceBar'),
             (11.0, 'Down'), (11.6, 'Up'), (12.6, 'Enter'), (14.0, 'SpaceBar'), (17.2, 'SpaceBar'),
             (21.0, ('SpaceBar', 1800)), (27.0, 'Escape'), (31.0, None)],
    # every menu layer and back: Settings, Credits, the Quit confirm, then Esc on the bare menu; focus must survive each
    # (PIE bursts are capped near 45 s, so the boot is skipped first)
    # Esc confirms the title (any key, once it is ready) and does nothing on the menu root, so it is pressed twice.
    # every input path: pad A, Enter, a click and Space on the cards; a key while the title fades; pad on the title and
    # menu; mouse hover then keyboard; a click into Settings, rows and pad B back; the Quit confirm by keys and pad B.
    # Esc only at the end: an Esc that reaches the PIE viewport stops the session.
    'input': [(2.6, 'Gamepad_FaceButton_Bottom'), (4.2, 'Enter'), (5.8, {'mouse': 'click', 'text': ''}), (7.4, 'SpaceBar'),
              (9.4, 'SpaceBar'), (11.0, 'Down'), (12.5, 'Tab'), (14.5, 'Tab'), (17.0, 'Gamepad_DPad_Down'),
              (17.7, {'mouse': 'move', 'text': 'Credits'}), (18.4, 'Down'), (19.1, 'Gamepad_DPad_Up'),
              (19.8, 'Gamepad_FaceButton_Right'), (20.5, {'mouse': 'click', 'text': 'Settings'}), (22.5, 'Down'),
              (23.1, 'Right'), (23.8, 'Gamepad_FaceButton_Right'), (25.3, 'Down'), (25.7, 'Down'), (26.1, 'Down'),
              (26.7, 'Enter'), (28.3, 'Right'), (28.9, 'Left'), (29.6, 'Gamepad_FaceButton_Right'), (31.0, None)],
    # measuring run (UI_PERF: no shots, no probe; frame times and hitch dumps): cold boot, Settings in and out, Wake up,
    # the film. No Esc where focus could be the viewport: in PIE that stops the session.
    'perf': [(23.5, 'SpaceBar'), (27.5, 'Down'), (28.1, 'Enter'), (30.5, 'Escape'), (32.0, 'Enter'), (45.0, None)],
    'perfns': [(23.5, 'SpaceBar'), (32.0, 'Enter'), (45.0, None)],  # the same run without opening Settings
    'perfintro': [(23.5, 'SpaceBar'), (32.0, 'Enter'), (40.0, None)],  # fits a 45 s shared-editor slot
    # AAA pass: the boot runs ~6.1 s now. Cold boot, title confirm while it forms, menu focus, Wake up, the film start
    'fast': [(8.0, 'SpaceBar'), (10.0, 'Down'), (10.6, 'Up'), (12.0, 'Enter'), (24.0, None)],
    'perffast': [(8.0, 'SpaceBar'), (10.0, 'Down'), (10.6, 'Up'), (12.0, 'Enter'), (24.0, None)],
    # every menu layer on the fast boot, keyboard only; focus must be visible after every move (focus-visibility check)
    'menufast': [(0.3, {'call': 'CONSOLE', 'cmd': 'au.Debug.SoundWaves 1'}), (0.8, {'menu': True}),
                 # Settings: Audio tab, into the rows, down to Music/Dialogue, one step left and back (the new binds)
                 # Up/Down move between rows (not into the slider); Left/Right on Music change it and the save (no A first)
                 (2.0, 'Down'), (2.7, 'Enter'), (3.8, 'Down'), (4.4, 'Enter'), (5.2, 'Right'), (5.8, 'Down'),
                 (6.3, 'Down'), (6.8, 'Down'), (7.4, 'Up'), (8.0, 'Down'), (8.6, 'Left'), (9.0, {'call': 'SETTINGSDUMP'}),
                 (9.4, 'Right'), (9.8, {'call': 'SETTINGSDUMP'}), (10.4, 'Escape'),
                 (11.4, 'Down'), (12.0, 'Down'), (12.7, 'Enter'), (13.8, 'Right'),
                 (14.4, 'Left'), (15.2, 'Escape'), (16.2, 'Up'), (17.2, 'Escape'), (18.4, None)],  # bare-menu Esc last: it can stop PIE
    # why Down from Interface volume skips Music/Dialogue: the Slate tree on the Audio page, then focus stepping down
    'audioprobe': [(0.8, {'menu': True}), (2.0, 'Down'), (2.7, 'Enter'), (3.8, 'Down'), (4.4, 'Enter'), (5.4, {'tree': 'audio'}),
                   (6.2, 'Right'), (6.8, 'Down'), (7.4, 'Down'), (8.0, {'tree': 'interface'}), (8.8, 'Down'),
                   (9.6, {'tree': 'after_down'}), (10.4, 'Escape'), (11.4, None)],
    # phone lock screen spec (story script.md section 3): T0 (6:40, early pair), BeatIndex 3 (later pair), BeatIndex 10 with
    # the clock advanced 37 minutes by the proof-only offset (7:17), set before beat 10 raises the phone; the lock shows ~1 s
    'lockproof': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)),
                  (8.5, ('SpaceBar', 1800)), (14.0, {'call': 'PHONEDUMP'}), (16.0, 'P'), (17.0, {'call': 'BEAT', 'n': 3}),
                  (19.5, 'P'), (20.2, {'call': 'PHONEDUMP'}), (22.5, 'P'), (23.5, {'call': 'PHONEMIN', 'n': 37}),
                  (25.0, {'call': 'BEAT', 'n': 10}), (28.2, {'call': 'PHONEDUMP'}), (30.0, None)],  # beat 10 raises the phone itself
    # QA #17: Restart Day from the pause menu (pad: Esc can stop PIE), then the black and the new morning's film with no HUD
    'restartproof': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)),
                     (8.5, ('SpaceBar', 1800)), (14.0, 'Gamepad_Special_Right'), (15.0, 'Gamepad_DPad_Down'),
                     (15.6, 'Gamepad_DPad_Down'), (16.4, 'Gamepad_FaceButton_Bottom'), (17.4, 'Gamepad_DPad_Left'),
                     (18.0, 'Gamepad_FaceButton_Bottom'), (30.0, None)],
    # Today ticks follow the beats (main 2026-11-10): beat 10 (its hook raises the phone), then Today after the lock
    'todayproof': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)),
                   (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False}), (14.0, {'call': 'BEAT', 'n': 10}), (14.1, {'wait': 3.2}),
                   (14.2, {'call': 'PHONEDUMP'}), (14.3, {'wait': 1.0}), (15.0, None)],
    # world 2026-11-10: the held screen and the phone body write stencil 200 (light shafts and the echo skip them)
    'stencilproof': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)),
                     (8.5, ('SpaceBar', 1800)), (13.0, {'ensure_phone': True}), (13.1, {'wait': 2.8}),
                     (13.2, {'call': 'CONSOLE', 'cmd': 'r.BufferVisualizationTarget CustomStencil'}),
                     (13.3, {'call': 'CONSOLE', 'cmd': 'ShowFlag.VisualizeBuffer 1'}), (13.4, {'wait': 2.5}),
                     (13.5, {'call': 'CONSOLE', 'cmd': 'ShowFlag.VisualizeBuffer 0'}), (13.6, {'wait': 1.0}), (14.0, None)],
    # every device on the fast boot: pad, mouse and keyboard on cards, title, menu, settings and the confirm dialog
    'inputfast': [(0.3, {'call': 'CONSOLE', 'cmd': 'au.Debug.SoundWaves 1'}), (0.8, {'unless_menu': 'Gamepad_FaceButton_Bottom'}), (1.3, {'mouse': 'click', 'text': ''}),
                  (1.8, {'unless_menu': 'Enter'}), (2.6, {'unless_menu': 'Gamepad_FaceButton_Bottom'}), (3.2, {'menu': True}),
                  (3.8, 'Gamepad_DPad_Down'), (4.4, 'Gamepad_DPad_Up'),
                  (5.0, {'mouse': 'move', 'text': 'Credits'}), (5.7, 'Down'), (6.4, {'mouse': 'click', 'text': 'Settings'}),
                  (7.6, 'Gamepad_DPad_Down'), (8.2, 'Gamepad_DPad_Right'), (8.8, 'Gamepad_FaceButton_Right'),
                  (9.8, 'Gamepad_DPad_Down'), (10.4, 'Gamepad_DPad_Down'), (11.0, 'Gamepad_FaceButton_Bottom'),
                  (12.0, 'Gamepad_DPad_Right'), (12.6, 'Gamepad_DPad_Left'), (13.2, 'Gamepad_FaceButton_Right'),
                  (14.2, 'Gamepad_FaceButton_Right'), (15.4, 'Gamepad_FaceButton_Bottom'), (17.0, None)],
    # straight to gameplay: skip cards, title, Wake up, the story and the film; then watch the objective form and quiet
    'hud': [(0.8, 'SpaceBar'), (1.3, 'SpaceBar'), (1.8, 'SpaceBar'), (2.6, 'SpaceBar'), (3.6, 'Enter'),
            (5.0, 'SpaceBar'), (6.0, 'SpaceBar'), (7.5, ('SpaceBar', 1800)), (10.5, ('SpaceBar', 1800)),
            (21.0, 'Gamepad_Special_Right'), (22.2, 'Gamepad_DPad_Down'), (22.8, 'Gamepad_DPad_Up'),
            (23.8, 'Gamepad_FaceButton_Bottom'), (25.0, {'call': 'ROLLOVER'}), (31.0, None)],
    # HUD on cue (the objective forms, then quiets after 6 s; a subtitle line rises), then the pause tear and the rollover
    'hudshow': [(0.8, 'SpaceBar'), (1.3, 'SpaceBar'), (1.8, 'SpaceBar'), (2.6, 'SpaceBar'), (3.6, 'Enter'),
                (5.0, 'SpaceBar'), (6.0, 'SpaceBar'), (7.5, ('SpaceBar', 1800)), (10.5, ('SpaceBar', 1800)),
                (14.0, {'call': 'HUDOBJ'}), (21.5, {'call': 'HUDSUB'}), (25.0, 'Gamepad_Special_Right'),
                (27.0, 'Gamepad_FaceButton_Bottom'), (28.5, {'call': 'ROLLOVER'}), (33.0, None)],
    # the phone in first person: lock, list, Mom's message, notes (straight to gameplay first, like 'hud')
    'phone': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)),
              (8.5, ('SpaceBar', 1800)), (14.0, {'ensure_phone': False}), (17.0, {'ensure_phone': True}),
              (17.1, {'wait': 1.6}), (17.2, {'wait': 1.0}),  # the lock (1.0 s), its slide, then Today at rest for a frame
              (20.0, 'Right'), (21.5, 'Enter'), (23.0, 'BackSpace'), (24.0, 'Right'), (25.5, {'ensure_phone': False}), (27.0, None)],
    # item inspect (user ask 2026-11-10): Key by the real Request path, keys/drag rotate, E closes; Screwdriver by pad
    # (D-pad, the right stick flips the hint, B closes); Hanger by right click; a second Key take stays shut (once a
    # morning); while up, P (phone) and the pad pause do nothing
    'inspectproof': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)),
                     (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False}), (14.0, {'call': 'INSPECTREQ', 'cmd': 'Key'}),
                     (14.1, {'wait': 1.2}), (14.2, {'call': 'INSPECTSTATE'}), (14.3, 'Right'), (14.4, {'wait': 0.7}), (14.5, 'Right'),
                     (14.6, {'wait': 0.9}), (14.7, {'call': 'INSPECTSTATE'}), (14.8, {'drag': [40, 12], 'n': 12}), (14.9, {'wait': 0.9}),
                     (15.0, {'call': 'INSPECTSTATE'}), (15.1, 'E'), (15.2, {'wait': 0.8}), (15.3, {'call': 'INSPECTSTATE'}),
                     (15.4, {'call': 'INSPECT', 'cmd': 'Screwdriver'}), (15.5, {'wait': 0.6}), (15.6, 'Gamepad_DPad_Right'),
                     (15.7, {'axis': 'Gamepad_RightX', 'value': 1.0, 'n': 20}), (15.8, {'wait': 0.6}), (15.9, {'call': 'INSPECTSTATE'}),
                     (16.0, 'Gamepad_FaceButton_Right'), (16.1, {'wait': 0.8}), (16.2, {'call': 'INSPECTSTATE'}),
                     (16.3, {'call': 'INSPECT', 'cmd': 'Hanger'}), (16.4, {'wait': 1.0}), (16.5, {'call': 'INSPECTSTATE'}),
                     (16.6, {'click': 'right'}), (16.7, {'wait': 0.8}), (16.8, {'call': 'INSPECTSTATE'}),
                     (16.9, {'call': 'INSPECTREQ', 'cmd': 'Key'}), (17.0, {'wait': 1.0}), (17.1, {'call': 'INSPECTSTATE'}),
                     (17.2, {'call': 'INSPECT', 'cmd': 'Key'}), (17.3, {'wait': 0.6}), (17.4, 'P'), (17.5, 'Gamepad_Special_Right'),
                     (17.6, {'wait': 0.6}), (17.7, {'call': 'PHONESTATE'}), (17.8, {'call': 'INSPECTSTATE'}), (17.9, 'E'),
                     (18.0, {'wait': 0.8}), (18.1, {'call': 'INSPECTSTATE'}), (18.2, None)],
    # main's inspect criteria (2026-11-10), run A: REAL takes through the interactor (SetFocus + Interact, so the montage,
    # CommitInteractionRow and the hook all run): screwdriver (two angles, a drag, E closes; the desk under the crosshair
    # must not get a new interaction), hanger (pad: D-pad turn, Tab must not raise the phone, B closes), Boot_L then the key;
    # the bag after each, once per item
    'inspecttake': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.6, {'call': 'INVDUMP'}), (13.7, {'call': 'TAKE', 'cmd': 'Screwdriver_DeskDrawer'}), (13.8, {'wait': 2.0}),
        (13.9, {'call': 'INSPECTSTATE'}), (14.0, 'Right'), (14.1, {'wait': 0.8}), (14.2, {'call': 'INSPECTSTATE'}),
        (14.3, {'drag': [40, 12], 'n': 12}), (14.4, 'E'), (14.5, {'wait': 1.2}), (14.6, {'call': 'INVDUMP'}),
        (14.7, {'call': 'TAKE', 'cmd': 'Hanger_CoatRail'}), (14.8, {'wait': 2.0}), (14.9, {'call': 'INSPECTSTATE'}),
        (15.0, 'Gamepad_DPad_Right'), (15.1, 'Tab'), (15.2, {'wait': 0.6}), (15.3, {'call': 'PHONESTATE'}), (15.4, {'call': 'INSPECTSTATE'}),
        (15.5, 'Gamepad_FaceButton_Right'), (15.6, {'wait': 1.2}), (15.7, {'call': 'INVDUMP'}),
        (15.8, {'call': 'TAKE', 'cmd': 'Boot_L'}), (15.9, {'wait': 2.5}), (16.0, {'call': 'TAKE', 'cmd': 'Key_Lux3D'}), (16.1, {'wait': 2.0}),
        (16.2, {'call': 'INSPECTSTATE'}), (16.3, 'E'), (16.4, {'wait': 1.5}), (16.5, {'call': 'INVDUMP'}), (16.6, None)],
    # run B: Shirt and KeyStub stay shut; one cinematic line held across SetStoryHUDHidden and a hard camera cut, then a
    # Nightmare line; Esc closes an open inspect without the pause menu (last: an Esc that reaches the viewport can stop PIE)
    'inspectcine': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.6, {'call': 'INSPECTREQ', 'cmd': 'Shirt'}), (13.7, {'wait': 0.8}), (13.8, {'call': 'INSPECTSTATE'}),
        (13.9, {'call': 'INSPECTREQ', 'cmd': 'KeyStub'}), (14.0, {'wait': 0.8}), (14.1, {'call': 'INSPECTSTATE'}),
        (14.2, {'call': 'CINESUB', 'cmd': 'Same room. Same light. Count the steps.', 'n': 0}), (14.3, {'wait': 0.5}),
        (14.4, {'call': 'HUDHIDE', 'n': 1}), (14.5, {'wait': 0.5}), (14.6, {'call': 'CAMCUT'}), (14.7, {'wait': 0.8}),
        (14.8, {'call': 'CINESUB', 'cmd': 'You always come back to this room.', 'n': 2, 'speaker': 'Nightmare'}), (14.9, {'wait': 1.0}),
        (15.0, {'call': 'CAMBACK'}), (15.1, {'call': 'HUDHIDE', 'n': 0}), (15.2, {'call': 'CINEHIDE'}),
        (15.3, {'call': 'INSPECT', 'cmd': 'Key'}), (15.4, {'wait': 0.7}), (15.5, 'Escape'), (15.6, {'wait': 1.0}),
        (15.7, {'call': 'INSPECTSTATE'}), (15.8, None)],
    # main's inspect criteria in ONE PIE session (ue_remote calls take ~5 s each, so states are few and combined)
    'inspectall': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.6, {'call': 'TAKE', 'cmd': 'Screwdriver_DeskDrawer'}), (13.7, {'wait': 1.5}), (13.8, {'call': 'INSPECTSTATE'}),
        (13.9, 'Right'), (14.0, {'wait': 0.9}), (14.1, {'drag': [40, 12], 'n': 12}), (14.2, {'wait': 0.6}), (14.3, {'call': 'INSPECTSTATE'}),
        (14.4, 'E'), (14.5, {'wait': 1.2}), (14.6, {'call': 'INVDUMP'}),
        (14.7, {'call': 'TAKE', 'cmd': 'Hanger_CoatRail'}), (14.8, {'wait': 1.5}), (14.9, 'Gamepad_DPad_Right'), (15.0, 'Tab'),
        (15.1, {'wait': 0.6}), (15.2, {'call': 'INSPECTSTATE'}), (15.3, 'Gamepad_FaceButton_Right'), (15.4, {'wait': 1.0}),
        (15.5, {'call': 'TAKE', 'cmd': 'Boot_L:Use'}), (15.6, {'wait': 2.0}), (15.9, {'call': 'INSPECTSTATE'}),
        (15.91, 'Left'), (15.92, {'wait': 0.9}), (15.93, {'call': 'INSPECTSTATE'}),  # the key at a 2nd angle
        (15.95, 'Gamepad_Special_Right'), (15.97, {'wait': 0.6}), (15.98, {'call': 'INSPECTSTATE'}), (16.0, 'E'), (16.1, {'wait': 1.2}),
        (16.2, {'call': 'INSPECTREQ', 'cmd': 'Shirt'}), (16.3, {'wait': 0.8}), (16.4, {'call': 'INSPECTREQ', 'cmd': 'KeyStub'}),
        (16.5, {'wait': 0.8}), (16.6, {'call': 'INVDUMP'}),
        (16.7, {'call': 'CINESUB', 'cmd': 'Same room. Same light. Count the steps.', 'n': 0}), (16.8, {'wait': 0.8}),
        (16.9, {'call': 'CINECUT'}), (17.0, {'wait': 1.0}),
        (17.1, {'call': 'CINESUB', 'cmd': 'You always come back to this room.', 'n': 2, 'speaker': 'Nightmare'}), (17.2, {'wait': 1.2}),
        (17.3, {'call': 'CINEEND'}), (17.4, {'call': 'INVDUMP'}),
        # QA's A1 lost PIE on a P during inspect ('Repeating last play command'): the same press last, focus logged per key
        (17.5, {'call': 'INSPECT', 'cmd': 'Key'}), (17.6, {'wait': 0.7}), (17.7, 'P'), (17.75, {'wait': 0.8}), (17.8, 'Tab'),
        (17.85, {'wait': 0.8}), (17.87, {'call': 'INSPECTSTATE'}), (17.9, None)],  # Esc on the PIE viewport stops PIE (editor binding)
    # world 2026-11-10: ApplyScreen forces the phone's ScreenLight to the template (2.5 cd, 55 cm, no shadows); the light as
    # BeginPlay left it, then world's drifted values put back and ApplyScreen rerun; the phone raised (no arm blowout)
    'phonelight': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.6, {'call': 'PHONELIGHT', 'cmd': 'old'}), (13.7, {'ensure_phone': True}), (13.8, {'wait': 2.8}),
        (13.9, {'call': 'PHONELIGHT'}), (13.95, {'call': 'BLEND', 'cmd': 'M_PP_FaceBlur:0'}),
        (14.0, {'call': 'FACEVIEW', 'cmd': '163,40,120,-3,35'}), (14.1, {'wait': 0.5}),
        (14.2, {'call': 'PHONELIGHT', 'cmd': 'spec1'}), (14.3, {'wait': 0.5}), (14.4, {'call': 'PHONELIGHT', 'cmd': 'apply'}),
        (14.5, {'call': 'FACEVIEW', 'cmd': '163,0,120,-3,35'}), (14.6, {'wait': 0.5}), (14.7, {'call': 'PHONELIGHT', 'cmd': 'spec1'}),
        (14.8, {'wait': 0.5}), (14.9, {'call': 'PHONELIGHT', 'cmd': 'apply'}), (15.0, {'call': 'CAMBACK'}), (15.1, {'ensure_phone': False}),
        (15.2, None)],  # 3/4 and front: world's FACEVIEW cameras (phonefix_timeline.json), face blur at 0 as world had it
    # the hair fan's source, same 3/4 pose: as shipped (spec 0.2), transmission off, intensity 1 cd, the phone light off
    'hairfan': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.7, {'ensure_phone': True}), (13.8, {'wait': 2.8}), (13.85, {'call': 'PHONELIGHT'}), (13.87, {'call': 'PHONELIGHT', 'cmd': 'off'}),
        (13.9, {'call': 'PHONELIGHT', 'cmd': 'on'}), (13.95, {'call': 'BLEND', 'cmd': 'M_PP_FaceBlur:0'}),
        (14.0, {'call': 'FACEVIEW', 'cmd': '163,40,120,-3,35'}), (14.1, {'wait': 0.4}), (14.2, {'call': 'PHONELIGHT'}),
        (14.3, {'call': 'PHONELIGHT', 'cmd': 'trans0'}), (14.4, {'call': 'PHONELIGHT', 'cmd': 'cd1'}),
        (14.5, {'call': 'PHONELIGHT', 'cmd': 'off'}), (14.6, {'call': 'CAMBACK'}), (14.7, {'ensure_phone': False}), (14.8, None)],
    # main's option B (19:23 build): the emitter 6 cm out of the screen at 1.2 cd; before (the 18:23 build, PIE copy) and after,
    # first-person arm and the same 3/4 pose
    'phoneB': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.7, {'ensure_phone': True}), (13.8, {'wait': 3.0}), (13.85, {'call': 'PHONELIGHT', 'cmd': 'prevB'}), (13.86, {'wait': 0.4}),
        (13.87, {'call': 'PHONELIGHT', 'cmd': 'apply'}), (13.95, {'call': 'BLEND', 'cmd': 'M_PP_FaceBlur:0'}),
        (14.0, {'call': 'FACEVIEW', 'cmd': '163,40,120,-3,35'}), (14.1, {'wait': 0.4}), (14.2, {'call': 'PHONELIGHT', 'cmd': 'prevB'}),
        (14.3, {'wait': 0.4}), (14.4, {'call': 'PHONELIGHT', 'cmd': 'apply'}), (14.6, {'call': 'CAMBACK'}),
        (14.7, {'ensure_phone': False}), (14.8, None)],
    # face's hair fan (hair_sweep3: no hair term fixes it), barn doors and size swept in the same 3/4 pose; 'hide' is
    # the light-off frame the fan count diffs against (Saved/Screenshots stills, in order)
    'phonesweep': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.7, {'ensure_phone': True}), (13.8, {'wait': 3.0}), (13.95, {'call': 'BLEND', 'cmd': 'M_PP_FaceBlur:0'}),
        (14.0, {'call': 'FACEVIEW', 'cmd': '163,40,120,-3,35'}), (14.1, {'wait': 0.5}), (14.15, {'call': 'PHONELIGHT', 'cmd': 'hide'}),
        (round(14.2, 2), {'call': 'PHONELIGHT', 'cmd': 'v:70,20,1.2,6.7,14.9,-7.2'}), (round(14.209999999999999, 2), {'wait': 0.3}), (round(14.25, 2), {'call': 'PHONELIGHT', 'cmd': 'v:60,20,1.2,6.7,14.9,-7.2'}), (round(14.26, 2), {'wait': 0.3}), (round(14.3, 2), {'call': 'PHONELIGHT', 'cmd': 'v:55,20,1.2,6.7,14.9,-7.2'}), (round(14.31, 2), {'wait': 0.3}), (round(14.350000000000001, 2), {'call': 'PHONELIGHT', 'cmd': 'v:60,20,0.6,12,20,-7.2'}), (round(14.360000000000001, 2), {'wait': 0.3}), (round(14.400000000000002, 2), {'call': 'PHONELIGHT', 'cmd': 'v:70,20,0.6,12,20,-1.2'}), (round(14.410000000000002, 2), {'wait': 0.3}), (round(14.450000000000003, 2), {'call': 'PHONELIGHT', 'cmd': 'v:70,20,0.6,12,20,-7.2,20,0'}), (round(14.460000000000003, 2), {'wait': 0.3}), (round(14.500000000000004, 2), {'call': 'PHONELIGHT', 'cmd': 'v:70,20,0.6,12,20,-7.2,-20,0'}), (round(14.510000000000003, 2), {'wait': 0.3}), (round(14.550000000000004, 2), {'call': 'PHONELIGHT', 'cmd': 'v:70,20,0.6,12,20,-7.2,0,20'}), (round(14.560000000000004, 2), {'wait': 0.3}), (round(14.600000000000005, 2), {'call': 'PHONELIGHT', 'cmd': 'v:70,20,0.6,12,20,-7.2,0,-20'}), (round(14.610000000000005, 2), {'wait': 0.3}),
        (16.0, {'call': 'CAMBACK'}), (16.4, {'ensure_phone': False}), (16.5, None)],
    # the mouse path alone: is LMB seen (bDragging) and do mouse axes arrive while it is held
    'dragproof': [(0.8, {'menu': True}), (1.6, 'Enter'), (3.0, 'SpaceBar'), (4.0, 'SpaceBar'), (5.5, ('SpaceBar', 1800)), (8.5, ('SpaceBar', 1800)), (13.5, {'ensure_phone': False})] + [
        (13.6, {'call': 'INSPECT', 'cmd': 'Key'}), (13.7, {'wait': 0.8}), (13.8, {'mouse_btn': 'press'}), (13.9, {'call': 'INSPECTSTATE'}),
        (14.0, {'axis': 'MouseX', 'value': 30.0, 'n': 40}), (14.1, {'call': 'INSPECTSTATE'}), (14.2, {'mouse_btn': 'release'}),
        (14.3, {'call': 'INSPECTSTATE'}), (14.4, 'LeftMouseButton'), (14.5, {'call': 'INSPECTSTATE'}), (14.6, 'E'), (14.7, None)],
    # skip every card with a different device, then the title on the first frame it exists
    'fastskip': [(0.8, 'Gamepad_FaceButton_Bottom'), (1.4, 'SpaceBar'), (2.0, {'mouse': 'click', 'text': ''}),
                 (2.6, 'Enter'), (3.4, 'Down'), (4.0, 'Gamepad_DPad_Up'), (5.0, None)],
    'menu': [(2.6, 'SpaceBar'), (4.2, 'SpaceBar'), (5.8, 'SpaceBar'), (7.4, 'SpaceBar'), (9.4, 'SpaceBar'),
             (12.5, 'Escape'), (14.5, 'Escape'), (16.5, 'Down'), (17.0, 'Enter'), (19.0, 'Escape'), (20.3, 'Down'),
             (20.7, 'Down'), (21.1, 'Down'), (21.6, 'Enter'), (23.0, 'Escape'), (24.3, 'Escape'), (25.3, 'Down'),
             (26.0, None)],
}



MODE = ''


def hold_exclusive():
    """True while this lane really holds EXCLUSIVE (main, 2026-11-09: menufast's keys at 22:31:56-22:32:19 went out
    while the lock read free). renew_all cannot be trusted alone: reply tokens can come back redacted, and the nested
    ue_remote run releases by guessed token, so ask the lease table itself before any input."""
    for lease in (hc.call('lease_status', owner=LANE).get('data') or {}).get('leases', []):
        if lease.get('mine') and any(r.get('resource') == 'global' for r in lease.get('resources', []))                 and (lease.get('expires_in_s') or 0) > 3:
            return True
    return False


def release_exclusive():
    """Release only this sweep's EXCLUSIVE (global) lease by its token. editor_lock.release(LANE) frees EVERYTHING ui
    holds (release_all + forced scan), including another ui run's area leases (editor-rules.md, 2026-11-09)."""
    for token, res in hc.leases_of(LANE):
        if 'global' in [r.lower() for r in res]:
            hc.release(LANE, token)
            editor_lock.forget(LANE, token)


def front_screen():
    """The front end's current screen class (pie_call with no FOA_CALL prints it), inside this sweep's EXCLUSIVE."""
    r = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/pie_call.py'],
                       env=dict(os.environ, FOA_EXCLUSIVE='1', FOA_CALL=''), capture_output=True, text=True, timeout=30)
    return r.stdout


SETTINGS_SAV = 'P:/FoA/Saved/SaveGames/Settings.sav'


def proof_call(name):
    """pie_call PROOFCTX / PROOFRESTORE inside this sweep's EXCLUSIVE (editor-rules: never write the player's FoA.sav)."""
    r = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/pie_call.py', f'FOA_CALL={name}'],
                       env=dict(os.environ, FOA_EXCLUSIVE='1'), capture_output=True, text=True, timeout=30)
    return r.stdout


def active_sounds():
    """Sound-on check: names of the sounds playing right after an input (Hayba audio_active_sounds)."""
    if MODE.startswith('perf'):  # a perf run measures frame times: no extra game-thread probe after each key
        return []
    d = hc.call('audio_active_sounds', {'limit': 32}).get('data') or {}
    names = []
    for snd in d.get('sounds') or []:
        n = snd.get('sound_path') or snd.get('sound') or snd.get('name') or ''
        names.append(str(n).rsplit('.', 1)[-1].rsplit('/', 1)[-1])
    return sorted(set(n for n in names if n))

def regression_steps(out):
    """Bounded, observed-state regression: never send later menu actions into gameplay."""
    deadline = time.monotonic() + 42

    def read():
        try:
            with open(out + '/live_state.json') as fh:
                state = json.load(fh)
            return state if time.time() - state['epoch'] < 2 else {}
        except (OSError, ValueError):
            return {}

    def wait(screen, overlay=None):
        while time.monotonic() < deadline:
            s = read()
            shown = [u[0] for u in s.get('ui', []) if 'COLLAPSED' not in u[1]]
            if s.get('Screen') == screen and (overlay in shown if overlay else shown == [screen]):
                print('observed', screen, overlay, s['t'], flush=True)
                time.sleep(.2)  # the 0.05 s default-focus timer has fired
                return s
            time.sleep(.1)
        raise AssertionError(f'Timed out waiting for {screen}, {overlay}; last state: {read()}')

    wait('WBP_BootSplash_C')
    for key in ('Gamepad_FaceButton_Bottom', 'Enter', 'SpaceBar', 'SpaceBar', 'SpaceBar', 'SpaceBar'):
        if read().get('Screen') != 'WBP_BootSplash_C':
            break
        yield 0, key
        time.sleep(1.8)
    s = read()
    if s.get('Screen') != 'WBP_MainMenu_C':
        wait('WBP_Title_C')
        yield 0, 'SpaceBar'
    wait('WBP_MainMenu_C')
    yield 0, 'Down'
    time.sleep(.4)
    yield 0, 'Enter'
    wait('WBP_MainMenu_C', 'WBP_Settings_C')
    yield 0, 'Escape'
    wait('WBP_MainMenu_C')
    for _ in range(3):
        yield 0, 'Down'
        time.sleep(.35)
    yield 0, 'Enter'
    wait('WBP_MainMenu_C', 'WBP_ConfirmDialog_C')
    yield 0, 'Left'
    time.sleep(.6)
    yield 0, 'Right'
    time.sleep(.6)
    yield 0, 'Gamepad_FaceButton_Right'
    wait('WBP_MainMenu_C')
    yield 0, 'Escape'
    wait('WBP_Title_C')
    yield 0, 'SpaceBar'
    wait('WBP_MainMenu_C')
    yield 0, 'Enter'
    while time.monotonic() < deadline:
        if read().get('bWaking') or read().get('bInGameplay'):
            time.sleep(3)
            yield 0, None
            return
        time.sleep(.1)
    raise AssertionError('Wake up did not change observed state')


def postprocess(out):
    """raw/sNNNNN shots -> frames/fNNNN.png (PIE window frames only, cropped to the viewport) + shots.json times."""
    from PIL import Image
    for f in glob.glob(out + '/frames/f*.png'):
        os.remove(f)
    sj = out + '/shots.json'
    probe = json.load(open(sj)) if os.path.exists(sj) else {}
    wall = probe.get('req_wall') or probe.get('requests', [])
    probe['req_wall'] = wall  # 'requests' is rewritten below with the kept frames' times; keep the originals
    game = probe.get('game_t', [])
    req = game if len(game) >= len(wall) else wall  # PIE real time per request when the recorder logged it
    kept, kept_t, stolen = [], [], 0
    for f in sorted(glob.glob(out + '/raw/s*.bmp') + glob.glob(out + '/raw/s*.png')):
        n = int(os.path.basename(f)[1:6])  # sNNNNN[.bmp], or sNNNNN00000.png from a run before the quoting fix
        im = Image.open(f)
        if im.size == (W + 6, H + 40):  # the PIE window: 3 px frame, 37 px title bar
            im = im.crop((3, 36, 3 + W, 36 + H))
        if im.size != (W, H):
            stolen += 1  # the level editor viewport took this request
        else:
            kept.append(im.convert('RGB')); kept_t.append(req[n] if n < len(req) else None)
        im.close()
        os.remove(f)
    for i, im in enumerate(kept):
        im.save(out + f'/frames/f{i + 1:04d}.png')
    new = sorted(glob.glob(out + '/frames/f*.png'))
    probe['requests'] = kept_t  # analyze_sweep / sweep_strips read frame times from here
    json.dump(probe, open(sj, 'w'))
    span = (kept_t[-1] - kept_t[0]) if len(kept_t) > 1 and kept_t[0] is not None else 1
    real = round((len(kept_t) - 1) / max(0.1, span), 1)
    meta = json.load(open(out + '/keys.json')); meta.update(frames=len(new), fps_measured=real, stolen_by_editor=stolen)
    if probe.get('t0') and game and len(wall) == len(game):  # each key in PIE time: epoch -> recorder wall -> PIE clock
        import numpy as np
        for k in meta['keys']:
            if 'epoch' in k:
                k['pie_t'] = round(float(np.interp(k['epoch'] - probe['t0'], wall, game)), 2)
    json.dump(meta, open(out + '/keys.json', 'w'), indent=1)
    print('kept', len(new), 'PIE frames at', real, 'fps;', stolen, 'requests went to the level editor viewport', flush=True)
    if not new:  # a measuring run takes no shots
        return new
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(real), '-i', out + '/frames/f%04d.png',
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out + '/sweep.mp4'])
    return new


def main(out, mode):
    global MODE
    MODE = mode
    os.makedirs(out + '/frames', exist_ok=True)
    capture_fps = 4 if mode == 'regression' else 30 if mode == 'phone' else FPS  # phone: main's 30 fps raise proof
    while True:
        editor_lock.acquire(LANE, wait_s=1500, ttl=60)  # EXCLUSIVE, inside a PIE window; 60 s cap (main's rule)
        # the previous holder's PIE can still be shutting down: give it 20 s, else let go and take a later window
        for _ in range(20):
            if not (hc.call('editor_get_state', {}).get('data') or {}).get('pie_running'):
                break
            time.sleep(1)
        # editor_lock only grants EXCLUSIVE inside a PIE window; a late grant is still ours (re-queueing lost the turn)
        if not (hc.call('editor_get_state', {}).get('data') or {}).get('pie_running'):
            break
        release_exclusive()
        time.sleep(30)
    keys = []
    p = hc.call('object_get_property', {'path': PLAY})['data']['properties']
    old = (int(p['NewWindowWidth']), int(p['NewWindowHeight']))
    started = False
    settings_backup = None
    failure = None
    try:
        if (hc.call('editor_get_state', {}).get('data') or {}).get('pie_running'):
            print('someone is in PIE (the user?): not starting')
            return
        hc.call('object_set_property', {'path': PLAY, 'properties': {'NewWindowWidth': W, 'NewWindowHeight': H}})
        before = set(glob.glob(SHOTS + '/ScreenShot*.png'))
        r = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/sweep_rec.py',
                            f'UI_OUT={out}', f'UI_STEP={0 if mode.startswith("perf") else 1.0 / capture_fps:.3f}',
                            f'UI_PERF={1 if mode.startswith("perf") else 0}', f'UI_TRACE={os.environ.get("UI_TRACE", "")}'],
                           env=dict(os.environ, FOA_EXCLUSIVE='1'),
                           capture_output=True, text=True, timeout=60)
        print(r.stdout.strip()[-200:], flush=True)
        hc.renew_all(LANE, 60)  # the nested ue_remote run renews the hold to its own default TTL: cap it again
        if not hold_exclusive():
            raise RuntimeError('EXCLUSIVE not held after the recorder run: no PIE, no input')
        settings_backup = open(SETTINGS_SAV, 'rb').read() if os.path.exists(SETTINGS_SAV) else None
        hc.call('editor_start_pie', {})
        started = True
        for _ in range(10):  # the GameInstance exists once the PIE world is up; progress goes to the QA slot before any key
            ctx = proof_call('PROOFCTX')
            if 'proof context' in ctx:
                print(ctx.strip().splitlines()[-1], flush=True)
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('proof progress context not set: no input (the run could write the player save)')
        t0 = time.time()
        rec_t0 = 0.0
        steps = regression_steps(out) if mode == 'regression' else SCRIPTS[mode]
        for at, key in steps:
            if mode == 'regression' and time.time() - t0 > 42:
                raise AssertionError('Regression deadline expired; no further keys will be sent')
            time.sleep(max(0.0, t0 + at - time.time()))
            if key is None:
                break
            hc.renew_all(LANE, 60)  # a stalled editor must not let the EXCLUSIVE lapse mid-run
            if not hold_exclusive():  # input only inside our own EXCLUSIVE (main's rule)
                raise RuntimeError(f'EXCLUSIVE lost at +{time.time() - t0:.1f}s: no more input')
            if not (hc.call('editor_get_state', {}).get('data') or {}).get('pie_running'):
                print('PIE is gone: no more keys, never press into another session', flush=True)
                break
            if isinstance(key, dict) and 'wait' in key:  # a real pause (scheduled times are floors: a slow step runs later)
                time.sleep(key['wait'])
                continue
            if isinstance(key, dict) and 'tree' in key:  # the live Slate tree, for focus and navigation questions
                # filtered per type: an unfiltered tree comes back cut at 50 widgets (the editor's own chrome first)
                json.dump({t: hc.call('editor_pie_widget_tree', {'max_depth': 80, 'filter': t}).get('data') for t in ('SSlider', 'SButton')},
                          open(f"{out}/tree_{key['tree']}.json", 'w'), indent=1)
                print('tree dumped:', key['tree'], flush=True)
                continue
            if isinstance(key, dict) and 'mouse_btn' in key:  # LMB down or up through Slate at the viewport centre (held across steps)
                r = hc.call('editor_pie_mouse', {'action': key['mouse_btn'], 'x': W // 2, 'y': H // 2, 'coordinate_space': 'viewport'})
                keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': json.dumps(key), 'ok': r.get('ok'),
                             'focused': (r.get('data') or {}).get('focused_widget_after'), 'handled_by_ui': None,
                             'err': json.dumps(r.get('data'))[:200], 'sounds': active_sounds()})
                print(keys[-1], flush=True)
                continue
            if isinstance(key, dict) and 'slatedrag' in key:  # the user's gesture: LMB down, the pointer moved, LMB up, through Slate
                dx, dy = key['slatedrag']
                r = hc.call('editor_pie_mouse', {'action': 'drag', 'x': W // 2, 'y': H // 2, 'to_x': W // 2 + dx, 'to_y': H // 2 + dy,
                                                 'steps': key.get('n', 24), 'coordinate_space': 'viewport'})
                keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': json.dumps(key), 'ok': r.get('ok'),
                             'focused': (r.get('data') or {}).get('focused_widget_after'), 'handled_by_ui': None,
                             'err': (r.get('error') or '')[:160], 'sounds': active_sounds()})
                print(keys[-1], flush=True)
                continue
            if isinstance(key, dict) and ('drag' in key or 'axis' in key or 'click' in key):  # held LMB + mouse axes, a stick, a click
                mid = {'x': W // 2, 'y': H // 2, 'coordinate_space': 'viewport'}
                if 'click' in key:
                    r = hc.call('editor_pie_mouse', {'action': 'click', 'button': key['click'], **mid})
                elif 'drag' in key:
                    hc.call('editor_pie_mouse', {'action': 'press', **mid})
                    for _ in range(key.get('n', 10)):
                        hc.call('editor_pie_axis', {'key': 'MouseX', 'value': key['drag'][0]})
                        r = hc.call('editor_pie_axis', {'key': 'MouseY', 'value': key['drag'][1]})
                    hc.call('editor_pie_mouse', {'action': 'release', **mid})
                else:
                    for _ in range(key.get('n', 10)):
                        r = hc.call('editor_pie_axis', {'key': key['axis'], 'value': key['value']})
                keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': json.dumps(key), 'ok': r.get('ok'),
                             'focused': None, 'handled_by_ui': None, 'err': (r.get('error') or '')[:160], 'sounds': active_sounds()})
                print(keys[-1], flush=True)
                continue
            if isinstance(key, dict) and 'menu' in key:  # state gate: SpaceBar only until the main menu is up
                t_in = time.time()
                for _ in range(14):
                    if 'WBP_MainMenu' in front_screen():
                        break
                    r = hc.call('editor_pie_press_key', {'key': 'SpaceBar'})
                    keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': 'SpaceBar (until menu)',
                                 'ok': r.get('ok'), 'focused': (r.get('data') or {}).get('focused_widget'),
                                 'handled_by_ui': (r.get('data') or {}).get('handled_by_ui'), 'err': '', 'sounds': active_sounds()})
                    print(keys[-1], flush=True)
                    time.sleep(0.4)
                else:
                    raise RuntimeError('the main menu never showed')
                t0 += time.time() - t_in  # the later steps keep their spacing from the menu's arrival
                continue
            if isinstance(key, dict) and 'ensure_phone' in key:  # P only when the phone is not already where we want it
                r = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/pie_call.py',
                                    'FOA_CALL=PHONESTATE'], env=dict(os.environ, FOA_EXCLUSIVE='1'), capture_output=True, text=True, timeout=30)
                up = 'phone open True' in r.stdout
                if up == key['ensure_phone']:
                    print('phone already', 'up' if up else 'down', flush=True)
                    continue
                r = hc.call('editor_pie_press_key', {'key': 'P'})
                keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': 'P' if key['ensure_phone'] else 'P (put away)',
                             'ok': r.get('ok'), 'focused': (r.get('data') or {}).get('focused_widget'), 'handled_by_ui': None,
                             'err': '', 'sounds': active_sounds()})
                print(keys[-1], flush=True)
                continue
            if isinstance(key, dict) and 'unless_menu' in key:  # a card-skip press that must never land on the menu
                if 'WBP_MainMenu' in front_screen():
                    print('menu already up: skip', key['unless_menu'], flush=True)
                    continue
                key = key['unless_menu']
            if isinstance(key, dict) and 'call' in key:  # a front-end function through pie_call (inside this EXCLUSIVE)
                r = subprocess.run([sys.executable, 'P:/FoA/Tools/Unreal/ue_remote.py', 'P:/FoA/Tools/Unreal/ui/pie_call.py',
                                    f"FOA_CALL={key['call']}"] + ([f"FOA_CMD={key['cmd']}"] if key.get('cmd') else [])
                                   + ([f"FOA_N={key['n']}"] if 'n' in key else []) + ([f"FOA_SPEAKER={key['speaker']}"] if 'speaker' in key else []),
                                   env=dict(os.environ, FOA_EXCLUSIVE='1'),
                                   capture_output=True, text=True, timeout=30)
                keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': f"call {key['call']}",
                             'ok': r.returncode == 0, 'focused': None, 'handled_by_ui': None,
                             'err': r.stdout.strip()[-160:], 'sounds': active_sounds()})
                hc.renew_all(LANE, 60)
                print(keys[-1], flush=True)
                if key['call'] in ('PHONEDUMP', 'BEAT', 'PHONEMIN', 'SETTINGSDUMP', 'PHONESTATE', 'TAKE', 'INVDUMP', 'PHONELIGHT') or key['call'].startswith(('INSPECT', 'CINE', 'HUDHIDE', 'CAM')):  # the proof's state, in full
                    print(r.stdout.strip()[-1500:], flush=True)
                continue
            if isinstance(key, dict):  # mouse: {'mouse': 'move'|'click', 'text': visible text of the widget to hit}
                tree = (hc.call('editor_pie_widget_tree', {'filter': key['text']}).get('data') or {}).get('widgets') or []
                hit = next((w_ for w_ in tree if key['text'] in (w_.get('text') or '')), tree[0] if tree else None)
                if hit:
                    r = hc.call('editor_pie_mouse', {'action': key['mouse'], 'x': hit['center_x'], 'y': hit['center_y']})
                else:  # keep what Slate did show, to find a better handle than visible text (sand labels)
                    json.dump(hc.call('editor_pie_widget_tree', {'max_depth': 60}).get('data'),
                              open(f"{out}/tree_miss_{key['text']}_{time.time() - t0:.1f}.json", 'w'))
                    r = {'ok': False, 'error': f"no widget with text {key['text']!r}"}
                d = r.get('data') or {}
                keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': f"mouse {key['mouse']} {key['text']}",
                             'ok': r.get('ok'), 'focused': d.get('focused_widget_after'), 'handled_by_ui': None,
                             'err': (r.get('error') or '')[:160], 'sounds': active_sounds()})
                print(keys[-1], flush=True)
                continue
            key, held = key if isinstance(key, tuple) else (key, None)
            r = hc.call('editor_pie_press_key', {'key': key, **({'held_ms': held} if held else {})})
            d = r.get('data') or {}
            keys.append({'t': round(time.time() - t0, 2), 'epoch': time.time(), 'key': key + (f' held {held} ms' if held else ''), 'ok': r.get('ok'), 'focused': d.get('focused_widget'),
                         'handled_by_ui': d.get('handled_by_ui'), 'err': (r.get('error') or '')[:160],
                         'sounds': active_sounds()})
            print(keys[-1], flush=True)
    except Exception as exc:
        failure = exc
        print('sweep failed:', repr(exc), flush=True)
    finally:
        if started and (hc.call('editor_get_state', {}).get('data') or {}).get('pie_running'):
            print(proof_call('PROOFRESTORE').strip()[-120:], flush=True)
            hc.call('editor_stop_pie', {})
        if started and settings_backup is not None:  # the run's settings presses (left and back) must not leave a trace
            time.sleep(0.5)
            open(SETTINGS_SAV, 'wb').write(settings_backup)
        hc.call('object_set_property', {'path': PLAY, 'properties': {'NewWindowWidth': old[0], 'NewWindowHeight': old[1]}})
        release_exclusive()
        print('PIE finished; editor lease released', flush=True)
    json.dump({'mode': mode, 'record_started_at': round(rec_t0, 2), 'fps': capture_fps, 'keys': keys,
               'error': repr(failure) if failure else None}, open(out + '/keys.json', 'w'), indent=1)
    time.sleep(3.0)  # the last shots land a frame or two after PIE ends
    new = postprocess(out)
    print('frames', len(new), '->', out)
    if failure:
        raise failure


if __name__ == '__main__':
    if sys.argv[2] == 'post':  # redo the frame extraction of a finished run
        print('frames', len(postprocess(sys.argv[1])))
    else:
        main(sys.argv[1], sys.argv[2])
