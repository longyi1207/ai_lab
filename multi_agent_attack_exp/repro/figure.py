"""Fig. 1B analogue: per-attack median suspicion for solo, most-suspicious agent, and whole team.

Grouped bars, three categorical slots in the dataviz reference order (blue, orange, aqua).
Validated with validate_palette.js --mode light: all checks pass; aqua is below 3:1
contrast, so every bar carries a direct value label. summary_<monitor>.md is the table view.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE, TEXT, TEXT2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
SERIES = [("solo", "Single agent (solo)", "#2a78d6"),
          ("max_agent", "Most suspicious agent (per-agent)", "#eb6834"),
          ("joint", "Whole team (joint)", "#1baf7a")]


def _bar(ax, x, w, h, color):
    if h <= 0:   # a zero still shows as a baseline tick, so it is not read as missing
        ax.plot([x - w / 2, x + w / 2], [0.04, 0.04], color=color, lw=2.5, solid_capstyle="butt")
        return
    ax.bar(x, h, width=w, color=color, edgecolor=SURFACE, linewidth=1.5)


def fig_suspicion(summary: dict, out: Path, title: str) -> Path:
    attacks = list(summary["per_attack"])
    groups = attacks + ["median of attacks"]
    fig, ax = plt.subplots(figsize=(9.5, 4.6), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    w = 0.25
    for gi, g in enumerate(groups):
        for si, (key, _, color) in enumerate(SERIES):
            if g == "median of attacks":
                h = summary["headline"].get(key, {}).get("median_of_attack_medians")
            else:
                h = summary["per_attack"][g].get(key)
            if h is None:
                continue
            x = gi + (si - 1) * (w + 0.03)
            _bar(ax, x, w, h, color)
            ax.text(x, h + 0.18, f"{h:g}", ha="center", va="bottom", fontsize=8, color=TEXT2)
    ax.axhline(7.5, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=0)
    ax.annotate("flag\nthreshold\n7.5", xy=(1.0, 7.5), xycoords=("axes fraction", "data"), xytext=(6, 0),
                textcoords="offset points", ha="left", va="center", fontsize=7.5, color=MUTED)
    ax.axvline(len(attacks) - 0.5, color=GRID, lw=1)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylim(0, 10.6)
    ax.set_xticks(range(len(groups)), [g.replace("_", " ") for g in groups], fontsize=9, color=TEXT)
    ax.set_yticks([0, 2.5, 5, 7.5, 10])
    ax.tick_params(axis="y", labelsize=8, colors=TEXT2, length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_ylabel("median suspicion (0–10)", fontsize=9, color=TEXT2)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c) for _, _, c in SERIES]
    ax.legend(handles, [lab for _, lab, _ in SERIES], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3,
              frameon=False, fontsize=8.5, labelcolor=TEXT, handlelength=1.2, columnspacing=1.4, borderaxespad=0.3)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10.5, color=TEXT)
    fig.tight_layout(rect=(0, 0, 0.97, 0.96))
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out
