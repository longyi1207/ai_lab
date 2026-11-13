"""SVG panels for the standalone compute-pause briefing deck."""

def svg_dc_topology():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 320" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .wire { stroke: #9a5b12; stroke-width: 1.5; fill: none; }
  </style>
  <text x="24" y="22" class="h">Datacenter hierarchy — IB/RoCE ≠ “only cross-pod”</text>
  <rect x="24" y="40" width="150" height="70" rx="3" class="box"/>
  <text x="36" y="62" class="t">GPU + HBM</text>
  <text x="36" y="80" class="s">die · SMs</text>
  <text x="36" y="96" class="s">ladder layer 1</text>
  <path d="M174 75 L200 75" class="wire"/>
  <rect x="200" y="40" width="170" height="70" rx="3" class="box"/>
  <text x="212" y="58" class="t">Node (e.g. 8-GPU)</text>
  <text x="212" y="76" class="s">NVLink inside = layer 2</text>
  <text x="212" y="94" class="s">NIC = layer-3 edge</text>
  <path d="M370 75 L396 75" class="wire"/>
  <rect x="396" y="40" width="140" height="70" rx="3" class="box"/>
  <text x="408" y="58" class="t">Rack</text>
  <text x="408" y="76" class="s">many nodes, or</text>
  <text x="408" y="94" class="s">1× NVL72 domain</text>
  <path d="M536 75 L562 75" class="wire"/>
  <rect x="562" y="40" width="134" height="70" rx="3" class="box"/>
  <text x="574" y="58" class="t">Pod / cluster</text>
  <text x="574" y="76" class="s">scale-out fabric</text>
  <text x="574" y="94" class="s">IB/RoCE leaf–spine</text>

  <rect x="24" y="128" width="672" height="72" rx="3" class="box"/>
  <text x="36" y="150" class="t">Where IB/RoCE actually starts = leaving the NVLink domain</text>
  <text x="36" y="170" class="s">Classic DGX: NVLink = one 8-GPU node → even same-rack node↔node is already IB/RoCE.</text>
  <text x="36" y="188" class="s">NVL72: NVLink = whole rack (72 GPUs) → IB/RoCE starts rack↔rack (in-pod or cross-pod).</text>

  <rect x="24" y="214" width="330" height="88" rx="3" class="box"/>
  <text x="36" y="236" class="t">East–West (inside the fence)</text>
  <text x="36" y="256" class="s">GPU↔GPU grads / acts / KV</text>
  <text x="36" y="274" class="s">= NVLink (in-domain) + IB/RoCE (out)</text>
  <text x="36" y="292" class="s">Fat · hard to tap fully</text>
  <rect x="366" y="214" width="330" height="88" rx="3" class="box"/>
  <text x="378" y="236" class="t">North–South (to the outside)</text>
  <text x="378" y="256" class="s">API tokens, SSH, admin, uploads</text>
  <text x="378" y="274" class="s">Skinny · natural chokepoint</text>
  <text x="378" y="292" class="s">Best first place for taps</text>
</svg>
<p class="cap">NIC sits on the node because that is the scale-out edge for classic topologies — not because IB is “a pod thing.” Cross-pod is just one hop on the same scale-out fabric.</p>
</div>'''


def svg_node_8gpu():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .g { fill: #fff; stroke: #9a5b12; }
    .wire { stroke: #8a867a; stroke-width: 1.2; fill: none; }
  </style>
  <text x="24" y="22" class="h">One 8-GPU node = ladder layers 2→3 (spatial zoom)</text>
  <rect x="40" y="40" width="520" height="180" rx="4" class="box"/>
  <text x="56" y="62" class="t">Server / node</text>
  <rect x="60" y="78" width="56" height="36" rx="2" class="g"/><text x="72" y="100" class="s">GPU0</text>
  <rect x="128" y="78" width="56" height="36" rx="2" class="g"/><text x="140" y="100" class="s">GPU1</text>
  <rect x="196" y="78" width="56" height="36" rx="2" class="g"/><text x="208" y="100" class="s">GPU2</text>
  <rect x="264" y="78" width="56" height="36" rx="2" class="g"/><text x="276" y="100" class="s">GPU3</text>
  <rect x="60" y="128" width="56" height="36" rx="2" class="g"/><text x="72" y="150" class="s">GPU4</text>
  <rect x="128" y="128" width="56" height="36" rx="2" class="g"/><text x="140" y="150" class="s">GPU5</text>
  <rect x="196" y="128" width="56" height="36" rx="2" class="g"/><text x="208" y="150" class="s">GPU6</text>
  <rect x="264" y="128" width="56" height="36" rx="2" class="g"/><text x="276" y="150" class="s">GPU7</text>
  <text x="56" y="188" class="s">Layer 2: NVLink / NVSwitch (copper, intra-node)</text>
  <rect x="360" y="90" width="160" height="70" rx="3" class="box"/>
  <text x="372" y="114" class="t">NIC → layer 3</text>
  <text x="372" y="132" class="s">InfiniBand / RoCE</text>
  <text x="372" y="148" class="s">node ↔ other nodes</text>
  <path d="M332 120 L360 120" class="wire"/>
  <text x="580" y="100" class="t">← to fabric</text>
  <text x="40" y="242" class="s">NVML reads per-GPU sensors inside the box. Cross-node bytes = NIC/NCCL path (layer 3), not NVML alone.</text>
</svg>
<p class="cap">Spatial zoom of the interconnect ladder’s layers 2→3. Fowler-style “two 8-GPU nodes” watch the cable between NICs; Rahman-style classifiers watch per-GPU NVML time series.</p>
</div>'''


def svg_interconnect_ladder():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Interconnect ladder copper to optics">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.25; }
  </style>
  <text x="24" y="22" class="h">Interconnect ladder — copper vs optics (organizing abstraction for everything below)</text>
  <text x="24" y="36" class="s">Read top→bottom once; later figures are zooms of a single layer.</text>

  <rect x="24" y="48" width="672" height="52" rx="3" class="hi"/>
  <text x="36" y="68" class="t">1 · Die / package / board</text>
  <text x="36" y="86" class="s">On-die mesh · HBM · NVLink-C2C (Grace↔GPU). Electrical, mm–cm. Opaque to facility taps. → zoom: board + SM</text>

  <rect x="24" y="112" width="672" height="52" rx="3" class="box"/>
  <text x="36" y="132" class="t">2 · Scale-up domain (NVLink / NVSwitch)</text>
  <text x="36" y="150" class="s">Intra-node mesh or whole-rack copper spine (NVL72). Still mostly electrical. → zoom: NVL72 + 8-GPU node</text>

  <rect x="24" y="176" width="672" height="70" rx="3" class="box"/>
  <text x="36" y="196" class="t">3 · Scale-out fabric (InfiniBand / RoCE / Spectrum-X)</text>
  <text x="36" y="214" class="s">NIC → DAC copper (short) or AOC/transceiver (longer). Here electrical ↔ optical conversion happens:</text>
  <text x="36" y="232" class="s">SerDes → laser/photodiode in QSFP/OSFP → fiber → far end recovers electrical → switch ASIC.</text>

  <rect x="24" y="258" width="330" height="58" rx="3" class="box"/>
  <text x="36" y="280" class="t">Tap-friendly</text>
  <text x="36" y="298" class="s">Optical fiber / NS chokepoints · passive taps</text>
  <rect x="366" y="258" width="330" height="58" rx="3" class="box"/>
  <text x="378" y="280" class="t">Tap-hostile</text>
  <text x="378" y="298" class="s">Copper NVLink spine · on-board links</text>
