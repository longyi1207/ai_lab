#!/usr/bin/env bash
# Quick smoke test for transformer_lab (M4-friendly).
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
fi

echo "==> install deps"
"$PYTHON" -m pip install -q -r requirements.txt

echo "==> train tiny MiniGPT"
"$PYTHON" train_tiny.py --steps 200

echo "==> training vs inference demo"
"$PYTHON" infer_demo.py --new-tokens 6

echo "==> KV cache timing (HF GPT-2)"
"$PYTHON" kv_cache_demo.py --new-tokens 16

if "$PYTHON" -c "import transformer_lens" 2>/dev/null; then
  echo "==> logit lens (TransformerLens)"
  "$PYTHON" logit_lens_demo.py
else
  echo "==> skip logit_lens_demo (pip install transformer-lens to enable)"
fi

echo "Done. Outputs in outputs/"
