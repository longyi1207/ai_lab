# Interconnect train-vs-infer detection

Seferis & Fist–style detector: can **cross-node communication size/shape** separate benign LLM pretraining from inference?

## Status

Production scaffold for **AWS CUDA** (2×8 GPU) + local smoke. P0–P2 complete offline; real GPU burn waits on budget.

## Hypothesis + stats gate

H1: mean cross-node GB/s(train) > infer under benign configs.

**Separable** iff Welch \(p < \alpha\) ∧ \(|d| \ge d_{\min}\) ∧ \(\Delta\mu > 0\) (defaults 0.05 / 0.8), with auto-calibrated threshold (Youden/midpoint/quantile).

## Layout

```
src/
  monitor/     probes: ib | nccl | proc_net | nvml | synthetic + nccl_hook
  workloads/   train_ddp, infer_dp, infer_tp (column-parallel), diloco (Nesterov outer), kv_disguise
  detect/      features (rate/FFT/burst), calibrate, stats, power, threshold, evaluate
  dashboard/   Plotly HTML
  run_experiment.py | run_replicates.py | run_grid.py | run_cluster.py
infra/
  terraform/   VPC, SG, cluster PG, 2×GPU, EFA auto by family, IAM minimal, Budgets alert
  scripts/     launch/bootstrap/sync/run_remote/pull/destroy/cost/autodestroy/spot_watch/…
configs/       smoke | grid_small | aws_g5 | aws_p4d
```

## Local (no AWS)

```bash
cd code/interconnect_train_detect
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

./scripts/smoke.sh
python -m src.run_replicates --config configs/smoke.yaml --reps 5
python -m src.run_grid --config configs/grid_small.yaml --steps 15
python -m src.detect.power --d 0.8 --power 0.8 --cluster-hourly 32.6
./scripts/demo_dashboard.sh
```

## AWS (when budget ready)

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars  # edit
cp infra/scripts/config.env.example infra/scripts/config.env

./infra/scripts/launch.sh
./infra/scripts/autodestroy.sh 4          # HARD: destroy after 4h
./infra/scripts/bootstrap.sh && ./infra/scripts/sync.sh
./infra/scripts/run_remote.sh configs/aws_g5.yaml
./infra/scripts/pull.sh
./infra/scripts/cost.sh                   # live Pricing API when creds allow
./infra/scripts/destroy.sh
```

- **g5.48xlarge**: software path; `efa_extra_nics` auto=0  
- **p4d.24xlarge**: interconnect-realistic; auto `efa_extra_nics=3`  
- Spot: `use_spot=true` + `spot_watch.sh` on each node  

## CI

Repo workflow: `.github/workflows/ictd.yml` — pytest + terraform fmt/validate.

## References

- Seferis & Fist, AAAI 2026 — doi:10.1609/aaai.v40i44.41127  
- DiLoCo — arXiv:2311.08105  
- Rahman & Tajdari — arXiv:2606.19262  
