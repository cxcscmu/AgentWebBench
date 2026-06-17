# scripts/

Run scripts for AgentWebBench. All paths are relative to the **project root**, so
invoke from there (e.g. `sh scripts/run_qa.sh ...` or `sbatch scripts/launchers/run_works_gemini.sh`).

## Task drivers (one per task)
Each driver runs `main.py` for one task, then its evaluation. Args: `METHOD API_TYPE MODEL_ID [URL]`
where `METHOD ∈ {classical, tool_embed, tool_prompt, multi_agent}`.

| driver | task | dataset |
|---|---|---|
| `run_web_search.sh`         | Web Search           | `data/web_search/` |
| `run_web_recommendation.sh` | Web Recommendation   | `data/web_recommendation/` |
| `run_qa.sh`                 | Question Answering   | `data/qa/` |
| `run_deep_research.sh`      | Deep Research        | `data/deep_research/` |

Example: `sh scripts/run_qa.sh multi_agent gemini gemini-3-flash-preview`

## run_classic_ir.sh
Non-agent / non-LLM baseline for Web Search: pure dense retrieval over the global
ClueWeb22 index (`awbench/classic_ir.py`), then document evaluation. Arg: `[NUM_DOCS]`.
Example: `sh scripts/run_classic_ir.sh 10`

## launchers/
Per-provider / per-model batch configs (SLURM `sbatch` scripts) that call the drivers
above with specific model lists. Edit/uncomment lines to choose what to run.

## serve_vllm.sh
Launches a local vLLM server for `--api_type local` models.

## Secrets
`HF_TOKEN` and API keys are read from `keys.env` (gitignored), not hardcoded.
Save-path prefix and all corpus paths come from `awbench/config.py`.
