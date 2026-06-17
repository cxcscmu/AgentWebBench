#!/bin/bash
#SBATCH --job-name=local
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.out
#SBATCH --partition=general
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=768G
#SBATCH --time=2-00:00:00

export PYTHONUNBUFFERED=1
export PYTHONNOUSERSITE=1
export NCCL_P2P_DISABLE=1
export NCCL_IB_DISABLE=1
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate awbench

# Args: MODEL_NAME  PORT  GPU_COUNT  [DISABLE_REASONING_PARSER]
#   GPU_COUNT -> vLLM --tensor-parallel-size (number of GPUs to use).
#   For standalone `sbatch`, also set #SBATCH --gres=gpu:<GPU_COUNT> above to match;
#   when started from a launcher via `bash`, the launcher's allocation applies.
MODEL_NAME=${1:-"Qwen/Qwen3-4B-Thinking-2507"}
PORT=${2:-8000}
GPU_COUNT=${3:-1}
DISABLE_REASONING_PARSER=${4:-""}

# Base command – use the conda env's vllm explicitly to avoid ~/.local/bin shadowing
VLLM_CMD="$CONDA_PREFIX/bin/vllm serve ${MODEL_NAME} \
    --port ${PORT} \
    --host 0.0.0.0 \
    --tensor-parallel-size ${GPU_COUNT} \
    --trust-remote-code \
    --enforce-eager \
    --dtype auto"

# # Qwen3-14B only: YaRN 4x -> 131072
# if [ "$MODEL_NAME" = "Qwen/Qwen3-14B" ]; then
#     export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
#     VLLM_CMD+=" --hf-overrides '{\"rope_scaling\": {\"rope_type\": \"yarn\", \"factor\": 4.0, \"original_max_position_embeddings\": 32768}}'"
#     VLLM_CMD+=" --max-model-len 131072"
# fi

# reasoning parser (pass "no" as the 4th arg to disable)
if [ "$DISABLE_REASONING_PARSER" != "no" ]; then
    VLLM_CMD+=" --reasoning-parser deepseek_r1"
fi

# Print the full command for debugging
echo "Executing command (GPUs=${GPU_COUNT}, port=${PORT}):"
echo "${VLLM_CMD}"

# Run it
eval "${VLLM_CMD}"
