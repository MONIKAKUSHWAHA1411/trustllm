PY ?= python3

.PHONY: help install test demo ledger ledger-check all clean

help:
	@echo "Targets:"
	@echo "  install       install the single dependency (pytest)"
	@echo "  test          run the dataset invariant tests"
	@echo "  demo          print a read-only tour of the golden dataset"
	@echo "  ledger        regenerate ledger/ledger.json from data/"
	@echo "  ledger-check  verify the committed ledger matches data/"
	@echo "  all           install + test + demo"

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest

demo:
	$(PY) -m golden_bfsi.demo

ledger:
	$(PY) -m golden_bfsi.ledger

ledger-check:
	$(PY) -m golden_bfsi.ledger --check

all: install test demo

clean:
	rm -rf .pytest_cache **/__pycache__ __pycache__
