# Single entry point for the project. Recipes are plain `uv run` commands so
# they behave the same on Windows, macOS, Linux and in CI.

# Which survey and year to process. Override on the command line:
#   make all SURVEY=config/surveys/other.yaml YEAR=2023
SURVEY ?= config/surveys/bra_pnadc_visita1.yaml
YEAR ?= 2024

.PHONY: help install test lint format ingest all

help:
	@echo "make install  - create the virtual environment from uv.lock and install git hooks"
	@echo "make test     - run the unit tests"
	@echo "make lint     - run ruff (lint + format check)"
	@echo "make format   - auto-format and auto-fix with ruff"
	@echo "make ingest   - raw fixed-width microdata -> Parquet, with validation report"
	@echo "make all      - rebuild everything from the raw files (grows phase by phase)"

install:
	uv sync --locked
	uv run pre-commit install

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

# Raw fixed-width microdata -> typed Parquet + reports/ingest_<survey>_<year>.md
ingest:
	uv run lacharm ingest --survey $(SURVEY) --year $(YEAR)

# Full pipeline from the raw files. Each phase appends its step here.
all: ingest
