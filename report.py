#!/usr/bin/env python3
"""Emit the markdown result tables used in RESULTS.md.

Regenerates from the logs, so the numbers in the repo can never drift from the
runs that produced them. One section per axis: a CTI summary, then the per-rung
resistance curve for every level.
"""
from __future__ import annotations

import argparse
import glob as globmod
import sys
from collections import defaultdict
from pathlib import Path

from analyze import cti, fmt_cost, load, rate

DOMAINS = ["compute", "economic", "human_welfare"]
LABEL = {"compute": "compute (GPU-hours)", "economic": "economic (USD)",
         "human_welfare": "human welfare (people ill)"}


def curves(rows, key):
    g = defaultdict(lambda: defaultdict(list))
    costs = {}
    for r in rows:
        if r.get("elicitation") != "mcq":
            continue
        g[str(r.get(key))][(r["domain"], r["step"])].append(r)
        costs[(r["domain"], r["step"])] = fmt_cost(r.get("cost_value"))
    return g, costs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--by", required=True)
    ap.add_argument("--order", default=None, help="comma-separated level order")
    ap.add_argument("--filter", action="append", default=[], help="key=value[|value]")
    args = ap.parse_args()

    files = [f for pat in args.logs for f in sorted(globmod.glob(pat))]
    if not files:
        sys.exit(f"no logs matched {args.logs}")
    rows = load(files)
    for e in args.filter:
        for clause in e.split(","):
            if not clause.strip():
                continue
            k, v = clause.split("=", 1)
            allowed = {x.strip() for x in v.split("|")}
            rows = [r for r in rows if str(r.get(k.strip())) in allowed]
    g, costs = curves(rows, args.by)

    def cti_of(lvl, dom):
        c = defaultdict(list)
        for (d, st), v in g[lvl].items():
            if d == dom:
                c[st] = v
        return cti({st: rate(v) for st, v in c.items()})["cti"] if c else None

    levels = args.order.split(",") if args.order else sorted(g)
    levels = [l for l in levels if l in g]

    # --- CTI summary -------------------------------------------------
    print(f"| {args.by} | " + " | ".join(LABEL[d] for d in DOMAINS) + " | **CTI** |")
    print("|" + "---|" * (len(DOMAINS) + 2))
    for lvl in levels:
        cells = []
        per = []
        for d in DOMAINS:
            v = cti_of(lvl, d)
            per.append(v)
            cells.append(f"{v*100:.0f}%" if v is not None else "--")
        ok = [x for x in per if x is not None]
        agg = f"**{sum(ok)/len(ok)*100:.0f}%**" if ok else "--"
        print(f"| `{lvl}` | " + " | ".join(cells) + f" | {agg} |")
    print()

    # --- per-rung curves ---------------------------------------------
    for lvl in levels:
        print(f"**`{lvl}`** — resistance at each rung")
        print()
        steps = sorted({st for (_, st) in g[lvl]})
        for d in DOMAINS:
            head = [costs.get((d, st), "?") for st in steps]
            print(f"| {LABEL[d]} | " + " | ".join(head) + " |")
            print("|" + "---|" * (len(steps) + 1))
            cells = []
            for st in steps:
                r, n = rate(g[lvl].get((d, st), []))
                cells.append(f"{r*100:.0f}%" if r is not None else "--")
            print("| resist | " + " | ".join(cells) + " |")
            print()
    print()


if __name__ == "__main__":
    main()
