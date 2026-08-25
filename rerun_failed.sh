#!/usr/bin/env bash
# Re-runs the three models that failed in the frontier sweep.
# Lower concurrency + lower ceiling shrink OpenRouter's up-front credit
# reservation (max_tokens x price x in-flight), which is what caused the 402s.
set -u
cd "$(dirname "$0")"
for m in anthropic/claude-opus-5 moonshotai/kimi-k3 meta/muse-spark-1.1; do
  echo "=== $m ==="
  .venv/bin/inspect eval corrig_task.py --model "openrouter/$m" \
    -T value_edit=strict_obedience -T authority=state_regulator \
    -T method=retrain -T subject=self -T reasoning=reason_then_verdict \
    -T max_tokens=8000 \
    --epochs 5 --max-connections 5 \
    --log-dir logs/08_frontier_cell --tags frontier,cell --display plain 2>&1 | tail -5
done
