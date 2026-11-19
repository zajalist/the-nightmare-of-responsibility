"""Offline syntax/type check of the splat Custom-node HLSL with DXC, before it reaches the shared editor:
    python Tools/Splats/hlsl/check_hlsl.py [path/to/dxc.exe]
Each node's code is wrapped like UE's CustomExpressionN(Parameters, inputs...), with the engine symbols it uses
stubbed (ResolvedView, View, helpers). Catches typos and type errors; the editor compile stays the final word."""
import os
import subprocess
import sys
import tempfile

H = os.path.dirname(os.path.abspath(__file__))
DXC = sys.argv[1] if len(sys.argv) > 1 else r"C:\VulkanSDK\1.4.357.0\Bin\dxc.exe"
STUB = """
#define MaterialFloat float
#define MaterialFloat2 float2
#define MaterialFloat3 float3
#define MaterialFloat4 float4
struct FWSVector3 { float3 v; };
float3 WSHackToFloat(FWSVector3 x) { return x.v; }
struct FMaterialVertexParameters { float3 WorldPosition; FWSVector3 PreViewTranslation; float4 SvPosition; float3x3 TangentToWorld; };
struct FViewState { float4x4 ViewToTranslatedWorld; float4x4 ViewToClip; float3 TranslatedWorldCameraOrigin; float4 ViewSizeAndInvSize; float StateFrameIndexMod8; };
static FViewState ResolvedView;
static FViewState View;
float3 GetTranslatedWorldPosition(FMaterialVertexParameters P) { return P.WorldPosition; }
FWSVector3 GetPreViewTranslation(FMaterialVertexParameters P) { return P.PreViewTranslation; }
float3 TransformLocalVectorToWorld(FMaterialVertexParameters P, float3 v) { return v * 1.01; }
Texture2D Tex; SamplerState TexSampler;
float4 Texture2DSample(Texture2D t, SamplerState s, float2 uv) { return t.Sample(s, uv); }
float4 Texture2DSampleLevel(Texture2D t, SamplerState s, float2 uv, float l) { return t.SampleLevel(s, uv, l); }
float InterleavedGradientNoise(float2 uv, float f) { return frac(52.98 * frac(dot(uv + f, float2(0.067, 0.0058)))); }
"""
NODES = {  # node: (files, return type, inputs[, additional outputs])
    "l2_dynamics": (("l2_dynamics.hlsl",), "float4",
                    "float3 Rest, float2 RS, float3 CornerOffset, float Clock, float4 Local, float Building, float Ambient, float3 Centre, float Radius, float Progress, float4 Wind, float Target, float4 Impact, float ReduceMotion"),
    "flow_eval": (("flow_lib.hlsl", "flow_eval.hlsl"), "float3",
                  "float3 RestPos, float2 RadiusSeed, float Clock, float3 Mode, float4 TimeCfg, float4 Flow, float4 Shape, float4 Place, float4 Tune, float4 Dissolve",
                  "float3 OffsetPrev, float4 Look"),   # additional outputs: UE passes them as inout params
    "billboard_quad": (("billboard_quad.hlsl",), "float3",
                       "float2 Corner, float2 RadiusSeed, float3 Offset, float3 OffsetPrev, float4 Look, float4 Splat"),
    "billboard_coverage": (("billboard_coverage.hlsl",), "float",
                           "float2 RadiusSeed, float3 Offset, float3 OffsetPrev, float4 Look, float4 Splat"),
    "gaussian_footprint": (("gaussian_footprint.hlsl",), "float", "float2 Corner, float Alpha, float Smoke, float4 Splat"),
    "gaussian_dither": (("gaussian_dither.hlsl",), "float", "float Opacity, float2 RadiusSeed"),
    "player_crawl": (("player_crawl.hlsl",), "float3", "float3 Offset, float4 PlayerPos, float2 RadiusSeed, float Time"),
    "spill_grain": (("spill_grain.hlsl",), "float4", "float3 WP, float3 Nv, float3 VC, float4 Spill, float T, float3 O, float3 V, float4 Sheen, float4 Rim, float VA"),
    "spill_feather": (("spill_feather.hlsl",), "float", "float3 WP, float VC, float4 Gap"),
    "spill_rim": (("spill_rim.hlsl",), "float3", "float3 N, float3 WP, float3 V, float4 Rim, float4 VC"),
    "overlay_climb": (("overlay_climb.hlsl",), "float", "float3 WP, float4 PlayerPos, float Amount"),
    "skin_sand": (("skin_sand.hlsl",), "float4", "float3 P, float Clock, float Amount, float ReduceMotion, float Transition"),
    "skin_sand_slip": (("skin_sand_slip.hlsl",), "float3", "float3 P, float Clock, float Amount, float ReduceMotion, float Transition"),
    "morph_offset": (("morph_offset.hlsl",), "float3", "float Idx, float2 RadiusSeed, float3 Rest, float Clock, float4 Ev, float4 Cfg"),
    "morph_look": (("morph_look.hlsl",), "float4", "float Idx, float Clock, float4 Ev, float4 Cfg"),
    "shade": (("shade.hlsl",), "float4",
              "float3 Color, float Opacity, float2 RadiusSeed, float4 Look, float Coverage, float3 Offset, float Time, float4 Light, float4 Sand"),
}
ok = True
for name, (files, ret, args, *outs) in NODES.items():
    code = "".join(open(os.path.join(H, f), encoding="utf-8").read() for f in files)
    if name=='l2_dynamics':
        sys.path.insert(0,os.path.dirname(H))
        import build_splat_dynamics
        code=build_splat_dynamics.dynamics_code()
    outs = [o.strip().split() for o in outs[0].split(",")] if outs else []
    sig = args + "".join(f", inout {t} {n}" for t, n in outs)
    call = ", ".join(f"({t})b" if t.startswith("float") and t != "float" else "a.x" for t in (s.split()[0] for s in args.split(",")))
    call += "".join(f", x{i}" for i in range(len(outs)))
    decl = "".join(f"{t} x{i} = ({t})0; " for i, (t, _) in enumerate(outs))
    keep = "".join(f" + x{i}.xxxx" for i in range(len(outs)))  # keep the outputs live
    src = STUB + f"\n{ret} Node(FMaterialVertexParameters Parameters, {sig})\n{{\n{code}\n}}\n" \
        + f"float4 main(float4 a : A, float4 b : B, float4 c : C) : SV_Position {{ FMaterialVertexParameters P = (FMaterialVertexParameters)0; P.WorldPosition = a.xyz; {decl}" \
        + f"float4 r = float4(Node(P, {call})" + (".xxxx" if ret == "float" else ".xyzz" if ret == "float3" else "") + f"); return r{keep}; }}\n"
    pixel = name.startswith(("spill", "overlay")) or name == "skin_sand"
    if pixel:
        src = src.replace(": SV_Position {", ": SV_Target {")
    with tempfile.NamedTemporaryFile("w", suffix=".hlsl", delete=False, encoding="utf-8") as f:
        f.write(src)
    r = subprocess.run([DXC, "-T", "ps_6_0" if pixel else "vs_6_0", "-E", "main", "-HV", os.environ.get("HLSL_VERSION", "2021"), f.name], capture_output=True, text=True)
    good = r.returncode == 0
    ok &= good
    print(f"{name:20s} {'OK' if good else 'FAIL'}")
    if not good:
        print(r.stderr[:3000])
    os.unlink(f.name)
sys.exit(0 if ok else 1)
