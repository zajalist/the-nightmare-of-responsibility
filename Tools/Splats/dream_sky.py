"""Texture-free dark dream atmosphere; shared shader and offline reference."""
import math

SKY_CODE='''// Directional haze and broad drifting cloud strata. No room photograph or texture reads.
float3 d = normalize(-Dir);
float t = Clock * 0.003;
float horizon = exp(-abs(d.z) * 5.5);
float a = sin(d.x * 6.0 + d.y * 3.0 + sin(d.z * 7.0) * 1.8 + t);
float b = sin(d.y * 9.0 - d.z * 5.0 + sin(d.x * 4.0 + t) * 2.0);
float c = sin(d.z * 13.0 + d.x * 7.0 - d.y * 4.0 - t * 0.6);
float cloud = smoothstep(-0.35, 0.85, a * 0.55 + b * 0.3 + c * 0.15);
float upper = smoothstep(-0.2, 0.5, d.z);
float3 dark = float3(0.0025, 0.0035, 0.006);
float3 haze = float3(0.017, 0.020, 0.024) * horizon;
float3 veil = float3(0.011, 0.014, 0.020) * cloud * (0.25 + 0.75 * upper);
return dark + haze + veil;'''

def smoothstep(lo,hi,x):
    t=max(0.,min(1.,(x-lo)/(hi-lo)))
    return t*t*(3-2*t)

def colour(direction,seconds=0.):
    """Same arithmetic as shader, with outward view direction rather than CameraVectorWS."""
    length=math.sqrt(sum(v*v for v in direction));x,y,z=(v/length for v in direction);t=seconds*.003
    a=math.sin(x*6+y*3+math.sin(z*7)*1.8+t)
    b=math.sin(y*9-z*5+math.sin(x*4+t)*2)
    c=math.sin(z*13+x*7-y*4-t*.6)
    cloud=smoothstep(-.35,.85,a*.55+b*.3+c*.15)
    upper=smoothstep(-.2,.5,z);horizon=math.exp(-abs(z)*5.5)
    return tuple(d+h*horizon+v*cloud*(.25+.75*upper)
                 for d,h,v in zip((.0025,.0035,.006),(.017,.020,.024),(.011,.014,.020)))

def specs(custom):
    return [('cam','CameraVectorWS',[-900,0],{}),('time','Time',[-900,200],{}),
            ('sky','Custom',[-540,0],custom('Dark dream atmosphere','CMOT_Float3',('Dir','Clock'),SKY_CODE))]
