// Nine taps of the actual game capture. No illustration texture or replacement art.
// Ink RGB = shadow-edge pooling, dry brush, paper variation.
struct RiceInk
{
    float Hash(float2 p)
    {
        float3 p3 = frac(float3(p.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return frac((p3.x + p3.y) * p3.z);
    }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        f = f*f*(3.0-2.0*f);
        return lerp(lerp(Hash(i),Hash(i+float2(1,0)),f.x),
                    lerp(Hash(i+float2(0,1)),Hash(i+1.0),f.x),f.y);
    }
    float Luma(float3 color)
    {
        return pow(saturate(dot(color,float3(0.2126,0.7152,0.0722))),0.56);
    }
};
RiceInk ink;
float2 q = saturate(UV);
float2 px = float2(1.0/1920.0,1.0/1080.0);
float2 nearTap = px*2.2, farTap = px*7.5;
float4 source = Texture2DSample(Frame,FrameSampler,q);
float l = ink.Luma(source.rgb);
float a = ink.Luma(Texture2DSample(Frame,FrameSampler,q-float2(nearTap.x,0)).rgb);
float b = ink.Luma(Texture2DSample(Frame,FrameSampler,q+float2(nearTap.x,0)).rgb);
float c = ink.Luma(Texture2DSample(Frame,FrameSampler,q-float2(0,nearTap.y)).rgb);
float d = ink.Luma(Texture2DSample(Frame,FrameSampler,q+float2(0,nearTap.y)).rgb);
float e = ink.Luma(Texture2DSample(Frame,FrameSampler,q-float2(farTap.x,0)).rgb);
float f = ink.Luma(Texture2DSample(Frame,FrameSampler,q+float2(farTap.x,0)).rgb);
float g = ink.Luma(Texture2DSample(Frame,FrameSampler,q-float2(0,farTap.y)).rgb);
float h = ink.Luma(Texture2DSample(Frame,FrameSampler,q+float2(0,farTap.y)).rgb);
float soft = l*.24+(a+b+c+d)*.10+(e+f+g+h)*.09;
float pool = ink.Noise(q*float2(17,11));
float bloom = ink.Noise(q*float2(43,27)+pool*2.5);
float fiber = ink.Noise(q*float2(440,1700));
float tooth = ink.Noise(q*float2(1100,380));
float contour = smoothstep(.035,.22,length(float2(b-a,d-c)));
float density = 1.0-smoothstep(.015,.98,soft);
// Uneven absorption preserves broad washes instead of posterized bands or hatching.
// Avoid symmetric gradient outlines: they darken both sides of bevel highlights.
float pigment = saturate(density*(.86+.14*bloom));
float dry = smoothstep(.62,.86,tooth)*smoothstep(.30,.85,pigment);
pigment *= 1.0-dry*Ink.y;
float edgePool = saturate((e+f+g+h)*.25-l)*contour;
pigment = saturate(pigment+edgePool*.24);
// Display palette: ivory #EEE4CC, charcoal #333A3B, blue-gray #687D86, ochre #B59A69.
float3 paper = pow(float3(238,228,204)/255.0,2.2);
float3 charcoal = pow(float3(51,58,59)/255.0,2.2);
float3 blueGray = pow(float3(104,125,134)/255.0,2.2);
float3 ochre = pow(float3(181,154,105)/255.0,2.2);
paper *= 1.0+(fiber-.5)*Ink.z+(pool-.5)*.025;
float3 pigmentColor = lerp(charcoal,blueGray,.20+.18*pool);
// Absorptive glazing keeps broad charcoal pools dark without outlining every edge.
float3 color = paper*pow(max(pigmentColor/paper,.001),pigment*1.25);
float middle = smoothstep(.12,.32,density)*(1.0-smoothstep(.72,.96,density));
color = lerp(color,ochre,middle*smoothstep(.45,.85,bloom)*.12);
// Deposit only on the darker side of a boundary, preserving paper highlights.
color = lerp(color,charcoal,edgePool*Ink.x*(.7+.3*bloom));
// A capillary front develops once per panel; reduced motion supplies Reveal=1.
float front = q.x*.43+q.y*.16+pool*.25+bloom*.10;
float developed = smoothstep(front-.075,front+.075,Reveal*1.12);
developed = max(developed,step(.999,Reveal));
float wetEdge = (1.0-smoothstep(.008,.055,abs(front-Reveal*1.12)))*(1.0-step(.999,Reveal));
color = lerp(color,pigmentColor,wetEdge*density*.13);
float edge = min(min(q.x,1.0-q.x),min(q.y,1.0-q.y));
float border = smoothstep(.006+pool*.008,.026+pool*.012,edge);
return float4(saturate(color),source.a*border*developed);

