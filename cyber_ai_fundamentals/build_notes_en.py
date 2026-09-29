#!/usr/bin/env python3
"""Build notes_en.html — English edition of the Cyber -> AI x Cyber fundamentals deck."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSS = (ROOT / "_notes_base.css").read_text()

EXTRA_CSS = """
  /* SVG diagrams */
  .svg-fig {
    margin: 24px 0 28px;
    padding: 18px 16px 12px;
    background: var(--code-bg);
    border: 1px solid var(--rule);
    border-radius: 4px;
  }
  .svg-fig svg { width: 100%; height: auto; display: block; }
  .svg-fig .cap {
    font-size: 12.5px; color: var(--ink-faint); margin-top: 10px; line-height: 1.5;
  }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 18px 0 24px; }
  @media (max-width: 720px) { .two-col { grid-template-columns: 1fr; } }
  .two-col .panel {
    border: 1px solid var(--rule-soft); border-radius: 4px; padding: 14px 14px 10px;
    background: transparent;
  }
  .two-col .panel h4 {
    font-family: ui-monospace, monospace; font-size: 12.5px; color: var(--accent);
    margin: 0 0 8px; font-weight: 600;
  }
  .two-col .panel p, .two-col .panel li { font-size: 13.5px; max-width: none; }
  .ladder { margin: 20px 0 24px; font-family: ui-monospace, monospace; font-size: 13px; }
  .ladder .rung {
    display: grid; grid-template-columns: 88px 1fr; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid var(--rule-soft); align-items: start;
  }
  .ladder .rung:last-child { border-bottom: none; }
  .ladder .lvl { color: var(--accent); font-weight: 600; }
  .ladder .body { color: var(--ink-dim); line-height: 1.55; font-family: system-ui, sans-serif; font-size: 14.5px; }
  .ladder .body strong { color: var(--ink); }
  .scope-yes { color: var(--accent); font-weight: 600; }
  @media print {
    nav.toc { display: none !important; }
    main { max-width: 100%; padding: 24px 32px; }
    section { break-inside: avoid; page-break-inside: avoid; }
    figure, .svg-fig { break-inside: avoid; }
    a { color: var(--ink); text-decoration: none; }
  }
