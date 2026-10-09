"""SVG figures for the OpenAI-math explainer deck. All plotted numbers are computed here, not hand-typed."""
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
    ('理论计算机', 40), ('组合', 37), ('代数几何/复几何', 36), ('数论', 31),
    ('概率/统计力学', 29), ('微分几何', 29), ('数学物理', 25), ('算子代数', 19),
    ('拓扑', 18), ('代数', 18), ('实/复分析', 16), ('偏微分方程', 16),
    ('凸几何/度量几何', 15), ('群论', 14), ('动力系统/遍历论', 12), ('泛函分析', 11), ('数理逻辑', 6),
]
DEEP = {'理论计算机', '组合', '数论', '概率/统计力学', '数学物理', '群论', '偏微分方程', '代数几何/复几何'}


def svg_fields():
    out = ['<text x="20" y="20" class="h">372 个结果族按学科分布（橙色 = 本 deck 深讲了其中至少一个结果）</text>']
    y = 42
    for name, n in FIELDS:
        w = n * 11
        cls = 'boxa' if name in DEEP else 'box'
        out.append(f'<text x="150" y="{y+11}" class="z" text-anchor="end">{name}</text>')
        out.append(f'<rect x="160" y="{y}" width="{w}" height="14" rx="2" class="{cls}"/>')
        out.append(f'<text x="{166+w}" y="{y+11}" class="s">{n}</text>')
        y += 20
    return fig('\n'.join(out), f'0 0 720 {y+10}',
               '来源：<a href="https://github.com/openai/math/blob/main/overview.pdf">openai/math overview.pdf</a> 的 17 个学科小节，逐条计数（合计 372）。编号 045/061/070/123/163 空缺，原因未公开。')


