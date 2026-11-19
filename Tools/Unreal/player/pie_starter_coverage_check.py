"""Immediate real garment/starter-section proof; restores exact visibility and touches no input or camera."""
import json
import unreal

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world,'PIE required'
p=unreal.GameplayStatics.get_player_character(world,0)
assert p,'Player required'
starter=p.get_editor_property('StartOutfit')
parts={n:p.get_editor_property(n) for n in ('Shirt','Trousers')}
original_visibility={n:c.is_visible() for n,c in parts.items()}
original_sections=[starter.is_material_section_shown(i,0) for i in range(4)]
rows=[]
result='FAIL';error=None
try:
    for shirt,trousers in ((False,False),(True,False),(False,True),(True,True)):
        for name,visible in (('Shirt',shirt),('Trousers',trousers)):
            assert parts[name].get_num_materials()>0,(name,'Real garment mesh missing')
            parts[name].set_visibility(visible,False)
        p.call_method('RefreshStarterCoverage',())
        actual=[starter.is_material_section_shown(i,0) for i in range(4)]
        assert actual[:2]==[not shirt,not trousers],(shirt,trousers,actual)
        assert actual[2:]==original_sections[2:],('Footwear coverage changed',actual,original_sections)
        rows.append(dict(shirt=shirt,trousers=trousers,starter_sections=actual))
    result='PASS'
except Exception as exc:error=repr(exc)
finally:
    for name,visible in original_visibility.items():parts[name].set_visibility(visible,False)
    for i,shown in enumerate(original_sections):starter.show_material_section(i,-1,shown,0)
    assert {n:c.is_visible() for n,c in parts.items()}==original_visibility
    assert [starter.is_material_section_shown(i,0) for i in range(4)]==original_sections
    with open('P:/FoA/Saved/CharacterShots/starter_coverage_runtime.json','w') as f:
        json.dump(dict(result=result,error=error,rows=rows,restored=True),f,indent=2)
print('STARTER COVERAGE',result,error or '')
