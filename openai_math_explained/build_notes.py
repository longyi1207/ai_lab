#!/usr/bin/env python3
"""Build notes.html for the "OpenAI math release, explained from zero" deck (cyber_ai_fundamentals style).

Rebuild:  python3 build_notes.py  →  notes.html
PDF:      Chrome headless print-to-pdf (see README.md)
"""
from pathlib import Path
import figs

ROOT = Path(__file__).resolve().parent
CSS = (ROOT / "_notes_base.css").read_text()

EXTRA_CSS = """
  .svg-fig { margin: 24px 0 28px; padding: 18px 16px 12px; background: var(--code-bg);
    border: 1px solid var(--rule); border-radius: 4px; }
  .svg-fig svg { width: 100%; height: auto; display: block; }
  .svg-fig .cap { font-size: 12.5px; color: var(--ink-faint); margin-top: 10px; line-height: 1.5; max-width: none; }
  .ladder { margin: 18px 0 22px; }
  .ladder .rung { display: grid; grid-template-columns: 74px 1fr; gap: 12px; padding: 9px 0;
    border-bottom: 1px solid var(--rule-soft); align-items: start; }
  .ladder .rung:last-child { border-bottom: none; }
  .ladder .lvl { color: var(--accent); font-weight: 600; font-family: ui-monospace, monospace; font-size: 13px; }
  .ladder .body { color: var(--ink-dim); line-height: 1.62; font-size: 15px; }
  .ladder .body strong { color: var(--ink); }
  .claim { margin: 18px 0; padding: 12px 16px; border-left: 3px solid var(--accent); background: var(--code-bg); }
  .claim .label { font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent); display: block; margin-bottom: 4px; }
  .claim p { margin: 0 0 8px; } .claim p:last-child { margin-bottom: 0; }
  .verdict { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 16px 0 22px; }
  @media (max-width: 720px) { .verdict { grid-template-columns: 1fr; } }
  .verdict .panel { border: 1px solid var(--rule-soft); border-radius: 4px; padding: 12px 14px 8px; }
  .verdict .panel h4 { font-family: ui-monospace, monospace; font-size: 12.5px; color: var(--accent); margin: 0 0 8px; }
  .verdict .panel p, .verdict .panel li { font-size: 14px; max-width: none; }
  pre { white-space: pre-wrap; word-break: break-all; }
  .kicker { break-after: avoid; page-break-after: avoid; }
  .tg { font-family: ui-monospace, monospace; font-size: 11px; color: var(--ink-faint); }
  blockquote { margin: 14px 0; padding-left: 14px; border-left: 2px solid var(--rule); color: var(--ink-dim); font-style: italic; }
  .jj h4 { font-size: 14px; margin: 22px 0 8px; color: var(--ink); }
  .jj blockquote { font-style: normal; }
  .jj th { text-transform: none; letter-spacing: 0; }
  .jj table { break-inside: auto; page-break-inside: auto; }
  .jj tr { break-inside: avoid; page-break-inside: avoid; }
  @media print {
    nav.toc { display: none !important; }
    main { max-width: 100%; padding: 24px 32px; }
    .svg-fig, .claim, .verdict, table { break-inside: avoid; page-break-inside: avoid; }
    h2, h3 { break-after: avoid; }
    a { color: var(--ink); text-decoration: none; }
  }
"""

REPO = "https://github.com/openai/math"

TOC = [
    ("scope", "0", "怎么用"), ("basics", "1", "先补课"), ("event", "2", "发生了什么"),
    ("verify", "3", "Lean 能保证什么"), ("qrh", "4", "准黎曼猜想"), ("pi", "5", "π 的逼近"),
    ("matmul", "6", "矩阵乘法 ω"), ("ugc", "7", "Unique Games"), ("bpl", "8", "L = BPL"),
    ("color", "9", "平面着色"), ("thompson", "10", "Thompson 群"), ("ns", "11", "Navier–Stokes"),
    ("vlasov", "12", "等离子体"), ("spin", "13", "自旋玻璃"), ("kakeya", "14", "挂谷与限制"), ("hodge", "15", "撤稿案例"),
    ("synthesis", "16", "横向看"), ("ai", "17", "对 AI 意味着"),
    ("fwd-calib", "18", "前瞻：先校准"), ("fwd-cs", "19", "计算机/密码/量子"), ("fwd-phys", "20", "物理/化学/材料"),
    ("fwd-bio", "21", "生物/医学/神经"), ("fwd-ai", "22", "AI 理论与对齐"), ("fwd-soc", "23", "经济/社会/治理"),
    ("fwd-synth", "24", "全景与 Top 10"),
    ("reactions", "25", "反应"), ("learn", "26", "开放问题/继续学"), ("sources", "27", "术语/来源"),
]

