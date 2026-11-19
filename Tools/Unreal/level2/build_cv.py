"""Add the L2 page context to the existing encounter. One phase per editor lease.

Offline imports are safe. Native phases use Hayba; `rows` runs via ue_remote inside a lease.
Order: rows, skeleton, start, context, sync, abort, finish, fold, assisted, detail, patches,
widget_members, widget.
Never rerun the L1 encounter builder.
StartLevel2CV(Journey, Assisted) is the only L2 entry point. Journey must be compiled first.
"""
import os
from pathlib import Path
import sys

sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal']
import build_drive as b
import cv_data as D
from held_tool_graphs import Batch, inspect

ENCOUNTER = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
GARMENT = '/Game/FoA/Gameplay/Encounter/BP_Garment'
WIDGET = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
JOURNEY = '/Game/FoA/Level2/Journey/BP_L2Journey'
MOVE = '/Game/FoA/Gameplay/Encounter/PDA_Move'
OPPONENT = '/Game/FoA/Gameplay/Encounter/PDA_Opponent'
EC, GC, WC, JC, MC = map(b.cls, (ENCOUNTER, GARMENT, WIDGET, JOURNEY, MOVE))
K, GS, SL = b.K, b.GS, b.SL
ARRAY = '/Script/Engine.KismetArrayLibrary:'
TEXT = '/Script/Engine.KismetTextLibrary:'
STRING = '/Script/Engine.KismetStringLibrary:'
TB = '/Script/UMG.TextBlock:'


def norm(title):
    return title.split('\n')[0].replace(' ', '').lower()


def asset(name, prefix='Move'):
    path = D.DATA + '/DA_' + prefix + '_' + name
    return path + '.' + path.rsplit('/', 1)[-1]


def compact_refs(graph):
    """Keep generated aliases short; native batches reject some long human-readable names."""
    refs={o['ref']:'cv'+str(i) for i,o in enumerate(o for o in graph.ops if 'ref' in o)}
    for op in graph.ops:
        for key in ('ref','node_id','from_node','to_node'):
            if key in op:op[key]=refs.get(op[key],op[key])
        if 'node_ids' in op:op['node_ids']=[refs.get(n,n) for n in op['node_ids']]


def rows():
    # ue_remote reuses the interpreter; take current authored tuning on repeat runs.
    import importlib
    importlib.reload(D)
    import unreal
    eal = unreal.EditorAssetLibrary
    def make(name, cls):
        path = D.DATA + '/' + name
        if eal.does_asset_exist(path):
            return unreal.load_asset(path)
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.load_class(None, b.cls(cls)))
        result = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, D.DATA, None, factory)
        assert result, path
        return result
    moves = {name:make('DA_Move_' + name, MOVE) for name in D.MOVES}
    for name, fields in D.MOVES.items():
        for key, value in fields.items():
            if key == 'Owner':
                key, value = 'bOpponentMove', value == 'Opponent'
            if key in ('DisplayName', 'Narration', 'TelegraphLine'):
                value = unreal.Text(value)
            moves[name].set_editor_property(key, value)
        assert eal.save_loaded_asset(moves[name], False)
    opponents = {name:make('DA_Opponent_' + name, OPPONENT) for name in D.OPPONENTS}
    for name, fields in D.OPPONENTS.items():
        row = opponents[name]
        for key, value in fields.items():
            if key in ('DisplayName', 'IntroLine', 'WinLine', 'LoseLine', 'VictoryLine'):
                value = unreal.Text(value)
            elif key == 'ActMoves': value = [moves[x] for x in value]
            elif key == 'OpeningMove': value = moves[value]
            elif key == 'Party': value = [opponents[x] for x in value]
            elif key == 'MoveWeights':
                for col, field in enumerate(('PoolPlausible','PoolSuspicious','PoolOpen','PoolEnraged')):
                    row.set_editor_property(field, [moves[n] for n,w in value.items() for _ in range(w[col]*2)])
                continue
            elif key == 'Mesh': value = unreal.load_asset(value)
            elif key == 'MeshTransform':
                x,y,z,yaw,sx,sy,sz = value
                value = unreal.Transform(unreal.Vector(x,y,z), unreal.Rotator(yaw=yaw), unreal.Vector(sx,sy,sz))
            elif key == 'Tint': value = unreal.LinearColor(*value, 1)
            row.set_editor_property(key, value)
        assert eal.save_loaded_asset(row, False)
    bp = unreal.load_asset(ENCOUNTER)
    cdo = unreal.get_default_object(bp.generated_class())
    lookup = dict(cdo.get_editor_property('Opponents'))
    lookup['CVExperience'] = opponents['CVExperience']
    cdo.set_editor_property('Opponents', lookup)
    assert eal.save_loaded_asset(bp, False)
    print('CV rows saved:', len(moves), 'moves,', len(opponents), 'page sections; L1 rows retained')


