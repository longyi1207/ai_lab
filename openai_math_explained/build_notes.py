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
    ("vlasov", "12", "等离子体"), ("spin", "13", "自旋玻璃"), ("hodge", "14", "撤稿案例"),
    ("synthesis", "15", "横向看"), ("ai", "16", "对 AI 意味着"), ("reactions", "17", "反应"),
    ("learn", "18", "开放问题/继续学"), ("sources", "19", "术语/来源"),
]

BODY = r'''
<header class="masthead">
  <div class="kicker">学习 deck · 给非数学背景的 AI 研究者</div>
  <h1>OpenAI 的 719 篇 AI 数学论文：从零读懂它们在说什么</h1>
  <p>2026-10-06，OpenAI 一次性公开了一个未发布内部模型生成的 <strong>722 篇数学手稿（372 个结果族）</strong>，其中声称解决了准黎曼猜想、Unique Games 猜想、矩阵乘法指数 ω ≤ 9/4、Thompson 群不可顺从、平面不能 5 着色等一批几十年的名题；第二天因一个符号错误撤回 3 篇。数学界称之为 "Mathocalypse"。这份 deck 的目标：<strong>只用线性代数 + 微积分 + 高中数学</strong>，把其中 10 个代表性结果各自讲到"能判断它有多大、多难、为什么重要、核实到哪一步"。</p>
  <p class="meta">2026-10-08 首版 · repo 快照 openai/math@fd4aeeb（含 10-07 撤稿与修补）· 每条事实标来源；[P] = 读过一手材料（论文/repo/Lean 源码），[R] = 二手报道，⚠ = 未核实或有冲突 · 研究底稿见 deep_reads/</p>
</header>

<section id="scope">
  <div class="kicker">Orientation</div>
  <h2><span class="n">0.</span>这份 deck 能带你到哪，到不了哪</h2>
  <div class="note">
    <span class="label">读完能得到</span>
    <p>对 10 个头条结果各有一个"阶梯式"理解：从一个你能手算的玩具例子出发，一级一级走到真正的命题；知道这个问题此前卡了多少年、卡在哪；知道 OpenAI 具体声称了什么、Lean 形式化覆盖到哪、人类专家目前怎么说；以及它对数学、对 AI、对 AI safety 各意味着什么。</p>
  </div>
  <div class="note bug">
    <span class="label">读完得不到</span>
    <p>判断任何一个证明是否正确的能力。这 10 个结果里，截至 10-08 <strong>没有一个</strong>有人类领域专家公开表示"我读完并确认了"。本 deck 里的"核实"只到两层：① 我们静态审查了 Lean 源码与陈述；② 汇总了公开反应。都标注了来源和可信度。</p>
  </div>
  <h3>0.1 阅读路径</h3>
  <p>§1 先补三样基础（数学家在做什么、什么叫"开放问题"、怎么判断一个结果有多大）。§2–§3 是事件本身和"Lean 到底保证了什么"——<strong>这两节决定你该怎么读后面所有的"声称"</strong>。§4–§14 是 10 个结果，每节结构相同：<em>阶梯 → 问题 → 为什么难 → OpenAI 声称 → 核实状态 → 如果为真</em>，可以按兴趣跳读。§15–§16 是横向总结和对 AI 的含义，§17 是各方反应，§18 是开放问题和继续学习的路线，§19 是术语表与来源。</p>
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
      <tr><td>14</td><td>Hodge 相关撤稿（032 等）</td><td>—</td><td>无</td><td>一个符号错误撤掉 3 篇：未形式化的风险</td></tr>
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
    <li><strong>题目是谁选的、失败了多少？</strong> 这是本次事件最容易被忽略的一问，见 §2.3 和 §15。</li>
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
  <p><strong>例外</strong>：README 承认 ζ 零点无零区（§4）和 CM 阿贝尔簇的 Hodge 猜想（§14）<em>不是</em>走这个固定流程产出的，并且 Re s &gt; 11/12 那份写作经过人工编辑。具体例外是什么（更多算力？人工引导？）没有披露 ⚠。</p>
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

<section id="qrh">
  <div class="kicker">数论 · family 003</div>
  <h2><span class="n">4.</span>准黎曼猜想：素数分布的"噪声上限"</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body">手数素数：100 以内 25 个，1000 以内 168 个，10⁶ 以内 78,498 个。记 π(x) = "≤ x 的素数个数"。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>素数定理</strong>：π(x) ≈ Li(x) = ∫₂ˣ dt/ln t。Li(10⁶) ≈ 78,626.5 vs 真实 78,498——比值趋于 1（1896 年证明）。真正的问题是<strong>误差 π(x) − Li(x) 有多大</strong>。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>ζ 函数编码了所有素数</strong>：ζ(s) = Σ 1/nˢ = ∏ₚ 1/(1−p⁻ˢ)。等式成立是因为每个整数唯一分解成素数之积。手算 s = 2：只取 p = 2,3,5 得 1.5625；取 100 以内全部素数得 1.6419；真值 π²/6 ≈ 1.6449。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body">把 s 推广到复数 s = σ + it，<strong>零点</strong>就是 ζ(s) = 0 的点。非平凡零点都在"临界带" 0 &lt; Re s &lt; 1 里，前三个在 ½ + 14.13i、½ + 21.02i、½ + 25.01i。<strong>黎曼猜想（1859）</strong>：全部在 Re s = ½ 上。</div></div>
    <div class="rung"><div class="lvl">第 4 级</div><div class="body"><strong>零点为什么控制误差</strong>：显式公式里每个零点 ρ = β + iγ 贡献一项大小约 x^β 的"振荡噪声"。所有零点 Re ≤ θ ⇒ 误差约 x^θ。黎曼猜想 ⇔ 误差约 √x。可以把零点想成素数分布的"频谱"，β 决定这个频率的振幅随 x 涨得多快。</div></div>
    <div class="rung"><div class="lvl">第 5 级</div><div class="body"><strong>此前已知的无零区</strong>：de la Vallée Poussin（1899）σ &gt; 1 − c/log t；Vinogradov–Korobov（1958）稍宽一些。<strong>关键：它们的宽度都随高度 t → ∞ 缩向 0</strong>。从来没人证明过存在一个<em>固定</em>的 δ &gt; 0，使 Re s &gt; 1 − δ 整个竖带没有零点。</div></div>
  </div>
  {{FIG_ZETA}}
  <h3>4.1 问题是什么</h3>
  <p><strong>准黎曼猜想</strong>：存在一条固定竖线 Re s = θ &lt; 1，右边没有任何零点。它是黎曼猜想（θ = ½）的弱版，但在 2026 年之前同样完全够不着。</p>
  <h3>4.2 为什么难</h3>
  <p>经典方法都从欧拉乘积在 σ &gt; 1 的正性出发（比如 3 + 4cos θ + cos 2θ ≥ 0 这个技巧），而这种正性越往高处越弱，所以得到的区域必然越来越窄。另一条路线"零点密度估计"（如 Guth–Maynard 2024，<a href="https://arxiv.org/abs/2405.20552">arXiv:2405.20552</a>）只能说"Re s &gt; σ 的零点很少"，不能说"一个都没有"。拿到固定宽度需要全新的机制。</p>
  <h3>4.3 OpenAI 声称了什么</h3>
  <div class="claim"><span class="label">声称 [P]</span>
    <p><a href="''' + REPO + '''/blob/main/preprints/The-Quasi-Riemann-Hypothesis-September-30-2026/paper.pdf">主论文</a>（2026-09-30，199 页）："We prove that all finite-order Hecke L-functions over Q(√−3) and all Dirichlet L-functions are zero-free in the half-plane ℜs &gt; 7/8 … In particular, the Riemann zeta function is zero-free in this half-plane." 论文自己强调："The Riemann hypothesis remains open."</p>
    <p>同族还有：一份 11/12 的另一个证明（49 页，人工辅助写作）；一份 9 页的"一致排除 Landau–Siegel 零点"。</p>
  </div>
  <p><strong>方法速写</strong>（只读了引言）：绕到 ℚ(√−3) 上，用三次 theta 级数的 Fourier 系数构造一个"完成和"，它有两种算法（反射公式 / Poisson 求和）；若存在零点 β &gt; 7/8，两种估计矛盾。最后利用 L_F(s, χ∘N) = L(s,χ)·L(s,χχ₋₃) 把结论转到所有 Dirichlet L 函数。</p>
  <h3>4.4 核实状态</h3>
  <div class="verdict">
    <div class="panel"><h4>机器</h4><ul>
      <li>Lean 挑战陈述只用 Mathlib 标准定义，例如 <code>theorem riemannZeta_ne_zero_of_seven_eighths_lt_re {s : ℂ} (hs : 7/8 &lt; s.re) : riemannZeta s ≠ 0</code>。<span class="tg">[P]</span></li>
      <li>解答约 2,926 个文件、48.7 万行，sorry/axiom/native_decide 均为 0。<span class="tg">[P]</span></li>
      <li>独立复核：Goldblatt 用两个内核跑通，<code>#print axioms</code> 只有三条标准公理。<span class="tg">[P]</span></li>
      <li>⚠ 依赖补丁 PrimeNumberTheoremAnd-lean4341.patch 约 4 万行，其中删掉了上游的 2 个 sorry 并补上证明——"依赖库"有一部分是 OpenAI 自己的代码。</li>
      <li>论文后续的应用（第 6 节推论）不在形式化范围内。</li></ul></div>
    <div class="panel"><h4>人</h4><ul>
      <li>Alex Kontorovich（Rutgers，PrimeNumberTheoremAnd 形式化项目发起人）："Quasi-RH?!?!???! Are you kidding me? If a human did this, it would be an instant Fields Medal…" <span class="tg">[R]</span></li>
      <li>Levent Alpöge："Big, big, big, big props for quasiriemann and no Siegel zeroes." <span class="tg">[R]</span></li>
      <li>截至 10-08，<strong>没有任何人类专家公开表示读完了这 199 页</strong>。⚠</li></ul></div>
  </div>
  <p><strong>判断</strong>：只要 Mathlib 对 <code>riemannZeta</code> 的定义正确、Lean 内核没 bug，这个定理就是"机器意义上已证明"——可信度比"一篇没人审过的论文"高一个量级。剩余风险在构建链（补丁和依赖）。</p>
  <h3>4.5 如果为真</h3>
  <ul>
    <li><strong>素数定理误差变成幂次节约</strong>：π(x) − Li(x) = O(x^{7/8} log²x)。从"宽度缩向 0"到"固定宽度"是质变；但 7/8 到 ½ 仍是整块未知。</li>
    <li><strong>Siegel 零点被排除</strong>：1935 年以来困扰一批"常数能否有效计算"问题的障碍解除（例如虚二次域类数的有效下界）。</li>
    <li><strong>算法推论</strong>（论文 Cor. 1.2）：最小二次非剩余 ≤ C(log p)^32 ⇒ 模 p 开平方、Miller 素性测试都变成<em>无条件</em>的确定性多项式时间算法。对实际密码学<strong>没有影响</strong>（实践中一直用随机算法，AKS 2002 早已给出无条件确定性素性测试；RSA、椭圆曲线的安全性不受影响）。</li>
  </ul>
</section>

<section id="pi">
  <div class="kicker">数论 · family 017（+ 005）</div>
  <h2><span class="n">5.</span>π 能被分数逼近得多好</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body">22/7 与 π 差 1.26×10⁻³；355/113（祖冲之"密率"）只差 2.67×10⁻⁷。对比基准 1/q²：1/113² ≈ 7.8×10⁻⁵——355/113 比它好了近 300 倍。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>连分数</strong>：π = [3; 7, 15, 1, 292, 1, 1, …]。下一项越大，前一个截断就越"超常地好"。355/113 后面紧跟 292，所以它特别准。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>Dirichlet（1842）</strong>：任何无理数都有无穷多个 p/q 满足 |x − p/q| &lt; 1/q²（抽屉原理）。所以"指数 2"总能达到。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>无理性指数</strong> μ(x) = 能让 |x − p/q| &lt; q^{−ν} 有无穷多解的最大 ν。有理数 1；Liouville 数 ∞；<strong>代数无理数（如 √2）恰好是 2</strong>——这是 Roth 定理（1955），获 1958 年 Fields 奖；e 是 2；几乎所有实数都是 2。难的是对<em>一个具体的数</em>证明。</div></div>
    <div class="rung"><div class="lvl">第 4 级</div><div class="body"><strong>π 的上界史</strong>：Mahler 1953 年 42 → Mignotte 1974 年 20 → Hata 1993 年 8.016 → Salikhov 2008 年 7.606 → Zeilberger–Zudilin 2020 年 7.103。70 年从 42 降到 7.1，离 2 还很远。</div></div>
  </div>
  {{FIG_FLINT}}
  <h3>5.1 OpenAI 声称了什么</h3>
  <div class="claim"><span class="label">声称 [P]</span>
    <p><a href="''' + REPO + '''/blob/main/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/paper.pdf">The irrationality exponent of π is 2</a>（2026-09-24，23 页）："We prove the conjecture that the irrationality exponent of π is 2. As a consequence, the classical Flint–Hills series Σ 1/(n³ sin²n) converges."</p>
    <p>精确版：对每个 ν &gt; 2，存在 Q(ν)，使一切 q ≥ Q(ν) 都有 |π − p/q| ≥ q^{−ν}。论文自己说明 Q(ν) <em>不可有效计算</em>，且 μ = 2 ≠ "连分数部分商有界"（后者更强，仍未解决）。</p>
  </div>
  <p><strong>方法</strong>：假设有无穷多个指数 ν &gt; 2 的逼近，挑出几个分母尺度彼此分离的，沿对数曲线做多变量插值得到一个非零行列式：算术上它是非零整数（≥ 1），解析上它被逼近误差压得极小，矛盾。Flint Hills 收敛则由已有的人类结果（Meiburg 2022：μ(π) &lt; 5/2 ⇒ 收敛）推出。</p>
  <p><strong>推理摘要</strong>（<a href="''' + REPO + '''/blob/main/reasoning_traces/irrationality-exponent-of-pi.pdf">42 页</a>）很值得读：模型一开始的目标只是 μ &lt; 5/2，试了 BBP、模形式、Padé、p-adic 等几十条路线，反复撞上"高度 vs 分母成本"这堵墙，最后用加权插值行列式先拿到 μ = 62/25 = 2.48，再推到 2。它还借用了自己的 Catalan 常数手稿里的行列式思路。</p>
  <h3>5.2 核实状态</h3>
  <p>Lean：<code>lean/docs/017.md</code> 与 <code>ComparatorChallenges/PiExponent</code> 存在，解答约 869 个文件、9.5 万行，grep 无 sorry/axiom <span class="tg">[P]</span>；但它<strong>没有登记在 formalization.yaml 里</strong> ⚠，也没有第三方复核。Flint Hills 推论不在形式化范围内。没有找到数论专家对这篇论文的具体评论 ⚠。</p>
  <div class="note">
    <span class="label">侧栏：Catalan 常数是无理数（family 005）</span>
    <p>G = 1 − 1/3² + 1/5² − 1/7² + … ≈ 0.91597。1978 年 Apéry 证明 ζ(3) 无理（van der Poorten 称之为 "A proof that Euler missed"），但同样的思路对 G 失效：清分母后线性形式不趋于 0。此前最好的只是"β(2), β(4), …, β(10) 中至少一个无理"。OpenAI 声称 G 无理（44 页），有 Lean（约 57 万行，同样未登记在 yaml 里 ⚠）。如果成立，这是 Apéry 之后近半个世纪里"单个经典常数无理性"最重要的结果之一。</p>
  </div>
  <h3>5.3 如果为真</h3>
  <p>对 π 这个具体常数第一次拿到"和几乎所有实数一样"的最优指数，70 年的上界竞赛结束；一个流行二十多年的 Flint Hills 谜题得解。实际应用几乎没有，价值在纯数学，以及"加权插值行列式"能否推广到 ζ(3)、log 2 等常数。</p>
</section>

<section id="matmul">
  <div class="kicker">理论计算机 · family 107</div>
  <h2><span class="n">6.</span>矩阵乘法到底能多快：ω ≤ 9/4</h2>
  <p>你天天在用的 GPU 训练，本质上是在做矩阵乘法。这一节回答：理论上它最快能多快。</p>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body">教科书算法：c_ij = Σ_k a_ik·b_kj，n² 个元素 × 每个 n 次乘法 = <strong>n³</strong>。2×2 需要 8 次乘法。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>Strassen 1969：2×2 只要 7 次乘法</strong>（见下方代码块，可手算验证）。关键是这个算法对 a…h 是什么不做假设，所以它们可以是矩阵块，于是能递归：T(n) = 7T(n/2) ⇒ n^{log₂7} ≈ <strong>n^2.807</strong>。省下的 1 次乘法在每层递归里复利放大。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>ω 的定义</strong>：能用约 n^ω 次运算完成 n×n 矩阵乘法的最小指数。显然 2 ≤ ω ≤ 3（下界 2：光读入 2n² 个数就要这么多步）。主流猜想 ω = 2。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body">"2×2 能用 7 次乘法"等价于"2×2 矩阵乘法<strong>张量的秩</strong> ≤ 7"。此后：Bini 1979 近似秩 → Schönhage 1981 → Strassen 1986 <strong>激光法</strong>（从一个低秩张量的高次幂里切出大量独立的矩阵乘法）。近 40 年的进展几乎全来自激光法的改进。</div></div>
  </div>
<pre><code>A = [[a,b],[c,d]]   B = [[e,f],[g,h]]
M1=(a+d)(e+h)  M2=(c+d)e  M3=a(f−h)  M4=d(g−e)
M5=(a+b)h      M6=(c−a)(e+f)          M7=(b−d)(g+h)
C11=M1+M4−M5+M7   C12=M3+M5   C21=M2+M4   C22=M1−M2+M3+M6
<span class="cm"># 验算 C12：M3+M5 = af−ah+ah+bh = af+bh ✓</span></code></pre>
  {{FIG_OMEGA}}
  <h3>6.1 OpenAI 声称了什么</h3>
  <div class="claim"><span class="label">声称 [P]</span>
    <p><strong>An Upper Bound of 9/4 for the Matrix Multiplication Exponent</strong>（2026-10-02，<strong>只有 13 页</strong>）："We prove that the exponent of matrix multiplication over the complex numbers is at most 9/4." 方法不是激光法，而是 Strassen 的<strong>渐近谱</strong>路线：对多项式乘法张量上的"张量特征"推出不等式，最后得到 ω ≤ 9/4。论文自己说："its proof does not specify a competitive finite matrix size."</p>
    <p>同族另两篇：ℂ 上 ω &lt; 2.258（83 页）；<em>任意域</em>（含正特征）上 ω &lt; 2.371054886（35 页，仍是激光法框架，比此前纪录多改进约 1.2×10⁻⁴）。</p>
  </div>
  <h3>6.2 核实状态</h3>
  <p><strong>陈述审查</strong> <span class="tg">[P]</span>：Lean 定理 <code>Arithmetic.omega ℂ ≤ 9/4</code>。算法被建模为直线程序（常数/输入/+/−/× 门，各计成本 1），<code>Correct</code> 要求对<em>所有</em>输入矩阵输出 A·B，ω 定义为标准的非一致代数复杂度——与文献一致，无隐藏假设。解答目录 sorry/axiom 为 0。<strong>人</strong>：Aaronson："a <em>rational</em> exponent for once (!), and via a completely different approach" <span class="tg">[R]</span>；激光法领域专家（Vassilevska Williams、Alman、Le Gall）未见公开表态 ⚠。</p>
  <h3>6.3 如果为真——以及它对 AI 训练意味着什么</h3>
  <ul>
    <li><strong>理论上</strong>：解线性方程组、矩阵求逆、行列式、传递闭包、二分图匹配、线性规划求解器等一大批算法的复杂度直接写成 ω 的函数，会同时下降。更重要的是证明"渐近谱"这条路走得通，ω = 2 似乎更近了。</li>
    <li><strong>对 GPU / LLM 训练：几乎没有直接影响。</strong>这是典型的"银河算法"（galactic algorithm）：常数巨大，只在天文数字规模的矩阵上才占优。GPU 上的 GEMM 用的就是 n³ 分块算法，瓶颈在显存带宽和 Tensor Core 吞吐；连 Strassen 在实践中都很少用（数值稳定性差、访存不规整）。</li>
    <li><strong>和 AlphaTensor / AlphaEvolve 的区别</strong>：它们找的是<em>固定小尺寸</em>的低秩分解（如 AlphaEvolve 2025 年的 4×4 复矩阵 48 次乘法），是可以落地到真实内核的常数级优化；ω 关心的是 n → ∞ 的<em>指数</em>。Dupont 等 2026-08 用 AlphaEvolve 优化激光法参数，第一次让 AI 碰到 ω，但只改进了 1.6×10⁻⁴。</li>
  </ul>
</section>

<section id="ugc">
  <div class="kicker">理论计算机 · family 102</div>
  <h2><span class="n">7.</span>Unique Games：近似算法的"天花板"在哪</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>NP 难</strong>：3SAT、Max-Cut 这类问题，大家相信没有多项式时间的精确算法（P ≠ NP）。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>退而求其次：近似</strong>。Max-Cut = 把图的顶点分两组，让跨组的边尽量多。随机分组期望切一半的边。手算三角形：最好切 2 条，随机期望切 1.5 条，比值 0.75。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>Goemans–Williamson（1995）</strong>：把每个顶点放松成单位向量，解一个半定规划（SDP），再用随机超平面切一刀，保证 <strong>0.878</strong>。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>近似也可能是难的</strong>：PCP 定理（1992–98）。Håstad（2001）证明 Max-Cut 近似到 16/17 ≈ 0.941 以上是 NP 难。于是 0.878 和 0.941 之间留下一个 25 年的缺口。</div></div>
    <div class="rung"><div class="lvl">第 4 级</div><div class="body"><strong>Unique Games</strong>：每个顶点从 q 个标签里选一个，每条边是一个置换约束（一端定了，另一端唯一确定）。手算：三角形、标签 {0,1,2}、约束 b=a+1, c=b+1, a=c+1（mod 3）——绕一圈 a=a+3=a，可全满足；把最后一条换成 a=c+2，最多满足 2/3。完全可满足的实例沿边传播就能多项式时间解，<strong>难的只是"几乎可满足"</strong>。</div></div>
  </div>
  <p><strong>UGC（Khot 2002）</strong>：对任意 ε, δ &gt; 0，区分"能满足 ≥ 1−ε"和"最多满足 ≤ δ"是 NP 难的。</p>
  {{FIG_MAXCUT}}
  <h3>7.1 为什么它这么重要</h3>
  <ul>
    <li><strong>KKMO 2007</strong>：若 UGC 成立，Max-Cut 的极限<em>恰好</em>是 0.878——GW 算法最优。</li>
    <li><strong>Khot–Regev 2008</strong>：若 UGC 成立，Vertex Cover 近似到 2−ε 是难的。</li>
    <li><strong>Raghavendra 2008</strong>：若 UGC 成立，对<em>所有</em>约束满足问题，基本 SDP 就是最优的多项式时间近似算法。一个算法 + 一个猜想决定了一整类问题的近似极限。</li>
    <li>反面证据：Arora–Barak–Steurer 2010 给出 UG 的亚指数时间算法，让一部分人怀疑 UGC。最近的进展是 2018 年的 <strong>2-to-2 定理</strong>（Khot–Minzer–Safra 等），证明了完备度约 1/2 的版本——"半个 UGC"。</li>
  </ul>
  <h3>7.2 OpenAI 声称了什么</h3>
  <div class="claim"><span class="label">声称 [P]</span>
    <p><strong>The Unique Games Theorem</strong>（2026-09-23，58 页）："We prove the Unique Games Conjecture. For every fixed ε, δ ∈ (0, 1/2), we give a deterministic polynomial-time reduction from 3SAT to Unique Games over a fixed finite alphabet, with completeness at least 1 − ε and soundness at most δ."</p>
    <p>同族另有 4 篇<em>不依赖 UGC</em>的直接归约：Max-Cut 超过 0.878 是 NP 难、Vertex Cover 低于 2 是 NP 难等——这就是 Aaronson 说"UGC 对它最有名的推论其实并不必要"的意思。</p>
  </div>
  <h3>7.3 核实状态</h3>
  <p><strong>陈述审查</strong> <span class="tg">[P]</span>：Lean 定理 <code>OAI.UniqueGamesTheorem.theorem11</code>。输入是 3SAT 公式的二进制编码，归约要求 <code>Turing.TM2ComputableInPolyTime</code>（Mathlib 的多带图灵机），完备性/可靠性条件写得清楚，并额外要求实例是"平移约束 + 简单二部图"——<strong>这是 UGC 的一个更强的、已知等价的形式，编码忠实</strong>。解答约 478 个文件、18.7 万行，sorry/axiom 为 0。</p>
  <p><strong>人</strong> <span class="tg">[R]</span>：Lance Fortnow："if they hold up, we've seen more progress in TCS in the last 24 hours than in the previous three decades combined." Mark Braverman（Quanta）："Math by press release is not that healthy for math." Dana Moshkovitz 称论文写得"不借助 AI 根本读不下去"（二手转述 ⚠）。Khot 本人未见公开表态 ⚠。</p>
  <h3>7.4 如果为真</h3>
  <p>"高效近似能做到多好"这个问题，对一大类问题画出了精确边界；原来写着"若 UGC 则……"的几百篇论文变成定理。和 AI safety 的一个联想（<em>我的推测，不是已有结论</em>）：辩论式可扩展监督（Irving–Christiano–Amodei 2018）的复杂性理论底子就是交互式证明与 PCP；UGC 精确刻画了"有一点点误差就无法高效区分"的边界，对"弱验证者监督强证明者"的协议设计有类比意义。</p>
</section>

<section id="bpl">
  <div class="kicker">理论计算机 · family 103（+ 109）</div>
  <h2><span class="n">8.</span>L = RL = BPL：小内存里，随机性没用</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>随机性能买到什么？</strong>判断 (x+y)² = x²+2xy+y² 是否恒成立：随机代入几个数检查就行，极快；但确定性的快速算法至今未知。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>P vs BPP</strong>：主流猜想 P = BPP（随机性不带来本质提升），但无条件证明遥不可及。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>换成内存受限版</strong>：L = 只用 O(log n) 比特内存（大约只能存几个指针）的确定性计算；RL/BPL = 同样内存 + 随机比特。手算例：无向图从 s 随机游走 n³ 步，只需记"当前位置 + 计数器"，高概率走到 t ⇒ 连通性 ∈ RL（1979）。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>去随机化史</strong>：Nisan 1992 BPL ⊆ L² → Saks–Zhou 1999 BPL ⊆ L^{3/2} → Hoza 2021 稍好 → <strong>Reingold 2005：无向连通性 ∈ L</strong>（拿掉一个具体问题的随机性的里程碑）。一般 BPL 在 3/2 次幂附近卡了 25 年。</div></div>
  </div>
  <div class="claim"><span class="label">声称 [P]</span>
    <p><strong>Exact Derandomization of Logarithmic Space: L = RL = BPL</strong>（2026-09-23，108 页）："We prove L = RL = BPL, resolving the derandomization problem for polynomial-time randomized logarithmic space." 更强版：能确定性地把接受概率估计到 2^{−q} 精度，空间 O(log n + q)。</p>
  </div>
  <p><strong>核实</strong> <span class="tg">[P]</span>：Lean 定理 <code>L = RL ∧ RL = BPL</code>；这一族的 Comparator 额外<strong>锁定了 20 个定义</strong>（机器、步进、空间、接受概率、L/RL/BPL），解答方不能偷改定义。模型是自定义多带图灵机，空间按访问过的工作格子数计，"所有硬币序列都在多项式时间内停机"——标准 BPL 定义。sorry/axiom 为 0。<strong>人</strong> <span class="tg">[R]</span>：Aaronson："one of the great derandomization conjectures short of P=BPP"，又说 "its truth was never in serious doubt"——结论本身没人怀疑，难在证明。</p>
  <p><strong>如果为真</strong>：第一个无条件"完全拿掉随机性"的自然资源类。它<strong>不</strong>蕴含 P = BPP，离 P vs NP 也很远（Fortnow："none of these results get us any closer to settling P v NP"）。证明里"低空间、高精度的线性代数"技术可能比结论更重要。</p>
  <div class="note">
    <span class="label">侧栏：整数乘法低于 n log n（family 109）</span>
    <p>小学竖式 n²；Karatsuba 1962 年 n^1.585；Schönhage–Strassen 1971 年 n log n log log n 并猜想 n log n 最优；Harvey–van der Hoeven 2019 年（Annals 2021）做到 O(n log n)。OpenAI 声称在多带图灵机上做到 O(n (log n)^{1−2^{−182}})（73 页，<strong>无 Lean</strong>）。2^{−182} 的节省只在天文规模上可见，实际意义为零；但它推翻了一个 50 年的"最优"猜想（在该计算模型下）。</p>
  </div>
</section>

<section id="color">
  <div class="kicker">组合 · family 158（+ 156）</div>
  <h2><span class="n">9.</span>给平面涂色：距离恰好为 1 的两点不能同色</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>图着色</strong>（CS 老朋友：寄存器分配、排课）：相邻顶点颜色不同，最少几种颜色？</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>单位距离图</strong>：平面上<em>每个点</em>都是顶点，距离恰好为 1 的两点连边。它的色数记作 χ(ℝ²)。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>为什么 3 色不够</strong>：Moser 菱形对（下图，7 个点）。<strong>为什么 7 色够</strong>：用直径小于 1 的正六边形铺满平面，按 7 色周期上色，同色六边形相距大于 1。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body">于是 4 ≤ χ ≤ 7，<strong>从 1950 年代一直卡到 2018 年</strong>；2018 年生物老龄化研究者 Aubrey de Grey 用一个 1581 点的有限图把下界推到 5（后经 Polymath16 + SAT 求解器缩小到约 509 点）。</div></div>
  </div>
  {{FIG_MOSER}}
  <div class="claim"><span class="label">声称 [P]</span>
    <p><strong>The Euclidean plane is not five-colorable</strong>（2026-09-23，62 页）："We prove that every coloring of the Euclidean plane with five colors has a monochromatic unit-distance pair, with no regularity assumption on the color classes. Consequently, the chromatic number of the plane is either six or seven."</p>
  </div>
  <p><strong>出人意料的方法</strong>：此前下界的标准套路是"找一个有限图，证明它不能 k 着色"（de Grey 那条路）。这篇<strong>没有给出任何有限图</strong>，而是走遍历论 + 测度论：先证明"存在真正的 k 着色 ⇔ 存在一种'弱可测'的 k 着色"（对平移和旋转做平均，用到这些群的<em>可顺从性</em>——正好接上 §10 的主题），再证明弱可测 5 着色不存在。最后一步，又回到了 1961 年的 Moser 菱形对。</p>
  <p><strong>核实</strong> <span class="tg">[P]</span>：Lean 陈述只有两行，人一眼能核对：</p>
<pre><code>def ProperColoring (k) (c : ℂ → Fin k) : Prop := ∀ x y : ℂ, ‖x - y‖ = 1 → c x ≠ c y
theorem no_proper_five_coloring : ¬ ∃ c : ℂ → Fin 5, ProperColoring 5 c</code></pre>
  <p>没有可测性假设，<strong>忠实于原问题</strong>。证明约 70 个文件、3 万行，无 sorry/axiom。Gil Kalai："raises the lower bound to six, leaving six and seven as the two possible answers"，同时提醒 "even Lean verification may have issues" <span class="tg">[R]</span>。</p>
  <p><strong>如果为真</strong>：χ(ℝ²) ∈ {6, 7}。新的开放问题：由 de Bruijn–Erdős 定理，一定存在一个需要 6 色的有限单位距离图——但没人知道它长什么样，这是 AI + SAT 的好目标。这也是"人审陈述、机器审证明"最理想的形态：陈述两行，证明三万行。</p>
  <div class="note">
    <span class="label">侧栏：Borsuk 猜想在 9 维不成立（family 156）</span>
    <p>圆盘不能切 2 块使每块直径都变小（总有一块含一对对径点），但切 3 块可以。Borsuk 1933 年问：ℝᵈ 中任何有界集合是否总能切成 d+1 块直径更小的部分？Kahn–Kalai 1993 年在 1325 维否定它；此后反例维数降到 64（2014）、63（2026-05，借助 GPT-5.5 Pro）。OpenAI 声称：取 ℝ⁴ 中所有单位向量 u 的投影矩阵 uuᵀ，它们落在 9 维空间里，<strong>不能用 10 块直径更小的集合覆盖</strong>——一下从 63 维降到 9 维（18 页，有 Lean）。4–8 维仍然开放。</p>
  </div>
</section>

<section id="thompson">
  <div class="kicker">群论 · family 248</div>
  <h2><span class="n">10.</span>Thompson 群 F：一个"证明了又撤回"了几十年的问题</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>群</strong> = 一组可以复合、可以撤销的操作。例：整数加法；正方形的 8 个对称。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>生成元</strong>：少数几个操作拼出整个群。ℤ 由"+1"生成；<strong>自由群 F₂</strong> 由 a、b 生成且没有任何关系，它的 Cayley 图是一棵每点 4 叉的无限树。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>Thompson 群 F</strong>：[0,1] 到自身的单调递增、分段线性函数，断点是 k/2ⁿ，每段斜率是 2 的整数次幂；运算是函数复合。由 x₀（下图）和 x₁ 两个元素生成。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>可顺从（amenable）= 能不能"公平地取平均"</strong>。Følner 判据：能否找到有限集合 A，用生成元平移后变化的比例任意小？ℤ 可以，F₂ 不行。这个概念是 von Neumann 1929 年为解释 <strong>Banach–Tarski 悖论</strong>（一个球切成有限块拼成两个同样大的球）引入的——悖论的根源正是旋转群里藏着 F₂。</div></div>
    <div class="rung"><div class="lvl">第 4 级</div><div class="body">"不可顺从是否都因为含 F₂？"答案是否（1980 年代有反例），但反例都很"怪"。F 不含 F₂（1985），所以如果 F 不可顺从，它就是一个<strong>自然、有限表示</strong>的反例。</div></div>
  </div>
  {{FIG_THOMPSON}}
  <h3>10.1 为什么这是"Lean 为什么重要"的最佳案例</h3>
  <p>Geoghegan 1979 年猜想 F 不可顺从。此后两个方向都有人宣布过证明：2009 年 arXiv 上几乎同时出现 Akhmedov（不可顺从）和 Shavgulidze（可顺从）的论文；Moore 2011 年指出后者的错误 "serious and do not seem to be repairable"——而那篇论文已经发表了；<strong>Justin Moore 本人 2012 年声称可顺从，后被指出 Lemma 4.13 有错并撤回</strong>；Akhmedov 的版本至今未被接受。<span class="tg">[P，arXiv 1102.0747 / 1209.2063 / 1310.4395]</span></p>
  <div class="claim"><span class="label">声称 [P]</span>
    <p><strong>Thompson's group F is nonamenable</strong>（2026-09-23，<strong>正文只有 13 页</strong>）："We prove that Thompson's group F is nonamenable. This confirms Geoghegan's conjecture."</p>
    <p>思路：借用泛函分析里的一个现象——无穷维 Hilbert 空间的单位球上存在一个 Lipschitz 映射，把每个点都移动至少 ½（Benyamini–Sternfeld 1983）。如果 F 有 Følner 集，在它上面取平均就会得到这个映射的近似不动点，矛盾。关键工具来自无穷维几何，而不是群论常用的组合计数。</p>
  </div>
  <p><strong>核实</strong> <span class="tg">[P]</span>：Lean 挑战文件<strong>从头定义了 F</strong>（单调递增同胚、有限个二进断点、斜率 2^k）和"不变均值"（线性、正、归一、左不变），定理是"存在使乘法 = 函数复合的群结构，且不存在不变均值"——乘法被强制为复合，没有作弊空间，<strong>忠实</strong>。证明约 68 个文件、9,500 行，无 sorry/axiom。Kalai 措辞谨慎地说论文 "announces" 这一结果 <span class="tg">[R]</span>；Geoghegan、Moore、Akhmedov 未见公开评论 ⚠。</p>
  <p><strong>要点</strong>：这个领域的人类历史是一串"宣布 → 发现错误 → 撤回"，连顶尖专家也撤回过。陈述约 60 行定义、人能逐行审；13 页论文按过去经验社区可能要几年才能达成共识。Lean 把"信任作者"换成了"信任内核 + 陈述"。</p>
</section>

<section id="ns">
  <div class="kicker">偏微分方程 · 9 月单独发布（+ family 376）</div>
  <h2><span class="n">11.</span>Navier–Stokes：流体会不会在有限时间里"炸掉"</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>ODE vs PDE</strong>：ODE 的未知量是一个随时间变化的数 x(t)；PDE 的未知量是一整个场，比如每一点、每一时刻的流速 u(x,t)——相当于无穷多个耦合的 ODE。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>手算爆破</strong>（下图）：ẋ = x² 、x(0) = 1 的解是 1/(1−t)，t = 0.9 时 10，t = 0.99 时 100，t → 1 时 ∞。方程完全光滑，解却在有限时刻坏掉。加阻尼 ẋ = x² − x：小初值衰减，大初值仍然爆破。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>NS 方程</strong>：∂ₜu + (u·∇)u − νΔu + ∇p = f，∇·u = 0。(u·∇)u 是非线性"自我输运"（对应玩具里的 x²），νΔu 是粘性（对应 −x），f 是外力。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>为什么 3D 难</strong>：唯一的全局守恒量是能量，而在 3D 的缩放下，尺度越小能量上界越"管不住"——叫"超临界"。2D 是临界的，所以 2D 早就解决了。</div></div>
  </div>
  {{FIG_BLOWUP}}
  <div class="claim"><span class="label">声称 [P]</span>
    <p>《Finite time blowup for Navier–Stokes》（2026-09-08，166 页，另有约 64 万行 Lean 的独立仓库 <a href="https://github.com/openai/NavierStokesAndEuler">openai/NavierStokesAndEuler</a>）："For every positive viscosity, we construct a solution … that starts from rest and develops unbounded velocity in finite time while maintaining uniformly bounded kinetic energy." 外力 f 光滑且时空紧支撑；论文明确说这建立了 Clay 的<strong>分支 (C)，并推出 (D)</strong>。</p>
  </div>
  <h3>11.1 关键细节：外力是你挑的</h3>
  <p>论文第 2 节自己点明："For any incompressible flow u and pressure p, we can always define the external force f to be the residual … The challenge is to choose a flow that blows up while this residual remains smooth." 也就是说，(C)/(D) 把问题变成"能否构造一个会爆的流，同时让'残差外力'保持光滑"——这比"流体<em>自己</em>会不会爆"（无外力的 (A)/(B)）弱得多。多数分析学家认为真正的问题是 (A)/(B) <span class="tg">[R]</span>。这不是作弊——(C) 是 Clay 合法写进题面的分支——而是<strong>规格与意图之间的差距</strong>，形状上很像 AI 里的规格博弈。</p>
  <h3>11.2 核实与争议</h3>
  <ul>
    <li><strong>Lean</strong> <span class="tg">[P]</span>：约 2,659 个文件、64 万行，无 sorry/axiom；Comparator 开启了 nanoda 第二内核。题面结构与 Clay (C)/(D) 一致（衰减条件未逐条比对 ⚠）。</li>
    <li><strong>社区</strong> <span class="tg">[R]</span>：Clay 主席 Bridson 说评估会 "deliberately unhurried"，Clay 仍把 NS 列为未解决；未见期刊投稿报道。Clay 规则要求在合格刊物发表 + 两年接受期。</li>
    <li><strong>归属争议</strong> <span class="tg">[R]</span>：NYU 的 Buckmaster 与 Alpöge 8 月已得到带外力的 Euler/Boussinesq 爆破，9 月 7 日公开；OpenAI 承认是听到他们的研究传闻后才启动的。Fefferman（Clay 题面作者）："The heroes of the story … are Córdoba and Martínez-Zoroa"（带外力 Euler 爆破的前驱工作）。初版论文未引用 Córdoba–Martínez-Zoroa，修订版补上。Gómez-Serrano（NPR）："The paper is not written for humans … as of today, the paper doesn't teach us much."</li>
  </ul>
  <div class="note">
    <span class="label">相关：受迫 Navier–Stokes 中的通用计算（family 376）</span>
    <p>声称：在 3 维环面上，存在一个光滑外力"程序"，使某个流体粒子进入指定区域<strong>当且仅当</strong>给定图灵机停机——所以这个可达性问题不可判定。论文诚实地说："There is an elementary way to force a chosen smooth incompressible velocity…" 它让人想到 Tao 2016 年的纲领（让流体<em>自己</em>搭出计算机、把能量一次次传给更小的自身副本从而爆破），但 376 把"编程"放在外力里，<strong>不推进</strong>那条无外力爆破纲领，论文也未引用 Tao 2016。</p>
  </div>
  <p><strong>如果为真</strong>：形式上关闭了一个千禧年问题的一个分支。对天气、湍流、工程几乎没有直接影响——工程求解器从不依赖整体正则性，真实流体在到达奇点之前分子尺度就接管了。</p>
</section>

<section id="vlasov">
  <div class="kicker">数学物理 · family 362</div>
  <h2><span class="n">12.</span>相对论 Vlasov–Maxwell：等离子体模型会不会自己坏掉</h2>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>等离子体</strong>：被电离的气体（聚变堆、太阳风）。太稀薄、粒子几乎不碰撞，所以用<strong>相空间密度</strong> f(t, x, v) 描述"在位置 x、动量 v 附近有多少粒子"——6 维 + 时间。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>自洽耦合</strong>：粒子受洛伦兹力（Vlasov 方程）→ 粒子形成电流 → 电流产生场（Maxwell 方程）→ 场再推粒子。非线性就来自这个闭环。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>相对论</strong>（c = 1）：速度 v̂ = p/√(1+p²)。p = 1 时 0.707，p = 10 时 0.995——动量可以无限大，速度永远 &lt; 1。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>Glassey–Strauss 1986</strong>：奇点只可能出现在高速处——只要粒子动量在有限时间内有界，解就能延续。整个问题被归约为：<strong>粒子会不会在有限时间里被加速到无穷大动量？</strong>此后 40 年只有小初值、降维、对称性等附带限制的结果。</div></div>
  </div>
  {{FIG_HARMONIC}}
  <div class="claim"><span class="label">声称 [P]</span>
    <p>《Global classical solutions of the three-dimensional relativistic Vlasov–Maxwell system》（2026-09-23，49 页）："We prove global existence and uniqueness for arbitrary smooth admissible initial data in the three-dimensional, one-species relativistic Vlasov–Maxwell system … without size or symmetry restrictions on the data."</p>
  </div>
  <p><strong>核实</strong> <span class="tg">[P]</span>：Lean 题面 <code>global_classical_solution</code> 的假设逐项对过（f₀ 光滑、紧支撑、非负；场各阶导数有界且属于 L²；两条 Gauss 约束），结论是存在 + 光滑 + 唯一。约 207 个文件、9 万行，无 sorry/axiom。<strong>范围限制</strong>：只覆盖<strong>单一粒子种类</strong>，而真实聚变等离子体至少有电子和离子两种；推广是否平凡不确定 ⚠。未找到等离子体 PDE 专家的具名评论 ⚠。</p>
  <p><strong>推理摘要很坦白</strong>：模型中途多次碰壁（"指数不等式矛盾：H&lt;0.41z vs H&gt;0.496z"），最后一句写道结论 "rests on the occupation bound, direction-count estimate, and cutoff cancellations … the cited continuation theorem alone does not establish those estimates."</p>
  <p><strong>如果为真</strong>：一个约 40 年的旗舰开放问题（单种类）得解，而且有机器验证，分量可能超过本批大多数结果。对聚变工程短期无影响（PIC、gyrokinetic 模拟不依赖这个定理）；它证明的是"模型本身不会自发产生无穷能量粒子"——一种"模型健康证明"。</p>
</section>

<section id="spin">
  <div class="kicker">概率与统计力学 · family 221</div>
  <h2><span class="n">13.</span>稀疏自旋玻璃：从磁铁到神经网络的能量地形</h2>
  <p>这一节和你的神经科学背景直接相连：Hopfield 网络的能量函数，就是自旋玻璃的 Hamiltonian。</p>
  <div class="ladder">
    <div class="rung"><div class="lvl">第 0 级</div><div class="body"><strong>Ising 磁体</strong>：每个格点一个自旋 σᵢ = ±1，能量 H = −Σ Jᵢⱼσᵢσⱼ。J &gt; 0 时相邻自旋想同向。</div></div>
    <div class="rung"><div class="lvl">第 1 级</div><div class="body"><strong>挫折</strong>（下图左）：三个自旋两两"想反向"，8 种构型里没有一种能同时满足三条边，基态 6 重简并。</div></div>
    <div class="rung"><div class="lvl">第 2 级</div><div class="body"><strong>自旋玻璃</strong>：耦合 Jᵢⱼ <em>随机</em>正负，挫折到处都是，能量地形崎岖、有指数多个亚稳态。<strong>SK 模型</strong>（1975）每对自旋都耦合；<strong>Parisi 1979</strong> 用"复本对称破缺"给出自由能公式——物理上神奇、数学上不严格；Guerra 2003 + Talagrand 2006 严格证明；Parisi 获 2021 年诺贝尔物理学奖。</div></div>
    <div class="rung"><div class="lvl">第 3 级</div><div class="body"><strong>稀释（稀疏）版本</strong>：每个自旋只连有限多条边。<strong>Mézard–Parisi 2001</strong> 用 cavity 方法给出层级公式；其中一个方向（上界）2003–04 年已证，<strong>等号是开放猜想</strong>。难点：稠密模型里两两重叠就够描述状态，稀疏模型要控制所有多复本重叠。</div></div>
    <div class="rung"><div class="lvl">第 4 级</div><div class="body"><strong>和随机 k-SAT 的联系</strong>：k-SAT 就是一个稀疏、k 元相互作用的自旋玻璃。Ding–Sly–Sun 2015 对大 k 严格证明了可满足性阈值，正是这套物理方法的预测。</div></div>
  </div>
  {{FIG_SPIN}}
  <div class="claim"><span class="label">声称 [P]</span>
    <p>《The Mézard–Parisi formula for diluted spin glasses》（2026-09-23，36 页）："We prove the Mézard–Parisi hierarchical cavity formula for diluted even-arity Ising models in the Panchenko–Talagrand class." 关键技巧：把每个分叉深度整体推迟一层再对深度平均，从而控制多复本重叠。推理摘要里有一句："Aha recursive structure: overfitting shared variable can simulate original model at smaller scale."</p>
  </div>
  <p><strong>核实</strong> <span class="tg">[P]</span>：Lean 定理 <code>mezard_parisi</code>（压强收敛到变分值），<code>Admissible</code> 逐条写出 Panchenko–Talagrand 类的假设；约 405 个文件、5.6 万行，无 sorry/axiom。<strong>范围比标题窄</strong>：只覆盖<strong>偶数元</strong> + 正性条件——3-SAT 这类奇数元模型、零温度下的硬约束 SAT 都不在内，所以它<strong>不</strong>直接推广 Ding–Sly–Sun。未找到具名专家评论 ⚠。</p>
  <h3>13.1 和 ML / 神经科学的联系（诚实版）</h3>
  <ul>
    <li><strong>Hopfield 网络</strong>（1982）：记忆是能量极小，存储容量由复本方法算出（Amit–Gutfreund–Sompolinsky 1985）；Hopfield 与 Hinton 获 2024 年诺贝尔物理学奖。</li>
    <li><strong>感知机</strong>：Gardner 1988 用复本方法算容量；同批的 family 222 给出了 Ising 感知机自由能和一个 jamming 指数。</li>
    <li><strong>损失地形</strong>："崎岖地形 + 层级聚类的极小值"这套直觉来自自旋玻璃（如 Choromanska 等 2015）。但这些类比大多是<em>启发式</em>的，这个定理不会告诉你 SGD 会找到什么。</li>
  </ul>
</section>

<section id="hodge">
  <div class="kicker">反面案例 · family 032 与 10-07 撤稿</div>
  <h2><span class="n">14.</span>一个符号错误撤掉 3 篇：未形式化的风险</h2>
  <p><strong>Hodge 猜想</strong>（千禧年问题）极简版：在光滑射影复代数簇上，有些"拓扑洞"可以由代数方程定义的子簇来"填"；猜想说凡是满足某个线性代数条件的洞都能这样填。p = 1 的情形 1924 年已知（Lefschetz）。</p>
  <p>OpenAI 声称对所有<strong>复乘（CM）阿贝尔簇</strong>证明了有理 Hodge 猜想（53 页）——这只是一个特殊类，不是千禧年问题本身；而且它和 ζ 无零区一样，<strong>不是</strong>按固定流程产出的，<strong>没有 Lean</strong>。<span class="tg">[P]</span></p>
  {{FIG_HODGE}}
  <h3>14.1 发生了什么 <span class="tg">[P]</span></h3>
  <p>history.md（10-07）："In 'Algebraicity of Weil classes on split abelian eightfolds' a sign error invalidates a stabilization-trace cancellation argument and the construction used by two dependent papers." 一个本应是 −1 的符号被当成 +1，带符号的计数从声称的 0 变成 −2m ≠ 0，关键定理的前提不成立；依赖它的两篇 K3 曲面论文连带撤回。CM 主论文不引用被撤论文，不在这条链上。</p>
  <h3>14.2 三个教训</h3>
  <ol>
    <li><strong>未形式化 ≈ 未验证</strong>：只有约 42% 的顶层结果有 Lean。这个错误只是一个符号——人眼和模型自查都漏了，Lean 必然会抓到。</li>
    <li><strong>错误沿依赖图传播</strong>：一个引理错了，三篇论文一起倒，下游 13 篇要更新引用——和 agent 长链推理中的错误复合是同一种结构。</li>
    <li><strong>标题漂移</strong>：家族 032 原名 "Hodge and Kuga–Satake results for all projective K3 surfaces"，撤稿后才降级为 CM 版本。读批量 AI 产出时，以最新 commit + history.md 为准，不以首发新闻为准。</li>
  </ol>
</section>

<section id="synthesis">
  <div class="kicker">Synthesis · 横向看</div>
  <h2><span class="n">15.</span>把 10 个结果放在一起看</h2>
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
    </tbody>
  </table></div>
  <h3>15.1 五个模式</h3>
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
  <h2><span class="n">16.</span>这件事对 AI 意味着什么</h2>
  <h3>16.1 数学好 ≠ 全面更聪明，但它是先行指标</h3>
  <p>数学对 AI 有一个独特优势：<strong>答案可以被机器检验</strong>（Lean），这让强化学习可以大量"试错 → 拿反馈 → 改进"。Chollet 的追问正中要害：这些"可验证领域"的进步能否迁移到不可验证的领域？合理的读法是：<strong>凡是能被自动检验的智力工作，接下来都会以类似速度被攻破</strong>——数学只是第一个。</p>
  <h3>16.2 信任瓶颈从"证明"转移到"规格"</h3>
  <p>一旦有了 Lean，问题从"证明对不对"变成"陈述有没有编码对"。这和对齐研究里的核心难题同构：系统可以完美优化你写下的目标，而你写下的目标可能不是你想要的。本 deck 每一节都在做的"逐行读 Lean 陈述"，就是一种 <strong>spec review</strong>——它会成为一项越来越重要、越来越稀缺的人类工作。</p>
  <h3>16.3 "能验证但不能理解"的知识</h3>
  <p>IAS 顾问组的原话：<em>"It is now the case that AI can output mathematical arguments in situations without the human who prompted it being able to understand the arguments, verify them, or take responsibility for them."</em> <span class="tg">[R]</span> 数学是这种局面最先出现、也最干净的领域（因为验证是完美的）。推广到科学：人类可能从"理解者"变成"检验者"。Tao 说的 Math 2.0——把讲解、社区建设、开辟新方向放到和解题同等重要的位置——本质上是在回答"人类在这个新分工里做什么"。</p>
  <h3>16.4 对安全研究的两面</h3>
  <div class="verdict">
    <div class="panel"><h4>好消息</h4><ul>
      <li><strong>验证比发现容易</strong>：如果未来的 AI 能为自己的行为给出形式化证明（"这个动作不会做 X"），人类不必理解它的全部能力，只需检验证明——这是 Guaranteed Safe AI 路线的核心想法，数学 AI 越强越可行。</li>
      <li>本批的 Lean 库本身就是"大规模 AI 产出 + 机器验证"的第一个真实样本，可以研究它的失败模式。</li></ul></div>
    <div class="panel"><h4>坏消息</h4><ul>
      <li>对齐里最难的部分（"这个 AI 真正想要什么""结果对人类好不好"）写不成 Lean。可验证领域飞速进步、不可验证领域落后，这个差距本身是风险。</li>
      <li>AI 研发里可验证的部分（kernel 优化、证明、benchmark）会最先被大规模自动化——"AI 改进 AI"的循环最可能从这里开始。</li></ul></div>
  </div>
  <h3>16.5 治理：单方面倾倒的先例</h3>
  <p>社区已经通过 IAS 顾问组形成了初步规范（披露模型名、prompt、推理链、计算时间与成本、选题方式、同类问题失败率），OpenAI 只遵守了一部分，然后一次性发布 700 多篇。AHM 的说法 "a demonstration of power" 虽然激烈，但点到了结构性问题：<strong>前沿公司单方面决定一项能力以什么方式进入公共领域，受影响的共同体只能事后反应</strong>。</p>
</section>

<section id="reactions">
  <div class="kicker">Reactions · 原话</div>
  <h2><span class="n">17.</span>各方怎么说</h2>
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
  <h2><span class="n">18.</span>开放问题与继续学习</h2>
  <h3>18.1 接下来值得盯的</h3>
  <ol>
    <li>OpenAI 会公开 4,000 题清单与失败案例吗？（决定能否回答"真实能力是多少"）</li>
    <li>未形式化的约 58% 里还有多少像 Weil 类论文那样的错误？撤稿率会怎么演化？</li>
    <li>谁来审 Lean 陈述的忠实性？<code>review: unchecked</code> 什么时候改变？<code>lana-agents</code> 依赖和大补丁由谁审？</li>
    <li>第一个人类领域专家对头条结果（准黎曼、UGC、Thompson F）给出"读完并确认"的独立结论会是什么时候？</li>
    <li>"补完他人工作"的优先权规范怎么建立（Buckmaster 事件）？</li>
    <li>平面色数：需要 6 色的有限单位距离图长什么样？</li>
  </ol>
  <h3>18.2 学习路线（只需线性代数 + 微积分起步）</h3>
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
  <h2><span class="n">19.</span>术语表与来源</h2>
  <h3>19.1 术语</h3>
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
  <h3>19.2 主要来源</h3>
  <p><strong>一手</strong>：<a href="''' + REPO + '''">openai/math</a>（README、history.md、overview.pdf、CONTENTS.md、lean/、preprints/、reasoning_traces/；快照 fd4aeeb，2026-10-08）· <a href="https://github.com/openai/NavierStokesAndEuler">openai/NavierStokesAndEuler</a> · <a href="https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf">Clay NS 官方陈述（Fefferman）</a> · <a href="https://github.com/leanprover/comparator">leanprover/comparator</a> · 独立复核 <a href="https://github.com/davegoldblatt/openai-zeta-proof-check">davegoldblatt/openai-zeta-proof-check</a>、<a href="https://github.com/erenciracioglu-dotcom/openai-math-9-4-lean-check">erenciracioglu-dotcom/openai-math-9-4-lean-check</a> · Epoch <a href="https://arxiv.org/abs/2609.25050">FrontierMath Erdős（arXiv:2609.25050）</a>。</p>
  <p><strong>报道与评论</strong>：<a href="https://fortune.com/2026/10/07/openai-math-controversy-solutions-370-outstanding-challenges-published-criticisms-celebration/">Fortune 10-07</a> · <a href="https://www.nature.com/articles/d41586-026-03196-8">Nature</a>（付费墙，未读全文 ⚠）· <a href="https://www.scientificamerican.com/article/openai-unleashes-hundreds-more-math-results-upon-a-field-already-in-shock/">Scientific American</a> · <a href="https://www.quantamagazine.org/ai-has-solved-one-of-maths-1-million-millennium-prize-problems-20260908/">Quanta 09-08</a> · <a href="https://www.quantamagazine.org/as-ai-closed-in-on-unique-games-proof-researchers-raced-to-beat-the-machines-20261007/">Quanta 10-07</a> · <a href="https://www.npr.org/2026/09/22/nx-s1-5968588/openai-navier-stokes-problem-mathematicians-learn-little">NPR 09-22</a> · <a href="https://scottaaronson.blog/?p=10169">Aaronson</a> · <a href="https://gilkalai.wordpress.com/2026/10/07/updates-sharing-ai-progress-on-mathematics-amazing-and-my-lecture-plans/">Kalai</a> · <a href="https://terrytao.wordpress.com/">Tao 博客</a> · <a href="https://www.latent.space/p/ainews-quasi-riemann-hypothesis-openai">Latent Space</a>。</p>
  <p><strong>经典文献</strong>：Strassen 1969；Coppersmith–Winograd 1990；Alman 等 <a href="https://arxiv.org/abs/2404.16349">arXiv:2404.16349</a>；Ambainis–Filmus–Le Gall <a href="https://arxiv.org/abs/1411.5414">arXiv:1411.5414</a>；Goemans–Williamson 1995；Khot 2002；KKMO 2007；Raghavendra 2008；Khot–Minzer–Safra 2018；Nisan 1992；Saks–Zhou 1999；Reingold 2008；Roth 1955；Zeilberger–Zudilin <a href="https://arxiv.org/abs/1912.06345">arXiv:1912.06345</a>；Meiburg <a href="https://arxiv.org/abs/2208.13356">arXiv:2208.13356</a>；Guth–Maynard <a href="https://arxiv.org/abs/2405.20552">arXiv:2405.20552</a>；de Grey <a href="https://arxiv.org/abs/1804.02385">arXiv:1804.02385</a>；Moore <a href="https://arxiv.org/abs/1102.0747">arXiv:1102.0747</a>；Tao 2016 <a href="https://arxiv.org/abs/1402.0290">arXiv:1402.0290</a>；Glassey–Strauss 1986；Parisi 1979；Talagrand 2006；Mézard–Parisi 2001；Ding–Sly–Sun 2015。</p>
  <p class="tg">研究底稿（含每条的 [P]/[R]/⚠ 标注、Lean grep 细节和未进 deck 的材料）见本目录 deep_reads/。</p>
</section>
'''

FIGS = {
    "{{FIG_FIELDS}}": figs.svg_fields(), "{{FIG_TRUST}}": figs.svg_trust(), "{{FIG_ZETA}}": figs.svg_zeta(),
    "{{FIG_FLINT}}": figs.svg_flint(), "{{FIG_OMEGA}}": figs.svg_omega(), "{{FIG_MAXCUT}}": figs.svg_maxcut(),
    "{{FIG_MOSER}}": figs.svg_moser(), "{{FIG_THOMPSON}}": figs.svg_thompson(), "{{FIG_BLOWUP}}": figs.svg_blowup(),
    "{{FIG_HARMONIC}}": figs.svg_harmonic(), "{{FIG_SPIN}}": figs.svg_spin(), "{{FIG_HODGE}}": figs.svg_hodge(),
}
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
