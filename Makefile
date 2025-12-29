.PHONY: \
	help \
	init \
	sync \
	sync-prod \
	test \
	test-cov \
	lint \
	clean \
	show-settings \
	serve

help:  ## Show this help message
	@echo "Vibe coding supervisor without battaries"
	@echo "=============================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

init:  ## Initialize project dependencies and setup
	uv venv
	uv sync

sync:  ## Install dev dependencies. Default
	uv sync

sync-prod:  ## Install without dev dependencies
	uv sync --no-dev

test:  ## Run tests
	uv run pytest tests/ -v

test-cov:  ## Run tests with coverage
	uv run pytest tests/ --cov=src/vibe --cov-report=html --cov-report=term-missing

lint:  ## Run linting
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/

show-settings:  ## Show current application settings
	uv run show-settings
