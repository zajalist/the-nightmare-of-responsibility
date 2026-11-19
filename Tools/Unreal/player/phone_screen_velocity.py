"""playercam lane (perf lane's find 2026-11-18: the raised phone's text smears under TSR, "Today" reads "Troag").
The phone screen is a WidgetComponent drawn through M_UI_PhoneScreen (Masked, Unlit). The phone rides the hand in the
camera's frame, but that masked primitive writes no usable velocity, so TSR reprojects its pixels like static room and the
text ghosts whenever the camera moves. M_UI_PhoneScreen becomes Translucent with Output Depth and Velocity (the engine's
own recipe for widgets that must stay sharp under camera motion, Widget3DPassThrough_Translucent_OutputDepthAndVelocity),
and Allow Custom Depth Writes so the screen keeps stencil 200 against the dream echo post process. The phone_glass Custom
node is unchanged: its mask output moves from Opacity Mask to Opacity. BP_Phone.ApplyScreen keeps assigning this material.
Hayba material tools only. Idempotent. Inside an asset lease on M_UI_PhoneScreen:
  $env:HAYBA_AGENT_ID='playercam'; python Tools/Unreal/player/phone_screen_velocity.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

M = '/Game/FoA/UI/Materials/M_UI_PhoneScreen'
MASK = 'MaterialExpressionComponentMask_1'


def ok(r, what):
    assert r.get('ok', True) and not r.get('error'), (what, json.dumps(r)[:600])
    return r


def run():
    info = ok(h.call('material_get_info', dict(path=M)), 'info')
    data = info.get('data') or info
    outs = {o['property']: o for o in data['material_outputs']}
    if outs['OpacityMask']['connected']:
        ok(h.call('material_disconnect', dict(material_path=M, to_property='opacity_mask')), 'disconnect mask')
    if not outs['Opacity']['connected']:
        ok(h.call('material_connect_nodes', dict(material_path=M, from_node=MASK, from_output_index=0, to_property='opacity')), 'opacity')
    print(ok(h.call('material_set_property', dict(material_path=M, properties={'blend_mode': 'Translucent'})), 'blend'))
    print(ok(h.call('object_set_property', dict(path=M, properties={'bOutputTranslucentVelocity': True,
                                                                     'AllowTranslucentCustomDepthWrites': True})), 'flags'))
    v = ok(h.call('material_validate', dict(material_path=M, compile=True)), 'validate')
    print(v)
    assert (v.get('data') or v).get('ok', True), v
    print(json.dumps(ok(h.call('material_compile', dict(material_path=M)), 'compile'))[:800])


if __name__ == '__main__':
    run()
