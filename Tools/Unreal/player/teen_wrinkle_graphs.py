"""Bone-driven cloth folds, reusing the existing 30 Hz player publisher with a 10 Hz gate.
Matches Tools/Cloth/wrinkle_driver.py; native component color setters cache material instances.
Run setup_teen_wrinkles.py once, compile, then this script under a player lease.
"""
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/Characters/Player/BP_FoAPlayer'
K='/Script/Engine.KismetMathLibrary:'
C=P+'.BP_FoAPlayer_C:'

def reset(name):
    nodes,_=inspect(P,name);e=find(nodes,name)
    returns=[n['node_id'] for n in nodes if n['title']=='Return Node']
    b=Batch(P,name);remove=[n['node_id'] for n in nodes if n['node_id'] not in [e,*returns]]
    if remove:b.ops.append(dict(op='remove',node_ids=remove))
    return b,e,returns

def weight():
    b,e,ends=reset('ClothBendWeight');assert len(ends)==1,ends
    for i,axis in enumerate(('A','B')):
        b.fn('n'+axis,K+'Normal',250,i*200);b.link(e,axis,'n'+axis,'A')
    b.fn('dot',K+'Dot_VectorVector',500,200)
    for axis in ('A','B'):b.link('n'+axis,'ReturnValue','dot',axis)
    b.fn('clamp',K+'FClamp',750,200,Min=-1,Max=1);b.link('dot','ReturnValue','clamp','Value')
    b.fn('angle',K+'DegAcos',1000,200);b.link('clamp','ReturnValue','angle','A')
    b.fn('range',K+'MapRangeClamped',1250,200,OutRangeA=0,OutRangeB=1)
    b.link('angle','ReturnValue','range','Value');b.link(e,'Low','range','InRangeA');b.link(e,'High','range','InRangeB')
    b.fn('square',K+'Multiply_DoubleDouble',1500,200)
    b.link('range','ReturnValue','square','A');b.link('range','ReturnValue','square','B')
    b.fn('twice',K+'Multiply_DoubleDouble',1500,400,B=2);b.link('range','ReturnValue','twice','A')
    b.fn('slope',K+'Subtract_DoubleDouble',1750,400,A=3);b.link('twice','ReturnValue','slope','B')
    b.fn('smooth',K+'Multiply_DoubleDouble',2000,200)
    b.link('square','ReturnValue','smooth','A');b.link('slope','ReturnValue','smooth','B')
    b.link('smooth','ReturnValue',ends[0],'Weight');b.chain(e,ends[0])
    b.comment('Smooth joint flexion',[o['ref'] for o in b.ops if 'ref' in o]);b.run()