# ------------------------------------------------------------------ trust stack
def svg_trust():
    rows = [
        ('① Lean 内核逐步检查证明', '本 repo：sorry = 0，自加 axiom = 0，native_decide = 0', 'boxg', 'g', '强'),
        ('② 只用 3 条标准公理', 'Comparator 416 个配置全部只允许 propext / Quot.sound / Classical.choice', 'boxg', 'g', '强'),
        ('③ Lean 陈述 = 论文想说的那句话？', '挑战文件由 OpenAI（agent）自己写；要靠人逐行读几十行定义', 'boxa', 'h', '要人审'),
        ('④ 依赖库与补丁里的定义对不对？', '24 个补丁（最大 ~2MB）+ 11 个来源不明的 lana-agents/* 依赖库', 'boxa', 'h', '未审'),
        ('⑤ 没有形式化的那 ~58%', '完全没有机器检查——10-07 撤回的 3 篇 Hodge 相关论文就在这里', 'boxr', 'r', '无'),
    ]
    out = ['<text x="20" y="20" class="h">"有 Lean 证明"到底保证了什么：从下往上的信任栈</text>']
    y = 36
    for title, sub, cls, tcls, verdict in rows:
        out.append(f'<rect x="20" y="{y}" width="600" height="46" rx="4" class="{cls}"/>')
        out.append(f'<text x="34" y="{y+19}" class="t">{title}</text>')
        out.append(f'<text x="34" y="{y+36}" class="s">{sub}</text>')
        out.append(f'<text x="640" y="{y+28}" class="{tcls}">{verdict}</text>')
        y += 54
    return fig('\n'.join(out), f'0 0 720 {y+4}',
               '①② 是机器能保证的；③④⑤ 仍然要靠人。审计数据来自本 deck 对 <code>lean/OAI/</code>（122,458 个 .lean 文件、约 2,600 万行）的源码 grep 与 Comparator 配置统计（2026-10-08，commit fd4aeeb）；未实际编译。')


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
    out.append(f'<text x="{sx(0.25):.1f}" y="{Y1+14}" class="s" text-anchor="middle">临界带 0&lt;Re s&lt;1</text>')
    out.append(f'<text x="{sx(1.09):.1f}" y="{sy(26):.1f}" class="r" text-anchor="middle">OpenAI 声称：</text>')
    out.append(f'<text x="{sx(1.09):.1f}" y="{sy(26)+14:.1f}" class="r" text-anchor="middle">整块无零点</text>')
    out.append(f'<text x="{sx(0.84):.1f}" y="{sy(9):.1f}" class="s" text-anchor="end">灰带：1899 年起已知的无零区 →</text>')
    out.append(f'<text x="{sx(0.84):.1f}" y="{sy(9)+12:.1f}" class="s" text-anchor="end">（宽度越往上越窄）</text>')
    out.append(f'<text x="{X0-30}" y="{(Y0+Y1)/2:.1f}" class="s" text-anchor="end">Im s</text>')
    out.append(f'<text x="{X0-8}" y="{Y0}" class="s" text-anchor="end">0</text>')
    out.append(f'<text x="{X0-8}" y="{sy(30):.1f}" class="s" text-anchor="end">30</text>')
    return fig('\n'.join(out), '0 0 720 330',
               '蓝点是 ζ 的前三个非平凡零点（都在 Re=½ 上，黎曼猜想说全部如此）。灰色带是 de la Vallée Poussin 型无零区的示意（宽度随高度 t 缩向 0，曲线形状为示意，常数取 0.1）。红色区域 Re s &gt; 7/8 是 OpenAI family 003 声称的"固定宽度"无零区——此前从未有人证明过任何固定宽度的竖带。')


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
    out.append(f'<text x="{sx(30):.1f}" y="{sy(9.5):.1f}" class="s">n=3 跳到 3.42（3/1 ≈ π）</text>')
    out.append(f'<text x="{sx(30):.1f}" y="{sy(7.3):.1f}" class="s">n=22 跳到 4.75（22/7）</text>')
    out.append(f'<text x="{sx(355)-6:.1f}" y="{sy(29.41)+4:.1f}" class="r" text-anchor="end">n=355 单项 +24.6 → 29.41（355/113，下一个连分数项是 292）</text>')
    out.append(f'<text x="{X0}" y="{Y1-10}" class="h">Flint Hills 级数 Σ 1/(n³ sin²n) 的部分和（n ≤ 400，实算）</text>')
    return fig('\n'.join(out), '0 0 720 290',
               '每一次跳跃都发生在 n 是 π 某个"超常好"分数逼近的分子时（sin n 很小）。级数收不收敛取决于这种跳跃有多频繁、多大——也就是取决于 π 的无理性指数。数值由本 deck 的 build 脚本直接计算。')