BODY = r'''
<header class="masthead">
  <div class="kicker">学习 deck · 给非数学背景的 AI 研究者</div>
  <h1>OpenAI 的 719 篇 AI 数学论文：从零读懂它们在说什么</h1>
  <p>2026-10-06，OpenAI 一次性公开了一个未发布内部模型生成的 <strong>722 篇数学手稿（372 个结果族）</strong>，其中声称解决了准黎曼猜想、Unique Games 猜想、矩阵乘法指数 ω ≤ 9/4、Thompson 群不可顺从、平面不能 5 着色等一批几十年的名题；第二天因一个符号错误撤回 3 篇。数学界称之为 "Mathocalypse"。这份 deck 的目标：<strong>只用线性代数 + 微积分 + 高中数学</strong>，把其中 11 个代表性结果各自讲到"能判断它有多大、多难、为什么重要、核实到哪一步"。</p>
  <p class="meta">2026-10-08 首版；10-09 改版（每个结果合并为从零详解的单一版本；新增 §14 挂谷问题与 Fourier 限制；Part II 前瞻重写为 §18–§24）· repo 快照 openai/math@fd4aeeb（含 10-07 撤稿与修补）· 每条事实标来源；[P] = 读过一手材料（论文/repo/Lean 源码），[R] = 二手报道，⚠ = 未核实或有冲突 · 研究底稿保存在作者的研究笔记中，未随本 deck 公开</p>
</header>

<section id="scope">
  <div class="kicker">Orientation</div>
  <h2><span class="n">0.</span>这份 deck 能带你到哪，到不了哪</h2>
  <div class="note">
    <span class="label">读完能得到</span>
    <p>对 11 个头条结果各有一个"阶梯式"理解：从一个你能手算的玩具例子出发，一级一级走到真正的命题；知道这个问题此前卡了多少年、卡在哪；知道 OpenAI 具体声称了什么、Lean 形式化覆盖到哪、人类专家目前怎么说；以及它对数学、对 AI、对 AI safety 各意味着什么。</p>
  </div>
  <div class="note bug">
    <span class="label">读完得不到</span>
    <p>判断任何一个证明是否正确的能力。这 11 个结果里，截至 10-09 <strong>没有一个</strong>有人类领域专家公开表示"我读完并确认了"。本 deck 里的"核实"只到两层：① 我们静态审查了 Lean 源码与陈述；② 汇总了公开反应。都标注了来源和可信度。</p>
  </div>
  <div class="note">
    <span class="label">选题说明</span>
    <p>372 个结果族里只讲了 11 个。筛选标准：① 问题有名，人类专家公认是难题（首日报道和数学家点名的优先）；② 尽量有 Lean 形式化，方便讲清"核实到哪一步"；③ 能用高中数学搭起来，并且和计算机、AI 有联系；④ OpenAI 公开了推理摘要的优先。首版（10-08）实际是按四个领域（数论、理论计算机、组合与群论、物理/偏微分方程）去挑的，没有系统地看完全部 17 个学科，调和分析整组（挂谷、Fourier 限制、Bochner–Riesz、局部光滑化、Falconer 距离）因此漏掉，10-09 补为 §14。<strong>仍未覆盖、但按名气看至少同一量级的</strong>还有：有理数上的 Hilbert 第十问题（004）、Hadwiger 猜想反例（157）、Kaplansky 零因子猜想反例（196）、自由群因子同构（287）、Baum–Connes 与 Kadison–Kaplansky 反例（285）、Hilbert–Smith 猜想（304）、Hilbert 第十六问题的一致界（143）、Erdős 倒数和猜想与拟多项式 Szemerédi 界（159）[推测：只读了标题，未读论文]。完整目录见 <a href="''' + REPO + '''/blob/main/overview.pdf">overview.pdf</a>。</p>
  </div>
  <h3>0.1 阅读路径</h3>
  <p>§1 先补三样基础（数学家在做什么、什么叫"开放问题"、怎么判断一个结果有多大）。§2–§3 是事件本身和"Lean 到底保证了什么"——<strong>这两节决定你该怎么读后面所有的"声称"</strong>。§4–§14 是 11 个结果，每节都从最基础的概念讲起，配可以手算的小例子和【检查】练习，结构相同：<em>先说结论 → 从零搭概念 → OpenAI 声称了什么 → 核实到什么程度 → 如果为真意味着什么</em>，可以按兴趣跳读。§15 是撤稿案例，§16–§17 是横向总结和对 AI 的含义。<strong>Part II（§18–§24）是前瞻</strong>：如果数学被 AI 大规模解决，或者 AI 的其他能力也突破，计算机与密码、物理与化学、生物与医学、AI 本身、经济与治理分别会发生什么。§18 先用历史和三条能力曲线校准；§19–§23 每节挑出该领域真正重要的问题，逐个讲清"瓶颈是不是数学、AI 能改变什么、更深远的影响是什么、大概什么时候"；§24 是全景、Top 10 和时间线。§25 是各方反应，§26 是开放问题和继续学习的路线，§27 是术语表与来源。</p>
  <h3>0.2 一张速查表</h3>
  <div class="tbl"><table>
    <thead><tr><th>§</th><th>结果（family 编号）</th><th>卡了多久</th><th>Lean</th><th>一句话</th></tr></thead>
    <tbody>
      <tr><td>4</td><td>准黎曼猜想（003）</td><td>~125 年</td><td>有</td><td>ζ 在 Re s &gt; 7/8 整块无零点</td></tr>
      <tr><td>5</td><td>π 的无理性指数 = 2（017）</td><td>~70 年</td><td>有⚠</td><td>π 不能被分数"异常好"地逼近</td></tr>
      <tr><td>6</td><td>矩阵乘法 ω ≤ 9/4（107）</td><td>57 年</td><td>有</td><td>一次下降 0.12，此前 12 年只降 0.0017</td></tr>
      <tr><td>7</td><td>Unique Games 猜想（102）</td><td>24 年</td><td>有</td><td>一大批近似算法的"最优性"变成定理</td></tr>
      <tr><td>8</td><td>L = RL = BPL（103）</td><td>~30 年</td><td>有</td><td>小内存计算里随机性毫无用处</td></tr>
      <tr><td>9</td><td>平面不能 5 着色（158）</td><td>76 年（下界上次推进在 2018）</td><td>有</td><td>平面色数 ∈ {6, 7}</td></tr>
      <tr><td>10</td><td>Thompson 群 F 不可顺从（248）</td><td>47 年</td><td>有</td><td>两个方向都有人"证明"过又撤回的名题</td></tr>
      <tr><td>11</td><td>Navier–Stokes 爆破（9 月单独发布）</td><td>千禧年问题</td><td>有</td><td>只覆盖"带外力"分支；归属有争议</td></tr>
      <tr><td>12</td><td>相对论 Vlasov–Maxwell（362）</td><td>40 年</td><td>有</td><td>等离子体模型的大初值整体光滑性（单粒子种类）</td></tr>
      <tr><td>13</td><td>Mézard–Parisi 公式（221）</td><td>25 年</td><td>有</td><td>稀疏自旋玻璃的自由能公式（偶数元情形）</td></tr>
      <tr><td>14</td><td>挂谷问题：四维集合 + 三维极大函数（074）</td><td>四维：数十年；三维集合版 2025 年才解决</td><td>无</td><td>四维挂谷集维数为满 4（此前约 3.059）；同批还声称三维 Fourier 限制猜想（077）</td></tr>
      <tr><td>15</td><td>Hodge 相关撤稿（032 等）</td><td>—</td><td>无</td><td>一个符号错误撤掉 3 篇：未形式化的风险</td></tr>
    </tbody>
  </table></div>
</section>

<section id="basics">
  <div class="kicker">Fundamentals · 先补课</div>
  <h2><span class="n">1.</span>数学家到底在做什么</h2>
  <p>一句话：<strong>研究抽象对象的结构，并用证明确立关于它们的真理</strong>。区分数学、科学、工程的关键是"怎么知道一件事是对的"：数学靠逻辑证明（一旦证明永远成立），科学靠实验（可能被推翻），工程靠"能用、测出来够好"。</p>
  <h3>1.1 四个词</h3>
  <div class="tbl"><table>
    <thead><tr><th>词</th><th>意思</th><th>这次事件里的例子</th></tr></thead>
    <tbody>
      <tr><td class="mono">猜想 conjecture</td><td>大家相信但没人证明的命题</td><td>Unique Games 猜想（Khot 2002）</td></tr>
      <tr><td class="mono">定理 theorem</td><td>已被证明的命题</td><td>Goemans–Williamson 的 0.878 算法</td></tr>
      <tr><td class="mono">反例 counterexample</td><td>一个具体对象，说明某个"对所有…都成立"的猜想是错的</td><td>9 维 Borsuk 反例；本批约 20% 的结果是反例/否证</td></tr>
      <tr><td class="mono">形式化 formalization</td><td>把证明写成计算机能逐步检查的代码（本批用 Lean 4）</td><td>本批约 300/719 个顶层结果有 Lean 证明</td></tr>
    </tbody>
  </table></div>
  <h3>1.2 两种数学文化</h3>
  <p>Fields 奖得主 Gowers 在 <a href="https://www.dpmms.cam.ac.uk/~wtg10/2cultures.pdf">The Two Cultures of Mathematics</a>（2000）里把数学家分成<strong>解题者</strong>（攻克具体难题，比如 Erdős 问题）和<strong>理论建构者</strong>（发明新概念、新框架，比如"群""流形"）。Thurston 在 <a href="https://arxiv.org/abs/math/9404236">On Proof and Progress in Mathematics</a>（1994）里进一步说：数学的目的不是产出定理，而是<strong>增进人类的理解</strong>。这两篇是读懂这次争论的钥匙——AI 这次大规模攻破的是"解题者文化"那一侧，Tao 说的"Math 1.0 结束"正是在这里。</p>
  <h3>1.3 怎么判断一个结果"有多大"：五个问题</h3>
  <ol>
    <li><strong>卡了多久、谁试过？</strong> 一个 50 年无人解决、顶尖专家多次失败的问题，和一个刚提出两年的问题，分量完全不同。</li>
    <li><strong>是"最后一步"还是"跳了一大步"？</strong> 矩阵乘法 ω 从 2.3713 到 2.3711 是前者，到 2.25 是后者。</li>
    <li><strong>能解锁多少别的结果？</strong> Unique Games 一旦成立，几百篇"若 UGC 则……"的论文同时变成定理。</li>
    <li><strong>方法新不新？</strong> 新方法往往比结论本身更重要，因为它能被复用。</li>
    <li><strong>题目是谁选的、失败了多少？</strong> 这是本次事件最容易被忽略的一问，见 §2.3 和 §16。</li>
  </ol>
</section>

<section id="event">
  <div class="kicker">The event · 时间线与数字</div>
  <h2><span class="n">2.</span>发生了什么</h2>
  <div class="tbl"><table>
    <thead><tr><th>日期</th><th>事件</th></tr></thead>
    <tbody>
      <tr><td class="mono">2025-07</td><td>OpenAI 实验模型与 Google DeepMind Gemini Deep Think 在 IMO 2025 达到金牌分数（35/42）——"有标准答案的竞赛题"被攻破。 <span class="tg">[R]</span></td></tr>
      <tr><td class="mono">2026-09-08</td><td>OpenAI 宣布约 1 万个 agent、88 小时证明了 3D Navier–Stokes 的"带外力有限时间爆破"（166 页 + Lean），引发归属争议（§11）。 <span class="tg">[P][R]</span></td></tr>
      <tr><td class="mono">2026-09 下旬</td><td>普林斯顿 IAS 主持的 Advisory Group on Mathematics and AI（成员含 Terence Tao）发布 AI 数学成果的出版建议。 <span class="tg">[R]</span></td></tr>
      <tr><td class="mono"><strong>2026-10-06</strong></td><td><a href="''' + REPO + '''">openai/math</a> 发布：722 篇手稿 / 372 个结果族，Apache-2.0，附 Lean 库与 10 份删节版推理摘要。 <span class="tg">[P]</span></td></tr>
      <tr><td class="mono">2026-10-07</td><td>撤回 3 篇（同一符号错误连锁），修补 14 篇，13 篇更新引用，新增 6 个形式化 → <strong>719 篇</strong>，"顶层结果形式化 300/719 ≈ 42%"。AHM（Association for Human Mathematics）声明经 Tao 博客转载；Scott Aaronson 发文 <a href="https://scottaaronson.blog/?p=10169">"The Mathocalypse"</a>。 <span class="tg">[P][R]</span></td></tr>
      <tr><td class="mono">2026-10-08</td><td>Tao 博客发 Lozano-Robledo 客座文 <a href="https://terrytao.wordpress.com/2026/10/08/what-should-we-tell-our-students/">What should we tell our students?</a>。 <span class="tg">[P]</span></td></tr>
    </tbody>
  </table></div>
  <h3>2.1 怎么产出的</h3>
  <p>README 原文 <span class="tg">[P]</span>："The vast majority of results were obtained with the same procedure using an unreleased internal OpenAI model. On average, each result used three hours of ChatGPT Pro thinking compute… the model was posed approximately 4,000 problems… requiring an appropriate level of significance led to the catalog." 也就是：<strong>约 4,000 道开放题 → 按"够重要"筛选 → 372 族</strong>。OpenAI 发言人对 Scientific American 说几乎所有结果都来自"交给单个 agent 的单个 prompt"<span class="tg">[R]</span>；MIT 的 Andrew Sutherland 回应："在模型能被复现之前，'一发入魂'应视为未验证——要看收据。"</p>
  <p><strong>例外</strong>：README 承认 ζ 零点无零区（§4）和 CM 阿贝尔簇的 Hodge 猜想（§15）<em>不是</em>走这个固定流程产出的，并且 Re s &gt; 11/12 那份写作经过人工编辑。具体例外是什么（更多算力？人工引导？）没有披露 ⚠。</p>
  <h3>2.2 数字对账</h3>
  <div class="tbl"><table>
    <thead><tr><th>说法</th><th>真实含义</th></tr></thead>
    <tbody>
      <tr><td>"722 篇" vs "719 篇"</td><td>发布时 722；10-07 撤回 3 篇后 719。早期新闻用 722。</td></tr>
      <tr><td>"372 族" vs "377"</td><td>目录编号 001–377，其中 045/061/070/123/163 空缺，实际 372 族。</td></tr>
      <tr><td>"~42% 已形式化"</td><td>300 个<em>顶层结果</em> ÷ 719 篇<em>手稿</em>——分子分母单位不同。按族算，242/372 ≈ 65% 的族有 Lean 范围说明文档。</td></tr>
      <tr><td>"162 篇完整 + 73 篇部分形式化"</td><td>部分媒体的说法，未找到出处 ⚠。</td></tr>
    </tbody>
  </table></div>
  {{FIG_FIELDS}}
  <h3>2.3 必须先记住的一件事：选择效应</h3>
  <p>Epoch AI 的 <a href="https://arxiv.org/abs/2609.25050">FrontierMath Erdős</a>（2026-09）选了 68 个<strong>预先登记</strong>为开放的 Erdős 问题，要求 Lean 证明，结果 GPT-6 Astra 只解出 2 个（≈3%），其他模型 0 个。OpenAI 这次是<strong>事后筛选</strong>：4,000 题里留下"够重要"的、没公开失败清单。粗算命中率 ≤ 9%（按族）——但两边题目难度不可比。<strong>两个数字都对，只是回答的问题不同</strong>：前者问"随便给一道开放题它能做出来吗"，后者问"给它 4,000 道，能挑出多少好结果"。</p>
</section>

<section id="verify">
  <div class="kicker">Verification · 读懂所有"声称"之前</div>
  <h2><span class="n">3.</span>"有 Lean 证明"到底保证了什么</h2>
  <p>Lean 是一种"证明助手"：你把定理和证明写成代码，一个很小的<strong>内核</strong>逐步检查每一步推理。只要内核没 bug、只用了公认的公理，通过检查就意味着"这个 Lean 陈述为真"。它和人类审稿的区别类似于"编译器 + 类型系统"和"code review"的区别——后者会漏，前者不会漏<em>它检查的那部分</em>。</p>
  {{FIG_TRUST}}
  <h3>3.1 我们对 Lean 库做的静态审计 <span class="tg">[P]</span></h3>
  <div class="tbl"><table>
    <thead><tr><th>检查项</th><th>结果</th><th>含义</th></tr></thead>
    <tbody>
      <tr><td class="mono">sorry（未完成证明）</td><td>0</td><td>没有"先空着"的步骤</td></tr>
      <tr><td class="mono">axiom 声明</td><td>0（命中全在注释里）</td><td>没有偷偷加公理</td></tr>
      <tr><td class="mono">native_decide / implemented_by / extern</td><td>0</td><td>没有"信任编译器"的后门</td></tr>
      <tr><td class="mono">decide +kernel</td><td>≈131 万行，5,848 个文件</td><td>大量有限计算由内核完成——仍在可信范围内，但证明极其庞大</td></tr>
      <tr><td class="mono">Comparator 配置</td><td>416 个，全部只允许三条标准公理；仅 2 个开启第二独立内核 nanoda</td><td>见下文</td></tr>
      <tr><td class="mono">lean/patches/</td><td>24 个补丁，打在第三方依赖库上（不是 Lean 内核，也不是 Mathlib），最大约 2 MB</td><td>补丁会改依赖库里的定义与证明 ⚠</td></tr>
      <tr><td class="mono">依赖</td><td>30 个，其中 11 个来自来源不明的 <code>lana-agents/*</code></td><td>信任链上的开放点 ⚠</td></tr>
      <tr><td class="mono">formalization.yaml</td><td><code>review: status: unchecked</code></td><td>OpenAI 自己标注：未经审查</td></tr>
    </tbody>
  </table></div>
  <p class="tg">范围：lean/OAI/ 共 122,458 个 .lean 文件、约 2,600 万行；只做了源码 grep 与配置统计，未实际编译（全库编译需数 GB 内存与 Linux 沙箱）。独立复核：Dave Goldblatt 用 Comparator + nanoda 两个内核跑通了 ζ 的 7/8 证明（约 63 分钟）<a href="https://github.com/davegoldblatt/openai-zeta-proof-check">[repo]</a>；另有第三方复查了 9/4 矩阵乘法定理的陈述 <a href="https://github.com/erenciracioglu-dotcom/openai-math-9-4-lean-check">[repo]</a>。</p>
  <h3>3.2 Comparator：防的是什么、不防什么</h3>
  <p>Lean FRO 的 <a href="https://github.com/leanprover/comparator">Comparator</a> 拿一个"挑战文件"（只有定理陈述，证明处写 <code>sorry</code>，只引用 Mathlib 等可信库）和一个"解答模块"做比对：解答里的定理必须和挑战里的陈述<strong>是同一个类型</strong>，且只用允许的公理。它防的是"在证明里偷换陈述、改定义、加公理"。它<strong>不防</strong>：挑战文件本身写的陈述是否忠实于论文想说的话——而挑战文件是 OpenAI（的 agent）自己写的。所以本 deck 每一节的"核实状态"，重点都在<strong>逐行读陈述</strong>。</p>
  <div class="note bug">
    <span class="label">一个活生生的反面例子</span>
    <p>OpenAI 的平面着色论文脚注提到：2026-05 有一份手稿宣称平面色数 = 7 并附有"形式化定理"——但那个定理<strong>把一个错误的密度上界当成了假设</strong>。形式化本身没错，错的是被证明的命题。<span class="tg">[P，经 OpenAI 论文转述；原稿未读 ⚠]</span> 这和 AI 里的"规格博弈"（specification gaming）是同一类问题：系统完美满足了写下来的规格，但规格不是你真正想要的。</p>
  </div>
</section>

{{RESULT:qrh}}

{{RESULT:pi}}

{{RESULT:matmul}}

{{RESULT:ugc}}

{{RESULT:bpl}}

{{RESULT:color}}

{{RESULT:thompson}}

{{RESULT:ns}}

{{RESULT:vlasov}}

{{RESULT:spin}}

{{RESULT:kakeya}}
<section id="hodge">
  <div class="kicker">反面案例 · family 032 与 10-07 撤稿</div>
  <h2><span class="n">15.</span>一个符号错误撤掉 3 篇：未形式化的风险</h2>
  <p><strong>Hodge 猜想</strong>（千禧年问题）极简版：在光滑射影复代数簇上，有些"拓扑洞"可以由代数方程定义的子簇来"填"；猜想说凡是满足某个线性代数条件的洞都能这样填。p = 1 的情形 1924 年已知（Lefschetz）。</p>
  <p>OpenAI 声称对所有<strong>复乘（CM）阿贝尔簇</strong>证明了有理 Hodge 猜想（53 页）——这只是一个特殊类，不是千禧年问题本身；而且它和 ζ 无零区一样，<strong>不是</strong>按固定流程产出的，<strong>没有 Lean</strong>。<span class="tg">[P]</span></p>
  {{FIG_HODGE}}
  <h3>15.1 发生了什么 <span class="tg">[P]</span></h3>
  <p>history.md（10-07）："In 'Algebraicity of Weil classes on split abelian eightfolds' a sign error invalidates a stabilization-trace cancellation argument and the construction used by two dependent papers." 一个本应是 −1 的符号被当成 +1，带符号的计数从声称的 0 变成 −2m ≠ 0，关键定理的前提不成立；依赖它的两篇 K3 曲面论文连带撤回。CM 主论文不引用被撤论文，不在这条链上。</p>
  <h3>15.2 三个教训</h3>
  <ol>
    <li><strong>未形式化 ≈ 未验证</strong>：只有约 42% 的顶层结果有 Lean。这个错误只是一个符号——人眼和模型自查都漏了，Lean 必然会抓到。</li>
    <li><strong>错误沿依赖图传播</strong>：一个引理错了，三篇论文一起倒，下游 13 篇要更新引用——和 agent 长链推理中的错误复合是同一种结构。</li>
    <li><strong>标题漂移</strong>：家族 032 原名 "Hodge and Kuga–Satake results for all projective K3 surfaces"，撤稿后才降级为 CM 版本。读批量 AI 产出时，以最新 commit + history.md 为准，不以首发新闻为准。</li>
  </ol>
</section>

<section id="synthesis">
  <div class="kicker">Synthesis · 横向看</div>
  <h2><span class="n">16.</span>把 11 个结果放在一起看</h2>
  <div class="tbl"><table>
    <thead><tr><th>结果</th><th>此前状态</th><th>声称的跳跃</th><th>陈述忠实？</th><th>人类专家确认</th></tr></thead>
    <tbody>
      <tr><td>准黎曼 7/8</td><td>无任何固定宽度无零带</td><td>质变</td><td>是（Mathlib 标准定义）</td><td>无</td></tr>
      <tr><td>μ(π) = 2</td><td>7.103</td><td>直接到终点</td><td>是（未登记 yaml ⚠）</td><td>无</td></tr>
      <tr><td>ω ≤ 9/4</td><td>2.371177</td><td>−0.12，越过已知壁垒</td><td>是</td><td>无</td></tr>
      <tr><td>UGC</td><td>"半个"（2-to-2，2018）</td><td>完整</td><td>是（更强形式）</td><td>无</td></tr>
      <tr><td>L = BPL</td><td>L^{3/2} 附近 25 年</td><td>完整</td><td>是（定义被锁定）</td><td>无</td></tr>
      <tr><td>平面 χ ≥ 6</td><td>χ ≥ 5（2018）</td><td>+1，新方法</td><td>是（两行陈述）</td><td>无</td></tr>
      <tr><td>Thompson F</td><td>两个方向都有过错误证明</td><td>解决</td><td>是</td><td>无</td></tr>
      <tr><td>NS 爆破</td><td>带外力 Euler 已有前驱</td><td>(C)/(D) 分支</td><td>结构一致</td><td>Clay 未认可，有争议</td></tr>
      <tr><td>Vlasov–Maxwell</td><td>40 年只有带限制的结果</td><td>单种类完整</td><td>是</td><td>无</td></tr>
      <tr><td>Mézard–Parisi</td><td>只有上界</td><td>偶数元类等号</td><td>是（范围比标题窄）</td><td>无</td></tr>
      <tr><td>四维挂谷 / 三维极大</td><td>四维维数下界约 3.059；三维集合版 2025 年刚解决</td><td>直接到 4；三维的更强版本</td><td>无法检查（没有 Lean）</td><td>无</td></tr>
    </tbody>
  </table></div>
  <h3>16.1 五个模式</h3>
  <ol>
    <li><strong>陈述短、证明长</strong>：平面着色陈述两行、证明 3 万行；准黎曼陈述一行、证明 48 万行。这正是"人审陈述、机器审证明"分工最理想的形态——也意味着人类审稿带宽成了新瓶颈。</li>
    <li><strong>论文都异常短</strong>：9/4 矩阵乘法 13 页、Thompson 群 13 页。要么方法真的意外地简洁，要么大量细节压在 Lean 里没写给人看——Gómez-Serrano 说 NS 论文 "not written for humans"。</li>
    <li><strong>跨领域借工具</strong>：Thompson 群用无穷维几何的 Lipschitz 映射；平面着色用遍历论；矩阵乘法用"渐近谱"而不是 40 年来的主流激光法。这可能是 AI 的一个真实优势：它没有人类专家的"领域惯性"。</li>
    <li><strong>"满足题面"与"回答真正的问题"之间的差距</strong>：NS 的外力可以任选；376 把计算放在外力里；平面着色脚注里那个"形式化了错误假设"的反例；Mézard–Parisi 只覆盖偶数元。每一个都是"规格 vs 意图"。</li>
    <li><strong>选择效应</strong>：4,000 题里挑出来的结果 vs 预先登记题目上的 3%（§2.3）。在 OpenAI 公开失败清单之前，无法回答"这个模型解开放问题的真实能力是多少"。</li>
  </ol>
</section>

<section id="ai">
  <div class="kicker">AI & AI safety 视角</div>
  <h2><span class="n">17.</span>这件事对 AI 意味着什么</h2>
  <h3>17.1 数学好 ≠ 全面更聪明，但它是先行指标</h3>
  <p>数学对 AI 有一个独特优势：<strong>答案可以被机器检验</strong>（Lean），这让强化学习可以大量"试错 → 拿反馈 → 改进"。Chollet 的追问正中要害：这些"可验证领域"的进步能否迁移到不可验证的领域？合理的读法是：<strong>凡是能被自动检验的智力工作，接下来都会以类似速度被攻破</strong>——数学只是第一个。</p>
  <h3>17.2 信任瓶颈从"证明"转移到"规格"</h3>
  <p>一旦有了 Lean，问题从"证明对不对"变成"陈述有没有编码对"。这和对齐研究里的核心难题同构：系统可以完美优化你写下的目标，而你写下的目标可能不是你想要的。本 deck 每一节都在做的"逐行读 Lean 陈述"，就是一种 <strong>spec review</strong>——它会成为一项越来越重要、越来越稀缺的人类工作。</p>
  <h3>17.3 "能验证但不能理解"的知识</h3>
  <p>IAS 顾问组的原话：<em>"It is now the case that AI can output mathematical arguments in situations without the human who prompted it being able to understand the arguments, verify them, or take responsibility for them."</em> <span class="tg">[R]</span> 数学是这种局面最先出现、也最干净的领域（因为验证是完美的）。推广到科学：人类可能从"理解者"变成"检验者"。Tao 说的 Math 2.0——把讲解、社区建设、开辟新方向放到和解题同等重要的位置——本质上是在回答"人类在这个新分工里做什么"。</p>
  <h3>17.4 对安全研究的两面</h3>
  <div class="verdict">
    <div class="panel"><h4>好消息</h4><ul>
      <li><strong>验证比发现容易</strong>：如果未来的 AI 能为自己的行为给出形式化证明（"这个动作不会做 X"），人类不必理解它的全部能力，只需检验证明——这是 Guaranteed Safe AI 路线的核心想法，数学 AI 越强越可行。</li>
      <li>本批的 Lean 库本身就是"大规模 AI 产出 + 机器验证"的第一个真实样本，可以研究它的失败模式。</li></ul></div>
    <div class="panel"><h4>坏消息</h4><ul>
      <li>对齐里最难的部分（"这个 AI 真正想要什么""结果对人类好不好"）写不成 Lean。可验证领域飞速进步、不可验证领域落后，这个差距本身是风险。</li>
      <li>AI 研发里可验证的部分（kernel 优化、证明、benchmark）会最先被大规模自动化——"AI 改进 AI"的循环最可能从这里开始。</li></ul></div>
  </div>
  <h3>17.5 治理：单方面倾倒的先例</h3>
  <p>社区已经通过 IAS 顾问组形成了初步规范（披露模型名、prompt、推理链、计算时间与成本、选题方式、同类问题失败率），OpenAI 只遵守了一部分，然后一次性发布 700 多篇。AHM 的说法 "a demonstration of power" 虽然激烈，但点到了结构性问题：<strong>前沿公司单方面决定一项能力以什么方式进入公共领域，受影响的共同体只能事后反应</strong>。</p>
</section>

{{PART2:18}}
{{PART2:19}}
{{PART2:20}}
{{PART2:21}}
{{PART2:22}}
{{PART2:23}}
{{PART2:24}}

<section id="reactions">
  <div class="kicker">Reactions · 原话</div>
  <h2><span class="n">25.</span>各方怎么说</h2>
  <div class="tbl"><table>
    <thead><tr><th>谁</th><th>原话</th><th>来源</th></tr></thead>
    <tbody>
      <tr><td>Levent Alpöge（Anthropic）</td><td>"It's obviously the most significant moment in mathematical history."（随后补充：会有人被抢先的 "sad stories"）</td><td>X <span class="tg">[R]</span></td></tr>
      <tr><td>Terence Tao</td><td>"Problems are being solved autonomously by AI prompters who have no interest in the broader field itself"；提出 Math 1.0 → 2.0</td><td>Fortune <span class="tg">[R]</span></td></tr>
      <tr><td>Dan Litt（多伦多大学）</td><td>"My view is that this is great for mathematics"，但担心"AI 已解决数学"的观感劝退年轻人</td><td>Fortune <span class="tg">[R]</span></td></tr>
      <tr><td>Tristan Buckmaster（NYU）</td><td>"There's likely to be a bunch of results where they take someone's work and then take it to completion"</td><td>Fortune <span class="tg">[R]</span></td></tr>
      <tr><td>Scott Aaronson</td><td>博文 "The Mathocalypse"；对 L = BPL："its truth was never in serious doubt"</td><td><a href="https://scottaaronson.blog/?p=10169">blog</a> <span class="tg">[R]</span></td></tr>
      <tr><td>Lance Fortnow</td><td>"if they hold up, we've seen more progress in TCS in the last 24 hours than in the previous three decades combined"</td><td>Computational Complexity blog <span class="tg">[R]</span></td></tr>
      <tr><td>Mark Braverman</td><td>"Math by press release is not that healthy for math."</td><td>Quanta <span class="tg">[R]</span></td></tr>
      <tr><td>François Chollet</td><td>追问：RLVR 友好领域的增益能否泛化，还是不可验证领域仍卡在人类数据上</td><td>X（转述）<span class="tg">[R]</span></td></tr>
      <tr><td>AHM</td><td>"Releasing over 700 files at once is not a demonstration of scholarship, but a demonstration of power."；呼吁数学家停止与 OpenAI 合作</td><td><a href="https://terrytao.wordpress.com/2026/10/07/ahm-statement-on-openais-october-6-release-of-mathematical-documents/">Tao 博客转载</a>（Tao 注明不背书）<span class="tg">[P]</span></td></tr>
      <tr><td>Álvaro Lozano-Robledo</td><td>"Keep calm and carry on studying math."；LLM "may work within the confines of the convex hull of ideas that are currently available in the literature"</td><td><a href="https://terrytao.wordpress.com/2026/10/08/what-should-we-tell-our-students/">Tao 博客客座文</a> <span class="tg">[P]</span></td></tr>
      <tr><td>Andrew Sutherland（MIT）</td><td>"We should ask for receipts."</td><td>SciAm 转载 <span class="tg">[R]</span></td></tr>
    </tbody>
  </table></div>
  <p class="tg">注：10-05 Tao 博客上的 "The Future of Mathematics" 是 Jeremy Avigad 的客座文，不是 Tao 本人所写；部分报道混淆了这一点。</p>
</section>

<section id="learn">
  <div class="kicker">Next steps</div>
  <h2><span class="n">26.</span>开放问题与继续学习</h2>
  <h3>26.1 接下来值得盯的</h3>
  <ol>
    <li>OpenAI 会公开 4,000 题清单与失败案例吗？（决定能否回答"真实能力是多少"）</li>
    <li>未形式化的约 58% 里还有多少像 Weil 类论文那样的错误？撤稿率会怎么演化？</li>
    <li>谁来审 Lean 陈述的忠实性？<code>review: unchecked</code> 什么时候改变？<code>lana-agents</code> 依赖和大补丁由谁审？</li>
    <li>第一个人类领域专家对头条结果（准黎曼、UGC、Thompson F）给出"读完并确认"的独立结论会是什么时候？</li>
    <li>"补完他人工作"的优先权规范怎么建立（Buckmaster 事件）？</li>
    <li>平面色数：需要 6 色的有限单位距离图长什么样？</li>
  </ol>
  <h3>26.2 学习路线（只需线性代数 + 微积分起步）</h3>
  <div class="tbl"><table>
    <thead><tr><th>阶段</th><th>材料</th><th>为什么</th></tr></thead>
    <tbody>
      <tr><td>1 · 数学是什么</td><td>Gowers《Mathematics: A Very Short Introduction》（中译《牛津通识读本：数学》）</td><td>Fields 奖得主写的 150 页入门：抽象、证明、什么叫难</td></tr>
      <tr><td>1 · 这场争论的源头</td><td>Thurston <a href="https://arxiv.org/abs/math/9404236">On Proof and Progress in Mathematics</a>；Gowers <a href="https://www.dpmms.cam.ac.uk/~wtg10/2cultures.pdf">The Two Cultures of Mathematics</a>；Tao <a href="https://arxiv.org/abs/math/0702396">What is good mathematics?</a></td><td>读完就完全明白 "Math 1.0 → 2.0" 在吵什么</td></tr>
      <tr><td>2 · 亲手摸证明</td><td>Natural Number Game（Kevin Buzzard，在线免费）</td><td>在 Lean 里从零证明加法交换律——之后你就真正理解 §3 的一切</td></tr>
      <tr><td>2 · 系统学证明</td><td>MIT 6.042 Mathematics for Computer Science（OCW + 免费教材）</td><td>为 CS 背景设计：证明方法、离散数学、概率</td></tr>
      <tr><td>3 · 直觉</td><td>3Blue1Brown：《线性代数的本质》、黎曼 ζ 函数可视化</td><td>§4 的图就是那一集的静态版</td></tr>
      <tr><td>3 · 跟新闻</td><td>Quanta Magazine 数学版；Princeton Companion to Mathematics（当工具书查词条）</td><td>每篇都解释"为什么难、前人卡在哪"</td></tr>
      <tr><td>4 · 与 ML 相关</td><td>Bubeck <a href="https://arxiv.org/abs/1405.4980">Convex Optimization: Algorithms and Complexity</a>；Prince《Understanding Deep Learning》（免费）</td><td>优化收敛证明、深度学习理论入门</td></tr>
    </tbody>
  </table></div>
</section>

<section id="sources">
  <div class="kicker">Glossary & sources</div>
  <h2><span class="n">27.</span>术语表与来源</h2>
  <h3>27.1 术语</h3>
  <div class="tbl"><table>
    <thead><tr><th>术语</th><th>一句话</th></tr></thead>
    <tbody>
      <tr><td class="mono">Lean / Mathlib</td><td>证明助手 / 它的社区数学库</td></tr>
      <tr><td class="mono">sorry / axiom</td><td>Lean 里"这步先空着" / "这条直接假设为真"——都会削弱证明</td></tr>
      <tr><td class="mono">Comparator</td><td>检查"解答证明的定理 = 挑战文件里的陈述，且只用允许公理"的工具</td></tr>
      <tr><td class="mono">无零区</td><td>ζ 或 L 函数在其中没有零点的区域</td></tr>
      <tr><td class="mono">无理性指数 μ</td><td>一个数能被分数"超常好"逼近的程度</td></tr>
      <tr><td class="mono">ω</td><td>矩阵乘法的最优指数，2 ≤ ω ≤ 3</td></tr>
      <tr><td class="mono">近似比</td><td>多项式时间算法保证拿到的"最优值的比例"</td></tr>
      <tr><td class="mono">L / RL / BPL</td><td>对数空间的确定性 / 单边随机 / 双边随机计算</td></tr>
      <tr><td class="mono">可顺从 amenable</td><td>群上存在平移不变的"平均"</td></tr>
      <tr><td class="mono">爆破 blowup</td><td>光滑方程的解在有限时间内趋于无穷</td></tr>
      <tr><td class="mono">复本对称破缺 RSB</td><td>Parisi 描述自旋玻璃层级态结构的方法</td></tr>
      <tr><td class="mono">银河算法</td><td>渐近更快、但只在天文规模上才占优的算法</td></tr>
    </tbody>
  </table></div>
  <h3>27.2 主要来源</h3>
  <p><strong>一手</strong>：<a href="''' + REPO + '''">openai/math</a>（README、history.md、overview.pdf、CONTENTS.md、lean/、preprints/、reasoning_traces/；快照 fd4aeeb，2026-10-08）· <a href="https://github.com/openai/NavierStokesAndEuler">openai/NavierStokesAndEuler</a> · <a href="https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf">Clay NS 官方陈述（Fefferman）</a> · <a href="https://github.com/leanprover/comparator">leanprover/comparator</a> · 独立复核 <a href="https://github.com/davegoldblatt/openai-zeta-proof-check">davegoldblatt/openai-zeta-proof-check</a>、<a href="https://github.com/erenciracioglu-dotcom/openai-math-9-4-lean-check">erenciracioglu-dotcom/openai-math-9-4-lean-check</a> · Epoch <a href="https://arxiv.org/abs/2609.25050">FrontierMath Erdős（arXiv:2609.25050）</a>。</p>
  <p><strong>报道与评论</strong>：<a href="https://fortune.com/2026/10/07/openai-math-controversy-solutions-370-outstanding-challenges-published-criticisms-celebration/">Fortune 10-07</a> · <a href="https://www.nature.com/articles/d41586-026-03196-8">Nature</a>（付费墙，未读全文 ⚠）· <a href="https://www.scientificamerican.com/article/openai-unleashes-hundreds-more-math-results-upon-a-field-already-in-shock/">Scientific American</a> · <a href="https://www.quantamagazine.org/ai-has-solved-one-of-maths-1-million-millennium-prize-problems-20260908/">Quanta 09-08</a> · <a href="https://www.quantamagazine.org/as-ai-closed-in-on-unique-games-proof-researchers-raced-to-beat-the-machines-20261007/">Quanta 10-07</a> · <a href="https://www.npr.org/2026/09/22/nx-s1-5968588/openai-navier-stokes-problem-mathematicians-learn-little">NPR 09-22</a> · <a href="https://scottaaronson.blog/?p=10169">Aaronson</a> · <a href="https://gilkalai.wordpress.com/2026/10/07/updates-sharing-ai-progress-on-mathematics-amazing-and-my-lecture-plans/">Kalai</a> · <a href="https://terrytao.wordpress.com/">Tao 博客</a> · <a href="https://www.latent.space/p/ainews-quasi-riemann-hypothesis-openai">Latent Space</a>。</p>
  <p><strong>经典文献</strong>：Strassen 1969；Coppersmith–Winograd 1990；Alman 等 <a href="https://arxiv.org/abs/2404.16349">arXiv:2404.16349</a>；Ambainis–Filmus–Le Gall <a href="https://arxiv.org/abs/1411.5414">arXiv:1411.5414</a>；Goemans–Williamson 1995；Khot 2002；KKMO 2007；Raghavendra 2008；Khot–Minzer–Safra 2018；Nisan 1992；Saks–Zhou 1999；Reingold 2008；Roth 1955；Zeilberger–Zudilin <a href="https://arxiv.org/abs/1912.06345">arXiv:1912.06345</a>；Meiburg <a href="https://arxiv.org/abs/2208.13356">arXiv:2208.13356</a>；Guth–Maynard <a href="https://arxiv.org/abs/2405.20552">arXiv:2405.20552</a>；de Grey <a href="https://arxiv.org/abs/1804.02385">arXiv:1804.02385</a>；Moore <a href="https://arxiv.org/abs/1102.0747">arXiv:1102.0747</a>；Tao 2016 <a href="https://arxiv.org/abs/1402.0290">arXiv:1402.0290</a>；Glassey–Strauss 1986；Parisi 1979；Talagrand 2006；Mézard–Parisi 2001；Ding–Sly–Sun 2015。</p>
  <p class="tg">研究底稿（含每条的 [P]/[R]/⚠ 标注、Lean grep 细节和未进 deck 的材料）保存在作者的研究笔记中，未随本 deck 公开。</p>
</section>
'''

