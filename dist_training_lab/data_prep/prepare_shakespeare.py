"""Phase 1 dataset prep: tiny-Shakespeare, GPT-2 BPE tokenized, memmap'd to disk.

Mirrors nanoGPT's data/shakespeare_char prep but with real GPT-2 BPE (tiktoken) instead of
char-level tokens, since Phase 2+ configs assume a real vocab size (50257).

Run: .venv/bin/python data_prep/prepare_shakespeare.py
Produces: data/shakespeare/train.bin, data/shakespeare/val.bin, data/shakespeare/meta.json
"""

import json
import logging
import urllib.request
from pathlib import Path

import numpy as np
import tiktoken

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_URL = "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "shakespeare"
VAL_FRACTION = 0.1


def download_raw_text() -> str:
    raw_path = OUT_DIR / "input.txt"
    if raw_path.exists():
        log.info("Found cached raw text at %s", raw_path)
        return raw_path.read_text()

    log.info("Downloading tiny-Shakespeare from %s", DATA_URL)
    with urllib.request.urlopen(DATA_URL, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text)
    log.info("Cached %d chars to %s", len(text), raw_path)
    return text


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = download_raw_text()

    enc = tiktoken.get_encoding("gpt2")
    ids = enc.encode_ordinary(text)
    log.info("Encoded %d chars -> %d tokens (compression ratio %.2fx)", len(text), len(ids), len(text) / len(ids))

    split_idx = int(len(ids) * (1 - VAL_FRACTION))
    train_ids = np.array(ids[:split_idx], dtype=np.uint16)
    val_ids = np.array(ids[split_idx:], dtype=np.uint16)

    train_ids.tofile(OUT_DIR / "train.bin")
    val_ids.tofile(OUT_DIR / "val.bin")
    log.info("Wrote %d train tokens, %d val tokens to %s", len(train_ids), len(val_ids), OUT_DIR)

    meta = {
        "vocab_size": enc.n_vocab,
        "tokenizer": "gpt2 (tiktoken)",
        "train_tokens": len(train_ids),
        "val_tokens": len(val_ids),
        "dtype": "uint16",
    }
    with open(OUT_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    log.info("Wrote meta.json: %s", meta)


if __name__ == "__main__":
    main()
