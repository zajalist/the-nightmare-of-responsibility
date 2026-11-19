"""Battle lane, GTX 1060 Low fight (coordinator 2026-11-18 15:10): at Low only, the black sand leaves the custom-depth pass.
  $env:HAYBA_AGENT_ID='battle'; python Tools/Unreal/encounter/low_custom_depth.py <declare|body|hook|revert|selftest>
Hold a lease on BP_Encounter first. Each phase compiles and saves.
Why sand: in the fight, custom depth draws every primitive with Render CustomDepth on. The garments have it off. Sand
(stencil 5: dressing piles, the clock, BP_BattleSand, BP_SandAmbience, the player's FaceDrift/BodyDrift) is most of
the triangles and every Nanite primitive in the pass. Stencil 5 only feeds the dream post's sand effects: the SandWarp
haze and the TimeEcho damping, which the atmosphere lane's Low branch turns off, and the lens pass's sand opt-out from
glow. Faces (4), the colour keep (1), the Nightmare tear (2) and the focus rim (3) keep custom depth.
ApplyLowDepth() (BP_Encounter):
  want = bActive and sg.ShadingQuality == 0. That cvar is what the overall Low preset (GameUserSettings, the Settings
  Quality row), a custom Shading Low and the console `scalability 0` all set.
  On a change: every primitive whose custom depth is on with stencil 5 loses it, and its stencil goes to 205, which
  marks it as this function's. Back above Low, or when the encounter ends, every primitive with custom depth off and
  stencil 205 gets stencil 5 and custom depth back. Medium and up: want is false, nothing is touched.
  StartEncounter calls it, then a 1 s looping timer catches a preset change during the fight. EndEncounter calls it
  after bActive goes false and clears the timer."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/level2']
from held_tool_graphs import Batch, inspect  # noqa: E402
import build_drive as b  # noqa: E402

ENC = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
EC, K, GS, SL = b.cls(ENC), b.K, b.GS, b.SL
PRIM = '/Script/Engine.PrimitiveComponent'
FN = 'ApplyLowDepth'
SAND, MINE = 5, 205


def declare():
    b.call('blueprint_add_variable', path=ENC, variable_name='bLowDepth', variable_type='bool', default_value='false',
           category='Encounter|Perf', update_existing=True)
    if not b.h.call('blueprint_inspect_graph', dict(path=ENC, graph_name=FN, limit=1)).get('ok'):
        b.call('blueprint_add_function', path=ENC, function_name=FN, pure=False, inputs=[], outputs=[])
    print('declare compile', b.call('blueprint_compile', path=ENC).get('error_count'))


def body():
    ns, _ = inspect(ENC, FN)
    e = next(n['node_id'] for n in ns if n['title'].replace(' ', '') == FN)
    g = Batch(ENC, FN)
    old = [n['node_id'] for n in ns if n['node_id'] != e]
    if old:
        g.ops.append(dict(op='remove', node_ids=old))
    # want = bActive and sg.ShadingQuality == 0
    g.fn('cvar', SL + 'GetConsoleVariableIntValue', 0, 300, VariableName='sg.ShadingQuality')
    g.fn('low', K + 'EqualEqual_IntInt', 250, 300, B=0); g.link('cvar', 'ReturnValue', 'low', 'A')
    g.get('active', 'bActive', 250, 450)
    g.fn('want', K + 'BooleanAND', 450, 350); g.link('active', 'bActive', 'want', 'A'); g.link('low', 'ReturnValue', 'want', 'B')
    g.get('cur', 'bLowDepth', 450, 500)
    g.fn('same', K + 'EqualEqual_BoolBool', 650, 400); g.link('want', 'ReturnValue', 'same', 'A'); g.link('cur', 'bLowDepth', 'same', 'B')
    g.node('changed', 'branch', 300, 0); g.link('same', 'ReturnValue', 'changed', 'Condition')
    g.set('mark', 'bLowDepth', 600, 0); g.link('want', 'ReturnValue', 'mark', 'bLowDepth')
    g.fn('actors', GS + 'GetAllActorsOfClass', 900, 0, ActorClass='/Script/Engine.Actor')
    g.node('eachA', 'macro', 1200, 0, macro_name='ForEachLoop'); g.link('actors', 'OutActors', 'eachA', 'Array')
    g.fn('comps', '/Script/Engine.Actor:K2_GetComponentsByClass', 1200, 300, ComponentClass=PRIM)
    g.link('eachA', 'Array Element', 'comps', 'self')
    g.node('eachB', 'macro', 1500, 0, macro_name='ForEachLoop'); g.link('comps', 'ReturnValue', 'eachB', 'Array')
    g.node('prim', 'cast', 1800, 0, class_path=PRIM); g.link('eachB', 'Array Element', 'prim', 'Object')
    # in the loop, bLowDepth is the new state: on the way down take (depth on, 5); on the way up take (depth off, 205)
    g.get('now', 'bLowDepth', 1800, 500)
    g.get('cd', 'bRenderCustomDepth', 2000, 300, PRIM); g.link('prim', 'AsPrimitive Component', 'cd', 'self')
    g.fn('cdok', K + 'EqualEqual_BoolBool', 2200, 300); g.link('cd', 'bRenderCustomDepth', 'cdok', 'A'); g.link('now', 'bLowDepth', 'cdok', 'B')
    g.get('st', 'CustomDepthStencilValue', 2000, 450, PRIM); g.link('prim', 'AsPrimitive Component', 'st', 'self')
    g.fn('from', K + 'SelectInt', 2000, 600, A=SAND, B=MINE); g.link('now', 'bLowDepth', 'from', 'bPickA')
    g.fn('stok', K + 'EqualEqual_IntInt', 2200, 450); g.link('st', 'CustomDepthStencilValue', 'stok', 'A'); g.link('from', 'ReturnValue', 'stok', 'B')
    g.fn('both', K + 'BooleanAND', 2400, 350); g.link('cdok', 'ReturnValue', 'both', 'A'); g.link('stok', 'ReturnValue', 'both', 'B')
    g.node('take', 'branch', 2100, 0); g.link('both', 'ReturnValue', 'take', 'Condition')
    g.fn('notnow', K + 'Not_PreBool', 2400, 600); g.link('now', 'bLowDepth', 'notnow', 'A')
    g.fn('depth', PRIM + ':SetRenderCustomDepth', 2400, 0); g.link('prim', 'AsPrimitive Component', 'depth', 'self')
    g.link('notnow', 'ReturnValue', 'depth', 'bValue')
    g.fn('to', K + 'SelectInt', 2600, 600, A=MINE, B=SAND); g.link('now', 'bLowDepth', 'to', 'bPickA')
    g.fn('stencil', PRIM + ':SetCustomDepthStencilValue', 2700, 0); g.link('prim', 'AsPrimitive Component', 'stencil', 'self')
    g.link('to', 'ReturnValue', 'stencil', 'Value')
    g.chain(e, 'cvar', 'changed'); g.link('changed', 'else', 'mark', 'execute'); g.chain('mark', 'actors')  # the cvar read is impure
    g.link('actors', 'then', 'eachA', 'Exec'); g.link('eachA', 'LoopBody', 'eachB', 'Exec')
    g.link('eachB', 'LoopBody', 'prim', 'execute'); g.link('prim', 'then', 'take', 'execute')
    g.link('take', 'then', 'depth', 'execute'); g.chain('depth', 'stencil')
    g.comment('Low only: the black sand (stencil 5) leaves the custom-depth pass during the fight; 205 marks what this '
              'function took, and it all goes back above Low or when the fight ends',
              ['cvar', 'low', 'active', 'want', 'cur', 'same', 'changed', 'mark', 'actors', 'eachA', 'comps', 'eachB',
               'prim', 'now', 'cd', 'cdok', 'st', 'from', 'stok', 'both', 'take', 'notnow', 'depth', 'to', 'stencil'])
    g.run()


def hook():
    """StartEncounter: after SetState, ApplyLowDepth then a 1 s looping timer. EndEncounter: after bActive goes false,
    ApplyLowDepth (restores) and clear the timer."""
    ns, es = inspect(ENC, 'StartEncounter')
    if not any(n['title'] == FN or n['title'] == 'Apply Low Depth' for n in ns):
        last = [n['node_id'] for n in ns if n['title'] == 'SetState'
                and not any(x['from_node'] == n['node_id'] and x['from_pin'] == 'then' for x in es)]
        assert len(last) == 1, last
        g = Batch(ENC, 'StartEncounter')
        g.fn('ld_apply', EC + ':' + FN, 2600, 0)
        g.fn('ld_timer', SL + 'K2_SetTimer', 2900, 0, FunctionName=FN, Time=1.0, bLooping='true')
        g.link(last[0], 'then', 'ld_apply', 'execute'); g.chain('ld_apply', 'ld_timer')
        g.comment('Low only: sand custom depth off; the timer catches a preset change mid-fight', ['ld_apply', 'ld_timer'])
        g.run()
    ns, es = inspect(ENC, 'EndEncounter')
    if not any(n['title'] == FN or n['title'] == 'Apply Low Depth' for n in ns):
        by = {n['node_id']: n for n in ns}
        sets = [x for x in es if x['from_pin'] == 'then' and by[x['from_node']]['title'] == 'Set bActive'
                and by[x['to_node']]['title'] == 'Set bPlayerTurn']
        assert len(sets) == 1, sets
        a, z = sets[0]['from_node'], sets[0]['to_node']
        g = Batch(ENC, 'EndEncounter')
        g.fn('ld_apply', EC + ':' + FN, 0, 1800)
        g.fn('ld_clear', SL + 'K2_ClearTimer', 300, 1800, FunctionName=FN)
        g.cut(a, 'then', z, 'execute')
        g.link(a, 'then', 'ld_apply', 'execute'); g.chain('ld_apply', 'ld_clear'); g.link('ld_clear', 'then', z, 'execute')
        g.comment('Sand custom depth back (Low fight cut)', ['ld_apply', 'ld_clear'])
        g.run()


def revert():
    """Unhook both call sites, empty the function (kept declared so nothing dangles), compile and save."""
    for graph in ('StartEncounter', 'EndEncounter'):
        ns, es = inspect(ENC, graph)
        by = {n['node_id']: n for n in ns}
        mine = [n['node_id'] for n in ns if n['title'] in (FN, 'Apply Low Depth')
                or (n['title'] in ('Set Timer by Function Name', 'Clear Timer by Function Name')
                    and any(p['name'] == 'FunctionName' and p.get('default_value') == FN for p in n['pins']))]
        if not mine:
            continue
        ins = [x for x in es if x['to_node'] in mine and x['to_pin'] == 'execute' and x['from_node'] not in mine]
        outs = [x for x in es if x['from_node'] in mine and x['from_pin'] == 'then' and x['to_node'] not in mine]
        g = Batch(ENC, graph)
        g.ops.append(dict(op='remove', node_ids=mine))
        for i in ins:
            for o in outs:
                g.link(i['from_node'], i['from_pin'], o['to_node'], o['to_pin'])
        print(graph, 'unhook', [by[m]['title'] for m in mine])
        g.run()
    ns, _ = inspect(ENC, FN)
    e = next(n['node_id'] for n in ns if n['title'].replace(' ', '') == FN)
    g = Batch(ENC, FN)
    g.ops.append(dict(op='remove', node_ids=[n['node_id'] for n in ns if n['node_id'] != e]))
    g.run()


def selftest():
    """Offline: the in-loop pick table is the inverse of itself (what goes down comes back up)."""
    pick = lambda now: (SAND if now else MINE, MINE if now else SAND, not now)  # noqa: E731  (take stencil, set stencil, depth)
    down, up = pick(True), pick(False)
    assert down == (5, 205, False) and up == (205, 5, True)
    assert down[1] == up[0] and up[1] == down[0]
    print('selftest ok')


if __name__ == '__main__':
    {'declare': declare, 'body': body, 'hook': hook, 'revert': revert, 'selftest': selftest}[sys.argv[1]]()
