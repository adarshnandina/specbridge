import pytest
from pydantic import ValidationError

from specbridge.config import Settings


def test_defaults_ok():
    s = Settings(_env_file=None)
    assert s.llm_provider == "fake" and s.embedding_dim == 384


def test_unknown_provider_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="openai")


def test_bad_dim_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, embedding_dim=0)


def test_prod_requires_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="prod")


def test_api_keys_parse_and_bad_format():
    s = Settings(_env_file=None, api_keys="k1:alice:viewer,k2:bob:admin")
    assert s.parsed_api_keys() == [("k1", "alice", "viewer"), ("k2", "bob", "admin")]
    with pytest.raises(ValueError):
        Settings(_env_file=None, api_keys="broken").parsed_api_keys()


def test_model_for_bedrock_uses_separate_ids():
    s = Settings(_env_file=None, llm_provider="bedrock", bedrock_model_answer="bedrock-x")
    assert s.model_for("qa") == "bedrock-x"