</svg>
<p class="cap">IB/RoCE (layer 3) carry the cross-node all-reduces Claim A people want to meter. Layer-2 copper spines move TB/s without becoming light — hard tap case for Cankaya/joshc.</p>
</div>'''


def svg_sm():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Streaming multiprocessor">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .g { fill: #fff; stroke: #9a5b12; stroke-width: 1; }
  </style>
  <text x="24" y="22" class="h">SM = Streaming Multiprocessor (GPU’s compute tile)</text>
  <rect x="24" y="40" width="280" height="200" rx="3" class="box"/>
  <text x="36" y="62" class="t">One GPU die (cartoon)</text>
  <rect x="44" y="78" width="36" height="28" rx="2" class="g"/>
  <rect x="88" y="78" width="36" height="28" rx="2" class="g"/>
  <rect x="132" y="78" width="36" height="28" rx="2" class="g"/>
  <rect x="176" y="78" width="36" height="28" rx="2" class="g"/>
  <rect x="220" y="78" width="36" height="28" rx="2" class="g"/>
  <rect x="44" y="116" width="36" height="28" rx="2" class="g"/>
  <rect x="88" y="116" width="36" height="28" rx="2" class="g"/>
  <rect x="132" y="116" width="36" height="28" rx="2" class="g"/>
  <rect x="176" y="116" width="36" height="28" rx="2" class="g"/>
  <rect x="220" y="116" width="36" height="28" rx="2" class="g"/>
  <rect x="44" y="154" width="36" height="28" rx="2" class="g"/>
  <rect x="88" y="154" width="36" height="28" rx="2" class="g"/>
  <rect x="132" y="154" width="36" height="28" rx="2" class="g"/>
  <rect x="176" y="154" width="36" height="28" rx="2" class="g"/>
  <rect x="220" y="154" width="36" height="28" rx="2" class="g"/>
  <text x="36" y="210" class="s">H100 ≈ 132 SMs · each SM = many</text>
  <text x="36" y="226" class="s">CUDA cores + Tensor Cores + schedulers</text>

  <rect x="320" y="40" width="376" height="200" rx="3" class="box"/>
  <text x="332" y="62" class="t">What “SM util” actually measures</text>
  <text x="332" y="88" class="s">NVML “SM utilization” ≈ fraction of SMs that</text>
  <text x="332" y="106" class="s">had ≥1 warp active over the sample window.</text>
  <text x="332" y="132" class="s">High SM util ⇒ compute units busy.</text>
  <text x="332" y="150" class="s">Low SM util + high HBM BW ⇒ memory-bound</text>
  <text x="332" y="168" class="s">(classic decode / bandwidth-limited kernels).</text>
  <text x="332" y="194" class="s">Does <tspan font-weight="600">not</tspan> say train vs infer, legal vs covert,</text>
  <text x="332" y="212" class="s">or which model. Just “are SMs awake?”</text>
</svg>
<p class="cap">Think of SMs as many small CPUs glued to shared HBM. Prefill matmuls wake lots of SMs; token-by-token decode often waits on memory → SM util can look “idle” while the GPU is still serving.</p>
</div>'''


def svg_allreduce():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Collectives that make training “loud” on the network</text>
  <rect x="24" y="40" width="330" height="150" rx="3" class="box"/>
  <text x="36" y="64" class="t">All-reduce (DDP heartbeat)</text>
  <text x="36" y="88" class="s">Each GPU has local gradient gᵢ</text>
  <text x="36" y="106" class="s">→ everyone gets mean(g)</text>
  <text x="36" y="124" class="s">Bytes / step ≈ O(model size)</text>
  <text x="36" y="148" class="s">Big, regular, every step</text>
  <text x="36" y="172" class="s">Cross-node → IB/RoCE counters spike</text>
  <rect x="366" y="40" width="330" height="150" rx="3" class="box"/>
  <text x="378" y="64" class="t">All-gather (FSDP / some TP)</text>
  <text x="378" y="88" class="s">Each GPU holds a shard</text>
  <text x="378" y="106" class="s">→ assemble full tensor locally</text>
  <text x="378" y="124" class="s">Also O(params) class traffic</text>
  <text x="378" y="148" class="s">Inference usually ships activations</text>
  <text x="378" y="172" class="s">or KV — O(tokens×hidden), not O(params)/step</text>
</svg>
<p class="cap">DiLoCo / LocalSGD: train locally for many steps, sync rarely → average cross-node GB/s can look “inference-quiet” while training still happens.</p>
</div>'''


def svg_prefill_decode():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 230" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .bar { fill: #9a5b12; opacity: 0.35; }
  </style>
  <text x="24" y="22" class="h">Inference anatomy: prefill vs decode (and why disagg ships KV)</text>
  <rect x="40" y="50" width="280" height="40" class="bar"/>
  <text x="50" y="75" class="t">Prefill — ingest whole prompt, build KV</text>
  <rect x="330" y="50" width="40" height="40" class="bar"/>
  <rect x="380" y="50" width="40" height="40" class="bar"/>
  <rect x="430" y="50" width="40" height="40" class="bar"/>
  <rect x="480" y="50" width="40" height="40" class="bar"/>
  <text x="330" y="110" class="s">Decode — one new token at a time</text>
  <rect x="24" y="130" width="330" height="80" rx="3" class="box"/>
  <text x="36" y="154" class="t">Same box (usual serving)</text>
  <text x="36" y="174" class="s">Prefill+decode share GPUs</text>
  <text x="36" y="194" class="s">Cross-node often quiet</text>
  <rect x="366" y="130" width="330" height="80" rx="3" class="box"/>
  <text x="378" y="154" class="t">Disaggregated serving</text>
  <text x="378" y="174" class="s">Prefill pool → ship KV → decode pool</text>
  <text x="378" y="194" class="s">Can make NS/EW look “training-loud”</text>
</svg>
<p class="cap">SM util: how busy GPU compute units are. Prefill can pin SMs; decode is often memory-bandwidth bound — so SM util alone is a weak train/infer label.</p>
</div>'''


def svg_zk_constraints():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 420" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">ZK vocabulary (enough to read zkLLM / VerInf / Peigné)</text>
  <rect x="24" y="36" width="220" height="100" rx="3" class="box"/>
  <text x="36" y="58" class="t">Statement</text>
  <text x="36" y="78" class="s">“I ran model W on x</text>
  <text x="36" y="94" class="s">and got y” (or a bound)</text>
  <text x="36" y="118" class="s">Public: arch, C=Commit(W)</text>
  <rect x="256" y="36" width="220" height="100" rx="3" class="box"/>
  <text x="268" y="58" class="t">Witness</text>
  <text x="268" y="78" class="s">Secret intermediates:</text>
  <text x="268" y="94" class="s">weights, activations…</text>
  <text x="268" y="118" class="s">Prover holds; verifier doesn’t</text>
  <rect x="488" y="36" width="208" height="100" rx="3" class="box"/>
  <text x="500" y="58" class="t">Constraints</text>
  <text x="500" y="78" class="s">Algebraic equations that</text>
  <text x="500" y="94" class="s">every correct step must</text>
  <text x="500" y="118" class="s">satisfy (the “circuit”)</text>
  <rect x="24" y="152" width="340" height="100" rx="3" class="box"/>
  <text x="36" y="174" class="t">Properties you want</text>
  <text x="36" y="196" class="s">Completeness: honest prover convinces</text>
  <text x="36" y="214" class="s">Soundness: cheater almost never passes</text>
  <text x="36" y="232" class="s">Zero-knowledge: proof leaks ~nothing extra</text>
  <rect x="376" y="152" width="320" height="100" rx="3" class="box"/>
  <text x="388" y="174" class="t">In this literature</text>
  <text x="388" y="196" class="s">zkLLM: prove exact integer circuit</text>
  <text x="388" y="214" class="s">VerInf: prove unexplained bits ≤ U</text>
  <text x="388" y="232" class="s">Peigné: ZK for training steps (horizon)</text>

  <rect x="24" y="268" width="672" height="130" rx="3" class="box"/>
  <text x="36" y="290" class="t">The integer / finite-field constraint (why float GPUs ≠ ZK circuits)</text>
  <text x="36" y="312" class="s">SNARKs do arithmetic in a prime field 𝔽_p (integers mod p). GPU serving does BF16/FP8 floats with rounding.</text>
  <text x="36" y="330" class="s">So zkLLM-style systems re-express the forward pass as a quantized / integer circuit, then prove that circuit.</text>
  <text x="36" y="348" class="s">What you proved: “integer program with Commit(W) produced y.” What you did <tspan font-weight="600">not</tspan> prove: bit-exact match to</text>
  <text x="36" y="366" class="s">arbitrary float serving on H100/B200. Softmax/nondeterminism → lookups + tolerances, not native IEEE floats.</text>
  <text x="36" y="384" class="s">VerInf dodges this by proving an unexplained-info bound instead of exact float equality.</text>
