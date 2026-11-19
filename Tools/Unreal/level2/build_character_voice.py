"""One dialogue voice owner shared by story, cinematics and L2. One step per lease."""
import os
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path[:0] = [str(Path(__file__).parent), 'P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import build_drive
from build_drive import G, call, cls, GS, SL
from held_tool_graphs import Batch
import editor_lock

FRONT = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
JOURNEY = '/Game/FoA/Level2/Journey/BP_L2Journey'
HUD = '/Game/FoA/UI/Game/WBP_HUD'
CINE = '/Game/FoA/UI/Game/WBP_CineSubtitle'
ROOT = '/Game/FoA/Audio/Dialogue'
STR = '/Script/Engine.KismetStringLibrary:'
TEXT = '/Script/Engine.KismetTextLibrary:'
AU = '/Script/Engine.AudioComponent:'
PROFILES = ('Player', 'Adviser', 'Manager', 'Receptionist', 'Interviewer')
BANK = [f'{ROOT}/S_Voice_{name}_{i:02d}.S_Voice_{name}_{i:02d}' for name in PROFILES for i in range(6)]
SIGNATURES = {'SayCharacter': [('Text','text'),('Speaker','int'),('Emotion','int')], 'StopCharacterVoice': []}


def inspect(path,graph):
    data=call('blueprint_inspect_graph',path=path,graph_name=graph)
    if not data.get('_truncated') and len(data['nodes'])==data.get('node_count',len(data['nodes'])) and len(data['edges'])==data.get('edge_count',len(data['edges'])):
        return data['nodes'],data['edges']
    # UE5.9's native inspector truncates at 50 without pagination; read all GUIDs before a cut.
    out=Path('P:/FoA/Saved/CharacterVoice')/(path.rsplit('/',1)[1]+'_'+graph+'_graph.json')
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/character_voice_graph_read.py',
         env={'FOA_VOICE_ASSET':path,'FOA_VOICE_GRAPH':graph},resources=['asset:'+path])
    full=json.loads(out.read_text(encoding='utf8'))
    assert len(full['nodes'])==data['node_count'] and len(full['edges'])==data['edge_count']
    return full['nodes'],full['edges']


build_drive.inspect=inspect


def skeleton():
    for path in (FRONT, JOURNEY):
        info = call('blueprint_get_info', path=path)
        have = {v['name'] for v in info['variables']}
        if info.get('_truncated'):
            script='\n'.join(['import unreal as u,json',f'bp=u.load_asset({path!r})',
                'print(json.dumps(dict(variables=[str(n) for n in u.BlueprintEditorLibrary.list_member_variable_names(bp)],functions=[str(g.get_name()) for g in u.BlueprintEditorLibrary.list_graphs(bp)])))'])
            complete=json.loads(call('python_run',script=script)['stdout'].strip())
            have.update(complete['variables']);info['functions']=complete['functions']
        if path == FRONT:
            if 'VoiceBank' not in have:
                call('blueprint_add_variable',path=path,variable_name='VoiceBank',variable_type='object:/Script/Engine.SoundBase',
                     container='array',category='Character voice')
            for name, typ, value in [('VoiceAudio','object:/Script/Engine.AudioComponent',''),
                ('VoiceLine','string',''),('VoiceSpeaker','int','-1'),('VoiceEmotion','int','-1'),
                ('VoiceVariant','int','1'),('VoicePhrase','object:/Script/Engine.SoundBase','')]+[
                    ('VoiceVariant'+str(i),'int','1') for i in range(5)]:
                if name not in have:
                    call('blueprint_add_variable', path=path, variable_name=name, variable_type=typ,
                         default_value=value, category='Character voice')
        funcs = dict(SIGNATURES)
        if path == FRONT:
            funcs['PickCharacterVoice'] = []
        for name, inputs in funcs.items():
            if name not in info['functions']:
                call('blueprint_add_function', path=path, function_name=name,
                     inputs=[dict(name=n,type=t) for n,t in inputs])
        call('blueprint_compile', path=path, save=True)


