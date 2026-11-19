"""Rig lane: the wire-hanger uses (T7 bed hook, T5/T6 door gap), Hayba graph batches + small editor-Python steps.
  $env:HAYBA_AGENT_ID='rig'; python Tools/Unreal/rig/hanger_use_build.py <step>
Steps (each idempotent, each under its own short asset lease, compiled 0/0 and saved):
  create    BP_FoAHangerUse (Actor: Hanger + Proxy static meshes, the path variables), its children _Door / _Bed,
            AN_FoA_HangerUse (AnimNotify: SpawnClass) under /Game/FoA/Characters/Player/Hanger
  graph     BP_FoAHangerUse EventGraph: BeginPlay takes the player, BeginGrip(Hanger, 'Hanger', HandInAnchor);
            Tick follows the montage position along the keys (Tools/Rig/hanger_use_keys.py), slides the pawn to the
            stance during the kneel, moves the proxy shirt; EndGrip + destroy when the montage stops.
  notify    AN_FoA_HangerUse.Received_Notify: spawns SpawnClass when the mesh's owner is a BP_FoAPlayer and none is alive.
  defaults  the children's keys, stance, montage (from Saved/RigShots/hanger_use/keys.json).
BeginGrip / EndGrip are the anim lane's (grip_runtime_graphs.py), called, never edited."""
import json
import os
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/rig']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

OWNER = os.environ.setdefault('HAYBA_AGENT_ID', 'rig')
D = '/Game/FoA/Characters/Player/Hanger'
BP, AN = D + '/BP_FoAHangerUse', D + '/AN_FoA_HangerUse'
KIDS = {'door': D + '/BP_FoAHangerUse_Door', 'bed': D + '/BP_FoAHangerUse_Bed'}
BPC = BP + '.BP_FoAHangerUse_C'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer'
PLAYER_C = PLAYER + '.BP_FoAPlayer_C'
K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
AI = '/Script/Engine.AnimInstance:'
SC = '/Script/Engine.SceneComponent:'
ACT = '/Script/Engine.Actor:'
KEYS = json.load(open('P:/FoA/Saved/RigShots/hanger_use/keys.json'))
HANGER = '/Game/FoA/Lux3D/wire_hanger/SM_Lux3D_WireHanger.SM_Lux3D_WireHanger'
SHIRT = '/Game/FoA/Lux3D/the_shirt_enemy/SM_Lux3D_ShirtEnemy.SM_Lux3D_ShirtEnemy'


def call(name, **args):
    r = h.call(name, args, owner=OWNER, timeout=60)
    assert r.get('ok'), (name, r)
    d = r.get('data', {})
    assert d.get('ok', True), (name, d)
    return d


def exists(path):
    return bool(h.call('blueprint_get_info', dict(path=path), owner=OWNER).get('ok'))


def create():
    if not exists(BP):
        call('blueprint_create', name='BP_FoAHangerUse', package_path=BP, parent_class_path='/Script/Engine.Actor')
    comps = json.dumps(call('blueprint_get_info', path=BP))
    for name in ('Hanger', 'Proxy'):
        if '"%s"' % name not in comps:
            call('blueprint_add_component', path=BP, component_class_path='/Script/Engine.StaticMeshComponent', component_name=name)
    for name, kind, cont, default in (
            ('Player', 'object:' + PLAYER_C, 'none', ''), ('Anim', 'object:/Script/Engine.AnimInstance', 'none', ''),
            ('Montage', 'object:/Script/Engine.AnimMontage', 'none', ''), ('PawnStart', 'transform', 'none', ''),
            ('StanceT', 'transform', 'none', ''), ('Stance', 'vector', 'none', ''), ('SlideTime', 'float', 'none', '0.6'),
            ('Dt', 'float', 'none', str(KEYS['dt'])), ('KeyCount', 'int', 'none', '0'),
            ('KeysA', 'transform', 'array', ''), ('KeysB', 'transform', 'array', ''), ('KeysW', 'float', 'array', ''),
            ('KeysP', 'transform', 'array', ''), ('ProxyHideAt', 'float', 'none', '0.0'),
            ('HandInAnchor', 'transform', 'none', ''), ('GripPose', 'name', 'none', 'Hanger')):
        call('blueprint_add_variable', path=BP, variable_name=name, variable_type=kind, container=cont,
             **({'default_value': default} if default else {}), category='Hanger', update_existing=True)
    call('blueprint_compile', path=BP, save=True)
    for use, path in KIDS.items():
        if not exists(path):
            call('blueprint_create', name=path.rsplit('/', 1)[1], package_path=path, parent_class_path=BPC)
            call('blueprint_compile', path=path, save=True)
    if not exists(AN):
        call('blueprint_create', name='AN_FoA_HangerUse', package_path=AN, parent_class_path='/Script/Engine.AnimNotify')
    call('blueprint_add_variable', path=AN, variable_name='SpawnClass', variable_type='class:' + BPC, category='Hanger',
         instance_editable=True, update_existing=True)
    call('blueprint_compile', path=AN, save=True)
    print('CREATE', json.dumps(call('blueprint_get_info', path=BP))[:1500])