def update():
    b,e,_=reset('UpdateClothWrinkles')
    b.fn('now','/Script/Engine.KismetSystemLibrary:GetGameTimeInSeconds',0,300)
    b.get('last','ClothLastUpdate',0,500)
    b.fn('dt',K+'Subtract_DoubleDouble',250,300);b.link('now','ReturnValue','dt','A');b.link('last','ClothLastUpdate','dt','B')
    b.fn('ready',K+'GreaterEqual_DoubleDouble',500,300,B=.1);b.link('dt','ReturnValue','ready','A')
    b.node('gate','branch',500,0);b.link('ready','ReturnValue','gate','Condition');b.chain(e,'gate')
    b.fn('velocity','/Script/Engine.Actor:GetVelocity',750,500)
    b.fn('speed',K+'VSizeXY',1000,500);b.link('velocity','ReturnValue','speed','A')
    b.fn('dtcap',K+'FClamp',750,700,Min=0,Max=.2);b.link('dt','ReturnValue','dtcap','Value')
    b.fn('travel',K+'Multiply_DoubleDouble',1250,500);b.link('speed','ReturnValue','travel','A');b.link('dtcap','ReturnValue','travel','B')
    b.get('distance','ClothDistance',1000,900)
    b.fn('sum',K+'Add_DoubleDouble',1500,500);b.link('distance','ClothDistance','sum','A');b.link('travel','ReturnValue','sum','B')
    b.set('setdistance','ClothDistance',1000,0);b.link('sum','ReturnValue','setdistance','ClothDistance');b.chain('gate','setdistance')
    b.set('settime','ClothLastUpdate',1400,0);b.link('now','ReturnValue','settime','ClothLastUpdate');b.chain('setdistance','settime')
    b.get('body','Body',1800,1000)
    bones=['pelvis','spine_01','spine_03','neck_01']+[name+'_'+s for s in 'lr' for name in ('upperarm','lowerarm','hand','thigh','calf','foot')]
    for i,name in enumerate(bones):
        b.fn(name,'/Script/Engine.SceneComponent:GetSocketLocation',2000+(i%4)*250,900+(i//4)*250,InSocketName=name)
        b.link('body','Body',name,'self')
    def delta(ref,a,c,x,y):
        b.fn(ref,K+'Subtract_VectorVector',x,y);b.link(a,'ReturnValue',ref,'A');b.link(c,'ReturnValue',ref,'B')
    delta('down','pelvis','spine_03',3100,900)
    delta('chest','neck_01','spine_03',3100,1100)
    delta('pelvisup','spine_01','pelvis',3100,1300)
    b.fn('spine',C+'ClothBendWeight',3400,1100,Low=30,High=62)
    b.link('chest','ReturnValue','spine','A');b.link('pelvisup','ReturnValue','spine','B')
    b.fn('radians',K+'Multiply_DoubleDouble',1800,400,B=.04487989505128276)
    b.link('setdistance','Output_Get','radians','A')
    b.fn('sin',K+'Sin',2050,400);b.link('radians','ReturnValue','sin','A')
    b.fn('drift',K+'Multiply_DoubleDouble',2300,400,B=.35);b.link('sin','ReturnValue','drift','A')
    tail='settime'
    for si,s in enumerate('lr'):
        x=3800+si*2200
        for ref,a,c in [('upper','lowerarm','upperarm'),('fore','hand','lowerarm'),('thigh','calf','thigh'),('calf','foot','calf')]:
            delta(ref+s,a+'_'+s,c+'_'+s,x,700+len(ref)*120)
        weights=[]
        for i,(name,a,c,low,high) in enumerate([('elbow','upper'+s,'fore'+s,45,130),('arm','upper'+s,'down',20,80),('hip','thigh'+s,'down',15,75),('knee','thigh'+s,'calf'+s,12,100)]):
            ref=name+s;b.fn(ref,C+'ClothBendWeight',x+300,700+i*220,Low=low,High=high)
            b.link(a,'ReturnValue',ref,'A');b.link(c,'ReturnValue',ref,'B');weights.append((ref,'Weight'))
        b.fn('torso'+s,K+'FMax',x+600,1200);b.link('spine','Weight','torso'+s,'A');b.link('hip'+s,'Weight','torso'+s,'B')
        weights[2]=('torso'+s,'ReturnValue')
        for kind in ('Weights','Phases'):
            name='Wrinkle'+kind+s.upper();b.fn(name+'color',K+'MakeColor',x+1000,600 if kind=='Weights' else 1700)
            for channel,(ref,pin) in zip('RGBA',weights):
                if kind=='Phases':
                    m=name+channel;b.fn(m,K+'Multiply_DoubleDouble',x+600,1700+'RGBA'.index(channel)*180,B=1.2);b.link(ref,pin,m,'A')
                    b.fn(m+'p',K+('Add_DoubleDouble' if s=='l' else 'Subtract_DoubleDouble'),x+800,1700+'RGBA'.index(channel)*180)
                    b.link(m,'ReturnValue',m+'p','A');b.link('drift','ReturnValue',m+'p','B');ref,pin=m+'p','ReturnValue'
                b.link(ref,pin,name+'color',channel)
            b.set(name,name,x+1000,0 if kind=='Weights' else 200);b.link(name+'color','ReturnValue',name,name)
            b.chain(tail,name);tail=name
    # A seated hip must crease trousers, not the entire polo front. Preserve
    # the common published values for lower/full garments; upper garments
    # use the measured spine flexion in their torso channel.
    upper={}
    for si,s in enumerate('LR'):
        for ki,kind in enumerate(('Weights','Phases')):
            param='Wrinkle'+kind+s;ref='upper'+str(si)+str(ki)
            b.fn(ref+'br',K+'BreakColor',8000,2000+si*600+ki*250)
            b.link(param,'Output_Get',ref+'br','InColor')
            b.fn(ref,K+'MakeColor',8400,2000+si*600+ki*250)
            for channel in 'RGA':b.link(ref+'br',channel,ref,channel)
            if kind=='Weights':b.link('spine','Weight',ref,'B')
            else:
                b.fn(ref+'mul',K+'Multiply_DoubleDouble',8000,2500+si*600,B=1.2)
                b.link('spine','Weight',ref+'mul','A')
                b.fn(ref+'phase',K+('Add_DoubleDouble' if s=='L' else 'Subtract_DoubleDouble'),8200,2500+si*600)
                b.link(ref+'mul','ReturnValue',ref+'phase','A');b.link('drift','ReturnValue',ref+'phase','B')
                b.link(ref+'phase','ReturnValue',ref,'B')
            upper[param]=ref
    for i,part in enumerate(('StartOutfit','StartPants','Shirt','Trousers','Suit')):
        x=8500+i*1400;b.get(part,part,x,1000)
        for j,param in enumerate(('WrinkleWeightsL','WrinkleWeightsR','WrinklePhasesL','WrinklePhasesR')):
            ref='apply'+str(i)+str(j);b.fn(ref,'/Script/Engine.MeshComponent:SetColorParameterValueOnMaterials',x+j*300,0,ParameterName=param)
            b.link(part,part,ref,'self')
            if part in ('StartOutfit','Shirt'):b.link(upper[param],'ReturnValue',ref,'ParameterValue')
            else:b.link(param,'Output_Get',ref,'ParameterValue')
            b.chain(tail,ref);tail=ref
    from hayba_call import call
    if call('blueprint_inspect_graph',dict(path=P,graph_name='UpdateClothCorruption')).get('ok'):
        b.fn('corruption',C+'UpdateClothCorruption',15800,0);b.chain(tail,'corruption')
    b.comment('Fold with the animated joints',[o['ref'] for o in b.ops if 'ref' in o]);b.run()
    nodes,edges=inspect(P,'UpdatePlayerPos')
    if not any(n['title']=='UpdateClothWrinkles' for n in nodes):
        tails=[n for n in nodes if any(p['name']=='then' for p in n['pins']) and not any(e['from_node']==n['node_id'] and e['from_pin']=='then' for e in edges)]
        assert len(tails)==1,tails
        hook=Batch(P,'UpdatePlayerPos');hook.fn('cloth',C+'UpdateClothWrinkles',2000,0);hook.chain(tails[0]['node_id'],'cloth');hook.run()

{'weight':weight,'update':update}[sys.argv[1]]()