def stop():
    g = G(FRONT, 'StopCharacterVoice')
    g.setv('VoiceLine', g.f(STR+'Concat_StrStr', A='', B=''))
    valid = g.branch(g.f(SL+'IsValid', Object=g.getv('VoiceAudio'))); g.side(valid)
    g.do(AU+'Stop', self=g.getv('VoiceAudio'))
    g.finish()


def pick():
    g = G(FRONT, 'PickCharacterVoice')
    index = g.math('Add_IntInt', A=g.math('Multiply_IntInt', A=g.getv('VoiceSpeaker'), B=6),
        B=g.math('Add_IntInt', A=g.math('Multiply_IntInt', A=g.getv('VoiceEmotion'), B=2), B=g.getv('VoiceVariant')))
    item=g.ref();g.node(item,'get_array_item',0,0);g.put(item,'Array',g.getv('VoiceBank'));g.put(item,'Dimension 1',index)
    g.setv('VoicePhrase', (item,'Output'))
    for i in range(5):
        branch=g.branch(g.math('EqualEqual_IntInt',A=g.getv('VoiceSpeaker'),B=i));g.side(branch)
        g.setv('VoiceVariant'+str(i),g.getv('VoiceVariant'))
        g.side(branch,False)
    g.finish()


def say():
    g = G(FRONT, 'SayCharacter')
    ready = g.branch(g.math('Not_PreBool', A=g.f(GS+'IsGamePaused'))); g.side(ready)
    line = g.f(TEXT+'Conv_TextToString', InText=g.arg('Text'))
    line = g.f(STR+'TrimTrailing', SourceString=g.f(STR+'Trim', SourceString=line))
    speaker = g.math('Clamp', Value=g.arg('Speaker'), Min=0, Max=4)
    emotion = g.math('Clamp', Value=g.arg('Emotion'), Min=0, Max=2)
    same = g.math('BooleanAND', A=g.f(STR+'EqualEqual_StrStr', A=line, B=g.getv('VoiceLine')),
        B=g.math('BooleanAND', A=g.math('EqualEqual_IntInt', A=speaker, B=g.getv('VoiceSpeaker')),
            B=g.math('EqualEqual_IntInt', A=emotion, B=g.getv('VoiceEmotion'))))
    changed = g.branch(g.math('Not_PreBool', A=same)); g.side(changed)
    g.own('StopCharacterVoice')
    nonempty = g.branch(g.math('Greater_IntInt', A=g.f(STR+'Len', S=line), B=0)); g.side(nonempty)
    g.setv('VoiceLine', line); g.setv('VoiceSpeaker', speaker); g.setv('VoiceEmotion', emotion)
    variant=g.getv('VoiceVariant0')
    for i in range(1,5):
        variant=g.math('SelectInt',A=g.getv('VoiceVariant'+str(i)),B=variant,
                       bPickA=g.math('EqualEqual_IntInt',A=speaker,B=i))
    g.setv('VoiceVariant', g.math('Subtract_IntInt', A=1, B=variant))
    g.own('PickCharacterVoice')
    audio = g.do(GS+'CreateSound2D', Sound=g.getv('VoicePhrase'), VolumeMultiplier=.7,
        PitchMultiplier=1., bPersistAcrossLevelTransition=False, bAutoDestroy=True)
    g.setv('VoiceAudio', audio)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('VoiceAudio')));g.side(valid)
    g.do(AU+'SetUISound',self=g.getv('VoiceAudio'),bInUISound=False)
    g.do(AU+'Play',self=g.getv('VoiceAudio'),StartTime=0.)
    g.finish()


def wrappers():
    for name, inputs in SIGNATURES.items():
        g = G(JOURNEY, name)
        front = g.do(GS+'GetActorOfClass', ActorClass=cls(FRONT))
        target = g.cast(front, cls(FRONT), 'BP Fo AFront End')
        g.do(cls(FRONT)+':'+name, self=target, **{n:g.arg(n) for n,_ in inputs})
        g.finish()


