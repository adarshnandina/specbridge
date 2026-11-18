# syntax=docker/dockerfile:1
# --- builder: resolve and install dependencies, bake the embedding model into the image ---------
FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir uv==0.13.5
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
# ADR-0009: the model is downloaded at build time into the image layer (no runtime network needed,
# reproducible, fast cold start) at the cost of ~130 MB of image size.
ENV HF_HOME=/opt/hf
RUN /app/.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# --- runtime: slim, non-root ---------------------------------------------------------------------
FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 app && mkdir -p /app/data /app/logs && chown -R app:app /app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /opt/hf /opt/hf
COPY --chown=app:app specbridge ./specbridge
COPY --chown=app:app erp_mock ./erp_mock
COPY --chown=app:app corpus ./corpus
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini pyproject.toml ./
COPY --chown=app:app config ./config
COPY --chown=app:app eval/datasets ./eval/datasets
COPY --chown=app:app docker/entrypoint.sh ./docker/entrypoint.sh
ENV PATH=/app/.venv/bin:$PATH PYTHONPATH=/app HF_HOME=/opt/hf HF_HUB_OFFLINE=1 \
    PYTHONUNBUFFERED=1 APP_ENV=prod DATA_DIR=/app/data LOG_DIR=/app/logs
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "specbridge.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
