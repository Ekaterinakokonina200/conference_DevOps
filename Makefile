setup:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

test:
	pytest

quality:
	ruff check .

migrate:
	alembic upgrade head

verify:
	pytest
	ruff check .