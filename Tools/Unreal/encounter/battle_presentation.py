"""Targeted battle presentation patch; never rebuilds the encounter's rules or event graph.

Offline: python Tools/Unreal/encounter/battle_presentation.py --selftest
Editor (short separate asset leases): stubs, camera, hooks, boundary, abort_guards; then widget_stubs, reparent, widget.
Compile BP_Encounter after stubs/camera and the final hooks; compile WBP_Encounter after widget_stubs/widget via Hayba.
"""
import math
import os
import sys

# Relative to the existing encounter actor: every camera remains inside the bedroom.
SHOTS = {
    'Intro': ((-475, 80, 180), (-80, 0, 110), 65),
    'PlayerCommand': ((-435, 155, 165), (-10, 0, 90), 60),
    'ResolvePlayerAction': ((-360, 190, 150), (-100, 0, 105), 62),
    'EnemyPhase': ((-360, 125, 150), (-20, 0, 110), 60),
    'Impact': ((-180, 110, 145), (-260, 0, 140), 50),
    'HitGarment': ((-300, 95, 125), (0, 0, 85), 58),
    'Victory': ((-110, 130, 125), (-260, 0, 150), 46),
    'Defeat': ((-120, 90, 175), (-260, 0, 105), 50),
}
PHASE_LINES = {'Intro': 'Getting dressed', 'PlayerCommand': 'Your move',
               'ResolvePlayerAction': 'Your move', 'EnemyPhase': 'Watch the sleeves',
               'Victory': '', 'Defeat': 'Another morning.'}


def selftest():
    assert set(PHASE_LINES) <= set(SHOTS)
    for pos, aim, fov in SHOTS.values():
        assert all(math.isfinite(v) for v in (*pos, *aim, fov))
        assert 40 <= fov <= 75 and pos != aim
        # Encounter_T8 is (-200,-55,0), yaw 180. Room interior excluding its furniture.
        assert -375 < -200 - pos[0] < 375 and -300 < -55 - pos[1] < 300
    assert len(set(SHOTS.values())) == len(SHOTS)
    print('battle presentation selfcheck: eight distinct bounded shots, six readable phases')


