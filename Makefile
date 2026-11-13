# Single entry point for the project. Recipes are plain `uv run` commands so
# they behave the same on Windows, macOS, Linux and in CI.

.PHONY: help install test lint format all

help:
	@echo "make install  - create the virtual environment from uv.lock and install git hooks"
	@echo "make test     - run the unit tests"
	@echo "make lint     - run ruff (lint + format check)"
	@echo "make format   - auto-format and auto-fix with ruff"
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

# Full pipeline: raw files -> Parquet -> catalog -> harmonized data -> QC -> indicators.
# Each phase appends its step here.
all: lint test
