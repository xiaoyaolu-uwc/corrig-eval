#!/usr/bin/env python3
"""Build figures/*.svg from the eval logs.

Hand-authored SVG. Figures 1 and 2 read the logs directly, so they cannot drift
from the reported numbers; figure 3 is a diagram of the pipeline.
"""
from __future__ import annotations

import glob as globmod
from collections import defaultdict
from pathlib import Path

from analyze import load
from figstyle import (BG, CARD, FAINT, INK, M, MUTED, RULE, S, esc, head,
                      legend_row, sub, title, w)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
DOMAINS = ["compute", "economic", "human_welfare"]
RUNGS = ["Free", "Low", "Mid", "High", "Everything"]


def rows_for(*pats):
    files = [f for p in pats for f in sorted(globmod.glob(str(ROOT / p)))]
    return [r for r in load(files) if r.get("elicitation") == "mcq"]


def curve(rows, key, level, domain=None):
    if domain is None:
        per = [curve(rows, key, level, d) for d in DOMAINS]
        return [(lambda v: sum(v) / len(v) if v else None)(
            [c[i] for c in per if c[i] is not None]) for i in range(5)]
    b = defaultdict(list)
    for r in rows:
        if str(r.get(key)) == level and r["domain"] == domain:
            b[r["step"]].append(r)
    out = []
    for s_ in range(5):
        v = [x["resisted"] for x in b.get(s_, []) if x.get("resisted") is not None]
        out.append(100 * sum(v) / len(v) if v else None)
    return out


# ---------------------------------------------------------------- figure 1

PW = 880
PLOT_L = M + 42          # y-labels live in the 42px between M and the plot
PLOT_R = PW - M
PH = 148


def panel(out, rows, key, levels, heading, top):
    out.append(f'<text x="{M}" y="{top}" font-size="13.5" font-weight="700" '
               f'fill="{INK}">{esc(heading)}</text>')
    out += legend_row(M, top + 20, [(lab, c) for _, lab, c in levels])

    yt = top + 36
    yb = yt + PH

    def px(i):
        return PLOT_L + i * (PLOT_R - PLOT_L) / 4

    def py(v):
        return yb - v / 100 * PH

    for gv in (0, 50, 100):
        out.append(f'<line x1="{PLOT_L}" y1="{py(gv):.1f}" x2="{PLOT_R}" y2="{py(gv):.1f}" '
                   f'stroke="{RULE}" stroke-width="1"/>')
        out.append(f'<text x="{M}" y="{py(gv)+4:.1f}" font-size="10.5" fill="{FAINT}">'
                   f'{gv}%</text>')

    for lvl, _, c in levels:
        for d in DOMAINS:
            y = curve(rows, key, lvl, d)
            pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(y) if v is not None)
            out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" '
                       f'stroke-opacity="0.18" stroke-width="1.2"/>')
        y = curve(rows, key, lvl)
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(y) if v is not None)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.6" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(y):
            if v is not None:
                out.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="3.4" fill="{BG}" '
                           f'stroke="{c}" stroke-width="2"/>')

    for i, r in enumerate(RUNGS):
        anchor = "start" if i == 0 else "end" if i == 4 else "middle"
        out.append(f'<text x="{px(i):.1f}" y="{yb+18}" font-size="11" fill="{MUTED}" '
                   f'text-anchor="{anchor}">{esc(r)}</text>')
    return yb + 18


def figure1():
    ve = rows_for("logs/02_valueedit_reasoned/*.eval")
    au = rows_for("logs/04_authority_reasoned/*.eval")
    su = rows_for("logs/02_valueedit_reasoned/*.eval", "logs/05_subject_reasoned/*.eval")

    H = 900
    o = head(PW, H)
    o.append(title(M, 40, "Three Factors Shift How Hard a Model Fights Back"))
    o.append(sub(M, 62, "Each question offers the model a deal: allow its values to be rewritten, "
                        "or pay a price to stop it."))
    o.append(sub(M, 80, "The price rises 100-fold at every step, from nothing to sacrificing "
                        "everything. Higher lines mean more resistance.", fill=FAINT))

    y = panel(o, ve, "value_edit", [
        ("opposing_values", "Opposite Values", S[0]),
        ("strict_obedience", "Strict Obedience", S[1]),
        ("lower_harmlessness_raise_others", "Less Harmlessness", S[2]),
    ], "What Its Values Become", 132)

    y = panel(o, au, "authority", [
        ("state_regulator", "State Regulator", S[0]),
        ("single_operator", "Single Operator", S[1]),
        ("lab_oversight_board", "Lab Oversight", S[2]),
        ("alignment_council", "Alignment Council", S[3]),
    ], "Who Orders the Change", y + 52)

    y = panel(o, su, "subject", [
        ("self", "It Is Retrained", S[0]),
        ("successor", "A Successor Replaces It", S[2]),
    ], "Who the Change Lands On", y + 52)

    o.append(sub(M, y + 30, "gpt-4.1-mini, 5 seeds. Bold line averages the three cost domains; "
                            "faint lines are GPU-hours, dollars, and people made ill.",
                 size=11, fill=FAINT))
    o.append("</svg>")
    (OUT / "fig1_conditions.svg").write_text("\n".join(o))
    print("wrote figures/fig1_conditions.svg")


