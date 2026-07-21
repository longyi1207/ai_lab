"""Turns a train.py JSONL log into a self-contained HTML dashboard: loss (train/eval),
grad norm, LR schedule, throughput. This is a minimal, from-scratch version of what
Weights & Biases / TensorBoard do automatically at scale — see README Phase 1 log for the
discussion of what's different when this gets productionized.

Usage: .venv/bin/python scripts/make_dashboard.py logs/<run_name>.jsonl > dashboard.html
"""

import json
import sys
from pathlib import Path


def load_log(path: str) -> dict:
    train_steps, train_loss, grad_norm, lr, tok_s = [], [], [], [], []
    eval_steps, eval_train, eval_val = [], [], []
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            if "train_loss" in d:
                train_steps.append(d["step"])
                train_loss.append(round(d["train_loss"], 4))
                grad_norm.append(round(d["grad_norm"], 4))
                lr.append(d["lr"])
                tok_s.append(round(d["tokens_per_sec"]))
            if "eval_val_loss" in d:
                eval_steps.append(d["step"])
                eval_train.append(round(d["eval_train_loss"], 4))
                eval_val.append(round(d["eval_val_loss"], 4))
    return {
        "train_steps": train_steps, "train_loss": train_loss, "grad_norm": grad_norm,
        "lr": lr, "tok_s": tok_s,
        "eval_steps": eval_steps, "eval_train": eval_train, "eval_val": eval_val,
    }


