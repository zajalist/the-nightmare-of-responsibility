"""BPL_FoAAudio (audio lane): one call per foot plant, so the anim lane's AN_FoA_FootPlant stays a one-liner.
  $env:HAYBA_AGENT_ID='horror'; python Tools/Unreal/horror/build_audio_lib.py
PlayFootstep(Location: Vector, Surface: Name, Gear: Name, Gait: float)
  Surface: 'Rug' (actors tagged Rug) or anything else for the wooden boards ('Sand' stays with BPL_SandFX.SpawnSandStep)
  Gear:    'Boots' (from T3), 'Shoes' (the suit, T9), anything else = socks
  Gait:    0 crouch, 1 walk, 2 jog -> volume 0.45..1.0
Layers on wood near the bed foot or the door: a board creak 35% of the time. Every step: a cloth rustle 45% of the time.
All sounds are the random no-repeat MetaSound presets (pitch and volume variance live in the template)."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, find, inspect  # noqa: E402

P = '/Game/FoA/Audio/BPL_FoAAudio'
MS = '/Game/FoA/Audio/MetaSounds/'
K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'


def s(name):
    return f'{MS}{name.split("_")[1]}/{name}.{name}'


def call(cmd, **params):
    r = h.call(cmd, params)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed'), d
    return d


def build():
    if not h.call('blueprint_get_info', {'path': P}).get('ok'):
        call('blueprint_create', name='BPL_FoAAudio', package_path=P, parent_class_path='/Script/Engine.BlueprintFunctionLibrary')
    info = call('blueprint_get_info', path=P)
    if 'PlayFootstep' not in info['functions']:
        call('blueprint_add_function', path=P, function_name='PlayFootstep',
             inputs=[{'name': 'Location', 'type': 'vector'}, {'name': 'Surface', 'type': 'name'},
                     {'name': 'Gear', 'type': 'name'}, {'name': 'Gait', 'type': 'float'}])
    ns, _ = inspect(P, 'PlayFootstep')
    e = find(ns, 'PlayFootstep')
    b = Batch(P, 'PlayFootstep')
    old = [n['node_id'] for n in ns if n['node_id'] != e]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    b.fn('vol', K + 'MapRangeClamped', 0, 400, InRangeA=0, InRangeB=2, OutRangeA=0.45, OutRangeB=1.0)
    b.link(e, 'Gait', 'vol', 'Value')
    for ref, pin, val, y in (('isRug', 'Surface', 'Rug', 550), ('isBoots', 'Gear', 'Boots', 700), ('isShoes', 'Gear', 'Shoes', 850)):
        b.fn(ref, K + 'EqualEqual_NameName', 0, y, B=val)
        b.link(e, pin, ref, 'A')
    b.node('rug', 'branch', 250, 0)
    b.link('isRug', 'ReturnValue', 'rug', 'Condition')
    b.node('rugBoots', 'branch', 500, -250)
    b.link('isBoots', 'ReturnValue', 'rugBoots', 'Condition')
    b.node('boots', 'branch', 500, 150)
    b.link('isBoots', 'ReturnValue', 'boots', 'Condition')
    b.node('shoes', 'branch', 750, 300)
    b.link('isShoes', 'ReturnValue', 'shoes', 'Condition')
    plays = [('pBR', 'S_Footsteps_BootsRug', 750, -350), ('pSR', 'S_Footsteps_SocksRug', 750, -150),
             ('pBW', 'S_Footsteps_BootsWood', 1000, 100), ('pDS', 'S_Footsteps_DressShoeWood', 1000, 300),
             ('pSW', 'S_Footsteps_SocksWood', 1000, 500)]
    for ref, snd, x, y in plays:
        b.fn(ref, GS + 'PlaySoundAtLocation', x, y, Sound=s(snd))
        b.link(e, 'Location', ref, 'Location')
        b.link('vol', 'ReturnValue', ref, 'VolumeMultiplier')
        b.link(e, '__WorldContext', ref, 'WorldContextObject')  # a function library has no self: pass the caller's world
    b.chain(e, 'rug', 'rugBoots', 'pBR')
    b.link('rugBoots', 'else', 'pSR', 'execute')
    b.link('rug', 'else', 'boots', 'execute')
    b.chain('boots', 'pBW')
    b.link('boots', 'else', 'shoes', 'execute')
    b.chain('shoes', 'pDS')
    b.link('shoes', 'else', 'pSW', 'execute')
    # creaky boards at the bed foot and the door, on wood only
    for ref, at, y in (('dBed', '145,-191,0', 1000), ('dDoor', '320,87,0', 1150)):
        b.fn(ref, K + 'Vector_Distance2D', 1300, y, V2=at)
        b.link(e, 'Location', ref, 'V1')
        b.fn(ref + 'N', K + 'Less_DoubleDouble', 1550, y, B=130)
        b.link(ref, 'ReturnValue', ref + 'N', 'A')
    b.fn('near', K + 'BooleanOR', 1800, 1050)
    b.link('dBedN', 'ReturnValue', 'near', 'A')
    b.link('dDoorN', 'ReturnValue', 'near', 'B')
    b.fn('wood', K + 'Not_PreBool', 1800, 1200)
    b.link('isRug', 'ReturnValue', 'wood', 'A')
    b.fn('chance', K + 'RandomBoolWithWeight', 1800, 1350, Weight=0.35)
    b.fn('creakA', K + 'BooleanAND', 2050, 1100)
    b.link('near', 'ReturnValue', 'creakA', 'A')
    b.link('wood', 'ReturnValue', 'creakA', 'B')
    b.fn('creakB', K + 'BooleanAND', 2300, 1200)
    b.link('creakA', 'ReturnValue', 'creakB', 'A')
    b.link('chance', 'ReturnValue', 'creakB', 'B')
    b.node('creak', 'branch', 1500, 0)
    b.link('creakB', 'ReturnValue', 'creak', 'Condition')
    b.fn('pCreak', GS + 'PlaySoundAtLocation', 1750, -100, Sound=s('S_Creaks_Floor'), VolumeMultiplier=0.7)
    b.link(e, 'Location', 'pCreak', 'Location')
    b.link(e, '__WorldContext', 'pCreak', 'WorldContextObject')
    for ref, _, _, _ in plays:
        b.link(ref, 'then', 'creak', 'execute')
    b.chain('creak', 'pCreak')
    # cloth on the body
    b.fn('clothOdds', K + 'RandomBoolWithWeight', 2000, 300, Weight=0.45)
    b.node('cloth', 'branch', 2000, 0)
    b.link('clothOdds', 'ReturnValue', 'cloth', 'Condition')
    b.fn('up', K + 'Add_VectorVector', 2250, 300, B='0,0,100')
    b.link(e, 'Location', 'up', 'A')
    b.fn('cv', K + 'Multiply_DoubleDouble', 2250, 450, B=0.5)
    b.link('vol', 'ReturnValue', 'cv', 'A')
    b.fn('pCloth', GS + 'PlaySoundAtLocation', 2500, -100, Sound=s('S_Foley_ClothMove'))
    b.link('up', 'ReturnValue', 'pCloth', 'Location')
    b.link(e, '__WorldContext', 'pCloth', 'WorldContextObject')
    b.link('cv', 'ReturnValue', 'pCloth', 'VolumeMultiplier')
    b.link('creak', 'else', 'cloth', 'execute')
    b.link('pCreak', 'then', 'cloth', 'execute')
    b.chain('cloth', 'pCloth')
    b.comment('Footstep by surface and gear', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()


if __name__ == '__main__':
    assert not call('editor_get_state')['pie_running'], 'PIE is running: wait'
    lease = h.lease_acquire(h.agent_id(), ['asset:' + P], ttl_s=180, wait_s=60)
    try:
        build()
    finally:
        h.release(h.agent_id(), lease)