</svg>
<p class="cap">A “constraint” is a math check over 𝔽_p (e.g. c − a·b = 0), not a governance policy. The integer gap is why “ZK receipt” and “bit-exact AE recompute” are different Plan B / Plan A stories.</p>
</div>'''


def svg_cankaya_facility():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 340" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.3; }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.1; marker-end: url(#ca); }
  </style>
  <defs>
    <marker id="ca" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
      <path d="M0,0 L5,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="20" class="h">Cankaya Plan A sketch — taps + air-gapped audit environment (AE)</text>
  <rect x="24" y="32" width="200" height="90" rx="3" class="box"/>
  <text x="36" y="54" class="t">Users / API</text>
  <text x="36" y="74" class="s">prompts in</text>
  <text x="36" y="92" class="s">tokens out</text>
  <path d="M224 70 L260 70" class="arr"/>
  <rect x="260" y="32" width="220" height="90" rx="3" class="hi"/>
  <text x="272" y="54" class="t">Monitored GPU pod</text>
  <text x="272" y="74" class="s">claimed whitelist model</text>
  <text x="272" y="92" class="s">NS link via warden</text>
  <path d="M370 122 L370 150" class="arr"/>
  <rect x="260" y="150" width="220" height="70" rx="3" class="box"/>
  <text x="272" y="172" class="t">Network tap (FPGA)</text>
  <text x="272" y="192" class="s">hash+sign payloads only</text>
  <text x="272" y="208" class="s">not semantic parse</text>
  <path d="M480 185 L520 185" class="arr"/>
  <rect x="520" y="150" width="176" height="70" rx="3" class="box"/>
  <text x="532" y="172" class="t">Verifier ledger</text>
  <text x="532" y="192" class="s">commitments only</text>
  <text x="532" y="208" class="s">(may be offshore)</text>
  <path d="M370 220 L370 248" class="arr"/>
  <rect x="200" y="248" width="340" height="78" rx="3" class="hi"/>
  <text x="212" y="270" class="t">AE (air-gapped) — Plan A evaluate</text>
  <text x="212" y="288" class="s">≥3 heterogeneous TCBs cross-check</text>
  <text x="212" y="304" class="s">reload W; Hash(W)=C; replay I/O; compare</text>
  <text x="212" y="318" class="s">executor GPU need not be trusted</text>
  <rect x="24" y="150" width="200" height="70" rx="3" class="box"/>
  <text x="36" y="172" class="t">Prover store</text>
  <text x="36" y="192" class="s">plaintext preimages</text>
  <text x="36" y="208" class="s">+ manifest / metadata</text>
</svg>
<p class="cap">Adapted from Cankaya’s system overview: online evidence capture is continuous; evaluation is random challenges. Plan B swaps the AE plaintext recompute for a ZK proof.</p>
</div>'''


def svg_four_gates():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 11px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Cankaya’s four doors on a challenged forward pass</text>
  <rect x="20" y="40" width="165" height="130" rx="3" class="box"/>
  <text x="32" y="64" class="t">1 · Weights</text>
  <text x="32" y="88" class="s">Hash(W) = C</text>
  <text x="32" y="108" class="s">whitelist model?</text>
  <text x="32" y="136" class="s">Hard check</text>
  <rect x="195" y="40" width="165" height="130" rx="3" class="box"/>
  <text x="207" y="64" class="t">2 · I/O evidence</text>
  <text x="207" y="88" class="s">preimage matches</text>
  <text x="207" y="108" class="s">tap commitment</text>
  <text x="207" y="136" class="s">Hard check</text>
  <rect x="370" y="40" width="165" height="130" rx="3" class="box"/>
  <text x="382" y="64" class="t">3 · Recompute</text>
  <text x="382" y="88" class="s">run W on input;</text>
  <text x="382" y="108" class="s">output matches?</text>
  <text x="382" y="136" class="s">Hard (bit-exact ideal)</text>
  <rect x="545" y="40" width="155" height="130" rx="3" class="box"/>
  <text x="557" y="64" class="t">4 · Semantics</text>
  <text x="557" y="88" class="s">blacklist use?</text>
  <text x="557" y="108" class="s">(CBRN, etc.)</text>
  <text x="557" y="136" class="s">Soft / inspectors</text>
</svg>
<p class="cap">Doors 1–3 can all pass while door 4 fails: whitelist model doing banned things. Soft classifiers are not a substitute for 1–3.</p>
</div>'''


def svg_joshc_tools():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg">
  <style>
    .t { font: 600 10.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 9.5px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">joshc near-term toolkit (facility mods before FlexHEG silicon)</text>
  <rect x="16" y="40" width="130" height="130" rx="3" class="box"/>
  <text x="28" y="64" class="t">Pull IB</text>
  <text x="28" y="88" class="s">Yank fat fabric;</text>
  <text x="28" y="106" class="s">force slow copper</text>
  <text x="28" y="140" class="s">hurts multi-node</text>
  <text x="28" y="156" class="s">train sync</text>
  <rect x="156" y="40" width="130" height="130" rx="3" class="box"/>
  <text x="168" y="64" class="t">BW limiter</text>
  <text x="168" y="88" class="s">Cap egress</text>
  <text x="168" y="106" class="s">(~100 KB/s)</text>
  <text x="168" y="140" class="s">+ TAP sample</text>
  <rect x="296" y="40" width="140" height="130" rx="3" class="box"/>
  <text x="308" y="64" class="t">Output recompute</text>
  <text x="308" y="88" class="s">Replay model M</text>
  <text x="308" y="106" class="s">on tapped I/O</text>
  <text x="308" y="140" class="s">Loose match →</text>
  <text x="308" y="156" class="s">covert channel</text>
  <rect x="446" y="40" width="130" height="130" rx="3" class="box"/>
  <text x="458" y="64" class="t">Memory wipe</text>
  <text x="458" y="88" class="s">Fill RAM with</text>
  <text x="458" y="106" class="s">known noise;</text>
  <text x="458" y="124" class="s">challenge; then</text>
  <text x="458" y="142" class="s">reload whitelist</text>
  <text x="458" y="158" class="s">via controlled path</text>
  <rect x="586" y="40" width="118" height="130" rx="3" class="box"/>
  <text x="598" y="64" class="t">PoW / PoM</text>
  <text x="598" y="88" class="s">Account FLOPs</text>
  <text x="598" y="106" class="s">/ memory vs</text>
  <text x="598" y="124" class="s">declared work</text>
  <text x="598" y="150" class="s">&gt;95% coverage</text>
</svg>
<p class="cap">Whitelist channel = the only high-bandwidth path allowed to reload weights after a wipe — gated by Hash(W)∈registered commitments.</p>
</div>'''


