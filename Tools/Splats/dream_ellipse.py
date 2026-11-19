"""Full source covariance in UE-local cm²; perspective-correct screen ellipse reference."""
import math

def covariance(sigmas_cm, quaternion):
    w,x,y,z=quaternion
    q=math.sqrt(w*w+x*x+y*y+z*z);w/=q;x/=q;y/=q;z/=q
    # PLY->glTF=(x,-y,-z), glTF->UE=(x,z,y). Quaternions are in parsed PLY space.
    axes=[(1-2*(y*y+z*z),-2*(x*z-w*y),-2*(x*y+w*z)),
          (2*(x*y-w*z),-2*(y*z+w*x),-(1-2*(x*x+z*z))),
          (2*(x*z+w*y),-(1-2*(x*x+y*y)),-2*(y*z-w*x))]
    c=[[sum(sigmas_cm[k]**2*axes[k][i]*axes[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return c[0][0],c[0][1],c[0][2],c[1][1],c[1][2],c[2][2]

def matrix(packed):
    xx,xy,xz,yy,yz,zz=packed
    return [[xx,xy,xz],[xy,yy,yz],[xz,yz,zz]]

def dot(a,b):return sum(x*y for x,y in zip(a,b))

def project(packed,rel,right,up,forward,transform=((1,0,0),(0,1,0),(0,0,1)),perspective=True,tan_half_fov=None,near_clip=1):
    """transform contains local-axis columns in world space; returns a,b,c of projected covariance."""
    depth=dot(rel,forward)
    if perspective and depth<=near_clip:raise ValueError('Camera plane or behind camera')
    slopes=[dot(rel,right)/depth,dot(rel,up)/depth] if perspective else [0,0]
    if perspective and tan_half_fov:
        slopes=[max(-1.3*t,min(1.3*t,s)) for s,t in zip(slopes,tan_half_fov)]
    jr=[r-slopes[0]*f for r,f in zip(right,forward)]
    ju=[u-slopes[1]*f for u,f in zip(up,forward)]
    lr=[dot(jr,axis) for axis in transform];lu=[dot(ju,axis) for axis in transform];c=matrix(packed)
    def bilinear(a,b):return sum(a[i]*c[i][j]*b[j] for i in range(3) for j in range(3))
    return bilinear(lr,lr),bilinear(lr,lu),bilinear(lu,lu)

def ellipse(projected):
    a,b,c=projected;delta=math.hypot(a-c,2*b)
    major=max((a+c+delta)/2,1e-8);minor=max((a+c-delta)/2,1e-8)
    e=(b,major-a)
    if math.hypot(*e)<1e-8:e=(1.,0.)
    length=math.hypot(*e);e=(e[0]/length,e[1]/length)
    return 3*math.sqrt(major),3*math.sqrt(minor),e

BILLBOARD='''// Full source covariance, projected with the local perspective Jacobian.
float3 R = ResolvedView.ViewToTranslatedWorld[0].xyz;
float3 U = ResolvedView.ViewToTranslatedWorld[1].xyz;
float3 F = ResolvedView.ViewToTranslatedWorld[2].xyz;
float3 rel = WP - Cam;
float perspective = 1.0 - ResolvedView.ViewToClip[3][3];
float depth = dot(rel,F);
float nearClip = max(1.0,ResolvedView.NearPlane);
if (perspective > 0.5 && depth <= nearClip) return float3(0,0,0);
// Bound the local perspective slope at a small border beyond the visible frustum.
// Offscreen points beside the eye must not acquire room-sized projected footprints.
float2 slope = float2(dot(rel,R),dot(rel,U))/max(depth,nearClip);
float2 limit = 1.3/max(abs(float2(ResolvedView.ViewToClip[0][0],ResolvedView.ViewToClip[1][1])),float2(0.001,0.001));
slope=clamp(slope,-limit,limit);
float3 JR = R - perspective * slope.x * F;
float3 JU = U - perspective * slope.y * F;
float3 T0 = TransformLocalVectorToWorld(Parameters,float3(1,0,0));
float3 T1 = TransformLocalVectorToWorld(Parameters,float3(0,1,0));
float3 T2 = TransformLocalVectorToWorld(Parameters,float3(0,0,1));
float3 lr = float3(dot(JR,T0),dot(JR,T1),dot(JR,T2));
float3 lu = float3(dot(JU,T0),dot(JU,T1),dot(JU,T2));
float3x3 C = float3x3(Cov0.x,Cov0.y,Cov1.x, Cov0.y,Cov1.y,Cov2.x, Cov1.x,Cov2.x,Cov2.y);
float a=dot(lr,mul(C,lr)), b=dot(lr,mul(C,lu)), c=dot(lu,mul(C,lu));
float delta=sqrt(max(0,(a-c)*(a-c)+4*b*b));
float major=max((a+c+delta)*0.5,0.000001), minor=max((a+c-delta)*0.5,0.000001);
float2 e=float2(b,major-a);
e=dot(e,e)>0.00000001 ? normalize(e) : float2(1,0);
float2 f=float2(-e.y,e.x);
float2 offset=(e*sqrt(major)*Corner.x+f*sqrt(minor)*Corner.y)*(3.0*Scale);
return R*offset.x+U*offset.y;'''

COVERAGE='''// Standard Gaussian through three sigma. Preserve source alpha; no tail subtraction.
float a = A * exp(-4.5 * dot(Corner,Corner));
return a > InterleavedGradientNoise(Parameters.SvPosition.xy + RS.y*117.0, View.StateFrameIndexMod8) ? 1.0 : 0.0;'''
