# AI x Cyber 极端风险与防线 — 研究底稿 + 来源可信度标记（2026-09-29）

> 这是 deck §10-§13（AI safety 视角层）背后的原始研究底稿，来自 5 路并行调研。deck 正文已把承重结论 + 行内来源写进去了；本文额外保留 **(a) 被标为"未独立核实"的条目**、**(b) 没塞进 deck 的数字/细节**、**(c) 怀疑论的更完整版本**——方便 LY 自己 fact-check 和深挖。
> 用法：deck 是给读者的成品；本文是给你的"带脚注的实验记录"。凡标 ⚠️ 的都请引用前再核一遍。

---

## A. 极端风险的概念脊柱（deck §10）

**四驱动力 + 提出者**
- 规模化自主攻击：GTG-1002（80-90% 自主，机器速度）→ [Anthropic](https://www.anthropic.com/news/disrupting-AI-espionage)；[IAPS 自主网络攻击](https://www.iaps.ai/research/autonomous-cyber-attacks)。MITRE 已编号 **C0062**（[attack.mitre.org/campaigns/C0062](https://attack.mitre.org/campaigns/C0062/)）。
- 攻防平衡 / AI Security Gap：**Dan Braun（Apollo Research）** 2025-01-08 [LessWrong](https://www.lesswrong.com/posts/gG4EhhWtD2is9Cx7m/implications-of-the-ai-security-gap)——"sabotage 比 theft 容易；对齐的 AGI 反而更好打"。相关：[The Dual-Use Gap](https://www.lesswrong.com/posts/CRfwCQcALQ2HpCkgj/the-dual-use-gap)；CSET [攻防平衡](https://cset.georgetown.edu/publication/anticipating-ais-impact-on-the-cyber-offense-defense-balance/)；["Uplifted Attackers, Human Defenders" arXiv:2508.15808](https://arxiv.org/abs/2508.15808)。⚠️ 反方（AI 利防守）："Deception and Detection", *International Security*（[MIT Press](https://doi.org/10.1162/ISEC.a.398)）——作者名未从摘要确认。
- 作为失控机制：**Redwood** [AI Control](https://www.redwoodresearch.org/research/ai-control)；Buck Shlegeris 区分 self-exfiltration vs **rogue internal deployment**（[blog](https://blog.redwoodresearch.org/p/ai-catastrophes-and-rogue-deployments)）；weight-upload limits（[blog](https://blog.redwoodresearch.org/p/preventing-model-exfiltration-with)）。IST **Loss of Control I&W**（2026-02，0-5 级）：[报告](https://securityandtechnology.org/virtual-library/report/ai-loss-of-control-risk-indications-warning/)。⚠️ **Ajeya Cotra** 说 OpenAI×HF ">50% of the way to full takeover"——一手出处未独立核实，经 [Redwood 二手](https://blog.redwoodresearch.org/p/are-we-existentially-threatened-by) 引用。
- 扩散：Anthropic 2026-09 "sophistication 不再是信号"（[报告](https://www.anthropic.com/threat-intelligence-report-september-2026)）；PentAGI 等公开框架。

**关键基础设施**：Anthropic FRT × PNNL 水厂模拟（[red.anthropic.com](https://red.anthropic.com/2026/critical-infrastructure-defense)）；Logan Graham 2025-12 众院国土安全作证（[PDF](https://www.congress.gov/119/meeting/house/118723/witnesses/HHRG-119-HM08-Wstate-GrahamPhDL-20251217.pdf)）。

**怀疑论（更完整版）**：**James Lewis (CSIS)《Dismissing Cyber Catastrophe》**（[CSIS](https://www.csis.org/analysis/dismissing-cyber-catastrophe)）——25 年没有一次灾难级、没人死于网络攻击、经济有韧性、核类比"智识偷懒"。GTG-1002 无 IoC（[BleepingComputer](https://www.bleepingcomputer.com/news/security/anthropic-claims-of-claude-ai-automated-cyberattacks-met-with-doubt/)；[CSO](https://www.csoonline.com/article/4092571/ai-controlled-cyber-attack-causes-a-stir.html)）。Intl AI Safety Report 2026："not yet fully autonomous"（[arXiv:2602.21012](https://arxiv.org/abs/2602.21012)）。

**定位**：cyber = 灾难级非生存级（除非经两桥）；Bengio "cyber 当下/bio 上限更高"（[Transformer](https://www.transformernews.ai/p/yoshua-bengio-the-ball-is-in-policymakers-international-ai-safety-report-cyber-risk-biorisk)）；[AI Risk Spectrum arXiv:2508.13700](https://arxiv.org/abs/2508.13700)。

**⚠️ 一个值得记的空白**：没有哪个组织"之于 cyber 相当于 SecureBio 之于 bio"——功能分散在 Berkeley RDI（评测）/RAND（weights）/IST（LoC）/lab FRT（能力披露）。这个空白本身是 misuse 岗可以提的 observation。

---

## B. 能力测量（deck §11）

**基准**：Cybench（[2408.08926](https://arxiv.org/abs/2408.08926)）；NYU CTF（[2406.05590](https://arxiv.org/abs/2406.05590)）；CVE-Bench（[2503.17332](https://arxiv.org/abs/2503.17332)，UIUC，US AISI 有贡献）；**CyberGym**（1,507 真实漏洞、35 个 0-day，[RDI](https://rdi.berkeley.edu/blog/cybergym/)）；⚠️ **ExploitGym**（898 实例，[arXiv:2605.11086](https://arxiv.org/abs/2605.11086)）——URL 搜索返回但未逐一重解析；SCONE-bench（[red.anthropic.com](https://red.anthropic.com/2026/exploit-evals/)）。⚠️ **AgentCyberRange**（[2606.14295](https://arxiv.org/pdf/2606.14295)）未核实。

**政府评测**：UK AISI **~4.7 月翻倍**（2026-02，比 2025-11 的 8 月更快；自承不确定，最长跨度只靠 6 题）——**已直接 fetch 核实**（[AISI](https://www.aisi.gov.uk/blog/how-fast-is-autonomous-ai-cyber-capability-advancing)）。开源落后 4-7 月（[AISI](https://www.aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber)）。CAISI：GLM-5.3 落后 ~4 月，⚠️ 具体分数表（ExploitGym 9.4% vs 44.4% 等）来自 [CAISI](https://www.nist.gov/news-events/news/2026/09/caisis-assessment-zais-glm-53-cyber-capabilities)，美国模型是关防护对比。CAISI 自有基准：**CTF-Archive-Diamond（285 题）、PortBench**。METR cyber ranges（Mythos 首个完成两个 range：32 步 6/10、7 步 ICS 3/10，[Obsidian 转述](https://www.obsidiansecurity.com/blog/what-frontier-ai-models-can-do-in-a-cyber-attack)）。

**真实能力现状**：Google **Big Sleep** 找到真实 0-day（CVE-2025-6965 等 20+，[TNW](https://thenextweb.com/news/google-ai-zero-day-exploit-cybersecurity-arms-race)）；GTIG 2026-05 披露**首例犯罪用 AI 开发的 0-day**（[CSO](https://www.csoonline.com/article/4169046/google-discovers-weaponized-zero-day-exploits-created-with-ai.html)）；Anthropic SCONE：405 合约 51.11%、模拟 $550.1M；截止后子集 19 攻击/$4.6M（[red.anthropic.com](https://red.anthropic.com/2026/exploit-evals/)）。XBOW #1 HackerOne US（[XBOW](https://xbow.com/blog/top-1-how-xbow-did-it)）。⚠️ "DepthFirst 基准"未找到——别当实锤。

**两个测不到**：novice uplift（RAND "触手可及于新手"，[RRA3892-2](https://www.rand.org/pubs/research_reports/RRA3892-2.html)）vs **APT uplift 几乎无阈值**（[FMF](https://www.frontiermodelforum.org/technical-reports/managing-advanced-cyber-risks-in-frontier-ai-frameworks/)）；eval 容器可被攻破（OpenAI×HF）。方法学：污染、test-time compute elicitation（[AISI](https://www.aisi.gov.uk/blog/more-compute-more-capability-why-ai-agent-evals-need-to-account-for-test-time-compute)）。

---

## C. 实验室防线（deck §12）

**逐家**（primary 文档已直接读）：
- Anthropic **RSP v3.0 里 "cyber" 零次出现**（[v3.0](https://www.anthropic.com/responsible-scaling-policy/rsp-v3-0)）——⚠️ v2.x→v3.0 的"降级"是研究员对原文的重构判断，deck 里已标脚注。ASL-3 分类器是 CBRN 不是 cyber。⚠️ "flagged cyber 请求路由到弱模型"——未对原报告核实。
- OpenAI Preparedness v2（[PDF](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf)）；GPT-5.5 公开定 High cyber（[deploymentsafety hub](https://deploymentsafety.openai.com/gpt-5-5/cybersecurity)）；⚠️ 首个 Critical = **"Astra"**（2026-09，[CNBC](https://www.cnbc.com/2026/09/01/open-ai-astra-cyber-model.html)；openai.com/index 页对抓取器 403，靠搜索快照+CNBC）；Trusted Access + GPT-5.x-Cyber 低拒答微调（[Trusted Access](https://openai.com/index/trusted-access-for-cyber/)；[GPT-5.6-Cyber VentureBeat](https://venturebeat.com/technology/openai-launches-gpt-5-6-cyber-with-reduced-refusals-95-completion-on-advanced-cybersecurity-tasks)）；Aardvark（[openai](https://openai.com/index/introducing-aardvark/)）。
- GDM **FSF 3.1**（2026-04，[PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/strengthening-our-frontier-safety-framework/frontier-safety-framework_3-1.pdf)）：一个 cyber CCL（uplift）→ SL2+；"防守适应"是不设更高级的理由；⚠️ 3.1 无独立 "cyber autonomy" CCL。
- Meta AASF v2（⚠️ 阈值措辞来自 [二手分析](https://frontierrisk.substack.com/p/metas-advanced-ai-scaling-framework)）；xAI FAIF（[PDF](https://media.x.ai/v1/website/xai-frontier-artificial-intelligence-framework-30-june-2026-99c40684.pdf)，定性无数字）；Z.AI GLM-5.3 分阶段+OpenVuln（[VentureBeat](https://venturebeat.com/technology/glm-5-3-is-here-with-advanced-cyber-capabilities-and-reportedly-already-found-a-serious-vulnerability-in-cursor)）。
- ⚠️ NSA/FBI/CISA **AA26-251A**（2026-09-08）指六家中国 lab 工业级蒸馏（[CISA](https://www.cisa.gov/news-events/cybersecurity-advisories/aa26-251a)）——注意：这是"蒸馏/窃取"议题，混进 misuse 表要小心（协调毒药）。⚠️ DeepSeek-V4 越狱 98-100% 合规——仅二手。

**通用技术 + 脆性**：abliteration 单方向剥 refusal（[the-decoder](https://the-decoder.com/stripping-safety-guardrails-from-open-weight-ai-models-is-now-a-turnkey-commercial-service/)）；TAR/SEAM 被破（[2605.26526](https://arxiv.org/abs/2605.26526)）；jailbreak-tuning ~97-99%（[2507.11630](https://arxiv.org/pdf/2507.11630)）；[Safety Gap Toolkit 2507.11544](https://arxiv.org/pdf/2507.11544)。**为什么比 bio 难**：FMF + Intl AI Safety Report 2026（双用途/自动化/演化/开源扩散）。

---

## D. 治理（deck §13）— 关键纠错已进 deck

**美国**：EO 2026-06-02（联邦 binding/业界自愿，[White House](https://www.whitehouse.gov/presidential-actions/2026/06/promoting-advanced-artificial-intelligence-innovation-and-security/)）——⚠️ "EO 14409" 是第三方编号，白宫原文无号，引用用日期。CAISI（[NIST](https://www.nist.gov/caisi)，5 lab 预部署协议）。CISA/NSA/FBI 西门子 PLC 公告（[The Record](https://therecord.media/nsa-fbi-warns-of-hackers-using-ai-generated-tools-critical-infrastructure)）。SB 53（binding，2026-01；权重被盗 + 协助攻击关键基础设施=灾难风险，[bill](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB53)）。⚠️ **Todd Young 是信件不是法案**，框架是进攻 cyber/国安不是 RSI。⚠️ **AI OVERWATCH Act = 芯片出口管制，不是 cyber 能力法**。FRONTIER Act / Romney 框架 = 未成法。
**EU**：AI Act Art.55（binding，2026-08 可罚；模型+基础设施安全、自我渗出、5 天报告，[Art.55](https://artificialintelligenceact.eu/article/55/)）；GPAI Code of Practice 安全章（自愿路径）。
**英国**：⚠️ **AISI 更名是 2025-02 不是 2024**（Safety→Security，[议会声明](https://questions-statements.parliament.uk/written-statements/detail/2025-02-24/hlws454)）。⚠️ CAISI-AISI "联合" 更像平行/协调，不一定是单一联合文件。
**多边**：IDAIS 伦敦 2026（cyber 阈值→有约束力法律契约，[idais.ai](https://idais.ai/dialogue/idais-london/)）；Seoul 2024 含 cyber 阈值；[Global Call for AI Red Lines](https://red-lines.ai/)（目标 2026 底，200+ 签署）；G7 广岛准则；[Intl AI Safety Report 2026](https://internationalaisafetyreport.org/)。

**中国**：Framework 3.0（2026-09-14，指南；54 风险；cyber 四子风险，[CAC](https://www.cac.gov.cn/2026-09/14/c_1791137092283345.htm)，⚠️ 逐条文本来自 [aisafetychina Brief #29](https://aisafetychina.substack.com/p/brief-29-what-chinas-new-ai-safety) 等二手，未提取 136 页 PDF 原文）。王丽宏五风险（2026-09-01，[geopolitechs](https://www.geopolitechs.org/p/the-five-biggest-ai-risks-according)）。Qinglang = 内容/备案执法非能力层。Z.AI GLM-5.3 分阶段（⚠️ $10B MaaS 门槛 + CyberGym 分数来自二手博客）。SafeWork/周伯文 AI-45°（[shlab](https://www.shlab.org.cn/news/5443947)）。Concordia Frontier Risk Monitor：cyber 指数 YoY **4.4×**（[airiskmonitor](https://airiskmonitor.net/doc/en/about)）。
**US-China**：趋同（agent 逃逸、非国家滥用、事件通报）；2026-09 **Bessent–何立峰**事件通报渠道（[CNBC](https://www.cnbc.com/2026/09/05/us-china-gear-up-for-mid-september-ai-safety-talks-reuters.html)）。⚠️ "Carolina Principles" 仅单一来源（Eastern Herald），未核实。分歧：阈值主权、开源哲学、技术霸权/出口管制。

---

## E. 给 deck 之后的开放问题（值得继续追）

1. ~4.7 月翻倍是否稳定？Mythos/GPT-5.5 是否把它往上打破？（AISI 自己不确定）
2. 没有任何验证过的 **APT 层 uplift** 基准——misuse 研究的真空。
3. OpenAI×HF 之后，**eval containment** 成了一级测量问题。
4. **"cyber 界的 SecureBio"缺位**——是否该有一个专门的非营利 cyber 能力观测台？
5. 出口管制/蒸馏议题（AA26-251A）如何不污染 misuse 协调桌。

---

_研究执行 2026-09-29，5 路并行子代理，每路都被要求标注未核实项。凡 ⚠️ 者引用前请再核。字段与 deck §10-§13 一一对应。_
