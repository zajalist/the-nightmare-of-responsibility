float off = Scale * (1.0 + 0.3 * sin(T * 1.2566)) * ddy(UV).y;
float ea = 0.0;
[unroll] for (int k = 1; k <= 4; k++)
{
    float2 e = UV - float2(0.0, k * off);
    ea += Texture2DSample(Glyphs, GlyphsSampler, e).a * step(0.0, e.y) * (0.22 / k);
}
return ea * Echo;
