/* =========================================================================
   AgentWebBench — Leaderboard data
   Transcribed verbatim from the ICML 2026 paper (Table 1, main results),
   plus supporting tables (retrieval ablation, LLM evolution, failure modes,
   interaction efficiency, content-agent visibility).
   Metrics are percentages (%). For KPC, lower is better.
   ========================================================================= */

window.AWB = (function () {
  // ---- Models (user-agent backbones) -------------------------------------
  const models = [
    { id: "qwen3-4b",  name: "Qwen3-4B",       org: "Qwen",     size: 4,    type: "open" },
    { id: "qwen3-14b", name: "Qwen3-14B",      org: "Qwen",     size: 14,   type: "open" },
    { id: "qwen3-30b", name: "Qwen3-30B-A3B",  org: "Qwen",     size: 30,   type: "open" },
    { id: "qwen3-80b", name: "Qwen3-80B-A3B",  org: "Qwen",     size: 80,   type: "open" },
    { id: "deepseek",  name: "DeepSeek-V3.2",  org: "DeepSeek", size: null, type: "open" },
    { id: "gpt5",      name: "GPT-5-mini",     org: "OpenAI",   size: null, type: "api"  },
    { id: "gemini3",   name: "Gemini-3-Flash", org: "Google",   size: null, type: "api"  },
  ];

  // ---- Coordination strategies / baselines -------------------------------
  const methods = [
    { id: "classical", name: "Classical",   short: "Classical",
      desc: "Centralized retrieval over the full index — an upper-reference baseline with universal access (no decentralized constraint).",
      kind: "baseline" },
    { id: "toolE", name: "Toolₑ",  short: "Tool_E",
      desc: "Embedding-similarity website selection + tool-based dense retrieval. No agent-to-agent communication.",
      kind: "agent" },
    { id: "toolP", name: "Toolₚ",  short: "Tool_P",
      desc: "LLM-reasoned (prompted) website selection + tool-based dense retrieval. No content agents.",
      kind: "agent" },
    { id: "multi", name: "Multi-Agent", short: "Multi-Agent",
      desc: "Full agent-to-agent coordination: both user and content agents reason autonomously over multi-turn interaction.",
      kind: "agent" },
  ];

  // ---- Task / metric definitions -----------------------------------------
  const tasks = {
    search: {
      name: "Web Search", icon: "search",
      blurb: "Ad-hoc ranked retrieval under strict website boundaries.",
      samples: 354, output: "Ranked documents", dataset: "MS MARCO Web Search",
      metrics: [
        { k: "n3", label: "N@3", lower: false },
        { k: "n5", label: "N@5", lower: false },
        { k: "r3", label: "R@3", lower: false },
        { k: "r5", label: "R@5", lower: false },
      ],
      primary: "n3",
    },
    rec: {
      name: "Web Recommendation", icon: "rec",
      blurb: "History-conditioned next-intent retrieval.",
      samples: 281, output: "Ranked documents", dataset: "ORBIT",
      metrics: [
        { k: "n3", label: "N@3", lower: false },
        { k: "n5", label: "N@5", lower: false },
        { k: "r3", label: "R@3", lower: false },
        { k: "r5", label: "R@5", lower: false },
      ],
      primary: "n3",
    },
    qa: {
      name: "Question Answering", icon: "qa",
      blurb: "Multi-step evidence integration into a short answer.",
      samples: 53, output: "Short answer", dataset: "DeepResearchGym (short)",
      metrics: [
        { k: "acc", label: "Accuracy", lower: false },
        { k: "f1",  label: "F1",       lower: false },
      ],
      primary: "acc",
    },
    research: {
      name: "Deep Research", icon: "research",
      blurb: "Long-horizon planning + structured report synthesis.",
      samples: 331, output: "Long report", dataset: "DeepResearchGym",
      metrics: [
        { k: "kpr",     label: "KPR",     lower: false },
        { k: "kpc",     label: "KPC",     lower: true  },
        { k: "clarity", label: "Clarity", lower: false },
        { k: "insight", label: "Insight", lower: false },
      ],
      primary: "kpr",
    },
  };

  // ---- Non-agent IR baseline (web search only) ---------------------------
  const classicIR = { n3: 47.86, n5: 51.04, r3: 57.63, r5: 65.25 };

  // ---- Main leaderboard rows (Table 1) -----------------------------------
  // Each row: { model, method, search{n3,n5,r3,r5}, rec{...}, qa{acc,f1}, research{kpr,kpc,clarity,insight} }
  const rows = [
    // Qwen3-4B
    { model: "qwen3-4b", method: "classical", search:{n3:47.65,n5:47.65,r3:54.80,r5:54.80}, rec:{n3:0.80,n5:0.80,r3:1.07,r5:1.07}, qa:{acc:18.87,f1:21.43}, research:{kpr:52.74,kpc:1.48,clarity:71.45,insight:63.84} },
    { model: "qwen3-4b", method: "toolE",     search:{n3:30.67,n5:31.03,r3:36.44,r5:37.29}, rec:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, qa:{acc:13.21,f1:15.21}, research:{kpr:53.17,kpc:2.19,clarity:77.13,insight:74.35} },
    { model: "qwen3-4b", method: "toolP",     search:{n3:32.62,n5:33.21,r3:35.31,r5:36.72}, rec:{n3:0.58,n5:0.58,r3:0.71,r5:0.71}, qa:{acc:13.21,f1:16.13}, research:{kpr:47.83,kpc:1.37,clarity:67.79,insight:61.99} },
    { model: "qwen3-4b", method: "multi",     search:{n3:26.80,n5:27.04,r3:29.38,r5:29.94}, rec:{n3:0.58,n5:0.58,r3:0.71,r5:0.71}, qa:{acc:15.09,f1:17.44}, research:{kpr:47.54,kpc:1.63,clarity:71.63,insight:62.63} },

    // Qwen3-14B
    { model: "qwen3-14b", method: "classical", search:{n3:47.59,n5:47.59,r3:55.37,r5:55.37}, rec:{n3:0.22,n5:0.22,r3:0.36,r5:0.36}, qa:{acc:16.98,f1:16.73}, research:{kpr:54.40,kpc:1.29,clarity:71.57,insight:59.12} },
    { model: "qwen3-14b", method: "toolE",     search:{n3:25.82,n5:27.94,r3:30.23,r5:35.31}, rec:{n3:0.18,n5:0.18,r3:0.36,r5:0.36}, qa:{acc:20.75,f1:17.90}, research:{kpr:54.62,kpc:0.68,clarity:75.83,insight:65.92} },
    { model: "qwen3-14b", method: "toolP",     search:{n3:30.06,n5:31.12,r3:33.90,r5:36.44}, rec:{n3:0.00,n5:0.14,r3:0.00,r5:0.36}, qa:{acc:20.75,f1:13.18}, research:{kpr:49.12,kpc:1.13,clarity:63.11,insight:52.81} },
    { model: "qwen3-14b", method: "multi",     search:{n3:27.33,n5:27.90,r3:31.36,r5:32.77}, rec:{n3:0.22,n5:0.53,r3:0.36,r5:1.07}, qa:{acc:28.30,f1:23.79}, research:{kpr:49.85,kpc:1.29,clarity:63.23,insight:51.69} },

    // Qwen3-30B-A3B
    { model: "qwen3-30b", method: "classical", search:{n3:49.90,n5:49.90,r3:57.34,r5:57.34}, rec:{n3:0.36,n5:0.36,r3:0.36,r5:0.36}, qa:{acc:28.30,f1:26.77}, research:{kpr:54.99,kpc:2.59,clarity:76.74,insight:69.88} },
    { model: "qwen3-30b", method: "toolE",     search:{n3:30.24,n5:30.97,r3:35.03,r5:36.72}, rec:{n3:0.18,n5:0.18,r3:0.36,r5:0.36}, qa:{acc:22.64,f1:25.71}, research:{kpr:57.95,kpc:2.94,clarity:81.54,insight:79.73} },
    { model: "qwen3-30b", method: "toolP",     search:{n3:32.24,n5:33.29,r3:36.44,r5:38.98}, rec:{n3:0.36,n5:0.36,r3:0.36,r5:0.36}, qa:{acc:24.53,f1:24.92}, research:{kpr:54.82,kpc:2.14,clarity:73.05,insight:68.37} },
    { model: "qwen3-30b", method: "multi",     search:{n3:29.38,n5:29.72,r3:32.77,r5:33.62}, rec:{n3:0.22,n5:0.22,r3:0.36,r5:0.36}, qa:{acc:20.75,f1:18.12}, research:{kpr:52.03,kpc:2.53,clarity:71.45,insight:64.38} },

    // Qwen3-80B-A3B
    { model: "qwen3-80b", method: "classical", search:{n3:48.65,n5:48.78,r3:54.80,r5:55.08}, rec:{n3:0.18,n5:0.18,r3:0.36,r5:0.36}, qa:{acc:33.96,f1:33.29}, research:{kpr:59.11,kpc:2.16,clarity:77.40,insight:68.70} },
    { model: "qwen3-80b", method: "toolE",     search:{n3:27.32,n5:27.92,r3:29.94,r5:31.36}, rec:{n3:0.18,n5:0.18,r3:0.36,r5:0.36}, qa:{acc:35.85,f1:35.56}, research:{kpr:62.90,kpc:2.20,clarity:85.62,insight:82.69} },
    { model: "qwen3-80b", method: "toolP",     search:{n3:33.73,n5:34.30,r3:37.85,r5:39.27}, rec:{n3:0.18,n5:0.18,r3:0.36,r5:0.36}, qa:{acc:32.08,f1:31.63}, research:{kpr:57.85,kpc:1.92,clarity:74.05,insight:65.86} },
    { model: "qwen3-80b", method: "multi",     search:{n3:33.32,n5:34.04,r3:38.42,r5:40.11}, rec:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, qa:{acc:37.74,f1:37.60}, research:{kpr:57.28,kpc:2.16,clarity:74.56,insight:65.26} },

    // DeepSeek-V3.2 (thinking)
    { model: "deepseek", method: "classical", search:{n3:49.02,n5:49.37,r3:55.37,r5:56.21}, rec:{n3:0.40,n5:0.40,r3:0.71,r5:0.71}, qa:{acc:24.53,f1:19.51}, research:{kpr:66.54,kpc:1.27,clarity:87.16,insight:80.48} },
    { model: "deepseek", method: "toolE",     search:{n3:33.98,n5:35.05,r3:37.85,r5:40.40}, rec:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, qa:{acc:20.75,f1:17.05}, research:{kpr:68.23,kpc:1.11,clarity:88.61,insight:83.56} },
    { model: "deepseek", method: "toolP",     search:{n3:34.98,n5:36.17,r3:40.11,r5:42.94}, rec:{n3:0.58,n5:0.89,r3:0.71,r5:1.42}, qa:{acc:24.53,f1:17.00}, research:{kpr:64.23,kpc:1.47,clarity:86.65,insight:74.89} },
    { model: "deepseek", method: "multi",     search:{n3:33.42,n5:34.23,r3:39.27,r5:41.24}, rec:{n3:0.18,n5:0.18,r3:0.36,r5:0.36}, qa:{acc:30.19,f1:29.55}, research:{kpr:64.95,kpc:1.59,clarity:87.07,insight:75.77} },

    // GPT-5-mini
    { model: "gpt5", method: "classical", search:{n3:51.39,n5:52.09,r3:58.76,r5:60.45}, rec:{n3:0.45,n5:0.45,r3:0.71,r5:0.71}, qa:{acc:35.85,f1:21.10}, research:{kpr:60.97,kpc:0.92,clarity:77.07,insight:74.80} },
    { model: "gpt5", method: "toolE",     search:{n3:34.23,n5:35.41,r3:38.98,r5:41.81}, rec:{n3:0.36,n5:0.36,r3:0.36,r5:0.36}, qa:{acc:37.74,f1:24.57}, research:{kpr:70.87,kpc:1.18,clarity:83.23,insight:82.27} },
    { model: "gpt5", method: "toolP",     search:{n3:40.29,n5:42.55,r3:47.18,r5:52.54}, rec:{n3:0.36,n5:0.36,r3:0.71,r5:0.71}, qa:{acc:32.08,f1:24.99}, research:{kpr:70.62,kpc:0.99,clarity:88.61,insight:85.29} },
    { model: "gpt5", method: "multi",     search:{n3:40.14,n5:42.30,r3:46.61,r5:51.69}, rec:{n3:0.00,n5:0.14,r3:0.00,r5:0.36}, qa:{acc:33.96,f1:22.78}, research:{kpr:69.39,kpc:1.28,clarity:89.15,insight:84.44} },

    // Gemini-3-Flash
    { model: "gemini3", method: "classical", search:{n3:52.21,n5:53.77,r3:60.17,r5:63.84}, rec:{n3:0.58,n5:0.73,r3:0.71,r5:1.07}, qa:{acc:60.38,f1:56.15}, research:{kpr:63.58,kpc:1.67,clarity:83.56,insight:76.86} },
    { model: "gemini3", method: "toolE",     search:{n3:39.56,n5:40.49,r3:44.63,r5:46.89}, rec:{n3:0.36,n5:0.36,r3:0.36,r5:0.36}, qa:{acc:56.60,f1:51.92}, research:{kpr:65.17,kpc:1.44,clarity:89.37,insight:86.16} },
    { model: "gemini3", method: "toolP",     search:{n3:47.52,n5:49.07,r3:56.50,r5:60.17}, rec:{n3:0.45,n5:0.59,r3:0.71,r5:1.07}, qa:{acc:67.92,f1:60.26}, research:{kpr:62.38,kpc:1.61,clarity:80.60,insight:71.90} },
    { model: "gemini3", method: "multi",     search:{n3:44.34,n5:47.08,r3:51.98,r5:58.47}, rec:{n3:0.36,n5:0.36,r3:0.36,r5:0.36}, qa:{acc:67.92,f1:61.10}, research:{kpr:62.45,kpc:1.37,clarity:81.00,insight:72.54} },
  ];

  // ---- Supporting tables --------------------------------------------------

  // Retrieval-backend ablation: Gemini-3, Web Search (Table 9)
  const retrievalAblation = {
    backends: ["Dense (Ours)", "BM25", "Hybrid"],
    rows: [
      { backend: "Dense (Ours)", method: "Classic IR",  n3:47.86, n5:51.04, r3:57.63, r5:65.25 },
      { backend: "Dense (Ours)", method: "Classical",   n3:52.21, n5:53.77, r3:60.17, r5:63.84 },
      { backend: "Dense (Ours)", method: "Toolₑ",  n3:39.56, n5:40.49, r3:44.63, r5:46.89 },
      { backend: "Dense (Ours)", method: "Toolₚ",  n3:47.52, n5:49.07, r3:56.50, r5:60.17 },
      { backend: "Dense (Ours)", method: "Multi-Agent", n3:44.34, n5:47.08, r3:51.98, r5:58.47 },
      { backend: "BM25", method: "Classic IR",  n3:28.12, n5:31.48, r3:33.33, r5:41.53 },
      { backend: "BM25", method: "Classical",   n3:38.47, n5:38.58, r3:42.37, r5:42.66 },
      { backend: "BM25", method: "Toolₑ",  n3:29.73, n5:29.84, r3:32.20, r5:32.49 },
      { backend: "BM25", method: "Toolₚ",  n3:35.75, n5:36.93, r3:40.40, r5:43.22 },
      { backend: "BM25", method: "Multi-Agent", n3:33.07, n5:34.93, r3:38.98, r5:43.50 },
      { backend: "Hybrid", method: "Classic IR",  n3:43.44, n5:47.41, r3:51.98, r5:61.86 },
      { backend: "Hybrid", method: "Classical",   n3:50.53, n5:51.47, r3:58.19, r5:60.45 },
      { backend: "Hybrid", method: "Toolₑ",  n3:37.59, n5:37.95, r3:42.09, r5:42.94 },
      { backend: "Hybrid", method: "Toolₚ",  n3:45.35, n5:47.21, r3:52.82, r5:57.34 },
      { backend: "Hybrid", method: "Multi-Agent", n3:44.94, n5:46.35, r3:53.11, r5:56.50 },
    ],
  };

  // LLM evolution across Qwen generations, 14B (Table 7) — Multi-Agent setting
  const evolution = [
    { model: "Qwen1.5-14B", year: "2024", search:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, rec:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, qa:{acc:0.00,f1:1.08}, research:{kpr:3.73,kpc:0.06,clarity:4.35,insight:4.26} },
    { model: "Qwen2.5-14B", year: "2024", search:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, rec:{n3:0.00,n5:0.00,r3:0.00,r5:0.00}, qa:{acc:5.66,f1:4.01}, research:{kpr:7.32,kpc:0.18,clarity:6.74,insight:6.89} },
    { model: "Qwen3-14B",   year: "2025", search:{n3:27.33,n5:27.90,r3:31.36,r5:32.77}, rec:{n3:0.22,n5:0.53,r3:0.36,r5:1.07}, qa:{acc:28.30,f1:23.79}, research:{kpr:49.85,kpc:1.29,clarity:63.23,insight:51.69} },
  ];

  // Failure-mode attribution (Table 4): % of incorrect predictions
  const failure = [
    { model: "Qwen3-4B",      search:[59.59,40.41], rec:[48.75,51.25], qa:[84.44,15.56] },
    { model: "Qwen3-14B",     search:[64.83,35.17], rec:[62.59,37.41], qa:[84.21,15.79] },
    { model: "Qwen3-30B-A3B", search:[56.41,43.59], rec:[52.86,47.14], qa:[83.33,16.67] },
    { model: "Qwen3-80B-A3B", search:[54.90,45.10], rec:[60.85,39.15], qa:[93.94,6.06] },
    { model: "DeepSeek-V3.2", search:[35.18,64.82], rec:[48.57,51.43], qa:[70.27,29.73] },
    { model: "GPT-5-mini",    search:[42.21,57.79], rec:[60.22,39.78], qa:[68.57,31.43] },
    { model: "Gemini-3",      search:[30.66,69.34], rec:[56.52,43.48], qa:[94.12,5.88] },
  ];

  // Interaction efficiency (Table 6): Qwen3-4B vs Gemini-3
  const efficiency = {
    cols: ["Turn", "#Agent", "#Req.", "User Valid %", "Content Turn", "Content Valid %"],
    groups: [
      { model: "Qwen3-4B", rows: [
        { task: "Web Search",         v: [2.61, 2.61, 2.79, 88.58, 2.53, 78.65] },
        { task: "Web Recommendation", v: [7.63, 6.02, 9.88, 84.88, 2.69, 53.99] },
        { task: "Question Answering", v: [3.38, 1.36, 2.06, 91.37, 3.83, 47.62] },
        { task: "Deep Research",      v: [4.61, 3.60, 4.05, 96.20, 2.24, 52.54] },
      ]},
      { model: "Gemini-3", rows: [
        { task: "Web Search",         v: [3.29, 4.64, 6.26, 99.10, 7.98, 56.42] },
        { task: "Web Recommendation", v: [3.27, 3.64, 6.55, 97.83, 10.61, 43.41] },
        { task: "Question Answering", v: [4.11, 2.40, 4.91, 75.05, 12.37, 25.26] },
        { task: "Deep Research",      v: [4.82, 5.07, 9.04, 93.04, 9.87, 57.03] },
      ]},
    ],
  };

  return { models, methods, tasks, classicIR, rows, retrievalAblation, evolution, failure, efficiency };
})();
