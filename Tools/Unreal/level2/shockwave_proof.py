"""Measure a native meteor at a known distance from the stationary driving car."""
import math
from pathlib import Path
import unreal

from drive_data import GOALS, SHELTERS, SHOCKWAVE_BAND, SHOCKWAVE_DURATION, SHOCKWAVE_SPEED


class ShockwaveProof:
    def __init__(self, world, journey):
        self.world = world
        self.journey = journey
        self.car = journey.get_editor_property('Car')
        self.meteor = self.car.get_editor_property('Meteor')
        self.controller = unreal.GameplayStatics.get_player_controller(world, 0)
        self.game = unreal.GameplayStatics.get_game_instance(world)
        self.collection = unreal.load_asset('/Game/FoA/Level2/Materials/MPC_L2')
        self.origin = self.car.get_actor_location()
        self.impact_at = self.origin + unreal.Vector(900, 0, -65)
        self.start = self.clock()
        self.stamp = None
        self.crossed = None
        self.armed = False
        self.done = False
        self.result = dict(passed=False, samples=[], shots=[], fixture='Arm meteor 900 cm in front of parked car')
        assert self.car.get_editor_property('Active') and unreal.GameplayStatics.get_player_pawn(world,0) == self.car
        unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (self.car, 'MeteorsLeft', 0))
        assert self.car.get_editor_property('MeteorsLeft') == 0
        self.cost_before = self.car.get_editor_property('Composure')
        self.verify_side_streets()
        self.car.call_method('StartLeg',(0,))
        unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName',(self.car,'MeteorsLeft',0))

    def verify_side_streets(self):
        """Sample the live sign states at authored junctions, using explicit location fixtures."""
        road=self.car.get_editor_property('Road')
        label=road.get_editor_property('DestinationLabel')
        post=road.get_editor_property('DestinationPost')
        rows=[]
        for leg,marks in ((1,(((22700,160,2),'TURN RIGHT'),((23900,7400,2),'TURN LEFT'),
                              ((28000,9200,2),'FOLLOW THE BEND'),(GOALS[1],'PARK'))),
                          (2,(((43500,8500,2),'TURN LEFT'),(GOALS[2],'PARK')))):
            self.car.call_method('StartLeg',(leg,))
            assert (self.car.get_editor_property('Destination')-unreal.Vector(*GOALS[leg])).length()<1
            for pos,expected in marks:
                self.car.set_actor_location(unreal.Vector(*pos),False,True)
                self.car.call_method('CheckDestination',())
                actual=str(label.get_editor_property('text'))
                assert actual==expected and label.is_visible() and post.is_visible()==(expected=='PARK'),(pos,actual,expected)
                rows.append(dict(leg=leg,position=pos,marker=actual))
        self.car.call_method('ResolveHit',(30,'QA'))
        self.car.set_actor_location(unreal.Vector(*SHELTERS[1]),False,True)
        self.car.call_method('CheckShelter',())
        assert self.car.get_editor_property('UsedShelter') and self.car.get_editor_property('Composure')==92
        self.car.call_method('CheckShelter',())
        assert self.car.get_editor_property('Composure')==92
        self.result['wayfinding_fixture']=rows

    def clock(self):
        return unreal.GameplayStatics.get_time_seconds(self.world)

    def shot(self, name):
        path = Path('P:/FoA/Saved/Codex/dream_transition') / f'shockwave_{name}.png'
        unreal.SystemLibrary.execute_console_command(self.world, f'Shot showui filename={path.as_posix()} -nosuffix', self.controller)
        self.result['shots'].append(str(path))

    def tick(self):
        assert all(unreal.SystemLibrary.is_valid(x) for x in (self.world, self.journey, self.car, self.meteor, self.game, self.controller))
        assert str(self.game.get_editor_property('SaveSlot')) == 'FoA_QA_Play'
        now = self.clock()
        assert now - self.start < 9, 'Meteor did not finish in time'
        if not self.armed:
            if now - self.start < .3:
                return
            self.shot('calm')
            self.meteor.call_method('Arm', (self.car, self.impact_at))
            self.armed = True
            return
        value = unreal.MaterialLibrary.get_vector_parameter_value(self.world, self.collection, 'Impact0')
        sand=unreal.MaterialLibrary.get_scalar_parameter_value(self.world,self.collection,'SandRadius')
        offset = self.car.get_actor_location() - self.origin
        velocity = self.car.get_editor_property('ShockwaveVelocity').length()
        assert abs(self.car.get_editor_property('Speed')) < .1
        if self.stamp is None:
            if value.a < .5:
                assert offset.length() < .1
                if self.meteor.get_editor_property('Age')>2.25 and len(self.result['shots'])==1:
                    mesh=self.meteor.get_editor_property('Shadow')
                    assert mesh.get_editor_property('static_mesh').get_name()=='SM_L2SandMeteor' and mesh.is_visible()
                    self.shot('falling_sand')
                return
            self.stamp = value.b
            assert abs(value.r - self.impact_at.x) < .05 and abs(value.g - self.impact_at.y) < .05
            assert self.meteor.get_editor_property('Impacted')
            self.shot('impact')
        age = now - self.stamp
        if not self.result['samples'] or age - self.result['samples'][-1]['age'] > .08:
            self.result['samples'].append(dict(age=age, offset=offset.to_tuple(), velocity=velocity, wave=value.a,sand_radius=sand))
        if self.crossed is None and self.car.get_editor_property('ShockwaveFired'):
            self.crossed = age
            arrival = (900 + SHOCKWAVE_BAND * .25) / SHOCKWAVE_SPEED
            assert math.isclose(age, arrival, abs_tol=.15), (age, arrival)
            self.shot('wave_at_car')
        if age >= SHOCKWAVE_DURATION + .15:
            assert self.crossed is not None, 'Wave never moved the car'
            assert abs(offset.x + 7.5) < .5 and abs(offset.y) < .1 and abs(offset.z) < .1, offset
            assert value.a == 0 and velocity < .1, (value, velocity)
            assert self.car.get_editor_property('Composure') == self.cost_before
            assert sand>=1400 and any(30 < sample['sand_radius'] < 1000 for sample in self.result['samples']),self.result
            self.result.update(passed=True, crossing_seconds=self.crossed, displacement_cm=offset.to_tuple())
            self.done = True