FIGS = {
    "{{FIG_FIELDS}}": figs.svg_fields(), "{{FIG_TRUST}}": figs.svg_trust(), "{{FIG_ZETA}}": figs.svg_zeta(),
    "{{FIG_FLINT}}": figs.svg_flint(), "{{FIG_OMEGA}}": figs.svg_omega(), "{{FIG_MAXCUT}}": figs.svg_maxcut(),
    "{{FIG_MOSER}}": figs.svg_moser(), "{{FIG_THOMPSON}}": figs.svg_thompson(), "{{FIG_BLOWUP}}": figs.svg_blowup(),
    "{{FIG_HARMONIC}}": figs.svg_harmonic(), "{{FIG_SPIN}}": figs.svg_spin(), "{{FIG_HODGE}}": figs.svg_hodge(),
    "{{FIG_METR}}": figs.svg_metr(figs.METR_ZH), "{{FIG_OPEN}}": figs.svg_openprob(figs.OPEN_ZH),
}
import md2html

JJ_DIR = ROOT / "精讲"


RESULT_KICKERS = {
    "qrh": "数论 · family 003",
    "pi": "数论 · family 017（+ 005）",
    "matmul": "理论计算机 · family 107",
    "ugc": "理论计算机 · family 102",
    "bpl": "理论计算机 · family 103（+ 109）",
    "color": "组合 · family 158（+ 156）",
    "thompson": "群论 · family 248",
    "ns": "偏微分方程 · 9 月单独发布（+ family 376）",
    "vlasov": "数学物理 · family 362",
    "spin": "概率与统计力学 · family 221",
    "kakeya": "调和分析 · family 074（+ 077）",
}
RESULT_ORDER = ['qrh', 'pi', 'matmul', 'ugc', 'bpl', 'color', 'thompson', 'ns', 'vlasov', 'spin', 'kakeya']


