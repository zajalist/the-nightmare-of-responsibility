import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import prepare_city_density as density
import numpy as np

class DensityTest(unittest.TestCase):
    def test_facade_grid_stays_regular_under_budget_and_inside_surface(self):
        segments=[(0,0,50,0,0,12,1),(0,0,50,0,12,30,1)]
        step,count=density.facade_grid(segments,5000)
        points,radii,windows=density.facade_samples(segments,step,step)
        self.assertEqual(len(points),count);self.assertLessEqual(count,5000)
        self.assertTrue(np.all((points[:,0]>0)&(points[:,0]<50)))
        self.assertTrue(np.all(points[:,2]==0))
        self.assertTrue(np.all((points[:,1]>-.63)&(points[:,1]<29.37)))
        self.assertTrue(np.allclose(radii,step*1.75));self.assertTrue(windows.any())
        x=np.unique(points[:,0]);self.assertLessEqual(float(np.diff(x).max()),step+1e-9)
        with self.assertRaises(AssertionError):density.facade_grid(segments,1)

    def test_cell_clipping_preserves_adjacent_facade_endpoints(self):
        left=density.clip_segment((-10,3),(110,3),(0,0,50,50))
        right=density.clip_segment((-10,3),(110,3),(50,0,100,50))
        self.assertEqual(left,(0,3,50,3));self.assertEqual(right,(50,3,100,3))
        self.assertIsNone(density.clip_segment((0,51),(100,51),(0,0,50,50)))

    def test_overlapping_footprints_cover_the_surface_without_mesh_backing(self):
        import math
        for hardness in (.7,2.):
            for ix in range(11):
                for iy in range(11):
                    hole=1.
                    for x in range(-3,4):
                        for y in range(-3,4):
                            r2=((ix/10-x)/1.75)**2+((iy/10-y)/1.75)**2
                            alpha=max(0,(math.exp(-hardness*r2)-math.exp(-hardness))/(1-math.exp(-hardness)))
                            hole*=1-alpha
                    self.assertGreater(1-hole,.993)

    def test_new_points_are_genuine_unique_and_old_silhouette_is_retained(self):
        raw=np.zeros(80,density.base.POINT)
        raw['u']=np.arange(80)*.4;raw['z']=np.arange(80)%5;raw['cls']=6;raw['bid']=17
        old=np.zeros(8,density.base.SAMPLE)
        for key in density.base.POINT.names:old[key]=raw[::10][key]
        new=density.enrich(old,raw,24,7)
        self.assertEqual(len(new),24)
        self.assertTrue(np.isin(old['u'],new['u']).all())
        self.assertTrue(np.isin(new['u'],raw['u']).all())
        self.assertEqual(len(np.unique(density.voxel_keys(new))),len(new))
        self.assertTrue(np.array_equal(new,density.enrich(old,raw,24,7)))

if __name__=='__main__':unittest.main()
