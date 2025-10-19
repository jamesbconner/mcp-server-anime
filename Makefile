# Makefile for MCP Server Anime development

.PHONY: help install install-dev test test-unit test-integration test-all coverage lint format type-check security clean build docs serve-docs pre-commit setup-dev

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install the package
	poetry install --no-dev

install-dev: ## Install the package with development dependencies
	poetry install
	poetry run pre-commit install

# Testing
test: test-unit ## Run unit tests (default)

test-unit: ## Run unit tests only
	poetry run pytest -m "not integration" -v

test-integration: ## Run integration tests only
	poetry run pytest -m integration -v

test-all: ## Run all tests including integration
	poetry run pytest -v

test-smoke: ## Run smoke tests for basic functionality
	poetry run pytest -m smoke -v

test-watch: ## Run tests in watch mode
	poetry run pytest-watch -- -m "not integration" -v

# Coverage
coverage: ## Run tests with coverage report
	poetry run pytest \
		--cov=src/mcp_server_anime \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=90

coverage-html: ## Generate HTML coverage report and open it
	poetry run pytest \
		--cov=src/mcp_server_anime \
		--cov-report=html \
		--cov-fail-under=90
	@echo "Opening coverage report..."
	@python -c "import webbrowser; webbrowser.open('htmlcov/index.html')"

# Code quality
lint: ## Run linting checks
	poetry run ruff check src tests

lint-fix: ## Run linting checks and fix issues
	poetry run ruff check --fix src tests

format: ## Format code with ruff
	poetry run ruff format src tests

format-check: ## Check code formatting
	poetry run ruff format --check src tests

type-check: ## Run type checking with mypy
	poetry run mypy src

security: ## Run security checks with bandit
	poetry run bandit -r src

security-report: ## Generate security report
	poetry run bandit -r src -f json -o bandit-report.json
	poetry run bandit -r src

# Quality checks (all)
quality: lint format-check type-check security ## Run all quality checks

quality-fix: lint-fix format ## Fix linting and formatting issues

# Pre-commit
pre-commit: ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	poetry run pre-commit install

pre-commit-update: ## Update pre-commit hooks
	poetry run pre-commit autoupdate

# Development setup
setup-dev: install-dev pre-commit-install ## Set up development environment
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything is working."

# Clean up
clean: ## Clean up build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf coverage.xml
	rm -rf .tox/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean ## Clean everything including virtual environment
	poetry env remove --all

# Build and distribution
build: clean ## Build the package
	poetry build

build-check: build ## Build and check the package
	poetry run twine check dist/*

publish-test: build-check ## Publish to test PyPI
	poetry publish --repository testpypi

publish: build-check ## Publish to PyPI
	poetry publish

# Documentation
docs: ## Build documentation
	@echo "Documentation build not yet implemented"

serve-docs: ## Serve documentation locally
	@echo "Documentation serving not yet implemented"

# Development utilities
shell: ## Open a poetry shell
	poetry shell

run: ## Run the MCP server
	poetry run mcp-server-anime

run-help: ## Show MCP server help
	poetry run mcp-server-anime --help

# Tox testing
tox: ## Run tests with tox
	tox

tox-parallel: ## Run tests with tox in parallel
	tox -p auto

# Docker (if needed)
docker-build: ## Build Docker image
	docker build -t mcp-server-anime .

docker-run: ## Run Docker container
	docker run --rm -it mcp-server-anime

# Benchmarking and profiling
benchmark: ## Run performance benchmarks
	@echo "Benchmarking not yet implemented"

profile: ## Profile the application
	@echo "Profiling not yet implemented"

# CI/CD helpers
ci-install: ## Install dependencies for CI
	pip install poetry
	poetry install

ci-test: ## Run tests for CI
	poetry run pytest \
		-m "not integration" \
		--cov=src/mcp_server_anime \
		--cov-report=xml \
		--cov-report=term-missing \
		--cov-fail-under=90 \
		--junit-xml=pytest-report.xml

ci-quality: ## Run quality checks for CI
	poetry run ruff check src tests --output-format=github
	poetry run ruff format --check src tests
	poetry run mypy src
	poetry run bandit -r src

# Version management
version: ## Show current version
	poetry version

version-patch: ## Bump patch version
	poetry version patch

version-minor: ## Bump minor version
	poetry version minor

version-major: ## Bump major version
	poetry version major

# Environment info
info: ## Show environment information
	@echo "Python version: $(shell python --version)"
	@echo "Poetry version: $(shell poetry --version)"
	@echo "Project version: $(shell poetry version -s)"
	@echo "Virtual environment: $(shell poetry env info --path)"

# Default Python and Poetry commands
python: ## Run Python in poetry environment
	poetry run python

pip: ## Run pip in poetry environment
	poetry run pip

# Help is the default target
.DEFAULT_GOAL := help