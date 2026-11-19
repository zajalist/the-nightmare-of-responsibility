"""Steer the stock car along surveyed streets with Unreal's raw gamepad keys."""
from math import atan2, degrees, hypot

from job_route import DESTINATIONS
from threshold_walk_proof import WalkProof

STICK_X, STICK_Y = 'Gamepad_LeftX', 'Gamepad_LeftY'
THROTTLE, BRAKE = 'Gamepad_RightTrigger', 'Gamepad_LeftTrigger'
ACCEPT, PARK = 'Gamepad_FaceButton_Bottom', 'Gamepad_FaceButton_Top'
CANCEL, CV = 'Gamepad_FaceButton_Right', 'Gamepad_DPad_Left'
ROUTES = (
    (),
    ((21200, 145), (23650, 400), (24350, 3850), (24600, 8670), (26300, 8730), (31000, 8650)),
    ((41500, 8560), (44500, 8160), (45240, 6610), (45430, 170), (45450, -4900)),
    ((45450, -4300), (45500, -1000), (45940, -45), (47600, 270)),
)


def bearing_error(x, y, yaw, target):
    desired = degrees(atan2(target[1] - y, target[0] - x))
    return (desired - yaw + 180) % 360 - 180


class Gamepad:
    def __init__(self, u, world):
        self.u, self.world, self.values = u, world, {}

    def set(self, key, value):
        assert key.startswith('Gamepad_') and -1 <= value <= 1
        if self.values.get(key, 0) == value:
            return
        self.values[key] = value
        command = f'Input.+key {key} {value:.3f}' if value or key in (STICK_X, STICK_Y) else f'Input.-key {key}'
        self.u.SystemLibrary.execute_console_command(self.world, command)

    def close(self):
        current = self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()
        if current and current == self.world and self.u.SystemLibrary.is_valid(current):
            for key in self.values:
                self.u.SystemLibrary.execute_console_command(self.world, f'Input.-key {key}')
        self.values.clear()

    def release_key(self,key):
        self.u.SystemLibrary.execute_console_command(self.world,f'Input.-key {key}')
        self.values.pop(key,None)


class GamepadWalk(WalkProof):
    def __init__(self, world, threshold, pad, engine):
        self.pad = pad
        super().__init__(world, threshold, None, cap_seconds=42, engine=engine)
        self.result['scope'] = 'Raw Gamepad_LeftY and A through the normal input mappings'

    def down(self, key):
        native = self.u.Key()
        native.set_editor_property('key_name', STICK_Y if key == 'W' else ACCEPT)
        return abs(self.pc.get_input_analog_key_state(native)) > .15 if key == 'W' else self.pc.is_input_key_down(native)

    def tick(self, dt=0):
        # Injected digital presses are one-frame events on some PIE focus changes.
        if self.pad.values.get(ACCEPT) and self.state == 'preheld' and not self.down('E'):
            self.pad.values.pop(ACCEPT)
            self.pad.set(ACCEPT,1)
        super().tick(dt)

    def send(self, key, down):
        self.pad.set(STICK_Y if key == 'W' else ACCEPT, int(down))
        self.pending = key, down, self.now()
        if down:
            self.held.add(key)
        else:
            self.held.discard(key)
        self.mark('input_requested', key=STICK_Y if key == 'W' else ACCEPT, down=down)

    def close(self):
        self.pad.close()


