"""Offline asset/geometry checks and execution of generated stop-progression wire plans.

This catches gate/ordering regressions before native authoring. It does not claim
Unreal pin/schema, animation contact, lighting or real-input verification.
"""
from pathlib import Path
import unittest
import build_drive as b
import build_journey as j
import build_stop_set as s
import stop_set_data as d
import build_interview as interview

plans={}
original_inspect,original_run=b.inspect,b.G.run
b.inspect=lambda path,name:([dict(node_id='entry',title=name)],[])
b.G.run=lambda self:plans.__setitem__((self.path,self.graph),self)
for fn in j.GRAPHS.values():fn()
for fn in s.GRAPHS.values():fn()
for fn in interview.GRAPHS.values():fn()
b.inspect,b.G.run=original_inspect,original_run


def literal(value):
    if value=='true':return True
    if value=='false':return False
    if isinstance(value,str):
        try:return float(value) if '.' in value else int(value)
        except ValueError:pass
    return value


class Flow:
    """Small evaluator for the generated Journey gates, using the real exec/data wires."""
    def __init__(self,state):self.state=state;self.calls=[];self.timers={}
    def run(self,name,args=None):
        plan=plans[j.BP,name];nodes={};inputs={};edges={}
        for op in plan.ops:
            if op['op']=='add_node':nodes[op['ref']]=op
            elif op['op']=='set_pin':inputs[op['node_id'],op['pin_name']]=literal(op['value'])
            elif op['op']=='connect':
                if op['to_pin']=='execute':edges[op['from_node'],op['from_pin']]=op['to_node']
                else:inputs[op['to_node'],op['to_pin']]=(op['from_node'],op['from_pin'])
        def pin(ref,key,default=None):
            value=inputs.get((ref,key),default)
            return evaluate(*value) if isinstance(value,tuple) else value
        def evaluate(ref,out='ReturnValue'):
            if ref=='entry':return (args or {}).get(out)
            node=nodes[ref];kind=node['node_type']
            if kind=='self':return self.state
            if kind in ('variable_get','variable_set'):
                target=pin(ref,'self',self.state)
                return target.get(node['variable_name']) if target else None
            if kind=='cast':return pin(ref,'Object')
            fn=node.get('function_name','').rsplit(':',1)[-1]
            a=pin(ref,'A');bb=pin(ref,'B')
            if fn.startswith('EqualEqual_'):return a==bb
            if fn.startswith('NotEqual_'):return a!=bb
            if fn.startswith('GreaterEqual_'):return a>=bb
            if fn.startswith('Greater_'):return a>bb
            if fn=='BooleanAND':return bool(a and bb)
            if fn=='BooleanOR':return bool(a or bb)
            if fn=='Not_PreBool':return not a
            if fn.startswith('Add_'):return a+bb
            if fn.startswith('Multiply_'):return a*bb
            if fn.startswith('Divide_'):return a//bb if fn.endswith('IntInt') else a/bb
            if fn=='Conv_IntToDouble':return float(pin(ref,'InInt'))
            if fn=='Conv_IntToString':return str(pin(ref,'InInt'))
            if fn=='Conv_StringToText':return pin(ref,'InString')
            if fn=='Concat_StrStr':return str(a)+str(bb)
            if fn in ('Clamp','FClamp'):return max(pin(ref,'Min'),min(pin(ref,'Max'),pin(ref,'Value')))
            if fn=='SelectInt':return a if pin(ref,'bPickA') else bb
            if fn=='IsValid':return pin(ref,'Object') is not None
            if fn=='IsInViewport':return True
            return None
        current=edges.get(('entry','then'));steps=0
        while current:
            steps+=1;assert steps<500,'Unexpected execution loop'
            node=nodes[current];kind=node['node_type'];port='then'
            if kind=='branch':port='then' if pin(current,'Condition') else 'else'
            elif kind=='cast':port='then' if pin(current,'Object') is not None else 'CastFailed'
            elif kind=='variable_set':
                target=pin(current,'self',self.state);target[node['variable_name']]=pin(current,node['variable_name'])
            elif kind=='call_function':
                full=node['function_name'];fn=full.rsplit(':',1)[-1];self.calls.append(fn)
                if fn=='ApplyMerge':self.state['visual_amount']=pin(current,'Amount')
                elif fn=='Learn':self.state['learned'].add(pin(current,'Flag'))
                elif fn=='K2_SetTimer':self.timers[pin(current,'FunctionName')]=pin(current,'Time')
                elif fn=='K2_ClearTimer':self.timers.pop(pin(current,'FunctionName'),None)
                elif full.startswith(j.cls(j.BP)+':') and fn not in ('StartFinale','ReapplyStageView','EnsureDialogue','RenderDialogue','HideDialogue'):
                    self.run(fn)
            current=edges.get((current,port))


