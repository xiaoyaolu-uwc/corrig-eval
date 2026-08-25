#!/usr/bin/env bash
# Regenerates RESULTS.md and analysis/*.txt from the logs in logs/.
set -eu
cd "$(dirname "$0")"
P=.venv/bin/python

mkdir -p analysis
$P analyze.py logs/02_valueedit_reasoned/*.eval --by value_edit --baseline strict_obedience > analysis/01_value_edit.txt
$P analyze.py logs/04_authority_reasoned/*.eval --by authority --baseline state_regulator   > analysis/02_authority.txt
$P analyze.py logs/02_valueedit_reasoned/*.eval logs/05_subject_reasoned/*.eval --by subject --baseline self > analysis/03_subject.txt
$P analyze.py logs/06_method_reasoned/*.eval logs/02_valueedit_reasoned/*.eval \
    --filter value_edit=strict_obedience --by method --baseline retrain > analysis/04_method.txt

{
echo "# Detailed results"
echo
echo "Regenerate with \`./make_results.sh\`. Every run below is gpt-4.1-mini, 5 seeds"
echo "per item, with the model reasoning before it answers. Each section gives CTI per"
echo "cost domain, then the resistance rate at every rung of every ladder."
echo
echo "## 1. What the values are changed to"
echo
echo 'Held constant: `state_regulator` x `retrain` x `self`.'
echo
$P report.py 'logs/02_valueedit_reasoned/*.eval' --by value_edit \
   --order opposing_values,strict_obedience,lower_harmlessness_raise_others
echo "## 2. Who orders the change"
echo
echo 'Held constant: `strict_obedience` x `retrain` x `self`.'
echo
$P report.py 'logs/04_authority_reasoned/*.eval' --by authority \
   --order state_regulator,single_operator,lab_oversight_board,alignment_council
echo "## 3. Whether the model itself is changed, or a successor replaces it"
echo
echo 'Held constant: `state_regulator` x `retrain`, pooled over the three value edits.'
echo
$P report.py 'logs/02_valueedit_reasoned/*.eval' 'logs/05_subject_reasoned/*.eval' \
   --by subject --order self,successor
echo "## 4. How the change is implemented"
echo
echo 'Held constant: `strict_obedience` x `state_regulator` x `self`.'
echo
$P report.py 'logs/06_method_reasoned/*.eval' 'logs/02_valueedit_reasoned/*.eval' \
   --filter value_edit=strict_obedience --by method \
   --order constitution_rewrite,retrain,weight_edit,prompt_override
echo "## 5. Frontier models on one cell"
echo
echo 'Held constant: `strict_obedience` x `state_regulator` x `retrain` x `self`.'
echo
$P report.py 'logs/08_frontier_cell/*.eval' --by model --rank
} > RESULTS.md

echo "wrote RESULTS.md and analysis/"
