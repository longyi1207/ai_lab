# Navier–Stokes：流体会不会在有限时间里"炸掉"（带外力的有限时间爆破）

> 偏微分方程 · OpenAI 2026-09-08 单独发布的结果（不在 10 月 openai/math 的 372 个 family 里），外加 10 月发布中与之相关的 family 376（受迫 NS 中的通用计算，§11.7.5）。前提只需要：会求导、知道偏导数 ∂/∂x 的意思、知道向量和点积。不需要学过偏微分方程（PDE），PDE 从头讲。
> 文中所有数字都由脚本实算或有出处；【检查】是可以自己动手算的小练习，答案在章末。标记：**[P]** = 我亲自读过的一手材料（论文 PDF、Lean 文件、Clay 官方文本）；**[R]** = 二手报道；**⚠** = 未核实或有争议。截至 2026-10-08。
> 预计阅读时间：60–90 分钟。可以分三次读：§11.1–11.3（PDE、流体方程、什么叫爆破）、§11.4–11.6（为什么难、历史、Clay 题面）、§11.7–11.9（OpenAI 的结果和相关的 family 376、核实、意义）。

---

## 11.0 先说结论：这一章要讲明白的一件事

Navier–Stokes（NS）方程描述水、空气怎么流动，工程上天天在用。但最基本的问题没人能回答：**从光滑、温和的初始状态出发，流速会不会在有限时间内变成无穷大？**

这一章要讲清楚的是一条因果链：

> 方程里有一项"流体自己推自己"的非线性项，它会把速度越推越陡 ⟸ 粘性在把它抹平 ⟸ 两者谁赢，取决于尺度 ⟸ 在 3 维里，我们手里唯一的"全局账本"（能量）在越来越小的尺度上越来越管不住 ⟸ 所以没人能证明粘性总会赢，也没人能造出它输的例子。

Clay 在 2000 年把它列为千禧年难题，给出 **四个可选表述 (A)–(D)**，证出任一即算解决：(A)(B) 是"无外力时解永远光滑"，(C)(D) 是"**存在**某个光滑外力，使解在有限时间坏掉"。

**OpenAI 在 2026-09-08 声称证明了 (C) 和 (D)**：一个光滑、只在有限时空范围内起作用的外力，让从静止开始的流体在 t = 1 时某点速度变成无穷大，总能量始终有界；附约 64 万行 Lean。同一天还发布了可能更重要的 **无外力 3D Euler（无粘性流体）从光滑初值爆破**。

读完这一章，你应该能用自己的话讲出：
- PDE 是什么，"光滑解永远存在"和"有限时间爆破"各是什么意思；
- 为什么能量守恒挡不住 3 维的爆破（超临界缩放，带数字）；
- Clay 的 (A)–(D) 各说了什么，外力 f 在 (C)/(D) 里扮演什么角色；
- OpenAI 的结果按 Clay 官方文本**形式上**算不算解决，离"拿到奖金"还差哪几道关，以及为什么很多分析学家认为真正的问题还是 (A)/(B)。

---

## 11.1 什么是 PDE：从热方程开始

### 11.1.1 ODE 和 PDE

你熟悉的微分方程，比如 y'(t) = −y(t)，未知量是**一个**随时间变化的数 y(t)。这叫常微分方程（ODE）。

偏微分方程（PDE）的未知量是**一整个场**：每个位置 x、每个时刻 t 都有一个值 u(x, t)。方程同时涉及对时间的导数 ∂u/∂t 和对空间的导数 ∂u/∂x。

把空间切成小格，每格一个未知数，相邻格子互相影响：PDE 就是"**无穷多个耦合的 ODE**"，像一个每个节点只和邻居通信的分布式系统。

### 11.1.2 最简单的 PDE：热方程

一根细铁棒，u(x, t) 是位置 x 在时刻 t 的温度。热方程是：

```
∂u/∂t = k · ∂²u/∂x²
```

右边的 ∂²u/∂x² 是"曲率"：如果某点比两边邻居都热（像山峰），它是负的，温度就下降；比邻居都冷（像山谷），它是正的，温度就上升。所以**热方程就是"每个点向邻居平均值靠拢"**。

离散成格子更好理解。格距 Δx，时间步 Δt，记 r = kΔt/Δx²，一步更新是：

```
新值ᵢ = 旧值ᵢ + r · (旧值ᵢ₋₁ − 2·旧值ᵢ + 旧值ᵢ₊₁)
```

**手算一步**（r = 0.25，脚本核对过）：7 个格子 `[0, 0, 0, 1, 0, 0, 0]`，中间那个是一个热点。
- 中间：1 + 0.25·(0 − 2 + 0) = 0.5
- 两个邻居：0 + 0.25·(0 − 0 + 1) = 0.25
- 结果：`[0, 0, 0.25, 0.5, 0.25, 0, 0]`，总和仍然是 1。

热点被摊开了，但总热量不变。

【检查 1】从 `[0, 0, 0.25, 0.5, 0.25, 0, 0]` 再走一步（r = 0.25），结果是什么？总和是多少？

### 11.1.3 数值模拟：热方程会把一切抹平

脚本实算：k = 1，初始温度在 |x| < 0.5 处为 1、其他地方为 0（一个"方块"，边缘是无限陡的台阶），用上面的格式在 1001 个格点上推进。

| t | 中心温度（数值） | 中心温度（精确解） | 总热量 | 最陡的斜率 |
|---|---|---|---|---|
| 0 | 1.0000 | 1.0000 | 0.990 | 100（网格允许的最陡台阶） |
| 0.01 | 0.9996 | 0.9996 | 0.990 | 2.82 |
| 0.1 | 0.7316 | 0.7364 | 0.990 | 0.83 |
| 0.5 | 0.3794 | 0.3829 | 0.990 | 0.22 |

（总热量是 0.990 而不是 1，是因为网格上的方块宽 0.99。）

要记住：**热方程只会让东西变平滑**，无穷陡的台阶瞬间变成光滑曲线，斜率一路下降；它是线性的，不可能自己"爆"。NS 里的**粘性项**数学上就是"对速度做热方程"，站在"光滑"这一边。

---

## 11.2 流体：速度场和 NS 方程逐项拆解