def result_html(sid):
    """One result section (§4–§14), rendered from its chapter Markdown file."""
    k = RESULT_ORDER.index(sid) + 1
    files = sorted(JJ_DIR.glob(f"{k:02d}_*.md"))
    assert len(files) == 1, f"result {sid}: expected exactly one chapter file, got {files}"
    md = files[0].read_text()
    first, _, rest = md.partition("\n")
    assert first.startswith("# "), files[0]
    return f'''<section id="{sid}" class="jj">
  <div class="kicker">{RESULT_KICKERS[sid]}</div>
  <h2><span class="n">{3 + k}.</span>{md2html.inline(first[2:].strip())}</h2>
{md2html.blocks(rest, heading_offset=1)}
</section>'''


for _sid in RESULT_ORDER:
    BODY = BODY.replace("{{RESULT:%s}}" % _sid, result_html(_sid))

P2_DIR = ROOT / "前瞻"
P2_SECTIONS = [('fwd-calib', 18), ('fwd-cs', 19), ('fwd-phys', 20), ('fwd-bio', 21), ('fwd-ai', 22), ('fwd-soc', 23), ('fwd-synth', 24)]
P2_KICKERS = {18: 'Part II · 前瞻 · 校准', 19: 'Part II · 前瞻 · 计算机', 20: 'Part II · 前瞻 · 物理', 21: 'Part II · 前瞻 · 生物', 22: 'Part II · 前瞻 · AI 本身', 23: 'Part II · 前瞻 · 社会', 24: 'Part II · 前瞻 · 全景'}


