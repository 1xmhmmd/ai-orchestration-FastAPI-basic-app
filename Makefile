.PHONY: install run test lint format typecheck docker-up docker-down

install:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v

lint:
	ruff check .

format:
	black .
	ruff check --fix .

typecheck:
	mypy app

docker-up:
	docker compose up --build

docker-down:
	docker compose down
