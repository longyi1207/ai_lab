# Cyber → AI x Cyber fundamentals — a from-zero primer

A sourced primer for going from zero cybersecurity background to literacy in "AI x Cyber":
core infosec vocabulary and standard frameworks (CIA triad, OWASP/CWE, CVE/CVSS/NVD, MITRE
ATT&CK, NIST incident-response lifecycle), then two real 2025–2026 cases where AI and cyber
actually intersected — Anthropic's disclosed AI-orchestrated espionage campaign (GTG-1002)
and the ExploitGym/OpenAI×Hugging Face incident — plus where AI-for-defense and AI-model-weights
security currently stand.

**Note on language:** the deck itself is written in Chinese (the author's primary language for
personal study notes); every factual claim is backed by an English-language primary source
(NIST, MITRE, CISA, FIRST.org, RAND, Anthropic, OpenAI, Hugging Face, UK AISI) linked inline, so
the sourcing is checkable even without reading the prose.

## Read

- **[`notes.pdf`](notes.pdf)** — print-ready deck
- **[`notes.html`](notes.html)** — same content, open locally

## Rebuild

```bash
python3 build_notes.py
# then print HTML → PDF, e.g. Chrome headless:
# google-chrome --headless --disable-gpu --no-pdf-header-footer \
#   --print-to-pdf=notes.pdf "file://$(pwd)/notes.html"
```

Depends on: `_notes_base.css`.

## Scope

**This is a reading/orientation primer, not a hands-on-skill project.** It says so explicitly in
its own §0: sufficient to read a CVE writeup, a pentest report, or an AI x cyber paper without
being lost; not sufficient for actual exploit-writing or penetration-testing skill, which the
deck's own closing section (§10) points toward (picoCTF → OverTheWire → TryHackMe → HackTheBox,
CompTIA Security+ → OSCP).

Every claim about a specific benchmark, incident, or organization was verified against a primary
source before being included (and in two cases — the ExploitGym/CVE-Bench name conflation, and
the "single agent, months" framing of Anthropic's smart-contract exploit study — corrected from a
looser secondary-source framing).

## License

MIT (same as parent repo).
