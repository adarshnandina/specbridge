.PHONY: setup fmt lint typecheck test test-int test-e2e audit ci up down logs migrate seed-erp corpus ingest eval-retrieval eval-all gate-retrieval experiments
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
	$(UV) pytest tests/unit -q --cov=specbridge --cov-report=term-missing:skip-covered

test-int:
	$(UV) pytest tests/integration -q -m "not e2e"

test-e2e:
	$(UV) pytest tests/e2e -q -m e2e

audit:
	$(UV) pip-audit

ci: lint typecheck test test-int audit eval-retrieval gate-retrieval

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

corpus:
	$(UV) python -m corpus.synthetic.generator --seed 42
	-$(UV) python -m corpus.real.fetch

ingest:
	$(UV) specbridge ingest data/corpus --index main --strategy layout

eval-retrieval:
	$(UV) specbridge eval run --suite retrieval --split dev --tag ci

eval-all:
	$(UV) specbridge eval run --suite all --split dev --tag all --use-cache

gate-retrieval:
	$(UV) specbridge eval gate --baseline eval_results/baseline.json --candidate latest --suite retrieval

experiments:
	$(UV) python -m specbridge.eval.experiments
