"""Text FX kit on the intro story's lines (WBP_IntroStory Txt_Sub, "Seventeen days. Not that anyone's counting."):
each panel's line gathers from sand over 1.1 s while the panel fades in. In place, idempotent:
  python Tools/Unreal/ui/textfx/intro_sand.py tree    Cvs_Root > Ret_Sub (RetainerBox, Txt_Sub's old canvas slot) > Txt_Sub
  python Tools/Unreal/ui/textfx/intro_sand.py graph   UpdateFrame's tail: Reveal = easeOut4(clamp(PanelTime / 1.1))
The panel fade (UpdateFrame sets Txt_Sub's render opacity) is unchanged: it fades the text inside the retainer."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock  # noqa: E402
import hayba_call as hc  # noqa: E402
from hayba_batch import B, compile_bp, graph, ok, save  # noqa: E402

P = '/Game/FoA/UI/Intro/WBP_IntroStory'
MI = '/Game/FoA/UI/Materials/MI_UI_SandText_HUD.MI_UI_SandText_HUD'
KML, MID, RB = '/Script/Engine.KismetMathLibrary', '/Script/Engine.MaterialInstanceDynamic', '/Script/UMG.RetainerBox'
STEP = sys.argv[1] if len(sys.argv) > 1 else ''


def tree():
    if 'Ret_Sub' not in str(hc.call('ui_query', {'path': P}).get('data')):
        ok(hc.call('ui_add_element', {'widget_blueprint_path': P, 'child_class': 'RetainerBox', 'parent_widget_name': 'Cvs_Root',
                                      'name': 'Ret_Sub', 'slot_props': {'anchors_min': [0.12, 1], 'anchors_max': [0.88, 1],
                                                                        'alignment': [0, 0], 'position': [0, -170],
                                                                        'size': [0, 100], 'z_order': 7}}), 'retainer')
        ok(hc.call('ui_reparent_element', {'widget_blueprint_path': P, 'widget_name': 'Txt_Sub', 'new_parent_name': 'Ret_Sub'}), 'text')
        ok(hc.call('ui_set_variable', {'widget_blueprint_path': P, 'widget_name': 'Ret_Sub', 'is_variable': True}), 'var')
    r = hc.call('ui_set_widget_properties', {'widget_blueprint_path': P, 'widget_name': 'Ret_Sub', 'properties': {
        'EffectMaterial': MI, 'TextureParameter': 'Texture', 'Visibility': 'HitTestInvisible'}})
    assert r.get('ok') and not (r.get('data') or {}).get('failed_properties'), r
    compile_bp(P, widget=True)
    print('tree', save(P))


def graph_step():
    nodes, edges = graph(P, 'UpdateFrame')
    if any(n['title'].startswith('SetScalarParameterValue') for n in nodes):
        print('already hooked')
        return
    outs = {(e['from_node'], e['from_pin']) for e in edges}
    tail = [n['node_id'] for n in nodes if any(p['name'] == 'then' and p.get('direction') == 'output' for p in n['pins'])
            and (n['node_id'], 'then') not in outs and not n['title'].startswith('Branch')]
    assert len(tail) == 1, tail
    b = B(P, 'UpdateFrame')
    rev = b.fn(f'{KML}:Ease', A=0.0, B=1.0, EasingFunc='EaseOut', BlendExp=4.0, Alpha=b.fn(
        f'{KML}:FClamp', Value=b.fn(f'{KML}:Divide_DoubleDouble', A=b.get('PanelTime'), B=1.1), Min=0.0, Max=1.0))
    b.chain(tail[0], b.fn(f'{MID}:SetScalarParameterValue', self=b.fn(f'{RB}:GetEffectMaterial', self=b.get('Ret_Sub')),
                          ParameterName='Reveal', Value=rev))
    b.run()
    compile_bp(P, widget=True)
    print('graph', save(P))


if __name__ == '__main__':
    token = editor_lock.acquire('ui', wait_s=900, ttl=180, areas=[P])
    try:
        assert not hc.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
        {'tree': tree, 'graph': graph_step}[STEP]()
    finally:
        if token:
            hc.release('ui', token)
            editor_lock.forget('ui', token)