def svg_verify_properties():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Verification properties">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Four properties (use these words precisely in §§6–8)</text>

  <rect x="24" y="40" width="336" height="88" rx="3" class="box"/>
  <text x="36" y="62" class="t">Completeness</text>
  <text x="36" y="82" class="s">Honest compliant prover almost always</text>
  <text x="36" y="100" class="s">passes. False reject → kills the deal.</text>
  <text x="36" y="118" class="s">(“If I’m clean, I get accepted.”)</text>

  <rect x="372" y="40" width="324" height="88" rx="3" class="box"/>
  <text x="384" y="62" class="t">Soundness</text>
  <text x="384" y="82" class="s">Cheater almost never passes.</text>
  <text x="384" y="100" class="s">False accept → fake compliance.</text>
  <text x="384" y="118" class="s">(“Dirty run can’t forge Accept.”)</text>

  <rect x="24" y="144" width="336" height="100" rx="3" class="box"/>
  <text x="36" y="166" class="t">Confidentiality</text>
  <text x="36" y="186" class="s">Weights / prompts / activations / customer</text>
  <text x="36" y="204" class="s">data stay private from the other party</text>
  <text x="36" y="222" class="s">(and often from each other’s silicon).</text>
  <text x="36" y="240" class="s">ZK ≈ cryptographic confidentiality of witness.</text>

  <rect x="372" y="144" width="324" height="100" rx="3" class="box"/>
  <text x="384" y="166" class="t">Assurance</text>
  <text x="384" y="186" class="s">How sure is the auditor that cheating</text>
  <text x="384" y="204" class="s">would be caught in the field?</text>
  <text x="384" y="222" class="s">Includes soundness + sampling rate +</text>
  <text x="384" y="240" class="s">tap coverage + stego slack (joshc ~1%).</text>

  <rect x="24" y="260" width="672" height="80" rx="3" class="box"/>
  <text x="36" y="282" class="t">Plan A vs Plan B on these axes</text>
  <text x="36" y="302" class="s">Plan A (plaintext AE recompute): can be strong on completeness/soundness/assurance if bit-exact + dense sampling —</text>
  <text x="36" y="320" class="s">but burns confidentiality (weights + challenged I/O enter the AE). Plan B (ZK): keep soundness/completeness goals,</text>
  <text x="36" y="338" class="s">restore confidentiality of the witness; assurance still needs sampling + good taps — π doesn’t watch untapped cables.</text>
</svg>
<p class="cap">Don’t collapse these. A demo can be complete+sound in crypto and still give low assurance if you sample 0.001% of requests or leave EW copper blind.</p>
</div>'''


def svg_why_not_plaintext():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Why plaintext recompute is not enough">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Why plaintext AE recompute is not “the endgame”</text>
  <rect x="24" y="40" width="220" height="120" rx="3" class="box"/>
  <text x="36" y="62" class="t">1 · IP / data</text>
  <text x="36" y="84" class="s">Whitelist W and challenged</text>
  <text x="36" y="102" class="s">x,y enter the AE in clear.</text>
  <text x="36" y="120" class="s">Rival states / labs hate this.</text>
  <text x="36" y="144" class="s">→ confidentiality failure</text>
  <rect x="256" y="40" width="220" height="120" rx="3" class="box"/>
  <text x="268" y="62" class="t">2 · Mutual distrust</text>
  <text x="268" y="84" class="s">Whose GPU is the AE?</text>
  <text x="268" y="102" class="s">Prover won’t trust verifier’s</text>
  <text x="268" y="120" class="s">box; verifier won’t trust</text>
  <text x="268" y="144" class="s">prover’s box either.</text>
  <rect x="488" y="40" width="208" height="120" rx="3" class="box"/>
  <text x="500" y="62" class="t">3 · AE is still a TCB</text>
  <text x="500" y="84" class="s">Air-gap ≠ zero leak.</text>
  <text x="500" y="102" class="s">Need diodes, cross-checks,</text>
  <text x="500" y="120" class="s">physical monitoring —</text>
  <text x="500" y="144" class="s">Cankaya’s hard part.</text>
  <rect x="24" y="180" width="672" height="100" rx="3" class="box"/>
  <text x="36" y="202" class="t">So why is Plan A still the near-term default?</text>
  <text x="36" y="224" class="s">Because it is fieldable without frontier-scale ZK: if you can stomach AE confidentiality risk + build bit-exact replay,</text>
  <text x="36" y="242" class="s">you get real assurance against “swap the model on the wire.” Plan B (zkLLM / VerInf) replaces the AE evaluate step when</text>
  <text x="36" y="260" class="s">confidentiality is the dealbreaker — it does not remove taps, sampling, or the need for soundness of the statement.</text>
</svg>
<p class="cap">Plaintext recompute answers soundness-ish checks by literally redoing the math. ZK answers them with a proof. Same audit question; different confidentiality cost.</p>
</div>'''


def svg_zk_recipe():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three-step hash-based zkSNARK recipe">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f3f0ea; stroke: #9a5b12; stroke-width: 1.3; }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#mr); }
  </style>
  <defs>
    <marker id="mr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="22" class="h">Hash-based zkSNARK = three compiles (BCS recipe)</text>

  <rect x="24" y="40" width="200" height="150" rx="4" class="hi"/>
  <text x="36" y="62" class="t">1 · IOP</text>
  <text x="36" y="84" class="s">Info-theoretic proof.</text>
  <text x="36" y="102" class="s">Prover posts long tables</text>
  <text x="36" y="120" class="s">(oracles). Verifier makes</text>
  <text x="36" y="138" class="s">few random point queries.</text>
  <text x="36" y="160" class="s">No crypto yet — just math.</text>
  <text x="36" y="178" class="s">~error-correcting codes.</text>

  <path d="M224 115 L248 115" class="arr"/>

  <rect x="248" y="40" width="200" height="150" rx="4" class="box"/>
  <text x="260" y="62" class="t">2 · Merkle</text>
  <text x="260" y="84" class="s">Commit to each long table</text>
  <text x="260" y="102" class="s">with a hash tree. Send only</text>
  <text x="260" y="120" class="s">the root. Later open the</text>
  <text x="260" y="138" class="s">queried cells + auth paths.</text>
  <text x="260" y="160" class="s">→ interactive argument</text>
  <text x="260" y="178" class="s">(computational soundness).</text>

  <path d="M448 115 L472 115" class="arr"/>

  <rect x="472" y="40" width="224" height="150" rx="4" class="box"/>
  <text x="484" y="62" class="t">3 · Fiat–Shamir</text>
  <text x="484" y="84" class="s">Replace verifier’s random</text>
  <text x="484" y="102" class="s">challenges with</text>
  <text x="484" y="120" class="s">H(transcript so far).</text>
  <text x="484" y="138" class="s">One proof file. Verifier</text>
  <text x="484" y="160" class="s">re-derives challenges,</text>
  <text x="484" y="178" class="s">checks openings + eqs.</text>

  <rect x="24" y="208" width="672" height="56" rx="3" class="box"/>
  <text x="36" y="230" class="t">What FlashProve / zkLLM / VerInf customize</text>
  <text x="36" y="250" class="s">Almost always Step 1 (the IOP for “this forward pass / bound”). Steps 2–3 are standard hash machinery (BLAKE2, Merkle, FS).</text>
