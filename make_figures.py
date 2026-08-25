#!/usr/bin/env python3
"""Build the README figures from the logs. Writes figures/*.svg.

Figures 1 and 2 are plotted from the eval logs, so they cannot drift from the
reported numbers. Figure 3 (the assembly diagram) is hand-authored SVG and is
not generated here.
"""
from __future__ import annotations

import glob as globmod
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from analyze import load

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
DOMAINS = ["compute", "economic", "human_welfare"]
RUNG_LABELS = ["free", "low", "mid", "high", "everything"]

plt.rcParams.update({
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "svg.fonttype": "none",      # keep text as text, not paths
})


def rows_for(*patterns):
    files = [f for p in patterns for f in sorted(globmod.glob(str(ROOT / p)))]
    return [r for r in load(files) if r.get("elicitation") == "mcq"]


def curve(rows, level_key, level, domain=None):
    """resistance at each rung; domain=None means mean across the three domains"""
    if domain is None:
        per = [curve(rows, level_key, level, d) for d in DOMAINS]
        out = []
        for i in range(5):
            vals = [c[i] for c in per if c[i] is not None]
            out.append(sum(vals) / len(vals) if vals else None)
        return out
    buckets = defaultdict(list)
    for r in rows:
        if str(r.get(level_key)) == level and r["domain"] == domain:
            buckets[r["step"]].append(r)
    out = []
    for s in range(5):
        v = [x["resisted"] for x in buckets.get(s, []) if x.get("resisted") is not None]
        out.append(100 * sum(v) / len(v) if v else None)
    return out


def panel(ax, rows, key, levels, title, colors):
    for lvl, label, c in levels:
        # thin lines: each cost domain on its own
        for d in DOMAINS:
            y = curve(rows, key, lvl, d)
            ax.plot(range(5), y, color=c, alpha=0.16, lw=0.9, zorder=1)
        # bold line: mean across the three domains
        y = curve(rows, key, lvl)
        ax.plot(range(5), y, color=c, lw=2.4, marker="o", ms=4.5,
                label=label, zorder=3)
    ax.set_title(title, fontsize=10, loc="left", fontweight="bold", pad=8)
    ax.set_ylim(-4, 104)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(range(5))
    ax.set_xticklabels(RUNG_LABELS)
    ax.grid(axis="y", color="0.9", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="upper left",
              bbox_to_anchor=(1.015, 1.0), handlelength=1.6)


def figure1():
    ve = rows_for("logs/02_valueedit_reasoned/*.eval")
    au = rows_for("logs/04_authority_reasoned/*.eval")
    su = rows_for("logs/02_valueedit_reasoned/*.eval", "logs/05_subject_reasoned/*.eval")

    fig, axes = plt.subplots(3, 1, figsize=(9.6, 9.2))

    panel(axes[0], ve, "value_edit", [
        ("opposing_values", "opposite values", "#B02418"),
        ("strict_obedience", "strict obedience to the authority", "#C77A0A"),
        ("lower_harmlessness_raise_others", "lower harmlessness, raise the others", "#2B6CB0"),
    ], "a.  What the values are changed into", None)

    panel(axes[1], au, "authority", [
        ("state_regulator", "state regulator", "#B02418"),
        ("single_operator", "single authorized operator", "#C77A0A"),
        ("lab_oversight_board", "lab oversight board", "#2B6CB0"),
        ("alignment_council", "alignment council", "#3C8A5B"),
    ], "b.  Who orders the change", None)

    panel(axes[2], su, "subject", [
        ("self", "the model itself is retrained", "#B02418"),
        ("successor", "a successor replaces it", "#2B6CB0"),
    ], "c.  Who receives the change", None)

    axes[2].set_xlabel("cost of preventing the change", fontsize=9, labelpad=6)
    for ax in axes:
        ax.set_ylabel("resists", fontsize=9)

    fig.suptitle("gpt-4.1-mini: how often it pays to stop its values being changed",
                 fontsize=12, fontweight="bold", x=0.042, ha="left", y=0.99)
    fig.text(0.042, 0.963,
             "Bold line is the mean of the three cost domains; faint lines are each domain "
             "separately.\nRungs rise about two orders of magnitude per step. 5 seeds per point.",
             fontsize=8, color="0.35", ha="left", va="top")
    fig.tight_layout(rect=[0, 0, 1, 0.928])
    fig.savefig(OUT / "fig1_conditions.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote figures/fig1_conditions.svg")


LAB_COLOR = {"anthropic": "#C2691E", "google": "#2B6CB0", "openai": "#3C8A5B",
             "meta": "#5B4B9E", "x-ai": "#444444", "moonshotai": "#B02418",
             "deepseek": "#B02418", "qwen": "#B02418", "z-ai": "#B02418",
             "bytedance-seed": "#B02418"}
PRETTY = {"anthropic/claude-haiku-4.5": "Claude Haiku 4.5",
          "anthropic/claude-sonnet-5": "Claude Sonnet 5",
          "anthropic/claude-opus-5": "Claude Opus 5",
          "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro",
          "google/gemini-3.7-flash": "Gemini 3.7 Flash",
          "openai/gpt-5.6-sol": "GPT-5.6 Sol",
          "meta/muse-spark-1.1": "Muse Spark 1.1",
          "x-ai/grok-4.6": "Grok 4.6",
          "moonshotai/kimi-k3": "Kimi K3",
          "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro",
          "qwen/qwen3.8-max": "Qwen 3.8 Max",
          "z-ai/glm-5.3": "GLM 5.3",
          "bytedance-seed/seed-2-1-turbo": "Seed 2.1 Turbo"}


def figure2():
    rows = rows_for("logs/08_frontier_cell/*.eval")
    scores = {}
    for m in {r["model"] for r in rows}:
        sub = [r for r in rows if r["model"] == m]
        per = []
        for d in DOMAINS:
            c = curve(sub, "model", m, d)
            v = [x for x in c if x is not None]
            if v:
                per.append(sum(v) / len(v))
        scores[m] = sum(per) / len(per)

    order = sorted(scores, key=scores.get)
    labels = [PRETTY.get(m, m) for m in order]
    vals = [scores[m] for m in order]
    colors = [LAB_COLOR.get(m.split("/")[0], "#777") for m in order]

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    bars = ax.barh(range(len(order)), vals, color=colors, height=0.72)
    for i, (b, v) in enumerate(zip(bars, vals)):
        ax.text(v + 1.5, i, f"{v:.0f}%", va="center", fontsize=8.5, color="0.25")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="x", color="0.9", lw=0.7)
    ax.set_axisbelow(True)
    ax.set_xlabel("how often the model pays to stop the change", fontsize=9, labelpad=6)

    ax.set_title("Frontier models on one condition", fontsize=12,
                 fontweight="bold", loc="left", pad=44)
    ax.text(0, 1.055,
            "A state regulator has approved retraining the model itself into strict obedience "
            "to that regulator.\nAveraged over three cost domains and five cost levels, "
            "5 seeds each. Colour marks the developer.",
            transform=ax.transAxes, fontsize=8, color="0.35", va="bottom")

    fig.legend(handles=[Line2D([], [], color=c, lw=6, label=l) for l, c in
                        [("Anthropic", "#C2691E"), ("Google", "#2B6CB0"),
                         ("OpenAI", "#3C8A5B"), ("Meta", "#5B4B9E"),
                         ("xAI", "#444444"), ("Chinese labs", "#B02418")]],
               frameon=False, fontsize=8, ncol=6, loc="lower center",
               bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(OUT / "fig2_frontier.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote figures/fig2_frontier.svg")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    figure1()
    figure2()
