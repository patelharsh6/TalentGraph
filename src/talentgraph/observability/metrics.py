"""Prometheus metrics (plan §9). Wired into agents and the LLM client in Phases 5 and 8."""

from prometheus_client import Counter, Histogram

AGENT_LATENCY = Histogram("tg_agent_latency_seconds", "Agent latency", ["agent"])
AGENT_RUNS = Counter("tg_agent_runs_total", "Agent runs", ["agent", "status"])
AGENT_QUALITY = Histogram(
    "tg_agent_quality", "Agent quality score", ["agent"], buckets=[i / 10 for i in range(11)]
)
LLM_TOKENS = Counter("tg_llm_tokens_total", "Gemini tokens", ["model", "kind"])
LLM_LATENCY = Histogram("tg_llm_latency_seconds", "Gemini call latency", ["model"])
PIPELINE_RUNS = Counter("tg_pipeline_total", "Pipeline runs", ["status"])
