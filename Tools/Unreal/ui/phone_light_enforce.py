"""BP_Phone.ApplyScreen (UCS + BeginPlay) also forces ScreenLight's values, so no placed copy can drift
(world 2026-11-10: Phone_Nightstand kept a default 5000-unit, 10 m, shadowed, 88 deg rect light; the glowing band across
his face, the blown-out arm and the hard light edges in the battle; A/B in Saved/WorldShots/perf/faceab2_sheet.png).
Values: 1.2 cd, 55 cm, no shadows, barn doors 70 deg x 20 cm, source 6.7 x 14.9 cm, specular 0.2, and the emitter 6 cm
out along the screen normal (main's option B, 2026-11-10): a rect light lights only its front half-space, so the hand
holding the phone falls behind it (ScreenShot00890: the back of the hand blew out at 2-4 cm). Existing setter nodes get
their pins updated, missing ones are appended; only nodes whose target is ScreenLight are touched.
  python Tools/Unreal/ui/phone_light_enforce.py        (quiet slot, PIE off; idempotent)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, save  # noqa: E402

P = '/Game/FoA/UI/Game/BP_Phone'
LL, LC, LCB, RL, SC = ('/Script/Engine.LocalLightComponent', '/Script/Engine.LightComponent', '/Script/Engine.LightComponentBase',
                       '/Script/Engine.RectLightComponent', '/Script/Engine.SceneComponent')
OUT = '(X=0.000000,Y=0.000000,Z=-7.200000)'  # was Z=-1.2; the light faces -Z (pitch -90), so -6 cm is out of the screen
SETS = [(f'{LL}:SetIntensityUnits', 'NewIntensityUnits', 'Candelas'), (f'{LC}:SetIntensity', 'NewIntensity', 1.2),
        (f'{LL}:SetAttenuationRadius', 'NewRadius', 55.0), (f'{LCB}:SetCastShadows', 'bNewValue', False),
        (f'{RL}:SetBarnDoorAngle', 'NewValue', 70.0), (f'{RL}:SetBarnDoorLength', 'NewValue', 20.0),
        (f'{RL}:SetSourceWidth', 'NewValue', 6.7), (f'{RL}:SetSourceHeight', 'NewValue', 14.9),
        # hair shades mostly specular? it does not: 0.2 left the hairline fan as it was (ScreenShot00881/882); kept, harmless
        (f'{LC}:SetSpecularScale', 'NewValue', 0.2),
        (f'{SC}:K2_SetRelativeLocation', 'NewLocation', OUT)]
TITLE = {'K2_SetRelativeLocation': 'SetRelativeLocation'}

assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
tok = editor_lock.acquire('ui', wait_s=120, ttl=90, areas=[P])
try:
    nodes, edges = graph(P, 'ApplyScreen')
    title = {n['node_id']: n['title'].replace(' ', '') for n in nodes}
    lights = {n['node_id'] for n in nodes if title[n['node_id']] in ('GetScreenLight', 'ScreenLight')}
    on_light = {title[e['to_node']]: e['to_node'] for e in edges if e['from_node'] in lights and e['to_pin'] == 'self'}
    b = B(P, 'ApplyScreen')
    todo = []
    for f, pin, v in SETS:
        name = f.split(':')[1]
        nid = on_light.get(TITLE.get(name, name))
        if nid:
            b.ops.append(dict(op='set_pin', node_id=nid, pin_name=pin, value=str(v).lower() if isinstance(v, bool) else str(v)))
        else:
            todo.append((f, pin, v))
    if todo:
        outs = {e['from_node'] for e in edges if e['from_pin'] == 'then'}
        tail = [n['node_id'] for n in nodes if any(p['name'] == 'then' for p in n['pins']) and n['node_id'] not in outs
                and title[n['node_id']] != 'ApplyScreen']
        assert len(tail) == 1, tail
        b.chain(tail[0], *[b.fn(f, self=b.get('ScreenLight'), **{pin: v}) for f, pin, v in todo])
    b.run()
    # the template matches what ApplyScreen enforces, so the editor view and a fresh placement agree
    r = hc.call('object_set_property', {'path': f'{P}.BP_Phone_C:ScreenLight_GEN_VARIABLE',
                                        'properties': {'RelativeLocation': OUT, 'Intensity': 1.2, 'SpecularScale': 0.2}})
    print('template', (r.get('data') or {}).get('applied'), r.get('error') or '')
    compile_bp(P)
    print('BP_Phone save', save(P))
finally:
    if tok:
        hc.release('ui', tok)
        editor_lock.forget('ui', tok)
