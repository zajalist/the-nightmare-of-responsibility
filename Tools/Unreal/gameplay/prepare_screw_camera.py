"""Camera-only in-place native BP patch. --inspect is default; --apply requires root clearance.
Adds a mode-specific camera setter immediately before existing entry view blend.
No stance, targets, animation, input, release or key-camera changes.
"""
import datetime,hashlib,json,math,os,shutil,sys
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
P='/Game/FoA/Gameplay/BP_Door';G='SetDoorToolPresentation';K='/Script/Engine.KismetMathLibrary:';SC='/Script/Engine.SceneComponent:'
MODE=sys.argv[1] if len(sys.argv)>1 else '--inspect';assert MODE in ('--inspect','--apply')
owner=os.environ.get('FOA_AGENT','character_camera');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'Do not inspect/mutate graph while user plays'
token=h.lease_acquire(owner,['asset:'+P],ttl_s=40,wait_s=3)
def normal(s):return ''.join(str(s).lower().split())
def rot(eye,aim):
    d=[a-b for a,b in zip(aim,eye)]
    return '(Pitch='+str(math.degrees(math.atan2(d[2],math.hypot(*d[:2]))))+',Yaw='+str(math.degrees(math.atan2(d[1],d[0])))+',Roll=0)'
try:
    nodes,edges=inspect(P,G)
    assert not any(normal(n.get('title',''))=='screwdriverframing' or n.get('comment')=='Screwdriver framing' for n in nodes),'Already patched; inspect existing camera nodes'
    # There are entry/restore blends. Entry is the view whose target comes from Self.
    views=[n for n in nodes if normal(n['title'])=='setviewtargetwithblend']
    by_id={n['node_id']:n for n in nodes};candidates=[]
    for view in views:
        targets=[e for e in edges if e['to_node']==view['node_id'] and e['to_pin']=='NewViewTarget']
        if any(normal(by_id[e['from_node']]['title']) in ('self','self-reference') for e in targets):candidates.append(view['node_id'])
    assert len(candidates)==1,('Entry view not unambiguous',views)
    view=candidates[0];incoming=[e for e in edges if e['to_node']==view and e['to_pin']=='execute'];assert len(incoming)==1
    b=Batch(P,G);b.get('frame_mode','ToolMode',4300,2400);b.get('frame_camera','ToolCamera',4300,2600)
    b.fn('frame_screw',K+'EqualEqual_NameName',4600,2400,B='Screwdriver');b.link('frame_mode','ToolMode','frame_screw','A')
    b.fn('frame_position',K+'SelectVector',4900,2400,A='-48,-144,108',B='-30,-144,102')
    b.fn('frame_aim',K+'SelectVector',4900,2650,A='-12,-84,91',B='-7,-84,88')
    b.fn('frame_rotation',K+'FindLookAtRotation',5200,2650)
    b.link('frame_position','ReturnValue','frame_rotation','Start');b.link('frame_aim','ReturnValue','frame_rotation','Target')
    b.fn('frame_fov',K+'SelectFloat',4900,2900,A=44.,B=36.)
    for ref in ('frame_position','frame_aim','frame_fov'):b.link('frame_screw','ReturnValue',ref,'bPickA')
    b.fn('set_frame',SC+'K2_SetRelativeLocationAndRotation',5250,2400,bSweep=False,bTeleport=True)
    b.link('frame_camera','ToolCamera','set_frame','self');b.link('frame_position','ReturnValue','set_frame','NewLocation');b.link('frame_rotation','ReturnValue','set_frame','NewRotation')
    b.fn('set_frame_fov','/Script/Engine.CameraComponent:SetFieldOfView',5550,2400)
    b.link('frame_camera','ToolCamera','set_frame_fov','self');b.link('frame_fov','ReturnValue','set_frame_fov','InFieldOfView')
    edge=incoming[0];b.cut(edge['from_node'],edge['from_pin'],view,'execute')
    b.link(edge['from_node'],edge['from_pin'],'set_frame','execute');b.chain('set_frame','set_frame_fov',view)
    b.comment('Screwdriver framing',[o['ref'] for o in b.ops if 'ref' in o])
    out=Path('P:/FoA/Saved/Integration/cinematic_audit');out.mkdir(exist_ok=True)
    protected=['Content/FoA/Characters/Player/BP_FoAPlayer.uasset','Content/FoA/Cinematics/LS_WakeUp.uasset','Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset']
    hashes=lambda:{p:hashlib.sha256(Path('P:/FoA',p).read_bytes()).hexdigest() for p in protected}
    before=hashes();report=dict(mode=MODE,ops=b.ops,before_nodes=nodes,before_edges=edges,protected_sha256=before)
    if MODE=='--apply':
        backup=Path('P:/FoA/Saved/Backups/screw_camera')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
        shutil.copy2('P:/FoA/Content/FoA/Gameplay/BP_Door.uasset',backup/'BP_Door.uasset')
        report['batch']=b.run();assert hashes()==before
        after_nodes,after_edges=inspect(P,G)
        # Existing nodes/pins are untouched; one entry exec edge is replaced, everything else retained.
        after_by={n['node_id']:n for n in after_nodes}
        for node in nodes:
            n=after_by[node['node_id']]
            assert n['title']==node['title']
        edgekey=lambda e:(e['from_node'],e['from_pin'],e['to_node'],e['to_pin'])
        protected_edges={edgekey(e) for e in edges if e!=edge}
        assert protected_edges<={edgekey(e) for e in after_edges}
        report.update(backup=str(backup),protected_after=hashes(),unrelated_edges_preserved=len(protected_edges))
    (out/('screw_camera_'+MODE[2:]+'.json')).write_text(json.dumps(report,indent=2))
    print('SCREW_CAMERA',MODE,'prepared',len(b.ops),'ops')
finally:h.release(owner,token)
