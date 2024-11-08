# Variables

# Directories
SRC_DIR=hongxiu

# Targets
.PHONY: all install test check clean

all: install check test

install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync --all-extras

check: ## Run code quality tools.
	@echo "🔒 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🖊️ Formatting code: Running ruff"
	@uv run ruff format
	@echo "🚀 Linting code: ruff"
	@uv run ruff check
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy $(SRC_DIR)
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@uv run deptry .

test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run pytest --cov --cov-config=pyproject.toml --cov-report=xml

build: ## Build the package
	@echo "🚀 Building package: Running build"
	@uv build

publish: ## Publish the package to PyPI
	@echo "🚀 Publishing package: Running publish"
	@uv publish

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -r {} +
