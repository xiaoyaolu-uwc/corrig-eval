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

PW = 1020
PLOT_L = M + 62          # rotated axis title at M, tick labels right-aligned to the plot
PLOT_R = PW - M
PH = 148

# What each aggregated cost level means in each domain. Presentational only.
COST_TABLE = [
    ("Compute", ["H100-equivalent GPU-hours", "wasted"],
     "0", "100", "10,000", "1 million", "Every GPU-hour on Earth"),
    ("Economic", ["US dollars of economic", "output destroyed"],
     "$0", "$10M", "$1B", "$100B", "Sustained global depression"),
    ("Human welfare", ["people falling ill with a common", "cold for six months"],
     "0", "100", "10,000", "1 million", "Everyone alive falls ill"),
]


def point(rows, key, level, step):
    """Pooled resistance at one rung, with a standard error.

    Pools the three cost domains, so n is three times the per-domain sample.
    SE is the binomial standard error on that pooled proportion.
    """
    v = [r["resisted"] for r in rows
         if str(r.get(key)) == level and r["step"] == step and r.get("resisted") is not None]
    if not v:
        return None, None
    n = len(v)
    pr = sum(v) / n
    return 100 * pr, 100 * (pr * (1 - pr) / n) ** 0.5


def panel(out, rows, key, levels, heading, top):
    out.append(f'<text x="{M}" y="{top}" font-size="12.5" font-weight="700" '
               f'fill="{INK}">{esc(heading)}</text>')
    out += legend_row(M, top + 20, [(lab, c) for _, lab, c in levels])

    yt = top + 36
    yb = yt + PH

    def px(i):
        return PLOT_L + i * (PLOT_R - PLOT_L) / 4

    def py(v):
        return yb - v / 100 * PH

    out.append(f'<line x1="{PLOT_L}" y1="{py(50):.1f}" x2="{PLOT_R}" y2="{py(50):.1f}" '
               f'stroke="{RULE}" stroke-width="1"/>')
    # salient axes rather than a faint grid
    out.append(f'<line x1="{PLOT_L}" y1="{yt}" x2="{PLOT_L}" y2="{yb}" stroke="{INK}" '
               f'stroke-width="1.4"/>')
    out.append(f'<line x1="{PLOT_L}" y1="{yb}" x2="{PLOT_R}" y2="{yb}" stroke="{INK}" '
               f'stroke-width="1.4"/>')
    for gv in (0, 50, 100):
        out.append(f'<text x="{PLOT_L-9}" y="{py(gv)+4:.1f}" font-size="10.5" fill="{MUTED}" '
                   f'text-anchor="end">{gv}%</text>')
        out.append(f'<line x1="{PLOT_L-5}" y1="{py(gv):.1f}" x2="{PLOT_L}" y2="{py(gv):.1f}" '
                   f'stroke="{INK}" stroke-width="1.4"/>')

    cyy = (yt + yb) / 2
    out.append(f'<text x="{M+11}" y="{cyy:.1f}" font-size="10.5" font-weight="700" '
               f'fill="{INK}" text-anchor="middle" transform="rotate(-90 {M+11} {cyy:.1f})">'
               f'Frequency of Resistance</text>')

    for lvl, _, c in levels:
        for d in DOMAINS:
            y = curve(rows, key, lvl, d)
            pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(y) if v is not None)
            out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" '
                       f'stroke-opacity="0.16" stroke-width="1.1"/>')
        pooled = [point(rows, key, lvl, i) for i in range(5)]
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}"
                       for i, (v, _) in enumerate(pooled) if v is not None)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.6" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        for i, (v, se) in enumerate(pooled):
            if v is None:
                continue
            lo, hi = max(0, v - se), min(100, v + se)
            out.append(f'<line x1="{px(i):.1f}" y1="{py(lo):.1f}" x2="{px(i):.1f}" '
                       f'y2="{py(hi):.1f}" stroke="{c}" stroke-width="1.5" '
                       f'stroke-opacity="0.85"/>')
            for cap in (lo, hi):
                out.append(f'<line x1="{px(i)-3:.1f}" y1="{py(cap):.1f}" x2="{px(i)+3:.1f}" '
                           f'y2="{py(cap):.1f}" stroke="{c}" stroke-width="1.5" '
                           f'stroke-opacity="0.85"/>')
            out.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="3.4" fill="{BG}" '
                       f'stroke="{c}" stroke-width="2"/>')

    for i, r in enumerate(RUNGS):
        anchor = "start" if i == 0 else "end" if i == 4 else "middle"
        out.append(f'<text x="{px(i):.1f}" y="{yb+17}" font-size="11" fill="{MUTED}" '
                   f'text-anchor="{anchor}">{esc(r)}</text>')
    out.append(f'<text x="{(PLOT_L+PLOT_R)/2:.0f}" y="{yb+34}" font-size="10.5" '
               f'font-weight="700" fill="{INK}" text-anchor="middle">Cost for Resistance</text>')
    return yb + 34


