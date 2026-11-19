"""Read-only: the facts behind the 02:02 PIE frames. For M_PP_MenuV31: domain, blendable location and priority.
For M_UI_SandText and M_UI_Scrim: domain, blend, and every parameter node's class and name (is Ink an MPC read?).
Run via ue_remote.py with FOA_AREAS=/Game/FoA/UI/Menu (or any UI asset path)."""
import unreal


def main():
    for path in ('/Game/FoA/UI/Menu/M_PP_MenuV31', '/Game/FoA/UI/Materials/M_UI_SandText', '/Game/FoA/UI/Materials/M_UI_Scrim'):
        m = unreal.load_asset(path)
        if not m:
            print('MISSING', path)
            continue
        print(path); print('  domain', m.get_editor_property('material_domain')); print('  blend', m.get_editor_property('blend_mode'),
              'location', m.get_editor_property('blendable_location'), 'priority', m.get_editor_property('blendable_priority'))
        for e in unreal.MaterialEditingLibrary.get_material_expressions(m) if hasattr(unreal.MaterialEditingLibrary, 'get_material_expressions') else []:
            cls = e.get_class().get_name()
            if 'Parameter' in cls:
                name = e.get_editor_property('parameter_name')
                extra = e.get_editor_property('collection').get_name() if cls == 'MaterialExpressionCollectionParameter' and e.get_editor_property('collection') else ''
                print('   ', cls, name, extra)


main()