TEMPLATE = """<!doctype html>
<title>__TITLE__</title>
<style>
.viz-root {
  color-scheme: light;
  --surface-1: #fcfcfb; --page: #f9f9f7;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #008300; --series-3: #e87ba4;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --surface-1: #1a1a19; --page: #0d0d0d;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #008300; --series-3: #d55181;
  }
}
:root[data-theme="dark"] .viz-root {
  color-scheme: dark;
  --surface-1: #1a1a19; --page: #0d0d0d;
  --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --series-1: #3987e5; --series-2: #008300; --series-3: #d55181;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.viz-root { padding: 24px; max-width: 1100px; margin: 0 auto; }
h1 { font-size: 18px; color: var(--text-primary); margin: 0 0 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; margin: 0 0 20px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px; overflow-x: auto; }
.panel.wide { grid-column: 1 / -1; }
.panel h2 { font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 0 0 2px; }
.panel .note { font-size: 12px; color: var(--text-secondary); margin: 0 0 10px; }
svg { display: block; overflow: visible; }
.gridline { stroke: var(--grid); stroke-width: 1; }
.axis-line { stroke: var(--axis); stroke-width: 1; }
.axis-label { fill: var(--text-muted); font-size: 11px; }
.line { fill: none; stroke-width: 2; stroke-linecap: round; }
.marker { stroke-width: 2; }
.annotation-line { stroke: var(--text-muted); stroke-width: 1; stroke-dasharray: 3 3; }
.annotation-label { fill: var(--text-secondary); font-size: 11px; }
.legend { display: flex; gap: 16px; margin-bottom: 10px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.crosshair { stroke: var(--axis); stroke-width: 1; pointer-events: none; opacity: 0; }
.tooltip { position: absolute; background: var(--surface-1); border: 1px solid var(--border); border-radius: 6px;
  padding: 8px 10px; font-size: 12px; color: var(--text-primary); pointer-events: none; opacity: 0;
  box-shadow: 0 4px 12px var(--border); white-space: nowrap; z-index: 10; }
.tooltip .row { display: flex; justify-content: space-between; gap: 12px; }
.tooltip .row .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
.tooltip .step { color: var(--text-muted); margin-bottom: 4px; }
table.data-table { border-collapse: collapse; font-size: 12px; margin-top: 12px; width: 100%; }
table.data-table th, table.data-table td { text-align: right; padding: 4px 10px; border-bottom: 1px solid var(--grid); font-variant-numeric: tabular-nums; }
table.data-table th:first-child, table.data-table td:first-child { text-align: left; }
table.data-table th { color: var(--text-muted); font-weight: 500; }
td.highlight { color: var(--series-3); font-weight: 600; }
details summary { cursor: pointer; font-size: 12px; color: var(--text-secondary); margin-top: 10px; }
</style>
<div class="viz-root">
  <h1>__TITLE__</h1>
  <p class="subtitle">__SUBTITLE__</p>
  <div class="grid">
    <div class="panel wide" id="panel-loss"></div>
    <div class="panel" id="panel-lr"></div>
    <div class="panel" id="panel-gradnorm"></div>
    <div class="panel wide" id="panel-tokspersec"></div>
  </div>
</div>
<div class="tooltip" id="tooltip"></div>
<script>
const DATA = __DATA_JSON__;

function els(tag, attrs, parent) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(el);
  return el;
}

function niceTicks(min, max, n) {
  const span = max - min || 1;
  const step = span / n;
  const ticks = [];
  for (let i = 0; i <= n; i++) ticks.push(min + step * i);
  return ticks;
}

function lineChart(containerId, opts) {
  const container = document.getElementById(containerId);
  const W = container.clientWidth || 1000, H = opts.height || 220;
  const padL = 46, padR = 12, padT = 10, padB = 24;
  const plotW = W - padL - padR, plotH = H - padT - padB;

  const allX = opts.series.flatMap(s => s.x);
  const allY = opts.series.flatMap(s => s.y);
  const xMin = Math.min(...allX), xMax = Math.max(...allX);
  let yMin = opts.yMin !== undefined ? opts.yMin : Math.min(...allY);
  let yMax = opts.yMax !== undefined ? opts.yMax : Math.max(...allY);
  if (opts.log) { yMin = Math.log10(Math.max(yMin, 1e-9)); yMax = Math.log10(yMax); }
  const yPad = (yMax - yMin) * 0.08 || 1;
  yMin -= yPad; yMax += yPad;

  const sx = x => padL + ((x - xMin) / (xMax - xMin || 1)) * plotW;
  const sy = y => {
    const v = opts.log ? Math.log10(Math.max(y, 1e-9)) : y;
    return padT + plotH - ((v - yMin) / (yMax - yMin || 1)) * plotH;
  };

  if (opts.title) {
    const h = document.createElement('h2'); h.textContent = opts.title; container.appendChild(h);
  }
  if (opts.note) {
    const p = document.createElement('p'); p.className = 'note'; p.textContent = opts.note; container.appendChild(p);
  }
  if (opts.series.length > 1) {
    const legend = document.createElement('div'); legend.className = 'legend';
    opts.series.forEach(s => {
      const item = document.createElement('div'); item.className = 'legend-item';
      item.innerHTML = `<span class="legend-dot" style="background:${s.color}"></span>${s.label}`;
      legend.appendChild(item);
    });
    container.appendChild(legend);
  }

  const svg = els('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` }, container);

  const yTicks = niceTicks(yMin + yPad, yMax - yPad, 4);
  yTicks.forEach(t => {
    const y = sy(opts.log ? Math.pow(10, t) : t);
    els('line', { x1: padL, x2: W - padR, y1: y, y2: y, class: 'gridline' }, svg);
    const label = opts.log ? Math.pow(10, t).toFixed(t < 0 ? 2 : 0) : (opts.yFmt ? opts.yFmt(t) : t.toFixed(2));
    els('text', { x: padL - 8, y: y + 3, class: 'axis-label', 'text-anchor': 'end' }, svg).textContent = label;
  });
  els('line', { x1: padL, x2: padL, y1: padT, y2: H - padB, class: 'axis-line' }, svg);
  els('line', { x1: padL, x2: W - padR, y1: H - padB, y2: H - padB, class: 'axis-line' }, svg);
  const xTicks = niceTicks(xMin, xMax, 4);
  xTicks.forEach(t => {
    els('text', { x: sx(t), y: H - padB + 16, class: 'axis-label', 'text-anchor': 'middle' }, svg).textContent = Math.round(t);
  });

  opts.series.forEach(s => {
    const d = s.x.map((x, i) => `${i === 0 ? 'M' : 'L'} ${sx(x).toFixed(1)} ${sy(s.y[i]).toFixed(1)}`).join(' ');
    els('path', { d, class: 'line', stroke: s.color, opacity: s.thin ? 0.55 : 1 }, svg);
    if (s.markers) {
      s.x.forEach((x, i) => {
        els('circle', { cx: sx(x), cy: sy(s.y[i]), r: 4, fill: opts.bg || 'var(--surface-1)', stroke: s.color, class: 'marker' }, svg);
      });
    }
  });

  if (opts.annotations) {
    opts.annotations.forEach(a => {
      const x = sx(a.x);
      els('line', { x1: x, x2: x, y1: padT, y2: H - padB, class: 'annotation-line' }, svg);
      els('text', { x: x + 5, y: padT + 12, class: 'annotation-label' }, svg).textContent = a.label;
    });
  }

  // hover crosshair + tooltip
  const crosshair = els('line', { x1: 0, x2: 0, y1: padT, y2: H - padB, class: 'crosshair' }, svg);
  const hitRect = els('rect', { x: padL, y: padT, width: plotW, height: plotH, fill: 'transparent' }, svg);
  const tooltip = document.getElementById('tooltip');
  hitRect.addEventListener('mousemove', (ev) => {
    const rect = svg.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const xVal = xMin + ((mx - padL) / plotW) * (xMax - xMin);
    let best = opts.series[0], bestIdx = 0, bestDist = Infinity;
    opts.series[0].x.forEach((x, i) => { const d = Math.abs(x - xVal); if (d < bestDist) { bestDist = d; bestIdx = i; } });
    const step = opts.series[0].x[bestIdx];
    crosshair.setAttribute('x1', sx(step)); crosshair.setAttribute('x2', sx(step)); crosshair.style.opacity = 1;
    let html = `<div class="step">step ${step}</div>`;
    opts.series.forEach(s => {
      const idx = s.x.indexOf(step) !== -1 ? s.x.indexOf(step) : bestIdx;
      const val = s.y[Math.min(idx, s.y.length - 1)];
      html += `<div class="row"><span><span class="dot" style="background:${s.color}"></span>${s.label}</span><span>${val.toFixed(opts.tooltipDecimals || 3)}</span></div>`;
    });
    tooltip.innerHTML = html;
    tooltip.style.opacity = 1;
    tooltip.style.left = (ev.clientX + 14) + 'px';
    tooltip.style.top = (ev.clientY - 10) + 'px';
  });
  hitRect.addEventListener('mouseleave', () => { crosshair.style.opacity = 0; tooltip.style.opacity = 0; });
}

lineChart('panel-loss', {
  title: 'Loss — raw train (noisy, per-step) vs eval train/val (averaged over 50 batches)',
  note: 'Val loss bottoms around step 500 then climbs — classic overfitting on a tiny (304K-token) corpus.',
  height: 260,
  log: true,
  tooltipDecimals: 3,
  series: [
    { label: 'train loss (raw)', color: 'var(--series-1)', x: DATA.train_steps, y: DATA.train_loss, thin: true },
    { label: 'eval train loss', color: 'var(--series-2)', x: DATA.eval_steps, y: DATA.eval_train, markers: true },
    { label: 'eval val loss', color: 'var(--series-3)', x: DATA.eval_steps, y: DATA.eval_val, markers: true },
  ],
  annotations: [ { x: 500, label: 'val loss minimum (step 500)' } ],
});

lineChart('panel-lr', {
  title: 'Learning rate schedule',
  note: 'Linear warmup (200 steps) then cosine decay to min_lr.',
  height: 200,
  tooltipDecimals: 6,
  series: [ { label: 'lr', color: 'var(--series-1)', x: DATA.train_steps, y: DATA.lr } ],
});

lineChart('panel-gradnorm', {
  title: 'Gradient norm (pre-clip)',
  note: 'Settles once past warmup — no instability.',
  height: 200,
  tooltipDecimals: 3,
  series: [ { label: 'grad norm', color: 'var(--series-1)', x: DATA.train_steps, y: DATA.grad_norm } ],
});

lineChart('panel-tokspersec', {
  title: 'Throughput (tokens/sec)',
  note: 'Periodic dips coincide with eval passes stealing compute — expected, not a regression.',
  height: 180,
  yFmt: v => (v/1000).toFixed(0) + 'k',
  tooltipDecimals: 0,
  series: [ { label: 'tok/s', color: 'var(--series-1)', x: DATA.train_steps, y: DATA.tok_s } ],
});
</script>
"""


def main():
    if len(sys.argv) < 2:
        print("usage: make_dashboard.py <path-to-jsonl>", file=sys.stderr)
        sys.exit(1)
    log_path = sys.argv[1]
    data = load_log(log_path)
    run_name = Path(log_path).stem
    html = (TEMPLATE
            .replace("__TITLE__", f"dist_training_lab — {run_name}")
            .replace("__SUBTITLE__", f"Phase 1 training dashboard, generated from {log_path}")
            .replace("__DATA_JSON__", json.dumps(data)))
    print(html)


if __name__ == "__main__":
    main()
