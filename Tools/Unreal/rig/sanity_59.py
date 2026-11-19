"""Rig lane, editor (read only): after the UE 5.9 move, are the rig lane's assets intact?
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/rig/sanity_59.py
Teen skeleton bone count (55, twist leaves), ABP_FoA_TeenPost, RTG, the 24 garment clips (no root track, length),
PDA_Opponent anim fields on the four rows, BP_Garment's SyncStateClip, the hanger grip pose asset."""
import unreal

EAL, AL = unreal.EditorAssetLibrary, unreal.AnimationLibrary
G = '/Game/FoA/Characters/Garments/SK_Garment_{}Armature_{}'
TAKES = {'Shirt': 'Lash', 'Trousers': 'Kick', 'Sock': 'Hop', 'Tie': 'CoilStrike'}
bad = []
clips = 0
for g, atk in TAKES.items():
    for take in ('Idle', 'Telegraph', atk, 'HitReact', 'Stun', 'Defeat'):
        a = unreal.load_asset(G.format(g, take))
        if not isinstance(a, unreal.AnimSequence):
            bad.append(('clip', g, take, type(a).__name__))
            continue
        clips += 1
        if 'root' in [str(n) for n in AL.get_animation_track_names(a)]:
            bad.append(('root_track', g, take))
for p in ('/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_TeenGrip_Hanger_R', '/Game/FoA/Characters/Player/Montages/AM_FoA_KneelScrewdriver',
          '/Game/FoA/Gameplay/AN_FoA_InteractionContact', '/Game/FoA/Gameplay/Encounter/BP_Garment'):
    if not EAL.does_asset_exist(p):
        bad.append(('missing', p))
rows = {}
for a in EAL.list_assets('/Game/FoA/Gameplay/Encounter/Data', recursive=False):
    if 'DA_Opponent_' in a:
        d = unreal.load_asset(a.split('.')[0])
        rows[d.get_name()] = [bool(d.get_editor_property(n)) for n in ('IdleAnim', 'TelegraphAnim', 'HitAnim', 'StunAnim', 'DefeatAnim')]
bp = unreal.load_asset('/Game/FoA/Gameplay/Encounter/BP_Garment')
fns = [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(bp)] if hasattr(unreal.BlueprintEditorLibrary, 'list_graph_names') else []
print('SANITY', unreal.SystemLibrary.get_engine_version(), 'clips', clips, 'rows', rows, 'SyncStateClip' in fns or fns[:3], 'bad', bad)
