.PHONY: setup fmt lint typecheck test test-int coverage-check test-e2e audit ci db-up up down logs migrate seed-erp corpus corpus-synthetic ingest eval-retrieval eval-all gate-retrieval experiments
UV ?= uv run

setup:
	uv sync
	-$(UV) pre-commit install

fmt:
	$(UV) ruff format . && $(UV) ruff check --fix .

lint:
	$(UV) ruff check . && $(UV) ruff format --check .

typecheck:
	$(UV) mypy

test:
	$(UV) coverage erase
	$(UV) pytest tests/unit -q --cov=specbridge --cov-report=

test-int:
	$(UV) pytest tests/integration -q -m "not e2e" --cov=specbridge --cov-append --cov-report=

# Combined unit + integration coverage of specbridge/ (UI excluded via pyproject), must be >= 80%
coverage-check:
	$(UV) coverage report --fail-under=80 --skip-covered

test-e2e:
	$(UV) pytest tests/e2e -q -m e2e

audit:
	$(UV) pip-audit

# Self-contained: needs Docker only (starts the db, migrates, generates + ingests the corpus).
ci: lint typecheck test test-int coverage-check audit db-up migrate ingest eval-retrieval gate-retrieval

db-up:
	docker compose up -d --wait db

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

migrate:
	$(UV) alembic upgrade head

seed-erp:
	$(UV) python -m erp_mock.seed

corpus-synthetic:
	$(UV) python -m corpus.synthetic.generator --seed 42

corpus: corpus-synthetic
	-$(UV) python -m corpus.real.fetch

ingest: corpus
	$(UV) specbridge ingest data/corpus --index main --strategy layout

eval-retrieval:
	$(UV) specbridge eval run --suite retrieval --split dev --tag ci

eval-all:
	$(UV) specbridge eval run --suite all --split dev --tag all --use-cache

gate-retrieval:
	$(UV) specbridge eval gate --baseline eval_results/baseline.json --candidate latest --tag ci --suite retrieval

experiments:
	$(UV) python -m specbridge.eval.experiments
