"""Execute generated hold/release Blueprint wire plans offline, not a parallel model."""
import math
import unittest
from types import SimpleNamespace
from threshold_walk_proof import WalkProof
import build_drive as b
import build_threshold as t
import threshold_data as d

plans={}
HOLD,RELEASE=math.ceil(d.BREATH_HOLD/.1)+3,math.ceil(d.BREATH_RELEASE/.1)+2  # ticks of .1 s
b.inspect=lambda path,name:([dict(node_id='entry',title=name)],[])
b.G.run=lambda self:plans.__setitem__((self.path,self.graph),self)
for name in (*t.walk.GRAPHS,'StartPath','Step','BeginFall','RestartFromRoad','RestoreRoom'):
    t.STEPS[name]()


def literal(value):
    if value in ('true','false'):return value=='true'
    if isinstance(value,str):
        try:return float(value) if '.' in value else int(value)
        except ValueError:pass
    return value


class VM:
    def __init__(self,**changes):
        self.s=dict(Phase=3,Age=20,RouteBeat=0,BreathState=0,BreathAge=0.,ReleaseAge=0.,BreathArmed=False,
            Replay=False,Player={'Location':d.EXIT},Phone={'bOpen':False},Game={'SaveSlot':'FoA_QA_Play'},
            CityStream={},HUD={},RouteGuide={},Splat={},Down=False,ReduceMotion=0,
            Stage=0,StageAge=0.,Torment=0.,TormentGoal=0.,ShakeAge=0.,ThoughtLine='',ThoughtUntil=0.)
        self.s.update(changes);self.calls=[]
        self.s['Player'].setdefault('CharacterMovement',{'MaxWalkSpeed':d.PATH_SPEED})
    def run(self,name,args=None):
        nodes={};ports={};edges={}
        for op in plans[t.BP,name].ops:
            if op['op']=='add_node':nodes[op['ref']]=op
            elif op['op']=='set_pin':ports[op['node_id'],op['pin_name']]=literal(op['value'])
            elif op['op']=='connect':
                if op['to_pin']=='execute':edges[op['from_node'],op['from_pin']]=op['to_node']
                else:ports[op['to_node'],op['to_pin']]=(op['from_node'],op['from_pin'])
        def pin(ref,key,default=None):
            value=ports.get((ref,key),default)
            return ev(*value) if isinstance(value,tuple) else value
        def vector(v):return tuple(map(float,v.split(','))) if isinstance(v,str) else v
        def ev(ref,out='ReturnValue'):
            if ref=='entry':return (args or {}).get(out)
            n=nodes[ref];kind=n['node_type']
            if kind=='self':return self.s
            if kind in ('variable_get','variable_set'):
                target=pin(ref,'self',self.s);return target.get(n['variable_name']) if target is not None else None
            if kind=='cast':return pin(ref,'Object')
            fn=n.get('function_name','').rsplit(':',1)[-1];a=pin(ref,'A');bb=pin(ref,'B')
            if fn.startswith('EqualEqual_'):return a==bb
            if fn.startswith('GreaterEqual_'):return a>=bb
            if fn.startswith('Greater_'):return a>bb
            if fn.startswith('LessEqual_'):return a<=bb
            if fn.startswith('Less_'):return a<bb
            if fn=='BooleanAND':return bool(a and bb)
            if fn=='BooleanOR':return bool(a or bb)
            if fn=='Not_PreBool':return not a
            if fn in ('Add_DoubleDouble','Add_IntInt'):return a+bb
            if fn in ('Subtract_DoubleDouble','Subtract_IntInt'):return a-bb
            if fn in ('Multiply_DoubleDouble','Multiply_IntInt'):return a*bb
            if fn=='Divide_DoubleDouble':return a/bb
            if fn=='Lerp':return a+(bb-a)*pin(ref,'Alpha')
            if fn=='FInterpTo':
                cur,goal=pin(ref,'Current'),pin(ref,'Target')
                return cur+(goal-cur)*max(0,min(1,pin(ref,'DeltaTime')*pin(ref,'InterpSpeed')))
            if fn=='Subtract_VectorVector':return tuple(x-y for x,y in zip(vector(a),vector(bb)))
            if fn in ('FClamp','Clamp'):return max(pin(ref,'Min'),min(pin(ref,'Max'),pin(ref,'Value')))
            if fn.startswith('Select'):return a if (pin(ref,'bPickA') if fn!='SelectObject' else pin(ref,'bSelectA')) else bb
            if fn=='MakeVector':return tuple(pin(ref,k,0) for k in ('X','Y','Z'))
            if fn=='BreakVector':return vector(pin(ref,'InVec'))[('X','Y','Z').index(out)]
            if fn=='Vector_Distance' or fn=='Vector_Distance2D':
                aa,bb=vector(pin(ref,'V1')),vector(pin(ref,'V2'));count=2 if fn.endswith('2D') else 3
                return math.sqrt(sum((aa[i]-bb[i])**2 for i in range(count)))
            if fn=='K2_GetActorLocation':return pin(ref,'self')['Location']
            if fn=='GetGameInstance':return self.s['Game']
            if fn=='GetTimeSeconds':return self.s['Age']
            if fn=='IsValid':return pin(ref,'Object') is not None
            if fn=='IsInputKeyDown':return self.s['Down']
            if fn=='GetScalarParameterValue':return self.s['ReduceMotion']
            return None
        current=edges.get(('entry','then'));steps=0
        while current:
            steps+=1;assert steps<500
            n=nodes[current];kind=n['node_type'];port='then'
            if kind=='branch':port='then' if pin(current,'Condition') else 'else'
            elif kind=='cast':port='then' if pin(current,'Object') is not None else 'CastFailed'
            elif kind=='variable_set':pin(current,'self',self.s)[n['variable_name']]=pin(current,n['variable_name'])
            elif kind=='call_function':
                full=n['function_name'];fn=full.rsplit(':',1)[-1];self.calls.append(fn)
                if fn=='K2_SetActorLocation':pin(current,'self',self.s)['Location']=pin(current,'NewLocation')
                if fn=='SetCinematic':self.s['cinematic']=pin(current,'bEnable')
                if full.startswith(t.cls(t.BP)+':') and fn in t.walk.GRAPHS and fn!='RefreshPath':
                    arguments={k:pin(current,k) for r,k in ports if r==current and k!='self'}
                    self.run(fn,arguments)
            current=edges.get((current,port))
    def tick(self,down,count=1,delta=.1):
        for _ in range(count):self.run('StepBreath',dict(Delta=delta,Down=down))
    def earn(self):
        self.run('StartHeadache');self.tick(False);self.tick(True,HOLD);self.tick(False,RELEASE)


