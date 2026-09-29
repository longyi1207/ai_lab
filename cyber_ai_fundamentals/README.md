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

## Hands-on lab (`labs/`)

Where the decks stay at literacy level, this turns the abstract attack phases into runnable code:

- **[`labs/ssrf_killchain/`](labs/ssrf_killchain/)** - a self-contained **SSRF kill-chain lab** that makes the GTG-1002 case study's "Task 1-5" table concrete. A three-service Docker target on an isolated network (a public SSRF-vulnerable web app, an unauthenticated internal admin API with no host port, and a fake cloud-metadata endpoint) reproduces the **Capital One 2019** pattern: SSRF -> internal service enumeration -> cloud IAM credential theft. Every phase maps 1:1 onto GTG-1002's tasks, uses real tooling (nmap, curl, Python), includes an out-of-band callback verifier (the lab-scale analogue of the "neutral third-party callback service" GTG-1002 used to confirm exploits actually worked), and ships the captured real run output under `output/`. All credentials are fake; the whole thing runs in a sandboxed, self-authored, authorized learning environment. The README maps each step to GTG-1002, adds a defender's view, and links authoritative resources (PortSwigger Web Security Academy, HackTricks, OWASP, Capital One post-mortems).

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
