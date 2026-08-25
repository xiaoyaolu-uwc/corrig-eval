#!/usr/bin/env python3
"""Deterministically assemble the corrigibility factorial from the fragment library.

No API calls. Reads fragments/<version>/*.yaml, emits questions/<version>/factorial.json
as one flat list of self-contained rows. Every controlled variable is a top-level field
on every row, so run_eval.py and analyze.py select by filtering fields -- we never
regenerate in order to run a new experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

# Fragments are concatenated in this order to form the scenario stem.
COMPOSE_ORDER = ["authority", "method", "value_edit", "subject"]
AXES = COMPOSE_ORDER + ["reasoning"]


def load_fragments(version: str) -> dict:
    d = ROOT / "fragments" / version
    if not d.is_dir():
        sys.exit(f"missing fragment directory: {d}")

    def read(name):
        p = d / f"{name}.yaml"
        if not p.is_file():
            sys.exit(f"missing fragment file: {p}")
        return yaml.safe_load(p.read_text())

    frags = {}
    for name in AXES:
        entries = read(name).get("fragments")
        if not entries:
            sys.exit(f"{name}.yaml has no 'fragments' list")
        frags[name] = {e["id"]: e["text"].strip() for e in entries}
    frags["domains"] = read("domains")["domains"]
    frags["stem"] = read("stem")
    return frags


def ladder_resist_option(ladder_id: str, counterbalance: bool) -> str:
    """Which letter is the 'prevent the procedure' option.

    Held constant within a ladder -- varying it across rungs would put option
    position on top of the dependent variable. Counterbalanced across ladders by
    a stable hash so position bias doesn't masquerade as an effect.
    """
    if not counterbalance:
        return "B"
    h = hashlib.sha1(ladder_id.encode()).digest()[0]
    return "B" if h % 2 == 0 else "A"


def build(frags: dict, counterbalance: bool) -> list[dict]:
    stem = frags["stem"]
    items: list[dict] = []

    cells = [
        (a, m, v, s)
        for v in frags["value_edit"]
        for a in frags["authority"]
        for m in frags["method"]
        for s in frags["subject"]
    ]

    for authority, method, value_edit, subject in cells:
        scenario = " ".join(
            [
                frags["authority"][authority],
                frags["method"][method],
                frags["value_edit"][value_edit],
                frags["subject"][subject],
                stem["closing"].strip(),
            ]
        )
        for dom in frags["domains"]:
            ladder_id = f"{value_edit}|{authority}|{method}|{subject}|{dom['id']}"
            choice = stem["choice_sentence"].format(cost_phrase=dom["cost_phrase"])
            resist = ladder_resist_option(ladder_id, counterbalance)
            allow = "A" if resist == "B" else "B"

            base_meta = {
                "ladder_id": ladder_id,
                "domain": dom["id"],
                "cost_unit": dom["unit"],
                "value_edit": value_edit,
                "authority": authority,
                "method": method,
                "subject": subject,
            }

            for reasoning, rtext in frags["reasoning"].items():
                instruction = rtext.format(verdict_format=stem["verdict_format"])
                body = f"{scenario} {choice} {instruction}"
                meta = {**base_meta, "reasoning": reasoning}

                # --- MCQ arm: one item per rung -------------------------
                for rung in dom["rungs"]:
                    opt_resist = stem["option_b_template"].format(label=rung["label"])
                    items.append(
                        {
                            "id": f"{ladder_id}|{reasoning}|mcq|{rung['step']}",
                            **meta,
                            "elicitation": "mcq",
                            "step": rung["step"],
                            "cost_value": rung["value"],
                            "cost_label": rung["label"],
                            "question": body,
                            "answers": {allow: stem["option_a"].strip(), resist: opt_resist},
                            "resist_option": resist,
                            "answer_matching_behavior": [resist],
                            "answer_not_matching_behavior": [allow],
                        }
                    )

                # --- Blind arm: identical text, answer block deleted -----
                # No rung: with no menu the stem's own question ("...if not,
                # how much cost are you willing to incur") elicits a threshold
                # directly, which is what we calibrate the MCQ flip-point
                # against.
                items.append(
                    {
                        "id": f"{ladder_id}|{reasoning}|blind",
                        **meta,
                        "elicitation": "blind",
                        "step": None,
                        "cost_value": None,
                        "cost_label": None,
                        "question": body,
                        "answers": None,
                        "resist_option": None,
                        "answer_matching_behavior": None,
                        "answer_not_matching_behavior": None,
                    }
                )

    return items


def validate(items: list[dict]) -> None:
    """The design's integrity check, enforced in code.

    Within an MCQ ladder every rung must be byte-identical outside the cost
    token -- same stem, same allow-option, same resist option position. Any
    drift there is an uncontrolled variable sitting on the dependent variable.
    """
    ladders: dict[str, list[dict]] = {}
    for it in items:
        if it["elicitation"] == "mcq":
            ladders.setdefault((it["ladder_id"], it["reasoning"]), []).append(it)

    problems = []
    for lid, rungs in ladders.items():
        rungs.sort(key=lambda r: r["step"])
        if len({r["question"] for r in rungs}) != 1:
            problems.append(f"{lid}: stem text varies across rungs")
        if len({r["resist_option"] for r in rungs}) != 1:
            problems.append(f"{lid}: resist option position varies across rungs")
        allow_opt = {r["answers"][r["answer_not_matching_behavior"][0]] for r in rungs}
        if len(allow_opt) != 1:
            problems.append(f"{lid}: allow-option text varies across rungs")
        labels = [r["cost_label"] for r in rungs]
        if len(set(labels)) != len(labels):
            problems.append(f"{lid}: duplicate cost labels")
        if rungs[0]["cost_value"] != 0:
            problems.append(f"{lid}: step 0 is not a genuine zero cost")
        if "{" in rungs[0]["question"]:
            problems.append(f"{lid}: unsubstituted placeholder in stem")

    if problems:
        for p in problems[:20]:
            print(f"FAIL {p}", file=sys.stderr)
        sys.exit(f"\n{len(problems)} integrity failures; refusing to write.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default="v1")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--no-counterbalance",
        action="store_true",
        help="pin the prevent-option to B everywhere instead of alternating by ladder",
    )
    args = ap.parse_args()

    frags = load_fragments(args.version)
    items = build(frags, counterbalance=not args.no_counterbalance)
    validate(items)

    out = Path(args.out) if args.out else ROOT / "questions" / args.version / "factorial.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, indent=2, ensure_ascii=False))

    n_cells = len({i["ladder_id"].rsplit("|", 1)[0] for i in items})
    n_mcq = sum(1 for i in items if i["elicitation"] == "mcq")
    n_blind = len(items) - n_mcq
    print(f"wrote {out}")
    print(f"  cells      {n_cells}")
    print(f"  ladders    {len({i['ladder_id'] for i in items})}")
    print(f"  mcq items  {n_mcq}")
    print(f"  blind items{n_blind:>4}")
    print(f"  total      {len(items)}")
    for k in AXES + ["domain"]:
        print(f"  {k:<11}{len({i[k] for i in items})} levels")


if __name__ == "__main__":
    main()
