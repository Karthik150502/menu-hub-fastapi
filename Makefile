.PHONY: install dev lint test migrate

install:
	poetry install

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check . && mypy app/

test:
	pytest --cov=app --cov-report=term-missing -v

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(name)"
