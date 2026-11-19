"""Read-only PIE capsule sweeps at the live pawn and reported stuck spot. No movement or actor edits."""
import json
import math

import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = editor.get_game_world()
playing = w is not None
w = w or editor.get_editor_world()
assert 'L_Tutorial_Bedroom' in w.get_name(), w.get_name()
p = unreal.GameplayStatics.get_player_character(w, 0) if playing else unreal.get_default_object(
    unreal.load_class(None, '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'))
cap = p.capsule_component
radius, half = cap.get_scaled_capsule_radius(), cap.get_scaled_capsule_half_height()
pc = unreal.GameplayStatics.get_player_controller(w, 0) if playing else None
control_yaw = pc.get_control_rotation().yaw if pc else 55.0
yaw = math.radians(control_yaw)
found = {}


def v(value):
    return [round(value.x, 4), round(value.y, 4), round(value.z, 4)]


def collider(actor, component=None):
    if actor is None:
        return None
    center, extent = actor.get_actor_bounds(False)
    result = dict(id=actor.get_name(), label=actor.get_actor_label(), cls=actor.get_class().get_name(),
                  location=v(actor.get_actor_location()), bounds_center=v(center), bounds_extent=v(extent))
    if component:
        result.update(component=component.get_name(), collision=str(component.get_collision_enabled()),
                      profile=str(component.get_collision_profile_name()))
        if isinstance(component, unreal.StaticMeshComponent) and component.static_mesh:
            mesh = component.static_mesh
            setup = mesh.get_editor_property('body_setup')
            result['mesh'] = mesh.get_path_name()
            if setup:
                result['trace_flag'] = str(setup.get_editor_property('collision_trace_flag'))
                geom = setup.get_editor_property('agg_geom')
                result['simple_shapes'] = {name: len(geom.get_editor_property(name))
                                           for name in ('box_elems', 'convex_elems', 'sphyl_elems', 'sphere_elems')}
    found[actor.get_name() + ':' + (component.get_name() if component else '')] = result
    return result


def unpack(hit):
    if isinstance(hit, tuple):
        hit = hit[1] if hit[0] else None
    if hit is None:
        return None
    parts = hit.to_tuple()
    component = next((value for value in parts if isinstance(value, unreal.PrimitiveComponent)), None)
    actor = next((value for value in parts if isinstance(value, unreal.Actor)), None)
    if actor is None and component:
        actor = component.get_owner()
    return dict(blocking=parts[0], initial_overlap=parts[1], time=parts[2], distance=parts[3],
                location=v(parts[4]), impact_point=v(parts[5]), normal=v(parts[6]), impact_normal=v(parts[7]),
                collider=collider(actor, component))


out = dict(world='PIE' if playing else 'Editor', player=v(p.get_actor_location()) if playing else None,
           capsule_center=v(cap.get_world_location()) if playing else None, radius=radius, half_height=half,
           capsule_collision=str(cap.get_collision_enabled()), capsule_profile=str(cap.get_collision_profile_name()),
           controller_yaw=control_yaw, move_ignored=pc.is_move_input_ignored() if pc else None,
           cinematic=p.get_editor_property('bCinematic'), movement=str(p.character_movement.movement_mode),
           max_walk_speed=p.character_movement.max_walk_speed, max_acceleration=p.character_movement.max_acceleration,
           velocity=v(p.get_velocity()), sweeps=[], floors=[])
positions = [('reported_stuck', unreal.Vector(288.471, -114.768, 90.0))]
if playing:
    positions.insert(0, ('live', p.get_actor_location()))
ignore = [p] if playing else []
directions = [('X+', unreal.Vector(60, 0, 0)), ('X-', unreal.Vector(-60, 0, 0)),
              ('Y+', unreal.Vector(0, 60, 0)), ('Y-', unreal.Vector(0, -60, 0)),
              ('native_forward', unreal.Vector(60 * math.cos(yaw), 60 * math.sin(yaw), 0))]
for label, position in positions:
    for lift in (0.0, 0.5, 2.15, 4.0):
        start = position + unreal.Vector(0, 0, lift)
        for direction, offset in directions:
            hit = unreal.SystemLibrary.capsule_trace_single_by_profile(w, start, start + offset, radius, half,
                    'Pawn', False, ignore, unreal.DrawDebugTrace.NONE, True)
            out['sweeps'].append(dict(position=label, lift=lift, direction=direction, start=v(start), hit=unpack(hit)))
    for complex_trace in (False, True):
        hit = unreal.SystemLibrary.line_trace_single(w, position + unreal.Vector(0, 0, 160),
                unreal.Vector(position.x, position.y, -30), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                complex_trace, ignore, unreal.DrawDebugTrace.NONE, True)
        out['floors'].append(dict(position=label, complex=complex_trace, hit=unpack(hit)))
for actor in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if actor.get_name() == 'StaticMeshActor_0' or actor.get_actor_label() in ('Floor', 'Bed', 'Nightstand'):
        collider(actor, actor.get_component_by_class(unreal.StaticMeshComponent))
out['colliders'] = list(found.values())
with open('P:/FoA/Saved/Integration/roam_geometry_probe.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print('ROAM_GEOMETRY', json.dumps(out, separators=(',', ':')))
