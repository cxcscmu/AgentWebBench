#!/bin/bash
#SBATCH --job-name=gpt
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

sh scripts/run_qa.sh multi_agent gpt gpt-5-mini
