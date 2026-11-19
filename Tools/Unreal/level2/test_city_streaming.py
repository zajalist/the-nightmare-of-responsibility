"""Offline hysteresis, geometry residency and native graph ownership checks."""
import unittest
from unittest.mock import patch
import city_streaming as c
import build_drive as b
import build_threshold as t


class CityStreamingTests(unittest.TestCase):
    def test_cook_roots_stay_inside_packaging_section(self):
        from apply_city_streaming import cook_config
        source='[Other]\nValue=1\n[/Script/UnrealEd.ProjectPackagingSettings]\n+MapsToCook=(FilePath="/Game/FoA/Level2/Maps/L_L2_CityTest")\nbCookMapsOnly=False\n[Later]\nKeep=2\n'
        result=cook_config(source,[c.MASTER,c.package(0,0)])
        self.assertLess(result.index(c.MASTER),result.index('[Later]'))
        self.assertIn('Keep=2',result);self.assertNotIn('/L_L2_CityTest"',result)
        self.assertEqual(cook_config(result,[c.MASTER,c.package(0,0)]),result)

    def test_hysteresis_avoids_boundary_churn_and_eventually_unloads(self):
        loaded=False;states=[]
        for distance in (10000,8999,9001,8999,10500,11499,11500,10000,8999):
            loaded=c.wanted(distance,loaded);states.append(loaded)
        self.assertEqual(states,[False,True,True,True,True,True,False,False,True])
        self.assertEqual(c.box_distance((5000,0),(2500,2500,0)),0)
        self.assertEqual(c.cell_centre(0,0),(2500.,-27500.,0.))
        self.assertEqual(c.cell_centre(11,11),(57500.,27500.,0.))

    def test_weighted_continuous_budget_covers_all_cells_and_far_lod(self):
        meshes=[dict(name=f'n{x}_{y}',cell=x*12+y,cell_xy=[x,y],sector=[x,y],lod='near',splats=25000) for x in range(12) for y in range(12)]
        manifest=dict(meshes=meshes,overview=[dict(name='far',splats=80000,lod='far')])
        result=c.plan(manifest)
        self.assertEqual(len(result['sectors']),144)
        self.assertEqual(len({s['package'] for s in result['sectors']}),144)
        self.assertGreater(result['peaks']['retained']['points'],result['peaks']['load']['points'])
        self.assertGreater(result['budget_guard_cm'],500)
        self.assertLess(result['estimated_peak_wanted_gpu_geometry_bytes'],c.GPU_GEOMETRY_CEILING)
        self.assertIn('Pending unload/GC',result['estimate_scope'])
        with self.assertRaises(AssertionError):c.plan(dict(meshes=meshes,overview=[]))

    def test_graphs_release_references_and_do_not_accept_zero_controllers(self):
        plans=[]
        with patch.object(b,'inspect',lambda path,name:([dict(node_id='entry',title=name)],[])),patch.object(b.G,'run',lambda self:plans.append(self)):
            c.update();c.release();c.threshold_ready()
            with patch.object(t.D,'CITY_MAP',c.MASTER):t.land()
        by_name={p.graph:p.ops for p in plans}
        for name in ('UpdateSector','ReleaseSector'):
            self.assertTrue(any(o.get('function_name','').endswith(':SetIsRequestingUnloadAndRemoval') for o in by_name[name]))
            ops=by_name[name]
            setters=[o['ref'] for o in ops if o.get('node_type')=='variable_set' and o.get('variable_name')=='Stream']
            clears=[ref for ref in setters if not any(
                (o.get('node_id')==ref and o.get('pin_name')=='Stream') or
                (o.get('to_node')==ref and o.get('to_pin')=='Stream') for o in ops)]
            self.assertEqual(len(clears),1,'Null object reset uses an unconnected default pin')
            self.assertFalse(any(o.get('pin_name')=='Stream' and o.get('value')=='None' for o in ops))
            self.assertFalse(any('CollectGarbage' in o.get('function_name','') for o in by_name[name]))
        ready=by_name['CheckCitySectors']
        self.assertTrue(any(o.get('value')=='144' for o in ready))
        self.assertTrue(any(o.get('function_name','').endswith(':Add_IntInt') for o in ready))
        self.assertTrue(any(o.get('from_pin')=='Completed' and o.get('to_pin')=='execute' for o in ready))
        # A retry reuses controllers whose initial BootstrapPending was cleared.
        # Re-arm and synchronously refresh before trusting their old Ready flag.
        prewarm=next(o['node_id'] for o in ready if o.get('pin_name')=='BootstrapPending' and o.get('value')=='true')
        refresh=next(o['ref'] for o in ready if o.get('function_name','').endswith(':UpdateSector'))
        self.assertTrue(any(o.get('from_node')==prewarm and o.get('to_node')==refresh and o.get('to_pin')=='execute' for o in ready))
        self.assertTrue(any(o.get('from_node')==refresh and o.get('to_pin')=='execute' for o in ready))
        land=by_name['Land']
        self.assertTrue(any(o.get('function_name','').endswith(':CheckCitySectors') for o in land))
        self.assertTrue(any('landing timeout' in str(o.get('value','')) for o in land))
        # Every generated connection names a declared node and data pins have
        # one producer. These are plan checks, not claims of native compilation.
        for plan in plans:
            refs={'entry'};pins=set()
            for op in plan.ops:
                if op['op']=='add_node':refs.add(op['ref'])
                if op['op']=='connect':
                    self.assertIn(op['from_node'],refs);self.assertIn(op['to_node'],refs)
                    if op['to_pin'] not in ('execute','Exec'):
                        pin=(op['to_node'],op['to_pin']);self.assertNotIn(pin,pins);pins.add(pin)


if __name__=='__main__':unittest.main()