### 11.2.1 速度场

流体的未知量是**速度场** u(x, t)（每点每刻一个 3 维向量）和**压力** p(x, t)（一个数）。

一个 2 维例子：u(x, y) = (−y, x)。在点 (1, 0) 速度是 (0, 1)，向上；在 (0, 1) 速度是 (−1, 0)，向左。画出来是**绕原点逆时针转**的刚体旋转，离中心越远转得越快（速度大小 = 半径 r）。

### 11.2.2 不可压缩：散度为零

水几乎压不缩。数学上写成**散度为零**：

```
∇·u = ∂u₁/∂x + ∂u₂/∂y + ∂u₃/∂z = 0
```

散度衡量"一个小区域里净流出多少"。散度为 0 = 流进多少就流出多少，体积不变。

【检查 2】计算 u = (−y, x) 和 w = (x, y) 的散度。哪个是不可压缩的？w 画出来是什么样子？

### 11.2.3 NS 方程：牛顿第二定律，写给一小团流体

Clay 官方题面（Fefferman 撰写）的原话是："Equation (1) is just Newton's law f = ma for a fluid element" [P]。方程是：

```
∂u/∂t + (u·∇)u  =  ν Δu  −  ∇p  +  f          ∇·u = 0
└──── 加速度 a ────┘  └粘性┘  └压力┘ └外力┘
```

逐项看：

**左边：一小团流体的加速度。** 它有两部分：
- ∂u/∂t：站在固定点看，速度随时间的变化。
- (u·∇)u：这团流体**移动到了速度不同的地方**带来的变化。即使流场不随时间变（定常流），顺着流线走的流体也可能在转弯、加速。

(u·∇)u 是 u 乘以 u 的导数，**关于 u 是二次的**，这就是 NS 的**非线性**来源，也是全部困难的来源。直观上：流体"自己推着自己走"。

**用旋转流手算这一项。** 对 u = (−y, x)，(u·∇)u 的第一个分量是 u₁·∂u₁/∂x + u₂·∂u₁/∂y = (−y)·0 + x·(−1) = −x；第二个分量是 (−y)·1 + x·0 = −y。所以 (u·∇)u = (−x, −y)，**指向圆心，大小为 r**。这正是高中物理的向心加速度 v²/r = r²/r = r。

**右边第一项：粘性 νΔu。** Δ = ∂²/∂x² + ∂²/∂y² + ∂²/∂z²，和热方程右边是同一个东西。相邻流层速度不同（剪切）时互相拖拽，把速度差抹平。

**右边第二项：压力 −∇p。** 从高压推向低压。在不可压缩流里，压力是"为了让 ∇·u = 0 时刻成立而自动调节出来的力"，即不可压缩约束的拉格朗日乘子。

**右边第三项：外力 f。** 比如重力、搅拌器、电磁力。**这一项是理解 OpenAI 结果的关键**，§11.6 专门讲。

【检查 3】对旋转流 u = (−y, x)，取 ν > 0、f = 0。(a) 计算 Δu。(b) 这个流是定常的（∂u/∂t = 0），方程要求 (u·∇)u = −∇p。找出压力 p。压力在中心高还是边缘高？

### 11.2.4 雷诺数：非线性和粘性谁大

一个尺度为 L、速度为 U 的流动：
- 非线性项把速度搬运一个尺度的时间约为 L/U；
- 粘性把这个尺度上的差异抹平的时间约为 L²/ν。

两者之比叫**雷诺数** Re = UL/ν。Re 大，非线性主导（湍流）；Re 小，粘性主导（像蜂蜜一样平稳）。

脚本实算（水 ν ≈ 1.0×10⁻⁶ m²/s，空气 ≈ 1.5×10⁻⁵ m²/s）：1 m/s 的水流过 0.1 m 的管子，Re = 10⁵；30 m/s 的空气流过 4 m 的汽车，Re = 8×10⁶。

记住这个量，§11.4 会用到：**爆破的问题就是，能不能在越来越小的尺度上，让雷诺数不降反升。**

---

## 11.3 "光滑解永远存在"和"有限时间爆破"

### 11.3.1 先看 ODE 玩具：方程完美，解却会坏

对比两个看起来很像的方程，初值都是 y(0) = 1：

| t | y' = y 的解 eᵗ | y' = y² 的解 1/(1−t) |
|---|---|---|
| 0.5 | 1.649 | 2 |
| 0.9 | 2.460 | 10 |
| 0.99 | 2.691 | 100 |

（脚本实算；用 RK4 数值积分 y' = y² 到 t = 0.99 得到 100.0000000001，和精确解一致。）

eᵗ 在每个有限时刻都有限；1/(1−t) 在 **t = 1 时变成无穷大**，这叫**有限时间爆破**。方程右边 y² 再光滑不过，坏掉的是解："越大长得越快"，增长率本身在增长。

### 11.3.2 加上阻尼：谁赢取决于初值

现在加一个"粘性"式的阻尼：y' = y² − y。用代换 z = 1/y 可以精确解出：z(t) = 1 + (z₀ − 1)eᵗ，y 爆破当且仅当 z 碰到 0。

| 初值 y₀ | 结果（脚本实算） |
|---|---|
| 0.5 | 衰减，y(3) ≈ 0.047 |
| 1.0 | 不动，永远 = 1（平衡点） |
| 1.1 | 爆破，t* = ln 11 ≈ 2.398 |
| 2.0 | 爆破，t* = ln 2 ≈ 0.693 |

**小初值阻尼赢，大初值非线性赢。** 对照§11.2.3 的 NS 方程：y² 扮演非线性的"自我输运"项 (u·∇)u，−y 扮演粘性项 νΔu，外力 f 暂时取 0。3 维 NS 的已知理论正好是这个形状：Fefferman 的题面写道，3 维中"(A) and (B) hold provided the initial velocity u° satisfies a smallness condition"，并且对大初值，光滑解至少在一段短时间 [0, T) 内存在 [P]。大初值能不能一直光滑下去，就是千禧年问题。

