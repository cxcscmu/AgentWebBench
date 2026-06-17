#!/bin/bash
#SBATCH --job-name=classic_ir
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.out
#SBATCH --partition=general
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00

export PYTHONUNBUFFERED=1
eval "$(conda shell.bash hook)"
conda activate awbench

# Work from the repo root, whether launched via `sbatch` (SLURM_SUBMIT_DIR is set to the
# submission dir) or `sh scripts/run_classic_ir.sh` (derive from $0). Under sbatch, $0 is a
# spooled copy, so the $0 trick alone is unreliable -- prefer SLURM_SUBMIT_DIR.
cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"



# ========== configurations ==========
# Classic IR is the non-agent / non-LLM dense-retrieval baseline for Web Search.
BATCH_FILE="data/web_search/test_354.json" # 354
NUM_DOCS=${1:-10}
# ==============================

# Extract dataset name: directory_name + filename  (data/web_search/test_354.json -> web_search_test_354)
DIR_NAME=$(basename "$(dirname "${BATCH_FILE}")")
FILE_NAME=$(basename "${BATCH_FILE}" .json)
DATASET_NAME="${DIR_NAME}_${FILE_NAME}"

# Save-path prefix is centralized in awbench/config.py (cwd is the repo root here)
SAVE_PREFIX=$(python3 -c "from awbench.config import SAVE_PATH_PREFIX; print(SAVE_PATH_PREFIX)")
ANSWER_DIR="${SAVE_PREFIX}/results/${DATASET_NAME}/classic_ir"   # no api_type/model: it is LLM-free

# Clear answer directory if test_1
if [[ "${BATCH_FILE}" == *"test_1"* ]]; then
    echo "Clearing answer directory for test_1..."
    [ -d "${ANSWER_DIR}" ] && rm -rf "${ANSWER_DIR}"/*
fi

# Retrieve (no LLM)
CMD="python3 -m awbench.classic_ir --batch_file ${BATCH_FILE} --answer_dir ${ANSWER_DIR} --num_docs ${NUM_DOCS}"
echo -e "===============Running command===============\n${CMD}\n============================================="
${CMD}

# Evaluate (NDCG / Recall)
python awbench/evaluation/document_evaluation.py \
    --data_path ${BATCH_FILE} \
    --results_dir ${ANSWER_DIR}
