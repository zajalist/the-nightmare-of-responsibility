"""Read-only helper for pp_monotone_code.py: write MF_Dream_MonoTone's live Custom node code to OUT."""
import os

import unreal

P = '/Game/FoA/PostProcess/Functions/MF_Dream_MonoTone'
unreal.load_asset(P)
node = unreal.find_object(None, P + '.MF_Dream_MonoTone:MaterialExpressionCustom_2')
open(os.environ['OUT'], 'w', encoding='utf-8').write(node.get_editor_property('code'))
print('read', len(node.get_editor_property('code')))
