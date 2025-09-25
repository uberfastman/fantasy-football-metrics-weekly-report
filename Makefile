# You can set these variables from the command line and also from the environment.
DOCS_OPTS    ?=
DOCS_BUILD   ?= mkdocs

# Determine this makefile's path. Be sure to place this BEFORE `include` directives, if any.
THIS_FILE := $(lastword $(MAKEFILE_LIST))

# Put it first so that "make" without argument is like "make help".
help:
	@$(DOCS_BUILD) -h $(DOCS_OPTS) $(O)

.PHONY: update update_no_venv lint secure test_code test_actions test_actions_amd check test_check pre_deploy git_post_deploy git_update_docs help Makefile

update: ## Install/update all project dependencies.
	uv sync --all-extras --dev

update_no_venv: ## Install/update all project dependencies without making/using a virtual environment.
	uv pip install --system -r pyproject.toml --all-extras

lint: ## Lint code with ruff.
	ruff check .

secure: ## Check code security with bandit.
	bandit -r ffmwr -s B113,B310,B311,B608

test_code: ## Run code tests with PyTest.
	pytest tests

test_actions: ## Test GitHub Actions using act.
	act -j build

test_actions_amd: ## Test GitHub Actions on ARM architecture using act.
	act --container-architecture linux/amd64 -j build

check: update lint secure ## Run all code checks.
	echo "Code checked."

test_check: check test_code ## Run all code checks and tests.
	echo "Code checked and tested."

pre_deploy: ## Set project version in pyproject.toml using latest git tag and update Docker Compose files with project and Python versions
	python scripts/pre_deploy.py && uv lock

git_post_deploy:  ## Update git by adding changed files, committing with a message about updating documentation and version number, and pushing
	git add . && git commit -m 'updated version number and documentation' && git push

git_update_docs:  ## Update git by adding changed documentation files, committing with a message about updating documentation, and pushing
	git add . && git commit -m 'updated documentation' && git push
