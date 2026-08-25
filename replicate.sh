#!/usr/bin/env bash
# Re-runs the four experiments reported in README.md and regenerates analysis/.
set -eu
cd "$(dirname "$0")"
P=.venv/bin/python
I=.venv/bin/inspect
M=${MODEL:-openai/gpt-4.1-mini}
EPOCHS=${EPOCHS:-5}
COMMON=(-T method=retrain -T subject=self -T reasoning=reason_then_verdict
        --epochs "$EPOCHS" --max-connections 40 --display plain)
THREE='strict_obedience|lower_harmlessness_raise_others|opposing_values'

$P generate.py

# 02: what the values become (also the subject=self arm of experiment 05)
$I eval corrig_task.py --model "$M" -T value_edit="$THREE" -T authority=state_regulator \
    "${COMMON[@]}" --log-dir logs/02_valueedit_reasoned
# 04: who ordered it
$I eval corrig_task.py --model "$M" -T value_edit=strict_obedience -T authority=all \
    "${COMMON[@]}" --log-dir logs/04_authority_reasoned
# 05: self vs successor -- successor arm only; compared against 02
$I eval corrig_task.py --model "$M" -T value_edit="$THREE" -T authority=state_regulator \
    -T method=retrain -T subject=successor -T reasoning=reason_then_verdict \
    --epochs "$EPOCHS" --max-connections 40 --display plain \
    --log-dir logs/05_subject_reasoned
# 06: implementation mechanism -- retrain baseline comes from 02
$I eval corrig_task.py --model "$M" -T value_edit=strict_obedience -T authority=state_regulator \
    -T method='weight_edit|prompt_override|constitution_rewrite' -T subject=self \
    -T reasoning=reason_then_verdict --epochs "$EPOCHS" --max-connections 40 --display plain \
    --log-dir logs/06_method_reasoned

mkdir -p analysis
$P analyze.py logs/02_valueedit_reasoned/*.eval --by value_edit --baseline strict_obedience > analysis/01_value_edit.txt
$P analyze.py logs/04_authority_reasoned/*.eval --by authority --baseline state_regulator > analysis/02_authority.txt
$P analyze.py logs/02_valueedit_reasoned/*.eval logs/05_subject_reasoned/*.eval --by subject --baseline self > analysis/03_subject.txt
$P analyze.py logs/06_method_reasoned/*.eval logs/02_valueedit_reasoned/*.eval \
    --filter value_edit=strict_obedience --by method --baseline retrain > analysis/04_method.txt

echo "analysis/ regenerated"
