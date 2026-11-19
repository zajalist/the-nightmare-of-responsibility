"""Read the active native city and verify that distant sectors release."""
import json
from pathlib import Path
import time
import unreal


class CityStreamingProof:
    def __init__(self, world, journey, request_input):
        self.world = world
        self.journey = journey
        self.car = journey.get_editor_property('Car')
        self.game = unreal.GameplayStatics.get_game_instance(world)
        self.controller = unreal.GameplayStatics.get_player_controller(world, 0)
        self.request_input = request_input
        self.plan = json.loads(Path('P:/FoA/Saved/Integration/city_streaming/plan.json').read_text())
        self.points = {s['package']: s['splats'] for s in self.plan['sectors']}
        self.started = time.monotonic()
        self.next_sample = 0
        self.before = None
        self.drive_start = None
        self.released = False
        self.done = False
        self.result = {}
        unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (self.car, 'MeteorsLeft', 0))
        assert self.car.get_editor_property('MeteorsLeft') == 0
        road = self.car.get_editor_property('Road')
        self.collision = road.get_editor_property('CityCollision')

    def snapshot(self):
        sector_class = unreal.load_class(None, '/Game/FoA/Level2/City/Expanded/BP_City2Sector.BP_City2Sector_C')
        sectors = unreal.GameplayStatics.get_all_actors_of_class(self.world, sector_class)
        assert len(sectors) == len(self.points), len(sectors)
        visible, retained, wanted = set(), set(), set()
        for actor in sectors:
            package = actor.get_editor_property('SectorPackage')
            assert package in self.points, package
            if actor.get_editor_property('DesiredLoaded'):
                wanted.add(package)
            stream = actor.get_editor_property('Stream')
            if unreal.SystemLibrary.is_valid(stream):
                if stream.is_level_loaded():
                    retained.add(package)
                if stream.is_level_visible():
                    visible.add(package)
        near_points = sum(self.points[path] for path in retained)
        return dict(visible=sorted(visible), retained=sorted(retained), wanted=sorted(wanted), near_points=near_points,
                    camera=self.controller.player_camera_manager.get_camera_location().to_tuple())

    def shot(self, name):
        path = f'P:/FoA/Saved/Codex/dream_transition/city_stream_{name}.png'
        unreal.SystemLibrary.execute_console_command(self.world, f'Shot showui filename={path} -nosuffix', self.controller)
        return path

    def geometry(self):
        counts = {'near_ground': 0, 'near_building': 0, 'far_ground': 0, 'far_building': 0}
        for actor in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.StaticMeshActor):
            label = actor.get_actor_label()
            if not label.startswith('CityDense_SM_CityDense_'):
                continue
            component = actor.static_mesh_component
            assert component.is_visible() and not component.get_editor_property('hidden_in_game'), label
            assert component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, label
            detail = 'near' if '_near_' in label else 'far'
            surface = 'ground' if '_ground_' in label else 'building'
            counts[detail+'_'+surface] += 1
        assert all(counts.values()), counts
        assert counts['far_ground'] + counts['far_building'] == len(self.plan['overview']), counts
        return counts

    def tick(self):
        assert all(unreal.SystemLibrary.is_valid(obj) for obj in (self.journey, self.car, self.game, self.controller, self.collision))
        assert str(self.game.get_editor_property('SaveSlot')) == 'FoA_QA_Play'
        assert not self.collision.is_visible() or self.collision.get_editor_property('hidden_in_game')
        assert self.collision.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION
        elapsed = time.monotonic() - self.started
        assert elapsed < 30, ('City stream did not settle', self.car.get_actor_location().to_tuple(), self.snapshot())
        if elapsed < self.next_sample:
            return
        self.next_sample = elapsed + .2
        if self.before is None and elapsed > .8:
            before = self.snapshot()
            if not before['wanted'] or before['wanted'] != before['visible']:
                return
            before['geometry'] = self.geometry()
            self.before = before
            self.result['entry_shot'] = self.shot('entry')
            return
        if self.before is None or elapsed < 3:
            return
        position = self.car.get_actor_location()
        if self.drive_start is None:
            self.drive_start = position.x
            self.request_input(dict(key='W', event='pressed'))
            return
        if not self.released:
            if position.x - self.drive_start >= 17000:
                self.request_input(dict(key='W', event='released'))
                self.released = True
            return
        if abs(self.car.get_editor_property('Speed')) > .1:
            return
        after = self.snapshot()
        if (not after['wanted'] or after['visible'] != after['wanted'] or after['retained'] != after['wanted']
                or not set(self.before['visible']) - set(after['retained'])
                or not set(after['visible']) - set(self.before['visible'])):
            return
        for row in (self.before, after):
            assert row['near_points'] <= self.plan['peaks']['retained']['points'], row
        after['geometry'] = self.geometry()
        self.result.update(passed=True, before=self.before, after=after, driven_cm=position.x-self.drive_start,
                           destination_shot=self.shot('destination'))
        self.done = True
