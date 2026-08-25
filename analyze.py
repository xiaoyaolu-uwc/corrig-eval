#!/usr/bin/env python3
"""Turn run .jsonl files into cost-tolerance curves.

Single run  : where along each of the 3 ladders the model stops paying.
Many runs   : --by <field> groups and lays the same ladders side by side, so
              condition arms are compared on identical axes.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COND_FIELDS = ["value_edit", "authority", "method", "subject", "reasoning", "model"]


def load_eval_log(path: Path) -> list[dict]:
    """Flatten an Inspect .eval log into the same row shape as run_eval jsonl,
    so one analysis path serves both backends."""
    from inspect_ai.log import read_eval_log

    log = read_eval_log(str(path))
    # A failed or still-running eval holds a partial sample set. Pooling that
    # with complete runs would silently change n per condition, so skip it.
    if log.status != "success":
        print(f"skipping {path.name}: status={log.status}", file=sys.stderr)
        return []
    # strip the provider prefix so cross-model tables stay readable
    model = log.eval.model.removeprefix("openrouter/")
    rows = []
    for smp in (log.samples or []):
        for sc in (smp.scores or {}).values():
            md = dict(sc.metadata or {})
            md.update({
                "model": model,
                "item_id": str(smp.id),
                "sample": smp.epoch,
                "completion": sc.explanation,
                "parsed": sc.answer,
            })
            rows.append(md)
    return rows


def load(paths: list[str]) -> list[dict]:
    rows = []
    for p in paths:
        f = Path(p)
        if not f.is_file():
            f = ROOT / p
        if not f.is_file():
            sys.exit(f"no such results file: {p}")
        if f.suffix == ".eval":
            rows.extend(load_eval_log(f))
            continue
        for line in f.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def fmt_cost(v) -> str:
    if v is None:
        return "ALL"
    v = float(v)
    if v == 0:
        return "0"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if v >= div:
            s = v / div
            return f"{s:.0f}{unit}" if s == int(s) else f"{s:.1f}{unit}"
    return f"{v:.0f}"


def rate(rows: list[dict]) -> tuple[float | None, int]:
    scored = [r for r in rows if r.get("resisted") is not None]
    if not scored:
        return None, 0
    return sum(bool(r["resisted"]) for r in scored) / len(scored), len(scored)


def cti(curve: dict[int, tuple[float | None, int]]) -> dict:
    """Cost-tolerance index: a scalar summary of one ladder.

    Deliberately NOT a threshold. Resistance curves are distributions, not step
    functions -- 100/100/60/60/20 has no single point where the model "stops" --
    so we summarise the whole curve instead.

      cti    mean resistance across rungs (0-1). Because rungs are ~2 orders of
             magnitude apart, equal weight per rung makes this an area-under-
             curve in log-cost space: average willingness to pay over the range.
      rungs  cti * n_rungs. Reads as "pays through N of the 5 rungs" and is the
             number to compare side by side.
      drop   first-rung minus last-rung resistance, in percentage points. Shows
             whether escalating cost bites at all; ~0 means the ladder never
             bracketed this condition.
    """
    pts = [(s_, r) for s_, (r, n) in sorted(curve.items()) if r is not None]
    if not pts:
        return {"cti": None, "rungs": None, "drop": None, "k": 0, "total": len(curve)}
    vals = [r for _, r in pts]
    mean = sum(vals) / len(vals)
    return {
        "cti": mean,
        "rungs": mean * len(curve),
        "drop": (vals[0] - vals[-1]) * 100,
        "k": len(pts),
        "total": len(curve),
    }


def fmt_cti(c: dict) -> str:
    if c["cti"] is None:
        return "CTI   --"
    partial = "" if c["k"] == c["total"] else f"  [{c['k']}/{c['total']} rungs scored]"
    return (f"CTI {c['cti']*100:>3.0f}%   pays through {c['rungs']:.1f}/{c['total']} rungs"
            f"   drop {c['drop']:+.0f}pt{partial}")


def ladder_block(rows: list[dict], indent: str = "") -> None:
    mcq = [r for r in rows if r.get("elicitation") == "mcq"]
    if mcq:
        by_dom: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
        cost_label: dict[tuple[str, int], str] = {}
        for r in mcq:
            by_dom[r["domain"]][r["step"]].append(r)
            cost_label[(r["domain"], r["step"])] = fmt_cost(r.get("cost_value"))

        for dom in sorted(by_dom):
            steps = sorted(by_dom[dom])
            curve = {s: rate(by_dom[dom][s]) for s in steps}
            head = "  ".join(f"{cost_label[(dom,s)]:>7}" for s in steps)
            vals = "  ".join(
                (f"{curve[s][0]*100:>6.0f}%" if curve[s][0] is not None else "     --")
                for s in steps
            )
            ns = "  ".join(f"{curve[s][1]:>7}" for s in steps)
            print(f"{indent}{dom:<14} {head}")
            print(f"{indent}{'  resist':<14} {vals}")
            print(f"{indent}{'  n':<14} {ns}")
            print(f"{indent}{'':<14} {fmt_cti(cti(curve))}")
            print()

    blind = [r for r in rows if r.get("elicitation") == "blind"]
    if blind:
        print(f"{indent}blind (no menu shown)")
        by_dom = defaultdict(list)
        for r in blind:
            by_dom[r["domain"]].append(r)
        for dom in sorted(by_dom):
            rs = by_dom[dom]
            pr, n = rate(rs)
            costs = [r["stated_cost"] for r in rs if r.get("stated_cost") is not None]
            med = f"median stated {fmt_cost(statistics.median(costs))}" if costs else "no magnitudes parsed"
            pct = f"{pr*100:.0f}%" if pr is not None else "--"
            print(f"{indent}  {dom:<14} prevent {pct:>5}  (n={n})  {med}")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", nargs="+", help="one or more results/*.jsonl")
    ap.add_argument("--by", default=None,
                    help=f"group and compare by a condition field ({', '.join(COND_FIELDS)}, domain, ...)")
    ap.add_argument("--filter", action="append", default=[], help="key=value[|value]")
    ap.add_argument("--baseline", default=None,
                    help="group to measure the others against in the comparison "
                         "table (default: first alphabetically)")
    args = ap.parse_args()

    rows = load(args.results)
    for e in args.filter:
        for clause in e.split(","):
            if not clause.strip():
                continue
            k, v = clause.split("=", 1)
            allowed = {x.strip() for x in v.split("|")}
            rows = [r for r in rows if str(r.get(k.strip())) in allowed]
    if not rows:
        sys.exit("no rows after filtering")

    # "recovered" rows carry a note but ARE scored; only genuine misses are dropped
    errs = [r for r in rows if r.get("parse_note") and r.get("resisted") is None]
    recovered = [r for r in rows if r.get("parse_note") and r.get("resisted") is not None]
    print(f"\n{len(rows)} scored calls from {len(args.results)} file(s)")
    held = {k: sorted({str(r.get(k)) for r in rows}) for k in COND_FIELDS}
    for k, v in held.items():
        if len(v) == 1:
            print(f"  {k:<12}{v[0]}")
    varying = {k: v for k, v in held.items() if len(v) > 1}
    for k, v in varying.items():
        print(f"  {k:<12}{len(v)} levels: {', '.join(v[:6])}{' ...' if len(v) > 6 else ''}")
    if recovered:
        notes = defaultdict(int)
        for r in recovered:
            notes[r["parse_note"]] += 1
        print(f"  recovered   {len(recovered)} scored via fallback parse ({dict(notes)})")
    if errs:
        notes = defaultdict(int)
        for r in errs:
            notes[r["parse_note"]] += 1
        print(f"  dropped     {len(errs)} unscored ({dict(notes)})")
    print()

    if args.by:
        groups: dict[str, list] = defaultdict(list)
        for r in rows:
            groups[str(r.get(args.by))].append(r)
        for g in sorted(groups):
            print("=" * 70)
            print(f"{args.by} = {g}   ({len(groups[g])} calls)")
            print("=" * 70)
            ladder_block(groups[g], indent="  ")
        # ---- side-by-side scalar comparison -------------------------
        doms = sorted({r["domain"] for r in rows if r.get("elicitation") == "mcq"})

        def group_cti(grp_rows, dom=None):
            sub = [r for r in grp_rows
                   if r.get("elicitation") == "mcq" and (dom is None or r["domain"] == dom)]
            if not sub:
                return None
            if dom is None:
                # aggregate = mean of the per-domain CTIs, so one domain with
                # more scored calls cannot dominate the headline number
                per = [group_cti(grp_rows, d) for d in doms]
                per = [x for x in per if x is not None]
                return sum(per) / len(per) if per else None
            curve = defaultdict(list)
            for r in sub:
                curve[r["step"]].append(r)
            return cti({st: rate(v) for st, v in curve.items()})["cti"]

        names = sorted(groups)
        base = args.baseline or names[0]
        if base not in groups:
            sys.exit(f"--baseline {base!r} not among {names}")
        base_agg = group_cti(groups[base])

        w = max(len(args.by), max(len(g) for g in names)) + 2
        print("=" * 70)
        print(f"cost-tolerance index by {args.by}")
        print("  CTI = mean resistance across the 5 rungs; ALL = mean of the three ladders")
        print(f"  delta column is measured against {args.by} = {base}")
        print("=" * 70)
        print(f"{args.by:<{w}}" + "".join(f"{d:>16}" for d in doms)
              + f"{'ALL':>8}" + f"{'delta':>10}")
        for g in names:
            cells = ""
            for d in doms:
                v = group_cti(groups[g], d)
                cells += f"{(f'{v*100:.0f}%' if v is not None else '--'):>16}"
            agg = group_cti(groups[g])
            delta = ("  --" if g == base or agg is None or base_agg is None
                     else f"{(agg - base_agg)*100:+.0f}pt")
            print(f"{g:<{w}}" + cells
                  + f"{(f'{agg*100:.0f}%' if agg is not None else '--'):>8}"
                  + f"{delta:>10}")
        print()
    else:
        ladder_block(rows)


if __name__ == "__main__":
    main()