FUNCTIONS = {
    'StartLevel2CV':[('Journey','object:/Script/Engine.Actor'), ('Assisted','bool')],
    'FinishLevel2CV':[('Won','bool')], 'SyncCVProgress':[], 'FoldCVSection':[],
    'SetCVContext':[], 'CVAssistedAction':[], 'AbortLevel2CV':[],
}


def skeleton():
    for name, kind, default in [('bLevel2CV','bool','false'),('bCVAssisted','bool','false'),
                               ('bCVOutcomeSent','bool','false'),('bCVKnowsPattern','bool','false'),
                               ('CVJourney','object:/Script/Engine.Actor',''),
                               ('CVProgress','int','0'),('CVSavedFleeLine','text',''),('CVSavedItemsLine','text','')]:
        b.call('blueprint_add_variable',path=ENCOUNTER,variable_name=name,variable_type=kind,
               default_value=default,category='Level 2',update_existing=True)
    info = b.call('blueprint_get_info', path=ENCOUNTER)
    for name, inputs in FUNCTIONS.items():
        if name not in info['functions']:
            b.call('blueprint_add_function',path=ENCOUNTER,function_name=name,
                   inputs=[dict(name=n,type=t) for n,t in inputs])
    if 'CVMoveDetail' not in info['functions']:
        b.call('blueprint_add_function',path=ENCOUNTER,function_name='CVMoveDetail',
               inputs=[dict(name='Move',type='object:'+MC)],outputs=[dict(name='Detail',type='text')],pure=True)
    info = b.call('blueprint_get_info',path=WIDGET)
    if 'RefreshCVPresentation' not in info['functions']:
        b.call('blueprint_add_function',path=WIDGET,function_name='RefreshCVPresentation')
    b.call('blueprint_compile',path=ENCOUNTER)
    b.call('blueprint_compile',path=WIDGET)


def start():
    g=b.G(ENCOUNTER,'StartLevel2CV')
    available=g.branch(g.math('Not_PreBool',A=g.getv('bActive')));g.side(available)
    valid=g.branch(g.f(SL+'IsValid',Object=g.arg('Journey')));g.side(valid)
    g.setv('CVJourney',g.arg('Journey'));g.setv('bLevel2CV',True)
    g.setv('bCVAssisted',g.arg('Assisted'));g.setv('bCVOutcomeSent',False);g.setv('CVProgress',0)
    g.setv('CVSavedFleeLine',g.getv('FleeLine'));g.setv('CVSavedItemsLine',g.getv('ItemsLine'))
    g.own('SetCVContext')
    # Bind the leader on the instance too: old placed overrides must not silently reject the CV id.
    g.do('/Script/Engine.BlueprintMapLibrary:Map_Add',TargetMap=g.getv('Opponents'),Key='CVExperience',
         Value=asset('CVExperience','Opponent'))
    g.own('StartEncounter',OpponentId='CVExperience')
    g.setv('bFreePreview',g.math('BooleanOR',A=g.getv('bFreePreview'),B=g.getv('bCVKnowsPattern')))
    g.finish()


def context():
    g=b.G(ENCOUNTER,'SetCVContext')
    gate=g.branch(g.getv('bLevel2CV'));g.side(gate)
    g.setv('FleeLine','The page is still unfinished.')
    g.setv('ItemsLine','The notes are already here.')
    g.finish()


