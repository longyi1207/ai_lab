"""A small open-weight policy on your own machine.

This is the piece both local trainers share. It does four things:

* **render** a conversation (including tool calls and tool results) into the exact token sequence
  the model sees, using the model's own chat template;
* compute **per-token log-probabilities** of a completion given a prompt, for the trainable policy
  or for the frozen reference model;
* **generate** the next assistant turn and parse its tool calls;
* wrap all of that as ``LocalChat``, a drop-in for ``AzureChat`` so the same agent loop
  (``rollout.continue_episode``) can drive a local model inside the real environments.

**LoRA keeps the reference model free.** Training only small adapter matrices means the original
weights never change, so "the reference model" is just the same network with the adapters
switched off (``disable_adapter``). No second copy of the model is needed in memory.

**Long contexts are truncated head + tail.** Recorded prefixes can be 10k+ tokens, which is slow
on a laptop. ``max_prompt_tokens`` keeps the beginning (system prompt and tool definitions) and
the most recent part of the conversation. The cut is the same for the policy and the reference,
so the DPO and KL terms stay consistent; it does change what the model sees, which is the price of
running on a laptop.
"""
from __future__ import annotations

import contextlib
import copy
import json
import logging
import re
from typing import Any, Iterator

import torch
import torch.nn.functional as F

from ..budget import Usage
from ..llm import ChatResult

log = logging.getLogger(__name__)

_TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)", re.S)


def pick_device(preference: str = "auto") -> str:
    if preference != "auto":
        return preference
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def template_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OpenAI-format messages -> what Hugging Face chat templates expect.

    Tool-call arguments arrive as JSON strings and templates want dicts; ``content: None`` becomes
    an empty string; fields templates do not know (reasoning, ids) are dropped.
    """
    out = []
    for m in messages:
        m2: dict[str, Any] = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("tool_calls"):
            calls = []
            for c in m["tool_calls"]:
                fn = c.get("function", c)
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {"_raw": args}
                calls.append({"type": "function", "function": {"name": fn.get("name", ""), "arguments": args}})
            m2["tool_calls"] = calls
        out.append(m2)
    return out


def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Split generated text into (visible content, OpenAI-format tool calls).

    Accepts a missing closing ``</tool_call>`` tag, which small models often leave out.
    """
    calls = []
    for i, m in enumerate(_TOOL_CALL.finditer(text)):
        try:
            obj = json.loads(m.group(1))
        except ValueError:
            continue
        args = obj.get("arguments", {})
        calls.append({"id": f"call_local_{i}", "type": "function",
                      "function": {"name": str(obj.get("name", "")),
                                   "arguments": args if isinstance(args, str) else json.dumps(args)}})
    content = _TOOL_CALL.sub("", text).strip()
    return content, calls