def probe():
    """Pins of the node kinds the graph uses that are not plain calls."""
    for kind, extra in (('get_array_item', {}), ('spawn_actor_from_class', {})):
        r = h.call('blueprint_add_node', dict(path=BP, graph_name='EventGraph', node_type=kind, x=-2000, y=-2000, **extra), owner=OWNER)
        print(kind, json.dumps(r)[:1500])
        nid = (r.get('data') or {}).get('node_id')
        if nid:
            h.call('blueprint_remove_nodes', dict(path=BP, graph_name='EventGraph', node_ids=[nid]), owner=OWNER)
    ns, _ = inspect(BP, 'EventGraph')
    print('EVENTGRAPH', [(n['node_id'], n['title']) for n in ns])


PINS = ('Array', 'Dimension 1', 'Output')  # get_array_item's pins (the probe step prints them)


def graph():
    import hanger_use_graph
    hanger_use_graph.build(BP, PLAYER_C, PINS)


def notify():
    """Received_Notify: only for a BP_FoAPlayer's mesh (not the Persona preview), only when no hanger use is alive."""
    ns, _ = inspect(AN, 'Received_Notify')
    e = next(n['node_id'] for n in ns if any(p['name'] == 'MeshComp' and p['direction'] == 'output' for p in n.get('pins', [])))
    ret = next((n['node_id'] for n in ns if any(p['name'] == 'ReturnValue' and p['direction'] == 'input' for p in n.get('pins', []))), None)
    b = Batch(AN, 'Received_Notify')
    old = [n['node_id'] for n in ns if n['node_id'] not in (e, ret)]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    if ret is None:
        ret = b.node('ret', 'function_result', 1800, 0)
    b.fn('owner', '/Script/Engine.ActorComponent:GetOwner', 0, 300); b.link(e, 'MeshComp', 'owner', 'self')
    b.node('cast', 'cast', 300, 0, class_path=PLAYER_C); b.link('owner', 'ReturnValue', 'cast', 'Object'); b.chain(e, 'cast')
    b.fn('alive', GS + 'GetActorOfClass', 600, 300, ActorClass=BPC); b.link('owner', 'ReturnValue', 'alive', 'WorldContextObject')
    b.fn('isv', '/Script/Engine.KismetSystemLibrary:IsValid', 900, 300); b.link('alive', 'ReturnValue', 'isv', 'Object')
    b.node('once', 'branch', 600, 0); b.link('isv', 'ReturnValue', 'once', 'Condition'); b.chain('cast', 'once')
    b.get('cls', 'SpawnClass', 900, 500)
    b.fn('xf', ACT + 'GetTransform', 900, 650); b.link('owner', 'ReturnValue', 'xf', 'self')
    b.node('spawn', 'spawn_actor_from_class', 1200, 0)
    b.link('once', 'else', 'spawn', 'execute'); b.link('cls', 'SpawnClass', 'spawn', 'Class'); b.link('xf', 'ReturnValue', 'spawn', 'SpawnTransform')
    b.link('owner', 'ReturnValue', 'spawn', 'Owner')
    b.pin(ret, 'ReturnValue', 'true')
    b.link('spawn', 'then', ret, 'execute'); b.link('once', 'then', ret, 'execute'); b.link('cast', 'CastFailed', ret, 'execute')
    b.comment('A BP_FoAPlayer montage reached the hanger: spawn its hanger use (one at a time)',
              ['owner', 'cast', 'alive', 'isv', 'once', 'cls', 'xf', 'spawn'])
    b.run()


STEPS = {'create': create, 'probe': probe, 'graph': graph, 'notify': notify}
if __name__ == '__main__':
    step = sys.argv[1]
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    lease = h.lease_acquire(OWNER, ['asset:' + D, 'asset:/Game/FoA/Characters/Player/Montages'], ttl_s=120, wait_s=600)
    try:
        STEPS[step]()
    finally:
        h.release(OWNER, lease)
