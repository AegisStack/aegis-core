# Local linting/formatting targets. These mirror .github/workflows/lint.yml.
#
# Common usage:
#   make lint          # lint every package (check-only, same as CI)
#   make format        # auto-fix Python formatting + ruff issues
#   make lint-sdk      # just the SDK
#   make lint-backend  # just the dashboard backend
#   make lint-frontend # just the frontend
#   make install-hooks # install the pre-commit git hook

FRONTEND := aegis-dashboard/frontend
BACKEND  := aegis-dashboard/backend

# Invoke via `python -m` so the tools resolve from the active interpreter
# whether or not their console scripts are on PATH.
PY   := python
RUFF := $(PY) -m ruff
BLACK := $(PY) -m black
MYPY := $(PY) -m mypy

.PHONY: lint format lint-sdk lint-backend lint-frontend \
        format-sdk format-backend install-hooks

lint: lint-sdk lint-backend lint-frontend

# ---- SDK (aegis/, tests/) ----
# mypy is intentionally omitted for now (matches CI). Run `$(MYPY) aegis`
# manually if you want to work through the missing annotations.
lint-sdk:
	$(RUFF) check aegis tests
	$(BLACK) --check aegis tests

format-sdk:
	$(RUFF) check --fix aegis tests
	$(BLACK) aegis tests

# ---- Dashboard backend ----
lint-backend:
	cd $(BACKEND) && $(RUFF) check app tests && $(BLACK) --check app tests

format-backend:
	cd $(BACKEND) && $(RUFF) check --fix app tests && $(BLACK) app tests

# ---- Dashboard frontend ----
lint-frontend:
	cd $(FRONTEND) && npm run lint && npm run type-check

# ---- Combined ----
format: format-sdk format-backend

install-hooks:
	pip install pre-commit
	pre-commit install
