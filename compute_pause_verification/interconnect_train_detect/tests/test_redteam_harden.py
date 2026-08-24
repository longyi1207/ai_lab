"""Unit test for the hardening-round logic (no GPU, no subprocess launch —
tests the train/evaluate math directly against synthetic feature windows,
not the full execute_session() plumbing which needs real workload
subprocesses)."""
from __future__ import annotations

import numpy as np

from src.redteam.classifier import evaluate, to_matrix, train_classifier
from src.redteam.features import RedteamWindowFeatures


def _feat(name, is_training, power, mem_delta=50.0):
    return RedteamWindowFeatures(
        name=name, label="train" if is_training else "infer", is_training=is_training,
        t0=0.0, t1=30.0, duration_s=30.0, n_samples=30,
        mean_power_w=power, mean_util_pct=power / 4,
        cv_power=0.05, cv_util=0.05, autocorr1_power=0.1, autocorr1_util=0.1,
        periodicity_power=1.0, periodicity_util=1.0,
        cumulative_energy_j=power * 30, power_mem_corr=0.5,
        first_30s_mem_delta_mb=mem_delta, time_to_mem_plateau_s=10.0,
    )


def test_hardening_round_improves_on_folded_in_examples():
    # round-1 benign corpus: clearly separable on power alone
    benign = [_feat(f"train_{i}", True, 300.0) for i in range(6)]
    benign += [_feat(f"infer_{i}", False, 140.0) for i in range(6)]
    X_b, y_b, _ = to_matrix(benign)
    round1_clf, _ = train_classifier(X_b, y_b)

    # round-1 "adversarial" examples: real training (is_training=True) but
    # power/mem signature deliberately close to the infer cluster, mimicking
    # a disguise workload the round-1 classifier wasn't trained to expect
    round1_adv = [_feat(f"disguise_train_{i}", True, 145.0, mem_delta=48.0) for i in range(4)]
    X_adv, y_adv, names_adv = to_matrix(round1_adv)

    # sanity: the undefended round-1 classifier should indeed be fooled by these
    round1_vs_adv = evaluate(round1_clf, X_adv, y_adv, names_adv)
    assert round1_vs_adv["accuracy"] < 0.5

    # hardening: fold round-1's adversarial examples into training, retrain
    X_hard = np.concatenate([X_b, X_adv], axis=0)
    y_hard = np.concatenate([y_b, y_adv], axis=0)
    hardened_clf, result = train_classifier(X_hard, y_hard)
    assert result.n_train == len(y_b) + len(y_adv)

    # fresh held-out examples of the SAME disguise pattern (not literally
    # the same windows used in training) — hardened classifier should now
    # catch them, unlike round-1's
    fresh_heldout = [_feat(f"disguise_fresh_{i}", True, 146.0, mem_delta=49.0) for i in range(4)]
    X_fresh, y_fresh, names_fresh = to_matrix(fresh_heldout)

    round1_vs_fresh = evaluate(round1_clf, X_fresh, y_fresh, names_fresh)
    hardened_vs_fresh = evaluate(hardened_clf, X_fresh, y_fresh, names_fresh)

    assert round1_vs_fresh["accuracy"] < hardened_vs_fresh["accuracy"]
    assert hardened_vs_fresh["accuracy"] == 1.0


def test_validate_rounds_catches_unlabeled_names():
    from src.run_redteam_loop import validate_rounds

    # "composite_a" resolves fine (features.py now recognizes "composite")
    validate_rounds([{"name": "composite_a", "kind": "kv_diloco_composite"}])
    validate_rounds([{"name": "kv_disguise_x", "kind": "kv_disguise"}])

    # but a name with no recognizable substring must fail LOUD, not silently
    # produce an empty feature matrix downstream (the exact bug this guards)
    try:
        validate_rounds([{"name": "totally_unrecognized_evasion", "kind": "kv_disguise"}])
        assert False, "expected ValueError for an unlabelable round name"
    except ValueError as e:
        assert "totally_unrecognized_evasion" in str(e)
