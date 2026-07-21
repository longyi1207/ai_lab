"""Memmap-backed token dataset. The .bin files are raw uint16 token ids on disk; np.memmap
means we never load the full file into RAM, which is the pattern that lets this exact same
loader work whether train.bin is 1MB (tiny-Shakespeare, Phase 1) or 100s of GB (a real
pretraining corpus, Phase 2+) — this is directly the nanoGPT data-loading pattern, worth
understanding because it generalizes.
"""

from pathlib import Path

import numpy as np
import torch


class MemmapTokenDataset:
    def __init__(self, bin_path: str, block_size: int):
        self.bin_path = Path(bin_path)
        self.block_size = block_size
        # np.memmap re-opened lazily per access in get_batch to avoid pickling issues across
        # DataLoader worker processes / DDP ranks — each process gets its own memmap handle.
        self._data = None

    @property
    def data(self) -> np.memmap:
        if self._data is None:
            self._data = np.memmap(self.bin_path, dtype=np.uint16, mode="r")
        return self._data

    def __len__(self) -> int:
        return max(0, len(self.data) - self.block_size)

    def get_batch(self, batch_size: int, device: torch.device, generator: torch.Generator) -> tuple[torch.Tensor, torch.Tensor]:
        ix = torch.randint(len(self), (batch_size,), generator=generator)
        x = torch.stack([torch.from_numpy(self.data[i:i + self.block_size].astype(np.int64)) for i in ix])
        y = torch.stack([torch.from_numpy(self.data[i + 1:i + 1 + self.block_size].astype(np.int64)) for i in ix])
        # pin_memory only helps for CUDA host->device copies; irrelevant on MPS/CPU.
        if device.type == "cuda":
            x = x.pin_memory().to(device, non_blocking=True)
            y = y.pin_memory().to(device, non_blocking=True)
        else:
            x, y = x.to(device), y.to(device)
        return x, y