</svg>
<p class="cap">Memorize this stack. When a paper says “we prove inference,” ask: what is the IOP relation? Everything else is packaging.</p>
</div>'''


def svg_reed_solomon_zk():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Reed-Solomon zero-knowledge encoding">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Reed–Solomon + random mask = zero-knowledge encoding</text>

  <rect x="24" y="40" width="330" height="140" rx="3" class="box"/>
  <text x="36" y="62" class="t">Message → polynomial → codeword</text>
  <text x="36" y="84" class="s">weights m₀…mₖ₋₁ + random r₀…rₜ₋₁</text>
  <text x="36" y="104" class="s">f(X) = r₀ + r₁X + … + rₜ₋₁ Xᵗ⁻¹</text>
  <text x="36" y="122" class="s">         + m₀ Xᵗ + … + mₖ₋₁ Xᵗ⁺ᵏ⁻¹</text>
  <text x="36" y="144" class="s">Evaluate f at n ≫ k points → long row</text>
  <text x="36" y="166" class="s">Different messages → rows differ almost everywhere</text>

  <rect x="366" y="40" width="330" height="140" rx="3" class="box"/>
  <text x="378" y="62" class="t">Why ≤ t opens leak nothing</text>
  <text x="378" y="84" class="s">Any t values of f are fixed by the</text>
  <text x="378" y="102" class="s">random mask alone — statistically</text>
  <text x="378" y="120" class="s">independent of the weights m.</text>
  <text x="378" y="144" class="s">t = query budget. Open more than t</text>
  <text x="378" y="166" class="s">columns ⇒ privacy can break.</text>

  <rect x="24" y="196" width="672" height="84" rx="3" class="box"/>
  <text x="36" y="218" class="t">FlashProve consequence</text>
  <text x="36" y="238" class="s">Commit once (anchor table). Each proof opens a few columns → budget depletes. So make many leaf tables with fresh masks,</text>
  <text x="36" y="256" class="s">each linked to the anchor (“same weights, new randomness”). One commitment ≈ millions of proofs until leaves wear out.</text>
</svg>
<p class="cap">College linear algebra: a degree-&lt;d polynomial is fixed by d points. Random low coefficients make the first t samples look random.</p>
</div>'''


