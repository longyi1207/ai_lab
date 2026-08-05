"""Tests for Welch t / Cohen d (no GPU)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.detect.stats import cohens_d, compare_two, hedges_g, welch_t


def test_cohens_d_large_separation():
    rng = np.random.default_rng(0)
    a = rng.normal(10, 1, size=30)
    b = rng.normal(0, 1, size=30)
    d = cohens_d(a, b)
    assert d > 3.0


def test_welch_rejects_equal_means():
    rng = np.random.default_rng(1)
    a = rng.normal(0, 1, size=40)
    b = rng.normal(0, 1, size=40)
    t, df, p = welch_t(a, b)
    assert p > 0.05


def test_welch_detects_shift():
    rng = np.random.default_rng(2)
    a = rng.normal(1.0, 0.5, size=25)
    b = rng.normal(0.0, 0.5, size=25)
    t, df, p = welch_t(a, b)
    assert p < 0.01
    assert t > 0


def test_compare_two_separable_flag():
    rng = np.random.default_rng(3)
    train = rng.normal(0.16, 0.01, size=8)
    infer = rng.normal(0.004, 0.001, size=8)
    r = compare_two(train, infer, n_boot=500)
    assert r.separable
    assert r.cohens_d > 0.8
    assert r.p_value < 0.05
    assert r.mean_diff > 0


def test_hedges_g_less_than_d_for_small_n():
    a = [1.0, 2.0, 3.0]
    b = [0.0, 0.5, 1.0]
    d = cohens_d(a, b)
    g = hedges_g(a, b)
    assert abs(g) <= abs(d) + 1e-9
