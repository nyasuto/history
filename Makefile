PYTHON := python3
PIP := pip

.PHONY: help install run clean lint format

help:
	@echo "Available commands:"
	@echo "  make install  - Install dependencies using uv"
	@echo "  make run      - Run the Streamlit app"
	@echo "  make lint     - Check code with Ruff"
	@echo "  make format   - Format code with Ruff"
	@echo "  make clean    - Remove cache files"

install:
	pip install uv
	uv sync

run:
	uv run streamlit run app.py

lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .venv
	rm -rf .ruff_cache
