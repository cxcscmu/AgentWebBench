#!/bin/bash
#SBATCH --job-name=local_4b
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.out
#SBATCH --partition=general
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:2
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00


export PYTHONUNBUFFERED=1

eval "$(conda shell.bash hook)"
conda activate awbench

MODEL_NAME=${1:-"Qwen/Qwen3-4B-Thinking-2507"}

# Start the local vLLM service (in the background)
echo "Starting vLLM service in background..."
GPU_COUNT=2
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()')
echo "vLLM: ${GPU_COUNT} GPU(s) on random port ${PORT}"
nohup bash scripts/serve_vllm.sh "$MODEL_NAME" "$PORT" "$GPU_COUNT" > logs/local_vllm_service_${SLURM_JOB_ID}_${MODEL_NAME//\//_}.out 2>&1 &
VLLM_PID=$!
echo "vLLM service started with PID: $VLLM_PID"
echo "vLLM service log: logs/local_vllm_service_${SLURM_JOB_ID}_${MODEL_NAME//\//_}.out"

# Wait for the service to come up (poll the port)
echo "Waiting for vLLM service to be ready..."
for i in {1..6000}; do
    if curl -s http://localhost:${PORT}/v1/models > /dev/null 2>&1; then
        echo "vLLM service is ready!"
        break
    fi
    if [ $i -eq 6000 ]; then
        echo "Warning: vLLM service may not be ready after 60 seconds"
    fi
    sleep 1
done

nvidia-smi

sh scripts/run_qa.sh multi_agent local Qwen/Qwen3-4B-Thinking-2507 http://localhost:${PORT}/v1