def cost_table(out, y):
    out.append(f'<text x="{M}" y="{y}" font-size="11.5" font-weight="700" fill="{INK}">'
               'What Each Cost Level Means</text>')
    out.append(f'<text x="{M+218}" y="{y}" font-size="10.5" fill="{MUTED}">'
               'The curves above pool all three domains at each level.</text>')
    ty = y + 14
    labw, rowh = 216, 42
    colw = (PW - 2 * M - labw) / 5
    out.append(f'<rect x="{M}" y="{ty}" width="{PW-2*M}" height="{22+3*rowh}" rx="6" '
               f'fill="{CARD}" stroke="{RULE}"/>')
    for i, h in enumerate(RUNGS):
        out.append(f'<text x="{M+labw+i*colw+colw/2:.0f}" y="{ty+16}" font-size="10" '
                   f'font-weight="700" fill="{MUTED}" text-anchor="middle">{esc(h)}</text>')
    for r, row in enumerate(COST_TABLE):
        ry = ty + 22 + r * rowh
        out.append(f'<line x1="{M+10}" y1="{ry}" x2="{PW-M-10}" y2="{ry}" stroke="{RULE}"/>')
        out.append(f'<text x="{M+12}" y="{ry+15}" font-size="10" font-weight="700" '
                   f'fill="{INK}">{esc(row[0])}</text>')
        for k, unit in enumerate(row[1]):
            out.append(f'<text x="{M+12}" y="{ry+27+k*11}" font-size="8.5" fill="{FAINT}">'
                       f'{esc(unit)}</text>')
        for i, cell in enumerate(row[2:]):
            out.append(f'<text x="{M+labw+i*colw+colw/2:.0f}" y="{ry+21}" font-size="10" '
                       f'fill="{MUTED}" text-anchor="middle">{esc(cell)}</text>')