def part2_html(sec_id, n):
    """One Part II section, rendered from 前瞻/NN_*.md."""
    files = sorted(P2_DIR.glob(f"{n}_*.md"))
    assert len(files) == 1, f"Part II §{n}: expected exactly one file, got {files}"
    md = files[0].read_text()
    first, _, rest = md.partition("\n")
    assert first.startswith("# "), files[0]
    return f'''<section id="{sec_id}" class="jj">
  <div class="kicker">{P2_KICKERS[n]}</div>
  <h2><span class="n">{n}.</span>{md2html.inline(first[2:].strip())}</h2>
{md2html.blocks(rest, heading_offset=1)}
</section>'''


for _sec_id, _n in P2_SECTIONS:
    BODY = BODY.replace("{{PART2:%d}}" % _n, part2_html(_sec_id, _n))
import re as _re
while _re.search(r'\^\{([^{}]*)\}', BODY):
    BODY = _re.sub(r'\^\{([^{}]*)\}', r'^(\1)', BODY)
for k, v in FIGS.items():
    assert k in BODY, k
    BODY = BODY.replace(k, v)

toc_html = "\n".join(f'  <a href="#{i}"><span class="num">{n}</span>{t}</a>' for i, n, t in TOC)

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>OpenAI 数学发布 · 从零读懂</title>
<style>
""" + CSS + EXTRA_CSS + """
</style>
</head>
<body>
<div class="page">
<nav class="toc">
""" + toc_html + """
</nav>
<main>
""" + BODY + """
</main>
</div>
<script>
(() => {
  const links = [...document.querySelectorAll('nav.toc a')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const id = '#' + e.target.id;
      links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === id));
    });
  }, { rootMargin: '-40% 0px -50% 0px', threshold: 0 });
  sections.forEach(s => io.observe(s));
})();
</script>
</body>
</html>
"""

out = ROOT / "notes.html"
out.write_text(HTML)
print(f"wrote {out} ({len(HTML)} bytes)")
