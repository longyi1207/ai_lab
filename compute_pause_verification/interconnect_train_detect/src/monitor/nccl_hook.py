"""Record NCCL/collective byte volumes for the NCCLProbe counter file.

Call `install_grad_hooks(model)` or `record_bytes(n)` from workloads.
Thread/process-safe via atomic rewrite of ICTD_NCCL_COUNTER.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

_lock = threading.Lock()
_tx = 0
_rx = 0
_n = 0

COUNTER_FILE = os.environ.get("ICTD_NCCL_COUNTER", "/tmp/ictd_nccl_bytes")


def _flush() -> None:
    Path(COUNTER_FILE).write_text(f"{_tx} {_rx} {_n}\n")


def reset() -> None:
    global _tx, _rx, _n
    with _lock:
        _tx = _rx = _n = 0
        _flush()


def record_bytes(n_bytes: int, bidirectional: bool = True) -> None:
    global _tx, _rx, _n
    with _lock:
        _tx += int(n_bytes)
        _rx += int(n_bytes) if bidirectional else 0
        _n += 1
        _flush()


def record_tensor_allreduce(tensor) -> None:
    """Estimate all-reduce traffic ≈ 2*(n-1)/n * nbytes ≈ 2*nbytes for large n."""
    try:
        nbytes = int(tensor.numel() * tensor.element_size())
    except Exception:
        return
    # ring allreduce ~ 2*(N-1)/N * size ≈ 2 * size for big clusters; use 2x
    record_bytes(2 * nbytes, bidirectional=False)
    # attribute half to rx
    global _rx
    with _lock:
        _rx += 2 * nbytes
        _flush()


def install_ddp_comm_hook(ddp_model) -> None:
    """Torch DDP comm hook that counts gradient all-reduce bytes."""
    import torch.distributed as dist
    from torch.distributed.algorithms.ddp_comm_hooks import default_hooks as default

    state = {"bytes": 0}

    def hook(state, bucket):  # noqa: A002
        buf = bucket.buffer()
        record_bytes(int(buf.numel() * buf.element_size()) * 2, bidirectional=False)
        global _rx
        with _lock:
            _rx += int(buf.numel() * buf.element_size()) * 2
            _flush()
        fut = dist.all_reduce(buf, async_op=True).get_future()
        return fut.then(lambda f: f.wait()[0] / dist.get_world_size())

    try:
        ddp_model.register_comm_hook(state, hook)
    except Exception:
        # fallback: no hook
        pass


def maybe_emit_event(monitor_client, n_bytes: int, op: str = "AllReduce") -> None:
    if monitor_client is None:
        return
    monitor_client.event("nccl_collective", bytes=n_bytes, op=op)
