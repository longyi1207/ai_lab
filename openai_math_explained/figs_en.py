"""SVG figures for the OpenAI-math explainer deck (English edition). All plotted numbers are computed here, not hand-typed."""
import math

STYLE = '''
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .z { font: 11px system-ui, sans-serif; fill: #55524a; }
    .h { font: 600 11.5px ui-monospace, monospace; fill: #9a5b12; }
    .r { font: 600 11px ui-monospace, monospace; fill: #b03a2e; }
    .g { font: 600 11px ui-monospace, monospace; fill: #2e7d4f; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .boxr { fill: #fbeceb; stroke: #b03a2e; }
    .boxg { fill: #eaf5ee; stroke: #2e7d4f; }
    .boxa { fill: #fff6e9; stroke: #9a5b12; }
    .ax { stroke: #8a867a; stroke-width: 1; fill: none; }
    .grid { stroke: rgba(26,26,24,0.08); stroke-width: 1; }
    .dash { stroke: #8a867a; stroke-width: 1; stroke-dasharray: 4 3; fill: none; }
    .ln { stroke: #1a1a18; stroke-width: 1.6; fill: none; }
    .lnr { stroke: #b03a2e; stroke-width: 2; fill: none; }
    .lna { stroke: #9a5b12; stroke-width: 1.8; fill: none; }
    .lnb { stroke: #2f5d8a; stroke-width: 1.8; fill: none; }
    .lng { stroke: #8a867a; stroke-width: 1.6; fill: none; }
    .arr { stroke: #8a867a; stroke-width: 1.2; fill: none; marker-end: url(#mr); }
    .arrr { stroke: #b03a2e; stroke-width: 1.4; fill: none; marker-end: url(#mrr); }
  </style>
  <defs>
    <marker id="mr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/></marker>
    <marker id="mrr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#b03a2e"/></marker>
  </defs>'''


def fig(svg_body, viewbox, cap):
    return f'''
<div class="svg-fig">
<svg viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg">{STYLE}
{svg_body}
</svg>
<p class="cap">{cap}</p>
</div>'''


def pts(seq):
    return ' '.join(f'{x:.1f},{y:.1f}' for x, y in seq)


# ------------------------------------------------------------------ 17 fields bar chart
FIELDS = [
    ('Theoretical CS', 40), ('Combinatorics', 37), ('Algebraic/complex geom.', 36), ('Number theory', 31),
    ('Probability/stat. mech.', 29), ('Differential geometry', 29), ('Mathematical physics', 25), ('Operator algebras', 19),
    ('Topology', 18), ('Algebra', 18), ('Real/complex analysis', 16), ('PDE', 16),
    ('Convex/metric geometry', 15), ('Group theory', 14), ('Dynamics/ergodic theory', 12), ('Functional analysis', 11), ('Logic', 6),
]
DEEP = {'Theoretical CS', 'Combinatorics', 'Number theory', 'Probability/stat. mech.', 'Mathematical physics', 'Group theory', 'PDE', 'Algebraic/complex geom.'}


def svg_fields():
    out = ['<text x="20" y="20" class="h">372 result families by field (orange = this deck covers at least one result in depth)</text>']
    y = 42
    for name, n in FIELDS:
        w = n * 11
        cls = 'boxa' if name in DEEP else 'box'
        out.append(f'<text x="150" y="{y+11}" class="z" text-anchor="end">{name}</text>')
        out.append(f'<rect x="160" y="{y}" width="{w}" height="14" rx="2" class="{cls}"/>')
        out.append(f'<text x="{166+w}" y="{y+11}" class="s">{n}</text>')
        y += 20
    return fig('\n'.join(out), f'0 0 720 {y+10}',
               'Source: the 17 subject sections of <a href="https://github.com/openai/math/blob/main/overview.pdf">openai/math overview.pdf</a>, counted entry by entry (total 372). Catalog numbers 045/061/070/123/163 are unused; no reason given.')


