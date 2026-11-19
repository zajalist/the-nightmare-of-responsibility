"""First-person opening stays ahead of the torso while turning toward the wardrobe."""
import math

D0=(330.,80.,92.)
HANDLE=(375.,62.,100.)
TOP=(224.,236.,205.)


def opening_keys():
    facing=math.atan2(TOP[1]-D0[1],TOP[0]-D0[0])
    keys=[]
    for frame in range(70):
        t=frame/30
        turn=max(0.,min(1.,(t-.6)/.5));turn=turn*turn*(3-2*turn)
        stumble=max(0.,min(1.,(t-2.)/.3))
        yaw=facing*turn;radius=32.+12.*stumble
        eye=(D0[0]+radius*math.cos(yaw),D0[1]+radius*math.sin(yaw),166.-22.*stumble)
        aim=tuple(a+(b-a)*turn for a,b in zip(HANDLE,TOP))
        if stumble:aim=tuple(a+(b-a)*stumble for a,b in zip(TOP,(224.,160.,150.)))
        keys.append((t,eye,aim))
    return keys


if __name__=='__main__':
    keys=opening_keys();assert keys[0][0]==0 and abs(keys[-1][0]-2.3)<1e-8
    for _,eye,aim in keys:
        assert math.hypot(eye[0]-D0[0],eye[1]-D0[1])>=31.99
        assert eye[0]<370 and 143<=eye[2]<=166
        assert sum((a-b)**2 for a,b in zip(eye,aim))>100
    print('Wardrobe opening:70 frames outside torso, clear of door wall')
