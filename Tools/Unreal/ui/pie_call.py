"""Calls one function on BP_FoAFrontEnd inside the running PIE world (proof runs of the UI loop).
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/pie_call.py FOA_CALL=WakeUp
FOA_CALL=END stops PIE. Prints the front end's state afterwards."""
import os
import time
import unreal

OWNER_FILE = 'P:/FoA/Saved/Integration/pie_owner.txt'  # who started the current PIE session


def head_px(world):
    """His head on screen (x, y, radius in px) for face's hair-fan disc: the head socket and a point 18 cm above it."""
    try:
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.does_socket_exist('head') and c.get_name() == 'Body')
        h = body.get_socket_location('head') + unreal.Vector(0, 0, 8)
        a = unreal.GameplayStatics.project_world_to_screen(pc, h)
        b = unreal.GameplayStatics.project_world_to_screen(pc, h + unreal.Vector(0, 0, 18))
        return [round(a[1].x), round(a[1].y), round(abs(a[1].y - b[1].y))]
    except Exception:
        return None


def shot(world, call):
    if call in ('TAKE', 'INVDUMP', 'INSPECT', 'INSPECTREQ', 'INSPECTSTATE', 'CINESUB', 'CINECUT', 'CINEEND', 'PHONESTATE', 'PHONELIGHT'):
        unreal.SystemLibrary.execute_console_command(world, 'Shot showui')
        import json
        with open('P:/FoA/Saved/UIShots/aaa/stills.jsonl', 'a', encoding='utf-8') as fh:  # order = Saved/Screenshots order
            fh.write(json.dumps(dict(t=round(time.time(), 2), call=call, cmd=os.environ.get('FOA_CMD', ''), head_px=head_px(world))) + '\n')
        print('still requested', call)


