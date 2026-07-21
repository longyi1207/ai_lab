"""Phase 4, step 3b: expert parallelism — experts distributed across ranks, tokens routed to
wherever their assigned expert lives via all_to_all. Verified against the single-device
MoELayer (moe_layer.py) computing the identical routing decision, unsplit.

This is the piece that makes MoE communication fundamentally different from tensor parallelism
(fixed all-reduce, same shape every step) or pipeline parallelism (fixed point-to-point,
same shape every step): the communication pattern here is DATA-DEPENDENT — how many tokens go
from rank i to rank j depends on what the router decided for THIS batch, which is why real
systems (DeepSeek's DeepEP) need a first "how many tokens am I sending you" round before the
actual token-data round, and why cross-node MoE traffic is much harder to schedule/overlap than
tensor or pipeline parallelism's static patterns — the direct motivation for DualPipe (see
README Phase 4).

Run: GLOO_SOCKET_IFNAME=lo0 .venv/bin/torchrun --nproc_per_node=4 --master_addr=127.0.0.1 \
     --master_port=29524 experiments/expert_parallel_demo.py
"""

import sys

import torch
import torch.distributed as dist
import torch.nn.functional as F

sys.path.insert(0, "experiments")
from moe_layer import ExpertFFN, MoELayer  # noqa: E402


def main():
    dist.init_process_group(backend="gloo")
    rank, world = dist.get_rank(), dist.get_world_size()

    n_embd, n_experts, top_k = 16, world * 2, 2  # 2 experts per rank
    experts_per_rank = n_experts // world
    tokens_per_rank = 6

    # --- build a reference MoE layer identically on every rank (same seed = same weights,
    # no communication needed to agree on them, same trick as tensor_parallel_mlp.py) ---
    torch.manual_seed(0)
    reference = MoELayer(n_embd, n_experts, top_k)
    reference.eval()  # freeze expert_bias so both paths route identically — isolates the
                       # thing under test (communication correctness) from the load-balancing
                       # update, which is already verified separately in moe_layer.py

    # this rank's local experts are a *view* into the reference's expert list — same weights,
    # not a copy — so gathering results back should equal the reference layer exactly.
    local_experts = torch.nn.ModuleList(
        [reference.experts[rank * experts_per_rank + i] for i in range(experts_per_rank)]
    )

    # --- every rank has its own shard of tokens (this is what "data parallel + expert
    # parallel on the same ranks" looks like — no separate mesh needed for this demo) ---
    torch.manual_seed(100 + rank)
    x_local = torch.randn(tokens_per_rank, n_embd)

    # routing decision computed locally — router is replicated (every rank has the same copy),
    # so no communication needed for this part, only the expert computation is sharded.
    with torch.no_grad():
        logits = reference.router(x_local)
        scores = logits.softmax(dim=-1)
        _, topk_idx = scores.topk(top_k, dim=-1)          # (tokens_per_rank, top_k)
        gate = scores.gather(-1, topk_idx)
        gate = gate / gate.sum(-1, keepdim=True)
        target_rank = topk_idx // experts_per_rank         # which rank owns each chosen expert

    # === DISPATCH: send each (token, chosen-expert) pair to the rank that owns that expert ===
    # send_lists[r] = every token-copy this rank needs to send to rank r (a token picked for
    # top_k=2 experts on two DIFFERENT ranks gets sent out twice, once per destination).
    send_lists = [[] for _ in range(world)]
    send_meta = [[] for _ in range(world)]  # (origin_token_idx, expert_id, gate_weight) per send
    for t in range(tokens_per_rank):
        for k in range(top_k):
            r = target_rank[t, k].item()
            send_lists[r].append(x_local[t])
            send_meta[r].append((t, topk_idx[t, k].item(), gate[t, k].item()))

    # NOTE on API choice: dist.all_to_all (the list-based version) turns out NOT to support
    # ragged/variable-size tensors on the gloo backend in practice — it errors with a tensor
    # size mismatch as soon as different ranks send different amounts (found by hitting it, not
    # by reading docs). all_to_all_single with explicit input_split_sizes/output_split_sizes
    # DOES support variable sizes on gloo — that's the fix, and it's also what real dispatch
    # kernels (DeepEP) are structured around: one flat buffer + split-size metadata, not a
    # Python list of differently-shaped tensors.
    send_counts = [len(lst) for lst in send_lists]
    send_flat = torch.cat([torch.stack(lst) if lst else torch.empty(0, n_embd) for lst in send_lists])
    send_expert_ids_flat = torch.tensor(
        [m[1] for meta in send_meta for m in meta], dtype=torch.long
    ) if any(send_meta) else torch.empty(0, dtype=torch.long)

    # sizes round-trip: every rank must learn how much it's about to RECEIVE from each sender
    # before it can allocate a correctly-shaped buffer — this is itself a (tiny) all_to_all.
    send_counts_t = torch.tensor(send_counts, dtype=torch.long)
    recv_counts_t = torch.empty(world, dtype=torch.long)
    dist.all_to_all_single(recv_counts_t, send_counts_t)
    recv_counts = recv_counts_t.tolist()

    recv_flat = torch.empty(sum(recv_counts), n_embd)
    dist.all_to_all_single(recv_flat, send_flat, output_split_sizes=recv_counts, input_split_sizes=send_counts)

    recv_expert_ids_flat = torch.empty(sum(recv_counts), dtype=torch.long)
    dist.all_to_all_single(recv_expert_ids_flat, send_expert_ids_flat,
                            output_split_sizes=recv_counts, input_split_sizes=send_counts)

    # === COMPUTE: run received tokens through THIS rank's local experts ===
    out_flat = torch.zeros_like(recv_flat)
    for local_e in range(experts_per_rank):
        global_e = rank * experts_per_rank + local_e
        sel = (recv_expert_ids_flat == global_e).nonzero(as_tuple=True)[0]
        if sel.numel() == 0:
            continue
        out_flat[sel] = local_experts[local_e](recv_flat[sel])

    # === COMBINE: send results back to each token's origin rank (reverse split sizes) ===
    returned_flat = torch.empty(sum(send_counts), n_embd)
    dist.all_to_all_single(returned_flat, out_flat, output_split_sizes=send_counts, input_split_sizes=recv_counts)

    # scatter back into origin-token positions, weighted by gate, matching moe_layer.py's
    # `out.index_add_(...)` combine step exactly.
    out_local = torch.zeros(tokens_per_rank, n_embd)
    offset = 0
    for r in range(world):
        for i, (t, _e, g) in enumerate(send_meta[r]):
            out_local[t] += returned_flat[offset + i] * g
        offset += send_counts[r]

    # === VERIFY: same tokens, through the reference MoELayer's forward, should match exactly ===
    with torch.no_grad():
        ref_out, _ = reference(x_local.unsqueeze(0))
        ref_out = ref_out.squeeze(0)
    max_diff = (out_local - ref_out).abs().max().item()

    print(f"[rank {rank}] tokens sent to each rank: {send_counts}  "
          f"received from each rank: {recv_counts}  "
          f"max|diff| vs single-device reference: {max_diff:.2e}  "
          f"{'PASS' if max_diff < 1e-5 else 'FAIL'}")

    dist.destroy_process_group()


if __name__ == "__main__":
    main()
