"""Reuse the prior FBX contract with zero allowed weight changes and8mm cap."""
from pathlib import Path
s=Path('P:/FoA/Tools/MPFB/check_underarm_fbx.py').read_text()
s=s.replace('underarm_weights_candidate','underarm_wedge_candidate').replace("('teen_shoulder','teen_underarm')","('teen_underarm','teen_underarm_wedge')")
s=s.replace("allowed=set(report['local_weights']['changed_weight_vertex_ids']);changed=set()",'allowed=set();changed=set()')
s=s.replace('delta.max()<1.202','delta.max()<.801').replace('central_chest_unchanged=True','central_chest_unchanged=True,weights_unchanged=True')
exec(compile(s,'check_underarm_fbx.py','exec'),globals())
