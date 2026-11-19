"""Repair allowlisted battle/wardrobe empty auto-rigs and actor animation bindings.

Engine script; default FOA_BATTLE_RIG_MODE=inspect. Apply requires the coordinator's
asset window. Reuses the existing CharacterMesh0 child locator, never creates actors,
opens Sequencer, or touches wake-up/manual-pose assets.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT='/Game/FoA/Cinematics/BattleIntro/'
PATHS=(ROOT+'LS_BattleIntro',ROOT+'LS_BattleIntro_Short',
       '/Game/FoA/Cinematics/Wardrobe/LS_WardrobeFall')
RIG='MovieSceneControlRigParameterTrack'
ANIM='MovieSceneSkeletalAnimationTrack'


def kind(obj):return obj.get_class().get_name()


def value(obj):
    if hasattr(obj,'export_text'):return obj.export_text()
    if hasattr(obj,'get_path_name'):return obj.get_path_name()
    return obj


def section_data(section):
    result=dict(start=section.get_start_frame() if section.has_start_frame() else None,
                end=section.get_end_frame() if section.has_end_frame() else None,
                row=section.get_row_index(),completion=str(section.get_completion_mode()),
                easing=section.get_editor_property('easing').export_text(),channels=[])
    if kind(section)=='MovieSceneSkeletalAnimationSection':
        result['params']=section.get_editor_property('params').export_text()
    if kind(section)=='MovieSceneCameraCutSection':result['camera']=value(section.get_camera_binding_id())
    for channel in section.get_all_channels():
        keys=[]
        for key in channel.get_keys():
            time=key.get_time()
            keys.append([time.frame_number.value,time.sub_frame,value(key.get_value())])
        result['channels'].append(dict(name=str(channel.channel_name),keys=keys))
    return result


def track_data(track):
    return dict(kind=kind(track),name=str(track.get_display_name()),sections=[section_data(s) for s in track.get_sections()])


def rig_audit(track,seq=None):
    row=track_data(track)
    try:
        rig=track.get_editor_property('control_rig')
        row['rig_class']=kind(rig) if rig else None
    except Exception as error:
        row['rig_class']=None;row['rig_read_error']=str(error)
        if seq is not None:
            import unreal
            for proxy in unreal.ControlRigSequencerLibrary.get_control_rigs(seq):
                if proxy.track==track:
                    row['rig_class']=kind(proxy.control_rig)
                    row['rig_class_path']=proxy.control_rig.get_class().get_path_name()
    row['channel_count']=sum(len(s['channels']) for s in row['sections'])
    row['key_count']=sum(len(c['keys']) for s in row['sections'] for c in s['channels'])
    # Unkeyed alone is insufficient: authored rigs of any other class remain untouched.
    standard_manny=row.get('rig_class_path')=='/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body.CR_Mannequin_Body_C'
    row['confirmed_empty_auto_rig']=(row['rig_class']=='FKControlRig' or standard_manny) and row['key_count']==0 and bool(row['sections'])
    return row


def locate(seq):
    players=[b for b in seq.get_bindings() if str(b.get_display_name())=='Player']
    assert len(players)==1,('Player binding ambiguous',len(players))
    player=players[0]
    import unreal
    template=unreal.MovieSceneBindingExtensions.get_object_template(player)
    assert template and template.get_class().get_name()=='BP_FoAPlayer_C','Unexpected Player template'
    mesh=template.get_editor_property('Mesh');assert mesh and mesh.get_name()=='CharacterMesh0'
    children=[b for b in seq.get_bindings() if b.get_parent().is_valid() and b.get_parent().get_id()==player.get_id()
              and str(b.get_display_name())==mesh.get_name()]
    assert len(children)==1,('Existing CharacterMesh0 locator required',len(children))
    return player,children[0]


def protected(seq,excluded):
    rows=[dict(binding='master',tracks=[track_data(t) for t in seq.get_tracks()])]
    for binding in seq.get_bindings():
        rows.append(dict(binding=value(binding.get_id()),name=str(binding.get_display_name()),
                         tracks=[track_data(t) for t in binding.get_tracks() if t not in excluded]))
    return hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()


def copy_section(original,replacement):
    section=replacement.add_section()
    section.set_editor_property('params',original.get_editor_property('params'))
    assert original.has_start_frame() and original.has_end_frame(),'Refuse unbounded animation section'
    section.set_range(original.get_start_frame(),original.get_end_frame())
    section.set_row_index(original.get_row_index())
    section.set_editor_property('easing',original.get_editor_property('easing'))
    section.set_completion_mode(original.get_completion_mode())
    assert section_data(section)==section_data(original),'Animation params/range/easing/channels changed during copy'
    return section


def process(seq,apply=False):
    import unreal
    path=seq.get_path_name().split('.')[0];assert path in PATHS,('Sequence outside allowlist',path)
    player,source=locate(seq)
    actor_anims=[t for t in player.get_tracks() if kind(t)==ANIM]
    child_anims=[t for t in source.get_tracks() if kind(t)==ANIM]
    rigs=[t for t in source.get_tracks() if kind(t)==RIG]
    report=dict(path=path,player=str(player.get_id()),component=str(source.get_id()),
                actor_animation=[track_data(t) for t in actor_anims],component_animation=[track_data(t) for t in child_anims],
                rigs=[rig_audit(t,seq) for t in rigs],changed=False)
    eligible=[t for t,row in zip(rigs,report['rigs']) if row['confirmed_empty_auto_rig']]
    blockers=[]
    if len(eligible)!=len(rigs):blockers.append('Unknown or authored Control Rig retained')
    if actor_anims and child_anims:blockers.append('Both actor and component already have animation; manual comparison required')
    if not actor_anims and not child_anims:blockers.append('No existing animation clips to preserve')
    report['blockers']=blockers
    if not apply or blockers or not (eligible or actor_anims):return report
    # Check all copies before deleting a track; retain authored cameras/transforms/audio verbatim.
    before=protected(seq,actor_anims+eligible)
    replacements=[]
    try:
        for old in actor_anims:
            replacement=source.add_track(unreal.MovieSceneSkeletalAnimationTrack);replacements.append(replacement)
            replacement.set_display_name(old.get_display_name())
            for original in old.get_sections():copy_section(original,replacement)
        assert protected(seq,actor_anims+eligible+replacements)==before,'Unrelated sequence content changed'
    except Exception:
        for replacement in replacements:source.remove_track(replacement)
        raise
    for old in actor_anims:player.remove_track(old)
    for rig in eligible:source.remove_track(rig)
    assert protected(seq,replacements)==before,'Protected sequence content changed'
    report.update(changed=True,removed_empty_rigs=len(eligible),relocated_tracks=len(replacements),protected_sha256=before)
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False),path
    report['component_animation_after']=[track_data(t) for t in source.get_tracks() if kind(t)==ANIM]
    return report


def main():
    import unreal
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'PIE active'
    mode=os.environ.get('FOA_BATTLE_RIG_MODE','inspect');assert mode in ('inspect','apply')
    selected=os.environ.get('FOA_BATTLE_RIG_SEQ','both')
    paths=PATHS[:2] if selected=='both' else (ROOT+selected,)
    assert all(p in PATHS for p in paths),'Only full/short battle intros are allowed'
    out=Path('P:/FoA/Saved/Integration/battle_intro_rig');out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for path in paths:
        name=path.rsplit('/',1)[-1];seq=unreal.load_asset(path);assert seq,path
        audit=process(seq)
        (out/(name+'_before.json')).write_text(json.dumps(audit,indent=1,default=str))
        if mode=='apply' and not audit['blockers']:
            backup=Path('P:/FoA/Saved/Backups/level-integration-20261111')/(name+'_before_empty_rig.uasset')
            if not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(Path('P:/FoA/Content')/(path.removeprefix('/Game/')+'.uasset'),backup)
        row=process(seq,apply=mode=='apply');rows.append(row)
        (out/(name+'_'+mode+'.json')).write_text(json.dumps(row,indent=1,default=str))
        print('BATTLE_RIG',name,'changed',row['changed'],'blockers',row['blockers'],
              'rigs',[(r['rig_class'],r['channel_count'],r['key_count']) for r in row['rigs']])
    return rows


if __name__=='__main__':main()
