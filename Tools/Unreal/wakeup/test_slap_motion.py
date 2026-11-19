"""Offline trajectory guard; live Teen contact and rendered acting remain required."""
import json
from pathlib import Path
import wake_math as m
from slap_motion import sample
from wake_cues import T


def main():
    assert abs(T['edge']+T['edge_hold']+1.5-25.3)<1e-6
    assert abs(T['edge']+T['edge_hold']+T['edge_reach']+T['edge_breath']-29.4)<1e-6
    rows=[]
    for f,u in [((1,0,0),(0,0,1)),((0,0,1),(0,1,0))]:
        start=m.mul(f,-48)
        contact=m.mul(u,28)
        points=[sample(i/120,start,contact,f,u)[0] for i in range(457)]
        assert m.length(m.sub(sample(1.5,start,contact,f,u)[0],contact))<1e-7
        assert m.length(m.sub(points[0],start))<1e-7
        assert m.length(m.sub(points[-1],start))<1e-7
        # Samples on either side of every phase boundary must not jump.
        for t in (.30,.80,1.22,1.38,1.5,1.56,1.66,1.95,2.35,2.72,3.05,3.5):
            a=sample(t-1e-6,start,contact,f,u)[0]
            b=sample(t+1e-6,start,contact,f,u)[0]
            assert m.length(m.sub(a,b))<.001,(t,a,b)
        assert abs(sample(1.5,start,contact,f,u)[1])<1e-7
        assert abs(sample(.30,start,contact,f,u)[1])<1e-7
        assert abs(m.dot(m.sub(sample(1.22,start,contact,f,u)[0],contact),u)-22)<1e-7  # high apex: a slap from the top
        assert abs(m.dot(m.sub(sample(2.35,start,contact,f,u)[0],contact),u)+8.5)<1e-7
        assert abs(m.dot(m.sub(sample(1.56,start,contact,f,u)[0],contact),u)+5)<1e-7  # impact: 5 cm into the clock
        # The palm moves vertically through the strike, give and collapse.
        for t in (1.38,1.5,1.56,1.66,1.95,2.35):
            assert abs(m.dot(m.sub(sample(t,start,contact,f,u)[0],contact),f))<1e-6
        max_step=max(m.length(m.sub(a,b)) for a,b in zip(points,points[1:]))
        assert max_step<3.5,max_step  # the strike and the drive-in peak near 3.2 m/s; nothing else comes close
        impact=m.length(m.sub(sample(1.5,start,contact,f,u)[0],sample(1.5-1/120,start,contact,f,u)[0]))*120
        assert impact>250,('slap too soft at contact, cm/s',impact)
        rows.append({'up':u,'max_step_cm_at120Hz':max_step,'contact_time':25.3})
    out=Path('P:/FoA/Saved/AnimShots/slap_trajectory_verified.json')
    out.write_text(json.dumps({'offline_only':True,'cases':rows,'live_teen_contact_verified':False},indent=2))
    print(out)


if __name__=='__main__':
    main()
