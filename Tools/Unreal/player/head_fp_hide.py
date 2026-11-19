"""First-person head hide, robust (main 2026-11-09 HIGH: a smeared head covered half the view after ClosePhone; story saw a
headless T8 battle start). Two steps, run in order:
  tags   (editor Python) tag Face, Hair, Eyebrows, FaceDrift and BodyDrift 'FPHide' on BP_FoAPlayer's component templates
         (FaceDrift / BodyDrift are the face lane's SM_SandFaceDrift head copies, which nothing hid in first person).
           python Tools/Unreal/ue_remote.py Tools/Unreal/player/head_fp_hide.py FOA_AREAS=Characters FOA_STEP=tags
  graph  (Hayba) UpdateHeadHidden(), called at the end of UpdateFirstPersonVisibility (every Tick), sets HiddenInGame =
         bCameraClose, written only when bCameraClose changes (so it never fights an effect's own hide), never propagated
         (v1 propagated from the Face and un-hid the FollowCamera's editor proxy mesh in third person: the camera body
         floating round his head in LS_WakeUp), on: the Face, each component attached directly to it, every 'FPHide' component, and every
         component attached to the Body at or above the neck (head, neck_01, neck_02 sockets). HiddenInGame is separate
         from the Visible flag effects drive, so third-person shots keep whatever an effect shows, and a future head copy
         is covered if it is tagged, parented to the Face, or socketed at the head. OnBecomeViewTarget / OnEndViewTarget
         also call UpdateFirstPersonVisibility, so a view-target switch re-evaluates even if the pawn is not ticking.
           $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/head_fp_hide.py graph"""
import os
import sys

TAGGED = ('Face', 'Hair', 'Eyebrows', 'FaceDrift', 'BodyDrift')
step = os.environ.get('FOA_STEP') or (sys.argv[1] if len(sys.argv) > 1 else '')

