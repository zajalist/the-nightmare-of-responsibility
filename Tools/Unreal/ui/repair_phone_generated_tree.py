"""Rebuild the missing generated phone widget tree without replacing its designer tree."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h

P = '/Game/FoA/UI/Game/WBP_Phone'

def call(cmd, **params):
    r = h.call(cmd, params)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('errors'), d
    return d

def main():
    assert not call('editor_get_state')['pie_running'], 'Wait for the user to stop Play'
    owner = h.agent_id()
    token = h.lease_acquire(owner, ['asset:' + P], ttl_s=60, wait_s=30)
    try:
        designer = P + '.WBP_Phone:WidgetTree'
        assert 'RootCanvas' in call('object_get_property', path=designer, names=['RootWidget'])['properties']['RootWidget']
        result = call('ui_compile_widget', widget_blueprint_path=P)
        print('PHONE_COMPILE', result)
        generated = call('object_get_property', path=P+'.WBP_Phone_C', names=['WidgetTree'])['properties']['WidgetTree']
        assert generated != 'None' and 'WidgetTree' in generated, generated
        root = call('object_get_property', path=P+'.WBP_Phone_C:WidgetTree', names=['RootWidget'])['properties']['RootWidget']
        assert root != 'None', root
        call('ui_save_widget', widget_blueprint_path=P)
        print('Generated phone tree restored; fresh P-open/read/close runtime proof still required')
    finally:
        h.release(owner, token)

if __name__ == '__main__': main()
