.PHONY: install fixture test lint demo clean

install:
	pip install -e ".[dev]"

fixture:
	python scripts/make_fixture_statement.py

test:
	pytest -q

lint:
	ruff check src tests && mypy src --ignore-missing-imports

demo: fixture
	python scripts/demo_slice.py

clean:
	rm -rf data/corpus/* data/masks/* .pytest_cache .ruff_cache
