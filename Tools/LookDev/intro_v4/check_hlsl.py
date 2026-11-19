"""Offline DXC check of the intro plate HLSL, wrapped like UE's Custom node (intro lane):
  python Tools/LookDev/intro_v4/check_hlsl.py [dxc.exe]   -> exit 0 when it compiles for ps_6_0"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story import hlsl_table  # noqa: E402

DXC = sys.argv[1] if len(sys.argv) > 1 else r'C:\VulkanSDK\1.4.357.0\Bin\dxc.exe'
code = open('P:/FoA/Tools/LookDev/hlsl/intro_plate_v4.hlsl', encoding='utf-8').read().replace('// @@TABLE@@', hlsl_table())
src = ('float4 Texture2DSampleLevel(Texture2D t, SamplerState s, float2 uv, float l) { return t.SampleLevel(s, uv, l); }\n'
       'Texture2D PT; SamplerState PS; Texture2D BT; SamplerState BS; Texture2D NT; SamplerState NS;\n'
       'float4 CustomExpression0(float2 UV, Texture2D Plate, SamplerState PlateSampler, Texture2D Back, SamplerState BackSampler,'
       ' Texture2D Noise, SamplerState NoiseSampler, float Age, float Motion, float Panel, float Calm)\n{\n' + code + '\n}\n'
       'float4 main(float2 uv : TEXCOORD0, float4 p : TEXCOORD1) : SV_Target { return CustomExpression0(uv, PT, PS, BT, BS, NT, NS, p.x, p.y, p.z, p.w); }\n')
d = tempfile.mkdtemp()
open(os.path.join(d, 'c.hlsl'), 'w').write(src)
r = subprocess.run([DXC, '-T', 'ps_6_0', '-E', 'main', os.path.join(d, 'c.hlsl'), '-Fo', os.path.join(d, 'c.dxil')], capture_output=True, text=True)
print('dxc', r.returncode, (r.stdout + r.stderr)[-2000:])
sys.exit(r.returncode)
