# Determine this makefile's path. Be sure to place this BEFORE `include` directives, if any.
THIS_FILE := $(lastword $(MAKEFILE_LIST))

# help target from https://github.com/cargo-bins/cargo-quickinstall/blob/e17486445f6577c551a35876dca73132cc4c6298/Makefile#L70
help:
	@grep -E '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: deps dev_deps lint secure test_code test_actions test_actions_amd check test_check help Makefile

deps: ## Install all dependencies.
	uv pip install -r requirements.txt

dev_deps: ## Install all development dependencies.
	uv pip install -r requirements-dev.txt

lint: ## Lint code with ruff.
	ruff check .

secure: ## Check code security with bandit.
	$ bandit -r ffmwr -s B113,B310,B311,B608

test_code: ## Run tests with PyTest.
	pytest tests

test_actions: ## Test GitHub Actions using act.
	act -j build

test_actions_amd: ## Test package GitHub Actions on ARM architecture using act.
	act --container-architecture linux/amd64 -j build

check: deps dev_deps lint secure ## Run all code checks.
	echo "Code checked."

test_check: check test_code ## Run all code checks and tests.
	echo "Code checked and tested."
