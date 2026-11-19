"""WBP_SandLine root canvas (a root cannot be replaced in Hayba): Ret_Line stretches over it with AutoSize on, so the
canvas desires the text's size (SConstraintCanvas::ComputeDesiredSize) and the line still fills and wraps in a host slot."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal'); sys.path.insert(0, 'P:/FoA/Tools/Unreal/ui')
import editor_lock, hayba_call as hc
from hayba_batch import compile_bp, ok, save
WBP = '/Game/FoA/UI/Widgets/Common/WBP_SandLine'
tok = editor_lock.acquire('ui', wait_s=300, ttl=120, areas=[WBP])
try:
    ok(hc.call('ui_set_widget_properties', {'widget_blueprint_path': WBP, 'widget_name': 'Ret_Line',
        'slot_props': {'anchors_min': [0, 0], 'anchors_max': [1, 1], 'position': [0, 0], 'size': [0, 0], 'auto_size': True}}), 'slot')
    compile_bp(WBP, widget=True); print('saved', save(WBP))
finally:
    if tok: hc.release('ui', tok); editor_lock.forget('ui', tok)