def hook(path, graph, source_title, function, pins=None, speaker_from_name=False, new_event=False):
    """Insert only our call after an existing entry/event, preserving its chain."""
    nodes, edges = inspect(path, graph)
    source = next(n['node_id'] for n in nodes if n['title'].replace(' ','') == source_title.replace(' ',''))
    already=[n['node_id'] for n in nodes if n['title'].replace(' ','')==function]
    if already:
        reached=source
        for _ in range(4):
            links=[e['to_node'] for e in edges if e['from_node']==reached and e['from_pin']=='then']
            assert len(links)==1,(path,graph,'Existing voice hook disconnected')
            reached=links[0]
            if reached in already:return
        raise AssertionError((path,graph,'Existing voice hook is not on the original chain'))
    outgoing = [e for e in edges if e['from_node']==source and e['from_pin']=='then']
    assert len(outgoing)<=1 if new_event else len(outgoing)==1, (path, graph, outgoing)
    b = Batch(path, graph)
    if outgoing:
        edge = outgoing[0];b.cut(source,'then',edge['to_node'],edge['to_pin'])
    b.fn('voice_call', cls(FRONT)+':'+function, 0, -600)
    for key, value in (pins or {}).items():
        if isinstance(value, tuple): b.link(source, value[0], 'voice_call', key)
        else: b.pin('voice_call', key, value)
    if speaker_from_name:
        b.fn('nightmare', '/Script/Engine.KismetMathLibrary:EqualEqual_NameName', 0,-250, B='Nightmare')
        b.link(source,'Speaker','nightmare','A')
        b.fn('speaker','/Script/Engine.KismetMathLibrary:SelectInt',280,-250,A=4,B=0)
        b.link('nightmare','ReturnValue','speaker','bPickA');b.link('speaker','ReturnValue','voice_call','Speaker')
    if path != FRONT:
        b.fn('front', GS+'GetActorOfClass', -800,-600, ActorClass=cls(FRONT))
        b.node('cast','cast',-400,-600,class_path=cls(FRONT))
        b.link('front','ReturnValue','cast','Object');b.link('cast','AsBP Fo AFront End','voice_call','self')
        b.chain(source,'front','cast','voice_call')
        first = 'front'
    else:
        first = 'voice_call';b.chain(source, first)
    if outgoing:
        b.link('voice_call','then',edge['to_node'],edge['to_pin'])
        if path != FRONT:
            b.link('cast','CastFailed',edge['to_node'],edge['to_pin'])
    b.comment('Character speech', [o['ref'] for o in b.ops if o['op']=='add_node']);result=b.run()
    after_nodes,after_edges=inspect(path,graph)
    added=result['refs']['voice_call']
    assert sum(n['node_id']==added for n in after_nodes)==1
    if outgoing:
        assert any(e['from_node']==added and e['from_pin']=='then' and e['to_node']==edge['to_node'] and e['to_pin']==edge['to_pin'] for e in after_edges),'Original execution continuation lost'
    out=Path('P:/FoA/Saved/CharacterVoice');out.mkdir(parents=True,exist_ok=True)
    (out/(path.rsplit('/',1)[1]+'_'+graph+'_hook.json')).write_text(json.dumps(dict(
        source=source,original_successors=outgoing,voice_node=added,verified=True),indent=2),encoding='utf8')


def story_hooks():
    # Audio starts independently of the subtitle accessibility visibility branch.
    hook(HUD, 'HandleNarration', 'HandleNarration', 'SayCharacter', {'Text':('Line',),'Speaker':0,'Emotion':1})
    hook(FRONT, 'ShowCinematicSubtitle', 'ShowCinematicSubtitle', 'SayCharacter', {'Text':('Line',),'Emotion':2}, True)
    hook(FRONT, 'HideCinematicSubtitle', 'HideCinematicSubtitle', 'StopCharacterVoice')
    hook(FRONT, 'ReturnToTitle', 'ReturnToTitle', 'StopCharacterVoice')
    hook(FRONT, 'RestartDay', 'RestartDay', 'StopCharacterVoice')


