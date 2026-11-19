import math
import random
import unittest
import dream_ellipse as e
import ply_to_splatmesh as convert

class EllipseTest(unittest.TestCase):
    def test_isotropic_on_axis_retains_three_sigma(self):
        p=e.project((4,0,0,4,0,4),(0,0,100),(1,0,0),(0,1,0),(0,0,1))
        self.assertEqual(p,(4,0,4));self.assertEqual(e.ellipse(p)[:2],(6,6))
    def test_rotated_thin_source_plane_is_not_collapsed_to_geomean(self):
        q=(math.cos(math.pi/8),0,0,math.sin(math.pi/8))
        cov=e.covariance((4,1,.1),q)
        p=e.project(cov,(0,100,0),(1,0,0),(0,0,1),(0,1,0))
        major,minor,axis=e.ellipse(p)
        self.assertAlmostEqual(major,12);self.assertAlmostEqual(minor,3)
        self.assertAlmostEqual(abs(axis[0]),math.sqrt(.5));self.assertAlmostEqual(abs(axis[1]),math.sqrt(.5))
    def test_actor_nonuniform_scale_and_rotation(self):
        transform=((0,2,0),(-3,0,0),(0,0,.5))
        p=e.project((4,0,0,1,0,.04),(0,0,100),(1,0,0),(0,1,0),(0,0,1),transform)
        self.assertEqual(p,(9,0,16));self.assertEqual(e.ellipse(p)[:2],(12,9))
    def test_perspective_jacobian_off_axis_and_orthographic(self):
        self.assertEqual(e.project((4,0,0,4,0,4),(100,0,100),(1,0,0),(0,1,0),(0,0,1)),(8,0,4))
        self.assertEqual(e.project((4,0,0,4,0,4),(100,0,100),(1,0,0),(0,1,0),(0,0,1),perspective=False),(4,0,4))
        with self.assertRaises(ValueError):e.project((1,0,0,1,0,1),(0,0,-1),(1,0,0),(0,1,0),(0,0,1))
    def test_converter_packs_covariance_without_moving_or_recolouring_points(self):
        cols={k:[0.,0.] for k in convert.REQUIRED}
        cols.update(x=[1.,2.],y=[-1.,-2.],z=[3.,4.],opacity=[2.,3.],rot_0=[1.,1.])
        for i,s in enumerate((.04,.01,.001)):cols['scale_'+str(i)]=[math.log(s)]*2
        plain,_,_=convert.build(cols,[],[0,1],random.Random(1),origin=[0,0,0])
        full,_,info=convert.build(cols,[],[0,1],random.Random(1),origin=[0,0,0],covariance=True)
        for channel in ('POSITION','COLOR_0','TEXCOORD_0','TEXCOORD_1'):
            self.assertEqual(plain[channel],full[channel])
        packed=tuple(full[c][i] for c in ('TEXCOORD_2','TEXCOORD_3','TEXCOORD_4') for i in range(2))
        for actual,wanted in zip(packed,(16,0,0,.01,0,1)):self.assertAlmostEqual(actual,wanted,places=6)
        self.assertAlmostEqual(info['support_radius_cm_max'],12)
    def test_offscreen_near_plane_splat_cannot_expand_across_room(self):
        projected=e.project((4,0,0,4,0,4),(500,0,20),(1,0,0),(0,1,0),(0,0,1),
                            tan_half_fov=(1,.5625),near_clip=10)
        self.assertLess(e.ellipse(projected)[0],10)
        with self.assertRaises(ValueError):
            e.project((4,0,0,4,0,4),(500,0,2),(1,0,0),(0,1,0),(0,0,1),tan_half_fov=(1,.5625),near_clip=10)
    def test_in_frustum_covariance_remains_unchanged(self):
        args=((4,1,0,4,0,2),(10,5,100),(1,0,0),(0,1,0),(0,0,1))
        self.assertEqual(e.project(*args),e.project(*args,tan_half_fov=(1,.5625),near_clip=10))

if __name__=='__main__':unittest.main()
