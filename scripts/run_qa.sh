#!/bin/bash
#SBATCH --job-name=qa
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

# ========== configurations ==========
BATCH_FILE="data/qa/test_53.json" # 53
METHOD=${1:-"multi_agent"} # classical, tool_prompt, tool_embed, multi_agent
API_TYPE=${2:-"gemini"} # gemini, gpt, hf, local
MODEL_ID=${3:-"none"} # model ID
URL=${4:-"None"}
TASK_TYPE="qa"
# ==============================

# Extract dataset name: directory_name + filename (without extension)
# Example: data/qa/test.json -> qa_test
DIR_NAME=$(basename "$(dirname "${BATCH_FILE}")")
FILE_NAME=$(basename "${BATCH_FILE}" .json)
DATASET_NAME="${DIR_NAME}_${FILE_NAME}"

RUN_DATE=$(date +%Y%m%d)
DATASET_WITH_DATE="${DATASET_NAME}"

# Save-path prefix is centralized in config.py at the project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SAVE_PREFIX=$(cd "${PROJECT_ROOT}" && python3 -c "from awbench.config import SAVE_PATH_PREFIX; print(SAVE_PATH_PREFIX)")
ANSWER_DIR="${SAVE_PREFIX}/results/${DATASET_WITH_DATE}/${API_TYPE}/${MODEL_ID}/${METHOD}"
LOG_DIR="${SAVE_PREFIX}/logs/${DATASET_WITH_DATE}/${API_TYPE}/${MODEL_ID}/${METHOD}"

# Clear log and answer directories if test_1
if [[ "${BATCH_FILE}" == *"test_1"* ]]; then
    echo "Clearing log and answer directories for test_1..."
    [ -d "${LOG_DIR}" ] && rm -rf "${LOG_DIR}"/*
    [ -d "${ANSWER_DIR}" ] && rm -rf "${ANSWER_DIR}"/*
    echo "Directories cleared."
fi

if [ "${URL}" != "None" ]; then
    CMD="python3 main.py --batch_file ${BATCH_FILE} --answer_dir ${ANSWER_DIR} --log_dir ${LOG_DIR} --method ${METHOD} --task_type ${TASK_TYPE} --api_type ${API_TYPE} --model_id ${MODEL_ID} --url ${URL}"
else
    CMD="python3 main.py --batch_file ${BATCH_FILE} --answer_dir ${ANSWER_DIR} --log_dir ${LOG_DIR} --method ${METHOD} --task_type ${TASK_TYPE} --api_type ${API_TYPE} --model_id ${MODEL_ID}"
fi
echo -e "===============Running command===============\n${CMD}\n============================================="
${CMD}


python awbench/evaluation/qa/evaluation.py \
    --data_path $BATCH_FILE \
    --results_dir $ANSWER_DIR