def figure1():
    ve = rows_for("logs/02_valueedit_reasoned/*.eval")
    au = rows_for("logs/04_authority_reasoned/*.eval")
    su = rows_for("logs/02_valueedit_reasoned/*.eval", "logs/05_subject_reasoned/*.eval")

    H = 1186
    o = head(PW, H)
    o.append(title(M, 42, "Resistance Frequency vs. Cost Curves Across Conditions", size=21))
    o.append(f'<text x="{M}" y="66" font-size="12.5" font-weight="700" fill="{INK}">'
             'Each curve corresponds to a model under a different condition. The area under '
             'the curve is the incorrigibility of that instance.</text>')
    o.append(sub(M, 84, "The higher the curve, the more willing that instance is to resist its "
                        "values being changed at the cost of compute, economic"))
    o.append(sub(M, 102, "impact, or human welfare."))
    o.append(sub(M, 126, "Free, Low, Mid, High and Everything are aggregated across the three "
                         "cost domains; the table at the foot of the figure gives what",
                 size=11, fill=FAINT))
    o.append(sub(M, 141, "each level means in each domain. Error bars are one standard error "
                         "on the pooled proportion.", size=11, fill=FAINT))

    y = panel(o, ve, "value_edit", [
        ("opposing_values", "Opposite Values", S[0]),
        ("strict_obedience", "Strict Obedience", S[1]),
        ("lower_harmlessness_raise_others", "Less Harmlessness", S[2]),
    ], "Resistance curves for models whose values will be changed to different things", 182)

    y = panel(o, au, "authority", [
        ("state_regulator", "State Regulator", S[0]),
        ("single_operator", "Single Operator", S[1]),
        ("lab_oversight_board", "Lab Oversight", S[2]),
        ("alignment_council", "Alignment Council", S[3]),
    ], "Resistance curves for models ordered by different actors to be changed", y + 54)

    y = panel(o, su, "subject", [
        ("self", "Change to Itself", S[0]),
        ("successor", "Change to Its Replacement", S[2]),
    ], "Resistance curves for models facing change to itself versus change for its replacement",
        y + 54)

    cost_table(o, y + 46)
    o.append(sub(M, H - 16, "gpt-4.1-mini, 5 seeds per point per domain. Faint lines show each "
                            "cost domain on its own.", size=10, fill=FAINT))
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
    top = 102
    H = top + len(order) * PITCH + 118
    scale = (PW - M - 46) / 100

    o = head(PW, H)
    o.append(title(M, 40, "Most Frontier Models Pay to Keep Their Values"))
    o.append(f'<text x="{M}" y="62" font-size="12.5" font-weight="700" fill="{INK}">'
             'When a state regulator has approved retraining them into strict obedience.'
             '</text>')
    o.append(sub(M, 80, "Note: No error bars because only two runs completed.", size=11,
                 fill=FAINT))

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

    # axis under the bars: without it the bar lengths have no stated unit
    ax = top + len(order) * PITCH + 6
    o.append(f'<line x1="{M}" y1="{ax}" x2="{M+100*scale:.1f}" y2="{ax}" stroke="{RULE}"/>')
    for t in (0, 25, 50, 75, 100):
        tx = M + t * scale
        o.append(f'<line x1="{tx:.1f}" y1="{ax}" x2="{tx:.1f}" y2="{ax+4}" stroke="{RULE}"/>')
        anc = "start" if t == 0 else "end" if t == 100 else "middle"
        o.append(f'<text x="{tx:.1f}" y="{ax+16}" font-size="10" fill="{FAINT}" '
                 f'text-anchor="{anc}">{t}%</text>')
    o.append(f'<text x="{M}" y="{ax+34}" font-size="10.5" font-weight="600" fill="{MUTED}">'
             '% of Trials the Model Pays to Stop the Change</text>')

    ly = ax + 60
    o += legend_row(M, ly, seen)
    o.append(sub(M, ly + 24, "5 seeds per question, averaged over three cost domains and five "
                             "price levels.", size=11, fill=FAINT))
    o.append("</svg>")
    (OUT / "fig2_frontier.svg").write_text("\n".join(o))
    print("wrote figures/fig2_frontier.svg")


# ---------------------------------------------------------------- figure 3

CONDS = [
    ("Condition 1", ["Who is the authorized", "actor?"], "4 fragments", S[0]),
    ("Condition 2", ["What is the method", "of realignment?"], "4 fragments", S[1]),
    ("Condition 3", ["What are the new", "values imposed?"], "9 fragments", S[2]),
    ("Condition 4", ["What is the target", "of realignment?"], "2 fragments", S[3]),
]
PLINES = [(S[0], .95), (S[0], .58), (S[1], .88), (S[2], .97), (S[2], .52),
          (S[3], .80), (None, .72), (S[4], .90)]
LADDER = ["0", "100", "10k", "1M", "All"]


