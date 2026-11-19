"""Per-state garment clips (rig lane, main's ruling b, 2026-11-10). Patches IN PLACE; never rebuilds existing functions.
Phases (FOA_PHASE):
  schema  PDA_Opponent gets IdleAnim, TelegraphAnim, HitAnim, StunAnim, DefeatAnim (AnimSequenceBase, like AttackAnim);
          then compile PDA_Opponent with Hayba blueprint_compile.
  rows    the four DA_Opponent_* rows point at SK_Garment_<G>Armature_<Take>.
  graph   BP_Garment: vars ClipState (Name), ClipProgress (int); function SyncStateClip; one call to it at the entry of
          StepBattleMotion (every motion tick) and of FlyToWear (story's defeat flight, so Defeat starts as it lifts off);
          then Hayba blueprint_compile BP_Garment.
SyncStateClip, on the Rig (SkeletalMeshComponent) only, never on the actor or Body:
  1 Progress changed (a hit) and not Defeated   -> HitAnim once, ClipState 'Hit'
  2 ClipState 'Hit' and the Rig still playing     -> wait for the flinch to finish
  3 State 'Attack', or State == ClipState and (still playing, or a held one-shot: Telegraph / Defeated) -> leave it
    (Lunge's attack clip keeps playing; Idle comes back by itself when it ends)
  4 otherwise play the State's clip: Telegraph once, Stunned loop, Defeated once, anything else Idle loop.
  $env:FOA_AREAS='Characters'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/garment_clip_wiring.py FOA_PHASE=schema|rows|graph"""
import os

import unreal

exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())

ENC = '/Game/FoA/Gameplay/Encounter'
OPP = f'{ENC}/PDA_Opponent'
OPP_C = f'{ENC}/PDA_Opponent.PDA_Opponent_C'
BP = f'{ENC}/BP_Garment'
GAR = '/Game/FoA/Characters/Garments'
KML = '/Script/Engine.KismetMathLibrary'
SKC = '/Script/Engine.SkeletalMeshComponent'
FIELDS = (('IdleAnim', 'Idle'), ('TelegraphAnim', 'Telegraph'), ('HitAnim', 'HitReact'), ('StunAnim', 'Stun'), ('DefeatAnim', 'Defeat'))


def schema():
    ensure_vars(OPP, [(f, BEL.get_object_reference_type(unreal.AnimSequenceBase), '', 'Opponent', True) for f, _ in FIELDS])
    unreal.EditorAssetLibrary.save_asset(OPP, only_if_is_dirty=False)
    print('GARMENT_WIRING schema ok; compile PDA_Opponent with Hayba next')


def rows():
    for g in ('Shirt', 'Trousers', 'Sock', 'Tie'):
        da = unreal.load_asset(f'{ENC}/Data/DA_Opponent_{g}')
        got = {}
        for f, take in FIELDS:
            a = unreal.load_asset(f'{GAR}/SK_Garment_{g}Armature_{take}')
            assert isinstance(a, unreal.AnimSequenceBase), (g, take)
            da.set_editor_property(f, a)
            got[f] = a.get_name()
        unreal.EditorAssetLibrary.save_loaded_asset(da, False)
        print('GARMENT_WIRING row', g, got)


def field(g, var, x, y):
    n = g.get(var, x, y, OPP_C)
    g.link(g.get('Data', x - 220, y), 'Data', n, 'self')
    return n


def play(g, x, y, anim_field, loop):
    n = g.call(f'{SKC}:PlayAnimation', x, y, bLooping='true' if loop else 'false')
    g.link(g.get('Rig', x - 220, y + 140), 'Rig', n, 'self')
    g.link(field(g, anim_field, x - 220, y + 220), anim_field, n, 'NewAnimToPlay')
    return n


def name_eq(g, a_var, b, x, y):
    n = g.call(f'{KML}:EqualEqual_NameName', x, y)
    g.link(g.get(a_var, x - 200, y), a_var, n, 'A')
    if isinstance(b, str) and b in ('State', 'ClipState'):
        g.link(g.get(b, x - 200, y + 60), b, n, 'B')
    else:
        g.default(n, 'B', b, 1)
    return n


def playing(g, x, y):
    n = g.call(f'{SKC}:IsPlaying', x, y)
    g.link(g.get('Rig', x - 200, y), 'Rig', n, 'self')
    return n


def b_and(g, a, b, x, y):
    n = g.call(f'{KML}:BooleanAND', x, y)
    g.link(a, 'ReturnValue', n, 'A'); g.link(b, 'ReturnValue', n, 'B')
    return n


def b_or(g, a, b, x, y):
    n = g.call(f'{KML}:BooleanOR', x, y)
    g.link(a, 'ReturnValue', n, 'A'); g.link(b, 'ReturnValue', n, 'B')
    return n


