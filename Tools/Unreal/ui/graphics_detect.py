"""First-run graphics auto-detect (perf lane via the coordinator, 2026-11-18): GameUserSettings defaults to Epic and
nothing ran the hardware benchmark, so a GTX 1060 started the fight at about 16 fps. Now the boot path picks the preset:

  BPFL_FoASettings.AutoDetectGraphics(Settings, bAllowInEditor) -> Ran
      once per Settings slot (SG_FoASettings.GraphicsDetectVersion < 2), only when GetBuildConfiguration() is
      "Shipping" unless bAllowInEditor (earlier gates failed: IsObjectCooked is editor-only, PIE's command line has
      no .uproject, and a packaged game's GetProjectDirectory is absolute too):
      RunHardwareBenchmark(10, 1, 1), ApplyHardwareBenchmarkResults, snap a mixed result to one preset (the GPU-driven
      shadow level) so Settings shows Low, Medium, High or Epic rather than a clamped "Low", ApplySettings, SaveSettings.
  LoadAndApplySettings: LoadSettings -> AutoDetectGraphics(Settings, false) -> (Ran) SaveSettings -> ApplySettings
The editor never runs it on its own (one shared editor: a benchmark there would change every lane's scalability);
QA plan UIG proves it in PIE on a fresh, unsaved SG_FoASettings and restores the editor's levels afterwards.
The thresholds (1060 -> Medium, 1650 laptop -> Low) are the perf lane's Config/DefaultScalability.ini.
  python Tools/Unreal/ui/graphics_detect.py        (idempotent; compile and save inside one lease)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, entry_of, graph, is_empty, ok, save  # noqa: E402

SG = '/Game/FoA/UI/Framework/SG_FoASettings'
SG_C = SG + '.SG_FoASettings_C'
LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings'
LIB_C = LIB + '.BPFL_FoASettings_C'
GUS = '/Script/Engine.GameUserSettings'
KML, KSL = '/Script/Engine.KismetMathLibrary', '/Script/Engine.KismetSystemLibrary'
KSTR = '/Script/Engine.KismetStringLibrary'


def packaged(b):
    """True in a Shipping build only. GetBuildConfiguration is pure (an impure node wired as data is pruned in 5.9)."""
    return b.fn(f'{KSTR}:EqualEqual_StrStr', A=b.fn(f'{KSL}:GetBuildConfiguration'), B='Shipping')


DETECT_VERSION = 2  # bump to re-detect every player once (version 0: older slots, whatever their bGraphicsDetected)


def shipping_gate_and_version():
    """Final-build fix (coordinator 12:30, perf lane's Shipping_20261118_1227): GetProjectDirectory is absolute in a
    packaged game too, so detection never ran. The gate is now GetBuildConfiguration() == "Shipping" (pure;
    "Development" in the editor and PIE). "Already detected" is SG_FoASettings.GraphicsDetectVersion >= 2 instead
    of bGraphicsDetected, so a slot from an earlier build is detected once more. GameUserSettings'
    LastGPUBenchmarkResult would be the natural test, but it is config-only in 5.9 (no UFUNCTION getter, not
    BlueprintVisible), so a Blueprint-only project cannot read it."""
    nodes, edges = graph(LIB, 'AutoDetectGraphics')
    by = {n['node_id']: n for n in nodes}
    t = lambda i: by[i]['title']  # noqa: E731
    starts = [n['node_id'] for n in nodes if n['title'].startswith('StartsWith')]
    old_get = [n['node_id'] for n in nodes if n['title'] == 'Get bGraphicsDetected']
    old_set = [n['node_id'] for n in nodes if n['title'].startswith('Set bGraphicsDetected')]
    if not (starts or old_get or old_set):
        return
    e = next(n['node_id'] for n in nodes if n['title'] == 'AutoDetectGraphics')
    b = B(LIB, 'AutoDetectGraphics')
    if starts:
        projdir = [x['from_node'] for x in edges if x['to_node'] == starts[0]]
        sink = next((x['to_node'], x['to_pin']) for x in edges if x['from_node'] == starts[0])
        b.refs.add(sink[0])
        b.ops.append(dict(op='remove', node_ids=starts + projdir))
        b.link(packaged(b), 'ReturnValue', sink[0], sink[1])
    if old_get:
        sink = next((x['to_node'], x['to_pin']) for x in edges if x['from_node'] == old_get[0])
        b.refs.add(sink[0])
        b.ops.append(dict(op='remove', node_ids=old_get))
        done = b.fn(f'{KML}:GreaterEqual_IntInt', A=b.get('GraphicsDetectVersion', cls=SG_C, target=(e, 'Settings')), B=DETECT_VERSION)
        b.link(done, 'ReturnValue', sink[0], sink[1])
    if old_set:
        prev = next(x['from_node'] for x in edges if x['to_node'] == old_set[0] and x['to_pin'] == 'execute')
        nxt = next(x['to_node'] for x in edges if x['from_node'] == old_set[0] and x['from_pin'] == 'then')
        b.refs.update({prev, nxt, e})
        b.ops.append(dict(op='remove', node_ids=old_set))
        b.chain(prev, b.set('GraphicsDetectVersion', DETECT_VERSION, cls=SG_C, target=(e, 'Settings')), nxt)
    b.run()


def build():
    if 'GraphicsDetectVersion' not in {v['name'] for v in hc.call('blueprint_get_info', {'path': SG})['data'].get('variables', [])}:
        ok(hc.call('blueprint_add_variable', {'path': SG, 'variable_name': 'GraphicsDetectVersion', 'variable_type': 'int',
                                               'default_value': '0', 'category': 'Graphics'}), 'version')
        compile_bp(SG)
        print('SG', save(SG))
    if 'AutoDetectGraphics' in hc.call('blueprint_get_info', {'path': LIB})['data']['functions'] and not is_empty(LIB, 'AutoDetectGraphics'):
        shipping_gate_and_version()
    if 'AutoDetectGraphics' not in hc.call('blueprint_get_info', {'path': LIB})['data']['functions']:
        ok(hc.call('blueprint_add_function', {'path': LIB, 'function_name': 'AutoDetectGraphics',
                                               'inputs': [{'name': 'Settings', 'type': f'object:{SG_C}'},
                                                          {'name': 'bAllowInEditor', 'type': 'bool'}],
                                               'outputs': [{'name': 'Ran', 'type': 'bool'}],
                                               'locals': [{'name': 'bRan', 'type': 'bool', 'default_value': 'false'}]}), 'fn')
    if is_empty(LIB, 'AutoDetectGraphics'):
        nodes, _ = graph(LIB, 'AutoDetectGraphics')
        e = next(n['node_id'] for n in nodes if n['title'] == 'AutoDetectGraphics')
        ret = next(n['node_id'] for n in nodes if n['title'].startswith('Return'))
        b = B(LIB, 'AutoDetectGraphics')
        gus = b.fn(f'{GUS}:GetGameUserSettings')   # impure: it has to sit on the exec path
        need = b.fn(f'{KML}:BooleanAND',
                    A=b.fn(f'{KML}:Not_PreBool', A=b.fn(f'{KML}:GreaterEqual_IntInt', B=DETECT_VERSION,
                                                        A=b.get('GraphicsDetectVersion', cls=SG_C, target=(e, 'Settings')))),
                    B=b.fn(f'{KML}:BooleanOR', A=(e, 'bAllowInEditor'), B=packaged(b)))
        keep = b.set('bRan', need)
        br = b.node('branch', {'Condition': b.get('bRan')})
        lvl = b.fn(f'{GUS}:GetOverallScalabilityLevel', self=gus)
        pick = b.fn(f'{KML}:SelectInt', A=b.fn(f'{GUS}:GetShadowQuality', self=gus), B=lvl,
                    bPickA=b.fn(f'{KML}:Less_IntInt', A=lvl, B=0))
        b.chain(e, gus, keep, br,
                b.fn(f'{GUS}:RunHardwareBenchmark', self=gus, WorkScale=10, CPUMultiplier=1.0, GPUMultiplier=1.0),
                b.fn(f'{GUS}:ApplyHardwareBenchmarkResults', self=gus),
                b.fn(f'{GUS}:SetOverallScalabilityLevel', self=gus, Value=pick),
                b.fn(f'{GUS}:ApplySettings', self=gus, bCheckForCommandLineOverrides=False),
                b.fn(f'{GUS}:SaveSettings', self=gus),
                b.set('GraphicsDetectVersion', DETECT_VERSION, cls=SG_C, target=(e, 'Settings')), ret)
        b.link(br, 'else', ret, 'execute')
        b.link(b.get('bRan')[0], 'bRan', ret, 'Ran')
        b.run()
    compile_bp(LIB)
    nodes, edges = graph(LIB, 'LoadAndApplySettings')
    if not any('AutoDetectGraphics' in n['title'].replace(' ', '') for n in nodes):
        load = next(n['node_id'] for n in nodes if n['title'].startswith('LoadSettings'))
        apply_ = next(n['node_id'] for n in nodes if n['title'].startswith('ApplySettings'))
        b = B(LIB, 'LoadAndApplySettings')
        det = b.fn(f'{LIB_C}:AutoDetectGraphics', Settings=(load, 'Settings'), bAllowInEditor=False)
        ran = b.node('branch', {'Condition': (det, 'Ran')})
        sv = b.fn(f'{LIB_C}:SaveSettings', Settings=(load, 'Settings'))
        b.ops.append(dict(op='disconnect', node_id=load, pin_name='then'))
        b.link(load, 'then', det, 'execute')
        b.chain(det, ran, sv, apply_)
        b.link(ran, 'else', apply_, 'execute')
        b.run()
    compile_bp(LIB)
    print('LIB', save(LIB))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[SG, LIB])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        build()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
