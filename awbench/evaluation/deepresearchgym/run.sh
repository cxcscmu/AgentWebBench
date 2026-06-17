#!/bin/bash
# Deep Research evaluation: score the reports produced by a run.
#
# Usage (from the repo root):
#   sh awbench/evaluation/deepresearchgym/run.sh <SUBFOLDER> [JUDGE_MODEL]
#
#   <SUBFOLDER>   results path under RESULTS_DIR (awbench/config.py), e.g.
#                 deep_research_test_331/local/Qwen/Qwen3-4B-Thinking-2507/multi_agent
#   [JUDGE_MODEL] OpenAI judge model (default: gpt-4.1-mini); needs OPENAI_API_KEY in keys.env
#
# Each script reads result_*.json from RESULTS_DIR/<SUBFOLDER> and appends its

SUBFOLDER="$1"
JUDGE_MODEL="${2:-gpt-4.1-mini}"

if [ -z "${SUBFOLDER}" ]; then
    echo "Usage: sh $0 <SUBFOLDER> [JUDGE_MODEL]" >&2
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
echo "=== Deep Research eval: ${SUBFOLDER} (judge: ${JUDGE_MODEL}) ==="

# Key-point recall (uses gold key points in key_point/<id>_aggregated.json)
python3 "${HERE}/eval_kpr_async.py"     --subfolder "${SUBFOLDER}" --open_ai_model "${JUDGE_MODEL}"

# Report quality (depth / objectivity / coverage / insight)
python3 "${HERE}/eval_quality_async.py" --subfolder "${SUBFOLDER}" --open_ai_model "${JUDGE_MODEL}"

# Citation faithfulness is separate and expensive (needs crawl4ai / the ClueWeb API
# and can be slow + costly). Run it manually when needed:
#   python3 "${HERE}/eval_citation_clueweb_async.py" --subfolder "${SUBFOLDER}" --open_ai_model "${JUDGE_MODEL}"