def main():
    call = os.environ.get('FOA_CALL', '')
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    caller = os.environ.get('FOA_CALLER', '')
    if call == 'BEGIN':
        with open(OWNER_FILE, 'w', encoding='utf-8') as fh:
            fh.write(caller)
        les.editor_request_begin_play()
        print('PIE begin requested')
        return
    if call == 'END':
        # A burst that overran must not stop the PIE session the next lane started after it (seen 2026-11-09).
        owner = open(OWNER_FILE, encoding='utf-8').read().strip() if os.path.exists(OWNER_FILE) else ''
        if owner and caller and owner != caller and os.environ.get('FOA_FORCE') != '1':
            print(f'PIE end refused: this PIE was started by {owner}, not {caller} (FOA_FORCE=1 overrides)')
            return
        les.editor_request_end_play()
        print('PIE end requested')
        return
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        print('NO_PIE_WORLD')
        return
    if call in ('PROOFCTX', 'PROOFRESTORE'):  # editor-rules: proof runs never write the player's FoA.sav (as pie_play.py)
        import json
        gi = unreal.GameplayStatics.get_game_instance(world)
        side = 'P:/FoA/Saved/UIShots/aaa/.proof_ctx.json'
        if call == 'PROOFCTX':
            if not os.path.exists(side):  # keep the FIRST context: a rerun inside one PIE must not save the QA slot as his
                json.dump([str(gi.get_editor_property('SaveSlot')), [str(k) for k in gi.get_editor_property('Knowledge')],
                           [str(n) for n in gi.get_editor_property('Notebook')]], open(side, 'w'))
            gi.call_method('SetProofProgressContext', ('FoA_QA_UI', set(), []))
            gi.call_method('ResetProgress')  # deletes only the QA slot: day 18, nothing known
            print('proof context FoA_QA_UI, day', gi.get_editor_property('DayCount'))
        else:
            if os.path.exists(side):
                slot, know, notes = json.load(open(side))
                gi.call_method('SetProofProgressContext', (slot, {unreal.Name(k) for k in know}, [unreal.Text(n) for n in notes]))
                gi.call_method('LoadProgress')
                os.remove(side)
            unreal.GameplayStatics.delete_game_in_slot('FoA_QA_UI', 0)
            print('proof context restored to', gi.get_editor_property('SaveSlot'))
        return
    if call == 'CONSOLE':  # one console command in the PIE world (the input sweep's on-screen sound list)
        unreal.SystemLibrary.execute_console_command(world, os.environ.get('FOA_CMD', ''))
        print('PIE console', os.environ.get('FOA_CMD', ''))
        return
    if call == 'LIT':  # the user's editor viewport may be in Shader Complexity; fix the PIE view only
        unreal.SystemLibrary.execute_console_command(world, 'viewmode lit')
        print('PIE viewmode lit')
        return
    if call == 'BEAT':  # lock-screen proof: the director's real EnterBeat(FOA_N) (beat hooks run; BeatIndex is not editable)
        d = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
        d.call_method('EnterBeat', (int(os.environ.get('FOA_N', '0')),))
        print('BeatIndex', d.get_editor_property('BeatIndex'))
        return
    if call == 'SETTINGSDUMP':  # the SAVED settings (slot 'Settings'), to prove a row change reached the save
        sg = unreal.GameplayStatics.load_game_from_slot('Settings', 0)
        print('saved settings', {k: round(sg.get_editor_property(k), 3) for k in ('MusicVolume', 'DialogueVolume')} if sg else None)
        return
    if call == 'PHONELIGHT':  # every phone's ScreenLight; FOA_CMD=old first puts world's drifted values back, then reruns ApplyScreen
        for ph in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C')):
            lt = next(c for c in ph.get_components_by_class(unreal.RectLightComponent))
            read = lambda: {k: str(lt.get_editor_property(k)) for k in ('intensity_units', 'intensity', 'attenuation_radius', 'cast_shadows',  # noqa: E731
                                                                         'barn_door_angle', 'barn_door_length', 'source_width', 'source_height',
                                                                         'specular_scale')}
            if os.environ.get('FOA_CMD') == 'spec1':  # the hair-fan BEFORE: full specular, everything else as ApplyScreen left it
                lt.set_specular_scale(1.0)
                print('phone light', ph.get_actor_label(), 'specular 1.0 (before)', read())
                continue
            if os.environ.get('FOA_CMD', '').startswith('v:'):  # a variant on the PIE copy: v:barn_angle,barn_len,cd,width,height,z
                vals = [float(v) for v in os.environ['FOA_CMD'][2:].split(',')]
                ba, bl, cd, sw, sh, z = vals[:6]
                tp, tr = (vals[6:8] + [0.0, 0.0])[:2]  # optional tilt of the emitter: pitch and roll offsets from straight out
                lt.set_editor_property('relative_rotation', unreal.Rotator(roll=tr, pitch=-90.0 + tp, yaw=0.0))
                lt.set_visibility(True)
                lt.set_barn_door_angle(ba)
                lt.set_barn_door_length(bl)
                lt.set_intensity(cd)
                lt.set_source_width(sw)
                lt.set_source_height(sh)
                lt.set_editor_property('relative_location', unreal.Vector(0.0, 0.0, z))
                print('phone light', ph.get_actor_label(), os.environ['FOA_CMD'], read(), 'z', lt.get_editor_property('relative_location').z)
                continue
            if os.environ.get('FOA_CMD') == 'hide':  # the light's own contribution: the same frame without it
                lt.set_visibility(False)
                print('phone light', ph.get_actor_label(), 'hidden')
                continue
            if os.environ.get('FOA_CMD') == 'prevB':  # the 18:23 build: 2.5 cd at the screen (Z -1.2), for the before frame
                lt.set_intensity(2.5)
                lt.set_editor_property('relative_location', unreal.Vector(0.0, 0.0, -1.2))
                print('phone light', ph.get_actor_label(), 'previous build', read(), 'z', lt.get_editor_property('relative_location').z)
                continue
            if os.environ.get('FOA_CMD') in ('trans0', 'trans1', 'off', 'on', 'cd1'):  # what lights the hair fan (PIE copy only)
                c = os.environ.get('FOA_CMD')
                if c.startswith('trans'):
                    lt.set_transmission(c == 'trans1')
                else:
                    lt.set_intensity({'off': 0.0, 'on': 2.5, 'cd1': 1.0}[c])
                print('phone light', ph.get_actor_label(), c, read(), 'transmission', lt.get_editor_property('transmission'))
                continue
            if os.environ.get('FOA_CMD') == 'apply':
                ph.call_method('ApplyScreen')
                print('phone light', ph.get_actor_label(), 'after ApplyScreen', read(), 'z', lt.get_editor_property('relative_location').z)
                continue
            print('phone light', ph.get_actor_label(), 'at BeginPlay', read())
            if os.environ.get('FOA_CMD') == 'old':
                lt.set_intensity_units(unreal.LightUnits.UNITLESS)
                lt.set_intensity(5000.0)
                lt.set_attenuation_radius(1000.0)
                lt.set_cast_shadows(True)
                lt.set_barn_door_angle(88.0)
                print('phone light', ph.get_actor_label(), 'set old', read())
                ph.call_method('ApplyScreen')
                print('phone light', ph.get_actor_label(), 'after ApplyScreen', read())
        return
    if call == 'FACEVIEW':  # world's perf_driver FACEVIEW (same poses as its A/B): FOA_CMD = yaw,yaw_off,dist,pitch,fov; pawn frozen
        import math
        yaw0, yoff, dist, pitch, fov = (float(v) for v in os.environ.get('FOA_CMD', '').split(','))
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw0), True)
        pawn.set_editor_property('custom_time_dilation', 0.0, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.does_socket_exist('head') and c.get_name() == 'Body')
        look = body.get_socket_location('head') + unreal.Vector(0, 0, 8)
        yaw, pr = math.radians(yaw0 + yoff), math.radians(-pitch)
        loc = look + unreal.Vector(math.cos(yaw) * math.cos(pr), math.sin(yaw) * math.cos(pr), math.sin(pr)) * dist
        cam = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor) if a.get_actor_label() == 'Shot_TopDown')
        cam.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, look), False, True)
        cam.camera_component.set_field_of_view(fov)
        unreal.GameplayStatics.get_player_controller(world, 0).set_view_target_with_blend(cam, 0.0)
        print('faceview', os.environ.get('FOA_CMD'), 'camera', [round(v, 1) for v in loc.to_tuple()], 'head', [round(v, 1) for v in look.to_tuple()])
        return
    if call == 'BLEND':  # world's perf_driver BLEND, PIE copy only: FOA_CMD = <blendable name>:<weight> on PP_DreamMono
        name, wt = os.environ.get('FOA_CMD', '').split(':')
        vol = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume) if a.get_actor_label() == 'PP_DreamMono')
        st = vol.get_editor_property('settings')
        wb = st.get_editor_property('weighted_blendables')
        arr = list(wb.get_editor_property('array'))
        hit = [b.set_editor_property('weight', float(wt)) or name for b in arr
               if b.get_editor_property('object') and b.get_editor_property('object').get_name() == name]
        wb.set_editor_property('array', arr)
        st.set_editor_property('weighted_blendables', wb)
        vol.set_editor_property('settings', st)
        print('blend', name, wt, 'hit', hit)
        return
    if call == 'CAMFACE':  # FOA_CMD = azimuth,distance,height: a camera on his head from the front (0) or 3/4 (35), looking at it
        az, dist, dz = (float(v) for v in os.environ.get('FOA_CMD', '').split(','))
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        mesh = next(m for m in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if m.does_socket_exist('head'))
        head = mesh.get_socket_location('head')
        yaw = pawn.get_actor_rotation().yaw + az
        fwd = unreal.MathLibrary.get_forward_vector(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        at = unreal.Vector(head.x + fwd.x * dist, head.y + fwd.y * dist, head.z + dz)
        look = unreal.MathLibrary.find_look_at_rotation(at, head)
        os.environ['FOA_CMD'] = f'{at.x},{at.y},{at.z},{look.pitch},{look.yaw}'
        call = 'CAMAT'
    if call == 'CAMAT':  # world's same-pose cameras: FOA_CMD = x,y,z,pitch,yaw (a hard cut to the menu camera moved there)
        x, y, z, pitch, yaw = (float(v) for v in os.environ.get('FOA_CMD', '').split(','))
        fe = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
        cam = fe.get_editor_property('MenuCamera')
        cam.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False, True)
        unreal.GameplayStatics.get_player_controller(world, 0).set_view_target_with_blend(cam, 0.0)
        print('camera at', os.environ.get('FOA_CMD'))
        return
    if call == 'PHONESTATE':  # is the phone up (the sweep's ensure_phone step presses P only when it must)
        phones = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
        print('phone open', any(ph.get_editor_property('bOpen') for ph in phones))
        return
    if call in ('PHONEMIN', 'PHONEDUMP'):  # proof-only clock offset (FOA_N minutes); every phone's screen state
        phones = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
        for ph in phones:
            w = ph.get_component_by_class(unreal.WidgetComponent).get_user_widget_object()
            if call == 'PHONEMIN':
                w.call_method('SetClockDebugMinutes', (float(os.environ.get('FOA_N', '0')),))
            txt = lambda n: str(w.get_editor_property(n).get_text()) if w.get_editor_property(n) else None  # noqa: E731
            lock = w.get_editor_property('Ovl_Lock')
            print('phone', ph.get_actor_label(), 'hidden', ph.is_hidden_ed() if hasattr(ph, 'is_hidden_ed') else ph.get_editor_property('hidden'),
                  'parent', ph.get_attach_parent_actor().get_actor_label() if ph.get_attach_parent_actor() else None,
                  '| page', w.get_editor_property('CurrentPage'), 'LockT', round(w.get_editor_property('LockT'), 2),
                  'lock opacity', round(lock.get_render_opacity(), 2) if lock else None,
                  '| clock', txt('Txt_Clock'), txt('Txt_StatusTime'), 'debug min', w.get_editor_property('ClockDebugMin'),
                  '| notif', txt('Txt_Notif0Head'), '/', txt('Txt_Notif0Body'), '|', txt('Txt_Notif1Head'), '/', txt('Txt_Notif1Body'),
                  '| inbox', repr(txt('Txt_Sender0')), repr(txt('Txt_Sender1')), '| ticked', list(w.get_editor_property('TaskTicked')),
                  '| checks filled', [round(w.get_editor_property(f'Img_Check{i}').get_editor_property('brush').tint_color.specified_color.a, 2) for i in range(4)])
        return
    if call in ('TAKE', 'INVDUMP'):  # a real take: the interactor's own SetFocus + Interact on a level actor (FOA_CMD = its label)
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        ix = pawn.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
        inv = ix.get_editor_property('Inventory')
        ias = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))
        if call == 'TAKE':  # FOA_CMD = label[:verb]; the row's own pipeline (BeginPendingRow: montage, contact, commit, hook),
            # past CanInteract: before he is dressed every take is blocked (IsDressingBlocked), which a proof cannot wait for
            label, _, verb = os.environ.get('FOA_CMD', '').partition(':')
            target = next(a for a in ias if a.get_actor_label() == label)
            ix.call_method('SetFocus', (target,))
            found, row = target.call_method('FindRow', (unreal.Name(verb or 'Take'), unreal.Name('None')))
            print('take', label, verb or 'Take', 'row found', found)
            if found:
                target.call_method('BeginPendingRow', (row,))
        print('bag', [str(i) for i in inv.get_editor_property('Items')], '| target', ix.get_editor_property('Target').get_actor_label() if ix.get_editor_property('Target') else None,
              '| states', {a.get_actor_label(): (str(a.get_editor_property('State')), a.get_editor_property('bPendingRow')) for a in ias
                           if a.get_actor_label() in ('Boot_L', 'Key_Lux3D', 'Screwdriver_DeskDrawer', 'Hanger_CoatRail', 'Desk', 'Shirt_T7', 'Door_Bedroom', 'Bed')},
              '| paused', unreal.GameplayStatics.is_game_paused(world))
        return
    if call in ('CINESUB', 'CINEHIDE', 'HUDHIDE', 'CAMCUT', 'CAMBACK', 'CINECUT', 'CINEEND'):  # cinematic subtitle proof (story's battle intro path)
        fe = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
        d = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        if call == 'CINESUB':
            fe.call_method('ShowCinematicSubtitle', (unreal.Text(os.environ.get('FOA_CMD', '')), float(os.environ.get('FOA_N', '0')),
                                                     unreal.Name(os.environ.get('FOA_SPEAKER', 'Him'))))
        elif call == 'CINEHIDE':
            fe.call_method('HideCinematicSubtitle')
        elif call == 'HUDHIDE':
            d.call_method('SetStoryHUDHidden', (os.environ.get('FOA_N', '1') == '1',))
        elif call == 'CAMCUT':  # a hard cut to the front end's menu camera
            pc.set_view_target_with_blend(fe.get_editor_property('MenuCamera'), 0.0)
        elif call == 'CINECUT':  # the story HUD hides and the camera cuts while the line is up
            d.call_method('SetStoryHUDHidden', (True,))
            pc.set_view_target_with_blend(fe.get_editor_property('MenuCamera'), 0.0)
        elif call == 'CINEEND':
            pc.set_view_target_with_blend(unreal.GameplayStatics.get_player_pawn(world, 0), 0.0)
            d.call_method('SetStoryHUDHidden', (False,))
            fe.call_method('HideCinematicSubtitle')
        else:
            pc.set_view_target_with_blend(unreal.GameplayStatics.get_player_pawn(world, 0), 0.0)
        sub, hud = fe.get_editor_property('CineSub'), fe.get_editor_property('HUD')
        line = sub.get_editor_property('Txt_Line') if sub else None
        print('cine', call, '| line', repr(str(line.get_text())) if line else None,
              'visible', str(sub.get_editor_property('Brd_Line').get_visibility()) if sub else None,
              'in viewport', sub.is_in_viewport() if sub else None, '| HUD', str(hud.get_visibility()) if hud else None,
              '| view target', pc.get_view_target().get_name() if pc.get_view_target() else None)
        return
    if call in ('INSPECT', 'INSPECTREQ', 'INSPECTSTATE'):  # item inspect proof: Open (FOA_CMD = DT_Items row), Request, state
        icls = unreal.load_class(None, '/Game/FoA/UI/Game/BP_ItemInspect.BP_ItemInspect_C')
        ins = unreal.GameplayStatics.get_actor_of_class(world, icls)
        if not ins and call != 'INSPECTSTATE':  # the library's own find-or-spawn ('Shirt' is skipped, so nothing opens)
            lib = unreal.get_default_object(unreal.load_class(None, '/Game/FoA/UI/Game/BPFL_ItemInspect.BPFL_ItemInspect_C'))
            lib.call_method('RequestInspect', (unreal.GameplayStatics.get_player_pawn(world, 0), unreal.Name('Shirt')))
            ins = unreal.GameplayStatics.get_actor_of_class(world, icls)
        if not ins:
            print('inspect: no actor')
            return
        if call == 'INSPECT':
            ins.call_method('Open', (unreal.Name(os.environ.get('FOA_CMD', 'Key')),))
        elif call == 'INSPECTREQ':
            ins.call_method('Request', (unreal.Name(os.environ.get('FOA_CMD', 'Key')),))
        w = ins.get_editor_property('Widget')
        txt = lambda n: str(w.get_editor_property(n).get_text()) if w else None  # noqa: E731
        mesh = ins.get_editor_property('ItemMesh')
        cam = unreal.GameplayStatics.get_player_camera_manager(world, 0)
        fe_ = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
        hud_ = fe_.get_editor_property('HUD') if fe_ else None
        print('inspect geometry | root', ins.root_component.get_name(), '| mesh from camera (cm)',
              round((mesh.get_world_location() - cam.get_camera_location()).length(), 1), '| mesh visible', mesh.is_visible(),
              '| HUD opacity', round(hud_.get_render_opacity(), 2) if hud_ else None)
        print('inspect', call, os.environ.get('FOA_CMD', ''), '| open', ins.get_editor_property('bOpen'), 'closing', ins.get_editor_property('bClosing'),
              '| yaw', round(ins.get_editor_property('Yaw'), 1), 'pitch', round(ins.get_editor_property('Pitch'), 1),
              'scale', round(ins.get_editor_property('Scale'), 3), 'T', round(ins.get_editor_property('T'), 2),
              '| mesh', mesh.static_mesh.get_name() if mesh.static_mesh else None, 'pp', round(ins.get_editor_property('PP').blend_weight, 2),
              '| paused', unreal.GameplayStatics.is_game_paused(world), 'pad', ins.get_editor_property('bPad'),
              '| text', repr(txt('Txt_ItemName')), repr(txt('Txt_ItemLine')), repr(txt('Txt_Hint')),
              '| widget in viewport', w.is_in_viewport() if w else None, '| seen', repr(ins.get_editor_property('Seen')),
              '| input: dragging', ins.get_editor_property('bDragging'), 'mouseX', round(ins.get_editor_property('AxisMouseX'), 2),
              'stickX', round(ins.get_editor_property('AxisStickX'), 2), 'velYaw', round(ins.get_editor_property('VelYaw'), 1),
              'mesh rel yaw', round(ins.get_editor_property('ItemMesh').get_editor_property('relative_rotation').yaw, 1),
              '| phone open', any(ph.get_editor_property('bOpen') for ph in unreal.GameplayStatics.get_all_actors_of_class(
                  world, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))),
              '| pause menu', (lambda fe: fe and fe.get_editor_property('PauseMenu') and fe.get_editor_property('PauseMenu').is_in_viewport())(
                  unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))))
        return
    cls = unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
    fe = unreal.GameplayStatics.get_actor_of_class(world, cls)
    if not fe:
        print('NO_FRONT_END')
        return
    if call in ('HUDOBJ', 'HUDSUB'):  # HUD proof: the objective forms and quiets, a subtitle line rises in
        hud = fe.get_editor_property('HUD')
        if not hud:
            print('NO_HUD')
            return
        if call == 'HUDOBJ':
            hud.call_method('HandleBeatChanged', (unreal.Name('T1'), unreal.Text('Take a few steps.'), False))
        else:
            hud.call_method('HandleNarration', (unreal.Text('Same ceiling. Same morning. Just get up. One thing at a time.'),))
    elif call == 'ROLLOVER':  # proof of the day rollover card: day 2, one learned line (script.md section 6)
        fe.call_method('PlayDayRollover', (2, unreal.Text("Key's in my left boot. Under the bed.")))
    elif call:
        fe.call_method(call)
    screen = fe.get_editor_property('Screen')
    print('called', call or '-', '| screen', screen.get_class().get_name() if screen else None,
          '| in gameplay', fe.get_editor_property('bInGameplay'), '| paused', unreal.GameplayStatics.is_game_paused(world))

main()
if os.environ.get('FOA_CALL', '') not in ('BEGIN', 'END'):
    _w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if _w:
        shot(_w, os.environ.get('FOA_CALL', ''))