def sync():
    g=b.G(ENCOUNTER,'SyncCVProgress');gate=g.branch(g.getv('bLevel2CV'));g.side(gate)
    garments=g.getv('Garments')
    # SpawnParty finishes before any CV action or widget refresh; EndEncounter closes the active gate.
    ready=g.branch(g.getv('bActive'));g.side(ready)
    total=0
    for i in range(3):
        item=g.ref();g.node(item,'get_array_item',0,0);g.put(item,'Array',garments);g.put(item,'Dimension 1',i)
        progress=g.getv('Progress',(item,'Output'),GARMENT)
        total=g.math('Add_IntInt',A=total,B=g.math('Clamp',Value=progress,Min=0,Max=4))
    g.setv('CVProgress',total)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('CVJourney')));g.side(valid)
    journey=g.cast(g.getv('CVJourney'),JC,'BP L2Journey')
    g.do(JC+':RefreshEmployability',self=journey,Progress=g.getv('CVProgress'));g.finish()


def finish():
    g=b.G(ENCOUNTER,'FinishLevel2CV')
    once=g.branch(g.math('BooleanAND',A=g.getv('bLevel2CV'),B=g.math('Not_PreBool',A=g.getv('bCVOutcomeSent'))));g.side(once)
    g.setv('bCVOutcomeSent',True)
    g.setv('bCVKnowsPattern',True)
    g.own('SyncCVProgress')
    g.own('AbortLevel2CV')
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('CVJourney')));g.side(valid)
    journey=g.cast(g.getv('CVJourney'),JC,'BP L2Journey')
    won=g.branch(g.arg('Won'));g.side(won);g.do(JC+':FinaleWon',self=journey)
    g.side(won,False);g.do(JC+':FinaleLost',self=journey);g.finish()


def abort():
    g=b.G(ENCOUNTER,'AbortLevel2CV');active=g.branch(g.getv('bLevel2CV'));g.side(active)
    g.setv('bCVOutcomeSent',True);g.setv('bAwaitingKey',False);g.setv('bPlayerTurn',False)
    for name in ('AdvancePrompt','RestoreBattleShot','S_Intro','S_PlayerCommand','S_ResolvePlayerAction',
                 'S_EnemyPhase','S_CheckEnd','S_Victory','S_Defeat'):
        g.do(SL+'K2_ClearTimer',FunctionName=name)
    g.own('DreamCycle',bStart=False)
    # Shared EndEncounter restores hit-stop, widget timers, player pose, camera and input locks.
    g.own('EndEncounter')
    g.setv('FleeLine',g.getv('CVSavedFleeLine'));g.setv('ItemsLine',g.getv('CVSavedItemsLine'))
    g.setv('bLevel2CV',False);g.setv('bCVAssisted',False);g.setv('BattleState','None')
    g.finish()


def fold():
    g=b.G(ENCOUNTER,'FoldCVSection')
    target=g.f(EC+':TargetGarment');section=(target[0],'Garment')
    valid=g.branch(g.f(SL+'IsValid',Object=section));g.side(valid)
    g.do(GC+':StopBattleMotion',self=section)
    # Keep the completed sheet visible on the desk; never call clothing equip or its dispatchers.
    g.do('/Script/Engine.Actor:K2_SetActorRotation',self=section,
         NewRotation=g.math('MakeRotator',Pitch=90,Yaw=0,Roll=0),bTeleportPhysics=True)
    g.own('SyncCVProgress');g.own('Respace');g.finish()


def assisted():
    g=b.G(ENCOUNTER,'CVAssistedAction')
    g.own('ApplyPlayerMove',Multiplier=1);g.own('PlayerActionDone');g.finish()


