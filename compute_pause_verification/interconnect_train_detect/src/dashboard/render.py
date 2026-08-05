"""Self-contained HTML dashboard from report.json (+ optional trace)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..util import ROOT, setup_logging

log = setup_logging("dashboard")


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>ICTD — {title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  :root {{
    --bg: #0f1419; --panel: #1a222c; --text: #e7ecf1; --muted: #8b9aab;
    --ok: #3dd68c; --bad: #f07178; --accent: #59c2ff; --line: #2a3542;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
    background: var(--bg); color: var(--text);
  }}
  header {{
    padding: 1.5rem 2rem; border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, #15202b, var(--bg));
  }}
  header h1 {{ margin: 0 0 .35rem; font-size: 1.45rem; letter-spacing: .02em; }}
  header .sub {{ color: var(--muted); font-size: .95rem; }}
  .verdict {{
    display: inline-block; margin-top: .75rem; padding: .35rem .7rem;
    border-radius: 4px; font-weight: 600; font-size: .9rem;
  }}
  .verdict.ok {{ background: #143d2a; color: var(--ok); }}
  .verdict.bad {{ background: #3d181c; color: var(--bad); }}
  .verdict.unk {{ background: #2a3038; color: var(--muted); }}
  main {{ padding: 1.25rem 2rem 3rem; display: grid; gap: 1.25rem;
    grid-template-columns: 1fr 1fr; }}
  .panel {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
    padding: 1rem 1.1rem;
  }}
  .panel.wide {{ grid-column: 1 / -1; }}
  h2 {{ margin: 0 0 .75rem; font-size: 1.05rem; color: var(--accent); }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th, td {{ text-align: left; padding: .4rem .5rem; border-bottom: 1px solid var(--line); }}
  th {{ color: var(--muted); font-weight: 500; }}
  .mono {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .85rem; }}
  @media (max-width: 960px) {{ main {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>Interconnect train × infer detection</h1>
  <div class="sub">{title} · threshold {threshold} Gbps · n_windows={n_windows}</div>
  <div class="verdict {verdict_class}">{verdict_text}</div>
</header>
<main>
  <div class="panel wide"><h2>GB/s by label</h2><div id="box"></div></div>
  <div class="panel"><h2>Welch t / Cohen d</h2><div id="stats_table"></div></div>
  <div class="panel"><h2>Threshold detections</h2><div id="det_table"></div></div>
  <div class="panel wide"><h2>Per-window GB/s</h2><div id="bars"></div></div>
</main>
<script>
const REPORT = {report_json};
const samples = REPORT.samples_gbps || {{}};
const labels = Object.keys(samples);
const colors = {{train:'#f07178', infer:'#3dd68c', diloco:'#ffcc66', train_disguised:'#c792ea', other:'#8b9aab'}};

const boxTraces = labels.map(l => ({{
  y: samples[l], type:'box', name:l, marker:{{color: colors[l]||'#59c2ff'}}, boxpoints:'all', jitter:.3
}}));
Plotly.newPlot('box', boxTraces, {{
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color:'#e7ecf1'}}, margin:{{t:20,r:20,b:40,l:50}},
  yaxis:{{title:'GB/s', gridcolor:'#2a3542'}}, showlegend:true
}}, {{responsive:true}});

const feats = REPORT.features || [];
Plotly.newPlot('bars', [{{
  x: feats.map(f => f.name),
  y: feats.map(f => f.gbps_mean),
  type:'bar',
  marker:{{color: feats.map(f => colors[f.label]||'#59c2ff')}},
}}], {{
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color:'#e7ecf1'}}, margin:{{t:20,r:20,b:80,l:50}},
  yaxis:{{title:'GB/s', gridcolor:'#2a3542'}}, xaxis:{{tickangle:-30}}
}}, {{responsive:true}});

function tbl(headers, rows) {{
  let h = '<table><thead><tr>' + headers.map(x=>'<th>'+x+'</th>').join('') + '</tr></thead><tbody>';
  for (const r of rows) h += '<tr>' + r.map(c=>'<td class="mono">'+c+'</td>').join('') + '</tr>';
  return h + '</tbody></table>';
}}

const comps = (REPORT.stats && REPORT.stats.comparisons) || [];
document.getElementById('stats_table').innerHTML = comps.length ? tbl(
  ['pair','n','Δmean','d','g','t','df','p','CI95 Δ','CI95 d','sep?'],
  comps.map(c => [
    c.name_a+' vs '+c.name_b,
    c.n_a+'/'+c.n_b,
    c.mean_diff.toFixed(4),
    c.cohens_d.toFixed(3),
    c.hedges_g.toFixed(3),
    c.t_stat.toFixed(3),
    c.df.toFixed(1),
    c.p_value < 1e-4 ? c.p_value.toExponential(2) : c.p_value.toFixed(4),
    '['+c.ci95_diff[0].toFixed(3)+','+c.ci95_diff[1].toFixed(3)+']',
    '['+c.ci95_d[0].toFixed(2)+','+c.ci95_d[1].toFixed(2)+']',
    c.separable ? 'YES' : 'no'
  ])
) : '<p style="color:#8b9aab">Need ≥2 replicate windows per label. Run <span class="mono">run_replicates</span>.</p>';

const dets = REPORT.detections || [];
document.getElementById('det_table').innerHTML = tbl(
  ['name','label','pred','gbps'],
  dets.map(d => [d.name, d.label, d.predicted, Number(d.gbps_mean).toFixed(4)])
);
</script>
</body>
</html>
"""


def render_dashboard(report: dict[str, Any], out_html: str | Path, title: str | None = None) -> Path:
    out = Path(out_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    v = report.get("verdict") or {}
    sep = v.get("separable")
    if sep is True:
        vclass, vtext = "ok", "SEPARABLE — train GB/s ≫ infer (p & d thresholds met)"
    elif sep is False:
        vclass, vtext = "bad", "NOT SEPARABLE — threshold/stats failed H1"
    else:
        vclass, vtext = "unk", str(v.get("note") or "insufficient replicates for t/d")

    html = TEMPLATE.format(
        title=title or report.get("trace") or "report",
        threshold=report.get("threshold_gbps", "?"),
        n_windows=report.get("n_windows", len(report.get("features") or [])),
        verdict_class=vclass,
        verdict_text=vtext,
        report_json=json.dumps(report),
    )
    out.write_text(html)
    log.info("dashboard → %s", out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()
    report = json.loads(Path(args.report).read_text())
    out = args.out or str(Path(args.report).with_name("dashboard.html"))
    render_dashboard(report, out, args.title)


if __name__ == "__main__":
    main()
