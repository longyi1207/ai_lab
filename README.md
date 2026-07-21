# ai_lab

Hands-on AI/ML systems learning projects — each subdirectory is self-contained (own README,
own dependencies, own venv). Real code, run and verified where the hardware allows, honestly
reported (including bugs found and negative results) where it doesn't.

## Projects

### [`dist_training_lab/`](dist_training_lab/) — distributed training & ML infrastructure

A hands-on curriculum covering the distributed-training and ML-infra skills frontier AI labs'
research-infrastructure / ML-platform-engineering roles screen for: DDP, FSDP2, tensor/pipeline/
expert parallelism, FP8 quantization, and fault tolerance — implemented from scratch and
numerically verified against single-device references wherever possible, entirely on a laptop
(no cloud spend required for correctness, only for real multi-GPU speed/memory numbers).

See [`dist_training_lab/README.md`](dist_training_lab/README.md) for the full phase-by-phase
writeup, including real bugs found (a macOS-specific FSDP2 device-mesh crash, a gloo backend
limitation with ragged `all_to_all`, an undocumented non-1.0 gradient through a naive FP8 cast)
and honest negative results (naive vs block-wise FP8 quantization barely differed in a toy
training run, which turned out to be more informative than a clean confirmation would have been).

### [`transformer_lab/`](transformer_lab/) — transformer training & interpretability basics

Small, readable scripts for training, inference, and interpretability: causal self-attention
from scratch, KV-cache speedup measurement, and a logit-lens walk through a real GPT-2's layers.
See [`transformer_lab/README.md`](transformer_lab/README.md).

## License

MIT — see [LICENSE](LICENSE).