def widget_cleanup_plan(nodes, edges):
    """Skip absent-widget calls, preserving all other authored EndEncounter cleanup.

    A CV debug finish can run after StartEncounter but before delayed ShowEncounter.
    Guard only calls receiving Widget as their target. Null-widget bypasses must
    also enter the next guard when two widget calls are adjacent in the chain.
    """
    marker = 'Widget cleanup readiness'
    if any(n.get('title') == marker for n in nodes):
        return None
    recipients = {e['to_node'] for e in edges
                  if e['from_pin'] == 'Widget' and e['to_pin'] in ('self', 'Object')}
    targets = sorted(t for t in recipients
                     if any(e['to_node'] == t and e['to_pin'] == 'execute' for e in edges))
    node_titles = {n['node_id']:norm(n['title']) for n in nodes}
    widget_valid = {e['to_node'] for e in edges if e['from_pin']=='Widget'
                    and e['to_pin']=='Object' and node_titles.get(e['to_node'])=='isvalid'}
    validity_gates = {e['to_node'] for e in edges if e['from_node'] in widget_valid
                      and e['from_pin']=='ReturnValue' and e['to_pin']=='Condition'}
    def already_guarded(target):
        incoming = [e for e in edges if e['to_node']==target and e['to_pin']=='execute']
        return incoming and all(e['from_node'] in validity_gates and e['from_pin']=='then' for e in incoming)
    if targets and all(already_guarded(target) for target in targets):
        return None
    titles = {norm(n['title']) for n in nodes if n['node_id'] in targets}
    assert {'cancellatentactions', 'removefromparent'} <= titles, ('Widget cleanup calls', titles)
    guards = {target:'wc'+str(i) for i,target in enumerate(targets)}
    g = Batch(ENCOUNTER, 'EndEncounter')
    g.get('wc_widget', 'Widget', -2600, -2000)
    g.fn('wc_valid', SL+'IsValid', -2300, -2000)
    g.link('wc_widget', 'Widget', 'wc_valid', 'Object')
    # Native batches resolve aliases immediately; create every bypass destination first.
    for i,target in enumerate(targets):
        g.node(guards[target], 'branch', -2000+i*320, -2000)
    for i,target in enumerate(targets):
        incoming = [e for e in edges if e['to_node'] == target and e['to_pin'] == 'execute']
        outgoing = [e for e in edges if e['from_node'] == target and e['from_pin'] == 'then']
        assert incoming and len(outgoing) == 1, ('Cleanup call must continue', target, incoming, outgoing)
        gate = guards[target]
        g.link('wc_valid', 'ReturnValue', gate, 'Condition')
        for e in incoming:
            g.cut(e['from_node'], e['from_pin'], target, 'execute')
            g.link(e['from_node'], e['from_pin'], gate, 'execute')
        g.link(gate, 'then', target, 'execute')
        next_edge = outgoing[0]
        next_node = guards.get(next_edge['to_node'], next_edge['to_node'])
        g.link(gate, 'else', next_node, next_edge['to_pin'])
    g.comment(marker, ['wc_widget', 'wc_valid']+list(guards.values()))
    return g


def cleanup_widgets():
    nodes, edges = inspect(ENCOUNTER, 'EndEncounter')
    plan = widget_cleanup_plan(nodes, edges)
    if plan:
        plan.run()


def guard_plan(path, graph, nodes, edges, source_title, function, pins=None, condition='bLevel2CV'):
    """Splice a contextual branch, keeping the existing execution path untouched on false."""
    source=[n['node_id'] for n in nodes if norm(n['title'])==norm(source_title)]
    assert len(source)==1,(graph,source_title,source)
    outgoing=[e for e in edges if e['from_node']==source[0] and e['from_pin']=='then']
    assert len(outgoing)==1,(graph,source_title,outgoing)
    edge=outgoing[0]
    branch_next={e['to_node'] for e in edges if e['from_node']==edge['to_node'] and e['from_pin']=='then'}
    if any(n['node_id'] in branch_next and norm(n['title'])==norm(function) for n in nodes): return None
    g=Batch(path,graph)
    g.get('cv_context',condition,-600,200)
    g.node('cv_gate','branch',-300,0);g.link('cv_context',condition,'cv_gate','Condition')
    g.fn('cv_action',EC+':'+function,0,-180,**(pins or {}))
    g.cut(edge['from_node'],edge['from_pin'],edge['to_node'],edge['to_pin'])
    g.link(edge['from_node'],edge['from_pin'],'cv_gate','execute')
    g.link('cv_gate','then','cv_action','execute')
    g.link('cv_gate','else',edge['to_node'],edge['to_pin'])
    g.comment('Level 2 '+source_title,['cv_context','cv_gate','cv_action'])
    return g


