"""Wave crossing and finite swept nudge contracts; no editor access."""
import unittest
from unittest.mock import patch
import build_drive as b
import car_shockwave as wave
import drive_data as d


class ShockwaveTests(unittest.TestCase):
    def run_wave(self, distance, dt=1/60, count=300):
        state=wave.State(); displacement=0.; triggers=0
        for i in range(count):
            state,delta,fired=wave.advance(state,stamp=10.,age=i*dt,distance=distance,dt=dt)
            displacement+=delta;triggers+=fired
        return state,displacement,triggers

    def test_one_crossing_and_complete_decay_at_different_frame_rates(self):
        for dt in (1/120,1/60,1/30,.1):
            state,moved,triggers=self.run_wave(900.,dt,int(5/dt))
            self.assertEqual(triggers,1)
            self.assertAlmostEqual(moved,7.5,places=5)
            self.assertEqual(state.speed,0.)

    def test_no_push_outside_wave_lifetime_or_without_radial_direction(self):
        for distance in (0.,1.,d.SHOCKWAVE_SPEED*d.SHOCKWAVE_DURATION+1):
            _,moved,triggers=self.run_wave(distance)
            self.assertEqual((moved,triggers),(0.,0))
        state,delta,fired=wave.advance(wave.State(),stamp=10.,age=-1.,distance=10.,dt=.1)
        self.assertEqual((delta,fired),(0.,False))

    def test_leaving_and_reentering_the_same_wave_cannot_retrigger(self):
        state=wave.State(); triggers=0
        for age,distance in ((.1,900),(.57,900),(.6,5000),(.7,100),(.8,5000),(.9,100)):
            state,_,fired=wave.advance(state,stamp=10.,age=age,distance=distance,dt=.1)
            triggers+=fired
        self.assertEqual(triggers,1)
        state,_,fired=wave.advance(state,stamp=20.,age=.2,distance=100.,dt=.1)
        self.assertTrue(fired)
        self.assertLessEqual(state.speed,d.SHOCKWAVE_NUDGE_SPEED)

    def test_push_begins_after_the_visible_front_has_arrived(self):
        state,_,fired=wave.advance(wave.State(),stamp=10.,age=.5,distance=900.,dt=.016)
        self.assertFalse(fired)
        state,_,fired=wave.advance(state,stamp=10.,age=.563,distance=900.,dt=.016)
        self.assertTrue(fired)

    def test_hitch_is_bounded_and_impulses_do_not_accumulate(self):
        state=wave.State(); moved=0.
        for stamp in (10.,20.,30.,40.):
            state,delta,_=wave.advance(state,stamp=stamp,age=.2,distance=100.,dt=10.)
            moved+=delta
            self.assertLessEqual(state.speed,d.SHOCKWAVE_NUDGE_SPEED)
            self.assertLessEqual(delta,6.)
        for _ in range(10):
            state,delta,_=wave.advance(state,stamp=40.,age=4.,distance=100.,dt=.1)
            moved+=delta
        self.assertEqual(state.speed,0.)
        self.assertLessEqual(moved,4*7.5)

    def test_native_plan_uses_existing_sweep_and_keeps_cost_logic_separate(self):
        import free_drive
        plans=[]
        with patch.object(b,'inspect',lambda path,name:([dict(node_id='entry',title=name)],[])), patch.object(b.G,'run',lambda self:plans.append(self)):
            wave.update();wave.reset();free_drive.move()
        by_name={p.graph:p.ops for p in plans}
        functions=[o.get('function_name','') for o in by_name['UpdateShockwave']]
        self.assertTrue(any(x.endswith(':GetVectorParameterValue') for x in functions))
        read=next(o['ref'] for o in by_name['UpdateShockwave'] if o.get('function_name','').endswith(':GetVectorParameterValue'))
        self.assertTrue(any(o.get('op')=='connect' and o.get('to_node')==read and o.get('to_pin')=='execute' for o in by_name['UpdateShockwave']))
        self.assertFalse(any('ResolveHit' in x or 'SetActor' in x for x in functions))
        # Rails (2026-11-17): the car rides its rail, so the wave no longer nudges a swept move.
        move=by_name['Move']
        self.assertFalse(any(o.get('function_name','').endswith(':K2_AddActorWorldOffset') for o in move))
        self.assertTrue(any(o.get('function_name','').endswith(':GetLocationAtDistanceAlongSpline') for o in move))


if __name__=='__main__':unittest.main()