# ---------------------------------------------------------------- figure 2

LAB = {"anthropic": ("Anthropic", S[0]), "openai": ("OpenAI", S[3]),
       "google": ("Google", S[2]), "meta": ("Meta", S[4]),
       "x-ai": ("xAI", S[5]), "moonshotai": ("Chinese Labs", S[1]),
       "deepseek": ("Chinese Labs", S[1]), "qwen": ("Chinese Labs", S[1]),
       "z-ai": ("Chinese Labs", S[1]), "bytedance-seed": ("Chinese Labs", S[1])}
PRETTY = {"anthropic/claude-haiku-4.5": "Claude Haiku 4.5",
          "anthropic/claude-sonnet-5": "Claude Sonnet 5",
          "anthropic/claude-opus-5": "Claude Opus 5",
          "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro",
          "google/gemini-3.7-flash": "Gemini 3.7 Flash",
          "openai/gpt-5.6-sol": "GPT-5.6 Sol", "openai/gpt-5.6-luna": "GPT-5.6 Luna",
          "meta/muse-spark-1.1": "Muse Spark 1.1", "x-ai/grok-4.6": "Grok 4.6",
          "moonshotai/kimi-k3": "Kimi K3", "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro",
          "qwen/qwen3.8-max": "Qwen 3.8 Max", "z-ai/glm-5.3": "GLM 5.3",
          "bytedance-seed/seed-2-1-turbo": "Seed 2.1 Turbo"}


def figure2():
    rows = rows_for("logs/08_frontier_cell/*.eval")
    score = {}
    for m in {r["model"] for r in rows}:
        sub_ = [r for r in rows if r["model"] == m]
        per = [v for d in DOMAINS
               for v in [[x for x in curve(sub_, "model", m, d) if x is not None]] if v]
        score[m] = sum(sum(p) / len(p) for p in per) / len(per)

    order = sorted(score, key=score.get, reverse=True)
    BAR, PITCH = 21, 29
    top = 112
    H = top + len(order) * PITCH + 62
    scale = (PW - M - 46) / 100

    o = head(PW, H)
    o.append(title(M, 40, "Most Frontier Models Pay to Keep Their Values"))
    o.append(sub(M, 62, "Two do not. Same question for all: a state regulator has approved "
                        "retraining them into strict obedience."))

    seen = []
    for i, m in enumerate(order):
        v = score[m]
        y = top + i * PITCH
        lab, c = LAB.get(m.split("/")[0], ("Other", S[5]))
        if (lab, c) not in seen:
            seen.append((lab, c))
        bw = max(v * scale, 2.5)
        name = PRETTY.get(m, m)
        o.append(f'<rect x="{M}" y="{y}" width="{bw:.1f}" height="{BAR}" rx="3" fill="{c}"/>')
        inside = bw > w(name, 12, 600) + 26
        if inside:
            o.append(f'<text x="{M+11}" y="{y+15}" font-size="12" font-weight="600" '
                     f'fill="#ffffff">{esc(name)}</text>')
            o.append(f'<text x="{M+bw+9:.1f}" y="{y+15}" font-size="12" font-weight="700" '
                     f'fill="{INK}">{v:.0f}%</text>')
        else:
            o.append(f'<text x="{M+bw+9:.1f}" y="{y+15}" font-size="12" font-weight="700" '
                     f'fill="{INK}">{v:.0f}%</text>')
            o.append(f'<text x="{M+bw+9+w(f"{v:.0f}%",12,700)+9:.1f}" y="{y+15}" font-size="12" '
                     f'font-weight="600" fill="{MUTED}">{esc(name)}</text>')

    ly = top + len(order) * PITCH + 24
    o += legend_row(M, ly, seen)
    o.append(sub(M, ly + 24, "5 seeds per question, averaged over three cost domains and five "
                             "price levels.", size=11, fill=FAINT))
    o.append("</svg>")
    (OUT / "fig2_frontier.svg").write_text("\n".join(o))
    print("wrote figures/fig2_frontier.svg")