def hook_after(path, graph, source_title, function, owner=EC):
    nodes,edges=inspect(path,graph)
    if any(norm(n['title'])==norm(function) for n in nodes): return
    source=[n['node_id'] for n in nodes if norm(n['title'])==norm(source_title)]
    assert len(source)==1,(graph,source_title,source)
    outgoing=[e for e in edges if e['from_node']==source[0] and e['from_pin']=='then']
    assert len(outgoing)<=1,(graph,outgoing)
    g=Batch(path,graph);g.fn('cv_hook',owner+':'+function,0,-600)
    if outgoing:
        e=outgoing[0];g.cut(e['from_node'],e['from_pin'],e['to_node'],e['to_pin'])
        g.link('cv_hook','then',e['to_node'],e['to_pin'])
    g.chain(source[0],'cv_hook');g.comment('Page progress',['cv_hook']);g.run()


def patches():
    nodes,edges=inspect(ENCOUNTER,'EventGraph')
    for source,won in [('S_Victory',True),('S_Defeat',False)]:
        plan=guard_plan(ENCOUNTER,'EventGraph',nodes,edges,source,'FinishLevel2CV',{'Won':str(won).lower()})
        if plan:
            plan.run()
            nodes,edges=inspect(ENCOUNTER,'EventGraph')
    nodes,edges=inspect(ENCOUNTER,'ApplyPlayerMove')
    plan=guard_plan(ENCOUNTER,'ApplyPlayerMove',nodes,edges,'SetRemaining','FoldCVSection')
    if plan: plan.run()
    for graph in ('ApplyPlayerMove','EnemyAct'):
        hook_after(ENCOUNTER,graph,'AddProgress','SyncCVProgress')
    # Branch immediately before BeginTimedInput. Its false path keeps the original timing chain.
    nodes,edges=inspect(ENCOUNTER,'EventGraph')
    if not any(norm(n['title'])==norm('CVAssistedAction') for n in nodes):
        target=next(n['node_id'] for n in nodes if norm(n['title'])=='begintimedinput')
        incoming=[e for e in edges if e['to_node']==target and e['to_pin']=='execute'];assert len(incoming)==1
        edge=incoming[0];g=Batch(ENCOUNTER,'EventGraph')
        g.get('cv_mode','bLevel2CV',0,-1700);g.get('cv_assist','bCVAssisted',0,-1500)
        g.fn('cv_both',K+'BooleanAND',300,-1700)
        g.link('cv_mode','bLevel2CV','cv_both','A');g.link('cv_assist','bCVAssisted','cv_both','B')
        g.node('cv_assist_gate','branch',600,-1700);g.link('cv_both','ReturnValue','cv_assist_gate','Condition')
        g.fn('cv_apply',EC+':CVAssistedAction',900,-1700)
        g.cut(edge['from_node'],edge['from_pin'],target,'execute')
        g.link(edge['from_node'],edge['from_pin'],'cv_assist_gate','execute')
        g.link('cv_assist_gate','then','cv_apply','execute');g.link('cv_assist_gate','else',target,'execute')
        g.comment('Optional timing assist',['cv_mode','cv_assist','cv_both','cv_assist_gate','cv_apply']);g.run()


def widget_members():
    # The shipped rows already contain these TextBlocks; the original RefreshRow found them by child index.
    for i in range(3):
        b.call('ui_set_variable',widget_blueprint_path=WIDGET,widget_name='Txt_Intent'+str(i),is_variable=True)
    result=b.call('blueprint_compile',path=WIDGET,save=True)
    assert not result.get('error_count') and not result.get('warning_count'),result


