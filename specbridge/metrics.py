"""Prometheus metrics registry."""

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter("sb_http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("sb_http_request_seconds", "HTTP latency", ["route"])
LLM_CALLS = Counter("sb_llm_calls_total", "LLM calls", ["purpose", "model", "status"])
LLM_TOKENS = Counter("sb_llm_tokens_total", "LLM tokens", ["purpose", "model", "direction"])
LLM_COST = Counter("sb_llm_cost_usd_total", "LLM cost USD", ["purpose", "model"])
RETRIEVAL_LATENCY = Histogram("sb_retrieval_seconds", "Retrieval latency", ["mode"])
EXTRACTION_STATUS = Counter("sb_extraction_status_total", "Extraction status events", ["status"])
AGENT_RUNS = Counter("sb_agent_runs_total", "Agent runs by final state", ["state"])
BUDGET_REMAINING = Gauge("sb_llm_budget_remaining_usd", "Remaining daily LLM budget")