# ------------------------------------------------------------------ trust stack
def svg_trust():
    rows = [
        ('① Lean kernel checks every proof step', 'this repo: sorry = 0, added axioms = 0, native_decide = 0', 'boxg', 'g', 'strong'),
        ('② Only the 3 standard axioms', 'all 416 Comparator configs allow only propext / Quot.sound / Classical.choice', 'boxg', 'g', 'strong'),
        ('③ Lean statement = what the paper claims?', 'challenge files written by OpenAI (agents); a human must read the definitions', 'boxa', 'h', 'human'),
        ('④ Are definitions in deps and patches right?', '24 patches (largest ~2 MB) + 11 lana-agents/* dependencies of unknown origin', 'boxa', 'h', 'unaudited'),
        ('⑤ The ~58% with no formalization', 'no machine check at all; the 3 Hodge-related papers withdrawn on 10-07 were here', 'boxr', 'r', 'none'),
    ]
    out = ['<text x="20" y="20" class="h">What "has a Lean proof" guarantees: the trust stack, bottom up</text>']
    y = 36
    for title, sub, cls, tcls, verdict in rows:
        out.append(f'<rect x="20" y="{y}" width="600" height="46" rx="4" class="{cls}"/>')
        out.append(f'<text x="34" y="{y+19}" class="t">{title}</text>')
        out.append(f'<text x="34" y="{y+36}" class="s">{sub}</text>')
        out.append(f'<text x="640" y="{y+28}" class="{tcls}">{verdict}</text>')
        y += 54
    return fig('\n'.join(out), f'0 0 720 {y+4}',
               '①② are guaranteed by the machine; ③④⑤ still need humans. Audit data: source grep of <code>lean/OAI/</code> (122,458 .lean files, ~26M lines) plus Comparator config counts (2026-10-08, commit fd4aeeb); not compiled.')


