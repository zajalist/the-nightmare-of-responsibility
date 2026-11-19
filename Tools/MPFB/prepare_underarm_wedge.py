"""Fair only the projected front-underarm wedge in actual seated pose; preserve weights."""
from pathlib import Path
source=Path('P:/FoA/Tools/MPFB/prepare_underarm_fit.py').read_text()
source=source.replace('protected=(abs(x)<.20)&(y<-.055)&(z<1.48)','protected=abs(x)<=.14')
source=source.replace("select=(abs(x)>.13)&(abs(x)<.26)&(abs(y)<.10)&(z>1.30)&(z<1.49)&~protected", "select=(abs(x)>.14)&(abs(x)<.225)&(y<-.035)&(y>-.125)&(z>1.385)&(z<1.485)&~protected")
source=source.replace("records['rest']=references", "records['rest']=references\nedge=json.loads(Path('P:/FoA/Saved/CharacterShots/wake_handoff/20261108_111013/bed_edge_body_pose.json').read_text())\nrecords['bed_edge']={r['name']:matrix(r['position'],r['rotation'],r['scale']) for r in edge['bones']}")
insert='''
# The measured image wedge is centred near |x|17.2,y-9,z144cm. Neighbour
# averaging occurs in this actual seated pose, then each correction is inverse-skinned.
adj=[set() for _ in points]
for edge in shirt.data.edges:
    a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
all_blends=np.array([sum((g.weight*bone_mats[group_names[g.group]] for g in v.groups if g.group in group_names),np.zeros((4,4))) for v in shirt.data.vertices])
def ramp(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
fade=ramp(.14,.16,abs(x))*(1-ramp(.205,.225,abs(x)))*ramp(1.385,1.41,z)*(1-ramp(1.46,1.485,z))*ramp(.035,.06,-y)
for iteration in range(18):
    posed=np.einsum('nij,nj->ni',all_blends,np.c_[after,np.ones(len(after))])[:,:3]
    delta=np.zeros_like(after)
    for i in ids:
        if adj[i]:
            desired=(posed[list(adj[i])].mean(0)-posed[i])*.38*fade[i]
            delta[i]=np.linalg.solve(all_blends[i,:3,:3],desired)
    after+=delta
    shift=after-points;length=np.linalg.norm(shift,axis=1);over=length>.008
    shift[over]*=(.008/length[over])[:,None];after=points+shift
'''
source=source.replace('before=measure(points)','before=measure(points)\n'+insert)
source=source.replace('length>.020','length>.008').replace('(.020/length[over])','(.008/length[over])')
source=source.replace('foa_teen_underarm_review.blend','foa_teen_underarm_wedge_review.blend').replace('/underarm_candidate','/underarm_wedge_candidate')
source=source.replace("'source':'foa_teen_shoulder_review.blend'","'source':'foa_teen_underarm_weights_review.blend'")
exec(compile(source,'prepare_underarm_fit.py','exec'),globals())