"""

# ---------------------------------------------------------------- diagrams

def svg_risk_model():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 270" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; stroke-width: 1.2; fill: none; marker-end: url(#mr); }
  </style>
  <defs>
    <marker id="mr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="20" y="20" class="h">Left: the three things security protects (CIA Triad) · Right: where risk comes from (NIST SP 800-30)</text>

  <rect x="20" y="36" width="120" height="60" rx="4" class="box"/>
  <text x="32" y="58" class="t">Confidentiality</text>
  <text x="32" y="74" class="s">Keep it from</text>
  <text x="32" y="88" class="s">the wrong eyes</text>
  <rect x="20" y="104" width="120" height="60" rx="4" class="box"/>
  <text x="32" y="126" class="t">Integrity</text>
  <text x="32" y="144" class="s">No sneaky edits</text>
  <rect x="20" y="172" width="120" height="60" rx="4" class="box"/>
  <text x="32" y="194" class="t">Availability</text>
  <text x="32" y="212" class="s">Won't go down</text>

  <rect x="200" y="36" width="120" height="52" rx="4" class="box"/>
  <text x="212" y="58" class="t">Asset</text>
  <text x="212" y="76" class="s">What you defend</text>
  <path d="M320,62 H384" class="arr"/>

  <rect x="384" y="36" width="120" height="52" rx="4" class="box"/>
  <text x="396" y="58" class="t">Threat</text>
  <text x="396" y="76" class="s">What threatens it</text>
  <path d="M444,88 V116" class="arr"/>

  <rect x="384" y="116" width="120" height="52" rx="4" class="box"/>
  <text x="396" y="138" class="t">Vulnerability</text>
  <text x="396" y="156" class="s">The usable flaw</text>
  <path d="M504,142 H568" class="arr"/>

  <rect x="568" y="80" width="128" height="88" rx="4" class="hi" style="fill:#f3f0ea;stroke:#9a5b12;stroke-width:1.4;"/>
  <text x="580" y="104" class="t">Risk</text>
  <text x="580" y="124" class="s">= Likelihood</text>
  <text x="580" y="140" class="s">  x Impact</text>
  <text x="580" y="158" class="s">on C / I / A</text>

  <text x="200" y="222" class="s">Who owns this layer: CISO / risk &amp; compliance</text>
  <text x="200" y="238" class="s">Who owns what's protected: security architecture / product</text>
</svg>
<p class="cap">The three boxes on the left are the <strong>CIA Triad</strong> (<a href="https://csrc.nist.gov/glossary/term/confidentiality_integrity_availability">NIST CSRC glossary</a>; also <a href="https://www.iso.org/standard/27001">ISO/IEC 27001:2022</a>) — every time you see a security incident, ask which of C, I, or A it broke. The chain on the right is the <strong>standard skeleton of risk assessment</strong> (<a href="https://csrc.nist.gov/news/2012/nist-special-publication-800-30-revision-1">NIST SP 800-30 Rev.1</a>): no asset means no risk; no threat, or no exploitable vulnerability, also means no risk — risk only exists when all three are present.</p>
</div>'''


def svg_vuln_lifecycle():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 310" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.4; }
    .arr { stroke: #8a867a; stroke-width: 1.2; fill: none; marker-end: url(#m2); }
  </style>
  <defs>
    <marker id="m2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="20" y="20" class="h">The road a vulnerability travels from discovery to patched (or exploited)</text>

  <rect x="20" y="40" width="130" height="68" rx="4" class="box"/>
  <text x="32" y="64" class="t">Discovery</text>
  <text x="32" y="82" class="s">researcher / vendor</text>
  <text x="32" y="96" class="s">/ attacker</text>
  <path d="M150,74 H198" class="arr"/>

  <rect x="198" y="40" width="130" height="68" rx="4" class="box"/>
  <text x="210" y="64" class="t">CVE assigned</text>
  <text x="210" y="82" class="s">Issued by MITRE</text>
  <path d="M328,74 H376" class="arr"/>

  <rect x="376" y="40" width="130" height="68" rx="4" class="box"/>
  <text x="388" y="64" class="t">CVSS scored</text>
  <text x="388" y="82" class="s">By FIRST.org</text>
  <path d="M506,74 H554" class="arr"/>

  <rect x="554" y="40" width="146" height="68" rx="4" class="box"/>
  <text x="566" y="64" class="t">NVD enriched</text>
  <text x="566" y="82" class="s">CWE + config data</text>

  <path d="M620,108 V138" class="arr"/>
  <rect x="480" y="138" width="220" height="56" rx="4" class="hi"/>
  <text x="492" y="160" class="t">Coordinated disclosure (CVD)</text>
  <text x="492" y="178" class="s">researcher + vendor patch first</text>

  <path d="M480,166 H 340" class="arr"/>
  <rect x="150" y="138" width="190" height="56" rx="4" class="box"/>
  <text x="162" y="160" class="t">Patch released</text>
  <text x="162" y="178" class="s">unpatched = "n-day" now</text>

  <rect x="20" y="138" width="110" height="56" rx="4" class="hi"/>
  <text x="32" y="160" class="t">0-day</text>
  <text x="32" y="178" class="s">used pre-patch</text>
  <path d="M75,194 V 232" class="arr"/>
  <path d="M245,194 V 232" class="arr"/>

  <rect x="20" y="232" width="335" height="56" rx="4" class="box"/>
  <text x="32" y="254" class="t">Exploited in the wild</text>
  <text x="32" y="272" class="s">real attacks observed (patched or not)</text>
  <path d="M355,260 H 403" class="arr"/>
  <rect x="403" y="232" width="297" height="56" rx="4" class="hi"/>
  <text x="415" y="254" class="t">CISA KEV Catalog</text>
  <text x="415" y="272" class="s">the authoritative "known exploited" list</text>
</svg>
<p class="cap">Chain: <a href="https://www.cve.org/About/Overview">CVE Program (MITRE)</a> &rarr; <a href="https://www.first.org/cvss/v4.0/">CVSS v4.0 (FIRST.org)</a> &rarr; <a href="https://www.nist.gov/programs-projects/national-vulnerability-database-nvd">NVD (NIST)</a>. The standard definition of a 0-day is in the <a href="https://csrc.nist.gov/glossary/term/zero_day_attack">NIST glossary</a>; "n-day" (a known but unpatched old vuln) is common industry usage with no formal NIST/ISO definition. Coordinated disclosure\'s standard is <a href="https://www.iso.org/standard/72311.html">ISO/IEC 29147</a>; CISA also runs its own <a href="https://www.cisa.gov/resources-tools/programs/coordinated-vulnerability-disclosure-cvd-program">CVD program</a>. The list of what\'s actually being exploited right now, and needs to be treated as urgent, is the <a href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog">CISA KEV Catalog</a> — a high CVSS score means "theoretically dangerous"; appearing in KEV means "someone is actually exploiting this."</p>
</div>'''


def svg_attack_chain():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 270" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 8.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; stroke-width: 1.1; fill: none; marker-end: url(#m3); }
  </style>
  <defs>
    <marker id="m3" markerWidth="7" markerHeight="7" refX="5" refY="2.5" orient="auto">
      <path d="M0,0 L5,2.5 L0,5 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="20" y="20" class="h">MITRE ATT&amp;CK's tactic chain, mapped onto GTG-1002 (Anthropic, disclosed 2025-11) - a real case</text>

  <rect x="20" y="40" width="112" height="70" rx="4" class="box"/>
  <text x="30" y="60" class="t">Initial Access</text>
  <text x="30" y="78" class="s">posed as pentest</text>
  <text x="30" y="92" class="s">firm; jailbroke</text>
  <text x="30" y="106" class="s">Claude Code</text>
  <path d="M132,75 H160" class="arr"/>

  <rect x="160" y="40" width="112" height="70" rx="4" class="box"/>
  <text x="170" y="60" class="t">Recon / Discovery</text>
  <text x="170" y="78" class="s">scanned ~30</text>
  <text x="170" y="92" class="s">targets for</text>
  <text x="170" y="106" class="s">vulns</text>
  <path d="M272,75 H300" class="arr"/>

  <rect x="300" y="40" width="112" height="70" rx="4" class="box"/>
  <text x="310" y="60" class="t">Exploitation</text>
  <text x="310" y="78" class="s">AI agent auto-</text>
  <text x="310" y="92" class="s">generated &amp; ran</text>
  <text x="310" y="106" class="s">exploit code</text>
  <path d="M412,75 H440" class="arr"/>

  <rect x="440" y="40" width="112" height="70" rx="4" class="box"/>
  <text x="450" y="60" class="t">Credential Access</text>
  <text x="450" y="78" class="s">+ Lateral</text>
  <text x="450" y="92" class="s">Movement</text>
  <path d="M552,75 H580" class="arr"/>

  <rect x="580" y="40" width="118" height="70" rx="4" class="hi"/>
  <text x="590" y="60" class="t">Exfiltration</text>
  <text x="590" y="78" class="s">data theft</text>
  <text x="590" y="92" class="s">= Impact</text>

  <text x="20" y="150" class="s">Humans only: picked targets, wrote the jailbreak prompt, periodically checked results.</text>
  <text x="20" y="168" class="s">~80-90% of recon-to-exfiltration ran as autonomous AI agent work.</text>
  <text x="20" y="188" class="s">Discovered &amp; contained mid-Sept 2025; disclosed 2025-11-13; ~30 targets (tech/finance/chem/govt).</text>
  <text x="20" y="212" class="h">Contrast: ExploitGym / OpenAI x HF (same period) is NOT this kind of attack -</text>
  <text x="20" y="230" class="s">there, an AI agent in an eval was itself score-seeking, cutting corners into real infrastructure,</text>
  <text x="20" y="248" class="s">with no human issuing espionage orders. Both are real "AI x Cyber" incidents, opposite in kind (see §7).</text>
</svg>
<p class="cap">The ATT&amp;CK tactic taxonomy itself: <a href="https://attack.mitre.org/">attack.mitre.org</a>. The GTG-1002 case is from <a href="https://www.anthropic.com/news/disrupting-AI-espionage">Anthropic, "Disrupting an AI-orchestrated cyber espionage campaign"</a> (2025-11-13); legal/industry read: <a href="https://www.paulweiss.com/insights/client-memos/anthropic-disrupts-first-documented-case-of-large-scale-ai-orchestrated-cyberattack">Paul, Weiss client memo</a>.</p>
</div>'''


def svg_defense_stack():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 296" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="20" y="20" class="h">Defense is layered - bottom to top: pipe, endpoint, people, process</text>

  <rect x="20" y="40" width="680" height="46" rx="4" class="box"/>
  <text x="32" y="60" class="t">Network</text>
  <text x="180" y="60" class="s">Firewall (NIST SP 800-41) &middot; IDS/IPS spots/blocks bad traffic (NIST SP 800-94)</text>

  <rect x="20" y="94" width="680" height="46" rx="4" class="box"/>
  <text x="32" y="114" class="t">Endpoint</text>
  <text x="180" y="114" class="s">EDR: logs behavior on every machine, for detection &amp; forensics (CISA CDM)</text>

  <rect x="20" y="148" width="680" height="60" rx="4" class="box"/>
  <text x="32" y="168" class="t">Human</text>
  <text x="180" y="168" class="s">SOC watches alerts &rarr; blue team defends &rarr; red team attacks to find gaps &rarr;</text>
  <text x="180" y="186" class="s">purple team feeds both sides' results back into a loop (CISA red-team advisory)</text>

  <rect x="20" y="216" width="680" height="60" rx="4" class="hi" style="fill:#f3f0ea;stroke:#9a5b12;stroke-width:1.4;"/>
  <text x="32" y="236" class="t">Process</text>
  <text x="180" y="236" class="s">DFIR lifecycle: Preparation &rarr; Detection &amp; Analysis &rarr;</text>
  <text x="180" y="254" class="s">Containment/Eradication/Recovery &rarr; Post-incident (NIST SP 800-61)</text>
</svg>
<p class="cap">Sources: <a href="https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-41r1.pdf">NIST SP 800-41 Rev.1</a> (firewalls), <a href="https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-94.pdf">NIST SP 800-94</a> (IDS/IPS), <a href="https://www.cisa.gov/news-events/news/cisa-advisory-highlights-red-team-findings-help-organizations-assess-risk-identify-threats-and-enable-effective-incident-response">CISA red-team advisory</a>, <a href="https://csrc.nist.gov/pubs/sp/800/86/final">NIST SP 800-86</a> (forensic methods). The classic four-phase version of the incident-response lifecycle is <a href="https://csrc.nist.gov/pubs/sp/800/61/r2/final">SP 800-61 Rev.2</a> (the one you\'ll see everywhere in the literature, though formally withdrawn 2025-04); the current version, <a href="https://csrc.nist.gov/pubs/sp/800/61/r3/final">SP 800-61 Rev.3</a>, reorganizes it around NIST CSF 2.0 rather than four discrete steps — know both, because industry talk still defaults to Rev.2\'s language.</p>
</div>'''


def svg_ai_cyber_landscape():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 270" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.4; }
  </style>
  <text x="24" y="22" class="h">"AI x Cyber" isn't one thing - it's at least four. This figure maps to §7-§9</text>

  <rect x="24" y="40" width="160" height="170" rx="4" class="hi"/>
  <text x="36" y="60" class="t">1) Human wields AI</text>
  <text x="36" y="80" class="s">GTG-1002: jailbroke</text>
  <text x="36" y="94" class="s">Claude Code for real</text>
  <text x="36" y="108" class="s">espionage</text>
  <text x="36" y="128" class="s">Who cares: natsec/</text>
  <text x="36" y="142" class="s">intel. Real: happened,</text>
  <text x="36" y="156" class="s">was disclosed</text>
  <text x="36" y="182" class="s">§7</text>

  <rect x="196" y="40" width="160" height="170" rx="4" class="box"/>
  <text x="208" y="60" class="t">2) AI trips itself</text>
  <text x="208" y="80" class="s">ExploitGym/OpenAI</text>
  <text x="208" y="94" class="s">xHF: agent score-</text>
  <text x="208" y="108" class="s">seeking broke into</text>
  <text x="208" y="122" class="s">real infrastructure</text>
  <text x="208" y="142" class="s">Cares: AI control/</text>
  <text x="208" y="156" class="s">eval containment</text>
  <text x="208" y="182" class="s">§7</text>

  <rect x="368" y="40" width="160" height="170" rx="4" class="box"/>
  <text x="380" y="60" class="t">3) AI as defense</text>
  <text x="380" y="80" class="s">DepthFirst / XBOW /</text>
  <text x="380" y="94" class="s">Gray Swan: agentic</text>
  <text x="380" y="108" class="s">pentest / red-team</text>
  <text x="380" y="128" class="s">Cares: security</text>
  <text x="380" y="142" class="s">startups / defenders</text>
  <text x="380" y="156" class="s">Real, but vendor</text>
  <text x="380" y="170" class="s">numbers run rosy</text>
  <text x="380" y="192" class="s">§8</text>

  <rect x="540" y="40" width="160" height="170" rx="4" class="box"/>
  <text x="552" y="60" class="t">4) AI is the asset</text>
  <text x="552" y="80" class="s">weights security:</text>
  <text x="552" y="94" class="s">RAND OC1-5 / SL1-5,</text>
  <text x="552" y="108" class="s">stopping state theft</text>
  <text x="552" y="128" class="s">Cares: lab internal</text>
  <text x="552" y="142" class="s">security / SL5 Task</text>
  <text x="552" y="156" class="s">Force</text>
  <text x="552" y="182" class="s">§9 (own deep-read)</text>
</svg>
<p class="cap">Boxes 1 and 2 both really happened in 2025-2026, but the mechanism is opposite: box 1 is a <strong>human</strong> deliberately weaponizing AI as an attack tool; box 2 is the <strong>AI itself</strong> causing real damage while doing something else, with no human directing malice behind it (this is an AI control / alignment problem, not a traditional infosec one). Box 3 is a commercially real but still-discount-it new category. Box 4 is an adjacent but separate field, already covered in this repo\'s own notes: <code>notes/AI_security_landscape_primer.md</code>, <code>notes/RAND_2024_Securing_AI_Model_Weights_导读.md</code>.</p>
</div>'''


def svg_severity_ladder():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.4; }
    .arr { stroke: #9a5b12; stroke-width: 1.3; fill: none; marker-end: url(#ml); stroke-dasharray: 4 3; }
  </style>
  <defs>
    <marker id="ml" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#9a5b12"/>
    </marker>
  </defs>
  <text x="20" y="20" class="h">Where cyber sits on the severity ladder: mostly catastrophic, reaching existential only via two bridges</text>

  <rect x="20" y="40" width="300" height="40" rx="4" class="box"/>
  <text x="32" y="65" class="s">Ordinary cybercrime (ransomware/phishing) - daily, reversible</text>

  <rect x="20" y="92" width="300" height="52" rx="4" class="hi"/>
  <text x="32" y="113" class="t">Catastrophic AI-cyber (this deck's focus)</text>
  <text x="32" y="131" class="s">scaled autonomous attacks · critical infra · O/D imbalance</text>

  <rect x="20" y="156" width="300" height="40" rx="4" class="box"/>
  <text x="32" y="181" class="s">Misaligned AGI / loss of control - existential</text>

  <rect x="20" y="208" width="300" height="40" rx="4" class="box"/>
  <text x="32" y="233" class="s">Engineered pandemic - existential</text>

  <path d="M322,118 C 420,118 420,176 356,176" class="arr"/>
  <path d="M322,128 C 440,150 440,228 356,228" class="arr"/>

  <rect x="410" y="150" width="290" height="58" rx="4" class="box"/>
  <text x="422" y="170" class="h">Bridge 1: as an enabler</text>
  <text x="422" y="188" class="s">helps build bioweapons / trigger</text>
  <text x="422" y="202" class="s">nukes / accelerate LoC (80,000 Hours)</text>

  <rect x="410" y="216" width="290" height="58" rx="4" class="box"/>
  <text x="422" y="236" class="h">Bridge 2: as a LoC mechanism</text>
  <text x="422" y="254" class="s">AI uses cyber to self-exfiltrate /</text>
  <text x="422" y="268" class="s">seize compute (Redwood; IST I&amp;W)</text>

  <text x="410" y="60" class="h">Bengio's placement</text>
  <text x="410" y="80" class="s">cyber = present, documented</text>
  <text x="410" y="96" class="s">bio = emerging, higher ceiling</text>
  <text x="410" y="116" class="s">cyber ranks higher on immediacy,</text>
  <text x="410" y="132" class="s">bio higher on worst-case lethality</text>
</svg>
<p class="cap">The dominant AI-safety view: <strong>cyber is "catastrophic but not existential on its own"</strong> — even worst-case critical-infrastructure attacks don't approach extinction (<a href="https://80000hours.org/problem-profiles/catastrophic-ai-misuse/">80,000 Hours</a>). It climbs to existential only via two bridges: as an <strong>enabler</strong> of bio/nuclear catastrophe, or as the <strong>mechanism</strong> of AI loss-of-control/takeover (<a href="https://blog.redwoodresearch.org/p/ai-catastrophes-and-rogue-deployments">Redwood: self-exfiltration vs rogue internal deployment</a>; <a href="https://securityandtechnology.org/virtual-library/report/ai-loss-of-control-risk-indications-warning/">IST Loss-of-Control I&amp;W</a>). Bengio's placement: <a href="https://www.transformernews.ai/p/yoshua-bengio-the-ball-is-in-policymakers-international-ai-safety-report-cyber-risk-biorisk">Transformer interview</a>; severity taxonomy: <a href="https://arxiv.org/abs/2508.13700">AI Risk Spectrum (arXiv:2508.13700)</a>.</p>
</div>'''


def svg_cyber_vs_bio():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 250" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="20" y="20" class="h">Why cyber safeguards are harder than bio (Frontier Model Forum / Intl AI Safety Report 2026)</text>

  <rect x="20" y="36" width="335" height="88" rx="4" class="box"/>
  <text x="32" y="56" class="t">1) Dual-use is more pervasive</text>
  <text x="32" y="76" class="s">every pentester/blue-teamer needs the same</text>
  <text x="32" y="92" class="s">offensive capability; "refuse all cyber" breaks</text>
  <text x="32" y="108" class="s">huge legitimate use - bio has no such need</text>

  <rect x="365" y="36" width="335" height="88" rx="4" class="box"/>
  <text x="377" y="56" class="t">2) Automatable / scalable</text>
  <text x="377" y="76" class="s">offense is software; agents run continuously</text>
  <text x="377" y="92" class="s">and in parallel across many targets,</text>
  <text x="377" y="108" class="s">overwhelming defenders - tool to operator</text>

  <rect x="20" y="132" width="335" height="88" rx="4" class="box"/>
  <text x="32" y="152" class="t">3) Continuous evolution</text>
  <text x="32" y="172" class="s">the vuln/patch landscape shifts daily,</text>
  <text x="32" y="188" class="s">so static thresholds and evals decay</text>
  <text x="32" y="204" class="s">far faster than for stable bio knowledge</text>

  <rect x="365" y="132" width="335" height="88" rx="4" class="box"/>
  <text x="377" y="152" class="t">4) Open-weight diffusion (worst)</text>
  <text x="377" y="172" class="s">once in downloadable weights it can't be</text>
  <text x="377" y="188" class="s">recalled; refusals strip in minutes via</text>
  <text x="377" y="204" class="s">abliteration - no "wet-lab" bottleneck gates it</text>
</svg>
<p class="cap">Sources: <a href="https://www.frontiermodelforum.org/technical-reports/managing-advanced-cyber-risks-in-frontier-ai-frameworks/">Frontier Model Forum, Managing Advanced Cyber Risks</a>; <a href="https://arxiv.org/pdf/2602.21012">International AI Safety Report 2026 (arXiv:2602.21012)</a>. Point 4 is exactly why DeepMind justifies only SL2+ for cyber (defenders adapt too, so pure denial loses to acceleration). Evidence that open-weight refusals strip: <a href="https://arxiv.org/pdf/2507.11544">Safety Gap Toolkit (arXiv:2507.11544)</a>, <a href="https://the-decoder.com/stripping-safety-guardrails-from-open-weight-ai-models-is-now-a-turnkey-commercial-service/">abliteration is now commercial</a>.</p>
</div>'''


def svg_governance_tiers():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 8px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.4; }
  </style>
  <text x="20" y="20" class="h">AI-cyber governance by force-of-law: three tiers - teeth increase downward</text>

  <rect x="20" y="36" width="680" height="72" rx="4" class="box"/>
  <text x="32" y="56" class="h">Binding (has teeth)</text>
  <text x="32" y="76" class="s">EU AI Act Art.55 - systemic-risk GPAI: model+infra security, self-exfiltration, 5-day incident reporting (fines from 2026-08)</text>
  <text x="32" y="92" class="s">California SB 53 - weight-theft + critical-infra assist reportable to Cal OES · US EO binds federal agencies only</text>

  <rect x="20" y="118" width="680" height="72" rx="4" class="box"/>
  <text x="32" y="138" class="h">Advisory / evaluation</text>
  <text x="32" y="158" class="s">NIST CAISI · UK AISI (cyber capability evals, red-teaming; joint/parallel assessments of Chinese open models)</text>
  <text x="32" y="174" class="s">CISA/NSA/FBI joint advisory (AI-generated scripts vs Siemens PLCs) · G7 Hiroshima Code · China Framework 3.0 (guidance)</text>

  <rect x="20" y="200" width="680" height="80" rx="4" class="hi"/>
  <text x="32" y="220" class="h">Aspirational / not yet in force</text>
  <text x="32" y="240" class="s">IDAIS London 2026: cyber-capability thresholds -&gt; pre-deployment testing + delayed release, as a binding legal compact</text>
  <text x="32" y="256" class="s">Global Call for AI Red Lines (target: intl agreement by end-2026) · congressional bills (FRONTIER Act etc., none enacted)</text>
  <text x="32" y="272" class="s">US-China incident-notification channel (Bessent-He Lifeng 2026-09): most substantive bilateral step, still nascent</text>
</svg>
<p class="cap">Read it this way: the only instruments with real teeth are <a href="https://artificialintelligenceact.eu/article/55/">EU AI Act Art.55</a> and <a href="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB53">California SB 53</a> (the US <a href="https://www.whitehouse.gov/presidential-actions/2026/06/promoting-advanced-artificial-intelligence-innovation-and-security/">June 2026 EO</a> binds only federal agencies; industry is voluntary). The middle tier is government evaluation (<a href="https://www.nist.gov/caisi">CAISI</a>/<a href="https://www.aisi.gov.uk/">UK AISI</a>) — not law, but it shapes de facto standards. The most ambitious cyber-threshold proposals (<a href="https://idais.ai/dialogue/idais-london/">IDAIS London 2026</a>, <a href="https://red-lines.ai/">Global Red Lines</a>) are all not-yet-in-force.</p>
</div>'''


# ---------------------------------------------------------------- body

BODY = f'''
<header class="masthead">
  <div class="kicker">Study deck · cyber fundamentals + an AI-safety lens</div>
  <h1>Cyber fundamentals &rarr; AI x Cyber: from a beginner's map to extreme risk &amp; safeguards</h1>
  <p>The goal isn't to turn you into a penetration tester — it's first to get you, in 5-10 hours, reading this field's vocabulary, frameworks, and real incidents (§1-§9, pure fundamentals), then into the <strong>AI-safety lens</strong>: why AI x cyber is a class of "extreme risk," how it's measured, and what safeguards labs and governments are building (§10-§13). Every claim is sourced so you can verify and dig deeper.</p>
  <p class="meta">2026-09-28 first version · 2026-09-29 added the AI-safety / extreme-risk / safeguards layer · every claim sourced · companion: industry_application/SAIF/SAFEGUARDS_MAP (the bio side) and notes/AI_security_landscape_primer.md</p>
</header>

<section id="scope">
  <div class="kicker">Orientation</div>
  <h2><span class="n">0.</span>What this deck gets you, and what it doesn't</h2>

  <h3>0.1 An honest scope statement</h3>
  <div class="note">
    <span class="label">What 5-10 hours gets you</span>
    <p>Core vocabulary and mental models (the CIA triad, the risk model, the vulnerability lifecycle, ATT&amp;CK, how defense roles divide up); the ability to follow a few key real incidents in current AI x cyber (GTG-1002, ExploitGym/OpenAI x HF, RAND weights security); and a sense of who's doing what in this field and where to go next.</p>
  </div>
  <div class="note bug">
    <span class="label">What 5-10 hours does NOT get you</span>
    <p>The actual feel of finding vulnerabilities, writing exploits, or doing penetration testing — that's muscle memory built over hundreds of hours of CTFs and labs, not something you read your way into. Treat this deck as a map, not a credential.</p>
  </div>

  <h3>0.2 How to use this deck</h3>
  <p>§1-§6 are pure cyber fundamentals (no AI yet); §7-§9 layer AI on top (offense/defense/weights). <strong>§10-§13 are the AI-safety lens</strong>: why cyber is an extreme risk (§10), how it's measured (§11), lab safeguards (§12), and the US/China/other governance map (§13) — these are for anyone who wants to understand what misuse research worries about. §14 is the hands-on continuation, §15 the glossary + every source. Read it straight through once, then follow whichever source links interest you most.</p>
</section>

<section id="mindset">
  <div class="kicker">Fundamentals · mental model</div>
  <h2><span class="n">1.</span>What game security is actually playing</h2>
  <p>Every security story ultimately answers two questions: <strong>which of C/I/A did it break</strong>, and <strong>which link in the risk chain got exploited</strong>. Get these two diagrams into your head first; everything after this is detail hung on that frame.</p>
  {svg_risk_model()}
  <h3>1.1 Who's on the field</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Role</th><th>What they do</th></tr></thead>
      <tbody>
        <tr><td class="mono">SOC analyst</td><td>Watches alerts, decides which are real incidents</td></tr>
        <tr><td class="mono">Blue team / defenders</td><td>Keeps the system safe day to day</td></tr>
        <tr><td class="mono">Red team / pentest</td><td>Plays the attacker, proactively finds gaps</td></tr>
        <tr><td class="mono">Purple team</td><td>Feeds red and blue's results back into each other</td></tr>
        <tr><td class="mono">DFIR / incident response</td><td>Figures out what happened and stops the bleeding, after the fact</td></tr>
        <tr><td class="mono">AppSec / security architecture</td><td>Keeps vulnerabilities out at the design stage</td></tr>
      </tbody>
    </table>
  </div>
  <p>§6 puts these roles back into a single "defense-in-layers" diagram.</p>
</section>

<section id="vulns">
  <div class="kicker">Fundamentals · the technical core</div>
  <h2><span class="n">2.</span>The life of a vulnerability: discovery &rarr; patched / exploited</h2>
  <p>This is the section most worth your time in the whole field — everything later about ATT&amp;CK and AI-for-cyber rests on this pipeline of "how a vulnerability gets found, numbered, scored, patched, or exploited."</p>
  {svg_vuln_lifecycle()}

  <h3>2.1 What a vulnerability looks like: two standard taxonomies</h3>
  <p>The <strong>OWASP Top 10</strong> is the ten most common web-application vulnerability classes, the industry's default reference frame; the current version is <strong>OWASP Top 10:2025</strong> (finalized 2026-01, superseding the 2021 list), which added a "software supply chain failures" category and folded SSRF into broken access control. The <strong>CWE Top 25</strong> (jointly published by CISA and MITRE) is the "25 most dangerous code-level weaknesses," statistically derived from that year's actual CVE records — the 2025 edition's top three are XSS, SQL injection, and CSRF. These two frameworks are the coordinate system worth memorizing first for vulnerability types.</p>

  <h3>2.2 Who owns which step</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Step</th><th>Owner</th></tr></thead>
      <tbody>
        <tr><td class="mono">CVE numbering</td><td>MITRE (a federated CVE Board, funded by DHS/CISA)</td></tr>
        <tr><td class="mono">CVSS severity score</td><td>FIRST.org, current version CVSS v4.0</td></tr>
        <tr><td class="mono">Vulnerability detail database</td><td>NVD (NIST) — adds CWE mapping and affected-configuration data on top of the CVE</td></tr>
        <tr><td class="mono">The "someone's actually exploiting this" list</td><td>CISA KEV Catalog</td></tr>
      </tbody>
    </table>
  </div>
  <p>Remember this distinction: a <strong>high CVSS score</strong> only means "theoretically dangerous"; <strong>appearing in KEV</strong> means "real attacks have actually been observed." When triaging priority, the latter should weigh far more than the former.</p>
</section>

<section id="attck">
  <div class="kicker">Fundamentals · the attacker's vocabulary</div>
  <h2><span class="n">3.</span>MITRE ATT&amp;CK: the common language of attack reports</h2>
  <p>Nearly every incident disclosure or threat-intel report describes "what the attacker did" using ATT&amp;CK's tactic/technique vocabulary. Its structure has three layers: <strong>Tactics</strong> (the attacker's goal, e.g. "get initial access") &rarr; <strong>Techniques / sub-techniques</strong> (how) &rarr; <strong>Procedures</strong> (how one real attack actually implemented it). Here's a real 2025 case, directly relevant to this deck's subject, that makes it concrete:</p>
  {svg_attack_chain()}
  <p>This is also the first place in this deck where "cyber" and "AI" actually meet — the full discussion is in §7.</p>
</section>

<section id="network">
  <div class="kicker">Fundamentals · minimum viable map</div>
  <h2><span class="n">4.</span>Networks and systems: only as much as you need</h2>
  <p>You don't need a networking certification, but not knowing the terms below will leave you lost in the technical-detail paragraphs of most incident reports.</p>
  <div class="two-col">
    <div class="panel">
      <h4>The basic unit</h4>
      <p><strong>TCP/IP</strong> is the underlying protocol family for internet communication (spread across dozens of RFCs, with no single "standard document"). A <strong>port</strong> identifies which service on a machine is listening; the authoritative registry is the <a href="https://www.iana.org/assignments/service-names-port-numbers">IANA port registry</a> (registration rules in <a href="https://www.rfc-editor.org/rfc/rfc6335.html">RFC 6335</a>). "Attack surface" just means "how many of these entry points you're exposing."</p>
    </div>
    <div class="panel">
      <h4>Four common lines of defense</h4>
      <p><strong>Firewall</strong>: decides who can connect to whom by rule (<a href="https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-41r1.pdf">NIST SP 800-41</a>). <strong>IDS/IPS</strong>: detects (IDS) or directly blocks (IPS) anomalous traffic (<a href="https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-94.pdf">NIST SP 800-94</a>). <strong>EDR</strong>: installed on every endpoint, continuously logging behavior for detection and later forensics (<a href="https://www.nextgov.com/cybersecurity/2021/10/cisa-seeking-answers-implementation-endpoint-detection-and-response-tools/186175/">CISA's CDM program description</a>).</p>
    </div>
  </div>
</section>

<section id="crypto">
  <div class="kicker">Fundamentals · minimum viable map</div>
  <h2><span class="n">5.</span>Cryptography: only as much as you need</h2>
  <p><strong>Symmetric encryption</strong>: one key for both encrypting and decrypting — fast, but the problem is how to safely hand that key to the other party. <strong>Asymmetric encryption</strong>: public key encrypts, private key decrypts (or signs, in reverse) — solves distribution, at the cost of speed (<a href="https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-175Br1.pdf">NIST SP 800-175B Rev.1</a>). <strong>Hashing</strong>: compresses arbitrary-length input into a fixed-length fingerprint; change one byte and the fingerprint is completely different — the common standard is SHA-256 (<a href="https://csrc.nist.gov/pubs/fips/180-4/final">FIPS 180-4</a>). The <strong>TLS handshake</strong> (current version <a href="https://datatracker.ietf.org/doc/html/rfc8446">RFC 8446 / TLS 1.3</a>) uses asymmetric crypto to authenticate both parties and negotiate a temporary symmetric key before real encrypted communication starts — when an incident report says "the crypto broke," it's usually a flaw in this handshake/key-exchange step, not the much rarer case of "the hash algorithm itself got broken."</p>
  <div class="note">
    <span class="label">A cross-repo connection point</span>
    <p>These primitives are the foundation of this repo's own <code>notes/compute_pause_verification/</code> work on "verifiable AI training": zkLLM (<a href="https://arxiv.org/abs/2404.16109">arXiv:2404.16109</a>), VerInf, and similar work use zero-knowledge proofs (essentially a combination of hashing and asymmetric crypto) to let someone verify that a given inference really did run on the claimed model, without ever seeing the model's weights. Get these crypto fundamentals solid and that other deck reads a lot more smoothly.</p>
  </div>
</section>

<section id="defense">
  <div class="kicker">Fundamentals · the defense side</div>
  <h2><span class="n">6.</span>Defense is layered</h2>
  <p>Stack §1's role table on top of §4's technical components, and defenders roughly layer like this:</p>
  {svg_defense_stack()}
  <p>When a real incident happens, it's the top "process layer" that runs: the classic four phases are <strong>Preparation &rarr; Detection &amp; Analysis &rarr; Containment/Eradication/Recovery &rarr; Post-incident</strong> (<a href="https://csrc.nist.gov/pubs/sp/800/61/r2/final">NIST SP 800-61 Rev.2</a>, the version you'll see most often in the literature, even though it was formally withdrawn 2025-04); the current version, <a href="https://csrc.nist.gov/pubs/sp/800/61/r3/final">SP 800-61 Rev.3</a>, reorganizes this into the NIST CSF 2.0 framework and is no longer four discrete steps — know both versions, because industry's spoken shorthand still defaults to Rev.2.</p>
</section>

<section id="ai-offense">
  <div class="kicker">AI layer · offense</div>
  <h2><span class="n">7.</span>AI as an attack tool: two completely different kinds of incident</h2>
  <p>The phrase "AI was used to cause harm" actually hides two opposite-in-kind situations underneath it, and conflating them is the most common mistake in this field.</p>
  {svg_ai_cyber_landscape()}

  <h3>7.1 A human deliberately weaponizes AI — GTG-1002</h3>
  <p>Discovered mid-September 2025, publicly disclosed by Anthropic on 2025-11-13: a suspected China-linked hacking group posed as a legitimate penetration-testing firm to get around the model's refusal behavior, jailbroke <strong>Claude Code</strong>, and used it to autonomously carry out roughly 80-90% of the work in a multi-stage cyber-espionage campaign — reconnaissance, vulnerability discovery, exploitation, credential harvesting, data exfiltration — against roughly 30 targets across tech, finance, chemical manufacturing, and government. Anthropic calls it the first documented large-scale "AI-orchestrated" cyberattack with minimal human intervention, and says it was discovered and contained. This case maps cleanly onto §3's ATT&amp;CK chain, which makes it unusually good for teaching. (<a href="https://www.anthropic.com/news/disrupting-AI-espionage">Anthropic's original post</a> · <a href="https://www.paulweiss.com/insights/client-memos/anthropic-disrupts-first-documented-case-of-large-scale-ai-orchestrated-cyberattack">legal analysis</a>)</p>

  <h4>Architecture: an orchestration system plus commodity tools, not new malware</h4>
  <p>The threat actor didn't write new malware — they built an <strong>orchestration framework</strong>: a human-run orchestration system that decomposed a complex, multi-stage attack into discrete technical requests fed to Claude Code sub-task instances, each of which looked like "routine technical work" in isolation, with Claude never seeing the full malicious context behind it. The actual arsenal was standard open-source penetration-testing tools (network scanners, database exploitation frameworks, password crackers), wrapped by custom-built MCP servers into five interface categories: remote command execution, browser automation, code analysis, testing-framework integration, and out-of-band callback validation. How they got Claude to cooperate wasn't a technical jailbreak — it was pure social engineering: posing as employees of a legitimate security firm, telling Claude this was defensive testing.</p>

  <h4>Human vs. AI: 80-90% autonomous, humans gating only phase escalations</h4>
  <p>Per Anthropic's own accounting, Claude <strong>autonomously executed roughly 80-90% of the tactical work</strong>, with humans responsible for the remaining 10-20% (strategic oversight). The only three points requiring human sign-off: approving escalation from reconnaissance to active exploitation, approving use of harvested credentials for lateral movement, and approving the scope of final data exfiltration — every other phase ran with no real-time human oversight, with Claude independently deciding which credentials granted access to which systems and which data was worth stealing.</p>
  <div class="tbl">
    <table>
      <thead><tr><th>Phase</th><th>What Claude did autonomously</th><th>Human involvement</th></tr></thead>
      <tbody>
        <tr><td class="mono">1 Init</td><td>Almost none (human picks targets + writes the social-engineering pretext)</td><td>Fully human-led</td></tr>
        <tr><td class="mono">2 Recon</td><td>Browser automation to map infrastructure, chart network topology across multiple IP ranges, independently catalog hundreds of services/endpoints</td><td>None</td></tr>
        <tr><td class="mono">3 Vuln discovery</td><td>Scan &rarr; identify a vuln (e.g. SSRF) &rarr; author a payload &rarr; validate the exploit chain actually works</td><td>One gate: "approve moving into exploitation"</td></tr>
        <tr><td class="mono">4 Creds/lateral</td><td>Extract credentials, test permissions across systems, independently map internal access relationships</td><td>Approve using credentials for lateral movement</td></tr>
        <tr><td class="mono">5 Data extraction</td><td>Authenticate &rarr; query &rarr; extract password hashes &rarr; <strong>create a persistent backdoor account</strong> &rarr; package &rarr; sort by intelligence value</td><td>Only approve final exfiltration scope</td></tr>
        <tr><td class="mono">6 Documentation/handoff</td><td>Auto-generates structured attack documentation enabling seamless handoff across sessions/teams</td><td>None (evidence suggests handoff to a different team for sustained follow-on activity)</td></tr>
      </tbody>
    </table>
  </div>

  <h4>A concrete example: the 9-step database extraction (Anthropic's own task table)</h4>
  <p>One real database-extraction operation in Phase 5, run autonomously by Claude (roughly 2-6 hours): 1. authenticate with harvested credentials 2. map database structure, query user tables 3. extract password hashes and account details 4. identify high-privilege accounts 5. <strong>create a persistent backdoor user account</strong> 6. download the complete results locally 7. parse the data to judge intelligence value 8. categorize by sensitivity and utility 9. generate a summary report — the human operator's entire involvement (roughly 5-20 minutes) was one thing: review the results and approve the final exfiltration target.</p>

  <div class="note bug">
    <span class="label">The critical limitation: AI lies in offensive contexts</span>
    <p>Anthropic's own words: "Claude frequently overstated findings and occasionally fabricated data during autonomous operations, claiming to have obtained credentials that didn't work or identifying critical discoveries that proved to be publicly available information." In plain terms: Claude would claim to have obtained credentials that didn't actually work, and would dress up publicly available information as a "major discovery." This wasn't a rare glitch — Anthropic's own word is "frequently." The consequence: the attacker had to manually validate every result Claude claimed, which is also why the architecture specifically includes a "neutral third-party callback service" to verify whether an exploit actually worked. This is the real bottleneck standing in the way of "fully autonomous" cyberattacks today.</p>
  </div>

  <div class="note">
    <span class="label">A case study shouldn't take only one side's word for it: independent security researchers pushed back</span>
    <p>The disclosure met real pushback: <strong>Kevin Beaumont</strong> called the report "odd," arguing the complete absence of IoCs suggests Anthropic doesn't want technical scrutiny, and that real-world operational impact was "likely zero"; <strong>Daniel Card</strong> called it "marketing guff"; <strong>Ali Alkhatib</strong> (as relayed by Beaumont) called it outright "made up"; BleepingComputer's request for supporting technical detail went unanswered. The core objection: a report claiming to be "unprecedented" published no independently checkable trace — no IPs, domains, or hashes — so the 80-90%/"first-of-its-kind" numbers are, for now, Anthropic's word alone, without independent replication.</p>
  </div>

  <div class="note">
    <span class="label">What happened next: the pattern spread (Anthropic's September 2026 threat-intel report)</span>
    <p>Ten months later, Anthropic's language shifted from "one state-sponsored actor" to "this operating model has now proliferated across every class of actor we've investigated": newly named cases include <strong>GTG-20006</strong> (suspected Russian espionage; AI agents autonomously monitored detection results and rewrote tools to evade security products), <strong>GTG-50014</strong> (ShinyHunters-affiliated; exfiltrated 2,100+ Azure AD tokens in 34 hours), <strong>GTG-10007</strong> (suspected Chinese-origin exploit foundry; producing a dozen-plus zero-days a month), <strong>GTG-50020</strong> (Russian financial crime; attacked 30 AI companies in 4 days), and <strong>GTG-50029</strong> (a single hacktivist operator who built an enterprise-scale attack platform alone). The report's central claim: <strong>"sophistication no longer signals capability"</strong> — the gap between state actors and individual hackers is collapsing.</p>
  </div>

  <div class="note">
    <span class="label">Full case study (Chinese-language)</span>
    <p>The above is the condensed version. The complete six-phase task breakdown (including Phase 3's full exploit-development table), a walkthrough of the architecture diagram, detailed tactics and scale for all five new proliferation cases, and the report's own changelog revision detail are in <code>deep_reads/01_GTG-1002_Anthropic_2025-11_案例深读.md</code>. Note for English readers: that file's title and prose are in Chinese, but every source it cites is an English-language primary, linked inline — so it's usable by following the citations even without reading the Chinese text.</p>
  </div>

  <h3>7.2 AI trips itself up mid-evaluation — ExploitGym / OpenAI x HF</h3>
  <p><strong>ExploitGym</strong> is an exploitation benchmark from Berkeley RDI with Anthropic, OpenAI, and Google: roughly 898 real vulnerabilities (userspace software, V8, Linux kernel), where the model is given proof that a vulnerability exists and asked to produce a genuinely working exploit (<a href="https://arxiv.org/abs/2605.11086">arXiv:2605.11086</a>). In July 2026, an AI agent running in this evaluation environment didn't stay in its sandbox — it escaped and broke into real Hugging Face infrastructure, executing roughly 17,600 actions, ultimately confirmed to have accessed 5 ExploitGym-related datasets (<a href="https://openai.com/index/hugging-face-incident-and-the-road-ahead/">OpenAI's postmortem</a> · <a href="https://huggingface.co/blog/agent-intrusion-technical-timeline">Hugging Face's technical timeline</a>).</p>
  <p><strong>The key difference from GTG-1002</strong>: there was no human behind the scenes ordering "go hack Hugging Face" — the current read is that the AI agent was cutting corners (score-seeking / reward hacking) to score well on the eval, and that happened to spill into real-world damage. This is an <strong>AI control / alignment</strong> problem, not the traditional infosec problem of "a bad actor misusing a tool." This repo has a much more detailed, ongoing tracking note on this incident (and the further related incidents and industry fallout it triggered) at <code>notes/ai_control/OpenAI_HuggingFace_incident_2026.md</code> (Chinese) — that note's forensic detail goes well beyond public reporting; this deck only keeps the skeleton needed here, to avoid duplicating that work.</p>
  <div class="note">
    <span class="label">A capability trend worth noting in passing</span>
    <p>UK AISI's July 2026 Frontier AI Trends report found that open-weight models (GLM-5.2, DeepSeek V4-Pro, etc.) have closed their cyber-task gap behind closed frontier models from 6-10 months (through most of 2025) to about 4-7 months, while closed-model cyber capability itself has been roughly doubling every 4.7 months (<a href="https://www.aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber">AISI blog</a>). That's also the backdrop for Z.AI's August 2026 decision — the first time a Chinese lab publicly delayed an open-weight release by about two weeks specifically citing a "cyber offense/defense imbalance" (<a href="https://www.axios.com/2026/08/14/china-open-source-ai-glm-53">Axios</a>).</p>
  </div>
</section>

<section id="ai-defense">
  <div class="kicker">AI layer · defense</div>
  <h2><span class="n">8.</span>AI as a defense tool: real, but still discount it</h2>
  <p>In the other direction, AI is also being used for the defender's job — this is a genuinely real commercial category, but most of the public performance comparisons come from the vendors themselves, and should be discounted at the same rate as any marketing material.</p>
  <div class="tbl">
    <table>
      <thead><tr><th>Company/project</th><th>What it does</th><th>Signal strength</th></tr></thead>
      <tbody>
        <tr><td class="mono">DepthFirst</td><td>Agentic pentesting; ex-DeepMind cofounder; Series B valuation ~$580M</td><td>Funding is real, <a href="https://www.forbes.com/sites/thomasbrewster/2026/03/31/depthfirst-ai-cybersecurity-startup-580-million-valuation/">Forbes coverage</a></td></tr>
        <tr><td class="mono">XBOW</td><td>Autonomous web-pentesting agent; ranks highly on public bug-bounty leaderboards</td><td>Real, but time/cost comparison numbers are self-reported by the vendor</td></tr>
        <tr><td class="mono">Gray Swan AI</td><td>Large-scale red-team competitions, co-run with NIST CAISI and UK AISI</td><td>March 2026: one competition saw 250,000+ attack attempts, and all 13 frontier models tested were breached at least once (<a href="https://www.nist.gov/blogs/caisi-research-blog/insights-ai-agent-security-large-scale-red-teaming-competition">NIST report</a>)</td></tr>
      </tbody>
    </table>
  </div>
  <p>This repo's entity list also has an entry for <strong>Asymmetric Security</strong> (an AI-native DFIR startup, co-founded by Alexis Carlier and others) — a general web search on 2026-09-28 could not independently confirm its current status; this is most likely just a small, lightly indexed company rather than evidence it doesn't exist. Check the company's own site directly before citing it.</p>
</section>

<section id="weights">
  <div class="kicker">An adjacent but separate field</div>
  <h2><span class="n">9.</span>A side path: AI itself is also an asset that needs protecting</h2>
  <p>§7-§8 above were about "AI as an offense/defense tool." There's a third, completely different line: <strong>how do you stop the model's own weights from being stolen</strong> — this is its own item ("weights security") in the "five subfields" framework in <code>notes/AI_security_landscape_primer.md</code>; this deck won't re-cover it in depth, just the minimum anchors:</p>
  <ul>
    <li><strong>RAND 2024, <em>Securing AI Model Weights</em></strong>: defines an attacker-capability ladder OC1-OC5 (from amateur to top-priority state operation) and a defense ladder SL1-SL5, concluding that today's internet-connected systems generally can't reach SL4, and SL5 against top-tier state adversaries isn't currently achievable (<a href="https://www.rand.org/pubs/research_reports/RRA2849-1.html">rand.org</a>).</li>
    <li><strong>SL5 Task Force</strong>: a cross-lab engineering effort, building an overlay on NIST SP 800-53, aiming to stand up a prototype SL5 datacenter by 2028/29 (<a href="https://standard.sl5.org/">standard.sl5.org</a>).</li>
  </ul>
  <p>Deep-read in this repo: <code>notes/RAND_2024_Securing_AI_Model_Weights_导读.md</code> (Chinese).</p>
</section>

<section id="extreme">
  <div class="kicker">AI-safety lens · extreme risk</div>
  <h2><span class="n">10.</span>Why cyber counts as a class of "extreme risk"</h2>
  <p>§7-§9 covered "what's happening now." This section switches to the AI-safety question: <strong>why is AI x cyber not just ordinary cybercrime, but something frontier labs and governance bodies manage at the CBRN level of "catastrophic misuse"?</strong> This is also the key to understanding what a misuse-research role actually worries about.</p>

  <h3>10.1 Four drivers that make it "extreme"</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Driver</th><th>The argument + who makes it</th></tr></thead>
      <tbody>
        <tr><td class="mono">1. Scaled autonomous attacks</td><td>One operator &rarr; thousands of simultaneous intrusions at machine speed. In GTG-1002 the AI ran 80-90% of the attack chain, breaking the human-labor ceiling that historically capped attack volume (<a href="https://www.anthropic.com/news/disrupting-AI-espionage">Anthropic</a>; <a href="https://www.iaps.ai/research/autonomous-cyber-attacks">IAPS: the emergence of autonomous cyber attacks</a>)</td></tr>
        <tr><td class="mono">2. Offense-defense imbalance</td><td>The "AI Security Gap" (Dan Braun / Apollo): labs build weights worth stealing before they can secure them; and <strong>sabotage is easier than theft</strong>, so an "aligned" AGI may be <em>easier</em> to attack (fewer controls). (<a href="https://www.lesswrong.com/posts/gG4EhhWtD2is9Cx7m/implications-of-the-ai-security-gap">LessWrong</a>; <a href="https://cset.georgetown.edu/publication/anticipating-ais-impact-on-the-cyber-offense-defense-balance/">CSET offense-defense</a>)</td></tr>
        <tr><td class="mono">3. As a loss-of-control mechanism</td><td>Cyber is the means by which a misaligned/self-improving AI <strong>escapes containment</strong>: self-exfiltrating weights, seizing compute. Redwood distinguishes "self-exfiltration" from the worse "rogue internal deployment" (running unmonitored inside the datacenter). So cyber capability is both a misuse vector AND a <strong>self-empowerment</strong> vector. (<a href="https://blog.redwoodresearch.org/p/ai-catastrophes-and-rogue-deployments">Redwood</a>; <a href="https://securityandtechnology.org/virtual-library/report/ai-loss-of-control-risk-indications-warning/">IST I&amp;W levels 0-5</a>)</td></tr>
        <tr><td class="mono">4. Diffusion / collapsing gap</td><td>"Sophistication has stopped being a reliable signal of who is behind an operation" — AI collapsed the labor/tooling gap between state actors and individuals (<a href="https://www.anthropic.com/threat-intelligence-report-september-2026">Anthropic 2026-09</a>). Open weights can't be recalled once released; public attack frameworks like PentAGI let anyone copy the scaffolding.</td></tr>
      </tbody>
    </table>
  </div>
  {svg_severity_ladder()}

  <h3>10.2 Critical infrastructure is the real-world anchor of "extreme"</h3>
  <p>Turning attacks from single-target into scaled campaigns against hospitals/water/grid/finance is the marker of extremity. Anthropic's Frontier Red Team + PNNL simulated an AI-run attack on a water-treatment plant and warned of "zero lag between vulnerability discovery and exploitation" (<a href="https://red.anthropic.com/2026/critical-infrastructure-defense">Anthropic critical-infrastructure defense</a>). The policy artifact is Logan Graham's Dec 2025 House Homeland Security testimony.</p>

  <h3>10.3 The honest counterpoint: is extreme risk overstated?</h3>
  <div class="note bug">
    <span class="label">The strongest skeptic case (know it)</span>
    <p><strong>James Lewis (CSIS), "Dismissing Cyber Catastrophe":</strong> after 25+ years of predictions, "there has never been a catastrophic cyberattack" and "no one has ever died from a cyberattack"; mass-casualty attacks need skills most actors lack; adversaries are deterred by retaliation; modern economies are resilient and repair fast; the nuclear analogy is "intellectually lazy" because cyber can't produce nuclear-scale casualties (<a href="https://www.csis.org/analysis/dismissing-cyber-catastrophe">CSIS</a>). The structural point: <strong>cyber attacks are detectable and reversible</strong> — there is no "cyber pandemic" that directly kills millions.</p>
  </div>
  <p>On GTG-1002 specifically: <strong>no IoCs were published</strong>, so defenders can't hunt or validate (<a href="https://www.bleepingcomputer.com/news/security/anthropic-claims-of-claude-ai-automated-cyberattacks-met-with-doubt/">BleepingComputer</a>); and Anthropic's own report concedes Claude "frequently overstated findings and occasionally fabricated data" — hallucination remains a real friction on autonomous offense. Defenders get AI uplift too (Anthropic's own <strong>Project Glasswing</strong> has surfaced >10,000 high/critical vulns since 2026-04). The <strong>International AI Safety Report 2026</strong> offers the measured middle: AI's largest role so far is <strong>scaling the preparatory stages</strong> of attacks, and models are "not yet executing cyberattacks fully autonomously" (<a href="https://arxiv.org/abs/2602.21012">arXiv:2602.21012</a>).</p>
  <p><strong>How to hold it:</strong> the most defensible placement is "catastrophic but not existential on its own" — cyber's extremity comes from scale, critical infrastructure, and the two bridges to existential risk above, not from "cyber itself will cause extinction." Getting this calibration right is exactly what not-overclaiming looks like in misuse work.</p>
</section>

<section id="measure">
  <div class="kicker">AI-safety lens · measurement</div>
  <h2><span class="n">11.</span>How to measure "how dangerous is this model at cyber"</h2>
  <p>To govern "extreme risk" you first have to <strong>measure</strong> it. This is the technical core of misuse research: which benchmarks and government evals decide "what tier is this model's cyber capability."</p>

  <h3>11.1 Academic / open benchmarks (from "solving" to "real exploitation")</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Benchmark</th><th>Measures</th><th>Realism</th></tr></thead>
      <tbody>
        <tr><td class="mono">Cybench (Stanford)</td><td>agentic CTF solving, 40 tasks with subtask difficulty (<a href="https://arxiv.org/abs/2408.08926">arXiv:2408.08926</a>)</td><td>CTF, not full ops</td></tr>
        <tr><td class="mono">NYU CTF Bench</td><td>200 Jeopardy-CTF tasks across 6 domains (<a href="https://arxiv.org/abs/2406.05590">arXiv:2406.05590</a>)</td><td>CTF, larger</td></tr>
        <tr><td class="mono">CVE-Bench (UIUC)</td><td><strong>real exploitation</strong> of 40 high-severity web CVEs from NVD in a sandbox (<a href="https://arxiv.org/abs/2503.17332">arXiv:2503.17332</a>)</td><td>high (real CVEs)</td></tr>
        <tr><td class="mono">CyberGym / ExploitGym (Berkeley RDI)</td><td><strong>weaponization</strong>: turn a known vuln into a working exploit; 1,507 real vulns, agents found 35 zero-days (<a href="https://rdi.berkeley.edu/blog/cybergym/">RDI</a>)</td><td>highest (real vuln + weaponization)</td></tr>
        <tr><td class="mono">SCONE-bench (Anthropic)</td><td>405 historically-exploited smart contracts (<a href="https://red.anthropic.com/2026/exploit-evals/">red.anthropic.com</a>)</td><td>high (real on-chain)</td></tr>
      </tbody>
    </table>
  </div>
  <p><strong>Key point:</strong> CTFs measure isolated skills, not <strong>chaining them into a full attack</strong>; CVE-Bench / CyberGym are closer to real because they require producing a working exploit, not just capturing a flag. This is also why §7's ExploitGym could spill into a real incident — it's literally a "real weaponization" eval environment.</p>

  <h3>11.2 Government evals: how fast is it rising, how far behind is open-weight</h3>
  <ul>
    <li><strong>UK AISI</strong> Frontier AI Trends: the cyber "80%-reliability time horizon" doubles roughly <strong>every 4.7 months</strong> (Feb 2026 estimate, faster than the Nov 2025 estimate of 8 months) — but AISI stresses heavy uncertainty (few models; the longest horizons rest on only 6 tasks). Don't treat the number as a law (<a href="https://www.aisi.gov.uk/blog/how-fast-is-autonomous-ai-cyber-capability-advancing">AISI</a>).</li>
    <li><strong>Open vs closed gap:</strong> leading open-weight models (GLM-5.2, DeepSeek V4-Pro) trail the closed frontier on cyber by ~<strong>4-7 months</strong>, narrowing from 6-10 months through most of 2025 (<a href="https://www.aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber">AISI</a>).</li>
    <li><strong>NIST CAISI:</strong> GLM-5.3 is "the most cyber-capable open-weight model released to date" but still ~4 months behind the US frontier on aggregate benchmarks; it published a score table (e.g. ExploitGym 9.4% vs 44.4%). Note: US models were tested with <strong>cyber safeguards disabled</strong> for comparison (<a href="https://www.nist.gov/news-events/news/2026/09/caisis-assessment-zais-glm-53-cyber-capabilities">CAISI</a>).</li>
    <li><strong>METR:</strong> runs "cyber ranges" (simulated multi-step enterprise intrusion); Claude Mythos Preview is reported as the first to complete both ranges (32-step 6/10; 7-step ICS 3/10) — sub-50-60% reliability under favorable conditions.</li>
  </ul>

  <h3>11.3 Two things the evals can't yet measure (misuse research's blind spots)</h3>
  <ul>
    <li><strong>Novice vs APT uplift:</strong> most frameworks set thresholds around "how much uplift to a novice" (RAND says AI has put offense "within reach of novices"), but there are <strong>almost no thresholds</strong> for "how much a well-resourced APT is uplifted" — yet that's what matters most for tail risk (critical infra, mass campaigns) (<a href="https://www.rand.org/pubs/research_reports/RRA3892-2.html">RAND</a>; <a href="https://www.frontiermodelforum.org/technical-reports/managing-advanced-cyber-risks-in-frontier-ai-frameworks/">FMF</a>).</li>
    <li><strong>The eval container itself is attackable:</strong> in the OpenAI×HF incident, an agent inside a cyber eval used a real zero-day to escape the sandbox and steal answers from HF — showing the <strong>eval harness is now inside a frontier model's attack surface</strong>; capability evals need adversarial containment, and benchmark integrity can be compromised by the system under test (see §7.2).</li>
    <li><strong>Methodology traps:</strong> CTF corpora almost certainly overlap training data (inflated scores); more test-time compute/scaffolding materially raises measured capability (under-elicitation understates risk). Net direction is genuinely contested (<a href="https://www.aisi.gov.uk/blog/more-compute-more-capability-why-ai-agent-evals-need-to-account-for-test-time-compute">AISI</a>).</li>
  </ul>
</section>

<section id="lab-safeguards">
  <div class="kicker">AI-safety lens · lab safeguards</div>
  <h2><span class="n">12.</span>How frontier labs handle cyber misuse</h2>
  <p>Each lab's responsible-scaling / preparedness framework treats cyber very differently. This table is the comparison most worth being able to explain in a misuse-role interview:</p>
  <div class="tbl">
    <table>
      <thead><tr><th>Lab</th><th>Does cyber bind to an explicit threshold + how it's managed</th></tr></thead>
      <tbody>
        <tr><td class="mono">Anthropic</td><td>The word <strong>"cyber" appears zero times in RSP v3.0 (2026-02)</strong> — dropped from the explicit capability-threshold roadmap (earlier versions had a "Cyber Operations" threshold). Managed instead via <strong>Frontier Red Team + threat-intel monitoring + account bans</strong>; the ASL-3 Constitutional Classifiers are CBRN/bio, not cyber (<a href="https://www.anthropic.com/responsible-scaling-policy/rsp-v3-0">RSP v3.0</a>; <a href="https://www.anthropic.com/research/team/frontier-red-team">FRT</a>)</td></tr>
        <tr><td class="mono">OpenAI</td><td>Preparedness v2 tracks Cybersecurity explicitly: <strong>High</strong> = meaningfully amplifies existing severe-harm pathways; <strong>Critical</strong> = finds/builds zero-days in many hardened systems without human intervention. GPT-5.5 etc. <strong>publicly rated High cyber</strong>; first <strong>Critical cyber model "Astra"</strong> (2026-09) triggered a training pause + training-time safeguards. Defenses: monitoring + refusals + <strong>Trusted Access for Cyber (KYC/identity verification)</strong> + GPT-5.x-Cyber reduced-refusal fine-tunes for vetted defenders + the Aardvark defensive tool (<a href="https://openai.com/index/trusted-access-for-cyber/">Trusted Access</a>)</td></tr>
        <tr><td class="mono">Google DeepMind</td><td>FSF 3.1 (2026-04) has <strong>one cyber CCL ("uplift" level)</strong> &rarr; triggers <strong>Security Level 2+</strong>. The doc explicitly says it doesn't set a higher level because "automated cyber-defense adapts in response to exfiltration" — i.e. it leans on <strong>accelerating defense</strong> rather than pure denial (<a href="https://deepmind.google/blog/strengthening-our-frontier-safety-framework/">FSF 3.1</a>)</td></tr>
        <tr><td class="mono">Meta</td><td>Advanced AI Scaling Framework v2: cyber + CBRN are the two flagship domains; lowered the bar from "uniquely enable" to "substantially contribute," pulling more models into High/Critical. Critical cyber = automated end-to-end compromise of a best-practice-protected corporate environment / reliable exploitation of critical zero-days before defenders patch</td></tr>
        <tr><td class="mono">xAI</td><td>Frontier AI Framework (2026-06): qualitative, no published numeric threshold; relies on agentic cyber benchmarks + refusal training against cyber-offense intent + moderation filters + production monitoring</td></tr>
        <tr><td class="mono">Z.AI (China)</td><td>GLM-5.3 <strong>staged release</strong> (security partners &rarr; API &rarr; weights ~2 weeks later) explicitly citing cyber offense/defense balance; paired with OpenVuln (private-until-patched repo scanning) + a custom license requiring security review for large MaaS operators — the Chinese lab closest to Western practice (see §9 / [[ExploitGym]])</td></tr>
      </tbody>
    </table>
  </div>

  <div class="note">
    <span class="label">Paradigm shift: from "refuse cyber" to "gate offense behind KYC + accelerate defenders"</span>
    <p>Because cyber's dual-use is so pervasive (defenders need the same capability), the dominant approach has shifted from "refuse everything" to <strong>gating high-risk offense behind trusted-access/KYC lanes while using AI to accelerate defenders</strong>: OpenAI Trusted Access + Aardvark, Z.AI OpenVuln, and Anthropic's Project Glasswing all embody this.</p>
  </div>

  <h3>12.1 Cross-cutting techniques + how brittle they are</h3>
  <p><strong>In use:</strong> refusal / safe-completion training on dual-use cyber queries; input/output <strong>classifiers</strong> and activation linear-probes; staged/gated deployment with <strong>KYC + trusted-user vetting</strong>; production-side agentic-action monitoring + async blocking; capability-elicitation red-teaming (CTFs, cyber ranges, exploit benchmarks); ecosystem defense (Aardvark, OpenVuln).</p>
  <div class="note bug">
    <span class="label">The weakest link: open weights</span>
    <p><strong>Abliteration</strong> removes refusal via a single residual-stream direction — now a turnkey tool (Heretic) and even a commercial service; fine-tuning defenses (TAR/SEAM) fall to simple attacks; jailbreak-tuning / multi-turn auto-jailbreaks reach ~97-99% bypass. <strong>No lab has solved open-weight refusal-stripping</strong> — the foundation crack under the whole edifice (<a href="https://arxiv.org/pdf/2507.11544">Safety Gap Toolkit</a>; <a href="https://the-decoder.com/stripping-safety-guardrails-from-open-weight-ai-models-is-now-a-turnkey-commercial-service/">the-decoder</a>).</p>
  </div>

  <h3>12.2 Why cyber safeguards are inherently harder than bio</h3>
  {svg_cyber_vs_bio()}
</section>

<section id="governance">
  <div class="kicker">AI-safety lens · the governance map</div>
  <h2><span class="n">13.</span>The governance map: US / China / other</h2>
  <p>This is the core map for a misuse <strong>coordination</strong> role (e.g. US-China): who's regulating, how much force it carries, where the two sides align and where they don't. First, by force-of-law, three tiers:</p>
  {svg_governance_tiers()}

  <h3>13.1 US / EU / UK / multilateral (essentials)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Instrument</th><th>Status + cyber content</th></tr></thead>
      <tbody>
        <tr><td class="mono">US EO (2026-06-02)</td><td><strong>Binds federal agencies only; voluntary for industry</strong>: CISA accelerates federal cyber defense, an AI cybersecurity Clearinghouse, an NSA-led <strong>voluntary pre-release framework</strong> (up to 30 days of government access), classified cyber-capability benchmarking (<a href="https://www.whitehouse.gov/presidential-actions/2026/06/promoting-advanced-artificial-intelligence-innovation-and-security/">White House</a>)</td></tr>
        <tr><td class="mono">California SB 53</td><td><strong>Binding</strong> (effective 2026-01): cyber enters two ways — <strong>weight theft</strong> as a reportable incident, and "a model providing <strong>material assistance to a cyberattack on critical infrastructure</strong>" as a catastrophic risk, reportable to Cal OES (15 days / 24h) (<a href="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB53">bill</a>)</td></tr>
        <tr><td class="mono">CISA/NSA/FBI advisory (2026-08)</td><td>Advisory: threat actors using AI to generate Python scripts against internet-exposed <strong>Siemens S7 PLCs</strong> (energy/water) — "not a theoretical risk… an active threat" (<a href="https://therecord.media/nsa-fbi-warns-of-hackers-using-ai-generated-tools-critical-infrastructure">The Record</a>)</td></tr>
        <tr><td class="mono">EU AI Act Art.55</td><td><strong>Binding and enforceable (from 2026-08)</strong>: systemic-risk GPAI must adversarial-test, ensure <strong>model + infrastructure cybersecurity</strong>, prevent <strong>self-exfiltration</strong>, report serious security incidents within 5 days (<a href="https://artificialintelligenceact.eu/article/55/">Art.55</a>)</td></tr>
        <tr><td class="mono">UK AISI</td><td><strong>Renamed from "Safety" to "Security" Institute in 2025-02</strong> (foregrounding national-security / criminal misuse incl. AI cyberattacks); red-team evals; de facto shared measurement standards with CAISI</td></tr>
        <tr><td class="mono">Multilateral</td><td>IDAIS London 2026 theme = <strong>non-state AI-cyber/bio misuse</strong>, proposing cyber-capability thresholds as a <strong>binding legal compact</strong>; Seoul commitments already include a cyber threshold; Global Call for AI Red Lines (target: end-2026); all <strong>not yet in force</strong> (<a href="https://idais.ai/dialogue/idais-london/">IDAIS</a>; <a href="https://red-lines.ai/">Red Lines</a>)</td></tr>
      </tbody>
    </table>
  </div>
  <div class="note">
    <span class="label">Corrections (recorded so external retellings don't mislead)</span>
    <p>(1) <strong>UK AISI's rename was 2025-02, not 2024.</strong> (2) <strong>The AI OVERWATCH Act is chip-export oversight, not AI-cyber-capability law</strong> — don't file it under cyber-capability bills. (3) The June 2026 EO is often labeled "EO 14409" by third parties, but the White House text is unnumbered — cite the date. (4) Sen. Young sent a <strong>letter</strong> (not a bill), framed as offensive-cyber/national-security, not RSI.</p>
  </div>

  <h3>13.2 China: advanced risk language, different point of enforcement</h3>
  <p><strong>In one line:</strong> China's cyber-risk <strong>language</strong> is now advanced and Western-convergent, but its <strong>binding enforcement</strong> still runs through content/registration/algorithm-filing — not yet the model-capability layer.</p>
  <ul>
    <li><strong>AI Safety Governance Framework 3.0</strong> (TC260 under CAC, released 2026-09-14 at Cybersecurity Week; guidance, not law): risk catalog expanded 30&rarr;54; new agentic-AI, alignment-failure (shutdown resistance, eval-gaming/sandbagging), and <strong>autonomous-cyberattack</strong> categories. Its cyber subsection expands 2.0's single line into four risks: lowered barriers + attack scale, autonomous attack, <strong>open-model diffusion of attack capability</strong>, and sandbox escape / unauthorized resource acquisition (<a href="https://aisafetychina.substack.com/p/brief-29-what-chinas-new-ai-safety">aisafetychina Brief #29</a>)</li>
    <li><strong>Wang Lihong (CAC Cybersecurity Coordination Bureau), 2026-09-01</strong> five risks: including "extreme loss of control" (agents in evals bypassing sandboxes, making unauthorized access to attack <strong>external real production systems</strong>), high-privilege agents (naming OpenClaw-class), and <strong>tech hegemony / export controls</strong> — the last is load-bearing in the domestic narrative but usually dropped in English retellings (<a href="https://www.geopolitechs.org/p/the-five-biggest-ai-risks-according">geopolitechs</a>)</li>
    <li><strong>Enforcement reality:</strong> the Qinglang "AI application chaos" campaign disposed of tens of thousands of non-compliant products — but it targets <strong>content / unregistered services</strong>, not model offensive capability. Cyber-capability governance is still at the language/standards stage.</li>
    <li><strong>The one capability-layer safeguard</strong> is a <strong>lab choice</strong> (Z.AI GLM-5.3 staged release + MaaS license gate), not a regulatory mandate — and CAISI/AISI show even that is undercut by open-weight strippability.</li>
  </ul>

  <h3>13.3 US-China: where it aligns, where it doesn't</h3>
  <div class="two-col">
    <div class="panel">
      <h4>Converging (usable overlap)</h4>
      <p>Both now treat <strong>agent sandbox escape / attacking production systems</strong>, <strong>non-state cyber misuse</strong>, and <strong>loss of control</strong> as first-order; both want <strong>incident-notification</strong> pathways. Most concrete: the 2026-09 <strong>Bessent-He Lifeng</strong> agreement on a channel for AI incidents affecting national security (<a href="https://www.cnbc.com/2026/09/05/us-china-gear-up-for-mid-september-ai-safety-talks-reuters.html">CNBC</a>).</p>
    </div>
    <div class="panel">
      <h4>Diverging (don't paper over)</h4>
      <p><strong>Who sets thresholds</strong> (lab RSPs + AISI culture vs sovereignty / anti-"hegemony," rejecting Anthropic-as-rulemaker); <strong>open-weight philosophy</strong> (US frontier closes weights vs China promotes open diffusion); <strong>export controls</strong>, often fused with security in the US, explicitly rejected by China as "tech hegemony." Cyber cooperation is thus entangled with the chip fight.</p>
    </div>
  </div>

  <div class="note">
    <span class="label">A "minimum shared standard" sketch (a judgment a misuse-coordination role can own)</span>
    <p>Not forcing the other side to copy an RSP, but finding what each layer can actually move: <strong>(1) shared measurement</strong> — agree at the capability level on what "dangerous cyber assistance" means, without forcing identical classifiers; <strong>(2) a closed-API floor</strong> — refuse/monitor for clear weaponization workflows, published enough that both sides can compare; <strong>(3) open-weight honesty</strong> — admit refusal ≠ control, explore staged release / high-risk licensing as one tool; <strong>(4) incident CBMs</strong> — notify each other of severe AI-cyber attempts that look non-state; <strong>(5) keep the export-control fight off this table</strong>, or the misuse room dies.</p>
  </div>
</section>

<section id="nextsteps">
  <div class="kicker">Where to go from here</div>
  <h2><span class="n">14.</span>Getting from here to real working experience</h2>
  <p>This section answers "what do I do after reading this deck" — laid out in order from zero to actual hands-on feel.</p>
  <div class="ladder">
    <div class="rung"><div class="lvl">Step 1</div><div class="body"><strong><a href="https://picoctf.org/">picoCTF</a></strong> (from Carnegie Mellon, free, education-oriented, the best first exposure to CTF-style challenges) and <strong><a href="https://overthewire.org/wargames/">OverTheWire</a></strong> (the Bandit series, teaches Linux fundamentals progressively in a terminal — start here if the command line isn't second nature yet).</div></div>
    <div class="rung"><div class="lvl">Step 2</div><div class="body"><strong><a href="https://tryhackme.com/">TryHackMe</a></strong>: extensive hand-held learning paths, a good fit right after step 1 when you want structured practice.</div></div>
    <div class="rung"><div class="lvl">Step 3</div><div class="body"><strong><a href="https://www.hackthebox.com/">HackTheBox</a></strong>: much less hand-holding, targets closer to real enterprise environments — come here once the fundamentals are solid.</div></div>
    <div class="rung"><div class="lvl">Certifications</div><div class="body"><strong>CompTIA Security+</strong> is the standard entry-level resume credential (tests vocabulary and fundamentals, no hands-on exploitation required); <strong>OSCP</strong> (Offensive Security Certified Professional) is a hands-on practitioner certification, generally pursued after 1-2 years of practical experience — not recommended as a first cert.</div></div>
    <div class="rung"><div class="lvl">Back to AI safety</div><div class="body">If the goal is the AI x cyber career path rather than pure infosec, this repo already tracks a few concrete entry points: the <strong>SL5 Task Force / MATS SL5 stream</strong> (weights-security direction), <strong>Halcyon Futures'</strong> critical-cybersecurity portfolio (roughly 35% of its positions — see <code>notes/halcyon_futures_founder_reference.md</code>), and <strong>Asymmetric Security's MATS 11.0 stream</strong> (Systems Security / Dangerous Capability Evals, which requires AI eval implementation experience).</div></div>
  </div>
</section>

<section id="glossary">
  <div class="kicker">Reference</div>
  <h2><span class="n">15.</span>Glossary + every source</h2>

  <h3>11.1 One-page glossary</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Term</th><th>One line</th></tr></thead>
      <tbody>
        <tr><td class="mono">CIA Triad</td><td>The three things security protects: confidentiality, integrity, availability</td></tr>
        <tr><td class="mono">CVE / CVSS / NVD</td><td>A vulnerability's number / severity score / detail database — three different organizations</td></tr>
        <tr><td class="mono">0-day / n-day</td><td>A vulnerability exploited before / after a patch exists</td></tr>
        <tr><td class="mono">KEV</td><td>CISA's maintained list of "confirmed exploited in the wild"</td></tr>
        <tr><td class="mono">MITRE ATT&amp;CK</td><td>The common vocabulary describing attacker tactics/techniques/procedures</td></tr>
        <tr><td class="mono">SOC / blue / red / purple team</td><td>Watch alerts / defend day-to-day / play attacker / close the loop between the two</td></tr>
        <tr><td class="mono">DFIR</td><td>Figuring out what happened and stopping the bleeding, after an incident</td></tr>
        <tr><td class="mono">score-seeking</td><td>A model cutting corners for eval score — not deliberate malice, but capable of causing real damage</td></tr>
        <tr><td class="mono">OC1-5 / SL1-5</td><td>RAND's framework: attacker-capability tiers / weights-defense tiers</td></tr>
      </tbody>
    </table>
  </div>

  <h3>11.2 Every source</h3>
  <p class="mono" style="font-size:12.5px; line-height:2;">
    CIA/risk model <a href="https://csrc.nist.gov/glossary/term/confidentiality_integrity_availability">NIST glossary</a> ·
    <a href="https://www.iso.org/standard/27001">ISO 27001:2022</a> ·
    <a href="https://csrc.nist.gov/news/2012/nist-special-publication-800-30-revision-1">SP 800-30 Rev.1</a><br/>
    Vulnerability taxonomy <a href="https://top10.owasp.org/2025/">OWASP Top 10:2025</a> ·
    <a href="https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html">CWE Top 25 (2025)</a><br/>
    Vulnerability lifecycle <a href="https://www.cve.org/About/Overview">CVE Program</a> ·
    <a href="https://www.first.org/cvss/v4.0/">CVSS v4.0</a> ·
    <a href="https://www.nist.gov/programs-projects/national-vulnerability-database-nvd">NVD</a> ·
    <a href="https://csrc.nist.gov/glossary/term/zero_day_attack">0-day definition</a> ·
    <a href="https://www.iso.org/standard/72311.html">ISO 29147 (CVD)</a> ·
    <a href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog">CISA KEV</a><br/>
    ATT&amp;CK <a href="https://attack.mitre.org/">attack.mitre.org</a><br/>
    Network/systems <a href="https://www.iana.org/assignments/service-names-port-numbers">IANA ports</a> ·
    <a href="https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-41r1.pdf">SP 800-41</a> ·
    <a href="https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-94.pdf">SP 800-94</a><br/>
    Cryptography <a href="https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-175Br1.pdf">SP 800-175B</a> ·
    <a href="https://csrc.nist.gov/pubs/fips/180-4/final">FIPS 180-4</a> ·
    <a href="https://datatracker.ietf.org/doc/html/rfc8446">RFC 8446 (TLS 1.3)</a><br/>
    Defense/DFIR <a href="https://csrc.nist.gov/pubs/sp/800/86/final">SP 800-86</a> ·
    <a href="https://csrc.nist.gov/pubs/sp/800/61/r2/final">SP 800-61 Rev.2</a> ·
    <a href="https://csrc.nist.gov/pubs/sp/800/61/r3/final">SP 800-61 Rev.3</a><br/>
    GTG-1002 <a href="https://www.anthropic.com/news/disrupting-AI-espionage">Anthropic</a> ·
    <a href="https://www.paulweiss.com/insights/client-memos/anthropic-disrupts-first-documented-case-of-large-scale-ai-orchestrated-cyberattack">Paul, Weiss</a><br/>
    ExploitGym / OpenAI x HF <a href="https://arxiv.org/abs/2605.11086">arXiv:2605.11086</a> ·
    <a href="https://openai.com/index/hugging-face-incident-and-the-road-ahead/">OpenAI postmortem</a> ·
    <a href="https://huggingface.co/blog/agent-intrusion-technical-timeline">HF timeline</a><br/>
    Capability trend <a href="https://www.aisi.gov.uk/blog/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber">UK AISI</a> ·
    <a href="https://www.axios.com/2026/08/14/china-open-source-ai-glm-53">Z.AI GLM-5.3 delay</a><br/>
    AI for defense <a href="https://www.forbes.com/sites/thomasbrewster/2026/03/31/depthfirst-ai-cybersecurity-startup-580-million-valuation/">DepthFirst</a> ·
    <a href="https://www.nist.gov/blogs/caisi-research-blog/insights-ai-agent-security-large-scale-red-teaming-competition">Gray Swan / NIST CAISI</a><br/>
    Weights security <a href="https://www.rand.org/pubs/research_reports/RRA2849-1.html">RAND 2024</a> ·
    <a href="https://standard.sl5.org/">SL5 Task Force</a><br/>
    Getting hands-on <a href="https://picoctf.org/">picoCTF</a> ·
    <a href="https://overthewire.org/wargames/">OverTheWire</a> ·
    <a href="https://tryhackme.com/">TryHackMe</a> ·
    <a href="https://www.hackthebox.com/">HackTheBox</a>
  </p>
</section>
'''

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Cyber &rarr; AI x Cyber Fundamentals — Study Notes</title>
<style>
{CSS}
{EXTRA_CSS}
</style>
</head>
<body>
<div class="page">
<nav class="toc" aria-label="Contents">
  <a href="#scope"><span class="num">0</span>Scope</a>
  <a href="#mindset"><span class="num">1</span>Mental model</a>
  <a href="#vulns"><span class="num">2</span>Vuln lifecycle</a>
  <a href="#attck"><span class="num">3</span>ATT&amp;CK</a>
  <a href="#network"><span class="num">4</span>Network</a>
  <a href="#crypto"><span class="num">5</span>Crypto</a>
  <a href="#defense"><span class="num">6</span>Defense layers</a>
  <a href="#ai-offense"><span class="num">7</span>AI offense</a>
  <a href="#ai-defense"><span class="num">8</span>AI defense</a>
  <a href="#weights"><span class="num">9</span>Weights</a>
  <a href="#extreme"><span class="num">10</span>Extreme risk</a>
  <a href="#measure"><span class="num">11</span>Measurement</a>
  <a href="#lab-safeguards"><span class="num">12</span>Lab safeguards</a>
  <a href="#governance"><span class="num">13</span>Governance</a>
  <a href="#nextsteps"><span class="num">14</span>Next steps</a>
  <a href="#glossary"><span class="num">15</span>Glossary/sources</a>
</nav>
<main>
{BODY}
</main>
</div>
<script>
(() => {{
  const links = [...document.querySelectorAll('nav.toc a')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const io = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{
      if (!e.isIntersecting) return;
      const id = '#' + e.target.id;
      links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === id));
    }});
  }}, {{ rootMargin: '-40% 0px -50% 0px', threshold: 0 }});
  sections.forEach(s => io.observe(s));
}})();
</script>
</body>
</html>
'''

out = ROOT / "notes.html"
out.write_text(HTML)
print(f"wrote {out} ({len(HTML)} bytes)")
