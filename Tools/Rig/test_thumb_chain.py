"""Headless Blender regression: an unreachable target must not reverse either thumb hinge."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Rig')
from mathutils import Vector, Quaternion
from grip_twin import thumb_chain
import math


class Hand:
    def __init__(self, side):
        self.names = [f'thumb_0{j}_{side}' for j in (1,2,3)]
        self.axes = {b:{'n':Vector((0,0,1))} for b in self.names}
        self.dirs = {b:Vector((0,1,0)) for b in self.names}
        self.aimed = []

    def head(self,b): return Vector((0,self.names.index(b),0))
    def dir(self,b): return self.dirs[b]
    def world(self,b,v): return v
    def aim(self,b,v):
        self.aimed.append(b)
        self.dirs[b] = v.normalized()
    def rot(self,b,axis,angle): pass
    def flex(self,b,angle):
        axis = self.dirs[b].cross(self.axes[b]['n']).normalized()
        self.dirs[b] = Quaternion(axis,math.radians(angle)) @ self.dirs[b]


for side in ('l','r'):
    old = Hand(side)
    old.aim(f'thumb_02_{side}',Vector((0,1,-1)))
    old.aim(f'thumb_03_{side}',Vector((0,1,-1)))
    assert all(old.dirs[b].z < 0 for b in old.names[1:]), 'negative control did not hyperextend'
    h = Hand(side)
    thumb_chain(h,side,Vector((0,1,0)),Vector((0,2,-1)),Vector((0,1,-1)),0)
    assert h.aimed == [f'thumb_01_{side}'], 'a hinge was free-aimed'
    assert all(h.dirs[b].z > 0 for b in h.names[1:]), 'thumb hyperextended'
print('THUMB_CHAIN regression passed for left and right; unreachable targets preserve palmward flexion')
