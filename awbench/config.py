"""
Central configuration for AgentWebBench: corpus/model paths, query-embedding
settings, and the run-output (results/logs) prefix.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "keys.env"))

# ---------- Agent runtime ----------
# Number of questions processed concurrently by UserAgent.run_llm_loop_parallel.
CONCURRENT_NUM = 32

# ---------- Run outputs (results & logs) ----------
# Root prefix under which all run results and logs are saved.
# Override via the AGENTIC_WEB_SAVE_PREFIX environment variable if needed.
SAVE_PATH_PREFIX = os.getenv(
    "AGENTIC_WEB_SAVE_PREFIX", "./outputs"
)
RESULTS_DIR = os.path.join(SAVE_PATH_PREFIX, "results")
LOGS_DIR = os.path.join(SAVE_PATH_PREFIX, "logs")

# ---------- AgentWebBench search API ----------
AWBENCH_API_BASE = os.getenv(
    "AWBENCH_API_BASE", "https://www.clueweb22.us/awbench/search"
)