class Drive:
    def __init__(self, car, pad, index, now, rows):
        self.car, self.pad, self.index, self.rows = car, pad, index, rows
        self.points = (*ROUTES[index], DESTINATIONS[index][:2])
        self.point = 0
        self.previous = self.start = car.get_actor_location().to_tuple()
        self.travel = 0.
        self.started = self.sample = now
        self.reversing = False
        self.throttle = False
        self.slow_since = now
        self.held_at = now
        self.next_strike = car.get_editor_property('NextMeteor')
        road = car.get_editor_property('Road')
        self.traffic = road.get_editor_property('TrafficEastA')
        body = road.get_editor_property('TrafficEastACollision')
        assert body.get_collision_enabled() == pad.u.CollisionEnabled.QUERY_ONLY
        assert body.get_collision_response_to_channel(pad.u.CollisionChannel.ECC_PAWN) == pad.u.CollisionResponseType.ECR_BLOCK
        self.traffic_start = self.traffic.get_world_location().x
        self.strikes = []
        self.rows.append(dict(kind='drive_start', job=index, position=self.start, t=round(now, 2)))
        if index:
            assert hypot(self.start[0]-DESTINATIONS[index-1][0],self.start[1]-DESTINATIONS[index-1][1])<800, (
                'Car did not resume at the previous parking spot',index,self.start)

    def tick(self, now):
        get = self.car.get_editor_property
        x, y, z = self.car.get_actor_location().to_tuple()
        delta = hypot(x-self.previous[0], y-self.previous[1])
        assert delta < 1200, ('Vehicle position jumped', self.previous, (x,y,z))
        self.travel += delta
        self.previous = x,y,z
        speed = get('Speed')
        next_strike = get('NextMeteor')
        if next_strike != self.next_strike:
            impact = get('Meteor').get_actor_location().to_tuple()
            self.strikes.append(dict(at=impact, next=round(next_strike,2), t=round(now,2)))
            self.next_strike = next_strike
        yaw = self.car.get_actor_rotation().yaw
        target = self.points[self.point]
        distance = hypot(x-target[0], y-target[1])
        if now >= self.sample:
            self.rows.append(dict(kind='drive_sample', job=self.index, position=[round(x),round(y),round(z)],
                yaw=round(yaw), speed=round(speed), point=self.point, t=round(now,2)))
            self.sample = now+1
        assert not get('Failed'), ('Lost all composure', self.index, self.point, self.previous)
        assert get('Clock') < 130, ('Route stalled', self.index, self.point, self.previous)
        final = self.point == len(self.points)-1
        if final and get('NearDestination') and get('ArrivalJob') == self.index:
            self.pad.close()
            assert self.travel > 2500, ('Untraveled destination', self.index, self.travel)
            self.rows.append(dict(kind='driven_arrival', job=self.index, metres=round(self.travel/100,1),
                                  hits=get('HitsResolved'), position=self.previous, t=round(now,2),
                                  strikes=self.strikes, composure=get('Composure'),
                                  traffic_travel_cm=abs(self.traffic.get_world_location().x-self.traffic_start)))
            return True
        if not final and distance < 475:
            self.point += 1
            target = self.points[self.point]
        angle = bearing_error(x,y,yaw,target)
        # Back out of a stopped turn or reverse along a street before taking the next corner.
        if abs(speed) > 60:
            self.slow_since = now
        if not self.reversing and (abs(angle)>130 or now-self.slow_since>1.8):
            self.reversing, self.held_at = True, now
        if self.reversing and (abs(angle)<65 or (now-self.held_at>2.3 and abs(angle)<140)):
            self.reversing, self.slow_since = False, now
        if self.reversing:
            angle = bearing_error(x,y,yaw+180,target)
        steer = round(max(-1., min(1., angle/40 * (-1 if self.reversing else 1))) * 12) / 12
        meteor = get('Meteor')
        brace = meteor.get_editor_property('Active') and 2.15 <= meteor.get_editor_property('Age') < 2.6
        if self.index == 0 and len(self.strikes) == 1:
            brace = False  # Measure one live, unbraced strike on the short first drive.
        self.pad.set(ACCEPT, int(brace))
        desired = 0 if final and distance < 440 else 475 if abs(angle)>20 or distance<1300 else 790
        self.pad.set(BRAKE, int(self.reversing))
        self.throttle = bool(desired and not self.reversing and speed < desired+(70 if self.throttle else -70))
        self.pad.set(THROTTLE, int(self.throttle))
        self.pad.set(STICK_X, steer)
        return False


if __name__ == '__main__':
    assert bearing_error(0,0,350,(10,0)) == 10
    assert bearing_error(0,0,10,(10,0)) == -10
    assert len(ROUTES)==len(DESTINATIONS) and all(ROUTES[1:])