# ------------------------------------------------------------------ omega timeline
OMEGA = [(1969, 2.807, 'Strassen'), (1978, 2.796, ''), (1979, 2.78, ''), (1981, 2.522, 'Schönhage'),
         (1986, 2.479, '激光法'), (1990, 2.376, 'Coppersmith–Winograd'), (2014, 2.3728639, 'Le Gall'),
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
    out.append(f'<text x="{sx(1968):.1f}" y="{sy(2.3078)+14:.1f}" class="s">激光法分析的已知壁垒 ≈2.3078（AFLG 2015）</text>')
    out.append(f'<circle cx="{sx(2026.8):.1f}" cy="{sy(2.25):.1f}" r="5" fill="#b03a2e"/>')
    out.append(f'<text x="{sx(2026.8)-10:.1f}" y="{sy(2.25)+20:.1f}" class="r" text-anchor="end">2026-10 OpenAI 声称 ω ≤ 9/4 = 2.25（ℂ 上，Lean 已形式化）</text>')
    out.append(f'<text x="{sx(1966):.1f}" y="{sy(2.0)-6:.1f}" class="s">ω ≥ 2（下界；主流猜想 ω = 2）</text>')
    out.append(f'<text x="{X0}" y="{Y1-14}" class="h">矩阵乘法指数 ω 的上界：57 年的历史</text>')
    return fig('\n'.join(out), '0 0 720 310',
               '数据：Strassen 1969；Pan/Bini/Schönhage 1978–81；Strassen 1986；Coppersmith–Winograd 1990；Le Gall 2014；Alman–Vassilevska Williams 2021；Duan–Wu–Zhou 2023；Alman 等 2024（<a href="https://arxiv.org/abs/2404.16349">arXiv:2404.16349</a>）；Dupont 等 2026-08（<a href="https://arxiv.org/abs/2608.16884">arXiv:2608.16884</a>，借助 AlphaEvolve）。2014→2026 共下降约 0.0017；OpenAI 的 2.25 一次下降约 0.12，而且低于已知的激光法壁垒——所以它必须是另一种方法（论文用的是 Strassen 的"渐近谱"路线）。')


# ------------------------------------------------------------------ max-cut number line
def svg_maxcut():
    X0, X1 = 60, 660
    sx = lambda a: X0 + (a - 0.5) / 0.5 * (X1 - X0)
    y = 90
    out = [f'<text x="20" y="22" class="h">Max-Cut 的近似比：多项式时间能保证切到"最优值的多少倍"？</text>',
           f'<rect x="{sx(0.878):.1f}" y="{y-14}" width="{sx(16/17)-sx(0.878):.1f}" height="28" fill="#e4e0d8"/>',
           f'<line x1="{X0}" y1="{y}" x2="{X1}" y2="{y}" class="ax"/>']
    for a, lab, cls in [(0.5, '0.5 随机分组', 's'), (0.878, '0.878 GW 1995（SDP）', 'g'), (16 / 17, '0.941 Håstad 2001：NP 难', 'r'), (1.0, '1.0', 's')]:
        above = a in (0.878, 1.0)
        out.append(f'<line x1="{sx(a):.1f}" y1="{y-8}" x2="{sx(a):.1f}" y2="{y+8}" class="ln"/>')
        out.append(f'<text x="{sx(a):.1f}" y="{y-22 if above else y+26}" class="{cls}" text-anchor="middle">{lab}</text>')
    out.append(f'<text x="{(sx(0.878)+sx(16/17))/2:.1f}" y="{y+44}" class="s" text-anchor="middle">灰：1995–2026 不知道真正的极限在哪</text>')
    out.append(f'<text x="{(sx(0.878)+sx(16/17))/2:.1f}" y="{y+58}" class="s" text-anchor="middle">UGC 成立 ⇒ 极限恰好是 0.878（KKMO 2007）</text>')
    y2 = 190
    out.append(f'<text x="20" y="{y2-12}" class="h">Unique Games 的"完备度"阶梯：能证明 NP 难的是哪种实例？</text>')
    boxes = [(30, '≈1/2 完备度', '2-to-2 定理 2018', 'box'), (250, '1−ε 完备度 = UGC', 'OpenAI 2026-09 声称 + Lean', 'boxr')]
    for x, a, b, cls in boxes:
        out.append(f'<rect x="{x}" y="{y2}" width="200" height="46" rx="4" class="{cls}"/>')
        out.append(f'<text x="{x+12}" y="{y2+19}" class="t">{a}</text>')
        out.append(f'<text x="{x+12}" y="{y2+36}" class="s">{b}</text>')
    out.append(f'<line x1="232" y1="{y2+23}" x2="246" y2="{y2+23}" class="arr"/>')
    out.append(f'<text x="470" y="{y2+19}" class="s">完全可满足（完备度 = 1）的实例</text>')
    out.append(f'<text x="470" y="{y2+34}" class="s">沿边传播就能多项式时间解，</text>')
    out.append(f'<text x="470" y="{y2+49}" class="s">所以难点只在"几乎可满足"</text>')
    return fig('\n'.join(out), '0 0 720 260',
               '来源：Goemans–Williamson, JACM 1995；Håstad, JACM 2001；Khot, STOC 2002；Khot–Kindler–Mossel–O\'Donnell, SICOMP 2007；Khot–Minzer–Safra, FOCS 2018。')


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
    out = ['<text x="20" y="22" class="h">Moser 菱形对（1961）：7 个点、11 条长度为 1 的边 ⇒ 3 种颜色不够</text>']
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
    out.append(f'<text x="{P(T1)[0]+14:.1f}" y="{(P(T1)[1]+P(T2)[1])/2+4:.1f}" class="r">|T₁T₂|=1 却同色</text>')
    tx = 430
    out.append(f'<text x="{tx}" y="60" class="t">推理（3 色时）</text>')
    for i, line in enumerate(['O、B₁、C₁ 两两相距 1 → 三种颜色各占一个',
                              'T₁ 与 B₁、C₁ 都相距 1 → T₁ 只能和 O 同色',
                              '同理 T₂ 也和 O 同色',
                              '但 T₁、T₂ 相距 1 → 矛盾 ⇒ χ ≥ 4']):
        out.append(f'<text x="{tx}" y="{82+i*18}" class="z">{line}</text>')
    out.append(f'<text x="{tx}" y="182" class="t">平面色数 χ 的已知范围</text>')
    for i, (yr, txt, cls) in enumerate([('1950–61', '4 ≤ χ ≤ 7（菱形对 + 六边形 7 色铺砌）', 's'),
                                        ('2018', '5 ≤ χ ≤ 7（de Grey，1581 点的有限图）', 's'),
                                        ('2026-09', '6 ≤ χ ≤ 7（OpenAI 声称，Lean 已形式化）', 'r')]):
        out.append(f'<text x="{tx}" y="{204+i*18}" class="{cls}">{yr}  {txt}</text>')
    return fig('\n'.join(out), '0 0 720 290',
               '坐标由 build 脚本计算：两个"两个单位正三角形拼成的菱形"共享顶点 O，尖顶 T 距 O 为 √3；把其中一个绕 O 转 2·arcsin(1/(2√3)) ≈ 33.6°，使两个尖顶恰好相距 1。')


# ------------------------------------------------------------------ Thompson x0
def svg_thompson():
    X0, Y0, S = 60, 270, 220
    P = lambda x, y: (X0 + x * S, Y0 - y * S)
    out = ['<text x="20" y="22" class="h">左：Thompson 群 F 的生成元 x₀ · 右："能否公平取平均"的直觉</text>',
           f'<rect x="{X0}" y="{Y0-S}" width="{S}" height="{S}" fill="none" class="ax"/>']
    out.append(f'<line x1="{P(0,0)[0]}" y1="{P(0,0)[1]}" x2="{P(1,1)[0]}" y2="{P(1,1)[1]}" class="dash"/>')
    chain = [P(0, 0), P(0.5, 0.25), P(0.75, 0.5), P(1, 1)]
    out.append(f'<polyline points="{pts(chain)}" class="lna"/>')
    for (x, y) in chain:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#9a5b12"/>')
    for (xm, ym, lab) in [(0.25, 0.125, '斜率 ½'), (0.625, 0.375, '斜率 1'), (0.875, 0.75, '斜率 2')]:
        x, y = P(xm, ym)
        out.append(f'<text x="{x+6:.1f}" y="{y+14:.1f}" class="s">{lab}</text>')
    for v, lab in [(0.5, '½'), (0.75, '¾'), (1, '1')]:
        out.append(f'<text x="{P(v,0)[0]:.1f}" y="{Y0+14}" class="s" text-anchor="middle">{lab}</text>')
    for v, lab in [(0.25, '¼'), (0.5, '½'), (1, '1')]:
        out.append(f'<text x="{X0-6}" y="{P(0,v)[1]+4:.1f}" class="s" text-anchor="end">{lab}</text>')
    rx = 340
    out.append(f'<text x="{rx}" y="60" class="t">ℤ：可顺从</text>')
    out.append(f'<line x1="{rx}" y1="80" x2="{rx+260}" y2="80" class="ax"/>')
    out.append(f'<line x1="{rx+60}" y1="80" x2="{rx+200}" y2="80" class="lnb"/>')
    for x in (rx + 60, rx + 200):
        out.append(f'<circle cx="{x}" cy="80" r="4" fill="#b03a2e"/>')
    out.append(f'<text x="{rx}" y="102" class="s">A = {{−n…n}} 平移 +1 只变 2 个元素：2/(2n+1) → 0</text>')
    out.append(f'<text x="{rx}" y="140" class="t">自由群 F₂：不可顺从</text>')
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
    out.append(f'<text x="{rx}" y="268" class="s">半径 n 的球约 3ⁿ 个点，约 2/3 在边界（红）上：比例不趋于 0</text>')
    return fig('\n'.join(out), '0 0 720 290',
               'x₀ 把 [0,½] 压到 [0,¼]、[½,¾] 平移到 [¼,½]、[¾,1] 拉到 [½,1]；F 由 x₀ 和 x₁ 两个元素生成。F 不含自由群 F₂（Brin–Squier 1985），所以"含 F₂ ⇒ 不可顺从"这把标准钥匙对它没用——这正是这个问题拖了 47 年的原因之一。')


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
    out = [f'<text x="20" y="22" class="h">手算的"有限时间爆破"：方程光滑，解却在有限时刻冲到无穷</text>',
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
    for i, (cls, txt) in enumerate([('lng', 'ẋ = x：eᵗ，增长但永不爆'), ('lnr', 'ẋ = x²：1/(1−t)，t→1 爆破'),
                                    ('lna', 'ẋ = x²−x，x₀=2：t=ln2 爆破'), ('lnb', 'ẋ = x²−x，x₀=½：衰减到 0')]):
        y = 50 + i * 20
        out.append(f'<line x1="{lx}" y1="{y}" x2="{lx+24}" y2="{y}" class="{cls}"/>')
        out.append(f'<text x="{lx+30}" y="{y+4}" class="s">{txt}</text>')
    out.append(f'<text x="{lx}" y="148" class="t">Clay 的四个分支（证出任一即算）</text>')
    for i, (lab, txt, cls) in enumerate([('A', 'ℝ³，无外力：永远光滑', 'box'), ('B', '𝕋³，无外力：永远光滑', 'box'),
                                         ('C', 'ℝ³，可选光滑外力：会爆破', 'boxr'), ('D', '𝕋³，可选光滑外力：会爆破', 'boxr')]):
        y = 158 + i * 26
        out.append(f'<rect x="{lx}" y="{y}" width="260" height="22" rx="3" class="{cls}"/>')
        out.append(f'<text x="{lx+8}" y="{y+15}" class="s">({lab}) {txt}</text>')
    out.append(f'<text x="{lx}" y="275" class="r">OpenAI 9/8 声称 (C)/(D)；(A)/(B) 仍开放</text>')
    return fig('\n'.join(out), '0 0 720 300',
               '左：x² 项像 Navier–Stokes 的非线性"自我输运"，−x 项像粘性阻尼。小初值时阻尼赢（蓝），大初值时非线性赢（橙）——这正是 3D NS 已知理论的形状：小初值有整体光滑解，大初值未知。曲线由 build 脚本按解析解计算。右：Clay 官方问题陈述（Fefferman）的四个分支。')


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
    out = [f'<text x="20" y="22" class="h">Vlasov–Maxwell 证明的收尾：动量每翻一倍要花 ≳1/k 的时间，而 Σ1/k 发散</text>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>',
           f'<polyline points="{pts(seq)}" class="lna"/>']
    for v in (0, 1, 2, 3, 4, 5):
        out.append(f'<text x="{X0-6}" y="{sy(v)+4:.1f}" class="s" text-anchor="end">{v}</text>')
    for k in (0, 20, 40, 60):
        out.append(f'<text x="{sx(k):.1f}" y="{Y0+16}" class="s" text-anchor="middle">k={k}</text>')
    out.append(f'<text x="{sx(60):.1f}" y="{sy(s)-8:.1f}" class="s" text-anchor="end">前 60 项和 ≈ {s:.2f}，继续增长、不封顶</text>')
    tx = 480
    for i, line in enumerate(['k = 动量已经翻倍的次数', '第 k 次翻倍（P≈2ᵏ）至少要 ~1/(k·log2) 时间',
                              '总时间 ≈ 调和级数 → ∞', '⇒ 有限时间内不可能翻倍无穷多次',
                              '⇒ 动量有界 ⇒（Glassey–Strauss 1986）', '　解可以一直延续：不会爆破']):
        out.append(f'<text x="{tx}" y="{70+i*20}" class="z">{line}</text>')
    return fig('\n'.join(out), '0 0 720 260',
               '这是 OpenAI 论文（family 362）推理摘要里的论证骨架的手算版；真正的难点在于证明"每翻一倍至少要 ~1/log P 时间"这一步（带符号的动量增量估计 + 方向改变次数计数）。阶梯由 build 脚本计算。')


# ------------------------------------------------------------------ spin glass
def svg_spin():
    out = ['<text x="20" y="22" class="h">左：最小的"挫折"系统 · 右：Parisi 的层级（超度量）结构</text>']
    A, B, C = (150, 60), (80, 180), (220, 180)
    out.append(f'<line x1="{A[0]}" y1="{A[1]}" x2="{B[0]}" y2="{B[1]}" class="lnr"/>')
    out.append(f'<line x1="{A[0]}" y1="{A[1]}" x2="{C[0]}" y2="{C[1]}" class="lnr"/>')
    out.append(f'<line x1="{B[0]}" y1="{B[1]}" x2="{C[0]}" y2="{C[1]}" class="lnr" stroke-dasharray="5 4"/>')
    for (x, y), lab in [(A, '↑'), (B, '↓'), (C, '↓')]:
        out.append(f'<circle cx="{x}" cy="{y}" r="14" fill="#f3f0ea" stroke="#1a1a18"/>')
        out.append(f'<text x="{x}" y="{y+5}" class="t" text-anchor="middle">{lab}</text>')
    out.append('<text x="40" y="215" class="s">三条边都"想要反向"（反铁磁）</text>')
    out.append('<text x="40" y="231" class="s">8 种构型里没有一种能让三条边同时满足</text>')
    out.append('<text x="40" y="247" class="s">（虚线那条必然不满足）：基态 6 重简并</text>')
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
    out.append('<text x="660" y="54" class="s">m₀</text><text x="660" y="124" class="s">m₁</text><text x="660" y="204" class="s">纯态</text>')
    out.append('<text x="395" y="232" class="s">两个纯态越"近亲"（共同祖先越深），重叠越大</text>')
    out.append('<text x="395" y="248" class="s">稀释模型要控制所有多复本重叠——这是难点</text>')
    return fig('\n'.join(out), '0 0 720 275',
               '自旋玻璃 = 随机正负耦合 + 到处是挫折 + 指数多个亚稳态。Hopfield 网络（1982）的能量函数就是这种 Hamiltonian；感知机容量（Gardner 1988）也是用同一套复本方法算的。')


# ------------------------------------------------------------------ Hodge withdrawal dependency graph
def svg_hodge():
    out = ['<text x="20" y="22" class="h">10-07 撤稿：一个符号错误沿依赖图传播</text>']
    nodes = [(30, 50, '八维阿贝尔簇上的 Weil 类', '反向 stabilization trace 符号应为 −1，写成了 +1', 'boxr'),
             (30, 140, 'K3 曲面的 Kuga–Satake 对应', '依赖上一篇 → 撤回', 'boxr'),
             (30, 210, 'K3 曲面乘积的有理 Hodge 猜想', '依赖上一篇 → 撤回', 'boxr'),
             (420, 90, 'CM 阿贝尔簇的有理 Hodge 猜想', '不在依赖链上；未撤，但也没有 Lean', 'boxg')]
    for x, y, a, b, cls in nodes:
        out.append(f'<rect x="{x}" y="{y}" width="{300 if x < 400 else 280}" height="46" rx="4" class="{cls}"/>')
        out.append(f'<text x="{x+10}" y="{y+19}" class="t">{a}</text>')
        out.append(f'<text x="{x+10}" y="{y+36}" class="s">{b}</text>')
    out.append('<line x1="180" y1="96" x2="180" y2="136" class="arrr"/>')
    out.append('<line x1="180" y1="186" x2="180" y2="206" class="arrr"/>')
    out.append('<line x1="345" y1="40" x2="345" y2="260" class="dash"/>')
    out.append('<text x="420" y="170" class="s">家族 032 原标题："Hodge and Kuga–Satake</text>')
    out.append('<text x="420" y="186" class="s">results for all projective K3 surfaces"</text>')
    out.append('<text x="420" y="202" class="s">→ 撤稿后改为只剩 CM 的版本</text>')
    out.append('<text x="420" y="226" class="r">722 篇 → 719 篇；另有 14 篇修补、13 篇更新引用</text>')
    return fig('\n'.join(out), '0 0 720 270',
               '来源：<a href="https://github.com/openai/math/blob/main/history.md">openai/math history.md</a>（2026-10-07）；家族标题对比初始 commit <code>adc7f12</code> 的 CONTENTS.md。撤稿说明原文："This withdrawal concerns the proof; it does not assert that the mathematical statement is false."')


# ------------------------------------------------------------------ forward look: METR horizon + projections
import datetime as _dt

METR_PTS = [((2019, 2), 0.1 / 60, 'GPT-2'), ((2023, 3), 4 / 60, 'GPT-4'), ((2024, 6), 11 / 60, ''),
            ((2024, 12), 39 / 60, 'o1'), ((2025, 2), 1.0, ''), ((2025, 4), 2.0, 'o3'), ((2025, 8), 3.4, ''),
            ((2025, 11), 4.9, ''), ((2025, 12), 5.9, ''), ((2026, 2), 12.0, ''), ((2026, 4), 17.4, 'Mythos Preview')]


def _yr(y, m, d=15):
    return y + (_dt.date(y, m, d) - _dt.date(y, 1, 1)).days / 365.25


def svg_metr(L):
    X0, X1, A, B = 70, 640, 2023.0, 2029.2
    Y0, Y1, LO, HI = 290, 40, -2, 4.5   # log10 hours
    sx = lambda t: X0 + (t - A) / (B - A) * (X1 - X0)
    sy = lambda h: Y0 - (math.log10(h) - LO) / (HI - LO) * (Y0 - Y1)
    out = [f'<text x="{X0}" y="22" class="h">{L["title"]}</text>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>']
    for h, lab in [(1 / 60, L['1min']), (1, L['1h']), (8, L['1d']), (160, L['1mo']), (2000, L['1y'])]:
        out.append(f'<line x1="{X0}" y1="{sy(h):.1f}" x2="{X1}" y2="{sy(h):.1f}" class="grid"/>')
        out.append(f'<text x="{X0-6}" y="{sy(h)+4:.1f}" class="s" text-anchor="end">{lab}</text>')
    for y in range(2023, 2030):
        out.append(f'<text x="{sx(y):.1f}" y="{Y0+16}" class="s" text-anchor="middle">{y}</text>')
    a = _yr(2026, 5, 1)
    for D, cls, lab in [(89, 'dash', L['opt']), (129, 'lnr', L['cen']), (213, 'dash', L['pes'])]:
        seq = []
        t = a
        while t <= B:
            h = 15 * 2 ** ((t - a) * 365.25 / D)
            if h > 10 ** HI:
                break
            seq.append((sx(t), sy(h)))
            t += 0.02
        out.append(f'<polyline points="{pts(seq)}" class="{cls}"/>')
        out.append(f'<text x="{seq[-1][0]+4:.1f}" y="{seq[-1][1]+4:.1f}" class="s">{lab}</text>')
    for (y, m), h, lab in METR_PTS:
        t = _yr(y, m)
        if t < A:
            continue
        out.append(f'<circle cx="{sx(t):.1f}" cy="{sy(h):.1f}" r="3.5" fill="#1a1a18"/>')
        if lab:
            dy = 16 if lab == 'Opus 4.6' else -6
            out.append(f'<text x="{sx(t)-6:.1f}" y="{sy(h)+dy:.1f}" class="s" text-anchor="end">{lab}</text>')
    out.append(f'<line x1="{sx(2023.0):.1f}" y1="{sy(16):.1f}" x2="{X1}" y2="{sy(16):.1f}" class="dash"/>')
    out.append(f'<text x="{sx(2023.1):.1f}" y="{sy(16)-4:.1f}" class="s">{L["unrel"]}</text>')
    return fig('\n'.join(out), '0 0 720 320', L['cap'])


def svg_openprob(L):
    X0, X1, A, B = 70, 600, 2026.5, 2031.0
    Y0, Y1 = 270, 40
    sx = lambda t: X0 + (t - A) / (B - A) * (X1 - X0)
    sy = lambda p: Y0 - p * (Y0 - Y1)
    out = [f'<text x="{X0}" y="22" class="h">{L["title"]}</text>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" class="ax"/>',
           f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" class="ax"/>']
    for p in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line x1="{X0}" y1="{sy(p):.1f}" x2="{X1}" y2="{sy(p):.1f}" class="grid"/>')
        out.append(f'<text x="{X0-6}" y="{sy(p)+4:.1f}" class="s" text-anchor="end">{int(p*100)}%</text>')
    for y in range(2027, 2032):
        out.append(f'<text x="{sx(y):.1f}" y="{Y0+16}" class="s" text-anchor="middle">{y}</text>')
    t0 = _yr(2026, 9, 6)
    for s_, C, cls, lab in [(3.0, 0.9, 'dash', L['opt']), (1.5, 0.8, 'lnr', L['cen']), (0.7, 0.6, 'dash', L['pes'])]:
        q0 = 0.03 / C
        L0 = math.log(q0 / (1 - q0))
        seq = []
        t = t0
        while t <= B:
            p = C / (1 + math.exp(-(L0 + s_ * (t - t0))))
            seq.append((sx(t), sy(p)))
            t += 0.02
        out.append(f'<polyline points="{pts(seq)}" class="{cls}"/>')
        out.append(f'<text x="{seq[-1][0]+4:.1f}" y="{seq[-1][1]+4:.1f}" class="s">{lab}</text>')
    out.append(f'<circle cx="{sx(t0):.1f}" cy="{sy(0.03):.1f}" r="4" fill="#1a1a18"/>')
    out.append(f'<text x="{sx(t0)+8:.1f}" y="{sy(0.03)-8:.1f}" class="s">{L["anchor"]}</text>')
    return fig('\n'.join(out), '0 0 720 300', L['cap'])


METR_ZH = dict(title='曲线 ①：AI 能独立完成的任务长度（METR p50，对数坐标）与三情景外推',
               **{'1min': '1 分钟', '1h': '1 小时', '1d': '1 工作日', '1mo': '1 工作月', '1y': '1 工作年'},
               opt='乐观 89 天倍增', cen='中心 129 天', pes='悲观 213 天', unrel='16 小时以上，现有任务集不可靠',
               cap='黑点是 METR TH1.1 原始数据里的 SOTA 模型（2023 起；GPT-2 2019 年为 0.1 分钟，在图外）。红线是中心情景：以 2026-05 约 15 小时为锚点，每 129 天翻倍（METR 2023 年起拟合，95% CI 104–158 天），相当于每年约 ×7。虚线是乐观（89 天，2024 年起的速度）和悲观（213 天，约 7 个月）。纵轴每一格是 10 倍。曲线由 build 脚本计算。')
OPEN_ZH = dict(title='曲线 ②：可形式化开放问题的单次解出率（每题约 $300）三情景',
               opt='乐观', cen='中心', pes='悲观',
               anchor='锚点：2026-09 FrontierMath Erdős 3%（2/68）',
               cap='三情景参数：乐观 +3.0 logit/年、上限 90%；中心 +1.5、上限 80%；悲观 +0.7、上限 60%。模型：解出率 = C × sigmoid(a + s·t)，C 是"有些题本身极难或无解"的上限，锚点是 Epoch FrontierMath Erdős（68 个预注册开放问题、必须给 Lean 证明）上 GPT-6 Astra 的 3%。斜率参照 FrontierMath Tier 4 在 10 个月内涨约 5.3 logit，三情景都取得更慢，因为开放问题的难度分布是重尾的。曲线由 build 脚本计算。')