def graph():
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(BP))
    ensure_vars(BP, [('ClipState', ptype('name'), 'None', 'Garment|Clips', False),
                     ('ClipProgress', ptype('int'), '0', 'Garment|Clips', False)])
    g = Graph.function(BP, 'SyncStateClip')
    entry = entry_node(g)
    # 1 a hit
    ne_p = g.call(f'{KML}:NotEqual_IntInt', 300, 300)
    g.link(g.get('Progress', 100, 300), 'Progress', ne_p, 'A'); g.link(g.get('ClipProgress', 100, 360), 'ClipProgress', ne_p, 'B')
    not_def = g.call(f'{KML}:NotEqual_NameName', 300, 420, B='Defeated')
    g.link(g.get('State', 100, 420), 'State', not_def, 'A')
    b1 = g.branch(600, 0)
    g.link(b_and(g, ne_p, not_def, 480, 340), 'ReturnValue', b1, 'Condition')
    g.link(entry, 'then', b1, 'execute')
    set_p = g.set('ClipProgress', 900, -200)
    g.link(g.get('Progress', 700, -120), 'Progress', set_p, 'ClipProgress')
    set_hit = g.set('ClipState', 1150, -200)
    g.default(set_hit, 'ClipState', 'Hit')
    hit = play(g, 1450, -200, 'HitAnim', False)
    g.link(b1, 'then', set_p, 'execute'); g.link(set_p, 'then', set_hit, 'execute'); g.link(set_hit, 'then', hit, 'execute')
    # 2 the flinch still running
    b2 = g.branch(900, 200)
    g.link(b_and(g, name_eq(g, 'ClipState', 'Hit', 700, 520), playing(g, 700, 600), 860, 560), 'ReturnValue', b2, 'Condition')
    g.link(b1, 'else', b2, 'execute')
    # 3 leave it alone
    same = name_eq(g, 'State', 'ClipState', 1000, 700)
    held = b_or(g, name_eq(g, 'State', 'Telegraph', 1000, 820), name_eq(g, 'State', 'Defeated', 1000, 900), 1200, 860)
    keep = b_or(g, name_eq(g, 'State', 'Attack', 1200, 620), b_and(g, same, b_or(g, playing(g, 1200, 760), held, 1380, 800), 1500, 760), 1680, 700)
    b3 = g.branch(1200, 200)
    g.link(keep, 'ReturnValue', b3, 'Condition')
    g.link(b2, 'else', b3, 'execute')
    # 4 the state's clip
    x = 1500
    prev = (b3, 'else')
    for state, fld, loop in (('Telegraph', 'TelegraphAnim', False), ('Stunned', 'StunAnim', True), ('Defeated', 'DefeatAnim', False)):
        b = g.branch(x, 200)
        g.link(name_eq(g, 'State', state, x - 200, 1000), 'ReturnValue', b, 'Condition')
        g.link(prev[0], prev[1], b, 'execute')
        p = play(g, x + 300, 200 + 300 * (1 + len(state) % 3), fld, loop)
        s = g.set('ClipState', x + 600, 200 + 300 * (1 + len(state) % 3))
        g.link(g.get('State', x + 420, 300 + 300 * (1 + len(state) % 3)), 'State', s, 'ClipState')
        g.link(b, 'then', p, 'execute'); g.link(p, 'then', s, 'execute')
        prev = (b, 'else')
        x += 900
    p = play(g, x, 200, 'IdleAnim', True)
    s = g.set('ClipState', x + 300, 200)
    g.link(g.get('State', x + 120, 300), 'State', s, 'ClipState')
    g.link(prev[0], prev[1], p, 'execute'); g.link(p, 'then', s, 'execute')
    for fn in ('StepBattleMotion', 'FlyToWear'):
        hook(fn)
    unreal.EditorAssetLibrary.save_asset(BP, only_if_is_dirty=False)
    print('GARMENT_WIRING graph ok; compile BP_Garment with Hayba next')


def hook(fn):
    """One call to SyncStateClip right after fn's entry; idempotent, the rest of fn untouched."""
    bp = unreal.load_asset(BP)
    if fn not in [str(n) for n in BEL.list_graph_names(bp)]:
        print('GARMENT_WIRING no function', fn, '(not hooked)')
        return
    g = Graph(BP, fn)
    entry = entry_node(g)
    then = g.pin(entry, 'then', 'out')
    linked = list(PIN.list_connected_pins(then))
    if linked and BEL.get_node_title(PIN.get_owning_node(linked[0])).replace(' ', '').startswith('SyncStateClip'):
        return
    pos = BEL.get_node_pos(entry)
    call = g.call(self_call(BP, 'SyncStateClip'), pos.x + 60, pos.y - 160)
    PIN.break_pin_links(then)
    g.link(entry, 'then', call, 'execute')
    if linked:
        assert PIN.try_create_connection(g.pin(call, 'then', 'out'), linked[0])
    print('GARMENT_WIRING hooked', fn)


{'schema': schema, 'rows': rows, 'graph': graph}[os.environ.get('FOA_PHASE', 'schema')]()