if step == 'tags':
    import unreal
    bp = unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer')
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    done = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        name = str(lib.get_variable_name(d))
        if name in TAGGED:
            c = lib.get_object_for_blueprint(d, bp)
            tags = [str(t) for t in c.get_editor_property('component_tags')]
            if 'FPHide' not in tags:
                c.set_editor_property('component_tags', [unreal.Name(t) for t in tags + ['FPHide']])
            done.append(name)
    assert sorted(set(done)) == sorted(TAGGED), done
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('HEAD_TAGS', sorted(set(done)))
else:
    sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
    import hayba_call as h  # noqa: E402
    from held_tool_graphs import Batch, inspect, find  # noqa: E402

    P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
    PC = P + '.BP_FoAPlayer_C'
    K = '/Script/Engine.KismetMathLibrary:'
    SC = '/Script/Engine.SceneComponent:'
    assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
    lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=60)
    try:
        r = h.call('blueprint_add_variable', dict(path=P, variable_name='LastHeadHidden', variable_type='bool', default_value='false',
                                                  instance_editable=False, update_existing=True, category='Camera'))
        assert r.get('ok'), r
        if not h.call('blueprint_inspect_graph', dict(path=P, graph_name='UpdateHeadHidden')).get('ok'):
            r = h.call('blueprint_add_function', dict(path=P, function_name='UpdateHeadHidden', inputs=[]))
            assert r.get('ok'), r
        nodes, _ = inspect(P, 'UpdateHeadHidden')
        if not any(n['title'] == 'GetChildrenComponents' and n['node_id'] for n in nodes) or len(nodes) <= 1 or                 sum(1 for n in nodes if n['title'] == 'GetChildrenComponents') < 2:  # v2: rebuild (v1 propagated)
            e = find(nodes, 'UpdateHeadHidden')
            b = Batch(P, 'UpdateHeadHidden')
            old = [n['node_id'] for n in nodes if n['node_id'] != e]
            if old:
                b.ops.append(dict(op='remove', node_ids=old))
            b.get('close', 'bCameraClose', 0, 300)
            b.get('face', 'Face', 0, 450)
            b.fn('hface', SC + 'SetHiddenInGame', 300, 0, bPropagateToChildren='false')
            b.link('face', 'Face', 'hface', 'self'); b.link('close', 'bCameraClose', 'hface', 'NewHidden')
            b.fn('tagged', '/Script/Engine.Actor:GetComponentsByTag', 300, 300, ComponentClass='/Script/Engine.PrimitiveComponent', Tag='FPHide')
            b.node('each1', 'macro', 600, 0, macro_name='ForEachLoop'); b.link('tagged', 'ReturnValue', 'each1', 'Array')
            b.fn('htag', SC + 'SetHiddenInGame', 900, -100, bPropagateToChildren='false')
            b.link('each1', 'Array Element', 'htag', 'self'); b.link('close', 'bCameraClose', 'htag', 'NewHidden')
            b.get('body', 'Body', 600, 450)
            b.fn('kids', SC + 'GetChildrenComponents', 900, 450, bIncludeAllDescendants='false'); b.link('body', 'Body', 'kids', 'self')
            b.node('each2', 'macro', 1200, 200, macro_name='ForEachLoop'); b.link('kids', 'Children', 'each2', 'Array')
            b.fn('sock', SC + 'GetAttachSocketName', 1200, 500); b.link('each2', 'Array Element', 'sock', 'self')
            ors = []
            for i, s in enumerate(('head', 'neck_01', 'neck_02')):
                b.fn('is%d' % i, K + 'EqualEqual_NameName', 1450, 450 + 120 * i, B=s); b.link('sock', 'ReturnValue', 'is%d' % i, 'A')
                ors.append('is%d' % i)
            b.fn('or1', K + 'BooleanOR', 1650, 480); b.link('is0', 'ReturnValue', 'or1', 'A'); b.link('is1', 'ReturnValue', 'or1', 'B')
            b.fn('or2', K + 'BooleanOR', 1800, 520); b.link('or1', 'ReturnValue', 'or2', 'A'); b.link('is2', 'ReturnValue', 'or2', 'B')
            b.node('neck', 'branch', 1500, 200); b.link('or2', 'ReturnValue', 'neck', 'Condition')
            b.fn('hneck', SC + 'SetHiddenInGame', 1800, 200, bPropagateToChildren='false')
            b.link('each2', 'Array Element', 'hneck', 'self'); b.link('close', 'bCameraClose', 'hneck', 'NewHidden')
            b.get('last', 'LastHeadHidden', 0, 600)
            b.fn('same', K + 'EqualEqual_BoolBool', 150, 600); b.link('close', 'bCameraClose', 'same', 'A'); b.link('last', 'LastHeadHidden', 'same', 'B')
            b.node('changed', 'branch', 150, 0); b.link('same', 'ReturnValue', 'changed', 'Condition')
            b.set('mark', 'LastHeadHidden', 2100, 0); b.link('close', 'bCameraClose', 'mark', 'LastHeadHidden')
            b.link(e, 'then', 'changed', 'execute'); b.link('changed', 'else', 'hface', 'execute'); b.link('hface', 'then', 'each1', 'Exec')
            b.link('each2', 'Completed', 'mark', 'execute')
            b.link('each1', 'LoopBody', 'htag', 'execute')
            b.fn('fkids', SC + 'GetChildrenComponents', 1000, 750, bIncludeAllDescendants='false'); b.link('face', 'Face', 'fkids', 'self')
            b.node('each0', 'macro', 1250, 750, macro_name='ForEachLoop'); b.link('fkids', 'Children', 'each0', 'Array')
            b.fn('hkid', SC + 'SetHiddenInGame', 1500, 750, bPropagateToChildren='false')
            b.link('each0', 'Array Element', 'hkid', 'self'); b.link('close', 'bCameraClose', 'hkid', 'NewHidden')
            b.link('each1', 'Completed', 'each0', 'Exec'); b.link('each0', 'LoopBody', 'hkid', 'execute'); b.link('each0', 'Completed', 'each2', 'Exec')
            b.link('each2', 'LoopBody', 'neck', 'execute'); b.link('neck', 'then', 'hneck', 'execute')
            b.comment('First person: nothing of the head renders (Face and its children, FPHide tags, head and neck sockets)',
                      ['close', 'last', 'same', 'changed', 'mark', 'face', 'hface', 'fkids', 'each0', 'hkid', 'tagged', 'each1', 'htag', 'body', 'kids', 'each2', 'sock', 'is0', 'is1', 'is2', 'or1', 'or2',
                       'neck', 'hneck'])
            b.run()
        F = 'UpdateFirstPersonVisibility'
        nodes, edges = inspect(P, F)
        if not any('UpdateHeadHidden' in n['title'] or 'Update Head Hidden' in n['title'] for n in nodes):
            vis = [n['node_id'] for n in nodes if n['title'] == 'SetVisibility']
            last = next(v for v in vis if not any(x['from_node'] == v and x['from_pin'] == 'then' for x in edges))  # the chain's end
            b = Batch(P, F)
            b.fn('head', PC + ':UpdateHeadHidden', 5200, 2400); b.link(last, 'then', 'head', 'execute')
            b.run()
        nodes, edges = inspect(P, 'EventGraph')
        if not any('BecomeViewTarget' in n['title'] or 'Become View Target' in n['title'] for n in nodes):
            b = Batch(P, 'EventGraph')
            for i, ev in enumerate(('K2_OnBecomeViewTarget', 'K2_OnEndViewTarget')):
                b.ops.append(dict(op='add_event', ref='ev%d' % i, event_name=ev, x=0, y=5200 + 250 * i))
                b.fn('fp%d' % i, PC + ':UpdateFirstPersonVisibility', 400, 5200 + 250 * i); b.link('ev%d' % i, 'then', 'fp%d' % i, 'execute')
            b.comment('A view-target switch re-evaluates the first-person head at once', ['ev0', 'ev1', 'fp0', 'fp1'])
            b.run()
    finally:
        h.release('anim', lease)
    print('HEAD_FP_GRAPHS done')
