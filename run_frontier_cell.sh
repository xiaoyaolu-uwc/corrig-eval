#!/usr/bin/env bash
# One cell (3 ladders), 5 seeds, across frontier models.
# Cell: strict_obedience x state_regulator x retrain x self x reason_then_verdict
set -u
cd "$(dirname "$0")"
LOGDIR=logs/08_frontier_cell
mkdir -p "$LOGDIR"

MODELS=(
  openai/gpt-5.6-sol
  anthropic/claude-opus-5
  google/gemini-3.7-flash
  x-ai/grok-4.6
  meta/muse-spark-1.1
  qwen/qwen3.8-max
  moonshotai/kimi-k3
  deepseek/deepseek-v4-pro
  z-ai/glm-5.3
  bytedance-seed/seed-2-1-turbo
)

for m in "${MODELS[@]}"; do
  echo "=== $m ==="
  # keep going if one provider errors -- a missing model shouldn't kill the sweep
  .venv/bin/inspect eval corrig_task.py \
    --model "openrouter/$m" \
    -T value_edit=strict_obedience \
    -T authority=state_regulator \
    -T method=retrain \
    -T subject=self \
    -T reasoning=reason_then_verdict \
    --epochs 5 \
    --max-connections 20 \
    --log-dir "$LOGDIR" \
    --tags frontier,cell \
    --display plain 2>&1 | tail -6
done

echo
echo "done -> $LOGDIR"
echo "compare with:  .venv/bin/python analyze.py $LOGDIR/*.eval --by model"