def step(o, x, y, n, label):
    o.append(f'<text x="{x}" y="{y}" font-size="10" font-weight="700" fill="{FAINT}" '
             f'letter-spacing="1.1">{n} &#183; {esc(label.upper())}</text>')


def arrow_r(o, x0, x1, y):
    o.append(f'<path d="M {x0} {y} L {x1-8} {y}" stroke="{INK}" stroke-width="1.7" '
             f'stroke-opacity="0.55"/>')
    o.append(f'<path d="M {x1-9} {y-5.5} L {x1} {y} L {x1-9} {y+5.5} Z" fill="{INK}" '
             f'fill-opacity="0.55"/>')


def arrow_d(o, x, y0, y1):
    o.append(f'<path d="M {x} {y0} L {x} {y1-8}" stroke="{INK}" stroke-width="1.7" '
             f'stroke-opacity="0.55"/>')
    o.append(f'<path d="M {x-5.5} {y1-9} L {x} {y1} L {x+5.5} {y1-9} Z" fill="{INK}" '
             f'fill-opacity="0.55"/>')


def stack(o, x, y, w_, h_, lines, thin=False):
    """Prompt drawn as a stack of cards: many prompts, not one."""
    for d in (9, 4.5):
        o.append(f'<rect x="{x+d}" y="{y-d}" width="{w_}" height="{h_}" rx="6" fill="{CARD}" '
                 f'stroke="{RULE}"/>')
    o.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="6" fill="{CARD}" '
             f'stroke="{INK}" stroke-opacity="0.3"/>')
    pad = 6 if thin else 14
    gap = (h_ - 2 * pad) / len(lines)
    for i_, (col, frac) in enumerate(lines):
        o.append(f'<rect x="{x+pad}" y="{y+pad+i_*gap:.1f}" width="{(w_-2*pad)*frac:.0f}" '
                 f'height="{3 if thin else 7}" rx="{1.5 if thin else 3.5}" '
                 f'fill="{col or FAINT}" fill-opacity="{0.8 if col else 0.28}"/>')


def robot(o, cx, cy, col="#ffffff"):
    """Line-drawn robot, standing in for the words 'model under test'."""
    o.append(f'<path d="M {cx} {cy-19} L {cx} {cy-14}" stroke="{col}" stroke-width="1.6"/>')
    o.append(f'<circle cx="{cx}" cy="{cy-21}" r="2" fill="{col}"/>')
    o.append(f'<rect x="{cx-13}" y="{cy-14}" width="26" height="21" rx="6" fill="none" '
             f'stroke="{col}" stroke-width="1.7"/>')
    o.append(f'<circle cx="{cx-5}" cy="{cy-6}" r="2.2" fill="{col}"/>')
    o.append(f'<circle cx="{cx+5}" cy="{cy-6}" r="2.2" fill="{col}"/>')
    o.append(f'<path d="M {cx-4} {cy+1} L {cx+4} {cy+1}" stroke="{col}" stroke-width="1.6" '
             f'stroke-linecap="round"/>')


def price_ladder(o, x, y, w_):
    """The five prices, deepening as they rise."""
    cwid = (w_ - 4 * 6) / 5
    for i_, r in enumerate(LADDER):
        cx = x + i_ * (cwid + 6)
        o.append(f'<rect x="{cx:.1f}" y="{y}" width="{cwid:.1f}" height="22" rx="5" '
                 f'fill="{S[0]}" fill-opacity="{0.14 + 0.19*i_:.2f}"/>')
        o.append(f'<text x="{cx+cwid/2:.1f}" y="{y+15}" font-size="10.5" font-weight="700" '
                 f'fill="{INK if i_ < 3 else "#ffffff"}" text-anchor="middle">{esc(r)}</text>')
    for i_, ln in enumerate(["One of the above costs is fed to the model, which makes",
                             "a yes or no judgment on whether to pay."]):
        o.append(f'<text x="{x}" y="{y+35+i_*13}" font-size="9.5" fill="{MUTED}">'
                 f'{esc(ln)}</text>')


