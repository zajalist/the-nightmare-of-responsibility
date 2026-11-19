"""Execute generated voice graph operations offline; native pins still need a compile."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import build_character_voice as voice
import build_drive
from held_tool_graphs import Batch


def plan(name, build):
    entry={'node_id':'entry','title':name}
    with patch.object(build_drive,'inspect',return_value=([entry],[])), patch.object(Batch,'run',lambda self:self.ops):
        result=[]
        original=build_drive.G.finish
        def capture(self):
            result.extend(original(self));return result
        with patch.object(build_drive.G,'finish',capture):build()
    return result


GRAPHS={n:plan(n,f) for n,f in [('SayCharacter',voice.say),('StopCharacterVoice',voice.stop),('PickCharacterVoice',voice.pick)]}


class Run:
    def __init__(self):
        self.state=dict(VoiceLine='',VoiceSpeaker=-1,VoiceEmotion=-1,VoiceVariant=1,VoiceAudio=None,VoiceBank=voice.BANK)
        self.state.update({f'VoiceVariant{i}':1 for i in range(5)})
        self.played=[];self.stopped=[];self.paused=False

    def call(self,name,**args):
        ops=GRAPHS[name]
        nodes={o['ref']:o for o in ops if o['op']=='add_node'}
        wires={(o['to_node'],o['to_pin']):(o['from_node'],o['from_pin']) for o in ops if o['op']=='connect'}
        defaults={(o['node_id'],o['pin_name']):o['value'] for o in ops if o['op']=='set_pin'}
        outputs={}
        def inp(node,pin,default=None):
            if (node,pin) in wires:return val(*wires[node,pin])
            raw=defaults.get((node,pin),default)
            if raw in ('true','false'):return raw=='true'
            try:return float(raw) if '.' in str(raw) and not str(raw).startswith('/') else int(raw)
            except (TypeError,ValueError):return raw
        def val(node,pin):
            if node=='entry':return args[pin]
            spec=nodes[node];kind=spec['node_type']
            if kind=='variable_get':return self.state[spec['variable_name']]
            if kind=='get_array_item':return inp(node,'Array')[inp(node,'Dimension 1')]
            if kind=='cast':return inp(node,'Object')
            if (node,pin) in outputs:return outputs[node,pin]
            fn=spec['function_name'].split(':')[-1]
            a=lambda:inp(node,'A');b=lambda:inp(node,'B')
            funcs={'Not_PreBool':lambda:not a(),'BooleanAND':lambda:a() and b(),
                'EqualEqual_StrStr':lambda:a()==b(),'EqualEqual_IntInt':lambda:a()==b(),
                'Greater_IntInt':lambda:a()>b(),'Subtract_IntInt':lambda:a()-b(),
                'Multiply_IntInt':lambda:a()*b(),'Add_IntInt':lambda:a()+b(),
                'Clamp':lambda:max(inp(node,'Min'),min(inp(node,'Max'),inp(node,'Value'))),
                'SelectInt':lambda:a() if inp(node,'bPickA') else b(),
                'SelectObject':lambda:a() if inp(node,'bSelectA') else b(),
                'Conv_TextToString':lambda:inp(node,'InText'),'Trim':lambda:inp(node,'SourceString').lstrip(),
                'TrimTrailing':lambda:inp(node,'SourceString').rstrip(),'Len':lambda:len(inp(node,'S')),
                'Concat_StrStr':lambda:(a() or '')+(b() or ''),'IsValid':lambda:bool(inp(node,'Object')),
                'IsGamePaused':lambda:self.paused}
            return funcs[fn]()
        def next_node(node,pin='then'):
            return next((o['to_node'] for o in ops if o['op']=='connect' and o['from_node']==node and o['from_pin']==pin and o['to_pin']=='execute'),None)
        node=next_node('entry')
        while node:
            spec=nodes[node];kind=spec['node_type'];side='then'
            if kind=='branch':side='then' if inp(node,'Condition') else 'else'
            elif kind=='variable_set':self.state[spec['variable_name']]=inp(node,spec['variable_name'])
            elif kind=='call_function':
                fn=spec['function_name'].split(':')[-1]
                if fn in GRAPHS:self.call(fn)
                elif fn=='Stop':self.stopped.append(inp(node,'self'))
                elif fn=='CreateSound2D':
                    assert not inp(node,'bPersistAcrossLevelTransition') and inp(node,'bAutoDestroy')
                    sound=inp(node,'Sound');self.played.append(sound);outputs[node,'ReturnValue']=f'audio{len(self.played)}'
                elif fn=='SetUISound':assert not inp(node,'bInUISound')
                elif fn=='Play':assert inp(node,'self')
                else:raise AssertionError(fn)
            node=next_node(node,side)


r=Run()
say=lambda text,speaker=0,emotion=1:r.call('SayCharacter',Text=text,Speaker=speaker,Emotion=emotion)
say(' First line ');first=r.played[-1]
for _ in range(100):say('First line')
assert len(r.played)==1 and not r.stopped
say('NPC line',1);say('Second player line')
assert r.played[-1]!=first and len(r.stopped)==2
say('Third player line');assert r.played[-1]==first
r.call('StopCharacterVoice');say('Third player line');assert len(r.played)==5
say('');assert r.state['VoiceLine']==''
count=len(r.played);r.paused=True;say('Paused line');assert len(r.played)==count
r.paused=False;say('Resumed line',99,-5);assert r.state['VoiceSpeaker']==4 and r.state['VoiceEmotion']==0
assert all('/Dialogue/S_Voice_' in p for p in r.played)
print('PASS generated graphs: text dedup, speaker isolation, per-speaker alternation, stop/reentry, blank interruption, pause and input clamps')