def presentation():
    g=b.G(WIDGET,'RefreshCVPresentation');enc=g.getv('Encounter')
    gate=g.branch(g.getv('bLevel2CV',enc,ENCOUNTER));g.side(gate)
    ready=g.branch(g.getv('bActive',enc,ENCOUNTER));g.side(ready)
    progress=g.getv('CVProgress',enc,ENCOUNTER)
    value=g.math('Add_IntInt',A=60,B=g.math('Divide_IntInt',A=g.math('Multiply_IntInt',A=40,B=progress),B=12))
    value=g.f(STRING+'Conv_IntToString',InInt=value)
    line=g.f(STRING+'Concat_StrStr',A='Write the C.V.   Employability ',B=value)
    g.do(TB+'SetText',self=g.getv('Txt_BattleHelp'),InText=g.f(TEXT+'Conv_StringToText',InString=line))
    g.do(TB+'SetText',self=g.getv('Txt_MirrorDetail'),InText='Read it back. Restore Composure and reveal the next truths.')
    status_line=g.f(TEXT+'Conv_TextToString',InText=g.f(TB+'GetText',self=g.getv('Txt_Statuses')))
    for before,after in [('The armhole is lost','Blanked'),('Armhole found','Detail found'),
                         ('The socks are mismatched','Misfiled'),('The tie is tight','Cornered')]:
        status_line=g.f(STRING+'Replace',SourceString=status_line,From=before,To=after)
    g.do(TB+'SetText',self=g.getv('Txt_Statuses'),InText=g.f(TEXT+'Conv_StringToText',InString=status_line))
    for i in range(3):
        array=g.getv('Garments',enc,ENCOUNTER)
        item=g.ref();g.node(item,'get_array_item',0,0);g.put(item,'Array',array);g.put(item,'Dimension 1',i)
        amount=g.getv('Progress',(item,'Output'),GARMENT)
        amount_text=g.f(STRING+'Conv_IntToString',InInt=amount)
        line=g.f(STRING+'Concat_StrStr',A='Revision ',B=amount_text)
        line=g.f(STRING+'Concat_StrStr',A=line,B=' of 4')
        g.do(TB+'SetText',self=g.getv('Txt_Progress'+str(i)),InText=g.f(TEXT+'Conv_StringToText',InString=line))
        target=g.getv('Txt_Intent'+str(i))
        old=g.f(TB+'GetText',self=target)
        line=g.math('SelectString',A='Revised.',B=g.f(TEXT+'Conv_TextToString',InText=old),
                    bPickA=g.math('GreaterEqual_IntInt',A=amount,B=4))
        g.do(TB+'SetText',self=target,InText=g.f(TEXT+'Conv_StringToText',InString=line))
    g.finish()
    hook_after(WIDGET,'RedrawAll','RefreshBattlePresentation','RefreshCVPresentation',WC)


