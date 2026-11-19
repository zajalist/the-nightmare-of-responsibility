"""Grow combed strands from short01's cap, constrained by its continuous outer envelope.
Preserve the body mask: MakeHuman fitting helpers are not scalp geometry.
"""
import bpy
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree



def continuous_shell(shell):
    """Rasterize the outer card envelope; bridge card gaps before clipping strands to it."""
    obj = shell.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = obj.to_mesh()
    me.calc_loop_triangles()
    xyz = np.array([tuple(shell.matrix_world @ v.co) for v in me.vertices])
    centre = (xyz.min(0) + xyz.max(0)) * 0.5
    # Centre below the crown so each scalp direction intersects the hairstyle once.
    centre[2] -= 0.035
    samples = []
    for tri in me.loop_triangles:
        a, b, c = xyz[list(tri.vertices)]
        for i in range(7):
            for j in range(7-i):
                samples.append(a + (b-a)*(i/6) + (c-a)*(j/6))
    obj.to_mesh_clear()
    delta = np.asarray(samples) - centre
    radius = np.linalg.norm(delta, axis=1)
    u = ((np.arctan2(delta[:,1],delta[:,0]) / (2*np.pi) + .5) * 128).astype(int) % 128
    v = np.clip(((np.arccos(np.clip(delta[:,2]/radius,-1,1)) / np.pi)*64).astype(int),0,63)
    field = np.zeros((64,128))
    np.maximum.at(field,(v,u),radius)
    for _ in range(4):
        neighbours = [np.roll(field,k,axis) for axis in (0,1) for k in (-1,1)]
        count = sum(n > 0 for n in neighbours)
        fill = sum(neighbours) / np.maximum(count,1)
        field = np.where((field == 0) & (count > 0), fill, field)
    valid = field > 0
    for _ in range(3):
        valid &= np.logical_and.reduce([np.roll(valid,k,axis) for axis in (0,1) for k in (-1,1)])
    for _ in range(4):
        neighbours = [np.roll(field,k,axis) for axis in (0,1) for k in (-1,1)]
        field = np.where(valid,(field*4 + sum(neighbours))/(4+sum(n>0 for n in neighbours)),0)
    assert np.isfinite(field).all() and valid.any()

    origin = Vector(centre)
    def clearance(base, normal):
        d = base - origin
        r = d.length
        fx = (math.atan2(d.y,d.x)/math.tau+.5)*128
        fy = min(63.,max(0.,math.acos(max(-1,min(1,d.z/r)))/math.pi*64))
        x,y = int(fx)%128,int(fy)
        if not valid[y,x]:
            return None
        ax,ay = fx-int(fx),fy-y
        samples = [(field[y,x],(1-ax)*(1-ay)), (field[y,(x+1)%128],ax*(1-ay)),
                   (field[min(63,y+1),x],(1-ax)*ay), (field[min(63,y+1),(x+1)%128],ax*ay)]
        radius = sum(v*w for v,w in samples if v>0)/max(1e-9,sum(w for v,w in samples if v>0))
        return max(.0015,float(radius-r))
    clearance.origin = origin
    return clearance


def tree_of(obj, skip_masks=False):
    masks = [m for m in obj.modifiers if m.type == "MASK" and m.show_viewport and m.vertex_group != "body"] if skip_masks else []
    for m in masks:
        m.show_viewport = False
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = [obj.matrix_world @ v.co for v in me.vertices]
    tree = BVHTree.FromPolygons(co, [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    for m in masks:
        m.show_viewport = True
    return tree


def comb_shell(body, hair, shell, count=32000):
    """Grow strands from short01's continuous cap, following its scalp and outer envelope."""
    scalp = tree_of(body, skip_masks=True)
    clearance = continuous_shell(shell)
    ev = shell.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    me.calc_loop_triangles()
    neighbours = {v.index:set() for v in me.vertices}
    for edge in me.edges:
        a,b = edge.vertices
        neighbours[a].add(b); neighbours[b].add(a)
    remaining = set(neighbours)
    islands = []
    while remaining:
        todo = [remaining.pop()]; island = set(todo)
        while todo:
            for n in neighbours[todo.pop()] & remaining:
                remaining.remove(n); island.add(n); todo.append(n)
        islands.append(island)
    cap = max(islands,key=len)
    tris = np.array([[tuple(shell.matrix_world @ me.vertices[i].co) for i in t.vertices]
                     for t in me.loop_triangles if t.vertices[0] in cap])
    ev.to_mesh_clear()
    areas = np.linalg.norm(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]),axis=1)
    rng = np.random.default_rng(83)
    chosen = tris[rng.choice(len(tris),count,p=areas/areas.sum())]
    uv = rng.random((count,2)); uv[uv.sum(1)>1] = 1-uv[uv.sum(1)>1]
    seeds = chosen[:,0]+uv[:,0,None]*(chosen[:,1]-chosen[:,0])+uv[:,1,None]*(chosen[:,2]-chosen[:,0])
    points=[]; radii=[]; sizes=[]
    mwi = hair.matrix_world.inverted()
    for seed in seeds:
        root,nrm,_,_ = scalp.find_nearest(Vector(seed))
        if root is None or clearance(root,nrm) is None:
            continue
        top = max(0,min(1,(nrm.z-.15)/.65))
        length = (.028 + .055*top) * rng.uniform(.85,1.15)
        p = root.copy(); strand=[]
        twist = rng.uniform(-.12,.12)
        for j in range(18):
            base,normal,_,_ = scalp.find_nearest(p)
            radial = base-clearance.origin
            radial.x *= 1.4
            radial.z *= .7
            radial.normalize()
            normal = (normal*.2+radial*.8).normalized()
            room = clearance(base,normal)
            if room is None:
                break
            t=j/17
            height = max(.0004,room-.0015) * math.sin(t*math.pi*.5)
            strand.append(base+normal*height)
            blend = max(0,min(1,(normal.z-.15)/.65))
            direction = Vector((-.12+twist,blend,-(1-blend)))
            direction -= normal*direction.dot(normal)
            if direction.length < .01:
                direction = Vector((0,1,0))
            direction.normalize()
            p=base+direction*(length/17)
        if len(strand)<3:
            continue
        sizes.append(len(strand))
        for j,p in enumerate(strand):
            points.append(tuple(mwi @ p))
            radii.append(.00012 * (1 - .8*j/max(1,len(strand)-1)))
    assert len(sizes)>count*.7, (len(sizes),count)
    data=bpy.data.hair_curves.new('Short01_Combed')
    data.add_curves(sizes)
    data.attributes['position'].data.foreach_set('vector',np.asarray(points,dtype=np.float32).ravel())
    radius=data.attributes.get('radius') or data.attributes.new('radius','FLOAT','POINT')
    radius.data.foreach_set('value',np.asarray(radii,dtype=np.float32))
    old=hair.data
    for mat in old.materials:
        data.materials.append(mat)
    hair.data=data
    bpy.data.hair_curves.remove(old)
    print('COMBED_SHELL',len(sizes),'curves',len(points),'points')
