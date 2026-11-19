import json,re
from pathlib import Path
from scipy.spatial.transform import Rotation as R
d=json.loads(Path('Saved/Integration/active_hand_clips.json').read_text())
def q(s):return [float(x) for x in re.search(r'Rotation=\(X=([^,]+),Y=([^,]+),Z=([^,]+),W=([^)]+)',s).groups()]
for name,row in d.items():
 print(name.rsplit('/',1)[1])
 for side in ('l','r'):
  print(side,[(f,[round((R.from_quat(q(row['bones'][f+'_'+j+'_'+side]['ref'])).inv()*R.from_quat(q(row['bones'][f+'_'+j+'_'+side]['local']))).magnitude()*180/3.14159265,1) for j in ('01','02','03')]) for f in ('thumb','index','middle','ring','pinky')])