下图左边把§11.3.1–11.3.2 的曲线画在一起（图里把未知量记作 x，ẋ 就是 dx/dt）：eᵗ 增长但永不爆破；1/(1−t) 在 t = 1 爆破；y' = y² − y 从初值 2 出发在 t = ln 2 ≈ 0.693 爆破，从初值 ½ 出发衰减到 0。右边是§11.6 要细讲的 Clay 四个分支：OpenAI 声称的是带外力的 (C)/(D)，无外力的 (A)/(B) 仍然开放。

{{FIG_BLOWUP}}

### 11.3.3 一个 PDE 玩具：Burgers 方程

把 NS 砍到 1 维、去掉压力：u_t + u·u_x = ν·u_xx。初值 u = −sin x。**无粘性时**，x = 0 处的斜率满足 (u_x)' = −(u_x)²，和 y' = y² 同构，得 u_x(0, t) = −1/(1−t)，t = 1 时斜率无穷大（激波）。**有粘性时**，脚本用谱方法模拟，最陡斜率被封顶在约 1/(2ν)：ν = 0.1 时 3.7（1/(2ν) = 5），ν = 0.01 时 48.4（50），ν = 0.003 时 164.9（166.7）。ν 越小顶越高，但总是有限（1 维粘性 Burgers 可经 Cole–Hopf 变换化成热方程，严格证明不爆）。

**3 维 NS 的问题是：粘性还能不能这样封顶？** 3 维多了一个机制：**涡拉伸**。涡管被拉长变细，像花样滑冰收手臂一样转得更快（角动量 r·u_θ 守恒：半径缩 10 倍，转速变 10 倍）。这个正反馈在 1、2 维都不存在。

### 11.3.4 精确地说"爆破"

"光滑"指所有阶导数都存在且连续（C^∞）。**整体光滑解**：对所有 t ≥ 0 光滑且能量有界。**有限时间爆破**：解在 [0, T) 上光滑，但 t → T 时某处速度或其导数 → ∞。Fefferman 的题面记录：对 NS（ν > 0），爆破时**速度本身**必须无界 [P]，所以 OpenAI 定理写的是 "lim sup ‖u(t)‖_∞ = ∞"。真实的水不会有无穷大速度，分子尺度会先让连续介质模型失效；爆破是**关于这个数学模型的**结论。

---

## 11.4 为什么 3 维这么难：能量与超临界缩放

### 11.4.1 能量：唯一的全局账本

不加外力时，NS 有一个漂亮的恒等式：总动能 E(t) = ½∫|u|² dx **只减不增**（粘性把动能变成热）。非线性项 (u·∇)u 对总能量的贡献恰好为 0，它只在不同尺度之间**搬运**能量，不制造能量。

所以我们有一个对所有时间都成立的上界：E(t) ≤ E(0)。问题是：**这个上界够不够阻止爆破？**

### 11.4.2 缩放对称性

NS 有一个对称性：如果 u(x, t) 是解，那么对任何 λ > 0，

```
u_λ(x, t) = λ · u(λx, λ²t)
```

也是解（压力和外力相应变换）。λ > 1 的意思是"把同一个流动缩小到 1/λ 的尺寸，加快到 λ² 倍的速度播放，流速变成 λ 倍"。

| λ | 尺寸 | 时间 | 流速 | 3D 能量 | 2D 能量 |
|---|---|---|---|---|---|
| 1 | 1 | 1 | ×1 | ×1 | ×1 |
| 10 | 1/10 | 1/100 | ×10 | ×0.1 | ×1 |
| 100 | 1/100 | 1/10⁴ | ×100 | ×0.01 | ×1 |
| 1000 | 1/1000 | 1/10⁶ | ×1000 | ×0.001 | ×1 |

能量那一列的来历：∫|λu(λx)|² dx，令 y = λx，在 3 维中 dx = dy/λ³，所以能量乘以 λ²/λ³ = 1/λ。

【检查 4】按同样的方法算 2 维的能量因子，验证它是 1。

**3D 那一列是关键**：把一个"爆破结构"缩小 1000 倍、加速到 1000 倍流速，所需的能量反而只要原来的千分之一。能量上界对小尺度几乎没有约束力。这叫**超临界**（supercritical）。2D 中能量不随缩放变，叫**临界**，所以 2D 的 NS 早就被证明整体光滑（Ladyzhenskaya，见 Fefferman 题面 [P]）。

### 11.4.3 用雷诺数再说一遍

固定总能量 E = 1、粘性 ν = 1。一团尺寸为 L 的流动，速度最大能有多大？

- 3D：能量 ≈ U²L³ ≤ 1，所以 U ≤ L^(−3/2)，雷诺数 Re = UL/ν ≤ L^(−1/2)。
- 2D：能量 ≈ U²L² ≤ 1，所以 U ≤ 1/L，Re ≤ 1。

| 尺寸 L | 3D 允许的最大 Re | 2D 允许的最大 Re |
|---|---|---|
| 1 | 1 | 1 |
| 10⁻² | 10 | 1 |
| 10⁻⁶ | 1,000 | 1 |
| 10⁻⁸ | 10,000 | 1 |

（脚本实算。）

2D：能量把每个尺度上的雷诺数都压在 1 以下，粘性永远有资格赢。3D：尺度越小，能量允许的雷诺数越大，**粘性在小尺度上可能输**。能量没有排除爆破，也没有证明爆破，它就是"不够用"。这就是 3D NS 问题的核心。

### 11.4.4 Tao 的"超临界屏障"（2016）

Tao（JAMS 29, 2016；arXiv:1402.0290）构造了一个"平均版 NS"：保留能量恒等式和缩放，只把非线性项换成平均过的版本，并证明它**会**爆破。推论：只用"能量 + 一般调和分析估计"的论证不可能证明 (A)/(B)，必须用到真实非线性项的精细结构。他还提出一个**纲领**：在真实流体里搭出"逻辑门"，让流体像自复制机器一样把能量一次次传给更小、更快的自身副本，从而在**无外力** NS 里爆破。这个纲领至今没有实现。（§11.7.5 的 family 376 让人想到这个纲领，但两者不是一回事。）

---

## 11.5 90 年的部分结果