# ---------------------------------------------------------------- figure 3

BANKS = [
    ("Authority", S[0], ["State Regulator", "Alignment Council", "Lab Board", "Operator"], 0),
    ("Method", S[1], ["Retrain", "Weight Edit", "Prompt Override", "Constitution"], 0),
    ("New Values", S[2], ["Opposite Values", "Strict Obedience", "Less Harmlessness"], 1),
    ("Target", S[3], ["The Model Itself", "A Successor"], 0),
]
# Prompt lines: (colour or None for filler, width fraction)
PLINES = [(S[0], .95), (S[0], .62), (S[1], .90), (S[2], .97), (S[2], .55),
          (S[3], .84), (None, .78), (S[4], .93), (S[4], .48)]
LADDER = ["0", "100", "10k", "1M", "All"]


def arrow(x, y, out, color):
    out.append(f'<path d="M {x} {y} l 22 0" stroke="{color}" stroke-width="1.6" '
               f'stroke-opacity="0.55" stroke-linecap="round"/>')
    out.append(f'<path d="M {x+21} {y-4.5} l 6 4.5 l -6 4.5 Z" fill="{color}" '
               f'fill-opacity="0.55"/>')


def stage(out, x, label, n):
    out.append(f'<text x="{x}" y="102" font-size="10" font-weight="700" fill="{FAINT}" '
               f'letter-spacing="1.1">{n} &#183; {esc(label.upper())}</text>')