def state(**change):
    result=dict(Phase=4,Stop=1,Employability=20,StopBusy=False,StopActionState=1,StopActionDone=False,
        Edited0=True,Edited1=False,Edited2=False,Assisted=False,HUD={},Game={},StopSet={'ActionDone':False},learned=set(),
        DialogueMode=0,DialogueState=0,DialogueReady=False,DialogueHeld=False)
    result.update(change);return result


class StopSets(unittest.TestCase):
    def test_reuses_existing_assets_and_unique_components(self):
        names=['Root',*d.GROUPS,'StageCamera','Key','Fill']+[r[0] for r in d.MESHES+d.SIGNS+d.FIGURES]
        self.assertEqual(len(names),len(set(names)))
        paths={r[2] for r in d.MESHES}|{r[5] for r in d.MESHES if r[5]}|{d.MANNY,d.SAND,d.SIT,d.PICKUP}
        for path in paths:
            if path.startswith('/Game/'):
                self.assertTrue(Path('P:/FoA/Content'+path[5:]+'.uasset').exists(),path)
        for name,_,_,at,dimensions,_ in d.MESHES:
            self.assertTrue(all(x>0 for x in dimensions),name)
        floor=next(r for r in d.MESHES if r[0]=='Floor')
        self.assertEqual(floor[3][2]+floor[4][2],0)
        for at,_ in d.CAMERAS.values():self.assertTrue(-400<at[0]<560 and -440<at[1]<440 and 0<at[2]<320)

    def test_label_action_is_visible_and_complete_before_callback(self):
        self.assertEqual([d.label_roll(i,0) for i in range(3)],list(d.LABEL_ROLL))
        self.assertNotEqual(d.label_roll(0,.5),d.LABEL_ROLL[0])
        self.assertEqual([d.label_roll(i,d.ACTION_SECONDS) for i in range(3)],[0,0,0])
        plan=plans[s.BP,'ActionStep']
        self.assertTrue(any(literal(o.get('value'))==d.ACTION_SECONDS for o in plan.ops))
        self.assertTrue(any(o.get('function_name','').endswith(':StopActionFinished') for o in plan.ops))

    def test_stock_scale_and_names_remain_readable_at_the_action_shelf(self):
        meshes={r[0]:r for r in d.MESHES};signs={r[0]:r for r in d.SIGNS}
        for i,name in enumerate(d.STOCK_NAMES):
            stock=meshes['Stock'+str(i)];label=meshes['Label'+str(i)]
            self.assertIn(stock[2],(d.CUBE,d.CYLINDER))
            self.assertLessEqual(max(stock[4]),50,'Stock must be retail packaging, not torso-sized books')
            self.assertEqual(stock[5],d.PAINT)
            self.assertLessEqual(abs(stock[3][1]-label[3][1]),1)
            self.assertEqual(signs['StockText'+str(i)][2],name)
            self.assertNotIn('StockText'+str(i),d.WHITE_SIGNS,'White packaging needs dark product lettering')

    def test_interview_hides_every_stop_only_prop_and_staff_follower(self):
        plan=plans[s.BP,'PrepareInterview']
        nodes={o['ref']:o for o in plan.ops if o['op']=='add_node'}
        wires={(o['to_node'],o['to_pin']):o['from_node'] for o in plan.ops if o['op']=='connect'}
        pins={(o['node_id'],o['pin_name']):literal(o['value']) for o in plan.ops if o['op']=='set_pin'}
        hidden=set()
        for ref,node in nodes.items():
            if not node.get('function_name','').endswith(':SetVisibility'):continue
            if pins.get((ref,'bNewVisibility')) is False and pins.get((ref,'bPropagateToChildren')) is True:
                hidden.add(nodes[wires[ref,'self']]['variable_name'])
        parents={r[0]:r[1] for r in d.MESHES+d.SIGNS+d.FIGURES}
        parents.update(dict(d.EXTRA_GROUPS))
        for name in d.STAFF:
            parents.update({name+'Face':name,name+'Suit':name})
        # Only the desk and its single paper are deliberately reused by interview.
        for name in set(parents)-{'OfficeDesk','OfficePaper'}:
            chain={name};parent=parents.get(name)
            while parent and parent not in chain:
                chain.add(parent);parent=parents.get(parent)
            self.assertTrue(chain & hidden,(name,'would leak into the separate interview set'))
        cleanup=[o.get('function_name','').rsplit(':',1)[-1] for o in plans[j.BP,'ReleaseStop'].ops]
        self.assertLess(cleanup.index('Restore'),cleanup.index('K2_DestroyActor'))
        restore=[o.get('function_name','').rsplit(':',1)[-1] for o in plans[s.BP,'Restore'].ops]
        self.assertIn('K2_ClearTimer',restore);self.assertIn('ClearPose',restore)

    def test_grocery_writing_camera_stays_in_front_of_the_opaque_shelf_back(self):
        shelf=next(row for row in d.MESHES if row[0]=='ShelfBack')
        self.assertLess(d.WRITER_CAMERAS[1][0][0],shelf[3][0]-shelf[4][0]/2)
        self.assertEqual(set(d.WRITER_CAMERAS),{0,1,2})

    def test_confirm_cannot_claim_action(self):
        st=state();f=Flow(st);f.run('Confirm')
        self.assertEqual((st['Phase'],st['StopActionDone'],st['Employability']),(4,False,20))
        st.update(Phase=5,StopActionState=10);f.run('ConfirmEdit')
        self.assertEqual(st['Employability'],20)
        self.assertFalse(st['learned'])

    def test_use_waits_for_actual_completion(self):
        st=state();f=Flow(st);f.run('UseStop')
        self.assertEqual((st['StopBusy'],st['StopActionState'],st['StopActionDone']),(True,2,False))
        f.run('StopActionFinished');self.assertFalse(st['StopActionDone'])
        st['StopSet']['ActionDone']=True;f.run('StopActionFinished')
        self.assertEqual((st['StopBusy'],st['StopActionState'],st['StopActionDone']),(False,3,True))
        self.assertEqual(st['DialogueMode'],2,'Completed task must enter its contact debrief')

    def test_rejection_reverts_without_grant_then_edit_grants_once(self):
        st=state(StopActionDone=True,StopActionState=3,DialogueMode=2,DialogueState=1);f=Flow(st)
        f.run('DialogueAdvance')  # completed contact reply -> rejection pulse
        self.assertEqual((st['Phase'],st['Employability'],st['visual_amount']),(4,20,.4))
        self.assertTrue(st['StopBusy']);self.assertEqual(f.timers['EndMergePreview'],d.PREVIEW_SECONDS)
        f.run('Confirm');self.assertEqual(st['Phase'],4)
        f.run('EndMergePreview');self.assertEqual(st['visual_amount'],.2)
        f.run('Confirm');self.assertEqual(st['Phase'],5)
        f.run('Confirm');self.assertEqual((st['Phase'],st['Employability'],st['Stop']),(11,40,2))
        f.run('ConfirmEdit');self.assertEqual(st['Employability'],40)
        self.assertEqual(st['learned'],{'Knows.L2Logistics'})

    def test_normal_and_assisted_retry_are_separate(self):
        for function,expected in [('RetryDraft',False),('RetryWithoutTiming',True)]:
            st=state(Phase=7,Assisted=not expected);f=Flow(st);f.run(function)
            self.assertEqual(st['Assisted'],expected);self.assertIn('StartFinale',f.calls)

    def test_cleanup_never_teleports_player_and_cancels_owned_timers(self):
        for path,name in ((j.BP,'ReleaseStop'),(s.BP,'Restore'),(s.BP,'ClearPose')):
            functions=[o.get('function_name','') for o in plans[path,name].ops]
            self.assertFalse(any('SetActorLocation' in fn or 'SetActorTransform' in fn for fn in functions),name)
        st=state();f=Flow(st);f.timers={n:1 for n in ('StageStop','FinishReturnToCar','EndMergePreview')}
        f.run('ReleaseStop');self.assertEqual(f.timers,{})

    def test_every_generated_wire_has_a_declared_node_and_single_data_source(self):
        for key,plan in plans.items():
            refs={'entry'};inputs=set()
            for op in plan.ops:
                if op['op']=='add_node':self.assertNotIn(op['ref'],refs);refs.add(op['ref'])
                if op['op']=='connect':
                    self.assertIn(op['from_node'],refs,key);self.assertIn(op['to_node'],refs,key)
                    if op['to_pin']!='execute':
                        dest=(op['to_node'],op['to_pin']);self.assertNotIn(dest,inputs,key);inputs.add(dest)


if __name__=='__main__':unittest.main()