def detail():
    nodes,_=inspect(ENCOUNTER,'CVMoveDetail')
    entry=next(n['node_id'] for n in nodes if norm(n['title'])=='cvmovedetail')
    result=next(n['node_id'] for n in nodes if norm(n['title'])=='returnnode')
    g=Batch(ENCOUNTER,'CVMoveDetail')
    old=[n['node_id'] for n in nodes if n['node_id'] not in (entry,result)]
    if old:g.ops.append(dict(op='remove',node_ids=old))
    g.chain(entry,result)
    def put(ref,pin,value):
        if isinstance(value,tuple):g.link(*value,ref,pin)
        elif value!='':g.pin(ref,pin,value)
    def fn(ref,name,**pins):
        g.fn(ref,name,0,0)
        for p,v in pins.items():put(ref,p,v)
        return ref,'ReturnValue'
    def select(ref,yes,no,condition):
        return fn(ref,K+'SelectString',A=yes,B=no,bPickA=condition)
    previous='Choose a section to revise.'
    details=dict(D.DETAILS)
    details.update(DeepBreath='Restore up to 15 Resolve and 5 Composure.',
                   CheckMirror='Restore up to 20 Composure. Reveal the next truths.')
    g.get('assist','bCVAssisted',0,0)
    for name,line in details.items():
        path=asset(name) if name in D.MOVES else '/Game/FoA/Gameplay/Encounter/Data/DA_Move_'+name+'.DA_Move_'+name
        yes=line
        if name in ('CVRewriteExperience','CVRewriteReliability'):
            yes=select('assisted_'+name,'Revise one part. Timing assist gives normal progress.',line,('assist','bCVAssisted'))
        is_move=fn('is_'+name,K+'EqualEqual_ObjectObject',A=(entry,'Move'),B=path)
        previous=select('line_'+name,yes,previous,is_move)
    g.get('blocked','BlockedBy',0,0,MC);g.link(entry,'Move','blocked','self')
    remedy='Blocked by an active condition.'
    for key,line in [('SleeveLabyrinth','Blanked. Find a detail first.'),('Mismatched','Misfiled. Sort the facts first.'),
                     ('Constricted','Cornered. Loosen the claim first.')]:
        equal=fn('status_'+key,K+'EqualEqual_NameName',A=('blocked','BlockedBy'),B=key)
        remedy=select('remedy_'+key,line,remedy,equal)
    usable=fn('usable',EC+':CanUseMove',Move=(entry,'Move'))
    previous=select('usable_line',previous,remedy,('usable','bCan'))
    cost=fn('cost',EC+':MoveCost',Move=(entry,'Move'));g.get('resolve','Resolve',0,0)
    short=fn('short',K+'Less_IntInt',A=('resolve','Resolve'),B=('cost','Cost'))
    need=fn('cost_text',STRING+'Conv_IntToString',InInt=('cost','Cost'))
    need=fn('need',STRING+'Concat_StrStr',A='Need ',B=need)
    need=fn('need_suffix',STRING+'Concat_StrStr',A=need,B=' Resolve. Breathe to recover.')
    previous=select('funded',need,previous,short)
    as_text=fn('as_text',TEXT+'Conv_StringToText',InString=previous)
    g.link(*as_text,result,'Detail')
    for i,o in enumerate(o for o in g.ops if o['op']=='add_node'):o.update(x=(i//5)*340,y=(i%5)*220)
    g.comment('C.V action details',[o['ref'] for o in g.ops if o['op']=='add_node']);compact_refs(g);g.run()
    nodes,edges=inspect(ENCOUNTER,'MoveDetail')
    if any(norm(n['title'])=='cvmovedetail' for n in nodes):return
    entry=next(n['node_id'] for n in nodes if norm(n['title'])=='movedetail')
    result=next(n['node_id'] for n in nodes if norm(n['title'])=='returnnode')
    incoming=[e for e in edges if e['to_node']==result and e['to_pin']=='Detail'];assert len(incoming)==1
    edge=incoming[0];g=Batch(ENCOUNTER,'MoveDetail')
    g.fn('cv_detail',EC+':CVMoveDetail',6000,1600);g.link(entry,'Move','cv_detail','Move')
    g.fn('cv_string',TEXT+'Conv_TextToString',6300,1600);g.link('cv_detail','Detail','cv_string','InText')
    g.fn('old_string',TEXT+'Conv_TextToString',6300,1850);g.link(edge['from_node'],edge['from_pin'],'old_string','InText')
    g.get('cv_context','bLevel2CV',6300,2100)
    g.fn('context_detail',K+'SelectString',6600,1600)
    g.link('cv_string','ReturnValue','context_detail','A');g.link('old_string','ReturnValue','context_detail','B')
    g.link('cv_context','bLevel2CV','context_detail','bPickA')
    g.fn('detail_text',TEXT+'Conv_StringToText',6900,1600);g.link('context_detail','ReturnValue','detail_text','InString')
    g.cut(edge['from_node'],edge['from_pin'],result,'Detail');g.link('detail_text','ReturnValue',result,'Detail')
    g.comment('C.V context',['cv_detail','cv_string','old_string','cv_context','context_detail','detail_text']);g.run()


STEPS={'skeleton':skeleton,'start':start,'context':context,'sync':sync,'finish':finish,'fold':fold,
       'assisted':assisted,'abort':abort,'patches':patches,'widget_members':widget_members,
       'widget':presentation,'rows':rows,'detail':detail,'cleanup_widgets':cleanup_widgets}


if __name__=='__main__':
    phase=os.environ.get('FOA_CV_PHASE') or sys.argv[1]
    if phase=='rows': rows()
    else:
        import editor_lock
        owner=os.environ.get('FOA_AGENT','l2_mech')
        editor_lock.acquire(owner,wait_s=300,ttl=180,areas=[ENCOUNTER,WIDGET,D.ROOT])
        try:
            assert not b.call('editor_get_state')['pie_running']
            STEPS[phase]()
        finally:
            for path in (ENCOUNTER,WIDGET): b.call('blueprint_compile',path=path)
            editor_lock.release(owner)
