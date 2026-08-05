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