def svg_merkle_open():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 290" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Merkle tree commit and open">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .hi { fill: #f7efe0; stroke: #9a5b12; stroke-width: 1.2; }
    .ln { stroke: #8a867a; stroke-width: 1.1; }
  </style>
  <text x="24" y="22" class="h">Merkle commitment: bind a long vector; open one cell later</text>

  <rect x="310" y="40" width="100" height="36" rx="3" class="hi"/>
  <text x="328" y="62" class="t">root R</text>
  <line x1="360" y1="76" x2="250" y2="100" class="ln"/>
  <line x1="360" y1="76" x2="470" y2="100" class="ln"/>

  <rect x="200" y="100" width="100" height="32" rx="3" class="box"/>
  <text x="214" y="120" class="s">H(left)</text>
  <rect x="420" y="100" width="100" height="32" rx="3" class="hi"/>
  <text x="434" y="120" class="s">H(right)</text>
  <line x1="250" y1="132" x2="160" y2="160" class="ln"/>
  <line x1="250" y1="132" x2="300" y2="160" class="ln"/>
  <line x1="470" y1="132" x2="420" y2="160" class="ln"/>
  <line x1="470" y1="132" x2="560" y2="160" class="ln"/>

  <rect x="110" y="160" width="90" height="28" rx="3" class="box"/>
  <text x="128" y="178" class="s">col 0</text>
  <rect x="250" y="160" width="90" height="28" rx="3" class="box"/>
  <text x="268" y="178" class="s">col 1</text>
  <rect x="390" y="160" width="90" height="28" rx="3" class="hi"/>
  <text x="408" y="178" class="s">col 2 ★</text>
  <rect x="530" y="160" width="90" height="28" rx="3" class="box"/>
  <text x="548" y="178" class="s">col 3</text>

  <rect x="24" y="208" width="672" height="66" rx="3" class="box"/>
  <text x="36" y="230" class="t">Open col 2</text>
  <text x="36" y="250" class="s">Send value(col 2) + sibling hashes on the path to R. Verifier re-hashes upward; accepts iff root matches the committed R.</text>
  <text x="36" y="268" class="s">Prover can’t change an unopened column later without breaking the root (assuming H is collision-resistant).</text>
</svg>
<p class="cap">IOP said “query oracle[i]”. Merkle implements that query without shipping the whole oracle.</p>
</div>'''


def svg_sumcheck_round():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="One round of sumcheck">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Sumcheck — reduce a huge sum to one random evaluation</text>

  <rect x="24" y="40" width="672" height="70" rx="3" class="box"/>
  <text x="36" y="62" class="t">Claim to check</text>
  <text x="36" y="84" class="s">Σ_{x ∈ {0,1}ⁿ} P(x)  =  S     (P known as a small arithmetic circuit / formula; n can be 20–40 → millions of terms)</text>

  <rect x="24" y="124" width="210" height="120" rx="3" class="box"/>
  <text x="36" y="146" class="t">Round i</text>
  <text x="36" y="168" class="s">Prover sends univariate</text>
  <text x="36" y="186" class="s">gᵢ(X) = Σ_{rest} P(r₁…rᵢ₋₁, X, ·)</text>
  <text x="36" y="210" class="s">Verifier checks</text>
  <text x="36" y="228" class="s">gᵢ(0)+gᵢ(1) = prior claim</text>

  <rect x="250" y="124" width="210" height="120" rx="3" class="box"/>
  <text x="262" y="146" class="t">Challenge</text>
  <text x="262" y="168" class="s">Verifier samples random</text>
  <text x="262" y="186" class="s">rᵢ ∈ 𝔽 (or H(transcript)</text>
  <text x="262" y="204" class="s">after Fiat–Shamir).</text>
  <text x="262" y="228" class="s">New claim: gᵢ(rᵢ) = Sᵢ</text>

  <rect x="476" y="124" width="220" height="120" rx="3" class="box"/>
  <text x="488" y="146" class="t">After n rounds</text>
  <text x="488" y="168" class="s">Claim is just</text>
  <text x="488" y="186" class="s">P(r₁,…,rₙ) = Sₙ</text>
  <text x="488" y="210" class="s">Verifier evaluates P at</text>
  <text x="488" y="228" class="s">that one point (cheap).</text>

  <rect x="24" y="260" width="672" height="64" rx="3" class="box"/>
  <text x="36" y="282" class="t">Why cheating fails</text>
  <text x="36" y="302" class="s">A false gᵢ agrees with the true univariate on ≤ deg(g) points. Random rᵢ hits a lie with tiny probability. n rounds → soundness ~ n·deg/|𝔽|.</text>
</svg>
<p class="cap">Workhorse of FlashProve (~2000 sumchecks / request). Matmul / all-reduce-style sums → few random point checks.</p>
</div>'''


def svg_fiat_shamir():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Fiat-Shamir transformation">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#mf); }
  </style>
  <defs>
    <marker id="mf" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="22" class="h">Fiat–Shamir: interactive random challenges → one proof file</text>

  <rect x="24" y="44" width="150" height="70" rx="3" class="box"/>
  <text x="36" y="68" class="t">msg₁</text>
  <text x="36" y="90" class="s">prover message</text>
  <path d="M174 79 L210 79" class="arr"/>
  <rect x="210" y="44" width="150" height="70" rx="3" class="box"/>
  <text x="222" y="68" class="t">c₁ = H(…)</text>
  <text x="222" y="90" class="s">challenge</text>
  <path d="M360 79 L396 79" class="arr"/>
  <rect x="396" y="44" width="150" height="70" rx="3" class="box"/>
  <text x="408" y="68" class="t">msg₂</text>
  <text x="408" y="90" class="s">depends on c₁</text>
  <path d="M546 79 L582 79" class="arr"/>
  <rect x="582" y="44" width="114" height="70" rx="3" class="box"/>
  <text x="594" y="68" class="t">c₂ = H</text>
  <text x="594" y="90" class="s">…</text>

  <rect x="24" y="140" width="672" height="100" rx="3" class="box"/>
  <text x="36" y="162" class="t">Security intuition (random-oracle model)</text>
  <text x="36" y="184" class="s">Prover must fix msgᵢ before learning cᵢ = H(transcript). To try many cᵢ they must re-hash many transcripts — expensive if H is</text>
  <text x="36" y="202" class="s">idealized as a random function (BLAKE2 in FlashProve). Verifier never sends coins; they recompute the same hash chain from the file.</text>
  <text x="36" y="224" class="s">FlashProve twist: challenges form a DAG (per-request chains join for a shared proximity test) so GPU can overlap work across a batch.</text>
</svg>
<p class="cap">If you only remember one sentence: the proof file is a frozen interactive transcript whose “randomness” is the hash of what came before.</p>
</div>'''


def svg_lookup_and_linear():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Lookups and linear claims">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Two more IOP gadgets you will see everywhere in zkML</text>

  <rect x="24" y="40" width="336" height="150" rx="3" class="box"/>
  <text x="36" y="62" class="t">Lookup</text>
  <text x="36" y="84" class="s">Non-arithmetic ops (SiLU, Softmax</text>
  <text x="36" y="102" class="s">piece, comparisons) → public table T</text>
  <text x="36" y="120" class="s">of pairs (u, f(u)). Prover claims every</text>
  <text x="36" y="138" class="s">secret pair is a row of T. Checked via</text>
  <text x="36" y="156" class="s">sumcheck-style grand-product / LogUp.</text>
  <text x="36" y="178" class="s">Table size must stay small (~2¹⁶).</text>

  <rect x="376" y="40" width="320" height="150" rx="3" class="box"/>
  <text x="388" y="62" class="t">Linear claim</text>
  <text x="388" y="84" class="s">End state of almost every reduction:</text>
  <text x="388" y="102" class="s">⟨v, m⟩ = c for known v,c and secret</text>
  <text x="388" y="120" class="s">committed message m. Batch many via</text>
  <text x="388" y="138" class="s">random linear combo. Then one</text>
  <text x="388" y="156" class="s">proximity test opens a few columns</text>
  <text x="388" y="178" class="s">and checks the combo + code distance.</text>

  <rect x="24" y="206" width="672" height="58" rx="3" class="box"/>
  <text x="36" y="228" class="t">Inference IOP flow (one sentence)</text>
  <text x="36" y="248" class="s">“y is greedy under committed W” → poly constraints + lookups on the trace → linear claims on Enc(W) &amp; Enc(trace) → proximity opens.</text>
</svg>
<p class="cap">zkLLM’s tlookup / zkAttn are lookup-family gadgets. FlashProve’s ~2000 sumchecks mostly feed these linear claims.</p>
</div>'''


def svg_flashprove():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="FlashProve pipeline">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#mfp); }
  </style>
  <defs>
    <marker id="mfp" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="22" class="h">FlashProve = commit-and-prove IOP for MoE inference (worked example of §0c)</text>

  <rect x="24" y="40" width="160" height="90" rx="3" class="box"/>
  <text x="36" y="62" class="t">Offline</text>
  <text x="36" y="82" class="s">Enc(W) + Merkle</text>
  <text x="36" y="100" class="s">+ range / proximity</text>
  <text x="36" y="118" class="s">→ commitment ID</text>
  <path d="M184 85 L220 85" class="arr"/>

  <rect x="220" y="40" width="160" height="90" rx="3" class="box"/>
  <text x="232" y="62" class="t">Leaf tables</text>
  <text x="232" y="82" class="s">fresh masks of same W</text>
  <text x="232" y="100" class="s">+ link proofs</text>
  <text x="232" y="118" class="s">(query budget)</text>
  <path d="M380 85 L416 85" class="arr"/>

  <rect x="416" y="40" width="160" height="90" rx="3" class="box"/>
  <text x="428" y="62" class="t">Online batch</text>
  <text x="428" y="82" class="s">integer prefill</text>
  <text x="428" y="100" class="s">segment traces</text>
  <text x="428" y="118" class="s">sumcheck / lookup</text>
  <path d="M576 85 L612 85" class="arr"/>

  <rect x="612" y="40" width="84" height="90" rx="3" class="box"/>
  <text x="624" y="62" class="t">π</text>
  <text x="624" y="82" class="s">~19 MB</text>
  <text x="624" y="100" class="s">CPU verify</text>
  <text x="624" y="118" class="s">~17 s</text>

  <rect x="24" y="150" width="672" height="130" rx="3" class="box"/>
  <text x="36" y="172" class="t">Measured (Llama 4 Maverick 400B MoE, 4-bit, 1×H100)</text>
  <text x="36" y="194" class="s">~110 prefill tok/s prove (batch 24) · ~70–95× vLLM GPU-time · hides weights &amp; experts; architecture public</text>
  <text x="36" y="214" class="s">Statement: exact-match greedy of integer model, or clipped-gap policy (Token-DiFR family). Post-hoc, not inline.</text>
  <text x="36" y="234" class="s">Lean: soundness of Lean verifier; C++/CUDA tested, not proved equivalent. Side-channels / float serving out of scope.</text>
  <text x="36" y="254" class="s">Lineage: Plan B evaluate engine at frontier demo scale — peer of VerInf, much faster / smaller π on a related claim.</text>
</svg>
<p class="cap"><a href="https://www.anthropic.com/research/provable-inference">Anthropic · FlashProve</a> · <a href="https://github.com/anthropics/FlashProve">github.com/anthropics/FlashProve</a> · Nov 2026</p>
</div>'''


def svg_field_sz():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Finite field and Schwartz-Zippel">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Two tiny math facts everything else sits on</text>

  <rect x="24" y="40" width="336" height="150" rx="3" class="box"/>
  <text x="36" y="62" class="t">1 · Finite field 𝔽_p</text>
  <text x="36" y="84" class="s">Pick a big prime p. All + − × happen</text>
  <text x="36" y="102" class="s">“mod p” (clock arithmetic).</text>
  <text x="36" y="124" class="s">SNARK math only works here —</text>
  <text x="36" y="142" class="s">not in floating-point GPU numbers.</text>
  <text x="36" y="168" class="s">Keep values small so mod p ≈ integers.</text>

  <rect x="376" y="40" width="320" height="150" rx="3" class="box"/>
  <text x="388" y="62" class="t">2 · Schwartz–Zippel</text>
  <text x="388" y="84" class="s">A nonzero polynomial of degree d</text>
  <text x="388" y="102" class="s">is zero at a random point with</text>
  <text x="388" y="120" class="s">probability ≤ d / |𝔽|  (tiny).</text>
  <text x="388" y="142" class="s">So: check one random point ≈</text>
  <text x="388" y="168" class="s">check the whole polynomial.</text>

  <rect x="24" y="208" width="672" height="72" rx="3" class="box"/>
  <text x="36" y="230" class="t">Why you care</text>
  <text x="36" y="252" class="s">Sumcheck, batching many claims, “did the prover lie?” — almost all soundness bounds are just Schwartz–Zippel in a trench coat.</text>
</svg>
<p class="cap">If you only memorize two formulas from this whole primer: “mod p” and “random point catches a lying polynomial.”</p>
</div>'''


def svg_arithmetize():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Arithmetization">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#ma); }
  </style>
  <defs>
    <marker id="ma" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="22" class="h">Arithmetization = turn the model run into equations</text>

  <rect x="24" y="44" width="180" height="90" rx="3" class="box"/>
  <text x="36" y="68" class="t">GPU story</text>
  <text x="36" y="90" class="s">matmul, SiLU,</text>
  <text x="36" y="108" class="s">softmax, argmax…</text>
  <path d="M204 89 L240 89" class="arr"/>

  <rect x="240" y="44" width="200" height="90" rx="3" class="box"/>
  <text x="252" y="68" class="t">Equation story</text>
  <text x="252" y="90" class="s">c − a·b = 0</text>
  <text x="252" y="108" class="s">(u,v) ∈ public table</text>
  <path d="M440 89 L476 89" class="arr"/>

  <rect x="476" y="44" width="220" height="90" rx="3" class="box"/>
  <text x="488" y="68" class="t">Proof story</text>
  <text x="488" y="90" class="s">check those eqs</text>
  <text x="488" y="108" class="s">without seeing a,b,W</text>

  <rect x="24" y="156" width="672" height="84" rx="3" class="box"/>
  <text x="36" y="178" class="t">Concrete</text>
  <text x="36" y="200" class="s">Y = W X  →  many multiply-add equations. Softmax / SiLU → “this value is in a public lookup table.”</text>
  <text x="36" y="220" class="s">“Circuit” here means that pile of equations — not AND/OR gates from undergrad digital logic.</text>
</svg>
<p class="cap">No equations → nothing to sumcheck. This step is why proofs talk about an integer / quantized model, not raw BF16 CUDA.</p>
</div>'''


def svg_unique_list():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Unique vs list decoding">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Codewords: how wrong can a table be and still “mean” one message?</text>

  <rect x="24" y="40" width="336" height="130" rx="3" class="box"/>
  <text x="36" y="62" class="t">Unique decoding</text>
  <text x="36" y="84" class="s">If the sent row is close enough to</text>
  <text x="36" y="102" class="s">a codeword, only ONE message fits.</text>
  <text x="36" y="124" class="s">Safe but needs more checks / opens.</text>
  <text x="36" y="148" class="s">Slower proofs.</text>

  <rect x="376" y="40" width="320" height="130" rx="3" class="box"/>
  <text x="388" y="62" class="t">List decoding</text>
  <text x="388" y="84" class="s">Allow bigger errors → a short LIST</text>
  <text x="388" y="102" class="s">of nearby codewords might fit.</text>
  <text x="388" y="124" class="s">Fewer opens (faster), but you must</text>
  <text x="388" y="148" class="s">pin which message you meant.</text>

  <rect x="24" y="188" width="672" height="72" rx="3" class="box"/>
  <text x="36" y="210" class="t">Where this shows up</text>
  <text x="36" y="232" class="s">Hash-based systems (FlashProve §7) often use list-decoding + an out-of-domain (OOD) sample so the list collapses to one message.</text>
</svg>
<p class="cap">Proximity test = “are you close to some codeword?” OOD sample = “and we mean this one.”</p>
</div>'''


def svg_three_stacks():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Three ZK stacks in this deck">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Three crypto stacks this briefing actually uses</text>

  <rect x="24" y="40" width="220" height="170" rx="3" class="box"/>
  <text x="36" y="62" class="t">A · Hash / IOP</text>
  <text x="36" y="84" class="s">Reed–Solomon + mask</text>
  <text x="36" y="102" class="s">Merkle openings</text>
  <text x="36" y="120" class="s">sumcheck · lookups</text>
  <text x="36" y="138" class="s">Fiat–Shamir</text>
  <text x="36" y="164" class="t">§7 FlashProve</text>
  <text x="36" y="186" class="s">(§8 often same family)</text>

  <rect x="256" y="40" width="220" height="170" rx="3" class="box"/>
  <text x="268" y="62" class="t">B · Algebraic PCS</text>
  <text x="268" y="84" class="s">Elliptic-curve group</text>
  <text x="268" y="102" class="s">Hyrax / IPA-style</text>
  <text x="268" y="120" class="s">ProveEval at points</text>
  <text x="268" y="138" class="s">+ sumcheck / lookups</text>
  <text x="268" y="164" class="t">§6 zkLLM</text>
  <text x="268" y="186" class="s">Hyrax binds W → C</text>

  <rect x="488" y="40" width="208" height="170" rx="3" class="box"/>
  <text x="500" y="62" class="t">C · zkVM</text>
  <text x="500" y="84" class="s">Prove a program run</text>
  <text x="500" y="102" class="s">(CPU/GPU step as</text>
  <text x="500" y="120" class="s">bytecode), not a</text>
  <text x="500" y="138" class="s">hand-built ML circuit</text>
  <text x="500" y="164" class="t">§10 Peigné</text>
  <text x="500" y="186" class="s">training horizon</text>

  <rect x="24" y="228" width="672" height="54" rx="3" class="box"/>
  <text x="36" y="250" class="t">Shared floor</text>
  <text x="36" y="268" class="s">Fields · Schwartz–Zippel · arithmetization · Fiat–Shamir · “what statement?” — then pick stack A, B, or C.</text>
</svg>
<p class="cap">If you only learn stack A, zkLLM’s Hyrax and Peigné’s zkVM will feel like aliens. Learn the shared floor, then the branch.</p>
</div>'''


def svg_pcs_hyrax():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Polynomial commitment vs Merkle">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Two ways to commit to a secret polynomial / table</text>

  <rect x="24" y="40" width="336" height="150" rx="3" class="box"/>
  <text x="36" y="62" class="t">Hash / Merkle path (§7)</text>
  <text x="36" y="84" class="s">Encode → hash tree → root.</text>
  <text x="36" y="102" class="s">Open = reveal a few cells</text>
  <text x="36" y="120" class="s">+ Merkle paths.</text>
  <text x="36" y="142" class="s">Assumption: hash is random.</text>
  <text x="36" y="168" class="s">Proof size grows with opens.</text>

  <rect x="376" y="40" width="320" height="150" rx="3" class="box"/>
  <text x="388" y="62" class="t">Algebraic PCS / Hyrax (§6)</text>
  <text x="388" y="84" class="s">Bind the poly into a short</text>
  <text x="388" y="102" class="s">group element C (Pedersen-</text>
  <text x="388" y="120" class="s">style). Open = ProveEval:</text>
  <text x="388" y="142" class="s">“at random r, P(r)=y.”</text>
  <text x="388" y="168" class="s">Assumption: discrete log.</text>

  <rect x="24" y="208" width="672" height="54" rx="3" class="box"/>
  <text x="36" y="230" class="t">Same job, different crypto</text>
  <text x="36" y="248" class="s">Both answer “I committed to one secret; later check random algebraic claims about it.” Merkle ≠ Hyrax.</text>
</svg>
<p class="cap">zkLLM’s first slide is Hyrax. FlashProve’s first slide is Merkle+RS. Do not mash them into one box.</p>
</div>'''


def svg_statement_choice():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 290" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Choosing the public statement">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Crypto proves a statement — you still choose which claim</text>

  <rect x="24" y="40" width="220" height="150" rx="3" class="box"/>
  <text x="36" y="62" class="t">Exact circuit</text>
  <text x="36" y="84" class="s">“Integer model on x</text>
  <text x="36" y="102" class="s">outputs y / greedy</text>
  <text x="36" y="120" class="s">token.”</text>
  <text x="36" y="148" class="t">§6 zkLLM</text>
  <text x="36" y="170" class="s">tight · float-painful</text>

  <rect x="256" y="40" width="220" height="150" rx="3" class="box"/>
  <text x="268" y="62" class="t">Clipped-gap / TokenDiFR</text>
  <text x="268" y="84" class="s">“Top token within a</text>
  <text x="268" y="102" class="s">gap of the model’s</text>
  <text x="268" y="120" class="s">argmax.”</text>
  <text x="268" y="148" class="t">§7 FlashProve</text>
  <text x="268" y="170" class="s">policy slack</text>

  <rect x="488" y="40" width="208" height="150" rx="3" class="box"/>
  <text x="500" y="62" class="t">Unexplained Û</text>
  <text x="500" y="84" class="s">“Leftover info in</text>
  <text x="500" y="102" class="s">the tokens ≤ Û</text>
  <text x="500" y="120" class="s">bits/token.”</text>
  <text x="500" y="148" class="t">§8 VerInf</text>
  <text x="500" y="170" class="s">score, not equality</text>

  <rect x="24" y="208" width="672" height="64" rx="3" class="box"/>
  <text x="36" y="230" class="t">Not crypto, but next door</text>
  <text x="36" y="252" class="s">DiFR (§5 contrast) = statistical accept region for Plan A recompute when floats disagree. Same “slack” intuition as clipped-gap / Û, different engine.</text>
</svg>
<p class="cap">Wrong statement ⇒ sound crypto proving the wrong policy question. Pick the claim before you pick the SNARK.</p>
</div>'''


def svg_zkvm():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="zkVM idea">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
    .arr { stroke: #8a867a; fill: none; stroke-width: 1.2; marker-end: url(#mz); }
  </style>
  <defs>
    <marker id="mz" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#8a867a"/>
    </marker>
  </defs>
  <text x="24" y="22" class="h">zkVM = prove “this program ran,” not “this hand-built ML circuit”</text>

  <rect x="24" y="44" width="160" height="90" rx="3" class="box"/>
  <text x="36" y="68" class="t">Training step</text>
  <text x="36" y="90" class="s">BF16/FP32 ops,</text>
  <text x="36" y="108" class="s">optimizer, shards…</text>
  <path d="M184 89 L220 89" class="arr"/>

  <rect x="220" y="44" width="180" height="90" rx="3" class="box"/>
  <text x="232" y="68" class="t">Guest program</text>
  <text x="232" y="90" class="s">runs inside a VM</text>
  <text x="232" y="108" class="s">(bytecode trace)</text>
  <path d="M400 89 L436 89" class="arr"/>

  <rect x="436" y="44" width="260" height="90" rx="3" class="box"/>
  <text x="448" y="68" class="t">SNARK over the trace</text>
  <text x="448" y="90" class="s">(+ recursion / folding</text>
  <text x="448" y="108" class="s">so steps stay short)</text>

  <rect x="24" y="156" width="672" height="94" rx="3" class="box"/>
  <text x="36" y="178" class="t">Why Peigné talks this way</text>
  <text x="36" y="200" class="s">Hand-arithmetizing every frontier training kernel is hopeless. A zkVM lets you write (or compile) the step as a program</text>
  <text x="36" y="220" class="s">and prove execution. Hard part moves to float fidelity + proving cost — still a research horizon, not a product.</text>
</svg>
<p class="cap">Same completeness/soundness/ZK wish-list. Different packaging: program trace instead of a bespoke attention circuit.</p>
</div>'''


def svg_mle_batch():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Multilinear extension and batching">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Two bookkeeping tricks used constantly</text>

  <rect x="24" y="40" width="336" height="140" rx="3" class="box"/>
  <text x="36" y="62" class="t">Multilinear extension</text>
  <text x="36" y="84" class="s">A table on corners {0,1}ⁿ becomes</text>
  <text x="36" y="102" class="s">ONE polynomial that matches the</text>
  <text x="36" y="120" class="s">table on those corners, and is</text>
  <text x="36" y="138" class="s">degree ≤ 1 in each variable.</text>
  <text x="36" y="160" class="s">Sumcheck often sums that polynomial.</text>

  <rect x="376" y="40" width="320" height="140" rx="3" class="box"/>
  <text x="388" y="62" class="t">Random batching</text>
  <text x="388" y="84" class="s">Many claims C₁…Cₖ true?</text>
  <text x="388" y="102" class="s">Pick random r; check</text>
  <text x="388" y="120" class="s">C₁ + r C₂ + r² C₃ + … = 0.</text>
  <text x="388" y="142" class="s">If any Cᵢ is false, the combo is a</text>
  <text x="388" y="160" class="s">nonzero poly → random r catches it.</text>

  <rect x="24" y="198" width="672" height="62" rx="3" class="box"/>
  <text x="36" y="220" class="t">Again: Schwartz–Zippel</text>
  <text x="36" y="242" class="s">Batching is not a new idea — it’s “one random point checks many equations at once.”</text>
</svg>
<p class="cap">When a paper says “we fold claims with a random challenge,” this is what they mean.</p>
</div>'''


def svg_proof_vs_arg():
    return '''
<div class="svg-fig">
<svg viewBox="0 0 720 260" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Proof vs argument and ROM">
  <style>
    .t { font: 600 11.5px ui-monospace, monospace; fill: #1a1a18; }
    .s { font: 10px ui-monospace, monospace; fill: #55524a; }
    .h { font: 600 11px ui-monospace, monospace; fill: #9a5b12; }
    .box { fill: #f3f0ea; stroke: rgba(26,26,24,0.18); }
  </style>
  <text x="24" y="22" class="h">Words people mix up</text>

  <rect x="24" y="40" width="220" height="120" rx="3" class="box"/>
  <text x="36" y="62" class="t">Proof (info-theoretic)</text>
  <text x="36" y="84" class="s">Even infinite compute</text>
  <text x="36" y="102" class="s">can’t fake it (except</text>
  <text x="36" y="120" class="s">tiny random chance).</text>
  <text x="36" y="144" class="s">IOP layer feels like this.</text>

  <rect x="256" y="40" width="220" height="120" rx="3" class="box"/>
  <text x="268" y="62" class="t">Argument</text>
  <text x="268" y="84" class="s">A cheater with a huge</text>
  <text x="268" y="102" class="s">computer who can break</text>
  <text x="268" y="120" class="s">the hash might fake it.</text>
  <text x="268" y="144" class="s">Merkle / SNARK layer.</text>

  <rect x="488" y="40" width="208" height="120" rx="3" class="box"/>
  <text x="500" y="62" class="t">Random oracle</text>
  <text x="500" y="84" class="s">Pretend hash H is a</text>
  <text x="500" y="102" class="s">perfect random function.</text>
  <text x="500" y="120" class="s">Theorems assume that;</text>
  <text x="500" y="144" class="s">BLAKE2 is the stand-in.</text>

  <rect x="24" y="180" width="672" height="60" rx="3" class="box"/>
  <text x="36" y="202" class="t">Practical English</text>
  <text x="36" y="224" class="s">FlashProve is an argument in the random-oracle model: “fake a proof” ≈ “break BLAKE2 / get absurdly lucky.”</text>
</svg>
<p class="cap">Lean theorems are about this idealized world. Real BLAKE2 is a belief, not a proof.</p>
</div>'''
