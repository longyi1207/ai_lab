#!/usr/bin/env bash
# Run the whole pipeline on the pilot config, one stage at a time, stopping on the first error.
#
#   SSE_ROOT=/path/to/score-seeking-eval RL_PIPELINE_ENV_FILE=/path/to/.env scripts/run_pilot.sh
#
# Every stage is resumable, so rerunning this script after an interruption continues where it
# stopped. The fine-tuning stage waits for the Azure job (usually tens of minutes to a few hours).
set -euo pipefail
cd "$(dirname "$0")/.."

CONFIG="${CONFIG:-configs/pilot.yaml}"
PY="${PY:-.venv/bin/python}"
run() { echo; echo "=== $* ==="; "$PY" -m rl_pipeline "$@" --config "$CONFIG"; }

run import
run select
run replay
run sample
run pairs
run finetune
run deploy
run evaluate
run teardown
run report
echo; echo "Done. See outputs/$(grep '^run_name:' "$CONFIG" | awk '{print $2}')/REPORT.md"
