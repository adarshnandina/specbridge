import os

# Tests never use real LLMs or the user's .env secrets.
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ.setdefault("EMBEDDING_MODEL", "hash")
os.environ["LOG_DIR"] = "./logs/test"
os.environ["API_KEYS"] = (
    "dev-viewer-key:alice:viewer,dev-engineer-key:bob:engineer,dev-approver-key:carol:approver,"
    "dev-engineer2-key:erin:engineer,dev-admin-key:dave:admin"
)