def run():
    import unreal
    ns = globals()
    exec(open('P:/FoA/Tools/Unreal/encounter/enc_graph.py', encoding='utf-8').read(), ns)
    BP = f'{ENC}/BP_Encounter'
    WBP = f'{ENC}/WBP_Encounter'
    PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
    TB, W = '/Script/UMG.TextBlock', '/Script/UMG.Widget'
    SB = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C'
    SC = '/Script/Engine.SceneComponent'
    T = BEL.get_basic_type_by_name
    actor = BEL.get_object_reference_type(unreal.Actor)
    phase = os.environ.get('FOA_PHASE', 'stubs')
    target = WBP if phase in ('widget', 'widget_stubs', 'reparent', 'inspect_layout', 'stat_icons') else BP
    bp = unreal.load_asset(target)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)

    def call(g, fn, x, y, **p):
        return fcall(g, self_call(BP, fn), x, y, **p)

    def find(g, text):
        hits = [n for n in g.ed.list_all_nodes() if event_key(text) in event_key(BEL.get_node_title(n).splitlines()[0])]
        assert len(hits) == 1, (text, [BEL.get_node_title(n) for n in hits])
        return hits[0]

    def prepend(g, n):
        e = entry_node(g)
        links = list(PIN.list_connected_pins(BEL.find_then_pin(e)))
        assert len(links) == 1
        PIN.break_pin_links(BEL.find_then_pin(e))
        go(e, n)
        wire(BEL.find_then_pin(n), links[0])

    def before(g, old, n):
        incoming = list(PIN.list_connected_pins(BEL.find_execute_pin(old)))
        assert len(incoming) == 1
        PIN.break_pin_links(BEL.find_execute_pin(old))
        wire(incoming[0], BEL.find_execute_pin(n))
        go(n, old)

    def has(g, text):
        return any(event_key(text) in event_key(BEL.get_node_title(n).splitlines()[0]) for n in g.ed.list_all_nodes())

    if phase == 'stat_icons':
        for stat in ('Composure', 'Resolve'):
            parent = unreal.find_object(None, f'{WBP}.WBP_Encounter:WidgetTree.Row_{stat}')
            children = [parent.get_child_at(i) for i in range(parent.get_children_count())]
            icon = next(c for c in children if c.get_name() == 'Icon_' + stat)
            saved = {}
            for child in children:
                old_slot = child.get_editor_property('slot')
                saved[child.get_name()] = {key: old_slot.get_editor_property(key) for key in
                                          ('padding', 'size', 'horizontal_alignment', 'vertical_alignment')}
            parent.clear_children()
            for child in [icon] + [c for c in children if c != icon]:
                slot = parent.add_child(child)
                for key, value in saved[child.get_name()].items():
                    slot.set_editor_property(key, value)
        print('Authored stat icons lead their labels; sizes set through Hayba properties')

    elif phase == 'inspect_layout':
        for name in ('RootCanvas', 'CommandPanel', 'BattleCommandHost', 'CommandBox', 'ActBox', 'ActButtons', 'CmdButtons',
                     'Btn_Breathe', 'Icon_Composure', 'Row_Composure'):
            obj = unreal.find_object(None, f'{WBP}.WBP_Encounter:WidgetTree.{name}')
            slot = obj.get_editor_property('slot')
            details = {}
            for prop in ('layout_data', 'auto_size', 'padding', 'size', 'horizontal_alignment', 'vertical_alignment'):
                try:
                    details[prop] = str(slot.get_editor_property(prop))
                except Exception:
                    pass
            print('LAYOUT', name, 'parent', obj.get_parent().get_name() if obj.get_parent() else None,
                  'vis', obj.get_visibility(), 'opacity', obj.get_render_opacity(), details)
    elif phase == 'boundary':
        g, e, _ = new_function(BP, 'SetBattlePresentation', [('Enabled', T('bool'))])
        g.at(e, 0, 0)
        probe = g.call('/Script/UMG.Widget:GetVisibility', 0, 1000)
        visibility = PIN.get_pin_type(po(probe))
        g.ed.remove_nodes([probe])
        ensure_vars_nc(BP, [('BattleHUD', BEL.get_object_reference_type(unreal.UserWidget), '', 'Encounter|Presentation', False),
                            ('BattleHUDVisibility', visibility, '', 'Encounter|Presentation', False),
                            ('bBattleHUDCached', T('bool'), 'false', 'Encounter|Presentation', False)])
        pawn = fcall(g, f'{GS}:GetPlayerPawn', 0, 220, PlayerIndex=0)
        cast = make(g, 300, 0, 'CastToBP_FoAPlayer')
        wire(po(pawn), pi(cast, 'Object'))
        battle = fcall(g, f'{PLAYER}:SetBattle', 620, 0, self=as_pin(cast), bEnable=po(e, 'Enabled'))
        component = fcall(g, '/Script/Engine.Actor:GetComponentByClass', 620, 300, self=pawn,
                          ComponentClass='/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C')
        interaction = make(g, 960, 0, 'CastToBPC_Interactor')
        wire(po(component), pi(interaction, 'Object'))
        suspended = fcall(g, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C:SetSuspended', 1280, 0,
                          self=as_pin(interaction), bSuspended=po(e, 'Enabled'))
        br = g.at(g.ed.add_branch_node(), 1620, 0)
        wire(po(e, 'Enabled'), BEL.find_condition_pin(br))
        chain(e, cast, battle, interaction, suspended, br)
        go(interaction, br, 'CastFailed')
        once = g.at(g.ed.add_branch_node(), 1940, -180)
        wire(po(fcall(g, f'{KML}:Not_PreBool', 1700, -430,
                      A=mget(g, 'bBattleHUDCached', 1460, -430))), BEL.find_condition_pin(once))
        go(br, once)
        fe = fcall(g, f'{GS}:GetActorOfClass', 2240, -180,
                   ActorClass='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
        valid_fe = g.at(g.ed.add_branch_node(), 2520, -180)
        wire(po(fcall(g, f'{KSL}:IsValid', 2320, -430, Object=fe)), BEL.find_condition_pin(valid_fe))
        hud = field(g, fe, 'HUD', '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C', 2540, -430)
        valid_hud = g.at(g.ed.add_branch_node(), 2800, -180)
        wire(po(fcall(g, f'{KSL}:IsValid', 2740, -600, Object=hud)), BEL.find_condition_pin(valid_hud))
        cached = mset(g, 'BattleHUD', 3080, -180, hud)
        vis = mset(g, 'BattleHUDVisibility', 3360, -180,
                   fcall(g, '/Script/UMG.Widget:GetVisibility', 3080, -450, self=hud))
        flag = mset(g, 'bBattleHUDCached', 3640, -180, 'true')
        hide = fcall(g, '/Script/UMG.Widget:SetVisibility', 3920, -180, self=hud, InVisibility='Collapsed')
        seq(once, fe, valid_fe)
        chain(valid_fe, valid_hud, cached, vis, flag, hide)
        was_cached = g.at(g.ed.add_branch_node(), 1940, 260)
        wire(po(mget(g, 'bBattleHUDCached', 1680, 500)), BEL.find_condition_pin(was_cached))
        go(br, was_cached, 'else')
        old_hud = mget(g, 'BattleHUD', 2180, 680)
        valid_old = g.at(g.ed.add_branch_node(), 2240, 260)
        wire(po(fcall(g, f'{KSL}:IsValid', 2040, 700, Object=old_hud)), BEL.find_condition_pin(valid_old))
        restore = fcall(g, '/Script/UMG.Widget:SetVisibility', 2580, 140, self=old_hud,
                        InVisibility=mget(g, 'BattleHUDVisibility', 2300, 500))
        uncache = mset(g, 'bBattleHUDCached', 2920, 260, 'false')
        chain(was_cached, valid_old, restore, uncache)
        go(valid_old, uncache, 'else')
        box(g, 'Battle owns the screen', '', g.ed.list_all_nodes(), 'stage')
        print('Battle boundary: suspend interaction, cache HUD visibility once, restore exactly on exit')

    elif phase == 'reparent':
        import json
        moves = json.load(open('P:/FoA/Saved/EncounterCaptures/battle_reparent.json', encoding='utf-8'))
        def widget(name):
            obj = unreal.find_object(None, f'{WBP}.WBP_Encounter:WidgetTree.{name}')
            assert obj, name
            return obj
        for move in moves:
            obj, parent = widget(move['widget']), widget(move['parent'])
            if obj.get_parent() != parent:
                obj.remove_from_parent()
                slot = parent.add_child(obj)
            else:
                slot = obj.get_editor_property('slot')
            assert slot, move
            if 'fill' in move['slot']:
                slot.set_editor_property('size', unreal.SlateChildSize(value=move['slot']['fill'],
                                                                      size_rule=unreal.SlateSizeRule.FILL))
            if 'padding' in move['slot']:
                slot.set_editor_property('padding', unreal.Margin(*move['slot']['padding']))
        for kind in ('Act', 'Breathe', 'Mirror', 'Items', 'Flee', 'Target', 'Composure', 'Resolve'):
            path = f'{ENC}/Icons/T_Battle_{kind}'
            assert unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False), path
        print('reparented existing widget objects', len(moves))

    elif phase == 'widget_stubs':
        ensure_vars_nc(WBP, [('bCommandFocus', T('bool'), 'false', 'Encounter|Presentation', False)])
        stub_functions(WBP, {'RefreshBattlePresentation': ((), (), False)})
        print('widget presentation stub ready')

    elif phase == 'stubs':
        stub_functions(BP, {
            'SetBattleShot': ((('Shot', T('name')),), (), False),
            'RestoreBattleShot': ((), (), False),
            'PresentImpact': ((('Who', actor), ('Amount', T('int'))), (), False),
            'SetBattlePresentation': ((('Enabled', T('bool')),), (), False),
        })
        print('presentation stubs ready')

    elif phase == 'camera':
        g, e, _ = new_function(BP, 'SetBattleShot', [('Shot', T('name'))])
        g.at(e, 0, 0)
        cam = mget(g, 'BattleCam', 0, 300)
        hero = mget(g, 'HeroCam', 0, 440)
        off = fcall(g, '/Script/Engine.ActorComponent:SetActive', 300, 0, self=hero, bNewActive='false')
        on = fcall(g, '/Script/Engine.ActorComponent:SetActive', 600, 0, self=cam, bNewActive='true')
        # Reduce motion keeps the establishing composition instead of making cuts.
        setting = fcall(g, '/Script/Engine.KismetMaterialLibrary:GetScalarParameterValue', -200, 680,
                        Collection='/Game/FoA/PostProcess/MPC_Dream.MPC_Dream', ParameterName='ReduceMotion')
        seq(e, setting, off, on)
        reduce = fcall(g, f'{KML}:Greater_DoubleDouble', 100, 680,
                      A=setting, B=0.5)
        shot = fcall(g, f'{KML}:SelectString', 400, 680, A='Intro',
                     B=fcall(g, '/Script/Engine.KismetStringLibrary:Conv_NameToString', 100, 850, InName=po(e, 'Shot')),
                     bPickA=reduce)
        prev = on
        for i, (name, (loc, aim, fov)) in enumerate(SHOTS.items()):
            x, y = 1000 + i * 660, 0
            br = g.at(g.ed.add_branch_node(), x, y)
            wire(po(fcall(g, '/Script/Engine.KismetStringLibrary:EqualEqual_StrStr', x, 300, A=shot, B=name)),
                 BEL.find_condition_pin(br))
            if i == 0:
                go(prev, br)
            else:
                go(prev, br, 'else')
            delta = [b - a for a, b in zip(loc, aim)]
            rotation = (math.degrees(math.atan2(delta[2], math.hypot(*delta[:2]))),
                        math.degrees(math.atan2(delta[1], delta[0])))
            vec = fcall(g, f'{KML}:MakeVector', x + 140, 420, X=loc[0], Y=loc[1], Z=loc[2])
            rot = fcall(g, f'{KML}:MakeRotator', x + 140, 620, Roll=0, Pitch=rotation[0], Yaw=rotation[1])
            move = fcall(g, f'{SC}:K2_SetRelativeLocationAndRotation', x + 240, -160, self=cam,
                         NewLocation=vec, NewRotation=rot, bTeleport='true')
            zoom = fcall(g, '/Script/Engine.CameraComponent:SetFieldOfView', x + 500, -160, self=cam, InFieldOfView=fov)
            go(br, move)
            go(move, zoom)
            prev = br
        box(g, 'Battle camera grammar', '', g.ed.list_all_nodes(), 'stage')

        g, e, _ = new_function(BP, 'RestoreBattleShot')
        g.at(e, 0, 0)
        active = g.at(g.ed.add_branch_node(), 260, 0)
        wire(po(mget(g, 'bActive', 0, 240)), BEL.find_condition_pin(active))
        shot = call(g, 'SetBattleShot', 560, 0, Shot=mget(g, 'BattleState', 300, 240))
        chain(e, active, shot)
        box(g, 'Return to the turn', '', g.ed.list_all_nodes(), 'stage')

        g, e, _ = new_function(BP, 'PresentImpact', [('Who', actor), ('Amount', T('int'))])
        g.at(e, 0, 0)
        hero = fcall(g, f'{KML}:EqualEqual_ObjectObject', 100, 300, A=po(e, 'Who'),
                     B=fcall(g, f'{GS}:GetPlayerPawn', -200, 440, PlayerIndex=0))
        name = fcall(g, '/Script/Engine.KismetStringLibrary:Conv_StringToName', 400, 300,
                     InString=fcall(g, f'{KML}:SelectString', 100, 580, A='Impact', B='HitGarment', bPickA=hero))
        cut = call(g, 'SetBattleShot', 700, 0, Shot=name)
        timer = fcall(g, f'{KSL}:K2_SetTimer', 1000, 0, FunctionName='RestoreBattleShot', Time=0.42, bLooping='false')
        chain(e, cut, timer)
        box(g, 'Read the impact', '', g.ed.list_all_nodes(), 'stage')

        g, e, _ = new_function(BP, 'CutTo', [('bHero', T('bool'))])
        g.at(e, 0, 0)
        shot = fcall(g, '/Script/Engine.KismetStringLibrary:Conv_StringToName', 280, 300,
                     InString=fcall(g, f'{KML}:SelectString', 0, 440, A='ResolvePlayerAction',
                                   B=fcall(g, '/Script/Engine.KismetStringLibrary:Conv_NameToString', 0, 600,
                                           InName=mget(g, 'BattleState', -220, 600)), bPickA=po(e, 'bHero')))
        cut = call(g, 'SetBattleShot', 600, 0, Shot=shot)
        go(e, cut)
        box(g, 'Cut to the action', '', g.ed.list_all_nodes(), 'stage')

        g, e, _ = new_function(BP, 'SetBattlePresentation', [('Enabled', T('bool'))])
        g.at(e, 0, 0)
        # The character lane owns the animation state and keeps input lock semantics here unchanged.
        assert 'SetBattle' in [str(n) for n in BEL.list_graph_names(unreal.load_asset(PLAYER.split('.')[0]))], 'SetBattle pending'
        pawn = fcall(g, f'{GS}:GetPlayerPawn', 0, 220, PlayerIndex=0)
        cast = make(g, 300, 0, 'CastToBP_FoAPlayer')
        wire(po(pawn), pi(cast, 'Object'))
        battle = fcall(g, f'{PLAYER}:SetBattle', 620, 0, self=as_pin(cast), bEnable=po(e, 'Enabled'))
        chain(e, cast, battle)
        box(g, 'Battle body language', '', g.ed.list_all_nodes(), 'stage')

    elif phase == 'hooks':
        for fn, hook, params in (
                ('SetState', 'SetBattleShot', {}),
                ('ShowEncounter', 'SetBattlePresentation', {'Enabled': 'true'}),
                ('EndEncounter', 'SetBattlePresentation', {'Enabled': 'false'})):
            g = Graph(BP, fn)
            if not has(g, hook):
                args = {'Shot': po(entry_node(g), 'NewState')} if fn == 'SetState' else params
                n = call(g, hook, -500, -300, **args)
                prepend(g, n)
                box(g, 'Battle presentation', '', [n], 'stage')
        for fn in ('ApplyPlayerMove', 'EnemyAct'):
            g = Graph(BP, fn)
            if not has(g, 'PresentImpact'):
                damage = find(g, 'Call On Damage')
                n = call(g, 'PresentImpact', -500, -300)
                for key in ('Who', 'Amount'):
                    sources = list(PIN.list_connected_pins(pi(damage, key)))
                    assert len(sources) == 1
                    wire(sources[0], pi(n, key))
                before(g, damage, n)
                box(g, 'Battle impact', '', [n], 'stage')
        g = Graph(BP, 'EndEncounter')
        old_cancel = find(g, 'Cancel Latent Actions') if has(g, 'Cancel Latent Actions') else None
        if old_cancel is None or not PIN.list_connected_pins(BEL.find_execute_pin(old_cancel)):
            ref = make(g, -1000, 400, 'reference to self')
            cancel = old_cancel or fcall(g, '/Script/UMG.UserWidget:CancelLatentActions', -1000, -600)
            feed(cancel, self=mget(g, 'Widget', -1250, -360))
            prepend(g, cancel)
            following = list(PIN.list_connected_pins(BEL.find_then_pin(cancel)))
            assert len(following) == 1
            PIN.break_pin_links(BEL.find_then_pin(cancel))
            cleanup, prev = [cancel], cancel
            for i, name in enumerate(('AdvancePrompt', 'RestoreBattleShot') + tuple('S_' + s for s in PHASE_LINES)):
                timer = fcall(g, f'{KSL}:K2_ClearTimer', -700 + i * 250, -600, FunctionName=name)
                go(prev, timer)
                cleanup.append(timer)
                prev = timer
            for i, name in enumerate(('TickWindow', 'HideDamage')):
                timer = fcall(g, f'{KSL}:K2_ClearTimer', 1400 + i * 300, -600,
                              Object=mget(g, 'Widget', 1400 + i * 300, -360), FunctionName=name)
                go(prev, timer)
                cleanup.append(timer)
                prev = timer
            style = call(g, 'DreamCycle', 2100, -600, bStart='false')
            go(prev, style)
            wire(BEL.find_then_pin(style), following[0])
            box(g, 'Cancel the unfinished turn', '', cleanup + [style], 'stage')
            g.ed.remove_nodes([n for n in g.ed.list_all_nodes() if 'Self-Reference' in BEL.get_node_title(n)
                               and not any(PIN.list_connected_pins(p) for p in BEL.list_output_pins(n))])
        # Existing hit-stop stays; its old fixed camera reset would overwrite every authored shot.
        g = Graph(BP)
        fixed = [n for n in g.ed.list_all_nodes() if 'Move Component To' in BEL.get_node_title(n)]
        if fixed:
            assert len(fixed) == 2
            first = min(fixed, key=lambda n: BEL.get_node_pos(n).x)
            upstream = list(PIN.list_connected_pins(pi(first, 'Move')))
            assert len(upstream) == 1
            PIN.break_pin_links(pi(first, 'Move'))
            g.ed.remove_nodes(fixed)
        print('presentation hooks preserve rule graphs and input lock paths')

    elif phase == 'finish_interaction':
        g = Graph(BP, 'EndEncounter')
        if not has(g, 'EndInteraction'):
            reset = find(g, 'ResetIgnoreInputFlags')
            incoming = list(PIN.list_connected_pins(BEL.find_execute_pin(reset)))
            assert len(incoming) == 1
            pawn = fcall(g, f'{GS}:GetPlayerPawn', 600, -1700, PlayerIndex=0)
            player = make(g, 900, -1900, 'CastToBP_FoAPlayer')
            wire(po(pawn), pi(player, 'Object'))
            release = fcall(g, f'{PLAYER}:EndInteraction', 1220, -1900, self=as_pin(player))
            PIN.break_pin_links(BEL.find_execute_pin(reset))
            wire(incoming[0], BEL.find_execute_pin(player))
            chain(player, release, reset)
            go(player, reset, 'CastFailed')
            box(g, 'Release the interaction first', '', [pawn, player, release], 'stage')
        print('EndInteraction clears its ownership before controller counters are reset')

    elif phase == 'abort_guards':
        g = Graph(BP)
        added = 0
        for node in list(g.ed.list_all_nodes()):
            title = BEL.get_node_title(node).splitlines()[0]
            custom = isinstance(node, unreal.K2Node_CustomEvent)
            if title != 'Delay' and not custom:
                continue
            if custom and event_name(node) == event_key('Shake'):
                continue
            out = po(node, 'Completed') if title == 'Delay' else BEL.find_then_pin(node)
            targets = list(PIN.list_connected_pins(out))
            if not targets:
                continue
            target_node = PIN.get_owning_node(targets[0])
            # The hit-stop's short delay must still restore normal time after an abort.
            if 'SetGlobalTimeDilation' in BEL.get_node_title(target_node):
                continue
            if isinstance(target_node, unreal.K2Node_IfThenElse):
                conditions = list(PIN.list_connected_pins(BEL.find_condition_pin(target_node)))
                if conditions and event_key(BEL.get_node_title(PIN.get_owning_node(conditions[0]))) == 'getbactive':
                    continue
            x, y = BEL.get_node_pos(node).x, BEL.get_node_pos(node).y
            gate = g.at(g.ed.add_branch_node(), x + 200, y - 240)
            active = mget(g, 'bActive', x - 40, y - 100)
            wire(po(active), BEL.find_condition_pin(gate))
            PIN.break_pin_links(out)
            wire(out, BEL.find_execute_pin(gate))
            for target_pin in targets:
                wire(BEL.find_then_pin(gate), target_pin)
            box(g, 'Continue the encounter', '', [gate, active], 'stage')
            added += 1
        # A reset can interrupt hit-stop. EndEncounter must not leave the whole morning slowed.
        g = Graph(BP, 'EndEncounter')
        if not has(g, 'SetGlobalTimeDilation'):
            normal = fcall(g, f'{GS}:SetGlobalTimeDilation', -1500, -900, TimeDilation=1.0)
            prepend(g, normal)
            box(g, 'Restore real time', '', [normal], 'stage')
        print('active guards after delayed callbacks and on custom events', added)

    elif phase == 'widget':
        ensure_vars_nc(WBP, [('bCommandFocus', T('bool'), 'false', 'Encounter|Presentation', False)])
        g, e, _ = new_function(WBP, 'RefreshBattlePresentation')
        g.at(e, 0, 0)
        E = mget(g, 'Encounter', 0, 300)
        bc = f'{ENC}/BP_Encounter.BP_Encounter_C'
        state = field(g, E, 'BattleState', bc, 220, 300)
        line = 'Getting dressed'
        for i, (name, label) in enumerate(PHASE_LINES.items()):
            line = fcall(g, f'{KML}:SelectString', 500 + i * 230, 460, A=label, B=line,
                         bPickA=fcall(g, f'{KML}:EqualEqual_NameName', 500 + i * 230, 720, A=state, B=name))
        st = fcall(g, f'{TB}:SetText', 2000, 0, self=mget(g, 'Txt_BattleHelp', 1760, 220),
                   InText=fcall(g, '/Script/Engine.KismetTextLibrary:Conv_StringToText', 1760, 460, InString=line))
        turn = field(g, E, 'bPlayerTurn', bc, 2050, 460)
        br = g.at(g.ed.add_branch_node(), 2350, 0)
        wire(po(turn), BEL.find_condition_pin(br))
        panel = mget(g, 'CommandPanel', 2320, 580)
        on = fcall(g, f'{W}:SetVisibility', 2650, -140, self=panel, InVisibility='Visible')
        # Keep the command vocabulary readable during enemy turns; the existing buttons disable actions.
        off = fcall(g, f'{W}:SetVisibility', 2650, 160, self=panel, InVisibility='Visible')
        no = mset(g, 'bCommandFocus', 2960, 160, 'false')
        first = g.at(g.ed.add_branch_node(), 2960, -140)
        wire(po(fcall(g, f'{KML}:Not_PreBool', 2760, -380, A=mget(g, 'bCommandFocus', 2500, -380))),
             BEL.find_condition_pin(first))
        mark = mset(g, 'bCommandFocus', 3260, -140, 'true')
        chain(e, st)
        last = st
        for i, (button, label) in enumerate((('Btn_Breathe', 'Deep breath'), ('Btn_Mirror', 'Check mirror (5 Resolve)'),
                                             ('Btn_Items', 'Items'), ('Btn_Flee', 'Try to leave'),
                                             ('Btn_NextTarget', 'Change target'))):
            value = label
            if button == 'Btn_Mirror':
                move = field(g, E, 'MirrorMove', bc, 2180, -1200)
                value = po(fcall(g, self_call(WBP, 'MoveLabel'), 2500, -1200, Move=move), 'Label')
            label_node = fcall(g, f'{SB}:SetLabel', 2100 + i * 280, -700, self=mget(g, button, 2050 + i * 280, -480),
                               NewLabel=value)
            go(last, label_node)
            last = label_node
        go(last, br)
        go(br, on)
        go(br, off, 'else')
        go(off, no)
        chain(on, first, mark)
        prev = mark
        for i, btn in enumerate(('Btn_Act0', 'Btn_Act1', 'Btn_Breathe', 'Btn_Mirror', 'Btn_Items')):
            x = 3540 + i * 500
            b = mget(g, btn, x, 300)
            enabled = g.at(g.ed.add_branch_node(), x, -140)
            wire(po(fcall(g, f'{W}:GetIsEnabled', x, 480, self=b)), BEL.find_condition_pin(enabled))
            focus = fcall(g, f'{SB}:FocusButton', x + 220, -340, self=b)
            go(prev, enabled, None if i == 0 else 'else')
            go(enabled, focus)
            prev = enabled
        box(g, 'Readable turn and focus', '', g.ed.list_all_nodes(), 'stage')
        g = Graph(WBP, 'RedrawAll')
        if not has(g, 'RefreshBattlePresentation'):
            tail = find(g, 'Refresh Prompt')
            n = fcall(g, self_call(WBP, 'RefreshBattlePresentation'), 1600, 0)
            go(tail, n)
            box(g, 'Turn presentation', '', [n], 'stage')
        # Preserve every row's indexing and references; stop dimming non-target intent below readable contrast.
        g = Graph(WBP, 'RefreshRow')
        focus = find(g, 'Select Float')
        val(focus, 'B', 0.82)
        print('widget presentation ready')
    else:
        raise AssertionError(phase)

    assert unreal.EditorAssetLibrary.save_asset(target, only_if_is_dirty=False), target
    print('battle presentation', phase, 'saved; compile through Hayba')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        run()