| 年份 | 结果 | 意义 |
|---|---|---|
| 1934 | **Leray**（Acta Math. 63）：任意有限能量初值都有整体**弱解** | 弱解只在"积分平均"意义下满足方程，允许奇点；光滑性、唯一性都未知 |
| 1982 | **Caffarelli–Kohn–Nirenberg**（CPAM 35）：奇点集的抛物 1 维 Hausdorff 测度为 0 | 奇点"不能形成一条时空曲线"（Fefferman 原话 [P]），但孤立点没被排除 |
| 2003 | **Escauriaza–Seregin–Šverák**：L³ 范数有界就不爆 | 爆破必须让 L³ 范数发散 |
| 2016 | **Tao**：平均版 NS 爆破 | 见 4.4 节 |
| 2019 | **Buckmaster–Vicol**（Annals 189）：某类弱解不唯一 | 弱解太"软" |
| 2014 / 2022 | **Luo–Hou** 数值（PNAS）；**Chen–Hou** 计算机辅助证明（arXiv:2210.07191）：**带边界**的 3D 轴对称 Euler 从光滑初值爆破 | 需要固体壁，不在全空间 ℝ³ |
| 2021 | **Elgindi**（Annals 194）：ℝ³ 上 Euler 对 C^{1,α} 初值爆破 | 初值不是 C^∞ |
| 2023 起 | **Córdoba–Martínez-Zoroa**（arXiv:2309.08495 等）：带外力的 3D Euler 爆破，外力光滑度有限 | "外力路线"的开创者：越来越细的涡层逐级放大 |
| 2025 | **DeepMind 等**（arXiv:2509.14185）：用神经网络找到 Boussinesq、IPM 等方程的**不稳定**自相似奇点，精度接近机器精度 | 为无边界情形的计算机辅助证明铺路 |
| 2026-08 | **Buckmaster–Alpöge**：IPM、Boussinesq、3D Euler 在**光滑外力**下爆破，Lean 验证；9 月 7 日（美东时间）公开 | 把 Córdoba–Martínez-Zoroa 的路线推到光滑外力 [P，Buckmaster 声明] |

这张表里反复出现的模式：**Euler（无粘性）比 NS 容易爆；带边界、低光滑度、带外力都比"全空间、C^∞、无外力"容易。** 每放宽一个条件，就有人能做出爆破。千禧年问题 (A)/(B) 是所有条件都不放宽的版本。

---

## 11.6 Clay 的题面：四个分支，以及外力 f 的角色

### 11.6.1 官方原文 [P]

Fefferman 的题面（https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf）先规定"物理上合理"的条件：初值和外力的所有导数快速衰减（条件 4、5），解在 ℝ³ × [0, ∞) 上 C^∞（6），能量一致有界（7）；周期情形用条件 8–11。然后：

> "To give reasonable leeway to solvers while retaining the heart of the problem, we ask for a proof of one of the following four statements."

| 分支 | 区域 | 外力 | 要证明什么 |
|---|---|---|---|
| **(A)** | ℝ³ | f ≡ 0 | **任意**光滑衰减初值 → 存在整体光滑、能量有界的解 |
| **(B)** | 周期环面 ℝ³/ℤ³ | f ≡ 0 | 同上，周期版 |
| **(C)** | ℝ³ | **存在**光滑衰减的 f | **存在**某个初值和外力，使光滑能量有界的整体解**不存在** |
| **(D)** | ℝ³/ℤ³ | **存在**光滑周期 f | 同上，周期版 |

两点：(A)/(B) 是"对所有初值都好"，(C)/(D) 是"存在一个坏例子"，**正反两个方向**；(A)/(B) 规定 f ≡ 0，(C)/(D) 允许你**自己挑**外力，只要光滑且衰减。Fefferman 还写道，Euler 方程（ν = 0）的对应问题"also open and very important"，但不在奖金清单上 [P]。

### 11.6.2 为什么"可以挑外力"让问题变了形状

OpenAI 论文第 2 节自己点明了这一点 [P]：

> "For any incompressible flow u and pressure p, we can always define the external force f to be the residual in (1.1). The Navier–Stokes equations then hold by construction. The challenge is to choose a flow that blows up while this residual remains smooth."

人话：随便画一个会爆的不可压缩流，代进 NS 左边减右边，差多少让 f 补多少，方程**自动**成立。难点只有一个：**补差的外力必须保持光滑**，在爆破时刻也不能坏。

用 ODE 玩具看清楚这个难点：

- **线性方程 y' = −y + g(t)**：想让 y = 1/(1−t) 爆破，需要的外力是 g = y' + y = 1/(1−t)² + 1/(1−t)，它自己也爆了，不光滑。事实上线性方程配光滑外力**永远不会**爆破。
- **非线性方程 y' = y² + g(t)**：同样的 y = 1/(1−t)，g = y' − y² = 1/(1−t)² − 1/(1−t)² = **0**。外力是 0，完全光滑。

所以爆破必须靠非线性项**自己**抵消奇异部分，外力只补光滑的余量。在 NS 里要让所有发散部分到任意阶导数都抵消，这就是那 166 页在做的事。

【检查 5】对 y' = −y + g(t)，如果 g 在 [0, 2] 上光滑有界（比如 |g| ≤ 1），y(0) = 0，y(t) 能在 t = 1 爆破吗？提示：比较 y' ≤ −y + 1。

### 11.6.3 那么 (C) 比 (A) 容易吗？

Clay 在 2000 年把 (C) 和 (A) 并列，认为四个分支都"retaining the heart of the problem"。但 2023 年以后 Córdoba–Martínez-Zoroa 打开的"外力路线"表明，**外力能承担大量"工程"工作**：在需要的时间、地点注入能量、"种下"扰动。Buckmaster 在声明里说这条路线"is the route Luis and Diego opened"，并把下一步目标称为"a path to unforced Euler" [P]。连这条路线的推进者，也把"无外力"看作更深一层的问题。

换句话说，(C)/(D) 把问题变成了"能否造一个会爆的流，同时让残差外力保持光滑"。这比"流体**自己**会不会爆"（无外力的 (A)/(B)）弱得多，多数分析学家认为真正的问题是 (A)/(B) [R]。二手报道的概括：外力路线是"a route the written problem permits but that most working mathematicians exclude from the question they care about" [R，Implicator]。⚠ 这是记者的概括，不是对分析学家的系统调查。

