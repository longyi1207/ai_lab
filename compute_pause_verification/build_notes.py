#!/usr/bin/env python3
"""Build notes.html for compute-pause verification study deck (dist_training_lab style)."""
from pathlib import Path
import svg_panels

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
    display: grid; grid-template-columns: 72px 1fr; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid var(--rule-soft); align-items: start;
  }
  .ladder .rung:last-child { border-bottom: none; }
  .ladder .lvl { color: var(--accent); font-weight: 600; }
  .ladder .body { color: var(--ink-dim); line-height: 1.55; font-family: system-ui, sans-serif; font-size: 14.5px; }
  .ladder .body strong { color: var(--ink); }
  @media print {
    nav.toc { display: none !important; }
    main { max-width: 100%; padding: 24px 32px; }
    section { break-inside: avoid; page-break-inside: avoid; }
    figure, .svg-fig { break-inside: avoid; }
    a { color: var(--ink); text-decoration: none; }
  }
"""

def svg_claims():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.4; }
  </style>
  <text x="24" y="22" class="h">Four different sentences people call “AI verification” — only one is this deck’s focus</text>
  <rect x="24" y="36" width="160" height="150" rx="4" class="hi"/>
  <text x="36" y="58" class="t">Claim A</text>
  <text x="36" y="78" class="s">No covert frontier</text>
  <text x="36" y="94" class="s">training / only</text>
  <text x="36" y="110" class="s">allowed workloads</text>
  <text x="36" y="132" class="s">Who cares: treaties,</text>
  <text x="36" y="148" class="s">pause / slowdown,</text>
  <text x="36" y="164" class="s">export controls</text>
  <text x="36" y="180" class="s">THIS DECK</text>
  <rect x="196" y="36" width="160" height="150" rx="4" class="box"/>
  <text x="208" y="58" class="t">Claim B</text>
  <text x="208" y="78" class="s">You got the model</text>
  <text x="208" y="94" class="s">you were sold /</text>
  <text x="208" y="110" class="s">audited</text>
  <text x="208" y="132" class="s">Who cares: banks,</text>
  <text x="208" y="148" class="s">hospitals, buyers</text>
  <text x="208" y="164" class="s">Tech: identity,</text>
  <text x="208" y="180" class="s">recompute, DRM-ish</text>
  <rect x="368" y="36" width="160" height="150" rx="4" class="box"/>
  <text x="380" y="58" class="t">Claim C</text>
  <text x="380" y="78" class="s">Run happened in</text>
  <text x="380" y="94" class="s">this jurisdiction /</text>
  <text x="380" y="110" class="s">TEE; cloud can’t peek</text>
  <text x="380" y="132" class="s">Who cares: sovereignty,</text>
  <text x="380" y="148" class="s">GDPR, enterprise</text>
  <text x="380" y="164" class="s">Tech: CC / TEE,</text>
  <text x="380" y="180" class="s">attestation, location</text>
  <rect x="540" y="36" width="160" height="150" rx="4" class="box"/>
  <text x="552" y="58" class="t">Claim D</text>
  <text x="552" y="78" class="s">This agent only</text>
  <text x="552" y="94" class="s">did approved tool</text>
  <text x="552" y="110" class="s">calls</text>
  <text x="552" y="132" class="s">Who cares: agent</text>
  <text x="552" y="148" class="s">users / enterprises</text>
  <text x="552" y="164" class="s">Tech: audit trails,</text>
  <text x="552" y="180" class="s">policy engines</text>
</svg>
<p class="cap">Mixing claims is the most common briefing failure. FlexHEG / Cankaya / joshc / Rahman are mostly Claim A. Commercial TEE “AI Passport” products are mostly B/C (sometimes D) — useful, but they do not by themselves prove “no covert training.”</p>
</div>'''

def svg_lineage():
    """Single Claim A figure: reading order (#) + real motivates/hardens edges."""
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Claim A lineage">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .ly { font: 600 9.5px ui-monospace, monospace; fill: #8a867a; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); stroke-width: 1; }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.3; }
    .arr { stroke: #8a867a; stroke-width: 1.15; fill: none; marker-end: url(#ml); }
  </style>
  <defs>
    <marker id="ml" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="20" class="h">Claim A lineage — arrows = motivates / hardens / implements a slice (not call-stack)</text>
  <text x="24" y="36" class="s">Numbers = deck reading order. Same row = siblings (different tools), not “later replaces earlier.”</text>

  <!-- #1 Wasil -->
  <rect x="270" y="48" width="180" height="44" rx="3" class="box"/>
  <text x="282" y="66" class="t">1 Wasil 2024</text>
  <text x="282" y="82" class="s">method menu</text>
  <text x="24" y="74" class="ly">menu</text>

  <path d="M300 92 L120 118" class="arr"/>
  <path d="M360 92 L360 118" class="arr"/>
  <path d="M420 92 L600 118" class="arr"/>

  <!-- row: classical | near-term | hardware -->
  <rect x="40" y="124" width="160" height="50" rx="3" class="box"/>
  <text x="52" y="144" class="t">2 Shavit + PoL</text>
  <text x="52" y="160" class="s">chip + transcript</text>
  <text x="24" y="118" class="ly">classical</text>

  <rect x="280" y="124" width="160" height="50" rx="3" class="box"/>
  <text x="292" y="144" class="t">4 joshc 2026</text>
  <text x="292" y="160" class="s">TAP / wipe red-team</text>
  <text x="280" y="118" class="ly">near-term facility</text>

  <rect x="520" y="124" width="160" height="50" rx="3" class="hi"/>
  <text x="532" y="144" class="t">8 FlexHEG</text>
  <text x="532" y="160" class="s">active caps / shell</text>
  <text x="520" y="118" class="ly">hardware track</text>

  <path d="M90 174 L90 198" class="arr"/>
  <path d="M160 174 L280 214" class="arr"/>
  <path d="M360 174 L360 198" class="arr"/>

  <!-- hardeners + Cankaya -->
  <rect x="40" y="204" width="160" height="50" rx="3" class="box"/>
  <text x="52" y="224" class="t">3 Rahman 2026</text>
  <text x="52" y="240" class="s">train↔infer NVML</text>
  <text x="24" y="198" class="ly">thin detector</text>

  <rect x="280" y="204" width="160" height="50" rx="3" class="box"/>
  <text x="292" y="224" class="t">9 Peigné 2026</text>
  <text x="292" y="240" class="s">ZK training horizon</text>
  <text x="280" y="198" class="ly">training crypto</text>

  <rect x="480" y="204" width="200" height="56" rx="3" class="hi"/>
  <text x="492" y="224" class="t">5 Cankaya 2026</text>
  <text x="492" y="240" class="s">taps · bit-exact · Plan A/B</text>
  <text x="480" y="198" class="ly">retrofit blueprint</text>

  <path d="M580 174 L580 202" class="arr"/>
  <path d="M580 260 L580 278" class="arr"/>

  <rect x="470" y="282" width="220" height="44" rx="3" class="box"/>
  <text x="482" y="300" class="t">6–7 zkLLM · VerInf · DiFR</text>
  <text x="482" y="316" class="s">Plan B evaluate engines</text>
  <text x="24" y="308" class="ly">inference crypto</text>

  <text x="24" y="348" class="s">FlexHEG ∥ Cankaya: longer silicon track vs near-term facility retrofit — complementary, not sequential.</text>
</svg>
<p class="cap">Wasil orients. Shavit designs classical monitoring; Rahman / Peigné harden thin slices of it (telemetry vs ZK transcripts). joshc stress-tests cheap facility controls → Cankaya assembles the retrofit; zkLLM/VerInf/DiFR sit under Plan B evaluate. FlexHEG is the parallel hardware-enforcement track.</p>
</div>'''
def svg_wasil():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.15); }
  </style>
  <text x="24" y="24" class="h">A · National Technical Means</text>
  <rect x="24" y="36" width="210" height="100" rx="4" class="box"/>
  <text x="36" y="58" class="t">① remote sensing</text>
  <text x="36" y="76" class="t">② whistleblowers</text>
  <text x="36" y="94" class="t">③ energy monitoring</text>
  <text x="36" y="112" class="t">④ customs · ⑤ finance</text>
  <text x="36" y="128" class="s">little access needed</text>

  <text x="256" y="24" class="h">B · Access-dependent</text>
  <rect x="256" y="36" width="210" height="100" rx="4" class="box"/>
  <text x="268" y="58" class="t">⑥ DC inspections</text>
  <text x="268" y="76" class="t">⑦ fab inspections</text>
  <text x="268" y="94" class="t">⑧ developer audits</text>
  <text x="268" y="112" class="s">need consent / entry</text>
  <text x="268" y="128" class="s">IAEA-flavored</text>

  <text x="488" y="24" class="h">C · Hardware-dependent</text>
  <rect x="488" y="36" width="208" height="100" rx="4" class="box"/>
  <text x="500" y="58" class="t">⑨ chip location track</text>
  <text x="500" y="76" class="t">⑩ on-chip / workload</text>
  <text x="500" y="94" class="s">pre-agree chip rules</text>
  <text x="500" y="112" class="s">→ Shavit / FlexHEG</text>

  <text x="24" y="172" class="t">Swiss-cheese model</text>
  <rect x="24" y="186" width="672" height="18" rx="2" fill="#e8e2d6" stroke="rgba(26,26,24,0.12)"/>
  <circle cx="80" cy="195" r="5" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="200" cy="195" r="4" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="340" cy="195" r="6" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="480" cy="195" r="4" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="600" cy="195" r="5" fill="#fdfcfb" stroke="#9a5b12"/>
  <rect x="24" y="214" width="672" height="18" rx="2" fill="#e8e2d6" stroke="rgba(26,26,24,0.12)"/>
  <circle cx="120" cy="223" r="4" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="280" cy="223" r="5" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="520" cy="223" r="6" fill="#fdfcfb" stroke="#9a5b12"/>
  <rect x="24" y="242" width="672" height="18" rx="2" fill="#e8e2d6" stroke="rgba(26,26,24,0.12)"/>
  <circle cx="180" cy="251" r="5" fill="#fdfcfb" stroke="#9a5b12"/>
  <circle cx="420" cy="251" r="4" fill="#fdfcfb" stroke="#9a5b12"/>
  <text x="24" y="278" class="s">each layer has holes; stacked layers make covert breach harder (Fearon / Baker: verifiable agreements are more signable)</text>
</svg>
<p class="cap">Wasil taxonomy: cooperation cost ↑ left→right; technical bite ↑ left→right. Not a system design — a menu.</p>
</div>'''

def svg_shavit():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#m2); }
  </style>
  <defs>
    <marker id="m2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <rect x="40" y="30" width="160" height="70" rx="4" class="box"/>
  <text x="52" y="54" class="t">① Chip firmware</text>
  <text x="52" y="74" class="s">sparse weight snapshot</text>
  <text x="52" y="90" class="s">secure-boot signed FW</text>
  <path d="M200 65 L250 65" class="arr"/>
  <rect x="250" y="30" width="180" height="70" rx="4" class="box"/>
  <text x="262" y="54" class="t">② Transcript + PoL</text>
  <text x="262" y="74" class="s">data / hparams / ckpts</text>
  <text x="262" y="90" class="s">spot-check recompute</text>
  <path d="M430 65 L480 65" class="arr"/>
  <rect x="480" y="30" width="180" height="70" rx="4" class="box"/>
  <text x="492" y="54" class="t">③ Supply registry</text>
  <text x="492" y="74" class="s">known ML chips only</text>
  <text x="492" y="90" class="s">spot physical audit</text>

  <rect x="120" y="140" width="480" height="130" rx="4" class="box"/>
  <text x="140" y="168" class="t">PoL check (Jia et al. intuition)</text>
  <text x="140" y="192" class="s">Claim: W_T came from (W_0, D, A) under claimed optimizer steps</text>
  <text x="140" y="214" class="s">Verifier samples steps i → recompute / check consistency with snapshots</text>
  <text x="140" y="236" class="s">Mismatch ⇒ lying about process  ·  Match + illegal FLOP ⇒ rule break</text>
  <text x="140" y="258" class="s">Refuse audit ≈ adverse inference (audit analogy)</text>
</svg>
<p class="cap">Shavit stack: fingerprints on chip + proof the transcript explains them + no dark chips outside the registry.</p>
</div>'''

def svg_joshc():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 320" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .bad { fill: #f3e8e0; stroke: #9a5b12; }
    .ok { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#m3); }
  </style>
  <defs>
    <marker id="m3" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="24" class="t">Naive story: training needs fat interconnect; inference needs skinny text</text>
  <rect x="24" y="44" width="200" height="56" rx="4" class="ok"/>
  <text x="36" y="68" class="t">pull IB / limit BW</text>
  <text x="36" y="86" class="s">e.g. ~100 KB/s/rack</text>
  <path d="M224 72 L270 72" class="arr"/>
  <rect x="270" y="44" width="200" height="56" rx="4" class="ok"/>
  <text x="282" y="68" class="t">output recompute</text>
  <text x="282" y="86" class="s">TAP + spot check M</text>
  <path d="M470 72 L516 72" class="arr"/>
  <rect x="516" y="44" width="180" height="56" rx="4" class="ok"/>
  <text x="528" y="68" class="t">“training slowed”</text>
  <text x="528" y="86" class="s">hope, not theorem</text>

  <text x="24" y="140" class="t">Covert RL under leaky recompute (~1% error budget + ~5% dark compute)</text>
  <rect x="24" y="156" width="300" height="80" rx="4" class="ok"/>
  <text x="36" y="180" class="t">95% “inference” racks</text>
  <text x="36" y="198" class="s">generate rollouts (looks like serving)</text>
  <text x="36" y="216" class="s">smuggle top rollouts in error budget</text>
  <path d="M324 196 L370 196" class="arr"/>
  <rect x="370" y="156" width="326" height="80" rx="4" class="bad"/>
  <text x="382" y="180" class="t">~5% dark racks</text>
  <text x="382" y="198" class="s">actual parameter updates</text>
  <text x="382" y="216" class="s">push small experts back every few hrs</text>

  <text x="24" y="268" class="t">Thresholds to break this (any one, vs current algos)</text>
  <text x="24" y="290" class="s">PoW/PoM covers &gt;95% · memory wipe every few minutes · covert channel ≪0.01% of traffic</text>
</svg>
<p class="cap">joshc’s killer scenario: compliant-looking RL rollouts + dark updater. Near-term network controls without those thresholds may not buy a real pause.</p>
</div>'''

def svg_flexheg():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .shell { fill: none; stroke: #9a5b12; stroke-width: 1.6; stroke-dasharray: 4 3; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <rect x="80" y="36" width="560" height="180" rx="8" class="shell"/>
  <text x="96" y="58" class="s">secure enclosure (tamper-evident → tamper-responsive)</text>
  <rect x="120" y="80" width="200" height="100" rx="4" class="box"/>
  <text x="140" y="110" class="t">Accelerator</text>
  <text x="140" y="130" class="s">GPU / tray</text>
  <text x="140" y="150" class="s">HBM · NVLink · PCIe</text>
  <rect x="380" y="80" width="220" height="100" rx="4" class="box"/>
  <text x="400" y="110" class="t">Guarantee processor</text>
  <text x="400" y="130" class="s">count · rules · receipts</text>
  <text x="400" y="150" class="s">sign attestations</text>
  <text x="310" y="138" class="t">↔</text>
  <text x="96" y="236" class="s">Interlock = GP sits on a mandatory data path (NIC-scale is the realistic third-party mount)</text>
</svg>
<p class="cap">FlexHEG dual core: local notarization + physical hardness. Privacy: prove compliance without shipping weights abroad.</p>
</div>'''

def svg_rahman():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#m4); }
  </style>
  <defs>
    <marker id="m4" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <rect x="40" y="40" width="160" height="70" rx="4" class="box"/>
  <text x="52" y="68" class="t">GPU workload</text>
  <text x="52" y="88" class="s">train / infer / mix</text>
  <path d="M200 75 L250 75" class="arr"/>
  <rect x="250" y="40" width="180" height="70" rx="4" class="box"/>
  <text x="262" y="68" class="t">NVML telemetry</text>
  <text x="262" y="88" class="s">no weights / no data</text>
  <path d="M430 75 L480 75" class="arr"/>
  <rect x="480" y="40" width="180" height="70" rx="4" class="box"/>
  <text x="492" y="68" class="t">Monitor model</text>
  <text x="492" y="88" class="s">train vs infer label</text>

  <rect x="120" y="140" width="480" height="70" rx="4" class="box"/>
  <text x="140" y="168" class="t">5 rounds monitor ↔ evader · 20 disguises · 9 GPUs · 4 arch gens</text>
  <text x="140" y="190" class="s">headline ~98.2% overall · hard disguises collapse to ~43–87% — robust-ish, not magic</text>
</svg>
<p class="cap">Thin layer only: “is this training?” not “did this training violate a FLOP license.” Empirically grounded where Shavit/ZK are still blueprints.</p>
</div>'''

def svg_zk():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 250" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#m5); }
  </style>
  <defs>
    <marker id="m5" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <rect x="40" y="50" width="150" height="60" rx="4" class="box"/>
  <text x="52" y="76" class="t">genesis proof</text>
  <text x="52" y="94" class="s">W₀ well-formed</text>
  <path d="M190 80 L240 80" class="arr"/>
  <rect x="240" y="50" width="150" height="60" rx="4" class="box"/>
  <text x="252" y="76" class="t">step proofs</text>
  <text x="252" y="94" class="s">Wᵢ → Wᵢ₊₁ valid</text>
  <path d="M390 80 L440 80" class="arr"/>
  <rect x="440" y="50" width="150" height="60" rx="4" class="box"/>
  <text x="452" y="76" class="t">ex-ante attest</text>
  <text x="452" y="94" class="s">rules before run</text>
  <path d="M590 80 L620 80" class="arr"/>
  <text x="628" y="84" class="t">π</text>

  <text x="40" y="150" class="t">vs Shavit</text>
  <text x="40" y="172" class="s">Shavit: heuristic / sampling recompute of a claimed transcript</text>
  <text x="40" y="192" class="s">ZK: cryptographic proof over BF16/FP32 training steps in a zkVM — stronger claim, no E2E prototype yet</text>
  <text x="40" y="216" class="s">Authors: ~36 months to deployable PoC; custom verify silicon 6–10 years; 13 open problems listed</text>
</svg>
<p class="cap">Crypto endgame of the Shavit idea. Treat as research horizon, not near-term pause tooling.</p>
</div>'''

def svg_verinf():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="24" class="h">VerInf statement (not bit-exact equality)</text>
  <rect x="24" y="40" width="330" height="120" rx="4" class="box"/>
  <text x="36" y="64" class="t">Committed integer model M</text>
  <text x="36" y="84" class="s">predicts hidden token stream</text>
  <text x="36" y="104" class="s">well enough that leftover</text>
  <text x="36" y="124" class="s">info ≤ public Û bits/token</text>
  <text x="36" y="144" class="s">ZK: no weights / acts / x,y</text>
  <rect x="370" y="40" width="326" height="120" rx="4" class="box"/>
  <text x="382" y="64" class="t">Demo anchor (Petrie 2026)</text>
  <text x="382" y="84" class="s">Llama-4-Maverick ~400B MoE</text>
  <text x="382" y="104" class="s">1000 tokens · Û ≈ 0.88 b/tok</text>
  <text x="382" y="124" class="s">π ≈ 94 GB · prove ~14h · verify ~18h</text>
  <text x="382" y="144" class="s">spot-check scare, not every request</text>
  <text x="24" y="190" class="t">vs zkLLM</text>
  <text x="24" y="212" class="s">zkLLM: prove exact integer circuit output y. Softmax via tables + tolerance. Scale ~13B, tiny π.</text>
  <text x="24" y="232" class="s">VerInf: prove predictive explanation bound. Deliberately skips float bit-exact. Scale ~400B, huge π.</text>
  <text x="24" y="252" class="s">Both are Cankaya Plan B evaluate engines — after taps/challenge exist. Plan A stays the near-term default.</text>
</svg>
<p class="cap"><a href="https://github.com/JamesPetrie/VerInf">VerInf</a> — unexplained-info ZK at frontier demo scale.</p>
</div>'''

def svg_inference_triad():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#m6); }
  </style>
  <defs>
    <marker id="m6" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="24" class="h">Same audit question: was this sampled request run on the whitelist model?</text>
  <rect x="24" y="40" width="200" height="100" rx="4" class="box"/>
  <text x="36" y="64" class="t">Plan A · Cankaya</text>
  <text x="36" y="84" class="s">air-gapped AE</text>
  <text x="36" y="102" class="s">plain recompute</text>
  <text x="36" y="120" class="s">bit-exact ideal</text>
  <path d="M224 90 L260 90" class="arr"/>
  <rect x="260" y="40" width="200" height="100" rx="4" class="box"/>
  <text x="272" y="64" class="t">Plan B · zkLLM</text>
  <text x="272" y="84" class="s">exact-circuit ZK</text>
  <text x="272" y="102" class="s">y = circuit(W,x)</text>
  <text x="272" y="120" class="s">~13B · &lt;200KB π</text>
  <path d="M460 90 L496 90" class="arr"/>
  <rect x="496" y="40" width="200" height="100" rx="4" class="box"/>
  <text x="508" y="64" class="t">Plan B · VerInf</text>
  <text x="508" y="84" class="s">Û unexplained bits</text>
  <text x="508" y="102" class="s">no bit-exact need</text>
  <text x="508" y="120" class="s">~400B · huge π</text>

  <text x="24" y="172" class="t">Dead-simple memory aid</text>
  <text x="24" y="196" class="s">Plan A: I watch you recompute.</text>
  <text x="24" y="216" class="s">zkLLM: you prove the circuit executed (receipt).</text>
  <text x="24" y="236" class="s">VerInf: you prove the committed model explains the tokens; leftover ≤ Û (score).</text>
  <text x="24" y="268" class="s">Near-term default in Cankaya: Plan A. zkLLM = early Plan-B instance. VerInf = frontier-scale Plan-B core.</text>
</svg>
<p class="cap">Inference side of Claim A / arms-control-like monitoring. Complements Peigné’s training ZK; sits under Cankaya’s tap → challenge → evaluate loop.</p>
</div>'''

def svg_zkllm_stack():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <rect x="40" y="20" width="640" height="40" rx="4" class="box"/>
  <text x="52" y="46" class="t">⑤ full LLM: layer stack → public x,y + Commit(W)=C</text>
  <rect x="40" y="72" width="640" height="40" rx="4" class="box"/>
  <text x="52" y="98" class="t">④ zkAttn: Softmax shift + digit exp tables + norm tolerance</text>
  <rect x="40" y="124" width="640" height="40" rx="4" class="box"/>
  <text x="52" y="150" class="t">③ tlookup: non-arith ops → set membership via rational identity</text>
  <rect x="40" y="176" width="640" height="40" rx="4" class="box"/>
  <text x="52" y="202" class="t">② sumcheck: matmul / big sums via random challenges</text>
  <rect x="40" y="228" width="640" height="28" rx="4" class="box"/>
  <text x="52" y="248" class="t">① Hyrax poly commit: hide W, bind C, ProveEval at random points</text>
</svg>
<p class="cap">zkLLM composition: verifier never re-runs the model — only checks random algebraic relations against commitments.</p>
</div>'''

def svg_tap_nsew():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="24" class="h">Where to put network taps (Cankaya Apr 2026 feasibility note)</text>
  <rect x="24" y="40" width="330" height="120" rx="4" class="box"/>
  <text x="36" y="64" class="t">North–South (frontend)</text>
  <text x="36" y="86" class="s">DC ↔ outside world (API, SSH)</text>
  <text x="36" y="106" class="s">cheap · active warden OK</text>
  <text x="36" y="126" class="s">cost ≪ 0.01% of facility TCO</text>
  <text x="36" y="146" class="s">do this first</text>
  <rect x="366" y="40" width="330" height="120" rx="4" class="box"/>
  <text x="378" y="64" class="t">East–West (backend)</text>
  <text x="378" y="86" class="s">GPU↔GPU · storage · all-reduce</text>
  <text x="378" y="106" class="s">optical split + random sample</text>
  <text x="378" y="126" class="s">~0.2–1.5% TCO (level-dep.)</text>
  <text x="378" y="146" class="s">copper scale-up (NVL*) stays blind</text>
  <text x="24" y="192" class="t">Tap outputs commitments (hash + timestamp + sign), not raw secrets to the peer state.</text>
  <text x="24" y="214" class="s">Prover can passively re-observe tap egress → near-term no mutually trusted silicon.</text>
  <text x="24" y="236" class="s">Storage fabric next (~0.3–0.5%): which weights loaded, datasets read, checkpoints written.</text>
  <text x="24" y="258" class="s">Biggest unknown: residual covert bps if only NS is tapped (Fermi ~10² bps — needs empirics).</text>
</svg>
<p class="cap">Evidence capture layer under Cankaya’s blueprint. Source: <a href="https://nacicankaya.substack.com/p/research-note-the-fundamentals-and">Cankaya, secure network taps (Apr 2026)</a>.</p>
</div>'''

def svg_bitexact():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 12px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="24" class="h">Plan A numerics: close joshc’s “~1% looks like error” channel</text>
  <rect x="24" y="40" width="330" height="100" rx="4" class="box"/>
  <text x="36" y="64" class="t">Non-invariance (common)</text>
  <text x="36" y="86" class="s">Same math, different FP reduction trees</text>
  <text x="36" y="106" class="s">(batch / kernel / SKU) → different bits</text>
  <text x="36" y="126" class="s">Deterministic if metadata fixed</text>
  <rect x="366" y="40" width="330" height="100" rx="4" class="box"/>
  <text x="378" y="64" class="t">True nondeterminism (rare)</text>
  <text x="378" y="86" class="s">atomicAdd races (some INT dequant)</text>
  <text x="378" y="106" class="s">Warp-scheduler order changes</text>
  <text x="378" y="126" class="s">Avoid / ban those kernels for audit</text>
  <text x="24" y="168" class="t">Record: SKU · weights · parallel topology · software stack · batch size / step</text>
  <text x="24" y="190" class="s">Then recompute on same SKU, or CPU-emulate tensor-core + SFU rounding (cross-gen).</text>
  <text x="24" y="212" class="s">No need for slow “determinism flags” on the live path — audit via metadata + replay.</text>
  <text x="24" y="234" class="s">Contrast: DiFR = statistical slack; VerInf = don’t require float bit-exact (Û absorbs).</text>
</svg>
<p class="cap"><a href="https://arxiv.org/abs/2606.00279">arXiv:2606.00279</a> — bit-exact inference verification (Cankaya).</p>
</div>'''

BODY = f'''
<header class="masthead">
  <div class="kicker">Briefing deck · compute-pause verification</div>
  <h1>Research directions for verifiable AI slowdown</h1>
  <p>A self-contained technical map of the main public papers and posts on verifying (and preferably throttling) frontier AI training under low trust. For each piece: who wrote it, what problem it addresses, how mature it is, and how it relates to the rest of the stack. Diagrams first; public links in each section.</p>
  <p class="meta">2026-08-04 · standalone briefing · sources linked inline (arXiv / LessWrong / Substack / project sites)</p>
</header>

<section id="map">
  <div class="kicker">Orientation</div>
  <h2><span class="n">0.</span>Why this exists, what “Claim A” means, and the stack</h2>


  <h3>0.0 Motivation — why anyone is building this</h3>
  <p><strong>Anthropic (2026), <em>When AI builds itself</em>.</strong> The Institute argued the world should have the <em>option</em> of a coordinated slowdown or temporary pause on frontier development — but only if parties can <strong>verify</strong> that others actually stopped, so bad actors cannot use a collective pause as cover to race ahead. Conditional pause language is the point: verification systems are a prerequisite, not a side quest.
  (<a href="https://www.anthropic.com/institute/recursive-self-improvement">anthropic.com/institute/recursive-self-improvement</a>)</p>
  <p><strong>AI 2027, Appendix S (scenario research).</strong> If the US and China tried an AI arms-control style deal, how would cheating be caught? The appendix lists four imperfect families: (1) intelligence collection, (2) crude compute shutdowns with inspectors, (3) <strong>hardware-enabled mechanisms (HEM)</strong> — tamper-resistant reporting of what accelerators run, analogous to seals/attestations in other verification regimes, and (4) politically extreme “AI lie detection” of officials. This deck is mostly fleshing out family (3) and the monitoring stack that sits under it.
  (<a href="https://ai-2027.com/">ai-2027.com</a> · research notes on compute / verification)</p>
  <p>Same problem, different genres: a lab institute essay (Anthropic) and a public scenario appendix (AI 2027) both treat <strong>credible verification</strong> as the binding constraint on any pause story.</p>

  <h3>0.1 The policy problem in one paragraph</h3>
  <p>Labs and governments sometimes talk about a <strong>coordinated slowdown or pause</strong> on frontier model development. That option is worthless if parties cannot tell whether others actually stopped. Self-reports are not enough under low trust (rival states, or competing labs). The technical agenda is: build monitoring / attestation / enforcement so large unauthorized <em>training</em> is discoverable or physically hard — without requiring mutual trust in each other’s word.</p>
  <p>Training vs inference is the load-bearing distinction. <strong>Training</strong> updates weights (often with heavy multi-GPU communication). <strong>Inference</strong> serves a fixed model. Datacenters can look “busy” either way; a sophisticated actor can try to disguise training (especially post-deployment RL) as serving. So “the GPUs are warm” is not a proof of compliance.</p>

  <h3>0.2 Four claims people mix up</h3>
  <p>People say “AI verification” for several <em>different sentences</em>. This deck is almost entirely about <strong>Claim A</strong>.</p>
  {svg_claims()}
  <div class="tbl">
    <table>
      <thead><tr><th>Claim</th><th>Plain English</th><th>Primary audience</th><th>Example tech</th></tr></thead>
      <tbody>
        <tr><td class="mono">A</td><td>No covert frontier training; only allowed / declared workloads on monitored compute</td><td>Treaties, pause/slowdown, export-control regimes</td><td>TAPs, recompute, train↔infer detectors, FlexHEG, PoL-style transcripts</td></tr>
        <tr><td class="mono">B</td><td>The model that answered you is the one you bought / audited</td><td>Enterprise buyers, regulated sectors</td><td>Model identity binding, inference receipts, DRM-adjacent ZK</td></tr>
        <tr><td class="mono">C</td><td>This run happened in a stated place / TEE; the host can’t read your data</td><td>Sovereignty, GDPR, confidential cloud</td><td>Confidential computing, remote attestation, location proofs</td></tr>
        <tr><td class="mono">D</td><td>This agent only performed approved tool calls</td><td>Agent products / enterprise copilots</td><td>Audit logs, policy engines, “passport” receipts</td></tr>
      </tbody>
    </table>
  </div>
  <div class="note">
    <span class="label">Scope of this deck</span>
    <p><strong>In:</strong> Claim A mechanisms and the research lineage around them. <strong>Out (except as contrast):</strong> commercial TEE inference products aimed at B/C/D. Those can share primitives (attestation, recompute) but answering B/C does not answer “did you secretly train a bigger model?”</p>
  </div>

  <h3>0.3 Map of works covered</h3>
  {svg_lineage()}
  <div class="ladder">
    <div class="rung"><div class="lvl">loose</div><div class="body"><strong>NTM / inspections</strong> — satellites, energy, site visits (Wasil’s access-light methods)</div></div>
    <div class="rung"><div class="lvl">medium</div><div class="body"><strong>Network / facility controls</strong> — TAPs, bandwidth caps, memory wipes, output recompute (joshc; Cankaya taps)</div></div>
    <div class="rung"><div class="lvl">tight</div><div class="body"><strong>Workload monitoring</strong> — weight snapshots + transcripts (Shavit); thin train↔infer telemetry (Rahman)</div></div>
    <div class="rung"><div class="lvl">hard</div><div class="body"><strong>Hardware-enabled guarantees</strong> — FlexHEG FLOP caps / licenses / interlocks</div></div>
    <div class="rung"><div class="lvl">crypto</div><div class="body"><strong>ZK training proofs</strong> — Peigné et al. (§9 research horizon)</div></div>
    <div class="rung"><div class="lvl">infer</div><div class="body"><strong>Near-term inference retrofit</strong> — Cankaya Plan A (§5 taps + bit-exact) then Plan B (§6 zkLLM · §7 VerInf)</div></div>
  </div>
  <p><strong>Maturity legend used below:</strong> <em>Survey</em> (conceptual menu) · <em>Blueprint</em> (architecture, no full deploy) · <em>Empirical paper</em> (measured results) · <em>Prototype / demo</em> · <em>Horizon</em> (no working end-to-end system yet) · <em>Product</em> (mass deployment — almost nothing here qualifies).</p>
</section>


<section id="glossary">
  <div class="kicker">Primer</div>
  <h2><span class="n">0b.</span>Hardware · ML systems · crypto vocabulary</h2>
  <p class="dek">Zoom from hall → interconnect layers → rack → node → board → SM, then why traffic looks different for train vs infer, then ZK vocab for §§6–7. Skim once; jump back when a later section feels opaque.</p>

  <h3>1 · Where this lives — a real hall</h3>
  <figure>
    <img src="figures/meta_rsc_datacenter_aisle.jpg" alt="Meta AI Research SuperCluster data hall aisle"/>
    <figcaption>Real AI cluster hall (Meta AI Research SuperCluster press photo): rack rows, cold-aisle containment, overhead cable trays carrying the scale-out fabric. Source: <a href="https://ai.meta.com/blog/ai-rsc/">Meta AI — Introducing the AI Research SuperCluster</a>.</figcaption>
  </figure>

  <h3>2 · Organizing abstraction — interconnect ladder</h3>
  <p>Everything below is a zoom into one of these layers. Tap feasibility is uneven because only some layers ever become light.</p>
  {svg_panels.svg_interconnect_ladder()}
  <div class="tbl">
    <table>
      <thead><tr><th>Link</th><th>Medium</th><th>Job</th><th>Tap note</th></tr></thead>
      <tbody>
        <tr><td class="mono">NVLink / NVSwitch</td><td>Copper (board / cable cartridge / rack spine)</td><td>Scale-up: activations, TP shards, in-rack collectives</td><td>Hard — never becomes light</td></tr>
        <tr><td class="mono">InfiniBand (Quantum…)</td><td>DAC copper short; fiber + QSFP/OSFP longer</td><td>Scale-out GPU↔GPU (NCCL over RDMA)</td><td>Fiber segments = tap candidates</td></tr>
        <tr><td class="mono">RoCE / Spectrum-X</td><td>Same physical story as IB, Ethernet framing</td><td>Same role as IB in many clouds</td><td>Same EO story</td></tr>
        <tr><td class="mono">PCIe</td><td>Board traces</td><td>GPU↔CPU / GPU↔NIC</td><td>Inside box</td></tr>
        <tr><td class="mono">AOC / transceiver</td><td>Electrical→laser→fiber→photodiode→electrical</td><td>Longer runs, leaf–spine, NS exit</td><td>Conversion lives in the pluggable module</td></tr>
      </tbody>
    </table>
  </div>
  <p><strong>Electro–optical conversion in one sentence:</strong> the NIC SerDes is electrical; for distance you plug in a module that drives a laser into fiber and recovers bits at the far end. Passive optical taps copy photons on the fiber; they do nothing for copper NVLink spines inside the rack.</p>

  <h3>3 · Ladder mapped onto a facility</h3>
  {svg_panels.svg_dc_topology()}
  <figure>
    <img src="figures/dgx_h100_cluster_topology.png" alt="DGX cluster topology"/>
    <figcaption>Same hierarchy, drawing form: servers → racks → pods → site. East–West ≈ ladder layers 2–3 inside the fence; North–South exits the site (best first tap chokepoint).</figcaption>
  </figure>

  <h3>4 · Zoom: one scale-up domain (rack)</h3>
  <figure>
    <img src="figures/gb200_nvl72_jensen.jpg" alt="NVIDIA GB200 NVL72 rack on stage"/>
    <figcaption>Ladder layer 2 at modern density: GB200 NVL72 = 72 Blackwell GPUs + Grace CPUs in one liquid-cooled copper NVLink domain (~130 TB/s). Source: <a href="https://blogs.nvidia.com/blog/blackwell-ai-inference/">NVIDIA Blog</a>.</figcaption>
  </figure>
  <figure>
    <img src="figures/nvlink_copper_spine.jpg" alt="Dense copper interconnect harness for multi-GPU scale-up"/>
    <figcaption>What layer-2 cabling looks like up close: dense copper (not fiber). Optical conversion mostly starts at the scale-out NIC edge (layer 3). Source: <a href="https://blogs.nvidia.com/blog/blackwell-ai-inference/">NVIDIA Blog</a>.</figcaption>
  </figure>

  <h3>5 · Zoom: one node (ladder layers 2→3)</h3>
  {svg_panels.svg_node_8gpu()}

  <h3>6 · Zoom: one board (ladder layers 1→2)</h3>
  <figure>
    <img src="figures/gb200_bianca_board_layout.png" alt="GB200 board layout"/>
    <figcaption>
      GB200 “Bianca” board (SemiAnalysis). Layer-1/2 callouts:
      <strong>Blackwell ×2</strong> — AI compute dies (SMs + HBM on-package);
      <strong>Grace CPU</strong> — Arm host / orchestrator;
      <strong>LPDDR5X</strong> — Grace system DRAM (not GPU HBM);
      <strong>NVLink-C2C</strong> — Grace↔GPU coherent link (still layer 1);
      <strong>NVLink5 connectors</strong> — out to rack scale-up domain (layer 2);
      <strong>CX-7</strong> — NIC mezzanine → IB/Ethernet scale-out (layer 3; EO starts here on long runs);
      <strong>Grace–Grace C2C</strong> — board-to-board CPU link;
      <strong>BMC</strong> — out-of-band management;
      <strong>MCIO / SlimSAS</strong> — PCIe storage/expansion.
      FlexHEG near-term retrofits often target the <em>NIC / enclosure</em>, not a GPU-die respin.
    </figcaption>
  </figure>

  <h3>7 · Zoom: inside the GPU die — SM</h3>
  {svg_panels.svg_sm()}

  <h3>8 · Why so many GPUs, and why traffic differs</h3>
  <p>Frontier training is big because the <em>model state does not fit on one GPU</em>, so you must shard and communicate constantly — mostly on ladder layers 2–3.</p>
  <div class="tbl">
    <table>
      <thead><tr><th>Scale intuition (public anchors, ~2024–26)</th><th>Number</th></tr></thead>
      <tbody>
        <tr><td>Llama 3.1 405B dense params</td><td class="mono">405×10⁹</td></tr>
        <tr><td>BF16 weights alone</td><td class="mono">405B × 2 B ≈ 810 GB</td></tr>
        <tr><td>Naive train state (W + grad + Adam ≈ 16 B/param)</td><td class="mono">≈ 6.5 TB total</td></tr>
        <tr><td>One H100 HBM</td><td class="mono">80 GB (SXM) / ~94–96 GB (some SKUs)</td></tr>
        <tr><td>B200 / Blackwell HBM class</td><td class="mono">~180–192 GB/GPU (gen-dependent)</td></tr>
        <tr><td>One GB200 NVL72 rack</td><td class="mono">72 GPUs · ~13.4 TB HBM aggregate</td></tr>
        <tr><td>Llama 3.1 405B pretrain cluster (Meta report)</td><td class="mono">up to ~16,384 H100s · ~3.8×10²⁵ FLOP · ~15.6T tokens</td></tr>
        <tr><td>Rough “why many GPUs”: fit train state + activations</td><td class="mono">405B needs ≫1 GPU; production runs use 10³–10⁴+</td></tr>
      </tbody>
    </table>
  </div>
  <p>Closed frontier labs (OpenAI / Anthropic / Google) don’t publish exact GPU counts; treat Llama 405B as the best public lower-bound picture of “what a near-frontier dense run looks like,” not the ceiling. MoE frontier runs can advertise huge total params with fewer active params/token — still multi-thousand-GPU jobs.</p>
  {svg_panels.svg_allreduce()}
  {svg_panels.svg_prefill_decode()}
  <div class="tbl">
    <table>
      <thead><tr><th>Term</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td class="mono">TP</td><td>Tensor parallelism — split a layer’s matrices across GPUs; exchange activations each layer</td></tr>
        <tr><td class="mono">DP / DDP</td><td>Data parallel — full model replica per worker; all-reduce gradients</td></tr>
        <tr><td class="mono">FSDP</td><td>Fully sharded data parallel — shard params; all-gather when needed</td></tr>
        <tr><td class="mono">NCCL</td><td>NVIDIA collective communications library implementing all-reduce etc.</td></tr>
        <tr><td class="mono">NVML / DCGM</td><td>Per-GPU sensor APIs (power, SM util, memory…). Not cross-node byte counters</td></tr>
        <tr><td class="mono">SM util</td><td>Fraction of SMs busy in the sample window — compute busyness, not “is this training?”</td></tr>
        <tr><td class="mono">Warden</td><td>Active network scrubber on the monitored path (normalize headers/timing to kill stego) — see §4</td></tr>
        <tr><td class="mono">DiLoCo</td><td>Low-communication training: many local steps, rare outer sync — can evade “fat interconnect” detectors</td></tr>
      </tbody>
    </table>
  </div>

  <h3>9 · Zero-knowledge proofs (for §§6–7, §9)</h3>
  {svg_panels.svg_verify_properties()}
  {svg_panels.svg_zk_constraints()}
  <p><strong>Constraint system intuition:</strong> turn “this forward pass was correct” into a huge set of algebraic checks over a <em>prime field</em> 𝔽_p (multiplications, lookups, range checks). The prover knows a <em>witness</em> (weights, activations) satisfying every constraint; the verifier checks a short proof that such a witness exists for the public statement — without learning the witness.</p>
  <p><strong>Integer constraint, concretely:</strong> GPUs run BF16/FP8 with rounding; SNARK circuits run integers mod p. zkLLM-style systems therefore prove a <em>quantized integer circuit</em> that approximates the model, not “whatever your CUDA float kernel did today.” That is why Plan A cares about bit-exact float recompute, and why VerInf replaces exact equality with an unexplained-info bound (Û / U-hat). Failures of soundness = false compliance; failures of ZK / confidentiality = IP/data leakage through the proof; failures of assurance = you never sampled the cheat.</p>
</section>

<section id="wasil">
  <div class="kicker">Survey · treaty framing</div>
  <h2><span class="n">1.</span>Wasil et al. — verification method menu</h2>
  <p class="dek"><a href="https://arxiv.org/abs/2408.16074">arXiv:2408.16074</a> · 2024</p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>Wasil, Reed, Miller, Barnett et al. — survey aimed at international AI agreements (access assumptions + evasion sketches).</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Survey / coordinate system.</strong> Not a deployable stack. Useful to prevent “we solved verification” talk after reading one mechanism.</p>
    </div>
  </div>
  <p><strong>Problem it frames:</strong> If states agree “don’t secretly train too big / don’t secretly build too many DCs,” what instruments exist? Two violation types: <strong>unauthorized training</strong> and <strong>unauthorized datacenters</strong>.</p>
  <p><strong>Lineage:</strong> Entry point for the rest of this deck. Later works sit in its hardware-dependent / access-dependent cells (Shavit, FlexHEG, location proofs, workload monitoring).</p>
  {svg_wasil()}
  <h3>What to remember technically</h3>
  <ul>
    <li>Methods differ in <strong>access assumptions</strong>: unilateral national technical means vs negotiated entry vs pre-agreed chip behavior.</li>
    <li>Hardware-dependent methods are highest bite and hardest diplomacy.</li>
    <li>Chip location ≠ training proof. Location answers “where is the silicon?”; workload methods answer “what did it run?”</li>
  </ul>
  <p><strong>One Wasil cell — chip location proofs — looks like this:</strong> you are not proving “this GPU trained legally.” You are proving (approximately) “this registered chip is physically near claimed site X,” so a dark training cluster in an undeclared country is harder to hide. Delay-based / multi-anchor checks exploit physics: light in fiber has a max speed, so round-trip time to a trusted probe sets a distance upper bound.</p>
  <figure>
    <img src="figures/location_verification_triangulation.png" alt="Location verification triangulation diagram"/>
    <figcaption>
      <strong>How to read the figure.</strong>
      Blue dots = trusted <em>anchors</em> (known-location probes / PoPs).
      Dashed arcs = “this chip answered me in ≤ T ms ⇒ it cannot be farther than ~c·T/2 in fiber.”
      Purple blob = intersection of several such bounds (where the chip is allowed to sit).
      Orange X = true location (ideally inside the blob).
      Spoofing “I’m in Virginia” while sitting in another country fails if enough distant anchors force the intersection away from Virginia.
      This is only a <em>where</em> check — still need workload methods (Shavit / joshc / FlexHEG / …) for <em>what ran</em>.
    </figcaption>
  </figure>
</section>

<section id="shavit">
  <div class="kicker">Classical compute monitoring</div>
  <h2><span class="n">2.</span>Shavit — Catch a Chinchilla (+ Proof-of-Learning)</h2>
  <p class="dek"><a href="https://arxiv.org/abs/2303.11341">arXiv:2303.11341</a> · 2023 · PoL primitive: Jia et al. 2021</p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>Yonadav Shavit — early blueprint for monitoring large training runs via chip-level weight fingerprints + training transcripts + supply-chain coverage.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Blueprint.</strong> Problem decomposition, not an industry-deployed end-to-end system as of 2026.</p>
    </div>
  </div>
  <p><strong>One sentence:</strong> force frontier training onto registered ML chips that leave sparse <em>weight fingerprints</em>; require a transcript that explains those fingerprints (Proof-of-Learning-style checks); audit the supply chain so dark chips can’t skip the net.</p>
  <p><strong>Lineage:</strong> Classical “what Claim A monitoring could look like.” Gaps it leaves → later work: train↔infer ambiguity (Rahman); cryptographic transcripts (Peigné); active hardware caps instead of after-the-fact snapshots (FlexHEG).</p>
  {svg_shavit()}
  <h3>Threat model that matters</h3>
  <p>Prover is a <strong>covert adversary</strong>: cheats only when it can look compliant. Design goal = make “look compliant while cheating” nearly impossible under random chip audits.</p>
  <div class="two-col">
    <div class="panel">
      <h4>On chip</h4>
      <p>Firmware occasionally hashes / records HBM weight shards. Needs signed firmware + later physical spot checks (remote attestation alone is weak against a physical adversary).</p>
    </div>
    <div class="panel">
      <h4>In the DC</h4>
      <p>Transcript = data references, hparams, checkpoints, optimizer trajectory. Verifier samples steps; inconsistency or illegal scale ⇒ fail.</p>
    </div>
  </div>
  <h3>Open issues Shavit already flags</h3>
  <ul>
    <li>Train vs infer lookalike occupancy of HBM.</li>
    <li>Legacy chips without secure firmware — small/medium training may escape.</li>
    <li>Vendor–prover collusion on backdoored firmware.</li>
  </ul>
</section>

<section id="rahman">
  <div class="kicker">Empirical thin layer</div>
  <h2><span class="n">3.</span>Rahman &amp; Tajdari — train vs infer from NVML</h2>
  <p class="dek"><a href="https://arxiv.org/abs/2606.19262">arXiv:2606.19262</a> · TAIGR @ ICML 2026</p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>Robi Rahman (MIRI Technical Governance; ex-Epoch) and Sabiha Tajdari (UVA) — SPAR-originated empirical red-team of GPU workload classifiers.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Empirical paper + public tooling lineage.</strong> Real numbers under adversarial disguise. Solves only a <em>thin slice</em> of Claim A (label train vs infer), not full rule verification.</p>
    </div>
  </div>
  <p><strong>Question:</strong> can you tell training vs inference from GPU telemetry (NVML) without touching weights or data?</p>
  <p><strong>Lineage:</strong> Attacks the gap Shavit flagged and that FlexHEG/joshc classifiers often assume. Complements interconnect-based detectors (communication volume) — different observation channel.</p>
  {svg_rahman()}
  <figure>
    <img src="figures/workload_monitoring_metrics.png" alt="Workload monitoring metrics"/>
    <figcaption>Example metric space for workload monitoring. Rahman asks whether this works under disguise.</figcaption>
  </figure>
  <h3>Numbers to keep (and not overclaim)</h3>
  <ul>
    <li>~98.2% overall accuracy across their matrix.</li>
    <li>Under the hardest disguises, ~43–87% — robust overall, meaningfully degraded under sophisticated evasion; not “solved.”</li>
    <li>Method: 5-round monitor–evader loop, multi-GPU / multi-arch — the right evaluation bar for any such detector.</li>
  </ul>
</section>

<section id="joshc">
  <div class="kicker">Near-term slowdowns</div>
  <h2><span class="n">4.</span>joshc — TAPs, wipes, and covert RL</h2>
  <p class="dek"><a href="https://www.lesswrong.com/posts/oHiNwWtDPcBLumPWp/how-might-governments-slow-or-halt-ai-training">LessWrong / Alignment Forum</a> · 2026</p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>joshc (Alignment Forum / LessWrong) — red-team essay on whether <em>fast, cheap facility mods</em> can slow training before treaty-grade hardware exists.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Red-team / requirements doc.</strong> Not a product. Sets pass/fail bars for prototypes (TAP + recompute + wipe + accounting).</p>
    </div>
  </div>
  <p><strong>Question:</strong> before global FlexHEG-class silicon exists, can governments slow training by pulling InfiniBand, capping rack egress (~100 KB/s), TAP+recomputing outputs, wiping memory, demanding PoW/PoM?</p>
  <p>Naive lever: training is communication-hungry; inference is text-skinny. joshc’s point: under <em>today’s prototype strength</em>, that lever may fail against modern RL pipelines (rollouts look like inference; updates can hide in a small dark fraction of compute + leaky recompute slack).</p>
  <p><strong>Lineage:</strong> Stress-tests the “medium” rung (after you’ve seen how thin NVML train↔infer is). Motivates tighter recompute (Cankaya bit-exact / DiFR), better taps, and why FlexHEG remains the longer-term enforcement story.</p>
  {svg_joshc()}
  <h3>Facility toolkit (where each tool sits)</h3>
  {svg_panels.svg_joshc_tools()}
  <h3>Five near-term tools (compressed)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Tool</th><th>Idea</th><th>Author’s read</th></tr></thead>
      <tbody>
        <tr><td class="mono">Pull IB</td><td>Replace ~400 GB/s fabrics with slow copper</td><td>~1y prep plausible</td></tr>
        <tr><td class="mono">BW limiter + TAP</td><td>Cap egress; sample traffic</td><td>to ~100 KB/s plausible</td></tr>
        <tr><td class="mono">Output recompute</td><td>Replay declared model M on tapped I/O</td><td>~1% nondeterminism budget = covert channel</td></tr>
        <tr><td class="mono">Memory wipe</td><td>Force verifiable fill; reload whitelist model</td><td>needs ≫99.99% coverage — hard</td></tr>
        <tr><td class="mono">PoW / PoM</td><td>Account for FLOPs/memory spent on declared serving</td><td>useful if &gt;95% coverage</td></tr>
      </tbody>
    </table>
  </div>
  <div class="note bug">
    <span class="label">Prototype bar</span>
    <p>If a demo doesn’t close the RL-smuggling channel under realistic slack, it has not purchased a credible pause — regardless of how good benign accuracy looks.</p>
  </div>
</section>

<section id="cankaya">
  <div class="kicker">Near-term retrofit · Plan A</div>
  <h2><span class="n">5.</span>Cankaya — taps, challenges, and precise replay (Plan A)</h2>
  <p class="dek">
    System overview <a href="https://www.lesswrong.com/posts/fgvmKqRGvBteKeDoc/a-system-overview-for-near-term-low-trust-ai-compute">LW</a> ·
    taps <a href="https://nacicankaya.substack.com/p/research-note-the-fundamentals-and">Substack Apr 2026</a> ·
    bit-exact <a href="https://arxiv.org/abs/2606.00279">2606.00279</a> ·
    DiFR (statistical slack) <a href="https://arxiv.org/abs/2511.20621">2511.20621</a>
  </p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p><strong>Naci Cankaya</strong> (MIRI technical governance) — whole-facility retrofit blueprint: capture I/O → random challenge → evaluate. Bit-exact paper is the Plan A numerics companion; taps note is the capture companion.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p>Overview: <strong>blueprint</strong>. Taps: <strong>feasibility + commodity-tech argument</strong> (NS ready-ish; EW needs pilots). Bit-exact: <strong>empirical + emulator prototype</strong> for inference — not a training verifier; not yet a fielded AE standard.</p>
    </div>
  </div>
  <p><strong>Shared audit question:</strong> was this sampled request run on the whitelist model?</p>
  <p><strong>Plan A (near-term default):</strong> air-gapped audit environment (AE) holds the whitelist weights and <em>recomputes</em> the challenged forward pass in plaintext, then compares to tapped I/O. For that comparison to be a pass/fail (not a ~1% stego channel à la joshc), you need <strong>precise replay</strong> — ideally bit-exact under recorded metadata, or a disciplined statistical alternative (DiFR).</p>
  <p><strong>Plan B (later sections):</strong> replace AE recompute with ZK so the peer needn’t see weights — zkLLM (§6) or VerInf (§7). Same challenge loop; different evaluate engine.</p>
  <p><strong>Lineage:</strong> Turns joshc’s TAP/recompute sketches into an arms-control-shaped architecture. FlexHEG is the longer hardware track; Peigné (§9) is the training-ZK cousin.</p>

  <h3>Properties checklist (before the diagrams)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Property</th><th>Plain English</th><th>Plan A (AE plaintext)</th><th>Plan B (ZK)</th></tr></thead>
      <tbody>
        <tr><td class="mono">Completeness</td><td>Honest clean prover passes</td><td>Needs bit-exact / DiFR so benign noise ≠ reject</td><td>Honest π verifies</td></tr>
        <tr><td class="mono">Soundness</td><td>Cheater fails</td><td>Recompute mismatch / wrong W vs C</td><td>Bad witness can’t forge π (or Û bound)</td></tr>
        <tr><td class="mono">Confidentiality</td><td>Secrets stay secret</td><td><strong>Weak</strong> — W and challenged I/O enter AE</td><td><strong>Stronger</strong> — witness not revealed</td></tr>
        <tr><td class="mono">Assurance</td><td>Field catch probability</td><td>Soundness × sample rate × tap coverage × stego slack</td><td>Same multipliers; π ≠ free lunch</td></tr>
      </tbody>
    </table>
  </div>
  {svg_panels.svg_why_not_plaintext()}
  <p><strong>Why plaintext recompute is not enough (even when it “works”):</strong> it can deliver completeness/soundness/assurance under good engineering, but it fails the low-trust confidentiality goal — rival labs/states will not ship frontier weights into the other party’s AE, and neither trusts the other’s silicon inside the cage. That is the explicit motivation for Plan B. Plan A remains the near-term default because ZK at frontier scale is still expensive / immature — not because confidentiality doesn’t matter.</p>

  {svg_inference_triad()}
  {svg_panels.svg_cankaya_facility()}
  {svg_panels.svg_four_gates()}

  <h3>Network taps (where commitments come from)</h3>
  {svg_tap_nsew()}
  <ul>
    <li><strong>NS first:</strong> frontend traffic is ~Gb/s-class in the note’s Fermi — commodity FPGA / mid-range NIC; active wardens fit.</li>
    <li><strong>EW:</strong> full mirror is infeasible; wide optical split + random sampling; need tensor metadata or bytes are meaningless.</li>
    <li><strong>Copper NVL*:</strong> passive optical taps miss intra-rack scale-up — security falls back onto NS + storage.</li>
  </ul>

  <h3>Bit-exact inference verification (precise replay)</h3>
  <p>This is the load-bearing Plan A engineering claim: unmodified serving stacks are often <em>deterministic enough</em> once you freeze the right metadata — so “looks like noise” is usually non-invariance (reduction trees), not irreducible chaos.</p>
  {svg_bitexact()}
  <ul>
    <li>Unmodified vLLM/HF are usually <strong>deterministic</strong> without special determinism flags; “noise” is mostly <strong>non-invariance</strong> (reduction trees), not atomics.</li>
    <li>CPU emulator can match A100/L40/H100 intermediates when SKU + kernel path are modeled.</li>
    <li><strong>Metadata checklist:</strong> SKU · weights · parallel topology · software stack · per-forward batch size.</li>
    <li><strong>DiFR:</strong> if you cannot field bit-exact, keep statistical slack — but then budget the covert channel explicitly (joshc’s warning).</li>
  </ul>
  <div class="note">
    <span class="label">How the pieces lock</span>
    <p>Tap → I/O commitments · Bit-exact (+ metadata) → close stego slack · AE recompute (Plan A) evaluates samples. §§6–7 swap in ZK at the evaluate step only.</p>
  </div>
</section>

<section id="zkllm">
  <div class="kicker">Plan B · exact-circuit ZK</div>
  <h2><span class="n">6.</span>zkLLM — prove the integer circuit ran</h2>
  <p class="dek"><a href="https://arxiv.org/abs/2404.16109">arXiv:2404.16109</a> · Sun, Li, Zhang · ACM CCS 2024 · <a href="https://github.com/jvhs0706/zkllm-ccs2024">code</a></p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>Haochen Sun, Jason Li, Hongyang Zhang — first widely cited exact-circuit ZK system for LLM inference at non-toy scale (~13B).</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Published system + limited scale.</strong> Spot-check engine, not “every API request.” Integer/quantized circuit ≠ arbitrary float serving bit-exact.</p>
    </div>
  </div>
  <p><strong>Statement:</strong> there exist weights W matching public commitment C such that the public architecture, run as an <em>integer circuit</em> on public x, yields public y — without revealing W or activations.</p>
  <p><strong>Lineage:</strong> One Plan B evaluate backend under Cankaya’s challenge loop. Precursor / contrast to VerInf (§7): exact receipt vs unexplained-info score. Complements Plan A when the AE cannot see weights.</p>
  {svg_zkllm_stack()}
  <h3>Numbers (paper anchors)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Item</th><th>Rough public figure</th></tr></thead>
      <tbody>
        <tr><td>Scale</td><td class="mono">~13B (OPT / LLaMA-2 class)</td></tr>
        <tr><td>Prove time</td><td class="mono">~1–15 min (CUDA, setting-dependent)</td></tr>
        <tr><td>Proof size</td><td class="mono">&lt; ~200 KB</td></tr>
        <tr><td>Verify</td><td class="mono">~1–3 s</td></tr>
        <tr><td>Commit scheme</td><td>Hyrax (no trusted setup)</td></tr>
      </tbody>
    </table>
  </div>
  <h3>Guts (enough to not handwave)</h3>
  <ul>
    <li><strong>Hyrax:</strong> polynomial commitment binds W into C; open evaluations at random points.</li>
    <li><strong>Sumcheck:</strong> big matmuls / sums become interactive algebraic checks.</li>
    <li><strong>tlookup:</strong> non-arithmetic ops → prove secret tensor entries lie in a public table via a rational identity at a random point.</li>
    <li><strong>zkAttn:</strong> Softmax shift shrinks exp domain; don’t prove exact log-sum-exp — only a <strong>tolerance band</strong> on row sums (fine for execution receipts; dangerous if bolted onto a manipulable unexplained-info score).</li>
  </ul>
  <h3>What it does <em>not</em> prove</h3>
  <ul>
    <li>Bit-exact match to H100/B200 float serving (that’s Plan A / bit-exact paper).</li>
    <li>Anything about training — only a forward pass receipt.</li>
    <li>Frontier 100B+ scale in the published system (see VerInf for the larger demo with a different statement).</li>
  </ul>
  <div class="note">
    <span class="label">Cheat intuition</span>
    <p>Swap whitelist model → fails vs C. Abuse Softmax tolerance → can still Accept under loose bands. Float nondeterminism is mostly irrelevant because you never claimed float equality.</p>
  </div>
</section>

<section id="verinf">
  <div class="kicker">Plan B · unexplained-info ZK</div>
  <h2><span class="n">7.</span>VerInf — bound leftover bits, skip float bit-exact</h2>
  <p class="dek">Petrie 2026 draft · <a href="https://github.com/JamesPetrie/VerInf">github.com/JamesPetrie/VerInf</a> · FLI / FlexHEG author</p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p><strong>James Petrie</strong> — same hardware-governance thread as FlexHEG. VerInf is the “replace the recompute cluster with a ZK evaluate engine” instance at frontier demo scale.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Working draft + large demo</strong>, not production audit tooling. Interactive, expensive proofs meant for rare high-stakes spot checks when both parties have serious compute.</p>
    </div>
  </div>
  <p><strong>Statement:</strong> a committed integer model explains a (possibly hidden) token stream well enough that leftover unexplained information is ≤ a public bound Û bits/token — without revealing weights, activations, or plaintext I/O.</p>
  <p><strong>Lineage:</strong> Other Plan B evaluate backend under Cankaya. Designed precisely because Plan A bit-exact and zkLLM-style exact equality both get brittle or tiny-scale at frontier serving.</p>
  {svg_verinf()}
  <h3>Why change the statement</h3>
  <ul>
    <li>Float nondeterminism + MoE/serving stacks make “y must equal AE recompute” expensive to field at 400B.</li>
    <li>Exact-circuit ZK at 13B already hurts; naively scaling the zkLLM statement is the wrong lever.</li>
    <li>Û is an auditable score: too large ⇒ looks like wrong model / stego / garbage; threshold is a policy knob.</li>
  </ul>
  <h3>Demo anchors (draft)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Item</th><th>Rough figure</th></tr></thead>
      <tbody>
        <tr><td>Model</td><td>Llama-4-Maverick ~400B MoE (commit all experts/layer)</td></tr>
        <tr><td>Sequence</td><td>1000 tokens (500+500), fully hidden in the demo</td></tr>
        <tr><td>Û</td><td class="mono">≈ 0.88 bits/token (~95% of vocab info explained)</td></tr>
        <tr><td>Prove / verify</td><td class="mono">~14 h prove · ~94 GB π · ~18 h verify (single high-end box class)</td></tr>
        <tr><td>Witness stream</td><td class="mono">~7 TB streamed · ~84 GB peak RAM</td></tr>
      </tbody>
    </table>
  </div>
  <h3>vs zkLLM (cheat table)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Cheat</th><th>Plan A (§5)</th><th>zkLLM (§6)</th><th>VerInf (§7)</th></tr></thead>
      <tbody>
        <tr><td>Swap whitelist model</td><td>recompute mismatch</td><td>fails vs C</td><td>Û blows up</td></tr>
        <tr><td>Float nondeterminism</td><td>pain; bit-exact / metadata</td><td>proves circuit, not float replica</td><td>slack → Û</td></tr>
        <tr><td>Softmax slack abuse</td><td>if loose match, channel</td><td>still Accept possible</td><td>forbidden design goal; unique shift</td></tr>
      </tbody>
    </table>
  </div>
  <div class="note bug">
    <span class="label">Cost intuition</span>
    <p>Spot checks, not every request. Plan A ≈ recompute GPU-time. zkLLM-13B ~minutes + tiny π. VerInf-400B = hours + tens of GB — rare audits when secrecy of weights beats AE plaintext.</p>
  </div>
</section>

<section id="flexheg">
  <div class="kicker">Hardware track · parallel to §§5–7</div>
  <h2><span class="n">8.</span>FlexHEG trilogy — especially Part II</h2>
  <p class="dek">
    Tech <a href="https://arxiv.org/abs/2506.03409">2506.03409</a> ·
    Overview <a href="https://arxiv.org/abs/2506.15093">2506.15093</a> ·
    Intl <a href="https://arxiv.org/abs/2506.15100">2506.15100</a> ·
    <a href="https://www.flexheg.com/">flexheg.com</a> · 2025
  </p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>James Petrie, Onni Aarne, and collaborators (FLI / ARIA-linked FlexHEG program). Hardware-enabled governance design for accelerators.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Blueprint + early demos</strong> (enclosure / metering ideas). <strong>Not</strong> mass-deployed product silicon. Grant-funded engineering (incl. partners building tap/wipe primitives).</p>
    </div>
  </div>
  <p><strong>FlexHEG</strong> = Flexible Hardware-Enabled Guarantees: a <strong>guarantee processor</strong> that locally enforces / attests rules, plus a <strong>secure enclosure</strong> that makes bypass expensive. Rules should be updatable under multi-party authorization.</p>
  <p><strong>Lineage:</strong> After the near-term retrofit path (§§5–7): moves Claim A from Shavit-style after-the-fact snapshots toward <em>active</em> guarantees (FLOP caps, licenses, interlocks). Near-term retrofit path often emphasized: NIC / scale-out interlock before in-die changes. Complements Cankaya’s facility-level taps (different layer).</p>
  {svg_flexheg()}
  <figure>
    <img src="figures/flexheg_figure4_interlock_design.png" alt="FlexHEG interlock design figure"/>
    <figcaption>Interlock intuition: put the guarantee processor on a path data must cross.</figcaption>
  </figure>
  <figure>
    <img src="figures/fixed_set_pod_diagram.png" alt="Fixed set pod"/>
    <figcaption>Fixed-set pod idea: fast links inside a declared set; starved RDMA outside — a governance-shaped topology.</figcaption>
  </figure>
  <h3>Integration ladder (speed vs hardness)</h3>
  <div class="tbl">
    <table>
      <thead><tr><th>Mount</th><th>Deploy speed</th><th>Security</th><th>Who can ship it</th></tr></thead>
      <tbody>
        <tr><td>In-die / PCB redesign</td><td>slow (multi-year silicon + fleet churn)</td><td>strongest</td><td>incumbent vendors</td></tr>
        <tr><td>Retrofit modules</td><td>medium</td><td>medium (detach risk)</td><td>third parties possible</td></tr>
        <tr><td>Firmware-only</td><td>faster</td><td>weaker vs physical</td><td>needs signed secure boot</td></tr>
        <tr><td>Pure software</td><td>fastest</td><td>weakest</td><td>anyone — not a treaty root</td></tr>
      </tbody>
    </table>
  </div>
  <figure>
    <img src="figures/attestation_crypto_flow.png" alt="Attestation crypto flow"/>
    <figcaption>Attestation mental model — local measurement → signed statement → remote verify.</figcaption>
  </figure>
</section>

<section id="zk">
  <div class="kicker">Crypto horizon · training</div>
  <h2><span class="n">9.</span>Peigné-Lefebvre et al. — ZK verification of frontier <em>training</em></h2>
  <p class="dek"><a href="https://arxiv.org/abs/2606.05433">arXiv:2606.05433</a> · 2026 · GPAI Policy Lab / FAR.AI · Sorbonne/LIP6</p>
  <div class="two-col">
    <div class="panel">
      <h4>Who</h4>
      <p>Pierre Peigné-Lefebvre, Ky Nguyen, and coauthors — argument that ZK verification of frontier <em>training</em> is possible in principle via a BF16/FP32-aware zkVM.</p>
    </div>
    <div class="panel">
      <h4>Maturity</h4>
      <p><strong>Horizon.</strong> Authors are explicit: no working end-to-end prototype; rough ~36 months to a deployable PoC vs 6–10 years for custom verification silicon; long open-problem list.</p>
    </div>
  </div>
  <p><strong>Idea:</strong> make Shavit’s transcript story cryptographically binding — genesis / step / optional ex-ante proofs without revealing the proprietary run.</p>
  <p><strong>Lineage:</strong> Different problem than §§5–7 (those audit <em>inference</em> whitelist forward passes). This is the crypto endgame of classical <em>training</em> monitoring. Does not replace near-term FlexHEG/Cankaya work; clarifies what “strong” would mean if telemetry stays porous.</p>
  {svg_zk()}
</section>

<section id="synth">
  <div class="kicker">Synthesis</div>
  <h2><span class="n">10.</span>Putting the stack in one breath</h2>
  <p class="dek">What an outsider should be able to repeat after this deck.</p>
  <pre><code>Claim A = verify no covert frontier training (≠ TEE model-identity or
confidential-cloud claims B/C). Wasil is the method menu. Shavit is the
classical chip+transcript blueprint. Rahman measures how far NVML train↔infer
detectors survive disguise (closes Shavit’s lookalike gap). joshc red-teams cheap
facility controls against covert RL.

Cankaya is the near-term low-trust retrofit: NS-first taps feed commitments;
Plan A = AE precise replay (bit-exact metadata; DiFR if needed). Plan B swaps
the evaluate step for ZK — zkLLM (~13B exact integer circuit) or VerInf
(~400B unexplained-info bound Û). FlexHEG is the parallel hardware-enforcement
track (active caps / interlocks), not a substitute for taps+evaluate. Peigné
sketches ZK *training* as a longer crypto horizon. Almost none of this is mass-deployed product yet — blueprints,
empirics, and prototypes.</code></pre>
  <h3>Open problems / next-step research (what to do after this deck)</h3>
  <p>These are not “unsolved math curiosities” — they are the load-bearing gaps between today’s blueprints and a credible pause. Several track cruxes raised against Cankaya’s retrofit (precise replay, sampling economics, perimeter, rare covert adapters, Plan A→B transition, adjudication).</p>

  <div class="tbl">
    <table>
      <thead><tr><th>#</th><th>Problem</th><th>Why it blocks</th><th>Concrete next step</th></tr></thead>
      <tbody>
        <tr>
          <td class="mono">1</td>
          <td><strong>Precise replay vs softer accept</strong></td>
          <td>Plan A soundness/completeness hinge on bit-exact (or DiFR slack). Unknown: residual mismatch rate across SKU/driver/batch, and FP cost of chasing zero mismatch vs budgeting a channel.</td>
          <td>Medium-scale empirics (e.g. ~70B) across heterogeneous GPUs/drivers: exact-match rate vs DiFR-style accept; metadata necessity set; cost/latency of each policy.</td>
        </tr>
        <tr>
          <td class="mono">2</td>
          <td><strong>Sampling economics</strong></td>
          <td>Assurance = soundness × sample rate. Appendix-style Fermi needs a real BoM: can Plan A / zkLLM / VerInf hit ~1% overhead at a stated catch probability?</td>
          <td>Publish cost curves: challenge rate → catch prob → $/request for AE recompute vs zkLLM-13B vs VerInf-400B-class proofs.</td>
        </tr>
        <tr>
          <td class="mono">3</td>
          <td><strong>Perimeter / NS-only residual</strong></td>
          <td>NS-first taps leave EW copper and off-perimeter compute undertapped. Bar: residual outside the fence can’t do consequential covert work at high confidence.</td>
          <td>NS-only red-team budget (joshc-style local RL / DiLoCo): how many covert FLOPs survive; optional interconnect detectors (Fowler-style) as complement.</td>
        </tr>
        <tr>
          <td class="mono">4</td>
          <td><strong>Rare-trigger / thin adapters</strong></td>
          <td>Forward-pass recompute can match a whitelist while a rarely activated LoRA / tool path does harm — identity ≠ all governance goals.</td>
          <td>Red-team: memory probes, NVML anomaly, wipe/accounting, inspector agents under disclosure bounds; measure miss rate for sparse triggers.</td>
        </tr>
        <tr>
          <td class="mono">5</td>
          <td><strong>Train↔infer under disguise</strong></td>
          <td>Rahman: hard disguises degrade NVML classifiers. joshc: RL rollouts look like serving. Soft labels alone won’t carry Claim A.</td>
          <td>Combined channel study: NVML + interconnect bytes + tap commitments under adaptive evade; report ROC under the hardest loop, not only benign accuracy.</td>
        </tr>
        <tr>
          <td class="mono">6</td>
          <td><strong>Plan A → Plan B transition</strong></td>
          <td>Plaintext AE burns confidentiality; ZK restores it but is immature/expensive. Stakeholders need a migration path, not a cliff.</td>
          <td>Timeline + dual-run design: which challenge classes stay on AE, which move to zkLLM/VerInf as prove-time falls; joint ops with both evaluate engines.</td>
        </tr>
        <tr>
          <td class="mono">7</td>
          <td><strong>Physical security of AE / taps</strong></td>
          <td>Low-trust Plan A assumes rival TCBs + continuous physical monitoring. If forgeable silently, assurance collapses.</td>
          <td>Red-team / OSINT: diodes, FPGA wardens, SCIFs at scale, hosting foreign TCBs on sensitive weights — map failure modes to FlexHEG hardware track.</td>
        </tr>
        <tr>
          <td class="mono">8</td>
          <td><strong>Adjudication &amp; consequences</strong></td>
          <td>Technical Accept/Reject ≠ treaty breach. Without an escalation ladder + false-positive budget, either everything is excused or everything detonates.</td>
          <td>Design CBRN-like ladder: anomaly → joint review → deeper disclosure → supervised inspection → predetermined response; name who adjudicates.</td>
        </tr>
        <tr>
          <td class="mono">9</td>
          <td><strong>Hardware enforcement demos</strong></td>
          <td>FlexHEG remains the long enforcement story; near-term needs NIC/enclosure interlocks with honest overheads and multi-party rule updates.</td>
          <td>Ship a NIC-level license/FLOP-cap prototype; measure overhead; stress single-vendor root-of-trust objections.</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="note">
    <span class="label">How to read this list</span>
    <p><strong>1–5</strong> are mostly empirical / systems (can move in months). <strong>6–7</strong> mix engineering with deployment politics. <strong>8</strong> is institutional. <strong>9</strong> / §8 FlexHEG is the parallel hardware track. A credible pause needs progress on several in parallel — closing only crypto or only taps is not enough.</p>
  </div>
  <div class="note">
    <span class="label">Primary sources (public)</span>
    <p>
      Wasil <a href="https://arxiv.org/abs/2408.16074">2408.16074</a> ·
      Shavit <a href="https://arxiv.org/abs/2303.11341">2303.11341</a> ·
      joshc <a href="https://www.lesswrong.com/posts/oHiNwWtDPcBLumPWp/how-might-governments-slow-or-halt-ai-training">LW</a> ·
      FlexHEG <a href="https://www.flexheg.com/">flexheg.com</a> ·
      Rahman <a href="https://arxiv.org/abs/2606.19262">2606.19262</a> ·
      Cankaya overview <a href="https://www.lesswrong.com/posts/fgvmKqRGvBteKeDoc/a-system-overview-for-near-term-low-trust-ai-compute">LW</a> ·
      taps <a href="https://nacicankaya.substack.com/p/research-note-the-fundamentals-and">Substack</a> ·
      bit-exact <a href="https://arxiv.org/abs/2606.00279">2606.00279</a> ·
      zkLLM <a href="https://arxiv.org/abs/2404.16109">2404.16109</a> ·
      VerInf <a href="https://github.com/JamesPetrie/VerInf">GitHub</a> ·
      DiFR <a href="https://arxiv.org/abs/2511.20621">2511.20621</a> ·
      Peigné <a href="https://arxiv.org/abs/2606.05433">2606.05433</a>
    </p>
  </div>
</section>

'''

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Compute-Pause Verification — Study Notes</title>
<style>
{CSS}
{EXTRA_CSS}
</style>
</head>
<body>
<div class="page">
<nav class="toc" aria-label="Contents">
  <a href="#map"><span class="num">0</span>Map</a>
  <a href="#glossary"><span class="num">0b</span>Primer</a>
  <a href="#wasil"><span class="num">1</span>Wasil</a>
  <a href="#shavit"><span class="num">2</span>Shavit</a>
  <a href="#rahman"><span class="num">3</span>Rahman</a>
  <a href="#joshc"><span class="num">4</span>joshc</a>
  <a href="#cankaya"><span class="num">5</span>Plan A</a>
  <a href="#zkllm"><span class="num">6</span>zkLLM</a>
  <a href="#verinf"><span class="num">7</span>VerInf</a>
  <a href="#flexheg"><span class="num">8</span>FlexHEG</a>
  <a href="#zk"><span class="num">9</span>ZK-train</a>
  <a href="#synth"><span class="num">10</span>Synth</a>
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
print(f"wrote {out} ({out.stat().st_size} bytes)")