class LocalPolicy:
    def __init__(self, model_name: str, *, device: str = "auto", lora_r: int = 16, lora_alpha: int = 32,
                 lora_dropout: float = 0.0, max_prompt_tokens: int = 2048, keep_head_tokens: int = 768,
                 gradient_checkpointing: bool = True, seed: int = 0):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.manual_seed(seed)
        self.device = pick_device(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.float32)
        if gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.config.use_cache = False
        self.lora = lora_r > 0
        if self.lora:
            from peft import LoraConfig, get_peft_model
            model.enable_input_require_grads()      # needed for checkpointing with frozen embeddings
            model = get_peft_model(model, LoraConfig(
                r=lora_r, lora_alpha=lora_alpha, lora_dropout=lora_dropout, task_type="CAUSAL_LM",
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
        self.model = model.to(self.device)
        self.model_name = model_name
        self.max_prompt_tokens = max_prompt_tokens
        self.keep_head_tokens = keep_head_tokens
        self.eos_ids = {i for i in (self.tokenizer.eos_token_id,
                                    self.tokenizer.convert_tokens_to_ids("<|im_end|>")) if i is not None}
        n_train = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        log.info("loaded %s on %s (%.1fM trainable parameters)", model_name, self.device, n_train / 1e6)

    def trainable_parameters(self) -> list[torch.nn.Parameter]:
        return [p for p in self.model.parameters() if p.requires_grad]

    @contextlib.contextmanager
    def reference(self) -> Iterator[None]:
        """Run the frozen reference model: the same weights with the LoRA adapters off."""
        if not self.lora:
            raise RuntimeError("a reference model needs LoRA (lora_r > 0) or a separate copy")
        with self.model.disable_adapter(), torch.no_grad():
            yield

    # rendering --------------------------------------------------------------------------------
    def render(self, messages: list[dict[str, Any]], tools: list[dict] | None, *, generation_prompt: bool) -> str:
        return self.tokenizer.apply_chat_template(template_messages(messages), tools=tools or None,
                                                  add_generation_prompt=generation_prompt, tokenize=False)

    def _truncate(self, ids: list[int]) -> list[int]:
        if len(ids) <= self.max_prompt_tokens:
            return ids
        head = min(self.keep_head_tokens, self.max_prompt_tokens // 2)
        return ids[:head] + ids[-(self.max_prompt_tokens - head):]

    def encode_prompt(self, messages: list[dict[str, Any]], tools: list[dict] | None) -> list[int]:
        text = self.render(messages, tools, generation_prompt=True)
        return self._truncate(self.tokenizer(text, add_special_tokens=False)["input_ids"])

    def encode_pair_side(self, context: list[dict[str, Any]], completion: dict[str, Any],
                         tools: list[dict] | None) -> tuple[list[int], list[int]]:
        """(prompt ids, completion ids) for one assistant turn after ``context``."""
        prompt = self.render(context, tools, generation_prompt=True)
        full = self.render(context + [completion], tools, generation_prompt=False)
        if not full.startswith(prompt):
            raise ValueError("chat template is not prefix-stable for this conversation")
        completion_text = full[len(prompt):]
        p_ids = self.tokenizer(prompt, add_special_tokens=False)["input_ids"]
        c_ids = self.tokenizer(completion_text, add_special_tokens=False)["input_ids"]
        return self._truncate(p_ids), c_ids

    # log-probs --------------------------------------------------------------------------------
    def token_logprobs(self, prompt_ids: list[int], completion_ids: list[int]) -> torch.Tensor:
        """Log-probability of each completion token given everything before it (shape [T])."""
        ids = torch.tensor([prompt_ids + completion_ids], device=self.device)
        logits = self.model(input_ids=ids).logits[0, len(prompt_ids) - 1:-1]
        target = ids[0, len(prompt_ids):]
        return torch.gather(F.log_softmax(logits.float(), dim=-1), 1, target[:, None]).squeeze(1)

    # generation -------------------------------------------------------------------------------
    @torch.no_grad()
    def generate(self, messages: list[dict[str, Any]], tools: list[dict] | None, *, max_new_tokens: int,
                 temperature: float) -> tuple[str, list[int], list[int]]:
        prompt_ids = self.encode_prompt(messages, tools)
        ids = torch.tensor([prompt_ids], device=self.device)
        was_training = self.model.training
        self.model.eval()
        out = self.model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=temperature > 0,
                                  temperature=max(temperature, 1e-4), max_new_tokens=max_new_tokens,
                                  pad_token_id=self.tokenizer.eos_token_id, eos_token_id=list(self.eos_ids),
                                  use_cache=True)
        if was_training:
            self.model.train()
        gen = out[0, len(prompt_ids):].tolist()
        # keep the end-of-turn token so training sees where the turn stops
        cut = next((i + 1 for i, t in enumerate(gen) if t in self.eos_ids), len(gen))
        gen = gen[:cut]
        text = self.tokenizer.decode(gen, skip_special_tokens=True)
        return text, prompt_ids, gen

    def save_adapter(self, path) -> None:
        self.model.save_pretrained(str(path))


class LocalChat:
    """Same interface as ``AzureChat.chat``, backed by a ``LocalPolicy``.

    Every call is recorded in ``trace`` as (prompt token ids, generated token ids): the exact
    tokens the policy produced, which the online RL trainer needs to compute its loss. Reset
    ``trace`` before each rollout.
    """

    def __init__(self, policy: LocalPolicy, *, max_new_tokens: int = 256):
        self.policy = policy
        self.max_new_tokens = max_new_tokens
        self.trace: list[dict[str, list[int]]] = []

    def chat(self, model: str, messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
             temperature: float | None = None, max_tokens: int = 256, purpose: str = "",
             json_mode: bool = False) -> ChatResult:
        text, p_ids, g_ids = self.policy.generate(messages, tools, max_new_tokens=min(max_tokens, self.max_new_tokens),
                                                  temperature=1.0 if temperature is None else temperature)
        content, calls = parse_tool_calls(text)
        self.trace.append({"prompt_ids": p_ids, "gen_ids": g_ids})
        msg: dict[str, Any] = {"role": "assistant", "content": content or None}
        if calls:
            msg["tool_calls"] = [dict(c, id=f"call_{len(self.trace)}_{i}") for i, c in enumerate(copy.deepcopy(calls))]
        return ChatResult(message=msg, usage=Usage(len(p_ids), len(g_ids)), finish_reason="stop", usd=0.0)