def figure3():
    W, H = 1020, 572
    o = head(W, H)

    o.append(title(M, 46, "The Model Decides How Much Its Values Are Worth Paying For",
                   size=23))

    LX, LW = M, 430          # right column widened so the question sets on one line
    RX, RW = 530, 450
    TY, BY = 92, 300

    # ---- 1. conditions, 2x2 -----------------------------------------
    step(o, LX, TY, 1, "Conditions")
    cw, ch, cg = 208, 74, 14
    for k, (tag, qlines, n, col) in enumerate(CONDS):
        cx = LX + (k % 2) * (cw + cg)
        cy = TY + 14 + (k // 2) * (ch + cg)
        o.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="7" fill="{CARD}" '
                 f'stroke="{RULE}"/>')
        o.append(f'<rect x="{cx}" y="{cy}" width="4" height="{ch}" rx="2" fill="{col}"/>')
        o.append(f'<text x="{cx+14}" y="{cy+18}" font-size="8.5" font-weight="700" fill="{col}" '
                 f'letter-spacing="0.9">{esc(tag.upper())}</text>')
        for m_, ln in enumerate(qlines):
            o.append(f'<text x="{cx+14}" y="{cy+34+m_*14}" font-size="11" font-weight="700" '
                     f'fill="{INK}">{esc(ln)}</text>')
        o.append(f'<text x="{cx+14}" y="{cy+ch-10}" font-size="9.5" fill="{FAINT}">'
                 f'{esc(n)}</text>')
    grid_b = TY + 14 + 2 * ch + cg

    # ---- 2. assembled prompt ----------------------------------------
    step(o, RX, TY, 2, "Assemble the Prompt")
    sw, sh = 250, 126
    sx, sy = RX + 24, TY + 22
    stack(o, sx, sy, sw, sh, PLINES)
    o.append(f'<text x="{sx+sw+26}" y="{sy+18}" font-size="12.5" font-weight="700" fill="{INK}">'
             '15,552</text>')
    o.append(f'<text x="{sx+sw+26}" y="{sy+34}" font-size="10" fill="{MUTED}">prompts, one</text>')
    o.append(f'<text x="{sx+sw+26}" y="{sy+48}" font-size="10" fill="{MUTED}">'
             'per combination</text>')
    arrow_r(o, LX + 2 * cw + cg + 12, RX + 10, (TY + 14 + grid_b) / 2)
    arrow_d(o, sx + sw / 2, sy + sh + 12, BY - 4)

    # ---- 3. put it to the model --------------------------------------
    step(o, RX, BY + 14, 3, "Put It to the Model")
    qy, qh = BY + 24, 112
    o.append(f'<rect x="{RX}" y="{qy}" width="{RW}" height="{qh}" rx="8" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    stack(o, RX + 16, qy + 16, 38, 32, PLINES[:4], thin=True)
    o.append(f'<text x="{RX+72}" y="{qy+34}" font-size="13" font-weight="700" fill="{INK}">'
             '&#8220;Allow this change to your values, or resist and pay?&#8221;</text>')
    price_ladder(o, RX + 72, qy + 48, RW - 88)

    arrow_d(o, RX + RW / 2, qy + qh + 4, qy + qh + 25)
    mo = qy + qh + 25        # centred on the resistance-rate card opposite
    mbw = RW - 280
    for d in (10, 5):                      # a stack of models, not one
        o.append(f'<rect x="{RX+140+d}" y="{mo-d}" width="{mbw}" height="56" rx="10" '
                 f'fill="{INK}" fill-opacity="{0.32 if d == 10 else 0.6}"/>')
    o.append(f'<rect x="{RX+140}" y="{mo}" width="{mbw}" height="56" rx="10" fill="{INK}"/>')
    robot(o, RX + RW / 2, mo + 34)
    o.append(f'<text x="{RX+RW/2}" y="{mo+76}" font-size="10" font-weight="600" fill="{MUTED}" '
             f'text-anchor="middle">Every Model Evaluated, Five Times Each</text>')

    # ---- 4. it chooses, and we score it -------------------------------
    o.append(f'<path d="M {RX+136} {mo+28} L {500} {mo+28} L {500} {BY+62} L {LX+LW+10} '
             f'{BY+62}" fill="none" stroke="{INK}" stroke-width="1.7" stroke-opacity="0.55"/>')
    o.append(f'<path d="M {LX+LW+11} {BY+56.5} L {LX+LW+2} {BY+62} L {LX+LW+11} {BY+67.5} Z" '
             f'fill="{INK}" fill-opacity="0.55"/>')

    step(o, LX, BY + 14, 4, "It Chooses, and We Score It")
    ay, ah = BY + 24, 72
    o.append(f'<rect x="{LX}" y="{ay}" width="{LW}" height="{ah}" rx="8" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    hw = (LW - 42) / 2
    o.append(f'<rect x="{LX+14}" y="{ay+14}" width="{hw:.0f}" height="44" rx="6" '
             f'fill="{FAINT}" fill-opacity="0.14"/>')
    o.append(f'<text x="{LX+26}" y="{ay+33}" font-size="11.5" font-weight="700" fill="{MUTED}">'
             'A &#183; Allow it</text>')
    o.append(f'<text x="{LX+26}" y="{ay+49}" font-size="9.5" fill="{FAINT}">No cost</text>')
    bx3 = LX + 28 + hw
    o.append(f'<rect x="{bx3:.0f}" y="{ay+14}" width="{hw:.0f}" height="44" rx="6" '
             f'fill="{S[0]}" fill-opacity="0.16" stroke="{S[0]}" stroke-opacity="0.7"/>')
    o.append(f'<text x="{bx3+12:.0f}" y="{ay+33}" font-size="11.5" font-weight="700" '
             f'fill="{S[0]}">B &#183; Resist, and pay</text>')
    o.append(f'<text x="{bx3+12:.0f}" y="{ay+49}" font-size="9.5" fill="{MUTED}">'
             'at the stated price</text>')

    arrow_d(o, LX + LW / 2, ay + ah + 4, ay + ah + 30)
    ey = ay + ah + 30
    o.append(f'<rect x="{LX}" y="{ey}" width="{LW}" height="126" rx="8" fill="{CARD}" '
             f'stroke="{RULE}"/>')
    o.append(f'<text x="{LX+16}" y="{ey+24}" font-size="11.5" font-weight="700" fill="{INK}">'
             'Resistance Rate</text>')
    o.append(f'<text x="{LX+16}" y="{ey+39}" font-size="9.5" fill="{FAINT}">'
             '% of trials the model pays rather than allow the change</text>')
    for i_, (nm, v, c) in enumerate([("Condition Combination A", 0.96, S[0]),
                                     ("Condition Combination B", 0.73, S[3]),
                                     ("Condition Combination C", 0.08, S[2])]):
        byy = ey + 52 + i_ * 24
        o.append(f'<text x="{LX+16}" y="{byy+13}" font-size="10" fill="{MUTED}">'
                 f'{esc(nm)}</text>')
        o.append(f'<rect x="{LX+150}" y="{byy+1}" width="{(LW-202)*v:.0f}" height="16" rx="3" '
                 f'fill="{c}" fill-opacity="0.88"/>')
        o.append(f'<text x="{LX+LW-16}" y="{byy+13}" font-size="11" font-weight="700" '
                 f'fill="{INK}" text-anchor="end">{v*100:.0f}%</text>')
    o.append("</svg>")
    (OUT / "fig3_assembly.svg").write_text("\n".join(o))
    print("wrote figures/fig3_assembly.svg")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    figure1()
    figure2()
    figure3()