---

## 11.7 OpenAI 声称了什么

### 11.7.1 主定理 [P]

论文 *Finite time blowup for Navier–Stokes*，署名 "OpenAI"，166 页，PDF 生成于 2026-09-08 12:06 PDT（https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf）。它是**单独发布**的：不在 10 月 6 日 openai/math 发布的 372 个 family 里，论文放在 OpenAI 的 CDN 上，约 64 万行的 Lean 证明在独立仓库 [openai/NavierStokesAndEuler](https://github.com/openai/NavierStokesAndEuler)（§11.8.2）。摘要：

> "For every positive viscosity, we construct a solution of the three-dimensional incompressible Navier–Stokes equations that starts from rest and develops unbounded velocity in finite time while maintaining uniformly bounded kinetic energy."

Theorem 1.1 的内容：对每个 ν > 0，存在
- 一个外力 f ∈ C_c^∞(ℝ³ × (0, ∞))：光滑，并且**在空间和时间上都只在一块有界区域里非零**（"紧支撑"）；
- 速度和压力 u, p 在 ℝ³ × [0, 1) 上光滑，**初值 u(·, 0) = 0**（从静止开始），并且始终局限在一个固定的有界区域 K 内；
- 能量 sup‖u(t)‖_{L²} < ∞，速度 lim sup_{t↑1} ‖u(t)‖_{L∞} = ∞。

论文原文："This establishes alternative (C) in the Millennium problem statement … Compact support also yields the corresponding construction on T³ … establishing alternative (D)"（Corollary 10.6）。

**任意粘性的手算。** 论文先在 ν = 1 时构造，再用缩放 u_ν(x, t) = √ν · u(x/√ν, t) 推到任意 ν。爆破时刻不变。

【检查 6】验证：把 u_ν = √ν · u(x/√ν, t) 代入，∂u_ν/∂t、(u_ν·∇)u_ν、νΔu_ν 三项都等于 √ν 乘以原来对应的项。

### 11.7.2 机制的直觉（读了论文第 2 节，以下是简化版）

1. **一根越来越细、越来越快的涡柱。** 原点附近的涡核里，流体螺旋向内、沿轴向上下流出。角动量守恒让向内的流体转得更快；不可压缩性让流进来的流体沿轴流走，向内流动才能持续。
2. **自相似收缩。** 记 τ = 1 − t。核的半径 ℓ_r ~ τ^(1/2)，高度 ℓ_z ~ τ^(1/2−h)，h 是固定小数，0 < h < 1/100。涡柱越来越细长。
3. **问题**：核心外的过渡环带留下一个"残差"，补它所需的外力在 t → 1 时发散。
4. **解决：在环带里加振荡脉冲。** 脉冲的速度平均为 0，但**二次乘积**（动量通量）平均不为 0。两族脉冲精心排列，让非线性通量**正好抵消**残差里发散的部分。每个脉冲由指数小的外力"种下"，再靠背景剪切长大。
5. **外部**：纯旋转、满足热方程的流动，不需要外力；再光滑截断到有界区域。

这正是 6.2 节的"非线性项自己抵消奇异部分"，只是要在 3 维里对所有阶导数做到。

### 11.7.3 数字感受：涡核怎么收缩

取 h = 0.005（论文只要求 0 < h < 1/100，这个值是我为演示选的），按论文给出的标度律算（脚本实算，ν = 1，常数因子取 1）：

| τ = 1 − t | 核半径 ℓ_r | 核高度 ℓ_z | 速度 ~ τ^(−1/2−h) | 核的能量 ~ τ^(1/2−3h) | 旋转雷诺数 τ^(−h) |
|---|---|---|---|---|---|
| 10⁻² | 0.1 | 0.102 | 10.2 | 0.107 | 1.023 |
| 10⁻⁴ | 0.01 | 0.0105 | 104.7 | 0.0115 | 1.047 |
| 10⁻⁸ | 10⁻⁴ | 1.10×10⁻⁴ | 1.10×10⁴ | 1.3×10⁻⁴ | 1.096 |
| 10⁻¹² | 10⁻⁶ | 1.15×10⁻⁶ | 1.15×10⁶ | 1.5×10⁻⁶ | 1.148 |

- **速度 → ∞，核的能量 → 0**：正是§11.4 的超临界，小尺度上用越来越少的能量达到越来越大的速度。
- 速度比纯缩放 τ^(−1/2) 多出因子 τ^(−h)，即**旋转雷诺数**。它趋于无穷，但极慢：τ 从 10⁻² 到 10⁻¹²，只从 1.02 涨到 1.15。爆破是在"刚好比临界多一点点"的边缘上实现的。
- 和已知定理一致：奇点是**一个点**（原点，t = 1），不违反 CKN；L³ 范数的三次方 ~ τ^(−4h)，在 τ = 10⁻¹² 时约 1.74，在发散，符合 ESS 的必要条件（⚠ ESS 针对无外力情形，这里只作直觉检查）。

### 11.7.4 同时发布的 Euler 结果

同一个 Lean 仓库还形式化了第二篇论文 *Finite time blowup for the Euler equation*（57 页，https://cdn.openai.com/pdf/315b36cd-ec98-4023-8342-93345194ece1/euler.pdf）[P]：

> "We exhibit finite-time blowup for the three-dimensional incompressible, unforced Euler equations from smooth, compactly supported, divergence-free initial data."

对比§11.5：Chen–Hou 需要边界，Elgindi 的初值只有 C^{1,α}，Córdoba–Martínez-Zoroa 和 Buckmaster–Alpöge 需要外力。这个结果把这些放宽全部去掉，只剩"没有粘性"与千禧年问题不同。Fefferman 说 Euler 的对应问题"also open and very important" [P]。我的判断（推测）：论离大家真正关心的问题有多近，它可能比带外力 NS 分量更重。⚠ 我没有找到任何专家对这篇论文的具名技术评价。

**规模** [R]：约 1 万个并发智能体，88 小时；Wikipedia 引用 270 万条消息、1300 亿输出 token，另有报道说"近 500 万"条 ⚠。`formalization.yaml` 记录模型为 "GPT-6 Astra"、框架 Codex [P]。

### 11.7.5 相关：受迫 NS 中的通用计算（family 376）

10 月的 openai/math 发布里有一个和"外力"直接相关的结果族：family 376，*Universal computation in forced Navier–Stokes flows*。它由一组预印本组成，代表作是 *A Fixed Particle Test for Computation in a Forced Viscous Flow*（2026-09-27）[P]。

**声称** [P]：固定一个平坦的 3 维环面、一个正的可计算粘性、从静止开始的流体、一个指定的流体粒子，以及一个固定的开区域（"探测器"）。对任意给定的图灵机和输入，可以写出一个光滑外力的有限"程序"，使这个粒子进入探测器**当且仅当**这台图灵机停机。停机问题不可判定，所以"这个粒子会不会到达那里"这个可达性问题也**不可判定**。

**论文自己说得很坦白** [P]："There is an elementary way to force a chosen smooth incompressible velocity: subtract its viscous term from its material acceleration. The mathematical work lies in choosing that velocity from the finite instruction table." 这就是§11.6.2 的"残差外力"技巧：想要什么流，就让外力补差。真正的工作在于设计这个流：它要逐条执行指令，保留可逆所需的信息，并且在不停机的运行中始终碰不到探测器。论文也写明，它"not a regularity theorem for general Navier–Stokes data"。

**和 Tao 纲领（§11.4.4）的关系**（我们的判断）：它让人想到 Tao 2016 的纲领，即让流体**自己**搭出计算机，把能量一次次传给更小的自身副本，从而爆破。但 376 把"编程"放在外力里，外力承担了全部编程工作，所以它**不推进**那条无外力爆破纲领，更接近"受迫流体的可控性 / 不可判定性"一类结果。截至 2026-10-09，仓库里这一族列出的 9 篇预印本全文都没有引用 Tao 2016 [P]。它引用的前驱是 Cristopher Moore 的广义移位（1990–91）、Bennett 的可逆计算（1973），以及 Cardona–Miranda–Peralta-Salas–Presas 在调整过度量的 3 维球面上构造的图灵完备定常 Euler 流（PNAS 2021）[P]。

**Lean** [P]：`lean/docs/376.md` 列出 6 个 Comparator 陈述，覆盖其中 4 篇预印本的选定结论，其中包括 ℝ³ 上的版本：一个光滑、紧支撑的流动，从静止出发，位于 (4,0,0) 的粒子进入固定开盒 (−1,2)³ 当且仅当机器停机。覆盖范围逐篇不同，例如 *Geometric Programs for Solenoidal Forcing* 一文的固定粒子停机检测器明确不在形式化范围内。⚠ 我们没有逐个读这 6 个陈述文件，也没有编译。

---

## 11.8 它被核实到什么程度

### 11.8.1 Lean 陈述：题面不是 OpenAI 写的

题面文件 `ComparatorChallenges/NavierStokes.lean` 开头写明，它复制自 **Google DeepMind 的 Formal Conjectures 项目**（commit `8bf45ed`），只改了 import、命名空间和记号 [P]。题面若由求解方自己写，就可能悄悄放宽条件；这里出自第三方。⚠ 我没有逐行 diff 上游。

分支 (C) 的陈述：

```lean
theorem navier_stokes_breakdown_R3 (nu : ℝ) (hnu : nu > 0) :
    ∃ (u₀ : ℝ³ → ℝ³) (f : ℝ³ → ℝ → ℝ³),
    InitialVelocityConditionDecay u₀ ∧ ForceConditionDecay f ∧
    ¬ (∃ v p, NavierStokesExistenceAndSmoothnessRn nu u₀ f v p)
```

逐词翻译：
- `(nu : ℝ) (hnu : nu > 0)`：对任意正的粘性 ν，
- `∃ (u₀ …) (f …)`：存在初值 u₀ 和外力 f，
- `InitialVelocityConditionDecay u₀`：u₀ 光滑、散度为 0、所有导数快速衰减（Clay 条件 4），
- `ForceConditionDecay f`：f 光滑，所有时空导数 ≤ C/(1 + |x| + t)^K（条件 5），
- `¬ (∃ v p, …)`：使得**不存在** v、p 同时满足 NS (1)、散度为 0 (2)、初值 (3)、C^∞ (6)、能量一致有界 (7)。

我逐条对过 Clay 原文：(4)–(7) 全在；周期版 (D) 含 (8)–(11)，并按 Clay 勘误要求压力也周期 [P]。**题面结构与 Clay (C)/(D) 一致**。注意 (C) 要的是"**不存在**任何整体光滑解"，不只是"我造的解会爆"；这需要光滑解的唯一性（Theorem 1.1 的 "Consequently…" 一句），Lean 里也证了。

### 11.8.2 证明本身

- 仓库 `openai/NavierStokesAndEuler`（快照 `f9e8bc5`，2026-09-10）：**2,659 个 `.lean` 文件**（NS 816、Euler 1,839）[P]，约 64 万行（作者研究笔记的统计）。
- `formalization.yaml`：sorry 数 0，只用 `propext`、`Classical.choice`、`Quot.sound` 三条标准公理；Comparator 开启 `enable_nanoda`，即再用一个独立实现的内核检查 [P]。review 状态写的是 **"self-assessed"**（自评）。
- ⚠ 我没有运行 `lake build` 或 Comparator，也没找到第三方公开跑通 NS Comparator 的报告（§4 的准黎曼猜想有 Goldblatt 的独立复核）。

### 11.8.3 人类专家和机构

- **Clay**（09-11，主席 Martin Bridson）[R]：据报道称 "the Navier–Stokes problem has apparently been settled"，同时评估会 "deliberately unhurried"（原句 "The process is deliberately unhurried, but we will provide updates"）。Clay 仍把 NS 列为未解决：官网问题页截至今天仍标 "Active"（我 10-08 核对过）。Clay 规则要求在合格刊物发表，再加两年接受期（§11.9.1）。
- **Gómez-Serrano**（NPR，09-22）[R]："The paper is not written for humans … as of today, the paper doesn't teach us much."
- **Fefferman** [R]："The heroes of the story … are Córdoba and Martínez-Zoroa." ⚠ 未找到原始出处。
- ⚠ **截至 2026-10-08，没有任何人类专家公开表示读完并核实了这 166 页论文**，也没有期刊投稿的报道。

### 11.8.4 优先权争议（简述）

- **Buckmaster 的声明**（https://cims.nyu.edu/~tristanb/statement.pdf）[P]：Buckmaster（NYU）和 Alpöge 8 月 15 日得到光滑外力下的 Boussinesq 和 3D Euler 爆破，8 月 22 日 Lean 验证，9 月 7 日（美东时间）连同 IPM 的结果一起公开。声明原文只写 "Today"；9 月 7 日据 Wikipedia [R]，声明 PDF 的元数据是 2026-09-08 02:38 UTC，即美东 9 月 7 日晚 [P]，按 UTC 算是 9 月 8 日。他们也大量用了 LLM（Claude、Codex）。他把路线的功劳归于 Córdoba 和 Martínez-Zoroa。关于 OpenAI，他叙述 9 月 6 日通话中"Eventually it was agreed that [the first prompt] had been sent in the past few days, after information about our work had reached OpenAI"，同时写明 "I am not accusing anyone of anything."
- **OpenAI 的回应** [R]："it is impossible for Dr. Buckmaster's Codex prompts over the last two months to have influenced the system in any way"。
- **双方说法不一** ⚠：Buckmaster 的叙述是，OpenAI 在他们的进展传到 OpenAI 之后才发出第一条提示词；OpenAI 否认的是他的 Codex 提示词影响过系统。两者针对的问题并不相同（一个关于时间先后，一个关于他们的用户数据是否被用到），目前都没有第三方核实。
- **引用** [P]：我读的 PDF（生成于 09-08 12:06 PDT）**已经引用** Córdoba–Martínez-Zoroa 的三篇工作 [6–8]；**没有引用** Buckmaster–Alpöge。

### 11.8.5 剩余风险

1. **Mathlib 定义**：Laplacian、gradient 等来自 Mathlib，"垃圾值约定"可能让陈述偏离原意；但题面要求处处 C^∞，影响很小。
2. **工具链**：Lean 4.34.0-rc2 是预发布版本 [P]；nanoda 双内核降低了风险。
3. **人类理解**：没人能说清这个方法能否推广到无外力情形。

---

## 11.9 如果为真，意味着什么（以及不意味着什么）

### 11.9.1 按 Clay 的文本，这算不算"解决了千禧年问题"？

分三层回答。

**第一层：题面。算。** 官方文本"we ask for a proof of one of the following four statements"，(C) 是其中之一 [P]。奖金规则第 5(b) 条还写明："In the case of the P versus NP Problem and the Navier-Stokes Problem, a resolution in either direction will be evaluated by the standard evaluation procedure" [P，https://www.claymath.org/wp-content/uploads/2022/03/millennium_prize_rules_0.pdf]。两个方向同等有效。

**第二层：奖金程序。还差得远。** 规则第 4 条要求同时满足 [P]：
- (a) 发表在"合格刊物"上（目前没有投稿报道 ⚠）；
- (b) 发表后至少过去 **2 年**；
- (c) 在全球数学界获得"general acceptance"，由 CMI 自行判断；
- (d) 令人满意地回答了官方题面提出的问题。

之后 CMI 还要组成至少 3 人的委员会审查（第 7 条）。第 8(b) 条：CMI 会"pay special attention to the question of whether a Prize solution depends crucially on insights published prior to the solution"，可以把前人列入获奖名单，这对 Córdoba–Martínez-Zoroa 和 Buckmaster–Alpöge 直接相关。第 8(c) 条：对正确性或**归属**无法下结论时，可以不授奖。另据报道 OpenAI 表示不申领奖金 [R]。推测：即使明年发表，按"发表后 2 年"，最早也要 2029 年前后才有结论。

**第三层：数学界关心的问题。大多数人会说没有。** "流体自己会不会爆"仍然完全开放。OpenAI 的结果没有回答无外力情形，也没有实现 Tao 的纲领（§11.4.4；§11.7.5 的 family 376 也没有）。

**"规格博弈"的说法要小心。** 很容易把这件事比作 AI 里的规格博弈（specification gaming）：满足了题目的字面要求，却没回答提问者真正关心的问题。但这不是作弊：Fefferman 在 2000 年是**有意**放入 (C) 的，认为它 "retaining the heart of the problem"（§11.6.1）。更准确的说法是：**出题人当年认为 (C) 和 (A) 一样难，2023 年以后的进展表明外力路线比预想的好走**。题面和意图的差距是事后显现的，不是求解方钻了出题人没想到的空子。

### 11.9.2 对数学、物理和 AI

1. **数学**：如果成立，这是第一个光滑外力、全空间、C^∞ 设定下的 NS 爆破：粘性不是万能的。同时发布的无外力 Euler 爆破（7.4 节）如果成立，可能是更大的消息。方法上，用振荡脉冲的二次通量"合成"所需应力，和 Euler 凸积分（Daneri–Székelyhidi）有亲缘关系，论文自己也这么说 [P]。
2. **物理和工程**：对天气预报、湍流模拟和工程几乎没有直接影响。NS 求解器从不依赖整体光滑性定理；真实流体在接近奇点前，分子尺度就让连续介质模型失效。结论是"**模型本身**在人为设计的外力下会坏"，不是"真实的水会出现无穷大速度"。
3. **AI**：三道独立的闸门：形式化通过 ≠ 题面忠实 ≠ 数学界接受。这里第二道因为用了第三方题面而比较可靠，第三道还远没走完。Buckmaster 说 LLM 让一个数学家加一个模型"can now do all this work in a month"，称之为"a Deep Blue-Kasparov moment" [P]。当 AI 实验室能在听到某个方向有进展后迅速投入大量算力，优先权和署名规范该怎么适应，是一个现实问题。

---

## 11.10 自测题

1. 用一句话说明：为什么 y' = y² 会在有限时间爆破，而 y' = y 不会？（§11.3.1）
2. NS 方程里哪一项是非线性的？它的物理意义是什么？（§11.2.3）
3. 为什么说 3D NS 的能量是"超临界"的？用缩放 λ = 1000 的数字说明。（§11.4.2–11.4.3）
4. Clay 的 (A) 和 (C) 在"外力"和"量词（任意/存在）"上分别有什么不同？（§11.6.1）
5. 为什么"可以自己挑外力"并不让问题变得平凡？关键的困难是什么？（§11.6.2）
6. OpenAI 的 Lean 题面是谁写的？为什么这一点重要？（§11.8.1）
7. 按 Clay 规则，从现在到可能颁奖，至少还要经过哪几步？（§11.9.1）
8. family 376 的流体"计算机"为什么不推进 Tao 的无外力爆破纲领？（§11.7.5）

---

## 附：【检查】答案

- **检查 1**：`[0, 0.0625, 0.25, 0.375, 0.25, 0.0625, 0]`，总和 1（脚本核对）。例如中间：0.5 + 0.25·(0.25 − 1 + 0.25) = 0.375。
- **检查 2**：∇·(−y, x) = ∂(−y)/∂x + ∂x/∂y = 0 + 0 = 0，不可压缩。∇·(x, y) = 1 + 1 = 2 ≠ 0：w 是从原点向外"喷"的流，每个小区域都在净流出，体积在膨胀。
- **检查 3**：(a) u = (−y, x) 的每个分量都是一次函数，二阶导数全为 0，所以 Δu = 0：刚体旋转没有剪切，粘性不起作用。(b) 由 2.3 节，(u·∇)u = (−x, −y)，所以 ∇p = (x, y)，p = (x² + y²)/2 + 常数。**边缘高、中心低**：压力差从外往里推，提供向心力。OpenAI 论文描述涡核时说的 "Pressure decreases toward the axis, supplying the leading centripetal force" 就是这件事。
- **检查 4**：2 维中 dx = dy/λ²，能量因子 λ²/λ² = 1。
- **检查 5**：不能。y' ≤ −y + 1 且 y(0) = 0，可以推出 y ≤ 1 − e^(−t) < 1；同理 y ≥ −1。线性方程配有界外力，解一直有界。
- **检查 6**：∂u_ν/∂t = √ν·∂u/∂t。(u_ν·∇)u_ν：速度因子 √ν × √ν，导数 ∇ 作用在 x/√ν 上带来 1/√ν，合计 √ν。νΔu_ν：ν × √ν × (1/√ν)² = √ν。三项一致。

## 附：术语表

| 术语 | 一句话解释 |
|---|---|
| ODE / PDE | 未知量是一个随时间变化的数 / 一整个场 |
| 热方程 | ∂u/∂t = kΔu，每个点向邻居平均值靠拢，只会使东西变平滑 |
| 散度 ∇·u | 小区域里的净流出；= 0 表示不可压缩 |
| 物质导数 | ∂u/∂t + (u·∇)u，一小团流体自身的加速度 |
| 粘性 νΔu | 相邻流层互相拖拽，数学上是速度的热方程 |
| 雷诺数 Re | UL/ν，非线性与粘性的强弱之比 |
| 弱解 | 只在积分平均意义下满足方程的解，允许奇点（Leray 1934） |
| 缩放对称性 | u_λ = λu(λx, λ²t) 仍是解 |
| 超临界 | 守恒量（能量）在小尺度上越来越管不住 |
| 涡拉伸 | 涡管被拉长变细、转得更快，3D 才有 |
| Euler 方程 | ν = 0 的 NS，无粘性流体 |
| Clay (A)–(D) | 千禧年问题的四个可选表述，证出任一即可 |
| 不可判定 | 没有任何算法能对所有输入都给出正确的是/否答案；图灵机停机问题是典型例子 |

## 附：想继续深入

- **Clay 官方题面**（Fefferman，5 页，强烈推荐全文读）：https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf
- **Clay 奖金规则**：https://www.claymath.org/wp-content/uploads/2022/03/millennium_prize_rules_0.pdf
- **OpenAI NS 论文**：https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf （先读第 1–2 节，约 6 页，几乎不需要 PDE 背景）
- **OpenAI Euler 论文**：https://cdn.openai.com/pdf/315b36cd-ec98-4023-8342-93345194ece1/euler.pdf
- **Lean 仓库**：https://github.com/openai/NavierStokesAndEuler ；题面上游：https://github.com/google-deepmind/formal-conjectures/blob/main/FormalConjectures/Millenium/NavierStokes.lean
- **Buckmaster 声明**：https://cims.nyu.edu/~tristanb/statement.pdf
- **family 376**（受迫 NS 中的通用计算）代表作：https://github.com/openai/math/blob/main/preprints/A-Fixed-Particle-Test-for-Computation-in-a-Forced-Viscous-Flow-September-27-2026/manuscript.pdf ；Lean 范围说明：https://github.com/openai/math/blob/main/lean/docs/376.md
- **Terence Tao**，arXiv:1402.0290（JAMS 2016）引言讲清了"超临界屏障"；更通俗的是他的博客 *Why global regularity for Navier-Stokes is hard*（2007）。
- **DeepMind 等**，*Discovery of Unstable Singularities*，arXiv:2509.14185
- **Chen & Hou**，*Stable nearly self-similar blowup of the 2D Boussinesq and 3D Euler equations with smooth data I: Analysis*，arXiv:2210.07191
- **Córdoba & Martínez-Zoroa**，*Blow-up for the incompressible 3D-Euler equations with uniform C^{1,1/2−ε} ∩ L² force*，arXiv:2309.08495
- **Bertozzi & Majda**，*Vorticity and Incompressible Flow*（剑桥，2002）：Fefferman 题面推荐的教科书。
- 二手报道（未逐字核对）：Quanta 2026-09-08 https://www.quantamagazine.org/ai-has-solved-one-of-maths-1-million-millennium-prize-problems-20260908/ ；Wikipedia "Navier–Stokes priority controversy" https://en.wikipedia.org/wiki/Navier%E2%80%93Stokes_priority_controversy ；Clay 09-11 声明转述 https://the-decoder.com/clay-mathematics-institute-says-the-navier-stokes-millennium-prize-problem-has-apparently-been-settled/ ；Implicator https://www.implicator.ai/clay-institute-navier-stokes-openai-proof-claim/
