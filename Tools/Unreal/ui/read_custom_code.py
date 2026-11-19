"""Read-only: write the HLSL of every Custom node in FOA_ASSETS (materials or material functions) to
Saved/UIShots/aaa/custom_code.txt (ue_remote truncates printed output)."""
import os
import unreal

MEL = unreal.MaterialEditingLibrary
out = []
for p in [s for s in os.environ.get('FOA_ASSETS', '').split(',') if s]:
    a = unreal.load_asset(p)
    ex = MEL.get_material_function_expressions(a) if isinstance(a, unreal.MaterialFunction) else MEL.get_material_expressions(a)
    for e in ex:
        if isinstance(e, unreal.MaterialExpressionCustom):
            out.append('===== %s %s %s\n%s\n' % (p, e.get_name(), e.get_editor_property('description'),
                                                  e.get_editor_property('code')))
open('P:/FoA/Saved/UIShots/aaa/custom_code.txt', 'w', encoding='utf-8').write(''.join(out))
print('wrote', len(out))
