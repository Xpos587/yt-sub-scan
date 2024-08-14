project_dir := .

.PHONY: lint
lint:
	black --check --diff $(project_dir)
	ruff $(project_dir)
	mypy $(project_dir) --strict

.PHONY: reformat
reformat:
	black $(project_dir)
	ruff $(project_dir) --fix

.PHONY: run
run:
	python -m scripts || true

.PHONY: import-api-keys
import-api-keys:
	python -m utils.import_api_keys