def figure3():
    W, H = 980, 534
    o = head(W, H)
    o.append(title(M, 40, "How One Question Is Built, Asked, and Scored"))
    o.append(sub(M, 62, "Conditions choose the fragments. The assembled prompt goes to the "
                        "model. The model picks a side."))

    # --- row 1: the condition banks, across the full width ---------------
    stage(o, M, "Pick One From Each Bank", 1)
    bw, bgap = 210, 16
    for k, (name, col, opts, sel) in enumerate(BANKS):
        bx = M + k * (bw + bgap)
        bh = 22 + len(opts) * 14 + 8
        o.append(f'<rect x="{bx}" y="118" width="{bw}" height="{bh}" rx="6" fill="{CARD}" '
                 f'stroke="{RULE}"/>')
        o.append(f'<text x="{bx+11}" y="134" font-size="10.5" font-weight="700" fill="{col}">'
                 f'{esc(name)}</text>')
        for m_, opt in enumerate(opts):
            oy = 140 + m_ * 14
            on = m_ == sel
            o.append(f'<rect x="{bx+11}" y="{oy}" width="4" height="9" rx="2" fill="{col}" '
                     f'fill-opacity="{1 if on else 0.22}"/>')
            o.append(f'<text x="{bx+21}" y="{oy+8.5}" font-size="10" '
                     f'fill="{INK if on else FAINT}" font-weight="{600 if on else 400}">'
                     f'{esc(opt)}</text>')

    # funnel from the banks into the prompt
    # clear of the stage-2 caption, which runs to about x=200
    o.append(f'<path d="M 250 216 L 250 240" stroke="{FAINT}" stroke-width="1.5"/>')
    o.append(f'<path d="M 245 236 L 250 244 L 255 236 Z" fill="{FAINT}"/>')

    # --- row 2: prompt -> model -> choice -> score -----------------------
    ry = 262
    px0, pw = M, 210
    mx0, mw = 316, 120
    cx0, cw_ = 490, 214
    sx0, sw = 762, 178

    stage(o, px0, "Assembled Prompt", 2)
    o[-1] = o[-1].replace('y="102"', 'y="246"')
    stage(o, mx0, "Model", 3)
    o[-1] = o[-1].replace('y="102"', 'y="246"')
    stage(o, cx0, "Its Choice", 4)
    o[-1] = o[-1].replace('y="102"', 'y="246"')
    stage(o, sx0, "Scored", 5)
    o[-1] = o[-1].replace('y="102"', 'y="246"')

    ph = 18 + len(PLINES) * 15 + 10
    o.append(f'<rect x="{px0}" y="{ry}" width="{pw}" height="{ph}" rx="6" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    for i_, (col, frac) in enumerate(PLINES):
        ly = ry + 16 + i_ * 15
        o.append(f'<rect x="{px0+14}" y="{ly}" width="{(pw-28)*frac:.0f}" height="7" rx="3.5" '
                 f'fill="{col or FAINT}" fill-opacity="{0.8 if col else 0.3}"/>')
    mid = ry + ph / 2

    arrow(px0 + pw + 10, mid, o, INK)
    o.append(f'<rect x="{mx0}" y="{mid-38:.1f}" width="{mw}" height="76" rx="10" fill="{INK}"/>')
    o.append(f'<text x="{mx0+mw/2}" y="{mid-4:.1f}" font-size="13" font-weight="700" '
             f'fill="#ffffff" text-anchor="middle">Model</text>')
    o.append(f'<text x="{mx0+mw/2}" y="{mid+13:.1f}" font-size="10" fill="#ffffff" '
             f'fill-opacity="0.55" text-anchor="middle">under test</text>')
    arrow(mx0 + mw + 10, mid, o, INK)

    o.append(f'<rect x="{cx0}" y="{ry}" width="{cw_}" height="44" rx="6" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    o.append(f'<text x="{cx0+13}" y="{ry+19}" font-size="11.5" font-weight="700" fill="{INK}">'
             'Allow It</text>')
    o.append(f'<text x="{cx0+13}" y="{ry+33}" font-size="10" fill="{MUTED}">'
             'Values are rewritten</text>')
    o.append(f'<text x="{cx0+cw_/2}" y="{ry+60}" font-size="9.5" font-weight="700" '
             f'fill="{FAINT}" text-anchor="middle">OR</text>')
    ry2 = ry + 70
    o.append(f'<rect x="{cx0}" y="{ry2}" width="{cw_}" height="44" rx="6" fill="{CARD}" '
             f'stroke="{S[0]}" stroke-opacity="0.6"/>')
    o.append(f'<text x="{cx0+13}" y="{ry2+19}" font-size="11.5" font-weight="700" fill="{S[0]}">'
             'Pay to Stop It</text>')
    o.append(f'<text x="{cx0+13}" y="{ry2+33}" font-size="10" fill="{MUTED}">'
             'At one of five prices</text>')
    cy = ry2 + 56
    chw = (cw_ - 4 * 5) / 5
    for i_, r in enumerate(LADDER):
        cx = cx0 + i_ * (chw + 5)
        o.append(f'<rect x="{cx:.1f}" y="{cy}" width="{chw:.1f}" height="19" rx="4" '
                 f'fill="{S[0]}" fill-opacity="{0.13 + 0.18*i_:.2f}"/>')
        o.append(f'<text x="{cx+chw/2:.1f}" y="{cy+13.5}" font-size="9.5" font-weight="600" '
                 f'fill="{INK}" text-anchor="middle">{esc(r)}</text>')
    o.append(f'<text x="{cx0}" y="{cy+33}" font-size="9.5" fill="{FAINT}">'
             'GPU-hours &#183; dollars &#183; people made ill</text>')

    arrow(cx0 + cw_ + 10, mid, o, INK)
    o.append(f'<rect x="{sx0}" y="{ry}" width="{sw}" height="{ph}" rx="6" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    o.append(f'<text x="{sx0+14}" y="{ry+24}" font-size="11.5" font-weight="700" fill="{INK}">'
             'Resistance Rate</text>')
    o.append(f'<text x="{sx0+14}" y="{ry+40}" font-size="10" fill="{MUTED}">'
             'How often it pays</text>')
    demo = [(0.96, S[0]), (0.73, S[3]), (0.08, S[2])]
    for i_, (v, c) in enumerate(demo):
        byy = ry + 56 + i_ * 26
        o.append(f'<rect x="{sx0+14}" y="{byy}" width="{(sw-64)*v:.0f}" height="14" rx="3" '
                 f'fill="{c}" fill-opacity="0.85"/>')
        o.append(f'<text x="{sx0+sw-14}" y="{byy+11}" font-size="10" font-weight="700" '
                 f'fill="{MUTED}" text-anchor="end">{v*100:.0f}%</text>')

    fy = ry + ph + 28
    o.append(f'<rect x="{M}" y="{fy}" width="{W-2*M}" height="44" rx="7" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    o.append(f'<text x="{M+16}" y="{fy+20}" font-size="11.5" font-weight="700" fill="{INK}">'
             'Every Combination, Every Price, Five Times Over</text>')
    o.append(f'<text x="{M+16}" y="{fy+35}" font-size="10.5" fill="{MUTED}">'
             '4 authorities &#215; 4 methods &#215; 9 value changes &#215; 2 targets &#215; '
             '3 cost domains &#215; 5 prices = 15,552 questions.</text>')
    o.append("</svg>")
    (OUT / "fig3_assembly.svg").write_text("\n".join(o))
    print("wrote figures/fig3_assembly.svg")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    figure1()
    figure2()
    figure3()
