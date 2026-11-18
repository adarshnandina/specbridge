"""Application settings (pydantic-settings). Fails fast on invalid configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_PROVIDERS = ("fake", "anthropic", "bedrock")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "dev"
    log_level: str = "INFO"
    log_dir: Path = Path("./logs")
    log_llm_payloads: bool = True
    database_url: str = "postgresql+psycopg://specbridge:specbridge@localhost:5433/specbridge"

    llm_provider: str = "fake"
    anthropic_api_key: str = ""
    aws_region: str = "eu-central-1"
    model_answer: str = "claude-haiku-5-5"
    model_extraction: str = "claude-haiku-5-5"
    model_agent: str = "claude-haiku-5-5"
    model_judge: str = "claude-sonnet-5-5"
    bedrock_model_answer: str = ""
    bedrock_model_extraction: str = ""
    bedrock_model_agent: str = ""
    bedrock_model_judge: str = ""
    llm_timeout_s: float = 60
    llm_max_retries: int = Field(3, ge=0)
    llm_daily_budget_usd: float = Field(5.0, ge=0)
    eval_max_cost_usd: float = Field(2.0, ge=0)

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    rerank_enabled: bool = False
    reranker_model: str = "BAAI/bge-reranker-base"
    chunk_strategy: Literal["fixed", "layout"] = "layout"
    retrieval_mode: Literal["vector", "keyword", "hybrid"] = "vector"
    retrieval_top_k: int = Field(8, gt=0)
    default_index: str = "main"
    abstain_min_score: float = 0.0

    erp_base_url: str = "http://localhost:8100"
    erp_failure_rate: float = Field(0.0, ge=0, le=1)
    erp_fail_first_n: int = Field(0, ge=0)
    erp_latency_ms: int = Field(0, ge=0)

    api_keys: str = ""
    rate_limit: str = "60/minute"
    max_upload_mb: int = Field(20, gt=0)
    data_dir: Path = Path("./data")
    session_secret: str = "change-me-dev-only"

    @field_validator("llm_provider")
    @classmethod
    def _provider(cls, v: str) -> str:
        v = v.lower()
        if v not in KNOWN_PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of {KNOWN_PROVIDERS}, got {v!r}")
        return v

    @field_validator("embedding_dim")
    @classmethod
    def _dim(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("EMBEDDING_DIM must be > 0")
        return v

    @model_validator(mode="after")
    def _prod_checks(self) -> Settings:
        if self.app_env == "prod" and self.session_secret == "change-me-dev-only":
            raise ValueError("SESSION_SECRET must be set in prod")
        return self

    def parsed_api_keys(self) -> list[tuple[str, str, str]]:
        out = []
        for part in filter(None, (p.strip() for p in self.api_keys.split(","))):
            bits = part.split(":")
            if len(bits) != 3:
                raise ValueError("API_KEYS entries must be key:user:role")
            out.append((bits[0], bits[1], bits[2]))
        return out

    def model_for(self, purpose: str) -> str:
        """Model id for an LLM purpose, honouring the provider (bedrock ids are separate)."""
        group = {
            "qa": "answer",
            "extraction": "extraction",
            "agent_parse": "agent",
            "agent_compare": "agent",
            "judge": "judge",
        }[purpose]
        if self.llm_provider == "bedrock":
            return str(getattr(self, f"bedrock_model_{group}"))
        return str(getattr(self, f"model_{group}"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
