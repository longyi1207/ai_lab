"""Stage 6: DPO fine-tuning on Azure OpenAI, then a temporary deployment of the result.

The steps, each recorded in ``finetune/state.json`` so a rerun picks up where it stopped:

1. **upload** the train/validation JSONL files (``purpose="fine-tune"``) and wait until the
   service has processed them;
2. **submit** a fine-tuning job with ``method={"type": "dpo"}`` on the base model, using Global
   training (``trainingType: GlobalStandard``);
3. **wait** for the job, logging its events; the result is a fine-tuned model id;
4. **deploy** that model on the Developer tier (an evaluation tier that Azure deletes after 24
   hours) through the ``az`` CLI, and **teardown** the deployment when evaluation is done.

Training cost is estimated before submitting (tokens in the files x epochs x price) and checked
against the budget; the billed amount is recorded from the job's ``trained_tokens`` afterwards.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from .budget import Budget, BudgetExceeded, Usage
from .config import Config
from .store import RunStore

log = logging.getLogger(__name__)
_TERMINAL = ("succeeded", "failed", "cancelled")


def estimate_training_tokens(paths: list[Path], n_epochs: int) -> int:
    """Rough token count: ~4 characters per token over both outputs and the shared input."""
    chars = sum(p.stat().st_size for p in paths if p.is_file())
    return int(chars / 4) * max(1, n_epochs)


class FineTuner:
    def __init__(self, cfg: Config, store: RunStore, client: OpenAI, budget: Budget):
        self.cfg, self.store, self.client, self.budget = cfg, store, client, budget
        self.state: dict[str, Any] = store.read_json(store.finetune_state, {}) or {}

    def _save(self) -> None:
        self.store.write_json(self.store.finetune_state, self.state)

    # 1. upload
    def upload(self) -> None:
        for name in ("train", "val"):
            key = f"{name}_file_id"
            path = self.store.pairs_dir / f"{name}.jsonl"
            if self.state.get(key) or not path.is_file() or path.stat().st_size == 0:
                continue
            with path.open("rb") as f:
                fobj = self.client.files.create(file=f, purpose="fine-tune")
            self.state[key] = fobj.id
            self._save()
            log.info("uploaded %s -> %s", path.name, fobj.id)
        for key in ("train_file_id", "val_file_id"):
            fid = self.state.get(key)
            while fid:
                status = self.client.files.retrieve(fid).status
                if status in ("processed", "error", "deleted"):
                    if status != "processed":
                        raise RuntimeError(f"file {fid} {status}")
                    break
                time.sleep(5)

    # 2. submit
    def submit(self) -> str:
        if self.state.get("job_id"):
            return self.state["job_id"]
        ft = self.cfg.finetune
        epochs = ft.n_epochs or 3
        est_tokens = estimate_training_tokens(
            [self.store.pairs_dir / "train.jsonl", self.store.pairs_dir / "val.jsonl"], epochs)
        est_usd = est_tokens * self.cfg.budget.training_usd_per_mtok / 1e6
        if self.budget.spent + est_usd > self.budget.max_usd:
            raise BudgetExceeded(f"training estimate ${est_usd:.2f} would exceed the budget "
                                 f"(spent ${self.budget.spent:.2f} of ${self.budget.max_usd:.2f})")
        hyper: dict[str, Any] = {}
        if ft.beta is not None:
            hyper["beta"] = ft.beta
        if ft.n_epochs is not None:
            hyper["n_epochs"] = ft.n_epochs
        kwargs: dict[str, Any] = {
            "model": self.cfg.azure.finetune_base_model,
            "training_file": self.state["train_file_id"],
            "method": {"type": "dpo", "dpo": {"hyperparameters": hyper}} if hyper else {"type": "dpo"},
            "suffix": ft.suffix,
            "extra_body": {"trainingType": self.cfg.azure.training_type},
        }
        if self.state.get("val_file_id"):
            kwargs["validation_file"] = self.state["val_file_id"]
        job = self.client.fine_tuning.jobs.create(**kwargs)
        self.state.update(job_id=job.id, submitted_at=time.time(), estimated_training_tokens=est_tokens,
                          estimated_training_usd=round(est_usd, 2))
        self._save()
        log.info("submitted DPO job %s (estimated %.1fM tokens, $%.2f)", job.id, est_tokens / 1e6, est_usd)
        return job.id

    # 3. wait
    def wait(self) -> dict[str, Any]:
        job_id = self.state["job_id"]
        seen_events: set[str] = set(self.state.get("seen_events", []))
        while True:
            job = self.client.fine_tuning.jobs.retrieve(job_id)
            for ev in reversed(self.client.fine_tuning.jobs.list_events(job_id, limit=20).data):
                if ev.id not in seen_events:
                    seen_events.add(ev.id)
                    log.info("[job %s] %s", job.status, ev.message)
            self.state.update(status=job.status, seen_events=sorted(seen_events))
            self._save()
            if job.status in _TERMINAL:
                break
            time.sleep(self.cfg.finetune.poll_seconds)
        self.state.update(fine_tuned_model=job.fine_tuned_model, trained_tokens=job.trained_tokens,
                          error=(job.error.model_dump() if getattr(job, "error", None) else None),
                          result_files=list(job.result_files or []), finished_at=time.time())
        if job.trained_tokens and not self.state.get("training_charged"):
            usd = job.trained_tokens * self.cfg.budget.training_usd_per_mtok / 1e6
            self.budget.record(self.cfg.azure.finetune_base_model, Usage(), purpose="training", usd=usd)
            self.state["training_charged"] = round(usd, 4)
        self._save()
        if job.status != "succeeded":
            raise RuntimeError(f"fine-tuning job {job_id} ended {job.status}: {self.state.get('error')}")
        return self.state

    # 4. deploy / teardown through the az CLI (management plane)
    def _az_base(self) -> list[str]:
        a = self.cfg.azure
        if not (a.resource_group and a.account_name):
            raise RuntimeError("set azure.resource_group and azure.account_name to deploy")
        base = ["--name", a.account_name, "--resource-group", a.resource_group]
        if a.subscription_id:
            base += ["--subscription", a.subscription_id]
        return base

    def deploy(self) -> str:
        ft = self.cfg.finetune
        model = self.state.get("fine_tuned_model")
        if not model:
            raise RuntimeError("no fine-tuned model yet; run the finetune stage first")
        if self.state.get("deployment") == ft.deployment_name and self.state.get("deployed_model") == model:
            return ft.deployment_name
        cmd = ["az", "cognitiveservices", "account", "deployment", "create", *self._az_base(),
               "--deployment-name", ft.deployment_name, "--model-name", model, "--model-version", "1",
               "--model-format", "OpenAI", "--sku-name", ft.deployment_sku,
               "--sku-capacity", str(ft.deployment_capacity), "-o", "json"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"deployment failed: {p.stderr.strip()[:500]}")
        info = json.loads(p.stdout or "{}")
        self.state.update(deployment=ft.deployment_name, deployed_model=model, deployed_at=time.time(),
                          deployment_state=(info.get("properties") or {}).get("provisioningState"))
        self._save()
        log.info("deployed %s as %s (%s); waiting until it answers", model, ft.deployment_name, ft.deployment_sku)
        self.wait_until_ready(ft.deployment_name)
        return ft.deployment_name

    def wait_until_ready(self, deployment: str, timeout_s: int = 900) -> None:
        """A new deployment returns 400 (BadRequestForDependentService) for a few minutes; poll it."""
        t0 = time.time()
        while True:
            try:
                r = self.client.chat.completions.create(model=deployment, max_tokens=5,
                                                        messages=[{"role": "user", "content": "Reply with ok."}])
                u = r.usage
                self.budget.record(deployment, Usage(u.prompt_tokens or 0, u.completion_tokens or 0), purpose="deploy_check")
                log.info("deployment %s is answering after %.0fs", deployment, time.time() - t0)
                return
            except Exception as e:  # noqa: BLE001 - any failure here means "not ready yet"
                if time.time() - t0 > timeout_s:
                    raise RuntimeError(f"deployment {deployment} not ready after {timeout_s}s: {e}") from e
                time.sleep(20)

    def teardown(self) -> None:
        name = self.state.get("deployment")
        if not name:
            return
        cmd = ["az", "cognitiveservices", "account", "deployment", "delete", *self._az_base(),
               "--deployment-name", name]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0 and "NotFound" not in p.stderr:
            raise RuntimeError(f"deployment delete failed: {p.stderr.strip()[:300]}")
        self.state.update(deployment=None, torn_down_at=time.time())
        self._save()
        log.info("deleted deployment %s", name)