# ------------------------------------------------------------------ zeta zero-free regions
def svg_zeta():
    X0, X1, R0, R1 = 80, 640, -0.2, 1.3
    Y0, Y1, T1 = 300, 40, 30.0
    sx = lambda r: X0 + (r - R0) / (R1 - R0) * (X1 - X0)
    sy = lambda t: Y0 - t / T1 * (Y0 - Y1)
    out = []
    # shaded regions
    out.append(f'<rect x="{sx(0.875):.1f}" y="{Y1}" width="{sx(R1)-sx(0.875):.1f}" height="{Y0-Y1}" fill="#fbeceb"/>')
    curve = [(sx(1 - 0.1 / math.log(t + 2)), sy(t)) for t in [i * 0.5 for i in range(0, 61)]]
    poly = curve + [(sx(1.0), sy(T1)), (sx(1.0), sy(0))]
    out.append(f'<polygon points="{pts(poly)}" fill="#e4e0d8"/>')
    out.append(f'<polyline points="{pts(curve)}" class="lng"/>')
    # axes and lines
    out.append(f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>')
    for r, lab, cls in [(0, 'Re=0', 'ax'), (0.5, 'Re=½', 'dash'), (1.0, 'Re=1', 'ax')]:
        out.append(f'<line x1="{sx(r):.1f}" y1="{Y0}" x2="{sx(r):.1f}" y2="{Y1}" class="{cls}"/>')
        out.append(f'<text x="{sx(r):.1f}" y="{Y0+16}" class="s" text-anchor="middle">{lab}</text>')
    out.append(f'<line x1="{sx(0.875):.1f}" y1="{Y0}" x2="{sx(0.875):.1f}" y2="{Y1}" class="lnr"/>')
    out.append(f'<text x="{sx(0.875):.1f}" y="{Y0+16}" class="r" text-anchor="middle">7/8</text>')
    for t in (14.1347, 21.0220, 25.0109):
        out.append(f'<circle cx="{sx(0.5):.1f}" cy="{sy(t):.1f}" r="4" fill="#2f5d8a"/>')
        out.append(f'<text x="{sx(0.5)-8:.1f}" y="{sy(t)+4:.1f}" class="s" text-anchor="end">½+{t:.2f}i</text>')
    out.append(f'<text x="{sx(0.25):.1f}" y="{Y1+14}" class="s" text-anchor="middle">critical strip 0&lt;Re s&lt;1</text>')
    out.append(f'<text x="{sx(1.09):.1f}" y="{sy(26):.1f}" class="r" text-anchor="middle">OpenAI claims:</text>')
    out.append(f'<text x="{sx(1.09):.1f}" y="{sy(26)+14:.1f}" class="r" text-anchor="middle">no zeros at all</text>')
    out.append(f'<text x="{sx(0.84):.1f}" y="{sy(9):.1f}" class="s" text-anchor="end">grey: known zero-free →</text>')
    out.append(f'<text x="{sx(0.84):.1f}" y="{sy(9)+12:.1f}" class="s" text-anchor="end">(since 1899; narrows up)</text>')
    out.append(f'<text x="{X0-30}" y="{(Y0+Y1)/2:.1f}" class="s" text-anchor="end">Im s</text>')
    out.append(f'<text x="{X0-8}" y="{Y0}" class="s" text-anchor="end">0</text>')
    out.append(f'<text x="{X0-8}" y="{sy(30):.1f}" class="s" text-anchor="end">30</text>')
    return fig('\n'.join(out), '0 0 720 330',
               'Blue dots: the first three non-trivial zeros of ζ (all on Re=½; the Riemann hypothesis says every one is). Grey band: schematic de la Vallée Poussin-type zero-free region (its width shrinks to 0 as the height t grows; curve shape illustrative, constant 0.1). Red region Re s &gt; 7/8: the fixed-width zero-free region claimed by OpenAI family 003. Nobody had previously proven any fixed-width zero-free strip.')


# ------------------------------------------------------------------ Flint Hills staircase
def svg_flint():
    X0, X1, N = 70, 680, 400
    Y0, Y1, S = 260, 30, 32.0
    sx = lambda n: X0 + n / N * (X1 - X0)
    sy = lambda v: Y0 - v / S * (Y0 - Y1)
    s, prev, seq = 0.0, 0.0, [(sx(0), sy(0))]
    for n in range(1, N + 1):
        s += 1 / (n ** 3 * math.sin(n) ** 2)
        seq += [(sx(n), sy(prev)), (sx(n), sy(s))]
        prev = s
    out = [f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>',
           f'<polyline points="{pts(seq)}" class="lna"/>']
    for v in (0, 10, 20, 30):
        out.append(f'<text x="{X0-6}" y="{sy(v)+4:.1f}" class="s" text-anchor="end">{v}</text>')
    for n in (0, 100, 200, 300, 400):
        out.append(f'<text x="{sx(n):.1f}" y="{Y0+16}" class="s" text-anchor="middle">{n}</text>')
    out.append(f'<text x="{sx(30):.1f}" y="{sy(9.5):.1f}" class="s">n=3 jumps to 3.42 (3/1 ≈ π)</text>')
    out.append(f'<text x="{sx(30):.1f}" y="{sy(7.3):.1f}" class="s">n=22 jumps to 4.75 (22/7)</text>')
    out.append(f'<text x="{sx(355)-6:.1f}" y="{sy(29.41)+4:.1f}" class="r" text-anchor="end">n=355: one term adds 24.6 → 29.41 (355/113; next continued-fraction term is 292)</text>')
    out.append(f'<text x="{X0}" y="{Y1-10}" class="h">Partial sums of the Flint Hills series Σ 1/(n³ sin²n), n ≤ 400 (computed)</text>')
    return fig('\n'.join(out), '0 0 720 290',
               'Each jump happens when n is the numerator of an unusually good fraction approximating π (so sin n is tiny). Whether the series converges depends on how often and how large these jumps are, which is governed by the irrationality exponent of π. Values computed by the build script of this deck.')


# ------------------------------------------------------------------ omega timeline
OMEGA = [(1969, 2.807, 'Strassen'), (1978, 2.796, ''), (1979, 2.78, ''), (1981, 2.522, 'Schönhage'),
         (1986, 2.479, 'laser method'), (1990, 2.376, 'Coppersmith–Winograd'), (2014, 2.3728639, 'Le Gall'),
         (2021, 2.3728596, ''), (2023, 2.371866, ''), (2024, 2.371339, ''), (2026.6, 2.371177, '')]


def svg_omega():
    X0, X1, A, B = 70, 640, 1965, 2028
    Y0, Y1, L, H = 280, 40, 2.0, 3.0
    sx = lambda yr: X0 + (yr - A) / (B - A) * (X1 - X0)
    sy = lambda w: Y0 - (w - L) / (H - L) * (Y0 - Y1)
    out = [f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>']
    for w in (2.0, 2.25, 2.5, 2.75, 3.0):
        out.append(f'<line x1="{X0}" y1="{sy(w):.1f}" x2="{X1}" y2="{sy(w):.1f}" class="grid"/>')
        out.append(f'<text x="{X0-6}" y="{sy(w)+4:.1f}" class="s" text-anchor="end">{w:.2f}</text>')
    for yr in (1970, 1980, 1990, 2000, 2010, 2020):
        out.append(f'<text x="{sx(yr):.1f}" y="{Y0+16}" class="s" text-anchor="middle">{yr}</text>')
    step = [(sx(1965), sy(3.0))]
    for yr, w, _ in OMEGA:
        step += [(sx(yr), step[-1][1]), (sx(yr), sy(w))]
    step.append((sx(2026.6), sy(2.371177)))
    out.append(f'<polyline points="{pts(step)}" class="ln"/>')
    for yr, w, lab in OMEGA:
        out.append(f'<circle cx="{sx(yr):.1f}" cy="{sy(w):.1f}" r="3" fill="#1a1a18"/>')
        if lab:
            out.append(f'<text x="{sx(yr)+6:.1f}" y="{sy(w)-6:.1f}" class="s">{lab} {w:.3f}</text>')
    out.append(f'<line x1="{X0}" y1="{sy(2.3078):.1f}" x2="{X1}" y2="{sy(2.3078):.1f}" class="dash"/>')
    out.append(f'<text x="{sx(1968):.1f}" y="{sy(2.3078)+14:.1f}" class="s">known barrier for laser-method analyses ≈2.3078 (AFLG 2015)</text>')
    out.append(f'<circle cx="{sx(2026.8):.1f}" cy="{sy(2.25):.1f}" r="5" fill="#b03a2e"/>')
    out.append(f'<text x="{sx(2026.8)-10:.1f}" y="{sy(2.25)+20:.1f}" class="r" text-anchor="end">2026-10 OpenAI claims ω ≤ 9/4 = 2.25 (over ℂ, Lean-formalized)</text>')
    out.append(f'<text x="{sx(1966):.1f}" y="{sy(2.0)-6:.1f}" class="s">ω ≥ 2 (lower bound; mainstream conjecture ω = 2)</text>')
    out.append(f'<text x="{X0}" y="{Y1-14}" class="h">Upper bounds on the matrix multiplication exponent ω: 57 years</text>')
    return fig('\n'.join(out), '0 0 720 310',
               'Data: Strassen 1969; Pan/Bini/Schönhage 1978–81; Strassen 1986; Coppersmith–Winograd 1990; Le Gall 2014; Alman–Vassilevska Williams 2021; Duan–Wu–Zhou 2023; Alman et al. 2024 (<a href="https://arxiv.org/abs/2404.16349">arXiv:2404.16349</a>); Dupont et al. 2026-08 (<a href="https://arxiv.org/abs/2608.16884">arXiv:2608.16884</a>, using AlphaEvolve). From 2014 to 2026 the bound fell by about 0.0017 in total. The claimed 2.25 drops it by about 0.12 at once and lands below the known laser-method barrier, so it must use a different method: the paper uses the asymptotic-spectrum approach of Strassen.')


# ------------------------------------------------------------------ max-cut number line
def svg_maxcut():
    X0, X1 = 60, 660
    sx = lambda a: X0 + (a - 0.5) / 0.5 * (X1 - X0)
    y = 90
    out = [f'<text x="20" y="22" class="h">Max-Cut approximation ratio: what fraction of the optimum can polynomial time guarantee?</text>',
           f'<rect x="{sx(0.878):.1f}" y="{y-14}" width="{sx(16/17)-sx(0.878):.1f}" height="28" fill="#e4e0d8"/>',
           f'<line x1="{X0}" y1="{y}" x2="{X1}" y2="{y}" class="ax"/>']
    for a, lab, cls in [(0.5, '0.5 random split', 's'), (0.878, '0.878 GW 1995 (SDP)', 'g'), (16 / 17, '0.941 Håstad 2001: NP-hard', 'r'), (1.0, '1.0', 's')]:
        above = a in (0.878, 1.0)
        out.append(f'<line x1="{sx(a):.1f}" y1="{y-8}" x2="{sx(a):.1f}" y2="{y+8}" class="ln"/>')
        out.append(f'<text x="{sx(a):.1f}" y="{y-22 if above else y+26}" class="{cls}" text-anchor="middle">{lab}</text>')
    out.append(f'<text x="{(sx(0.878)+sx(16/17))/2:.1f}" y="{y+44}" class="s" text-anchor="middle">grey: true limit unknown 1995–2026</text>')
    out.append(f'<text x="{(sx(0.878)+sx(16/17))/2:.1f}" y="{y+58}" class="s" text-anchor="middle">UGC true ⇒ the limit is exactly 0.878 (KKMO 2007)</text>')
    y2 = 190
    out.append(f'<text x="20" y="{y2-12}" class="h">Unique Games completeness ladder: which instances are provably NP-hard?</text>')
    boxes = [(30, '≈1/2 completeness', '2-to-2 theorem, 2018', 'box'), (250, '1−ε completeness = UGC', 'OpenAI 2026-09 claim + Lean', 'boxr')]
    for x, a, b, cls in boxes:
        out.append(f'<rect x="{x}" y="{y2}" width="200" height="46" rx="4" class="{cls}"/>')
        out.append(f'<text x="{x+12}" y="{y2+19}" class="t">{a}</text>')
        out.append(f'<text x="{x+12}" y="{y2+36}" class="s">{b}</text>')
    out.append(f'<line x1="232" y1="{y2+23}" x2="246" y2="{y2+23}" class="arr"/>')
    out.append(f'<text x="470" y="{y2+19}" class="s">Fully satisfiable instances</text>')
    out.append(f'<text x="470" y="{y2+34}" class="s">are easy (propagate along</text>')
    out.append(f'<text x="470" y="{y2+49}" class="s">edges): only "almost" is hard</text>')
    return fig('\n'.join(out), '0 0 720 260',
               'Sources: Goemans–Williamson, JACM 1995; Håstad, JACM 2001; Khot, STOC 2002; Khot–Kindler–Mossel–O\'Donnell, SICOMP 2007; Khot–Minzer–Safra, FOCS 2018.')


# ------------------------------------------------------------------ Moser spindle
def svg_moser():
    a = 2 * math.asin(1 / (2 * math.sqrt(3)))

    def rh(th):
        T = (math.sqrt(3) * math.cos(th), math.sqrt(3) * math.sin(th))
        B = (math.cos(th - math.pi / 6), math.sin(th - math.pi / 6))
        C = (math.cos(th + math.pi / 6), math.sin(th + math.pi / 6))
        return B, C, T
    B1, C1, T1 = rh(-a / 2)
    B2, C2, T2 = rh(a / 2)
    O = (0.0, 0.0)
    sc, ox, oy = 140, 70, 170
    P = lambda p: (ox + p[0] * sc, oy - p[1] * sc)
    edges = [(O, B1), (O, C1), (B1, C1), (B1, T1), (C1, T1), (O, B2), (O, C2), (B2, C2), (B2, T2), (C2, T2)]
    out = ['<text x="20" y="22" class="h">Moser spindle (1961): 7 points, 11 unit-length edges ⇒ 3 colors are not enough</text>']
    for p, q in edges:
        (x1, y1), (x2, y2) = P(p), P(q)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="ln"/>')
    (x1, y1), (x2, y2) = P(T1), P(T2)
    out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="lnr"/>')
    for p, col, lab in [(O, '#b03a2e', 'O'), (T1, '#b03a2e', 'T₁'), (T2, '#b03a2e', 'T₂'),
                        (B1, '#2f5d8a', 'B₁'), (C1, '#2e7d4f', 'C₁'), (B2, '#2e7d4f', 'B₂'), (C2, '#2f5d8a', 'C₂')]:
        x, y = P(p)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{col}"/>')
        out.append(f'<text x="{x+9:.1f}" y="{y-8:.1f}" class="t">{lab}</text>')
    out.append(f'<text x="{P(T1)[0]+14:.1f}" y="{(P(T1)[1]+P(T2)[1])/2+4:.1f}" class="r">|T₁T₂|=1</text>')
    tx = 430
    out.append(f'<text x="{tx}" y="60" class="t">Argument (with 3 colors)</text>')
    for i, line in enumerate(['O, B₁, C₁ pairwise at distance 1 → one color each',
                              'T₁ is 1 from B₁, C₁ → T₁ = color of O',
                              'likewise T₂ = color of O',
                              'but |T₁T₂| = 1 → contradiction ⇒ χ ≥ 4']):
        out.append(f'<text x="{tx}" y="{82+i*18}" class="z">{line}</text>')
    out.append(f'<text x="{tx}" y="182" class="t">Known bounds on χ of the plane</text>')
    for i, (yr, txt, cls) in enumerate([('1950s', '4 ≤ χ ≤ 7 (spindle, hexagons)', 's'),
                                        ('2018', '5 ≤ χ ≤ 7 (de Grey graph)', 's'),
                                        ('2026-09', '6 ≤ χ ≤ 7 (OpenAI, Lean)', 'r')]):
        out.append(f'<text x="{tx}" y="{204+i*18}" class="{cls}">{yr}  {txt}</text>')
    return fig('\n'.join(out), '0 0 720 290',
               'Coordinates computed by the build script: two rhombi, each made of two unit equilateral triangles, share the vertex O, and each tip T is √3 from O. Rotating one rhombus about O by 2·arcsin(1/(2√3)) ≈ 33.6° puts the two tips exactly 1 apart.')


# ------------------------------------------------------------------ Thompson x0
def svg_thompson():
    X0, Y0, S = 60, 270, 220
    P = lambda x, y: (X0 + x * S, Y0 - y * S)
    out = ['<text x="20" y="22" class="h">Left: the generator x₀ of the Thompson group F · Right: can you average fairly?</text>',
           f'<rect x="{X0}" y="{Y0-S}" width="{S}" height="{S}" fill="none" class="ax"/>']
    out.append(f'<line x1="{P(0,0)[0]}" y1="{P(0,0)[1]}" x2="{P(1,1)[0]}" y2="{P(1,1)[1]}" class="dash"/>')
    chain = [P(0, 0), P(0.5, 0.25), P(0.75, 0.5), P(1, 1)]
    out.append(f'<polyline points="{pts(chain)}" class="lna"/>')
    for (x, y) in chain:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#9a5b12"/>')
    for (xm, ym, lab) in [(0.25, 0.125, 'slope ½'), (0.625, 0.375, 'slope 1'), (0.875, 0.75, 'slope 2')]:
        x, y = P(xm, ym)
        out.append(f'<text x="{x+6:.1f}" y="{y+14:.1f}" class="s">{lab}</text>')
    for v, lab in [(0.5, '½'), (0.75, '¾'), (1, '1')]:
        out.append(f'<text x="{P(v,0)[0]:.1f}" y="{Y0+14}" class="s" text-anchor="middle">{lab}</text>')
    for v, lab in [(0.25, '¼'), (0.5, '½'), (1, '1')]:
        out.append(f'<text x="{X0-6}" y="{P(0,v)[1]+4:.1f}" class="s" text-anchor="end">{lab}</text>')
    rx = 340
    out.append(f'<text x="{rx}" y="60" class="t">ℤ: amenable</text>')
    out.append(f'<line x1="{rx}" y1="80" x2="{rx+260}" y2="80" class="ax"/>')
    out.append(f'<line x1="{rx+60}" y1="80" x2="{rx+200}" y2="80" class="lnb"/>')
    for x in (rx + 60, rx + 200):
        out.append(f'<circle cx="{x}" cy="80" r="4" fill="#b03a2e"/>')
    out.append(f'<text x="{rx}" y="102" class="s">A = {{−n…n}}: shift by 1 changes 2, 2/(2n+1) → 0</text>')
    out.append(f'<text x="{rx}" y="140" class="t">Free group F₂: non-amenable</text>')
    cx, cy = rx + 130, 205
    out.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="#1a1a18"/>')
    for k in range(4):
        ang = k * math.pi / 2
        x1, y1 = cx + 34 * math.cos(ang), cy + 34 * math.sin(ang)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x1:.1f}" y2="{y1:.1f}" class="ln"/>')
        for d in (-0.5, 0, 0.5):
            x2, y2 = x1 + 20 * math.cos(ang + d), y1 + 20 * math.sin(ang + d)
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="ln"/>')
            out.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="3" fill="#b03a2e"/>')
    out.append(f'<text x="{rx}" y="268" class="s">radius-n ball: ~3ⁿ points, ~2/3 on the boundary</text>')
    return fig('\n'.join(out), '0 0 720 290',
               'x₀ squeezes [0,½] onto [0,¼], shifts [½,¾] onto [¼,½] and stretches [¾,1] onto [½,1]; F is generated by x₀ and x₁. F contains no free subgroup F₂ (Brin–Squier 1985), so the standard key "contains F₂ ⇒ non-amenable" does not apply. That is one reason the problem stayed open for 47 years.')


# ------------------------------------------------------------------ blow-up curves + Clay table
def svg_blowup():
    X0, X1, T = 70, 420, 1.2
    Y0, Y1, V = 270, 40, 20.0
    sx = lambda t: X0 + t / T * (X1 - X0)
    sy = lambda v: Y0 - min(v, V) / V * (Y0 - Y1)
    ts = [i / 200 * T for i in range(201)]
    e = [(sx(t), sy(math.exp(t))) for t in ts]
    inv = [(sx(t), sy(1 / (1 - t))) for t in ts if t < 1 - 1 / V]
    blow = [(sx(t), sy(1 / (1 - 0.5 * math.exp(t)))) for t in ts if 1 - 0.5 * math.exp(t) > 1 / V]
    dec = [(sx(t), sy(1 / (1 + math.exp(t)))) for t in ts]
    out = [f'<text x="20" y="22" class="h">Finite-time blowup by hand: a smooth equation whose solution reaches infinity in finite time</text>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>',
           f'<line x1="{sx(1):.1f}" y1="{Y0}" x2="{sx(1):.1f}" y2="{Y1}" class="dash"/>',
           f'<line x1="{sx(math.log(2)):.1f}" y1="{Y0}" x2="{sx(math.log(2)):.1f}" y2="{Y1}" class="dash"/>',
           f'<polyline points="{pts(e)}" class="lng"/>',
           f'<polyline points="{pts(inv)}" class="lnr"/>',
           f'<polyline points="{pts(blow)}" class="lna"/>',
           f'<polyline points="{pts(dec)}" class="lnb"/>']
    for t in (0, 0.5, 1.0):
        out.append(f'<text x="{sx(t):.1f}" y="{Y0+16}" class="s" text-anchor="middle">t={t:g}</text>')
    out.append(f'<text x="{sx(math.log(2)):.1f}" y="{Y0+30}" class="s" text-anchor="middle">ln2≈0.693</text>')
    for v in (0, 10, 20):
        out.append(f'<text x="{X0-6}" y="{sy(v)+4:.1f}" class="s" text-anchor="end">{v}</text>')
    lx = 440
    for i, (cls, txt) in enumerate([('lng', 'ẋ = x: eᵗ, grows but never blows up'), ('lnr', 'ẋ = x²: 1/(1−t), blows up at t=1'),
                                    ('lna', 'ẋ = x²−x, x₀=2: blows up at t=ln2'), ('lnb', 'ẋ = x²−x, x₀=½: decays to 0')]):
        y = 50 + i * 20
        out.append(f'<line x1="{lx}" y1="{y}" x2="{lx+24}" y2="{y}" class="{cls}"/>')
        out.append(f'<text x="{lx+30}" y="{y+4}" class="s">{txt}</text>')
    out.append(f'<text x="{lx}" y="148" class="t">Clay alternatives (any one wins)</text>')
    for i, (lab, txt, cls) in enumerate([('A', 'ℝ³, no force: smooth forever', 'box'), ('B', '𝕋³, no force: smooth forever', 'box'),
                                         ('C', 'ℝ³, chosen smooth force: blowup', 'boxr'), ('D', '𝕋³, chosen smooth force: blowup', 'boxr')]):
        y = 158 + i * 26
        out.append(f'<rect x="{lx}" y="{y}" width="260" height="22" rx="3" class="{cls}"/>')
        out.append(f'<text x="{lx+8}" y="{y+15}" class="s">({lab}) {txt}</text>')
    out.append(f'<text x="{lx}" y="275" class="r">OpenAI 9/8: (C)/(D); (A)/(B) open</text>')
    return fig('\n'.join(out), '0 0 720 300',
               'Left: the x² term plays the role of the nonlinear self-transport in Navier–Stokes, the −x term the role of viscous damping. With small initial data damping wins (blue); with large data the nonlinearity wins (orange). This mirrors what is known for 3D NS: global smooth solutions for small data, unknown for large data. Curves computed from the exact solutions by the build script. Right: the four alternatives in the official Clay problem statement (Fefferman).')


# ------------------------------------------------------------------ harmonic staircase (Vlasov-Maxwell)
def svg_harmonic():
    X0, X1, K = 70, 460, 60
    Y0, Y1, V = 230, 40, 5.0
    sx = lambda k: X0 + k / K * (X1 - X0)
    sy = lambda v: Y0 - v / V * (Y0 - Y1)
    s, seq = 0.0, [(sx(0), sy(0))]
    for k in range(1, K + 1):
        seq.append((sx(k - 1) if k > 1 else sx(0), sy(s)))
        s += 1 / k
        seq += [(sx(k - 1), sy(s)), (sx(k), sy(s))]
    out = [f'<text x="20" y="22" class="h">Vlasov–Maxwell endgame: each momentum doubling takes ≳1/k time, and Σ1/k diverges</text>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>',
           f'<polyline points="{pts(seq)}" class="lna"/>']
    for v in (0, 1, 2, 3, 4, 5):
        out.append(f'<text x="{X0-6}" y="{sy(v)+4:.1f}" class="s" text-anchor="end">{v}</text>')
    for k in (0, 20, 40, 60):
        out.append(f'<text x="{sx(k):.1f}" y="{Y0+16}" class="s" text-anchor="middle">k={k}</text>')
    out.append(f'<text x="{sx(60):.1f}" y="{sy(s)-8:.1f}" class="s" text-anchor="end">first 60 terms ≈ {s:.2f}; grows without bound</text>')
    tx = 480
    for i, line in enumerate(['k = number of momentum doublings so far', 'doubling k (P≈2ᵏ) takes ≳ 1/(k·log2)',
                              'total time ≈ harmonic series → ∞', '⇒ finitely many doublings in finite time',
                              '⇒ momentum stays bounded, so by', '   Glassey–Strauss 1986: no blowup']):
        out.append(f'<text x="{tx}" y="{70+i*20}" class="z">{line}</text>')
    return fig('\n'.join(out), '0 0 720 260',
               'A hand-computable version of the argument skeleton in the reasoning summary of the OpenAI paper (family 362). The real difficulty is proving that each doubling takes at least ~1/log P time (signed momentum-increment estimates plus counting direction changes). Staircase computed by the build script.')


# ------------------------------------------------------------------ spin glass
def svg_spin():
    out = ['<text x="20" y="22" class="h">Left: the smallest frustrated system · Right: the hierarchical (ultrametric) structure of Parisi</text>']
    A, B, C = (150, 60), (80, 180), (220, 180)
    out.append(f'<line x1="{A[0]}" y1="{A[1]}" x2="{B[0]}" y2="{B[1]}" class="lnr"/>')
    out.append(f'<line x1="{A[0]}" y1="{A[1]}" x2="{C[0]}" y2="{C[1]}" class="lnr"/>')
    out.append(f'<line x1="{B[0]}" y1="{B[1]}" x2="{C[0]}" y2="{C[1]}" class="lnr" stroke-dasharray="5 4"/>')
    for (x, y), lab in [(A, '↑'), (B, '↓'), (C, '↓')]:
        out.append(f'<circle cx="{x}" cy="{y}" r="14" fill="#f3f0ea" stroke="#1a1a18"/>')
        out.append(f'<text x="{x}" y="{y+5}" class="t" text-anchor="middle">{lab}</text>')
    out.append('<text x="40" y="215" class="s">all three bonds "want" opposite spins</text>')
    out.append('<text x="40" y="231" class="s">none of the 8 configurations satisfies all three</text>')
    out.append('<text x="40" y="247" class="s">(dashed bond always fails): 6-fold degenerate</text>')
    out.append('<text x="40" y="263" class="s">Z(β) = 2e^(−3β) + 6e^β</text>')
    root = (520, 50)
    lvl1 = [(440, 120), (600, 120)]
    out.append(f'<circle cx="{root[0]}" cy="{root[1]}" r="4" fill="#1a1a18"/>')
    for p in lvl1:
        out.append(f'<line x1="{root[0]}" y1="{root[1]}" x2="{p[0]}" y2="{p[1]}" class="ln"/>')
        out.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="4" fill="#1a1a18"/>')
        for dx in (-45, -15, 15, 45):
            q = (p[0] + dx, 200)
            out.append(f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" class="ln"/>')
            out.append(f'<circle cx="{q[0]}" cy="{q[1]}" r="4" fill="#2f5d8a"/>')
    out.append('<text x="660" y="54" class="s">m₀</text><text x="660" y="124" class="s">m₁</text><text x="660" y="204" class="s">states</text>')
    out.append('<text x="395" y="232" class="s">closer relatives ⇒ larger overlap</text>')
    out.append('<text x="395" y="248" class="s">diluted: need all multi-replica overlaps</text>')
    return fig('\n'.join(out), '0 0 720 275',
               'Spin glass = random ± couplings + frustration everywhere + exponentially many metastable states. The energy function of a Hopfield network (1982) is exactly such a Hamiltonian; perceptron capacity (Gardner 1988) was computed with the same replica method.')


# ------------------------------------------------------------------ Hodge withdrawal dependency graph
def svg_hodge():
    out = ['<text x="20" y="22" class="h">Oct 7 withdrawals: one sign error propagates through the dependency graph</text>']
    nodes = [(30, 50, 'Weil classes on abelian eightfolds', 'sign error: −1 written as +1', 'boxr'),
             (30, 140, 'Kuga–Satake for K3 surfaces', 'depends on the above → withdrawn', 'boxr'),
             (30, 210, 'Rational Hodge for products of K3s', 'depends on the above → withdrawn', 'boxr'),
             (420, 90, 'Rational Hodge, CM abelian varieties', 'not on this chain; not withdrawn; no Lean', 'boxg')]
    for x, y, a, b, cls in nodes:
        out.append(f'<rect x="{x}" y="{y}" width="{300 if x < 400 else 280}" height="46" rx="4" class="{cls}"/>')
        out.append(f'<text x="{x+10}" y="{y+19}" class="t">{a}</text>')
        out.append(f'<text x="{x+10}" y="{y+36}" class="s">{b}</text>')
    out.append('<line x1="180" y1="96" x2="180" y2="136" class="arrr"/>')
    out.append('<line x1="180" y1="186" x2="180" y2="206" class="arrr"/>')
    out.append('<line x1="345" y1="40" x2="345" y2="260" class="dash"/>')
    out.append('<text x="420" y="170" class="s">Family 032 first titled "Hodge and</text>')
    out.append('<text x="420" y="186" class="s">Kuga–Satake … all K3 surfaces"</text>')
    out.append('<text x="420" y="202" class="s">→ retitled to the CM-only version afterwards</text>')
    out.append('<text x="420" y="226" class="r">722 → 719; 14 repaired, 13 re-cited</text>')
    return fig('\n'.join(out), '0 0 720 270',
               'Sources: <a href="https://github.com/openai/math/blob/main/history.md">openai/math history.md</a> (2026-10-07); the family title is compared against CONTENTS.md at the initial commit <code>adc7f12</code>. The withdrawal notice reads: "This withdrawal concerns the proof; it does not assert that the mathematical statement is false."')