def cleanup_hooks():
    for path,event in ((FRONT,'ReceiveEndPlay'),(JOURNEY,'ReceiveEndPlay'),(HUD,'Destruct')):
        node=call('blueprint_add_event',path=path,event_name=event,graph_name='EventGraph',x=0,y=-2600)
        hook(path,'EventGraph',node['title'],'StopCharacterVoice',new_event=not node.get('already_existed',False))
        call('blueprint_compile',path=path,save=True)


def import_profile(index):
    stage=Path(tempfile.gettempdir())/'hayba-asset-connectors'/'main-character-voice'/'waves'
    stage.mkdir(parents=True,exist_ok=True)
    sources=Path('P:/FoA-Assets/audio/character-voices-kokoro-v1/phrases')
    for i in range(6):
        name=f'S_Voice_{PROFILES[index]}_{i:02d}'
        path=ROOT+'/'+name
        if not Path('P:/FoA/Content'+path[5:]+'.uasset').exists():
            shutil.copyfile(sources/(name+'.wav'),stage/(name+'.wav'))
            call('asset_import',source_file=str(stage/(name+'.wav')),destination_path=ROOT,asset_type='sound_wave')
        call('audio_asset_set',path=path,settings=dict(sound_class='/Game/FoA/Audio/Mix/SC_Dialogue',
             looping=False,volume=1.,pitch=1.,compression_quality=70))
        call('asset_save',asset_paths=[path])


def bank_defaults():
    assert all(Path('P:/FoA/Content'+p.split('.')[0][5:]+'.uasset').exists() for p in BANK)
    call('blueprint_set_defaults',path=FRONT,properties={'VoiceBank':BANK})
    call('asset_save',asset_paths=[FRONT])


def capture():
    import time
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/character_voice_capture.py',resources=['asset:'+FRONT,'asset:'+JOURNEY])
    rows=json.loads(Path('P:/FoA/Saved/CharacterVoice/graphs/manifest.json').read_text())
    deadline=time.monotonic()+25
    while not all(Path(r['png']).exists() for r in rows):
        assert time.monotonic()<deadline,'Graph captures did not finish'
        time.sleep(.1)


STEPS = dict(skeleton=skeleton, stop=stop, pick=pick, say=say, wrappers=wrappers, bank=bank_defaults,story_hooks=story_hooks,cleanup=cleanup_hooks,capture=capture)
STEPS.update({f'import{i}':lambda i=i:import_profile(i) for i in range(5)})
if __name__ == '__main__':
    owner = os.environ.get('FOA_AGENT', 'main-character-voice')
    os.environ['FOA_AGENT'] = os.environ['HAYBA_AGENT_ID'] = owner
    step=sys.argv[1]
    touched=[] if step.startswith('import') else ([FRONT,JOURNEY] if step in ('skeleton','capture') else
        [JOURNEY] if step=='wrappers' else [FRONT,HUD] if step=='story_hooks' else
        [FRONT,JOURNEY,HUD] if step=='cleanup' else [FRONT])
    token=editor_lock.acquire(owner, wait_s=5, ttl=180, areas=[FRONT,JOURNEY,HUD,CINE,ROOT])
    try:
        if token:os.environ['FOA_LEASE']=token
        assert not call('editor_get_state')['pie_running']
        for path in (FRONT,JOURNEY,HUD,CINE):
            source=Path('P:/FoA/Content'+path[5:]+'.uasset')
            backup=Path('P:/FoA/Saved/Backups/level-integration-20261112/CharacterVoice')/source.name
            if source.exists() and not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        STEPS[step]()
    finally:
        try:
            for path in touched:
                result=call('blueprint_compile',path=path)
                assert not result.get('error_count'),result
                call('asset_save',asset_paths=[path])
        finally:editor_lock.release(owner)
