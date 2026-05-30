# transformer_lab

Hands-on scripts for **training**, **inference**, and **interpretability** — companion to `notes/transformer_interview_visual.md` and `notes/transformer_hands_on_learning.md`.

## Quick start

```bash
cd code/transformer_lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash run_all.sh
```

Or step by step:

| Script | What you learn | Time (M4) |
|--------|----------------|-----------|
| `train_tiny.py` | Parallel training, causal mask, teacher forcing | ~1 min |
| `infer_demo.py` | Serial inference vs one-shot training forward | ~5 sec |
| `kv_cache_demo.py` | HF GPT-2 with/without KV cache timing | ~30 sec |
| `logit_lens_demo.py` | Layer-wise predictions (TransformerLens) | ~1 min |

Optional interpretability dependency:

```bash
pip install transformer-lens
python logit_lens_demo.py
```

## Files

```
minimal_gpt.py      # ~150 lines: causal MHA + pre-norm GPT + generate()
train_tiny.py       # char-level train on data/tiny_corpus.txt
infer_demo.py       # prints training vs inference side-by-side
kv_cache_demo.py    # measures cache speedup on real GPT-2
logit_lens_demo.py  # residual → unembed per layer
outputs/            # checkpoints + figures (gitignored patterns ok)
```

## Concept map

```
train_tiny.py     →  notes/transformer_interview_visual.md §6 Training
infer_demo.py     →  §6 Inference (serial steps)
kv_cache_demo.py  →  §8 KV cache
logit_lens_demo.py → hook into openllama_playground / emotion_vectors path
```

## Next steps

- Scale up: [nanoGPT](https://github.com/karpathy/nanoGPT) Shakespeare, then [nanochat](https://github.com/karpathy/nanochat) on cloud
- Deep MI: `../openllama_playground/`, `../emotion_vectors/`, [ARENA](https://www.arena.education/)