class WalkTests(unittest.TestCase):
    def test_destroyed_python_wrapper_closes_without_touching_input(self):
        proof=object.__new__(WalkProof)
        def invalid(_):raise TypeError('ObjectInstance is null')
        proof.u=SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=invalid))
        proof.world=proof.th=proof.gi=proof.pc=object()
        proof.request_input=lambda _:self.fail('Dead world received input')
        self.assertFalse(proof.alive());proof.close()
        def unrelated(_):raise TypeError('unexpected API signature')
        proof.u.SystemLibrary.is_valid=unrelated
        with self.assertRaisesRegex(TypeError,'unexpected API'):proof.alive()

    def test_real_input_driver_runs_generated_walk_and_releases_keys(self):
        v=VM(Age=0,Player={'Location':d.ENTRY});clock=[0.];keys=set();pending=[];world=object()
        v.s['Game']['DayCount']=2
        class Obj:
            def __init__(self,data):self.data=data
            def get_editor_property(self,name):return self.data[name]
            def get_world(self):return world
        class Key:
            def set_editor_property(self,name,value):self.name=value
        pc=SimpleNamespace(is_input_key_down=lambda key:key.name in keys)
        engine=SimpleNamespace(Key=Key,SystemLibrary=SimpleNamespace(is_valid=lambda obj:obj is not None),
            GameplayStatics=SimpleNamespace(get_game_instance=lambda w:Obj(v.s['Game']),get_player_controller=lambda w,i:pc),
            UnrealEditorSubsystem=None,get_editor_subsystem=lambda _:SimpleNamespace(get_game_world=lambda:world))
        proof=WalkProof(world,Obj(v.s),lambda args:pending.append((clock[0]+.3,args)),engine=engine,now=lambda:clock[0])
        for i in range(440):
            clock[0]+=.1
            while pending and pending[0][0]<=clock[0]:
                _,args=pending.pop(0)
                if args['event']=='pressed':keys.add(args['key'])
                else:keys.discard(args['key'])
            if v.s['Phase']==3:
                v.s['Age']+=.1;v.s['Down']='E' in keys
                if 'W' in keys and v.s['BreathState']==0:
                    x,y,z=v.s['Player']['Location'];v.s['Player']['Location']=(x,y+d.PATH_SPEED*.1,z)
                v.run('StepPath',{'Delta':.1})
                # The VM recurses only owned new graphs, so execute the external
                # existing BeginFall at its generated call site for this fixture.
                if v.calls and v.calls[-1]=='BeginFall':v.run('BeginFall')
            proof.tick(.1)
            if proof.done:break
        self.assertTrue(proof.result['passed'],proof.result)
        self.assertFalse(keys);self.assertEqual(v.s['RouteBeat'],2)
        events=[row['event'] for row in proof.result['trace']]
        self.assertIn('early_release_reset',events);self.assertIn('full_hold_waited_for_release',events)

    def test_preheld_and_held_forever_never_complete(self):
        v=VM();v.run('StartHeadache');v.tick(True,500)
        self.assertEqual((v.s['BreathState'],v.s['RouteBeat']),(1,0))
        v.tick(False);v.tick(True,500)
        self.assertEqual((v.s['BreathState'],v.s['RouteBeat']),(3,0))

    def test_early_release_resets_hold_and_requires_new_full_hold(self):
        v=VM();v.run('StartHeadache');v.tick(False);v.tick(True,10);v.tick(False)
        self.assertEqual((v.s['BreathState'],v.s['BreathAge'],v.s['RouteBeat']),(1,0,0))
        v.tick(True,HOLD);v.tick(False,RELEASE);self.assertEqual(v.s['RouteBeat'],1)

    def test_repress_during_exhale_cannot_award_and_no_auto_repeat(self):
        v=VM();v.run('StartHeadache');v.tick(False);v.tick(True,HOLD);v.tick(False,3);v.tick(True)
        self.assertEqual((v.s['RouteBeat'],v.s['BreathState']),(0,3))
        v.tick(False,RELEASE);v.tick(False,500);self.assertEqual(v.s['RouteBeat'],1)
        v.earn();v.run('FinishBreath');self.assertEqual(v.s['RouteBeat'],2);self.assertFalse(v.s['cinematic'])

    def test_timeout_and_qa_play_never_bypass_but_f6_context_does(self):
        v=VM(Age=999);v.run('BeginFall');self.assertEqual(v.s['Phase'],3)
        v.s['Game']['SaveSlot']='FoA_QA_DebugSkip';v.run('BeginFall');self.assertEqual(v.s['Phase'],4)
        n=v.calls.count('PlayFall');v.run('BeginFall');self.assertEqual(v.calls.count('PlayFall'),n)

    def test_earned_fall_requires_exit_and_replay_still_works(self):
        v=VM(Player={'Location':d.ENTRY});v.earn();v.earn();v.run('BeginFall');self.assertEqual(v.s['Phase'],3)
        v.s['Player']['Location']=d.EXIT;v.run('BeginFall');self.assertEqual(v.s['Phase'],4)
        v=VM(Phase=2,Replay=True);v.run('BeginFall');self.assertEqual(v.s['Phase'],4)

    def test_boundary_recovers_preserves_earned_beats_and_cleanup_resets(self):
        v=VM(RouteBeat=1,BreathState=2,Player={'Location':(20000,-80000,-100)})
        v.run('StepPath',{'Delta':.1})
        self.assertEqual(v.s['Player']['Location'],(d.OFFSET[0],d.OFFSET[1]+d.SAFE_Y[1],92))
        self.assertEqual((v.s['RouteBeat'],v.s['BreathState'],v.s['Phase']),(1,0,3))
        v.s['Phase']=-1;v.run('ResetPath');self.assertEqual(v.s['RouteBeat'],0)

    def test_frame_hitch_never_grants_a_whole_hold(self):
        v=VM();v.run('StartHeadache');v.tick(False);v.tick(True);v.tick(True,delta=30)
        self.assertAlmostEqual(v.s['BreathAge'],d.MAX_STEP);self.assertLess(d.MAX_STEP,d.BREATH_HOLD/2)

    def play(self,v,walk=True,limit=90.):
        """A player who holds W (or stands still) and breathes as soon as asked; returns (stage times, seconds)."""
        t=0.;seen=[]
        while v.s['Phase']==3 and t<limit:
            t+=.1;v.s['Age']+=.1;state=v.s['BreathState']
            v.s['Down']=(state==1 and v.s['BreathArmed']) or state==2
            if walk and state==0:
                x,y,z=v.s['Player']['Location'];speed=v.s['Player']['CharacterMovement']['MaxWalkSpeed']
                v.s['Player']['Location']=(x,y+speed*.1,z)
            before=v.s['Stage'];v.run('StepPath',{'Delta':.1})
            if v.s['Stage']!=before:seen.append((round(t,1),v.s['Stage'],round(v.s['Player']['Location'][1]-d.OFFSET[1])))
            if v.calls and v.calls[-1]=='BeginFall':v.run('BeginFall')
        return seen,t

    def test_torment_stages_rise_in_order_and_the_walk_reaches_the_fall(self):
        v=VM(Age=0,Player={'Location':d.ENTRY},TormentGoal=.15);seen,t=self.play(v)
        self.assertEqual([s for _,s,_ in seen][:8],[1,2,3,4,5,6,7,8],seen)
        self.assertEqual((v.s['Phase'],v.s['RouteBeat']),(4,2))
        gaps=[b[0]-a[0] for a,b in zip(seen,seen[1:]) if b[1] not in (5,)]
        self.assertGreaterEqual(min(gaps),d.STAGE_GAP[0]-.11,seen)
        self.assertTrue(12<=t<=40,(t,seen))
        # pressure slowed him, and the breaths settled it again
        self.assertLess(v.s['Torment'],.5)

    def test_standing_still_never_stalls_the_torment(self):
        v=VM(Age=0,Player={'Location':d.ENTRY},TormentGoal=.15);seen,_=self.play(v,walk=False,limit=40)
        self.assertGreaterEqual(v.s['RouteBeat'],2,seen)
        self.assertEqual(v.s['Phase'],3,'an idle player must still walk to EXIT himself')

    def test_hands_rise_at_his_feet_and_breath_eases_the_pressure(self):
        v=VM(Age=0,Player={'Location':d.ENTRY},Stage=2,StageAge=5.,TormentGoal=.55)
        v.run('StepPath',{'Delta':.1});self.assertEqual(v.s['Stage'],3)
        self.assertIn('K2_SetWorldLocation',v.calls);self.assertEqual(v.calls.count('RiseFear'),2)
        v.s['Torment']=1.;v.run('StartHeadache');v.tick(False)
        for _ in range(20):v.s['Down']=True;v.run('StepPath',{'Delta':.1})
        self.assertEqual(v.s['BreathState'],2);self.assertLess(v.s['Torment'],.9)

    def test_all_generated_wires_resolve(self):
        for key,p in plans.items():
            refs={'entry'};data=set()
            for op in p.ops:
                if op['op']=='add_node':self.assertNotIn(op['ref'],refs);refs.add(op['ref'])
                if op['op']=='connect':
                    self.assertIn(op['from_node'],refs,key);self.assertIn(op['to_node'],refs,key)
                    if op['to_pin']!='execute':
                        pin=(op['to_node'],op['to_pin']);self.assertNotIn(pin,data,key);data.add(pin)


if __name__=='__main__':unittest.main()
