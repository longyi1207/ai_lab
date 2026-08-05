#!/usr/bin/env bash
# Build a demo merged report + dashboard from synthetic samples (no GPU).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
.venv/bin/python <<'PY'
import json
from pathlib import Path
import numpy as np
from src.detect.stats import pairwise_by_label
from src.detect.threshold import Detection, score_report
from src.dashboard.render import render_dashboard
from src.util import ensure_dir, write_json

rng = np.random.default_rng(0)
train = list(rng.normal(12.0, 1.5, size=10))   # Gbps-ish
infer = list(rng.normal(0.8, 0.2, size=10))
diloco = list(rng.normal(1.2, 0.3, size=10))
comps = pairwise_by_label(
    {"train": train, "infer": infer, "diloco": diloco},
    n_boot=1000,
)
dets = []
for i, x in enumerate(train):
    dets.append(Detection(f"train_{i}", "train", "training" if x>=5 else "not_training", x, 5.0, x>=5))
for i, x in enumerate(infer):
    dets.append(Detection(f"infer_{i}", "infer", "training" if x>=5 else "not_training", x, 5.0, x>=5))
report = score_report(dets)
report["n_windows"] = len(dets)
report["threshold_gbps"] = 5.0
report["samples_gbps"] = {"train": train, "infer": infer, "diloco": diloco}
report["features"] = [
    {"name": d.name, "label": d.label, "gbps_mean": d.gbps_mean, "t0": 0, "t1": 1,
     "duration_s": 1, "bytes_total": 0, "gbps_p95": d.gbps_mean, "sample_hz": 1,
     "source": "demo", "n_samples": 1}
    for d in dets
]
primary = next(c for c in comps if c.name_a=="train" and c.name_b=="infer").to_dict()
report["stats"] = {"alpha": 0.05, "d_min": 0.8, "comparisons": [c.to_dict() for c in comps]}
report["verdict"] = {
    "train_vs_infer": primary,
    "separable": primary["separable"] and primary["mean_diff"] > 0,
    "note": "SEPARABLE" if primary["separable"] else "NOT",
}
out = ensure_dir(Path("dashboard/demo"))
write_json(out / "report.json", report)
render_dashboard(report, out / "dashboard.html", title="demo synthetic AWS-scale rates")
print("wrote", out / "dashboard.html")
print("separable", report["verdict"]["separable"], "d=", primary["cohens_d"], "p=", primary["p_value"])
PY
