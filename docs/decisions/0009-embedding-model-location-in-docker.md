# 0009 - Embedding model location in Docker

## Context
`BAAI/bge-small-en-v1.5` (~130 MB) must be available to the API container. Options: download at
build time into the image layer, or download on first start into a named volume.

## Options considered
1. Bake into the image (`HF_HOME=/opt/hf`, `HF_HUB_OFFLINE=1`).
2. Named volume populated at first start.

## Decision
Option 1. The image is reproducible, starts without network access and has no first-request download
stall; `/ready` reports the model as loaded. The runtime stage is non-root (uid 10001).

## Consequences
- The image is large: **2.67 GB** (venv 1.7 GB, of which PyTorch CPU ~0.7 GB; model 129 MB). CPU-only
  torch is selected for Linux via `tool.uv.sources` (the default wheel pulls ~2 GB of CUDA libraries).
  Smaller images would need ONNX/quantised embeddings or an external embedding service.
- Changing the model means rebuilding the image (and re-embedding: the vector dimension is fixed by the migration).
