# Cyber -> AI x Cyber fundamentals - a from-zero primer

A sourced primer for going from zero cybersecurity background to literacy in "AI x Cyber":
core infosec vocabulary and standard frameworks (CIA triad, OWASP/CWE, CVE/CVSS/NVD, MITRE
ATT&CK, NIST incident-response lifecycle), then a full case study of the two real 2025-2026
incidents where AI and cyber actually intersected - Anthropic's disclosed AI-orchestrated
espionage campaign (GTG-1002) and the ExploitGym/OpenAI x Hugging Face incident - plus where
AI-for-defense and AI-model-weights security currently stand.

## Read

- **[`notes.pdf`](notes.pdf)** / **[`notes.html`](notes.html)** - English edition (start here)
- **[`notes_zh.pdf`](notes_zh.pdf)** / **[`notes_zh.html`](notes_zh.html)** - Chinese edition (the author's primary study-notes language; content matches the English edition section-for-section, maintained in parallel rather than auto-translated)
- **[`deep_reads/01_GTG-1002_Anthropic_2025-11_案例深读.md`](deep_reads/01_GTG-1002_Anthropic_2025-11_案例深读.md)** - a much fuller GTG-1002 case study than either deck has room for: Anthropic's complete six-phase task breakdown, the AI-hallucination-in-offensive-ops caveat, independent security researchers' skepticism (Kevin Beaumont, Daniel Card, Ali Alkhatib - the report published no IoCs), and Anthropic's September 2026 follow-up showing this operating model has since spread to at least five more named threat groups. Written in Chinese, but every source it cites is an English-language primary, linked inline.
- **[`reports/Anthropic_2025-11_GTG-1002_full_report.pdf`](reports/Anthropic_2025-11_GTG-1002_full_report.pdf)** - the primary source, saved locally for traceability.

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
