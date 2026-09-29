# Cyber -> AI x Cyber fundamentals - from a beginner's map to extreme risk & safeguards

Part I (§1-§9) is a sourced primer taking you from zero cybersecurity background to literacy in
"AI x Cyber": core infosec vocabulary and standard frameworks (CIA triad, OWASP/CWE, CVE/CVSS/NVD,
MITRE ATT&CK, NIST incident-response lifecycle), then the two real 2025-2026 incidents where AI and
cyber actually intersected - Anthropic's disclosed AI-orchestrated espionage campaign (GTG-1002) and
the ExploitGym/OpenAI x Hugging Face incident - plus where AI-for-defense and AI-model-weights
security stand.

Part II (§10-§13) adds an **AI-safety lens** on cyber misuse and extreme risk: why AI x cyber is a
class of "extreme risk" (the conceptual spine, the honest skeptic case, and its placement on the
catastrophic-vs-existential ladder), how cyber capability is measured (the benchmark ladder, UK
AISI's capability-doubling estimate and its caveats, the novice-vs-APT blind spot), how frontier
labs handle cyber misuse (the RSP/Preparedness/FSF comparison, the shift from "refuse cyber" to
"KYC/trusted-access + accelerate defenders," and why cyber is harder to safeguard than bio), and the
US/China/other governance map by force-of-law.

## Read

- **[`notes.pdf`](notes.pdf)** / **[`notes.html`](notes.html)** - English edition (start here)
- **[`notes_zh.pdf`](notes_zh.pdf)** / **[`notes_zh.html`](notes_zh.html)** - Chinese edition (the author's primary study-notes language; content matches the English edition section-for-section, maintained in parallel rather than auto-translated)
- **[`reports/Anthropic_2025-11_GTG-1002_full_report.pdf`](reports/Anthropic_2025-11_GTG-1002_full_report.pdf)** - the primary source for the GTG-1002 case, saved here for traceability.

> The decks occasionally point to fuller `deep_reads/…` notes (a line-by-line GTG-1002 case study and the research memo behind Part II, with every source-confidence flag). Those are the author's private working notes and are **not published in this repo** — the decks themselves are self-contained, and every claim in them carries its own inline primary source.

## Hands-on labs (`labs/`)

Where the decks stay at literacy level, these turn abstract attacks into runnable, reproducible code.
Each lab focuses on one core tool / vulnerability class, ships real captured output under `output/`,
and runs entirely against a self-built target on an isolated Docker network — a sandboxed,
authorized learning environment; all credentials are fake.

- **[`labs/ssrf_killchain/`](labs/ssrf_killchain/)** — **SSRF kill-chain** (tools: nmap, curl, Python). Makes the GTG-1002 case study's "Task 1-5" table concrete: a three-service Docker target (a public SSRF-vulnerable web app, an unauthenticated internal admin API with no host port, and a fake cloud-metadata endpoint) reproduces the **Capital One 2019** pattern — SSRF → internal service enumeration → cloud IAM credential theft — with each phase mapped 1:1 onto GTG-1002's tasks and an out-of-band callback verifier.
- **[`labs/sqli_lab/`](labs/sqli_lab/)** — **SQL injection** (tool: **sqlmap**). A deliberately injectable "book search" app (SQLite backend, string-concatenated query). Shows the injection by hand (UNION-reading a hidden `users` table), then with sqlmap, which detects the injection, enumerates the schema, dumps the table, and auto-cracks the md5 password hashes. Includes the one-line parameterized-query fix.
- **[`labs/metasploit_cve_lab/`](labs/metasploit_cve_lab/)** — **known-CVE exploitation** (tool: **Metasploit**). A real vulnerable target, Apache Struts2 **S2-045 / CVE-2017-5638** (the vulnerability class behind the 2017 Equifax breach): recon with nmap, prove RCE by hand via an OGNL header injection (the command runs as **root**), then confirm the CVE independently with the Metasploit module's `check`.

## Rebuild

```bash
python3 build_notes_en.py   # -> notes.html (English)
python3 build_notes.py      # -> notes_zh.html (Chinese)
# then print HTML -> PDF, e.g. Chrome headless:
# google-chrome --headless --disable-gpu --no-pdf-header-footer \
#   --print-to-pdf=notes.pdf "file://$(pwd)/notes.html"
```

Depends on: `_notes_base.css`.

## Scope

**This is a reading/orientation primer, not a hands-on-skill project.** It says so explicitly in
its own opening section: sufficient to read a CVE writeup, a pentest report, or an AI x cyber
paper without being lost; not sufficient for actual exploit-writing or penetration-testing skill,
which the deck's own closing section points toward (picoCTF -> OverTheWire -> TryHackMe ->
HackTheBox, CompTIA Security+ -> OSCP).

Every claim about a specific benchmark, incident, or organization was checked against a primary
source before being included. Two corrections worth flagging: the ExploitGym/CVE-Bench naming
conflation common in secondary sources (they're different benchmarks), and the "single agent,
months of work" framing of Anthropic's smart-contract exploit study (it's a cross-model benchmark
result, not a single long-running agent).

## License

MIT (same as parent repo).
